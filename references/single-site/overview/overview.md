# Overview

The parts every report carries: the masthead, the analytics overview, and the operational impact and notes frames. Script: `scripts/overview.py`. The rules it follows are in SKILL.md, [What always renders](../../../SKILL.md#what-always-renders), [Operational impact](../../../SKILL.md#operational-impact) and [Notes band](../../../SKILL.md#notes-band).

## What you write

Nothing. The script fills every slot from the saved responses and the figures it takes: the site's name and photo, the reporting period, the author, the issue date, the five overview figures, the operational impact date line and the reporting window note when there is a month to date.

- **Building size**: PEAK stores it in square metres for every site. A US site shows square feet, converted and rounded to the nearest 100 ft²
- **A newly onboarded site**: the reporting period and the operational impact date line start with the first month the sections kept, and the period adds "monitoring live since" the earliest go-live a section hands on, to the day where one is dated, per SKILL.md, [Newly onboarded sites](../../../SKILL.md#newly-onboarded-sites)

## Data

All in the main batch:

| Need | Call |
| --- | --- |
| Name, photo, building size, currency, comfort band | `platform.sites` with those fields; the currency sets the labour rate |
| Rules running | `search_rules(task_state:"running", limit:1)`, its `pagination.total`, system types included: `search_rules` has no type filter |
| Sensors | `search_favourites(limit:1)`, its `pagination.total` |
| Equipment | `search_equipment(limit:1)` twice, plain and filtered to the system types 21, 37, 69, 70, 87, 105 and 114, the second total subtracted from the first |
| Thermal zones, only when no section hands them on | `count_indoor_environment_zones` by level and `search_indoor_environment` level × all over the quarter: points on the levels that scored |

The author comes from `who_am_i`, passed to `report.py plan` as `--author`, and the company and service names from `BRAND.md`.

**Takes:** the thermal zones figure; the names of the figures shown that run partial over the month to date, which the reporting window note lists; and each section's first month kept and go-live, for a site that went live inside the windows.
