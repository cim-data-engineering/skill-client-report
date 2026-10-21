# Sustainability ratings

Owns the sustainability ratings section: a card per NABERS measure and each measure's rating history. No operational impact row and no notes band item. Scaffold part: `sustainability-ratings`. Script: `scripts/sustainability_ratings.py`, which builds every card, chart and link below.

Not one of the section choices. Every report fetches the site's ratings, and the section renders only when PEAK holds at least one current rating for it.

## What you write

Nothing, on the page or in chat. The section is never asked for, so neither its presence nor its absence is mentioned when the report is handed over.

## Scope

- **Measures**: NABERS energy, indoor environment and water, read off the rating type name in PEAK. Waste and every non-NABERS rating type are out of scope and never appear
- **Rating type**: a measure carries only the rating type of its latest rating. Energy can be rated as base building or whole building, and the two are not comparable, so the card and chart never mix them
- **Current**: a measure is current when its latest rating, by rating period end, has not expired by the issue date
- **When it renders**: only when at least one measure is current. Once it renders, every in-scope measure with a rating shows, current or expired, however long ago it lapsed
- **Order**: energy, indoor environment, water, in cards and charts alike

## Section header

How the building rates under NABERS  
Date: As at {issue date}. Each rating is plotted at the end of its rating period.

## Rating cards

One card per measure, three at most, side by side.

| Line | Reference |
| --- | --- |
| Name | Energy, Indoor environment or Water |
| Score | x.x / 6 stars, the latest rating, the out-of figure being the rating type's maximum score in PEAK |
| Bar | The score as a share of the maximum, on the inline score bar |
| Change | {Up\|Down} x.x from y.y, or No change from y.y, against the measure's previous rating |
| Expiry | Current: Expires {Mon YYYY}. Expired: an Expired chip beside the change chip, and no date |

**Display:**

- The change chip is the delta chip, by whether the change is good: positive when the rating rose, muted when it held or fell. No red, the same rule as operational impact: a fall is stated in the glyph and the word, not colour coded
- The Expired chip is the neutral rating chip: grey, and always the word
- A measure with only one rating has no previous to compare, so its card carries no change chip
- No intensity, usage or area figures. The card answers where the building stands and which way it moved

## Rating history

One chart per measure shown, stacked in measure order, each under its own chart title.

**Display:**

- Plot every rating of the measure's type, each at the last day of its rating period, a dot on each with its value to 1dp beneath it, or above it where the baseline is too close
- Join the dots with straight lines. A gap between ratings is a stretch with no new rating, so the line carries across it. A measure with one rating is a single dot
- Each chart sets its own y range: the top is half a star above the highest rating, never above the maximum, as a dashed line labelled on the left; the bottom is half a star below the lowest, never below 0, as the baseline, also labelled. A 6.0 high and a 4.5 low runs 4.0 to 6.0, and a measure held at 6.0 runs along the dashed top line
- Each chart sets its own time axis, from the 1 January or 1 July at or before its first rating to the first one after its last, so a short history fills the width. Labels sit at each January and July, Jan 26 and Jul 26, or each January alone once the axis spans more than four years. No tick marks and no vertical gridlines
- No legend: the last dot is the latest rating, and the card above already says so

**Links:**

- Section link under the charts, labelled "See sustainability ratings". Bundle slot `ratings`:
  `https://ace.cimenviro.com/dashboard/ratings?site_ids={{site_id}}&ratings_type_id_or_filter=all_ratings`
- The source line above it, "Source: NABERS ratings recorded in PEAK", is fixed text and carries no link

## Data

One call in the main batch, whatever sections are chosen: `platform.sustainability_ratings` for the site with `limit:200`, selecting the score, rating period end, expiry date, and the rating type's name and maximum score. Every rating the site has recorded comes back in one page, so there is no follow-up. PEAK's rating period end is exclusive, so the period's last day is the day before it. The current test, the history, the axes and the y ranges are all worked out from those rows.
