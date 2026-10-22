#!/usr/bin/env python3
"""Key wins: everything about the section but the choosing and the writing.

    python3 references/single-site/actions-and-wins/scripts/key_wins.py digest [<dir>] <response file> [...]
    python3 references/single-site/actions-and-wins/scripts/key_wins.py photos <dir>

The two candidate pulls, closures with comments and open actions with comments, are
read where they come back and never saved: what people wrote stays out of the
files. When one comes back offloaded as a file, `digest` prints it screened and
compact, reading the file where the gateway put it; given the report's <dir> first,
its dates read in the site's own time and its savings in the site's currency. Once
<dir>/wins.json names the chosen tickets, scripts/report.py next prints the impact
and photo calls, and then the level call; `photos` downloads each win's ticket images,
tiles them into one numbered contact sheet per win and strips the signed links from
the saved attachments; assemble() turns wins.json into the bundle's wins at fill time.
See references/single-site/actions-and-wins/key-wins.md.
"""
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "scripts"))
import peak_io as io  # noqa: E402
import wins_io as kw  # noqa: E402

BULK_RUN, BULK_GAP = 3, 120     # three or more closures, each within two minutes of the one before: a bulk close-out
FIELDS = ["ticket_id", "summary", "description", "solution", "savings", "comment_count", "created_at",
          "resolved_at", "equipment_ids",
          "assignees.id", "assignees.entity.name",
          {"path": "comments", "args": {"limit": 8, "user_only": True},
           "sub_fields": ["text", "created_at", "author_full_name"]}]


def esc(ctx):
    return {"type": "escalated", "site_ids": [ctx["site"]["site_id"]], "ticket_archived": False}


def calls(ctx):
    q0, q1 = ctx["quarter"]
    return [dict(io.gql("kw/closed.json", "tickets.tickets",
                        dict(esc(ctx), status_id=6, has_comments=True, resolved_at_local_start=q0 + "T00:00:00",
                             resolved_at_local_end=q1 + "T00:00:00", limit=1000), FIELDS), read=True),
            dict(io.gql("kw/in-flight.json", "tickets.tickets",
                        dict(esc(ctx), status_ids=[1, 3, 7], has_comments=True, limit=1000),
                        [f for f in FIELDS if f != "resolved_at"]), read=True)]


# ── candidates and the digest ───────────────────────────────────────────────
def bulk(rows):
    """Ticket ids closed in a bulk close-out: BULK_RUN or more closures, each within BULK_GAP
    seconds of the one before."""
    out, run = set(), []
    for r in sorted((r for r in rows if r.get("resolved_at")), key=lambda r: io.utc(r["resolved_at"])) + [None]:
        if r and run and (io.utc(r["resolved_at"]) - io.utc(run[-1]["resolved_at"])).total_seconds() <= BULK_GAP:
            run.append(r)
            continue
        if len(run) >= BULK_RUN:
            out |= {x.get("ticket_id") for x in run}
        run = [r] if r else []
    return out


def screen(rows):
    """Drop what needs no reading: closures nobody worked, bulk close-outs, and tickets
    whose only commenters are agents or CIM's system accounts. Returns (kept, reasons)."""
    closed_together = bulk(rows)
    why, keep = Counter(), []
    for r in rows:
        if r.get("resolved_at") and (r.get("created_at") or "")[:19] == r["resolved_at"][:19]:
            why["created and resolved the same moment"] += 1
        elif r.get("resolved_at") and r.get("ticket_id") in closed_together:
            why["bulk close-out, three or more closed each within two minutes of the last"] += 1
        elif not kw.human(r):
            why["only an agent or a CIM system account commented"] += 1
        else:
            keep.append(r)
    return keep, why


def digest(args):
    """Candidate pulls that came back as files, screened and printed compact. With the report's
    folder first, dates read in the site's own time and savings carry its currency."""
    root = args[0] if os.path.isfile(os.path.join(args[0], "plan.json")) else None
    paths = args[1:] if root else args
    if not paths:
        raise SystemExit("usage: key_wins.py digest [<dir>] <response file> [...]")
    tz, sym = None, ""
    if root:
        work = io.Work(root)
        tz = io.zone(work.ctx["site"]["timezone"])
        facts = (work.get("overview/site.json").first() or {}) if work.has("overview/site.json") else {}
        sym = io.currency(facts)[1] if facts.get("monetary_currency") else ""
    rows = [r for p in paths for r in io.read(p).rows]
    keep, why = screen(rows)
    day = lambda ts: (io.utc(ts).astimezone(tz).date().isoformat() if tz else ts[:10]) if ts else "?"
    print("%d candidates, %d left after screening. Screened out: %s." % (
        len(rows), len(keep), "; ".join("%d %s" % (n, w) for w, n in why.items()) or "nothing"))
    if not root:
        print("Dates are UTC. Pass the report's folder first, digest <dir> <file>, for the site's own dates "
              "and currency.")
    for r in sorted(keep, key=lambda r: -len(kw.human(r))):
        state = ("closed %s" % day(r.get("resolved_at"))) if r.get("resolved_at") else "open"
        print("\n[%s] %s, raised %s%s · %s" % (r["ticket_id"], state, day(r.get("created_at")),
                                              kw.saving_text(r.get("savings"), sym), (r.get("summary") or "").strip()))
        for k in ("description", "solution"):
            if kw.clip(r.get(k)):
                print("  %s: %s" % (k, kw.clip(r.get(k))))
        for c in sorted(kw.human(r), key=lambda c: c.get("created_at") or ""):
            print("  - %s, %s: %s" % (day(c.get("created_at")), c.get("author_full_name") or "?", kw.clip(c.get("text"))))


# ── the chosen wins ─────────────────────────────────────────────────────────
def load_wins(work):
    return kw.load_wins(work)


def more(ctx, work):
    wins = load_wins(work)
    return kw.evidence(work, wins, esc(ctx)) if wins else []


def build(ctx, work, shared):
    return {"drop": True} if shared.get("nothing_resolved") else {}


def assemble(ctx, work):
    """wins.json -> the bundle's wins, plus the Key wins statement and date line and
    anything to say in chat."""
    imp, level_of = kw.impacts(work), kw.levels(work)
    chat, out = [], []
    for w in load_wins(work):
        got, said = kw.win(work, w, imp, level_of, ctx["site"].get("timezone"), escape_titles=True)
        out.append(got)
        chat += said
    out.sort(key=lambda w: 0 if len(w.get("photos", [])) >= 2 else 1 if w.get("photos") else 2)
    qw = io.whole(ctx, ctx["quarter_months"])
    return {"wins": out,
            "statements": {"Key wins": "Key wins this quarter"},
            "datelines": {"Key wins": io.span(qw[0], qw[-1]) + io.and_to_date(ctx, " and ")},
            "chat": chat}


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "digest":
        digest(sys.argv[2:])
    elif len(sys.argv) == 3 and sys.argv[1] == "photos":
        kw.photos(sys.argv[2], load_wins(io.Work(sys.argv[2])))
    else:
        sys.exit("usage: key_wins.py digest <response file> [...] | key_wins.py photos <dir>")
