# V3 pin map: STM32U575VIT6 (LQFP-100)

`pinmap.csv` is the source of truth. It was checked against
ST's [STM32_open_pin_data](https://github.com/STMicroelectronics/STM32_open_pin_data)
`mcu/STM32U575VITx.xml`: every non-GPIO signal exists on its pin, no pin or
net is used twice, the interrupt inputs sit on distinct EXTI lines, and no
UCPD1 CC or dead-battery pin (PA15, PB15, PB5, PB14) is used.

The board uses 36 of the 82 I/O pins. The other 46 are NC-flagged and free for
bodge wires.

All non-Q LQFP-100 STM32U5 parts (U575, U585, U595, U5A5) share this pinout,
so the flight part U5A5VJT6 fits the same footprint. Never fit a Q-suffix
(SMPS) part: its pinout differs.

## Radio (E22-400M30S)

The radio pins sit on the side of the package that faces the E22.

| E22 pin | Net | STM32 pin | Reset level held by |
|---|---|---|---|
| SCK / MISO / MOSI | SPI1_SCK / SPI1_MISO / SPI1_MOSI | PA5 / PA6 / PA7 | SPI1 AF5 |
| NSS | SPI1_CS0 | PC4 | R9 pull-up (deselected) |
| NRST | RF1_RST | PE3 | R5 pull-up (out of reset) |
| BUSY | RF1_IO0 | PB9 | EXTI9 |
| DIO1 | RF1_IO1 | PB8 | EXTI8, the IRQ line the Zephyr sx126x driver uses |
| DIO2 | RF1_IO2 | PC5 | EXTI5 |
| RXEN / TXEN | RF1_RX_EN / RF1_TX_EN | PA3 / PA2 | R11 / R12 pull-downs (PA and LNA off) |
| (U19 ON) | RF_PWR_EN | PE2 | R95 pull-up: radio on by default, like V2 |

## Everything else

| Function | Pins |
|---|---|
| USB FS | PA11 DM, PA12 DP |
| SWD (J22 JST-SH + STDC14) | PA13 SWDIO, PA14 SWCLK, PB3 SWO (STDC14 only) |
| VCP UART (STDC14) | USART1: PA9 TX, PA10 RX |
| USB-C CC sense | PB1 ADC1_IN16 (CC1), PB2 ADC1_IN17 (CC2) |
| Firmware_Active LED (D1) | PB0 |
| User LED (D2) | PC6 |
| User button SW3 | PC13 (WKUP2, can wake from Standby) |
| BOOT0 button SW1 | PH3-BOOT0 (10k pull-down) |
| HSE 16 MHz | PH0, PH1 |
| LSE 32.768 kHz | PC14, PC15 |

## J3 breakout (10-pin screw terminal, 3.3 V logic only)

| J3 pin | Net | STM32 | Default Zephyr node (disabled) |
|---|---|---|---|
| 1 | GND | | |
| 2 | J3_IO1 | PA0 | UART4_TX |
| 3 | J3_IO2 | PA1 | UART4_RX |
| 4 | J3_IO3 | PC0 | I2C3_SCL (R104 4.7k pull-up) |
| 5 | J3_IO4 | PC1 | I2C3_SDA (R105 4.7k pull-up) |
| 6 | J3_IO5 | PB13 | SPI2_SCK |
| 7 | J3_IO6 | PC2 | SPI2_MISO |
| 8 | J3_IO7 | PC3 | SPI2_MOSI |
| 9 | J3_IO8 | PA4 | SPI2 CS GPIO, or DAC1_OUT1 |
| 10 | GND | | |

PA0, PA1, PC0-PC3 and PA4 are also ADC inputs.

## Power pins (LQFP-100)

VBAT 6, VDD 11/28/50/75/100, VDDUSB 73, VDDA 22, VREF+ 21, VREF- 20,
VSSA 19, VSS 10/27/49/74/99, NRST 14, VCAP 48 (4.7 uF, LDO mode).
