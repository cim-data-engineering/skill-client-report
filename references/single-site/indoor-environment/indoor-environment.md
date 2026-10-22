# Indoor environment

Owns the operational impact thermal comfort row, the indoor environment health snapshot, and monthly thermal comfort. Scaffold parts: `indoor-environment-snapshot`, `monthly-thermal-comfort`. Script: `scripts/indoor_environment.py`, which builds every figure, row, chart and link below.

## What you write

Nothing. Levels with configured points but no score this quarter are in neither the table nor the thermal zones figure. The script names them to say in chat, not on the page.

## Operational impact row

| Rating chip                               | Metric label                    | Value                                       | Subtitle                                                                           |
| ----------------------------------------- | ------------------------------- | ------------------------------------------- | ---------------------------------------------------------------------------------- |
| See below thermal comfort score benchmark | x.x% thermal comfort maintained | Site thermal comfort score over the quarter | {Up|Down} x.x pp from y.y% in {first month of the quarter} to z.z% in {last month, or the month to date} |

Same movement definition as the snapshot Chg column, the reporting period's last month minus its first in pp, the last being the month to date where the report carries one, so this figure equals the site row Chg in the snapshot below it. Name both endpoint values and their months. Both endpoints come from the `site` series already fetched. Score to 1dp, matching the snapshot.

Section link, labelled "See live indoor environment dashboard", over the quarter. Bundle slot `comfort`:
`https://ace.cimenviro.com/indoor-environment/thermal-comfort?summary_site_id={{site_id}}&summary_ts={{quarter_last_month}}&site_ids={{site_id}}&start_date={{quarter_start}}T00:00:00.000&end_date={{quarter_end}}T00:00:00.000`

## Thermal comfort score benchmark

| Rating    | Thermal comfort score |
| --------- | --------------------- |
| Excellent | >= 92%                |
| Good      | >= 85%                |
| Average   | >= 75%                |
| Poor      | < 75%                 |

## Indoor environment health snapshot

Thermal comfort by level, or by zone for a single-level site  
Date: the quarter. Share of zone readings inside the comfort band set for the site during working hours, by level, in building order

Heatmap table on the `heatmap` component. One row per site level, a score column for each month of the reporting period, the month to date last and headed "to date" where the report carries one, cell value the thermal comfort score to 1dp, closing with a signed change column.

| Column        | Reference                                            |
| ------------- | ---------------------------------------------------- |
| Level         | Site levels that returned a comfort score            |
| Zones         | Thermal zones configured on that level               |
| Month columns | Thermal comfort score for that month x.x%            |
| Chg           | Last month column minus the first, in pp x.x         |

**Display:**

- Color cells per the thermal comfort score benchmark. Color the cell, not the text
- Score to 1dp. The benchmark bands sit far from the data here, so 1dp cannot round across a band edge
- Emphasise only the closing month column, per the `heatmap` component
- Zones as a plain numeral, left of the score columns, never colored and never barred. It sizes the level, so the reader knows whether a swing covers two zones or twenty
- Zones counts the zone temperature points configured for comfort scoring. The site row totals the levels shown, and that total is the thermal zones figure the section hands on. A level whose points returned no score in the quarter has no row and counts in neither
- Chg signed with a direction glyph. Green up, red down, muted when flat
- Sort levels in building order, highest level first, then ground, then basements, not by Chg. The reader is looking for where in the building comfort is drifting, and the Chg column carries the direction
- Close with a site row at the bottom, separated from the level rows
- Site row comes from the site rollup, so it will not equal the average of the level rows. Do not reconcile them
- One level means the level row and the site row are the same figure, so list the zones as the rows instead, from the zone call in Fetch, headed "Thermal comfort by zone". One row per zone, each month the mean of its points' scores. Show each zone's average temperature over its points where the Zones count would go, since a count of 1 says nothing, and the site's average in the site row. Label rows by zone name, adding the unit's letter where one name covers several zones
- Truncate level name with ellipsis, do not wrap rows

**Links:**

- Hyperlink level name to the section link with `&level_ids={level_id}` appended, the row's own id off the level call. Add chevron indicating link >

## Monthly thermal comfort

Where comfort has been heading  
Date: the six complete months ending with the quarter, and the month to date where the report carries one

Chart: Site thermal comfort score. Monthly line chart. Render the two nearest thermal comfort benchmark thresholds and label them: one either side where the series sits inside a band, otherwise the threshold it crosses plus the next one out, so the reader can see which months fall on which side.

**Display:**

- Display values on points, 1dp x.x%
- Add chart title
- The score is the same `site` series as the snapshot site row, so the months they share must agree
- Each value sits over its own month; a month with no score leaves a gap in the line
- Thermal comfort swings hard, so the Y axis follows the data, scaled to fit both thresholds

**Links:**

- Source link on the chart, over the 6 month window the chart draws. Bundle slot `trend_comfort`
- `https://ace.cimenviro.com/indoor-environment/thermal-comfort?summary_site_id={{site_id}}&summary_ts={{quarter_last_month}}&site_ids={{site_id}}&start_date={{trend_start}}T00:00:00.000&end_date={{quarter_end}}T00:00:00.000`

## Notes band items

- **Thermal comfort score.** Comfort band set per zone in PEAK, typically 21–24.9 °C (68–79 °F). The site row is PEAK's site-level score, not an average of the rows below
- **Zones.** Zone temperature points configured for comfort scoring. Levels with no score in the period are excluded here and from the thermal zones figure in the analytics overview

## Data

All in the main batch: `search_indoor_environment(metric:"temperature")` at three groupings, and `count_indoor_environment_zones`.

| Call | Window | Feeds |
| --- | --- | --- |
| `level` × `month`, `limit:80` | quarter | the snapshot grid; paged by `report.py next` when levels × 3 passes 80 |
| `site` × `month` | 6 months | the snapshot closing row (the quarter's months) and the trend |
| `site` × `all` | quarter | the headline score |
| `count_indoor_environment_zones`, `aggregate_entity:"level"` | current configuration | the Zones column and the thermal zones figure |
| `search_zones` for levels with points but no score, `limit:250`, a follow-up | current configuration | their names, for chat |
| `site` × `all`, a follow-up for a site that went live in the quarter | months kept | the headline score |

- The Zones column joins the count's `included_point_count` to the level rows on `level_id`, and a level the count does not return counts 0. Summed over the levels shown, it is the site row and the thermal zones figure. Never page zone rows to count them, and never substitute `search_zones`, `platform.levels` or `platform.zones`: they list zone objects, not zone temperature points
- A single-level site is the one follow-up: `next` asks for `zone` × `month` rows, which carry `zone_name` and `zone_value`
- Levels sort into building order from their names: a name with no readable floor first, then numbered floors highest first, ground (G, GND, GRD, Ground), then basements (B1, Basement 2, or a signed level such as "Level -2"; a hyphen with no space before it is a separator). A building PEAK names oddly is worth a line in chat
- The level count carries no names, so chat names unscored levels from a `search_zones` follow-up

## Newly onboarded sites

A site that went live inside the windows has less history than they ask for, and the section covers what exists.

- A `site` × `month` series that starts after the trend window's first month went live in its first scored month. Comfort rows carry no counts to date the day, so that month is dropped unless nothing follows it
- Every figure, the trend and the date lines take the months kept, whole months only apart from the month to date, the headline from a follow-up `site` × `all` over them, and the section hands on the first month kept and the go-live month
- The snapshot carries only the months kept, so it is only as wide as the data
- A movement needs two months. One month: no movement and no Chg column, rows lowest score first
- A trend needs three points. Under three: no trend, so no monthly thermal comfort section
- A level that began scoring after the site did draws its earlier months and its Chg as dashes with no fill, so the row keeps the table's width. Say in chat when it began scoring
- A gap in the middle of the series is an outage, not onboarding: the chart plots the months that exist and leaves the gap visible; say so in chat
