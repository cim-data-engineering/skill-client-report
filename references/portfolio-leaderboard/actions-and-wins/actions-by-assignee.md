# Actions resolved by assignee

Owns the actions resolved by assignee table and its total row, each person moving against last month's table, and hands on each person's actions resolved as a team ranking. Scaffold part: `actions-by-assignee`. Script: `scripts/actions_by_assignee.py`, which builds every row, figure and note below.

## What you write

Nothing, on the page or in chat.

## Section header

Eyebrow: Assignee leaderboard  
Statement: Actions resolved by assignee  
Date line: "Actions resolved {period}, ranked by resolved, with moves since {the month before}. Completion rate is resolved ÷ (resolved + open now), with open now as at {issue date}. Under each name, the assignee's company, then their sites by open actions, most first." The period runs from the quarter's first day to its last, with a spaced hyphen, and the month before is the one before the leaderboard month: "Actions resolved 1 July - 30 September 2026, ranked by resolved, with moves since August."

## Definitions

- **Resolved**: an action resolved in the quarter, in any status but Not Doing
- **Open now**: an action with status open, in progress or on hold, as at the issue date, whenever it was raised
- **Completion rate**: resolved ÷ (resolved + open now)
- **Actions, not alerts**: every count is of action tickets, one per action, never the alerts behind them

## Assignee table

One row per assignee with actions resolved in the quarter or open now, then a total row.

| Column | Content |
| --- | --- |
| Rank | Position by resolved, the person's movement under it; the trophy replaces 1 |
| Assignee | Their company's logo tile and the person's name, with their sites line under the name |
| Sites | Sites where the person resolved an action in the quarter or holds one open |
| Resolved | Actions the person resolved in the quarter |
| Completion rate | A bar on a 0 to 100 scale with the value beside it, to 1dp |
| Open now | Actions the person holds open, emphasised when non-zero |

**Rows and ranking:**

- Rank by resolved, most first, with ties alphabetical by name. Every assignee with work shows, however many there are; the table breaks between rows across pages, its header repeating
- An action counts once for each person holding it: two assignees on one action put it in both rows
- Every assignee counts, whoever they are: contractors, CIM, the client's own managing agents, shared accounts and AI agents alike. Each is their PEAK user, so two people with one name hold a row each. One with no name in PEAK shows as "Unnamed assignee"
- An action held by nobody counts in the total row and has no row of its own

**Movement:** against last month's table, which ranked the assignees by actions resolved over the quarter a month earlier. Movement is the person's place there less their place now. Someone who resolved nothing then shows "New"; someone who resolved nothing in the quarter shows no movement. "↑2" in green, "↓1" in red, nothing when they hold their place, per the company table movement in DESIGN.md.

**Assignee sites line:** under the name, in `label`: the person's company first, then their sites by open actions, most first. Up to two sites are named, each with "N open" in `text-heading` at 600 where non-zero, then "+N more sites". An assignee with no company starts at their sites.

**Total row:** the actions resolved in the quarter and open now, each counted once, as handed on, so it matches every other count of the portfolio's actions. Its completion rate is worked from those two.

**Logos:** each company's logo as handed on, in the square tile; a company without one gets its initials, and an assignee with no company an empty tile.

**Links:** the name and section links open PEAK's ticket report over the quarter, with one `site_ids` per site.

- Each name links to the report at the person's sites, narrowed to them, grouped by company, with a chevron:
  `https://ace.cimenviro.com/reports/tickets?site_ids={{site_id}}&start_date={{quarter_start}}T00:00:00.000&end_date={{quarter_end}}T00:00:00.000&grouping=user_entity&assignee_ids={{assignee_id}}`
- The section link, "See actions by assignee ›", opens the report at every site, grouped by assignee:
  `https://ace.cimenviro.com/reports/tickets?site_ids={{site_id}}&start_date={{quarter_start}}T00:00:00.000&end_date={{quarter_end}}T00:00:00.000&grouping=assignee`
- The section carries the anchor `actions-by-assignee`

**Renders when:** any action was resolved in the quarter or is open now.

**Hands on:**

- **A team ranking** labelled Assignees, of assignees, under the anchor `actions-by-assignee`, by quarter, in the unit "actions": each person's actions resolved over the quarter and over the quarter a month earlier, as whole numbers, their name, their company and its logo, and for whoever leads a meta line of their company and their sites, "Kestrel Air Services · 2 sites". It carries the section link, its words and its URL. Someone who resolved none in a window has no figure on it. Handed on only when anyone resolved an action in the quarter

## Notes band items

- **Completion rate.** "Open now includes actions raised before {the quarter's first month}.": "before July"

## Data

No calls of its own. **Takes:**

- **Who holds each action**: each action resolved in the quarter, resolved in the quarter a month earlier and open now, Not Doing left out, with its site and each assignee holding it: their PEAK user id, name and company. With them, the actions resolved in the quarter and open now, each counted once
- **Company logos**: each company's logo, embedded
