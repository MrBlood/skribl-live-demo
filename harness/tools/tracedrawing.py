"""A picture, as the strokes a person would draw it with.

The owner's verdict on the first examples was that the drawings looked plain;
a flower built from loops in code does not look like a drawing however well
it moves. So an example can start from a real picture -- the owner offered
images to copy -- and this turns its lines into strokes for the hand model:

  1. INK: the picture's lines, separated from its ground (Otsu threshold, on
     whichever side of it the lines are).
  2. CENTRE LINES: the ink thinned to one pixel (skeletonize), with the line's
     own width kept from the distance to the ink's edge, so a bold line in the
     picture is a heavy stroke and a fine one light.
  3. STROKES: the centre lines walked into paths -- through junctions along the
     straightest continuation, the way a pen keeps going -- with whiskers too
     short to be marks dropped.
  4. ORDER: big shapes first, then detail, each stroke starting at the end
     nearest where the pen last lifted, so the drawing builds up the way a
     person sketches rather than in scanline order.
  5. COLOUR: each stroke takes the picture's colour under it.

Returns strokes in canvas units, fitted into the canvas with a margin:
[{"path": [(x, y), ...], "width": px, "color": "#rrggbb"}].
Needs scikit-image (a tool dependency only; the app does not use it).
"""
import math

import numpy as np
from PIL import Image
from skimage.filters import threshold_otsu
from skimage.morphology import remove_small_objects, skeletonize
from scipy import ndimage

NB = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]


def _ink(img, invert=None):
    """Ink is whatever differs clearly from the picture's ground -- by COLOUR,
    not brightness alone, or a mid-tone green line reads as ground."""
    if img.mode in ("RGBA", "LA"):
        a = np.asarray(img.convert("RGBA"))[..., 3]
        if a.min() < 250:
            return a > 40                                 # a transparent PNG: ink is opaque
    rgb = np.asarray(img.convert("RGB"), dtype=float)
    border = np.concatenate([rgb[0], rgb[-1], rgb[:, 0], rgb[:, -1]])
    ground = np.median(border, axis=0)
    diff = np.sqrt(((rgb - ground) ** 2).sum(axis=2))
    th = max(45.0, threshold_otsu(diff))
    return diff > th


def _walk(sk, rgb=None):
    """Skeleton pixels -> strokes. The skeleton is cut into segments at every
    junction; then, at each junction, the pair of segments that carry on most
    nearly straight (within 40 degrees, and of a like colour) are rejoined --
    the way a pen keeps going through a crossing -- and the rest end there."""
    pts = set(zip(*np.nonzero(sk)))
    nb = lambda p: [(p[0] + dy, p[1] + dx) for dy, dx in NB if (p[0] + dy, p[1] + dx) in pts]
    deg = {p: len(nb(p)) for p in pts}
    node = lambda p: deg[p] != 2
    seen, segs = set(), []
    ek = lambda a, b: (a, b) if a < b else (b, a)
    for s in [p for p in pts if node(p)]:
        for n0 in nb(s):
            if ek(s, n0) in seen:
                continue
            seg = [s, n0]; seen.add(ek(s, n0))
            while not node(seg[-1]):
                nxt = [n for n in nb(seg[-1]) if ek(seg[-1], n) not in seen]
                if not nxt:
                    break
                seen.add(ek(seg[-1], nxt[0])); seg.append(nxt[0])
            segs.append(seg)
    # Closed loops with no junction at all (a circle on its own).
    rest = pts - {p for sg in segs for p in sg}
    while rest:
        s = min(rest); loop = [s]; rest.discard(s)
        while True:
            nxt = [n for n in nb(loop[-1]) if n in rest]
            if not nxt:
                break
            loop.append(nxt[0]); rest.discard(nxt[0])
        if len(loop) > 2:
            loop.append(loop[0])
        segs.append(loop)

    def tangent(seg, at_start):
        q = seg if at_start else seg[::-1]
        a, b = q[0], q[min(len(q) - 1, 10)]
        v = (b[0] - a[0], b[1] - a[1]); L = math.hypot(*v) or 1
        return (v[0] / L, v[1] / L)

    def colour(seg):
        if rgb is None:
            return np.zeros(3)
        return np.median(rgb[[p[0] for p in seg], [p[1] for p in seg]], axis=0)

    ends = {}                               # node -> [(seg index, at_start)]
    for i, sg in enumerate(segs):
        if sg[0] == sg[-1] and len(sg) > 2 and not node(sg[0]):
            continue
        ends.setdefault(sg[0], []).append((i, True))
        ends.setdefault(sg[-1], []).append((i, False))
    link = {}                               # (seg, at_start) -> (seg, at_start)
    cols = [colour(sg) for sg in segs]
    for nd, es in ends.items():
        es = [e for e in es if e not in link]
        pairs = []
        for i in range(len(es)):
            for j in range(i + 1, len(es)):
                (a, sa), (b, sb) = es[i], es[j]
                if a == b:
                    continue
                ta, tb = tangent(segs[a], sa), tangent(segs[b], sb)
                straight = -(ta[0] * tb[0] + ta[1] * tb[1])      # 1 = carries straight on
                if straight > math.cos(math.radians(40)) and np.abs(cols[a] - cols[b]).sum() < 90:
                    pairs.append((straight, es[i], es[j]))
        for _, e1, e2 in sorted(pairs, reverse=True):
            if e1 in link or e2 in link:
                continue
            link[e1] = e2; link[e2] = e1
    out, done = [], set()
    for i in range(len(segs)):
        if i in done:
            continue
        # Walk back to a free end, then forward along the links.
        cur, start = i, True
        guard = 0
        while (cur, start) in link and guard < len(segs):
            j, sj = link[(cur, start)]
            cur, start = j, not sj
            guard += 1
            if cur == i:
                break
        path, c, at = [], cur, start
        while c is not None and c not in done:
            done.add(c)
            piece = segs[c] if at else segs[c][::-1]
            path.extend(piece if not path else piece[1:])
            nxt = link.get((c, not at))
            c, at = (nxt[0], nxt[1]) if nxt else (None, None)
        out.append(path)
    return out


def _rdp(pts, eps):
    if len(pts) < 3:
        return pts
    (x0, y0), (x1, y1) = pts[0], pts[-1]
    dx, dy = x1 - x0, y1 - y0; L = math.hypot(dx, dy) or 1e-9
    dmax, idx = -1, 0
    for i in range(1, len(pts) - 1):
        d = abs(dy * pts[i][0] - dx * pts[i][1] + x1 * y0 - y1 * x0) / L
        if d > dmax:
            dmax, idx = d, i
    if dmax > eps:
        return _rdp(pts[:idx + 1], eps)[:-1] + _rdp(pts[idx:], eps)
    return [pts[0], pts[-1]]


def trace(path, *, canvas=(816, 612), margin=0.08, min_len=10, invert=None, max_px=900):
    img = Image.open(path)
    img.thumbnail((max_px, max_px))
    rgb = np.asarray(img.convert("RGB"))
    ink = _ink(img, invert)
    ink = remove_small_objects(ink, max_size=12)
    ink = ndimage.binary_closing(ink, iterations=1)
    dist = ndimage.distance_transform_edt(ink)
    sk = skeletonize(ink)
    raw = _walk(sk, rgb)
    # Fit the picture's ink box into the canvas, centred, with a margin.
    ys, xs = np.nonzero(ink)
    bx0, bx1, by0, by1 = xs.min(), xs.max(), ys.min(), ys.max()
    cw, ch = canvas
    sc = min(cw * (1 - 2 * margin) / max(1, bx1 - bx0), ch * (1 - 2 * margin) / max(1, by1 - by0))
    ox = (cw - (bx1 - bx0) * sc) / 2 - bx0 * sc
    oy = (ch - (by1 - by0) * sc) / 2 - by0 * sc
    strokes = []
    for p in raw:
        if len(p) < min_len:
            continue
        w = float(np.median([dist[y, x] for y, x in p])) * 2 * sc
        cols = rgb[[y for y, x in p], [x for y, x in p]]
        col = "#%02x%02x%02x" % tuple(int(v) for v in np.median(cols, axis=0))
        xy = [(x * sc + ox, y * sc + oy) for y, x in p]
        if len(xy) > 3 and math.hypot(xy[0][0] - xy[-1][0], xy[0][1] - xy[-1][1]) < 2:
            # A closed loop: simplified as two halves, or its matching ends
            # would collapse it to a point.
            h = len(xy) // 2
            xy = _rdp(xy[:h + 1], 0.6)[:-1] + _rdp(xy[h:], 0.6)
        else:
            xy = _rdp(xy, 0.6)
        strokes.append({"path": xy, "width": max(2.0, w), "color": col,
                        "len": sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(xy, xy[1:]))})
    return order(strokes)


def order(strokes):
    """Big shapes first, then detail; each stroke begins nearest the last lift."""
    if not strokes:
        return []
    big = sorted([s for s in strokes if s["len"] >= 60], key=lambda s: (min(p[1] for p in s["path"]), -s["len"]))
    small = [s for s in strokes if s["len"] < 60]
    out, pen = [], (big[0]["path"][0] if big else strokes[0]["path"][0])

    def gap(s):
        a, b = s["path"][0], s["path"][-1]
        return min(math.hypot(a[0] - pen[0], a[1] - pen[1]), math.hypot(b[0] - pen[0], b[1] - pen[1]))

    for sweep, group in ((True, big), (False, small)):
        rest = list(group)
        while rest:
            # The big shapes keep a top-down sweep, taking the nearest of the
            # next few; details go nearest-next.
            s = min(rest[:4], key=gap) if sweep else min(rest, key=gap)
            rest.remove(s)
            a, b = s["path"][0], s["path"][-1]
            if math.hypot(b[0] - pen[0], b[1] - pen[1]) < math.hypot(a[0] - pen[0], a[1] - pen[1]):
                s["path"] = list(reversed(s["path"]))
            out.append(s); pen = s["path"][-1]
    return out
