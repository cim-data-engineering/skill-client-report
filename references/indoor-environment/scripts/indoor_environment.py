#!/usr/bin/env python3
"""Indoor environment: the thermal comfort impact row, comfort by level and the
six-month comfort trend. See references/indoor-environment/indoor-environment.md.
"""
import os
import re
import sys
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "scripts"))
import peak_io as io  # noqa: E402

NAME = "indoor-environment"
BANDS = [(92.0, "Excellent"), (85.0, "Good"), (75.0, "Average")]
PAGE = 80


def calls(ctx):
    sid, (q0, q1), (t0, t1) = ctx["site"]["site_id"], ctx["quarter"], ctx["trend"]
    ie = lambda f, ent, per, a, b, **kw: io.call(f, "search_indoor_environment", metric="temperature",
                                                site_ids=[sid], aggregate_entity=ent, aggregate_period=per,
                                                local_start_date=a, local_end_date=b, **kw)
    return [
        ie("ie/level-month.json", "level", "month", q0, q1, limit=PAGE),
        ie("ie/site-month.json", "site", "month", t0, t1),
        ie("ie/site-all.json", "site", "all", q0, q1),
        io.call("ie/zones-by-level.json", "count_indoor_environment_zones", metric="temperature",
                site_ids=[sid], aggregate_entity="level"),
    ]


def _pages(base_call, first, prefix):
    """Every further page of a paged call, from the first page's total."""
    total = first.total or 0
    return [dict(base_call, file="%s-%d.json" % (prefix, s), args=dict(base_call["args"], start_index=s))
            for s in range(PAGE, total, PAGE)]


def level_rows(work):
    rows = list(work.get("ie/level-month.json").rows)
    s = PAGE
    while work.has("ie/level-month-%d.json" % s):
        rows += work.get("ie/level-month-%d.json" % s).rows
        s += PAGE
    return rows


def more(ctx, work):
    base = {c["file"]: c for c in calls(ctx)}
    out = []
    first = work.get("ie/level-month.json")
    if first.has_more:
        out += [c for c in _pages(base["ie/level-month.json"], first, "ie/level-month") if not work.has(c["file"])]
    if not out and len({r["level_id"] for r in level_rows(work)}) == 1:
        # One level: the level row and the site row are the same figure, so list zones instead.
        sid, (q0, q1) = ctx["site"]["site_id"], ctx["quarter"]
        zc = io.call("ie/zone-month.json", "search_indoor_environment", metric="temperature", site_ids=[sid],
                     aggregate_entity="zone", aggregate_period="month", local_start_date=q0,
                     local_end_date=q1, limit=PAGE)
        if not work.has("ie/zone-month.json"):
            out.append(zc)
        else:
            out += [c for c in _pages(zc, work.get("ie/zone-month.json"), "ie/zone-month") if not work.has(c["file"])]
    return out


def floor_key(name):
    """Building order, highest first. A name with no readable floor sorts above the
    numbered ones, alphabetically, so a grouping such as NABERS IE heads the table."""
    n = name.strip().lower()
    if re.match(r"^(ground|gf|g|lobby)\b", n):
        return 0.0
    m = re.match(r"^(?:basement|b)[\s\-_]*0*(\d+)", n)
    if m:
        return -float(m.group(1))
    if n.startswith("basement"):
        return -1.0
    if n.startswith(("mezz", "mezzanine")):
        return 0.5
    m = re.match(r"^(?:level|lvl|floor|fl|l)[\s\-_]*0*(\d+)", n) or re.match(r"^0*(\d+)", n)
    if m:
        return float(m.group(1))
    if n.startswith("roof"):
        return 999.0
    return None


def band(v):
    for t, label in BANDS:
        if v >= t:
            return label
    return "Poor"


def build(ctx, work, shared):
    qm, tm = ctx["quarter_months"], ctx["trend_months"]
    month_of = lambda r: (r.get("date") or "")[:7]
    site_all = work.get("ie/site-all.json")
    link = site_all.link

    by_level, names, unit = defaultdict(dict), {}, "°C"
    for r in level_rows(work):
        by_level[r["level_id"]][month_of(r)] = r["score"]
        names[r["level_id"]] = r.get("level_name") or "Level %s" % r["level_id"]
        unit = r.get("unit") or unit
    zones = {r["level_id"]: r.get("included_point_count") or 0 for r in work.get("ie/zones-by-level.json").rows}

    single = len(by_level) == 1
    if single:
        zrows = list(work.get("ie/zone-month.json").rows) if work.has("ie/zone-month.json") else []
        s = PAGE
        while work.has("ie/zone-month-%d.json" % s):
            zrows += work.get("ie/zone-month-%d.json" % s).rows
            s += PAGE
        zs, ztemp, znames = defaultdict(dict), defaultdict(list), {}
        for r in zrows:
            key = r.get("zone_id") or r.get("fav_id")
            zs[key][month_of(r)] = r["score"]
            if r.get("zone_value") is not None:
                ztemp[key].append(r["zone_value"])
            znames[key] = r.get("zone_name") or str(key)
        dup = defaultdict(int)
        for k in znames:
            dup[znames[k]] += 1
        rows = [{"name": znames[k] + ((" " + str(k)[-2:]) if dup[znames[k]] > 1 else ""),
                 "counts": ["%.1f %s" % (sum(ztemp[k]) / len(ztemp[k]), unit) if ztemp[k] else "&ndash;"],
                 "months": [io.pct(zs[k][m[:7]], 1) if m[:7] in zs[k] else None for m in qm]}
                for k in sorted(znames, key=lambda k: znames[k])]
        label, counts_head = "Zone", ["Avg temp"]
    else:
        order = sorted(by_level, key=lambda l: (floor_key(names[l]) is not None, -(floor_key(names[l]) or 0), names[l]))
        rows = [{"name": names[l], "link": (link + "&level_ids=%s" % l) if link else None,
                 "counts": [zones.get(l, 0)],
                 "months": [io.pct(by_level[l][m[:7]], 1) if m[:7] in by_level[l] else None for m in qm]}
                for l in order]
        label, counts_head = "Level", ["Zones"]

    site_m = {month_of(r): r for r in work.get("ie/site-month.json").rows}
    site_q = [io.pct(site_m[m[:7]]["score"], 1) for m in qm if m[:7] in site_m]
    shown_zones = sum(zones.get(l, 0) for l in by_level)
    shared["thermal_zones"] = shown_zones
    heat = {"label": label, "dp": 1, "bands": [92, 85, 75], "counts": counts_head, "rows": rows,
            "site": {"counts": [shown_zones], "months": site_q}}

    score = io.pct(site_all.first()["score"], 1)
    delta, sub = io.movement(site_q[0], site_q[-1], 1, io.month(qm[0]), io.month(qm[-1]))
    impact = [dict({"chip": band(score), "chip_class": "pos" if band(score) in ("Excellent", "Good") else "warn",
                    "fig": "%.1f%%" % score, "cap": "thermal comfort maintained", "sub": sub, "order": 2},
                   **({"delta": delta} if delta else {}))]

    tmonths = [m for m in tm if m[:7] in site_m]
    values = [io.pct(site_m[m[:7]]["score"], 1) for m in tmonths]
    th = io.thresholds(values, BANDS)
    trend = {"values": values, "thresholds": th, "dp": 1, "note_after": "Site thermal comfort score",
             "alt": io.line_alt("site thermal comfort score", tmonths, values, th, 1)}

    facts_site = shared.get("site_facts") or {}
    lo, hi = facts_site.get("thermal_comfort_min_temp"), facts_site.get("thermal_comfort_max_temp")
    band_text = ("is %g–%g %s across this building" % (lo, hi, unit)) if lo is not None and hi is not None \
        else "is typically 21–24.9 °C (68–79 °F)"

    unscored = [(names.get(l, str(l)), n) for l, n in zones.items() if n and l not in by_level]
    movers = [r for r in rows if None not in (r["months"][0], r["months"][-1])]
    up = sorted(movers, key=lambda r: r["months"][-1] - r["months"][0], reverse=True)
    down = sorted(movers, key=lambda r: r["months"][-1] - r["months"][0])
    fmt = lambda r: "%s %.1f%% to %.1f%% (%+.1f pp)" % (r["name"], r["months"][0], r["months"][-1],
                                                       r["months"][-1] - r["months"][0])
    facts = [
        "Indoor environment: site %.1f%% over the quarter (%s); %s %.1f%% to %s %.1f%%."
        % (score, band(score), io.month(qm[0]), site_q[0], io.month(qm[-1]), site_q[-1]),
        "Biggest rises: " + ("; ".join(fmt(r) for r in up[:3] if r["months"][-1] > r["months"][0]) or "none"),
        "Biggest falls: " + ("; ".join(fmt(r) for r in down[:3] if r["months"][-1] < r["months"][0]) or "none"),
        "Below Good in %s: " % io.month(qm[-1]) + ("; ".join("%s %.1f%%" % (r["name"], r["months"][-1])
                                                         for r in rows if r["months"][-1] is not None and r["months"][-1] < 85) or "none"),
        "Site comfort by month, %s: %s." % (io.span(tm[0], tm[-1], short=True), ", ".join("%.1f%%" % v for v in values)),
        "Rows in building order as printed: %s." % ", ".join(r["name"] for r in rows),
    ]
    if unscored:
        facts.append("Not in the table (configured points, no score this quarter, so in neither figure): %s. "
                     "Say so in chat, not on the page." % ", ".join("%s %d points" % u for u in unscored))
    if len(values) < 6:
        facts.append("Only %d months of comfort history: see Newly onboarded sites in SKILL.md." % len(values))
    return {
        "impact": impact,
        "comfort": heat,
        "trend_comfort": trend,
        "links": {"comfort": link, "trend_comfort": work.get("ie/site-month.json").link},
        "datelines": {"Indoor environment health snapshot":
                      "%s. Share of zone readings inside the ASHRAE comfort band during working hours, by %s, in "
                      "building order." % (io.span(qm[0], qm[-1]), "zone" if single else "level"),
                      "Monthly thermal comfort": "%s, the last six complete months." % io.span(tm[0], tm[-1])},
        "notes": {
            "Thermal comfort score":
                "<strong>Thermal comfort score.</strong> The share of zone readings inside the ASHRAE comfort band "
                "during site working hours. The band is set per zone in PEAK and %s, so a level scores 100%% when "
                "every zone reading in working hours fell inside it. The site row comes from the site rollup and "
                "will not equal the average of the level rows." % band_text,
            "Zones":
                "<strong>Zones</strong> in the indoor environment snapshot counts the zone temperature points "
                "configured for comfort scoring on each level shown, and its site row is the thermal zones figure "
                "in the analytics overview. A level whose points returned no score in the quarter is left out of both.",
        },
        "prose": {
            "ie_snapshot": "The note under comfort by level: where in the building comfort moved and why.",
            "ie_trend": "The note under the six-month comfort chart: the direction against the benchmark lines.",
        },
        "facts": facts,
    }
