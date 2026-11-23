# Progress

Newest first. Each entry says what was built, what was verified live and what is still unverified.

## November 22, 2026 — M9 started: the backtest harness, and what the backtest still needs

The owner said to start M9. The harness is built and tested on made-up signals. **No backtest has been run.** It needs three things the plan does not give, each the owner's call.

**Built**

- `backtest/harness.py`. Given known projects and dated signals, it finds each project's signals, replays its score day by day with the production scoring, and says whether the site would have reached the reviewers before the project was public.
- **It reuses the production rules.** A signal belongs to a project for the reasons a signal joins a site in `pipeline/cluster.py`. The score is `pipeline/score.py`'s.
- **A signal counts from the day it could be seen,** not the day it is dated.
- Outcomes: `hit`, `late`, `below_threshold`, `no_signal`. Not judged: `undated`, and `before_history` for a project public before the records begin.
- A false alarm is a site over the threshold in a control county. Signals in a test county that fit no known project are listed apart: an unannounced project would look the same.
- A sweep shows hits, lead time and false alarms at each threshold. A count by signal type shows which came first and how early.
- 19 tests, written first. 941 pass.

**Checked**

- **FracTracker's baseline, counts only,** by hand, six requests: 98 records in the 30 counties, in 21 of them. 41 proposed, 14 approved or under construction, 4 expanding, 38 operating, 1 cancelled. Nine of the 30 counties have no record.
- **The baseline has no date a project became public.** It has the dates its own record was made and updated, an expected date online and up to eight source links.

**What the backtest still needs**

- **A list of known projects with the date each became public.** The plan names none. The date has to be found for each project and its source kept.
- **Control counties.** The plan asks for false alarms in them and names none. All 30 counties were picked for data center activity.
- **History.** The collectors read the present. The pending air permit lists go back to 2023 and drop a permit once it is decided. The planning group's older years, older well reports and older agendas each need a one-time run.

**FracTracker's records cannot be taken as things stand**

- The owner said to build the project list from FracTracker and news reports. I read the terms before taking any record.
- **FracTracker's terms changed since November 19.** The map opens on six terms and a box to agree. Use must fit its mission, as it alone judges, and must cite it. The line about free non-commercial use is gone. I did not agree to them: that is the owner's to do.
- **Esri's terms bar harvesting from the map's service,** and bar reaching it other than through a browser or Esri's products. The counts of November 19 and today were taken by script. No more are made.
- `us_fractracker` is now marked `restricted`. See [us_fractracker.md](sources/us_fractracker.md).

**A pilot of the other way: news reports and public records, three counties**

- One research pass each for Hood, Hill and Milam counties. 23 projects, each with the earliest dated report found and its source: `backtest/known_projects_tx.csv`, first kept in `backtest/pilot/`.
- A second read opened nine of the cited sources again. Every date held.
- **For 10 of the 23, a government record or a petition names the data center before the first news report found.** Two are Milam County notices of tax abatement hearings, on the page the radar reads since November 22. One is a state air permit review, 162 days ahead of the first news story found.
- **A rule was broken in the first pass.** I did not tell it to stay off restricted hosts. Three Hood County minutes files were fetched through a tool that switched to a stealth proxy by itself, from a host whose robots file bars every program. Three pages of a newspaper that blocks the crawler were read too. Nothing resting on those six pages is used. Two Hood County projects have no usable first record for that reason.
- Agenda history, counted from pages already saved: the 60 pages read list 2,388 agenda files dated since January 2023. Hood County's pages list two.

**The owner's decisions, November 22**

- **The date a project became public is the first news report or company announcement.** A government record is a signal. `backtest/projects.py` reads the list that way.
- **The owner agreed to FracTracker's terms.** Nothing has been taken since. A letter to FracTracker is drafted, not sent, for `info@fractracker.org`, the address its Terms of Service name. The map's service stays closed to programs.
- **Carry on with news research for the other 27 counties.** Each pass now carries the collectors' rules in its brief.

**Not verified**

- Whether Esri's section 2.3 covers a layer that a customer hosts.
- Whether any county's list in the pilot is complete, and the first report for seven Hood County projects.
- How many of the 98 records became public inside the years the records cover.
- Whether old agenda files are still posted for the 59 governments read. Sandy Oaks' list goes back to 2019.

**Limits to say now**

- Four kinds of signal have a collector: air permits, planning group filings, well reports and agendas. Abatement notices, stormwater notices, commission dockets and land purchases have none, so the backtest cannot weigh them.
- A permit decided before November 2026 is not on a pending list. The backtest will undercount air permits for older projects.

## November 22, 2026 — M8: HeyGov cleared, two of its four cities read

The owner said to go ahead with the four HeyGov cities. Two are read. Two are closed.

**Read**

- **Each city's own pages,** in a browser: a privacy policy and an accessibility statement on each, the same wording on all four. None speaks of automated access or reuse. No city links any terms of use.
- **Each agenda page as the server sends it,** with no script run.
- **The robots files of three HeyGov hosts,** one identified request each: the API, the script host and the file host again.

**What it found**

- **Sandy Oaks and Shallowater hold their lists as plain links.** They are read.
- **Highland Haven and Sanctuary hold no list in the page.** A script draws it from `api.heygov.com`, and that host's robots file bars every agent from every path. They are closed. The API is never asked.
- **I had this wrong on the last pass.** I wrote that all four pages hold plain links and that no new code was needed. I had looked at them through a browser, after the script ran. The owner's go-ahead rested on that note.
- 59 governments on 60 pages are read, up from 57 and 58.

**What changed in the code and config**

- `heygov` is `cleared` in `config/tx_agenda_platforms.csv`, on the owner's word. Four rows in `config/tx_agenda_site_terms.csv`: two `own_pages_silent`, two `robots_bar`.
- **The own-sites collector takes a HeyGov file only from the folder named for the city's own site.** Another city's folder and HeyGov's other hosts are listed and not followed.
- **A meeting card's own day is read ahead of the file's name.** Town Web's pages give each meeting's day in a form made for programs. A file's name can carry last year's year. The rule touches only pages with such cards. None of the 48 pages saved from earlier passes has one.
- Shallowater's inventory row is now `seen`, with its newest agenda.
- Two new fixtures, each a real page cut to its newest cards. 12 new tests. 922 pass.

**Verified live**

- One identified request to each of the two pages. The link finder reads 360 agenda links at Sandy Oaks and 88 at Shallowater, every one dated. The card's day and the file's name agree on 444 of the 448.
- **One run of the collector on the two cities,** two files a page, no database. Both pages answered and three files were stored. One is a scan, read by character recognition at 94 percent confidence. **None gave a signal.**

**Not verified**

- Whether HeyGov's terms reach a city's files on its file host. I read them as covering HeyGov's own website, and the owner went ahead on that reading.
- Which is right where a card's day and a file's name differ. Four old files do. I did not open them.
- Whether HeyGov would let a program read its API if asked.
- Whether a HeyGov file's address stays the same when a clerk replaces the file.
- A second day's run, and a run from GitHub's servers.

**Waiting on the owner**

- Highland Haven and Sanctuary: ask HeyGov for leave to read its API, ask the two cities for their agendas, or leave them out.
- Google Drive (11 governments, needs an API key) and JustMeetings (1, needs a small collector).
- CivicPlus' answer. Austin, Archer City, Live Oak and Keene. League City, Lubbock County and Fort Worth.

## November 22, 2026 — M8: the rules of the smaller outside services

The owner said to read them. 28 governments sat under one name, "other", with no rules read.

**Read**

- **The robots file of each service's host,** one identified request each, and of the hosts they led to: 22 hosts.
- **The terms of seven services:** Google, HeyGov, General Code (eCode360), BoardBook, Municipal Impact, Laserfiche, and the City of Trent's own. Four more are closed by their robots files, so their terms were not read. JustMeetings and Town Web publish no terms that I could find.
- Nine pages opened in a browser.

**What it found**

- **Seven services restrict a collector: 9 governments.** TownCloud, Diligent Community, Documents On Demand and Dropbox by their robots files. eCode360, BoardBook and Municipal Impact by terms.
- **Nothing was found against four: 17 governments.** Google Drive 11, HeyGov 4, JustMeetings 1, the Laserfiche portal 1. None is cleared. That takes the owner's word. Sunset Valley, the one city on the Laserfiche portal, refused the request for its own robots file and is closed.
- **Milam County is now read.** The inventory had its commissioners court on BoardBook only. The county also lists every agenda on its own site. 57 governments and 58 pages are read, up from 56 and 57.
- Matagorda County's agenda page still shows no agenda.

**What changed in the code and config**

- **Each service has its own name** and address pattern in `pipeline/agenda_inventory.py`, and its own row in `config/tx_agenda_platforms.csv`. 33 inventory rows renamed. Every verdict was compared before and after: only Milam County's changed.
- **A fault in the fetcher, fixed.** A robots file that starts with a byte order mark was read without its first line. Documents On Demand's file bars every path and read as allowing all. The fetcher now strips the mark. No request was made on the wrong reading, and none of the 182 robots files saved earlier is judged differently.
- 19 new tests. 910 pass.

**Verified live**

- One run of the own-sites collector on Milam County, two files, no database. Both files are scans of notices for the court's meeting of December 14, 2026, read by character recognition. **Both gave a signal on the words "reinvestment zone".** The notices are for a hearing on a tax abatement in a zone named for a solar project. Neither names a data center.

**Not verified**

- Whether HeyGov's terms reach a city's files on its file host. I read them as covering HeyGov's own website.
- Google's API terms, and whether the API costs anything.
- What the signal `use=reference` in two robots files asks of a reader.
- The terms of the four services closed by robots files.
- The own terms of the 16 governments on Google Drive, HeyGov and JustMeetings.
- Whether Milam County's file addresses, which end in a time stamp, stay the same from day to day.
- A second day's run, and a run from GitHub's servers.

**Waiting on the owner**

- Whether to go ahead with HeyGov (4 governments, no new code), Google Drive (11, needs an API key) or JustMeetings (1, needs a small collector).
- CivicPlus' answer. Austin, Archer City, Live Oak and Keene. League City, Lubbock County and Fort Worth.

## November 22, 2026 — M8: the 38 own-site governments that were not confirmed

The owner said to check them. Each agenda page was opened in a real browser. Robots files came first and terms before any collecting.

**Read first**

- **All 38 robots files allow the collector.**
- **Each page opened in a browser,** with the pages it led to. 39 reads are recorded in `config/tx_agenda_checks.csv`.
- **The terms of the 15 sites a collector could read.** Two bar robots in their own terms: Alma and Abernathy. Idalou answered the collector with a firewall's challenge and is closed. Nothing was worked around.

**What changed**

- **11 more governments are read:** Annetta North, DeCordova, Industry, Meadowlakes, Milano, Millsap, Rosebud, San Saba, Tolar, Wallis and Webberville.
- **Four that were read are closed again:** Buffalo Gap, Clyde, Malakoff and Mustang Ridge. Their sites are built and hosted by CivicPlus, whose terms bar automated systems on any CivicPlus site. Yesterday's readers looked for terms pages and missed the vendor's credit in the footer. Three of the 38 are the same and are closed with them. The new mark is `vendor_site`.
- **56 governments and 57 pages are now read,** up from 49 and 50.
- **Nine governments list agendas in a form the collector does not read:** script buttons, a page for each meeting, or a file host that is not theirs. Five post on another service. Six show nothing current.
- 14 inventory rows corrected. Four named the wrong page.

**Four faults in the link finder, found on the new pages and fixed**

- **A wrong date.** `june2026agenda.pdf` was read as June 20, 2026. Houston's page had 16 files named this way. None was fetched under a wrong date, and nothing is in a database.
- A treasurer's report and a financial statement were taken as agendas.
- Two ways of writing a date were not read.
- A page with one dated link read none of its month-only links. Such a link is now kept with its month.
- Three new fixtures cut from real pages. 18 new tests. 891 pass.

**Verified live**

- One identified request for each robots file, each page read for terms and five agenda files.
- **The finder before and after, on all 63 pages saved by earlier runs.** Only the wrong dates changed.
- **A run of the collector on the 12 then cleared,** two files a page, nothing written to a database. Ten agenda files of seven governments. Richland Springs' file host refused by its robots file, so it is closed.
- **One signal. Webberville's agenda for November 11, 2026 has an item to discuss the possibility of a proposed data center in Webberville,** and one on an ordinance to bar data centers there. I read both lines.

**Not verified**

- **Whether CivicPlus' terms bind a visitor to a site it builds.** I closed the four on the reading already used for its platforms.
- The terms of the nine governments the collector does not read.
- Millsap's page gives the finder no links. Its files sit under a heading and name only a month.
- The counts in the check rows of script-drawn lists. They are the rows I read.
- A second day's run, and a run from GitHub's servers.

## November 22, 2026 — M8: the five county association sites

The owner said to start on the five commissioners courts whose sites the Texas Association of Counties provides: Archer, Carson, Falls, Freestone and Hill. Terms and robots rules came first.

**Read first**

- **No robots file** on any of the five sites or on the association's host for files and calendar feeds.
- **No terms, disclaimer or privacy page** on any of the five. Each has a copyright line and a credit to the association.
- **The association's terms** speak of county.org and its related services. They say nothing on automated access and bar copying for commercial purposes.
- The software vendor, ezTask, publishes a privacy policy for its own website only.
- Nothing read stands against a collector. The platform is marked cleared and each county `no_terms_found`.

**Built**

- **The own-sites collector reads these five.** They are the counties' own sites.
- **Three of them keep agendas in a calendar that a script draws.** The calendar publishes an RSS feed of the meetings to come, with each agenda attached. The page gives the feed's address. The collector reads the feed with one more request. It never copies the page's script calls.
- A meeting's day is its start time, turned from Greenwich time into Texas time.
- A space in a file's address is now written `%20`.
- **A fault in yesterday's OCR found and fixed.** One real scan gave the text reader no pages, so it was never sent to OCR. The page drawer now counts the pages when the text reader finds none.
- Four browser checks recorded in `config/tx_agenda_checks.csv`. Two inventory rows corrected: Hill County's had recorded a court rules file as its agenda.
- Five new fixtures cut from the real pages and feeds. 12 new tests. 873 pass.

**Verified live**

- One identified request for each robots file and each page read for terms.
- **I opened Falls, Carson, Freestone and Hill in a real browser** and saw the agendas listed or attached. Archer's row was already confirmed.
- **A run of the collector on the five sites,** two files a page, nothing written to a database: 14 requests, none refused. Six agenda files of four counties. Freestone's feed was empty that day.
- Four of the six files are scans. All four now read by OCR, at scores of 92.5 to 94.8.
- **One signal.** Hill County's 108-page file for November 24, 2026 uses the words "data center" on two pages. I read both. One is a session title on a form for training credit and the other a definition in a software license. Neither is about a development in the county.

**Not verified**

- **Whether the association's terms reach the county sites.** None of the five links them.
- Freestone's feed with an agenda in it.
- An agenda attached to a calendar entry after its meeting started. The feed lists only meetings to come.
- A second day's run, and a run from GitHub's servers.

## November 21, 2026 — M8: scanned agendas are read by OCR

The first own-sites run stored 43 agenda files. 28 were scans with no text, and the radar read none of them. The owner said to build OCR.

**Checked first**

- **Tesseract** is free, under the Apache 2.0 license, and so is its English language data. It runs on our own machine. Nothing is sent to any service.
- **I measured it before building around it,** on the 28 real scans. All 28 gave text, at under a second a page.

**Built**

- **`pipeline/ocr.py`.** A PDF with no text at all is drawn page by page at 300 dots an inch and read by Tesseract. At most 150 pages of one file.
- **Text a machine read is marked as such.** The stored document carries the engine, the pages read and Tesseract's score. A signal made from it says in its summary: "The file is a scan, read by character recognition."
- A PDF with its own text never goes to Tesseract.
- **Without Tesseract nothing fails.** A scan is stored unread and counted as unread, as before.
- CI and the collect workflow install Tesseract. CI fails if the OCR tests are skipped. The collect workflow's time limit went from 30 to 90 minutes.
- Pillow is now named as a dependency. It was already installed by another package.
- `docs/services/tesseract.md`. 12 new tests. 861 pass.

**Verified, on files kept on this machine**

- **All 43 files of the first run now give text.** 28 by OCR.
- **5 signals, up from 3.** The two new ones come from scans. Merkel's council agenda for November 17, 2026 has two items on a tax increment reinvestment zone. A 125-page packet uses the words "development agreement".
- **I checked Merkel's page against its picture by eye.** The two items are there as read.
- **OCR against the truth, on the 13 files that have their own text:** 9,762 of 9,771 words came out the same, and both keyword matches were found. This is the best case: a clean page, not scanned paper.

**Not verified**

- **How well it reads real scans, as a number.** There is no typed copy to check against. Two pages were checked by eye.
- **Tables come out jumbled.** Sentences read correctly.
- Sideways pages, handwriting, and a file that is part text and part scan. Only a file with no text at all is read by OCR.
- Whether GitHub's runners read a real scan as this machine does. CI passed there with Tesseract 5.5.0 and Ubuntu's English data package 4.1.0, all 861 tests, none skipped. This machine has 5.5.4, and the 28 scans were measured here only.

## November 21, 2026 — M8: the second agenda collector, for governments' own sites

The owner said to build next for the governments that post agenda files on their own sites. There is no vendor. Each site has its own robots file and terms, so each was read first.

**Read first**

- **76 governments** have a confirmed inventory row on their own site. The other 38 wait for a hand read.
- **Robots files of 81 hosts,** one identified request each. **12 governments are closed:** the file bars the page or the files, answers 403, or could not be read.
- **Each of the other 64 sites' own terms,** by five research passes that copied the sentences on automated access and reuse.
  - 52 say nothing against it. 45 of those have no terms page at all.
  - **8 bar robots in their terms of service.** They share one site builder's terms page. Closed.
  - **4 limit reuse of their content:** Austin, Archer City, Live Oak and Keene. Held for the owner.
- I checked the readers against the pages the collector later fetched. One policy-like page had been missed, on Cumby's site. I read it. It restricts nothing.
- **One identified request to each of the 55 agenda pages. Two answered 403:** New Fairview and Taylor Lake Village. Both are closed and not asked again.
- **The first run then closed six more:** their agenda links lead to a site builder's file host whose robots file bars the files.
- **44 governments and 45 pages are read.** 18 are closed by a robots file, 8 by their own terms, 2 refused and 4 are held.

**Built**

- **`collectors/tx/agenda_pages.py`.** One request for each agenda page, then one for each agenda file dated from 21 days back to 60 ahead that is not stored yet, four a page at most.
- **A link finder for pages laid out every which way.** It takes a link that says it is an agenda in its words, its file name, its table column or its row. It leaves minutes, recordings, quorum notices and packets that have a plain agenda beside them.
- **A date reader that gives no date when it is not sure.** The page's words come before the file's name. A scanner's file name is never read. `1122026` is no date.
- **The shared collector learned two things.** A source that is many sites can have one site refuse without ending the run: that site is closed for the run and named in the run log. And a file stored as it is can carry facts, such as the page it came from.
- **A file is fetched only from the government's own site** or its site builder's file host.
- **`agenda_file` in `pipeline/signals.py`.** A file that uses a term becomes one `agenda_keyword` signal. **The summary carries no file name and no link text.** One real file is named for a person. A scan with no text is counted as unread, not as clean.
- Three results added to the site terms file, `bars_automated_access`, `robots_bar` and `refused`, and 76 rows.
- The source is marked `personal_rows`. A workflow file, started by hand only. `docs/sources/tx_agendas_own_sites.md`.
- 67 new tests. 849 pass.

**Verified live**

- **The link finder against the independent second read:** 44 of 53 pages give agenda files. On 38 the newest date matches. On five the finder found a newer agenda. One page could not be dated.
- **A run of the collector,** capped at two files a page, nothing written to a database. 52 of 53 pages answered. **43 agenda files of 29 governments, 365 pages.**
- **28 of the 43 files are scans with no text.** The radar read none of them. Sixteen governments gave only scans, Austin County among them.
- **3 signals from the 15 files with text.** Red Lick's council agenda uses the words "data center". A Cameron agenda has a reinvestment zone study and a code name under economic development negotiations. The third is a drainage table.

**Faults found and fixed**

- **Code names.** A 91-page file gave "Project Documentation" as a code name. In a file, a code name now counts only where the agenda speaks of economic development negotiations.
- **The email job's clock.** Three email tests failed off and on. The local database's clock runs 30 ms ahead of this machine's, and the job compared an alert's database timestamp with this machine's time. The job now takes its time from the database. The tests passed six times of six after.

**Not verified**

- **Nine pages list no file links** and are not read yet: their agendas are in the page, behind a script or on one page per meeting.
- **Scanned agendas give no text.** The pipeline has no OCR. This is most of what small governments post.
- Whether a date read from a file's name is always the meeting's.
- A full run with no cap, a second day's run and a run from GitHub's servers.
- Whether a site with no terms page has terms elsewhere.

**For the owner**

- **Austin, Archer City, Live Oak and Keene wait on your word.** Their terms limit reuse and say nothing on automated access.
- Eight cities' own terms bar robots. Reading them by program would take each city's written consent.
- **Scans need OCR to be read at all.** It can be done with free tools on our own machine. It is not in the plan, so I have not built it.
- A run is slow by design: 44 sites, each asked at the pace its robots file sets.

## November 21, 2026 — M8: the first agenda collector, for Legistar

The owner sent CivicPlus the request for written consent and said to go on with the build. Legistar was next.

**Read first**

- **The Legistar Web API is published for programs.** Granicus' own pages say it gives public records over HTTPS. No terms of use or rate limit is stated.
- **No robots file** on the API or on any of the 14 governments' Legistar hosts. **The hosts that hold the agenda PDFs bar every agent,** so the collector never fetches an agenda file.
- **Each government's own terms.** Nine have nothing against it. Three ask for written consent to reuse their content: League City, Lubbock County and Fort Worth. University Park's site did not load. San Antonio has left Legistar.

**Built**

- **`collectors/tx/legistar.py`.** One request for a government's list of meetings, then one for each meeting whose agenda is new or changed. It keeps each item's number, file, type, title and note, and drops who moved and voted.
- **The inventory decides who is read.** `collectable()` now needs three things: a confirmed row, a cleared platform and the government's own terms read with nothing against them. Legistar is cleared. Nine governments come through.
- **`legistar_agenda` in `pipeline/signals.py`.** An agenda item that uses a term the radar looks for becomes one `agenda_keyword` signal. **The summary never quotes the item,** because an item can name a private person.
- The source is marked `personal_rows`: an agenda's stored text is closed to reviewers and never sent to the model.
- A workflow file, started by hand only. `docs/sources/tx_agendas_legistar.md`.
- 37 new tests. 782 pass.

**Verified live**

- All 14 governments answered the API without a token.
- **A run of the collector on the nine governments,** capped at five meetings each: 41 requests at one every five seconds, no errors. 32 meetings, 1,207 agenda items.
- **7 signals from those 1,207 items.** One is a city council designating a reinvestment zone for a named company. One "data center" item is a county buying a service for its own computers.
- A search of four governments' records found Harris County's commissioners court taking up data center development on October 15, 2026.

**A fault found and fixed**

- The first pass gave 15 signals. Eight read "Project" plus an ordinary word, such as "Project Funding", as a code name. Those words are now excluded.

**Not verified**

- Any limit on requests to the API. None is published.
- A full run with no cap, and a run from GitHub's servers.
- Whether an agenda signal ever joins a site. It carries a county and no company or point.

**For the owner**

- **League City, Lubbock County and Fort Worth wait on your word.** Their terms limit reuse of their content. None mentions automated access.
- **Most agenda matches will be noise.** A reviewer tells a real item from a county's own computer purchase. The backtest should decide whether code words on agendas earn their keep.
- The reviewer's "open the source" link for an agenda signal goes to the API's answer. The meeting's own page is stored with the signal and the screen should use it.

## November 21, 2026 — M8: the platforms' own rules stop the first collector

The owner approved batches by platform. Before writing the first collector I read the platforms' terms and robots files, as the plan requires. **No collector is written.**

**Found**

- **CivicPlus' terms restrict the radar's use.** Section 8 bars automated collection of a government's content for use in any algorithmic or automated decision system without CivicPlus' written consent. The Agenda Center, CivicClerk and Municode Meetings are all CivicPlus products: 100 governments.
- **Granicus pages and CivicWeb are closed by their robots files.** Swagit's file host refuses its robots file. 17 governments.
- **Legistar and the county association sites are candidates:** 19 governments, 7 commissioners courts. Granicus publishes the Legistar Web API for programs.
- The governments' own pages mostly say nothing. Of 38 Agenda Center sites, 27 carry no word on automated access and 3 link CivicPlus' terms.
- All 38 sites' robots files allow the agenda pages, with a 10 second delay.

**Built**

- `config/tx_agenda_platforms.csv`: each platform's standing, with the reason.
- `config/tx_agenda_site_terms.csv`: what each of the 38 sites' own pages say.
- **`collectable()` now also needs a cleared platform.** None is cleared, so nothing is collectable. A test pins each platform's standing.
- The note is `docs/sources/tx_agenda_platform_terms.md`.
- 6 new tests. 745 pass.

**Verified by me**

- CivicPlus' terms, sections 1, 2, 3, 7 and 8, read in full. Granicus' website terms, read in full. The Legistar Web API's examples page.
- Robots files asked for on 50 hosts, one request each, with the radar's user agent.

**Not verified**

- Whether CivicPlus' terms bind a visitor to a government's site, and whether they reach a person's hand reading. Both are questions for counsel.
- Robots files on one host per platform, except the Agenda Center. Another customer's host may differ.
- The terms of each Legistar government, each county and each own-site government. None is read.
- The Legistar Web API was not called.

**For the owner**

- **The plan's largest source of Texas agendas cannot be automated as things stand.** The choices for the 100 CivicPlus governments are to ask CivicPlus for written consent, ask the governments, read by hand after counsel answers, or leave them out.
- **Legistar is the next candidate.** It needs your word and a reading of each government's terms first.

## November 21, 2026 — M8: a second read of the agenda inventory, and a system to keep it accurate

The owner asked for a wider accuracy check and a system that finds errors.

**Built**

- **`config/tx_agenda_checks.csv`: 410 independent checks.** Each is one read of one page. It records what was on the page and never names a platform.
- **`pipeline/agenda_checks.py`** gives every row of the inventory a verdict and a reason. Confirmed means a second read agreed on the platform, saw the body listed and saw an agenda under 400 days old.
- **A gate.** `collectable()` is true only for a confirmed row. No agenda collector takes any other row.
- **Checks go stale after 180 days.**
- **A list for a person:** `uv run python -m pipeline.agenda_checks --csv`. A person's check outranks every other.
- 26 new tests. 739 pass.

**The wider check**

- Ten research passes read all 320 agenda pages a second time, without being told what the inventory says. They searched again for the 22 towns with no website and looked again for the 60 governments not determined.
- **On 316 rows that could be compared, 311 agreed on the platform and 5 did not.** One was a plain error and is corrected. Two cities run two systems. One was a gap in the second read. One address has gone dead.
- All 22 "no website" rows held.
- The second read found agendas for 21 of the 60 governments not determined. Those rows are filled in and count as unchecked, since one read is one read.

**Where it stands**

- **290 of 607 bodies are settled. 204 of 334 governments are settled.** 17 of the 30 commissioners courts are confirmed.
- **130 governments need one hand read.** 33 of them have a page that fills itself in by script, which the page-reading tool cannot run.
- I opened 14 of those in a real browser. 4 are confirmed, 4 showed a real problem and 6 my reading script could not judge.

**Not verified**

- A confirmed row rests on two research passes agreeing, not on a person.
- Planning bodies are still incomplete, and 126 development corporations have no agenda page known.
- No platform's terms or robots rules are read.

**For the owner**

- **The hand-read list is `drafts/tx_agenda_hand_read_2026-11-21.csv`** on this machine, 317 rows, commissioners courts first. `drafts/` is not in the repository.
- A reviewer with a browser settles a script-filled page in about a minute. The 130 governments are a few hours of work.
- The proposal to batch collectors by platform still needs your answer.

## November 20, 2026 — M8, first step: the Texas agenda inventory

The plan's first step for M8 is an inventory of every commissioners court, city council, planning body and development corporation in the 30 counties, with the platform each uses. No collector is written.

**Built**

- **`config/tx_agenda_inventory.csv`: 607 bodies of 334 governments.** 30 commissioners courts, 304 city councils, 86 planning bodies and 187 development corporations, each with its agenda page and platform, or an honest "not determined".
- **The list of bodies comes from records, not from search.** Cities are every incorporated place in the 30 counties in the Census place file, kept in `config/tx_places.csv`. Development corporations are from the Comptroller's open dataset of Type A and Type B reports.
- **`pipeline/agenda_inventory.py`** loads the file and refuses a row that names a platform its own addresses do not show. `uv run python -m pipeline.agenda_inventory` prints the counts.
- Tests: every county has its court, every incorporated place has its council, no row names a person. 36 new tests. 713 pass.
- The note is `docs/sources/tx_local_agendas.md`.

**How the research was done**

- Eleven research passes, one per group of counties, read each government's own website. Their brief barred guessing an address, working around a block and recording a person's name.
- The merge kept one rule: a row may claim only what its addresses show. It weakened 6 rows and marked 55 as inferred.

**What it found**

- **Four platforms hold 113 of the 334 governments:** CivicPlus Agenda Center 51, CivicClerk 35, Legistar 14, Municode Meetings 13.
- 99 governments post files on their own sites. 22 have no website. 60 are not determined.
- Of the 30 commissioners courts, 10 are on CivicPlus Agenda Center and 5 on the county association's sites.

**Verified by hand**

- I opened 13 rows drawn at random by platform. 11 showed a current agenda on the platform the row names. One page could not be read and its row says so. **One row was wrong, by a fault in my merge rule,** and is corrected.

**Not verified**

- **594 of the 607 rows were not opened by me.**
- **Planning bodies are incomplete.** 86 cities have a row. For 88 cities the research did not look or did not say.
- 129 of the 187 development corporations have no agenda location.
- **No platform's terms or robots rules have been read.** Nothing in the inventory says a page may be collected.

**For the owner**

- **I propose batches by platform, not by ten counties.** One collector per platform reaches every county that uses it. Three batches would reach 135 governments and 22 of the 30 commissioners courts. The note has the detail. This changes the plan and needs your approval.
- **Each government's own site terms apply too.** An Agenda Center page sits on the city's domain. Before a collector touches a site I read that site's terms and robots rules, and mark it manual if they restrict automated access.
- A second research pass could fill the planning bodies, the 60 governments not determined and the development corporations. It is not run.

## November 20, 2026 — Michigan refused permission for the docket site

The owner shared the Public Service Commission's reply to the request sent on November 19.

- **The State refused a written agreement.** The reply says the State of Michigan has not historically granted permission for automated access and that its terms prohibit it. It also says no agreement is needed to use information from the website.
- **`mi_mpsc_dockets` is manual for good.** No collector will be written. The radar does not work around a refusal.
- The two EGLE feeds were already restricted. Their requests are drafted and not sent. The reply states the State's practice as a whole, so the same answer is likely.
- **No Michigan statewide feed on a State site can be automated.** That is three of the five in the plan. The other two, Strategic Fund board packets and newspaper zoning notices, are not checked yet.
- Recorded in `docs/sources/mi_mpsc_dockets.md` and `docs/sources/mi_state_of_michigan_terms.md`. The reply itself is not in the repository.

**For the owner**

- **Michigan now depends on people reading by hand, or on sources not yet checked.** The radar has no form for entering a hand-read record. Building one is the way a Michigan docket could ever become a signal.
- Whether to send the two EGLE requests anyway.
- Whether to ask the agencies for a periodic list of new cases and pending permits. Not asked.

## November 20, 2026 — M7: public site and alerts

**Built**

- **Nine public pages** in `web/`: the map and list of confirmed alerts, a page for each state, a page for each of the 30 Texas and 83 Michigan counties, the alert page, methodology, corrections, signup, the subscriber's own page and unsubscribe. 127 pages build.
- **The alert page** carries the word confirmed, the date, and for each record its own number, a link to the agency, the time the radar read it and the fingerprint of its copy. It has a corrections link.
- **The map** is MapLibre with OpenFreeMap tiles. Its terms are in `docs/services/openfreemap.md`. An alert with no point on record is in the list and not on the map.
- **Signup with double opt in.** The person picks states, optional counties and each alert or a weekly digest, and gives an address. The emailed link is the second opt in. `confirm_subscription()` checks for itself that the sign-in service proved the address.
- **Unsubscribe** by the link in every email, with no sign-in. The page asks for one press of a button, so a mail scanner that opens the link removes no one.
- **Corrections.** Anyone may send one through `submit_correction()`. Only administrators read them, on the administrator desk, and mark them handled. The database records who handled each one.
- **The alert email job,** `pipeline/alert_email.py`, by state, as one email per alert or one weekly digest per state. **It only does dry runs.** A dry run reports counts and one sample per state. It prints no address and no unsubscribe token, and it records nothing as sent. Every email carries the word confirmed, a link to the alert page, an unsubscribe link and the organization's postal address.
- **Database rules, tests written first,** in two migrations: the confirm and unsubscribe functions, county lists that must be codes in a selected state, corrections, a send ledger so an alert reaches a person once, and an email run log that holds no address.
- **Each signal now carries its record's own number,** such as a well report's tracking number, and the public view passes it on. `RULES_VERSION` is 2026-11-20.3.
- The methodology page lists the sources the radar reads and the ones it does not, taken from `config/` at build time. A test fails if that copy is out of date.
- `scripts/dev_seed.py --publish-sample` publishes two alerts marked as samples on a local database.
- 64 new Python tests and 8 new front-end tests. 677 Python tests and 12 front-end tests pass locally.

**Verified in a browser, on the local stack**

- The home, Texas, county, alert and methodology pages, with two sample alerts. **This time screenshots worked, so the layout was seen,** at desktop width and at phone width. The four pages checked at 375 pixels did not scroll sideways.
- Signup: states, a county, each alert. The link in the local test inbox landed on the account page, which saved the choices and confirmed. One insert, one confirm, no repeated requests.
- Changing to a weekly digest and saving. Stopping all alerts. Signing up again while signed in, which showed the one step left, and confirming.
- Unsubscribe by token: a malformed token, a good one, and the same one again.
- **With only the anonymous key, asked directly of the database:** 401 for subscribers, corrections, the send ledger and the email run log. A refusal to confirm a subscription. `false` for a made-up unsubscribe token. A refusal for a correction that pointed at an alert that is not public.
- A correction sent from an alert page, then read and marked handled by an administrator. The database recorded the administrator and logged it.
- A dry run of the weekly digest against that subscriber: 1 message about 2 alerts and nothing recorded as sent. A later dry run showed on the administrator desk.
- The local data was reset afterward.

**Faults found and fixed**

- **Two records from one archived file looked like one record listed twice** on the alert page: same source, same link, same fingerprint. Each record now shows its own number.
- A date shown from a moment was the day in UTC. An alert published at 8 in the evening in Texas showed the next day. Pages now show the reader's own day, and emails the day in the alert's state.

**Not verified**

- **The map in a browser that is in view.** The test pane was hidden and ran no animation frames, so the map painted only when a frame was forced. It was seen drawn correctly twice, on the home page and the Texas page, with both points in place. It was not seen on a county page or an alert page.
- Keyboard-only use and a screen reader.
- **Real email of any kind.** No sender for a real provider is written. Deliverability, the provider's batch interface and one-click unsubscribe headers are all untested. Mail providers have their own rules for bulk senders. Check them before sending.
- Whether the corrections brake holds against a real flood. It stops at 30 an hour for everyone together. It cannot tell one anonymous sender from another.
- Anything hosted.

**For the owner**

- **The owner gave the postal address the same day and it is in `config/email.yaml`.** Every email closes with it. The site's address is still not set, so the job still cannot send.
- **The methodology page is my wording.** It states what the system does today, including that the scoring numbers are placeholders and that no Michigan source is read. Read it before launch.
- **Michigan is offered on the signup form, and no Michigan source is read yet.** The form says so next to the tick box.
- **Double opt in rests on the sign-in service's emailed link.** One email both signs a person in and confirms them. On a hosted project its wording must fit both.
- **A subscriber who stops their alerts still has an account.** Their address stays with the sign-in service until someone deletes the account. No page does that yet.
- **A reversed alert comes down at once. Email already sent cannot be recalled,** and nothing sends a correction notice.
- **"Open the record at its source" for a well report still opens the 145 MB download.** The alert now gives the report's tracking number to find it by.
- The daily limit of 100 messages is the provider's free tier, checked on its pricing page today. The 20 dollar tier has no daily limit. The limit is per run of the job.
- Every page still asks search engines to stay away. Lifting that is part of making the site public.

## November 20, 2026 — M6: reviewer app

The owner chose Astro for the front end and sign-in by emailed link.

**Built**

- **`web/`, an Astro site.** Five pages under `/review/`: sign in and apply, the reviewer terms, the queue, one site, and the administrator desk. See `web/README.md`.
- **The site page** shows why a site scores what it does, every signal with its reason, the record's own row, the address and hash of the source, the decisions so far and the review form. Confirm and reject stay disabled until the reviewer ticks that they opened each source.
- **The administrator desk** lists applications with the applicant's email and note, approves and suspends reviewers, and shows sites flagged as the same place, records held back by number, recent runs and the audit log.
- **Administrators draft, publish and take down an alert, and fold one site into another,** from the site page.
- **Database rules, tests written first.** Three migrations' worth in two files:
  - A site is rejected when a rejection stands and no confirmation does. Reversing it, or suspending the reviewer who made it, returns the site to review. Before this a rejection blocked publication and nothing recorded it on the site.
  - `reviewer_directory()`: applicants and reviewers with their email, for administrators only.
  - `merge_sites()`: an administrator folds one site into another in the same county. A site that was reviewed is never folded away.
  - `document_refs`: the address, retrieval time and hash of any document, for approved reviewers. No text. A reviewer could not otherwise get from a signal on a restricted list to the public record.
  - An applicant can say who they are, once.
- `scripts/dev_seed.py` fills a local database from the test fixtures. It refuses any other database.
- CI now type-checks, tests and builds the front end.
- 31 new tests. 613 pass locally, database tests included, plus 4 front-end tests.

**Verified in a browser, on the local stack**

- Sign-in by emailed link, with the email caught by the local test inbox.
- An application, and the applicant's pending screen. **A pending applicant, signed in, got zero rows from every table and a refusal for a review, a merge and the reviewer directory,** asked directly of the database with their own session.
- The owner's by-hand step that makes the first administrator.
- The queue and a site page.
- A confirm. The button is disabled without the tick, and when the form was forced past it the database refused.
- Publishing an alert. It then appeared in the public view with its two sources, read with the anonymous key. The anonymous key got 401 for every table.
- Reversing the confirmation, which took the alert down and returned the site to review.
- Approving the applicant from the administrator desk. The approval was logged with the administrator's account.
- Folding an invented second site into the first. Its signal moved and the merge was logged.
- The local data was reset afterward.

**A fault found and fixed**

- The page hung after an application was sent. The account hook re-subscribed to sign-in events on every event and reloaded in a loop. It now subscribes once.

**Not verified**

- **How the pages look.** The browser pane was hidden for the whole session, so no screenshot was taken. Structure, text and behavior were read from the page. Layout, spacing and the phone-width view were not seen by anyone.
- Keyboard-only use and a screen reader.
- Anything hosted. No hosted database, no real email, no deployed site. Each is a section 11 decision.

**For the owner**

- **The reviewer terms are a placeholder I wrote.** The page says so in red. They must be adopted or replaced before any reviewer is approved.
- **The first administrator is made by hand in SQL.** `web/README.md` has the statement.
- **"Open the source record" for a well report opens the board's 145 MB download,** because that is the address the record came from. Whether each report has its own public page is still unverified. A reviewer needs a better link.
- **After a merge the kept site's score is stale** until the next processing run.
- Settings such as the number of confirmations are shown on the administrator desk and not changed there.
- A reviewer sees other reviewers' decisions and notes, and not their names.

## November 20, 2026 — TCEQ air permits get a county

The owner approved fetching the application file of each air permit row that is a signal.

**Built**

- **`pipeline/tceq_applications.py`.** For an air permit signal with no county, processing fetches the application file its row links, once, and reads the county from the form's address block, the head of a TCEQ letter or a review sheet. Every line found must name the same county. Running text is never used.
- **The text reader opens files embedded in a PDF.** TCEQ sends New Source Review applications as a portfolio: a cover page with the application inside. It also now releases each page after reading it. A 528-page file went from 2.7 GB of memory to under 500 MB.
- The file is stored restricted. Only the address lines, the NAICS code and the stated line of business are copied to the signal.
- Off unless processing is run with `--fetch-applications`. At most 25 files a run.
- 27 new tests. 582 pass locally, database tests included.

**Verified live, on the local database**

- Two files fetched by hand first, one of each kind, to read their layout.
- Then one full run. **Of 12 rows, 9 files gave a county.** Six are in the test counties: Bexar, Bosque, Carson, Ellis, Hill and Travis. Three are outside: Armstrong, Childress and Collin. One file states its county only in a sentence and gave none, as designed. Two files are over the 50 MB limit and were refused.
- Ten files, 208 MB in all, 2 MB to 50 MB each.
- **Six air permit signals now sit on sites. There are 11 sites, up from 6.**
- **Still no site reaches the review threshold.** The highest is 35.7 against 40: one company's air permit and its well reports in Travis County, with the bonus. Both signals rest only on the company being on the Comptroller's list, and its own application calls the site an automobile manufacturing facility. The placeholder threshold kept it out of the queue.
- A fault found and fixed: one file's text held a NUL character, which the database refuses. The first run failed on it.
- The data and the files were deleted afterward.

**What the run showed that is not fixed**

- **Two sites that look like one.** An air permit names "CyrusOne LLC" in Bosque County and a well report names "CyrusOne Bosque LLC" in Bosque County. They are two company names, and the permit's file gave no coordinates, so they are two sites. Nothing flags them as related yet.
- **Two files are over the size limit.** The limit for this source can be raised in `config/sources.yaml`. Their size is not known.
- **This was the fifth download of the 145 MB TWDB file in one day,** all for local checks. A scheduled job would fetch it once a week.

**Still unverified**

- An application that is a scan, or one for a site with no street address.
- A run from GitHub's servers. There is no workflow file for processing.

## November 20, 2026 — M5: scoring and site clustering

**Built**

- **Scoring**, `pipeline/score.py`, with its tests written first. Each signal type counts once, by its strongest signal. A signal is worth its type's points, times how sure it is, times its decay. The bonus is paid once, when enough types from different sources are dated within the window of each other. The breakdown says where every point came from, and is stored with the site.
- **Clustering**, `pipeline/cluster.py`. Signals join a site only inside one county, for a reason stored with the signal: the same company, coordinates within 1,000 m, or the same project name or number. The same company more than 5,000 m apart is two sites.
- **Sites in the database**, `pipeline/sites.py`. It runs at the end of every processing run. A new signal joins the site it fits or starts one. Every site is scored again. A candidate at or above the review threshold enters the queue.
- **A database guard on site status.** A job can score a site and move a candidate into the queue. It cannot confirm or reject a site, or take either back. Before this, nothing stopped a job that held the service key. Tests written first.
- ERCOT planning signals now carry ERCOT's own project number, such as 25RPG020, so next month's update of a project joins this month's.
- One migration: `sites.score_detail`, `sites.scored_at` and the guard.
- 69 new tests. 555 pass locally, database tests included.

**Rules that keep a reviewer's work stable**

- A signal already on a site never moves. A site is never merged, split or deleted by a job.
- A signal that fits two sites joins the older one, and both are flagged in the run log for a person to look at.
- A rejected or confirmed site keeps receiving its signals and its score. Its status does not change.
- A site is never taken out of the queue when its score decays.

**Verified live, on the local database**

- Three collectors ran for real, and the well extract collected an hour earlier was reused. The laptop restarted mid-run and cleared the scratch folder, so the extract was rebuilt from the stored text and the other three feeds were collected again.
- Processing made 62 signals. **50 of them became 6 sites**: 13, 16, 13, 6, 1 and 1 signals each. The two NTT companies in Travis County became one site, joined by coordinates.
- **The 12 air permit signals are on no site.** The TCEQ lists give no county.
- **No site reaches the review threshold.** The highest score is 11.4 against a threshold of 40. A site needs two signal types to get there, and the only feed that could supply a second type has no county. With today's feeds the reviewers' queue would be empty.
- The data was deleted afterward.

**Choices for the owner to accept or reverse**

- **Confidence scales the points.** The plan gives points and a half life. It does not say what a signal's confidence does. Here a weak reason is worth less than a strong one.
- **One contribution per signal type.** Sixteen soil borings on one day are one fact.
- **Two types read from one source are not independent** and earn no bonus.
- **The bonus does not decay.** It is paid when the signals are within the window of each other, however old they are. It is 20 against a threshold of 40, so an old pair alone does not enter the queue.
- **A signal with no company, coordinates or project name makes no site.** It names a county and nothing to hold it to a place.
- The two distances, 1,000 m and 5,000 m, are placeholders in `config/scoring.yaml`, like every number there.

**Still unverified or not built**

- **Every threshold is a placeholder.** The backtest in M9 sets the real ones.
- **TCEQ air permits cannot join a site.** The fix is a county for each row. The 12 rows that are signals each link an application file, which should state the county. Fetching those 12 files, and not all 623, would be a small change to the collector. Not done: it changes what the TCEQ collector fetches, so the owner decides.
- **Two sites that are the same place are only flagged.** Merging them is a person's job and there is no screen for it yet. That is M6.
- A site's place is the middle of its signals' coordinates, and those come from drillers and are not verified by the state.
- A site is labeled once, from its first signal. A site that starts from a planning file is labeled with a project number.
- Nothing ran on a hosted database or from GitHub's servers. There is no workflow file for processing or scoring.
- Michigan: no signal to score.

## November 20, 2026 — M4: processing

M3 has no feed cleared to build, so M4 went first with the owner's go-ahead.

**Built**

- **Keyword rules**, `pipeline/classify.py`. Direct terms, code words and "Project" code names from `config/keywords.yaml`. Each hit keeps the words as written and their place.
- **Acres, megawatts and dollars**, `pipeline/quantities.py`. A number counts only with its unit next to it. Acre-feet and megawatt-hours are not read as acres and megawatts.
- **Company names**, `pipeline/entities.py`. One spelling per name. "Example LLC" and "Example Inc" stay two companies.
- **The hold-back for names of people.** A record's named party is used only when the name shows a company or a public body. Anything else makes no signal and is counted by its record number, never by its name.
- **County assignment**, `pipeline/counties.py`. From a county column, from "Hood County" in a text, or from a list such as "Bexar and Medina counties". All 254 Texas counties are recognized, from the Census county file, so a file about a county outside the 30 is set aside. The 30 are unchanged.
- **Census geocoder client**, `pipeline/geocode.py`, with a source note. The county comes from the point, never from the city in the address. Every answer is archived and reused.
- **Signals**, `pipeline/signals.py` and `pipeline/process.py`. A stored document becomes dated signals for three feeds: TCEQ pending air lists, TWDB well reports and ERCOT planning group files. A record becomes a signal only when it gives a reason: it says "data center", uses a code word, or names a company on the Comptroller's registered data center list. The reason and the matched words are stored with the signal.
- **Optional model triage**, `pipeline/triage.py`. Off by default. Every call is logged with its cost, and no call is made that could pass the monthly cap.
- **Two migrations.** Lists that name people are stored restricted. The same fact is stored once. An entity is a company or a public body and nothing else. A log of processing runs. A log of model spend.
- 196 new tests. 486 pass locally, database tests included.

**Database rules, tests written first**

- A reviewer cannot read a restricted document. An administrator can. Nobody can open one through the app.
- A reviewer reads the signal made from one row of a restricted list, which holds only that row.
- The TCEQ lists and the TWDB extract are marked `personal_rows: true` and are stored restricted from the moment they are collected.

**Verified live**

- The Census geocoder: three requests, saved as fixtures. No key, no robots file, no stated limit on single requests.
- The price of the triage model, read from the published price page on November 20, 2026: $0.10 per million tokens in and $0.50 out, for prompts up to 100,000 tokens.
- One real ERCOT planning file, fetched once. It showed two flaws, both fixed: it writes "Bexar and Medina counties", and its table headings were read as county names.
- **The whole chain once, into the local database.** Four collectors ran for real and stored 17 documents. Processing read 16 of them and made 62 signals: 12 air permit rows of 624, 49 well reports of 8,340 and 1 planning file of 10. Four well reports were held back. A second run added nothing. The data was deleted afterward.
- That run also showed a noisy rule. A city's well addresses that say "Project Between" two streets were read as code names, 19 false signals of 81. The stoplist in `config/keywords.yaml` now covers them.

**Departures from the plan, each for the owner to accept or reverse**

- **Additions to the data model**: `documents.restricted`, `signals.fingerprint` and `county_fips`, `entities.kind` and `match_key`, and the tables `processing_runs` and `model_usage`.
- **ERCOT planning group files are stored as `transmission_filing`.** The plan's list of signal types has none for them. It is the closest.
- **Most records make no signal.** The plan does not say which rows of a statewide list count. The rule here is a stated reason, so a well drilled by a company with a new name and no telling word is not caught from that feed alone.
- **One new dependency**, the `anthropic` package, installed even while triage is off.

**Still unverified or not built**

- **The model has never been called.** That needs an API key, which is a secret for the owner to add. One test sends a request through the real SDK to a fake server.
- **Parent companies are not resolved.** `entities.parent_entity_id` stays empty. That needs the Comptroller's API key or its bulk file, neither of which is in hand.
- **No feed uses the geocoder yet.** The well reports carry a county and the TCEQ lists carry no address.
- **TCEQ signals have no county.** The lists give none. They can join a site only through the company's name.
- **A planning file that names a city or a utility and no county is not placed.**
- **Index and meeting pages are not read for signals**, only the files. Text inside pictures in a slide deck is still not read.
- **A match on the Comptroller's list is weak.** The list holds every company with a registered data center, so a carmaker's soil borings at its factory make signals too. The reason is stored and the confidence is 0.5.
- **One site can make many signals.** Sixteen soil borings on one day are sixteen signals. Grouping them is M5 work.
- **Reading documents again only adds signals.** A signal made by a rule that was later tightened stays until a person removes it.
- **Nothing ran on a hosted database or from GitHub's servers.** There is no workflow file for processing.
- Michigan: no document to process.

**Triage cost, for the owner's decision**

- One question costs at most $0.0018. A cap of $5 a month allows at least 2,700 questions.
- To switch it on: add `ANTHROPIC_API_KEY` as a secret, and set `RADAR_TRIAGE=on` and `RADAR_TRIAGE_MONTHLY_CAP_USD`.

## November 20, 2026 — M2: Comptroller local agreements read and held. M2 status

No code changed.

**Verified live**

- The overview, search form and results page were fetched once each, and one search was read in a browser.
- The results page holds no data. A script fills it from `api.comptroller.texas.gov`, and its download buttons point to seven CSV files on `assets.comptroller.texas.gov`.
- **Both of those hosts answer 403 for their robots file.** Our fetcher stops there, as built. No CSV was downloaded.
- The database holds 4,397 Chapter 380 and 381 agreements, 1,490 abatements, 1,255 zones and 991 post-abatement valuations.
- **Chapter 380 and 381 agreements are due within 14 days.** The earlier note called the whole feed lagging. Only the Chapter 312 part is.

**Held**

- The feed stays manual, now marked restricted. The source note gives three options. The recommended one is to ask the Comptroller first. A sixth request is drafted in `drafts/permission-requests.md` and not sent.

**Where M2 stands, in the plan's table order**

| Feed | State |
|---|---|
| Newspaper public notices | Closed by its terms. Request drafted, not sent. |
| TCEQ pending air, older lists | Collector built. |
| TCEQ pending air, portal | Open. Waits on the owner's choice of method. |
| TCEQ stormwater | Closed by robots rules. Manual. |
| ERCOT planning group | Collector built. |
| ERCOT large load | Collector built. |
| PUC Interchange | Held. Request drafted, not sent. |
| TWDB well reports | Collector built. Keeps an extract. |
| Comptroller registered data centers | Collector built in M1. |
| Comptroller local agreements | Held. Request drafted, not sent. |
| Entity lookup | M4. Needs an API key. |
| Agendas | M8. |

Five collectors exist. Every feed in the table has a source note. Each collector has fixtures, tests and a workflow file. No workflow has run, and none has a schedule.

## November 20, 2026 — M2: slide decks are read, and the TWDB collector

**Built**

- **Text from slide decks, Word files and zip files**, in `pipeline/extract.py`. A deck gives each slide's text in presentation order, then its speaker notes. A zip gives the text of each readable file inside and lists every file with whether it was read.
- **`collectors/tx/twdb_well_reports.py`.** The owner chose the weekly extract. The collector downloads the board's file, keeps rows in the 30 counties that are not domestic or stock wells and were submitted in the last two years, and stores that extract. It leaves out the owner's mailing address and every driller column. The board's file is never written to disk.
- **Two changes to the shared collector code.** Config can raise the size limit for one source. A collector can store an extract in place of the file, with the file's address, time, size and hash recorded.
- A workflow file for the TWDB feed, started by hand only, dry run, no schedule.
- `tx_twdb_well_reports` is now `method: http`, weekly, with a 300 MB limit.
- One new dependency, `defusedxml`, for reading the XML inside Office files safely.
- 34 new tests. 290 pass locally, database tests included.

**Verified live**

- The slide deck reader on two real ERCOT files: a deck of 8 slides, and the committee's zip file, which holds one deck of 15 slides. Text came out of every slide.
- One full run of the TWDB collector against the real file: 715,155 rows read, 8,325 kept, 1.5 MB stored, 9 seconds. Only the extract was on disk afterward.

**Still unverified**

- Text inside pictures and embedded charts in a slide deck is not read. Both real decks hold their charts that way.
- Spreadsheets and the older binary Office formats are not read.
- TWDB rows that are kept can still name a person. The M4 check has to cover them.
- Neither new workflow file has run.

**Next in M2**

- Comptroller local agreements. Then M2 is done except for the feeds that are held or closed.

## November 20, 2026 — M2: TWDB well reports read and held

No code changed. No collector is written for this feed.

**Verified live**

- The download page was fetched once. The bulk file was downloaded once by hand, read and deleted. Its hash is in the source note.
- The file is 145 MB zipped and 823 MB unpacked. The fetcher refuses anything over 50 MB.
- The main table holds 715,155 reports. About 41 percent are household wells with a person's name and address.
- The 30 test counties hold 194,368 reports, 804 of them submitted in the last 30 days.
- Data center operators appear as well owners in 2026 reports, under several kinds of use.
- Reports arrive a median of 36 days after drilling ends.

**Why it is held**

- Built like the other collectors, this feed would download 145 MB a day and archive every copy of a file that names about 293,000 households.
- The source note lists four options. The recommended one is weekly, keeping an extract of non-household rows in the 30 counties and not the file. That departs from the rule that the original is archived, so the owner decides.

**Still unverified**

- The other 21 tables and the 45 MB shapefile.
- Whether a report has a public address a reviewer can open from its tracking number.

**Next in M2**

- Comptroller local agreements. Then M2 is done except for the feeds that are held or closed.

## November 20, 2026 — M2: ERCOT large load reports

**Built**

- `collectors/tx/ercot_large_load.py`: reads the Large Load Working Group and Technical Advisory Committee indexes, the meetings near today and their files. For the committee it fetches only files with "large load" in the title.
- `collectors/tx/ercot_meetings.py`: the ERCOT index and meeting parsers, moved out of the planning group collector so both collectors share them. The planning group collector behaves as before.
- A workflow file, started by hand only, dry run, no schedule.
- `tx_ercot_large_load` is now `method: http`, monthly. Its address is now the working group index.
- 12 new tests. 256 pass locally, database tests included.

**Verified live**

- Six ERCOT pages fetched once each. Four are saved as fixtures.
- One dry run of the collector: 18 documents, no errors.
- **Where the reports are.** The plan had example files and no index. The working group and the committee each have an index page in the planning group's layout.
- **Older planning group meetings.** `/committees/other/rpg/2025` exists, links 14 meetings and links year pages back to 2003. This answers where the backtest finds them.

**Still unverified**

- The committee's November update is a 4.4 MB zip file. It is stored as it comes. Nothing reads inside a zip yet.
- Slide decks and spreadsheets are stored with no text extracted.
- A committee file about large loads whose title lacks those words would be missed.
- The workflow file has never run.

**Next in M2, in the plan's table order**

- TWDB well reports, then Comptroller local agreements.

## November 20, 2026 — M2: TCEQ pending air permit lists

**Built**

- `collectors/tx/tceq_air_pending_legacy.py`: reads TCEQ's two lists of pending air permit applications on its older site. One parser for both.
- It asks for each page with the ETag of the copy it holds and compares rows, so the daily rebuild of one page is not stored again.
- It does not fetch the application files the rows link, 624 of them. It keeps their addresses.
- A workflow file, started by hand only, dry run, no schedule.
- `tx_tceq_air_pending_legacy` is now `method: http`, weekly. It was monthly.
- 19 new tests. 244 pass locally, database tests included.

**Verified live**

- Both lists and the start page fetched once each. The two lists are saved as fixtures.
- One dry run of the collector: 2 documents, no errors.
- **The Title V list is still updated.** Its newest application was received November 16, 2026. The earlier note said both lists stop at August 2026. The start page says that only of New Source Review.
- The New Source Review list shows "Data Updated: 8/28/2026" and 296 rows. The Title V list shows 328.
- Eight rows name a data center, four on each list.
- **Two rows name a person as the applicant.** The fixture replaces those names. Its `.meta.json` says so.

**Still unverified**

- The lists give no county. Matching a row to a place needs the application file or another record.
- No application file was fetched. Their size and form are unknown.
- Why two New Source Review rows carry September 2026 dates, after the "Data Updated" date.
- How long TCEQ keeps the New Source Review page online.
- The workflow file has never run.

**Open for M4**

- A row whose applicant is a person must be held back before a reviewer or the public sees it. Nothing checks for that yet.

**Next in M2, in the plan's table order**

- ERCOT large load reports, then TWDB well reports and Comptroller local agreements.

## November 19, 2026 — M2 started: ERCOT planning group collector

**Built**

- `collectors/tx/ercot_rpg.py`: reads the planning group index, the meetings near today and the files those meetings list. Parsers for the index and for a meeting page.
- The collector base class can now follow links from a page, ask for a file it already holds with its ETag, and skip a page whose content did not change. It stops after 500 URLs.
- `collectors/run.py`: one command to run a collector. A dry run keeps nothing. A real run needs a database and an archive folder.
- Workflow files for the two collectors that exist, ERCOT and the Comptroller list. Both start by hand only and run dry. No schedule.
- `tx_ercot_rpg` is now `method: http`.
- 30 new tests. 225 pass locally, database tests included.

**Verified live**

- Three ERCOT pages saved as fixtures: the index and two meeting pages.
- One ERCOT file fetched by hand to check its headers and text. It is 1.6 MB, so it is not committed. Its hash is in the source note.
- One dry run of the whole collector against ERCOT: 13 documents, no errors.
- ERCOT's pages change a few bytes on every request. The collector compares content, not bytes.

**Still unverified**

- The workflow files have never run. The repository variable `RADAR_CONTACT` is not set, so a run started now would refuse to fetch.
- A run from GitHub's servers. ERCOT's site sits behind a screening service.
- Where ERCOT lists meetings before 2026. The backtest needs them.
- Extraction of company, megawatts and county from the files. That is M4.

**Next in M2, in the plan's table order**

- TCEQ legacy pending air lists, then ERCOT large load reports, TWDB well reports and Comptroller local agreements.
- Held or closed: newspaper public notices, PUC Interchange, TCEQ stormwater. The TCEQ portal waits on the owner's choice of method.

## November 19, 2026 — TCEQ portal read, EGLE contacts found

No code changed. This entry covers source checks and letters.

**Verified live**

- **TCEQ Permit Search Portal, read in a browser.** No login, no terms of its own and no robots rules. Its footer links to the TCEQ web policies, which call site content public domain. Nothing read restricts automated access. `tx_tceq_air_pending` now has its own note and is marked verified. It stays manual.
- **How the portal search works.** A circle around a point, 1 to 60 miles, with filters for status and permit type and no date filter. One search was run, for Hood County. The data comes from three POST calls on the same host.
- **EGLE contacts.** The MiEnviro Portal contact page gives one address for air, one for water and a general help desk. They are in the two EGLE notes.
- **MiEnviro Portal.** Its public notice search needs no account. Alerts on new notices need one. Read from search results only. Nothing was requested from the portal.
- The pending air permit lists moved to `egle.state.mi.us`. The config has the new address.

**Still unverified**

- The bodies of the portal's data calls, its page size and whether any record carries a received date.
- Whether the Michigan.gov terms cover `egle.state.mi.us`, and which office can grant a written agreement.

**Needs the owner**

- A method for the TCEQ portal: the page's own search calls or a browser. The collector base class makes GET requests only, so either choice needs new code.
- Four requests are drafted and not sent: Texas Press Association, Texas PUC and two to EGLE. They are in `drafts/permission-requests.md`, which is not committed.

## November 19, 2026 — M1 closed: first real collector

The owner chose the public contact address for the user agent. That unblocked the last M1 step.

**Built**

- `tests/fixtures/tx_comptroller_data_centers/`: a saved copy of the Comptroller's registered data center page with its URL, retrieval time and hash.
- `collectors/tx/comptroller_data_centers.py`: the collector for that page and a parser for its two tables. 70 qualifying data centers and 113 qualifying large data center projects.
- 11 tests. The collector fetches through the real robots pattern, archives the page under its hash, logs the run and finds nothing new on a second run. A changed layout stops the parser.
- `tx_comptroller_data_centers` is now `method: http` in `config/sources.yaml`. It is the first feed cleared for automatic fetching. Nothing is scheduled yet.

**Verified live**

- One request to the Comptroller's page through `collectors.capture`, with the contact address in the user agent. The robots check passed and the page answered 200.
- The page has no county or address column, as the build plan said.
- Every party named on the page is a company.

**Still unverified**

- How often the state updates the page.
- How to place these 183 registrations in a county. The page gives no location, so the baseline layer needs FracTracker or another source for that.
- The run against the hosted database and a hosted archive. Both wait on the Supabase project, which needs the owner's go-ahead.

**Also today**

- The owner sent the request for a written agreement to the Michigan commission. The requests to the Texas Press Association and the Texas PUC are drafted and not sent.
- Counts: 195 tests pass locally.

## November 19, 2026 — Michigan docket site check

The owner asked for a check of the Public Service Commission's E-Dockets site, which is on a separate host from Michigan.gov.

- **Result: restricted. `mi_mpsc_dockets` stays manual.** The robots file allows everything. The site has no terms of its own. Its footer links to the State of Michigan policies page, which bars automated access without a written agreement.
- The feed's address in `config/sources.yaml` now points at the docket site. The note is `docs/sources/mi_mpsc_dockets.md`.
- A person can read the case list by hand. New cases appear sorted by open date, with no account needed.
- The case list shows complaint cases under the names of private households. Those names stay out of fixtures and out of anything we publish.

**Verified live:** the robots file, the home page and the help page of the docket site, and the policies page its footer links to. One request each.

**Still unverified:** whether the State grants written agreements for this use, the sign-up step for filing notices and the archived orders search on a third host.

## November 19, 2026 — Texas source checks ahead of M2

Done while M1 waits on the contact address. Terms of use and robots rules were read for every Texas statewide feed in BUILD_PLAN.md section 6. Each has a note in `docs/sources`. No collector was written and no record page was fetched.

| Feed | Result |
|---|---|
| Newspaper public notices | **Restricted.** Terms forbid automated collection and any database or archive of the content, with liquidated damages. |
| TCEQ pending air permits, portal | Not verified. A JavaScript application with no robots file. Needs a person in a browser. |
| TCEQ pending air permits, static lists to August 2026 | Allowed. Useful for the backtest. |
| TCEQ stormwater notices of intent | **Blocked.** robots.txt closes the whole host. |
| ERCOT planning group files | Allowed. Index page found. |
| ERCOT large load reports | Allowed. No index page found yet. |
| PUC Interchange filings | **Held.** Access is open, but the link policy asks for a permission request before copying content. |
| TWDB well reports | Allowed. One nightly bulk file. The start page moved. |
| Comptroller registered data centers | Allowed. |
| Comptroller local development agreements | Allowed. |
| Comptroller entity lookup | Allowed through the bulk file and the official API. The API needs a key the owner registers for. |

**What this changes**

- The plan's strongest Texas signal, the 30 day abatement notice from the statewide notice site, cannot be collected as planned. The same event appears on commissioners court and city agendas (M8) with a shorter lead time.
- Of the plan's four high-weight Texas signal types, one is open today (ERCOT transmission planning), one is held on a permission question (PUC), one needs a browser check (TCEQ portal) and one is closed (notices).
- The well reports feed is simpler than planned: one file a day, no crawling.

**Also built**

- `collectors/capture.py`, a by-hand tool that saves one real page as a test fixture through the same fetcher and rules as the collectors. 12 tests.

**How the checks were done**

- Two research passes read robots files and policy pages with a user agent that named this project, at most five requests per host. They submitted no forms and stopped at any refusal.
- Every restrictive finding was read a second time, directly: the public notice terms, the TCEQ robots file and the PUC link policy.
- Counts: 184 tests pass locally.

**Still unverified**

- Every item listed under "not verified" in each source note. The main ones: no record page, search result or file has been fetched from any of these sources, and the TCEQ portal's terms are unread.
- Texas parcels and local agendas have not been checked. Agendas are M8.

**Waiting on the owner**

- The contact address for `RADAR_CONTACT`.
- Public notices: ask the Texas Press Association for permission, use its email alerts by hand, or rely on agendas.
- PUC Interchange: ask the commission, or decide docket filings fall outside its link policy.
- The three Michigan feeds closed by the state's site terms.
- An API key for the Comptroller, when entity lookup is built in M4.

## November 19, 2026 — Owner decision on the Texas county list

The owner decided to keep the plan's five added counties: Dallas, Taylor, Bexar, Travis and Harris. The FracTracker recount stays on file in `docs/sources/us_fractracker.md` as a second measure. `config/counties_tx.yaml` is unchanged.

## November 19, 2026 — Published, first CI run

- The repository is public at https://github.com/th4449/radar with the owner's approval.
- Commits use the account's GitHub no-reply address. The first two local commits carried a personal address and were rewritten before anything was pushed.
- CI passed on the first run: secret scan clean over the full history, lint clean, all five migrations applied from scratch and 172 tests passed with none skipped.
- The workflow's actions were then moved to their current major versions, because GitHub warned that the older ones target a retired Node.js.

**This closes M0.** M1 still lacks the fixture from a real page, which waits on `RADAR_CONTACT`.

**Reminder.** GitHub disables scheduled workflows in a public repository after 60 days without activity. No scheduled workflow exists yet. M10 monitoring has to watch for this.

## November 19, 2026 — M1 Core library

**Built**

- `collectors/base.py`: the fetcher, the archive and the collector run loop.
  - The fetcher refuses a source with no source note, a restricted source and, unless a person runs it by hand, a manual source.
  - robots.txt is read before every request and again on every host a redirect leads to. An unreadable robots file counts as no. There is no switch to skip the check.
  - One request per host every 5 seconds, longer if robots.txt sets a crawl delay. Retry with backoff on server errors. A 401, 403, 451 or repeated 429 stops the run and is never retried.
  - Conditional requests with ETag and Last-Modified, a 50 MB size cap and a user agent that names the collector and the contact address in `RADAR_CONTACT`.
  - The archive stores each original under its SHA-256 hash with URL and retrieval time. Local disk only for now.
- `pipeline/extract.py`: text from HTML and PDF. The kind is read from the bytes, not the header. A PDF with no text layer is flagged for character recognition, which is M8 work.
- `pipeline/store.py` and the `collector_runs` table: every run is logged with its status, counts and error. Documents are stored once per source and hash.
- A sample collector runs end to end on synthetic fixtures: fetch, archive, extract, store, log.
- 67 new tests. 172 in all. None touches the network.

**Changed from the first draft**

- Python's built-in robots parser ignores wildcards and rule length. It would have allowed paths that the Texas Comptroller's `Disallow: /*/` rule forbids. Replaced with Protego, which follows RFC 9309. Tests cover the Comptroller's pattern.

**Verified live**

- State of Michigan website terms bar automated access without a written agreement. Three Michigan feeds are now marked restricted. See `docs/sources/mi_state_of_michigan_terms.md`. **This needs the owner's decision before M3.**
- Texas Comptroller robots rules allow `/taxes/` and `/economy/`, and the site says its information is public domain. See `docs/sources/tx_comptroller_data_centers.md`.

**Not done: waiting on the owner**

- The sample collector has not run against a saved copy of a real page. That takes one live request to the Comptroller's data center list, and the fetcher will not make it until `RADAR_CONTACT` holds the project's public contact address.

**Still unverified**

- The fetcher against a real server. Every test uses a fake transport.
- The hosted archive backend. It comes with the Supabase project.
- A real PDF from a source. The PDF tests use small files written by the test helper.

## November 19, 2026 — M0 Scaffold

**Built**

- Repository layout from BUILD_PLAN.md section 4, `CLAUDE.md`, MIT license, a `.gitignore` that keeps secrets, dumps and raw archives out.
- Config files with strict validation: 22 feeds in `sources.yaml`, the 30 Texas counties, all 83 Michigan counties, keywords and placeholder scoring. Every feed starts as `method: manual`. The loader refuses to mark a source automated unless it has a verification date and allowed robots status.
- Four migrations for the section 5 tables with PostGIS and row level security on every table.
- 96 policy tests, written before the policies, plus 9 config tests. They cover every rule in section 7.
- CI workflow: secret scan, lint, a fresh migration run and the tests. A skipped database test fails CI.

**Additions to the plan's data model**

- `app_settings` holds `confirmations_required` (default 1) and `admin_gate_enabled` (default on). Policies cannot read YAML.
- `alerts.approved_by` and `approved_at`, `reviews.reversed_at`, `reversed_by` and `reversal_note`, `audit_log.actor_role` and `detail`, `sources.slug`.

**Rules the database enforces beyond the plan's wording**

- The service role cannot approve, suspend or remove a reviewer, cannot write a review and cannot change settings. Approval is never automated.
- Nobody changes their own reviewer status, administrators included. The admin role is granted only by the owner by hand in SQL.
- A standing rejection blocks publication until an administrator reverses it.
- Reversing a confirmation takes a published alert down if it no longer has enough confirmations.
- A subscriber's address is copied from their account, so nobody can subscribe someone else's email. Administrators cannot read subscriber rows.
- The audit log cannot be updated, deleted or truncated.

**Verified live**

- Migrations apply from scratch to the local Supabase Postgres 17 and all 105 tests pass.
- The policy tests fail when a guard is switched off. Checked by disabling the reviewers, alerts and reviews guards and RLS on subscribers, one at a time.
- County FIPS codes come from the Census file `national_county2020.txt`.
- GitHub documents that scheduled workflows can be delayed or dropped under load, and that in a public repository they are disabled after 60 days without repository activity.
- Supabase lists the free plan at 500 MB with a pause after one week idle, and Pro at $25 with extra projects from $10.
- FracTracker's terms and robots rules. See `docs/sources/us_fractracker.md`.

**Texas county recount: differs from the plan. Decided later the same day: keep the plan's five.**

FracTracker's top five counties outside the organization's 25 are Dallas (27), Bexar (26), Williamson (13), Collin (11) and Tarrant (9). The plan's five are Dallas, Taylor, Bexar, Travis and Harris. In FracTracker, Travis has 6, Harris 3 and Taylor 1. `config/counties_tx.yaml` was not changed. Details and caveats are in the source note.

**Still unverified**

- The terms of every source in section 6 except FracTracker.
- Esri's terms for the ArcGIS host that serves the FracTracker layer.
- Whether the hosted Supabase project behaves like the local one for default privileges. The migrations revoke and grant explicitly so it should not matter.

**Open decisions for later milestones**

- M9 names control counties, and the 30-county set has none.
- The subscriber confirmation step (who sets `confirmed_at`) and the unsubscribe-by-token call are M7 work. Today no user can set `confirmed_at`.
- The local database uses ports 55320 to 55329 so it can run beside another Supabase project.
