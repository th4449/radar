# ERCOT Regional Planning Group project files

- Source ids: `tx_ercot_rpg` and `tx_ercot_large_load`
- Index page: https://www.ercot.com/committees/other/rpg
- Checked: November 19, 2026
- Result: **allowed.** Manual until the first fixtures are saved and a collector is written in M2.

## What was verified

- **Robots rules.** `https://www.ercot.com/robots.txt` has one group for all agents and no crawl delay. It does not close `/files/docs/`, `/committees/` or `/calendar/`. It does close `/meetings`, `/widgets`, `/ical`, `/misdownload` and several `/content/` folders. A collector must stay out of those.
- **Terms.** The Website User Agreement at https://www.ercot.com/help/terms, last updated July 20, 2023, says public contents may be used, reproduced and redistributed if they are not modified and notices are kept, and that raw data may be reused in compilations and analyses without the notices.
- **Limit on use.** The same agreement prohibits use that "negatively affects the performance of this website" and lets ERCOT block access. It says nothing about robots, crawlers or scraping.
- **Where the files are.** The index page lists each meeting as a link under `/calendar/`, for example `/calendar/03172026-RPG-Meeting`. Meeting pages list their documents under `/files/docs/<year>/<month>/<day>/`.

## What was not verified

- No meeting page and no file under `/files/docs/` has been fetched by us.
- ERCOT's "Legal Policies and Notices" page at `/about/legal` was not read.
- No index page for large load reports was found. Those reports sit under `/files/docs/` like the others. The large load pages seen in the site navigation were not read.
- The ERCOT public API and data product pages. Whether they cover these files is unknown.

## Notes for the collector

- Walk from the index page to meeting pages to files. Do not use the calendar feed under `/ical` or the committee widget under `/widgets`. Robots rules close both.
- ERCOT's own limit is site performance. Keep to one request every 5 seconds or slower and fetch each file once.
- ERCOT runs an email list for the group. A reviewer can subscribe as a cross-check.
- In September 2026 ERCOT said it was weighing whether to keep reviewing large load projects in this process. The feed may thin out.
