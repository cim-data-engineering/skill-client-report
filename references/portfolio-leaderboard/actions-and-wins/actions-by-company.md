# Actions resolved by company

Owns the actions resolved by company table and its total row, each company moving against last month's table, and hands on each site's actions resolved as a ranking. Scaffold part: `actions-by-company`. Script: `scripts/actions_by_company.py`, which builds every row, figure and note below.

## What you write

Nothing on the page. In chat, say what the script prints: how many actions have no assignee with a company, and any company shown with its initials for want of a logo.

## Section header

Eyebrow: Vendor leaderboard  
Statement: Actions resolved by company  
Date line: "Actions resolved {period}, ranked by resolved, with moves since {the month before}. Completion rate is resolved ÷ (resolved + open now), with open now as at {issue date}. Each company's sites are listed by open actions, most first." The period runs from the quarter's first day to its last, with a spaced hyphen, and the month before is the one before the leaderboard month: "Actions resolved 1 July - 30 September 2026, ranked by resolved, with moves since August."

## Definitions

- **Resolved**: an action resolved in the quarter, in any status but Not Doing
- **Open now**: an action with status open, in progress or on hold, as at the issue date, whenever it was raised
- **Completion rate**: resolved ÷ (resolved + open now)
- **Actions, not alerts**: every count is of action tickets, one per action, never the alerts behind them

## Company table

One row per assignee company with actions resolved in the quarter or open now, then a total row.

| Column | Content |
| --- | --- |
| Rank | Position by resolved, the company's movement under it; the trophy replaces 1 |
| Company | The company's logo tile and name, with its sites line under the name |
| Sites | Sites where the company resolved an action in the quarter or holds one open |
| Resolved | Actions the company resolved in the quarter |
| Completion rate | A bar on a 0 to 100 scale with the value beside it, to 1dp |
| Open now | Actions the company holds open, emphasised when non-zero |

**Rows and ranking:**

- Rank by resolved, most first, with ties alphabetical by company name. Every company with work shows, however many there are; the table breaks between rows across pages, its header repeating
- An action counts once for each company holding it: one assignee from each of two companies puts it in both rows
- Every assignee counts under their company, whoever they are: contractors, CIM, the client's own managing agents and AI agents alike. An action held by nobody, or by assignees with no company in PEAK, is unassigned
- Unassigned actions count in the total row but have no row of their own; the script says how many in chat

**Movement:** against last month's table, which ranked the companies by actions resolved over the quarter a month earlier. Movement is the company's place there less its place now. A company that resolved nothing then shows "New"; one that resolved nothing in the quarter shows no movement. "↑2" in green, "↓1" in red, nothing when it holds its place, per the company table movement in DESIGN.md.

**Company sites line:** under the company name, the company's sites in `label`, by open actions most first. Up to two are named, each with "N open" in `text-heading` at 600 where non-zero, then "+N more sites".

**Total row:** counts each action once, so its resolved figure equals the sum of the sites in the ranking it hands on, and its open figure every action open across the portfolio. Its completion rate is worked from those two.

**Logos:** each company's logo from PEAK, embedded once, in the square tile; a company without one gets its initials.

**Links:** the section carries the anchor `actions-by-company`. No dashboard link.

**Renders when:** any action was resolved in the quarter or is open now.

**Hands on:**

- **A ranking** labelled Actions resolved, under the anchor `actions-by-company`, by quarter: each site's actions resolved over the quarter, and over the quarter a month earlier, as whole numbers. A site that resolved none in a window has no figure on it, so it is off the board now, or New on it where it resolved none a month earlier. Handed on only when any action was resolved in the quarter

## Notes band items

- **Completion rate.** "Open now includes actions raised before {the quarter's first month}.": "before July"

## Data

All in the main batch:

| Need | Call |
| --- | --- |
| Resolved in the quarter, per site | `count_tickets(ticket_types:["escalated"], aggregate_entities:["site"], statuses:["open","in_progress","closed","on_hold"])` resolved over the quarter, 20 sites a call |
| Resolved a month earlier, per site | the same, resolved over the quarter a month earlier |
| Open now, per site | the same with `statuses:["open","in_progress","on_hold"]` and no date bound |
| Who resolved each action | `tickets.tickets` (`type:"escalated"`, `ticket_archived:false`, every `site_ids`) resolved over the quarter, `limit:1000` |
| Who resolved each action a month earlier | the same, resolved over the quarter a month earlier |
| Who holds each open action | the same with `status_ids:[1,3,7]` and no date bound |

- The ticket pulls select only `ticket_id`, `site_id`, `status_id`, and `assignees` with `id`, `entity.name` and `entity.logo_url`: which company holds each action, never what anyone wrote
- `report.py next` pages each pull from its first page's total, 1000 rows a page
- Every figure in the ranking and the total row is a `count_tickets` count. The ticket rows only say which company holds each action
- Rows with status Not Doing are dropped from the pulls
- Each window is read in each site's own time zone
