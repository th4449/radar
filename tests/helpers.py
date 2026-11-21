"""Test helpers: a fake clock, a recording HTTP transport and tiny PDF, slide deck, Word and
zip writers.

Nothing here touches the network. Synthetic documents made here test the library. Tests for a
real source use saved copies of that source's pages under tests/fixtures/<source-id>/.
"""

from __future__ import annotations

import datetime as dt
import io
import zipfile
from collections.abc import Callable
from xml.sax.saxutils import escape

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


# --- Office files and zip files -----------------------------------------------------------------

_A = "http://schemas.openxmlformats.org/drawingml/2006/main"
_P = "http://schemas.openxmlformats.org/presentationml/2006/main"
_R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
_RELS = "http://schemas.openxmlformats.org/package/2006/relationships"


def make_zip(files: dict[str, bytes]) -> bytes:
    """A zip file holding the given files, in the given order."""
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, body in files.items():
            archive.writestr(name, body)
    return out.getvalue()


def _shape(lines: list[str]) -> str:
    paragraphs = "".join(f"<a:p><a:r><a:t>{escape(line)}</a:t></a:r></a:p>" for line in lines)
    return f"<p:sp><p:txBody>{paragraphs}</p:txBody></p:sp>"


def _rels(entries: list[tuple[str, str, str]]) -> bytes:
    body = "".join(
        f'<Relationship Id="{rel_id}" Type="{_R}/{kind}" Target="{target}"/>'
        for rel_id, kind, target in entries
    )
    return f'<Relationships xmlns="{_RELS}">{body}</Relationships>'.encode()


def make_pptx(slides: list[str | tuple[str, str]], file_order: list[int] | None = None) -> bytes:
    """A minimal slide deck. Each slide is its text, or (text, speaker notes).

    Lines of text are separated by newlines. Every slide also carries a slide number field, as
    PowerPoint adds one. file_order gives the number in each slide's file name, to make a deck
    whose file names do not follow the presentation order.
    """
    numbers = file_order or list(range(1, len(slides) + 1))
    files: dict[str, bytes] = {
        "[Content_Types].xml": b'<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>'
    }
    ids, rels = "", []
    for position, (slide, number) in enumerate(zip(slides, numbers, strict=True), start=1):
        text, notes = slide if isinstance(slide, tuple) else (slide, None)
        field = f'<a:p><a:fld type="slidenum"><a:t>{position}</a:t></a:fld></a:p>'
        files[f"ppt/slides/slide{number}.xml"] = (
            f'<p:sld xmlns:a="{_A}" xmlns:p="{_P}"><p:cSld><p:spTree>'
            f"{_shape(text.split(chr(10))) if text else ''}"
            f"<p:sp><p:txBody>{field}</p:txBody></p:sp>"
            "</p:spTree></p:cSld></p:sld>"
        ).encode()
        if notes is not None:
            files[f"ppt/notesSlides/notesSlide{number}.xml"] = (
                f'<p:notes xmlns:a="{_A}" xmlns:p="{_P}"><p:cSld><p:spTree>'
                f"{_shape(notes.split(chr(10)))}</p:spTree></p:cSld></p:notes>"
            ).encode()
            files[f"ppt/slides/_rels/slide{number}.xml.rels"] = _rels(
                [("rId1", "notesSlide", f"../notesSlides/notesSlide{number}.xml")]
            )
        ids += f'<p:sldId id="{255 + position}" r:id="rId{position}"/>'
        rels.append((f"rId{position}", "slide", f"slides/slide{number}.xml"))
    files["ppt/presentation.xml"] = (
        f'<p:presentation xmlns:p="{_P}" xmlns:r="{_R}"><p:sldIdLst>{ids}</p:sldIdLst>'
        "</p:presentation>"
    ).encode()
    files["ppt/_rels/presentation.xml.rels"] = _rels(rels)
    return make_zip(files)


def make_docx(paragraphs: list[str]) -> bytes:
    """A minimal Word file with one run of text per paragraph."""
    body = "".join(f"<w:p><w:r><w:t>{escape(p)}</w:t></w:r></w:p>" for p in paragraphs)
    document = f'<w:document xmlns:w="{_W}"><w:body>{body}</w:body></w:document>'
    return make_zip({"[Content_Types].xml": b"<Types/>", "word/document.xml": document.encode()})


def make_portfolio(cover: str, files: dict[str, bytes]) -> bytes:
    """A PDF with other files embedded in it, the way TCEQ sends some applications."""
    import pypdfium2 as pdfium

    document = pdfium.PdfDocument(make_pdf([cover]))
    for name, body in files.items():
        document.new_attachment(name).set_data(body)
    out = io.BytesIO()
    document.save(out)
    document.close()
    return out.getvalue()


def make_scan(pages: list[str]) -> bytes:
    """A PDF of pictures of typed pages, with no text in the file, as a scanner makes one.

    Each string is one page. Lines are split on newlines. An empty string is a blank page.
    """
    from PIL import Image, ImageDraw, ImageFont

    font = ImageFont.load_default(size=44)
    images = []
    for text in pages:
        image = Image.new("L", (2550, 3300), 255)  # a letter page at 300 dots an inch
        draw = ImageDraw.Draw(image)
        for number, line in enumerate(text.splitlines()):
            draw.text((240, 260 + 76 * number), line, fill=0, font=font)
        images.append(image)
    out = io.BytesIO()
    images[0].save(out, format="PDF", resolution=300, save_all=True, append_images=images[1:])
    return out.getvalue()
