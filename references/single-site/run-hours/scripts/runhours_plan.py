#!/usr/bin/env python3
"""Plan a run-hours pull: which week, which points, and in what order. run_hours.py calls
these functions; the command line runs the same steps and prints what they decided.

    python3 runhours_plan.py window <site.json> <workdir> [--site-id N] [--week-of YYYY-MM-DD]
                                    [--hours "Mon-Fri 08:00-18:00, Sat 09:00-13:00"]
    python3 runhours_plan.py plan <workdir> <discovery.json> [more.json ...]
    python3 runhours_plan.py last <workdir> <last-reading.json>

window  Fixes the last full Monday-to-Sunday week in site local time from the saved
        search_sites result, writes <workdir>/window.json, and gives the discovery call.
        --hours assesses against the user's hours instead of the site's.
plan    Keeps each unit's metadata listed for its equipment type in
        references/single-site/run-hours/run-hours-signals.md, orders the units for the
        view, and writes <workdir>/plan.json.
last    Reads the latest-reading call, the newest reading before the week of a
        sample of the site's run points, and writes <workdir>/last.json.

The rules are the reference's tables, parsed and checked at run time: change a rule
there, not here.
"""
import argparse
import json
import re
import sys
from collections import Counter
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[4] / "scripts"))
import peak_io as io  # noqa: E402

SIGNALS = Path(__file__).resolve().parent.parent / "run-hours-signals.md"

# ---- Tunables ----------------------------------------------------------------
POINTS_PER_CALL = 36     # ~672 rows per point-week keeps a call under ~25k rows / ~2 MB
DISCOVERY_LIMIT = 1000   # units per discovery page: ~170 KB for a 100-unit office tower
PROBE_POINTS    = 20     # points asked for their latest reading before the week, a type at a
                         # time, to find when the site's data stopped
HISTORY_FIELDS  = ["fav_id", "ts", "data"]
PAGE_ORDER      = ["Central plant", "Field units"]
DAY_KEYS        = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
DAY_ABBR        = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


# ---- Reference tables ---------------------------------------------------------
# The columns each parsed table must carry. A table may carry more; the rules read only these.
SCHEMA = {
    "Central plant": ["Equipment type", "Short code", "Metadata to fetch"],
    "Field units": ["Equipment type", "Short code", "Metadata to fetch"],
}
UNIT_SUFFIX = re.compile(r"\s*\((?:msv|hz|rpm|%|v|a|kw|fahrenheit|ft/min)\)\s*$|\s+%$", re.I)


class TableError(ValueError):
    pass


def read_tables(path=SIGNALS):
    """Every pipe table in the reference, keyed by the ## heading above it, each row a dict with its
    line number under "_line". A table is a header row, a --- separator, then rows of the header's
    width; anything else stops with the file and line."""
    tables, heading = {}, None
    lines = Path(path).read_text().splitlines()
    name, i = Path(path).name, 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("## "):
            heading = line[3:].strip()
        elif line.startswith("|") and heading and heading not in tables:
            header = _cells(line)
            sep = lines[i + 1].strip() if i + 1 < len(lines) else ""
            if not re.fullmatch(r"\|(\s*:?-{3,}:?\s*\|)+", sep) or len(_cells(sep)) != len(header):
                raise TableError(f"{name}:{i + 2}: the '{heading}' table needs a --- separator row under its header")
            rows, i = [], i + 2
            while i < len(lines) and lines[i].strip().startswith("|"):
                cells = _cells(lines[i])
                if len(cells) != len(header):
                    raise TableError(f"{name}:{i + 1}: {len(cells)} cells where the '{heading}' table has "
                                     f"{len(header)} columns")
                rows.append(dict(zip(header, cells), _line=i + 1))
                i += 1
            tables[heading] = rows
            continue
        i += 1
    for heading, columns in SCHEMA.items():
        if heading not in tables:
            raise TableError(f"{name}: no table under '## {heading}'")
        have = set(tables[heading][0]) if tables[heading] else set()
        missing = [c for c in columns if c not in have]
        if missing:
            raise TableError(f"{name}: the '{heading}' table has no '{missing[0]}' column")
    return tables


def _cells(line):
    return [c.strip().strip("`").strip() for c in line.strip().strip("|").split("|")]


def name_tokens(name):
    return [t for t in re.split(r"[^A-Za-z0-9]+", (name or "").upper()) if t]


def base_name(name):
    """The metadata name without a unit in brackets: 'Supply Air Fan Speed (Hz)' -> 'Supply Air Fan Speed'."""
    prev, n = None, (name or "").strip()
    while prev != n:
        prev, n = n, UNIT_SUFFIX.sub("", n).strip()
    return n


def metadata_role(name):
    """'temp' for a leaving water temperature, 'status' for a status (or a speed state), else 'analog'."""
    b = base_name(name).lower()
    if b.endswith("temperature"):
        return "temp"
    if re.search(r"(status|running)$", b) or "(msv)" in (name or "").lower():
        return "status"
    return "analog"


def natural(text):
    """Sort key that orders 1, 2, 10 rather than 1, 10, 2; blanks last."""
    if not text:
        return [(1, "")]
    return [(0, int(t), "") if t.isdigit() else (0, -1, t.lower())
            for t in re.split(r"(\d+)", text) if t]


def plural(n, word):
    """'1 unit', '2 units'; 'history call' becomes 'history calls'."""
    return f"{n} {word}" + ("" if n == 1 else "s")


class Rules:
    """The tables of references/single-site/run-hours/run-hours-signals.md, checked and ready to classify with."""

    def __init__(self, path=SIGNALS):
        tables = read_tables(path)
        name = Path(path).name
        self.types, self.lists = {}, {}
        for page in PAGE_ORDER:
            for row in tables[page]:
                code = row["Short code"]
                at = f"{name}:{row['_line']}"
                if not code or code in self.types:
                    raise TableError(f"{at}: the short code '{code}' is missing or already an equipment type")
                names = [n.strip() for n in row["Metadata to fetch"].split("·") if n.strip()]
                if not names:
                    raise TableError(f"{at}: {code} lists no metadata to fetch")
                self.types[code] = {"code": code, "name": row["Equipment type"], "order": len(self.types),
                                    "page": page}
                self.lists[code] = {base_name(n): i for i, n in enumerate(names)}

    def classify(self, name, *type_codes):
        """(role, rank key, speed state?) when the name is listed for one of these types, else None."""
        b = base_name(name)
        for code in type_codes:
            rank = self.lists.get(code, {}).get(b)
            if rank is not None:
                role = metadata_role(name)
                state = role == "status" and "(msv)" in name.lower() and "speed" in name.lower()
                return role, (rank, len(name)), state
        return None

    def charted_type(self, equipment_name, peak_type):
        """A unit with FCU in its name is a Fan Coil Unit, whatever its type in PEAK."""
        fcu = any(t == "FCU" or re.fullmatch(r"FCU\d+", t) for t in name_tokens(equipment_name))
        return "FCU" if fcu and "FCU" in self.types else peak_type


# ---- window ------------------------------------------------------------------
def read_page(path):
    """(rows, pagination total) of one saved response, whatever its wrapper."""
    r = io.read(str(path))
    return r.rows, r.total


def load_site(path, site_id=None):
    """The site's search_sites row: the one --site-id names, else the first."""
    rows = read_page(path)[0]
    if site_id is not None:
        rows = [r for r in rows if isinstance(r, dict) and str(r.get("site_id")) == str(site_id)]
    site = rows[0] if rows else None
    if not isinstance(site, dict) or "timezone" not in site:
        sys.exit(f"{path}: expected the search_sites result for "
                 f"{'site %s' % site_id if site_id is not None else 'one site'}, with timezone")
    return site


def _slot(hhmm):
    hours, minutes = (int(x) for x in str(hhmm or "0:0").split(":")[:2])
    return max(0, min(96, round((hours * 60 + minutes) / 15)))


def working_slots(hours):
    """Per-day [start, end) slots from the site's working_hours; None for a closed day."""
    days = []
    for key in DAY_KEYS:
        start, end = _slot(hours.get(f"{key}Start")), _slot(hours.get(f"{key}End"))
        if not hours.get(f"{key}Enabled") or start == end == 0:
            days.append(None)
        else:
            days.append([start, end if end > start else 96])   # past midnight: to midnight
    return days


HOURS_GROUP = re.compile(r"(?P<days>[a-z]+(?:\s*-\s*[a-z]+)?)\s+(?P<start>\d{1,2}:\d{2})\s*-\s*(?P<end>\d{1,2}:\d{2})")


def parse_hours(spec):
    """working_hours in the site record's own keys from 'Mon-Fri 08:00-18:00, Sat 09:00-13:00'.

    Groups are separated by commas or semicolons; a day range may wrap
    (Fri-Mon); an end of 00:00 or 24:00 is midnight. A day not named is closed.
    """
    def day(word):
        hit = [i for i, key in enumerate(DAY_KEYS) if len(word) >= 3 and key.startswith(word)]
        if not hit:
            raise ValueError(f"--hours: '{word}' is not a day (Mon, Tue, ... Sun)")
        return hit[0]

    hours = {f"{key}{part}": value for key in DAY_KEYS
             for part, value in (("Enabled", False), ("Start", "00:00"), ("End", "00:00"))}
    for group in (g.strip().lower() for g in re.split(r"[,;]", spec or "") if g.strip()):
        m = HOURS_GROUP.fullmatch(group)
        if not m:
            raise ValueError(f"--hours: cannot read '{group}'; write e.g. \"Mon-Fri 08:00-18:00, Sat 09:00-13:00\"")
        ends = [day(w.strip()) for w in m["days"].split("-")]
        first, last = ends[0], ends[-1]
        for i in range((last - first) % 7 + 1):
            key = DAY_KEYS[(first + i) % 7]
            end = "24:00" if _slot(m["end"]) == 0 else m["end"]          # an end of 00:00 is midnight
            hours.update({f"{key}Enabled": True, f"{key}Start": m["start"], f"{key}End": end})
    for key in DAY_KEYS:
        start, end = _slot(hours[f"{key}Start"]), _slot(hours[f"{key}End"])
        if hours[f"{key}Enabled"] and end and end <= start:
            raise ValueError(f"--hours: {key} ends at or before it starts")
    return hours


def week_label(days):
    first, last = days[0], days[-1]
    head = f"Mon {first.day}"
    if first.month != last.month or first.year != last.year:
        head += f" {first:%b}" + (f" {first.year}" if first.year != last.year else "")
    return f"{head} to Sun {last.day} {last:%b} {last.year}"


def make_window(site_path, workdir, site_id=None, today=None, week_of=None, hours=None):
    """Fix the week in site local time, write <workdir>/window.json, and return (window, calls): the
    discovery call, as {file, query_name, args, fields}."""
    site = load_site(site_path, site_id)
    tz = io.zone(site["timezone"])          # legacy names read as the zone they link to
    work = Path(workdir)
    work.mkdir(parents=True, exist_ok=True)

    today = date.fromisoformat(today) if today else datetime.now(tz).date()
    if week_of:
        ref = date.fromisoformat(week_of)
        monday = ref - timedelta(days=ref.weekday())
        if monday + timedelta(days=7) > today:
            sys.exit(f"the week of {week_of} has not finished in site local time")
    else:
        monday = today - timedelta(days=today.weekday() + 7)
    dates = [monday + timedelta(days=i) for i in range(7)]

    def utc(d):
        return datetime.combine(d, time(0), tzinfo=tz).astimezone(timezone.utc)

    start, end = utc(monday), utc(monday + timedelta(days=7))
    hours_source = "site"
    if hours:
        site["working_hours"], hours_source = parse_hours(hours), "user"
    slots = working_slots(site.get("working_hours") or {})
    if not any(slots):
        sys.exit("working hours are empty (every day closed or 00:00). Ask the user what hours to "
                 'assess against and run window again with them, e.g. --hours "Mon-Fri 08:00-18:00, '
                 'Sat 09:00-13:00"; a day not named is closed.')

    names = list(dict.fromkeys(datetime.combine(d, time(12), tzinfo=tz).tzname() for d in dates))   # in date order
    window = {
        "site_id": site["site_id"], "site_name": site["site_name"],
        "timezone": site["timezone"], "tz_label": "/".join(names),
        "hours_source": hours_source,
        "start": start.strftime("%Y-%m-%dT%H:%M:%SZ"), "end": end.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "link_start": start.strftime("%Y-%m-%dT%H:%M:%S.000"),
        "link_end": end.strftime("%Y-%m-%dT%H:%M:%S.000"),
        "link_host": io.host(site),
        "label": week_label(dates),
        "days": [{"date": d.isoformat(), "label": f"{DAY_ABBR[i]} {d.day}", "wh": slots[i]}
                 for i, d in enumerate(dates)],
    }
    (work / "window.json").write_text(json.dumps(window, indent=1))

    charted = list(Rules().types)
    # One row per unit of an in-scope type, its points nested: the unit's name, type
    # and level travel once rather than on every point.
    discovery = {
        "query_name": "platform.equipment",
        "args": {"site_id": site["site_id"], "is_active": True, "metadata_type_codes": charted,
                 "limit": DISCOVERY_LIMIT, "start_index": 0},
        "fields": ["equipment_id", "name", "metadata_type.type_code", "zone.level.level_name",
                   "zone.zone_name.zone_name",
                   {"path": "favourites", "sub_fields": [
                       "fav_id", "is_active", "metadata.name",
                       {"path": "history_available",
                        "args": {"start": window["start"], "end": window["end"], "end_exclusive": True}}]}],
    }
    return window, [dict(discovery, file="discovery-0.json")]


def cmd_window(args):
    window, calls = make_window(args.site, args.workdir, args.site_id, args.today, args.week_of, args.hours)
    print(f"{window['site_name']}: {window['label']} ({window['tz_label']}), "
          f"{window['start']} to {window['end']} UTC. Wrote {Path(args.workdir) / 'window.json'}.")
    for c in calls:
        print(f"{c['file']}: " + json.dumps({k: v for k, v in c.items() if k != "file"}))


# ---- plan --------------------------------------------------------------------


def read_units(paths):
    """Discovered units with their points, de-duplicated across pages.

    Reads the equipment-rooted discovery: one row per unit, its points nested under it.
    """
    units, seen = {}, set()

    def unit_for(eid, eq):
        return units.setdefault(eid, {
            "equipment_id": eid, "name": eq.get("name") or str(eid),
            "peak_type": (eq.get("metadata_type") or {}).get("type_code"),
            "level": ((eq.get("zone") or {}).get("level") or {}).get("level_name"),
            "zone": ((eq.get("zone") or {}).get("zone_name") or {}).get("zone_name"),
            "points": []})

    for path in paths:
        for row in read_page(path)[0]:
            unit = unit_for(row["equipment_id"], row)
            for p in row.get("favourites") or []:
                if p.get("is_active") is False or p.get("fav_id") in seen:
                    continue
                seen.add(p.get("fav_id"))
                unit["points"].append(p)
    return list(units.values())


SENSOR_ROLES = ("status", "analog")              # readings; a temperature is never used on its own
COMMAND_END = re.compile(r"(enable|command|occupancy)$", re.I)


# Why a unit is left off the chart, in the order the notes give them: the key the plan records, what the
# plan's summary says, and the note naming the units, written from (units, listing, by_type).
REASONS = [
    ("command only", "only an enable, command or schedule, no sensor",
     lambda us, ls, bt: "Only an enable, command or schedule, with no sensor to show the unit ran, not drawn: "
                        f"{ls(u['name'] for u in us)} ({bt(us)})."),
    ("no history this week", "listed metadata, but no history this week",
     lambda us, ls, bt: f"No history this week, not drawn: {ls(u['name'] for u in us)}."),
    ("no points", "no points in PEAK",
     lambda us, ls, bt: f"No points in PEAK, not drawn: {ls(u['name'] for u in us)} ({bt(us)})."),
    ("shared record", "a Common record, which covers several units",
     lambda us, ls, bt: f"Common records, not drawn, as each covers several units: {ls(u['name'] for u in us)} "
                        f"({bt(us)})."),
    ("HLI record", "a chiller's HLI record, which repeats the chiller",
     lambda us, ls, bt: f"Chiller HLI records, not drawn, as each repeats its chiller: {ls(u['name'] for u in us)}."),
    ("temperature only", "only a temperature, which is never used on its own",
     lambda us, ls, bt: "Only a leaving water temperature, which is never used on its own, not drawn: "
                        f"{ls(u['name'] for u in us)}."),
    ("no listed metadata", "none of the metadata listed for its type",
     lambda us, ls, bt: f"None of the metadata listed for their type, not drawn: {ls(u['name'] for u in us)} "
                        f"({bt(us)})."),
]
WHY = {key: summary for key, summary, _ in REASONS}


def pick_points(unit, rules):
    """Every metadata listed for the unit's equipment type that the unit has, with history this week.

    Enables, commands and schedules are not listed: they say what the unit was told to do, not that it
    ran. A record with Common or HLI in its name is not a unit and is not drawn; a Common record's
    leaving water temperature can still serve its type's units.
    """
    found = []
    for p in unit["points"]:
        name = (p.get("metadata") or {}).get("name") or ""
        hit = rules.classify(name, unit["peak_type"], unit["type"])
        if hit:
            role, key, state = hit
            found.append({"fav_id": p["fav_id"], "name": name, "role": role, "key": key, "state": state,
                          "live": bool(p.get("history_available"))})
    found.sort(key=lambda c: (c["key"], c["fav_id"]))
    pull, seen = [], set()
    for c in found:
        if c["live"] and base_name(c["name"]) not in seen:
            seen.add(base_name(c["name"]))
            pull.append(c)
    unit["temps"] = [{"fav_id": c["fav_id"], "name": c["name"], "role": "temp"} for c in pull if c["role"] == "temp"]
    tokens = name_tokens(unit["name"])
    if "COMMON" in tokens or "HLI" in tokens:
        unit["pull"], unit["why"] = [], "shared record" if "COMMON" in tokens else "HLI record"
        return
    readings = [c for c in pull if c["role"] in SENSOR_ROLES]
    if not readings:
        pull = []                                  # a temperature is never the only metadata used
    unit["pull"] = [dict({k: c[k] for k in ("fav_id", "name", "role")}, **({"state": True} if c["state"] else {}))
                    for c in pull]
    if pull:
        unit["probe"] = {"fav_id": readings[0]["fav_id"], "unit": unit["name"], "point": readings[0]["name"]}
        return
    names = [(p.get("metadata") or {}).get("name") or "" for p in unit["points"]]
    listed = [c for c in found if c["role"] in SENSOR_ROLES]
    if listed:
        unit["why"] = "no history this week"
        unit["probe"] = {"fav_id": listed[0]["fav_id"], "unit": unit["name"], "point": listed[0]["name"]}
    elif not unit["points"]:
        unit["why"] = "no points"
    elif unit["temps"]:
        unit["why"] = "temperature only"
    elif any(COMMAND_END.search(base_name(n)) for n in names):
        unit["why"] = "command only"
    else:
        unit["why"] = "no listed metadata"


def borrow_shared_temperature(units):
    """A unit with no leaving water temperature of its own takes its type's Common record's, where the site
    has exactly one."""
    for ty in {u["type"] for u in units}:
        commons = [u for u in units if u["type"] == ty and u.get("temps") and "COMMON" in name_tokens(u["name"])]
        if len(commons) != 1:
            continue
        src, t = commons[0], commons[0]["temps"][0]
        for u in units:
            if u is not src and u["type"] == ty and u["pull"] and not any(p["role"] == "temp" for p in u["pull"]):
                u["pull"].append({"fav_id": t["fav_id"], "name": t["name"], "role": "temp",
                                  "equipment_id": src["equipment_id"], "shared": src["name"]})


def make_plan(workdir, discovery):
    """Pick every unit's metadata from the saved discovery pages, write <workdir>/plan.json and return the plan."""
    work = Path(workdir)
    rules = Rules()
    units = []
    for unit in read_units(discovery):
        peak = unit["peak_type"]
        if peak not in rules.types:
            continue                      # discovery asks only for the types in the tables
        unit["type"] = rules.charted_type(unit["name"], peak)
        ty = rules.types[unit["type"]]
        unit["type_name"], unit["page"] = ty["name"], ty["page"]
        if unit["type"] != peak:
            unit["regrouped_from"] = rules.types[peak]["name"]
        pick_points(unit, rules)
        units.append(unit)
    borrow_shared_temperature(units)

    def order(u):
        return (PAGE_ORDER.index(u["page"]), rules.types[u["type"]]["order"], natural(u["level"]), natural(u["name"]))

    units.sort(key=order)
    favs = list(dict.fromkeys(p["fav_id"] for u in units for p in u["pull"]))
    chunks = [{"fav_ids": favs[i:i + POINTS_PER_CALL]} for i in range(0, len(favs), POINTS_PER_CALL)]

    dead = [u for u in units if u.get("why") == "no history this week"]
    drawn = [u for u in units if u["pull"]]
    plan = {
        "units": [{k: u.get(k) for k in ("equipment_id", "name", "type", "type_name", "page",
                                          "level", "zone", "regrouped_from", "pull", "why")}
                  for u in units],
        "chunks": chunks,
        "outage": bool(dead) and not drawn,
        "probe": probe_points(drawn if chunks else dead),
    }
    unknown = sorted({u["why"] for u in units if u.get("why")} - set(WHY))
    if unknown:
        raise ValueError(f"a unit left off the chart for '{unknown[0]}', which REASONS does not name")
    (work / "plan.json").write_text(json.dumps(plan, indent=1))
    return plan


def cmd_plan(args):
    plan = make_plan(args.workdir, args.discovery)
    print("\n".join(summary_lines(plan)))
    if not plan["chunks"]:
        print(nothing_to_draw(plan))


def probe_points(units):
    """Up to PROBE_POINTS of the units' best points, taken a type at a time so every type is asked."""
    by_type = {}
    for u in units:
        by_type.setdefault(u["type"], []).append(u["probe"])
    out, queues = [], list(by_type.values())
    while queues and len(out) < PROBE_POINTS:
        out += [q.pop(0) for q in queues][:PROBE_POINTS - len(out)]
        queues = [q for q in queues if q]
    return out


def summary_lines(plan):
    """What the plan decided, in sentences: the units it draws, and why the rest are not drawn."""
    out = []
    drawn = [u for u in plan["units"] if u["pull"]]
    if drawn:
        types = Counter(u["type_name"] for u in drawn)
        points = sum(len(u["pull"]) for u in drawn)
        out.append(f"To draw: {plural(len(drawn), 'unit')} in {plural(len(types), 'type')}, "
                   f"{plural(points, 'point')}, {plural(len(plan['chunks']), 'history call')}.")
    for why, n in Counter(u["why"] for u in plan["units"] if not u["pull"]).items():
        out.append(f"Not drawn: {plural(n, 'unit')}, {WHY[why]}.")
    regrouped = Counter(f"{u['regrouped_from']} as {u['type_name']}"
                        for u in plan["units"] if u["regrouped_from"] and u["pull"])
    if regrouped:
        out.append("Regrouped by name: " + ", ".join(f"{k} {n}" for k, n in regrouped.items()) + ".")
    return out


def nothing_to_draw(plan):
    """Why a plan with no history call draws nothing."""
    if plan["outage"]:
        dead = sum(1 for u in plan["units"] if u.get("why") == "no history this week")
        return (f"none of the {plural(dead, 'unit')} with listed metadata logged any history this week, so the "
                "site's data feed looks down.")
    return "no unit at the site has the metadata listed for its equipment type."


def history_call(args):
    return {"query_name": "platform.history", "args": args, "fields": HISTORY_FIELDS}


def week_call(window, fav_ids):
    """One chunk's history over the week."""
    return history_call({"fav_ids": fav_ids, "start": window["start"], "end": window["end"], "end_exclusive": True})


def probe_call(window, plan):
    """The newest reading before the week of each sampled point: when the site's data stopped."""
    return history_call({"fav_ids": [p["fav_id"] for p in plan["probe"]], "latest": True,
                         "end": window["start"], "end_exclusive": True})


def last_reading(workdir, response):
    """When the site last reported before the week: the newest reading of the points the plan probed,
    written to <workdir>/last.json and returned, its "local" None where none has reported."""
    work = Path(workdir)
    window = json.loads((work / "window.json").read_text())
    probe = {str(p["fav_id"]): p for p in json.loads((work / "plan.json").read_text()).get("probe") or []}
    if not probe:
        raise ValueError("plan.json has no probe: the plan found no unit with listed metadata")
    rows = [r for r in read_page(response)[0] if str(r.get("fav_id")) in probe and r.get("ts")]
    if not rows:
        last = {"local": None}
    else:
        newest = max(rows, key=lambda r: io.utc(r["ts"]))
        local = io.utc(newest["ts"]).astimezone(io.zone(window["timezone"]))
        p = probe[str(newest["fav_id"])]
        last = {"local": local.isoformat(), "text": f"{local:%a} {local.day} {local:%b %Y %H:%M} {local.tzname()}",
                "unit": p["unit"], "point": p["point"]}
    (work / "last.json").write_text(json.dumps(last))
    return last


def cmd_last(args):
    last = last_reading(args.workdir, args.response)
    print("The site's run points last reported %s." % last["text"] if last["local"]
          else "None of the points asked has a reading in PEAK's history before the week.")


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    w = sub.add_parser("window", help="fix the week and print the discovery calls")
    w.add_argument("site", help="saved search_sites result for the site")
    w.add_argument("workdir")
    w.add_argument("--site-id", type=int, help="the site to plan, where the search returned several")
    w.add_argument("--week-of", help="any date in the Monday-to-Sunday week to show")
    w.add_argument("--hours", help='the user\'s working hours, e.g. "Mon-Fri 08:00-18:00, Sat 09:00-13:00"; '
                                   "a day not named is closed")
    w.add_argument("--today", help=argparse.SUPPRESS)
    p = sub.add_parser("plan", help="pick each unit's metadata from the discovery pages")
    p.add_argument("workdir")
    p.add_argument("discovery", nargs="+", help="saved discovery pages")
    last = sub.add_parser("last", help="say when the site last reported, from the saved latest-reading call")
    last.add_argument("workdir")
    last.add_argument("response", help="saved response of the latest-reading call")
    args = parser.parse_args(argv[1:])
    try:
        {"window": cmd_window, "plan": cmd_plan, "last": cmd_last}[args.command](args)
    except (ValueError, KeyError) as exc:
        sys.exit(f"runhours_plan: {exc}")


if __name__ == "__main__":
    main(sys.argv)
