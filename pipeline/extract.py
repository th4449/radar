"""Text extraction for HTML and PDF.

The kind of a document is decided from its first bytes, not from the Content-Type header,
because servers often label PDFs and HTML wrongly.

Scanned PDFs have no text layer. They come back with needs_ocr set and empty text. Character
recognition is milestone M8 work.
"""

from __future__ import annotations

import io
import re
from dataclasses import dataclass
from typing import Literal

import pdfplumber
from selectolax.lexbor import LexborHTMLParser

Kind = Literal["html", "pdf", "text", "unknown"]

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


def sniff(body: bytes, content_type: str | None = None) -> Kind:
    head = body[:2048]
    if head.lstrip().startswith(b"%PDF-"):
        return "pdf"
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


def _pdf(body: bytes) -> Extracted:
    with pdfplumber.open(io.BytesIO(body)) as pdf:
        pages = [_tidy(page.extract_text() or "") for page in pdf.pages]
    text = "\n\n".join(p for p in pages if p)
    return Extracted("pdf", text, pages=len(pages), needs_ocr=bool(pages) and not text)


def extract(body: bytes, content_type: str | None = None) -> Extracted:
    kind = sniff(body, content_type)
    if kind == "pdf":
        return _pdf(body)
    if kind == "html":
        return _html(body)
    if kind == "text":
        return Extracted("text", _tidy(body.decode("utf-8", errors="replace")))
    return Extracted("unknown", "")
