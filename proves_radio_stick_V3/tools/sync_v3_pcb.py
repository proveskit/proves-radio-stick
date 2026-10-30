#!/usr/bin/env python3
"""Bring the V3 board in line with the schematic netlist and place the MCU island.

Does what KiCad's "Update PCB from Schematic" does (drop footprints the
netlist lost, add new ones, assign every pad's net), then clears the RP2350
island (tracks, vias, zones) and places the STM32U575VIT6 island from PLACE.

Usage (KiCad 10 python): python3 sync_v3_pcb.py <netlist.xml>
Overwrites ../proves_radio_stick_V3.kicad_pcb.
"""
import os, sys, xml.etree.ElementTree as ET
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, '..', 'proves_radio_stick_V3.kicad_pcb')
KLIB = os.environ.get('KICAD_FOOTPRINT_DIR', '/usr/share/kicad/footprints')
PLIB = {'FC_DEV_BOARD': os.path.join(HERE, '..', 'footprints.pretty'),
        'easyeda2kicad': os.path.join(HERE, '..', 'easyeda2kicad.pretty')}
MM = 1e6
ISLAND = (212.45, 84.3, 240.2, 109.8)   # RP2350 island cleared of copper

def P(x, y): return pcbnew.VECTOR2I(int(round(x * MM)), int(round(y * MM)))
def inside(pt, box): return box[0] <= pt.x / MM <= box[2] and box[1] <= pt.y / MM <= box[3]

# ------------------------------------------------------------------ netlist
root = ET.parse(sys.argv[1]).getroot()
comps, pad_net = {}, {}
for c in root.iter('comp'):
    props = {p.get('name'): p.get('value') for p in c.iter('property')}
    comps[c.get('ref')] = dict(fp=c.findtext('footprint'), value=c.findtext('value'),
                               dnp='dnp' in props)
for n in root.iter('net'):
    for node in n.iter('node'):
        pad_net[(node.get('ref'), node.get('pin'))] = n.get('name')

b = pcbnew.LoadBoard(PCB)

def load(fpid):
    lib, name = fpid.split(':', 1)
    path = PLIB.get(lib, os.path.join(KLIB, lib + '.pretty'))
    f = pcbnew.FootprintLoad(path, name)
    assert f, fpid
    f.SetFPID(pcbnew.LIB_ID(lib, name))
    return f

# ------------------------------------------------------------------ footprints
KEEP_UNLISTED = ('G***', 'H1', 'H2', 'H3', 'H4')
have = {f.GetReference(): f for f in b.GetFootprints()}
fresh = {ref: load(c['fp']) for ref, c in comps.items()
         if ref not in have or have[ref].GetFPIDAsString() != c['fp']}
for ref in list(have):
    if ref not in comps and ref not in KEEP_UNLISTED:
        b.Delete(have.pop(ref))

for ref, c in sorted(comps.items()):
    f = have.get(ref)
    if ref in fresh:
        if f is not None:
            b.Delete(f)
        f = fresh[ref]
        f.SetReference(ref)
        b.Add(f)
    have[ref] = f
    f.SetValue(c['value'])
    f.SetDNP(c['dnp'])
    f.SetExcludedFromBOM(c['dnp'])
    f.SetExcludedFromPosFiles(c['dnp'])

nets = {}
def net(name):
    if name not in nets:
        ni = b.FindNet(name)
        if ni is None:
            ni = pcbnew.NETINFO_ITEM(b, name)
            b.Add(ni)
        nets[name] = ni
    return nets[name]

for ref, f in have.items():
    if ref not in comps:
        continue
    for pad in f.Pads():
        name = pad_net.get((ref, pad.GetNumber()))
        if name is None or name.startswith('unconnected-'):
            pad.SetNetCode(0)
        else:
            pad.SetNet(net(name))

# ------------------------------------------------------------------ clear the island
for t in list(b.GetTracks()):
    pts = [t.GetPosition()] if t.Type() == pcbnew.PCB_VIA_T else [t.GetStart(), t.GetEnd()]
    if any(inside(p, ISLAND) for p in pts):
        b.Delete(t)
# E22 signal tracks that ran from the module to the old RP2350 pins.
RADIO = {'SPI1_SCK', 'SPI1_MISO', 'SPI1_MOSI', 'SPI1_CS0', 'RF1_RST', 'RF1_IO0', 'RF1_IO1',
         'RF1_IO2', 'RF1_RX_EN', 'RF1_TX_EN', 'RF_PWR_EN'}
for t in list(b.GetTracks()):
    if t.GetNetname().lstrip('/') in RADIO:
        b.Delete(t)
for z in list(b.Zones()):
    bb = z.GetBoundingBox()
    small = bb.GetWidth() < 15 * MM and bb.GetHeight() < 15 * MM
    if small and not z.GetIsRuleArea() and z.GetLayer() == pcbnew.F_Cu and \
            z.GetNetname() in ('GND', '+1V1') and inside(bb.Centre(), ISLAND):
        b.Delete(z)

# ------------------------------------------------------------------ placement
from v3_placement import PLACE
for ref, (x, y, rot, side) in PLACE.items():
    f = have[ref]
    if f.IsFlipped() != (side == 'B'):
        f.Flip(f.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
    f.SetPosition(P(x, y))
    f.SetOrientationDegrees(rot)

b.BuildConnectivity()
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
pcbnew.SaveBoard(PCB, b)
print('footprints', len(b.GetFootprints()), 'tracks', len(b.GetTracks()), 'zones', len(list(b.Zones())))
