# Equipment run hours

Owns the equipment run hours section and its notes-band item. No operational impact row. Scaffold part: `equipment-run-hours`. Scripts: `scripts/run_hours.py`, which drives the three `runhours_*.py` scripts beside it, copied unchanged from skill-health-check.

When each unit of plant ran across one week, against the site's working hours: Monday to Sunday edge to edge, one row per unit, bars exact to 15 minutes. Out-of-hours running and plant that never ran show without reading any text, which is what the reader comes to this section for.

## What you write

One prose slot, `run_hours` in `prose.json`: the note under the chart. Two to four sentences, from the facts `report.py bundle` prints:

- Lead with the plant that ran most outside working hours, named, and whether that is its job (a domestic hot water pump or a comms-room unit on all week is expected; an air handler is not)
- Then anything on all week with nothing to check it against, which may be a stuck status rather than the unit running, and central plant that did not run at all
- Say what it means for the building, not how the chart is drawn. The legend and the notes item carry the encoding

Report in chat, not on the page: units left off the chart and why (only an enable or schedule, no points in PEAK, plant alarms but no run point), equipment types the signals reference does not cover yet, and any units beyond the first pass of 100. The build notes in `facts.md` list them.

## Scope

- **The week**: the last full Monday-to-Sunday week inside the quarter, in site local time, so the section closes on the same month as every other window in the report. The window step converts local midnights to UTC, daylight saving included
- **Working hours** come from the site in PEAK, each day its own; a closed day has no working-hours column and all its running is outside hours. All days closed or all `00:00` stops the plan step: ask the user what hours to assess against, never guess, and run `report.py plan` again with `--hours "Mon-Fri 08:00-18:00, Sat 09:00-13:00"`
- **Equipment**: every type in `run-hours-signals.md`, central plant first, then field units. VAVs, chilled beams, lighting, lifts and meters stay out
- **Sensors only**: a row is drawn only from a sensor that reports the unit running, a run status, a speed, current or power reading, or a compressor status. An enable, command or occupancy schedule says what the unit was told to do, not that it ran
- **First pass**: up to 100 units, central plant always whole. The report draws the first pass only; the rest is named in chat

## Which point draws the row

Each unit brings up to two sensors, its status and an analog (speed, frequency, current, power), picked by `run-hours-signals.md`, which `runhours_plan.py` parses on every run.

| The unit has | The row is drawn from |
| --- | --- |
| Status and analog, both changing | Whichever shows less running. The usual faults (a status stuck on, an enable mapped as status, a speed idling above zero) all add hours, so the smaller count is the genuine one, unless one switched on at most once all week beside one that switched on three or more times |
| Status and analog, one held all week | The one that changes |
| Status and analog, both held | Status when they agree; hatched when they don't |
| Status only | Status. On all week is kept and noted as unverified |
| Analog or speed state only | The analog. Held at one running value all week is hatched |
| Only a compressor status | The compressor, noted: it cannot show whether the fan ran |
| Only an enable, command or schedule, or no history | Not drawn; noted |

A reading holds for up to an hour, or one and a half times the point's own interval. A longer silence is hatched, never drawn as off. Collector restarts that write 0 to every point at once are left out.

## Display

- One chart per page of plant, **Central plant** then **Field units**, each a static SVG the script draws in the report's tokens. A page with no rows is left out
- Groups by equipment type, in the order of the signals reference's types table; rows by level, then name in natural order
- A grey working-hours column on each day, headed with the day and its hours; "closed" where it has none
- Bars in muted grey during working hours, `warning` outside them, hatched where there is no reliable data. Legend above the chart, as on the other charts
- Each unit name links to its PEAK chart for the same week with working hours on, built by the build step: no tool returns that page
- Level and zone sit right-aligned before the week where they fit; the full name, the point drawn and the location are in the hover

## Notes band item

- **Run hours.** How a row is drawn and what the hatching means. The script writes it

## Data

`report.py plan` runs `runhours_plan.py window` and adds its calls to the main batch: a `platform.equipment` discovery pull with every in-scope unit's points nested, and two `limit:1` census counts. `report.py next` runs `runhours_plan.py plan` over the saved discovery pages and prints the `platform.history` calls. History responses are large and come back as files, so they are copied, never written out. `report.py bundle` runs `runhours_build.py` and draws the result.
