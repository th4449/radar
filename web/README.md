# Reviewer app

The reviewer desk, and from milestone M7 the public site. Astro builds static pages. The screens
that show data are Preact components that read the database in the browser with the visitor's
own session.

**What a person may see or do is decided by the database, never by this code.** A screen that
hides a button is a courtesy. The policy or trigger behind it is the rule, and each one has a
test under `tests/db/`.

## Pages

| Address | Who | What |
|---|---|---|
| `/review/` | anyone | Sign in by emailed link. Apply to review. See where an application stands. |
| `/review/terms/` | anyone | The reviewer terms. A draft until the organization adopts them. |
| `/review/queue/` | approved reviewers | Sites by status, highest score first. |
| `/review/site/?id=` | approved reviewers | One site: why it scores what it does, every signal with its reason and source, the decisions so far, and the review form. Administrators also get the alert form and the merge form. |
| `/review/admin/` | administrators | Applications and reviewers, sites flagged as the same place, records held back, recent runs and the audit log. |

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
uv run python scripts/dev_seed.py
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
every site into the review queue by hand, so there is something to look at. It refuses any
database that is not on this computer.

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
  URL, and `/review/` in its list of allowed redirect addresses.
- Hosting for the built site.
- The reviewer terms, adopted or replaced.
