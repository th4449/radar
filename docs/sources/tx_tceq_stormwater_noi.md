# TCEQ construction stormwater notices of intent

- Source id: `tx_tceq_stormwater_noi`
- Checked: November 19, 2026
- Result: **blocked for automated access. Manual only.**

## What was verified

- `https://www2.tceq.texas.gov/robots.txt` is two lines: `User-agent: *` and `Disallow: /`. Every path on the host is closed to every crawler. Read twice.
- `https://www14.tceq.texas.gov/robots.txt` has the same two lines.

## What was not verified

- The search page itself. Search results from other sites cite `www2.tceq.texas.gov/wq_dpa/index.cfm` as the "Water Quality General Permits & Registration Search". Because robots.txt closes the host, we did not request it.
- Whether TCEQ offers a bulk file of general permit authorizations or will provide one on request.
- `www3.tceq.texas.gov`, which hosts the STEERS filing system. Not checked.

## How we use it

A reviewer may run the search in a browser when checking a site that already has other signals. This is a late signal, close to earthwork, so it confirms more than it warns.

An option for the owner: ask TCEQ for the notices of intent as a periodic public information request.
