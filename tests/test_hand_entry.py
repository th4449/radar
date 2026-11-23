"""Entering a record a person read by hand. Written before the command.

Some sources a program may not read and a person may. The command takes the record's saved
file and its facts. It checks the facts against the file, stores the file with its address,
time and hash as a run does, and makes one signal. Every agency and company here is made up.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import pytest

from pipeline import hand_entry
from pipeline.config import load_sources
from pipeline.signals import Listing, Rules

from .helpers import make_pdf, make_source

NOW = dt.datetime(2026, 12, 1, 16, 0, tzinfo=dt.UTC)
SAVED_AT = dt.datetime(2026, 12, 1, 15, 0, tzinfo=dt.UTC)
RULES = Rules(listings={})
NOTICES = make_source(
    id="tx_example_notices",
    name="Example county notices",
    url="https://www.notices.example.gov/search",
    method="manual",
    robots_status="restricted",
    hand_entered=True,
)
TEXT = (
    "NOTICE OF PUBLIC HEARING. The Commissioners Court of Hood County will consider a tax "
    "abatement agreement with Example Hosting LLC for a data center in Reinvestment Zone 4."
)


def saved(tmp_path: Path, text: str = TEXT, name: str = "notice.pdf") -> Path:
    path = tmp_path / name
    path.write_bytes(make_pdf([text]))
    return path


def facts(**changes) -> hand_entry.Facts:
    base = {
        "url": "https://www.notices.example.gov/notice/4471",
        "event_date": dt.date(2026, 11, 28),
        "county": "Hood",
        "signal_type": "abatement_notice",
        "summary": "Hood County published a notice of a hearing on a tax abatement agreement "
        "with Example Hosting LLC for a data center.",
        "reference": "Notice 4471",
        "party": "Example Hosting LLC",
        "reason": None,
    }
    return hand_entry.Facts(**{**base, **changes})


def prepare(tmp_path, source=NOTICES, rules=RULES, **changes):
    path = changes.pop("path", None) or saved(tmp_path)
    return hand_entry.prepare(source, path, facts(**changes), rules, saved_at=SAVED_AT, now=NOW)


def test_a_record_is_prepared_as_a_stored_file_and_one_signal(tmp_path):
    ready = prepare(tmp_path)
    assert ready.result.url == "https://www.notices.example.gov/notice/4471"
    assert ready.result.retrieved_at == SAVED_AT
    assert ready.result.body.startswith(b"%PDF")
    draft = ready.draft
    assert (draft.signal_type, draft.event_date) == ("abatement_notice", dt.date(2026, 11, 28))
    assert draft.county_fips == "48221"
    assert (draft.party, draft.party_kind) == ("Example Hosting LLC", "company")
    assert draft.extracted["entered_by_hand"] is True
    assert draft.extracted["reference"] == "Example county notices, Notice 4471"


def test_the_reason_comes_from_the_words_of_the_file_itself(tmp_path):
    draft = prepare(tmp_path).draft
    rules = {r["rule"] for r in draft.extracted["reasons"]}
    assert rules == {"direct_term", "code_word"}  # "data center" and "reinvestment zone"
    assert draft.confidence == RULES.confidence["direct_term"]


def test_a_file_that_uses_none_of_the_terms_needs_a_stated_reason(tmp_path):
    quiet = saved(tmp_path, "Notice of a hearing on an agreement with Example Hosting LLC.")
    with pytest.raises(hand_entry.NotEntered, match="--reason"):
        prepare(tmp_path, path=quiet, summary="Hood County published a notice of a hearing.")
    draft = prepare(
        tmp_path,
        path=quiet,
        summary="Hood County published a notice of a hearing on an agreement.",
        reason="The county judge named this company's site at the meeting of November 10.",
    ).draft
    assert [r["rule"] for r in draft.extracted["reasons"]] == ["stated_by_hand"]
    # A reason a person states counts as the weakest kind does.
    assert draft.confidence == RULES.confidence["code_word"]


def test_a_company_on_the_comptrollers_list_is_a_reason(tmp_path):
    listed = Rules(
        listings={"EXAMPLE HOSTING LLC": [Listing("Example Hosting LLC", "owner", "EX1", "q")]}
    )
    quiet = saved(tmp_path, "Notice of a hearing on an agreement with Example Hosting LLC.")
    draft = prepare(
        tmp_path, rules=listed, path=quiet, summary="Hood County published a notice of a hearing."
    ).draft
    assert [r["rule"] for r in draft.extracted["reasons"]] == ["listed_company"]


def test_only_a_source_the_owner_has_marked_takes_a_record(tmp_path):
    held = make_source(id="tx_example_held", method="manual", robots_status="restricted")
    with pytest.raises(hand_entry.NotEntered, match="not marked hand_entered"):
        prepare(tmp_path, source=held)
    # No source is marked today. Marking one is the owner's decision.
    assert [s.id for s in load_sources().sources if s.hand_entered] == []


@pytest.mark.parametrize(
    ("changes", "says"),
    [
        ({"url": "https://elsewhere.example.com/notice/4471"}, "not on the source's own site"),
        ({"url": "ftp://www.notices.example.gov/notice/4471"}, "web address"),
        ({"event_date": dt.date(2026, 12, 5)}, "in the future"),
        ({"county": "Loving"}, "not a county the radar covers"),
        ({"signal_type": "rumor"}, "not a kind of signal"),
        ({"summary": "Too short."}, "summary"),
        ({"summary": "A data center is planned in Hood County by Example Hosting LLC."},
         "the file does not say"),
        ({"reference": ""}, "reference"),
        ({"reference": "Example Hosting LLC notice"}, "never names a party"),
        ({"party": "John Example"}, "may be a person"),
        ({"party": None}, "names no company"),
    ],
)  # fmt: skip
def test_facts_that_break_a_rule_are_refused(tmp_path, changes, says):
    with pytest.raises(hand_entry.NotEntered, match=says):
        prepare(tmp_path, **changes)


def test_a_record_with_no_company_is_taken_when_the_file_gives_a_project_name(tmp_path):
    named = saved(
        tmp_path,
        "Executive session under Section 551.087 on economic development negotiations: "
        "Project Falcon. A tax abatement in a reinvestment zone.",
    )
    draft = prepare(
        tmp_path,
        path=named,
        party=None,
        summary="Hood County posted a notice of a closed session on economic development "
        "negotiations it calls Project Falcon.",
    ).draft
    assert draft.party is None
    assert {r.get("term") for r in draft.extracted["reasons"]} >= {"Project Falcon"}


def test_a_file_that_cannot_be_read_as_a_record_is_refused(tmp_path):
    empty = tmp_path / "empty.pdf"
    empty.write_bytes(b"")
    with pytest.raises(hand_entry.NotEntered, match="empty"):
        prepare(tmp_path, path=empty)
    blob = tmp_path / "archive.webarchive"
    blob.write_bytes(b"bplist00\xd1\x01\x02" * 40)
    with pytest.raises(hand_entry.NotEntered, match="PDF, a web page"):
        prepare(tmp_path, path=blob)


def test_the_time_the_file_was_saved_cannot_be_in_the_future(tmp_path):
    with pytest.raises(hand_entry.NotEntered, match="in the future"):
        hand_entry.prepare(
            NOTICES, saved(tmp_path), facts(), RULES, saved_at=NOW + dt.timedelta(hours=2), now=NOW
        )


def test_the_command_names_what_is_wrong_and_stores_nothing(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    args = [
        "tx_public_notices", str(saved(tmp_path)), "--url", "https://x.example/1",
        "--date", "2026-11-28", "--county", "Hood", "--type", "abatement_notice",
        "--summary", "A summary of the record that is long enough.", "--reference", "Notice 1",
    ]  # fmt: skip
    assert hand_entry.main(args) == 2
    assert "DATABASE_URL" in capsys.readouterr().err
