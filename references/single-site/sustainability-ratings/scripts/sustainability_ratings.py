#!/usr/bin/env python3
"""Sustainability ratings: a card per NABERS measure and each one's rating history.
See references/single-site/sustainability-ratings/sustainability-ratings.md.

Not one of the section choices. report.py adds it to every report, and build()
drops it when PEAK holds no current rating for the site.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "scripts"))
import peak_io as io  # noqa: E402

# The measures the section shows, in card and chart order, each found by a word in the
# PEAK rating type name. Waste and every non-NABERS type stay out.
MEASURES = [("Energy", "energy"), ("Indoor environment", "indoor"), ("Water", "water")]


def calls(ctx):
    return [io.gql("ratings/ratings.json", "platform.sustainability_ratings",
                   {"site_id": ctx["site"]["site_id"], "limit": 200},
                   ["sustainability_rating_id", "score", "period_end_date", "expiry_date",
                    "sustainability_rating_type.name", "sustainability_rating_type.max_score"])]


def more(ctx, work):
    return []


def measure(type_name):
    n = (type_name or "").lower()
    if "nabers" not in n or "waste" in n:
        return None
    return next((label for label, word in MEASURES if word in n), None)


def mon_year(day):
    x = io.d(day)
    return "%s %d" % (io.MONTHS[x.month - 1][:3], x.year)


def half_year(x, up=False):
    """The 1 January or 1 July at or before x; with up, the first one after x."""
    start = io.d("%d-%02d-01" % (x.year, 1 if x.month < 7 else 7))
    return io.add_months(start, 6) if up else start


def build(ctx, work, shared):
    today = io.d(ctx["today"])
    by = {}
    for r in work.get("ratings/ratings.json").rows:
        t = r.get("sustainability_rating_type") or {}
        label = measure(t.get("name"))
        if label and r.get("score") is not None and r.get("period_end_date"):
            # PEAK's period end is exclusive: the rating period's last day is the day before
            by.setdefault(label, []).append(dict(r, type=t["name"], max=t.get("max_score") or 6.0,
                                                 end=io.last_day(r["period_end_date"]).isoformat()))
    for rows in by.values():
        rows.sort(key=lambda r: r["end"])
        # Energy can be rated base building or whole building, and the two are not
        # comparable, so a measure carries only the rating type of its latest rating.
        kind = rows[-1]["type"]
        rows[:] = [r for r in rows if r["type"] == kind]

    # A measure is current when its latest rating has not expired by the issue date. One
    # current measure brings the section in, and then every measure with a rating shows.
    live = lambda rows: bool(rows[-1].get("expiry_date")) and io.d(rows[-1]["expiry_date"]) >= today
    shown = [label for label, _ in MEASURES if label in by]
    if not any(live(by[label]) for label in shown):
        return {"drop": True}

    cards, charts = [], []
    for label in shown:
        rows = by[label]
        cur = rows[-1]
        card = {"name": label, "score": cur["score"], "max": cur["max"]}
        if live(rows):
            card["expires"] = mon_year(cur["expiry_date"])
        else:
            card["expired"] = True
        if len(rows) > 1:
            prev = rows[-2]["score"]
            c = round(cur["score"] - prev, 1)
            card["delta"] = {"dir": "up" if c > 0 else "down" if c < 0 else "flat",
                             "amount": "%.1f" % abs(c), "from": "%.1f" % prev}
        cards.append(card)
        vals = [r["score"] for r in rows]
        lo, hi = max(0.0, min(vals) - 0.5), min(cur["max"], max(vals) + 0.5)
        charts.append({"name": label, "lo": lo, "hi": hi,
                       "axis": [half_year(io.d(rows[0]["end"])).isoformat(),
                                half_year(io.d(cur["end"]), up=True).isoformat()],
                       "points": [[r["end"], r["score"]] for r in rows],
                       "alt": "%s chart of the NABERS %s rating by the end of each rating period, between %.1f and "
                              "%.1f stars: %s." % ("Line" if len(rows) > 1 else "Point", label.lower(), lo, hi,
                                                   ", ".join("%.1f for the period to %s" % (r["score"], mon_year(r["end"]))
                                                             for r in rows))})

    host = io.host(ctx["site"])
    link = "%s/dashboard/ratings?site_ids=%s&ratings_type_id_or_filter=all_ratings" % (host, ctx["site"]["site_id"])

    return {"ratings": {"cards": cards, "charts": charts},
            "links": {"ratings": link},
            "datelines": {"Sustainability ratings": "As at %s. Each rating is plotted at the end of its rating "
                                                    "period." % io.day_long(ctx["today"])}}
