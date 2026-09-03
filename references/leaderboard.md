# Action leaderboard

Owns the assignee leaderboard. No operational impact row. Scaffold part: `assignee-leaderboard`.

## Fetch

The shared action pull in SKILL.md over the 6 month window covers Resolved and the assignee names. Open now is a different question — work raised before the window can still be open today — so also read the open set with `search_action_tickets(status_ids:[1,3,7])`, unbounded by date, and count by assignee as at the issue date.

## Assignee leaderboard

Who closed the work
Date: last 6 months

| Column          | Reference                                |
| --------------- | ---------------------------------------- |
| Rank            | Position by actions resolved             |
| Assignee        | Action ticket assignee full name         |
| Company         | Assignee company name                    |
| Resolved        | Actions resolved in the period           |
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
- Truncate assignee and company name with ellipsis, do not wrap rows

**Links:**

- Add link to PEAK assignee leaderboard with last 6 month custom date range selected
- `https://ace.cimenviro.com/reports/tickets?site_ids={{site_id}}&start_date=2026-02-01T00:00:00.000&end_date=2026-07-31T00:00:00.000&grouping=assignee`

## Notes band item

- **Completion rate** is resolved / (resolved + currently open) as at the issue date, so 100% reflects holding no open work
