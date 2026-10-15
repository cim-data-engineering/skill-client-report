# Run-hours signals

Which point stands for a unit running. The recipe reads every point on the site's in-scope equipment and sorts it by name with the rules below, at run time — so this is a guide, not a list to keep complete. A point PEAK added last week is read the same way as one added years ago, and nothing here names a metadata id.

`references/run-hours/scripts/runhours_plan.py` parses these tables on every run: edit a table and the next run follows it, with no second copy in code. `references/run-hours/run-hours.md` does not need this file at run time — open it to change a rule.

## Equipment types

In-scope types, in the order the view draws them and the first pass fetches them: central plant before field units, then by system, then top to bottom.

| Page | System | Code | Equipment type | Name word | Compressor is the unit | Heating is the unit | Also never |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Central plant | Cooling | CH | Chiller | CH | yes | | |
| Central plant | Cooling | CT | Cooling Tower | CT | | | |
| Central plant | Cooling | CWP | Condenser Water Pumps | CWP | | | |
| Central plant | Cooling | PCHWP | Primary Chilled Water Pumps | PCHWP | | | |
| Central plant | Cooling | SCHW | Secondary Chilled Water System | SCHWP | | | |
| Central plant | Cooling | SCHWP | Secondary Chilled Water Pumps | | | | |
| Central plant | Cooling | TCW | Tenant Condenser Water | TCWP | | | |
| Central plant | Cooling | DAC | Dry Air Cooler | DAC | | | |
| Central plant | Cooling | DACP | Dry Air Cooler Pump | DACP | | | |
| Central plant | Cooling | UFCS | Under-Floor Cooling System | | | | |
| Central plant | Heating | HWB | Boiler | BLR, HWB | | yes | |
| Central plant | Heating | SB | Steam Boiler | SB | | yes | |
| Central plant | Heating | CHaP | Combined Heating & Power | CHP | | yes | |
| Central plant | Heating | HE | Heat Exchanger | HE, HX | | | |
| Central plant | Heating | PHWP | Primary Hot Water Pumps | PHWP, PHHWP | | | |
| Central plant | Heating | SHW | Secondary Hot Water System | SHWP, SHHWP | | | |
| Central plant | Heating | UFHWS | Under-Floor Heating System | | | | |
| Central plant | Hot water | CAL | Calorifier | CAL | | yes | |
| Central plant | Hot water | DHWT | Domestic Hot Water | DHWP | | yes | |
| Central plant | Hot water | SWH | Solar Water Heater | SWH | | yes | |
| Central plant | Air | AHU | Air Handling Units | AHU | | | Heat Pump, Heat Recovery |
| Central plant | Air | HRU | Heat Recovery Unit | HRU | | | |
| Central plant | Air | AIR HX | Air to Air Heat Exchanger | | | | |
| Central plant | Air | ECO-HR | Econet Heat Recovery Unit | | | | |
| Central plant | Air | SAF | Supply Air Fan | SAF | | | |
| Central plant | Air | TL | Thermal Labyrinth | TL | | | |
| Central plant | Air | EC | Evaporative Cooler | EC | | | |
| Central plant | Air | CPV | Car Park Ventilation | CPV | | | |
| Central plant | Water | DCW | Domestic Cold Water | DCWP | | | |
| Central plant | Water | CWB | Cold Water Booster Pumps | CWBP | | | |
| Central plant | Water | HYD | Hydraulic Pump | HYD | | | |
| Central plant | Water | MISC-Pump | Miscellaneous Pump | | | | |
| Field units | Packaged | PAC | Packaged Air Conditioning Units | PAC, RTU | | | Heat Recovery |
| Field units | Packaged | HP | Heat Pump | HP | yes | | |
| Field units | Packaged | VRV | Variable Refrigerant Volume Systems | VRV, VRF | yes | | |
| Field units | Packaged | MSS | Multi Split Systems | | | | |
| Field units | Packaged | SS | Split Systems | | | | |
| Field units | Packaged | CRAC | Computer Room Air Conditioning Unit | CRAC | | | |
| Field units | Packaged | ACC | Air Cooled Condensers | ACC | | | |
| Field units | Terminal | FCU | Fan Coil Units | FCU | | | Heat Pump, Heat Recovery |
| Field units | Terminal | UH | Unit Heater | UH | | | |
| Field units | Terminal | ACRTN | Air Curtain | | | | |
| Field units | Extract | KF | Kitchen Fans | KEF, KSAF | | | |
| Field units | Extract | EAF | Exhaust Air Fans | EAF, EF | | | |

- **Page** follows what the type serves: the whole building or a large area is central plant, one space or tenancy is a field unit. A type that could go either way — a heat pump feeding a plant loop — is placed by what it usually serves; move its row if a portfolio differs.
- **Name word** is a word in an equipment name that means this type, anywhere in the name and glued to its number or not — `B2 FCU 210-1`, `KEF11-1`, `Common - SHWP - 2`. It is read only to group a unit with the type its name says, and only between the types **Regrouped by name** allows.
- **Compressor is the unit** is `yes` where the compressor running is the unit running, so a compressor status counts as a status. Elsewhere it is a last resort: a PAC's compressor cycles while its fan runs on.
- **Heating is the unit** is `yes` where heating is what the unit is for, so the heating words that **Never a run signal** sets aside on a fan — a burner, an immersion heater, a heating status — are this unit's own: a boiler with only `Burner Status` is drawn from it.
- **Also never** adds words that disqualify a point on this type only, on top of **Never a run signal** — an AHU's heat-pump or heat-recovery status is not its fan.

A type in neither this table nor **Never charted** is unclassified: its units are left off the chart and counted in the notes, so a new PEAK type shows up as a gap to fill here rather than as plant quietly missing. Between them the two tables list every type in PEAK's catalogue; add a row when PEAK adds one.

## Regrouped by name

A unit whose name says one type while PEAK says another is drawn under its name's type only where that pair is here — the mix-ups that recur across portfolios. A name that also names PEAK's own type keeps it. Every other disagreement is left as PEAK has it: the first word of a name is as often a building or plantroom code (`CH AHU-12`, `EC Boiler-01` for an energy centre) or a heating circuit (`CT Heating Pump 2`, constant temperature) as a type, and a pump named for what it serves (`AHU-CHWP-10`) is still a pump.

| Code | Takes units PEAK types as | Seen as |
| --- | --- | --- |
| FCU | AHU, PAC | `FCU-1-01`, `B2 FCU 210-1` typed AHU; `FCU-3-02` typed PAC |
| AHU | PAC, FCU | `AHU-01` typed PAC |
| PAC | AHU, FCU | `PAC-1` typed AHU |
| CRAC | AHU, PAC, FCU | `CRAC-1` typed PAC |
| VRV | PAC, FCU, AHU | `VRF-L3-01` typed PAC |
| KF | EAF | `KEF-1` typed EAF |
| SCHW | PCHWP, SCHWP | `SCHWP-2` typed PCHWP |
| PCHWP | SCHW, SCHWP | `PCHWP-1` typed SCHW |
| SHW | PHWP | `SHWP-1` typed PHWP |
| PHWP | SHW | `PHWP-1` typed SHW |
| TCW | CWP | `TCWP-1` typed CWP |
| CWP | TCW | `CWP-1` typed TCW |

## Never charted

| Codes | Why |
| --- | --- |
| VAV, UFAD, ACB | Box- and floor-level terminals and chilled beams are not a run-hours signal, and a site has hundreds: none has a fan or compressor of its own, so the AHU serving them is charted instead |
| LT, ELVTR, ELVTR-GRP, VT | Lighting and lifts — only when the user asks |
| PSM, SYS-PM, GM, SYS-GM, WM, SYS-WM, TEM, SM, CAM | Meters — only when the user asks |
| VSD | A drive is read through the equipment it drives, where its speed is a signal like any other |
| BLD, ZN, People, SYS-BACER, SYS-WEAT, UNASSIGN, DMS, CIM, BAC-STATUS | Building and platform records, not plant |
| GEN, GT, UPS, COMP, PS, FIP, GsD, BFX, CPL, Door, FT, INCP, LN, PRA, RWT, STM-TRAP, THST, TUN, WT, FCBD, Ref, CFT, SWBD | Not HVAC or hot-water plant |
| BT, CEN, NV, PCB | No moving part to run |

## Roles

Each point takes at most one role, from how its name ends. The recipe compares a unit's status with its analog and keeps whichever shows less running, and a compressor status only where neither exists. A command is never drawn — it says what the unit was told to do, not that it ran — but a unit with only commands is named as such in the notes.

| Role | Name ends with, best first | What it is |
| --- | --- | --- |
| status | Status, Running | The unit reporting that it runs |
| analog | Speed Feedback, Speed, Frequency, Hz, RPM, Speed Command, Current, Amps, Amperage, Power, Velocity, Fan Output, Load, Output | A measure of the moving part, zero when it stops |
| command | Command, Enable, Occupancy | What the unit was told to do; never draws a row |

- The longest ending that matches decides — `Speed Command` ranks after `RPM`, not with `Speed`. Brackets and a trailing unit are ignored: `Speed (Hz)` is `Speed`, `Load %` is `Load`.
- A name marked `(MSV)` is a state, not a measure, so an `(MSV)` speed stands in as the unit's status (off, low, high). A speed state held at one running state all week shows the speed the unit is set to, not when it ran, and its row is hatched: a fan coil's `Fan Speed (MSV)` can sit at 3 all week while its enable switches with the day. A plain point beats its `(MSV)` twin.
- The state numbering is read from the week: a speed state that reports 0 counts from 0, so 0 is off and 1 is the lowest speed; one that never reports 0 counts from 1, the BACnet convention, so 1 is off.
- **Load** and **Output** count only when the name names no component — `Chiller Load`, `Hot Water Boiler Load`. A coil's or a system's load can read zero while the fan runs, and the least-run-time comparison would then pick it.
- A status that names a compressor becomes the **compressor** role unless the type says **Compressor is the unit**; on those other types an analog or command naming a compressor is skipped.

## Never a run signal

A point whose name contains any of these, as whole words and in any case, is skipped whatever it ends with — except on a type the **Except where** column names, where that row does not apply. **Marks plant** rows tell the notes apart: a unit left undrawn that still reports one of them is plant whose running is not integrated, where one with only sensors and setpoints is usually a shared or zone record.

| Name contains | Why | Except where | Marks plant |
| --- | --- | --- | --- |
| Filter, Alarm, Fault, Trip, Lockout, Overload, Safety, Shutdown, Leak, Detector, Maintenance | Protection and health, not running | | yes |
| Setpoint, Set Point, Set-point, Minimum, Maximum, Limit, Reset, Potential, Full Load, Highest, Lowest | Targets, limits and ratings | | |
| Damper, Valve, Coil, Wheel, Humidifier, Duct Heater, Fan Heater, Crankcase Heater, Basin Heater, Preheat, Reheat, Baseboard, Steam Supply, Desiccant, Regeneration | A different component from the one that runs | | |
| Burner, Immersion Heater, Electric Heater, Gas Heater, Heater Status, Heater Enable, Heater Output, Heater Stage | A heater beside the unit, cycling on its own | Heating is the unit | |
| Mode, Call, Demand, Stage, Lead, Lag, Schedule Status, After Hours, Optimum, Setback, Economy, Purge, Shed, Available, Thermo, Terminal, Startup, Anti | What the controls want or allow, not what ran | | |
| High Speed, Low Speed, Medium Speed, High Fan, Low Fan, Medium Fan | One stage of a multi-speed fan, which misses the others | | |
| Building, Plant, System Flow, Cooling Load, Heating Load, Secondary Chilled Water Load | Plant-wide, not this unit | | |
| Heat Status, Heat Enable, Heating Enable, Heat Output | Heating stages, which cycle while the fan runs | Heating is the unit | |
| Cool Status, Cool Enable, Cooling Enable, Thermal Power | Cooling stages, which cycle while the fan runs | | |
| Temperature, Pressure, Humidity, Dew, Enthalpy, CO2, Level, Energy, Consumption, Cost, Efficiency | Conditions and totals | | |
| Count, Number Of, Starts, Hours, Duration, Timer, Delay | Tallies | | |
| Manual, Local, Override, Hand/Auto, Switch, Contact, Position, Select, Isolation, Bypass, Confirmation | Hand controls and positions | | |
| Frost, Fire, Smoke, Defrost, Door, Wind, Outside Air Velocity, Condenser Speed, Compressor Enable, Direction, Dehumidification, Dehumidifier, Humidistat, Equipment Status, Air Flow Rate, Input Status, Measurement, Data Status, Wet/Dry, Snow, UV, Light, Communication, Communications, Comms, Stagnation | End like a run signal without being one | | |

## Which point wins

When a unit has several points in one role, the one naming its main moving part wins. The most specific (longest) phrase in the name decides — `Return Air Fan Status` is return air, not fan — and when two phrases are equally long the name takes the less preferred rank, so `Pump Flow Status` ranks as flow.

| Rank | Component named | Examples |
| --- | --- | --- |
| 1 | Supply Air Fan, Supply Fan, Indoor Fan | Unit Supply Air Fan Status, PAC Supply Air Fan Speed |
| 2 | (none — the unit itself) | Chiller Status, Unit ON/OFF Status, Hot Water Boiler Load |
| 3 | Fan, Pump, Compressor | Cooling Tower Fan Status, Primary Chilled Water Pump Speed |
| 4 | Flow, Supply Air Flow | Primary Chilled Water Pump Flow Status |
| 5 | Return Air, VSD | Unit Return Air Fan Status, VSD Speed % |
| 6 | Exhaust Air, Exhaust Fan, Extract | Unit Exhaust Air Fan Status |
| 7 | Outside Air, Relief | Unit Outside Air Fan Status |
| 8 | Condenser Fan, Condenser Water Fan, Condenser Status, Condenser Pump | PAC Condenser Fan Status |

Two endings rank last whatever they name: **Occupancy**, a schedule rather than an instruction to this unit, comes after any enable or command; **Load** and **Output**, indirect measures, come after any speed, current or power. A point that only an **Except where** lets through ranks last in its role too: a boiler's `Burner Status` draws the row only where no boiler status is mapped beside it. Within a rank: the ending's place in **Roles**, then the plain point before its `(MSV)` twin, then the shorter name.

## Runs around the clock

A unit drawn on all week, with no second signal that changes to check it against, is named in the notes as possibly a stuck switch — unless it serves a space conditioned day and night for what is in it, where running all week is its job. Those are listed on a line of their own. Words match whole, in any case, in the unit's name or its zone's.

| Codes | Name or zone contains | Why |
| --- | --- | --- |
| CRAC | | A computer room unit cools IT equipment, which never stops |
| | Comms, Communication, Communications, Server, Data Room, Data Hall, Data Centre, Data Center, MDF | A unit named for a comms or server room, or zoned in one, conditions it continuously |

`Comms` matches only as a whole word, never inside `Common`. `MER` is left out: it is as often a mechanical equipment room, a plantroom, as a telecoms one.

## What the rules pick

Illustrative, from the live catalogue — this table is not parsed.

| Equipment | Status | Analog | Command (named in the notes, never drawn) |
| --- | --- | --- | --- |
| Chiller | Chiller Status | Chiller Speed, else Chiller Current, else Chiller Load | Chiller Enable |
| AHU | Unit Supply Air Fan Status | Unit Supply Air Fan Speed Feedback, else Speed | Unit Supply Air Fan Command, else Enable |
| PAC | PAC Supply Air Fan Status | PAC Supply Air Fan Speed Feedback, else Speed | PAC Supply Air Fan Enable |
| FCU | FCU Supply Air Fan Status | FCU Supply Air Fan Speed | FCU Supply Air Fan Enable |
| Pump | Primary Chilled Water Pump Status | Primary Chilled Water Pump Speed Feedback, else Speed | Primary Chilled Water Pump Enable |
| Boiler | Hot Water Boiler Status | Hot Water Boiler Load | Hot Water Boiler Enable |
