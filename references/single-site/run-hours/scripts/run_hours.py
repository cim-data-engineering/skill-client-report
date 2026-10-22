#!/usr/bin/env python3
"""Equipment run hours as a report section: when each unit ran across the latest
full Monday-to-Sunday week, against the site's working hours.

runhours_plan.py fixes the week and picks every unit's points, and
runhours_build.py turns the history into the aggregate. This module drives them through the
report's hooks and draws the aggregate as static SVG in the report's design, since
the report carries no script. Where the site's data is missing from that week, it
moves to the latest full week before the data stopped. See references/single-site/run-hours/run-hours.md.
"""
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta
from html import escape

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "..", "scripts"))
import peak_io as io  # noqa: E402

DIR = "runhours"                     # under peak/, where the runhours_*.py scripts keep their files
EARLIER = DIR + "/earlier"           # the latest full week with data, when the latest week lacks it

# Layout, in the report's chart units (the sheet draws every chart 682 wide).
W, LABEL, RIGHT_PAD = 682, 168, 4
HEAD, GROUP_H, ROW_H, BAR_H, LEVEL_GAP, BOTTOM = 34, 20, 15, 8, 4, 6
FS_NAME, FS_SMALL = 10, 8.5
CHAR = 0.56                          # average glyph width as a share of the font size, for cutting labels


def script(name, *args):
    p = subprocess.run([sys.executable, os.path.join(HERE, name)] + list(args), capture_output=True, text=True)
    if p.returncode:
        raise SystemExit("run hours: %s stopped: %s" % (name, (p.stderr or p.stdout).strip()))
    return p.stdout


def printed_calls(text):
    """The calls runhours_plan.py prints: a label line naming the file, then the call as JSON."""
    out, name = [], None
    for line in text.splitlines():
        m = re.search(r"->\s*(\S+?\.json)", line)
        if m:
            name = m.group(1)
        elif line.startswith("{") and name:
            out.append(dict(json.loads(line), file=name))
            name = None
    return out


def as_call(rel, c):
    return {"file": "%s/%s" % (rel, c["file"]), "tool": "execute_graphql_query",
            "args": {k: c[k] for k in ("query_name", "args", "fields")}}


def load(work, rel, name):
    path = os.path.join(work.path(rel), name)
    if not os.path.isfile(path):
        return None
    with open(path) as fh:
        return json.load(fh)


def window(ctx, peak, rel, monday=None):
    """Fix one week in <peak>/<rel>/ and return its discovery and census calls, kept beside it
    for paging. The latest full week unless `monday` names an earlier one."""
    rh = os.path.join(peak, rel)
    os.makedirs(rh, exist_ok=True)
    args = ["window", ctx["site_file"], rh, "--site-id", str(ctx["site"]["site_id"]), "--today", ctx["today"]]
    if monday:
        args += ["--week-of", monday]
    if ctx.get("hours"):
        args += ["--hours", ctx["hours"]]
    out = [as_call(rel, c) for c in printed_calls(script("runhours_plan.py", *args))]
    with open(os.path.join(rh, "calls.json"), "w") as fh:
        json.dump(out, fh, indent=1)
    return out


def calls(ctx):
    return window(ctx, os.path.join(ctx["dir"], "peak"), DIR)


def week_calls(ctx, work, rel):
    """What one week's pull still needs: discovery pages, then its plan and history."""
    rh = work.path(rel)
    disc = work.get("%s/discovery-0.json" % rel)
    if disc.total and disc.total > 1000:
        base = next(c for c in load(work, rel, "calls.json") if c["file"].endswith("discovery-0.json"))
        pages = [dict(base, file="%s/discovery-%d.json" % (rel, s),
                      args=dict(base["args"], args=dict(base["args"]["args"], start_index=s)))
                 for s in range(1000, disc.total, 1000)]
        missing = [p for p in pages if not work.has(p["file"])]
        if missing:
            return missing
    if not os.path.isfile(os.path.join(rh, "plan.json")):
        discs = sorted(os.path.join(rh, f) for f in os.listdir(rh) if re.match(r"discovery-\d+\.json$", f))
        census = work.path(DIR)
        out = script("runhours_plan.py", "plan", rh, *discs, "--census",
                     os.path.join(census, "census-all.json"), os.path.join(census, "census-known.json"))
        with open(os.path.join(rh, "plan.out"), "w") as fh:
            fh.write(out)
    plan, win = load(work, rel, "plan.json"), load(work, rel, "window.json")
    chunks = [c for c in plan["chunks"] if c["pass"] == 1]
    return [{"file": "%s/history-1-%d.json" % (rel, i), "tool": "execute_graphql_query",
             "args": {"query_name": "platform.history",
                      "args": {"fav_ids": c["fav_ids"], "start": win["start"], "end": win["end"],
                               "end_exclusive": True},
                      "fields": ["fav_id", "ts", "data"]}}
            for i, c in enumerate(chunks, 1) if not work.has("%s/history-1-%d.json" % (rel, i))]


def history(work, rel):
    rh = work.path(rel)
    return sorted(os.path.join(rh, f) for f in os.listdir(rh) if re.match(r"history-1-\d+[ab]?\.json$", f))


def aggregate(work, rel):
    """Build the week's aggregate; returns the build's notes."""
    return script("runhours_build.py", work.path(rel), *history(work, rel))


def stopped(ctx, work, rel):
    """When the site's data stopped short of a whole week: None when the week is whole or
    nothing in it could ever draw, the call that finds the time when only the reading before
    the week can say, else the local time, or "never" when no point has reported at all."""
    plan, win = load(work, rel, "plan.json"), load(work, rel, "window.json")
    if any(c["pass"] == 1 for c in plan["chunks"]):
        aggregate(work, rel)
        gap = load(work, rel, "agg.json").get("feed_gap")
        if not gap:
            return None
        if gap[0] > 0:                 # quiet from inside the week: the week before that point is whole
            return datetime.fromisoformat(win["days"][0]["date"]) + timedelta(minutes=15 * gap[0])
    elif not plan.get("outage"):
        return None
    probe = "%s/last-reading.json" % rel
    if not work.has(probe):
        return {"file": probe, "tool": "execute_graphql_query",
                "args": {"query_name": "platform.history",
                         "args": {"fav_ids": [p["fav_id"] for p in plan["probe"]], "latest": True,
                                  "end": win["start"], "end_exclusive": True},
                         "fields": ["fav_id", "ts", "data"]}}
    script("runhours_plan.py", "last", work.path(rel), work.path(probe))
    last = load(work, rel, "last.json")["local"]
    return datetime.fromisoformat(last).replace(tzinfo=None) if last else "never"


def more(ctx, work):
    out = week_calls(ctx, work, DIR)
    if out:
        return out
    if load(work, EARLIER, "window.json"):
        return week_calls(ctx, work, EARLIER)
    if load(work, DIR, "earlier.json"):
        return []
    when = stopped(ctx, work, DIR)
    if isinstance(when, dict):
        return [when]
    # The latest full week before the data stopped is the one before the week it stopped in,
    # and it is shown only where it falls inside the reporting period.
    monday = when.date() - timedelta(days=when.weekday() + 7) if isinstance(when, datetime) else None
    outside = when is not None and (monday is None or monday < io.d(ctx["quarter"][0]))
    with open(os.path.join(work.path(DIR), "earlier.json"), "w") as fh:
        json.dump({"stopped": when.isoformat() if isinstance(when, datetime) else when,
                   "monday": monday.isoformat() if monday else None, "outside": outside}, fh)
    if when is None or outside:
        return []
    return [c for c in window(ctx, work.peak, EARLIER, monday.isoformat()) if "census" not in c["file"]]


# ── drawing ─────────────────────────────────────────────────────────────────
def fit(text, width, size):
    """Cut a label to its width with an ellipsis; SVG text has no overflow rule of its own."""
    room = int(width / (size * CHAR))
    return text if len(text) <= room else text[:max(room - 1, 1)].rstrip(" ·-,") + "…"


def ampm(slot):
    h, m = divmod(slot * 15, 60)
    h %= 24
    return "%d%s%s" % (h % 12 or 12, (":%02d" % m) if m else "", "am" if h < 12 else "pm")


def page_table(page, days, n):
    """One page of plant as a table of SVG strips. The day header is the thead, so
    a printed page repeats it, and every unit is a row of its own, so a page break
    falls between units and never through one. Each strip draws its share of the
    working-hours columns and day rules, overlapping its neighbours by half a unit
    so the columns print without a seam; the header rounds their tops and a closing
    strip their bottoms."""
    x0, x1 = LABEL, W - RIGHT_PAD
    dw = (x1 - x0) / 7
    sw = dw / 96
    px = lambda s: x0 + s * sw
    cols = [(x0 + i * dw + d["wh"][0] * sw, (d["wh"][1] - d["wh"][0]) * sw) for i, d in enumerate(days) if d["wh"]]
    mids = [x0 + i * dw for i in range(8)]

    def strip(h, body, cls=None):
        return ('<tr%s><td><svg viewBox="0 0 %d %g">%s</svg></td></tr>'
                % (' class="%s"' % cls if cls else "", W, h, body))

    def ground(h):
        """The working-hours columns and day rules behind a strip h tall."""
        return "".join(['<rect class="rh-wh" x="%.2f" y="-0.5" width="%.2f" height="%g"/>' % (x, w, h + 1)
                        for x, w in cols]
                       + ['<line class="rh-mid" x1="%.2f" y1="-0.5" x2="%.2f" y2="%g"/>' % (x, x, h + 0.5)
                          for x in mids])

    head = ['<defs><pattern id="rh-hatch-%d" width="4" height="4" patternUnits="userSpaceOnUse" '
            'patternTransform="rotate(45)"><rect class="rh-hatch-bg" width="4" height="4"/>'
            '<line class="rh-hatch" x1="0" y1="0" x2="0" y2="4"/></pattern></defs>' % n]
    top = HEAD - 4
    head += ['<path class="rh-wh" d="M%.2f,%g V%g Q%.2f,%g %.2f,%g H%.2f Q%.2f,%g %.2f,%g V%g Z"/>'
             % (x, HEAD + 0.5, top + 3, x, top, x + 3, top, x + w - 3, x + w, top, x + w, top + 3, HEAD + 0.5)
             for x, w in cols]
    head += ['<line class="rh-mid" x1="%.2f" y1="2" x2="%.2f" y2="%g"/>' % (x, x, HEAD + 0.5) for x in mids]
    for i, d in enumerate(days):
        cx = x0 + i * dw + dw / 2
        head.append('<text class="rh-day" x="%.1f" y="12" text-anchor="middle">%s</text>' % (cx, escape(d["label"])))
        head.append('<text class="rh-hours" x="%.1f" y="24" text-anchor="middle">%s</text>'
                    % (cx, "closed" if not d["wh"] else "%s-%s" % (ampm(d["wh"][0]), ampm(d["wh"][1]))))
    rows = []
    for g in page["groups"]:
        rows.append(strip(GROUP_H, ground(GROUP_H) + '<text class="rh-group" x="0" y="14">%s</text>'
                          % escape(g["name"]), "rh-g"))
        for r in g["rows"]:
            gap = LEVEL_GAP if r.get("level_break") else 0
            h = gap + ROW_H
            ty, by = gap + ROW_H / 2 + 3.5, gap + (ROW_H - BAR_H) / 2
            fg = []
            where = " · ".join(x for x in (r.get("where") or []) if x)
            name_w = LABEL - 14 - (min(len(where), 14) * FS_SMALL * CHAR + 8 if where else 0)
            tip = escape("%s%s%s" % (r["name"], " (%s)" % r["point"] if r.get("point") else "",
                                     "\n" + r["where_full"] if r.get("where_full") else ""))
            fg.append('<a href="%s" target="_blank"><text class="rh-name" x="8" y="%.1f"><title>%s</title>%s &rsaquo;</text></a>'
                      % (escape(r["href"]), ty, tip, escape(fit(r["name"], name_w - 2 * FS_NAME * CHAR, FS_NAME))))
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
            rows.append(strip(h, ground(h) + "".join(fg)))
    b = BOTTOM
    end = "".join(['<path class="rh-wh" d="M%.2f,-0.5 V%g Q%.2f,%g %.2f,%g H%.2f Q%.2f,%g %.2f,%g V-0.5 Z"/>'
                   % (x, b - 3, x, b, x + 3, b, x + w - 3, x + w, b, x + w, b - 3) for x, w in cols]
                  + ['<line class="rh-mid" x1="%.2f" y1="-0.5" x2="%.2f" y2="%g"/>' % (x, x, b) for x in mids])
    rows.append(strip(b, end, "rh-end"))
    return ('<table aria-label="%s run times against working hours">\n<thead>%s</thead>\n<tbody>\n%s\n</tbody>\n</table>'
            % (escape(page["title"]), strip(HEAD, "".join(head)), "\n".join(rows)))


def render(agg):
    out = []
    for n, page in enumerate(agg["pages"]):
        if not any(g["rows"] for g in page["groups"]):
            continue
        out.append('<div class="rhpage"><h3 class="charttitle">%s</h3>\n%s\n</div>'
                   % (escape(page["title"]), page_table(page, agg["days"], n)))
    return "\n".join(out)


def build(ctx, work, shared):
    moved = load(work, DIR, "earlier.json") or {}
    rel = EARLIER if load(work, EARLIER, "plan.json") else DIR
    plan, window = load(work, rel, "plan.json"), load(work, rel, "window.json")
    stop = moved.get("stopped")
    stop = "never" if stop == "never" else (datetime.fromisoformat(stop).strftime("%a %-d %b %Y %H:%M")
                                            if stop else None)
    if not any(c["pass"] == 1 for c in plan["chunks"]):
        with open(os.path.join(work.path(rel), "plan.out")) as fh:
            why = " ".join(l for l in fh.read().splitlines() if not l.startswith("{"))
        if plan.get("outage") and stop:
            why = ("None of the units with a run point logged any history in %s, and %s, so no full week in "
                   "the reporting period has data. The site's data feed looks down." % (
                       window["label"], "they have never reported" if stop == "never"
                       else "they last reported %s" % stop))
        return {"drop": ["run-hours"], "chat": ["Run hours is left out, with nothing to draw. " + " ".join(why.split())]}
    notes = aggregate(work, rel)
    agg = load(work, rel, "agg.json")
    later = [u for u in plan["units"] if u.get("pass") == 2 and u.get("pull")]
    built = [l[2:] for l in notes.splitlines() if l.startswith("- ")]
    chat = ["Run hours: " + " ".join(built)] if built else []
    latest = load(work, DIR, "window.json")["label"]
    if rel == EARLIER:
        chat.append("Run hours shows %s, the latest full week before the site's data stopped at %s, rather than "
                    "%s, the latest full week." % (window["label"], stop, latest))
    elif stop == "never":
        chat.append("Run hours draws %s with its gap hatched: the site's run points hold no history before it, so "
                    "there is no earlier full week to show." % latest)
    elif stop:
        chat.append("Run hours draws %s with its gap hatched: the site's data stopped at %s, and the full week "
                    "before that falls outside the reporting period." % (latest, stop))
    if later:
        drawn = sum(len(g["rows"]) for p in agg["pages"] for g in p["groups"])
        chat.append("Run hours draws %d units. Its first pass holds up to 100 and takes each type whole, so the %d "
                    "beyond it are not drawn; the report makes no later pass." % (drawn, len(later)))
    return {
        "run_hours": {"html": render(agg)},
        "datelines": {"Equipment run hours":
                      "%s, the latest full week%s, against the site's working hours. Bars are exact to 15 minutes."
                      % (window["label"], " with complete data" if rel == EARLIER else "")},
        "notes": {"Run hours":
                  "<strong>Run hours.</strong> Drawn from run status or a speed, current or power reading. Enables "
                  "and schedules are not used, as they show commanded state only. Where signals disagree, the lower "
                  "runtime is used."},
        "chat": chat,
    }
