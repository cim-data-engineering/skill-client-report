# Overview

The parts every portfolio report carries: the masthead, the scorecard strip and the notes band frame. Scaffold parts: `masthead`, `scorecards`, `notes`. Script: `scripts/overview.py`, which fills every slot below and hands on the site facts.

## What you write

Nothing on the page. In chat, say what the script prints: any site with no building size, and any site whose size was converted into the portfolio's unit.

## Masthead

- Eyebrow: Monthly performance leaderboard
- Title: {Client} portfolio. The HTML title is "{Client} {Leaderboard month} Performance Leaderboard": "Northwind Estates September 2026 Performance Leaderboard"
- Prepared by: {Company name} - {Company service name} · Powered by PEAK. The company name is `name` in `BRAND.md`, CIM by default; the service name is `service-name`, Data Driven Operations by default. Powered by PEAK stays in every brand
- Metadata row: Month, Sites, Author, Issued
  - **Month**: the leaderboard month: "September 2026"
  - **Sites**: the number of sites in the report
  - **Author**: the full name of the logged-in PEAK MCP user, from `who_am_i`
  - **Issued**: the issue date
- The AI disclaimer, verbatim, below the metadata row: "AI was used to help compile this report. All figures, analysis and recommendations were human-reviewed."
- **Client logo**: a slot right of the title block. It holds the logo file the user supplied, passed as `--client-logo`, trimmed of its transparent margins and kept in its own colours. With none supplied the slot is empty and shows nothing. Never search PEAK for a logo and never ask for one
- Never print a PEAK site id in the text. Links carry it in the URL

## Scorecard strip

The analytics overview's stat cards, as a scorecard strip with no section header. Each figure is the sum of the per-site figures.

| Card | Figure |
| --- | --- |
| Portfolio size | The sites' building sizes summed, in square metres or square feet |
| Equipment | Equipment at every site, less the system types |
| Sensors | Sensors at every site |
| Rules running | Rules with status running at every site |
| Thermal zones | The thermal zones figure it takes: zone temperature points on the levels that scored in the quarter, or every configured point where no site scored |

**Sizes and units:**

- A site in the United States records its size in square feet; every other site in square metres
- The portfolio takes the unit that holds most of its floor area. A site recorded in the other unit is converted into it, and the script says so in chat
- A site with no building size counts in no size total and in no size-weighted portfolio row. The script names it in chat

## Notes band items

- **Portfolio rows.** "Scores are weighted by building size; counts are summed." Shown when any section draws a weighted portfolio row

## Data

All in the main batch, the site facts 100 sites a call and each count 10, since an unfiltered count across many more sites runs past the gateway's timeout:

| Need | Call |
| --- | --- |
| Building size, currency, state, country, building photo link | `platform.sites` with `site_ids` |
| Rules running | `search_rules(task_state:"running", limit:1)` with `site_ids`, its `pagination.total` |
| Sensors | `search_favourites(limit:1)` with `site_ids`, its `pagination.total` |
| Equipment | `search_equipment(limit:1)` with `site_ids` twice, plain and filtered to the system types 21, 37, 69, 70, 87, 105 and 114, the second total subtracted from the first |

- The totals of a split call add across its chunks
- The client name comes from `--client`, the author from `who_am_i` passed as `--author`, and the company and service names from `BRAND.md`

**Hands on:** the site facts, each site's building size, currency, state, country and building photo link, before any section builds.

**Takes:** the thermal zones figure, and whether any section drew a weighted portfolio row.
