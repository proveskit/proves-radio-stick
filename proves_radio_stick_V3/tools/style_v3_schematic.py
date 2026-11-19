#!/usr/bin/env python3
"""Apply the PROVES schematic style rules (proves-pcb-design skill + Greenberg
"Useful Schematics") to the V3 sheet. Runs after tidy_v3_schematic.py, then
`kicad-cli sch upgrade`. Idempotent. Never changes connectivity: every edit is a
field, a rotation about a power pin, or a label swapped for a power symbol of the
same net name.

  - instances carry this project's name (V2 / FC copies kept their old project)
  - power symbols upright: rails point up, GND points down (Greenberg 2)
  - RF_VCC distributed by a project power symbol, not global labels (Greenberg checklist)
  - value strings with units (100nF, 4.7uF, 12pF), connector Values say their function
  - MPN on every connector and IC
  - each rail's source note carries (min, typ, max) V @ (min, typ, max) A (Greenberg 11)

Usage: python3 style_v3_schematic.py   (paths relative to this file)
"""
import os, re, uuid

HERE = os.path.dirname(os.path.abspath(__file__))
V3 = os.path.dirname(HERE)
SCH = os.path.join(V3, 'proves_radio_stick_V3.kicad_sch')
LIB = os.path.join(V3, 'symbols', 'proves_power.kicad_sym')
PROJECT = 'proves_radio_stick_V3'

VALUES = {'100n': '100nF', '4.7u': '4.7uF', '1u': '1uF', '12p': '12pF', '10p': '10pF',
          'Conn_Coaxial': 'SMA antenna', 'Screw_Terminal_01x10': 'J3 breakout',
          'USB_C_Receptacle_USB2.0_16P': 'USB-C (USB 2.0)', 'SWD Port': 'SWD (JST-SH)'}
MPN = {'J2': '132134', 'J5': 'PZ1.27-2x7P ZZ', 'J12': 'TYPE-C-31-M-12', 'J22': 'BM03B-SRSS-TB',
       'U1': 'STM32U575VIT6', 'U2': 'TPS62085RLTR', 'U4': 'USBLC6-2SC6', 'U19': 'TPS22918DBVR'}
# R95's +3V3 hangs below the resistor; turned upright it sits inside R95's body.
# Fixing it means redrawing R95 above the ON line (next schematic rewrite).
KEEP_ROTATION = {'#PWR0168'}
# Appended to the note that already sits beside each rail's source.
RAILS = [('USB 2.0 full speed', 'VBUS = (4.75, 5.0, 5.25) V @ (0.02, 0.1, 0.8) A'),
         ('TPS62085 (3 A) makes', '+3V3 = (3.25, 3.32, 3.39) V @ (0.005, 0.04, 0.15) A'),
         ('RF_VCC = VBUS via FB1', 'RF_VCC = (4.7, 5.0, 5.25) V @ (0.005, 0.1, 0.65) A')]

def blocks(s, head):
    """Yield (start, end) of every top-level-in-sheet block that starts with `head`."""
    i = 0
    while True:
        i = s.find(head, i)
        if i < 0:
            return
        depth, j = 0, i
        while True:
            c = s[j]
            if c == '(':
                depth += 1
            elif c == ')':
                depth -= 1
                if depth == 0:
                    break
            elif c == '"':
                j = s.index('"', j + 1)
                while s[j - 1] == '\\':
                    j = s.index('"', j + 1)
            j += 1
        yield i, j + 1
        i = j + 1

def prop(block, name):
    m = re.search(r'\(property "%s" "((?:[^"\\]|\\.)*)"' % re.escape(name), block)
    return m.group(1) if m else None

def set_prop_value(block, name, value):
    return re.sub(r'(\(property "%s" )"(?:[^"\\]|\\.)*"' % re.escape(name), lambda m: m.group(1) + '"' + value + '"', block, count=1)

def add_prop(block, name, value, x, y):
    new = ('\t\t(property "%s" "%s"\n\t\t\t(at %s %s 0)\n\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.27 1.27)\n'
           '\t\t\t\t)\n\t\t\t\t(hide yes)\n\t\t\t)\n\t\t)\n') % (name, value, x, y)
    k = block.index('\t\t(pin ') if '\t\t(pin ' in block else block.rindex('\t\t(instances')
    return block[:k] + new + block[k:]

def at_of(block):
    m = re.search(r'\(at ([-\d.]+) ([-\d.]+)(?: ([-\d.]+))?\)', block)
    return float(m.group(1)), float(m.group(2)), float(m.group(3) or 0)

def num(v):
    return ('%.4f' % v).rstrip('0').rstrip('.')

def fix_symbol(b):
    lib = re.search(r'\(lib_id "([^"]+)"\)', b).group(1)
    ref, val = prop(b, 'Reference'), prop(b, 'Value')
    if lib.startswith('power:') and not lib.endswith('PWR_FLAG') and ref not in KEEP_ROTATION:
        x, y, rot = at_of(b)
        if rot != 0:
            b = re.sub(r'\(at [-\d.]+ [-\d.]+ [-\d.]+\)', '(at %s %s 0)' % (num(x), num(y)), b, count=1)
            dy = 3.81 if val.startswith('GND') else -3.556
            b = re.sub(r'(\(property "Value" "[^"]*"\s*\(at )[-\d.]+ [-\d.]+ [-\d.]+\)',
                       lambda m: m.group(1) + '%s %s 0)' % (num(x), num(y + dy)), b, count=1)
            b = b.replace('\t\t\t\t(justify left)\n', '').replace('\t\t\t\t(justify right)\n', '')
    if val in VALUES and not ref.startswith('#'):
        b = set_prop_value(b, 'Value', VALUES[val])
    if ref in MPN and prop(b, 'MPN') is None:
        x, y, _ = at_of(b)
        b = add_prop(b, 'MPN', MPN[ref], num(x), num(y))
    return b

def power_instance(net, x, y, n):
    return ('\t(symbol\n\t\t(lib_id "proves_power:%(net)s")\n\t\t(at %(x)s %(y)s 0)\n\t\t(unit 1)\n'
            '\t\t(exclude_from_sim no)\n\t\t(in_bom yes)\n\t\t(on_board yes)\n\t\t(dnp no)\n\t\t(uuid "%(u)s")\n'
            '\t\t(property "Reference" "#PWR0%(n)d"\n\t\t\t(at %(x)s %(yr)s 0)\n\t\t\t(effects\n\t\t\t\t(font\n'
            '\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t)\n\t\t\t\t(hide yes)\n\t\t\t)\n\t\t)\n'
            '\t\t(property "Value" "%(net)s"\n\t\t\t(at %(x)s %(yv)s 0)\n\t\t\t(effects\n\t\t\t\t(font\n'
            '\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t)\n\t\t\t)\n\t\t)\n'
            '\t\t(property "Footprint" ""\n\t\t\t(at %(x)s %(y)s 0)\n\t\t\t(effects\n\t\t\t\t(font\n'
            '\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t)\n\t\t\t\t(hide yes)\n\t\t\t)\n\t\t)\n'
            '\t\t(pin "1"\n\t\t\t(uuid "%(pu)s")\n\t\t)\n'
            '\t\t(instances\n\t\t\t(project "%(p)s"\n\t\t\t\t(path "/%(root)s"\n\t\t\t\t\t(reference "#PWR0%(n)d")\n'
            '\t\t\t\t\t(unit 1)\n\t\t\t\t)\n\t\t\t)\n\t\t)\n\t)\n') % dict(
                net=net, x=num(x), y=num(y), yr=num(y + 3.81), yv=num(y - 3.556), n=n,
                u=uuid.uuid4(), pu=uuid.uuid4(), p=PROJECT, root=ROOT)

def lib_symbol(s, net):
    """The project power symbol `net`, drawn like power:VBUS (arrow up)."""
    i, j = next(blocks(s, '(symbol "power:VBUS"'))
    body = s[i:j].replace('"power:VBUS"', '"proves_power:%s"' % net).replace('VBUS_', net + '_')
    body = body.replace('(property "Value" "VBUS"', '(property "Value" "%s"' % net)
    body = re.sub(r'global label with name \\"VBUS\\"', r'global label with name \\"%s\\"' % net, body)
    return body

s = open(SCH).read()
ROOT = re.search(r'\(path "/([0-9a-f-]{36})"', s).group(1)

# instances: this project
s = re.sub(r'\(project "[^"]*"', '(project "%s"' % PROJECT, s)

out, last = [], 0
for i, j in list(blocks(s, '\t(symbol\n\t\t(lib_id')):
    out.append(s[last:i]); out.append(fix_symbol(s[i:j])); last = j
out.append(s[last:]); s = ''.join(out)

# RF_VCC global labels -> project power symbol at the same point
n = 1 + max(int(m) for m in re.findall(r'"#PWR0*(\d+)"', s))
for i, j in reversed(list(blocks(s, '\t(global_label "RF_VCC"'))):
    x, y, _ = at_of(s[i:j])
    s = s[:i] + power_instance('RF_VCC', x, y, n).rstrip('\n') + s[j:]
    n += 1
if '(symbol "proves_power:RF_VCC"' not in s:
    k = s.index('\t(lib_symbols\n') + len('\t(lib_symbols\n')
    s = s[:k] + '\t\t' + lib_symbol(s, 'RF_VCC') + '\n' + s[k:]

# rail ranges on the notes beside each rail's source
for anchor, line in RAILS:
    if line in s:
        continue
    m = re.search(r'\(text "((?:[^"\\]|\\.)*%s(?:[^"\\]|\\.)*)"' % re.escape(anchor), s)
    s = s[:m.end(1)] + '\\n' + line + s[m.end(1):]

open(SCH, 'w').write(s)

# project power library and its sym-lib-table entry
if not os.path.exists(LIB):
    i, j = next(blocks(s, '\t\t(symbol "proves_power:RF_VCC"'))
    sym = s[i:j].replace('"proves_power:RF_VCC"', '"RF_VCC"')
    open(LIB, 'w').write('(kicad_symbol_lib\n\t(version 20241209)\n\t(generator "style_v3_schematic")\n' + sym + '\n)\n')
table = os.path.join(V3, 'sym-lib-table')
t = open(table).read()
if '"proves_power"' not in t:
    t = t.rstrip().rstrip(')') + '  (lib (name "proves_power")(type "KiCad")(uri "${KIPRJMOD}/symbols/proves_power.kicad_sym")(options "")(descr "PROVES project power symbols"))\n)\n'
    open(table, 'w').write(t)
print('styled', SCH)
