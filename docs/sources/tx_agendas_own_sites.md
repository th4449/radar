# Texas agendas on governments' own sites

- Source id: `tx_agendas_own_sites`
- What it is: the agenda page of each government that posts its agendas as files on its own website, and the agenda files that page links to
- Checked: November 21, 2026
- Result: **allowed for 44 of 76 governments, one site at a time.** 32 are closed or held.
- Collector: `collectors/tx/agenda_pages.py`
- Fixtures: `tests/fixtures/tx_agendas_own_sites/`, four real pages cut down to their agenda lists
- Workflow: `.github/workflows/collect-tx-agendas-own-sites.yml`, started by hand only

The owner said on November 21, 2026 to build next for the governments that post agenda files on their own sites. There is no vendor here and no shared rule. Each site has its own robots file and its own terms, so each was read.

## Which governments were looked at

The agenda inventory lists 114 governments with files on their own sites. **76 of them have a row that an independent check confirmed.** Only those were read. The other 38 wait for a hand read of their rows.

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

## What the collector does

For each page, one run makes:

1. **One request for the page.**
2. **One request for each agenda file** dated from 21 days back to 60 days ahead that is not stored yet. Four files a page at most.

- Requests go through the shared fetcher: the robots file of every host is read first, one request every 5 seconds to a host, longer if the robots file asks, with the radar's user agent and contact address.
- **A refusal closes that site for the rest of the run and the other sites go on.** The run log names the site. Nothing is retried. A person then marks the site `refused`.
- **A file is fetched only from the government's own site** or from its site builder's file host. A link to any other host is listed in the run log and not followed.
- A stored file is asked for again only if the site gave a way to ask whether it changed.
- PDF and Word .docx files are read. An old-format .doc file is not.
- A page that lists no agenda does not stop the run. The run log names it.

**What is stored.** For a page, the list of agenda links found on it, not the page. For an agenda, the file itself, with the government, its counties, the page it was linked from, the date and where the date was read.

**The source is marked `personal_rows`.** An agenda names staff, appointees and applicants. Its stored text is open to administrators and not to reviewers, and none of it is sent to the model.

## How a link is judged

A link is taken when it leads to a file and says it is an agenda: in its own words, in its file's name, in the heading of its table column, or in its row when the link itself says nothing. On a page whose title or address speaks of agendas or meetings, a file with a date is taken too.

Left alone: minutes, recordings, handouts, presentations, action summaries, quorum notices and cancellations. A packet is left when the page has the plain agenda for the same day.

**How a date is read.** In this order:

1. The link's own words, such as "November 17, 2026".
2. The file's name, when a date is written out in it.
3. The row, only when the row holds one date and no more than four files.
4. A row that gives a month and a day, with the year of the folder the file was uploaded to.
5. Digits run together in the file's name, such as `11172026`, only when they can be read one way.

- A scanner's file name is never read. It gives the minute the page was scanned.
- **A date that is not sure is no date.** `1122026` could be January 12 or November 2.
- Where the date came from is kept with the file.

## What becomes a signal

`agenda_file` in `pipeline/signals.py` reads the file's text. A file that uses a term in `config/keywords.yaml` becomes one `agenda_keyword` signal, the lowest weight in the scoring.

- **The summary names the government, the date and the words that matched. Nothing else.** It carries no file name and no link text. One real file is named for a person.
- The pages the terms are on and the words around each match are kept for the reviewer, who opens the government's agenda page.
- A file whose head says "minutes" and not "agenda" is not called an agenda.
- **A code name such as "Project Falcon" counts only where the agenda speaks of economic development negotiations.** A long file calls every road job "Project" something.
- **A scan with no text is counted as unread,** not as clean. Nobody has read it.
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
- **28 of the 43 files are scans with no text.** A second PDF reader found none either. Sixteen governments gave only scans, Austin County among them. The radar read none of those 28.
- **The signal step on the 15 files with text: 3 signals.**
  - Red Lick's council agenda for November 3, 2026 uses the words "data center".
  - A Cameron agenda for November 17, 2026 has a "reinvestment zone" study and a code name under its closed session on economic development negotiations.
  - A Piney Point Village file uses "light industrial" in a drainage table on page 91. It is not about a development. A reviewer would see that.
- **A fault found and fixed.** The first pass read "Project Documentation" and "Project Per the schedule" in that 91-page file as code names. A code name now counts in a file only where the agenda speaks of economic development negotiations, and never across a line break.

## What was not verified

- **Whether a government's site rules bind a visitor who never sees them,** and whether a site with no terms page has terms elsewhere. 45 sites show none.
- **The nine pages that list no file links.** Their agendas are in the page itself, behind a script, or on one page per meeting: San Felipe, Caney City, Hooks, Cumby, China Grove, Teague, Jacinto City, Kirby and Lakeside City. The collector reads none of them yet.
- **Scanned agendas: 28 of 43 files in the first run.** The pipeline has no OCR. A scan gives no text and no signal, and the run log counts it as unread.
- Grey Forest's file host. Its site is built like the six the first run closed, and it had no recent agenda to ask for. A run will stop at its robots file if that bars the files.
- Old-format .doc files, which Red Lick posts.
- Whether the meeting date read from a file's name is always the meeting's. A name can carry the day the file was posted.
- The site builder's terms for the file host `img1.wsimg.com`. Its robots file is read on every run.
- A statement on Shoreacres' home page that the city was consolidated into La Porte. I did not check it. Its newest agenda is from May 2026.
- A full run with no cap, a second day's run, and a run from GitHub's servers.
- The 38 own-site governments whose inventory rows are not confirmed.

## For the owner

- **Four governments wait on your word.** Their terms limit reuse and say nothing on automated access:
  - **Austin.** Its legal notice grants personal use, asks written permission to use copyrighted material and bars collecting files to replicate the site.
  - **Archer City.** Its home page says content may not be reproduced without the city secretary's written consent.
  - **Live Oak.** Its terms say content may not be reproduced without permission.
  - **Keene.** Its terms allow downloading for personal, educational or non-commercial use and ask written permission for any other use.
- **Eight governments' own terms bar robots.** Reading their agendas by program would take each city's written consent.
- **Two sites refused the request.** New Fairview and Taylor Lake Village stay closed unless they say otherwise.
- **Most small governments post scans.** Reading them takes OCR, which the plan does not have. Free tools exist and run on our own machine. I have not built it. Austin County's commissioners court is among the scans.
- Nothing runs on a schedule. The workflow is started by hand.
