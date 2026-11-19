"""The fetcher is polite and stops when told no. No test here touches the network."""

from __future__ import annotations

import httpx
import pytest

from collectors import base
from collectors.base import (
    Blocked,
    Fetcher,
    FetchError,
    NotPermitted,
    RobotsDisallowed,
    TooLarge,
)

from .helpers import CONTACT, FakeClock, Site, make_source

PAGE = "https://records.example.gov/notices/1"
HTML = httpx.Response(200, html="<html><body><p>Notice</p></body></html>")


def fetcher_for(site: Site, clock: FakeClock | None = None, **kwargs) -> Fetcher:
    clock = clock or FakeClock()
    kwargs.setdefault("contact", CONTACT)
    source = kwargs.pop("source", make_source())
    return Fetcher(source, transport=site.transport, clock=clock, sleep=clock.sleep, **kwargs)


# --- identity -----------------------------------------------------------------------------------


def test_user_agent_names_the_collector_and_a_contact():
    agent = base.user_agent("radar@example.org")
    assert agent.startswith("DataCenterRadar/")
    assert "contact: radar@example.org" in agent


def test_no_live_request_without_a_contact_address(monkeypatch):
    monkeypatch.delenv("RADAR_CONTACT", raising=False)
    with pytest.raises(NotPermitted):
        Fetcher(make_source(), transport=Site().transport)


def test_every_request_carries_the_user_agent():
    site = Site({PAGE: HTML})
    fetcher_for(site).get(PAGE)
    assert len(site.requests) == 2  # robots.txt, then the page
    for request in site.requests:
        assert CONTACT in request.headers["user-agent"]


# --- our own rules ------------------------------------------------------------------------------


def test_refuses_a_source_that_has_no_source_note_yet():
    source = make_source(method="manual", robots_status="not_checked", verified_at=None)
    for by_hand in (False, True):
        with pytest.raises(NotPermitted):
            fetcher_for(Site(), source=source, by_hand=by_hand)


@pytest.mark.parametrize("status", ["restricted", "blocked"])
def test_refuses_a_restricted_source_even_by_hand(status):
    source = make_source(method="manual", robots_status=status)
    for by_hand in (False, True):
        with pytest.raises(NotPermitted):
            fetcher_for(Site(), source=source, by_hand=by_hand)


def test_a_manual_source_is_fetched_only_by_hand():
    source = make_source(method="manual")
    with pytest.raises(NotPermitted):
        fetcher_for(Site(), source=source)
    site = Site({PAGE: HTML})
    assert fetcher_for(site, source=source, by_hand=True).get(PAGE).status == 200


def test_rejects_urls_that_are_not_http():
    with pytest.raises(FetchError):
        fetcher_for(Site()).get("file:///etc/hosts")


# --- robots.txt ---------------------------------------------------------------------------------


def test_robots_disallow_stops_the_request_before_it_is_made():
    site = Site({PAGE: HTML}, robots="User-agent: *\nDisallow: /notices/")
    with pytest.raises(RobotsDisallowed):
        fetcher_for(site).get(PAGE)
    assert site.page_urls() == []


def test_robots_rule_for_our_agent_is_honored():
    site = Site({PAGE: HTML}, robots="User-agent: DataCenterRadar\nDisallow: /\n")
    with pytest.raises(RobotsDisallowed):
        fetcher_for(site).get(PAGE)


def test_no_robots_file_means_allowed():
    site = Site({PAGE: HTML}, robots=None)
    assert fetcher_for(site).get(PAGE).status == 200


@pytest.mark.parametrize("robots_status", [401, 403, 500, 503])
def test_unreadable_robots_file_means_not_allowed(robots_status):
    site = Site({PAGE: HTML}, robots=robots_status)
    with pytest.raises(RobotsDisallowed):
        fetcher_for(site).get(PAGE)
    assert site.page_urls() == []


def test_robots_is_read_once_per_host():
    other = "https://records.example.gov/notices/2"
    site = Site({PAGE: HTML, other: HTML})
    f = fetcher_for(site)
    f.get(PAGE)
    f.get(other)
    assert site.urls().count("https://records.example.gov/robots.txt") == 1


def test_there_is_no_switch_to_skip_robots():
    import inspect

    params = set(inspect.signature(Fetcher.__init__).parameters)
    assert not {p for p in params if "robot" in p.lower() or "ignore" in p.lower()}


# --- pacing -------------------------------------------------------------------------------------


def test_requests_to_one_host_are_spaced_out():
    other = "https://records.example.gov/notices/2"
    site = Site({PAGE: HTML, other: HTML})
    clock = FakeClock()
    f = fetcher_for(site, clock)
    f.get(PAGE)
    f.get(other)
    # robots.txt, page, page: two waits of the full interval.
    assert clock.sleeps == [base.DEFAULT_MIN_INTERVAL, base.DEFAULT_MIN_INTERVAL]


def test_a_longer_crawl_delay_in_robots_is_honored():
    site = Site({PAGE: HTML}, robots="User-agent: *\nCrawl-delay: 30\nAllow: /")
    clock = FakeClock()
    fetcher_for(site, clock).get(PAGE)
    assert clock.sleeps == [30.0]


# --- failures -----------------------------------------------------------------------------------


@pytest.mark.parametrize("status", [401, 403, 451])
def test_a_refusal_is_never_retried(status):
    site = Site({PAGE: httpx.Response(status)})
    with pytest.raises(Blocked):
        fetcher_for(site).get(PAGE)
    assert site.page_urls() == [PAGE]


def test_server_errors_are_retried_with_backoff():
    site = Site({PAGE: [httpx.Response(503), httpx.Response(502), HTML]})
    clock = FakeClock()
    assert fetcher_for(site, clock).get(PAGE).status == 200
    assert site.page_urls() == [PAGE] * 3
    assert 10.0 in clock.sleeps and 20.0 in clock.sleeps  # backoff doubles


def test_gives_up_after_three_attempts():
    site = Site({PAGE: httpx.Response(500)})
    with pytest.raises(FetchError) as excinfo:
        fetcher_for(site).get(PAGE)
    assert not isinstance(excinfo.value, Blocked)
    assert site.page_urls() == [PAGE] * 3


def test_retry_after_is_honored():
    site = Site({PAGE: [httpx.Response(429, headers={"Retry-After": "60"}), HTML]})
    clock = FakeClock()
    fetcher_for(site, clock).get(PAGE)
    assert 60.0 in clock.sleeps


def test_repeated_429_counts_as_a_block():
    site = Site({PAGE: httpx.Response(429)})
    with pytest.raises(Blocked):
        fetcher_for(site).get(PAGE)


def test_network_errors_are_retried_then_reported():
    def boom(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("timed out", request=request)

    site = Site({PAGE: boom})
    with pytest.raises(FetchError):
        fetcher_for(site).get(PAGE)
    assert site.page_urls() == [PAGE] * 3


def test_a_missing_page_is_an_ordinary_error():
    with pytest.raises(FetchError) as excinfo:
        fetcher_for(Site()).get(PAGE)
    assert not isinstance(excinfo.value, Blocked | RobotsDisallowed)


def test_oversized_body_is_refused(monkeypatch):
    monkeypatch.setattr(base, "MAX_BODY_BYTES", 1000)
    site = Site({PAGE: httpx.Response(200, content=b"x" * 5000)})
    with pytest.raises(TooLarge):
        fetcher_for(site).get(PAGE)


# --- redirects ----------------------------------------------------------------------------------


def test_redirects_are_followed_and_recorded():
    target = "https://records.example.gov/notices/final"
    site = Site({PAGE: httpx.Response(302, headers={"Location": "/notices/final"}), target: HTML})
    result = fetcher_for(site).get(PAGE)
    assert (result.url, result.final_url) == (PAGE, target)


def test_robots_is_checked_on_the_host_a_redirect_leads_to():
    elsewhere = "https://cdn.example.net/file"

    def handler_robots(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="User-agent: *\nDisallow: /")

    site = Site(
        {
            PAGE: httpx.Response(301, headers={"Location": elsewhere}),
            elsewhere: HTML,
            "https://cdn.example.net/robots.txt": handler_robots,
        }
    )
    with pytest.raises(RobotsDisallowed):
        fetcher_for(site).get(PAGE)
    assert elsewhere not in site.urls()


def test_redirect_loops_end():
    site = Site({PAGE: httpx.Response(302, headers={"Location": PAGE})})
    with pytest.raises(FetchError):
        fetcher_for(site).get(PAGE)


# --- caching ------------------------------------------------------------------------------------


def test_unchanged_documents_are_not_downloaded_again():
    def conditional(request: httpx.Request) -> httpx.Response:
        if request.headers.get("if-none-match") == '"v1"':
            return httpx.Response(304)
        return httpx.Response(200, html="<html><body>v1</body></html>", headers={"ETag": '"v1"'})

    site = Site({PAGE: conditional})
    f = fetcher_for(site)
    first = f.get(PAGE)
    second = f.get(PAGE)
    assert (first.status, first.not_modified, first.etag) == (200, False, '"v1"')
    assert (second.status, second.not_modified, second.body) == (304, True, b"")
    assert f.validators == {PAGE: ('"v1"', None)}


# --- robots.txt wildcards -----------------------------------------------------------------------

# The shape of a real state agency file: everything in a folder is closed, then some folders
# are opened again. The longest matching rule has to win.
WILDCARD_ROBOTS = """\
User-agent: *
Disallow: /*/
Allow: /taxes/
Allow: /economy/
Disallow: /fmtemp/
Disallow: /taxes/*.xls$
"""


@pytest.mark.parametrize(
    "path,allowed",
    [
        ("/taxes/data-centers/data-center-lists.php", True),
        ("/economy/development/search-tools/sb1340/", True),
        ("/internal/reports/page.php", False),  # closed by the wildcard rule
        ("/fmtemp/file.txt", False),
        ("/taxes/files/list.xls", False),  # the longer, more specific rule wins
        ("/taxes/files/list.xlsx", True),  # $ anchors the end, so .xlsx is not .xls
        ("/index.php", True),  # top level, no folder
    ],
)
def test_wildcard_and_longest_match_rules(path, allowed):
    url = "https://records.example.gov" + path
    site = Site({url: HTML}, robots=WILDCARD_ROBOTS)
    if allowed:
        assert fetcher_for(site).get(url).status == 200
    else:
        with pytest.raises(RobotsDisallowed):
            fetcher_for(site).get(url)
        assert site.page_urls() == []
