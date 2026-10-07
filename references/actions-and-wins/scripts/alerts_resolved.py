#!/usr/bin/env python3
"""Actions resolved and the leaderboard: the faults resolved impact row, six
months of raised vs resolved, and who closed the work. Every number printed is a
count from count_tickets or a pagination.total; rows only add what a count
cannot, the median and company names. See
references/actions-and-wins/alerts-resolved.md.
"""
import os
import re
import sys
from datetime import datetime, timezone
from statistics import median

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "scripts"))
import peak_io as io  # noqa: E402

NAME = "alerts-resolved"
STAT4 = ["open", "in_progress", "closed", "on_hold"]           # every status but Not Doing
BANDS = [(99.0, "Excellent"), (95.0, "Good"), (90.0, "Average")]
AGENT = re.compile(r"^\s*agent\b", re.I)
BULK = 10                  # closures in one sitting, each within GAP of the one before, is a bulk close-out
GAP = 600                  # seconds


def esc(ctx):
    return {"type": "escalated", "site_ids": [ctx["site"]["site_id"]], "ticket_archived": False}


# Open now carries only what the leaderboard needs, the company of anyone holding open
# work: saved responses hold numbers, ids and type, level or company names, never what
# people wrote. The key win candidates, comments and all, are read where they arrive.
OPEN_FIELDS = ["status_id", "assignees.id", "assignees.entity.name"]


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
               ["age", "resolved_at", "status_id", "assignees.id", "assignees.entity.name"]),
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
    from zoneinfo import ZoneInfo
    t = datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(ZoneInfo(tz))
    return t.date()


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

    if not faults or not sum(resolved):
        return {"drop": ["alerts-resolved", "key-wins"],
                "facts": ["Actions resolved: nothing resolved in the window (%d alerts closed in the quarter, "
                          "%d actions resolved in six months), so the section and Key wins are left out. Give "
                          "the open count in chat instead." % (faults, sum(resolved))]}

    res_rows = rows(work, "ar/resolved-rows.json")
    open_rows = rows(work, "ar/open-rows.json")
    company = {}
    for r in res_rows + open_rows:
        for a in r.get("assignees") or []:
            if a.get("id") and (a.get("entity") or {}).get("name"):
                company.setdefault(a["id"], a["entity"]["name"])

    board = {}
    for f, key in (("ar/resolved-by-assignee.json", "resolved"), ("ar/open-by-assignee.json", "open")):
        for r in work.get(f).rows:
            aid, name = r.get("assignee_id"), " ".join((r.get("assignee_name") or "").split())
            if not aid or AGENT.match(name):
                continue
            e = board.setdefault(aid, {"name": name, "company": company.get(aid, ""), "resolved": 0, "open": 0})
            e[key] += r.get("ticket_count") or 0
    rate = lambda e: e["resolved"] / (e["resolved"] + e["open"]) if e["resolved"] + e["open"] else 0
    leaderboard = sorted(board.values(), key=lambda e: (-e["resolved"], -rate(e), e["name"]))

    in_q = [r for r in res_rows if r.get("status_id") != 8 and r.get("age") is not None and r.get("resolved_at")
            and q0 <= local_day(r["resolved_at"], tz).isoformat() < q1]
    med = median(r["age"] for r in in_q) / 86400000 if in_q else None
    med_text = ("%d days" % round(med) if med >= 1 else "%.1f hours" % (med * 24)) if med is not None else "–"
    pct_rec = recovered / faults * 100
    impact = [{"chip": band(pct_rec), "chip_class": "pos" if band(pct_rec) in ("Excellent", "Good") else "warn",
               "fig": "{:,}".format(faults), "cap": "faults resolved with %d%% verified recovery" % round(pct_rec),
               "sub": "Median time to resolve of %s, measured from linked action creation to resolution." % med_text,
               "order": 5}]

    # a run of closures minutes apart is a bulk close-out, not a run of repairs
    bulk = sittings(sorted(r["resolved_at"] for r in res_rows if r.get("resolved_at") and r.get("status_id") != 8))
    site = ctx["site"]
    host = re.match(r"https?://[^/]+", site.get("site_link") or "")
    host = host.group(0) if host else "https://ace.cimenviro.com"
    span6 = io.span(tm[0], tm[-1])
    facts = [
        "Actions: %d raised and %d resolved over %s. By month, raised %s; resolved %s."
        % (sum(raised), sum(resolved), io.span(tm[0], tm[-1], short=True), ", ".join(map(str, raised)),
           ", ".join(map(str, resolved))),
        "Faults resolved this quarter: %d alerts closed on running rules, %d recovered (%.1f%%); median time to "
        "resolve %s over %d actions resolved in the quarter." % (faults, recovered, pct_rec, med_text, len(in_q)),
        "Bulk close-outs (%d or more closed minutes apart): " % BULK + ("; ".join(
            "%d on %s" % (n, io.day_short(local_day(t, tz).isoformat())) for t, n in bulk) or "none"),
        "Leaderboard top three: " + "; ".join("%s (%s) %d resolved, %d open" % (e["name"], e["company"] or "no company",
                                                                             e["resolved"], e["open"])
                                              for e in leaderboard[:3]),
        "Open now: %d actions with %d people." % (sum(e["open"] for e in leaderboard),
                                                  sum(1 for e in leaderboard if e["open"])),
    ]
    return {
        "impact": impact,
        "alerts": {"a": raised, "b": resolved, "scale": "shared", "note_after": "Faults triaged and resolved",
                   "alt": "Grouped bar chart of actions raised and resolved each month, %s. Raised %s and %d. "
                          "Resolved %s and %d." % (io.span(tm[0], tm[-1], sep=" to "), ", ".join(map(str, raised[:-1])), raised[-1],
                                                   ", ".join(map(str, resolved[:-1])), resolved[-1])},
        "leaderboard": leaderboard,
        "links": {"alerts": work.get("ar/alerts-closed.json").link,
                  "leaderboard": "%s/reports/tickets?site_ids=%s&start_date=%sT00:00:00.000&end_date=%sT00:00:00.000"
                                 "&grouping=assignee" % (host, site["site_id"], t0, io.last_day(t1).isoformat())},
        "datelines": {
            "Monthly alerts raised vs resolved":
                "%s, the last six complete months. Raised counts actions created in the month, resolved counts "
                "actions closed in it. Actions marked Not Doing are excluded from both series." % span6,
            "Actions leaderboard":
                "Actions resolved %s, ranked by resolved. Completion rate is resolved ÷ (resolved + currently open); "
                "open now as at %s." % (span6, io.day_long(ctx["today"]))},
        "notes": {
            "Verified recovery": "<strong>Verified recovery.</strong> Recovery rate is alerts resolved in the period "
                                 "with fault status recovered, divided by all alerts resolved in the period, counting "
                                 "alerts with status closed on rules still running.",
            "Median time to resolve": "<strong>Median time to resolve</strong> is measured from the linked action's "
                                      "creation to its resolution, over the actions resolved in the quarter, not from "
                                      "the alert's own dates, since detection is automatic but resolution is human work.",
            "Raised vs resolved": "<strong>Raised vs resolved.</strong> Raised counts action tickets created in the "
                                  "month, not the alerts behind them: detection is automatic, raising an action is a "
                                  "human triage decision, and one action can be linked to many alerts. Resolved counts "
                                  "actions on their resolution date. Actions marked Not Doing are excluded from both series.",
            "Completion rate": "<strong>Completion rate</strong> is resolved ÷ (resolved + currently open) as at the "
                               "issue date, so 100% reflects holding no open work.",
        },
        "prose": {"alerts_trend": "The note under raised vs resolved: the balance across the six months, and any "
                                  "month where raised ran far above resolved or a bulk close-out drove a peak."},
        "facts": facts,
    }
