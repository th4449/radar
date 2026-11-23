# Texas backtest

BUILD_PLAN.md milestone M9. Written by `python -m backtest.run` from the history the radar held on Nov 23, 2026. Do not edit by hand.

**Nothing here is a finding about a company or a place.** A signal is a dated public record that uses a term the radar looks for. The scores and the threshold are placeholders.

## In short

- **0 of 73 judged projects reached the review threshold of 40 before they were public.**
- **1 of 73 had any signal before the public date.** 0 of those could have been tied to the project by the everyday radar. The rest were tied here by the project's name in the record's words, which only the backtest can do.
- 4 more had a signal only on or after the public date.
- **The highest score any known project reached on any day is 7.5.** At 40, the radar would have sent none of them to a reviewer, before or after it was public.
- Median lead time over hits: none. There is no hit to measure.
- False alarms in the 11 control counties: 0. The history holds 0 signals there.

## What was judged

`known_projects_tx.csv` holds 128 projects. A project is judged when it has a public date after Jan 1, 2023, the day the history starts.

| Verdict | Projects | Meaning |
|---|---|---|
| hit | 0 | reached the review threshold before the public date |
| late | 0 | reached it on or after the public date |
| below_threshold | 1 | had a signal before the public date and never reached it |
| no_signal | 72 | had no signal before the public date |
| undated | 49 | not judged: no public date was found |
| before_history | 6 | not judged: public before the records begin |

## What the radar held

| Source | Documents | Records read | Signals | Held back |
|---|---|---|---|---|
| Agendas on Legistar | 3635 | 107102 | 1151 | 0 |
| Agenda files on governments' own sites | 1847 | 1784 | 231 | 0 |
| ERCOT planning group files | 433 | 372 | 78 | 0 |
| State well reports | 1 | 15986 | 49 | 17 |
| TCEQ pending air permits | 2 | 627 | 12 | 0 |

- 5316 dated agendas from 39 governments were read. A record is an agenda item, an agenda file, a well report, a planning file or a row of a permit list.
- 1521 signals in all. 77 carry no county and can sit on no site: the planning files that name no test county and every pending air permit.
- A record is held back when its named party may be a person. It makes no signal and is counted by its number.

## Projects that had a signal

| Project | County | Public | First signal seen | Days ahead | Signals | Peak score before public | Verdict | Tied by |
|---|---|---|---|---|---|---|---|---|
| `dallas-garland-digital-realty` | Dallas | Dec 2, 2022 | Jul 18, 2025 | -959 | 1 agenda item or file | 0 | before_history | the record names the project's company or code name |
| `archer-project-raptor` | Archer | none | Sep 22, 2025 | not judged | 3 agenda item or file | 1.5 | undated | the same project name or number |
| `milam-sb-energy` | Milam | May 12, 2025 | Oct 20, 2025 | -161 | 4 agenda item or file | 0 | no_signal | the record names the project's company or code name |
| `milam-riot-rockdale` | Milam | Jan 16, 2026 | Dec 8, 2025 | +39 | 7 agenda item or file | 4.5 | below_threshold | the record names the project's company or code name |
| `travis-tesla-giga-texas` | Travis | Oct 10, 2023 | May 4, 2026 | -937 | 13 well report | 0 | no_signal | the same company |
| `austin-cleanspark` | Austin | Oct 29, 2025 | May 11, 2026 | -194 | 1 agenda item or file | 0 | no_signal | the record names the project's company or code name |
| `bosque-cyrusone-thad-hill` | Bosque | Jul 30, 2025 | Jul 16, 2026 | -351 | 1 well report | 0 | no_signal | the same company |

Days ahead is the public date less the day the first signal could be seen. A minus sign means the signal came after the project was public.

## What was read near the projects that were judged

For each judged project: the agendas the radar held from its county, dated in the year before its public date. The city is one the project's row names in its place, which for a site outside any city is the nearest one.

| Agendas held | Judged projects | With a signal before public |
|---|---|---|
| the county's and the city's | 3 | 0 |
| the city's | 2 | 0 |
| the county's only | 7 | 1 |
| another government's only | 31 | 0 |
| none | 30 | 0 |

The well reports and the ERCOT planning files cover every county from Jan 1, 2023. The pending air permit lists show only what is pending today.

| County | Judged projects | With a signal before public | Governments read | Agendas held | Oldest agenda held |
|---|---|---|---|---|---|
| Austin | 1 | 0 | 3 | 191 | Jan 1, 2023 |
| Bexar | 8 | 0 | 3 | 101 | Jan 17, 2023 |
| Bosque | 1 | 0 | 0 | 0 | none |
| Bowie | 2 | 0 | 2 | 21 | Jan 1, 2026 |
| Callahan | 1 | 0 | 0 | 0 | none |
| Carson | 1 | 0 | 2 | 3 | Nov 16, 2026 |
| Dallas | 17 | 0 | 5 | 2125 | Jan 3, 2023 |
| Ellis | 3 | 0 | 0 | 0 | none |
| Freestone | 1 | 0 | 0 | 0 | none |
| Harris | 6 | 0 | 6 | 974 | Jan 3, 2023 |
| Hill | 2 | 0 | 2 | 113 | Jan 3, 2023 |
| Hood | 8 | 0 | 0 | 0 | none |
| Hopkins | 1 | 0 | 0 | 0 | none |
| Johnson | 2 | 0 | 1 | 21 | Feb 6, 2025 |
| Lubbock | 2 | 0 | 0 | 0 | none |
| Matagorda | 3 | 0 | 0 | 0 | none |
| Milam | 3 | 1 | 3 | 365 | Jan 3, 2023 |
| Potter | 2 | 0 | 0 | 0 | none |
| Somervell | 2 | 0 | 0 | 0 | none |
| Taylor | 1 | 0 | 2 | 36 | Jun 5, 2023 |
| Tom Green | 4 | 0 | 0 | 0 | none |
| Travis | 2 | 0 | 4 | 1033 | Jan 5, 2023 |

## By kind of signal

| Kind | Signals | Tied to a known project | Projects with one before public | Median days ahead |
|---|---|---|---|---|
| agenda item or file | 1382 | 16 | 1 | 39 |
| ERCOT planning file | 78 | 0 | 0 | none |
| well report | 49 | 14 | 0 | none |
| pending air permit | 12 | 0 | 0 | none |

## By the rule that made the signal

| Strongest reason | Signals | Tied to a known project |
|---|---|---|
| says "data center" | 109 | 13 |
| company on the Comptroller's list | 33 | 13 |
| company named like one on the list | 1 | 1 |
| "Project" and a code name | 399 | 3 |
| a code word | 979 | 0 |

A signal tied to no known project is not shown to be wrong. The list of known projects is not complete.

## Records tied to no project that a person should read

42 records that say "data center", or are a planning file that names the county, were seen in the year before a judged project in the same county became public. The program ties a record to a project only by a name the list of known projects carries, and a county calls a project by names the list does not have. **Any of these may be an early record of a known project. None is counted as one.** Many are a government's own computer rooms.

| County | Seen | Kind | Record |
|---|---|---|---|
| Bexar | 2024-03-14 | ERCOT planning file | ERCOT Regional Planning Group file "EIR - CPS - Eastside 345_138-kV Switching Station Project_SCOPE_March_RPG_.pdf" |
| Bexar | 2024-05-10 | ERCOT planning file | ERCOT Regional Planning Group file "EIR - CPS - Eastside 345_138-kV Switching Station Project_May_RPG.pdf" |
| Dallas | 2024-09-20 | ERCOT planning file | ERCOT Regional Planning Group file "Oncor_Wilmer345-138 kV Switch_Project_RPG_09252024.pdf" |
| Dallas | 2025-01-28 | ERCOT planning file | ERCOT Regional Planning Group file "2024_RTP_Final_Update_January_2025_RPG.pdf" |
| Dallas | 2025-04-28 | ERCOT planning file | ERCOT Regional Planning Group file "Oncor_Southern-DFW-Load-Interconnection_Project_RPG_04292025.pdf" |
| Dallas | 2026-04-22 | agenda item or file | Dallas City Council, meeting of April 22, 2026, item 51, file 26-1360A |
| Dallas | 2026-05-12 | agenda item or file | Farmers Branch City Council, meeting of May 19, 2026, item L.2, file R2026-060 |
| Dallas | 2026-05-19 | agenda item or file | Lewisville Planning and Zoning Commission, meeting of May 19, 2026, item 2, file 26-4594 |
| Freestone | 2025-04-28 | ERCOT planning file | ERCOT Regional Planning Group file "Oncor_Southern-DFW-Load-Interconnection_Project_RPG_04292025.pdf" |
| Harris | 2023-01-30 | agenda item or file | Harris County Commissioners Court, meeting of January 31, 2023, item in position 263 |
| Harris | 2023-02-21 | agenda item or file | Harris County Commissioners Court, meeting of February 21, 2023, item 278, file 23-0871 |
| Harris | 2023-03-21 | agenda item or file | Houston, agenda for the meeting of March 21, 2023 |
| Harris | 2023-04-21 | agenda item or file | Harris County Commissioners Court, meeting of April 25, 2023, item 294, file 23-2262 |
| Harris | 2023-04-21 | agenda item or file | Harris County Commissioners Court, meeting of April 25, 2023, item 295, file 23-2263 |
| Harris | 2023-09-19 | agenda item or file | Houston, agenda for the meeting of September 19, 2023 |
| Harris | 2023-10-06 | agenda item or file | Harris County Commissioners Court, meeting of October 10, 2023, item 31, file 23-5833 |
| Harris | 2023-10-31 | agenda item or file | Harris County Commissioners Court, meeting of October 31, 2023, item 260, file 23-6207 |
| Harris | 2024-01-05 | agenda item or file | Harris County Commissioners Court, meeting of January 9, 2024, item 203, file 24-0205 |
| Harris | 2024-02-23 | agenda item or file | Harris County Commissioners Court, meeting of February 27, 2024, item 491, file 24-1271 |
| Harris | 2024-03-22 | agenda item or file | Harris County Commissioners Court, meeting of March 26, 2024, item 435, file 24-1777 |
| Harris | 2024-03-22 | agenda item or file | Harris County Commissioners Court, meeting of March 26, 2024, item 454, file 24-1894 |
| Harris | 2024-05-30 | agenda item or file | Harris County Commissioners Court, meeting of June 4, 2024, item 350, file 24-3041 |
| Harris | 2024-12-10 | agenda item or file | Houston, agenda for the meeting of December 10, 2024 |
| Harris | 2025-02-21 | agenda item or file | Harris County Commissioners Court, meeting of February 27, 2025, item 117, file 25-1237 |
| Harris | 2025-05-15 | agenda item or file | Harris County Commissioners Court, meeting of May 22, 2025, item 126, file 25-3255 |
| Harris | 2025-05-15 | agenda item or file | Harris County Commissioners Court, meeting of May 22, 2025, item 206, file 25-3164 |
| Harris | 2025-08-23 | agenda item or file | Harris County Commissioners Court, meeting of August 26, 2025, item 11, file 25-5079 |
| Harris | 2025-08-23 | agenda item or file | Harris County Commissioners Court, meeting of August 26, 2025, item 134, file 25-5193 |
| Harris | 2025-08-23 | agenda item or file | Harris County Commissioners Court, meeting of August 26, 2025, item 325, file 25-5359 |
| Harris | 2025-12-02 | agenda item or file | Houston, agenda for the meeting of December 2, 2025 |
| Harris | 2025-12-04 | agenda item or file | Harris County Commissioners Court, meeting of December 11, 2025, item 334, file 25-7630 |
| Harris | 2026-01-27 | agenda item or file | Houston, agenda for the meeting of January 27, 2026 |
| Hill | 2026-05-05 | agenda item or file | Hillsboro, agenda for the meeting of May 5, 2026 |
| Milam | 2025-02-24 | agenda item or file | Milam County, agenda for the meeting of February 24, 2025 |
| Milam | 2025-11-18 | agenda item or file | Milam County, agenda for the meeting of November 18, 2025 |
| Milam | 2025-11-18 | agenda item or file | Milam County, agenda for the meeting of November 18, 2025 |
| Milam | 2026-01-27 | agenda item or file | Milam County, agenda for the meeting of January 27, 2026 |
| Milam | 2026-01-27 | agenda item or file | Milam County, agenda for the meeting of January 27, 2026 |
| Milam | 2026-06-08 | agenda item or file | Milam County, agenda for the meeting of June 8, 2026 |
| Milam | 2026-06-22 | agenda item or file | Milam County, agenda for the meeting of June 22, 2026 |
| Milam | 2026-11-09 | agenda item or file | Milam County, agenda for the meeting of November 9, 2026 |
| Travis | 2025-11-25 | agenda item or file | Round Rock City Council, meeting of December 4, 2025, item D.7 |

## Pending air permits

- The two lists give 12 signals. They give no county, so none can sit on a site or be tied to a project by the rules above.
- By the applicant's name alone, in any county, 10 name a company of a known project. **0 of those were received before that project's public date.**
- The lists show what is pending today. A permit decided before November 2026 is gone from them, so this feed cannot be judged on history.

## Control counties

Lamb, Comanche, Eastland, Lampasas, Mills, Wood, Titus, Colorado, Lavaca, Runnels, Coleman.

- Signals: 0. Sites: 0. False alarms: 0.
- **This is a weak test.** The radar reads no agenda in a control county. Only the well reports and the ERCOT planning files could have given a signal there.

## Sites that fit no known project

In the test counties, signals that fit no known project make 128 sites under the everyday rules. None is named here: none has been reviewed.

| Held together by | Sites | Highest score | At or over the threshold |
|---|---|---|---|
| a "Project" code name | 123 | 1.5 | 0 |
| a company or coordinates | 3 | 13.5 | 0 |
| a project number | 2 | 9 | 0 |

The sites held by a company or coordinates:

| County | Kind | Signals | First seen | Highest score |
|---|---|---|---|---|
| Travis | well report | 13 | Mar 7, 2025 | 13.5 |
| Carson | well report | 16 | Mar 3, 2026 | 7.5 |
| Travis | well report | 6 | Jun 24, 2026 | 4.5 |

Signals that fit two known projects equally and were given to neither: 1.

## Other thresholds

The same signals, with only the bar moved.

| Threshold | Hits | Reached it only after public | Judged | Hit rate | Median lead, days | False alarms in control counties | Sites that fit no known project, at or over |
|---|---|---|---|---|---|---|---|
| 1 | 1 | 4 | 73 | 1% | 39 | 0 | 128 |
| 2 | 1 | 4 | 73 | 1% | 39 | 0 | 5 |
| 3 | 1 | 4 | 73 | 1% | 39 | 0 | 5 |
| 4 | 1 | 4 | 73 | 1% | 39 | 0 | 5 |
| 5 | 0 | 1 | 73 | 0% | none | 0 | 4 |
| 10 | 0 | 0 | 73 | 0% | none | 0 | 1 |
| 20 | 0 | 0 | 73 | 0% | none | 0 | 0 |
| 40 | 0 | 0 | 73 | 0% | none | 0 | 0 |

A site that fits no known project is not a false alarm. Nobody has shown what it is. The count says how many sites a reviewer would be sent.

## Every signal tied to a known project

| Seen | Project | Kind | Strongest reason | Record | Tied by | Name found |
|---|---|---|---|---|---|---|
| 2025-07-18 | `dallas-garland-digital-realty` | agenda item or file | says "data center" | Carrollton City Council, meeting of July 22, 2025, item *16, file 7287 | the record names the project's company or code name | company Digital Realty |
| 2025-09-22 | `archer-project-raptor` | agenda item or file | "Project" and a code name | Archer County, agenda for the meeting of September 22, 2025 | the same project name or number | code name Project Raptor |
| 2025-10-20 | `milam-sb-energy` | agenda item or file | says "data center" | Milam County, agenda for the meeting of October 20, 2025 | the record names the project's company or code name | company SB Energy |
| 2025-10-24 | `milam-sb-energy` | agenda item or file | says "data center" | Milam County, agenda for the meeting of October 24, 2025 | the record names the project's company or code name | company SB Energy |
| 2025-11-24 | `milam-sb-energy` | agenda item or file | says "data center" | Milam County, agenda for the meeting of November 24, 2025 | the record names the project's company or code name | company Milam County DC LLC |
| 2025-11-24 | `milam-sb-energy` | agenda item or file | says "data center" | Milam County, agenda for the meeting of November 24, 2025 | the record names the project's company or code name | company Milam County DC LLC |
| 2025-12-08 | `milam-riot-rockdale` | agenda item or file | says "data center" | Milam County, agenda for the meeting of December 8, 2025 | the record names the project's company or code name | company Riot Rockdale LLC |
| 2025-12-08 | `milam-riot-rockdale` | agenda item or file | says "data center" | Milam County, agenda for the meeting of December 8, 2025 | the record names the project's company or code name | company Riot Rockdale LLC |
| 2026-01-12 | `milam-riot-rockdale` | agenda item or file | says "data center" | Milam County, agenda for the meeting of January 12, 2026 | the record names the project's company or code name | company Riot Rockdale LLC |
| 2026-01-12 | `milam-riot-rockdale` | agenda item or file | says "data center" | Milam County, agenda for the meeting of January 12, 2026 | the record names the project's company or code name | company Riot Rockdale LLC |
| 2026-01-26 | `milam-riot-rockdale` | agenda item or file | says "data center" | Milam County, agenda for the meeting of January 26, 2026 | the record names the project's company or code name | company Riot Rockdale LLC |
| 2026-01-26 | `milam-riot-rockdale` | agenda item or file | says "data center" | Milam County, agenda for the meeting of January 26, 2026 | the record names the project's company or code name | company Riot Rockdale LLC |
| 2026-02-09 | `milam-riot-rockdale` | agenda item or file | says "data center" | Milam County, agenda for the meeting of February 9, 2026 | the record names the project's company or code name | company Riot Rockdale LLC |
| 2026-04-13 | `archer-project-raptor` | agenda item or file | "Project" and a code name | Archer County, agenda for the meeting of April 13, 2026 | the same project name or number | code name Project Raptor |
| 2026-04-27 | `archer-project-raptor` | agenda item or file | "Project" and a code name | Archer County, agenda for the meeting of April 27, 2026 | the same project name or number | code name Project Raptor |
| 2026-05-04 | `travis-tesla-giga-texas` | well report | company on the Comptroller's list | Texas well report tracking number 722439 | the same company |  |
| 2026-05-04 | `travis-tesla-giga-texas` | well report | company on the Comptroller's list | Texas well report tracking number 722441 | the same company |  |
| 2026-05-04 | `travis-tesla-giga-texas` | well report | company on the Comptroller's list | Texas well report tracking number 722442 | the same company |  |
| 2026-05-04 | `travis-tesla-giga-texas` | well report | company on the Comptroller's list | Texas well report tracking number 722443 | the same company |  |
| 2026-05-04 | `travis-tesla-giga-texas` | well report | company on the Comptroller's list | Texas well report tracking number 722444 | the same company |  |
| 2026-05-04 | `travis-tesla-giga-texas` | well report | company on the Comptroller's list | Texas well report tracking number 722445 | the same company |  |
| 2026-05-04 | `travis-tesla-giga-texas` | well report | company on the Comptroller's list | Texas well report tracking number 722447 | the same company |  |
| 2026-05-04 | `travis-tesla-giga-texas` | well report | company on the Comptroller's list | Texas well report tracking number 722448 | the same company |  |
| 2026-05-04 | `travis-tesla-giga-texas` | well report | company on the Comptroller's list | Texas well report tracking number 722449 | the same company |  |
| 2026-05-04 | `travis-tesla-giga-texas` | well report | company on the Comptroller's list | Texas well report tracking number 722450 | the same company |  |
| 2026-05-04 | `travis-tesla-giga-texas` | well report | company on the Comptroller's list | Texas well report tracking number 722451 | the same company |  |
| 2026-05-04 | `travis-tesla-giga-texas` | well report | company on the Comptroller's list | Texas well report tracking number 722453 | the same company |  |
| 2026-05-04 | `travis-tesla-giga-texas` | well report | company on the Comptroller's list | Texas well report tracking number 722454 | the same company |  |
| 2026-05-11 | `austin-cleanspark` | agenda item or file | says "data center" | Austin County, agenda for the meeting of May 11, 2026 | the record names the project's company or code name | company CleanSpark, Inc. |
| 2026-07-16 | `bosque-cyrusone-thad-hill` | well report | company named like one on the list | Texas well report tracking number 728122 | the same company |  |

## How a signal's day was set

| A signal counts from | Signals |
|---|---|
| the day Legistar says the agenda was last published | 960 |
| the day of the meeting: the day the file was posted is not kept | 231 |
| the day of the meeting: no earlier publishing day is recorded | 191 |
| the day in the file's address, the day ERCOT posted it | 78 |
| the day the report was submitted to the state | 49 |
| the day the radar first held the list | 12 |

Where the day a record was posted is not kept, the later day is used. A lead time here is never longer than the records support.

