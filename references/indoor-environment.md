# Indoor environment

Owns the operational impact thermal comfort row, the indoor environment health snapshot, and monthly thermal comfort. Scaffold parts: `indoor-environment-snapshot`, `monthly-thermal-comfort`.

## Fetch

`search_indoor_environment(metric:"temperature", aggregate_period:"month", limit:80)`, two calls:

| Call                        | Window   | Feeds                                              |
| --------------------------- | -------- | -------------------------------------------------- |
| `aggregate_entity:"level"`  | quarter  | the snapshot grid                                  |
| `aggregate_entity:"site"`   | 7 months | the snapshot closing row (last 3) and the trend    |

Both windows close on the last complete month: `local_end_date` is exclusive, so pass the first of the month after it. Level rows are levels x months, so page when levels x 3 exceeds 80.

The level rollup carries no zone count, so Zones needs `aggregate_entity:"zone"`, `aggregate_period:"all"`, `level_ids:[one level]`, `limit:1`, read `pagination.total` — one small call per level, and the most expensive thing in this section.

Cap that cost. Up to about a dozen levels, take the per-level counts. Above that, one call for the site total (same query, no `level_ids`) and drop the Zones column from the table: on a 25-storey tower the column would cost more calls than the rest of the report, and floor-by-floor zone counts in a tower are nearly uniform anyway. Give the site total in the notes either way.

Do not substitute `platform.levels` or `platform.zones`. They count zone *objects*, not zone temperature points — at one 25-level site that was 340 against 200 scored zones, which would contradict the thermal zones figure in the analytics overview. `has_ie_config` on `platform.zones` means a zone-specific override, not participation in the score.

## Operational impact row

| Rating chip                               | Metric label                    | Value                                    | Subtitle                                                                        |
| ----------------------------------------- | ------------------------------- | ---------------------------------------- | ------------------------------------------------------------------------------- |
| See below thermal comfort score benchmark | x.x% thermal comfort maintained | Site thermal comfort score over the quarter | {Up\|Down} x.x pp from y.y% in {first month of the quarter} to z.z% in {last month} |

Same movement definition as the snapshot Chg column — the quarter's last month minus its first, in pp — so this figure equals the site row Chg in the snapshot below it. Name both endpoint values and their months. Both endpoints come from the `site` series already fetched. Score to 1dp, matching the snapshot.

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

Heatmap table on the same `heatmap` component as the equipment health snapshot. One row per site level, three score columns — the months of the quarter — cell value the thermal comfort score to 1dp, closing with a signed change column.

| Column        | Reference                                             |
| ------------- | ----------------------------------------------------- |
| Level         | Site levels with at least one thermal zone            |
| Zones         | Thermal zones on that level that returned a score     |
| Month columns | Thermal comfort score for that month x.x%             |
| Chg           | Last month of the quarter minus the first, in pp x.x  |

**Display:**

- Color cells per the thermal comfort score benchmark. Color the cell, not the text
- Score to 1dp. The benchmark bands sit far from the data here, so 1dp cannot round across a band edge
- Emphasise only the closing month column, per the `heatmap` component
- Zones as a plain numeral, left of the score columns, never colored and never barred — it sizes the level, so the reader knows whether a swing covers two zones or twenty
- Zones counts scored zones, so the site row can fall short of the thermal zones count in the analytics overview, which counts every zone temperature point. Say so in the notes rather than reconciling them
- Chg signed with a direction glyph. Green up, red down, muted when flat
- Sort levels in building order, highest level first, ground last — not by Chg. The reader is looking for where in the building comfort is drifting, and the Chg column carries the direction
- Close with a site row at the bottom, same style as the equipment health snapshot
- Site row comes from the site rollup, so it will not equal the average of the level rows. Do not reconcile them
- Truncate level name with ellipsis, do not wrap rows

**Links:**

- Hyperlink level name to PEAK with the same quarter as a custom date range, add chevron indicating link >
- `https://ace.cimenviro.com/indoor-environment/thermal-comfort?summary_site_id={{site_id}}&summary_ts={{quarter_last_month}}&site_ids={{site_id}}&start_date={{quarter_start}}T00:00:00.000&end_date={{quarter_end}}T00:00:00.000`

## Monthly thermal comfort

Where comfort has been heading
Date: the seven complete months ending with the quarter

Chart: Site thermal comfort score. A monthly line chart built like Chart 1 in monthly equipment health, against the thermal comfort benchmark thresholds.

**Display:**

- Display values on points, 1dp x.x%
- Add chart title
- The score is the same `site` series as the snapshot site row, so the months they share must agree
- Thermal comfort swings harder than equipment health, so let the Y axis follow the data rather than reusing the equipment health scale

**Links:**

- Source link on the chart, over the 7 month window. Use custom dates, not a relative range — the report is a fixed quarter and must keep showing the same window as it ages
- `https://ace.cimenviro.com/indoor-environment/thermal-comfort?summary_site_id={{site_id}}&summary_ts={{quarter_last_month}}&site_ids={{site_id}}&level_ids={{level_id}}&start_date={{trend_start}}T00:00:00.000&end_date={{quarter_end}}T00:00:00.000`

## Notes band items

- **Thermal comfort score.** Share of zone readings inside the ASHRAE comfort band during site working hours. The band is set per zone in PEAK, typically 21-24.9C (68-79F), so a level scores 100% when every zone reading in working hours fell inside it. The site row comes from the site rollup and will not equal the average of the level rows
- **Zones.** The count is scored zones over the quarter, against the zone temperature points in the analytics overview. Say how many scored, and why the rest did not — usually too few working-hours readings
