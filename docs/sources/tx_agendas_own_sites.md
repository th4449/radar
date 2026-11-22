# Texas agendas on governments' own sites

- Source id: `tx_agendas_own_sites`
- What it is: the agenda page of each government that posts its agendas as files on its own website, and the agenda files that page links to
- Checked: November 21 and 22, 2026
- Result: **allowed for 52 of 111 governments, one site at a time.** 43 are closed or held and 16 are not read. **Five more counties are read on the sites their association provides.** See "The county association sites" below. **Two more cities are read whose files HeyGov keeps.** See "Two cities on HeyGov" below. 59 governments in all, on 60 pages.
- Collector: `collectors/tx/agenda_pages.py`
- Fixtures: `tests/fixtures/tx_agendas_own_sites/`, eleven real pages cut down to their agenda lists and three real calendar feeds
- Workflow: `.github/workflows/collect-tx-agendas-own-sites.yml`, started by hand only

The owner said on November 21, 2026 to build next for the governments that post agenda files on their own sites. There is no vendor here and no shared rule. Each site has its own robots file and its own terms, so each was read.

## Which governments were looked at

The agenda inventory listed 114 governments with files on their own sites. **76 of them had a row that an independent check confirmed.** Those were read on November 21, 2026. The other 38 were checked on November 22, 2026. See "The other 38" below. Four of them turned out to post elsewhere, so the inventory listed 110. Milam County was added the same day: see "Milam County" below. The inventory now lists 111.

| Of the 111 governments, on November 22, 2026 | |
|---|---:|
| Read | 52 |
| Closed by a robots file, their own or their file host's | 19 |
| Closed by their own terms | 10 |
| Built and hosted by CivicPlus, held with its platforms | 7 |
| Held for the owner | 4 |
| Refused the request | 3 |
| Confirmed, in a form the collector does not read. Terms not read | 8 |
| Row not confirmed, and none of the above | 8 |

## What was verified

**Robots files.** One identified request for the robots file of each of 81 hosts: the 76 sites and the hosts their agenda files sit on.

| Answer | Hosts |
|---|---:|
| Allows the agenda page and files | 55 |
| No robots file | 15 |
| Answers 403 for the robots file | 6 |
| Bars the page or the files | 4 |
| Request failed | 1 |

**12 governments are closed by a robots file:**

| Government | Why |
|---|---|
| Helotes, Sulphur Springs | The robots file bars the agenda page |
| Irving, Briarcliff | The robots file bars the files |
| Holliday, Nash, Richardson, Katy, Johnson County | The robots file answers 403. The fetcher treats a robots file it cannot read as a refusal |
| Tool, Trinidad | Their files sit on a site builder's host whose robots file answers 403 |
| Cresson | The robots request failed |

**Six more were closed by the first run.** Their own robots files allow the collector. Their agenda links lead on to a site builder's file host whose robots file bars the files. The fetcher reads the robots file of every host a request is sent on to, so it stopped there. They are Sealy, Balcones Heights, Bertram, Combine, Shavano Park and St. Hedwig.

**Each site's own terms.** Five research passes read the home page, footer and every terms, disclaimer, privacy and policy page of the other 64 sites. They copied the sentences that speak of automated access or reuse. I placed each result.

| What the site's own pages say | Governments | Standing |
|---|---:|---|
| No terms, disclaimer or privacy page found | 45 | Read |
| Terms-like pages that say nothing on automated access or reuse | 7 | Read |
| Terms of service that bar robots | 8 | **Closed** |
| Terms that limit reuse of the site's content | 4 | **Held for the owner** |

- **The eight that bar robots** share one site builder's terms page. It says the license to use the site does not include data mining or robots, and bars downloading without written consent. They are Frankston, Point Venture, Berryville, Hubbard, Morgan, Brownsboro, Como and Payne Springs. All eight have a robots file that allows the collector. The terms decide.
- **The four held:** Austin, Archer City, Live Oak and Keene. None names automated access. See "For the owner" below.
- Three of the 45 carry a copyright line that reserves all rights and nothing else.

**A check on the readers.** I searched the 53 agenda pages the collector later fetched for any link whose words look like terms or policy and that a reader had not listed. One real page turned up, on Cumby's site. I read it. It is a notice that the site is being updated and says nothing on automated access.

**A live look: one identified request to each of the 55 agenda pages** of the 52 governments that passed both readings.

- 53 pages answered.
- **Two answered 403: New Fairview and Taylor Lake Village.** Their robots files allow the page. A refusal is final. Both are marked `refused` in `config/tx_agenda_site_terms.csv` and are not asked again.

**After the first run closed six more, 44 governments and 45 pages are read.** Houston and Austin County are among them. Austin County is the only commissioners court.

| Of the 76 governments | |
|---|---:|
| Read | 44 |
| Closed by a robots file, their own or their file host's | 18 |
| Closed by their own terms | 8 |
| Held for the owner | 4 |
| Refused the request | 2 |

## The county association sites

The owner said on November 22, 2026 to start on these. Five commissioners courts in the test counties post their agendas on sites the Texas Association of Counties provides: Archer, Carson, Falls, Freestone and Hill. The sites run on software by a vendor named ezTask. They are the counties' own sites, so this collector reads them.

**What was read, on November 22, 2026**

| What | Finding |
|---|---|
| The robots file of each of the five sites | None. Each answers 404 |
| The robots file of the association's host for files and calendar feeds, `newtools.cira.state.tx.us` | None |
| The home page and agenda page of each site | No terms, disclaimer or privacy page is linked. Each carries a copyright line and a credit to the association. Falls County's line reserves all rights |
| Falls County's accessibility page and site map | No terms |
| The association's terms for county.org, dated March 30, 2011 | They speak of "the county.org site and various related services". Nothing on robots or automated access. They bar copying for commercial purposes and republishing content without the association's leave |
| The association's disclaimer | It grants leave to copy and distribute its information for noncommercial use |
| The vendor's site | No robots file. A privacy policy for its own website only. No terms of use are linked |

**Nothing read stands against a collector.** All five are marked `no_terms_found` in `config/tx_agenda_site_terms.csv` and the platform is marked `cleared` in `config/tx_agenda_platforms.csv`.

**How each county posts its agendas**

| County | Where the agendas are | How the collector reads it |
|---|---|---|
| Archer | A list of files by year on its Public Notices page | The page |
| Falls | A list of dated links on its Agendas and Minutes page | The page |
| Carson, Freestone, Hill | Attached to the meeting entries of a calendar that a script draws | The calendar's feed |

**The calendar feed.** The calendar offers its visitors an RSS feed, on the association's host. The feed lists the meetings to come, each with its start time and whatever the county attached. The page gives the feed's address. The collector reads it with one more request and takes a file whose words or name say it is an agenda. The meeting's day is its start time, turned from Greenwich time into Texas time.

- **The feed lists only meetings to come.** An agenda attached after its meeting started is never seen. A daily run sees each agenda while its meeting is still ahead.
- The page's own script calls are not copied. The feed is what the site publishes for programs.
- A feed that stops being a feed stops the run for a person to look.

**The independent checks.** A research pass cannot run a calendar's script, and it saw no list on Falls County's page. I opened each page in a real browser on November 22, 2026 and recorded what was there in `config/tx_agenda_checks.csv`:

- Falls: a list of 26 dated agendas for 2026, the newest for November 23.
- Carson: the calendar entry for November 23 opens one agenda file.
- Freestone: the entry for November 18 opens one agenda file.
- Hill: the entry for November 24 opens one agenda file.

Two inventory rows were corrected. Hill County's row had recorded a court rules file as its agenda. Carson County's row said the current agenda was one file linked from the page.

**A run of the collector on the five sites,** November 22, 2026, two files a page, nothing written to a database:

- **14 requests, none refused:** five pages, three feeds and six agenda files.
- **Six agenda files of four counties stored.** Freestone's feed was empty: its next meeting was not yet entered. The run log names its page.
- **Four of the six are scans.** Three were read by OCR in the run, at scores of 92.5 to 94.8. The fourth is the fault below.
- **One signal.** Hill County's file for November 24, 2026 is 108 pages, the agenda with its briefs. It uses the words "data center" on two pages. I read both. One is a session title on a form for training credit. The other is a definition in a software license. Neither is about a development in the county. A reviewer would see that.
- **A fault found and fixed.** One Falls County scan gave the text reader no pages at all, so it was never sent to OCR and was counted as unread. A PDF is now counted by the page drawer when the text reader finds no pages. That file then read at a score of 93.4.
- Every file came with a way to ask later whether it changed. The pages and feeds did not.

**Not verified**

- **Whether the association's terms reach the county sites.** None of the five sites links them, and they name county.org. I could not settle it from the pages.
- **Freestone's feed with an agenda in it.** It was empty on the day. Its calendar attached an agenda to a past meeting, which I saw in the browser.
- A feed entry that holds two meetings' agendas, or an agenda whose link does not say "agenda". Such a link is left.
- A second day's run, and a run from GitHub's servers.

## Milam County, added on November 22, 2026

The inventory had the Milam County Commissioners Court on BoardBook. BoardBook's terms bar copying by an automatic process, so that page is closed. See [tx_agenda_platform_terms.md](tx_agenda_platform_terms.md).

**The county also lists its agendas on its own site,** at `milamcounty.net/how_do_i/view/agendas_minutes.php`. I opened the page in a browser. It lists the court's meetings by year from 2019, a date to a row, with links Agenda, Packet and Minutes to files on the county's site. 321 Agenda links in all, the newest for a meeting on December 14, 2026.

| What | Finding |
|---|---|
| Robots file | The address leads to the site builder's host, which answers 404. No rules |
| Terms | No terms, disclaimer or privacy page is linked from the home page or the agenda page |
| Site builder | Revize. Its terms cover its own website only |
| Link finder | 318 links read from the saved page, every one dated. The newest dates match what the browser showed |

**First run, two files, no database.** Both files are scans of notices for the court's meeting of December 14, 2026. Character recognition read them at 85 and 88 percent confidence. **Both gave a signal on the words "reinvestment zone".** The notices are for a hearing on a tax abatement in a reinvestment zone named for a solar project. Neither names a data center.

Not verified: whether the file addresses, which end in a time stamp, stay the same from day to day. If they change, a file would be fetched again under a new address.

## Two cities on HeyGov, added on November 22, 2026

Sandy Oaks and Shallowater list their agendas on their own pages. The files are kept by HeyGov, on `files.heygov.com`, each city's in a folder named for its site. The owner said on November 22, 2026 to go ahead with HeyGov. The service's own rules are in [tx_agenda_platform_terms.md](tx_agenda_platform_terms.md).

| What | Sandy Oaks | Shallowater |
|---|---|---|
| Robots file | allows every path | allows every path |
| Its own pages | a privacy policy and an accessibility statement. Nothing on automated access or reuse | the same |
| The page as served | 1.4 MB, the whole list from 2019 on | 0.3 MB, the whole list |
| Link finder | 360 agenda links, every one dated | 88 agenda links, every one dated |
| Newest agenda | November 19, 2026 | November 16, 2026 |

- **Two more cities are on HeyGov and are not read:** Highland Haven and Sanctuary. Their pages draw their lists by script from HeyGov's API, whose robots file bars every agent.
- **Each meeting is a card that carries its own day.** The collector now reads that day ahead of the file's name. On these two pages the card and the file's name agree for 444 of 448 links. The four that differ are from 2020 to early 2026, and each differs by a year or by a day of the month. I did not open those four files to see which is right.
- **A HeyGov file is fetched only from the city's own folder.** A link into another city's folder is listed in the run log and not followed.
- The notice that a meeting was canceled is left, as on every page. So are minutes and videos.

**First run, two files a page, no database.** Both pages answered and three files were stored, two for Sandy Oaks and one for Shallowater. Shallowater's is a scan, read by character recognition at 94 percent confidence. **None of the three gave a signal.** They are a special meeting and public hearing on November 19, a canvass of election results on November 17 and a regular council meeting on November 16.

Not verified: a second day's run, and whether HeyGov's file addresses stay the same when a clerk replaces a file.

## The other 38, checked on November 22, 2026

The owner said on November 22, 2026 to check them. For each: the robots file, then the agenda page opened in a real browser, then the site's terms for the ones a collector could read.

**All 38 robots files allow the collector.** 28 allow the page, eight sites have no robots file and two answer the robots address with a web page, which bars nothing.

**What the browser showed**

| Standing | Governments | Which |
|---|---:|---|
| Agenda files linked on the government's own page | 15 | below |
| Agendas listed, in a form the collector does not read | 9 | Alvord, Marlin, Tye, Enchanted Oaks, Itasca, Maypearl, Pecan Hill, Seven Points, Whitney |
| The site is built and hosted by CivicPlus | 3 | Creedmoor, Grapevine, The Hills |
| The agendas are on another service | 5 | Cibolo, New Deal, Slaton, Reno, Runaway Bay |
| Nothing current, or nothing shown | 6 | Aquilla, Lake Bridgeport, Lawn, Penelope, Valley Mills, Hedwig Village |

- **The nine the collector does not read.** Five list meetings by script, with a View Agenda button and no file address. Alvord and Marlin keep each agenda on a page of its own and the file on their site builder's storage at another host. Tye's one file is on such storage too. Enchanted Oaks links its agenda from its home page to its site builder's file host. Their terms were not read, so they stay closed.
- **The five on another service.** Cibolo embeds a meeting platform. New Deal and Slaton post on a code publisher's document service. Reno and Runaway Bay link a folder on a file-sharing service. Their inventory rows now say `other`.
- **The six.** Aquilla's newest agenda is from 2020, Lake Bridgeport's from 2022 and Penelope's from 2023. Lawn shows one file with no year. Valley Mills' pages are empty. Hedwig Village keeps agendas in nested folders drawn by script, which I did not open to the end.

**The 15 with files on their own page.** One identified request to each home page and agenda page, then to each terms page.

| Government | Finding | Standing |
|---|---|---|
| Alma | The same site builder's terms as the eight closed before: no data mining or robots | **Closed** |
| Abernathy | Its own terms of service bar any robot or spider, for any purpose | **Closed** |
| Idalou | The site answered the collector with a firewall's script challenge in place of the page | **Closed.** Not worked around |
| Richland Springs | The first run found its files are served from its site builder's host, whose robots file bars them | **Closed** |
| DeCordova, Industry, San Saba, Millsap | Terms or privacy pages that say nothing on automated access or reuse. DeCordova's and Millsap's are empty | Read |
| Annetta North, Meadowlakes, Milano, Rosebud, Tolar, Wallis, Webberville | No terms, disclaimer or privacy page | Read |

**11 more governments are read.**

**Four that were read are closed again.** Buffalo Gap, Clyde, Malakoff and Mustang Ridge carry the credit "Government Websites by CivicPlus". CivicPlus' terms cover any user of a CivicPlus site and bar automated systems. The readers of November 21 looked for terms pages and did not see the credit. I found it on November 22 in the pages the first run saved. The collector read those four sites on November 21 and 22. Nothing from them is in a database. All seven CivicPlus-built sites are marked `vendor_site` and wait with the CivicPlus platforms.

**Other site builders.** Revize builds Meadowlakes' and Richland Springs' sites and three read before. Its terms of use speak of its own website only. Read November 22, 2026.

**Four inventory rows named the wrong page.** Annetta North, Industry, San Saba and Enchanted Oaks now name the page that lists the agendas. Industry's old address answers 404. New Deal's row now names the document service. Slaton's body is its City Commission.

**Five agenda files were read for what their page does not say.** Annetta North, DeCordova, Tolar and Millsap list agendas by month with no day. Wallis' page does not name the body. Each file's heading gave the meeting day and the council.

**The link finder was run on the 12 saved pages. It had four faults.**

- **A wrong date.** `june2026agenda.pdf` was read as June 20, 2026. Four digits that make a year are now a year. Houston's page had 16 such files, named like `Oct2026.pdf`. None was in the date window, so none was fetched under a wrong date.
- **A treasurer's report and a financial statement were taken as agendas** on a page that lists them beside the agendas. Both are now left.
- **Two ways of writing a date were not read:** `Nov16_2026`, and a list typed as one paragraph with each meeting's date before its link.
- **A page with one dated link read none of its month-only links.** A link that names a month and no day is now kept with its month. A run takes last month's, this month's and the coming months', two at most.
- The finder was run before and after on all 63 pages saved by the earlier runs. Nothing else changed.

**A run of the collector on the 12 then cleared,** November 22, 2026, two files a page, nothing written to a database:

- 12 pages answered. **Ten agenda files of seven governments stored.**
- Richland Springs' file was refused by its file host's robots file. It is closed.
- Industry, Meadowlakes and Tolar had no agenda inside the date window. Their newest are from September.
- **Millsap's page gives the finder nothing.** Its files sit under a heading "Agenda" and their own words name only a month.
- One file is a scan and was read by OCR.
- **One signal. Webberville's agenda for November 11, 2026 uses the words "data center" twice.** One item is to discuss the possibility of a proposed data center in Webberville. Another is on an ordinance to bar data centers from locating there. Both are on page 1. I read both.

**Not verified**

- **Whether CivicPlus' terms bind a visitor to a site CivicPlus builds.** The four were closed on the reading already used for its platforms.
- The terms of the nine governments whose agendas the collector does not read.
- Whether Meadowlakes' files are sent on to its site builder's host. It had no agenda inside the date window.
- The counts in the check rows of script-drawn lists. They are the rows I read, not the whole list.
- Grapevine's and Hedwig Village's planning bodies. Their lists were not opened.
- Wallis' corporation page. Its last file's year was not read.

## What the collector does

For each page, one run makes:

1. **One request for the page.**
2. **One request for each agenda file** dated from 21 days back to 60 days ahead that is not stored yet. Four files a page at most.
3. **One request for each agenda that names a month and no day,** for last month, this month and the months ahead. Two a page at most.

- Requests go through the shared fetcher: the robots file of every host is read first, one request every 5 seconds to a host, longer if the robots file asks, with the radar's user agent and contact address.
- **A refusal closes that site for the rest of the run and the other sites go on.** The run log names the site. Nothing is retried. A person then marks the site `refused`.
- **A file is fetched only from the government's own site** or from its site builder's file host. A link to any other host is listed in the run log and not followed. On HeyGov's file host only the folder named for the government's own site counts.
- A stored file is asked for again only if the site gave a way to ask whether it changed.
- PDF and Word .docx files are read. An old-format .doc file is not.
- A page that lists no agenda does not stop the run. The run log names it.

**What is stored.** For a page, the list of agenda links found on it, not the page. For an agenda, the file itself, with the government, its counties, the page it was linked from, the date and where the date was read.

**The source is marked `personal_rows`.** An agenda names staff, appointees and applicants. Its stored text is open to administrators and not to reviewers, and none of it is sent to the model.

## How a link is judged

A link is taken when it leads to a file and says it is an agenda: in its own words, in its file's name, in the heading of its table column, or in its row when the link itself says nothing. On a page whose title or address speaks of agendas or meetings, a file with a date is taken too.

Left alone: minutes, recordings, handouts, presentations, action summaries, quorum notices, cancellations, treasurer's reports and financial statements. A packet is left when the page has the plain agenda for the same day.

**How a date is read.** In this order:

1. The link's own words, such as "November 17, 2026".
2. The day of the meeting card the link sits in, on the pages Town Web builds. Each card gives its meeting's day in a form made for programs.
3. The file's name, when a date is written out in it.
4. The row, only when the row holds one date and no more than four files.
5. A row that gives a month and a day, with the year of the folder the file was uploaded to.
6. The words on the link's own line before it, when a list is typed as one paragraph: "September 9, 2026 - Agenda".
7. Digits run together in the file's name, such as `11172026`, only when they can be read one way.

- A scanner's file name is never read. It gives the minute the page was scanned.
- **A date that is not sure is no date.** `1122026` could be January 12 or November 2.
- **A month and a year are not a day.** `june2026agenda.pdf` and "November 2026 Agenda" give a month. The file is kept with its month and no date. A month alone never makes a file an agenda: a report for October is named for its month too.
- Where the date came from is kept with the file.

## What becomes a signal

`agenda_file` in `pipeline/signals.py` reads the file's text. A file that uses a term in `config/keywords.yaml` becomes one `agenda_keyword` signal, the lowest weight in the scoring.

- **The summary names the government, the date and the words that matched. Nothing else.** It carries no file name and no link text. One real file is named for a person.
- The pages the terms are on and the words around each match are kept for the reviewer, who opens the government's agenda page.
- A file whose head says "minutes" and not "agenda" is not called an agenda.
- **A code name such as "Project Falcon" counts only where the agenda speaks of economic development negotiations.** A long file calls every road job "Project" something.
- **A scan is read by character recognition** with Tesseract, on our own machine. A signal made from a scan says so in its summary, and the engine and its score are kept with it. See [tesseract.md](../services/tesseract.md).
- A scan that still gives no text is counted as unread, not as clean. Nobody has read it.
- A file the page did not date takes the date written at its own head. With none there, it is held as undated.

## Verified live

On November 21, 2026:

- **One identified request to each of 55 agenda pages.** 53 answered and two refused, as above.
- **The link finder against the independent second read,** on those 53 pages:
  - 44 pages give agenda file links. Nine give none.
  - On 38 of the 44, the newest agenda's date is the one the second read recorded.
  - On five the finder found a newer agenda than the second read listed: Bruceville-Eddy, Alamo Heights, Buffalo Gap, Cameron and Houston.
  - On one, Terrell Hills, no link could be dated. Its files are named for a month and a year.
- **A run of the collector itself** on the 50 governments then cleared, capped at two files a page. Nothing was written to a database.
  - 52 of 53 pages answered. Annetta South's page failed once. It had answered earlier the same day.
  - **Six sites' files were refused** by their file host's robots file. Those six are now closed.
  - **43 agenda files of 29 governments were stored:** 41 PDF and 2 Word, 365 pages in all.
- **28 of the 43 files are scans with no text.** A second PDF reader found none either. Sixteen governments gave only scans, Austin County among them. The first pass read none of those 28.
- **OCR was then built and read all 28.** It added two signals: Merkel's council agenda for November 17, 2026 has two items on a tax increment reinvestment zone, and a 125-page packet uses the words "development agreement".
- **The signal step on the 15 files with text: 3 signals.**
  - Red Lick's council agenda for November 3, 2026 uses the words "data center".
  - A Cameron agenda for November 17, 2026 has a "reinvestment zone" study and a code name under its closed session on economic development negotiations.
  - A Piney Point Village file uses "light industrial" in a drainage table on page 91. It is not about a development. A reviewer would see that.
- **A fault found and fixed.** The first pass read "Project Documentation" and "Project Per the schedule" in that 91-page file as code names. A code name now counts in a file only where the agenda speaks of economic development negotiations, and never across a line break.

## What was not verified

- **Whether a government's site rules bind a visitor who never sees them,** and whether a site with no terms page has terms elsewhere. 45 sites show none.
- **The nine pages that list no file links.** Their agendas are in the page itself, behind a script, or on one page per meeting: San Felipe, Caney City, Hooks, Cumby, China Grove, Teague, Jacinto City, Kirby and Lakeside City. The collector reads none of them yet.
- **How well OCR reads real scans, as a number.** Two pages were checked by eye. Tables come out jumbled. See [tesseract.md](../services/tesseract.md).
- Grey Forest's file host. Its site is built like the six the first run closed, and it had no recent agenda to ask for. A run will stop at its robots file if that bars the files.
- Old-format .doc files, which Red Lick posts.
- The terms of the county association and whether they reach the five county sites. See "The county association sites".
- Whether the meeting date read from a file's name is always the meeting's. A name can carry the day the file was posted.
- The site builder's terms for the file host `img1.wsimg.com`. Its robots file is read on every run.
- A statement on Shoreacres' home page that the city was consolidated into La Porte. I did not check it. Its newest agenda is from May 2026.
- A full run with no cap, a second day's run, and a run from GitHub's servers.
- The 12 own-site governments whose rows are still not confirmed. Four of them are closed for another reason. See "The other 38".

## For the owner

- **Four governments wait on your word.** Their terms limit reuse and say nothing on automated access:
  - **Austin.** Its legal notice grants personal use, asks written permission to use copyrighted material and bars collecting files to replicate the site.
  - **Archer City.** Its home page says content may not be reproduced without the city secretary's written consent.
  - **Live Oak.** Its terms say content may not be reproduced without permission.
  - **Keene.** Its terms allow downloading for personal, educational or non-commercial use and ask written permission for any other use.
- **Eight governments' own terms bar robots.** Reading their agendas by program would take each city's written consent.
- **Two sites refused the request.** New Fairview and Taylor Lake Village stay closed unless they say otherwise.
- **Most small governments post scans.** They are now read by OCR on our own machine. A signal from a scan is marked as a machine's reading. Austin County's commissioners court is among the scans.
- Nothing runs on a schedule. The workflow is started by hand.
