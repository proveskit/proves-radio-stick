# V3 radio stick: pre-layout schematic review, round 1 (principal PCB layout view)

Goal restated: get the STM32U575VIT6 (LQFP-100) radio stick order-ready at JLCPCB tonight, as the trial board for STM32U5A5. Only the MCU island changes. This review asks whether the r1 schematic/netlist gives layout what it needs, and whether the island can hold it.

Evidence sources (all read this session):
- Board: `rs/proves_radio_stick_V3/proves_radio_stick_V3.kicad_pcb` (still V2), read through KiCad 10 pcbnew via `kc.sh`.
- Netlist `work/v3.net.xml`, BOM `work/v3_bom_r1.csv`, `pinmap/pinmap.csv`, `PLAN.md`, `SOURCING.md`, `tools/gen_v3_schematic.py`.
- ST open pin data `opd/mcu/STM32U575VITx.xml` and `STM32U5A5VJTx.xml`. Diffed by position. All 100 pin names match. Only the USB AF names change (FS to HS on PA8 to PA12 and PA14).
- Placement checker (rerunnable): `work/lr1/place_check.py`. It loads the real KiCad library footprints at the proposed coordinates and checks courtyard overlap per side against each other and against the V2 parts that stay. Result: 0 new overlaps. Two touching courtyards remain (SW2/SW3 at 0.00 mm). R26 and R27 overlap J12 by 0.01 mm, and that overlap is already in V2.
- Dumps: `work/lr1/dump.py`, `routes.py`, `vbus.py`, `pads.py`.
- No datasheet could be fetched: jlcpcb.com API and st.com return 403 through the proxy. Points marked "(memory)" are from memory and not verified this session.

## Board facts that drive the layout (measured)

- Stackup. F.Cu / 0.2104 core / In1 / 1.065 prepreg / In2 / 0.2104 / B.Cu, εr 4.5. In1 is a whole-board GND zone, In2 a whole-board +3V3 zone, and B.Cu has a whole-board GND pour. F.Cu has GND only for x < 216.1, plus RP2350-specific islands: a +1V1 pour, an EPAD GND pour (pri 8/9) and a +3V3 pour (pri 6).
- Rules. Min track and clearance 0.127. Via 0.4/0.2. Default netclass 0.25 track, 0.8/0.4 via. The RF netclass has diff pair 0.2/0.25. There is no USB netclass.
- Fixed neighbour courtyards:
  - U3 (E22): x ≤ 212.37, y 88.54..113.01.
  - J3: y ≥ 109.86, x 212.59..239.54. THT pads at y 113.5.
  - J12: x ≥ 236.16, y 93.53..104.25. D+/D- pads at x 237.44, y 98.14..99.64.
  - L1: x ≥ 231.66, y 104.17..108.56.
  - H4: x ≥ 240.0, y ≤ 89.5.
- E22 pads:
  - Top row y 88.75: CS 191.70, SCK 194.24, MOSI 196.78, MISO 199.32, RST 201.86, BUSY 204.40, DIO1 206.94.
  - Bottom row y 112.75: RXEN 196.78, TXEN 199.32, DIO2 201.86, VCC 204.4/206.94.
  - ANT is pad 21 at (181.56, 88.75), with the RF keepout at x 168.5..182.3.
- V2 routed every E22 signal by dropping a via next to the E22 pad and running on B.Cu under the module to the island. This adds 16 to 30 mm of B.Cu per net with 2 vias (`routes.py`). That channel is proven and is reused below.
- V2 VBUS to the radio runs as a 0.8 mm B.Cu trace at y 115.4 under J3, from x 212 to 239.2. It stays out of the island.
- Already two-sided: C4, C79, C80, R95, U19, R14 and R15 are on B.Cu in V2. Bottom-side parts add per-part cost only. They do not add a new side.
- No fiducials on the board (0 matches for "Fiducial").

## Fit arithmetic (question 2)

- LQFP-100 (KiCad `LQFP-100_14x14mm_P0.5mm`): pad centres ±7.675, pads 1.6 × 0.3. Tip to tip is 16.95 mm, not 16. Courtyard is 17.55 × 17.55 = 308 mm².
- Height. The top-side free height from the board edge (84.3) to the J3 body (109.86) is 25.56 mm. The MCU takes 17.55, which leaves 8.0 mm. The button/connector row needs 5.5 mm (KMR2 body plus pads). That leaves about 2.2 mm under the MCU for one row of 0402s and LEDs.
- Width. Between the E22 courtyard (212.37) and J5/U4 (231.3) the width is 18.9 mm. The MCU takes 17.55, which leaves 1.06 mm on the left as a routing-only channel.
- So there is no room for a top-side decoupling ring or crystals. The crystals and 11 of the 14 MCU caps go on B.Cu inside the MCU shadow. The B side inside the 17.55 mm square has 308 mm². The crystals, load caps, decaps and pull resistors use about 77 mm² of courtyard, roughly 25 %.
- Top-side budget for the island: x 212.6..240, y 84.5..109.86, minus J12 and L1, is about 612 mm². Proposed top placements use about 472 mm² of courtyard (77 %). The rest is the left channel and the bottom strip.
- What does not fit:
  - The top strip from x 212.6 to 240 is 27.4 mm long. Buttons (9.9), J22 (6.9) and J4 (16.3, unfitted 2.54 mm header) need 33.1 mm before STDC14 (10 mm horizontal). **J4 has to leave the schematic.**
  - Between the MCU courtyard (230.97) and the J12 courtyard (236.16) there is 5.2 mm. U4 (3.5 mm wide rotated) plus R7/R8 0 Ω in series (1.9 mm) plus R26/R27 does not fit. **R7/R8 have to go.**

## Findings

| id | sev | finding | evidence | concrete fix |
|---|---|---|---|---|
| L1 | blocker | J4 (Conn_01x06, THT 2.54 mm, no LCSC, excluded from BOM) is still in the netlist and cannot be placed. It needs 16.3 mm of top edge that STDC14, J22 and three buttons already use. Its signals are SCL1/SDA1/RX/TX/+3V3/GND. | netlist J4.1..6. V2 courtyard 223.74..240.06 × 83.78..87.42. Top-strip sum in Fit. | Delete J4 from the generator. RX/TX/3V3/GND stay reachable on STDC14 (pins 13/14/3/5). If I2C1 must be broken out, add 2 SMD test pads on the bottom. |
| L2 | major | R7/R8 (0 Ω, 0402) in series on USB_DM/DP leave no room for U4 between the MCU and J12. They also add 4 pads and stubs on a pair that must later carry HS on U5A5. Neither the U575 OTG_FS nor the U5A5 HS PHY needs series resistors (memory). | netlist R7 USB_DM↔USB_D-, R8 USB_DP↔USB_D+. Gap 230.97→236.16 = 5.19 mm. | Delete R7/R8 and join USB_DM to USB_D- and USB_DP to USB_D+. Keep U4 as the only part on the pair. |
| L3 | major | The pin map puts E22 nets on the far side of the package, so they cross the USB/SWD/STDC14 corner and the button row. CS=PA15 (pin 77, top-right), RST=PB12 (51, bottom-right), TX_EN=PA8 (67, right side, between USART1 and USB), RX_EN=PB5 (91) and PWR_EN=PB4 (90) sit on the top edge under the buttons, and DIO2=PB10 (47, bottom-right). The E22 bundle arrives on B.Cu at the MCU's left/bottom-left. | pin coordinates at U1 (222.2, 98.85) rot 0 computed from the footprint. E22 pad rows above. Manhattan sum 425 mm before vs 309 mm after (script in reply). | Swap to free pins (all unconnected today, same names on U575 and U5A5): CS→PC4 (33) as GPIO CS, RX_EN→PA3 (26), TX_EN→PA2 (25), DIO2→PC5 (34, EXTI5 unique), RF_PWR_EN→PC3 (18), RST→PE3 (2). Keep SPI1 PA5/6/7 (30-32), BUSY PB9 (96) and DIO1 PB8 (95, EXTI8). Update pinmap.csv, the generator and the Zephyr DTS together. |
| L4 | note | RF_PWR_EN is on PB4 (NJTRST, pull-up after reset, from memory). R95 is a 10 kΩ **pull-up** to +3V3, so the radio load switch is ON from power-up through boot and USB enumeration (up to 650 mA TX-capable rail live before firmware runs). | pinmap PB4 RF_PWR_EN. OPD pin 90 "PB4 (NJTRST)". netlist R95.1 RF_PWR_EN, R95.2 +3V3. | EE/product call: if the radio should stay off until firmware enables it, make R95 a pull-down. The L3 move to PC3 also takes the pin off the JTAG pull-up. |
| L5 | major | No USB differential netclass. The only diff-pair class (RF) is 0.2/0.25, about 110 Ω on this stackup (IPC-2141 estimate). U5A5 runs HS on PA11/PA12. | Netclass dump. Stackup F.Cu→In1 0.2104 mm, εr 4.5. | Add a `USB` netclass for USB_D±/USB_DP/DM: 0.25 mm width, 0.15 mm gap, about 91 Ω by estimate. Confirm with the JLC impedance calculator for JLC04161H-7628 and order impedance control only if HS matters for this run. Route the pair on F.Cu over unbroken In1, with no vias. |
| L6 | major | Crystals and decaps cannot sit on top. Only 1.06 mm is free on the left (E22) and 0 mm on top (buttons), so placement is forced to B.Cu. The B.Cu layer is referenced to In2 (+3V3), not GND, at 0.21 mm. | Fit section. Stackup. | Place Y101/Y102/C115-118 on B under pins 8-13 (plan below). Add an In2 GND island (higher priority than the +3V3 zone) under the crystals and a B.Cu rule area (no tracks except OSC nets) around them. Stitch GND vias. |
| L7 | major | STDC14 cannot go "opposite USB-C" as PLAN.md §layout asks. The island has no left edge. The only spot is vertical at the top-right, beside J12. The STLINK 14-pin plug body (assumed about 6 × 13 mm, not verified) could foul the USB-C shell top by up to about 0.2 mm at x 236.2, y 93.5..96. | J5 courtyard 231.31..235.81 × 84.61..94.59 (checker). J12 courtyard starts at x 236.16. | Check against the STLINK-V3 cable drawing or a 3D model before freezing. Fallback: STDC14 horizontal at x 221.4..231.4 on the top strip, and J22 moves to B.Cu or is dropped (product call. PLAN wants it for Pi Debug Probe users). |
| L8 | minor | `FC_DEV_BOARD:BTN_KMR2_4.6X2.8` has no courtyard, so DRC cannot catch the button-to-MCU spacing (0.06 mm in the plan). | `GetCourtyard` empty for SW1/SW2. | Add an F.CrtYd of ±1.65 × ±2.75 mm (rot 0: ±2.75 × ±1.65) to the footprint. |
| L9 | minor | D3/R80 (3V3 LED) V2 position overlaps the MCU courtyard. | D3 229.65..231.19 × 106.06..109.11 vs U1 to 230.97 × 107.62. | Move D3 to the bottom strip (224.0, 108.7) and R80 to B.Cu. |
| L10 | minor | STDC14 is C22438122, an unshrouded and unkeyed THT 2x7 1.27 mm header. The STLINK cable can mate rotated. THT also means a hand-solder line item at JLC. | SOURCING.md row J5. BOM footprint `PinHeader_2x07_P1.27mm_Vertical` (THT, 0.65 drill). | Accept for the trial board with bold pin-1 silk and a "notch →" mark. A keyed shroud (FTSH-107) has about 12 in stock per SOURCING. |
| L11 | minor | No fiducials. Both sides now carry fine-pitch or 0402 parts (0.5 mm LQFP on top). | 0 Fiducial footprints. | Order with JLC edge rails and fiducials added by JLC on the two long edges (USB-C overhangs the right edge by 0.13 mm, SMA sits on the left edge). The island has no top-side room for board fiducials. On B.Cu, 2 fiducials fit outside the MCU shadow, for example near x 236..239 clear of the J12 shell posts. |
| L12 | minor | Pull-ups R5 (RST), R9 (CS), R14 (BUSY) and R15 (DIO1) go to +3V3 while E22 VCC (RF_VCC) is switched by U19. With the radio off they back-power its I/O through ESD diodes. | netlist R5.2, R9.2, R14.1, R15.1 on +3V3. U19 OUT = RF_VCC. | EE reviewer to decide: drop R14/R15 (BUSY and DIO1 are radio-driven outputs) and set the MCU pins to analog when PWR_EN=0. Possibly inherited from V2. |
| L13 | minor | Little bring-up access: no pads for VCAP, +3V3, VBUS or RF_VCC. | netlist has no TP on those nets (TP1-7 are SPI/RF only, unfitted Keystone). | Add 1.0 mm SMD test pads on B.Cu for VCAP, +3V3, RF_VCC and GND. No BOM impact. |
| L14 | minor (inherited) | R26/R27 courtyards overlap J12 by 0.01 mm. VBUS runs on In2 inside the +3V3 plane at x 239..241, y 100.8..109. | checker. `vbus.py`. | Nudge R26/R27 0.05 mm left. Leave the VBUS-on-In2 as is (outside the island). |
| L15 | note | RP2350-era F.Cu zones (+1V1 pour, EPAD GND pri 8/9) sit inside the island. The +3V3 F.Cu pour (pri 6, x from 230.66) reaches into the MCU courtyard corner. | zone dump. | Delete the +1V1 and EPAD zones. Trim the +3V3 pour to x ≥ 231.4. Extend the F.Cu GND pour over the island and under the LQFP body, tied to VSS 10/19/20/27/49/74/99 and stitched to In1. |
| L16 | note | Footprints are fine for JLC Standard. All 0402 (JLC handles 0201). The 3225-4 pad suits X322516MLB4SI. The 3215-2 suits SC-32S. The LQFP is the KiCad IPC land pattern. The CL values match the BOM caps (9 pF→12 p, 7 pF→10 p, per SOURCING). | BOM. SOURCING.md. | None. Verify the 4.7 µF 0402 (C23733) is X5R ≥ 6.3 V for VCAP (memory: ESR < 0.1 Ω required). |
| L17 | note | JLC cost: the board is already two-sided (V2), so putting decaps and crystals on B adds per-part cost only. THT on the board: J2 SMA, J3, J5 (new), and the J12 shell posts. | dump above. | None. Expect one extra THT line for J5 (memory: JLC charges hand solder per joint). |

## Proposed placement (checked by `work/lr1/place_check.py`, 0 new overlaps)

U1 sits at the centre of the island, rotated 0 (pin 1 top-left). USB pins 70/71 face J12, SWD pins 72/76 face J5, and the E22 bundle lands at the left and bottom-left after the L3 swaps.

| ref | side | centre (x, y) mm | rot | courtyard / note |
|---|---|---|---|---|
| U1 STM32U575VIT6 | F | 222.20, 98.85 | 0 | 213.43..230.97 × 90.08..107.62. Pins: 12/13 at x 214.53, y 98.35/98.85. 70/71 at x 229.88, y 95.35/94.85. 48/49/50 at y 106.47, x 227.2/227.7/228.2. |
| SW1 BOOT0 / SW2 RESET / SW3 USER | F | 214.25 / 217.55 / 220.85, 87.27 | 90 | 212.60..222.50 × 84.52..90.02 (pitch 3.3) |
| J22 JST-SH SWD | F | 226.00, 87.20 | 0 | 222.56..229.44 × 84.55..89.84. Signal pins face the MCU. |
| J5 STDC14 (pin 1 origin) | F | 232.92, 85.79 | 0 | 231.31..235.81 × 84.61..94.59, vertical. THT tails keep B clear at x 232.4..234.7. |
| U4 USBLC6-2SC6 | F | 233.30, 99.00 | 90 | 231.56..235.04 × 96.91..101.09. Flow-through: D- on 1/6, D+ on 3/4. Pin 2 GND via straight to In1. |
| R26 / R27 (CC 5.1k) | F | 235.66, 100.70 / 235.66, 95.62 | 90 / -90 | R27 moves down 0.7 mm to clear J5 |
| D1 FW-active / D2 user LED | F | 237.20 / 238.90, 91.50 | 90 | above J12, below H4 |
| D3 3V3 LED | F | 224.00, 108.70 | 0 | bottom strip, under free pins 38-46 |
| C113 VCAP 4.7 µF | F | 227.45, 108.20 | 180 | pads directly below pins 48 (VCAP) / 49 (VSS). The loop is under 2 mm with no vias. |
| C(VDD50) / C(VDD28) 100 nF | F | 229.40 / 217.45, 108.20 | 0 | straddle pins 49/50 and 27/28 |
| Y101 16 MHz | B | 216.90, 99.00 | 90 | under pins 12/13. Two staggered vias at x ≈ 215.8 and 216.4. Trace ≤ 2.5 mm. |
| C115 / C116 12 pF | B | 219.40, 98.00 / 219.40, 100.10 | 90 | |
| Y102 32.768 kHz | B | 216.90, 94.70 | 90 | under pins 8/9 |
| C117 / C118 10 pF | B | 219.00, 93.90 / 219.00, 95.90 | 90 | |
| C101-C112, C114 | B | inside the pad ring, one per VDD/VSS pair: VBAT 6, VDD 11, VREF+/VDDA 21/22, VDD 75, VDDUSB 73, VDD 100. C114 by NRST 14. | – | Vias go just inside the pad inner edge (≥ 215.7 / ≤ 228.7 / ≥ 91.9 / ≤ 105.8), staggered ≥ 1 mm apart so In1 keeps webbing. |
| R101 (BOOT0), R102 (USER_BTN), R103/R13/R80 (LEDs), R39/R41, R104/R105 | B | near their pins and loads, outside the crystal rule area | – | |
| R5, R9, R11, R12 (E22 pulls) | B | under the E22 right end, x 207..212, next to R14/R15 | – | on the B.Cu bundle |
| R7, R8, J4 | – | deleted (L1, L2) | | |

Routing plan:
- **USB.** F.Cu from pins 70/71 (x 229.9, y 94.85/95.35) diagonally into U4, then to J12 A6/B6/A7/B7, about 8 to 9 mm. The pair passes between J5's last row (y 93.41) and U4. Join A6/B6 and A7/B7 with V2's existing J12 fan-out. The ESD split around U4 is about 1.9 mm. Use the USB netclass from L5.
- **E22 bundle.** Vias next to the E22 pads (as in V2), then B.Cu under the module. The top row (SCK/MOSI/MISO/CS) runs diagonally to the bottom-left corner pins 26-34. RXEN/TXEN/DIO2 come along y 109..112 above the J3 pads (pad top edge 112.4). RST/BUSY/DIO1 go to the top-left pins 2/95/96. Keep B.Cu at x ≥ 190 (the closest V2 via was 191.7), so nothing enters the RF keepout or runs under the ANT feed. Keep the bundle out of the crystal rule area (B, x 215..220, y 92.6..101.2).
- **J3 IO.** PA0/PA1/PC0/PC1 run down the 1.06 mm left channel (3 tracks at 0.152/0.152). PB13-15 come from the bottom-right pins 52-54. Everything reaches J3 above its THT pads.
- **Top-side pins.** Pins 76-100 cannot fan out upward (button and J22 pads are 0.5 mm away). Fan inward to vias. SWO (89) and NRST (14) reach J5 on B.Cu.
- **Ground.** In1 stays solid. F.Cu GND pour under the LQFP body with stitching. No In1 cuts in the island.

## Answers in brief
1. The schematic is close. It needs: J4 deleted, R7/R8 deleted, a KMR2 courtyard, test pads, and the six-pin swap. Footprints are JLC-fine. No missing ground or shield nets (U4.2, Y101.2/4, J12.S1 and all VSS are on GND).
2. It fits only with the MCU at (222.2, 98.85) rot 0. Crystals and 11 caps go on B. J4, R7 and R8 are deleted. STDC14 goes vertical at the top-right. D3/R80 move.
3. USB is about 9 mm on F.Cu and needs a 90 Ω class. The E22 nets use V2's proven B.Cu-under-module channel. The RF feed is more than 30 mm away. The VCAP loop is under 2 mm on F.Cu. In2 is +3V3, so B.Cu crystals need an In2 GND island.
4. The board is already two-sided. J5 adds one THT line. Use JLC rails and fiducials on the long edges.
5. Six swaps (L3), verified free and identically named on U575VIT6 and U5A5VJT6 open pin data.
