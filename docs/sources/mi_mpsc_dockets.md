# Michigan Public Service Commission dockets

- Source id: `mi_mpsc_dockets`
- Site: https://mi-psc.my.site.com/s/ (E-Dockets)
- Also: news releases at https://www.michigan.gov/mpsc/commission/news-releases
- Checked: November 19, 2026
- Result: **restricted. The feed stays manual.** The docket site's robots file allows everything, but the site has no terms of its own and sends readers to the State of Michigan policies page, which bars automated access without a written agreement.

## What was verified

- **Robots rules.** `https://mi-psc.my.site.com/robots.txt` answered 200. It is the default file for this hosting platform. It allows every path for every agent except a password reset page, sets no crawl delay and lists a sitemap.
- **Terms.** Neither the home page nor the help page carries terms of use. The footer on both reads "Copyright 2026 State of Michigan" and has one policy link, "Policies", which goes to https://www.michigan.gov/som/footer/policies. That page has the same paragraph as the one in [mi_state_of_michigan_terms.md](mi_state_of_michigan_terms.md): no access by automated means, with scripts, web crawlers and screen scrapers named, unless a separate written agreement with the State allows it. It also bars copying or republishing content without written permission, unless the law provides otherwise.
- **Scope of those terms.** The policies page speaks of Michigan.gov throughout. It has no sentence that names sites on other domains. The docket site is on another domain, but it is a State of Michigan site and it offers that page as its policies. We read the terms as covering it.
- **What the site offers without an account.** A list of cases sorted by open date, a case page for each docket, a list of filings, a hearings calendar and a help page. The home page says that commenting on a case and subscribing to filing notices do not need an account.
- **Contact.** The help page gives the Executive Business Section, 517-284-8090, LARA-MPSC-edockets@michigan.gov.
- **The news releases** sit on Michigan.gov and are covered by the same terms.

## Why this is restricted

The robots file and the terms point in different directions. The terms are the stricter rule, and they tell users to follow both. A robots file that the hosting platform installs by default does not show that the State agreed to automated access. The only stated way to automate this feed is a written agreement with the State.

## What a person can do by hand

- Open the case list once a week and read the new cases. On the day of this check the newest cases included two transmission line certificate applications and a request for a rule on measuring large electric loads. These are the case types the plan looks for.
- Subscribe to filing notices on the case pages of known data center dockets. This follows cases we already know. It does not find new ones.

## Notes for any later collector

- The site is a JavaScript application. The case list does not arrive as plain HTML, so a simple page request would not be enough even with permission.
- The case list includes complaint cases opened by private individuals, shown by household name. Those names must not be stored in fixtures or published. Any collector or manual entry form takes utility and company cases only.

## Options for the owner

1. Ask the commission for a written agreement, using the contact above. This is the path the terms name.
2. Have a reviewer read the case list by hand each week and subscribe to notices on known dockets. No permission is needed.
3. Both: start the hand check now and send the request.

## Not verified

- Whether the commission or the State grants written agreements for this kind of use, and who signs one.
- The sign-up step for filing notices and any terms shown there. No form was submitted.
- The case and filing page layouts, the sitemap and the archived orders search on `adms.apps.lara.state.mi.us`, which is a third host with its own rules.
- An older contact address, mpscedockets@michigan.gov, seen in search results. The help page address above is the one to use.
