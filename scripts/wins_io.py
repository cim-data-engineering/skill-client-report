#!/usr/bin/env python3
"""Key wins, the part both reports share once the wins are chosen: reading wins.json, the
impact, photo and level calls for its tickets, the photos step (download, contact
sheets, signed links stripped from disk), and each win's impact tag, level, photos,
saving and ticket links at fill time. Choosing the candidates, screening and the
digest stay with each report's key_wins.py.

Imported by the scripts under references/*/actions-and-wins/ only.
"""
import hashlib
import html
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import peak_io as io  # noqa: E402

SEVERITY = ["safety", "reliability", "comfort", "energy", "water", "other"]
SYSTEM_NAMES = {n.lower() for n in io.SYSTEM_ACCOUNTS.values()}
SIGNED = ("link", "preview")    # an attachment's signed links, which never stay on disk
IMAGE = {"image/jpeg": "jpg", "image/jpg": "jpg", "image/png": "png", "image/webp": "webp"}
PER_WIN = 16           # images tiled per win; a ticket can carry dozens of uploads
COMMENT_CHARS = 420
SAVING = re.compile(r"\*\*(.+?)\*\*")   # a saving the win's tickets reference, set bold
UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
STATES = ("fixed", "in_flight")
MIN_SAVING = 200           # a key win states a saving only from this much, in the site's currency
ATTACHMENTS = ["ticket_id", "attachments.attachment_id", "attachments.file_name", "attachments.mime_type",
               "attachments.preview.link.url", "attachments.link.url"]


# ── comments ────────────────────────────────────────────────────────────────
def system(name):
    """Whether a comment's author is CIM's system rather than a person. Comments carry only the
    author's name, so system accounts are known by their names and agents by the name rule."""
    name = " ".join((name or "").split())
    return name.lower() in SYSTEM_NAMES or io.system_account(None, name)


def human(r):
    return [c for c in r.get("comments") or [] if not system(c.get("author_full_name"))]


def clip(text):
    text = " ".join((text or "").split())
    return text[:COMMENT_CHARS].rsplit(" ", 1)[0] + " …" if len(text) > COMMENT_CHARS else text


def saving_text(amount, sym):
    """' · savings $6,800' for the digest, or ' · savings under $200' for less, '' for none."""
    amount = round(amount or 0)
    if amount >= MIN_SAVING:
        return " · savings %s%s" % (sym, "{:,}".format(amount))
    return " · savings under %s%d" % (sym, MIN_SAVING) if amount else ""


# ── the chosen wins ─────────────────────────────────────────────────────────
def load_wins(work, most=None, states=False):
    """wins.json's wins, None before it is written. Each win names its tickets by full id; with
    `states`, each says whether it is fixed or in flight."""
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
    if most and len(wins) > most:
        raise SystemExit("wins.json holds %d wins: %d at most, the strongest across the portfolio" % (len(wins), most))
    for w in wins:
        bad = [t for t in w.get("tickets") or [] if not UUID.match(str(t))]
        if bad or not w.get("tickets"):
            raise SystemExit("wins.json: the win %r needs its tickets as full ticket ids, as the candidate "
                             "pulls print them%s" % (w.get("heading"), ": not %s" % ", ".join(bad) if bad else ""))
        if states and w.get("state", "fixed") not in STATES:
            raise SystemExit("wins.json: the win %r has state %r, which is fixed or in_flight"
                             % (w.get("heading"), w.get("state")))
    return wins


def tickets(wins):
    return list(dict.fromkeys(t for w in wins for t in w["tickets"]))


def evidence(work, wins, scope, site_field=False):
    """The follow-up calls for the chosen wins: their impact and photo calls, then, once those are
    saved, the level call for their equipment. scope is the tickets.tickets filter for the report's
    sites."""
    ids = tickets(wins)
    have = {r.get("ticket_id") for r in work.get("kw/impacts.json").rows} if work.has("kw/impacts.json") else set()
    if not set(ids) <= have or not work.has("kw/attachments.json"):
        fields = ATTACHMENTS[:1] + (["site_id"] if site_field else []) + ATTACHMENTS[1:]
        return [io.call("kw/impacts.json", "search_action_tickets", ticket_ids=ids, limit=50),
                io.gql("kw/attachments.json", "tickets.tickets", dict(scope, ticket_ids=ids, limit=50), fields)]
    eq = list(dict.fromkeys(e for r in work.get("kw/impacts.json").rows if r.get("ticket_id") in ids
                            for e in r.get("equipment_ids") or []))
    have_eq = {r.get("equipment_id") for r in work.get("kw/levels.json").rows} if work.has("kw/levels.json") else set()
    if eq and not set(eq) <= have_eq:
        return [io.gql("kw/levels.json", "platform.equipment", {"equipment_ids": eq, "limit": 100},
                       ["equipment_id", "name", "zone.level.level_name", "zone.level.system"])]
    return []


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


def drop_repeats(plan, files):
    """{pick: path} for each win's downloaded photos, less any whose bytes repeat an earlier one in the same
    win, deleted: one image uploaded to two tickets is one photo. plan is {win: [picks]}."""
    for picks_ in plan.values():
        seen = set()
        for p in [p for p in picks_ if p in files]:
            with open(files[p], "rb") as fh:
                digest = hashlib.sha1(fh.read()).hexdigest()
            if digest in seen:
                os.remove(files.pop(p))
            seen.add(digest)
    return files


def photos(root, wins):
    """Download each win's ticket images and tile them into one numbered contact sheet per win. The
    signed links leave the disk on every path, downloaded, lapsed or failed."""
    nxt = "python3 scripts/report.py next %s" % root
    if wins is None:
        raise SystemExit("No wins.json in %s yet: choose the wins by key-wins.md and write it, then run %s for the "
                         "impact and photo calls, and photos once they are saved." % (root, nxt))
    if not wins:
        print("wins.json names no win, so key wins is left out and there are no photos to fetch. Next: python3 "
              "scripts/report.py fill %s" % root)
        return
    work = io.Work(root)
    if not work.has("kw/attachments.json"):
        raise SystemExit("kw/attachments.json is not saved yet: run %s, make the calls it prints and save them, "
                         "then run photos straight away." % nxt)
    att = {r["ticket_id"]: r.get("attachments") or [] for r in work.get("kw/attachments.json").rows}
    out_dir = os.path.join(root, "kw", "photos")
    os.makedirs(out_dir, exist_ok=True)
    jobs, plan = picks(wins, att, out_dir)
    again = ("Delete %s, run %s for the photo call again, save it and run photos straight away."
             % (work.path("kw/attachments.json"), nxt))
    try:
        if not jobs:
            print("No win's tickets carry an image, so there are no sheets. Next: %s, which prints the level call "
                  "if one is still due or says there are none; then fill." % nxt)
            return
        if not any(urls for _, urls, _ in jobs):
            raise SystemExit("kw/attachments.json holds no photo links: the photos step removes them once it has "
                             "run, since they are signed. " + again)

        def get(job):
            pick, urls, dest = job
            err = None
            for u in urls:
                try:
                    return pick, fetch(u, dest), None
                except Exception as e:             # a lapsed link reads as 403
                    err = e
            return pick, None, err
        with ThreadPoolExecutor(8) as pool:
            got = list(pool.map(get, jobs))
    finally:
        unsign(work)
    failed = [(p, e) for p, d, e in got if not d]
    if failed and len(failed) == len(got):
        raise SystemExit("No photo downloaded (%s). The links lapse twenty minutes after the call. %s Where they "
                         "cannot be fetched from where you are running, the wins go out without photos: say so in "
                         "chat, run %s, then fill." % (failed[0][1], again, nxt))
    sheets = contact_sheets(root, plan, drop_repeats(plan, {p: d for p, d, e in got if d}))
    print("Downloaded %d of %d images. One sheet per win, each tile numbered with its pick:"
          % (len(got) - len(failed), len(got)))
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
        raise SystemExit("photos need Pillow: pip install pillow")
    out = []
    tile, cols = 320, 4
    for k, picks_ in plan.items():
        picks_ = [p for p in picks_ if p in files]
        if not picks_:
            continue
        rows = (len(picks_) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * tile, rows * (tile + 28)), "white")
        draw = ImageDraw.Draw(sheet)
        for i, p in enumerate(picks_):
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
def impacts(work):
    return {r["ticket_id"]: r for r in work.get("kw/impacts.json").rows}


def levels(work):
    """{equipment id: level name}, leaving out PEAK's system placeholder level."""
    out = {}
    if work.has("kw/levels.json"):
        for r in work.get("kw/levels.json").rows:
            lv = ((r.get("zone") or {}).get("level") or {})
            if lv.get("level_name") and not lv.get("system"):
                out[r["equipment_id"]] = lv["level_name"]
    return out


def small_saving(text):
    """True when a figure a win sets bold, "$67" or "$1.2k", is under MIN_SAVING."""
    m = re.search(r"(\d[\d,]*(?:\.\d+)?)\s*(k|thousand|m|million)?\b", text, re.I)
    scale = {"k": 1e3, "thousand": 1e3, "m": 1e6, "million": 1e6}.get((m.group(2) or "").lower(), 1) if m else 1
    return bool(m) and float(m.group(1).replace(",", "")) * scale < MIN_SAVING


def win(work, w, imp, level_of, tz, escape_titles):
    """One chosen win for the bundle: its impact tag, the level its equipment serves, its photos, its
    words with a saving set bold, and its ticket links. Returns (win, chat lines)."""
    chat, tags = [], []
    for t in w["tickets"]:
        row = imp.get(t)
        if not row:
            raise SystemExit("kw/impacts.json has no row for %s: make the calls report.py next prints" % t)
        real = [i for i in (row.get("impacts") or []) if i in SEVERITY and i != "other"]
        tags += real
        if not real:
            chat.append("Ticket %s, \"%s\", has no impact set in PEAK, so its win takes the tag of its other "
                        "tickets or Other. Set the impact in PEAK and re-run." % (t[:8], row.get("title")))
    names = []
    for t in w["tickets"]:
        for e in imp[t].get("equipment_ids") or []:
            if level_of.get(e) and level_of[e] not in names:
                names.append(level_of[e])
    pics = []
    shelf = os.path.join(work.root, "kw", "photos")
    for p in w.get("photos") or []:
        p = {"pick": p} if isinstance(p, str) else dict(p)
        pick = p.pop("pick", None)
        hit = [f for f in os.listdir(shelf) if f.split(".")[0] == pick] if pick and os.path.isdir(shelf) else []
        if not hit:
            raise SystemExit("wins.json: photo %r is not on disk: run key_wins.py photos first" % pick)
        pics.append(dict(p, src=os.path.join("kw", "photos", hit[0])))
    # a saving's figure shows from MIN_SAVING; a smaller one drops out, its words kept
    body = re.sub(r"(?:\s+of)?\s*\*\*(.+?)\*\*", lambda m: "" if small_saving(m.group(1)) else m.group(0), w["body"])
    # the model's words go in as text, with a saving it marked ** set bold
    body = SAVING.sub(r"<strong>\1</strong>", html.escape(body, quote=False))
    title = lambda t: (imp[t].get("title") or "").strip()
    titles = Counter(title(t) for t in w["tickets"])
    ref = lambda t: title(t) + (" (raised %s)" % io.day_short(io.local_day(imp[t]["created_at"], tz))
                                if titles[title(t)] > 1 and imp[t].get("created_at") else "")
    out = {"impact": min(tags, key=SEVERITY.index) if tags else "other",
           "heading": html.escape(w["heading"], quote=False), "body": body,
           "refs": [{"url": imp[t]["ticket_link"], "title": html.escape(ref(t), quote=False) if escape_titles else ref(t)}
                    for t in w["tickets"]]}
    if names:
        out["level"] = names[0] if len(names) == 1 else names
    if pics:
        out["photos"] = pics
    return out, chat
