#!/usr/bin/env python3
"""Blooby grows from small to full screen on his star, waving the whole time.

The owner asked for it after the Blooby cheer (v323): "make a blooby waving
start small then emerge at full screen ... keep star background logo and start
blooby small and grow full size -- show multiple interpretations". These are
the seven takes, A1 to E, that the owner has as .skribl files and a filmed
mock (FUTURE.md 6l). The owner picked C for Blooby's first hello; the app
plays the take `hello`, below.

Each take is a Flip drawn through the real Flip editor with real pen input
(artdraw), on a 9:16 canvas in the Home Screen icon's lilac:

  page 0      the star, kept UNDER every page after it (the logo's white
              six-point star, a soft lilac glow round it), drawn once
  growth      Blooby redrawn on every page, a little bigger each time, his
              arm at the next step of his wave
  loop        Blooby at full size waving, looped forever: his body drawn once
              and the page copied, then each page's arm and eyes (as
              make_flip.py draws the waving card)

Take E is the one exception: the star grows with him, so there is no page
underneath and every page carries both.

    python3 harness/tools/make_grow.py OUTDIR TAKE [TAKE ...]

Writes OUTDIR/<take>.skribl (exactly what Flip's "Save a backup" writes),
OUTDIR/<take>.json (the share payload) and OUTDIR/<take>.meta.json. Needs the
local server (SKRIBL_BASE). A page that draws itself replays at the pace its
pen events were sent, so a busy machine records it slower: take D's drawing-in
came out at about eight seconds on a loaded box.

THE HELLO AS MOCKED AT THE v323 SEAL (FUTURE.md 6m): take C with

    GROW_FILL_FRAC=0.525 GROW_LIFT=0.087 GROW_NOGLOW=1 GROW_SOLID=1

-- Blooby at the icon's share of the star and standing on its white, no band
of light round the star, its corners filled. Unset, every take draws as it
did when the owner first saw the seven.

THE HELLO AS IT SHIPS (the owner's pick after v327, mock C: "C looks good")
is its own take, `hello`: take C at that share and lift, with three changes.

  * The star's points are points (pointed_star). The one closed outline of
    a round pen ended every point in a ball, and its smoothing pinched a
    neck behind some: the owner's "nubs" on the star tips.
  * Its page draws itself, a time-lapse of the pen: the outline, then the
    colouring, then the hatching that fills the points, each group fitted
    to its share of STAR_MS with every stroke keeping its own rhythm (the
    pen draws at its own pace; the hello plays it fast, as "fit" would).
  * No ground: the payload carries no background colour, so the hello's
    own light (the Home Screen icon's glass, lib/hello.js) shows through.

    python3 harness/tools/make_grow.py OUTDIR hello
    cp OUTDIR/hello.json skribl/static/brand/blooby-hello.json
"""
import copy
import json
import math
import os
import pathlib
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent))
import artdraw  # noqa: E402
import blooby  # noqa: E402
import browsing  # noqa: E402
from artdraw import PURPLE, Stroke as S  # noqa: E402
from flipworks import PINK, _ellipse, _fill, _offset  # noqa: E402

BASE = os.environ.get("SKRIBL_BASE", "http://127.0.0.1:5001")
LILAC = blooby.ICON_TILE          # the icon's lilac
GLOW = "#ddd3ff"                  # the star's light on it
WHITE = "#ffffff"
SHADOW = "#d4cbf5"                # his shadow on the star: the icon's deep lilac at 22% on white
FPS = 12
TITLES = {"A1": "Blooby says hi (A1, even)", "A2": "Blooby says hi (A2, eased)",
          "A3": "Blooby says hi (A3, settle and twinkle)", "B": "Blooby says hi (B, pop)",
          "C": "Blooby says hi (C, walks up)", "D": "Blooby says hi (D, draws himself)",
          "E": "Blooby says hi (E, the whole logo)", "hello": "Blooby says hi"}
CYCLE = 12                        # pages per wave: one wave a second
STAR_INNER = blooby.ICON_STAR_INNER
# THE WHOLE STAR, as the app's Blooby badge has it (blooby.BADGE_*): in a tall
# phone frame the icon's star, its points running off the sides, read as a
# white band across the screen. All six points inside, a little margin.
STAR_FRAC = float(os.environ.get("GROW_STAR_FRAC", 0.5))   # its points' reach, as a share of the width
FILL_FRAC = float(os.environ.get("GROW_FILL_FRAC", 0.70))  # his full height, as a share of the width (the badge's)
# The hello (take `hello`): the icon's share of the star, lifted onto its white.
HELLO_FILL, HELLO_LIFT = 0.525, 0.087
# The star's page as a time-lapse: outline, colouring, hatching -- each
# group's milliseconds, and the beat between its strokes.
STAR_MS = ((820, 18), (460, 24), (300, 0))

# ------------------------------------------------------------------ Blooby

BODY = [blooby.FILL, blooby.OUTL, blooby.OUTR, blooby.FOOTL, blooby.FOOTR] + blooby.REST_L \
    + [blooby.SMILE, blooby.BLUSH]
_ref = [p for s in blooby.pose("wave", ground=False) for p in s.pts]
RX0, RX1 = min(x for x, _ in _ref), max(x for x, _ in _ref)
RY0, RY1 = min(y for _, y in _ref), max(y for _, y in _ref)
REF_C = ((RX0 + RX1) / 2, (RY0 + RY1) / 2)      # his middle in the waving pose
REF_FEET = (372.0, 492.0)                       # where he stands
REF_H = RY1 - RY0


def arm_at(ph):
    """His waving arm at phase `ph`: flipworks.wave's arm, at any phase."""
    s0, l1, l2 = (468, 300), 78, 70
    a1 = math.radians(36 + 8 * math.cos(ph))
    a2 = math.radians(12 + 42 * math.cos(ph - 1.0))
    e = (s0[0] + l1 * math.sin(a1), s0[1] - l1 * math.cos(a1))
    w = (e[0] + l2 * math.sin(a2), e[1] - l2 * math.cos(a2))
    h = (w[0] + 16 * math.sin(a2), w[1] - 16 * math.cos(a2))
    path = [s0, e, w]
    out = [S(path, "fill", PURPLE, size=30, pace=1.1, taper=(0.04, 0.06)),
           S(_offset(path, 15), "contour", size=8, weight=[(0, 0.6), (0.5, 1.0), (1, 0.8)]),
           S(_offset(path, -15), "form", size=6),
           S(_fill(h[0], h[1], 12, 12, turns=1.8, n=16), "fill", PURPLE, size=24, pace=2.0, taper=(0.03, 0.04)),
           S(_ellipse(h[0], h[1], 23, 24, a0=math.degrees(a2) + 90), "form", size=8)]
    # A flick of motion beside the hand at each end of the swing, as the card's wave has.
    d = (ph - 1.0) % (2 * math.pi)
    for centre, sgn in ((0.0, -1), (math.pi, 1)):
        if abs((d - centre + math.pi) % (2 * math.pi) - math.pi) < math.pi / CYCLE:
            out.append(S([(h[0] + sgn * 40, h[1] - 30), (h[0] + sgn * 50, h[1]), (h[0] + sgn * 40, h[1] + 28)],
                         "accent", size=5))
    return out


def eyes(blink):
    if blink:
        return [S([(334, 286), (344, 292), (354, 286)], "detail", size=6),
                S([(376, 286), (386, 292), (396, 286)], "detail", size=6)]
    return [S(_ellipse(344, 283, 7, 12, n=10), "detail", size=7), S(_ellipse(386, 283, 7, 12, n=10), "detail", size=7)]


def shadow():
    return [S(_fill(372, 497, 78, 11, turns=1.6, n=22), "fill", SHADOW, size=14, pace=1.6, peak=1.0, flat=True)]


def sparkles(t):
    """Four little twinkles round his head as he lands, `t` 0..1..0."""
    if t <= 0:
        return []
    out = []
    for (x, y), col in (((196, 126), PURPLE), ((548, 112), PINK), ((176, 300), PINK), ((574, 268), PURPLE)):
        r = 16 * t
        out += [S([(x, y - r), (x, y + r)], "accent", col, size=max(2.0, 5 * t), taper=(0.3, 0.3)),
                S([(x - r * 0.8, y), (x + r * 0.8, y)], "accent", col, size=max(2.0, 5 * t), taper=(0.3, 0.3))]
    return out


def place(strokes, k, at, anchor=REF_C, sx=1.0, sy=1.0, rot=0.0, minsize=1.1):
    """`strokes` (Blooby's own coordinates) scaled by k, stretched by sx/sy,
    turned by `rot` degrees about `anchor`, with `anchor` landing on `at`."""
    c, s = math.cos(math.radians(rot)), math.sin(math.radians(rot))
    out = []
    for st in strokes:
        n = copy.copy(st)
        pts = []
        for x, y in st.pts:
            dx, dy = (x - anchor[0]) * k * sx, (y - anchor[1]) * k * sy
            pts.append((at[0] + dx * c - dy * s, at[1] + dx * s + dy * c))
        n.pts = pts
        n.size = max(minsize, st.size * k * math.sqrt(sx * sy) * 1.05)
        out.append(n)
    return out


# ------------------------------------------------------------------ the star

def star_pts(cx, cy, r):
    pts = []
    for k in range(12):
        rr = r if k % 2 == 0 else r * STAR_INNER
        a = math.radians(-90 + 30 * k)
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    return pts + [pts[0]]


def clip(pts, x0, y0, x1, y1):
    """A polyline cut to the rectangle: the pieces inside it."""
    inside = lambda p: x0 <= p[0] <= x1 and y0 <= p[1] <= y1
    out, cur = [], []
    for a, b in zip(pts, pts[1:]):
        steps = max(1, int(math.hypot(b[0] - a[0], b[1] - a[1]) / 3))
        for i in range(steps + 1):
            p = (a[0] + (b[0] - a[0]) * i / steps, a[1] + (b[1] - a[1]) * i / steps)
            if inside(p):
                cur.append(p)
            elif cur:
                out.append(cur)
                cur = []
    if cur:
        out.append(cur)
    return [c for c in out if len(c) > 2]


def poly_rows(poly, step, reach, x0, x1):
    """A marker's back-and-forth colouring inside a polygon, one stroke for each
    part of it a row runs through on its own (a star's points are separate
    until they meet the middle). Each row stops where its round end comes
    within `reach` of the edge, measured square to the edge, so on a slanted
    edge the ends do not bulge past it (they made a scalloped, cloud-like rim)."""
    ys = [p[1] for p in poly]
    y, strokes, active = min(ys) + reach, [], []
    while y <= max(ys) - reach:
        xs = []
        for (ax, ay), (bx, by) in zip(poly, poly[1:]):
            if (ay <= y < by) or (by <= y < ay):
                slope = abs(by - ay) / (math.hypot(bx - ax, by - ay) or 1)     # sin of the edge's angle
                xs.append((ax + (y - ay) * (bx - ax) / (by - ay), reach / max(slope, 0.2)))
        xs.sort()
        ivs = [(max(a + ia, x0), min(b - ib, x1)) for (a, ia), (b, ib) in zip(xs[0::2], xs[1::2])]
        ivs = [(a, b) for a, b in ivs if b - a > 3]
        nxt = []
        for a, b in ivs:
            hits = [j for j, (_, (pa, pb), _) in enumerate(active) if pa < b and a < pb]
            mine = len(hits) == 1 and sum(1 for c, d in ivs if active[hits[0]][1][0] < d and c < active[hits[0]][1][1]) == 1
            if mine:
                pts, _, dr = active[hits[0]]
            else:
                pts, dr = [], 1
                strokes.append(pts)
            k = min(10, (b - a) / 3)
            row = [(a, y), (a + k, y), (b - k, y), (b, y)]
            pts.extend(row if dr > 0 else row[::-1])
            nxt.append((pts, (a, b), -dr))
        active = nxt
        y += step
    return [s for s in strokes if len(s) >= 4]


def star_strokes(cx, cy, r, cw, ch, scale=1.0):
    """The logo's star: a soft band of its light on the lilac, the white
    colouring, and a broad white edge on the star's own line. The colouring's
    round ends reach at most half that edge's width past the line, so the edge
    hides them and the star's sides read straight. `scale` thins every brush
    for a small star."""
    m = 2
    edge_w, fill_w = max(3.0, 14 * scale), max(4.0, 26 * scale)
    glow = [S(blooby.dense(p, 5), "form", GLOW, size=max(3, 12 * scale), peak=1.0, flat=True, pace=1.4)
            for p in clip(star_pts(cx, cy, r + 15 * scale), m, m, cw - m, ch - m)]
    if os.environ.get("GROW_NOGLOW"):
        glow = []                 # a crisp edge: no band of light round the star
    # dense(): points close together, so the pen's smoothing follows each row's
    # turn instead of bowing it out past the edge (blooby.card's colouring does the same).
    fill = [S(blooby.dense(p, 4), "fill", WHITE, size=fill_w, pace=2.6, peak=1.0, flat=True)
            for p in poly_rows(star_pts(cx, cy, r), max(3, 14 * scale), fill_w / 2 - edge_w / 2 + 1, m, cw - m)]
    # A stroke down the middle of each point, ending where its round end meets
    # both edges: the rows cross a slanted point at an angle and could leave a
    # gap on its centre line (two small holes in the side points, first draft).
    half = math.atan2(STAR_INNER * math.sin(math.radians(30)), 1 - STAR_INNER * math.cos(math.radians(30)))
    stop = r - (fill_w / 2) / math.sin(half)
    spines = []
    for k in range(6):
        a = math.radians(-90 + 60 * k)
        p = [(cx + r * f * math.cos(a), cy + r * f * math.sin(a)) for f in (0.2, stop / r)]
        spines += [S(blooby.dense(q, 4), "fill", WHITE, size=fill_w, pace=2.0, peak=1.0, flat=True)
                   for q in clip(p, m, m, cw - m, ch - m)]
    edge = [S(blooby.dense(p, 4), "form", WHITE, size=edge_w, peak=1.0, flat=True, pace=1.2)
            for p in clip(star_pts(cx, cy, r), m, m, cw - m, ch - m)]
    if os.environ.get("GROW_SOLID"):
        # Four more white lines just inside the edge: the rows' round ends cannot
        # reach into a point's narrow corners, and left lilac slivers there
        # (456 device pixels inside the star at 3x; none with these).
        for d in (0.7, 1.4, 2.1, 2.8):
            edge += [S(blooby.dense(p, 4), "form", WHITE, size=edge_w, peak=1.0, flat=True, pace=1.2)
                     for p in clip(star_pts(cx, cy, r - d * edge_w), m, m, cw - m, ch - m)]
    return glow + fill + spines + edge


# A point's half angle, at its tip.
HALF = math.atan2(STAR_INNER * math.sin(math.radians(30)), 1 - STAR_INNER * math.cos(math.radians(30)))


def _edge_dist(r):
    """How far each side's line is from the middle (the same for all twelve)."""
    (tx, ty), (ix, iy) = star_pts(0, 0, r)[0], star_pts(0, 0, r)[1]
    return abs(tx * iy - ty * ix) / math.hypot(ix - tx, iy - ty)


def _truncated(pts, wmin):
    """The star with each point cut square where it is `wmin` wide: no row of
    the colouring is shorter than that, so none turns a hairpin that the pen's
    smoothing swings out past the side (bumps along the narrow points)."""
    out, n = [], len(pts)
    for k in range(n):
        if k % 2:
            out.append(pts[k])
            continue
        tip = pts[k]
        for other in (pts[k - 1], pts[(k + 1) % n]):
            dx, dy = other[0] - tip[0], other[1] - tip[1]
            d = math.hypot(dx, dy)
            back = (wmin / 2) / math.sin(HALF)          # along the side, to where the point is wmin wide
            out.append((tip[0] + dx / d * back, tip[1] + dy / d * back))
    return out


def _hatch(inner, tip, centre, depth, size, outline_half):
    """A straight line `depth` inside one side and parallel to it, from the
    inner corner out to where it meets the point's middle: hatching that fills
    a point with no turn for the smoothing to swing past the side."""
    tx, ty = tip[0] - inner[0], tip[1] - inner[1]
    d = math.hypot(tx, ty)
    ux, uy = tx / d, ty / d
    nx, ny = -uy, ux
    if (centre[0] - inner[0]) * nx + (centre[1] - inner[1]) * ny < 0:
        nx, ny = -nx, -ny                           # the normal that points into the star
    end = d - depth / math.tan(HALF)                # along the side, where this line reaches the middle
    if end <= 4:
        return None
    # On past the middle, as far as its round end stays inside the other
    # side's outline, so the two sides' lines overlap instead of leaving a
    # sliver; and back past the inner corner, into the star's body.
    over = min(size * 0.6, max(0.0, (depth + outline_half - size / 2) / math.sin(2 * HALF)))
    return [(inner[0] + nx * depth - ux * size, inner[1] + ny * depth - uy * size),
            (inner[0] + nx * depth + ux * (end + over), inner[1] + ny * depth + uy * (end + over))]


def pointed_star(cx, cy, r, cw, ch, outline=5.0, row=26.0, wmin=20.0,
                 hatches=((2.5, 5.0), (6.0, 6.0), (10.5, 7.0), (15.5, 8.0), (21.0, 9.0), (27.0, 10.0))):
    """The hello's star, inked the way a hand inks one, as three groups in the
    order they are drawn: the outline, the colouring, the hatching.

    No stroke turns a corner. Each side is its own fine line from the inner
    corner out to the point, lifting off there, so every point ends in a
    point; the colouring runs on the star shrunk by its round ends' reach
    and cut square where a point gets narrow, so those ends stay under the
    outline; and straight lines parallel to each side fill the narrow
    points. (star_strokes' one closed loop of a round pen ended every point
    in a ball, and its smoothing pinched a neck behind some.)"""
    m = 2
    pts = star_pts(cx, cy, r)[:12]
    shrink = 1 - (row / 2 - outline / 2 + 0.5) / _edge_dist(r)
    inset = _truncated(star_pts(cx, cy, r * shrink)[:12], wmin)
    rows = [S(blooby.dense(p, 4), "fill", WHITE, size=row, pace=2.6, peak=1.0, flat=True)
            for p in poly_rows(inset + [inset[0]], 14, 0.5, m, cw - m)]
    sides = [(pts[(k + 1) % 12], pts[k]) if k % 2 == 0 else (pts[k], pts[(k + 1) % 12]) for k in range(12)]
    hatching = []
    for depth, size in hatches:
        for inner, tip in sides:
            p = _hatch(inner, tip, (cx, cy), depth, size, outline / 2)
            if p:
                hatching.append(S(blooby.dense(p, 2), "fill", WHITE, size=size, pace=0.9, peak=1.0, flat=True))
    lines = [S(blooby.dense([inner, tip], 2), "form", WHITE, size=outline, pace=0.8, peak=1.0, flat=True)
             for inner, tip in sides]
    return lines, rows, hatching


# ------------------------------------------------------------------ the takes

def ease_out(t):
    return 1 - (1 - t) ** 3


def ease_out_back(t, c=0.9):
    return 1 + (c + 1) * (t - 1) ** 3 + c * (t - 1) ** 2


def take(name, cw, ch):
    """The pages of a take: dicts saying what each page holds."""
    hello = name == "hello"
    k_full = (HELLO_FILL if hello else FILL_FRAC) * cw / REF_H              # his full height, as a share of the width
    lift = HELLO_LIFT if hello else float(os.environ.get("GROW_LIFT", 0))
    mid = (cw / 2, ch / 2 - lift * cw)                                       # where he stands, lifted onto the star
    pages, loop_n, star_page = [], 24, True
    feet_full = (mid[0] + (REF_FEET[0] - REF_C[0]) * k_full, mid[1] + (REF_FEET[1] - REF_C[1]) * k_full)

    def growth(scales, **kw):
        g = len(scales)
        for i, s in enumerate(scales):
            ph = 2 * math.pi * (i - g) / CYCLE
            spec = {"k": k_full * s, "at": mid, "ph": ph, "blink": False}
            spec.update({key: (v[i] if isinstance(v, list) else v) for key, v in kw.items()})
            pages.append(spec)

    if name == "A1":       # the plainest reading: he grows at an even rate, from the middle
        g = 24
        growth([0.12 + 0.88 * i / (g - 1) for i in range(g)])
    elif name == "A2":     # the same, eased: quick at first, gently arriving
        g = 24
        growth([0.12 + 0.88 * ease_out(i / (g - 1)) for i in range(g)])
    elif name == "A3":     # eased, a breath past full size and back, and a twinkle as he lands
        g = 26
        sc = [0.12 + 0.88 * ease_out_back(i / (g - 1)) for i in range(g)]
        tw = [max(0.0, 1 - abs(i - (g - 5)) / 4) for i in range(g)]
        growth(sc, sparkle=tw)
    elif name == "B":      # pop: up from a dot, past full size, squash and settle, twinkles
        sc = [0.05, 0.22, 0.48, 0.78, 1.04, 1.14, 1.12, 1.04, 0.96, 0.95, 0.99, 1.02, 1.01, 1.0]
        sx = [1.0, 0.9, 0.88, 0.9, 0.95, 1.0, 1.04, 1.06, 1.04, 1.0, 0.98, 0.99, 1.0, 1.0]
        sy = [1.0, 1.12, 1.14, 1.1, 1.04, 1.0, 0.96, 0.94, 0.97, 1.0, 1.02, 1.01, 1.0, 1.0]
        tw = [0, 0, 0, 0, 0.3, 0.7, 1.0, 1.0, 0.8, 0.6, 0.4, 0.2, 0, 0]
        growth(sc, sx=sx, sy=sy, sparkle=tw, anchor=REF_FEET, at=feet_full)
    elif name in ("C", "hello"):   # he walks up to you from far off on the star, waving, a waddle in each step
        g = 40
        sc, at, rot = [], [], []
        far_feet = (mid[0], mid[1] - 0.18 * ch)
        for i in range(g):
            t = i / (g - 1)
            s = 1 / (6 - 5 * t)                                  # nearing at an even pace: slow, then fast
            u = (s - 1 / 6) / (1 - 1 / 6)
            step = abs(math.sin(math.pi * 6 * t))                # six steps
            fx = far_feet[0] + (feet_full[0] - far_feet[0]) * u
            fy = far_feet[1] + (feet_full[1] - far_feet[1]) * u - 10 * s * step
            sc.append(s)
            at.append((fx, fy))
            rot.append(4 * math.sin(math.pi * 6 * t) * (1 - 0.6 * t))
        growth(sc, at=at, rot=rot, anchor=REF_FEET)
        pages[-1]["rot"] = 0.0
    elif name == "D":      # he draws himself, small, then grows into his place
        pages.append({"k": k_full * 0.3, "at": mid, "ph": 2 * math.pi * -20 / CYCLE, "blink": False, "draw": True})
        g = 20
        growth([0.3 + 0.7 * ease_out(i / g) for i in range(1, g + 1)])
    elif name == "E":      # the whole logo grows: the star with him
        star_page, loop_n = False, 12
        g = 22
        growth([0.18 + 0.82 * ease_out(i / (g - 1)) for i in range(g)], star=True)
    else:
        raise SystemExit(f"no take {name}")
    for p in pages:
        if p.get("star"):
            p["star_k"] = p["k"] / k_full
    return {"pages": pages, "loop_n": loop_n, "star_page": star_page, "k_full": k_full, "mid": mid}


# ------------------------------------------------------------------ drawing it

def page_strokes(p, part="all", cw=0, ch=0, star_r=0):
    anchor = p.get("anchor", REF_C)
    kw = dict(anchor=anchor, sx=p.get("sx", 1.0), sy=p.get("sy", 1.0), rot=p.get("rot", 0.0))
    out = []
    if p.get("star"):
        sk = p["star_k"]
        out += star_strokes(p["at"][0], p["at"][1], star_r * sk, cw, ch, scale=max(0.25, sk))
    if part in ("all", "body"):
        out += place(shadow() + BODY, p["k"], p["at"], **kw)
    if part in ("all", "arm"):
        out += place(arm_at(p["ph"]) + eyes(p.get("blink")) + sparkles(p.get("sparkle", 0)), p["k"], p["at"], **kw)
    return out


def build(name, out_dir, browser):
    ctx = browser.new_context(viewport={"width": 1100, "height": 1500})
    page = ctx.new_page()
    errs = []
    page.on("pageerror", lambda e: errs.append(str(e)))
    browsing.goto(page, BASE, "/flip")
    page.wait_for_timeout(900)
    page.evaluate("() => { window.SkriblHints && window.SkriblHints.hide(); }")
    page.evaluate("""() => { const t = window.SkriblCanvasSizes, id = t.SIZES.find(s => s.label === '9:16').id;
        const b = document.querySelector(`[data-size='${id}']`); if (b) b.click(); }""")
    page.wait_for_timeout(400)
    page.evaluate(f"""() => {{ setBg('{LILAC}'); onion = false; fps = {FPS};
        if (window.SkriblPressure) SkriblPressure.setEnabled(true);
        if (typeof setTool === 'function') setTool('pen'); }}""")
    cw, ch = page.evaluate("() => [CW, CH]")
    spec = take(name, cw, ch)
    star_r = STAR_FRAC * cw
    logical = [cw, ch]
    t0 = time.time()

    def draw(strokes, seed, tempo=1.6, gaps=6.0):
        artdraw.draw(page, strokes, seed=seed, canvas="#pad", logical=logical, tempo=tempo, pause_tempo=gaps)

    first, hello = True, name == "hello"
    if spec["star_page"]:
        if hello:
            groups = pointed_star(cw / 2, ch / 2, star_r, cw, ch)
            draw([s for g in groups for s in g], 1, tempo=1.0, gaps=6.0)
        else:
            draw(star_strokes(cw / 2, ch / 2, star_r, cw, ch), 1, tempo=2.2)
        first = False
    for i, p in enumerate(spec["pages"]):
        if not first:
            page.evaluate("() => addFrame(false)")
            page.wait_for_timeout(60)
        first = False
        draw(page_strokes(p, "all", cw, ch, star_r), 10 + i, tempo=(1.3 if p.get("draw") else 1.7),
             gaps=(2.5 if p.get("draw") else 6.0))
    growth_end = page.evaluate("() => frames.length")      # the loop starts on the next page
    # The loop: full size, his body once and the page copied, then each page's arm and eyes.
    n = spec["loop_n"]
    full = {"k": spec["k_full"], "at": spec["mid"], "ph": 0.0}
    if not spec["star_page"]:
        full.update(star=True, star_k=1.0)
    page.evaluate("() => addFrame(false)")
    page.wait_for_timeout(60)
    draw(page_strokes(full, "body", cw, ch, star_r) if not spec["star_page"] else page_strokes(full, "body"), 900,
         tempo=1.7)
    for _ in range(n - 1):
        page.evaluate("() => addFrame(true)")
    page.wait_for_timeout(200)
    blink_at = n * 2 // 3
    for j in range(n):
        page.evaluate("i => go(i)", growth_end + j)
        page.wait_for_timeout(40)
        p = dict(full, ph=2 * math.pi * j / CYCLE, blink=(j == blink_at))
        p.pop("star", None)
        draw(page_strokes(p, "arm"), 1000 + j, tempo=1.7)
    total = page.evaluate("() => frames.length")
    draws = [i for i, p in enumerate(spec["pages"]) if p.get("draw")]
    off = 1 if spec["star_page"] else 0
    draws = [d + off for d in draws] + ([0] if hello else [])
    under = {"page": 0, "from": 1, "to": total - 1} if spec["star_page"] else None
    loop = {"from": growth_end, "to": total - 1, "forever": True}
    if hello:
        # THE STAR'S PAGE AS A TIME-LAPSE, in the editor itself so the backup
        # and the post agree: each group fitted to its milliseconds, each
        # stroke keeping its own rhythm, a beat between strokes.
        bad = page.evaluate("""([counts, plan]) => {
            const pts = frames[0].strokes, runs = [];
            for (const p of pts) { if (p.start || !runs.length) runs.push([]); runs[runs.length - 1].push(p); }
            if (runs.length !== counts.reduce((a, b) => a + b, 0)) return runs.length + ' strokes for ' + counts;
            let t = pts[0].t, at = 0;
            counts.forEach((n, g) => {
              const group = runs.slice(at, at + n), span = plan[g][0], beat = plan[g][1];
              at += n;
              const raw = group.reduce((a, s) => a + Math.max(1, s[s.length - 1].t - s[0].t), 0);
              const k = (span - beat * (n - 1)) / raw;
              group.forEach(s => { const t0 = s[0].t;
                s.forEach(p => { p.t = Math.round(t + (p.t - t0) * k); });
                t = s[s.length - 1].t + beat; });
            });
            return null; }""", [[len(g) for g in groups], [list(x) for x in STAR_MS]])
        if bad:
            raise SystemExit(f"hello: the star page recorded {bad}")
    page.evaluate("""([draws, under, loop]) => { frames.forEach(f => { delete f.draw; });
        draws.forEach(i => { frames[i].draw = true; });
        docUnder = under; docLoop = loop; idx = 0; buildStrip(); render(); }""",
                  [draws, under, loop])
    page.evaluate("t => window.SkriblName && window.SkriblName.set(t)", TITLES.get(name, 'Blooby says hi'))
    page.wait_for_timeout(300)
    doc = page.evaluate("() => serializeFlip()")
    payload = page.evaluate("""async () => { const p = await buildSharePayload();
        for (const k of ['thumbnail', 'caption']) delete p[k]; return p; }""")
    ctx.close()
    if errs:
        raise SystemExit(f"{name}: page errors {errs[:2]}")
    if hello:
        for f in payload["frames"]:
            f["background"] = None          # the hello's own light shows through (lib/hello.js)
    out = pathlib.Path(out_dir)
    (out / f"{name}.skribl").write_text(json.dumps(doc))
    (out / f"{name}.json").write_text(json.dumps(payload))
    meta = {"take": name, "pages": total, "growth_end": growth_end, "loop": loop, "under": under, "fps": FPS,
            "canvas": [cw, ch], "points": sum(len(f.get("strokes", [])) for f in payload["frames"]),
            "minutes": round((time.time() - t0) / 60, 1),
            "saved_under": payload.get("under"), "saved_loop": payload.get("loop"), "saved_fps": payload.get("fps")}
    (out / f"{name}.meta.json").write_text(json.dumps(meta, indent=1))
    print(json.dumps(meta), flush=True)


if __name__ == "__main__":
    from playwright.sync_api import sync_playwright
    out_dir = sys.argv[1]
    pathlib.Path(out_dir).mkdir(parents=True, exist_ok=True)
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        for name in sys.argv[2:]:
            build(name, out_dir, b)
        b.close()
