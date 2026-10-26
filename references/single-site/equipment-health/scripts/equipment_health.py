#!/usr/bin/env python3
"""Equipment health: three operational impact rows, the snapshot heatmap and
both monthly charts, from the section's saved calls. See
references/single-site/equipment-health/equipment-health.md for what each figure means;
this module is that reference's arithmetic.
"""
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "scripts"))
import peak_io as io  # noqa: E402

HANDS_ON = ["scored_equipment", "scored_rules"]   # known at plan time, so the overview fetches no counts of its own
BANDS = [(99.0, "Excellent"), (97.0, "Good"), (90.0, "Average")]
# Labour model: annual minutes saved per scored rule, by priority id, priced at the region's hourly rate
# by currency code over a 7.5-hour working day.
ANNUAL_MINS = {1: 365 * 0.5, 2: 52 * 1.0, 3: 12 * 1.0, 4: 4 * 1.0, 5: 4 * 1.0}
LABOUR_RATES = {"AUD": 150, "USD": 100, "NZD": 150, "GBP": 75, "CAD": 150, "EUR": 100, "SGD": 120, "CHF": 120,
                "SEK": 900, "BRL": 250, "CNY": 300, "IDR": 500000}
WORKING_DAY = 7.5
MONEY = {"AUD": "dollars", "USD": "dollars", "NZD": "dollars", "CAD": "dollars", "SGD": "dollars", "GBP": "pounds",
         "EUR": "euros", "CHF": "francs", "SEK": "kronor", "BRL": "reais", "CNY": "yuan", "IDR": "rupiah"}


def calls(ctx):
    sid, (q0, q1), (t0, t1) = ctx["site"]["site_id"], ctx["quarter"], ctx["trend"]
    eh = lambda f, ent, per, a, b, **kw: io.call(f, "search_equipment_health_scores", site_ids=[sid],
                                                aggregate_entities=ent, aggregate_period=per,
                                                local_start_date=a, local_end_date=b, **kw)
    return [
        io.gql("eh/types.json", "platform.metadata_types", {"limit": 400}, ["type_id", "type"]),
        eh("eh/type-month.json", ["metadata_type"], "month", t0, t1),
        eh("eh/type-all.json", ["metadata_type"], "all", q0, q1, select_equipment_count=True),
        eh("eh/type-priority-month.json", ["metadata_type", "priority"], "month", t0, t1),
    ]


def more(ctx, work):
    # A site that went live inside the quarter takes its headline score and its counts over the months it kept
    on = onboarding(ctx, site_months(work))
    if on and on["start"] > ctx["quarter"][0] and not work.has("eh/type-all-live.json"):
        return [io.call("eh/type-all-live.json", "search_equipment_health_scores", site_ids=[ctx["site"]["site_id"]],
                        aggregate_entities=["metadata_type"], aggregate_period="all", local_start_date=on["start"],
                        local_end_date=ctx["quarter"][1], select_equipment_count=True)]
    return []


def site_months(work):
    """{"YYYY-MM": the site's month}, rolled up from its equipment types with the BACER left out."""
    return {(r.get("date") or "")[:7]: r for r in io.rollup(work.get("eh/type-month.json").rows, "date")}


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


def compact(n, dp=2):
    """1834812 -> '1.83M', 7340 -> '7.3k'."""
    if n >= 1e6:
        return "%.*fM" % (dp, n / 1e6)
    if n >= 1e3:
        return "%.1fk" % (n / 1e3)
    return "%d" % n


def words(n, dp=2):
    """1834812 -> '1.83 million', for running text."""
    if n >= 1e6:
        return "%.*f million" % (dp, n / 1e6)
    return "{:,}".format(int(round(n)))


def month_of(r):
    return (r.get("date") or "")[:7]


def snapshot(ctx, work, kq, site_q, link, live):
    """The heatmap: a row per equipment type with a scored rule, its equipment and rules counted over the
    months it shows, sorted by change across the period (one month: the lowest leads), closed by the site row."""
    names = {r["type_id"]: r["type"] for r in work.get("eh/types.json").rows}
    scores = defaultdict(dict)
    for r in work.get("eh/type-month.json").rows:
        scores[r["metadata_type_id"]][month_of(r)] = r
    rows = []
    for r in work.get("eh/type-all-live.json" if live else "eh/type-all.json").rows:
        tid = r["metadata_type_id"]
        if tid == io.BACER:
            continue
        months = [io.pct(scores[tid][m[:7]]["score"], 1) if m[:7] in scores[tid] else None for m in kq]
        if all(v is None for v in months):
            continue
        rows.append({"name": names.get(tid, "Type %d" % tid), "type_id": tid,
                     "link": link + "&equipment_type_ids=%d" % tid,
                     "counts": [r.get("equipment_count") or 0, r.get("task_count") or 0], "months": months})
    if len(kq) > 1:
        chg = lambda r: (r["months"][-1] - r["months"][0]) if None not in (r["months"][0], r["months"][-1]) else -1e9
        rows.sort(key=lambda r: (-chg(r), -(r["months"][-1] or 0), r["name"]))   # ties: the higher score leads
    else:
        rows.sort(key=lambda r: (r["months"][0], r["name"]))      # one month: the lowest leads
    return {"label": "Equipment type", "dp": 1, "bands": [99, 97, 90], "counts": ["Equip", "Rules"],
            "months": [io.mon(m) for m in kq], "to_date": kq[-1] == ctx["to_date"],
            "rows": [{k: v for k, v in r.items() if k != "type_id"} for r in rows],
            "site": {"counts": [sum(r["counts"][0] for r in rows), sum(r["counts"][1] for r in rows)],
                     "months": site_q}}


def by_month(ctx, work, kt, per_hr):
    """(checks, labour minutes, labour cost, scored rules) for each trend month, each priced over its own days."""
    rows = defaultdict(list)
    for r in io.rollup(work.get("eh/type-priority-month.json").rows, "date", "priority_id"):
        rows[month_of(r)].append(r)
    checks_m, mins_m, cost_m, rules_m = {}, {}, {}, {}
    for m in kt:
        rs = rows.get(m[:7], [])
        checks_m[m] = sum(r.get("total_executions") or 0 for r in rs)
        mins_m[m] = sum((r.get("task_count") or 0) * ANNUAL_MINS.get(r.get("priority_id"), 4.0) for r in rs) \
            * io.days_in(ctx, m) / 365
        cost_m[m] = int(round(mins_m[m] / 60 * per_hr))
        rules_m[m] = sum(r.get("task_count") or 0 for r in rs)
    return checks_m, mins_m, cost_m, rules_m


def checks_chart(ctx, kt, checks_m, cost_m, code, sym, note):
    """Chart 2: checks and labour cost by month. A month with no checks scored, an outage or before
    go-live, is a gap, not a zero."""
    a = [checks_m[m] or None for m in kt]
    b = [cost_m[m] if checks_m[m] else None for m in kt]
    alt = lambda v, f: "no data" if v is None else f % v
    return {"a": a, "b": b, "labels_a": [compact(v) if v else "" for v in a],
            "labels_b": ["%s%s" % (sym, compact(v)) if v is not None else "" for v in b],
            "months": [io.mon(m) for m in kt], "to_date": kt[-1] == ctx["to_date"],
            "note_after": "Automated health checks",
            "note": note,
            "alt": "Grouped bar chart, %s. Automated checks: %s million. Labour cost avoided: %s thousand %s."
                   % (io.span(kt[0], kt[-1], sep=" to "), io.listing(alt(v and v / 1e6, "%.2f") for v in a),
                      io.listing(alt(v if v is None else v / 1e3, "%.1f") for v in b), MONEY.get(code, code))
                   + io.to_date_note(ctx, kt)}


def coverage_chat(ctx, kt, rules_m):
    """A month scored off under half the rules of each month beside it, or off none, is a data outage
    wearing a score. A count that rises or falls by half again and holds is a coverage change."""
    seq = [(m, rules_m[m]) for m in kt]
    rules_text = lambda n: "{:,} rule{}".format(n, "" if n == 1 else "s") if n else "none"
    low = [i for i, (m, n) in enumerate(seq)
           if len(seq) > 1 and (n == 0 or all(n < x / 2 for _, x in seq[max(i - 1, 0):i] + seq[i + 1:i + 2]))]
    out = ["%s scored %s" % (io.month_label(ctx, seq[i][0]), rules_text(seq[i][1])) for i in low]
    steps = ["%s scored %s against %s in %s" % (io.month_label(ctx, seq[i][0]), rules_text(seq[i][1]),
                                                "{:,}".format(seq[i - 1][1]), io.month_label(ctx, seq[i - 1][0]))
             for i in range(1, len(seq)) if i not in low and i - 1 not in low
             and max(seq[i][1], seq[i - 1][1]) >= 1.5 * min(seq[i][1], seq[i - 1][1])]
    chat = []
    if out:
        chat.append("Equipment health data was out for part of the window: %s, against the months either side."
                    % io.listing(out))
    if steps:
        chat.append("Equipment health coverage changed, not an outage: %s." % "; ".join(steps))
    return chat


def datelines(ctx, kq, kt):
    if kq == ctx["quarter_months"]:
        snap = ("%s, the three months of the reporting quarter%s. Share of rule executions returning no fault, by "
                "equipment type, sorted by change across the %s."
                % (io.span(kq[0], io.whole(ctx, kq)[-1]), io.and_to_date(ctx), "period" if ctx["to_date"] else "quarter"))
    else:
        snap = ("%s. Share of rule executions returning no fault, by equipment type, %s."
                % (io.months_text(ctx, kq), "sorted by change across the period" if len(kq) > 1 else "lowest first"))
    trend = ("%s, the last six complete months%s." % (io.span(kt[0], io.whole(ctx, kt)[-1]), io.and_to_date(ctx))
             if kt == ctx["trend_months"] else "%s." % io.months_text(ctx, kt))
    return {"Equipment health snapshot": snap, "Monthly equipment health": trend}


def build(ctx, work, shared):
    quarter = io.rollup(work.get("eh/type-all.json").rows)
    if not quarter:
        shared["scored_equipment"] = shared["scored_rules"] = 0     # nothing scored, so nothing counted
        return {"drop": True, "chat": ["Equipment health is left out: PEAK holds no equipment health score for the "
                                       "site in the quarter."]}
    shared.setdefault("partial", []).extend(["automated checks", "labour cost avoided"])
    # a site that went live inside the windows shows only the months it was monitored in full
    site_m = site_months(work)
    on = onboarding(ctx, site_m)
    start, kq, kt = io.kept_months(ctx, on)
    io.hand_on_start(shared, start, kq, on)
    host = io.host(ctx["site"])
    dashboard = lambda start: ("%s/dashboard/equipment-health?site_ids=%s&start_date=%sT00:00:00.000"
                               "&end_date=%sT00:00:00.000" % (host, ctx["site"]["site_id"], start,
                                                              ctx["through"]))
    link = dashboard(kq[0])
    site_q = io.site_scores(site_m, kq)
    live = kq != ctx["quarter_months"] and work.has("eh/type-all-live.json")
    heat = snapshot(ctx, work, kq, site_q, link, live)
    shared["scored_equipment"], shared["scored_rules"] = heat["site"]["counts"]

    # operational impact rows
    score = io.pct((io.rollup(work.get("eh/type-all-live.json").rows) if live else quarter)[0]["score"], 1)
    named = ((shared.get("site_facts") or {}).get("monetary_currency") or "").strip()
    code, sym = io.currency(shared.get("site_facts") or {})
    per_hr = LABOUR_RATES.get(code, 100)
    checks_m, mins_m, cost_m, rules_m = by_month(ctx, work, kt, per_hr)
    full = lambda m: (io.add_months(io.d(m), 1) - io.d(m)).days
    checks = sum(checks_m[m] for m in kq)
    rules = heat["site"]["counts"][1]
    mins, cost, days = sum(mins_m[m] for m in kq), sum(cost_m[m] for m in kq), sum(io.days_in(ctx, m) for m in kq)
    impact = [
        io.score_row(ctx, score, BANDS, kq, site_q, "equipment health maintained", "equipment-health-score"),
        {"chip": "Continuous", "chip_class": "neu", "fig": "{:,}".format(checks),
         "cap": "automated equipment health checks ran 24/7",
         "sub": "Averaging %s monthly checks across %s scored rules." % (
             words(checks / sum(io.days_in(ctx, m) / full(m) for m in kq)), "{:,}".format(rules)),
         "row": "automated-checks"},
        {"chip": "Modelled", "chip_class": "neu", "fig": "%s%s" % (sym, "{:,}".format(cost)),
         "cap": "labour cost avoided",
         "sub": "%.1f hours and %.1f working days of inspection time, valued at %s %d/hr."
                % (mins / 60, mins / 60 / WORKING_DAY, code, per_hr),
         "row": "labour-cost-avoided"},
    ]

    trend_eh, _ = io.trend_line(ctx, kt, site_m, BANDS, "site equipment health score")

    # the labour cost method, worded once for the notes band and the note under Chart 2
    method = lambda window: (
        "<strong>Labour cost avoided.</strong> Assumes each rule replaces one manual check: P1 daily at "
        "30 seconds; P2 weekly, P3 monthly and P4–5 quarterly at 1 minute. Prorated over %s at %s %d/hr "
        "(regional rate) and a %g-hour working day." % (window, code, per_hr, WORKING_DAY))
    trend_checks = checks_chart(ctx, kt, checks_m, cost_m, code, sym,
                                method("each month's days" + (" (%s to date)" % io.month(ctx["to_date"])
                                                              if ctx["to_date"] else "")))

    chat = []
    if on:
        chat.append("Equipment health went live %s, so its figures start with %s." % (
            "on about %s" % io.day_long(on["day"]) if on["day"] else "in %s" % io.month(on["month"]),
            io.month_label(ctx, start)) + ("" if trend_eh else " Too few months for its trend chart."))
    chat += coverage_chat(ctx, kt, rules_m)
    if named.lower() not in io.CURRENCIES:
        chat.append("%s, so labour cost avoided is priced at the US rate in dollars." % (
            "PEAK's currency for the site, %s, is not one the report prices" % named if named
            else "PEAK holds no currency for the site"))

    links = {"equipment_health": link}
    if trend_eh:
        links["trend_eh"] = dashboard(kt[0])
    return dict({
        "impact": impact,
        "equipment_health": heat,
        "trend_eh": trend_eh,
        "trend_checks": trend_checks,
        "links": links,
        "datelines": datelines(ctx, kq, kt),
        "notes": {"Labour cost avoided": method("the %d-day period" % days)},
        "chat": chat,
    }, **({} if kt == ctx["trend_months"] else {"statements": {"Monthly equipment health": "The trend so far"}}))
