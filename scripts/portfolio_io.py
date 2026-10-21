#!/usr/bin/env python3
"""Helpers the portfolio report's section scripts share: the report's windows, calls
split across the sites a tool takes at once, their saved chunks and pages read back
as one, each site's region label and building size, the ranking, the portfolio rows
(a plain average of the sites, or for ratings one weighted by building size), and
dates printed with a spaced hyphen, since the portfolio page carries no en or em dash.

Imported by scripts/report.py and the scripts under references/portfolio-leaderboard/ only.
"""
import base64
import os
import re
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor
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
WINS_DAYS = 90


# ── windows ─────────────────────────────────────────────────────────────────
def today(sites):
    """The issue date: the earliest local date across the sites, so the leaderboard month has closed at
    every one of them."""
    from datetime import datetime
    return min(datetime.now(io.zone(s.get("timezone"))).date() for s in sites)


def windows(today):
    """The report's windows from `today` (the earliest local date across the sites), every one but
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


def region(ctx, site):
    """The label in brackets after a site's name: its state, or its country where the portfolio spans
    countries; nothing where every site shares it, or where the name already ends in brackets."""
    if site["site_name"].strip().endswith(")"):
        return None
    countries = {(s.get("country") or "").strip().lower() for s in ctx["sites"]} - {""}
    if len(countries) > 1:
        return (site.get("country") or "").strip() or None
    if len({state(s) for s in ctx["sites"]}) == 1:
        return None
    return state(site) or None


def host(ctx):
    for s in ctx["sites"]:
        m = re.match(r"https?://[^/]+", s.get("site_link") or "")
        if m:
            return m.group(0)
    return "https://ace.cimenviro.com"


def shown(shared, site_ids):
    """Mark sites as carrying data somewhere in the report: the masthead counts only these."""
    shared.setdefault("shown_sites", set()).update(s for s in site_ids if s is not None)


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


def held(rows):
    """Who holds each action in ticket rows, Not Doing left out: [{ticket, site, assignees: [{id, name,
    first, email, company, logo_url}]}]. Every assignee counts, agents and the client's own managing agents
    included. Email is empty where the pull does not select it."""
    out = []
    for r in rows:
        if r.get("status_id") == 8:
            continue
        people = []
        for a in r.get("assignees") or []:
            ent = a.get("entity") or {}
            first = (a.get("firstname") or "").strip()
            people.append({"id": a.get("id"), "logo_url": ent.get("logo_url"), "first": first,
                           "name": " ".join(x for x in (first, (a.get("lastname") or "").strip()) if x),
                           "email": (a.get("email") or "").strip(),
                           "company": (ent.get("name") or "").strip()})
        out.append({"ticket": r["ticket_id"], "site": r["site_id"], "assignees": people})
    return out


def fetch_logos(urls):
    """{company: data URI} for each company logo PEAK links, embedded so the report stays one
    file. A logo that cannot be fetched is left out, and the company's initials stand in."""
    def get(item):
        name, url = item
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "client-report"})
            with urllib.request.urlopen(req, timeout=15) as r:
                kind, body = r.headers.get_content_type(), r.read()
        except OSError:
            return name, None
        if not kind.startswith("image/"):
            return name, None
        return name, "data:%s;base64,%s" % (kind, base64.b64encode(body).decode())
    with ThreadPoolExecutor(8) as pool:
        return dict(pool.map(get, urls.items()))


def logo_links(actions):
    """{company: logo link} off the assignees of held actions."""
    out = {}
    for act in actions:
        for a in act["assignees"]:
            if a["company"] and a["logo_url"]:
                out.setdefault(a["company"], a["logo_url"])
    return out


def unit_of(site):
    return "ft²" if io.in_feet(site.get("country")) else "m²"


def sizes(ctx, facts):
    """({site_id: building size in the report's unit}, unit, [sites shown outside their own unit]). PEAK
    stores every size in m². The report takes the unit most of its floor area reads in, ft² for US
    sites, and converts from m² into it, rounded to the nearest 100 ft²."""
    raw = {s["site_id"]: (facts.get(s["site_id"]) or {}).get("building_size") for s in ctx["sites"]}
    by_unit = {}
    for s in ctx["sites"]:
        if raw[s["site_id"]]:
            by_unit[unit_of(s)] = by_unit.get(unit_of(s), 0) + raw[s["site_id"]]
    unit = max(by_unit, key=by_unit.get) if by_unit else unit_of(ctx["sites"][0])
    out = {s["site_id"]: io.area(raw[s["site_id"]] or None, unit == "ft²") for s in ctx["sites"]}
    moved = [s["site_name"].strip() for s in ctx["sites"] if raw[s["site_id"]] and unit_of(s) != unit]
    return out, unit, moved


def by_size(ctx, size):
    """The sites, largest building first, then by name."""
    return sorted(ctx["sites"], key=lambda s: (-(size.get(s["site_id"]) or 0), name_key(s)))


def name_key(site):
    return site["site_name"].strip().lower()


def num(v):
    return "{:,}".format(int(round(v))) if v is not None else "-"


# ── ranks and portfolio rows ────────────────────────────────────────────────
RANK_DP = 2            # scores rank to two places, one more than the page prints


def rank(sites, value):
    """[(rank, site)] best first on the value to RANK_DP places, ties split alphabetically by site
    name, so no two sites share a place. Sites with no value are left out."""
    have = [s for s in sites if value(s) is not None]
    have.sort(key=lambda s: (-round(value(s), RANK_DP), name_key(s)))
    return [(k, s) for k, s in enumerate(have, 1)]


def standings(keys, now, then, name):
    """A leaderboard board: ([(rank, key)] best first on the figures `now` to RANK_DP places, {key:
    move}). Last month's board ranks every key with a figure in `then`, on the board now or not, and a
    move is the place there less the place now, "new" with no figure there. Ties split
    alphabetically by name(key), ignoring case, so no two share a place; keys with no figure are left
    out."""
    def order(v):
        have = [k for k in keys if v.get(k) is not None]
        return sorted(have, key=lambda k: (-round(v[k], RANK_DP), name(k).strip().lower(), str(k)))
    ranked = list(enumerate(order(now), 1))
    before = {k: i for i, k in enumerate(order(then), 1)}
    return ranked, {k: before[k] - i if k in before else "new" for i, k in ranked}


def climbers(ctx):
    """Whether boards name a biggest climber: not in a portfolio of three sites or fewer, where a climb
    is mostly two sites swapping places."""
    return len(ctx["sites"]) > 3


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


def mean(values):
    """The plain average of {site_id: value} over the sites with a value: a portfolio row's score."""
    have = [v for v in values.values() if v is not None]
    return sum(have) / len(have) if have else None


def portfolio_months(scores, months, dp=1):
    """A portfolio row: the average of the sites scored each month, and its change over the sites
    scored at both ends only, so a site going live or dropping out is not read as a move. scores is
    {site_id: {month: value}}. Returns (values by month, change or None, [sites the change leaves out])."""
    row = [mean({sid: v.get(m) for sid, v in scores.items()}) for m in months]
    both = {sid: v for sid, v in scores.items() if v.get(months[0]) is not None and v.get(months[-1]) is not None}
    # rounded as the rows print, so a portfolio of one site reads that site's change exactly
    change = (round(mean({sid: v[months[-1]] for sid, v in both.items()}), dp)
              - round(mean({sid: v[months[0]] for sid, v in both.items()}), dp)) if both else None
    left = [sid for sid, v in scores.items() if sid not in both and any(x is not None for x in v.values())]
    return row, change, left


def weighted(values, size):
    """The building-size-weighted mean of {site_id: value} over the sites that have both. Sustainability
    ratings only; every other portfolio row is a plain average."""
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
