# Alerts resolved and leaderboard

Owns the operational impact faults resolved row, monthly alerts raised vs resolved, and the assignee leaderboard. Scaffold parts: `monthly-alerts`, `assignee-leaderboard`.

The two go together because they answer the same question from either end — how much fault work the site took on, and who closed it — from one pull of action tickets.

Nothing resolved in the window means no section. The recovery rate has no denominator, "who closed the work" has no answer, and a leaderboard of people sitting on zero is not one. Delete the section, its operational impact row and its notes items, and give the open count in chat instead — the same rule Key wins follows. A newly onboarded site is where this happens.

## Fetch

- The shared action pull in SKILL.md carries the resolved rows behind the leaderboard, the median, and the resolved series; the raised series comes from its per-month counts
- `search_alert_tickets` for the recovery rate: alerts resolved in the window with status closed, read against their fault status. This is the only call in the report that reads alert tickets, so it does not run at all when this section is out
- Open now is a different question from Resolved: work raised before the window can still be open today. Read the open set with the Open now calls in Shared data — one per open status, unbounded by date — and count by assignee as at the issue date

## Operational impact row

| Rating chip                        | Metric label                                | Value                                                                                       | Subtitle                                                                                                                                           |
| ---------------------------------- | ------------------------------------------- | ------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| See below alert recovery benchmark | x faults resolved with x% verified recovery | Resolved alerts with status closed over the quarter, on rules still running | Median time to resolve of x days. Based on the alert's linked action creation and resolution date, not the alert's own creation and resolution date |

Section link, labelled "See live issues being resolved":
`https://ace.cimenviro.com/tickets/escalated/search?tickets_order_by=updated_at%20DESC&site_ids={{site_id}}&status_ids=6&archived=false`

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
Date: the seven complete months ending with the quarter

Grouped bars by month.

- **Raised**: actions created in the month, one per action
- **Resolved**: actions resolved in the month, one per action
- **Exclude**: actions marked Not Doing from both series

## Assignee leaderboard

Who closed the work
Date: the 7 month window

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
- Exclude non-human users from the leaderboard — Agent Hannah, or any other agent. They still count in raised vs resolved. No need to call this out in the report
- Truncate assignee and company name with ellipsis, do not wrap rows

**Links:**

- Add link to the PEAK assignee leaderboard over the same 7 month window
- `https://ace.cimenviro.com/reports/tickets?site_ids={{site_id}}&start_date={{trend_start}}T00:00:00.000&end_date={{quarter_end}}T00:00:00.000&grouping=assignee`

## Notes band items

- **Verified recovery.** Recovery rate is alerts resolved in the period with fault status recovered, divided by all alerts resolved in the period, counting alerts with status closed on rules still running
- **Median time to resolve** is measured from the linked action's creation to its resolution — not from the alert's own dates, since detection is automatic but resolution is human work
- **Raised vs resolved.** Raised counts action tickets created in the month, not the alerts behind them: detection is automatic, raising an action is a human triage decision, and one action can be linked to many alerts. Resolved counts actions on their resolution date. Actions marked Not Doing are excluded from both series
- **Completion rate** is resolved / (resolved + currently open) as at the issue date, so 100% reflects holding no open work
- Every bar covers a whole month, so a fall in either series is real. A month where raised runs far above resolved is worth a sentence in the chart note
