# Overview

The parts every portfolio report carries: the masthead, the scorecard strip and the notes band frame. Scaffold parts: `masthead`, `scorecards`, `notes`. Script: `scripts/overview.py`, which fills every slot below and hands each section the sites' building sizes before any of them builds.

## What you write

Nothing. The overview builds last, so it takes the thermal zones figure off the indoor environment section and the notes frame off whichever sections drew a portfolio row. It names in chat any site with no building size, and any site whose size was converted into the portfolio's unit.

## Masthead

- Eyebrow: Quarterly building performance review
- Title: {Client} portfolio. The HTML title is "{Client} Portfolio Quarterly Building Performance Review"
- Prepared by: {Company name} - {Company service name} · Powered by PEAK. The company name is `name` in `BRAND.md`, CIM by default; the service name is `service-name`, Data Driven Operations by default. Powered by PEAK stays in every brand
- Metadata row: Reporting period, Sites, Author, Issued
  - **Reporting period**: the quarter's first day to its last, or to the issue date where the report carries a month to date, with a spaced hyphen: "1 Jul - 21 Oct 2026"
  - **Sites**: the number of sites in the report
  - **Author**: the full name of the logged-in PEAK MCP user, from `who_am_i`
  - **Issued**: the issue date
- The AI disclaimer, verbatim, below the metadata row: "AI was used to help compile this report. All figures, analysis and recommendations were human-reviewed."
- **Client logo**: a slot right of the title block. It holds the logo file the user supplied, passed as `--client-logo`, trimmed of its transparent margins and kept in its own colours. With none supplied the slot is empty and shows nothing. Never search PEAK for a logo and never ask for one
- Never print a PEAK site id in the text. Links carry it in the URL

## Scorecard strip

The analytics overview's stat cards, set straight under the masthead with no section header, so page one has room for the leaderboard. Each figure is the sum of the per-site figures.

| Card | Figure |
| --- | --- |
| Portfolio size | The sites' building sizes summed, in square metres or square feet |
| Equipment | Equipment at every site, less the system types (the platform checking itself, not plant) |
| Sensors | Sensors at every site |
| Rules running | Rules with status running at every site |
| Thermal zones | Zone temperature points on the levels that scored in the quarter, the same figure the thermal comfort table totals |

**Sizes and units:**

- A site in the United States records its size in square feet; every other site in square metres
- The portfolio takes the unit that holds most of its floor area. A site recorded in the other unit is converted into it, and the script says so in chat
- A site with no building size counts in no size total and in no size-weighted portfolio row. The script names it in chat

## Notes band items

Numbered in report order, each owned by the section it explains. A note carries business logic the page does not already show; anything a legend, heading or date line says stays out. This section owns two:

- **Portfolio rows.** "Scores are weighted by building size; counts are summed." Shown when any section draws a weighted portfolio row. It opens the band
- **The reporting window.** Shown when the report carries a month to date: the month, how many of its days it holds, that actions resolved this quarter include those days when the actions section is in, and that scores are unaffected. It closes the band

## Data

All in the main batch, each split at 100 sites a call:

| Need | Call |
| --- | --- |
| Building size, currency, state, country | `platform.sites` with `site_ids` |
| Rules running | `search_rules(task_state:"running", limit:1)` with `site_ids`, its `pagination.total` |
| Sensors | `search_favourites(limit:1)` with `site_ids`, its `pagination.total` |
| Equipment | `search_equipment(limit:1)` with `site_ids` twice, plain and filtered to the system types 21, 37, 69, 70, 87, 105 and 114, the second total subtracted from the first |

- The totals of a split call add across its chunks
- Thermal zones come from the indoor environment section's figures. When that section has no data, the figure is every zone temperature point configured across the sites, off the same section's zone count
- The client name comes from `--client`, the author from `who_am_i` passed as `--author`, and the company and service names from `BRAND.md`
