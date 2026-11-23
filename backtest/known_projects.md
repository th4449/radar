# Known projects: how the list is made

`known_projects_tx.csv` is the backtest's list of known data center projects in the Texas test counties. It is built from news reports and public records only, with no use of FracTracker. `backtest/projects.py` loads it and refuses a row that breaks a rule.

The first three counties were a trial on November 22, 2026: Hood, Hill and Milam, 23 projects. The owner then said to carry on with the other 27 the same way.

**The date a project became public is its `news_date`:** the first news report or company announcement. The owner settled that on November 22, 2026. A government record is a signal, never the public date.

## How it was made

- One research pass per county searched news sites, trade press, company releases and government pages, and looked for the earliest dated report that calls each project a data center.
- A second read then opened nine of the cited sources again. Every date held.
- Bitcoin mines are listed only where a source calls them a data center. The `crypto` column marks them.
- No private individual is named. Companies, their LLCs and officials acting in office are.

## The columns that carry the dates

| Column | Meaning |
|---|---|
| `record_date` | The earliest dated public record or report found that calls the project a data center, of any kind |
| `record_kind` | What that is: a county notice, a state permit review, a company release, a news story, a petition |
| `news_date` | The earliest news report or company announcement found |
| `record_read`, `news_read` | `second_read` opened twice. `first_read` opened by the research pass only. `not_opened` known from a headline, an excerpt or a secondary source. `set_aside` see below. `none_found` |

## What it shows, and what it does not

- **For 10 of the 23, a government record or a petition names the data center before the first news report found.** Two are county notices of tax abatement hearings in Milam County, 4 and 39 days ahead. One is a state air permit review for a site in Hill County, 162 days ahead.
- **This is not a measured lead time.** A news date here is the earliest report found, not the earliest that exists. Two local papers post little online and one refused requests.
- It bears on what "the date it became public" should mean. If a county's own notice counts as public, the radar can at best tie it, because that notice is one of the records the radar reads.

## What was read against a block, and is set aside

The first pass was not told to stay off restricted hosts. Two things followed.

- Three Hood County minutes files were fetched through a tool that switched to a stealth proxy by itself. That county's document host bars every program in its robots file.
- Three pages of one newspaper were read before the pass learned the site blocks the crawler it was using.

Nothing that rests on those six pages is used here. Two Hood County projects have no usable first record for that reason, and a person needs to date them. Later passes must use a plain connection, stay off the hosts in `config/tx_agenda_platforms.csv` marked restricted, and stop at a refusal.

## Not verified

- Whether any list is complete. Hill County's judge told a reporter in May 2026 that at least eight projects were in the works. Six were found.
- The first report for seven Hood County projects. The local paper could not be searched.
- The day a government record could first be seen online. Minutes and permit reviews carry the day they were made.
- Whether two Hill County entries, Project Aquila and the C.R. 3106 project, are one project.
- Street addresses and coordinates for most projects. Two have coordinates, both of a power plant.

## Cost

Each county took one research pass of 95 to 113 tool calls and 11 to 16 minutes.
