#!/usr/bin/env python3
"""Blooby -- the purple guy the owner named, Skribl's mascot -- and his trading card.

    python3 harness/tools/blooby.py card OUTDIR
    python3 harness/tools/blooby.py icon skribl/static [MASTER.png]

Blooby is built from his own Flip drawing (flipworks.wave: the marker fill, the
two-sided outline, the feet, the ground), so every pose keeps the hand he was
first drawn with; the owner's brief for him was "keep the sloppiness", and a
tidied vector of him was turned down for losing it.

The card follows the owner's hand-drawn trading cards (Rod Carew, MASH, Stevie
Wonder, All Star): colour first, then a black-yellow-black frame, an arched
window, a title with stars, a rounded name plate -- every stroke of it drawn by
the real Pad, frame and lettering included, so the card is a Skribl too. Its
Ideas example (`make_art.py blooby-card`) is that drawing; `card OUTDIR` above
draws it once more and writes the picture of it lying on a table, aged a little,
with the short shadow a thin card casts (card.png raw, card-paper.png,
card-dark.png). Needs the local server.

Coordinates are Pad's 4:3 canvas (816 x 612), as in artworks.py.
"""
import base64
import copy
import math
import pathlib
import random
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE.parent))
import artdraw  # noqa: E402
import flipworks  # noqa: E402
from artdraw import INK, PURPLE, Stroke as S  # noqa: E402
from flipworks import PINK, _ellipse, _fill, _offset  # noqa: E402

# ---------------------------------------------------------------- Blooby, posed

W = flipworks.wave()
BODY = W["base"]                       # fill, outline L, outline R, feet, resting arm (5), ground, smile, blush
FILL, OUTL, OUTR, FOOTL, FOOTR = BODY[0:5]
REST_L = BODY[5:10]
GROUND, SMILE, BLUSH = BODY[10], BODY[11], BODY[12]
EYES = [S(_ellipse(344, 283, 7, 12, n=10), "detail", size=7), S(_ellipse(386, 283, 7, 12, n=10), "detail", size=7)]


def arm(path, hand, contour_side=15):
    """An arm as his are drawn: a broad purple stroke, ink down both sides, a round hand."""
    hx, hy = hand
    return [S(path, "fill", PURPLE, size=30, pace=1.1, taper=(0.04, 0.06)),
            S(_offset(path, contour_side), "contour", size=8, weight=[(0, 0.6), (0.5, 1.0), (1, 0.8)]),
            S(_offset(path, -contour_side), "form", size=6),
            S(_fill(hx, hy, 12, 12, turns=1.8, n=16), "fill", PURPLE, size=24, pace=2.0, taper=(0.03, 0.04)),
            S(_ellipse(hx, hy, 23, 24, a0=-60), "form", size=8)]


def wave_arm():
    """The raised arm from the Flip drawing's sixth page, the top of his wave."""
    return [s for s in W["pages"][5] if s.role in ("fill", "contour", "form")][:5]


def base(rest=True, ground=True):
    out = [FILL, OUTL, OUTR, FOOTL, FOOTR]
    if rest:
        out += REST_L
    if ground:
        out.append(GROUND)
    return out


def pose(name, trait="none", ground=True):
    """Blooby in one of the poses mocked for the brand: wave, pen, cheer, think,
    oops, sleep, or just his face. `trait` adds his mark: "swoosh" (the one
    chosen: a purple pen line under his feet for the ground), "trail" or "nib".
    `ground=False` leaves out the line he stands on, for the app icon's star."""
    st = []
    if name == "wave":
        st = base() + wave_arm() + [SMILE, BLUSH] + EYES
    elif name == "pen":
        st = base() + arm([(468, 320), (512, 356), (536, 404)], (544, 420), -15) + [SMILE, BLUSH] + EYES
        st += [S([(552, 436), (596, 372)], "contour", size=11),          # the pen
               S([(596, 372), (604, 356)], "detail", PURPLE, size=7),
               S([(612, 486), (590, 470), (572, 492), (550, 478), (532, 498)], "accent", PURPLE, size=6, taper=(0.05, 0.4))]
    elif name == "cheer":
        st = base(rest=False) + arm([(272, 300), (244, 240), (232, 184)], (228, 166), -15) \
            + arm([(468, 300), (498, 240), (510, 184)], (514, 166))
        st += [S([(334, 292), (344, 279), (354, 292)], "detail", size=7), S([(376, 292), (386, 279), (396, 292)], "detail", size=7),
               S([(326, 318), (342, 340), (362, 350), (382, 340), (396, 316)], "detail", size=7,
                 weight=[(0, 0.6), (0.5, 1.0), (1, 0.6)]), BLUSH,
               S([(186, 150), (200, 162)], "accent", PINK, size=6), S([(560, 140), (548, 156)], "accent", PINK, size=6),
               S([(200, 210), (184, 214)], "accent", PURPLE, size=6), S([(546, 210), (562, 206)], "accent", PURPLE, size=6)]
    elif name == "think":
        st = base() + arm([(468, 300), (506, 252), (482, 206)], (462, 198), -15)
        st += [S(_ellipse(352, 275, 7, 12, n=10), "detail", size=7), S(_ellipse(394, 275, 7, 12, n=10), "detail", size=7),
               S([(338, 336), (356, 332), (372, 336)], "detail", size=6), BLUSH,
               S([(540, 150), (546, 126), (572, 120), (580, 140), (562, 156), (562, 172)], "accent", PURPLE, size=7,
                 taper=(0.05, 0.2)),
               S([(562, 190), (563, 192)], "accent", PURPLE, size=9)]
    elif name == "oops":
        st = base(rest=False) + arm([(272, 316), (236, 300), (214, 266)], (206, 250), -15) \
            + arm([(468, 316), (504, 300), (526, 266)], (534, 250))
        st += [S(_ellipse(344, 283, 10, 12, n=12), "detail", size=7), S(_ellipse(386, 283, 10, 12, n=12), "detail", size=7),
               S(_ellipse(362, 334, 7, 9, n=10), "detail", size=6),
               S([(266, 380), (300, 330), (330, 360), (310, 392), (290, 360), (340, 318), (380, 352), (360, 396), (334, 372),
                  (390, 330), (430, 356), (414, 392), (392, 370), (444, 336), (476, 366)], "accent", PINK, size=7,
                 taper=(0.04, 0.2))]
    elif name == "sleep":
        st = base(rest=False) + arm([(272, 330), (262, 380), (284, 420)], (298, 430), 15) \
            + arm([(468, 330), (478, 380), (456, 420)], (442, 430), -15)
        st += [S([(334, 286), (344, 294), (354, 286)], "detail", size=6), S([(376, 286), (386, 294), (396, 286)], "detail", size=6),
               S([(352, 336), (362, 340), (372, 336)], "detail", size=6), BLUSH,
               S([(468, 186), (494, 186), (468, 212), (494, 212)], "accent", PURPLE, size=7, taper=(0.03, 0.05)),
               S([(510, 140), (528, 140), (510, 160), (528, 160)], "accent", PURPLE, size=6, taper=(0.03, 0.05))]
    elif name == "face":
        st = [FILL, OUTL, OUTR, SMILE, BLUSH] + EYES
    if trait == "swoosh":
        st = [s for s in st if s is not GROUND] + [
            S([(232 + 6 * k, 504 - 7 * math.sin(k / 46 * 2 * math.pi)) for k in range(47)], "accent", PURPLE, size=10,
              taper=(0.1, 0.35))]
    elif trait == "trail":
        st += [S([(306, 496), (270, 508), (246, 492), (226, 506), (200, 496), (182, 512), (160, 500)], "accent", PURPLE,
                 size=6, taper=(0.05, 0.6))]
    elif trait == "nib":
        st += [S([(360, 194), (372, 162), (384, 194)], "contour", size=8),
               S(_fill(372, 184, 5, 7, turns=1.4, n=10), "fill", PURPLE, size=8),
               S([(372, 168), (372, 182)], "detail", size=4)]
    if not ground:
        st = [s for s in st if s is not GROUND]
    return st


# ---------------------------------------------------------------- the card

CARD_W = "#f6f0e0"     # ivory, not white: the owner asked for "less new sheen"
EDGE, THICK, WORN, CREASE = "#9d968a", "#6f685d", "#bbb3a5", "#958c7e"   # warm greys, to sit on ivory
FLAP, CURL = "#e7dfcd", "#d5cab3"
LAV, WINDOW, YEL = "#b9a8ff", "#fbf1d8", "#f3d54e"
TABLE = "#e6dfd1"      # the ground the Ideas example is drawn on: a shade darker than the card, so it reads
X0, Y0, X1, Y1 = 214, 22, 602, 590            # the card, portrait
AX0, AX1, AY_TOP, AY1 = 268, 548, 128, 486    # the arched window
AR = (AX1 - AX0) / 2
ACX, ACY = (AX0 + AX1) / 2, AY_TOP + AR
PX0, PY0, PX1, PY1 = 292, 502, 524, 552       # the name plate


def dense(pts, step=6):
    """Points no more than `step` apart, so Pad's smoothing follows corners and
    hairpins instead of overshooting them (sparse, it bulged the colouring past
    the card and threw stray lines off its corners)."""
    out = [pts[0]]
    for (ax, ay), (bx, by) in zip(pts, pts[1:]):
        n = max(1, int(math.hypot(bx - ax, by - ay) / step))
        out += [(ax + (bx - ax) * k / n, ay + (by - ay) * k / n) for k in range(1, n + 1)]
    return out


def rows(x0, y0, x1, y1, step, inset=0, shape=None):
    """Back-and-forth colouring across a box (or a shape(y) -> (xa, xb)). The
    inset has to clear the brush's radius or the colour spills past the edge."""
    pts, y, k = [], y0 + inset, 0
    while y <= y1 - inset:
        a, b = shape(y) if shape else (x0 + inset, x1 - inset)
        if b > a:
            pts += [(a, y), (b, y)] if k % 2 == 0 else [(b, y), (a, y)]
        y += step
        k += 1
    return pts


def rrect(x0, y0, x1, y1, r, n=6):
    out = []
    for cx, cy, a0 in ((x1 - r, y0 + r, -90), (x1 - r, y1 - r, 0), (x0 + r, y1 - r, 90), (x0 + r, y0 + r, 180)):
        out += [(cx + r * math.cos(math.radians(a0 + 90 * t / n)), cy + r * math.sin(math.radians(a0 + 90 * t / n)))
                for t in range(n + 1)]
    return out + [out[0]]


def arch_x(y, grow=0):
    r = AR + grow
    if y >= ACY:
        return (AX0 - grow, AX1 + grow)
    dy = ACY - y
    if dy > r:
        return (1, 0)
    dx = math.sqrt(r * r - dy * dy)
    return (ACX - dx, ACX + dx)


def arch_path(grow=0):
    r = AR + grow
    pts = [(AX0 - grow, AY1 + grow)] + [(ACX - r * math.cos(math.radians(t)), ACY - r * math.sin(math.radians(t)))
                                        for t in range(0, 181, 9)]
    return pts + [(AX1 + grow, AY1 + grow), (AX0 - grow, AY1 + grow)]


def star(cx, cy, r):
    p = [(cx + (r if k % 2 == 0 else r * 0.45) * math.cos(math.radians(-90 + 36 * k)),
          cy + (r if k % 2 == 0 else r * 0.45) * math.sin(math.radians(-90 + 36 * k))) for k in range(10)]
    return p + [p[0]]


def sig_strokes(x, y, scale):
    """The 'skribl' signature as pen strokes: the brand mark's own path, read
    from its template so the card's title is the logo, slant included."""
    src = (ROOT / "skribl" / "templates" / "skribl" / "_skribl_brand_mark.html").read_text()
    d = re.search(r'<path class="st" d="([^"]+)"', src).group(1)
    nums = [float(v) for v in re.findall(r"-?\d+\.?\d*", d)]
    pts, i = [(nums[0], nums[1])], 2
    while i + 6 <= len(nums):
        c1, c2, p = (nums[i], nums[i + 1]), (nums[i + 2], nums[i + 3]), (nums[i + 4], nums[i + 5])
        p0 = pts[-1]
        for t in (0.25, 0.5, 0.75, 1.0):
            u = 1 - t
            pts.append((u ** 3 * p0[0] + 3 * u * u * t * c1[0] + 3 * u * t * t * c2[0] + t ** 3 * p[0],
                        u ** 3 * p0[1] + 3 * u * u * t * c1[1] + 3 * u * t * t * c2[1] + t ** 3 * p[1]))
        i += 6
    sk = lambda px, py: (x + (px - py * math.tan(math.radians(8))) * scale, y + py * scale)
    return [sk(*p) for p in pts], [sk(38.8, 11.5), sk(39.4, 11.8)]   # the line, and the i's dot


LETTERS = {   # capitals in a 1 x 1.4 box, as a hand letters them
    "B": [[(0, 0), (0, 1.4)],
          [(0, 0)] + [(0.3 + 0.36 * math.sin(math.radians(t)), 0.33 - 0.33 * math.cos(math.radians(t)))
                      for t in range(0, 181, 15)] + [(0, 0.66)],
          [(0, 0.66)] + [(0.34 + 0.44 * math.sin(math.radians(t)), 1.03 - 0.37 * math.cos(math.radians(t)))
                         for t in range(0, 181, 15)] + [(0, 1.4)]],
    "L": [[(0, 0), (0, 1.4), (0.8, 1.4)]],
    "O": "ellipse",
    "Y": [[(0, 0), (0.45, 0.7)], [(0.9, 0), (0.45, 0.7), (0.45, 1.4)]],
}


def lettering(word, x, y, h, size=6.2):
    w = h / 1.4
    out, cx = [], x
    for ch in word:
        if LETTERS[ch] == "ellipse":
            out.append(S(_ellipse(cx + w * 0.45, y + h / 2, w * 0.48, h / 2, a0=-100, turns=1.05, n=16), "detail",
                         size=size, peak=1.0, flat=True))
            cx += w * 1.18
        else:
            for line in LETTERS[ch]:
                out.append(S(dense([(cx + px * w, y + py * w) for px, py in line], 3), "detail", size=size, peak=1.0,
                             flat=True))
            cx += w * (1.15 if ch != "Y" else 1.2)
    return out


def blooby(scale, dx, dy):
    """Blooby waving, with his swoosh, scaled into place."""
    out = []
    for s in pose("wave", "swoosh"):
        c = copy.copy(s)
        c.pts = [(dx + px * scale, dy + py * scale) for px, py in s.pts]
        c.size = s.size * scale * 1.05
        out.append(c)
    return out


def card(with_blooby=True):
    """Blooby's trading card, in the order it is drawn: colour, the yellow bands,
    the card's worn edge and corners, the ink of the frames, the title and its
    stars, Blooby, his name. Without Blooby it is the card the waving Flip
    keeps underneath (card_flip): the window empty, for him to wave in."""
    st = []
    # Colour first, as the owner's cards are: the card, the panel, the window, the plate.
    st.append(S(rows(X0, Y0, X1, Y1, 12, inset=17), "fill", CARD_W, size=26, pace=2.6, peak=1.0, flat=True))
    st.append(S(rows(X0 + 34, Y0 + 34, X1 - 34, Y1 - 34, 10, inset=13), "fill", LAV, size=22, pace=2.6, peak=1.0, flat=True))
    st.append(S(rows(AX0, AY_TOP, AX1, AY1, 9, inset=9, shape=lambda y: arch_x(y, -9)), "fill", WINDOW, size=20, pace=2.6,
                peak=1.0, flat=True))
    pr = (PY1 - PY0) / 2
    reach = lambda y: math.sqrt(max(0, pr * pr - (y - PY0 - pr) ** 2))
    plate = lambda y: (PX0 + pr - reach(y) + 8, PX1 - pr + reach(y) - 8)
    st.append(S(rows(PX0, PY0, PX1, PY1, 8, inset=7, shape=plate), "fill", CARD_W, size=16, pace=2.4, peak=1.0, flat=True))
    # The yellow bands of the frame, the arch and the plate.
    st.append(S(rrect(X0 + 28, Y0 + 28, X1 - 28, Y1 - 28, 16), "form", YEL, size=11, peak=1.0, flat=True))
    st.append(S(arch_path(7), "form", YEL, size=11, peak=1.0, flat=True))
    st.append(S(rrect(PX0 - 7, PY0 - 7, PX1 + 7, PY1 + 7, 26), "form", YEL, size=10, peak=1.0, flat=True))
    ink = lambda p, sz=5: S(p, "detail", size=sz, peak=1.0, flat=True)
    # The card's own edge, as an old card wears: soft corners, each its own, the pencil edge fading where
    # the ink has rubbed off at the tips. Top right is folded (a crease across the tip), bottom left has
    # curled up off the table, top left has a small crease, bottom right is only worn. The two white
    # rings close the margin to the edge; drawn quickly, the pen cut a corner and left a wedge open.
    st.append(S(rrect(X0 + 6, Y0 + 6, X1 - 6, Y1 - 6, 4), "fill", CARD_W, size=13, pace=0.7, peak=1.0, flat=True))
    st.append(S(rrect(X0 + 15, Y0 + 15, X1 - 15, Y1 - 15, 6), "fill", CARD_W, size=12, pace=0.7, peak=1.0, flat=True))
    rad = {"tl": 9, "tr": 7, "br": 8, "bl": 11}
    corners = {"tl": (X0, Y0, 1, 1), "tr": (X1, Y0, -1, 1), "br": (X1, Y1, -1, -1), "bl": (X0, Y1, 1, -1)}
    at = lambda c, px, py: (corners[c][0] + corners[c][2] * px, corners[c][1] + corners[c][3] * py)

    def arc(c, wob=(0, 0.7, -0.5, 0.9, 0.2, -0.6, 0.4)):
        r = rad[c]
        return [at(c, r - (r + wob[i % len(wob)]) * math.cos(math.radians(t)), r - (r + wob[i % len(wob)]) * math.sin(math.radians(t)))
                for i, t in enumerate(range(0, 91, 15))]
    # The four sides, fading into the corners; then the worn tips, lighter and thinner.
    # arc(c)[0] sits on the card's left/right side, arc(c)[-1] on its top/bottom.
    for c0, c1, end in (("tl", "tr", -1), ("tr", "br", 0), ("br", "bl", -1), ("bl", "tl", 0)):
        st.append(S([arc(c0)[end], arc(c1)[end]], "detail", EDGE, size=2.4, peak=1.0, taper=(0.04, 0.04)))
    for c in rad:
        st.append(S(arc(c), "detail", WORN, size=1.7, peak=1.0, taper=(0.3, 0.3)))
    # The card's thickness, down the right and along the bottom.
    st.append(S([(X1 + 1, Y0 + 12), (X1 + 1, Y1 - 10), (X1 - 2, Y1 - 1), (X1 - 10, Y1 + 1), (X0 + 16, Y1 + 1)], "detail",
                THICK, size=3.6, peak=1.0, taper=(0.06, 0.08)))
    # Top right: folded once, so a crease runs across the tip, a little kinked, and the flap beyond it is shaded.
    flap = []
    for i, k in enumerate(range(6, 30, 4)):
        seg = [at("tr", k + 2, 3.5), at("tr", 3.5, k)]
        flap += seg if i % 2 == 0 else seg[::-1]
    st.append(S(flap, "fill", FLAP, size=4.5, pace=1.2, peak=1.0, flat=True))
    st.append(S([at("tr", 36, 0.5), at("tr", 19, 13), at("tr", 0.5, 32)], "detail", CREASE, size=1.7, pace=0.5, peak=1.0,
                taper=(0.1, 0.2)))
    # Bottom left: curled up. No line, only shading that darkens toward the lifted tip, and the tip's edge
    # a shade darker. (With a line as well it read as a second fold; the owner saw the two as identical.)
    for k, col in ((28, FLAP), (13, CURL)):
        bend, kk, i = [], 4.0, 0
        while kk < k:
            seg = [at("bl", kk + 3, 3.5), at("bl", 3.5, kk + 3)]
            bend += seg if i % 2 == 0 else seg[::-1]
            kk += 2.5
            i += 1
        st.append(S(bend, "fill", col, size=4.5, pace=1.0, peak=1.0, flat=True))
    st.append(S(arc("bl")[1:-1], "detail", CREASE, size=2.0, peak=1.0, taper=(0.3, 0.3)))
    # Top left: just a small crease nicking in from the side.
    st.append(S([at("tl", 0.5, 30), at("tl", 9, 25), at("tl", 15, 24)], "detail", CREASE, size=1.4, pace=0.5, peak=1.0,
                taper=(0.1, 0.4)))
    # The ink of the frame, the arch and the plate, each band black both sides.
    st.append(ink(rrect(X0 + 22, Y0 + 22, X1 - 22, Y1 - 22, 18), 4.5))
    st.append(ink(rrect(X0 + 34, Y0 + 34, X1 - 34, Y1 - 34, 14), 4.5))
    st.append(ink(arch_path(13), 4.5))
    st.append(ink(arch_path(1), 4.5))
    st.append(ink(rrect(PX0 - 13, PY0 - 13, PX1 + 13, PY1 + 13, 30), 4.5))
    st.append(ink(rrect(PX0 - 1, PY0 - 1, PX1 + 1, PY1 + 1, 22), 4))
    # The title: the signature in accent purple, outlined in ink so it reads on the lavender (as the All
    # Star title is outlined), over a yellow shadow. Its tall letters break the frame on purpose; its
    # foot clears the arch, where the two yellows had run together.
    main, dot = sig_strokes(325, 25.5, 2.7)
    st.append(S([(x + 4, y + 4) for x, y in main], "form", YEL, size=12, pace=0.9, peak=1.0, flat=True))
    st.append(S(main, "form", INK, size=11, pace=0.9, peak=1.0, flat=True))
    st.append(S(dot, "form", INK, size=11.5, peak=1.0, flat=True))
    st.append(S(main, "form", PURPLE, size=5.6, pace=0.9, peak=1.0, flat=True))
    st.append(S(dot, "form", PURPLE, size=6, peak=1.0, flat=True))
    for cx, cy in ((276, 92), (540, 92)):
        st.append(S(star(cx, cy, 15), "fill", YEL, size=7, peak=1.0, flat=True))
        st.append(ink(star(cx, cy, 17), 3.5))
    # Blooby, centred in the window by his measured extent (his raised arm pulled a guessed placement
    # left), then his name, centred on the plate by its ink.
    bl = blooby(0.66, 140, 112)
    xs = [x for b in bl for x, _ in b.pts]
    bl = blooby(0.66, 140 + ACX - (min(xs) + max(xs)) / 2, 112) if with_blooby else []
    st += bl
    word = lettering("BLOOBY", 0, 0, 30)
    xs = [x for w in word for x, _ in w.pts]
    word = lettering("BLOOBY", (PX0 + PX1) / 2 - (min(xs) + max(xs)) / 2, (PY0 + PY1) / 2 - 15, 30)
    # Slow enough that every line reaches its end: quick, the pen lifted early and the Y came up short.
    for w in word:
        w.pace *= 0.35
    st += word
    for x in st[:len(st) - len(bl) - len(word)]:
        x.pts = dense(x.pts)
    # A slower hand on all but the colouring, so small curves stay round rather than faceted.
    for x in st:
        if x.role != "fill":
            x.pace *= 0.4
    return st


def _in_window(strokes):
    """Strokes in Blooby's own coordinates, placed in the card's window exactly
    as card() places him: the same scale, centred by the same measured extent
    of his waving pose, so the Flip's Blooby stands where the still card's does."""
    xs = [x for b in blooby(0.66, 140, 112) for x, _ in b.pts]
    dx, dy, k = 140 + ACX - (min(xs) + max(xs)) / 2, 112, 0.66
    out = []
    for s in strokes:
        c = copy.copy(s)
        c.pts = [(dx + px * k, dy + py * k) for px, py in s.pts]
        c.size = s.size * k * 1.05
        out.append(c)
    return out


def card_flip():
    """The trading card as a Flip that waves (owner: "keep it looping forever
    so he just keeps waving ... and it doesn't start over", then "the blooby
    card was supposed to draw blooby on slide 1 too, then make him wave in a
    loop"). Page 1 is the card without Blooby, kept UNDER every page after it
    and drawing itself once. Page 2 draws Blooby himself, once, in the pose
    the wave comes round to before its first page ("intro", the last pose), so
    he steps straight into it. Pages 3-12 are his wave (flipworks.wave: the
    body once, the arm and eyes per page, one blink), placed in the window as
    the still card places him, with his purple swoosh for the ground, and
    looped Forever. He is not drawn on page 1 itself: the page kept under
    shows beneath every page of the wave, and his resting arm would stand
    beside the waving one throughout."""
    swoosh = [s for s in pose("wave", "swoosh") if s.role == "accent" and s.color == PURPLE and len(s.pts) > 40]
    body = [s for s in W["base"] if s is not GROUND] + swoosh
    return {"fps": W["fps"], "card": card(with_blooby=False), "body": _in_window(body),
            "pages": [_in_window(pg) for pg in W["pages"]], "order": W["order"], "intro": len(W["pages"]) - 1}


# The tempo the card is drawn at -- (hand, pauses), as make_art's TEMPO -- and how much faster its
# example replays than it was drawn. Drawn any quicker the pen's events thin out and the small curves
# go faceted; so it is drawn at this pace and its recorded clock is shortened instead.
CARD_TEMPO = (4.0, 6.0)
CARD_REPLAY_SPEEDUP = 2.6


# ---------------------------------------------------------------- the picture of it

def _photograph(card_png, out):
    """The drawing as a card lying on a table: a pinhole the pen left in the colouring closed, a faint
    paper grain and yellowing toward the edges, a slight tilt, and the short shadow a thin card casts,
    a breath more under each corner as if they lift, most under the curled one."""
    from PIL import Image, ImageChops, ImageDraw, ImageFilter
    im = Image.open(card_png).convert("RGBA")
    a = im.getchannel("A")
    closed = a.filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.MinFilter(5))
    patch = im.filter(ImageFilter.MedianFilter(7))
    patch.putalpha(closed)
    patch.alpha_composite(im)
    im = patch
    w, h = im.size
    a = im.getchannel("A")
    rnd = random.Random(7)
    grain = Image.new("L", (w // 2, h // 2))
    grain.putdata([int(255 - abs(rnd.gauss(0, 4))) for _ in range((w // 2) * (h // 2))])
    grain = grain.resize((w, h), Image.BILINEAR).filter(ImageFilter.GaussianBlur(0.6))
    rgb = ImageChops.multiply(im.convert("RGB"), Image.merge("RGB", (grain, grain, grain)))
    inner = a.point(lambda v: 255 if v > 128 else 0).filter(ImageFilter.GaussianBlur(26))
    edge = inner.point(lambda v: int(max(0, 255 - v * 1.6) * 0.21))
    rgb = Image.composite(ImageChops.multiply(rgb, Image.new("RGB", (w, h), (226, 204, 160))), rgb, edge)
    rgb = Image.blend(rgb, Image.new("RGB", (w, h), (238, 228, 205)), 0.03)
    aged = rgb.convert("RGBA")
    aged.putalpha(a)
    card = aged.rotate(2.2, resample=Image.BICUBIC, expand=True)
    for bg, shade, op, name in (("#f3efe6", "#4a4236", 0.62, "card-paper.png"), ("#0d0f14", "#000000", 1.0, "card-dark.png")):
        W_, H_ = card.width + 160, card.height + 160
        pic = Image.new("RGBA", (W_, H_), bg)
        ca = card.getchannel("A")
        for (dx, dy), o, b in (((-8, 6), op * 0.75, 6), ((-2, 2), op * 0.6, 2)):
            sh = Image.new("RGBA", card.size, shade)
            sh.putalpha(ca.point(lambda v, o=o: int(v * o)))
            layer = Image.new("RGBA", (W_, H_), (0, 0, 0, 0))
            layer.alpha_composite(sh, (80 + dx, 80 + dy))
            pic.alpha_composite(layer.filter(ImageFilter.GaussianBlur(b)))
        px = ca.load()
        pts = [(x, y) for y in range(0, card.height, 3) for x in range(0, card.width, 3) if px[x, y] > 128]
        tips = {"tl": min(pts, key=lambda p: p[0] + p[1]), "tr": max(pts, key=lambda p: p[0] - p[1]),
                "br": max(pts, key=lambda p: p[0] + p[1]), "bl": max(pts, key=lambda p: p[1] - p[0])}
        col = Image.new("RGB", (1, 1), shade).getpixel((0, 0))
        lift = Image.new("RGBA", (W_, H_), (0, 0, 0, 0))
        d = ImageDraw.Draw(lift)
        for k, (r, o) in {"tl": (9, 0.22), "tr": (11, 0.28), "br": (9, 0.22), "bl": (15, 0.38)}.items():
            x, y = tips[k]
            x, y = x + 74, y + 85
            d.ellipse((x - r, y - r, x + r, y + r), fill=col + (int(255 * op * o),))
        pic.alpha_composite(lift.filter(ImageFilter.GaussianBlur(7)))
        pic.alpha_composite(card, (80, 80))
        pic.convert("RGB").save(out / name)


def draw_card(out, base="http://127.0.0.1:5001"):
    """Draw the card in the real Pad (transparent ground) and write card.png and its pictures."""
    import browsing
    from PIL import Image
    from playwright.sync_api import sync_playwright
    out = pathlib.Path(out)
    out.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1100, "height": 900}, device_scale_factor=2)
        browsing.goto(pg, base, "/skribl-pad")
        pg.wait_for_timeout(800)
        pg.evaluate("() => { window.SkriblHints && window.SkriblHints.hide(); }")
        pg.evaluate("""() => { const t = window.SkriblCanvasSizes, id = t.SIZES.find(s => s.label === '4:3').id;
            document.querySelector(`#canvasSeg button[data-size='${id}']`).click(); }""")
        pg.wait_for_timeout(300)
        pg.evaluate("() => { setTool('pen'); if (window.SkriblPressure) SkriblPressure.setEnabled(true); }")
        artdraw.draw(pg, card(), tempo=CARD_TEMPO[0], pause_tempo=CARD_TEMPO[1])
        pg.wait_for_timeout(600)
        url = pg.evaluate("() => document.getElementById('canvas').toDataURL('image/png')")
        b.close()
    raw = out / "card-raw.png"
    raw.write_bytes(base64.b64decode(url.split(",")[1]))
    im = Image.open(raw).convert("RGBA")
    bb = im.getchannel("A").point(lambda v: 255 if v > 8 else 0).getbbox()
    im.crop((bb[0] - 10, bb[1] - 10, bb[2] + 10, bb[3] + 10)).save(out / "card.png")
    raw.unlink()
    _photograph(out / "card.png", out)


# ------------------------------------------------------------- the app icon

# THE HOME SCREEN ICON (v320): Blooby waving, drawn straight onto a lilac tile
# with no sticker edge -- option J of the owner's mocks, picked over the paper
# and the full-purple tiles. His body IS the brand purple, so a tile in that
# purple swallows him; lilac is the strongest purple that keeps his outline and
# his body clear at 60 points. verify_identity reads this value from here.
ICON_TILE = "#cdbfff"
# THE EDGE (owner, N4 of the second icon round). The lilac deepens toward the
# tile's edge, so the icon has some depth beside iOS 26's glass icons without
# drawing a fake glass sheen into a picture iOS cannot relight. It starts near
# the middle and builds gradually (ICON_EDGE_FROM, ICON_EDGE_CURVE), so there is
# no band where it begins; the corners are ICON_EDGE exactly.
ICON_EDGE = "#a994f8"
ICON_EDGE_FROM = 0.12
ICON_EDGE_CURVE = 2.2
# THE STAR (owner, the third icon round): Blooby stands on the six-point star of
# the owner's own star icon, in white, on the same lilac -- "soft white", picked
# over the star on the brand gradient as the more loveable of the two. The star
# is that icon's, measured: point up, inner corners at 0.407 of the outer. Its
# points reach 0.72 of the side from the centre, past an edge at 0.5, so he
# stands on white with a lilac wedge between each pair of points, and all four
# corners stay lilac. verify_identity looks for the star's top point above his
# head and for the lilac in the wedge beside him.
ICON_STAR_R = 0.72
ICON_STAR_INNER = 0.407
ICON_FILL = 0.757          # his height, as a share of the tile's: today's size, less the ground line
ICON_SIZES = {"icon-512.png": 512, "icon-192.png": 192, "apple-touch-icon.png": 180}
# AS SHARP AS THE FILES ALLOW (owner: "as hi res ... as possible"). The icon is
# composed at ICON_MASTER from strokes the Pad drew at device scale ICON_DPR --
# about his full height at that size, so nothing in it is enlarged -- and each
# file is a reduction of that one picture.
ICON_MASTER = 4096
ICON_DPR = 8
# AND THE DEPTH THAT MAKES IT LOOK MADE ("and premium"). The star's light spills
# a little onto the lilac, and Blooby casts a soft shadow onto the star, a touch
# below him, so he stands on it instead of being pasted over it. Both are light
# in the picture itself, not a glass sheen iOS would have to relight.
ICON_GLOW = ((0.030, 0.275), (0.010, 0.30))           # (blur, as a share of the side; strength)
ICON_SHADOW = (0.012, 0.014, 0.22, (92, 66, 196))      # blur, drop, strength, a deep lilac


def _hex(c):
    return tuple(int(c[i:i + 2], 16) for i in (1, 3, 5))


def icon_ground(side):
    """The icon's tile: ICON_TILE in the middle, deepening to ICON_EDGE at the
    edge. The distance is half rounded-square, half circle, so the darkening
    follows the tile's shape without drawing its outline."""
    from PIL import Image
    mid, edge = _hex(ICON_TILE), _hex(ICON_EDGE)
    img = Image.new("RGB", (side, side))
    px = img.load()
    h = side / 2
    for y in range(side):
        for x in range(side):
            dx, dy = abs(x - h + 0.5) / h, abs(y - h + 0.5) / h
            r = 0.5 * (dx ** 4 + dy ** 4) ** 0.25 + 0.5 * (dx * dx + dy * dy) ** 0.5 / 2 ** 0.25
            u = min(1.0, max(0.0, (r - ICON_EDGE_FROM) / (1.08 - ICON_EDGE_FROM))) ** ICON_EDGE_CURVE
            px[x, y] = tuple(round(mid[i] + (edge[i] - mid[i]) * u) for i in range(3))
    return img


def icon_star(side):
    """The star he stands on, as a mask: point up, centred, ICON_STAR_R and
    ICON_STAR_INNER."""
    from PIL import Image, ImageDraw
    c, pts = side / 2, []
    for k in range(12):
        r = ICON_STAR_R * (1 if k % 2 == 0 else ICON_STAR_INNER) * side
        a = math.radians(-90 + 30 * k)
        pts.append((c + r * math.cos(a), c + r * math.sin(a)))
    m = Image.new("L", (side, side), 0)
    ImageDraw.Draw(m).polygon(pts, fill=255)
    return m


def _enclosed(alpha):
    """His ink and everything it closes in -- body, arms, hands -- as a mask.
    Flooded from outside at a quarter of the size, because Pillow's flood fill
    walks pixel by pixel in Python; his outline is thick enough to stay closed."""
    from PIL import Image, ImageDraw
    q = alpha.resize((max(1, alpha.width // 4), max(1, alpha.height // 4)), Image.BILINEAR)
    pad = Image.new("L", (q.width + 2, q.height + 2), 0)
    pad.paste(q.point(lambda v: 255 if v > 40 else 0), (1, 1))
    ImageDraw.floodfill(pad, (0, 0), 128)
    inside = pad.crop((1, 1, pad.width - 1, pad.height - 1)).point(lambda v: 0 if v == 128 else 255)
    return inside.resize(alpha.size, Image.BILINEAR).point(lambda v: 255 if v > 127 else 0)


def icon_compose(him, side=ICON_MASTER):
    """The icon at `side`, from his drawing `him` (RGBA, cropped to his ink):
    the lilac, the star's light on it, the star, his shadow on the star, and him.

    HIS UNPAINTED SPOTS STAY (owner: "We want the sloppy underneath like real
    original with the unpainted spots"). His marker fill does not quite reach
    his outline -- the hand that drew him -- and the star shows through those
    spots white, as the paper does in his original drawing. A draft filled them
    with his purple and was turned down. So his shadow is cut away inside his
    outline: it falls on the star around him, never into those spots."""
    from PIL import Image, ImageChops, ImageFilter
    tile = icon_ground(1024).resize((side, side), Image.BICUBIC).convert("RGBA")   # a smooth ramp: worked small, enlarged
    star = icon_star(side)
    white = Image.new("L", (side, side), 255)
    for blur, strength in ICON_GLOW:
        glow = star.filter(ImageFilter.GaussianBlur(side * blur)).point(lambda v, s=strength: round(v * s))
        tile.alpha_composite(Image.merge("RGBA", (white, white, white, glow)))
    tile.paste(Image.new("RGBA", (side, side), (255, 255, 255, 255)), (0, 0), star)
    h = round(side * ICON_FILL)
    w = round(him.width * h / him.height)
    him = him.resize((w, h), Image.LANCZOS)
    at = ((side - w) // 2, (side - h) // 2)
    body = Image.new("L", (side, side), 0)
    body.paste(_enclosed(him.getchannel("A")), at)
    blur, drop, strength, col = ICON_SHADOW
    shade = Image.new("L", (side, side), 0)
    shade.paste(body.filter(ImageFilter.GaussianBlur(side * blur)), (0, round(side * drop)))
    shade = ImageChops.multiply(shade.point(lambda v: round(v * strength)), ImageChops.invert(body))
    tile.alpha_composite(Image.merge("RGBA", tuple(Image.new("L", (side, side), v) for v in col) + (shade,)))
    tile.alpha_composite(him, at)
    return tile.convert("RGB")


def draw_icons(out, base="http://127.0.0.1:5001", master=None):
    """Draw Blooby waving in the real Pad (transparent ground), compose the icon
    and write the three files the manifest and the touch-icon tag name, each
    reduced from that one picture; `master`, if given, is where the full-size
    picture goes. Needs the local server.

    Drawn at a calm tempo: a fast hand captures too few points along each
    curve, and his eyes came out as hexagons the first time."""
    import browsing
    from PIL import Image
    from playwright.sync_api import sync_playwright
    out = pathlib.Path(out)
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1100, "height": 900}, device_scale_factor=ICON_DPR)
        browsing.goto(pg, base, "/skribl-pad")
        pg.wait_for_timeout(800)
        pg.evaluate("() => { window.SkriblHints && window.SkriblHints.hide(); }")
        pg.evaluate("""() => { const t = window.SkriblCanvasSizes, id = t.SIZES.find(s => s.label === '4:3').id;
            document.querySelector(`#canvasSeg button[data-size='${id}']`).click(); }""")
        pg.wait_for_timeout(300)
        pg.evaluate("() => { setTool('pen'); if (window.SkriblPressure) SkriblPressure.setEnabled(true); }")
        artdraw.draw(pg, pose("wave", ground=False), tempo=1.2, pause_tempo=6.0)
        pg.wait_for_timeout(500)
        url = pg.evaluate("() => document.getElementById('canvas').toDataURL('image/png')")
        b.close()
    him = Image.open(__import__("io").BytesIO(base64.b64decode(url.split(",")[1]))).convert("RGBA")
    him = him.crop(him.getchannel("A").point(lambda v: 255 if v > 8 else 0).getbbox())
    tile = icon_compose(him)
    if master:
        tile.save(master, optimize=True)
    for name, px in ICON_SIZES.items():
        tile.resize((px, px), Image.LANCZOS).save(out / name, optimize=True)
    return [out / n for n in ICON_SIZES]


if __name__ == "__main__":
    if len(sys.argv) not in (3, 4) or sys.argv[1] not in ("card", "icon") \
            or (len(sys.argv) == 4 and sys.argv[1] != "icon"):
        raise SystemExit(__doc__.split("\n\n")[1])
    if sys.argv[1] == "icon":
        print("wrote", ", ".join(str(x) for x in draw_icons(sys.argv[2], master=(sys.argv[3:] or [None])[0])))
        raise SystemExit(0)
    draw_card(sys.argv[2])
    print("wrote", ", ".join(f"{sys.argv[2]}/{n}" for n in ("card.png", "card-paper.png", "card-dark.png")))
