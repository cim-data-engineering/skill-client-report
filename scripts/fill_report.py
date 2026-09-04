#!/usr/bin/env python3
"""Fill a scaffolded client report from a data bundle.

    python3 scripts/fill_report.py data.json --out report.html

Everything mechanical lives here: heatmap rows and their band colours, chart
geometry recomputed from each series' own range, the leaderboard, the wins and
every masthead slot. The narrative sentences are written by the model and
passed in through the bundle; nothing in this file invents prose.
"""
import argparse, json, os, re, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
X = [80, 190, 300, 410, 520, 630]          # month column centres, per DESIGN.md
BASELINE, LEFT, RIGHT = 196, 36, 670


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
        cells += "".join('<td class="c %s%s">%.*f</td>'
                         % (band(v, t), " now" if i == len(mo) - 1 else "", dp, v)
                         for i, v in enumerate(mo))
        link = ('<a href="%s">%s &rsaquo;</a>' % (r["link"], r["name"])) if r.get("link") else r["name"]
        body.append('      <tr><td class="lv">%s</td>%s<td class="cg">%s</td></tr>'
                    % (link, cells, chg(mo[-1] - mo[0], dp)))
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
               % " ".join("%d,%.1f" % (x, y(val)) for x, val in zip(X, v)))
    out += ['        <circle cx="%d" cy="%.1f" r="4.5" class="pt"/>' % (x, y(val)) for x, val in zip(X, v)]
    for x, val in zip(X, v):
        ly = y(val) + 18 if y(val) + 22 < BASELINE else y(val) - 10
        out.append('        <text class="val" x="%d" y="%.1f" text-anchor="middle">%.*f%%</text>' % (x, ly, dp, val))
    out += ['        <text class="axis" x="%d" y="216" text-anchor="middle">%s</text>' % (x, m)
            for x, m in zip(X, months)]
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
    for k in range(len(months)):
        for x0, val, mx, cls in ((47 + 110 * k, a[k], amax, "bar-primary"),
                                 (83 + 110 * k, b[k], bmax, "bar-benchmark")):
            t = BASELINE - (val / mx) * H
            x1 = x0 + 30
            out.append('      <path class="%s" d="M%d,%d V%.1f Q%d,%.1f %d,%.1f H%d Q%d,%.1f %d,%.1f V%d Z"/>'
                       % (cls, x0, BASELINE, t, x0, t - 4, x0 + 4, t - 4, x1 - 4, x1, t - 4, x1, t, BASELINE))
    out.append('      <line class="baseline" x1="%d" y1="%d" x2="%d" y2="%d"/>' % (LEFT, BASELINE, RIGHT, BASELINE))
    for k in range(len(months)):
        ta = BASELINE - (a[k] / amax) * H
        tb = BASELINE - (b[k] / bmax) * H
        out.append('      <text class="val" x="%d" y="%.1f" text-anchor="middle">%s</text>'
                   '<text class="val" x="%d" y="%.1f" text-anchor="middle">%s</text>'
                   % (47 + 110 * k + 15, ta - 8, la[k], 83 + 110 * k + 15, tb - 8, lb[k]))
    out += ['      <text class="axis" x="%d" y="216" text-anchor="middle">%s</text>' % (x, m)
            for x, m in zip(X, months)]
    return ('<svg viewBox="0 0 682 236" role="img" aria-label="%s">\n%s\n    </svg>'
            % (d["alt"], "\n".join(out)))


def swap_svg(s, after, svg):
    i = s.index('<svg viewBox="0 0 682 236"', s.index(after))
    return s[:i] + svg + s[s.index("</svg>", i) + 6:]


# ── main ────────────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("data")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    D = json.load(open(a.data, encoding="utf-8"))
    sections = D.get("sections") or "equipment-health,indoor-environment,alerts-resolved,key-wins"

    tmp = tempfile.mktemp(suffix=".html")
    subprocess.run([sys.executable, os.path.join(HERE, "build_report.py"), "scaffold",
                    "--sections", sections, "--out", tmp], check=True, capture_output=True)
    s = open(tmp, encoding="utf-8").read()
    os.unlink(tmp)

    site, meta, months = D["site"], D["meta"], D["months"]

    # global swaps first: the sample site id and window live in every link
    for old, new in D.get("global_replace", []):
        s = s.replace(old, new)

    # shell + masthead
    for old, new in D["replace"]:
        if s.count(old) != 1:
            sys.exit("fill: anchor matched %d times: %.70s" % (s.count(old), old))
        s = s.replace(old, new)

    # operational impact rows, in the order the skill fixes
    if "impact" in D:
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
        blocks = []
        for w in D["wins"]:
            b = '  <div class="win">\n    <h3>%s</h3>\n    <p>%s</p>\n' % (w["heading"], w["body"])
            if w.get("snap"):
                b += '    <p class="snap">%s</p>\n' % w["snap"]
            b += ('    <p class="refs">' + " &middot; ".join(
                '<a href="%s">%s</a>' % (r["url"], r["title"]) for r in w["refs"]) + '</p>\n  </div>')
            blocks.append(b)
        i = s.index('  <div class="win">')
        j = s.rindex("</div>", i, s.index("</section>", i)) + len("</div>")
        s = s[:i] + "\n\n".join(blocks) + s[j:]

    open(a.out, "w", encoding="utf-8").write(s)
    print("wrote %s" % a.out)


if __name__ == "__main__":
    main()
