# Texas backtest: what it shows and what is proposed

BUILD_PLAN.md milestone M9. Written by hand on November 23, 2026. The backtest ran three times that day.

- **The first run** used the radar as it was built, with a review threshold of 40. Its numbers are under "The first run" and "Why so little". Its report is in this repository's history, at commit `7d163cf`.
- **The owner then approved three changes,** listed under "Decided". **The second run** has them.
- **The owner then added one name to the list of known projects. The third run** has it, and [report_tx.md](report_tx.md), which a program writes, is the third run's.

**Nothing here is a finding about a company or a place.**

## The third run, with the name the owner added

- **Two of 73 judged projects reach the review threshold of 3 before they were public,** 77 and 39 days ahead. The median is 58 days.
- **The second is the SB Energy project in Milam County.** The county's agenda for February 24, 2025 has an item on a grading plan for what it calls the Orion Data Center in Burlington. The list did not carry that name, so the first two runs did not count the record. The owner added it on November 23, 2026.
- **No source read says in words that the Orion Data Center and the SB Energy project are one.** The tie rests on the place, the timing and the address of the project's first news story, which carries the word orion.
- Both early records are Milam County agendas. Both sit on a site a reviewer would see.
- 58 sites that fit no known project reach the bar, one fewer than in the second run.
- 71 of 73 judged projects still have no signal before their public date.

## The second run, with the three changes

- **One of 73 judged projects reaches the review threshold of 3 before it was public,** 39 days ahead. It is the same record as in the first run: Milam County files for the meeting of December 8, 2025.
- **That record now sits on a site a reviewer would see.** It is held by its meeting's agenda.
- **The cost: 59 sites that fit no known project reach the bar in four years of records,** about 15 a year. 54 are one meeting's agenda that says "data center", 3 are held by a company or coordinates and 2 by a project number. Before the changes the count at this bar was 5. Many of the 54 are a government's own computer rooms. Nobody has reviewed any of them.
- Signals that rest on "Project" and a code name fell from 399 to 93, and the sites they make from 123 to 35. The three tied to a known project are kept.
- False alarms in the eleven control counties: still none, and still a weak test.
- **Nothing else moved.** 72 of 73 judged projects have no signal before their public date. The reasons under "Why so little" stand.

## The first run

- **No known project reached the review threshold of 40,** before or after it was public. 73 projects were judged. The highest score any of the 128 ever reaches is 7.5.
- **One of 73 had a signal before its public date.** Two Milam County files for the meeting of December 8, 2025 name Riot Rockdale and a data center, 39 days before the first news report found.
  - **The lead may be 70 days.** One of the two is a notice whose own date and address stamp are November 7, 2025. The backtest counts an agenda file from the day of its meeting, because the day a file was posted is not kept. Whether the notice could be seen on November 7 is not verified.
  - The research for the list of known projects found a later notice of the same county by hand, posted December 8. The collector holds that one too.
- **The radar as first built would not have sent that record to a reviewer.** An agenda names people, so an agenda signal carries no company. It has no company, no coordinates and no project name, and a signal with none of those sits on no site. The backtest tied it to the project by finding the project's company in the record's words.
- Four more judged projects had a signal only after they were public, 161 to 937 days after.
- **False alarms in the eleven control counties: none.** The history holds no signal there at all, so this says little.

## Why so little

1. **The radar held no agenda where most projects are.** For 61 of the 73, it held no agenda of the project's county government or of the city its row names, in the year before the public date. For 30 it held no agenda from any government in the county in that year. Hood County has 8 judged projects and the radar held no agenda from it.
2. **Where it held the agendas, there was often nothing to find.** Twelve judged projects sit where the county's or the city's agendas were held. Eight are in Dallas and Harris counties, and for six of those the earliest record the research found is a state filing or the company's own release. No vote came first.
3. **A history run reads what a site holds today, not what it held then.** Milam County posted a notice on May 8, 2025 for the SB Energy project, four days before the first news report. The county's page holds no agenda dated from mid May through July 2025 now. The research found that notice at an older address. An everyday collector running in May 2025 could have read it. So the backtest understates what a running radar would have seen, by an amount it cannot measure.
4. **Well reports came late.** Fourteen well reports are tied to a known project. Every one was submitted after the project was public.
5. **The feeds the plan weights highest could not be judged.** Abatement notices, commission dockets and stormwater notices are held or closed. The pending air permit lists show only today's rows: ten name a company of a known project, and none was received before that project's public date.
6. **The planning group files are hard to place.** 78 signals, 65 with no county, none tied to a known project.
7. **Two keyword rules made noise.** In the first run 399 signals rest on "Project" and a code name. Three are tied to a known project, all for one name. Most of the rest are ordinary phrases, such as a project's contract or a flood control project number. They make 123 sites. 979 signals rest on a code word alone and none is tied to a known project.

## Records a person should read

After the first run the report listed 42 records tied to no project that say "data center" or are a planning file naming the county, each seen in the year before a judged project in that county became public. Many are a government's own computer rooms or a zoning ordinance. Three were not:

- **Milam County, February 24, 2025.** An item on a grading plan for what the county calls the Orion Data Center in Burlington, 77 days before the SB Energy project's public date. **The owner added the name and the third run counts the record.** The report now lists 41.
- **Milam County, November 18, 2025.** A town hall on a proposed data center near Burlington. The unnamed project east of Burlington has a public date of November 16, 2026, and its row already says the true first report is earlier.
- **Hillsboro, May 5, 2026.** An update on a data center project, a month before the public date of the Hill County project near Abbott. The agenda does not say which project.

Three sites that fit no known project carry a company and coordinates, all from well reports: two in Travis County and one in Carson County. They are unreviewed and are not named in this repository.

## Decided

The owner approved all of this on November 23, 2026. It is done, and the second run above has it.

**1. The thresholds are not validated.** One early record cannot tell a good bar from a bad one. `placeholder: true` stays in `config/scoring.yaml`.

**2. `review_threshold` is 3, down from 40, as a working number.** The reasons, all from the first run:

- 40 is out of reach. Nothing the radar holds on any known project passes 7.5.
- The scores do sort the records. Records tied to a known project score 4.5 to 13.5. The 123 code-name sites score 1.5.
- Any bar from 2 to 4 gives the same result: the one early record crosses. On the first run's rules a reviewer was sent 5 sites that fit no known project in four years of records, and 128 at a bar of 1. **With the third change below it is 59,** because every agenda that says "data center" now makes a site.
- In words, a bar of 3 means: a record that says "data center", a well owned by a company on the Comptroller's list or a planning file that names the county goes to a reviewer by itself. A bare code word or code name does not.

**3. An agenda record that says "data center" opens a site held by its government and meeting.** Records of one meeting share a site. A code word alone opens none. Without this the bar did not matter for agendas, and agendas gave the only early record. A meeting is not a place: the site says where the record is, and a reviewer reads it for where the project is. Two projects on one agenda share a site.

**4. On Legistar a "Project" code name counts only where the item speaks of economic development negotiations,** the rule agenda files already had. An item whose heading sits in an earlier item is missed.

**5. The backtest is run again after any held feed is settled.** It is one command.

## Not verified

- **The public dates.** Each is the earliest news report found. An older report would shorten or erase the one lead. 49 projects have no public date and are not judged.
- **The day an agenda file was posted.** It is not kept, so a file counts from the day of its meeting. The one lead is 39 days on that rule and 70 days by the file's own date.
- **How many of the 59 sites a reviewer would call noise.** None has been read as a reviewer would.
- **The ties.** A program tied each record to a project, and nobody has checked them. One is known to be wrong: a Carrollton item on the city's own computing contract is tied to a Garland project by the vendor's name. That project is not judged.
- **The Comptroller's list as it stood in the past.** A company counts as listed from the day its registration took effect. Whether the list showed it that day is not known.
- **Whether a control county has a project.** The screen behind the list rests on two or three searches a county.
- Michigan local agendas wait on these thresholds in the plan. Nothing here was tested on Michigan records.
