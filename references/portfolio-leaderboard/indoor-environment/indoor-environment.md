# Indoor environment

Owns the thermal comfort by site table and its portfolio row, and hands on the sites' leaderboard month scores as a ranking and the zone points that scored as the thermal zones figure. Scaffold part: `indoor-environment`. Script: `scripts/indoor_environment.py`, which builds every row, cell and link below.

## What you write

Nothing on the page. In chat, say what the script prints: any site with no comfort score in the quarter, which is left out of the table and the ranking, and any site with too few zones to lead, starred and ranked after the rest.

## Section header

Eyebrow: Indoor environment health snapshot  
Statement: Thermal comfort by site  
Date line: "{period}. Share of zone readings inside the site's comfort band during working hours." The period runs from the quarter's first day to its last, with a spaced hyphen. Where the sites scored differ between the quarter's first and last months, it adds "Its Chg compares the {N} sites scored in both {first month} and {last month}."

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
| Site | The site name with its region label in muted brackets |
| Size | Building size, in the portfolio's unit, named in the header |
| Levels | Levels that returned a comfort score in the quarter |
| Zones | Zone temperature points that returned a comfort score in the quarter |
| Target | The site's default comfort band in PEAK, "21-24.9", in the site's own unit, named under the heading, or in each cell where the sites' units differ. A dash where PEAK holds none |
| Month columns | The site's thermal comfort score for each month of the quarter |
| Chg | Last month column minus the first, 1dp, signed with a glyph |

**Ranking:**

- Best first on the score rounded to 2 decimal places, one more than the table prints. Equal scores split alphabetically by site name, ignoring case, so no two sites share a place, and no note explains a tie
- A site with scores in the quarter but none in the leaderboard month ranks after every site that has one, alphabetically
- **Too few zones to lead**: a site with fewer than 20 zones, and at or under 30% of the median across the sites in the table, ranks after every other site with a score, by its score, here and on last month's board. An asterisk follows its name, and under the table: "* Low zone count, ranked after the other sites." No site is starred where every site has fewer than 20, so a portfolio of small sites keeps its order

**Portfolio row:**

- Each month's score is the plain average of the sites scored that month
- Size, Levels and Zones are summed over the rows shown. The Zones total is the thermal zones figure it hands on. Target is empty
- Chg is the last month less the first over only the sites scored in both, so a site going live or dropping out is not read as a move; a dash where no site was

**Display:**

- Region label: the site's state, or its country where the portfolio spans countries; none where every site shares one, or where the name already ends in brackets
- Color cells per the thermal comfort benchmark, by band, on the printed value, with the band key above the table naming the thresholds
- Scores to 1dp. Only the closing month column carries weight, per the `heatmap` component
- A month a site had no score shows a dash with no fill, and Chg is a dash when either end is missing
- Size, Levels, Zones and Target as plain text, never colored and never barred
- Target is the site's default band even where levels or zones override it, with no margin, marker or note. No column where no site has a band
- Every site, not a sample. The table breaks between rows across pages, its header repeating
- Site names wrap to three lines at most rather than truncating

**Links:**

- Each site name links to that site's thermal comfort dashboard over the period, with a chevron:
  `https://ace.cimenviro.com/indoor-environment/thermal-comfort?summary_site_id={{site_id}}&summary_ts={{quarter_last_month}}&site_ids={{site_id}}&start_date={{quarter_start}}T00:00:00.000&end_date={{quarter_end}}T00:00:00.000`
- The section carries the anchor `cf-by-site`

**Hands on:**

- **A ranking** labelled Thermal comfort, under the anchor `cf-by-site`, by month: each site's score for the leaderboard month and for the month before, to 1dp, in the unit "%", and the sites with too few zones to lead, for the reason "Low zone count"
- **Thermal zones**: the Zones total
- **Sites with data**: each site with a comfort score in the quarter

## Data

All in the main batch, every call with `metric:"temperature"`:

| Call | Window | Feeds |
| --- | --- | --- |
| `search_indoor_environment`, `site` × `month`, `limit:80`, 100 sites a call | quarter | the month cells, the board and its movement |
| `search_indoor_environment`, `level` × `all`, `limit:80`, 100 sites a call | quarter | Levels: each site's levels that returned a score |
| `search_indoor_environment`, `zone` × `all`, `limit:1`, a call a site | quarter | Zones: the `pagination.total`, a row per point that returned a score |

- Both `level` and `site` calls page at 80 rows: `report.py next` asks for each further page from the first page's total
- Zones takes a call a site because PEAK holds no dated zone count, and a one-row page's total counts the site's points without fetching them. A zone with two points counts twice. Never count zones from `search_zones`, `platform.levels`, `platform.zones` or `count_indoor_environment_zones`: they list configured zones, not points that returned a score
- With no comfort score at any site the section drops and hands on no thermal zones
- Target needs no call of its own: it is `thermal_comfort_min_temp` and `thermal_comfort_max_temp` from the site facts, in the unit the site's level rows carry, else °F for a US site and °C otherwise
