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

NAME = "indoor-environment"
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
            out += [c for c in _pages(zc, work.get("ie/zone-month.json"), "ie/zone-month") if not work.has(c["file"])]
    # Levels with comfort points but no score carry no name in the counts, so chat names them from their zones
    quiet = unscored(work)
    if quiet and not work.has("ie/levels-unscored.json"):
        out.append(io.call("ie/levels-unscored.json", "search_zones", site_ids=[sid], level_ids=sorted(quiet),
                           limit=250))
    # A site that went live inside the quarter takes its headline score over the months after it
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
    """A site whose comfort scores start inside the trend window, after its first month, went live
    then. PEAK's comfort rows carry no reading counts to tell the day, so that month counts as
    monitored in part: the windows keep the months after it, or that month alone when nothing
    follows. None for a site scored from the window's first month."""
    tm = ctx["trend_months"]
    have = [m for m in tm if m[:7] in site_m]
    if not have or have[0] == tm[0]:
        return None
    i = tm.index(have[0])
    return {"month": have[0], "day": None, "start": tm[i + 1] if i + 1 < len(tm) else have[0]}


def months_text(ctx, months, lead=", and "):
    """'August – September 2026, and October to date', 'September 2026' or 'October 2026 to date'."""
    whole = io.whole(ctx, months)
    if not whole:
        return "%s %d to date" % (io.month(months[0]), io.d(months[0]).year)
    head = io.span(whole[0], whole[-1]) if len(whole) > 1 else "%s %d" % (io.month(whole[0]), io.d(whole[0]).year)
    return head + (io.and_to_date(ctx, lead) if months[-1] == ctx.get("to_date") else "")


def floor_key(name):
    """Building order, highest first. A name with no readable floor sorts above the
    numbered ones, alphabetically, so a grouping such as NABERS IE heads the table.
    Level numbers keep their sign, so basements written as negative levels sort below
    ground, as do B1, Basement 2 and the like."""
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
    # "Level -2" is two below ground, but "Level-03" beside "Level 02" is level 3: a minus counts
    # only with a space before it
    m = re.match(r"^(?:level|lvl|floor|fl|l)(?:\s+(-)\s*|[\s\-_]*)0*(\d+)", n) or re.match(r"^(-?)0*(\d+)", n)
    if m:
        return -float(m.group(2)) if m.group(1) else float(m.group(2))
    if n.startswith("roof"):
        return 999.0
    return None


def band(v):
    for t, label in BANDS:
        if v >= t:
            return label
    return "Poor"


def build(ctx, work, shared):
    site_m = site_months(work)
    if not site_m:
        return {"drop": [NAME], "chat": ["Indoor environment left out: PEAK returned no comfort score for the site "
                                         "in the window."]}
    shared.setdefault("partial", [])                  # its scores show the month to date and stand as they are
    qm, tm = ctx["quarter_months"], ctx["trend_months"]
    # A site that went live inside the window shows the months it was monitored in full
    on = onboarding(ctx, site_m)
    start = on["start"] if on else tm[0]
    kq, kt = [m for m in qm if m >= start], [m for m in tm if m >= start]
    keep = {m[:7] for m in kq}
    shared.setdefault("period_start", []).append(kq[0])
    if on:
        shared.setdefault("live_since", []).append({"month": on["month"], "day": None})
    month_of = lambda r: (r.get("date") or "")[:7]
    sid = ctx["site"]["site_id"]
    host = re.match(r"https?://[^/]+", ctx["site"].get("site_link") or "")
    host = host.group(0) if host else "https://ace.cimenviro.com"
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
    one = len(kq) == 1                                # no change to show: the lowest score leads

    single = len(by_level) == 1
    if single:
        # One row per zone, each month the mean of its points' scores; a zone's average
        # temperature takes the place of the Zones count
        zrows = list(work.get("ie/zone-month.json").rows) if work.has("ie/zone-month.json") else []
        s = PAGE
        while work.has("ie/zone-month-%d.json" % s):
            zrows += work.get("ie/zone-month-%d.json" % s).rows
            s += PAGE
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
        label, counts_head, site_counts = "Zone", ["Avg temp"], [avg([t for l in shown for t in temps[l]])]
    else:
        order = sorted(shown, key=lambda l: (floor_key(names[l]) is not None, -(floor_key(names[l]) or 0), names[l]))
        rows = [{"name": names[l], "link": link + "&level_ids=%s" % l,
                 "counts": [zones.get(l, 0)],
                 "months": [io.pct(by_level[l][m[:7]], 1) if m[:7] in by_level[l] else None for m in kq]}
                for l in order]
        label, counts_head = "Level", ["Zones"]
    if one:
        rows.sort(key=lambda r: (r["months"][0] is None, r["months"][0] or 0))

    site_q = [io.pct(site_m[m[:7]]["score"], 1) if m[:7] in site_m else None for m in kq]
    shown_zones = sum(zones.get(l, 0) for l in shown)
    shared["thermal_zones"] = shown_zones
    heat = {"label": label, "dp": 1, "bands": [92, 85, 75], "counts": counts_head, "rows": rows,
            "months": [io.mon(m) for m in kq], "to_date": kq[-1] == ctx["to_date"],
            "site": {"counts": site_counts if single else [shown_zones], "months": site_q}}

    # the headline score: the quarter's rollup, or for a site that went live in it, the rollup over
    # the months after
    chat = []
    site_all = work.get("ie/site-all.json")
    if kq != qm:
        if work.has("ie/site-all-live.json"):
            site_all = work.get("ie/site-all-live.json")
        else:
            chat.append("The thermal comfort headline still includes %s, monitored only in part. Run python3 "
                        "scripts/report.py next %s, make the call it prints, then bundle again."
                        % (io.month(on["month"]), ctx.get("dir", "<dir>")))
    score = io.pct(site_all.first()["score"], 1)
    got = [(m, v) for m, v in zip(kq, site_q) if v is not None]
    if len(got) > 1:
        delta, sub = io.movement(got[0][1], got[-1][1], 1, io.month(got[0][0]), io.month_label(ctx, got[-1][0]))
    else:
        delta, sub = None, "Scored over %s." % io.month_label(ctx, kq[0])   # a movement needs two months
    impact = [dict({"chip": band(score), "chip_class": "pos" if band(score) in ("Excellent", "Good") else "warn",
                    "fig": "%.1f%%" % score, "cap": "thermal comfort maintained", "sub": sub, "row": "thermal-comfort"},
                   **({"delta": delta} if delta else {}))]

    # the trend, each score over its own month; a trend needs three points
    values = [io.pct(site_m[m[:7]]["score"], 1) if m[:7] in site_m else None for m in kt]
    pts = [(m, v) for m, v in zip(kt, values) if v is not None]
    trend = None
    if len(pts) >= 3:
        th = io.thresholds([v for _, v in pts], BANDS)
        trend = {"values": values, "months": [io.mon(m) for m in kt], "to_date": kt[-1] == ctx["to_date"],
                 "thresholds": th, "dp": 1,
                 "alt": io.line_alt(ctx, "site thermal comfort score", [m for m, _ in pts], [v for _, v in pts],
                                    th, 1)}

    facts_site = shared.get("site_facts") or {}
    lo, hi = facts_site.get("thermal_comfort_min_temp"), facts_site.get("thermal_comfort_max_temp")
    band_text = ("%g–%g %s across this building" % (lo, hi, unit)) if lo is not None and hi is not None \
        else "typically 21–24.9 °C (68–79 °F)"
    # the range held on one line: word joiners either side of the dash, a no-break space before the unit
    in_band = "the comfort band set for the site in PEAK%s" % (
        (", %g\u2060–\u2060%g\u00a0%s," % (lo, hi, unit)) if lo is not None and hi is not None else "")

    level_names = {}
    if work.has("ie/levels-unscored.json"):
        level_names = {r["level_id"]: r.get("level_name") for r in work.get("ie/levels-unscored.json").rows}
    quiet = ["%s (%d points)" % (level_names.get(l) or "level %s" % l, n) for l, n in unscored(work).items()]
    if quiet:
        chat.append("Comfort points are configured on %s, but none returned a score this quarter, so they are in "
                    "neither the comfort table nor the thermal zones figure." % io.listing(quiet))
    if on:
        chat.append("Thermal comfort scores start in %s %d, part way through the month as far as PEAK shows, so "
                    "its figures start with %s." % (io.month(on["month"]), io.d(on["month"]).year,
                                                    io.month_label(ctx, start))
                    if start != on["month"] else
                    "Thermal comfort scores start in %s %d, so its figures cover that month alone."
                    % (io.month(on["month"]), io.d(on["month"]).year))
    gaps = [io.month_label(ctx, m) for m, v in zip(kt, values) if v is None]
    if gaps:
        chat.append("Thermal comfort has no score for %s, a gap in the data rather than onboarding." % io.listing(gaps))
    if trend is None:
        chat.append("Thermal comfort has %d month%s of scores, too few for a trend, so the monthly thermal comfort "
                    "section is left out." % (len(pts), "" if len(pts) == 1 else "s"))

    links = {"comfort": link}
    datelines = {"Indoor environment health snapshot":
                 "%s. Share of zone readings inside %s during working hours, by %s%s."
                 % (months_text(ctx, kq, " and "), in_band, "zone" if single else "level",
                    ", lowest first" if one else "" if single else ", in building order")}
    if trend:
        links["trend_comfort"] = dashboard(kt[0])
        datelines["Monthly thermal comfort"] = ("%s, the last six complete months%s."
                                                % (io.span(kt[0], io.whole(ctx, kt)[-1]), io.and_to_date(ctx))
                                                if kt == tm else "%s." % months_text(ctx, kt))
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
