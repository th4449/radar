"""The sender that hands alert emails to the provider. Written before the code.

No test here sends anything. A stand-in answers the way Resend's documentation of its batch
address says it answers, read on November 23, 2026. Every address is made up.
"""

from __future__ import annotations

import json
import uuid

import httpx
import pytest

from pipeline import alert_email
from pipeline.config import load_email
from pipeline.email_sender import NotSent, ResendSender, sender_from_env

KEY = "re_test_key_value"
SETTINGS = load_email().model_copy(
    update={
        "site_url": "https://radar.example.org",
        "from_address": "alerts@radar.example.org",
    }
)


def message(n: int, kind: str = "each") -> alert_email.Message:
    return alert_email.Message(
        user_id=uuid.UUID(int=n),
        to=f"person{n}@example.com",
        token=uuid.UUID(int=1000 + n),
        kind=kind,
        state="TX",
        alert_ids=(12,),
        subject="Confirmed alert: Signals near Granbury",
        text=f"The body for person {n}.",
    )


class Provider:
    def __init__(self, status: int = 200, short: bool = False) -> None:
        self.requests: list[httpx.Request] = []
        self.status, self.short = status, short

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if self.status != 200:
            body = {"statusCode": self.status, "name": "validation_error", "message": "refused"}
            return httpx.Response(self.status, json=body)
        sent = json.loads(request.content)
        ids = [{"id": str(uuid.uuid4())} for _ in sent[: len(sent) - (1 if self.short else 0)]]
        return httpx.Response(200, json={"data": ids})


def sender(provider: Provider) -> ResendSender:
    return ResendSender(KEY, SETTINGS, transport=httpx.MockTransport(provider))


def test_a_batch_goes_to_the_provider_as_one_request():
    provider = Provider()
    sender(provider).send([message(1), message(2)])
    (request,) = provider.requests
    assert str(request.url) == "https://api.resend.com/emails/batch"
    assert request.headers["authorization"] == f"Bearer {KEY}"
    first, second = json.loads(request.content)
    assert first["to"] == ["person1@example.com"] and second["to"] == ["person2@example.com"]
    assert first["from"] == "Dekleptocracy Alliance <alerts@radar.example.org>"
    assert first["subject"] == "Confirmed alert: Signals near Granbury"
    assert first["text"] == "The body for person 1."
    assert "html" not in first  # plain words only


def test_every_email_carries_its_own_unsubscribe_link_in_its_headers():
    provider = Provider()
    sender(provider).send([message(1)])
    (sent,) = json.loads(provider.requests[0].content)
    token = uuid.UUID(int=1001)
    assert sent["headers"] == {
        "List-Unsubscribe": f"<https://radar.example.org/unsubscribe/?token={token}>"
    }


def test_the_same_batch_sent_again_carries_the_same_key_so_nobody_gets_it_twice():
    provider = Provider()
    one = sender(provider)
    one.send([message(1), message(2)])
    one.send([message(2), message(1)])
    one.send([message(1), message(3)])
    keys = [r.headers["idempotency-key"] for r in provider.requests]
    assert keys[0] == keys[1] != keys[2]
    assert all(len(k) <= 256 for k in keys)


def test_a_refusal_raises_and_names_no_person_and_no_key():
    provider = Provider(status=422)
    with pytest.raises(NotSent) as caught:
        sender(provider).send([message(1)])
    said = str(caught.value)
    assert "422" in said and "validation_error" in said
    assert "person1@example.com" not in said and KEY not in said


def test_a_batch_the_provider_took_only_part_of_raises():
    with pytest.raises(NotSent, match="1 of 2"):
        sender(Provider(short=True)).send([message(1), message(2)])


def test_a_batch_larger_than_the_provider_takes_is_refused_before_anything_is_sent():
    provider = Provider()
    with pytest.raises(NotSent, match="100"):
        sender(provider).send([message(n) for n in range(101)])
    assert provider.requests == []


def test_an_empty_batch_asks_the_provider_nothing():
    provider = Provider()
    sender(provider).send([])
    assert provider.requests == []


# --- the three locks ------------------------------------------------------------------------------

READY = {"RADAR_EMAIL_LIVE": "true", "RESEND_API_KEY": KEY}


def test_a_sender_exists_only_when_the_owner_has_set_every_lock():
    assert isinstance(sender_from_env(SETTINGS, READY), ResendSender)
    # The owner's switch, the provider's key, and the settings the owner fills in.
    with pytest.raises(NotSent, match="RADAR_EMAIL_LIVE"):
        sender_from_env(SETTINGS, {"RESEND_API_KEY": KEY})
    with pytest.raises(NotSent, match="RADAR_EMAIL_LIVE"):
        sender_from_env(SETTINGS, {**READY, "RADAR_EMAIL_LIVE": "yes"})
    with pytest.raises(NotSent, match="RESEND_API_KEY"):
        sender_from_env(SETTINGS, {"RADAR_EMAIL_LIVE": "true"})
    with pytest.raises(NotSent, match="from_address"):
        sender_from_env(SETTINGS.model_copy(update={"from_address": None}), READY)
    with pytest.raises(NotSent, match="site_url"):
        sender_from_env(SETTINGS.model_copy(update={"site_url": None}), READY)


def test_the_settings_as_they_stand_today_cannot_send():
    with pytest.raises(NotSent):
        sender_from_env(load_email(), READY)
    assert "from_address" in load_email().missing() and "site_url" in load_email().missing()


def test_the_command_is_a_dry_run_unless_asked_and_refuses_when_a_lock_is_open(monkeypatch, capsys):
    monkeypatch.setenv("DATABASE_URL", "postgresql://nowhere.invalid/none")
    monkeypatch.delenv("RADAR_EMAIL_LIVE", raising=False)
    monkeypatch.delenv("RESEND_API_KEY", raising=False)
    # Asked to send with no lock set: it refuses before it opens the database.
    assert alert_email.main(["--kind", "weekly", "--send"]) == 2
    assert "not sent" in capsys.readouterr().err
