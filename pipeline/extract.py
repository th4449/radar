"""Text extraction for HTML, PDF, slide decks, Word files and zip files.

The kind of a document is decided from its first bytes, not from the Content-Type header,
because servers often label PDFs and HTML wrongly.

A scanned PDF has no text layer. Where Tesseract is installed its pages are read by character
recognition, on this machine, and the result says so: `ocr` holds the engine, how many pages
it read and how sure it was. See pipeline/ocr.py. Where Tesseract is not installed, or it finds
no words, the file comes back with needs_ocr set and empty text. A file embedded in a PDF or
held in a zip is not read this way.

A slide deck (.pptx) gives the text of each slide in order, then that slide's speaker notes.
Text inside a picture or an embedded chart object is not read. A deck with slides and no text
at all comes back with needs_ocr set.

A PDF can carry other files inside it. TCEQ sends some applications as a "portfolio": a cover
page with the application and its spreadsheets embedded. The text of each embedded PDF, slide
deck or Word file is read and added under a line that names it. Embedded files are not opened
more than one level deep.

A zip file gives the text of each file inside it that can be read, under a line that names the
file. A zip inside a zip is not opened. Spreadsheets and the older binary Office formats are
recognized where possible and not read.
"""

from __future__ import annotations

import io
import posixpath
import re
import zipfile
from dataclasses import dataclass
from typing import Literal
from xml.etree.ElementTree import Element, ParseError

import pdfplumber
import pypdfium2 as pdfium
from defusedxml import DefusedXmlException
from defusedxml.ElementTree import fromstring as parse_xml
from selectolax.lexbor import LexborHTMLParser

from pipeline import ocr

Kind = Literal["html", "pdf", "text", "pptx", "docx", "xlsx", "zip", "unknown"]

# The file ending used when a document of each kind is stored.
SUFFIX: dict[str, str] = {
    "pdf": "pdf",
    "html": "html",
    "text": "txt",
    "pptx": "pptx",
    "docx": "docx",
    "xlsx": "xlsx",
    "zip": "zip",
    "unknown": "bin",
}

# Limits for reading inside a zip container. They stop a small file that unpacks to a huge one.
MAX_MEMBER_BYTES = 200 * 1024 * 1024
MAX_TOTAL_BYTES = 600 * 1024 * 1024
MAX_MEMBERS_READ = 200
MAX_SLIDES = 2000

_DROP_TAGS = ["script", "style", "noscript", "template", "svg", "iframe", "head"]
_HTML_START = re.compile(rb"^\s*(<!doctype\s+html|<html|<head|<body|<\?xml)", re.IGNORECASE)
_SPACES = re.compile(r"[ \t\r\f\v ]+")


@dataclass(frozen=True)
class Extracted:
    kind: Kind
    text: str
    pages: int | None = None
    title: str | None = None
    needs_ocr: bool = False
    # For a zip file: one entry per file inside, read or not.
    members: tuple[dict, ...] = ()
    # Set when the text was read from a scan by character recognition. See pipeline/ocr.py.
    ocr: dict | None = None


def _zip_kind(body: bytes) -> Kind:
    try:
        with zipfile.ZipFile(io.BytesIO(body)) as archive:
            names = set(archive.namelist())
    except (zipfile.BadZipFile, OSError, ValueError):
        return "unknown"
    if "[Content_Types].xml" in names:
        if "ppt/presentation.xml" in names:
            return "pptx"
        if "word/document.xml" in names:
            return "docx"
        if "xl/workbook.xml" in names:
            return "xlsx"
    return "zip"


def sniff(body: bytes, content_type: str | None = None) -> Kind:
    head = body[:2048]
    if head.lstrip().startswith(b"%PDF-"):
        return "pdf"
    if head.startswith(b"PK\x03\x04"):
        return _zip_kind(body)
    if _HTML_START.match(head) or b"<html" in head.lower():
        return "html"
    ctype = (content_type or "").split(";")[0].strip().lower()
    if ctype in ("text/html", "application/xhtml+xml"):
        return "html"
    if ctype == "application/pdf":
        return "unknown"  # labeled PDF but does not start like one
    if ctype.startswith("text/") or ctype in ("application/json", "application/xml"):
        return "text"
    if b"\x00" not in head:
        try:
            head.decode("utf-8")
        except UnicodeDecodeError:
            return "unknown"
        return "text"
    return "unknown"


def _tidy(text: str) -> str:
    # A PDF's text layer can hold NUL characters. The database refuses them.
    text = text.replace("\x00", "")
    lines = (_SPACES.sub(" ", line).strip() for line in text.splitlines())
    return "\n".join(line for line in lines if line)


def _html(body: bytes) -> Extracted:
    tree = LexborHTMLParser(body)
    title_node = tree.css_first("title")
    title = _tidy(title_node.text()) if title_node else None
    tree.strip_tags(_DROP_TAGS)
    root = tree.body or tree.root
    text = _tidy(root.text(separator="\n")) if root else ""
    return Extracted("html", text, title=title or None)


def _pdf_pages(body: bytes) -> list[str]:
    pages: list[str] = []
    with pdfplumber.open(io.BytesIO(body)) as pdf:
        for page in pdf.pages:
            pages.append(_tidy(page.extract_text() or ""))
            page.close()  # a long file would otherwise hold every page's layout in memory
    return pages


def _pdf_attachments(body: bytes) -> list[tuple[str, bytes]]:
    """Files embedded in a PDF. A "PDF portfolio" is a cover page with the real files inside."""
    try:
        document = pdfium.PdfDocument(body)
    except pdfium.PdfiumError:
        return []
    try:
        found = []
        for index in range(min(document.count_attachments(), MAX_MEMBERS_READ + 1)):
            attachment = document.get_attachment(index)
            name = (attachment.get_name() or "").replace("\x00", "").strip()
            found.append((name or f"attachment {index + 1}", bytes(attachment.get_data())))
        return found
    except (pdfium.PdfiumError, ValueError):
        return []
    finally:
        document.close()


def _pdf(body: bytes, inside: bool = False) -> Extracted:
    pages = _pdf_pages(body)
    text = "\n\n".join(p for p in pages if p)
    if inside:  # an embedded file's own embedded files are not opened
        return Extracted("pdf", text, pages=len(pages), needs_ocr=bool(pages) and not text)

    members: list[dict] = []
    parts = [text] if text else []
    total = 0
    for name, data in _pdf_attachments(body):
        entry = {"name": name, "bytes": len(data), "read": False}
        members.append(entry)
        total += len(data)
        if len(members) > MAX_MEMBERS_READ or total > MAX_TOTAL_BYTES:
            entry["why"] = "too many files or too much data in this file"
            continue
        if len(data) > MAX_MEMBER_BYTES:
            entry["why"] = "too large to read"
            continue
        kind = sniff(data)
        entry["kind"] = kind
        try:
            if kind == "pdf":
                inner = _pdf(data, inside=True)
            elif kind in ("pptx", "docx"):
                inner = _pptx(data) if kind == "pptx" else _docx(data)
            else:
                entry["why"] = "this kind of file is not read"
                continue
        except Exception as exc:  # noqa: BLE001 - a damaged embedded file must not stop the rest
            entry["why"] = f"could not be read: {type(exc).__name__}"
            continue
        entry |= {"read": True, "pages": inner.pages, "needs_ocr": inner.needs_ocr}
        if inner.text:
            parts.append(f"File: {name}\n{inner.text}")
    text = "\n\n".join(parts)
    # Some scans are files whose pages the text reader cannot find at all. The page drawer can.
    count = len(pages) or (0 if text else _page_count(body))
    read = _scan(body) if count and not text else None
    if read is not None:
        text = "\n\n".join(_tidy(page) for page in read.pages if page.strip())
    return Extracted(
        "pdf", text, pages=count, needs_ocr=bool(count) and not text,
        members=tuple(members), ocr=read.facts() if read is not None and text else None,
    )  # fmt: skip


def _page_count(body: bytes) -> int:
    """How many pages the page drawer finds in a PDF. 0 when it cannot open the file."""
    try:
        document = pdfium.PdfDocument(body)
    except pdfium.PdfiumError:
        return 0
    try:
        return len(document)
    finally:
        document.close()


def _scan(body: bytes) -> ocr.OcrResult | None:
    """A scan's pages as Tesseract reads them. None where it is not installed or cannot run:
    the file is then stored unread and marked as needing it."""
    if not ocr.available():
        return None
    try:
        return ocr.read_pdf(body)
    except ocr.OcrFailed:
        return None


# --- Office files and zip files -----------------------------------------------------------------


class _Unreadable(Exception):
    """A file inside a container that will not be read."""


def _member(archive: zipfile.ZipFile, name: str) -> bytes:
    info = archive.getinfo(name)
    if info.file_size > MAX_MEMBER_BYTES:
        raise _Unreadable(f"{name} unpacks to more than {MAX_MEMBER_BYTES} bytes")
    with archive.open(info) as handle:
        data = handle.read(MAX_MEMBER_BYTES + 1)
    if len(data) > MAX_MEMBER_BYTES:
        raise _Unreadable(f"{name} unpacks to more than {MAX_MEMBER_BYTES} bytes")
    return data


def _xml(data: bytes) -> Element:
    # Office files declare no document type. One that does is not read.
    if b"<!DOCTYPE" in data or b"<!ENTITY" in data:
        raise _Unreadable("the XML declares a document type")
    try:
        return parse_xml(data, forbid_dtd=True)
    except (ParseError, DefusedXmlException) as exc:
        raise _Unreadable(f"the XML does not parse or is not safe to parse: {exc}") from exc


def _local(tag: object) -> str:
    return tag.rsplit("}", 1)[-1] if isinstance(tag, str) else ""


def _paragraphs(root: Element) -> list[str]:
    """The text of each paragraph, in document order.

    Slides and Word files both mark a paragraph as "p", a run of text as "t", a line break as
    "br" and a tab as "tab". The slide number, which PowerPoint fills in itself, is left out.
    """
    lines: list[str] = []

    def walk(node: Element, buffer: list[str]) -> None:
        for child in node:
            name = _local(child.tag)
            if name == "p":
                inner: list[str] = []
                walk(child, inner)
                lines.append("".join(inner))
            elif name == "t":
                buffer.append(child.text or "")
            elif name == "br":
                buffer.append("\n")
            elif name == "tab":
                buffer.append("\t")
            elif name == "fld" and child.get("type", "").startswith("slidenum"):
                continue
            else:
                walk(child, buffer)

    loose: list[str] = []
    walk(root, loose)
    lines.append("".join(loose))
    return [line for line in (_tidy(line) for line in lines) if line]


def _relationships(archive: zipfile.ZipFile, part: str) -> list[tuple[str, str, str]]:
    """(id, type, target path) for each relationship of a part. Empty if it has none."""
    folder, name = posixpath.split(part)
    rels = posixpath.join(folder, "_rels", name + ".rels")
    if rels not in archive.namelist():
        return []
    out = []
    for rel in _xml(_member(archive, rels)):
        if rel.get("TargetMode") == "External":
            continue
        target = rel.get("Target", "")
        path = target.lstrip("/") if target.startswith("/") else posixpath.join(folder, target)
        out.append((rel.get("Id", ""), rel.get("Type", ""), posixpath.normpath(path)))
    return out


def _slide_order(archive: zipfile.ZipFile) -> list[str]:
    """Slide parts in presentation order. The file names alone do not give the order."""
    names = set(archive.namelist())
    by_id = {
        rel_id: path
        for rel_id, kind, path in _relationships(archive, "ppt/presentation.xml")
        if kind.endswith("/slide")
    }
    ordered: list[str] = []
    for node in _xml(_member(archive, "ppt/presentation.xml")).iter():
        if _local(node.tag) != "sldId":
            continue
        rel_id = next((v for k, v in node.attrib.items() if _local(k) == "id" and "}" in k), None)
        if rel_id in by_id and by_id[rel_id] in names:
            ordered.append(by_id[rel_id])
    if ordered:
        return ordered

    def number(name: str) -> int:
        digits = re.sub(r"\D", "", posixpath.basename(name))
        return int(digits) if digits else 0

    return sorted((n for n in names if re.fullmatch(r"ppt/slides/slide\d+\.xml", n)), key=number)


def _pptx(body: bytes) -> Extracted:
    with zipfile.ZipFile(io.BytesIO(body)) as archive:
        slides = _slide_order(archive)
        if len(slides) > MAX_SLIDES:
            raise _Unreadable(f"more than {MAX_SLIDES} slides")
        pages: list[str] = []
        for part in slides:
            lines = _paragraphs(_xml(_member(archive, part)))
            for _id, kind, notes in _relationships(archive, part):
                if kind.endswith("/notesSlide") and notes in archive.namelist():
                    said = _paragraphs(_xml(_member(archive, notes)))
                    if said:
                        lines += ["Notes:", *said]
            pages.append("\n".join(lines))
    text = "\n\n".join(page for page in pages if page)
    return Extracted("pptx", text, pages=len(pages), needs_ocr=bool(pages) and not text)


def _docx(body: bytes) -> Extracted:
    with zipfile.ZipFile(io.BytesIO(body)) as archive:
        lines = _paragraphs(_xml(_member(archive, "word/document.xml")))
    return Extracted("docx", "\n".join(lines))


def _zip(body: bytes) -> Extracted:
    """The text of each readable file inside, under a line that names it."""
    parts: list[str] = []
    members: list[dict] = []
    total = 0
    with zipfile.ZipFile(io.BytesIO(body)) as archive:
        for info in archive.infolist():
            name = info.filename
            if (
                info.is_dir()
                or name.startswith("__MACOSX/")
                or posixpath.basename(name)[:1]
                in (
                    ".",
                    "~",
                )
            ):
                continue
            entry: dict = {"name": name, "bytes": info.file_size, "read": False}
            members.append(entry)
            total += info.file_size
            if len(members) > MAX_MEMBERS_READ or total > MAX_TOTAL_BYTES:
                entry["why"] = "past the limit for one zip file"
                continue
            try:
                inner = _extract(_member(archive, name), None, inside_zip=True)
            except _Unreadable as exc:
                entry["why"] = str(exc)
                continue
            entry.update(kind=inner.kind, pages=inner.pages, needs_ocr=inner.needs_ocr)
            if inner.kind in ("zip", "xlsx", "unknown"):
                entry["why"] = "this kind of file is not read"
                continue
            entry["read"] = True
            if inner.text:
                parts.append(f"File: {name}\n{inner.text}")
    return Extracted(
        "zip",
        "\n\n".join(parts),
        needs_ocr=any(m.get("needs_ocr") for m in members),
        members=tuple(members),
    )


def _extract(body: bytes, content_type: str | None, inside_zip: bool) -> Extracted:
    kind = sniff(body, content_type)
    if kind == "pdf":
        return _pdf(body)
    if kind == "html":
        return _html(body)
    if kind == "text":
        return Extracted("text", _tidy(body.decode("utf-8", errors="replace")))
    try:
        if kind == "pptx":
            return _pptx(body)
        if kind == "docx":
            return _docx(body)
        if kind == "zip" and not inside_zip:
            return _zip(body)
    except (_Unreadable, zipfile.BadZipFile, KeyError, OSError, ValueError, RuntimeError):
        # A damaged or unusual file is kept and stored. It just yields no text.
        return Extracted(kind, "")
    return Extracted(kind, "")


def extract(body: bytes, content_type: str | None = None) -> Extracted:
    return _extract(body, content_type, inside_zip=False)
