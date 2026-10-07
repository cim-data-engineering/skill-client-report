#!/usr/bin/env python3
"""Plan a run-hours pull: which week, which points, and in what order.

Usage:
    python3 runhours_plan.py window <site.json> <workdir> [--week-of YYYY-MM-DD] [--include LT,...]
                                    [--hours "Mon-Fri 08:00-18:00, Sat 09:00-13:00"]
    python3 runhours_plan.py plan <workdir> <discovery.json> [more.json ...] [--census census.json ...] [--cap N]
    python3 runhours_plan.py calls <workdir> [--pass 2]
    python3 runhours_plan.py last <workdir> <last-reading.json>

window  Reads the saved search_sites result (timezone and working hours), fixes
        the last full Monday-to-Sunday week in site local time, writes
        <workdir>/window.json and prints the discovery and census calls to make.
        --hours assesses against the user's hours instead of the site's.
plan    Sorts every discovered point with the rules in
        references/run-hours/run-hours-signals.md, picks each unit's
        candidate points, orders the units for the view, splits them into a
        first pass of up to --cap units and the rest, writes
        <workdir>/plan.json and prints the history calls to make.
calls   Prints the history calls for the later pass, once the user asks for it.
last    Reads the latest-reading call the plan prints when nothing logged all
        week, and says when the site last reported, in site local time.

The rules are the reference's tables, parsed at run time — change a rule there,
not here. Standard library only — no third-party dependencies, by design, so
the script runs wherever the skill is unpacked.
"""
import argparse
import json
import re
import sys
from collections import Counter
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

sys.dont_write_bytecode = True             # leave no __pycache__ beside the skill
sys.path.insert(0, str(Path(__file__).resolve().parent))
from runhours_history import read_page, read_results  # noqa: E402

SIGNALS = Path(__file__).resolve().parent.parent / "run-hours-signals.md"

# ---- Tunables ----------------------------------------------------------------
CAP_UNITS       = 100    # first-pass size; central plant is always fetched whole
POINTS_PER_CALL = 36     # ~672 rows per point-week keeps a call under ~25k rows / ~2 MB
DISCOVERY_LIMIT = 1000   # units per discovery page: ~170 KB for a 100-unit office tower
PROBE_POINTS    = 20     # points asked for the latest reading when nothing logged all week,
                         # a type at a time; the call returns one row, the newest of them all
HISTORY_FIELDS  = ["fav_id", "ts", "data"]
DEFAULT_HOST    = "https://ace.cimenviro.com"
PAGE_ORDER      = ["Central plant", "Field units", "Other"]
ROLE_ORDER      = ["status", "analog", "command", "compressor"]
TRAILING_UNITS  = {"%", "percent", "w", "kw", "v", "a", "msv"}
DAY_KEYS        = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
DAY_ABBR        = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
NUMBERED        = re.compile(r"([A-Z]*)0*(\d+)([A-Z]*)")    # 'P01A' -> P, 1, A; '10' -> '', 10, ''


# ---- Reference tables ---------------------------------------------------------
def read_tables(path=SIGNALS):
    """Every pipe table in the reference, keyed by the ## heading above it."""
    tables, heading = {}, None
    lines = Path(path).read_text().splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("## "):
            heading = line[3:].strip()
        elif line.startswith("|") and heading and heading not in tables:
            header = _cells(line)
            rows, i = [], i + 2                          # skip the --- separator
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append(dict(zip(header, _cells(lines[i]))))
                i += 1
            tables[heading] = rows
            continue
        i += 1
    return tables


def _cells(line):
    return [c.strip().strip("`").strip() for c in line.strip().strip("|").split("|")]


def _split(cell):
    return [p.strip() for p in (cell or "").split(",") if p.strip()]


def _yes(cell):
    return (cell or "").strip().lower() == "yes"


def _phrase(text):
    """Whole-word, case-insensitive matcher for one phrase."""
    return re.compile(r"(?<![a-z0-9])" + re.escape(text.lower()) + r"(?![a-z0-9])")


def normalise(name):
    """Lower-case name without brackets or a trailing unit, and whether it is (MSV)."""
    low = name.lower()
    msv = "(msv)" in low
    tokens = re.sub(r"\([^)]*\)", " ", low).split()
    while tokens and tokens[-1] in TRAILING_UNITS:
        tokens.pop()
    return " ".join(tokens), msv


def name_tokens(name):
    return [t for t in re.split(r"[^A-Za-z0-9]+", (name or "").upper()) if t]


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
    """The tables of references/run-hours/run-hours-signals.md, ready to classify with."""

    NEEDED = ("Equipment types", "Regrouped by name", "Never charted", "Roles",
              "Never a run signal", "Which point wins", "Runs around the clock")

    def __init__(self, path=SIGNALS):
        tables = read_tables(path)
        missing = [h for h in self.NEEDED if h not in tables]
        if missing:
            raise ValueError(f"{Path(path).name}: no table under '## {missing[0]}'")
        self.types = {}
        for order, row in enumerate(tables["Equipment types"]):
            self.types[row["Code"]] = {
                "code": row["Code"], "name": row["Equipment type"], "order": order,
                "page": row["Page"], "system": row["System"],
                "words": [p.upper() for p in _split(row["Name word"])],
                "flags": {col for col, cell in row.items() if _yes(cell)},   # 'Compressor is the unit', ...
                "also_never": [_phrase(p) for p in _split(row["Also never"])],
            }
        columns = set(tables["Equipment types"][0]) if tables["Equipment types"] else set()
        self.regroup_from = {row["Code"]: set(_split(row["Takes units PEAK types as"]))
                             for row in tables["Regrouped by name"]}
        self.never_charted = {c for row in tables["Never charted"] for c in _split(row["Codes"])}
        self.endings = {row["Role"]: [e.lower() for e in _split(row["Name ends with, best first"])]
                        for row in tables["Roles"]}
        self.never, self.marks_plant = [], []
        for row in tables["Never a run signal"]:
            exempt = (row.get("Except where") or "").strip() or None
            if exempt and exempt not in columns:
                raise ValueError(f"Never a run signal: 'Except where' names no Equipment types "
                                 f"column: {exempt}")
            for p in _split(row["Name contains"]):
                self.never.append((_phrase(p), exempt))
                if _yes(row.get("Marks plant")):
                    self.marks_plant.append(_phrase(p))
        self.components = [(len(p), int(row["Rank"]), _phrase(p))
                           for row in tables["Which point wins"]
                           for p in _split(row["Component named"]) if not p.startswith("(")]
        self.by_word = {w: code for code, ty in self.types.items() for w in ty["words"]}
        self.compressor = _phrase("compressor")
        clock = tables["Runs around the clock"]
        self.clock_codes = {c for row in clock for c in _split(row["Codes"])}
        self.clock_words = [_phrase(p) for row in clock for p in _split(row["Name or zone contains"])]

    def classify(self, name, type_code):
        """(role, rank key, speed state?) for a point name on this type, or None if no run signal."""
        n, msv = normalise(name)
        ty = self.types.get(type_code, {})
        flags = ty.get("flags", set())
        if any(rx.search(n) for rx, exempt in self.never if exempt not in flags) \
                or any(p.search(n) for p in ty.get("also_never", [])):
            return None
        # A point only this type's exception lets through — a boiler's burner status — is
        # its last resort: the boiler's own status beside it still decides the row.
        excepted = any(rx.search(n) for rx, exempt in self.never if exempt)
        match = None
        for role, ends in self.endings.items():
            for pos, end in enumerate(ends):
                if (n == end or n.endswith(" " + end)) and (match is None or len(end) > len(match[2])):
                    match = (role, pos, end)
        if not match:
            return None
        role, pos, end = match
        rank = self.component_rank(n)
        if end in ("load", "output") and rank != 2:
            return None                  # a coil's or a system's load, not the unit's
        state = msv and role == "analog"
        if state:
            role, pos = "status", 0      # an (MSV) speed is a state: off, low, high
        if self.compressor.search(n) and "Compressor is the unit" not in flags:
            if role != "status":
                return None
            role = "compressor"
        weaker = end in ("occupancy", "load", "output") or excepted   # a schedule, an indirect measure
        return role, (int(weaker), rank, pos, int(msv), len(n)), state

    def component_rank(self, n):
        """Rank of the most specific component phrase in the name; 2 when none."""
        hits = [(length, rank) for length, rank, rx in self.components if rx.search(n)]
        if not hits:
            return 2
        longest = max(length for length, _ in hits)
        return max(rank for length, rank in hits if length == longest)

    def is_plant(self, point_names):
        """Whether any point reports a plant alarm or filter — plant whose running is not mapped."""
        return any(rx.search(normalise(n)[0]) for n in point_names for rx in self.marks_plant)

    def runs_around_the_clock(self, unit):
        """Whether the unit serves a space conditioned day and night, so running all week is its job."""
        if {unit["peak_type"], unit["type"]} & self.clock_codes:
            return True
        text = " ".join((unit.get(k) or "").lower() for k in ("name", "zone"))
        return any(rx.search(text) for rx in self.clock_words)

    def charted_type(self, equipment_name, peak_type):
        """The type a unit is drawn under: its name's, where Regrouped by name allows the pair.

        A name that names PEAK's own type anywhere keeps it ('CH AHU-12' is an
        AHU). Otherwise the first name word whose type may take PEAK's decides
        ('B2 FCU PLANT-ROOM' typed AHU is a fan coil); a location code such as the
        'CH' or 'EC' opening a name is passed over, since no row lets a chiller take
        an AHU or an evaporative cooler take a boiler.
        """
        words = [self.name_word(tok) for tok in name_tokens(equipment_name)]
        if peak_type in words:
            return peak_type
        return next((w for w in words if w and peak_type in self.regroup_from.get(w, ())), peak_type)

    def name_word(self, tok):
        """The type a name token means, if any: 'FCU', or 'KEF11' glued to its number."""
        code = self.by_word.get(tok)
        if not code:
            glued = re.fullmatch(r"([A-Z]+)\d+", tok)
            code = self.by_word.get(glued.group(1)) if glued else None
        return code


# ---- window ------------------------------------------------------------------
def load_site(path):
    try:
        rows = read_results(path)
        site = rows[0] if rows else None
    except ValueError:
        site = json.loads(Path(path).read_text())
    if not isinstance(site, dict) or "timezone" not in site:
        sys.exit(f"{path}: expected the search_sites result for one site, with timezone")
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
            hours.update({f"{key}Enabled": True, f"{key}Start": m["start"], f"{key}End": m["end"]})
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


def cmd_window(args):
    from zoneinfo import ZoneInfo           # stdlib from 3.9; needs the system tz database
    site = load_site(args.site)
    tz = ZoneInfo(site["timezone"])
    work = Path(args.workdir)
    work.mkdir(parents=True, exist_ok=True)

    today = date.fromisoformat(args.today) if args.today else datetime.now(tz).date()
    if args.week_of:
        ref = date.fromisoformat(args.week_of)
        monday = ref - timedelta(days=ref.weekday())
        if monday + timedelta(days=7) > today:
            sys.exit(f"the week of {args.week_of} has not finished in site local time")
    else:
        monday = today - timedelta(days=today.weekday() + 7)
    dates = [monday + timedelta(days=i) for i in range(7)]

    def utc(d):
        return datetime.combine(d, time(0), tzinfo=tz).astimezone(timezone.utc)

    start, end = utc(monday), utc(monday + timedelta(days=7))
    hours_source = site.get("hours_source", "site")
    if args.hours:
        site["working_hours"], hours_source = parse_hours(args.hours), "user"
    slots = working_slots(site.get("working_hours") or {})
    if not any(slots):
        sys.exit("working hours are empty (every day closed or 00:00). Ask the user what hours to "
                 'assess against and run window again with them, e.g. --hours "Mon-Fri 08:00-18:00, '
                 'Sat 09:00-13:00"; a day not named is closed.')

    names = sorted({datetime.combine(d, time(12), tzinfo=tz).tzname() for d in dates})
    link = re.match(r"https?://[^/]+", site.get("site_link") or "")
    include = [c.strip() for c in (args.include or "").split(",") if c.strip()]
    window = {
        "site_id": site["site_id"], "site_name": site["site_name"],
        "timezone": site["timezone"], "tz_label": "/".join(names),
        "hours_source": hours_source,
        "start": start.strftime("%Y-%m-%dT%H:%M:%SZ"), "end": end.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "link_start": start.strftime("%Y-%m-%dT%H:%M:%S.000"),
        "link_end": end.strftime("%Y-%m-%dT%H:%M:%S.000"),
        "link_host": link.group(0) if link else DEFAULT_HOST,
        "label": week_label(dates),
        "days": [{"date": d.isoformat(), "label": f"{DAY_ABBR[i]} {d.day}", "wh": slots[i]}
                 for i, d in enumerate(dates)],
        "include": include,
    }
    (work / "window.json").write_text(json.dumps(window, indent=1))

    rules = Rules()
    charted = list(rules.types) + [c for c in include if c not in rules.types]
    known = charted + sorted(c for c in rules.never_charted if c not in charted)
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
    # Two counts: every unit, and units of a type the tables know. Equal counts mean
    # no unit is of a type PEAK added after the tables were written.
    census = [{"query_name": "platform.equipment",
               "args": {"site_id": site["site_id"], "is_active": True, **extra, "limit": 1},
               "fields": ["equipment_id"]}
              for extra in ({}, {"metadata_type_codes": known})]
    print(f"{site['site_name']}: {window['label']} ({window['tz_label']}), "
          f"{window['start']} to {window['end']} UTC. Wrote {work / 'window.json'}.")
    print("Three calls, in parallel, each exactly as printed. Save the responses in "
          f"{work} under the names given.")
    print(f"Discovery -> discovery-0.json. Where its pagination.total is over {DISCOVERY_LIMIT}, "
          f"make the same call again for each further page, in parallel, with start_index "
          f"{DISCOVERY_LIMIT}, {2 * DISCOVERY_LIMIT}, ... -> discovery-{DISCOVERY_LIMIT}.json, "
          f"discovery-{2 * DISCOVERY_LIMIT}.json, ...:")
    print(json.dumps(discovery))
    for name, call in zip(("census-all.json", "census-known.json"), census):
        print(f"Census count -> {name}:")
        print(json.dumps(call))


# ---- plan --------------------------------------------------------------------
def _number(tok):
    """(word, unit number) of a name token: 'P01A' -> ('P', '1A'), '10' -> ('', '10'), 'CHWP' -> ('CHWP', None)."""
    m = NUMBERED.fullmatch(tok)
    return (m.group(1), m.group(2) + m.group(3)) if m else (tok, None)


def pair_members(unit):
    """(name words, member numbers) for a COMMON record that names the units it pairs, else None.

    'Common - PCHWP - 3/4', 'SHWP P-10A/B - COMMON', 'AHU-CHWP-10-11-COMMON' and
    'PUMP-10&11-COMMON' all do. Only bare numbers count: 'VRV-L11-COMMON' is a
    level's group and 'EWH-COMMON' names no units, so neither is a pair.
    """
    tokens = name_tokens(unit["name"])
    if "COMMON" not in tokens:
        return None
    words, numbers, last = set(), set(), None
    for tok in (t for t in tokens if t != "COMMON"):
        word, number = _number(tok)
        if number is not None and not word:
            numbers.add(number)
            last = number
        elif len(tok) == 1 and last and last[-1].isalpha():
            numbers.add(last[:-1] + tok)                       # '10A/B': B is 10B
        else:
            words.add(word)
    return (words, numbers) if numbers else None


def member_of(unit, words, numbers):
    """Whether a unit is one of the pair: every word of the pair's name, and a number it lists."""
    own, number = set(), None
    for tok in name_tokens(unit["name"]):
        word, num = _number(tok)
        if word:
            own.add(word)
        if num is not None:
            number = num
    return number in numbers and words <= own


def signal_grade(unit):
    """1 for a status or analog, 0 for a compressor status alone."""
    return 1 if {p["role"] for p in unit["pull"]} & {"status", "analog"} else 0


def read_units(paths):
    """Discovered units with their points, de-duplicated across pages.

    Reads the equipment-rooted discovery (points nested under each unit) and, for
    older saved runs, the point-per-row pages of platform.favourites.
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
        for row in read_results(path):
            if "favourites" in row:
                unit = unit_for(row["equipment_id"], row)
                points = row.get("favourites") or []
            else:
                unit, points = unit_for(row["equipment_id"], row.get("equipment") or {}), [row]
            for p in points:
                if p.get("is_active") is False or p.get("fav_id") in seen:
                    continue
                seen.add(p.get("fav_id"))
                unit["points"].append(p)
    return list(units.values())


def read_census(paths):
    """(units per type, type names, units of an unknown type) from the saved census.

    A full census — every unit's type, as older runs saved it — is counted
    by type and names any unknown type. The MCP's two counts — every
    unit, and units of a type the tables know, each a pagination.total — give
    only how many units are of an unknown type, the difference.
    """
    counts, names, totals = Counter(), {}, []
    for path in paths or []:
        rows, total = read_page(path)
        if rows and isinstance(rows[0], dict) and "metadata_type" in rows[0]:
            for row in rows:
                mt = row.get("metadata_type") or {}
                counts[mt.get("type_code")] += 1
                names[mt.get("type_code")] = mt.get("type")
        elif total is not None:
            totals.append(int(total))
        elif rows:
            raise ValueError(f"{path}: a census response with neither unit types nor a count")
    if totals and len(totals) != 2:
        raise ValueError("pass both census counts, every unit and units of a known type")
    return counts, names, (max(totals) - min(totals)) if totals else None


SENSOR_ROLES = ("status", "analog", "compressor")   # a reading of the unit; a command is not


def pick_points(unit, rules):
    """The points to pull for one unit: its status and analog, else a compressor status.

    Only sensors draw a row. An enable, command or occupancy schedule says what the
    unit was told to do, not that it ran, so a unit with nothing else is left off
    the chart and named in the notes.
    """
    found = {role: [] for role in ROLE_ORDER}
    for p in unit["points"]:
        name = (p.get("metadata") or {}).get("name") or ""
        hit = rules.classify(name, unit["type"])
        if hit:
            role, key, state = hit
            found[role].append({"fav_id": p["fav_id"], "name": name, "role": role, "key": key,
                                "state": state, "live": bool(p.get("history_available"))})
    best = {}
    for role, cands in found.items():
        cands.sort(key=lambda c: (c["key"], c["fav_id"]))
        best[role] = next((c for c in cands if c["live"]), None)
    pull = [best[r] for r in ("status", "analog") if best[r]] or ([best["compressor"]] if best["compressor"] else [])
    unit["pull"] = [dict({k: c[k] for k in ("fav_id", "name", "role")}, **({"state": True} if c["state"] else {}))
                    for c in pull]
    if pull:
        return
    sensors = [c for r in SENSOR_ROLES for c in found[r]]
    if sensors:
        unit["why"] = "no history this week"
        best = min(sensors, key=lambda c: (c["key"], c["fav_id"]))
        unit["probe"] = {"fav_id": best["fav_id"], "unit": unit["name"], "point": best["name"]}
    elif not unit["points"]:
        unit["why"] = "no points"
    elif "COMMON" in name_tokens(unit["name"]):
        unit["why"] = "shared record"
    elif found["command"]:
        unit["why"] = "command only"
    elif rules.is_plant((p.get("metadata") or {}).get("name") or "" for p in unit["points"]):
        unit["why"] = "alarms only"
    else:
        unit["why"] = "sensors or setpoints only"


def drop_covered_pairs(units):
    """Drop a COMMON pair record where a member is drawn from a signal at least as good.

    Kept where the pair is the only record of the pumps running: a pair status
    beside members that carry only enables, which are not drawn.
    """
    for unit in units:
        pair = pair_members(unit)
        if pair and unit["pull"] and any(
                other is not unit and other["type"] == unit["type"] and other["pull"]
                and not pair_members(other) and member_of(other, *pair)
                and signal_grade(other) >= signal_grade(unit)
                for other in units):
            unit["why"], unit["pull"] = "pair point, members charted", []


def assign_passes(units, cap):
    """Central plant in the first pass whole; each field type whole where it still fits under cap.

    A type too big to fit waits for the later pass without holding back the
    smaller types after it; while the first pass is still empty, the next type
    goes in whatever its size, so there is always a first view.
    """
    count = sum(1 for u in units if u["pull"] and u["page"] == "Central plant")
    for u in units:
        u["pass"] = 1
    for type_code in dict.fromkeys(u["type"] for u in units if u["page"] != "Central plant"):
        group = [u for u in units if u["type"] == type_code]
        size = sum(1 for u in group if u["pull"])
        fits = cap is None or count == 0 or count + size <= cap
        for u in group:
            u["pass"] = 1 if fits else 2
        count += size if fits else 0


def cmd_plan(args):
    work = Path(args.workdir)
    window = json.loads((work / "window.json").read_text())
    rules = Rules()
    include = set(window.get("include") or [])
    census, census_names, unknown_units = read_census(args.census)

    units, unknown = [], Counter()
    for unit in read_units(args.discovery):
        peak = unit["peak_type"]
        if peak not in rules.types and peak not in include:
            unknown[peak] += 1
            continue
        unit["type"] = rules.charted_type(unit["name"], peak) if peak in rules.types else peak
        ty = rules.types.get(unit["type"])
        unit["type_name"] = ty["name"] if ty else census_names.get(peak, peak)
        unit["page"] = ty["page"] if ty else "Other"
        if unit["type"] != peak:
            unit["regrouped_from"] = rules.types[peak]["name"]
        unit["around_the_clock"] = rules.runs_around_the_clock(unit)
        pick_points(unit, rules)
        units.append(unit)
    drop_covered_pairs(units)

    def order(u):
        ty = rules.types.get(u["type"])
        return (PAGE_ORDER.index(u["page"]), ty["order"] if ty else 999, u["type_name"],
                natural(u["level"]), natural(u["name"]))

    units.sort(key=order)
    assign_passes(units, args.cap if args.cap and args.cap > 0 else None)
    chunks = []
    for pass_no in (1, 2):
        favs = [p["fav_id"] for u in units if u["pass"] == pass_no for p in u["pull"]]
        chunks += [{"pass": pass_no, "fav_ids": favs[i:i + POINTS_PER_CALL]}
                   for i in range(0, len(favs), POINTS_PER_CALL)]

    # Types in neither table: named in the notes, so a new PEAK type is a visible gap.
    known = set(rules.types) | rules.never_charted | include | {None}
    unclassified = Counter({c: n for c, n in (census or unknown).items() if c not in known})
    dead = [u for u in units if u.get("why") == "no history this week"]
    plan = {
        "units": [{k: u.get(k) for k in ("equipment_id", "name", "type", "type_name", "page",
                                          "level", "zone", "regrouped_from", "around_the_clock",
                                          "pass", "pull", "why")}
                  for u in units],
        "chunks": chunks,
        "unclassified": [{"code": c, "type": census_names.get(c, c), "units": n}
                         for c, n in unclassified.most_common()],
        "unknown_units": unknown_units or 0,
        "outage": bool(dead) and not any(u["pull"] for u in units),
        "probe": probe_points(dead) if dead and not chunks else [],
    }
    (work / "plan.json").write_text(json.dumps(plan, indent=1))
    print(f"{window['site_name']}: {window['label']}. Wrote {work / 'plan.json'}.")
    print_summary(plan)
    if not chunks:
        print_nothing_to_draw(window, plan, dead, work)
        return
    print_calls(window, plan, 1, work)


def probe_points(dead):
    """Up to PROBE_POINTS of the units' best points, taken a type at a time so every type is asked."""
    by_type = {}
    for u in dead:
        by_type.setdefault(u["type"], []).append(u["probe"])
    out, queues = [], list(by_type.values())
    while queues and len(out) < PROBE_POINTS:
        out += [q.pop(0) for q in queues][:PROBE_POINTS - len(out)]
        queues = [q for q in queues if q]
    return out


WHY_TEXT = {"no history this week": "a run point, but no history this week",
            "command only": "only an enable, command or schedule, no sensor",
            "alarms only": "plant alarms or filters but no run point",
            "sensors or setpoints only": "only sensors, setpoints or dampers",
            "shared record": "a COMMON record with no sensor of its own",
            "no points": "no points in PEAK",
            "pair point, members charted": "a COMMON pair record whose members are drawn"}


def print_summary(plan):
    for pass_no, label in ((1, "First pass"), (2, "Later pass")):
        drawn = [u for u in plan["units"] if u["pull"] and u["pass"] == pass_no]
        if not drawn:
            continue
        types = Counter(u["type_name"] for u in drawn)
        calls = sum(1 for c in plan["chunks"] if c["pass"] == pass_no)
        points = sum(len(u["pull"]) for u in drawn)
        detail = (": " + ", ".join(f"{t} {n}" for t, n in types.items())) if pass_no == 2 else ""
        print(f"{label}: {plural(len(drawn), 'unit')} in {plural(len(types), 'type')}, "
              f"{plural(points, 'point')}, {plural(calls, 'history call')}{detail}.")
    for why, n in Counter(u["why"] for u in plan["units"] if not u["pull"]).items():
        print(f"Not drawn: {plural(n, 'unit')}, {WHY_TEXT.get(why, why)}.")
    regrouped = Counter(f"{u['regrouped_from']} as {u['type_name']}"
                        for u in plan["units"] if u["regrouped_from"] and u["pull"])
    if regrouped:
        print("Regrouped by name: " + ", ".join(f"{k} {n}" for k, n in regrouped.items()) + ".")
    if plan["unclassified"]:
        print("Unclassified types at this site: "
              + ", ".join(f"{u['type']} ({u['code']}) {u['units']}" for u in plan["unclassified"]))
    if plan["unknown_units"]:
        print(f"Unclassified: {plural(plan['unknown_units'], 'unit')} of a type neither table in "
              "run-hours-signals.md covers.")


def history_call(args):
    return {"query_name": "platform.history", "args": args, "fields": HISTORY_FIELDS}


def print_nothing_to_draw(window, plan, dead, work):
    if plan["outage"]:
        print(f"Nothing to draw: none of the {plural(len(dead), 'unit')} with a run point logged any "
              f"history from {window['start']} to {window['end']}, so the site's data feed looks down. "
              "Say so rather than showing an empty view. To say since when, make this call exactly as "
              f"printed: it returns one row, the newest reading of any of these "
              f"{plural(len(plan['probe']), 'point')}. Save it as {work / 'last-reading.json'}, then run "
              f"runhours_plan.py last {work} {work / 'last-reading.json'}")
        print(json.dumps(history_call({"fav_ids": [p["fav_id"] for p in plan["probe"]], "latest": True})))
    else:
        print("Nothing to draw: no plant at the site carries a usable run point. Say so with the "
              "summary above rather than showing an empty view.")


def print_calls(window, plan, pass_no, work):
    chunks = [c for c in plan["chunks"] if c["pass"] == pass_no]
    label = "first pass" if pass_no == 1 else "later pass"
    if not chunks:
        print(f"No history calls for the {label}: every unit with a run point is in the other pass.")
        return
    names = f"history-{pass_no}-1.json" + (f" to history-{pass_no}-{len(chunks)}.json" if len(chunks) > 1 else "")
    print(f"History calls, {label}: {len(chunks)}. Make each exactly as printed, in parallel, and save "
          f"the responses in {work} as {names}, in the order printed:")
    for chunk in chunks:
        print(json.dumps(history_call({"fav_ids": chunk["fav_ids"], "start": window["start"],
                                       "end": window["end"], "end_exclusive": True})))


def cmd_calls(args):
    work = Path(args.workdir)
    window = json.loads((work / "window.json").read_text())
    print_calls(window, json.loads((work / "plan.json").read_text()), args.pass_no, work)


def cmd_last(args):
    """When the site last reported: the newest reading of the points the plan probed."""
    from zoneinfo import ZoneInfo           # stdlib from 3.9; needs the system tz database
    work = Path(args.workdir)
    window = json.loads((work / "window.json").read_text())
    probe = {str(p["fav_id"]): p for p in json.loads((work / "plan.json").read_text()).get("probe") or []}
    if not probe:
        raise ValueError("plan.json has no probe: the last step follows a plan with nothing to draw")
    rows = [r for r in read_results(args.response) if str(r.get("fav_id")) in probe and r.get("ts")]
    if not rows:
        print(f"None of the {plural(len(probe), 'point')} asked has a reading in PEAK's history at all: "
              "the site's points have never reported, or their history is not reaching PEAK. Say so.")
        return
    newest = max(rows, key=lambda r: datetime.fromisoformat(str(r["ts"]).replace("Z", "+00:00")))
    local = datetime.fromisoformat(str(newest["ts"]).replace("Z", "+00:00")).astimezone(
        ZoneInfo(window["timezone"]))
    p = probe[str(newest["fav_id"])]
    print(f"The site's run points last reported {local:%a} {local.day} {local:%b %Y %H:%M} {local.tzname()}, "
          f"the newest reading of the {plural(len(probe), 'point')} sampled across its types "
          f"({p['unit']}, {p['point']}). Say its data feed has been down since then, and that there is "
          f"no run-hours view for {window['label']}.")


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    w = sub.add_parser("window", help="fix the week and print the discovery calls")
    w.add_argument("site", help="saved search_sites result for the site")
    w.add_argument("workdir")
    w.add_argument("--week-of", help="any date in the Monday-to-Sunday week to show")
    w.add_argument("--include", help="never-charted type codes the user asked for, e.g. LT")
    w.add_argument("--hours", help='the user\'s working hours, e.g. "Mon-Fri 08:00-18:00, Sat 09:00-13:00"; '
                                   "a day not named is closed")
    w.add_argument("--today", help=argparse.SUPPRESS)
    p = sub.add_parser("plan", help="pick points and passes from the discovery pages")
    p.add_argument("workdir")
    p.add_argument("discovery", nargs="+", help="saved discovery pages")
    p.add_argument("--census", nargs="+", action="extend",
                   help="the two saved census counts, or a full census")
    p.add_argument("--cap", type=int, default=CAP_UNITS,
                   help=f"first-pass units (default {CAP_UNITS}; 0 fetches everything)")
    c = sub.add_parser("calls", help="print the history calls for one pass of an existing plan")
    c.add_argument("workdir")
    c.add_argument("--pass", dest="pass_no", type=int, default=2)
    last = sub.add_parser("last", help="say when the site last reported, from the saved latest-reading call")
    last.add_argument("workdir")
    last.add_argument("response", help="saved response of the latest-reading call")
    args = parser.parse_args(argv[1:])
    try:
        {"window": cmd_window, "plan": cmd_plan, "calls": cmd_calls, "last": cmd_last}[args.command](args)
    except (ValueError, KeyError) as exc:
        sys.exit(f"runhours_plan: {exc}")


if __name__ == "__main__":
    main(sys.argv)
