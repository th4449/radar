"""The words of an alert email. See BUILD_PLAN.md section 7.

Every email carries the word confirmed, a link to the alert page with its sources, an
unsubscribe link and the organization's postal address.
"""

from __future__ import annotations

import datetime as dt

import pytest
from pydantic import ValidationError

from pipeline import alert_email
from pipeline.config import EmailFile, load_email

SETTINGS = load_email().model_copy(
    update={
        "site_url": "https://radar.example.org",
        "postal_address": "1 Example Street, Austin, TX 78701",
    }
)
PLACES = alert_email.Places()
WHEN = dt.datetime(2026, 11, 20, 15, 0, tzinfo=dt.UTC)
GRANBURY = alert_email.AlertItem(
    12, "TX", "48221", "Signals near Granbury", "Two records name this tract.\n", WHEN, 2
)
SALINE = alert_email.AlertItem(
    13, "MI", "26161", "Signals near Saline", "One record names this tract.", WHEN, 1
)


# The settings file with nothing filled in by the owner.
BLANK = load_email().model_copy(update={"site_url": None, "postal_address": None})


def test_the_settings_file_loads_and_sending_is_not_ready():
    settings = load_email()
    # The postal address is set. The site has no address until it is hosted.
    assert settings.postal_address.splitlines()[-1] == "Arlington VA 22206-9998"
    # Nor an address to send from, until the owner proves a domain to the provider.
    assert settings.missing() == ["site_url", "from_address"]
    assert BLANK.missing() == ["postal_address", "site_url", "from_address"]
    assert settings.batch_size <= settings.daily_limit


def test_the_postal_address_closes_every_email_as_the_owner_gave_it():
    _, text = alert_email.render_each(GRANBURY, load_email(), PLACES, "t")
    assert text.endswith(
        "Dekleptocracy Alliance\n2850 S Quincy St\nPO Box 6580\nArlington VA 22206-9998"
    )


def test_a_site_address_must_be_a_web_address_with_no_slash_at_the_end():
    base = load_email().model_dump()
    for bad in ("radar.example.org", "https://radar.example.org/", "ftp://radar.example.org"):
        with pytest.raises(ValidationError):
            EmailFile.model_validate({**base, "site_url": bad})
    assert EmailFile.model_validate({**base, "site_url": "https://radar.example.org"})


def test_an_alert_email_carries_everything_section_7_asks_for():
    subject, text = alert_email.render_each(GRANBURY, SETTINGS, PLACES, "the-token")
    assert subject == "Confirmed alert in Hood County, Texas: Signals near Granbury"
    assert "Confirmed. Published November 20, 2026." in text
    assert "Hood County, Texas." in text
    assert "Two records name this tract." in text
    assert "2 public records" in text
    assert "https://radar.example.org/alert/?id=12" in text
    assert "https://radar.example.org/corrections/?alert=12" in text
    assert "https://radar.example.org/unsubscribe/?token=the-token" in text
    assert "https://radar.example.org/account/" in text
    assert text.rstrip().endswith("Dekleptocracy Alliance\n1 Example Street, Austin, TX 78701")


def test_an_alert_email_never_says_a_data_center_is_planned():
    _, text = alert_email.render_each(GRANBURY, SETTINGS, PLACES, "t")
    assert "It does not mean a data center is planned." in text
    assert text.count(alert_email.STANDING) == 1


def test_a_digest_lists_each_alert_with_its_link():
    second = alert_email.AlertItem(14, "TX", "48217", "Signals near Hillsboro", "Body.", WHEN, 3)
    subject, text = alert_email.render_weekly("TX", [GRANBURY, second], SETTINGS, PLACES, "tok")
    assert subject == "Texas weekly digest: 2 confirmed alerts"
    assert text.index("Signals near Granbury") < text.index("Signals near Hillsboro")
    for needed in (
        "https://radar.example.org/alert/?id=12",
        "https://radar.example.org/alert/?id=14",
        "Hill County. 3 public records.",
        "https://radar.example.org/unsubscribe/?token=tok",
        "1 Example Street, Austin, TX 78701",
        "you signed up for Texas alerts",
    ):
        assert needed in text
    # The digest links to the alert. It does not repeat the alert's text.
    assert "Two records name this tract." not in text


def test_an_alerts_date_is_the_day_in_its_own_state():
    """Published at 8 in the evening in Texas is still that day, though UTC has moved on."""
    late = dt.datetime(2026, 11, 21, 2, 0, tzinfo=dt.UTC)
    texas = alert_email.AlertItem(1, "TX", "48221", "H", "B", late, 1)
    michigan = alert_email.AlertItem(2, "MI", "26161", "H", "B", late, 1)
    assert alert_email.published_day(texas) == "November 20, 2026"
    assert alert_email.published_day(michigan) == "November 20, 2026"
    assert (
        "Published November 20, 2026." in alert_email.render_each(texas, SETTINGS, PLACES, "t")[1]
    )


def test_a_digest_of_one_alert_reads_as_one():
    subject, text = alert_email.render_weekly("MI", [SALINE], SETTINGS, PLACES, "tok")
    assert subject == "Michigan weekly digest: 1 confirmed alert"
    assert "Washtenaw County. 1 public record." in text


def test_an_email_rendered_before_the_owner_sets_the_address_says_so():
    _, text = alert_email.render_each(GRANBURY, BLANK, PLACES, "t")
    assert "Postal address [not set]" in text
    assert "[not set]/alert/?id=12" in text


def test_a_county_outside_the_lists_is_shown_by_its_code():
    assert PLACES.county("48221") == "Hood County"
    assert PLACES.county("99999") == "County 99999"
