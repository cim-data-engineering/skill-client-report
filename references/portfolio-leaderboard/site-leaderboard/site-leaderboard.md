# Site leaderboard

Owns the leaderboard month's performance leaderboard: a board for each ranking it takes, each ranking the sites on one figure and moving them against last month's board. Scaffold part: `site-leaderboard`. Script: `scripts/site_leaderboard.py`, which builds every board from those rankings.

## What you write

Nothing, on the page or in chat.

## Section header

Eyebrow: Site rankings  
Statement: "{Leaderboard month} performance leaderboard": "September 2026 performance leaderboard"  
No date line: each board's caption carries its window. With more than 10 sites, the header carries "Top 10 of {N} sites on each board.", N being the sites in the report.

## Boards

One board per ranking, in the order the rankings come.

| Part | Content |
| --- | --- |
| Title | "{label} leaders", from the ranking's label |
| Value | the site's figure now, at the ranking's decimals |
| Caption | by the ranking's window. Month: "{Leaderboard month} · moves since {the month before}", "September · moves since August". Quarter: "{First month} - {Leaderboard month} · moves since {the month before}", "July - September · moves since August" |
| Movement | against the site's place on last month's board |

**Ranking:**

- Best first on the unrounded value. Equal values split alphabetically by site name, ignoring case. No shared places, and no note explaining a tie
- A site with no figure now is not on that board
- Last month's board ranks every site with a figure on the window it ranked, whether or not the site is on the board now. Movement is the site's place there less its place now. A site with no figure there shows "New" and is never a climber

**Each board:**

- **Leader block**: rank 1 alone. The trophy and the word "Leader" as an eyebrow, the site name, the value, then a meta line: "{state} · {building size}" with the movement
- **Chasing pack**: ranks 2 to 10, each with rank, site name, movement and value
- **Biggest climber**: the largest climb across every site on the board, not only the ten shown, with an "↑ N places" chip. Two sites tied on it are named together; more than two are given as "N sites". The block is left out when no site climbed

**Display:**

- Movement under the rank: "↑N" in green, "↓N" in red, nothing when a site holds its place
- The pack is set small at body weight, so the hierarchy sits with the leader. No band fills and no pills in the pack
- Names clamp to two lines, and every row in a board has one height
- Up to three boards side by side. A board renders when its ranking holds a site, and fewer boards take the width the missing ones leave
- The site label on a board is the name alone; the state moves to the leader's meta line

**Links:**

- Every site name on a board jumps to the anchor its ranking carries, in the same document and the same tab. Chromium keeps these as links in the printed PDF
- No dashboard links on this section

**Renders when:** at least one board does.

## Notes band items

None.

## Data

No calls of its own. **Takes:**

- **Rankings**: each a label, an anchor, a window (month or quarter), each site's figure now and on the window last month's board ranked, and the decimals to show
- **Site facts**: each leader's state and building size
