# Design decisions log (radio stick V3, LQFP-100)
| # | Decision | Why | Source |
|---|---|---|---|
| 1 | MCU STM32U575VIT6 C5270999 (non-Q), footprint LQFP-100 | JLC 188 @ $6.33; pin-identical to U5A5VJT6 | Michael 06:24Z, ST pin data |
| 2 | J3 = UART4 + I2C3 + SPI2 + CS at once; D2 user LED PC6; 4.7k I2C3 pull-ups | face board + SD breakout + UART simultaneously | pin map |
| 3 | RF1_RX_EN PB5 -> PC7 (later PA3, row 9); SPI2 MISO/MOSI PB14/PB15 -> PC2/PC3 | PB5/PB14 are UCPD1 dead-battery pins, PA15/PB15 CC pins (ST pin data) | EE1-01/02 |
| 4 | Keep radio power default ON (R95 pull-up, PB4) | matches V2 and FC behavior; idle current small | EE1-06 declined |
| 5 | R14/R15 BUSY/DIO1 pull-ups DNP | back-power the unpowered radio | EE1-07 |
| 6 | No J3 series resistors; J3 is 3.3 V logic only (silk) | board space; prototype | EE1-08 declined |
| 7 | LSE drive medium-high in DTS | 7 pF crystal margin | EE1-04 |
| 8 | 30 dBm only on >=1.5 A USB-C hosts (CC sense), firmware rule | E22 ~650 mA TX vs 500 mA USB2 | EE1-03 |
| 9 | Radio pins to the E22-facing side: CS PC4, RST PE3, DIO2 PC5, RXEN PA3, TXEN PA2; RF_PWR_EN PE2 (not PC3, which SPI2 MOSI needs) | E22 route length 425 -> ~309 mm; avoid UCPD pins | L3 + EE1-01 |
| 10 | Delete J4 + I2C1 pull-ups R39/R41; delete R7/R8 0R | no room in the island; UART/3V3/GND on STDC14 | L1, L2 |
| 11 | Crystals and most decaps on the bottom side, inside the LQFP shadow | 1 mm free left of MCU, 0 above | L6 |
| 12 | Layout r1 review acted as the pre-layout schematic review; no separate r2 layout schematic pass | its findings are placement items, verified in layout review | process |
| 13 | Schematic review r2: 0 blockers; fixed stale GPIO18/J4 notes and the pin map README | review-sch-ee-r2 | EE2-04/05 |
| 14 | Keep radio default ON (R95 to +3V3) | matches V2 behaviour students know; moving R95 to GND is now free if wanted | EE2 minor, declined |
| 15 | J3 symbol overlaps the title block in the render: left as is | cosmetic; moving a V2-copied symbol risks broken wires | EE2-07 declined |
| 16 | E22-400M30S (C411292) shows no LCSC/JLC stock: Michael checks in JLC BOM tool; fallback U3 DNP + hand-fit or pre-order | JLC blocked from the cloud | EE2-01 open |
| 17 | Netclasses: Default 0.2/0.15, via 0.6/0.3; USB 0.25/0.15; +3V3 0.3; 5 V rails 0.5 | LQFP 0.5 mm escape; JLC 4-layer min 0.09 mm | layout |
| 18 | Routing: Freerouting 2.1.0 via a headless Java driver (outer layers only, 4 variants, best kept), then maze_v3 for leftovers and plane ties | Freerouting CLI never writes the SES; inner layers stay planes | layout |
| 19 | Layout r1: C113 turned so VCAP/GND sit under pins 48/49; plane-tie vias on 11 supply pins; J5 turned 180, U4 to 270 to free SWO and VBUS | review-pcb-*-r1 | B1, M1, M3 |
| 20 | Layout r2: both reviewers GO for 5 prototypes. Fixed J3 pin labels (port letter + number, P dropped to fit 2.54 mm), BOOT/RESET/USER labels behind the switches (V2 "RST" was stale), 7.4 mm dead GND stub, 0.46/0.2 GND vias for U4.2 and U1.27/C102.2 | review-pcb-*-r2 | N3, EE r2 #4 |
| 21 | Deferred to next spin: U1 pin 99 ground (8 mm), HSE/LSE trace length 9-11 mm, USB pair coupling and D+ ESD stub (matters only for U5A5 HS), fiducials, VCAP/RF_VCC test points, keyed J5 | none stops boot, FS USB or SWD (EE r2) | open |
| 22 | Order settings: tented vias, two-sided PCBA, BOM/CPL from jlcpcb/production_files (footprints carry no LCSC field); check LQFP/U4/U2/U19/Y101/J12/J5 rotation in JLC's preview | CPL offsets learned from V2; J5 offset unknown | open |
| 23 | proves-pcb-design / Greenberg pass: fixed instance names, file format, 5 power symbols, RF_VCC power symbol, value units, connector Values, MPNs, rail ranges, stackup metadata, silk (personality text restored, date, JLC number) | netlist nets identical, ERC and DRC unchanged | reviews/skill-review-r1.md |
| 24 | Left: global labels instead of wires (Greenberg 7/9), stock STM32 symbol (3), R95 rail pointing down, 64 vias < 0.2 mm from pads (V2: 61), single-sided assembly, radio on by default | renames nets or needs a rewrite / re-route; see the review | skill-review-r1 |
