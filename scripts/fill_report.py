#!/usr/bin/env python3
"""Fill a scaffolded client report from a data bundle.

    python3 scripts/fill_report.py data.json --out report.html

Everything mechanical lives here: heatmap rows and their band colours, chart
geometry recomputed from each series' own range, the leaderboard, the wins and
their photos, the run hours chart and the platform links. The narrative
sentences are written by the model and passed in through the bundle; nothing in
this file invents prose.

The bundle's keys, each drawn by the code below that reads it:

    sections        the --sections list the scaffold is built from
    months          {"quarter": [...], "trend": [...]}, the column and axis labels
    replace         [[sample, text], ...]: each sample string in the scaffold, found
                    exactly once, swapped for the report's own: the masthead, the
                    section statements and date lines, the overview figures, notes
    replace_all     the same for wording that recurs across sections
    global_replace  the sample site id and window inside every link
    links           {slot: url or null}, per LINK_SLOTS
    impact          operational impact rows, in report order
    equipment_health, comfort                       the two heatmaps
    trend_eh, trend_checks, trend_comfort, alerts   the charts
    leaderboard     one row per assignee: name, company, resolved, open
    wins            the key wins, with their refs, impact, level and photos
    run_hours       {"chart": the chart.json run_hours.py draw wrote, "note": ...}
"""
import argparse, base64, io, json, os, re, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
def xs(n):
    """Month column centres. Six months are the DESIGN.md positions; a window
    trimmed for a newly onboarded site spreads evenly over the same plot width."""
    if n == 6:
        return [80, 190, 300, 410, 520, 630]
    step = (630 - 80) / (n - 1) if n > 1 else 0
    return [round(80 + step * i) for i in range(n)]
BASELINE, LEFT, RIGHT = 196, 36, 670
# Win impact tags. The key is the PEAK `impacts` value, which is also the class
# the dot colour hangs off; the label is what prints. See references/actions-and-wins/key-wins.md
# for how a win's impact is chosen from its action tickets.
IMPACTS = {"energy": "Energy", "comfort": "Comfort", "reliability": "Reliability",
           "water": "Water", "safety": "Safety", "other": "Other"}
# Win photos embed at this height in pixels, about twice their printed size, so
# they stay sharp on paper without carrying a phone camera's megabytes.
PHOTO_PX = 480
SOFT_PX = 300     # below this a tile has under 1.5x its printed size, and prints visibly soft
MAX_PHOTOS = 4
# Section and chart-source links, keyed by bundle slot and found in the scaffold
# by the link text that follows them. Each one is the platform_link that section's
# own PEAK call returned; see the platform links rules in SKILL.md. Row links ride
# on their rows and ticket links on their wins, so neither is a slot here.
LINK_SLOTS = {"equipment_health": "See live equipment health dashboard",
              "comfort": "See live indoor environment dashboard",
              "alerts": "See live issues being resolved",
              "leaderboard": "See live actions leaderboard",
              "trend_eh": "PEAK equipment health dashboard",
              "trend_comfort": "PEAK indoor environment dashboard"}


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


def note(s, eyebrow, text):
    """Rewrite the chartnote that follows a given section eyebrow."""
    i = s.index(eyebrow)
    k = s.index('<p class="chartnote">', i)
    return s[:k] + '<p class="chartnote">' + text + '</p>' + s[s.index("</p>", k) + 4:]


def href(url):
    """A platform link separates its params with bare &, which an href owes as
    &amp;. Skipping one already written that way keeps this safe to apply twice."""
    return re.sub(r"&(?!amp;)", "&amp;", url.strip())


def set_links(s, links):
    """Point each link row at the URL its own PEAK call returned. A slot set to
    null drops that link rather than leaving the scaffold's sample one standing."""
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
def heatmap(d, months):
    dp, t, counts = d["dp"], d["bands"], d.get("counts", [])
    head = ['        <th class="lv">%s</th>' % d["label"]]
    head += ['        <th class="ct">%s</th>' % c for c in counts]
    head += ['        <th class="mo">%s</th>' % m for m in months]
    head += ['        <th class="cg">Chg</th>']
    body = []
    for r in d["rows"]:
        cells = "".join('<td class="ct">%s</td>' % (f"{v:,}" if isinstance(v, int) else v)
                        for v in r.get("counts", []))
        mo = r["months"]
        cells += "".join(
            '<td class="c none">&mdash;</td>' if v is None else
            '<td class="c %s%s">%.*f</td>' % (band(v, t), " now" if i == len(mo) - 1 else "", dp, v)
            for i, v in enumerate(mo))
        link = ('<a href="%s">%s &rsaquo;</a>' % (href(r["link"]), r["name"])) if r.get("link") else r["name"]
        delta = ('<span class="chg flat">&mdash;</span>' if None in (mo[0], mo[-1])
                 else chg(mo[-1] - mo[0], dp))
        body.append('      <tr><td class="lv">%s</td>%s<td class="cg">%s</td></tr>'
                    % (link, cells, delta))
    sr = d["site"]
    cells = "".join('<td class="ct">%s</td>' % f"{v:,}" for v in sr.get("counts", []))
    mo = sr["months"]
    cells += "".join('<td class="c %s%s">%.*f</td>'
                     % (band(v, t), " now" if i == len(mo) - 1 else "", dp, v)
                     for i, v in enumerate(mo))
    body.append('      <tr class="total"><td class="lv">Site</td>%s<td class="cg">%s</td></tr>'
                % (cells, chg(mo[-1] - mo[0], dp)))
    return ('<table class="hm">\n    <thead>\n      <tr>\n' + "\n".join(head)
            + '\n      </tr>\n    </thead>\n    <tbody>\n' + "\n".join(body)
            + '\n    </tbody>\n  </table>')


# ── charts ──────────────────────────────────────────────────────────────────
def line_chart(d, months):
    """Y range spans the data and whichever thresholds are drawn, plus padding."""
    v, th, dp = d["values"], d["thresholds"], d["dp"]
    lo, hi = min(v + [t[0] for t in th]), max(v + [t[0] for t in th])
    pad = max((hi - lo) * 0.18, 0.15)
    lo, hi = lo - pad, hi + pad
    top, bot = 50.0, 190.0
    y = lambda val: top + (hi - val) * (bot - top) / (hi - lo)
    out = []
    for tv, tlabel in th:
        out.append('        <text class="axis" x="44" y="%.1f">%s threshold</text>' % (y(tv) - 8, tlabel))
        out.append('        <line class="benchline" x1="%d" y1="%.1f" x2="%d" y2="%.1f"/>'
                   '<text class="axis" x="4" y="%.1f">%.1f</text>'
                   % (LEFT, y(tv), RIGHT, y(tv), y(tv) + 3, tv))
    out.append('        <line class="baseline" x1="%d" y1="%d" x2="%d" y2="%d"/>' % (LEFT, BASELINE, RIGHT, BASELINE))
    out.append('        <polyline class="series-line" points="%s"/>'
               % " ".join("%d,%.1f" % (x, y(val)) for x, val in zip(xs(len(v)), v)))
    out += ['        <circle cx="%d" cy="%.1f" r="4.5" class="pt"/>' % (x, y(val)) for x, val in zip(xs(len(v)), v)]
    for x, val in zip(xs(len(v)), v):
        ly = y(val) + 18 if y(val) + 22 < BASELINE else y(val) - 10
        out.append('        <text class="val" x="%d" y="%.1f" text-anchor="middle">%.*f%%</text>' % (x, ly, dp, val))
    out += ['        <text class="axis" x="%d" y="216" text-anchor="middle">%s</text>' % (x, m)
            for x, m in zip(xs(len(months)), months)]
    return ('<svg viewBox="0 0 682 236" role="img" aria-label="%s">\n%s\n      </svg>'
            % (d["alt"], "\n".join(out)))


def grouped_bar(d, months):
    a, b = d["a"], d["b"]
    # Compact labels keep long values from colliding; the bundle may supply its own.
    la = d.get("labels_a") or [d.get("fmt_a", "%s") % v for v in a]
    lb = d.get("labels_b") or [d.get("fmt_b", "%s") % v for v in b]
    amax, bmax = max(a) * 1.06, max(b) * 1.06
    H = 140.0
    out = []
    C = xs(len(months))
    step = (C[1] - C[0]) if len(C) > 1 else 110
    w = min(30, step * 0.27)
    for k in range(len(months)):
        for x0, val, mx, cls in ((C[k] - w - 3, a[k], amax, "bar-primary"),
                                 (C[k] + 3, b[k], bmax, "bar-benchmark")):
            t = BASELINE - (val / mx) * H
            x1 = x0 + w
            out.append('      <path class="%s" d="M%.1f,%d V%.1f Q%.1f,%.1f %.1f,%.1f H%.1f Q%.1f,%.1f %.1f,%.1f V%d Z"/>'
                       % (cls, x0, BASELINE, t, x0, t - 4, x0 + 4, t - 4, x1 - 4, x1, t - 4, x1, t, BASELINE))
    out.append('      <line class="baseline" x1="%d" y1="%d" x2="%d" y2="%d"/>' % (LEFT, BASELINE, RIGHT, BASELINE))
    for k in range(len(months)):
        ta = BASELINE - (a[k] / amax) * H
        tb = BASELINE - (b[k] / bmax) * H
        out.append('      <text class="val" x="%d" y="%.1f" text-anchor="middle">%s</text>'
                   '<text class="val" x="%d" y="%.1f" text-anchor="middle">%s</text>'
                   % (C[k] - w / 2 - 3, ta - 8, la[k], C[k] + w / 2 + 3, tb - 8, lb[k]))
    out += ['      <text class="axis" x="%d" y="216" text-anchor="middle">%s</text>' % (x, m)
            for x, m in zip(xs(len(months)), months)]
    return ('<svg viewBox="0 0 682 236" role="img" aria-label="%s">\n%s\n    </svg>'
            % (d["alt"], "\n".join(out)))


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
    saved there as <name>-<n>.jpg, exactly as embedded, to be looked at."""
    pair = len(photos) == 2
    figs = []
    for n, p in enumerate(photos, 1):
        p = {"src": p} if isinstance(p, str) else p
        src = p["src"] if os.path.isabs(p["src"]) else os.path.join(base, p["src"])
        jpg = photo_jpeg(src, 1.5 if pair else 1.0, p.get("focus"), p.get("zoom", 1))
        if out:
            open(os.path.join(out, "%s-%d.jpg" % (name, n)), "wb").write(jpg)
        figs.append('<figure><img src="data:image/jpeg;base64,%s" alt="Photo from the action ticket"></figure>'
                    % base64.b64encode(jpg).decode())
    return '<div class="photos%s">%s</div>' % (" pair" if pair else "", "".join(figs))


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
    sections = D.get("sections") or "equipment-health,indoor-environment,actions-and-wins,run-hours"

    tmp = tempfile.mktemp(suffix=".html")
    subprocess.run([sys.executable, os.path.join(HERE, "build_report.py"), "scaffold",
                    "--sections", sections, "--out", tmp], check=True, capture_output=True)
    s = open(tmp, encoding="utf-8").read()
    os.unlink(tmp)

    months = D["months"]

    # global swaps first: the sample site id and window live in every link
    for old, new in D.get("global_replace", []):
        s = s.replace(old, new)

    # every occurrence: window wording recurs across the trend sections
    for old, new in D.get("replace_all", []):
        if old not in s:
            sys.exit("fill: replace_all anchor not found: %.70s" % old)
        s = s.replace(old, new)

    # exactly one occurrence: a second match means the anchor is not specific enough
    for old, new in D["replace"]:
        if s.count(old) != 1:
            sys.exit("fill: anchor matched %d times: %.70s" % (s.count(old), old))
        s = s.replace(old, new)

    # platform links, each one straight off the call that answered its section
    if "links" in D:
        s = set_links(s, D["links"])

    # operational impact rows, in the order the skill fixes
    if D.get("impact"):
        rows = []
        for r in D["impact"]:
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
        j = s.rindex("</div>", i, s.index('<div class="seclinks">', i)) + len("</div>")
        s = s[:i] + "\n\n".join(rows) + "\n\n" + s[j:].lstrip("\n")

    # heatmaps
    if "equipment_health" in D:
        s = swap(s, '<th class="ct">Equip</th>', heatmap(D["equipment_health"], months["quarter"]))
        s = note(s, "Equipment health snapshot", D["equipment_health"]["note"])
    if "comfort" in D:
        s = swap(s, '<th class="lv">Level</th>', heatmap(D["comfort"], months["quarter"]))
        s = note(s, "Indoor environment health snapshot", D["comfort"]["note"])

    # charts
    for key, anchor, kind in (("trend_eh", "Site equipment health score", "line"),
                              ("trend_checks", "Automated health checks", "bar"),
                              ("trend_comfort", "Site thermal comfort score", "line"),
                              ("alerts", "Faults triaged and resolved", "bar")):
        if key not in D:
            continue
        c = D[key]
        svg = line_chart(c, months["trend"]) if kind == "line" else grouped_bar(c, months["trend"])
        s = swap_svg(s, anchor, svg)
        s = note(s, c["note_after"], c["note"])

    # leaderboard
    if "leaderboard" in D:
        TR = ('<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
              'stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" role="img" '
              'aria-label="First place"><path d="M6 9H4.5a2.5 2.5 0 0 1 0-5H6"/><path d="M18 9h1.5a2.5 2.5 0 0 0 0-5H18"/>'
              '<path d="M4 22h16"/><path d="M10 14.66V17c0 .55-.47.98-.97 1.21C7.85 18.75 7 20.24 7 22"/>'
              '<path d="M14 14.66V17c0 .55.47.98.97 1.21C16.15 18.75 17 20.24 17 22"/>'
              '<path d="M18 2H6v7a6 6 0 0 0 12 0V2Z"/></svg>')
        rows, tr, to = [], 0, 0
        for k, e in enumerate(D["leaderboard"], 1):
            res, op = e["resolved"], e["open"]
            tr += res; to += op
            pct = res / (res + op) * 100 if res + op else 0
            rows.append('      <tr><td class="rank">%s</td><td class="name">%s</td><td class="co">%s</td>'
                        '<td class="num">%s</td><td><span class="scorecell"><span class="track">'
                        '<span class="fill" style="width:%.1f%%"></span></span><span class="sval">%.1f%%</span>'
                        '</span></td><td class="num %s">%d</td></tr>'
                        % (TR if k == 1 else k, e["name"], e["company"], f"{res:,}", pct, pct,
                           "open-zero" if op == 0 else "open-hot", op))
        tp = tr / (tr + to) * 100 if tr + to else 0
        rows.append('      <tr class="total"><td></td><td>Total</td><td></td><td class="num">%s</td>'
                    '<td><span class="scorecell"><span class="track"><span class="fill" style="width:%.1f%%">'
                    '</span></span><span class="sval">%.1f%%</span></span></td><td class="num">%d</td></tr>'
                    % (f"{tr:,}", tp, tp, to))
        i = s.index("Who closed the work")
        t0 = s.index("<tbody>", i) + len("<tbody>")
        s = s[:t0] + "\n" + "\n".join(rows) + "\n    " + s[s.index("</tbody>", t0):]

    # key wins
    if "wins" in D:
        base = os.path.dirname(os.path.abspath(a.data))   # photo paths are relative to the bundle
        blocks = []
        for wn, w in enumerate(D["wins"], 1):
            photos = w.get("photos") or []
            if len(photos) > MAX_PHOTOS:
                sys.exit("fill: %d photos on %r — %d at most (references/actions-and-wins/key-wins.md)"
                         % (len(photos), w["heading"], MAX_PHOTOS))
            # One photo sits beside the text; two to four run in a row under the heading.
            side = len(photos) == 1
            pad = "      " if side else "    "
            b = ""
            # No impact key means an older bundle: fill it without a tag rather
            # than guessing one the action tickets never carried.
            if w.get("impact"):
                k = w["impact"]
                if k not in IMPACTS:
                    sys.exit("fill: unknown win impact %r — one of %s" % (k, ", ".join(IMPACTS)))
                b += pad + '<p class="impact %s"><i></i>%s</p>\n' % (k, IMPACTS[k])
            b += pad + '<h3>%s</h3>\n' % w["heading"]
            if w.get("level"):
                lv = w["level"] if isinstance(w["level"], list) else [w["level"]]
                b += pad + '<p class="where"><span class="k">%s</span>%s</p>\n' % (
                    "Levels" if len(lv) > 1 else "Level", ", ".join(lv))
            if photos and not side:
                b += pad + photo_row(photos, base, a.photos_out, "win%d" % wn) + "\n"
            b += pad + '<p>%s</p>\n' % w["body"]
            if w.get("snap"):
                b += pad + '<p class="snap">%s</p>\n' % w["snap"]
            b += pad + '<p class="refs">' + " &middot; ".join(
                '<a href="%s">%s</a>' % (href(r["url"]), r["title"]) for r in w["refs"]) + '</p>\n'
            if side:
                b = ('  <div class="win compact">\n    %s\n    <div class="wtext">\n%s    </div>\n  </div>'
                     % (photo_row(photos, base, a.photos_out, "win%d" % wn), b))
            else:
                b = '  <div class="win">\n' + b + '  </div>'
            blocks.append(b)
        m = re.search(r'  <div class="win[ "]', s)
        if not m:
            sys.exit("fill: the bundle carries wins but key-wins is not in its sections")
        i = m.start()
        j = s.rindex("</div>", i, s.index("</section>", i)) + len("</div>")
        s = s[:i] + "\n\n".join(blocks) + s[j:]

    # run hours: the chart and its date line as references/run-hours/scripts/run_hours.py
    # drew them, and the note under the chart
    if "run_hours" in D:
        rh = D["run_hours"]
        path = os.path.join(os.path.dirname(os.path.abspath(a.data)), rh["chart"])
        drawn = json.load(open(path, encoding="utf-8"))
        eyebrow = '<p class="eyebrow">Equipment run hours</p>'
        if eyebrow not in s:
            sys.exit("fill: the bundle carries run_hours but run-hours is not in its sections")
        i = s.index('<div class="rh">')
        j = s.index("<!-- /rh -->", i) + len("<!-- /rh -->")
        s = s[:i] + '<div class="rh">\n' + drawn["html"] + "\n  </div>" + s[j:]
        k = s.index('<p class="h2note">', s.index(eyebrow))
        s = s[:k] + '<p class="h2note">' + drawn["dateline"] + s[s.index("</p>", k):]
        s = note(s, eyebrow, rh["note"])

    open(a.out, "w", encoding="utf-8").write(s)
    n = s.count("<figure>")
    print("wrote %s" % a.out + (", %d KB with %d photos embedded" % (len(s) // 1024, n) if n else ""))


if __name__ == "__main__":
    main()
