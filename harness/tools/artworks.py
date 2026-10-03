"""The drawings How it works shows -- each written as an illustrator would draw it.

Every drawing is its stroke ORDER: gesture and silhouette, then form, then
detail, then a few accents last. Coordinates are Pad's 4:3 canvas (816 x 612).
Points are hand-placed control points; artdraw.py makes them a hand's line.
Three colours at most: Skribl purple, one accent, a dark ink, on paper.
"""
from artdraw import INK, PURPLE, Stroke as S

PINK = "#ff6f91"


def _tilt(strokes, deg, cx=408, cy=320):
    import math
    a = math.radians(deg); c, s_ = math.cos(a), math.sin(a)
    for st in strokes:
        st.pts = [(cx + (x - cx) * c - (y - cy) * s_, cy + (x - cx) * s_ + (y - cy) * c) for x, y in st.pts]
    return strokes


def _dot(cx, cy, r):
    """A small solid round: one tight turn and a half, closing on the middle."""
    import math
    pts = [(cx + r * (1 - k / 14) * math.cos(-1.2 + k * 0.67), cy + r * (1 - k / 14) * math.sin(-1.2 + k * 0.67))
           for k in range(15)]
    return pts


def cat():
    """A cat, head and shoulders, head tipped: sixteen strokes, one idea -- the
    face. Silhouette, then the body, then the eyes (purple, then the lids), the
    pink nose, the mouth, and three whiskers flicked on each side last."""
    return _tilt([
        # ears and the top of the head in one sweep: heavy at the ear roots,
        # thin at the tips and across the top where it turns into the light
        S([(316, 250), (300, 180), (306, 112), (344, 158), (376, 190), (410, 184),
           (446, 190), (488, 162), (538, 132), (520, 196), (504, 252)], "gesture",
          weight=[(0, 0.85), (0.16, 0.45), (0.3, 1.0), (0.5, 0.7), (0.68, 1.0), (0.82, 0.4), (1, 0.95)]),
        # cheeks and jaw, fullest at the bottom, a tuft at each cheek
        S([(314, 244), (300, 282), (290, 312), (282, 330), (296, 336), (306, 370), (340, 402), (384, 420),
           (432, 418), (478, 400), (510, 368), (520, 338), (532, 330), (520, 304), (506, 248)], "gesture",
          weight=[(0, 0.6), (0.45, 1.0), (0.7, 1.0), (1, 0.55)]),
        # the body: two falling lines that taper away
        S([(336, 404), (300, 456), (282, 520), (280, 596)], "contour", size=10,
          taper=(0.08, 0.55), weight=[(0, 1.0), (1, 0.5)]),
        S([(482, 400), (526, 452), (548, 520), (554, 596)], "contour", size=10,
          taper=(0.08, 0.55), weight=[(0, 1.0), (1, 0.5)]),
        # eyes: the purple iris, glancing to her left, then the almond over it
        S(_dot(381, 297, 7), "fill", PURPLE, size=11),
        S(_dot(467, 297, 7), "fill", PURPLE, size=11),
        S([(340, 300), (356, 284), (380, 280), (400, 294), (384, 312), (360, 314), (342, 302)], "detail", size=6.5,
          weight=[(0, 0.7), (0.3, 1.0), (0.55, 0.9), (0.75, 0.45), (1, 0.55)]),
        S([(424, 296), (442, 280), (468, 282), (486, 298), (466, 312), (442, 312), (426, 298)], "detail", size=6.5,
          weight=[(0, 0.7), (0.3, 1.0), (0.55, 0.9), (0.75, 0.45), (1, 0.55)]),
        # the nose, the accent, then the mouth in one stroke
        S([(398, 342), (418, 342), (408, 355), (401, 345), (412, 346)], "fill", PINK, size=10),
        S([(383, 374), (396, 378), (407, 364), (419, 378), (432, 373)], "detail", weight=[(0, 0.6), (0.5, 1.0), (1, 0.6)]),
        # three whiskers each side, fanned, flicked out fast
        S([(368, 358), (318, 348), (262, 340)], "accent", taper=(0.05, 0.6)),
        S([(368, 366), (316, 364), (258, 366)], "accent", taper=(0.05, 0.6)),
        S([(370, 374), (320, 382), (266, 394)], "accent", taper=(0.05, 0.6)),
        S([(448, 358), (500, 346), (556, 338)], "accent", taper=(0.05, 0.6)),
        S([(448, 366), (502, 362), (560, 364)], "accent", taper=(0.05, 0.6)),
        S([(446, 374), (498, 380), (552, 392)], "accent", taper=(0.05, 0.6)),
    ], -6)


def _blob(cx, cy, rx, ry, turns=2.2, n=26, start=1.0):
    """Colour laid in with a loose spiral that closes on the middle."""
    import math
    return [(cx + rx * start * (1 - k / n) ** 0.8 * math.cos(-0.9 + 2 * math.pi * turns * k / n),
             cy + ry * start * (1 - k / n) ** 0.8 * math.sin(-0.9 + 2 * math.pi * turns * k / n)) for k in range(n + 1)]


def _sharp(pts, d=4):
    """Keep a polyline's corners: a point just either side of each one, so the
    smoothed hand turns there instead of rounding the corner off."""
    import math

    def toward(p, q):
        L = math.hypot(q[0] - p[0], q[1] - p[1]) or 1
        return (p[0] + (q[0] - p[0]) * d / L, p[1] + (q[1] - p[1]) * d / L)
    out = [pts[0]]
    for a, b, c in zip(pts, pts[1:], pts[2:]):
        out += [toward(b, a), b, toward(b, c)]
    return out + [pts[-1]]


def _arc(cx, cy, rx, ry, a0, a1, n=10):
    import math
    return [(cx + rx * math.cos(math.radians(a0 + (a1 - a0) * k / n)),
             cy + ry * math.sin(math.radians(a0 + (a1 - a0) * k / n))) for k in range(n + 1)]


def scene():
    """A cottage on a hill, a tree beside it, mountains far off: depth in a
    few lines. Near is heavy and dark, far is thin and purple; the tree's
    canopy is painted over the mountains, so they pass behind it. The hill
    first, then the cottage, the tree, the far range, the path towards us,
    and a few accents last."""
    return [
        # the hill: the ground of the whole picture, heaviest nearest the middle
        S([(30, 432), (220, 402), (400, 392), (600, 398), (790, 424)], "gesture", size=10,
          weight=[(0, 0.5), (0.45, 1.0), (1, 0.45)], taper=(0.06, 0.12)),
        # the cottage: walls in one stroke, the roof over them, the door, the
        # chimney. Corners stay corners: a hand slows into a corner and turns.
        S(_sharp([(300, 300), (300, 396), (460, 396), (460, 300)]), "contour", size=9,
          weight=[(0, 0.7), (0.4, 1.0), (1, 0.75)]),
        S(_sharp([(280, 318), (380, 222), (480, 318)]), "contour", size=10, weight=[(0, 0.8), (0.5, 1.0), (1, 0.85)]),
        S(_sharp([(368, 396), (368, 352), (392, 352), (392, 396)]), "form", size=6.5),
        S(_sharp([(440, 280), (440, 248), (458, 248), (458, 297)]), "form", size=6),
        # the tree: trunk, then the canopy painted over it, then its shadow side
        S([(586, 404), (590, 350), (596, 292)], "contour", size=11, weight=[(0, 1.0), (1, 0.6)], taper=(0.05, 0.2)),
        S(_blob(600, 256, 60, 52, turns=2.8, n=40, start=0.9), "fill", PURPLE, size=28, peak=0.95, pace=2.0, taper=(0.03, 0.05)),
        S(_arc(600, 256, 66, 58, -10, 120), "form", size=6, weight=[(0, 0.4), (0.5, 1.0), (1, 0.4)]),
        # far: the mountains, thin and purple, broken where the cottage stands
        S([(30, 352), (110, 262), (160, 304), (232, 220), (290, 290)], "form", PURPLE, size=6, peak=0.75,
          weight=[(0, 0.5), (0.35, 1.0), (0.7, 0.8), (1, 0.4)]),
        S([(474, 300), (512, 258), (548, 226)], "form", PURPLE, size=6, peak=0.75,
          weight=[(0, 0.4), (1, 0.9)]),
        S([(660, 236), (700, 200), (790, 300)], "form", PURPLE, size=6, peak=0.75,
          weight=[(0, 0.9), (0.3, 1.0), (1, 0.5)]),
        # the sun, high and small, the accent colour
        S(_blob(712, 104, 20, 20, turns=3.0, n=30), "fill", PINK, size=16, pace=1.6),
        # the path, widening as it comes to us
        S([(372, 398), (356, 452), (316, 522), (282, 610)], "contour", size=8,
          weight=[(0, 0.3), (1, 1.0)], taper=(0.04, 0.1)),
        S([(388, 398), (410, 452), (416, 522), (468, 610)], "contour", size=8,
          weight=[(0, 0.3), (1, 1.0)], taper=(0.04, 0.1)),
        # accents: the lit window, the smoke, two birds
        S(_sharp([(420, 326), (444, 326), (444, 352), (420, 352), (420, 327)]), "detail", size=5),
        S(_blob(432, 339, 7, 7, turns=1.6, n=12), "fill", PURPLE, size=11),
        S([(449, 240), (442, 222), (454, 206), (446, 188)], "accent", size=4.5),
        S([(150, 140), (162, 150), (172, 140), (182, 150), (194, 140)], "accent", size=4.5),
    ]


def snail():
    """One line that becomes something: it begins as a spiral and becomes a
    snail, out of the shell, along its body, up the head and both feelers,
    and away along the ground."""
    import math
    spiral = []
    for k in range(56):
        u = k / 55
        a = -math.pi / 2 + u * 2.6 * 2 * math.pi
        # A shell, not a compass: whorls widen faster as they grow, the centre
        # drifts toward the opening, and the oval leans and breathes a little.
        r = 6 + 120 * u ** 0.82
        ox = 1.08 + 0.06 * math.sin(3 * a + 0.7)
        cx, cy = 392 - 16 * u, 352 + 10 * u
        spiral.append((cx + r * ox * math.cos(a) + 3 * math.sin(5.3 * u), cy + r * 0.96 * math.sin(a)))
    path = spiral + [(300, 470), (420, 474), (560, 470), (618, 456), (636, 414), (646, 360), (652, 318),
                     (642, 300), (660, 296), (664, 318), (662, 360), (676, 316), (694, 296), (708, 306),
                     (690, 326), (674, 372), (684, 430), (702, 466), (740, 474), (790, 470)]
    return [S(path, "gesture", PURPLE, size=11, pace=0.85,
              weight=[(0, 0.35), (0.3, 0.8), (0.55, 1.0), (0.75, 0.75), (0.9, 1.0), (1, 0.5)], taper=(0.04, 0.08))]


def tool_pen():
    """Pen: one flowing loop line that swells where the pen presses and thins
    at the ends, then a quick pink swoosh under it."""
    import math
    loops = []
    for k in range(110):
        u = 3.6 * 2 * math.pi * k / 109 - 0.6
        # a cursive run of tall loops: forward, round the top, back down
        loops.append((150 + 22 * u + 38 * math.sin(u), 320 - 96 * (0.5 - 0.5 * math.cos(u)) - 12 * math.sin(u)))
    return [
        S(loops, "gesture", PURPLE, size=20, pace=0.85, taper=(0.08, 0.18),
          weight=[(0, 0.3), (0.12, 1.0), (0.25, 0.3), (0.4, 1.0), (0.53, 0.3), (0.68, 1.0), (0.82, 0.3), (1, 0.6)]),
        S([(160, 420), (360, 404), (560, 414), (660, 398)], "accent", PINK, size=11, pace=1.3, taper=(0.06, 0.6)),
    ]


def tool_eraser():
    """Eraser: a purple heart, then one sweep of the eraser wipes a clean
    channel back to the paper."""
    import math

    def heart(side):
        pts = []
        for k in range(19):
            a = min(math.pi, math.pi * k / 16) * side
            x = 16 * math.sin(a) ** 3
            y = 13 * math.cos(a) - 5 * math.cos(2 * a) - 2 * math.cos(3 * a) - math.cos(4 * a)
            pts.append((408 + 11.5 * x, 300 - 11.5 * y))
        return pts
    return [
        S(heart(-1), "contour", PURPLE, size=30, weight=[(0, 0.7), (0.5, 1.0), (1, 0.8)]),
        S(heart(+1), "contour", PURPLE, size=30, weight=[(0, 0.7), (0.5, 1.0), (1, 0.8)]),
        S([(560, 150), (470, 262), (370, 392), (300, 470)], "form", INK, size=14, pace=0.8,
          taper=(0.02, 0.02), tool="eraser"),
    ]


def tool_shape():
    """Shape: three shapes dropped in, each a press and a drag -- a rounded
    box, a circle, a five-sided shape."""
    return [
        S([(96, 236), (196, 330), (300, 440)], "form", PURPLE, size=14, pace=0.35, tool="shape",
          shape={"kind": "rect", "radius": 34}),
        S([(330, 168), (430, 262), (532, 372)], "form", INK, size=14, pace=0.35, tool="shape",
          shape={"kind": "ellipse"}),
        S([(560, 246), (650, 330), (742, 428)], "form", PINK, size=14, pace=0.35, tool="shape",
          shape={"kind": "poly", "sides": 5, "radius": 20}),
    ]


def footballer():
    """A footballer kneeling in celebration -- from a traced line drawing the
    owner supplied, cleaned up (art/footballer.json): 331 traced fragments
    joined into a few dozen long lines and brand marks left off. (Its ball was
    rebuilt once and taken out again at the owner's word.) The long outlines
    go down first, then the inner lines, the face last."""
    import json
    import math
    import pathlib
    d = json.loads((pathlib.Path(__file__).parent / "art" / "footballer.json").read_text())
    x0, y0, w, h = 38, 21, 868, 960
    s = min((816 - 40) / w, (612 - 40) / h)
    ox, oy = (816 - w * s) / 2, (612 - h * s) / 2
    m = lambda pts: [((x - x0) * s + ox, (y - y0) * s + oy) for x, y in pts]
    L = lambda p: sum(math.dist(a, b) for a, b in zip(p, p[1:]))
    fig = sorted(d["figure"], key=L, reverse=True)
    face = lambda p: all(395 <= x <= 565 and 60 <= y <= 220 for x, y in p)
    outlines = [p for p in fig if L(p) > 200 and not face(p)]
    inner = sorted((p for p in fig if L(p) <= 200 and not face(p)), key=lambda p: min(y for _, y in p))
    faces = [p for p in fig if face(p)]
    out = [S(m(p), "contour", size=6.5, pace=1.2, weight=[(0, 0.6), (0.5, 1.0), (1, 0.6)]) for p in outlines]
    out += [S(m(p), "detail", size=4.5, pace=1.3) for p in inner]
    out += [S(m(p), "detail", size=4, pace=1.0) for p in faces]
    return out


def skull():
    """A skull in a fedora, sunglasses, a mustache and a long beard -- from a
    vector the owner supplied (art/skull.json). Its lines were filled outlines,
    so each became the pen stroke down its middle; its solid parts (the hat
    band, the lenses, the nose, the cheekbones) became scribbled fills. Drawn
    top down the way the picture is read: the hat, the glasses, the face, the
    mustache and teeth, then the beard, long lines before short in each."""
    import json
    import math
    import pathlib
    d = json.loads((pathlib.Path(__file__).parent / "art" / "skull.json").read_text())
    x0, y0, w, h = 50, 25, 1045, 1327
    s = min((816 - 40) / w, (612 - 40) / h)
    ox, oy = (816 - w * s) / 2, (612 - h * s) / 2
    m = lambda pts: [((x - x0) * s + ox, (y - y0) * s + oy) for x, y in pts]
    L = lambda p: sum(math.dist(a, b) for a, b in zip(p, p[1:]))
    band = lambda p: (0 if sum(y for _, y in p) / len(p) < 420 else
                      1 if sum(y for _, y in p) / len(p) < 620 else
                      2 if sum(y for _, y in p) / len(p) < 900 else 3)
    items = [(band(p), 0, -L(p), S(m(p), "detail", size=5.6, pace=1.15)) for p in d["lines"]]
    items += [(band(f), 1, -L(f), S(m(f), "fill", size=10.5, pace=2.2, taper=(0.03, 0.04))) for f in d["fills"]]
    return [it[3] for it in sorted(items, key=lambda it: it[:3])]


ART = {"cat": cat, "scene": scene, "snail": snail, "footballer": footballer, "skull": skull,
       # the tool cards' examples (Pen, Eraser, Shape)
       "pen": tool_pen, "eraser": tool_eraser, "shape": tool_shape}
