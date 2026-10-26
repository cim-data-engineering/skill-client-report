# Open P1-2 actions

Owns the open P1-2 actions section: the portfolio's open P1-2 backlog at each month end over the past year, from the month its first P1-2 action was raised, then the sites and the people holding the most priority 1 and 2 actions open now, most first, each split by how long its actions have been open. It is not a leaderboard: no trophy, no movement and no award. Scaffold part: `open-actions`. Script: `scripts/open_actions.py`, which builds every row, figure and link below.

## What you write

Nothing on the page. In chat, say what the script prints: that the section is left out when nothing is open.

## Section header

Eyebrow: the issue month, "October 2026"  
Statement: Open P1-2 actions  
Date line: "Priority 1 and 2 open actions (new, in progress and on hold).", then where a list is cut, "Top 10 of {N} sites and {N} assignees." naming the lists cut.  
Legend under it: "≥60d", "30-60d", "<30d", one swatch each, keying the chart and both lists' bars.

## Definitions

- **Open P1-2**: an action with priority 1 or 2 and status open, in progress or on hold, as at the issue date, whenever it was raised
- **Age open**: the days since the action was raised, as PEAK gives it on the pull: 60 or more, 30 to 60, or under 30, the buckets PEAK's ticket report shows
- **Actions, not alerts**: every count is of action tickets, one per action, never the alerts behind them

## Backlog chart

Under the legend, chart title "Backlog at month end": a stacked bar for each of the eleven month ends before the issue month, from the first month, then the issue month, twelve at most, on one scale. Each bar splits by age open on the day, in the lists' shades, 60 days or more at the base, with its total on top.

- **First month**: the month the portfolio's first P1-2 action was raised, open or closed, at any site. Month ends before it are left out; a month end from it on with nothing open shows 0
- **Month end**: every action open as the month closed, on the definition above: raised before the first of the next month, and not closed before it. Its age is counted to the month's last day
- **The issue month**: the backlog as at the issue date, the count the lists add up to, labelled by its month alone
- PEAK keeps no priority or status history, so a month end is rebuilt from today's records: an action raised as P3 and later raised to P1 counts at P1 in every month it was open
- It is shorter than the monthly charts, so it and both lists hold one page. Both lists' rows are as tall as an assignee's three lines, so the two sit level
- With the issue month alone, its one bar sits in the middle

## Lists

Two lists side by side, Sites then Assignees, each under a board head with "Open P1-2" on its right.

| Column | Content |
| --- | --- |
| Rank | Position by open P1-2 actions, most first |
| Logo | Assignees only: the person's company logo, grey; empty for no company |
| Name | The site name with its region label in brackets, or the person's name, each a link with a chevron. Under a person's name, in muted text, their company and the site holding the most of their open P1-2 actions, ties alphabetical, then "+ {N} sites": "Company A · Site A + 1 site", the site cut short before the count is; under "No assignee", the site holding the most unassigned. Under it all a bar on the list's own scale, the most open filling it, split by age open with the oldest first |
| Count | Open P1-2 actions |

**Rows and ranking:**

- Region label: the site's state, or its country where the portfolio spans countries; none where every site shares one, or where the name already ends in brackets
- Most first, ties alphabetical by name; the top 10 on each list
- Sites: every site with data, those holding none at 0, with no bar and no link
- Assignees: everyone holding one, CIM, the client's managing agents and AI agents included. An action counts once for each person holding it. Actions held by nobody are one row, "No assignee", with no link; an account with no name in PEAK is "Unnamed assignee"

**Links:** PEAK's ticket report, priority 1 and 2 only, from `{{raised}}`, the day the oldest action the name counts was raised (its age counted back from the issue date, a day early), to `{{issue_date}}`, so every action counted is in it. One `site_ids` per site.

- Each site opens its report grouped by assignee:
  `https://ace.cimenviro.com/reports/tickets?site_ids={{site_id}}&start_date={{raised}}T00:00:00.000&end_date={{issue_date}}T23:59:59.999&grouping=assignee&priority_ids=1&priority_ids=2`
- Each person opens the report at their sites, grouped by site and narrowed to them:
  `https://ace.cimenviro.com/reports/tickets?site_ids={{site_id}}&start_date={{raised}}T00:00:00.000&end_date={{issue_date}}T23:59:59.999&grouping=site&priority_ids=1&priority_ids=2&assignee_ids={{assignee_id}}`
- The section carries the anchor `open-actions`

**Renders when:** any priority 1 or 2 action is open now.

## Data

All in the main batch:

| Need | Call |
| --- | --- |
| Each open P1-2 action, its age, when it was raised and who holds it | `tickets.tickets` (`type:"escalated"`, `ticket_archived:false`, every `site_ids`, `status_ids:[1,3,7]`, `priority_ids:[1,2]`), `limit:1000` |
| Each assignee's name | `count_tickets(ticket_types:["escalated"], aggregate_entities:["assignee"], statuses:["open","in_progress","on_hold"], priorities:[1,2])`, 20 sites a call: `assignee_name` by `assignee_id` |
| Each P1-2 action closed since the first month end | `tickets.tickets` (`type:"escalated"`, `ticket_archived:false`, every `site_ids`, `status_ids:[6]`, `priority_ids:[1,2]`, `resolved_at_local_start` the first of the month after the first month end), `limit:1000`, selecting `ticket_id`, `site_id`, `created_at` and `resolved_at` only |
| The first P1-2 action raised | `tickets.tickets` (`type:"escalated"`, `ticket_archived:false`, every `site_ids`, `status_ids:[1,3,6,7]`, `priority_ids:[1,2]`, `orderBy:"created_at_ASC"`), `limit:1`, selecting `site_id` and `created_at` only |

- The ticket pull selects only `ticket_id`, `site_id`, `status_id`, `age`, `created_at`, and `assignees` with `id`, `entity.name` and `entity.logo_url`: how long each action has been open and who holds it, never what anyone wrote. No names: PEAK refuses the whole pull when one assignee has none, so names come from the count by assignee
- `report.py next` pages both pulls from their first page's total, 1000 rows a page
- Every list count and age split comes from the open pull, so each bar always adds up to its count
- The month ends come from the two pulls, from the first action's month, each date read in its site's own time. The last bar is the open pull's own count, so it always equals the lists. Not doing and archived actions are left out, as everywhere else
- Each shown company's logo is fetched once from the link on its assignees and embedded; a company without one gets its initials

**Hands on:** the sites with data: each site holding an open P1-2 action. **Takes:** the sites with data marked before it builds, listed at 0.
