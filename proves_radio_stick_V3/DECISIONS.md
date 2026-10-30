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
