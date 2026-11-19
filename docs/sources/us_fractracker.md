# FracTracker data centers tracker

- Source id: `us_fractracker`
- Layer: baseline of known sites
- Page: https://www.fractracker.org/data-centers
- Checked: November 19, 2026
- Method: manual. A person pulls counts by hand about once a month. No scheduled job.

## What was verified

- **Terms.** The page says the data "can be downloaded and shared freely for non-commercial use with credit to FracTracker." This project is non-commercial. Every use must credit FracTracker Alliance.
- **Robots rules, fractracker.org.** `https://fractracker.org/robots.txt` reads `User-agent: *` and an empty `Disallow:`. Nothing is disallowed.
- **Robots rules, www.arcgis.com.** `https://www.arcgis.com/robots.txt` lists `User-agent: *` with no disallow lines.
- **Where the data lives.** The map is an ArcGIS web experience, item `5a4d072ad01449bba5698a80103fb909`, public. Its main web map points to a public feature layer, `data_centers_v4_agol_all`, on `services.arcgis.com`. The layer allows the Query operation only and returns at most 1,000 records per request.
- **Fields.** Each record has `state`, `county`, `city`, `lat`, `long`, `status`, `operator_name`, `tenant`, megawatt fields, `date_updated` and up to eight source links. The county field was filled in for all 230 Texas records.
- **Status values.** Operating, Expanding, Approved/Permitted/Under construction, Proposed, Suspended, Cancelled.
- **Size on the day checked.** 230 Texas records and 26 Michigan records.

## What was not verified

- `https://services.arcgis.com/robots.txt` returned 403 with the text "Invalid URL". That host publishes no robots file we could read.
- The ArcGIS items carry no license text of their own. The only terms found are the sentence on the FracTracker page.
- Esri's ArcGIS Online terms of use were not read. That is the reason this source stays manual.
- How often FracTracker updates the layer. The layer's last data edit was in November 2026.

## How we use it

- Counts and comparisons only. We do not republish FracTracker's records, and the raw data is not committed to this repository.
- Requests made on November 19, 2026: three item lookups, one layer description and two statistics queries, each a few seconds apart. They carried a user agent that named this project. The project contact address had not been set yet.

## Texas county recount, November 19, 2026

BUILD_PLAN.md section 10 asks for a count of facilities by county, to check the five counties added to the organization's 25.

Method: count records where `state = 'TX'`, grouped by `county`, keeping the four statuses that match the plan's wording (operating, under construction, planned and proposed): Operating, Expanding, Approved/Permitted/Under construction and Proposed. That is 223 of the 230 Texas records, in 77 counties.

Counties outside the organization's 25, by that count:

| Rank | County | Facilities | In the plan's five |
|---|---|---|---|
| 1 | Dallas | 27 | yes |
| 2 | Bexar | 26 | yes |
| 3 | Williamson | 13 | no |
| 4 | Collin | 11 | no |
| 5 | Tarrant | 9 | no |
| 6 | Medina | 6 | no |
| 6 | Travis | 6 | yes |
| 8 | Denton | 5 | no |
| 17 (tied) | Harris | 3 | yes |
| 54 (tied) | Taylor | 1 | yes |

**The top five differ from the plan.** FracTracker's top five outside the 25 are Dallas, Bexar, Williamson, Collin and Tarrant. The plan's five are Dallas, Taylor, Bexar, Travis and Harris. Two match.

Why the two trackers disagree, as far as the data shows:

- FracTracker holds 230 Texas records. The commercial tracker the plan used counts 59 in Dallas County alone, so it is counting many more facilities, most likely smaller colocation sites.
- FracTracker counts one record in Taylor County. A count of records does not measure size. A single campus counts the same as a single small facility.
- FracTracker shows 2 records in Hood County, where the research document reports at least eight pending projects. FracTracker undercounts in at least one county we know well.

**Decision, November 19, 2026.** The owner kept the plan's five: Dallas, Taylor, Bexar, Travis and Harris. `config/counties_tx.yaml` was not changed.

Data credit: FracTracker Alliance, U.S. Data Centers Tracker (2026), https://www.fractracker.org/data-centers.
