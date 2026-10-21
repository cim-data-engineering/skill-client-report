#!/usr/bin/env python3
"""Drive a client report from the section scripts, so the model only makes the
PEAK calls and picks and writes the key wins.

    python3 scripts/report.py plan   <dir> --site <dir>/site.json --author "Full Name" [--sections ...]
    python3 scripts/report.py plan   <dir> --sites <dir>/sites.json [...] --client "Name" --author "Full Name"
                                     [--client-logo <file>] [--site-ids ...]
    python3 scripts/report.py next   <dir>
    python3 scripts/report.py bundle <dir>
    python3 scripts/report.py fill   <dir> [--out <file.html>]

plan    Fixes the quarter from today in site time and prints every call the chosen
        sections need, each with the file under <dir>/peak/ its response is saved as.
        --site plans the single-site report; --sites plans the portfolio report over
        the active sites in those search_sites pages, with every section.
next    Checks every printed call was saved, then prints the follow-up calls the
        responses call for (paging, a single-level site's zones, run hours history,
        key win evidence once wins.json exists), or says there are none.
bundle  Builds every figure, row, series, link and note into <dir>/data.json, and
        prints anything to say in chat at hand-over, then the next step.
fill    Merges <dir>/wins.json into the bundle, fills the report and runs the
        check.

Each section is a folder under references/<mode>/ holding its reference and its
scripts; MODES below is the whole registry, one entry per report. A module exposes
calls(ctx), more(ctx, work) and build(ctx, work, shared). plan.json names the mode,
and one without a mode is single-site.
"""
import argparse
import importlib
import importlib.util
import json
import os
import re
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
#   rankings            [{label, anchor, window: "months" | "quarters", now, start, dp}], one board each
#   weighted            set when a section draws a size-weighted portfolio row
#   partial             names of the volume figures shown that run short over a month to date; in the
#                       single-site report, present once any section shows the month to date
# A figure the plan needs, before anything is fetched, a module names in HANDS_ON: plan.json
# lists them as handed_on.

# The portfolio report: every section, no prompt. Each drops itself when PEAK has nothing
# for it. PORTFOLIO_PAGE is the page order, which numbers the notes band; PORTFOLIO_ORDER
# the build order.
PORTFOLIO_MODULES = {"overview": ("portfolio-leaderboard/overview", "overview"),
                     "site-leaderboard": ("portfolio-leaderboard/site-leaderboard", "site_leaderboard"),
                     "equipment-health": ("portfolio-leaderboard/equipment-health", "equipment_health"),
                     "indoor-environment": ("portfolio-leaderboard/indoor-environment", "indoor_environment"),
                     "actions-by-company": ("portfolio-leaderboard/actions-and-wins", "actions_by_company"),
                     "key-wins": ("portfolio-leaderboard/actions-and-wins", "key_wins"),
                     "sustainability-ratings": ("portfolio-leaderboard/sustainability-ratings",
                                                "sustainability_ratings")}
PORTFOLIO_PAGE = ["overview", "site-leaderboard", "equipment-health", "indoor-environment", "actions-by-company",
                  "key-wins", "sustainability-ratings"]
PORTFOLIO_ORDER = ["equipment-health", "indoor-environment", "actions-by-company", "key-wins",
                   "sustainability-ratings", "site-leaderboard", "overview"]
MODES = {"single-site": {"options": OPTIONS, "modules": MODULES, "order": ORDER, "auto": AUTO},
         "portfolio": {"options": {}, "modules": PORTFOLIO_MODULES, "order": PORTFOLIO_ORDER,
                       "auto": PORTFOLIO_ORDER}}


def mode_of(ctx):
    return ctx.get("mode", "single-site")


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
             "screened and compact with: python3 references/single-site/actions-and-wins/scripts/key_wins.py digest <that file>")


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
    from zoneinfo import ZoneInfo
    today = io.d(a.today) if a.today else datetime.now(ZoneInfo(site["timezone"])).date()
    root = os.path.abspath(a.dir)
    os.makedirs(os.path.join(root, "peak"), exist_ok=True)
    ctx = dict(io.windows(today), site=site, author=a.author, sections=[s for s in ORDER if s in sections],
               dir=root, site_file=os.path.abspath(a.site), hours=a.hours,
               brand=brand())
    ctx["handed_on"] = sorted({f for s in ctx["sections"] for f in getattr(module(s), "HANDS_ON", [])})
    with open(os.path.join(root, "plan.json"), "w") as fh:
        json.dump(ctx, fh, indent=1)
    calls = [c for s in active(ctx) for c in module(s).calls(ctx)]
    with open(os.path.join(root, "calls.json"), "w") as fh:
        json.dump(calls, fh, indent=1)
    save = [c for c in calls if not c.get("read")]
    read = [c for c in calls if c.get("read")]
    print("%s: quarter %s, trends %s, issued %s%s." % (
        site["site_name"], io.period(ctx["quarter"][0], ctx["through"], True),
        io.span(ctx["trend_months"][0], ctx["trend_months"][-1], True), io.day_short(ctx["today"]),
        io.and_to_date(ctx, "; both windows close on ")))
    print("Sections: %s." % ", ".join(OPTIONS[o][0] if o in OPTIONS else o for o in picked))
    print("\n%d calls. Make them all in one parallel batch, each exactly as printed: the tool, then its "
          "arguments. %s Then run: python3 scripts/report.py next %s\n" % (len(calls), save_rule(a.dir), a.dir))
    show(save, 1)
    if read:
        print("\nIn the same batch, %d to read: the key win candidates. %s\n" % (len(read), READ_RULE))
        show(read, len(save) + 1)


def plan_portfolio(a):
    import portfolio_io as pio
    sites, seen = [], set()
    for r in [r for f in a.sites for r in io.read(f).rows]:
        sid = r.get("site_id")
        if sid in seen or r.get("is_active") is False or (a.site_ids and sid not in a.site_ids):
            continue
        seen.add(sid)
        sites.append({k: r.get(k) for k in ("site_id", "site_name", "state", "country", "city", "timezone",
                                             "site_link")})
    if not sites:
        sys.exit("%s holds no active site%s" % (", ".join(a.sites), " among --site-ids" if a.site_ids else ""))
    if len(sites) == 1:
        sys.exit("%s holds one active site, %s: build the single-site report for it, planned with --site"
                 % (", ".join(a.sites), sites[0]["site_name"].strip()))
    logo = os.path.abspath(a.client_logo) if a.client_logo else None
    if logo and not os.path.isfile(logo):
        sys.exit("client logo not found: %s" % a.client_logo)
    from zoneinfo import ZoneInfo
    today = io.d(a.today) if a.today else datetime.now(ZoneInfo(sites[0]["timezone"])).date()
    root = os.path.abspath(a.dir)
    os.makedirs(os.path.join(root, "peak"), exist_ok=True)
    ctx = dict(io.windows(today), mode="portfolio", sites=sites, client=a.client.strip(), client_logo=logo,
               author=a.author, sections=list(PORTFOLIO_ORDER), dir=root, brand=brand())
    ctx["prev_quarter"] = pio.prev_quarter(ctx)
    with open(os.path.join(root, "plan.json"), "w") as fh:
        json.dump(ctx, fh, indent=1)
    calls = [c for s in active(ctx) for c in module(s, "portfolio").calls(ctx)]
    with open(os.path.join(root, "calls.json"), "w") as fh:
        json.dump(calls, fh, indent=1)
    save = [c for c in calls if not c.get("read")]
    read = [c for c in calls if c.get("read")]
    print("%s portfolio: %d sites, reporting period %s, issued %s%s." % (
        ctx["client"], len(sites), pio.reporting_period(ctx, True), io.day_short(ctx["today"]),
        io.and_to_date(ctx, "; both windows close on ")))
    print("Sections: every one with data. Each site's dates are its own local calendar.")
    print("\n%d calls to save. Make them in parallel batches of about twenty, each exactly as printed: the tool, "
          "then its arguments. %s Then run: python3 scripts/report.py next %s\n"
          % (len(save), PORTFOLIO_SAVE % a.dir, a.dir))
    show(save, 1)
    if read:
        print("\nAlongside them, %d to read: the key win candidates. %s\n" % (len(read), PORTFOLIO_READ_RULE % a.dir))
        show(read, len(save) + 1)


def brand():
    """BRAND.md's identity: name / service-name replace the masthead's CIM defaults."""
    path = os.path.join(ROOT, "BRAND.md")
    text = open(path, encoding="utf-8").read() if os.path.isfile(path) else ""
    m = re.match(r"---\n(.*?)\n---", text, re.S)
    head = m.group(1) if m else ""
    get = lambda k: (re.search(r"^%s:\s*(\S.*?)\s*$" % k, head, re.M) or [None, None])[1]
    return {"name": get("name") or "CIM", "service": get("service-name") or "Data Driven Operations"}


# ── next ────────────────────────────────────────────────────────────────────
def cmd_next(a):
    work = io.Work(a.dir)
    with open(os.path.join(work.root, "calls.json")) as fh:
        calls = json.load(fh)
    missing = [c["file"] for c in calls if not c.get("read") and not work.has(c["file"])]
    if missing:
        sys.exit("Not saved yet: %s. %s" % (", ".join(missing), PORTFOLIO_SAVE % a.dir if mode_of(work.ctx) == "portfolio"
                                                                 else save_rule(a.dir)))
    mode = mode_of(work.ctx)
    new = [c for s in active(work.ctx) for c in module(s, mode).more(work.ctx, work)]
    if not new:
        folder = "portfolio-leaderboard" if mode == "portfolio" else "single-site"
        if not os.path.isfile(os.path.join(work.root, "wins.json")):
            print("No more calls. Next: python3 scripts/report.py bundle %s" % a.dir)
        elif os.path.isdir(os.path.join(work.root, "kw", "photos")):
            print("No more calls. Next: python3 scripts/report.py fill %s" % a.dir)
        else:
            print("No more calls. Next, if any win could carry photos: python3 "
                  "references/%s/actions-and-wins/scripts/key_wins.py photos %s; then fill." % (folder, a.dir))
        return
    have = {c["file"] for c in calls}
    calls += [c for c in new if c["file"] not in have]
    with open(os.path.join(work.root, "calls.json"), "w") as fh:
        json.dump(calls, fh, indent=1)
    read = [c for c in new if c.get("read")]
    new = [c for c in new if not c.get("read")]
    if new:
        print("%d more calls, in one parallel batch, each exactly as printed. %s Then run next again.\n"
              % (len(new), PORTFOLIO_SAVE % a.dir if mode == "portfolio" else save_rule(a.dir)))
        show(new, 1)
    if read:
        print("%s%d to read, never saved: the shortlist in full. Read it where it comes back; one that comes back "
              "offloaded prints compact with: python3 references/portfolio-leaderboard/actions-and-wins/scripts/"
              "key_wins.py digest %s <that file> --top 0. Choose the wins from it and write %s/wins.json, then run "
              "next again.\n" % ("\n" if new else "", len(read), a.dir, a.dir))
        show(read, len(new) + 1)


# ── bundle ──────────────────────────────────────────────────────────────────
def merge(into, part):
    for k, v in part.items():
        if k in ("impact", "drop", "chat"):
            into.setdefault(k, []).extend(v)
        elif isinstance(v, dict) and k in ("links", "datelines", "notes", "statements"):
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
            r["section"] = s
        merge(data, part)
    data["sections"] = ",".join(s for s in ctx["sections"] if s not in data.get("drop", []))
    data["impact"] = [{k: v for k, v in r.items() if k not in ("row", "section")}
                      for r in sorted(data.get("impact", []), key=lambda r: IMPACT_ORDER.index(r["row"]))
                      if r["section"] not in data.get("drop", [])]
    if not data["impact"]:
        data.pop("impact")                 # no row-owning section is in, so neither is the frame
    data["months"] = {"quarter": [io.mon(m) for m in ctx["quarter_months"]],
                      "trend": [io.mon(m) for m in ctx["trend_months"]],
                      "to_date": bool(ctx["to_date"])}
    with open(os.path.join(work.root, "data.json"), "w") as fh:
        json.dump(data, fh, indent=1, ensure_ascii=False)
    print("Wrote %s/data.json." % a.dir)
    for c in data.get("chat", []):
        print("Say in chat at hand-over: " + c)
    if "key-wins" in ctx["sections"] and "key-wins" not in data.get("drop", []):
        print("Next: choose the key wins from the two candidate pulls and write %s/wins.json, both by "
              "references/single-site/actions-and-wins/key-wins.md. Then run: python3 scripts/report.py next %s" % (a.dir, a.dir))
    else:
        print("Next: python3 scripts/report.py fill %s" % a.dir)


def bundle_portfolio(a, work):
    ctx = work.ctx
    shared = {"facts": module("overview", "portfolio").facts(ctx, work)}       # each site's platform row
    data = {}
    for s in PORTFOLIO_ORDER:
        part = module(s, "portfolio").build(ctx, work, shared)
        for n in part.get("notes", {}).values():         # notes run in page order; a closing one ends the band
            n["order"] = len(PORTFOLIO_PAGE) if n.pop("closes", False) else PORTFOLIO_PAGE.index(s)
        merge(data, part)
    data["sections"] = ",".join(s for s in PORTFOLIO_ORDER if s != "overview" and s not in data.get("drop", []))
    data["months"] = {"quarter": [io.mon(m) for m in ctx["quarter_months"]], "to_date": bool(ctx["to_date"])}
    with open(os.path.join(work.root, "data.json"), "w") as fh:
        json.dump(data, fh, indent=1, ensure_ascii=False)
    print("Wrote %s/data.json." % a.dir)
    for c in data.get("chat", []):
        print("Say in chat at hand-over: " + c)
    if "key-wins" not in data.get("drop", []):
        print("Next: shortlist the key win candidates and write %s/shortlist.json, by "
              "references/portfolio-leaderboard/actions-and-wins/key-wins.md. Then run: python3 scripts/report.py "
              "next %s" % (a.dir, a.dir))
    else:
        print("Next: python3 scripts/report.py fill %s" % a.dir)


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
        got = kw.load_wins(work)
        if not got or not got[0]:
            sections.remove("key-wins")
            chat.append("Key wins left out: no win qualified. Say what you read and rejected, per key-wins.md.")
        else:
            merge(data, kw.assemble(ctx, work, site_facts(work)))
    data["sections"] = ",".join(sections)
    chat = data.pop("chat", []) + chat
    data.pop("drop", None)
    final = os.path.join(work.root, "report-data.json")
    with open(final, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=1, ensure_ascii=False)
    name = re.sub(r"[^a-z0-9]+", "-", ctx["site"]["site_name"].lower()).strip("-")
    last = io.d(io.whole(ctx, ctx["quarter_months"])[-1])     # the quarter's last complete month names the file
    out = a.out or os.path.join(work.root, "%s-q%d-%d.html" % (name, (last.month - 1) // 3 + 1, last.year))
    tiles = os.path.join(work.root, "tiles")
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


def fill_portfolio(a, work):
    ctx = work.ctx
    with open(os.path.join(work.root, "data.json"), encoding="utf-8") as fh:
        data = json.load(fh)
    sections = [s for s in data["sections"].split(",") if s]
    chat = []
    if "key-wins" in sections:
        kw = module("key-wins", "portfolio")
        got = kw.load_wins(work)
        if not got:
            sections.remove("key-wins")
            chat.append("Key wins left out: no win qualified. Say what you read and rejected, per key-wins.md.")
        else:
            merge(data, kw.assemble(ctx, work, module("overview", "portfolio").facts(ctx, work)))
    data["sections"] = ",".join(sections)
    chat = data.pop("chat", []) + chat
    data.pop("drop", None)
    final = os.path.join(work.root, "report-data.json")
    with open(final, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=1, ensure_ascii=False)
    name = re.sub(r"[^a-z0-9]+", "-", ctx["client"].lower()).strip("-") or "portfolio"
    last = io.d(io.whole(ctx, ctx["quarter_months"])[-1])     # the quarter's last complete month names the file
    out = a.out or os.path.join(work.root, "%s-portfolio-q%d-%d.html" % (name, (last.month - 1) // 3 + 1, last.year))
    tiles = os.path.join(work.root, "tiles")
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
    for name, func in (("next", cmd_next), ("bundle", cmd_bundle)):
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
