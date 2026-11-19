"""Test helpers: a fake clock, a recording HTTP transport and a tiny PDF writer.

Nothing here touches the network. Synthetic documents made here test the library. Tests for a
real source use saved copies of that source's pages under tests/fixtures/<source-id>/.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Callable

import httpx

from pipeline.config import Source

CONTACT = "radar-tests@example.org"


def make_source(**overrides) -> Source:
    data = dict(
        id="tx_example",
        state="TX",
        name="Example agency notices",
        url="https://records.example.gov/notices",
        layer="signal",
        method="http",
        intended_method="http",
        cadence="daily",
        robots_status="allowed",
        verified_at=dt.date(2026, 11, 19),
        notes="",
    )
    data.update(overrides)
    return Source(**data)


class FakeClock:
    """Time that moves only when something sleeps."""

    def __init__(self) -> None:
        self.now = 1000.0
        self.sleeps: list[float] = []

    def __call__(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


class Site:
    """A fake web. Routes map a URL to a response or to a function of the request."""

    def __init__(self, routes: dict | None = None, robots: str | int | None = "") -> None:
        self.routes: dict[str, object] = dict(routes or {})
        self.robots = robots
        self.requests: list[httpx.Request] = []

    def urls(self) -> list[str]:
        return [str(r.url) for r in self.requests]

    def page_urls(self) -> list[str]:
        return [u for u in self.urls() if not u.endswith("/robots.txt")]

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        url = str(request.url)
        if url in self.routes:
            route = self.routes[url]
            if isinstance(route, list):  # a scripted sequence of responses
                route = route.pop(0) if len(route) > 1 else route[0]
            if isinstance(route, Callable):
                return route(request)
            return route
        if request.url.path == "/robots.txt":
            if isinstance(self.robots, int):
                return httpx.Response(self.robots)
            if self.robots is None:
                return httpx.Response(404)
            return httpx.Response(200, text=self.robots)
        return httpx.Response(404)

    @property
    def transport(self) -> httpx.MockTransport:
        return httpx.MockTransport(self.handler)


def make_pdf(pages: list[str]) -> bytes:
    """A minimal, valid PDF with one text block per page. An empty string makes a blank page."""
    objects: list[bytes] = []
    kids = " ".join(f"{4 + 2 * i} 0 R" for i in range(len(pages)))
    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    objects.append(f"<< /Type /Pages /Kids [{kids}] /Count {len(pages)} >>".encode())
    objects.append(
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>"
    )
    for i, text in enumerate(pages):
        ops: list[str] = []
        if text:
            ops = ["BT", "/F1 12 Tf", "72 720 Td", "14 TL"]
            for line in text.split("\n"):
                escaped = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
                ops.append(f"({escaped}) Tj T*")
            ops.append("ET")
        stream = "\n".join(ops).encode("latin-1")
        objects.append(
            (
                "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
                f"/Resources << /Font << /F1 3 0 R >> >> /Contents {5 + 2 * i} 0 R >>"
            ).encode()
        )
        objects.append(b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream")

    out = bytearray(b"%PDF-1.4\n")
    offsets: list[int] = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{number} 0 obj\n".encode() + body + b"\nendobj\n"
    xref_at = len(out)
    out += f"xref\n0 {len(objects) + 1}\n".encode() + b"0000000000 65535 f \n"
    for offset in offsets:
        out += f"{offset:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n".encode()
    out += f"startxref\n{xref_at}\n%%EOF\n".encode()
    return bytes(out)
