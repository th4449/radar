# Texas backtest: what it shows and what is proposed

BUILD_PLAN.md milestone M9. Written by hand on November 23, 2026, from [report_tx.md](report_tx.md), which a program writes. Every number here is in that report. The owner decides everything under "Proposed".

**Nothing here is a finding about a company or a place.**

## The result

- **No known project reaches the review threshold of 40,** before or after it was public. 73 projects were judged. The highest score any of the 128 ever reaches is 7.5.
- **One of 73 had a signal before its public date.** Two Milam County files for the meeting of December 8, 2025 name Riot Rockdale and a data center, 39 days before the first news report found.
  - **The lead may be 70 days.** One of the two is a notice whose own date and address stamp are November 7, 2025. The backtest counts an agenda file from the day of its meeting, because the day a file was posted is not kept. Whether the notice could be seen on November 7 is not verified.
  - The research for the list of known projects found a later notice of the same county by hand, posted December 8. The collector holds that one too.
- **The radar as built would not have sent that record to a reviewer.** An agenda names people, so an agenda signal carries no company. It has no company, no coordinates and no project name, and a signal with none of those sits on no site. The backtest tied it to the project by finding the project's company in the record's words.
- Four more judged projects had a signal only after they were public, 161 to 937 days after.
- **False alarms in the eleven control counties: none.** The history holds no signal there at all, so this says little.

## Why so little

1. **The radar held no agenda where most projects are.** For 61 of the 73, it held no agenda of the project's county government or of the city its row names, in the year before the public date. For 30 it held no agenda from any government in the county in that year. Hood County has 8 judged projects and the radar held no agenda from it.
2. **Where it held the agendas, there was often nothing to find.** Twelve judged projects sit where the county's or the city's agendas were held. Eight are in Dallas and Harris counties, and for six of those the earliest record the research found is a state filing or the company's own release. No vote came first.
3. **A history run reads what a site holds today, not what it held then.** Milam County posted a notice on May 8, 2025 for the SB Energy project, four days before the first news report. The county's page holds no agenda dated from mid May through July 2025 now. The research found that notice at an older address. An everyday collector running in May 2025 could have read it. So the backtest understates what a running radar would have seen, by an amount it cannot measure.
4. **Well reports came late.** Fourteen well reports are tied to a known project. Every one was submitted after the project was public.
5. **The feeds the plan weights highest could not be judged.** Abatement notices, commission dockets and stormwater notices are held or closed. The pending air permit lists show only today's rows: ten name a company of a known project, and none was received before that project's public date.
6. **The planning group files are hard to place.** 78 signals, 65 with no county, none tied to a known project.
7. **Two keyword rules make noise.** 399 signals rest on "Project" and a code name. Three are tied to a known project, all for one name. Most of the rest are ordinary phrases, such as a project's contract or a flood control project number. They make 123 sites. 979 signals rest on a code word alone and none is tied to a known project.

## Records a person should read

The report lists 42 records tied to no project that say "data center" or are a planning file naming the county, each seen in the year before a judged project in that county became public. Many are a government's own computer rooms or a zoning ordinance. Three are not:

- **Milam County, February 24, 2025.** An item on a grading plan for what the county calls the Orion Data Center in Burlington. That is 77 days before the SB Energy project's public date, and the address of that project's first news story carries the word orion. The list of known projects does not have the name, so the program does not count the record. **If the owner adds the name, two of 73 had an early signal.**
- **Milam County, November 18, 2025.** A town hall on a proposed data center near Burlington. The unnamed project east of Burlington has a public date of November 16, 2026, and its row already says the true first report is earlier.
- **Hillsboro, May 5, 2026.** An update on a data center project, a month before the public date of the Hill County project near Abbott. The agenda does not say which project.

Three sites that fit no known project carry a company and coordinates, all from well reports: two in Travis County and one in Carson County. They are unreviewed and are not named in this repository.

## Proposed

**1. Do not treat the thresholds as validated.** One early record and no hit cannot tell a good bar from a bad one. Keep `placeholder: true` in `config/scoring.yaml` whatever the number is.

**2. Lower `review_threshold` from 40 to 3 as a working number.** The reasons, all from this history:

- 40 is out of reach. Nothing the radar holds on any known project passes 7.5.
- The scores do sort the records. Records tied to a known project score 4.5 to 13.5. The 123 code-name sites score 1.5.
- Any bar from 2 to 4 gives the same result: the one early record crosses, and a reviewer is sent 5 sites that fit no known project in four years of records. At 1 a reviewer is sent 128.
- In words, a bar of 3 means: a record that says "data center", a well owned by a company on the Comptroller's list or a planning file that names the county goes to a reviewer by itself. A bare code word or code name does not.

**3. Give an agenda record a way onto a site.** Without it the bar does not matter for agendas, and agendas gave the only early record. One way: an agenda record that says "data center" opens a site held by its government and meeting. This changes what milestone M5 built, so it waits for the owner.

**4. Hold the "Project" code-name rule on Legistar to the rule agenda files already have:** a code name counts only where the item speaks of economic development negotiations.

**5. Run the backtest again after each of these and after any held feed is settled.** It is one command.

The other choice is to leave 40 in place until more feeds exist. The radar would then send no known kind of record to a reviewer.

## Not verified

- **The public dates.** Each is the earliest news report found. An older report would shorten or erase the one lead. 49 projects have no public date and are not judged.
- **The day an agenda file was posted.** It is not kept, so a file counts from the day of its meeting. The one lead is 39 days on that rule and 70 days by the file's own date.
- **The ties.** A program tied each record to a project, and nobody has checked them. One is known to be wrong: a Carrollton item on the city's own computing contract is tied to a Garland project by the vendor's name. That project is not judged.
- **The Comptroller's list as it stood in the past.** A company counts as listed from the day its registration took effect. Whether the list showed it that day is not known.
- **Whether a control county has a project.** The screen behind the list rests on two or three searches a county.
- Michigan local agendas wait on these thresholds in the plan. Nothing here was tested on Michigan records.
