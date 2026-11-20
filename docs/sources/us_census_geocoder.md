# Census Bureau geocoder

- Source id: `us_census_geocoder`
- Page: https://geocoding.geo.census.gov/geocoder/
- Interface guide: https://geocoding.geo.census.gov/geocoder/Geocoding_Services_API.html, dated February 2026
- Checked: November 20, 2026
- Result: **allowed.** A lookup service the pipeline asks one question at a time. Not a collector.
- Client: `pipeline/geocode.py`
- Fixtures: `tests/fixtures/us_census_geocoder/`, three real answers

## What was verified

- **It is offered for programs.** The start page says the geocoder gives interactive and programmatic access. The guide says it is for developers inside the bureau and for the general public.
- **No key.** No request needs one.
- **Robots rules.** `https://geocoding.geo.census.gov/robots.txt` answers 404. The host publishes no rules.
- **Limits.** The guide and the bureau's question and answer sheet, dated May 15, 2024, state one limit: 10,000 records in a batch file. Neither gives a limit on single requests. The radar does not use batch files.
- **Terms.** Neither page states terms of use for the geocoder. Census Bureau data is a work of the federal government.
- **Accuracy, as the bureau states it.** The geocoder places an address along a street's range of addresses. The coordinates are approximate.

## What the radar asks

Two questions, each a single GET request.

1. **Where is this address?** `geographies/onelineaddress`. The answer gives the matched address, a point and the county that holds the point.
2. **Which county holds this point?** `geographies/coordinates`.

Both ask for the current benchmark, the current vintage and the Counties layer only.

## Rules the client keeps

- **Never send a record that names a person.** The address goes in the request's query string. The pipeline checks the named party first and sends only records of companies and public bodies.
- **The county comes from the point.** The bureau's own headquarters has a Washington, DC mailing address and stands in Prince George's County, Maryland. The saved answer shows it.
- **More than one match is ambiguous.** The client then gives no coordinates. It gives a county only if every match is in the same one.
- **Every answer is archived** with its address, retrieval time and hash, like any document. The same question is answered from the archive after that.
- Requests go through the shared fetcher: one every 5 seconds, with the radar's user agent. A refusal stops the lookup.
- If an answer stops looking like the saved ones, the lookup fails. Nothing is guessed.

## Verified live

Three requests on November 20, 2026, through `collectors.capture`:

- The guide's example address. One match, in county 24033.
- A point on the courthouse square in Granbury. County 48221, Hood.
- An address that does not exist. An empty list of matches.

## What was not verified

- Any limit on the rate of single requests. None is published. The fetcher's pace is far below anything a public service would notice.
- How the service answers when it is busy or down. The client treats anything but the documented JSON as a failure.
- An address with more than one match. None was found to save. That test uses the saved answer with its match doubled.
- How often an answer changes. The bureau updates its address data twice a year. Archived answers have no expiry yet.
- A run from GitHub's servers.

## Who uses it today

No feed needs it yet. TWDB well reports carry a county and coordinates. The TCEQ lists carry neither an address nor a county. It is built for the notice and agenda feeds, which give street addresses.
