#!/usr/bin/env python3
"""Open P1-2 actions: the sites and the people holding the most priority 1 and 2 actions open
now, most first, each count split by how long the actions have been open, and each name
opening its PEAK ticket report, then the portfolio's open P1-2 backlog at each of the last five
month ends and now. Not a leaderboard: no moves and no award. The lists and the backlog now come
from the one ticket pull, each month end from two counts. See
references/portfolio-leaderboard/actions-and-wins/open-actions.md.
"""
import os
import sys
from collections import defaultdict
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "scripts"))
import peak_io as io  # noqa: E402
import portfolio_io as pio  # noqa: E402

NAME = "open-actions"
PRIORITIES = [1, 2]
PAGE = 1000
SHOWN = 20
DAY_MS = 86400000
AGES = (60, 30)                        # days: 60 or more, 30 to 60, under 30
UNNAMED, NOBODY = "Unnamed assignee", "No assignee"
COUNT_CHUNK = 20
BACKLOG_MONTHS = 6                     # the issue month to date and the five month ends before it
OPEN = ["open", "in_progress", "on_hold"]
# The rows say only who holds each action and how long it has been open: ids, its age, and each
# assignee's company with its logo link. PEAK refuses the whole pull when any assignee has no name
# recorded, so names come from a count by assignee. Never what anyone wrote.
FIELDS = ["ticket_id", "site_id", "status_id", "age", "assignees.id", "assignees.entity.name",
          "assignees.entity.logo_url"]


def pulls(ctx):
    return pio.split(ctx, "op/rows.json", len(ctx["sites"]), lambda f, ids: io.gql(
        f, "tickets.tickets", {"type": "escalated", "site_ids": ids, "ticket_archived": False, "limit": PAGE,
                               "status_ids": [1, 3, 7], "priority_ids": PRIORITIES}, FIELDS))


def month_ends(ctx):
    """[(first of the month, first of the next)] for the five complete months before the issue
    month, oldest first: each backlog bar counts what was open as its month closed."""
    t = io.d(ctx["today"])
    first = date(t.year, t.month, 1)
    return [(io.add_months(first, k), io.add_months(first, k + 1)) for k in range(1 - BACKLOG_MONTHS, 0)]


def backlog_calls(ctx):
    """Two counts a month end, `end` the first of the next month: actions raised before it and still
    open now, and actions raised before it and closed on or after it. Together they are every action
    open as the month closed, at the priority it holds now."""
    out = []
    for m, end in month_ends(ctx):
        tag, bound = m.strftime("%Y-%m"), end.isoformat()
        out += pio.split(ctx, "op/backlog-%s-open.json" % tag, COUNT_CHUNK, lambda f, ids: io.call(
            f, "count_tickets", site_ids=ids, ticket_types=["escalated"], statuses=OPEN, priorities=PRIORITIES,
            local_created_end=bound))
        out += pio.split(ctx, "op/backlog-%s-closed.json" % tag, COUNT_CHUNK, lambda f, ids: io.call(
            f, "count_tickets", site_ids=ids, ticket_types=["escalated"], statuses=OPEN + ["closed"],
            priorities=PRIORITIES, local_created_end=bound, local_resolved_start=bound))
    return out


def calls(ctx):
    return pulls(ctx) + pio.split(ctx, "op/assignees.json", COUNT_CHUNK, lambda f, ids: io.call(
        f, "count_tickets", site_ids=ids, ticket_types=["escalated"], aggregate_entities=["assignee"],
        statuses=OPEN, priorities=PRIORITIES)) + backlog_calls(ctx)


def backlog(ctx, work, now):
    """The open P1-2 backlog at each month end, then `now`, the count open as at the issue date, under
    the issue month to date. None for a month end whose counts were not saved."""
    def summed(name):
        files = pio.chunk_files(work, name)
        return sum(r.get("ticket_count") or 0 for f in files for r in work.get(f).rows) if files else None
    values, months = [], []
    for m, _ in month_ends(ctx):
        tag = m.strftime("%Y-%m")
        a, b = summed("op/backlog-%s-open.json" % tag), summed("op/backlog-%s-closed.json" % tag)
        values.append(None if a is None or b is None else a + b)
        months.append(io.mon(m.isoformat()))
    t = io.d(ctx["today"])
    months.append(io.mon(date(t.year, t.month, 1).isoformat()))
    values.append(now)
    told = ", ".join("%s %s" % (m, "no data" if v is None else v) for m, v in zip(months, values))
    return {"months": months, "values": values, "to_date": True,
            "note": "Each month end counts the actions raised by then and not yet closed, at the priority "
                    "each holds now. %s counts those open as at %s." % (months[-1], io.day_long(ctx["today"])),
            "alt": "Bar chart of open priority 1 and 2 actions at each month end, %s to date: %s."
                   % (months[0], told)}


def more(ctx, work):
    return pio.pages_due(work, pulls(ctx), PAGE, nested=True)


def link(ctx, since, site_ids, grouping, assignee_ids=()):
    """PEAK's ticket report from `since`, the day the oldest action it counts was raised, to today at these
    sites, priority 1 and 2 only, grouped by "site" or "assignee", narrowed to these assignees where any
    are given, so every action the list counts is in it however long it has been open."""
    end = io.d(ctx["today"])
    params = (["site_ids=%s" % i for i in site_ids]
              + ["start_date=%sT00:00:00.000" % since, "end_date=%sT23:59:59.999" % end.isoformat(),
                 "grouping=%s" % grouping]
              + ["priority_ids=%d" % p for p in PRIORITIES] + ["assignee_ids=%s" % a for a in assignee_ids])
    return "%s/reports/tickets?%s" % (pio.host(ctx), "&".join(params))


def raised(ctx, age_ms):
    """The day an action open `age_ms` was raised, counting back from the issue date."""
    from datetime import timedelta
    return (io.d(ctx["today"]) - timedelta(days=int((age_ms or 0) // DAY_MS) + 1)).isoformat()


def bucket(age_ms):
    """0 for open 60 days or more, 1 for 30 to 60 days, 2 for under 30."""
    days = (age_ms or 0) / DAY_MS
    return 0 if days >= AGES[0] else 1 if days >= AGES[1] else 2


def most_first(counts, name):
    """[(rank, key)], most first, ties alphabetical by name."""
    return list(enumerate(sorted(counts, key=lambda k: (-counts[k], name(k).strip().lower(), str(k))), 1))


def build(ctx, work, shared):
    raw = pio.rows(work, "op/rows.json", PAGE)
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
    logos = pio.fetch_logos({c: u for c, u in pio.logo_links(actions).items() if c in shown})

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

    note = "Priority 1 and 2 actions open as at %s by age open." % io.day_long(ctx["today"])
    over = [what for n, what in ((len(listed), "%d sites" % len(listed)), (len(set(people) - {NOBODY}), "%d assignees" % len(set(people) - {NOBODY})))
            if n > SHOWN]
    if over:
        note += " Top %d of %s." % (SHOWN, " and ".join(over))
    month = "%s %d" % (io.month(ctx["today"]), io.d(ctx["today"]).year)
    return {"open_actions": {"panels": [{"title": "Sites", "rows": site_rows},
                                        {"title": "Assignees", "rows": person_rows}],
                             "backlog": backlog(ctx, work, len(actions))},
            "dated_heads": {"Open P1-2 actions": {"date": month, "note": note}}}
