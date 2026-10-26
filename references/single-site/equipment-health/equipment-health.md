# Equipment health

Owns three of the operational impact rows (the equipment health score, the automated health checks and the labour cost avoided) plus the equipment health snapshot and both charts in monthly equipment health. The checks and the cost model measure what the equipment health rules did, so they belong to this section. Scaffold parts: `equipment-health-snapshot`, `monthly-equipment-health`. Script: `scripts/equipment_health.py`, which builds every figure, row, chart and link below.

## What you write

Nothing. The script fills the whole section, the note under Chart 2 included. With no equipment health score for the site in the quarter, the section is left out and the script says so in chat.

## Operational impact rows

| Rating chip                         | Metric label                     | Value                                     | Subtitle                                                                          |
| ----------------------------------- | -------------------------------- | ----------------------------------------- | --------------------------------------------------------------------------------- |
| See below equipment score benchmark | x.x% equipment health maintained | Site equipment health score over the quarter | {Up\|Down} x.x pp from y.y% in {first month of the quarter} to z.z% in {last month, or the month to date} |

The row carries a movement, not a baseline: the reporting period's last month minus its first, in pp, the last being the month to date where the report carries one. Same definition as the snapshot Chg column, so this figure equals the site row Chg in the snapshot below it. Name both endpoint values and their months; the headline figure is the quarter score, so a bare "up x.x pp" implies a baseline that appears nowhere in the report. The headline score is the site's score over the quarter, rolled up from the `metadata_type` × `all` rows; both movement endpoints come from the site's monthly series, rolled up from the `metadata_type` × `month` rows already fetched. No separate 12 month call. Score to 1dp, matching the snapshot.

| Rating chip | Metric label                                 | Value                          | Subtitle                                         |
| ----------- | -------------------------------------------- | ------------------------------ | ------------------------------------------------ |
| Continuous  | x automated equipment health checks ran 24/7 | Total executions over the quarter | Averaging x monthly checks across y scored rules |
| Modelled    | $x labour cost avoided                       | The monthly figures Chart 2 draws for the reporting period, added up | x hours and y.y working days of inspection time  |

Section link, labelled "See live equipment health dashboard", over the quarter. Bundle slot `equipment_health`:
`https://ace.cimenviro.com/dashboard/equipment-health?site_ids={{site_id}}&start_date={{quarter_start}}T00:00:00.000&end_date={{quarter_end}}T00:00:00.000`

## Labour cost avoided model

Each month: rules scored that month (by priority) x annual mins saved per rule x (the month's days / 365) x labour cost per minute. The headline adds up those monthly figures over the reporting period, so it equals Chart 2's bars for the same months. The labour rate follows the site's currency, by the rates in this section's script, and hours convert to days at a 7.5-hour working day. A currency PEAK names that the script does not price is costed at the US rate, and chat says so.

| Priority | Annual checks | Mins per check | Annual mins saved per rule | Labour cost per hour (USD) | Annual cost saved per rule (USD) |
| -------- | ------------- | -------------- | -------------------------- | -------------------------- | -------------------------------- |
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

Heatmap table of monthly equipment health scores, one row per equipment type, a score column for each month of the reporting period, the quarter's three and then the month to date where the report carries one, headed "to date", plus two count columns.

| Column         | Reference                                              |
| -------------- | ------------------------------------------------------ |
| Equipment type | Equipment types with at least one scored rule          |
| Equipment      | Equipment of that type with a rule scored in the months shown |
| Rules          | Rules scored on that type in the months shown          |
| Month columns  | Equipment health score for that month x.x%             |
| Chg            | Last month column minus the first, in pp x.x           |

**Display:**

- Color cells per the equipment score benchmark. Color the cell, not the text
- Score to 1dp. A cell takes its band from the printed value, so the numeral and its color always agree
- Emphasise only the closing month column. Earlier months step back to body weight, per the `heatmap` component. A grid of bold figures reads as noise
- Equipment and Rules as plain numerals, left of the score columns, never colored and never barred
- Chg signed with a direction glyph. Green up, red down, muted when flat
- Sort by Chg descending, so the biggest improvement leads and any decline closes
- Close with a site row, separated from the sort
- Site row is the type rows' scores weighted by their rules, as PEAK rolls up a site, so it will not equal their plain average. Do not reconcile them. Its Equipment and Rules are the totals of the rows shown, so those two columns do add up, and they are the scored equipment and rules the section hands on to the analytics overview
- Display all equipment types, not a sample
- Truncate equipment type name with ellipsis, do not wrap rows
- Equipment health rules count can differ to overall site rules count as rules can trigger alerts but not score
- Leave out the BACER (`SYS-BACER`), the device that reads the BMS into PEAK. Every other type shows, Water Meters (System) included

**Links:**

- Hyperlink equipment type name to the section link with `&equipment_type_ids={metadata_type_id}` appended, the row's own id off the heatmap call. Add chevron indicating link >

## Monthly equipment health

Six months of trend
Date: the six complete months ending with the quarter, and the month to date where the report carries one

Chart 1: Site equipment health score
Monthly line chart. Render the two nearest benchmark thresholds and label them: one either side where the series sits inside a band, otherwise the threshold it crosses plus the next one out, so the reader can see which months fall on which side. Auto scale Y axis to fit both.

Chart 2: Site automated health checks and labour cost avoided
Grouped monthly bar chart of total automated rule checks (LHS) vs labour cost avoided (RHS), the monthly view of the two rows above. Price each month with the labour cost model, prorated over that month's days, the month to date over its days so far.

Under it, a chart note carrying the labour cost avoided notes item word for word, except that it prorates over each month's own days rather than the quarter's, so the method sits beside the figures it prices. The script writes both from one sentence.

**Display:**

- Display values on points. Chart 1 display 1dp x.x% and Chart 2 compact number formatting
- Add chart titles
- Chart 1's score is the same site series as the snapshot site row, so the months they share must agree
- Each value sits over its own month; a month with no score leaves a gap in the line, and a month with no checks a gap in Chart 2

**Links:**

- Source link on Chart 1, over the 6 month window the chart draws. Bundle slot `trend_eh`
- `https://ace.cimenviro.com/dashboard/equipment-health?site_ids={{site_id}}&start_date={{trend_start}}T00:00:00.000&end_date={{quarter_end}}T00:00:00.000`

## Newly onboarded sites

A site that went live inside the windows has less history than they ask for, and the section covers what exists.

- A site series that starts after the trend window's first month went live in its first scored month. Its checks per rule, against the next month's pace, date the day; at nine tenths of that pace or more it ran from the 1st
- The go-live month is dropped unless it ran from the 1st or nothing follows it. Every figure, chart and date line takes the months kept, whole months only apart from the month to date, the headline, the Equipment and the Rules from a follow-up `metadata_type` × `all` over them, and the section hands on the first month kept and the go-live date
- The snapshot carries only the months kept, so it is only as wide as the data
- A movement needs two months. One month: no movement and no Chg column, rows lowest score first, so the plant needing attention leads
- A trend needs three points, since two drawn as a line invite the reader to extend it. Under three: no Chart 1. Wherever the months were trimmed, the section is titled "The trend so far"
- The labour cost model prorates over the days actually monitored, never the calendar quarter
- An equipment type whose rules began scoring after the site did draws its earlier months and its Chg as dashes with no fill, so the row keeps the table's width
- A gap in the middle of the series is an outage, not onboarding, and so is a month scored off a fraction of the usual rules. The chart plots the months that exist and leaves the gap visible. Chat names a month scored off under half the rules of each month beside it, or off none, as an outage; a rule count that rises or falls by half again from one month to the next is a coverage change, on its own line

## Notes band items

- **Labour cost avoided.** The model above, with the region's rate named

## Data

All in the main batch. Type names come from `platform.metadata_types`, selecting only `type_id` and `type`. The rest are `search_equipment_health_scores`, which takes no `limit` and returns every group, so none of them page:

| `aggregate_entities` | `aggregate_period` | Window   | Feeds                                            |
| -------------------- | ------------------ | -------- | ------------------------------------------------ |
| `metadata_type`      | `month`            | 6 months | heatmap cells (the quarter's months), and rolled up, the snapshot site row and Chart 1 |
| `metadata_type`, with `select_equipment_count` | `all` | quarter | the Equipment and Rules counts, the Rules total the scored rules in the checks row, and rolled up, the headline score |
| `metadata_type`, `priority` | `month`     | 6 months | rolled up by priority, Chart 2 bars, and the checks and labour cost rows, summed over the reporting period |
| `metadata_type`, with `select_equipment_count` | `all` | months kept | follow-up, a site that went live in the quarter: the Equipment and Rules counts, and rolled up, the headline score |

- `local_end_date` is exclusive, so the scripts pass the first of the month after the window's last month, the month to date included, which then holds whatever exists so far. A mid-month bound is refused for scanning too many rows
- `select_equipment_count` adds each type's distinct `equipment_count` to its row, so no per-equipment call is needed. It scores only rules on a piece of equipment, as the equipment health dashboard does
- Executions sum across priorities for the checks total, and the per-priority split drives the labour model, each month priced over its own days; the checks and labour cost rows add up the same monthly figures Chart 2 draws
- Distinct equipment and rule counts come from an `all` call, never by summing months: it counts distinct across the whole window, so it is legitimately higher than any single month. Scores never sum
- Every site figure rolls up from the type rows with the BACER left out: each score the mean of its types' weighted by their rules, which is how PEAK rolls up a site, the checks and rules summed
