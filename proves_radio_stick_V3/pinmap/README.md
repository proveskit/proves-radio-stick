# V3 pin map — STM32U585CIU6 (UFQFPN-48)

`pinmap.csv` is the source of truth. It was checked against ST's
[STM32_open_pin_data](https://github.com/STMicroelectronics/STM32_open_pin_data)
`mcu/STM32U585CIUx.xml`: every non-GPIO signal exists on its pin, no pin or
net is used twice, and the interrupt inputs sit on distinct EXTI lines.

All 37 I/O pins are used; there are **no spares**.

## Radio (E22-400M30S)

| E22 pin | Net | STM32 pin | Notes |
|---|---|---|---|
| SCK / MISO / MOSI | SPI1_SCK / SPI1_MISO / SPI1_MOSI | PA5 / PA6 / PA7 | SPI1 AF5 |
| NSS | SPI1_CS0 | PA15 | GPIO CS. JTDI pull-up keeps the radio deselected through reset |
| NRST | RF1_RST | PB12 | |
| BUSY | RF1_IO0 | PB9 | EXTI9 |
| DIO1 | RF1_IO1 | PB8 | EXTI8, the IRQ line the Zephyr sx126x driver uses |
| DIO2 | RF1_IO2 | PB10 | EXTI10 |
| RXEN / TXEN | RF1_RX_EN / RF1_TX_EN | PB5 / PA8 | Neither pin has a reset pull-up, so the 10k pull-downs hold the PA/LNA off |
| (U19 ON) | RF_PWR_EN | PB4 | NJTRST pull-up matches the 10k pull-up: radio defaults ON, like V2 |

## Everything else

| Function | Pins |
|---|---|
| USB FS | PA11 DM, PA12 DP |
| SWD (J22 JST-SH + STDC14) | PA13 SWDIO, PA14 SWCLK, PB3 SWO (STDC14 only) |
| VCP UART (STDC14) and J4 UART | USART1: PA9 TX, PA10 RX. **Shared**: use STDC14 VCP *or* J4, not both |
| I2C1 (J4, 4.7k pull-ups) | PB6 SCL, PB7 SDA |
| USB-C CC sense | PB1 ADC1_IN16 (CC1), PB2 ADC1_IN17 (CC2) |
| Firmware_Active LED (D1) | PB0 |
| User button SW3 | PC13 (WKUP2, can wake from Standby) |
| BOOT0 button SW1 | PH3-BOOT0 (10k pull-down) |
| HSE 16 MHz | PH0, PH1 |
| LSE 32.768 kHz | PC14, PC15 |

## J3 breakout (10-pin screw terminal)

| J3 pin | Net | STM32 | Useful functions |
|---|---|---|---|
| 1 | GND | | |
| 2 | J3_IO1 | PA0 | ADC1_IN5, TIM2_CH1, UART4_TX, WKUP1 |
| 3 | J3_IO2 | PA1 | ADC1_IN6, TIM2_CH2, UART4_RX |
| 4 | J3_IO3 | PA2 | ADC1_IN7, TIM2_CH3, LPUART1_TX |
| 5 | J3_IO4 | PA3 | ADC1_IN8, TIM2_CH4, LPUART1_RX |
| 6 | J3_IO5 | PA4 | ADC1_IN9, **DAC1_OUT1** |
| 7 | J3_IO6 | PB13 | SPI2_SCK, I2C2_SCL |
| 8 | J3_IO7 | PB14 | SPI2_MISO, I2C2_SDA |
| 9 | J3_IO8 | PB15 | SPI2_MOSI |
| 10 | GND | | |

So J3 offers 5 ADC inputs, a DAC output, 4 PWM channels (TIM2), a UART
(UART4 or low-power LPUART1), and SPI2 or I2C2.

## Trade-offs taken to fit 37 pins
- The optional second user LED from the plan is dropped.
- J4's UART shares USART1 with the ST-LINK VCP instead of having its own.
- VBUS sense is dropped: the board is bus-powered, so VBUS is always present,
  and the CC-sense pins give more useful information.

## Package notes for the schematic
- This package has **no VDDUSB, VDDIO2 or VREF+ pins**. VDDUSB is bonded to
  VDD, and VREF+ to VDDA.
- Power pins: VBAT (1), VSSA (8), VDDA (9), VCAP (22), VSS/VDD (23/24, 35/36,
  47/48).
