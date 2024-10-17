# proves-radio-stick
New repo for working on a USB stick sized LoRa radio module. 

# Design Purpose
Being able to send and receive data using radios is one of the most fundemental functionalities of the satellite system. Right now, if we want to do anything with the radios we need to take a whole flight controller board out and get it setup to send and receive data. It would be nice to have an [RTL-SDR Style](https://www.rtl-sdr.com/buy-rtl-sdr-dvb-t-dongles/) USB dongle that can be used for testing and ground station purposes! 

# Design Requirements
- Employs an RP2040 Microcontroller
- Onboard low noise LDO Regulator for converting USB 5V to 3.3V for the Microcontroller and Radio
- Uses an RFM9XW radio module slot
- SMA Adaptor for the Antenna
- Is as comapct as possible 
