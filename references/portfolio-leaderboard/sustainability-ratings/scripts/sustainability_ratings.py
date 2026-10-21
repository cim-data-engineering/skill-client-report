#!/usr/bin/env python3
"""Sustainability ratings by site: each site's latest rating for each measure, on its
own rating type's scale, with a building-size-weighted portfolio row. See
references/portfolio-leaderboard/sustainability-ratings/sustainability-ratings.md.

Every portfolio report fetches the ratings, and build() drops the section when no
site holds a current one.
"""
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "scripts"))
import peak_io as io  # noqa: E402
import portfolio_io as pio  # noqa: E402

NAME = "sustainability-ratings"
PAGE = 200
FIRST = ["energy", "indoor environment", "water"]   # column order; any other measure follows alphabetically
UNMEASURED = "Other"                                # PEAK's catch-all measure, and the column for a type naming none
IMPLIED = {"indoor": "Indoor environment"}          # measures PEAK has no option for, read from a type's name


def pulls(ctx):
    return pio.split(ctx, "ratings/ratings.json", len(ctx["sites"]), lambda f, ids: io.gql(
        f, "platform.sustainability_ratings", {"site_ids": ids, "limit": PAGE},
        ["site_id", "score", "period_end_date", "expiry_date", "sustainability_rating_type_id",
         "sustainability_rating_type.name", "sustainability_rating_type.min_score",
         "sustainability_rating_type.max_score", "sustainability_rating_type.sustainability_rating_measures.name"]))


def calls(ctx):
    return pulls(ctx)


def more(ctx, work):
    return pio.pages_due(work, pulls(ctx), PAGE, nested=True)


def measures(t):
    """The measures a rating type rates. PEAK offers only energy, water, waste and Other, so a type rating
    Other, or naming no measure, takes the measure its name implies, if any."""
    names = [m["name"].strip() for m in t.get("sustainability_rating_measures") or [] if m.get("name")]
    title = (t.get("name") or "").lower()
    implied = next((v for k, v in IMPLIED.items() if k in title), UNMEASURED)
    return list(dict.fromkeys(implied if n.lower() == UNMEASURED.lower() else n for n in names or [UNMEASURED]))


def column_key(name):
    n = name.strip().lower()
    return (FIRST.index(n), "") if n in FIRST else (len(FIRST), n)


def build(ctx, work, shared):
    today = io.d(ctx["today"])
    size, unit, _ = pio.sizes(ctx, shared["facts"])
    types, by = {}, defaultdict(lambda: defaultdict(list))     # site -> measure -> ratings
    for r in pio.rows(work, "ratings/ratings.json", PAGE):
        t = r.get("sustainability_rating_type") or {}
        if r.get("score") is None or not r.get("period_end_date"):
            continue
        tid = r["sustainability_rating_type_id"]
        types[tid] = t
        for m in measures(t):
            by[r["site_id"]][m].append(r)

    # A type's precision: halves on a scale of ten points or fewer, or any fractional score, print to 1dp.
    frac = defaultdict(bool)
    for site in by.values():
        for rows in site.values():
            for r in rows:
                t = types[r["sustainability_rating_type_id"]]
                frac[r["sustainability_rating_type_id"]] |= (r["score"] != int(r["score"])
                                                             or (t.get("max_score") or 0) - (t.get("min_score") or 0) <= 10)
    live = lambda r: bool(r.get("expiry_date")) and io.d(r["expiry_date"]) >= today

    # Per site and measure, the latest rating decides the type; its history keeps to that type.
    latest = {}
    for sid, site in by.items():
        for m, rows in site.items():
            rows.sort(key=lambda r: r["period_end_date"])
            kind = rows[-1]["sustainability_rating_type_id"]
            same = [r for r in rows if r["sustainability_rating_type_id"] == kind]
            latest[(sid, m)] = (same[-1], same[-2] if len(same) > 1 else None)
    columns = sorted({m for (sid, m), (cur, _) in latest.items() if live(cur)}, key=column_key)
    if not columns:
        return {"drop": [NAME]}

    def scale(tid):
        t = types[tid]
        return t.get("min_score") or 0.0, t.get("max_score") or 6.0

    def show(score, tid):
        return "%.1f" % score if frac[tid] else "%d" % round(score)

    def cell(score, tid, expired=False, prev=None):
        lo, hi = scale(tid)
        c = {"value": show(score, tid), "pct": max(0.0, min(100.0, (score - lo) / (hi - lo) * 100 if hi > lo else 0)),
             "expired": expired}
        if prev is not None and show(prev, tid) != show(score, tid):
            c["move"] = "up" if score > prev else "down"
        return c

    host = pio.host(ctx)
    link = lambda ids: "%s/dashboard/ratings?%s&ratings_type_id_or_filter=all_ratings" % (
        host, "&".join("site_ids=%s" % i for i in ids))
    rows, shown = [], []
    for s in pio.by_size(ctx, size):
        sid = s["site_id"]
        cells = []
        for m in columns:
            if (sid, m) not in latest:
                cells.append(None)
                continue
            cur, prev = latest[(sid, m)]
            cells.append(cell(cur["score"], cur["sustainability_rating_type_id"], not live(cur),
                              prev["score"] if prev else None))
        if any(cells):
            shown.append(sid)
            rows.append({"name": s["site_name"].strip(), "state": pio.state(s), "link": link([sid]),
                         "size": pio.num(size[sid]), "cells": cells})

    # The portfolio row: current ratings only, weighted by building size, and only where one rating
    # type fills the column, since scales differ between types. Its arrow compares the same sites'
    # previous ratings, weighted the same way.
    portfolio = []
    for m in columns:
        cur = {sid: latest[(sid, mm)] for (sid, mm) in latest if mm == m and live(latest[(sid, mm)][0])}
        kinds = {c["sustainability_rating_type_id"] for c, _ in cur.values()}
        if len(kinds) != 1:
            portfolio.append(None)
            continue
        tid = kinds.pop()
        now = pio.weighted({sid: c["score"] for sid, (c, _) in cur.items()}, size)
        if now is None:
            portfolio.append(None)
            continue
        both = {sid: (c, p) for sid, (c, p) in cur.items() if p and size.get(sid)}
        before = after = None
        if both:
            after = pio.weighted({sid: c["score"] for sid, (c, _) in both.items()}, size)
            before = pio.weighted({sid: p["score"] for sid, (_, p) in both.items()}, size)
        c = cell(now, tid)
        if before is not None and show(after, tid) != show(before, tid):
            c["move"] = "up" if after > before else "down"
        portfolio.append(c)
    if any(portfolio):
        shared["weighted"] = True
    sized = [size[sid] for sid in shown if size[sid]]
    return {
        "ratings": {"unit": unit, "columns": columns, "rows": rows,
                    "portfolio": {"size": pio.num(sum(sized)) if sized else "-", "cells": portfolio}},
        "links": {"ratings": link(pio.ids(ctx))},
        "datelines": {"Sustainability ratings": "As at %s. Each site's latest rating for each measure."
                                                % io.day_long(ctx["today"])},
        "notes": {"Sustainability ratings": {"order": 4, "html": "<strong>Sustainability ratings.</strong> The "
                                                                 "portfolio row counts current ratings only, and its "
                                                                 "arrow compares the same sites' previous ratings."}},
    }
