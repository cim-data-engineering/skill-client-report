#!/usr/bin/env python3
"""The parts every report carries: masthead, analytics overview, the operational
impact and notes frames, and the footer. See references/overview/overview.md.

Imported by scripts/report.py, which hands each section module the same three
hooks: calls() before the fetch, more() for any follow-up round, build() to turn
the saved responses into the bundle. This one builds last, so it can take the
thermal zones figure off the indoor environment site row when that section is in.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "scripts"))
import peak_io as io  # noqa: E402

NAME = "overview"
SYSTEM_TYPES = [21, 37, 69, 70, 87, 105, 114]     # the platform checking itself, not plant
STATES = {"New South Wales": "NSW", "Victoria": "VIC", "Queensland": "QLD", "South Australia": "SA",
          "Western Australia": "WA", "Tasmania": "TAS", "Australian Capital Territory": "ACT",
          "Northern Territory": "NT"}


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
                metadata_type_ids=SYSTEM_TYPES, limit=1),
    ]
    if "indoor-environment" not in ctx["sections"]:
        # Thermal zones is the snapshot's site row: points on the levels that scored.
        out += [io.call("overview/zones-by-level.json", "count_indoor_environment_zones",
                        metric="temperature", site_ids=[sid], aggregate_entity="level"),
                io.call("overview/levels-scored.json", "search_indoor_environment", metric="temperature",
                        site_ids=[sid], aggregate_entity="level", aggregate_period="all",
                        local_start_date=q0, local_end_date=q1, limit=80)]
    return out


def more(ctx, work):
    if "indoor-environment" not in ctx["sections"] and work.has("overview/levels-scored.json"):
        r = work.get("overview/levels-scored.json")
        if r.has_more:
            return [dict(c, file="overview/levels-scored-80.json", args=dict(c["args"], start_index=80))
                    for c in calls(ctx) if c["file"] == "overview/levels-scored.json"]
    return []


def facts_site(work):
    return work.get("overview/site.json").first() or {}


def place(site):
    state = STATES.get(site.get("state") or "", site.get("state") or "")
    return " ".join(x for x in (site.get("city"), state, site.get("postcode")) if x)


def build(ctx, work, shared):
    site, facts = ctx["site"], facts_site(work)
    name = facts.get("site_name") or site["site_name"]
    q0, q1 = ctx["quarter"]
    qlast = io.last_day(q1).isoformat()
    total = lambda f: work.get(f).total or 0

    if "thermal_zones" in shared:
        zones = shared["thermal_zones"]
    else:
        counts = {r["level_id"]: r.get("included_point_count") or 0
                  for r in work.get("overview/zones-by-level.json").rows}
        scored = {r["level_id"] for f in ("overview/levels-scored.json", "overview/levels-scored-80.json")
                  if work.has(f) for r in work.get(f).rows}
        zones = sum(counts.get(l, 0) for l in scored)

    size = facts.get("building_size")
    unit = "ft²" if (site.get("country") or "").lower() in ("united states", "usa", "us") else "m²"
    brand = ctx.get("brand") or {}
    platform = "CIM PEAK" if not brand.get("override") else "PEAK"
    shared["site_facts"] = facts
    return {
        "masthead": {
            "site_name": name,
            "photo_url": facts.get("photo_url"),
            "period": io.period(q0, qlast, short=True),
            "author": ctx["author"],
            "issued": io.day_short(ctx["today"]),
            "footer": "%s · %s, %s" % (platform, name, place(site)) if place(site) else "%s · %s" % (platform, name),
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
        "notes": {"The reporting window": "<strong>The reporting window.</strong> " + reporting_window(ctx)},
        "facts": ["Analytics overview: %s thermal zones (zone temperature points on the levels that "
                  "returned a comfort score this quarter)." % "{:,}".format(zones)],
    }


def reporting_window(ctx):
    secs, months = ctx["sections"], ctx["trend_months"]
    volume = []
    if "equipment-health" in secs:
        volume += ["automated checks", "labour cost avoided"]
    if "alerts-resolved" in secs:
        volume += ["actions raised and resolved"]
    q0, q1 = ctx["quarter"]
    text = ("Every monthly series closes on %s %d, the last complete month, so no column or bar covers "
            "a part-month" % (io.month(months[-1]), io.d(months[-1]).year))
    if len(volume) > 1:
        text += ", and %s can be read against each other directly" % io.listing(volume)
    return (text + ". The quarter is %s, the three complete months named in the masthead."
            % io.span(q0, io.last_day(q1).isoformat()))
