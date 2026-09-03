# Indoor environment

Owns the operational impact thermal comfort row, the indoor environment health snapshot, and monthly thermal comfort. Scaffold parts: `indoor-environment-snapshot`, `monthly-thermal-comfort`.

## Fetch

`search_indoor_environment(metric:"temperature", aggregate_period:"month", limit:80)`, two calls:

| Call                        | Window   | Feeds                                              |
| --------------------------- | -------- | -------------------------------------------------- |
| `aggregate_entity:"level"`  | quarter  | the snapshot grid                                  |
| `aggregate_entity:"site"`   | 7 months | the snapshot closing row (last 3) and the trend    |
| `aggregate_entity:"site"`, `aggregate_period:"all"` | quarter | the headline score in the operational impact row |

Both windows close on the last complete month: `local_end_date` is exclusive, so pass the first of the month after it. Level rows are levels x months, so page when levels x 3 exceeds 80.

The level rollup carries no zone count, so Zones costs one small call per level: `aggregate_entity:"zone"`, `aggregate_period:"all"`, `level_ids:[one level]`, `limit:1`, read `pagination.total`. It is the most expensive thing in this section.

The column is worth having, and it is not slow: the calls are one row each and all go out together, so a 14-level building costs one batch of 14 tiny responses. Take the per-level counts up to about 25 levels. Above that, make one call for the site total (same query, no `level_ids`), drop the column, and give the site total in the notes instead — floor-by-floor counts in a tower are nearly uniform anyway.

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
- Zones counts scored zones, the same basis as the thermal zones figure in the analytics overview, so the site row should equal it. If it does not, a zone scored in one window and not the other — say which in the notes
- Chg signed with a direction glyph. Green up, red down, muted when flat
- Sort levels in building order, highest level first, ground last — not by Chg. The reader is looking for where in the building comfort is drifting, and the Chg column carries the direction
- Close with a site row at the bottom, same style as the equipment health snapshot
- Site row comes from the site rollup, so it will not equal the average of the level rows. Do not reconcile them
- One level means the level row and the site row are the same figure, so list the zones as the rows instead, from the zone call in Fetch. Show each zone's average temperature where the Zones count would go — a count of 1 says nothing. Label rows by zone name, adding the unit's letter where one name covers several zones
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
- `https://ace.cimenviro.com/indoor-environment/thermal-comfort?summary_site_id={{site_id}}&summary_ts={{quarter_last_month}}&site_ids={{site_id}}&start_date={{trend_start}}T00:00:00.000&end_date={{quarter_end}}T00:00:00.000`

## Notes band items

- **Thermal comfort score.** Share of zone readings inside the ASHRAE comfort band during site working hours. The band is set per zone in PEAK, typically 21-24.9C (68-79F), so a level scores 100% when every zone reading in working hours fell inside it. The site row comes from the site rollup and will not equal the average of the level rows
- **Zones.** The count is scored zones over the quarter. Where it falls short of the analytics overview figure, say how many scored and why the rest did not — usually too few working-hours readings
