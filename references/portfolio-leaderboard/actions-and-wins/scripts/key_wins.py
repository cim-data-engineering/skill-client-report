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
import html
import json
import os
import re
import sys
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "scripts"))
import peak_io as io  # noqa: E402
import portfolio_io as pio  # noqa: E402

NAME = "key-wins"
MAX_WINS = 10
MAX_SHORTLIST = 25     # tickets read in full: enough to find ten wins, few enough to read
TOP = 60               # candidates the digest prints, best first, a third of them kept for work in flight
SEVERITY = ["safety", "reliability", "comfort", "energy", "water", "other"]
AGENT = io.AGENT
SYSTEM_NAMES = {n.lower() for n in io.SYSTEM_ACCOUNTS.values()}
BULK_SECONDS = 120     # closures at one site within two minutes of each other are one close-out
IMAGE = {"image/jpeg": "jpg", "image/jpg": "jpg", "image/png": "png", "image/webp": "webp"}
PER_WIN = 16           # images tiled per win; a ticket can carry dozens of uploads
COMMENT_CHARS = 420
CHUNK = 20             # sites per candidate pull
SAVING = re.compile(r"\*\*(.+?)\*\*")   # a saving the win's tickets reference, set bold
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
def system(name):
    """A comment author that is CIM's system rather than a person: an agent, or a system account by name."""
    name = (name or "").strip()
    return bool(AGENT.match(name)) or name.lower() in SYSTEM_NAMES


def human(r):
    return [c for c in r.get("comments") or [] if not system(c.get("author_full_name"))]


def stamp(ts):
    """A PEAK timestamp as an aware datetime, None where there is none."""
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
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
        elif not human(r):
            why["only an agent commented"] += 1
        # comments come newest first, so the eight read always hold the latest
        elif not r.get("resolved_at") and max(c.get("created_at") or "" for c in human(r))[:10] < since:
            why["open, with no person commenting in the 90 days"] += 1
        else:
            keep.append(r)
    return keep, why


def rank(r):
    """Best first: finished before open, then the most people engaged, the highest priority,
    and a recorded saving."""
    return (0 if r.get("resolved_at") else 1, -len({c.get("author_full_name") for c in human(r)}), -len(human(r)),
            r.get("priority_id") or 9, -(r.get("savings") or 0))


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
        sym = io.currency(facts.get(sid) or {})[2]
        saved = (" · savings %s%s" % (sym, "{:,}".format(round(r["savings"])))) if round(r.get("savings") or 0) else ""
        people = len({c.get("author_full_name") for c in human(r)})
        pr = r.get("priority_id")
        print("\n[%s] %s · %s · P%s · %d comment%s by %d %s%s · %s" % (
            r["ticket_id"], site["site_name"].strip(), state, pr if pr and 1 <= pr <= 5 else "-", len(human(r)),
            "" if len(human(r)) == 1 else "s", people, "person" if people == 1 else "people", saved,
            (r.get("summary") or "").strip()))
        for k in ("description", "solution"):
            if clip(r.get(k)):
                print("  %s: %s" % (k, clip(r.get(k))))
        # the full pass prints every comment with words in it, an agent's marked as such
        for c in sorted(r.get("comments") or [], key=lambda c: c.get("created_at") or ""):
            if clip(c.get("text")):
                who = c.get("author_full_name") or "?"
                print("  - %s, %s%s: %s" % (day(c.get("created_at"), sid), who, " (system)" if system(who) else "",
                                            clip(c.get("text"))))


def clip(text):
    text = " ".join((text or "").split())
    return text[:COMMENT_CHARS].rsplit(" ", 1)[0] + " …" if len(text) > COMMENT_CHARS else text


# ── the chosen wins ─────────────────────────────────────────────────────────
UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")


def load_wins(work):
    path = os.path.join(work.root, "wins.json")
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as fh:
        wins = json.load(fh)
    if len(wins) > MAX_WINS:
        raise SystemExit("wins.json holds %d wins: %d at most, the strongest across the portfolio"
                         % (len(wins), MAX_WINS))
    for w in wins:
        bad = [t for t in w.get("tickets") or [] if not UUID.match(t)]
        if bad or not w.get("tickets"):
            raise SystemExit("wins.json: the win %r needs its tickets as full ticket ids, as the candidate "
                             "pulls print them%s" % (w.get("heading"), ": not %s" % ", ".join(bad) if bad else ""))
    return wins


def tickets(wins):
    return list(dict.fromkeys(t for w in wins for t in w["tickets"]))


def load_shortlist(work):
    path = os.path.join(work.root, "shortlist.json")
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as fh:
        ids = json.load(fh)
    bad = [t for t in ids if not UUID.match(t)]
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
    if not wins:
        return []
    ids = tickets(wins)
    have = {r.get("ticket_id") for r in work.get("kw/impacts.json").rows} if work.has("kw/impacts.json") else set()
    if not set(ids) <= have or not work.has("kw/attachments.json"):
        return [io.call("kw/impacts.json", "search_action_tickets", ticket_ids=ids, limit=50),
                io.gql("kw/attachments.json", "tickets.tickets", dict(esc(pio.ids(ctx)), ticket_ids=ids, limit=50),
                       ["ticket_id", "site_id", "attachments.attachment_id", "attachments.file_name",
                        "attachments.mime_type", "attachments.preview.link.url", "attachments.link.url"])]
    eq = list(dict.fromkeys(e for r in work.get("kw/impacts.json").rows if r.get("ticket_id") in ids
                            for e in r.get("equipment_ids") or []))
    have_eq = {r.get("equipment_id") for r in work.get("kw/levels.json").rows} if work.has("kw/levels.json") else set()
    if eq and not set(eq) <= have_eq:
        return [io.gql("kw/levels.json", "platform.equipment", {"equipment_ids": eq, "limit": 100},
                       ["equipment_id", "name", "zone.level.level_name", "zone.level.system"])]
    return []


def build(ctx, work, shared):
    return {}


# ── photos ──────────────────────────────────────────────────────────────────
def fetch(url, dest):
    req = urllib.request.Request(url, headers={"User-Agent": "client-report"})
    with urllib.request.urlopen(req, timeout=60) as r, open(dest, "wb") as fh:
        fh.write(r.read())
    return dest


def photos(root):
    work = io.Work(root)
    wins = load_wins(work)
    if wins is None:
        raise SystemExit("No %s/wins.json yet: choose the wins by key-wins.md and write it, then run "
                         "python3 scripts/report.py next %s for their impact and photo calls." % (root, root))
    if not wins:
        print("wins.json holds no win, so there are no photos. Next: python3 scripts/report.py fill %s" % root)
        return
    if not work.has("kw/attachments.json"):
        raise SystemExit("kw/attachments.json is not saved yet: run python3 scripts/report.py next %s and make the "
                         "calls it prints, then photos again." % root)
    att = {r["ticket_id"]: r.get("attachments") or [] for r in work.get("kw/attachments.json").rows}
    jobs, plan = [], {}
    out_dir = os.path.join(root, "kw", "photos")
    os.makedirs(out_dir, exist_ok=True)
    for k, w in enumerate(wins, 1):
        seen, n = set(), 0
        for t in w["tickets"]:
            for a in att.get(t, []):
                ext = IMAGE.get((a.get("mime_type") or "").lower())
                # one upload attached to two tickets is one photo; two uploads sharing a file name are two
                name = a.get("attachment_id") or ((a.get("link") or {}).get("url") or "").split("?")[0]
                if not ext or name in seen or n >= PER_WIN:
                    continue
                seen.add(name)
                n += 1
                pick = "w%d-%d" % (k, n)
                urls = [u for u in ((a.get("link") or {}).get("url"), ((a.get("preview") or {}).get("link") or {}).get("url")) if u]
                jobs.append((pick, urls, os.path.join(out_dir, "%s.%s" % (pick, ext))))
                plan.setdefault(k, []).append(pick)

    if not jobs:
        print("No win's tickets carry an image, so there are no sheets. Next: python3 scripts/report.py next %s, "
              "which prints the level call if it is still due, then fill." % root)
        return

    def get(job):
        pick, urls, dest = job
        err = None
        for u in urls:
            try:
                return pick, fetch(u, dest), None
            except Exception as e:                 # a lapsed link reads as 403
                err = e
        return pick, None, err
    with ThreadPoolExecutor(8) as pool:
        got = list(pool.map(get, jobs))
    failed = [(p, e) for p, d, e in got if not d]
    if failed and len(failed) == len(got):
        raise SystemExit("no photo downloaded (%s). The links lapse twenty minutes after the call: make the "
                         "kw/attachments.json call again, save it, and re-run photos." % failed[0][1])
    unsign(work)
    sheets = contact_sheets(root, plan, {p: d for p, d, e in got if d})
    print("Downloaded %d of %d images. One sheet per win, each tile numbered with its pick:" % (len(got) - len(failed), len(got)))
    for k, s in sheets:
        print("  win %d (%s): %s" % (k, wins[k - 1].get("heading", "")[:60], s))
    if failed:
        print("Not downloaded: " + ", ".join(p for p, e in failed))
    print("Look at each sheet, then add the picks to that win's photos in wins.json, in story order, e.g. "
          '"photos": ["w1-2", {"pick": "w1-4", "focus": [0.7, 0.4], "zoom": 2}]. A win with no good photo gets none.')


def unsign(work):
    """Rewrite kw/attachments.json without its signed links once the photos are on disk: the files keep
    counts, ids and names only, never a credential."""
    path = work.path("kw/attachments.json")
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    clean = re.sub(r'"(?:url)"\s*:\s*"https?://[^"]*"', '"url": null', text)
    if clean != text:
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(clean)


def contact_sheets(root, plan, files):
    try:
        from PIL import Image, ImageDraw, ImageOps
    except ImportError:
        raise SystemExit("photos need Pillow: pip install pillow")
    out = []
    tile, cols = 320, 4
    for k, picks in plan.items():
        picks = [p for p in picks if p in files]
        if not picks:
            continue
        rows = (len(picks) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * tile, rows * (tile + 28)), "white")
        draw = ImageDraw.Draw(sheet)
        for i, p in enumerate(picks):
            try:
                im = ImageOps.exif_transpose(Image.open(files[p])).convert("RGB")
            except Exception:
                continue
            size = "%dx%d" % im.size                # the original's, so a soft print shows here
            im.thumbnail((tile - 8, tile - 8))
            x, y = (i % cols) * tile, (i // cols) * (tile + 28)
            sheet.paste(im, (x + (tile - im.width) // 2, y + 28 + (tile - im.height) // 2))
            draw.text((x + 6, y + 6), "%s  %s" % (p, size), fill="black")
        path = os.path.join(root, "kw", "sheet-w%d.jpg" % k)
        sheet.save(path, quality=80)
        out.append((k, path))
    return out


# ── assembly, at fill time ──────────────────────────────────────────────────
def assemble(ctx, work, facts):
    """wins.json -> the bundle's wins, each with its site, plus the Key wins date line and
    anything to say in chat. Finished repairs lead work in flight; within each, the order
    is wins.json's."""
    wins = load_wins(work)
    imp = {r["ticket_id"]: r for r in work.get("kw/impacts.json").rows}
    sites = {s["site_id"]: s for s in ctx["sites"]}
    levels = {}
    if work.has("kw/levels.json"):
        for r in work.get("kw/levels.json").rows:
            lv = ((r.get("zone") or {}).get("level") or {})
            if lv.get("level_name") and not lv.get("system"):
                levels[r["equipment_id"]] = lv["level_name"]
    chat, out = [], []
    for w in wins:
        tags = []
        for t in w["tickets"]:
            row = imp.get(t)
            if not row:
                raise SystemExit("kw/impacts.json has no row for %s: make the calls report.py next prints" % t)
            real = [i for i in (row.get("impacts") or []) if i in SEVERITY and i != "other"]
            tags += real
            if not real:
                chat.append("Ticket %s, \"%s\", has no impact set in PEAK, so its win takes the tag of its other "
                            "tickets or Other. Set the impact in PEAK and re-run." % (t[:8], row.get("title")))
        impact = min(tags, key=SEVERITY.index) if tags else "other"
        sid = imp[w["tickets"][0]].get("site_id")
        site = sites.get(sid)
        if not site:
            raise SystemExit("the win %r is on site %s, which is not in this report" % (w["heading"], sid))
        names = []
        for t in w["tickets"]:
            for e in imp[t].get("equipment_ids") or []:
                if levels.get(e) and levels[e] not in names:
                    names.append(levels[e])
        pics = []
        for p in w.get("photos") or []:
            p = {"pick": p} if isinstance(p, str) else dict(p)
            pick = p.pop("pick", None)
            hit = [f for f in os.listdir(os.path.join(work.root, "kw", "photos")) if f.split(".")[0] == pick] \
                if pick and os.path.isdir(os.path.join(work.root, "kw", "photos")) else []
            if not hit:
                raise SystemExit("wins.json: photo %r is not on disk: run key_wins.py photos first" % pick)
            pics.append(dict(p, src=os.path.join("kw", "photos", hit[0])))
        sym = io.currency(facts.get(sid) or {})[2]
        saved = round(sum(imp[t].get("savings") or 0 for t in w["tickets"]))
        if saved and not SAVING.search(w["body"]):
            chat.append("The tickets behind \"%s\" record %s%s in savings, which its text does not mention."
                        % (w["heading"], sym, "{:,}".format(saved)))
        body = SAVING.sub(r"<strong>\1</strong>", html.escape(w["body"], quote=False))
        titles = Counter((imp[t].get("title") or "").strip() for t in w["tickets"])
        ref = lambda t: (imp[t].get("title") or "").strip() + (
            " (raised %s)" % io.day_short(io.local_day(imp[t]["created_at"], site.get("timezone"))) if titles[(imp[t].get("title") or "").strip()] > 1
            and imp[t].get("created_at") else "")
        win = {"site": {"name": site["site_name"].strip(), "state": pio.region(ctx, site)}, "site_id": sid,
               "impact": impact,
               "heading": html.escape(w["heading"], quote=False), "body": body,
               "refs": [{"url": imp[t]["ticket_link"], "title": ref(t)} for t in w["tickets"]]}
        if names:
            win["level"] = names[0] if len(names) == 1 else names
        if pics:
            win["photos"] = pics
        win["_fixed"] = w.get("state", "fixed") == "fixed"
        out.append(win)
    out.sort(key=lambda w: 0 if w["_fixed"] else 1)
    for w in out:
        w.pop("_fixed")
    return {"wins": out, "datelines": {"Key wins": "%s." % pio.wins_period(ctx)}, "chat": chat}


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
        photos(sys.argv[2])
    else:
        sys.exit("usage: key_wins.py digest <dir> <response file> [...] [--top N] | key_wins.py photos <dir>")
