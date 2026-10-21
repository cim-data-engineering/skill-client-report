#!/usr/bin/env python3
"""Actions resolved: the counts and ticket pulls behind the actions rankings, with no part of
its own. Hands on each site's actions resolved over the quarter and over the quarter a month
earlier as a ranking, and each company's and each person's as team rankings, every name with
its PEAK ticket report. Every site figure is a count_tickets count; the ticket rows say who
holds each action. See references/portfolio-leaderboard/actions-and-wins/actions-resolved.md.
"""
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "scripts"))
import peak_io as io  # noqa: E402
import portfolio_io as pio  # noqa: E402

NAME = "actions-resolved"
STAT4 = ["open", "in_progress", "closed", "on_hold"]           # every status but Not Doing
COUNT_CHUNK, PAGE = 20, 1000
UNNAMED = "Unnamed assignee"
# The rows say only who holds each action: ids, each assignee's name and email, and their company
# with its logo link. Never what anyone wrote.
FIELDS = ["ticket_id", "site_id", "status_id", "assignees.id", "assignees.firstname", "assignees.lastname",
          "assignees.email", "assignees.entity.name", "assignees.entity.logo_url"]


def pulls(ctx):
    resolved = lambda name, w: pio.split(ctx, name, len(ctx["sites"]), lambda f, ids: io.gql(
        f, "tickets.tickets", {"type": "escalated", "site_ids": ids, "ticket_archived": False, "limit": PAGE,
                               "resolved_at_local_start": w[0] + "T00:00:00",
                               "resolved_at_local_end": w[1] + "T00:00:00"}, FIELDS))
    return resolved("ar/resolved-rows.json", ctx["quarter"]) + resolved("ar/resolved-prev-rows.json", ctx["prev_board"])


def calls(ctx):
    (q0, q1), (p0, p1) = ctx["quarter"], ctx["prev_board"]
    count = lambda name, w0, w1: pio.split(ctx, name, COUNT_CHUNK, lambda f, ids: io.call(
        f, "count_tickets", site_ids=ids, ticket_types=["escalated"], aggregate_entities=["site"], statuses=STAT4,
        local_resolved_start=w0, local_resolved_end=w1))
    return count("ar/resolved.json", q0, q1) + count("ar/resolved-prev.json", p0, p1) + pulls(ctx)


def more(ctx, work):
    return pio.pages_due(work, pulls(ctx), PAGE, nested=True)


def counts(work, name):
    out = defaultdict(int)
    for r in pio.rows(work, name):
        if r.get("site_id"):
            out[r["site_id"]] += r.get("ticket_count") or 0
    return out


def tally(actions, key):
    """{holder: ticket ids} and {holder: site ids} for holders keyed by key(assignee), each action once a holder."""
    tickets, sites = defaultdict(set), defaultdict(set)
    for act in actions:
        for a in act["assignees"]:
            k = key(a)
            if k:
                tickets[k].add(act["ticket"])
                sites[k].add(act["site"])
    return dict(tickets), dict(sites)


def build(ctx, work, shared):
    resolved, prev = counts(work, "ar/resolved.json"), counts(work, "ar/resolved-prev.json")
    sids = pio.ids(ctx)
    if not any(resolved[s] for s in sids):
        return {}                         # nothing resolved in the quarter: no ranking to hand on
    # a site that resolved nothing is not on the board, this month or last
    shared.setdefault("rankings", []).append({
        "label": "Actions resolved", "window": "quarter", "dp": 0, "unit": "actions",
        "now": {s: resolved[s] or None for s in sids}, "start": {s: prev[s] or None for s in sids},
        "links": {s: pio.tickets_link(ctx, [s], "assignee") for s in sids}})

    now = pio.held(pio.rows(work, "ar/resolved-rows.json", PAGE))
    then = pio.held(pio.rows(work, "ar/resolved-prev-rows.json", PAGE))
    logos = pio.fetch_logos(pio.logo_links(now))
    who = {}
    for act in then + now:                # each person's name and company as the quarter shows them
        for a in act["assignees"]:
            if a["id"]:
                who[a["id"]] = a

    # companies: each company's actions resolved, its sites, and its people for its PEAK link
    co_now, co_sites = tally(now, lambda a: a["company"])
    co_then, _ = tally(then, lambda a: a["company"])
    co_people = defaultdict(set)
    for act in now:
        for a in act["assignees"]:
            if a["company"] and a["id"]:
                co_people[a["company"]].add(a["id"])
    every = set(co_now) | set(co_then)
    shared.setdefault("team_rankings", []).append({
        "label": "Companies", "noun": "companies", "window": "quarter", "unit": "actions",
        "names": {c: c for c in every}, "now": {c: len(co_now.get(c, ())) or None for c in every},
        "start": {c: len(co_then.get(c, ())) or None for c in every},
        "meta": {c: [pio.site_count(len(co_sites[c]))] for c in co_now},
        "tiles": {c: {"company": c, "logo": logos.get(c)} for c in co_now},
        "links": {c: pio.tickets_link(ctx, sorted(co_sites[c]), "site", sorted(co_people[c])) for c in co_now}})

    # people: each assignee's actions resolved and their sites
    p_now, p_sites = tally(now, lambda a: a["id"])
    p_then, _ = tally(then, lambda a: a["id"])
    label = lambda p: who[p]["name"] or UNNAMED
    # each person's busiest site, where they resolved the most, ties alphabetical: for their shoutout
    site_name = {s["site_id"]: s["site_name"].strip() for s in ctx["sites"]}
    at = defaultdict(lambda: defaultdict(int))
    for act in now:
        for p in {a["id"] for a in act["assignees"] if a["id"]}:
            at[p][act["site"]] += 1
    busiest = lambda p: site_name[min(at[p], key=lambda s: (-at[p][s], site_name[s].lower()))]
    every = set(p_now) | set(p_then)
    shared.setdefault("team_rankings", []).append({
        "label": "Assignees", "noun": "assignees", "window": "quarter", "unit": "actions",
        "names": {p: label(p) for p in every}, "now": {p: len(p_now.get(p, ())) or None for p in every},
        "start": {p: len(p_then.get(p, ())) or None for p in every},
        "meta": {p: [x for x in (who[p]["company"], pio.site_count(len(p_sites[p]))) if x] for p in p_now},
        "tiles": {p: {"company": who[p]["company"], "logo": logos.get(who[p]["company"])} for p in p_now},
        "links": {p: pio.tickets_link(ctx, sorted(p_sites[p]), "user_entity", [p]) for p in p_now},
        "shoutouts": {p: {"first": who[p]["first"], "email": who[p]["email"], "site": busiest(p)}
                      for p in p_now if who[p]["first"] and who[p]["email"]}})

    unlogged = sorted(c for c in co_now if not logos.get(c))
    chat = ["Initials stand in for the logos of %s, with none in PEAK or none that could be fetched."
            % io.listing(unlogged)] if unlogged else []
    return {"chat": chat}
