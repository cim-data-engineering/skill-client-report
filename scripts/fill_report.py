#!/usr/bin/env python3
"""Fill a scaffolded client report from a data bundle.

    python3 scripts/fill_report.py data.json --out report.html

Everything mechanical lives here: heatmap rows and their band colours, chart
geometry recomputed from each series' own range, the leaderboard, the wins and
their photos, the platform links and every masthead slot. The wins are
written by the model and passed in through the bundle; nothing in this file
invents prose.
"""
import argparse, base64, html, io, json, os, re, subprocess, sys, tempfile
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
REFERENCE = os.path.join(HERE, "..", "assets", "reference-report.html")


def eyebrows():
    """Every section eyebrow the reference report carries, whichever sections a report keeps."""
    with open(REFERENCE, encoding="utf-8") as fh:
        return set(re.findall(r'<p class="eyebrow">([^<]+)</p>', fh.read()))
def xs(n):
    """Month column centres, spread evenly over the plot width; a single month sits in the middle."""
    if n == 1:
        return [355]
    step = (630 - 80) / (n - 1) if n > 1 else 0
    return [round(80 + step * i) for i in range(n)]
BASELINE, LEFT, RIGHT = 196, 36, 670
TODATE_TOP = 30           # the month to date's tinted column runs from here to the baseline
# Win impact tags. The key is the PEAK `impacts` value, which is also the class
# the dot colour hangs off; the label is what prints. See references/single-site/actions-and-wins/key-wins.md
# for how a win's impact is chosen from its action tickets.
IMPACTS = {"energy": "Energy", "comfort": "Comfort", "reliability": "Reliability",
           "water": "Water", "safety": "Safety", "other": "Other"}
# Where a win stands, its label's chip and its words, in page order
WIN_GROUPS = (("fixed", "pos", "Fixed"), ("in_flight", "warn", "In progress"))
# Win photos embed at this height in pixels, about twice their printed size, so
# they stay sharp on paper without carrying a phone camera's megabytes.
PHOTO_PX = 480
SOFT_PX = 300     # below this a tile has under 1.5x its printed size, and prints visibly soft
MAX_PHOTOS = 4
# Section and chart-source links, keyed by bundle slot and found in the scaffold
# by the link text that follows them. Each one is built by its section's script;
# see the Links block in its reference. Row links ride on their rows and ticket links
# on their wins, so neither is a slot here.
# Every external link opens in a new tab on its own, since some viewers drop the page's <base target>.
EXTERNAL = re.compile(r'<a\b(?![^>]*\btarget=)([^>]*\bhref="https?://[^>]*)>')
LINK_SLOTS = {"equipment_health": "See live equipment health dashboard",
              "comfort": "See live indoor environment dashboard",
              "leaderboard": "See live actions leaderboard",
              "trend_eh": "PEAK equipment health dashboard",
              "trend_comfort": "PEAK indoor environment dashboard",
              "ratings": "See sustainability ratings"}


# ── helpers ─────────────────────────────────────────────────────────────────
def band(v, t):
    """t is [excellent, good, average] descending; below average is Poor."""
    return "b4" if v >= t[0] else "b3" if v >= t[1] else "b2" if v >= t[2] else "b1"


def chg(c, dp):
    if abs(c) < 0.5 / 10 ** dp:
        return '<span class="chg flat">%.*f</span>' % (dp, 0)
    glyph, cls = ("&uarr; +", "up") if c > 0 else ("&darr; &minus;", "down")
    return '<span class="chg %s">%s%.*f</span>' % (cls, glyph, dp, abs(c))


def swap(s, anchor, new, end='</table>'):
    """Replace the table that CONTAINS `anchor`: open tag found backwards, close forwards."""
    i = s.index(anchor)
    start = s.rindex("<table", 0, i)
    stop = s.index(end, i) + len(end)
    if s.count("<table", start, i) != 1:
        raise SystemExit("fill: anchor %.30s is not inside its own table" % anchor)
    return s[:start] + new + s[stop:]


def initials(name):
    """'Kestrel Air Services (KAS)' -> 'KA', 'Linwood' -> 'L', 'CIM' -> 'CIM': a missing logo's stand-in."""
    words = [w for w in re.findall(r"[A-Za-z0-9]+", re.sub(r"\(.*?\)", "", name))
             if w.lower() not in ("and", "of", "the", "pty", "ltd", "limited", "inc", "co")]
    if len(words) == 1 and words[0].isupper() and len(words[0]) <= 3:
        return words[0]
    return "".join(w[0] for w in words[:2]).upper()


def note(s, anchor, text):
    """Rewrite the chartnote that follows `anchor`, a chart's title."""
    i = s.index(anchor)
    k = s.index('<p class="chartnote">', i)
    return s[:k] + '<p class="chartnote">' + text + '</p>' + s[s.index("</p>", k) + 4:]


def href(url):
    """A platform link separates its params with bare &, which an href owes as
    &amp;. Skipping one already written that way keeps this safe to apply twice."""
    return re.sub(r"&(?!amp;)", "&amp;", url.strip())


def set_links(s, links):
    """Point each link row at its URL. A slot set to null drops that link rather
    than leaving the scaffold's sample one standing."""
    for slot, url in links.items():
        if slot not in LINK_SLOTS:
            raise SystemExit("fill: unknown link slot %r — one of %s" % (slot, ", ".join(LINK_SLOTS)))
        text = re.escape(LINK_SLOTS[slot])
        if not re.search(r'<a href="[^"]*">%s' % text, s):
            raise SystemExit("fill: no link row for %r — is its section in the report?" % slot)
        if url:
            s = re.sub(r'<a href="[^"]*">(%s)' % text,
                       lambda m: '<a href="%s">%s' % (href(url), m.group(1)), s)
        else:
            s = re.sub(r'\s*<p class="chartsource">[^<]*<a href="[^"]*">%s</a>[^<]*</p>' % text, "", s)
            s = re.sub(r'<a href="[^"]*">%s[^<]*</a>' % text, "", s)
            s = re.sub(r'\n *<div class="seclinks">\s*</div>', "", s)
    return s


# ── heatmaps ────────────────────────────────────────────────────────────────
def heatmap(d):
    """A month to date closes the columns: its header says so, and its cells band like the
    rest, since a score is a rate over whatever days exist. With one month there is no change
    to show, so the Chg column goes. A month with no score is a dash, the site row's too."""
    months, to_date = d["months"], d["to_date"]
    dp, t, counts = d["dp"], d["bands"], d.get("counts", [])
    moves = len(months) > 1
    head = ['        <th class="lv">%s</th>' % d["label"]]
    head += ['        <th class="ct">%s</th>' % c for c in counts]
    head += ['        <th class="mo">%s%s</th>' % (m, "<em>to date</em>" if to_date and i == len(months) - 1 else "")
             for i, m in enumerate(months)]
    head += ['        <th class="cg">Chg</th>'] if moves else []
    cell = lambda v, now: ('<td class="c none">&mdash;</td>' if v is None else
                           '<td class="c %s%s">%.*f</td>' % (band(v, t), " now" if now else "", dp, v))
    delta = lambda mo: ('<td class="cg">%s</td>' % ('<span class="chg flat">&mdash;</span>' if None in (mo[0], mo[-1])
                                                     else chg(mo[-1] - mo[0], dp))) if moves else ""
    body = []
    for r in d["rows"]:
        cells = "".join('<td class="ct">%s</td>' % (f"{v:,}" if isinstance(v, int) else v)
                        for v in r.get("counts", []))
        mo = r["months"]
        cells += "".join(cell(v, i == len(mo) - 1) for i, v in enumerate(mo))
        name = html.escape(r["name"], quote=False)
        link = ('<a href="%s">%s &rsaquo;</a>' % (href(r["link"]), name)) if r.get("link") else name
        body.append('      <tr><td class="lv">%s</td>%s%s</tr>' % (link, cells, delta(mo)))
    sr = d["site"]
    cells = "".join('<td class="ct">%s</td>' % (f"{v:,}" if isinstance(v, int) else v) for v in sr.get("counts", []))
    mo = sr["months"]
    cells += "".join(cell(v, i == len(mo) - 1) for i, v in enumerate(mo))
    body.append('      <tr class="total"><td class="lv">Site</td>%s%s</tr>' % (cells, delta(mo)))
    return ('<table class="hm">\n    <thead>\n      <tr>\n' + "\n".join(head)
            + '\n      </tr>\n    </thead>\n    <tbody>\n' + "\n".join(body)
            + '\n    </tbody>\n  </table>')


# ── charts ──────────────────────────────────────────────────────────────────
def to_date_marks(months, to_date):
    """The month to date's marks, shared by every monthly chart: a tinted column behind
    it and 'to date' under its axis label."""
    if not to_date:
        return [], []
    C = xs(len(months))
    step = (C[-1] - C[-2]) if len(C) > 1 else 110
    band = ['        <rect class="todate" x="%.1f" y="%d" width="%.1f" height="%d" rx="3"/>'
            % (C[-1] - step / 2, TODATE_TOP, step, BASELINE - TODATE_TOP)]
    sub = ['        <text class="axis-sub" x="%d" y="228" text-anchor="middle">to date</text>' % C[-1]]
    return band, sub


def text_w(t):
    """About how wide a value label prints, in px: the face is sans at 11px, semibold."""
    return sum(3.2 if ch in ".,:" else 9.6 if ch in "MW" else 6.6 for ch in t)


def line_chart(d):
    """Y range spans the data and whichever thresholds are drawn, plus padding. Each point sits
    over its own month, and a month with no score leaves a gap in the line. A month to date
    closes the line dashed, on an open point: its score can still move."""
    months, to_date, v = d["months"], d["to_date"], list(d["values"])
    th, dp = d["thresholds"], d["dp"]
    C = xs(len(months))
    vals = [val for val in v if val is not None]
    lo, hi = min(vals + [t[0] for t in th]), max(vals + [t[0] for t in th])
    pad = max((hi - lo) * 0.18, 0.15)
    lo, hi = lo - pad, hi + pad
    top, bot = 50.0, 190.0
    y = lambda val: top + (hi - val) * (bot - top) / (hi - lo)
    pts = [(C[i], val, i) for i, val in enumerate(v) if val is not None]
    # runs of consecutive months holding a score: the line joins each run's points
    runs, run = [], []
    for x, val, i in pts:
        if run and run[-1][2] != i - 1:
            runs.append(run)
            run = []
        run.append((x, val, i))
    runs.append(run)
    out = []
    # Value labels sit above or below each point; a threshold label takes the first of
    # four places (left or right end, above or below its line) that no value label, point
    # or stretch of the line covers, else the first such place further along its line.
    label_y = lambda val: y(val) + 18 if y(val) + 22 < BASELINE else y(val) - 10   # under the point, or over it near the baseline
    boxes = []
    for x, val, _ in pts:
        ly = label_y(val)
        w = 6.2 * len("%.*f%%" % (dp, val))
        boxes.append((x - w / 2 - 3, ly - 10, x + w / 2 + 3, ly + 3))
        boxes.append((x - 6, y(val) - 6, x + 6, y(val) + 6))
    segs = [(p[0], y(p[1]), q[0], y(q[1])) for r in runs for p, q in zip(r, r[1:])]
    def crosses(x0, y0, x1, y1):
        for ax, ay, bx, by in segs:
            n = max(int(abs(bx - ax) / 2), 1)
            if any(x0 - 6 <= ax + (bx - ax) * k / n <= x1 + 6 and y0 - 3 <= ay + (by - ay) * k / n <= y1 + 3
                   for k in range(n + 1)):
                return True
        return False
    def clear(x0, y0, x1, y1):
        return all(x1 < a or x0 > c or y1 < b or y0 > e for a, b, c, e in boxes) and not crosses(x0, y0, x1, y1)
    for tv, tlabel in th:
        text, ty = "%s threshold" % tlabel, y(tv)
        w = 6.0 * len(text)          # the axis face is mono at 10px: 6px a character
        slide = [(x, yy, "start") for x in range(66, int(RIGHT - 4 - w), 22) for yy in (ty - 8, ty + 14)]
        for x, yy, anchor in [(44, ty - 8, "start"), (44, ty + 14, "start"),
                              (RIGHT - 4, ty - 8, "end"), (RIGHT - 4, ty + 14, "end")] + slide:
            x0 = x if anchor == "start" else x - w
            if clear(x0, yy - 9, x0 + w, yy + 2):
                break
        else:
            x, yy, anchor = 44, ty - 8, "start"
        out.append('        <text class="axis" x="%d" y="%.1f"%s>%s</text>'
                   % (x, yy, ' text-anchor="end"' if anchor == "end" else "", text))
        out.append('        <line class="benchline" x1="%d" y1="%.1f" x2="%d" y2="%.1f"/>'
                   '<text class="axis" x="4" y="%.1f">%.1f</text>'
                   % (LEFT, y(tv), RIGHT, y(tv), y(tv) + 3, tv))
    out.append('        <line class="baseline" x1="%d" y1="%d" x2="%d" y2="%d"/>' % (LEFT, BASELINE, RIGHT, BASELINE))
    last = len(v) - 1
    part = to_date and v[last] is not None and len(pts) > 1
    for r in runs:
        xy = ["%d,%.1f" % (x, y(val)) for x, val, _ in r]
        dash = part and r[-1][2] == last and len(r) > 1
        if len(xy) - dash > 1:
            out.append('        <polyline class="series-line" points="%s"/>' % " ".join(xy[:-1] if dash else xy))
        if dash:
            out.append('        <polyline class="series-line todate-line" points="%s"/>' % " ".join(xy[-2:]))
    out += ['        <circle cx="%d" cy="%.1f" r="4.5" class="%s"/>'
            % (x, y(val), "pt todate-pt" if part and i == last else "pt") for x, val, i in pts]
    for x, val, _ in pts:
        out.append('        <text class="val" x="%d" y="%.1f" text-anchor="middle">%.*f%%</text>' % (x, label_y(val), dp, val))
    out += ['        <text class="axis" x="%d" y="216" text-anchor="middle">%s</text>' % (x, m)
            for x, m in zip(C, months)]
    band, sub = to_date_marks(months, to_date)
    return ('<svg viewBox="0 0 682 236" role="img" aria-label="%s">\n%s\n      </svg>'
            % (html.escape(d["alt"]), "\n".join(band + out + sub)))


def grouped_bar(d):
    """A month to date sits in a tinted column: its bars count only the days so far."""
    months, to_date = d["months"], d["to_date"]
    a, b = d["a"], d["b"]
    # Compact labels keep long values from colliding; the bundle may supply its own.
    la = d.get("labels_a") or ["%s" % v for v in a]
    lb = d.get("labels_b") or ["%s" % v for v in b]
    # Two units (checks against dollars) take a scale each; one unit (actions raised
    # against resolved) shares one, or a 17 draws as tall as a 69.
    top = lambda vs: max([v or 0 for v in vs] + [1])     # a month with no data (None) draws no bar
    if d.get("scale") == "shared":
        amax = bmax = max(top(a), top(b)) * 1.06
    else:
        amax, bmax = top(a) * 1.06, top(b) * 1.06
    H = 140.0
    out = []
    C = xs(len(months))
    step = (C[1] - C[0]) if len(C) > 1 else 110
    w = min(30, step * 0.27)
    for k in range(len(months)):
        for x0, val, mx, cls in ((C[k] - w - 3, a[k], amax, "bar-primary"),
                                 (C[k] + 3, b[k], bmax, "bar-benchmark")):
            if val is None:
                continue
            t = BASELINE - (val / mx) * H
            x1 = x0 + w
            out.append('      <path class="%s" d="M%.1f,%d V%.1f Q%.1f,%.1f %.1f,%.1f H%.1f Q%.1f,%.1f %.1f,%.1f V%d Z"/>'
                       % (cls, x0, BASELINE, t, x0, t - 4, x0 + 4, t - 4, x1 - 4, x1, t - 4, x1, t, BASELINE))
    out.append('      <line class="baseline" x1="%d" y1="%d" x2="%d" y2="%d"/>' % (LEFT, BASELINE, RIGHT, BASELINE))
    for k in range(len(months)):
        if a[k] is None or b[k] is None:
            continue
        ta = BASELINE - (a[k] / amax) * H
        tb = BASELINE - (b[k] / bmax) * H
        xa, xb = C[k] - w / 2 - 3, C[k] + w / 2 + 3
        # two labels side by side at one height read as one figure, so a close pair moves apart
        gap = (xb - xa) - (text_w(la[k]) + text_w(lb[k])) / 2
        if gap < 6 and abs(ta - tb) < 12:
            xa, xb = xa - (6 - gap) / 2, xb + (6 - gap) / 2
        out.append('      <text class="val" x="%d" y="%.1f" text-anchor="middle">%s</text>'
                   '<text class="val" x="%d" y="%.1f" text-anchor="middle">%s</text>'
                   % (xa, ta - 8, la[k], xb, tb - 8, lb[k]))
    out += ['      <text class="axis" x="%d" y="216" text-anchor="middle">%s</text>' % (x, m)
            for x, m in zip(xs(len(months)), months)]
    band, sub = to_date_marks(months, to_date)
    return ('<svg viewBox="0 0 682 236" role="img" aria-label="%s">\n%s\n    </svg>'
            % (html.escape(d["alt"]), "\n".join(band + out + sub)))


def drop_chart(s, title):
    """Delete the chart block a title heads, for a trend too short to draw, and its section
    with it once no chart is left there."""
    i = s.index('<h3 class="charttitle">%s' % title)
    start = s.rindex("\n", 0, s.rindex('<div class="chartblock">', 0, i)) + 1
    sec0 = s.rindex("<section", 0, start)
    sec1 = s.index("</section>", i)
    nxt = s.find('<div class="chartblock">', i, sec1)
    stop = s.rindex("\n", 0, nxt) + 1 if nxt != -1 else s.rindex("\n", 0, sec1) + 1
    s = s[:start] + s[stop:]
    s = re.sub(r"\n[ \t]*\n(?:[ \t]*\n)+", "\n\n", s)
    sec1 = s.index("</section>", sec0) + len("</section>")
    if '<div class="chartblock">' not in s[sec0:sec1]:
        s = s[:s.rindex("\n", 0, sec0) + 1] + s[sec1:].lstrip("\n")
    return s


# ── sustainability ratings ──────────────────────────────────────────────────
def rating_cards(cards):
    """A card per measure: the score out of its maximum on a 0 to max score bar, the change
    from the previous rating, then the month the rating expires, or an Expired chip."""
    out = []
    for c in cards:
        d, chips = c.get("delta"), []
        if d and d["dir"] == "flat":
            chips.append('<span class="delta neu">No change from %s</span>' % d["from"])
        elif d:
            chips.append('<span class="delta %s">%s %s from %s</span>' % (
                "pos" if d["dir"] == "up" else "neu", "&uarr; Up" if d["dir"] == "up" else "&darr; Down",
                d["amount"], d["from"]))
        if c.get("expired"):
            chips.append('<span class="chip neu">Expired</span>')
        out.append('    <div class="stat"><p class="k">%s</p><p class="n">%.1f <span>/ %g stars</span></p>'
                   '<span class="track"><span class="fill" style="width:%.1f%%"></span></span>%s%s</div>'
                   % (c["name"], c["score"], c["max"], c["score"] / c["max"] * 100,
                      '<div class="nbsub">%s</div>' % "".join(chips) if chips else "",
                      "" if c.get("expired") else '<p class="nbexp">Expires %s</p>' % c["expires"]))
    return '  <div class="nbgrid">\n' + "\n".join(out) + "\n  </div>"


def rating_chart(c):
    """A rating history on its own time axis and y range, lo to hi: the top a dashed line,
    the bottom the baseline, both labelled. Values sit under their points, or above where
    the baseline is too close. The axis is labelled every January and July, or every
    January alone once it spans more than four years."""
    t0, t1 = (date.fromisoformat(a) for a in c["axis"])
    x = lambda t: 60 + (t - t0).days / (t1 - t0).days * 590
    top, base, h = 26, 118, 140
    y = lambda v: base - (v - c["lo"]) / (c["hi"] - c["lo"]) * (base - top)
    out = ['        <line class="benchline" x1="%d" y1="%d" x2="%d" y2="%d"/><text class="axis" x="4" y="%d">%.1f</text>'
           % (LEFT, top, RIGHT, top, top + 3, c["hi"]),
           '        <line class="baseline" x1="%d" y1="%d" x2="%d" y2="%d"/><text class="axis" x="4" y="%d">%.1f</text>'
           % (LEFT, base, RIGHT, base, base + 3, c["lo"])]
    pts = [(x(date.fromisoformat(t)), y(v), v) for t, v in c["points"]]
    if len(pts) > 1:
        out.append('        <polyline class="series-line" points="%s"/>' % " ".join("%.1f,%.1f" % p[:2] for p in pts))
    out += ['        <circle cx="%.1f" cy="%.1f" r="4.5" class="pt"/>' % p[:2] for p in pts]
    out += ['        <text class="val" x="%.1f" y="%.1f" text-anchor="middle">%.1f</text>'
            % (px, py + 18 if py + 18 <= base - 6 else py - 10, v) for px, py, v in pts]
    yearly = (t1 - t0).days > 4 * 366
    m = t0
    while m <= t1:
        if not (yearly and m.month == 7):
            out.append('        <text class="axis" x="%.1f" y="%d" text-anchor="middle">%s %02d</text>'
                       % (x(m), h - 4, m.strftime("%b"), m.year % 100))
        m = date(m.year + 1, 1, 1) if m.month == 7 else date(m.year, 7, 1)
    return ('  <div class="chartblock">\n    <h3 class="charttitle">%s</h3>\n    <div class="chart">\n'
            '      <svg viewBox="0 0 682 %d" role="img" aria-label="%s">\n%s\n      </svg>\n    </div>\n  </div>'
            % (c["name"], h, html.escape(c["alt"]), "\n".join(out)))


def swap_svg(s, after, svg):
    i = s.index('<svg viewBox="0 0 682 236"', s.index(after))
    return s[:i] + svg + s[s.index("</svg>", i) + 6:]


# ── win photos ──────────────────────────────────────────────────────────────
def photo_jpeg(path, aspect, focus=None, zoom=1):
    """A ticket photo as JPEG bytes: turned upright, cropped to its tile around
    `focus` (x, y as fractions of the frame, centre by default) and `zoom` times
    tighter than the largest crop that fits, shrunk and re-encoded. Re-encoding
    also drops the camera's EXIF block, GPS position included, which the
    original upload carries and a client report must not."""
    try:
        from PIL import Image, ImageOps
    except ImportError:
        sys.exit("fill: win photos need Pillow — pip install pillow")
    if not os.path.isfile(path):
        sys.exit("fill: photo not found: %s" % path)
    try:
        im = Image.open(path)
        icc = im.info.get("icc_profile")
        im = ImageOps.exif_transpose(im)
    except Exception as e:
        sys.exit("fill: cannot read photo %s (%s) — pass a JPEG or PNG" % (path, e))
    if "A" in im.getbands():
        im = Image.alpha_composite(Image.new("RGBA", im.size, "white"), im.convert("RGBA"))
    im = im.convert("RGB")
    w, h = im.size
    fx, fy = focus or (0.5, 0.5)
    if not (0 <= fx <= 1 and 0 <= fy <= 1):
        sys.exit("fill: focus %r on %s — [x, y] as fractions of the frame, 0 to 1" % (focus, path))
    if zoom < 1:
        sys.exit("fill: zoom %r on %s — 1 or more, where 2 keeps half the width" % (zoom, path))
    cw, ch = (h * aspect, h) if w / h > aspect else (w, w / aspect)
    cw, ch = round(cw / zoom), round(ch / zoom)
    x = min(max(round(fx * w - cw / 2), 0), w - cw)
    y = min(max(round(fy * h - ch / 2), 0), h - ch)
    im = im.crop((x, y, x + cw, y + ch))
    if ch > PHOTO_PX:
        im = im.resize((round(PHOTO_PX * aspect), PHOTO_PX), Image.LANCZOS)
    elif ch < SOFT_PX:
        print("fill: warning: %s is only %d px tall once cropped, so it prints soft; "
              "pass the original rather than the preview, or zoom less" % (path, ch), file=sys.stderr)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=80, optimize=True, progressive=True, icc_profile=icc)
    return buf.getvalue()


def photo_row(photos, base, out=None, name="win"):
    """Figures in the order given, each a path or {src, focus, zoom}. A pair
    crops to 3:2 so its row keeps the height of three squares; one, three or
    four crop square. No caption: the win's text explains its photos, and a
    caption would be one more claim to get wrong. With `out`, each tile is also
    saved there exactly as embedded, to be looked at: as <name>-<n>.jpg, or with
    no name under its own photo's name, so a tile keeps its pick's number (w2-1.jpg)."""
    pair = len(photos) == 2
    figs = []
    for n, p in enumerate(photos, 1):
        p = {"src": p} if isinstance(p, str) else p
        src = p["src"] if os.path.isabs(p["src"]) else os.path.join(base, p["src"])
        jpg = photo_jpeg(src, 1.5 if pair else 1.0, p.get("focus"), p.get("zoom", 1))
        if out:
            tile = "%s-%d" % (name, n) if name else os.path.splitext(os.path.basename(p["src"]))[0]
            open(os.path.join(out, tile + ".jpg"), "wb").write(jpg)
        figs.append('<figure><img src="data:image/jpeg;base64,%s" alt="Photo from the action ticket"></figure>'
                    % base64.b64encode(jpg).decode())
    return '<div class="photos%s">%s</div>' % (" pair" if pair else "", "".join(figs))


# ── named slots ─────────────────────────────────────────────────────────────
# The section scripts hand over every mechanical string by name, so nothing has to
# find the scaffold's sample text first. Each slot is located by the markup around it.
def sub_one(s, pattern, repl, what):
    s2, n = re.subn(pattern, repl, s, count=1, flags=re.S)
    if not n:
        sys.exit("fill: no %s in the scaffold" % what)
    return s2


def stat_cards(s, stats):
    """Fill the overview's stat cards from {label: figure}, and leave out each card the bundle does not
    name: a figure with nothing scored behind it has no card."""
    m = re.search(r'<div class="statgrid">.*?\n\s*</div>\n', s, re.S)
    if not m:
        sys.exit("fill: no stat cards in the scaffold")
    found = set()

    def card(c):
        indent, label = c.groups()
        found.add(label)
        if label not in stats:
            return ""
        return '%s<div class="stat"><p class="k">%s</p><p class="n">%s</p></div>\n' % (indent, label, stats[label])
    grid = re.sub(r'([ \t]*)<div class="stat"><p class="k">([^<]+)</p><p class="n">.*?</p></div>\n', card, m.group(0))
    for label in set(stats) - found:
        sys.exit("fill: no %s stat in the scaffold" % label)
    return s[:m.start()] + grid + s[m.end():]


def after_eyebrow(s, eyebrow, tag_open, tag_close, text):
    """Rewrite the first `tag_open...tag_close` in the section an eyebrow heads. A section out of this
    report is passed over; an eyebrow the reference report does not carry names no slot, and stops."""
    i = s.find('<p class="eyebrow">%s</p>' % eyebrow)
    if i == -1:
        if eyebrow not in eyebrows():
            sys.exit("fill: no section headed %r in the reference report: a section script names a slot that "
                     "does not exist" % eyebrow)
        return s                          # the section is out of this report
    k = s.find(tag_open, i, s.index("</section>", i))
    if k == -1:
        sys.exit("fill: the section headed %r has no %s to fill" % (eyebrow, tag_open))
    j = s.index(tag_close, k)
    return s[:k] + tag_open + text + s[j:]


def fill_slots(s, D):
    m = D.get("masthead")
    if m:
        site = html.escape(m["site_name"], quote=False)
        s = sub_one(s, r"<title>[^<]*</title>", lambda _: "<title>%s Quarterly Building Performance Review</title>" % site, "title")
        s = sub_one(s, r"<h1>[^<]*</h1>", lambda _: "<h1>%s</h1>" % site, "h1")
        if m.get("photo_url"):
            s = sub_one(s, r'\s*<!-- Site photo slot:.*?-->\s*<div class="sitephoto"[^>]*>.*?</div>',
                        lambda _: '\n    <div class="sitephoto"><img src="%s" alt="%s"></div>'
                        % (html.escape(m["photo_url"]), html.escape(m["site_name"])), "site photo slot")
        if m.get("prepared"):
            s = sub_one(s, r'<p class="prepared">.*?</p>', lambda _: '<p class="prepared">%s</p>' % m["prepared"], "prepared by")
        for label, key in (("Reporting period", "period"), ("Author", "author"), ("Issued", "issued")):
            s = sub_one(s, r"<dt>%s</dt><dd>[^<]*</dd>" % label,
                        lambda _, label=label, key=key: "<dt>%s</dt><dd>%s</dd>" % (label, m[key]), label)
        s = after_eyebrow(s, "Analytics overview", "<h2>", "</h2>", "What we monitor at %s" % site)
    o = D.get("overview")
    if o:
        s = after_eyebrow(s, "Analytics overview", '<p class="h2note">', "</p>", o["as_at"])
        s = stat_cards(s, o["stats"])
    for eyebrow, text in D.get("statements", {}).items():
        s = after_eyebrow(s, eyebrow, "<h2>", "</h2>", text)
    for eyebrow, text in D.get("datelines", {}).items():
        s = after_eyebrow(s, eyebrow, '<p class="h2note">', "</p>", text)
    for key, inner in D.get("notes", {}).items():
        i = s.find("<li><strong>%s" % key)
        if i != -1:
            j = s.index("</li>", i)
            s = s[:i] + "<li>" + inner + s[j:]
        elif key == "The reporting window" and '<section class="notes">' in s:
            # the reporting window has no slot: it shows only with a month to date, last in the band
            k = s.index("</ol>", s.index('<section class="notes">'))
            s = s[:k] + "  <li>" + inner + "</li>\n  " + s[k:]
        else:
            sys.exit("fill: no notes item %r in the scaffold for a section in the report" % key)
    rh = D.get("run_hours")
    if rh:
        i = s.index('<div class="rh">')
        j = s.index("<!-- /rh -->", i)
        s = s[:i] + '<div class="rh">\n' + rh["html"] + "\n  </div>" + s[j + len("<!-- /rh -->"):]
    return s


# ── the parts the sections fill ─────────────────────────────────────────────
TROPHY = ('<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
          'stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" role="img" '
          'aria-label="First place"><path d="M6 9H4.5a2.5 2.5 0 0 1 0-5H6"/><path d="M18 9h1.5a2.5 2.5 0 0 0 0-5H18"/>'
          '<path d="M4 22h16"/><path d="M10 14.66V17c0 .55-.47.98-.97 1.21C7.85 18.75 7 20.24 7 22"/>'
          '<path d="M14 14.66V17c0 .55.47.98.97 1.21C16.15 18.75 17 20.24 17 22"/>'
          '<path d="M18 2H6v7a6 6 0 0 0 12 0V2Z"/></svg>')
CHARTS = (("trend_eh", "Site equipment health score", "line"),
          ("trend_checks", "Automated health checks", "bar"),
          ("trend_comfort", "Site thermal comfort score", "line"),
          ("alerts", "Faults triaged and resolved", "bar"))


def scaffold(sections, mode="single-site"):
    """The scaffold for these sections, from build_report; its own message where it stops."""
    fd, tmp = tempfile.mkstemp(suffix=".html")
    os.close(fd)
    try:
        r = subprocess.run([sys.executable, os.path.join(HERE, "build_report.py"), "scaffold", "--mode", mode,
                            "--sections", sections, "--out", tmp], capture_output=True, text=True)
        if r.returncode:
            sys.exit("fill: the scaffold stopped: %s" % (r.stderr or r.stdout).strip())
        return open(tmp, encoding="utf-8").read()
    finally:
        os.unlink(tmp)


def drop_section(s, anchor):
    """Delete the section that holds `anchor`, and the blank line it leaves."""
    i = s.index(anchor)
    start = s.rindex("\n", 0, s.rindex("<section", 0, i)) + 1
    stop = s.index("</section>", i) + len("</section>")
    return s[:start] + s[stop:].lstrip("\n")


def fill_impact(s, impact):
    """The operational impact rows, in the order the skill fixes."""
    rows = []
    for r in impact:
        sub = r["sub"]
        if r.get("delta"):
            d = r["delta"]
            glyph = "&uarr; Up" if d["dir"] == "up" else "&darr; Down"
            cls = "pos" if d["dir"] == "up" else "neu"
            sub = '<span class="delta %s">%s %s</span> %s' % (cls, glyph, d["amount"], sub)
        rows.append('  <div class="irow">\n    <span class="chip %s">%s</span>\n    <div>\n'
                    '      <span class="fig">%s</span> <span class="figcap">%s</span>\n'
                    '      <div class="isub">%s</div>\n    </div>\n  </div>'
                    % (r.get("chip_class", "neu"), r["chip"], r["fig"], r["cap"], sub))
    i = s.index('  <div class="irow">')
    end = s.index("</section>", i)                 # the rows end before the section's link row, or the section
    links = s.find('<div class="seclinks">', i, end)
    j = s.rindex("</div>", i, links if links != -1 else end) + len("</div>")
    return s[:i] + "\n\n".join(rows) + "\n\n" + s[j:].lstrip("\n")


def fill_charts(s, D):
    for key, anchor, kind in CHARTS:
        if key not in D:
            continue
        c = D[key]
        if c is None:                     # a trend too short to draw: the section left it out
            s = drop_chart(s, anchor)
            continue
        s = swap_svg(s, anchor, line_chart(c) if kind == "line" else grouped_bar(c))
        if c.get("note"):
            s = note(s, c["note_after"], c["note"])
    return s


def fill_ratings(s, ratings):
    """The scaffold's sample cards and charts swapped for the site's own."""
    i = s.index('<div class="ratings"')
    j = s.index("<!-- /ratings -->", i) + len("<!-- /ratings -->")
    body = [rating_cards(ratings["cards"])] + [rating_chart(c) for c in ratings["charts"]]
    return s[:i] + '<div class="ratings">\n' + "\n".join(body) + "\n  </div>" + s[j:]


def fill_leaderboard(s, entries):
    rows, tr, to = [], 0, 0
    for k, e in enumerate(entries, 1):
        res, op = e["resolved"], e["open"]
        tr += res; to += op
        pct = res / (res + op) * 100 if res + op else 0
        # the company logo in a square tile beside the name, as PEAK shows it; its initials without one
        co = html.escape(e["company"])
        tile = ('<span class="logo"><img src="%s" alt="%s" title="%s"></span>' % (e["logo"], co, co) if e.get("logo")
                else '<span class="logo none" title="%s">%s</span>' % (co, initials(e["company"])))
        rows.append('      <tr><td class="rank">%s</td><td class="assignee"><span class="who">%s<span class="nm">%s</span>'
                    '</span></td><td class="co">%s</td>'
                    '<td class="num">%s</td><td><span class="scorecell"><span class="track">'
                    '<span class="fill" style="width:%.1f%%"></span></span><span class="sval">%.0f%%</span>'
                    '</span></td><td class="num %s">%d</td></tr>'
                    % (TROPHY if k == 1 else k, tile, html.escape(e["name"], quote=False), co, f"{res:,}", pct, pct,
                       "open-zero" if op == 0 else "open-hot", op))
    tp = tr / (tr + to) * 100 if tr + to else 0
    rows.append('      <tr class="total"><td></td><td>Total</td><td></td><td class="num">%s</td>'
                '<td><span class="scorecell"><span class="track"><span class="fill" style="width:%.1f%%">'
                '</span></span><span class="sval">%.0f%%</span></span></td><td class="num">%d</td></tr>'
                % (f"{tr:,}", tp, tp, to))
    i = s.index("Who closed the work")
    t0 = s.index("<tbody>", i) + len("<tbody>")
    return s[:t0] + "\n" + "\n".join(rows) + "\n    " + s[s.index("</tbody>", t0):]


def win_block(w, base, photos_out):
    """One win card. One photo sits beside the text; two to four run in a row under the heading."""
    photos = w.get("photos") or []
    if len(photos) > MAX_PHOTOS:
        sys.exit("fill: %d photos on %r — %d at most (references/single-site/actions-and-wins/key-wins.md)"
                 % (len(photos), w["heading"], MAX_PHOTOS))
    side = len(photos) == 1
    pad = "      " if side else "    "
    b = ""
    # A win without an impact prints no tag, never one its action tickets did not carry.
    if w.get("impact"):
        k = w["impact"]
        if k not in IMPACTS:
            sys.exit("fill: unknown win impact %r — one of %s" % (k, ", ".join(IMPACTS)))
        b += pad + '<p class="impact %s"><i></i>%s</p>\n' % (k, IMPACTS[k])
    b += pad + '<h3>%s</h3>\n' % w["heading"]
    if w.get("level"):
        lv = w["level"] if isinstance(w["level"], list) else [w["level"]]
        b += pad + '<p class="where"><span class="k">%s</span>%s</p>\n' % (
            "Levels" if len(lv) > 1 else "Level", html.escape(", ".join(lv), quote=False))
    if photos and not side:
        b += pad + photo_row(photos, base, photos_out, name=None) + "\n"
    b += pad + '<p>%s</p>\n' % w["body"]
    b += pad + '<p class="refs">' + " &middot; ".join(
        '<a href="%s">%s</a>' % (href(r["url"]), r["title"]) for r in w["refs"]) + '</p>\n'
    if side:
        return ('  <div class="win compact">\n    %s\n    <div class="wtext">\n%s    </div>\n  </div>'
                % (photo_row(photos, base, photos_out, name=None), b))
    return '  <div class="win">\n' + b + '  </div>'


def win_groups(wins, blocks):
    """The win cards under their labels, Fixed then In progress, each label ahead of the first card
    at that status, and shown even where every win is one kind. blocks are the cards, in the wins' order."""
    out = []
    for state, chip, label in WIN_GROUPS:
        group = [b for w, b in zip(wins, blocks) if w.get("state", "fixed") == state]
        if group:
            out += ['  <h3 class="wgroup"><span class="chip %s">%s</span></h3>' % (chip, label)] + group
    return "\n\n".join(out)


def fill_wins(s, wins, base, photos_out):
    m = re.search(r'  <(?:h3 class="wgroup"|div class="win[ "])', s)
    if not m:
        sys.exit("fill: the bundle carries wins but key-wins is not in its sections")
    i = m.start()
    j = s.rindex("</div>", i, s.index("</section>", i)) + len("</div>")
    return s[:i] + win_groups(wins, [win_block(w, base, photos_out) for w in wins]) + s[j:]


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
    # empty when every section dropped itself: the frame alone
    s = scaffold(D.get("sections", "all"))
    s = fill_slots(s, D)                  # masthead, overview, statements, date lines, notes, run hours
    if "links" in D:
        s = set_links(s, D["links"])
    if D.get("impact"):
        s = fill_impact(s, D["impact"])
    if "equipment_health" in D:
        s = swap(s, '<th class="ct">Equip</th>', heatmap(D["equipment_health"]))
    if "comfort" in D:
        s = swap(s, '<th class="lv">Level</th>', heatmap(D["comfort"]))
    s = fill_charts(s, D)
    if "ratings" in D:
        s = fill_ratings(s, D["ratings"])
    if D.get("leaderboard"):
        s = fill_leaderboard(s, D["leaderboard"])
    elif "leaderboard" in D:              # nobody to rank: the board goes, the chart above it stays
        s = drop_section(s, "Who closed the work")
    if "wins" in D:
        # photo paths are relative to the bundle
        s = fill_wins(s, D["wins"], os.path.dirname(os.path.abspath(a.data)), a.photos_out)
    s = EXTERNAL.sub(r'<a\1 target="_blank" rel="noopener">', s)
    open(a.out, "w", encoding="utf-8").write(s)
    n = s.count("<figure>")
    print("wrote %s" % a.out + (", %d KB with %d photos embedded" % (len(s) // 1024, n) if n else ""))


if __name__ == "__main__":
    main()
