# TCEQ Permit Search Portal

- Source id: `tx_tceq_air_pending`
- Site: https://permit-search.tceq.texas.gov/
- Checked: November 19, 2026, in a browser
- Result: **nothing found that restricts automated access. The feed stays manual until the owner picks a method and fixtures are saved.**

The older static lists are a separate source. See [tx_tceq_air_pending_legacy.md](tx_tceq_air_pending_legacy.md).

## What was verified

- **No login.** The search form, the map and the result list all load for an anonymous visitor.
- **No terms of its own.** The page shows no terms, no notice to accept and no captcha. The only "Terms" link on the page belongs to the Google map.
- **It adopts the TCEQ web policies.** The footer links to the Disclaimer and Web Policies pages on `www.tceq.texas.gov`. Those are the pages read for the legacy lists: site content is considered public domain unless noted, TCEQ asks for acknowledgment, and TCEQ blocks traffic that looks malicious or threatens availability. None of them mentions robots, crawlers or scraping.
- **No robots rules.** The host answers `/robots.txt` with the application shell, as noted earlier. Our fetcher reads that as a site that publishes no rules.
- **Contacts on the page.** Report errors: registry@tceq.texas.gov. Other feedback: info@tceq.texas.gov.

## How the search works

- **Area.** Three choices: a location, "Near Me" or "All of Texas". A location is an address, city, zip or county, filled in by a Google place lookup. The search is then a circle around that point, with a radius from 1 to 60 miles. It is not a county boundary.
- **Status.** New Application, Issued Permit and Renewal/Amendment. All three are checked by default.
- **Type.** Air, Waste and Water, each with sub-types. Air has two: Air New Source and Air Operating.
- **Keyword.** One box for a business name, an activity or a permit number.
- **No date filter.** The form has none.
- **Results.** A map with counts and a list of cards, five to a page. A card shows the site name, a permit or registration number, the program, the status, the location and a one-line overview, with a "More details" link. The cards seen showed no date.
- **One search was run:** Hood County, a 15 mile radius set by the page, every status and type. It returned 1,386 records, 670 of them air.
- **Data calls.** The search made three POST requests on the same host: `/psp-webservices/v1/search/LatLong`, `/psp-webservices/v1/search/permitsWithPages` and `/psp-webservices/v1/filters/count`. The place lookup goes to Google.

## Notes for any later collector

- The page gets its data with POST requests. The collector base class makes GET requests only. A collector needs either a browser or support for the page's own search calls.
- With no date filter, new applications are found by comparing each day's New Application list with the day before.
- A radius search does not follow county lines. A county has to be matched from the location text on each record.
- Water has a sub-type for on-site sewage facilities, which can be private households. A collector takes air permits only and does not store other types.
- The lookup step depends on Google's place service, which has its own terms. A collector should send coordinates it already holds for each county and skip that step.

## Options for the owner

1. Build the collector on the page's own search calls, one statewide or per-county request a day for new air applications. Nothing read so far bars it.
2. Run a browser instead. It is slower and heavier, and it loads Google's map each time.
3. Before either, send TCEQ a short note at the feedback address saying what we plan and asking if a bulk export exists. The policies do not require it.

## Not verified

- The request and response bodies of the three data calls, the page size they allow and whether they accept a request without the place lookup.
- What "More details" shows, and whether any record carries a received date.
- Whether the "All of Texas" search returns every new application in one list.
- Whether on-site sewage records name private individuals.
- How TCEQ treats repeated daily requests to the search service. The policies say only that it blocks traffic that threatens availability.
- How the governor's September 21, 2026 directive changes what the portal shows.
