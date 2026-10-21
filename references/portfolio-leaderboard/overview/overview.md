# Overview

The parts every portfolio report carries: the masthead and the scorecard strip. Scaffold parts: `masthead`, `scorecards`. Script: `scripts/overview.py`, which fills every slot below and hands on the site facts.

## What you write

Nothing on the page. In chat, say what the script prints: any site with no data anywhere in the report, left out of the Sites count; any site with no building size; and any site whose size shows in a unit other than its own.

## Masthead

- Eyebrow: Monthly performance leaderboard
- Title: {Client} portfolio. The HTML title is "{Client} {Leaderboard month} Performance Leaderboard": "Northwind Estates September 2026 Performance Leaderboard"
- Prepared by: {Company name} - {Company service name} · Powered by PEAK. The company name is `name` in `BRAND.md`, CIM by default; the service name is `service-name`, Data Driven Operations by default. Powered by PEAK stays in every brand
- Metadata row: Month, Sites, Author, Issued
  - **Month**: the leaderboard month: "September 2026"
  - **Sites**: the sites with data somewhere in the report: an equipment health or comfort score in the quarter, an action resolved in the quarter, an open P1-2 action, a row in the sustainability ratings table, or a key win. Each section marks the sites it shows, and the fill adds a site that shows only through a win. A site with none is left out of the count and named in chat; its equipment, sensors and rules still count in the scorecards. Where no section shows a site, every site counts
  - **Author**: the full name of the logged-in PEAK MCP user, from `who_am_i`
  - **Issued**: the issue date, the earliest local date across the sites, so the leaderboard month has closed at every one
- The AI disclaimer, verbatim, below the metadata row: "AI was used to help compile this report. All figures, analysis and recommendations were human-reviewed."
- **Client logo**: a slot right of the title block. It holds only a logo file the user supplied, passed as `--client-logo`: a raster logo trimmed of its transparent margins, an SVG as it is, each in its own colours. A logo dark enough to vanish on the navy masthead sits on a light tile. With none supplied the slot is empty and shows nothing. Never search PEAK for a logo and never ask for one
  - `report.py plan` refuses a file inside this skill or inside a brand overlay, any folder holding a `BRAND.md`: those are sample and partner logos, never a client's. A brand overlay's logos go to the masthead, never this slot
  - The fill reads the file each time it runs, so the bundle holds no logo, and a logo added to or dropped from the plan shows on the next fill
- Never print a PEAK site id in the text. Links carry it in the URL

## Scorecard strip

The analytics overview's stat cards, as a scorecard strip with no section header. Each figure is the sum of the per-site figures.

| Card | Figure |
| --- | --- |
| Portfolio size | The sites' building sizes summed, in the portfolio's unit |
| Equipment | Equipment at every site, less the system types |
| Sensors | Sensors at every site |
| Rules running | Rules with status running at every site |
| Thermal zones | The thermal zones figure it takes: zone temperature points on the levels that scored in the quarter, or every configured point where no site scored |

**Sizes and units:**

- PEAK stores every site's building size in square metres, US sites included
- A site in the United States reads in square feet: the stored figure × 10.7639, rounded to the nearest 100 ft². A size is converted, never relabelled
- The portfolio takes the unit most of its floor area reads in, so a mostly US portfolio shows ft² and any other m². Every size shows in that unit, and the script names in chat any site shown in a unit other than its own
- A site with no building size counts in no size total, and in no sustainability ratings portfolio row, the one row weighted by size. The script names it in chat

## Data

All in the main batch, the site facts 100 sites a call and each count 10, since an unfiltered count across many more sites runs past the gateway's timeout:

| Need | Call |
| --- | --- |
| Building size, currency, state, country, building photo link, default comfort band | `platform.sites` with `site_ids`, the band as `thermal_comfort_min_temp`, `thermal_comfort_max_temp` and `thermal_comfort_margin`, in the site's own unit |
| Rules running | `search_rules(task_state:"running", limit:1)` with `site_ids`, its `pagination.total` |
| Sensors | `search_favourites(limit:1)` with `site_ids`, its `pagination.total` |
| Equipment | `search_equipment(limit:1)` with `site_ids` twice, plain and filtered to the system types 21, 37, 69, 70, 87, 105 and 114, the second total subtracted from the first |

- The totals of a split call add across its chunks
- The client name comes from `--client`, the author from `who_am_i` passed as `--author`, and the company and service names from `BRAND.md`

**Hands on:** the site facts, each site's building size, currency, state, country, building photo link and default comfort band, before any section builds.

**Takes:** the thermal zones figure, and the sites with data, which is why it builds after every other section.
