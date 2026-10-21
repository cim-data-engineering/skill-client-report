#!/usr/bin/env python3
"""Equipment health: three operational impact rows, the snapshot heatmap and
both monthly charts, from the section's saved calls. See
references/single-site/equipment-health/equipment-health.md for what each figure means;
this module is that reference's arithmetic.
"""
import os
import re
import sys
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "scripts"))
import peak_io as io  # noqa: E402

NAME = "equipment-health"
BANDS = [(99.0, "Excellent"), (97.0, "Good"), (90.0, "Average")]
# Labour model: annual minutes saved per scored rule, by priority id.
ANNUAL_MINS = {1: 365 * 0.5, 2: 52 * 1.0, 3: 12 * 1.0, 4: 4 * 1.0, 5: 4 * 1.0}


def calls(ctx):
    sid, (q0, q1), (t0, t1) = ctx["site"]["site_id"], ctx["quarter"], ctx["trend"]
    eh = lambda f, ent, per, a, b: io.call(f, "search_equipment_health_scores", site_ids=[sid],
                                          aggregate_entities=ent, aggregate_period=per,
                                          local_start_date=a, local_end_date=b)
    return [
        io.gql("eh/types.json", "platform.metadata_types", {"limit": 400}, ["type_id", "type"]),
        eh("eh/type-month.json", ["metadata_type"], "month", q0, q1),
        eh("eh/type-all.json", ["metadata_type"], "all", q0, q1),
        eh("eh/equipment-all.json", ["equipment"], "all", q0, q1),
        eh("eh/site-month.json", ["site"], "month", t0, t1),
        eh("eh/site-all.json", ["site"], "all", q0, q1),
        eh("eh/priority-all.json", ["priority"], "all", q0, q1),
        eh("eh/priority-month.json", ["priority"], "month", t0, t1),
    ]


def more(ctx, work):
    # A site that went live inside the quarter takes its headline score over the months it kept
    on = onboarding(ctx, site_months(work))
    if on and on["start"] > ctx["quarter"][0] and not work.has("eh/site-all-live.json"):
        return [io.call("eh/site-all-live.json", "search_equipment_health_scores", site_ids=[ctx["site"]["site_id"]],
                        aggregate_entities=["site"], aggregate_period="all", local_start_date=on["start"],
                        local_end_date=ctx["quarter"][1])]
    return []


def band(v):
    for t, label in BANDS:
        if v >= t:
            return label
    return "Poor"


def site_months(work):
    return {(r.get("date") or "")[:7]: r for r in work.get("eh/site-month.json").rows}


def onboarding(ctx, site_m):
    """For scores that start after the trend window's first month: the month they start, the day
    its checks per rule date it to against the next month's pace, and the first month the windows
    keep, which skips the go-live month unless it ran from the 1st or is the last."""
    tm = ctx["trend_months"]
    have = [m for m in tm if m[:7] in site_m]
    if not have or have[0] == tm[0]:
        return None
    first, day = have[0], None
    if len(have) > 1:
        pace = lambda r: (r.get("total_executions") or 0) / max(r.get("task_count") or 0, 1)
        rate, n = pace(site_m[have[1][:7]]) / io.days_in(ctx, have[1]), io.days_in(ctx, first)
        if rate:
            ran = min(n, max(1, int(round(pace(site_m[first[:7]]) / rate))))
            day = 1 if ran >= 0.9 * n else n - ran + 1          # nine tenths of the pace is a whole month
    i = tm.index(first)
    return {"month": first, "day": io.d(first).replace(day=day).isoformat() if day else None,
            "start": first if day == 1 or i + 1 == len(tm) else tm[i + 1]}


def months_text(ctx, months):
    """'August – September 2026, and October to date', 'September 2026' or 'October 2026 to date'."""
    whole = io.whole(ctx, months)
    if not whole:
        return "%s %d to date" % (io.month(months[0]), io.d(months[0]).year)
    head = io.span(whole[0], whole[-1]) if len(whole) > 1 else "%s %d" % (io.month(whole[0]), io.d(whole[0]).year)
    return head + (io.and_to_date(ctx) if months[-1] == ctx.get("to_date") else "")


def build(ctx, work, shared):
    shared.setdefault("partial", []).extend(["automated checks", "labour cost avoided"])
    qm, tm = ctx["quarter_months"], ctx["trend_months"]
    # a site that went live inside the windows shows only the months it was monitored in full
    site_m = site_months(work)
    on = onboarding(ctx, site_m)
    start = on["start"] if on else tm[0]
    kq, kt = [m for m in qm if m >= start], [m for m in tm if m >= start]
    shared.setdefault("trend_start", []).append(start)
    shared.setdefault("period_start", []).append(kq[0])
    if on:
        shared.setdefault("live_since", []).append({"month": on["month"], "day": on["day"]})
    names = {r["type_id"]: r["type"] for r in work.get("eh/types.json").rows}
    month_of = lambda r: (r.get("date") or "")[:7]

    # snapshot heatmap
    tm_rows = work.get("eh/type-month.json")
    scores = defaultdict(dict)
    for r in tm_rows.rows:
        scores[r["metadata_type_id"]][month_of(r)] = r
    equip = defaultdict(set)
    for r in work.get("eh/equipment-all.json").rows:
        equip[r["metadata_type_id"]].add(r["equipment_id"])
    type_all = work.get("eh/type-all.json")
    host = re.match(r"https?://[^/]+", ctx["site"].get("site_link") or "")
    host = host.group(0) if host else "https://ace.cimenviro.com"
    dashboard = lambda start: ("%s/dashboard/equipment-health?site_ids=%s&start_date=%sT00:00:00.000"
                               "&end_date=%sT00:00:00.000" % (host, ctx["site"]["site_id"], start,
                                                              ctx["through"]))
    link = dashboard(kq[0])
    rows = []
    for r in type_all.rows:
        tid = r["metadata_type_id"]
        if tid in io.SYSTEM_TYPES:
            continue
        months = [io.pct(scores[tid][m[:7]]["score"], 1) if m[:7] in scores[tid] else None for m in kq]
        if all(v is None for v in months):
            continue
        rows.append({"name": names.get(tid, "Type %d" % tid), "type_id": tid,
                     "link": link + "&equipment_type_ids=%d" % tid,
                     "counts": [len(equip.get(tid, ())), r.get("task_count") or 0], "months": months})
    if len(kq) > 1:
        chg = lambda r: (r["months"][-1] - r["months"][0]) if None not in (r["months"][0], r["months"][-1]) else -1e9
        rows.sort(key=lambda r: (-chg(r), -(r["months"][-1] or 0), r["name"]))   # ties: the higher score leads
    else:
        rows.sort(key=lambda r: (r["months"][0], r["name"]))      # one month: the lowest leads
    site_q = [io.pct(site_m[m[:7]]["score"], 1) if m[:7] in site_m else None for m in kq]
    heat = {"label": "Equipment type", "dp": 1, "bands": [99, 97, 90], "counts": ["Equip", "Rules"],
            "months": [io.mon(m) for m in kq], "to_date": kq[-1] == ctx["to_date"],
            "rows": [{k: v for k, v in r.items() if k != "type_id"} for r in rows],
            "site": {"counts": [sum(r["counts"][0] for r in rows), sum(r["counts"][1] for r in rows)],
                     "months": site_q}}

    # operational impact rows
    live = kq != qm and work.has("eh/site-all-live.json")
    site_all = work.get("eh/site-all-live.json" if live else "eh/site-all.json").first()
    score = io.pct(site_all["score"], 1)
    got = [(m, v) for m, v in zip(kq, site_q) if v is not None]
    if len(got) > 1:
        delta, sub = io.movement(got[0][1], got[-1][1], 1, io.month(got[0][0]), io.month_label(ctx, got[-1][0]))
    else:
        delta, sub = None, "Scored over %s." % io.month_label(ctx, kq[0])   # a movement needs two months

    # checks and labour cost by month, each priced over its own days; the rows add up the quarter's
    code, per_hr, sym = io.currency(shared.get("site_facts") or {})
    by_month = defaultdict(list)
    for r in work.get("eh/priority-month.json").rows:
        by_month[month_of(r)].append(r)
    full = lambda m: (io.add_months(io.d(m), 1) - io.d(m)).days
    checks_m, mins_m, cost_m, rules_m = {}, {}, {}, {}
    for m in kt:
        rs = by_month.get(m[:7], [])
        checks_m[m] = sum(r.get("total_executions") or 0 for r in rs)
        mins_m[m] = sum((r.get("task_count") or 0) * ANNUAL_MINS.get(r.get("priority_id"), 4.0) for r in rs) \
            * io.days_in(ctx, m) / 365
        cost_m[m] = int(round(mins_m[m] / 60 * per_hr))
        rules_m[m] = sum(r.get("task_count") or 0 for r in rs)

    checks = sum(checks_m[m] for m in kq)
    rules = sum(r.get("task_count") or 0 for r in work.get("eh/priority-all.json").rows)
    mins, cost, days = sum(mins_m[m] for m in kq), sum(cost_m[m] for m in kq), sum(io.days_in(ctx, m) for m in kq)
    impact = [
        dict({"chip": band(score), "chip_class": "pos" if band(score) in ("Excellent", "Good") else "warn",
              "fig": "%.1f%%" % score, "cap": "equipment health maintained", "sub": sub,
              "row": "equipment-health-score"}, **({"delta": delta} if delta else {})),
        {"chip": "Continuous", "chip_class": "neu", "fig": "{:,}".format(checks),
         "cap": "automated equipment health checks ran 24/7",
         "sub": "Averaging %s monthly checks across %s scored rules." % (
             io.words(checks / sum(io.days_in(ctx, m) / full(m) for m in kq)), "{:,}".format(rules)),
         "row": "automated-checks"},
        {"chip": "Modelled", "chip_class": "neu", "fig": "%s%s" % (sym, "{:,}".format(cost)),
         "cap": "labour cost avoided",
         "sub": "%.1f hours and %.1f working days of inspection time, valued at %s %d/hr."
                % (mins / 60, mins / 60 / io.WORKING_DAY, code, per_hr),
         "row": "labour-cost-avoided"},
    ]

    # Chart 1: six months of the site score; a trend needs three points
    values = [io.pct(site_m[m[:7]]["score"], 1) if m[:7] in site_m else None for m in kt]
    pts = [(m, v) for m, v in zip(kt, values) if v is not None]
    trend_eh = None
    if len(pts) >= 3:
        th = io.thresholds([v for _, v in pts], BANDS)
        trend_eh = {"values": values, "months": [io.mon(m) for m in kt], "to_date": kt[-1] == ctx["to_date"],
                    "thresholds": th, "dp": 1,
                    "alt": io.line_alt(ctx, "site equipment health score", [m for m, _ in pts], [v for _, v in pts],
                                       th, 1)}

    # the labour cost method, worded once for the notes band and the note under Chart 2
    method = lambda window: (
        "<strong>Labour cost avoided.</strong> Assumes each rule replaces one manual check: P1 daily at "
        "30 seconds; P2 weekly, P3 monthly and P4–5 quarterly at 1 minute. Prorated over %s at %s %d/hr "
        "(regional rate) and a %g-hour working day." % (window, code, per_hr, io.WORKING_DAY))

    # Chart 2: checks and labour cost by month
    # a month with no checks scored, an outage or before go-live, is a gap, not a zero
    a = [checks_m[m] or None for m in kt]
    b = [cost_m[m] if checks_m[m] else None for m in kt]
    money = "dollars" if sym == "$" else ("pounds" if sym == "£" else "euros")
    alt = lambda v, f: "no data" if v is None else f % v
    trend_checks = {"a": a, "b": b, "labels_a": [io.compact(v) if v else "" for v in a],
                    "labels_b": ["%s%.1fk" % (sym, v / 1000) if v is not None else "" for v in b],
                    "months": [io.mon(m) for m in kt], "to_date": kt[-1] == ctx["to_date"],
                    "note_after": "Automated health checks",
                    "note": method("each month's days" + (" (%s to date)" % io.month(ctx["to_date"])
                                                              if ctx["to_date"] else "")),
                    "alt": "Grouped bar chart, %s. Automated checks: %s and %s million. Labour cost avoided: %s and %s thousand %s."
                           % (io.span(kt[0], kt[-1], sep=" to "), ", ".join(alt(v and v / 1e6, "%.2f") for v in a[:-1]), alt(a[-1] and a[-1] / 1e6, "%.2f"),
                              ", ".join(alt(v if v is None else v / 1e3, "%.1f") for v in b[:-1]), alt(b[-1] if b[-1] is None else b[-1] / 1e3, "%.1f"), money)
                           + io.to_date_note(ctx, kt)}

    chat = []
    if on:
        chat.append("Equipment health went live %s, so its figures start with %s." % (
            "on about %s" % io.day_long(on["day"]) if on["day"] else "in %s" % io.month(on["month"]),
            io.month_label(ctx, start)) + ("" if trend_eh else " Too few months for its trend chart."))

    # A month scored off under half the rules of each month beside it, or off none, is a data outage
    # wearing a score. A count that rises or falls by half again and holds is a coverage change.
    seq = [(m, rules_m[m]) for m in kt]
    rules_text = lambda n: "{:,} rule{}".format(n, "" if n == 1 else "s") if n else "none"
    low = [i for i, (m, n) in enumerate(seq)
           if len(seq) > 1 and (n == 0 or all(n < x / 2 for _, x in seq[max(i - 1, 0):i] + seq[i + 1:i + 2]))]
    out = ["%s scored %s" % (io.month_label(ctx, seq[i][0]), rules_text(seq[i][1])) for i in low]
    steps = ["%s scored %s against %s in %s" % (io.month_label(ctx, seq[i][0]), rules_text(seq[i][1]),
                                                "{:,}".format(seq[i - 1][1]), io.month_label(ctx, seq[i - 1][0]))
             for i in range(1, len(seq)) if i not in low and i - 1 not in low
             and max(seq[i][1], seq[i - 1][1]) >= 1.5 * min(seq[i][1], seq[i - 1][1])]
    if out:
        chat.append("Equipment health data was out for part of the window: %s, against the months either side."
                    % io.listing(out))
    if steps:
        chat.append("Equipment health coverage changed, not an outage: %s." % "; ".join(steps))

    links = {"equipment_health": link}
    if trend_eh:
        links["trend_eh"] = dashboard(kt[0])
    full_window = kq == qm
    return dict({
        "impact": impact,
        "equipment_health": heat,
        "trend_eh": trend_eh,
        "trend_checks": trend_checks,
        "links": links,
        "datelines": {"Equipment health snapshot":
                      "%s, the three months of the reporting quarter%s. Share of rule executions returning no "
                      "fault, by equipment type, sorted by change across the %s."
                      % (io.span(kq[0], io.whole(ctx, kq)[-1]), io.and_to_date(ctx), "period" if ctx["to_date"] else "quarter")
                      if full_window else
                      "%s. Share of rule executions returning no fault, by equipment type, %s."
                      % (months_text(ctx, kq), "sorted by change across the period" if len(kq) > 1 else "lowest first"),
                      "Monthly equipment health": "%s, the last six complete months%s."
                                                  % (io.span(kt[0], io.whole(ctx, kt)[-1]), io.and_to_date(ctx))
                                                  if kt == tm else "%s." % months_text(ctx, kt)},
        "notes": {"Labour cost avoided": method("the %d-day period" % days)},
        "chat": chat,
    }, **({} if kt == tm else {"statements": {"Monthly equipment health": "The trend so far"}}))
