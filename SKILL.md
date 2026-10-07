---
name: client-report
description: Generates a client-facing quarterly building performance review for a PEAK site - analytics overview, operational impact metrics, equipment health and indoor environment snapshots, monthly trends, alerts resolved with the actions leaderboard and key wins, and equipment run hours against working hours, as a self-contained print-ready HTML page, asking up front which sections to include and building only those. Use this whenever the user runs the /client-report slash command or asks for a client report, a quarterly or site building performance review, a site performance report from PEAK, or a report to send a facilities manager or building owner. Do not auto-trigger on general PEAK questions or ticket workflows.
---

# Client Report

A quarterly building performance review for one PEAK site: a self-contained A4 print-first HTML page the partner hands to a facilities manager. The reader chooses which sections it carries, and that choice decides what you fetch, what markup you build and which references you read. A section that is out is never fetched, built or read.

## Build order

Commands name each script by its path inside this skill. Run them from a working folder of your own, so the bundle, the saved responses and the report never land in the skill.

1. **Resolve the site and the sections**: [Section selection](#section-selection). Nothing is fetched before this settles, because the selection decides what there is to fetch.
2. **Read the reference for each chosen section**, in its folder under `references/`, per [Section selection](#section-selection). Each carries its table spec, benchmark, links and notes items, and closes with a Data recipes block holding the PEAK calls behind them. The others describe sections you are not building; leave them unread.
3. **Fetch**: [Data recipes](#data-recipes), then the Data recipes block at the end of each chosen reference. Nothing else. One call resolves the site; every remaining call that does not wait on another response then goes out in a single parallel batch. Resolve equipment type names with an unfiltered `search_equipment_types(limit:200)` rather than waiting on the health scores for their ids, so they join that batch. The follow-ups that do wait, such as the key win evidence and the run hours history, go out together once their inputs are in.
4. **Write the data bundle**: one `data.json` carrying every figure, row, series and sentence the report needs. Derive it from the fetched rows with a short python script, reading the large pulls off the files the gateway wrote them to rather than out of the conversation. What people wrote on tickets stays where it came back: never copy comments into a file or a script, since the wins are written in your own words from them. The prose is yours and follows [Writing the narrative](#writing-the-narrative); the bundle is where it lives. `scripts/fill_report.py` is the schema: its key names are the contract.
5. **Fill**: `python3 scripts/fill_report.py data.json --out skyline-q3.html`. It scaffolds the chosen sections, then renders both heatmaps with their band colours, recomputes each chart's y geometry from its own data range, and lays in the operational impact rows, the leaderboard, the wins, the run hours chart and the platform links. The masthead, the statements, the date lines and the notes go in as `replace` pairs, each a sample string from the scaffold and the report's own text. Tables and charts are the script's, so a change to how one looks goes in `fill_report.py` or `DESIGN.md`, never in a filled file. `build_report.py parts` lists what a section owns, and `build_report.py part <name>` prints one part when you are adding a section to a report that already exists.
6. **Check and hand over**: `python3 scripts/build_report.py check <file>` catches sample values, unresolved placeholders and markers left behind. It is a backstop, not a substitute for reading the numbers. Then name the sections you left out, so the reader knows the omission was asked for.

## Section selection

Ask before fetching anything. The masthead and [Analytics overview](#analytics-overview) always render. The four sections below are the reader's choice, and each owns a set of parts that come and go together: its operational impact rows, its own section, its monthly trend, their links and its notes-band items.

Ask with one `AskUserQuestion` call and one multi-select question, header "Sections": "Which sections should the report cover from last quarter?" Four options is the tool's limit, and four is the whole list. Describe each by what it adds:

| Choice               | `sections` name      | Reference                                                              | Adds                                                                                                                                                                   |
| -------------------- | -------------------- | ---------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Equipment run hours  | `run-hours`          | `references/run-hours/run-hours.md`                                    | when each unit of plant ran across the last full week of the quarter, against the site's working hours                                                                 |
| Equipment health     | `equipment-health`   | `references/equipment-health/equipment-health.md`                      | the equipment health score, automated checks and labor cost avoided rows; health by equipment type; the score and checks trends                                        |
| Indoor environment   | `indoor-environment` | `references/indoor-environment/indoor-environment.md`                  | the thermal comfort row, comfort by level, the six month comfort trend                                                                                                 |
| Actions and key wins | `actions-and-wins`   | `references/actions-and-wins/alerts-resolved.md` and `key-wins.md`     | the faults resolved row with verified recovery, six months of raised vs resolved, who closed the work, and the key wins: repairs made plus live work the owner should see |

Each section keeps its reference in its own folder, and any scripts it needs beside it. Actions and key wins is one choice over two references, because both read the site's action tickets and share their pulls. Inside the bundle it is two sections, `alerts-resolved` and `key-wins`, so Key wins can drop on its own.

**Rules:**

- Everything is included by default. A dismissed prompt, an unanswered question, or an invocation naming only a site gets the full report
- Skip the prompt when the invocation already names the sections ("/client-report Skyline Tower: equipment health and run hours only") and state the resolved list in your reply instead
- Resolve the list before the first PEAK call. A section that is out is never fetched
- [Operational impact](#operational-impact) and the [Notes band](#notes-band) are frames around rows and items the sections own. Operational impact renders when Equipment health, Indoor environment or Actions and key wins is in, since run hours owns no row; the notes band renders with any section. The scaffold builds it that way
- The notes band is an `<ol>`, so items dropped with their section renumber themselves. Trim the shared reporting-window item to the series that survive
- Never leave behind an empty section, a header with no content, a link to a section that is out, or a note explaining a number the report no longer shows. The scaffold handles the parts it knows about; check the prose yourself
- Three things can come up empty after the fetch, and only the fetch can tell: Actions and key wins, when nothing was resolved in the window; Key wins alone, when no win qualifies; and Equipment run hours, when no plant carries a sensor that shows it running. Leave the section out of the bundle's `sections`, listing `alerts-resolved` in place of `actions-and-wins` when only Key wins drops, and say so in chat, not on the page. The references carry the rule

## Writing the narrative

Every sentence on the page is written by the partner's engineer to the building's facility manager: the statement under each section name, the note under each table and chart, the key wins, the methodology notes. Write like a building performance engineer, not a marketer.

- Open with the most meaningful improvement. If nothing improved, open with what held steady
- Use numbers as evidence and round them sensibly. 79%, not 79.08%. A move of 0.01 pp is not a move, so call it stable
- Explain a known cause plainly, and say when something is still open or needs a follow-up. Never imply an issue is resolved unless the data says so
- Do not narrate the table row by row. The table is already on the page and the reader runs the plant; the note says what it means
- Three or four short sentences. Facts carry it, so drop the summing-up line that tells the reader what to think
- No superlatives, no congratulation, no editorial framing. Past tense, active, plain words. Not "leveraged", "robust", "significant", "it is worth noting", "demonstrates"
- No em dashes. A full stop, a comma or a colon does the same work and does not read as generated. Ticket titles and the brand line are quoted verbatim, so leave their punctuation alone
- Nor the other tells: "not just X, but Y", rhetorical questions, a list of three where two would do, a sentence that opens by restating the one before it, stacked hedges like "may potentially"
- Never describe the report itself or how it was made. The reader wants the building, not the method

A chart note before and after. The first packs everything in, opens on an editorial framing, quotes 79.08% and closes on a movement too small to be one:

> Water meters are the exception on an otherwise flat page: three meters on five rules sat at 54% through June and July, then recovered to 79.08% in August after the flatlined sub-meters on the podium cold water and cooling tower make-up lines were chased down. Everything else stayed inside Excellent all quarter, and the only fall is air handling units at 0.75 pp, which tracks the fan motor failure on AHU-6-3 in July. The site line moved 0.01 pp.

> Water meter health improved from 54% to 79% in August, although flatlined sub-meters on the podium cold water and cooling tower make-up lines still require attention. Overall site health remained stable at 99.6%. The small reduction in AHU health was linked to a fan motor failure on AHU-6-3.

## What always renders

### Report title

- {Site name} Quarterly Building Performance Review
- Prepared by: {Company name} {Company service name}. Powered by PEAK
- Reporting period: the quarter as a date range, per [Data recipes](#data-recipes), or the site's own coverage per [Newly onboarded sites](#newly-onboarded-sites)
- Author: full name of the logged-in PEAK MCP user, from `who_am_i`, always present, never omitted or substituted
- Issue date: issue date
- Disclaimer, verbatim, below the masthead metadata row: "AI was used to help compile this report. All figures, analysis and recommendations were human-reviewed."
- Company name default "CIM" unless `name` is set in `BRAND.md` or given by the user
- Company service name default "Data Driven Operations" unless `service-name` is set in `BRAND.md` or given by the user
- Site `photo_url`: square, right of title block
- Never print the PEAK site id anywhere in the report text, masthead or footer. It is a system id and means nothing to the reader. Links carry it in the URL, which is where it belongs

### Analytics overview

What we monitor at {site name}  
Date: As at {issue date}

| Display metric | Reference                      |
| -------------- | ------------------------------ |
| Building size  | Use sqm or sqft per region     |
| Equipment      | Total equipment                |
| Sensors        | Total sensors                  |
| Rules          | Total rules status running     |
| Thermal zones  | Total indoor environment zones |

All five render whatever the selection, including thermal zones when indoor environment is out. This is the monitoring footprint, not a summary of the sections below it.

## Operational impact

What that monitoring delivered this quarter  
Date: the quarter

Each row belongs to a section and is specified in that reference: three to equipment health, one to indoor environment, one to alerts resolved. The section renders when at least one of them is in, and drops when none is.

**Display:**

- No red in this section. The rating chip reads Excellent or Good on the positive chip, Average or Poor on the warning chip, never the negative one. A movement takes the positive delta when it improves and the muted delta when it declines or holds flat. State a fall plainly in the figure, the glyph and the word: reported, not colour coded. Red stays available to the snapshot tables and charts below
- Keep the surviving rows in this order: equipment health score, thermal comfort, automated checks, labor cost avoided, faults resolved
- Where a row states a movement, it runs from the quarter's first month to its last: the reporting period, and nothing outside it

## Notes band

Numbered methodology items in report order, each owned by the section it explains, plus one shared item:

- **The reporting window**: every monthly series closes on the last complete month, so no column or bar covers a part-month and the volume series can be read against each other directly. Name the series the report actually shows, and the three complete months the quarter covers

## After the render

A follow-up on a report that already exists is not a rebuild. Match the reading to the ask:

- **A number, a date, a name, a sentence**: edit the file. One PEAK call if the answer needs one, no references, no `DESIGN.md`
- **A section that was left out**: `python3 scripts/build_report.py part key-wins --sections <the report's full new list>` prints that part's markup on its own. Paste it in report order, read its reference, fetch only its calls. Re-scaffolding would throw away the report you have. Where the new section owns operational impact rows or notes items, add those too; if the report lacks the frame they belong in, scaffold a fresh file instead
- **A visual or structural change**, such as a new component, a table re-laid out or a different chart form: read `DESIGN.md`. `## Colors` and `## Typography` for the tokens and their roles, `## Components` for what a component owes, `## Layout` for the print rules. The rendered file carries the CSS but not the reasoning behind it
- **A rebrand**: `BRAND.md` and the logo assets it names, per [Output & theming](#output--theming). Both files stay at the repo root. The tokens sit in one `:root` block and the masthead logo is one inlined SVG, so this is a handful of edits on the file you already have

## Newly onboarded sites

A site can have less history than the window asks for. Read that from the first fetch rather than assuming: if the earliest month returned by the `site` × `month` call is later than the window start, the site went live inside the window and the report covers what exists.

- Trim both windows to the months that returned data, still whole months only. The month a site went live in is not a complete month for it unless it went live on the 1st, so drop it
- Say it once, in the masthead: "Reporting period: 1 – 31 August 2026, monitoring live since 14 July 2026". The reader needs to know the report is short because the site is new, not because something failed. Don't repeat it section by section
- A movement needs two months. With one, state the score and drop the delta. "Up 0.00 pp" against a month that does not exist is worse than no delta. That covers the heatmap Chg column too: with one month, drop the column, and sort the rows by score with the lowest first, so the plant needing attention leads
- A trend needs three points. With fewer, drop the trend chart and keep the snapshot; two months drawn as a line invites the reader to extend it. Where that empties a trends section, delete the section
- Delete the surplus month columns from the heatmap header and every row, so the table is only as wide as the data
- An equipment type or a level can start later than the site did, when new rules go on old plant. Keep its cell so the row stays the table's width, as `<td class="c none">&mdash;</td>`: no band class, so no fill, which is what a month with no reading should look like. Dash its Chg too, and say in the section note when its rules began scoring
- Prorate the labor cost model over the days actually monitored, not the calendar quarter, or it credits the monitoring with time it wasn't running
- A gap in the middle of a series is an outage, not onboarding. So is a month that scored off a fraction of the usual rules. One rule against 850 either side is an outage wearing a score. Treat both alike: plot the months that exist, leave the gap visible, and say so in the chart note

## Output & theming

One self-contained A4 print-first HTML file: all CSS inline, charts as inline SVG, no JS. The scaffold supplies the stylesheet and every component, and `fill_report.py` draws every table and chart from the bundle, so their geometry is never yours to compute:

- Chart series colours are CSS classes backed by `:root` tokens (`.bar-primary`, `.bar-benchmark`, `.series-line`, `.pt`, `.sw-primary`, `.sw-benchmark`), never hardcoded hex, because SVG presentation attributes cannot read `var()`. Heatmap band fills work the same way (`.b4`, `.b3`, `.b2`, `.b1` for Excellent, Good, Average, Poor)
- Section headers are three stacked lines: the section name as an uppercase eyebrow in `primary`, the statement beneath it as the `h2` headline, and the date line as a muted byline. The statement is the headline, never the section name

Resolve the theme in this order:

1. **The scaffold**: its `:root` and component CSS are DESIGN.md compiled. A default CIM build needs nothing further; don't re-derive values the file already carries
2. **`BRAND.md`** (repo root): if present, apply its YAML frontmatter overrides by editing `:root`, the `@font-face` block and the masthead logo. Honor only these keys and ignore everything else:
  - `name`, `service-name`: replace the company name and service name defaults in [Report title](#report-title)
  - `colors:`: `primary`, `primary-container`, `on-primary-container`, `secondary`, `on-secondary`, `on-secondary-muted`, `chart-benchmark`, `text-heading` only
  - `fonts:`: `display`, `text`, `mono` family swaps mapped onto the DESIGN.md typography roles (display → h1/h2/card-title/metric; text → body/body-sm/label/eyebrow; mono → mono). Sizes, weights and line-heights always keep DESIGN.md values. Families on Google Fonts load from the CDN, and the `font-family` stack carries the offline case; a family that is not on Google Fonts is embedded from `assets/fonts` as a base64 data URI, since a relative font path does not survive the report leaving this repo
  - `logos:`: `reversed` (masthead) and `full-color`, paths to partner files. Inline the referenced SVG contents (data URI for PNG) so the report stays self-contained
3. **`DESIGN.md`** (repo root, alongside BRAND.md): read its `## Colors` and `## Typography` sections when an override needs the role mapping, and the rest when you need a component the scaffold has no CSS for or are changing the design itself, per [After the render](#after-the-render). DESIGN.md is the source of truth; the scaffold is its output
4. A missing BRAND.md, or any key left commented or absent, keeps the CIM default. An untouched fork must render identically to CIM's own output

Derived rules when overrides are active:

- `secondary` overridden → re-derive the `shadow` token as the new `secondary` hue at 8% opacity
- Any brand override active → platform strings read `PEAK` (drop the CIM prefix) in the masthead metadata row and footer. `Powered by PEAK` is always kept, in every brand
- No overrides → keep `CIM PEAK` and the CIM masthead logo the scaffold already carries from `assets/logo-white.svg`

## Data recipes

Every recipe here answers a whole need in one request: pull rows for a window, not a month; pass a set, not one id at a time; ask for a count whenever a count is all you need, from `count_tickets`, `count_indoor_environment_zones` or `pagination.total`, rather than tallying rows; and derive locally anything already sitting in rows you hold. A per-item loop is the sign of a missed batch filter.

Every window closes on the **last complete month**, so nothing in the report covers a part-month. Two reasons: a quarterly review should read as of the quarter, not as of the day it was generated; and equipment health scores are stored pre-aggregated on month boundaries, so a mid-month bound forces a raw scan and a wide call is then refused for scanning too many rows.

Two windows, named here because the references reuse them. The **quarter** is the three complete months ending on the last complete month, and the snapshots use it column for column. The **6 month window** is the six complete months ending there, which the trends use, so a trend carries the quarter plus the three months before it. Both close on the same month, so trends and snapshots share that bucket and must not disagree on it. Equipment run hours shows one week: the last full Monday-to-Sunday week inside the quarter.

The references build PEAK links from these, so substitute rather than hardcoding dates:

| Placeholder              | Value                                                  |
| ------------------------ | ------------------------------------------------------ |
| `{{quarter_start}}`      | first day of the quarter, `YYYY-MM-DD`                 |
| `{{quarter_end}}`        | last day of the quarter, the last complete month's end |
| `{{quarter_last_month}}` | first day of that last month, for `summary_ts`         |
| `{{trend_start}}`        | first day of the 6 month window                        |

Pass the section and chart links to `fill_report.py` in `links`, keyed by the slot each reference names, and it lays them into the scaffold. Row links ride on their rows and ticket links on their wins. The run hours unit links are built by its scripts.

Always:

- Site: `search_sites(keyword:"<site>", include_working_hours:true)`. With Equipment run hours in, save the response as `site.json`: the run hours window step reads the timezone and working hours off it
- Author: `who_am_i`, the user's full name for the masthead
- Site facts: `search_sites` omits these, so use GraphQL: `platform.sites` args `{site_id}` fields `[site_name, photo_url, building_size, monetary_currency]`
- Equipment type names: equipment health scores come back as `metadata_type_id` with no names, so resolve them all with one unfiltered `search_equipment_types(limit:200)` in the main batch. Never one call per type
- Counts for the analytics overview: never fetch rows. Call with `limit:1` and read `pagination.total`: `search_rules(task_state:running)`, `search_favourites` for sensors, and `search_equipment` twice, once plain and once filtered to system types 21,37,69,70,87,105,114 so you can subtract them
- Thermal zones: the zone temperature points configured for comfort scoring on the levels that returned a comfort score over the quarter. It is the indoor environment snapshot's site row, so the two never disagree. When Indoor environment is in, read it off that site row and make no call for it. Otherwise it is two calls in the main batch: `count_indoor_environment_zones(metric:"temperature", site_ids:[id], aggregate_entity:"level")`, and `search_indoor_environment(metric:"temperature", site_ids:[id], aggregate_entity:"level", aggregate_period:"all")` over the quarter for the levels that scored. Sum `included_point_count` over those levels. Count points with `count_indoor_environment_zones`, never `search_favourites` by point code: the code differs by equipment type, so a fixed list of codes misses whatever the building happens to use

Only when Actions and key wins is in:

Every number the leaderboard and the raised vs resolved chart print is a count, so it comes from `count_tickets`, never from tallying rows. The server reads each window in site time, so no timestamp needs converting, and a count cannot be cut short by a `limit`. Rows carry only what a count cannot: titles, comments, the median and company names.

The counts. Each carries `site_ids`, `ticket_types:["escalated"]` and `statuses:["open","in_progress","closed","on_hold"]`. The type counts actions, one per ticket, never the alerts behind them: an action can be bulk-linked to dozens of alerts, so weighting by alerts makes a month spike on a triage decision rather than on work. The statuses drop Not Doing.

- **Resolved by assignee**: `aggregate_entities:["assignee"]`, `local_resolved_start`/`local_resolved_end` over the 6 month window. The leaderboard's Resolved column
- **Open now by assignee**: `aggregate_entities:["assignee"]` with `statuses:["open","in_progress","on_hold"]` instead, and no date bound, since work raised before the window can still be open today. The leaderboard's Open now column
- **Raised and resolved by month**: ungrouped, one call per month per series, since `count_tickets` has no month bucket: `local_created_start`/`local_created_end` for raised and `local_resolved_start`/`local_resolved_end` for resolved, on that month's own bounds, all in the main batch

The rows are one GraphQL query, `tickets.tickets`, carrying `type:"escalated"`, `site_ids` and `ticket_archived:false` on all of them. How the pulls are shaped:

- It carries `summary`, the ticket title, so any pull that needs titles gets them inline. `search_action_tickets` is the fallback for equipment names, and only when a summary does not already carry them — Key wins runs it once over its shortlist regardless, since the win impact tags come off its `impacts` field and the GraphQL rows carry only raw `impact_ids`
- `comments` is a sub-field taking its own `limit` and `user_only`, and its body field is `text`, not `comment_text`. A comment history rides along with the row it belongs to, so a whole shortlist's histories come back in one call
- Array filters throughout, `status_ids` and `ticket_ids`, so a set of statuses or tickets goes in one call
- `limit` goes well past what the search tools page at, so size the pull to the site rather than assuming. Read `pagination.total` off the first response and check `has_more`: a `limit` under the total returns a full page and sets `has_more:true` instead of erring, so an unchecked pull silently drops rows and whatever it feeds is quietly wrong. A busy site runs to hundreds of actions in a window

The calls:

- **Resolved**: `resolved_at_local_start`/`resolved_at_local_end` over the 6 month window, fields `age`, `resolved_at`, `status_id` and `assignees{id, entity{name}}`, `limit:1000`. It answers the median, over the actions resolved in the quarter, the operational impact row's own window, from `age`, which on a resolved action is the milliseconds from creation to resolution, and the company of everyone who closed work, `entity{name}` matched on the `assignee_id` the counts return. Select only those fields: `summary` and `comment_count` belong to the Key wins pull, and across a thousand rows they push the response past the gateway's size limit
- **Open now**: `status_ids:[1,3,7]`, no date bound, with `ticket_id`, `summary`, `comment_count` and `assignees{id, entity{name}}`. It names the company of anyone holding open work with nothing resolved in the window, and serves the Key wins in-flight candidates. The Open now figures themselves come from the count
- **Key wins candidates**: `status_id:6`, `has_comments:true`, resolved inside the quarter, carrying `summary`, `comment_count` and `comments` inline, rather than widening the Resolved pull
- **Shortlist comments**: `ticket_ids:[the in-flight candidates you chose]` with the `comments` sub-field, since Open now carries their titles but not their histories
- **Photos**: `ticket_ids:[every ticket the chosen wins link]` with the `attachments` sub-field, once the wins are settled. `references/actions-and-wins/key-wins.md` carries the fields and what to do with the photos

A response too large to return inline comes back as a file, with its path. Read it with `jq` or a short python script rather than re-fetching it in smaller pages.

Then, on the rows:

- `created_at` and `resolved_at` come back as UTC instants while the `_local` filters read site time, so convert before bucketing by month or a late-evening ticket lands in the wrong one. Leave `orderBy` alone, it errors; sort the rows yourself
- Drop status Not Doing throughout. Status ids where a filter needs them: 1 New, 3 In Progress, 6 Closed, 7 On Hold, 8 Not Doing. `count_tickets` takes the same statuses by name: `open`, `in_progress`, `closed`, `on_hold`, `not_doing`
