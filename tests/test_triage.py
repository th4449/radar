"""The optional model triage: off by default, capped, and never trusted without its quote.

No test calls the model. Most use a stand-in client. One sends a request through the real SDK
to a fake server, to check the request the SDK builds and how its answer is read.
"""

from __future__ import annotations

import datetime as dt
import json
from decimal import Decimal
from types import SimpleNamespace

import anthropic
import httpx2
import pytest

from pipeline.config import load_triage
from pipeline.signals import Draft
from pipeline.triage import (
    SYSTEM,
    MemoryLedger,
    NotConfigured,
    Triager,
    annotate,
    cost_usd,
    eligible,
    worst_case_usd,
)

SETTINGS = load_triage()
EXCERPTS = "CPS Energy submitted the Large Load Additions Project for review.\n\nAbout 2 GW Load."


def reply(
    verdict: str = "relevant",
    quote: str = "Large Load Additions Project",
    *,
    stop_reason: str = "end_turn",
    text: str | None = None,
    tokens: tuple[int, int] = (800, 60),
) -> SimpleNamespace:
    body = text if text is not None else json.dumps({"verdict": verdict, "quote": quote})
    return SimpleNamespace(
        stop_reason=stop_reason,
        content=[SimpleNamespace(type="thinking", thinking=""), SimpleNamespace(type="text",
                                                                               text=body)],
        usage=SimpleNamespace(input_tokens=tokens[0], output_tokens=tokens[1]),
    )  # fmt: skip


class StandIn:
    """A client that records what it was asked and answers from a script."""

    def __init__(self, *replies: SimpleNamespace) -> None:
        self.replies = list(replies) or [reply()]
        self.requests: list[dict] = []
        self.messages = SimpleNamespace(create=self._create)

    def _create(self, **kwargs) -> SimpleNamespace:
        self.requests.append(kwargs)
        return self.replies.pop(0) if len(self.replies) > 1 else self.replies[0]


def triager(client: StandIn | None = None, cap: str = "5", spent: str = "0"):
    ledger = MemoryLedger(spent)
    return Triager(client or StandIn(), ledger, Decimal(cap), SETTINGS), ledger


def draft(rules: tuple[str, ...] = ("code_word",), snippets: tuple[str, ...] = (EXCERPTS,)):
    return Draft(
        signal_type="transmission_filing", key="k", event_date=dt.date(2026, 7, 17),
        summary="ERCOT file mentions \"large load\".", confidence=0.3, county_fips="48029",
        party=None, party_kind=None,
        extracted={"reasons": [{"rule": r, "term": "x"} for r in rules],
                   "snippets": list(snippets)},
    )  # fmt: skip


# --- switched off unless everything is set ------------------------------------------------------


def test_triage_is_off_by_default():
    assert Triager.from_env(MemoryLedger(), env={}) is None
    assert Triager.from_env(MemoryLedger(), env={"RADAR_TRIAGE": "off"}) is None
    assert Triager.from_env(MemoryLedger(), env={"RADAR_TRIAGE_MONTHLY_CAP_USD": "5"}) is None


@pytest.mark.parametrize("cap", ["", "five", "0", "-1", "nan", "inf"])
def test_switched_on_without_a_real_cap_it_refuses_to_start(cap):
    env = {"RADAR_TRIAGE": "on", "RADAR_TRIAGE_MONTHLY_CAP_USD": cap}
    with pytest.raises(NotConfigured):
        Triager.from_env(MemoryLedger(), env=env, client=StandIn())


def test_switched_on_with_a_cap_it_starts():
    env = {"RADAR_TRIAGE": "ON", "RADAR_TRIAGE_MONTHLY_CAP_USD": "7.50"}
    made = Triager.from_env(MemoryLedger(), env=env, client=StandIn())
    assert made is not None and made.cap_usd == Decimal("7.50")


def test_the_model_and_prices_are_the_ones_in_the_plan_and_on_the_price_page():
    assert SETTINGS.model == "claude-haiku-5-5"
    assert (SETTINGS.input_per_mtok, SETTINGS.output_per_mtok) == (0.10, 0.50)
    assert (SETTINGS.long_input_per_mtok, SETTINGS.long_output_per_mtok) == (0.50, 2.50)
    assert SETTINGS.prices_checked == dt.date(2026, 11, 20)


# --- cost and the cap ---------------------------------------------------------------------------


def test_cost_at_the_base_and_the_long_prompt_rates():
    assert cost_usd(SETTINGS, 50_000, 0) == Decimal("0.005")
    assert cost_usd(SETTINGS, 0, 1_000_000) == Decimal("0.50")
    assert cost_usd(SETTINGS, 800, 60) == Decimal("0.00011")
    assert cost_usd(SETTINGS, 100_000, 0) == Decimal("0.01")
    assert cost_usd(SETTINGS, 100_001, 1000) == Decimal("0.0525005")


def test_the_worst_case_is_never_below_what_a_call_can_cost():
    worst = worst_case_usd(SETTINGS, EXCERPTS)
    most_tokens_in = len(SYSTEM.encode()) + len(EXCERPTS.encode())
    assert worst >= cost_usd(SETTINGS, most_tokens_in, SETTINGS.max_output_tokens)
    assert worst < Decimal("0.01")  # a call on a short excerpt costs well under a cent


def test_a_call_is_made_and_logged_with_its_cost():
    client = StandIn(reply(tokens=(800, 60)))
    t, ledger = triager(client)
    answer = t.ask(EXCERPTS, document_id=42)
    assert answer.verdict == "relevant" and answer.quote == "Large Load Additions Project"
    assert answer.model == "claude-haiku-5-5" and answer.prompt_version == 1
    assert ledger.rows == [
        {"model": "claude-haiku-5-5", "document_id": 42, "input_tokens": 800,
         "output_tokens": 60, "cost_usd": Decimal("0.00011"), "outcome": "relevant"}
    ]  # fmt: skip
    assert ledger.spent_this_month() == Decimal("0.00011")


def test_no_call_is_made_once_the_cap_would_be_passed():
    worst = worst_case_usd(SETTINGS, EXCERPTS)
    client = StandIn()
    # One cent of room is more than a call can cost. A tenth of the worst case is not.
    t, ledger = triager(client, cap="5", spent=str(Decimal("5") - worst / 10))
    assert t.ask(EXCERPTS) is None
    assert client.requests == [] and ledger.rows == []
    assert t.skipped_for_cap == 1 and t.calls == 0


def test_the_cap_holds_over_many_calls():
    client = StandIn(reply(tokens=(900, 2048)))  # every answer as long as allowed
    t, ledger = triager(client, cap="0.01")
    answers = [t.ask(EXCERPTS) for _ in range(40)]
    assert 0 < t.calls < 40
    assert answers[t.calls :] == [None] * (40 - t.calls)
    assert ledger.spent_this_month() <= Decimal("0.01")
    assert t.skipped_for_cap == 40 - t.calls


def test_text_is_cut_to_the_limit_before_it_is_sent():
    client = StandIn(reply(verdict="unclear", quote=""))
    t, _ = triager(client)
    t.ask("large load " * 5000)
    sent = client.requests[0]["messages"][0]["content"]
    assert len(sent) <= SETTINGS.max_excerpt_chars + len("<excerpts>\n\n</excerpts>")


def test_nothing_is_sent_for_an_empty_excerpt():
    client = StandIn()
    t, _ = triager(client)
    assert t.ask("   \n ") is None and client.requests == []


# --- an answer needs its words ------------------------------------------------------------------


def test_an_answer_whose_quote_is_not_in_the_record_becomes_unclear():
    t, ledger = triager(StandIn(reply(verdict="relevant", quote="a new data center campus")))
    answer = t.ask(EXCERPTS)
    assert (answer.verdict, answer.quote) == ("unclear", None)
    assert ledger.rows[0]["outcome"] == "unclear"


def test_a_quote_may_differ_in_spacing_and_case_only():
    t, _ = triager(StandIn(reply(quote="large load  additions\nproject")))
    assert t.ask(EXCERPTS).verdict == "relevant"


def test_an_answer_with_no_quote_becomes_unclear():
    t, _ = triager(StandIn(reply(verdict="not_relevant", quote="  ")))
    assert t.ask(EXCERPTS).verdict == "unclear"


@pytest.mark.parametrize(
    ("made", "outcome"),
    [
        (reply(stop_reason="refusal", text=""), "refusal"),
        (reply(stop_reason="max_tokens", text='{"verdict": "rel'), "cut_off"),
        (reply(text="not json"), "unreadable"),
        (reply(text='{"verdict": "maybe", "quote": "x"}'), "unreadable"),
        (reply(text='{"quote": "x"}'), "unreadable"),
    ],
)
def test_a_reply_that_cannot_be_used_gives_no_answer_and_is_still_paid_for(made, outcome):
    t, ledger = triager(StandIn(made))
    assert t.ask(EXCERPTS) is None
    assert ledger.rows[0]["outcome"] == outcome
    assert ledger.rows[0]["cost_usd"] > 0


# --- which signals are asked about --------------------------------------------------------------


def test_only_a_weak_signal_from_an_open_record_is_asked_about():
    assert eligible("tx_ercot_rpg", draft())
    assert eligible("tx_ercot_rpg", draft(rules=("code_word", "project_code_name")))
    assert not eligible("tx_ercot_rpg", draft(rules=("direct_term",)))
    assert not eligible("tx_ercot_rpg", draft(rules=("code_word", "direct_term")))
    assert not eligible("tx_ercot_rpg", draft(snippets=()))


def test_a_record_from_a_list_that_names_people_is_never_sent():
    assert not eligible("tx_twdb_well_reports", draft())
    assert not eligible("tx_tceq_air_pending_legacy", draft())
    client = StandIn()
    t, _ = triager(client)
    out = annotate("tx_twdb_well_reports", [draft()], t)
    assert client.requests == [] and "triage" not in out[0].extracted


def test_the_answer_is_stored_beside_the_signal_and_changes_nothing_else():
    t, _ = triager(StandIn(reply(verdict="not_relevant", quote="for review")))
    before = draft()
    (after,) = annotate("tx_ercot_rpg", [before], t, document_id=7)
    assert after.extracted["triage"]["verdict"] == "not_relevant"
    assert after.extracted["triage"]["quote"] == "for review"
    assert (after.summary, after.confidence, after.signal_type, after.county_fips) == (
        before.summary, before.confidence, before.signal_type, before.county_fips,
    )  # fmt: skip
    assert "triage" not in before.extracted


def test_with_triage_off_the_drafts_pass_through_untouched():
    drafts = [draft()]
    assert annotate("tx_ercot_rpg", drafts, None) is drafts


def test_a_signal_the_cap_leaves_unasked_is_kept_as_it_is():
    t, _ = triager(StandIn(), cap="0.000001")
    (after,) = annotate("tx_ercot_rpg", [draft()], t)
    assert "triage" not in after.extracted


# --- the request the real SDK builds ------------------------------------------------------------


def test_the_request_and_the_reading_of_its_answer_through_the_real_sdk():
    seen: list[httpx2.Request] = []

    def server(request: httpx2.Request) -> httpx2.Response:
        seen.append(request)
        return httpx2.Response(
            200,
            json={
                "id": "msg_test", "type": "message", "role": "assistant",
                "model": "claude-haiku-5-5",
                "content": [
                    {"type": "text",
                     "text": json.dumps({"verdict": "relevant", "quote": "About 2 GW Load"})}
                ],
                "stop_reason": "end_turn", "stop_sequence": None,
                "usage": {"input_tokens": 812, "output_tokens": 44},
            },
        )  # fmt: skip

    client = anthropic.Anthropic(
        api_key="not-a-real-key",
        max_retries=0,
        http_client=anthropic.DefaultHttpxClient(transport=httpx2.MockTransport(server)),
    )
    ledger = MemoryLedger()
    answer = Triager(client, ledger, Decimal("5"), SETTINGS).ask(EXCERPTS, document_id=3)

    assert (answer.verdict, answer.quote) == ("relevant", "About 2 GW Load")
    assert ledger.rows[0]["input_tokens"] == 812 and ledger.rows[0]["output_tokens"] == 44
    assert ledger.rows[0]["cost_usd"] == Decimal("0.0001032")

    (request,) = seen
    assert request.url.path == "/v1/messages"
    body = json.loads(request.content)
    assert body["model"] == "claude-haiku-5-5"
    assert body["max_tokens"] == SETTINGS.max_output_tokens
    assert body["system"] == SYSTEM
    assert body["messages"] == [{"role": "user", "content": f"<excerpts>\n{EXCERPTS}\n</excerpts>"}]
    assert body["output_config"]["effort"] == "low"
    schema = body["output_config"]["format"]["schema"]
    assert body["output_config"]["format"]["type"] == "json_schema"
    assert schema["properties"]["verdict"]["enum"] == ["relevant", "not_relevant", "unclear"]
    assert schema["additionalProperties"] is False
    # This model rejects sampling settings and a thinking budget. None is sent.
    assert not {"temperature", "top_p", "top_k", "thinking"} & set(body)
