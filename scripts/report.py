#!/usr/bin/env python3
"""Drive a client report from the section scripts, so the model only makes the
PEAK calls, picks the key wins and writes the prose.

    python3 scripts/report.py plan   <dir> --site <dir>/site.json --author "Full Name" [--sections ...]
    python3 scripts/report.py next   <dir>
    python3 scripts/report.py bundle <dir>
    python3 scripts/report.py fill   <dir> [--out <file.html>]

plan    Fixes the quarter from today in site time and prints every call the chosen
        sections need, each with the file under <dir>/peak/ its response is saved as.
next    Checks every printed call was saved, then prints the follow-up calls the
        responses call for (paging, a single-level site's zones, run hours history,
        key win evidence once wins.json exists), or says there are none.
bundle  Builds every figure, row, series, link and note into <dir>/data.json, and
        writes <dir>/facts.md: what each prose slot is for and the facts to write
        it from, plus the key win candidates.
fill    Merges <dir>/prose.json and <dir>/wins.json into the bundle, fills the
        report and runs the check.

Each section is a folder under references/ holding its reference and its
scripts; MODULES below is the whole registry. A module exposes calls(ctx),
more(ctx, work) and build(ctx, work, shared).
"""
import argparse
import importlib
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
MODULES = {"overview": ("overview", "overview"),
           "equipment-health": ("equipment-health", "equipment_health"),
           "indoor-environment": ("indoor-environment", "indoor_environment"),
           "alerts-resolved": ("actions-and-wins", "alerts_resolved"),
           "key-wins": ("actions-and-wins", "key_wins"),
           "run-hours": ("run-hours", "run_hours")}
ORDER = ["equipment-health", "indoor-environment", "alerts-resolved", "key-wins", "run-hours"]
# prose.json key -> (bundle object, field) it fills
PROSE = {"eh_snapshot": ("equipment_health", "note"), "eh_score_trend": ("trend_eh", "note"),
         "eh_checks_trend": ("trend_checks", "note"), "ie_snapshot": ("comfort", "note"),
         "ie_trend": ("trend_comfort", "note"), "alerts_trend": ("alerts", "note"),
         "run_hours": ("run_hours", "note")}


def module(section):
    folder, name = MODULES[section]
    path = os.path.join(ROOT, "references", folder, "scripts")
    if path not in sys.path:
        sys.path.insert(0, path)
    return importlib.import_module(name)


def active(ctx):
    return ["overview"] + [s for s in ORDER if s in ctx["sections"]]


def show(calls, start):
    for i, c in enumerate(calls, start):
        print("%3d. %s -> %s" % (i, c["tool"], c["file"]))
        print("     " + json.dumps(c["args"], separators=(", ", ": ")))


def save_rule(root):
    return ("Save each response under %s/peak/ as the file named. An offloaded response: copy the file "
            "you were handed (cp). Inline responses: write them out verbatim, all together if you like, "
            "as one JSON object in %s/peak/inline.json, {\"<file name>\": <response exactly as returned>, ...}."
            % (root, root))


# ── plan ────────────────────────────────────────────────────────────────────
def cmd_plan(a):
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
    sections = [s for o in picked for s in (OPTIONS[o][1] if o in OPTIONS else [o])]
    from zoneinfo import ZoneInfo
    today = io.d(a.today) if a.today else datetime.now(ZoneInfo(site["timezone"])).date()
    root = os.path.abspath(a.dir)
    os.makedirs(os.path.join(root, "peak"), exist_ok=True)
    ctx = dict(io.windows(today), site=site, author=a.author, sections=[s for s in ORDER if s in sections],
               dir=root, site_file=os.path.abspath(a.site), hours=a.hours,
               brand={"override": brand_override()})
    with open(os.path.join(root, "plan.json"), "w") as fh:
        json.dump(ctx, fh, indent=1)
    calls = [c for s in active(ctx) for c in module(s).calls(ctx)]
    with open(os.path.join(root, "calls.json"), "w") as fh:
        json.dump(calls, fh, indent=1)
    q0, q1 = ctx["quarter"]
    print("%s: quarter %s, trends %s, issued %s." % (site["site_name"], io.period(q0, io.last_day(q1).isoformat(), True),
                                                    io.span(ctx["trend_months"][0], ctx["trend_months"][-1], True),
                                                    io.day_short(ctx["today"])))
    print("Sections: %s." % ", ".join(OPTIONS[o][0] if o in OPTIONS else o for o in picked))
    print("\n%d calls. Make them all in one parallel batch, each exactly as printed: the tool, then its "
          "arguments. %s Then run: python3 scripts/report.py next %s\n" % (len(calls), save_rule(a.dir), a.dir))
    show(calls, 1)


def brand_override():
    """True when BRAND.md sets any key, so platform strings read PEAK rather than CIM PEAK."""
    path = os.path.join(ROOT, "BRAND.md")
    if not os.path.isfile(path):
        return False
    text = open(path, encoding="utf-8").read()
    m = re.match(r"---\n(.*?)\n---", text, re.S)
    return bool(m and re.search(r"^\s*[a-z-]+:\s*\S", m.group(1), re.M))


# ── next ────────────────────────────────────────────────────────────────────
def cmd_next(a):
    work = io.Work(a.dir)
    with open(os.path.join(work.root, "calls.json")) as fh:
        calls = json.load(fh)
    missing = [c["file"] for c in calls if not work.has(c["file"])]
    if missing:
        sys.exit("Not saved yet: %s. %s" % (", ".join(missing), save_rule(a.dir)))
    new = [c for s in active(work.ctx) for c in module(s).more(work.ctx, work)]
    if not new:
        print("No more calls. Next: python3 scripts/report.py bundle %s" % a.dir
              if not os.path.isfile(os.path.join(work.root, "wins.json"))
              else "No more calls. Next, if any win could carry photos: python3 "
                   "references/actions-and-wins/scripts/key_wins.py photos %s; then fill." % a.dir)
        return
    have = {c["file"] for c in calls}
    calls += [c for c in new if c["file"] not in have]
    with open(os.path.join(work.root, "calls.json"), "w") as fh:
        json.dump(calls, fh, indent=1)
    print("%d more calls, in one parallel batch, each exactly as printed. %s Then run next again.\n"
          % (len(new), save_rule(a.dir)))
    show(new, 1)


# ── bundle ──────────────────────────────────────────────────────────────────
def merge(into, part):
    for k, v in part.items():
        if k in ("impact", "facts", "drop", "chat"):
            into.setdefault(k, []).extend(v)
        elif isinstance(v, dict) and k in ("links", "datelines", "notes", "prose", "statements"):
            into.setdefault(k, {}).update(v)
        else:
            into[k] = v


def cmd_bundle(a):
    work = io.Work(a.dir)
    ctx = work.ctx
    shared = {"site_facts": work.get("overview/site.json").first() or {}}
    data = {}
    for s in [s for s in ORDER if s in ctx["sections"]] + ["overview"]:
        merge(data, module(s).build(ctx, work, shared))
    data["sections"] = ",".join(s for s in ctx["sections"] if s not in data.get("drop", []))
    data["impact"] = [{k: v for k, v in r.items() if k != "order"}
                      for r in sorted(data.get("impact", []), key=lambda r: r["order"])
                      if not ((r["order"] == 5 and "alerts-resolved" in data.get("drop", [])))]
    data["months"] = {"quarter": [io.mon(m) for m in ctx["quarter_months"]],
                      "trend": [io.mon(m) for m in ctx["trend_months"]]}
    with open(os.path.join(work.root, "data.json"), "w") as fh:
        json.dump(data, fh, indent=1, ensure_ascii=False)
    prose = {k: v for k, v in data.get("prose", {}).items() if k in PROSE and PROSE[k][0] in data}
    lines = ["# Facts for the prose, %s" % ctx["site"]["site_name"], ""]
    lines += ["- " + f for f in data.get("facts", [])]
    lines += ["", "## prose.json", "",
              "Write %s/prose.json with these keys, each two to four sentences, by Writing the narrative in "
              "SKILL.md and the section's reference:" % a.dir, ""]
    lines += ["- `%s`: %s" % (k, v) for k, v in prose.items()]
    if "key-wins" in ctx["sections"] and "key-wins" not in data.get("drop", []):
        lines += ["", "## wins.json", "",
                  "Read kw/digest.md, choose by references/actions-and-wins/key-wins.md, and write %s/wins.json: "
                  "a list, best first, of {\"tickets\": [8-character ids], \"state\": \"fixed\" or \"in_flight\", "
                  "\"heading\": ..., \"body\": ...%s}. Then run report.py next for the impact, photo and level "
                  "calls." % (a.dir, ", \"snap\": ..." if "equipment-health" in ctx["sections"] else "")]
    with open(os.path.join(work.root, "facts.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print("Wrote %s/data.json and %s/facts.md." % (a.dir, a.dir))
    print("\n".join(lines))


# ── fill ────────────────────────────────────────────────────────────────────
def cmd_fill(a):
    work = io.Work(a.dir)
    ctx = work.ctx
    with open(os.path.join(work.root, "data.json"), encoding="utf-8") as fh:
        data = json.load(fh)
    prose_path = os.path.join(work.root, "prose.json")
    prose = json.load(open(prose_path, encoding="utf-8")) if os.path.isfile(prose_path) else {}
    missing = [k for k, (obj, _) in PROSE.items() if obj in data and k in data.get("prose", {}) and not prose.get(k)]
    if missing:
        sys.exit("prose.json is missing %s" % ", ".join(missing))
    for k, text in prose.items():
        if k in PROSE and PROSE[k][0] in data:
            data[PROSE[k][0]][PROSE[k][1]] = text
    sections = data["sections"].split(",")
    chat = []
    if "key-wins" in sections:
        kw = module("key-wins")
        got = kw.load_wins(work)
        if not got or not got[0]:
            sections.remove("key-wins")
            chat.append("Key wins left out: no win qualified. Say what you read and rejected, per key-wins.md.")
        else:
            merge(data, kw.assemble(ctx, work))
    data["sections"] = ",".join(sections)
    chat = data.pop("chat", []) + chat
    for k in ("prose", "facts", "drop"):
        data.pop(k, None)
    final = os.path.join(work.root, "report-data.json")
    with open(final, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=1, ensure_ascii=False)
    name = re.sub(r"[^a-z0-9]+", "-", ctx["site"]["site_name"].lower()).strip("-")
    out = a.out or os.path.join(work.root, "%s-q%d-%d.html" % (name, (io.d(ctx["quarter_months"][-1]).month - 1) // 3 + 1,
                                                              io.d(ctx["quarter_months"][-1]).year))
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


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("plan")
    p.add_argument("dir")
    p.add_argument("--site", required=True, help="the saved search_sites response")
    p.add_argument("--site-id", type=int)
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
    a.func(a)


if __name__ == "__main__":
    main()
