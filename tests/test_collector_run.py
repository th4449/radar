"""A sample collector fetches, archives, extracts and logs, end to end, on synthetic fixtures."""

from __future__ import annotations

from pathlib import Path

import httpx

from collectors.base import Collector, Fetcher, LocalArchive
from pipeline.store import MemorySink

from .helpers import CONTACT, FakeClock, Site, make_pdf, make_source

SYNTHETIC = Path(__file__).parent / "fixtures" / "synthetic"
NOTICE = "https://records.example.gov/notices/falcon.html"
PERMIT = "https://records.example.gov/permits/177301.pdf"
MISSING = "https://records.example.gov/notices/gone.html"

NOTICE_BODY = (SYNTHETIC / "notice.html").read_bytes()
PERMIT_BODY = make_pdf(["Pending air permit application 177301", "Applicant: Example Power LLC"])


class SampleCollector(Collector):
    source_id = "tx_example"

    def __init__(self, urls: list[str]) -> None:
        self._urls = urls

    def urls(self) -> list[str]:
        return self._urls


def site() -> Site:
    return Site(
        {
            NOTICE: httpx.Response(200, content=NOTICE_BODY, headers={"Content-Type": "text/html"}),
            PERMIT: httpx.Response(
                200, content=PERMIT_BODY, headers={"Content-Type": "application/pdf"}
            ),
        }
    )


def run(web: Site, urls: list[str], tmp_path, sink: MemorySink | None = None):
    clock = FakeClock()
    source = make_source()
    sink = sink or MemorySink()
    with Fetcher(
        source, contact=CONTACT, transport=web.transport, clock=clock, sleep=clock.sleep
    ) as f:
        summary = SampleCollector(urls).run(
            source=source, fetcher=f, store=LocalArchive(tmp_path), sink=sink, runner="test"
        )
    return summary, sink


def test_end_to_end_html_and_pdf(tmp_path):
    summary, sink = run(site(), [NOTICE, PERMIT], tmp_path)

    assert (summary.status, summary.documents_seen, summary.documents_new, summary.errors) == (
        "ok", 2, 2, 0,
    )  # fmt: skip
    assert sink.runs[1]["status"] == "ok"
    assert sink.runs[1]["runner"] == "test"

    docs = {d.url: d for d in sink.documents.values()}
    notice, permit = docs[NOTICE], docs[PERMIT]
    # Traceability: URL, retrieval time, hash, and the original bytes on disk.
    archive = LocalArchive(tmp_path)
    assert archive.get(notice.storage_path) == NOTICE_BODY
    assert archive.get(permit.storage_path) == PERMIT_BODY
    assert notice.retrieved_at.tzinfo is not None
    assert len(notice.sha256) == 64 and notice.sha256 != permit.sha256
    assert "Project Falcon LLC" in notice.text
    assert "Example Power LLC" in permit.text
    assert permit.raw_meta["pages"] == 2


def test_a_second_run_finds_nothing_new(tmp_path):
    sink = MemorySink()
    run(site(), [NOTICE, PERMIT], tmp_path, sink)
    summary, _ = run(site(), [NOTICE, PERMIT], tmp_path, sink)
    assert (summary.status, summary.documents_seen, summary.documents_new) == ("ok", 2, 0)
    assert len(sink.documents) == 2
    assert len(sink.runs) == 2


def test_a_broken_link_makes_the_run_partial_and_is_logged(tmp_path):
    summary, sink = run(site(), [NOTICE, MISSING], tmp_path)
    assert (summary.status, summary.documents_new, summary.errors) == ("partial", 1, 1)
    assert sink.runs[1]["detail"] == {"failed_urls": [MISSING]}
    assert "404" in sink.runs[1]["error"]


def test_all_links_failing_is_a_failed_run(tmp_path):
    summary, sink = run(site(), [MISSING], tmp_path)
    assert summary.status == "failed"
    assert sink.runs[1]["status"] == "failed"


def test_a_refusal_stops_the_run_at_once(tmp_path):
    web = site()
    web.routes[NOTICE] = httpx.Response(403)
    summary, sink = run(web, [NOTICE, PERMIT], tmp_path)
    assert summary.status == "blocked"
    assert "Do not work around it" in sink.runs[1]["error"]
    assert PERMIT not in web.urls()  # nothing more was asked of the site
    assert sink.documents == {}


def test_robots_disallow_stops_the_run(tmp_path):
    web = site()
    web.robots = "User-agent: *\nDisallow: /"
    summary, sink = run(web, [NOTICE, PERMIT], tmp_path)
    assert summary.status == "blocked"
    assert web.page_urls() == []


# --- sources that are an index leading to other pages -------------------------------------------

LISTING = "https://records.example.gov/notices"


class IndexCollector(Collector):
    """Starts at a listing and follows the links it names. The listing carries a visit counter."""

    source_id = "tx_example"

    def urls(self) -> list[str]:
        return [LISTING]

    def follow(self, result):
        if result.url == LISTING:
            return [NOTICE, PERMIT, NOTICE, LISTING]  # repeats and a loop back to the start
        return ()

    def content_key(self, result):
        if result.url == LISTING:
            return result.body.split(b"<!--")[0].decode()
        return None


def listing_site(counter: int, etag: str | None = None) -> Site:
    def permit(request: httpx.Request) -> httpx.Response:
        if etag and request.headers.get("If-None-Match") == etag:
            return httpx.Response(304)
        headers = {"Content-Type": "application/pdf"}
        if etag:
            headers["ETag"] = etag
        return httpx.Response(200, content=PERMIT_BODY, headers=headers)

    web = site()
    web.routes[LISTING] = httpx.Response(
        200,
        content=b"<html><body>Two notices</body></html><!-- visit %d -->" % counter,
        headers={"Content-Type": "text/html"},
    )
    web.routes[PERMIT] = permit
    return web


def run_index(web: Site, tmp_path, sink: MemorySink, collector: Collector | None = None):
    clock = FakeClock()
    source = make_source()
    with Fetcher(
        source, contact=CONTACT, transport=web.transport, clock=clock, sleep=clock.sleep
    ) as f:
        return (collector or IndexCollector()).run(
            source=source, fetcher=f, store=LocalArchive(tmp_path), sink=sink, runner="test"
        )


def test_followed_links_are_each_fetched_once(tmp_path):
    web, sink = listing_site(1), MemorySink()
    summary = run_index(web, tmp_path, sink)
    assert (summary.status, summary.documents_seen, summary.documents_new) == ("ok", 3, 3)
    assert web.page_urls() == [LISTING, NOTICE, PERMIT]


def test_a_page_with_the_same_content_key_is_not_stored_again(tmp_path):
    sink = MemorySink()
    run_index(listing_site(1), tmp_path, sink)
    web = listing_site(2)  # the listing's bytes differ, what it says does not
    summary = run_index(web, tmp_path, sink)
    assert (summary.status, summary.documents_seen, summary.documents_new) == ("ok", 3, 0)
    assert web.page_urls() == [LISTING, NOTICE, PERMIT]  # its links are still followed
    assert len(sink.documents) == 3


def test_validators_from_earlier_runs_make_the_next_request_conditional(tmp_path):
    sink = MemorySink()
    run_index(listing_site(1, etag='"v1"'), tmp_path, sink)
    web = listing_site(1, etag='"v1"')
    summary = run_index(web, tmp_path, sink)
    asked = [r for r in web.requests if str(r.url) == PERMIT]
    assert [r.headers.get("If-None-Match") for r in asked] == ['"v1"']
    assert (summary.documents_seen, summary.documents_new) == (3, 0)


def test_a_run_that_wants_too_many_urls_stops(tmp_path):
    class Runaway(IndexCollector):
        max_urls = 2

    web, sink = listing_site(1), MemorySink()
    summary = run_index(web, tmp_path, sink, Runaway())
    assert summary.status == "partial"
    assert "stopped after 2 URLs" in summary.error
    assert web.page_urls() == [LISTING, NOTICE]


# --- a source that is many sites ------------------------------------------------------------------

OTHER = "https://www.othertown.example.gov/agendas/november.pdf"
PERMIT_2 = "https://records.example.gov/permits/177302.pdf"


class ManySites(SampleCollector):
    """One source, several governments' sites. A refusal closes one site, not the run."""

    refusal_closes_host_only = True

    def facts(self, result):
        return {"record": "agenda_file", "page": "https://example.gov/agendas"}


def run_many(web: Site, urls: list[str], tmp_path):
    clock = FakeClock()
    source = make_source()
    sink = MemorySink()
    with Fetcher(
        source, contact=CONTACT, transport=web.transport, clock=clock, sleep=clock.sleep
    ) as f:
        summary = ManySites(urls).run(
            source=source, fetcher=f, store=LocalArchive(tmp_path), sink=sink, runner="test"
        )
    return summary, sink


def many_sites() -> Site:
    web = site()
    pdf = httpx.Response(200, content=PERMIT_BODY, headers={"Content-Type": "application/pdf"})
    web.routes[OTHER] = pdf
    web.routes[PERMIT_2] = pdf
    return web


def test_a_refusal_from_one_site_of_many_closes_that_site_and_the_rest_go_on(tmp_path):
    web = many_sites()
    web.routes[NOTICE] = httpx.Response(403)
    summary, sink = run_many(web, [NOTICE, PERMIT, OTHER, PERMIT_2], tmp_path)

    assert summary.status == "partial"
    # The site that refused was asked once and never again, by any address.
    assert web.page_urls() == [NOTICE, OTHER]
    assert [d.url for d in sink.documents.values()] == [OTHER]
    refused = sink.runs[1]["detail"]["refused_hosts"]
    assert list(refused) == ["records.example.gov"]
    assert "Do not work around it" in refused["records.example.gov"]


def test_a_robots_file_that_bars_one_site_of_many_closes_only_that_site(tmp_path):
    web = many_sites()
    web.routes["https://records.example.gov/robots.txt"] = httpx.Response(
        200, text="User-agent: *\nDisallow: /"
    )
    summary, sink = run_many(web, [NOTICE, OTHER], tmp_path)

    assert summary.status == "partial"
    assert web.page_urls() == [OTHER]
    assert list(sink.runs[1]["detail"]["refused_hosts"]) == ["records.example.gov"]


def test_every_site_refusing_is_a_failed_run_with_nothing_stored(tmp_path):
    web = many_sites()
    web.robots = "User-agent: *\nDisallow: /"
    summary, sink = run_many(web, [NOTICE, OTHER], tmp_path)
    assert summary.status == "failed"
    assert web.page_urls() == [] and sink.documents == {}


def test_a_collector_of_one_site_still_stops_at_a_refusal(tmp_path):
    assert SampleCollector.refusal_closes_host_only is False
    web = many_sites()
    web.routes[NOTICE] = httpx.Response(403)
    summary, _ = run(web, [NOTICE, OTHER], tmp_path)
    assert summary.status == "blocked"
    assert web.page_urls() == [NOTICE]


def test_a_file_stored_as_it_is_carries_what_the_collector_knows_about_it(tmp_path):
    summary, sink = run_many(many_sites(), [OTHER], tmp_path)
    assert summary.status == "ok"
    (doc,) = sink.documents.values()
    assert doc.raw_meta["record"] == "agenda_file"
    assert doc.raw_meta["page"] == "https://example.gov/agendas"
    assert LocalArchive(tmp_path).get(doc.storage_path) == PERMIT_BODY  # the file itself
