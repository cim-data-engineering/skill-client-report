# Indoor environment

Owns the operational impact thermal comfort row, the indoor environment health snapshot, and monthly thermal comfort. Scaffold parts: `indoor-environment-snapshot`, `monthly-thermal-comfort`.

## Operational impact row

| Rating chip                               | Metric label                    | Value                                       | Subtitle                                                                           |
| ----------------------------------------- | ------------------------------- | ------------------------------------------- | ---------------------------------------------------------------------------------- |
| See below thermal comfort score benchmark | x.x% thermal comfort maintained | Site thermal comfort score over the quarter | {Up|Down} x.x pp from y.y% in {first month of the quarter} to z.z% in {last month} |

Same movement definition as the snapshot Chg column, the quarter's last month minus its first in pp, so this figure equals the site row Chg in the snapshot below it. Name both endpoint values and their months. Both endpoints come from the `site` series already fetched. Score to 1dp, matching the snapshot.

Section link, labelled "See live indoor environment dashboard":  
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
| Level         | Site levels with at least one thermal zone           |
| Zones         | Thermal zones on that level that returned a score    |
| Month columns | Thermal comfort score for that month x.x%            |
| Chg           | Last month of the quarter minus the first, in pp x.x |

**Display:**

- Color cells per the thermal comfort score benchmark. Color the cell, not the text
- Score to 1dp. The benchmark bands sit far from the data here, so 1dp cannot round across a band edge
- Emphasise only the closing month column, per the `heatmap` component
- Zones as a plain numeral, left of the score columns, never colored and never barred. It sizes the level, so the reader knows whether a swing covers two zones or twenty
- Zones counts scored zones, the same basis as the thermal zones figure in the analytics overview, so the site row should equal it. If it does not, a zone scored in one window and not the other, so say which in the notes
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

- Source link on the chart, over the 6 month window. Use custom dates, not a relative range. The report is a fixed quarter and must keep showing the same window as it ages
- `https://ace.cimenviro.com/indoor-environment/thermal-comfort?summary_site_id={{site_id}}&summary_ts={{quarter_last_month}}&site_ids={{site_id}}&start_date={{trend_start}}T00:00:00.000&end_date={{quarter_end}}T00:00:00.000`

## Notes band items

- **Thermal comfort score.** Share of zone readings inside the ASHRAE comfort band during site working hours. The band is set per zone in PEAK, typically 21-24.9C (68-79F), so a level scores 100% when every zone reading in working hours fell inside it. The site row comes from the site rollup and will not equal the average of the level rows
- **Zones.** The count is scored zones over the quarter. Where it falls short of the analytics overview figure, say how many scored and why the rest did not, usually too few working-hours readings

## Data recipes

All of it is `search_indoor_environment(metric:"temperature")`.

| `aggregate_entity` | `aggregate_period` | Window   | Feeds                                                        |
| ------------------ | ------------------ | -------- | ------------------------------------------------------------ |
| `level`            | `month`            | quarter  | the snapshot grid                                            |
| `site`             | `month`            | 6 months | the snapshot closing row (last 3) and the trend              |
| `site`             | `all`              | quarter  | the headline score in the operational impact row             |
| `zone`             | `all`              | quarter  | the Zones column, and the site total from `pagination.total` |

- `local_end_date` is exclusive, so pass the first of the month after the last complete month
- Level rows are levels x months, so page at `limit:80` when levels x 3 exceeds 80
- The zone rows carry `level_id` and `level_name`, so never call once per level with `level_ids`. Page the unfiltered call at `limit:80` and tally the levels yourself: 200 zones is three calls whatever the building's height, and `pagination.total` on the first page is the site total. The rows also carry `zone_name` and `zone_value`, which is what the single-level case needs, so that costs nothing extra either
- Where a tower is tall enough that the column stops earning its width, drop the column and give the site total in the notes. A tower's floors carry near-identical zone counts, so past about a dozen levels the column prints the same number over and over. At one 25-level site, 19 floors had exactly eight. That is a display decision now, not a fetch one
- Do not substitute `platform.levels` or `platform.zones`. They count zone objects, not zone temperature points. At one 25-level site that was 340 against 200 scored zones
