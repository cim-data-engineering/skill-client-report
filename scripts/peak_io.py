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


def call(file, tool, **args):
    """A call for the model to make: the PEAK tool, its arguments, and the file its
    response is saved as, under peak/."""
    return {"file": file, "tool": tool, "args": args}


def gql(file, query, args, fields):
    return call(file, "execute_graphql_query", query_name=query, args=args, fields=fields)


# ── windows ─────────────────────────────────────────────────────────────────
def add_months(d, n):
    m = d.year * 12 + d.month - 1 + n
    return date(m // 12, m % 12 + 1, 1)


def windows(today):
    """Every window closes on the last complete month before `today` (site local).
    The quarter is its three complete months, the trend window its six."""
    end = date(today.year, today.month, 1)            # exclusive
    return {"today": today.isoformat(),
            "quarter": [add_months(end, -3).isoformat(), end.isoformat()],
            "trend": [add_months(end, -6).isoformat(), end.isoformat()],
            "quarter_months": [add_months(end, i).isoformat() for i in range(-3, 0)],
            "trend_months": [add_months(end, i).isoformat() for i in range(-6, 0)]}


def d(s):
    return date.fromisoformat(s[:10])


def last_day(start_excl_end):
    """The inclusive last day of a window whose end is exclusive."""
    e = d(start_excl_end)
    return date.fromordinal(e.toordinal() - 1)


# ── formats ─────────────────────────────────────────────────────────────────
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


def line_alt(what, months, values, th, dp):
    vals = ["%.*f" % (dp, v) for v in values]
    head = "Line chart of monthly %s, %s: %s and %s percent" % (
        what, span(months[0], months[-1], sep=" to "), ", ".join(vals[:-1]), vals[-1])
    (t1, l1), (t2, l2) = th[0], th[-1]
    return head + ", against the %.1f percent %s threshold and the %.1f percent %s threshold." % (t2, l2, t1, l1)


def movement(first, last, dp, m0, m1, unit="pp"):
    c = round(last - first, dp)
    if c == 0:
        return None, "Steady at %.*f%% from %s to %s." % (dp, last, m0, m1)
    return ({"dir": "up" if c > 0 else "down", "amount": "%.*f %s" % (dp, abs(c), unit)},
            "from %.*f%% in %s to %.*f%% in %s." % (dp, first, m0, dp, last, m1))
