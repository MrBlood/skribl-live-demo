"""Make the Text tool's lettering: skribl/static/fonts/text-*.json.

    python3 harness/tools/make_textfonts.py SVG_FONTS_DIR LETTERS_JSON [OUT_DIR]

Text (lib/textwrite.js) writes words as pen strokes, so every style is a set
of LINES, never filled outlines:

  print, script   two single-line fonts, made for pen plotters: EMS
                  Readability (from Source Sans Pro Light) and EMS Allure
                  (from Allura), by Sheldon B. Michaels, SVG conversion by
                  Windell H. Oskay, under the SIL Open Font License 1.1
                  (skribl/static/fonts/OFL.txt). SVG_FONTS_DIR is the
                  svg_fonts folder of the hersheytext npm package, 2.0.0.
  skribl          the owner's own hand: a letter set posted from Your hand
                  (/skribl-pad?letters=1) and read back by letterfont.py
                  (LETTERS_JSON). Each point keeps the time it was drawn at,
                  so Text writes it at the pace the owner wrote it.

THE UNITS. Everything is in 1/U of a cap height (U below), y UP from the
baseline: a font's x from its own origin, a hand's from the letter's ink
centre, as letterfont.py gives it. Each line is flat and DELTA-coded, the
first point whole and every later one the step from the one before: a font's
as x, y pairs, a hand's as x, y, t triples (t in ms from the letter's first
point). Small steps are short numbers, which is most of the file's size.

    font:  {"v":1, "kind":"font", "name", "u", "x", "adv", "g": {ch: [advance, line, ...]}}
    hand:  {"v":1, "kind":"hand", "name", "u", "x", "g": {id: [line, ...]}}

A hand's ids are Your hand's (editor_letters.js BOXES): letters, digits, the
16 marks, five accents drawn to sit over a letter, and second tries "e2"...

THINNED, NOT TRACED AGAIN. A font's curves are flattened and then simplified
to within TOL of themselves (a quarter of a percent of a cap height); a
hand's points are kept wherever they are SPACE apart, each with its own time,
so its speed along every stroke is the speed it was drawn at. lib/textwrite.js
fills the gaps in again as it writes, so the pen moves smoothly at any size.
"""
import json
import math
import os
import re
import sys
import xml.etree.ElementTree as ET

U = 250                  # units per cap height
TOL = 0.0025             # a font line's simplification tolerance, in cap heights
SPACE = 0.02             # a hand's point spacing, in cap heights

FONTS = {
    "print": ("EMSReadability.svg", "Print",
              "EMS Readability, by Sheldon B. Michaels (SVG by Windell H. Oskay), "
              "from Source Sans Pro Light by Paul D. Hunt. SIL Open Font License 1.1"),
    "script": ("EMSAllure.svg", "Script",
               "EMS Allure, by Sheldon B. Michaels (SVG by Windell H. Oskay), "
               "from Allura by Rob Leuschke. SIL Open Font License 1.1"),
}
# Letters, numbers, punctuation and the common accents. No emoji.
CHARS = ([chr(c) for c in range(32, 127)]
         + list("¡¿«»–—“”€£°·")
         + list("àáâãäåçèéêëìíîïñòóôõöùúûüýÿ")
         + list("ÀÁÂÃÄÅÇÈÉÊËÌÍÎÏÑÒÓÔÕÖÙÚÛÜÝ"))


# ---- a font: SVG glyph paths, flattened ----
def _bez(p0, p1, p2, p3, depth=0, out=None):
    """A cubic as a polyline, split until each piece is flat to within 0.2 units."""
    out = [] if out is None else out
    d1 = _dist_seg(p1, p0, p3)
    d2 = _dist_seg(p2, p0, p3)
    if depth > 10 or max(d1, d2) < 0.2:
        out.append(p3)
        return out
    m01 = _mid(p0, p1); m12 = _mid(p1, p2); m23 = _mid(p2, p3)
    m012 = _mid(m01, m12); m123 = _mid(m12, m23); m = _mid(m012, m123)
    _bez(p0, m01, m012, m, depth + 1, out)
    _bez(m, m123, m23, p3, depth + 1, out)
    return out


def _mid(a, b):
    return ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)


def _dist_seg(p, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    L = dx * dx + dy * dy
    if L == 0:
        return math.hypot(p[0] - a[0], p[1] - a[1])
    t = max(0, min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L))
    return math.hypot(p[0] - a[0] - t * dx, p[1] - a[1] - t * dy)


def path_lines(d):
    toks = re.findall(r"[MmLlHhVvCcSsQqTtZz]|-?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?", d or "")
    i, cmd, cur, start, lines, line, last_c = 0, None, (0.0, 0.0), (0.0, 0.0), [], [], None

    def num():
        nonlocal i
        v = float(toks[i]); i += 1
        return v
    while i < len(toks):
        t = toks[i]
        if re.match(r"[A-Za-z]", t):
            cmd = t; i += 1
            if cmd in "Zz":
                if line:
                    line.append(start); lines.append(line); line = []
                cur = start
                continue
        rel, C = cmd.islower(), cmd.upper()
        if C == "M":
            x, y = num(), num()
            if rel:
                x += cur[0]; y += cur[1]
            if line:
                lines.append(line)
            line = [(x, y)]; cur = start = (x, y); cmd = "l" if rel else "L"; last_c = None
        elif C == "L":
            x, y = num(), num()
            if rel:
                x += cur[0]; y += cur[1]
            line.append((x, y)); cur = (x, y); last_c = None
        elif C == "H":
            x = num(); x = x + cur[0] if rel else x
            line.append((x, cur[1])); cur = (x, cur[1]); last_c = None
        elif C == "V":
            y = num(); y = y + cur[1] if rel else y
            line.append((cur[0], y)); cur = (cur[0], y); last_c = None
        elif C in "CS":
            if C == "C":
                x1, y1, x2, y2, x, y = (num() for _ in range(6))
                if rel:
                    x1 += cur[0]; y1 += cur[1]
            else:
                x2, y2, x, y = (num() for _ in range(4))
                x1, y1 = (2 * cur[0] - last_c[0], 2 * cur[1] - last_c[1]) if last_c else cur
            if rel:
                x2 += cur[0]; y2 += cur[1]; x += cur[0]; y += cur[1]
            line.extend(_bez(cur, (x1, y1), (x2, y2), (x, y))); last_c = (x2, y2); cur = (x, y)
        elif C in "QT":
            if C == "Q":
                qx, qy, x, y = (num() for _ in range(4))
                if rel:
                    qx += cur[0]; qy += cur[1]
            else:
                x, y = num(), num()
                qx, qy = (2 * cur[0] - last_c[0], 2 * cur[1] - last_c[1]) if last_c else cur
            if rel:
                x += cur[0]; y += cur[1]
            c1 = (cur[0] + 2 / 3 * (qx - cur[0]), cur[1] + 2 / 3 * (qy - cur[1]))
            c2 = (x + 2 / 3 * (qx - x), y + 2 / 3 * (qy - y))
            line.extend(_bez(cur, c1, c2, (x, y))); last_c = (qx, qy); cur = (x, y)
        else:
            i += 1
    if line:
        lines.append(line)
    return [l for l in lines if len(l) >= 2]


def rdp(pts, tol):
    if len(pts) < 3:
        return pts
    a, b = pts[0], pts[-1]
    k, far = 0, -1.0
    for i in range(1, len(pts) - 1):
        d = _dist_seg(pts[i], a, b)
        if d > far:
            k, far = i, d
    if far <= tol:
        return [a, b]
    return rdp(pts[:k + 1], tol)[:-1] + rdp(pts[k:], tol)


def load_svg_font(path):
    root = ET.parse(path).getroot()
    ns = {"s": "http://www.w3.org/2000/svg"}
    font = root.find(".//s:font", ns)
    adv = float(font.get("horiz-adv-x", 500))
    glyphs = {}
    for g in font.findall("s:glyph", ns):
        u = g.get("unicode")
        if u:
            glyphs[u] = (float(g.get("horiz-adv-x", adv)), path_lines(g.get("d")))
    return adv, glyphs


def delta(flat, width):
    """Whole numbers, the first `width` of them as they are, the rest as steps."""
    out = []
    prev = [0] * width
    for i in range(0, len(flat), width):
        row = flat[i:i + width]
        out.extend(v - p for v, p in zip(row, prev))
        prev = row
    return out


def _median(v):
    v = sorted(v)
    return v[len(v) // 2]


def build_font(path, name, credit):
    adv, glyphs = load_svg_font(path)
    # WHERE THE LINES ARE, read from the letters rather than the font's own
    # metadata: a single-line font is the middle of a drawn outline, so its
    # baseline sits half a stroke above 0, and a script's x-height is its own.
    # The middle of a dozen letters, so one swash cannot move a line.
    lo = lambda ch: min(y for line in glyphs[ch][1] for _, y in line)
    hi = lambda ch: max(y for line in glyphs[ch][1] for _, y in line)
    small = "acemnorsuvwz"
    base = _median([lo(c) for c in small])
    xh = _median([hi(c) for c in small]) - base
    cap = _median([hi(c) for c in "BDEFHIKLMNPRTUVWXZ"]) - base
    k = U / cap
    out = {}
    for ch in CHARS:
        if ch not in glyphs:
            continue
        a, lines = glyphs[ch]
        enc = [round(a * k)]
        for line in lines:
            line = rdp(line, TOL * cap)
            flat = []
            for x, y in line:
                flat += [round(x * k), round((y - base) * k)]
            # a line that rounds to one point is a dot: keep it as one
            if len(flat) >= 4 and all(v == flat[j % 2] for j, v in enumerate(flat)):
                flat = flat[:2] + flat[:2]
            enc.append(delta(flat, 2))
        out[ch] = enc
    return {"v": 1, "kind": "font", "name": name, "credit": credit, "u": U,
            "x": round(xh * k), "adv": round(adv * k), "g": out}


# ---- a hand: a posted letter set, read back ----
def build_hand(letters_json, name):
    doc = json.load(open(letters_json, encoding="utf-8"))
    L = doc["letters"]
    lines = doc.get("lines") or {"cap": 0.16, "x": 0.334, "base": 0.74}
    xh = (lines["base"] - lines["x"]) / (lines["base"] - lines["cap"])
    out = {}
    for gid, strokes in L.items():
        if not strokes:
            continue
        enc = []
        for st in strokes:
            kept = [st[0]]
            for p in st[1:]:
                q = kept[-1]
                if math.hypot(p[0] - q[0], p[1] - q[1]) >= SPACE:
                    kept.append(p)
            if st[-1] is not kept[-1]:
                kept.append(st[-1])   # the stroke ends where the pen lifted
            flat = []
            for x, y, _w, t in kept:
                flat += [round(x * U), round(y * U), int(t)]
            enc.append(delta(flat, 3))
        out[gid] = enc
    return {"v": 1, "kind": "hand", "name": name, "u": U, "x": round(xh * U), "g": out}


def main(argv):
    if len(argv) < 3:
        sys.exit(__doc__)
    svg_dir, letters = argv[1], argv[2]
    out_dir = argv[3] if len(argv) > 3 else os.path.join(
        os.path.dirname(__file__), "..", "..", "skribl", "static", "fonts")
    os.makedirs(out_dir, exist_ok=True)
    made = {key: build_font(os.path.join(svg_dir, f), name, credit)
            for key, (f, name, credit) in FONTS.items()}
    made["skribl"] = build_hand(letters, "Skribl")
    for key, doc in made.items():
        text = json.dumps(doc, ensure_ascii=False, separators=(",", ":"))
        p = os.path.normpath(os.path.join(out_dir, "text-%s.json" % key))
        with open(p, "w", encoding="utf-8") as f:
            f.write(text)
        print("%-7s %4d glyphs  %6d bytes  %s" % (key, len(doc["g"]), len(text.encode("utf-8")), p))


if __name__ == "__main__":
    main(sys.argv)
