"""Reading where a TCEQ application file says its site is.

The texts here are synthetic, built on the wording and line order of two real application files
read on November 20, 2026. Those files run to hundreds of pages and name company and agency
staff, so they are not saved as fixtures.
"""

from __future__ import annotations

from pipeline.counties import CountyIndex
from pipeline.extract import extract
from pipeline.signals import Doc, Rules, tceq_air_pending
from pipeline.tceq_applications import read_application

from .helpers import make_docx, make_pdf, make_portfolio

TX = CountyIndex.for_state("TX")

# TCEQ's online form, as a Title V application carries it.
FORM = """Texas Commission on Environmental Quality
Title V Existing
9999
Site Information (Regulated Entity)
What is the name of the permit area to be EXAMPLE DATA CENTER
authorized?
Does the site have a physical address? Yes
Physical Address
Number and Street 100 EXAMPLE PKWY
City MIDLOTHIAN
State TX
ZIP 76065
County ELLIS
Latitude (N) (##.######) 32.443055
Longitude (W) (-###.######) 97.059166
Primary SIC Code 0
Primary NAICS Code 518210
What is the primary business of this entity? DATA CENTER
Customer (Applicant) Information
Legal Name EXAMPLE DATA LLC"""

# The head of a TCEQ letter, as both kinds of file carry it.
LETTER = """Permit Number: O9999
Example Data LLC
Example Data Center
Midlothian, Ellis County
Regulated Entity Number: RN100000000
Customer Reference Number: CN600000000"""

REVIEW = (
    "Regulated Entity No.: ................................ RN100000000\n"
    "County: ................................................. Armstrong Region: ........ 1"
)


def test_the_form_gives_the_county_address_and_coordinates():
    site = read_application(FORM, TX)
    assert site.status == "read"
    assert (site.county, site.county_fips, site.in_scope) == ("Ellis", "48139", True)
    assert (site.street, site.city, site.zip) == ("100 EXAMPLE PKWY", "MIDLOTHIAN", "76065")
    assert (site.naics, site.primary_business) == ("518210", "DATA CENTER")
    assert site.evidence == ("County ELLIS",)


def test_a_west_longitude_typed_without_its_minus_sign_is_read_as_west():
    site = read_application(FORM, TX)
    assert (site.lon, site.lat) == (-97.059166, 32.443055)
    signed = FORM.replace("(-###.######) 97.059166", "(-###.######) -97.059166")
    assert read_application(signed, TX).lon == -97.059166


def test_coordinates_outside_texas_are_not_kept():
    site = read_application(FORM.replace("32.443055", "52.443055"), TX)
    assert (site.lon, site.lat) == (None, None) and site.county == "Ellis"


def test_the_letter_head_gives_the_county_and_city():
    site = read_application(LETTER, TX)
    assert (site.status, site.county, site.city) == ("read", "Ellis", "Midlothian")
    assert site.evidence == ("Midlothian, Ellis County",)
    assert site.street is None and site.lon is None


def test_the_review_sheet_gives_a_county_outside_the_test_set():
    site = read_application(REVIEW, TX)
    assert (site.status, site.county, site.county_fips, site.in_scope) == (
        "read", "Armstrong", "48011", False,
    )  # fmt: skip
    assert site.evidence == ("County Armstrong",)


def test_every_line_must_name_the_same_county():
    agree = read_application(FORM + "\n\n" + LETTER, TX)
    assert agree.status == "read" and agree.county == "Ellis"
    assert agree.evidence == ("County ELLIS", "Midlothian, Ellis County")

    differ = read_application(FORM + "\n\n" + LETTER.replace("Ellis", "Dallas"), TX)
    assert differ.status == "ambiguous"
    assert (differ.county, differ.county_fips) == (None, None)
    assert differ.counties_read == ("Dallas", "Ellis")


def test_counties_named_in_passing_are_not_read():
    text = (
        "The Honorable Example Person\nCounty Judge\nCounty Courthouse\n"
        "Units of the same kind operate in Harris County and in Wise County.\n"
        "A copy is at the Hood County library.\nCounty PM County"
    )
    site = read_application(text, TX)
    assert site.status == "no_county" and site.evidence == ()


def test_a_place_that_is_not_a_texas_county_is_not_read():
    site = read_application(LETTER.replace("Ellis County", "Example County"), TX)
    assert site.status == "no_county"


def test_only_address_lines_are_kept_never_the_people_in_the_file():
    text = (
        FORM + "\nResponsible Official Contact\nPrefix MR\nFirst INVENTED\nLast PERSON\n"
        "Phone 555-0100\nEmail invented.person@example.com"
    )
    kept = str(read_application(text, TX).as_dict())
    assert "INVENTED" not in kept and "555-0100" not in kept and "example.com" not in kept


# --- the file itself ----------------------------------------------------------------------------


def test_a_plain_application_pdf_is_read():
    body = make_pdf([FORM, "Page two"])
    site = read_application(extract(body, "application/pdf").text, TX)
    assert (site.status, site.county) == ("read", "Ellis")


def test_an_application_inside_a_pdf_portfolio_is_read():
    cover = "If this page is the only one that appears, download the document."
    body = make_portfolio(
        cover,
        {
            "1-404507-ac.pdf": make_pdf(
                ["Cover email", LETTER, REVIEW.replace("Armstrong", "Ellis")]
            ),
            "20260130-01_workbook.xlsx": b"PK\x03\x04 not a real workbook",
            "notice.docx": make_docx(["Amended public notice"]),
        },
    )
    out = extract(body, "application/pdf")
    assert out.kind == "pdf" and out.pages == 1
    assert out.text.startswith(cover)
    assert "File: 1-404507-ac.pdf\nCover email" in out.text
    assert "File: notice.docx\nAmended public notice" in out.text
    read = {m["name"]: (m["read"], m.get("pages"), m.get("why")) for m in out.members}
    assert read["1-404507-ac.pdf"] == (True, 3, None)
    assert read["notice.docx"][0] is True
    assert read["20260130-01_workbook.xlsx"][0] is False

    site = read_application(out.text, TX)
    assert (site.status, site.county, site.city) == ("read", "Ellis", "Midlothian")


def test_a_portfolio_inside_a_portfolio_is_not_opened():
    inner = make_portfolio("Inner cover", {"deep.pdf": make_pdf([LETTER])})
    out = extract(make_portfolio("Outer cover", {"inner.pdf": inner}), "application/pdf")
    assert "Inner cover" in out.text and "Ellis County" not in out.text


def test_text_never_carries_a_nul_character():
    # A real application file had one in its text layer, and the database refuses them.
    from pipeline.extract import _tidy

    assert _tidy("County\x00 ELLIS\n\x00\nNext") == "County ELLIS\nNext"
    out = extract(b"<html><body><p>County\x00 ELLIS</p></body></html>", "text/html")
    assert "\x00" not in out.text


def test_a_pdf_with_nothing_embedded_reads_as_before():
    out = extract(make_pdf(["One", "Two"]), "application/pdf")
    assert (out.text, out.pages, out.members) == ("One\n\nTwo", 2, ())


def test_an_application_file_makes_no_signal_and_is_not_an_error():
    import datetime as dt

    url = "https://www.tceq.texas.gov/assets/public/permitting/air/reports/applications/1-tc.pdf"
    doc = Doc(
        "tx_tceq_air_pending_legacy", url, dt.datetime(2026, 11, 20, tzinfo=dt.UTC), "0" * 64,
        FORM, {}, make_pdf([FORM]),
    )  # fmt: skip
    out = tceq_air_pending(doc, Rules(listings={}))
    assert out.drafts == [] and out.records == 0
