#!/usr/bin/env python3
"""Equipment run hours as a report section: when each unit ran across the latest
full Monday-to-Sunday week, against the site's working hours.

runhours_plan.py fixes the week and picks every unit's points, and runhours_build.py
turns the history into the aggregate. This module drives them through the report's
hooks and draws the aggregate as static SVG in the report's design, since the report
carries no script. Where the site's data is missing from that week, it moves to the
latest full week before the data stopped. See references/single-site/run-hours/run-hours.md.
"""
import json
import os
import re
import sys
from datetime import datetime, timedelta
from html import escape

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "..", "scripts"))
import peak_io as io  # noqa: E402
import runhours_build as rb  # noqa: E402
import runhours_plan as rp  # noqa: E402

DIR = "runhours"                     # under peak/, where the run hours files are kept
EARLIER = DIR + "/earlier"           # the latest full week with data, when the latest week lacks it

# Layout, in the report's chart units (the sheet draws every chart 682 wide).
W, LABEL, RIGHT_PAD = 682, 168, 4
HEAD, GROUP_H, ROW_H, BAR_H, LEVEL_GAP, BOTTOM = 34, 20, 15, 8, 4, 6
FS_NAME, FS_SMALL = 10, 8.5
CHAR = 0.56                          # average glyph width as a share of the font size, for cutting labels


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
    """Fix one week in <peak>/<rel>/ and return its discovery and census calls. The latest full
    week unless `monday` names an earlier one."""
    site_file = os.path.join(ctx["dir"], ctx["site_file"])
    _, calls = rp.make_window(site_file, os.path.join(peak, rel), ctx["site"]["site_id"], ctx["today"], monday,
                              ctx.get("hours"))
    return [as_call(rel, c) for c in calls]


def calls(ctx):
    return window(ctx, os.path.join(ctx["dir"], "peak"), DIR)


def discoveries(work, rel):
    """The week's discovery call and its pages, as calls.json lists them."""
    pat = re.compile(re.escape(rel) + r"/discovery-\d+\.json")
    return [c for c in work.calls if pat.fullmatch(c["file"])]


def week_calls(ctx, work, rel):
    """What one week's pull still needs: discovery pages, then its plan and history."""
    first = next(c for c in discoveries(work, rel) if c["file"] == "%s/discovery-0.json" % rel)
    disc, step = work.get(first["file"]), io.call_args(first)["limit"]
    if disc.total and disc.total > step:
        pages = [io.at_offset(first, "%s/discovery-%d.json" % (rel, s), s) for s in range(step, disc.total, step)]
        missing = [p for p in pages if not work.has(p["file"])]
        if missing:
            return missing
    rh = work.path(rel)
    if not os.path.isfile(os.path.join(rh, "plan.json")):
        census = work.path(DIR)
        rp.make_plan(rh, [work.path(c["file"]) for c in discoveries(work, rel)],
                     [os.path.join(census, "census-all.json"), os.path.join(census, "census-known.json")])
    plan, win = load(work, rel, "plan.json"), load(work, rel, "window.json")
    chunks = [c for c in plan["chunks"] if c["pass"] == 1]
    return [as_call(rel, dict(rp.week_call(win, c["fav_ids"]), file="history-1-%d.json" % i))
            for i, c in enumerate(chunks, 1) if not work.has("%s/history-1-%d.json" % (rel, i))]


def stopped(ctx, work, rel):
    """When the site's data stopped short of a whole week: None when the week is whole or
    nothing in it could ever draw, the call that finds the time when only the reading before
    the week can say, else the local time, or "never" when no point has reported at all."""
    plan, win = load(work, rel, "plan.json"), load(work, rel, "window.json")
    if any(c["pass"] == 1 for c in plan["chunks"]):
        gap = rb.run(work.path(rel)).get("feed_gap")
        if not gap:
            return None
        if gap[0] > 0:                 # quiet from inside the week: the week before that point is whole
            return datetime.fromisoformat(win["days"][0]["date"]) + timedelta(minutes=15 * gap[0])
    elif not plan.get("outage"):
        return None
    probe = "%s/last-reading.json" % rel
    if not work.has(probe):
        return as_call(rel, dict(rp.probe_call(win, plan), file="last-reading.json"))
    last = rp.last_reading(work.path(rel), work.path(probe))["local"]
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
    if stop and stop != "never":
        t = datetime.fromisoformat(stop)
        stop = "%s %d %s" % (t.strftime("%a"), t.day, t.strftime("%b %Y %H:%M"))
    if not any(c["pass"] == 1 for c in plan["chunks"]):
        why = "%s %s" % (rp.nothing_to_draw(plan), " ".join(rp.summary_lines(plan)))
        if plan.get("outage") and stop:
            why = ("None of the units with a run point logged any history in %s, and %s, so no full week in "
                   "the reporting period has data. The site's data feed looks down." % (
                       window["label"], "they have never reported" if stop == "never"
                       else "they last reported %s" % stop))
        return {"drop": True, "chat": ["Run hours is left out, with nothing to draw: " + why]}
    agg = rb.run(work.path(rel))
    later = [u for u in plan["units"] if u.get("pass") == 2 and u.get("pull")]
    chat = ["Run hours: " + " ".join(agg["notes"])] if agg["notes"] else []
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
        chat.append("Run hours draws %d units. Its first pass holds up to %d and takes each type whole, so the %d "
                    "beyond it are not drawn; the report makes no later pass." % (drawn, rp.CAP_UNITS, len(later)))
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
