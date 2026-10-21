# Alerts resolved and leaderboard

Owns the operational impact faults resolved row, monthly actions raised vs resolved, and the actions leaderboard. Scaffold parts: `monthly-alerts`, `actions-leaderboard`.

The two answer the same question from either end: how much fault work the site took on, and who closed it. Both come from counts of action tickets. Script: `scripts/alerts_resolved.py`, which builds every figure, row, link and note below.

## What you write

Nothing. The script fills the chart and the leaderboard.

A window with nothing resolved means no section. With no alert closed in the quarter the recovery rate has no denominator; with no action resolved in the six months "who closed the work" has no answer, and a leaderboard of people sitting on zero is not one. Either one leaves out the section, its operational impact row, its notes items and its partial figures in the reporting window note. The script says in chat which it was, with the counts left unshown. Key wins goes with it. A newly onboarded site is where this happens.

## Operational impact row

| Rating chip                        | Metric label                                | Value                                                                                       | Subtitle                                                                                                                                           |
| ---------------------------------- | ------------------------------------------- | ------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| See below alert recovery benchmark | x faults resolved with x% verified recovery | Resolved alerts with status closed over the quarter, on rules still running | Median time to resolve of x days. Based on the alert's linked action creation and resolution date, not the alert's own creation and resolution date |

## Alert recovery benchmark

Recovery rate is alerts resolved in the period with fault status recovered divided by all alerts resolved in the period. Filter for alerts with status closed.

| Rating    | Recovery rate |
| --------- | ------------- |
| Excellent | >= 99%        |
| Good      | >= 95%        |
| Average   | >= 90%        |
| Poor      | < 90%         |

## Monthly actions raised vs resolved

Faults triaged and resolved
Date: the six complete months ending with the quarter, and the month to date where the report carries one

Grouped bars by month.

- **Raised**: actions created in the month, one per action
- **Resolved**: actions resolved in the month, one per action
- **Exclude**: actions marked Not Doing from both series

## Actions leaderboard

Who closed the work
Date: the 6 month window

| Column          | Reference                                |
| --------------- | ---------------------------------------- |
| Rank            | Position by actions resolved             |
| Assignee        | Company logo, then assignee full name    |
| Company         | Assignee company name                    |
| Resolved        | Actions resolved in the window           |
| Completion rate | Resolved / (resolved + open now) x%      |
| Open now        | Actions currently open, as at issue date |

**Display:**

- Rank by resolved descending, tie-break on completion rate descending
- Trophy glyph replaces the rank numeral at 1. Nothing on 2 or 3
- Completion rate as a bar on a 0-100 scale with the value beside it, to 0dp
- Open now emphasised when non-zero, muted at zero
- Resolved and Open now as plain numerals. No bars
- Close with a total row, separated from the rank
- Include assignees with zero resolved but open actions. Exclude actions marked as Not Doing
- Exclude CIM's own system accounts from the leaderboard: CIM Support, the CIM API logins and the AI agents (Agent Hannah, or any other agent). `peak_io.system_account` decides by PEAK user id, from the list in `peak_io.SYSTEM_ACCOUNTS`, with the agent name rule for agents added later. CIM's people rank like anyone else, and so do contractors' shared logins, such as a dispatch desk or a generic BMS account. The excluded accounts' actions still count in raised vs resolved and faults resolved. No need to call this out in the report
- Each assignee sits beside their company's logo in a square tile, as PEAK shows it. The script fetches each logo once from its `logo_url` and embeds it. A company without one gets its initials instead, and the script names it to say in chat
- Truncate assignee and company name with ellipsis, do not wrap rows

**Links:**

- Add link to the PEAK actions leaderboard over the same 6 month window. Bundle slot `leaderboard`
- `https://ace.cimenviro.com/reports/tickets?site_ids={{site_id}}&start_date={{trend_start}}T00:00:00.000&end_date={{quarter_end}}T00:00:00.000&grouping=assignee`

## Notes band items

- **Verified recovery.** Share of alerts closed in the period with the fault recovered. Includes only alerts on active rules
- **Raised vs resolved.** Counts actions, not alerts. One action can cover several alerts

## Data

All in the main batch:

| Need | Call |
| --- | --- |
| Leaderboard Resolved | `count_tickets` by `assignee`, resolved over the 6 month window |
| Leaderboard Open now | `count_tickets` by `assignee`, statuses open, in progress and on hold, no date bound |
| Raised and resolved series | `count_tickets` ungrouped, one per month per series, on each month's own bounds, since it has no month bucket |
| Median, companies | `tickets.tickets` resolved over the 6 month window, fields `age`, `resolved_at`, `status_id`, `assignees{id, entity{name, logo_url}}` |
| Company of anyone with only open work | `tickets.tickets` Open now, `status_ids:[1,3,7]`, selecting only `status_id` and `assignees{id, entity{name, logo_url}}` |
| Verified recovery | `search_alert_tickets(status:"closed", rule_states:["running"])` over the quarter, plain and with `fault_statuses:["recovered"]`, `limit:1` each: the two `pagination.total` values |

- Every count carries `ticket_types:["escalated"]`, which counts actions, one per ticket, never the alerts behind them: an action can be bulk-linked to dozens of alerts. Every status list leaves out Not Doing. The server reads each window in site time, and a count cannot be cut short by a `limit`
- The leaderboard joins the two assignee counts on `assignee_id`, keeping anyone with open work and nothing resolved, leaving out the null id (unassigned work) and CIM's system accounts by user id, or any agent by name: the counts carry no email, so the id list and the name rule decide. Company is `entity{name}` for the same id off the rows, and its logo `entity{logo_url}`, a PNG on PEAK's public downloads
- The median runs over the actions resolved in the quarter, the operational impact row's own window, from `age`, which on a resolved action is the milliseconds from creation to resolution. Under a day it reads in hours
- `count_tickets` is no substitute for the alert counts: it cannot filter on alert status or rule state
- Closures that land minutes apart, ten or more in a run, are a bulk close-out rather than repairs. The script names them to say in chat, since they explain a resolved peak
