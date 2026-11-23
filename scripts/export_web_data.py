"""Write the places and sources the public site shows, from the files in config/.

    uv run python scripts/export_web_data.py

The site is built without Python, so it reads web/src/lib/places.json. That file is a copy.
config/ is the record. tests/test_web_data.py fails when the copy is out of date.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from pipeline.config import load_counties, load_sources  # noqa: E402

OUT = REPO / "web" / "src" / "lib" / "places.json"
STATES = (("TX", "Texas"), ("MI", "Michigan"))


def slug(name: str) -> str:
    """ "St. Clair" -> "st-clair". Used in page addresses, so it must never change for a name."""
    return re.sub(r"[^a-z0-9]+", "-", name.lower().replace(".", "").replace("'", "")).strip("-")


def build() -> dict:
    states = []
    for code, name in STATES:
        counties = sorted(load_counties(code).counties, key=lambda c: c.name)
        slugs = [slug(c.name) for c in counties]
        if len(set(slugs)) != len(slugs):
            raise ValueError(f"two {name} counties share a page address")
        states.append(
            {
                "code": code,
                "name": name,
                "slug": code.lower(),
                "counties": [
                    {"fips": c.fips, "name": c.name, "slug": slug(c.name)} for c in counties
                ],
            }
        )
    # Record sources only: no trackers kept as baselines by hand, no lookup services.
    sources = [
        {
            "name": s.name,
            "state": s.state,
            "url": str(s.url),
            "read": s.may_fetch_automatically or s.hand_saved or s.hand_entered,
            # A person saves the page or the record in a browser. No program asks the site.
            "by_hand": s.hand_saved or s.hand_entered,
            "use": s.layer,
        }
        for s in load_sources().sources
        if s.layer == "signal"
        or ((s.may_fetch_automatically or s.hand_saved or s.hand_entered) and s.layer != "lookup")
    ]
    return {"states": states, "sources": sources}


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(build(), indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUT.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
