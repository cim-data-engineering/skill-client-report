#!/usr/bin/env python3
"""Actions resolved: the counts and ticket pulls behind the actions rankings, with no part of
its own. Hands on each site's actions resolved over the quarter and over the quarter a month
earlier as a ranking, and each company's and each person's as team rankings, every name with
its PEAK ticket report. An action counts only for its assignees outside CIM who commented on it,
and for its site when any of them did: the ticket rows say who holds each action and who commented,
so every figure is counted from them, and a count by assignee names them. See
references/portfolio-leaderboard/actions-and-wins/actions-resolved.md.
"""
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "scripts"))
import peak_io as io  # noqa: E402
import portfolio_io as pio  # noqa: E402

STAT4 = ["open", "in_progress", "closed", "on_hold"]           # every status but Not Doing
COUNT_CHUNK, PAGE, COMMENTS = 20, 1000, 100      # COMMENTS: comments read per action, newest first
CIM = 1                                           # CIM's company id in PEAK: its people are never ranked
UNNAMED = "Unnamed assignee"
NOTE = "A resolved action only counts for rankings if the assignee commented on it."
# The rows say only who holds each action and who commented on it: ids, each assignee's company with its
# id and logo link, and each comment's author. PEAK refuses the whole pull when any assignee has no name or
# email recorded, so names come from a count by assignee, which leaves such a name empty, and the leader's
# first name and email from one ticket of theirs whose assignees all have names. Never what anyone wrote.
FIELDS = ["ticket_id", "site_id", "status_id", "assignees.id", "assignees.entity.id", "assignees.entity.name",
          "assignees.entity.logo_url",
          {"path": "comments", "args": {"user_only": True, "limit": COMMENTS}, "sub_fields": ["author_id"]}]
LEADER = ["ticket_id", "assignees.id", "assignees.firstname", "assignees.email"]


def pulls(ctx):
    # has_comments: an action nobody commented on can never count
    resolved = lambda name, w: pio.split(ctx, name, len(ctx["sites"]), lambda f, ids: io.gql(
        f, "tickets.tickets", {"type": "escalated", "site_ids": ids, "ticket_archived": False, "has_comments": True,
                               "limit": PAGE, "resolved_at_local_start": w[0] + "T00:00:00",
                               "resolved_at_local_end": w[1] + "T00:00:00"}, FIELDS))
    return resolved("ar/resolved-rows.json", ctx["quarter"]) + resolved("ar/resolved-prev-rows.json", ctx["prev_board"])


def calls(ctx):
    (q0, q1), (p0, p1) = ctx["quarter"], ctx["prev_board"]
    count = lambda name, w0, w1, by: pio.split(ctx, name, COUNT_CHUNK, lambda f, ids: io.call(
        f, "count_tickets", site_ids=ids, ticket_types=["escalated"], aggregate_entities=[by], statuses=STAT4,
        local_resolved_start=w0, local_resolved_end=w1))
    return (count("ar/assignees.json", q0, q1, "assignee") + count("ar/assignees-prev.json", p0, p1, "assignee")
            + pulls(ctx))


def more(ctx, work):
    due = io.pages_due(work, pulls(ctx))
    if due or work.has("ar/leader.json"):
        return due
    # the Assignees leader's first name and email, for the shoutout: one ticket of theirs whose assignees
    # all have names, since one without fails the pull
    p = people(ctx, work)
    if not p["now"]:
        return []
    ranked, _ = pio.standings(list(p["every"]), p["now"], p["then"], p["label"])
    lead = ranked[0][1]
    named = [act for act in p["acts"] if lead in {a["id"] for a in act["assignees"]}
             and all(p["names"].get(a["id"]) for a in act["holders"] if a["id"])]
    if not named:
        return []
    act = named[0]
    return [dict(io.gql("ar/leader.json", "tickets.tickets", {"type": "escalated", "site_ids": [act["site"]],
                                                              "ticket_ids": [act["ticket"]], "ticket_archived": False,
                                                              "limit": 1}, LEADER), optional=True)]


def commented(rows, nm):
    """held() actions keeping, as their assignees, only the people outside CIM who commented on each, CIM's
    system accounts and agents never; an action left with none is dropped. holders keeps every assignee."""
    authors = {r["ticket_id"]: {c.get("author_id") for c in r.get("comments") or []} for r in rows}
    out = []
    for act in pio.held(rows):
        act["holders"] = act["assignees"]
        act["assignees"] = [a for a in act["holders"]
                            if a["id"] and a["id"] in authors[act["ticket"]] and a["company_id"] != CIM
                            and not io.system_account(a["id"], nm.get(a["id"]))]
        if act["assignees"]:
            out.append(act)
    return out


def per_site(actions):
    out = defaultdict(int)
    for act in actions:
        out[act["site"]] += 1
    return out


def names(work):
    """{user id: name} off the counts by assignee, the quarter's over last month's board's; an empty name
    where PEAK holds none."""
    out = {}
    for name in ("ar/assignees-prev.json", "ar/assignees.json"):
        for r in pio.rows(work, name):
            if r.get("assignee_id"):
                out[r["assignee_id"]] = (r.get("assignee_name") or "").strip()
    return out


def tally(actions, key):
    """{holder: ticket ids} and {holder: {site: actions}} for holders keyed by key(assignee), each action once
    a holder."""
    tickets, sites = defaultdict(set), defaultdict(lambda: defaultdict(int))
    for act in actions:
        for k in {key(a) for a in act["assignees"]} - {None, ""}:
            tickets[k].add(act["ticket"])
            sites[k][act["site"]] += 1
    return dict(tickets), sites


def people(ctx, work):
    """Who resolved what, the quarter and last month's board: each person's commented actions, sites and
    company, CIM and accounts PEAK holds no name or company for left out of the ranking."""
    nm = names(work)
    now = commented(pio.rows(work, "ar/resolved-rows.json"), nm)
    then = commented(pio.rows(work, "ar/resolved-prev-rows.json"), nm)
    who, blank = {}, defaultdict(set)
    for act in then + now:                # each person's name and company as the quarter shows them
        for a in act["assignees"]:
            if a["id"]:
                a["name"] = nm.get(a["id"]) or ""
                who[a["id"]] = a
    for acts, mark in ((then, False), (now, True)):        # a quarter ticket marks the count the chat gives
        for act in acts:
            for a in act["assignees"]:
                if a["id"] and not a["name"] and not a["company"]:
                    blank[a["id"]].add(act["ticket"] if mark else None)
    ranks = lambda a: bool(a["id"]) and not io.system_account(a["id"], a["name"]) and a["id"] not in blank
    key = lambda a: a["id"] if ranks(a) else None
    p_now, p_sites = tally(now, key)
    p_then, _ = tally(then, key)
    every = set(p_now) | set(p_then)
    return {"names": nm, "who": who, "acts": now, "then_acts": then, "blank": blank, "ranks": ranks,
            "every": every, "sites": p_sites,
            "now": {p: len(p_now.get(p, ())) or None for p in every},
            "then": {p: len(p_then.get(p, ())) or None for p in every},
            "label": lambda p: who[p]["name"] or UNNAMED}


def tickets_link(ctx, site_ids, grouping, assignee_ids=()):
    """PEAK's ticket report over the quarter at these sites, grouped by "site", "user_entity" (the
    assignee's company) or "assignee", and narrowed to these assignees where any are given."""
    params = (["site_ids=%s" % i for i in site_ids]
              + ["start_date=%sT00:00:00.000" % ctx["quarter"][0], "end_date=%sT00:00:00.000" % ctx["through"],
                 "grouping=%s" % grouping]
              + ["assignee_ids=%s" % a for a in assignee_ids])
    return "%s/reports/tickets?%s" % (io.host(*ctx["sites"]), "&".join(params))


def where(at, site_name):
    """A leader's meta: the site they resolved the most at, ties alphabetical, then '+ N sites' for the rest."""
    top = min(at, key=lambda s: (-at[s], site_name[s].lower()))
    return site_name[top] + (" + %s" % io.plural(len(at) - 1, "site") if len(at) > 1 else "")


def leader_contact(work):
    """{id: (first name, email)} off the leader pull, empty when it was not made or PEAK refused it."""
    got = work.get("ar/leader.json", optional=True) if work.has("ar/leader.json") else None
    return {a.get("id"): ((a.get("firstname") or "").strip(), (a.get("email") or "").strip())
            for r in (got.rows if got else []) for a in r.get("assignees") or [] if a.get("id")}


def build(ctx, work, shared):
    p = people(ctx, work)
    now, then, who, ranks = p["acts"], p["then_acts"], p["who"], p["ranks"]
    resolved, prev = per_site(now), per_site(then)
    sids = pio.ids(ctx)
    if not any(resolved[s] for s in sids):
        return {}                         # nothing counts in the quarter: no ranking to hand on
    pio.shown(shared, [s for s in sids if resolved[s]])
    # a site that resolved nothing is not on the board, this month or last
    shared.setdefault("rankings", []).append({
        "label": "Actions resolved", "window": "quarter", "dp": 0, "unit": "actions", "note": NOTE,
        "now": {s: resolved[s] or None for s in sids}, "start": {s: prev[s] or None for s in sids},
        "links": {s: tickets_link(ctx, [s], "assignee") for s in sids}})

    logos = io.fetch_logos(pio.logo_links(now))
    site_name = {s["site_id"]: s["site_name"].strip() for s in ctx["sites"]}

    # companies: each company's actions resolved by its people who commented, CIM left out, its sites,
    # and its people for its PEAK link
    co_key = lambda a: a["company"] if ranks(a) else None
    co_now, co_sites = tally(now, co_key)
    co_then, _ = tally(then, co_key)
    co_people = defaultdict(set)
    for act in now:
        for a in act["assignees"]:
            if co_key(a):
                co_people[a["company"]].add(a["id"])
    every = set(co_now) | set(co_then)
    shared.setdefault("team_rankings", []).append({
        "label": "Companies", "noun": "companies", "window": "quarter", "unit": "actions", "note": NOTE,
        "names": {c: c for c in every}, "now": {c: len(co_now.get(c, ())) or None for c in every},
        "start": {c: len(co_then.get(c, ())) or None for c in every},
        "meta": {c: [where(co_sites[c], site_name)] for c in co_now},
        "tiles": {c: {"company": c, "logo": logos.get(c)} for c in co_now},
        "links": {c: tickets_link(ctx, sorted(co_sites[c]), "site", sorted(co_people[c])) for c in co_now}})

    # people: each assignee's actions resolved and their sites
    contact = leader_contact(work)
    p_now = {k: v for k, v in p["now"].items() if v}
    shared.setdefault("team_rankings", []).append({
        "label": "Assignees", "noun": "assignees", "window": "quarter", "unit": "actions", "note": NOTE,
        "names": {k: p["label"](k) for k in p["every"]}, "now": p["now"], "start": p["then"],
        "meta": {k: [x for x in (who[k]["company"], where(p["sites"][k], site_name)) if x] for k in p_now},
        "tiles": {k: {"company": who[k]["company"], "logo": logos.get(who[k]["company"])} for k in p_now},
        "links": {k: tickets_link(ctx, sorted(p["sites"][k]), "user_entity", [k]) for k in p_now},
        "shoutouts": {k: {"first": contact[k][0], "email": contact[k][1],
                          "site": site_name[min(p["sites"][k], key=lambda s: (-p["sites"][k][s], site_name[s].lower()))]}
                      for k in p_now if k in contact and all(contact[k])}})

    chat = []
    unlogged = sorted(c for c in co_now if not logos.get(c))
    if unlogged:
        chat.append("Initials stand in for the logos of %s, with none in PEAK or none that could be fetched."
                    % io.listing(unlogged))
    for uid, held in sorted(((u, t - {None}) for u, t in p["blank"].items()), key=lambda x: -len(x[1])):
        if not held:
            continue
        chat.append("PEAK holds no name, email or company for the user %s, who resolved %d of the quarter's actions: "
                    "counted on the site board, left off the team boards. Ask ops to name the account in PEAK."
                    % (uid, len(held)))
    return {"chat": chat}
