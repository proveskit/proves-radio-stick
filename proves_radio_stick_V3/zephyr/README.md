# Zephyr support for PROVES Radio Stick V3

Out-of-tree board `proves_radio_stick_v3` (vendor `bronco_space`, same as the
PROVES flight controller boards) and a bring-up app. Tested against Zephyr
**v4.4.2**, the version `proves-core-reference` pins, with `hal_stm32` added.

```
zephyr/
├── boards/bronco_space/proves_radio_stick_v3/   board definition
└── app/                                         bring-up app (LoRa shell over USB)
```

## Build

In a west workspace that has Zephyr v4.4.2 plus `hal_stm32`, `cmsis` and
`loramac-node`:

```sh
west build -b proves_radio_stick_v3 <repo>/proves_radio_stick_V3/zephyr/app \
    -- -DBOARD_ROOT=<repo>/proves_radio_stick_V3/zephyr
```

Upstream samples work the same way, e.g. `samples/basic/blinky`.
`samples/drivers/lora/send` also builds, but it transmits on 865.1 MHz, which
is outside the E22-400's 410–493 MHz band. Use the app below instead.

## Flash

| Probe | Connector | Command |
|---|---|---|
| STLINK-V3MINIE | J5 (STDC14) | `west flash` (STM32CubeProgrammer) or `west flash -r openocd` |
| Raspberry Pi Debug Probe / any CMSIS-DAP | J22 (JST-SH) | `west flash -r pyocd` (first `pyocd pack install stm32u585ciux`) or `west flash -r openocd --config <board>/support/openocd-cmsis-dap.cfg` |
| None (USB ROM bootloader) | USB-C | Hold **BOOT0** (SW1), tap **RESET** (SW2), release, then `west flash -r dfu-util` |

J22 has no NRST line. If firmware has disabled SWD or sits in Stop/Standby,
use the STDC14 probe (connect-under-reset) or the BOOT0 route.

## Bring-up app

The console and shell run on USB CDC-ACM (`/dev/tty.usbmodem*`); no probe is
needed. At boot the app:

1. reads the USB-C CC pins (PB1/PB2) and reports what the host advertises;
2. presets the radio to the PROVES link: 437.4 MHz, BW 125 kHz, SF8, CR 4/5,
   preamble 8. TX drive is 22 dBm on ≥1.5 A USB-C ports and 10 dBm otherwise,
   because the E22 draws ~650 mA at 30 dBm;
3. blinks the Firmware Active LED (D1).

Then use the Zephyr LoRa shell:

```
uart:~$ lora recv 10000
uart:~$ lora send hello
uart:~$ lora config sf 7
```

## Board notes

- **Clocks:** 16 MHz HSE → PLL1 VCO 480 MHz. R /3 gives 160 MHz SYSCLK and
  Q /10 gives 48 MHz for USB, so USB has crystal accuracy. Zephyr's U5 clock
  driver has no CRS support, so crystal-less HSI48 USB isn't an option.
  LSE 32.768 kHz drives the RTC and LPTIM1 (low-power tick).
- **Radio:** described as `semtech,sx1262`, as on FC v5e. The E22-400M30S
  is an SX1268, but Zephyr 4.4 only accepts that compatible through the LoRa
  Basics Modem module, which the flight software doesn't use.
  `dio3-tcxo-voltage` and `rx-boosted` match FC v5e.
- **Radio power:** `rf_vcc` is a `regulator-fixed` on PB4 (U19 TPS22918),
  on at boot. Use the regulator API to power-cycle the module.
- **J3 breakout:** DAC1, SPI2, I2C2, LPUART1 and TIM2 PWM are pre-wired but
  disabled. Enable one per pin in an overlay, e.g. `&spi2 { status = "okay"; };`.
- **Flash layout:** MCUboot 64 KB, two 960 KB image slots, 64 KB storage.
