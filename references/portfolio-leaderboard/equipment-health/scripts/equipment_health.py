#!/usr/bin/env python3
"""Equipment health by site: the ranked heatmap and its portfolio row, with the sites'
leaderboard month scores handed on as a ranking and its equipment and rules totals as
the scored equipment and rules figures. See
references/portfolio-leaderboard/equipment-health/equipment-health.md for what each
figure means; this module is that reference's arithmetic.
"""
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "scripts"))
import peak_io as io  # noqa: E402
import portfolio_io as pio  # noqa: E402

ANCHOR = "eh-by-site"
BANDS = [99, 97, 90]
LOW_RULES, LOW_NOTE = 50, "Low rules count"     # too few scored rules to lead: ranked after the other sites
# Each call scans every rule's month rows for its sites, and PEAK refuses a call over 200,000 rows:
# about 10,000 a site over a quarter, three times that at the largest. Six sites a call keeps inside it.
CHUNK = 6


def calls(ctx):
    q0, q1 = ctx["quarter"]
    eh = lambda name, size, ent, per, **kw: pio.split(ctx, name, size, lambda f, ids: io.call(
        f, "search_equipment_health_scores", site_ids=ids, aggregate_entities=ent, aggregate_period=per,
        local_start_date=q0, local_end_date=q1, **kw))
    return (eh("eh/type-month.json", CHUNK, ["metadata_type"], "month")
            + eh("eh/type-all.json", CHUNK, ["metadata_type"], "all", select_equipment_count=True))


def more(ctx, work):
    return []


def build(ctx, work, shared):
    qm = ctx["quarter_months"]
    size, unit, _ = pio.sizes(ctx, shared["facts"])
    month_of = lambda r: (r.get("date") or "")[:7]

    # each site's month, rolled up from its equipment types with the BACER left out
    scores, rules_by_month = defaultdict(dict), defaultdict(dict)
    for r in io.rollup(pio.rows(work, "eh/type-month.json"), "site_id", "date"):
        scores[r["site_id"]][month_of(r)] = r["score"] * 100
        rules_by_month[r["site_id"]][month_of(r)] = r["task_count"]
    rules, equip = defaultdict(int), defaultdict(int)
    for r in io.rollup(pio.rows(work, "eh/type-all.json"), "site_id"):
        rules[r["site_id"]], equip[r["site_id"]] = r["task_count"], r["equipment_count"]

    months, scored, missing = pio.quarter_scores(ctx, scores)
    if not scored:
        return {"drop": True}

    pio.shown(shared, [s["site_id"] for s in scored])
    now = {s["site_id"]: months[s["site_id"]][-1] for s in scored}         # the leaderboard month
    start = {s["site_id"]: months[s["site_id"]][-2] for s in scored}       # the month last month's board ranked
    low = pio.low_coverage({s["site_id"]: rules[s["site_id"]] for s in scored}, LOW_RULES)
    order = pio.board_order(scored, now, low)

    host = io.host(*ctx["sites"])
    link = lambda sid: ("%s/dashboard/equipment-health?site_ids=%s&start_date=%sT00:00:00.000&end_date=%sT00:00:00.000"
                        % (host, sid, ctx["quarter"][0], ctx["through"]))
    rows = [{"rank": k, "name": s["site_name"].strip(), "state": pio.region(ctx, s), "link": link(s["site_id"]),
             "size": pio.num(size[s["site_id"]]),
             "counts": ["{:,}".format(equip[s["site_id"]]), "{:,}".format(rules[s["site_id"]])],
             "months": months[s["site_id"]], "low": s["site_id"] in low} for k, s in order]
    sids = [s["site_id"] for s in scored]
    portfolio, change, left = pio.portfolio_months({sid: scores[sid] for sid in sids}, [m[:7] for m in qm])
    shared["scored_equipment"] = sum(equip[sid] for sid in sids)
    shared["scored_rules"] = sum(rules[sid] for sid in sids)
    heat = {"unit": unit, "dp": 1, "bands": BANDS, "counts": ["Equip", "Rules"], "rows": rows,
            "portfolio": {"size": pio.size_total(size, sids),
                          "counts": ["{:,}".format(shared["scored_equipment"]),
                                     "{:,}".format(shared["scored_rules"])],
                          "months": portfolio, "change": change}}
    if low:
        heat["note"] = "* %s, ranked after the other sites." % LOW_NOTE
    shared.setdefault("rankings", []).append({"label": "Equipment health", "anchor": ANCHOR, "window": "month",
                                              "now": now, "start": start, "dp": 1, "unit": "%",
                                              "low": sorted(low), "low_note": LOW_NOTE})

    chat = []
    if low:
        starred = ["%s (%s)" % (s["site_name"].strip(), io.plural(rules[s["site_id"]], "rule")) for _, s in order
                   if s["site_id"] in low]
        chat.append("Too few scored rules to lead, so ranked after the other sites on the equipment health board "
                    "and table, starred: %s." % io.listing(starred))
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
    note = "%s. Share of automated checks that found no fault.%s" % (pio.reporting_period(ctx),
                                                                      pio.chg_note(ctx, sids, left))
    return {
        "equipment_health": heat,
        "datelines": {"Equipment health snapshot": note},
        "chat": chat,
    }
