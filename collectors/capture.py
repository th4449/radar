"""Save one real page as a test fixture. Run by a person, one URL at a time.

    export RADAR_CONTACT="<the project's public contact address>"
    uv run python -m collectors.capture tx_comptroller_data_centers \\
        https://comptroller.texas.gov/taxes/data-centers/data-center-lists.php

It makes a single request through the same fetcher the collectors use, so every rule holds:
the source needs a source note, robots.txt is checked, and a refusal is final.

The file lands in tests/fixtures/<source-id>/ next to a .meta.json that records the URL,
retrieval time and SHA-256 hash. Fixtures are committed to a public repository. Read the saved
file before committing it, and do not commit a page that names private individuals.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit

import httpx

from collectors.base import Fetcher, FetchError, sha256_hex
from pipeline.config import Source, load_sources
from pipeline.extract import SUFFIX, sniff

FIXTURES = Path(__file__).resolve().parent.parent / "tests" / "fixtures"


def _default_name(url: str) -> str:
    path = urlsplit(url).path.rstrip("/")
    stem = Path(path).stem if path else "index"
    return re.sub(r"[^a-z0-9]+", "-", stem.lower()).strip("-") or "index"


def capture(
    source: Source,
    url: str,
    *,
    fixtures_dir: Path = FIXTURES,
    name: str | None = None,
    force: bool = False,
    contact: str | None = None,
    transport: httpx.BaseTransport | None = None,
    **fetcher_kwargs,
) -> Path:
    """Fetch url once by hand and save it. Returns the path of the saved file."""
    name = name or _default_name(url)
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", name):
        raise ValueError("name must be lowercase letters, digits and hyphens")
    out_dir = fixtures_dir / source.id
    existing = list(out_dir.glob(f"{name}.*")) if out_dir.exists() else []
    if existing and not force:
        raise FileExistsError(f"{existing[0]} exists. Pass --force to replace it.")

    with Fetcher(
        source, by_hand=True, contact=contact, transport=transport, **fetcher_kwargs
    ) as fetcher:
        result = fetcher.get(url)

    kind = sniff(result.body, result.content_type)
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in existing:
        old.unlink()
    target = out_dir / f"{name}.{SUFFIX[kind]}"
    target.write_bytes(result.body)
    meta = {
        "source_id": source.id,
        "url": result.url,
        "final_url": result.final_url,
        "retrieved_at": result.retrieved_at.isoformat(timespec="seconds"),
        "sha256": sha256_hex(result.body),
        "bytes": len(result.body),
        "content_type": result.content_type,
        "etag": result.etag,
        "last_modified": result.last_modified,
        "kind": kind,
    }
    (out_dir / f"{name}.meta.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Save one real page as a test fixture.")
    parser.add_argument("source_id", help="the id in config/sources.yaml")
    parser.add_argument("url")
    parser.add_argument("--name", help="file name without extension")
    parser.add_argument("--force", action="store_true", help="replace an existing fixture")
    args = parser.parse_args(argv)

    try:
        source = load_sources().by_id(args.source_id)
    except KeyError:
        print(f"no source with id {args.source_id} in config/sources.yaml", file=sys.stderr)
        return 2
    try:
        target = capture(source, args.url, name=args.name, force=args.force)
    except (FetchError, FileExistsError, ValueError) as exc:
        print(f"not saved: {exc}", file=sys.stderr)
        return 1
    print(f"saved {target}")
    print("Read the file before committing it. Fixtures are public.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
