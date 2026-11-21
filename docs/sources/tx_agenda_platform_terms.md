# Texas agenda platforms: what their own rules say

- Milestone: M8
- Registry: `config/tx_agenda_platforms.csv`
- Read: November 21, 2026
- Result: **six platforms restrict a collector** by their vendor's terms or their robots file. **Legistar is cleared** and has a collector. The county association sites are a candidate.

The owner approved building the agenda collectors by platform. The first step for each is to read its terms and robots rules. This note is that reading. It changes the plan, because the largest vendor's terms stand against the radar's use.

## Where each platform stands

| Platform | Vendor | Governments | Robots file | Standing |
|---|---|---:|---|---|
| CivicPlus Agenda Center | CivicPlus | 51 | allows, 10 second delay | **Restricted by the vendor's terms** |
| CivicClerk | CivicPlus | 36 | allows | **Restricted by the vendor's terms** |
| Municode Meetings | CivicPlus | 13 | allows | **Restricted by the vendor's terms** |
| Swagit | Granicus | 7 | pages allowed, file host refuses | **Restricted** |
| CivicWeb | Diligent | 6 | bars every agent | **Restricted by robots** |
| Granicus | Granicus | 4 | bars all but three search engines | **Restricted by robots** |
| Legistar | Granicus | 14 | none | **Cleared.** 9 governments are read. See [tx_agendas_legistar.md](tx_agendas_legistar.md) |
| County association sites | Texas Association of Counties | 5 | none | Candidate |
| Files on the government's own site | each government | 114 | not read | Not read |
| Other outside platforms | various | 23 | not read | Not read |

**117 of the 136 governments in the three platform batches are on a restricted platform.** 100 of them are on a CivicPlus product.

## CivicPlus

**Read:** CivicPlus' Terms of Use, https://www.civicplus.help/legal-center/docs/civicplus-terms-of-use. The page gives a last revision of March 20, 2026. I read sections 1, 2, 3, 7 and 8 in full.

**Who it covers.** The terms address any user of a CivicPlus site or "Solution". Solutions are the products governments buy. CivicPlus' legal center lists Agenda and Meeting Management terms for CivicClerk and Municode Meetings, and CivicPlus announced that it acquired Municode. So the Agenda Center, CivicClerk and Municode Meetings are all under these terms.

**What section 7 bars:**

- An automated system that sends more requests than a person could in the same time with a browser, unless CivicPlus permits it.
- Reaching a site or product by any means other than the interface CivicPlus provides.

A collector at one request every 10 seconds stays under the first. The second is less clear.

**What section 8 bars.** It is headed as a ban on scraping for AI purposes, and its definitions reach much further than that heading.

- "Automated scraping" is any script or automated process that reads, copies or downloads material from a product.
- "AI training purposes" includes using any algorithmic or automated decision-making system.
- "Authority data" is anything a government provides through a product, public or not. An agenda is authority data.
- **It bars automated scraping of authority data for those purposes.**
- It bars using authority data for those purposes without CivicPlus' written consent, whatever the source.
- It bars collecting content in a manner inconsistent with ordinary human use.

**What section 8 allows:** search engines that follow the robots file, accessibility tools, and a feed or export that CivicPlus or the government has authorized, used for its intended purpose. It then says no exception permits use for AI training purposes without a signed writing from CivicPlus.

**What section 8 says about public records.** A right to obtain or use a public record comes from the law and from the government, not from CivicPlus.

**Why this stops the collector.** The radar reads records with keyword rules, scores them and may ask a language model about them. That is an algorithmic system. A collector would be an automated process downloading a government's agendas for use in it. My reading is that section 8 names exactly this. I am not a lawyer, and I cannot say whether these terms bind a person who visits a city's website and never sees them. The standing rule decides it: a source whose terms restrict automated access is not automated.

**Robots files.** All 38 Agenda Center sites whose rows are confirmed were checked, one request each, identified. Every one allows the agenda pages and files for the radar's agent and asks for a 10 second delay. Each disallows `/RSS.aspx`. A CivicClerk portal's file allows every path, bars a list of named AI crawlers and declares that content may not be used to train AI models. `meetings.municode.com` carries the same file.

**Each site's own terms.** Three research passes read the terms, copyright and privacy pages of the 38 sites. The results are in `config/tx_agenda_site_terms.csv`.

- **27 sites:** the government's own pages say nothing on automated access. Most hold one copyright line that reserves all rights.
- **3 sites link CivicPlus' terms from their home page:** Selma, DeSoto and Jersey Village. A visitor to those three is pointed at the vendor's terms.
- **4 sites** have no terms page that could be found, or pages that load empty.
- **4 sites did not load** for the reader: Decatur, Marble Falls, Mabank and Ellis County.
- One reader reported that two pages were fetched through its tool's alternate proxy after errors. I do not know whether those sites were refusing the tool. No collector decision rests on those two pages.

So the governments themselves mostly say nothing. The restriction is the vendor's.

## Granicus: Legistar, Swagit and Granicus pages

**Read:** Granicus' Terms of Use, https://granicus.com/trust-center/terms-of-use/, dated July 20, 2026, in full. It speaks of "this website", meaning granicus.com. It reserves copyright in the site's material and says nothing about automated access. It does not name Legistar, Swagit or customer sites.

- **Legistar: cleared on November 21, 2026,** on the owner's word to go on with the build. A customer's Legistar host has no robots file. Granicus publishes the Legistar Web API at https://webapi.legistar.com/ with a page of examples for getting started. That page says replies are limited to public items, asks callers to page and filter to reduce load, and says some customers require a token, which is each customer's policy. An interface published for programs is the right way in. Neither page states terms of use or a rate limit.
- **Granicus pages: restricted.** The robots file on a customer's Granicus host names three search engines and bars every other agent from every path.
- **Swagit: restricted.** A customer's Swagit pages have a default robots file that bars nothing. The agenda files sit on another host, which answers 403 for its robots file. The fetcher treats a robots file it cannot read as a refusal.

## CivicWeb

**Restricted.** The robots file on a customer's CivicWeb host bars every agent from every path. Diligent's terms were not read. The robots file settles it.

## County association sites

**Candidate.** The Texas Association of Counties hosts these sites. The one checked, Carson County, has no robots file. Its home page links no terms, privacy or policy page and carries a copyright line only. The association's own terms for these sites were not found.

## What is not verified

- **Whether CivicPlus' terms bind a visitor to a government's site.** That is a legal question.
- **Whether a person's hand reading of a CivicPlus-hosted agenda may then be scored by the radar.** Section 8 speaks of using authority data, not only of collecting it. This needs counsel before reviewers are set to work on those sites.
- Whether CivicPlus gives written consent for a use like this, and to whom.
- Robots files were read on one host for each of CivicClerk, Municode Meetings, Legistar, Granicus, Swagit, CivicWeb and the county association sites. Another customer's host may differ.
- The terms of each Legistar government, each county and every government that posts files on its own site. None is read.
- The Legistar Web API was not called. Which of the 14 governments require a token is not known.

## Options for the owner

**For the 100 governments on CivicPlus products**

1. **Ask CivicPlus for written consent.** The terms name this path. **The owner sent the request on November 21, 2026. No answer yet.** Until one comes, the three CivicPlus platforms stay restricted. A short request can say what the radar is, that it reads public agendas at one request every 10 seconds and that it trains no model.
2. **Ask the governments.** The terms say the right to a public record comes from the government under law. A government could send its agendas, or agree in writing to their collection. I have not checked what Texas law requires a government to provide or how.
3. **Leave them to hand reading,** after counsel has answered the question above.
4. **Leave them out.**

**For the rest**

5. **Legistar: done.** Each of its 14 governments' own terms was read and the collector uses the published API. Nine governments are read, Harris County and Dallas among them. Five are held out. See [tx_agendas_legistar.md](tx_agendas_legistar.md).
6. **Then the five county association sites and the 114 own-site governments,** each after its own terms and robots file are read.

Nothing above is done. Each needs the owner's word.
