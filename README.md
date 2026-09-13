# proves-radio-stick
New repo for working on a USB stick sized LoRa radio module. 

# Design Purpose
Being able to send and receive data using radios is one of the most fundemental functionalities of the satellite system. Right now, if we want to do anything with the radios we need to take a whole flight controller board out and get it setup to send and receive data. It would be nice to have an [RTL-SDR Style](https://www.rtl-sdr.com/buy-rtl-sdr-dvb-t-dongles/) USB dongle that can be used for testing and ground station purposes! 

# Design Requirements
- Employs an RP2040 Microcontroller (V0); RP2350 from V1 onward
- Onboard 3.3 V regulator for the microcontroller (LDO on V0, TPS62085 buck from V1); V2 radio runs from 5 V VBUS via ferrite
- Radio module: RFM9XW slot (V0), EByte E32-400M20S (V1), EByte E22-400M30S (V2)
- SMA Adaptor for the Antenna
- Is as comapct as possible 

# Versions
| Dir | MCU | Radio | Rail | Antenna | Notes |
|---|---|---|---|---|---|
| `provesradiostick_V0` | RP2040 | RFM9XW slot (SX127x) | 3V3 LDO | SMA | Original concept |
| `proves_radio_stick_V1` | RP2350 | EByte E32-400M20S (SX1278, 20 dBm) | 3V3 buck (TPS62085) | SMA | 4-layer 60 x 32.89 mm |
| `proves_radio_stick_V2` | RP2350 | EByte E22-400M30S (SX1268, 30 dBm) — same module as FC v5e | 3V3 buck + 5 V `RF_VCC` from VBUS via ferrite | SMA | 4-layer 80.5 x 32.89 mm; V1 stretched 20.5 mm to fit the 24 x 38.5 mm module |

## V2 radio pinout (RP2350 GPIO)
| E22 pin | Net | GPIO |
|---|---|---|
| NSS / SCK / MOSI / MISO | SPI1_CS0 / SPI1_SCK / SPI1_MOSI / SPI1_MISO | 9 / 10 / 11 / 8 |
| NRST | RF1_RST | 6 |
| BUSY | RF1_IO0 | 14 |
| DIO1 | RF1_IO1 | 15 |
| DIO2 | RF1_IO2 | 16 |
| RXEN / TXEN | RF1_RX_EN / RF1_TX_EN | 20 / 21 |
| VCC | RF_VCC (5 V, VBUS → FB1 → U19 TPS22918 load switch) | — |
| Radio power enable | RF_PWR_EN → U19 ON (10k pull-up to 3V3, default ON) | 18 |

V2 note: at 30 dBm the E22 draws ~650 mA peak on TX, above the 500 mA USB 2.0 default; use a USB 3 or high-current port for sustained TX. The 110 µF behind U19 soft-starts over ~3 ms (CT 1 nF, ~0.19 A inrush) so the host only sees ~11 µF at plug-in. Drive GPIO18 low then high to power-cycle the radio (hold NRST low and SPI lines low while off). V2 drops the 2.54 mm SWD pin header J1; use the JST-SH SWD connector J22. J3 screw terminal is sourced as Cixi Kefa KF128-2.54-10P (LCSC C474928), a 2.54 mm drop-in for the Phoenix MPT 0,5/10-2,54 footprint. J4 header and TP1–TP7 are not populated by JLC. Firmware differs from V1: SX1268 driver with BUSY handshake, not SX1278. Pin numbering differs from FC v5e (v5e uses SPI0 GPIO9-12, BUSY 13, DIO1 14, RXEN 22).
