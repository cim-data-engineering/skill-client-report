# Issues raised vs resolved

Owns the operational impact faults resolved row and the monthly alerts raised vs resolved chart. Scaffold part: `monthly-alerts`.

## Fetch

- The shared action pull in SKILL.md carries the monthly buckets and the resolution dates behind the median. One pull serves this section, the leaderboard and key wins
- `search_alert_tickets` for the recovery rate: alerts resolved in the window with status closed, read against their fault status. The analytics overview's `limit:1` count does not cover this — the rate needs the resolved rows themselves

## Operational impact row

| Rating chip                        | Metric label                                | Value                                                                                       | Subtitle                                                                                                                                        |
| ---------------------------------- | ------------------------------------------- | ------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| See below alert recovery benchmark | x faults resolved with x% verified recovery | Resolved alerts with current status closed last 3 months and current rule status is running | Median time to resolve of x days. Based on the alert's linked action creation and resolution date, not the alert's own creation and resolution date |

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
Date: last 6 complete months plus the current month to date

Grouped bars by month.

- **Raised**: actions created in the month. Count the alerts linked to each action, or 1 where an action has none, since work was still raised
- **Resolved**: actions resolved in the month, counted the same way
- **Exclude**: actions marked Not Doing, and alerts whose rule is no longer running, from both series

## Notes band items

- **Verified recovery.** Recovery rate is alerts resolved in the period with fault status recovered, divided by all alerts resolved in the period, counting alerts with status closed on rules still running
- **Median time to resolve** is measured from the linked action's creation to its resolution — not from the alert's own dates, since detection is automatic but resolution is human work
- **Raised vs resolved.** Raised means an alert ticket is triaged into an action ticket, not when the alert ticket was created — detection is automatic, raising is a human triage decision. Resolved counts the same way on resolution date. Rules must be running; actions marked Not Doing are excluded from both series
- Label the last month as partial. Both series run short there because the month is young, so say it in the chart note rather than letting the reader read a slowdown
