# State of Michigan website terms

- Applies to: `mi_mpsc_dockets`, `mi_egle_notices`, `mi_egle_air_pending`
- Page: https://www.michigan.gov/policies
- Checked: November 19, 2026
- Result: **automated access is restricted. These three feeds are manual until the owner decides.**

## What the terms say

The policies page for Michigan.gov has users agree not to access the website "through any automated means". It names scripts, web crawlers and screen scrapers as examples, and it tells users to follow any robots.txt file on the site.

The same paragraph allows an exception only under "a separate, written agreement with the State of Michigan". The page also says each department or agency may have additional policies of its own.

## Robots rules

- `https://www.michigan.gov/robots.txt` answered our plain request with 403 "Access Denied". We did not retry and did not try another way in.
- `https://www.deq.state.mi.us/robots.txt` answered 404. That host publishes no robots file.

## What this means for each feed

| Feed | Host | Status |
|---|---|---|
| `mi_mpsc_dockets` | mi-psc.my.site.com and michigan.gov/mpsc | Restricted. The docket site adopts these policies and the news releases sit on Michigan.gov. |
| `mi_egle_notices` | michigan.gov/egle and the MiEnviro Portal | Restricted. |
| `mi_egle_air_pending` | deq.state.mi.us | Treated as restricted. It is a State of Michigan host on another domain. Whether the Michigan.gov terms cover it was not confirmed, so we assume they do. |

## What was not checked

- The Public Service Commission's E-Dockets system was checked later the same day. It has no terms of its own and links to this policies page. See [mi_mpsc_dockets.md](mi_mpsc_dockets.md).
- Whether EGLE or the commission publishes an official feed, API, email list or bulk download for these records.
- `michiganbusiness.org` (Strategic Fund board packets). It is a different site with its own terms.

## Options for the owner

1. Ask the State for written permission. The terms name that path.
2. Have a person check these three pages by hand on a schedule. The pages are public and free to read.
3. Look for official subscriptions or feeds, such as docket email notices, and use those.
4. Rely on other Michigan signals first, such as Strategic Fund packets and zoning notices, if their terms allow.

No collector will be written for these feeds until one of these is chosen.
