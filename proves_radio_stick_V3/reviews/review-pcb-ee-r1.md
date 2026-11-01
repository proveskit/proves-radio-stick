# Radio Stick V3: layout EE review, round 1 (electrical correctness of the routed board)

Board: `proves_radio_stick_V3.kicad_pcb` (08:54). Tools: KiCad 10 pcbnew Python + `kicad-cli pcb drc --schematic-parity`.
My scripts are in `scratchpad/eer1/`; I edited no repo or work files.

**Verdict: no blockers.** The routed copper matches the netlist, and USB enumeration and SWD should work.
Four island majors are cheap fixes worth doing before the order: the ESD ground (M1), the VSS returns (M2), the D+ ESD stub (M3) and the decoupling detours (M4).

## What I checked and found clean
- **Netlist vs copper.** I compared all 316 pad-net pairs in `v3.net.xml` with the PCB pads: 0 mismatches. No netlist ref is missing from the PCB; the PCB has extra H1-H4 and a logo.
  DRC: 0 copper errors and 0 unconnected. The 53 parity `net_conflict` items are all `unconnected-*` NC pins with no net (benign).
- **U1 pin map.** Every pinmap.csv row lands on the correct LQFP-100 pad, checked against `opd/mcu/STM32U575VITx.xml` and `STM32U5A5VJTx.xml`.
  Examples: PA11=70, PA12=71, PA13=72, PA14=76, PB3=89, PH3/BOOT0=94, NRST=14, VCAP=48 (C113 4.7 uF), VDDUSB=73.
  All VDD/VDDA/VREF+/VBAT pins are on +3V3, and all VSS/VSSA/VREF- pins are on GND. The used pins have the same names on the U5A5.
- **USB data mapping.** J12 A6/B6 go to USB_D+, then U4 pins 3/4 (I/O2), then U1.71 (PA12). J12 A7/B7 go to USB_D-, then U4 pins 1/6 (I/O1), then U1.70 (PA11).
  U4 pinout (1 I/O1, 2 GND, 3 I/O2, 4 I/O2, 5 VBUS, 6 I/O1) is from the USBLC6-2 datasheet front-page diagram.
  - D- passes through the U4.1 pad on its way to the MCU (graph path: J12.A7, then U4.1, then vias (234.38,96.73) and (234.26,95.02), then U1.70). This is good.
  - CC: R26/R27 (5.1k Rd) sit 0.05 mm from A5/B5.
- **VBUS to U4.5.** The path is J12 VBUS, then F.Cu to via (239.22,100.83), then B.Cu 0.3 mm to via (233.3,101.14), then U4.5. It is present and continuous.
- **J5 STDC14 (rotated 180).** Pad positions follow the pad numbers: odd pins are at x=234.19 and even pins at x=232.92, with pin 1 at (234.19,93.41).
  - Nets: 3 +3V3, 4 SWDIO, 5/7/11 GND, 6 SWCLK, 8 SWO, 12 NRST, 13 RX (PA10), 14 TX (PA9); 1, 2, 9 and 10 are NC.
  - This matches STDC14 (UM2448 STDC14 table, from memory: 13 = T_VCP_RX, the target RX; 14 = T_VCP_TX).
  - Copper lengths: SWDIO 3.9 mm with 0 vias, SWCLK 5.5 mm with 0 vias, SWO 12.2 mm with 1 via, NRST 31 mm with 2 vias.
- **Reference planes.** I sampled every non-GND track at 50 um against the fill of its reference plane (In1 for F.Cu, In2 for B.Cu).
  - No signal crosses the In2 GND-island edge or the V2 In2 VBUS track (x 239.2-241.1, y 100.8-109.0). The only exceptions are the crystal nets and a 0.5 mm +3V3 B.Cu stub at (240.9,106.5).
  - The remaining voids are 0.5-0.95 mm runs next to THT pads (J3, TPs, J5).
- **In2 +3V3 plane.** It is one 2156 mm² region (plus a 0.18 mm² sliver at J5.3, flagged as a starved thermal). All 11 +3V3 vias land in it, including the buck output via (240.39,106.01).
- **RF clearance.** The closest island signal to the RF_ANT/U3-ANT copper is SPI1_CS0 at 7.6 mm (TP2, 189.1,85.9). No island copper is inside RF_keepout.
- **SPI1 lengths (MCU to E22).** SCK 39.9, MOSI 35.4, MISO 41.8 and CS 40.1 mm, with 2-3 vias each; the stubs to the test points are 3-6 mm. This is harmless at the SX1268's 16 MHz SPI limit.
  DIO/BUSY: BUSY (RF1_IO0, PB9) is 23.3 mm with 1 via, DIO1 (RF1_IO1, PB8) is 19.1 mm with 3 vias, DIO2 (PC5) is 23.5 mm with 0 vias.
- **CC sense to PB1/PB2.** CC1 is 16.8 mm and CC2 is 20.3 mm, with 2 vias each, on In1/In2 reference. They pass more than 3 mm from the U2/L1 SW node; acceptable for a DC ADC sense.

## Island findings

### MAJOR
**M1. U4 (USBLC6) GND pin has no via, so the ESD return runs 5.8 mm of 0.2 mm track.**
- Where: U4.2 at (233.3,97.86).
- Evidence:
  - DRC reports `starved_thermal` on U4 pad 2.
  - The only pour U4.2 touches is a 1.5 mm² F.Cu sliver under U4, and that sliver has 0 vias.
  - Its copper is a 0.2 mm track via (233.3,96.95) and (234.15,96.10) to R27.1 and then J12 A12/B1. Those sit on a 2.1 mm² sliver, also with 0 vias, and reach In1 only through the shell S1 THT.
- Why it matters: USBLC6-2 datasheet §2.3 says "from GND plane to GND pin must be as short as possible". §2.2 estimates about 6 nH per 10 mm, adding about 144 V to the clamping voltage in its example.
- Fix: add a 0.45/0.2 GND via at **(234.50, 99.11)**. That spot is inside the existing U4 GND sliver and clear on F.Cu and B.Cu (my grid search found 0.36 mm or more to D-). This ties U4.2 to In1 within about 1.7 mm. If M3 frees space, also add a second via at the U4 body centre.

**M2. Two VSS pins have no local plane via.**
- U1.49 (227.7,106.53) touches no pour. Its only copper is a 0.2 mm track running 11.5 mm via (230.54,105.46) and (233.32,102.68) to J12 A1/B12, which sit on a 9 mm² piece with 1 via.
  This VSS pin serves VDD50 (C103) and VCAP48 (C113), so the C103 and C113 loops return through the USB connector.
  - Fix: rotate C113 to 0°. Pad 1 (VCAP) then sits at (226.97,108.2) under pin 48 and pad 2 (GND) at (227.93,108.2) under pin 49.
  - Then run U1.49 straight down to C113.2 and add a 0.45/0.2 GND via at **(227.93,108.95)**, which probes clear.
- U1.99 (216.7,91.18) touches no pour. The nearest via by copper is 8.4 mm away at (209.47,90.78). C105 (the decap for VDD100) returns through the B.Cu pour to a via 2.5 mm away.
  - No 0.45/0.2 site within 1 mm is free. The space is blocked by the BOOT0 B.Cu track at x=218.02, the RF1_IO0/IO1 F.Cu tracks and the +3V3 via (215.54,90.58).
  - Fix: move the BOOT0 B.Cu run (218.02, 88.24 to 91.53) 0.6 mm left, then drop a GND via about 0.5 mm above C105.2 (217.88,92.4) and stub it to pin 99 under the body.
- U1.27 / C102.2 (minor): these share a 1.1 mm² sliver with no via. They reach the main F.Cu pour through 3.2 mm of track to R12.1 (nearest via 2.6 mm), and no free site exists. Acceptable.
- Rule: AN5373 says each VSS goes to the ground plane by the shortest path (from memory; st.com blocked).

**M3. USB_D+ ESD clamp hangs on a T-stub; the D+ line does not pass through U4's pads.**
- Graph path: J12.A6/B6, then via (236.08,98.25), then B.Cu diagonal (235.30,96.62) to (232.69,99.23), then via (231.18,99.23), then B.Cu up x=231.38 to via (231.38,94.94), then U1.71.
  U4.3/U4.4 hang off the via at (231.18,99.23) on a 2.1 mm stub (1.17 mm F.Cu plus 0.9 mm, plus a via).
- Impact:
  - At full speed (12 Mb/s) the stub is electrically invisible, so enumeration is unaffected.
  - The clamp still sits 5.5 mm upstream of the MCU branch, but the via plus stub adds about 1.5-2 nH in series with the clamp, against datasheet §2.3/Fig. 6 ("track from data lines to I/O pins as short as possible").
- Fix: re-route D+ so the connector side lands on U4.4 (232.35,100.14) and the MCU side leaves from U4.3 (232.35,97.86), as in the datasheet Fig. 17 flow-through.
  Delete the B.Cu diagonal and the via at (231.18,99.23). This also frees the U4 body centre for a second GND via (M1).
  If there is no time tonight, it is acceptable for a full-speed prototype.

**M4. Decoupling caps are reached by detours: up to 10.6 mm of track plus a via from the VDD pins.**
- Distances, measured as track-only shortest paths in pcbnew:

  | VDD pin | Nearest decap (track) | Nearest In2 via (track) |
  |---|---|---|
  | VDD11 | C108, 8.5 mm | 6.2 mm |
  | VDDUSB73 | C106, 10.6 mm | 8.4 mm |
  | VDD75 | C106, 7.7 mm | 5.5 mm |
  | VBAT6 | none | 6.0 mm |

  VDD28, VDD50 and VDD100 are fine at 1.4, 2.0 and 3.2 mm.
- Cause: pin 75 runs F.Cu left past C104/C106 to a via at (224.75,93.88), then B.Cu back right to the caps at (226.92,92.9/94.1).
- Fixes:
  - Add a +3V3 via at about (227.0,92.85) on the existing pin-75/73 F.Cu track, straight into C104.1/C106.1. That cuts about 5 mm.
  - For VDD11, add a via next to C108.1 (221.32,95.0) on the pin-11 F.Cu run.
  - C109-C112 (the VDDA/VREF+ caps) return to GND through 6.5-8.4 mm of B.Cu pour. Add one GND via between C110 and R9 (around 220.7,104.4, check DRC).

### MINOR (island)
- **m1. Crystal routing.**
  - OSC_IN goes pin 12, then out to via (212.78,98.26) outside the pin row, then 3.5 mm on B.Cu to Y101.1. Its load cap C115 sits on the opposite branch, 3.6 mm F.Cu plus a via away. Total length is 11.2 mm.
  - OSC32_IN is 9.0 mm and OSC32_OUT is 7.6 mm, for crystals only about 3 mm from the pins.
  - The OSC_IN and OSC32_IN B.Cu legs cross the In2 GND-island edge at x=215.
  - AN2867 asks for the shortest traces with the load caps next to the crystal (from memory). Workable at 16 MHz with the LSE medium-high drive (decision 7), but shorten if re-routing.
- **m2. In2 GND island.** It is 38 mm² but stitched by only one via (217.6,94.9). Add 3 GND vias inside it, for example at (215.6,97.5), (219.9,97.3) and (219.9,101.6), after checking DRC.
- **m3. USB pair for the U5A5 (HS).** Connector-to-MCU length is 14.6-17.1 mm for D+ (3 vias) and 10.9-11.7 mm for D- (2 vias), so skew is about 3.5-5 mm. The pair is not coupled and D+ references In2 on B.Cu. This is fine at full speed but must be redone as a 90 ohm coupled pair before any OTG_HS build.
- **m4. NRST.** NRST runs 6 mm parallel to OSC_OUT on F.Cu at 0.5 mm pitch (y 99.35 vs 98.85). C114 (100 nF) is 8 mm by copper from pin 14. Acceptable with the 100 nF.
- **m5. Parts and BOM fields.** U2 footprint has LCSC C2070694 (RLTT) but the schematic and BOM have C130072 (RLTR). 33 island footprints (C101-C118, R101-R105, U1, U4, Y101/2, J5, SW1-3, D2) have no `LCSC Part` field.
  Run Update PCB from Schematic before generating the JLC BOM/CPL from the PCB.
- **m6. J5 header.** J5 is an unshrouded 1.27 mm header (`PinHeader_2x07`). The STLINK-V3 STDC14 ribbon can be plugged in reversed. Add a pin-1 silk mark next to (234.19,93.41) or use a shrouded part such as FTSH-107.

## Inherited (V2 copper, unchanged; I confirmed identical tracks and vias in work/v2.kicad_pcb)
- **i1 (minor-major). Radio supply.** The E22's ~650 mA TX current (E22-400M30S manual, from memory; ebyte page fetched without specs) flows through single 0.56/0.3 vias at every layer change: (239.22,100.83), (239.99,109.02), (211.70,115.70), (208.44,116.55) and (206.94,113.30), plus a parallel via at (206.94,114.9).
  - A 0.3 mm via carries roughly 1-1.5 A at a 10 °C rise, so the margin is about 2x.
  - The VBUS run on In2 is 9.4 mm of 0.4 mm track. On JLC 4-layer the inner copper is 0.5 oz (from memory), giving about 23 mΩ, 16 mV drop and a large temperature rise under continuous TX by IPC-2221 internal (about 40 °C).
  - Fix: double each via (add one 0.6 mm from each), and widen the In2 VBUS track to 0.8 mm or move it to B.Cu.
- **i2.** There is a dangling VBUS via at (240.68,108.27) with only an F.Cu connection; it can be deleted.
- **i3.** The F.Cu routing under the E22 body has grown versus V2: about 120 mm of F.Cu signal now runs inside the U3 courtyard (V2 had about 36 mm). For example, SPI1_CS0 has 22 mm and RF1_RX_EN 18 mm on F.Cu, directly under the module.
  EBYTE hardware notes advise against routing under the module, or recommend keeping its top-side area as ground (from memory). This is island routing in an inherited area: move these runs to B.Cu, where In1 GND shields them, if re-routing.
- **i4.** The USBLC6 datasheet Fig. 17 shows 100 nF on VBUS at the device. The nearest VBUS cap is C15 (10 uF) at the buck, about 10 mm away. Optional: add a 0402 100 nF from U4.5 to GND.

## Things that would stop enumeration or flashing
None found:
- D+/D- are not swapped, and both CC lines have Rd.
- VBUS reaches U4.
- The HSE is routed to PH0/PH1.
- VDDUSB is on +3V3.
- The BOOT0 10k pull-down R101 is on PH3.
- NRST reaches SW2 and J5.12.
- SWDIO/SWCLK/SWO reach J5 pins 4/6/8 and J22.

## Sources
- USBLC6-2 datasheet, st.com/resource/en/datasheet/usblc6-2.pdf: cover-page pin diagram, §2.2 (p.4), §2.3 (p.6, Figs. 5-6), §2.6 Fig. 17 (p.11). Read via WebFetch.
- ST open pin data XMLs (local).
- From memory (st.com/ebyte/JLC not readable here): AN5373, AN2867, UM2448 STDC14 table, E22-400M30S manual, JLC inner copper weight, via current rule of thumb.
