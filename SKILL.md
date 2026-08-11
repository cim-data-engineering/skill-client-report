

## Sections

1. [Report title](#report-title)  
2. [Analytics overview](#analytics-overview)  
3. [Operational impact](#operational-impact)  
4. [Equipment health snapshot](#equipment-health-snapshot)  
5. [Monthly equipment health](#monthly-equipment-health)  
6. [Alerts raised vs resolved](#alerts-raised-vs-resolved)  
7. [Assignee leaderboard](#assignee-leaderboard)  
8. [Key wins](#key-wins)

## Report title {#report-title}

* \[Site name\] Quarterly Building Performance Review  
  Prepared by: \[Company name\] \- \[Company service name\]. Powered by PEAK  
* Reporting period: \[last 3 months date range\]  
* Issue date: \[issue date\]  
* Company name default “CIM” unless given  
* Company service name default “Data Driven Operations” 

## Analytics overview {#analytics-overview}

Date: as at issue date

| Display metric | Reference |
| :---- | :---- |
| Building size | Use sqm or sqft per region |
| Equipment | Total equipment |
| Sensors | Total sensors |
| Rules | Total rules status running |

## Operational impact {#operational-impact}

Date: last 3 months

| Rating chip | Metric label | Value | Subtitle |
| :---- | :---- | :---- | :---- |
| See below equipment score benchmark | \[x.x\]% equipment health maintained | Site equipment health score last 3 months | Up \[x.x\] pp vs \[y.y\]% over the last 12 months |
| Continuous | \[x\] automated equipment health checks ran 24/7 | Total executions last 3 months | Averaging \[x\] monthly checks across \[y\] scored rules |
| Modelled | $\[x\] labor cost avoided | See below labor cost avoided model | \[x\] hours and \[y.y\] working days of inspection time |
| See below alert recovery benchmark  | \[x\] faults resolved with \[x\]% verified recovery | Resolved alerts with current status closed last 3 months | Median time to resolve of \[x\] days. Based on alert’s linked action creation and resolution date, do not use the alert creation and resolution date. |

**Equipment score benchmark:**

| Rating | Equipment health score |
| :---- | :---- |
| Excellent | \>= 99% |
| Good | \>= 97% |
| Average | \>= 90% |
| Poor | \< 90% |

**Labor cost avoided model:**  
Unique rules scored (by priority) last 3 months x annual mins saved per rule x (days in window / 365\) x labor cost per minute. Convert labor cost per hour to GBP, EUR or AUD based on site country and currency.

| Priority | Annual checks | Mins per check | Annual mins saved per rule | Labor cost per hour ($US) | Annual cost saved per rule ($US) |
| :---- | :---- | :---- | :---- | :---- | :---- |
| P1 | 365 | 0.50 | 182.5 | $150 | $456.25 |
| P2 | 52 | 1.00 | 52.0 | $150 | $130.00 |
| P3 | 12 | 1.00 | 12.0 | $150 | $30.00 |
| P4-5 | 4 | 1.00 | 4.0 | $150 | $10.00 |

*Footnote:*  
Each rule replaces a manual inspection at a set frequency by priority: P1 daily at 0.5 mins per check, P2 weekly, P3 monthly, P4-5 quarterly, all at 1 min. Savings prorate that annual effort over the period, valued at $150/hr.

### 

**Alert recovery benchmark:**  
Recovery rate is alerts resolved in the period with fault status recovered divided by all alerts resolved in the period. Filter for alerts with status closed.

| Rating | Recovery rate |
| :---- | :---- |
| Excellent | \>= 99% |
| Good | \>= 95% |
| Average | \>= 90% |
| Poor | \< 90% |

## Equipment health snapshot {#equipment-health-snapshot}

Date: last complete month vs last 3 months

| Column | Reference |
| :---- | :---- |
| Equipment type | Equipment types with at least one scored rule |
| Equipment | Total equipment count of that type with a scored rule |
| Rules | Total scored rules on that type |
| Last month | Equipment health score, last month by type \[x.x\]% |
| Chg | Last month minus last 3 months in pp \[x.x\] |

**Display:**

* Score as a bar on a 0-100 scale with the value beside it  
* Rating chip beside the score, per equipment score benchmark  
* Chg signed with a direction glyph. Green up, red down, muted when flat  
* Equipment and Rules as plain numerals. No bars.  
* Sort by biggest positive Chg signed then by biggest negative Chg signed  
* Close with a site row, separated from the sort  
* Display all equipment types, not a sample  
* Exclude equipment type BACER or Bacer (System). These are platform health checks  
* Color the rating, not the bar.

**Links:**

* Hyperlink equipment type name to PEAK with last 3 month custom date range selected   
* https://ace.cimenviro.com/dashboard/equipment-health?site\_ids={{site\_id}}\&start\_date=2026-05-01T00:00:00.000\&end\_date=2026-07-31T00:00:00.000\&equipment\_type\_ids={{equipment\_type\_id}} 

## Monthly equipment health {#monthly-equipment-health}

Date: last 6 months

Chart 1: Site equipment health score  
Monthly line chart of equipment health score. Auto scale Y axis.

Chart 2: Site automated health checks  
Monthly bar chart of total automated rule checks.

**Display**

* Display values on points. Chart 1 display 1dp \[x.x\]% and Chart 2 compact number formatting  
* Add chart titles

## Alerts raised vs resolved {#alerts-raised-vs-resolved}

Date: 6 months

Grouped bars by month.

* **Raised**: actions created in the month. Count the alerts linked to each action, or 1 where an action has none, since work was still raised.  
* **Resolved**: actions resolved in the month, counted the same way.  
* **Exclude**: actions marked Not Doing from both series.

**Notes**

* Raised means an alert ticket is triaged into an action ticket, not when the alert ticket was created. Detection is automatic, raising is a human triage decision.  
* Filter on rule state is running. If an action is not linked to an alert still count it.

## Assignee leaderboard {#assignee-leaderboard}

Date: last 6 months

| Column | Reference |
| :---- | :---- |
| Rank | Position by actions resolved |
| Assignee | Action ticket assignee full name |
| Company | Assignee company name |
| Resolved | Actions resolved in the period |
| Completion rate | Resolved / (resolved \+ currently open) \[x\]% |
| Open now | Actions currently open, as at issue date |

**Display:**

* Rank by resolved descending, tie-break on completion rate descending  
* Trophy glyph replaces the rank numeral at \#1. Nothing on \#2 or \#3  
* Completion rate as a bar on a 0-100 scale with the value beside it  
* Open now emphasised when non-zero, muted at zero  
* Resolved and Open now as plain numerals. No bars  
* Close with a total row, separated from the rank  
* Include assignees with zero resolved but open actions. Exclude actions marked as Not Doing

## Key wins {#key-wins}

Date: last 3 months

Highlight resolved or open actions, written for the facilities manager or building owner.

**Audience:**  
Written by the partner maintaining the site, delivered to the facilities manager, forwarded by them to the owner. Each win must evidence custodianship: the building is watched, faults are found and fixed, closures are verified rather than asserted. Write from the partner’s side, not the platform’s.

**Selection:**  
Read the comment history on each candidate. A win needs a physical or control change described by whoever made it. 

Exclude actions resolved by stopping, tuning or ignoring a rule, platform, integration or data mapping work, actions marked as not doing.

**Display:**

* Heading names the outcome and the equipment type and name.  
* Two to three sentences: what was wrong, what was changed, why it matters  
* Lead with the building outcome: comfort, reliability, energy, tenant experience  
* Rank by what the owner cares about. Critical plant over terminal units, permanent fixes over one-off resets  
* Link the action ticket with PEAK url for quick reference evidence  
* Where several tickets form one win link them all  
* Where win appears in the equipment health snapshot say so.