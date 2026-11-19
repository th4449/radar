# Data Center Early Warning Radar

A public early warning system that tells communities a data center may be coming before it is announced.

Scheduled collectors pull public records. A pipeline turns them into dated signals tied to a site. A scoring engine flags clusters. Reviewers approved by the organization confirm each alert against the source record. Confirmed alerts appear on a public map and go by email to people who signed up for that state.

No single record proves a data center is coming. The product is the cluster, the human check and the link back to the source.

Built by Anti-Corruption Action and Dekleptocracy Alliance. The specification is [BUILD_PLAN.md](BUILD_PLAN.md). Progress is in [docs/progress.md](docs/progress.md).

## Status

Under construction. No collector runs on a schedule yet and no alert has been published.

## Run the tests

You need [uv](https://docs.astral.sh/uv/), Docker and the [Supabase CLI](https://supabase.com/docs/guides/local-development).

```bash
uv sync
supabase db start
uv run pytest
```

`supabase db start` runs a local Postgres with the same roles the hosted database uses. The policy tests in `tests/db` need it. They are skipped with a clear message when it is not running, and CI fails if they are skipped.

## Rules for contributors

- Public records only. Every stored document keeps its URL, retrieval time and SHA-256 hash.
- Read a source's terms of use and robots rules before writing a collector, and write what you found in `docs/sources`. Never work around a block, a captcha or a login.
- Collector tests run against saved fixtures, never the live site.
- Never commit secrets, reviewer data or subscriber data.
- Use the language of signals. Never state that a data center is planned unless a source says so.

## License

Code is under the [MIT License](LICENSE). Data from third parties keeps its own terms, noted in `docs/sources`.
