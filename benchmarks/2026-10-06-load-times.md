# Client report load times, before and after the count tools

Measured 6 October 2026 by six runners, one per site per recipe, run side by side so each pair saw the same PEAK load.
Each section ran alone, as if it were the only one selected. **Ready** runs from a section's first call being written to the next section's first,
so it covers writing the calls, the calls themselves, any follow-up round, and working out the figures. **Fetch** stops at the last result.
Key wins is unchanged, and the old runs ended on it with no clean end marker, so it is compared on fetch.
Equipment health and key wins make identical calls in both recipes, so their differences, up to 13%, are the run-to-run noise.

## 44 Market Street (site 552)

| Section | Before | After | Change | Fetch before → after | Calls (rounds) before → after | Data before → after | Spilled to file |
|---|---|---|---|---|---|---|---|
| Masthead and overview | 12 s | 11 s | -10% | 9 s → 8 s | 7 (1) → 7 (1) | 6K → 5K chars | 0 → 0 |
| Equipment health | 21 s | 22 s | +5% | 8 s → 9 s | 7 (1) → 7 (1) | 37K → 37K chars | 0 → 0 |
| Indoor environment | 129 s | 61 s | -52% | 34 s → 5 s | 8 (2) → 4 (1) | 261K → 30K chars | 0 → 0 |
| Alerts resolved and leaderboard | 143 s | 57 s | -60% | 65 s → 24 s | 6 (2) → 18 (1) | 36K → 10K chars | 2 → 1 |
| Key wins (fetch) | 34 s | 38 s | +13% | 34 s → 38 s | 4 (2) → 4 (2) | 49K → 49K chars | 1 → 1 |
| **Report total** | **339 s** | **190 s** | **-44%** | | | | |

Leaving out people no longer on the site roster: ready 131 s against 57 s with everyone, fetch 23 s against 24 s. Left out: Raj Prasad, Ritvick Mohan, Hamza Arif.

`search_zones` paging every zone object: 5 s fetch over 2 calls, 37K chars, 322 zone objects. The count tool answered every level in one call.

## Skyline Tower (site 371)

| Section | Before | After | Change | Fetch before → after | Calls (rounds) before → after | Data before → after | Spilled to file |
|---|---|---|---|---|---|---|---|
| Masthead and overview | 14 s | 13 s | -4% | 8 s → 8 s | 7 (1) → 7 (1) | 6K → 5K chars | 0 → 0 |
| Equipment health | 23 s | 23 s | +3% | 8 s → 8 s | 7 (1) → 7 (1) | 34K → 34K chars | 0 → 0 |
| Indoor environment | 106 s | 34 s | -68% | 11 s → 6 s | 6 (2) → 4 (1) | 108K → 9K chars | 0 → 0 |
| Alerts resolved and leaderboard | 126 s | 53 s | -58% | 9 s → 24 s | 5 (1) → 18 (1) | 28K → 19K chars | 0 → 0 |
| Key wins (fetch) | 16 s | 18 s | +10% | 16 s → 18 s | 4 (2) → 4 (2) | 19K → 19K chars | 0 → 0 |
| **Report total** | **284 s** | **141 s** | **-50%** | | | | |

Leaving out people no longer on the site roster: ready 51 s against 53 s with everyone, fetch 23 s against 24 s. Left out: Matthew Strang, Howie Mann.

`search_zones` paging every zone object: 6 s fetch over 4 calls, 114K chars, 952 zone objects. The count tool answered every level in one call.

## 66 Goulburn Street (site 144)

| Section | Before | After | Change | Fetch before → after | Calls (rounds) before → after | Data before → after | Spilled to file |
|---|---|---|---|---|---|---|---|
| Masthead and overview | 10 s | 9 s | -9% | 7 s → 6 s | 7 (1) → 7 (1) | 5K → 5K chars | 0 → 0 |
| Equipment health | 21 s | 21 s | -1% | 8 s → 7 s | 7 (1) → 7 (1) | 34K → 34K chars | 0 → 0 |
| Indoor environment | 141 s | 84 s | -41% | 12 s → 6 s | 6 (2) → 4 (1) | 151K → 31K chars | 0 → 0 |
| Alerts resolved and leaderboard | 239 s | 86 s | -64% | 8 s → 24 s | 5 (1) → 18 (1) | 45K → 29K chars | 0 → 0 |
| Key wins (fetch) | 23 s | 22 s | -6% | 23 s → 22 s | 4 (2) → 4 (2) | 31K → 31K chars | 0 → 0 |
| **Report total** | **434 s** | **222 s** | **-49%** | | | | |

Leaving out people no longer on the site roster: ready 36 s against 86 s with everyone, fetch 23 s against 24 s. Left out: Kenisha Pudun, Shafayet Ali.

`search_zones` paging every zone object: 5 s fetch over 2 calls, 43K chars, 349 zone objects. The count tool answered every level in one call.

## Where the time goes

Every call costs about 1.2 s just to write, even inside one parallel batch: tools start as each call is written, so a batch of n calls takes roughly n x 1.2 s plus its slowest call. Measured over 223 consecutive calls. That is why the alerts fetch rose from 8 to 9 s to 24 s at the two smaller sites: its 18 calls take about 20 s to write, 12 of them the per-month counts. It still finishes about 60% sooner, because no row needs counting by hand.

| Call | Calls timed | Median | Slowest |
|---|---|---|---|
| `search_favourites` | 6 | 5.8 s | 6.9 s |
| `search_alert_tickets` | 18 | 3.0 s | 3.7 s |
| `search_action_tickets` | 6 | 2.7 s | 2.8 s |
| `count_indoor_environment_zones` | 6 | 2.3 s | 3.2 s |
| `search_equipment_health_scores` | 36 | 1.8 s | 3.4 s |
| `search_indoor_environment (zone)` | 14 | 1.8 s | 4.2 s |
| `search_rules` | 6 | 1.8 s | 2.0 s |
| `search_indoor_environment (level)` | 6 | 1.7 s | 2.1 s |
| `search_zones` | 8 | 1.4 s | 1.5 s |
| `search_equipment_types` | 6 | 1.4 s | 1.4 s |
| `who_am_i` | 6 | 1.2 s | 1.5 s |
| `tickets.tickets` | 37 | 1.1 s | 2.3 s |
| `search_equipment` | 12 | 1.1 s | 1.3 s |
| `search_site_assignees` | 3 | 1.1 s | 1.1 s |
| `count_tickets` | 84 | 1.0 s | 2.0 s |
| `search_indoor_environment (site)` | 12 | 1.0 s | 1.0 s |
| `platform.sites` | 6 | 0.8 s | 1.4 s |

`search_favourites`, the overview's sensor count, is the slowest call in the report. It runs while the rest of the overview's calls are still being written, so it adds little to the section.

## Cross-check

Every figure the old and new runs derived matches, at all three sites, except the zone counts, which changed by design to configured sensors:

- Thermal zones: 44 Market Street 380 to 418, Skyline Tower 169 to 334, 66 Goulburn Street 200 unchanged
- Zones column: 44 Market Street L02 16 to 18, L03 17 to 18, L20 13 to 14, L25 14 to 34, L26 14 to 28. Skyline Tower Ground 13 to 14, Level 03 30 to 33, Level 06 49 to 53, NABERS IE 12 to 21. Every monthly score is identical
- Leaderboard, raised vs resolved, median time to resolve, verified recovery, equipment health and key wins are identical. Two cosmetic differences: people tied on resolved and completion swap order, which the ranking rule leaves open, and one name comes back from `count_tickets` with a double space ("Brandon  Quisumbing") that HTML renders as one

## Decisions from these numbers

- **People who have left stay on the leaderboard.** Leaving them out saves no fetch time, since the same 18 calls go out either way, and the derivation swung both ways: 2 s faster at Skyline Tower, 50 s faster at 66 Goulburn Street, 74 s slower at 44 Market Street, where the slimmer rows came back inline instead of to a file and had to be transcribed. Not a dramatic or a reliable gain, so the leaderboard keeps everyone who closed work
- **The Zones column stays at any height.** `count_indoor_environment_zones` answers every level in one call. `search_zones` is not a substitute: it lists zone objects, not sensors (952 at Skyline Tower over 4 pages), so it is slower and counts the wrong thing
- **The leaderboard link stays built from parts.** `count_tickets` returns no `platform_link` in any grouping

## What would save more

- A month bucket on `count_tickets` would turn the 12 per-month calls into 2, about 12 s off every report with the alerts section
- Company names on `count_tickets` assignee rows would let the resolved rows shrink to `age` alone
- A scored-in-window option on `count_indoor_environment_zones` would let the Zones column show scored zones again at no cost

## Method

Each runner was a Claude Code subagent following one spec, with the recipes written out as exact calls, for one site and one recipe: before is the skill at `4ff2adb`, after is this branch. Pairs for the same site ran at the same time. Sections are split by call signature and timed from the transcript timestamps, which record each call as it is written and each result as it returns. Windows: quarter July to September 2026, six months April to September 2026. Single runs, so read differences under about 10% as noise.
