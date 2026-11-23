"""The archive in the hosted project. Written before the code.

A stand-in answers the way the storage service answered on November 23, 2026, when its local
copy was asked: a second upload of the same file is refused as a duplicate, and a missing
file is a 400 whose body says 404. A later version may use the plain status codes, so both
are taken.
"""

from __future__ import annotations

import hashlib
import json

import httpx
import pytest

from collectors.base import LocalArchive
from collectors.hosted_archive import ArchiveError, NotConfigured, SupabaseArchive, archive_from_env

KEY = "test-service-key"
BODY = b"<html>a stored page</html>"
SHA = hashlib.sha256(BODY).hexdigest()
PATH = f"{SHA[:2]}/{SHA}.html"


class Storage:
    """The storage service, as far as the archive uses it."""

    def __init__(self, plain_statuses: bool = False) -> None:
        self.objects: dict[str, bytes] = {}
        self.requests: list[httpx.Request] = []
        self.plain = plain_statuses

    def _error(self, status: int, code: str) -> httpx.Response:
        body = {"statusCode": str(status), "error": code, "message": code, "code": code}
        return httpx.Response(status if self.plain else 400, json=body)

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if request.headers.get("authorization") != f"Bearer {KEY}":
            return self._error(403, "AccessDenied")
        prefix = "/storage/v1/object/archive/"
        assert request.url.path.startswith(prefix), request.url.path
        name = request.url.path[len(prefix) :]
        if request.method == "POST":
            if name in self.objects:
                return self._error(409, "KeyAlreadyExists")
            self.objects[name] = request.content
            return httpx.Response(200, json={"Key": f"archive/{name}"})
        if name not in self.objects:
            return self._error(404, "NoSuchKey")
        return httpx.Response(200, content=self.objects[name])


def archive(storage: Storage, key: str = KEY) -> SupabaseArchive:
    return SupabaseArchive("https://project.example", key, transport=httpx.MockTransport(storage))


@pytest.mark.parametrize("plain", [False, True])
def test_a_file_is_stored_under_its_hash_and_read_back(plain):
    storage = Storage(plain)
    store = archive(storage)
    assert store.put(SHA, BODY, "html") == PATH
    assert storage.objects == {PATH: BODY}
    assert store.get(PATH) == BODY
    sent = storage.requests[0]
    assert sent.headers["content-type"] == "text/html"
    assert "x-upsert" not in sent.headers  # a stored file is never written over


@pytest.mark.parametrize("plain", [False, True])
def test_storing_the_same_bytes_twice_is_fine(plain):
    storage = Storage(plain)
    store = archive(storage)
    assert store.put(SHA, BODY, "html") == store.put(SHA, BODY, "html") == PATH
    assert len(storage.objects) == 1


def test_the_same_path_as_a_folder_on_disk_gives(tmp_path):
    # A document's storage path means the same whichever store holds the file.
    assert LocalArchive(tmp_path).put(SHA, BODY, "html") == archive(Storage()).put(
        SHA, BODY, "html"
    )


def test_a_body_that_does_not_match_its_hash_is_not_sent():
    storage = Storage()
    with pytest.raises(ValueError, match="sha256"):
        archive(storage).put("0" * 64, BODY, "html")
    assert storage.requests == []


@pytest.mark.parametrize("plain", [False, True])
def test_a_missing_file_is_an_error_a_run_can_catch(plain):
    with pytest.raises(OSError, match="not in the archive"):
        archive(Storage(plain)).get(PATH)


def test_a_file_that_comes_back_changed_is_refused():
    storage = Storage()
    storage.objects[PATH] = b"<html>something else</html>"
    with pytest.raises(ArchiveError, match="does not match its hash"):
        archive(storage).get(PATH)


def test_a_refusal_is_reported_without_the_key():
    storage = Storage()
    with pytest.raises(ArchiveError) as caught:
        archive(storage, key="wrong-key-value").put(SHA, BODY, "html")
    assert "AccessDenied" in str(caught.value)
    assert "wrong-key-value" not in str(caught.value)


def test_the_store_is_chosen_from_the_settings(tmp_path):
    local = archive_from_env({"RADAR_ARCHIVE_DIR": str(tmp_path)})
    assert isinstance(local, LocalArchive)
    hosted = archive_from_env(
        {"RADAR_ARCHIVE_URL": "https://project.example", "RADAR_ARCHIVE_KEY": KEY}
    )
    assert isinstance(hosted, SupabaseArchive)
    with pytest.raises(NotConfigured, match="RADAR_ARCHIVE_DIR"):
        archive_from_env({})
    with pytest.raises(NotConfigured, match="both"):
        archive_from_env(
            {"RADAR_ARCHIVE_DIR": str(tmp_path), "RADAR_ARCHIVE_URL": "https://project.example",
             "RADAR_ARCHIVE_KEY": KEY}
        )  # fmt: skip
    with pytest.raises(NotConfigured, match="RADAR_ARCHIVE_KEY"):
        archive_from_env({"RADAR_ARCHIVE_URL": "https://project.example"})
    with pytest.raises(NotConfigured, match="https"):
        archive_from_env({"RADAR_ARCHIVE_URL": "http://project.example", "RADAR_ARCHIVE_KEY": KEY})


def test_the_key_is_never_in_what_the_store_says_of_itself():
    assert KEY not in repr(archive(Storage()))
    assert json.dumps(str(archive(Storage()))).count(KEY) == 0
