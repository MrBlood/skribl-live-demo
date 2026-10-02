"""Flip loops for How it works: pages drawn through the real Flip, key poses first.

Each loop is a list of PAGES; each page a list of Strokes (artdraw). A layer
that must not move (the ground, a body) is drawn once and the page DUPLICATED,
as an animator traces through onion skin, so its proportions are identical on
every page. Then the KEY poses are drawn, then the in-betweens. The last page
leads into the first, so the loop is seamless. Canvas 816 x 612 (4:3).
"""
import math

from artdraw import INK, PURPLE, Stroke as S

PINK = "#ff6f91"


def _ellipse(cx, cy, rx, ry, a0=-100, turns=1.04, n=20):
    pts = []
    for k in range(n + 1):
        a = math.radians(a0) + 2 * math.pi * turns * k / n
        pts.append((cx + rx * math.cos(a), cy + ry * math.sin(a)))
    return pts


def _fill(cx, cy, rx, ry, turns=3.2, n=46):
    """Colour laid in as an artist scribbles a fill: one loose spiral from the
    edge to the middle, so no ring leaves a gap of paper and none overshoots."""
    pts = []
    for k in range(n + 1):
        u = k / n
        a = math.radians(-60) + 2 * math.pi * turns * u
        f = 1 - u ** 0.9
        pts.append((cx + rx * f * math.cos(a), cy + ry * f * math.sin(a)))
    return pts


GROUND = 516


def bounce():
    """A ball bouncing in place: 10 pages at 12 fps. Spacing follows the fall
    (slow at the top, fast at the floor); it stretches along the fall and
    squashes flat on contact; its shadow grows as it comes down."""
    # (centre y, rx, ry) per page; page 0 is the top, page 5 the contact.
    # Big enough to read on a phone: the ball is a fifth of the page high.
    R = 66
    poses = [(118, 1.0, 1.0), (146, 0.98, 1.02), (226, 0.92, 1.1), (346, 0.84, 1.2), (GROUND - 80, 0.88, 1.16),
             (None, 1.42, 0.6), (GROUND - 86, 0.86, 1.16), (334, 0.88, 1.12), (214, 0.96, 1.04), (140, 1.0, 1.0)]
    poses = [((GROUND - R * sy) if cy is None else cy, R * sx, R * sy) for cy, sx, sy in poses]
    keys = [0, 5]                                   # drawn first, as an animator would
    order = keys + [i for i in range(len(poses)) if i not in keys]
    pages = {}
    for i, (cy, rx, ry) in enumerate(poses):
        h = (GROUND - (cy + ry)) / (GROUND - 184)   # 0 on the floor .. 1 at the top
        h = max(0, min(1, h)); sw = 0.9 * rx * (1 - 0.45 * h)
        out = [
            S(_fill(408, cy, rx - 10, ry - 10), "fill", PURPLE, size=24, peak=0.95, pace=2.4, taper=(0.03, 0.04)),
            # Heavy on the shadow side (lower right), light where it turns to the top-left light.
            S(_ellipse(408, cy, rx, ry, a0=-120), "contour", size=8, weight=[(0, 0.45), (0.3, 1.0), (0.55, 1.0), (0.8, 0.5), (1, 0.4)]),
            S([(408 - rx * 0.6, cy - ry * 0.12), (408 - rx * 0.5, cy - ry * 0.42), (408 - rx * 0.24, cy - ry * 0.62)], "accent", "#ffffff", size=7),
            S([(408 - sw, GROUND + 7), (408, GROUND + 8), (408 + sw, GROUND + 7)], "detail", INK,
              size=5 + 9 * (1 - h), peak=0.7, taper=(0.3, 0.3)),
        ]
        pages[i] = out
    return {"fps": 12, "base": [S([(140, GROUND + 9), (408, GROUND + 6), (676, GROUND + 9)], "gesture", size=7,
                                  weight=[(0, 0.4), (0.5, 1.0), (1, 0.4)])],
            "pages": [pages[i] for i in range(len(poses))], "order": order}


def _offset(path, d):
    """The polyline moved `d` px to its left: one side of a drawn tube."""
    out = []
    for k, (x, y) in enumerate(path):
        a = path[max(0, k - 1)]; b = path[min(len(path) - 1, k + 1)]
        dx, dy = b[0] - a[0], b[1] - a[1]; L = math.hypot(dx, dy) or 1
        out.append((x - dy / L * d, y + dx / L * d))
    return out


def _bean(cx, cy, h, w, side, n=14):
    """One side of a pear-shaped body, top to bottom, as an artist draws it."""
    pts = []
    for k in range(n + 1):
        u = math.pi * k / n
        ww = w + 24 * (1 - math.cos(u)) / 2
        pts.append((cx + side * ww * math.sin(u), cy - h * math.cos(u)))
    return pts


def _bean_fill(cx, cy, h, w, inset=20, step=21):
    """A marker's back-and-forth fill across the body, row by row, inside the
    line by `inset`: solid at a glance, and drawn the way a person colours in."""
    pts, side = [], 1
    y = cy - h + inset + 6
    while y < cy + h - inset:
        u = math.acos(max(-1, min(1, (cy - y) / h)))
        half = (w + 24 * (1 - math.cos(u)) / 2) * math.sin(u) - inset
        if half > 4:
            # Points just inside each end keep the smoothed turn from
            # bulging past the end of the row (and over the line).
            k = min(12, half / 3)
            row = [(cx - half, y), (cx - half + k, y), (cx + half - k, y), (cx + half, y)]
            pts += row if side > 0 else row[::-1]
            side = -side
        y += step
    return pts


def wave():
    """A character waving hello: 10 pages at 10 fps. The body is drawn once
    and the page duplicated, so it cannot drift; the arm is redrawn on every
    page, extremes first. The forearm lags the upper arm (follow-through), so
    the hand swings in an arc rather than a hinge; one page blinks."""
    cx, cy, h, w = 372, 330, 140, 104
    body = [
        S(_bean_fill(cx, cy, h, w), "fill", PURPLE, size=32, peak=0.95, pace=2.6, taper=(0.02, 0.03)),
        S(_bean(cx, cy, h, w, -1), "contour", size=11, weight=[(0, 0.5), (0.25, 0.8), (0.75, 1.0), (1, 0.6)]),
        S(_bean(cx, cy, h, w, +1), "contour", size=11, weight=[(0, 0.5), (0.3, 0.75), (0.8, 1.0), (1, 0.7)]),
        # feet, the resting arm and the ground shadow
        S([(318, 466), (306, 486), (340, 492), (352, 474)], "form", size=8),
        S([(398, 474), (404, 492), (440, 488), (432, 466)], "form", size=8),
        S([(272, 300), (252, 352), (246, 398)], "fill", PURPLE, size=30, pace=1.1, taper=(0.05, 0.1)),
        S(_offset([(272, 300), (252, 352), (246, 398)], 15), "form", size=6),
        S(_offset([(272, 300), (252, 352), (246, 398)], -15), "form", size=6),
        S(_fill(244, 414, 11, 11, turns=1.8, n=16), "fill", PURPLE, size=24, pace=2.0, taper=(0.03, 0.04)),
        S(_ellipse(244, 414, 21, 22, a0=-60), "form", size=7),
        S([(250, 504), (372, 498), (494, 504)], "detail", size=5, peak=0.5, taper=(0.3, 0.3)),
        # the face: a smile and a blush; the eyes are per page, for the blink
        S([(334, 326), (358, 346), (388, 328)], "detail", size=6, weight=[(0, 0.6), (0.5, 1.0), (1, 0.6)]),
        S([(400, 314), (414, 318), (404, 324), (418, 326)], "accent", PINK, size=8),
    ]
    S0, L1, L2 = (468, 300), 78, 70
    pages = []
    n = 10
    for i in range(n):
        ph = 2 * math.pi * i / n
        a1 = math.radians(36 + 8 * math.cos(ph))
        a2 = math.radians(12 + 42 * math.cos(ph - 1.0))
        E = (S0[0] + L1 * math.sin(a1), S0[1] - L1 * math.cos(a1))
        W = (E[0] + L2 * math.sin(a2), E[1] - L2 * math.cos(a2))
        H = (W[0] + 16 * math.sin(a2), W[1] - 16 * math.cos(a2))
        arm = [S0, E, W]
        out = [
            S(arm, "fill", PURPLE, size=30, pace=1.1, taper=(0.04, 0.06)),
            S(_offset(arm, 15), "contour", size=8, weight=[(0, 0.6), (0.5, 1.0), (1, 0.8)]),
            S(_offset(arm, -15), "form", size=6),
            S(_fill(H[0], H[1], 12, 12, turns=1.8, n=16), "fill", PURPLE, size=24, pace=2.0, taper=(0.03, 0.04)),
            S(_ellipse(H[0], H[1], 23, 24, a0=math.degrees(a2) + 90), "form", size=8),
        ]
        if i == 6:      # the blink
            out += [S([(334, 286), (344, 292), (354, 286)], "detail", size=6),
                    S([(376, 286), (386, 292), (396, 286)], "detail", size=6)]
        else:
            out += [S(_ellipse(344, 283, 7, 12, n=10), "detail", size=7),
                    S(_ellipse(386, 283, 7, 12, n=10), "detail", size=7)]
        # A flick of motion beside the hand at each extreme.
        if i in (1, 6):
            sgn = -1 if i == 1 else 1
            out.append(S([(H[0] + sgn * 40, H[1] - 30), (H[0] + sgn * 50, H[1]), (H[0] + sgn * 40, H[1] + 28)],
                         "accent", size=5))
        pages.append(out)
    keys = [1, 6]
    order = keys + [i for i in range(n) if i not in keys]
    return {"fps": 10, "base": body, "pages": pages, "order": order}


FLIPS = {"bounce": bounce, "wave": wave}
