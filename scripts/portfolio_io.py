#!/usr/bin/env python3
"""Helpers the portfolio report's section scripts share: the report's windows, calls
split across the sites a tool takes at once, their saved chunks and pages read back
as one, each site's region label and building size, the ranking, the portfolio rows
(a plain average of the sites scored), and dates printed with a spaced hyphen, since the
portfolio page carries no en or em dash.

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
    """The chunks a split call was planned as, in order, from calls.json: never whatever sits on disk."""
    pat = re.compile(re.escape(name[:-len(".json")]) + r"-(\d+)\.json")
    got = [(int(pat.fullmatch(c["file"]).group(1)), c["file"]) for c in work.calls
           if pat.fullmatch(c["file"]) and not io.start_of(c)]
    return [f for _, f in sorted(got)]


def rows(work, name):
    """Every row of a split call: each chunk across its pages."""
    return [r for f in chunk_files(work, name) for r in io.rows(work, f)]


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


def shown(shared, site_ids):
    """Mark sites as carrying data somewhere in the report: the masthead counts only these."""
    shared.setdefault("shown_sites", set()).update(s for s in site_ids if s is not None)


def held(rows):
    """Who holds each action in ticket rows, Not Doing left out: [{ticket, site, assignees: [{id, name,
    first, email, company, company_id, logo_url}]}]. Every assignee counts, agents and the client's own
    managing agents included. Email is empty where the pull does not select it."""
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
                           "company": (ent.get("name") or "").strip(), "company_id": ent.get("id")})
        out.append({"ticket": r["ticket_id"], "site": r["site_id"], "assignees": people})
    return out


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


# ── dates without a dash ────────────────────────────────────────────────────
def period(first, last_incl, short=False):
    """'1 July - 30 September 2026' (short: '1 Jul - 30 Sep 2026')."""
    return io.period(first, last_incl, short, dash="-")


def reporting_period(ctx, short=False):
    """The quarter: '1 July - 30 September 2026'."""
    return period(ctx["quarter"][0], ctx["through"], short)


def wins_period(ctx, short=False):
    """The key wins' 90 days: '24 July - 21 October 2026'."""
    return period(ctx["wins"][0], ctx["today"], short)
