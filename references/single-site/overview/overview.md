# Overview

The parts every report carries: the masthead, the analytics overview, and the operational impact and notes frames. Script: `scripts/overview.py`. The rules it follows are in SKILL.md, [What always renders](../../../SKILL.md#what-always-renders), [Operational impact](../../../SKILL.md#operational-impact) and [Notes band](../../../SKILL.md#notes-band).

## What you write

Nothing. The script fills every slot from the saved responses and the figures it takes: the site's name and photo, the reporting period, the author, the issue date, the five overview figures, the operational impact date line and the reporting window note when there is a month to date.

- **Building size**: PEAK stores every site's building size in square metres, US sites included. A site in the United States shows it in square feet, converted and rounded to the nearest 100 ft²; every other site shows square metres as stored
- **A newly onboarded site**: when a section's scores start inside the windows, the reporting period and the operational impact date line start with the first month the sections kept, and the masthead says once when monitoring went live: "1 Aug – 21 Oct 2026, monitoring live since 30 Jul 2026". The day is the one equipment health dates its first checks to; with no day to go on, the month alone ("since Jul 2026"). See SKILL.md, [Newly onboarded sites](../../../SKILL.md#newly-onboarded-sites)

## Data

All in the main batch:

| Need | Call |
| --- | --- |
| Name, photo, building size, currency, comfort band | `platform.sites` with those fields; the currency sets the labour rate |
| Rules running | `search_rules(task_state:"running", limit:1)`, its `pagination.total`: every running rule, the system types' included, since `search_rules` takes no equipment type filter |
| Sensors | `search_favourites(limit:1)`, its `pagination.total` |
| Equipment | `search_equipment(limit:1)` twice, plain and filtered to the system types 21, 37, 69, 70, 87, 105 and 114, the second total subtracted from the first |
| Thermal zones, only when no section hands them on | `count_indoor_environment_zones` by level and `search_indoor_environment` level × all over the quarter: points on the levels that scored |

The author comes from `who_am_i`, passed to `report.py plan` as `--author`, and the company and service names from `BRAND.md`.

**Takes:** the thermal zones figure; the names of the figures shown that run partial over the month to date, which the reporting window note lists; and, for a site that went live inside the windows, the first month each section kept and the month (and day, where known) its scores start.
