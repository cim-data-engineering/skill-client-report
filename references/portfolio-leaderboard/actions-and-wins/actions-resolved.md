# Actions resolved

Owns the actions resolved counts and ticket pulls, and hands them on as rankings: each site's actions resolved, and each company's and each person's. It has no part on the page. Script: `scripts/actions_resolved.py`, which builds every ranking below.

## What you write

Nothing on the page. In chat, say what the script prints: any company shown with its initials for want of a logo, and any account PEAK holds no name or company for, by its user id, for ops to name in PEAK.

## Definitions

- **Resolved**: an action resolved in the quarter, in any status but Not Doing
- **Actions, not alerts**: every count is of action tickets, one per action, never the alerts behind them
- **Who resolved it**: the action's assignees. An action counts once for each company holding it and once for each person. The site ranking counts every action, whoever resolved it
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
| Resolved in the quarter, per site | `count_tickets(ticket_types:["escalated"], aggregate_entities:["site"], statuses:["open","in_progress","closed","on_hold"])` resolved over the quarter, 20 sites a call |
| Resolved a month earlier, per site | the same, resolved over the quarter a month earlier |
| Each person's name | the same counts with `aggregate_entities:["assignee"]`, over the quarter and over the quarter a month earlier: `assignee_name` by `assignee_id` |
| Who resolved each action | `tickets.tickets` (`type:"escalated"`, `ticket_archived:false`, every `site_ids`) resolved over the quarter, `limit:1000` |
| Who resolved each action a month earlier | the same, resolved over the quarter a month earlier |
| The Assignees leader's first name and email | once the pulls are whole, `report.py next` prints one `tickets.tickets` on one ticket of the leader's whose assignees all have names, selecting `ticket_id` and `assignees` with `id`, `firstname` and `email`: `ar/leader.json` |

- The ticket pulls select only `ticket_id`, `site_id`, `status_id`, and `assignees` with `id`, `entity.name` and `entity.logo_url`: who holds each action and their company, never what anyone wrote. No names or emails: PEAK refuses the whole pull when one assignee has none, so names come from the counts by assignee
- `report.py next` pages each pull from its first page's total, 1000 rows a page
- Every site figure is a `count_tickets` count. The ticket rows only say who holds each action
- Rows with status Not Doing are dropped from the pulls
- Each company's logo is fetched once from the link on its assignees and embedded; a company without one gets its initials
- Each window is read in each site's own time zone
