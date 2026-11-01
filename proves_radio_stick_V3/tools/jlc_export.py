#!/usr/bin/env python3
"""Write the JLCPCB order files for V3 into ../jlcpcb/ (run inside the KiCad 10 container).

  gerber/            Gerbers + Excellon drills, and GERBER-proves_radio_stick_V3.zip
  production_files/  BOM-proves_radio_stick_V3.csv  (Comment,Designator,Footprint,LCSC,Quantity)
                     CPL-proves_radio_stick_V3.csv  (Designator,Val,Package,Mid X,Mid Y,Rotation,Layer)

Same layout as V2's files. CPL rotations get JLC's per-package offsets: taken from V2's
CPL where V2 used the same footprint, otherwise from ROTATION_OFFSET below. Check the
rotations in JLC's placement preview before ordering either way.
"""
import csv, io, math, os, re, subprocess, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
PRJ = os.path.join(HERE, '..')
NAME = 'proves_radio_stick_V3'
OUT = os.path.join(PRJ, 'jlcpcb')
GERB = os.path.join(OUT, 'gerber')
PROD = os.path.join(OUT, 'production_files')
PCB = os.path.join(PRJ, NAME + '.kicad_pcb')
SCH = os.path.join(PRJ, NAME + '.kicad_sch')
V2_CPL = os.path.join(PRJ, '..', 'proves_radio_stick_V2', 'jlcpcb', 'production_files',
                      'CPL-proves_radio_stick_V2.csv')
V2_PCB = os.path.join(PRJ, '..', 'proves_radio_stick_V2', 'proves_radio_stick_V2.kicad_pcb')

# Footprints new in V3 (offsets as in the kicad-jlcpcb-tools rotation table).
ROTATION_OFFSET = [
    (r'^LQFP-', 270),
    (r'^SOT-23', 180),
    (r'^Crystal_SMD_', 0),
]

# Footprints whose KiCad origin is pin 1, not the body centre JLC places by: offset to the
# pad centre in the footprint's own frame (x right, y down, before rotation).
CENTRE_OFFSET = [
    (r'^TerminalBlock_Phoenix_MPT-0,5-10-2.54_', (11.43, 0.0)),
    (r'^PinHeader_2x07_P1.27mm_', (0.635, 3.81)),
]

def centre(r):
    """CPL Mid X/Y: KiCad's position plus CENTRE_OFFSET rotated with the footprint (pos files are y-up)."""
    x, y = float(r['PosX']), float(r['PosY'])
    off = next((o for pat, o in CENTRE_OFFSET if re.match(pat, r['Package'])), None)
    if off is None:
        return x, y
    dx, dy = off[0] * (-1 if r['Side'] == 'bottom' else 1), off[1]
    a = math.radians(float(r['Rot']))
    return x + dx * math.cos(a) + dy * math.sin(a), y - (-dx * math.sin(a) + dy * math.cos(a))

def run(*args):
    subprocess.run(args, check=True, stdout=subprocess.DEVNULL)

def kicad_pos(pcb):
    tmp = '/tmp/pos.csv'
    run('kicad-cli', 'pcb', 'export', 'pos', '--format', 'csv', '--units', 'mm', '--side', 'both',
        '--exclude-dnp', '-o', tmp, pcb)
    return list(csv.DictReader(open(tmp)))

def v2_offsets():
    """Package -> JLC rotation offset, learned from V2's KiCad positions vs its CPL."""
    if not (os.path.exists(V2_CPL) and os.path.exists(V2_PCB)):
        return {}
    kicad = {r['Ref']: r for r in kicad_pos(V2_PCB)}
    off = {}
    for r in csv.DictReader(open(V2_CPL)):
        k = kicad.get(r['Designator'])
        if k:
            off[r['Package']] = (float(r['Rotation']) - float(k['Rot'])) % 360
    return off

def gerbers():
    os.makedirs(GERB, exist_ok=True)
    layers = 'F.Cu,In1.Cu,In2.Cu,B.Cu,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,F.Mask,B.Mask,Edge.Cuts'
    run('kicad-cli', 'pcb', 'export', 'gerbers', '--layers', layers, '--subtract-soldermask',
        '-o', GERB + '/', PCB)
    run('kicad-cli', 'pcb', 'export', 'drill', '--format', 'excellon', '--excellon-separate-th',
        '--generate-map', '--map-format', 'pdf', '-o', GERB + '/', PCB)
    z = os.path.join(PROD, 'GERBER-%s.zip' % NAME)
    with zipfile.ZipFile(z, 'w', zipfile.ZIP_DEFLATED) as zf:
        for f in sorted(os.listdir(GERB)):
            if not f.endswith('.pdf'):
                zf.write(os.path.join(GERB, f), f)

def bom():
    tmp = '/tmp/bom.csv'
    run('kicad-cli', 'sch', 'export', 'bom', '--fields', 'Value,Reference,Footprint,LCSC Part,${QUANTITY}',
        '--labels', 'Comment,Designator,Footprint,LCSC,Quantity', '--group-by', 'Value,Footprint,LCSC Part',
        '--ref-range-delimiter', '', '--exclude-dnp', '-o', tmp, SCH)
    rows = list(csv.DictReader(open(tmp)))
    missing = [r['Designator'] for r in rows if not r['LCSC']]
    with open(os.path.join(PROD, 'BOM-%s.csv' % NAME), 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['Comment', 'Designator', 'Footprint', 'LCSC', 'Quantity'])
        for r in rows:
            if r['LCSC']:
                w.writerow([r['Comment'], r['Designator'], r['Footprint'].split(':')[-1], r['LCSC'], r['Quantity']])
    return rows, missing

def cpl(bom_rows):
    fitted = {d for r in bom_rows if r['LCSC'] for d in r['Designator'].split(',')}
    learned = v2_offsets()
    unknown = set()
    with open(os.path.join(PROD, 'CPL-%s.csv' % NAME), 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['Designator', 'Val', 'Package', 'Mid X', 'Mid Y', 'Rotation', 'Layer'])
        for r in kicad_pos(PCB):
            if r['Ref'] not in fitted:
                continue
            pkg = r['Package']
            off = learned.get(pkg)
            if off is None:
                off = next((o for pat, o in ROTATION_OFFSET if re.match(pat, pkg)), None)
            if off is None:
                unknown.add(pkg)
                off = 0
            x, y = centre(r)
            w.writerow([r['Ref'], r['Val'], pkg, '%.6f' % x, '%.6f' % y,
                        '%.6f' % ((float(r['Rot']) + off) % 360), r['Side']])
    return unknown

if __name__ == '__main__':
    os.makedirs(PROD, exist_ok=True)
    gerbers()
    rows, missing = bom()
    unknown = cpl(rows)
    print('BOM lines', sum(1 for r in rows if r['LCSC']), '| no LCSC (not in BOM):', ' '.join(missing) or 'none')
    print('CPL packages with no known rotation offset:', ' '.join(sorted(unknown)) or 'none')
