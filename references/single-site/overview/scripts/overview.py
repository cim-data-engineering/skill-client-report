#!/usr/bin/env python3
"""The parts every report carries: masthead, analytics overview, and the operational
impact and notes frames. See references/single-site/overview/overview.md.

Imported by scripts/report.py, which hands each section module the same three
hooks: calls() before the fetch, more() for any follow-up round, build() to turn
the saved responses into the bundle. It takes the scored equipment, rules and thermal
zones from `shared` when sections hand them on, and for a site that went live inside
the windows the first month the sections kept and when their scores start, so it
builds after the sections.
"""
import html
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "scripts"))
import peak_io as io  # noqa: E402



def calls(ctx):
    sid, (q0, q1) = ctx["site"]["site_id"], ctx["quarter"]
    out = [
        io.gql("overview/site.json", "platform.sites", {"site_id": sid},
               ["site_name", "photo_url", "building_size", "monetary_currency",
                "thermal_comfort_min_temp", "thermal_comfort_max_temp"]),
        io.call("overview/sensors.json", "search_favourites", site_ids=[sid], limit=1),
    ]
    if "scored_equipment" not in handed_on(ctx):
        # With no section handing them on, the overview counts the equipment and rules that scored in the quarter.
        out.append(io.call("overview/types-scored.json", "search_equipment_health_scores", site_ids=[sid],
                           aggregate_entities=["metadata_type"], aggregate_period="all", local_start_date=q0,
                           local_end_date=q1, select_equipment_count=True))
    if "thermal_zones" not in handed_on(ctx):
        # With no section handing thermal zones on, the overview counts them: zones with a reading in the quarter.
        out.append(io.call("overview/zones-scored.json", "search_indoor_environment", metric="temperature",
                           site_ids=[sid], aggregate_entity="zone", aggregate_period="all",
                           local_start_date=q0, local_end_date=q1, limit=80))
    return out


def handed_on(ctx):
    """The figures sections hand on, known at plan time."""
    return ctx["handed_on"]


def more(ctx, work):
    if "thermal_zones" in handed_on(ctx):
        return []
    return io.pages_due(work, [c for c in calls(ctx) if c["file"] == "overview/zones-scored.json"])


def facts_site(work):
    return work.get("overview/site.json").first() or {}


def build(ctx, work, shared):
    site, facts = ctx["site"], facts_site(work)
    name = facts.get("site_name") or site["site_name"]
    # A site that went live inside the quarter reports from the first month a section kept
    q0, qlast = min(shared.get("period_start") or [ctx["quarter"][0]]), ctx["through"]
    total = lambda f: work.get(f).total or 0

    if "scored_equipment" in shared:
        equipment, rules = shared["scored_equipment"], shared["scored_rules"]
    else:
        types = io.rollup(work.get("overview/types-scored.json").rows)
        equipment, rules = (types[0]["equipment_count"], types[0]["task_count"]) if types else (0, 0)
    if "thermal_zones" in shared:
        zones = shared["thermal_zones"]
    else:
        zones = len({r["zone_id"] for r in io.rows(work, "overview/zones-scored.json")})

    # PEAK stores building size in m² for every site; a US site shows it in ft², converted
    feet = io.in_feet(site.get("country"))
    size, unit = io.area(facts.get("building_size"), feet), "ft²" if feet else "m²"
    brand = ctx.get("brand") or {}
    window = reporting_window(ctx, shared.get("partial"))
    stats = {
        "Building size": ("{:,}".format(int(round(size))) + " <span>%s</span>" % unit) if size else "&ndash;",
        "Equipment": "{:,}".format(equipment),
        "Sensors": "{:,}".format(total("overview/sensors.json")),
        "Rules": "{:,}".format(rules),
        "Thermal zones": "{:,}".format(zones),
    }
    for label, n in (("Equipment", equipment), ("Rules", rules), ("Thermal zones", zones)):
        if not n:
            stats.pop(label)                          # nothing scored behind it: the card is left out
    return {
        "masthead": {
            "site_name": name,
            "photo_url": facts.get("photo_url"),
            "period": io.period(q0, qlast, short=True) + live_since(shared.get("live_since")),
            "author": ctx["author"],
            "issued": io.day_short(ctx["today"]),
            "prepared": "Prepared by <strong>%s — %s</strong> · Powered by PEAK" % (
                html.escape(brand.get("name", "CIM"), quote=False),
                html.escape(brand.get("service", "Data Driven Operations"), quote=False)),
        },
        "overview": {
            "as_at": "As at %s" % io.day_long(ctx["today"]),
            "stats": stats,
        },
        "datelines": {"Operational impact": io.period(q0, qlast)},
        "notes": {"The reporting window": "<strong>The reporting window.</strong> " + window} if window else {},
    }


def live_since(starts):
    """', monitoring live since 14 Jul 2026' for a site that went live inside the windows: the
    earliest go-live a section hands on, to the day where one is dated, else the month."""
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
