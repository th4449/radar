# Michigan agendas on governments' own sites

- Source id: `mi_agendas_own_sites`
- Interface: each government's own website. The list is `config/mi_agenda_inventory.csv`
- Checked: November 23, 2026
- Result: **77 of 220 governments have a row a collector could take. No job reads any of them.** The source is still marked `manual`, and only the owner changes that.
- Collector: none yet
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

**Revize.** About 50 of the sites are hosted by Revize. A Revize site's robots request redirects to a Revize file host. Most answer 404 there: no file. The 13 Revize file hosts themselves bar every program from everything but document files such as PDFs. So a collector may fetch an agenda PDF kept on a Revize file host and may not read a page there. Revize's own terms of use speak of its own website only, read November 22, 2026.

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

## Not verified

- **Most terms were read through a page-reading tool that gives a summary.** It cut long sentences short. The nine pages that mattered were read again in full by the radar's reader. The other 81 hosts rest on the summary's word that no terms page exists or that a page says nothing.
- **The terms of site builders other than CivicPlus, Revize and Granicus were not read.** Fifteen other builders are credited across the sites. A builder's terms could cover the sites it hosts, as CivicPlus' do. Each row's note names its site's credit.
- **Which host an agenda file is on,** where a page gives a relative link. A PDF on a Revize file host is open to the collector. The fetcher checks the robots file of every host before every request, so a file on a closed host is not fetched.
- **No page was opened in a real browser.** A list a script draws shows nothing to a plain read: Belleville, the city of Plymouth and two development authorities.
- That any of this is still so on the day a collector first runs.

## Before a collector is written

1. The owner decides the eight held sites.
2. The owner says whether the collector built for Texas' own sites may read Michigan's. The platforms file clears "own_site_files" on the owner's word of November 21, 2026, which was given for Texas.
3. A collector class for Michigan, with fixtures saved from real pages and tests that run on the fixtures.
4. The source's method changes from `manual` only on the owner's word.
