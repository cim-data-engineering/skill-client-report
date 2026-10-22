#!/usr/bin/env python3
"""Key wins across the portfolio: everything about the section but the choosing and
the writing.

    python3 references/portfolio-leaderboard/actions-and-wins/scripts/key_wins.py digest <dir> <response file> [...] [--top N]
    python3 references/portfolio-leaderboard/actions-and-wins/scripts/key_wins.py photos <dir>

A portfolio can hold more candidates than anyone can read, so they are read in two
passes, and neither pass is saved. The candidate pulls, the closures with comments
over the 90 days to the issue date and the open actions with comments across every
site, carry each ticket's title, site, priority, saving and who commented, but
nothing anyone wrote. `digest` screens a pull
that came back as a file and ranks what is left. Once <dir>/shortlist.json names the
tickets worth reading in full, scripts/report.py next prints one pull of their
descriptions, solutions and comments. Once <dir>/wins.json names the chosen tickets,
next prints the impact and photo calls, and then the level call; `photos` downloads
each win's ticket images and tiles them into one numbered contact sheet per win;
assemble() turns wins.json into the bundle's wins at fill time. See
references/portfolio-leaderboard/actions-and-wins/key-wins.md.
"""
import json
import os
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "scripts"))
import peak_io as io  # noqa: E402
import portfolio_io as pio  # noqa: E402
import wins_io as kw  # noqa: E402

MAX_WINS = 10
MAX_SHORTLIST = 25     # tickets read in full: enough to find ten wins, few enough to read
TOP = 60               # candidates the digest prints, best first, a third of them kept for work in flight
BULK_SECONDS = 120     # closures at one site within two minutes of each other are one close-out
CHUNK = 20             # sites per candidate pull
# The first pass: enough to screen and rank, nothing anyone wrote but the title.
LIGHT = ["ticket_id", "site_id", "summary", "priority_id", "savings", "created_at", "resolved_at", "status_id",
         {"path": "comments", "args": {"limit": 8, "user_only": True}, "sub_fields": ["created_at", "author_full_name"]}]
# The second pass, on the shortlist only: every word, to choose and write the wins from.
FULL = ["ticket_id", "site_id", "summary", "priority_id", "description", "solution", "savings", "created_at", "resolved_at",
        "status_id", "equipment_ids", "assignees.id", "assignees.entity.name",
        {"path": "comments", "args": {"limit": 8, "user_only": True},
         "sub_fields": ["text", "created_at", "author_full_name"]}]


def esc(ids):
    return {"type": "escalated", "site_ids": ids, "ticket_archived": False}


def calls(ctx):
    w0, w1 = ctx["wins"]
    closed = pio.split(ctx, "kw/closed.json", CHUNK, lambda f, ids: dict(io.gql(
        f, "tickets.tickets", dict(esc(ids), status_id=6, has_comments=True, resolved_at_local_start=w0 + "T00:00:00",
                                   resolved_at_local_end=w1 + "T00:00:00", limit=1000), LIGHT), read=True))
    flight = pio.split(ctx, "kw/in-flight.json", CHUNK, lambda f, ids: dict(io.gql(
        f, "tickets.tickets", dict(esc(ids), status_ids=[1, 3, 7], has_comments=True, limit=1000),
        [x for x in LIGHT if x != "resolved_at"]), read=True))
    return closed + flight


# ── candidates and the digest ───────────────────────────────────────────────
def stamp(ts):
    """A PEAK timestamp as an aware datetime, None where there is none."""
    if not ts:
        return None
    try:
        return io.utc(ts)
    except ValueError:
        return None


def screen(rows, since):
    """Drop what needs no reading: closures nobody worked, bulk close-outs, tickets whose
    only commenter is an agent, and open work no person has commented on since `since`,
    the first of the 90 days. Returns (kept, reasons)."""
    closed = defaultdict(list)
    for r in rows:
        t = stamp(r.get("resolved_at"))
        if t:
            closed[r.get("site_id")].append(t)
    near = lambda r: sum(1 for t in closed[r.get("site_id")]
                         if abs((t - stamp(r["resolved_at"])).total_seconds()) <= BULK_SECONDS)
    why, keep = Counter(), []
    for r in rows:
        made, done = stamp(r.get("created_at")), stamp(r.get("resolved_at"))
        if done and made and abs((done - made).total_seconds()) < 1:
            why["created and resolved the same moment"] += 1
        elif done and near(r) >= 3:
            why["bulk close-out, three or more at one site closed within two minutes"] += 1
        elif not kw.human(r):
            why["only an agent commented"] += 1
        # comments come newest first, so the eight read always hold the latest
        elif not r.get("resolved_at") and max(c.get("created_at") or "" for c in kw.human(r))[:10] < since:
            why["open, with no person commenting in the 90 days"] += 1
        else:
            keep.append(r)
    return keep, why


def rank(r):
    """Best first: finished before open, then the most people engaged, the highest priority,
    and a recorded saving."""
    return (0 if r.get("resolved_at") else 1, -len({c.get("author_full_name") for c in kw.human(r)}),
            -len(kw.human(r)), r.get("priority_id") or 9, -(r.get("savings") or 0))


def best(keep, top):
    """The best `top` of the ranked candidates, a third of them work in flight, so a portfolio's
    closures never crowd it out; a kind short of its share hands the rest to the other."""
    done = [r for r in keep if r.get("resolved_at")]
    live = [r for r in keep if not r.get("resolved_at")]
    n = min(len(live), max(top // 3, top - len(done)))
    return done[:top - n] + live[:n]


def digest(root, paths, top=TOP):
    """Candidate pulls, screened and ranked, one line each with the site. With the light
    first-pass rows this is the list to shortlist from; with the full second-pass rows each
    line carries the description, solution and comments to choose and write from."""
    work = io.Work(root)
    ctx = work.ctx
    sites = {s["site_id"]: s for s in ctx["sites"]}
    facts = {r["site_id"]: r for r in pio.rows(work, "overview/sites.json")}
    rows = [r for p in paths for r in io.read(p).rows]
    keep, why = screen(rows, ctx["wins"][0])
    keep.sort(key=rank)

    def day(ts, sid=None):
        """The date in the site's own time, as the reader dates the work."""
        t = stamp(ts)
        if not t:
            return "?"
        tz = (sites.get(sid) or {}).get("timezone")
        return (t.astimezone(io.zone(tz)) if tz else t).date().isoformat()
    print("%d candidates, %d left after screening. Screened out: %s." % (
        len(rows), len(keep), "; ".join("%d %s" % (n, w) for w, n in why.items()) or "nothing"))
    if top and len(keep) > top:
        shown = best(keep, top)
        print("The %d best by the ranking below, %d of them work in flight; %d more not shown (--top 0 prints all). "
              "Ranked: finished before open, then most people commenting, priority, a recorded saving."
              % (top, sum(1 for r in shown if not r.get("resolved_at")), len(keep) - top))
        keep = shown
    for r in keep:
        site = sites.get(r.get("site_id")) or {"site_name": "site %s" % r.get("site_id")}
        sid = r.get("site_id")
        state = ("closed %s" % day(r.get("resolved_at"), sid)) if r.get("resolved_at") else "open"
        people = len({c.get("author_full_name") for c in kw.human(r)})
        pr = r.get("priority_id")
        print("\n[%s] %s · %s · P%s · %d comment%s by %d %s%s · %s" % (
            r["ticket_id"], site["site_name"].strip(), state, pr if pr and 1 <= pr <= 5 else "-", len(kw.human(r)),
            "" if len(kw.human(r)) == 1 else "s", people, "person" if people == 1 else "people",
            kw.saving_text(r.get("savings"), io.currency(facts.get(sid) or {})[1]), (r.get("summary") or "").strip()))
        for k in ("description", "solution"):
            if kw.clip(r.get(k)):
                print("  %s: %s" % (k, kw.clip(r.get(k))))
        # the full pass prints every comment with words in it, an agent's marked as such
        for c in sorted(r.get("comments") or [], key=lambda c: c.get("created_at") or ""):
            if kw.clip(c.get("text")):
                who = c.get("author_full_name") or "?"
                print("  - %s, %s%s: %s" % (day(c.get("created_at"), sid), who, " (system)" if kw.system(who) else "",
                                            kw.clip(c.get("text"))))


# ── the chosen wins ─────────────────────────────────────────────────────────
def load_wins(work):
    return kw.load_wins(work, most=MAX_WINS, states=True)


def load_shortlist(work):
    path = os.path.join(work.root, "shortlist.json")
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as fh:
        ids = json.load(fh)
    bad = [t for t in ids if not kw.UUID.match(t)]
    if bad or len(ids) > MAX_SHORTLIST:
        raise SystemExit("shortlist.json: up to %d full ticket ids, as the candidate pulls print them%s"
                         % (MAX_SHORTLIST, ": not %s" % ", ".join(bad) if bad else ""))
    return ids


def more(ctx, work):
    wins = load_wins(work)
    if wins is None:
        ids = load_shortlist(work)
        if not ids:
            return []
        # The second pass: the shortlist in full, read where it comes back and never saved.
        return [dict(io.gql("kw/full.json", "tickets.tickets",
                            dict(esc(pio.ids(ctx)), ticket_ids=ids, limit=MAX_SHORTLIST), FULL), read=True)]
    return kw.evidence(work, wins, esc(pio.ids(ctx)), site_field=True) if wins else []


def build(ctx, work, shared):
    return {}


def assemble(ctx, work):
    """wins.json -> the bundle's wins, each with its site, plus the Key wins date line and
    anything to say in chat. Finished repairs lead work in flight; within each, the order
    is wins.json's."""
    imp, level_of = kw.impacts(work), kw.levels(work)
    sites = {s["site_id"]: s for s in ctx["sites"]}
    chat, out = [], []
    for w in load_wins(work):
        at = {(imp.get(t) or {}).get("site_id") for t in w["tickets"]}
        if len(at) > 1:
            raise SystemExit("wins.json: the win %r spans sites %s: a win's tickets are all at one site"
                             % (w["heading"], ", ".join(str(s) for s in sorted(at, key=str))))
        sid = at.pop()
        site = sites.get(sid)
        if not site:
            raise SystemExit("the win %r is on site %s, which is not in this report" % (w["heading"], sid))
        got, said = kw.win(work, w, imp, level_of, site.get("timezone"), escape_titles=False)
        chat += said
        out.append((0 if w.get("state", "fixed") == "fixed" else 1,
                    dict({"site": {"name": site["site_name"].strip(), "state": pio.region(ctx, site)}, "site_id": sid},
                         **got)))
    out.sort(key=lambda x: x[0])
    return {"wins": [w for _, w in out], "datelines": {"Key wins": "%s." % pio.wins_period(ctx)}, "chat": chat}


if __name__ == "__main__":
    if len(sys.argv) >= 4 and sys.argv[1] == "digest":
        args = sys.argv[3:]
        top = TOP
        if "--top" in args:
            i = args.index("--top")
            top = int(args[i + 1])
            args = args[:i] + args[i + 2:]
        digest(sys.argv[2], args, top)
    elif len(sys.argv) == 3 and sys.argv[1] == "photos":
        kw.photos(sys.argv[2], load_wins(io.Work(sys.argv[2])))
    else:
        sys.exit("usage: key_wins.py digest <dir> <response file> [...] [--top N] | key_wins.py photos <dir>")
