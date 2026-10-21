# Equipment health

Owns the equipment health by site table and its portfolio row, and hands on the sites' scores as a ranking. Scaffold part: `equipment-health`. Script: `scripts/equipment_health.py`, which builds every row, cell, link and note below.

## What you write

Nothing on the page. In chat, say what the script prints: any site with no score in the quarter, which is left out of the table and the ranking, and any site whose scored rules in a month fell below half of its busiest month. That month covers part of the plant, from an outage or rules still going live, so it moves the site's change and the portfolio row without the plant having changed.

## Section header

Eyebrow: Equipment health snapshot  
Statement: Equipment health by site  
Date line: "{period}. Share of rule executions returning no fault." The period runs from the quarter's first day to its last, or to the issue date where the report carries a month to date, with a spaced hyphen: "1 July - 21 October 2026".

## Equipment score benchmark

| Rating | Equipment health score |
| --- | --- |
| Excellent | >= 99% |
| Good | >= 97% |
| Average | >= 90% |
| Poor | < 90% |

## Ranked heatmap

One row per site with a score in the quarter, ranked by its score for the period's last month, then a portfolio row.

| Column | Content |
| --- | --- |
| Rank | Position by the last month's score; the trophy replaces 1 |
| Site | The site name with its state abbreviation in muted brackets, "88 Example St (NSW)" |
| Size | Building size, in the portfolio's unit, named in the header |
| Equip | Equipment with a scored rule in the quarter |
| Rules | Scored rules in the quarter |
| Month columns | The site's equipment health score for each month of the quarter, then the month to date headed "to date" |
| Chg | Last month column minus the first, 1dp, signed with a glyph |

**Ranking:**

- Best first on the unrounded score. Equal scores split alphabetically by site name, ignoring case. No shared places and no notes explaining ties
- A site with scores in the quarter but none in its last month ranks after every site that has one, alphabetically

**Portfolio row:**

- Each month's score is weighted by building size over the sites with a score that month. A site with no building size is left out of the weighting
- Size, Equip and Rules are summed over the rows shown
- Chg is the portfolio row's own last month less its first

**Display:**

- Color cells per the equipment score benchmark, by band, on the printed value, with the band key above the table naming the thresholds
- Scores to 1dp. Only the closing month column carries weight, per the `heatmap` component
- A month a site had no score shows a dash with no fill, and Chg is a dash when either end is missing
- Equip, Rules and Size as plain numerals, never colored and never barred
- Equip and Rules leave out the system types
- Every site, not a sample. The table breaks between rows across pages, its header repeating
- Site names wrap within a fixed row height rather than truncating

**Links:**

- Each site name links to that site's equipment health dashboard over the period, with a chevron:
  `https://ace.cimenviro.com/dashboard/equipment-health?site_ids={{site_id}}&start_date={{quarter_start}}T00:00:00.000&end_date={{quarter_end}}T00:00:00.000`
- The section carries the anchor `eh-by-site`

**Hands on:** a ranking labelled Equipment health, under the anchor `eh-by-site`, over months: each site's score for the period's first and last month, to 1dp.

## Notes band items

- **Scored equipment.** Equip and Rules count equipment and rules that scored in the period, so they can sit below the monitored totals in the scorecards

## Data

All in the main batch: `search_equipment_health_scores` over the quarter with every `site_ids`, split across calls:

| `aggregate_entities` | `aggregate_period` | Feeds |
| --- | --- | --- |
| `site` | `month` | the month cells, the board and its movement, and each month's scored rules for the outage check |
| `metadata_type` | `all` | Rules: `task_count` summed per site over every type but the system types |
| `equipment` | `all` | Equip: distinct `equipment_id` per site, the system types left out |

- Six sites a call. Every grouping scans each rule's month rows for its sites, about 10,000 a site over a quarter and three times that at the largest, and PEAK refuses a call that would scan more than 200,000
- `metadata_type` groups within each site already, so it carries `site_id` and takes no `site` beside it
- `local_end_date` is exclusive and every bound a month boundary, the month to date included, so the month to date holds whatever exists so far
- Distinct counts come from an `all` call, never by summing months. Scores never sum: the site cell is PEAK's site rollup, and the portfolio row is the size-weighted mean of those
- A site's scored rules in a month below half of its busiest month is what the script names in chat
