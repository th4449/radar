# Administrator runbook

BUILD_PLAN.md milestone M10. Written November 23, 2026, before launch. It says what an administrator does and what to do when something breaks. Administrators are Dekleptocracy Alliance staff.

**Three rules sit above everything here.**

1. **Never work around a refusal.** A site that refuses the radar's reader is left alone: no retry, no other tool, no other connection. A person reads the source note and decides.
2. **Never say a data center is planned unless a record says so.** An alert restates public records.
3. **Never write a private person's name** in a note, an alert or a correction's answer. Companies and officials acting in office are in scope.

## Each weekday

1. **Read the monitor.** See "The monitor" below. It runs each day at 14:30 UTC. A failed run arrives as an email from GitHub to the account that set the schedule.
2. **Open the queue** at `/review/queue/`. A site is there because its score reached the review bar or a reviewer opened it.
3. **Read corrections** on the administrator's desk at `/review/admin/`. Anyone can send one, with no account.
4. **During the first 30 days, approve alerts.** While the approval gate is on, only an administrator can publish.

## The schedule

On a schedule since November 27, 2026, on the owner's go-ahead. Times are UTC. In Texas that is between about 4 and 9:30 in the morning.

| Job | When |
|---|---|
| Legistar agendas | Every day, 10:10 |
| Agendas on governments' own sites | Every day, 10:25 |
| ERCOT planning group | Mondays, 10:40 |
| TCEQ pending air permits | Mondays, 10:50 |
| State well reports | Mondays, 11:05 |
| ERCOT large load reports | The 2nd of the month, 11:15 |
| QPQ study page | The 2nd of the month, 11:25 |
| Processing | Every day, 13:20 |
| The monitor | Every day, 14:30 |

- **Each job can still be started by hand** from the Actions tab.
- **Not on a schedule:** the email job, until real email is decided, and the policy tests on the hosted database, which run on the owner's word each time.
- **The Comptroller's list is still saved by hand** once a month. The monitor says when it is due.

**Four rules of GitHub's that matter here,** from its page on events that trigger workflows, read November 27, 2026.

- A scheduled job can start late when GitHub is busy, and it says a job can even be dropped. The monitor's `stale` state is the net for that.
- **In a public repository, scheduled jobs are switched off when the repository has had no activity for 60 days.** A commit counts. If the radar goes quiet for two months, every schedule stops, the monitor's too, and nobody is told. Re-enable them on the Actions tab.
- A scheduled job runs the newest commit on the main branch.
- **GitHub emails the person who last changed a schedule line** when a scheduled job fails. Today that is the account that pushed them. The monitor fails on purpose when a source needs a person, so that email is how the radar asks for help.

## The monitor

```
uv run python -m pipeline.health
```

It needs `DATABASE_URL`. It reads the run log, changes nothing and sends nothing. It ends with an error code when any source needs a person. Each watched source has one state.

| State | What it means | What to do |
|---|---|---|
| `ok` | Read cleanly and recently enough | Nothing |
| `failing` | The newest run failed or finished with errors | Read the error on the desk under Recent runs. See "A collector fails" |
| `blocked` | The site refused | **Do not run it again.** See "A site refuses" |
| `stuck` | A run started hours ago and never finished | Look at the run in GitHub Actions. Start it once more by hand only if nothing refused |
| `stale` | No clean run within its cadence | Find out why no run started: a schedule that is off, or a workflow that was disabled |
| `never_run` | No run is logged | Expected before launch. After launch, the workflow has never run |
| `due_by_hand` | A page a person saves is older than its cadence | See "The Comptroller's list" |

A source held for a permission is not watched. Nothing is supposed to run.

## A collector fails

- **The layout changed.** The run stops and keeps the page that surprised it. Nothing is guessed. A person compares the stored page with the test copy in `tests/fixtures/`, and a build session changes the parser with a new test.
- **Some addresses failed.** A run that reads many sites ends as partial when a link is dead. Read the failed addresses in the run's detail. A government that moved its agendas needs its row in `config/tx_agenda_inventory.csv` checked again by an independent read.
- **A file could not be read.** A scan with no text is stored unread and counted. Nobody has read it. Open it yourself if the meeting matters.

## A site refuses

A 403, a robots file that bars the path or cannot be read, a captcha or a login page.

1. **Stop.** The run already has. Do not start it again.
2. Write what happened in the source's note in `docs/sources/`: the day, the address, the answer.
3. For one government of many, set its row in `config/tx_agenda_site_terms.csv` to `refused` or `robots_bar`. The collector then leaves it alone and the other governments are still read.
4. For a whole source, the owner decides: wait, write to the agency, or mark the source `manual`. Only the owner marks a source `hand_saved`.

## The Comptroller's list

The Comptroller's site refused the reader on November 23, 2026. A person saves the page once a month.

1. Open https://comptroller.texas.gov/taxes/data-centers/data-center-lists.php in a browser.
2. Save it as HTML only: "Page Source" in Safari, "Webpage, HTML Only" in Chrome. Not a web archive and not a PDF.
3. Store it in the hosted project, with the name the browser gave the file:

```
uv run python scripts/store_by_hand_hosted.py tx_comptroller_data_centers "<the saved file>"
```

The command makes no request to the Comptroller's site. It checks the file first and refuses one that is not the page, before it asks for anything. **Never use it on a file a program fetched.**

**What it asks for and why.** Storing needs the hosted database's address and the archive's key, and neither is on any person's machine.

- It asks for **the database password** at a prompt that shows nothing. That is the password set in the Supabase dashboard. The command does not choose or change it.
- It reads **the archive's key** from Supabase's own tool, so the person must be signed in to it (`supabase login`) and the checkout must be linked to the project (`supabase link`).
- It prints neither, writes neither to a file and leaves neither in the shell.

`python -m collectors.by_hand`, the command underneath, is for a database whose settings are already in the shell, such as the local one.

## Entering a record by hand

For a source a program may not read and a person may. **Only a source the owner has marked `hand_entered` takes a record.** None is marked yet.

1. Open the record at its source and save it as a PDF or a web page.
2. Run the command on the saved file:

```
uv run python -m pipeline.hand_entry <source-id> "<the saved file>" \
    --url "<the record's own address>" --date 2026-11-28 --county Hood \
    --type abatement_notice --reference "Notice 4471" \
    --summary "Hood County published a notice of a hearing on ..." \
    --party "Example Hosting LLC"
```

- **The summary restates the record.** It may not say planned, approved or coming unless the file says so.
- **`--party` is a company or a public body.** A name that may be a person is refused. Leave a person out.
- `--reference` is the record's own number or title, never a party's name. It is what the public sees beside the link.
- If the file uses none of the radar's terms, add `--reason` with one sentence on why the record is a signal.
- The command checks all of this before it stores anything. It keeps the file with its hash and makes one signal. A reviewer still confirms it before anything is public.

## Reviewers

- **Applications** are on the administrator's desk. Approve only a person the organization knows. An administrator cannot approve themselves, and the database refuses it.
- **Suspend** a reviewer on the same screen. A suspended reviewer can do nothing.
- **Reverse a decision** on the site's page, with a reason. The reason is kept. If a published alert then lacks the confirmations it needs, the database takes it down.
- Every action is in the audit log at the foot of the desk.

## What a reviewer confirms

- A record that points at a site: a company, a place, a project name.
- **A rule on data centers that a government is weighing:** a moratorium, a zoning change. The owner decided this on November 23, 2026.
- Not a government buying data center services for its own computers. The radar sets most of those aside. Reject one that gets through.
- Not a passing mention.
- The reviewer opens each source record first and ticks that they did.

## Publishing an alert

On a site's page an administrator writes a headline and a body, saves a draft and publishes.

- The database publishes only when the site has the confirmations it needs and no standing rejection.
- **The body restates the records.** Say which government, which meeting or filing, and what the record says. Use the word signal. Do not say a data center is planned, coming or approved unless the record says it in those words.
- A site held by a meeting's agenda says where the record is, not where a project is. Say so if the record gives no place.
- To take an alert down, unpublish it on the same form. The public page then says there is no alert at that address.

## Corrections

1. Read it on the desk. The sender may be the company, the government or a neighbor.
2. Open the alert and its records again.
3. If the alert is wrong, unpublish it or fix the text, and reverse the decision behind it with the reason.
4. Mark the correction handled with a short note. The note names no private person.

## Sites that may be the same place

The desk lists signals that fit two sites. The radar never merges sites by itself. An administrator merges them on the site's page, with a note.

## Settings

The desk shows the two settings: confirmations needed for an alert, and the approval gate. **The owner changes them in the database, not from the desk.** Every change is logged.

## Letters and permissions

Eighteen letters are out, listed in `docs/progress.md`. Nine went on November 25, 2026. Five ask a Michigan government whose terms are held for permission: Otsego Township, Berlin Charter Township, Plymouth Charter Township, Rockwood and Ross Township. Three tell a city the owner cleared that its agendas are read, and ask it to say if it objects: Dearborn, Keego Harbor and Southgate. One more asks Revize about the 24 sites whose files its robots rule bars. The owner sent Ross Township's, Keego Harbor's and Revize's. Nothing drafted is unsent. A source waiting on an answer is not read by a job. When an answer comes, the owner decides what it allows, and a build session records it in the source's note before any collector changes.

## Page numbers on files stored before November 24, 2026

`python -m pipeline.reread` notes which pages of each stored PDF hold no words, so a reviewer is shown the file's own page numbers. It needs `DATABASE_URL` and the archive. It says what it would do and writes nothing unless given `--write`. It opens a file only when the stored text has fewer pieces than the file has pages, and it leaves any file that reads differently today. It fetches nothing from any site. Dump the database first. A file stored since that day carries the note already, so the job has nothing to do on it.

## The email job

It does a dry run unless the owner has unlocked sending. A dry run shows on the desk what would be sent, in counts. It prints no address. Real sending needs three things only the owner sets: the variable `RADAR_EMAIL_LIVE`, the provider's key, and the site's address and the from address in `config/email.yaml`.

## What an administrator never does

- Run a collector again after a refusal.
- Approve, suspend or remove a reviewer by any path but the desk, or let a job do it.
- Share an unpublished site, signal or note outside the desk.
- Put a key, a subscriber's address or reviewer data in the repository. It is public.
- Change the Texas county list or the scoring thresholds. Those are the owner's.

## Backups

```
uv run python scripts/backup.py dump <a folder outside the repository>
uv run python scripts/backup.py trial <the dump file>
```

- `dump` needs `DATABASE_URL`. It writes one file and, beside it, the number of rows in each table that day.
- `trial` needs `TRIAL_DATABASE_URL`, a Postgres server **on this computer**. It restores the dump into a scratch database, counts every table against the dump's numbers, and drops the scratch database. Run it after every dump you mean to rely on.
- **A dump holds subscribers' addresses and reviewers' records.** The command refuses to write one inside the repository. Never upload one as a workflow artifact.
- A trial restores the radar's own tables. The sign-in accounts belong to the hosted service and are not in the dump: ask the service how it backs them up.

## When an email run fails

- The run stops at the batch the provider refused. What went before it is recorded as sent, so nobody gets it twice.
- The error names the provider's answer, never a person or the key. Read it on the desk under Alert emails.
- Start the same run again once the cause is fixed. A batch sent again within a day is taken once by the provider.

## Not written yet

- Restoring the sign-in accounts. They belong to the hosted service.
- Michigan. No Michigan source is read. The agenda inventory, its second reads and each site's terms are on file. Two agenda collectors are written and tested on saved pages, `collectors/mi/legistar.py` and `collectors/mi/agenda_pages.py`. Neither is on the list a job can run. To start one on the owner's word: change the source's method to `http`, add the collector to the list in `collectors/run.py` and add its workflow file.
