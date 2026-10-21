#!/usr/bin/env python3
"""Actions resolved by assignee: the assignee table and its total row, each person moving
against last month's table, with each person's actions resolved over the quarter and over
the quarter a month earlier handed on as a team ranking. No calls of its own: it counts
from who holds each action, with the actions counted once for the total row, and draws
each company's logo, all handed on, so it builds after the section that hands them on. See
references/portfolio-leaderboard/actions-and-wins/actions-by-assignee.md.
"""
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "scripts"))
import peak_io as io  # noqa: E402
import portfolio_io as pio  # noqa: E402

NAME = "actions-by-assignee"
ANCHOR = "actions-by-assignee"
UNNAMED = "Unnamed assignee"


def calls(ctx):
    return []


def more(ctx, work):
    return []


def build(ctx, work, shared):
    actions = shared.get("holders")
    if not actions or not (actions["resolved"] or actions["open"]):
        return {"drop": [NAME]}
    logos = shared.get("logos") or {}
    names = {s["site_id"]: s["site_name"].strip() for s in ctx["sites"]}
    res, opn, prev = defaultdict(set), defaultdict(set), defaultdict(set)
    site_res, site_open = defaultdict(lambda: defaultdict(int)), defaultdict(lambda: defaultdict(int))
    who = {}             # each person's name and company: the quarter's, else open now's, else a month earlier's
    for key, by, by_site in (("resolved", res, site_res), ("open", opn, site_open), ("prev", prev, None)):
        for act in actions[key]:
            for a in act["assignees"]:
                pid = a["id"]
                if not pid or act["ticket"] in by[pid]:
                    continue
                who.setdefault(pid, a)
                by[pid].add(act["ticket"])
                if by_site is not None:
                    by_site[pid][act["site"]] += 1
    label = lambda p: who[p]["name"] or UNNAMED
    # the same order the team board ranks on: most resolved first, ties alphabetical by name
    order = lambda held: sorted(held, key=lambda p: (-len(held[p]), label(p).strip().lower(), str(p)))
    before = {p: k for k, p in enumerate(order(prev), 1)}

    rows, where = [], {}
    for k, p in enumerate(order({p: res[p] for p in set(res) | set(opn)}), 1):
        where[p] = set(site_res[p]) | set(site_open[p])
        sites = sorted(where[p], key=lambda s: (-site_open[p][s], -site_res[p][s], names.get(s, "").lower()))
        if not res[p]:
            move = None                       # a person who resolved nothing holds no place to move from or to
        elif p in before:
            move = before[p] - k or None
        else:
            move = "new"
        co = who[p]["company"]
        rows.append({"rank": k, "move": move, "name": label(p), "company": co or None, "logo": logos.get(co),
                     "link": pio.tickets_link(ctx, sites, "user_entity", [p]),
                     "sites": [{"name": names.get(s, str(s)), "open": site_open[p][s]} for s in sites],
                     "resolved": len(res[p]), "open": len(opn[p])})

    link = {"text": "See actions by assignee", "url": pio.tickets_link(ctx, pio.ids(ctx), "assignee")}
    if any(res.values()):
        every = set(where) | set(prev)
        shared.setdefault("team_rankings", []).append(
            {"label": "Assignees", "anchor": ANCHOR, "window": "quarter", "noun": "assignees", "unit": "actions", "link": link,
             "names": {p: label(p) for p in every}, "now": {p: len(res[p]) or None for p in every},
             "start": {p: len(prev[p]) or None for p in every},
             "meta": {p: [x for x in (who[p]["company"], pio.site_count(len(where[p]))) if x] for p in where},
             "tiles": {p: {"company": who[p]["company"], "logo": logos.get(who[p]["company"])} for p in where}})

    return {
        "assignees": {"rows": rows, "total": actions["total"], "link": link},
        "datelines": {"Assignee leaderboard":
                      "Actions resolved %s, ranked by resolved, with moves since %s. Completion rate is resolved "
                      "&divide; (resolved + open now), with open now as at %s. Under each name, the assignee's company, "
                      "then their sites by open actions, most first." % (pio.reporting_period(ctx),
                                                                          io.month(ctx["quarter_months"][-2]),
                                                                          io.day_long(ctx["today"]))},
        "notes": {"Completion rate": {"html": "<strong>Completion rate.</strong> Open now includes actions raised "
                                               "before %s." % io.month(ctx["quarter"][0])}},
    }
