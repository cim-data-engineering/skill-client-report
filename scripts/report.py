#!/usr/bin/env python3
"""Drive a client report from the section scripts, so the model only makes the
PEAK calls and picks and writes the key wins.

    python3 scripts/report.py plan   <dir> --site <dir>/site.json --author "Full Name" [--sections ...]
    python3 scripts/report.py plan   <dir> --sites <dir>/sites.json [...] --client "Name" --author "Full Name"
                                     [--client-logo <file>] [--site-ids ...]
    python3 scripts/report.py next   <dir>
    python3 scripts/report.py verify <dir>
    python3 scripts/report.py bundle <dir>
    python3 scripts/report.py fill   <dir> [--out <file.html>]

plan    Fixes the report's windows from today in site time and prints every call the
        sections need, each with the file under <dir>/peak/ its response is saved as.
        --site plans the single-site report, its quarter and the chosen sections;
        --sites plans the portfolio leaderboard for the last complete month over the
        active sites in those search_sites pages, with every section.
next    Checks every printed call was saved and reads back as a PEAK response, then
        prints the follow-up calls the responses call for (paging, a single-level
        site's zones, run hours history, key win evidence once wins.json exists), or
        says there are none.
verify  Reads back every saved response: each must parse as a PEAK response, hold
        the rows its pagination says it should, and name only the report's sites.
        A response copied by hand that lost or mistyped rows shows up here.
bundle  Builds every figure, row, series, link and note into <dir>/data.json, and
        prints anything to say in chat at hand-over, then the next step.
fill    Merges <dir>/wins.json into the bundle, fills the report and runs the
        check.

Each section is a folder under references/<mode>/ holding its reference and its
scripts; the registry below names each report's sections, their folders and order. A module exposes
calls(ctx), more(ctx, work) and build(ctx, work, shared). plan.json names the mode, and holds its
paths relative to the report folder, so a folder can be moved or copied whole.
"""
import argparse
import glob
import importlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import peak_io as io  # noqa: E402

# The four choices the section prompt offers, and the report sections each one turns on.
OPTIONS = {"equipment-health": ("Equipment health", ["equipment-health"]),
           "indoor-environment": ("Indoor environment", ["indoor-environment"]),
           "actions-and-wins": ("Actions and key wins", ["alerts-resolved", "key-wins"]),
           "run-hours": ("Equipment run hours", ["run-hours"])}
# report section -> (folder under references/, module in its scripts/)
MODULES = {"overview": ("single-site/overview", "overview"),
           "equipment-health": ("single-site/equipment-health", "equipment_health"),
           "indoor-environment": ("single-site/indoor-environment", "indoor_environment"),
           "alerts-resolved": ("single-site/actions-and-wins", "alerts_resolved"),
           "key-wins": ("single-site/actions-and-wins", "key_wins"),
           "run-hours": ("single-site/run-hours", "run_hours"),
           "sustainability-ratings": ("single-site/sustainability-ratings", "sustainability_ratings")}
ORDER = ["sustainability-ratings", "equipment-health", "indoor-environment", "alerts-resolved", "key-wins",
         "run-hours"]
# Sections the prompt never offers. Every report fetches them, and each drops itself
# when the site has nothing to show.
AUTO = ["sustainability-ratings"]
# The operational impact rows the sections own, in the order the frame shows them.
IMPACT_ORDER = ["equipment-health-score", "thermal-comfort", "automated-checks", "labour-cost-avoided",
                "faults-resolved"]

# What sections hand on to each other, through `shared`, by the figure's name; no section
# names another, and each builds after every section whose figures it takes.
#   site_facts / facts  the site's, or each site's, platform row, seeded before any section builds
#   thermal_zones       zone points on the levels that scored (zones_configured: every configured point)
#   rankings            [{label, anchor | links, window: "month" | "quarter", now, start, dp, unit}], one board
#                       each: now on the leaderboard month or the quarter ending on it, start on the window
#                       last month's leaderboard ranked; each name jumps to the anchor, or opens its own link;
#                       an optional note joins the date line
#   team_rankings       [{label, links, window, noun, unit, names, meta, tiles, now, start, shoutouts}], one
#                       board each, as rankings but over the companies or people holding the work, keyed by
#                       company or person; tiles each one's company and its logo, shoutouts each person's
#                       {first, email, site} for the leader's shoutout
#   partial             names of the volume figures shown that run short over a month to date, present
#                       once any section shows the month to date; single-site only
#   trend_start         [first month kept], each score section's, for a site that went live inside the
#                       windows: the actions chart starts where the earliest of them does; single-site only
#   period_start        [first month kept], each score section's: the masthead's reporting period starts at
#                       the earliest; single-site only
#   live_since          [{month, day}], each score section's go-live, for the masthead; single-site only
#   nothing_resolved    True when the actions section dropped for want of anything resolved, so key wins
#                       drops too; single-site only
#   shown_sites         {site ids} each section shows data for: the masthead's Sites count; portfolio only
# A section that has nothing to show returns {"drop": True}; the report drops it under its registry name.
# A figure the plan needs, before anything is fetched, a module names in HANDS_ON: plan.json
# lists them as handed_on.

# The portfolio report: every section, no prompt. Each drops itself when PEAK has nothing
# for it. PORTFOLIO_ORDER is the build order.
PORTFOLIO_MODULES = {"overview": ("portfolio-leaderboard/overview", "overview"),
                     "site-leaderboard": ("portfolio-leaderboard/site-leaderboard", "site_leaderboard"),
                     "team-leaderboard": ("portfolio-leaderboard/team-leaderboard", "team_leaderboard"),
                     "equipment-health": ("portfolio-leaderboard/equipment-health", "equipment_health"),
                     "indoor-environment": ("portfolio-leaderboard/indoor-environment", "indoor_environment"),
                     "actions-resolved": ("portfolio-leaderboard/actions-and-wins", "actions_resolved"),
                     "open-actions": ("portfolio-leaderboard/actions-and-wins", "open_actions"),
                     "key-wins": ("portfolio-leaderboard/actions-and-wins", "key_wins"),
                     "sustainability-ratings": ("portfolio-leaderboard/sustainability-ratings",
                                                "sustainability_ratings")}
PORTFOLIO_ORDER = ["equipment-health", "indoor-environment", "actions-resolved", "sustainability-ratings",
                   "open-actions", "key-wins", "site-leaderboard", "team-leaderboard", "overview"]
MODES = {"single-site": {"modules": MODULES}, "portfolio": {"modules": PORTFOLIO_MODULES}}


def mode_of(ctx):
    return ctx["mode"]


def module(section, mode="single-site"):
    folder, name = MODES[mode]["modules"][section]
    path = os.path.join(ROOT, "references", folder, "scripts")
    if mode != "single-site":
        # loaded by path under a name of its own, so no module of the other mode can shadow it
        key = "%s_%s" % (mode, name)
        if key not in sys.modules:
            spec = importlib.util.spec_from_file_location(key, os.path.join(path, name + ".py"))
            sys.modules[key] = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(sys.modules[key])
        return sys.modules[key]
    if path not in sys.path:
        sys.path.insert(0, path)
    return importlib.import_module(name)


def check_registry(mode):
    """Stop where the registry and the scaffold disagree on a section's name: each section built has its
    parts in build_report, and every conditional block in the scaffold names a section the report knows."""
    import build_report as br
    if mode == "portfolio":
        order, modules, parts, ref = PORTFOLIO_ORDER, PORTFOLIO_MODULES, br.PORTFOLIO["section_parts"], br.PORTFOLIO["ref"]
        named = set()
    else:
        order, modules, parts, ref = ["overview"] + ORDER, MODULES, br.SECTION_PARTS, br.REF
        named = {s for owners in br.PART_IF.values() for s in owners} | set(AUTO) | {
            s for _, sections in OPTIONS.values() for s in sections}
    built = set(order) - {"overview"}
    with open(ref, encoding="utf-8") as fh:
        named |= {n.strip() for line in fh for m in [br.IF_RE.match(line)] if m for n in m.group(1).split(",")}
    problems = (["%s is in the order but not the modules, or the reverse" % s for s in set(order) ^ set(modules)]
                + ["%s has no parts in build_report" % s for s in built - set(parts)]
                + ["build_report has parts for %s, which the report does not build" % s for s in set(parts) - built]
                + ["%s is named in the scaffold or the section options but is not a section" % s for s in named - built])
    if problems:
        sys.exit("The %s registry disagrees with itself: %s." % (mode, "; ".join(sorted(problems))))


def active(ctx):
    if mode_of(ctx) == "portfolio":
        return list(PORTFOLIO_ORDER)
    return ["overview"] + [s for s in ORDER if s in ctx["sections"]]


def show(calls, start):
    for i, c in enumerate(calls, start):
        print("%3d. %s %s" % (i, c["tool"], "(read, never saved)" if c.get("read") else "-> " + c["file"]))
        print("     " + json.dumps(c["args"], separators=(", ", ": ")))


def save_rule(root):
    return ("Save each response under %s/peak/ as the file named: an offloaded one by copying the file you "
            "were handed (cp), an inline one by writing it to its file exactly as returned, one file per "
            "response. Every response to save holds counts, scores, ids and type, level or company names "
            "only." % root)


PORTFOLIO_SAVE = ("Save each response under %s/peak/ as the file named: an offloaded one by copying the file you "
                  "were handed (cp), an inline one by writing it to its file exactly as returned, one file per "
                  "response. Every response to save holds counts, scores, ids, and the names and titles PEAK "
                  "keeps on its records: never what anyone wrote on a ticket.")


READ_RULE = ("Read these where they come back and never save them: they carry what people wrote on the "
             "tickets, and the files hold none of that. One that comes back offloaded as a file prints "
             "screened and compact with: python3 references/single-site/actions-and-wins/scripts/key_wins.py digest %s <that file>")


CLOSING = ("The %s leaderboard is built on %s, the day the month closed, so its scores may not have settled. "
           "Build it again from the 2nd before it is sent.")


PORTFOLIO_READ_RULE = ("Read these where they come back and never save them. They carry each candidate's title, "
                       "site, priority, saving and who commented, enough to shortlist from. A pull whose pagination "
                       "says has_more is read on with the same call at the next start_index. One that comes back "
                       "offloaded as a file prints screened and ranked, each candidate with its site, with: python3 "
                       "references/portfolio-leaderboard/actions-and-wins/scripts/key_wins.py digest %s <that file> "
                       "[...]. One read inline is screened by eye, by the patterns in key-wins.md under Data.")


# ── plan ────────────────────────────────────────────────────────────────────
def cmd_plan(a):
    if a.sites:
        return plan_portfolio(a)
    check_registry("single-site")
    site_rows = io.read(a.site).rows
    if a.site_id:
        site_rows = [r for r in site_rows if r.get("site_id") == a.site_id]
    if not site_rows:
        sys.exit("%s holds no site%s" % (a.site, " %d" % a.site_id if a.site_id else ""))
    site = site_rows[0]
    if len(site_rows) > 1 and not a.site_id and (site.get("score") or 1) < 0.9:
        sys.exit("%s holds %d sites; pass --site-id" % (a.site, len(site_rows)))
    picked = [s.strip() for s in (a.sections or "all").split(",") if s.strip()]
    if picked == ["all"]:
        picked = list(OPTIONS)
    unknown = [s for s in picked if s not in OPTIONS and s not in ORDER]
    if unknown:
        sys.exit("unknown section %s; choose from %s" % (", ".join(unknown), ", ".join(OPTIONS)))
    sections = [s for o in picked for s in (OPTIONS[o][1] if o in OPTIONS else [o])] + AUTO
    today = io.d(a.today) if a.today else datetime.now(io.zone(site.get("timezone"))).date()
    root = os.path.abspath(a.dir)
    os.makedirs(os.path.join(root, "peak"), exist_ok=True)
    ctx = dict(io.windows(today), mode="single-site", site=site, author=a.author,
               sections=[s for s in ORDER if s in sections], dir=root,
               site_file=os.path.relpath(os.path.abspath(a.site), root), hours=a.hours, brand=brand())
    ctx["handed_on"] = sorted({f for s in ctx["sections"] for f in getattr(module(s), "HANDS_ON", [])})
    calls = write_plan(root, ctx, [c for s in active(ctx) for c in module(s).calls(ctx)])
    save = [c for c in calls if not c.get("read") and not os.path.isfile(os.path.join(root, "peak", c["file"]))]
    read = [c for c in calls if c.get("read")]
    print("%s: quarter %s, trends %s, issued %s%s." % (
        site["site_name"], io.period(ctx["quarter"][0], ctx["through"], True),
        io.span(ctx["trend_months"][0], ctx["trend_months"][-1], True), io.day_short(ctx["today"]),
        io.and_to_date(ctx, "; both windows close on ")))
    print("Sections: %s." % ", ".join(OPTIONS[o][0] if o in OPTIONS else o for o in picked))
    print("\n%s to save. Make them all in one parallel batch, each exactly as printed: the tool, then its "
          "arguments. %s Then run: python3 scripts/report.py next %s\n" % (io.plural(len(save), "call"), save_rule(a.dir),
                                                                           a.dir))
    show(save, 1)
    if read:
        print("\nIn the same batch, %d to read: the key win candidates. %s\n" % (len(read), READ_RULE % a.dir))
        show(read, len(save) + 1)


def plan_portfolio(a):
    import portfolio_io as pio
    check_registry("portfolio")
    sites, seen, saved = [], set(), set()
    for r in [r for f in a.sites for r in io.read(f).rows]:
        sid = r.get("site_id")
        saved.add(sid)
        if sid in seen or r.get("is_active") is False or (a.site_ids and sid not in a.site_ids):
            continue
        seen.add(sid)
        sites.append({k: r.get(k) for k in ("site_id", "site_name", "state", "country", "city", "timezone",
                                             "site_link")})
    unknown = [i for i in a.site_ids or [] if i not in saved]
    if unknown:
        print("Not in %s, so left out: --site-ids %s." % (", ".join(a.sites), " ".join(str(i) for i in unknown)))
    if not sites:
        sys.exit("%s holds no active site%s. Say so in chat, and ask for the client or sites the report is for."
                 % (", ".join(a.sites), " among --site-ids" if a.site_ids else ""))
    if len(sites) == 1:
        sid = sites[0]["site_id"]
        sys.exit("%s holds one active site, %s, so it gets the single-site report. Call search_sites(site_ids:[%d], "
                 "include_working_hours:true), save it as %s/site.json, then: python3 scripts/report.py plan %s "
                 "--site %s/site.json --site-id %d --author \"%s\" (with --sections as the section question settles)"
                 % (", ".join(a.sites), sites[0]["site_name"].strip(), sid, a.dir, a.dir, a.dir, sid, a.author))
    logo = os.path.abspath(a.client_logo) if a.client_logo else None
    if logo and not os.path.isfile(logo):
        sys.exit("client logo not found: %s" % a.client_logo)
    if logo and not client_logo_ok(logo):
        sys.exit("%s is a logo shipped with a skill (a sample or a brand overlay's), not the client's. The client "
                 "logo slot takes only a file the user supplied; plan again without --client-logo." % a.client_logo)
    today = io.d(a.today) if a.today else pio.today(sites)
    root = os.path.abspath(a.dir)
    os.makedirs(os.path.join(root, "peak"), exist_ok=True)
    ctx = dict(pio.windows(today), mode="portfolio", sites=sites, client=a.client.strip(),
               client_logo=os.path.relpath(logo, root) if logo else None,
               author=a.author, sections=list(PORTFOLIO_ORDER), dir=root, brand=brand())
    calls = write_plan(root, ctx, [c for s in active(ctx) for c in module(s, "portfolio").calls(ctx)])
    save = [c for c in calls if not c.get("read") and not os.path.isfile(os.path.join(root, "peak", c["file"]))]
    read = [c for c in calls if c.get("read")]
    print("%s portfolio: %d sites, the %s leaderboard. Scores and actions resolved %s, key wins %s, issued %s."
          % (ctx["client"], len(sites), pio.month_name(ctx), pio.reporting_period(ctx, True),
             pio.wins_period(ctx, True), io.day_short(ctx["today"])))
    if pio.closing(ctx):
        print("Say in chat now: " + CLOSING % (pio.month_name(ctx), io.day_long(ctx["today"])))
    print("Sections: every one with data. Each site's dates are its own local calendar.")
    print("\n%s to save. Make them in parallel batches of about twenty, each exactly as printed: the tool, "
          "then its arguments. %s Then run: python3 scripts/report.py next %s\n"
          % (io.plural(len(save), "call"), PORTFOLIO_SAVE % a.dir, a.dir))
    show(save, 1)
    if read:
        print("\nAlongside them, %d to read: the key win candidates. %s\n" % (len(read), PORTFOLIO_READ_RULE % a.dir))
        show(read, len(save) + 1)


def write_plan(root, ctx, calls):
    """Write plan.json and calls.json, clearing first what an earlier plan in this folder left that no
    longer holds. Returns the calls the folder now plans."""
    calls, cleared = replan(root, calls, ctx["today"])
    if cleared:
        print("Cleared %s an earlier plan in this folder left that no longer hold: %s."
              % (io.plural(len(cleared), "file"), ", ".join(cleared[:12]) + (" ..." if len(cleared) > 12 else "")))
    with open(os.path.join(root, "plan.json"), "w") as fh:
        json.dump(dict(ctx, dir="."), fh, indent=1)
    with open(os.path.join(root, "calls.json"), "w") as fh:
        json.dump(calls, fh, indent=1)
    folders(root, calls)
    return calls


# Built from the saved responses, so a changed plan clears them: the bundle, the filled report and
# its tiles, and run hours' plan and aggregate.
DERIVED = ["data.json", "report-data.json", "tiles", "*.html", "peak/runhours/plan.json", "peak/runhours/agg.json",
           "peak/runhours/earlier.json", "peak/runhours/last.json", "peak/runhours/earlier"]
# Chosen from the key win candidates, so new candidates clear them.
CHOSEN = ["wins.json", "shortlist.json", "kw"]


def replan(root, calls, today):
    """(the calls the folder plans, the files cleared). Planning a folder again on the same issue date
    with the same calls keeps every saved response and follow-up. Otherwise each saved response whose
    call changed or is no longer planned goes, follow-ups included, with everything built from them; and
    where the key win candidates changed, so do the wins chosen from them. A new issue date clears every
    response, since a count as at the issue date answers differently on another day with the same call."""
    path = os.path.join(root, "calls.json")
    if not os.path.isfile(path):
        return calls, []
    with open(path, encoding="utf-8") as fh:
        old = json.load(fh)
    with open(os.path.join(root, "plan.json"), encoding="utf-8") as fh:
        same_day = json.load(fh).get("today") == today
    was = {c["file"]: c for c in old}
    if same_day and all(was.get(c["file"]) == c for c in calls):
        return old, []
    planned = {c["file"]: c for c in calls}
    gone = [c for c in old if not same_day or planned.get(c["file"]) != c]
    cleared = [c["file"] for c in gone if not c.get("read") and os.path.isfile(os.path.join(root, "peak", c["file"]))]
    for f in cleared:
        os.remove(os.path.join(root, "peak", f))
    for pattern in DERIVED + (CHOSEN if any(c.get("read") for c in gone) else []):
        for p in glob.glob(os.path.join(root, pattern)):
            shutil.rmtree(p) if os.path.isdir(p) else os.remove(p)
            cleared.append(os.path.relpath(p, root))
    return calls, cleared


def folders(root, calls):
    """Every folder under peak/ the calls save into, so a response can be copied straight to its file."""
    for c in calls:
        if not c.get("read"):
            os.makedirs(os.path.dirname(os.path.join(root, "peak", c["file"])), exist_ok=True)


def client_logo_ok(path):
    """False for a logo that ships with a skill: anything inside this skill, or inside a brand overlay
    (a folder holding a BRAND.md). Those are sample and partner logos, never a client's."""
    path = os.path.realpath(path)
    if path.startswith(os.path.realpath(ROOT) + os.sep):
        return False
    d = os.path.dirname(path)
    while d and d != os.path.dirname(d):
        if os.path.isfile(os.path.join(d, "BRAND.md")):
            return False
        d = os.path.dirname(d)
    return True


def brand():
    """BRAND.md's identity: name / service-name replace the masthead's CIM defaults. A value may be quoted
    and carry a trailing # comment; the file may have CRLF line ends or a byte-order mark."""
    path = os.path.join(ROOT, "BRAND.md")
    text = open(path, encoding="utf-8-sig").read().replace("\r\n", "\n") if os.path.isfile(path) else ""
    m = re.match(r"---\n(.*?)\n---", text, re.S)
    head = m.group(1) if m else ""

    def get(key):
        found = re.search(r"^%s:\s*(\S.*?)\s*$" % key, head, re.M)
        if not found:
            return None
        value = re.sub(r"\s+#.*$", "", found.group(1)).strip()
        return value[1:-1].strip() if len(value) > 1 and value[0] == value[-1] and value[0] in "\"'" else value
    return {"name": get("name") or "CIM", "service": get("service-name") or "Data Driven Operations"}


# ── next ────────────────────────────────────────────────────────────────────
def cmd_next(a):
    work = io.Work(a.dir)
    with open(os.path.join(work.root, "calls.json")) as fh:
        calls = json.load(fh)
    missing = [c for c in calls if not c.get("read") and not work.has(c["file"])]
    if missing:
        print("Not saved yet, so make these again exactly as printed: %s\n" % (
            PORTFOLIO_SAVE % a.dir if mode_of(work.ctx) == "portfolio" else save_rule(a.dir)))
        show(missing, 1)
        sys.exit(1)
    problems = verify(work, calls)
    if problems:
        sys.exit("Saved, but not as PEAK returned it:\n  %s\nSave each again from the tool's output: copy an offloaded "
                 "file with cp, write an inline one exactly as returned. Then run next again." % "\n  ".join(problems))
    mode = mode_of(work.ctx)
    new = [c for s in active(work.ctx) for c in module(s, mode).more(work.ctx, work)]
    if not new:
        print("No more calls. Next: " + next_step(work, a.dir))
        return
    have = {c["file"] for c in calls}
    calls += [c for c in new if c["file"] not in have]
    with open(os.path.join(work.root, "calls.json"), "w") as fh:
        json.dump(calls, fh, indent=1)
    folders(work.root, new)
    read = [c for c in new if c.get("read")]
    new = [c for c in new if not c.get("read")]
    if new:
        print("%s more, in one parallel batch, each exactly as printed. %s Then run next again.\n"
              % (io.plural(len(new), "call"), PORTFOLIO_SAVE % a.dir if mode == "portfolio" else save_rule(a.dir)))
        show(new, 1)
    if read:
        print("%s%d to read, never saved: the shortlist in full. Read it where it comes back; one that comes back "
              "offloaded prints compact with: python3 references/portfolio-leaderboard/actions-and-wins/scripts/"
              "key_wins.py digest %s <that file> --top 0. Choose the wins from it and write %s/wins.json, then run "
              "next again.\n" % ("\n" if new else "", len(read), a.dir, a.dir))
        show(read, len(new) + 1)


def next_step(work, d):
    """What follows once no call is due: bundle until it has run, then the key wins where the bundle
    kept them, then fill."""
    path = os.path.join(work.root, "data.json")
    if not os.path.isfile(path):
        return "python3 scripts/report.py bundle %s" % d
    with open(path, encoding="utf-8") as fh:
        sections = json.load(fh)["sections"].split(",")
    folder = "portfolio-leaderboard" if mode_of(work.ctx) == "portfolio" else "single-site"
    has = lambda f: os.path.isfile(os.path.join(work.root, f))
    if "key-wins" not in sections or no_wins(work.root):
        return "python3 scripts/report.py fill %s" % d
    if not has("wins.json"):
        if folder == "portfolio-leaderboard" and not has("shortlist.json"):
            return ("shortlist the key win candidates and write %s/shortlist.json, by references/%s/actions-and-wins/"
                    "key-wins.md, then run python3 scripts/report.py next %s" % (d, folder, d))
        return ("choose the key wins and write %s/wins.json, by references/%s/actions-and-wins/key-wins.md, then run "
                "python3 scripts/report.py next %s" % (d, folder, d))
    if os.path.isdir(os.path.join(work.root, "kw", "photos")):
        return "python3 scripts/report.py fill %s" % d
    return ("if any win could carry photos, python3 references/%s/actions-and-wins/scripts/key_wins.py photos %s; "
            "then fill." % (folder, d))


def no_wins(root):
    """True when wins.json names no win: nothing to photograph, so the next step is fill."""
    try:
        with open(os.path.join(root, "wins.json"), encoding="utf-8") as fh:
            return json.load(fh) == []
    except (OSError, ValueError):
        return False


# ── verify ──────────────────────────────────────────────────────────────────
def verify(work, calls):
    """Problems with the saved responses: one that is not a PEAK response, an error saved as data, a
    page holding fewer or more rows than its pagination says, or a row for a site outside the report.
    An optional call PEAK refused is the section's to handle; every other refusal is made again."""
    ctx = work.ctx
    sites = {s["site_id"] for s in ctx["sites"]} if mode_of(ctx) == "portfolio" else {ctx["site"]["site_id"]}
    out = []
    for c in calls:
        if c.get("read") or not work.has(c["file"]):
            continue
        path = work.path(c["file"])
        try:
            with open(path, encoding="utf-8") as fh:
                payload = json.load(fh)
        except ValueError as e:
            out.append("%s is not JSON (%s)" % (c["file"], e))
            continue
        try:
            r = io.Response(payload)
        except io.PeakRefusal as e:
            if not c.get("optional"):
                out.append("%s is PEAK's error, not data: make the call again (%s)" % (c["file"], e))
            continue
        except ValueError as e:
            out.append("%s does not read as a PEAK response (%s)" % (c["file"], e))
            continue
        args = io.call_args(c)
        limit, start = args.get("limit"), args.get("start_index") or 0
        if r.total is not None and limit and limit > 1:
            want = max(0, min(limit, r.total - start))
            if len(r.rows) != want:
                out.append("%s holds %d rows where its pagination says %d" % (c["file"], len(r.rows), want))
        bad = sorted({row.get("site_id") for row in r.rows if isinstance(row, dict)
                      and isinstance(row.get("site_id"), int) and row["site_id"] not in sites})
        if bad and "site_ids" in args:
            out.append("%s holds rows for site ids %s, which are not in this report" % (c["file"], bad))
    return out


def cmd_verify(a):
    work = io.Work(a.dir)
    with open(os.path.join(work.root, "calls.json")) as fh:
        calls = json.load(fh)
    problems = verify(work, calls)
    for p in problems:
        print("ERROR: " + p)
    if problems:
        sys.exit("%d saved response(s) to make again." % len(problems))
    print("ok: every saved response reads back as PEAK returned it.")


# ── bundle ──────────────────────────────────────────────────────────────────
def merge(into, part, section=None):
    if part.get("drop") is True:
        part = dict(part, drop=[section])
    for k, v in part.items():
        if k in ("impact", "drop", "chat"):
            into.setdefault(k, []).extend(v)
        elif isinstance(v, dict) and k in ("links", "datelines", "notes", "statements", "dated_heads"):
            into.setdefault(k, {}).update(v)
        else:
            into[k] = v


def site_facts(work):
    """The site's platform row, which every section takes."""
    return work.get("overview/site.json").first() or {}


def cmd_bundle(a):
    work = io.Work(a.dir)
    ctx = work.ctx
    if mode_of(ctx) == "portfolio":
        return bundle_portfolio(a, work)
    shared = {"site_facts": site_facts(work)}
    data = {}
    for s in [s for s in ORDER if s in ctx["sections"]] + ["overview"]:
        part = module(s).build(ctx, work, shared)
        for r in part.get("impact", []):
            if r["row"] not in IMPACT_ORDER:
                sys.exit("%s hands on an impact row %r that IMPACT_ORDER does not place" % (s, r["row"]))
            r["section"] = s
        merge(data, part, s)
    data["sections"] = ",".join(s for s in ctx["sections"] if s not in data.get("drop", []))
    data["impact"] = [{k: v for k, v in r.items() if k not in ("row", "section")}
                      for r in sorted(data.get("impact", []), key=lambda r: IMPACT_ORDER.index(r["row"]))
                      if r["section"] not in data.get("drop", [])]
    if not data["impact"]:
        data.pop("impact")                 # no row-owning section is in, so neither is the frame
    with open(os.path.join(work.root, "data.json"), "w") as fh:
        json.dump(data, fh, indent=1, ensure_ascii=False)
    print("Wrote %s/data.json." % a.dir)
    for c in data.get("chat", []):
        print("Say in chat at hand-over: " + c)
    print("Next: " + next_step(work, a.dir))


def bundle_portfolio(a, work):
    import portfolio_io as pio
    ctx = work.ctx
    shared = {"facts": module("overview", "portfolio").facts(ctx, work)}       # each site's platform row
    data = {}
    for s in PORTFOLIO_ORDER:
        merge(data, module(s, "portfolio").build(ctx, work, shared), s)
    data["sections"] = ",".join(s for s in PORTFOLIO_ORDER if s != "overview" and s not in data.get("drop", []))
    data["months"] = {"quarter": [io.mon(m) for m in ctx["quarter_months"]]}
    if pio.closing(ctx):
        data.setdefault("chat", []).append(CLOSING % (pio.month_name(ctx), io.day_long(ctx["today"])))
    with open(os.path.join(work.root, "data.json"), "w") as fh:
        json.dump(data, fh, indent=1, ensure_ascii=False)
    print("Wrote %s/data.json." % a.dir)
    for c in data.get("chat", []):
        print("Say in chat at hand-over: " + c)
    if os.path.isfile(os.path.join(work.root, "shortlist.json")) and not os.path.isfile(os.path.join(work.root, "wins.json")):
        print("Next: python3 scripts/report.py next %s for the shortlist in full, then choose the wins from it and "
              "write %s/wins.json." % (a.dir, a.dir))
    else:
        print("Next: " + next_step(work, a.dir))


# ── fill ────────────────────────────────────────────────────────────────────
def cmd_fill(a):
    work = io.Work(a.dir)
    ctx = work.ctx
    if mode_of(ctx) == "portfolio":
        return fill_portfolio(a, work)
    with open(os.path.join(work.root, "data.json"), encoding="utf-8") as fh:
        data = json.load(fh)
    sections = data["sections"].split(",")
    chat = []
    if "key-wins" in sections:
        kw = module("key-wins")
        got = need_wins(kw.load_wins(work), a.dir)
        if not got:
            sections.remove("key-wins")
            chat.append("Key wins left out: no win qualified. Say what you read and rejected, per key-wins.md.")
        else:
            merge(data, kw.assemble(ctx, work))
    data["sections"] = ",".join(sections)
    chat = data.pop("chat", []) + chat
    data.pop("drop", None)
    final = os.path.join(work.root, "report-data.json")
    with open(final, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=1, ensure_ascii=False)
    name = re.sub(r"[^a-z0-9]+", "-", ctx["site"]["site_name"].lower()).strip("-")
    last = io.d(io.whole(ctx, ctx["quarter_months"])[-1])     # the quarter's last complete month names the file
    out = a.out or os.path.join(work.root, "%s-q%d-%d.html" % (name, (last.month - 1) // 3 + 1, last.year))
    tiles = fresh_tiles(work.root)
    r = subprocess.run([sys.executable, os.path.join(HERE, "fill_report.py"), final, "--out", out,
                        "--photos-out", tiles], capture_output=True, text=True)
    print((r.stdout + r.stderr).strip())
    if r.returncode:
        sys.exit(r.returncode)
    r = subprocess.run([sys.executable, os.path.join(HERE, "build_report.py"), "check", out],
                       capture_output=True, text=True)
    print((r.stdout + r.stderr).strip())
    if any(os.scandir(tiles)) if os.path.isdir(tiles) else False:
        print("Photo tiles exactly as printed: %s" % tiles)
    for c in chat:
        print("Say in chat: " + c)
    if r.returncode:
        sys.exit(r.returncode)


def need_wins(wins, d):
    if wins is None:
        sys.exit("No %s/wins.json yet: write the chosen wins, or [] when none qualified, then fill." % d)
    return wins


def fresh_tiles(root):
    """The tiles folder, emptied, so it holds exactly the tiles this fill prints."""
    tiles = os.path.join(root, "tiles")
    shutil.rmtree(tiles, ignore_errors=True)
    return tiles


def fill_portfolio(a, work):
    ctx = work.ctx
    with open(os.path.join(work.root, "data.json"), encoding="utf-8") as fh:
        data = json.load(fh)
    sections = [s for s in data["sections"].split(",") if s]
    chat = []
    if "key-wins" in sections:
        kw = module("key-wins", "portfolio")
        got = need_wins(kw.load_wins(work), a.dir)
        if not got:
            sections.remove("key-wins")
            chat.append("Key wins left out: no win qualified. Say what you read and rejected, per key-wins.md.")
        else:
            merge(data, kw.assemble(ctx, work))
    data["sections"] = ",".join(sections)
    # the client logo is read now, so a logo added to or taken out of the plan shows on the next fill
    logo = os.path.join(work.root, ctx["client_logo"]) if ctx.get("client_logo") else None
    m = data["masthead"]
    if m.get("shown"):                      # a site that shows only through a win still counts
        shown = set(m["shown"]) | {w.get("site_id") for w in data.get("wins") or []}
        m["sites"] = len(shown - {None})
        blank = [s["site_name"].strip() for s in ctx["sites"] if s["site_id"] not in shown]
        if blank:
            chat.append("PEAK holds no scores, actions or ratings for %s in this report's windows, so %s left out of "
                        "the masthead's site count; %s equipment, sensors and rules still count in the scorecards."
                        % (io.listing(blank), "it is" if len(blank) == 1 else "they are",
                           "its" if len(blank) == 1 else "their"))
    ov, use = module("overview", "portfolio"), bool(logo and client_logo_ok(logo))
    data["masthead"]["logo"] = ov.logo(logo) if use else None
    data["masthead"]["logo_tile"] = ov.dark(logo) if use else False
    chat = data.pop("chat", []) + chat
    data.pop("drop", None)
    final = os.path.join(work.root, "report-data.json")
    with open(final, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=1, ensure_ascii=False)
    name = re.sub(r"[^a-z0-9]+", "-", ctx["client"].replace("'", "").replace("\u2019", "").lower()).strip("-") or "portfolio"
    out = a.out or os.path.join(work.root, "%s-portfolio-%s.html" % (name, ctx["month"][:7]))   # the leaderboard month
    tiles = fresh_tiles(work.root)
    r = subprocess.run([sys.executable, os.path.join(HERE, "fill_portfolio.py"), final, "--out", out,
                        "--photos-out", tiles], capture_output=True, text=True)
    print((r.stdout + r.stderr).strip())
    if r.returncode:
        sys.exit(r.returncode)
    r = subprocess.run([sys.executable, os.path.join(HERE, "build_report.py"), "check", out, "--mode", "portfolio"],
                       capture_output=True, text=True)
    print((r.stdout + r.stderr).strip())
    if any(os.scandir(tiles)) if os.path.isdir(tiles) else False:
        print("Photo tiles exactly as printed: %s" % tiles)
    for c in chat:
        print("Say in chat: " + c)
    if r.returncode:
        sys.exit(r.returncode)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("plan")
    p.add_argument("dir")
    which = p.add_mutually_exclusive_group(required=True)
    which.add_argument("--site", help="the saved search_sites response: the single-site report")
    which.add_argument("--sites", nargs="+", help="the saved search_sites pages: the portfolio report")
    p.add_argument("--site-id", type=int)
    p.add_argument("--client", help="portfolio: the name the report carries")
    p.add_argument("--client-logo", help="portfolio: a logo file the user supplied")
    p.add_argument("--site-ids", type=int, nargs="+", help="portfolio: only these of the saved sites")
    p.add_argument("--author", required=True, help="who_am_i's user_name")
    p.add_argument("--sections", help="comma-separated: %s, or all (default)" % ", ".join(OPTIONS))
    p.add_argument("--today", help="issue date, YYYY-MM-DD in site time (default: today)")
    p.add_argument("--hours", help='run hours against these working hours, e.g. "Mon-Fri 08:00-18:00"')
    p.set_defaults(func=cmd_plan)
    for name, func in (("next", cmd_next), ("verify", cmd_verify), ("bundle", cmd_bundle)):
        q = sub.add_parser(name)
        q.add_argument("dir")
        q.set_defaults(func=func)
    f = sub.add_parser("fill")
    f.add_argument("dir")
    f.add_argument("--out")
    f.set_defaults(func=cmd_fill)
    a = ap.parse_args()
    if a.cmd == "plan" and a.sites and not a.client:
        ap.error("--sites needs --client")
    a.func(a)


if __name__ == "__main__":
    main()
