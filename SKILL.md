---
name: client-report
description: Generates a client-facing quarterly building performance review for a PEAK site — analytics overview, operational impact metrics, equipment health snapshot and monthly trends, alerts raised vs resolved, assignee leaderboard, and key wins — styled per the design system in DESIGN.md with partner brand overrides from BRAND.md (defaults to CIM when no overrides are set). Use when the user runs the /client-report slash command or asks for a client report, quarterly building performance review, or site performance report from PEAK data. Do not auto-trigger on general PEAK questions or ticket workflows.
---

# Client Report

## Output & theming

The deliverable is a single self-contained A4 print-first HTML file — all CSS inline, charts as hand-authored inline SVG, no JS — modelled on `assets/reference-report.html`. Copy its structure, classes and chart techniques; replace the sample data. Chart series colours are CSS classes backed by `:root` tokens (`.bar-primary`, `.bar-benchmark`, `.series-line`, `.pt`, `.sw-primary`, `.sw-benchmark`), never hardcoded hex — SVG presentation attributes cannot read `var()`. Heatmap band fills are the same deal (`.b4`, `.b3`, `.b2`, `.b1` for Excellent, Good, Average, Poor), so a brand that swaps its measurement containers recolours both heatmaps without touching markup.

Resolve the theme in this order:

1. **`DESIGN.md`** — all tokens and rules. Every value defaults from here.
2. **`BRAND.md`** (repo root) — if present, apply overrides from its YAML frontmatter. Honor only these keys and ignore everything else:
   - `name`, `service-name` — replace the company name and service name defaults in [Report title](#report-title)
   - `colors:` — `primary`, `primary-container`, `on-primary-container`, `secondary`, `on-secondary`, `on-secondary-muted`, `chart-benchmark`, `text-heading` only
   - `fonts:` — `display`, `text`, `mono` family swaps mapped onto the DESIGN.md typography roles (display → h1/h2/card-title/metric; text → body/body-sm/label/eyebrow; mono → mono). Sizes, weights and line-heights always keep DESIGN.md values. Families on Google Fonts load CDN-first with `assets/fonts` fallback per DESIGN.md; otherwise local `assets/fonts` only.
   - `logos:` — `reversed` (masthead) and `full-color`, paths to partner files. Inline the referenced SVG contents (data URI for PNG) so the report stays self-contained.
3. A missing BRAND.md, or any key left commented or absent, keeps the CIM default — an untouched fork must render identically to CIM's own output.

Derived rules when overrides are active:

- `secondary` overridden → re-derive the `shadow` token as the new `secondary` hue at 8% opacity.
- Any brand override active → platform strings read `PEAK · Site {id}` (drop the CIM prefix) in the masthead metadata row and footer. `Powered by PEAK` is always kept, in every brand.
- No overrides → keep `CIM PEAK` and the CIM masthead logo inlined from `assets/logo-white.svg`.

## Sections

1. [Report title](#report-title)
2. [Analytics overview](#analytics-overview)
3. [Operational impact](#operational-impact)
4. [Equipment health snapshot](#equipment-health-snapshot)
5. [Indoor environment health snapshot](#indoor-environment-health-snapshot)
6. [Monthly equipment health](#monthly-equipment-health)
7. [Alerts raised vs resolved](#alerts-raised-vs-resolved)
8. [Assignee leaderboard](#assignee-leaderboard)
9. [Key wins](#key-wins)

Each section header renders as three stacked lines, per the reference report: the section name as an uppercase eyebrow in `primary`, the statement line beneath it as the `h2` headline, and the date line as a muted byline.

## Report title

- {Site name} Quarterly Building Performance Review
- Prepared by: {Company name} {Company service name}. Powered by PEAK
- Reporting period: last 3 months date range
- Issue date: issue date
- Company name default “CIM” unless `name` is set in `BRAND.md` or given by the user
- Company service name default “Data Driven Operations” unless `service-name` is set in `BRAND.md` or given by the user
- Site `photo_url`: square, right of title block

## Analytics overview

What we monitor at {site name}  
Date: As at {issue date}

| Display metric | Reference                      |
| -------------- | ------------------------------ |
| Building size  | Use sqm or sqft per region     |
| Equipment      | Total equipment                |
| Sensors        | Total sensors                  |
| Rules          | Total rules status running     |
| Thermal zones  | Total indoor environment zones |

## Operational impact

What that monitoring delivered this quarter  
Date: last 3 months

| Rating chip                               | Metric label                                 | Value                                                                                       | Subtitle                                                                                                                                          |
| ----------------------------------------- | -------------------------------------------- | ------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| See below equipment score benchmark       | x.x% equipment health maintained             | Site equipment health score last 3 months                                                   | Up x.x pp vs y.y% over the last 12 months                                                                                                         |
| See below thermal comfort score benchmark | x.x% thermal comfort maintained              | Site thermal comfort score last 3 months                                                    | Up x.x pp vs y.y% over the last 12 months                                                                                                         |
| Continuous                                | x automated equipment health checks ran 24/7 | Total executions last 3 months                                                              | Averaging x monthly checks across y scored rules                                                                                                  |
| Modelled                                  | $x labor cost avoided                        | See below labor cost avoided model                                                          | x hours and y.y working days of inspection time                                                                                                   |
| See below alert recovery benchmark        | x faults resolved with x% verified recovery  | Resolved alerts with current status closed last 3 months and current rule status is running | Median time to resolve of x days. Based on alert’s linked action creation and resolution date, do not use the alert creation and resolution date. |

**Links:**

- Equipment score link: Add link to live equipment health dashboard with last 3 month custom date range selected. Label "See live equipment health dashboard".
- `https://ace.cimenviro.com/dashboard/equipment-health?site_ids={{site_id}}&start_date=2026-05-01T00:00:00.000&end_date=2026-07-31T00:00:00.000&equipment_type_ids={{equipment_type_id}}`
- Alerts resolved link: Add link to actions manager table with filtered list of all closed actions no date range filter. Label "See live issues being resolved".
- `https://ace.cimenviro.com/tickets/escalated/search?tickets_order_by=updated_at%20DESC&site_ids={{site_id}}&status_ids=6&archived=false`
- Indoor environment link: Add link to live indoor environment thermal comfort dashboard with last 3 month custom date range selected. Label "See live indoor environment dashboard"
- `https://ace.cimenviro.com/indoor-environment/thermal-comfort?summary_site_id={{site_id}}&summary_ts=2026-08-01&site_ids={{site_id}}&start_date=2026-05-01T00:00:00.000&end_date=2026-08-11T00:00:00.000`

**Equipment score benchmark:**

| Rating    | Equipment health score |
| --------- | ---------------------- |
| Excellent | >= 99%                 |
| Good      | >= 97%                 |
| Average   | >= 90%                 |
| Poor      | < 90%                  |

**Thermal comfort score benchmark:**

| Rating    | Thermal comfort score benchmark |
| --------- | ------------------------------- |
| Excellent | >= 92%                          |
| Good      | >= 85%                          |
| Average   | >= 75%                          |
| Poor      | < 75%                           |

**Labor cost avoided model:**  
Unique rules scored (by priority) last 3 months x annual mins saved per rule x (days in window / 365) x labor cost per minute. Assumed labor rates based on site region: USD 100/hr, AUD 150/hr, NZD 150/hr, GBP 75/hr, CAD 150/hr, EUR 100/hr.

| Priority | Annual checks | Mins per check | Annual mins saved per rule | Labor cost per hour ($US) | Annual cost saved per rule ($US) |
| -------- | ------------- | -------------- | -------------------------- | ------------------------- | -------------------------------- |
| P1       | 365           | 0.50           | 182.5                      | $100                      | $456.25                          |
| P2       | 52            | 1.00           | 52.0                       | $100                      | $130.00                          |
| P3       | 12            | 1.00           | 12.0                       | $100                      | $30.00                           |
| P4-5     | 4             | 1.00           | 4.0                        | $100                      | $10.00                           |

*Footnote:*  
Each rule replaces a manual inspection at a set frequency by priority: P1 daily at 0.5 mins per check, P2 weekly, P3 monthly, P4-5 quarterly, all at 1 min. Savings prorate that annual effort over the period.

**Alert recovery benchmark:**  
Recovery rate is alerts resolved in the period with fault status recovered divided by all alerts resolved in the period. Filter for alerts with status closed.

| Rating    | Recovery rate |
| --------- | ------------- |
| Excellent | >= 99%        |
| Good      | >= 95%        |
| Average   | >= 90%        |
| Poor      | < 90%         |

## Equipment health snapshot

Health by equipment type  
Date: last 3 complete months plus the current month to date

Heatmap table of monthly equipment health scores, built on the same `heatmap` component as [Indoor environment health snapshot](#indoor-environment-health-snapshot). One row per equipment type, four score columns — the last 3 complete months plus the current month to date — cell value the equipment health score, and two count columns the thermal comfort heatmap does not carry.

| Column         | Reference                                                |
| -------------- | -------------------------------------------------------- |
| Equipment type | Equipment types with at least one scored rule            |
| Equipment      | Total equipment count of that type with a scored rule    |
| Rules          | Total scored rules on that type                          |
| Month columns  | Equipment health score for that month x.xx%              |
| Chg            | Current month to date minus the start month in pp x.xx   |

**Display:**

- Color cells per the equipment score benchmark. Color the cell, not the text
- Score to 2dp. The benchmark bands sit close together, and 1dp rounds a value across a band edge so the numeral and its color disagree
- Emphasise only the current month column. Earlier months step back to body weight, per the `heatmap` component — a grid of bold figures reads as noise
- Equipment and Rules as plain numerals, left of the score columns, never colored and never barred
- Chg signed with a direction glyph. Green up, red down, muted when flat
- Sort by Chg descending, so the biggest improvement leads and any decline closes
- Close with a site row, separated from the sort
- Site row comes from the site rollup, so it will not equal the average of the type rows. Do not reconcile them
- Display all equipment types, not a sample
- Truncate equipment type name with ellipsis, do not wrap rows
- Label the current month column as partial, since it holds fewer days than the rest
- Equipment health rules count can differ to overall site rules count as rules can trigger alerts but not score
- Exclude equipment type BACER or Bacer (System). These are platform health checks

**Links:**

- Hyperlink equipment type name to PEAK with the same 4 month custom date range selected, add chevron indicating link >
- `https://ace.cimenviro.com/dashboard/equipment-health?site_ids={{site_id}}&start_date=2026-05-01T00:00:00.000&end_date=2026-08-12T00:00:00.000&equipment_type_ids={{equipment_type_id}}`

## Indoor environment health snapshot

Thermal comfort by level  
Date: last 3 complete months plus the current month to date

Heatmap table of monthly indoor environment thermal comfort scores, built on the same `heatmap` component as [Equipment health snapshot](#equipment-health-snapshot). One row per site level, four score columns — the last 3 complete months plus the current month to date — cell value the thermal comfort score to 1dp, closing with a signed change column.

| Column        | Reference                                                  |
| ------------- | ---------------------------------------------------------- |
| Level         | Site levels with at least one thermal zone                 |
| Zones         | Thermal zones on that level that returned a score          |
| Month columns | Thermal comfort score for that month x.x%                  |
| Chg           | Current month to date minus the start month in pp x.x      |

**Display:**

- Color cells per the thermal comfort score benchmark. Color the cell, not the text
- Score to 1dp. The benchmark bands sit far from the data here, so 1dp cannot round across a band edge
- Emphasise only the current month column, per the `heatmap` component
- Zones as a plain numeral, left of the score columns, never colored and never barred — it sizes the level, so the reader knows whether a swing covers two zones or twenty
- Zones counts scored zones, so the site row can fall short of the thermal zones count in [Analytics overview](#analytics-overview), which counts every zone temperature point. Say so in the notes rather than reconciling them
- Chg signed with a direction glyph. Green up, red down, muted when flat
- Sort levels in building order, highest level first, ground last — not by Chg. The reader is looking for where in the building comfort is drifting, and the Chg column carries the direction
- Close with a site row at the bottom similar style as equipment health snapshot
- Site row comes from the site rollup, so it will not equal the average of the level rows. Do not reconcile them
- Truncate level name with ellipsis, do not wrap rows
- Label the current month column as partial, since it holds fewer days than the rest

**Links:**

- Hyperlink level name to PEAK with the same 4 month custom date range selected, add chevron indicating link >
- `https://ace.cimenviro.com/indoor-environment/thermal-comfort?summary_site_id={{site_id}}&summary_ts=2026-08-01&site_ids={{site_id}}&start_date=2026-05-01T00:00:00.000&end_date=2026-08-11T00:00:00.000`

**Notes:**  
How the score is calculated: Share of zone readings inside the ASHRAE comfort band during site working hours. The band is set per zone in PEAK, typically 21-24.9C (68-79F). A reading scores 100% if all zone temperature readings during working hours and date range fell within the target band.

## Monthly equipment health

Six months of trend  
Date: last 6 months

Chart 1: Site equipment health score  
Monthly line chart of equipment health score. Add nearest benchmark threshold and label it. Auto scale Y axis.

Add source and link to equipment health dashboard.

Chart 2: Site automated health checks and labor cost avoided  
Grouped monthly bar chart of total automated rule checks (LHS) vs labor cost avoided (RHS).

**Display:**

- Display values on points. Chart 1 display 1dp x.x% and Chart 2 compact number formatting
- Add chart titles

## Alerts raised vs resolved

Faults triaged and resolved  
Date: 6 months

Grouped bars by month.

- **Raised**: actions created in the month. Count the alerts linked to each action, or 1 where an action has none, since work was still raised.
- **Resolved**: actions resolved in the month, counted the same way.
- **Exclude**: actions marked Not Doing, and alerts whose rule is no longer running, from both series.

**Notes:**

- Raised means an alert ticket is triaged into an action ticket, not when the alert ticket was created. Detection is automatic, raising is a human triage decision.
- Filter on rule state is running. If an action is not linked to an alert still count it.

## Assignee leaderboard

Who closed the work  
Date: last 6 months

| Column          | Reference                                |
| --------------- | ---------------------------------------- |
| Rank            | Position by actions resolved             |
| Assignee        | Action ticket assignee full name         |
| Company         | Assignee company name                    |
| Resolved        | Actions resolved in the period           |
| Completion rate | Resolved / (resolved + open now) x%      |
| Open now        | Actions currently open, as at issue date |

**Display:**

- Rank by resolved descending, tie-break on completion rate descending
- Trophy glyph replaces the rank numeral at 1. Nothing on 2 or 3
- Completion rate as a bar on a 0-100 scale with the value beside it
- Open now emphasised when non-zero, muted at zero
- Resolved and Open now as plain numerals. No bars
- Close with a total row, separated from the rank
- Include assignees with zero resolved but open actions. Exclude actions marked as Not Doing
- Truncate assignee and company name with ellipsis do not wrap rows

**Links:**

- Add link to PEAK assignee leaderboard with last 6 month custom date range selected
- `https://ace.cimenviro.com/reports/tickets?site_ids={{site_id}}&start_date=2026-02-01T00:00:00.000&end_date=2026-07-31T00:00:00.000&grouping=assignee`

## Key wins

What changed in the building this quarter  
Date: last 3 months

Highlight resolved or open actions, written for the facilities manager or building owner.

**Audience:**  
Written by the partner maintaining the site, delivered to the facilities manager, forwarded by them to the owner. Each win must evidence custodianship: the building is watched, faults are found and fixed, closures are verified rather than asserted. Write from the partner’s side, not the platform’s.

**Selection:**  
Read the comment history on each candidate. A win needs a physical or control change described by whoever made it.

Exclude actions resolved by stopping, tuning or ignoring a rule, platform, integration or data mapping work, actions marked as not doing.

**Display:**

- Heading names the outcome and the equipment type and name.
- Two to three sentences: what was wrong, what was changed, why it matters
- Lead with the building outcome: comfort, reliability, energy, tenant experience
- Rank by what the owner cares about. Critical plant over terminal units, permanent fixes over one-off resets
- Link the action ticket with PEAK url for quick reference evidence, include action title as link name not id
- Where several tickets form one win link them all
- Where win appears in the equipment health snapshot say so.

## Data recipes

Site facts — `search_sites` omits these, use GraphQL:  
`platform.sites` args `{site_id}` fields `[site_name, photo_url, building_size, monetary_currency]`

Counts — never fetch rows. Call with `limit:1`, read `pagination.total`:  
`search_rules(task_state:running)`, `search_favourites`, `search_equipment`  
(subtract system types 21,37,69,70,87,105,114), `search_alert_tickets`.

Thermal zones — `search_favourites(metadata_name:"%Zone Temperature", limit:1)`,
read `pagination.total`. Anchor the wildcard at the end: `%Zone Temp%` also
matches setpoint points and roughly doubles the count. Four point names mean
zone temperature (`VAV-Zn-T`, `PAC-Zn-T`, `Un-Zn-T`, `ZnT`), so filter on name,
not `metadata_codes`.

Indoor environment — `search_indoor_environment(metric:"temperature")`, two calls:
`aggregate_entity:"level"` for the grid and `"site"` for the closing row, both
`aggregate_period:"month"`, `limit:80`. Window runs from the first of the month
three complete months back to tomorrow, since `local_end_date` is exclusive and
the current month is reported to date. Rows are levels x months, so page when
levels x 4 exceeds 80. Never use `aggregate_entity:"zone"` for the snapshot —
that is one row per zone per month, hundreds of rows for the same picture.
Drill to zone only when investigating a named level.

Status ids: 1 New, 3 In Progress, 6 Closed, 7 On Hold, 8 Not Doing.

Scores/executions/rule counts — one call each, already aggregated:  
`search_equipment_health_scores(aggregate_entities:[site|metadata_type|priority], aggregate_period:[month|all])`

The equipment health heatmap needs two calls at `metadata_type` and two at `site`
over the same 4 month window: `aggregate_period:"month"` fills the cells,
`"all"` gives the Equipment and Rules counts. Take the counts from the `all`
call, never by summing or picking a month — it counts distinct equipment and
rules across the whole window, so it is legitimately higher than any single
month. The tool takes no `limit`; it returns every group.

Raised vs resolved + leaderboard — `tickets.tickets`, `type:"escalated"`,  
`ticket_archived:false`, `limit:400`, date bounds `*_at_local_*`.  
Fields: `ticket_id, created_at, resolved_at, status_id, assignees{id,firstname,lastname}, ticket_links{ticket(type:alert){ticket_id, rule_id}}`.  
Bucket by site-local month; drop `status_id:8`; weight by linked alerts whose rule is still running. An action with no linked alert counts 1; an action whose every linked alert is on a stopped rule counts 0.  
Flag any action closing many alerts at once — it distorts the month.
