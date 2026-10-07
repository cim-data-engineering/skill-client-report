# Indoor environment

Owns the operational impact thermal comfort row, the indoor environment health snapshot, and monthly thermal comfort. Scaffold parts: `indoor-environment-snapshot`, `monthly-thermal-comfort`. Script: `scripts/indoor_environment.py`, which builds every figure, row, chart and link below.

## What you write

Two notes in `prose.json`, from the facts `report.py bundle` prints:

- `ie_snapshot`, under comfort by level: where in the building comfort moved and why, naming the levels that moved most and any that sit below Good
- `ie_trend`, under the six-month chart: the direction against the benchmark lines

Levels with configured points but no score this quarter are in neither the table nor the thermal zones figure. `facts.md` names them: say so in chat, not on the page.

## Operational impact row

| Rating chip                               | Metric label                    | Value                                       | Subtitle                                                                           |
| ----------------------------------------- | ------------------------------- | ------------------------------------------- | ---------------------------------------------------------------------------------- |
| See below thermal comfort score benchmark | x.x% thermal comfort maintained | Site thermal comfort score over the quarter | {Up|Down} x.x pp from y.y% in {first month of the quarter} to z.z% in {last month} |

Same movement definition as the snapshot Chg column, the quarter's last month minus its first in pp, so this figure equals the site row Chg in the snapshot below it. Name both endpoint values and their months. Both endpoints come from the `site` series already fetched. Score to 1dp, matching the snapshot.

Section link, labelled "See live indoor environment dashboard": the `platform_link` off the `site` × `all` quarter call. Bundle slot `comfort`.

## Thermal comfort score benchmark

| Rating    | Thermal comfort score |
| --------- | --------------------- |
| Excellent | >= 92%                |
| Good      | >= 85%                |
| Average   | >= 75%                |
| Poor      | < 75%                 |

## Indoor environment health snapshot

Thermal comfort by level  
Date: the quarter

Heatmap table on the same `heatmap` component as the equipment health snapshot. One row per site level, three score columns for the months of the quarter, cell value the thermal comfort score to 1dp, closing with a signed change column.

| Column        | Reference                                            |
| ------------- | ---------------------------------------------------- |
| Level         | Site levels that returned a comfort score            |
| Zones         | Thermal zones configured on that level               |
| Month columns | Thermal comfort score for that month x.x%            |
| Chg           | Last month of the quarter minus the first, in pp x.x |

**Display:**

- Color cells per the thermal comfort score benchmark. Color the cell, not the text
- Score to 1dp. The benchmark bands sit far from the data here, so 1dp cannot round across a band edge
- Emphasise only the closing month column, per the `heatmap` component
- Zones as a plain numeral, left of the score columns, never colored and never barred. It sizes the level, so the reader knows whether a swing covers two zones or twenty
- Zones counts the zone temperature points configured for comfort scoring. The site row totals the levels shown, and the analytics overview prints that same total as thermal zones, so the two always agree. A level whose points returned no score in the quarter has no row and counts in neither
- Chg signed with a direction glyph. Green up, red down, muted when flat
- Sort levels in building order, highest level first, ground last, not by Chg. The reader is looking for where in the building comfort is drifting, and the Chg column carries the direction
- Close with a site row at the bottom, same style as the equipment health snapshot
- Site row comes from the site rollup, so it will not equal the average of the level rows. Do not reconcile them
- One level means the level row and the site row are the same figure, so list the zones as the rows instead, from the zone call in Fetch. Show each zone's average temperature where the Zones count would go, since a count of 1 says nothing. Label rows by zone name, adding the unit's letter where one name covers several zones
- Truncate level name with ellipsis, do not wrap rows

**Links:**

- Hyperlink level name to the section link with `&level_ids={level_id}` appended, the row's own id off the level call. Add chevron indicating link >
- The level and zone groupings come back with `platform_link: null`, because that page cannot express them, so a row link is the site call's link narrowed and never a call of its own

## Monthly thermal comfort

Where comfort has been heading  
Date: the six complete months ending with the quarter

Chart: Site thermal comfort score. A monthly line chart built like Chart 1 in monthly equipment health, against the thermal comfort benchmark thresholds.

**Display:**

- Display values on points, 1dp x.x%
- Add chart title
- The score is the same `site` series as the snapshot site row, so the months they share must agree
- Thermal comfort swings harder than equipment health, so let the Y axis follow the data rather than reusing the equipment health scale

**Links:**

- Source link on the chart: the `platform_link` off the `site` × `month` 6 month call, so it opens the window the chart draws. Bundle slot `trend_comfort`

## Notes band items

- **Thermal comfort score.** Share of zone readings inside the ASHRAE comfort band during site working hours. The band is set per zone in PEAK, typically 21-24.9C (68-79F), so a level scores 100% when every zone reading in working hours fell inside it. The site row comes from the site rollup and will not equal the average of the level rows
- **Zones.** The count is the zone temperature points configured for comfort scoring on each level shown, and the site row is the thermal zones figure in the analytics overview. A level whose points returned no score in the quarter is left out of both

## Data

Four calls in the main batch: three `search_indoor_environment(metric:"temperature")` and one `count_indoor_environment_zones`.

| Call | Window | Feeds |
| --- | --- | --- |
| `level` × `month`, `limit:80` | quarter | the snapshot grid; paged by `report.py next` when levels × 3 passes 80 |
| `site` × `month` | 6 months | the snapshot closing row (last 3) and the trend |
| `site` × `all` | quarter | the headline score and the section link |
| `count_indoor_environment_zones`, `aggregate_entity:"level"` | current configuration | the Zones column and the thermal zones figure |

- The Zones column joins the count's `included_point_count` to the level rows on `level_id`, and a level the count does not return counts 0. Summed over the levels shown, it is the site row and the analytics overview's thermal zones figure. Never page zone rows to count them, and never substitute `search_zones`, `platform.levels` or `platform.zones`: they list zone objects, not zone temperature points
- A single-level site is the one follow-up: `next` asks for `zone` × `month` rows, which carry `zone_name` and `zone_value`
- Levels sort into building order from their names: a name with no readable floor first, then numbered floors highest first, ground, then basements. `facts.md` prints the order; a building PEAK names oddly is worth a line in chat
