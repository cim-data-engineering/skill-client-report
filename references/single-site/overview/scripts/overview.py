#!/usr/bin/env python3
"""The parts every report carries: masthead, analytics overview, and the operational
impact and notes frames. See references/single-site/overview/overview.md.

Imported by scripts/report.py, which hands each section module the same three
hooks: calls() before the fetch, more() for any follow-up round, build() to turn
the saved responses into the bundle. It takes the thermal zones figure from `shared`
when a section hands one on, and for a site that went live inside the windows the
first month the sections kept and when their scores start, so it builds after the
sections.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "scripts"))
import peak_io as io  # noqa: E402

NAME = "overview"


def calls(ctx):
    sid, (q0, q1) = ctx["site"]["site_id"], ctx["quarter"]
    out = [
        io.gql("overview/site.json", "platform.sites", {"site_id": sid},
               ["site_name", "photo_url", "building_size", "monetary_currency",
                "thermal_comfort_min_temp", "thermal_comfort_max_temp"]),
        io.call("overview/rules.json", "search_rules", site_ids=[sid], task_state="running", limit=1),
        io.call("overview/sensors.json", "search_favourites", site_ids=[sid], limit=1),
        io.call("overview/equipment.json", "search_equipment", site_ids=[sid], limit=1),
        io.call("overview/equipment-system.json", "search_equipment", site_ids=[sid],
                metadata_type_ids=io.SYSTEM_TYPES, limit=1),
    ]
    if "thermal_zones" not in handed_on(ctx):
        # With no section handing thermal zones on, the overview counts them: points on the levels that scored.
        out += [io.call("overview/zones-by-level.json", "count_indoor_environment_zones",
                        metric="temperature", site_ids=[sid], aggregate_entity="level"),
                io.call("overview/levels-scored.json", "search_indoor_environment", metric="temperature",
                        site_ids=[sid], aggregate_entity="level", aggregate_period="all",
                        local_start_date=q0, local_end_date=q1, limit=80)]
    return out


def handed_on(ctx):
    """The figures sections hand on, known at plan time. A plan made before plan.json listed them
    names none, and then indoor environment, the one section that hands any on, decides."""
    got = ctx.get("handed_on")
    if got is None:
        return ["thermal_zones"] if "indoor-environment" in ctx["sections"] else []
    return got


def more(ctx, work):
    if "thermal_zones" not in handed_on(ctx) and work.has("overview/levels-scored.json"):
        r = work.get("overview/levels-scored.json")
        if r.has_more:
            return [dict(c, file="overview/levels-scored-80.json", args=dict(c["args"], start_index=80))
                    for c in calls(ctx) if c["file"] == "overview/levels-scored.json"]
    return []


def facts_site(work):
    return work.get("overview/site.json").first() or {}


def build(ctx, work, shared):
    site, facts = ctx["site"], facts_site(work)
    name = facts.get("site_name") or site["site_name"]
    # A site that went live inside the quarter reports from the first month a section kept
    q0, qlast = min(shared.get("period_start") or [ctx["quarter"][0]]), ctx["through"]
    total = lambda f: work.get(f).total or 0

    if "thermal_zones" in shared:
        zones = shared["thermal_zones"]
    else:
        counts = {r["level_id"]: r.get("included_point_count") or 0
                  for r in work.get("overview/zones-by-level.json").rows}
        scored = {r["level_id"] for f in ("overview/levels-scored.json", "overview/levels-scored-80.json")
                  if work.has(f) for r in work.get(f).rows}
        zones = sum(counts.get(l, 0) for l in scored)

    # PEAK stores building size in m² for every site; a US site shows it in ft², converted
    feet = io.in_feet(site.get("country"))
    size, unit = io.area(facts.get("building_size"), feet), "ft²" if feet else "m²"
    brand = ctx.get("brand") or {}
    shared["site_facts"] = facts
    window = reporting_window(ctx, shared.get("partial"))
    return {
        "masthead": {
            "site_name": name,
            "photo_url": facts.get("photo_url"),
            "period": io.period(q0, qlast, short=True) + live_since(shared.get("live_since")),
            "author": ctx["author"],
            "issued": io.day_short(ctx["today"]),
            "prepared": "Prepared by <strong>%s — %s</strong> · Powered by PEAK" % (brand.get("name", "CIM"),
                                                                                  brand.get("service", "Data Driven Operations")),
        },
        "overview": {
            "as_at": "As at %s" % io.day_long(ctx["today"]),
            "stats": {
                "Building size": ("{:,}".format(int(round(size))) + " <span>%s</span>" % unit) if size else "&ndash;",
                "Equipment": "{:,}".format(total("overview/equipment.json") - total("overview/equipment-system.json")),
                "Sensors": "{:,}".format(total("overview/sensors.json")),
                "Rules running": "{:,}".format(total("overview/rules.json")),
                "Thermal zones": "{:,}".format(zones),
            },
        },
        "datelines": {"Operational impact": io.period(q0, qlast)},
        "notes": {"The reporting window": "<strong>The reporting window.</strong> " + window} if window else {},
    }


def live_since(starts):
    """', monitoring live since 30 Jul 2026' for a site that went live inside the windows: the
    earliest month a section's scores start in, on the day one of them dates it to, or the month
    alone where none can."""
    if not starts:
        return ""
    first = min(s["month"] for s in starts)
    day = min((s["day"] for s in starts if s["month"] == first and s.get("day")), default=None)
    return ", monitoring live since %s" % (io.day_short(day) if day else "%s %d" % (io.month(first)[:3],
                                                                                    io.d(first).year))


def reporting_window(ctx, volume):
    """volume: the partial figures handed on, None when no section shows the month to date."""
    m = ctx["to_date"]
    if not m or volume is None:
        return ""
    full = (io.add_months(io.d(m), 1) - io.d(m)).days
    text = "%s %d covers %d of %d days, to the issue date. " % (io.month(m), io.d(m).year, io.days_in(ctx, m), full)
    if volume:
        return text + "Its %s are partial totals; scores are unaffected." % io.listing(volume)
    return text + "Scores are unaffected."
