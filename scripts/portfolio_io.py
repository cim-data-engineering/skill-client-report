#!/usr/bin/env python3
"""Helpers the portfolio report's section scripts share: the report's windows, calls
split across the sites a tool takes at once, their saved chunks and pages read back
as one, each site's state and building size, the ranking and the building-size
weighting every portfolio row uses, and dates printed with a spaced hyphen, since
the portfolio page carries no en or em dash.

Imported by scripts/report.py and the scripts under references/portfolio-leaderboard/ only.
"""
import os
import re
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import peak_io as io  # noqa: E402

# PEAK spells states out; the page carries the abbreviation.
STATES = {
    "new south wales": "NSW", "victoria": "VIC", "queensland": "QLD", "south australia": "SA",
    "western australia": "WA", "tasmania": "TAS", "northern territory": "NT",
    "australian capital territory": "ACT",
    "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR", "california": "CA", "colorado": "CO",
    "connecticut": "CT", "delaware": "DE", "district of columbia": "DC", "florida": "FL", "georgia": "GA",
    "hawaii": "HI", "idaho": "ID", "illinois": "IL", "indiana": "IN", "iowa": "IA", "kansas": "KS",
    "kentucky": "KY", "louisiana": "LA", "maine": "ME", "maryland": "MD", "massachusetts": "MA",
    "michigan": "MI", "minnesota": "MN", "mississippi": "MS", "missouri": "MO", "montana": "MT",
    "nebraska": "NE", "nevada": "NV", "new hampshire": "NH", "new jersey": "NJ", "new mexico": "NM",
    "new york": "NY", "north carolina": "NC", "north dakota": "ND", "ohio": "OH", "oklahoma": "OK",
    "oregon": "OR", "pennsylvania": "PA", "rhode island": "RI", "south carolina": "SC",
    "south dakota": "SD", "tennessee": "TN", "texas": "TX", "utah": "UT", "vermont": "VT",
    "virginia": "VA", "washington": "WA", "west virginia": "WV", "wisconsin": "WI", "wyoming": "WY",
    "alberta": "AB", "british columbia": "BC", "manitoba": "MB", "new brunswick": "NB",
    "newfoundland and labrador": "NL", "nova scotia": "NS", "ontario": "ON", "prince edward island": "PE",
    "quebec": "QC", "saskatchewan": "SK",
}
FEET = ("united states", "usa", "us")
SQFT_PER_SQM = 10.7639
WINS_DAYS = 90


# ── windows ─────────────────────────────────────────────────────────────────
def windows(today):
    """The report's windows from `today` (the first site's local date), every one but
    the key wins' on month boundaries, end exclusive:
        month       the leaderboard month, the last complete month
        quarter     the three complete months ending on it; quarter_months their firsts
        prev_board  the quarter a month earlier, which last month's leaderboard ranked
        wins        the 90 days to today
        through     the leaderboard month's last day"""
    first = date(today.year, today.month, 1)
    return {"today": today.isoformat(),
            "month": io.add_months(first, -1).isoformat(),
            "quarter": [io.add_months(first, -3).isoformat(), first.isoformat()],
            "quarter_months": [io.add_months(first, k).isoformat() for k in (-3, -2, -1)],
            "prev_board": [io.add_months(first, -4).isoformat(), io.add_months(first, -1).isoformat()],
            "wins": [(today - timedelta(days=WINS_DAYS - 1)).isoformat(), (today + timedelta(days=1)).isoformat()],
            "through": io.last_day(first.isoformat()).isoformat()}


def closing(ctx):
    """True on the 1st: the leaderboard month has only just closed, so a site west of the
    first one can still be in it, and its scores may not have settled."""
    return io.d(ctx["today"]).day == 1


def month_name(ctx):
    """'September 2026': the leaderboard month."""
    return "%s %d" % (io.month(ctx["month"]), io.d(ctx["month"]).year)


# ── calls across many sites ─────────────────────────────────────────────────
def ids(ctx):
    return [s["site_id"] for s in ctx["sites"]]


def chunks(seq, n):
    return [seq[i:i + n] for i in range(0, len(seq), n)]


def split(ctx, name, size, make):
    """One call per `size` sites, saved as <name>-1.json, <name>-2.json and so on.
    `make(file, site_ids)` builds each call."""
    base = name[:-len(".json")]
    return [make("%s-%d.json" % (base, k), part) for k, part in enumerate(chunks(ids(ctx), size), 1)]


def chunk_files(work, name):
    base, k, out = name[:-len(".json")], 1, []
    while work.has("%s-%d.json" % (base, k)):
        out.append("%s-%d.json" % (base, k))
        k += 1
    return out


def pages_due(work, calls, step, nested=False):
    """The follow-up pages a saved chunk asks for: <chunk>-<offset>.json from its
    pagination total, `step` rows a page. A GraphQL call (nested) carries its paging
    inside its own args."""
    out = []
    for c in calls:
        if not work.has(c["file"]):
            continue
        first = work.get(c["file"])
        if not first.has_more:
            continue
        for s in range(step, first.total or 0, step):
            f = c["file"].replace(".json", "-%d.json" % s)
            if work.has(f):
                continue
            args = (dict(c["args"], args=dict(c["args"]["args"], start_index=s)) if nested
                    else dict(c["args"], start_index=s))
            out.append(dict(c, file=f, args=args))
    return out


def rows(work, name, step=None):
    """Every row of a split call: each chunk, then each page of it."""
    out = []
    for f in chunk_files(work, name):
        out += work.get(f).rows
        s = step
        while s and work.has(f.replace(".json", "-%d.json" % s)):
            out += work.get(f.replace(".json", "-%d.json" % s)).rows
            s += step
    return out


def total(work, name):
    """A split call's pagination totals, summed across its chunks."""
    return sum(work.get(f).total or 0 for f in chunk_files(work, name))


# ── sites ───────────────────────────────────────────────────────────────────
def state(site):
    s = (site.get("state") or "").strip()
    return STATES.get(s.lower(), s)


def host(ctx):
    for s in ctx["sites"]:
        m = re.match(r"https?://[^/]+", s.get("site_link") or "")
        if m:
            return m.group(0)
    return "https://ace.cimenviro.com"


def site_count(n):
    """'1 site', '4 sites'."""
    return "%d site%s" % (n, "" if n == 1 else "s")


def tickets_link(ctx, site_ids, grouping, assignee_ids=()):
    """PEAK's ticket report over the quarter at these sites, grouped by "site", "user_entity" (the
    assignee's company) or "assignee", and narrowed to these assignees where any are given."""
    params = (["site_ids=%s" % i for i in site_ids]
              + ["start_date=%sT00:00:00.000" % ctx["quarter"][0], "end_date=%sT00:00:00.000" % ctx["through"],
                 "grouping=%s" % grouping]
              + ["assignee_ids=%s" % a for a in assignee_ids])
    return "%s/reports/tickets?%s" % (host(ctx), "&".join(params))


def unit_of(site):
    return "ft²" if (site.get("country") or "").strip().lower() in FEET else "m²"


def sizes(ctx, facts):
    """({site_id: building size in the report's unit}, unit, [sites converted]). The unit
    is the one that holds most of the floor area; a site recorded in the other is
    converted into it."""
    raw = {s["site_id"]: (facts.get(s["site_id"]) or {}).get("building_size") for s in ctx["sites"]}
    by_unit = {}
    for s in ctx["sites"]:
        if raw[s["site_id"]]:
            u = unit_of(s)
            by_unit[u] = by_unit.get(u, 0) + raw[s["site_id"]] * (SQFT_PER_SQM if u == "m²" else 1)
    unit = max(by_unit, key=by_unit.get) if by_unit else unit_of(ctx["sites"][0])
    out, moved = {}, []
    for s in ctx["sites"]:
        v = raw[s["site_id"]]
        if not v:
            out[s["site_id"]] = None
            continue
        u = unit_of(s)
        if u != unit:
            v = v * SQFT_PER_SQM if unit == "ft²" else v / SQFT_PER_SQM
            moved.append(s["site_name"].strip())
        out[s["site_id"]] = v
    return out, unit, moved


def by_size(ctx, size):
    """The sites, largest building first, then by name."""
    return sorted(ctx["sites"], key=lambda s: (-(size.get(s["site_id"]) or 0), name_key(s)))


def name_key(site):
    return site["site_name"].strip().lower()


def num(v):
    return "{:,}".format(int(round(v))) if v is not None else "-"


# ── ranks and portfolio rows ────────────────────────────────────────────────
def rank(sites, value):
    """[(rank, site)] best first on the unrounded value, ties split alphabetically by site
    name. Sites with no value are left out."""
    have = [s for s in sites if value(s) is not None]
    have.sort(key=lambda s: (-value(s), name_key(s)))
    return [(k, s) for k, s in enumerate(have, 1)]


def standings(keys, now, then, name):
    """A leaderboard board: ([(rank, key)] best first on the unrounded figures `now`, {key: move}).
    Last month's board ranks every key with a figure in `then`, on the board now or not, and a
    move is the place there less the place now, "new" with no figure there. Ties split
    alphabetically by name(key), ignoring case; keys with no figure are left out."""
    def order(v):
        have = [k for k in keys if v.get(k) is not None]
        return sorted(have, key=lambda k: (-v[k], name(k).strip().lower(), str(k)))
    ranked = list(enumerate(order(now), 1))
    before = {k: i for i, k in enumerate(order(then), 1)}
    return ranked, {k: before[k] - i if k in before else "new" for i, k in ranked}


def climber(ranked, moves):
    """The one biggest climber among `ranked`, the places a board shows, never its leader: {key,
    places, rank}, the highest placed of any tied on the climb, or None when no one below the
    leader climbed."""
    climbs = [(moves[k], -rank, k) for rank, k in ranked if rank > 1 and moves[k] != "new" and moves[k] > 0]
    if not climbs:
        return None
    places, rank, key = max(climbs)
    return {"key": key, "places": places, "rank": -rank}


def board_window(ctx, window):
    """The months a board ranks, short as a table header carries them: 'Sep', or over the quarter 'Jul - Sep'."""
    qm = ctx["quarter_months"]
    short = lambda m: io.MONTHS[io.d(m).month - 1][:3]
    return short(qm[-1]) if window == "month" else "%s - %s" % (short(qm[0]), short(qm[-1]))


def board_head(ctx, ranks, more=None):
    """A leaderboard's header: the leaderboard month for its eyebrow, and its date line saying what each
    board ranks, "the sites on one measure", against last month's board, then `more`."""
    line = "Each board ranks %s, with moves since %s." % (ranks, io.month(ctx["quarter_months"][-2]))
    return {"date": month_name(ctx), "note": " ".join(x for x in (line, more) if x)}


def weighted(values, size):
    """The building-size-weighted mean of {site_id: value} over the sites that have both."""
    pairs = [(v, size.get(sid)) for sid, v in values.items() if v is not None and size.get(sid)]
    w = sum(s for _, s in pairs)
    return sum(v * s for v, s in pairs) / w if w else None


# ── dates without a dash ────────────────────────────────────────────────────
def period(first, last_incl, short=False):
    """'1 July - 30 September 2026' (short: '1 Jul - 30 Sep 2026')."""
    a, b = io.d(first), io.d(last_incl)
    n = (lambda m: io.MONTHS[m - 1][:3]) if short else (lambda m: io.MONTHS[m - 1])
    if a.year == b.year:
        return "%d %s - %d %s %d" % (a.day, n(a.month), b.day, n(b.month), b.year)
    return "%d %s %d - %d %s %d" % (a.day, n(a.month), a.year, b.day, n(b.month), b.year)


def reporting_period(ctx, short=False):
    """The quarter: '1 July - 30 September 2026'."""
    return period(ctx["quarter"][0], ctx["through"], short)


def wins_period(ctx, short=False):
    """The key wins' 90 days: '24 July - 21 October 2026'."""
    return period(ctx["wins"][0], ctx["today"], short)


def span(first, last):
    """'July - September', or across a year 'November 2025 - January 2026'."""
    a, b = io.d(first), io.d(last)
    if a.year == b.year:
        return "%s - %s" % (io.month(first), io.month(last))
    return "%s %d - %s %d" % (io.month(first), a.year, io.month(last), b.year)
