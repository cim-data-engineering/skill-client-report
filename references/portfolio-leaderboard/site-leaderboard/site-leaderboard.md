# Site leaderboard

Owns the leaderboard month's site leaderboard: a board for each ranking it takes, each ranking the sites on one figure and moving them against last month's board. Scaffold part: `site-leaderboard`. Script: `scripts/site_leaderboard.py`, which builds every board from those rankings.

## What you write

Nothing on the page. In chat, say what the script prints: any leader with no building photo.

## Section header

Eyebrow: the leaderboard month, "September 2026"  
Statement: Site leaderboard  
Date line: "Each board ranks the sites on one measure, with moves since {the month before}.", then with more than 10 sites "Top 10 of {N} sites on each board.", N being the sites in the report.

## Boards

One board per ranking, in the order the rankings come. Each is a small ranked table.

| Part | Content |
| --- | --- |
| Head | the ranking's label and its months as a table header: "Equipment health" with "Sep", "Actions resolved" with "Jul - Sep" |
| Value | the site's figure now, at the ranking's decimals, with the ranking's unit after the leader's: "99.6 %", "105 actions" |
| Movement | against the site's place on last month's board |

**Ranking:**

- Best first on the unrounded value. Equal values split alphabetically by site name, ignoring case. No shared places, and no note explaining a tie
- A site with no figure now is not on that board
- Last month's board ranks every site with a figure on the window it ranked, whether or not the site is on the board now. Movement is the site's place there less its place now. A site with no figure there shows "New"

**Each board** reads in three steps, the leader first:

1. **Leader**: rank 1, its row set large under the building's photo, cropped to a wide band. The trophy and the movement in the rank column, the site name, then "{state} · {building size}" with the value and unit. A leader with no photo in PEAK gets a plain panel with a building mark, and the script names it in chat
2. **Biggest climber**: the one challenger, the row under the leader: "Biggest climber", the site name, and "↑{places} to {place now}", "↑2 to 5th". It is the largest climb among ranks 2 to 10, so it is never the leader and always on the board. Sites tied on the climb go to the one placed highest. With no climber, the row shows a dash
3. **Chasing pack**: ranks 2 to 10, each with rank, site name, movement and value, a step smaller

**Display:**

- Every tier shares the rank column, so the leader's name, its meta line, the climber and the pack's names all start on one line
- Movement: "↑N" in green, "↓N" in red, nothing when a site holds its place
- Names clamp to two lines. The tiers sit level across the boards, whichever names take two lines
- Up to three boards side by side. A board renders when its ranking holds a site, and fewer boards take the width the missing ones leave
- The site label on a board is the name alone; the state moves to the leader's meta line

**Links:**

- Every site name on a board links where its ranking says: to the section that explains its figure, or to its own PEAK report. The leader's has a chevron; the climber's and the pack's do not, so the pack stays quiet. Chromium keeps these as links in the printed PDF
- No dashboard links on this section

**Renders when:** at least one board does.

## Notes band items

None.

## Data

No PEAK calls of its own. The script fetches each leader's photo once from its link, crops it to the band and embeds it as a JPEG. **Takes:**

- **Rankings**: each a label, an anchor or each site's PEAK report, a window (month or quarter), its unit, each site's figure now and on the window last month's board ranked, and the decimals to show
- **Site facts**: each leader's state, building size and building photo link
