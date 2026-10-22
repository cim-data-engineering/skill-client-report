#!/usr/bin/env python3
"""Indoor environment: the thermal comfort impact row, comfort by level and the
six-month comfort trend. See references/single-site/indoor-environment/indoor-environment.md.
"""
import os
import re
import sys
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "scripts"))
import peak_io as io  # noqa: E402

HANDS_ON = ["thermal_zones"]      # known at plan time, so the overview fetches no zones of its own
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


def level_rows(work):
    return io.rows(work, "ie/level-month.json")


def more(ctx, work):
    out = io.pages_due(work, [c for c in calls(ctx) if c["file"] == "ie/level-month.json"])
    if out:
        return out
    sid, (q0, q1) = ctx["site"]["site_id"], ctx["quarter"]
    if len({r["level_id"] for r in level_rows(work)}) == 1:
        # One level: the level row and the site row are the same figure, so list zones instead.
        zc = io.call("ie/zone-month.json", "search_indoor_environment", metric="temperature", site_ids=[sid],
                     aggregate_entity="zone", aggregate_period="month", local_start_date=q0,
                     local_end_date=q1, limit=PAGE)
        if not work.has("ie/zone-month.json"):
            out.append(zc)
        else:
            out += io.pages_due(work, [zc])
    # the level count carries no names, so chat names unscored levels from their zones
    quiet = unscored(work)
    if quiet:
        zn = io.call("ie/levels-unscored.json", "search_zones", site_ids=[sid], level_ids=sorted(quiet), limit=250)
        out += io.pages_due(work, [zn]) if work.has(zn["file"]) else [zn]
    # a site that went live inside the quarter takes its headline score over the months it kept
    on = onboarding(ctx, site_months(work))
    if on and on["start"] > q0 and not work.has("ie/site-all-live.json"):
        out.append(io.call("ie/site-all-live.json", "search_indoor_environment", metric="temperature",
                           site_ids=[sid], aggregate_entity="site", aggregate_period="all",
                           local_start_date=on["start"], local_end_date=q1))
    return out


def unscored(work):
    """Levels with comfort points configured that returned no score this quarter: {level_id: points}."""
    scored = {r["level_id"] for r in level_rows(work)}
    return {r["level_id"]: r.get("included_point_count") or 0 for r in work.get("ie/zones-by-level.json").rows
            if r.get("included_point_count") and r["level_id"] not in scored}


def site_months(work):
    return {(r.get("date") or "")[:7]: r for r in work.get("ie/site-month.json").rows}


def onboarding(ctx, site_m):
    """For scores that start after the trend window's first month: the month they start and the
    first month the windows keep. Comfort rows carry no counts to date the day, so the go-live
    month is skipped unless it is the last."""
    tm = ctx["trend_months"]
    have = [m for m in tm if m[:7] in site_m]
    if not have or have[0] == tm[0]:
        return None
    i = tm.index(have[0])
    return {"month": have[0], "day": None, "start": tm[i + 1] if i + 1 < len(tm) else have[0]}


def floor_key(name):
    """Building order, highest first. A name with no readable floor sorts above the
    numbered ones, alphabetically, so a grouping such as NABERS IE heads the table.
    A level number keeps its minus when a space comes before it ("Level -2")."""
    n = name.strip().lower()
    if re.match(r"^(ground|gnd|grd|gf|g|lobby)\b", n):
        return 0.0
    m = re.match(r"^(?:basement|b)[\s\-_]*0*(\d+)", n)
    if m:
        return -float(m.group(1))
    if n.startswith("basement"):
        return -1.0
    if n.startswith(("mezz", "mezzanine")):
        return 0.5
    m = re.match(r"^(?:level|lvl|floor|fl|l)(?:\s+(-)\s*|[\s\-_]*)0*(\d+)", n) or re.match(r"^(-?)0*(\d+)", n)
    if m:
        return -float(m.group(2)) if m.group(1) else float(m.group(2))
    if n.startswith("roof"):
        return 999.0
    return None


def month_of(r):
    return (r.get("date") or "")[:7]


def zone_rows(work, keep, kq, shown, temps, unit):
    """One level means the level row and the site row are the same figure, so the rows are its zones,
    each month the mean of its points' scores, each with its average temperature where the zone
    count would go. Returns (rows, label, count heading, site row counts)."""
    zrows = io.rows(work, "ie/zone-month.json") if work.has("ie/zone-month.json") else []
    zs, ztemp, znames = defaultdict(lambda: defaultdict(list)), defaultdict(list), {}
    for r in zrows:
        if month_of(r) not in keep:
            continue
        key = r.get("zone_id") or r.get("fav_id")
        if r.get("score") is not None:
            zs[key][month_of(r)].append(r["score"])
        if r.get("zone_value") is not None:
            ztemp[key].append(r["zone_value"])
        znames[key] = r.get("zone_name") or str(key)
    dup = defaultdict(int)
    for k in znames:
        dup[znames[k]] += 1
    avg = lambda xs: "%.1f %s" % (sum(xs) / len(xs), unit) if xs else "&ndash;"
    rows = [{"name": znames[k] + ((" " + str(k)[-2:]) if dup[znames[k]] > 1 else ""),
             "counts": [avg(ztemp[k])],
             "months": [io.pct(sum(zs[k][m[:7]]) / len(zs[k][m[:7]]), 1) if zs[k][m[:7]] else None for m in kq]}
            for k in sorted(znames, key=lambda k: znames[k])]
    return rows, "Zone", ["Avg temp"], [avg([t for l in shown for t in temps[l]])]


def level_table(by_level, names, zones, shown, kq, link):
    """A row per level that scored, in building order: highest first, then ground, then basements."""
    order = sorted(shown, key=lambda l: (floor_key(names[l]) is not None, -(floor_key(names[l]) or 0), names[l]))
    return [{"name": names[l], "link": link + "&level_ids=%s" % l,
             "counts": [zones.get(l, 0)],
             "months": [io.pct(by_level[l][m[:7]], 1) if m[:7] in by_level[l] else None for m in kq]}
            for l in order]


def unscored_chat(work):
    level_names = {}
    if work.has("ie/levels-unscored.json"):
        level_names = {r["level_id"]: r.get("level_name") for r in io.rows(work, "ie/levels-unscored.json")}
    quiet = ["%s (%d points)" % (level_names.get(l) or "level %s" % l, n) for l, n in unscored(work).items()]
    if not quiet:
        return []
    return ["Comfort points are configured on %s, but none returned a score this quarter, so they are in "
            "neither the comfort table nor the thermal zones figure." % io.listing(quiet)]


def build(ctx, work, shared):
    if not work.get("ie/site-all.json").first():
        shared["thermal_zones"] = 0                   # zone points on the levels that scored: none did
        return {"drop": True, "chat": ["Indoor environment is left out: PEAK holds no thermal comfort score for the "
                                       "site in the quarter."]}
    shared.setdefault("partial", [])                  # its scores show the month to date and stand as they are
    qm, tm = ctx["quarter_months"], ctx["trend_months"]
    # a site that went live inside the windows shows only the months it was monitored in full
    site_m = site_months(work)
    on = onboarding(ctx, site_m)
    start, kq, kt = io.kept_months(ctx, on)
    keep = {m[:7] for m in kq}
    io.hand_on_start(shared, start, kq, on)
    sid = ctx["site"]["site_id"]
    host = io.host(ctx["site"])
    dashboard = lambda start: ("%s/indoor-environment/thermal-comfort?summary_site_id=%s&summary_ts=%s&site_ids=%s"
                               "&start_date=%sT00:00:00.000&end_date=%sT00:00:00.000"
                               % (host, sid, qm[-1], sid, start, ctx["through"]))
    link = dashboard(kq[0])

    by_level, names, temps, unit = defaultdict(dict), {}, defaultdict(list), "°C"
    for r in level_rows(work):
        by_level[r["level_id"]][month_of(r)] = r["score"]
        names[r["level_id"]] = r.get("level_name") or "Level %s" % r["level_id"]
        unit = r.get("unit") or unit
        if month_of(r) in keep and r.get("zone_value") is not None:
            temps[r["level_id"]].append(r["zone_value"])
    zones = {r["level_id"]: r.get("included_point_count") or 0 for r in work.get("ie/zones-by-level.json").rows}
    shown = [l for l in by_level if any(m[:7] in by_level[l] for m in kq)]
    one = len(kq) == 1                                # one month: the lowest score leads
    single = len(by_level) == 1
    if single:
        rows, label, counts_head, site_counts = zone_rows(work, keep, kq, shown, temps, unit)
    else:
        rows, label, counts_head = level_table(by_level, names, zones, shown, kq, link), "Level", ["Zones"]
    if one:
        rows.sort(key=lambda r: (r["months"][0] is None, r["months"][0] or 0))

    site_q = io.site_scores(site_m, kq)
    shown_zones = sum(zones.get(l, 0) for l in shown)
    shared["thermal_zones"] = shown_zones
    heat = {"label": label, "dp": 1, "bands": [92, 85, 75], "counts": counts_head, "rows": rows,
            "months": [io.mon(m) for m in kq], "to_date": kq[-1] == ctx["to_date"],
            "site": {"counts": site_counts if single else [shown_zones], "months": site_q}}

    live = kq != qm and work.has("ie/site-all-live.json")
    score = io.pct(work.get("ie/site-all-live.json" if live else "ie/site-all.json").first()["score"], 1)
    impact = [io.score_row(ctx, score, BANDS, kq, site_q, "thermal comfort maintained", "thermal-comfort")]
    trend, pts = io.trend_line(ctx, kt, site_m, BANDS, "site thermal comfort score")

    facts_site = shared.get("site_facts") or {}
    lo, hi = facts_site.get("thermal_comfort_min_temp"), facts_site.get("thermal_comfort_max_temp")
    band_text = ("%g–%g %s across this building" % (lo, hi, unit)) if lo is not None and hi is not None \
        else "typically 21–24.9 °C (68–79 °F)"

    chat = unscored_chat(work)
    if on:
        chat.append("Thermal comfort went live in %s, so its figures start with %s." % (
            io.month(on["month"]), io.month_label(ctx, start)) + ("" if trend else " Too few months for its trend."))
    elif len(pts) < len(tm):
        chat.append("Indoor environment has %d months of comfort history, short of the %d the trend covers."
                    % (len(pts), len(tm)))

    links = {"comfort": link}
    datelines = {"Indoor environment health snapshot":
                 "%s. Share of zone readings inside the comfort band set for the site during working "
                 "hours, by %s, %s." % (io.months_text(ctx, kq, " and "), "zone" if single else "level",
                                        "lowest first" if one else "in building order")}
    if trend:
        links["trend_comfort"] = dashboard(kt[0])
        datelines["Monthly thermal comfort"] = ("%s, the last six complete months%s."
                                                % (io.span(kt[0], io.whole(ctx, kt)[-1]), io.and_to_date(ctx))
                                                if kt == tm else "%s." % io.months_text(ctx, kt))
    out = {
        "impact": impact,
        "comfort": heat,
        "trend_comfort": trend,
        "links": links,
        "datelines": datelines,
        "notes": {
            "Thermal comfort score":
                "<strong>Thermal comfort score.</strong> Comfort band set per zone in PEAK, %s. The site row is "
                "PEAK's site-level score, not an average of the rows below." % band_text,
            "Zones":
                "<strong>Zones.</strong> Zone temperature points configured for comfort scoring. Levels with no "
                "score in the period are excluded here and from the thermal zones figure in the analytics overview.",
        },
        "chat": chat,
    }
    if single:
        out["statements"] = {"Indoor environment health snapshot": "Thermal comfort by zone"}
    return out
