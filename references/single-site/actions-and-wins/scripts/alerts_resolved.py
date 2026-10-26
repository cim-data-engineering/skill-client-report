#!/usr/bin/env python3
"""Actions resolved and the leaderboard: the faults resolved impact row, six
months of raised vs resolved, and who closed the work, with a shoutout for its
leader. Every number printed is a count from count_tickets or a pagination.total;
rows only add what a count cannot, the median, company names and logos, and the
ticket the leader's first name and email are read off. See
references/single-site/actions-and-wins/alerts-resolved.md.
"""
import os
import sys
from statistics import median

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "scripts"))
import peak_io as io  # noqa: E402

STAT4 = ["open", "in_progress", "closed", "on_hold"]           # every status but Not Doing
BANDS = [(99.0, "Excellent"), (95.0, "Good"), (90.0, "Average")]
EYEBROW = "Monthly actions raised vs resolved"
BULK = 10                  # closures in one sitting, each within GAP of the one before, is a bulk close-out
GAP = 600                  # seconds


def esc(ctx):
    return {"type": "escalated", "site_ids": [ctx["site"]["site_id"]], "ticket_archived": False}


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
               ["ticket_id", "age", "resolved_at", "status_id"] + COMPANY),
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
    due = io.pages_due(work, [c for c in calls(ctx) if c["file"] in ("ar/resolved-rows.json", "ar/open-rows.json")])
    if due or work.has("ar/leader.json"):
        return due
    # the leader's first name and email, for the shoutout: one ticket they resolved whose assignees all have
    # names, since one without fails the pull
    ranked = standings(work)
    if not ranked or not ranked[0][1]["resolved"]:
        return []                         # no one resolved an action that counts: no leader to thank
    names = {r["assignee_id"]: r.get("assignee_name")
             for f in ("ar/resolved-by-assignee.json", "ar/open-by-assignee.json")
             for r in work.get(f).rows if r.get("assignee_id")}
    lead = ranked[0][0]
    named = [r for r in io.rows(work, "ar/resolved-rows.json") if r.get("status_id") != 8 and r.get("ticket_id")
             and lead in {a.get("id") for a in r.get("assignees") or []}
             and all(names.get(a["id"]) for a in r.get("assignees") or [] if a.get("id"))]
    return [io.leader_pull(ctx["site"]["site_id"], named[0]["ticket_id"])] if named else []


def sittings(stamps):
    """(first timestamp, count) for each run of at least BULK closures, each within GAP of the last."""
    out, run = [], []
    for s in stamps + [None]:
        if s and run and (io.utc(s) - io.utc(run[-1])).total_seconds() <= GAP:
            run.append(s)
            continue
        if len(run) >= BULK:
            out.append((run[0], len(run)))
        run = [s] if s else []
    return out


def drop_reason(faults, resolved, open_now):
    """Why the section is out, when nothing was resolved: no alert closed in the quarter leaves the
    recovery rate no denominator, and no action resolved leaves no one to rank. None when it stays."""
    if faults and sum(resolved):
        return None
    if not faults and not sum(resolved):
        return ("nothing was resolved, with no alert closed in the quarter and no action resolved in the six "
                "months. %s open now." % ("1 action is" if open_now == 1 else "%d actions are" % open_now))
    if not faults:
        return ("no alert on a running rule was closed in the quarter, so the faults resolved row has no "
                "recovery rate. The %s resolved over the six months and the %d open now are not shown."
                % (io.plural(sum(resolved), "action"), open_now))
    return ("no action was resolved in the six months, so there is no one to rank. The %s closed in the "
            "quarter and the %s open now are not shown." % (io.plural(faults, "alert"), io.plural(open_now, "action")))


def standings(work):
    """[(assignee id, entry)]: each assignee's actions resolved and open now, CIM's own system accounts left
    out, ranked by resolved then completion rate."""
    entries = {}
    for f, key in (("ar/resolved-by-assignee.json", "resolved"), ("ar/open-by-assignee.json", "open")):
        for r in work.get(f).rows:
            aid, name = r.get("assignee_id"), " ".join((r.get("assignee_name") or "").split())
            if not aid or io.system_account(aid, name):     # CIM's own system accounts never rank
                continue
            e = entries.setdefault(aid, {"name": name, "company": "", "resolved": 0, "open": 0})
            e[key] += r.get("ticket_count") or 0
    rate = lambda e: e["resolved"] / (e["resolved"] + e["open"]) if e["resolved"] + e["open"] else 0
    return sorted(entries.items(), key=lambda x: (-x[1]["resolved"], -rate(x[1]), x[1]["name"]))


def board(ranked, rows):
    """(leaderboard, companies with no logo): the standings, each beside their company's logo."""
    company, logo_url = {}, {}
    for r in rows:
        for a in r.get("assignees") or []:
            ent = a.get("entity") or {}
            if a.get("id") and ent.get("name"):
                company.setdefault(a["id"], ent["name"])
                if ent.get("logo_url"):
                    logo_url.setdefault(ent["name"], ent["logo_url"])
    leaderboard = []
    for aid, e in ranked:
        e["company"] = company.get(aid, "")
        leaderboard.append(e)
    names = list(dict.fromkeys(e["company"] for e in leaderboard if e["company"]))
    logos = io.fetch_logos({n: logo_url[n] for n in names if n in logo_url})
    for e in leaderboard:
        if logos.get(e["company"]):
            e["logo"] = logos[e["company"]]
    return leaderboard, [n for n in names if not logos.get(n)]


def median_text(res_rows, q0, q1, tz):
    """The median time to resolve over the actions resolved in the quarter: in days, or hours under a day."""
    in_q = [r for r in res_rows if r.get("status_id") != 8 and r.get("age") is not None and r.get("resolved_at")
            and q0 <= io.local_day(r["resolved_at"], tz) < q1]
    if not in_q:
        return None
    med = median(r["age"] for r in in_q) / 86400000
    return io.plural(round(med), "day") if med >= 1 else "%.1f hours" % (med * 24)


def build(ctx, work, shared):
    tm, (q0, q1), (t0, _) = ctx["trend_months"], ctx["quarter"], ctx["trend"]
    tz = ctx["site"]["timezone"]
    count = lambda f: (work.get(f).first() or {}).get("ticket_count", 0)
    raised = [count("ar/raised-%s.json" % m[:7]) for m in tm]
    resolved = [count("ar/resolved-%s.json" % m[:7]) for m in tm]
    faults = work.get("ar/alerts-closed.json").total or 0
    recovered = work.get("ar/alerts-recovered.json").total or 0
    why = drop_reason(faults, resolved, work.get("ar/open-rows.json").total or 0)
    if why:
        shared["nothing_resolved"] = True        # with nothing resolved, no win has anything to stand on
        return {"drop": True, "chat": ["Actions and key wins are left out: " + why]}
    shared.setdefault("partial", []).append("action counts")      # only once the section stays

    res_rows = io.rows(work, "ar/resolved-rows.json")
    ranked = standings(work)
    leaderboard, unlogged = board(ranked, res_rows + io.rows(work, "ar/open-rows.json"))
    pct_rec = recovered / faults * 100
    chip = io.band(pct_rec, BANDS)
    med = median_text(res_rows, q0, q1, tz)
    impact = [{"chip": chip, "chip_class": "pos" if chip in ("Excellent", "Good") else "warn",
               "fig": "{:,}".format(faults), "cap": "faults resolved with %d%% verified recovery" % round(pct_rec),
               "sub": ("Median time to resolve of %s, measured from linked action creation to resolution." % med
                       if med else "No action was resolved in the quarter to time."),
               "row": "faults-resolved"}]

    # a run of closures minutes apart is a bulk close-out, not a run of repairs
    bulk = sittings(sorted(r["resolved_at"] for r in res_rows if r.get("resolved_at") and r.get("status_id") != 8))
    site = ctx["site"]
    host = io.host(site)
    # the leaderboard counts the whole six months; the chart starts where the site's monitoring does
    six = io.span(tm[0], io.whole(ctx, tm)[-1])
    first = max(tm[0], min(shared.get("trend_start") or [tm[0]]))
    keep = [i for i, m in enumerate(tm) if m >= first]
    window = "the last six complete months" if len(keep) == len(tm) else "the complete months monitored"
    tm, raised, resolved = [tm[i] for i in keep], [raised[i] for i in keep], [resolved[i] for i in keep]
    tw = io.whole(ctx, tm)
    span6 = io.span(tw[0], tw[-1])
    chart_line = ("%s, %s%s. Raised counts actions created in the month, resolved counts "
                  "actions closed in it. Actions marked Not Doing are excluded from both series."
                  % (span6, window, io.and_to_date(ctx)))
    chat = []
    if bulk:
        chat.append("Resolved counts include bulk close-outs, %d or more actions closed minutes apart: %s."
                    % (BULK, io.listing("%d on %s" % (n, io.day_short(io.local_day(t, tz))) for t, n in bulk)))
    if unlogged:
        chat.append("Leaderboard initials stand in for %s, with no logo in PEAK or none that could be fetched."
                    % io.listing(unlogged))
    if not leaderboard:
        chat.append("No one outside CIM's system accounts resolved or holds an action, so the actions leaderboard "
                    "is left out.")
    links = {"leaderboard": "%s/reports/tickets?site_ids=%s&start_date=%sT00:00:00.000&end_date=%sT00:00:00.000"
                            "&grouping=assignee" % (host, site["site_id"], t0, ctx["through"])} if leaderboard else {}
    # the leader's shoutout, where they resolved an action and PEAK gave their first name and email
    lead = ranked[0][0] if ranked and ranked[0][1]["resolved"] else None
    first, email = io.leader_contact(work).get(lead, ("", ""))
    shout = io.shoutout(first, email, site["site_name"].strip()) if first and email else None
    return {
        "impact": impact,
        "alerts": {"a": raised, "b": resolved, "scale": "shared",
                   "months": [io.mon(m) for m in tm], "to_date": tm[-1] == ctx["to_date"],
                   "alt": "Grouped bar chart of actions raised and resolved each month, %s. Raised %s. Resolved %s."
                          % (io.span(tm[0], tm[-1], sep=" to "), io.listing(map(str, raised)),
                             io.listing(map(str, resolved)))
                          + io.to_date_note(ctx, tm)},
        "leaderboard": leaderboard,
        "shoutout": shout,
        "links": links,
        "datelines": {
            EYEBROW: chart_line,
            "Actions leaderboard":
                "Actions resolved %s%s, ranked by resolved. Completion rate is resolved ÷ (resolved + currently "
                "open); open now as at %s." % (six, io.and_to_date(ctx, " and "), io.day_long(ctx["today"]))},
        "notes": {
            "Verified recovery": "<strong>Verified recovery.</strong> Share of alerts closed in the period with the "
                                 "fault recovered. Includes only alerts on active rules.",
            "Raised vs resolved": "<strong>Raised vs resolved.</strong> Counts actions, not alerts. One action can "
                                  "cover several alerts.",
        },
        "chat": chat,
    }
