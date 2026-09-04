---
version: alpha
name: CIM
description: Print-first theme for client-facing A4 performance reports — a white sheet with one dark masthead, instrument-grade numbers, and colour reserved for measurement. Rebrand by editing tokens only; the prose speaks in token roles, not brand names.
colors:
  primary: "#006CFF"
  primary-container: "#E3EEFD"
  on-primary-container: "#0057D9"
  secondary: "#002556"
  on-secondary: "#FFFFFF"
  on-secondary-muted: "#CBE0FB"
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
  shadow: "rgba(0, 37, 86, 0.08)"
typography:
  h1:
    fontFamily: Archivo
    fontSize: 2.5rem
    fontWeight: 700
    lineHeight: 1.15
    letterSpacing: -0.014em
  h2:
    fontFamily: Archivo
    fontSize: 2rem
    fontWeight: 600
    lineHeight: 1.2
    letterSpacing: -0.014em
  card-title:
    fontFamily: Archivo
    fontSize: 1.0625rem
    fontWeight: 600
    lineHeight: 1.35
  body:
    fontFamily: IBM Plex Sans
    fontSize: 1rem
    fontWeight: 400
    lineHeight: 1.55
  body-sm:
    fontFamily: IBM Plex Sans
    fontSize: 0.875rem
    fontWeight: 400
    lineHeight: 1.5
  label:
    fontFamily: IBM Plex Sans
    fontSize: 0.8125rem
    fontWeight: 500
    lineHeight: 1.35
  eyebrow:
    fontFamily: IBM Plex Sans
    fontSize: 0.8125rem
    fontWeight: 600
    lineHeight: 1.35
    letterSpacing: 0.1em
  metric:
    fontFamily: Archivo
    fontSize: 2rem
    fontWeight: 700
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
  lg: 14px
  full: 999px
spacing:
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 32px
  2xl: 48px
components:
  page:
    backgroundColor: "{colors.surface-dim}"
    textColor: "{colors.text-body}"
    typography: "{typography.body}"
  sheet:
    backgroundColor: "{colors.surface}"
    width: 210mm
  masthead:
    backgroundColor: "{colors.secondary}"
    textColor: "{colors.on-secondary}"
    padding: 48px 56px
  masthead-label:
    textColor: "{colors.on-secondary-muted}"
    typography: "{typography.label}"
  eyebrow:
    textColor: "{colors.primary}"
    typography: "{typography.eyebrow}"
  card:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text-body}"
    rounded: "{rounded.lg}"
    padding: 24px
  card-title:
    textColor: "{colors.text-heading}"
    typography: "{typography.card-title}"
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
  rating-positive:
    backgroundColor: "{colors.success-container}"
    textColor: "{colors.on-success-container}"
    rounded: "{rounded.full}"
    height: 24px
  rating-warning:
    backgroundColor: "{colors.warning-container}"
    textColor: "{colors.on-warning-container}"
    rounded: "{rounded.full}"
    height: 24px
  rating-negative:
    backgroundColor: "{colors.error-container}"
    textColor: "{colors.on-error-container}"
    rounded: "{rounded.full}"
    height: 24px
  rating-neutral:
    backgroundColor: "{colors.surface-tint}"
    textColor: "{colors.text-muted}"
    rounded: "{rounded.full}"
    height: 24px
  heatmap-cell:
    textColor: "{colors.text-heading}"
    typography: "{typography.body-sm}"
  heatmap-band-excellent:
    backgroundColor: "#D7F4E6"
  heatmap-band-good:
    backgroundColor: "#EFFBF5"
  heatmap-band-average:
    backgroundColor: "#FDEDD3"
  heatmap-band-poor:
    backgroundColor: "#FADBDC"
  tag:
    backgroundColor: "{colors.primary-container}"
    textColor: "{colors.on-primary-container}"
    rounded: "{rounded.full}"
    height: 26px
  table-header:
    textColor: "{colors.text-muted}"
    typography: "{typography.mono}"
  table-rule-strong:
    backgroundColor: "{colors.secondary}"
    height: 2px
  divider:
    backgroundColor: "{colors.outline}"
    height: 1px
  chart-bar-primary:
    backgroundColor: "{colors.primary}"
    rounded: "{rounded.xs}"
  chart-bar-benchmark:
    backgroundColor: "{colors.chart-benchmark}"
    rounded: "{rounded.xs}"
  chart-baseline:
    backgroundColor: "{colors.outline-strong}"
    height: 1px
  footer:
    textColor: "{colors.text-muted}"
    typography: "{typography.mono}"
---

## Overview

Calm, quantified engineering credibility. The report reads like precise instrumentation, not marketing: a white A4 sheet, one dark masthead, numbers given room to be read, and colour spent only where it measures something. The artefact is an HTML page printed to PDF and handed to a client — everything must hold up on paper, with no hover, tooltip or motion carrying information.

This file is a theme. Every rule below is written against token roles (`primary`, `secondary`, `rating-*`), so rebranding is a token swap; the prose should never need editing. Partner rebranding never edits this file at all — brand overrides live in `BRAND.md` at the repo root, and any value not overridden there falls back to the defaults here.

## Colors

`secondary` is identity, `primary` is accent, green and red are *only* ever measurement.

- **primary:** the single accent — links, eyebrows, the primary chart series, inline score-bar fills. Never decorative.
- **secondary:** the identity anchor — the masthead field, all headings, and every 2px strong rule. The masthead is the only dark field on the page.
- **surface / surface-dim:** the white sheet, previewed on a `surface-dim` backdrop on screen; `surface-dim` also backs the notes/methodology band. Neutrals are tinted toward `secondary` — never warm grey, never pure black text.
- **success / warning / error:** carry meaning only — delta chips and rating chips. Green means the movement is *good* (falling energy is green), not that the number went up.
- **chart-benchmark:** the comparison series beside `primary`; **on-secondary-muted** is its counterpart for labels sitting on the masthead.

## Typography

Three family roles split the work; the families themselves are brand, named only in the `typography` tokens. The **display family** (`h1`, `h2`, `card-title`, `metric`) carries display — the report title, section headings, card titles and metric figures — at 600–700 with tight tracking in `text-heading`, so the numbers land with weight. The **text family** (`body`, `body-sm`, `label`, `eyebrow`) carries everything read at length: body at 400 and 1.55, labels at 500, the eyebrow at 600 uppercase. The **mono family** (`mono`) is reserved for table headers, equipment/point IDs, and the footer (400 for rest, 500 for emphasis). Metrics use tabular numerals so columns align. Set the root at 14px so 1rem body prints near 10.5pt on A4. Load families on Google Fonts from the CDN, one `@font-face` per subset. The report is a single file that leaves the repo, so a relative `assets/fonts` path would not resolve where the reader opens it; carry the offline case in the `font-family` stack instead, ending each of the three tokens in the system faces. A family not on Google Fonts has no CDN to load from, so embed its woff2 as a base64 data URI in the `src` and the file stays self-contained.

## Layout

The sheet is A4 portrait (210mm, ≈794px), centred on `page` for screen preview. Sections pad 48px 56px and are separated by `divider` hairlines; the 8px spacing scale governs everything inside, with 24px card padding. For export: `@page { size: A4; margin: 0 }` with margins carried by section padding so the masthead bleeds; `print-color-adjust: exact` everywhere; `page-break-inside: avoid` on sections, tables and figures; `thead` repeats across page breaks. A table longer than one page is the exception — a `heatmap` with a row per level usually is — and takes `page-break-inside: auto` with the avoid moved down to its rows, so it breaks between rows instead of jumping to a fresh page and stranding a gap.

## Elevation & Depth

The page is flat — hierarchy comes from rules and whitespace, not shadows. On screen the sheet may float on one soft shadow in `shadow` — the `secondary` hue at 8% opacity, re-derived whenever `secondary` changes; in print there are none.

## Shapes

Radii climb with size: 4px chart-bar tops (top corners only), 6px delta chips, 14px cards, `full` for rating chips and tags. Borders are 1px hairlines in `outline`; 2px rules belong to `secondary` alone — opening a table and closing its total row.

## Components

- **masthead:** `secondary` field with an `eyebrow` in `on-secondary-muted`, the report title in `h1`, then a metadata row (period, comparison, site, issue date) as `masthead-label` over values, split from the title by a hairline at 18% `on-secondary`.
- **section header:** three stacked lines — an `eyebrow` in `primary` naming the section, a statement in `h2` saying what the section shows ("What we monitor at {site}"), and an optional `body-sm` byline in `text-muted` carrying the as-at date or period — with 24px clear before the content. The statement is the headline, never the section name.
- **metric row:** `metric-value` with a plain caption beside it, a one-line `body-sm` explanation in `text-muted` beneath, and a rating or delta chip.
- **delta chip:** `delta-positive` / `delta-negative` chosen by whether the change is *good*, not by its sign, always with a direction glyph and words.
- **rating chip:** benchmark-band label in the matching `rating-*` container — always words, never colour alone. Excellent and Good are both `rating-positive`; Average is `rating-warning`; Poor is `rating-negative`; `rating-neutral` is for non-benchmark labels (e.g. Continuous, Modelled).
- **table:** `table-rule-strong` on top and above the total row; `table-header` in mono uppercase; numerals right-aligned and tabular; hairline row rules. Inline 0–100 score bars use an `outline` track with a `primary` fill and the value beside them — semantic colour stays on the rating chip, never the bar.
- **heatmap:** a table whose score cells are filled by benchmark band — the one place the row itself carries colour, because the grid *is* the reading. The four `heatmap-band-*` fills are mixed from the measurement colours over `surface` at one matched strength — `success`, `warning` and `error` at 22%, with Excellent and Good taking two steps of the same green (22% and 9%) because the `*-container` tokens would put both on one fill and collapse the two bands that hold most of the data. Re-derive all four whenever a measurement colour changes; they are deliberately brand-stable, since what a score *means* does not change with the partner. The numeral stays `heatmap-cell` at every band, so the value is legible without the fill and the page still reads in grayscale — but only the newest column carries weight, at 600 in `text-heading`; earlier columns drop to 400 in `text-body`. A grid of uniformly bold figures reads as noise, and the reader's question is where the building stands *now*, with the history as context. `text-body` rather than `text-muted` is the floor here, because `text-muted` falls under 4.5:1 against the lighter band fills. Cells are separated by `surface` hairlines rather than `outline`, so each column reads as one continuous field. A band key above the table names all four bands in words; count and identifier columns flanking the grid stay uncoloured and keep normal `outline` rules. Every heatmap states its benchmark and picks a score precision fine enough that rounding cannot cross a band edge.
- **chart:** first series `primary`, comparison `chart-benchmark`; values labelled directly on points/bars; axis labels in `mono` and `text-muted`; gridlines in `outline`. A `body-sm` note in `text-muted` under each chart states the one thing the reader should take from it.
- **notes band:** a `surface-dim` section for methodology and footnotes, numbered, in `body-sm`.
- **footer:** single `mono` line in `text-muted` — site identity left, issue date right.

## Do's and Don'ts

**Do**
- Lead with a number and a plain caption: "18% — annual portfolio energy reduction".
- Write sentence case, and state findings as measured facts, not marketing claims.
- Label values directly on charts — a printed page has no tooltips.
- Keep every page legible in grayscale: chips and deltas carry words and glyphs, never colour alone.
- Check print preview before issuing: clean page breaks, colours exported, table headers repeating.

**Don't**
- No emoji, anywhere. No gradients, no decorative colour, no cards with a coloured left border.
- Don't use green or red as decoration, and don't tint a whole card or row by status. The `heatmap` is the one sanctioned exception: its cells are tinted by measured band, not by status, and the fill *is* the chart.
- Don't add a second dark field — the masthead is the only one.
- Don't let hover, tooltips or motion carry information; the deliverable is a PDF.
- Don't recolour, re-space or rebuild the logo; use the reversed (white) version on the masthead.
