#!/usr/bin/env python3
"""Actions resolved and the leaderboard: the faults resolved impact row, six
months of raised vs resolved, and who closed the work. Every number printed is a
count from count_tickets or a pagination.total; rows only add what a count
cannot, the median and company names and logos. See
references/single-site/actions-and-wins/alerts-resolved.md.
"""
import base64
import os
import re
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from statistics import median

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "scripts"))
import peak_io as io  # noqa: E402

NAME = "alerts-resolved"
STAT4 = ["open", "in_progress", "closed", "on_hold"]           # every status but Not Doing
BANDS = [(99.0, "Excellent"), (95.0, "Good"), (90.0, "Average")]
# The chart counts actions. The scaffold's eyebrow still reads "alerts" until assets/reference-report.html
# takes EYEBROW, so the date line goes under both and fills whichever the scaffold carries.
EYEBROW = "Monthly actions raised vs resolved"
OLD_EYEBROW = "Monthly alerts raised vs resolved"
BULK = 10                  # closures in one sitting, each within GAP of the one before, is a bulk close-out
GAP = 600                  # seconds


def esc(ctx):
    return {"type": "escalated", "site_ids": [ctx["site"]["site_id"]], "ticket_archived": False}


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


# Open now carries only what the leaderboard needs, the company of anyone holding open
# work: saved responses hold numbers, ids and type, level or company names and logo
# links, never what people wrote. The key win candidates, comments and all, are read
# where they arrive.
COMPANY = ["assignees.id", "assignees.entity.name", "assignees.entity.logo_url"]
OPEN_FIELDS = ["status_id"] + COMPANY


def calls(ctx):
    sid, (q0, q1), (t0, t1) = ctx["site"]["site_id"], ctx["quarter"], ctx["trend"]
    count = lambda f, **kw: io.call(f, "count_tickets", site_ids=[sid], ticket_types=["escalated"], **kw)
    out = [count("ar/resolved-by-assignee.json", statuses=STAT4, aggregate_entities=["assignee"],
                 local_resolved_start=t0, local_resolved_end=t1),
           count("ar/open-by-assignee.json", statuses=["open", "in_progress", "on_hold"],
                 aggregate_entities=["assignee"])]
    for m in ctx["trend_months"]:
        nxt = io.add_months(io.d(m), 1).isoformat()
        out.append(count("ar/raised-%s.json" % m[:7], statuses=STAT4, local_created_start=m, local_created_end=nxt))
    for m in ctx["trend_months"]:
        nxt = io.add_months(io.d(m), 1).isoformat()
        out.append(count("ar/resolved-%s.json" % m[:7], statuses=STAT4, local_resolved_start=m, local_resolved_end=nxt))
    out += [
        io.gql("ar/resolved-rows.json", "tickets.tickets",
               dict(esc(ctx), resolved_at_local_start=t0 + "T00:00:00", resolved_at_local_end=t1 + "T00:00:00", limit=1000),
               ["age", "resolved_at", "status_id"] + COMPANY),
        # Open now: the company of anyone holding open work and nothing resolved.
        io.gql("ar/open-rows.json", "tickets.tickets", dict(esc(ctx), status_ids=[1, 3, 7], limit=1000), OPEN_FIELDS),
        io.call("ar/alerts-closed.json", "search_alert_tickets", site_ids=[sid], status="closed",
                rule_states=["running"], local_resolved_start=q0, local_resolved_end=q1, limit=1),
        io.call("ar/alerts-recovered.json", "search_alert_tickets", site_ids=[sid], status="closed",
                rule_states=["running"], fault_statuses=["recovered"], local_resolved_start=q0,
                local_resolved_end=q1, limit=1),
    ]
    return out


def more(ctx, work):
    out = []
    for f in ("ar/resolved-rows.json", "ar/open-rows.json"):
        r = work.get(f)
        if r.has_more:
            base = next(c for c in calls(ctx) if c["file"] == f)
            out += [dict(base, file=f.replace(".json", "-%d.json" % s),
                         args=dict(base["args"], args=dict(base["args"]["args"], start_index=s)))
                    for s in range(1000, r.total or 0, 1000) if not work.has(f.replace(".json", "-%d.json" % s))]
    return out


def rows(work, f):
    out, s = list(work.get(f).rows), 1000
    while work.has(f.replace(".json", "-%d.json" % s)):
        out += work.get(f.replace(".json", "-%d.json" % s)).rows
        s += 1000
    return out


def band(v):
    for t, label in BANDS:
        if v >= t:
            return label
    return "Poor"


def local_day(ts, tz):
    t = datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(io.zone(tz))
    return t.date()


def plural(n, word):
    return "%d %s%s" % (n, word, "" if n == 1 else "s")


def sittings(stamps):
    """(first timestamp, count) for each run of at least BULK closures, each within GAP of the last."""
    out, run = [], []
    when = lambda s: datetime.fromisoformat(s.replace("Z", "+00:00"))
    for s in stamps + [None]:
        if s and run and (when(s) - when(run[-1])).total_seconds() <= GAP:
            run.append(s)
            continue
        if len(run) >= BULK:
            out.append((run[0], len(run)))
        run = [s] if s else []
    return out


def build(ctx, work, shared):
    tm, (q0, q1), (t0, t1) = ctx["trend_months"], ctx["quarter"], ctx["trend"]
    tz = ctx["site"]["timezone"]
    count = lambda f: (work.get(f).first() or {}).get("ticket_count", 0)
    raised = [count("ar/raised-%s.json" % m[:7]) for m in tm]
    resolved = [count("ar/resolved-%s.json" % m[:7]) for m in tm]
    faults = work.get("ar/alerts-closed.json").total or 0
    recovered = work.get("ar/alerts-recovered.json").total or 0

    open_now = work.get("ar/open-rows.json").total or 0
    if not faults or not sum(resolved):
        if not faults and not sum(resolved):
            why = ("nothing was resolved, with no alert closed in the quarter and no action resolved in the six "
                   "months. %s open now." % ("1 action is" if open_now == 1 else "%d actions are" % open_now))
        elif not faults:
            why = ("no alert on a running rule was closed in the quarter, so the faults resolved row has no "
                   "recovery rate. The %s resolved over the six months and the %d open now are not shown."
                   % (plural(sum(resolved), "action"), open_now))
        else:
            why = ("no action was resolved in the six months, so there is no one to rank. The %s closed in the "
                   "quarter and the %s open now are not shown." % (plural(faults, "alert"), plural(open_now, "action")))
        return {"drop": ["alerts-resolved", "key-wins"], "chat": ["Actions and key wins are left out: " + why]}
    shared.setdefault("partial", []).append("action counts")      # only once the section stays

    res_rows = rows(work, "ar/resolved-rows.json")
    open_rows = rows(work, "ar/open-rows.json")
    company, logo_url = {}, {}
    for r in res_rows + open_rows:
        for a in r.get("assignees") or []:
            ent = a.get("entity") or {}
            if a.get("id") and ent.get("name"):
                company.setdefault(a["id"], ent["name"])
                if ent.get("logo_url"):
                    logo_url.setdefault(ent["name"], ent["logo_url"])

    board = {}
    for f, key in (("ar/resolved-by-assignee.json", "resolved"), ("ar/open-by-assignee.json", "open")):
        for r in work.get(f).rows:
            aid, name = r.get("assignee_id"), " ".join((r.get("assignee_name") or "").split())
            if not aid or io.system_account(aid, name):     # CIM's own system accounts never rank
                continue
            e = board.setdefault(aid, {"name": name, "company": company.get(aid, ""), "resolved": 0, "open": 0})
            e[key] += r.get("ticket_count") or 0
    rate = lambda e: e["resolved"] / (e["resolved"] + e["open"]) if e["resolved"] + e["open"] else 0
    leaderboard = sorted(board.values(), key=lambda e: (-e["resolved"], -rate(e), e["name"]))
    names = list(dict.fromkeys(e["company"] for e in leaderboard if e["company"]))
    logos = fetch_logos({n: logo_url[n] for n in names if n in logo_url})
    for e in leaderboard:
        if logos.get(e["company"]):
            e["logo"] = logos[e["company"]]
    unlogged = [n for n in names if not logos.get(n)]

    in_q = [r for r in res_rows if r.get("status_id") != 8 and r.get("age") is not None and r.get("resolved_at")
            and q0 <= local_day(r["resolved_at"], tz).isoformat() < q1]
    med = median(r["age"] for r in in_q) / 86400000 if in_q else None
    med_text = ("%d days" % round(med) if med >= 1 else "%.1f hours" % (med * 24)) if med is not None else "–"
    pct_rec = recovered / faults * 100
    impact = [{"chip": band(pct_rec), "chip_class": "pos" if band(pct_rec) in ("Excellent", "Good") else "warn",
               "fig": "{:,}".format(faults), "cap": "faults resolved with %d%% verified recovery" % round(pct_rec),
               "sub": "Median time to resolve of %s, measured from linked action creation to resolution." % med_text,
               "row": "faults-resolved"}]

    # a run of closures minutes apart is a bulk close-out, not a run of repairs
    bulk = sittings(sorted(r["resolved_at"] for r in res_rows if r.get("resolved_at") and r.get("status_id") != 8))
    site = ctx["site"]
    host = re.match(r"https?://[^/]+", site.get("site_link") or "")
    host = host.group(0) if host else "https://ace.cimenviro.com"
    tw = io.whole(ctx, tm)
    span6 = io.span(tw[0], tw[-1])
    chart_line = ("%s, the last six complete months%s. Raised counts actions created in the month, resolved counts "
                  "actions closed in it. Actions marked Not Doing are excluded from both series."
                  % (span6, io.and_to_date(ctx)))
    chat = []
    if bulk:
        chat.append("Resolved counts include bulk close-outs, %d or more actions closed minutes apart: %s."
                    % (BULK, io.listing("%d on %s" % (n, io.day_short(local_day(t, tz).isoformat())) for t, n in bulk)))
    if unlogged:
        chat.append("Leaderboard initials stand in for %s, with no logo in PEAK or none that could be fetched."
                    % io.listing(unlogged))
    return {
        "impact": impact,
        "alerts": {"a": raised, "b": resolved, "scale": "shared",
                   "alt": "Grouped bar chart of actions raised and resolved each month, %s. Raised %s and %d. "
                          "Resolved %s and %d." % (io.span(tm[0], tm[-1], sep=" to "), ", ".join(map(str, raised[:-1])), raised[-1],
                                                   ", ".join(map(str, resolved[:-1])), resolved[-1])
                          + io.to_date_note(ctx, tm)},
        "leaderboard": leaderboard,
        "links": {"leaderboard": "%s/reports/tickets?site_ids=%s&start_date=%sT00:00:00.000&end_date=%sT00:00:00.000"
                                 "&grouping=assignee" % (host, site["site_id"], t0, ctx["through"])},
        "datelines": {
            EYEBROW: chart_line,
            OLD_EYEBROW: chart_line,
            "Actions leaderboard":
                "Actions resolved %s%s, ranked by resolved. Completion rate is resolved ÷ (resolved + currently "
                "open); open now as at %s." % (span6, io.and_to_date(ctx, " and "), io.day_long(ctx["today"]))},
        "notes": {
            "Verified recovery": "<strong>Verified recovery.</strong> Share of alerts closed in the period with the "
                                 "fault recovered. Includes only alerts on active rules.",
            "Raised vs resolved": "<strong>Raised vs resolved.</strong> Counts actions, not alerts. One action can "
                                  "cover several alerts.",
        },
        "chat": chat,
    }
