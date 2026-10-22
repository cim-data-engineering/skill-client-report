#!/usr/bin/env python3
"""Plan a run-hours pull: which week, which points, and in what order. run_hours.py calls
these functions; the command line runs the same steps and prints what they decided.

    python3 runhours_plan.py window <site.json> <workdir> [--site-id N] [--week-of YYYY-MM-DD] [--include LT,...]
                                    [--hours "Mon-Fri 08:00-18:00, Sat 09:00-13:00"]
    python3 runhours_plan.py plan <workdir> <discovery.json> [more.json ...] [--census census.json ...] [--cap N]
    python3 runhours_plan.py last <workdir> <last-reading.json>

window  Fixes the last full Monday-to-Sunday week in site local time from the saved
        search_sites result, writes <workdir>/window.json, and gives the discovery and
        census calls. --hours assesses against the user's hours instead of the site's.
plan    Sorts every discovered point with the rules in
        references/single-site/run-hours/run-hours-signals.md, picks each unit's
        points, orders the units for the view, splits them into a first pass of up
        to --cap units and the rest, and writes <workdir>/plan.json.
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
CAP_UNITS       = 100    # first-pass size; central plant is always fetched whole
POINTS_PER_CALL = 36     # ~672 rows per point-week keeps a call under ~25k rows / ~2 MB
DISCOVERY_LIMIT = 1000   # units per discovery page: ~170 KB for a 100-unit office tower
PROBE_POINTS    = 20     # points asked for their latest reading before the week, a type at a
                         # time, to find when the site's data stopped
HISTORY_FIELDS  = ["fav_id", "ts", "data"]
PAGE_ORDER      = ["Central plant", "Field units", "Other"]
ROLE_ORDER      = ["status", "analog", "command", "compressor"]
TRAILING_UNITS  = {"%", "percent", "w", "kw", "v", "a", "msv"}
DAY_KEYS        = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
DAY_ABBR        = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
NUMBERED        = re.compile(r"([A-Z]*)0*(\d+)([A-Z]*)")    # 'P01A' -> P, 1, A; '10' -> '', 10, ''


# ---- Reference tables ---------------------------------------------------------
# The columns each parsed table must carry. A table may carry more; the rules read only these.
SCHEMA = {
    "Equipment types": ["Page", "System", "Code", "Equipment type", "Name word", "Compressor is the unit",
                        "Heating is the unit", "Also never"],
    "Regrouped by name": ["Code", "Takes units PEAK types as"],
    "Never charted": ["Codes"],
    "Roles": ["Role", "Name ends with, best first"],
    "Never a run signal": ["Name contains", "Except where", "Marks plant"],
    "Which point wins": ["Rank", "Component named"],
    "Runs around the clock": ["Codes", "Name or zone contains"],
}
FLAGS = ("Compressor is the unit", "Heating is the unit")
ENDINGS = {"load", "output", "occupancy"}        # endings the rules treat specially, so Roles must list them


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


def _flag(cell, where):
    cell = (cell or "").strip().lower()
    if cell not in ("", "yes"):
        raise TableError(f"{where}: a flag cell holds yes or nothing, not '{cell}'")
    return cell == "yes"


def _cells(line):
    return [c.strip().strip("`").strip() for c in line.strip().strip("|").split("|")]


def _split(cell):
    return [p.strip() for p in (cell or "").split(",") if p.strip()]


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
    """The tables of references/single-site/run-hours/run-hours-signals.md, checked and ready to classify with."""

    def __init__(self, path=SIGNALS):
        tables = read_tables(path)
        name = Path(path).name
        at = lambda row: f"{name}:{row['_line']}"
        self.types = {}
        for order, row in enumerate(tables["Equipment types"]):
            if row["Code"] in self.types:
                raise TableError(f"{at(row)}: the code {row['Code']} is already an equipment type")
            if row["Page"] not in PAGE_ORDER:
                raise TableError(f"{at(row)}: Page is one of {', '.join(PAGE_ORDER)}, not '{row['Page']}'")
            self.types[row["Code"]] = {
                "code": row["Code"], "name": row["Equipment type"], "order": order,
                "page": row["Page"], "system": row["System"],
                "words": [p.upper() for p in _split(row["Name word"])],
                "flags": {col for col in FLAGS if _flag(row[col], at(row))},
                "also_never": [_phrase(p) for p in _split(row["Also never"])],
            }
        self.regroup_from = {row["Code"]: set(_split(row["Takes units PEAK types as"]))
                             for row in tables["Regrouped by name"]}
        self.never_charted = {c for row in tables["Never charted"] for c in _split(row["Codes"])}
        self.endings = {row["Role"]: [e.lower() for e in _split(row["Name ends with, best first"])]
                        for row in tables["Roles"]}
        missing = ENDINGS - {e for ends in self.endings.values() for e in ends}
        if missing:
            raise TableError(f"{name}: the Roles table no longer lists the ending '{sorted(missing)[0]}'")
        self.never, self.marks_plant = [], []
        for row in tables["Never a run signal"]:
            exempt = row["Except where"].strip() or None
            if exempt and exempt not in FLAGS:
                raise TableError(f"{at(row)}: 'Except where' names no Equipment types flag column: {exempt}")
            for p in _split(row["Name contains"]):
                self.never.append((_phrase(p), exempt))
                if _flag(row["Marks plant"], at(row)):
                    self.marks_plant.append(_phrase(p))
        self.components, self.unit_rank = [], None
        for row in tables["Which point wins"]:
            if not row["Rank"].isdigit():
                raise TableError(f"{at(row)}: Rank is a whole number, not '{row['Rank']}'")
            names = _split(row["Component named"])
            if names and names[0].startswith("("):
                self.unit_rank = int(row["Rank"])       # (none: the unit itself)
                continue
            self.components += [(len(p), int(row["Rank"]), _phrase(p)) for p in names]
        if self.unit_rank is None:
            raise TableError(f"{name}: the 'Which point wins' table has no '(none ...)' row for the unit itself")
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
        if end in ("load", "output") and rank != self.unit_rank:
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
        """Rank of the most specific component phrase in the name; the unit's own rank when none."""
        hits = [(length, rank) for length, rank, rx in self.components if rx.search(n)]
        if not hits:
            return self.unit_rank
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


def make_window(site_path, workdir, site_id=None, today=None, week_of=None, hours=None, include=""):
    """Fix the week in site local time, write <workdir>/window.json, and return (window, calls): the
    discovery call, then the two census counts, each {file, query_name, args, fields}."""
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

    names = sorted({datetime.combine(d, time(12), tzinfo=tz).tzname() for d in dates})
    include = [c.strip() for c in (include or "").split(",") if c.strip()]
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
    return window, [dict(discovery, file="discovery-0.json")] + [
        dict(call, file=f) for f, call in zip(("census-all.json", "census-known.json"), census)]


def cmd_window(args):
    window, calls = make_window(args.site, args.workdir, args.site_id, args.today, args.week_of, args.hours,
                                args.include)
    print(f"{window['site_name']}: {window['label']} ({window['tz_label']}), "
          f"{window['start']} to {window['end']} UTC. Wrote {Path(args.workdir) / 'window.json'}.")
    for c in calls:
        print(f"{c['file']}: " + json.dumps({k: v for k, v in c.items() if k != "file"}))


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


def read_census(paths):
    """Units of a type neither table covers, from the two saved census counts.

    The counts are every unit and units of a type the tables know, each a
    pagination.total; their difference is the units of an unknown type. None
    without a census.
    """
    totals = []
    for path in paths or []:
        rows, total = read_page(path)
        if total is not None:
            totals.append(int(total))
        elif rows:
            raise ValueError(f"{path}: a census response with no count")
    if totals and len(totals) != 2:
        raise ValueError("pass both census counts, every unit and units of a known type")
    return (max(totals) - min(totals)) if totals else None


SENSOR_ROLES = ("status", "analog", "compressor")   # a reading of the unit; a command is not


def _shared(units, what):
    n = len(units)
    return f"{n} {what[0]}{'s carry' if n != 1 else ' carries'} {what[1].format(their='their' if n != 1 else 'its')}"


# Why a unit is left off the chart, in the order the notes give them: the key the plan records, what the
# plan's summary says, and the note naming the units, written from (units, listing, by_type).
REASONS = [
    ("command only", "only an enable, command or schedule, no sensor",
     lambda us, ls, bt: "Only an enable, command or schedule, with no sensor to show the unit ran, not drawn: "
                        f"{ls(u['name'] for u in us)} ({bt(us)})."),
    ("alarms only", "plant alarms or filters but no run point",
     lambda us, ls, bt: f"Plant with alarms but no run point, not drawn: {ls(u['name'] for u in us)} ({bt(us)})."),
    ("no history this week", "a run point, but no history this week",
     lambda us, ls, bt: f"No history this week, not drawn: {ls(u['name'] for u in us)}."),
    ("pair point, members charted", "a COMMON pair record whose members are drawn",
     lambda us, ls, bt: f"Left out because their member units are shown: {ls(u['name'] for u in us)}."),
    ("no points", "no points in PEAK",
     lambda us, ls, bt: f"No points in PEAK, not drawn: {ls(u['name'] for u in us)} ({bt(us)})."),
    ("shared record", "a COMMON record with no sensor of its own",
     lambda us, ls, bt: _shared(us, ("shared COMMON record", "no sensor of {their} own"))
                        + f", not drawn ({bt(us)})."),
    ("sensors or setpoints only", "only sensors, setpoints or dampers",
     lambda us, ls, bt: _shared(us, ("record", "only sensors, setpoints or dampers"))
                        + f", not drawn ({bt(us)}), e.g. {', '.join(u['name'] for u in us[:3])}."),
]
WHY = {key: summary for key, summary, _ in REASONS}


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
        unit["probe"] = {"fav_id": pull[0]["fav_id"], "unit": unit["name"], "point": pull[0]["name"]}
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


def make_plan(workdir, discovery, census=None, cap=CAP_UNITS):
    """Pick every unit's points and passes from the saved discovery pages, write <workdir>/plan.json and
    return the plan."""
    work = Path(workdir)
    window = json.loads((work / "window.json").read_text())
    rules = Rules()
    include = set(window.get("include") or [])
    unknown_units = read_census(census)

    units = []
    for unit in read_units(discovery):
        peak = unit["peak_type"]
        if peak not in rules.types and peak not in include:
            continue                      # discovery asks only for the charted and included types
        unit["type"] = rules.charted_type(unit["name"], peak) if peak in rules.types else peak
        ty = rules.types.get(unit["type"])
        unit["type_name"] = ty["name"] if ty else peak
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
    assign_passes(units, cap if cap and cap > 0 else None)
    chunks = []
    for pass_no in (1, 2):
        favs = [p["fav_id"] for u in units if u["pass"] == pass_no for p in u["pull"]]
        chunks += [{"pass": pass_no, "fav_ids": favs[i:i + POINTS_PER_CALL]}
                   for i in range(0, len(favs), POINTS_PER_CALL)]

    dead = [u for u in units if u.get("why") == "no history this week"]
    drawn = [u for u in units if u["pull"] and u["pass"] == 1]
    plan = {
        "units": [{k: u.get(k) for k in ("equipment_id", "name", "type", "type_name", "page",
                                          "level", "zone", "regrouped_from", "around_the_clock",
                                          "pass", "pull", "why")}
                  for u in units],
        "chunks": chunks,
        "unknown_units": unknown_units or 0,
        "outage": bool(dead) and not any(u["pull"] for u in units),
        "probe": probe_points(drawn if chunks else dead),
    }
    unknown = sorted({u["why"] for u in units if u.get("why")} - set(WHY))
    if unknown:
        raise ValueError(f"a unit left off the chart for '{unknown[0]}', which REASONS does not name")
    (work / "plan.json").write_text(json.dumps(plan, indent=1))
    return plan


def cmd_plan(args):
    plan = make_plan(args.workdir, args.discovery, args.census, args.cap)
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
    """What the plan decided, in sentences: the units drawn in each pass, and why the rest are not."""
    out = []
    for pass_no, label in ((1, "First pass"), (2, "Later pass")):
        drawn = [u for u in plan["units"] if u["pull"] and u["pass"] == pass_no]
        if not drawn:
            continue
        types = Counter(u["type_name"] for u in drawn)
        calls = sum(1 for c in plan["chunks"] if c["pass"] == pass_no)
        points = sum(len(u["pull"]) for u in drawn)
        detail = (": " + ", ".join(f"{t} {n}" for t, n in types.items())) if pass_no == 2 else ""
        out.append(f"{label}: {plural(len(drawn), 'unit')} in {plural(len(types), 'type')}, "
                   f"{plural(points, 'point')}, {plural(calls, 'history call')}{detail}.")
    for why, n in Counter(u["why"] for u in plan["units"] if not u["pull"]).items():
        out.append(f"Not drawn: {plural(n, 'unit')}, {WHY[why]}.")
    regrouped = Counter(f"{u['regrouped_from']} as {u['type_name']}"
                        for u in plan["units"] if u["regrouped_from"] and u["pull"])
    if regrouped:
        out.append("Regrouped by name: " + ", ".join(f"{k} {n}" for k, n in regrouped.items()) + ".")
    if plan["unknown_units"]:
        out.append(f"Unclassified: {plural(plan['unknown_units'], 'unit')} of a type neither table in "
                   "run-hours-signals.md covers.")
    return out


def nothing_to_draw(plan):
    """Why a plan with no history call draws nothing."""
    if plan["outage"]:
        dead = sum(1 for u in plan["units"] if u.get("why") == "no history this week")
        return (f"none of the {plural(dead, 'unit')} with a run point logged any history this week, so the "
                "site's data feed looks down.")
    return "no plant at the site carries a usable run point."


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
        raise ValueError("plan.json has no probe: the plan found no unit with a run point")
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
    w.add_argument("--include", help="never-charted type codes the user asked for, e.g. LT")
    w.add_argument("--hours", help='the user\'s working hours, e.g. "Mon-Fri 08:00-18:00, Sat 09:00-13:00"; '
                                   "a day not named is closed")
    w.add_argument("--today", help=argparse.SUPPRESS)
    p = sub.add_parser("plan", help="pick points and passes from the discovery pages")
    p.add_argument("workdir")
    p.add_argument("discovery", nargs="+", help="saved discovery pages")
    p.add_argument("--census", nargs="+", action="extend",
                   help="the two saved census counts")
    p.add_argument("--cap", type=int, default=CAP_UNITS,
                   help=f"first-pass units (default {CAP_UNITS}; 0 fetches everything)")
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
