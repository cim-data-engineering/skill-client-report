---
name: client-report
description: Generates a client-facing quarterly building performance review for a PEAK site - analytics overview, operational impact metrics, equipment health and indoor environment snapshots, monthly trends, alerts resolved with the actions leaderboard and key wins, and equipment run hours against working hours, as a self-contained print-ready HTML page, asking up front which sections to include and building only those. Use this whenever the user runs the /client-report slash command or asks for a client report, a quarterly or site building performance review, a site performance report from PEAK, or a report to send a facilities manager or building owner. Do not auto-trigger on general PEAK questions or ticket workflows.
---

# Client Report

A quarterly building performance review for one PEAK site: a self-contained A4 print-first HTML page the partner hands to a facilities manager. The reader chooses which sections it carries, and that choice decides what you fetch and what the page shows. A section that is out should cost nothing.

Every figure, row, series, link, date line and methodology note comes from the section scripts. Your part is the PEAK calls, the key wins and the prose: the scripts exist so that no run works out a number, writes a derivation or reads the template, which is where the time used to go.

## Build order

Work in one directory, `report/` below.

1. **Resolve the site and the sections**: [Section selection](#section-selection). Call `search_sites(keyword:"<site>", include_working_hours:true)` and `who_am_i` together, and save the `search_sites` response as `report/site.json`. Nothing else is fetched before the sections settle.
2. **Plan**: `python3 scripts/report.py plan report --site report/site.json --author "<who_am_i user_name>" --sections <names>`. It fixes the quarter from today in site time and prints every call the sections need, each with the file under `report/peak/` its response is saved as.
3. **Fetch**: make every printed call in one parallel batch, exactly as printed. Save each response the plan lists to save as its file: an offloaded one by copying the file you were handed, an inline one by writing it to its file exactly as returned, one file per response. Those responses hold counts, scores, ids and type, level or company names only. The plan lists the key win candidate pulls apart: read those where they come back and never save them, since they carry what people wrote on the tickets. Then `python3 scripts/report.py next report`, and make whatever it prints the same way until it says there are no more calls.
4. **Bundle**: `python3 scripts/report.py bundle report` writes every figure into `report/data.json`, and `report/facts.md`: the facts each note is written from, and the prose slots to fill.
5. **Write**: `report/prose.json`, one entry per slot `facts.md` names, by [Writing the narrative](#writing-the-narrative) and the "What you write" part of each chosen section's reference. The rest of a reference is what its script already did; read it only to answer a question it raises. With Actions and key wins in, choose the wins from the two candidate pulls and write `report/wins.json`; `next` then prints the impact and photo calls for them, and once those are saved, the level call. Make those, run `python3 references/actions-and-wins/scripts/key_wins.py photos report`, look at the one numbered contact sheet it makes per win, and add your picks to `wins.json`.
6. **Fill and check**: `python3 scripts/report.py fill report` fills the report, saves every photo tile as it prints, and runs the check. Look at the tiles. Then say in chat whatever it lists, name the sections left out, and hand over the file.

No browser render, screenshot or chart patch is needed: the fill script lays out every table and chart from the data, keeps labels clear of each other and scales each chart to its own range, and `check` catches anything left behind.

## Section selection

Ask before fetching anything. The masthead and [Analytics overview](#analytics-overview) always render. The four sections below are the reader's choice, and each owns a set of parts that come and go together: its operational impact rows, its own section, its monthly trend, their links and its notes-band items.

Ask with one `AskUserQuestion` call and one multi-select question, header "Sections": "Which sections should the report cover from last quarter?" Four options is the tool's limit, and four is the whole list. Describe each by what it adds:

| Choice                | `--sections` name    | Folder under `references/` | Adds                                                                                                                                       |
| --------------------- | -------------------- | -------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| Equipment health      | `equipment-health`   | `equipment-health/`        | the equipment health score, automated checks and labor cost avoided rows; health by equipment type; the score and checks trends            |
| Indoor environment    | `indoor-environment` | `indoor-environment/`      | the thermal comfort row, comfort by level, the six month comfort trend                                                                     |
| Actions and key wins  | `actions-and-wins`   | `actions-and-wins/`        | the faults resolved row with verified recovery, six months of raised vs resolved, who closed the work, and the key wins: repairs made plus live work the owner should see |
| Equipment run hours   | `run-hours`          | `run-hours/`               | when each unit of plant ran across the last full week of the quarter, against the site's working hours                                    |

Each folder holds the section's reference and a `scripts/` folder with its arithmetic. Actions and key wins is one choice with two references, `alerts-resolved.md` and `key-wins.md`, because the two answer the same question from either end and share their pulls. `references/overview/` is the part every report carries.

**Rules:**

- Everything is included by default. A dismissed prompt, an unanswered question, or an invocation naming only a site gets the full report
- Skip the prompt when the invocation already names the sections ("/client-report Skyline Tower: equipment health and key wins only") and state the resolved list in your reply instead
- Resolve the list before the first PEAK call. A section that is out is never fetched
- [Operational impact](#operational-impact) and the [Notes band](#notes-band) are frames around rows and items the sections own, so they render only when a section that owns one is in. The scaffold builds it that way
- Never leave behind an empty section, a header with no content, a link to a section that is out, or a note explaining a number the report no longer shows. The scripts handle the parts they know about; check the prose yourself
- Three things can come up empty after the fetch, and only the fetch can tell: Actions and key wins when nothing was resolved in the window, Key wins alone when no win qualifies, and run hours when no plant carries a sensor that shows it running. The scripts leave the section out and `facts.md` says why; say so in chat, not on the page

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

The overview script fills every slot below; these are the rules it follows.

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
- **A section that was left out**: run the build again in a fresh directory with the report's full new list, copying `prose.json` and `wins.json` across, so only the new section's prose is left to write. The calls are cheap and the bundle rebuilds in seconds
- **A visual or structural change**, such as a new component, a table re-laid out or a different chart form: read `DESIGN.md`. `## Colors` and `## Typography` for the tokens and their roles, `## Components` for what a component owes, `## Layout` for the print rules. The rendered file carries the CSS but not the reasoning behind it
- **A rebrand**: `BRAND.md` and the logo assets it names, per [Output & theming](#output--theming). Both files stay at the repo root. The tokens sit in one `:root` block and the masthead logo is one inlined SVG, so this is a handful of edits on the file you already have

## Newly onboarded sites

A site can have less history than the window asks for, and `facts.md` says so when a section's six-month series comes back short. The site went live inside the window, and the report covers what exists.

- Trim both windows to the months that returned data, still whole months only. The month a site went live in is not a complete month for it unless it went live on the 1st, so drop it
- Say it once, in the masthead: "Reporting period: 1 – 31 August 2026, monitoring live since 14 July 2026". The reader needs to know the report is short because the site is new, not because something failed. Don't repeat it section by section
- A movement needs two months. With one, state the score and drop the delta. "Up 0.00 pp" against a month that does not exist is worse than no delta. That covers the heatmap Chg column too: with one month, drop the column, and sort the rows by score with the lowest first, so the plant needing attention leads
- A trend needs three points. With fewer, drop the trend chart and keep the snapshot; two months drawn as a line invites the reader to extend it. Where that empties a trends section, delete the section
- Delete the surplus month columns from the heatmap header and every row, so the table is only as wide as the data
- An equipment type or a level can start later than the site did, when new rules go on old plant. Keep its cell so the row stays the table's width, as `<td class="c none">&mdash;</td>`: no band class, so no fill, which is what a month with no reading should look like. Dash its Chg too, and say in the section note when its rules began scoring
- Prorate the labor cost model over the days actually monitored, not the calendar quarter, or it credits the monitoring with time it wasn't running
- A gap in the middle of a series is an outage, not onboarding. So is a month that scored off a fraction of the usual rules. One rule against 850 either side is an outage wearing a score. Treat both alike: plot the months that exist, leave the gap visible, and say so in the chart note

## Output & theming

One self-contained A4 print-first HTML file: all CSS inline, charts as inline SVG, no JS. The scaffold supplies the stylesheet and every component, and `fill_report.py` draws every chart from the bundle, so the geometry is never yours to compute:

- Chart series colours are CSS classes backed by `:root` tokens (`.bar-primary`, `.bar-benchmark`, `.series-line`, `.pt`, `.sw-primary`, `.sw-benchmark`), never hardcoded hex, because SVG presentation attributes cannot read `var()`. Heatmap band fills work the same way (`.b4`, `.b3`, `.b2`, `.b1` for Excellent, Good, Average, Poor)
- Section headers are three stacked lines: the section name as an uppercase eyebrow in `primary`, the statement beneath it as the `h2` headline, and the date line as a muted byline. The statement is the headline, never the section name

Resolve the theme in this order:

1. **The scaffold**: its `:root` and component CSS are DESIGN.md compiled. A default CIM build needs nothing further; don't re-derive values the file already carries
2. **`BRAND.md`** (repo root): if present, apply its YAML frontmatter overrides by editing `:root`, the `@font-face` block and the masthead logo. Honor only these keys and ignore everything else:
  - `name`, `service-name`: replace the company name and service name defaults in [Report title](#report-title). The scripts read these two and fill the masthead with them
  - `colors:`: `primary`, `primary-container`, `on-primary-container`, `secondary`, `on-secondary`, `on-secondary-muted`, `chart-benchmark`, `text-heading` only
  - `fonts:`: `display`, `text`, `mono` family swaps mapped onto the DESIGN.md typography roles (display → h1/h2/card-title/metric; text → body/body-sm/label/eyebrow; mono → mono). Sizes, weights and line-heights always keep DESIGN.md values. Families on Google Fonts load from the CDN, and the `font-family` stack carries the offline case; a family that is not on Google Fonts is embedded from `assets/fonts` as a base64 data URI, since a relative font path does not survive the report leaving this repo
  - `logos:`: `reversed` (masthead) and `full-color`, paths to partner files. Inline the referenced SVG contents (data URI for PNG) so the report stays self-contained
3. **`DESIGN.md`** (repo root, alongside BRAND.md): read its `## Colors` and `## Typography` sections when an override needs the role mapping, and the rest when you need a component the scaffold has no CSS for or are changing the design itself, per [After the render](#after-the-render). DESIGN.md is the source of truth; the scaffold is its output
4. A missing BRAND.md, or any key left commented or absent, keeps the CIM default. An untouched fork must render identically to CIM's own output

Derived rules when overrides are active:

- `secondary` overridden → re-derive the `shadow` token as the new `secondary` hue at 8% opacity
- Any brand override active → platform strings read `PEAK` (drop the CIM prefix) in the masthead metadata row and footer. `Powered by PEAK` is always kept, in every brand
- No overrides → keep `CIM PEAK` and the CIM masthead logo the scaffold already carries from `assets/logo-white.svg`

## How the scripts fetch

A full report is about forty calls, most of them small counts, and a long session has a call budget. Each section's `calls()` is written to answer the section in one request, so the discipline holds without you policing it: rows for a window, not a month; a set of ids, never one at a time; a count wherever a count is all that is needed, from `count_tickets`, `count_indoor_environment_zones` or `pagination.total`; and everything else derived locally from rows already held. Any change to a section's calls goes in its script, with the reason in its reference's Data block.

Every window closes on the **last complete month**, so nothing in the report covers a part-month. A quarterly review should read as of the quarter, not as of the day it was generated, and equipment health scores are stored pre-aggregated on month boundaries, so a mid-month bound forces a raw scan. The **quarter** is the three complete months ending on the last complete month, and the snapshots use it column for column. The **6 month window** is the six complete months ending there, which the trends use. Run hours takes the last full Monday-to-Sunday week inside the quarter.

Links come back with the data, so the report does not build them. `search_equipment_health_scores`, `search_indoor_environment`, `search_alert_tickets` and `search_action_tickets` each return `platform_link`: a section link comes off one of that section's quarter calls, a chart's source link off its 6 month call, and a row link narrows the section link with the row's own filter, `&equipment_type_ids={id}` or `&level_ids={id}`. Where a link a section needs comes back null, the script drops it; say so in chat rather than assembling a URL. The actions leaderboard and the run hours unit charts are the only links built from parts, since no call returns those pages.

A large response is not a failure. Past roughly 60,000 characters the gateway writes the result to a file and hands you the path: copy it under its name and the scripts read it from there. Status ids where a filter needs them: 1 New, 3 In Progress, 6 Closed, 7 On Hold, 8 Not Doing, which every count and pull leaves out.
