"""The drawings How it works shows -- each written as an illustrator would draw it.

Every drawing is its stroke ORDER: gesture and silhouette, then form, then
detail, then a few accents last. Coordinates are Pad's 4:3 canvas (816 x 612).
Points are hand-placed control points; artdraw.py makes them a hand's line.
Three colours at most: Skribl purple, one accent, a dark ink, on paper.
"""
from artdraw import INK, PURPLE, Stroke as S

PINK = "#ff6f91"
EAR_PINK = "#f7a3b7"   # the softer pink inside a cat's ears


def cat():
    """A cat sitting up, glancing to her left -- the owner's own line drawing
    (art/cat.json): each line hand-placed along its path, then snapped onto
    the centre of the drawing's ink, whiskers fitted to their own thin lines.
    The head in one sweep over both ears, the cheek and jaw, the body, the
    tail, the legs and paws; then the pink in the ears, the purple eyes and
    their lids, the nose and mouth, and the whiskers flicked on last."""
    import json
    import pathlib
    d = json.loads((pathlib.Path(__file__).parent / "art" / "cat.json").read_text())
    xs = [x for st in d["strokes"] for x, _ in st["pts"]]
    ys = [y for st in d["strokes"] for _, y in st["pts"]]
    x0, y0, w, h = min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)
    s = min((816 - 60) / w, (612 - 48) / h)
    ox, oy = (816 - w * s) / 2, (612 - h * s) / 2
    m = lambda pts: [((x - x0) * s + ox, (y - y0) * s + oy) for x, y in pts]
    colour = {"ink": INK, "pink": PINK, "earpink": EAR_PINK, "purple": PURPLE}
    # Line weights from the drawing itself: outlines about 14px of its 1024,
    # legs and lids a little lighter, toes and whiskers fine.
    size = {"gesture": 9.5, "contour": 9.5, "form": 8.5, "detail": 6.0, "accent": 3.2, "fill": 9.0}
    out = []
    for st in d["strokes"]:
        role = st["role"]
        sz = 3.6 if st["name"].startswith("toe") else 11.0 if st["name"].startswith("iris") else size[role]
        kw = {"taper": (0.05, 0.6)} if role == "accent" else {"taper": (0.02, 0.02)} if role == "fill" else {}
        if role in ("gesture", "contour"):
            kw["weight"] = [(0, 0.75), (0.5, 1.0), (1, 0.75)]
        out.append(S(m(st["pts"]), role, colour[st["color"]], size=sz, **kw))
    return out


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


def tool_brushes():
    """Brush: the same easy wave drawn four times, top to bottom in the
    drawer's order, Pen, Marker, Pencil and Air, one colour, so the only
    difference is the brush. Air goes over its middle again, as it builds."""
    import math

    def wave(y, x0=150, x1=666, n=40):
        # The one wave across 150..666; a part of it keeps the whole's phase.
        return [(x, y - 24 * math.sin(2 * math.pi * 1.25 * (x - 150) / 516))
                for x in (x0 + (x1 - x0) * k / n for k in range(n + 1))]
    return [
        S(wave(132), "form", PURPLE, size=16, pace=0.9, taper=(0.08, 0.18), brush="pen"),
        S(wave(246), "form", PURPLE, size=16, pace=0.9, taper=(0.08, 0.18), brush="marker"),
        S(wave(360), "form", PURPLE, size=16, pace=0.9, taper=(0.08, 0.18), brush="pencil"),
        S(wave(474), "form", PURPLE, size=16, pace=0.9, taper=(0.08, 0.18), brush="airbrush"),
        S(wave(474, 300, 516, 18), "form", PURPLE, size=16, pace=0.9, taper=(0.35, 0.4), brush="airbrush"),
    ]


def tool_recolor():
    """Recolor: three balloons drawn in ink, outlines first, then the knots
    and the strings gathered in one hand. RECOLOR_TAPS colours them after,
    while the take still records, so the replay shows each one change."""
    import math

    def balloon(cx, cy, rx, ry, tilt):
        pts = []
        for k in range(37):
            a = -math.pi / 2 + 2 * math.pi * 1.04 * k / 36
            # a little fuller at the top, drawn to a soft point at the knot
            r = 1.0 - 0.10 * max(0.0, math.sin(a))
            x, y = rx * r * math.cos(a), ry * r * math.sin(a)
            pts.append((cx + x * math.cos(tilt) - y * math.sin(tilt), cy + x * math.sin(tilt) + y * math.cos(tilt)))
        return pts

    hand = (408, 548)
    tops = [(262, 212, 78, 96, -0.18), (408, 168, 82, 100, 0.0), (556, 222, 76, 94, 0.2)]
    out = [S(balloon(*b), "contour", INK, size=10, weight=[(0, 0.8), (0.5, 1.0), (1, 0.85)]) for b in tops]
    for cx, cy, rx, ry, tilt in tops:
        # The knot: a small closed triangle tied on at the balloon's foot.
        kx, ky = _on_balloon(cx, cy, rx, ry, tilt, math.pi / 2)
        ux, uy = -math.sin(tilt), math.cos(tilt)          # down the balloon's own axis
        px, py = math.cos(tilt), math.sin(tilt)           # across it
        tip = (kx - ux * 1.5, ky - uy * 1.5)
        a, b = (kx + ux * 11 - px * 7, ky + uy * 11 - py * 7), (kx + ux * 11 + px * 7, ky + uy * 11 + py * 7)
        out.append(S([tip, a, b, tip], "detail", INK, size=5, pace=1.2, taper=(0.05, 0.05)))
        base = (kx + ux * 11, ky + uy * 11)
        out.append(S([base, (base[0] + 10, base[1] + 80), (base[0] * 0.4 + hand[0] * 0.6 - 8, base[1] * 0.4 + hand[1] * 0.6), hand],
                     "detail", INK, size=3.5, pace=1.1, taper=(0.05, 0.3)))
    # A shine on each, last: a short arc inside its upper left.
    for cx, cy, rx, ry, tilt in tops:
        arc = [_on_balloon(cx, cy, rx * 0.66, ry * 0.66, tilt, a) for a in (3.55 + 0.11 * k for k in range(8))]
        out.append(S(arc, "accent", INK, size=4.5, pace=1.3, taper=(0.2, 0.4)))
    return out


# Recolor's drawing: after the lines, each balloon's outline is tapped with
# Recolor on, in the pen's colour of the moment, on its far side from the
# others (the middle one at its top): the left balloon's right edge lies
# inside the middle one's left, and a tap there took the middle balloon.
def _on_balloon(cx, cy, rx, ry, tilt, a):
    import math
    r = 1.0 - 0.10 * max(0.0, math.sin(a))
    x, y = rx * r * math.cos(a), ry * r * math.sin(a)
    return (cx + x * math.cos(tilt) - y * math.sin(tilt), cy + x * math.sin(tilt) + y * math.cos(tilt))


RECOLOR_TAPS = [("#ff6f91", _on_balloon(262, 212, 78, 96, -0.18, 3.1416)),
                ("#7c5cff", _on_balloon(408, 168, 82, 100, 0.0, -1.5708)),
                ("#ff6f91", _on_balloon(556, 222, 76, 94, 0.2, 0.0))]


class Words:
    """A line of words the Text tool writes, as a person uses it (make_art.py
    write_words): Shape's picker, Text, the words typed, a style and a size,
    placed with their middle at `at`, then Write it. They write themselves in
    at the hand's own pace (1x) while the take records, in the pen's colour
    and thickness, so the replay writes them again."""
    def __init__(self, text, at, *, style="skribl", size="L", color=INK, pen=9):
        self.text, self.at, self.style, self.size, self.color, self.pen = text, at, style, size, color, pen


def tool_text():
    """Text: a speech bubble in purple, its round in one line from the tail's
    right foot the long way to its left one, then the tail, a V down to its
    point and back; "hello!" writes itself inside it in Skribl's hand (the
    owner's own); a small pink heart is flicked on last."""
    import math
    cx, cy, a, b, n = 408, 290, 176, 104, 2.4

    def edge(t):
        c, s = math.cos(t), math.sin(t)
        return (cx + a * math.copysign(abs(c) ** (2 / n), c), cy + b * math.copysign(abs(s) ** (2 / n), s))
    # The tail's two feet on the bubble's underside, left of the middle.
    t_right, t_left = 0.57 * math.pi, 0.70 * math.pi
    round_ = [edge(t_right - (t_right - (t_left - 2 * math.pi)) * k / 40) for k in range(41)]
    lf, rf = edge(t_left), edge(t_right)
    tip = (lf[0] - 46, lf[1] + 84)
    tail = [lf, (lf[0] - 18, lf[1] + 40), tip, ((rf[0] + tip[0]) / 2 + 4, (rf[1] + tip[1]) / 2 - 6), rf]

    def heart(side, hx=cx + a + 34, hy=cy - b - 22, k=2.1):
        pts = []
        for i in range(15):
            u = min(math.pi, math.pi * i / 12) * side
            x = 16 * math.sin(u) ** 3
            y = 13 * math.cos(u) - 5 * math.cos(2 * u) - 2 * math.cos(3 * u) - math.cos(4 * u)
            pts.append((hx + k * x, hy - k * y))
        return pts
    return [
        S(round_, "contour", PURPLE, size=12, pace=1.3, taper=(0.05, 0.05),
          weight=[(0, 0.8), (0.35, 0.92), (0.75, 1.0), (1, 0.85)]),
        S(tail, "form", PURPLE, size=11, pace=1.1, taper=(0.04, 0.04)),
        Words("hello!", (cx, cy)),
        S(heart(-1), "accent", PINK, size=8, pace=1.4, taper=(0.1, 0.3)),
        S(heart(+1), "accent", PINK, size=8, pace=1.4, taper=(0.1, 0.3)),
    ]


def tool_mirror():
    """Mirror: a butterfly drawn on its left side with Mirror left to right on
    (make_art.py MIRROR), so its right side draws itself beside every stroke.
    The wings' outlines first, the body, the veins, then the pink spots and
    the antennae last. Everything here is the left half; the axis is the
    canvas's middle, x = 408."""
    up = [(400, 236), (362, 182), (302, 130), (234, 104), (180, 116), (152, 158), (158, 212), (194, 260),
          (260, 292), (330, 300), (398, 288)]
    low = [(398, 300), (350, 322), (298, 362), (262, 414), (268, 462), (306, 480), (352, 452), (384, 404), (400, 342)]
    body = [(408, 194), (397, 200), (393, 216), (400, 232), (396, 252), (391, 292), (393, 352), (400, 402), (408, 426)]
    return [
        S(up, "contour", PURPLE, size=12, weight=[(0, 0.7), (0.4, 1.0), (1, 0.8)]),
        S(low, "contour", PURPLE, size=11, weight=[(0, 0.7), (0.5, 1.0), (1, 0.8)]),
        S(body, "form", INK, size=8, taper=(0.06, 0.06)),
        S([(396, 262), (330, 220), (262, 166)], "detail", PURPLE, size=4.5, taper=(0.1, 0.5)),
        S([(396, 272), (300, 262), (206, 214)], "detail", PURPLE, size=4.5, taper=(0.1, 0.5)),
        S([(396, 318), (334, 380), (300, 440)], "detail", PURPLE, size=4.5, taper=(0.1, 0.5)),
        S(_blob(262, 214, 24, 21, turns=3.2, n=34), "fill", PINK, size=15, taper=(0.04, 0.04)),
        S(_blob(318, 420, 14, 13, turns=2.4, n=22), "fill", PINK, size=12, taper=(0.04, 0.04)),
        S([(403, 198), (390, 168), (372, 140), (354, 122), (342, 122), (342, 134), (352, 136)], "accent", INK,
          size=4.5, taper=(0.05, 0.4)),
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


def pug():
    """A pug sitting, head tipped, glancing up -- the owner's own coloured
    drawing (art/pug.json). Colour first, as a broad marker: the tan of him,
    the brown of his ears and muzzle, the purple of his eyes, each patch once
    round inside its edge and then back and forth across it. Then the ink on
    top, the head long lines before short, the pupils and the nose, then the
    body, legs, paws and the curled tail."""
    import json
    import math
    import pathlib
    d = json.loads((pathlib.Path(__file__).parent / "art" / "pug.json").read_text())
    xs = [x for p in d["lines"] for x, _ in p]
    ys = [y for p in d["lines"] for _, y in p]
    x0, y0, w, h = min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)
    s = min((816 - 60) / w, (612 - 40) / h)
    ox, oy = (816 - w * s) / 2, (612 - h * s) / 2
    m = lambda pts: [((x - x0) * s + ox, (y - y0) * s + oy) for x, y in pts]
    L = lambda p: sum(math.dist(a, b) for a, b in zip(p, p[1:]))
    colour = {"tan": "#fbe1c0", "brown": "#6d503f", "white": "#ffffff", "purple": PURPLE, "nose": INK, "pupil": INK}
    fill = lambda f: S(m(f["pts"]), "fill", colour[f["color"]], size=f["size"] * s * 1.25, pace=2.2,
                       peak=1.0, flat=True)
    # Full pressure and a touch wider: the editor thins a line with pressure,
    # and a light touch left the colour streaky. Each colour runs a little
    # under the lines that border it, so the ink covers its edge.
    by = lambda name: [fill(f) for f in sorted((f for f in d["fills"] if f["color"] == name), key=lambda f: -f["area"])]
    def disc(cx, cy, r, colour_, size):
        """A solid round: once round the rim, then a spiral to the middle."""
        (cx, cy), = m([(cx, cy)]); r *= s
        rim = [(cx + r * math.cos(k * 0.3), cy + r * math.sin(k * 0.3)) for k in range(22)]
        sp = [(cx + r * (1 - k / 24) * math.cos(6.6 + k * 0.5), cy + r * (1 - k / 24) * math.sin(6.6 + k * 0.5)) for k in range(1, 25)]
        # Slow: drawn fast, the editor joins too few points and a circle comes out a hexagon.
        return S(rim + sp, "fill", colour_, size=size, pace=0.6, peak=1.0, flat=True)
    # The eyes as the drawing has them, measured from it: a full purple iris,
    # a round pupil at its right edge. The nose a rounded dark shape.
    EYES = [((719, 376), (733, 372)), ((921, 309), (935, 305))]
    out = by("tan") + by("brown") + by("white")
    out += [disc(ic[0], ic[1], 20, PURPLE, 9.5) for ic, _ in EYES]
    head = lambda p: sum(y for _, y in p) / len(p) < 530
    # Ink at an even weight, as the drawing has it.
    line = lambda p: S(m(p), "detail", size=8.5, pace=1.15, peak=0.95, flat=True)
    out += [line(p) for p in sorted((p for p in d["lines"] if head(p)), key=L, reverse=True)]
    nose = [S(_blob(*m([(809, 384)])[0], 25 * s, 16 * s, turns=2.4, n=30), "fill", INK, size=9, pace=0.6, peak=1.0,
              flat=True)]
    out += nose + [disc(pc[0], pc[1], 11, INK, 8) for _, pc in EYES]
    out += [line(p) for p in sorted((p for p in d["lines"] if not head(p)), key=L, reverse=True)]
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


def blooby_card():
    """Blooby's trading card (blooby.py): colour, frame, title, Blooby, his name."""
    import blooby
    return blooby.card()


ART = {"cat": cat, "scene": scene, "snail": snail, "footballer": footballer, "skull": skull, "pug": pug,
       "blooby-card": blooby_card,
       # the tool cards' examples (Pen, Eraser, Shape, Brush, Recolor, Text, Mirror)
       "pen": tool_pen, "eraser": tool_eraser, "shape": tool_shape, "brushes": tool_brushes, "recolor": tool_recolor,
       "text": tool_text, "mirror": tool_mirror}
