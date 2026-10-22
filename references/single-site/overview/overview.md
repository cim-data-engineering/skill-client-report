# Overview

The parts every single-site report carries: the masthead, the analytics overview, and the operational impact and notes band frames around the rows and items the sections own. Script: `scripts/overview.py`, which fills every slot below.

## What you write

Nothing. The script fills every slot from the saved responses and the figures it takes: the site's name and photo, the reporting period, the author, the issue date, the five overview figures, the operational impact date line and the reporting window note when there is a month to date.

## Masthead

- Title: {Site name} Quarterly Building Performance Review
- Prepared by: {Company name} {Company service name}. Powered by PEAK. The company name is `name` in `BRAND.md` or one the user gives, CIM by default; the service name is `service-name`, Data Driven Operations by default. Powered by PEAK stays in every brand
- Reporting period: the quarter as a date range, running to the issue date where the report carries a month to date
- Author: the full name of the logged-in PEAK MCP user, from `who_am_i`, always present, never omitted or substituted
- Issue date
- The AI disclaimer, verbatim, below the metadata row: "AI was used to help compile this report. All figures, analysis and recommendations were human-reviewed."
- The site's `photo_url`, square, right of the title block
- Never print the PEAK site id in the text or the masthead. Links carry it in the URL

## Analytics overview

What we monitor at {site name}  
Date: As at {issue date}

| Display metric | Reference |
| --- | --- |
| Building size | m² as PEAK stores it; ft² for US sites, converted |
| Equipment | Total equipment, less the BACER |
| Sensors | Total sensors |
| Rules | Total rules status running, less the BACER's |
| Thermal zones | Zone temperature points on the levels that scored in the quarter |

All five render whatever sections are chosen. This is the monitoring footprint, not a summary of the sections below it.

- **Building size**: PEAK stores it in square metres for every site. A US site shows square feet, converted and rounded to the nearest 100 ft²
- **Thermal zones**: the figure it takes when one is handed on, so it always equals the comfort site row; counted here, off the same calls, only when none is

## Operational impact

What that monitoring delivered this quarter  
Date: the quarter

A frame around the rows the sections hand on. It renders when at least one row is in, and drops when none is.

- No red in this section. The rating chip reads Excellent or Good on the positive chip, Average or Poor on the warning chip, never the negative one. A movement takes the positive delta when it improves and the muted delta when it declines or holds flat. A fall is stated plainly in the figure, the glyph and the word: reported, not colour coded
- Where a row states a movement, it runs from the reporting period's first month to its last, the month to date where the report carries one, and nothing outside it

## Notes band

Numbered notes in page order, each owned by the section it explains. A note carries business logic the page does not already show: an assumption, a scope rule, or why two figures differ. Anything a legend, chart heading, date line or impact row already says stays out. Each is a short professional definition, not an explanation.

This part owns one item, only when the report carries a month to date:

- **The reporting window**: the month to date and how many of its days it holds, the partial figures it takes, and that scores are unaffected. It closes the band

## Newly onboarded sites

A site that went live inside the windows has less history than they ask for, and the report covers what exists. The reporting period and the operational impact date line start with the first month the sections kept, and the period adds "monitoring live since" the earliest go-live handed on, to the day where one is dated: "Reporting period: 1 – 31 August 2026, monitoring live since 14 July 2026". It is said once, in the masthead, and never repeated section by section.

## Data

All in the main batch:

| Need | Call |
| --- | --- |
| Name, photo, building size, currency, comfort band | `platform.sites` with those fields; the currency sets the labour rate |
| Rules running | `search_rules(task_state:"running", limit:1)`, its `pagination.total`, less that of `tasks.tasks` (`primary_metadata_type_ids:[105]`, `task_state:true`, `limit:1`), the BACER's running rules: `search_rules` has no type filter |
| Sensors | `search_favourites(limit:1)`, its `pagination.total` |
| Equipment | `search_equipment(limit:1)` twice, plain and filtered to the BACER, type 105, the second total subtracted from the first |
| Thermal zones, only when none is handed on | `count_indoor_environment_zones` by level and `search_indoor_environment` level × all over the quarter: points on the levels that scored |

The author comes from `who_am_i`, passed to `report.py plan` as `--author`, and the company and service names from `BRAND.md`.

**Hands on:** the site facts, its name, photo, building size and currency, before any section builds.

**Takes:** the operational impact rows and the notes band items the sections hand on; the thermal zones figure; the names of the figures shown that run partial over the month to date, which the reporting window note lists; and each section's first month kept and go-live, for a site that went live inside the windows.
