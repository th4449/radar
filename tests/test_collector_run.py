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
