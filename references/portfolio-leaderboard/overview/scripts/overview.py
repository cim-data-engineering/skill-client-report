#!/usr/bin/env python3
"""The parts every portfolio report carries: the masthead and the scorecard strip.
See references/portfolio-leaderboard/overview/overview.md.

Imported by scripts/report.py through the same three hooks every section has:
calls() before the fetch, more() for any follow-up round, build() to turn the saved
responses into the bundle. facts() hands the site facts to every section before any
of them builds. It takes the thermal zones figure from `shared`, so it builds after
the section that hands it on.
"""
import base64
import io as bytes_io
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "scripts"))
import peak_io as io  # noqa: E402
import portfolio_io as pio  # noqa: E402

NAME = "overview"
CHUNK = 100
COUNT_CHUNK = 10              # an unfiltered equipment count across many more sites runs past the gateway's timeout
LOGO_PX = 288                                     # the slot is 72px tall: four times that keeps it sharp in print


def calls(ctx):
    count = lambda name, tool, **kw: pio.split(ctx, name, COUNT_CHUNK, lambda f, ids: io.call(f, tool, site_ids=ids, **kw))
    return (pio.split(ctx, "overview/sites.json", CHUNK,
                      lambda f, ids: io.gql(f, "platform.sites", {"site_ids": ids, "limit": CHUNK},
                                            ["site_id", "site_name", "building_size", "monetary_currency", "state",
                                             "country", "photo_url", "thermal_comfort_min_temp",
                                             "thermal_comfort_max_temp", "thermal_comfort_margin"]))
            + count("overview/rules.json", "search_rules", task_state="running", limit=1)
            + count("overview/sensors.json", "search_favourites", limit=1)
            + count("overview/equipment.json", "search_equipment", limit=1)
            + count("overview/equipment-system.json", "search_equipment", metadata_type_ids=io.SYSTEM_TYPES, limit=1))


def more(ctx, work):
    return []


def facts(ctx, work):
    """{site_id: platform.sites row}: building size, currency, state, country, the building's photo link and
    its default comfort band."""
    return {r["site_id"]: r for r in pio.rows(work, "overview/sites.json")}


def logo(path):
    """The supplied client logo as a data URI: a raster one trimmed of its transparent
    margins and scaled to the slot, its colours kept; an SVG as it is."""
    raw = open(path, "rb").read()
    if path.lower().endswith(".svg"):
        return "data:image/svg+xml;base64," + base64.b64encode(raw).decode()
    try:
        from PIL import Image
    except ImportError:
        raise SystemExit("the client logo needs Pillow: pip install pillow")
    im = Image.open(path)
    if "A" in im.getbands() or im.mode == "P":
        im = im.convert("RGBA")
        box = im.getchannel("A").getbbox()
        if box:
            im = im.crop(box)
    if im.height > LOGO_PX:
        im = im.resize((round(im.width * LOGO_PX / im.height), LOGO_PX), Image.LANCZOS)
    buf = bytes_io.BytesIO()
    im.save(buf, "PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def dark(path):
    """True for a logo drawn dark enough to vanish on the navy masthead, which then sits on a light tile:
    a raster one by the mean lightness of its opaque pixels, an SVG by the fills it names."""
    if path.lower().endswith(".svg"):
        text = open(path, encoding="utf-8", errors="ignore").read()
        cols = re.findall(r"#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b", text)
        if not cols:
            return "fill" not in text or bool(re.search(r'fill="(?:black|#000)', text))   # unfilled paths draw black
        def lum(h):
            h = h if len(h) == 6 else "".join(c * 2 for c in h)
            r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
            return 0.2126 * r + 0.7152 * g + 0.0722 * b
        return sum(lum(h) < 0.45 for h in cols) > len(cols) / 2
    try:
        from PIL import Image
    except ImportError:
        return False
    im = Image.open(path).convert("RGBA")
    im.thumbnail((128, 128))
    px = [(r, g, b) for r, g, b, a in im.getdata() if a > 128]
    if not px:
        return False
    return sum(0.2126 * r + 0.7152 * g + 0.0722 * b for r, g, b in px) / len(px) / 255 < 0.45


def build(ctx, work, shared):
    size, unit, moved = pio.sizes(ctx, shared["facts"])
    known = [v for v in size.values() if v]
    brand = ctx.get("brand") or {}
    zones = shared.get("thermal_zones")
    if zones is None:
        zones = shared.get("zones_configured", 0)
    eq = pio.total(work, "overview/equipment.json") - pio.total(work, "overview/equipment-system.json")

    chat = []
    shown = shared.get("shown_sites") or set()
    unsized = [s["site_name"].strip() for s in ctx["sites"] if not size[s["site_id"]]]
    if unsized:
        chat.append("No building size in PEAK for %s: left out of the portfolio size and of the sustainability "
                    "ratings' portfolio row, the one row weighted by size." % io.listing(unsized))
    if moved:
        chat.append("Building sizes for %s show in %s, the unit most of the portfolio's floor area reads in, "
                    "converted from the square metres PEAK stores." % (io.listing(moved), unit))

    return {
        "masthead": {
            "client": ctx["client"],
            "title": "%s %s Performance Leaderboard" % (ctx["client"], pio.month_name(ctx)),
            "h1": "%s portfolio" % ctx["client"],
            "prepared": "Prepared by <strong>%s - %s</strong> · Powered by PEAK" % (brand.get("name", "CIM"),
                                                                                 brand.get("service", "Data Driven Operations")),
            "month": pio.month_name(ctx),
            "sites": len(shown) or len(ctx["sites"]),     # the sites with data somewhere in the report
            "shown": sorted(shown),
            "author": ctx["author"],
            "issued": io.day_short(ctx["today"]),
            "logo": None,                 # read at fill time, so a logo taken out of the plan stays out
        },
        "overview": {
            "label": "What we monitor across the %s portfolio, as at %s" % (ctx["client"], io.day_long(ctx["today"])),
            "stats": {
                "Portfolio size": (pio.num(sum(known)) + " <span>%s</span>" % unit) if known else "-",
                "Equipment": "{:,}".format(eq),
                "Sensors": "{:,}".format(pio.total(work, "overview/sensors.json")),
                "Rules running": "{:,}".format(pio.total(work, "overview/rules.json")),
                "Thermal zones": "{:,}".format(zones),
            },
        },
        "chat": chat,
    }
