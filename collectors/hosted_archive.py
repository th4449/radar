"""The archive in the hosted project. See BUILD_PLAN.md section 3 and docs/launch_checklist.md.

Every stored file lives in one private bucket of the project's storage, under the same path a
folder on disk gives it: the first two characters of its hash, then the hash and a suffix. So
a document's storage path means the same whichever store holds the file.

- **A stored file is never written over.** A second upload of the same bytes is refused by the
  service as a duplicate, and that is fine: the name is the hash.
- **A file read back is checked against its name.** Bytes that do not match their hash are
  refused, not returned.
- The bucket is private and has no policy. Only the service key reads or writes it.

Which store a job uses comes from its settings:

    RADAR_ARCHIVE_DIR                       a folder on this machine
    RADAR_ARCHIVE_URL, RADAR_ARCHIVE_KEY    the hosted project and its service key

The key is a secret. It is never written into the repository, a log or an error.

The answers this is written to are the ones the storage service gave when its local copy was
asked on November 23, 2026. **It has not been run against a hosted project.**
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path

import httpx

from collectors.base import ArchiveStore, LocalArchive, sha256_hex

BUCKET = "archive"
CONTENT_TYPES = {
    "html": "text/html",
    "pdf": "application/pdf",
    "txt": "text/plain",
    "json": "application/json",
    "xml": "application/xml",
    "csv": "text/csv",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "zip": "application/zip",
}


class NotConfigured(Exception):
    """The settings do not say where the archive is."""


class ArchiveError(OSError):
    """The storage service refused or failed. A run counts it as an error and goes on."""


def _problem(response: httpx.Response) -> tuple[str, str]:
    """The status and code of an answer that is not a success.

    The service has answered 400 with the real status in the body. Both forms are read.
    """
    status, code = str(response.status_code), ""
    try:
        body = response.json()
    except ValueError:
        body = None
    if isinstance(body, dict):
        status = str(body.get("statusCode") or status)
        code = str(body.get("code") or body.get("error") or "")
    return status, code


class SupabaseArchive:
    """One private bucket in the hosted project's storage."""

    def __init__(
        self,
        url: str,
        key: str,
        *,
        bucket: str = BUCKET,
        transport: httpx.BaseTransport | None = None,
        timeout: float = 120.0,
    ) -> None:
        self._where = f"{url.rstrip('/')}/storage/v1/object/{bucket}"
        self._client = httpx.Client(
            headers={"Authorization": f"Bearer {key}", "apikey": key},
            transport=transport,
            timeout=timeout,
        )

    def __repr__(self) -> str:
        return f"SupabaseArchive({self._where})"

    def put(self, sha256: str, body: bytes, suffix: str) -> str:
        if sha256_hex(body) != sha256:
            raise ValueError("sha256 does not match the body")
        storage_path = f"{sha256[:2]}/{sha256}.{suffix}"
        content_type = CONTENT_TYPES.get(suffix, "application/octet-stream")
        response = self._client.post(
            f"{self._where}/{storage_path}", content=body, headers={"Content-Type": content_type}
        )
        if response.is_success:
            return storage_path
        status, code = _problem(response)
        if status == "409":
            return storage_path  # the same bytes are already there
        raise ArchiveError(f"the archive refused {storage_path}: {status} {code}".rstrip())

    def get(self, storage_path: str) -> bytes:
        response = self._client.get(f"{self._where}/{storage_path}")
        if not response.is_success:
            status, code = _problem(response)
            if status == "404":
                raise ArchiveError(f"{storage_path} is not in the archive")
            raise ArchiveError(f"the archive refused {storage_path}: {status} {code}".rstrip())
        body = response.content
        named = Path(storage_path).stem
        if sha256_hex(body) != named:
            raise ArchiveError(f"{storage_path} does not match its hash")
        return body


def archive_from_env(env: Mapping[str, str] | None = None) -> ArchiveStore:
    """The store the settings name. Raises NotConfigured when they name none, or two."""
    env = os.environ if env is None else env
    folder = (env.get("RADAR_ARCHIVE_DIR") or "").strip()
    url = (env.get("RADAR_ARCHIVE_URL") or "").strip()
    key = (env.get("RADAR_ARCHIVE_KEY") or "").strip()
    if folder and url:
        raise NotConfigured("both RADAR_ARCHIVE_DIR and RADAR_ARCHIVE_URL are set. Set one.")
    if folder:
        return LocalArchive(Path(folder))
    if url:
        if not key:
            raise NotConfigured("RADAR_ARCHIVE_URL is set and RADAR_ARCHIVE_KEY is not")
        if not url.startswith("https://") and not url.startswith("http://127.0.0.1"):
            raise NotConfigured("RADAR_ARCHIVE_URL must be an https address")
        bucket = (env.get("RADAR_ARCHIVE_BUCKET") or BUCKET).strip()
        return SupabaseArchive(url, key, bucket=bucket)
    raise NotConfigured(
        "set RADAR_ARCHIVE_DIR for a folder, or RADAR_ARCHIVE_URL and RADAR_ARCHIVE_KEY for "
        "the hosted project"
    )
