#!/usr/bin/env python3
"""Thermal comfort by site: the ranked heatmap and its portfolio row, with the sites'
leaderboard month scores handed on as a ranking and the zone points that scored as
the thermal zones figure. See
references/portfolio-leaderboard/indoor-environment/indoor-environment.md.
"""
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "scripts"))
import peak_io as io  # noqa: E402
import portfolio_io as pio  # noqa: E402

ANCHOR = "cf-by-site"
BANDS = [92, 85, 75]
LOW_ZONES, LOW_NOTE = 20, "Low zone count"      # too few zones to lead: ranked after the other sites
CHUNK, PAGE = 100, 80


def paged(ctx):
    q0, q1 = ctx["quarter"]
    ie = lambda name, ent: pio.split(ctx, name, CHUNK, lambda f, ids: io.call(
        f, "search_indoor_environment", metric="temperature", site_ids=ids, aggregate_entity=ent,
        aggregate_period="month" if ent == "site" else "all", local_start_date=q0, local_end_date=q1, limit=PAGE))
    return ie("ie/site-month.json", "site") + ie("ie/level-all.json", "level")


def calls(ctx):
    # Zones: each site's zone points with a reading, the pagination total of a one-row page, a call a site
    q0, q1 = ctx["quarter"]
    return paged(ctx) + pio.split(ctx, "ie/zones-scored.json", 1, lambda f, ids: io.call(
        f, "search_indoor_environment", metric="temperature", site_ids=ids, aggregate_entity="zone",
        aggregate_period="all", local_start_date=q0, local_end_date=q1, limit=1))


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
    files = set(pio.chunk_files(work, "ie/zones-scored.json"))
    points = {io.call_args(c)["site_ids"][0]: work.get(c["file"]).total or 0 for c in work.calls if c["file"] in files}
    zones = lambda sid: points.get(sid, 0)

    months, scored, missing = pio.quarter_scores(ctx, scores)
    if not scored:
        return {"drop": True}

    sids = [s["site_id"] for s in scored]
    pio.shown(shared, sids)
    shared["thermal_zones"] = sum(zones(sid) for sid in sids)
    now = {sid: months[sid][-1] for sid in sids}           # the leaderboard month
    start = {sid: months[sid][-2] for sid in sids}         # the month last month's board ranked
    low = pio.low_coverage({sid: zones(sid) for sid in sids}, LOW_ZONES)
    order = pio.board_order(scored, now, low)

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
             "months": months[s["site_id"]], "low": s["site_id"] in low} for k, s in order]
    portfolio, change, left = pio.portfolio_months({sid: scores[sid] for sid in sids}, [m[:7] for m in qm])
    heat = {"unit": unit, "dp": 1, "bands": BANDS, "counts": ["Levels", "Zones"], "rows": rows,
            "band_unit": t_units.pop() if len(t_units) == 1 else "",
            "portfolio": {"size": pio.size_total(size, sids),
                          "counts": ["{:,}".format(sum(len(levels[sid]) for sid in sids)),
                                     "{:,}".format(shared["thermal_zones"])],
                          "months": portfolio, "change": change}}
    if not any(r["band"] for r in rows):
        heat.pop("band_unit")
    if low:
        heat["note"] = "* %s, ranked after the other sites." % LOW_NOTE
    shared.setdefault("rankings", []).append({"label": "Thermal comfort", "anchor": ANCHOR, "window": "month",
                                              "now": now, "start": start, "dp": 1, "unit": "%",
                                              "low": sorted(low), "low_note": LOW_NOTE})

    chat = []
    if low:
        starred = ["%s (%s)" % (s["site_name"].strip(), io.plural(zones(s["site_id"]), "zone")) for _, s in order
                   if s["site_id"] in low]
        chat.append("Too few thermal zones to lead, so ranked after the other sites on the thermal comfort board "
                    "and table, starred: %s." % io.listing(starred))
    if missing:
        chat.append("No thermal comfort score from %s to %s for %s: left out of the thermal comfort table and "
                    "ranking." % (io.month(qm[0]), io.month(qm[-1]), io.listing(missing)))
    note = ("%s. Share of zone readings inside the site's comfort band during working hours.%s"
            % (pio.reporting_period(ctx), pio.chg_note(ctx, sids, left)))
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
