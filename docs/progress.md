# Progress

Newest first. Each entry says what was built, what was verified live and what is still unverified.

## November 26, 2026 — The database's address is not set: Supabase refused the password change

**On the owner's word.** The owner said to fix `RADAR_DATABASE_URL`. Committed earlier and not pushed: `411f45d`.

- **Why it needs a password.** The jobs connect as the database's owner role. Nobody holds that role's password: Supabase made one when the project was created and showed it to no one. So the address cannot be written until the password is set again.
- **What was tried.** One statement on the hosted database, through Supabase's own tool, to give the owner role a new password. It carried only the password's verifier, the form Postgres stores, because the hosted database logs every statement of that kind. The method was tried first on the local database with a throwaway role: the password connected and a wrong one was refused.
- **Supabase refused it:** "permission denied to alter role. Only superusers can alter privileged roles." That is Supabase's guard on its own roles. **Nothing was changed** and no secret was set. Supabase's tool has no command that resets the password. No other way in was tried.
- **What is left is the owner's:** reset the database password in the project's database settings in the dashboard. Then run `drafts/set_database_url.py`, which asks for the password without showing it, checks that the address connects through the session pooler and hands it to GitHub. It was tried against the local database with a right and a wrong password. The file is in `drafts/`, which git ignores.

- **The owner ran the helper twice, later the same day, and the password was refused both times.** The pooler answered from this machine and knew the project: "password authentication failed for user "postgres"". So the address's host and user name are right, and the password given was not the one the database holds. Nothing was set. `gh secret list` shows `RADAR_ARCHIVE_KEY` alone.
- **What Supabase's logs show, read the same hour.** The pooler logged each refusal with "using a one-off auth_query connection", so it asks the database afresh on each try and holds no old password. The database's log for the day holds one statement that changes a role's password: the refused one above, at 17:23 UTC. It holds none from a reset. No network address is banned.
- **Two facts from Supabase's page on connecting**, read in excerpt on November 26, 2026 (`supabase.com/docs/guides/database/connecting-to-postgres`): the shared pooler answers on IPv4 on every plan, and the direct address needs a paid add-on to do so. The reset is in the project's Database Settings.

**Not verified:** the helper with a password the hosted database accepts, and that the pooler's address answers GitHub's servers. Whether a reset in the dashboard leaves a line in the database's log: not known, so the missing line suggests no reset reached the database and does not prove it.

## November 26, 2026 — The live switch is on and the archive's key is set

**On the owner's word.** The owner said: add `RADAR_ARCHIVE_KEY` and set `RADAR_LIVE` to true. The owner also said the radar will be at `standuptocorruption.org/radar`. Pushed earlier, on the owner's word: `e22c50e`, CI passed.

- **`RADAR_LIVE` is the word true.** It reads back from GitHub as set. From now on a workflow started on GitHub is a real run, not a dry run. Nothing started: no workflow has a schedule and none was started by hand.
- **`RADAR_ARCHIVE_KEY` is a GitHub secret.** It is the hosted project's `service_role` key. It was piped from Supabase's tool into GitHub. It was never printed, and it is in no file.
- **Checked before it was set,** with two read-only requests to the hosted storage: the key reads the `archive` bucket, the bucket is private and it holds no files.
- **The project's newer secret key was not used.** Supabase's tool hides its value, so it could not be passed on. Two things follow, both from Supabase's own pages, read in excerpt on November 26, 2026. The older key and the older public key are signed by one secret, so revoking that secret ends both. And Supabase says it is retiring both older keys in early 2027. **Before then the owner should make a secret key in the project's API key settings and put it in `RADAR_ARCHIVE_KEY`.** Sources: `supabase.com/docs/guides/auth/signing-keys` and `supabase.com/docs/guides/getting-started/api-keys`.
- **A real run still cannot start.** `RADAR_DATABASE_URL` is not set. A run without it stops with "a real run needs DATABASE_URL and an archive" before it asks any site for anything. That address holds the database's password, which only the owner can set or read.
- **A dry run on GitHub is no longer possible through the workflows.** With the switch on, each one goes straight to a real run. A dry run still works from this machine.
- **The site's address is written down and nothing is hosted there.** `config/email.yaml` still has no site address: that is one of the three locks on real email and it was not asked for.
- **The build does not work under `/radar` yet.** 39 links start at the root of a domain, the sign-in emails send a person back to `/account/` and `/review/`, and the build sets no base path. Not changed in this step.

**Not verified:** a workflow on GitHub's servers. None has been started. Whether GitHub stored the key whole: a secret cannot be read back, so the proof is the first real run.

## November 25, 2026 — Two GitHub variables are set

**On the owner's word.** Pushed earlier, on the owner's word: `cff1d97`, CI passed.

- `RADAR_CONTACT` is the project's public contact address. `RADAR_ARCHIVE_URL` is the hosted project's address. Neither is a secret, and both read back from GitHub as set.
- **A correction.** I told the owner four settings stood between the radar and real runs. There are five. I had left out `RADAR_CONTACT`, without which a workflow refuses to start, even as a dry run.
- **Three are not set and are the owner's:** the secrets `RADAR_DATABASE_URL` and `RADAR_ARCHIVE_KEY`, and the switch `RADAR_LIVE`. Until then every workflow is a dry run and keeps nothing.

**Not verified:** a workflow on GitHub's servers. None has been started.

## November 25, 2026 — A long file's summary names the page

**On the owner's word.** The owner was told that 142 of 228 Texas file signals read "past its first page", was offered *uses the words "data center" on page 2*, and said to name the page. Pushed earlier, on the owner's word: `bc98731`, CI passed.

- **The rule:** where a file has more than two pages, the words are not on its first page and the file's own page numbers are sure, the summary names the page.
- **The wording.** The one-page form is the one the owner was shown first. The owner was then shown all four and said the same day to keep them. The approval is noted beside the wording in `pipeline/signals.py`.

| Pages with the words | The summary ends |
|---|---|
| One | *on page 2.* |
| Two | *on pages 2 and 3.* |
| Three | *on pages 2, 3 and 7.* |
| Four or more | *on 5 of its pages, first on page 3.* |

- **Where the numbers are not sure, or the words are only in a file attached inside the PDF,** the summary still ends *past its first page*, the wording the owner approved on November 24.
- Nothing else changes: which files are signals, how sure, the meeting they are held to and the reference line.
- `RULES_VERSION` is `2026-11-25.1`.
- Tests came first: 6 new. 1,398 pass.
- **On the stored Texas agenda files, all 142 now name a page:** 93 one page, 37 two and 12 three. None has four or more and none falls back. The other 86 of the 228 read "An agenda that", as before. A real one: *A 3-page file that Maud posted for a meeting of January 1, 2026 uses the words "large load" on page 2.*

**Not verified:** the four-page form on a real file. No stored file has the words on four pages or more.

## November 25, 2026 — Every letter of the day is out

Pushed earlier, on the owner's word: `cae92af`, CI passed.

**The owner said** Ross Township's letter and Revize's letter are sent, and gave an address for Southgate.

- **Southgate's notice: sent** from the Dekleptocracy Alliance mailbox to the address the owner gave, an address at `southgatemi.gov`. The text is the notice the owner approved.
- **Eighteen letters are out.** Nine went on November 25:

| To | What | Sent by |
|---|---|---|
| Otsego Township | request for permission | the session, on the owner's word |
| Berlin Charter Township | request for permission | the session, on the owner's word |
| Plymouth Charter Township | request for permission | the session, on the owner's word |
| Rockwood | request for permission | the session, on the owner's word |
| Ross Township | request for permission | the owner |
| Dearborn | notice that its agendas are read | the session, on the owner's word |
| Keego Harbor | notice that its agendas are read | the owner |
| Southgate | notice that its agendas are read | the session, to the address the owner gave |
| Revize | question about its robots rule and 24 sites | the owner |

- Nothing drafted is unsent.
- The watch on the mailboxes lists all eighteen. An objection from Dearborn, Keego Harbor or Southgate goes first in its report.

**Nothing changes until an answer comes.** The five held sites stay held and the 24 Revize sites stay closed.

**Not verified:** that any letter arrived. Which address the owner used for Ross Township, Keego Harbor and Revize is not known to the session.

## November 25, 2026 — A county's contract for space in its own data center is set aside

**On the owner's word:** add the county contract's wording to the list that sets aside a government's own computers. Pushed earlier, on the owner's word: `2dc53f6`, CI passed.

- **Two entries under `own_computers` in `config/keywords.yaml`,** both spellings as the contract writes them: "data center use & services" and "data center use and services". They come from page 92 of the Keego Harbor packet read that day.
- "Data center use" by itself is not added. It is how a zoning item names the land use.
- Tests came first: 2 new, on the contract's own lines. One holds that the same words beside a rezoning still give the signal.
- **On the file itself:** the words "data center" are now set aside. The file still gives one draft signal, for "development agreement" alone on page 16, as sure as 0.3 where it was 0.9, held to no meeting. It opens no site.
- **On the stored Texas agendas: nothing changes.** The same 1,052 signals and the same 31 items set aside. No Texas document holds the words "data center use".
- The rules' version changes by itself when the keywords file does.

**Also recorded.** The owner said Keego Harbor's notice is sent. Fifteen letters are out. Southgate's notice, Ross Township's letter and Revize's letter are not sent.

**Tests.** 1,392 pass.

**Not verified:** the wording on any other county's contract. Another county will word its services differently, and each new wording needs its own record.

## November 25, 2026 — A notice to Dearborn. Southgate's and Keego Harbor's are the owner's to send

**On the owner's word:** send the three cleared cities a notice in place of the request. The owner was shown the three changes first: the subject, the opening and the words after the quoted terms.

- **Dearborn: sent** to the City Clerk, at the address on the city's clerk page.
- **Southgate: not sent.** The city's contact page says it lists no addresses "due to spam bots" and writes the clerk's office address out in words. A program did not use an address the city keeps from programs. The notice is written, in `drafts/mi-notices-2026-11-25.md`.
- **Keego Harbor: not sent.** Its contact page gives a form and no address. The notice is written, in the same file.
- Four pages were read for this by the radar's reader, once each: a clerk or contact page of each city, and Southgate's contact page.
- The watch on the mailboxes lists fourteen letters.

**Not verified:** that any of the five letters of the day arrived.

## November 25, 2026 — Letters sent, three Michigan sites cleared and read, three Texas checks run

**The owner's words:** send the letters, pull the Michigan data for the sites that allow non-commercial use, and run the three Texas checks. Pushed earlier the same day, on the owner's word: `69040fa`, CI passed.

**1. Four letters were sent. Four were not.**

- **Sent,** by email from the Dekleptocracy Alliance mailbox, each as the owner saw it: Otsego Township, Berlin Charter Township, Plymouth Charter Township and Rockwood. Otsego Township's address is on its home page. The other three are the clerk's address on each site's clerk page, which the radar's reader opened once.
- **Not sent: Revize.** No address. Revize's own site bars every program, so its contact page was not opened.
- **Not sent: Ross Township.** Its contact page hides its addresses from programs and offers a form. The hidden addresses were not decoded. The form is the owner's to fill in.
- **Not sent: Keego Harbor, Southgate and Dearborn.** The owner cleared them the same day and their agendas were read. Each letter says "We have collected none of your agendas", which is no longer true. They need new words or no letter. That is the owner's to say.
- No message came back as undeliverable in the first minutes.
- The watch on the mailboxes now lists thirteen letters.

**2. Three sites are cleared and were read once.**

- Keego Harbor, Southgate and Dearborn are marked `noncommercial_cleared` in `config/mi_agenda_site_terms.csv`, a new mark that lets a collector take a confirmed row. Each note keeps the sentence that was read and the day. Tests came first. Texas' four sites with like terms are untouched.
- **What a collector could take in Michigan is now 121 rows of 56 governments,** 51 with their governing body: Allegan 12, Oakland 11, Washtenaw 9, Wayne 7, Kalamazoo 6, Monroe 6. It was 112 rows of 53.
- **The pull, by hand, nothing in a database:** 9 pages, 9 agenda files, no refusal, 21 requests. Two files are scans read by character recognition. The files are outside the repository, each under its hash.
- **One draft signal, and it is not a project.** A 151-page Keego Harbor packet uses "data center" on page 92 and "development agreement" on page 16. Both pages were opened. Page 92 is a county contract for computer services. Page 16 is a form's standing words. The set-aside for a government's own computers did not catch it: the contract says "Data Center Use & Services" and "County's Data Center", and neither is on the list. Adding a word is the owner's to decide.
- Both Michigan sources are still `manual`. No job reads them.

**3. The three Texas checks, on the stored history.** 1,784 agenda files and 3,635 Legistar agendas with 107,102 items. Read only.

- **How many agenda files take the "past its first page" wording: 142 of 228 signals, 62 percent.** The owner approved the wording on three Michigan files of 16. In Texas it is the common case. In 53 of the 142 the first page with the words is page 2, and in 20 it is page 11 or later. 15 of the 142 hold the direct term. Another 25 long files have the words on their first page, and 61 are one or two pages or uncounted. The page numbers of all 142 are sure, since the re-read.
- **The phrase "facility used for" changes nothing in Texas.** With it and without it the rules give the same 1,052 signals and set aside the same 31 items. No stored Texas agenda holds the phrase.
- **"Special land use" is not used in Texas' stored agendas.** No document holds the words, so the rule that stopped a signal on them alone removed none.

**Tests.** 1,390 pass, one of them new.

**Not verified, or not done**

- Whether the four letters arrived. No bounce is not proof.
- The three cleared sites' terms were not read again today. The sentences are those read on November 23.
- Dearborn's five other pages. Their rows are inferred and no second read confirmed them.
- The pull's files against a second read. The collector's newest agenda was not compared with the checks file.
- Whether a wording change is wanted for Texas, where most file signals read "past its first page".
- Nothing is pushed.

## November 25, 2026 — The hosted database is created and every migration is on it

**On the owner's word.** The owner was told the price, 10 dollars a month, and said to create it. Pushed earlier the same day, on the owner's word: `861c1bb`, CI passed.

- **A Supabase project named `radar`,** in the owner's organization, us-east-1, Postgres 17. Created through the account's connector with the price confirmed.
- **All 14 migrations applied in order** with `supabase db push`, from this checkout linked to the project. A dry run listed them first. The ledger holds 14 rows under the files' own numbers, `20261119000001` to `20261124000001`.
- No secret passed through the session. The push used the sign-in the Supabase tool on this computer already holds. The database's password was never shown or set by me.

**Checked on the hosted database**

- **Its schema is the local one's.** A dump of the `public` and `private` schemas from each is the same, line for line: 2,334 lines, 19 tables, 30 policies, every grant, function and trigger.
- Every table in `public` has row level security on. The anonymous role holds one grant: select on `public_alerts`. That view has the `study_payers` column.
- **Asked through the hosted API with the public key:** `public_alerts` answers with an empty list. Twelve other tables and views were refused: documents, signals, sites, subscribers, reviewers, corrections, the audit log, the settings, the record of emails sent, both study tables and `document_refs`.
- The archive bucket exists, is private and has no policy. The public key lists nothing in it.
- Settings: one confirmation, the approval gate on.
- PostGIS 3.3.7 is in the `extensions` schema.
- No row in documents, signals, sites, reviewers or subscribers.

**What Supabase's own security check says,** all by design and none changed:

- Two views run with their owner's rights: `public_alerts` and `document_refs`. That is how the anonymous key reads one narrow view over tables it cannot read.
- Five functions run with their owner's rights and can be called through the API: `submit_correction` and `unsubscribe` by anyone, `confirm_subscription`, `merge_sites` and `reviewer_directory` by a signed-in user. Each is the one door to what it does and checks its caller.
- `alert_sends` has row level security and no policy. Only the service role reads it.

**Not verified, or not done**

- **The policy tests on the hosted database.** They need its address, a secret, and they write test rows. They pass on the local database, whose schema is the same.
- **No job can reach it.** The owner adds `RADAR_DATABASE_URL` and `RADAR_ARCHIVE_KEY` as GitHub secrets and `RADAR_ARCHIVE_URL` as a variable. `RADAR_LIVE` stays the owner's switch. None is set.
- The archive against the hosted storage service. `collectors/hosted_archive.py` has run only against the local copy.
- No administrator exists. The owner creates the first by hand.
- The sign-in settings of the project: its site address, its redirect addresses and its emails are as Supabase made them.
- No copy of the study's page is stored there, so nothing is matched.
- The stored history was not copied to it.

## November 25, 2026 — Five things the owner asked for: one cannot be done, four are

**The owner's words:** apply the migration to the hosted database, switch on the study source, draft a letter to Revize about the 24 closed sites, re-read stored documents so their page numbers are right, and address the eight Michigan sites whose terms are held and Otsego's files on a second host.

**1. The migration: not applied. There is no hosted database.**

- **A correction first.** Notes of November 24 and my messages to the owner spoke of "the hosted database". None exists. The Supabase account lists four projects and none is the radar's. The repository has no variable and no secret. The stored history is in `radar_backtest` on the owner's computer, as the launch checklist has said since November 23. Seven lines below are corrected where they stand.
- Creating a hosted project is a paid resource and the owner's decision under section 11. It was not created.
- **The price, checked today:** the Supabase account priced a new project in the owner's organization, which is on the Pro plan, at 10 dollars a month.
- Three "not verified" lines of November 24 said a check could not be made because the documents were hosted. They are on this computer. Those checks are still not made: how many long Texas agendas take the "past its first page" wording, the set-aside phrase against the 28 items the owner reviewed, and how often "special land use" stood alone in Texas.

**2. The study source is switched on.**

- `us_qpq_data_center_payers` is `http`, its collector is on the list in `collectors/run.py`, and `.github/workflows/collect-us-qpq-data-center-payers.yml` starts it by hand. No schedule. Like every workflow it is a dry run until the owner sets `RADAR_LIVE`.
- **One dry run by hand,** by the radar's reader: robots read, the page loaded, the parser read the table. Nothing kept.
- The methodology page lists it among the sources read, as "United States". That label is mine.
- **No copy is stored, so nothing is matched.** A real run needs a database to keep the copy in.

**3. A letter to Revize is drafted, not sent:** `drafts/revize-request-2026-11-25.md`, outside the repository.

- It quotes the rule, `Allow: /*.pdf$`, and shows why a file linked with `?t=` after `.pdf` falls outside it. It asks Revize to change the rule, to permit the files in writing, or to say the bar is meant.
- **The address is the owner's to fill in.** Revize's own site bars every program but seven named crawlers, read today, so its contact page was not opened.

**4. The re-read job is built and has run on the stored history.** `python -m pipeline.reread`.

- It notes, with each PDF stored before November 24, which of its pages hold no words. Where the stored text has a piece for every page, the note is empty and the file is not opened. Otherwise the file is read again from the archive, and the note is written only if it reads today as the stored text, to the letter, with the same count of pages.
- A signal already made from the file gets the file's own page numbers in the same step, and is marked. Nothing else about it changes.
- It writes nothing without `--write`, changes no stored text and fetches nothing from any site. 12 tests.
- **Run on the history database,** after a dump to `~/.local/share/radar/backtest/backups/`:

| | |
|---|---|
| PDFs with no note | 2,139: 1,777 agenda files and 362 ERCOT planning files |
| Noted without opening the file | 1,957 |
| Read again from the archive | 182: 181 agenda files and 1 ERCOT file |
| Read again and matched the stored text to the letter | 182 |
| Left without a note | 0 |
| Pages with no words, in those 182 files | 2,548. The most in one file is 156 |
| Signals changed | 0. The history database holds none |

- 14 of the 182 are scans read by character recognition. Each read today exactly as it was stored.
- **Checked afterward in the database:** for every one of the 2,139, the pieces of the stored text equal the file's pages less the pages noted. The count of documents is 5,919, as in the dump.
- Not verified: the stored text against the dump, byte for byte. The job has no statement that changes text. And the signal step on a real signal: it is tested on made-up files only.

**5. The eight held sites: a letter to each is drafted, not sent, and none is cleared.** `drafts/mi-held-sites-requests-2026-11-25.md`.

- Each home page was read once by the radar's reader for the address to write to. Otsego Township's gives an email address. The other seven give a contact or clerk page, which was not opened.
- The draft gives my reading of each sentence, for the owner to decide: Keego Harbor, Southgate and Dearborn allow non-commercial use on their plain words. Otsego Township, Berlin and Plymouth turn on the phrase "any means not intentionally made available". Ross Township and Rockwood need written permission. It is a reading, not legal advice.
- **Clearing any of the eight is still the owner's word.** "Address" was not taken as that.

**6. Otsego's second host counts as the city's own.**

- The reader asked `cdn-www-cityofotsego-org-g4w4.b-cdn.net` for its robots file. It answered with the city's own file, which bars `/wp-admin/` and names the city's sitemap. The agenda files are allowed.
- One agenda file was then fetched from it, once: a two-page PDF, the City Commission's agenda for November 16, 2026. Kept outside the repository.
- The host is listed in `OWN_FILE_HOSTS` and counts for Otsego's pages only. Three tests, written first.
- bunny.net's terms of service were read through a tool that gives a summary. It found nothing on robots or on the public's access. Not read in full.

**Tests.** 1,389 pass, 15 of them new. The web tests are 17, and the site builds.

**Not verified, or not done**

- Anything on a hosted database. None exists.
- The study workflow on GitHub's servers. It has not been started.
- Otsego's files through the collector on the live site. Both Michigan sources are still `manual`.
- Whether each of the eight sites' terms still read as they did on November 23.
- Revize's address.
- Nothing is pushed.

## November 25, 2026 — M12: the owner approved the methodology page's section on the study

- The owner was shown the section "Company names and the QPQ Tracker's study" as it stands on the methodology page and said to keep it. No word of it changed.
- The approval is noted at the top of `web/src/pages/methodology/index.astro`.
- All three pieces of the study's wording are now approved: the review page's note, the alert's section and this one.

**Verified:** the tests, the lint and the web checks pass. Nothing else changed.

**Still not verified, or not done:** everything listed in the two entries below, apart from this wording. Nothing is switched on. The migration is not on the hosted database. (Corrected the same day: there is no hosted database. See the entry above.)

## November 24, 2026 — M12: 45 operating companies added to the payers' names

**On the owner's word.** The owner asked for the research, was shown the list with its sources and said to add it.

- **45 names for 16 payers** in `config/study_payers.yaml`, each with the filing that states whose it is. 38 come from the company's own SEC filing, three from another company's SEC filing, three from the company's own site and one from a City of Detroit record.
- **A name listed with its legal form now meets a record only as written.** Without that, listing "Switch, Ltd." would have let "Switch LLC" match. It also closes the same gap for "Southern Company", which was already listed.
- A payer may now have several entries in the file, one for each source.

**How it was checked**

- Three research agents found the names. Each reported that the SEC refused a plain request and that it read the filings through a third-party fetch service.
- That reading was not relied on. The SEC's robots file allows its filings archive. All 20 filings were fetched directly, once each, with a user agent that gives the project's public contact address. The SEC answered every one, and the words were read in the saved copies.
- **On the Comptroller's saved list of 290 companies, 5 met a payer before and 19 do now.** A test holds that count.

**Tests.** 1,374 pass.

**Not verified, or left out**

- Walbridge Aldinger LLC, the two QTS names and the Vantage name were read with a web reading tool, not as raw files.
- Numbered project companies, such as "Vantage Data Centers TX11, LLC", are left out. No filing was found that states whose they are. The same holds for the project companies that only news reports tie to Google.
- Electric Transmission Texas, LLC is left out: a joint venture of AEP and Berkshire Hathaway Energy.
- Whether each filing is still current. Switch's is from 2021.
- Oncor's annual report says a Sempra subsidiary owns 80.25% of it, and Sempra is a separate payer in the study. Nothing was changed for that.
- Still nothing is matched in a database: no copy of the study's page is stored.

## November 24, 2026 — M12: the money cross-reference, built and not switched on

**Two departures from the plan, both put to the owner first.** The owner said to build it this way.

- **The study's page, not its API.** The plan says to match through the QPQ Tracker's API. The site's robots file bars `/api/` to every agent, and no endpoint returns the list of payers. The study's page is allowed and holds the whole list.
- **Names, not parent companies.** The plan says to match resolved parent companies. The radar has none: `entities.parent_entity_id` has been empty since M4. Matching is on a company's name as a record gives it.

**Built**

- **Source note** `docs/sources/us_qpq_data_center_payers.md`: the robots file, the API notes, the missing terms page and what the page holds.
- **Collector** `collectors/us/qpq_data_center_payers.py`. One page. It reads the table of 61 payers: name, class, direct giving, contributions, states and the address of each payer's page. A new copy is stored only when the table says something new. A changed layout fails the run and keeps the page for a person.
- **Matching** `pipeline/study.py`. A company meets a payer when the whole name is the same, with a legal form at the end set aside. A longer name never matches.
- **Other names** `config/study_payers.yaml`. 11 payers have other names, 17 names in all. Each is a part of the payer's label or a filer the page lists under it. Four names that are ordinary words match only when they stand alone: Switch, Meta, Oracle and Amazon.
- **Two tables** `study_payers` and `entity_study_payers`, rebuilt from the newest stored copy on every processing run. Policy tests were written first. Approved reviewers read them. No one writes through the app. The anonymous key reads neither.
- **The review page** tells the reviewer a company has a payer's name, how the names met, the study's class for the payer and the states, with a link.
- **The public alert** gets a short section when there is a match: the payer's name as the study writes it, a link to its page and three sentences on what a match does not show. The public view never gives the name a record gave.
- **The methodology page** has a section on it.

**Verified live**

- One request for the study's page, through `collectors.capture`, on November 24. The radar's fetcher read the robots file and went on. The table was in the page as served, so no browser is needed.
- The 61 rows add up to the page's own figures: $148,392,563 and 16,389 contributions.
- On the local database's API: the review page's query answers, the public view gives the new column to the anonymous key and the payers table refuses it.

**Tests.** 1,351 pass, 93 of them new. The web tests are 17, and the site builds.

**Not verified, or not done**

- **Nothing is matched yet.** No copy of the page is stored, the local database holds no company, and the hosted database was not read. (Corrected November 25, 2026: no hosted database exists. The history database on the owner's computer holds no company either.) The matching is tested on the real list with names I wrote.
- **The migration is not on the hosted database.** The alert page now asks for the new column. Apply the migration before the site is built against that database. (Corrected November 25, 2026: no hosted database exists yet. The migration waits for one.)
- **The methodology page's section is mine.** The owner approved the wording of the review page's note and of the alert's section on November 24, 2026, and has not been shown the methodology section. (Shown and approved on November 25, 2026. See the entry above.)
- **Most real matches will be missed.** A project filed under a new LLC does not meet its parent. Subsidiaries the study's page does not name are not listed: CenterPoint Energy Houston Electric, AEP Texas, DTE Electric, Amazon Data Services and others. Adding them is the owner's call.
- 35 of the 61 payers are utilities. A utility named in an interconnection record says little about who is building.
- How often the study's list changes, and whether the site answers GitHub's servers.
- Neither page was looked at in a browser with a real match.
- No workflow file and no place in the registry, as with Michigan's agendas. Both come when the owner says to run it.

## November 24, 2026 — M11: a second run by hand, and three more faults fixed

**Pushed** on the owner's word, as `552734f`. CI passed.

**On the owner's word, nothing stored.** The 101 pages cleared now, up to two meeting pages from a list and one agenda file from each. Ann Arbor's Legistar was left out: nothing in that collector changed.

| | First run | Second run |
|---|---|---|
| Pages cleared | 145 | 101 |
| Pages read | 142 | 101 |
| Newest agenda matches the second read's | 111 | 79 |
| Differs | 22 | 13 |
| No agenda file on the list | 9 | 9, of which 7 are lists of meeting pages |
| Sites that refused | 25 | 0 |
| Files and agenda pages kept | 56 | 62 |
| Draft signals | 23 | 16 |

**What the run confirmed**

- The date fixes, where their pages are still read: Ganges Township's agenda is dated, and Lodi Township's mistyped 2027 is no longer its newest.
- **Novi is read.** Its two recent council agendas were kept from their own pages.
- **Heath Township is read.** Its file was fetched through its meeting page.
- **Plainwell is read:** three pages, three files. Its lists link PDFs. The second read's note that they end in `.aspx` was wrong, and so was my table that left it out.
- Otsego's file on another host and Lyndon Township's pages were named in the run log and not asked for.
- The 16 signals are the same 16 the keyword trial left. Three take the long-file wording.
- No fetched file carried a meeting date outside October 2026 to January 2027.

**Three more faults, fixed after the run, with tests. Not run again.**

- **A page's base address was ignored.** Allegan's page names one in its head, so its links are at the site's root and not beside the page. Each of its files was a 404 on both runs. My fixture had cut the base address out and my test held the wrong address. Both are corrected.
- **A link that leads to the file itself was kept as nothing.** Holly's list links a download address with no file type. The collector followed it as a meeting's page and kept an empty list. Such an answer is now kept as the agenda. It is tested on a made-up site, not on Holly's.
- **The labels of buttons were kept as words of a page.** One of Novi's agendas began with three of them.

**Not verified**

- The three fixes above, live.
- Nine of the first run's 22 differing pages. They are on Revize sites that are now closed.
- The 13 pages that still differ are not fixed: packets that nothing calls an agenda, names with no day or no year, and Novi's corridor authority, whose list holds old packet files and so is not followed.

**Cost:** about 230 requests by the radar's fetcher: 101 pages, 6 meeting pages, 62 files and pages kept, 4 that failed, and a robots request for each host. Worked out from the report.

## November 24, 2026 — M11: a list that gives each meeting a page of its own is followed

**Pushed** on the owner's word, as `35c53d8`. CI passed.

**On the owner's word.** Both Michigan sources are still `manual`. Nothing here has run live but the seven requests below.

**Seen first.** Seven identified requests by the radar's fetcher, robots read before each site: three list pages and one meeting page on each of four sites. Novi's list was saved on November 23. All seven loaded. Each is a fixture, cut down. One post author's name was taken out of a fixture.

**Four sites, four shapes**

| Government | What its meeting page holds | Read now |
|---|---|---|
| Novi | The agenda itself, written on the page, with a link to each packet item | Yes |
| Heath Township | A link to the agenda file on the township's own site | Yes |
| Otsego city | A link to the agenda file on another host | No. The run log names the file |
| Lyndon Township | Links with download addresses and no file type | No. The run log names the page |

**What was built,** in Michigan's collector only. Texas' does not follow such a list: it was not tried there.

- Where a list links no agenda file, the collector finds the links that lead to a page on the same site, say agenda or meeting, and give a day in their words or their address. It follows the recent ones, four at most.
- On a meeting's page it takes a file whose own words or name say agenda, two at most. A link to a packet item is not the agenda.
- Where the page links no such file and its main part says agenda and runs to 800 characters, **the page itself is the agenda.** Its words are kept, without the site's menus, and read for signals as a file's are.
- A past meeting's page that is stored is not asked for again. One for a meeting still to come is.
- The run log names a meeting page that holds no agenda, and a file on another host.
- Tests came first: 11 new, on the real pages. 1,256 pass.

**Not verified**

- **No run has followed a real list.** The tests run on the saved pages.
- Novi's three other lists, for its planning commission and two authorities. They are taken to read as its council's does.
- The 800-character line comes from one real page.
- What Lyndon Township's download addresses serve. None was asked for.

**The owner's, if wanted:** Otsego's agenda files sit on `cdn-www-cityofotsego-org-g4w4.b-cdn.net`. Reading them means reading that host's robots file and counting the host as the city's own. Neither is done.

## November 24, 2026 — M11: the pages with the terms are the file's own page numbers

**Pushed** on the owner's word, as `1b005ae`. CI passed.

**On the owner's word.**

**A correction first.** I told the owner a reviewer sees these page numbers. The review page did not show them. They were kept with the signal and never displayed. It shows them now, and only where they are sure.

- **The fault:** the stored text holds nothing for a page with no words, such as a scanned insert in a packet. The pages were counted over the text, so the count ran behind the file. In one real 260-page packet a term on page 170 was given as page 148.
- **The extractor notes which pages of a PDF have no words.** The archive step keeps the note with the document, as `pages_without_text`. No stored text changes.
- **The agenda processor gives the file's own page numbers.** Text from a file attached inside a PDF has no page of the PDF and is given none.
- **A document stored before the note was kept** gives its numbers as before. They are marked sure only when the text has a piece for every page.
- **The review page says where the words are,** under "Why it is here": *The words are on page 28. The file has 31 pages.* Where the numbers are not sure it says nothing.
- The wording for a long file still turns on the first page that has words. That is the agenda even behind a cover that is a picture.
- Tests came first: 6 in Python and 1 for the page, then 1 more for a scan. 1,245 and 14 pass. The page type-checks and builds.

**Checked against the real files.** The 56 Michigan agendas were read again from the scratch folder with the changed extractor. 2 of the 52 PDFs have pages with no words. One signal's pages moved, the 260-page packet's. **Each of the 37 pages the signals now name was opened in the file itself and holds one of the terms. None was wrong.**

**Not verified**

- Documents already in the hosted database carry no note. Their numbers can still run behind until each is read again. That would be a job over the stored files, and it is not built. (Corrected November 25, 2026: no hosted database exists. The stored documents are in the history database on the owner's computer, which that session could have read and did not.) The job was built and run on November 25, 2026.
- The page in a browser. It was built, not opened.
- Scans read by character recognition: the note is made there too, and is tested only on a made-up scan.

## November 24, 2026 — M11: a long file with the words past its first page is not called an agenda

**Pushed** on the owner's word, as `5cc8904`. CI passed.

**On the owner's word.** The owner read the wording and said on November 24, 2026 to keep it. It is in the summary a subscriber would read. Nothing uses it yet: both Michigan sources are `manual` and the site is not public.

- A packet binds the agenda to the minutes of earlier meetings and to lists of bills. In three of the 15 Michigan files that said "data center", the words were there and nowhere on the agenda. The summary called each an agenda for that day's meeting.
- **The rule:** where a file has more than two pages and the words are not on its first page, the summary does not call it an agenda. It says what the record shows.
- **The wording, as the owner approved it:** *A 31-page file that Augusta Charter Township posted for a meeting of November 24, 2026 uses the words "data center" past its first page.* The reference under it reads *Augusta Charter Township, file posted for the meeting of November 24, 2026.*
- Everything else reads as before: a file of one or two pages, a long file with the words on its first page, and a file whose pages were not counted.
- The same records are signals, as sure as before and held to the same meeting. A test holds that.
- Tests came first: 12 new. 1,238 pass.
- **On the 56 Michigan agendas: 3 of the 16 signals take the new wording,** the three that were found by reading: a list of bills, and two packets' minutes.

**Why no page number.** The stored text drops a page that has no words, so the count of pages with words can run behind the file's own page numbers. In 2 of the 52 PDF files it does. "Past its first page" is true either way. The same count is what a reviewer sees as the pages with the terms. That is not fixed.

**Not verified:** the rule on Texas agendas. A long Texas agenda that takes up a matter on its third page would read as a file, which is true and says less. How many do is not known: the stored documents are in the hosted database. (Corrected November 25, 2026: no hosted database exists. The stored documents are in the history database on the owner's computer, which that session could have read and did not.)

## November 24, 2026 — M11: an ordinance's definition of a data center is no longer set aside

**Pushed** on the owner's word, as `36460d6`. CI passed.

**On the owner's word.** The set-aside for a government's own computers is the owner's rule of November 23. It read one real item wrongly: the definition of "Data Center" in a Michigan township's moratorium ordinance, which lists "computer servers".

- `config/keywords.yaml`: the phrase "facility used for" is added to the rule's `unless` list. It comes from that item. The owner chose it over the single word "facility", which could bring back hosting items.
- Adding a word to that list can only keep more records. It cannot lose one.
- Tests came first: 2 new, one on the real item and one on a file that holds only such a definition. 1,226 pass.
- **On the 56 Michigan agendas: nothing is set aside now, where one hit was.** The same 16 signals, the same 10 labelled.

**Not verified:** the phrase against the 28 real Texas items the owner reviewed. They are in the hosted database and the local one is empty. (Corrected November 25, 2026: no hosted database exists. The stored documents are in the history database on the owner's computer, which that session could have read and did not.) The seven real hosting wordings kept in the tests are all still set aside. Another ordinance that words its definition differently would need its own word, from its own record.

## November 24, 2026 — M11: a label for the reviewer where "data center" sits beside the words of rule making

**Pushed** on the owner's word, as `7af9565`. CI passed.

**On the owner's word.** The owner read the wording and said on November 24, 2026 to keep it. No reviewer can see it yet: both Michigan sources are `manual` and the site is not public.

- `config/keywords.yaml` has a new list, `rule_making`: moratorium, ordinance, zoning amendment, text amendment. Each was read on a real agenda.
- **It is a label and nothing else.** Where one of the words sits in the same agenda item as "data center", the signal keeps which words. The record is a signal as before, with the same summary and the same confidence. A test holds each of those.
- The review page shows it under "Why it is here". The wording, as the owner approved it: *Also in the item: "moratorium", "ordinance". These are the words of a government writing its own rules. A project can use them too.*
- The last sentence is there because an ordinance can rezone land for a project. The label names the words and decides nothing.
- Tests came first: 5 in Python and 1 for the page. 1,224 and 13 pass. The page type-checks and builds.

**Tried on the 56 Michigan agendas: 10 of the 15 signals that say "data center" are labelled.**

| My reading of the file | Files | Labelled |
|---|---|---|
| A moratorium or a zoning ordinance | 11 | 9 |
| A named project | 3 | 1 |
| Unclear | 1 | 0 |

- **Two rule-making files got no label.** Their items use none of the four words: one says "no new draft", the other "resolution language".
- **One project file got the label.** The township's packet holds a list of state bills, one of them a statewide moratorium on data centers. The label is true to the words and says nothing false. It is not the township's own rule.

**Not verified:** the label on Texas agendas, and on any agenda item from Legistar beyond the tests. The page was built, not opened in a browser.

## November 24, 2026 — M11: "special land use" is no longer a reason by itself

**On the owner's word.** This changes a keyword rule that came from the build plan.

- `config/keywords.yaml` has a new list, `only_with_another_term`, with one term in it: "special land use". A record that uses it and no other term gives no signal. Beside another term it still counts and is still shown to the reviewer.
- The rule holds in every processor: agenda files, agenda items, planning files, permit rows and a file entered by hand. In an agenda file "beside" means anywhere in the file.
- Tests came first: 5 new, in four files. 1,219 pass.
- **Tried again on the 56 Michigan agendas: 16 signals where there were 23.** The seven that went are the drive-through, the campground and the like. Every file that says "data center" still gives its signal.
- Texas' saved agendas and tests read as before. No Texas test used the term alone.

**A correction.** I told the owner the set-aside for a government's own computers met nothing in the sample. It met one hit, and set it aside wrongly: a zoning ordinance's definition of a data center, which lists "servers". The table below is corrected. The rule is not changed.

**Not verified:** how often Texas' stored agendas used "special land use" alone. The stored documents are in the hosted database, which this session did not read. (Corrected November 25, 2026: no hosted database exists. The stored documents are in the history database on the owner's computer, which that session could have read and did not.)

## November 24, 2026 — M11: the keyword rules tried on 56 Michigan agendas

**Pushed** on the owner's word, as `3f9f2b3`. CI passed.

**No request was made and nothing was changed.** The 56 agenda files of the run by hand were still in the scratch folder. Their text was rebuilt from the files and matched the run's, file for file: 819 pages, 36 governments, meetings of November 4 to December 2, 2026. I read the words around every kind of hit.

| Rule | Hits | Files | What the files were about |
|---|---|---|---|
| "data center" | 86 | 15 | 11 a moratorium or a zoning amendment, 3 a named project, 1 unclear |
| "special land use" | 62 | 11 | a drive-through, a campground, a repair shop, a market, a subdivision. One was a data center overlay, which the direct term had caught |
| "development agreement" | 2 | 2 | a subdivision, and the data center overlay again |
| "light industrial", "data processing" | 3 | 1 | the data center overlay again |
| A project code name | 0 | 0 | none in the sample |
| A government's own computers, set aside | 1 | 1 | a zoning ordinance's definition of a data center, which lists "servers". Wrongly set aside. Corrected November 24: this row first said none |

**What it shows**

- **The direct term missed nothing.** Every file that says "data center" in any form gave a signal: 15 of 15.
- **"Special land use" alone is noise here.** It is Michigan's ordinary term for a use that needs a hearing. It gave 7 of the run's 23 signals by itself, and none of the 7 was about a data center or anything like one. "Development agreement" gave one more by itself, for a subdivision.
- **Most Michigan mentions are a town writing its rules, not a project arriving.** 11 of the 15: a moratorium in three townships, a zoning amendment or ordinance in eight governments. The signal's summary says only that the agenda uses the words. It does not tell a reviewer which kind it is.
- **Three were about a named project:** a line in a list of bills that names a company beside the words, the minutes of a township where one is being built, and a resolution about a university's.
- **In three of the 15 files the words were not in the agenda itself.** They were in a packet: a list of bills, or the minutes of an earlier meeting. The summary still calls the file an agenda for the meeting of that day.
- **One township's packet came out of extraction with its letters spaced apart.** The words still matched. The snippet a reviewer would see is hard to read.
- **One item a person would want and no rule caught:** "Power plant moratorium", on a township board's agenda.

**Not verified**

- 56 files from two weeks is a small sample. The newest file of each page only, and none from the 24 Revize sites or from Ann Arbor's Legistar, whose six agendas gave no hit.
- The code-name rule met nothing to try it on. The set-aside for a government's own computers met one hit and got it wrong: a definition in a zoning ordinance. The file still gave its signal from its other hits. A file that held only such a definition would give none. Not fixed.
- I judged what each hit was about by reading the words around it, not the whole file.

**Proposed, not done.** Each is the owner's: `config/keywords.yaml` came from the build plan.

1. Stop a signal on "special land use" alone.
2. Tell the reviewer when the words sit beside "moratorium" or "ordinance".
3. Say "packet" where the words are past the agenda's own pages.

## November 23, 2026 — M11: the Revize files stay closed, on the owner's word

**The owner said to leave the 24 Revize sites' files closed.** No address is built to pass the robots rule.

- The 24 sites are marked `robots_bar` in `config/mi_agenda_site_terms.csv`, the way Texas' two such sites are. No run asks them for anything, their lists included. A list with no file gives the radar nothing, and each run would have been refused 24 times.
- **I told the owner the lists would still be read. That was wrong** by Texas' own precedent, and is corrected here.
- **What a collector could take is now 112 rows of 53 governments,** 48 with their governing body: Allegan 12, Oakland 10, Washtenaw 9, Kalamazoo 6, Monroe 6, Wayne 5. It was 168 rows of 77.
- Seven other sites Revize builds stay cleared. Four gave the run a file. Three were not settled by it: Allegan, Birmingham and Sylvan Lake.
- A letter to Revize is not written. It would be the owner's to send.

**Not verified:** whether the three unsettled Revize sites' files are barred too. A run would be refused and say so.

## November 23, 2026 — M11: one run by hand of the Michigan collectors, nothing stored

**On the owner's word.** Each cleared page once and at most one agenda file from each, then Ann Arbor's list and its published agendas. The run log stayed in memory and the files in a scratch folder outside the repository. Both sources are still `manual`.

**Legistar, Ann Arbor:** seven requests, all answered. Six agendas, 127 items, no draft signal.

**Own sites**

| | |
|---|---|
| Pages asked for | 145 |
| Pages read | 142 |
| Newest agenda matches the second read's | 111 |
| Differs | 22 |
| No agenda link | 9 |
| Sites whose files a robots rule refused | 25 |
| Agenda files fetched | 56, of 36 governments |
| Text, and scans read by character recognition | 54 and 2 |
| Draft signals, stored nowhere | 23 |

**What the run showed**

- **Revize's file hosts refuse the files as the sites write them.** The robots rule allows an address that ends in `.pdf`. The sites add `?t=` and a number. 24 sites' files were refused, and the fetcher left each site alone. **My note of this morning said those files were open. It was wrong, and is corrected** in the source note and the robots table. The same file without the `?t=` mark is an address the rule allows. Whether to ask for it is the owner's to decide. It is not done.
- **Plainwell was not read.** The fetcher's robots request did not come back open. This morning's answer was a web page with a 200. Why it differed is not known.
- **The date reader misread six kinds of file name,** one of them badly: a 2012 agenda in a folder for 2012 was read as December 2026 and asked for as the newest. All six are fixed and tested on the names the run reported. A notice that there is no meeting is no longer an agenda.
- **Five or more pages' newest files are not taken:** packets that nothing calls an agenda on a page whose title does not speak of meetings, and names with a month and a day and no year. Not fixed.
- **15 of the 23 draft signals came from "data center",** in the agendas of 14 governments. Most are a moratorium or a zoning amendment under discussion. The other 8 came from "special land use" or "development agreement" alone. "Special land use" is Michigan's ordinary term. The keyword rules were written for Texas and need trying here before any Michigan signal reaches a reviewer.

**Code:** `collectors/tx/agenda_pages.py`, the date reader, for both states. 13 new tests. Texas' fixtures read as before.

**Not verified**

- The 142 pages were not read again after the fixes.
- Why three of Allegan's files failed. The run log does not keep the reason for a failure.
- Any file of the 24 Revize sites.

**Cost:** about 330 requests by the radar's fetcher: 7 to Legistar's API, 142 pages, 56 files fetched, 28 file requests refused or failed, and about 90 robots requests, one for each host. The count is worked out from the report, not logged. No subagent and no web search.

## November 23, 2026 — M11: Michigan collectors written on the owner's word

**The owner said the Texas clearing of own sites and Legistar holds for Michigan.** The platforms file records it for both. The eight sites whose terms are held stay held.

**What was built**

- `collectors/mi/legistar.py` and `collectors/mi/agenda_pages.py`. Each is the Texas collector pointed at Michigan's inventory: its own source id and its own state, nothing else. The Texas collectors gained a `state` setting so the two share one body of code.
- `tests/test_mi_agendas_legistar.py` and `tests/test_mi_agendas_own_sites.py`, 28 tests on saved fixtures.
- **No job can run either.** Both sources stay `manual`. The collectors are not on the list in `collectors/run.py` and have no workflow file. Tests hold that.
- Both sources now carry `verified_at: 2026-11-23`. That is what lets a person save a fixture by hand. It does not let a job run.

**Verified live, with the radar's fetcher**

- **Ann Arbor's Legistar answers the API without a token.** Two requests: the list of meetings from November 9 on, and one council meeting. Eight meetings, six with a published agenda.
- **Ten cleared own-site pages, one request each, robots read first.** All ten loaded. One for each of ten governing bodies across the six counties.
- **On nine of the ten the collector finds the agendas,** and its newest agenda matches the second read's.

**What the pages showed**

- **A fault, fixed.** Oshtemo Township lists a report of receipts and disbursements between its packets, in a file named for the meeting's day. Read as an agenda, it took the place of that day's packet. Such a report is now left. Texas' fixtures read as before.
- **Novi is not read.** Its list links each meeting to a page of its own, not to a file. By the second read's notes four more governments are the same or close: Otsego city, Lyndon Township, Heath Township and Plainwell. Following a meeting's page is one more request a meeting and a change to the collector. It is not built.
- **Seven governments' pages carry the year in their address,** 21 pages. Each needs a new inventory row in January.
- **Ann Arbor's calendar holds every board, not the four in the inventory.** A run would take them all, as Texas' does.
- **An Ann Arbor agenda named two people who signed up to speak.** The fixture leaves those two items out. A stored agenda would hold such names. The source is marked as holding personal rows.

**Not verified**

- What the collector finds on the other 135 cleared pages.
- Any agenda file. None was fetched, so text or scan is not known.
- The code-name signal rule on Michigan agendas.
- The four governments named beside Novi rest on the second read's notes, not on a page the collector read.

**Cost:** 12 pages and answers fetched by the radar's fetcher, and 12 robots requests before them, across 11 hosts. No subagent and no web search.

## November 23, 2026 — M11: each confirmed site's own terms read

**Pushed** on the owner's word, as `e6b3546`. CI passed.

**What was done**

- Five passes read the terms of the 90 hosts that carry a confirmed row, for 88 governments. Every home page loaded and none refused.
- The reading tool cut long sentences short. **Nine terms pages were then read in full by the radar's own reader,** one request each, robots checked first.
- `config/mi_agenda_site_terms.csv` holds one row for each host. `docs/sources/mi_agendas_own_sites.md` and `docs/sources/mi_agendas_legistar.md` are the source notes.

| What the site says | Hosts | A collector |
|---|---|---|
| No terms, disclaimer or privacy page | 63 | may read |
| A policy page that says nothing on automated access or reuse | 16 | may read |
| Terms bar obtaining material by means the site does not provide | 3 | held for the owner |
| Terms allow non-commercial use and ask consent for other use | 3 | held for the owner |
| Terms bar use or copying without written consent | 2 | held for the owner |
| Built and hosted by CivicPlus | 2 | held with the CivicPlus platforms |
| The home page gave the reader nothing | 1 | not read |

- **No site's terms name a robot, a crawler or a scraper.**
- **Held for the owner, eight sites:** Otsego Township, Berlin Charter Township, Plymouth Charter Township, Ross Township, Rockwood, Keego Harbor, Southgate and Dearborn. The source note quotes each sentence.
- Rochester and Dearborn Heights run on CivicPlus and wait with its platforms.

**What a collector could take: 168 rows of 77 governments,** 71 of them with their governing body. By county: Oakland 18, Washtenaw 13, Wayne 13, Allegan 12, Monroe 9, Kalamazoo 8. **No job reads any of them.** Both Michigan agenda sources are still `manual`, no Michigan collector is written, and a test holds both.

**Two things the shared platforms file does that the owner has not said for Michigan.** It clears "own_site_files" and Legistar on the owner's word of November 21, 2026, given for the Texas build. The same file now counts Michigan rows as cleared. I did not treat that as the owner's word for Michigan. It is asked.

**Code:** a government with two hosts is read only when both allow it. Before, the first row in the terms file decided. Rochester's development authority has its own site, which is why it mattered. A test holds it.

**Slips, as the passes reported them**

- One pass opened a page of legal postings on Dearborn Heights' site that was not a policy page.
- One pass added two words to the list it asked about. It filed the finding where the brief says.
- Waits between requests were not timed.

**Not verified**

- **81 of the 90 hosts rest on the reading tool's summary** that no terms page exists or that a page says nothing. I read nine in full.
- **The terms of 15 site builders were not read.** A builder's terms could cover the sites it hosts, as CivicPlus' do. Revize's and Granicus' speak of their own websites.
- Whether Ann Arbor's Legistar answers the published API without a token. No request has been made to it.
- The signal rule for a body meeting under a code name has not been tried on a Michigan agenda.

**Cost:** 10 requests by the radar's reader. The five passes made 151 tool calls and used about 755,000 tokens. No web search.

**Tests:** 1,173 pass.

## November 23, 2026 — M11: the four moved sites read, and a second read of 195 pages

**The owner's word:** read the four moved sites before the second reads start.

**The four moved sites**

- The radar's reader asked each new address for its robots file, once. All four redirect to the same Revize file as the old address and answer 404 there. No robots file, so open.
- A research pass then read the four sites. **Pontiac, Plymouth Charter Township and Van Buren Charter Township post agendas on their own sites.** Milford Charter Township sends its to Documents On Demand, which is closed.
- `config/mi_agenda_inventory.csv` now holds **526 bodies of 220 governments**. One row was dropped before it went in: a joint body on an outside host whose name and kind are not known.

**The robots files of every candidate host**

- A candidate is a row on the government's own site or on Legistar: 232 rows, on 198 pages, on 103 hosts, for 99 governments.
- The radar's reader asked each host for its robots file, once, six seconds apart. `docs/sources/mi_agenda_robots.csv` holds every answer of the day: 122 site hosts and the 13 Revize file hosts.
- **Two hosts are closed to the collector.** Detroit's site answered 403 to the robots request itself. Dexter Township's dropped the connection. Neither was asked again, and their three pages got no second read.
- Plainwell's site answers the robots request with its page-not-found page and a 200. That is no robots file. It was read as open.
- Six hosts ask for a delay between requests, of 3 to 20 seconds. No agenda page on an open host is barred.

**The second read**

- Six passes opened the other 195 pages, one request each, with no search and no agenda file opened. The readers were not told what the inventory says. **All 195 loaded. No host refused.**
- `config/mi_agenda_checks.csv` holds the 195 reads as observations. `pipeline/agenda_checks.py` compares them with the inventory.

| Verdict | Rows | Governing bodies |
|---|---|---|
| Confirmed | 194 | 80 |
| The newest agenda is old or undated | 12 | 5 |
| The page was read and showed no agendas | 17 | 4 |
| The body was not seen named on the page | 5 | 2 |
| The second read saw another platform | 1 | 1 |
| No second read: host closed | 3 | 1 |
| Total | 232 | 93 |

- **80 of the 93 candidate governments have a confirmed governing body.** Among them Ann Arbor, Dearborn, Pontiac, Novi, Farmington Hills and Auburn Hills.
- Not confirmed, for a person to read: Wayne County's commission page lists meetings and no agenda files. Belleville and the city of Plymouth draw their lists by script. Exeter Township's page holds minutes. Saugatuck's newest agenda is on Google Drive. Carleton and Royal Oak Township list agendas without naming the body. Five townships post one undated agenda.
- Five Dearborn boards show no agendas on the page the inventory names. Each links a page for the year, one step on, that was not opened.
- **A confirmed row is still not a collector's.** No site's own terms have been read: `config/mi_agenda_site_terms.csv` does not exist. A test holds that.

**Slips, as the passes reported them**

- The research pass on the moved sites asked one outside host, a development authority's, for its robots file. The request redirected to a Revize host and was not followed. The host was not read.
- Readers did not treat packets alike. Some counted a dated packet as an agenda and some did not. Dorr Township's three rows are not on the same footing.
- Three pages that list several bodies were captured in part: Lyndon Township, Riverview and Grosse Pointe Shores.
- Two readers removed backslashes that the reading tool had put before brackets in an address.
- About 24 long pages were read only in their first 100,000 characters, where the newest items sit.

**Not verified**

- **I opened no page myself.** Every observation came through the fetch tool's summary of a page, not its raw HTML. The tool may have completed a relative address. No read was made in a real browser.
- Which host the agenda files are on, where a page gives relative links. Those links are quoted in the notes and joined to nothing.
- The signal rule for a body meeting under a code name was written for Texas. It has not been tried on a Michigan agenda.

**Cost:** 83 requests by the radar's reader. The moved-sites pass made 24 tool calls and used about 159,000 tokens. The six second reads made 246 tool calls and used about 1.13 million tokens. No web search.

**Tests:** 1,171 pass.

## November 23, 2026 — M11: the Revize robots files read, and 27 more sites inventoried

**The owner's word:** read the Revize robots files where their redirect leads.

**What was done**

1. The radar's own reader asked each of the 39 unread sites for its robots file, once, six seconds apart, with the project's name and contact address in the request. It followed the redirect, as RFC 9309 section 2.3.1.2 says and as `collectors/base.py` already does.
2. **31 answered 404 where the redirect leads.** The site publishes no rules, so it is open.
3. **8 answered with a robots file, the same file each time.** It bars every program but five named search and social crawlers. Those sites are closed: Bedford Township, Grosse Ile Township, Huron Charter Township, Milford village, Richland village, Rochester Hills, South Haven and West Bloomfield Township. With Dexter, Saline and Lyon Township, read earlier, 11 Revize sites are closed by their own file.
4. The reader also asked each of the 13 Revize file hosts for its own robots file, once. **Every one bars every program from everything but document files such as PDFs.** So an agenda file kept on a Revize host can be fetched and a page there cannot.
5. Two research passes then read the 31 open sites for their agenda pages. 27 were read. `config/mi_agenda_inventory.csv` now holds **518 bodies of 220 governments**. The rows are research. No independent check has been made and no collector may take a row.

**Four sites were not read, because they have moved to a new address:** Plymouth Charter Township, Van Buren Charter Township, Milford Charter Township and Pontiac. The robots answer above was for the old address. Both passes reported that the new address sends its robots request to the same Revize file that answered 404. The radar's reader has not asked the new addresses itself. One pass tried to open that file with its own tool, against its instructions, and the tool refused before any request was sent. I did not make the request in its place. One request for each of the four would settle it, on the owner's word.

**Where the 220 governing bodies post agendas now**

| Where | Governments |
|---|---|
| Files on the government's own site | 89 |
| Legistar | 1, Ann Arbor |
| CivicPlus products, held until CivicPlus answers the letter | 29: AgendaCenter 15, CivicClerk 9, Municode Meetings 5 |
| Documents On Demand, closed by its robots file | 18 |
| Other outside platforms that are closed | 6: CivicWeb 3, Diligent 2, eCode360 1 |
| Outside platforms not read yet | 5 |
| Revize site closed by its own robots file | 11 |
| Revize site moved to a new address, not read | 4 |
| Own site answered 403 | 9 |
| Own site's robots file names the reader | 8 |
| A script draws the list and it was not read | 9 |
| No agendas online | 25 |
| Minutes only, agendas not found | 2: Lima Township, Hazel Park |
| Site did not answer or no site | 4 |

- **At most 90 of 220 could be read by a collector,** up from 71, before any second read or reading of each site's terms.
- The 19 added: Allen Park, Brownstown Township, Charleston Township, Flat Rock, Galesburg, Grosse Pointe, Grosse Pointe Shores, Richland Township, Riverview, South Rockwood, Sumpter Township, Franklin, Huntington Woods, Orion Township, Oxford village, South Lyon, Springfield Township, Sylvan Lake and Clarkston.
- Of the other eight that were read: Beverly Hills and Birmingham send their governing body's agendas to CivicClerk, Bingham Farms and Wolverine Lake to Documents On Demand, Woodhaven to CivicWeb and Orchard Lake to Diligent. Wakeshma Township posts minutes only. Hazel Park's council agendas were not found in six pages.

**Code:** the inventory now knows a portal on the older `diligent.community` name as Diligent, with a test. Orchard Lake's link uses it.

**Corrected before the rows went in:** five rows. The four moved sites' notes were rewritten to say exactly what was and was not read. Orchard Lake's note was rewritten to say its redirect was reported by the research pass.

**Slips, as the passes reported them**

- One pass tried to open a Revize robots address for Plymouth Township. Its brief said to follow a new host's robots redirect and my message said never to open a Revize host. The tool refused and nothing was sent. The conflict was mine.
- One outside host not on the list was opened: the Galesburg downtown authority's own site. Its robots file was read first and is open. It posts no agendas and has no row.
- Five hosts got six pages, the limit. A few pages were asked twice. Gaps between requests were not timed. One host asks for 20 seconds between requests and the gap cannot be proved.

**Not verified**

- **Which host the agenda files are on, for 12 governments.** Their pages give the file links as relative addresses. The evidence addresses were built against the government's own host and no file was opened. If a page sets its base to a Revize host, the files are there. A PDF is open to the reader on either host.
- Every page was read through the fetch tool's summary, not as raw HTML. Several long pages were read only in their first part, where the newest items sit.
- The planning commission rows for Bingham Farms, Wolverine Lake and Orchard Lake rest on a link for the whole government. No page says the portal carries that body's agendas.
- That the eight robots files and the 404s will stay as they were on the day.

**Bodies noticed and left out:** Birmingham's Shopping District Board, which posts on CivicClerk and is not a body type the inventory lists. Development bodies in Beverly Hills, Franklin, Hazel Park and Riverview that post no agendas.

**Kept for the record:** the eight sites' shared robots file has the SHA-256 hash `32eadb82fa51cea6c899a6f8834aa8ab0ca144437d964b3391d5ce4881dab833`. Eleven of the 13 file hosts share one file, hash `06ca9acdad52936cff2efe1bb2a45c7dc4f505b52dfced87c85717d3338ddfd3`.

**Cost:** 52 requests by the radar's reader. The two research passes ran no web search, made 132 tool calls and used about 418,000 tokens.

**Tests:** 1,169 pass.

## November 23, 2026 — M11: the agenda inventory for all six Michigan counties

**The owner's word:** run the inventory for the other five counties.

**What was done:** eight research passes read the websites of the 191 governments in Allegan, Kalamazoo, Monroe, Oakland and Wayne counties, under a tighter brief than the Washtenaw trial's. `config/mi_agenda_inventory.csv` now holds **478 bodies of 220 governments**. Every government has one governing body. **The rows are research. No independent check has been made and no collector may take a row.**

**Where the 220 governing bodies post agendas**

| Where | Governments |
|---|---|
| Files on the government's own site | 70 |
| Legistar | 1, Ann Arbor |
| CivicPlus products, held until CivicPlus answers the letter | 27: AgendaCenter 15, CivicClerk 7, Municode Meetings 5 |
| Documents On Demand, closed by its robots file | 16 |
| Other outside platforms that are closed | 4: CivicWeb 2, Diligent 1, eCode360 1 |
| Outside platforms not read yet | 5: IQM2, BoardDocs, a Laserfiche portal, a shared folder, a file service |
| Own site on Revize hosting, treated as closed | 42 |
| Own site answered 403 | 9 |
| Own site's robots file names the reader | 8 |
| A script draws the list and it was not read | 9 |
| No agendas online | 24 |
| Minutes only on a closed host, so not known | 1, Lima Township |
| Site did not answer or no site | 4 |

- **At most 71 of 220 could be read by a collector,** before any second read or reading of each site's terms.
- Among them: Wayne County, Dearborn, Novi, Farmington Hills, Auburn Hills, Highland Park and the city of Allegan.
- Detroit's council agendas were not found: a script draws the list. Its planning commission and development authorities were.
- Of the six county boards, one posts on its own site: Wayne. Three use CivicClerk: Washtenaw, Oakland and Monroe. Two sites refused: Allegan and Kalamazoo.

**The Revize question, open for the owner.** On a Revize site the robots file redirects to another host. The research treated that as closed and read nothing: 39 governments. Three more were followed to the file itself and are closed by it: Dexter, Saline and Lyon Township. The robots standard, RFC 9309 section 2.3.1.2, says a reader follows such a redirect and obeys the file it reaches, and the radar's own fetcher does. No Revize robots file has been re-read since.

**Corrected before the rows went in:** 13 rows. Three Livonia rows and three White Lake rows were given the platform their address shows. Six Municode rows were marked inferred. One row that rested on a researcher's memory was dropped.

**Slips, as the passes reported them**

- **Two Municode Meetings hosts were opened and read,** for Lathrup Village and Madison Heights. Another pass read the same vendor's robots file as barring an AI reader. Their rows are marked inferred.
- Three Revize robots redirects were followed to an answer of 404, and those sites were then read: Ortonville, Independence Township and Ecorse. That is what the standard says and not what the brief said.
- One Comstock Township page may have been served from the bare address before that address's robots file was read. It was read next and is open.
- After Allegan County's site refused, later searches for townships carried the county's name. None was about the county's agendas.
- Five hosts got seven requests, counting the robots file, against a limit of about six pages.
- Gaps between requests were not timed in most passes. Some pages were asked a second question from the reader's cache.

**Checked by me and not verified:** I asked for the robots files of the two Municode hosts, once each, to settle which reading is right. Both dropped the connection. I did not retry.

**Cost:** 84 web searches, 917 tool calls and about 1.9 million tokens across the eight passes.

**Not verified**

- Every page was read through a summarizing reader, not as raw HTML.
- No evidence file was opened.
- Body names on closed sites are not confirmed.
- Whether any of the 24 governments that post no agendas post them somewhere the research did not look.
- 1,168 tests pass.

## November 23, 2026 — M11: the Washtenaw County inventory, a one-county trial

**What was done:** a research pass read the websites of the 29 governments in Washtenaw County and recorded where each body posts its agendas. 68 rows are in `config/mi_agenda_inventory.csv`. **They are research. No independent check has been made and no collector may take a row.**

**What it found, by government**

- 14 post agenda files on their own sites: Chelsea, Milan and 12 townships, Saline Township among them.
- 1 uses Legistar: Ann Arbor.
- 4 use CivicPlus products, which are held until CivicPlus answers the letter: Washtenaw County, Ypsilanti, Pittsfield Township and Manchester.
- 5 keep agendas on Documents On Demand, whose robots file bars every program: Ann Arbor Township, Barton Hills, Northfield, Salem and Sharon. Lima Township links only minutes there.
- 4 have sites that are closed to the reader: Dexter and Saline by a robots file, Sylvan by a robots file that names the reader, Scio by a 403 on its robots file.
- **At most 15 of 29 could be read by a collector,** before any second read or reading of each site's terms.

**Corrected before the rows went in:** 17 rows. Ten were renamed to the Documents On Demand platform their address shows. Five that rested on a search excerpt are marked not found. The county's row is marked inferred. The Ann Arbor development authority's row points at the city's Legistar calendar.

**Slips in the research pass, as it reported them**

- **A rendered read of the county's page reached the CivicClerk host before that host's robots file was read.** The file bars a reader of this kind. The host was not opened again and the row is marked inferred.
- After Scio Township's site refused, one web search was run on its agendas. Nothing was opened.
- Searches limited to three closed sites were run and only the result excerpts were used.
- For four townships the robots file was read on the www address and the pages were read there, while the sites write their links without www.
- The gaps between requests were not timed, including the 20 seconds the county's robots file asks for.

**Cost:** 16 web searches, 161 tool calls and 14 minutes.

**Not verified**

- Every page was read through a summarizing reader, not as raw HTML. Dates and links are as it reported them.
- Manchester now calls itself a city. The Census list of 2020 has it as a village and the inventory keeps that name.
- Whether Bridgewater Township still posts agendas: its newest was from August.
- No development body was looked for where a government's agenda host is closed.
- 1,166 tests pass.

## November 23, 2026 — M11 begun: the agenda code reads a second state

**The owner's word:** start milestone M11, Michigan agendas, with Washtenaw, Wayne, Oakland, Monroe, Allegan and Kalamazoo counties.

**Built, tests first**

- `config/mi_places.csv`: every city, village and township in the six counties, from two Census files. 86 cities, 24 villages and 104 townships. With the six county boards that is **220 governments**. Two townships named Salem carry their county in the name.
- The inventory and its checks take a state. Michigan has its own inventory, checks and site terms files. The platforms file is shared. Texas is read when no state is given, and nothing about Texas changed.
- Michigan's kinds of body: county board, city council, township board, village council. A row in a county outside the six is refused.
- The check column `names_texas` is now `names_state`: whether a page is for a place in the inventory's own state.
- The two agenda processors read the state from the source a document was stored under. A Michigan record is placed in a Michigan county and never in a Texas one. A township is named with its kind, "Ann Arbor Charter Township", because a city and a township often share a name.
- Two sources added and **marked manual: `mi_agendas_legistar` and `mi_agendas_own_sites`.** No job reads them. The site lists them as not read.
- 23 tests. 1,165 pass.

**Verified**

- The Census Bureau's robots file was read before the township file was downloaded, once, on November 23.
- With an empty Michigan inventory the collectors' lists of governments they may read are empty for Michigan and unchanged for Texas: 9 Legistar governments.

**Not verified**

- **No Michigan government's website has been read for a collector.** The inventory file has its header and no rows. A one-county research pass, Washtenaw, was running when this was written.
- Whether a Michigan agenda speaks of "economic development" beside a code name as a Texas one does. The rule for code names was written from Texas agendas and Texas law. No Michigan agenda has been read against it.
- No Michigan collector exists. None is written until each site's terms and robots file are read.

## November 23, 2026 — Entering a record by hand

**The owner's decision:** build hand entry as a command that keeps a saved copy and works only for sources the owner marks.

**Built, tests first**

- `python -m pipeline.hand_entry`: a person saves a record as a PDF or a web page and gives its facts. The command checks the facts against the file before anything is stored, then keeps the file with its address, time and hash and makes one signal.
- **It holds a hand-read record to the rules every record meets.** A reason, read from the words of the file with the radar's own terms, or stated in a sentence. A party that shows a company or a public body. A summary that does not say planned, approved or coming unless the file does. A reference that names no party.
- A new setting, `hand_entered`, which only a manual source may carry. **No source is marked.**
- 25 tests. 1,142 pass.

**Verified**

- In the test database: a made-up tax abatement notice that says "data center" was stored with its hash, made one signal on a site named for its company and went to the reviewers' queue at a score of 27. Entered twice, it is one signal.

**Not verified**

- The command against a real record from a real source. None is marked.
- Which sources may be marked. The Texas public notice site's terms bar storing its content at all. Michigan's reply said no agreement is needed when a person reads its pages.

**Not built yet**

- Hosting for the site.

## November 23, 2026 — Built before going online: archive, real runs, email, backups

**The owner's decision:** build everything before putting anything online. Nothing here is switched on.

**Built, tests first**

- **The archive in the hosted project.** `collectors/hosted_archive.py`: one private bucket, each file under its hash, never written over, and checked against its name when read back. A migration makes the bucket with no policy, so only the service key reaches it. The jobs pick their archive from the settings.
- **A switch for real runs.** Every collector workflow is a dry run unless the repository variable `RADAR_LIVE` is the word true. New workflows run processing and the email job, by hand only. No commit can switch a real run on, and no workflow has a schedule.
- **A sender for real email.** `pipeline/email_sender.py` hands a batch to Resend in one request, in plain words, each email with its own unsubscribe link and each batch with a key that stops it going twice. `--send` is refused unless a switch, the provider's key, the site's address and a from address are all set. The settings as they stand cannot send.
- **A backup command and a restore trial.** `scripts/backup.py`. It refuses to write a dump inside the repository.
- 30 tests. 1,117 pass.

**Verified live**

- **The archive, against the storage service's local copy:** a file stored, stored again, read back and a missing file asked for. The service answers a duplicate and a missing file with a 400 whose body carries the real status, and the store reads both forms.
- **The backup, on the history database:** 5,919 documents dumped, restored into a scratch database and counted back whole. The first trial failed, rightly: the sites table needs the map extension, which a bare database lacks. The trial now prepares the scratch database.
- Resend's batch address, its limit of 100 emails a request and its idempotency key, read in its documentation on November 23, 2026. I read the request example, the parameters and the response, not the whole page.

**Not verified**

- **Anything against a hosted service.** No hosted database, storage or email account exists.
- That the storage service of a hosted project answers as its local copy does.
- Whether the bucket's default size limit takes the largest file a collector keeps.

**Not built yet,** when this was written

- A way to enter a record a person read by hand. Built later that day: see the entry above.
- Hosting for the site.

## November 23, 2026 — M10: monitoring, the launch checklist and the runbook

**The radar is not launched.** M10 builds what launch needs and launches nothing.

**Built, tests first**

- `python -m pipeline.health`: monitoring for failed collectors. It reads the run log and gives each watched source one state: ok, failing, blocked, stuck, stale, never run or due by hand. It writes and sends nothing, and ends with an error code when a source needs a person.
- `.github/workflows/monitor.yml` runs it. Started by hand only. A schedule is a launch decision.
- [launch_checklist.md](launch_checklist.md): the owner's decisions, what is not built, the secrets, the steps before the first real run and the first 30 days.
- [runbook.md](runbook.md): what an administrator does each weekday and what to do for each state, a refusal, a correction, a reviewer and an alert.
- 22 tests. 1,087 pass.

**Verified live**

- The monitor run on the history database gave the right states: the own-site run as failing, because two sites refused, and the Comptroller's list as stored by a person today.
- **Two governments are now closed in the config,** which that reading showed was owed: Grey Forest and Meadowlakes keep their agenda files on a host whose robots file bars them. 57 governments' own sites are read, down from 59.
- GitHub's documentation says a failed scheduled run is reported to the account that last changed the schedule. Read November 23, 2026.

**What launch still lacks,** all in the checklist

- A hosted database, and a place for the archive in it. Only a folder on one machine is written.
- Real runs in the workflows, a workflow for processing and any schedule.
- A sender for real email, hosting for the site and a backup.
- Each waits on a decision that section 11 keeps for the owner.

**Not verified**

- The prices of the hosted services on the day.
- That sign-in emails from the hosted project arrive, and within what limits.
- How long an everyday run of each collector takes on GitHub's runners.

## November 23, 2026 — A government's own computers are set aside, and two verdicts changed

**The owner's instructions**

- Change the two passing mentions in the policy group to rejected. The review now stands at **28 confirmed and 30 rejected.**
- Set aside an agenda item about a government's own information technology.

**Built, tests first**

- `config/keywords.yaml`: `own_computers`, two lists. Words that show an item is about a government's own computers, such as co-location, network services and information technology. And words for land or a project, such as abatement, zoning, moratorium and proposed, which always win.
- In both agenda readers the words "data center" make no signal in such an item. Another term in the item still counts, and the signal then opens no site. In a file, the item is taken from one numbered line to the next.
- `RULES_VERSION` is `2026-11-23.2`. The report counts what was set aside.
- 10 tests. 1,065 pass.

**The fourth run of the backtest**

- **32 sites that fit no known project reach the bar, down from 58:** about eight a year.
- **The rule took out 26 of the 28 the owner rejected as a government's own computers, and none the owner confirmed.** No signal tied to a known project was lost. The two hits stand.
- Of the 32 left, the owner's review confirmed 28 and rejected 4.

**Not verified**

- **The rule on agendas it was not written from.** Its words came from the same 58 sites it is measured on. A real project item that uses one of those words and none of the words for land or a project would be set aside, and nobody would see it.

## November 23, 2026 — The owner reviewed the 58 sites: 30 confirmed, 28 rejected

- The owner read a list of the 58 sites that fit no known project and reach the bar of 3, with a link to each record, and gave a verdict for each group.
- **Rejected, 28:** a government's own computers. 22 of them are Harris County and Houston.
- **Confirmed, 30:** 20 rules or discussions on data centers, 5 agendas about a specific project, 3 groups of well reports and 2 ERCOT planning files.
- So at the bar of 3 about half of what reaches a reviewer is noise, seven sites a year in these records.
- **A verdict on the list publishes nothing.** No alert exists until a site is confirmed on the reviewer desk, and the desk has no database yet. The list is not in the repository.
- The first version of the list cut each record's words short. It was rebuilt to show the whole agenda item.
- **Not verified:** each site one at a time. The verdicts were given by group. Two of the 20 policy items are passing mentions and not a rule.
- **Proposed, not built:** a rule that sets aside an agenda item about a government's own information technology.

## November 23, 2026 — A rule on data centers is an alert, and a watch on the mailboxes

**The owner's decisions**

- **A moratorium or a zoning rule on data centers is an alert.** A reviewer confirms it when the record says so. The reviewer's choice on the desk, the reviewer terms and the methodology page now say so. A government buying data center services for its own computers is not an alert.
- **Watch the email for replies to the letters.**

**The watch**

- A scheduled task on the owner's computer checks two mailboxes at 10 and 4 on weekdays and reports any reply. It reads only: it sends nothing, changes nothing and does not say what an answer allows. It runs while the desktop app is open.
- **What the mailboxes show today:** five letters went out on November 23 from the Anti-Corruption Action address, to the Texas Press Association, the PUC, EGLE twice and the Comptroller. No reply to any yet. CivicPlus sent only an automatic acknowledgment on November 21.
- **No sent copy of the TDLR letter was found in any connected mailbox** when the watch was set up. **The owner sent it later that day, at 16:38 UTC,** to the agency's open records address from the Anti-Corruption Action address. The sent copy is in the mailbox and the watch names it.

## November 23, 2026 — Every drafted letter has been sent

The owner said on November 23, 2026 that all the letters have been sent. The mailbox shows five of them went out that day.

| To | About | Answer |
|---|---|---|
| Michigan Public Service Commission | its docket site | Refused on November 20, 2026 |
| Texas Press Association | the statewide public notice site | None yet |
| Public Utility Commission of Texas | Interchange filings | None yet |
| EGLE | pending air permit lists | None yet |
| EGLE | MiEnviro Portal public notices | None yet |
| Texas Comptroller | local development agreement files | None yet |
| CivicPlus | its three agenda platforms | None yet. Sent November 21 |
| FracTracker Alliance | how the tracker data is used | None yet. Sent through its website |
| TDLR | the building registration search | None yet |

**Nothing changes until an answer comes.** Every one of these sources stays as it is marked: no collector reads it. An answer is the owner's to pass on.

## November 23, 2026 — Two letters sent by the owner

- **FracTracker Alliance:** sent through the form on its website. It says how the tracker data has been used and asks whether that use fits FracTracker's mission.
- **TDLR:** sent. It asks whether a slow reader may use the registration search. Until the agency answers, the search is asked nothing.
- No answer to either yet.
- A review list of the 58 sites that fit no known project was made for the owner, with a link to each record. It is not in the repository: nothing on it has been reviewed.

## November 23, 2026 — The Comptroller's list is saved by hand

**The owner's decisions**

- Mark the Comptroller's list of registered data centers manual, and build the command that stores a page a person saved.
- For TDLR registrations, write to the agency first. The letter is drafted and not sent.

**Built, tests first**

- `python -m collectors.by_hand <source-id> <file>` stores a page a person saved in a browser. It makes no request, checks the file with the collector's own parser, and stores it as a run does, marked as saved by hand. A file that is not the page is refused and nothing is stored.
- A new setting in `config/sources.yaml`, `hand_saved`, which only a manual source may carry. The Comptroller's list is `manual`, `blocked` and `hand_saved`. The fetcher refuses it, and its workflow file is removed.
- The collector and its parser stay, with their tests, on the source as it stood on November 19.
- The methodology page lists the source as read and says a person saves it.
- 18 tests. 1,054 pass. The site's type check, tests and build pass in a copy outside iCloud.

**The first page saved by hand**

- The owner saved the page on November 23 and it was stored in the backtest's history database with the new command. The parser read it: 189 registrations, six more large projects than on November 19.
- `backtest/run.py` now reads the newest copy the history holds and falls back on the test copy only when there is none. The backtest's result did not change: two of 73. One record gives no signal because its company was registered after the record's date.
- 1 more test. 1,055 pass.

**Not verified**

- Which browser and save format the owner used. One browser-saved page has been read. Another browser's save may differ.
- No hosted database exists yet. The copy is in the history database on the owner's laptop.

## November 23, 2026 — M9: a name added, the Comptroller refused again, TDLR proposed

**The owner's instructions**

- Add the name Orion Data Center to the list of known projects.
- Give the Comptroller's site a run.
- Propose TDLR building registrations as a source.

**Done**

- **The name is on the SB Energy row in Milam County,** with a note that no source read says in words that the two are one project. The backtest ran a third time. **Two of 73 judged projects now reach the bar before they were public, 77 and 39 days ahead.** Both are Milam County agendas. 58 sites that fit no known project reach the bar. The report and the findings are the third run's.
- **The Comptroller's site refused again,** at 11:46 UTC. One request, for the robots file. Nothing was stored and nothing else was tried. Three refusals that day, about six hours apart. The owner decides whether to mark the source manual.
- **TDLR building registrations are proposed.** [tx_tdlr_building_registrations.md](sources/tx_tdlr_building_registrations.md) is the proposal, and the source is in `config/sources.yaml` as `manual`. Nothing collects it and the site was asked nothing today.
  - 34 of the 128 known projects have a registration as their earliest record, 31 of them in Dallas, Bexar and Harris counties, where agendas showed nothing.
  - For 21 with both dates, the registration came before the first news report in 13 and the same day or after in 8. The median is two days ahead.
  - **The open question:** the search answers only through the page's own script call. **The owner chose to write to the agency first.** A letter to its Public Information Coordinator is drafted and not sent. Until the agency answers, the search is asked nothing.

**Not verified**

- That the Orion Data Center is the SB Energy project.
- Whether the Comptroller's refusal is lasting.
- Whether the TDLR search answers a program at all. It has not been asked anything.

## November 23, 2026 — M9: the owner approved three changes, and the backtest ran again

**The owner's decisions,** after reading the findings of the first run

- **The review threshold is 3, down from 40.** A working number. The scoring file stays marked as a placeholder.
- **An agenda record that says "data center" opens a site,** held by its government and meeting.
- **On Legistar a "Project" code name counts only where the item speaks of economic development negotiations,** as in an agenda file.
- The Comptroller's site is asked once more on a later day.

**Built, tests first**

- `pipeline/cluster.py`: a fourth reason signals are one site, the same meeting's agenda. `pipeline/signals.py` keeps the meeting with an agenda signal that says "data center" and with no other. `pipeline/sites.py` names such a site "Agenda of" its government and meeting.
- The Legistar code-name rule. `RULES_VERSION` is `2026-11-23.1`.
- `config/scoring.yaml`: 3, with what the number means written beside it.
- The database tests that pin how a site is made and queued keep their own bar of 40. Two new ones run at the file's bar.
- 12 tests. 1,036 pass.

**The second run.** [report_tx.md](../backtest/report_tx.md) is now this run's.

- **One of 73 judged projects reaches the bar before it was public, 39 days ahead.** The same Milam County record as before. It now sits on a site a reviewer would see.
- **59 sites that fit no known project reach the bar in four years of records, about 15 a year.** 54 are one meeting's agenda that says "data center". On the first run's rules the count at this bar was 5, which is the number I gave the owner before the change. Nobody has read the 59 as a reviewer would.
- Code-name signals fell from 399 to 93 and their sites from 123 to 35.
- Nothing else moved: 72 of 73 have no signal before their public date.

**Not verified**

- How many of the 59 sites are noise.
- Whether a real closed-session item is missed because its heading sits in an earlier item. In four governments' stored agendas, 66 of 179 code-name items carry the heading themselves.
- No stored signal in any real database carries a meeting yet. Reading documents again only adds signals, so a signal made before today stays off a site.

## November 23, 2026 — M9: the backtest ran. No hit, one early signal, thresholds proposed

**The result.** See [report_tx.md](../backtest/report_tx.md), written by a program, and [findings_tx.md](../backtest/findings_tx.md), written by hand.

- **No known project reaches the review threshold of 40,** before or after it was public. 73 were judged. The highest score any of the 128 reaches is 7.5.
- **One of 73 had a signal before its public date:** Milam County files for the meeting of December 8, 2025, 39 days before the first news report found, or 70 days by one file's own date.
- **The radar as built would not have sent that record to a reviewer.** An agenda signal carries no company, so it sits on no site. The backtest tied it by the project's name in the record's words.
- False alarms in the eleven control counties: none. The history holds no signal there, so this says little.
- **Proposed to the owner, nothing changed:** keep the scoring file marked as a placeholder, lower the review threshold from 40 to 3, give an agenda record a way onto a site, and tighten the "Project" code-name rule on Legistar. The reasons are in the findings.

**The history runs, all ended**

| Source | Stored | Note |
|---|---|---|
| Legistar | 3,625 agendas from 9 governments | No error. I estimated 3,619 |
| Governments' own sites | 1,784 agenda files, dated for 33 governments | **About 1,900 requests against my estimate of 490.** Many pages reach back further than my sample showed. One request a site every five seconds held, 189 files at most from one site |
| ERCOT planning group | 372 files and 61 pages | No error |
| Well reports | 15,986 rows kept | One download |
| Pending air permits | Both lists as they stand | |

- **Two sites refused and were left alone:** Grey Forest and Meadowlakes keep files on a host whose robots file bars them. Eight files failed to download. 22 governments' pages gave no dated file.
- The history database was dumped to the store outside the repository after the last run.

**Built**

- `backtest/history.py`: stored documents read as dated signals. A signal counts from the day its record could be seen, the later bound where that day is not kept. A company counts as listed only from the day its registration took effect.
- It ties a record to a known project by the project's company beside the words "data center", or by a "Project" code name. **This is the backtest's own reason.** The everyday pipeline cannot do it, and the report counts it apart.
- `backtest/report.py` and `backtest/run.py`: the report, written from the harness result. The harness now keeps each project's highest score on any day, and a sweep row says how many sites a reviewer would be sent at each bar.
- **A signal that fits no known project is unreviewed, so the report never names it.** The full listing is written outside the repository.
- 36 tests. 1,024 pass.

**The Comptroller's site refused the collector**

- I ran the everyday collector once to give the history a copy of the registered data center list. The robots file answered 403, twice. Nothing was stored and nothing else was tried.
- The backtest uses the copy saved with the tests on November 19, 2026.
- **The owner said to ask once more on a later day.** See [tx_comptroller_data_centers.md](sources/tx_comptroller_data_centers.md).

**Leads for a person,** from the report's list of 42 records tied to no project

- Milam County, February 24, 2025: an item on a data center at Burlington under a name the list of known projects lacks, 77 days before the SB Energy project's public date. If the owner adds the name, two of 73 had an early signal.
- Milam County, November 18, 2025: a town hall on a proposed data center near Burlington.
- Hillsboro, May 5, 2026: an update on a data center project.
- Three sites that fit no known project carry a company and coordinates, from well reports in Travis and Carson counties. Their names were given to the owner and are not in the repository.

**Not verified**

- The public dates, each the earliest news report found.
- **What the sites held in the past.** A history run reads what a page holds today. Milam County's page holds no agenda dated from mid May through July 2025, the weeks in which the county posted its notice on the SB Energy project. A running collector could have read it. The backtest understates what a running radar would have seen, by an amount it cannot measure.
- The ties a program made between records and projects. One is known to be wrong and is named in the findings.
- Whether the Comptroller's list showed a registration on the day it took effect.
- Abatement notices, commission dockets, stormwater notices and decided air permits: none could be judged.

## November 23, 2026 — M9: history runs started, FracTracker's file taken, two decisions by the owner

**The owner's decisions**

- Go ahead with the history runs and the eleven control counties.
- **A local blog counts as a first report.** The Tom Green County row that rests on one is back at medium.
- **Use FracTracker's data.** The owner gave the spreadsheet's address.

**Built**

- A history setting for four collectors: Legistar, the ERCOT planning group, governments' own agenda pages and the well reports. `python -m collectors.run <source> --history-since 2023-01-01`. Each reads only what an everyday run may read, at the same pace, and skips what is stored.
- `config/counties_tx_control.yaml`: the eleven control counties. The radar does not watch them.
- 14 tests, written first. 988 pass.

**Collected, into a database of its own on the local Postgres and a folder outside the repository and outside iCloud**

- **Well reports:** one download. 15,986 rows kept since January 1, 2023, in the 30 counties and the eleven controls.
- **Pending air permit lists:** both pages as they stand.
- **Still running when this was written:** the ERCOT planning group, governments' own agenda pages and Legistar.
- **A slip of mine.** The runs first wrote to the database the tests use, and 12 database tests failed because they expect it empty. One commit, `64b587d`, was made in that state. I stopped the three runs after 12 minutes, moved the 405 stored documents to a database of their own, checked the copy by count and hash, cleared the first and started the runs again. They skip what is stored. 988 tests pass.

**FracTracker's file**

- One sheet, downloaded once through the spreadsheet's own export address: 1,733 rows, 230 in Texas, 98 in the 30 counties. It is kept outside this repository. See [us_fractracker.md](sources/us_fractracker.md).
- A program matched 72 of the 98 to 51 of the list's 126 projects. **Nine proposed or approved projects matched nothing** and went to a research pass.
- **The research pass:** four of the nine are already in the list under another name, one is outside the 30 counties, one is older than the 2023 cut and one is marketed land. **Two were added, with no date and rated low:** land on State Highway 16 in Bexar County and a 217 acre tract at Venus whose county is unsettled. The list now holds 128 projects. 79 have a public date.
- A lead for a person: the City of Venus record that would date the Venus tract is on a meeting platform that is not cleared.
- **FracTracker lists nothing in the eleven control counties** and nothing in the five test counties where the list has none.
- It gives no date a project became public.

**Not verified**

- The machine's matches. No person has checked them.
- That the spreadsheet is the one the map links. I did not open the map's link.
- Whether FracTracker judges this use to fit its mission. Its terms leave that to FracTracker. The letter drafted for it has not been sent by me.

## November 22, 2026 — M9: what a history run would ask for, and control counties proposed

The owner said to push. The six commits are on `main` and the checks passed. **No backtest has run and no history has been collected.** This entry is a proposal for the owner.

**What a history run back to January 1, 2023 would ask for**

| Feed | Requests | Basis | How far back it reaches |
|---|---|---|---|
| Legistar agendas, 9 governments | about 3,630 | Counted: 10 list requests on November 22 | All of 2023 on. 3,619 meetings have a published agenda |
| ERCOT planning group | about 630 | Counted: 57 meetings on four index pages. Files estimated at 10 a meeting, from four meetings read: 3, 9, 17 and 12 | All of 2023 on |
| Agendas on governments' own sites, 60 pages | about 490 | **Estimated** from 11 saved pages: 7 older dated files a page | **Under a year on most pages.** The oldest link on the saved pages runs from October 2025 to September 2026 |
| Well reports | 1 | One 145 MB file, as now | All of 2023 on, by the day a report was submitted |
| Pending air permit lists | 2 | The two pages, as now | Only applications still pending today. A decided one is gone |

About 4,750 requests, one every 5 seconds to a host. Legistar is about five hours and the rest under two.

**What the history cannot give, whatever is run**

- **54 of the 73 projects made public since 2023 sit where the radar may read no agenda at all.** Eight more have only their county's page. Seven have a city page with under a year on it. Four have Legistar's full history: two in Dallas and two under Harris County.
- No abatement notices, no transmission filings, no stormwater notices and no local agreements. Each of those sources is held or closed.
- Air permits decided before today are gone from the lists.
- **So the hit rate will mostly measure what the radar is allowed to read,** not how well it scores. The report has to say which misses are misses of coverage.

**Control counties proposed: eleven**

Lamb, Comanche, Eastland, Lampasas, Mills, Wood, Titus, Colorado, Lavaca, Runnels and Coleman.

- Twenty candidates were screened by one pass with two or three web searches each: `backtest/control_counties_screen.csv`. A sign of a project was found in five: Gray, Deaf Smith, Young, Leon and Jackson. Four were unclear: Hockley, Montague, Lee and Cass. Nothing was found for the eleven.
- **"Nothing found" is weak.** It means two or three searches returned nothing. It rests on search excerpts.
- Two carry a note. A Lampasas paper reports farm groups' worry about data centers, with the county judge saying he knew of no interest in the county. Colorado County's paper shows the county watching Austin County's moratorium. No project turned up in either. Neither page was opened.
- **They are all small.** Their 2024 populations run from 4,563 to 48,742, by the Census estimates. None mirrors Lubbock, Potter, Tom Green or the five urban counties.
- **They would be judged on the three statewide feeds only:** air permits, well reports and planning group files. No agenda inventory exists for them. A false alarm rate from them says nothing about agenda signals.

**The state building registrations, read by me**

- The robots file leaves the registration pages open and closes every `.csv` address, which closes the search's spreadsheet export to a program. The policy page says nothing about automated access and lets state information be copied if it does not mislead. See [tx_tdlr_building_registrations.md](sources/tx_tdlr_building_registrations.md).
- It is a proposal only. Nothing collects it. Six of the nine records that came after the news are registrations, so it is likely a late signal.

**Verified live**

- Legistar's meeting lists, 10 requests, none refused. ERCOT's index and its 2023, 2024 and 2025 pages and four meeting pages, 8 requests. Nothing was stored.
- The Census population estimates file, one request after its robots file. The Census API now asks for a key, so it was not used.
- The registration site: three requests.

**Not verified**

- The count for governments' own sites. It is known only after the 60 pages are read.
- How many ERCOT files there are, and how large.
- Whether any control county is clean.
- The day each older record could first be seen. Legistar gives the day an agenda was published. For a file on a government's own site the meeting day is the safe choice.

## November 22, 2026 — M9: the list of known projects, all 30 counties

The owner said to carry on with news research for the other 27 counties. The list is built. **No backtest has been run.**

**Built**

- `backtest/known_projects_tx.csv`: **126 projects in 25 of the 30 counties**, one row per site, each with the earliest news report found and the earliest record found. Dallas 28, Bexar 15, Ellis 10, Hood 10, Harris 9.
- `backtest/projects.py` loads it and refuses a row that breaks a rule. **The public date is the first news report or company announcement,** as the owner settled. A government record is a signal.
- `backtest/known_projects_hosts.csv`: the robots result for each of the 62 sites checked. A test refuses a read that rests on a closed site.
- `backtest/known_projects.md`: the method, what was left out, and what is not verified.
- 33 tests on the loader and the list. 974 pass in all.

**How it was researched**

- One pass per county, two for Dallas, each with the collectors' rules in its brief. Then a second read by separate passes, which opened the cited pages again and ran no searches.
- **Second read of the 27 later counties:** 85 cited lines held. 11 showed a gap in wording or place and dropped to low. 2 could not be opened. No date differed.
- All 28 state building registrations sent for a second read held.

**What it holds**

- **79 projects have a public date,** 73 of them in 2023 or later. **47 have none.**
- No known project was found in Burnet, Erath, Falls, San Saba or Wise. In each, the county's agendas or the local papers were closed to the pass.
- For 18 projects both a government record and the first report were read on the page. The record came first in 9 and after in 9. That is not a lead time: see the method file.
- **34 records are state building registrations** at the Texas Department of Licensing and Regulation. The plan does not list that source.

**A rule tightened, and reads set aside**

- **A robots file that bars an AI reader acting for a user, under any name, closes the site.** Some passes read such sites because the file did not name their reader. I first said that was allowed, then changed my view: a file that bars every AI reader it knew by name is saying no.
- I then read the robots file of every site a read rests on, once each, with the project's user agent.
- **22 cited lines in 17 projects are set aside.** Thirteen are from the three-county trial, which never checked robots files. Two of the trial's longest leads lose their first report.
- Rows left out: two rumors, two tracts with no data center announced, two marketed sites, one designation, one crypto site no source calls a data center and one undated tracker listing.

**The owner's decisions, November 22**

- The public date is the first news report or company announcement.
- The owner agreed to FracTracker's terms. Nothing has been taken. A letter is drafted for `info@fractracker.org`, not sent.

**Not verified**

- Whether any county's list is complete. Officials in five counties spoke of more projects than were found.
- The first report for 47 projects.
- The day a government record could first be seen online.
- The terms of the state registration site. A second-read pass saw its robots file and one policy page. I have not read them.

**Leads for a person**

- Parker County: a state air registration from about April 2025, said to name a data center, about 13 months before the first news.
- Hopkins County: a city letter of intent of December 19, 2024, six months before the company's release.
- Seagoville rezoned 138 acres for a data center on November 18, 2024, with no news report found.

**Still needed for the backtest**

- Control counties. The five test counties with no known project are close to controls, and are weak ones.
- History: one-time runs back to 2023 for each collector, with request counts brought to the owner first.
- A loader for historical signals and the report writer.

**Cost.** About 8 million tokens and about 850 web searches. Firecrawl credits spent: under 10.

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
