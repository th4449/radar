# The site

The public site and the reviewer desk. Astro builds static pages. The screens that show data
are Preact components that read the database in the browser with the visitor's own session.

**What a person may see or do is decided by the database, never by this code.** A screen that
hides a button is a courtesy. The policy or trigger behind it is the rule, and each one has a
test under `tests/db/`.

## Public pages

A visitor with no account reads one thing from the database: the view `public_alerts`, which
holds confirmed, published alerts and the records behind them.

| Address | What |
|---|---|
| `/` | Every confirmed alert on a map and in a list. |
| `/tx/`, `/mi/` | One state: its alerts and its counties. |
| `/tx/hood/` and the like | One county. A page for each of the 30 Texas counties and 83 Michigan counties. |
| `/alert/?id=` | One alert: the word confirmed, the date, each record with its own number, a link to the agency, the time the radar read it and the fingerprint of its copy. A corrections link. |
| `/methodology/` | How the radar works, which sources it reads and which it does not. The lists come from `config/`. |
| `/corrections/` | Anyone may send a correction. No account. Only administrators read it. |
| `/subscribe/` | Sign up for alerts: states, optional counties, each alert or a weekly digest. |
| `/account/` | A subscriber confirms, changes what they get or stops. |
| `/unsubscribe/?token=` | The link in every email. It needs no sign-in. |

The states, counties and sources the pages name are a copy of `config/`, in
`src/lib/places.json`. After changing `config/`, run:

```bash
uv run python scripts/export_web_data.py
```

A test fails if the copy is out of date.

### Double opt in

1. The person picks states on `/subscribe/` and gives an address. The choices wait in their
   browser.
2. The sign-in service emails a link to that address. Opening it lands on `/account/`, which
   saves the choices and calls `confirm_subscription()`.

The database function checks for itself that the address was proved by an emailed link. No
alert is due to anyone whose subscription is not confirmed. A person who is already signed in
saves their choices and then presses a confirm button.

### The map

MapLibre draws it with OpenFreeMap tiles. See `docs/services/openfreemap.md`. An alert with no
point on record is in the list and not on the map.

## Reviewer desk

| Address | Who | What |
|---|---|---|
| `/review/` | anyone | Sign in by emailed link. Apply to review. See where an application stands. |
| `/review/terms/` | anyone | The reviewer terms. A draft until the organization adopts them. |
| `/review/queue/` | approved reviewers | Sites by status, highest score first. |
| `/review/site/?id=` | approved reviewers | One site: why it scores what it does, every signal with its reason and source, the decisions so far, and the review form. Administrators also get the alert form and the merge form. |
| `/review/admin/` | administrators | Applications and reviewers, corrections from readers, sites flagged as the same place, records held back, recent runs, the email job's dry runs and the audit log. |

## Run it on your own machine

Needs Node 24, Docker and the Supabase CLI.

```bash
supabase start
```

```bash
cp web/.env.example web/.env
```

Fill `web/.env` from `supabase status`: the API URL and the anonymous key. Then:

```bash
uv run python scripts/dev_seed.py --publish-sample
```

```bash
npm --prefix web install
```

```bash
npm --prefix web run dev
```

Open http://127.0.0.1:4321/review/. Sign-in emails go to the local test inbox at
http://127.0.0.1:55324, not to anyone's mailbox.

`scripts/dev_seed.py` stores the saved test fixtures as documents, runs processing and moves
every site into the review queue by hand, so there is something to look at. With
`--publish-sample` it also publishes two alerts marked as samples, so the public pages have
something to show. It refuses any database that is not on this computer.

The database tests expect an empty database. Run `supabase db reset --local` before them if
you have seeded.

## The first administrator

There is no way to become an administrator through the app. The owner makes the first one by
hand, in SQL, as the database owner:

1. The person signs in once and sends an application, so their account and reviewer row exist.
2. The owner runs, with that person's email:

```sql
update public.reviewers
set status = 'approved', role = 'admin'
where user_id = (select id from auth.users where email = '<their email>');
```

The change is written to the audit log as made by the owner. After that, administrators approve
and suspend reviewers from `/review/admin/`. Only the owner changes a role.

## Checks

```bash
npm --prefix web run check
```

```bash
npm --prefix web test
```

```bash
npm --prefix web run build
```

## Before this runs anywhere but a laptop

Each of these is the owner's decision under section 11 of the build plan.

- A hosted Supabase project, and its address and anonymous key in the build settings.
- Real sign-in email. The hosted project needs an email sender, the site's address as its Site
  URL, and `/review/` and `/account/` in its list of allowed redirect addresses. The same
  emailed link signs a reviewer in and confirms a subscriber, so its wording must fit both.
- Hosting for the built site, and taking `noindex` out of `src/layouts/Base.astro`. Until
  then every page asks search engines to stay away.
- The reviewer terms, adopted or replaced. The methodology page, read and approved.
- The organization's postal address and the site's address in `config/email.yaml`. The email
  job only does dry runs and cannot send without both.
