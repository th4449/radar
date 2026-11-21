"""The site's copy of the places and sources matches config/."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location(
    "export_web_data", REPO / "scripts/export_web_data.py"
)
export = importlib.util.module_from_spec(spec)
spec.loader.exec_module(export)


def test_the_sites_copy_is_current():
    assert json.loads(export.OUT.read_text(encoding="utf-8")) == export.build(), (
        "run: uv run python scripts/export_web_data.py"
    )


def test_every_county_has_its_own_page_address():
    data = export.build()
    assert [len(s["counties"]) for s in data["states"]] == [30, 83]
    for state in data["states"]:
        slugs = [c["slug"] for c in state["counties"]]
        assert len(set(slugs)) == len(slugs)
        assert all(s and s == s.lower() and " " not in s for s in slugs)
    assert export.slug("St. Clair") == "st-clair"
    assert export.slug("Tom Green") == "tom-green"


def test_the_site_never_lists_a_source_as_read_that_may_not_be_fetched():
    data = export.build()
    read = {s["name"] for s in data["sources"] if s["read"]}
    assert "TCEQ pending air permit lists on the older site" in read
    assert "Texas newspaper public notices, including 30 day tax abatement notices" not in read
    assert not [s for s in data["sources"] if s["state"] == "MI" and s["read"]]
