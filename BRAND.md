---
# BRAND.md — partner branding overlay for the client report.
#
# Leave this file untouched and every report renders in CIM's default brand.
# To rebrand, uncomment only the keys you change; anything left commented
# (or this file missing entirely) falls back to the CIM defaults in
# DESIGN.md and SKILL.md. Only the keys below are honored — any other key
# is ignored at generation time.
#
# The values shown are a worked example for a fictional partner,
# "Automated Controls". A live copy of this file with every key filled in
# sits at assets/brand-example/BRAND.example.md.

# ── Identity ────────────────────────────────────────────────────────────
# name: Automated Controls
# service-name: Smart Building Operations

# ── Colors — identity tokens only ───────────────────────────────────────
# These eight tokens are the brand surface. Neutrals (surface*, outline*,
# text-body, text-muted) and measurement colors (success/warning/error and
# their containers) are part of the design system and stay upstream-owned.
# colors:
#   primary: "#7C3AED"              # the single accent
#   primary-container: "#EDE7FD"    # light tint of primary (tags)
#   on-primary-container: "#6427CE" # readable on primary-container
#   secondary: "#221A44"            # identity anchor — masthead, rules
#   on-secondary: "#FFFFFF"         # text on the masthead
#   on-secondary-muted: "#CBC3F2"   # muted labels on the masthead
#   chart-benchmark: "#D9D2F7"      # comparison chart series
#   text-heading: "#221A44"         # headings — normally tracks secondary

# ── Fonts — family swaps only ───────────────────────────────────────────
# Three slots mapped onto the DESIGN.md typography roles. Sizes, weights
# and line-heights are locked upstream. Families on Google Fonts load
# CDN-first with an assets/fonts fallback; for licensed families, drop
# woff2 files in assets/fonts and they load locally only.
# fonts:
#   display: Space Grotesk          # h1, h2, card-title, metric
#   text: Inter                     # body, body-sm, label, eyebrow
#   mono: JetBrains Mono            # table headers, IDs, footer

# ── Logos — paths to files you add ──────────────────────────────────────
# Put your logo files in assets/brand/ (never overwrite assets/logo*.svg).
# The reversed (white) variant is required for the dark masthead; SVG
# preferred, PNG accepted (inlined as a data URI). Don't recolor, re-space
# or rebuild logos to fit — supply proper variants.
# logos:
#   reversed: assets/brand/automated-controls-white.svg
#   full-color: assets/brand/automated-controls.svg
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
