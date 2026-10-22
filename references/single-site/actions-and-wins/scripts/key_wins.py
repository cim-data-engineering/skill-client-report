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
import html
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "scripts"))
import peak_io as io  # noqa: E402

SEVERITY = ["safety", "reliability", "comfort", "energy", "water", "other"]
SYSTEM_NAMES = {n.lower() for n in io.SYSTEM_ACCOUNTS.values()}
BULK_RUN, BULK_GAP = 3, 120     # three or more closures, each within two minutes of the one before: a bulk close-out
SIGNED = ("link", "preview")    # an attachment's signed links, which never stay on disk
IMAGE = {"image/jpeg": "jpg", "image/jpg": "jpg", "image/png": "png", "image/webp": "webp"}
PER_WIN = 16           # images tiled per win; a ticket can carry dozens of uploads
COMMENT_CHARS = 420
SAVING = re.compile(r"\*\*(.+?)\*\*")   # a saving the win's tickets reference, set bold
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
def person(name):
    """Whether a comment's author is a person. Comments carry only the author's name, so CIM's
    system accounts are known by their names in peak_io's list, and agents by the name rule."""
    name = " ".join((name or "").split())
    return name.lower() not in SYSTEM_NAMES and not io.system_account(None, name)


def human(r):
    return [c for c in r.get("comments") or [] if person(c.get("author_full_name"))]


def when(ts):
    t = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    return t if t.tzinfo else t.replace(tzinfo=timezone.utc)


def bulk(rows):
    """Ticket ids closed in a bulk close-out: BULK_RUN or more closures, each within BULK_GAP
    seconds of the one before."""
    out, run = set(), []
    for r in sorted((r for r in rows if r.get("resolved_at")), key=lambda r: when(r["resolved_at"])) + [None]:
        if r and run and (when(r["resolved_at"]) - when(run[-1]["resolved_at"])).total_seconds() <= BULK_GAP:
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
        if r.get("resolved_at") and r.get("created_at", "")[:19] == r["resolved_at"][:19]:
            why["created and resolved the same moment"] += 1
        elif r.get("resolved_at") and r.get("ticket_id") in closed_together:
            why["bulk close-out, three or more closed each within two minutes of the last"] += 1
        elif not human(r):
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
    day = lambda ts: (when(ts).astimezone(tz).date().isoformat() if tz else ts[:10]) if ts else "?"
    print("%d candidates, %d left after screening. Screened out: %s." % (
        len(rows), len(keep), "; ".join("%d %s" % (n, w) for w, n in why.items()) or "nothing"))
    if not root:
        print("Dates are UTC. Pass the report's folder first, digest <dir> <file>, for the site's own dates "
              "and currency.")
    for r in sorted(keep, key=lambda r: -len(human(r))):
        state = ("closed %s" % day(r.get("resolved_at"))) if r.get("resolved_at") else "open"
        amount = round(r.get("savings") or 0)
        saved = (" · savings %s%s" % (sym, "{:,}".format(amount)) if amount >= io.MIN_SAVING
                 else " · savings under %s%d" % (sym, io.MIN_SAVING) if amount else "")
        print("\n[%s] %s, raised %s%s · %s" % (r["ticket_id"], state, day(r.get("created_at")), saved,
                                              (r.get("summary") or "").strip()))
        for k in ("description", "solution"):
            if clip(r.get(k)):
                print("  %s: %s" % (k, clip(r.get(k))))
        for c in sorted(human(r), key=lambda c: c.get("created_at") or ""):
            print("  - %s, %s: %s" % (day(c.get("created_at")), c.get("author_full_name") or "?", clip(c.get("text"))))


def clip(text):
    text = " ".join((text or "").split())
    return text[:COMMENT_CHARS].rsplit(" ", 1)[0] + " …" if len(text) > COMMENT_CHARS else text


# ── the chosen wins ─────────────────────────────────────────────────────────
UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")


def load_wins(work):
    path = os.path.join(work.root, "wins.json")
    if not os.path.isfile(path):
        return None
    try:
        with open(path, encoding="utf-8") as fh:
            wins = json.load(fh)
    except ValueError as e:
        raise SystemExit("wins.json is not valid JSON (%s): write the chosen wins as a list, or [] when none "
                         "qualified" % e)
    if not isinstance(wins, list) or not all(isinstance(w, dict) for w in wins):
        raise SystemExit("wins.json holds a list of wins, one object each, or [] when none qualified")
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
    return {}


# ── photos ──────────────────────────────────────────────────────────────────
def fetch(url, dest):
    req = urllib.request.Request(url, headers={"User-Agent": "client-report"})
    with urllib.request.urlopen(req, timeout=60) as r, open(dest, "wb") as fh:
        fh.write(r.read())
    return dest


def links(a):
    """An attachment's download links, the original first."""
    return [u for u in ((a.get("link") or {}).get("url"), ((a.get("preview") or {}).get("link") or {}).get("url")) if u]


def identity(a):
    """What tells one attachment from another: its id, else its link without the signature. Never
    the file name, which screenshots share ("image.png")."""
    if a.get("attachment_id"):
        return a["attachment_id"]
    return urllib.parse.urlsplit(links(a)[0]).path if links(a) else None


def picks(wins, att, out_dir):
    """(download jobs, {win: picks}): each win's image attachments, one copy of each and PER_WIN
    at most, numbered w<win>-<n> in the order the tickets carry them."""
    jobs, plan = [], {}
    for k, w in enumerate(wins, 1):
        seen, n = set(), 0
        for t in w["tickets"]:
            for a in att.get(t, []):
                ext = IMAGE.get((a.get("mime_type") or "").lower())
                key = identity(a)
                if not ext or key is None or key in seen or n >= PER_WIN:
                    continue
                seen.add(key)
                n += 1
                pick = "w%d-%d" % (k, n)
                jobs.append((pick, links(a), os.path.join(out_dir, "%s.%s" % (pick, ext))))
                plan.setdefault(k, []).append(pick)
    return jobs, plan


def unsign(work):
    """Rewrite kw/attachments.json without its signed links, which carry security tokens and lapse
    anyway: each attachment keeps everything else, its id, name and type. Nothing after the photos
    reads the links."""
    saved = work.get("kw/attachments.json")
    rows = [dict(r, attachments=[{k: v for k, v in a.items() if k not in SIGNED} for a in r.get("attachments") or []])
            for r in saved.rows]
    out = {"results": rows}
    if saved.total is not None:
        out["pagination"] = {"total": saved.total, "has_more": saved.has_more}
    with open(work.path("kw/attachments.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False)


def photos(root):
    work = io.Work(root)
    wins = load_wins(work)
    if wins is None:
        raise SystemExit("No wins.json in %s yet: choose the wins by key-wins.md and write it, then run python3 "
                         "scripts/report.py next %s for the impact and photo calls, and photos once they are saved."
                         % (root, root))
    if not wins:
        print("wins.json names no win, so key wins is left out and there are no photos to fetch. Next: python3 "
              "scripts/report.py fill %s" % root)
        return
    if not work.has("kw/attachments.json"):
        raise SystemExit("kw/attachments.json is not saved yet: run python3 scripts/report.py next %s, make the calls "
                         "it prints and save them, then run photos straight away." % root)
    att = {r["ticket_id"]: r.get("attachments") or [] for r in work.get("kw/attachments.json").rows}
    out_dir = os.path.join(root, "kw", "photos")
    os.makedirs(out_dir, exist_ok=True)
    jobs, plan = picks(wins, att, out_dir)
    nxt = "python3 scripts/report.py next %s" % root
    again = ("Delete %s, run %s for the photo call again, save it and run photos straight away."
             % (work.path("kw/attachments.json"), nxt))

    if not jobs:
        unsign(work)
        print("No win's tickets carry an image, so there are no sheets. Next: %s, which prints the level call if "
              "one is still due or says there are none; then fill." % nxt)
        return
    if not any(urls for _, urls, _ in jobs):
        raise SystemExit("kw/attachments.json holds no photo links: the photos step removes them once it has run, "
                         "since they are signed. " + again)

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
    unsign(work)                                   # downloaded or lapsed, the signed links leave the disk
    failed = [(p, e) for p, d, e in got if not d]
    if failed and len(failed) == len(got):
        raise SystemExit("No photo downloaded (%s). The links lapse twenty minutes after the call. %s Where they "
                         "cannot be fetched from where you are running, the wins go out without photos: say so in "
                         "chat, run %s, then fill." % (failed[0][1], again, nxt))
    sheets = contact_sheets(root, plan, io.drop_repeats(plan, {p: d for p, d, e in got if d}))
    print("Downloaded %d of %d images. One sheet per win, each tile numbered with its pick:" % (len(got) - len(failed), len(got)))
    for k, s in sheets:
        print("  win %d (%s): %s" % (k, wins[k - 1].get("heading", "")[:60], s))
    if failed:
        print("Not downloaded: %s. To try them again: %s" % (", ".join(p for p, e in failed), again))
    print("Look at each sheet, then add the picks to that win's photos in wins.json, in story order, e.g. "
          '"photos": ["w1-2", {"pick": "w1-4", "focus": [0.7, 0.4], "zoom": 2}]. A win with no good photo gets none. '
          "Next: %s, which prints the level call if one is still due or says there are none; then fill." % nxt)


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
        # a saving's figure shows from MIN_SAVING; a smaller one drops out, its words kept
        body = re.sub(r"(?:\s+of)?\s*\*\*(.+?)\*\*", lambda m: "" if io.small_saving(m.group(1)) else m.group(0), w["body"])
        # the model's words go in as text, with a saving it marked ** set bold
        body = SAVING.sub(r"<strong>\1</strong>", html.escape(body, quote=False))
        titles = Counter((imp[t].get("title") or "").strip() for t in w["tickets"])
        ref = lambda t: (imp[t].get("title") or "").strip() + (
            " (raised %s)" % io.day_short(io.local_day(imp[t]["created_at"], ctx["site"].get("timezone"))) if titles[(imp[t].get("title") or "").strip()] > 1
            and imp[t].get("created_at") else "")
        win = {"impact": impact, "heading": html.escape(w["heading"], quote=False), "body": body,
               "refs": [{"url": imp[t]["ticket_link"], "title": html.escape(ref(t), quote=False)} for t in w["tickets"]]}
        if names:
            win["level"] = names[0] if len(names) == 1 else names
        if pics:
            win["photos"] = pics
        out.append(win)
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
        photos(sys.argv[2])
    else:
        sys.exit("usage: key_wins.py digest <response file> [...] | key_wins.py photos <dir>")
