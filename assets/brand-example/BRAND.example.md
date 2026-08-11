---
# BRAND.example.md — a complete, working example of a partner rebrand for the
# fictional partner "Automated Controls". Every overridable key is filled in.
#
# To try it: copy the frontmatter below over the commented template in
# /BRAND.md, copy the two logo SVGs from this folder into assets/brand/,
# and update the logos: paths accordingly. Generated reports will render
# in the Automated Controls brand; delete the overrides to return to CIM.

name: Automated Controls
service-name: Smart Building Operations

colors:
  primary: "#7C3AED"
  primary-container: "#EDE7FD"
  on-primary-container: "#6427CE"
  secondary: "#221A44"
  on-secondary: "#FFFFFF"
  on-secondary-muted: "#CBC3F2"
  chart-benchmark: "#D9D2F7"
  text-heading: "#221A44"

fonts:
  display: Space Grotesk
  text: Inter
  mono: JetBrains Mono

logos:
  reversed: assets/brand-example/automated-controls-white.svg
  full-color: assets/brand-example/automated-controls.svg
---

## What this example shows

- **Identity**: masthead reads "Prepared by **Automated Controls — Smart Building
  Operations** · Powered by PEAK"; platform strings become `PEAK · Site N`.
- **Colors**: violet accent replaces CIM blue, deep indigo masthead replaces navy,
  pale violet benchmark series replaces pale blue. Neutrals and the green/amber/red
  measurement colors are untouched — they are not brand.
- **Fonts**: all three families are on Google Fonts, so no woff2 files need to
  ship; the generated report keeps the CDN-first + local-fallback loading rule.
- **Logos**: original SVGs beside this file, both variants; the reversed (white)
  wordmark sits on the dark masthead, inlined into the report at generation time.
