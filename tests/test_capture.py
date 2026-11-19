"""The by-hand fixture tool obeys the same rules as the collectors."""

from __future__ import annotations

import hashlib
import json

import httpx
import pytest

from collectors.base import Blocked, NotPermitted, RobotsDisallowed
from collectors.capture import _default_name, capture, main

from .helpers import CONTACT, FakeClock, Site, make_pdf, make_source

URL = "https://records.example.gov/taxes/Data-Center_Lists.php"
BODY = b"<!DOCTYPE html><html><body><h1>Registered data centers</h1></body></html>"


def run(site: Site, tmp_path, source=None, **kwargs):
    clock = FakeClock()
    return capture(
        source or make_source(method="manual"),
        kwargs.pop("url", URL),
        fixtures_dir=tmp_path,
        contact=CONTACT,
        transport=site.transport,
        clock=clock,
        sleep=clock.sleep,
        **kwargs,
    )


def test_saves_the_bytes_and_a_metadata_file(tmp_path):
    site = Site({URL: httpx.Response(200, content=BODY, headers={"Content-Type": "text/html"})})
    target = run(site, tmp_path)

    assert target == tmp_path / "tx_example" / "data-center-lists.html"
    assert target.read_bytes() == BODY
    meta = json.loads((tmp_path / "tx_example" / "data-center-lists.meta.json").read_text())
    assert meta["url"] == URL
    assert meta["sha256"] == hashlib.sha256(BODY).hexdigest()
    assert meta["bytes"] == len(BODY)
    assert meta["kind"] == "html"
    assert meta["retrieved_at"].endswith("+00:00")
    assert site.page_urls() == [URL]  # exactly one request for the page


def test_a_pdf_gets_a_pdf_extension(tmp_path):
    url = "https://records.example.gov/files/Pending.PDF"
    site = Site({url: httpx.Response(200, content=make_pdf(["Pending permits"]))})
    assert run(site, tmp_path, url=url).name == "pending.pdf"


def test_does_not_overwrite_without_force(tmp_path):
    site = Site({URL: httpx.Response(200, content=BODY)})
    run(site, tmp_path)
    with pytest.raises(FileExistsError):
        run(site, tmp_path)
    assert len(site.page_urls()) == 1  # the second attempt made no request
    run(site, tmp_path, force=True)


def test_refuses_a_source_without_a_note_or_with_a_restriction(tmp_path):
    site = Site({URL: httpx.Response(200, content=BODY)})
    unverified = make_source(method="manual", robots_status="not_checked", verified_at=None)
    restricted = make_source(method="manual", robots_status="restricted")
    for source in (unverified, restricted):
        with pytest.raises(NotPermitted):
            run(site, tmp_path, source=source)
    assert site.requests == []
    assert not (tmp_path / "tx_example").exists()


def test_robots_and_refusals_still_apply(tmp_path):
    closed = Site({URL: httpx.Response(200, content=BODY)}, robots="User-agent: *\nDisallow: /")
    with pytest.raises(RobotsDisallowed):
        run(closed, tmp_path)
    refused = Site({URL: httpx.Response(403)})
    with pytest.raises(Blocked):
        run(refused, tmp_path)
    assert not (tmp_path / "tx_example").exists()


def test_needs_a_contact_address(tmp_path, monkeypatch):
    monkeypatch.delenv("RADAR_CONTACT", raising=False)
    site = Site({URL: httpx.Response(200, content=BODY)})
    with pytest.raises(NotPermitted):
        capture(make_source(), URL, fixtures_dir=tmp_path, transport=site.transport)
    assert site.requests == []


@pytest.mark.parametrize(
    "url,name",
    [
        ("https://x.example/taxes/data-centers/data-center-lists.php", "data-center-lists"),
        ("https://x.example/files/NSR_PTIs Pending.pdf", "nsr-ptis-pending"),
        ("https://x.example/", "index"),
        ("https://x.example/economy/search-tools/sb1340/", "sb1340"),
    ],
)
def test_default_names(url, name):
    assert _default_name(url) == name


def test_command_line_reports_an_unknown_source(capsys):
    assert main(["tx_no_such_source", URL]) == 2
    assert "no source with id" in capsys.readouterr().err


def test_command_line_refuses_an_unverified_source(capsys, monkeypatch):
    monkeypatch.setenv("RADAR_CONTACT", CONTACT)
    # tx_public_notices has no source note yet, so nothing is fetched.
    assert main(["tx_public_notices", "https://www.texaspublicnotices.com/"]) == 1
    assert "not saved" in capsys.readouterr().err
