#!/usr/bin/env python3
"""Open P1-2 actions: the portfolio's open P1-2 backlog at each month end over the past year, then
the sites and the people holding the most priority 1 and 2 actions open now, most first, each split
by how long the actions have been open, and each name opening its PEAK ticket report. Not a
leaderboard: no moves and no award. See references/portfolio-leaderboard/actions-and-wins/open-actions.md.
"""
import os
import sys
from collections import defaultdict
from datetime import date, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "scripts"))
import peak_io as io  # noqa: E402
import portfolio_io as pio  # noqa: E402

NAME = "open-actions"
PRIORITIES = [1, 2]
PAGE = 1000
SHOWN = 10                             # a list, so the backlog chart and both lists hold one page
DAY_MS = 86400000
AGES = (60, 30)                        # days: 60 or more, 30 to 60, under 30, the buckets PEAK shows
UNNAMED, NOBODY = "Unnamed assignee", "No assignee"
COUNT_CHUNK = 20
BACKLOG_MONTHS = 12                    # the issue month and the eleven month ends before it
# The rows say only who holds each action, when it was raised and how long it has been open: ids, its
# dates and age, and each assignee's company with its logo link. PEAK refuses the whole pull when any
# assignee has no name recorded, so names come from a count by assignee. Never what anyone wrote.
FIELDS = ["ticket_id", "site_id", "status_id", "age", "created_at", "assignees.id", "assignees.entity.name",
          "assignees.entity.logo_url"]
# The closed actions say only when each was raised and closed.
CLOSED_FIELDS = ["ticket_id", "site_id", "created_at", "resolved_at"]


def pulls(ctx):
    return pio.split(ctx, "op/rows.json", len(ctx["sites"]), lambda f, ids: io.gql(
        f, "tickets.tickets", {"type": "escalated", "site_ids": ids, "ticket_archived": False, "limit": PAGE,
                               "status_ids": [1, 3, 7], "priority_ids": PRIORITIES}, FIELDS))


def month_ends(ctx):
    """[(first of the month, first of the next)] for the eleven complete months before the issue
    month, oldest first: each backlog bar counts what was open as its month closed."""
    t = io.d(ctx["today"])
    first = date(t.year, t.month, 1)
    return [(io.add_months(first, k), io.add_months(first, k + 1)) for k in range(1 - BACKLOG_MONTHS, 0)]


def closed_pulls(ctx):
    """The P1-2 actions closed since the first month end: with the actions open now, every action open
    at any month end. Not doing is left out, as everywhere else."""
    since = month_ends(ctx)[0][1].isoformat()
    return pio.split(ctx, "op/closed.json", len(ctx["sites"]), lambda f, ids: io.gql(
        f, "tickets.tickets", {"type": "escalated", "site_ids": ids, "ticket_archived": False, "limit": PAGE,
                               "status_ids": [6], "priority_ids": PRIORITIES,
                               "resolved_at_local_start": since + "T00:00:00"}, CLOSED_FIELDS))


def calls(ctx):
    return pulls(ctx) + pio.split(ctx, "op/assignees.json", COUNT_CHUNK, lambda f, ids: io.call(
        f, "count_tickets", site_ids=ids, ticket_types=["escalated"], aggregate_entities=["assignee"],
        statuses=["open", "in_progress", "on_hold"], priorities=PRIORITIES)) + closed_pulls(ctx)


def more(ctx, work):
    return io.pages_due(work, pulls(ctx) + closed_pulls(ctx))


def backlog(ctx, work, open_rows):
    """The open P1-2 backlog at each month end, then as at the issue date under the issue month, each
    split by age open on the day: [60 days or more, 30 to 60, under 30]. A month end holds every
    action raised before the first of the next month and not closed by then."""
    tz = {s["site_id"]: s.get("timezone") for s in ctx["sites"]}
    day = lambda r, k: io.d(io.local_day(r[k], tz.get(r["site_id"]) or "UTC"))
    rows = [(day(r, "created_at"), None) for r in open_rows if r.get("created_at")]
    rows += [(day(r, "created_at"), day(r, "resolved_at")) for r in pio.rows(work, "op/closed.json")
             if r.get("created_at") and r.get("resolved_at")]
    today = io.d(ctx["today"])
    ends = [end for _, end in month_ends(ctx)] + [today + timedelta(days=1)]
    months = [io.mon(m.isoformat()) for m, _ in month_ends(ctx)] + [io.mon(date(today.year, today.month, 1).isoformat())]
    stacks = []
    for end in ends:
        ages = [0, 0, 0]
        for raised_on, closed_on in rows:
            if raised_on < end and (closed_on is None or closed_on >= end):
                ages[bucket(((end - timedelta(days=1)) - raised_on).days * DAY_MS)] += 1
        stacks.append(ages)
    values = [sum(a) for a in stacks]
    told = ", ".join("%s %d" % (m, v) for m, v in zip(months, values))
    return {"months": months, "values": values, "stacks": stacks,
            "alt": "Stacked bar chart of open priority 1 and 2 actions at each month end by age open, %s to %s: %s."
                   % (months[0], months[-1], told)}


def link(ctx, since, site_ids, grouping, assignee_ids=()):
    """PEAK's ticket report from `since`, the day the oldest action it counts was raised, to today at these
    sites, priority 1 and 2 only, grouped by "site" or "assignee", narrowed to these assignees where any
    are given, so every action the list counts is in it however long it has been open."""
    end = io.d(ctx["today"])
    params = (["site_ids=%s" % i for i in site_ids]
              + ["start_date=%sT00:00:00.000" % since, "end_date=%sT23:59:59.999" % end.isoformat(),
                 "grouping=%s" % grouping]
              + ["priority_ids=%d" % p for p in PRIORITIES] + ["assignee_ids=%s" % a for a in assignee_ids])
    return "%s/reports/tickets?%s" % (io.host(*ctx["sites"]), "&".join(params))


def raised(ctx, age_ms):
    """The day an action open `age_ms` was raised, counting back from the issue date."""
    return (io.d(ctx["today"]) - timedelta(days=int((age_ms or 0) // DAY_MS) + 1)).isoformat()


def bucket(age_ms):
    """0 for open 60 days or more, 1 for 30 to 60 days, 2 for under 30."""
    days = (age_ms or 0) / DAY_MS
    return 0 if days >= AGES[0] else 1 if days >= AGES[1] else 2


def most_first(counts, name):
    """[(rank, key)], most first, ties alphabetical by name."""
    return list(enumerate(sorted(counts, key=lambda k: (-counts[k], name(k).strip().lower(), str(k))), 1))


def build(ctx, work, shared):
    raw = pio.rows(work, "op/rows.json")
    age = {r["ticket_id"]: bucket(r.get("age")) for r in raw}
    since = {r["ticket_id"]: raised(ctx, r.get("age")) for r in raw}
    names = {r["assignee_id"]: (r.get("assignee_name") or "").strip()
             for r in pio.rows(work, "op/assignees.json") if r.get("assignee_id")}
    site = {s["site_id"]: s for s in ctx["sites"]}
    actions = [a for a in pio.held(raw) if a["site"] in site]
    for act in actions:
        for a in act["assignees"]:
            a["name"] = names.get(a["id"]) or ""
    if not actions:
        return {"drop": [NAME], "chat": ["No priority 1 or 2 action is open across the portfolio, so the open "
                                         "P1-2 actions section is left out."]}

    # open actions by age at each site and with each person, the actions no one holds as one more
    site_ages, person_ages = defaultdict(lambda: [0, 0, 0]), defaultdict(lambda: [0, 0, 0])
    sites, who, oldest = defaultdict(set), {}, {}
    for act in actions:
        b = age[act["ticket"]]
        site_ages[act["site"]][b] += 1
        for k in [act["site"]] + [a["id"] for a in act["assignees"] if a["id"]]:
            oldest[k] = min(oldest.get(k, since[act["ticket"]]), since[act["ticket"]])
        holders = {a["id"] for a in act["assignees"] if a["id"]}
        for a in act["assignees"]:
            if a["id"]:
                who[a["id"]] = a
                sites[a["id"]].add(act["site"])
        for p in holders or {NOBODY}:
            person_ages[p][b] += 1
    on_sites = {s: sum(v) for s, v in site_ages.items()}
    people = {p: sum(v) for p, v in person_ages.items()}
    label = lambda p: NOBODY if p == NOBODY else (who[p]["name"] or UNNAMED)
    ranked_people = most_first(people, label)
    shown = {who[p]["company"] for _, p in ranked_people[:SHOWN] if p != NOBODY}
    logos = io.fetch_logos({c: u for c, u in pio.logo_links(actions).items() if c in shown})

    # every site with data, those holding none at 0
    pio.shown(shared, on_sites)
    listed = {s: on_sites.get(s, 0) for s in shared["shown_sites"] if s in site}
    site_rows = [{"rank": k, "name": site[s]["site_name"].strip(), "state": pio.region(ctx, site[s]),
                  "count": listed[s], "ages": site_ages[s],
                  "link": link(ctx, oldest[s], [s], "assignee") if listed[s] else None}
                 for k, s in most_first(listed, lambda s: site[s]["site_name"])[:SHOWN]]
    person_rows = []
    for k, p in ranked_people[:SHOWN]:
        row = {"rank": k, "name": label(p), "count": people[p], "ages": person_ages[p], "tile": {}}
        if p != NOBODY:
            co = who[p]["company"]
            row.update(company=co or None, tile={"company": co, "logo": logos.get(co)},
                       link=link(ctx, oldest[p], sorted(sites[p]), "site", [p]))
        person_rows.append(row)

    trend = backlog(ctx, work, raw)
    note = "Priority 1 and 2 open actions (new, in progress and on hold)."
    over = [what for n, what in ((len(listed), "%d sites" % len(listed)), (len(set(people) - {NOBODY}), "%d assignees" % len(set(people) - {NOBODY})))
            if n > SHOWN]
    if over:
        note += " Top %d of %s." % (SHOWN, " and ".join(over))
    month = "%s %d" % (io.month(ctx["today"]), io.d(ctx["today"]).year)
    return {"open_actions": {"panels": [{"title": "Sites", "rows": site_rows},
                                        {"title": "Assignees", "rows": person_rows}],
                             "backlog": trend},
            "dated_heads": {"Open P1-2 actions": {"date": month, "note": note}}}
