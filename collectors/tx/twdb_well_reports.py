"""Texas Water Development Board well reports: an extract, not the file.

The board publishes every well report drillers have submitted as one zip file, rebuilt each
night. It is about 145 MB. About four reports in ten are household wells, with a person's name
and home address.

The radar does not keep that file. Each run downloads it, reads the main table and keeps only
the rows that

- are in one of the test counties,
- are not domestic or stock wells, and
- were submitted in the last two years.

From each row it keeps the columns in KEEP. The owner's mailing address and everything about
the driller are left out. What is stored is that extract, with the address, retrieval time,
size and hash of the board's file. The owner approved this on November 20, 2026, as a
departure from the rule that the original is archived.

Rows that pass can still name a person, for example as the owner of an irrigation well. A later
step must hold those back before anyone outside the organization sees them.

If the table's columns change, the run stops with LayoutChanged and stores nothing.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import io
import zipfile
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field

from collectors.base import Collector, FetchResult, LayoutChanged, Reduced
from pipeline.config import load_control_counties, load_counties

URL = "https://www.twdb.texas.gov/groundwater/data/SDRDownload.zip"
TABLE = "SDRDownload/WellData.txt"
ENCODING = "cp1252"  # the board's tables are Windows text, not UTF-8
WINDOW_DAYS = 730
HOUSEHOLD_USES = frozenset({"Domestic", "Stock"})

# The table's columns as read on November 20, 2026. A change here stops the run.
COLUMNS = (
    "WellReportTrackingNumber", "DateSubmitted", "OwnerName", "OwnerAddress1", "OwnerAddress2",
    "OwnerCity", "OwnerState", "OwnerZip", "OwnerOtherCountry", "OwnerCountry", "OwnerWellNumber",
    "County", "WellAddress1", "WellAddress2", "WellCity", "WellZip", "WellLocationDescription",
    "NumberOfWellsDrilled", "Elevation", "CoordDDLat", "Dlat", "Mlat", "Slat", "CoordDDLong",
    "Dlong", "Mlong", "Slong", "GridNumber", "LocationVerifiedByDriller", "TypeOfWork",
    "TypeOfWorkOtherDesc", "OriginalWellReportTrackingNumber", "ProposedUse",
    "ProposedUseOtherDesc", "TCEQApprovedPlans", "PWSNo", "DrillingStartDate", "DrillingEndDate",
    "SealMethod", "SealMethodOtherDesc", "DistanceToSepticOrOtherContamination",
    "DistanceToSepticTank", "DistanceToPropertyLine", "DistanceVerificationMethod",
    "ApprovedByVariance", "SealedByDriller", "SealedByName", "SurfaceCompletion",
    "SurfaceCompletionOtherDesc", "CompletedByDriller", "PumpType", "PumpTypeOtherDesc",
    "PumpDepth", "ChemicalAnalysis", "InjuriousWater", "CompanyName", "DrillerName",
    "DrillerSigned", "ApprenticeSigned", "Comments", "PluggedWithin48Hrs",
    "PluggingReportTrackingNumber", "KnownLocationError", "HorizontalDatumType",
    "DrillerAddress1", "DrillerAddress2", "DrillerCity", "DrillerState", "DrillerZip",
    "DrillerOtherCountry", "DrillerCountry", "LicenseNumber", "ApprenticeRegistrationNumber",
)  # fmt: skip

# What is kept from a row. No owner mailing address and nothing about the driller.
KEEP = (
    "WellReportTrackingNumber", "DateSubmitted", "OwnerName", "OwnerWellNumber", "County",
    "WellAddress1", "WellAddress2", "WellCity", "WellZip", "WellLocationDescription",
    "NumberOfWellsDrilled", "CoordDDLat", "CoordDDLong", "TypeOfWork", "TypeOfWorkOtherDesc",
    "OriginalWellReportTrackingNumber", "ProposedUse", "ProposedUseOtherDesc", "PWSNo",
    "DrillingStartDate", "DrillingEndDate", "Comments", "PluggingReportTrackingNumber",
)  # fmt: skip

_INDEX = {name: i for i, name in enumerate(COLUMNS)}
_KEEP_AT = tuple(_INDEX[name] for name in KEEP)
_NUMBER, _DATE, _COUNTY, _USE = (
    _INDEX["WellReportTrackingNumber"],
    _INDEX["DateSubmitted"],
    _INDEX["County"],
    _INDEX["ProposedUse"],
)


@dataclass
class Extract:
    """The rows kept from one copy of the table, and counts of the rows that were not."""

    since: dt.date
    rows: list[tuple[str, ...]] = field(default_factory=list)
    rows_total: int = 0
    rows_other_county: int = 0
    rows_household: int = 0
    rows_too_old: int = 0
    rows_undated: int = 0
    rows_malformed: int = 0
    malformed_tracking_numbers: list[str] = field(default_factory=list)

    def body(self) -> bytes:
        """The extract as UTF-8 text: one header line, then one line per row, oldest first."""
        ordered = sorted(self.rows, key=lambda row: (row[1], row[0].zfill(12)))
        lines = ["|".join(KEEP), *("|".join(row) for row in ordered)]
        return ("\n".join(lines) + "\n").encode("utf-8")

    def counts(self) -> dict:
        return {
            "since": self.since.isoformat(),
            "rows_total": self.rows_total,
            "rows_kept": len(self.rows),
            "rows_other_county": self.rows_other_county,
            "rows_household": self.rows_household,
            "rows_too_old": self.rows_too_old,
            "rows_undated": self.rows_undated,
            "rows_malformed": self.rows_malformed,
            "malformed_tracking_numbers": self.malformed_tracking_numbers,
        }


def _lines(stream: io.BufferedIOBase) -> Iterator[str]:
    """Lines of the table. Only CRLF ends a row: a comment can hold a bare line feed."""
    pending = ""
    while chunk := stream.read(1 << 20):
        pending += chunk.decode(ENCODING, errors="replace")
        *whole, pending = pending.split("\r\n")
        yield from whole
    if pending:
        yield pending


def _one_line(value: str) -> str:
    return " ".join(value.split()) if ("\n" in value or "\r" in value) else value.strip()


def reduce_table(lines: Iterable[str], counties: frozenset[str], since: dt.date) -> Extract:
    """Keep the rows the radar may hold. See the module text for the rule."""
    rows = iter(lines)
    header = tuple(next(rows, "").lstrip("﻿").split("|"))
    if header != COLUMNS:
        raise LayoutChanged(
            f"the well table has {len(header)} columns that do not match the {len(COLUMNS)} "
            "expected"
        )
    out = Extract(since)
    cutoff = since.isoformat()
    for line in rows:
        if not line:
            continue
        out.rows_total += 1
        cells = line.split("|")
        if len(cells) != len(COLUMNS):
            # A stray pipe inside a field. Which field cannot be told, so the row is not used.
            out.rows_malformed += 1
            if len(out.malformed_tracking_numbers) < 50:
                out.malformed_tracking_numbers.append(cells[_NUMBER][:20])
            continue
        if cells[_COUNTY].strip() not in counties:
            out.rows_other_county += 1
        elif cells[_USE].strip() in HOUSEHOLD_USES:
            out.rows_household += 1
        elif len(submitted := cells[_DATE].strip()[:10]) != 10 or submitted[4] != "-":
            out.rows_undated += 1
        elif submitted < cutoff:
            out.rows_too_old += 1
        else:
            out.rows.append(tuple(_one_line(cells[i]) for i in _KEEP_AT))
    return out


def reduce_zip(body: bytes, counties: frozenset[str], since: dt.date) -> Extract:
    try:
        archive = zipfile.ZipFile(io.BytesIO(body))
    except zipfile.BadZipFile as exc:
        raise LayoutChanged("the download is not a zip file") from exc
    with archive:
        if TABLE not in archive.namelist():
            raise LayoutChanged(f"the zip file has no {TABLE}")
        with archive.open(TABLE) as stream:
            return reduce_table(_lines(stream), counties, since)


class TwdbWellReports(Collector):
    """One download. The file is reduced to an extract and is not kept."""

    source_id = "tx_twdb_well_reports"

    def __init__(self, today: dt.date | None = None, counties: Iterable[str] | None = None) -> None:
        self.today = today or dt.datetime.now(dt.UTC).date()
        self.counties = frozenset(
            counties if counties is not None else (c.name for c in load_counties("TX").counties)
        )
        # Rows submitted before this day are left out.
        self.since = self.today - dt.timedelta(days=WINDOW_DAYS)
        self._made: dict[str, Reduced] = {}

    @classmethod
    def history(cls, since: dt.date, today: dt.date | None = None) -> TwdbWellReports:
        """Reports submitted from a day on, in the test and the control counties. For the backtest.

        Still one download, and the same rows are left out: household wells, the mailing
        address and the driller.
        """
        names = [c.name for c in load_counties("TX").counties]
        names += [c.name for c in load_control_counties("TX").counties]
        collector = cls(today=today, counties=names)
        collector.since = since
        return collector

    def urls(self) -> list[str]:
        return [URL]

    def reduce(self, result: FetchResult) -> Reduced:
        if result.url not in self._made:
            extract = reduce_zip(result.body, self.counties, self.since)
            meta = {**extract.counts(), "table": TABLE, "columns": list(KEEP)}
            self._made[result.url] = Reduced(extract.body(), "text/plain; charset=utf-8", meta)
        return self._made[result.url]

    def content_key(self, result: FetchResult) -> str:
        # The board rebuilds the file every night. The key is taken from the extract, so a
        # rebuild that changes nothing the radar keeps is not stored again.
        return hashlib.sha256(self.reduce(result).body).hexdigest()
