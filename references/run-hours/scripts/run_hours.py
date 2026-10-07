#!/usr/bin/env python3
"""Equipment run hours for the client report: the report's week, and its chart.

    python3 references/run-hours/scripts/run_hours.py window <site.json> <workdir> --site-id N --quarter-end YYYY-MM-DD [--hours "..."]
    python3 references/run-hours/scripts/run_hours.py draw <workdir>

window  Takes the report's site out of the saved search_sites response, fixes
        the week the section shows, the last full Monday-to-Sunday week inside the
        quarter, and hands both to runhours_plan.py window, which writes
        <workdir>/window.json and prints the discovery and census calls to make.
draw    Runs runhours_build.py over the saved first-pass history responses and
        draws the aggregate as static SVG in the report's design, since the report
        carries no script. Writes <workdir>/chart.json for fill_report.py: the
        chart, its date line, and a note under it only where field units were
        left out to keep the chart to its first pass. Prints what to say in chat.

The pull and the classification are skill-health-check's: runhours_plan.py,
runhours_build.py and runhours_history.py beside this file, copied unchanged.
See references/run-hours/run-hours.md.
"""
import argparse
import json
import re
import subprocess
import sys
from collections import Counter
from datetime import date, timedelta
from html import escape
from pathlib import Path

sys.dont_write_bytecode = True             # leave no __pycache__ beside the skill
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from runhours_history import read_results  # noqa: E402
from runhours_plan import CAP_UNITS  # noqa: E402

# Layout, in the report's chart units (the sheet draws every chart 682 wide).
W, LABEL, RIGHT_PAD = 682, 168, 4
HEAD, GROUP_H, ROW_H, BAR_H, LEVEL_GAP, BOTTOM = 34, 20, 15, 8, 4, 6
FS_NAME, FS_SMALL = 10, 8.5
CHAR = 0.56                                # average glyph width as a share of the font size, for cutting labels


def script(name, *args):
    p = subprocess.run([sys.executable, str(HERE / name)] + [str(a) for a in args], capture_output=True, text=True)
    if p.returncode:
        sys.exit("%s stopped: %s" % (name, (p.stderr or p.stdout).strip()))
    return p.stdout


# ── window ──────────────────────────────────────────────────────────────────
def cmd_window(a):
    # a keyword search can return several sites; the plan reads one
    site = [r for r in read_results(a.site) if r.get("site_id") == a.site_id]
    if not site:
        sys.exit("site %d is not in %s" % (a.site_id, a.site))
    work = Path(a.workdir)
    work.mkdir(parents=True, exist_ok=True)
    (work / "site.json").write_text(json.dumps({"results": site[:1]}))
    last = date.fromisoformat(a.quarter_end)
    sunday = last - timedelta(days=(last.weekday() + 1) % 7)
    args = ["window", work / "site.json", work, "--week-of", (sunday - timedelta(days=6)).isoformat()]
    if a.hours:
        args += ["--hours", a.hours]
    sys.stdout.write(script("runhours_plan.py", *args))


# ── drawing ─────────────────────────────────────────────────────────────────
def fit(text, width, size):
    """Cut a label to its width with an ellipsis; SVG text has no overflow rule of its own."""
    room = int(width / (size * CHAR))
    return text if len(text) <= room else text[:max(room - 1, 1)].rstrip(" ·-,") + "…"


def ampm(slot):
    h, m = divmod(slot * 15, 60)
    h %= 24
    return "%d%s%s" % (h % 12 or 12, (":%02d" % m) if m else "", "am" if h < 12 else "pm")


def page_svg(page, days, n):
    x0, x1 = LABEL, W - RIGHT_PAD
    dw = (x1 - x0) / 7
    sw = dw / 96
    px = lambda s: x0 + s * sw
    fg, y = [], HEAD
    for i, d in enumerate(days):
        cx = x0 + i * dw + dw / 2
        fg.append('<text class="rh-day" x="%.1f" y="12" text-anchor="middle">%s</text>' % (cx, escape(d["label"])))
        fg.append('<text class="rh-hours" x="%.1f" y="24" text-anchor="middle">%s</text>'
                  % (cx, "closed" if not d["wh"] else "%s-%s" % (ampm(d["wh"][0]), ampm(d["wh"][1]))))
    for g in page["groups"]:
        fg.append('<text class="rh-group" x="0" y="%.1f">%s</text>' % (y + 14, escape(g["name"])))
        y += GROUP_H
        for r in g["rows"]:
            if r.get("level_break"):
                y += LEVEL_GAP
            ty, by = y + ROW_H / 2 + 3.5, y + (ROW_H - BAR_H) / 2
            where = " · ".join(x for x in (r.get("where") or []) if x)
            name_w = LABEL - 14 - (min(len(where), 14) * FS_SMALL * CHAR + 8 if where else 0)
            tip = escape("%s%s%s" % (r["name"], " (%s)" % r["point"] if r.get("point") else "",
                                     "\n" + r["where_full"] if r.get("where_full") else ""))
            fg.append('<a href="%s"><text class="rh-name" x="8" y="%.1f"><title>%s</title>%s</text></a>'
                      % (escape(r["href"]), ty, tip, escape(fit(r["name"], name_w, FS_NAME))))
            if where:
                fg.append('<text class="rh-where" x="%d" y="%.1f" text-anchor="end">%s</text>'
                          % (LABEL - 6, ty, escape(fit(where, 14 * FS_SMALL * CHAR, FS_SMALL))))
            if r.get("nodata"):
                fg.append('<rect x="%d" y="%.1f" width="%.1f" height="%d" fill="url(#rh-hatch-%d)"><title>%s</title></rect>'
                          % (x0, by, x1 - x0, BAR_H, n, escape(r["nodata"])))
            else:
                for a, b in r.get("gaps") or []:
                    fg.append('<rect x="%.2f" y="%.1f" width="%.2f" height="%d" fill="url(#rh-hatch-%d)"/>'
                              % (px(a), by, (b - a) * sw, BAR_H, n))
                for a, b in r.get("runs") or []:
                    for i in range(a // 96, (b - 1) // 96 + 1):
                        o = i * 96
                        s, f = max(a, o) - o, min(b, o + 96) - o
                        w0, w1 = (days[i]["wh"] or [0, 0])
                        for lo, hi, cls in ((s, min(f, w0), "rh-out"), (max(s, w0), min(f, w1), "rh-in"),
                                            (max(s, w1), f, "rh-out")):
                            if hi > lo:
                                fg.append('<rect class="%s" x="%.2f" y="%.1f" width="%.2f" height="%d"/>'
                                          % (cls, px(o + lo), by, (hi - lo) * sw + 0.3, BAR_H))
            y += ROW_H
    bottom = y + BOTTOM
    bg = ['<rect class="rh-wh" x="%.2f" y="%d" width="%.2f" height="%.1f" rx="3"/>'
          % (x0 + i * dw + d["wh"][0] * sw, HEAD - 4, (d["wh"][1] - d["wh"][0]) * sw, bottom - HEAD + 4)
          for i, d in enumerate(days) if d["wh"]]
    bg += ['<line class="rh-mid" x1="%.2f" y1="%d" x2="%.2f" y2="%.1f"/>' % (x0 + i * dw, 2, x0 + i * dw, bottom)
           for i in range(8)]
    defs = ('<defs><pattern id="rh-hatch-%d" width="4" height="4" patternUnits="userSpaceOnUse" '
            'patternTransform="rotate(45)"><rect class="rh-hatch-bg" width="4" height="4"/>'
            '<line class="rh-hatch" x1="0" y1="0" x2="0" y2="4"/></pattern></defs>' % n)
    return ('<svg viewBox="0 0 %d %.0f" role="img" aria-label="%s run times against working hours">%s%s%s</svg>'
            % (W, bottom, escape(page["title"]), defs, "".join(bg), "".join(fg)))


def render(agg):
    out = []
    for n, page in enumerate(agg["pages"]):
        if not any(g["rows"] for g in page["groups"]):
            continue
        out.append('<div class="rhpage"><h3 class="charttitle">%s</h3>\n%s\n</div>'
                   % (escape(page["title"]), page_svg(page, agg["days"], n)))
    return "\n".join(out)


def cmd_draw(a):
    work = Path(a.workdir)
    if not (work / "plan.json").is_file():
        sys.exit("No plan in %s: run runhours_plan.py plan over the saved discovery pages first." % work)
    plan = json.loads((work / "plan.json").read_text())
    window = json.loads((work / "window.json").read_text())
    if not any(c["pass"] == 1 for c in plan["chunks"]):
        sys.exit("Nothing to draw: leave the section out, and say why in chat from the plan step's summary.")
    hist = sorted(p for p in work.iterdir() if re.match(r"history-1-\d+[ab]?\.json$", p.name))
    if not hist:
        sys.exit("No first-pass history in %s: save each history response as the plan step named it." % work)
    notes = script("runhours_build.py", work, *hist)
    agg = json.loads((work / "agg.json").read_text())
    dateline = ("%s, the last full week of the quarter, against the site's working hours. Bars are exact to "
                "15 minutes." % window["label"])
    # field units past the first pass are the one omission the page states
    later = [u for u in plan["units"] if u.get("pass") == 2 and u.get("pull")]
    chart = {"html": render(agg), "dateline": dateline}
    if later:
        types = ["%s (%d)" % (t, n) for t, n in Counter(u["type_name"] for u in later).most_common()]
        types = ", ".join(types[:-1]) + " and " + types[-1] if len(types) > 1 else types[0]
        field = sum(1 for u in plan["units"] if u.get("pass") == 1 and u.get("pull") and u.get("page") != "Central plant")
        chart["note"] = (("Central plant is drawn in full and field units fill the chart up to %d units, so %d more "
                          "field units are left out: %s." % (CAP_UNITS, len(later), types)) if field else
                         ("Central plant fills the chart, so %d field units are left out: %s." % (len(later), types)))
    (work / "chart.json").write_text(json.dumps(chart))

    rows = sum(len(g["rows"]) for p in agg["pages"] for g in p["groups"])
    print("Wrote %s: %d units drawn, %s, working hours from the %s." % (
        work / "chart.json", rows, window["label"],
        "user" if window.get("hours_source") == "user" else "site's settings in PEAK"))
    if later:
        print("\nNote under the chart: " + chart["note"])
    print("\nBuild notes, for chat:\n" + notes.strip())
    left = {}
    for u in json.loads((work / "plan.json").read_text())["units"]:     # as the build left it
        if u.get("why"):
            left.setdefault(u["why"], []).append(u["name"])
    if left:
        print("\nLeft off the chart, every unit by reason, for chat:")
        for why, names in sorted(left.items(), key=lambda kv: -len(kv[1])):
            print("- %s (%d): %s" % (why, len(names), ", ".join(names)))
    if later:
        print("\nNot shown, beyond the first pass: " + ", ".join(u["name"] for u in later))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    w = sub.add_parser("window", help="fix the report's week and print the discovery and census calls")
    w.add_argument("site", help="the saved search_sites response, with working hours")
    w.add_argument("workdir")
    w.add_argument("--site-id", type=int, required=True, help="the PEAK site id the report is for")
    w.add_argument("--quarter-end", required=True, help="the quarter's last day, YYYY-MM-DD")
    w.add_argument("--hours", help='working hours to assess against when the site has none, '
                                   'e.g. "Mon-Fri 08:00-18:00, Sat 09:00-13:00"')
    w.set_defaults(func=cmd_window)
    d = sub.add_parser("draw", help="build the aggregate and draw the chart")
    d.add_argument("workdir")
    d.set_defaults(func=cmd_draw)
    a = ap.parse_args()
    a.func(a)


if __name__ == "__main__":
    main()
