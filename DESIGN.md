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
  impact-water: "#00A3B5"
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
    textColor: "{colors.secondary}"
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
  impact-tag:
    textColor: "{colors.text-muted}"
    typography: "{typography.eyebrow}"
    fontSize: 0.6875rem
    dotSize: 8px
  win-level:
    textColor: "{colors.text-heading}"
    typography: "{typography.label}"
  win-savings:
    textColor: "{colors.text-heading}"
    fontWeight: 600
  company-logo:
    backgroundColor: "{colors.surface}"
    borderColor: "{colors.outline}"
    rounded: "{rounded.xs}"
    size: 40px
    padding: 2px
  win-photo:
    borderColor: "{colors.outline}"
    rounded: "{rounded.sm}"
    width: 168px
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
  chart-to-date:
    backgroundColor: "{colors.surface-tint}"
    rounded: "{rounded.xs}"
---

## Overview

Calm, quantified engineering credibility. The report reads like precise instrumentation, not marketing: a white A4 sheet, one dark masthead, numbers given room to be read, and colour spent only where it measures something. The artefact is an HTML page printed to PDF and handed to a client — everything must hold up on paper, with no hover, tooltip or motion carrying information.

This file is a theme. Every rule below is written against token roles (`primary`, `secondary`, `rating-*`), so rebranding is a token swap; the prose should never need editing. Partner rebranding never edits this file at all — brand overrides live in `BRAND.md` at the repo root, and any value not overridden there falls back to the defaults here.

## Colors

`secondary` is identity, `primary` is accent, green and red are *only* ever measurement. The **impact tag** dot is the single place colour marks a *category* instead, and it earns that by staying an 8px dot beside a word that already says the same thing.

- **primary:** the single accent — links, the primary chart series, inline score-bar fills. Never decorative. The only text set in `primary` is a link, so no label or heading reads as one.
- **secondary:** the identity anchor — the masthead field, all headings and section eyebrows, and every 2px strong rule. The masthead is the only dark field on the page.
- **surface / surface-dim:** the white sheet, previewed on a `surface-dim` backdrop on screen; `surface-dim` also backs the notes/methodology band. Neutrals are tinted toward `secondary` — never warm grey, never pure black text.
- **success / warning / error:** carry meaning only — delta chips and rating chips. Green means the movement is *good* (falling energy is green), not that the number went up.
- **chart-benchmark:** the comparison series beside `primary`; **on-secondary-muted** is its counterpart for labels sitting on the masthead.
- **impact-water:** the one hue the palette carries purely to separate a category, held by the water impact dot. It exists because the five other impacts already map onto tokens on the page and water has nothing to borrow that a reader would not misread as one of them. Like the `heatmap-band-*` fills it is brand-stable and stays out of `BRAND.md`: what an impact *is* does not change with the partner.

## Typography

Three family roles split the work; the families themselves are brand, named only in the `typography` tokens. The **display family** (`h1`, `h2`, `card-title`, `metric`) carries display — the report title, section headings, card titles and metric figures — at 600–700 with tight tracking in `text-heading`, so the numbers land with weight. The **text family** (`body`, `body-sm`, `label`, `eyebrow`) carries everything read at length: body at 400 and 1.55, labels at 500, the eyebrow at 600 uppercase. The **mono family** (`mono`) is reserved for table headers, equipment/point IDs, and the page number (400 for rest, 500 for emphasis). Metrics use tabular numerals so columns align. Set the root at 14px so 1rem body prints near 10.5pt on A4. Load families on Google Fonts from the CDN, one `@font-face` per subset. The report is a single file that leaves the repo, so a relative `assets/fonts` path would not resolve where the reader opens it; carry the offline case in the `font-family` stack instead, ending each of the three tokens in the system faces. A family not on Google Fonts has no CDN to load from, so embed its woff2 as a base64 data URI in the `src` and the file stays self-contained.

## Layout

The sheet is A4 portrait (210mm, ≈794px), centred on `page` for screen preview. Sections pad 48px 56px and are separated by `divider` hairlines; the 8px spacing scale governs everything inside, with 24px card padding. For export: `@page { size: A4; margin: 0 0 10mm }`, the top and sides carried by section padding so the masthead bleeds, and the foot holding the page number, "Page 2 of 9", bottom right at the 56px gutter in `mono` and `text-muted`; and `box-decoration-break: clone` on sections so a section that runs onto another page repeats its padding there — nothing prints against the paper's edge either side of a break. `print-color-adjust: exact` everywhere. A page break falls between components, never through one: section headers, stat grids, metric rows, charts, win cards, notes items and table rows never split; a section header, chart title, legend or band key keeps with what follows it, and a link row, chart source or note, or total row keeps with what precedes it. A table under about half a page moves to the next page whole. A longer one — a `heatmap` with a row per level often is — breaks between rows instead of jumping to a fresh page and stranding a gap: its `thead` repeats on every page it reaches, its first two rows stay with the header and its last two with the total. The run hours chart is a table for the same reason, one SVG strip per unit under a day header that repeats. Page one holds the masthead, analytics overview and operational impact: in print the spacing between their blocks tightens so all three fit the first sheet — masthead padding 28px, those two sections 28px and 20px, impact rows 8px, the site photo 100px to match the title block. Type sizes never change for the fit. The print rules target Chromium (Chrome or Edge, Save as PDF), so check print preview there.

## Elevation & Depth

The page is flat — hierarchy comes from rules and whitespace, not shadows. On screen the sheet may float on one soft shadow in `shadow` — the `secondary` hue at 8% opacity, re-derived whenever `secondary` changes; in print there are none.

## Shapes

Radii climb with size: 4px chart-bar tops (top corners only), 6px delta chips and photo tiles, 14px cards, `full` for rating chips and tags. Borders are 1px hairlines in `outline`; 2px rules belong to `secondary` alone — opening a table and closing its total row.

## Components

- **masthead:** `secondary` field with an `eyebrow` in `on-secondary-muted`, the report title in `h1`, then a metadata row (reporting period, author, issue date) as `masthead-label` over values, split from the title by a hairline at 18% `on-secondary`. A client logo dark enough to vanish on the field sits on a `surface` tile at `rounded.sm`.
- **section header:** three stacked lines — an `eyebrow` in `secondary` naming the section, a statement in `h2` saying what the section shows ("What we monitor at {site}"), and an optional `body-sm` byline in `text-muted` carrying the as-at date or period — with 24px clear before the content. The statement is the headline, never the section name.
- **metric row:** `metric-value` with a plain caption beside it, a one-line `body-sm` explanation in `text-muted` beneath, and a rating or delta chip.
- **delta chip:** `delta-positive` / `delta-negative` chosen by whether the change is *good*, not by its sign, always with a direction glyph and words.
- **rating chip:** benchmark-band label in the matching `rating-*` container — always words, never colour alone. Excellent and Good are both `rating-positive`; Average is `rating-warning`; Poor is `rating-negative`; `rating-neutral` is for non-benchmark labels (e.g. Continuous, Modelled).
- **impact tag:** the building outcome a key win belongs to — Energy, Comfort, Reliability, Water, Safety, Other — set above the win's heading as an `eyebrow` at the smallest step in `text-muted`, led by an 8px dot. Impact is a *category* dimension, not a measurement: it says which kind of outcome the win sits under, never how good or bad anything is. So the colour sits on the dot alone and never on the text, and the word is what carries the meaning — the dot is there to let a reader scan a page of wins for the one they came for. That also keeps it clear of the rule that green and red measure: `error` on a Safety dot is a category marker, not a bad reading. Dots map onto tokens already on the page — energy `warning`, comfort `primary`, reliability `secondary`, safety `error`, water `impact-water`, other `outline-strong` — so a rebrand carries the tag with it. Six categories is the whole vocabulary; never invent a seventh, and never colour a whole win card by its impact.
- **win level:** where the win's equipment is, under its heading: the key "Level" at the impact tag's eyebrow step in `text-muted`, then the level name in `label` and `text-heading`. It places the win in the building and carries no colour.
- **win savings:** the saving a win's tickets reference, set inside its text in `text-heading` at weight 600. It is the only emphasis a win's text carries: a figure in a sentence, never a chip, a callout or a colour.
- **win photos:** photos and screenshots off the win's action tickets, set as evidence and never as decoration. Each is a `figure` holding one `rounded.sm` tile with an `outline` hairline, and no caption: the win's text explains them. Two to four run in one row under the level line, a column each, cropped square, except a pair, which crops to 3:2 so its row keeps the height of three. A single photo sits 168px wide beside the text instead, so a one-photo win stays the height of its words. Photos embed in the file at about twice their printed size, so the report stays one file that prints sharp. Never tint, filter or crop a photo into a shape, and never give a win an image that does not bear on it.
- **company logo:** the assignee's company logo from PEAK, in a 40px square tile before their name in the actions leaderboard, as PEAK shows it: `surface`, an `outline` hairline, `rounded.xs`, the logo scaled to fit and never cropped, the company name as its alt text. Without a logo, the tile holds the company's initials on `surface-dim`, in the display family at 600 in `text-muted`; for a person with no company it stays empty.
- **table:** `table-rule-strong` on top and above the total row; `table-header` in mono uppercase; numerals right-aligned and tabular; hairline row rules. Inline 0–100 score bars use an `outline` track with a `primary` fill and the value beside them — semantic colour stays on the rating chip, never the bar.
- **heatmap:** a table whose score cells are filled by benchmark band — the one place the row itself carries colour, because the grid *is* the reading. The four `heatmap-band-*` fills are mixed from the measurement colours over `surface` at one matched strength — `success`, `warning` and `error` at 22%, with Excellent and Good taking two steps of the same green (22% and 9%) because the `*-container` tokens would put both on one fill and collapse the two bands that hold most of the data. Re-derive all four whenever a measurement colour changes; they are deliberately brand-stable, since what a score *means* does not change with the partner. The numeral stays `heatmap-cell` at every band, so the value is legible without the fill and the page still reads in grayscale — but only the newest column carries weight, at 600 in `text-heading`; earlier columns drop to 400 in `text-body`. A grid of uniformly bold figures reads as noise, and the reader's question is where the building stands *now*, with the history as context. `text-body` rather than `text-muted` is the floor here, because `text-muted` falls under 4.5:1 against the lighter band fills. Cells are separated by `surface` hairlines rather than `outline`, so each column reads as one continuous field. A band key above the table names all four bands in words; count and identifier columns flanking the grid stay uncoloured and keep normal `outline` rules. Every heatmap states its benchmark and bands each cell on its printed value, so the numeral and its fill always agree. A month to date closes the month columns, "to date" set beneath its month label; it is the newest column, so it carries the weight, and its cells band like the rest because a score is a rate over the days that exist.
- **chart:** first series `primary`, comparison `chart-benchmark`; values labelled directly on points/bars; axis labels in `mono` and `text-muted`; gridlines in `outline`. A chart whose figures rest on a model carries that method under it, as a `body-sm` note in `text-muted`. A month to date, where the report carries one, closes every monthly chart and is marked three ways: a `surface-tint` column behind it from the plot top to the baseline, "to date" set under its axis label in the smaller axis style, and on a line chart the last segment dashed onto an open point, `surface` inside a `primary` ring. Its bars keep their series fill, since the column and the label already say they count fewer days; its score is a rate and is plotted as it stands.
- **rating card:** a sustainability rating, one card per measure, three at most in a row, on the same `card` with an `outline` hairline as the analytics overview stats. The measure name in `metric-label`, the score in `metric-value` with its out-of figure in `label` and `text-muted`, the inline score bar beneath it running 0 to the rating's maximum, then a delta chip and the expiry month in `body-sm` and `text-muted`. An expired rating swaps the expiry month for a `rating-neutral` Expired chip beside the delta chip; the bar stays `primary` either way, as every score bar does.
- **rating history:** a line chart per rating measure under its own `card-title`, built as the monthly line charts are: `primary` line and points, values on the points, axis labels in `mono` and `text-muted`, no legend. Ratings are sparse and irregular, so each chart sets its own time axis, labelled every six months or every January past four years, and its own y range, half a star beyond its highest and lowest ratings, marked by a dashed top line and the baseline, each labelled.
- **link:** `primary` with no underline. A link that stands on its own — a section link, a row name in a table or heatmap, a unit name in the run hours chart — closes with a `›` chevron; one set inside a line of text, a chart source or a win's ticket, does not. Every link opens in a new tab, so the report stays open behind it.
- **notes band:** a `surface-dim` section for methodology and footnotes, numbered, in `body-sm`.
- **scorecard strip:** the analytics overview's stat cards set directly under the masthead with no section header, used where page one has to carry more than the overview. The cards keep their `card` hairline and `metric-label` over the figure, set a step under `metric` at 1.75rem so the strip stays shallow; in print only their padding tightens.
- **leaderboard board:** a ranking drawn as a small ranked table in the report's own parts, so the leaderboards read as the rest of the report does. Three tiers, each a step quieter: the leader lands first, the challenger second, the field last.
  - **Leaderboard header:** the section header every section uses: the leaderboard month as the eyebrow, the title as the statement ("Site leaderboard"), and the date line saying what each board ranks and that moves are against last month.
  - **Board head:** the ranking's name as a `card-title` and its months ("Sep", "Jul - Sep") in `label` and `text-muted`, over the `table-rule-strong`.
  - **Leader:** on a site board, the building's photo first, cropped to a 2:1 band, 5:2 in print on page one, with an `outline` hairline, framed as the key wins' photos are and embedded at about twice its printed width; with no photo the same band on `surface-dim` holds a building mark in `outline-strong`. Then the leader's row set large: the trophy in `secondary` and the movement under it in the rank column, as the tables carry them; on a team board the company logo in its 40px tile in its own colours; the name in the display family with a chevron; then the muted meta line, clamped to two lines, beside the figure in `metric`, its unit after it in the scorecard's unit style ("99.6 %", "105 actions"), so a score never reads as a count.
  - **Biggest climber:** the second row, between hairlines: the trend-up icon in the rank column, "Biggest climber" in `label` and `text-muted`, the name in the display family at 600, and the climb as "↑2 to 5th" in `on-success-container` at 600. One name only; with no climber the row reads "None" in `label` and `text-muted`, so the board keeps its shape. In a portfolio of three sites or fewer, where a climb is mostly two sites swapping places, no board carries the tier.
  - **Chasing pack:** the table body a step smaller: rank in `text-muted`, name, movement and value in `text-body`, hairline rules between rows, and no chevrons, so the pack reads as context.
  - Every tier shares one rank column, and on a team board one logo column, so the leader's name, its meta line, the climber and every pack name start on one line. Movement on a board is a glyph and a number: "↑3" in `on-success-container`, "↓2" in `text-muted`, "New" in `text-muted`, nothing when it holds its place. A place lost reads quietly; only a climb takes colour.
  - Names clamp to two lines. Each board is a subgrid row of the section, so every tier sits level across the boards whichever names wrap. Up to three boards sit side by side; fewer boards take the width they leave. Each name links to the section that explains its figure, or to the PEAK report its ranking gives it.
  - **Team logos:** on a team board the leader's company logo sits in its tile in its own colours; the climber's and the pack's sit unframed at 30 by 18px in a soft neutral grey, so the colour on the board sits with the leader. The grey darkens a pale mark and lifts an off-white ground to white, so a light logo still reads and no logo takes a tint. A company without a logo gets its initials on `surface-dim`. This is the one place a company logo is filtered.
- **ranked heatmap:** the `heatmap` with a leading rank column, one row per site, ranked best first. The trophy replaces rank 1; no medals, no shared places. The site name carries its region in brackets in `text-muted`, and clamps to three lines. The comfort table's Target column sits after the counts, uncoloured like them, its unit under the heading. A portfolio row closes it, under the `secondary` 2px rule, banded like any other row.
- **shoutout button:** the report's one button, thanking a leader: a `primary` pill 36px high, a clap emoji and the label in `surface` at 600, set beside the team leaderboard's title above the board of the leader it thanks. On a narrow screen it drops under the date line.
- **open actions list:** a ranked list of open work under the board head the leaderboards use, hairline rules between rows. Each row: the rank in `text-muted`; for a person, the company logo unframed and grey; the name as a link with its context in `text-muted`; a full-width bar under the name on the list's own scale, split by age open, oldest first, 2px between segments; and the count in `text-heading` at 600. The age steps run light to dark, under 30 days and 30 to 60 days in `text-muted` mixed to 55% and 90%, 60 days or more in `on-error-container`, so stale work is the only colour; a legend under the date line names them. No trophy and no movement.
- **rating table:** a sustainability rating per site per measure, set on the inline score bar running from its rating type's minimum score to its maximum, so ratings on different scales still read as a share of the way up. Beside the bar, the value, then a fixed-width suffix holding `*` for an expired rating and an arrow against the previous rating, none on an expired one, so the values align whatever the suffix holds. Up is `on-success-container`, down `on-error-container`, and a legend above the table names all three marks in words.
- **portfolio leaderboard pages:** page one holds the masthead, the scorecard strip and the whole site leaderboard, and page two the team leaderboard alone. In print, block spacing tightens and type sizes never change: only page one's leaderboard tightens its top padding, photo band and row height, and page two opens 48px down like every other page. A leaderboard never splits across pages, and the section after each starts a new page. A by-site table section moves to the next page whole rather than split; one of 16 rows or more starts its own page and breaks between rows, its header repeating. In print the by-site rows tighten to 44px and the open P1-2 rows to 40px, so sixteen sites or twenty names fit a page. The side-by-side boards stack only on narrow screens, never in print. In print the sheet takes the printable width, so a browser that adds its own margins, or prints on Letter, neither pushes the boards off the page nor drops them into one column.

## Do's and Don'ts

**Do**
- Lead with a number and a plain caption: "18% — annual portfolio energy reduction".
- Write sentence case, and state findings as measured facts, not marketing claims.
- Label values directly on charts — a printed page has no tooltips.
- Keep every page legible in grayscale: chips and deltas carry words and glyphs, never colour alone.
- Check print preview before issuing: clean page breaks, colours exported, table headers repeating.

**Don't**
- No emoji, anywhere. No gradients, no decorative colour, no cards with a coloured left border.
- Don't use green or red as decoration, and don't tint a whole card or row by status. The `heatmap` is the one sanctioned exception: its cells are tinted by measured band, not by status, and the fill *is* the chart. The impact dot is not a third case — it is a category marker, so it never spreads to the label, the heading or the card.
- Don't add a second dark field — the masthead is the only one.
- Don't let hover, tooltips or motion carry information; the deliverable is a PDF.
- Don't recolour, re-space or rebuild the logo; use the reversed (white) version on the masthead.
