"""Draw like an illustrator, through the real editor, with a real pen.

The owner's brief for How it works' drawings: they must look like a skilled
person drew them, because the replay shows every stroke in order. So:

* REAL PEN INPUT. Strokes go in as Chrome's own pen input (CDP
  Input.dispatchMouseEvent, pointerType "pen", with force), so the editor sees
  trusted pointer events with pressure, exactly as from a stylus, and records
  them on its own clock. Timing and the hand's path come from handmotion.py.
* A STROKE HAS A ROLE, and the role sets its weight -- the illustrator's rule:
    gesture / contour   heavy, the outer silhouette and where shapes overlap
    form                medium, the shapes that turn the silhouette solid
    detail              light, interior marks
    accent              light and quick, the last few flicks
  Every stroke tapers: pressure rises from the touch and eases before the
  lift, so no line starts or stops blunt.
* AT MOST THREE COLOURS: Skribl purple, one accent, a dark ink, on paper.
* The ORDER is the drawing's own list, written gesture -> form -> detail ->
  accent, because the replay is the performance.

A drawing is a list of Stroke(...)s; draw(page, strokes) performs it.
"""
import math
import random
import time

import handmotion as hm

PURPLE = "#7c5cff"
INK = "#1f1b2e"
PAPER = "#f6f2ea"

# role -> (base brush px, peak pressure, pace)
ROLES = {
    "gesture": (13.0, 0.95, 0.95),
    "contour": (12.0, 0.92, 0.9),
    "form":    (7.5, 0.80, 1.0),
    "detail":  (5.0, 0.75, 0.85),
    "accent":  (4.5, 0.85, 1.6),
    "fill":    (6.0, 0.70, 1.9),
}


class Stroke:
    def __init__(self, pts, role="form", color=INK, *, size=None, pace=None, peak=None, taper=(0.12, 0.2), bend=0.0,
                 weight=None, tool="pen", shape=None):
        # `tool`: the dock tool this stroke is made with ("pen", "eraser",
        # "shape"), picked as a person taps it. `shape`: for the Shape tool,
        # {"kind": "rect"|"ellipse"|"poly"|"line", "radius": 0..50, "sides": n},
        # set on the shape card; the stroke's first and last points are the drag.
        self.tool, self.shape = tool, shape
        # `weight`: [(u, w), ...] along the stroke (u 0..1), where an artist
        # leans in or lifts off -- a contour swells on its shadow side and
        # thins where it turns into the light. Multiplies the taper.
        self.weight = weight
        self.pts, self.role, self.color = pts, role, color
        b, p, v = ROLES[role]
        self.size = size or b
        self.peak = peak or p
        self.pace = pace or v
        self.taper = taper
        self.bend = bend


def _wobble(path, amt, seed):
    """A hand's gentle bow along a long line -- low frequency, never jitter."""
    if amt <= 0 or len(path) < 3:
        return path
    rnd = random.Random(seed)
    L = sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(path, path[1:])) or 1
    ph1, ph2 = rnd.uniform(0, 6.28), rnd.uniform(0, 6.28)
    out, s = [path[0]], 0.0
    for i in range(1, len(path)):
        a, b = path[i - 1], path[i]
        s += math.hypot(b[0] - a[0], b[1] - a[1])
        u = s / L
        dx, dy = b[0] - a[0], b[1] - a[1]; d = math.hypot(dx, dy) or 1
        nx, ny = -dy / d, dx / d
        off = amt * (math.sin(math.pi * u) * 0.7 * math.sin(ph1 + u * 2.1) + 0.3 * math.sin(ph2 + u * 5.3))
        out.append((b[0] + nx * off, b[1] + ny * off))
    return out


def plan(strokes, seed=1, tempo=1.0):
    """Each stroke as timed points with its pressure: [(x, y, ms, p)] per stroke."""
    out = []
    for i, st in enumerate(strokes):
        path = hm.catmull(st.pts, 1.2)
        L = sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(path, path[1:]))
        path = _wobble(path, min(2.2, L / 220) if st.role in ("gesture", "contour", "form") else 0.6, seed * 97 + i)
        pts = hm.stroke(path, pace=st.pace * tempo, seed=seed * 31 + i, pmin=0.3, pmax=1.0, tremor=0.25)
        T = pts[-1][2] or 1
        a, b = st.taper
        shaped = []
        for x, y, ms, p_speed in pts:
            u = ms / T
            rise = min(1.0, u / a) if a > 0 else 1.0
            fall = min(1.0, (1 - u) / b) if b > 0 else 1.0
            env = (0.5 - 0.5 * math.cos(math.pi * rise)) * (0.5 - 0.5 * math.cos(math.pi * fall))
            # Mostly the envelope, a little of the speed (lighter where quick).
            w = 1.0
            if st.weight:
                ks = st.weight
                for (u0, w0), (u1, w1) in zip(ks, ks[1:]):
                    if u0 <= u <= u1:
                        f = (u - u0) / ((u1 - u0) or 1)
                        f = 0.5 - 0.5 * math.cos(math.pi * f)
                        w = w0 + (w1 - w0) * f
                        break
            p = st.peak * (0.12 + 0.88 * env) * w * (0.85 + 0.15 * p_speed)
            shaped.append((x, y, ms, max(0.04, min(1.0, p))))
        out.append(shaped)
    return out


def draw(page, strokes, *, seed=1, set_ink=None, canvas="#canvas", logical=None, tempo=1.0, pause_tempo=None):
    """Perform `strokes` on the editor canvas with real pen input.

    `set_ink(page, color, size)` sets the brush between strokes (the editor's
    own state); the default is Pad's globals, which Flip shares by name.
    `canvas` / `logical` say which canvas and its authored size (Flip: "#pad",
    (CW, CH)). `tempo` speeds the hand along each stroke and `pause_tempo` (by
    default the same) the gaps between strokes: a calm hand with brisk gaps
    keeps an example short without the line itself looking rushed."""
    box = page.locator(canvas).bounding_box()
    lg = logical or page.evaluate("() => { const s = getCanvasLogicalSize(); return [s.width, s.height]; }")
    sx, sy = box["width"] / lg[0], box["height"] / lg[1]
    cdp = page.context.new_cdp_session(page)
    set_ink = set_ink or (lambda pg, c, s: pg.evaluate("([c, s]) => { color = c; size = s; }", [c, s]))
    timed = plan(strokes, seed, tempo)
    prev_end, tool = None, None
    for st, pts in zip(strokes, timed):
        if st.tool != tool:
            page.evaluate("t => setTool(t)", st.tool); tool = st.tool
        if st.shape:
            page.evaluate("""s => { document.querySelector(`#shapeSeg [data-shape='${s.kind}']`).click();
                for (const [id, v] of [['shapeRadius', s.radius], ['shapeSides', s.sides]]) {
                  const el = document.getElementById(id); if (el == null || v == null) continue;
                  el.value = String(v); el.dispatchEvent(new Event('input', { bubbles: true })); }
                const p = document.getElementById('shapePop'); if (p) p.hidden = true; }""", st.shape)
        set_ink(page, st.color, st.size)
        if prev_end is not None:
            time.sleep(hm.pause(prev_end, st.pts[0], seed) / 1000 * 0.8 / (pause_tempo or tempo))
        t0 = time.perf_counter()
        for k, (x, y, ms, p) in enumerate(pts):
            while (time.perf_counter() - t0) * 1000 < ms:
                pass
            cdp.send("Input.dispatchMouseEvent", {
                "type": "mousePressed" if k == 0 else "mouseMoved",
                "x": box["x"] + x * sx, "y": box["y"] + y * sy,
                "button": "left", "buttons": 1, "clickCount": 1 if k == 0 else 0,
                "pointerType": "pen", "force": p})
        x, y = pts[-1][0], pts[-1][1]
        cdp.send("Input.dispatchMouseEvent", {"type": "mouseReleased", "x": box["x"] + x * sx,
                                              "y": box["y"] + y * sy, "button": "left", "buttons": 0,
                                              "clickCount": 1, "pointerType": "pen", "force": 0})
        prev_end = st.pts[-1]
    cdp.detach()
