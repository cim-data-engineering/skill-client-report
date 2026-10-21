#!/usr/bin/env python3
"""Fill a scaffolded portfolio report from a data bundle.

    python3 scripts/fill_portfolio.py report-data.json --out report.html

Draws every portfolio component from the bundle: the masthead and its client logo,
the scorecard strip, the leaderboard boards, the ranked heatmaps, the company
table, the win cards and the sustainability ratings table. The band classes,
change glyphs, link escaping, logo initials and photo crops are fill_report.py's,
imported as they are. Nothing here invents prose: the wins come in through the
bundle, written by the model, and every other string is a section script's.

The portfolio page carries no en or em dash, so the fill refuses to write one.
"""
import argparse
import html
import json
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from fill_report import IMPACTS, MAX_PHOTOS, band, chg, href, initials, photo_row  # noqa: E402

TROPHY = ('<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" '
          'stroke-linecap="round" stroke-linejoin="round" role="img" aria-label="First place">'
          '<path d="M6 9H4.5a2.5 2.5 0 0 1 0-5H6"/><path d="M18 9h1.5a2.5 2.5 0 0 0 0-5H18"/><path d="M4 22h16"/>'
          '<path d="M10 14.66V17c0 .55-.47.98-.97 1.21C7.85 18.75 7 20.24 7 22"/>'
          '<path d="M14 14.66V17c0 .55.47.98.97 1.21C16.15 18.75 17 20.24 17 22"/>'
          '<path d="M18 2H6v7a6 6 0 0 0 12 0V2Z"/></svg>')
CLIMB = ('<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" '
         'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/>'
         '<polyline points="16 7 22 7 22 13"/></svg>')
DASHES = re.compile("[\u2013\u2014]|&ndash;|&mdash;")
REGION = re.compile(r"[ \t]*<!-- fill: ([a-z-]+) -->\n(.*?)[ \t]*<!-- /fill: \1 -->\n?", re.S)
SITES_LINE = 76         # characters the company sites line's two lines hold, site names, open counts and the rest


def esc(s):
    """A PEAK string (a site, company, level or measure name, a ticket title) escaped for
    HTML, an en or em dash in it set as a hyphen."""
    return html.escape(re.sub("[\u2013\u2014]", "-", s or ""), quote=True)


def site_label(r, link=None):
    """'88 Example St (NSW)': the state in muted brackets, linked with a chevron when the row has a link."""
    inner = '<span class="sn">%s</span>%s' % (esc(r["name"]), ' <span class="rg">(%s)</span>' % esc(r["state"])
                                              if r.get("state") else "")
    return '<a href="%s">%s&nbsp;&rsaquo;</a>' % (href(link), inner) if link else inner


def anchor(name, anchor_id, cls=None):
    """A site name that jumps to its section in this document, in this tab."""
    return '<a href="#%s" target="_self"%s><span class="sn">%s</span>&nbsp;<span class="chev">&rsaquo;</span></a>' % (
        anchor_id, ' class="%s"' % cls if cls else "", esc(name))


def move(m):
    if m == "new":
        return '<span class="mv new">New</span>'
    if not m:
        return ""
    return '<span class="mv %s">%s%d</span>' % ("up" if m > 0 else "down", "&uarr;" if m > 0 else "&darr;", abs(m))


# ── leaderboard ─────────────────────────────────────────────────────────────
def board(b):
    lead, pack = b["rows"][0], b["rows"][1:]
    out = ['    <div class="rkcol">',
           '      <h3 class="charttitle">%s</h3>' % esc(b["title"]),
           '      <p class="rkcap">%s</p>' % b["caption"],
           '      <div class="leader">',
           '        <p class="llab">%s<span>Leader</span></p>' % TROPHY,
           '        <div class="lrow">%s<span class="lval">%s</span></div>' % (anchor(lead["name"], b["anchor"], "lname"),
                                                                            lead["value"]),
           '        <div class="lrow lmeta"><span>%s</span>%s</div>' % (" &middot; ".join(
               x for x in (esc(lead.get("state")), lead.get("size")) if x), move(lead.get("move"))),
           '      </div>']
    if pack:
        out += ['      <table class="rk">',
                '        <colgroup><col class="c-rank"><col><col class="c-mv"><col class="c-pv"></colgroup>',
                '        <tbody>']
        out += ['        <tr><td class="rank">%d</td><td class="lv">%s</td><td class="mvc">%s</td><td class="pv">%s</td></tr>'
                % (r["rank"], anchor(r["name"], b["anchor"]), move(r.get("move")), r["value"]) for r in pack]
        out += ['        </tbody>', '      </table>']
    c = b.get("climber")
    if c:
        who = ("%d sites" % len(c["names"]) if len(c["names"]) > 2
               else " and ".join(anchor(n, b["anchor"], "cname") for n in c["names"]))
        out += ['      <div class="climb">',
                '        <div class="lrow"><p class="llab">%s<span>Biggest climber</span></p>'
                '<span class="delta pos">&uarr; %d place%s</span></div>' % (CLIMB, c["places"], "" if c["places"] == 1 else "s"),
                '        <div class="cwho">%s</div>' % who,
                '      </div>']
    out.append('    </div>')
    return "\n".join(out)


def boards(d):
    n = len(d["boards"])
    tall = any(len((b.get("climber") or {}).get("names", [])) == 2 for b in d["boards"])
    return ('  <div class="rkgrid%s%s">\n' % ("" if n == 3 else " n%d" % n, " tall" if tall else "")
            + "\n".join(board(b) for b in d["boards"]) + "\n  </div>\n")


# ── ranked heatmaps ─────────────────────────────────────────────────────────
def cell(v, t, dp, now):
    if v is None:
        return '<td class="c none">-</td>'
    return '<td class="c %s%s">%.*f</td>' % (band(round(v, dp), t), " now" if now else "", dp, v)


def change(mo, dp):
    if None in (mo[0], mo[-1]) or len(mo) < 2:
        return '<span class="chg flat">-</span>'
    return chg(round(mo[-1], dp) - round(mo[0], dp), dp)


def heatmap(d, months):
    dp, t = d["dp"], d["bands"]
    head = ['<th class="rank"></th>', '<th class="lv">Site</th>', '<th class="ct sz">Size <span class="u">%s</span></th>' % d["unit"]]
    head += ['<th class="ct">%s</th>' % c for c in d["counts"]]
    head += ['<th class="mo">%s</th>' % m for m in months]
    head += ['<th class="cg">Chg</th>']
    body = []
    for r in d["rows"]:
        mo = r["months"]
        body.append('      <tr><td class="rank">%s</td><td class="lv">%s</td><td class="ct">%s</td>%s%s<td class="cg">%s</td></tr>'
                    % (TROPHY if r["rank"] == 1 else r["rank"], site_label(r, r.get("link")), r["size"],
                       "".join('<td class="ct">%s</td>' % c for c in r["counts"]),
                       "".join(cell(v, t, dp, i == len(mo) - 1) for i, v in enumerate(mo)), change(mo, dp)))
    p = d["portfolio"]
    body.append('      <tr class="total"><td></td><td class="lv">Portfolio</td><td class="ct">%s</td>%s%s<td class="cg">%s</td></tr>'
                % (p["size"], "".join('<td class="ct">%s</td>' % c for c in p["counts"]),
                   "".join(cell(v, t, dp, i == len(p["months"]) - 1) for i, v in enumerate(p["months"])),
                   change(p["months"], dp)))
    return ('  <table class="hm wide">\n    <thead>\n      <tr>%s</tr>\n    </thead>\n    <tbody>\n%s\n    </tbody>\n  </table>\n'
            % ("".join(head), "\n".join(body)))


# ── companies ───────────────────────────────────────────────────────────────
def scorecell(pct):
    return ('<span class="scorecell"><span class="track"><span class="fill" style="width:%.1f%%"></span></span>'
            '<span class="sval">%.1f%%</span></span>' % (pct, pct))


def companies(d):
    rows = []
    for r in d["rows"]:
        co = esc(r["company"])
        tile = ('<span class="logo"><img src="%s" alt="%s" title="%s"></span>' % (r["logo"], co, co) if r.get("logo")
                else '<span class="logo none" title="%s">%s</span>' % (co, esc(initials(r["company"]))))
        label = lambda s: s["name"] + (" %d open" % s["open"] if s["open"] else "")
        # Two lines hold about SITES_LINE characters: past that, one site is named, so the count of the rest shows
        rest = len(r["sites"]) - 2
        two = len(" · ".join(label(s) for s in r["sites"][:2])) + (len(" · +%d more sites" % rest) if rest > 0 else 0)
        k = 2 if two <= SITES_LINE else 1
        named = ['<span class="vs">%s%s</span>' % (esc(s["name"]), " <b>%d open</b>" % s["open"] if s["open"] else "")
                 for s in r["sites"][:k]]
        if len(r["sites"]) > k:
            more = len(r["sites"]) - k
            named.append('<span class="vs more">+%d more site%s</span>' % (more, "" if more == 1 else "s"))
        line = '<span class="sep"> &middot; </span>'.join(named)
        res, op = r["resolved"], r["open"]
        rows.append('      <tr><td class="rank">%s%s</td><td class="assignee"><span class="who">%s<span class="nm"><span class="co-name">%s</span>'
                    '<span class="vsites">%s</span></span></span></td><td class="num">%d</td><td class="num">%s</td>'
                    '<td>%s</td><td class="num %s">%d</td></tr>'
                    % (TROPHY if r["rank"] == 1 else r["rank"], move(r.get("move")), tile, co, line, len(r["sites"]), f"{res:,}",
                       scorecell(res / (res + op) * 100 if res + op else 0), "open-zero" if op == 0 else "open-hot", op))
    t = d["total"]
    res, op = t["resolved"], t["open"]
    rows.append('      <tr class="total"><td></td><td>Total</td><td class="num"></td><td class="num">%s</td><td>%s</td>'
                '<td class="num">%s</td></tr>' % (f"{res:,}", scorecell(res / (res + op) * 100 if res + op else 0), f"{op:,}"))
    return ('  <table class="lbt vend">\n    <thead>\n      <tr><th></th><th>Company</th><th class="num">Sites</th>'
            '<th class="num">Resolved</th><th>Completion rate</th><th class="num">Open now</th></tr>\n    </thead>\n'
            '    <tbody>\n%s\n    </tbody>\n  </table>\n' % "\n".join(rows))


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
    return "\n\n".join(blocks) + "\n"


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


def notes(items):
    return ("  <ol>\n" + "\n".join("    <li>%s</li>" % n["html"] for n in sorted(items.values(), key=lambda n: n["order"]))
            + "\n  </ol>\n")


# ── named slots ─────────────────────────────────────────────────────────────
def sub_one(s, pattern, repl, what):
    s2, n = re.subn(pattern, lambda m: repl, s, count=1, flags=re.S)
    if not n:
        sys.exit("fill: no %s in the scaffold" % what)
    return s2


def after_eyebrow(s, eyebrow, tag_open, tag_close, text):
    i = s.find('<p class="eyebrow">%s</p>' % eyebrow)
    if i == -1:
        return s                          # the section is out of this report
    k = s.index(tag_open, i)
    j = s.index(tag_close, k)
    return s[:k] + tag_open + text + s[j:]


def fill_slots(s, D):
    m = D["masthead"]
    s = sub_one(s, r"<title>[^<]*</title>", "<title>%s</title>" % esc(m["title"]), "title")
    s = sub_one(s, r"<h1>[^<]*</h1>", "<h1>%s</h1>" % esc(m["h1"]), "h1")
    s = sub_one(s, r'<p class="prepared">.*?</p>', '<p class="prepared">%s</p>' % m["prepared"], "prepared by")
    for label, key in (("Month", "month"), ("Sites", "sites"), ("Author", "author"), ("Issued", "issued")):
        s = sub_one(s, r"<dt>%s</dt><dd>[^<]*</dd>" % label, "<dt>%s</dt><dd>%s</dd>" % (label, esc(str(m[key]))), label)
    logo = ('<div class="clientlogo"><img src="%s" alt="%s"></div>' % (m["logo"], esc(m["client"]))
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
    if "boards" in D:
        note = D["boards"].get("note")
        s = re.sub(r'\n *<p class="h2note lnote">[^<]*</p>',
                   lambda _: '\n    <p class="h2note lnote">%s</p>' % note if note else "", s, count=1)
    for slot, url in D.get("links", {}).items():
        if slot != "ratings":
            sys.exit("fill: unknown link slot %r" % slot)
        s = sub_one(s, r'<a href="[^"]*">See sustainability ratings', '<a href="%s">See sustainability ratings' % href(url),
                    "ratings link")
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

    fd, tmp = tempfile.mkstemp(suffix=".html")
    os.close(fd)
    subprocess.run([sys.executable, os.path.join(HERE, "build_report.py"), "scaffold", "--mode", "portfolio",
                    "--sections", sections, "--out", tmp], check=True, capture_output=True)
    s = open(tmp, encoding="utf-8").read()
    os.unlink(tmp)

    months = D["months"]["quarter"]
    base = os.path.dirname(os.path.abspath(a.data))       # photo paths are relative to the bundle
    render = {"boards": lambda: boards(D["boards"]),
              "eh-table": lambda: heatmap(D["equipment_health"], months),
              "cf-table": lambda: heatmap(D["comfort"], months),
              "companies": lambda: companies(D["companies"]),
              "wins": lambda: wins(D["wins"], base, a.photos_out),
              "ratings": lambda: ratings(D["ratings"]),
              "notes": lambda: notes(D.get("notes", {}))}

    def region(m):
        name = m.group(1)
        if name not in render:
            sys.exit("fill: unknown fill region %r" % name)
        return render[name]()
    s = REGION.sub(region, s)
    if not D.get("notes"):
        s = re.sub(r'\n<section class="notes">.*?</section>\n', "\n", s, flags=re.S)
    s = fill_slots(s, D)

    hits = DASHES.findall(s)
    if hits:
        i = DASHES.search(s).start()
        sys.exit("fill: %d en or em dash(es) in the portfolio output, first at: %r" % (len(hits), s[max(0, i - 60):i + 20]))
    open(a.out, "w", encoding="utf-8").write(s)
    n = s.count("<figure>")
    print("wrote %s" % a.out + (", %d KB with %d photos embedded" % (len(s) // 1024, n) if n else ""))


if __name__ == "__main__":
    main()
