#!/usr/bin/env python3
"""Equipment health by site: the ranked heatmap and its portfolio row, and the sites'
leaderboard month scores handed on as a ranking. See
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
ANCHOR = "eh-by-site"
BANDS = [99, 97, 90]
# Each call scans every rule's month rows for its sites, and PEAK refuses a call over 200,000 rows:
# about 10,000 a site over a quarter, three times that at the largest. Six sites a call keeps inside it.
CHUNK = 6


def calls(ctx):
    q0, q1 = ctx["quarter"]
    eh = lambda name, size, ent, per: pio.split(ctx, name, size, lambda f, ids: io.call(
        f, "search_equipment_health_scores", site_ids=ids, aggregate_entities=ent, aggregate_period=per,
        local_start_date=q0, local_end_date=q1))
    return (eh("eh/site-month.json", CHUNK, ["site"], "month")
            + eh("eh/type-all.json", CHUNK, ["metadata_type"], "all")
            + eh("eh/equipment-all.json", CHUNK, ["equipment"], "all"))


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
        if r.get("metadata_type_id") not in io.SYSTEM_TYPES:
            rules[r["site_id"]] += r.get("task_count") or 0
    for r in pio.rows(work, "eh/equipment-all.json"):
        if r.get("metadata_type_id") not in io.SYSTEM_TYPES:
            equip[r["site_id"]].add(r["equipment_id"])

    months = lambda sid: [scores[sid].get(m[:7]) for m in qm]
    scored = [s for s in ctx["sites"] if any(v is not None for v in months(s["site_id"]))]
    missing = [s["site_name"].strip() for s in ctx["sites"] if s not in scored]
    if not scored:
        return {"drop": [NAME]}

    pio.shown(shared, [s["site_id"] for s in scored])
    now = {s["site_id"]: months(s["site_id"])[-1] for s in scored}         # the leaderboard month
    start = {s["site_id"]: months(s["site_id"])[-2] for s in scored}       # the month last month's board ranked
    ranked = pio.rank(scored, lambda s: now[s["site_id"]])
    tail = sorted((s for s in scored if now[s["site_id"]] is None), key=pio.name_key)
    order = ranked + [(len(ranked) + k, s) for k, s in enumerate(tail, 1)]

    host = pio.host(ctx)
    link = lambda sid: ("%s/dashboard/equipment-health?site_ids=%s&start_date=%sT00:00:00.000&end_date=%sT00:00:00.000"
                        % (host, sid, ctx["quarter"][0], ctx["through"]))
    rows = [{"rank": k, "name": s["site_name"].strip(), "state": pio.region(ctx, s), "link": link(s["site_id"]),
             "size": pio.num(size[s["site_id"]]),
             "counts": ["{:,}".format(len(equip[s["site_id"]])), "{:,}".format(rules[s["site_id"]])],
             "months": months(s["site_id"])} for k, s in order]
    sids = [s["site_id"] for s in scored]
    portfolio, change, left = pio.portfolio_months({sid: scores[sid] for sid in sids}, [m[:7] for m in qm])
    shown_size = [size[sid] for sid in sids if size[sid]]
    heat = {"unit": unit, "dp": 1, "bands": BANDS, "counts": ["Equip", "Rules"], "rows": rows,
            "portfolio": {"size": pio.num(sum(shown_size)) if shown_size else "-",
                          "counts": ["{:,}".format(sum(len(equip[sid]) for sid in sids)),
                                     "{:,}".format(sum(rules[sid] for sid in sids))],
                          "months": portfolio, "change": change}}
    shared.setdefault("rankings", []).append({"label": "Equipment health", "anchor": ANCHOR, "window": "month",
                                              "now": now, "start": start, "dp": 1, "unit": "%"})

    chat = []
    if missing:
        chat.append("No equipment health score from %s to %s for %s: left out of the equipment health table and "
                    "ranking." % (io.month(qm[0]), io.month(qm[-1]), io.listing(missing)))
    # A month that scored off under half of a site's busiest month is an outage, or rules still going live:
    # either way its score covers part of the plant, and it moves the site's change, its place on the board
    # and the portfolio row.
    for s in scored:
        n = [rules_by_month[s["site_id"]].get(m[:7], 0) for m in qm]
        most = max(n)
        low = ["%s %s" % (io.month(m), "{:,}".format(x)) for m, x in zip(qm, n) if x and x < most / 2]
        if low:
            chat.append("Equipment health at %s scored off far fewer rules in some months: %s, against %s in its "
                        "busiest. Those months cover part of the plant, from an outage or rules still going live, so "
                        "its change and its place on the board are not the plant's alone."
                        % (s["site_name"].strip(), io.listing(low), "{:,}".format(most)))
    note = ("%s. Share of automated checks that found no fault. Equip and Rules count the equipment and rules "
            "scored; the portfolio row averages the sites." % pio.reporting_period(ctx))
    if left and len(sids) - len(left) > 0:
        note += " Its Chg compares the %s scored in both %s and %s." % (
            pio.site_count(len(sids) - len(left)), io.month(qm[0]), io.month(qm[-1]))
    return {
        "equipment_health": heat,
        "datelines": {"Equipment health snapshot": note},
        "chat": chat,
    }
