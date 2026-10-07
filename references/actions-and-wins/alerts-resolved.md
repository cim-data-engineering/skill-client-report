# Alerts resolved and leaderboard

Owns the operational impact faults resolved row, monthly alerts raised vs resolved, and the actions leaderboard. Scaffold parts: `monthly-alerts`, `actions-leaderboard`.

The two answer the same question from either end: how much fault work the site took on, and who closed it. Both come from counts of action tickets. Script: `scripts/alerts_resolved.py`, which builds every figure, row, link and note below. This reference and `key-wins.md` are one choice in the section prompt, Actions and key wins.

## What you write

One note in `prose.json`, from the facts `report.py bundle` prints:

- `alerts_trend`, under raised vs resolved: the balance across the six months. Every bar covers a whole month, so a fall in either series is real. A month where raised runs far above resolved, or a resolved peak that a bulk close-out explains, is worth a sentence

Nothing resolved in the window means no section. The recovery rate has no denominator, "who closed the work" has no answer, and a leaderboard of people sitting on zero is not one. Delete the section, its operational impact row and its notes items, and give the open count in chat instead. Key wins follows the same rule. A newly onboarded site is where this happens.

## Operational impact row

| Rating chip                        | Metric label                                | Value                                                                                       | Subtitle                                                                                                                                           |
| ---------------------------------- | ------------------------------------------- | ------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| See below alert recovery benchmark | x faults resolved with x% verified recovery | Resolved alerts with status closed over the quarter, on rules still running | Median time to resolve of x days. Based on the alert's linked action creation and resolution date, not the alert's own creation and resolution date |

Section link, labelled "See live issues being resolved": the `platform_link` off the plain verified recovery count in Data recipes, which opens the alerts this row is counting. Bundle slot `alerts`.

## Alert recovery benchmark

Recovery rate is alerts resolved in the period with fault status recovered divided by all alerts resolved in the period. Filter for alerts with status closed.

| Rating    | Recovery rate |
| --------- | ------------- |
| Excellent | >= 99%        |
| Good      | >= 95%        |
| Average   | >= 90%        |
| Poor      | < 90%         |

## Monthly alerts raised vs resolved

Faults triaged and resolved
Date: the six complete months ending with the quarter

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
| Assignee        | Action ticket assignee full name         |
| Company         | Assignee company name                    |
| Resolved        | Actions resolved in the window           |
| Completion rate | Resolved / (resolved + open now) x%      |
| Open now        | Actions currently open, as at issue date |

**Display:**

- Rank by resolved descending, tie-break on completion rate descending
- Trophy glyph replaces the rank numeral at 1. Nothing on 2 or 3
- Completion rate as a bar on a 0-100 scale with the value beside it
- Open now emphasised when non-zero, muted at zero
- Resolved and Open now as plain numerals. No bars
- Close with a total row, separated from the rank
- Include assignees with zero resolved but open actions. Exclude actions marked as Not Doing
- Exclude non-human users from the leaderboard: Agent Hannah, or any other agent. They still count in raised vs resolved. No need to call this out in the report
- Truncate assignee and company name with ellipsis, do not wrap rows

**Links:**

- Add link to the PEAK actions leaderboard over the same 6 month window. No call answers this page, `count_tickets` included, so it is the one link in the report built from parts: substitute the site id, the 6 month window's first day and the quarter's last day, both `YYYY-MM-DD`. Bundle slot `leaderboard`
- `https://ace.cimenviro.com/reports/tickets?site_ids={{site_id}}&start_date={{trend_start}}T00:00:00.000&end_date={{quarter_end}}T00:00:00.000&grouping=assignee`

## Notes band items

- **Verified recovery.** Recovery rate is alerts resolved in the period with fault status recovered, divided by all alerts resolved in the period, counting alerts with status closed on rules still running
- **Median time to resolve** is measured from the linked action's creation to its resolution, not from the alert's own dates, since detection is automatic but resolution is human work
- **Raised vs resolved.** Raised counts action tickets created in the month, not the alerts behind them: detection is automatic, raising an action is a human triage decision, and one action can be linked to many alerts. Resolved counts actions on their resolution date. Actions marked Not Doing are excluded from both series
- **Completion rate** is resolved / (resolved + currently open) as at the issue date, so 100% reflects holding no open work
- Every bar covers a whole month, so a fall in either series is real. A month where raised runs far above resolved is worth a sentence in the chart note

## Data

All in the main batch:

| Need | Call |
| --- | --- |
| Leaderboard Resolved | `count_tickets` by `assignee`, resolved over the 6 month window |
| Leaderboard Open now | `count_tickets` by `assignee`, statuses open, in progress and on hold, no date bound |
| Raised and resolved series | `count_tickets` ungrouped, one per month per series, on each month's own bounds, since it has no month bucket |
| Median, company names | `tickets.tickets` resolved over the 6 month window, fields `age`, `resolved_at`, `status_id`, `assignees{id, entity{name}}` |
| Company of anyone with only open work | `tickets.tickets` Open now, `status_ids:[1,3,7]`, selecting only `status_id` and `assignees{id, entity{name}}` |
| Verified recovery | `search_alert_tickets(status:"closed", rule_states:["running"])` over the quarter, plain and with `fault_statuses:["recovered"]`, `limit:1` each: the two `pagination.total` values |

- Every count carries `ticket_types:["escalated"]`, which counts actions, one per ticket, never the alerts behind them: an action can be bulk-linked to dozens of alerts. Every status list leaves out Not Doing. The server reads each window in site time, and a count cannot be cut short by a `limit`
- The leaderboard joins the two assignee counts on `assignee_id`, keeping anyone with open work and nothing resolved, leaving out the null id (unassigned work) and any agent by name. Company is `entity{name}` for the same id off the rows
- The median runs over the actions resolved in the quarter, the operational impact row's own window, from `age`, which on a resolved action is the milliseconds from creation to resolution. Under a day it reads in hours
- `count_tickets` is no substitute for the alert counts: it cannot filter on alert status or rule state
- Closures that land minutes apart, ten or more in a run, are a bulk close-out rather than repairs. `facts.md` names them, since they explain a resolved peak
