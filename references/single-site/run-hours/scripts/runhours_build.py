#!/usr/bin/env python3
"""Turn a run-hours plan and its history pulls into the view's aggregate. run_hours.py calls
run(); the command line does the same and prints the notes.

    python3 runhours_build.py <workdir>

Reads <workdir>/window.json and plan.json and the history, history-<n>.json for each of
the plan's chunks, draws each unit's row from its listed metadata with the fewest running
hours, and writes <workdir>/agg.json, the renderer's only input, with the notes to state
with the view.
"""
import argparse
import json
import math
import re
import sys
from collections import Counter
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.append(str(Path(__file__).resolve().parents[4] / "scripts"))
import peak_io as io  # noqa: E402
import runhours_plan as rules  # noqa: E402

# ---- Tunables ----------------------------------------------------------------
SLOTS_PER_DAY   = 96     # 15-minute slots
WEEK            = 7 * SLOTS_PER_DAY
BRIDGE_SLOTS    = 4      # a gap up to an hour holds the last reading; longer is hatched ...
HOLD_FACTOR     = 1.5    # ... unless the point reports less often: then 1.5 times its usual interval
ANALOG_ON_SHARE = 0.05   # an analog is ON above 5% of its own weekly maximum
DISAGREE_HOURS  = 2.0    # metadata this far apart (and 10%) get a note
CHANGE_LOG_SHARE = 0.5   # a point with readings in under half the week's slots ...
CHANGE_READINGS = 0.8    # ... where this share of readings differ from the one before logs on change
RESET_POINTS    = 10     # a sweep of this many points or more all reading 0 at once ...
RESET_BACK      = 0.8    # ... with this share of those on before on again at the next reading ...
RESET_MIN_BACK  = 3      # ... and at least this many, is a data collector restarting
SHARED_GAP_UNITS = 3     # a data gap this many units share is named once, with its times
FEED_GAP_HOURS  = 12     # every periodic point silent this long at once: the site's feed, so the week is not whole
NAMES_IN_NOTE   = 8      # list names in a note up to this many, then just count
GENERIC_ZONE    = re.compile(r"(zone|area|default|all|general|none|n/?a|unassigned|site|building)\s*\d*", re.I)
SIGNAL_WORDS    = {"status": "run status", "state": "speed state", "analog": "speed, current or power",
                   "temp": "leaving water temperature"}
TEMP_MIN_RANGE  = 5.0    # a leaving water temperature that moves less than this all week (°C) is not used ...
TEMP_MIN_RANGE_F = 9.0   # ... or this (°F) for metadata in Fahrenheit


# ---- Slots -------------------------------------------------------------------
def parse_readings(rows):
    """(fav_id, UTC time, value) for every reading that carries a value."""
    return [(str(row["fav_id"]), io.utc(row["ts"]), float(row["data"]))
            for row in rows if row.get("data") is not None]


def collector_resets(readings):
    """{UTC second: points} for each sweep in which every point read 0 for one reading.

    A data collector that restarts can write 0 to every point it serves in its
    first sweep and the true values in the next: the plant did not stop. A sweep
    is the readings that share a timestamp to the second. It is a restart where
    it holds RESET_POINTS or more points, every one of them reads 0, and nearly
    every periodic point that read above 0 just before reads above 0 again at its
    next reading. A point logged on change of value is no evidence either way.
    """
    series = {}
    for fav, ts, value in readings:
        series.setdefault(fav, []).append((ts, value))
    sweeps = {}
    for s in series.values():
        s.sort()
        periodic = not logged_on_change([v for _, v in s])
        for i, (ts, _) in enumerate(s):
            sweeps.setdefault(ts.replace(microsecond=0), []).append((s, i, periodic))
    resets = {}
    for when, members in sweeps.items():
        if len(members) < RESET_POINTS or any(s[i][1] for s, i, _ in members):
            continue
        was_on = [(s, i) for s, i, periodic in members if periodic and i and s[i - 1][1]]
        back = sum(1 for s, i in was_on if i + 1 < len(s) and s[i + 1][1])
        if back >= RESET_MIN_BACK and back >= RESET_BACK * len(was_on):
            resets[when] = len(members)
    return resets


def slot_readings(rows, window):
    """(fav_id -> {"slots": {absolute slot: (max, last reading)}, "series": readings in time order},
    {local time: points} for each collector restart, whose readings are left out).

    Slots are on the site's wall clock. A slot is ON if the point was on at any
    reading in it; the gap after it holds the slot's last reading.
    """
    tz = io.zone(window["timezone"])        # legacy names read as the zone they link to
    monday = date.fromisoformat(window["days"][0]["date"])
    readings = parse_readings(rows)
    resets = collector_resets(readings)
    stamped = []
    for fav, ts, value in readings:
        if ts.replace(microsecond=0) in resets:
            continue
        local = ts.astimezone(tz)
        day = (local.date() - monday).days
        if 0 <= day < 7:
            stamped.append((fav, local, day, value))
    out = {}
    for fav, local, day, value in sorted(stamped, key=lambda s: (s[0], s[1])):
        slot = day * SLOTS_PER_DAY + (local.hour * 60 + local.minute) // 15
        rec = out.setdefault(fav, {"slots": {}, "series": []})
        prev = rec["slots"].get(slot)
        rec["slots"][slot] = (max(value, prev[0]) if prev else value, value)
        rec["series"].append(value)
    return out, {when.astimezone(tz): n for when, n in resets.items()}


def bridge(raw, last, hold=BRIDGE_SLOTS, on_change=False, before=None):
    """Hold the last reading across gaps of up to `hold` slots; leave longer gaps None.

    A point logged on change of value holds every reading until the next, to the
    end of the week — silence is the value not changing. Before its first reading
    it holds `before` where that is known, and is left None where it is not.
    """
    out, i = list(raw), 0
    while i < WEEK:
        if out[i] is not None:
            i += 1
            continue
        j = i
        while j < WEEK and out[j] is None:
            j += 1
        if on_change and i == 0:
            out[i:j] = [before] * j
        elif on_change or j - i <= hold:
            fill = last[i - 1] if i > 0 else (out[j] if j < WEEK else None)
            out[i:j] = [fill] * (j - i)
        i = j
    return out


def hold_slots(slots):
    """(slots a reading holds, the point's usual interval in slots).

    A reading holds for 1.5 times the point's usual interval, and never under an
    hour. Most points report every 15 minutes, so a silence over an hour is an
    outage. Some are polled far less often, such as a status every 4 hours with a
    reading at each change, and hold 6.
    """
    marks = sorted(slots)
    steps = sorted(b - a for a, b in zip(marks, marks[1:]))
    usual = steps[len(steps) // 2] if steps else 1
    return max(BRIDGE_SLOTS, math.ceil(HOLD_FACTOR * usual)), usual


def logged_on_change(series):
    """Whether a point reports on change of value rather than every 15 minutes.

    Such a point sends a handful of readings a week, and nearly every one differs
    from the one before; a periodic point sends one a slot, mostly unchanged. A
    typical one sends ten readings a week, at 07:00 and 18:00, each a change.
    """
    if len(series) < 2 or len(series) > WEEK * CHANGE_LOG_SHARE:
        return False
    changes = sum(1 for a, b in zip(series, series[1:]) if a != b)
    return changes >= CHANGE_READINGS * (len(series) - 1)


def on_cut(point, distinct):
    """The reading at and above which a status, state or command point is ON.

    Binary: 1. A speed state (MSV) counts from 0 when the week shows a 0 — 0 is
    off — and otherwise from 1, the BACnet numbering, where 1 is off. Any other
    whole-number point numbered from 1 is read the same way.
    """
    if "(msv)" in point["name"].lower():
        return 1 if min(distinct) == 0 else 2
    whole = all(float(v).is_integer() for v in distinct)
    return 2 if whole and min(distinct) >= 1 and max(distinct) >= 2 else 0.5


def read_point(rec, point):
    """ON/OFF per slot for one pulled point, plus what the decision needs to know."""
    if not rec:
        return None
    slots, series = rec["slots"], rec["series"]
    if point["role"] == "temp":
        return read_temperature(slots, series, point)
    raw = [slots[s][0] if s in slots else None for s in range(WEEK)]
    last = [slots[s][1] if s in slots else None for s in range(WEEK)]
    distinct = set(series)
    if point["role"] == "analog":
        top = max(series)
        cut = ANALOG_ON_SHARE * top if top > 0 else float("inf")
        is_on = lambda v: v > cut                                    # noqa: E731
    else:
        cut = on_cut(point, distinct)
        is_on = lambda v: v >= cut                                   # noqa: E731
    on_change = logged_on_change(series)
    before = None
    if on_change and distinct <= {0.0, 1.0} and all(a != b for a, b in zip(series, series[1:])):
        before = 1.0 - series[0]              # a switch that logs only changes was the other way before
    hold, every = hold_slots(slots)
    on = [None if v is None else is_on(v) for v in bridge(raw, last, hold, on_change, before)]
    return {"on": on, "stuck": len(distinct) == 1, "held": series[0] if len(distinct) == 1 else None,
            "hours": sum(1 for x in on if x) / 4, "runs": len(ranges(on, True)), "on_change": on_change,
            "sparse": every if hold > BRIDGE_SLOTS and not on_change else None}


def read_temperature(slots, series, point):
    """A leaving water temperature shows running at or above the midpoint of its weekly range.

    Not used when the range is under 5 °C (9 °F for metadata in Fahrenheit): the water never heated or cooled.
    """
    lo, hi = min(series), max(series)
    floor = TEMP_MIN_RANGE_F if "fahrenheit" in point["name"].lower() else TEMP_MIN_RANGE
    if hi - lo < floor:
        return None
    mid = (lo + hi) / 2
    raw = [slots[s][1] if s in slots else None for s in range(WEEK)]
    hold, every = hold_slots(slots)
    on = [None if v is None else v >= mid for v in bridge(raw, raw, hold)]
    return {"on": on, "stuck": False, "held": None, "hours": sum(1 for x in on if x) / 4,
            "runs": len(ranges(on, True)), "on_change": False, "sparse": None}


def ranges(flags, want):
    """Merged [start, end) slot ranges where flags[i] is `want` (True for ON, None for a gap)."""
    out, start = [], None
    for i, flag in enumerate(list(flags) + ["end"]):
        if flag is want and start is None:
            start = i
        elif flag is not want and start is not None:
            out.append([start, i])
            start = None
    return out


# ---- The row decision ----------------------------------------------------------
class Row:
    """What decide() settled for one unit."""

    def __init__(self, point=None, reading=None, other=None, nodata=None, split=None, left_out=(), flat=False):
        self.point, self.reading, self.other = point, reading, other
        self.nodata, self.split = nodata, split
        self.left_out, self.flat = list(left_out), flat


def decide(unit, points):
    """Which metadata draws the row, following references/single-site/run-hours/run-hours-signals.md.

    The unit is drawn from the metadata with the fewest running periods. A reading off or zero
    all week is left out while another reading changes. A temperature is used only alongside a
    reading, and its changes do not make a stuck-off reading be left out. When nothing changed:
    all off is drawn off, all on is drawn on (unverified), a mix has no reliable data.
    """
    got = [(p, points.get(str(p["fav_id"]))) for p in unit["pull"]]
    got = [(p, r) for p, r in got if r]
    reads = [(p, r) for p, r in got if p["role"] != "temp"]
    temps = [(p, r) for p, r in got if p["role"] == "temp"] if reads else []
    if not reads:
        return Row(nodata="No data this week")
    moving = [(p, r) for p, r in reads if not r["stuck"]]
    left_out = [p for p, r in reads if r["stuck"] and r["hours"] == 0 and moving]
    keep = [(p, r) for p, r in reads if p not in left_out]
    if not moving and not temps:
        if len({r["hours"] > 0 for _, r in reads}) > 1:
            names = " and ".join(p["name"] for p, _ in reads[:3])
            return Row(nodata=f"{names} each held one value all week and disagree, so run time is unknown")
        other = reads[1][0] if len(reads) > 1 else None
        return Row(reads[0][0], reads[0][1], other, flat=True)
    cands = keep + temps
    both = [i for i in range(WEEK) if all(r["on"][i] is not None for _, r in cands)]
    hours = [sum(1 for i in both if r["on"][i]) / 4 for _, r in cands]
    lo = min(range(len(cands)), key=lambda i: (hours[i], i))
    hi = max(range(len(cands)), key=lambda i: hours[i])
    other = cands[hi][0] if hi != lo else (cands[1 - lo][0] if len(cands) > 1 else None)
    split = None
    if hi != lo and hours[hi] - hours[lo] >= max(DISAGREE_HOURS, 0.1 * hours[hi]):
        split = (cands[lo][0], hours[lo], cands[hi][0], hours[hi])
    return Row(cands[lo][0], cands[lo][1], other, split=split, left_out=left_out)


def feed_gap(readings):
    """[start, end) slots of the first stretch of FEED_GAP_HOURS or more in which no point
    logged every 15 minutes reported: the site's data feed stopped, not one unit. None when
    the week is whole, or when too few such points report to tell. A point logged on change
    says nothing by being silent, so it is not asked."""
    periodic = [r["on"] for r in readings if r and not r["on_change"]]
    if len(periodic) < SHARED_GAP_UNITS:
        return None
    quiet = [all(on[i] is None for on in periodic) for i in range(WEEK)]
    return next((g for g in ranges(quiet, True) if g[1] - g[0] >= FEED_GAP_HOURS * 4), None)


# ---- Text helpers --------------------------------------------------------------
def hhmm(slot):
    return "24:00" if slot >= SLOTS_PER_DAY else f"{slot * 15 // 60:02d}:{slot * 15 % 60:02d}"


def hours_text(wh):
    return "closed" if not wh else f"{hhmm(wh[0])}-{hhmm(wh[1])}"


def working_hours_note(window):
    groups = []
    for day in window["days"]:
        text = hours_text(day["wh"])
        if groups and groups[-1][1] == text:
            groups[-1][0].append(day["label"][:3])
        else:
            groups.append(([day["label"][:3]], text))
    parts = [(f"{d[0]}-{d[-1]}" if len(d) > 1 else d[0]) + f" {t}" for d, t in groups]
    source = "the site's PEAK settings" if window.get("hours_source") != "user" else "the user"
    return f"Working hours from {source}: {', '.join(parts)} ({window['tz_label']})."


def units_text(n):
    return io.plural(n, "unit")


def moment(window, local):
    """'Thu 17 08:00' for a local time in the week."""
    labels = {d["date"]: d["label"] for d in window["days"]}
    return f"{labels.get(local.date().isoformat(), f'{local:%a} {local.day}')} {local:%H:%M}"


def span_text(window, span):
    """'Mon 14 00:00 to 11:30', or 'Mon 14 22:00 to Tue 15 06:00', for a [start, end) slot range."""
    (a, b), days = span, window["days"]
    first, last = a // SLOTS_PER_DAY, (b - 1) // SLOTS_PER_DAY
    head = f"{days[first]['label']} {hhmm(a - first * SLOTS_PER_DAY)}"
    tail = hhmm(b - last * SLOTS_PER_DAY)
    return f"{head} to {tail}" if last == first else f"{head} to {days[last]['label']} {tail}"


def listing(names):
    names = list(names)
    if len(names) <= NAMES_IN_NOTE:
        return ", ".join(names)
    return ", ".join(names[:NAMES_IN_NOTE]) + f" and {len(names) - NAMES_IN_NOTE} more"


def by_type(units):
    return ", ".join(f"{t} {n}" for t, n in Counter(u["type_name"] for u in units).most_common())


def chart_link(window, unit, favs):
    """favs: fav ids, or (equipment_id, fav_id) pairs for metadata on another record (a shared Common one)."""
    groups = {}
    for f in favs:
        eid, fid = f if isinstance(f, tuple) else (unit["equipment_id"], f)
        groups.setdefault(eid, []).append(fid)
    return (f"{window['link_host']}/charts?split=true&splitbyunit=true&splitbyequip=false"
            f"&start={window['link_start']}&end={window['link_end']}&workinghours=true"
            + "".join(f"&fav-{eid}={','.join(str(x) for x in ids)}" for eid, ids in groups.items()))


def signal_kind(point):
    return "state" if point.get("state") else point["role"]


def _words(text):
    return re.findall(r"[a-z0-9]+", (text or "").lower())


def _within(part, whole):
    """Whether part's words run, in order, somewhere in whole."""
    p, w = _words(part), _words(whole)
    return bool(p) and any(w[i:i + len(p)] == p for i in range(len(w) - len(p) + 1))


def where(unit):
    """([level, zone] for the label, "" where dropped, and hover text); the label keeps only what informs.

    A zone is dropped where it is a default (Zone1, All), repeats the level, or is in
    the unit's own name (FCU Kitchen-A in zone Kitchen); a level that a more
    specific zone repeats gives way to it ('Level 2' beside 'Level 2 Kitchen'), and
    'Level 3' is shortened to 'L3'. The hover keeps both as PEAK has them.
    """
    level, zone = (" ".join((unit.get(k) or "").split()) for k in ("level", "zone"))
    hover = " · ".join(x for x in (level, zone) if x)
    if zone and (GENERIC_ZONE.fullmatch(zone) or _within(zone, unit["name"]) or _within(zone, level)):
        zone = ""
    if level and zone and _within(level, zone):
        level = ""
    level = re.sub(r"\blevel\s+(\d+)\b", r"L\1", level, flags=re.I)
    return ([level, zone] if level or zone else []), hover


# ---- Build -------------------------------------------------------------------
def load_history(work, plan):
    """The week's history rows, one history-<n>.json per chunk of the plan, de-duplicated on
    (point, time). A file holding points outside its own chunk was saved from another call's
    response, which would silently hatch units, so it stops the build."""
    kept = {}
    for n, chunk in enumerate(plan["chunks"], 1):
        name = f"history-{n}.json"
        want = {str(f) for f in chunk["fav_ids"]}
        rows = [r for r in io.read(str(work / name)).rows if isinstance(r, dict)]
        foreign = {str(r.get("fav_id")) for r in rows} - want
        if foreign:
            raise SystemExit(f"run hours: {name} holds history for {io.plural(len(foreign), 'point')} outside its "
                             "own call, so it was saved from another call's response. Save it again from its own.")
        for r in rows:
            kept[(str(r.get("fav_id")), r.get("ts"))] = r
    return list(kept.values())


def build(window, plan, rows):
    units = plan["units"]
    readings, resets = slot_readings(rows, window)
    points = {str(p["fav_id"]): read_point(readings.get(str(p["fav_id"])), p)
              for u in units for p in u["pull"]}

    notes = {"split": [], "held_other": [], "unverified": [], "off": [], "temp": [],
             "on_change": [], "sparse": [], "nodata": [], "gaps": [], "drawn": Counter()}
    pages, prev = {}, None
    for u in (u for u in units if u["pull"]):
        d = decide(u, points)
        row = {"name": u["name"], "runs": [], "gaps": [], "nodata": d.nodata, "point": None,
               "level_break": bool(prev and prev["type_name"] == u["type_name"]
                                   and prev["level"] != u["level"])}
        row["where"], row["where_full"] = where(u)
        prev = u

        def fav(p):
            return (p["equipment_id"], p["fav_id"]) if p.get("equipment_id") else p["fav_id"]
        favs = [fav(p) for p in u["pull"]]
        if d.point:
            favs = [fav(d.point)] + [fav(p) for p in u["pull"] if p["fav_id"] != d.point["fav_id"]]
            row["point"] = d.point["name"]
            row["runs"] = ranges(d.reading["on"], True)
            row["gaps"] = ranges(d.reading["on"], None)
            notes["drawn"][signal_kind(d.point)] += 1
            if d.split:
                sp, hs, ap, ha = d.split
                notes["split"].append(f"{u['name']} ({sp['name']} {hs:g} h, {ap['name']} {ha:g} h)")
            for p in d.left_out:
                notes["held_other"].append(f"{u['name']} ({p['name']})")
            if d.point["role"] == "temp":
                notes["temp"].append(u["name"] + (f" (from {d.point['shared']})" if d.point.get("shared") else ""))
            if d.flat and d.reading["hours"]:
                notes["unverified"].append(u["name"])
            if not row["runs"]:
                notes["off"].append(u["name"])
            if d.reading["on_change"]:
                notes["on_change"].append(u["name"])
            if d.reading["sparse"]:
                notes["sparse"].append((u["name"], d.reading["sparse"]))
            if row["gaps"]:
                notes["gaps"].append((u["name"], row["gaps"]))
        else:
            notes["nodata"].append(f"{u['name']} ({d.nodata.rstrip('.')})")
        row["href"] = chart_link(window, u, favs)
        page = pages.setdefault(u["page"], {})
        page.setdefault(u["type_name"], []).append(row)

    return {
        "days": [{"label": d["label"], "wh": d["wh"]} for d in window["days"]],
        "pages": [{"title": title, "groups": [{"name": g, "rows": rs} for g, rs in pages[title].items()]}
                  for title in rules.PAGE_ORDER if title in pages],
        "notes": note_lines(window, plan, units, notes, resets),
        "feed_gap": feed_gap(list(points.values())),
    }


def note_lines(window, plan, units, notes, resets):
    lines = [working_hours_note(window)]
    drawn, hatched = notes["drawn"], len(notes["nodata"])
    kinds = ", ".join(f"{SIGNAL_WORDS[r]} {drawn[r]}" for r in SIGNAL_WORDS if drawn[r])
    lines.append((f"Rows drawn from: {kinds}" if kinds else "No row could be drawn from the listed metadata")
                 + (f"; {hatched} hatched, no reliable data." if hatched else "."))
    if notes["split"]:
        lines.append(f"Metadata disagreed at {units_text(len(notes['split']))}, each drawn from the one "
                     f"with the fewest running hours: {listing(notes['split'])}.")
    if notes["held_other"]:
        lines.append("Left out as off or zero all week while another reading of the unit changed: "
                     f"{listing(notes['held_other'])}.")
    if notes["temp"]:
        lines.append("Drawn from the leaving water temperature, which showed less running than the unit's "
                     "readings (a shared Common temperature shows when the plant ran, not which unit): "
                     f"{listing(notes['temp'])}.")
    if notes["unverified"]:
        lines.append("On in every reading all week, with nothing that changed to check it against, so "
                     f"unverified: {listing(notes['unverified'])}.")
    if notes["off"]:
        lines.append(f"Off in every reading all week, so drawn as off: {listing(notes['off'])}.")
    if notes["on_change"]:
        lines.append(f"Logged on change of value rather than every 15 minutes, so each reading holds until "
                     f"the next: {listing(notes['on_change'])}.")
    if notes["sparse"]:
        every = {}
        for name, slots in notes["sparse"]:
            every.setdefault(slots, []).append(name)
        lines.append("Reported less often than every 15 minutes, so each reading holds for one and a half "
                     "times its interval and the bar edges are only that exact. "
                     + "; ".join(f"Every {interval_text(slots)}: {listing(names)}"
                                 for slots, names in sorted(every.items())) + ".")
    if notes["nodata"]:
        lines.append(f"Hatched, no reliable data: {listing(notes['nodata'])}.")
    if resets:
        lines.append("A data collector restarting, not the plant, so left out: every point in one reading "
                     "read 0, between normal readings either side, at "
                     + ", ".join(f"{moment(window, when)} ({io.plural(n, 'point')})"
                                 for when, n in sorted(resets.items())) + ".")
    lines += gap_lines(window, notes["gaps"])
    regrouped = [u for u in units if u.get("regrouped_from") and u["pull"]]
    for (was, name), n in Counter((u["regrouped_from"], u["type_name"]) for u in regrouped).items():
        lines.append(f"{units_text(n)} typed {was} in PEAK, grouped with {name} as their names say.")
    # Why a unit is not drawn is known before any history is pulled, for every unit the plan read.
    skipped = [u for u in plan["units"] if not u["pull"]]
    for why, _, note in rules.REASONS:
        hit = [u for u in skipped if u["why"] == why]
        if hit:
            lines.append(note(hit, listing, by_type))
    return lines


def gap_lines(window, gapped):
    """The data-gap notes: a stretch several units lost at once, by its times, then gaps of one unit's own."""
    counts = Counter(tuple(g) for _, gaps in gapped for g in gaps)
    shared = sorted(g for g, n in counts.items() if n >= SHARED_GAP_UNITS)
    lines = []
    if shared:
        spans = [f"{span_text(window, g)} ({units_text(counts[g])}: "
                 f"{listing(name for name, gaps in gapped if list(g) in gaps)})" for g in shared]
        more = f"; and {len(spans) - NAMES_IN_NOTE} more" if len(spans) > NAMES_IN_NOTE else ""
        lines.append("Hatched where several units lost data at once, so the data feed rather than the "
                     "plant: " + "; ".join(spans[:NAMES_IN_NOTE]) + more + ".")
    own = [name for name, gaps in gapped if any(tuple(g) not in shared for g in gaps)]
    if own:
        lines.append(f"Hatched stretches are data gaps longer than the point holds a reading: {listing(own)}.")
    return lines


def interval_text(slots):
    minutes = slots * 15
    return f"{minutes} min" if minutes < 60 else f"{minutes / 60:g} h"


def run(workdir):
    """Build the week's aggregate from <workdir>'s plan and history, write agg.json and return it."""
    work = Path(workdir)
    window = json.loads((work / "window.json").read_text())
    plan = json.loads((work / "plan.json").read_text())
    agg = build(window, plan, load_history(work, plan))
    (work / "agg.json").write_text(json.dumps(agg, indent=1))
    return agg


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("workdir")
    args = parser.parse_args(argv[1:])
    try:
        agg = run(args.workdir)
    except (OSError, ValueError, KeyError) as exc:
        sys.exit(f"runhours_build: {exc}")
    print("Notes:")
    for line in agg["notes"]:
        print(f"- {line}")


if __name__ == "__main__":
    main(sys.argv)
