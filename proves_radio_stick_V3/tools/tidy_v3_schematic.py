#!/usr/bin/env python3
"""Lay out the generated V3 schematic for reading (step 1b, after gen_v3_schematic.py).

gen_v3_schematic.py keeps V2's placement and drops the STM32 block into the
space the RP2350 left, so blocks end up wherever there was room. This script
moves each functional block to a fixed place on the sheet, draws a titled frame
round it and adds design notes. It never changes the circuit:

* Items are moved as rigid "drawing clusters": every wire, pin, label, junction
  and no-connect that touch each other move together, so no connection breaks.
  A cluster that spans two blocks stops the script.
* Symbol UUIDs and every field value stay as they are (the PCB links to them).
* Only text, frames and positions change. Check with
  `kicad-cli sch export netlist` before and after: the nets must be identical.

Usage: python3 tidy_v3_schematic.py   (edits ../proves_radio_stick_V3.kicad_sch
in place; refuses to run twice on the same file).
"""
import math, os, re, sys, uuid

HERE = os.path.dirname(os.path.abspath(__file__))
SCH = os.path.join(os.path.dirname(HERE), 'proves_radio_stick_V3.kicad_sch')
MARK = 'Sheet layout: tools/tidy_v3_schematic.py'

# ---------------------------------------------------------------- s-expr

TOK = re.compile(r'\(|\)|"(?:[^"\\]|\\.)*"|[^\s()]+')

def parse(s):
    st = [[]]
    for m in TOK.finditer(s):
        t = m.group()
        if t == '(':
            st.append([])
        elif t == ')':
            x = st.pop(); st[-1].append(x)
        else:
            st[-1].append(t)
    return st[0][0]

def dump(x, ind=0):
    head = [e for e in x if not isinstance(e, list)]
    kids = [e for e in x if isinstance(e, list)]
    s = '\t' * ind + '(' + ' '.join(head)
    if not kids:
        return s + ')'
    return s + '\n' + '\n'.join(dump(k, ind + 1) for k in kids) + '\n' + '\t' * ind + ')'

def find(x, key): return [e for e in x if isinstance(e, list) and e and e[0] == key]
def get(x, key):
    r = find(x, key); return r[0] if r else None
def unq(s): return s[1:-1] if s.startswith('"') else s
def q(s): return '"' + s.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n') + '"'
def num(v): return ('%.4f' % v).rstrip('0').rstrip('.')
def uid(): return q(str(uuid.uuid4()))
def at_of(e):
    a = get(e, 'at'); return float(a[1]), float(a[2])
def prop(sym, name):
    for p in find(sym, 'property'):
        if unq(p[1]) == name:
            return unq(p[2])

# ---------------------------------------------------------------- geometry

def lib_pins(libsyms):
    out = {}
    for s in find(libsyms, 'symbol'):
        pins = []
        for sub in find(s, 'symbol'):
            for p in find(sub, 'pin'):
                a = get(p, 'at')
                pins.append((float(a[1]), float(a[2])))
        out[unq(s[1])] = pins
    return out

def sym_pins(sym, pins):
    sx, sy = at_of(sym)
    r = math.radians(float(get(sym, 'at')[3]))
    lid = unq((get(sym, 'lib_name') or get(sym, 'lib_id'))[1])
    res = []
    for px, py in pins[lid]:
        assert not get(sym, 'mirror'), 'mirrored symbols not handled'
        xr = px * math.cos(r) - py * math.sin(r)
        yr = px * math.sin(r) + py * math.cos(r)
        res.append((round(sx + xr, 3), round(sy - yr, 3)))
    return res

def wire_pts(e):
    return [(float(p[1]), float(p[2])) for p in find(get(e, 'pts'), 'xy')]

def on_seg(p, a, b, eps=0.01):
    (x, y), (x1, y1), (x2, y2) = p, a, b
    if abs((x2 - x1) * (y - y1) - (y2 - y1) * (x - x1)) > eps * max(1, math.dist(a, b)):
        return False
    return min(x1, x2) - eps <= x <= max(x1, x2) + eps and min(y1, y2) - eps <= y <= max(y1, y2) + eps

MOVABLE = ('symbol', 'wire', 'polyline', 'bus', 'label', 'global_label', 'hierarchical_label',
           'junction', 'no_connect', 'text', 'text_box', 'rectangle')

def translate(e, dx, dy):
    """Move one top-level item (and all its fields) by (dx, dy)."""
    def mv(a, ix=1):
        a[ix] = num(float(a[ix]) + dx); a[ix + 1] = num(float(a[ix + 1]) + dy)
    k = e[0]
    if k in ('wire', 'polyline', 'bus'):
        for p in find(get(e, 'pts'), 'xy'):
            mv(p)
        return
    if k in ('rectangle', 'text_box'):
        for key in ('start', 'end', 'at'):
            if get(e, key):
                mv(get(e, key))
        return
    mv(get(e, 'at'))
    for p in find(e, 'property'):
        mv(get(p, 'at'))

def connection_clusters(items, pins):
    """Union-find over items that touch electrically or graphically."""
    parent = list(range(len(items)))
    def root(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]; i = parent[i]
        return i
    def join(i, j): parent[root(i)] = root(j)
    points = {}   # rounded point -> item indices
    segs = []     # (item index, a, b)
    for i, e in enumerate(items):
        k = e[0]
        if k == 'symbol':
            pts = sym_pins(e, pins)
        elif k in ('wire', 'bus'):
            pts = wire_pts(e)
            segs += [(i, a, b) for a, b in zip(pts, pts[1:])]
        elif k in ('label', 'global_label', 'hierarchical_label', 'junction', 'no_connect'):
            pts = [at_of(e)]
        else:
            continue
        for p in pts:
            points.setdefault((round(p[0], 2), round(p[1], 2)), []).append(i)
    for idx in points.values():
        for j in idx[1:]:
            join(idx[0], j)
    for i, a, b in segs:
        for p, idx in points.items():
            if on_seg(p, a, b):
                for j in idx:
                    join(i, j)
    return [root(i) for i in range(len(items))]

# ---------------------------------------------------------------- extents

CHAR = 0.8  # stroke-font advance per character, in units of the font size (rough)

def text_box(x, y, s, size, ang, just, vjust='center'):
    """Rough box of a text item: [(x0, y0), (x1, y1)]."""
    lines = s.split('\n')
    w = max(len(l) for l in lines) * size * CHAR
    h = len(lines) * size * 1.6
    if 'left' in just:
        a0, a1 = 0, w
    elif 'right' in just:
        a0, a1 = -w, 0
    else:
        a0, a1 = -w / 2, w / 2
    if vjust == 'top':
        b0, b1 = 0, h
    elif vjust == 'bottom':
        b0, b1 = -h, 0
    else:
        b0, b1 = -h / 2, h / 2
    if int(float(ang)) % 180 == 90:  # vertical text reads upward
        return [(x + b0, y - a1), (x + b1, y - a0)]
    return [(x + a0, y + b0), (x + a1, y + b1)]

def effects_of(e):
    eff = get(e, 'effects')
    size = float(get(get(eff, 'font'), 'size')[1]) if eff is not None else 1.27
    j = get(eff, 'justify') if eff is not None else None
    just = j[1:] if j else []
    hid = (eff is not None and get(eff, 'hide') is not None) or get(e, 'hide') is not None
    return size, just, hid

def lib_graphics(libsyms):
    out = {}
    for s in find(libsyms, 'symbol'):
        pts = []
        def walk(x):
            for c in x:
                if not isinstance(c, list) or not c:
                    continue
                if c[0] in ('start', 'end', 'xy', 'mid'):
                    pts.append((float(c[1]), float(c[2])))
                elif c[0] == 'circle':
                    cx, cy = map(float, get(c, 'center')[1:3]); r = float(get(c, 'radius')[1])
                    pts.extend([(cx - r, cy - r), (cx + r, cy + r)])
                elif c[0] == 'pin':
                    a = get(c, 'at'); pts.append((float(a[1]), float(a[2])))
                elif c[0] in ('symbol', 'rectangle', 'polyline', 'pts', 'arc'):
                    walk(c)
        walk(s)
        out[unq(s[1])] = pts
    return out

def extent(e, gfx):
    k = e[0]
    pts = []
    if k == 'symbol':
        sx, sy = at_of(e)
        r = math.radians(float(get(e, 'at')[3]))
        lid = unq((get(e, 'lib_name') or get(e, 'lib_id'))[1])
        for px, py in gfx[lid]:
            pts.append((sx + px * math.cos(r) - py * math.sin(r), sy - (px * math.sin(r) + py * math.cos(r))))
        for p in find(e, 'property'):
            size, just, hid = effects_of(p)
            if not hid and unq(p[2]):
                a = get(p, 'at')
                pts += text_box(float(a[1]), float(a[2]), unq(p[2]), size, a[3], just)
    elif k in ('wire', 'polyline', 'bus'):
        pts = wire_pts(e)
    elif k in ('label', 'global_label', 'hierarchical_label'):
        x, y = at_of(e); ang = get(e, 'at')[3]
        size, just, _ = effects_of(e)
        s = unq(e[1])
        n = len(re.sub(r'[~{}]', '', s)) + (3 if k != 'label' else 0)
        bx = text_box(x, y, 'x' * n, size, ang, just or ['left'], 'bottom' if k == 'label' else 'center')
        pts += bx
    elif k in ('junction', 'no_connect'):
        x, y = at_of(e); pts = [(x - 0.7, y - 0.7), (x + 0.7, y + 0.7)]
    elif k == 'text':
        x, y = at_of(e); size, just, _ = effects_of(e)
        vj = 'top' if 'top' in just else 'bottom' if 'bottom' in just else 'center'
        pts = text_box(x, y, unq(e[1]).replace('\\n', '\n'), size, get(e, 'at')[3], just, vj)
    elif k == 'rectangle':
        pts = [tuple(map(float, get(e, 'start')[1:3])), tuple(map(float, get(e, 'end')[1:3]))]
    return pts

def bbox(pts):
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return min(xs), min(ys), max(xs), max(ys)

# ---------------------------------------------------------------- layout

G = 1.27  # every offset is a whole number of 50 mil grid steps

# Parts of the generated sheet, by select box (generated-sheet mm). A drawing
# cluster belongs to the part whose box holds any of its anchor points.
PARTS = {
    'usbc':    (12, 183, 112, 245),   # J12, CC resistors R26/R27, CC sense labels
    'esd':     (155, 95, 215, 128),   # U4 USBLC6
    'buck':    (285, 12, 380, 52),    # U2 TPS62085, L1, R3/R4, C14/C15
    'rail':    (285, 53, 400, 92),    # U19 TPS22918, FB1, C4-C6, C79/C80, R95
    'decoup':  (12, 14, 84, 50),      # C101-C114
    'hse':     (20, 60, 60, 95),
    'lse':     (20, 98, 60, 130),
    'boot0':   (20, 133, 70, 158),
    'button':  (20, 159, 70, 183),
    'mcu':     (84.5, 20, 160, 188),
    'stdc14':  (155, 45, 215, 78),
    'swd':     (295, 215, 320, 232),  # J22 JST-SH SWD
    'tps':     (225, 88, 271, 112),   # TP1-TP6 (DNP) on the SPI/IRQ labels
    'radio':   (271, 99, 370, 166),   # U3 E22, pull-ups, C7/L2 match, J2
    'reset':   (215, 195, 238, 245),  # SW2
    'leds':    (240, 205, 265, 245),  # D1 Firmware_Active, D3 power
    'uled':    (155, 133, 195, 158),  # D2 user LED
    'i2c':     (155, 159, 195, 185),  # R104/R105
    'j3':      (340, 240, 400, 300),
    'holes':   (60, 255, 100, 290),
}
# Generated-sheet items the tidy layout drops: every old heading and note
# (rewritten below), a junction that sits on nothing and a stray V2 dot
# (a filled circle graphic that landed inside the MCU body).
DROP_ALL_TEXT = True
STRAY_JUNCTIONS = {(269.24, 186.69)}

# ---------------------------------------------------------------- the sheet

PAPER, PAGE = 'A3', (420, 297)
TITLE_BLOCK = (298, 250)  # top-left corner of KiCad's title block on A3
TITLE_BLOCK_FIELDS = [
    ['title', '"PROVES Radio Stick V3"'], ['date', '"2026-10-30"'], ['rev', '"3.0"'],
    ['company', '"PROVES Kit / Open Source Space Foundation"'],
    ['comment', '3', '"STM32U575VIT6 (LQFP-100) USB LoRa stick, EByte E22-400M30S 30 dBm"'],
    ['comment', '2', '"Power in (top row) -> MCU -> radio -> antenna. Blocks join by net label."'],
    ['comment', '1', '"Pin map: pinmap/pinmap.csv (source of truth), pinmap/README.md"'],
]

# (frame title, [(part, x, y) = where the part's top-left goes],
#  [(note, part or 'part^' (its bottom) or '@' (sheet mm), dx, dy, font size)])
H = 1.5  # sub-heading size; notes at 1.5 and up are drawn bold
LAYOUT = [
    ('1  USB-C INPUT AND ESD (J12, U4)', [('usbc', 17, 22), ('esd', 92, 30)], [
        ('USB 2.0 full speed, 5 V.\nR26/R27 5.1k on CC1/CC2 = sink.\n'
         'PB1/PB2 (ADC) read CC for the\nhost current limit:\n'
         '  0.25-0.61 V  default USB\n  0.70-1.16 V  1.5 A\n  1.31-2.04 V  3.0 A\n'
         '30 dBm TX (~650 mA from VBUS)\nneeds a 1.5 A USB-C host.\n\n'
         'U4 USBLC6-2SC6 ESD sits next\nto J12. D+/D- run straight to\n'
         'PA12/PA11; no series resistors.', 'esd^', 0, 3.81, 1.27)]),
    ('2  3.3 V BUCK (U2)', [('buck', 147, 22)], [
        ('TPS62085 (3 A) makes +3V3 from VBUS for the MCU,\n'
         'LEDs, J3 and pull-ups.\nVout = 0.8 V x (1 + R4/R3) = 3.32 V.', 'buck^', 0, 3.81, 1.27)]),
    ('3  RADIO 5 V SWITCH (U19)', [('rail', 237, 22)], [
        ('RF_VCC = VBUS via FB1 and load switch U19 (>= 5 V for 30 dBm).\n'
         'CT 1 nF -> 2.9 ms ramp, 0.19 A inrush into 110 uF.\n'
         'ON = RF_PWR_EN (PE2). R95 to +3V3 = radio ON by default;\n'
         'move R95 to GND for default OFF.', 'rail^', 0, 3.81, 1.27)]),
    ('4  MCU SUPPORT', [('decoup', 17, 112), ('hse', 17, 168), ('lse', 53, 168),
                        ('boot0', 17, 214), ('button', 53, 214)], [
        ('Decoupling (place each cap at its pin)', 'decoup', 0, -3.81, H),
        ('C101-C105 VDD 11/28/50/75/100, C106 VDDUSB 73,\nC107 4.7u bulk, C108 VBAT 6, '
         'C109/C110 VDDA 22,\nC111/C112 VREF+ 21, C113 VCAP 48 (LDO), C114 NRST 14', 'decoup^', 0, 1.27, 1.27),
        ('HSE 16 MHz (PH0/PH1)', 'hse', 0, -3.81, H),
        ('LSE 32.768 kHz (RTC)', 'lse', 0, -3.81, H),
        ('HSE CL 9 pF -> 12 pF caps; LSE CL 7 pF -> 10 pF.', 'hse^', 0, 6.35, 1.27),
        ('BOOT0 (SW1)', 'boot0', 0, -3.81, H),
        ('User button (SW3)', 'button', 0, -3.81, H),
        ('BOOT0: hold SW1, press RESET -> ROM USB DFU bootloader.\n'
         'SW3 on PC13 (WKUP2), active low: can wake from Standby.', 'button^', -36, 1.27, 1.27)]),
    ('5  MCU (U1)', [('mcu', 104, 112)], [
        ('STM32U575VIT6, LQFP-100. Flight part STM32U5A5VJT6 fits the same\n'
         'footprint; never fit a Q (SMPS) part. Pins: pinmap/pinmap.csv.\n'
         'The 46 unused I/O are NC-flagged and free for bodge wires.', 'mcu^', -2.54, 2.54, 1.27)]),
    ('6  RADIO (U3 E22-400M30S) AND ANTENNA (J2)', [('radio', 198, 112), ('tps', 198, 195)], [
        ('SPI1 + BUSY (PB9) + DIO1 IRQ (PB8).\nR11/R12 hold RXEN/TXEN low (PA and\n'
         'LNA off) until firmware drives them.\nR14/R15 DNP: pull-ups would back-power\n'
         'the switched-off radio. TP1-TP7 DNP.\n\n'
         'RF_ANT: 50 Ohm microstrip, 0.36 mm F.Cu\nover In1 GND, 0.2104 mm er 4.5\n'
         '(JLC04161H-7628), no vias, >= 0.5 mm\npour gap. E22 VCC 2.5-5.5 V\n'
         '(>= 5.0 V for 30 dBm), TX 650 mA.', 'tps', 58, -2.54, 1.27)]),
    ('7  DEBUG (J5, J22)', [('stdc14', 346, 22), ('swd', 346, 52)], [
        ('J5 STDC14 fits STLINK-V3MINIE.\nPins 13/14 = T_VCP_RX/T_VCP_TX:\n'
         'USART1 PA9 TX / PA10 RX.\nJ22 JST-SH: SWD only (no SWO).', 'swd^', 0, 3.81, 1.27)]),
    ('8  J3 BREAKOUT (screw terminal)', [('j3', 320, 112), ('i2c', 375, 112)], [
        ('I2C3 pull-ups', 'i2c', 0, -3.81, H),
        ('3.3 V logic only: J3_IO1-8 go straight to MCU pins\n'
         '(no buffer or protection). IO3/IO4 = I2C3 SCL/SDA,\n'
         'IO5-IO8 = SPI2. Full map: pinmap/README.md.', 'j3^', 0, 3.81, 1.27)]),
    ('9  RESET AND LEDS', [('reset', 320, 178), ('leds', 340, 178), ('uled', 370, 178)], [
        ('SW2 pulls ~{RESET} (NRST) low. D3 = +3V3 power,\nD1 = Firmware_Active (PB0), D2 = USER_LED (PC6).',
         'leds^', -20, 3.81, 1.27)]),
    ('10  MOUNTING', [('holes', 198, 243)], []),
]

# Field and label touch-ups, in generated-sheet coordinates (they move with
# their part). Field angles are in the symbol's own frame, as KiCad stores them.
# ref: {field: (x, y, angle, justify)}
FIELDS = {
    'Y101': {'Reference': (43.18, 65.405, 0, 'left'), 'Value': (43.18, 67.945, 0, 'left')},
    'Y102': {'Reference': (38.1, 101.6, 0, 'left'), 'Value': (38.1, 104.14, 0, 'left')},
    'SW1': {'Reference': (35.56, 151.13, 0, 'left'), 'Value': (41.91, 151.13, 0, 'left')},
    'SW3': {'Reference': (35.56, 176.53, 0, 'left'), 'Value': (41.91, 176.53, 0, 'left')},
    'D2': {'Reference': (184.15, 146.05, 90, 'left'), 'Value': (184.15, 148.59, 90, 'left')},
    'SW2': {'Reference': (226.06, 228.6, 90, 'right'), 'Value': (226.06, 231.14, 90, 'right')},
    'R26': {'Reference': (66.04, 192.405, 0, 'right'), 'Value': (74.93, 192.405, 0, 'right')},
    'R27': {'Reference': (80.01, 196.85, 0, 'left'), 'Value': (85.09, 196.85, 0, 'left')},
    '#PWR0201': {'Value': (83.82, 50.8, 90, 'left')},   # VREF+ +3V3, read sideways before
}
FIELD_SIZE = {'R26': 1.27, 'R27': 1.27}  # V2's 1.778 mm fields, now the sheet's 1.27 mm
# Extra moves for single clusters inside a part, by a symbol in them: the LSE
# load caps drop clear of the crystal's labels.
NUDGE = {'C117': (0, 5.08), 'C118': (0, 5.08)}
# Global labels turned to read sideways (same connection point): USB_D-/+ off
# J12 no longer stand across the CC2 wire.
TURN = {('USB_D-', 66.04, 209.55): 0, ('USB_D+', 66.04, 212.09): 0}

def touch_up(t):
    for sym in find(t, 'symbol'):
        ref = prop(sym, 'Reference')
        for p in find(sym, 'property'):
            name = unq(p[1])
            if ref in FIELD_SIZE and name in ('Reference', 'Value'):
                f = get(get(p, 'effects'), 'font')
                get(f, 'size')[1:3] = [num(FIELD_SIZE[ref])] * 2
            if name in FIELDS.get(ref, {}):
                x, y, ang, just = FIELDS[ref][name]
                p[p.index(get(p, 'at'))] = ['at', num(x), num(y), str(ang)]
                eff = get(p, 'effects')
                eff[:] = [e for e in eff if not (isinstance(e, list) and e[0] == 'justify')] + [['justify', just]]
        if ref in FIELDS and get(sym, 'fields_autoplaced'):
            sym.remove(get(sym, 'fields_autoplaced'))
    for lab in find(t, 'global_label'):
        key = (unq(lab[1]),) + at_of(lab)
        if key in TURN:
            get(lab, 'at')[3] = str(TURN[key])
            eff = get(lab, 'effects')
            eff[eff.index(get(eff, 'justify'))] = ['justify', 'left' if TURN[key] in (0, 90) else 'right']

def assign(items, cl):
    """Map item index -> part name. Exits if a drawing cluster spans two parts."""
    part_of_cluster, out = {}, {}
    for i, e in enumerate(items):
        if e[0] == 'text':
            continue
        pts = wire_pts(e) if e[0] in ('wire', 'polyline', 'bus') else [at_of(e)]
        for p in pts:
            for name, box in PARTS.items():
                if box[0] <= p[0] <= box[2] and box[1] <= p[1] <= box[3]:
                    if part_of_cluster.setdefault(cl[i], name) != name:
                        sys.exit('cluster spans parts %s and %s at %s' % (part_of_cluster[cl[i]], name, p))
    for i in range(len(items)):
        if cl[i] in part_of_cluster:
            out[i] = part_of_cluster[cl[i]]
    return out

def main(argv):
    src = open(SCH).read()
    if MARK in src:
        sys.exit('already tidied: run gen_v3_schematic.py first')
    t = parse(src)
    libsyms = get(t, 'lib_symbols')
    pins, gfx = lib_pins(libsyms), lib_graphics(libsyms)
    # drop old headings/notes and stray junctions
    t[:] = [e for e in t if not (isinstance(e, list) and (
        (e[0] == 'text' and DROP_ALL_TEXT) or e[0] == 'circle' or
        (e[0] == 'junction' and at_of(e) in STRAY_JUNCTIONS)))]
    touch_up(t)
    items = [e for e in t if isinstance(e, list) and e[0] in MOVABLE]
    cl = connection_clusters(items, pins)
    part = assign(items, cl)
    lost = [items[i] for i in range(len(items)) if i not in part]
    if lost:
        sys.exit('items in no part: %s' % [(e[0], dump(get(e, 'at') or get(e, 'pts'))) for e in lost])
    boxes = {}
    for i, name in part.items():
        boxes.setdefault(name, []).extend(extent(items[i], gfx))
    boxes = {n: bbox(p) for n, p in boxes.items()}
    if '--report' in argv:
        for n, b in boxes.items():
            print('%-8s %6.1f %6.1f %6.1f %6.1f   w %5.1f h %5.1f' % (n, *b, b[2] - b[0], b[3] - b[1]))
        return
    # move each part so its box's top-left lands on its layout spot
    moved = {}
    for title, members, notes in LAYOUT:
        for name, x, y in members:
            b = boxes[name]
            dx = round((x - b[0]) / G) * G
            dy = round((y - b[1]) / G) * G
            moved[name] = (b[0] + dx, b[1] + dy, b[2] + dx, b[3] + dy)
            for i, n in part.items():
                if n == name:
                    translate(items[i], dx, dy)
    for ref, (dx, dy) in NUDGE.items():
        c = [cl[i] for i, e in enumerate(items) if e[0] == 'symbol' and prop(e, 'Reference') == ref][0]
        for i, e in enumerate(items):
            if cl[i] == c:
                translate(e, dx, dy)
    missing = set(PARTS) - set(moved)
    assert not missing, 'parts with no layout spot: %s' % missing
    # frames, titles and notes
    new, frames = [], []
    for title, members, notes in LAYOUT:
        pts = [p for name, _x, _y in members for p in (moved[name][:2], moved[name][2:])]
        notes = [note_xy(n, moved) for n in notes]
        for s, x, y, size in notes:
            pts += text_box(x, y, s, size, 0, ['left'], 'top')
        x0, y0, x1, y1 = bbox(pts)
        fr = (math.floor((x0 - 2.54) / G) * G, math.floor((y0 - 7.62) / G) * G,
              math.ceil((x1 + 2.54) / G) * G, math.ceil((y1 + 2.54) / G) * G)
        fr = (fr[0], fr[1], max(fr[2], fr[0] + math.ceil((len(title) * 2.0 * CHAR + 5) / G) * G), fr[3])
        frames.append((title, fr))
        new.append(rect(*fr))
        new.append(text(title, fr[0] + 1.27, fr[1] + 1.27, 2.0, bold=True))
        for s, x, y, size in notes:
            new.append(text(s, x, y, size, bold=size >= 1.5))
    for a in range(len(frames)):
        for b in range(a + 1, len(frames)):
            A, B = frames[a][1], frames[b][1]
            if A[0] < B[2] and B[0] < A[2] and A[1] < B[3] and B[1] < A[3]:
                print('WARNING: frames overlap: %s / %s' % (frames[a][0], frames[b][0]))
    for title, fr in frames:
        if fr[0] < 12 or fr[1] < 12 or fr[2] > PAGE[0] - 12 or fr[3] > PAGE[1] - 12 or \
                (fr[2] > TITLE_BLOCK[0] and fr[3] > TITLE_BLOCK[1]):
            print('WARNING: frame off the page or on the title block: %s %s' % (title, fr))
    new.append(text(MARK, TITLE_BLOCK[0] - 2.54, PAGE[1] - 15.24, 1.27, just='right'))
    get(t, 'paper')[1] = q(PAPER)
    tb = get(t, 'title_block')
    tb[:] = ['title_block'] + TITLE_BLOCK_FIELDS
    si = t.index(get(t, 'sheet_instances'))
    t[si:si] = new
    open(SCH, 'w').write(dump(t) + '\n')
    print('tidied %d items into %d blocks -> %s' % (len(part), len(LAYOUT), SCH))

def note_xy(n, moved):
    """(text, 'part' or 'part^', dx, dy, size): place relative to the moved part's
    top-left corner, or its bottom-left corner with '^'."""
    s, ref, dx, dy, size = n
    if ref == '@':
        return s, dx, dy, size
    b = moved[ref.rstrip('^')]
    y = b[3] if ref.endswith('^') else b[1]
    return s, round((b[0] + dx) / G) * G, round((y + dy) / G) * G, size

def rect(x0, y0, x1, y1):
    return ['rectangle', ['start', num(x0), num(y0)], ['end', num(x1), num(y1)],
            ['stroke', ['width', '0.3'], ['type', 'dash'], ['color', '72', '72', '160', '1']],
            ['fill', ['type', 'none']], ['uuid', uid()]]

def text(s, x, y, size, bold=False, just='left'):
    font = ['font', ['size', num(size), num(size)]]
    if bold:
        font.append(['thickness', num(size * 0.15)]); font.append(['bold', 'yes'])
    return ['text', q(s), ['exclude_from_sim', 'no'], ['at', num(x), num(y), '0'],
            ['effects', font, ['justify', just, 'top']], ['uuid', uid()]]

if __name__ == '__main__':
    main(sys.argv[1:])
