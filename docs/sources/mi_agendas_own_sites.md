# Michigan agendas on governments' own sites

- Source id: `mi_agendas_own_sites`
- Interface: each government's own website. The list is `config/mi_agenda_inventory.csv`
- Checked: November 23, 2026
- Result: **53 of 220 governments have a row a collector could take. A collector is written. No job reads any of them.** It was 77 until the run by hand of November 23 met 24 sites whose files a robots rule bars. The owner said to leave those closed. The source is still marked `manual`, and only the owner changes that.
- Collector: `collectors/mi/agenda_pages.py`, which is Texas' `collectors/tx/agenda_pages.py` pointed at Michigan's inventory
- Tests: `tests/test_mi_agendas_own_sites.py`, on ten saved pages
- Counties: Allegan, Kalamazoo, Monroe, Oakland, Washtenaw and Wayne

## The four conditions

A row is a collector's only when all four hold. Each is a file a person can read.

| Condition | Where it is recorded | Who read it |
|---|---|---|
| The inventory names the page | `config/mi_agenda_inventory.csv` | Research passes, November 23 |
| An independent second read agrees | `config/mi_agenda_checks.csv` | Six passes not told what the inventory says, November 23 |
| The site's robots file lets the collector in | `docs/sources/mi_agenda_robots.csv` | The radar's own reader, one request a host, November 23 |
| The site's own terms say nothing against it | `config/mi_agenda_site_terms.csv` | Five passes, and nine pages read in full by the radar's reader, November 23 |

`pipeline/agenda_checks.py` applies them. The platforms file, `config/tx_agenda_platforms.csv`, is shared with Texas.

## Robots files

One identified request for each host, redirects followed as RFC 9309 section 2.3.1.2 says. No retry.

- **122 site hosts were asked.** 112 let the collector in: a file that allows it, or no file.
- **8 Revize-hosted sites bar every program** but five named search and social crawlers: Bedford Township, Grosse Ile Township, Huron Charter Township, Milford village, Richland village, Rochester Hills, South Haven and West Bloomfield Township. Three more were read as closed by research passes: Dexter, Saline and Lyon Township.
- **Detroit's site answered 403** to the robots request. **Dexter Township's dropped the connection.** Neither was asked again.
- Plainwell answers the robots request with its page-not-found page and a 200. That is no robots file.
- Six hosts ask for 3 to 20 seconds between requests. The fetcher keeps a site's own delay.

**Revize.** About 50 of the sites are hosted by Revize. A Revize site's robots request redirects to a Revize file host. Most answer 404 there: no file. The 13 Revize file hosts themselves bar every program from everything but document files: the rule allows an address that ends in `.pdf`. **The sites write each file's address with `?t=` and a number after it, and the rule bars that address.** So the collector reads a Revize site's list and is refused its files. The run by hand of November 23 showed it on 24 sites. An earlier version of this note said the files were open. That was wrong. Revize's own terms of use speak of its own website only, read November 22, 2026.

## Terms of use

Read for the 90 hosts that carry a confirmed row. Every home page loaded and none refused.

| What the site says | Hosts | A collector |
|---|---|---|
| No terms, disclaimer or privacy page | 63 | may read |
| A privacy or policy page that says nothing on automated access or reuse | 16 | may read |
| Terms bar obtaining material "through any means not intentionally made available" | 3 | **held for the owner** |
| Terms allow non-commercial use and ask consent for other use | 3 | **held for the owner** |
| Terms bar use or copying without written consent | 2 | **held for the owner** |
| Built and hosted by CivicPlus | 2 | held with the CivicPlus platforms |
| The home page gave the reader nothing | 1 | not read |

**No site's terms name a robot, a crawler or a scraper.**

The eight held for the owner:

- **Otsego Township, Berlin Charter Township and Plymouth Charter Township** use the same sentence: "You may not obtain or attempt to obtain any materials or information through any means not intentionally made available or provided for through" the site. An agenda linked on a public page is made available by the site. Whether a program that follows that link is such a means is the owner's to decide.
- **Ross Township** has that sentence and adds: "You will use protected content solely for your personal use, and will make no other use of the content without the express written permission of Ross Township and the copyright owner."
- **Rockwood:** "No such information shall be used other than to view the same without the written permission of the City of Rockwood."
- **Keego Harbor:** content may be viewed, downloaded and printed "for personal, educational, or non-commercial use. Any other use (including reproduction, modification, or distribution) requires prior written permission".
- **Southgate:** content "may generally be viewed, downloaded, or printed for personal, educational, informational, or other lawful non-commercial purposes."
- **Dearborn:** "Commercial use of material contained at this site is prohibited without the express written permission of the City of Dearborn." The page also bars use of the site "for other than its intended purposes".

**Rochester and Dearborn Heights** run on CivicPlus. CivicPlus' terms cover every site it hosts and bar automated collection. They wait with its platforms on the answer to the letter. See [tx_agenda_platform_terms.md](tx_agenda_platform_terms.md).

**Ann Arbor's** policies page says information on its site "is considered public information and may be distributed or copied", but for logos and for material marked with a copyright.

## The collector

The owner said on November 23, 2026 that the clearing of own sites given for Texas holds for Michigan. The same day ten cleared pages were fetched once each by the radar's fetcher, which read each host's robots file first. All ten loaded. Each is a governing body's page, and they cover the six counties: Allegan, Auburn Hills, Chelsea, Comstock Township, Erie Township, Luna Pier, Novi, Oshtemo Township, River Rouge and Superior Township. Each was cut down to its agenda list and saved as a fixture.

- **On nine of the ten the collector finds the agendas.** Its newest agenda matches the second read's on all nine. Two of the ten, Chelsea and Allegan, are Revize sites. Their lists are read. On the run below Chelsea's files were refused and Allegan's failed.
- **One fault was found and fixed.** Oshtemo Township lists a report of receipts and disbursements between its packets, in a file named for the meeting's day. Read as an agenda, the report took the place of that day's packet. Such a report is now left, for both states.
- **Novi's agendas are not read.** Its list links each meeting to a page of its own, not to a file. The collector reads files only. The run log names such a page.

**Governments the collector would not read as it stands,** by the second read's notes. Only Novi's page was fetched.

| Government | Why |
|---|---|
| Novi | Each agenda link leads to a page for the meeting |
| Otsego city | Each agenda link leads to a document page |
| Lyndon Township | Each agenda is a post on the site |
| Heath Township | The agenda is a post linked from the home page |
| Plainwell | Agenda files have addresses that end in `.aspx` |

**Seven governments' pages carry the year in their address:** Novi, Commerce Township, Farmington, Farmington Hills, Highland Park, Holly and Plainwell, 21 pages. Each needs a new inventory row in January.

## The run by hand of November 23, 2026

On the owner's word the collector ran once, by hand, with nothing stored: each cleared page and at most one agenda file from each. The run log was kept in memory and the files in a scratch folder outside the repository.

| | |
|---|---|
| Pages asked for | 145 |
| Pages read | 142 |
| Pages whose newest agenda matches the second read's | 111 |
| Pages where it differs | 22 |
| Pages that gave no agenda link | 9 |
| Sites whose files a robots rule refused | 25 |
| Agenda files fetched | 56, of 36 governments |
| Files that are text, and scans read by character recognition | 54 and 2 |
| Draft signals in those 56 files | 23 |

**Refused, 25 sites.** 24 are Revize sites whose file addresses the file host's robots rule bars, as above. The 25th is Plainwell: the fetcher's robots request did not come back open, and its three pages were not read. The fetcher left each site alone after the refusal.

**Failed, 4 files.** Three of Allegan's and one of Leighton Township's, whose page writes the link without `https://`. The run log does not keep the reason for a failure.

**No agenda link, 9 pages:** Novi's council and economic development pages, Otsego's two, Heath Township, Lyndon Township, Holly, Dorr Township's development authority and Saugatuck's planning commission.

**Where the newest agenda differs, 22 pages.** Three kinds:

- **The reader misread a date in a file's name.** Six ways, each now fixed and tested on the names the run reported: the day run onto the year (`August-102026`), the month run onto the word before it (`PacketAPR72026`), a number before the date (`1_3-27-2024`), the day first (`10Nov2026`), a run of digits in a folder for another year (`/2012/Agendas/a120626s.pdf`, read as December 2026) and a year mistyped in a name (`1.27.2027` in the upload folder of January 2026). A notice that there is no meeting is no longer taken as an agenda.
- **The page has more on it than the second read counted,** or the site slipped. A later agenda of another board on a shared page, a notice of a special meeting, a link whose words say 2026 over a file named 2025.
- **The collector does not take the newest file.** Packets that nothing calls an agenda, on a page whose title does not speak of meetings: Bridgewater Township, Auburn Hills' planning commission, Schoolcraft Township's November files, Walled Lake. A name that gives a month and a day and no year: Whiteford Township. These are not fixed.

**The draft signals were stored nowhere.** 15 of the 23 came from the words "data center", in the agendas of 14 governments: mostly a moratorium or a zoning amendment under discussion, one a line in a list of bills. The other 8 came from "special land use" or "development agreement" alone, for a drive-through, a campground and the like. "Special land use" is Michigan's ordinary term for a use that needs a hearing. The keyword rules were written for Texas and are untried here. One township's file came out of extraction with its letters spaced apart.

**After the run: 53 governments.** The 24 Revize sites are closed, on the owner's word. What a collector could take is now 112 rows of 53 governments, 48 of them with their governing body: Allegan 12, Oakland 10, Washtenaw 9, Kalamazoo 6, Monroe 6 and Wayne 5. That is 101 pages on own sites and Ann Arbor on Legistar.

The 24: Allen Park, Brownstown Township, Charleston Township, Chelsea, Clarkston, Flat Rock, Franklin, Freedom Township, Galesburg, Grosse Pointe, Grosse Pointe Shores, Huntington Woods, Milan, Orion Township, the village of Oxford, Pontiac, Riverview, South Lyon, South Rockwood, Springfield Township, Sumpter Township, Van Buren Township, Webster Township and Woodhaven.

Seven other sites Revize builds stay cleared. Four gave the run a file: Ecorse, Richland Township, York Township and Ypsilanti Township. Three were not settled by it: Allegan, whose files failed, and Birmingham and Sylvan Lake, which had no file in the run's window.

## Not verified

- **The pages were not read again after the fixes.** The fixes are tested on the file names and addresses the run reported, not on the pages.
- **Why Plainwell's robots request failed, and why three of Allegan's files failed.**
- **The files of the 24 Revize sites.** None was fetched.
- **Most terms were read through a page-reading tool that gives a summary.** It cut long sentences short. The nine pages that mattered were read again in full by the radar's reader. The other 81 hosts rest on the summary's word that no terms page exists or that a page says nothing.
- **The terms of site builders other than CivicPlus, Revize and Granicus were not read.** Fifteen other builders are credited across the sites. A builder's terms could cover the sites it hosts, as CivicPlus' do. Each row's note names its site's credit.
- **Which host an agenda file is on,** where a page gives a relative link. A PDF on a Revize file host is open to the collector. The fetcher checks the robots file of every host before every request, so a file on a closed host is not fetched.
- **No page was opened in a real browser.** A list a script draws shows nothing to a plain read: Belleville, the city of Plymouth and two development authorities.
- That any of this is still so on the day a collector first runs.

## Before a job reads it

1. The owner decides the eight held sites. Until then they stay held.
2. **Decided: the Revize files stay closed.** As the sites write them the robots rule bars them. The same file without the `?t=` mark is an address the rule allows. The owner said on November 23, 2026 to leave them closed. The 24 sites are marked `robots_bar` in `config/mi_agenda_site_terms.csv`, as Texas' two such sites are, so no run asks them for anything. A letter to Revize is not written.
3. The owner says to run it.
4. The source's method changes from `manual` to `http`, the collector goes on the list in `collectors/run.py` and a workflow file is added. A test holds all three together.
5. The owner decides what the trial of the keyword rules proposed. They were tried on the run's 56 files on November 24, 2026: `docs/progress.md` has the count. The direct term missed nothing, "special land use" alone gave only noise, and most mentions were a town writing its rules. The owner said that day to stop a signal on "special land use" alone, and it is done. A label for the reviewer, where "data center" sits beside "moratorium" or "ordinance" in the same item, was built the same day, and the owner approved its wording. One proposal is open: saying "packet" where the words are past the agenda's own pages.
