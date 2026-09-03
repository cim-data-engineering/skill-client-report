#!/usr/bin/env python3
"""Assemble and verify a client report from assets/reference-report.html.

The reference report is the design system compiled: its <style> block holds every
DESIGN.md token and component, and each report section is marked off as a part.
Rather than re-emit ~19KB of CSS and the markup of sections nobody asked for,
scaffold the file you need and edit the sample data in place.

    scaffold  copy the shell, the always-on parts and the selected sections
    part      print one part's markup, to add a section to a report already built
    check     look for sample data, sample links and markers left behind
    parts     list part names and sizes

    python3 scripts/build_report.py scaffold --sections equipment-health,key-wins \
        --out skyline-q3.html
    python3 scripts/build_report.py check skyline-q3.html
"""

import argparse, os, re, sys

REF = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "reference-report.html")

ALWAYS = ["shell", "masthead", "analytics-overview", "footer"]
SECTION_PARTS = {
    "equipment-health": ["equipment-health-snapshot", "monthly-equipment-health"],
    "indoor-environment": ["indoor-environment-snapshot", "monthly-thermal-comfort"],
    "alerts-resolved": ["monthly-alerts", "assignee-leaderboard"],
    "key-wins": ["key-wins"],
}
# Parts that render for any of several sections. Operational impact is a frame
# around rows the sections own, so it only stands if one of them is in.
ROW_SECTIONS = ["equipment-health", "indoor-environment", "alerts-resolved"]
PART_IF = {"operational-impact": ROW_SECTIONS, "notes": ROW_SECTIONS}
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


def cmd_scaffold(args):
    sections = [s.strip() for s in args.sections.split(",") if s.strip()] \
        if args.sections not in (None, "all") else list(SECTION_PARTS)
    keep = resolve(sections)
    body = []
    for name, lines in read_parts():
        if name in keep:
            body += render(lines, sections)
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
    for pat in (r'<td class="name">([^<]+)</td>', r'<td class="co">([^<]+)</td>',
                r'<h3>([^<]+)</h3>', r'<title>([^<]+)</title>',
                # narrative slots: long, site-specific sentences, so an exact
                # match means the sample's commentary was left in place. h2note
                # is deliberately absent — it carries window and method wording
                # that is correct for every report and recurs legitimately.
                r'<p class="chartnote">([^<]+)</p>', r'<p class="snap">([^<]+)</p>', r'<div class="win">\s*<h3>[^<]*</h3>\s*<p>([^<]+)</p>'):
        for m in re.finditer(pat, src, re.S):
            found.add(m.group(1))
    for m in re.finditer(r'<p class="refs">(.*?)</p>', src, re.S):
        found |= set(re.findall(r'>([^<>]{8,})</a>', m.group(1)))
    # only platform links are report data — font and preconnect hosts stay
    found |= {h for h in re.findall(r'href="([^"]+)"', src) if "cimenviro.com" in h}
    stop = {"CIM", "Total"}
    return sorted(s.strip() for s in found if len(s.strip()) >= 5 and s.strip() not in stop)


def cmd_check(args):
    text = open(args.report, encoding="utf-8").read()
    errors, warnings = [], []

    for marker in ("<!-- part:", "<!-- if:", "<!-- endif"):
        if marker in text:
            errors.append("marker left in the output: %s" % marker)
    for m in set(re.findall(r"\{\{[^}]+\}\}", text)) | set(re.findall(r"\{[a-z_]+_id\}", text)):
        errors.append("unresolved placeholder: %s" % m)

    hits = [s for s in sample_strings() if s in text]
    for h in hits[:20]:
        errors.append("sample data still in the report: %s" % (h[:90] + ("…" if len(h) > 90 else "")))
    if len(hits) > 20:
        errors.append("... and %d more sample values" % (len(hits) - 20))

    ref = open(REF, encoding="utf-8").read()
    site = re.search(r"Site (\d+) · ([^,<]+)", ref)
    if site:
        for token in (site.group(1), site.group(2)):
            if token in text:
                warnings.append("reference site's own %s appears — fine only if this "
                                "report really is for it" % ("id %s" % token if token.isdigit() else "name %r" % token))

    # Key wins is the one section that can be scaffolded and then find nothing
    # to say: an empty heading is worse than no heading, so it must be deleted.
    kw = text.find('<p class="eyebrow">Key wins</p>')
    if kw != -1 and 'class="win"' not in text[kw:text.find("</section>", kw)]:
        errors.append("Key wins section carries no wins — delete the section rather "
                      "than shipping the heading (references/key-wins.md)")

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
    a = ap.parse_args()
    a.func(a)
