"""The helper that stores a hand-saved page in the hosted project. Written before the helper.

`collectors.by_hand` needs the hosted database's address and the archive's key. Both are
secrets that live on GitHub and on no person's machine. The helper puts them together for one
command, in memory only: the database password from a prompt that shows nothing, the key
from Supabase's own tool. It prints neither and writes neither to a file.

No test here touches a database, Supabase's tool or the network. Every value is made up.
"""

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path

import pytest

from .test_tx_comptroller_data_centers import BODY

REPO = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("hosted", REPO / "scripts/store_by_hand_hosted.py")
hosted = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hosted)

REF = "abcdefghijklmnopqrst"
POOLER = f"postgresql://postgres.{REF}@aws-0-us-east-1.pooler.example.test:5432/postgres"
PASSWORD = "made-up-pass-1"
KEY = "made-up-service-value"
LISTING = json.dumps(
    [
        {"name": "anon", "type": "legacy", "api_key": "made-up-public-value"},
        {"name": "service_role", "type": "legacy", "api_key": KEY},
        {"name": "default", "type": "secret", "api_key": "sb_secret_abc····"},
    ]
)
SOURCE = "tx_comptroller_data_centers"
SETTINGS = ("DATABASE_URL", "RADAR_ARCHIVE_URL", "RADAR_ARCHIVE_KEY")


def linked(tmp_path: Path) -> Path:
    temp = tmp_path / "supabase-temp"
    temp.mkdir(exist_ok=True)
    (temp / "project-ref").write_text(REF + "\n")
    (temp / "pooler-url").write_text(POOLER + "\n")
    return temp


def saved(tmp_path: Path, body: bytes = BODY) -> Path:
    path = tmp_path / "data-center-lists.html"
    path.write_bytes(body)
    return path


class Calls:
    """Stands in for the prompt, Supabase's tool, the database and the storing command."""

    def __init__(self, *, password: str = PASSWORD, refusal: str | None = None, code: int = 0):
        self.password, self.refusal, self.code = password, refusal, code
        self.asked = 0
        self.connected: list[str] = []
        self.keys_for: list[str] = []
        self.stored: list[tuple[list[str], dict[str, str | None]]] = []

    def ask(self, prompt: str) -> str:
        self.asked += 1
        return self.password

    def keys(self, ref: str) -> str:
        self.keys_for.append(ref)
        return LISTING

    def connect(self, url: str) -> str | None:
        self.connected.append(url)
        return self.refusal

    def store(self, argv: list[str]) -> int:
        names = (*SETTINGS, "RADAR_ARCHIVE_DIR")
        self.stored.append((argv, {name: os.environ.get(name) for name in names}))
        return self.code

    def run(self, tmp_path: Path, argv: list[str]) -> int:
        return hosted.main(
            argv,
            ask=self.ask,
            keys=self.keys,
            connect=self.connect,
            store=self.store,
            temp=linked(tmp_path),
        )


def test_the_address_carries_the_password_encoded_and_asks_for_encryption():
    url = hosted.database_url(POOLER, "p@ss:w/rd 1")

    assert url == (
        f"postgresql://postgres.{REF}:p%40ss%3Aw%2Frd%201"
        "@aws-0-us-east-1.pooler.example.test:5432/postgres?sslmode=require"
    )


def test_a_password_already_in_the_saved_address_is_not_used():
    old = POOLER.replace(f"postgres.{REF}@", f"postgres.{REF}:old-one@")

    assert "old-one" not in hosted.database_url(old, PASSWORD)


def test_a_checkout_that_is_not_linked_cannot_start(tmp_path):
    with pytest.raises(hosted.CannotStart, match="supabase link"):
        hosted.linked_project(tmp_path / "nothing-here")


def test_the_service_key_is_taken_from_the_listing():
    assert hosted.service_key(LISTING) == KEY


@pytest.mark.parametrize(
    "listing",
    [
        json.dumps([{"name": "anon", "type": "legacy", "api_key": "x"}]),
        json.dumps([{"name": "service_role", "type": "legacy", "api_key": "hidden···"}]),
        json.dumps([{"name": "service_role", "type": "legacy", "api_key": ""}]),
        "not json",
    ],
)
def test_a_listing_with_no_usable_service_key_cannot_start(listing):
    with pytest.raises(hosted.CannotStart):
        hosted.service_key(listing)


def test_a_file_that_is_not_the_page_is_refused_before_any_secret_is_asked_for(tmp_path, capsys):
    calls = Calls()

    code = calls.run(tmp_path, [SOURCE, str(saved(tmp_path, b"<html>Access Denied</html>"))])

    assert code == 1
    assert (calls.asked, calls.keys_for, calls.connected, calls.stored) == (0, [], [], [])
    assert "not stored" in capsys.readouterr().err


def test_the_page_is_stored_with_the_settings_held_in_memory_only(tmp_path, monkeypatch, capsys):
    for name in SETTINGS:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("RADAR_ARCHIVE_DIR", "/a/local/folder")
    calls = Calls()
    path = saved(tmp_path)

    code = calls.run(tmp_path, [SOURCE, str(path), "--saved-at", "2026-11-24T15:30:00-06:00"])

    assert code == 0
    ((argv, during),) = calls.stored
    assert argv == [SOURCE, str(path), "--saved-at", "2026-11-24T15:30:00-06:00"]
    assert during["DATABASE_URL"] == hosted.database_url(POOLER, PASSWORD)
    assert during["RADAR_ARCHIVE_URL"] == f"https://{REF}.supabase.co"
    assert during["RADAR_ARCHIVE_KEY"] == KEY
    assert during["RADAR_ARCHIVE_DIR"] is None  # a local folder would make two archives
    assert calls.connected == [hosted.database_url(POOLER, PASSWORD)]
    assert calls.keys_for == [REF]
    # afterwards the shell's settings are as they were
    assert [os.environ.get(name) for name in SETTINGS] == [None, None, None]
    assert os.environ["RADAR_ARCHIVE_DIR"] == "/a/local/folder"
    said = capsys.readouterr()
    for secret in (PASSWORD, KEY, REF):
        assert secret not in said.out + said.err


def test_the_settings_are_put_back_even_when_storing_fails(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://the-local-one")
    calls = Calls()

    def fails(argv):
        raise RuntimeError("the storage service failed")

    with pytest.raises(RuntimeError):
        hosted.main(
            [SOURCE, str(saved(tmp_path))],
            ask=calls.ask,
            keys=calls.keys,
            connect=calls.connect,
            store=fails,
            temp=linked(tmp_path),
        )

    assert os.environ["DATABASE_URL"] == "postgresql://the-local-one"
    assert "RADAR_ARCHIVE_KEY" not in os.environ


@pytest.mark.parametrize("password", ["", "   ", "\x1b[200~pasted\x1b[201~", "café-pass"])
def test_an_empty_or_garbled_password_stores_nothing(tmp_path, password, capsys):
    calls = Calls(password=password)

    code = calls.run(tmp_path, [SOURCE, str(saved(tmp_path))])

    assert code == 2
    assert (calls.connected, calls.stored) == ([], [])
    assert "Nothing was stored" in capsys.readouterr().out


def test_a_refused_password_stores_nothing_and_is_never_printed(tmp_path, capsys):
    refusal = f'password authentication failed for user "postgres" ({PASSWORD})'
    calls = Calls(refusal=refusal)

    code = calls.run(tmp_path, [SOURCE, str(saved(tmp_path))])

    assert code == 2
    assert (calls.keys_for, calls.stored) == ([], [])
    said = capsys.readouterr()
    assert "password authentication failed" in said.out
    assert PASSWORD not in said.out + said.err


def test_the_storing_commands_own_code_is_passed_on(tmp_path):
    assert Calls(code=1).run(tmp_path, [SOURCE, str(saved(tmp_path))]) == 1
