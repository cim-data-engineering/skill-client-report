#!/usr/bin/env python3
"""Equipment run hours as a report section: when each unit ran across the last
full week of the quarter, against the site's working hours.

The pipeline is skill-health-check's, copied unchanged beside this file:
runhours_plan.py fixes the week and picks every unit's points, runhours_build.py
turns the history into the aggregate. This module drives them through the
report's hooks and draws the aggregate as static SVG in the report's design, since
the report carries no script. See references/run-hours/run-hours.md.
"""
import json
import os
import re
import subprocess
import sys
from datetime import timedelta
from html import escape

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "scripts"))
import peak_io as io  # noqa: E402

NAME = "run-hours"
DIR = "runhours"                     # under peak/, where the health-check scripts keep their files

# Layout, in the report's chart units (the sheet draws every chart 682 wide).
W, LABEL, RIGHT_PAD = 682, 168, 4
HEAD, GROUP_H, ROW_H, BAR_H, LEVEL_GAP, BOTTOM = 34, 20, 15, 8, 4, 6
FS_NAME, FS_SMALL = 10, 8.5
CHAR = 0.56                          # average glyph width as a share of the font size, for cutting labels


def week_of(ctx):
    """Monday of the last full Monday-to-Sunday week inside the quarter."""
    last = io.last_day(ctx["quarter"][1])
    sunday = last - timedelta(days=(last.weekday() + 1) % 7)
    return (sunday - timedelta(days=6)).isoformat()


def script(name, *args):
    p = subprocess.run([sys.executable, os.path.join(HERE, name)] + list(args), capture_output=True, text=True)
    if p.returncode:
        raise SystemExit("run hours: %s stopped: %s" % (name, (p.stderr or p.stdout).strip()))
    return p.stdout


def printed_calls(text):
    """The calls the health-check scripts print: a label line naming the file, then the call as JSON."""
    out, name = [], None
    for line in text.splitlines():
        m = re.search(r"->\s*(\S+?\.json)", line)
        if m:
            name = m.group(1)
        elif line.startswith("{") and name:
            out.append(dict(json.loads(line), file=name))
            name = None
    return out


def as_call(c):
    return {"file": "%s/%s" % (DIR, c["file"]), "tool": "execute_graphql_query",
            "args": {k: c[k] for k in ("query_name", "args", "fields")}}


def calls(ctx):
    rh = os.path.join(ctx["dir"], "peak", DIR)
    os.makedirs(rh, exist_ok=True)
    args = ["window", ctx["site_file"], rh, "--week-of", week_of(ctx), "--today", ctx["today"]]
    if ctx.get("hours"):
        args += ["--hours", ctx["hours"]]
    return [as_call(c) for c in printed_calls(script("runhours_plan.py", *args))]


def more(ctx, work):
    rh = work.path(DIR)
    disc = work.get("%s/discovery-0.json" % DIR)
    if disc.total and disc.total > 1000:
        base = next(c for c in calls(ctx) if c["file"].endswith("discovery-0.json"))
        pages = [dict(base, file="%s/discovery-%d.json" % (DIR, s),
                      args=dict(base["args"], args=dict(base["args"]["args"], start_index=s)))
                 for s in range(1000, disc.total, 1000)]
        missing = [p for p in pages if not work.has(p["file"])]
        if missing:
            return missing
    plan_path = os.path.join(rh, "plan.json")
    if not os.path.isfile(plan_path):
        discs = sorted(os.path.join(rh, f) for f in os.listdir(rh) if re.match(r"discovery-\d+\.json$", f))
        out = script("runhours_plan.py", "plan", rh, *discs, "--census",
                     os.path.join(rh, "census-all.json"), os.path.join(rh, "census-known.json"))
        with open(os.path.join(rh, "plan.out"), "w") as fh:
            fh.write(out)
    with open(plan_path) as fh:
        plan = json.load(fh)
    with open(os.path.join(rh, "window.json")) as fh:
        window = json.load(fh)
    chunks = [c for c in plan["chunks"] if c["pass"] == 1]
    return [{"file": "%s/history-1-%d.json" % (DIR, i), "tool": "execute_graphql_query",
             "args": {"query_name": "platform.history",
                      "args": {"fav_ids": c["fav_ids"], "start": window["start"], "end": window["end"],
                               "end_exclusive": True},
                      "fields": ["fav_id", "ts", "data"]}}
            for i, c in enumerate(chunks, 1) if not work.has("%s/history-1-%d.json" % (DIR, i))]


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


def out_of_hours(agg):
    """Hours each drawn unit ran outside working hours, most first."""
    hours = []
    for page in agg["pages"]:
        for g in page["groups"]:
            for r in g["rows"]:
                n = 0
                for a, b in r.get("runs") or []:
                    for s in range(a, b):
                        wh = agg["days"][s // 96]["wh"]
                        if not wh or not (wh[0] <= s % 96 < wh[1]):
                            n += 1
                if n:
                    hours.append((n / 4, r["name"], g["name"]))
    return sorted(hours, reverse=True)


def build(ctx, work, shared):
    rh = work.path(DIR)
    with open(os.path.join(rh, "plan.json")) as fh:
        plan = json.load(fh)
    with open(os.path.join(rh, "window.json")) as fh:
        window = json.load(fh)
    if not any(c["pass"] == 1 for c in plan["chunks"]):
        with open(os.path.join(rh, "plan.out")) as fh:
            why = fh.read().strip()
        return {"drop": ["run-hours"], "facts": ["Run hours: nothing to draw, so the section is left out. Say why "
                                                 "in chat: " + " ".join(why.split())]}
    hist = sorted(os.path.join(rh, f) for f in os.listdir(rh) if re.match(r"history-1-\d+[ab]?\.json$", f))
    notes = script("runhours_build.py", rh, *hist)
    with open(os.path.join(rh, "agg.json")) as fh:
        agg = json.load(fh)
    rows = sum(len(g["rows"]) for p in agg["pages"] for g in p["groups"])
    ooh = out_of_hours(agg)
    later = [u for u in plan["units"] if u.get("pass") == 2 and u.get("pull")]
    facts = ["Run hours: %s, %d units drawn, working hours from the %s."
             % (window["label"], rows, "user" if window.get("hours_source") == "user" else "site's settings in PEAK"),
             "Most running outside working hours: " + ("; ".join("%s (%s) %.1f h" % (n, g, h) for h, n, g in ooh[:6]) or "none"),
             "Build notes, for chat and the chart note: " + " ".join(
                 l[2:] for l in notes.splitlines() if l.startswith("- "))]
    if later:
        facts.append("Not drawn, beyond the first pass of 100 units: %d units. Name them in chat." % len(later))
    return {
        "run_hours": {"html": render(agg)},
        "datelines": {"Equipment run hours":
                      "%s, the last full week of the quarter, against the site's working hours. Bars are "
                      "exact to 15 minutes." % window["label"]},
        "notes": {"Run hours":
                  "<strong>Run hours.</strong> Each row is one unit, drawn from a sensor that reports it running: "
                  "a run status, or a speed, current or power reading. An enable or schedule says what the unit "
                  "was told to do, not that it ran, so it never draws a row. Where status and speed disagree, the "
                  "one showing less running is kept, since the usual faults all add hours. Grey columns are the "
                  "site's working hours in PEAK; hatching marks no reliable data."},
        "prose": {"run_hours": "The note under the run hours chart: which plant ran outside working hours, and "
                               "anything on all week or not at all, from the facts below."},
        "facts": facts,
    }
