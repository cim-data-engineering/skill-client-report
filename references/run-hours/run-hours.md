# Equipment run hours

Owns the equipment run hours section and its notes-band item. No operational impact row. Scaffold part: `equipment-run-hours`. Scripts: `references/run-hours/scripts/run_hours.py`, which fixes the week and draws the chart, and the three `runhours_*.py` scripts beside it, which pull and classify the points. Those three are the health check skill's, copied unchanged, so a change to them belongs in that skill first.

When each unit of plant ran across one week, against the site's working hours: Monday to Sunday edge to edge, one row per unit, bars exact to 15 minutes. Out-of-hours running and plant that never ran show without reading any text, which is what the reader comes to this section for.

## Equipment run hours

When the plant ran
Date: the week, as `run_hours.py draw` prints it

**Scope:**

- **The week**: the last full Monday-to-Sunday week inside the quarter, in site local time, so the section closes on the same month as every other window in the report. The window step converts local midnights to UTC, daylight saving included
- **Working hours** come from the site in PEAK, each day its own; a closed day has no working-hours column and all its running is outside hours. All days closed or all `00:00` stops the window step: ask the user what hours to assess against, never guess, and run it again with `--hours "Mon-Fri 08:00-18:00, Sat 09:00-13:00"`
- **Equipment**: every type in `run-hours-signals.md`, central plant first, then field units. VAVs, chilled beams, lighting, lifts and meters stay out
- **Sensors only**: a row is drawn only from a sensor that reports the unit running: a run status, a speed, current or power reading, or a compressor status. An enable, command or occupancy schedule says what the unit was told to do, not that it ran
- **First pass**: up to 100 units, central plant always whole. The report draws the first pass; a note under the chart counts any units beyond it by type, and chat names them

**Which point draws the row:**

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

**Display:**

- One chart per page of plant, **Central plant** then **Field units**, each a static SVG drawn in the report's tokens. A page with no rows is left out
- Groups by equipment type, in the order of the signals reference's types table; rows by level, then name in natural order
- A grey working-hours column on each day, headed with the day and its hours; "closed" where it has none
- Bars in muted grey during working hours, `warning` outside them, hatched where there is no reliable data. Legend above the chart, as on the other charts
- Each unit name links to its PEAK chart for the same week with working hours on. No tool returns that page, so the build step writes the link
- Level and zone sit right-aligned before the week where they fit; the full name, the point drawn and the location are in the hover

**Under the chart:**

- No note: the chart is the reading, and the legend and the notes item carry the encoding
- The one exception is field units left out to keep the chart to its first pass. Then the draw step writes a single note under the chart saying how many and of which types, and `fill_report.py` places it

Say in chat, not on the page: the units left off the chart and why (only an enable or schedule, no points in PEAK, alarms but no run point, no history that week), equipment types the signals reference does not cover, and the names of any units beyond the first pass.

## Notes band item

- **Run hours.** How a row is drawn and what the hatching means. The scaffold carries it as written

## Data recipes

The pull is `platform.equipment` for the units and their points, then `platform.history` for the week. Work in one folder, `runhours/` below, beside the bundle.

1. **Window**: save the `search_sites` response, made with `include_working_hours:true`, as `site.json`, then run `python3 references/run-hours/scripts/run_hours.py window site.json runhours --site-id <the site's id> --quarter-end <the quarter's last day>`, which takes the report's site out of a search that matched several. It prints a discovery pull, every in-scope unit with its points nested, and two `limit:1` census counts. They go in the main batch; save each response in `runhours/` under the name printed, and page the discovery pull as the printout says when it has more
2. **Plan**: `python3 references/run-hours/scripts/runhours_plan.py plan runhours runhours/discovery-0.json --census runhours/census-all.json runhours/census-known.json`, adding any further discovery pages after the first. It sorts the points by `run-hours-signals.md` and prints the history calls. Make them in parallel and save each as it names them. Where it says there is nothing to draw, the section is out: say why in chat
3. **Draw**: `python3 references/run-hours/scripts/run_hours.py draw runhours` builds the week, writes `runhours/chart.json` with the chart, its date line and any note under it, and prints what to say in chat, every unit left off named with its reason
4. **Bundle**: `"run_hours": {"chart": "runhours/chart.json"}`, the path relative to the bundle. `fill_report.py` lays in the chart, its date line and the note where there is one

The discovery and history responses usually come back as files: copy each under its name rather than writing it out.
