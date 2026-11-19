# Comptroller franchise tax account lookup

- Source id: `tx_comptroller_entity_lookup`
- Search page: https://comptroller.texas.gov/taxes/franchise/account-status/search
- Checked: November 19, 2026
- Result: **allowed through the official routes below.** Manual until a collector is written.

## What was verified

- **The lookup moved.** The old `mycpa.cpa.state.tx.us/coa/` addresses redirect to the page above.
- **Robots rules.** The search page and detail pages are under `/taxes/`, which `comptroller.texas.gov/robots.txt` allows. The address the page's own script queries, under `/data-search/`, is **closed** by the `Disallow: /*/` rule. A collector must not call it.
- **Reuse.** The Comptroller's privacy and security policy calls information on its sites public domain. See `tx_comptroller_data_centers.md`.
- **The search page.** No captcha, no login and no notice about automated queries. It tells visitors that API access to the data is available.
- **Official API.** Documented at https://api-doc.comptroller.texas.gov/public-data/. It has a search by taxpayer id, name or file number and a detail call with account and officer data. Both need an API key, obtained by registering.
- **Bulk file.** "Active Franchise Taxpayers" on the state open data portal, https://data.texas.gov/d/9cir-efmm, published by the Comptroller, last updated November 14, 2026. It has taxpayer number, name, address, Secretary of State file number and status codes. The portal's robots rules set a crawl delay of 1 second and leave dataset downloads open.

## Which route to use

1. **Bulk file first.** No key, one download, and it answers "does this LLC exist and since when" for most cases.
2. **Official API for detail,** such as officers, when a site is under review. This needs an API key. Registering for a key creates an account and a secret, so the owner does it. See BUILD_PLAN.md section 11.
3. Never the `/data-search/` address.

## What was not verified

- The terms shown when registering for an API key, and the API's rate or monthly limits. The documentation gives no numbers.
- Any terms of use for the open data portal. The dataset's license field is empty.
- The dataset download itself.

## Privacy

The detail call returns officer names. Officers of an LLC acting for the company are in scope. Do not publish them unless a reviewer confirms they are relevant to the alert.
