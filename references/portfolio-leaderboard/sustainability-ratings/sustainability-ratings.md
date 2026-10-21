# Sustainability ratings

Owns the sustainability ratings by site table, the last content section before the notes. Scaffold part: `sustainability-ratings`. Script: `scripts/sustainability_ratings.py`, which builds every row, cell, link and note below.

Every portfolio report fetches the sites' ratings, and the section renders only when at least one site holds a current rating.

## What you write

Nothing, on the page or in chat. Neither the section's presence nor its absence is mentioned at hand-over.

## Naming

The section, its headings, its notes and every fixed line say "sustainability ratings" and never name a rating scheme. PEAK can hold any scheme a client tracks, so the page names what is measured, not who rates it.

## Scope

- **Every rating type** PEAK records for the sites, grouped by the measure each type rates: PEAK's `sustainability_rating_measures`, such as energy, water and waste. PEAK has no indoor environment measure, so a type that rates Other or names no measure sits under Indoor environment when its name says indoor, and under Other otherwise
- **One type per cell**: per site and measure, the latest rating by rating period end decides the rating type shown, and its history keeps to that type. Two types are never mixed in one cell or one comparison
- **Current**: a rating is current when it has not expired by the issue date
- **Renders when**: at least one site holds a current rating for some measure

## Section header

Eyebrow: Sustainability ratings  
Statement: Sustainability ratings by site  
Date line: "As at {issue date}. Each site's latest rating for each measure."

Above the table, a legend: ↑ "Up from the rating before" in green, ↓ "Down from the rating before" in red, * "Expired".

## Rating table

**Rows:** one per site holding a rating for any measure shown, largest building first, then a portfolio row.

**Columns:**

| Column | Content |
| --- | --- |
| Site | The site name with its state abbreviation in muted brackets, linked to that site's ratings dashboard |
| Size | Building size, in the portfolio's unit, named in the header |
| One per measure | Each measure that holds a current rating at any site, headed with the measure's name. Energy, indoor environment and water lead in that order; any other measure follows alphabetically |

**Rating cell:**

- The inline score bar, running from the rating type's minimum score to its maximum, so ratings on different scales still read as a share of the way up
- The value at the precision its type uses: 1dp for a type rated in fractions, such as half stars on a scale of ten points or fewer; whole numbers otherwise
- A fixed-width suffix: `*` when the rating has expired, then an arrow against the site's previous rating of the same type, ↑ up or ↓ down, nothing when it held or there is no previous rating
- A dash when the site has no rating for the measure

**Portfolio row:** per measure, the building-size-weighted mean of the current ratings, on the same bar and at the same precision.

- It shows only when every current rating in the column shares one rating type. Ratings on different scales cannot be averaged, so otherwise the cell is a dash
- Expired ratings count in no portfolio cell, and a site with no building size counts in no weighting
- Its arrow compares the same sites' previous ratings of the same type, weighted the same way, over the sites that have both

**Display:**

- Up is `on-success-container`, down `on-error-container`, per the rating table component in DESIGN.md
- Under the table, the source line: "Source: sustainability ratings recorded in PEAK. The portfolio row is weighted by building size."

**Links:**

- Each site name links to its ratings dashboard: `https://ace.cimenviro.com/dashboard/ratings?site_ids={{site_id}}&ratings_type_id_or_filter=all_ratings`
- The section link, "See sustainability ratings ›", opens the same dashboard with every site: one `site_ids={{site_id}}` per site. Bundle slot `ratings`
- The section carries the anchor `sustainability-ratings`

## Notes band items

- **Sustainability ratings.** The portfolio row counts current ratings only, and its arrow compares the same sites' previous ratings

## Data

One call in the main batch: `platform.sustainability_ratings` with every `site_ids` and `limit:200`, selecting `site_id`, `score`, `period_end_date`, `expiry_date`, `sustainability_rating_type_id` and, on `sustainability_rating_type`, `name`, `min_score`, `max_score` and `sustainability_rating_measures.name`. `report.py next` pages it from the first page's total.

- PEAK's rating period end is exclusive. Only the order of ratings depends on it here
- The current test, the latest rating per site and measure, the previous rating of the same type, the precision and the portfolio row are all worked out from those rows
