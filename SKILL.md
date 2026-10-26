---
name: client-report
description: Generates a client-facing report from PEAK as a self-contained print-ready HTML page. For one site, a quarterly building performance review, asking which sections to include. For a client company or several sites, a monthly portfolio leaderboard for the last complete month, with every section that has data. Use whenever the user runs /client-report or asks for a client report, a quarterly or building performance review, a portfolio leaderboard, or a site or portfolio performance report from PEAK. Do not auto-trigger on general PEAK questions or ticket workflows.
---

# Client Report

Two reports from one engine, each a self-contained A4 print-first HTML page:

- **Single-site report**: a quarterly building performance review for one PEAK site, which the partner hands to a facilities manager. The reader chooses which sections it carries, and a section that is out is never fetched
- **Portfolio leaderboard report**: a monthly leaderboard across a client's sites for the last complete month, sent to the ops leaders, site teams and vendors it ranks. Every section renders when PEAK has data for it

The section scripts make every figure, row, series, link, date line and note, and `scripts/fill_report.py` (single-site) and `scripts/fill_portfolio.py` (portfolio) draw them. Your part is the PEAK calls and the key wins. A change to how something looks is a change to those scripts or to `DESIGN.md`, never to a filled file.

**What to read:** this file, and the report's `key-wins.md` when key wins are in. Every other reference documents what its script already does; open it only to answer a question the script raises.

## Which report

Resolve the name before anything else, and before the section question.

- Call `search_sites(keyword:"<name>")` and `search_clients(client_name:"%<name>%")` together; for a name with punctuation or several words, call `search_clients` again with the punctuation removed and `%` before, between and after its words. A site matches at a match score of 0.9 or more; a weaker hit is only ever offered as an option. A client matches when its name is the name given, ignoring case and punctuation. With no client returned, search again with the last word dropped, one word at a time, and stop at the first search that returns clients: those are the closest clients
- **A site matches and no client does**: the single-site report
- **A client matches and no site does**: the portfolio report over the client's active sites, from `search_sites(client_ids:[<id>], limit:80)`, paged. A client with one active site gets the single-site report for that site, and `report.py plan` prints its commands. A client with no active site is never built: say so, and offer similar clients that hold sites, as below
- **A site and a client both match**: one `AskUserQuestion` call, header "Report": "<name> is both a PEAK site and a client. Which report?", options "<site name> (site)" and "<client name> portfolio (N sites)", N the sites with `is_active` true in the client's `search_sites(client_ids:[<id>], limit:80)` pages. Fetch those pages first; they are the `sites.json` pages if the portfolio is chosen
- **Neither matches**: one `AskUserQuestion` call, header "Report", up to four options: the closest clients as "<client name> portfolio (N sites)", then site hits scoring 0.5 or more as "<site name> (site)". Nothing at all: say so and ask for the site or client name
- **Several sites named**: the portfolio report over exactly those sites, titled with the client they share. Read each site's client ids with `platform.sites` selecting `site_id` and `clients`, keep the ids every site carries, and take the one with the fewest active sites, from `search_sites(client_ids:[<id>], limit:1)` and its `pagination.total`, skipping a client with more than ten times as many active sites as were named, a platform-wide grouping. Its name comes off `search_clients(client_name:"%", limit:200)`, paged. With no shared client, use the user's name for the group, else "Portfolio"
- "portfolio", "client" or "all sites for" point to the portfolio report
- A logo file the user supplies, as an attachment or a path, goes to `--client-logo`. Never search PEAK for a client logo, never ask for one, and never pass a logo from this skill or a brand overlay, which `plan` refuses
- More than about 50 active sites: before fetching, one `AskUserQuestion` call, header "Scope": "<Client> has N active sites, so the report runs long, a hundred or more PEAK calls. Build it for every site, or one state?", options "All N sites" then the three states with the most sites, each with its count. A state chosen keeps its sites through `--site-ids`
- State the resolved report, title and scope in one line in chat, "Portfolio report: 12 sites for <Client>", naming any other clients the search returned so the user can redirect, then go on

## Build order

Work in one directory, `report/` below.

1. **Resolve the site and the sections** per [Sections](#sections). Call `search_sites(keyword:"<site>", include_working_hours:true)` and `who_am_i` together, and save the `search_sites` response as `report/site.json`. Nothing else is fetched before the sections settle
   - **Portfolio**: save the client's `search_sites` pages as `report/sites.json`, `report/sites-2.json` and on, or the one `search_sites(site_ids:[...])` response for sites named one by one, and call `who_am_i`
2. **Plan**: `python3 scripts/report.py plan report --site report/site.json --author "<who_am_i user_name>" --sections <names>`, the names comma-separated with no spaces (`--sections equipment-health,run-hours`) and left off for the full report. It fixes the windows and prints every call the sections need, each with the file under `report/peak/` its response is saved as. Planning a folder again on the same issue date keeps each saved response whose call is unchanged and clears the rest; a new issue date clears them all
   - **Portfolio**: `python3 scripts/report.py plan report --sites report/sites.json [report/sites-2.json ...] --client "<name>" --author "<who_am_i user_name>"`, with `--client-logo <file>` for a supplied logo and `--site-ids <id> ...` to keep only some sites. It keeps the active sites and splits each call across the sites a tool takes at once
3. **Fetch**: make every printed call in one parallel batch, exactly as printed; a portfolio plan can print a hundred, so send those in batches of about twenty. Save each response the plan lists to save as its file, an offloaded one by copying the file you were handed, an inline one written exactly as returned. The calls marked read, never saved, are the key win candidate pulls: read them where they come back and never save them, since they carry what people wrote on the tickets. Then `python3 scripts/report.py next report`, and make whatever it prints the same way until it says there are no more calls
   - A call that fails with a 5xx or a timeout is made again exactly as printed; if it keeps failing, stop and say which call and what it returned. After a dropped PEAK connection, `next` lists the calls still unsaved; if the server does not come back, say so and stop, since everything saved keeps
   - `next` reads every saved response back first, and stops on one that does not parse, holds PEAK's error instead of data, holds more or fewer rows than its pagination says, or carries a site outside the report: save that one again from the tool's output. `report.py verify report` runs the same check alone
4. **Bundle**: `python3 scripts/report.py bundle report` writes every figure into `report/data.json`, prints anything to say in chat at hand-over, then the next step
5. **Key wins**, when Actions and key wins is in: choose and write `report/wins.json` by `references/single-site/actions-and-wins/key-wins.md`, `[]` when no win qualifies; `next` then prints the impact and photo calls. Once those are saved, run `python3 references/single-site/actions-and-wins/scripts/key_wins.py photos report` straight away, since the photo links lapse twenty minutes after the call, then `next` again for the level call. Look at the contact sheet made per win, and add your picks to `wins.json`
   - **Portfolio**: follow `references/portfolio-leaderboard/actions-and-wins/key-wins.md`, which reads the candidates in two passes, a shortlist then the shortlist in full, and uses its own `scripts/key_wins.py photos`
6. **Fill and check**: `python3 scripts/report.py fill report` fills the report, saves every photo tile, and runs the check. Look at the tiles. Then say in chat whatever it lists, name the sections left out, and hand over the file

## Sections

### Single-site

Ask before fetching anything, with one `AskUserQuestion` call and one multi-select question, header "Sections": "Which sections should the report cover from last quarter?" The four options are the whole list:

| Choice | `--sections` name | Folder under `references/single-site/` | Adds |
| --- | --- | --- | --- |
| Equipment health | `equipment-health` | `equipment-health/` | the equipment health score, automated checks and labour cost avoided rows; health by equipment type; the score and checks trends |
| Indoor environment | `indoor-environment` | `indoor-environment/` | the thermal comfort row, comfort by level, the six month comfort trend |
| Actions and key wins | `actions-and-wins` | `actions-and-wins/` | the faults resolved row with verified recovery, six months of raised vs resolved, who closed the work, and the key wins: repairs made plus live work the owner should see |
| Equipment run hours | `run-hours` | `run-hours/` | when each unit of plant ran across the latest full Monday-to-Sunday week, against the site's working hours |

Actions and key wins is one choice with two references, `alerts-resolved.md` and `key-wins.md`, which share their pulls. `overview/` is the part every report carries: the masthead, the analytics overview, and the operational impact and notes band frames.

- Everything is in by default: a dismissed prompt or an unanswered question gets the full report
- Skip the prompt when the invocation names the sections ("/client-report Skyline Tower: equipment health and key wins only"), and state the resolved list in your reply instead
- A section that is out is never fetched, and leaves behind no empty section, header, link or note. The scripts handle the parts they know about; check the wins yourself
- Four things can come up empty after the fetch: equipment health or indoor environment when PEAK holds no score for the site in the quarter, Actions and key wins when nothing was resolved, Key wins alone when no win qualifies, and run hours when no plant carries a sensor that shows it running. The scripts leave the section out and print why; say so in chat, not on the page
- Where only the masthead and the analytics overview survive, say so before handing the file over rather than shipping it as a review

**Automatic:** `sustainability-ratings`, a card per NABERS energy, indoor environment and water rating and its history. `report.py plan` adds it to every report and its script leaves it out when PEAK holds no current rating. Never offer it, and say nothing about it in chat.

### Portfolio

Never asks which sections to include. Every section is planned and fetched, and renders when PEAK returns data for it. A site with no data for a section is left out of that section, and its script names it to say in chat.

| Section | Folder under `references/portfolio-leaderboard/` | Renders when |
| --- | --- | --- |
| Masthead and scorecard strip | `overview/` | always |
| Site leaderboard | `site-leaderboard/` | at least one of its boards has data |
| Team leaderboard | `team-leaderboard/` | at least one of its boards has data |
| Open P1-2 actions | `actions-and-wins/open-actions.md` | any priority 1 or 2 action is open now |
| Equipment health by site | `equipment-health/` | any site returned an equipment health score in the quarter |
| Thermal comfort by site | `indoor-environment/` | any site returned a thermal comfort score in the quarter |
| Key wins | `actions-and-wins/key-wins.md` | at least one win qualifies |
| Sustainability ratings by site | `sustainability-ratings/` | any site holds a current rating; never mentioned in chat |

`actions-and-wins/actions-resolved.md` has no part on the page: it makes the actions resolved pulls and hands on the rankings the two leaderboards draw.

## Wiring

Each reference owns its section: what it shows, its rules, calls, notes band items, anchor and chat lines. It names what it hands on and takes by the figure, never by the section at the other end, and cites only `DESIGN.md` component names. Placement, figure flow and build order live here and in the registry at the top of `scripts/report.py`; a section builds after every section whose figures it takes. Every equipment and rule count and every equipment health score leaves out the BACER, equipment type 105 (`SYS-BACER`), the device that reads the building's BMS into PEAK rather than building plant. Every other type counts, the system ones such as the meters included.

**Single-site page:** page one holds the masthead, the analytics overview and operational impact; then sustainability ratings, the equipment health and indoor environment snapshots, their monthly trends, equipment run hours, monthly alerts and the actions leaderboard, key wins, and the notes band. A section that is out leaves no gap. Impact rows run equipment health score, thermal comfort, automated checks, labour cost avoided, faults resolved; notes run in page order, the reporting window last.

| Figure | Handed on by | Taken by |
| --- | --- | --- |
| Site facts: name, photo, building size, currency | the overview, before any section builds | every section |
| Impact rows and notes band items | equipment health, indoor environment, alerts resolved; run hours a note | the overview's frames |
| Scored equipment and rules | equipment health, at plan time | the analytics overview |
| Thermal zones that scored | indoor environment, at plan time | the analytics overview |
| Partial figures over a month to date | equipment health, alerts resolved | the reporting window note |
| First month kept and go-live | equipment health, indoor environment | the masthead reporting period |
| Trend start: the first month kept | equipment health, indoor environment | the raised vs resolved chart's first month |
| Nothing resolved | alerts resolved | key wins, which drops with it |

**Portfolio page:** page one holds the masthead, the scorecard strip and the site leaderboard, page two the team leaderboard, and the other sections follow in the [Portfolio](#portfolio) table's order.

| Figure | Handed on by | Taken by |
| --- | --- | --- |
| Site facts: building size, currency, state, country, photo link, comfort band | the overview, before any section builds | every section |
| A ranking: each site's figure now and on last month's board, with its label, link, window, unit and note, and the sites too small to lead | equipment health, indoor environment, actions resolved, in that order | the site leaderboard, a board each |
| A team ranking: the same over companies or people, with logos, each one's site line, the leader's meta line and shoutout | actions resolved, companies then assignees | the team leaderboard, a board each |
| Scored equipment and rules | equipment health | the scorecards |
| Thermal zone points that scored | indoor environment | the scorecards |
| Sites with data | equipment health, indoor environment, actions resolved, sustainability ratings, open P1-2 actions, then each key win's site at fill | the masthead's Sites count; open P1-2 actions, for the sites holding none |

### Windows

`report.py plan` fixes every window, and every PEAK date filter reads in each site's own time zone.

- **Single-site**: the **quarter** is the three complete months before the issue date's month, which the snapshots show column for column; the **6 month window** is the six complete months ending there, which the trends draw. Once more than a week of the issue month has passed, the **month to date** joins both as their last month and the reporting period runs to the issue date: its scores stand as rates, and its volumes run short, which the reporting window note says
- Every bound is a month boundary, the month to date fetched to the first of the next month, since equipment health scores are stored pre-aggregated by month
- **Portfolio**: the **issue date** is the earliest local date across the sites; the **leaderboard month**, the last complete month before it, names the report; the **quarter** is the three complete months ending on it. Every ranking moves against **last month's board**: the month before, or the quarter a month earlier. **Key wins** cover the 90 days to the issue date. **Open P1-2 actions** are open at the issue date, the backlog drawn at the eleven month ends before, from the month the first P1-2 action was raised. Nothing covers a part month
- Built on the 1st, the portfolio's scores may not have settled: `report.py plan` says so, and the build goes again from the 2nd before it is sent

**Links:** the section scripts build every link from the URL its reference writes out, on the host of the site's `site_link`. `{{site_id}}` is the PEAK site id and `{{assignee_id}}` a PEAK user id; `{{quarter_start}}` and `{{trend_start}}` are the first days of the quarter and the 6 month window; `{{quarter_end}}` is the last day the period covers, the issue date where it carries a month to date and the leaderboard month's last day in the portfolio; `{{quarter_last_month}}` is the first day of its last month; all `YYYY-MM-DD`. A row link is the section link with the row's own filter appended, `&equipment_type_ids={id}` or `&level_ids={id}`.

**Calls:** each call in a section's `calls()` answers a whole need in one request: rows for a window, not a month at a time; a set of ids, not one at a time; a count wherever a count will do, from `count_tickets`, `count_indoor_environment_zones` or `pagination.total`. Everything else is derived from rows already held. A change to a section's calls goes in its script, with the reason in its reference's Data block. Status ids: 1 New, 3 In Progress, 6 Closed, 7 On Hold, 8 Not Doing, which every count and pull leaves out.

## After the render

A follow-up on a report that already exists is not a rebuild. Match the reading to the ask:

- **A number, a date, a name, a sentence**: edit the file, with one PEAK call if the answer needs one and no references or `DESIGN.md`. A sentence you write follows the Voice in the report's `key-wins.md`
- **A section that was left out**: build again in a fresh directory with the full new list, copying `wins.json` across so the wins already chosen carry over
- **A visual or structural change**, such as a new component or a different chart form: read `DESIGN.md`, `## Colors` and `## Typography` for the tokens and their roles, `## Components` for what a component owes, `## Layout` for the print rules
- **A rebrand**: `BRAND.md` and the logo assets it names, per [Output & theming](#output--theming). The tokens sit in one `:root` block and the masthead logo is one inlined SVG, so this is a handful of edits on the file you already have

## Output & theming

One self-contained A4 print-first HTML file: all CSS inline, charts as inline SVG, no JS. The scaffold supplies the stylesheet and every component, and the fill scripts draw every chart, so the geometry is never yours to compute.

Resolve the theme in this order:

1. **The scaffold**: its `:root` and component CSS are `DESIGN.md` compiled. A default CIM build needs nothing further
2. **`BRAND.md`** (repo root): if present, apply its YAML frontmatter overrides by editing `:root`, the `@font-face` block and the masthead logo. Honor only these keys:
   - `name`, `service-name`: the masthead's company and service names, CIM and Data Driven Operations by default. `Powered by PEAK` stays in every brand
   - `colors:`: `primary`, `primary-container`, `on-primary-container`, `secondary`, `on-secondary`, `on-secondary-muted`, `chart-benchmark`, `text-heading` only
   - `fonts:`: `display`, `text`, `mono` family swaps onto the `DESIGN.md` typography roles (display → h1/h2/card-title/metric; text → body/body-sm/label/eyebrow; mono → mono); sizes, weights and line-heights keep `DESIGN.md` values. A family on Google Fonts loads from the CDN, one `@font-face` per subset, its `font-family` stack ending in the system faces for the offline case. A family not on Google Fonts is embedded from `assets/fonts` as a base64 woff2 data URI, since a relative font path does not survive the report leaving this repo
   - `logos:`: `reversed` (masthead) and `full-color`, paths to partner files, inlined as SVG contents or a PNG data URI so the report stays self-contained
3. **`DESIGN.md`** (repo root): read `## Colors` and `## Typography` when an override needs the role mapping
4. A missing `BRAND.md`, or any key left commented or absent, keeps the CIM default. An untouched fork renders identically to CIM's own output

When `secondary` is overridden, re-derive the `shadow` token as the new `secondary` hue at 8% opacity. With no overrides, keep the CIM masthead logo the scaffold carries from `assets/logo-white.svg`.
