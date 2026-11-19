# V3 against proves-pcb-design and Greenberg "Useful Schematics" (2026-10-31)

Goal: check the V3 stick against the proves-pcb-design skill and Greenberg's style guide (Greenberg wins where they differ). Fix whatever keeps the netlist identical. List the rest with a reason.
Evidence: `kicad-cli sch erc`, `pcb drc --schematic-parity`, the skill's `sch_lint.py` and `erc_summary.py`, a netlist diff by pin membership, and renders.

## Gates, before and after

| Gate | Before | After |
|---|---|---|
| Netlist nets (name + pin set) | baseline | identical. The 28 component diffs are all Value or MPN fields |
| ERC | 0 errors, 223 warnings (72 footprint_link, 151 lib_symbol) | the same |
| `sch_lint.py` | 78 errors (instance project names, file format 20250114) | 0 errors. 1 warning: GND_1 is used through `lib_name`, which the lint does not see |
| DRC | 0 errors, 0 unconnected, 72 lib + 1 starved thermal | the same |
| DRC schematic parity | 90 notes (mostly missing LCSC field) | 59 (pins named unconnected-*, DNP attributes) |
| Copper (Gerbers) | | unchanged apart from the date header |

## Fixed

| Rule | Change |
|---|---|
| Instances name this project | 77 symbols copied from V2 or the FC said `proves_radio_stick_V2`, `FC_V5` or nothing |
| KiCad 10 files | sheet upgraded to format 20260306 |
| Greenberg 2: rails up, GND down | 5 power symbols turned upright: VREF+/VREF-, J5 +3V3/GND, J12 GND |
| Greenberg checklist: power by supply symbols | RF_VCC is a project power symbol (`symbols/proves_power.kicad_sym`) instead of 2 global labels. The net name is unchanged |
| Every part has a value, with units | 100n, 4.7u, 1u, 12p and 10p become 100nF, 4.7uF, 1uF, 12pF and 10pF (19 parts). The BOM merges 2 lines (36 to 34), with the same LCSC parts |
| Connector Value = function | J2 "SMA antenna", J3 "J3 breakout", J12 "USB-C (USB 2.0)", J22 "SWD (JST-SH)" |
| MPN on connectors and ICs | J2, J5, J12, J22, U1, U2, U4, U19. MPN and LCSC Part also copied onto the footprints |
| Greenberg 11: rail ranges | VBUS (4.75, 5.0, 5.25) V @ (0.02, 0.1, 0.8) A; +3V3 (3.25, 3.32, 3.39) V @ (0.005, 0.04, 0.15) A; RF_VCC (4.7, 5.0, 5.25) V @ (0.005, 0.1, 0.65) A |
| Stackup metadata JLC04161H-7628 | In2 changed from 1 oz to 0.5 oz to match In1; finish set to ENIG |
| Personality silk stays | V2's "1 2 3 4 5 6 7 . . . How many more days until the weekend?" was deleted with the RP2350 island. It is restored under the E22, at 0.8 mm |
| Silk: order date, JLC number | "C. Oct 30, 2026"; "JLCJLCJLCJLC" placeholder on the back |
| Refdes on connectors | J3, J5 and J12 shown; U4 hidden (passive-like part, its ref overlapped J12's) |

## Left as is

| Rule | Why | When |
|---|---|---|
| Greenberg 6, 7, 9: wires, not labels; global labels only off-sheet | One flat sheet with 33 global labels. Local labels rename every net to `/NAME`, and drawing wires means rebuilding most of the sheet | next schematic rewrite |
| Greenberg 3: functional symbols | U1 is KiCad's stock STM32 symbol (pins grouped by port); U3 is the V2 E22 symbol | next rewrite, with a project library |
| Greenberg 2 at R95 | R95's +3V3 hangs below the resistor. Turned upright, it sits inside R95's body. Needs R95 redrawn above the ON line | next rewrite |
| Readability | C1 and C3 are +3V3 bulk caps, but they are drawn in the radio block (inherited from V2) | next rewrite |
| Vias 0.20 mm from SMD pads | 64 vias are closer than that (V2 has 61). The board uses tented vias. Moving them means re-running the plane ties | next spin |
| Crystal within 5 mm; ESD on every student connector; test points on rails and resets | Already deferred in the layout reviews (HSE/LSE 9-11 mm, J3 has no ESD, no TPs) | next spin |
| Single-sided assembly | No room: the island's passives sit inside the LQFP shadow on the back | accepted |
| Off at boot (100k pull-down on enables) | RF_PWR_EN has a 10k pull-up, so the radio is on by default, as on V2 (DECISIONS rows 4 and 14). The stick is not a spacecraft load | accepted |
| Board name in exposed copper | The free area on the back is a GND via field | next spin |
| J2 and J22 refdes | No room inside the board edge next to them | accepted |
| `jlcpcb/project.db` is what gets ordered | V3's BOM and CPL come from `tools/jlc_export.py`, not the Bouni plugin. Load them in the plugin if that is the house flow | Michael |
| Order settings | Add 4-wire Kelvin test and solvent cleaning, and no conformal coat, to the JLC order | Michael, at order |
