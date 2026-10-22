# AGENTS.md

What to check before committing a change to this skill. How the skill works is in `SKILL.md`; this file only holds the rules for changing it.

## Where things live

- `SKILL.md` orchestrates: which report, build order, sections and their wiring. It points down to the references, never the other way
- `references/<report>/<section>/` owns one section: business logic a person can read and maintain, and a Data block of the exact MCP calls, so a run spends nothing on discovery. A reference links nothing above or beside it; naming a `DESIGN.md` component is fine
- The scripts make every figure, row, link and line of text on the page. Change output in the script, never in a filled report
- `DESIGN.md` and `BRAND.md` hold the look only: tokens, components and print rules, no business logic

## Before you commit

1. **No customer data.** Test live on Skyline Tower (site 371) or the Demo Starcourt Mall portfolio. Samples use PEAK's demo contractors (Demo Hawkins Air, Demo Automated Controls) and invented names (Northwind Estates, 12 Harbour Lane). No other client, site, contractor or person name, id or live figure in any file, comment, sample or commit message, and never a real person's name. Build into `report/`, which git ignores, or outside the repo
2. **No history.** Files read as present-tense instructions. Nothing from chat, earlier runs or past commits, and no "used to", "previously" or "we found". The reason for a change goes in its commit message
3. **Production ready and minimal.** Make the smallest change that does the job, in the words the file already uses. Add no sections, caveats or commentary the change doesn't need
4. **References in sync.** A change to a script's behaviour, calls or printed text updates its reference in the same commit. A change to wiring or order updates `SKILL.md` Wiring and the registry in `scripts/report.py`
5. **Link templates stay put.** The URLs in the references are written out by hand on purpose. Change one only when PEAK's page changes, and open the link to test it
6. **Style-only changes are CSS only.** A colour, size or spacing tweak edits the CSS. `DESIGN.md` changes only where a token or rule becomes untrue, with no added rationale
7. **Verify, scaled to the change.**
   - Docs only: no script changed
   - Script change: build Skyline Tower or Demo Starcourt Mall end to end; the `report.py fill` check passes
   - Layout or CSS change: print to PDF in Chrome and look at every page break
   - Refactor: run `report.py bundle` and `fill` on a copy of an earlier run's `report/` folder, before and after, and diff `data.json` and the HTML
