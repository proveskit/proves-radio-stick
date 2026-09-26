#!/usr/bin/env python3
"""Generate the V3 schematic from the V2 schematic.

Removes the RP2350 / QSPI flash / 12 MHz crystal / 1V1 / BOOTSEL circuitry
from V2 and adds the STM32U585 block, wired by labels to the unchanged radio,
power, USB-C and connector sections. Pin assignments come from
../pinmap/pinmap.csv.

Usage: python3 gen_v3_schematic.py   (run from anywhere; paths are relative
to this file). Overwrites ../proves_radio_stick_V3.kicad_sch.
"""
import csv, math, os, re, uuid

HERE = os.path.dirname(os.path.abspath(__file__))
V3 = os.path.dirname(HERE)
V2_SCH = os.path.join(V3, '..', 'proves_radio_stick_V2', 'proves_radio_stick_V2.kicad_sch')
OUT = os.path.join(V3, 'proves_radio_stick_V3.kicad_sch')
KICAD_SYM = '/Applications/KiCad/KiCad.app/Contents/SharedSupport/symbols'
PROJECT = 'proves_radio_stick_V3'

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
def q(s): return '"' + s + '"'
def uid(): return q(str(uuid.uuid4()))
def num(v): return ('%.4f' % v).rstrip('0').rstrip('.')
def font(): return ['effects', ['font', ['size', '1.27', '1.27']]]
def hidden(): return ['effects', ['font', ['size', '1.27', '1.27']], ['hide', 'yes']]

# ---------------------------------------------------------------- load V2

t = parse(open(V2_SCH).read())
root_uuid = unq(get(t, 'uuid')[1])
libsyms = get(t, 'lib_symbols')

# Regions (mm) cleared of V2 content: RP2350/flash/crystal/1V1 block,
# its 3V3 decoupling row, and the BOOTSEL button chain.
REGIONS = [(10, 15, 228, 182), (190, 15, 282, 45), (203, 190, 222, 245)]
KEEP_TEXT_REGIONS = [REGIONS[2]]  # keep the "RESET" heading

def inr(x, y, regs=REGIONS):
    return any(a <= x <= c and b <= y <= d for a, b, c, d in regs)

def at_of(e):
    a = get(e, 'at'); return float(a[1]), float(a[2])

def ref_of(sym):
    for p in find(sym, 'property'):
        if unq(p[1]) == 'Reference':
            return unq(p[2])

# Wires from the RP2350 pins to the TP1-TP6 junctions cross the region edge.
# Drop them, and the junctions that become plain corners.
TP_JUNCS = {(233.68, 93.98), (238.76, 96.52), (243.84, 99.06),
            (248.92, 101.6), (257.81, 109.22), (262.89, 111.76)}

removed = []
body = []
for e in t:
    if not isinstance(e, list):
        body.append(e); continue
    k = e[0]
    if k == 'symbol':
        x, y = at_of(e)
        if inr(x, y):
            removed.append(ref_of(e)); continue
    elif k in ('label', 'global_label', 'no_connect'):
        if inr(*at_of(e)):
            continue
    elif k == 'junction':
        x, y = at_of(e)
        if inr(x, y) or (x, y) in TP_JUNCS:
            continue
    elif k == 'text':
        x, y = at_of(e)
        if inr(x, y) and not inr(x, y, KEEP_TEXT_REGIONS):
            continue
    elif k in ('wire', 'polyline', 'bus'):
        pts = [(float(p[1]), float(p[2])) for p in find(get(e, 'pts'), 'xy')]
        if any(inr(*p) for p in pts):
            continue
        if k == 'wire' and math.dist(*pts) < 0.1:  # zero-length V2 leftovers
            continue
    body.append(e)
t[:] = body

# J3 breakout nets are renamed after the STM32 pins behind them.
J3_RENAME = {'GPIO%d' % (22 + i): 'J3_IO%d' % (1 + i) for i in range(8)}
for e in find(t, 'global_label'):
    if unq(e[1]) in J3_RENAME:
        e[1] = q(J3_RENAME[unq(e[1])])

def set_prop(sym, name, value):
    for p in find(sym, 'property'):
        if unq(p[1]) == name:
            p[2] = q(value); return
    x, y = at_of(sym)
    sym.append(['property', q(name), q(value), ['at', num(x), num(y), '0'], hidden()])

# USB series resistors: STM32 OTG_FS needs none, so R7/R8 become 0R links.
for sym in find(t, 'symbol'):
    if ref_of(sym) in ('R7', 'R8'):
        set_prop(sym, 'Value', '0')
        set_prop(sym, 'LCSC Part', 'C17168')
    # Same TPS62085 die on the larger reel, which JLC stocks in quantity.
    if ref_of(sym) == 'U2':
        set_prop(sym, 'Value', 'TPS62085RLTR')
        set_prop(sym, 'LCSC Part', 'C130072')

# ---------------------------------------------------------------- lib symbols

def lib_symbol_from(libfile, name, new_name=None):
    lt = parse(open(os.path.join(KICAD_SYM, libfile + '.kicad_sym')).read())
    syms = {unq(s[1]): s for s in find(lt, 'symbol')}
    s = syms[name]
    ext = get(s, 'extends')
    if ext:  # flatten: parent graphics + child properties
        parent = syms[unq(ext[1])]
        pname = unq(parent[1])
        s = [e for e in parent if not (isinstance(e, list) and e[0] == 'property')] + \
            [e for e in s if isinstance(e, list) and e[0] == 'property']
        s[1] = q(name)
        for sub in find(s, 'symbol'):
            sub[1] = q(unq(sub[1]).replace(pname, name, 1))
    s = [e for e in s]
    s[1] = q(libfile + ':' + name)
    return s

for libfile, name in [('MCU_ST_STM32U5', 'STM32U585CIUx'), ('Device', 'Crystal'),
                      ('Connector_Generic', 'Conn_02x07_Odd_Even'),
                      ('Power_Protection', 'USBLC6-2SC6')]:
    libsyms.append(lib_symbol_from(libfile, name))

LIB = {unq(s[1]): s for s in find(libsyms, 'symbol')}

def lib_pins(lib_id):
    out = {}
    for sub in find(LIB[lib_id], 'symbol'):
        for p in find(sub, 'pin'):
            a = get(p, 'at')
            out.setdefault(unq(get(p, 'number')[1]), (float(a[1]), float(a[2]), float(a[3])))
    return out

# ---------------------------------------------------------------- geometry

def pin_xy(sx, sy, rot, px, py):
    r = math.radians(rot)
    xr = px * math.cos(r) - py * math.sin(r)
    yr = px * math.sin(r) + py * math.cos(r)
    return round(sx + xr, 4), round(sy - yr, 4)

def outward(rot, pang):
    """Screen direction (dx, dy) pointing away from the body."""
    a = math.radians(pang + 180 + rot)
    return round(math.cos(a)), -round(math.sin(a))

DIR_ANGLE = {(1, 0): 0, (0, -1): 90, (-1, 0): 180, (0, 1): 270}

# ---------------------------------------------------------------- builders

new = []
pwr_n = [200]

def instances(ref):
    return ['instances', ['project', q(PROJECT),
            ['path', q('/' + root_uuid), ['reference', q(ref)], ['unit', '1']]]]

def symbol(lib_id, ref, value, x, y, rot=0, fp='', lcsc='', ds='~', show_val=True, ref_at=None, val_at=None):
    pins = lib_pins(lib_id)
    rx, ry = ref_at or (x + 2.54, y - 1.27)
    vx, vy = val_at or (x + 2.54, y + 1.27)
    power = ref.startswith('#')
    s = ['symbol', ['lib_id', q(lib_id)], ['at', num(x), num(y), str(rot)], ['unit', '1'],
         ['exclude_from_sim', 'no'], ['in_bom', 'no' if power else 'yes'],
         ['on_board', 'no' if power else 'yes'], ['dnp', 'no'], ['uuid', uid()],
         ['property', '"Reference"', q(ref), ['at', num(rx), num(ry), '0'],
          hidden() if power else ['effects', ['font', ['size', '1.27', '1.27']], ['justify', 'left']]],
         ['property', '"Value"', q(value), ['at', num(vx), num(vy), '0'],
          ['effects', ['font', ['size', '1.27', '1.27']], ['justify', 'left']] if show_val else hidden()],
         ['property', '"Footprint"', q(fp), ['at', num(x), num(y), '0'], hidden()],
         ['property', '"Datasheet"', q(ds), ['at', num(x), num(y), '0'], hidden()]]
    if lcsc:
        s.append(['property', '"LCSC Part"', q(lcsc), ['at', num(x), num(y), '0'], hidden()])
    for n in pins:
        s.append(['pin', q(n), ['uuid', uid()]])
    s.append(instances(ref))
    new.append(s)
    return s

def power(net, x, y, d):
    """Power symbol at (x, y) whose glyph points in screen direction d."""
    base = {'GND': (0, 1), '+3V3': (0, -1), 'VBUS': (0, -1)}[net]
    rot = (DIR_ANGLE[d] - DIR_ANGLE[base]) % 360
    pwr_n[0] += 1
    symbol('power:' + net, '#PWR%04d' % pwr_n[0], net, x, y, rot, show_val=(net != 'GND'),
           val_at=(x + d[0] * 6.35, y + d[1] * 4.445 + (0.635 if d[1] == 0 else 0)))

def wire(x1, y1, x2, y2):
    new.append(['wire', ['pts', ['xy', num(x1), num(y1)], ['xy', num(x2), num(y2)]],
                ['stroke', ['width', '0'], ['type', 'default']], ['uuid', uid()]])

def junction(x, y):
    new.append(['junction', ['at', num(x), num(y)], ['diameter', '0'], ['color', '0', '0', '0', '0'],
                ['uuid', uid()]])

def label(name, x, y, d, glob):
    ang = DIR_ANGLE[d]
    if glob:
        just = 'left' if ang in (0, 90) else 'right'
        new.append(['global_label', q(name), ['shape', 'bidirectional'],
                    ['at', num(x), num(y), str(ang)], ['fields_autoplaced', 'yes'],
                    ['effects', ['font', ['size', '1.27', '1.27']], ['justify', just]], ['uuid', uid()],
                    ['property', '"Intersheetrefs"', '"${INTERSHEET_REFS}"',
                     ['at', num(x), num(y), '0'], hidden()]])
    else:
        just = ['justify', 'left' if ang in (0, 90) else 'right', 'bottom']
        new.append(['label', q(name), ['at', num(x), num(y), str(ang)],
                    ['effects', ['font', ['size', '1.27', '1.27']], just], ['uuid', uid()]])

def text(s, x, y, size=2.54):
    new.append(['text', q(s), ['exclude_from_sim', 'no'], ['at', num(x), num(y), '0'],
                ['effects', ['font', ['size', str(size), str(size)]], ['justify', 'left', 'bottom']],
                ['uuid', uid()]])

def no_connect(x, y):
    new.append(['no_connect', ['at', num(x), num(y)], ['uuid', uid()]])

def part(lib_id, ref, value, x, y, rot=0, fp='', lcsc='', nets=None, stub=2.54, ds='~',
         ref_at=None, val_at=None, ties=()):
    """Place a part and hang a label / power symbol / NC flag off each pin.

    nets: pin -> 'G:NAME' global label, 'L:NAME' local label,
          'P:NET' power symbol on the pin, 'U:NET' power symbol upright at
          the end of a stub, 'NC', or None (left for manual wiring).
    ties: pin pairs joined by a wire (e.g. the two contacts of a switch side).
    """
    symbol(lib_id, ref, value, x, y, rot, fp, lcsc, ds, ref_at=ref_at, val_at=val_at)
    pins = lib_pins(lib_id)
    ends = {}
    for n, spec in (nets or {}).items():
        px, py, pa = pins[n]
        tx, ty = pin_xy(x, y, rot, px, py)
        d = outward(rot, pa)
        ends[n] = (tx, ty)
        if spec is None:
            continue
        if spec == 'NC':
            no_connect(tx, ty); continue
        kind, name = spec.split(':', 1)
        if kind == 'P':
            power(name, tx, ty, d); continue
        ex, ey = tx + d[0] * stub, ty + d[1] * stub
        wire(tx, ty, ex, ey)
        if kind == 'U':
            power(name, ex, ey, (0, 1) if name == 'GND' else (0, -1)); continue
        label(name, ex, ey, d, kind == 'G')
    for a, b in ties:
        pa, pb = pins[a], pins[b]
        wire(*pin_xy(x, y, rot, pa[0], pa[1]), *pin_xy(x, y, rot, pb[0], pb[1]))
    return ends

C0402 = 'Capacitor_SMD:C_0402_1005Metric'
R0402 = 'Resistor_SMD:R_0402_1005Metric'

def cap(ref, val, lcsc, x, y, top, bot='P:GND'):
    part('Device:C', ref, val, x, y, fp=C0402, lcsc=lcsc, nets={'1': top, '2': bot})

def res(ref, val, x, y, top, bot):
    part('Device:R', ref, val, x, y, fp=R0402, lcsc='C25744' if val == '10k' else '',
         nets={'1': top, '2': bot})

# ---------------------------------------------------------------- STM32U585

LOCAL = {'OSC_IN', 'OSC_OUT', 'OSC32_IN', 'OSC32_OUT', 'BOOT0', 'USER_BTN', 'VCAP'}
PIN_NUM = {}
for sub in find(LIB['MCU_ST_STM32U5:STM32U585CIUx'], 'symbol'):
    for p in find(sub, 'pin'):
        PIN_NUM.setdefault(unq(get(p, 'name')[1]), unq(get(p, 'number')[1]))

mcu_nets = {}
with open(os.path.join(V3, 'pinmap', 'pinmap.csv')) as f:
    for row in csv.DictReader(f):
        net = row['net']
        net = {'USART1_TX': 'TX', 'USART1_RX': 'RX', 'SWO': 'SWO'}.get(net, net)
        mcu_nets[PIN_NUM[row['pin']]] = ('L:' if net in LOCAL else 'G:') + net
mcu_nets['7'] = 'G:~{RESET}'
mcu_nets['22'] = 'L:VCAP'

UX, UY = 119.38, 101.6
ends = part('MCU_ST_STM32U5:STM32U585CIUx', 'U1', 'STM32U585CIU6', UX, UY,
            fp='Package_DFN_QFN:QFN-48-1EP_7x7mm_P0.5mm_EP5.6x5.6mm_ThermalVias',
            lcsc='C5271026', ds='https://www.st.com/resource/en/datasheet/stm32u585ci.pdf',
            ref_at=(UX + 5.08, UY + 43.18), val_at=(UX + 5.08, UY + 45.72),
            nets={**mcu_nets, **{n: None for n in ('1', '9', '24', '36', '48', '8', '23', '35', '47', '49')}})

# Supply pins: VBAT, VDD x3 and VDDA share one +3V3 bus above the chip.
top = sorted({ends[n][0] for n in ('1', '24', '36', '48', '9')})
ty = ends['1'][1]; by = ty - 5.08
for x in top:
    wire(x, ty, x, by)
for a, b in zip(top, top[1:]):
    wire(a, by, b, by)
for x in top[:-1]:
    junction(x, by)
wire(top[0] - 5.08, by, top[0], by)
power('+3V3', top[0] - 5.08, by, (0, -1))
# Ground pins: VSS x3 + EP stack on one pin position, VSSA beside it.
bot = sorted({ends[n][0] for n in ('23', '8')})
gy = ends['23'][1]; gb = gy + 5.08
for x in bot:
    wire(x, gy, x, gb)
wire(bot[0], gb, bot[1], gb)
power('GND', bot[0], gb, (0, 1))

# Decoupling (place each cap at its pin in layout).
text('STM32U585 decoupling', 55.88, 19.05)
text('C101-C103 at VDD 24/36/48, C105 at VBAT, C106/C107 at VDDA, C108 at VCAP', 55.88, 41.91, 1.27)
DEC = [('C101', '100n', 'C1525', 'P:+3V3'), ('C102', '100n', 'C1525', 'P:+3V3'),
       ('C103', '100n', 'C1525', 'P:+3V3'), ('C104', '4.7u', 'C23733', 'P:+3V3'),
       ('C105', '100n', 'C1525', 'P:+3V3'), ('C106', '1u', 'C52923', 'P:+3V3'),
       ('C107', '100n', 'C1525', 'P:+3V3'), ('C108', '4.7u', 'C23733', 'L:VCAP'),
       ('C109', '100n', 'C1525', 'G:~{RESET}')]
for i, (ref, val, lcsc, topnet) in enumerate(DEC):
    cap(ref, val, lcsc, 60.96 + 12.7 * i, 31.75, topnet)

text('STM32U585CIU6', 106.68, 49.53)

# HSE 16 MHz (CL 9 pF -> 12 pF load caps).
text('HSE 16 MHz', 25.4, 52.07)
part('Device:Crystal_GND24', 'Y101', '16MHz', 40.64, 62.23,
     fp='Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm', lcsc='C13738',
     ref_at=(46.99, 66.04), val_at=(46.99, 68.58),
     nets={'1': 'L:OSC_IN', '3': 'L:OSC_OUT', '2': 'P:GND', '4': 'P:GND'})
cap('C110', '12p', 'C1547', 30.48, 77.47, 'L:OSC_IN')
cap('C111', '12p', 'C1547', 50.8, 77.47, 'L:OSC_OUT')

# LSE 32.768 kHz (CL 7 pF -> 10 pF load caps).
text('LSE 32.768 kHz', 25.4, 91.44)
part('Device:Crystal', 'Y102', '32.768kHz', 40.64, 99.06,
     fp='Crystal:Crystal_SMD_3215-2Pin_3.2x1.5mm', lcsc='C97604',
     ref_at=(36.83, 104.14), val_at=(36.83, 106.68),
     nets={'1': 'L:OSC32_IN', '2': 'L:OSC32_OUT'})
cap('C112', '10p', 'C32949', 30.48, 111.76, 'L:OSC32_IN')
cap('C113', '10p', 'C32949', 50.8, 111.76, 'L:OSC32_OUT')

# BOOT0 button (ROM USB DFU) and user button (PC13 / WKUP2).
SW = 'Adafruit ItsyBitsy RP2040-eagle-import:SWITCH_TACT_SMT4.6X2.8'
SWFP = 'FC_DEV_BOARD:BTN_KMR2_4.6X2.8'
text('BOOT0 (hold + reset = USB DFU)', 25.4, 125.73)
part(SW, 'SW1', 'KMR2', 40.64, 134.62, fp=SWFP, lcsc='C72443',
     nets={'A': 'U:+3V3', "A'": None, 'B': 'L:BOOT0', "B'": None},
     ties=(('A', "A'"), ('B', "B'")), ref_at=(35.56, 130.81), val_at=(41.91, 130.81))
res('R101', '10k', 60.96, 139.7, 'L:BOOT0', 'P:GND')
text('User button', 25.4, 151.13)
part(SW, 'SW3', 'KMR2', 40.64, 160.02, fp=SWFP, lcsc='C72443',
     nets={'A': 'U:GND', "A'": None, 'B': 'L:USER_BTN', "B'": None},
     ties=(('A', "A'"), ('B', "B'")), ref_at=(35.56, 156.21), val_at=(41.91, 156.21))
res('R102', '10k', 60.96, 165.1, 'P:+3V3', 'L:USER_BTN')

# STDC14 debug header (STLINK-V3MINIE). Pins 3-12 are the MIPI-10 layout.
text('Debug: STDC14 (STLINK-V3MINIE)', 162.56, 49.53)
text('Pins 13/14 = T_VCP_RX/T_VCP_TX (target RX/TX). J4 shares USART1.', 162.56, 80.01, 1.27)
part('Connector_Generic:Conn_02x07_Odd_Even', 'J5', 'STDC14', 180.34, 64.77,
     fp='Connector_PinHeader_1.27mm:PinHeader_2x07_P1.27mm_Vertical', lcsc='C22438122',
     ref_at=(177.8, 53.34), val_at=(184.15, 53.34),
     nets={'1': 'NC', '2': 'NC', '3': None, '4': 'G:SWDIO', '5': None, '6': 'G:SWCLK',
           '7': None, '8': 'G:SWO', '9': 'NC', '10': 'NC', '11': None,
           '12': 'G:~{RESET}', '13': 'G:RX', '14': 'G:TX'})
jx = 180.34 - 5.08  # odd-row pin tips
y3, y5, y7, y11 = 64.77 - 5.08, 64.77 - 2.54, 64.77, 64.77 + 5.08
wire(jx, y3, jx - 7.62, y3)
power('+3V3', jx - 7.62, y3, (-1, 0))
for yy in (y5, y7, y11):
    wire(jx, yy, jx - 2.54, yy)
wire(jx - 2.54, y5, jx - 2.54, y11)
junction(jx - 2.54, y7)
wire(jx - 2.54, y7, jx - 7.62, y7)
power('GND', jx - 7.62, y7, (-1, 0))

# USB ESD on the connector side of R7/R8.
text('USB ESD', 162.56, 97.79)
part('Power_Protection:USBLC6-2SC6', 'U4', 'USBLC6-2SC6', 180.34, 111.76, stub=5.08,
     ref_at=(182.88, 104.14), val_at=(182.88, 121.92),
     fp='Package_TO_SOT_SMD:SOT-23-6', lcsc='C7519',
     ds='https://www.st.com/resource/en/datasheet/usblc6-2.pdf',
     nets={'1': 'G:USB_D-', '6': 'G:USB_D-', '3': 'G:USB_D+', '4': 'G:USB_D+',
           '5': 'P:VBUS', '2': 'P:GND'})

# USB-C CC sense. V2 routes J12.CC1 -> R26 pin 2 at (64.77, 194.31) and
# J12.CC2 -> corner (63.5, 201.93) -> R27 pin 2. Hang labels off both.
v2_ends = {(float(p[1]), float(p[2])) for w in find(t, 'wire') for p in find(get(w, 'pts'), 'xy')}
assert (64.77, 194.31) in v2_ends and (63.5, 201.93) in v2_ends, 'V2 CC routing moved'
wire(64.77, 194.31, 64.77, 189.23)
junction(64.77, 194.31)
label('USB_CC1_SENSE', 64.77, 189.23, (0, -1), True)
# Move R26/R27's GND symbol right so the CC2 label clears it.
for sym in find(t, 'symbol'):
    if ref_of(sym) == '#PWR090':
        assert at_of(sym) == (78.74, 199.39), 'V2 CC GND moved'
        for e in [sym] + find(sym, 'property'):
            a = get(e, 'at'); a[1] = num(float(a[1]) + 13.97); a[2] = num(float(a[2]) - 1.27)
t[:] = [e for e in t if not (isinstance(e, list) and e[0] == 'wire' and
        [(float(p[1]), float(p[2])) for p in find(get(e, 'pts'), 'xy')] == [(78.74, 198.12), (78.74, 199.39)])]
wire(78.74, 198.12, 92.71, 198.12)
wire(63.5, 201.93, 68.58, 201.93)
junction(63.5, 201.93)
label('USB_CC2_SENSE', 68.58, 201.93, (1, 0), True)

# ---------------------------------------------------------------- finish

# Drop lib symbols nothing uses any more.
used = {unq(get(s, 'lib_id')[1]) for s in find(t, 'symbol') + find(new, 'symbol')}
used |= {unq(get(s, 'lib_name')[1]) for s in find(t, 'symbol') if get(s, 'lib_name')}
libsyms[:] = [e for e in libsyms if not (isinstance(e, list) and e[0] == 'symbol' and unq(e[1]) not in used)]

tb = ['title_block', ['title', '"PROVES Radio Stick V3"'], ['date', '"2026-09-26"'],
      ['rev', '"3.0"'], ['company', '"PROVES Kit / Open Source Space Foundation"'],
      ['comment', '1', '"STM32U585CIU6 + EByte E22-400M30S"']]
old_tb = get(t, 'title_block')
if old_tb:
    t.remove(old_tb)
idx = t.index(get(t, 'paper')) + 1
t.insert(idx, tb)

si = t.index(get(t, 'sheet_instances'))
t[si:si] = new

open(OUT, 'w').write(dump(t) + '\n')
print('removed:', ' '.join(sorted(r for r in removed if not r.startswith('#'))))
print('added %d items -> %s' % (len(new), OUT))
