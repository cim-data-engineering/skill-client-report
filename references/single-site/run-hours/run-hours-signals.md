# Run hours signals

For each equipment type, this file lists the PEAK metadata used to work out when a unit was running, and the rules that turn that metadata into the bars on the run hours chart. Equipment types not listed are not included in the run hours view.

## How run hours are worked out

1. **Fetch** the metadata the unit has from its equipment type's row in [Central plant](#central-plant) or [Field units](#field-units).
2. **Count** the 15-minute periods in the week in which each metadata shows running, as defined in [When a metadata shows running](#when-a-metadata-shows-running).
3. **Take the lowest.** The unit is drawn from the metadata with the fewest running periods, because every listed metadata shows running whenever the unit runs.
4. **Leave out stuck metadata.** A metadata that is off or zero all week is left out while another of the unit's metadata, other than a temperature, changes.
5. **Nothing changed.** If none of the unit's metadata changed all week, the unit is drawn off when all of it is off, drawn on and noted as unverified when all of it is on, and shown as no reliable data otherwise.

The chart link for each unit opens every metadata fetched for it, the one the unit is drawn from first.

## When a metadata shows running

| Metadata | Shows running when |
| --- | --- |
| Status: name ends in Status, Running or Flow Status | its value is 1 (on); for a status numbered from 1, whose values are 1 and 2, its value is 2 |
| Multi-state status: name ends in (MSV) | its value is above its off state, which is 0 if the value is 0 at any time in the week and 1 otherwise |
| Speed, frequency, current, power, load, firing rate or velocity | its value is above 5% of its highest value in the week |
| Leaving water temperature | its value is at or above the midpoint between its lowest and highest values in the week. Never used on its own, nor when those values differ by less than 5 °C (9 °F) |

A value applies until the next one, for up to one hour, or up to 1.5 times the metadata's usual reporting interval if it reports less often than every 15 minutes. A longer gap is shown as no data, not as off.

A metadata name with a unit in brackets, such as (MSV), (Hz), (RPM), (Fahrenheit) or %, is the same metadata as the name without it. Speeds, currents and powers are judged against their own highest value, so their units do not matter.

## Metadata to fetch

A metadata belongs in an equipment type's list only if it reads running at every time the equipment runs. Compressor metadata does not, because the compressor cycles while the unit runs. This covers compressor metadata on fan units, a chiller's Compressor Status, and one stage of a multi-compressor chiller (names starting Chiller Compressor). Neither does metadata for a second fan or pump that can stop while the unit runs, such as an air handling unit's return fan. Enables and commands are not listed: they record whether the unit was allowed to run, not whether it ran.

Only actual units are drawn. A record with Common in its name covers several units, and one with HLI in its name repeats a chiller, so neither is drawn. A unit with no leaving water temperature of its own still uses the one on its type's Common record, when the site has exactly one. A unit with FCU in its name is treated as a Fan Coil Unit, whatever its equipment type in PEAK.

To add a metadata, put its exact PEAK name in its equipment type's row, after checking in a PEAK chart that it reads running at every time the equipment runs.

## Central plant

| Equipment type | Short code | Metadata to fetch |
| --- | --- | --- |
| Air Handling Units | AHU | Unit Supply Air Fan Status · Unit Supply Air Fan Speed · Unit Power · Unit Supply Air Flow Status · Unit Supply Air Fan Frequency · Unit Supply Air Fan Speed Hz · Unit ON/OFF Status · Unit Supply Air Fan Speed RPM · Unit Supply Air Fan Current · Unit Supply Air Fan Power · Unit Supply Air Fan Speed Feedback · Unit Supply Air Velocity |
| Supply Air Fan | SAF | Supply Air Fan Status · Supply Air Fan Speed · Supply Air Fan Flow Status · Supply Air Fan Frequency · Supply Air Fan Current |
| Chiller | CH | Chiller Status · Chiller Load · Chiller Current · Chiller VSD Frequency · Chiller HLI Status · Chiller Speed · VSD Status |
| Cooling Tower | CT | Cooling Tower Fan Status · Cooling Tower Fan Speed · Cooling Tower Fan Speed Feedback · VSD Operating Frequency · VSD Speed |
| Primary Chilled Water Pumps | PCHWP | Primary Chilled Water Pump Status · Primary Chilled Water Pump Speed · Primary Chilled Water Pump Flow Status · Primary Chilled Water Pump Frequency · Primary Chilled Water Pump Current · Primary Chilled Water Pump Power · Primary Chilled Water Pump Speed Feedback · VSD Speed |
| Car Park Ventilation | CPV | Car Park Exhaust Air Fan Status · Car Park Supply Air Fan Status · Car Park Exhaust Air Fan Speed · Car Park Supply Air Fan Speed · Car Park Exhaust Air Fan Speed Feedback · Car Park Supply Air Fan Speed Feedback |
| Condenser Water Pumps | CWP | Condenser Water Pump Status · Condenser Water Pump Speed · Condenser Water Pump Flow Status · Condenser Water Pump Current · Condenser Water Pump Power · Condenser Water Pump Speed Feedback · Condenser Water Pump Variable Speed Drive Status · VSD Speed · VSD Operating Frequency |
| Primary Hot Water Pumps | PHWP | Primary Hot Water Pump Status · Primary Hot Water Pump Speed · Primary Hot Water Pump Flow Status · Primary Hot Water Pump Current · Primary Hot Water Pump Frequency · Primary Hot Water Pump Power · Primary Hot Water Pump Speed Feedback · VSD Speed |
| Boiler | HWB | Hot Water Boiler Status · Hot Water Boiler Load · Hot Water Boiler Firing Rate · Hot Water Common Leaving Temperature · Hot Water Leaving Temperature |
| Secondary Chilled Water System | SCHW | Secondary Chilled Water Pump Status · Secondary Chilled Water Pump Speed · Secondary Chilled Water Pump Flow Status · Chilled Water Pump Frequency · Secondary Chilled Water Pump Speed Feedback · VSD Speed |
| Tenant Condenser Water | TCW | Tenant Condenser Water Pump Status · Tenant Condenser Water Pump Speed · Tenant Cooling Tower Fan Status · Tenant Cooling Tower Fan Speed · Tenant Condenser Water Recirculating Pump Status · Tenant Condenser Water Pump Current · Tenant Condenser Water Pump Speed Feedback |
| Secondary Hot Water System | SHW | Secondary Hot Water Pump Status · Secondary Hot Water Pump Speed · Secondary Hot Water Pump Flow Status · Secondary Hot Water Pump Current · Secondary Hot Water Pump Speed Feedback · VSD Speed |
| Heat Exchanger | HE | HE Secondary Water Pump Speed · HE Secondary Water Pump Status · HE Primary Water Pump Speed · HE Primary Water Pump Status · Heat Exchanger Secondary Load · HE Load · HE Secondary Water Pump Speed Feedback |
| Under-Floor Heating System | UFHWS | In-Floor System Pump Status · In-Floor Heating Current · In-Floor System Status · Under-Floor Heating Fan Speed · Under-Floor Heating Fan Status |
| Hydraulic Pump | HYD | Hydraulic Pump Status |
| Domestic Hot Water | DHWT | Domestic Hot Water Pump Status · Domestic Hot Water Status · Domestic Hot Water Pump Speed · Domestic Hot Water Leaving Temperature · Domestic Hot Water Pump Current · Domestic Hot Water Pump Flow Status |
| Calorifier | CAL | Calorifier Heating Status · Calorifier Hot Water Common Leaving Temperature · Calorifier Hot Water Leaving Temperature · Calorifier Load · Calorifier Primary Water Leaving Temperature |
| Cold Water Booster Pumps | CWB | Cold Water Booster Pump Status · Cold Water Booster Pump Speed |
| Miscellaneous Pump | MISC-Pump | Miscellaneous Pump Status |
| Heat Recovery Unit | HRU | Heat Recovery Unit Fan Speed · Heat Recovery Unit Fan Status |
| Dry Air Cooler | DAC | Dry Air Cooler Current · Dry Air Cooler Fan Speed · Dry Air Cooler Fan Status · Dry Air Cooler Power |
| Domestic Cold Water | DCW | Domestic Cold Water Pump Speed · Domestic Cold Water Pump Status |
| Air to Air Heat Exchanger | AIR HX | AIR HX Supply Air Fan Status · AIR HX Supply Air Fan Speed |
| Steam Boiler | SB | Steam Boiler Status · Steam Boiler Supply Temperature |
| Econet Heat Recovery Unit | ECO-HR | Econet Heat Recovery Pump Speed · AHU Heat Recovery Pump Speed |
| Solar Water Heater | SWH | Solar Water Heater Leaving Temperature · Solar Water Heater Pump Status |
| Combined Heating & Power | CHaP | CHP Electrical Power · CHP Engine Run Status · CHP Primary Flow Temperature · CHP Running |
| Dry Air Cooler Pump | DACP | Dry Air Cooler Pump Speed · Dry Air Cooler Pump Status |
| Evaporative Cooler | EC | Evaporative Cooler Status |
| Thermal Labyrinth | TL | Thermal Labyrinth Supply Air Fan Speed · Thermal Labyrinth Supply Air Fan Status |
| Under-Floor Cooling System | UFCS | In-Floor Cooling System Pump Flow Status · In-Floor Cooling System Pump Status |

## Field units

| Equipment type | Short code | Metadata to fetch |
| --- | --- | --- |
| Packaged Air Conditioning Units | PAC | PAC Supply Air Fan Status · PAC Supply Air Fan Speed · PAC Indoor Fan Status · PAC Supply Air Fan Current · PAC Supply Air Fan Speed Feedback · PAC Supply Air Flow Status |
| Exhaust Air Fans | EAF | Exhaust Air Fan Status · Exhaust Air Fan Speed · Exhaust Air Fan Flow Status · Exhaust Air Fan Current · Exhaust Air Fan Frequency · Exhaust Air Fan Power · Exhaust Air Fan Speed Feedback · Exhaust Air Fan Speed RPM |
| Fan Coil Units | FCU | FCU Supply Air Fan Status · FCU Supply Air Fan Speed · FCU Power · FCU Supply Air Fan Current · FCU Supply Air Fan Frequency · FCU Supply Air Fan Power · FCU Supply Air Fan Speed RPM · FCU Supply Air Flow Status · FCU Supply Air Velocity |
| Computer Room Air Conditioning Unit | CRAC | CRAC Fan Status · CRAC Fan Speed · CRAC Supply Air Fan Speed |
| Heat Pump | HP | Heat Pump Status · Heat Pump Current · Heat Pump Fan Status · Heat Pump Load · Heat Pump Power |
| Kitchen Fans | KF | Kitchen Exhaust Fan Status · Kitchen Supply Air Fan Status · Kitchen Exhaust Fan Frequency · Kitchen Exhaust Fan Speed · Kitchen Supply Air Fan Frequency · Kitchen Supply Air Fan Speed |
| Air Curtain | ACRTN | Air Curtain Fan Speed · Air Curtain Fan Status |
| Unit Heater | UH | Unit Heater Fan Current · Unit Heater Fan Status |
| Air Cooled Condensers | ACC | Condenser Unit Status |
| Variable Refrigerant Flow Systems | VRF | VRF Outdoor Unit Power · VRF Outdoor Unit Status · VRF Unit Fan Speed · VRF Unit Fan Status |
