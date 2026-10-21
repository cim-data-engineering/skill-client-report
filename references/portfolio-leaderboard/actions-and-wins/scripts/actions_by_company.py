#!/usr/bin/env python3
"""Actions resolved by company: the company table and its total row, with each site's
actions resolved this quarter and last handed on as a ranking. Every count in the
ranking and the total row is a count_tickets figure; the ticket rows only say
which company holds each action. See
references/portfolio-leaderboard/actions-and-wins/actions-by-company.md.
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
# The rows say only who holds each action: ids, and each assignee's company with its logo
# link. Never what anyone wrote.
FIELDS = ["ticket_id", "site_id", "status_id", "assignees.id", "assignees.entity.name", "assignees.entity.logo_url"]


def esc(ids):
    return {"type": "escalated", "site_ids": ids, "ticket_archived": False, "limit": PAGE}


def pulls(ctx):
    q0, q1 = ctx["quarter"]
    every = len(ctx["sites"])
    return (pio.split(ctx, "ar/resolved-rows.json", every, lambda f, ids: io.gql(
                f, "tickets.tickets", dict(esc(ids), resolved_at_local_start=q0 + "T00:00:00",
                                           resolved_at_local_end=q1 + "T00:00:00"), FIELDS))
            + pio.split(ctx, "ar/open-rows.json", every, lambda f, ids: io.gql(
                f, "tickets.tickets", dict(esc(ids), status_ids=[1, 3, 7]), FIELDS)))


def calls(ctx):
    (q0, q1), (p0, p1) = ctx["quarter"], ctx["prev_quarter"]
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


def holders(r):
    """The companies holding an action: each assignee's company, once. Every assignee counts,
    agents and the client's own managing agents included."""
    out = []
    for a in r.get("assignees") or []:
        co = ((a.get("entity") or {}).get("name") or "").strip()
        if co and co not in out:
            out.append(co)
    return out


def build(ctx, work, shared):
    resolved, prev, open_now = counts(work, "ar/resolved.json"), counts(work, "ar/resolved-prev.json"), \
        counts(work, "ar/open.json")
    sids = [s["site_id"] for s in ctx["sites"]]
    total_res, total_open = sum(resolved[s] for s in sids), sum(open_now[s] for s in sids)
    if sum(resolved[s] for s in sids):
        shared.setdefault("rankings", []).append({"label": "Actions resolved", "anchor": ANCHOR, "window": "quarters",
                                                  "now": {s: resolved[s] for s in sids},
                                                  "start": {s: prev[s] for s in sids}, "dp": 0})
    if not total_res and not total_open:
        return {"drop": [NAME]}
    shared.setdefault("partial", []).append("Actions resolved this quarter")

    names = {s["site_id"]: s["site_name"].strip() for s in ctx["sites"]}
    co_res, co_open, logo_url = defaultdict(set), defaultdict(set), {}
    site_res, site_open = defaultdict(lambda: defaultdict(int)), defaultdict(lambda: defaultdict(int))
    loose = {"resolved": 0, "open": 0}
    for key, rows in (("resolved", pio.rows(work, "ar/resolved-rows.json", PAGE)),
                      ("open", pio.rows(work, "ar/open-rows.json", PAGE))):
        for r in rows:
            if r.get("status_id") == 8:
                continue
            cos = holders(r)
            if not cos:
                loose[key] += 1
            for co in cos:
                (co_res if key == "resolved" else co_open)[co].add(r["ticket_id"])
                (site_res if key == "resolved" else site_open)[co][r["site_id"]] += 1
            for a in r.get("assignees") or []:
                ent = a.get("entity") or {}
                if ent.get("name") and ent.get("logo_url"):
                    logo_url.setdefault(ent["name"].strip(), ent["logo_url"])

    companies = sorted(set(co_res) | set(co_open), key=lambda c: (-len(co_res[c]), c.lower()))
    logos = fetch_logos({c: logo_url[c] for c in companies if c in logo_url})
    rows = []
    for k, c in enumerate(companies, 1):
        where = set(site_res[c]) | set(site_open[c])
        sites = sorted(where, key=lambda s: (-site_open[c][s], -site_res[c][s], names.get(s, "").lower()))
        rows.append({"rank": k, "company": c, "logo": logos.get(c),
                     "sites": [{"name": names.get(s, str(s)), "open": site_open[c][s]} for s in sites],
                     "resolved": len(co_res[c]), "open": len(co_open[c])})

    chat = []
    if loose["resolved"] or loose["open"]:
        chat.append("%d actions resolved this quarter and %d open now have no assignee with a company, so they count "
                    "in the total row and in no company's row." % (loose["resolved"], loose["open"]))
    unlogged = [c for c in companies if not logos.get(c)]
    if unlogged:
        chat.append("Company table initials stand in for %s, with no logo in PEAK or none that could be fetched."
                    % io.listing(unlogged))
    return {
        "companies": {"rows": rows, "total": {"resolved": total_res, "open": total_open}},
        "datelines": {"Vendor leaderboard":
                      "Actions resolved %s, ranked by resolved. Completion rate is resolved &divide; (resolved + open "
                      "now), with open now as at %s. Each company's sites are listed by open actions, most first."
                      % (pio.reporting_period(ctx), io.day_long(ctx["today"]))},
        "notes": {"Completion rate": {"html": "<strong>Completion rate.</strong> Open now includes actions raised "
                                               "before the quarter."}},
        "chat": chat,
    }
