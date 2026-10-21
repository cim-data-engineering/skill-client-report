#!/usr/bin/env python3
"""Actions resolved by company: the company table and its total row, each company
moving against last month's table. Hands on each site's actions resolved over the
quarter and over the quarter a month earlier as a ranking, each company's as a team
ranking, who holds each action and the company logos. Every count in the site ranking
and the total row is a count_tickets figure; the ticket rows only say who holds each
action. See references/portfolio-leaderboard/actions-and-wins/actions-by-company.md.
"""
import base64
import os
import sys
import urllib.request
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "scripts"))
import peak_io as io  # noqa: E402
import portfolio_io as pio  # noqa: E402

NAME = "actions-by-company"
ANCHOR = "actions-by-company"
STAT4 = ["open", "in_progress", "closed", "on_hold"]           # every status but Not Doing
OPEN = ["open", "in_progress", "on_hold"]
COUNT_CHUNK, PAGE = 20, 1000
# The rows say only who holds each action: ids, each assignee's name, and their company with
# its logo link. Never what anyone wrote.
FIELDS = ["ticket_id", "site_id", "status_id", "assignees.id", "assignees.firstname", "assignees.lastname",
          "assignees.entity.name", "assignees.entity.logo_url"]


def esc(ids):
    return {"type": "escalated", "site_ids": ids, "ticket_archived": False, "limit": PAGE}


def pulls(ctx):
    every = len(ctx["sites"])
    resolved = lambda name, w: pio.split(ctx, name, every, lambda f, ids: io.gql(
        f, "tickets.tickets", dict(esc(ids), resolved_at_local_start=w[0] + "T00:00:00",
                                   resolved_at_local_end=w[1] + "T00:00:00"), FIELDS))
    return (resolved("ar/resolved-rows.json", ctx["quarter"])
            + resolved("ar/resolved-prev-rows.json", ctx["prev_board"])
            + pio.split(ctx, "ar/open-rows.json", every, lambda f, ids: io.gql(
                f, "tickets.tickets", dict(esc(ids), status_ids=[1, 3, 7]), FIELDS)))


def calls(ctx):
    (q0, q1), (p0, p1) = ctx["quarter"], ctx["prev_board"]
    count = lambda name, **kw: pio.split(ctx, name, COUNT_CHUNK, lambda f, ids: io.call(
        f, "count_tickets", site_ids=ids, ticket_types=["escalated"], aggregate_entities=["site"], **kw))
    return (count("ar/resolved.json", statuses=STAT4, local_resolved_start=q0, local_resolved_end=q1)
            + count("ar/resolved-prev.json", statuses=STAT4, local_resolved_start=p0, local_resolved_end=p1)
            + count("ar/open.json", statuses=OPEN)
            + pulls(ctx))


def more(ctx, work):
    return pio.pages_due(work, pulls(ctx), PAGE, nested=True)


def fetch_logos(urls):
    """{company: data URI} for each company logo PEAK links, embedded so the report stays
    one file. A logo that cannot be fetched is left out, and the company's initials stand in."""
    def get(item):
        name, url = item
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "client-report"})
            with urllib.request.urlopen(req, timeout=15) as r:
                kind, body = r.headers.get_content_type(), r.read()
        except OSError:
            return name, None
        if not kind.startswith("image/"):
            return name, None
        return name, "data:%s;base64,%s" % (kind, base64.b64encode(body).decode())
    with ThreadPoolExecutor(8) as pool:
        return dict(pool.map(get, urls.items()))


def counts(work, name):
    out = defaultdict(int)
    for r in pio.rows(work, name):
        if r.get("site_id"):
            out[r["site_id"]] += r.get("ticket_count") or 0
    return out


def held(rows):
    """Who holds each action, Not Doing left out: [{ticket, site, assignees: [{id, name, company}]}]."""
    out = []
    for r in rows:
        if r.get("status_id") == 8:
            continue
        people = []
        for a in r.get("assignees") or []:
            name = " ".join(x for x in ((a.get("firstname") or "").strip(), (a.get("lastname") or "").strip()) if x)
            people.append({"id": a.get("id"), "name": name, "company": ((a.get("entity") or {}).get("name") or "").strip()})
        out.append({"ticket": r["ticket_id"], "site": r["site_id"], "assignees": people})
    return out


def companies_of(action):
    """The companies holding an action: each assignee's company, once. Every assignee counts,
    agents and the client's own managing agents included."""
    out = []
    for a in action["assignees"]:
        if a["company"] and a["company"] not in out:
            out.append(a["company"])
    return out


def companies_by_resolved(held_by):
    """{company: ticket ids} -> the companies, most resolved first, ties alphabetical."""
    return sorted(held_by, key=lambda c: (-len(held_by[c]), c.lower()))


def build(ctx, work, shared):
    resolved, prev, open_now = counts(work, "ar/resolved.json"), counts(work, "ar/resolved-prev.json"), \
        counts(work, "ar/open.json")
    sids = [s["site_id"] for s in ctx["sites"]]
    total_res, total_open = sum(resolved[s] for s in sids), sum(open_now[s] for s in sids)
    if total_res:
        # a site that resolved nothing is not on the board, this month or last
        shared.setdefault("rankings", []).append({"label": "Actions resolved", "anchor": ANCHOR, "window": "quarter",
                                                  "now": {s: resolved[s] or None for s in sids},
                                                  "start": {s: prev[s] or None for s in sids}, "dp": 0,
                                                  "unit": "actions"})
    if not total_res and not total_open:
        return {"drop": [NAME]}

    names = {s["site_id"]: s["site_name"].strip() for s in ctx["sites"]}
    actions = {"resolved": held(pio.rows(work, "ar/resolved-rows.json", PAGE)),
               "prev": held(pio.rows(work, "ar/resolved-prev-rows.json", PAGE)),
               "open": held(pio.rows(work, "ar/open-rows.json", PAGE))}
    co_res, co_open, co_prev, co_people = defaultdict(set), defaultdict(set), defaultdict(set), defaultdict(set)
    site_res, site_open = defaultdict(lambda: defaultdict(int)), defaultdict(lambda: defaultdict(int))
    loose = {"resolved": 0, "open": 0}
    for key, by_co, by_site in (("resolved", co_res, site_res), ("open", co_open, site_open), ("prev", co_prev, None)):
        for act in actions[key]:
            cos = companies_of(act)
            if not cos and key in loose:
                loose[key] += 1
            for co in cos:
                by_co[co].add(act["ticket"])
                if by_site is not None:
                    by_site[co][act["site"]] += 1
            if key != "prev":
                for a in act["assignees"]:
                    if a["id"] and a["company"]:
                        co_people[a["company"]].add(a["id"])
    logo_url = {}
    for f in ("ar/resolved-rows.json", "ar/open-rows.json"):
        for r in pio.rows(work, f, PAGE):
            for a in (r.get("assignees") or []) if r.get("status_id") != 8 else []:
                ent = a.get("entity") or {}
                if ent.get("name") and ent.get("logo_url"):
                    logo_url.setdefault(ent["name"].strip(), ent["logo_url"])

    # Last month's ranking: each company's actions resolved over the quarter a month earlier
    before = {c: k for k, c in enumerate(companies_by_resolved(co_prev), 1)}

    companies = companies_by_resolved({c: co_res[c] for c in set(co_res) | set(co_open)})
    logos = fetch_logos({c: logo_url[c] for c in companies if c in logo_url})
    rows, where = [], {}
    for k, c in enumerate(companies, 1):
        where[c] = set(site_res[c]) | set(site_open[c])
        sites = sorted(where[c], key=lambda s: (-site_open[c][s], -site_res[c][s], names.get(s, "").lower()))
        if not co_res[c]:
            move = None                       # a company that resolved nothing holds no place to move from or to
        elif c in before:
            move = before[c] - k or None
        else:
            move = "new"
        rows.append({"rank": k, "move": move, "company": c, "logo": logos.get(c),
                     "link": pio.tickets_link(ctx, sites, "site", sorted(co_people[c])),
                     "sites": [{"name": names.get(s, str(s)), "open": site_open[c][s]} for s in sites],
                     "resolved": len(co_res[c]), "open": len(co_open[c])})

    link = {"text": "See actions by company", "url": pio.tickets_link(ctx, sids, "user_entity")}
    shared["holders"] = dict(actions, total={"resolved": total_res, "open": total_open})
    shared["logos"] = logos
    if any(co_res.values()):
        every = set(companies) | set(co_prev)
        shared.setdefault("team_rankings", []).append(
            {"label": "Companies", "anchor": ANCHOR, "window": "quarter", "noun": "companies", "unit": "actions", "link": link,
             "names": {c: c for c in every}, "now": {c: len(co_res[c]) or None for c in every},
             "start": {c: len(co_prev[c]) or None for c in every},
             "meta": {c: [pio.site_count(len(where[c]))] for c in companies},
             "tiles": {c: {"company": c, "logo": logos.get(c)} for c in companies}})

    chat = []
    if loose["resolved"] or loose["open"]:
        n = lambda k: "%d action%s" % (k, "" if k == 1 else "s")
        span = "from %s to %s" % (io.month(ctx["quarter_months"][0]), io.month(ctx["quarter_months"][-1]))
        parts = [w % n(loose[k]) for k, w in (("resolved", "%s resolved " + span), ("open", "%s open now")) if loose[k]]
        one = loose["resolved"] + loose["open"] == 1
        chat.append("%s %s no assignee with a company, so %s in the total row and in no company's row."
                    % (io.listing(parts), "has" if one else "have", "it counts" if one else "they count"))
    unlogged = [c for c in companies if not logos.get(c)]
    if unlogged:
        chat.append("Company table initials stand in for %s, with no logo in PEAK or none that could be fetched."
                    % io.listing(unlogged))
    return {
        "companies": {"rows": rows, "total": {"resolved": total_res, "open": total_open}, "link": link},
        "datelines": {"Vendor leaderboard":
                      "Actions resolved %s, ranked by resolved, with moves since %s. Completion rate is resolved "
                      "&divide; (resolved + open now), with open now as at %s. Each company's sites are listed by open "
                      "actions, most first." % (pio.reporting_period(ctx), io.month(ctx["quarter_months"][-2]),
                                                io.day_long(ctx["today"]))},
        "notes": {"Completion rate": {"html": "<strong>Completion rate.</strong> Open now includes actions raised "
                                               "before %s." % io.month(ctx["quarter"][0])}},
        "chat": chat,
    }
