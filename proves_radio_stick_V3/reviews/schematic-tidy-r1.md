# V3 schematic tidy: design note (2026-10-30)

Before: /tmp/claude-0/-home-claude/674b3aef-f740-5b2a-bc1d-98dbdf2f1ed2/scratchpad/work/sch_tidy_before.png (and sch_r2-1.png)
After:  /tmp/claude-0/-home-claude/674b3aef-f740-5b2a-bc1d-98dbdf2f1ed2/scratchpad/work/sch_tidy_after.png (2481 px wide)

## Critique of the generated sheet
- No reading order. The power parts sat top right, USB-C bottom left and the MCU support parts top left.
  J3 sat on top of the title block. The headings were loose text with no frames, and some of them
  ("User LED", "J3 I2C3 pull-ups") overlapped labels.
- The decoupling note ran into the MCU's VREF pins. The VREF+ "+3V3" was printed sideways across ~RESET.
  The SW1, Y101, R27 and D2 reference/value fields overlapped other fields or wires.
  The USB_D- label stood across the CC2 wire.
- Stray V2 leftovers: a filled circle graphic inside the MCU body and a junction on nothing at (269.24, 186.69).
- Old title block date (2026-09-26). The "Antenna / ESD" heading named an ESD part that does not exist.

## What changed (new step 1b: tools/tidy_v3_schematic.py, after gen_v3_schematic.py)
- Stays one flat A3 sheet. A2 was not needed once the blocks were packed.
- Top row, left to right: 1 USB-C input + ESD, 2 3.3 V buck, 3 radio 5 V switch, 7 debug (at the edge).
  Main row: 4 MCU support (decoupling, HSE, LSE, BOOT0, user button), 5 MCU, 6 radio + antenna,
  then 8 J3 breakout, 9 reset/LEDs and 10 mounting at the right edge.
- Each block has a numbered, titled dashed frame and short notes covering:
  - each part's job and the reasoning behind key choices: CC thresholds; 30 dBm needs a 1.5 A USB-C host;
    Vout = 3.32 V from R4/R3; the U19 ramp and the R95 default
  - firmware hints: BOOT0 DFU; PC13/WKUP2 can wake the MCU from Standby; RXEN/TXEN pull-downs;
    R14/R15 DNP and why
  - the J3 note: 3.3 V logic only; IO3/IO4 = I2C3, IO5-8 = SPI2
  - the RF_ANT microstrip spec, the LQFP-100 flight-part and no-Q-suffix rule, and where the pin map lives
- Title block: date 2026-10-30, rev 3.0, company "PROVES Kit / Open Source Space Foundation", and three comment lines.
- Fixes: field touch-ups (Y101, Y102, SW1, SW3, SW2, D2, R26, R27 and the VREF+ power value);
  R26/R27 fields shrunk to the sheet's 1.27 mm; LSE load caps lowered 5.08 mm;
  USB_D-/USB_D+ labels turned to read sideways at the same connection point;
  the stray circle and junction removed.
- Method: the script finds every drawing cluster by union-find over shared points (wire ends, points on
  wires, pins, labels, junctions, no-connects). It moves each cluster rigidly by a whole number of
  1.27 mm steps, so no connection can break. It exits if a cluster spans two blocks. Symbol UUIDs are
  unchanged (153/153 identical). The script refuses to run twice on the same file.
  It writes a marker text, "Sheet layout: tools/tidy_v3_schematic.py", in the free strip left of the title block.
- tools/README.md has a new step 1b. The generator, PCB and jlcpcb/ are untouched. Nothing is committed.

## Verification
- netcmp.py net_before.xml net_after.xml: IDENTICAL
- ERC: 0 errors, 223 warnings, the same as before. The categories are unchanged
  (151 lib_symbol_issues, 72 footprint_link_issues; both come from the container's missing library tables).

## Known limits / electrical concerns
- No electrical errors found. The tidy exposed no unconnected or merged nets.
- The note text widths are estimated, so some frames have spare room on the right.
  The USB_CC1_SENSE label still points up past J12.
- Re-running gen_v3_schematic.py makes new symbol UUIDs (uuid4). That was already true before this work.
  After any regeneration, run tidy again and then re-sync the PCB.
