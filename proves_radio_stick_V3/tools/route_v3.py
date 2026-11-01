#!/usr/bin/env python3
"""Route the V3 MCU island with Freerouting, keeping the V2 routing outside it.

  python3 route_v3.py prep <drc.json> <v2.kicad_pcb>
                                        drop dangling V2 stubs, restore V2's USB-side VBUS
                                        routing, add island pours, lock tracks
  python3 route_v3.py dsn <out.dsn>     export Specctra DSN (outer GND pours left out)
  python3 route_v3.py ses <in.ses>      import the routed session and refill zones
  python3 route_v3.py finish            hand tracks, GND stitching vias, refill
  python3 route_v3.py readable          front silk names: ANT, USB, SWD; move the J12 and J3 refs
  python3 route_v3.py vias              standard 0.3 mm vias only (JLC fee below that), refill

Run with KiCad 10 python; edits ../proves_radio_stick_V3.kicad_pcb in place.
"""
import json, os, re, sys
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
    vy = y + 1.1
    add_track(b, 'VBUS', pcbnew.F_Cu, 0.3, [(x, y), (x, vy)])
    add_via(b, 'VBUS', x, vy)
    # Jog up before J12's NPTH peg at (238.88, 101.78).
    add_track(b, 'VBUS', pcbnew.B_Cu, 0.3, [(x, vy), (237.9, vy), (238.2, 100.83), (239.22, 100.83)])

# Layout review r1 fixes, applied after routing (see fixups).
# Crystal nets: MCU pin -> crystal pad -> load cap, as short as the maze finds.
CRYSTAL_CHAINS = [('/OSC32_IN', [('U1', '8'), ('Y102', '1'), ('C117', '1')]),
                  ('/OSC32_OUT', [('U1', '9'), ('Y102', '2'), ('C118', '1')]),
                  ('/OSC_IN', [('U1', '12'), ('Y101', '1'), ('C115', '1')]),
                  ('/OSC_OUT', [('U1', '13'), ('Y101', '3'), ('C116', '1')])]
# Short pin-to-pin ties: VCAP and its ground straight down to C113.
DIRECT = [('GND', ('U1', '49'), ('C113', '2')), ('/VCAP', ('U1', '48'), ('C113', '1'))]
# Pads that get their own via to the plane: MCU supply/ground pins, the decaps' pads,
# the crystal caps' ground and the USB ESD ground.
PLANE_TIES = [('U1', n) for n in ('6', '10', '11', '19', '20', '21', '22', '27', '28', '49', '50',
                                  '73', '74', '75', '99', '100')] + \
    [(c, p) for c in ['C%d' % i for i in range(101, 119) if i != 113] for p in ('1', '2')] + \
    [('C113', '2'), ('U4', '2')]

SOLID_GND = [('U4', '2'), ('U1', '99'), ('U1', '49'), ('U1', '74'), ('U1', '10'), ('U1', '27')]

def pad_end(b, ref, num):
    f = next(f for f in b.GetFootprints() if f.GetReference() == ref)
    p = next(p for p in f.Pads() if p.GetNumber() == num)
    side = '*' if p.GetDrillSize().x > 0 else ('B' if f.IsFlipped() else 'F')
    return p.GetX() / MM, p.GetY() / MM, side, p.GetNetname(), p

def fixups(b):
    """Layout review fixes applied to the routed board.

    Crystal nets are re-laid as the shortest pin -> crystal -> load-cap chain the maze
    finds (the autorouter's copper for them is removed), VCAP and pin 49 go straight to
    C113, and every supply/ground pad in PLANE_TIES gets its own via to the plane.
    """
    import maze_v3
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    width = lambda net: 0.3 if net in ('GND', '+3V3', '/VCAP') else 0.2
    for net, chain in CRYSTAL_CHAINS:
        old = [t for t in b.GetTracks() if t.GetNetname() == net]
        paths = []
        for a, z in zip(chain, chain[1:]):
            path = maze_v3.route(b, net, pad_end(b, *a)[:3], pad_end(b, *z)[:3], width(net), ignore=())
            paths.append(path)
        if all(paths):
            for t in old:
                b.Delete(t)
            for path in paths:
                maze_v3.commit(b, net, path, width(net))
        print('crystal', net, 'rerouted' if all(paths) else 'kept (no path)')
    # C113 must have its VCAP pad under pin 48 and its GND pad under pin 49.
    c113 = next(f for f in b.GetFootprints() if f.GetReference() == 'C113')
    if pad_end(b, 'C113', '1')[0] > pad_end(b, 'C113', '2')[0]:
        pads = [pad_end(b, 'C113', n)[4] for n in ('1', '2')] + [pad_end(b, 'U1', n)[4] for n in ('48', '49')]
        for t in list(b.GetTracks()):
            if t.GetNetname() in ('/VCAP', 'GND') and t.Type() != pcbnew.PCB_VIA_T and \
                    any(p.HitTest(t.GetStart(), 0) or p.HitTest(t.GetEnd(), 0) for p in pads):
                b.Delete(t)
        c113.SetOrientationDegrees(c113.GetOrientationDegrees() + 180)
        print('C113 turned; pad 1 now at', pad_end(b, 'C113', '1')[:2])
    for net, a, z in DIRECT:
        path = maze_v3.route(b, net, pad_end(b, *a)[:3], pad_end(b, *z)[:3], width(net))
        print('direct', net, a, z, 'ok' if path else 'NO PATH')
        if path:
            maze_v3.commit(b, net, path, width(net))
    for ref, num in PLANE_TIES:
        x, y, side, net, _ = pad_end(b, ref, num)
        if net not in maze_v3.PLANES:
            continue
        own = [t for t in b.GetTracks() if t.Type() == pcbnew.PCB_VIA_T and t.GetNetname() == net and
               (t.GetPosition() - P(x, y)).EuclideanNorm() < 1.2 * MM]
        if own:
            continue     # already has a via of its own (idempotent re-runs)
        path = maze_v3.route(b, net, (x, y, side), None, width(net))
        print('tie', ref, num, net, 'ok' if path else 'NO PATH')
        if path:
            maze_v3.commit(b, net, path, width(net))
    # Ground pads boxed in by routing: connect them solidly to the F.Cu pour.
    for ref, num in SOLID_GND:
        pad_end(b, ref, num)[4].SetLocalZoneConnection(pcbnew.ZONE_CONNECTION_FULL)
    b.BuildConnectivity()
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())

def relock(b):
    """Before a second autorouter pass: fix power, ground, crystal and VCAP copper;
    let every other signal be ripped up."""
    for t in b.GetTracks():
        n = t.GetNetname()
        t.SetLocked(t.GetNetClassName() != 'Default' or n in ('GND', '/VCAP') or n.startswith('/OSC'))

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
    v2_signal = {t.m_Uuid.AsString() for t in b.GetTracks()
                 if t.GetNetClassName() == 'Default' and t.GetNetname() != 'GND'}
    # Keep V2's power and RF copper and the pre-routes fixed; V2 signal tracks may be
    # ripped up and rerouted.
    for t in b.GetTracks():
        t.SetLocked(t.m_Uuid.AsString() not in v2_signal)

E22_UNDER = (175.0, 90.3, 211.0, 111.3)

def dsn(b, out):
    for z in list(b.Zones()):
        if not z.GetIsRuleArea() and z.GetLayer() in (pcbnew.F_Cu, pcbnew.B_Cu):
            b.Delete(z)
    assert pcbnew.ExportSpecctraDSN(b, out)
    # 0.5 mm hole-to-hole between 0.3 mm vias needs 0.2 mm copper between them;
    # the router knows nothing about hole spacing otherwise.
    dsn = open(out).read().replace('(clearance 37.5 (type smd_smd))',
                                   '(clearance 37.5 (type smd_smd))\n      (clearance 200 (type via_via))')
    # No new F.Cu tracks under the E22 module (between its pad rows).
    if os.environ.get('E22_KEEPOUT', '1') == '0':
        return
    x0, y0, x1, y1 = E22_UNDER
    keepout = '    (keepout "" (polygon F.Cu 0  %d %d  %d %d  %d %d  %d %d  %d %d))\n' % (
        x0 * 1000, -y0 * 1000, x1 * 1000, -y0 * 1000, x1 * 1000, -y1 * 1000, x0 * 1000, -y1 * 1000, x0 * 1000, -y0 * 1000)
    dsn = dsn.replace('    (via "', keepout + '    (via "', 1)
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
                have = sum(inside(hx, hy) for hx, hy in holes)
                want = 4 if layer == pcbnew.In2_Cu else 1     # the crystal ground island
                if have >= want:
                    continue
                spots = [(x0 + i * 0.1, y0 + j * 0.1) for i in range(int((x1 - x0) / 0.1) + 1)
                         for j in range(int((y1 - y0) / 0.1) + 1)]
                for _ in range(want - have):
                    spot = next(((x, y) for x, y in spots if inside(x, y) and ok(x, y)), None)
                    print('fragment', b.GetLayerName(layer), round(x0, 2), round(y0, 2), '->', spot)
                    if not spot:
                        break
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

# Free ends of tracks left without a load once fixups re-tied pin 49 (J12 -> under U1).
DEAD_ENDS = [('GND', 227.97, 105.46)]

def drop_dead_ends(b):
    """Walk back from each free end, deleting segments (and their duplicates) until a pad, via or branch."""
    near = lambda p, q: (p - q).EuclideanNorm() < 0.02 * MM
    for net, x, y in DEAD_ENDS:
        at = P(x, y)
        while True:
            segs = [t for t in b.GetTracks() if t.Type() == pcbnew.PCB_TRACE_T and t.GetNetname() == net
                    and (near(at, t.GetStart()) or near(at, t.GetEnd()))]
            far = {(o.x, o.y) for t in segs for o in [t.GetEnd() if near(at, t.GetStart()) else t.GetStart()]}
            stop = any(t.Type() == pcbnew.PCB_VIA_T and near(t.GetPosition(), at) for t in b.GetTracks()) or any(
                p.GetNetname() == net and p.HitTest(at) for f in b.GetFootprints() for p in f.Pads())
            if not segs or len(far) != 1 or stop:
                break
            for t in segs:
                print('drop dead-end', net, t.GetStart().x / MM, t.GetStart().y / MM, t.GetEnd().x / MM, t.GetEnd().y / MM)
                b.Delete(t)
            at = pcbnew.VECTOR2I(*far.pop())

# Every via is a standard 0.3 mm hole: JLC's 0.2 mm tier adds TG155 and a 4-wire Kelvin test
# ($37.62 on the 2026-10-31 5-board quote). Layout r2's 0.2 mm GND vias in the U4.2 and U1.27/C102.2
# pour slivers are replaced: U4.2 gets a 0.56/0.3 via 0.6 mm above the pad on a 0.25 mm stub; the
# U1.27/C102.2 corner has no room for one and keeps its 3.9 mm track to the GND via at (213.30, 108.72),
# with C102.2 back on a thermal so both 0402 pads heat alike (r2 N4 tombstone note).
MIN_DRILL = 0.3
U4_GND_VIA = (233.3, 97.26)

def standard_vias(b):
    """Idempotent."""
    for t in list(b.GetTracks()):
        if t.Type() == pcbnew.PCB_VIA_T and t.GetDrillValue() < MIN_DRILL * MM - 1000:
            print('drop small via', t.GetNetname(), t.GetPosition().x / MM, t.GetPosition().y / MM)
            b.Delete(t)
    pad_end(b, 'C102', '2')[4].SetLocalZoneConnection(pcbnew.ZONE_CONNECTION_INHERITED)
    if not any(t.Type() == pcbnew.PCB_VIA_T and t.GetPosition() == P(*U4_GND_VIA) for t in b.GetTracks()):
        v = pcbnew.PCB_VIA(b)
        v.SetPosition(P(*U4_GND_VIA))
        v.SetWidth(int(0.56 * MM))
        v.SetDrill(int(MIN_DRILL * MM))
        v.SetNet(b.FindNet('GND'))
        b.Add(v)
        add_track(b, 'GND', pcbnew.F_Cu, 0.25, [(233.3, 97.862), U4_GND_VIA])

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

J3_PINS = ['PA0', 'PA1', 'PC0', 'PC1', 'PB13', 'PC2', 'PC3', 'PA4']

SW_LABELS = {'SW1': 'BOOT', 'SW2': 'RESET', 'SW3': 'USER'}    # on B.Silk behind each switch

def silk(b):
    """V3 silkscreen: board name, J3 pin names, island passives without refs. Idempotent."""
    texts = [d for d in b.GetDrawings() if d.GetClass() == 'PCB_TEXT']
    labels = [str(n) for n in range(22, 30)] + J3_PINS + [n[1:] for n in J3_PINS]
    j3 = sorted((t for t in texts if t.GetText() in labels and t.GetY() > 115 * MM), key=lambda t: t.GetX())
    pads = sorted((p for p in b.FindFootprintByReference('J3').Pads() if p.GetNetname() != 'GND'),
                  key=lambda p: p.GetX())
    for t, name, pad in zip(j3, J3_PINS, pads):
        # 'PB13' is wider than the 2.54 mm cell; drop the port 'P' and centre on the pad.
        t.SetText(name[1:])
        t.SetTextSize(pcbnew.VECTOR2I(int(0.75 * MM), int(1.0 * MM)))
        t.SetTextThickness(int(0.15 * MM))
        t.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_CENTER)
        t.SetVertJustify(pcbnew.GR_TEXT_V_ALIGN_CENTER)
        t.SetPosition(pcbnew.VECTOR2I(pad.GetX(), int(115.75 * MM)))
    template = next(t for t in texts if t.GetText() == 'Ebyte E22-400M30S')
    for t in texts:
        txt = t.GetText()
        if txt.startswith('1 2 3 4 5 6 7') or txt.strip() in ('D', 'A'):
            b.Delete(t)
        elif txt.startswith('PROVES Radio Stick V2'):
            t.SetText('PROVES Radio Stick V3\nSTM32U575VIT6, Oct 2026')
        elif txt.startswith('J3:') or txt in SW_LABELS.values() or (txt == 'RST' and t.GetX() > 220 * MM):
            b.Delete(t)    # V2's RST sat over its reset switch at x 222.4; V3's is SW2
    def add(text, x, y, angle=0):
        t = template.Duplicate()
        t.SetText(text)
        t.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_CENTER)
        t.SetVertJustify(pcbnew.GR_TEXT_V_ALIGN_CENTER)
        t.SetTextAngleDegrees(angle)
        t.SetPosition(P(x, y))
        b.Add(t)
    add('J3: 3.3 V ONLY', 232.5, 110.0)
    for ref, label in SW_LABELS.items():
        f = b.FindFootprintByReference(ref)
        f.Reference().SetVisible(False)
        add(label, f.GetX() / MM, f.GetY() / MM, 90)
    for ref in ('U1', 'D2'):
        b.FindFootprintByReference(ref).Reference().SetVisible(False)
    for f in b.GetFootprints():
        ref = f.GetReference()
        x, y = f.GetX() / MM, f.GetY() / MM
        if ref[0] in 'CRY' and ISLAND[0] <= x <= ISLAND[2] and ISLAND[1] <= y <= ISLAND[3]:
            f.Reference().SetVisible(False)

PERSONALITY = ("1 2 3 4 5 6 7 . . . How many more days until the weekend?\n"
               "1 2 3 What's the fee for the damage? \nNow I'm in the studio looking at your image . . .")

def skill_silk(b):
    """proves-pcb-design silk rules. Idempotent."""
    texts = {d.GetText(): d for d in b.GetDrawings() if d.GetClass() == 'PCB_TEXT'}
    name = next(t for k, t in texts.items() if k.startswith('PROVES Radio Stick V3'))
    name.SetText('PROVES Radio Stick V3\nSTM32U575VIT6, C. Oct 30, 2026')
    def add(text, x, y, size):
        if text in texts:
            return
        t = name.Duplicate()
        t.SetText(text)
        t.SetTextSize(pcbnew.VECTOR2I(int(size * MM), int(size * MM)))
        t.SetTextThickness(int(0.15 * MM))
        t.SetPosition(P(x, y))
        b.Add(t)
    # V2's personality silk sat where the MCU island is now; it moves under the E22.
    add(PERSONALITY, 191.5, 101.2, 0.8)
    add('JLCJLCJLCJLC', 184.0, 113.6, 1.0)    # JLC order-number placeholder
    # J2 and J22 refs have no room inside the edge (E22 and U1 fill the space next to them).
    for ref, show in (('J3', True), ('J5', True), ('J12', True), ('U4', False)):
        b.FindFootprintByReference(ref).Reference().SetVisible(show)

def readable_silk(b):
    """Front-side names for what a newcomer plugs in or probes (graphic design review). Idempotent."""
    texts = {d.GetText(): d for d in b.GetDrawings() if d.GetClass() == 'PCB_TEXT' and d.GetLayer() == pcbnew.F_SilkS}
    def add(text, x, y):
        t = texts.get(text) or pcbnew.PCB_TEXT(b)
        t.SetText(text)
        t.SetLayer(pcbnew.F_SilkS)
        t.SetTextSize(pcbnew.VECTOR2I(int(0.8 * MM), int(0.8 * MM)))
        t.SetTextThickness(int(0.15 * MM))
        t.SetPosition(P(x, y))
        if text not in texts:
            b.Add(t)
    add('ANT', 169.2, 94.2)      # under the SMA
    add('USB', 243.0, 105.6)     # under the USB-C
    add('SWD', 233.56, 96.3)     # under the J5 ref
    # J12 sat between U4 and the USB-C pads and read as U4's ref; J3 sat by D3, 5 mm off the block.
    for ref, x, y, angle in (('J12', 243.0, 92.2, 0), ('J3', 211.6, 113.5, 90)):
        r = b.FindFootprintByReference(ref).Reference()
        r.SetVisible(True)
        r.SetPosition(P(x, y))
        r.SetTextAngleDegrees(angle)
        r.SetTextSize(pcbnew.VECTOR2I(int(0.8 * MM), int(0.8 * MM)))


def fields(b, net_xml):
    """Copy Value and MPN from the exported schematic netlist onto the footprints."""
    import xml.etree.ElementTree as ET
    for c in ET.parse(net_xml).getroot().iter('comp'):
        f = b.FindFootprintByReference(c.get('ref'))
        if f is None:
            continue
        f.SetValue(c.findtext('value'))
        for k, v in {x.get('name'): x.text for x in c.iter('field')}.items():
            if k in ('MPN', 'LCSC Part') and v:
                f.SetField(k, v)
                f.GetField(k).SetVisible(False)

def stackup_text(path):
    """JLC04161H-7628: both inner layers 0.5 oz (0.0152 mm), ENIG. pcbnew's Python has no stackup API."""
    s = open(path).read()
    s = re.sub(r'(\(layer "In2.Cu"\s*\(type "copper"\)\s*\(thickness )0.035\)', r'\g<1>0.0152)', s)
    s = s.replace('(copper_finish "None")', '(copper_finish "ENIG")')
    open(path, 'w').write(s)

def finish(b):
    silk(b)
    drop_dead_ends(b)
    standard_vias(b)
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
    {'prep': prep, 'dsn': dsn, 'ses': ses, 'finish': finish, 'silk': silk, 'skill': lambda b, net_xml: (skill_silk(b), fields(b, net_xml)),
     'touchup': lambda b: (silk(b), drop_dead_ends(b), standard_vias(b), pcbnew.ZONE_FILLER(b).Fill(b.Zones())), 'fixups': fixups, 'relock': relock, 'readable': readable_silk,
     'vias': lambda b: (standard_vias(b), pcbnew.ZONE_FILLER(b).Fill(b.Zones()))}[cmd](b, *args)
    if cmd != 'dsn':
        pcbnew.SaveBoard(PCB, b)
    if cmd == 'skill':
        stackup_text(PCB)
    print(cmd, 'ok: tracks', len(b.GetTracks()), 'zones', len(list(b.Zones())))
