# PROVES Radio Stick V3 — STM32U585 plan

## Goal

A low-cost USB radio stick that doubles as an **STM32U5 on-ramp**: developers
already comfortable with the RP2350 radio stick / FC v5e can plug in V3 and
learn the STM32U5 toolchain (CubeMX, ST-LINK, Zephyr on STM32) while talking to
the same E22-400M30S (SX1268) radio they fly.

Success = one-click JLCPCB order (Gerbers + BOM + CPL, every part with an LCSC
number, no hand-soldered parts except optional headers), and a Zephyr board
definition that transmits/receives LoRa out of the box. **Zephyr is the only
supported firmware target** (matches the F Prime + Zephyr flight software).

## Guiding principles

1. **Change only the MCU island.** Keep V2's USB-C, TPS62085 3V3 buck,
   TPS22918 RF_VCC load switch, E22-400M30S, SMA, J3 screw terminal and
   80.5 x 32.89 mm 4-layer outline. Those are already JLC-sourced and reviewed.
   The RP2350 + W25Q128 + 12 MHz crystal + 1V1 inductor region is what gets
   replaced.
2. **Standard STM32 dev ergonomics.** Official-probe debug connector, BOOT0
   button for ROM USB DFU, SWO, a user button — the things STM32 tutorials
   assume exist.
3. **Minimise JLC extended parts.** Each unique extended part adds a loading
   fee; prefer Basic parts for passives/LEDs/ESD and reuse V2 part numbers.
4. **Pin map validated in CubeMX** (as a pin/AF checking tool only); the
   Zephyr devicetree + pinctrl is the source of truth.

## What V2 has today (from the netlist)

| Function | V2 (RP2350) | V3 action |
|---|---|---|
| MCU | RP2350 QFN-60, C42411118 | → STM32U585CIU6 UFQFPN-48, [C5271026](https://jlcpcb.com/partdetail/STMicroelectronics-STM32U585CIU6/C5271026) |
| Flash | W25Q128 QSPI (U11) | **Remove** — U585 has 2 MB internal flash |
| Core rail | 1V1 via on-chip reg + L3 3.3 µH | **Remove** — replaced by VCAP cap (LDO variant) |
| Clock | 12 MHz ABM8 crystal (Y1) | → 16 MHz HSE crystal + 32.768 kHz LSE crystal, both populated |
| Boot | BOOTSEL button on QSPI_SS (SW1) | → BOOT0 button + pulldown (ROM USB DFU) |
| Reset | SW2 on RUN | → SW2 on NRST + 100 nF |
| Debug | J22 JST-SH 3-pin SWD | → **add** STDC14 1.27 mm header (SWO, NRST, VCP UART); **keep** J22 for Pi Debug Probe users |
| USB | RP2350 USB, 22 Ω series (R7/R8) | → OTG_FS PA11/PA12 direct (no series R), + USBLC6-2 ESD |
| Radio SPI | SPI1 GPIO 8-11 | → SPI1 PA5/PA6/PA7, NSS as GPIO |
| Radio ctrl | RST 6, BUSY 14, DIO1 15, DIO2 16, RXEN 20, TXEN 21, PWR_EN 18 | → GPIOs; BUSY/DIO1 on distinct EXTI lines |
| J3 breakout | GPIO22-29 (4 ADC) | → 8 pins chosen to expose ADC, timer PWM, a 2nd SPI/I2C/UART |
| J4 (DNP) | I2C1 + UART0 + 3V3 | → keep as DNP header: I2C1 + USART1 |
| LEDs | D3 power, D1 Firmware_Active (GPIO7) | keep (Firmware_Active → PB0) |
| — | — | **Add** user button (SW3) |
| Radio power | VBUS → FB1 → TPS22918 → RF_VCC | unchanged |

## Key design decisions (recommendations)

| Decision | Recommendation | Why |
|---|---|---|
| Package | **UFQFPN-48 (STM32U585CIU6)** | Confirmed JLC part (C5271026); 48 pins is enough (see pin budget). No in-stock drop-in fallback, so pre-buy the chips. |
| Regulator variant | **LDO part (no "Q" suffix)** | SMPS "Q" variants need an extra inductor + VDD11 pins; LDO keeps the BOM and layout simple. Power saving isn't the point of this board. |
| USB clock | **HSI48 + CRS synced to USB SOF** | Crystal-less USB FS is supported; removes a dependency on HSE. |
| HSE | **Populate a 16 MHz 3225 crystal** (reuse ABM8 family if available) | Lets devs learn RCC/PLL config the "normal" way and gives stable SPI/timer clocks. |
| LSE | **Populate 32.768 kHz** | RTC + LPTIM are core U5 learning topics; one extended part. |
| Debug connector | **STDC14 (2x7 1.27 mm) + keep J22 JST-SH 3-pin** | STDC14 plugs straight into STLINK-V3MINIE (~$10) with NRST, SWO and VCP UART — needed for connect-under-reset, which matters on U5 once firmware uses Stop/Standby. J22 (C160389, already on V2) lets anyone with a Raspberry Pi Debug Probe from RP2350 work debug the U585 via CMSIS-DAP + OpenOCD (`target/stm32u5x.cfg`) at zero extra cost. Silkscreen: connect only one probe at a time. |
| USB ESD | **USBLC6-2SC6** | V2 has none; a stick that is plugged in constantly needs it. |
| USB current detect | **Route CC1/CC2 to ADC pins** (keep 5.1k Rd) | Reads the Type-C host's Rp to tell default (500 mA USB 2 / 900 mA USB 3), 1.5 A or 3 A; firmware caps E22 TX power when the port can't source ~650 mA. |
| Board stack/outline | **Reuse V2 4-layer, 80.5 x 32.89 mm** | Keeps RF, USB-C and SMA placement and the plastic/enclosure story unchanged. |

## Pin map

Done in Phase 1; see [pinmap/README.md](pinmap/README.md) and
`pinmap/pinmap.csv`. The package has 37 I/O pins and all 37 are used (radio
11, USB 2, SWD+SWO 3, crystals 4, BOOT0 1, USART1 2, I2C1 2, LED 1, button 1,
CC sense 2, J3 8).

TCXO note: FC v5e sets `dio3-tcxo-voltage = SX126X_DIO3_TCXO_1V8`; confirm the
E22-400M30S behaves the same on V3 (it is the same module, so it should).

## Phases

### Phase 0 — Sourcing check (½ day) — results in [SOURCING.md](SOURCING.md)
- [x] STM32U585CIU6 (C5271026): 103 at JLC, $11.73. U575CIU6 fallback has
      **0 stock**, so there is no drop-in fallback.
- [x] LCSC numbers: HSE C13738 (Basic), LSE C97604, USBLC6-2SC6 C7519,
      STDC14 male 2x7 1.27 mm THT C22438122, buttons C72443.
- [x] Basic vs Extended: about 18 unique Extended (target ≤ 12 not met; see
      SOURCING.md for trims). Swap TPS62085RLTT → RLTR (C130072), which has
      more stock.
- [ ] **Buy STM32U585CIU6 + E22-400M30S into the JLC parts library** once the
      schematic freezes.
- [ ] Check whether JLC Economic PCBA accepts this 4-layer stack-up plus THT
      parts; otherwise budget for Standard PCBA.

### Phase 1 — Pin map ✅
- [x] Pin map validated against ST open pin data (AFs, EXTI lines, no
      conflicts): [pinmap/README.md](pinmap/README.md).
- [x] Trade-offs: no second user LED, J4 UART shares USART1 with the VCP,
      no VBUS sense.

### Phase 2 — Schematic ✅ (generated; needs human review in KiCad)
`proves_radio_stick_V3.kicad_sch` is generated from V2 by
`tools/gen_v3_schematic.py`: it removes the RP2350 section and adds the
STM32U585 block, connected by labels to the unchanged radio, power and USB-C
sections.
- [x] Removed U18 RP2350, U11 W25Q128, Y1, L3, C2, C63–C78, R1, R2, R10, R93,
      R94, D4 and the old SW1 BOOTSEL chain.
- [x] U1 STM32U585CIU6 (QFN-48 7x7, EP to GND, thermal vias). C101–C103
      100 nF VDD, C104 4.7 µF bulk, C105 100 nF VBAT, C106 1 µF + C107 100 nF
      VDDA, C108 4.7 µF VCAP (AN5373, LDO part), C109 100 nF NRST.
- [x] HSE Y101 16 MHz + 2x 12 pF; LSE Y102 32.768 kHz + 2x 10 pF.
- [x] SW1 BOOT0 to 3V3 + R101 10k pull-down; SW3 user button on PC13 + R102
      10k pull-up; SW2 reset unchanged on `~{RESET}` → NRST.
- [x] J5 STDC14 (SWD, SWO, NRST, VCP on USART1) in parallel with J22 JST-SH.
- [x] U4 USBLC6-2SC6 on the connector side; R7/R8 now 0 Ω (C17168).
- [x] USB_CC1/2_SENSE labels on the CC nets → PB1/PB2.
- [x] J3 nets renamed J3_IO1–J3_IO8. U2 → TPS62085RLTR (C130072).
- [x] ERC: no connection errors (only the library/footprint-link warnings V2
      also has). Netlist checked pin-by-pin against `pinmap/pinmap.csv`.
- [x] BOM `bom/proves_radio_stick_V3.csv`: every fitted part has an LCSC number.
- [ ] **Human review in KiCad**: tidy placement; the CC2 wire runs behind the
      V2 `USB_D-` label.
- [ ] Load-cap check: confirm HSE/LSE gm margin per ST AN2867 once the layout
      gives a stray-capacitance estimate.

### Phase 3 — Layout (3–4 days, in KiCad by a human)
`proves_radio_stick_V3.kicad_pcb` is still a copy of the V2 board. Start with
*Tools → Update PCB from Schematic*: this removes the RP2350 footprints and
loads U1, Y101/Y102, J5, U4, SW3, R101/R102 and C101–C113.
- [ ] Keep USB-C, buck, load switch, E22 module, SMA, J3 exactly where they
      are in V2; lock them.
- [ ] Place U585 where RP2350 + flash sat; decoupling on the same layer,
      shortest VCAP/VDD loops.
- [ ] USB DP/DM as 90 Ω diff pair, ESD right at connector.
- [ ] Crystals tight to PH0/PH1 and PC14/PC15, guard ring to GND, no traces
      beneath.
- [ ] Keep SPI to the radio short; keep MCU clock nets away from the E22's
      RF section and antenna feed.
- [ ] STDC14 at the board edge opposite USB-C so the probe and the USB cable
      don't fight.
- [ ] DRC clean against JLC 4-layer capabilities (reuse V2 DRC rules).

### Phase 4 — Zephyr bring-up ✅ (build-verified; needs hardware)
Zephyr only. Board and app are in [zephyr/](zephyr/README.md), built against
Zephyr v4.4.2 (the version `proves-core-reference` pins) with no warnings.
- [x] Board `bronco_space/proves_radio_stick_v3`: HSE → PLL1 160 MHz, USB
      48 MHz from PLL1Q (Zephyr's U5 driver has no CRS, so crystal-accurate
      USB instead of HSI48), LSE for RTC/LPTIM, CDC-ACM console.
- [x] `lora0` on SPI1 matching FC v5e (`semtech,sx1262` compatible so it uses
      loramac-node like the flight software; TCXO 1.8 V; rx-boosted).
- [x] RF_PWR_EN as `regulator-fixed`; J3 peripherals pre-wired, disabled.
- [x] Runners: STM32CubeProgrammer/OpenOCD (STLINK on J5), pyOCD/OpenOCD
      CMSIS-DAP (Pi Debug Probe on J22), dfu-util (BOOT0 ROM DFU), J-Link.
- [x] Bring-up app: USB shell with the Zephyr LoRa shell, preset to the
      flight link (437.4 MHz, BW125, SF8, CR4/5), CC-sense TX power limit.
- [x] Builds: hello_world, blinky, lora send/receive, bring-up app.
- [ ] On hardware: USB enumeration, DFU entry, LoRa interop with an FC v5e.
- [ ] Move the board into `proves-core-reference/boards/bronco_space/` once
      proven on hardware; MCUboot/sysbuild build not yet tried.

### Phase 5 — JLC package + review (1 day)
- [ ] Generate Gerbers/drill/BOM/CPL into `proves_radio_stick_V3/jlcpcb/`.
- [ ] Check CPL rotations in the JLC viewer, especially U585 pin 1, E22,
      USB-C, STDC14, crystals.
- [ ] Peer review checklist: power pins all decoupled, BOOT0 default low,
      NRST not driven by anything push-pull, USB ESD orientation, SWO routed.
- [ ] Update top-level README version table and add a V3 pinout table.

### Phase 6 — Order and validate (≈2 weeks with JLC lead time)
- [ ] Order 5 assembled boards.
- [ ] Bring-up: 3V3/RF_VCC rails, SWD connect, USB enumeration, DFU entry,
      LoRa TX/RX against FC v5e, TX current on USB 2 vs USB 3 host, CC
      detect vs a 1.5 A/3 A Type-C host, debug via both STLINK-V3MINIE and
      Pi Debug Probe.
- [ ] File issues → V3.1 errata.

## Rough effort
~2.5–3 engineer-weeks of design + firmware before order, plus JLC lead time.

## Decisions made
- Zephyr is the only supported firmware.
- HSE (16 MHz) and LSE (32.768 kHz) crystals are both populated.
- J22 JST-SH 3-pin SWD stays, in parallel with the STDC14 header.
- Single radio build: 30 dBm E22-400M30S only, no low-power variant. Target
  host is a USB-C port; the CC-sense ADC path lets firmware reduce TX power
  on hosts that only advertise default USB current (e.g. USB-A adapters).
