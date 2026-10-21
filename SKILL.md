---
name: client-report
description: Generates a client-facing report from PEAK as a self-contained print-ready HTML page. For one site: a quarterly building performance review with the analytics overview, operational impact, equipment health and indoor environment snapshots, sustainability ratings, monthly trends, alerts resolved with the actions leaderboard and key wins, and equipment run hours, asking which sections to include. For a client company or several sites: a monthly portfolio leaderboard for the last complete month, with site and team leaderboards, the open P1-2 actions by site and by assignee, equipment health and thermal comfort by site, key wins and sustainability ratings, with every section that has data. Use whenever the user runs /client-report or asks for a client report, a quarterly or building performance review, a portfolio leaderboard, or a site or portfolio performance report from PEAK. Do not auto-trigger on general PEAK questions or ticket workflows.
---

# Client Report

Two reports from one engine. [Which report](#which-report) decides which one a request gets.

- **Single-site report**: a quarterly building performance review for one PEAK site, the sections below
- **Portfolio leaderboard report**: a monthly leaderboard across a client's sites for the last complete month, sent each month. Page one holds the masthead, the portfolio scorecards and a three-board site leaderboard led by each leader's building photo, and page two a team leaderboard of the companies and people doing the work. The open P1-2 actions follow, the sites and people holding the most, then ranked by-site detail, key wins and sustainability ratings. Its sections are under `references/portfolio-leaderboard/`, per [Portfolio sections](#portfolio-sections), and its windows per [Portfolio windows](#portfolio-windows)

The single-site report is a quarterly building performance review for one PEAK site: a self-contained A4 print-first HTML page the partner hands to a facilities manager. The reader chooses which sections it carries, and that choice decides what you fetch and what the page shows. A section that is out should cost nothing.

Every figure, row, series, link, date line and methodology note comes from the section scripts. Your part is the PEAK calls and the key wins. Layout belongs to `scripts/fill_report.py`, which draws every table and chart from the bundle, and to `scripts/fill_portfolio.py` for the portfolio report, so a change to how something looks is a change to those scripts or to `DESIGN.md`, never to a filled file.

## Which report

Resolve the name before anything else, and before the section question.

- Call `search_sites(keyword:"<name>")` and `search_clients(client_name:"%<name>%")` together, and, for a name with punctuation or more than one word, `search_clients` again with the punctuation removed and `%` between its words. A site matches only at a match score of 0.9 or more; a weaker hit is never used on its own, only offered as an option. A client matches when its name is the name given, ignoring case and punctuation
- **A site matches and no client does**: the single-site report
- **A client matches and no site does**: the portfolio report over the client's active sites, from `search_sites(client_ids:[<id>], limit:80)`, paged. A client with one active site gets the single-site report for that site instead, and `report.py plan` prints its commands
- **A client with no active site** is never built: say so, and offer the clients with similar names that hold sites, as below
- **A site and a client both match**: ask once, with one `AskUserQuestion` call, header "Report": "<name> is both a PEAK site and a client. Which report?" The options are "<site name> (site)", the single-site report, and "<client name> portfolio (N sites)", N counting the sites with `is_active` true in the client's `search_sites(client_ids:[<id>], limit:80)` pages. Fetch those pages before asking; they are the `sites.json` pages if the portfolio is chosen
- **Neither matches**: ask with one `AskUserQuestion` call, header "Report", up to four options: the closest clients, each "<client name> portfolio (N sites)" with N counted the same way, then the weaker site hits, each "<site name> (site)". Nothing coming back at all: say so and ask for the site or client name
- **Several sites named**: the portfolio report over exactly those sites. Title it with the client they share: read each site's client ids with `platform.sites` selecting `site_id` and `clients`, keep the ids every site carries, and take the one with the fewest active sites, from `search_sites(client_ids:[<id>], limit:1)` and its `pagination.total`. Skip a client holding more than ten times as many active sites as were named: that is a platform-wide grouping, not the sites' owner. Its name comes off `search_clients(client_name:"%", limit:200)`, paged. Where no shared client remains, use the name the user gave the group, else "Portfolio"
- The words "portfolio", "client" or "all sites for" point to the portfolio report
- A logo file the user supplies, as an attachment or a path, goes to `--client-logo`. Never search PEAK for a client logo, never ask for one, and never pass a logo from this skill or a brand overlay, which `plan` refuses
- More than about 50 active sites: offer to narrow it by state before fetching, with one `AskUserQuestion` call, header "Scope": "<Client> has N active sites, so the report runs long, a hundred or more PEAK calls. Build it for every site, or one state?" The options are "All N sites", then the three states with the most sites, each with its count; any other state comes through the tool's own Other. A state chosen keeps its sites through `--site-ids`
- State the resolved report, its title and its scope in one line in chat, "Portfolio report: 12 sites for <Client>", naming any other clients the search returned so the user can redirect, then go on. `report.py plan` keeps only the active sites in the pages it is given

## Build order

Work in one directory, `report/` below.

1. **Resolve the site and the sections**: [Section selection](#section-selection-single-site). Call `search_sites(keyword:"<site>", include_working_hours:true)` and `who_am_i` together, and save the `search_sites` response as `report/site.json`. Nothing else is fetched before the sections settle.
   - **Portfolio**: save the client's `search_sites` pages as `report/sites.json`, then `report/sites-2.json` and on as it pages, or the one `search_sites(site_ids:[...])` response for sites named one by one, and call `who_am_i`. The portfolio needs no working hours and asks no section question
2. **Plan**: `python3 scripts/report.py plan report --site report/site.json --author "<who_am_i user_name>" --sections <names>`. It fixes the quarter from today in site time, a legacy zone name such as `US/Eastern` read as the zone it links to, and prints every call the sections need, each with the file under `report/peak/` its response is saved as.
   - **Portfolio**: `python3 scripts/report.py plan report --sites report/sites.json [report/sites-2.json ...] --client "<name>" --author "<who_am_i user_name>"`, adding `--client-logo <file>` for a supplied logo and `--site-ids <id> ...` to keep only some of the saved sites; an id not in the pages is named and left out. It fixes the leaderboard month from the issue date, the earliest local date across the sites, per [Portfolio windows](#portfolio-windows), and splits each call across the sites a tool takes at once. Every PEAK date filter reads in each site's own time zone, so each site is bounded on its own calendar
3. **Fetch**: make every printed call in one parallel batch, exactly as printed. A portfolio plan can print a hundred calls: send those in parallel batches of about twenty. A call that fails with a 5xx or a timeout is made again exactly as printed, since the gateway often clears; if it keeps failing, stop and say which call and what it returned. A dropped or expired PEAK connection is not the call's fault: once the server is back, make the unsaved calls again exactly as printed, and `report.py next` lists which those are. If it does not come back, say so and stop; everything saved so far keeps. Save each response the plan lists to save as its file: an offloaded one by copying the file you were handed, an inline one by writing it to its file exactly as returned, one file per response. Those responses hold counts, scores, ids and type, level, company or assignee names only. The plan lists the key win candidate pulls apart: read those where they come back and never save them, since they carry what people wrote on the tickets. Then `python3 scripts/report.py next report`, and make whatever it prints the same way until it says there are no more calls. `next` first reads every saved response back and stops on one that does not parse, holds more or fewer rows than its pagination says, or carries a site outside the report: save that one again from the tool's output. `python3 scripts/report.py verify report` runs the same check on its own.
4. **Bundle**: `python3 scripts/report.py bundle report` writes every figure into `report/data.json`, and prints anything to say in chat at hand-over, then the next step.
5. **Write**: with Actions and key wins in, choose the wins from the two candidate pulls by `references/single-site/actions-and-wins/key-wins.md` and [Writing the narrative](#writing-the-narrative), and write `report/wins.json`; `next` then prints the impact and photo calls for them. Once those are saved, run `python3 references/single-site/actions-and-wins/scripts/key_wins.py photos report` straight away, since the photo links lapse twenty minutes after the call, then `next` again for the level call. Look at the one numbered contact sheet it makes per win, and add your picks to `wins.json`. Every other reference is what its script already did; read it only to answer a question it raises.
   - **Portfolio**: the candidates are read in two passes, by `references/portfolio-leaderboard/actions-and-wins/key-wins.md`: shortlist up to 25 from the candidate pulls into `report/shortlist.json`, read the shortlist in full from the one pull `next` prints, then write `report/wins.json`. The photos step is `python3 references/portfolio-leaderboard/actions-and-wins/scripts/key_wins.py photos report`
6. **Fill and check**: `python3 scripts/report.py fill report` fills the report, saves every photo tile as it prints, and runs the check. Look at the tiles. Then say in chat whatever it lists, name the sections left out, and hand over the file.

## Section selection (single-site)

Ask before fetching anything. The masthead and [Analytics overview](#analytics-overview) always render. The four sections below are the reader's choice, and each owns a set of parts that come and go together: its operational impact rows, its own section, its monthly trend, their links and its notes-band items.

Ask with one `AskUserQuestion` call and one multi-select question, header "Sections": "Which sections should the report cover from last quarter?" Four options is the tool's limit, and four is the whole list. Describe each by what it adds:

| Choice                | `--sections` name    | Folder under `references/single-site/` | Adds                                                                                                                                       |
| --------------------- | -------------------- | -------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| Equipment health      | `equipment-health`   | `equipment-health/`        | the equipment health score, automated checks and labor cost avoided rows; health by equipment type; the score and checks trends            |
| Indoor environment    | `indoor-environment` | `indoor-environment/`      | the thermal comfort row, comfort by level, the six month comfort trend                                                                     |
| Actions and key wins  | `actions-and-wins`   | `actions-and-wins/`        | the faults resolved row with verified recovery, six months of raised vs resolved, who closed the work, and the key wins: repairs made plus live work the owner should see |
| Equipment run hours   | `run-hours`          | `run-hours/`               | when each unit of plant ran across the latest full Monday-to-Sunday week, against the site's working hours                                |

Each folder holds the section's reference and a `scripts/` folder with its arithmetic. Actions and key wins is one choice with two references, `alerts-resolved.md` and `key-wins.md`, because the two answer the same question from either end and share their pulls. `references/single-site/overview/` is the part every report carries.

**Rules:**

- Everything is included by default. A dismissed prompt, an unanswered question, or an invocation naming only a site gets the full report
- Skip the prompt when the invocation already names the sections ("/client-report Skyline Tower: equipment health and key wins only") and state the resolved list in your reply instead
- Resolve the list before the first PEAK call. A section that is out is never fetched
- [Operational impact](#operational-impact) and the [Notes band](#notes-band) are frames around rows and items the sections own, so they render only when a section that owns one is in. The scaffold builds it that way
- Never leave behind an empty section, a header with no content, a link to a section that is out, or a note explaining a number the report no longer shows. The scripts handle the parts they know about; check the wins yourself
- Three things can come up empty after the fetch, and only the fetch can tell: Actions and key wins when nothing was resolved in the window, Key wins alone when no win qualifies, and run hours when no plant carries a sensor that shows it running. The scripts leave the section out and print why; say so in chat, not on the page
- Where what survives is the masthead and the analytics overview alone, say so before handing the file over rather than shipping it as a review

### Automatic sections

| Section | `--sections` name | Folder under `references/single-site/` | Adds |
| --- | --- | --- | --- |
| Sustainability ratings | `sustainability-ratings` | `sustainability-ratings/` | a card per NABERS energy, indoor environment and water rating, current or expired, and each one's rating history |

Never offered in the prompt and never asked about. `report.py plan` adds it to every report, so its one call is always in the main batch, and its script leaves it out when PEAK holds no current rating for the site. Say nothing about it in chat, whether it is in or out.

### Portfolio sections

The portfolio report never asks which sections to include. Every section is planned and fetched, and each renders when PEAK returns data for it and is left out otherwise. Report order runs down this table, after the masthead and scorecard strip.

| Section | Folder under `references/portfolio-leaderboard/` | Renders when |
| --- | --- | --- |
| Masthead and scorecard strip | `overview/` | always |
| Site leaderboard for the leaderboard month | `site-leaderboard/` | at least one of its three boards has data |
| Team leaderboard for the leaderboard month | `team-leaderboard/` | at least one of its two boards has data |
| Open P1-2 actions | `actions-and-wins/`, `open-actions.md` | any priority 1 or 2 action is open now |
| Equipment health by site | `equipment-health/` | any site returned an equipment health score in the quarter |
| Thermal comfort by site | `indoor-environment/` | any site returned a thermal comfort score in the quarter |
| Key wins | `actions-and-wins/`, `key-wins.md` | at least one win qualifies |
| Sustainability ratings by site | `sustainability-ratings/` | any site holds a current rating; never mentioned in chat |

Each folder holds the section's reference and a `scripts/` folder with its arithmetic. A site with no data for a section is left out of that section's table and ranking, and its script names it to say in chat. `actions-and-wins/actions-resolved.md` has no part on the page: it makes the actions resolved calls and hands on the actions rankings the two leaderboards draw.

## How sections fit together

Each section's reference owns its section: what it shows, its rules, its calls, its notes band items, its anchor and what it says in chat. It names what it hands on and what it takes by the figure, never by the section at the other end, and cites this file and `DESIGN.md` but no other reference. Where each section sits, which figures feed which section and the build order live here, and the registry at the top of `scripts/report.py` carries the same in code.

- **Build order**: a section builds after every section whose figures it takes. The registry fixes the order
- **System types**: equipment types 21, 37, 69, 70, 87, 105 and 114, the platform checking itself rather than building plant. Every equipment count leaves them out; Rules running counts every running rule
- **Region label**: in the portfolio report, the bracket after a site's name holds its state, or its country where the portfolio spans countries; nothing where every site shares one, or where the name already ends in brackets

**Single-site page:** the masthead, the analytics overview, operational impact, sustainability ratings, the equipment health and indoor environment snapshots, their monthly trends, equipment run hours, monthly alerts and the actions leaderboard, key wins, then the notes band. A section that is out leaves no gap.

| Figure | Handed on by | Taken by |
| --- | --- | --- |
| Site facts: name, photo, building size, currency | the overview, before any section builds | every section |
| Thermal zones: zone points on the levels that scored | indoor environment, known at plan time | the analytics overview, which counts its own only when no section hands them on, so its figure always equals the comfort site row |
| Partial figures: volumes that run short over a month to date | equipment health and alerts resolved; indoor environment shows the month to date with none | the reporting window note |

**Portfolio page:** page one holds the masthead, the scorecard strip and the site leaderboard, page two the team leaderboard, and the other sections follow in the order of the [Portfolio sections](#portfolio-sections) table.

| Figure | Handed on by | Taken by |
| --- | --- | --- |
| Site facts: building size, currency, state, country, building photo link, default comfort band | the overview, before any section builds | every section |
| A ranking: a label, an anchor or each site's PEAK report, a window (the leaderboard month or the quarter ending on it), the unit of its figure, each site's figure now and on the window last month's board ranked | equipment health, indoor environment and actions resolved, in that order | the site leaderboard, one board each, its site names linking to the anchor or each to its own PEAK report |
| A team ranking: a ranking over the companies or people holding the work, with its unit, each one's name, company, logo and PEAK report, its leader's meta line, and for people the leader's shoutout: first name, email and busiest site | actions resolved, companies then assignees | the team leaderboard, one board each |
| Thermal zones: zone points on the levels that scored, and every configured point | indoor environment | the scorecards, so the card always equals the comfort table's Zones total |
| Sites with data: each site a section shows | equipment health, indoor environment, actions resolved, sustainability ratings and open P1-2 actions, in that order, and each key win's site at fill | the masthead's Sites count; open P1-2 actions, for the sites holding none |

## Writing the narrative

Every sentence on the page is written by the partner's engineer to the building's facility manager: the statement under each section name, the key wins, the methodology notes. Write like a building performance engineer, not a marketer.

- Use numbers as evidence and round them sensibly. 79%, not 79.08%. A move of 0.01 pp is not a move, so call it stable
- Explain a known cause plainly, and say when something is still open or needs a follow-up. Never imply an issue is resolved unless the data says so
- Facts carry it, so drop the summing-up line that tells the reader what to think
- No superlatives, no congratulation, no editorial framing. Past tense, active, plain words. Not "leveraged", "robust", "significant", "it is worth noting", "demonstrates"
- No em dashes. A full stop, a comma or a colon does the same work and does not read as generated. Ticket titles and the brand line are quoted verbatim, so leave their punctuation alone
- Nor the other tells: "not just X, but Y", rhetorical questions, a list of three where two would do, a sentence that opens by restating the one before it, stacked hedges like "may potentially"
- Never describe the report itself or how it was made. The reader wants the building, not the method

## What always renders

Single-site report. The portfolio's masthead and scorecard strip are in `references/portfolio-leaderboard/overview/overview.md`.

The overview script fills every slot below; these are the rules it follows.

### Report title

- {Site name} Quarterly Building Performance Review
- Prepared by: {Company name} {Company service name}. Powered by PEAK
- Reporting period: the quarter as a date range, per [How the scripts fetch](#how-the-scripts-fetch), or the site's own coverage per [Newly onboarded sites](#newly-onboarded-sites)
- Author: full name of the logged-in PEAK MCP user, from `who_am_i`, always present, never omitted or substituted
- Issue date: issue date
- Disclaimer, verbatim, below the masthead metadata row: "AI was used to help compile this report. All figures, analysis and recommendations were human-reviewed."
- Company name default "CIM" unless `name` is set in `BRAND.md` or given by the user
- Company service name default "Data Driven Operations" unless `service-name` is set in `BRAND.md` or given by the user
- `Powered by PEAK` in the masthead stays in every brand
- Site `photo_url`: square, right of title block
- Never print the PEAK site id anywhere in the report text or masthead. It is a system id and means nothing to the reader. Links carry it in the URL, which is where it belongs

### Analytics overview

What we monitor at {site name}  
Date: As at {issue date}

| Display metric | Reference                      |
| -------------- | ------------------------------ |
| Building size  | m² as PEAK stores it; ft² for US sites, converted |
| Equipment      | Total equipment                |
| Sensors        | Total sensors                  |
| Rules          | Total rules status running     |
| Thermal zones  | Total indoor environment zones |

All five render whatever the selection, including thermal zones when indoor environment is out. This is the monitoring footprint, not a summary of the sections below it.

## Operational impact

Single-site report. The portfolio report carries no operational impact section.

What that monitoring delivered this quarter  
Date: the quarter

Each row belongs to a section and is specified in that reference: three to equipment health, one to indoor environment, one to alerts resolved. The section renders when at least one of them is in, and drops when none is.

**Display:**

- No red in this section. The rating chip reads Excellent or Good on the positive chip, Average or Poor on the warning chip, never the negative one. A movement takes the positive delta when it improves and the muted delta when it declines or holds flat. State a fall plainly in the figure, the glyph and the word: reported, not colour coded. Red stays available to the snapshot tables and charts below
- Keep the surviving rows in this order: equipment health score, thermal comfort, automated checks, labor cost avoided, faults resolved
- Where a row states a movement, it runs from the reporting period's first month to its last, the month to date where the report carries one: the reporting period, and nothing outside it

## Notes band

Numbered notes in page order, each owned by the section it explains. A note carries business logic the page does not already show: an assumption, a scope rule, or why two figures differ. Anything a legend, chart heading, date line or impact row already says stays out. Write each as a short professional definition, not an explanation.

One item is shared, and only when the report carries a month to date:

- **The reporting window**: the month to date and how many of its days it holds, the partial figures the sections hand on, and that scores are unaffected. It closes the band

## After the render

A follow-up on a report that already exists is not a rebuild. Match the reading to the ask:

- **A number, a date, a name, a sentence**: edit the file. One PEAK call if the answer needs one, no references, no `DESIGN.md`
- **A section that was left out**: run the build again in a fresh directory with the report's full new list, copying `wins.json` across, so the wins already chosen carry over
- **A visual or structural change**, such as a new component, a table re-laid out or a different chart form: read `DESIGN.md`. `## Colors` and `## Typography` for the tokens and their roles, `## Components` for what a component owes, `## Layout` for the print rules. The rendered file carries the CSS but not the reasoning behind it
- **A rebrand**: `BRAND.md` and the logo assets it names, per [Output & theming](#output--theming). Both files stay at the repo root. The tokens sit in one `:root` block and the masthead logo is one inlined SVG, so this is a handful of edits on the file you already have

## Newly onboarded sites

Single-site report. In the portfolio report a site's months with no score show as dashes in its row, and the leaderboard marks it "New" where it has nothing to move from, per the portfolio references.

A site can have less history than the window asks for, and `report.py bundle` says so when a section's six-month series comes back short. The site went live inside the window, and the report covers what exists.

- Trim both windows to the months that returned data, still whole months only apart from the month to date. The month a site went live in is not a complete month for it unless it went live on the 1st, so drop it
- Say it once, in the masthead: "Reporting period: 1 – 31 August 2026, monitoring live since 14 July 2026". The reader needs to know the report is short because the site is new, not because something failed. Don't repeat it section by section
- A movement needs two months. With one, state the score and drop the delta. "Up 0.0 pp" against a month that does not exist is worse than no delta. That covers the heatmap Chg column too: with one month, drop the column, and sort the rows by score with the lowest first, so the plant needing attention leads
- A trend needs three points. With fewer, drop the trend chart and keep the snapshot; two months drawn as a line invites the reader to extend it. Where that empties a trends section, delete the section
- Delete the surplus month columns from the heatmap header and every row, so the table is only as wide as the data
- An equipment type or a level can start later than the site did, when new rules go on old plant. The script draws its earlier months and its Chg as dashes with no fill, so the row keeps the table's width; leave them, and say in chat when its rules began scoring
- Prorate the labor cost model over the days actually monitored, not the calendar quarter, or it credits the monitoring with time it wasn't running
- A gap in the middle of a series is an outage, not onboarding. So is a month that scored off a fraction of the usual rules. One rule against 850 either side is an outage wearing a score. Treat both alike: plot the months that exist, leave the gap visible, and say so in chat. The equipment health script names any such month

## Output & theming

One self-contained A4 print-first HTML file: all CSS inline, charts as inline SVG, no JS. The scaffold supplies the stylesheet and every component, and `fill_report.py` draws every chart from the bundle, so the geometry is never yours to compute.

Resolve the theme in this order:

1. **The scaffold**: its `:root` and component CSS are DESIGN.md compiled. A default CIM build needs nothing further; don't re-derive values the file already carries
2. **`BRAND.md`** (repo root): if present, apply its YAML frontmatter overrides by editing `:root`, the `@font-face` block and the masthead logo. Honor only these keys and ignore everything else:
  - `name`, `service-name`: the company and service names, per [Report title](#report-title)
  - `colors:`: `primary`, `primary-container`, `on-primary-container`, `secondary`, `on-secondary`, `on-secondary-muted`, `chart-benchmark`, `text-heading` only
  - `fonts:`: `display`, `text`, `mono` family swaps mapped onto the DESIGN.md typography roles (display → h1/h2/card-title/metric; text → body/body-sm/label/eyebrow; mono → mono). Sizes, weights and line-heights always keep DESIGN.md values. Families on Google Fonts load from the CDN, and the `font-family` stack carries the offline case; a family that is not on Google Fonts is embedded from `assets/fonts` as a base64 data URI, since a relative font path does not survive the report leaving this repo
  - `logos:`: `reversed` (masthead) and `full-color`, paths to partner files. Inline the referenced SVG contents (data URI for PNG) so the report stays self-contained
3. **`DESIGN.md`** (repo root, alongside BRAND.md): read `## Colors` and `## Typography` when an override needs the role mapping, and anything else per [After the render](#after-the-render)
4. A missing BRAND.md, or any key left commented or absent, keeps the CIM default. An untouched fork must render identically to CIM's own output

Derived rules when overrides are active:

- `secondary` overridden → re-derive the `shadow` token as the new `secondary` hue at 8% opacity
- No overrides → keep the CIM masthead logo the scaffold already carries from `assets/logo-white.svg`

## How the scripts fetch

Every call in a section's `calls()` answers a whole need in one request: rows for a window, not a month at a time; a set of ids, never one id at a time; a count wherever a count is all that is needed, from `count_tickets`, `count_indoor_environment_zones` or `pagination.total`; and everything else derived locally from rows already held. A change to a section's calls goes in its script, with the reason in its reference's Data block.

In the single-site report, the **quarter** is the three complete months before the issue date's month, and the snapshots use it column for column. The **6 month window** is the six complete months ending there, which the trends use. Once more than a week of the current month has passed, that **month to date** joins both windows as their last month, so the snapshots carry four columns and the trends seven points, and the reporting period runs from the quarter's first day to the issue date. Before then, every window closes on the last complete month and nothing covers a part-month. Every bound is a month boundary, the month to date included: it is fetched up to the first of the next month and holds whatever exists so far, because equipment health scores are stored pre-aggregated on month boundaries and a mid-month bound forces a raw scan. The scripts mark the month to date wherever it shows: "to date" under its column and axis labels, a tinted column behind it on every chart, and on a line chart a dashed last segment onto an open point. Its scores are rates and stand as they are; its volumes are short by construction, which the reporting window note says.

The section scripts build every link from the URL its reference writes out, on the host of the site's `site_link`. `{{site_id}}` is the PEAK site id; `{{quarter_start}}` and `{{trend_start}}` are the first days of the quarter and the 6 month window, `{{quarter_end}}` is the last day the reporting period covers, the issue date where it carries a month to date, and `{{quarter_last_month}}` the first day of its last month, all `YYYY-MM-DD`. A row link is the section link with the row's own filter appended, `&equipment_type_ids={id}` or `&level_ids={id}`. Key win evidence links to the `ticket_link` on each action ticket row.

A response too large to return inline comes back as a file: copy it under its name and the scripts read it from there. Status ids where a filter needs them: 1 New, 3 In Progress, 6 Closed, 7 On Hold, 8 Not Doing, which every count and pull leaves out.

### Portfolio windows

The portfolio report is a monthly leaderboard, built early each month for the month just ended and sent to the ops leaders, site teams and vendors it ranks.

- **Issue date**: the earliest local date across the sites, so the leaderboard month has closed at every one
- **Leaderboard month**: the last complete month before the issue date. It names the report, its masthead and its file
- **Quarter**: the three complete months ending on the leaderboard month. The heatmaps show it column for column, and actions resolved count over it
- **Last month's board**: every ranking moves against the board the report showed a month earlier, so an arrow means the same on every board. A board on the leaderboard month moves against the month before; one on the quarter, against the quarter a month earlier
- **Key wins**: the 90 days to the issue date, so the strongest win of those days can show in consecutive months
- **Open P1-2 actions**: open as at the issue date, whenever raised, under the issue month
- Nothing covers a part month. In the link templates, `{{quarter_start}}` is the quarter's first day, `{{quarter_end}}` the leaderboard month's last day and `{{quarter_last_month}}` the leaderboard month's first day; `{{assignee_id}}` is an assignee's PEAK user id
- Built on the 1st, the report ranks a month that has only just closed, and its scores may not have settled. `report.py plan` says so, and the build goes again from the 2nd before it is sent
