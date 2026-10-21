# Open P1-2 actions

Owns the open P1-2 actions section: the sites and the people holding the most priority 1 and 2 actions open now, most first, each split by how long its actions have been open, so the reader sees at once where the open work sits and how old it is. It is not a leaderboard: no trophy, no movement and no award. Scaffold part: `open-actions`. Script: `scripts/open_actions.py`, which builds every row, figure and link below.

## What you write

Nothing on the page. In chat, say what the script prints: that the section is left out when nothing is open.

## Section header

Eyebrow: the issue month, "October 2026"  
Statement: Open P1-2 actions  
Date line: "Priority 1 and 2 actions open as at {issue date} by age open.", then where a list is cut, "Top 20 of {N} sites and {N} assignees." naming the lists cut.  
Legend under it: "≥60d", "30-60d", "<30d", one swatch each.

## Definitions

- **Open P1-2**: an action with priority 1 or 2 and status open, in progress or on hold, as at the issue date, whenever it was raised
- **Age open**: the days since the action was raised, as PEAK gives it on the pull: 60 or more, 30 to 60, or under 30
- **Actions, not alerts**: every count is of action tickets, one per action, never the alerts behind them

## Lists

Two lists side by side, Sites then Assignees, each under a board head with "Open P1-2" on its right.

| Column | Content |
| --- | --- |
| Rank | Position by open P1-2 actions, most first |
| Logo | Assignees only: the person's company logo, grey; empty for no company |
| Name | The site name with its region label in brackets, per [How sections fit together](../../../SKILL.md#how-sections-fit-together), or the person's name with their company after it, each a link with a chevron; under it a bar on the list's own scale, the most open filling it, split by age open with the oldest first |
| Count | Open P1-2 actions |

**Rows and ranking:**

- Most first, ties alphabetical by name; the top 20 on each list
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
| Each open P1-2 action, its age and who holds it | `tickets.tickets` (`type:"escalated"`, `ticket_archived:false`, every `site_ids`, `status_ids:[1,3,7]`, `priority_ids:[1,2]`), `limit:1000` |
| Each assignee's name | `count_tickets(ticket_types:["escalated"], aggregate_entities:["assignee"], statuses:["open","in_progress","on_hold"], priorities:[1,2])`, 20 sites a call: `assignee_name` by `assignee_id` |

- The ticket pull selects only `ticket_id`, `site_id`, `status_id`, `age`, and `assignees` with `id`, `entity.name` and `entity.logo_url`: how long each action has been open and who holds it, never what anyone wrote. No names: PEAK refuses the whole pull when one assignee has none, so names come from the count by assignee
- `report.py next` pages the pull from its first page's total, 1000 rows a page
- Every count and every age split comes from the one pull, so each bar always adds up to its count
- Each shown company's logo is fetched once from the link on its assignees and embedded; a company without one gets its initials

**Hands on:** the sites with data: each site holding an open P1-2 action. **Takes:** the sites with data marked before it builds, listed at 0.
