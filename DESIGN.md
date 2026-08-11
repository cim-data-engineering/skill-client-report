---
version: alpha
name: CIM
description: Design system for CIM and the PEAK Platform — an AI-powered building analytics platform for commercial property portfolios.
colors:
  primary: "#006CFF"
  primary-hover: "#0057D9"
  primary-active: "#0046AE"
  on-primary: "#FFFFFF"
  primary-container: "#E3EEFD"
  on-primary-container: "#0057D9"
  secondary: "#002556"
  secondary-hover: "#001B3F"
  on-secondary: "#FFFFFF"
  surface: "#FFFFFF"
  surface-dim: "#F7F9FC"
  surface-tint: "#F2F7FE"
  outline: "#E4E9F0"
  outline-strong: "#CFD7E3"
  text-heading: "#002556"
  text-body: "#3D4E68"
  text-muted: "#6B7A94"
  success: "#35C881"
  success-container: "#E8F8F0"
  on-success-container: "#22A96A"
  warning: "#F5A623"
  warning-container: "#FEF4E3"
  on-warning-container: "#A8700C"
  error: "#E5484D"
  error-container: "#FDECEC"
  on-error-container: "#C62B25"
  chart-benchmark: "#CBE0FB"
typography:
  display:
    fontFamily: Inter
    fontSize: 4rem
    fontWeight: 600
    lineHeight: 1.08
    letterSpacing: -0.022em
  h1:
    fontFamily: Inter
    fontSize: 2.5rem
    fontWeight: 600
    lineHeight: 1.2
    letterSpacing: -0.014em
  h2:
    fontFamily: Inter
    fontSize: 2rem
    fontWeight: 600
    lineHeight: 1.2
    letterSpacing: -0.014em
  h3:
    fontFamily: Inter
    fontSize: 1.5rem
    fontWeight: 600
    lineHeight: 1.2
  card-title:
    fontFamily: Inter
    fontSize: 1.0625rem
    fontWeight: 600
    lineHeight: 1.35
  body-lg:
    fontFamily: Inter
    fontSize: 1.125rem
    fontWeight: 400
    lineHeight: 1.55
  body:
    fontFamily: Inter
    fontSize: 1rem
    fontWeight: 400
    lineHeight: 1.55
  body-sm:
    fontFamily: Inter
    fontSize: 0.875rem
    fontWeight: 400
    lineHeight: 1.5
  label:
    fontFamily: Inter
    fontSize: 0.8125rem
    fontWeight: 500
    lineHeight: 1.35
  eyebrow:
    fontFamily: Inter
    fontSize: 0.8125rem
    fontWeight: 600
    lineHeight: 1.35
    letterSpacing: 0.1em
  metric:
    fontFamily: Inter
    fontSize: 2rem
    fontWeight: 600
    lineHeight: 1.05
    letterSpacing: -0.02em
    fontFeature: tnum
  mono:
    fontFamily: IBM Plex Mono
    fontSize: 0.6875rem
    fontWeight: 400
    lineHeight: 1.4
rounded:
  xs: 4px
  sm: 6px
  md: 10px
  lg: 14px
  xl: 20px
  full: 999px
spacing:
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 32px
  2xl: 48px
  3xl: 96px
components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.on-primary}"
    rounded: "{rounded.md}"
    padding: 0 18px
    height: 40px
  button-primary-hover:
    backgroundColor: "{colors.primary-hover}"
    textColor: "{colors.on-primary}"
  button-primary-active:
    backgroundColor: "{colors.primary-active}"
    textColor: "{colors.on-primary}"
  button-secondary:
    backgroundColor: "{colors.secondary}"
    textColor: "{colors.on-secondary}"
    rounded: "{rounded.md}"
    height: 40px
  button-secondary-hover:
    backgroundColor: "{colors.secondary-hover}"
    textColor: "{colors.on-secondary}"
  button-outline:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.primary}"
    rounded: "{rounded.md}"
    height: 40px
  button-ghost-hover:
    backgroundColor: "{colors.surface-tint}"
    textColor: "{colors.primary}"
  button-marketing:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.on-primary}"
    rounded: "{rounded.full}"
    height: 48px
  card:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text-body}"
    rounded: "{rounded.lg}"
    padding: 24px
  card-title:
    textColor: "{colors.text-heading}"
    typography: "{typography.card-title}"
  card-marketing:
    backgroundColor: "{colors.surface}"
    rounded: "{rounded.xl}"
    padding: 24px
  page:
    backgroundColor: "{colors.surface-dim}"
    textColor: "{colors.text-body}"
    typography: "{typography.body}"
  eyebrow:
    textColor: "{colors.primary}"
    typography: "{typography.eyebrow}"
  metric-value:
    textColor: "{colors.text-heading}"
    typography: "{typography.metric}"
  metric-label:
    textColor: "{colors.text-muted}"
    typography: "{typography.label}"
  delta-positive:
    backgroundColor: "{colors.success-container}"
    textColor: "{colors.on-success-container}"
    rounded: "{rounded.sm}"
    padding: 2px 7px
  delta-negative:
    backgroundColor: "{colors.error-container}"
    textColor: "{colors.on-error-container}"
    rounded: "{rounded.sm}"
    padding: 2px 7px
  status-watch:
    backgroundColor: "{colors.warning-container}"
    textColor: "{colors.on-warning-container}"
    rounded: "{rounded.full}"
    height: 24px
  status-dot-ok:
    backgroundColor: "{colors.success}"
    size: 7px
  status-dot-watch:
    backgroundColor: "{colors.warning}"
    size: 7px
  status-dot-fault:
    backgroundColor: "{colors.error}"
    size: 7px
  tag:
    backgroundColor: "{colors.primary-container}"
    textColor: "{colors.on-primary-container}"
    rounded: "{rounded.full}"
    height: 26px
  input:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text-heading}"
    rounded: "{rounded.md}"
    height: 40px
    padding: 0 12px
  input-outline:
    backgroundColor: "{colors.outline-strong}"
    height: 1px
  divider:
    backgroundColor: "{colors.outline}"
    height: 1px
  sidebar:
    backgroundColor: "{colors.secondary}"
    textColor: "{colors.on-secondary}"
    width: 248px
    padding: 18px 12px
  topbar:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text-heading}"
    height: 60px
  dialog:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text-body}"
    rounded: "{rounded.xl}"
    padding: 24px
  tooltip:
    backgroundColor: "{colors.secondary}"
    textColor: "{colors.on-secondary}"
    rounded: "{rounded.sm}"
    padding: 5px 9px
  chart-bar-primary:
    backgroundColor: "{colors.primary}"
    rounded: "{rounded.xs}"
  chart-bar-benchmark:
    backgroundColor: "{colors.chart-benchmark}"
    rounded: "{rounded.xs}"
  code:
    textColor: "{colors.text-muted}"
    typography: "{typography.mono}"
---

## Overview

Calm, quantified engineering credibility. CIM monitors millions of live building data points and tells property teams exactly what to fix — so the UI reads like precise instrumentation, not marketing. Navy anchors, one blue for action, white cards floating on a cool near-white page, and numbers given room to be read.

Two surfaces share these tokens: the **PEAK Platform** (dense operator dashboards — KPI tiles, score gauges, delta chips, alert lists) and the **marketing site** (statement headlines, pill CTAs, cropped architectural photography over a pale-blue circle). Same palette and typeface; marketing simply breathes more and rounds corners further.

## Colors

Navy is identity, blue is interaction, green and red are *only* ever measurement.

- **primary (#006CFF):** the single interactive colour — buttons, links, active nav, the primary chart series. Never decorative.
- **secondary (#002556):** brand navy. Full-bleed hero and footer fields, the app sidebar, all headings, tooltips. One navy field per page.
- **surface (#FFFFFF) / surface-dim (#F7F9FC):** white cards on a cool near-white page. Neutrals are navy-tinted; never warm grey, never pure black text.
- **success / error / warning:** carry meaning only — delta chips (green when the movement is *good*, so falling energy is green) and equipment status. A green pill must mean something.
- **chart-benchmark (#CBE0FB):** the pale blue used for benchmark bars and for the offset circle behind cropped building photography — CIM's most recognisable device.

## Typography

One grotesque does everything; hierarchy comes from weight and size, not from a second family. Headings are 600 with tight tracking; body is 400 at 1.55; metrics are 600 with tabular numerals so columns align. `eyebrow` is a single word above a headline — 13px, 600, uppercase, 0.1em, in primary blue. `mono` (IBM Plex Mono) is reserved for BMS point names, rule IDs and table micro-labels.

> **Substitution flagged:** CIM's licensed webfont was unavailable; Inter is the nearest match to the type in PEAK's own product screenshots. Swap `fontFamily` when the real font is supplied.

## Layout

8px-based scale, 24px card padding, 96px between marketing sections. Content maxes at 1200px (1360px for dashboards) with 24px gutters. The app is a 248px fixed navy sidebar plus a sticky 60px topbar over a 12-column card grid with 24px gaps. Sticky elements: marketing nav, app topbar, sidebar, table headers. Minimum touch target 44px.

## Elevation & Depth

Shadows are soft, low-opacity and navy-tinted — `rgba(0,37,86,.06–.10)`, vertical offset only. Two levels in-app: resting `0 1px 3px` and raised/menu `0 4px 14px`; one dramatic level for marketing collages and modals (`0 12px 32px` / `0 24px 64px`). Hover lifts a card 2px and steps the shadow up. Blur is used sparingly — sticky bars over content, and cards on navy sit at 6% white with a 16% white hairline. Focus is always a 3px `rgba(0,108,255,.35)` ring.

## Shapes

Radii climb with surface size: 6px chips, 10px controls, 14px product cards, 20px marketing cards and dialogs, `full` for pill CTAs, tags, delta chips and the floating marketing stat capsules. Chart bars round only their top corners (4px). Borders are 1px hairlines in `outline`; the only 2px rule is the active-nav indicator.

## Components

- **button-primary:** one per view. Hover darkens a step, press darkens again and scales to .985, disabled is 40% opacity. Marketing CTAs use `button-marketing` (pill, 48px); in-app buttons keep the 10px radius.
- **card:** the surface everything sits in — white, 14px, hairline border when on white, no border on `surface-dim`.
- **metric tile:** `metric-label` above `metric-value`, with a delta chip inline and an optional `↗` drill-in.
- **delta chip:** `delta-positive` / `delta-negative` chosen by whether the change is *good*, not by its sign.
- **alert row:** severity glyph in a tinted square, title, then the impact line phrased as "Fix to maintain: Energy use & carbon emissions", then site · equipment (mono) · assignee.
- **sidebar:** navy, reversed logo top-left, active item on a 10% white wash with a 2px blue inset rule and a count pill on the right.

## Do's and Don'ts

**Do**
- Lead with a number and a plain caption: "18% — Annual portfolio energy reduction".
- Write sentence case, second person ("your portfolio"), and let PEAK act: "PEAK monitors millions of data points".
- Keep motion functional: 140ms controls, 220ms panels, 600ms fade-and-rise reveals; standard easing.
- Use the real duotone brand glyphs for marketing features and Lucide (24px, 1.75px stroke) for UI icons.
- Crop architectural photography into a circle over an offset `chart-benchmark` circle.

**Don't**
- No emoji, anywhere.
- No purple or multi-hue gradients, no cards with a coloured left border, no bounce or parallax.
- Don't use green or red as decoration, and don't tint a whole card by status.
- Don't put two navy fields mid-page, or frosted glass on white.
- Don't recolour, re-space or rebuild the CIM logo; use the white version on navy or photography.
