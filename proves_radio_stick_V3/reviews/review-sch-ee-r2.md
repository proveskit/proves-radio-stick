# Radio Stick V3 schematic review, round 2 (principal EE)

Goal restated: get the STM32U575VIT6 (LQFP-100) radio stick order-ready at JLCPCB by morning, as the trial for the U5A5VJT6 flight controller. This round checks that the r1 fixes in commit f18b556 landed, that the six moved radio pins and the two moved J3 pins broke nothing, and looks for anything r1 missed.

Evidence used this session:
- Netlist `WORK/v3.net.xml` dumped to `/tmp/claude-0/-home-claude/674b3aef-f740-5b2a-bc1d-98dbdf2f1ed2/scratchpad/rev_ee2/nets.txt` (script `rev_ee/nets.py`). Component fields (value, LCSC, dnp, exclude_from_bom) read from the same XML.
- `check_pinmap.py` against both ST open pin data files, `check_netlist.py` against the netlist (both rerun, results below).
- `WORK/erc.rpt` (06:53:42): only `lib_symbol_issues` and `footprint_link_issues` warnings (library table not configured in the container). Zero errors. Note it ignores "Global label only appears once", so I checked single-node nets in the netlist instead: none.
- ST open pin data `STM32U575VITx.xml` / `STM32U5A5VJTx.xml` for the AF and wake-up/tamper functions on every moved pin.
- Built Zephyr DTS `build_app/zephyr/zephyr.dts` (06:54, built from the f18b556 tree) and Zephyr source `zws/zephyr/drivers/usb/udc/udc_stm32.c`.
- Render `WORK/sch_r2-1.png`; schematic text items in `proves_radio_stick_V3.kicad_sch`.
- Web: LCSC product-detail pages for C5270999 (STM32U575VIT6, 188 in stock) and C411294 (E22-900M30S, found, out of stock); LCSC product-detail C411292 returns "Part not found" (fetched twice); JLCPCB partdetail C411292 shows E22-400M30S, Extended, no stock figure. ST community thread "stm32u575 rom bootloader no usb enumeration on nucleo u575zi q". AN2606 (st.com PDF and stmcu.com.cn mirror) was reachable only as a table of contents: section 95.1 / Table 217 "STM32U575xx/85xx configuration in system memory boot mode" exists at p.501, but its rows were not readable. DS13737 was not reachable. Points from either are labelled "memory".

## 1. r1 fixes, verified in the netlist

| r1 item | Expected | Netlist (measured) | Result |
|---|---|---|---|
| L3 CS | PC4 | `SPI1_CS0` = R9.1, TP2.1 (DNP), U1.33 PC4, U3.19 NSS | landed |
| L3 RST | PE3 | `RF1_RST` = R5.1, TP7.1 (DNP), U1.2 PE3, U3.15 NRST | landed |
| L3 DIO2 | PC5 | `RF1_IO2` = U1.34 PC5, U3.8 DIO2 | landed |
| L3 RXEN | PA3 | `RF1_RX_EN` = R11.2 (R11.1 GND), U1.26 PA3, U3.6 | landed |
| L3 TXEN | PA2 | `RF1_TX_EN` = R12.2 (R12.1 GND), U1.25 PA2, U3.7 | landed |
| L3 RF_PWR_EN | PE2 | `RF_PWR_EN` = R95.1 (R95.2 +3V3), U1.1 PE2, U19.3 ON | landed (pull-up kept, decision 4) |
| EE1-02 J3 SPI2 | PB13/PC2/PC3 | J3_IO5 = J3.6/U1.52 PB13, J3_IO6 = J3.7/U1.17 PC2, J3_IO7 = J3.8/U1.18 PC3 | landed |
| L1, L2 removals | J4, R39, R41, R7, R8 gone | none of the five refs in the component list | landed |
| EE1-07 / EE1-18 | R14, R15, TP1-7 DNP | all nine carry `dnp` and `exclude_from_bom` | landed |
| L2 USB direct | J12 -> U4 -> PA11/PA12 | `USB_D+` = J12.A6/B6, U4.3/4, U1.71 PA12; `USB_D-` = J12.A7/B7, U4.1/6, U1.70 PA11. No other parts on the pair | landed, D+/D- polarity correct |
| EE1-04 LSE | drive medium-high | DTS `&clk_lse { driving-capability = <2>; }`, present in built `zephyr.dts` line 1611 | landed |
| EE1-01 UCPD | no UCPD pin used | PA15, PB5, PB14, PB15 all `unconnected-(U1-...)` | landed |
| Firmware | DTS follows netlist | built DTS: cs PC4, reset PE3, busy PB9, dio1 PB8, tx-en PA2, rx-en PA3, rf-vcc enable PE2, spi2 PB13/PC2/PC3 | matches |

Checks rerun: `check_pinmap.py` on U575VITx: 36 pins, 0 problems, EXTI lines {9, 8, 5, 13} unique. `check_netlist.py`: OK, 100 U1 pins, 46 NC-flagged, parts without LCSC only H1-H4 and the DNP TP1-TP7.

## 2. Moved pins: reset state, EXTI, boot, 5 V

| Pin | Net | Reset state (memory: U5 GPIOs reset to analog, no pull, except debug pins) | External level before firmware | Verdict |
|---|---|---|---|---|
| PE2 (1) | RF_PWR_EN | analog, Hi-Z. No JTAG pull (unlike old PB4) | R95 10k to +3V3: radio ON from reset, as decision 4 wants | OK |
| PE3 (2) | RF1_RST | analog, Hi-Z | R5 10k to +3V3: radio out of reset | OK |
| PC4 (33) | SPI1_CS0 | analog, Hi-Z | R9 10k to +3V3: NSS idle high | OK |
| PC5 (34) | RF1_IO2 | analog, Hi-Z | driven by the SX1268 (or Hi-Z); analog mode has no input buffer, so no crowbar | OK |
| PA2 (25) | RF1_TX_EN | analog, Hi-Z | R12 10k to GND: PA off | OK |
| PA3 (26) | RF1_RX_EN | analog, Hi-Z | R11 10k to GND: LNA path off | OK |

- PE2 and PE3 carry DEBUG_TRACECLK / TRACED0 (opd). These only become active if a debugger enables 4-bit synchronous trace; SWO trace on PB3 does not touch them. Note only.
- PE3 has TAMP_IN6/TAMP_OUT3, PC5 has TAMP_IN4/TAMP_OUT5 and PWR_WKUP5, PA2/PA3 have PWR_WKUP4/5 (opd). None is active unless firmware enables the tamper or wake-up function. Note only.
- EXTI: DIO1 PB8 = 8, BUSY PB9 = 9, DIO2 PC5 = 5, USER_BTN PC13 = 13. All unique. J3 still shares lines (PA0/PC0 = 0, PA1/PC1 = 1, PB13 with the button on 13); PC2 = 2, PC3 = 3, PA4 = 4 do not collide with the radio. Same as r1 EE1-16.
- USB VBUS sensing: PA9 is OTG_FS_VBUS (opd) and is used as USART1_TX. `udc_stm32.c` never sets `vbus_sensing_enable`, so the HAL init field stays 0 (disabled). No conflict.
- 5 V on J3: decision 6 keeps J3 3.3 V-only by silk. PC2/PC3 are FT_a and PA4 is TT_a (memory, DS13737 not reachable). The move did not make J3 less tolerant than r1.

## 3. Findings

Blockers: none. Majors: 1 (sourcing, needs a check before the BOM upload).

| id | severity | finding | evidence | fix |
|---|---|---|---|---|
| EE2-01 | major (inherited, unverified) | The E22-400M30S LCSC number C411292 now returns "Part not found" on LCSC, while the sister E22-900M30S C411294 resolves (out of stock). JLC's own part page still lists C411292 as Extended but shows no stock figure. SOURCING.md's "250 in stock" is from an earlier check. If C411292 is delisted, the JLC BOM upload fails on the one part the board exists for. | LCSC product-detail C411292: "Part not found. Please kindly contact support to check availability or alternatives" (two fetches). LCSC C411294 page: E22-900M30S, Out of Stock. LCSC C5270999 control fetch works (188). JLC partdetail C411292: "Extended", no stock shown. jlc.sh API: proxy 403. | Before ordering, search C411292 in the JLC BOM tool. If it is not orderable, either pre-order E22-400M30S into the JLC private parts library through Global Sourcing, or mark U3 DNP and hand-fit the modules (the stencil still covers its pads). Record the outcome in SOURCING.md. |
| EE2-02 | minor (memory) | In system-bootloader mode (BOOT0 held, DFU flashing), the ROM may configure other bootloader interfaces on the radio pins. From memory, the U5 bootloader also listens on USART2 PA2/PA3 and FDCAN1 PB8/PB9. If so, PA2 (TXEN) can be driven high (PA on, idle) and PB9 (BUSY, an SX1268 push-pull output) can be driven against the radio, because R95 keeps the radio powered in bootloader mode. Transient and current-limited, not damage-level. | AN2606 section 95.1 / Table 217 exists (TOC read) but rows not readable. Netlist: PA2 = RF1_TX_EN, PB9 = RF1_IO0 (BUSY), R95 to +3V3. | Check AN2606 Table 217 when reachable. If PB8/PB9 or PA2/PA3 are listed, accept for the trial board or default the radio OFF (R95 to GND, same C25744) so the module is unpowered during DFU. |
| EE2-03 | minor (re-check of declined EE1-06) | New fact since decision 4: RF_PWR_EN moved from PB4 (NJTRST internal pull-up) to PE2 (no pull at reset). The r1 objection that a pull-down could not hold the switch off is gone. Default-off is now a zero-cost swap of R95's top end to GND; firmware already drives PE2 through `regulator-fixed` with `regulator-boot-on`. | Netlist `RF_PWR_EN`; opd pin 1 PE2 has no JTAG function; DTS rf-vcc node. | No change required. Product call stands; listed so the cost is visible. |
| EE2-04 | minor | Stale schematic notes: the U19 note says "firmware enables via GPIO18" (RP2350 name; now PE2), and the STDC14 note says "J4 shares USART1" (J4 is deleted). | `kicad_sch` text items at line 17593 and 24627. | Edit both strings in `gen_v3_schematic.py` (or the copied V2 text): "firmware enables via PE2"; drop the J4 sentence. |
| EE2-05 | minor | Docs disagree with the netlist. `pinmap/README.md` J3 table still lists the QFN-48 map (J3_IO3 = PA2, J3_IO4 = PA3, J3_IO6/7 = PB14/PB15). PA2/PA3 now drive TXEN/RXEN, so a user enabling LPUART1 "on J3" from that table would key the PA. `decisions.md` row 3 says RXEN -> PC7, but the commit put it on PA3. | pinmap README lines 43-50; decisions.md row 3; pinmap.csv and netlist. | Regenerate the README J3 table from pinmap.csv; amend decisions row 3 to PA3 (superseded by layout L3). |
| EE2-06 | minor | `check_pinmap.py` against `STM32U5A5VJTx.xml` fails on PA11/PA12 because the CSV names the FS AF (`USB_OTG_FS_DM/DP`) and the U5A5 names them `USB_OTG_HS_DM/DP`. Expected, but it means the pin map is not checked against the target part. | Run output: "NO AF PA11 USB_OTG_FS_DM ... USB_OTG_HS_DM", 2 problems, rc 1. | Let the checker accept `USB_OTG_FS_*` or `USB_OTG_HS_*` for PA11/PA12, then run it on both parts in CI. |
| EE2-07 | minor (cosmetic) | J3's symbol overlaps the title block in the render. | `sch_r2-1.png`, bottom right. | Move J3 up about 15 mm in the generator. |
| EE2-08 | note | PC13 (USER_BTN, R102 pull-up, SW3 to GND) sits next to OSC32_IN (pin 8). Button edges are rare and slow, so the LSE risk is small. | Netlist `/USER_BTN` U1.7; `/OSC32_IN` U1.8. | Layout: keep the PC13 trace off the LSE guard and away from Y102. |
| EE2-09 | note | E22 back-power path with RF_VCC off is now R9 (NSS) and R5 (NRST) only, about 0.33 mA each through the module's IO clamps. Accepted in r1. | Netlist R9.2, R5.2 on +3V3; R14/R15 DNP. | Firmware: drive PC4 and PE3 low (or set them analog) before PE2 goes low. |
| EE2-10 | note | J3 has no supply pin (pins 1 and 10 are GND), so an external face board or SD breakout needs its own 3.3 V, while R104/R105 pull I2C3 to the stick's +3V3. Inherited from V2. | Netlist J3.1, J3.10 on GND; R104.1/R105.1 on +3V3. | None for V3. Document it next to the "3V3 logic only" silk. |
| EE2-11 | note | Blocks rechecked with no new issue: buck feedback 0.8 x (1 + 510k/162k) = 3.32 V (R3/R4); PLL1 16 MHz / 1 x 30 = 480 MHz VCO, /3 = 160 MHz, /10 = 48 MHz USB (DTS); BOOT0 R101 pull-down with SW1 to +3V3; NRST C114 + SW2; all 22 E22 pins, all 6 U19, U4 and 7 U2 pins and all J12 pins connected; no single-node nets. | Netlist; DTS; component list. | None. |

Declined r1 items rechecked: EE1-08 (J3 series resistors) has no new evidence and stays declined. EE1-06 is EE2-03 above.
