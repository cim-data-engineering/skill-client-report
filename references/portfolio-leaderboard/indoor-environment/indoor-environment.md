# Indoor environment

Owns the thermal comfort by site table and its portfolio row, and hands on the sites' scores as a ranking and the zone points as the thermal zones figure. Scaffold part: `indoor-environment`. Script: `scripts/indoor_environment.py`, which builds every row, cell and link below.

## What you write

Nothing on the page. In chat, say what the script prints: any site with no comfort score in the quarter, which is left out of the table and the ranking.

## Section header

Eyebrow: Indoor environment health snapshot  
Statement: Thermal comfort by site  
Date line: "{period}. Share of zone readings inside the ASHRAE comfort band during working hours." The period runs from the quarter's first day to its last, or to the issue date where the report carries a month to date, with a spaced hyphen.

## Thermal comfort score benchmark

| Rating | Thermal comfort score |
| --- | --- |
| Excellent | >= 92% |
| Good | >= 85% |
| Average | >= 75% |
| Poor | < 75% |

## Ranked heatmap

One row per site with a comfort score in the quarter, ranked by its score for the period's last month, then a portfolio row.

| Column | Content |
| --- | --- |
| Rank | Position by the last month's score; the trophy replaces 1 |
| Site | The site name with its state abbreviation in muted brackets |
| Size | Building size, in the portfolio's unit, named in the header |
| Levels | Levels that returned a comfort score in the quarter |
| Zones | Zone temperature points on those levels |
| Month columns | The site's thermal comfort score for each month of the quarter, then the month to date headed "to date" |
| Chg | Last month column minus the first, 1dp, signed with a glyph |

**Ranking:**

- Best first on the unrounded score. Equal scores split alphabetically by site name, ignoring case. No shared places and no notes explaining ties
- A site with scores in the quarter but none in its last month ranks after every site that has one, alphabetically

**Portfolio row:**

- Each month's score is weighted by building size over the sites with a score that month. A site with no building size is left out of the weighting
- Size, Levels and Zones are summed over the rows shown. The Zones total is the thermal zones figure it hands on
- Chg is the portfolio row's own last month less its first

**Display:**

- Color cells per the thermal comfort benchmark, by band, on the printed value, with the band key above the table naming the thresholds
- Scores to 1dp. Only the closing month column carries weight, per the `heatmap` component
- A month a site had no score shows a dash with no fill, and Chg is a dash when either end is missing
- Size, Levels and Zones as plain numerals, never colored and never barred
- Every site, not a sample. The table breaks between rows across pages, its header repeating

**Links:**

- Each site name links to that site's thermal comfort dashboard over the period, with a chevron:
  `https://ace.cimenviro.com/indoor-environment/thermal-comfort?summary_site_id={{site_id}}&summary_ts={{quarter_last_month}}&site_ids={{site_id}}&start_date={{quarter_start}}T00:00:00.000&end_date={{quarter_end}}T00:00:00.000`
- The section carries the anchor `cf-by-site`

**Hands on:**

- **A ranking** labelled Thermal comfort, under the anchor `cf-by-site`, over months: each site's score for the period's first and last month, to 1dp
- **Thermal zones**: the Zones total, and every zone temperature point configured across the sites for a quarter in which no site scored

## Notes band items

None. The date line defines the score.

## Data

All in the main batch, every call with `metric:"temperature"`:

| Call | Window | Feeds |
| --- | --- | --- |
| `search_indoor_environment`, `site` × `month`, `limit:80`, 100 sites a call | quarter | the month cells, the board and its movement |
| `search_indoor_environment`, `level` × `all`, `limit:80`, 100 sites a call | quarter | Levels: each site's levels that returned a score |
| `count_indoor_environment_zones`, `aggregate_entity:"level"`, 10 sites a call | current configuration | Zones, joined to the scored levels on `level_id` |

- Both `search_indoor_environment` calls page at 80 rows: `report.py next` asks for each further page from the first page's total
- The zone count returns every level in one response, which PEAK refuses past 40,000 characters, so it takes ten sites a call
- Zones counts `included_point_count`, points configured for comfort scoring. A level that returned no score counts in neither column. Never count zone objects from `search_zones`, `platform.levels` or `platform.zones`: they are not zone temperature points
- With no comfort score at any site the section drops, and still hands on every configured point across the sites, off the same zone count
