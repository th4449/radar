"""Shared fetch and archive code for every collector.

The rules this module enforces, from BUILD_PLAN.md sections 6 and 12:

- A source is fetched only after its terms and robots rules were read and written up.
- robots.txt is checked before every request, on every host a redirect leads to. There is no
  switch to turn the check off.
- Requests are slow, one host at a time, and identify the collector with a contact address.
- A refusal from the site (401, 403, 451, repeated 429) stops the run. We never work around a
  block, a captcha or a login.
- Everything fetched is stored with its URL, retrieval time and SHA-256 hash.
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import hashlib
import os
import time
from collections import deque
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import ClassVar, Protocol
from urllib.parse import urljoin, urlsplit

import httpx
from protego import Protego

from pipeline.config import Source
from pipeline.extract import SUFFIX, Extracted, extract

VERSION = "0.1"
AGENT_TOKEN = "DataCenterRadar"  # noqa: S105 - the robots.txt product token, not a secret

DEFAULT_MIN_INTERVAL = 5.0  # seconds between requests to one host
MAX_BODY_BYTES = 50 * 1024 * 1024
MAX_REDIRECTS = 5
MAX_ATTEMPTS = 3
MAX_BACKOFF = 120.0
TIMEOUT = 30.0

REDIRECT_STATUSES = frozenset({301, 302, 303, 307, 308})
RETRY_STATUSES = frozenset({429, 500, 502, 503, 504})
# The site is telling us no. Stop and tell a person.
BLOCK_STATUSES = frozenset({401, 403, 407, 451})


class FetchError(Exception):
    """A request failed for an ordinary reason, such as a 404 or a timeout."""


class NotPermitted(FetchError):
    """Our own rules forbid fetching this source right now."""


class LayoutChanged(ValueError):
    """A page no longer looks like the saved copy its parser was written against."""


class RobotsDisallowed(FetchError):
    """robots.txt forbids the URL, or could not be read."""


class Blocked(FetchError):
    """The site refused us. Never retried and never worked around."""


class TooLarge(FetchError):
    """The response is bigger than MAX_BODY_BYTES."""


# --- identity -----------------------------------------------------------------------------------


def user_agent(contact: str | None = None) -> str:
    """The user agent every request carries. It needs a contact address a site owner can use."""
    contact = (contact or os.environ.get("RADAR_CONTACT") or "").strip()
    if "@" not in contact and not contact.startswith("https://"):
        raise NotPermitted(
            "Set RADAR_CONTACT to the project's public contact address before any live request."
        )
    return f"{AGENT_TOKEN}/{VERSION} (public records collector; contact: {contact})"


def check_source_permitted(source: Source, *, by_hand: bool = False) -> None:
    """Raise unless this source may be fetched.

    by_hand marks a single request a person runs themselves, such as saving a test fixture.
    It lifts only the "manual" setting. It never lifts a missing source note or a restriction.
    """
    if source.robots_status in ("restricted", "blocked"):
        raise NotPermitted(
            f"{source.id}: automated access is {source.robots_status}. See docs/sources."
        )
    if source.verified_at is None:
        raise NotPermitted(
            f"{source.id}: terms and robots rules are not written up yet in docs/sources."
        )
    if source.method == "manual" and not by_hand:
        raise NotPermitted(f"{source.id}: this source is collected by a person, not a job.")


# --- pacing -------------------------------------------------------------------------------------


class RateLimiter:
    """At most one request per host every min_interval seconds."""

    def __init__(
        self,
        min_interval: float = DEFAULT_MIN_INTERVAL,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.min_interval = min_interval
        self._clock = clock
        self._sleep = sleep
        self._last: dict[str, float] = {}

    def wait(self, host: str, interval: float | None = None) -> None:
        interval = max(self.min_interval, interval or 0.0)
        last = self._last.get(host)
        if last is not None:
            remaining = interval - (self._clock() - last)
            if remaining > 0:
                self._sleep(remaining)
        self._last[host] = self._clock()


# --- robots.txt ---------------------------------------------------------------------------------


class Robots:
    """Reads and caches robots.txt for each host. When in doubt the answer is no.

    Rules are matched the way RFC 9309 describes: the longest matching rule wins, and the
    wildcards * and $ work. Python's own robotparser does neither, and would wrongly allow
    paths that a rule such as "Disallow: /*/" forbids.
    """

    def __init__(self, client: httpx.Client, limiter: RateLimiter) -> None:
        self._client = client
        self._limiter = limiter
        self._cache: dict[str, Protego | bool] = {}

    def _load(self, origin: str) -> Protego | bool:
        if origin in self._cache:
            return self._cache[origin]
        self._limiter.wait(urlsplit(origin).netloc)
        rules: Protego | bool
        try:
            resp = self._client.get(origin + "/robots.txt", follow_redirects=True)
        except httpx.TransportError:
            rules = False  # could not read the rules, so do not proceed
        else:
            if resp.status_code == 200:
                # A byte order mark at the start would hide the first line from the parser,
                # and a file that bars every path would then read as allowing them all.
                rules = Protego.parse(resp.text.lstrip("﻿"))
            elif resp.status_code in (404, 410):
                rules = True  # the site publishes no rules
            else:
                # A refusal or a server error on robots.txt itself. Treat as disallowed.
                rules = False
        self._cache[origin] = rules
        return rules

    def allowed(self, url: str) -> bool:
        parts = urlsplit(url)
        rules = self._load(f"{parts.scheme}://{parts.netloc}")
        if isinstance(rules, bool):
            return rules
        return rules.can_fetch(url, AGENT_TOKEN)

    def crawl_delay(self, url: str) -> float | None:
        parts = urlsplit(url)
        rules = self._cache.get(f"{parts.scheme}://{parts.netloc}")
        if isinstance(rules, Protego):
            delay = rules.crawl_delay(AGENT_TOKEN)
            return float(delay) if delay else None
        return None


# --- fetching -----------------------------------------------------------------------------------


@dataclass(frozen=True)
class FetchResult:
    url: str  # the URL we asked for
    final_url: str  # where redirects ended
    status: int
    content_type: str | None
    etag: str | None
    last_modified: str | None
    body: bytes
    retrieved_at: dt.datetime
    not_modified: bool = False


class Fetcher:
    """A polite HTTP client bound to one source."""

    def __init__(
        self,
        source: Source,
        *,
        contact: str | None = None,
        by_hand: bool = False,
        transport: httpx.BaseTransport | None = None,
        min_interval: float = DEFAULT_MIN_INTERVAL,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
        validators: dict[str, tuple[str | None, str | None]] | None = None,
    ) -> None:
        check_source_permitted(source, by_hand=by_hand)
        self.source = source
        # The limit is the same for every source unless config/sources.yaml raises it for one.
        self.max_body_bytes = (
            source.max_body_mb * 1024 * 1024 if source.max_body_mb else MAX_BODY_BYTES
        )
        self._sleep = sleep
        self._client = httpx.Client(
            headers={"User-Agent": user_agent(contact), "Accept-Encoding": "gzip"},
            timeout=TIMEOUT,
            follow_redirects=False,
            transport=transport,
        )
        self._limiter = RateLimiter(min_interval, clock, sleep)
        self._robots = Robots(self._client, self._limiter)
        # url -> (etag, last_modified) from an earlier run, for conditional requests.
        self.validators = validators if validators is not None else {}

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> Fetcher:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def get(self, url: str) -> FetchResult:
        current = url
        for _hop in range(MAX_REDIRECTS + 1):
            parts = urlsplit(current)
            if parts.scheme not in ("http", "https") or not parts.netloc:
                raise FetchError(f"not an http(s) URL: {current}")
            if not self._robots.allowed(current):
                raise RobotsDisallowed(f"robots.txt does not allow {current}")
            status, headers, body = self._request(current, conditional=current == url)
            if status in REDIRECT_STATUSES and "location" in headers:
                current = urljoin(current, headers["location"])
                continue
            break
        else:
            raise FetchError(f"more than {MAX_REDIRECTS} redirects from {url}")

        now = dt.datetime.now(dt.UTC)
        if status == 304:
            etag, last_modified = self.validators.get(url, (None, None))
            return FetchResult(url, current, 304, None, etag, last_modified, b"", now, True)
        if status != 200:
            raise FetchError(f"HTTP {status} for {current}")
        etag, last_modified = headers.get("etag"), headers.get("last-modified")
        if etag or last_modified:
            self.validators[url] = (etag, last_modified)
        return FetchResult(
            url, current, 200, headers.get("content-type"), etag, last_modified, body, now
        )

    def _request(self, url: str, *, conditional: bool) -> tuple[int, httpx.Headers, bytes]:
        host = urlsplit(url).netloc
        headers: dict[str, str] = {}
        if conditional and url in self.validators:
            etag, last_modified = self.validators[url]
            if etag:
                headers["If-None-Match"] = etag
            if last_modified:
                headers["If-Modified-Since"] = last_modified

        for attempt in range(1, MAX_ATTEMPTS + 1):
            self._limiter.wait(host, self._robots.crawl_delay(url))
            backoff = min(MAX_BACKOFF, self._limiter.min_interval * 2**attempt)
            try:
                with self._client.stream("GET", url, headers=headers) as resp:
                    status = resp.status_code
                    if status in BLOCK_STATUSES:
                        raise Blocked(
                            f"HTTP {status} from {host}. Stopping. Do not work around it."
                        )
                    if status in RETRY_STATUSES:
                        if attempt == MAX_ATTEMPTS:
                            if status == 429:
                                raise Blocked(f"{host} keeps answering 429. Stopping.")
                            raise FetchError(f"HTTP {status} for {url} after {attempt} attempts")
                        self._sleep(_retry_after(resp.headers, backoff))
                        continue
                    body = bytearray()
                    for chunk in resp.iter_bytes():
                        body += chunk
                        if len(body) > self.max_body_bytes:
                            raise TooLarge(f"{url} is larger than {self.max_body_bytes} bytes")
                    return status, resp.headers, bytes(body)
            except httpx.TransportError as exc:
                if attempt == MAX_ATTEMPTS:
                    raise FetchError(f"{url}: {exc!r} after {attempt} attempts") from exc
                self._sleep(backoff)
        raise AssertionError("unreachable")


def _retry_after(headers: httpx.Headers, default: float) -> float:
    """Honor Retry-After when it is a number of seconds, never waiting less than our backoff."""
    value = headers.get("retry-after", "")
    if value.isdigit():
        return min(MAX_BACKOFF, max(default, float(value)))
    return default


# --- archive ------------------------------------------------------------------------------------


def sha256_hex(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


class ArchiveStore(Protocol):
    def put(self, sha256: str, body: bytes, suffix: str) -> str:
        """Store the bytes and return the storage path. Storing the same bytes twice is fine."""

    def get(self, storage_path: str) -> bytes: ...


class LocalArchive:
    """Files on disk, named by their hash. The hosted backend comes with the Supabase project."""

    def __init__(self, root: Path) -> None:
        self.root = Path(root)

    def put(self, sha256: str, body: bytes, suffix: str) -> str:
        if sha256_hex(body) != sha256:
            raise ValueError("sha256 does not match the body")
        storage_path = f"{sha256[:2]}/{sha256}.{suffix}"
        target = self.root / storage_path
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            tmp = target.with_suffix(target.suffix + ".part")
            tmp.write_bytes(body)
            tmp.replace(target)
        return storage_path

    def get(self, storage_path: str) -> bytes:
        return (self.root / storage_path).read_bytes()


@dataclass(frozen=True)
class ArchivedDocument:
    source_id: str  # the id in config/sources.yaml
    url: str
    retrieved_at: dt.datetime
    sha256: str
    storage_path: str
    text: str
    raw_meta: dict


def archive(
    result: FetchResult, source: Source, store: ArchiveStore, extra_meta: dict | None = None
) -> ArchivedDocument:
    """Hash the body, store the original and extract its text."""
    digest = sha256_hex(result.body)
    extracted: Extracted = extract(result.body, result.content_type)
    storage_path = store.put(digest, result.body, SUFFIX[extracted.kind])
    meta = {
        "final_url": result.final_url,
        "content_type": result.content_type,
        "etag": result.etag,
        "last_modified": result.last_modified,
        "bytes": len(result.body),
        "kind": extracted.kind,
        "pages": extracted.pages,
        "title": extracted.title,
        "needs_ocr": extracted.needs_ocr,
        **({"members": list(extracted.members)} if extracted.members else {}),
        # Text read from a scan by a machine is marked as such, with how sure the machine was.
        **({"ocr": extracted.ocr} if extracted.ocr else {}),
        **(extra_meta or {}),
    }
    return ArchivedDocument(
        source.id, result.url, result.retrieved_at, digest, storage_path, extracted.text, meta
    )


# --- collector ----------------------------------------------------------------------------------


@dataclass(frozen=True)
class Reduced:
    """What a collector stores in place of a file it does not keep."""

    body: bytes
    content_type: str
    meta: dict = field(default_factory=dict)  # recorded with the document


class Sink(Protocol):
    """Where runs and documents are recorded. See pipeline/store.py."""

    def start_run(self, source: Source, runner: str | None = None) -> int: ...

    def save_document(self, doc: ArchivedDocument) -> bool:
        """Return True when the document is new for its source."""

    def finish_run(self, run_id: int, summary: RunSummary) -> None: ...

    def known(self, source: Source) -> dict[str, dict]:
        """The stored metadata of the newest document for each URL of this source."""

    def find(self, source: Source, url: str) -> ArchivedDocument | None:
        """The newest stored document for one URL of this source."""


def _original(result: FetchResult) -> dict:
    """What is recorded about a fetched file that is not itself stored."""
    return {"original_sha256": sha256_hex(result.body), "original_bytes": len(result.body)}


@dataclass
class RunSummary:
    source_id: str
    status: str = "running"  # ok, partial, failed or blocked
    documents_seen: int = 0
    documents_new: int = 0
    errors: int = 0
    error: str | None = None
    detail: dict = field(default_factory=dict)


class Collector:
    """One source. A subclass names the source and lists the URLs to start from.

    A source that is one page or a fixed list needs only urls(). A source that is an index
    leading to other pages also defines follow(). A page that carries tracking codes which
    change on every request defines content_key(), so an unchanged page is not stored again.

    A source whose file holds far more than the radar should keep defines reduce(). The run then
    stores what reduce() returns and records the address, retrieval time, size and hash of the
    file itself. The file is never stored, not even when the run fails on it.
    """

    source_id: ClassVar[str]
    max_urls: ClassVar[int] = 500  # a run that wants more than this has gone wrong
    # A source that is many sites sets this. A refusal then closes that one site for the rest
    # of the run and the other sites go on. The refusal is still final: nothing is retried.
    refusal_closes_host_only: ClassVar[bool] = False

    def urls(self) -> Iterable[str]:
        raise NotImplementedError

    def follow(self, result: FetchResult) -> Iterable[str]:
        """More URLs found in a page that was just fetched in full. Each URL is fetched once."""
        return ()

    def content_key(self, result: FetchResult) -> str | None:
        """A key that changes only when what the page says changes, or None to use the bytes."""
        return None

    def reduce(self, result: FetchResult) -> Reduced | None:
        """What to store in place of the fetched file, or None to store the file itself."""
        return None

    def facts(self, result: FetchResult) -> dict | None:
        """More to record with a file that is stored as it is, such as the page it came from."""
        return None

    def run(
        self,
        *,
        source: Source,
        fetcher: Fetcher,
        store: ArchiveStore,
        sink: Sink,
        runner: str | None = None,
    ) -> RunSummary:
        if source.id != self.source_id:
            raise ValueError(f"{type(self).__name__} collects {self.source_id}, not {source.id}")
        summary = RunSummary(source.id)
        run_id = sink.start_run(source, runner)
        failed_urls: list[str] = []
        refused: dict[str, str] = {}  # host -> why, for a collector of many sites
        try:
            # What earlier runs stored: validators for conditional requests, and content keys.
            known = sink.known(source)
            for url, meta in known.items():
                if meta.get("etag") or meta.get("last_modified"):
                    fetcher.validators.setdefault(
                        url, (meta.get("etag"), meta.get("last_modified"))
                    )

            queue: deque[str] = deque(self.urls())
            asked: set[str] = set()
            while queue:
                url = queue.popleft()
                if url in asked or urlsplit(url).netloc.lower() in refused:
                    continue
                if len(asked) >= self.max_urls:
                    summary.errors += 1
                    summary.error = f"stopped after {self.max_urls} URLs"
                    break
                asked.add(url)
                try:
                    result = fetcher.get(url)
                except (Blocked, RobotsDisallowed, NotPermitted) as exc:
                    if self.refusal_closes_host_only and not isinstance(exc, NotPermitted):
                        # One site of many said no. Leave it alone and read the others.
                        refused[urlsplit(url).netloc.lower()] = str(exc)
                        summary.errors += 1
                        summary.error = str(exc)
                        continue
                    # A refusal ends the run. A person decides what happens next.
                    summary.status = "blocked"
                    summary.error = str(exc)
                    break
                except FetchError as exc:
                    summary.errors += 1
                    summary.error = str(exc)
                    failed_urls.append(url)
                    continue
                summary.documents_seen += 1
                if result.not_modified:
                    continue
                reduces = type(self).reduce is not Collector.reduce
                try:
                    reduced = self.reduce(result)
                    key = self.content_key(result)
                    more = list(self.follow(result))
                except LayoutChanged as exc:
                    # Keep the page that surprised us, then stop. A person looks at it. A file
                    # this collector does not keep is not kept here either: only its hash is.
                    if reduces:
                        summary.detail["unread_file"] = _original(result)
                    elif sink.save_document(archive(result, source, store)):
                        summary.documents_new += 1
                    summary.status = "failed"
                    summary.error = f"{url}: {exc}"
                    break
                queue.extend(more)
                if key is not None and known.get(url, {}).get("content_key") == key:
                    continue  # the page says what it said last time
                extra = {"content_key": key} if key is not None else {}
                if reduced is None:
                    extra |= self.facts(result) or {}
                if reduced is not None:
                    extra |= {**reduced.meta, **_original(result), "original_kept": False}
                    result = dataclasses.replace(
                        result, body=reduced.body, content_type=reduced.content_type
                    )
                if sink.save_document(archive(result, source, store, extra or None)):
                    summary.documents_new += 1
            if summary.status == "running":
                if summary.errors == 0:
                    summary.status = "ok"
                elif summary.documents_seen > 0:
                    summary.status = "partial"
                else:
                    summary.status = "failed"
        except Exception as exc:
            summary.status = "failed"
            summary.error = repr(exc)
            raise
        finally:
            if failed_urls:
                summary.detail["failed_urls"] = failed_urls
            if refused:
                summary.detail["refused_hosts"] = refused
            sink.finish_run(run_id, summary)
        return summary
