#!/usr/bin/env python3
"""Thermal comfort by site: the ranked heatmap and its portfolio row, with the sites'
leaderboard month scores handed on as a ranking and the zone points as the thermal
zones figure. See
references/portfolio-leaderboard/indoor-environment/indoor-environment.md.
"""
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "scripts"))
import peak_io as io  # noqa: E402
import portfolio_io as pio  # noqa: E402

NAME = "indoor-environment"
ANCHOR = "cf-by-site"
BANDS = [92, 85, 75]
CHUNK, PAGE = 100, 80
ZONE_CHUNK = 10              # the zone count returns a row per level and refuses a response over 40,000 characters


def paged(ctx):
    q0, q1 = ctx["quarter"]
    ie = lambda name, ent: pio.split(ctx, name, CHUNK, lambda f, ids: io.call(
        f, "search_indoor_environment", metric="temperature", site_ids=ids, aggregate_entity=ent,
        aggregate_period="month" if ent == "site" else "all", local_start_date=q0, local_end_date=q1, limit=PAGE))
    return ie("ie/site-month.json", "site") + ie("ie/level-all.json", "level")


def calls(ctx):
    return paged(ctx) + pio.split(ctx, "ie/zones-by-level.json", ZONE_CHUNK, lambda f, ids: io.call(
        f, "count_indoor_environment_zones", metric="temperature", site_ids=ids, aggregate_entity="level"))


def more(ctx, work):
    return io.pages_due(work, paged(ctx))


def build(ctx, work, shared):
    qm = ctx["quarter_months"]
    size, unit, _ = pio.sizes(ctx, shared["facts"])
    month_of = lambda r: (r.get("date") or "")[:7]

    scores = defaultdict(dict)
    for r in pio.rows(work, "ie/site-month.json"):
        scores[r["site_id"]][month_of(r)] = r["score"] * 100
    levels, units = defaultdict(set), {}
    for r in pio.rows(work, "ie/level-all.json"):
        levels[r["site_id"]].add(r["level_id"])
        units.setdefault(r["site_id"], r.get("unit"))
    points = {}
    for r in pio.rows(work, "ie/zones-by-level.json"):
        points[r["level_id"]] = (r["site_id"], r.get("included_point_count") or 0)
    zones = lambda sid: sum(points.get(l, (sid, 0))[1] for l in levels[sid])
    shared["zones_configured"] = sum(n for _, n in points.values())

    months = lambda sid: [scores[sid].get(m[:7]) for m in qm]
    scored = [s for s in ctx["sites"] if any(v is not None for v in months(s["site_id"]))]
    missing = [s["site_name"].strip() for s in ctx["sites"] if s not in scored]
    if not scored:
        return {"drop": [NAME]}

    sids = [s["site_id"] for s in scored]
    pio.shown(shared, sids)
    shared["thermal_zones"] = sum(zones(sid) for sid in sids)
    now = {sid: months(sid)[-1] for sid in sids}           # the leaderboard month
    start = {sid: months(sid)[-2] for sid in sids}         # the month last month's board ranked
    ranked = pio.rank(scored, lambda s: now[s["site_id"]])
    tail = sorted((s for s in scored if now[s["site_id"]] is None), key=pio.name_key)
    order = ranked + [(len(ranked) + k, s) for k, s in enumerate(tail, 1)]

    host = io.host(*ctx["sites"])
    link = lambda sid: ("%s/indoor-environment/thermal-comfort?summary_site_id=%s&summary_ts=%s&site_ids=%s"
                        "&start_date=%sT00:00:00.000&end_date=%sT00:00:00.000"
                        % (host, sid, qm[-1], sid, ctx["quarter"][0], ctx["through"]))
    # each site's comfort band as its default in PEAK sets it, in the site's own unit
    unit_t = lambda sid: units.get(sid) or ("°F" if io.in_feet((shared["facts"].get(sid) or {}).get("country")) else "°C")
    t_units = {unit_t(s["site_id"]) for s in scored}
    rows = [{"rank": k, "name": s["site_name"].strip(), "state": pio.region(ctx, s), "link": link(s["site_id"]),
             "size": pio.num(size[s["site_id"]]),
             "counts": ["{:,}".format(len(levels[s["site_id"]])), "{:,}".format(zones(s["site_id"]))],
             "band": band_text(shared["facts"].get(s["site_id"]) or {}, unit_t(s["site_id"]) if len(t_units) > 1 else None),
             "months": months(s["site_id"])} for k, s in order]
    portfolio, change, left = pio.portfolio_months({sid: scores[sid] for sid in sids}, [m[:7] for m in qm])
    shown_size = [size[sid] for sid in sids if size[sid]]
    heat = {"unit": unit, "dp": 1, "bands": BANDS, "counts": ["Levels", "Zones"], "rows": rows,
            "band_unit": t_units.pop() if len(t_units) == 1 else "",
            "portfolio": {"size": pio.num(sum(shown_size)) if shown_size else "-",
                          "counts": ["{:,}".format(sum(len(levels[sid]) for sid in sids)),
                                     "{:,}".format(shared["thermal_zones"])],
                          "months": portfolio, "change": change}}
    if not any(r["band"] for r in rows):
        heat.pop("band_unit")
    shared.setdefault("rankings", []).append({"label": "Thermal comfort", "anchor": ANCHOR, "window": "month",
                                              "now": now, "start": start, "dp": 1, "unit": "%"})

    chat = []
    if missing:
        chat.append("No thermal comfort score from %s to %s for %s: left out of the thermal comfort table and "
                    "ranking." % (io.month(qm[0]), io.month(qm[-1]), io.listing(missing)))
    note = ("%s. Share of zone readings inside the site's comfort band during working hours."
            % pio.reporting_period(ctx))
    if left and len(sids) - len(left) > 0:
        note += " Its Chg compares the %s scored in both %s and %s." % (
            io.plural(len(sids) - len(left), "site"), io.month(qm[0]), io.month(qm[-1]))
    return {
        "comfort": heat,
        "datelines": {"Indoor environment health snapshot": note},
        "chat": chat,
    }


def band_text(fact, unit=None):
    """'21-24.9': the site's default comfort band in PEAK, its unit added where the table's sites differ;
    None where PEAK holds no band."""
    lo, hi = fact.get("thermal_comfort_min_temp"), fact.get("thermal_comfort_max_temp")
    if lo is None or hi is None:
        return None
    num = lambda v: ("%.1f" % v).rstrip("0").rstrip(".")
    return "%s%s%s%s" % (num(lo), " to " if lo < 0 or hi < 0 else "-", num(hi), " %s" % unit if unit else "")
