#!/usr/bin/env python3
"""Route the V3 MCU island with Freerouting, keeping the V2 routing outside it.

  python3 route_v3.py prep <drc.json> <v2.kicad_pcb>
                                        drop dangling V2 stubs, restore V2's USB-side VBUS
                                        routing, add island pours, lock tracks
  python3 route_v3.py dsn <out.dsn>     export Specctra DSN (outer GND pours left out)
  python3 route_v3.py ses <in.ses>      import the routed session and refill zones
  python3 route_v3.py finish            hand tracks, GND stitching vias, refill

Run with KiCad 10 python; edits ../proves_radio_stick_V3.kicad_pcb in place.
"""
import json, os, sys
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, '..', 'proves_radio_stick_V3.kicad_pcb')
MM = 1e6

def P(x, y): return pcbnew.VECTOR2I(int(round(x * MM)), int(round(y * MM)))

def rect_zone(b, net, layer, box, prio):
    z = pcbnew.ZONE(b)
    z.SetLayer(layer)
    z.SetNet(b.FindNet(net))
    z.SetAssignedPriority(prio)
    z.SetLocalClearance(int(0.2 * MM))
    z.SetMinThickness(int(0.2 * MM))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
    z.SetThermalReliefGap(int(0.25 * MM))
    z.SetThermalReliefSpokeWidth(int(0.3 * MM))
    z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
    x0, y0, x1, y1 = box
    o = z.Outline()
    o.NewOutline()
    for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
        o.Append(P(x, y))
    b.Add(z)

def restore_v2_vbus(b, v2_pcb):
    # The island clear-out took V2's VBUS run from J12 to U2 with it; that part of
    # the board is unchanged, so copy those tracks and vias back.
    v2 = pcbnew.LoadBoard(v2_pcb)
    vbus = b.FindNet('VBUS')
    for t in v2.GetTracks():
        if t.GetNetname() == 'VBUS' and min(t.GetStart().x, t.GetEnd().x) > 236 * MM:
            c = t.Duplicate()
            c.SetParent(b)
            c.SetNet(vbus)
            b.Add(c)

def pad_xy(b, ref, num):
    f = next(f for f in b.GetFootprints() if f.GetReference() == ref)
    p = next(p for p in f.Pads() if p.GetNumber() == num)
    return p.GetX() / MM, p.GetY() / MM

def preroute_vbus(b):
    """U4's VBUS pin to V2's VBUS via beside J12, fixed before autorouting.

    Left to the router, the D+/D- and CC tracks box the pin in.
    """
    x, y = pad_xy(b, 'U4', '5')
    vy = y + 1.0
    add_track(b, 'VBUS', pcbnew.F_Cu, 0.3, [(x, y), (x, vy)])
    add_via(b, 'VBUS', x, vy)
    # Jog up before J12's NPTH peg at (238.88, 101.78).
    add_track(b, 'VBUS', pcbnew.B_Cu, 0.3, [(x, vy), (237.9, vy), (238.2, 100.83), (239.22, 100.83)])

def prep(b, drc_json, v2_pcb):
    stale = {i['uuid'] for v in json.load(open(drc_json))['violations']
             if v['type'] in ('track_dangling', 'via_dangling') for i in v['items']}
    for t in list(b.GetTracks()):
        if t.m_Uuid.AsString() in stale:
            b.Delete(t)
    restore_v2_vbus(b, v2_pcb)
    preroute_vbus(b)
    # V2's planes kept 0.5 mm from other nets, which cuts the STDC14 +3V3 pin off
    # In2 inside the 1.27 mm pin field; 0.25 mm lets the plane reach it.
    for z in b.Zones():
        if z.GetLayer() in (pcbnew.In1_Cu, pcbnew.In2_Cu):
            z.SetLocalClearance(int(0.25 * MM))
    # F.Cu GND pour over the island (V2's pour stopped at x 216).
    rect_zone(b, 'GND', pcbnew.F_Cu, (216.15, 84.6, 245.2, 116.9), 0)
    # GND under the bottom-side crystals on In2 (otherwise the +3V3 plane).
    rect_zone(b, 'GND', pcbnew.In2_Cu, (215.0, 93.3, 220.3, 101.0), 4)
    # Keep V2's power and RF copper fixed; signal tracks may be ripped up and rerouted.
    for t in b.GetTracks():
        t.SetLocked(t.GetNetClassName() != 'Default' or t.GetNetname() == 'GND')

def dsn(b, out):
    for z in list(b.Zones()):
        if not z.GetIsRuleArea() and z.GetLayer() in (pcbnew.F_Cu, pcbnew.B_Cu):
            b.Delete(z)
    assert pcbnew.ExportSpecctraDSN(b, out)
    # 0.5 mm hole-to-hole between 0.3 mm vias needs 0.2 mm copper between them;
    # the router knows nothing about hole spacing otherwise.
    dsn = open(out).read().replace('(clearance 37.5 (type smd_smd))',
                                   '(clearance 37.5 (type smd_smd))\n      (clearance 200 (type via_via))')
    open(out, 'w').write(dsn)

def ses(b, ses_in):
    assert pcbnew.ImportSpecctraSES(b, ses_in)
    b.BuildConnectivity()
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())

ISLAND = (212.6, 84.6, 241.0, 110.0)
STITCH_PITCH = 1.6
VIA_D, VIA_DRILL = 0.6, 0.3

# Connections the router leaves open, as (net, layer, width, points).
HAND = []

def add_track(b, net, layer, width, pts):
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        t = pcbnew.PCB_TRACK(b)
        t.SetStart(P(x0, y0)); t.SetEnd(P(x1, y1))
        t.SetLayer(layer); t.SetWidth(int(width * MM)); t.SetNet(b.FindNet(net))
        b.Add(t)

def add_via(b, net, x, y):
    v = pcbnew.PCB_VIA(b)
    v.SetPosition(P(x, y)); v.SetWidth(int(VIA_D * MM)); v.SetDrill(int(VIA_DRILL * MM))
    v.SetNet(b.FindNet(net)); v.SetLocked(True)
    b.Add(v)
    return v

def stitch(b):
    """GND vias on a grid, plus one in every GND fill fragment that has no via.

    A via goes only where the outer GND pours and both inner planes all have copper
    for the via and its clearance, so it cannot land on another net's track or pad.
    """
    import math
    fills = lambda net, layer: [z for z in b.Zones() if z.GetNetname() == net and z.GetLayer() == layer]
    need = [fills('GND', pcbnew.F_Cu), fills('GND', pcbnew.B_Cu), fills('GND', pcbnew.In1_Cu),
            fills('GND', pcbnew.In2_Cu) + fills('+3V3', pcbnew.In2_Cu)]
    holes = [(t.GetX() / MM, t.GetY() / MM) for t in b.GetTracks() if t.Type() == pcbnew.PCB_VIA_T]
    holes += [(p.GetX() / MM, p.GetY() / MM) for f in b.GetFootprints() for p in f.Pads()
              if p.GetDrillSize().x > 0]
    ring = [(0.0, 0.0)] + [(0.55 * math.cos(a * math.pi / 4), 0.55 * math.sin(a * math.pi / 4)) for a in range(8)]

    def ok(x, y):
        return all((x - hx) ** 2 + (y - hy) ** 2 > 1.0 for hx, hy in holes) and \
            all(any(z.HitTestFilledArea(z.GetLayer(), P(x + dx, y + dy)) for z in zs)
                for zs in need for dx, dy in ring)

    def place(x, y):
        add_via(b, 'GND', x, y)
        holes.append((x, y))

    added = 0
    y = ISLAND[1] + 0.8
    while y < ISLAND[3]:
        x = ISLAND[0] + 0.8
        while x < ISLAND[2]:
            if ok(x, y):
                place(x, y)
                added += 1
            x += STITCH_PITCH
        y += STITCH_PITCH

    # Fragments: a GND fill polygon in the island with no via inside it.
    for layer in (pcbnew.F_Cu, pcbnew.B_Cu, pcbnew.In2_Cu):
        for z in fills('GND', layer):
            polys = z.GetFilledPolysList(layer)
            for k in range(polys.OutlineCount()):
                bb = polys.Outline(k).BBox()
                x0, y0, x1, y1 = bb.GetLeft() / MM, bb.GetTop() / MM, bb.GetRight() / MM, bb.GetBottom() / MM
                if x1 < ISLAND[0] or x0 > ISLAND[2] or y1 < ISLAND[1] or y0 > ISLAND[3]:
                    continue
                inside = lambda hx, hy: polys.Outline(k).PointInside(P(hx, hy))
                if any(inside(hx, hy) for hx, hy in holes):
                    continue
                spots = [(x0 + i * 0.1, y0 + j * 0.1) for i in range(int((x1 - x0) / 0.1) + 1)
                         for j in range(int((y1 - y0) / 0.1) + 1)]
                spot = next(((x, y) for x, y in spots if inside(x, y) and ok(x, y)), None)
                print('fragment', b.GetLayerName(layer), round(x0, 2), round(y0, 2), '->', spot)
                if spot:
                    place(*spot)
                    added += 1
    return added

def drop_dangling_vias(b):
    ends = {}
    for t in b.GetTracks():
        if t.Type() != pcbnew.PCB_VIA_T:
            for pt in (t.GetStart(), t.GetEnd()):
                ends.setdefault(t.GetNetname(), []).append(pt)
    for v in [t for t in b.GetTracks() if t.Type() == pcbnew.PCB_VIA_T]:
        if v.GetNetname() in ('GND', '+3V3'):
            continue
        if not any((pt - v.GetPosition()).EuclideanNorm() < v.GetWidth(pcbnew.F_Cu) / 2
                   for pt in ends.get(v.GetNetname(), [])):
            print('drop dangling via', v.GetNetname(), v.GetX() / MM, v.GetY() / MM)
            b.Delete(v)

HOLE2HOLE = 0.5    # JLC: 0.5 mm between hole walls

def spread_vias(b):
    """Push apart via pairs closer than the hole-to-hole rule; tracks follow the via."""
    vias = [t for t in b.GetTracks() if t.Type() == pcbnew.PCB_VIA_T]
    for k, u in enumerate(vias):
        for v in vias[k + 1:]:
            d = (u.GetPosition() - v.GetPosition()).EuclideanNorm() / MM
            need = (u.GetDrill() + v.GetDrill()) / 2 / MM + HOLE2HOLE + 0.02
            if d >= need or d == 0:
                continue
            # Move the via with fewer tracks on it.
            ends = lambda w: [t for t in b.GetTracks() if t.Type() != pcbnew.PCB_VIA_T and
                              t.GetNetCode() == w.GetNetCode() and
                              w.GetPosition() in (t.GetStart(), t.GetEnd())]
            mv, other = (u, v) if len(ends(u)) <= len(ends(v)) else (v, u)
            dirv = mv.GetPosition() - other.GetPosition()
            step = (need - d) * MM / (d * MM)
            delta = pcbnew.VECTOR2I(int(dirv.x * step), int(dirv.y * step))
            old = mv.GetPosition()
            for t in ends(mv):
                if t.GetStart() == old:
                    t.SetStart(old + delta)
                if t.GetEnd() == old:
                    t.SetEnd(old + delta)
            mv.SetPosition(old + delta)
            print('spread via', mv.GetNetname(), round(old.x / MM, 2), round(old.y / MM, 2), 'by', round(need - d, 3))

def finish(b):
    drop_dangling_vias(b)
    spread_vias(b)
    for net, layer, width, pts in HAND:
        add_track(b, net, layer, width, pts)
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    print('stitching vias', stitch(b))
    b.BuildConnectivity()
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())

if __name__ == '__main__':
    cmd, args = sys.argv[1], sys.argv[2:]
    b = pcbnew.LoadBoard(PCB)
    {'prep': prep, 'dsn': dsn, 'ses': ses, 'finish': finish}[cmd](b, *args)
    if cmd != 'dsn':
        pcbnew.SaveBoard(PCB, b)
    print(cmd, 'ok: tracks', len(b.GetTracks()), 'zones', len(list(b.Zones())))
