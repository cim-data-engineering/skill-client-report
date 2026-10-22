#!/usr/bin/env python3
"""Shared helpers for the report's scripts: saved PEAK responses, the report's
windows, and the dates and numbers every section prints the same way.

A PEAK response reaches a script only as a file you saved: an offloaded one
copied from the path the gateway handed back, an inline one written out
verbatim. The payload can arrive wrapped in an MCP text block, bare
({"results": [...], "pagination": {...}}) or as a bare list, so read() takes
all three. Standard library only, so the scripts run wherever the skill is
unpacked.
"""
import json
import os
import re
from datetime import date

MONTHS = ["January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]


# ── saved responses ─────────────────────────────────────────────────────────
class Response:
    """One saved call: its rows, pagination total, platform_link and has_more."""

    def __init__(self, payload):
        self.raw = payload
        self.total = self.link = None
        self.has_more = False
        obj = payload
        for _ in range(4):                       # shapes nest at most twice
            if isinstance(obj, list) and obj and isinstance(obj[0], dict) and "text" in obj[0]:
                obj = json.loads(obj[0]["text"])
                continue
            if isinstance(obj, dict) and "text" in obj and "results" not in obj:
                obj = json.loads(obj["text"])
                continue
            break
        if isinstance(obj, dict):
            if obj.get("errors") or obj.get("status") == "error":
                raise ValueError("the saved response is an error, not data: %.200s" % json.dumps(obj))
            pg = obj.get("pagination") or {}
            self.total, self.has_more = pg.get("total"), bool(pg.get("has_more"))
            self.link = obj.get("platform_link") or None
            obj = obj.get("results", [])
        self.rows = obj if isinstance(obj, list) else [obj]

    def first(self):
        return self.rows[0] if self.rows else None


def read(path):
    try:
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
    except OSError as e:
        raise SystemExit("missing response %s: make its call and save the response there (%s)" % (path, e))
    try:
        return Response(json.loads(text))
    except ValueError as e:
        raise SystemExit("%s is not a saved PEAK response: %s" % (path, e))


class Work:
    """The report's working directory: plan.json, and the responses under peak/."""

    def __init__(self, root):
        self.root = root
        self.peak = os.path.join(root, "peak")
        with open(os.path.join(root, "plan.json"), encoding="utf-8") as fh:
            self.ctx = json.load(fh)

    def path(self, name):
        return os.path.join(self.peak, name)

    def has(self, name):
        return os.path.isfile(self.path(name))

    def get(self, name):
        return read(self.path(name))


def drop_repeats(plan, files):
    """{pick: path} for each win's downloaded photos, less any whose bytes repeat an earlier one in the same
    win, deleted: one image uploaded to two tickets is one photo. plan is {win: [picks]}."""
    import hashlib
    for picks in plan.values():
        seen = set()
        for p in [p for p in picks if p in files]:
            with open(files[p], "rb") as fh:
                digest = hashlib.sha1(fh.read()).hexdigest()
            if digest in seen:
                os.remove(files.pop(p))
            seen.add(digest)
    return files


def call(file, tool, **args):
    """A call for the model to make: the PEAK tool, its arguments, and the file its
    response is saved as, under peak/."""
    return {"file": file, "tool": tool, "args": args}


def gql(file, query, args, fields):
    return call(file, "execute_graphql_query", query_name=query, args=args, fields=fields)


# The system equipment types: the platform checking itself, not plant. Every equipment and rule count leaves them out.
SYSTEM_TYPES = [21, 37, 69, 70, 87, 105, 114]


# ── who ranks ───────────────────────────────────────────────────────────────
# CIM's own system accounts, by PEAK user id: support, the API logins and the AI agents. Their actions
# count wherever work is measured, but they never rank as people. PEAK has no system-account flag.
SYSTEM_ACCOUNTS = {
    "4ddcfd76-f5f0-46f3-863a-2bf90ce22469": "CIM Support",
    "e28a4b09-a670-4954-823b-72e411e7cc2d": "CIM Engineering API",
    "d266f1a8-4822-4235-b174-aebce72328e8": "Engineering Read-Only CIM API User",
    "7ba072a9-ada6-4f2b-82d3-b86cbc71558c": "Agent Hannah Escalations",
    "ceb1f491-e901-4369-8708-2a38bbc4e9ea": "Agent Hana v1.0",
}
AGENT = re.compile(r"^\s*agent\b", re.I)          # the AI review agents, whatever company they sit under


def system_account(user_id, name=None):
    """True for an account that is CIM's system rather than a person: one of SYSTEM_ACCOUNTS, or an
    agent by name. Contractors' shared logins (a dispatch desk, a BMS controls account) rank."""
    return bool(user_id and str(user_id) in SYSTEM_ACCOUNTS) or bool(name and AGENT.match(name))


# ── time zones ──────────────────────────────────────────────────────────────
# Legacy IANA names PEAK still stores on some sites, each mapped to the zone it links to. Slim tzdata
# builds ship without the links, so ZoneInfo("Australia/Queensland") fails there.
LEGACY_ZONES = {
    "Australia/ACT": "Australia/Sydney", "Australia/Canberra": "Australia/Sydney",
    "Australia/NSW": "Australia/Sydney", "Australia/North": "Australia/Darwin",
    "Australia/Queensland": "Australia/Brisbane", "Australia/South": "Australia/Adelaide",
    "Australia/Tasmania": "Australia/Hobart", "Australia/Victoria": "Australia/Melbourne",
    "Australia/West": "Australia/Perth", "Australia/Yancowinna": "Australia/Broken_Hill",
    "Australia/LHI": "Australia/Lord_Howe",
    "US/Eastern": "America/New_York", "US/Central": "America/Chicago", "US/Mountain": "America/Denver",
    "US/Pacific": "America/Los_Angeles", "US/Arizona": "America/Phoenix", "US/Alaska": "America/Anchorage",
    "US/Hawaii": "Pacific/Honolulu", "US/East-Indiana": "America/Indiana/Indianapolis",
    "US/Michigan": "America/Detroit",
    "Canada/Eastern": "America/Toronto", "Canada/Central": "America/Winnipeg",
    "Canada/Mountain": "America/Edmonton", "Canada/Pacific": "America/Vancouver",
    "Canada/Atlantic": "America/Halifax", "Canada/Newfoundland": "America/St_Johns",
    "GB": "Europe/London", "GB-Eire": "Europe/London", "Eire": "Europe/Dublin", "NZ": "Pacific/Auckland",
    "Singapore": "Asia/Singapore", "Hongkong": "Asia/Hong_Kong", "PRC": "Asia/Shanghai", "Japan": "Asia/Tokyo",
    "Brazil/East": "America/Sao_Paulo",
}


def zone(name):
    """The ZoneInfo for a site's time zone, legacy names read as the zone they link to."""
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
    name = (name or "").strip() or "UTC"
    try:
        return ZoneInfo(LEGACY_ZONES.get(name, name))
    except (ZoneInfoNotFoundError, ValueError):
        raise SystemExit("unknown time zone %r on the site in PEAK: add it to LEGACY_ZONES in scripts/peak_io.py"
                         % name)


# ── windows ─────────────────────────────────────────────────────────────────
PART_MONTH_DAYS = 7          # complete days of today's month before it joins the windows


def add_months(d, n):
    m = d.year * 12 + d.month - 1 + n
    return date(m // 12, m % 12 + 1, 1)


def windows(today):
    """The report's windows from `today` (site local). The quarter is the three complete
    months before today's month, the trend window the six. Once more than a week of
    today's month has passed, that month to date joins both as their last month. Every
    bound is a month boundary, so the month to date is fetched up to the first of the
    next month and holds whatever exists so far."""
    first = date(today.year, today.month, 1)
    part = (today - first).days >= PART_MONTH_DAYS
    end = add_months(first, 1) if part else first     # exclusive
    months = lambda back: [add_months(first, i).isoformat() for i in range(-back, 1 if part else 0)]
    return {"today": today.isoformat(),
            "quarter": [add_months(first, -3).isoformat(), end.isoformat()],
            "trend": [add_months(first, -6).isoformat(), end.isoformat()],
            "quarter_months": months(3),
            "trend_months": months(6),
            "to_date": first.isoformat() if part else None,
            "through": (today if part else last_day(first.isoformat())).isoformat()}


def d(s):
    return date.fromisoformat(s[:10])


def last_day(start_excl_end):
    """The inclusive last day of a window whose end is exclusive."""
    e = d(start_excl_end)
    return date.fromordinal(e.toordinal() - 1)


def whole(ctx, months):
    """The complete months of a window's month list: all of them but the month to date."""
    return [m for m in months if m != ctx.get("to_date")]


def days_in(ctx, m):
    """Days a window month covers: all of it, or the month to date's days so far."""
    if m == ctx.get("to_date"):
        return d(ctx["through"]).day
    return (add_months(d(m), 1) - d(m)).days


def month_label(ctx, m):
    """'September', or 'October to date' for the month to date."""
    return month(m) + (" to date" if m == ctx.get("to_date") else "")


def and_to_date(ctx, lead=", and "):
    """', and October to date' when the windows carry a month to date, else ''."""
    m = ctx.get("to_date")
    if not m:
        return ""
    return "%s%s%s to date" % (lead, month(m), " %d" % d(m).year if d(m).month == 1 else "")


# ── formats ─────────────────────────────────────────────────────────────────
# the site's currency as PEAK names it (every MonetaryCurrencyEnum value): (code, labour rate per hour
# for the region, symbol). The symbol prints straight before the figure, so a code that reads as a word
# carries its own space.
CURRENCIES = {"australian dollar": ("AUD", 150, "$"), "us dollar": ("USD", 100, "$"),
              "united states dollar": ("USD", 100, "$"), "new zealand dollar": ("NZD", 150, "$"),
              "british pound": ("GBP", 75, "£"), "pound sterling": ("GBP", 75, "£"),
              "canadian dollar": ("CAD", 150, "$"), "euro": ("EUR", 100, "€"),
              "singapore dollar": ("SGD", 120, "S$"), "swiss franc": ("CHF", 120, "CHF "),
              "swedish krona": ("SEK", 900, "SEK "), "brazilian real": ("BRL", 250, "R$"),
              "chinese yuan": ("CNY", 300, "¥"), "indonesian rupiah": ("IDR", 500000, "Rp ")}


def currency(facts):
    """(code, labour rate per hour, symbol) for a site, from its site facts."""
    return CURRENCIES.get((facts.get("monetary_currency") or "").strip().lower(), ("USD", 100, "$"))


MIN_SAVING = 200           # a key win states a saving only from this much, in the site's currency


def small_saving(text):
    """True when a figure a win sets bold, "$67" or "$1.2k", is under MIN_SAVING."""
    m = re.search(r"(\d[\d,]*(?:\.\d+)?)\s*(k|thousand|m|million)?\b", text, re.I)
    scale = {"k": 1e3, "thousand": 1e3, "m": 1e6, "million": 1e6}.get((m.group(2) or "").lower(), 1) if m else 1
    return bool(m) and float(m.group(1).replace(",", "")) * scale < MIN_SAVING


WORKING_DAY = 7.5          # hours in the working day the labour model counts, every region


# ── building size ───────────────────────────────────────────────────────────
# PEAK stores every site's building size in square metres, US sites included. US sites show square feet,
# converted.
FEET = ("united states", "usa", "us", "united states of america")
SQFT_PER_SQM = 10.7639


def in_feet(country):
    """True where building sizes read in square feet: the United States."""
    return (country or "").strip().lower() in FEET


def area(m2, feet):
    """A PEAK building size (m²) in the unit the page shows: m² as stored, or square feet converted
    and rounded to the nearest 100 ft², the precision the stored figures were entered at."""
    if m2 is None:
        return None
    return round(m2 * SQFT_PER_SQM / 100) * 100 if feet else m2


def mon(s):
    """Column label for a month: 'Jul 26'."""
    m = d(s)
    return "%s %02d" % (MONTHS[m.month - 1][:3], m.year % 100)


def month(s):
    return MONTHS[d(s).month - 1]


def span(first, last, short=False, sep=" – "):
    """'July – September 2026', or across a year 'December 2025 – February 2026'.
    Chart descriptions pass sep=" to ", which reads aloud the way it is meant."""
    a, b = d(first), d(last)
    n = (lambda m: MONTHS[m - 1][:3]) if short else (lambda m: MONTHS[m - 1])
    if a.year == b.year:
        return "%s%s%s %d" % (n(a.month), sep, n(b.month), b.year)
    return "%s %d%s%s %d" % (n(a.month), a.year, sep, n(b.month), b.year)


def day_long(s):
    x = d(s)
    return "%d %s %d" % (x.day, MONTHS[x.month - 1], x.year)


def local_day(ts, tz):
    """A PEAK UTC timestamp as the site's own date, 'YYYY-MM-DD'."""
    from datetime import datetime
    return datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(zone(tz)).date().isoformat()


def day_short(s):
    x = d(s)
    return "%d %s %d" % (x.day, MONTHS[x.month - 1][:3], x.year)


def period(first, last_incl, short=False):
    """'1 July – 30 September 2026' (short: '1 Jul – 30 Sep 2026')."""
    a, b = d(first), d(last_incl)
    n = (lambda m: MONTHS[m - 1][:3]) if short else (lambda m: MONTHS[m - 1])
    if a.year == b.year:
        return "%d %s – %d %s %d" % (a.day, n(a.month), b.day, n(b.month), b.year)
    return "%d %s %d – %d %s %d" % (a.day, n(a.month), a.year, b.day, n(b.month), b.year)


def compact(n, dp=2):
    """1834812 -> '1.83M', 7340 -> '7.3k'."""
    if n >= 1e6:
        return "%.*fM" % (dp, n / 1e6)
    if n >= 1e3:
        return "%.1fk" % (n / 1e3)
    return "%d" % n


def words(n, dp=2):
    """1834812 -> '1.83 million', for running text."""
    if n >= 1e6:
        return "%.*f million" % (dp, n / 1e6)
    return "{:,}".format(int(round(n)))


def listing(items):
    """'a', 'a and b', 'a, b and c'."""
    items = list(items)
    if len(items) < 2:
        return "".join(items)
    return ", ".join(items[:-1]) + " and " + items[-1]


def pct(score, dp):
    """A PEAK 0-1 score as a percentage rounded for display."""
    return round(score * 100, dp)


# ── charts and rows shared by the sections ──────────────────────────────────
def thresholds(values, bands):
    """The two benchmark lines Chart 1 draws: one either side where the series sits
    inside a band, otherwise the threshold it crosses plus the next one out."""
    lo, hi = min(values), max(values)
    ts = sorted(bands, key=lambda b: -b[0])
    crossed = [b for b in ts if lo < b[0] <= hi]
    if len(crossed) >= 2:
        pick = crossed[:2]
    elif crossed:
        c = crossed[0]
        i = ts.index(c)
        nb = [ts[j] for j in (i - 1, i + 1) if 0 <= j < len(ts)]
        nb.sort(key=lambda b: min(abs(b[0] - lo), abs(b[0] - hi)))
        pick = [c] + nb[:1]
    else:
        above = [b for b in ts if b[0] > hi]
        below = [b for b in ts if b[0] <= lo]
        pick = above[-1:] + below[:1]
        if len(pick) < 2:
            pick = sorted(ts, key=lambda b: min(abs(b[0] - lo), abs(b[0] - hi)))[:2]
    return [[float(t), label] for t, label in sorted(pick, key=lambda b: -b[0])]


def to_date_note(ctx, months):
    """' October is to date.' for a chart description whose last month is the month to date."""
    return " %s is to date." % month(months[-1]) if months and months[-1] == ctx.get("to_date") else ""


def line_alt(ctx, what, months, values, th, dp):
    vals = ["%.*f" % (dp, v) for v in values]
    head = "Line chart of monthly %s, %s: %s and %s percent" % (
        what, span(months[0], months[-1], sep=" to "), ", ".join(vals[:-1]), vals[-1])
    (t1, l1), (t2, l2) = th[0], th[-1]
    return (head + ", against the %.1f percent %s threshold and the %.1f percent %s threshold." % (t2, l2, t1, l1)
            + to_date_note(ctx, months))


def movement(first, last, dp, m0, m1, unit="pp"):
    c = round(last - first, dp)
    if c == 0:
        return None, "Steady at %.*f%% from %s to %s." % (dp, last, m0, m1)
    return ({"dir": "up" if c > 0 else "down", "amount": "%.*f %s" % (dp, abs(c), unit)},
            "from %.*f%% in %s to %.*f%% in %s." % (dp, first, m0, dp, last, m1))
