# FracTracker data centers tracker

- Source id: `us_fractracker`
- Layer: baseline of known sites
- Page: https://www.fractracker.org/data-centers
- Checked: November 19, 2026, and again on November 22, 2026
- Method: manual. **Since November 22, 2026 nothing is taken from it by program at all.** See "Read again on November 22, 2026".
- Result: **restricted.** Its terms now ask for agreement and Esri's terms bar harvesting from the map's service.

## Read again on November 22, 2026

The backtest in milestone M9 needs a list of known projects. Before taking any record I read the terms again, and Esri's for the first time. Both stand in the way.

**FracTracker's terms have changed since November 19.**

- The sentence that the data can be downloaded and shared freely for non-commercial use with credit is gone from the page.
- The map now opens on a notice of six terms and a box to tick: "I agree to the above terms and conditions". I did not tick it.
- The terms say FracTracker keeps all rights in the data compilation. Use must be consistent with and supportive of its mission, and it alone decides whether a use is. Any public use must cite FracTracker Alliance. Using the site is agreeing to its Terms of Service.
- The Terms of Service, last updated November 20, 2025, ask anyone unsure whether a use fits the mission to write first. The Data Statement asks to be listed as co-author where published work relies heavily on its data.
- **The map links a spreadsheet to view and download the data.** That is the channel FracTracker offers. I did not open it.

**Esri's terms.**

- ArcGIS Online's terms of use say public content is subject to the content owner's terms of use, and that a user must abide by them. That points back to FracTracker's terms.
- Esri's Web Site and Service Terms of Use, section 2.3, bar reaching services other than through a standard web browser or Esri products, and bar harvesting information from the service by hand or systematically. Whether "the Service" there covers a layer a customer hosts is not something I can settle.
- **So no record is taken from the map's service by program.** The counts below and the counts of November 22 were taken that way, by a script and not a browser: six requests on November 19 and six on November 22. I read that now as against section 2.3. No more are made.

**Counts taken on November 22, before this reading.** 98 records in the 30 test counties, in 21 of them: 41 proposed, 14 approved or under construction, 4 expanding, 38 operating and 1 cancelled. Nine of the 30 counties have no record. The layer holds no date a project became public. It holds the dates its own record was made and updated, an expected date online and up to eight source links.

**For the owner.** Taking FracTracker's records, even from the spreadsheet it offers, means agreeing to its terms for the organization. That is the owner's to do. The terms invite a letter first.

## The owner agreed to the terms, November 22, 2026

- The owner told me the same day that the terms are agreed to for the organization.
- **Nothing has been taken since.** The agreement opens one channel: the spreadsheet FracTracker links from the map. It has not been opened. Taking it waits for the owner's word.
- **The map's service stays closed to programs.** Esri's section 2.3 is Esri's rule, and FracTracker's terms do not lift it.
- What the terms bind the project to: use that fits FracTracker's mission as it judges, FracTracker Alliance cited in anything public, and co-authorship offered where published work relies heavily on its data.
- A letter to FracTracker is drafted, not sent. It goes to `info@fractracker.org`. The Terms of Service name that address for questions on whether a use fits the mission, read on November 22, 2026. The contact page lists the same address for general inquiries.

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
- Esri's ArcGIS Online terms of use were not read on November 19. They were read on November 22, 2026: see above.
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
