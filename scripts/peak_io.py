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
import base64
import http.client
import json
import os
import re
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone

MONTHS = ["January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]


# ── saved responses ─────────────────────────────────────────────────────────
class PeakRefusal(ValueError):
    """A saved response that is PEAK's error rather than data."""


def text_block(obj):
    """True for an MCP text block, {"type": "text", "text": "..."}, as against a row that holds a text field."""
    return isinstance(obj, dict) and isinstance(obj.get("text"), str) and (
        obj.get("type") == "text" or set(obj) == {"text"})


class Response:
    """One saved call: its rows, pagination total, platform_link and has_more. Raises PeakRefusal
    for an error saved as data, and ValueError for text that does not parse."""

    def __init__(self, payload):
        self.raw = payload
        self.total = self.link = None
        self.has_more = False
        obj = payload
        for _ in range(4):                       # shapes nest at most twice
            if isinstance(obj, list) and obj and text_block(obj[0]):
                obj = json.loads(obj[0]["text"])
                continue
            if text_block(obj):
                obj = json.loads(obj["text"])
                continue
            break
        if isinstance(obj, dict):
            if obj.get("errors") or obj.get("status") == "error":
                raise PeakRefusal("the saved response is an error, not data: %.200s" % json.dumps(obj))
            pg = obj.get("pagination") or {}
            self.total, self.has_more = pg.get("total"), bool(pg.get("has_more"))
            self.link = obj.get("platform_link") or None
            obj = obj.get("results", [])
        self.rows = obj if isinstance(obj, list) else [obj]

    def first(self):
        return self.rows[0] if self.rows else None


def read(path, optional=False):
    """The saved response at path. An optional call PEAK refused reads as None."""
    try:
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
    except OSError as e:
        raise SystemExit("missing response %s: make its call and save the response there (%s)" % (path, e))
    try:
        return Response(json.loads(text))
    except PeakRefusal as e:
        if optional:
            return None
        raise SystemExit("%s is not a saved PEAK response: %s" % (path, e))
    except ValueError as e:
        raise SystemExit("%s is not a saved PEAK response: %s" % (path, e))


class Work:
    """The report's working directory: plan.json, calls.json, and the responses under peak/."""

    def __init__(self, root):
        self.root = root
        self.peak = os.path.join(root, "peak")
        self._calls = None
        with open(os.path.join(root, "plan.json"), encoding="utf-8") as fh:
            self.ctx = json.load(fh)

    @property
    def calls(self):
        """Every call planned so far, follow-up pages included: the record of which files a pull spans."""
        if self._calls is None:
            path = os.path.join(self.root, "calls.json")
            self._calls = json.load(open(path, encoding="utf-8")) if os.path.isfile(path) else []
        return self._calls

    def path(self, name):
        return os.path.join(self.peak, name)

    def has(self, name):
        return os.path.isfile(self.path(name))

    def get(self, name, optional=False):
        return read(self.path(name), optional)


# ── paging ──────────────────────────────────────────────────────────────────
def call_args(c):
    """A call's own arguments: a GraphQL call carries them inside its args."""
    return c["args"]["args"] if isinstance(c["args"].get("args"), dict) else c["args"]


def start_of(c):
    return call_args(c).get("start_index") or 0


def at_offset(c, file, start):
    args = c["args"]
    nested = isinstance(args.get("args"), dict)
    return dict(c, file=file, args=dict(args, args=dict(args["args"], start_index=start)) if nested
                else dict(args, start_index=start))


def pages_due(work, calls):
    """The follow-up pages the saved calls ask for, from each first page's total, a page every `limit`
    rows: <file>-<offset>.json. Pages already saved are left out."""
    out = []
    for c in calls:
        step = call_args(c).get("limit")
        if not step or step < 2 or not work.has(c["file"]):
            continue
        first = work.get(c["file"])
        if not first.has_more:
            continue
        for s in range(step, first.total or 0, step):
            f = c["file"].replace(".json", "-%d.json" % s)
            if not work.has(f):
                out.append(at_offset(c, f, s))
    return out


def pages(work, file):
    """A call's file, then the follow-up pages calls.json lists for it, in offset order."""
    pat = re.compile(re.escape(file[:-len(".json")]) + r"-(\d+)\.json")
    more = sorted((start_of(c), c["file"]) for c in work.calls if pat.fullmatch(c["file"]) and start_of(c))
    return [file] + [f for _, f in more]


def rows(work, file):
    """Every row of a call across its pages."""
    return [r for f in pages(work, file) for r in work.get(f).rows]


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
# the site's currency as PEAK names it (every MonetaryCurrencyEnum value): (code, symbol). The symbol
# prints straight before the figure, so a code that reads as a word carries its own space.
CURRENCIES = {"australian dollar": ("AUD", "$"), "us dollar": ("USD", "$"),
              "united states dollar": ("USD", "$"), "new zealand dollar": ("NZD", "$"),
              "british pound": ("GBP", "£"), "pound sterling": ("GBP", "£"),
              "canadian dollar": ("CAD", "$"), "euro": ("EUR", "€"),
              "singapore dollar": ("SGD", "S$"), "swiss franc": ("CHF", "CHF "),
              "swedish krona": ("SEK", "SEK "), "brazilian real": ("BRL", "R$"),
              "chinese yuan": ("CNY", "¥"), "indonesian rupiah": ("IDR", "Rp ")}


def currency(facts):
    """(code, symbol) for a site, from its site facts."""
    return CURRENCIES.get((facts.get("monetary_currency") or "").strip().lower(), ("USD", "$"))


def plural(n, noun):
    """'1 call', '3 calls'."""
    return "%d %s%s" % (n, noun, "" if n == 1 else "s")


def band(v, bands):
    """The benchmark label a score falls in: bands is [(threshold, label)], highest first; below them all, Poor."""
    for t, label in bands:
        if v >= t:
            return label
    return "Poor"


def host(*sites):
    """The PEAK host links are built on: the first of the sites with a site_link."""
    for s in sites:
        m = re.match(r"https?://[^/]+", s.get("site_link") or "")
        if m:
            return m.group(0)
    return "https://ace.cimenviro.com"


def fetch_logos(urls):
    """{company: data URI} for each company logo PEAK links, embedded so the report stays one
    file. A logo that cannot be fetched is left out, and the company's initials stand in."""
    def get(item):
        name, url = item
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "client-report"})
            with urllib.request.urlopen(req, timeout=15) as r:
                kind, body = r.headers.get_content_type(), r.read()
        except (OSError, ValueError, http.client.HTTPException):
            return name, None
        if not kind.startswith("image/"):
            return name, None
        return name, "data:%s;base64,%s" % (kind, base64.b64encode(body).decode())
    with ThreadPoolExecutor(8) as pool:
        return dict(pool.map(get, urls.items()))


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


def utc(ts):
    """A PEAK timestamp, '2026-10-12T03:15:00Z', as an aware datetime; one with no offset is UTC."""
    t = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
    return t if t.tzinfo else t.replace(tzinfo=timezone.utc)


def local_day(ts, tz):
    """A PEAK UTC timestamp as the site's own date, 'YYYY-MM-DD'."""
    return utc(ts).astimezone(zone(tz)).date().isoformat()


def day_short(s):
    x = d(s)
    return "%d %s %d" % (x.day, MONTHS[x.month - 1][:3], x.year)


def period(first, last_incl, short=False, dash="–"):
    """'1 July – 30 September 2026' (short: '1 Jul – 30 Sep 2026')."""
    a, b = d(first), d(last_incl)
    n = (lambda m: MONTHS[m - 1][:3]) if short else (lambda m: MONTHS[m - 1])
    if a.year == b.year:
        return "%d %s %s %d %s %d" % (a.day, n(a.month), dash, b.day, n(b.month), b.year)
    return "%d %s %d %s %d %s %d" % (a.day, n(a.month), a.year, dash, b.day, n(b.month), b.year)


def listing(items):
    """'a', 'a and b', 'a, b and c'."""
    items = list(items)
    if len(items) < 2:
        return "".join(items)
    return ", ".join(items[:-1]) + " and " + items[-1]


def pct(score, dp):
    """A PEAK 0-1 score as a percentage rounded for display."""
    return round(score * 100, dp)


def months_text(ctx, months, lead=", and "):
    """'August – September 2026, and October to date', 'September 2026' or 'October 2026 to date'."""
    whole_months = whole(ctx, months)
    if not whole_months:
        return "%s %d to date" % (month(months[0]), d(months[0]).year)
    head = (span(whole_months[0], whole_months[-1]) if len(whole_months) > 1
            else "%s %d" % (month(whole_months[0]), d(whole_months[0]).year))
    return head + (and_to_date(ctx, lead) if months[-1] == ctx.get("to_date") else "")


# ── charts and rows shared by the sections ──────────────────────────────────
def kept_months(ctx, on):
    """(first month kept, the quarter's months from it, the trend's months from it). A site that went
    live inside the windows keeps the months it was monitored in full; any other keeps them all."""
    start = on["start"] if on else ctx["trend_months"][0]
    return start, [m for m in ctx["quarter_months"] if m >= start], [m for m in ctx["trend_months"] if m >= start]


def hand_on_start(shared, start, kq, on):
    """Hand on where a section's months start: the trend window, the reporting period, and the go-live."""
    shared.setdefault("trend_start", []).append(start)
    shared.setdefault("period_start", []).append(kq[0])
    if on:
        shared.setdefault("live_since", []).append({"month": on["month"], "day": on["day"]})


def site_scores(site_m, months):
    """The site score for each month, as a percentage to 1dp, None for a month with none."""
    return [pct(site_m[m[:7]]["score"], 1) if m[:7] in site_m else None for m in months]


def score_row(ctx, score, bands, kq, site_q, cap, row):
    """An operational impact score row: its benchmark chip, the score, and the move from the period's
    first scored month to its last. A movement needs two months."""
    got = [(m, v) for m, v in zip(kq, site_q) if v is not None]
    if len(got) > 1:
        delta, sub = movement(got[0][1], got[-1][1], 1, month(got[0][0]), month_label(ctx, got[-1][0]))
    else:
        delta, sub = None, "Scored over %s." % month_label(ctx, kq[0])
    chip = band(score, bands)
    return dict({"chip": chip, "chip_class": "pos" if chip in ("Excellent", "Good") else "warn",
                 "fig": "%.1f%%" % score, "cap": cap, "sub": sub, "row": row}, **({"delta": delta} if delta else {}))


def trend_line(ctx, kt, site_m, bands, what):
    """(the monthly site score chart, the months that scored). A trend needs three points, so with
    fewer there is no chart."""
    values = site_scores(site_m, kt)
    pts = [(m, v) for m, v in zip(kt, values) if v is not None]
    if len(pts) < 3:
        return None, pts
    th = thresholds([v for _, v in pts], bands)
    return {"values": values, "months": [mon(m) for m in kt], "to_date": kt[-1] == ctx["to_date"],
            "thresholds": th, "dp": 1,
            "alt": line_alt(ctx, what, [m for m, _ in pts], [v for _, v in pts], th, 1)}, pts

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
