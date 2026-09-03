# Equipment health

Owns three of the operational impact rows — the equipment health score, the automated health checks and the labor cost avoided — plus the equipment health snapshot and both charts in monthly equipment health. The checks and the cost model measure what the equipment health rules did, so they belong to this section. Scaffold parts: `equipment-health-snapshot`, `monthly-equipment-health`.

## Fetch

`search_equipment_health_scores` shapes all six calls. It takes no `limit` and returns every group, so none of these page.

Pass `local_end_date` as the first of the month after the last complete month; it is exclusive, and both windows close there. A mid-month bound is refused for scanning too many rows — Shared data in SKILL.md says why.

| Call                                       | Window        | Feeds                                                        |
| ------------------------------------------ | ------------- | ------------------------------------------------------------ |
| `aggregate_entities:["metadata_type"]`, `aggregate_period:"month"` | quarter  | heatmap cells                                     |
| `aggregate_entities:["metadata_type"]`, `aggregate_period:"all"`   | quarter  | the Equipment and Rules counts                    |
| `aggregate_entities:["site"]`, `aggregate_period:"month"`          | 7 months | snapshot site row (last 3), Chart 1 (all 7)       |
| `aggregate_entities:["site"]`, `aggregate_period:"all"`            | quarter  | the headline score in the operational impact row  |
| `aggregate_entities:["priority"]`, `aggregate_period:"all"`        | quarter  | the checks and labor cost rows                    |
| `aggregate_entities:["priority"]`, `aggregate_period:"month"`      | 7 months | Chart 2 bars                                      |

On the `priority` calls, executions sum across priorities for the checks total and the per-priority split drives the labor model. Take distinct counts from an `all` call, never by summing months or picking one — it counts distinct equipment and rules across the whole window, so it is legitimately higher than any single month. Scores never sum either; the site row is its own rollup.

## Operational impact rows

| Rating chip                         | Metric label                     | Value                                     | Subtitle                                                                          |
| ----------------------------------- | -------------------------------- | ----------------------------------------- | --------------------------------------------------------------------------------- |
| See below equipment score benchmark | x.x% equipment health maintained | Site equipment health score over the quarter | {Up\|Down} x.xx pp from y.yy% in {first month of the quarter} to z.zz% in {last month} |

The row carries a movement, not a baseline: the quarter's last month minus its first, in pp — the same definition as the snapshot Chg column, so this figure equals the site row Chg in the snapshot below it. Name both endpoint values and their months; the headline figure is the quarter score, so a bare "up x.xx pp" implies a baseline that appears nowhere in the report. The headline score is the `site` × `all` rollup over the quarter; both movement endpoints come from the `site` × `month` series already fetched — no separate 12 month call. Score to 2dp, matching the snapshot.

| Rating chip | Metric label                                 | Value                          | Subtitle                                         |
| ----------- | -------------------------------------------- | ------------------------------ | ------------------------------------------------ |
| Continuous  | x automated equipment health checks ran 24/7 | Total executions over the quarter | Averaging x monthly checks across y scored rules |
| Modelled    | $x labor cost avoided                        | See the labor cost model below | x hours and y.y working days of inspection time  |

Section link, labelled "See live equipment health dashboard":
`https://ace.cimenviro.com/dashboard/equipment-health?site_ids={{site_id}}&start_date={{quarter_start}}T00:00:00.000&end_date={{quarter_end}}T00:00:00.000&equipment_type_ids={{equipment_type_id}}`

## Labor cost avoided model

Unique rules scored (by priority) over the quarter x annual mins saved per rule x (days in window / 365) x labor cost per minute. Assumed labor rates based on site region: USD 100/hr, AUD 150/hr, NZD 150/hr, GBP 75/hr, CAD 150/hr, EUR 100/hr.

| Priority | Annual checks | Mins per check | Annual mins saved per rule | Labor cost per hour ($US) | Annual cost saved per rule ($US) |
| -------- | ------------- | -------------- | -------------------------- | ------------------------- | -------------------------------- |
| P1       | 365           | 0.50           | 182.5                      | $100                      | $456.25                          |
| P2       | 52            | 1.00           | 52.0                       | $100                      | $130.00                          |
| P3       | 12            | 1.00           | 12.0                       | $100                      | $30.00                           |
| P4-5     | 4             | 1.00           | 4.0                        | $100                      | $10.00                           |

Each rule replaces a manual inspection at a set frequency by priority: P1 daily at 0.5 mins per check, P2 weekly, P3 monthly, P4-5 quarterly, all at 1 min. Savings prorate that annual effort over the days monitored in the period.

## Equipment score benchmark

| Rating    | Equipment health score |
| --------- | ---------------------- |
| Excellent | >= 99%                 |
| Good      | >= 97%                 |
| Average   | >= 90%                 |
| Poor      | < 90%                  |

## Equipment health snapshot

Health by equipment type
Date: the quarter

Heatmap table of monthly equipment health scores, one row per equipment type, three score columns — the months of the quarter, matching the reporting period in the masthead — plus two count columns the thermal comfort heatmap does not carry.

| Column         | Reference                                              |
| -------------- | ------------------------------------------------------ |
| Equipment type | Equipment types with at least one scored rule          |
| Equipment      | Total equipment count of that type with a scored rule  |
| Rules          | Total scored rules on that type                        |
| Month columns  | Equipment health score for that month x.xx%            |
| Chg            | Last month of the quarter minus the first, in pp x.xx  |

**Display:**

- Color cells per the equipment score benchmark. Color the cell, not the text
- Score to 2dp. The benchmark bands sit close together, and 1dp rounds a value across a band edge so the numeral and its color disagree
- Emphasise only the closing month column. Earlier months step back to body weight, per the `heatmap` component — a grid of bold figures reads as noise
- Equipment and Rules as plain numerals, left of the score columns, never colored and never barred
- Chg signed with a direction glyph. Green up, red down, muted when flat
- Sort by Chg descending, so the biggest improvement leads and any decline closes
- Close with a site row, separated from the sort
- Site row comes from the site rollup, so it will not equal the average of the type rows. Do not reconcile them
- Display all equipment types, not a sample
- Truncate equipment type name with ellipsis, do not wrap rows
- Equipment health rules count can differ to overall site rules count as rules can trigger alerts but not score
- Exclude equipment type BACER or Bacer (System). These are platform health checks

**Links:**

- Hyperlink equipment type name to PEAK with the same quarter as a custom date range, add chevron indicating link >
- `https://ace.cimenviro.com/dashboard/equipment-health?site_ids={{site_id}}&start_date={{quarter_start}}T00:00:00.000&end_date={{quarter_end}}T00:00:00.000&equipment_type_ids={{equipment_type_id}}`

## Monthly equipment health

Seven months of trend
Date: the seven complete months ending with the quarter

Chart 1: Site equipment health score
Monthly line chart. Render the two nearest benchmark thresholds and label them — one either side where the series sits inside a band, otherwise the threshold it crosses plus the next one out, so the reader can see which months fall on which side. Auto scale Y axis to fit both.

Chart 2: Site automated health checks and labor cost avoided
Grouped monthly bar chart of total automated rule checks (LHS) vs labor cost avoided (RHS) — the monthly view of the two rows above. Price each month with the labor cost model, prorated over that month's days.

**Display:**

- Display values on points. Chart 1 display 1dp x.x% and Chart 2 compact number formatting
- Add chart titles
- Chart 1's score is the same `site` series as the snapshot site row, so the months they share must agree
- A step change in the site score often tracks a change in what is being scored, not a change in the building. Check the rule count per month before writing the note: newly deployed rules commonly fault until their thresholds settle, and that is the more useful thing to tell the reader
- Every bucket is a whole month, so a dip in Chart 2 is a real fall in volume. Say what moved it — usually the rule count, sometimes a shorter month — rather than leaving the reader to guess

**Links:**

- Source link on Chart 1, over the 7 month window. Use custom dates, not a relative range — the report is a fixed quarter and must keep showing the same window as it ages
- `https://ace.cimenviro.com/dashboard/equipment-health?site_ids={{site_id}}&start_date={{trend_start}}T00:00:00.000&end_date={{quarter_end}}T00:00:00.000`

## Notes band items

- **Labor cost avoided.** The model above, with the region's rate named
