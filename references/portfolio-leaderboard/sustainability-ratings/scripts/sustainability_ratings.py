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
    return io.pages_due(work, pulls(ctx))


def by_size(ctx, size):
    """The sites, largest building first, then by name."""
    return sorted(ctx["sites"], key=lambda s: (-(size.get(s["site_id"]) or 0), pio.name_key(s)))


def weighted(values, size):
    """The building-size-weighted mean of {site_id: value} over the sites that have both."""
    pairs = [(v, size.get(sid)) for sid, v in values.items() if v is not None and size.get(sid)]
    w = sum(s for _, s in pairs)
    return sum(v * s for v, s in pairs) / w if w else None


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


def ratings_by_site(work):
    """(rating types by id, {site: {measure: [ratings]}}) for every scored rating with a period end."""
    types, by = {}, defaultdict(lambda: defaultdict(list))
    for r in pio.rows(work, "ratings/ratings.json"):
        t = r.get("sustainability_rating_type") or {}
        if r.get("score") is None or not r.get("period_end_date"):
            continue
        types[r["sustainability_rating_type_id"]] = t
        for m in measures(t):
            by[r["site_id"]][m].append(r)
    return types, by


def latest_ratings(by):
    """{(site, measure): (latest rating, the one before of the same type)}. The latest rating decides the
    type; its history keeps to that type."""
    latest = {}
    for sid, site in by.items():
        for m, rows in site.items():
            rows.sort(key=lambda r: r["period_end_date"])
            kind = rows[-1]["sustainability_rating_type_id"]
            same = [r for r in rows if r["sustainability_rating_type_id"] == kind]
            latest[(sid, m)] = (same[-1], same[-2] if len(same) > 1 else None)
    return latest


class Cells:
    """A rating type's scale and precision, and the table cell a score takes on it. A type rated in
    fractions, or on a scale of ten points or fewer, prints to 1dp."""

    def __init__(self, types, by):
        self.types, self.frac = types, defaultdict(bool)
        for site in by.values():
            for rows in site.values():
                for r in rows:
                    t = types[r["sustainability_rating_type_id"]]
                    self.frac[r["sustainability_rating_type_id"]] |= (
                        r["score"] != int(r["score"]) or (t.get("max_score") or 0) - (t.get("min_score") or 0) <= 10)

    def show(self, score, tid):
        return "%.1f" % score if self.frac[tid] else "%d" % round(score)

    def cell(self, score, tid, expired=False, prev=None):
        t = self.types[tid]
        lo, hi = t.get("min_score") or 0.0, t.get("max_score") or 6.0
        c = {"value": self.show(score, tid),
             "pct": max(0.0, min(100.0, (score - lo) / (hi - lo) * 100 if hi > lo else 0)), "expired": expired}
        if prev is not None and not expired and self.show(prev, tid) != self.show(score, tid):
            c["move"] = "up" if score > prev else "down"     # an expired rating says how it stood, not where it is going
        return c


def portfolio_cell(cells, latest, size, m, live):
    """The portfolio row's cell for a measure: current ratings only, weighted by building size, and only
    where one rating type fills the column, since scales differ between types, and two or more sites
    hold one, since a single site's rating is not the portfolio's. Its arrow compares the same sites'
    previous ratings, weighted the same way."""
    cur = {sid: latest[(sid, mm)] for (sid, mm) in latest if mm == m and live(latest[(sid, mm)][0])}
    kinds = {c["sustainability_rating_type_id"] for c, _ in cur.values()}
    if len(kinds) != 1 or sum(1 for sid in cur if size.get(sid)) < 2:
        return None
    tid = kinds.pop()
    now = weighted({sid: c["score"] for sid, (c, _) in cur.items()}, size)
    if now is None:
        return None
    both = {sid: (c, p) for sid, (c, p) in cur.items() if p and size.get(sid)}
    before = after = None
    if both:
        after = weighted({sid: c["score"] for sid, (c, _) in both.items()}, size)
        before = weighted({sid: p["score"] for sid, (_, p) in both.items()}, size)
    c = cells.cell(now, tid)
    if before is not None and cells.show(after, tid) != cells.show(before, tid):
        c["move"] = "up" if after > before else "down"
    return c


def build(ctx, work, shared):
    today = io.d(ctx["today"])
    size, unit, _ = pio.sizes(ctx, shared["facts"])
    types, by = ratings_by_site(work)
    cells = Cells(types, by)
    live = lambda r: bool(r.get("expiry_date")) and io.d(r["expiry_date"]) >= today
    latest = latest_ratings(by)
    columns = sorted({m for (sid, m), (cur, _) in latest.items() if live(cur)}, key=column_key)
    if not columns:
        return {"drop": True}

    host = io.host(*ctx["sites"])
    link = lambda ids: "%s/dashboard/ratings?%s&ratings_type_id_or_filter=all_ratings" % (
        host, "&".join("site_ids=%s" % i for i in ids))
    rows, shown = [], []
    for s in by_size(ctx, size):
        sid = s["site_id"]
        row = []
        for m in columns:
            if (sid, m) not in latest:
                row.append(None)
                continue
            cur, prev = latest[(sid, m)]
            row.append(cells.cell(cur["score"], cur["sustainability_rating_type_id"], not live(cur),
                                  prev["score"] if prev else None))
        if any(row):
            shown.append(sid)
            rows.append({"name": s["site_name"].strip(), "state": pio.region(ctx, s), "link": link([sid]),
                         "size": pio.num(size[sid]), "cells": row})
    portfolio = [portfolio_cell(cells, latest, size, m, live) for m in columns]
    pio.shown(shared, shown)
    sized = [size[sid] for sid in shown if size[sid]]
    return {
        "ratings": {"unit": unit, "columns": columns, "rows": rows,
                    "portfolio": {"size": pio.num(sum(sized)) if sized else "-", "cells": portfolio}},
        "datelines": {"Sustainability ratings": "As at %s. Each site's latest rating for each measure."
                                                % io.day_long(ctx["today"])},
    }
