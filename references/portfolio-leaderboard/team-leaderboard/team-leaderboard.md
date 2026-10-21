# Team leaderboard

Owns the leaderboard month's team leaderboard: a board for each team ranking it takes, each ranking the companies or the people holding the work on one figure and moving them against last month's board. Scaffold part: `team-leaderboard`. Script: `scripts/team_leaderboard.py`, which builds every board from those rankings.

## What you write

Nothing, on the page or in chat.

## Section header

Eyebrow: the leaderboard month, "September 2026"  
Statement: Team leaderboard  
Date line: "Each board ranks by actions resolved, with moves since {the month before}.", then, when a board ranks more than 10, how many it ranks: "Top 10 of 24 assignees.", or with both boards over 10, "Top 10 of 12 companies and 24 assignees."

## Boards

One board per team ranking, in the order the rankings come. Each is a small ranked table.

| Part | Content |
| --- | --- |
| Head | the ranking's label and its months as a table header: "Companies" with "Jul - Sep" |
| Value | the figure now, a whole number, with the ranking's unit after the leader's: "114 actions" |
| Movement | against the place on last month's board |

**Ranking:**

- Most first on the figure. Equal figures split alphabetically by name, ignoring case. No shared places, and no note explaining a tie
- A company or person with no figure now is not on that board
- Last month's board ranks every company or person with a figure on the window it ranked, whether or not they are on the board now. Movement is the place there less the place now. One with no figure there shows "New"

**Each board** reads in three steps, the leader first:

1. **Leader**: rank 1, its row set large. The trophy and the movement in the rank column, the company's logo in its tile and in its own colours, the name, then the meta line the ranking gives its leader with the value and unit: "4 sites" for a company, "Kestrel Air Services · 2 sites" for a person
2. **Biggest climber**: the one challenger, the row under the leader: "Biggest climber", the company logo, the name and "↑{places} to {place now}", "↑2 to 10th". It is the largest climb among ranks 2 to 10, so it is never the leader and always on the board. Those tied on the climb go to the one placed highest. With no climber, the row shows a dash
3. **Chasing pack**: ranks 2 to 10, each with rank, company logo, name, movement and value, a step smaller

**Display:**

- Every name sits beside its company's logo, so the reader knows whose crew a person is in: a company's own logo, a person's company's. Only the leader's is in colour; the climber's and the pack's are grey. A company without a logo gets its initials; a person with no company, an empty space
- Every tier shares the rank and logo columns, so the leader's name, the climber's and the pack's all start on one line
- Movement: "↑N" in green, "↓N" in red, nothing when a company or person holds its place
- Names clamp to two lines. The tiers sit level across the boards, whichever names take two lines
- The boards sit side by side. A board renders when its ranking holds anyone, and fewer boards take the width the missing ones leave

**Links:**

- Every name on a board links where its ranking says: to the section that explains its figure, or to its own PEAK report. The leader's has a chevron; the climber's and the pack's do not, so the pack stays quiet. Chromium keeps these as links in the printed PDF

**Renders when:** at least one board does.

## Data

No calls of its own. **Takes:**

- **Team rankings**: each a label, each name's PEAK report, a window (month or quarter), what it ranks ("companies", "assignees"), its unit, each company's or person's name, their figure now and on the window last month's board ranked, each one's company and its logo, and the meta line for whoever leads
