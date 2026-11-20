# TCEQ pending air permit applications

- Source id: `tx_tceq_air_pending_legacy`. The new portal is `tx_tceq_air_pending`, with its own note.
- Start page: https://www.tceq.texas.gov/permitting/air/airpermit-applications-notices
- Checked: November 19, 2026

## The feed moved in August 2026

The start page says that from August 31, 2026 the Air Permits Division publishes pending applications in the TCEQ Permit Search Portal. The older static lists on `www.tceq.texas.gov` cover applications that were complete before that date. So there are two sources.

## Legacy lists on www.tceq.texas.gov: allowed

- **Robots rules.** `https://www.tceq.texas.gov/robots.txt` closes the site search and a few named paths. It does not close `/permitting/` or `/assets/`. A comment in the file says robots may access all areas already open to anonymous users. No crawl delay.
- **Reuse.** The linking policy says site content is considered public domain unless noted. The logo is excepted. TCEQ asks for acknowledgment.
- **Blocking.** The public access policy says TCEQ logs traffic and blocks activity that looks malicious or that threatens availability. Nothing on the policy pages mentions robots, crawlers or scraping.
- **Pages.** The start page links to `nsr-pending-permits.html` and `titlev-pending-permits.html` under `/assets/public/permitting/air/reports/applications/`. We have not fetched them.

Use: mostly the backtest in milestone M9, since these lists stop at August 2026.

## Permit Search Portal

Read in a browser on November 19, 2026. See [tx_tceq_air_pending.md](tx_tceq_air_pending.md).

## Other

- TCEQ offers email updates through GovDelivery. Whether a list covers pending air applications was not checked.
- The governor's September 21, 2026 directive paused permits for data center projects. How that changes what these lists show is unknown.
- The TCEQ privacy policy page was requested and returned nothing relevant to automated access. We did not read it line by line.
