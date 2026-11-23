"""Meeting agendas of Texas governments that publish through Legistar.

Granicus publishes the Legistar Web API at webapi.legistar.com for reading a government's public
meeting records. This collector reads that API and nothing else. It never fetches the agenda
PDF: those sit on hosts whose robots files bar every agent. See
docs/sources/tx_agendas_legistar.md.

For each government that is cleared, one run makes:

  one request for the list of meetings from back_days ago onward, then
  one request for each meeting whose agenda is published and is new or changed since last run.

What is stored for a meeting is its agenda as the API gives it, cut down to the fields the
radar reads: the meeting's body, date and place and each item's number, file number, type,
title and note. Who moved, seconded or voted is dropped.

Which governments are read is not decided here. `cleared_clients` asks the agenda inventory:
the row must be confirmed by an independent check, the platform must be cleared and the
government's own terms must have nothing against it. See pipeline/agenda_checks.py.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
from collections.abc import Iterable
from dataclasses import dataclass
from typing import ClassVar
from urllib.parse import urlsplit

from collectors.base import Collector, FetchResult, LayoutChanged, Reduced, Sink
from pipeline.config import Source

API = "https://webapi.legistar.com/v1"
_CLIENT = re.compile(r"^[a-z0-9]+$")
_LIST = re.compile(r"^/v1/([a-z0-9]+)/events$")
_EVENT = re.compile(r"^/v1/([a-z0-9]+)/events/(\d+)$")
_SKIP = re.compile(r"[?&]\$skip=(\d+)")

# The fields kept from each agenda item. Movers, seconders and votes are left behind.
_ITEM_FIELDS = {
    "EventItemId": "id",
    "EventItemAgendaSequence": "sequence",
    "EventItemAgendaNumber": "number",
    "EventItemMatterFile": "file",
    "EventItemMatterType": "type",
    "EventItemMatterName": "name",
    "EventItemTitle": "title",
    "EventItemAgendaNote": "note",
}
_EVENT_FIELDS = {
    "EventId": "event_id",
    "EventBodyName": "body",
    "EventDate": "date",
    "EventTime": "time",
    "EventLocation": "location",
    "EventAgendaStatusName": "agenda_status",
    "EventAgendaLastPublishedUTC": "agenda_published",
    "EventLastModifiedUtc": "modified",
    "EventInSiteURL": "page",
}


@dataclass(frozen=True)
class Client:
    """One government on Legistar. `name` is its name in the API's addresses."""

    name: str
    government: str
    counties: tuple[str, ...]

    def __post_init__(self) -> None:
        if not _CLIENT.match(self.name):
            raise ValueError(f"not a Legistar client name: {self.name!r}")


def client_name(*addresses: str) -> str | None:
    """The client name in a government's Legistar address, such as roundrock.legistar.com."""
    for address in addresses:
        host = urlsplit(address).netloc.lower()
        if host.endswith(".legistar.com") and host != "webapi.legistar.com":
            name = host.removesuffix(".legistar.com")
            if _CLIENT.match(name):
                return name
    return None


def cleared_clients(today: dt.date | None = None, state: str = "TX") -> list[Client]:
    """The governments this collector may read today, from a state's agenda inventory."""
    from pipeline import agenda_checks, agenda_inventory

    today = today or dt.datetime.now(dt.UTC).date()
    checks = agenda_checks.Checks(agenda_checks.load_checks(state=state))
    clients: dict[str, Client] = {}
    for body in agenda_inventory.load_inventory(state=state):
        if body.platform != "legistar":
            continue
        if body.body_type not in agenda_inventory.GOVERNING:
            continue
        if not agenda_checks.collectable(body, checks, today, state=state):
            continue
        name = client_name(body.agenda_url, body.evidence)
        if name:
            clients[name] = Client(name, body.government, body.counties)
    return [clients[name] for name in sorted(clients)]


def events_url(client: str, since: dt.date, skip: int = 0) -> str:
    """The list of meetings from a day on. The API answers a thousand at a time."""
    return (
        f"{API}/{client}/events?$filter=EventDate+ge+datetime%27{since.isoformat()}%27"
        "&$orderby=EventDate" + (f"&$skip={skip}" if skip else "")
    )


def event_url(client: str, event_id: int) -> str:
    return f"{API}/{client}/events/{event_id}?EventItems=1&AgendaNote=1"


def _json(result: FetchResult) -> object:
    try:
        return json.loads(result.body)
    except ValueError as exc:
        raise LayoutChanged(f"not JSON: {exc}") from exc


def _text(value: object) -> str:
    return " ".join(str(value).split()) if value is not None else ""


def _day(value: object) -> str:
    """The date of an API timestamp such as 2026-11-19T00:00:00."""
    text = str(value or "")
    if not re.match(r"^\d{4}-\d{2}-\d{2}", text):
        raise LayoutChanged(f"not a date: {text!r}")
    return text[:10]


def reduce_event(data: object, client: Client) -> dict:
    """One meeting's agenda, cut down to what the radar reads."""
    if not isinstance(data, dict) or "EventId" not in data or "EventItems" not in data:
        raise LayoutChanged("a meeting without EventId or EventItems")
    items = data["EventItems"]
    if not isinstance(items, list):
        raise LayoutChanged("EventItems is not a list")
    event = {new: data.get(old) for old, new in _EVENT_FIELDS.items()}
    event["date"] = _day(event["date"])
    for key in ("body", "time", "location", "agenda_status"):
        event[key] = _text(event[key])
    kept = []
    for item in items:
        if not isinstance(item, dict):
            raise LayoutChanged("an agenda item that is not a record")
        row = {new: item.get(old) for old, new in _ITEM_FIELDS.items()}
        for key in ("number", "file", "type", "name", "title", "note"):
            row[key] = _text(row[key])
        kept.append(row)
    kept.sort(key=lambda row: (row["sequence"] is None, row["sequence"] or 0, row["id"] or 0))
    return {
        "platform": "legistar",
        "client": client.name,
        "government": client.government,
        "counties": list(client.counties),
        **event,
        "items": kept,
    }


class LegistarAgendas(Collector):
    """The list of meetings for each cleared government, then each new or changed agenda."""

    source_id = "tx_agendas_legistar"
    back_days: ClassVar[int] = 14
    # A first run on a large city meets many meetings at once. The rest wait for the next run.
    max_events_per_client: ClassVar[int] = 40
    max_urls: ClassVar[int] = 600
    # The API's own limit on one answer. A list that long has a next page.
    page_size: ClassVar[int] = 1000

    def __init__(
        self,
        clients: Iterable[Client] | None = None,
        today: dt.date | None = None,
        back_days: int | None = None,
    ) -> None:
        self.today = today or dt.datetime.now(dt.UTC).date()
        self.clients = {
            c.name: c for c in (cleared_clients(self.today) if clients is None else clients)
        }
        if back_days is not None:
            self.back_days = back_days
        self._known: dict[str, dict] = {}
        self._parsed: dict[str, object] = {}
        self.held_over: dict[str, int] = {}
        self._wanted: dict[str, int] = {}  # meetings asked for so far, by government

    @classmethod
    def history(
        cls,
        since: dt.date,
        today: dt.date | None = None,
        clients: Iterable[Client] | None = None,
    ) -> LegistarAgendas:
        """Every published agenda from a day on. One request a meeting, none held over.

        A stored meeting that has not changed is not asked for again, so a run that stops
        can be started again.
        """
        today = today or dt.datetime.now(dt.UTC).date()
        collector = cls(clients=clients, today=today, back_days=(today - since).days)
        collector.max_events_per_client = 1_000_000
        collector.max_urls = 20_000
        return collector

    # --- which addresses ---------------------------------------------------------------------

    def urls(self) -> list[str]:
        since = self.today - dt.timedelta(days=self.back_days)
        return [events_url(name, since) for name in self.clients]

    def _kind(self, url: str) -> tuple[str, Client, int | None] | None:
        parts = urlsplit(url)
        if parts.netloc != "webapi.legistar.com":
            return None
        listing, event = _LIST.match(parts.path), _EVENT.match(parts.path)
        found = listing or event
        if not found or found.group(1) not in self.clients:
            return None
        client = self.clients[found.group(1)]
        return ("list", client, None) if listing else ("event", client, int(event.group(2)))

    def _data(self, result: FetchResult) -> object:
        if result.url not in self._parsed:
            self._parsed[result.url] = _json(result)
        return self._parsed[result.url]

    def follow(self, result: FetchResult) -> Iterable[str]:
        kind = self._kind(result.url)
        if kind is None or kind[0] != "list":
            return ()
        client = kind[1]
        events = self._data(result)
        if not isinstance(events, list):
            raise LayoutChanged("the list of meetings is not a list")
        wanted: list[str] = []
        for event in events:
            if not isinstance(event, dict) or "EventId" not in event:
                raise LayoutChanged("a meeting without EventId")
            if not event.get("EventAgendaLastPublishedUTC"):
                continue  # no agenda is published for it yet
            url = event_url(client.name, int(event["EventId"]))
            # Stored already, and not changed since: nothing to ask for.
            if self._known.get(url, {}).get("event_modified") == event.get("EventLastModifiedUtc"):
                continue
            wanted.append(url)
        # The cap is for the whole government, across the pages of its list.
        room = max(0, self.max_events_per_client - self._wanted.get(client.name, 0))
        if len(wanted) > room:
            self.held_over[client.name] = self.held_over.get(client.name, 0) + len(wanted) - room
            wanted = wanted[:room]
        self._wanted[client.name] = self._wanted.get(client.name, 0) + len(wanted)
        if len(events) >= self.page_size:
            # A full answer. The next page is asked for after this page's meetings.
            skip = _SKIP.search(result.url)
            since = self.today - dt.timedelta(days=self.back_days)
            start = (int(skip.group(1)) if skip else 0) + len(events)
            wanted.append(events_url(client.name, since, skip=start))
        return wanted

    # --- what is stored ----------------------------------------------------------------------

    def reduce(self, result: FetchResult) -> Reduced | None:
        kind = self._kind(result.url)
        if kind is None:
            raise LayoutChanged(f"an address this collector did not ask for: {result.url}")
        what, client, _ = kind
        data = self._data(result)
        if what == "list":
            if not isinstance(data, list):
                raise LayoutChanged("the list of meetings is not a list")
            listing = [
                {
                    "event_id": e.get("EventId"),
                    "body": _text(e.get("EventBodyName")),
                    "date": _day(e.get("EventDate")),
                    "agenda_published": e.get("EventAgendaLastPublishedUTC"),
                    "modified": e.get("EventLastModifiedUtc"),
                }
                for e in data
                if isinstance(e, dict)
            ]
            body = {"platform": "legistar", "client": client.name, "meetings": listing}
            meta = {"record": "legistar_meetings", "client": client.name}
        else:
            body = reduce_event(data, client)
            meta = {
                "record": "legistar_agenda",
                "client": client.name,
                "government": client.government,
                "counties": list(client.counties),
                "event_id": body["event_id"],
                "event_date": body["date"],
                "event_modified": body["modified"],
                "items": len(body["items"]),
            }
        encoded = json.dumps(body, ensure_ascii=False, sort_keys=True, indent=1).encode()
        return Reduced(encoded, "application/json", meta)

    def content_key(self, result: FetchResult) -> str | None:
        reduced = self.reduce(result)
        return hashlib.sha256(reduced.body).hexdigest() if reduced else None

    # --- the run -----------------------------------------------------------------------------

    def run(self, *, source: Source, sink: Sink, **kwargs):
        # follow() needs to know what earlier runs stored, to skip meetings that did not change.
        self._known = sink.known(source)
        return super().run(source=source, sink=_WithDetail(sink, self._detail), **kwargs)

    def _detail(self) -> dict:
        detail: dict = {"governments": sorted(self.clients)}
        if self.held_over:
            detail["held_over"] = dict(self.held_over)
        return detail


class _WithDetail:
    """A sink that adds this collector's own notes to the run log as the run is closed."""

    def __init__(self, sink: Sink, detail) -> None:
        self._sink, self._extra = sink, detail

    def finish_run(self, run_id, summary) -> None:
        summary.detail.update(self._extra())
        self._sink.finish_run(run_id, summary)

    def __getattr__(self, name: str):
        return getattr(self._sink, name)
