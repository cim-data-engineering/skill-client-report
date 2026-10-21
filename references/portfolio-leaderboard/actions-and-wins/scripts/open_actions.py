#!/usr/bin/env python3
"""Open P1-2 actions: the sites and the people holding the most priority 1 and 2 actions open
now, most first, each count split by how long the actions have been open, and each name
opening its PEAK ticket report. Not a leaderboard: no moves and no award. Every figure comes
from the one ticket pull. See references/portfolio-leaderboard/actions-and-wins/open-actions.md.
"""
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "scripts"))
import peak_io as io  # noqa: E402
import portfolio_io as pio  # noqa: E402

NAME = "open-actions"
PRIORITIES = [1, 2]
PAGE = 1000
SHOWN = 10
DAY_MS = 86400000
AGES = (60, 30)                        # days: 60 or more, 30 to 60, under 30
UNNAMED, NOBODY = "Unnamed assignee", "No assignee"
# The rows say only who holds each action and how long it has been open: ids, its age, each
# assignee's name, and their company with its logo link. Never what anyone wrote.
FIELDS = ["ticket_id", "site_id", "status_id", "age", "assignees.id", "assignees.firstname", "assignees.lastname",
          "assignees.entity.name", "assignees.entity.logo_url"]


def pulls(ctx):
    return pio.split(ctx, "op/rows.json", len(ctx["sites"]), lambda f, ids: io.gql(
        f, "tickets.tickets", {"type": "escalated", "site_ids": ids, "ticket_archived": False, "limit": PAGE,
                               "status_ids": [1, 3, 7], "priority_ids": PRIORITIES}, FIELDS))


def calls(ctx):
    return pulls(ctx)


def more(ctx, work):
    return pio.pages_due(work, pulls(ctx), PAGE, nested=True)


def link(ctx, site_ids, grouping, assignee_ids=()):
    """PEAK's ticket report on its last 90 days to today at these sites, priority 1 and 2 only,
    grouped by "site" or "assignee", narrowed to these assignees where any are given."""
    params = (["site_ids=%s" % i for i in site_ids]
              + ["relative_date=last_90_days", "include_today=true", "grouping=%s" % grouping]
              + ["priority_ids=%d" % p for p in PRIORITIES] + ["assignee_ids=%s" % a for a in assignee_ids])
    return "%s/reports/tickets?%s" % (pio.host(ctx), "&".join(params))


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
    site = {s["site_id"]: s for s in ctx["sites"]}
    actions = [a for a in pio.held(raw) if a["site"] in site]
    if not actions:
        return {"drop": [NAME], "chat": ["No priority 1 or 2 action is open across the portfolio, so the open "
                                         "P1-2 actions section is left out."]}

    # open actions by age at each site and with each person, the actions no one holds as one more
    site_ages, person_ages = defaultdict(lambda: [0, 0, 0]), defaultdict(lambda: [0, 0, 0])
    sites, who = defaultdict(set), {}
    for act in actions:
        b = age[act["ticket"]]
        site_ages[act["site"]][b] += 1
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

    site_rows = [{"rank": k, "name": site[s]["site_name"].strip(), "state": pio.state(site[s]), "count": on_sites[s],
                  "ages": site_ages[s], "link": link(ctx, [s], "assignee")}
                 for k, s in most_first(on_sites, lambda s: site[s]["site_name"])[:SHOWN]]
    person_rows = []
    for k, p in ranked_people[:SHOWN]:
        row = {"rank": k, "name": label(p), "count": people[p], "ages": person_ages[p], "tile": {}}
        if p != NOBODY:
            co = who[p]["company"]
            row.update(company=co or None, tile={"company": co, "logo": logos.get(co)},
                       link=link(ctx, sorted(sites[p]), "site", [p]))
        person_rows.append(row)

    note = "Priority 1 and 2 actions open as at %s by age open." % io.day_long(ctx["today"])
    month = "%s %d" % (io.month(ctx["today"]), io.d(ctx["today"]).year)
    return {"open_actions": {"panels": [{"title": "Sites", "rows": site_rows},
                                        {"title": "Assignees", "rows": person_rows}]},
            "dated_heads": {"Open P1-2 actions": {"date": month, "note": note}}}
