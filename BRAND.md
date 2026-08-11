---
name: Hoffman Building Technologies
service-name: Building Automation & Smart Buildings

colors:
  primary: "#08b06d"              # HBT green — the single accent
  primary-container: "#e4f7ee"    # light green tint (tags)
  on-primary-container: "#0a6b3c" # readable on primary-container (AA)
  secondary: "#011659"            # HBT navy — masthead, rules
  on-secondary: "#FFFFFF"
  on-secondary-muted: "#b6c2df"   # muted labels on navy masthead
  chart-benchmark: "#c9d3e8"      # comparison series (navy tint)
  text-heading: "#011659"

fonts:
  display: Figtree
  text: Figtree
  # mono: left commented — no HBT mono family, keep CIM's JetBrains Mono

logos:
  reversed: assets/brand/logo-hbt-white.png     # 926×300, transparent
  full-color: assets/brand/logo-hbt-color.png   # 851×218, transparent
---

## How to rebrand

1. Uncomment and edit the keys above — only what differs from CIM.
2. Add your logo files under `assets/brand/` and point the `logos:` keys at them.
3. If a font family is not on Google Fonts, drop its woff2 files in `assets/fonts/`.
4. Validate the palette: copy your `colors:` values over the matching tokens in a
   scratch copy of `DESIGN.md` and run `npx @google/design.md lint` on it — the
   linter checks WCAG AA contrast and broken references.
5. Generate a report; compare against `assets/reference-report.html` for structure.

To preview what a filled-in file looks like, see
`assets/brand-example/BRAND.example.md` (fictional partner "Automated Controls",
with working logo files beside it).

## What you own vs what upstream owns

| Partner-owned (edit freely)      | Upstream-owned (never edit)        |
| :------------------------------- | :--------------------------------- |
| `BRAND.md`                       | `DESIGN.md`                        |
| `assets/brand/*`                 | `SKILL.md`                         |
| `assets/fonts/*` (additions)     | `assets/reference-report.html`     |
|                                  | `assets/logo.svg`, `assets/logo-white.svg`, `assets/trophy.svg` |

Editing upstream-owned files forfeits clean merges: this repo keeps improving, and
a fork that only touches the partner-owned column can `git merge` upstream at any
time without conflicts.

## Rules the generator applies

- Missing file, or a key left commented → the CIM default. No partial surprises.
- Keys outside the whitelist above are ignored.
- When `secondary` is overridden, the screen shadow re-derives as that hue at 8%
  opacity (the `shadow` token role in DESIGN.md).
- When any brand override is active, platform strings read `PEAK · Site N` — the
  CIM prefix is dropped. `Powered by PEAK` is always kept and cannot be removed.
- Unbranded (default) reports keep `CIM PEAK` and
  `Prepared by CIM — Data Driven Operations`.
