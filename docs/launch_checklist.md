# Launch checklist

BUILD_PLAN.md milestone M10. Written November 23, 2026. **The radar is not launched.** Nothing runs on a schedule, no email is sent and the site is not public. A hosted database exists since November 25, 2026. It is empty, and no job can reach it until the owner adds its address as a secret. Since November 26, 2026, the switch `RADAR_LIVE` is true and the archive's key is set, both on the owner's word. A real run still cannot start: it stops before it asks any site for anything, because the database's address is not set.

Each line says who does it. **Owner** means a decision or an action that section 11 of the build plan keeps for the owner. **Session** means work a build session can do once the owner has said yes to what it rests on.

## 1. Decisions that wait for the owner

Nothing below starts without a yes to its line.

- [x] **Owner.** Create the hosted Supabase project. The owner said yes on November 25, 2026, to the price Supabase quoted that day: 10 dollars a month in the owner's organization, which is on the Pro plan. A session created it, named `radar`, in the us-east-1 region.
- [ ] **Owner.** Add the secrets as GitHub and Supabase secrets. None goes in the repository. See part 3. `RADAR_ARCHIVE_KEY` was added on November 26, 2026. `RADAR_DATABASE_URL` is not: it holds the database's password, which only the owner can set or read.
- [ ] **Owner.** Turn on real email, and choose the provider's tier. The email job only does dry runs today.
- [ ] **Owner.** Make the site public: host it and point a name at it. Buying a domain or changing DNS is the owner's. The owner said on November 26, 2026, that the site will be at `standuptocorruption.org/radar`. It is not there yet.
- [ ] **Owner.** Create the first administrator by hand, outside the repository. There is no self-service path to that role.
- [ ] **Owner.** Approve each reviewer. Never automated.
- [ ] **Owner.** Put the collectors, processing and the monitor on a schedule.
- [ ] **Owner.** Adopt the reviewer terms at `/review/terms/`. They are a draft.
- [ ] **Owner.** Keep or change the review threshold of 3 and one confirmation for an alert. Both are working numbers. See [findings_tx.md](../backtest/findings_tx.md).

## 2. Built, and waiting for the hosted project

The owner said on November 23, 2026 to build everything before putting anything online. These were built that day. **None has run against a hosted service.** The hosted database of November 25, 2026 holds the schema and no row. Each is switched on by a setting only the owner can make.

- [x] **A place for the archive in the hosted project.** One private bucket in the project's storage, made by a migration. Tried against the storage service's local copy. `collectors/hosted_archive.py`.
- [x] **Real runs in the workflows.** Every collector workflow is a dry run unless the repository variable `RADAR_LIVE` is the word true. No commit can switch it.
- [x] **A workflow for processing,** started by hand, and only when `RADAR_LIVE` is true.
- [x] **A sender for real email,** behind three locks: the variable `RADAR_EMAIL_LIVE`, the secret `RESEND_API_KEY`, and the site's address and the from address in `config/email.yaml`. `pipeline/email_sender.py`. Not run against the provider.
- [x] **A backup command and a restore trial.** `scripts/backup.py`. Tried on the history database on November 23, 2026: 5,919 documents were dumped, restored into a scratch database and counted back whole. Not tried on a hosted database.

- [x] **A way to enter a record a person read by hand.** `python -m pipeline.hand_entry` takes the record's saved file and its facts, keeps the file with its hash and makes one signal. **No source is marked for it.** See part 2b.

## 2a. Not built yet

- [ ] **Hosting for the site.** The build is static and passes in CI. It is deployed nowhere. The owner has named its address: `standuptocorruption.org/radar`.
- [ ] **A build that works under `/radar`.** Today the site assumes it sits at the root of a domain: 39 links in `web/src` start at `/`, the sign-in emails send a person back to `/account/` and `/review/`, and the build sets no base path. Under `/radar` every one of those would leave the radar. The hosted project's sign-in settings also need the public address before a sign-in link works.

## 2b. Sources a person may enter by hand

- [ ] **Owner.** Mark each source a person may read and enter, with `hand_entered: true` in `config/sources.yaml`. None is marked.
- Entering by hand is not a way around a site's terms. **A source whose terms bar storing its content stays unmarked.** The Texas public notice site's terms bar putting its content in any database or archive.
- The State of Michigan's reply of November 20, 2026 said no agreement is needed to use its pages when a person reads them. Its three feeds are the likeliest to mark: the commission's dockets and the two EGLE feeds. The owner decides.

## 3. Secrets and settings

| Name | Where | For | Exists |
|---|---|---|---|
| `RADAR_CONTACT` | GitHub variable, not a secret | The public contact address in every request | **Yes.** Set November 25, 2026, on the owner's word |
| `RADAR_LIVE` | GitHub variable | The word true switches the workflows from dry runs to real runs. **The owner's switch** | **Yes, and it is true.** Set November 26, 2026, on the owner's word. A workflow started now is a real run |
| `RADAR_DATABASE_URL` | GitHub secret | Collectors, processing, the email job and the monitor write and read the database | No |
| `RADAR_ARCHIVE_URL` | GitHub variable | The hosted project's address, for the archive | **Yes.** Set November 25, 2026, on the owner's word |
| `RADAR_ARCHIVE_KEY` | GitHub secret | The project's service key, which alone reads and writes the archive's bucket | **Yes.** Added November 26, 2026, on the owner's word. It is the project's older `service_role` key. It went from Supabase's tool straight into GitHub and was never shown or written to a file. Supabase says it is retiring this kind of key in early 2027: replace it before then with a secret key from the project's API key settings |
| `PUBLIC_SUPABASE_URL`, `PUBLIC_SUPABASE_ANON_KEY` | Site build | Sent to every browser. The anonymous key reads one view | No |
| `RADAR_EMAIL_LIVE` | GitHub variable | The word true lets the email job send. **The owner's switch** | No |
| `RESEND_API_KEY` | GitHub secret | Sending alerts | No |
| `site_url`, `from_address` | `config/email.yaml` | The links in every email, and the address they are from. The provider sends only from a domain the owner has proved | Not set |
| `ANTHROPIC_API_KEY`, with `RADAR_TRIAGE` and `RADAR_TRIAGE_MONTHLY_CAP_USD` | GitHub secret and variables | Optional model triage. Off by default. The radar works without it | No |

## 4. Before the first real run

- [x] **Session.** Apply every migration in `db/migrations/` to the hosted database, in order. Done November 25, 2026 with `supabase db push`: all 14, the ledger under the files' own numbers. A dump of the hosted schema is the same as the local one's, line for line.
- [ ] **Session.** Run the policy tests against the hosted database or a copy of it. They are the proof that a pending reviewer cannot confirm, a user cannot approve themselves and the anonymous key reads only `public_alerts`. **Not run on the hosted database:** they need its address, which is a secret, and they write test rows. They pass on the local database, whose schema is the same. Asked with the public key on November 25, 2026, the hosted API gave `public_alerts` and refused every table tried.
- [ ] **Owner.** Check the settings table: one confirmation required, and **the approval gate on**. Read on November 25, 2026: one confirmation, the gate on. While it is on, only an administrator can publish an alert.
- [ ] **Session.** Run each collector once by hand as a real run, one at a time, and read its log. A refusal ends that source: record it and do not run it again.
- [ ] **Owner.** Save the Comptroller's list by hand and store it. See [runbook.md](runbook.md).
- [ ] **Session.** Run processing once and read what it made. Expect sites in the reviewers' queue: at the bar of 3, a record that says "data center" reaches a reviewer by itself.
- [ ] **Session.** Run the monitor. Every watched source should be `ok`.

## 5. Sources on the day

Read from `config/sources.yaml` and the notes in `docs/sources/` on November 23, 2026.

- **Read by a job:** Legistar agendas for 9 governments, agenda files on 57 governments' own sites, the ERCOT planning group, ERCOT large load totals, TCEQ pending air permits and state well reports. Since November 25, 2026 also the QPQ Tracker's study page, once a month, for its list of payers.
- **Saved by a person:** the Comptroller's list of registered data centers, once a month.
- **Waiting on an answer to a letter:** Texas public notices, the PUC, the Comptroller's local agreements, TDLR registrations, CivicPlus agenda platforms, two Michigan feeds and, since November 25, 2026, five Michigan governments whose terms are held and Revize, for 24 Michigan sites. No collector reads them. FracTracker has been asked whether its data may be used as it is.
- **Refused:** the Michigan Public Service Commission.
- **No Michigan source is read.** The site says so.

## 6. Launch day

- [ ] **Owner.** Give the go-ahead for each of: the schedules, real email, the public site.
- [ ] **Session.** Add the schedule lines to the workflows, at each source's cadence in `config/sources.yaml`. The account that adds them is the one GitHub emails when a scheduled run fails.
- [ ] **Session.** Schedule the monitor once a day, after the collectors.
- [ ] **Owner.** Send one real alert email to yourself first. Check the unsubscribe link and the postal address.
- [ ] **Owner.** Open the public site signed out. It should show confirmed alerts and nothing else.

## 7. The first 30 days

- [ ] **Owner.** Approve each alert before it goes public. The gate does this in the database.
- [ ] **Owner.** Read the monitor's result each weekday. See the runbook for what each state asks of you.
- [ ] **Owner.** After 30 days, decide whether to lift the gate. It is one setting, which the owner changes in the database. The administrator's desk shows it and the change is logged.

## Not verified for this list

- **Prices.** The Supabase, email and hosting prices were not checked on the day this was written.
- **That the sign-in emails will arrive.** Reviewers and subscribers sign in by an emailed link that the hosted project sends. Its limits were not checked.
- **That GitHub's free minutes cover the schedules.** The own-site agenda run took three and a half hours for four years of history. An everyday run is far shorter and was not timed.
- Whether any source that answered a job in November 2026 still does on launch day. The Comptroller's site stopped in four days.
