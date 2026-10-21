# Actions resolved

Owns the actions resolved ticket pulls, and hands them on as rankings: each site's actions resolved, and each company's and each person's. It has no part on the page. Script: `scripts/actions_resolved.py`, which builds every ranking below.

## What you write

Nothing on the page. In chat, say what the script prints: how many of the quarter's actions it left out and why, any company shown with its initials for want of a logo, and any account PEAK holds no name or company for, by its user id, for ops to name in PEAK.

## Definitions

- **Resolved**: an action resolved in the quarter, in any status but Not Doing, that counts
- **Counts**: every resolved action, created and closed in one step included, but two kinds closed out with no comment from a person on the action at any point, only agents' or none, which no ranking counts, this month or on last month's board:
  1. **Recovered with no comment**: created and closed in one step, every linked alert already recovered at that moment. PEAK stamps an action created closed as resolved the instant it was created
  2. **Closed in fault with no comment**: a person closed it while every linked alert was in fault, and every one is still in fault today
- **Who closed it**: the change among the action's latest three stamped nearest its resolved_at, within 5 seconds; an action created closed has its creation alone. An agent's close always counts, Agent Hannah's above all, credited to the assignees like any other. Where no close shows in those three, the rules apply
- **A person**: anyone `peak_io.system_account` does not name, as for who ranks below. CIM's system accounts and agents never comment or close as a person, nor does PEAK's own system user, which carries no id
- **An alert's state at the close**: its fault status now, where it has not changed since the close. An alert that changed after the close is in neither state, so the action counts, as does an action with no linked alert
- **Actions, not alerts**: every count is of action tickets, one per action, never the alerts behind them
- **Who resolved it**: the action's assignees. An action counts once for each company holding it and once for each person. The site ranking counts every action that counts, whoever resolved it
- **Who ranks**: people, CIM's included, and contractors' shared logins, such as a dispatch desk. CIM's system accounts never rank, and CIM's company figure leaves them out: `peak_io.system_account` decides, by the user ids in `peak_io.SYSTEM_ACCOUNTS` (CIM Support, the CIM API logins and the AI agents) and any name starting "Agent", since the rows carry no email. An account PEAK holds no name and no company for is left off both team rankings; one with a company but no name ranks as "Unnamed assignee"

## Hands on

Each ranking runs over the quarter and moves against the quarter a month earlier, as whole numbers in the unit "actions". Anyone who resolved none in a window has no figure on it, so they are off the board now, or New on it where they resolved none a month earlier. Handed on only when any action was resolved in the quarter.

- **Sites with data**: each site with an action resolved in the quarter
- **A ranking** labelled Actions resolved: each site's actions resolved. Each site opens its PEAK ticket report over the quarter, grouped by assignee
- **A team ranking** labelled Companies, of companies: each company's actions resolved by the people who rank, its name and logo, and for whichever leads a meta line of its busiest site, where it resolved the most in the quarter, ties alphabetical, then "+ {N} sites" for the rest: "Site A + 3 sites", "Site A + 1 site", or the site alone. Each company opens its PEAK ticket report at its sites, narrowed to its assignees who rank and grouped by site
- **A team ranking** labelled Assignees, of assignees: each person's actions resolved, their name, their company and its logo, and for whoever leads a meta line of their company, then their busiest site and "+ {N} sites" the same way: "Company A · Site A + 1 site". Each person opens their PEAK ticket report at their sites, narrowed to them and grouped by company. It also carries the leader's shoutout: their first name and email off the leader pull, and their busiest site; none without the leader pull

The reports are PEAK's ticket report over the quarter, one `site_ids` per site and one `assignee_ids` per assignee named:

- Site: `https://ace.cimenviro.com/reports/tickets?site_ids={{site_id}}&start_date={{quarter_start}}T00:00:00.000&end_date={{quarter_end}}T00:00:00.000&grouping=assignee`
- Company: the same at the company's sites, with `&grouping=site&assignee_ids={{assignee_id}}` for each of its assignees who rank on an action resolved in the quarter
- Person: the same at their sites, with `&grouping=user_entity&assignee_ids={{assignee_id}}`

## Data

All in the main batch but the leader pull:

| Need | Call |
| --- | --- |
| Each person's name | `count_tickets(ticket_types:["escalated"], aggregate_entities:["assignee"], statuses:["open","in_progress","closed","on_hold"])` resolved over the quarter and over the quarter a month earlier, 20 sites a call: `assignee_name` by `assignee_id` |
| Each action resolved, who holds it and whether it counts | `tickets.tickets` (`type:"escalated"`, `ticket_archived:false`, every `site_ids`) resolved over the quarter, `limit:1000` |
| The same a month earlier | the same, resolved over the quarter a month earlier |
| The Assignees leader's first name and email | once the pulls are whole, `report.py next` prints one `tickets.tickets` on one ticket of the leader's whose assignees all have names, selecting `ticket_id` and `assignees` with `id`, `firstname` and `email`: `ar/leader.json` |

- The ticket pulls select `ticket_id`, `site_id`, `status_id`, `created_at`, `resolved_at`, and `assignees` with `id`, `entity.name` and `entity.logo_url`: who holds each action and their company. To tell whether it counts, they add `comments(user_only:true)` and the latest three of `change_history(sort_order:"DESC")`, each with `author_id` and `author_full_name`, the close by `ts`, and each linked alert's `fault_status` and `last_fault_transitioned_at` under `ticket_links.ticket`. Never what anyone wrote. No assignee names or emails: PEAK refuses the whole pull when one assignee has none, so names come from the counts by assignee
- `report.py next` pages each pull from its first page's total, 1000 rows a page, about 1 MB
- Every figure counts the action rows that count. A count from `count_tickets` cannot tell a comment's author or an alert's state at the close, so no figure is one, and a board's figure can sit below the PEAK report its name opens: the script says so in chat whenever it left an action out
- Rows with status Not Doing are dropped from the pulls
- Each company's logo is fetched once from the link on its assignees and embedded; a company without one gets its initials
- Each window is read in each site's own time zone
