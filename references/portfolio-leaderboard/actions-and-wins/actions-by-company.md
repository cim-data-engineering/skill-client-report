# Actions resolved by company

Owns the actions resolved by company table and its total row, and hands each site's actions resolved this quarter and last quarter to the leaderboard. Scaffold part: `actions-by-company`. Script: `scripts/actions_by_company.py`, which builds every row, figure and note below. One folder with `key-wins.md`: the table says who did the work across the portfolio, the wins say what it was.

## What you write

Nothing on the page. In chat, say what the script prints: how many actions have no assignee with a company, and any company shown with its initials for want of a logo.

## Section header

Eyebrow: Vendor leaderboard  
Statement: Actions resolved by company  
Date line: "Actions resolved {period}, ranked by resolved. Completion rate is resolved ÷ (resolved + open now), with open now as at {issue date}. Each company's sites are listed by open actions, most first." The period runs from the quarter's first day to the issue date where the report carries a month to date, with a spaced hyphen.

## Definitions

- **Resolved**: an action resolved in the window, in any status but Not Doing
- **Open now**: an action with status open, in progress or on hold, as at the issue date, whenever it was raised
- **Completion rate**: resolved ÷ (resolved + open now)
- **Actions, not alerts**: every count is of action tickets, one per action, never the alerts behind them

## Company table

One row per assignee company with actions resolved in the quarter or open now, then a total row.

| Column | Content |
| --- | --- |
| Rank | Position by resolved; the trophy replaces 1 |
| Company | The company's logo tile and name, with its sites line under the name |
| Sites | Sites where the company resolved an action this quarter or holds one open |
| Resolved | Actions the company resolved this quarter |
| Completion rate | A bar on a 0 to 100 scale with the value beside it, to 1dp |
| Open now | Actions the company holds open, emphasised when non-zero |

**Rows and ranking:**

- Rank by resolved, most first, with ties alphabetical by company name. Every company with work shows, however many there are; the table breaks between rows across pages, its header repeating
- An action counts once for each company holding it: one assignee from each of two companies puts it in both rows
- Non-human assignees, such as agents, hold no row. An action held only by agents, or by nobody, is unassigned
- Unassigned actions count in the total row but have no row of their own; the script says how many in chat

**Company sites line:** under the company name, the company's sites in `label`, by open actions most first. Up to two are named, each with "N open" in `text-heading` at 600 where non-zero, then "+N more sites".

**Total row:** counts each action once, so its resolved figure equals the sum of the sites on the actions resolved board, and its open figure every action open across the portfolio. Its completion rate is worked from those two.

**Logos:** each company's logo from PEAK, embedded once, in the square tile; a company without one gets its initials.

**Board figures:** each site's actions resolved this quarter, and in the three whole months before the quarter, handed to the leaderboard. A site with none counts 0 and still ranks.

**Links:** the section carries the anchor `actions-by-company`, which the leaderboard's actions board links to. No dashboard link.

**Renders when:** any action was resolved this quarter or is open now. The actions board renders when any was resolved this quarter.

## Notes band items

- **Completion rate.** Open now includes actions raised before the quarter

## Data

All in the main batch:

| Need | Call |
| --- | --- |
| Resolved this quarter, per site | `count_tickets(ticket_types:["escalated"], aggregate_entities:["site"], statuses:["open","in_progress","closed","on_hold"])` resolved over the quarter, 20 sites a call |
| Resolved last quarter, per site | the same, resolved over the three whole months before the quarter |
| Open now, per site | the same with `statuses:["open","in_progress","on_hold"]` and no date bound |
| Who resolved each action | `tickets.tickets` (`type:"escalated"`, `ticket_archived:false`, every `site_ids`) resolved over the quarter, `limit:1000` |
| Who holds each open action | the same with `status_ids:[1,3,7]` and no date bound |

- Both ticket pulls select only `ticket_id`, `site_id`, `status_id`, and `assignees` with `id`, `firstname`, `lastname`, `entity.name` and `entity.logo_url`: who holds each action, never what anyone wrote. The names only tell an agent from a person
- `report.py next` pages each pull from its first page's total, 1000 rows a page
- Every figure on the board and in the total row is a `count_tickets` count. The ticket rows only say which company holds each action
- Rows with status Not Doing are dropped from the pulls
- Each window is read in each site's own time zone
