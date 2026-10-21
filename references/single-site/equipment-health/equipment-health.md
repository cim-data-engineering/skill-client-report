# Equipment health

Owns three of the operational impact rows (the equipment health score, the automated health checks and the labor cost avoided) plus the equipment health snapshot and both charts in monthly equipment health. The checks and the cost model measure what the equipment health rules did, so they belong to this section. Scaffold parts: `equipment-health-snapshot`, `monthly-equipment-health`. Script: `scripts/equipment_health.py`, which builds every figure, row, chart and link below.

## What you write

Nothing. The script fills the whole section, the note under Chart 2 included.

## Operational impact rows

| Rating chip                         | Metric label                     | Value                                     | Subtitle                                                                          |
| ----------------------------------- | -------------------------------- | ----------------------------------------- | --------------------------------------------------------------------------------- |
| See below equipment score benchmark | x.x% equipment health maintained | Site equipment health score over the quarter | {Up\|Down} x.xx pp from y.yy% in {first month of the quarter} to z.zz% in {last month, or the month to date} |

The row carries a movement, not a baseline: the reporting period's last month minus its first, in pp, the last being the month to date where the report carries one. Same definition as the snapshot Chg column, so this figure equals the site row Chg in the snapshot below it. Name both endpoint values and their months; the headline figure is the quarter score, so a bare "up x.xx pp" implies a baseline that appears nowhere in the report. The headline score is the `site` × `all` rollup over the quarter; both movement endpoints come from the `site` × `month` series already fetched. No separate 12 month call. Score to 2dp, matching the snapshot.

| Rating chip | Metric label                                 | Value                          | Subtitle                                         |
| ----------- | -------------------------------------------- | ------------------------------ | ------------------------------------------------ |
| Continuous  | x automated equipment health checks ran 24/7 | Total executions over the quarter | Averaging x monthly checks across y scored rules |
| Modelled    | $x labor cost avoided                        | The monthly figures Chart 2 draws for the reporting period, added up | x hours and y.y working days of inspection time  |

Section link, labelled "See live equipment health dashboard", over the quarter. Bundle slot `equipment_health`:
`https://ace.cimenviro.com/dashboard/equipment-health?site_ids={{site_id}}&start_date={{quarter_start}}T00:00:00.000&end_date={{quarter_end}}T00:00:00.000`

## Labor cost avoided model

Each month: rules scored that month (by priority) x annual mins saved per rule x (the month's days / 365) x labor cost per minute. The headline adds up those monthly figures over the reporting period, so it equals Chart 2's bars for the same months. The labor rate follows the site's currency (`peak_io.currency`), and hours convert to days at a 7.5-hour working day.

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

Heatmap table of monthly equipment health scores, one row per equipment type, a score column for each month of the reporting period in the masthead, the quarter's three and then the month to date where the report carries one, headed "to date", plus two count columns the thermal comfort heatmap does not carry.

| Column         | Reference                                              |
| -------------- | ------------------------------------------------------ |
| Equipment type | Equipment types with at least one scored rule          |
| Equipment      | Total equipment count of that type with a scored rule  |
| Rules          | Total scored rules on that type                        |
| Month columns  | Equipment health score for that month x.xx%            |
| Chg            | Last month column minus the first, in pp x.xx          |

**Display:**

- Color cells per the equipment score benchmark. Color the cell, not the text
- Score to 1dp. A cell takes its band from the printed value, so the numeral and its color always agree
- Emphasise only the closing month column. Earlier months step back to body weight, per the `heatmap` component. A grid of bold figures reads as noise
- Equipment and Rules as plain numerals, left of the score columns, never colored and never barred
- Chg signed with a direction glyph. Green up, red down, muted when flat
- Sort by Chg descending, so the biggest improvement leads and any decline closes
- Close with a site row, separated from the sort
- Site row comes from the site rollup, so it will not equal the average of the type rows. Do not reconcile them. Its Equipment and Rules are the totals of the rows shown, so those two columns do add up
- Display all equipment types, not a sample
- Truncate equipment type name with ellipsis, do not wrap rows
- Equipment health rules count can differ to overall site rules count as rules can trigger alerts but not score
- Exclude the system types. Bacer and Water Meters (System) are the two that turn up

**Links:**

- Hyperlink equipment type name to the section link with `&equipment_type_ids={metadata_type_id}` appended, the row's own id off the heatmap call. Add chevron indicating link >

## Monthly equipment health

Six months of trend
Date: the six complete months ending with the quarter, and the month to date where the report carries one

Chart 1: Site equipment health score
Monthly line chart. Render the two nearest benchmark thresholds and label them: one either side where the series sits inside a band, otherwise the threshold it crosses plus the next one out, so the reader can see which months fall on which side. Auto scale Y axis to fit both.

Chart 2: Site automated health checks and labor cost avoided
Grouped monthly bar chart of total automated rule checks (LHS) vs labor cost avoided (RHS), the monthly view of the two rows above. Price each month with the labor cost model, prorated over that month's days, the month to date over its days so far.

Under it, a chart note carrying the labor cost avoided notes item word for word, except that it prorates over each month's own days rather than the quarter's, so the method sits beside the figures it prices. The script writes both from one sentence.

**Display:**

- Display values on points. Chart 1 display 1dp x.x% and Chart 2 compact number formatting
- Add chart titles
- Chart 1's score is the same `site` series as the snapshot site row, so the months they share must agree
- Each value sits over its own month; a month with no score leaves a gap in the line, and a month with no checks a gap in Chart 2

**Links:**

- Source link on Chart 1, over the 6 month window the chart draws. Bundle slot `trend_eh`
- `https://ace.cimenviro.com/dashboard/equipment-health?site_ids={{site_id}}&start_date={{trend_start}}T00:00:00.000&end_date={{quarter_end}}T00:00:00.000`

## Newly onboarded sites

Per SKILL.md, [Newly onboarded sites](../../../SKILL.md#newly-onboarded-sites):

- A `site` × `month` series that starts after the trend window's first month went live in its first scored month. Its checks per rule, against the next month's pace, date the day; at nine tenths of that pace or more it ran from the 1st
- The go-live month is dropped unless it ran from the 1st or nothing follows it. Every figure, chart and date line takes the months kept, the headline from a follow-up `site` × `all` over them, and the section hands on the first month kept and the go-live date
- One month: no movement and no Chg column, rows lowest score first. Under three points: no Chart 1, and the section is titled "The trend so far"
- Chat names a month scored off under half the rules of each month beside it, or off none, as an outage; a rule count that rises or falls by half again from one month to the next is a coverage change, on its own line

## Notes band items

- **Labor cost avoided.** The model above, with the region's rate named

## Data

All in the main batch. Type names come from `platform.metadata_types`, selecting only `type_id` and `type`. The rest are `search_equipment_health_scores`, which takes no `limit` and returns every group, so none of them page:

| `aggregate_entities` | `aggregate_period` | Window   | Feeds                                            |
| -------------------- | ------------------ | -------- | ------------------------------------------------ |
| `metadata_type`      | `month`            | quarter  | heatmap cells                                    |
| `metadata_type`      | `all`              | quarter  | the Rules count                                  |
| `equipment`          | `all`              | quarter  | the Equipment count, distinct equipment per type |
| `site`               | `month`            | 6 months | snapshot site row (the quarter's months), Chart 1 (all) |
| `site`               | `all`              | quarter  | the headline score in the operational impact row |
| `priority`           | `all`              | quarter  | the scored rules count in the checks row         |
| `priority`           | `month`            | 6 months | Chart 2 bars, and the checks and labor cost rows, summed over the reporting period |
| `site`               | `all`              | months kept | follow-up, a site that went live in the quarter: the headline score |

- `local_end_date` is exclusive, so the scripts pass the first of the month after the window's last month, the month to date included, which then holds whatever exists so far. A mid-month bound is refused for scanning too many rows
- The type rows carry rules but no equipment count, and PEAK does not group by `metadata_type` and `equipment` together, so the Equipment column counts distinct `equipment_id` per type off the `equipment` rows, which return their type
- Executions sum across priorities for the checks total, and the per-priority split drives the labor model, each month priced over its own days; the checks and labor cost rows add up the same monthly figures Chart 2 draws
- Distinct equipment and rule counts come from an `all` call, never by summing months: it counts distinct across the whole window, so it is legitimately higher than any single month. Scores never sum, and the site row is its own rollup
