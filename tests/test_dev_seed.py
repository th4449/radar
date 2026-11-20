"""The local demo-data script refuses any database that is not on this computer."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "dev_seed.py"


def load():
    spec = importlib.util.spec_from_file_location("dev_seed", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    "url",
    [
        "postgresql://postgres:x@db.example.supabase.co:5432/postgres",
        "postgresql://postgres:x@10.0.0.5:5432/postgres",
        "postgresql://postgres:x@127.0.0.1.example.org:5432/postgres",
    ],
)
def test_it_refuses_a_database_elsewhere(monkeypatch, capsys, url):
    monkeypatch.setenv("DATABASE_URL", url)
    assert load().main() == 2
    assert "only fills a database on this computer" in capsys.readouterr().err
