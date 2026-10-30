#!/usr/bin/env python3
"""Close single connections the autorouter leaves open with a small grid maze router.

  python3 maze_v3.py <net> <x0> <y0> <F|B|*> <x1> <y1> <F|B|*> [width] [--ignore NET] [--dry]
  python3 maze_v3.py --from-drc <drc.json>   close every unconnected pad/track pair DRC lists

Searches a 0.1 mm grid on F.Cu and B.Cu (vias allowed) around the two points,
keeping the netclass clearance from every other net's tracks, vias and pads,
then adds the path to ../proves_radio_stick_V3.kicad_pcb and refills zones.
'*' means the endpoint is a through-hole pad and either layer will do.
"""
import heapq, math, os, sys
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, '..', 'proves_radio_stick_V3.kicad_pcb')
MM = 1e6
G = 0.1                      # grid pitch, mm
CLR = 0.16                   # clearance kept to other nets, mm (rule is 0.15)
VIA_D, VIA_DRILL = 0.6, 0.3
HOLE2HOLE = 0.5
LAYERS = (pcbnew.F_Cu, pcbnew.B_Cu)

def P(x, y): return pcbnew.VECTOR2I(int(round(x * MM)), int(round(y * MM)))

PLANES = {'GND': pcbnew.In1_Cu, '+3V3': pcbnew.In2_Cu}

def route(b, net, a, z, width, ignore=()):
    """Path from a to z, or from a to a via onto net's plane when z is None."""
    to_plane = z is None
    if to_plane:
        z = (a[0], a[1], '*')
    (ax, ay, al), (zx, zy, zl) = a, z
    x0, x1 = min(ax, zx) - 3, max(ax, zx) + 3
    y0, y1 = min(ay, zy) - 3, max(ay, zy) + 3
    box = pcbnew.BOX2I(P(x0 - 2, y0 - 2), P(x1 - x0 + 4, y1 - y0 + 4))
    others = []
    for t in b.GetTracks():
        if t.GetNetname() not in (net,) + tuple(ignore) and t.GetBoundingBox().Intersects(box):
            others.append(t)
    for f in b.GetFootprints():
        for p in f.Pads():
            if p.GetNetname() != net and p.GetBoundingBox().Intersects(box):
                others.append(p)
    near_items = [t for t in b.GetTracks() if t.GetBoundingBox().Intersects(box)] + \
        [p for f in b.GetFootprints() for p in f.Pads() if p.GetBoundingBox().Intersects(box)]
    # Hole spacing applies to every net; SMD pads of every net keep vias out (no via-in-pad).
    holes = [(t.GetX() / MM, t.GetY() / MM, t.GetDrill() / MM) for t in near_items if t.Type() == pcbnew.PCB_VIA_T]
    holes += [(p.GetX() / MM, p.GetY() / MM, p.GetDrillSize().x / MM) for p in near_items
              if p.Type() == pcbnew.PCB_PAD_T and p.GetDrillSize().x > 0]
    smd = [p for p in near_items if p.Type() == pcbnew.PCB_PAD_T and p.GetDrillSize().x == 0]
    edge = b.GetBoardEdgesBoundingBox()

    def hit(x, y, layer, r):
        pt = P(x, y)
        if not edge.Contains(pt):
            return True
        for o in others:
            if o.IsOnLayer(layer) and o.HitTest(pt, int(r * MM)):
                return True
        return False

    nx, ny = int((x1 - x0) / G) + 1, int((y1 - y0) / G) + 1
    free = {}
    def track_ok(i, j, li):
        k = (i, j, li)
        if k not in free:
            free[k] = not hit(x0 + i * G, y0 + j * G, LAYERS[li], width / 2 + CLR)
        return free[k]
    vfree = {}
    def via_ok(i, j):
        if (i, j) not in vfree:
            x, y = x0 + i * G, y0 + j * G
            vfree[(i, j)] = all(not hit(x, y, l, VIA_D / 2 + CLR) for l in
                                (pcbnew.F_Cu, pcbnew.B_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu)) and \
                all(math.hypot(x - hx, y - hy) >= (VIA_DRILL + hd) / 2 + HOLE2HOLE for hx, hy, hd in holes) and \
                not any(p.HitTest(P(x, y), int(VIA_D / 2 * MM)) for p in smd)
        return vfree[(i, j)]

    plane = [zn for zn in b.Zones() if to_plane and zn.GetNetname() == net and zn.GetLayer() == PLANES[net]]
    def on_plane(i, j):
        x, y = x0 + i * G, y0 + j * G
        return any(zn.HitTestFilledArea(zn.GetLayer(), P(x + dx, y + dy)) for zn in plane
                   for dx, dy in ((0, 0), (0.5, 0), (-0.5, 0), (0, 0.5), (0, -0.5)))

    def cell(x, y): return int(round((x - x0) / G)), int(round((y - y0) / G))
    si, sj = cell(ax, ay); gi, gj = cell(zx, zy)
    starts = [0, 1] if al == '*' else [0 if al == 'F' else 1]
    goals = {0, 1} if zl == '*' else {0 if zl == 'F' else 1}
    near = lambda i, j, ci, cj: abs(i - ci) <= 6 and abs(j - cj) <= 6   # inside the pad itself
    h = (lambda i, j: 0.0) if to_plane else (lambda i, j: math.hypot(i - gi, j - gj))
    pq = [(h(si, sj), 0.0, si, sj, l) for l in starts]
    prev = {(si, sj, l): None for l in starts}
    cost = {(si, sj, l): 0.0 for l in starts}
    steps = [(1, 0, 1), (-1, 0, 1), (0, 1, 1), (0, -1, 1), (1, 1, 1.42), (1, -1, 1.42), (-1, 1, 1.42), (-1, -1, 1.42)]
    end = None
    while pq:
        _, c, i, j, l = heapq.heappop(pq)
        if to_plane:
            if not (al != '*' and near(i, j, si, sj)) and via_ok(i, j) and on_plane(i, j):
                end = (i, j, l)
                break
        elif (i, j) == (gi, gj) and l in goals:
            end = (i, j, l)
            break
        if c > cost[(i, j, l)]:
            continue
        nbrs = [(i + di, j + dj, l, w) for di, dj, w in steps]
        nbrs.append((i, j, 1 - l, 12.0))
        for ni, nj, nl, w in nbrs:
            if not (0 <= ni < nx and 0 <= nj < ny):
                continue
            if nl != l:
                # No via inside an SMD end pad (only through-hole ends, '*', may take one).
                if not via_ok(i, j) or (near(i, j, si, sj) and al != '*') or (near(i, j, gi, gj) and zl != '*'):
                    continue
            elif not (near(ni, nj, si, sj) or near(ni, nj, gi, gj) or track_ok(ni, nj, nl)):
                continue
            nc = c + w
            if nc < cost.get((ni, nj, nl), 1e18):
                cost[(ni, nj, nl)] = nc
                prev[(ni, nj, nl)] = (i, j, l)
                heapq.heappush(pq, (nc + h(ni, nj), nc, ni, nj, nl))
    if end is None:
        return None
    path = []
    k = end
    while k is not None:
        path.append(k)
        k = prev[k]
    path.reverse()
    pts = [(x0 + i * G, y0 + j * G, l) for i, j, l in path]
    if to_plane:
        x, y, l = pts[-1]
        pts.append((x, y, 1 - l))     # the via onto the plane
    return pts

def commit(b, net, path, width):
    ni = b.FindNet(net)
    # Collapse runs that keep the same direction and layer into single segments.
    pts = [path[0]]
    for k in range(1, len(path) - 1):
        (xa, ya, la), (xb, yb, lb), (xc, yc, lc) = pts[-1], path[k], path[k + 1]
        same_dir = la == lb == lc and abs((xb - xa) * (yc - yb) - (yb - ya) * (xc - xb)) < 1e-9
        if not same_dir:
            pts.append(path[k])
    pts.append(path[-1])
    for (xa, ya, la), (xb, yb, lb) in zip(pts, pts[1:]):
        if la != lb:
            v = pcbnew.PCB_VIA(b)
            v.SetPosition(P(xa, ya)); v.SetWidth(int(VIA_D * MM)); v.SetDrill(int(VIA_DRILL * MM))
            v.SetNet(ni); b.Add(v)
        elif (xa, ya) != (xb, yb):
            t = pcbnew.PCB_TRACK(b)
            t.SetStart(P(xa, ya)); t.SetEnd(P(xb, yb)); t.SetWidth(int(width * MM))
            t.SetLayer(LAYERS[la]); t.SetNet(ni); b.Add(t)
    return pts

def end_of(item):
    """(x, y, layer) for a DRC unconnected item, or None for zones."""
    d = item['description']
    x, y = item['pos']['x'], item['pos']['y']
    if d.startswith('PTH pad') or d.startswith('Via'):
        return x, y, '*'
    if ' on F.Cu' in d:
        return x, y, 'F'
    if ' on B.Cu' in d:
        return x, y, 'B'
    return None

def close_from_drc(path):
    import json
    b = pcbnew.LoadBoard(PCB)
    widths = {nc: b.GetDesignSettings().m_NetSettings.GetNetClassByName(nc).GetTrackWidth() / MM
              for nc in ('Default', 'PWR3V3', 'PWR5V', 'USB')}
    for u in json.load(open(path))['unconnected_items']:
        a, z = (end_of(i) for i in u['items'])
        net = u['items'][0]['description'].split('[')[1].split(']')[0]
        if not a or not z:
            print('skip', net, '(zone)')
            continue
        nc = b.FindNet(net).GetNetClassName()
        w = widths.get(nc, 0.2)
        found = route(b, net, a, z, w)
        if found:
            commit(b, net, found, w)
        elif net in PLANES:
            # Tie each end to the plane instead.
            found = [route(b, net, e, None, w) for e in (a, z)]
            for f in found:
                if f:
                    commit(b, net, f, w)
            found = all(found)
        print(net, 'closed' if found else 'NO PATH', a, z)
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    pcbnew.SaveBoard(PCB, b)

if __name__ == '__main__':
    if sys.argv[1] == '--from-drc':
        close_from_drc(sys.argv[2])
        sys.exit(0)
    args = sys.argv[1:]
    dry = '--dry' in args
    ignore = [args[k + 1] for k, v in enumerate(args) if v == '--ignore']
    args = [v for k, v in enumerate(args) if v not in ('--dry', '--ignore') and (k == 0 or args[k - 1] != '--ignore')]
    net = args[0]
    a = (float(args[1]), float(args[2]), args[3])
    z = (float(args[4]), float(args[5]), args[6])
    width = float(args[7]) if len(args) > 7 else 0.2
    b = pcbnew.LoadBoard(PCB)
    path = route(b, net, a, z, width, ignore)
    if not path:
        sys.exit('no path for %s' % net)
    pts = commit(b, net, path, width)
    print(net, 'path', [(round(x, 2), round(y, 2), 'FB'[l]) for x, y, l in pts])
    if dry:
        sys.exit(0)
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    pcbnew.SaveBoard(PCB, b)
