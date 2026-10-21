#!/usr/bin/env python3
"""The leaderboard month's performance leaderboard: a board for each ranking handed
on, each with its leader, the chasing pack and the biggest climber, every move
against last month's board. No calls of its own: it draws the rankings in `shared`,
so it builds after the sections that hand them on. See
references/portfolio-leaderboard/site-leaderboard/site-leaderboard.md.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "scripts"))
import peak_io as io  # noqa: E402
import portfolio_io as pio  # noqa: E402

NAME = "site-leaderboard"
SHOWN = 10


def calls(ctx):
    return []


def more(ctx, work):
    return []


def board(ctx, size, unit, ranking, caption):
    now, start, dp = ranking["now"], ranking["start"], ranking["dp"]
    sites = [s for s in ctx["sites"] if now.get(s["site_id"]) is not None]
    ranked = pio.rank(sites, lambda s: now[s["site_id"]])
    # last month's board: every site with a figure on the window it ranked, on the board now or not
    before = {s["site_id"]: k for k, s in pio.rank(ctx["sites"], lambda s: start.get(s["site_id"]))}
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
    return {"title": "%s leaders" % ranking["label"], "anchor": ranking["anchor"], "caption": caption, "rows": rows,
            "climber": climber}


def build(ctx, work, shared):
    rankings = shared.get("rankings") or []
    if not rankings:
        return {"drop": [NAME]}
    size, unit, _ = pio.sizes(ctx, shared["facts"])
    qm = ctx["quarter_months"]
    since = "moves since %s" % io.month(qm[-2])
    captions = {"month": "%s &middot; %s" % (io.month(qm[-1]), since),
                "quarter": "%s &middot; %s" % (pio.span(qm[0], qm[-1]), since)}
    boards = [board(ctx, size, unit, r, captions[r["window"]]) for r in rankings]
    boards = [b for b in boards if b["rows"]]
    if not boards:
        return {"drop": [NAME]}
    n = len(ctx["sites"])
    return {"boards": {"boards": boards,
                       "note": "Top %d of %d sites on each board." % (SHOWN, n) if n > SHOWN else None},
            "statements": {"Site rankings": "%s performance leaderboard" % pio.month_name(ctx)}}
