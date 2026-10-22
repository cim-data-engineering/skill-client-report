#!/usr/bin/env python3
"""Assemble and verify a client report from assets/reference-report.html.

The reference report is the design system compiled: its <style> block holds every
DESIGN.md token and component, and each report section is marked off as a part.
fill_report.py scaffolds the chosen sections from it and fills them from the bundle,
so a report carries only the parts it was asked for.

    scaffold  copy the shell, the always-on parts and the selected sections
    part      print one part's markup, to add a section to a report already built
    check     look for sample data, sample links and markers left behind
    parts     list part names and sizes

    python3 scripts/build_report.py scaffold --sections equipment-health,key-wins \
        --out skyline-q3.html
    python3 scripts/build_report.py check skyline-q3.html

--mode portfolio does the same for the portfolio report from
assets/portfolio-report.html, which takes the reference report's <style> block and
masthead logo at scaffold time, so both reports carry one compiled design system.
"""

import argparse, os, re, sys

REF = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "reference-report.html")

ALWAYS = ["shell", "masthead", "analytics-overview", "close"]
SECTION_PARTS = {
    "sustainability-ratings": ["sustainability-ratings"],
    "equipment-health": ["equipment-health-snapshot", "monthly-equipment-health"],
    "indoor-environment": ["indoor-environment-snapshot", "monthly-thermal-comfort"],
    "alerts-resolved": ["monthly-alerts", "actions-leaderboard"],
    "key-wins": ["key-wins"],
    "run-hours": ["equipment-run-hours"],
}
# Parts that render for any of several sections. Operational impact is a frame
# around rows the sections own, so it only stands if one of them is in.
ROW_SECTIONS = ["equipment-health", "indoor-environment", "alerts-resolved"]
PART_IF = {"operational-impact": ROW_SECTIONS, "notes": ROW_SECTIONS + ["run-hours"]}
# The portfolio report's scaffold and its part maps. Every section is in unless it
# dropped itself, and no part depends on another section.
PORTFOLIO = {"ref": os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "portfolio-report.html"),
             "always": ["shell", "masthead", "scorecards", "close"],
             "section_parts": {"site-leaderboard": ["site-leaderboard"],
                               "team-leaderboard": ["team-leaderboard"],
                               "equipment-health": ["equipment-health"],
                               "indoor-environment": ["indoor-environment"],
                               "actions-resolved": [],
                               "open-actions": ["open-actions"],
                               "key-wins": ["key-wins"],
                               "sustainability-ratings": ["sustainability-ratings"]},
             "part_if": {}}
SHARED = REF                         # the reference report, whose stylesheet and logo the portfolio takes
PART_RE = re.compile(r"^\s*<!-- part: ([a-z-]+) -->\s*$")
IF_RE = re.compile(r"^\s*<!-- if: ([a-z-, ]+) -->\s*$")
ENDIF_RE = re.compile(r"^\s*<!-- endif -->\s*$")


def read_parts():
    """Ordered [(part_name, [lines])]. Everything before the first marker is the shell."""
    parts, name, buf = [], "shell", []
    for line in open(REF, encoding="utf-8").read().split("\n"):
        m = PART_RE.match(line)
        if m:
            parts.append((name, buf))
            name, buf = m.group(1), []
        else:
            buf.append(line)
    parts.append((name, buf))
    return parts


def resolve(sections):
    unknown = [s for s in sections if s not in SECTION_PARTS]
    if unknown:
        sys.exit("unknown section(s): %s\nchoose from: %s"
                 % (", ".join(unknown), ", ".join(SECTION_PARTS)))
    keep = list(ALWAYS)
    for part, owners in PART_IF.items():
        if any(o in sections for o in owners):
            keep.append(part)
    for s in SECTION_PARTS:          # section order follows the report, not the CLI
        if s in sections:
            keep += SECTION_PARTS[s]
    return keep


def render(lines, sections):
    """Drop if-blocks for sections that are out; strip every marker."""
    out, skipping = [], None
    for line in lines:
        m = IF_RE.match(line)
        if m:                        # a comma list keeps the block for any of them
            owners = [o.strip() for o in m.group(1).split(",")]
            skipping = not any(o in sections for o in owners)
            continue
        if ENDIF_RE.match(line):
            skipping = None
            continue
        if not skipping:
            out.append(line)
    return tidy(out)


def tidy(lines):
    """Close the gaps a dropped block leaves: no run of blank lines, and no link
    row left standing with every link gone."""
    out = []
    for line in lines:
        if line.strip() == "" and out and out[-1].strip() == "":
            continue
        out.append(line)
    text = "\n".join(out)
    text = re.sub(r'\n *<div class="seclinks">\s*</div>', "", text)
    return text.split("\n")


def use_mode(mode):
    """Point the scaffold, the part maps and the check at one report's scaffold."""
    global REF, ALWAYS, SECTION_PARTS, PART_IF
    if mode == "portfolio":
        REF, ALWAYS = PORTFOLIO["ref"], PORTFOLIO["always"]
        SECTION_PARTS, PART_IF = PORTFOLIO["section_parts"], PORTFOLIO["part_if"]


def shared_parts():
    """The reference report's <style> block and masthead logo. The portfolio page carries
    no en or em dash, so the stylesheet's comments take a hyphen instead."""
    src = open(SHARED, encoding="utf-8").read()
    style = re.search(r"<style>.*?</style>", src, re.S).group(0)
    logo = re.search(r"[ \t]*<svg class=\"logo\".*?</svg>", src, re.S).group(0)
    return re.sub("[\u2013\u2014]", "-", style), logo


def cmd_scaffold(args):
    use_mode(args.mode)
    sections = [s.strip() for s in args.sections.split(",") if s.strip()] \
        if args.sections not in (None, "all") else list(SECTION_PARTS)
    keep = resolve(sections)
    body = []
    for name, lines in read_parts():
        if name in keep:
            body += render(lines, sections)
    if args.mode == "portfolio":
        style, logo = shared_parts()
        text = "\n".join(body)
        text = text.replace("<!-- style: reference-report -->", style).replace("  <!-- logo: reference-report -->", logo)
        body = text.split("\n")
    open(args.out, "w", encoding="utf-8").write("\n".join(body))
    dropped = [s for s in SECTION_PARTS if s not in sections]
    print("wrote %s — %d lines" % (args.out, len(body)))
    print("sections in:  %s" % (", ".join(sections) or "none"))
    print("sections out: %s" % (", ".join(dropped) or "none"))
    print("Every figure, name, date and link in this file is sample data for the "
          "reference site. Replace all of it, then run `check`.")


def sample_strings():
    """Sample values pulled from the reference report itself, so this list cannot
    drift as the sample changes. Whole cell/heading/link texts only — long enough
    that a match means unreplaced markup, not a coincidence."""
    src = open(REF, encoding="utf-8").read()
    found = set()
    for pat in (r'<td class="name">([^<]+)</td>', r'<span class="nm">([^<]+)</span>',
                r'<h3>([^<]+)</h3>', r'<title>([^<]+)</title>',
                # h2note and chartnote are deliberately absent — they carry window and
                # method wording that is correct for every report and recurs legitimately.
                # So are leaderboard companies: the sample's are PEAK's demo companies,
                # which any report can carry.
                # An operational impact row is matched whole, figure to sentence: the
                # sentence alone is a template a real site can repeat word for word.
                r'(<span class="fig">[^<]+</span> <span class="figcap">[^<]+</span>\s*<div class="isub">.*?</div>)'):
        for m in re.finditer(pat, src, re.S):
            found.add(m.group(1))
    # a win's body is its one unclassed paragraph, wherever the impact tag, the
    # level line and the photos put it, so read it off each win in turn
    for m in re.finditer(r'<div class="win[^"]*">(.*?)<p class="refs">', src, re.S):
        found |= set(re.findall(r'<p>(.+?)</p>', m.group(1)))
    for m in re.finditer(r'<p class="refs">(.*?)</p>', src, re.S):
        found |= set(re.findall(r'>([^<>]{8,})</a>', m.group(1)))
    # only platform links are report data — font and preconnect hosts stay. The ratings
    # link carries no dates, so a report for the sample site prints it exactly; the
    # data-sample marker catches an unfilled ratings section instead.
    found |= {h for h in re.findall(r'href="([^"]+)"', src)
              if "cimenviro.com" in h and "/dashboard/ratings" not in h}
    stop = {"CIM", "Total"}
    return sorted(s.strip() for s in found if len(s.strip()) >= 5 and s.strip() not in stop)


def cmd_check(args):
    if args.mode == "portfolio":
        return check_portfolio(args)
    text = open(args.report, encoding="utf-8").read()
    errors, warnings = [], []

    for marker in ("<!-- part:", "<!-- if:", "<!-- endif"):
        if marker in text:
            errors.append("marker left in the output: %s" % marker)
    for m in set(re.findall(r"\{\{[^}]+\}\}", text)) | set(re.findall(r"\{[a-z_]+_id\}", text)):
        errors.append("unresolved placeholder: %s" % m)

    hits = [s for s in sample_strings() if s in text]
    for h in hits[:20]:
        h = " ".join(re.sub(r"<[^>]+>", " ", h).split())
        errors.append("sample data still in the report: %s" % (h[:90] + ("…" if len(h) > 90 else "")))
    if len(hits) > 20:
        errors.append("... and %d more sample values" % (len(hits) - 20))

    # The PEAK site id is a system id. It belongs in a link URL, never in the text.
    visible = re.sub(r'\s(?:href|src)="[^"]*"', "", text)
    for m in sorted(set(re.findall(r"Site\s+\d+", visible))):
        errors.append("site id in visible text: %s — a system id the reader has no use for, "
                      "keep it to the link URLs" % m)

    ref = open(REF, encoding="utf-8").read()
    rid = re.search(r"site_ids=(\d+)", ref)
    rname = re.search(r"PEAK · ([^,<]+)", ref)
    for token in [m.group(1) for m in (rid, rname) if m]:
        # the id where a link carries it, not the same digits in a count or a chart coordinate
        pat = (r"(?:site_ids?=|/escalated/)%s(?!\d)" if token.isdigit() else "%s") % re.escape(token)
        if re.search(pat, text):
            warnings.append("reference site's own %s appears — fine only if this "
                            "report really is for it" % ("id %s" % token if token.isdigit() else "name %r" % token))

    # Key wins is the one section that can be scaffolded and then find nothing
    # to say: an empty heading is worse than no heading, so it must be deleted.
    kw = text.find('<p class="eyebrow">Key wins</p>')
    if kw != -1 and not re.search(r'class="win[ "]', text[kw:text.find("</section>", kw)]):
        errors.append("Key wins section carries no wins — delete the section rather "
                      "than shipping the heading (references/single-site/actions-and-wins/key-wins.md)")

    # A win photo has to travel inside the file. An attachment link is signed and
    # short-lived, so a photo left as a link breaks soon after the report is sent.
    # The sample's placeholder tiles are SVG; every real photo is embedded as JPEG.
    for src in sorted(set(re.findall(r'<figure><img src="([^"]*)"', text))):
        if src.startswith("data:image/svg"):
            errors.append("placeholder photo tile still in the report — fill the wins from the bundle")
        elif not src.startswith("data:"):
            errors.append("win photo linked rather than embedded: %.60s… — download it and pass "
                          "the file to fill_report.py (references/single-site/actions-and-wins/key-wins.md)" % src)

    # The run hours sample chart is a placeholder; the script draws the real one.
    if 'data-sample="run-hours"' in text:
        errors.append("sample run hours chart still in the report — fill it from the bundle's run_hours")

    # So are the sustainability ratings sample cards and charts; the fill draws the real ones.
    if 'data-sample="ratings"' in text:
        errors.append("sample sustainability ratings still in the report — fill them from the bundle's ratings")

    # A heatmap trimmed for a short-history site has to lose the same columns
    # from its header and from every row, so a ragged table means a missed row.
    for t in re.findall(r'<table class="hm">(.*?)</table>', text, re.S):
        cols = len(re.findall(r'<th class="mo"', t))
        widths = {len(re.findall(r'<td class="c ', r))
                  for r in re.findall(r"<tr[^>]*>.*?</tr>", t, re.S)} - {0}
        if widths - {cols}:
            errors.append("heatmap has %d month columns but rows with %s — trim header "
                          "and rows together" % (cols, sorted(widths)))

    present = re.findall(r'<p class="eyebrow">([^<]+)</p>', text)
    print("sections present: %s" % ", ".join(present))
    for w in warnings:
        print("warn:  %s" % w)
    for e in errors:
        print("ERROR: %s" % e)
    if errors:
        sys.exit("\n%d problem(s) — the report is not ready to hand over." % len(errors))
    print("ok — no sample data, placeholders or markers left.")


def check_portfolio(args):
    """The same promises for the portfolio report: no marker, placeholder or sample left,
    no site id in the text, no empty key wins, photos embedded, no en or em dash, and
    every ranked heatmap as wide in its rows as in its header."""
    use_mode("portfolio")
    text = open(args.report, encoding="utf-8").read()
    src = open(REF, encoding="utf-8").read()
    errors, warnings = [], []
    for marker in ("<!-- part:", "<!-- if:", "<!-- endif", "<!-- fill:", "<!-- /fill:", "<!-- style:", "<!-- logo:"):
        if marker in text:
            errors.append("marker left in the output: %s" % marker)
    for m in set(re.findall(r"\{\{[^}]+\}\}", text)) | set(re.findall(r"\{[a-z_]+_id\}", text)):
        errors.append("unresolved placeholder: %s" % m)
    for m in sorted(set(re.findall(r'data-sample="([a-z-]+)"', text))):
        errors.append("sample %s still in the report: fill it from the bundle" % m)
    found = set()
    # Company and assignee names are left out: a sample company or person can share a name with a
    # real one, and the team boards' data-sample marker already catches them unfilled.
    names = re.sub(r"<!-- fill: team-boards -->.*?<!-- /fill: team-boards -->", "", src, flags=re.S)
    for pat in (r'<span class="sn">([^<]+)</span>', r'<h3>([^<]+)</h3>',
                r'<title>([^<]+)</title>', r'<h1>([^<]+)</h1>', r'<div class="win[^"]*"[^>]*>.*?<p>(.+?)</p>'):
        found |= {m.group(1) for m in re.finditer(pat, names, re.S)}
    found |= {h for h in re.findall(r'href="([^"]+)"', src) if "cimenviro.com" in h}
    hits = sorted(x for x in found if len(x.strip()) >= 5 and x in text)
    for h in hits[:20]:
        errors.append("sample data still in the report: %s" % " ".join(re.sub(r"<[^>]+>", " ", h).split())[:90])
    visible = re.sub(r'\s(?:href|src)="[^"]*"', "", text)
    for m in sorted(set(re.findall(r"Site\s+\d+", visible))):
        errors.append("site id in visible text: %s, a system id the reader has no use for" % m)
    dashes = re.findall("[\u2013\u2014]|&ndash;|&mdash;", text)
    if dashes:
        errors.append("%d en or em dash(es) in the report: the portfolio page uses a hyphen" % len(dashes))
    kw = text.find('<p class="eyebrow">Key wins</p>')
    if kw != -1 and not re.search(r'class="win[ "]', text[kw:text.find("</section>", kw)]):
        errors.append("Key wins section carries no wins: delete the section rather than shipping the heading "
                      "(references/portfolio-leaderboard/actions-and-wins/key-wins.md)")
    for src_ in sorted(set(re.findall(r'<figure><img src="([^"]*)"', text))):
        if not src_.startswith("data:image/jpeg"):
            errors.append("win photo not embedded as JPEG: %.60s" % src_)
    for t in re.findall(r'<table class="hm wide">(.*?)</table>', text, re.S):
        cols = len(re.findall(r'<th class="mo"', t))
        widths = {len(re.findall(r'<td class="c[ "]', r)) for r in re.findall(r"<tr[^>]*>.*?</tr>", t, re.S)} - {0}
        if widths - {cols}:
            errors.append("ranked heatmap has %d month columns but rows with %s" % (cols, sorted(widths)))
    # each section by its eyebrow, or by its title where the eyebrow is a month
    month = re.compile(r"[A-Z][a-z]+ \d{4}$")
    heads = [(m.start(), m.group(2) if month.match(m.group(1)) and m.group(2) else m.group(1))
             for m in re.finditer(r'<p class="eyebrow">([^<]+)</p>(?:\s*<h2>([^<]+)</h2>)?', text)]
    print("sections present: %s" % ", ".join(h for _, h in heads))
    for w in warnings:
        print("warn:  %s" % w)
    for e in errors:
        print("ERROR: %s" % e)
    if errors:
        sys.exit("\n%d problem(s): the report is not ready to hand over." % len(errors))
    print("ok: no sample data, placeholders, markers or dashes left.")


def cmd_part(args):
    """One part on its own, for adding a section to a report that already exists.
    Re-scaffolding would throw away the filled-in report; this does not."""
    sections = [x.strip() for x in args.sections.split(",") if x.strip()] \
        if args.sections not in (None, "all") else list(SECTION_PARTS)
    resolve(sections)
    for name, lines in read_parts():
        if name == args.name:
            sys.stdout.write("\n".join(render(lines, sections)) + "\n")
            return
    sys.exit("unknown part: %s — run `parts` to list them" % args.name)


def cmd_parts(args):
    use_mode(args.mode)
    for name, lines in read_parts():
        owner = next((s for s, ps in SECTION_PARTS.items() if name in ps), None) \
            or ("any of " + ", ".join(PART_IF[name]) if name in PART_IF else "always")
        print("%-28s %4d lines   %s" % (name, len(lines), owner))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("scaffold", help="build a working file with only the parts needed")
    s.add_argument("--sections", help="comma-separated: %s (default all)" % ", ".join(SECTION_PARTS))
    s.add_argument("--out", required=True)
    s.set_defaults(func=cmd_scaffold)
    o = sub.add_parser("part", help="print one part's markup, for a report already built")
    o.add_argument("name")
    o.add_argument("--sections", help="the report's full section list, so the part's "
                                      "conditional blocks resolve the same way (default all)")
    o.set_defaults(func=cmd_part)
    c = sub.add_parser("check", help="find sample data, placeholders or markers left behind")
    c.add_argument("report")
    c.set_defaults(func=cmd_check)
    p = sub.add_parser("parts", help="list parts and which section owns each")
    p.set_defaults(func=cmd_parts)
    for q in (s, c, p):
        q.add_argument("--mode", choices=["single-site", "portfolio"], default="single-site")
    a = ap.parse_args()
    a.func(a)
