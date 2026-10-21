#!/usr/bin/env python3
"""The leaderboard month's team leaderboard: a board for each team ranking handed on,
ranking the companies or the people holding the work, each with its leader, the
chasing pack and the biggest climber, every move against last month's board, and a
shoutout button for the first leader whose ranking carries one. No calls of its own: it
draws the team rankings in `shared`, so it builds after the sections that hand them on. See references/portfolio-leaderboard/team-leaderboard/team-leaderboard.md.
"""
import os
import sys
from urllib.parse import quote, urlencode

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "scripts"))
import portfolio_io as pio  # noqa: E402

NAME = "team-leaderboard"
SHOWN = 10
# The shoutout form: whom it thanks (their email), their site and the comment come prefilled;
# the sender fills in their own email.
SHOUTOUT_FORM = "https://airtable.com/app11XTZy9PtGOZwf/shrwYEpydoRJ62FzK"
COMMENT = "Nice job!"


def calls(ctx):
    return []


def more(ctx, work):
    return []


def shoutout(ranking, key):
    """The button thanking this one on the shoutout form, where the ranking carries their shoutout."""
    s = (ranking.get("shoutouts") or {}).get(key)
    if not s:
        return None
    query = urlencode([("prefill_assignee_shoutout_name", s["email"]), ("prefill_assignee_shoutout_site", s["site"]),
                       ("prefill_comment", COMMENT)], quote_via=quote)
    return {"text": "Send %s a shoutout" % s["first"], "url": "%s?%s" % (SHOUTOUT_FORM, query)}


def board(ctx, ranking):
    """The board for one team ranking, how many it ranks, and its leader's shoutout."""
    names, now = ranking["names"], ranking["now"]
    ranked, moves = pio.standings(list(names), now, ranking["start"], names.get)
    rows, links = [], ranking.get("links") or {}
    for k, key in ranked[:SHOWN]:
        r = {"rank": k, "name": names[key], "value": "{:,}".format(int(now[key])), "move": moves[key] or None,
             "link": links.get(key)}
        if k == 1:
            r["meta"] = ranking["meta"].get(key) or []
        if "tiles" in ranking:
            r["tile"] = ranking["tiles"].get(key) or {}
        rows.append(r)
    b = {"title": ranking["label"], "anchor": ranking.get("anchor"), "window": pio.board_window(ctx, ranking["window"]),
         "unit": ranking.get("unit"), "rows": rows, "noun": ranking["noun"]}
    if pio.climbers(ctx):                 # a portfolio of three sites or fewer shows no climber tier
        c = pio.climber(ranked[:SHOWN], moves)
        if c and "tiles" in ranking:
            c["tile"] = ranking["tiles"].get(c["key"]) or {}
        b["climber"] = dict(c, name=names[c["key"]], link=links.get(c["key"])) if c else None
    return b, len(ranked), shoutout(ranking, ranked[0][1]) if ranked else None


def build(ctx, work, shared):
    built = [x for x in (board(ctx, r) for r in shared.get("team_rankings") or []) if x[0]["rows"]]
    if not built:
        return {"drop": [NAME]}
    over = ["%d %s" % (n, b["noun"]) for b, n, _ in built if n > SHOWN]
    # one shoutout only: the first board's leader that carries one
    shout = next((s for _, _, s in built if s), None)
    return {"team_boards": [b for b, _, _ in built], "shoutout": shout,
            "dated_heads": {"Team leaderboard": pio.board_head(
                ctx, "by actions resolved", "Top %d of %s." % (SHOWN, " and ".join(over)) if over else None)}}
