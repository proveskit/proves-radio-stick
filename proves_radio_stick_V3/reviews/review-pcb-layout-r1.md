# Radio Stick V3: PCB layout review r1 (layout craft and manufacturability)

Reviewer role: principal PCB layout engineer. Board: `$REPO/proves_radio_stick_V3/proves_radio_stick_V3.kicad_pcb` as of 08:54Z.
Method: pcbnew Python (KiCad 10 container) dumped every pad, track, via and zone fill. Shapely then measured copper paths, pad-to-via distances, plane voids and legal via sites. The legal-site check uses 0.6/0.3 vias, 0.15 mm clearance to other-net copper on all layers, hole-to-hole 0.5 mm and at least 0.1 mm from same-net SMD pads. DRC rerun: 0 unconnected, 0 errors, 203 warnings (72 lib, 64 silk overlap, 62 silk over copper, 3 text height, 2 starved thermal). Scripts are in `scratchpad/pr/`. No repo file was edited.
Overall: the board can be fabricated and DRC is clean. However, three ground-return problems at the MCU, plus the HSE routing, are not up to the standard a human layout engineer would sign off. Each fix is local and small.

## Island findings

### Blocker
**B1. VSS pins 49 and 99 have no local ground. The VCAP and VDD50/VDD100 decoupling loops return through 7-10 mm of 0.2 mm track.**
- U1.49 (227.7, 106.525) is not in any pour. Its only copper is a 0.2 mm F.Cu track: (227.98,105.46) -> (230.54,105.46) -> (233.32,102.68) -> (236.46,102.68) -> J12 A1/B12 (237.435,102.14), about 10.9 mm long, with no via. Shortest pin-to-plane-via path: 8.9 mm.
- The same track is the return for C113 (VCAP, 4.7 u) and C103 (VDD50). Root cause: C113 sits at 180°, so its GND pad (226.97) is under pin 48 (VCAP, x 227.20) and its VCAP pad (227.93) is under pin 49 (GND, x 227.70). The two connections cross, so the router could not tie pin 49 to C113.2. C113.2 itself reaches a via only through 7.3 mm of F.Cu pour.
- U1.99 (216.7, 91.175) is also outside the pour. Its 0.2 mm track runs (216.7,90.35) -> (210.70,90.03) -> via (209.48,90.58), 6.95 mm of track. Pin 100's +3V3 via is 0.9 mm away, but the GND side of that loop is 8.3 mm.
- Fix, pin 49: rotate C113 to 0° (VCAP pad at x 226.97 under pin 48, GND pad at 227.93 under pin 49). Run a 0.3 mm track from pin 49 straight down to C113.2, and add a GND via at (227.9, 109.0) (checked legal). Then delete the 10.9 mm track to J12.
- Fix, pin 99: today there is no legal via site within 1.6 mm. Move RF1_IO1's F.Cu jog at (217.50,88.09)-(218.70,91.18) to B.Cu (it has vias already). Then run pin 99 straight up 0.6 mm to a new GND via at about (216.9, 89.9), or tie it to SW2 B' GND (218.35, 89.32), which already links to SW3 A'. Rerun DRC after.

### Major
**M1. VDD 11, VDD 73/75 and VBAT 6 are 5.5-8.6 mm from their caps (path lengths measured along copper):**

| pin | to first plane via | to its cap | cap GND to via |
|---|---|---|---|
| 11 VDD (214.525,97.85) | 6.3 mm, via (220.42,96.90) | C108 8.56 mm | 1.75 mm |
| 75 VDD | 5.5 mm, via (224.75,93.88) | C106 7.7 mm / C104 8.7 mm | 1.5 / 2.6 mm |
| 73 VDDUSB | 8.4 mm (via pin 75's loop outside the toes) | C106 10.6 mm | 1.5 mm |
| 6 VBAT | 6.0 mm, via (208.8,96.0) | no cap | - |
| 100 / 28 / 50 / 48 VCAP | 0.9 / 5.5 / none / none | C105 3.3 / C102 1.45 / C103 1.97 / C113 1.98 mm | 2.5 / 6.1 / 4.5 / 7.3 mm |
| 21-22 VREF+/VDDA | 2.1-2.6 mm, via (216.31,102.05) | C111 4.5 / C112 5.7 mm | 6.5-8.4 mm |

- Pins 73/75: the F.Cu +3V3 track at y = 92.85 already passes directly over C104 (B.Cu, 226.92-227.88, 92.9). Add a +3V3 via at (226.22, 92.9) (legal) with a 0.5 mm B.Cu stub to C104.1. That cuts pin 75 to C104 from 8.7 to about 4 mm.
- Pin 11: add a +3V3 via at (215.9, 97.35) (legal, just inside the pad heel) and move C108 next to it on B.Cu, at about (215.9, 96.6) vertical. Otherwise the loop stays at 8.6 mm.
- VDDA/VREF caps C109-C112: their GND pads (y 102.92) reach a via only through 6.5-8.4 mm of B.Cu pour. Add GND vias at (218.2, 102.2) and (219.4, 102.2) (both legal, between the cap rows).
- Pin 50/C103 has no +3V3 plane via; it is fed by about 9 mm of F.Cu track from C14. Add a via at (229.1, 107.0) (legal).

**M2. HSE and LSE traces are long, run on F.Cu, and run beside NRST.** Measured routed lengths:
- OSC_IN: 11.25 mm (F 5.9 / B 5.3, 2 vias). OSC_OUT: 10.5 mm (1 via). OSC32_IN: 9.0 mm. OSC32_OUT: 7.6 mm. AN2867 guidance is to keep these as short as possible, and a few mm is typical for this package.
- OSC_IN leaves pin 12 outward to a via at (212.78, 98.26) outside the LQFP, then comes back on B.Cu. That is a Freerouting detour. Its load cap C115 hangs off a second 3.6 mm F.Cu branch to a via at (218.51, 97.95).
- On F.Cu, OSC_IN (y 98.35) and OSC_OUT (y 98.85) run 3.6-4.1 mm at 0.3 mm gap beside +3V3 (97.85) and NRST (99.35). In total, 4.4 mm of NRST, 3.2 mm of USER_BTN and 3.0 mm of +3V3 lie within 0.6 mm of the oscillator copper. The extra roughly 1.5-2 pF of stray capacitance also eats into the 12 p / 10 p load-cap budget.
- The via OSC_IN (218.505, 97.952) sits 0.155 mm from Y101 pad 3 (OSC_OUT). That couples input to output.
- Fix: place Y101 so pads 1/3 face pins 12/13 at about (215.9, 98.6), with vias at the pad heels (x ≈ 215.6). Join C115/C116 to the crystal pads on B.Cu (not through a second via), and delete the outward vias at 212.78 and 213.24. Target 3-4 mm per net, with no F.Cu run longer than 1 mm. Do the same for Y102 / OSC32 (pins 8/9).

**M3. The In2 GND island under the crystals is tied to ground by one via.**
- The island is 38.2 mm² (215.0-220.3 x 93.3-101.0). Its only GND via is (217.6, 94.9). Three OSC vias and the +3V3 via at (220.42, 96.90) punch antipads through it. Y101's GND pads reach a via through 3.0 / 5.5 mm of pour.
- OSC_IN and OSC32_IN each cross the island edge on B.Cu, going out over +3V3 to the outward vias in M2. They are the only signals that cross from the island to the +3V3 plane. No other B.Cu track crosses the island edge. The In2 VBUS track (241.07, 100.8-109.0) runs under no island signal (checked).
- Fix: add GND stitching vias at (215.8,94.7), (215.9,97.2), (217.0,97.2), (218.4,93.5), (218.4,95.0) and (219.9,97.6). All six are checked legal today. Once M2 is fixed, both crossings go away.

**M4. U4 (USBLC6) GND pin 2 is a starved thermal: one spoke, no via.** DRC flags it (233.3, 97.86). Pad-to-via path: none; the pin connects only through one F.Cu spoke. That is the ESD discharge path.
- No legal via site exists within 2.5 mm, because USER_LED (U1.63 -> R103) snakes 12 mm through the USB area: (230.97,97.97) -> (233.17,96.58) -> (234.81,95.06) -> (236.16,93.71) -> R103.
- Fix: reroute USER_LED on B.Cu north of J5, or swap it to a top-row pin. Then add a GND via at (233.3, 96.6) with a 0.3 mm stub to U4.2.

**M5. USB D+/D- (needed for the U5A5 HS upgrade; acceptable for FS):**
- Lengths: D+ 21.57 mm (F 9.4 / B 12.2, 3 vias); D- 15.50 mm (F 13.7 / B 1.8, 2 vias). Skew 6.1 mm, about 40 ps.
- The pair is not coupled. D+ runs on B.Cu, referenced to the In2 +3V3 plane; D- runs on F.Cu over In1 GND.
- U4 is a tee stub on D+: the F.Cu branch from via (231.18,99.23) to pins 3/4 is about 2.1-2.5 mm. D- flows through pins 1/6 correctly.
- D- drops to B.Cu (234.26,95.02)-(234.38,96.73) only to hop USER_LED. That hop is needless.
- No plane splits: the only "voids" under the pair are the antipads at their own vias.
- Fix: after the M4 reroute, route D+/D- as a coupled F.Cu pair (0.25 / 0.15 mm, or recompute for 90 Ω on JLC04161H-7628) over In1. Pass U4 flow-through (in at pins 1/3, out at 6/4). Use at most 2 vias per net and match length within 0.5 mm.

**M6. Bottom silk in the island cannot be read.**
- 64 silk-overlap and 62 silk-over-copper warnings. Most are in the island.
- V2's B.SilkS lyric text "1 2 3 4 5 6 7 . . . How many more days..." at (215.5, 101.0) (line 25598 of the .kicad_pcb) runs across Y101, C101, C107 and C114-C116.
- The C109-C112, C115-C118, R101/R102 and Y102 reference labels all sit on top of each other or on pads. On top, the C102 and C103 references sit on U1 pins 26-32 and 49-50. JLC clips silk off pads, so these labels will be unreadable.
- Fix: move the lyric text off the island (for example to 175-200 x 104-110 on B.Silk, which is clear). Set island B.Silk references to 0.6 mm / 0.1 mm stroke and place them outside the 0402 pads, or hide them and ship an assembly drawing. Move the C102 and C103 references below the caps (y about 109.2).

### Minor
- m1. Vias near SMD pads (all vias are tented both sides, so wicking risk is low):
  - VBUS via (233.3, 101.14), 0.04 mm from U4.5.
  - D- via (234.38, 96.73), 0.17 mm from U4.1.
  - D3-A via (224.22, 109.58), 0.13 mm from D3.2.
  - SWO via (230.25, 92.22), 0.18 mm from U1.75.
  - Fix: pull the VBUS via 0.3 mm out to (233.3, 101.45).
- m2. Fiducials: there are none on the board. JLC can place a 0.5 mm-pitch LQFP without them using rail fiducials, but local fiducials help double-sided placement. Add two 1 mm global fiducials per side if space allows (top: about (212, 91) and (231, 107); bottom: matching spots clear of the island). Check them with the legal-site script.
- m3. Test access:
  - 3V3 and GND: J5 pins 3/5/7/11 (THT).
  - VCAP: only C113's 0402 pad, so add a 1 mm TP pad on VCAP near (226.5, 109.3).
  - RF_VCC: only C4 (B.Cu, 1210) and the U19 pins.
  - TP1-TP7 are V2 SPI/RF test points and are DNP.
- m4. J5 STDC14 (pin 1 now at (234.19, 93.41)):
  - Measured: J5 courtyard 231.31-235.81 x 84.61-94.59; J12 courtyard starts at x 236.16; D1 at x 236.43; R27 spans y 94.64-96.59 directly beside it; the board top edge is y 84.25.
  - The ST STDC14 cable plug (Samtec FFSD-07 class, about 12.4 x 5 mm, **from memory, not measured**) centred on the pin field would span roughly x 231.1-236.1 and y 83.4-95.8. That leaves about 0.1 mm to J12's courtyard and puts R27 under the plug. The plug overhangs the top edge, which is fine.
  - The footprint is an unshrouded, unkeyed 2x7 header (BOM C22438122, not verified), so the cable can be plugged in reversed. Reversed, target 3V3 (pin 3) lands on the probe's NRST pin (12).
  - Fix: use a keyed shrouded 1.27 mm 2x7 header if JLC stocks one, or add a pin-1 triangle and "KEY" silk. Confirm the plug against J12 with a real STLINK-V3 cable before ordering.
- m5. Acid traps / slivers: no junction under 45° in the island. 45° junctions at pin 50 (+3V3) and at the D+ via (231.18, 99.23) are fine for JLC. There is a 1.1 mm² F.Cu GND fill fragment at U1.27 with no via; delete it or give it a via (C102 GND is better fixed by a via near (217.9, 110.5), which is legal).
- m6. Thermal reliefs:
  - The island F.Cu GND zone uses 0.25 mm gap and 0.3 mm spokes. That is fine for 0402 parts.
  - J5.3 (+3V3 on In2) is starved (one spoke); acceptable for a sense pin.
  - The VSS pins cannot get pour at all between 0.5 mm-pitch pins, which is why B1 needs explicit tracks and vias.
- m7. Freerouting artifacts a human would redo:
  - The outward crystal vias (M2).
  - The D- hop (M5).
  - USER_LED's 12 mm path through the USB area (M4).
  - /LED2_A is 6.5 mm for a 3.3 mm gap.
  - 35 segments under 0.05 mm long.
  - Elsewhere detour ratios are 1.1-1.7, which is acceptable.
- m8. Assembly: no courtyard overlaps (DRC). R80 (B) sits directly under D3 (F), which is fine. The bottom island parts are all 0402 plus two crystals, which suits a two-sided JLC Standard PCBA (bottom reflowed first). The island PCB footprints carry no LCSC field, but the BOM CSV has them (U1 C5270999, Y101 C13738, Y102 C97604, U4 C7519, J5 C22438122). Keep the BOM as the source for JLC.

## Inherited (V2) findings
- I1. V2 bottom lyric text over the island (see M6). It is inherited, but it now covers island parts, so moving it is island scope.
- I2. Vias in pad on U3 GND pads 11/12 (209.48, 87.95 / 89.55 / 111.95 / 113.55), C4 pads (209.89, 114.5; 206.94, 113.3 / 114.9), C80.2 and FB1.2. They are tented, so there is some solder-wicking risk on the E22 GND pads and the 1210. JLC will accept them; consider plugged/filled vias (POFV) if voiding matters.
- I3. The In2 VBUS track (0.4 mm) cuts the +3V3 plane from (239.22,100.83) to (241.07,102.68)-(241.07,107.99). One B.Cu +3V3 segment, (240.37,105.95)-(242.41,108.00), crosses the slot (1.27 mm over void). No island signal crosses it.
- I4. Duplicated or backtracking segments (0° junctions) on VBUS around (240.33, 108.6) and on U2-FB around (241.2-241.5, 105.2-107.0). These are harmless but untidy.
- I5. SW1-SW3 reference text is under the 0.8 mm minimum (3 text_height warnings), and the SW2/SW3 references sit on switch pads.

## Suggested order of work (about 1-2 h)
1. B1: rotate C113 and add the pin 49 via; reroute RF1_IO1 and add the pin 99 via.
2. M4: reroute USER_LED, then the U4 GND via.
3. M5: reroute D+/D- as a coupled pair.
4. M2 + M3: rework the crystal fanout and add the island stitching vias.
5. M1: add vias at (226.22,92.9), (215.9,97.35), (218.2,102.2), (219.4,102.2) and (229.1,107.0).
6. M6: silk cleanup.
7. Rerun DRC, then rerun this measurement script to confirm each pad-to-via path is under 2 mm.
