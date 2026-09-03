---
name: client-report
description: Generates a client-facing quarterly building performance review for a PEAK site — analytics overview, operational impact metrics, equipment health and indoor environment snapshots, monthly trends, alerts resolved with the assignee leaderboard, and key wins — as a self-contained print-ready HTML page, asking up front which sections to include and building only those. Styled per the design system in DESIGN.md with partner brand overrides from BRAND.md (defaults to CIM when no overrides are set). Use this whenever the user runs the /client-report slash command or asks for a client report, a quarterly or site building performance review, a site performance report from PEAK, or a report to send a facilities manager or building owner. Do not auto-trigger on general PEAK questions or ticket workflows.
---

# Client Report

A quarterly building performance review for one PEAK site, delivered as a self-contained A4 print-first HTML page that the partner hands to a facilities manager. The reader chooses which sections it carries, and that choice narrows everything downstream — the PEAK calls, the markup, the references you read. A section that is out should cost nothing.

## Build order

1. **Resolve the site and the sections** — [Section selection](#section-selection). Nothing is fetched before this settles, because the selection decides what there is to fetch.
2. **Scaffold the file** — `python3 scripts/build_report.py scaffold --sections equipment-health,key-wins --out skyline-q3.html`. It copies the stylesheet, the always-on sections and only the parts the chosen sections own — in report order, so the file already reads top down — dropping the operational impact rows, section links and notes items of everything left out as it goes. The scaffold *is* `assets/reference-report.html`, filtered — so don't read that file or hand-write its CSS. `scaffold` with no `--sections` gives you everything; `parts` lists what exists.
3. **Read one reference per chosen section** — `references/<section>.md`. Each carries its own PEAK calls, table spec, benchmark, links and notes items. The others describe sections you are not building; leave them unread.
4. **Fetch** — [Shared data](#shared-data), then the Fetch block of each chosen reference. Nothing else. Most of these are aggregate calls that answer a whole section in one request; going back for rows you can derive from what you already hold is the main way this report gets slow.
5. **Fill the scaffold in place** — every figure, name, date and link in it is sample data for a different building. Read it from the masthead down rather than whole (offset past the `</style>` line, or grep to the section you are filling): the stylesheet needs no edits unless a brand override is active. Then work section by section with edits, so the CSS and component markup stay exactly as designed and you never re-emit them.
6. **Check and hand over** — `python3 scripts/build_report.py check <file>` catches sample values, unresolved placeholders and markers left behind. It is a backstop, not a substitute for reading the numbers. Then name the sections you left out, so the omission reads as asked for rather than missing.

## Section selection

Ask before fetching anything. The masthead and [Analytics overview](#analytics-overview) always render — the four sections below are the reader's choice, and each owns a slice that comes or goes whole: its operational impact rows, its section, its monthly trend, their links, and its notes-band items.

Ask with one `AskUserQuestion` call carrying one multi-select question. Four options is the tool's limit and also the whole list, so nothing needs splitting across two questions:

| Question                                                   | Header   | Options (`multiSelect: true`)                                                          |
| ---------------------------------------------------------- | -------- | -------------------------------------------------------------------------------------- |
| Which sections should the report cover from last quarter?   | Sections | Equipment health · Indoor environment · Actions resolved and leaderboard · Key wins   |

Describe each option by what it adds, so the reader can see what leaving it out costs:

| Choice                           | `--sections` name    | Reference                          | Adds                                                                                                                              |
| -------------------------------- | -------------------- | ---------------------------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| Equipment health                 | `equipment-health`   | `references/equipment-health.md`   | the equipment health score, automated checks and labor cost avoided rows; health by equipment type; the score and checks trends   |
| Indoor environment               | `indoor-environment` | `references/indoor-environment.md` | the thermal comfort row, comfort by level, the six month comfort trend                                                            |
| Actions resolved and leaderboard | `alerts-resolved`    | `references/alerts-resolved.md`            | the faults resolved row with verified recovery, six months of raised vs resolved, and who closed the work                         |
| Key wins                         | `key-wins`           | `references/key-wins.md`           | what physically changed in the building, evidenced from action comments                                                           |

**Rules:**

- Everything is included by default. A dismissed prompt, an unanswered question, or an invocation naming only a site gets the full report
- Skip the prompt when the invocation already names the sections ("/client-report Skyline Tower — equipment health and key wins only") and state the resolved list in your reply instead
- Resolve the list before the first PEAK call. A section that is out is never fetched
- [Operational impact](#operational-impact) and the [Notes band](#notes-band) are frames around rows and items the sections own, so they render only when at least one of the first three sections is in. Key wins on its own gives a masthead, the analytics overview and the wins — a short report, but an honest one, and the scaffold builds it that way
- The notes band is an `<ol>`, so items dropped with their section renumber themselves. Trim the shared current month item to the series that survive
- Never leave behind an empty section, a header with no content, a link to a section that is out, or a note explaining a number the report no longer shows. The scaffold handles this for the parts it knows; the prose is yours to keep honest

## What always renders

### Report title

- {Site name} Quarterly Building Performance Review
- Prepared by: {Company name} {Company service name}. Powered by PEAK
- Reporting period: last 3 months date range
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

All five render whatever the section selection, including thermal zones when indoor environment is out. This section is the monitoring footprint, not a summary of the sections below it — it is what the client is paying for, and it stands on its own.

## Operational impact

What that monitoring delivered this quarter
Date: last 3 months

A frame around rows the sections own: three from equipment health, one from indoor environment, one from alerts resolved. Their specs live in those references. The section renders when at least one of them is in and drops when none is.

**Display:**

- No red in this section. An improvement takes the positive chip, a decline or a flat result takes the muted chip — never the negative one. State a fall plainly in the figure, the glyph and the word: the section carries custodianship to the owner, so a decline is reported, not colour coded. Red stays available to the snapshot tables and charts below, where the detail belongs
- Keep the surviving rows in this order: equipment health score, thermal comfort, automated checks, labor cost avoided, faults resolved. Rows stack, so a removed row costs no layout work
- Where a row states a movement, the start month is the first month of the reporting quarter, so it reads as where the quarter opened against where the site is running now

## Notes band

Numbered methodology items in report order, each owned by the section it explains, plus one shared item:

- **The current month** — every monthly series runs to the issue date, so the last bucket holds part of a month. Volume series are short there by construction; scores are rates over whatever days exist, so they are not. Name only the series the report actually shows

## After the render

A follow-up on a report that already exists is not a rebuild. Match the reading to the ask:

- **A number, a date, a name, a sentence** — edit the file. One PEAK call if the answer needs one, no references, no `DESIGN.md`
- **A section that was left out** — `python3 scripts/build_report.py part key-wins --sections <the report's full new list>` prints that part's markup on its own. Paste it in report order, read its reference, fetch only its calls. Re-scaffolding would throw away the report you have. Where the new section owns operational impact rows or notes items, add those too; if the report has neither of those frames, it was built with none of the three data sections in, so scaffold a fresh file instead
- **A visual or structural change** — a new component, a table re-laid out, a different chart form — is where `DESIGN.md` earns its read: `## Colors` and `## Typography` for the tokens and the roles they fill, `## Components` for what a component owes, `## Layout` for the print rules. The rendered file carries the CSS but not the reasoning, so changing the design without it is guesswork
- **A rebrand** — `BRAND.md` and the logo assets it names, per [Output & theming](#output--theming). Both files stay at the repo root because that is where the brand overlay skills write them, and because a rebrand reads them as a pair. All the tokens sit in one `:root` block and the masthead logo is one inlined SVG, so this stays a handful of edits on the file you already have

## Shared data

Windows, named once because the references reuse them: the **quarter** is the last 3 months; the **4 month window** is the last 3 complete months plus the current month to date, which the snapshots use; the **7 month window** is the last 6 complete months plus the current month to date, which the trends use. Every monthly series ends on the current month to date, so trends and snapshots share their closing bucket and must not disagree on it.

Always:

- Author — `who_am_i`, the user's full name for the masthead
- Site facts — `search_sites` omits these, so use GraphQL: `platform.sites` args `{site_id}` fields `[site_name, photo_url, building_size, monetary_currency]`
- Counts for the analytics overview — never fetch rows. Call with `limit:1` and read `pagination.total`: `search_rules(task_state:running)`, `search_favourites`, `search_equipment` (subtract system types 21,37,69,70,87,105,114), `search_alert_tickets`
- Thermal zones — `search_favourites(metadata_name:"%Zone Temperature", limit:1)`, read `pagination.total`. Anchor the wildcard at the end: `%Zone Temp%` also matches setpoint points and roughly doubles the count. Four point names mean zone temperature (`VAV-Zn-T`, `PAC-Zn-T`, `Un-Zn-T`, `ZnT`), so filter on name, not `metadata_codes`

Only when Actions resolved and leaderboard, or Key wins, is in — one pull serves both, so fetch it once and skip it entirely when neither is:

- `tickets.tickets`, `type:"escalated"`, `ticket_archived:false`, `limit:400`, date bounds `*_at_local_*` over the 7 month window
- Fields: `ticket_id, created_at, resolved_at, status_id, assignees{id,firstname,lastname}, ticket_links{ticket(type:alert){ticket_id, rule_id}}`
- Bucket by site-local month; drop `status_id:8`; weight by linked alerts whose rule is still running. An action with no linked alert counts 1; an action whose every linked alert is on a stopped rule counts 0
- Flag any action closing many alerts at once — it distorts the month
- Status ids: 1 New, 3 In Progress, 6 Closed, 7 On Hold, 8 Not Doing

## Output & theming

One self-contained A4 print-first HTML file — all CSS inline, charts as hand-authored inline SVG, no JS. The scaffold supplies the stylesheet and every component, so this is a handful of edits rather than a rebuild:

- The scaffold's chart SVGs are hand-authored at six columns and the monthly trends run seven, so recompute x positions across the plot width rather than reusing the coordinates and dropping the last month
- Chart series colours are CSS classes backed by `:root` tokens (`.bar-primary`, `.bar-benchmark`, `.series-line`, `.pt`, `.sw-primary`, `.sw-benchmark`), never hardcoded hex — SVG presentation attributes cannot read `var()`. Heatmap band fills work the same way (`.b4`, `.b3`, `.b2`, `.b1` for Excellent, Good, Average, Poor), so a brand that swaps its measurement colours recolours both heatmaps without touching markup
- Section headers are three stacked lines: the section name as an uppercase eyebrow in `primary`, the statement beneath it as the `h2` headline, and the date line as a muted byline. The statement is the headline, never the section name

Resolve the theme in this order:

1. **The scaffold** — its `:root` and component CSS are DESIGN.md compiled. A default CIM build needs nothing further, and re-deriving values the file already carries is wasted work
2. **`BRAND.md`** (repo root) — if present, apply its YAML frontmatter overrides by editing `:root`, the `@font-face` block and the masthead logo. Honor only these keys and ignore everything else:
   - `name`, `service-name` — replace the company name and service name defaults in [Report title](#report-title)
   - `colors:` — `primary`, `primary-container`, `on-primary-container`, `secondary`, `on-secondary`, `on-secondary-muted`, `chart-benchmark`, `text-heading` only
   - `fonts:` — `display`, `text`, `mono` family swaps mapped onto the DESIGN.md typography roles (display → h1/h2/card-title/metric; text → body/body-sm/label/eyebrow; mono → mono). Sizes, weights and line-heights always keep DESIGN.md values. Families on Google Fonts load CDN-first with `assets/fonts` fallback; otherwise local `assets/fonts` only
   - `logos:` — `reversed` (masthead) and `full-color`, paths to partner files. Inline the referenced SVG contents (data URI for PNG) so the report stays self-contained
3. **`DESIGN.md`** (repo root, alongside BRAND.md) — read its `## Colors` and `## Typography` sections when an override needs the role mapping, and the rest when you need a component the scaffold has no CSS for or are changing the design itself, per [After the render](#after-the-render). It is the source of truth; the scaffold is only its output
4. A missing BRAND.md, or any key left commented or absent, keeps the CIM default — an untouched fork must render identically to CIM's own output

Derived rules when overrides are active:

- `secondary` overridden → re-derive the `shadow` token as the new `secondary` hue at 8% opacity
- Any brand override active → platform strings read `PEAK · Site {id}` (drop the CIM prefix) in the masthead metadata row and footer. `Powered by PEAK` is always kept, in every brand
- No overrides → keep `CIM PEAK` and the CIM masthead logo the scaffold already carries from `assets/logo-white.svg`
