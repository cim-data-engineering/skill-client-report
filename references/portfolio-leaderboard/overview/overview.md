# Overview

The parts every portfolio report carries: the masthead and the scorecard strip. Scaffold parts: `masthead`, `scorecards`. Script: `scripts/overview.py`, which fills every slot below and hands on the site facts.

## What you write

Nothing on the page. In chat, say what the script prints: any site with no data anywhere in the report, left out of the Sites count; any site with no building size; and any site whose size shows in a unit other than its own.

## Masthead

- Eyebrow: Monthly performance leaderboard
- Title: {Client} portfolio. The HTML title is "{Client} {Leaderboard month} Performance Leaderboard": "Northwind Estates September 2026 Performance Leaderboard"
- Prepared by: {Company name} - {Company service name} · Powered by PEAK. The company name is `name` in `BRAND.md`, CIM by default; the service name is `service-name`, Data Driven Operations by default. Powered by PEAK stays in every brand
- Metadata row: Sites, Author, Issued
  - **Sites**: the sites with data, the figure it takes: each site the report shows data for. A site with none is left out of the count and named in chat; its sensors still count in the scorecards
  - **Author**: the full name of the logged-in PEAK MCP user, from `who_am_i`
  - **Issued**: the issue date, the earliest local date across the sites, so the leaderboard month has closed at every one
- The AI disclaimer, verbatim, below the metadata row: "AI was used to help compile this report. All figures, analysis and recommendations were human-reviewed."
- **Client logo**: a slot right of the title block. It holds only the logo file the user supplied, passed as `--client-logo` and read at fill: a raster logo trimmed of its transparent margins, an SVG as it is, each in its own colours, a dark one on a light tile. `report.py plan` refuses a file inside this skill or a brand overlay (a folder holding a `BRAND.md`). With none supplied the slot is empty and shows nothing. Never search PEAK for a logo and never ask for one
- Never print a PEAK site id in the text. Links carry it in the URL

## Scorecard strip

The analytics overview's stat cards, as a scorecard strip with no section header. Each figure is the sum of the per-site figures. An Equipment, Rules or Thermal zones card with nothing scored behind it is left out.

| Card | Figure |
| --- | --- |
| Portfolio size | The sites' building sizes summed, in the portfolio's unit |
| Equipment | The scored equipment it takes: equipment with a rule scored in the quarter, the equipment health portfolio row's Equip |
| Sensors | Sensors at every site |
| Rules | The scored rules it takes: rules scored in the quarter, the equipment health portfolio row's Rules |
| Thermal zones | The thermal zones figure it takes: zone temperature points that returned a comfort score in the quarter, the thermal comfort portfolio row's Zones |

**Sizes and units:**

- PEAK stores every site's building size in square metres, US sites included
- A site in the United States reads in square feet: the stored figure × 10.7639, rounded to the nearest 100 ft². A size is converted, never relabelled
- The portfolio takes the unit most of its floor area reads in, and the script names in chat any site shown in a unit other than its own
- A site with no building size counts in no size total. The script names it in chat

## Data

All in the main batch, the site facts 100 sites a call and the sensor count 10, since an unfiltered count across many more sites runs past the gateway's timeout:

| Need | Call |
| --- | --- |
| Building size, currency, state, country, building photo link, default comfort band | `platform.sites` with `site_ids`, the band as `thermal_comfort_min_temp`, `thermal_comfort_max_temp` and `thermal_comfort_margin`, in the site's own unit |
| Sensors | `search_favourites(limit:1)` with `site_ids`, its `pagination.total` |

- The totals of a split call add across its chunks
- The client name comes from `--client`, the author from `who_am_i` passed as `--author`, and the company and service names from `BRAND.md`

**Hands on:** the site facts, each site's building size, currency, state, country, building photo link and default comfort band, before any section builds.

**Takes:** the scored equipment and rules, the thermal zones figure, and the sites with data.
