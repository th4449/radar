"""Hand alert emails to the provider. See BUILD_PLAN.md sections 3, 7 and 11.

**Sending real email is the owner's decision.** This module can send only when three things
are all true, and the owner sets each of them:

1. The setting `RADAR_EMAIL_LIVE` is the word true. A repository variable.
2. `RESEND_API_KEY` holds the provider's key. A secret.
3. `config/email.yaml` gives the postal address, the site's address and the address the
   emails are from. The provider sends only from a domain the owner has proved is theirs.

With any of them missing there is no sender, and the email job is a dry run.

The provider is Resend. One request carries a batch of up to 100 emails, as its documentation
of `POST https://api.resend.com/emails/batch` says, read on November 23, 2026. **Nothing here
has been run against the provider.**

- Plain words only. An email is the text the job rendered, with no tracking of any kind.
- Each email carries its own unsubscribe link in its headers, as well as in its words.
- A batch carries a key made from who it is for and what it holds. Sent again within a day,
  the provider takes the same batch once.
- An error names the provider's answer. It never names a person, an address or the key.
"""

from __future__ import annotations

import contextlib
import hashlib
import os
from collections.abc import Mapping, Sequence

import httpx

from pipeline.alert_email import Message
from pipeline.config import EmailFile

BATCH_ADDRESS = "https://api.resend.com/emails/batch"
MAX_BATCH = 100  # the provider's limit on one request


class NotSent(RuntimeError):
    """Nothing was handed to the provider, or the provider did not take all of it."""


class ResendSender:
    def __init__(
        self,
        api_key: str,
        settings: EmailFile,
        *,
        transport: httpx.BaseTransport | None = None,
        timeout: float = 60.0,
    ) -> None:
        missing = settings.missing()
        if missing:
            raise NotSent(f"config/email.yaml does not set: {', '.join(missing)}")
        self._from = f"{settings.organization} <{settings.from_address}>"
        self._site = settings.site_url
        self._client = httpx.Client(
            headers={"Authorization": f"Bearer {api_key}"}, transport=transport, timeout=timeout
        )

    def __repr__(self) -> str:
        return "ResendSender()"

    def _key(self, batch: Sequence[Message]) -> str:
        """The same batch gives the same key, in whatever order it is handed over."""
        parts = sorted(f"{m.user_id}:{m.kind}:{','.join(map(str, m.alert_ids))}" for m in batch)
        return "radar-" + hashlib.sha256("\n".join(parts).encode()).hexdigest()

    def send(self, batch: Sequence[Message]) -> None:
        """Hand one batch to the provider. Raise if any of it was not accepted."""
        if not batch:
            return
        if len(batch) > MAX_BATCH:
            raise NotSent(f"a batch of {len(batch)} is over the provider's limit of {MAX_BATCH}")
        payload = [
            {
                "from": self._from,
                "to": [m.to],
                "subject": m.subject,
                "text": m.text,
                "headers": {"List-Unsubscribe": f"<{self._site}/unsubscribe/?token={m.token}>"},
            }
            for m in batch
        ]
        try:
            response = self._client.post(
                BATCH_ADDRESS, json=payload, headers={"Idempotency-Key": self._key(batch)}
            )
        except httpx.HTTPError as exc:
            raise NotSent(f"the provider could not be reached: {type(exc).__name__}") from None
        if not response.is_success:
            name = ""
            with contextlib.suppress(ValueError, AttributeError):
                name = str(response.json().get("name") or "")
            raise NotSent(f"the provider refused the batch: {response.status_code} {name}".strip())
        try:
            taken = len(response.json()["data"])
        except (ValueError, KeyError, TypeError):
            raise NotSent("the provider's answer could not be read") from None
        if taken != len(batch):
            raise NotSent(f"the provider took {taken} of {len(batch)} emails")


def sender_from_env(settings: EmailFile, env: Mapping[str, str] | None = None) -> ResendSender:
    """A sender, if the owner has set every lock. Raises NotSent and says which is open."""
    env = os.environ if env is None else env
    if (env.get("RADAR_EMAIL_LIVE") or "").strip() != "true":
        raise NotSent("RADAR_EMAIL_LIVE is not set to true. Sending is the owner's decision.")
    key = (env.get("RESEND_API_KEY") or "").strip()
    if not key:
        raise NotSent("RESEND_API_KEY is not set")
    return ResendSender(key, settings)
