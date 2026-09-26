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
| LEDs | D3 power, D1 Firmware_Active (GPIO7) | keep; add optional 2nd user LED |
| — | — | **Add** user button (SW3) |
| Radio power | VBUS → FB1 → TPS22918 → RF_VCC | unchanged |

## Key design decisions (recommendations)

| Decision | Recommendation | Why |
|---|---|---|
| Package | **UFQFPN-48 (STM32U585CIU6)** | Confirmed JLC part; 48 pins is enough (see pin budget). Fallback: pin-compatible STM32U575CIU6 if stock is out (loses crypto accelerators only). |
| Regulator variant | **LDO part (no "Q" suffix)** | SMPS "Q" variants need an extra inductor + VDD11 pins; LDO keeps the BOM and layout simple. Power saving isn't the point of this board. |
| USB clock | **HSI48 + CRS synced to USB SOF** | Crystal-less USB FS is supported; removes a dependency on HSE. |
| HSE | **Populate a 16 MHz 3225 crystal** (reuse ABM8 family if available) | Lets devs learn RCC/PLL config the "normal" way and gives stable SPI/timer clocks. |
| LSE | **Populate 32.768 kHz** | RTC + LPTIM are core U5 learning topics; one extended part. |
| Debug connector | **STDC14 (2x7 1.27 mm) + keep J22 JST-SH 3-pin** | STDC14 plugs straight into STLINK-V3MINIE (~$10) with NRST, SWO and VCP UART — needed for connect-under-reset, which matters on U5 once firmware uses Stop/Standby. J22 (C160389, already on V2) lets anyone with a Raspberry Pi Debug Probe from RP2350 work debug the U585 via CMSIS-DAP + OpenOCD (`target/stm32u5x.cfg`) at zero extra cost. Silkscreen: connect only one probe at a time. |
| USB ESD | **USBLC6-2SC6** | V2 has none; a stick that is plugged in constantly needs it. |
| USB current detect | **Route CC1/CC2 to ADC pins** (keep 5.1k Rd) | Reads the Type-C host's Rp to tell default (500 mA USB 2 / 900 mA USB 3), 1.5 A or 3 A; firmware caps E22 TX power when the port can't source ~650 mA. |
| Board stack/outline | **Reuse V2 4-layer, 80.5 x 32.89 mm** | Keeps RF, USB-C and SMA placement and the plastic/enclosure story unchanged. |

## Pin budget (UFQFPN-48 ≈ 38 I/O after power, USB, SWD, OSC)

Tentative — **must be validated in CubeMX** against DS13086 alternate-function
tables before schematic entry.

| Function | Pins | Tentative assignment |
|---|---|---|
| USB FS | 2 | PA11 DM, PA12 DP |
| SWD + SWO | 3 | PA13 SWDIO, PA14 SWCLK, PB3 SWO |
| HSE / LSE | 4 | PH0/PH1, PC14/PC15 |
| BOOT0 | 1 | PH3-BOOT0 |
| Radio SPI | 4 | SPI1: PA5 SCK, PA6 MISO, PA7 MOSI, PA4 NSS (GPIO) |
| Radio control | 7 | NRST, BUSY (EXTI), DIO1 (EXTI), DIO2, RXEN, TXEN, RF_PWR_EN |
| Debug VCP UART | 2 | USART1 PA9/PA10 → STDC14 |
| J4 I2C | 2 | I2C1 PB6/PB7 (+4.7k pull-ups) |
| LEDs + user button | 3 | Firmware_Active LED, user LED, SW3 |
| USB CC sense | 2 | CC1, CC2 on ADC-capable pins |
| J3 breakout | 8 | ≥3 ADC, ≥2 timer PWM, one SPI2 or I2C/UART pair |
| **Total** | **38** | ~0 spare — trim J3 or the user LED if CubeMX finds conflicts |

TCXO note: FC v5e sets `dio3-tcxo-voltage = SX126X_DIO3_TCXO_1V8`; confirm the
E22-400M30S behaves the same on V3 (it is the same module, so it should).

## Phases

### Phase 0 — Sourcing check (½ day)
- [ ] Confirm live JLC stock/price of STM32U585CIU6 (C5271026); note fallback
      STM32U575CIU6 LCSC number.
- [ ] Confirm LCSC numbers for: STDC14 2x7 1.27 mm header, 16 MHz and
      32.768 kHz crystals, USBLC6-2SC6, BOOT0/user buttons (reuse KMR2 C72443).
- [ ] Record which parts are Basic vs Extended; target ≤ 12 unique extended parts.
- [ ] Check whether JLC Economic PCBA accepts this 4-layer stack-up; otherwise
      budget for Standard PCBA.

### Phase 1 — Pin map (1 day)
- [ ] New CubeMX project for STM32U585CIUx; enable USB OTG_FS device, SPI1,
      USART1, I2C1, RTC/LSE, HSE, SWD+SWO, EXTI for BUSY/DIO1.
- [ ] Assign J3 breakout pins to maximise peripheral variety.
- [ ] Publish the pin table in the README (same format as the V2 table); it
      becomes the Zephyr pinctrl/devicetree input in Phase 4.

### Phase 2 — Schematic (2–3 days)
- [ ] Copy V2 project to `proves_radio_stick_V3/` (rename files, keep
      footprint libs and `jlcpcb/project.db` workflow).
- [ ] Delete RP2350 sheet section, W25Q128, Y1 12 MHz, L3, C65/C66/C68/C69
      (1V1/VREG_AVDD), R7/R8, R93/R94, J22.
- [ ] Add STM32U585 symbol/footprint (KiCad lib has `MCU_ST_STM32U5`;
      check UFQFPN-48 footprint's exposed-pad handling).
- [ ] Power: 100 nF per VDD pin + 4.7 µF bulk, VDDA 1 µF + 100 nF (ferrite
      optional), VDDUSB 100 nF, VBAT to 3V3, VCAP 4.7 µF per datasheet.
- [ ] NRST: 100 nF to GND + SW2 + STDC14 pin. SWD: J22 JST-SH and STDC14 in
      parallel on SWDIO/SWCLK/GND. BOOT0: 10k pulldown + SW1 to 3V3.
- [ ] USB: USBLC6-2 at connector, 5.1k CC pulldowns unchanged, CC1/CC2 also
      to ADC pins (host current advertisement), VBUS sense
      divider to a GPIO (optional, useful for USB-detect examples).
- [ ] Radio: re-wire SPI/control nets to the Phase 1 pins; keep R9/R14/R15/
      R5/R11/R12 pull-ups/-downs and TP1–TP7.
- [ ] Add SW3 user button, optional second LED.
- [ ] ERC clean; add LCSC field on every part (same convention as V2).

### Phase 3 — Layout (3–4 days)
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

### Phase 4 — Zephyr bring-up, in parallel with Phase 3 (3–5 days)
Zephyr only — the PROVES flight software (`proves-core-reference`) is F Prime
on Zephyr, so this is the crossover path that matters.
- [ ] Zephyr board `boards/bronco_space/proves_radio_stick_v3/` modelled on
      upstream `b_u585i_iot02a` for SoC/clock setup and on FC v5e's `lora0`
      node (`semtech,sx1262` compatible, `busy-gpios`, `dio1-gpios`,
      `rx-enable-gpios`/`tx-enable-gpios`, `dio3-tcxo-voltage`).
- [ ] RF_PWR_EN handled as a regulator-fixed or power-domain node so the
      radio is sequenced correctly.
- [ ] Samples: `blinky`, USB CDC-ACM console, LoRa `send`/`receive`
      interop test against an FC v5e.
- [ ] USB-C current detect: read CC ADC at boot, clamp E22 TX power when the
      host only advertises default USB current.
- [ ] Document flashing three ways: STLINK-V3MINIE (`west flash`),
      Raspberry Pi Debug Probe on J22 (`west flash --runner openocd` /
      pyOCD), and ROM USB DFU (BOOT0 + reset, `dfu-util`).

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
