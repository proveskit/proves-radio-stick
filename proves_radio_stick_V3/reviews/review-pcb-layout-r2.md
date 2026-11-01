# Radio Stick V3: PCB layout review r2 (commit 5e7e67e)

Method: I ran DRC on the repo board with the project rules (`kicad-cli pcb drc --severity-all --schematic-parity`, output in `drc_r2rev.json`). Result: **0 errors, 0 unconnected**, 104 warnings (72 lib, 23 silk overlap, 5 silk over copper, 3 text height, 1 starved thermal), plus 90 parity notes. Note: DRC on the bare `$W/r2.kicad_pcb` without the .kicad_pro reports 194 false "clearance" errors, so always run it from the repo folder. I measured pads, vias, track walks and zone-fill fragments with pcbnew (scripts `$W/m2.py` to `m6.py`). Nothing was edited.

## 1. Round-1 findings
| # | Status | Evidence |
|---|---|---|
| B1 pin 49 | FIXED | 0.3 mm F.Cu from pin 49 to C113.2, then GND via (227.90,108.83): about 2.3 mm to the plane. Pin 49 and C113.2 sit in the 315 mm² F.Cu GND pour, which has 18 vias. VCAP is now 1.78 mm, all on F.Cu. The old J12 track remains as a 7.4 mm dead-end stub, see N3. |
| B1 pin 99 | NOT FIXED | Its "solid" pour connection is a 0.78 mm² F.Cu fragment with no via. The return is still the 0.2 mm track (216.7,91.17)->(216.38,90.03)->(210.15,90.58)->U3.12 track->via (209.48,89.55), about 8 mm. |
| M1 VDD/VCAP loops | PARTLY | Fixed: C104/C106 +3V3 vias (226.32,92.9/94.1); pin 73 to its via is 4.0 mm (was 8.4); pin 75 has a via 1.1 mm away (230.97,92.75); pin 50 via (228.70,106.53) is 0.5 mm away; C109-C112 GND vias (217.0,102.62), (218.8,102.32), (220.0,102.32) are 0.6 mm away (were 6.5-8.4 mm). Not fixed: pin 11 is still 6.3 mm to via (220.42,96.90), and C108 has not moved. Pin 28 is 3.0 mm. C102.2 / U1.27 GND reach a via only through 9.0 / 4.8 mm of track to (213.3,108.72). |
| M2 HSE/LSE | PARTLY | OSC32_OUT went from 7.6 to 5.5 mm. OSC_IN 11.25 (F 5.9), OSC_OUT 10.5 and OSC32_IN 9.0 mm are unchanged. The OSC_IN via (218.505,97.95) is still 0.155 mm from Y101.3 (OSC_OUT), and the outward via (212.78,98.26) is still there. |
| M3 In2 island | PARTLY | The In2 GND island (215-220.3 x 93.3-101) now has 4 GND vias instead of 1: (217.6,94.9), (219.88,94.9), (220.18,93.6), (220.18,98.3). The OSC_IN/OSC32_IN crossings are unchanged. |
| M4 U4 GND | PARTLY | The pad is now solid (the starved-thermal flag is gone). It sits in a 3.2 mm² F.Cu fragment with no via. Its 0.2 mm track runs (233.3,97.86)->(234.15,96.1). USER_LED is still 11.96 mm and snakes through the USB area. |
| M5 USB pair | NOT FIXED (deferred) | Unchanged: D+ 21.57 mm (3 vias), D- 15.50 mm (2 vias), skew 6.1 mm. The U4 tee stub and the D- hop remain. FS is fine. |
| M6 silk | FIXED (island) | Silk overlap went from 64 to 23 and silk over copper from 62 to 5. The lyric text is gone and the island references are hidden. All 23 remaining overlaps are on J3/SW/D2, and the J3 labels are a new problem (N1). |
| m1 via near pad | NOT FIXED | VBUS via (233.30,101.14) is still 0.038 mm from U4.5. See N2 for the new vias. |
| m2 fiducials, m3 test points | NOT FIXED (deferred) | None on the board. JLC rail fiducials cover a 5-board run. |
| m4 J5 keying | NOT FIXED | Still an unshrouded 2x7 header. |
| m5 sliver | NOT FIXED | The U1.27 fragment grew to 2.54 mm² and still has no via. |
| m6 J5.3 thermal | NOT FIXED | 1 starved_thermal warning (J5.3 +3V3 on In2). Acceptable. |
| m7 router artifacts | NOT FIXED | 39 segments shorter than 0.05 mm (was 35), and 2 exact duplicate segments. Duplicate pairs also sit at pin 49/C113 and U1.27. Harmless. |
| I1-I5 | I1 FIXED | I5 still has 3 text_height warnings (SW1-SW3 refs) and the SW2/SW3 refs still sit on pads. I2-I4 were not re-measured; nothing in the brief touched them. |

## 2. New findings
- **N1 should-fix: the new J3 pin-name silk cannot be read** (render `$W/r2_j3silk.png`). 11 overlap warnings at y 116.4:
  - The PA4/PC3/PC2/PB13/PC1/PC0/PA1/PA0 labels overlap each other and the V2 label-grid dividers.
  - "J3: 3.3 V LOGIC ONLY" (226.0,110.8) runs over the top silk line of J3.
  - Fix (10 min): use 0.8 mm height / 0.55 mm width / 0.12 mm stroke so 3-4 characters fit the 2.54 mm cells. Otherwise drop the "P" (A0, C1, B13), or rotate the labels 90°. Delete the old dividers and move the warning text to y ≈ 109.8.
- **N2 nit: about 25 new plane vias sit tangent to their pads** (0.001-0.02 mm edge gap), for example C109-C113, U1.21 at (215.625,102.95) and U1.75 at (230.975,92.75). The board is tented both sides and has no solder_mask_bridge errors. The hole edge is still 0.15 mm from the pad, so wicking risk is low. In the JLC order, keep "tented vias". Do not choose "via opening".
- **N3 nit: dead-end GND stub.** The old pin-49 track J12 A1/B12 -> (233.32,102.68) -> (230.54,105.46) -> (227.97,105.46) now ends under U1 at 7.4 mm from J12, with no load. Delete it.
- **N4 nit: "solid" GND on pins 99 and 27, U4.2 and C102.2 only reaches via-less pour slivers** (0.78 / 2.54 / 3.21 mm²). The ground return is unchanged. The full-copper pads also add a small tombstone risk on 0402 C102 (one pad solid, the other on a track). Either give each sliver a via or revert to thermal.
- **N5 nit: 90 parity notes, all benign:**
  - 53 unconnected-pin nets.
  - 33 footprints missing the "LCSC Part" field.
  - 4 H1-H4 exclude-from-BOM mismatches.
  - If the JLC BOM/CPL comes from the footprints (the KiCad JLC plugin), the island has no LCSC numbers. Use `v3_bom_r1.csv`, or run Update PCB from Schematic first.

## 3. Go / no-go for 5 prototype boards at JLC tomorrow: **GO, no blockers**
1. (should-fix, 10 min, do before ordering) N1: J3 silk is the only operator-facing label for the 3.3 V-only header.
2. (should-fix, accept for the proto) B1 pin 99, about 8 mm of 0.2 mm GND track. Pin 49 is now correct, and the other three VSS pins plus VSSA have returns. Expect only extra ground bounce, not a failure. Fix it in the next spin with the RF1_IO1 move from r1.
3. (should-fix, accept) M2 crystal routing. Check HSE/LSE start-up and ppm on the bench, and keep the 12 p / 10 p load caps as tunable 0402s.
4. (minor) M4 U4 GND via, M1 pin 11 / C102 loops, and M3 crossings: all ESD/EMI margin, not function.
5. (minor) M5 USB: FS only. Record it as a blocker for a U5A5 HS build.
6. (order settings) Two-sided PCBA, tented vias, BOM from the CSV. Ask JLC for rail fiducials. Probe 3V3/VCAP at C113/J5 since there are no test points.
7. (cleanup) N3 stub, N4 slivers, duplicate segments, SW text height, J5 keying silk.
