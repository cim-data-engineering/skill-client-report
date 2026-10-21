#!/usr/bin/env python3
"""Actions resolved: the ticket pulls behind the actions rankings, with no part of its own. Hands
on each site's actions resolved over the quarter and over the quarter a month earlier as a
ranking, and each company's and each person's as team rankings, every name with its PEAK ticket
report. Every figure counts the action rows that count, closed with the work rather than closed
out with no word from anyone; the rows say who holds each action, and a count by assignee names
them. See references/portfolio-leaderboard/actions-and-wins/actions-resolved.md.
"""
import json
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "scripts"))
import peak_io as io  # noqa: E402
import portfolio_io as pio  # noqa: E402

NAME = "actions-resolved"
STAT4 = ["open", "in_progress", "closed", "on_hold"]           # every status but Not Doing
COUNT_CHUNK, PAGE = 20, 1000
UNNAMED = "Unnamed assignee"
ONE_STEP = 1           # seconds: an action created closed is stamped resolved the instant it was created
CLOSE_GAP = 5          # seconds: the change that closed an action is stamped within this of its resolved_at
HISTORY = 3            # an action's latest changes: the close is nearly always the latest, and among these
# The rows say only who holds each action: ids, and each assignee's company with its logo link. PEAK
# refuses the whole pull when any assignee has no name or email recorded, so names come from a count by
# assignee, which leaves such a name empty, and the leader's first name and email from one ticket of
# theirs whose assignees all have names. To tell whether each action counts, they also say when it was
# created and resolved, who commented on it and who made its latest changes, by id and name, and each
# linked alert's fault status and when that last changed. Never what anyone wrote.
FIELDS = ["ticket_id", "site_id", "status_id", "created_at", "resolved_at",
          "assignees.id", "assignees.entity.name", "assignees.entity.logo_url",
          {"path": "comments", "args": {"user_only": True}, "sub_fields": ["author_id", "author_full_name"]},
          {"path": "change_history", "args": {"limit": HISTORY, "sort_order": "DESC"},
           "sub_fields": ["author_id", "author_full_name", "ts"]},
          {"path": "ticket_links", "sub_fields": [{"path": "ticket", "sub_fields": [
              "type", "fault_status", "last_fault_transitioned_at"]}]}]
LEADER = ["ticket_id", "assignees.id", "assignees.firstname", "assignees.email"]
WHY = {"recovered": "%d created and closed in one step with every alert already recovered",
       "in fault": "%d closed by a person while every alert was in fault, and still is"}


def pulls(ctx):
    resolved = lambda name, w: pio.split(ctx, name, len(ctx["sites"]), lambda f, ids: io.gql(
        f, "tickets.tickets", {"type": "escalated", "site_ids": ids, "ticket_archived": False, "limit": PAGE,
                               "resolved_at_local_start": w[0] + "T00:00:00",
                               "resolved_at_local_end": w[1] + "T00:00:00"}, FIELDS))
    return resolved("ar/resolved-rows.json", ctx["quarter"]) + resolved("ar/resolved-prev-rows.json", ctx["prev_board"])


def calls(ctx):
    (q0, q1), (p0, p1) = ctx["quarter"], ctx["prev_board"]
    count = lambda name, w0, w1: pio.split(ctx, name, COUNT_CHUNK, lambda f, ids: io.call(
        f, "count_tickets", site_ids=ids, ticket_types=["escalated"], aggregate_entities=["assignee"],
        statuses=STAT4, local_resolved_start=w0, local_resolved_end=w1))
    return count("ar/assignees.json", q0, q1) + count("ar/assignees-prev.json", p0, p1) + pulls(ctx)


def more(ctx, work):
    due = pio.pages_due(work, pulls(ctx), PAGE, nested=True)
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
             and all(p["names"].get(a["id"]) for a in act["assignees"] if a["id"])]
    if not named:
        return []
    act = named[0]
    return [io.gql("ar/leader.json", "tickets.tickets", {"type": "escalated", "site_ids": [act["site"]],
                                                         "ticket_ids": [act["ticket"]], "ticket_archived": False,
                                                         "limit": 1}, LEADER)]


def when(ts):
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def person(user_id, name):
    """True for a person: not CIM's system accounts or agents, nor PEAK's system user, which carries no
    id and no name. A comment left without signing in carries a name alone: a person's."""
    return bool(user_id or name) and not io.system_account(user_id, name)


def closer(r):
    """The change that closed the action: of its latest changes, the one stamped nearest its resolved_at,
    within CLOSE_GAP; None where none is. An action created closed has its creation alone."""
    t = when(r["resolved_at"])
    near = [(abs((when(c["ts"]) - t).total_seconds()), c) for c in r.get("change_history") or [] if c.get("ts")]
    near = [x for x in near if x[0] <= CLOSE_GAP]
    return min(near, key=lambda x: x[0])[1] if near else None


def left_out(r):
    """Why a resolved action counts on no ranking, or None where it counts. Only where no person
    commented on it and a person closed it, or no close shows in its latest changes:
        recovered   created and closed in one step, every linked alert already recovered
        in fault    every linked alert in fault at the close and still in fault
    An alert's state at the close is its fault status now where that has not changed since: one that
    changed after the close is in neither state, so the action counts. So does one with no alert, and
    every close by an agent, Agent Hannah's, credited to the assignees."""
    if any(person(c.get("author_id"), c.get("author_full_name")) for c in r.get("comments") or []):
        return None
    c = closer(r)
    if c and not person(c.get("author_id"), c.get("author_full_name")):
        return None
    closed = when(r["resolved_at"])
    alerts = [l["ticket"] for l in r.get("ticket_links") or [] if (l.get("ticket") or {}).get("type") == "alert"]
    state = {a.get("fault_status") if not a.get("last_fault_transitioned_at")
             or when(a["last_fault_transitioned_at"]) <= closed else None for a in alerts}
    if state == {"recovered"} and (closed - when(r["created_at"])).total_seconds() < ONE_STEP:
        return "recovered"
    return "in fault" if state == {"fault"} else None


def screened(work, name):
    """The actions resolved in a window that count, as pio.held gives them, and {why: actions} for those
    left out per left_out."""
    keep, out = [], Counter()
    for r in pio.rows(work, name, PAGE):
        why = left_out(r) if r.get("status_id") != 8 else None
        if why:
            out[why] += 1
        else:
            keep.append(r)
    return pio.held(keep), out


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
    """Who resolved what, the quarter and last month's board, over the actions that count: each person's
    actions, sites and company, CIM's system accounts and accounts PEAK holds no name or company for left
    out of the ranking."""
    nm = names(work)
    now, out = screened(work, "ar/resolved-rows.json")
    then, _ = screened(work, "ar/resolved-prev-rows.json")
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
    return {"names": nm, "who": who, "acts": now, "then_acts": then, "out": out, "blank": blank, "ranks": ranks,
            "every": every, "sites": p_sites,
            "now": {p: len(p_now.get(p, ())) or None for p in every},
            "then": {p: len(p_then.get(p, ())) or None for p in every},
            "label": lambda p: who[p]["name"] or UNNAMED}


def where(at, site_name):
    """A leader's meta: the site they resolved the most at, ties alphabetical, then '+ N sites' for the rest."""
    top = min(at, key=lambda s: (-at[s], site_name[s].lower()))
    return site_name[top] + (" + %s" % pio.site_count(len(at) - 1) if len(at) > 1 else "")


def leader_contact(work):
    """{id: (first name, email)} off the leader pull, empty when it was not made or PEAK refused it."""
    if not work.has("ar/leader.json"):
        return {}
    try:
        with open(work.path("ar/leader.json"), encoding="utf-8") as fh:
            rows = io.Response(json.load(fh)).rows
    except ValueError:
        return {}
    return {a.get("id"): ((a.get("firstname") or "").strip(), (a.get("email") or "").strip())
            for r in rows for a in r.get("assignees") or [] if a.get("id")}


def build(ctx, work, shared):
    p = people(ctx, work)
    now, then, who, ranks = p["acts"], p["then_acts"], p["who"], p["ranks"]
    resolved, prev = Counter(act["site"] for act in now), Counter(act["site"] for act in then)
    sids = pio.ids(ctx)
    if not any(resolved[s] for s in sids):
        return {}                         # nothing resolved in the quarter that counts: no ranking to hand on
    pio.shown(shared, [s for s in sids if resolved[s]])
    # a site that resolved nothing is not on the board, this month or last; every action that counts
    # counts here, whoever closed it
    shared.setdefault("rankings", []).append({
        "label": "Actions resolved", "window": "quarter", "dp": 0, "unit": "actions",
        "now": {s: resolved[s] or None for s in sids}, "start": {s: prev[s] or None for s in sids},
        "links": {s: pio.tickets_link(ctx, [s], "assignee") for s in sids}})
    logos = pio.fetch_logos(pio.logo_links(now))
    site_name = {s["site_id"]: s["site_name"].strip() for s in ctx["sites"]}

    # companies: each company's actions resolved by its people, CIM's system accounts left out, its sites,
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
        "label": "Companies", "noun": "companies", "window": "quarter", "unit": "actions",
        "names": {c: c for c in every}, "now": {c: len(co_now.get(c, ())) or None for c in every},
        "start": {c: len(co_then.get(c, ())) or None for c in every},
        "meta": {c: [where(co_sites[c], site_name)] for c in co_now},
        "tiles": {c: {"company": c, "logo": logos.get(c)} for c in co_now},
        "links": {c: pio.tickets_link(ctx, sorted(co_sites[c]), "site", sorted(co_people[c])) for c in co_now}})

    # people: each assignee's actions resolved and their sites
    contact = leader_contact(work)
    p_now = {k: v for k, v in p["now"].items() if v}
    shared.setdefault("team_rankings", []).append({
        "label": "Assignees", "noun": "assignees", "window": "quarter", "unit": "actions",
        "names": {k: p["label"](k) for k in p["every"]}, "now": p["now"], "start": p["then"],
        "meta": {k: [x for x in (who[k]["company"], where(p["sites"][k], site_name)) if x] for k in p_now},
        "tiles": {k: {"company": who[k]["company"], "logo": logos.get(who[k]["company"])} for k in p_now},
        "links": {k: pio.tickets_link(ctx, sorted(p["sites"][k]), "user_entity", [k]) for k in p_now},
        "shoutouts": {k: {"first": contact[k][0], "email": contact[k][1],
                          "site": site_name[min(p["sites"][k], key=lambda s: (-p["sites"][k][s], site_name[s].lower()))]}
                      for k in p_now if k in contact and all(contact[k])}})

    chat = []
    if p["out"]:
        n = sum(p["out"].values())
        chat.append("Left out of the actions resolved boards: %d of the quarter's %d resolved actions, %s, none with a "
                    "comment from a person. So a board's figure can sit below the PEAK report its name opens."
                    % (n, n + len(now), io.listing(WHY[k] % p["out"][k] for k in WHY if p["out"][k])))
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
