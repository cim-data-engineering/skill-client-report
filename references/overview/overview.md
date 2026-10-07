# Overview

The parts every report carries: the masthead, the analytics overview, the operational impact and notes frames, and the footer. Script: `scripts/overview.py`. The rules it follows are in SKILL.md, [What always renders](../../SKILL.md#what-always-renders), [Operational impact](../../SKILL.md#operational-impact) and [Notes band](../../SKILL.md#notes-band).

## What you write

Nothing. The overview builds last, after the sections, so it can take the thermal zones figure off the indoor environment site row, and it fills every slot from the saved responses: the site's name and photo, the reporting period, the author, the issue date, the five overview figures, the operational impact date line, the reporting window note and the footer.

## Data

Five calls, all in the main batch, plus two when Indoor environment is out:

| Need | Call |
| --- | --- |
| Name, photo, building size, currency, comfort band | `platform.sites` with those fields; the currency sets the labour rate |
| Rules running | `search_rules(task_state:"running", limit:1)`, its `pagination.total` |
| Sensors | `search_favourites(limit:1)`, its `pagination.total` |
| Equipment | `search_equipment(limit:1)` twice, plain and filtered to the system types 21, 37, 69, 70, 87, 105 and 114, the second total subtracted from the first |
| Thermal zones, only with Indoor environment out | `count_indoor_environment_zones` by level and `search_indoor_environment` level × all over the quarter: points on the levels that scored, the same figure the snapshot's site row would print |

The author comes from `who_am_i`, passed to `report.py plan` as `--author`, and the company and service names from `BRAND.md`.
