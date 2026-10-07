# Indoor environment

Owns the operational impact thermal comfort row, the indoor environment health snapshot, and monthly thermal comfort. Scaffold parts: `indoor-environment-snapshot`, `monthly-thermal-comfort`.

## Operational impact row

| Rating chip                               | Metric label                    | Value                                       | Subtitle                                                                           |
| ----------------------------------------- | ------------------------------- | ------------------------------------------- | ---------------------------------------------------------------------------------- |
| See below thermal comfort score benchmark | x.x% thermal comfort maintained | Site thermal comfort score over the quarter | {Up|Down} x.x pp from y.y% in {first month of the quarter} to z.z% in {last month} |

Same movement definition as the snapshot Chg column, the quarter's last month minus its first in pp, so this figure equals the site row Chg in the snapshot below it. Name both endpoint values and their months. Both endpoints come from the `site` series already fetched. Score to 1dp, matching the snapshot.

Section link, labelled "See live indoor environment dashboard", bundle slot `comfort`:
`https://ace.cimenviro.com/indoor-environment/thermal-comfort?summary_site_id={{site_id}}&summary_ts={{quarter_last_month}}&site_ids={{site_id}}&start_date={{quarter_start}}T00:00:00.000&end_date={{quarter_end}}T00:00:00.000`

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
| Chg           | Last month of the quarter minus the first, in pp x.x, taken between the two scores as printed so the row agrees with itself |

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

- Hyperlink level name to PEAK with the same quarter as a custom date range, add chevron indicating link >
- `https://ace.cimenviro.com/indoor-environment/thermal-comfort?summary_site_id={{site_id}}&summary_ts={{quarter_last_month}}&site_ids={{site_id}}&start_date={{quarter_start}}T00:00:00.000&end_date={{quarter_end}}T00:00:00.000&level_ids={{level_id}}`

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

- Source link on the chart, over the 6 month window, bundle slot `trend_comfort`. Use custom dates, not a relative range. The report is a fixed quarter and must keep showing the same window as it ages
- `https://ace.cimenviro.com/indoor-environment/thermal-comfort?summary_site_id={{site_id}}&summary_ts={{quarter_last_month}}&site_ids={{site_id}}&start_date={{trend_start}}T00:00:00.000&end_date={{quarter_end}}T00:00:00.000`

## Notes band items

- **Thermal comfort score.** Share of zone readings inside the ASHRAE comfort band during site working hours. The band is set per zone in PEAK, typically 21-24.9C (68-79F); name this site's from `thermal_comfort_min_temp` and `thermal_comfort_max_temp` on the site, in the scaffold's `{{comfort_band}}`, so a level scores 100% when every zone reading in working hours fell inside it. The site row comes from the site rollup and will not equal the average of the level rows
- **Zones.** The count is the zone temperature points configured for comfort scoring on each level shown, and the site row is the thermal zones figure in the analytics overview. A level whose points returned no score in the quarter is left out of both

## Data recipes

The scores are `search_indoor_environment(metric:"temperature")`, and the zone counts are one `count_indoor_environment_zones` call.

| `aggregate_entity` | `aggregate_period` | Window   | Feeds                                                        |
| ------------------ | ------------------ | -------- | ------------------------------------------------------------ |
| `level`            | `month`            | quarter  | the snapshot grid                                            |
| `site`             | `month`            | 6 months | the snapshot closing row (last 3) and the trend              |
| `site`             | `all`              | quarter  | the headline score in the operational impact row             |
| `zone`             | `all`              | quarter  | the zone rows, only for a single-level site                  |

- `local_end_date` is exclusive, so pass the first of the month after the last complete month
- Level rows are levels x months, so page at `limit:80` when levels x 3 exceeds 80
- The Zones column is `count_indoor_environment_zones(metric:"temperature", site_ids:[id], aggregate_entity:"level")`: one row per level carrying `included_point_count`, joined to the level rows on `level_id`, and a level it does not return counts 0. It reads current configuration and takes no dates, so it goes in the main batch with the rest. Summed over the levels the level rows return, it is the site row and the analytics overview's thermal zones figure. Never page zone rows to count them
- The zone rows are for the single-level case only, which the level rows reveal, so fetch them after, paging at `limit:80`. They carry `zone_name` and `zone_value`, which is what that case lists
- Do not substitute `search_zones`, `platform.levels` or `platform.zones`. They list zone objects, not zone temperature points
