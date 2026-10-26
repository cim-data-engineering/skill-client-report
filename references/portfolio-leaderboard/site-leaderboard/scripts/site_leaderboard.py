#!/usr/bin/env python3
"""The leaderboard month's site leaderboard: a board for each ranking handed
on, each with its leader under the building's photo, the biggest climber and the
chasing pack, every move against last month's board. No PEAK calls of its own: it
draws the rankings in `shared`, so it builds after the sections that hand them on,
and fetches each leader's photo from the link in the site facts. See
references/portfolio-leaderboard/site-leaderboard/site-leaderboard.md.
"""
import base64
import os
import sys
import urllib.request
from io import BytesIO

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "scripts"))
import peak_io as io  # noqa: E402
import portfolio_io as pio  # noqa: E402

SHOWN = 10
PHOTO_W = 560           # the leader's photo band, 2:1, at about twice its printed width


def calls(ctx):
    return []


def more(ctx, work):
    return []


def photo(url):
    """The building's photo as a JPEG data URI, cropped to the leader's 2:1 band; None when it cannot be fetched."""
    try:
        from PIL import Image, ImageOps
    except ImportError:
        sys.exit("the leaders' building photos need Pillow: pip install pillow")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "client-report"})
        with urllib.request.urlopen(req, timeout=20) as r:
            im = Image.open(BytesIO(r.read()))
            im.load()
    except (OSError, ValueError):
        return None
    im = ImageOps.exif_transpose(im).convert("RGB")
    w = min(PHOTO_W, im.width)
    im = ImageOps.fit(im, (w, w // 2), Image.LANCZOS, centering=(0.5, 0.4))
    buf = BytesIO()
    im.save(buf, "JPEG", quality=82, optimize=True)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def board(ctx, size, unit, ranking):
    """The board for one ranking, and the site that leads it."""
    now, start, dp = ranking["now"], ranking["start"], ranking["dp"]
    site = {s["site_id"]: s for s in ctx["sites"]}
    name = lambda sid: site[sid]["site_name"].strip()
    low = set(ranking.get("low") or ())
    ranked, moves = pio.standings(list(site), now, start, name, low)
    fmt = (lambda v: "%.*f" % (dp, v)) if dp else (lambda v: "{:,}".format(int(round(v))))
    rows = []
    links = ranking.get("links") or {}
    for k, sid in ranked[:SHOWN]:
        r = {"rank": k, "name": name(sid), "value": fmt(now[sid]), "move": moves[sid] or None, "link": links.get(sid),
             "low": sid in low}
        if k == 1:
            r["meta"] = [x for x in (pio.region(ctx, site[sid]),
                                     "%s %s" % (pio.num(size[sid]), unit) if size.get(sid) else None) if x]
        rows.append(r)
    b = {"title": ranking["label"], "anchor": ranking.get("anchor"), "window": pio.board_window(ctx, ranking["window"]),
         "unit": ranking.get("unit"), "rows": rows}
    if pio.climbers(ctx):                 # a portfolio of three sites or fewer shows no climber tier
        c = pio.climber(ranked[:SHOWN], moves)
        b["climber"] = dict(c, name=name(c["key"]), link=links.get(c["key"]), low=c["key"] in low) if c else None
    return b, (ranked[0][1] if ranked else None), len(ranked)


def build(ctx, work, shared):
    size, unit, _ = pio.sizes(ctx, shared["facts"])
    made = [board(ctx, size, unit, r) for r in shared.get("rankings") or []]
    built = [(b, sid) for b, sid, _ in made if b["rows"]]
    if not built:
        return {"drop": True}
    counts = sorted({n for b, _, n in made if b["rows"]})
    # each leader's building photo, fetched once however many boards it leads
    links, photos = {}, {}
    for b, sid in built:
        if sid not in photos:
            links[sid] = (shared["facts"].get(sid) or {}).get("photo_url")
            photos[sid] = photo(links[sid]) if links[sid] else None
        b["rows"][0]["photo"] = photos[sid]
    chat = []
    bare = [b["rows"][0]["name"] for b, sid in built if not photos[sid]]
    bare = list(dict.fromkeys(bare))
    if bare:
        chat.append("No building photo in PEAK%s for %s, so %s leader panel shows a plain building mark."
                    % ("" if not any(links[sid] for b, sid in built if not photos[sid]) else ", or none that could be fetched,",
                       io.listing(bare), "its" if len(bare) == 1 else "each"))
    drawn = [r for r, (b, _, _) in zip(shared["rankings"], made) if b["rows"]]
    # the boards showing a site too small to lead, starred and ranked after the rest, each named once under them
    starred = [r["low_note"] for r, (b, _, _) in zip(shared["rankings"], made) if any(x["low"] for x in b["rows"])]
    note = ("* %s, ranked after the other sites." % " or ".join(starred[:1] + [n.lower() for n in starred[1:]])
            if starred else None)
    more = list(dict.fromkeys(r["note"] for r in drawn if r.get("note")))   # each note once
    cut = [n for n in counts if n > SHOWN]
    if cut:
        more.append("Top %d of %s sites on %s." % (
            SHOWN, "%d" % cut[0] if len(cut) == 1 else "%d to %d" % (cut[0], cut[-1]),
            "each board" if len(cut) == len(counts) else "the boards that rank more"))
    return {"boards": [b for b, _ in built], "boards_note": note, "chat": chat,
            "dated_heads": {"Site leaderboard": pio.board_head(ctx, "the sites on one measure", " ".join(more) or None)}}
