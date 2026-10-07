#!/usr/bin/env python3
"""Equipment health: three operational impact rows, the snapshot heatmap and
both monthly charts, from eight saved calls. See
references/equipment-health/equipment-health.md for what each figure means;
this module is that reference's arithmetic, so the model never redoes it.
"""
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "scripts"))
import peak_io as io  # noqa: E402

NAME = "equipment-health"
SYSTEM_TYPES = {21, 37, 69, 70, 87, 105, 114}
BANDS = [(99.0, "Excellent"), (97.0, "Good"), (90.0, "Average")]
# Labour model: annual minutes saved per scored rule, by priority id.
ANNUAL_MINS = {1: 365 * 0.5, 2: 52 * 1.0, 3: 12 * 1.0, 4: 4 * 1.0, 5: 4 * 1.0}
HOURS_PER_DAY = 7.6
CURRENCIES = {"australian dollar": ("AUD", 150, "$"), "us dollar": ("USD", 100, "$"),
              "united states dollar": ("USD", 100, "$"), "new zealand dollar": ("NZD", 150, "$"),
              "british pound": ("GBP", 75, "£"), "pound sterling": ("GBP", 75, "£"),
              "canadian dollar": ("CAD", 150, "$"), "euro": ("EUR", 100, "€")}


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
    return []


def rate(facts):
    return CURRENCIES.get((facts.get("monetary_currency") or "").strip().lower(), ("USD", 100, "$"))


def band(v):
    for t, label in BANDS:
        if v >= t:
            return label
    return "Poor"


def build(ctx, work, shared):
    qm, tm = ctx["quarter_months"], ctx["trend_months"]
    q0, q1 = ctx["quarter"]
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
    link = next((x.link for x in (tm_rows, type_all, work.get("eh/site-all.json"),
                                  work.get("eh/priority-all.json")) if x.link), None)
    rows = []
    for r in type_all.rows:
        tid = r["metadata_type_id"]
        if tid in SYSTEM_TYPES:
            continue
        months = [io.pct(scores[tid][m[:7]]["score"], 2) if m[:7] in scores[tid] else None for m in qm]
        if all(v is None for v in months):
            continue
        rows.append({"name": names.get(tid, "Type %d" % tid), "type_id": tid,
                     "link": (link + "&equipment_type_ids=%d" % tid) if link else None,
                     "counts": [len(equip.get(tid, ())), r.get("task_count") or 0], "months": months})
    chg = lambda r: (r["months"][-1] - r["months"][0]) if None not in (r["months"][0], r["months"][-1]) else -1e9
    rows.sort(key=lambda r: (-chg(r), -(r["months"][-1] or 0), r["name"]))   # ties: the higher score leads
    site_m = {month_of(r): r for r in work.get("eh/site-month.json").rows}
    site_q = [io.pct(site_m[m[:7]]["score"], 2) for m in qm if m[:7] in site_m]
    heat = {"label": "Equipment type", "dp": 2, "bands": [99, 97, 90], "counts": ["Equip", "Rules"],
            "rows": [{k: v for k, v in r.items() if k != "type_id"} for r in rows],
            "site": {"counts": [sum(r["counts"][0] for r in rows), sum(r["counts"][1] for r in rows)],
                     "months": site_q}}

    # operational impact rows
    site_all = work.get("eh/site-all.json").first()
    score = io.pct(site_all["score"], 2)
    delta, sub = io.movement(site_q[0], site_q[-1], 2, io.month(qm[0]), io.month(qm[-1]))
    pri = work.get("eh/priority-all.json").rows
    checks = sum(r.get("total_executions") or 0 for r in pri)
    rules = sum(r.get("task_count") or 0 for r in pri)
    code, per_hr, sym = rate(shared.get("site_facts") or {})
    days = (io.d(q1) - io.d(q0)).days
    mins = sum((r.get("task_count") or 0) * ANNUAL_MINS.get(r.get("priority_id"), 4.0) for r in pri) * days / 365
    cost = mins / 60 * per_hr
    impact = [
        dict({"chip": band(score), "chip_class": "pos" if band(score) in ("Excellent", "Good") else "warn",
              "fig": "%.2f%%" % score, "cap": "equipment health maintained", "sub": sub,
              "order": 1}, **({"delta": delta} if delta else {})),
        {"chip": "Continuous", "chip_class": "neu", "fig": "{:,}".format(checks),
         "cap": "automated equipment health checks ran 24/7",
         "sub": "Averaging %s monthly checks across %s scored rules." % (io.words(checks / len(qm)),
                                                                        "{:,}".format(rules)),
         "order": 3},
        {"chip": "Modelled", "chip_class": "neu", "fig": "%s%s" % (sym, "{:,}".format(int(round(cost)))),
         "cap": "labour cost avoided",
         "sub": "%.1f hours and %.1f working days of inspection time, valued at %s %d/hr."
                % (mins / 60, mins / 60 / HOURS_PER_DAY, code, per_hr),
         "order": 4},
    ]

    # Chart 1: six months of the site score
    trend = [site_m[m[:7]] for m in tm if m[:7] in site_m]
    values = [io.pct(r["score"], 1) for r in trend]
    tmonths = [m for m in tm if m[:7] in site_m]
    th = io.thresholds(values, BANDS)
    trend_eh = {"values": values, "thresholds": th, "dp": 1, "note_after": "Site equipment health score",
                "alt": io.line_alt("site equipment health score", tmonths, values, th, 1)}

    # Chart 2: checks and labour cost by month, each month priced over its own days
    by_month = defaultdict(list)
    for r in work.get("eh/priority-month.json").rows:
        by_month[month_of(r)].append(r)
    a, b, rule_counts = [], [], []
    for m in tm:
        rs = by_month.get(m[:7], [])
        mdays = (io.add_months(io.d(m), 1) - io.d(m)).days
        a.append(sum(r.get("total_executions") or 0 for r in rs))
        b.append(int(round(sum((r.get("task_count") or 0) * ANNUAL_MINS.get(r.get("priority_id"), 4.0)
                               for r in rs) * mdays / 365 / 60 * per_hr)))
        rule_counts.append(sum(r.get("task_count") or 0 for r in rs))
    money = "dollars" if sym == "$" else ("pounds" if sym == "£" else "euros")
    trend_checks = {"a": a, "b": b, "labels_a": [io.compact(v) for v in a],
                    "labels_b": ["%s%.1fk" % (sym, v / 1000) for v in b], "note_after": "Automated health checks",
                    "alt": "Grouped bar chart, %s. Automated checks: %s and %s million. Labour cost avoided: %s and %s thousand %s."
                           % (io.span(tm[0], tm[-1], sep=" to "), ", ".join("%.2f" % (v / 1e6) for v in a[:-1]), "%.2f" % (a[-1] / 1e6),
                              ", ".join("%.1f" % (v / 1e3) for v in b[:-1]), "%.1f" % (b[-1] / 1e3), money)}

    # facts the three notes are written from
    movers = [r for r in rows if None not in (r["months"][0], r["months"][-1])]
    up = sorted(movers, key=lambda r: r["months"][-1] - r["months"][0], reverse=True)
    down = sorted(movers, key=lambda r: r["months"][-1] - r["months"][0])
    weak = [r for r in rows if r["months"][-1] is not None and r["months"][-1] < 97]
    rule_shift = []
    for r in type_all.rows:
        tid = r["metadata_type_id"]
        f, l = scores[tid].get(qm[0][:7]), scores[tid].get(qm[-1][:7])
        if tid not in SYSTEM_TYPES and f and l and (l.get("task_count") or 0) != (f.get("task_count") or 0):
            rule_shift.append("%s %d to %d rules" % (names.get(tid, tid), f.get("task_count") or 0, l.get("task_count") or 0))
    fmt = lambda r: "%s %.2f%% to %.2f%% (%+.2f pp)" % (r["name"], r["months"][0], r["months"][-1],
                                                       r["months"][-1] - r["months"][0])
    facts = [
        "Equipment health: site %.2f%% over the quarter (%s); %s %.2f%% to %s %.2f%%."
        % (score, band(score), io.month(qm[0]), site_q[0], io.month(qm[-1]), site_q[-1]),
        "Biggest rises: " + ("; ".join(fmt(r) for r in up[:3] if r["months"][-1] > r["months"][0]) or "none"),
        "Biggest falls: " + ("; ".join(fmt(r) for r in down[:3] if r["months"][-1] < r["months"][0]) or "none"),
        "Below Good in %s: " % io.month(qm[-1]) + ("; ".join("%s %.2f%% (%s)" % (r["name"], r["months"][-1], band(r["months"][-1]))
                                                         for r in weak) or "none"),
        "Rule count changes across the quarter: " + ("; ".join(rule_shift) or "none"),
        "Site score by month, %s: %s." % (io.span(tm[0], tm[-1], short=True), ", ".join("%.1f%%" % v for v in values)),
        "Scored rules by month: %s." % ", ".join("{:,}".format(v) for v in rule_counts),
        "Checks by month: %s; labour cost by month: %s." % (", ".join(io.compact(v) for v in a),
                                                           ", ".join("%s%s" % (sym, "{:,}".format(v)) for v in b)),
    ]
    return {
        "impact": impact,
        "equipment_health": heat,
        "trend_eh": trend_eh,
        "trend_checks": trend_checks,
        "links": {"equipment_health": link, "trend_eh": work.get("eh/site-month.json").link},
        "datelines": {"Equipment health snapshot":
                      "%s, the three months of the reporting quarter. Share of rule executions returning no fault, "
                      "by equipment type, sorted by change across the quarter." % io.span(qm[0], qm[-1]),
                      "Monthly equipment health": "%s, the last six complete months." % io.span(tm[0], tm[-1])},
        "notes": {"Labour cost avoided":
                  "<strong>Labour cost avoided.</strong> Each rule replaces a manual inspection at a set frequency by "
                  "priority: P1 daily at 0.5 minutes per check; P2 weekly, P3 monthly and P4–5 quarterly at 1 minute. "
                  "Savings prorate that annual effort over the %d-day period, valued at %s %d/hr for this site's "
                  "region. A working day is taken as %.1f hours." % (days, code, per_hr, HOURS_PER_DAY)},
        "prose": {
            "eh_snapshot": "The note under the health-by-type heatmap: what moved across the quarter and why.",
            "eh_score_trend": "The note under Chart 1, the six-month site score: the direction, and any step change "
                              "and its cause (a rule count change is often the cause, not the building).",
            "eh_checks_trend": "The note under Chart 2, checks and labour cost by month: what moved the volume.",
        },
        "facts": facts,
    }
