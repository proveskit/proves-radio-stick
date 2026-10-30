"""MCU island placement for the V3 board: ref -> (x mm, y mm, rotation deg, side).

U1 sits where the RP2350 and its flash were, pin 1 top-left: USB (pins 70/71)
faces J12, SWD faces the STDC14, and the radio pins (bottom-left) face the
E22. Crystals and most decoupling go on the bottom inside the LQFP shadow,
each beside the pin it serves; vias drop straight into the In1 GND and
In2 +3V3 planes.
"""
PLACE = {
    'U1':   (222.20, 98.85, 0, 'F'),
    # top strip: buttons, SWD connectors, LEDs
    'SW1':  (214.25, 87.27, 90, 'F'),    # BOOT0
    'SW2':  (217.55, 87.27, 90, 'F'),    # RESET
    'SW3':  (220.85, 87.27, 90, 'F'),    # USER
    'J22':  (226.00, 87.20, 0, 'F'),
    'J5':   (234.19, 93.41, 180, 'F'),   # STDC14 pin 1; turned so SWO (8) faces U1
    'D1':   (237.20, 89.30, 90, 'F'),
    'D2':   (238.90, 89.30, 90, 'F'),
    'R13':  (237.20, 92.30, 90, 'F'),
    'R103': (238.90, 92.30, 90, 'F'),
    # USB
    'U4':   (233.30, 99.00, 270, 'F'),   # VBUS pin 5 faces down, toward the B.Cu feed
    'R26':  (235.66, 100.70, 90, 'F'),
    'R27':  (235.66, 95.62, -90, 'F'),
    # strip under the MCU (top)
    'C102': (217.45, 108.20, 0, 'F'),    # VDD 28
    'C113': (227.45, 108.20, 180, 'F'),  # VCAP 48
    'C103': (229.40, 108.20, 0, 'F'),    # VDD 50
    'D3':   (224.00, 108.70, 0, 'F'),
    'R11':  (213.90, 108.60, 90, 'F'),    # RXEN pull-down
    'R12':  (214.90, 108.60, 90, 'F'),    # TXEN pull-down
    # bottom, inside the LQFP shadow
    'Y102': (216.60, 94.90, 90, 'B'),    # LSE, pins 8/9
    'C117': (219.70, 94.30, 0, 'B'),
    'C118': (219.70, 95.50, 0, 'B'),
    'Y101': (216.60, 99.60, 90, 'B'),    # HSE, pins 12/13
    'C115': (219.70, 99.00, 0, 'B'),
    'C116': (219.70, 100.20, 0, 'B'),
    'C108': (221.80, 95.00, 0, 'B'),     # VBAT 6
    'C101': (221.80, 97.60, 0, 'B'),     # VDD 11
    'C114': (221.80, 99.60, 0, 'B'),     # NRST 14
    'C111': (216.40, 103.40, 90, 'B'),    # VREF+ 21, 1u
    'C112': (217.60, 103.40, 90, 'B'),    # VREF+ 21, 100n
    'C109': (218.80, 103.40, 90, 'B'),    # VDDA 22, 1u
    'C110': (220.00, 103.40, 90, 'B'),    # VDDA 22, 100n
    'R9':   (221.40, 103.40, 90, 'B'),    # radio CS pull-up
    'R104': (223.00, 103.40, 90, 'B'),   # I2C3 SCL pull-up
    'R105': (224.20, 103.40, 90, 'B'),   # I2C3 SDA pull-up
    'C107': (224.50, 98.85, 0, 'B'),     # bulk 4.7u
    'C105': (217.40, 92.40, 0, 'B'),     # VDD 100
    'R101': (219.40, 92.40, 0, 'B'),     # BOOT0 pull-down
    'R102': (221.40, 92.40, 0, 'B'),     # user button pull-up
    'C104': (227.40, 92.90, 0, 'B'),     # VDD 75
    'C106': (227.40, 94.10, 0, 'B'),     # VDDUSB 73
    'R80':  (224.00, 108.70, 0, 'B'),    # D3 resistor
    'R5':   (211.20, 93.40, 0, 'B'),     # radio RST pull-up
}
