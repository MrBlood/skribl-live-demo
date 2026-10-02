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


def cat():
    """A cat, head and shoulders, head tipped, glancing to one side.
    One idea: the face. Purple is the colour (eyes, collar, inside the ears);
    pink is the accent (nose, tag)."""
    return _tilt([
        # -- gesture: the silhouette ------------------------------------------
        # ears and the top of the head in one sweep. The left ear stands, the
        # right one tips out. Heavy at the ear roots, thin at the tips, light
        # across the top of the head where it turns into the light.
        S([(316, 250), (300, 180), (306, 112), (344, 158), (376, 190), (410, 184),
           (446, 190), (488, 162), (538, 132), (520, 196), (504, 252)], "gesture",
          weight=[(0, 0.85), (0.16, 0.45), (0.3, 1.0), (0.5, 0.7), (0.68, 1.0), (0.82, 0.4), (1, 0.95)]),
        # cheeks and jaw: fullest at the bottom, the shadow side; a tuft of
        # fur breaks the outline at each cheek
        S([(314, 244), (300, 282), (290, 312), (282, 330), (296, 336), (306, 370), (340, 402), (384, 420),
           (432, 418), (478, 400), (510, 368), (520, 338), (532, 330), (520, 304), (506, 248)], "gesture",
          weight=[(0, 0.6), (0.45, 1.0), (0.7, 1.0), (1, 0.55)]),
        # the body, sitting: two falling lines that taper away
        S([(336, 404), (300, 456), (282, 520), (280, 596)], "contour", size=10,
          taper=(0.08, 0.55), weight=[(0, 1.0), (1, 0.5)]),
        S([(482, 400), (526, 452), (548, 520), (554, 596)], "contour", size=10,
          taper=(0.08, 0.55), weight=[(0, 1.0), (1, 0.5)]),
        # -- form --------------------------------------------------------------
        S([(324, 228), (318, 168), (356, 204)], "form", size=6),
        S([(498, 230), (520, 166), (480, 200)], "form", size=6),
        S([(332, 214), (326, 186), (342, 204), (332, 196)], "fill", PURPLE, size=11, peak=0.55),
        S([(494, 214), (508, 184), (488, 204), (500, 196)], "fill", PURPLE, size=11, peak=0.55),
        # the collar: a purple band under the jaw
        S([(344, 408), (376, 426), (414, 430), (452, 424), (478, 408)], "form", PURPLE, size=10, peak=0.9,
          weight=[(0, 0.6), (0.5, 1.0), (1, 0.6)]),
        # -- detail: eyes, glancing to the cat's left -------------------------
        # each eye: the iris first, solid, then the lids drawn over it as one
        # almond that closes at both corners, then the pupil
        S([(370, 290), (384, 288), (390, 300), (380, 310), (368, 304), (372, 295), (382, 298), (378, 304)], "fill", PURPLE, size=13),
        S([(456, 290), (470, 288), (476, 300), (466, 310), (454, 304), (458, 295), (468, 298), (464, 304)], "fill", PURPLE, size=13),
        S([(340, 300), (356, 284), (380, 280), (400, 294), (384, 312), (360, 314), (342, 302)], "detail", size=6.5,
          weight=[(0, 0.7), (0.3, 1.0), (0.55, 0.9), (0.75, 0.45), (1, 0.55)]),
        S([(424, 296), (442, 280), (468, 282), (486, 298), (466, 312), (442, 312), (426, 298)], "detail", size=6.5,
          weight=[(0, 0.7), (0.3, 1.0), (0.55, 0.9), (0.75, 0.45), (1, 0.55)]),
        S([(382, 289), (381, 305)], "detail", size=5.5, pace=0.55),
        S([(468, 289), (467, 305)], "detail", size=5.5, pace=0.55),
        # nose (the accent), filled in two strokes, then the mouth
        S([(397, 342), (419, 342), (408, 356), (398, 344)], "detail", PINK, size=7, pace=0.65),
        S([(402, 345), (414, 345), (408, 351), (404, 346)], "fill", PINK, size=10),
        S([(408, 356), (407, 366), (396, 378), (383, 374)], "detail", weight=[(0, 1.0), (1, 0.6)]),
        S([(407, 366), (419, 378), (432, 373)], "detail", weight=[(0, 1.0), (1, 0.6)]),
        # chest fur under the collar: three small flicks
        S([(392, 448), (398, 474)], "accent", size=5.5),
        S([(410, 456), (412, 484)], "accent", size=5.5),
        S([(428, 448), (430, 470)], "accent", size=5.5),
        # -- accents: whiskers flicked fast, and the tag on the collar --------
        S([(370, 362), (320, 352), (258, 350)], "accent", taper=(0.05, 0.6)),
        S([(368, 372), (316, 374), (262, 386)], "accent", taper=(0.05, 0.6)),
        S([(446, 362), (498, 350), (560, 346)], "accent", taper=(0.05, 0.6)),
        S([(446, 372), (500, 372), (556, 384)], "accent", taper=(0.05, 0.6)),
        S([(414, 432), (406, 446), (414, 458), (424, 448), (416, 434)], "detail", PINK, size=8),
    ], -6)


def scene():
    """A cottage on a hill, framed by a tree close by, mountains far off.
    Depth by overlap (far lines stop where near things cover them), by size,
    and by line: far is thin and purple, near is heavy and dark. Laid in as a
    landscape painter would: the hill, the near frame, the middle, the far,
    then the path towards us, and accents last."""
    import math
    out = [
        # -- gesture: the hill line, the ground of the whole picture ----------
        S([(186, 428), (290, 408), (380, 402), (426, 401)], "gesture", size=9, weight=[(0, 1.0), (1, 0.75)],
          taper=(0.08, 0.1)),
        S([(580, 391), (660, 382), (740, 386), (812, 398)], "gesture", size=9, weight=[(0, 0.75), (1, 0.45)],
          taper=(0.1, 0.25)),
        # -- near: the tree that frames the corner, heavy ----------------------
        S([(64, 610), (88, 500), (102, 380), (118, 280), (142, 196)], "contour", size=13,
          weight=[(0, 1.0), (0.7, 0.8), (1, 0.45)], taper=(0.04, 0.3)),
        S([(132, 610), (140, 500), (150, 390), (160, 300), (178, 214)], "contour", size=11,
          weight=[(0, 1.0), (1, 0.4)], taper=(0.04, 0.3)),
        S([(150, 236), (206, 182), (280, 140), (370, 112)], "contour", size=9,
          weight=[(0, 1.0), (1, 0.3)], taper=(0.05, 0.45)),
        S([(118, 300), (74, 262), (30, 248)], "contour", size=8, weight=[(0, 1.0), (1, 0.3)], taper=(0.05, 0.45)),
    ]
    # leaves along the branch: purple, each a quick loop, pointing along it
    for (x, y, ang) in [(214, 164, -40), (252, 132, -70), (286, 152, 20), (326, 104, -60), (356, 128, 15),
                        (186, 196, -110), (64, 236, -120), (40, 262, 160)]:
        a = math.radians(ang); L = 28
        tip = (x + L * math.cos(a), y + L * math.sin(a))
        sideA = (x + 0.5 * L * math.cos(a) - 5 * math.sin(a), y + 0.5 * L * math.sin(a) + 5 * math.cos(a))
        sideB = (x + 0.5 * L * math.cos(a) + 5 * math.sin(a), y + 0.5 * L * math.sin(a) - 5 * math.cos(a))
        mid = (x + 0.45 * L * math.cos(a), y + 0.45 * L * math.sin(a))
        out.append(S([(x, y), sideA, tip, sideB, (x + 1, y + 1), mid, (x + 0.75 * L * math.cos(a), y + 0.75 * L * math.sin(a))],
                     "fill", PURPLE, size=11, peak=0.9, taper=(0.15, 0.2)))
    out += [
        # -- middle: the cottage, a block in perspective -----------------------
        S([(416, 336), (466, 284), (518, 336)], "contour", size=8, weight=[(0, 0.8), (0.5, 1.0), (1, 0.8)]),
        S([(466, 284), (536, 268), (590, 320)], "contour", size=7.5),
        S([(518, 336), (590, 320)], "form", size=6.5),
        S([(428, 334), (428, 402), (508, 402), (508, 334)], "form", size=6.5),
        S([(508, 402), (578, 392), (578, 322)], "form", size=6),
        S([(456, 402), (456, 364), (480, 364), (480, 402)], "detail", size=5),
        S([(530, 344), (556, 340), (556, 364), (530, 368), (530, 345)], "detail", size=4.5),
        S([(536, 350), (550, 348), (550, 360), (537, 362)], "fill", PURPLE, size=7),
        S([(546, 282), (546, 260), (562, 258), (562, 292)], "detail", size=5.5),
        # -- far: mountains, thin and purple, broken where nearer things stand
        S([(196, 330), (250, 262), (296, 300), (360, 228), (414, 300), (428, 318)], "form", PURPLE, size=5,
          peak=0.7, weight=[(0, 0.4), (0.4, 1.0), (1, 0.5)]),
        S([(596, 304), (640, 248), (690, 286), (748, 214), (812, 284)], "form", PURPLE, size=5, peak=0.7,
          weight=[(0, 0.5), (0.6, 1.0), (1, 0.4)]),
        # the sun, peeking over the ridge in the gap between the peaks
        S([(663, 268), (666, 248), (680, 236), (698, 235), (711, 247), (713, 262)], "form", PINK, size=7, peak=0.85,
          taper=(0.1, 0.2)),
        # shade: the side wall and under the eave, hatched once
        S([(516, 396), (532, 378)], "accent", PURPLE, size=4), S([(536, 394), (556, 374)], "accent", PURPLE, size=4),
        S([(556, 392), (574, 372)], "accent", PURPLE, size=4), S([(560, 336), (574, 324)], "accent", PURPLE, size=4),
    ]
    # -- near again: the path, an S that widens as it comes to us -----------
    cen = [(468, 404), (452, 446), (482, 494), (500, 540), (452, 612)]
    wid = [8, 30, 60, 86, 130]
    left = [(x - w / 2, y) for (x, y), w in zip(cen, wid)]
    right = [(x + w / 2, y) for (x, y), w in zip(cen, wid)]
    out += [S(left, "contour", size=8.5, weight=[(0, 0.25), (1, 1.0)], taper=(0.04, 0.1)),
            S(right, "contour", size=8.5, weight=[(0, 0.25), (1, 1.0)], taper=(0.04, 0.1))]
    # grass, leaning: three tufts, each blade a curve from its root
    for bx, sc in ((640, 1.0), (730, 0.85)):
        for dx, h, lean in [(-14, 70, -40), (-4, 96, -14), (6, 104, 8), (16, 74, 34)]:
            root = (bx + dx * sc, 610)
            out.append(S([root, (root[0] + lean * 0.25 * sc, 610 - h * 0.45 * sc),
                          (root[0] + lean * sc, 610 - h * sc)], "contour",
                         size=9, pace=1.5, taper=(0.04, 0.75), weight=[(0, 1.0), (1, 0.5)]))
    out += [
        # -- accents: smoke from the chimney, two birds far off ---------------
        S([(554, 252), (548, 236), (560, 222), (552, 206), (564, 192)], "accent", size=4),
        S([(468, 168), (480, 177), (490, 168), (500, 177), (512, 168)], "accent", size=4.5),
        S([(520, 140), (529, 146), (536, 139), (543, 146), (552, 140)], "accent", size=4),
    ]
    return out


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


ART = {"cat": cat, "scene": scene, "snail": snail}
