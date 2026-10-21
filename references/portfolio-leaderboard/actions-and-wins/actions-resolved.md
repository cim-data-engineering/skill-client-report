# Actions resolved

Owns the actions resolved counts and ticket pulls, and hands them on as rankings: each site's actions resolved, and each company's and each person's. It has no part on the page. Script: `scripts/actions_resolved.py`, which builds every ranking below.

## What you write

Nothing on the page. In chat, say what the script prints: any company shown with its initials for want of a logo.

## Definitions

- **Resolved**: an action resolved in the quarter, in any status but Not Doing
- **Actions, not alerts**: every count is of action tickets, one per action, never the alerts behind them
- **Who resolved it**: the action's assignees, CIM, the client's managing agents and AI agents included. An action counts once for each company holding it and once for each person

## Hands on

Each ranking runs over the quarter and moves against the quarter a month earlier, as whole numbers in the unit "actions". Anyone who resolved none in a window has no figure on it, so they are off the board now, or New on it where they resolved none a month earlier. Handed on only when any action was resolved in the quarter.

- **A ranking** labelled Actions resolved: each site's actions resolved. Each site opens its PEAK ticket report over the quarter, grouped by assignee
- **A team ranking** labelled Companies, of companies: each company's actions resolved, its name and logo, and for whichever leads its sites as the meta line, "4 sites". Each company opens its PEAK ticket report at its sites, narrowed to its assignees and grouped by site
- **A team ranking** labelled Assignees, of assignees: each person's actions resolved, their name, their company and its logo, and for whoever leads a meta line of their company and their sites, "Kestrel Air Services · 2 sites". Each person opens their PEAK ticket report at their sites, narrowed to them and grouped by company. It also carries each person's shoutout: their first name, their email and their busiest site, where they resolved the most in the quarter, ties alphabetical

The reports are PEAK's ticket report over the quarter, one `site_ids` per site and one `assignee_ids` per assignee named:

- Site: `https://ace.cimenviro.com/reports/tickets?site_ids={{site_id}}&start_date={{quarter_start}}T00:00:00.000&end_date={{quarter_end}}T00:00:00.000&grouping=assignee`
- Company: the same at the company's sites, with `&grouping=site&assignee_ids={{assignee_id}}` for each of its assignees on an action resolved in the quarter
- Person: the same at their sites, with `&grouping=user_entity&assignee_ids={{assignee_id}}`

## Data

All in the main batch:

| Need | Call |
| --- | --- |
| Resolved in the quarter, per site | `count_tickets(ticket_types:["escalated"], aggregate_entities:["site"], statuses:["open","in_progress","closed","on_hold"])` resolved over the quarter, 20 sites a call |
| Resolved a month earlier, per site | the same, resolved over the quarter a month earlier |
| Who resolved each action | `tickets.tickets` (`type:"escalated"`, `ticket_archived:false`, every `site_ids`) resolved over the quarter, `limit:1000` |
| Who resolved each action a month earlier | the same, resolved over the quarter a month earlier |

- The ticket pulls select only `ticket_id`, `site_id`, `status_id`, and `assignees` with `id`, `firstname`, `lastname`, `email`, `entity.name` and `entity.logo_url`: who holds each action and their company, never what anyone wrote
- `report.py next` pages each pull from its first page's total, 1000 rows a page
- Every site figure is a `count_tickets` count. The ticket rows only say who holds each action
- Rows with status Not Doing are dropped from the pulls
- Each company's logo is fetched once from the link on its assignees and embedded; a company without one gets its initials
- Each window is read in each site's own time zone
