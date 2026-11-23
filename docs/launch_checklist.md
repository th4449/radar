# Launch checklist

BUILD_PLAN.md milestone M10. Written November 23, 2026. **The radar is not launched.** Nothing runs on a schedule, no database is hosted, no email is sent and the site is not public.

Each line says who does it. **Owner** means a decision or an action that section 11 of the build plan keeps for the owner. **Session** means work a build session can do once the owner has said yes to what it rests on.

## 1. Decisions that wait for the owner

Nothing below starts without a yes to its line.

- [ ] **Owner.** Create the hosted Supabase project. It is a paid resource or can become one. The price was not checked for this list: check it against the 60 dollar a month target on the day.
- [ ] **Owner.** Add the secrets as GitHub and Supabase secrets. None goes in the repository. See part 3.
- [ ] **Owner.** Turn on real email, and choose the provider's tier. The email job only does dry runs today.
- [ ] **Owner.** Make the site public: host it and point a name at it. Buying a domain or changing DNS is the owner's.
- [ ] **Owner.** Create the first administrator by hand, outside the repository. There is no self-service path to that role.
- [ ] **Owner.** Approve each reviewer. Never automated.
- [ ] **Owner.** Put the collectors, processing and the monitor on a schedule.
- [ ] **Owner.** Adopt the reviewer terms at `/review/terms/`. They are a draft.
- [ ] **Owner.** Keep or change the review threshold of 3 and one confirmation for an alert. Both are working numbers. See [findings_tx.md](../backtest/findings_tx.md).

## 2. Not built yet

**The radar cannot launch until these exist.** Each is session work that waits on a decision above.

- [ ] **A place for the archive in the hosted project.** Only a folder on one machine is written (`LocalArchive`). Every stored file, its hash and its path depend on this.
- [ ] **Real runs in the workflows.** Every collector workflow is a dry run that keeps nothing, started by hand. A real run needs the database and the archive.
- [ ] **A workflow for processing.** `python -m pipeline.process` turns stored documents into signals and sites. Nothing runs it.
- [ ] **A sender for real email.** The email job is given no sender and cannot send. `site_url` in `config/email.yaml` is empty.
- [ ] **Hosting for the site.** The build is static and passes in CI. It is deployed nowhere.
- [ ] **A backup of the hosted database,** and one trial of restoring it.
- [ ] **A way to enter a record a person read by hand,** for the sources that stay manual. Only a whole saved page can be stored today, for one source.

## 3. Secrets and settings

| Name | Where | For | Exists |
|---|---|---|---|
| `RADAR_CONTACT` | GitHub variable, not a secret | The public contact address in every request | Check before the first real run |
| `RADAR_DATABASE_URL` | GitHub secret | Collectors, processing and the monitor write and read the database | No |
| Archive credentials | GitHub secret | Storing each file | No. Waits on how the archive is hosted |
| `PUBLIC_SUPABASE_URL`, `PUBLIC_SUPABASE_ANON_KEY` | Site build | Sent to every browser. The anonymous key reads one view | No |
| Email provider key | Supabase or GitHub secret | Sending alerts | No |
| `ANTHROPIC_API_KEY`, with `RADAR_TRIAGE` and `RADAR_TRIAGE_MONTHLY_CAP_USD` | GitHub secret and variables | Optional model triage. Off by default. The radar works without it | No |

## 4. Before the first real run

- [ ] **Session.** Apply every migration in `db/migrations/` to the hosted database, in order.
- [ ] **Session.** Run the policy tests against the hosted database or a copy of it. They are the proof that a pending reviewer cannot confirm, a user cannot approve themselves and the anonymous key reads only `public_alerts`.
- [ ] **Owner.** Check the settings table: one confirmation required, and **the approval gate on**. While it is on, only an administrator can publish an alert.
- [ ] **Session.** Run each collector once by hand as a real run, one at a time, and read its log. A refusal ends that source: record it and do not run it again.
- [ ] **Owner.** Save the Comptroller's list by hand and store it. See [runbook.md](runbook.md).
- [ ] **Session.** Run processing once and read what it made. Expect sites in the reviewers' queue: at the bar of 3, a record that says "data center" reaches a reviewer by itself.
- [ ] **Session.** Run the monitor. Every watched source should be `ok`.

## 5. Sources on the day

Read from `config/sources.yaml` and the notes in `docs/sources/` on November 23, 2026.

- **Read by a job:** Legistar agendas for 9 governments, agenda files on 57 governments' own sites, the ERCOT planning group, ERCOT large load totals, TCEQ pending air permits and state well reports.
- **Saved by a person:** the Comptroller's list of registered data centers, once a month.
- **Waiting on an answer to a letter:** Texas public notices, the PUC, the Comptroller's local agreements, TDLR registrations, CivicPlus agenda platforms and two Michigan feeds. No collector reads them. FracTracker has been asked whether its data may be used as it is.
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
