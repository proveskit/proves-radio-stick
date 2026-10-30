# V3 build tools

Everything here runs with KiCad 10's Python (`pcbnew`) and `kicad-cli`, for example in
the `kicad/kicad:10.0` container. Freerouting 2.1.0 (`freerouting.jar`) and a JDK are
needed for the routing step.

| Step | Command (from `proves_radio_stick_V3/`) | What it does |
|---|---|---|
| 1. Schematic | `python3 tools/gen_v3_schematic.py` | Builds the V3 schematic from V2: MCU block, decoupling, crystals, buttons, STDC14, USB ESD, LEDs, pull-ups |
| 1b. Sheet layout | `python3 tools/tidy_v3_schematic.py` | Moves each block to its place on the A3 sheet (power row on top, then MCU support, MCU, radio, connectors), draws titled frames, adds design notes and fills the title block. Moves whole connected clusters only, keeps every UUID and net; refuses to run twice. Check: the `kicad-cli sch export netlist` output must not change |
| 2. Netlist | `kicad-cli sch export netlist --format kicadxml -o v3.net.xml proves_radio_stick_V3.kicad_sch` | |
| 3. Sync + place | start from V2's board, then `cd tools && python3 sync_v3_pcb.py ../v3.net.xml` | "Update PCB from schematic", clears the RP2350 island, places parts from `v3_placement.py` |
| 4. Prep | `kicad-cli pcb drc --format json -o drc0.json proves_radio_stick_V3.kicad_pcb` then `python3 tools/route_v3.py prep drc0.json <V2 board>` | Drops dangling V2 stubs, restores V2's VBUS run, pre-routes U4's VBUS feed, adds island pours, locks power/RF copper |
| 5. DSN | `python3 tools/route_v3.py dsn v3.dsn` | Specctra export without the outer pours, plus a via-to-via clearance rule |
| 6. Route | `javac -proc:none -cp freerouting.jar tools/FreeroutingHeadless.java` then `java -cp freerouting.jar:tools FreeroutingHeadless v3.dsn v3.ses 80 [via_cost ripup_cost]` | Freerouting's batch router with the inner planes closed to tracks; keeps the pass with the fewest open connections. Results vary run to run: try a few cost pairs (50 100, 20 100, 50 300, 30 60) and keep the best |
| 7. Import | `python3 tools/route_v3.py ses v3.ses && python3 tools/route_v3.py finish` | Imports the session, spreads vias to the 0.5 mm hole rule, adds GND stitching (and a via in every GND fragment), refills |
| 8. Close | DRC to JSON, then `python3 tools/maze_v3.py --from-drc drc.json` | Grid maze router for whatever is still open; ties +3V3/GND ends to their plane when a point-to-point path does not exist |
| 9. Order files | `python3 tools/jlc_export.py` | Gerbers, drills, BOM and CPL into `jlcpcb/` in V2's format |

Freerouting's own command line ignores the pass limit and never writes the session
file in 2.1.0, which is why `FreeroutingHeadless.java` drives the router directly.
