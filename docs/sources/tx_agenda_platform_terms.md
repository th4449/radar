# Texas agenda platforms: what their own rules say

- Milestone: M8
- Registry: `config/tx_agenda_platforms.csv`
- Read: November 21 and 22, 2026
- Result: **six platforms restrict a collector** by their vendor's terms or their robots file. **Legistar is cleared** and has a collector. **Governments' own sites are cleared one site at a time** and have a collector. **The five county association sites are cleared** and the own-sites collector reads them. **Of eleven smaller outside services, seven restrict a collector.** Nothing was found against the other four, and none of them is cleared.

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
| County association sites | Texas Association of Counties | 5 | none | **Cleared.** All 5 are read. See [tx_agendas_own_sites.md](tx_agendas_own_sites.md) |
| Files on the government's own site | each government | 111 | each site's own | **Cleared, one site at a time.** 95 sites read, 52 governments collected. See [tx_agendas_own_sites.md](tx_agendas_own_sites.md) |
| Eleven smaller outside services | various | 26 | each its own | **Seven restricted, four with nothing against them and not cleared.** See "The smaller outside services" below |

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
- **7 more governments post files on a site CivicPlus builds and hosts,** outside its meeting products: Buffalo Gap, Clyde, Malakoff, Mustang Ridge, Creedmoor, Grapevine and The Hills. Each page carries the credit "Government Websites by CivicPlus". The terms address any user of a CivicPlus site, so these seven are held too, as `vendor_site` in `config/tx_agenda_site_terms.csv`. Found November 22, 2026. The collector had read the first four on November 21 and 22.
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

**Cleared on November 22, 2026.** The Texas Association of Counties provides these sites. None of the five has a robots file, and neither has the association's host for files and calendar feeds. None links a terms, privacy or policy page. The association's terms for county.org say nothing on automated access and bar copying for commercial purposes. The software vendor, ezTask, publishes a privacy policy for its own website only. The owner said on November 22, 2026 to start on these sites. The full reading is in [tx_agendas_own_sites.md](tx_agendas_own_sites.md).

Not verified: whether the association's terms reach the county sites. None of the five links them.

## The smaller outside services

**Read on November 22, 2026,** on the owner's word. 28 governments sat in the inventory under one name, "other", with no rules read. They are on eleven services, and one county has no agenda to read. Each service now has its own name in the inventory and its own row in `config/tx_agenda_platforms.csv`.

For each service I read the robots file of the host that holds the agendas, with one identified request, and then the service's terms.

| Service | Governments | Robots file | Terms | Standing |
|---|---:|---|---|---|
| Google Drive and Docs | 11 | allows folder, file and document pages | bar automated access only where a robots file bars it | Nothing against it. **Not cleared** |
| HeyGov | 4 | no rule on the file host. **The API bars every agent.** Each city's file allows | speak of heygov.com only | **Cleared on November 22, 2026.** 2 read, 2 closed by the API's robots file |
| JustMeetings, once AgendaLink | 1 | allows. Says no AI training | none found | Nothing against it. **Not cleared** |
| Laserfiche portal | 1 | none | silent on automated access | Nothing against the portal. **The one city's own site refused** |
| TownCloud | 3 | bars every agent | not read | **Restricted by robots** |
| eCode360 | 2 | allows the document addresses | personal use only | **Restricted by terms** |
| Diligent Community | 1 | bars every agent | not read | **Restricted by robots** |
| Documents On Demand | 1 | bars every agent | not read | **Restricted by robots** |
| Municipal Impact | 1 | allows, 5 second delay | the town's own terms bar robots | **Restricted by terms** |
| Dropbox | 1 | bars shared file addresses | not read | **Restricted by robots** |
| BoardBook | 0 | none | bar copying by a robot | **Restricted by terms** |

**9 governments are on a restricted service. 17 were on one with nothing found against it.** A service with nothing against it is a `candidate` in the registry. No collector takes it until the owner says so and each government's own terms are read. The owner cleared HeyGov the same day: see "HeyGov, cleared" below. The other three, 13 governments, are still candidates.

### Nothing found against

**Google Drive and Docs.** Briaroaks, Buckholts, Clifton, Cottonwood Shores, Coyote Flats, Cranfills Gap, Hico, Italy, Paradise, Reno and Runaway Bay.

- **Read:** Google's Terms of Service, https://policies.google.com/terms, effective July 30, 2026. Drive's added terms, effective October 22, 2025. The abuse policies for Drive and Docs. I read the passages on automated access and on other people's content, not every section.
- Among the things users must not do, the terms list using automated means to reach content against the machine-readable instructions on Google's pages. A robots file is the example they give. Automated access that keeps to the robots file is not on the list.
- The robots files of `drive.google.com` and `docs.google.com` allow folder, file and document pages for every agent and ask for a 1 second delay. They bar the direct download address.
- The terms say content that belongs to someone else may be used only with that party's leave or as the law allows. A city's posted agenda is a public record.
- **What stands in the way is how the pages work.** A folder page draws its list by script, and the address a file downloads from is barred. Reading a folder needs Google's Drive API, which takes a key from a Google account. A key is a secret, and the API has terms of its own that I have not read. Nothing is built.

**HeyGov.** Highland Haven, Sanctuary, Sandy Oaks and Shallowater.

- Each city lists its agenda files on its own page. Town Web builds the sites. The files sit on `files.heygov.com`.
- **Corrected the same day:** I first wrote that all four pages hold their lists as plain links. Two do. See "HeyGov, cleared" below.
- The file host's robots file holds a notice about content signals and no rule. Each of the four cities' robots files allows every path.
- **Read:** HeyGov's terms, https://heygov.com/terms-and-conditions. They speak of the website at heygov.com and bar republishing or copying its material. My reading is that this means HeyGov's own material, not a city's agenda. That reading is not verified.
- Town Web's home page links a privacy policy and an accessibility statement. I found no terms of use.
- I opened Sandy Oaks' page in a browser. It links a privacy policy of its own.

**HeyGov, cleared.** The owner said on November 22, 2026 to go ahead with the four cities. I then read each city's own pages and looked at each agenda page as the server sends it, before any script runs.

| City | Its own pages | The agenda page as served | Standing |
|---|---|---|---|
| Sandy Oaks | a privacy policy and an accessibility statement. Silent on automated access | holds the list: 1,078 links to its HeyGov folder | **Read** |
| Shallowater | the same two pages, the same wording | holds the list: 326 links | **Read** |
| Highland Haven | the same two pages | holds no list. A script draws it from `api.heygov.com` | **Closed by robots** |
| Sanctuary | a privacy policy, the same wording | holds no list. The same script | **Closed by robots** |

- **The robots file of `api.heygov.com` bars every agent from every path.** I read it with one identified request. A collector could list Highland Haven's and Sanctuary's agendas only by asking that API, so it does not. Their files sit on the file host, which bars nothing, but the collector has no list to find them by and does not guess addresses.
- **My earlier note was wrong for those two.** I had read all four pages through a browser, where the script had already run, and wrote that each holds plain links. The check that caught it was asking for the page with no script.
- No city links any terms of use. Each footer names Town Web as the site's builder.
- The file host's robots file was read again: the same notice about content signals, and no rule and no signal line.
- **The collector takes a HeyGov file only from the folder named for the city's own site,** `files.heygov.com/<the city's site>/`. Another city's folder and HeyGov's other hosts are never followed.
- Sandy Oaks and Shallowater are read by the own-sites collector. See [tx_agendas_own_sites.md](tx_agendas_own_sites.md).

**JustMeetings.** Cibolo.

- The city's page embeds a meeting page on `horizon.agendalink.app`. The agenda file is on `files.justmeetings.com`. MCCi sells the product.
- `horizon.agendalink.app` has no robots file. The file host's robots file allows every path for an agent it does not name, bars a list of named AI crawlers and says content may not be used to train AI models. The radar trains no model.
- **No terms of use were found** on justmeetings.com, agendalink.app or the meeting page. MCCi links a privacy policy only.
- The meeting page is drawn by script. A collector would have to be built for it.

**Laserfiche portal.** Sunset Valley.

- The portal's robots address answers with the portal's own page. It publishes no rules.
- **Read in full:** Laserfiche's Terms of Use, effective May 22, 2023. They speak of Laserfiche's website and services. They ask users not to copy content they have no right to. They say nothing on automated access.
- **Sunset Valley's own site, which lists the agendas, answered 403 for its robots file.** A robots file that cannot be read is a refusal. Nothing of Sunset Valley is read.

### Restricted

- **eCode360.** New Deal and Slaton. **Read in full:** General Code's terms, https://ecode360.com/docs/TOS.html, undated. Content is for personal use only. They bar copying any part of the site for commercial, non-profit or public purposes. The robots file allows the document addresses and says content may not be used to train AI models. The terms settle it.
- **BoardBook.** Milam County. **Read in full:** the terms at https://www.boardbook.org/boardbook-terms-and-conditions-of-use, version of June 11, 2020, from the Texas Association of School Boards. They cover the online applications at boardbook.org. They bar copying or distributing any content by a robot, spider or other automatic process unless the supplier authorizes it. `meetings.boardbook.org` has no robots file. **Milam County also posts its agendas on its own site, and is read there.** See [tx_agendas_own_sites.md](tx_agendas_own_sites.md).
- **Municipal Impact.** Trent. The robots file allows the agenda pages with a 5 second delay. **The town's own terms of service** say the license to use the site does not include robots or data gathering tools, and bar downloading without written consent. It is the same wording as Alma's and the eight sites closed on November 21. The vendor's terms for its own website, https://municipalimpact.com/terms/, bar copying beyond one-time personal use.
- **TownCloud.** Hudson Oaks, Murchison and Volente. The robots file on `towncloud.io` bars every agent from every path.
- **Diligent Community.** Bee Cave. The robots file on the city's Diligent host bars every agent from every path, then names several hundred more.
- **Documents On Demand.** Hood County. The robots file on the county's host bars every agent from every path.
- **Dropbox.** De Kalb. The robots file on `www.dropbox.com` bars shared file addresses for every agent it does not name.

For the last four the vendor's terms were not read. The robots file settles each.

### One county with nothing to read

**Matagorda County** stays under "other". Its agenda page is on a county association site and showed no agenda on November 21 or on November 22, 2026, in a browser both times.

### A fault in the fetcher, found here and fixed

Documents On Demand's robots file starts with a byte order mark, three bytes a reader does not see. The parser took the first line as no rule at all. **A file that bars every path read as allowing every path.**

- The fetcher now strips the mark before it reads a robots file. A test holds it, with that file's exact bytes.
- No request was made on the wrong reading. I caught it comparing the parser's answer with the file's plain text.
- I checked the 182 robots files saved since November 21. Two others start with the mark. Both are error pages with no rules, so no earlier decision changes.

## What is not verified

- **Whether CivicPlus' terms bind a visitor to a government's site.** That is a legal question.
- **Whether a person's hand reading of a CivicPlus-hosted agenda may then be scored by the radar.** Section 8 speaks of using authority data, not only of collecting it. This needs counsel before reviewers are set to work on those sites.
- Whether CivicPlus gives written consent for a use like this, and to whom.
- Robots files were read on one host for each of CivicClerk, Municode Meetings, Legistar, Granicus, Swagit, CivicWeb and the county association sites. Another customer's host may differ.
- The terms of the 38 own-site governments whose inventory rows are not confirmed.
- **For the smaller services:** whether HeyGov's terms reach a city's files on its file host. The owner went ahead on my reading that they cover HeyGov's own website. Whether HeyGov would let a program read its API if asked. Google's API terms. What the signal `use=reference` in the JustMeetings and eCode360 robots files asks of a reader. The terms of TownCloud, Diligent, Documents On Demand and Dropbox. The own terms of the 12 governments on Google Drive and JustMeetings.
- I read each smaller service's robots file on one host. Another customer's host may differ.
- Volente keeps older agendas on its own site and Bee Cave's development corporation has a site of its own. Neither was opened.

## Options for the owner

**For the 100 governments on CivicPlus products**

1. **Ask CivicPlus for written consent.** The terms name this path. **The owner sent the request on November 21, 2026. No answer yet.** Until one comes, the three CivicPlus platforms stay restricted. A short request can say what the radar is, that it reads public agendas at one request every 10 seconds and that it trains no model.
2. **Ask the governments.** The terms say the right to a public record comes from the government under law. A government could send its agendas, or agree in writing to their collection. I have not checked what Texas law requires a government to provide or how.
3. **Leave them to hand reading,** after counsel has answered the question above.
4. **Leave them out.**

**For the rest**

5. **Legistar: done.** Each of its 14 governments' own terms was read and the collector uses the published API. Nine governments are read, Harris County and Dallas among them. Five are held out. See [tx_agendas_legistar.md](tx_agendas_legistar.md).
6. **Own sites: done.** The owner said on November 21, 2026 to build for the 76 governments whose rows were confirmed, and on November 22 to check the other 38. 52 governments are read. See [tx_agendas_own_sites.md](tx_agendas_own_sites.md).
7. **The five county association sites: done.** Their robots files and terms were read on November 22, 2026 and all five are read. See [tx_agendas_own_sites.md](tx_agendas_own_sites.md).

**For the smaller outside services**

8. **HeyGov: done for 2 of 4 governments.** The owner said on November 22, 2026 to go ahead. Sandy Oaks and Shallowater are read. Highland Haven and Sanctuary are closed by the robots file of HeyGov's API. To open them, ask HeyGov for leave to read the API, or ask each city for its agendas.
9. **Google Drive: 11 governments.** It needs a collector that uses Google's Drive API, and a key, which is a secret the owner would add. I have not read the API's terms or checked whether it costs anything.
10. **JustMeetings: 1 government.** It needs a small collector for a page drawn by script.
11. **The seven restricted services: 9 governments.** Leave them out, or ask the government for its agendas.

Options 1 to 4 and 9 to 11 are not done. Each needs the owner's word.
