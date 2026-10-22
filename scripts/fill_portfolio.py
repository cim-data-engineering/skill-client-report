#!/usr/bin/env python3
"""Fill a scaffolded portfolio report from a data bundle.

    python3 scripts/fill_portfolio.py report-data.json --out report.html

Draws every portfolio component from the bundle: the masthead and its client logo,
the scorecard strip, the site and team leaderboard boards, the open P1-2 lists, the
ranked heatmaps, the win cards and the sustainability ratings table. The
band classes, change glyphs, link escaping, logo initials and photo crops are
fill_report.py's, imported as they are. Nothing here invents prose: the wins come in through the
bundle, written by the model, and every other string is a section script's.

The portfolio page carries no en or em dash, so the fill refuses to write one.
"""
import argparse
import html
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from fill_report import (EXTERNAL, IMPACTS, LEFT, MAX_PHOTOS, RIGHT, band, chg, href, initials,  # noqa: E402
                         photo_row, scaffold, win_groups)

TROPHY = ('<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" '
          'stroke-linecap="round" stroke-linejoin="round" role="img" aria-label="First place">'
          '<path d="M6 9H4.5a2.5 2.5 0 0 1 0-5H6"/><path d="M18 9h1.5a2.5 2.5 0 0 0 0-5H18"/><path d="M4 22h16"/>'
          '<path d="M10 14.66V17c0 .55-.47.98-.97 1.21C7.85 18.75 7 20.24 7 22"/>'
          '<path d="M14 14.66V17c0 .55.47.98.97 1.21C16.15 18.75 17 20.24 17 22"/>'
          '<path d="M18 2H6v7a6 6 0 0 0 12 0V2Z"/></svg>')
CLIMB = ('<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" '
         'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/>'
         '<polyline points="16 7 22 7 22 13"/></svg>')
CLAP = '<span class="clap" aria-hidden="true">&#x1F44F;</span>'
DASHES = re.compile("[\u2013\u2014]|&ndash;|&mdash;")
REGION = re.compile(r"[ \t]*<!-- fill: ([a-z-]+) -->\n(.*?)[ \t]*<!-- /fill: \1 -->\n?", re.S)
# A link out of the report, to PEAK or the shoutout form, that does not already name its target


def esc(s):
    """A PEAK string (a site, company, level or measure name, a ticket title) escaped for
    HTML, an en or em dash in it set as a hyphen."""
    return html.escape(re.sub("[\u2013\u2014]", "-", s or ""), quote=True)


def site_label(r, link=None):
    """'88 Example St (NSW)': the state in muted brackets, linked with a chevron when the row has a link."""
    inner = '<span class="sn">%s</span>%s' % (esc(r["name"]), ' <span class="rg">(%s)</span>' % esc(r["state"])
                                              if r.get("state") else "")
    return '<a href="%s">%s&nbsp;&rsaquo;</a>' % (href(link), inner) if link else inner


def jump(r, b):
    """A board name's link: the PEAK report its ranking gives it, opening in a new tab, or the
    anchor of the section that explains its figure, in this tab."""
    return '"%s"' % href(r["link"]) if r.get("link") else '"#%s" target="_self"' % b["anchor"]


def move(m):
    if m == "new":
        return '<span class="mv new">New</span>'
    if not m:
        return ""
    return '<span class="mv %s">%s%d</span>' % ("up" if m > 0 else "down", "&uarr;" if m > 0 else "&darr;", abs(m))


# ── leaderboard ─────────────────────────────────────────────────────────────
BUILDING = ('<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" '
            'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 21V5l8-3v19"/><path d="M12 21V9l8 3v9"/>'
            '<path d="M2 21h20"/><path d="M8 7v.01M8 11v.01M8 15v.01M16 14v.01M16 17v.01"/></svg>')


def ordinal(n):
    """'1st', '2nd', '13th'."""
    return "%d%s" % (n, "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th"))


def board(b):
    """One board, a small ranked table: the head; the leader set large under its building photo or
    beside its company's logo, its figure carrying the board's unit; the biggest climber, "None" when
    no one climbed, or no climber tier where the board has none; then the chasing pack. Every tier
    shares the rank column, so all the names start on one line."""
    lead, pack = b["rows"][0], b["rows"][1:]
    logos = any("tile" in r for r in b["rows"])
    mini = lambda r: tile((r.get("tile") or {}).get("company"), (r.get("tile") or {}).get("logo"), "tlogo")
    out = ['    <div class="rkcol">',
           '      <div class="rkhead"><h3 class="rkt">%s</h3><span>%s</span></div>' % (esc(b["title"]), b["window"])]
    if "photo" in lead:
        out.append('      <div class="lphoto%s">%s</div>' % (
            "" if lead["photo"] else " none",
            '<img src="%s" alt="%s">' % (lead["photo"], esc(lead["name"])) if lead["photo"] else BUILDING))
    out.append('      <div class="leader%s"><span class="rkmark">%s%s</span>%s%s<span class="lmeta">%s</span>'
               '<span class="lval">%s%s</span></div>' % (
                   " co" if logos else "", TROPHY, move(lead.get("move")),
                   '<span class="who">%s</span>' % tile(lead["tile"].get("company"), lead["tile"].get("logo")) if logos else "",
                   '<a href=%s class="lname"><span class="sn">%s</span>&nbsp;<span class="chev">&rsaquo;</span></a>' % (
                       jump(lead, b), esc(lead["name"])), " &middot; ".join(esc(x) for x in lead.get("meta") or []),
                   lead["value"], "<span>%s</span>" % esc(b["unit"]) if b.get("unit") else ""))
    if "climber" in b:
        c = b["climber"]
        out.append('      <div class="climb%s"><span class="rkmark">%s</span><p class="clab">Biggest climber</p>%s<p class="cwho%s">%s</p>%s</div>' % (
            " co" if logos else "", CLIMB, '<span class="clogo">%s</span>' % mini(c) if logos and c else "",
            "" if c else " none", '<a href=%s>%s</a>' % (jump(c, b), esc(c["name"])) if c else "None",
            '<span class="cup">&uarr;%d to %s</span>' % (c["places"], ordinal(c["rank"])) if c else ""))
    if pack:
        out += ['      <table class="rk">',
                '        <colgroup><col class="c-rank">%s<col><col class="c-mv"><col class="c-pv"></colgroup>'
                % ('<col class="c-logo">' if logos else ""),
                '        <tbody>']
        out += ['        <tr><td class="rank">%d</td>%s<td class="lv"><a href=%s>%s</a></td><td class="mvc">%s</td><td class="pv">%s</td></tr>'
                % (r["rank"], '<td class="lg">%s</td>' % mini(r) if logos else "", jump(r, b), esc(r["name"]),
                   move(r.get("move")), r["value"]) for r in pack]
        out += ['        </tbody>', '      </table>']
    out.append('    </div>')
    return "\n".join(out)


def shoutout(s):
    """The shoutout button beside the team leaderboard's title; nothing without one."""
    return '    <a class="shout" href="%s">%s%s</a>\n' % (href(s["url"]), CLAP, esc(s["text"])) if s else ""


def boards(bs):
    """The boards side by side."""
    n = len(bs)
    return ('  <div class="rkgrid%s">\n' % ("" if n == 3 else " n%d" % n)
            + "\n".join(board(b) for b in bs) + "\n  </div>\n")


# ── ranked heatmaps ─────────────────────────────────────────────────────────
def cell(v, t, dp, now):
    if v is None:
        return '<td class="c none">-</td>'
    return '<td class="c %s%s">%.*f</td>' % (band(round(v, dp), t), " now" if now else "", dp, v)


def change(mo, dp, given=False, value=None):
    """A row's Chg: its last month less its first, or for the portfolio row the `value` it was handed,
    which compares only the sites scored at both ends."""
    if given:
        return '<span class="chg flat">-</span>' if value is None else chg(round(value, dp), dp)
    if None in (mo[0], mo[-1]) or len(mo) < 2:
        return '<span class="chg flat">-</span>'
    return chg(round(mo[-1], dp) - round(mo[0], dp), dp)


def heatmap(d, months):
    dp, t = d["dp"], d["bands"]
    band = "band_unit" in d               # each site's comfort band, after its counts
    head = ['<th class="rank"></th>', '<th class="lv">Site</th>', '<th class="ct sz">Size <span class="u">%s</span></th>' % d["unit"]]
    head += ['<th class="ct">%s</th>' % c for c in d["counts"]]
    if band:
        head += ['<th class="ct bd">Target%s</th>' % (' <span class="u">%s</span>' % esc(d["band_unit"]) if d["band_unit"] else "")]
    head += ['<th class="mo">%s</th>' % m for m in months]
    head += ['<th class="cg">Chg</th>']
    body = []
    for r in d["rows"]:
        mo = r["months"]
        body.append('      <tr><td class="rank">%s</td><td class="lv">%s</td><td class="ct">%s</td>%s%s%s<td class="cg">%s</td></tr>'
                    % (TROPHY if r["rank"] == 1 else r["rank"], site_label(r, r.get("link")), r["size"],
                       "".join('<td class="ct">%s</td>' % c for c in r["counts"]),
                       '<td class="ct bd">%s</td>' % esc(r.get("band") or "-") if band else "",
                       "".join(cell(v, t, dp, i == len(mo) - 1) for i, v in enumerate(mo)), change(mo, dp)))
    p = d["portfolio"]
    body.append('      <tr class="total"><td></td><td class="lv">Portfolio</td><td class="ct">%s</td>%s%s%s<td class="cg">%s</td></tr>'
                % (p["size"], "".join('<td class="ct">%s</td>' % c for c in p["counts"]),
                   '<td class="ct bd"></td>' if band else "",
                   "".join(cell(v, t, dp, i == len(p["months"]) - 1) for i, v in enumerate(p["months"])),
                   change(p["months"], dp, "change" in p, p.get("change"))))
    return ('  <table class="hm wide">\n    <thead>\n      <tr>%s</tr>\n    </thead>\n    <tbody>\n%s\n    </tbody>\n  </table>\n'
            % ("".join(head), "\n".join(body)))


# ── open actions ────────────────────────────────────────────────────────────
def tile(company, logo, cls="logo"):
    """The company's logo in its square tile, its initials without one, empty for no company:
    the table's tile, or with cls "tlogo" the board's small one."""
    if not company:
        return '<span class="%s none"></span>' % cls
    co = esc(company)
    if logo:
        return '<span class="%s"><img src="%s" alt="%s" title="%s"></span>' % (cls, logo, co, co)
    return '<span class="%s none" title="%s">%s</span>' % (cls, co, esc(initials(company)))


AGE_CLASSES = ("a60", "a30", "a0")    # open 60 days or more, 30 to 60, under 30


def open_actions(d):
    """The open P1-2 backlog over the last year, then the lists side by side: each a ranked table under
    its head, the name over a bar on the list's own scale split by age, oldest first, and the count at
    the end."""
    out = []
    if d.get("backlog") and len(d["backlog"]["values"]) > 1:
        out.append(backlog_chart(d["backlog"]))
    out.append('  <div class="opgrid">')
    for p in d["panels"]:
        top = max(r["count"] for r in p["rows"])
        logos = any(r.get("tile") is not None for r in p["rows"])
        out += ['    <div class="oplist">',
                '      <div class="rkhead"><h3 class="rkt">%s</h3><span>Open P1-2</span></div>' % esc(p["title"]),
                '      <table class="op">',
                '        <colgroup><col class="c-rank">%s<col><col class="c-ct"></colgroup>'
                % ('<col class="c-logo">' if logos else ""),
                '        <tbody>']
        for r in p["rows"]:
            if r.get("state") is not None:
                name = site_label(r, r.get("link"))
            elif r.get("link"):
                name = '<a href="%s">%s&nbsp;&rsaquo;</a>%s' % (href(r["link"]), esc(r["name"]),
                                                               ' <span class="rg">%s</span>' % esc(r["company"]) if r.get("company") else "")
            else:
                name = '<span class="sn none">%s</span>' % esc(r["name"])
            bar = "".join('<span class="%s" style="width:calc(%.2f%% - 2px)"></span>' % (cls, n / top * 100)
                          for cls, n in zip(AGE_CLASSES, r["ages"]) if n)
            out.append('        <tr><td class="rank">%d</td>%s<td class="nm"><span class="ol">%s</span><span class="agebar">%s</span>'
                       '</td><td class="ct">%d</td></tr>'
                       % (r["rank"], '<td class="lg">%s</td>' % tile(r["tile"].get("company"), r["tile"].get("logo"), "tlogo")
                          if logos else "", name, bar, r["count"]))
        out += ['        </tbody>', '      </table>', '    </div>']
    out.append('  </div>')
    return "\n".join(out) + "\n"


# The backlog chart is shorter than the monthly charts, so it and both lists hold one page.
BL_VIEW, BL_BASE, BL_H = 150, 112, 78


def backlog_chart(d):
    """A bar a month end on one scale, split by age open as the list bars are, oldest at the base, the
    total on top; the last bar is the issue month, counted as at the issue date."""
    months, vals, stacks = d["months"], d["values"], d["stacks"]
    n = len(months)
    step = (RIGHT - LEFT - 40) / max(n - 1, 1)
    C = [LEFT + 20 + step * i for i in range(n)]
    w = min(44, step * (0.55 if n > 8 else 0.4))
    top = max(vals + [1]) * 1.08
    out = []
    for x, v, parts in zip(C, vals, stacks):
        y = BL_BASE
        for cls, part in zip(AGE_CLASSES, parts):
            if part:
                h = part / top * BL_H
                out.append('      <rect class="stk %s" x="%.1f" y="%.1f" width="%.1f" height="%.1f"/>'
                           % (cls, x - w / 2, y - h, w, max(h - 1, 0.5)))
                y -= h
        out.append('      <text class="val" x="%.1f" y="%.1f" text-anchor="middle">%d</text>' % (x, y - 6, v))
    out.append('      <line class="baseline" x1="%d" y1="%d" x2="%d" y2="%d"/>' % (LEFT, BL_BASE, RIGHT, BL_BASE))
    out += ['      <text class="axis" x="%.1f" y="%d" text-anchor="middle">%s</text>' % (x, BL_BASE + 16, m)
            for x, m in zip(C, months)]
    return "\n".join(['  <div class="chartblock backlog">',
                      '    <h3 class="charttitle">Backlog at month end</h3>',
                      '    <div class="chart">',
                      '      <svg viewBox="0 0 682 %d" role="img" aria-label="%s">' % (BL_VIEW, esc(d["alt"])),
                      "\n".join(out),
                      '      </svg>',
                      '    </div>',
                      '  </div>'])


# ── wins ────────────────────────────────────────────────────────────────────
def wins(ws, base, photos_out):
    blocks = []
    for wn, w in enumerate(ws, 1):
        photos = w.get("photos") or []
        if len(photos) > MAX_PHOTOS:
            sys.exit("fill: %d photos on %r, %d at most (references/portfolio-leaderboard/actions-and-wins/key-wins.md)"
                     % (len(photos), w["heading"], MAX_PHOTOS))
        side = len(photos) == 1
        pad = "      " if side else "    "
        b = pad + '<p class="wsite">%s</p>\n' % site_label(w["site"])
        if w.get("impact"):
            if w["impact"] not in IMPACTS:
                sys.exit("fill: unknown win impact %r, one of %s" % (w["impact"], ", ".join(IMPACTS)))
            b += pad + '<p class="impact %s"><i></i>%s</p>\n' % (w["impact"], IMPACTS[w["impact"]])
        b += pad + '<h3>%s</h3>\n' % w["heading"]
        if w.get("level"):
            lv = w["level"] if isinstance(w["level"], list) else [w["level"]]
            b += pad + '<p class="where"><span class="k">%s</span>%s</p>\n' % ("Levels" if len(lv) > 1 else "Level",
                                                                              ", ".join(esc(x) for x in lv))
        if photos and not side:
            b += pad + photo_row(photos, base, photos_out, "win%d" % wn) + "\n"
        b += pad + '<p>%s</p>\n' % w["body"]
        b += pad + '<p class="refs">' + " &middot; ".join('<a href="%s">%s</a>' % (href(r["url"]), esc(r["title"]))
                                                          for r in w["refs"]) + '</p>\n'
        if side:
            b = ('  <div class="win compact">\n    %s\n    <div class="wtext">\n%s    </div>\n  </div>'
                 % (photo_row(photos, base, photos_out, "win%d" % wn), b))
        else:
            b = '  <div class="win">\n' + b + '  </div>'
        blocks.append(b)
    return win_groups(ws, blocks) + "\n"


# ── sustainability ratings ──────────────────────────────────────────────────
def rating_cell(c):
    if not c:
        return '<td class="nb none">-</td>'
    arrow = {"up": '<span class="nbi up" title="Up from the rating before">&uarr;</span>',
             "down": '<span class="nbi down" title="Down from the rating before">&darr;</span>'}.get(c.get("move"),
                                                                                                   '<span class="nbi"></span>')
    return ('<td class="nb"><span class="scorecell nbs"><span class="track"><span class="fill" style="width:%.1f%%">'
            '</span></span><span class="sval">%s</span><span class="nbsfx"><span class="nbx">%s</span>%s</span></span></td>'
            % (c["pct"], c["value"], "*" if c.get("expired") else "", arrow))


def ratings(d):
    head = ('<th class="lv">Site</th><th class="ct">Size <span class="u">%s</span></th>' % d["unit"]
            + "".join('<th class="mo">%s</th>' % esc(c) for c in d["columns"]))
    body = ['      <tr><td class="lv">%s</td><td class="ct">%s</td>%s</tr>'
            % (site_label(r, r.get("link")), r["size"], "".join(rating_cell(c) for c in r["cells"])) for r in d["rows"]]
    p = d["portfolio"]
    body.append('      <tr class="total"><td class="lv">Portfolio</td><td class="ct">%s</td>%s</tr>'
                % (p["size"], "".join(rating_cell(c) for c in p["cells"])))
    return ('  <table class="hm nbt">\n    <thead>\n      <tr>%s</tr>\n    </thead>\n    <tbody>\n%s\n    </tbody>\n  </table>\n'
            % (head, "\n".join(body)))


# ── named slots ─────────────────────────────────────────────────────────────
def sub_one(s, pattern, repl, what):
    s2, n = re.subn(pattern, lambda m: repl, s, count=1, flags=re.S)
    if not n:
        sys.exit("fill: no %s in the scaffold" % what)
    return s2


def reference():
    with open(os.path.join(HERE, "..", "assets", "portfolio-report.html"), encoding="utf-8") as fh:
        return fh.read()


def after_eyebrow(s, eyebrow, tag_open, tag_close, text):
    """Rewrite the first `tag_open...tag_close` in the section an eyebrow heads. A section out of this
    report is passed over; an eyebrow the portfolio scaffold does not carry names no slot, and stops."""
    i = s.find('<p class="eyebrow">%s</p>' % eyebrow)
    if i == -1:
        if '<p class="eyebrow">%s</p>' % eyebrow not in reference():
            sys.exit("fill: no section headed %r in the portfolio scaffold: a section script names a slot that "
                     "does not exist" % eyebrow)
        return s                          # the section is out of this report
    k = s.find(tag_open, i, s.index("</section>", i))
    if k == -1:
        sys.exit("fill: the section headed %r has no %s to fill" % (eyebrow, tag_open))
    j = s.index(tag_close, k)
    return s[:k] + tag_open + text + s[j:]


def dated_head(s, title, head):
    """A section header whose eyebrow is a month, found by its title: the month, and the date line."""
    i = s.find("<h2>%s</h2>" % title)
    if i == -1:
        if "<h2>%s</h2>" % title not in reference():
            sys.exit("fill: no section titled %r in the portfolio scaffold" % title)
        return s                          # the section is out of this report
    j = s.rfind('<p class="eyebrow">', 0, i)
    s = s[:j] + '<p class="eyebrow">%s</p>' % esc(head["date"]) + s[s.index("</p>", j) + len("</p>"):]
    i = s.find("<h2>%s</h2>" % title)
    m = re.compile(r'<p class="h2note">[^<]*</p>').search(s, i)
    return s[:m.start()] + '<p class="h2note">%s</p>' % head["note"] + s[m.end():]


def fill_slots(s, D):
    m = D["masthead"]
    s = sub_one(s, r"<title>[^<]*</title>", "<title>%s</title>" % esc(m["title"]), "title")
    s = sub_one(s, r"<h1>[^<]*</h1>", "<h1>%s</h1>" % esc(m["h1"]), "h1")
    s = sub_one(s, r'<p class="prepared">.*?</p>', '<p class="prepared">%s</p>' % m["prepared"], "prepared by")
    for label, key in (("Sites", "sites"), ("Author", "author"), ("Issued", "issued")):
        s = sub_one(s, r"<dt>%s</dt><dd>[^<]*</dd>" % label, "<dt>%s</dt><dd>%s</dd>" % (label, esc(str(m[key]))), label)
    logo = ('<div class="clientlogo%s"><img src="%s" alt="%s"></div>' % (" tile" if m.get("logo_tile") else "",
                                                                       m["logo"], esc(m["client"]))
            if m.get("logo") else '<div class="clientlogo"></div>')
    s = sub_one(s, r'<div class="clientlogo">.*?</div>', logo, "client logo slot")
    o = D["overview"]
    s = sub_one(s, r'<section class="overview strip" aria-label="[^"]*">',
                '<section class="overview strip" aria-label="%s">' % esc(o["label"]), "scorecard strip")
    for label, value in o["stats"].items():
        s = sub_one(s, r'<p class="k">%s</p><p class="n">.*?</p>' % re.escape(label),
                    '<p class="k">%s</p><p class="n">%s</p>' % (label, value), "the %s stat" % label)
    for eyebrow, text in D.get("statements", {}).items():
        s = after_eyebrow(s, eyebrow, "<h2>", "</h2>", text)
    for eyebrow, text in D.get("datelines", {}).items():
        s = after_eyebrow(s, eyebrow, '<p class="h2note">', "</p>", text)
    for title, head in D.get("dated_heads", {}).items():
        s = dated_head(s, title, head)
    return s


# ── main ────────────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("data")
    ap.add_argument("--out", required=True)
    ap.add_argument("--photos-out", help="also save each win photo here, cropped exactly as embedded")
    a = ap.parse_args()
    if a.photos_out:
        os.makedirs(a.photos_out, exist_ok=True)
    D = json.load(open(a.data, encoding="utf-8"))
    sections = D.get("sections", "")

    s = scaffold(sections, "portfolio")

    months = D["months"]["quarter"]
    base = os.path.dirname(os.path.abspath(a.data))       # photo paths are relative to the bundle
    render = {"boards": lambda: boards(D["boards"]),
              "team-boards": lambda: boards(D["team_boards"]),
              "shoutout": lambda: shoutout(D.get("shoutout")),
              "eh-table": lambda: heatmap(D["equipment_health"], months),
              "cf-table": lambda: heatmap(D["comfort"], months),
              "open": lambda: open_actions(D["open_actions"]),
              "wins": lambda: wins(D["wins"], base, a.photos_out),
              "ratings": lambda: ratings(D["ratings"])}

    def region(m):
        name = m.group(1)
        if name not in render:
            sys.exit("fill: unknown fill region %r" % name)
        return render[name]()
    s = REGION.sub(region, s)
    s = fill_slots(s, D)
    # every external link opens in a new tab on its own, since some viewers drop the page's <base target>
    s = EXTERNAL.sub(r'<a\1 target="_blank" rel="noopener">', s)

    hits = DASHES.findall(s)
    if hits:
        i = DASHES.search(s).start()
        sys.exit("fill: %d en or em dash(es) in the portfolio output, first at: %r" % (len(hits), s[max(0, i - 60):i + 20]))
    open(a.out, "w", encoding="utf-8").write(s)
    n = s.count("<figure>")
    print("wrote %s" % a.out + (", %d KB with %d photos embedded" % (len(s) // 1024, n) if n else ""))


if __name__ == "__main__":
    main()
