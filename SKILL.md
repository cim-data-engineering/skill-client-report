---
name: client-report
description: Generates a client-facing quarterly building performance review for a PEAK site — analytics overview, operational impact metrics, equipment health and indoor environment snapshots, monthly trends, alerts resolved with the assignee leaderboard, and key wins — as a self-contained print-ready HTML page, asking up front which sections to include and building only those. Styled per the design system in DESIGN.md with partner brand overrides from BRAND.md (defaults to CIM when no overrides are set). Use this whenever the user runs the /client-report slash command or asks for a client report, a quarterly or site building performance review, a site performance report from PEAK, or a report to send a facilities manager or building owner. Do not auto-trigger on general PEAK questions or ticket workflows.
---

# Client Report

A quarterly building performance review for one PEAK site: a self-contained A4 print-first HTML page the partner hands to a facilities manager. The reader chooses which sections it carries, and that choice decides what you fetch, what markup you build and which references you read. A section that is out should cost nothing.

## Build order

1. **Resolve the site and the sections** — [Section selection](#section-selection). Nothing is fetched before this settles, because the selection decides what there is to fetch.
2. **Scaffold the file** — `python3 scripts/build_report.py scaffold --sections equipment-health,key-wins --out skyline-q3.html`. It copies the stylesheet, the always-on sections and the parts the chosen sections own, in report order, and drops the operational impact rows, section links and notes items of everything left out. The scaffold is `assets/reference-report.html` filtered, so don't read that file or hand-write its CSS. `scaffold` with no `--sections` gives you everything; `parts` lists what exists.
3. **Read one reference per chosen section** — `references/<section>.md`. Each carries its own PEAK calls, table spec, benchmark, links and notes items. The others describe sections you are not building; leave them unread.
4. **Fetch** — [Shared data](#shared-data), then the Fetch block of each chosen reference. Nothing else. Most are aggregate calls that answer a whole section in one request, so don't go back for rows you can derive from what you already hold.
5. **Fill the scaffold in place** — every figure, name, date and link in it is sample data for a different building. Read it from the masthead down rather than whole (offset past the `</style>` line, or grep to the section you are filling): the stylesheet needs no edits unless a brand override is active. Then work section by section with edits, so the CSS and component markup stay exactly as designed and you never re-emit them. Two slots are easy to miss: the `<title>` in the shell, and the second `seclinks` block under the snapshot table.
6. **Check and hand over** — `python3 scripts/build_report.py check <file>` catches sample values, unresolved placeholders and markers left behind. It is a backstop, not a substitute for reading the numbers. Then name the sections you left out, so the reader knows the omission was asked for.

## Section selection

Ask before fetching anything. The masthead and [Analytics overview](#analytics-overview) always render. The four sections below are the reader's choice, and each owns a set of parts that come and go together: its operational impact rows, its own section, its monthly trend, their links and its notes-band items.

Ask with one `AskUserQuestion` call and one multi-select question. Four options is the tool's limit, and four is the whole list:

| Question                                                   | Header   | Options (`multiSelect: true`)                                                          |
| ---------------------------------------------------------- | -------- | -------------------------------------------------------------------------------------- |
| Which sections should the report cover from last quarter?   | Sections | Equipment health · Indoor environment · Actions resolved and leaderboard · Key wins   |

Describe each option by what it adds:

| Choice                           | `--sections` name    | Reference                          | Adds                                                                                                                              |
| -------------------------------- | -------------------- | ---------------------------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| Equipment health                 | `equipment-health`   | `references/equipment-health.md`   | the equipment health score, automated checks and labor cost avoided rows; health by equipment type; the score and checks trends   |
| Indoor environment               | `indoor-environment` | `references/indoor-environment.md` | the thermal comfort row, comfort by level, the seven month comfort trend                                                            |
| Actions resolved and leaderboard | `alerts-resolved`    | `references/alerts-resolved.md`    | the faults resolved row with verified recovery, seven months of raised vs resolved, and who closed the work                         |
| Key wins                         | `key-wins`           | `references/key-wins.md`           | what physically changed in the building, evidenced from action comments                                                           |

**Rules:**

- Everything is included by default. A dismissed prompt, an unanswered question, or an invocation naming only a site gets the full report
- Skip the prompt when the invocation already names the sections ("/client-report Skyline Tower — equipment health and key wins only") and state the resolved list in your reply instead
- Resolve the list before the first PEAK call. A section that is out is never fetched
- [Operational impact](#operational-impact) and the [Notes band](#notes-band) are frames around rows and items the sections own, so they render only when at least one of the first three sections is in. Key wins on its own gives the masthead, the analytics overview and the wins. The scaffold builds it that way
- The notes band is an `<ol>`, so items dropped with their section renumber themselves. Trim the shared reporting-window item to the series that survive
- Never leave behind an empty section, a header with no content, a link to a section that is out, or a note explaining a number the report no longer shows. The scaffold handles the parts it knows about; check the prose yourself
- Key wins is the only section that can come up empty after the fetch, because whether a closure qualifies is only visible in its comments. If none qualifies, delete the section from the built file and say so in chat, not on the page. `references/key-wins.md` has the rule

## What always renders

### Report title

- {Site name} Quarterly Building Performance Review
- Prepared by: {Company name} {Company service name}. Powered by PEAK
- Reporting period: the quarter as a date range, per [Shared data](#shared-data), or the site's own coverage per [Newly onboarded sites](#newly-onboarded-sites)
- Author: full name of the logged-in PEAK MCP user, from `who_am_i` — always present, never omitted or substituted
- Issue date: issue date
- Disclaimer, verbatim, below the masthead metadata row: "AI was used to help compile this report. All figures, analysis and recommendations were human-reviewed."
- Company name default "CIM" unless `name` is set in `BRAND.md` or given by the user
- Company service name default "Data Driven Operations" unless `service-name` is set in `BRAND.md` or given by the user
- Site `photo_url`: square, right of title block

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

All five render whatever the selection, including thermal zones when indoor environment is out. This section is the monitoring footprint, not a summary of the sections below it, so it stands on its own.

## Operational impact

What that monitoring delivered this quarter
Date: the quarter

The rows belong to the sections — three to equipment health, one to indoor environment, one to alerts resolved — and each is specified in that reference. The section renders when at least one of them is in, and drops when none is.

**Display:**

- No red in this section. An improvement takes the positive chip; a decline or a flat result takes the muted chip, never the negative one. State a fall plainly in the figure, the glyph and the word — reported, not colour coded. Red stays available to the snapshot tables and charts below, where the detail belongs
- Keep the surviving rows in this order: equipment health score, thermal comfort, automated checks, labor cost avoided, faults resolved. Rows stack, so a removed row costs no layout work
- Where a row states a movement, it runs from the quarter's first month to its last: the reporting period, and nothing outside it

## Notes band

Numbered methodology items in report order, each owned by the section it explains, plus one shared item:

- **The reporting window** — every monthly series closes on the last complete month, so no column or bar covers a part-month and the volume series can be read against each other directly. Name the series the report actually shows, and the three complete months the quarter covers

## After the render

A follow-up on a report that already exists is not a rebuild. Match the reading to the ask:

- **A number, a date, a name, a sentence** — edit the file. One PEAK call if the answer needs one, no references, no `DESIGN.md`
- **A section that was left out** — `python3 scripts/build_report.py part key-wins --sections <the report's full new list>` prints that part's markup on its own. Paste it in report order, read its reference, fetch only its calls. Re-scaffolding would throw away the report you have. Where the new section owns operational impact rows or notes items, add those too; if the report has neither of those frames, it was built with none of the three data sections in, so scaffold a fresh file instead
- **A visual or structural change** — a new component, a table re-laid out, a different chart form — read `DESIGN.md`: `## Colors` and `## Typography` for the tokens and their roles, `## Components` for what a component owes, `## Layout` for the print rules. The rendered file carries the CSS but not the reasoning behind it
- **A rebrand** — `BRAND.md` and the logo assets it names, per [Output & theming](#output--theming). Both files stay at the repo root: that is where the brand overlay skills write them, and a rebrand reads them as a pair. The tokens sit in one `:root` block and the masthead logo is one inlined SVG, so this is a handful of edits on the file you already have

## Shared data

Every window closes on the **last complete month**, so nothing in the report covers a part-month. Two reasons: a quarterly review should read as of the quarter, not as of the day it was generated; and equipment health scores are stored pre-aggregated on month boundaries, so a mid-month bound forces a raw scan and a wide call is then refused for scanning too many rows.

Two windows, named here because the references reuse them. The **quarter** is the three complete months ending on the last complete month, and the snapshots use it column for column. The **7 month window** is the seven complete months ending there, which the trends use, so a trend carries the quarter plus the four months before it. Both close on the same month, so trends and snapshots share that bucket and must not disagree on it.

The references build PEAK links from these, so substitute rather than hardcoding dates:

| Placeholder              | Value                                                   |
| ------------------------ | ------------------------------------------------------- |
| `{{quarter_start}}`      | first day of the quarter, `YYYY-MM-DD`                  |
| `{{quarter_end}}`        | last day of the quarter — the last complete month's end |
| `{{quarter_last_month}}` | first day of that last month, for `summary_ts`          |
| `{{trend_start}}`        | first day of the 7 month window                         |

Always:

- Author — `who_am_i`, the user's full name for the masthead
- Site facts — `search_sites` omits these, so use GraphQL: `platform.sites` args `{site_id}` fields `[site_name, photo_url, building_size, monetary_currency]`
- Counts for the analytics overview — never fetch rows. Call with `limit:1` and read `pagination.total`: `search_rules(task_state:running)`, `search_favourites` for sensors, and `search_equipment` twice, once plain and once filtered to system types 21,37,69,70,87,105,114 so you can subtract them
- Thermal zones — `search_favourites(metadata_codes:["VAV-Zn-T","PAC-Zn-T","Un-Zn-T","ZnT"], limit:1)`, read `pagination.total`. Filter on the codes, not the name. `%Zone Temperature` also matches `Un-MxZT`, the per-AHU maximum zone temperature, and `EF-ZnT` on exhaust fans; neither is a thermal zone, and on a small site the AHU aggregates alone inflated the count by 14%. Never widen to `%Zone Temp%` either — that picks up setpoints and roughly doubles it. Codes are case-sensitive and an unknown one matches nothing silently, so a zero here at a site that plainly has thermal comfort data means the list is wrong for that site, not that the site has no zones

Only when Actions resolved and leaderboard, or Key wins, is in — one pull serves both, so fetch it once and skip it entirely when neither is:

- `tickets.tickets`, `type:"escalated"`, `ticket_archived:false`, `limit:400`, date bounds `*_at_local_*`. Use the 7 month window for the monthly buckets and the leaderboard. When Key wins is the only section in, narrow it to the quarter — that is all it shortlists from
- Fields: `ticket_id, created_at, resolved_at, status_id, assignees{id,firstname,lastname}, ticket_links{ticket(type:alert){ticket_id, rule_id}}`
- Bucket by site-local month; drop `status_id:8`; weight by linked alerts whose rule is still running. An action with no linked alert counts 1; an action whose every linked alert is on a stopped rule counts 0
- Flag any action closing many alerts at once — it distorts the month
- Status ids: 1 New, 3 In Progress, 6 Closed, 7 On Hold, 8 Not Doing

## Newly onboarded sites

A site can have less history than the window asks for. Read that from the first fetch rather than assuming: if the earliest month returned by the `site` × `month` call is later than the window start, the site went live inside the window and the report covers what exists.

- Trim both windows to the months that returned data, still whole months only. The month a site went live in is not a complete month for it unless it went live on the 1st, so drop it
- Say it once, in the masthead: "Reporting period: 1 – 31 August 2026, monitoring live since 14 July 2026". The reader needs to know the report is short because the site is new, not because something failed. Don't repeat it section by section
- A movement needs two months. With one, state the score and drop the delta — "up 0.00 pp" against a month that does not exist is worse than no delta. That covers the heatmap Chg column too: with one month, drop the column. The score still stands on its own
- A trend needs three points. With fewer, drop the trend chart and keep the snapshot; two months drawn as a line invites the reader to extend it. Where that empties a trends section, delete the section
- Delete the surplus month columns from the heatmap header and every row, so the table is only as wide as the data
- Prorate the labor cost model over the days actually monitored, not the calendar quarter, or it credits the monitoring with time it wasn't running
- A gap in the middle of a series is an outage, not onboarding. Plot the months that exist, leave the gap visible, and say so in the chart note

## Output & theming

One self-contained A4 print-first HTML file — all CSS inline, charts as hand-authored inline SVG, no JS. The scaffold supplies the stylesheet and every component, so this is a handful of edits rather than a rebuild:

- The scaffold's chart SVGs already run seven columns at x = 80, 172 … 632, so the x positions carry over. The y geometry does not: recompute every point, bar top, benchmark line and value label from your own data range, and pick the range from the data plus the thresholds you are drawing. Reusing the sample's y values plots the sample's data, not yours
- Chart series colours are CSS classes backed by `:root` tokens (`.bar-primary`, `.bar-benchmark`, `.series-line`, `.pt`, `.sw-primary`, `.sw-benchmark`), never hardcoded hex — SVG presentation attributes cannot read `var()`. Heatmap band fills work the same way (`.b4`, `.b3`, `.b2`, `.b1` for Excellent, Good, Average, Poor), so a brand that swaps its measurement colours recolours both heatmaps without touching markup
- Section headers are three stacked lines: the section name as an uppercase eyebrow in `primary`, the statement beneath it as the `h2` headline, and the date line as a muted byline. The statement is the headline, never the section name

Resolve the theme in this order:

1. **The scaffold** — its `:root` and component CSS are DESIGN.md compiled. A default CIM build needs nothing further; don't re-derive values the file already carries
2. **`BRAND.md`** (repo root) — if present, apply its YAML frontmatter overrides by editing `:root`, the `@font-face` block and the masthead logo. Honor only these keys and ignore everything else:
   - `name`, `service-name` — replace the company name and service name defaults in [Report title](#report-title)
   - `colors:` — `primary`, `primary-container`, `on-primary-container`, `secondary`, `on-secondary`, `on-secondary-muted`, `chart-benchmark`, `text-heading` only
   - `fonts:` — `display`, `text`, `mono` family swaps mapped onto the DESIGN.md typography roles (display → h1/h2/card-title/metric; text → body/body-sm/label/eyebrow; mono → mono). Sizes, weights and line-heights always keep DESIGN.md values. Families on Google Fonts load CDN-first with `assets/fonts` fallback; otherwise local `assets/fonts` only
   - `logos:` — `reversed` (masthead) and `full-color`, paths to partner files. Inline the referenced SVG contents (data URI for PNG) so the report stays self-contained
3. **`DESIGN.md`** (repo root, alongside BRAND.md) — read its `## Colors` and `## Typography` sections when an override needs the role mapping, and the rest when you need a component the scaffold has no CSS for or are changing the design itself, per [After the render](#after-the-render). DESIGN.md is the source of truth; the scaffold is its output
4. A missing BRAND.md, or any key left commented or absent, keeps the CIM default — an untouched fork must render identically to CIM's own output

Derived rules when overrides are active:

- `secondary` overridden → re-derive the `shadow` token as the new `secondary` hue at 8% opacity
- Any brand override active → platform strings read `PEAK · Site {id}` (drop the CIM prefix) in the masthead metadata row and footer. `Powered by PEAK` is always kept, in every brand
- No overrides → keep `CIM PEAK` and the CIM masthead logo the scaffold already carries from `assets/logo-white.svg`
