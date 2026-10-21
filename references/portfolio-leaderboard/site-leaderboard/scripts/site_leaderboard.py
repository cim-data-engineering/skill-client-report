#!/usr/bin/env python3
"""The building performance leaderboard: three boards, each with its leader, the
chasing pack and the biggest climber. No calls of its own: it ranks the per-site
figures the equipment health, indoor environment and actions sections leave in
`shared`, so it builds after them. See
references/portfolio-leaderboard/site-leaderboard/site-leaderboard.md.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "scripts"))
import peak_io as io  # noqa: E402
import portfolio_io as pio  # noqa: E402

NAME = "site-leaderboard"
SHOWN = 10
BOARDS = [("equipment-health", "Equipment health leaders", "eh-by-site"),
          ("indoor-environment", "Thermal comfort leaders", "cf-by-site"),
          ("actions-by-company", "Actions resolved leaders", "actions-by-company")]


def calls(ctx):
    return []


def more(ctx, work):
    return []


def board(ctx, size, unit, figures, title, anchor, caption):
    now, start, dp = figures["now"], figures["start"], figures["dp"]
    sites = [s for s in ctx["sites"] if now.get(s["site_id"]) is not None]
    ranked = pio.rank(sites, lambda s: now[s["site_id"]])
    before = {s["site_id"]: k for k, s in pio.rank(sites, lambda s: start.get(s["site_id"]))}
    moves = {s["site_id"]: (before[s["site_id"]] - k if s["site_id"] in before else "new") for k, s in ranked}
    fmt = (lambda v: "%.*f" % (dp, v)) if dp else (lambda v: "{:,}".format(int(round(v))))
    rows = []
    for k, s in ranked[:SHOWN]:
        sid = s["site_id"]
        r = {"rank": k, "name": s["site_name"].strip(), "value": fmt(now[sid]), "move": moves[sid] or None}
        if k == 1:
            r["state"] = pio.state(s)
            r["size"] = "%s %s" % (pio.num(size[sid]), unit) if size.get(sid) else None
        rows.append(r)
    climbs = [m for m in moves.values() if m != "new" and m > 0]
    climber = None
    if climbs:
        top = max(climbs)
        names = [s["site_name"].strip() for k, s in ranked if moves[s["site_id"]] == top]
        climber = {"names": names, "places": top}
    return {"title": title, "anchor": anchor, "caption": caption, "rows": rows, "climber": climber}


def build(ctx, work, shared):
    figures = shared.get("boards") or {}
    if not figures:
        return {"drop": [NAME]}
    size, unit, _ = pio.sizes(ctx, shared["facts"])
    qm = ctx["quarter_months"]
    score_caption = "%s &middot; moves since %s" % (io.month_label(ctx, qm[-1]), io.month(qm[0]))
    boards = [board(ctx, size, unit, figures[key], title, anchor,
                    "This quarter &middot; moves since last quarter" if key == "actions-by-company" else score_caption)
              for key, title, anchor in BOARDS if key in figures]
    boards = [b for b in boards if b["rows"]]
    if not boards:
        return {"drop": [NAME]}
    n = len(ctx["sites"])
    return {"boards": {"boards": boards,
                       "note": "Top %d of %d sites on each board." % (SHOWN, n) if n > SHOWN else None}}
