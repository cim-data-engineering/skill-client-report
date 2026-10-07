#!/usr/bin/env python3
"""Key wins: everything about the section but the choosing and the writing.

    python3 references/actions-and-wins/scripts/key_wins.py digest <response file> [...]
    python3 references/actions-and-wins/scripts/key_wins.py photos <dir>

The two candidate pulls, closures with comments and open actions with comments, are
read where they come back and never saved: what people wrote stays out of the
files. When one comes back offloaded as a file, `digest` prints it screened and
compact, reading the file where the gateway put it. Once <dir>/wins.json names
the chosen tickets, scripts/report.py next prints the impact and photo calls, and
then the level call; `photos` downloads each win's ticket images and tiles them
into one numbered contact sheet per win; assemble() turns wins.json into the
bundle's wins at fill time. See references/actions-and-wins/key-wins.md.
"""
import json
import os
import re
import sys
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "scripts"))
import peak_io as io  # noqa: E402

NAME = "key-wins"
SEVERITY = ["safety", "reliability", "comfort", "energy", "water", "other"]
AGENT = re.compile(r"^\s*agent\b", re.I)
IMAGE = {"image/jpeg": "jpg", "image/jpg": "jpg", "image/png": "png", "image/webp": "webp"}
PER_WIN = 16           # images tiled per win; a ticket can carry dozens of uploads
COMMENT_CHARS = 420
FIELDS = ["ticket_id", "summary", "comment_count", "created_at", "resolved_at", "equipment_ids",
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
def human(r):
    return [c for c in r.get("comments") or [] if not AGENT.match(c.get("author_full_name") or "")]


def screen(rows):
    """Drop what needs no reading: closures nobody worked, bulk close-outs, and tickets
    whose only commenter is an agent. Returns (kept, reasons)."""
    stamps = Counter(r["resolved_at"][:19] for r in rows if r.get("resolved_at"))
    why, keep = Counter(), []
    for r in rows:
        if r.get("resolved_at") and r.get("created_at", "")[:19] == r["resolved_at"][:19]:
            why["created and resolved the same moment"] += 1
        elif r.get("resolved_at") and stamps[r["resolved_at"][:19]] >= 3:
            why["bulk close-out, three or more sharing a resolved second"] += 1
        elif not human(r):
            why["only an agent commented"] += 1
        else:
            keep.append(r)
    return keep, why


def digest(paths):
    """A candidate pull that came back as a file, screened and printed compact."""
    rows = [r for p in paths for r in io.read(p).rows]
    keep, why = screen(rows)
    day = lambda ts: ts[:10] if ts else "?"
    print("%d candidates, %d left after screening. Screened out: %s." % (
        len(rows), len(keep), "; ".join("%d %s" % (n, w) for w, n in why.items()) or "nothing"))
    for r in sorted(keep, key=lambda r: -len(human(r))):
        state = ("closed %s" % day(r.get("resolved_at"))) if r.get("resolved_at") else "open"
        print("\n[%s] %s, raised %s · %s" % (r["ticket_id"], state, day(r.get("created_at")),
                                            (r.get("summary") or "").strip()))
        for c in sorted(human(r), key=lambda c: c.get("created_at") or ""):
            text = " ".join((c.get("text") or "").split())
            if len(text) > COMMENT_CHARS:
                text = text[:COMMENT_CHARS].rsplit(" ", 1)[0] + " …"
            print("  - %s, %s: %s" % (day(c.get("created_at")), c.get("author_full_name") or "?", text))


# ── the chosen wins ─────────────────────────────────────────────────────────
UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")


def load_wins(work):
    path = os.path.join(work.root, "wins.json")
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as fh:
        wins = json.load(fh)
    for w in wins:
        bad = [t for t in w.get("tickets") or [] if not UUID.match(t)]
        if bad or not w.get("tickets"):
            raise SystemExit("wins.json: the win %r needs its tickets as full ticket ids, as the candidate "
                             "pulls print them%s" % (w.get("heading"), ": not %s" % ", ".join(bad) if bad else ""))
    return wins


def tickets(wins):
    return list(dict.fromkeys(t for w in wins for t in w["tickets"]))


def more(ctx, work):
    wins = load_wins(work)
    if not wins:
        return []
    ids = tickets(wins)
    have = {r.get("ticket_id") for r in work.get("kw/impacts.json").rows} if work.has("kw/impacts.json") else set()
    if not set(ids) <= have or not work.has("kw/attachments.json"):
        return [io.call("kw/impacts.json", "search_action_tickets", ticket_ids=ids, limit=50),
                io.gql("kw/attachments.json", "tickets.tickets", dict(esc(ctx), ticket_ids=ids, limit=50),
                       ["ticket_id", "attachments.attachment_id", "attachments.file_name", "attachments.mime_type",
                        "attachments.preview.link.url", "attachments.link.url"])]
    eq = list(dict.fromkeys(e for r in work.get("kw/impacts.json").rows if r.get("ticket_id") in ids
                            for e in r.get("equipment_ids") or []))
    have_eq = {r.get("equipment_id") for r in work.get("kw/levels.json").rows} if work.has("kw/levels.json") else set()
    if eq and not set(eq) <= have_eq:
        return [io.gql("kw/levels.json", "platform.equipment", {"equipment_ids": eq, "limit": 100},
                       ["equipment_id", "name", "zone.level.level_name", "zone.level.system"])]
    return []


def build(ctx, work, shared):
    return {"facts": [], "prose": {}}


# ── photos ──────────────────────────────────────────────────────────────────
def fetch(url, dest):
    req = urllib.request.Request(url, headers={"User-Agent": "client-report"})
    with urllib.request.urlopen(req, timeout=60) as r, open(dest, "wb") as fh:
        fh.write(r.read())
    return dest


def photos(root):
    work = io.Work(root)
    wins = load_wins(work)
    if not wins:
        raise SystemExit("write %s/wins.json first" % root)
    att = {r["ticket_id"]: r.get("attachments") or [] for r in work.get("kw/attachments.json").rows}
    jobs, plan = [], {}
    out_dir = os.path.join(root, "kw", "photos")
    os.makedirs(out_dir, exist_ok=True)
    for k, w in enumerate(wins, 1):
        seen, n = set(), 0
        for t in w["tickets"]:
            for a in att.get(t, []):
                ext = IMAGE.get((a.get("mime_type") or "").lower())
                name = (a.get("file_name") or "").strip().lower()
                if not ext or name in seen or n >= PER_WIN:
                    continue
                seen.add(name)
                n += 1
                pick = "w%d-%d" % (k, n)
                urls = [u for u in ((a.get("link") or {}).get("url"), ((a.get("preview") or {}).get("link") or {}).get("url")) if u]
                jobs.append((pick, urls, os.path.join(out_dir, "%s.%s" % (pick, ext))))
                plan.setdefault(k, []).append(pick)

    def get(job):
        pick, urls, dest = job
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
    sheets = contact_sheets(root, plan, {p: d for p, d, e in got if d})
    print("Downloaded %d of %d images. One sheet per win, each tile numbered with its pick:" % (len(got) - len(failed), len(got)))
    for k, s in sheets:
        print("  win %d (%s): %s" % (k, wins[k - 1].get("heading", "")[:60], s))
    if failed:
        print("Not downloaded: " + ", ".join(p for p, e in failed))
    print("Look at each sheet, then add the picks to that win's photos in wins.json, in story order, e.g. "
          '"photos": ["w1-2", {"pick": "w1-4", "focus": [0.7, 0.4], "zoom": 2}]. A win with no good photo gets none.')


def contact_sheets(root, plan, files):
    try:
        from PIL import Image, ImageDraw, ImageOps
    except ImportError:
        raise SystemExit("photos need Pillow — pip install pillow")
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
def assemble(ctx, work):
    """wins.json -> the bundle's wins, plus the Key wins statement and date line and
    anything to say in chat."""
    wins = load_wins(work)
    imp = {r["ticket_id"]: r for r in work.get("kw/impacts.json").rows}
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
                raise SystemExit("wins.json: photo %r is not on disk — run key_wins.py photos first" % pick)
            pics.append(dict(p, src=os.path.join("kw", "photos", hit[0])))
        win = {"impact": impact, "heading": w["heading"], "body": w["body"],
               "refs": [{"url": imp[t]["ticket_link"], "title": imp[t].get("title")} for t in w["tickets"]]}
        if names:
            win["level"] = names[0] if len(names) == 1 else names
        if pics:
            win["photos"] = pics
        if w.get("snap") and "equipment-health" in ctx["sections"]:
            win["snap"] = w["snap"]
        win["_state"] = w.get("state", "fixed")
        out.append(win)
    out.sort(key=lambda w: 0 if len(w.get("photos", [])) >= 2 else 1 if w.get("photos") else 2)
    states = [w.pop("_state") for w in out]
    fixed = all(s == "fixed" for s in states)
    q = io.span(ctx["quarter_months"][0], ctx["quarter_months"][-1])
    return {"wins": out,
            "statements": {"Key wins": "What changed in the building this quarter" if fixed
                           else "What we found and acted on this quarter"},
            "datelines": {"Key wins": "%s. %s" % (q, "Faults found by continuous monitoring and fixed on the floor."
                                                      if fixed else "Repairs made this quarter, and faults found by "
                                                      "continuous monitoring that are still being worked.")},
            "chat": chat}


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "digest":
        digest(sys.argv[2:])
    elif len(sys.argv) == 3 and sys.argv[1] == "photos":
        photos(sys.argv[2])
    else:
        sys.exit("usage: key_wins.py digest <response file> [...] | key_wins.py photos <dir>")
