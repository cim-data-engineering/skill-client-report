#!/usr/bin/env python3
"""Equipment health by site: the ranked heatmap, its portfolio row, and the figures
the equipment health board ranks on. See
references/portfolio-leaderboard/equipment-health/equipment-health.md for what each
figure means; this module is that reference's arithmetic.
"""
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "scripts"))
import peak_io as io  # noqa: E402
import portfolio_io as pio  # noqa: E402

NAME = "equipment-health"
SYSTEM_TYPES = {21, 37, 69, 70, 87, 105, 114}     # the platform checking itself, not plant
BANDS = [99, 97, 90]
CHUNK, EQUIPMENT_CHUNK = 100, 10                 # equipment rows run long, so their calls take fewer sites


def calls(ctx):
    q0, q1 = ctx["quarter"]
    eh = lambda name, size, ent, per: pio.split(ctx, name, size, lambda f, ids: io.call(
        f, "search_equipment_health_scores", site_ids=ids, aggregate_entities=ent, aggregate_period=per,
        local_start_date=q0, local_end_date=q1))
    return (eh("eh/site-month.json", CHUNK, ["site"], "month")
            + eh("eh/type-all.json", CHUNK, ["metadata_type"], "all")
            + eh("eh/equipment-all.json", EQUIPMENT_CHUNK, ["equipment"], "all"))


def more(ctx, work):
    return []


def build(ctx, work, shared):
    qm = ctx["quarter_months"]
    size, unit, _ = pio.sizes(ctx, shared["facts"])
    month_of = lambda r: (r.get("date") or "")[:7]

    scores, rules_by_month = defaultdict(dict), defaultdict(dict)
    for r in pio.rows(work, "eh/site-month.json"):
        scores[r["site_id"]][month_of(r)] = r["score"] * 100
        rules_by_month[r["site_id"]][month_of(r)] = r.get("task_count") or 0
    rules, equip = defaultdict(int), defaultdict(set)
    for r in pio.rows(work, "eh/type-all.json"):
        if r.get("metadata_type_id") not in SYSTEM_TYPES:
            rules[r["site_id"]] += r.get("task_count") or 0
    for r in pio.rows(work, "eh/equipment-all.json"):
        if r.get("metadata_type_id") not in SYSTEM_TYPES:
            equip[r["site_id"]].add(r["equipment_id"])

    months = lambda sid: [scores[sid].get(m[:7]) for m in qm]
    scored = [s for s in ctx["sites"] if any(v is not None for v in months(s["site_id"]))]
    missing = [s["site_name"].strip() for s in ctx["sites"] if s not in scored]
    if not scored:
        return {"drop": [NAME]}

    now = {s["site_id"]: months(s["site_id"])[-1] for s in scored}
    start = {s["site_id"]: months(s["site_id"])[0] for s in scored}
    ranked = pio.rank(scored, lambda s: now[s["site_id"]])
    tail = sorted((s for s in scored if now[s["site_id"]] is None), key=pio.name_key)
    order = ranked + [(len(ranked) + k, s) for k, s in enumerate(tail, 1)]

    host = pio.host(ctx)
    link = lambda sid: ("%s/dashboard/equipment-health?site_ids=%s&start_date=%sT00:00:00.000&end_date=%sT00:00:00.000"
                        % (host, sid, ctx["quarter"][0], ctx["through"]))
    rows = [{"rank": k, "name": s["site_name"].strip(), "state": pio.state(s), "link": link(s["site_id"]),
             "size": pio.num(size[s["site_id"]]),
             "counts": ["{:,}".format(len(equip[s["site_id"]])), "{:,}".format(rules[s["site_id"]])],
             "months": months(s["site_id"])} for k, s in order]
    sids = [s["site_id"] for s in scored]
    portfolio = [pio.weighted({sid: scores[sid].get(m[:7]) for sid in sids}, size) for m in qm]
    shown_size = [size[sid] for sid in sids if size[sid]]
    heat = {"unit": unit, "dp": 1, "bands": BANDS, "counts": ["Equip", "Rules"], "rows": rows,
            "portfolio": {"size": pio.num(sum(shown_size)) if shown_size else "-",
                          "counts": ["{:,}".format(sum(len(equip[sid]) for sid in sids)),
                                     "{:,}".format(sum(rules[sid] for sid in sids))],
                          "months": portfolio}}
    if any(v is not None for v in portfolio):
        shared["weighted"] = True
    shared.setdefault("boards", {})[NAME] = {"now": now, "start": start, "dp": 1}

    chat = []
    if missing:
        chat.append("No equipment health score this quarter for %s: left out of the equipment health table and "
                    "board." % io.listing(missing))
    # A month that scored off a fraction of a site's usual rules is a data outage wearing a score.
    for s in scored:
        n = [rules_by_month[s["site_id"]].get(m[:7], 0) for m in qm]
        live = sorted(x for x in n if x)
        usual = live[len(live) // 2] if live else 0
        low = ["%s scored %s" % (io.month_label(ctx, m), "{:,} rule{}".format(x, "" if x == 1 else "s"))
               for m, x in zip(qm, n) if x and x < usual / 2]
        if low:
            chat.append("Equipment health data was out for part of the quarter at %s: %s, against about %s scored "
                        "rules in its other months. That is an outage, not a score." % (
                            s["site_name"].strip(), io.listing(low), "{:,}".format(usual)))
    return {
        "equipment_health": heat,
        "datelines": {"Equipment health snapshot": "%s. Share of rule executions returning no fault."
                                                   % pio.reporting_period(ctx)},
        "notes": {"Scored equipment": {"order": 2, "html": "<strong>Scored equipment.</strong> Equip and Rules count "
                                                           "equipment and rules that scored in the period, so they can "
                                                           "sit below the monitored totals in the scorecards."}},
        "chat": chat,
    }
