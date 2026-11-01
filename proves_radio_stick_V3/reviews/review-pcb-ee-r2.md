# Radio Stick V3: layout EE review, round 2 (commit 5e7e67e)

I read the repo board (byte-identical to work/r2.kicad_pcb) with KiCad 10 pcbnew Python and `kicad-cli pcb drc --schematic-parity`. I compared it with the r1 board (`git show 3df05ed`).
Scripts and DRC JSON are in `scratchpad/eer2/` (q20-q23, site.py). I changed no repo or work files.

**Verdict: GO for a 5-board prototype.** Nothing found stops boot, USB enumeration or SWD flashing. Two optional vias, about 10 minutes of work, would close the last ESD and VSS gaps (N1).

## Re-checks that still pass
- **Netlist vs copper.** All 316 pad-net pairs match `v3.net.xml` (0 mismatches).
- **DRC.** 0 unconnected, 0 copper or clearance errors. The 53 parity `net_conflict` items are all NC `unconnected-*` pins.
- **USB, SWD, clocks.**
  - USB D+/D- mapping is unchanged and correct: PA12=71, PA11=70; D- flows through U4.1.
  - J5 STDC14 is unchanged: 4 SWDIO, 6 SWCLK, 8 SWO, 12 NRST, 13 RX, 14 TX.
  - HSE goes to pins 12/13, LSE to pins 8/9, VCAP to pin 48 (1.8 mm F.Cu, 0 vias).
- **Planes.**
  - In1 GND is one fill piece.
  - In2 +3V3 is one 2139 mm² piece plus a 0.2 mm² sliver at J5.3, which is the only starved thermal left.
  - The In2 GND island now has 4 stitch vias (r1: 1).
- **The 36 new vias.**
  - All are 0.6/0.3, and all F/B vias are tented by the board default.
  - Two touch the inner end of a U1 pad by 0.005 mm: (215.62,102.95) at pin 21 and (230.97,92.75) at pin 75. Both are the same net (+3V3).
  - Their drill edges sit 0.15 mm outside each pad, so the drill is clear of the paste. Benign.

## 1. Round-1 findings
| # | Status | Evidence (r2 measurement) |
|---|---|---|
| M1 U4 GND via | NOT FIXED | U4.2 sits on a 3.2 mm² F.Cu sliver with 0 vias. The nearest GND via is 5.9 mm away; by copper it is 5.8 mm to J12 A12/B1. A 0.45/0.2 site at (234.50,99.11) is still free and lies inside that sliver (site.py, q23). The maze tool only tried 0.6/0.3. |
| M2a U1.49 / C113 | FIXED | C113 is rotated. U1.49 reaches C113.2 in 1.4 mm, then a new via at (227.90,108.83) 0.6 mm further on. C103.2 has a via 0.6 mm away. |
| M2b U1.99 | NOT FIXED | U1.99 is on a 0.8 mm² F.Cu sliver with 0 vias, and still 8.4 mm by track to via (209.47,90.78). C105.2 has a via 0.67 mm away (B.Cu), so VDD100 decoupling is fine; only the pin's own return is long. |
| M2c U1.27 / C102.2 | NOT FIXED (minor) | They share a 2.5 mm² sliver with 0 vias, 3.9 mm by track to via (213.30,108.72). Free 0.45/0.2 site at (217.48,108.8), inside the sliver. |
| M3 D+ ESD T-stub | NOT FIXED (accepted) | Copper is identical to r1: F 9.4 mm, B 12.2 mm, 3 vias; U4.3/4 still hang off via (231.18,99.23). OK at full speed. |
| M4 decap and plane ties | MOSTLY FIXED | Track distance to the nearest In2 via: VBAT6 1.2 mm (r1 6.0); VDDUSB73 2.0 mm (8.4); VDD75 0.8 mm (5.5); VDDA22 1.4 mm; VREF+21 1.0 mm. C104.1/C106.1/C108.1 each have a via within 0.6-0.7 mm. C109-C112 GND vias are 0.6-1.8 mm away (r1 6.5-8.4). VDD11 is unchanged: 6.2 mm to a via, 8.2 mm to C108. |
| m1 crystals | PARTLY | OSC32_OUT is 5.5 mm, 1 via (r1 7.7). OSC_IN (11.2 mm), OSC_OUT and OSC32_IN (9.0 mm) are unchanged and still cross the In2 GND island edge at x=215. Workable. |
| m2 In2 GND island | FIXED | 4 vias: (217.6,94.9), (219.88,94.9), (220.18,93.6), (220.18,98.3). |
| m3 USB pair for U5A5 HS | NOT FIXED (deferred) | Same skew and vias. Record it as a U5A5 respin item. |
| m4 NRST / C114 | NOT FIXED (accepted) | C114 is still 8.0 mm by copper from pin 14. |
| m5 BOM fields | PARTLY | The PCB still lacks `LCSC Part` on 33 island footprints, and U2 is C2070694 on the PCB vs C130072 in the schematic (DRC parity). But `jlcpcb/production_files/BOM` (09:44) has every part with an LCSC number, U1 C5270999 and U2 C130072. Order from that BOM. |
| m6 J5 pin-1 / shroud | NOT FIXED | Not addressed in r2. |
| i1 radio supply vias | NOT FIXED (inherited) | Single 0.56/0.3 vias at (239.22,100.83), (239.99,109.02), (211.70,115.70), (208.44,116.55) and (206.94,113.30; one parallel at 114.9). Same as V2, which works. |
| i2 dangling VBUS via | NOT FIXED | Still at (240.68,108.27). Harmless. |
| i3 F.Cu under E22 / i4 VBUS 100 nF | NOT FIXED (inherited) | No change. |

## 2. New or remaining findings
- **N1 (should-fix, about 10 minutes): two cheap GND vias that the maze tool missed because it only tried 0.6/0.3.**
  - Add a 0.45/0.2 GND via at **(234.50,99.11)**. It lands inside the U4.2 F.Cu sliver and ties the USBLC6 ground to In1 and B.Cu within about 1.7 mm (closes M1).
  - Add a 0.45/0.2 GND via at **(217.48,108.80)**. It lands inside the U1.27/C102.2 sliver.
  - Both spots clear 0.15 mm copper and 0.5 mm hole-to-hole by grid probe, and both sizes are within the project's JLC rules (min 0.4/0.2). Rerun DRC after adding them.
  - Optional: a 0.45/0.2 GND via at about (215.90,89.83) for U1.99, with a 0.2 mm stub over the toe of pin 100. Routing is not proven, so drop it if DRC complains.
- **N2 (nit): CPL rotations.** U1 is at 270° and U4/U19 (SOT-23-6) are on KiCad rotations. Check pin 1 of U1, U4, U2, U19, Y101 and J12 in the JLC placement preview before paying. A wrong LQFP rotation is the one PCBA error that would stop the board booting.
- **N3 (nit):** four parity `footprint_symbol_mismatch` items on H1-H4 (BOM exclude flag). Cosmetic; H1-H4 are not in the BOM.

Nothing new is a blocker. The r2 changes introduced no shorts, no plane splits and no net changes (only 36 vias added and 1 OSC32_OUT via removed vs r1).

## 3. Go / no-go
**GO** for 5 prototype boards at JLCPCB tomorrow, using `jlcpcb/production_files` regenerated after N1 (or as-is if N1 is skipped).
- Bring-up risks that remain, none fatal:
  - ESD clamp ground inductance (M1, if N1 is skipped).
  - Long return on the VDD11 and VSS99 pins (expect slightly more MCU noise, not a failure).
  - Inherited E22 TX supply vias at about 2x current margin.
- Not for a flight build or the U5A5 (HS USB) until M3/m3 and i1 are reworked.
- Sources: measurements on the board only. The datasheet references in r1 still apply (USBLC6-2 §2.3; AN5373/AN2867 from memory).
