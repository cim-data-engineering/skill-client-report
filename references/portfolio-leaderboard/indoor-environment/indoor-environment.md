# Indoor environment

Owns the thermal comfort by site table and its portfolio row, and hands on the sites' leaderboard month scores as a ranking and the zone points as the thermal zones figure. Scaffold part: `indoor-environment`. Script: `scripts/indoor_environment.py`, which builds every row, cell and link below.

## What you write

Nothing on the page. In chat, say what the script prints: any site with no comfort score in the quarter, which is left out of the table and the ranking.

## Section header

Eyebrow: Indoor environment health snapshot  
Statement: Thermal comfort by site  
Date line: "{period}. Share of zone readings inside the site's comfort band in PEAK during working hours; the portfolio row averages the sites." The period runs from the quarter's first day to its last, with a spaced hyphen. Where the sites scored differ between the quarter's first and last months, it adds which its Chg compares: "Its Chg compares the 6 sites scored in both July and September."

## Thermal comfort score benchmark

| Rating | Thermal comfort score |
| --- | --- |
| Excellent | >= 92% |
| Good | >= 85% |
| Average | >= 75% |
| Poor | < 75% |

## Ranked heatmap

One row per site with a comfort score in the quarter, ranked by its score for the leaderboard month, then a portfolio row.

| Column | Content |
| --- | --- |
| Rank | Position by the leaderboard month's score; the trophy replaces 1 |
| Site | The site name with its region label in muted brackets, per [How sections fit together](../../../SKILL.md#how-sections-fit-together) |
| Size | Building size, in the portfolio's unit, named in the header |
| Levels | Levels that returned a comfort score in the quarter |
| Zones | Zone temperature points on those levels |
| Target | The site's default comfort band as its PEAK site settings hold it, "21-24.9", in the site's own unit, named under the heading. Where the table's sites use different units, each cell carries its own and the heading none. A dash where PEAK holds no band |
| Month columns | The site's thermal comfort score for each month of the quarter |
| Chg | Last month column minus the first, 1dp, signed with a glyph |

**Ranking:**

- Best first on the score rounded to 2 decimal places, one more than the table prints. Equal scores split alphabetically by site name, ignoring case, so no two sites share a place, and no note explains a tie
- A site with scores in the quarter but none in the leaderboard month ranks after every site that has one, alphabetically

**Portfolio row:**

- Each month's score is the plain average of the sites scored that month, unweighted, so a site with no building size counts like any other
- Size, Levels and Zones are summed over the rows shown. The Zones total is the thermal zones figure it hands on. Target is empty
- Chg compares only the sites scored in both the quarter's first and last months: their average at the end less their average at the start, so a site going live or dropping out is not read as a move. With no site scored at both ends it is a dash

**Display:**

- Color cells per the thermal comfort benchmark, by band, on the printed value, with the band key above the table naming the thresholds
- Scores to 1dp. Only the closing month column carries weight, per the `heatmap` component
- A month a site had no score shows a dash with no fill, and Chg is a dash when either end is missing
- Size, Levels, Zones and Target as plain text, never colored and never barred
- Target is the site's default band, even where levels or zones override it, and carries no margin, marker or note. Sites are scored on the bands set for them, so the column shows what each was scored against. No column where no site has a band
- Every site, not a sample. The table breaks between rows across pages, its header repeating
- Site names wrap to three lines at most rather than truncating

**Links:**

- Each site name links to that site's thermal comfort dashboard over the period, with a chevron:
  `https://ace.cimenviro.com/indoor-environment/thermal-comfort?summary_site_id={{site_id}}&summary_ts={{quarter_last_month}}&site_ids={{site_id}}&start_date={{quarter_start}}T00:00:00.000&end_date={{quarter_end}}T00:00:00.000`
- The section carries the anchor `cf-by-site`

**Hands on:**

- **A ranking** labelled Thermal comfort, under the anchor `cf-by-site`, by month: each site's score for the leaderboard month and for the month before, to 1dp, in the unit "%"
- **Thermal zones**: the Zones total, and every zone temperature point configured across the sites for a quarter in which no site scored
- **Sites with data**: each site with a comfort score in the quarter

**Takes:** the site facts: each site's building size, country and default comfort band

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
- Target needs no call of its own: it is `thermal_comfort_min_temp` and `thermal_comfort_max_temp` from the site facts, read off the overview's `platform.sites` call. Its unit is the one the site's level rows carry, else °F for a US site and °C for any other. Level and zone bands are never read
