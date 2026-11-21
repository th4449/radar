"""Fill the LOCAL database with the test fixtures, so the reviewer app has something to show.

    uv run python scripts/dev_seed.py

For a developer's own machine only. It refuses any database that is not on this computer.
It stores the saved copies of real public records from tests/fixtures the way a collector
would, runs processing on them and then, as the database owner, moves every site into the
review queue so the screens can be tried. A real site enters the queue by its score.

It creates no accounts unless asked. Sign in through the app, then see web/README.md for how
the owner makes the first administrator.

    uv run python scripts/dev_seed.py --publish-sample

also publishes two sample alerts, so the public pages have something to show. For that it
makes one invented administrator, demo-admin@example.org, who confirms the two sites and
publishes the alerts through the same rules the app uses. The alert text is marked as a sample.
"""

from __future__ import annotations

import datetime as dt
import os
import sys
from pathlib import Path
from urllib.parse import urlsplit

import psycopg

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

import json  # noqa: E402
import uuid  # noqa: E402

from collectors.base import FetchResult, LocalArchive, archive  # noqa: E402
from collectors.tx import comptroller_data_centers as comptroller  # noqa: E402
from collectors.tx import tceq_air_pending_legacy as tceq  # noqa: E402
from collectors.tx import twdb_well_reports as twdb  # noqa: E402
from pipeline import process  # noqa: E402
from pipeline.config import load_counties, load_sources  # noqa: E402
from pipeline.store import PostgresSink  # noqa: E402

DEFAULT_URL = "postgresql://postgres:postgres@127.0.0.1:55322/postgres"
DEMO_ADMIN = "demo-admin@example.org"


def publish_samples(conn: psycopg.Connection) -> int:
    """Confirm and publish two sites as an invented administrator. Local demo only."""
    found = conn.execute("select id from auth.users where email = %s", [DEMO_ADMIN]).fetchone()
    admin = found[0] if found else uuid.uuid4()
    if not found:
        conn.execute(
            "insert into auth.users (id, email, email_confirmed_at) values (%s, %s, now())",
            [admin, DEMO_ADMIN],
        )
        conn.execute(
            """insert into public.reviewers (user_id, display_name, agreed_terms_at, status, role)
               values (%s, 'Demo administrator', now(), 'approved', 'admin')""",
            [admin],
        )
    sites = conn.execute(
        """select id, label, county_fips from public.sites s
           where status = 'in_review'
             and not exists (select 1 from public.alerts a where a.site_id = s.id)
           order by score desc, id limit 2"""
    ).fetchall()
    claims = json.dumps({"sub": str(admin), "role": "authenticated"})
    for site_id, label, _county in sites:
        with conn.transaction():
            conn.execute("select set_config('request.jwt.claims', %s, true)", [claims])
            conn.execute("set local role authenticated")
            conn.execute(
                """insert into public.reviews (site_id, reviewer_id, decision, source_checked, note)
                   values (%s, %s, 'confirm', true, 'Sample review made by dev_seed.py.')""",
                [site_id, admin],
            )
            conn.execute(
                """insert into public.alerts (site_id, headline, body, published_at)
                   values (%s, %s, %s, now())""",
                [
                    site_id,
                    f"Sample alert: records name {label}",
                    "This is a sample made on a developer's machine to show how an alert page "
                    "looks. It is not a real alert and no reviewer checked it.\n\n"
                    "A real alert says here, in a reviewer's words, what each record shows.",
                ],
            )
    return len(sites)


FIXTURES = REPO / "tests" / "fixtures"


def main() -> int:
    url = os.environ.get("DATABASE_URL", DEFAULT_URL)
    if urlsplit(url).hostname not in ("127.0.0.1", "localhost"):
        print("refused: this script only fills a database on this computer", file=sys.stderr)
        return 2
    store = LocalArchive(Path(os.environ.get("RADAR_ARCHIVE_DIR", REPO / "archive")))
    sources = load_sources()
    when = dt.datetime.now(dt.UTC)

    wells = (FIXTURES / "tx_twdb_well_reports" / "welldata-sample.txt").read_bytes()
    counties = frozenset(c.name for c in load_counties("TX").counties)
    extract = twdb.reduce_table(
        wells.decode(twdb.ENCODING).split("\r\n"), counties, dt.date(2024, 11, 20)
    ).body()
    saved = [
        ("tx_comptroller_data_centers", comptroller.URL, "text/html",
         (FIXTURES / "tx_comptroller_data_centers" / "data-center-lists.html").read_bytes()),
        ("tx_tceq_air_pending_legacy", tceq.NSR, "text/html",
         (FIXTURES / "tx_tceq_air_pending_legacy" / "nsr-pending-permits.html").read_bytes()),
        ("tx_tceq_air_pending_legacy", tceq.TITLE_V, "text/html",
         (FIXTURES / "tx_tceq_air_pending_legacy" / "titlev-pending-permits.html").read_bytes()),
        ("tx_twdb_well_reports", twdb.URL, "text/plain", extract),
    ]  # fmt: skip

    with psycopg.connect(url, autocommit=True) as conn:
        sink = PostgresSink(conn)
        for source_id, address, content_type, body in saved:
            source = sources.by_id(source_id)
            run_id = sink.start_run(source, runner="dev-seed")
            result = FetchResult(address, address, 200, content_type, None, None, body, when)
            new = sink.save_document(archive(result, source, store))
            conn.execute(
                """update public.collector_runs
                   set finished_at = now(), status = 'ok', documents_seen = 1, documents_new = %s
                   where id = %s""",
                [int(new), run_id],
            )
        summary = process.run(conn, store, runner="dev-seed")
        moved = conn.execute(
            "update public.sites set status = 'in_review' where status = 'candidate'"
        ).rowcount
    print(f"processing: {summary.status}, {summary.signals_new} new signals")
    print(f"sites: {summary.detail['sites']}")
    print(f"moved {moved} sites into the review queue by hand, for the demo")
    if "--publish-sample" in sys.argv[1:]:
        with psycopg.connect(url, autocommit=True) as conn:
            print(f"published {publish_samples(conn)} sample alerts as {DEMO_ADMIN}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
