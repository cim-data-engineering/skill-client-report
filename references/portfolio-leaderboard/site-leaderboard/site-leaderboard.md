# Site leaderboard

Owns the building performance leaderboard on page one: three boards ranking the sites on equipment health, thermal comfort and actions resolved. Scaffold part: `site-leaderboard`. Script: `scripts/site_leaderboard.py`, which builds every board from the per-site figures the equipment health, indoor environment and actions sections hand it.

## What you write

Nothing, on the page or in chat. The sections it ranks name any site they leave out.

## Section header

Eyebrow: Site rankings  
Statement: Building performance leaderboard  
No date line: each board's caption carries its window. With more than 10 sites, the header carries "Top 10 of {N} sites on each board.", N being the sites in the report.

## Boards

| Board | Value | Caption | Movement against |
| --- | --- | --- | --- |
| Equipment health leaders | the site's equipment health score for the period's last month | "{Last month} · moves since {first month}", the last month read "October to date" where it is the month to date | the site's rank on the period's first month |
| Thermal comfort leaders | the site's thermal comfort score for the same months | the same | the same |
| Actions resolved leaders | actions resolved in the quarter, the month to date included | "This quarter · moves since last quarter" | the site's rank on actions resolved in the three whole months before the quarter |

**Ranking:**

- Best first on the unrounded value. Equal values split alphabetically by site name, ignoring case. No shared places, and no note explaining a tie
- A site with no value for the board's month is not on that board
- Movement is the site's rank on the earlier window less its rank now, among the sites on the board that have both. A site with no value on the earlier window shows "New" and is never a climber
- Scores display to 1dp; actions as whole numbers

**Each board:**

- **Leader block**: rank 1 alone. The trophy and the word "Leader" as an eyebrow, the site name, the value, then a meta line: "{state} · {building size}" with the movement
- **Chasing pack**: ranks 2 to 10, each with rank, site name, movement and value
- **Biggest climber**: the largest climb across every site on the board, not only the ten shown, with an "↑ N places" chip. Two sites tied on it are named together; more than two are given as "N sites". The block is left out when no site climbed

**Display:**

- Movement under the rank: "↑N" in green, "↓N" in red, nothing when a site holds its place
- The pack is set small at body weight, so the hierarchy sits with the leader. No band fills and no pills in the pack
- Names clamp to two lines, and every row in a board has one height
- Up to three boards side by side. A board renders when its source section has data, and fewer boards take the width the missing ones leave
- The site label on a board is the name alone; the state moves to the leader's meta line

**Links:**

- Every site name on a board jumps to its section in the same document and opens in the same tab: equipment health to the Equipment health by site section, thermal comfort to Thermal comfort by site, actions to Actions resolved by company. Chromium keeps these as links in the printed PDF
- No dashboard links on this section

**Renders when:** at least one board does.

## Notes band items

None. The boards rank figures the sections below already define.

## Data

No calls of its own. It ranks what the sections leave in `shared`:

| Board | From | Figures |
| --- | --- | --- |
| Equipment health | `equipment-health` | each site's score for the period's first and last month |
| Thermal comfort | `indoor-environment` | each site's score for the period's first and last month |
| Actions resolved | `actions-by-company` | each site's actions resolved this quarter and in the three whole months before it |

It builds after those three sections and before the overview. Building sizes and states come from the overview's site facts.
