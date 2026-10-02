#!/usr/bin/env python3
"""Make the examples How it works plays -- REAL Skribls, drawn by the real editor.

    python3 harness/tools/make_help_demos.py            # every demo
    python3 harness/tools/make_help_demos.py pen shape  # just these

Each demo is drawn by driving Skribl Pad with a pointer along a hand-drawn path
(speed eases in and out, the line wobbles a little, the way a hand does), and
what the editor records is what is saved: `serializeSkribl()` straight to
skribl/static/help/demos/<name>.json. So the Eraser example is what the eraser
does, not a picture of it, and when a tool changes, re-running this re-records
its example from the tool itself. Nothing here is drawn by hand-written stroke
data.

Needs the local server (harness/bootstrap.sh) at SKRIBL_BASE or 127.0.0.1:5001.
verify_helpdemos.py checks every file this writes: it validates as a post, it
plays, and every tool on each editor has one.
"""
import json
import math
import os
import pathlib
import random
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE.parent))
import browsing  # noqa: E402

OUT = ROOT / "skribl" / "static" / "help" / "demos"
BASE = os.environ.get("SKRIBL_BASE", "http://127.0.0.1:5001")
W, H = 816, 612            # Pad's default 4:3 canvas, the help cards' shape

# Skribl's own palette (lib/palette.js), so the examples look like Skribls.
PURPLE, PINK, SKY, SUN, MINT = "#7c5cff", "#ff5ca8", "#38bdf8", "#facc15", "#34d399"


# ---- hand-drawn paths, in canvas units ------------------------------------
def ease(n):
    """Parameter values that start slow, travel, and settle: a hand's speed."""
    return [0.5 - 0.5 * math.cos(math.pi * i / (n - 1)) for i in range(n)]


def wobble(pts, amt, seed):
    rnd = random.Random(seed)
    out, dx, dy = [], 0.0, 0.0
    for x, y in pts:
        dx = dx * 0.85 + rnd.uniform(-amt, amt) * 0.15
        dy = dy * 0.85 + rnd.uniform(-amt, amt) * 0.15
        out.append((x + dx, y + dy))
    return out


def curve(fn, n=60, seed=1, amt=1.2):
    return wobble([fn(t) for t in ease(n)], amt, seed)


def arc(cx, cy, rx, ry, a0, a1, n=60, seed=1):
    return curve(lambda t: (cx + rx * math.cos(a0 + (a1 - a0) * t),
                            cy + ry * math.sin(a0 + (a1 - a0) * t)), n, seed)


def seg(x0, y0, x1, y1, n=24, seed=1):
    return curve(lambda t: (x0 + (x1 - x0) * t, y0 + (y1 - y0) * t), n, seed, 0.8)


def petal(cx, cy, ang, length, width, n=40, seed=1):
    ca, sa = math.cos(ang), math.sin(ang)

    def f(t):
        a = t * 2 * math.pi
        u, v = length * (1 - math.cos(a)) / 2, width * math.sin(a) / 2
        return cx + u * ca - v * sa, cy + u * sa + v * ca
    return curve(f, n, seed)


# ---- the demos ---------------------------------------------------------------
# Each is a list of steps: ("tool", name), ("color", hex), ("size", px), or
# ("stroke", [points]) / ("drag", (x0, y0), (x1, y1)) for the Shape tool.
def teardrop(tip, base, width, n=46, seed=1):
    """A petal or leaf: pointed at `tip`, round at `base`, drawn as one loop."""
    (tx, ty), (bx, by) = tip, base
    L = math.hypot(bx - tx, by - ty); ca, sa = (bx - tx) / L, (by - ty) / L

    def f(t):
        a = t * 2 * math.pi
        u = L * (1 - math.cos(a)) / 2
        v = width * math.sin(a) * (u / L) ** 0.8
        return tx + u * ca - v * sa, ty + u * sa + v * ca
    return curve(f, n, seed)


def demo_pen():
    """A flower, the way someone doodles one: stem, a leaf, petals, centre."""
    cx, cy = 408, 230
    s = [("tool", "pen"), ("size", 22), ("color", MINT),
         ("stroke", curve(lambda t: (cx + 18 * math.sin(t * 2.4), 585 - (585 - cy - 150) * t), 30, 3)),
         ("stroke", teardrop((cx + 14, 500), (cx + 175, 395), 34, 40, 4))]
    s += [("color", PINK)]
    for i in range(5):
        a = math.radians(-90 + i * 72)
        s.append(("stroke", teardrop((cx, cy), (cx + 175 * math.cos(a), cy + 175 * math.sin(a)), 120, 44, 10 + i)))
    s += [("color", SUN), ("size", 40), ("stroke", arc(cx, cy, 34, 34, 0, 2 * math.pi, 30, 20))]
    return s


def demo_eraser():
    """Three bold lines, then the eraser cuts a clean channel through them."""
    s = [("tool", "pen"), ("size", 30)]
    for i, c in enumerate((PURPLE, PINK, SKY)):
        y = 160 + i * 150
        s += [("color", c), ("stroke", curve(lambda t, y=y: (100 + 616 * t, y + 34 * math.sin(t * 1.5 * 2 * math.pi)), 40, 30 + i))]
    s += [("tool", "eraser"), ("size", 70),
          ("stroke", curve(lambda t: (440 - 60 * t, 70 + 480 * t), 30, 40))]
    return s


def demo_shape():
    return [("tool", "shape"), ("size", 20),
            ("shape", "poly"), ("sides", 5), ("radius", 22), ("color", PURPLE), ("drag", (80, 70), (380, 340)),
            ("shape", "rect"), ("radius", 34), ("color", SKY), ("drag", (440, 90), (740, 300)),
            ("shape", "ellipse"), ("color", PINK), ("drag", (250, 370), (570, 560))]


def demo_draw():
    """The first quick-start card: a sun with a face, doodled."""
    cx, cy, r = 408, 306, 150
    s = [("tool", "pen"), ("size", 24), ("color", SUN),
         ("stroke", arc(cx, cy, r, r, -math.pi / 2, 1.5 * math.pi, 46, 50))]
    for i in range(10):
        a = i * 2 * math.pi / 10 + 0.12
        s.append(("stroke", seg(cx + (r + 38) * math.cos(a), cy + (r + 38) * math.sin(a),
                                cx + (r + 100) * math.cos(a), cy + (r + 100) * math.sin(a), 10, 60 + i)))
    s += [("color", PURPLE), ("size", 30),
          ("stroke", arc(cx - 52, cy - 38, 8, 16, 0, 2 * math.pi, 14, 70)),
          ("stroke", arc(cx + 52, cy - 38, 8, 16, 0, 2 * math.pi, 14, 71)),
          ("size", 24), ("stroke", arc(cx, cy + 6, 74, 58, 0.18 * math.pi, 0.82 * math.pi, 26, 72))]
    return s


DEMOS = {"pen": demo_pen, "eraser": demo_eraser, "shape": demo_shape, "draw": demo_draw}


# ---- driving the editor -----------------------------------------------------
def run(page, steps):
    box = page.locator("#canvas").bounding_box()
    sx, sy = box["width"] / W, box["height"] / H
    to = lambda p: (box["x"] + p[0] * sx, box["y"] + p[1] * sy)
    for step in steps:
        kind = step[0]
        if kind == "tool":
            page.evaluate("t => setTool(t)", step[1])
        elif kind == "color":
            page.evaluate("c => { color = c; }", step[1])
        elif kind == "size":
            page.evaluate("s => { size = s; }", step[1])
        elif kind == "shape":
            page.evaluate("k => document.querySelector(`#shapeSeg [data-shape='${k}']`).click()", step[1])
        elif kind in ("sides", "radius"):
            el = "shapeSides" if kind == "sides" else "shapeRadius"
            page.evaluate("([id, v]) => { const s = document.getElementById(id); s.value = String(v);"
                          " s.dispatchEvent(new Event('input', { bubbles: true })); }", [el, step[1]])
        elif kind == "stroke":
            pts = [to(p) for p in step[1]]
            page.mouse.move(*pts[0]); page.mouse.down()
            for p in pts[1:]:
                page.mouse.move(*p)
            page.mouse.up(); page.wait_for_timeout(90)
        elif kind == "drag":
            a, b = step[1], step[2]
            page.mouse.move(*to(a)); page.mouse.down()
            for t in ease(30)[1:]:
                page.mouse.move(*to((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)))
                page.wait_for_timeout(8)
            page.mouse.up(); page.wait_for_timeout(220)
        page.evaluate("() => { const p = document.getElementById('shapePop'); if (p) p.hidden = true; }")


def make(browser, name):
    ctx = browser.new_context(viewport={"width": 1280, "height": 960})
    page = ctx.new_page()
    errs = []
    page.on("pageerror", lambda e: errs.append(str(e)))
    browsing.goto(page, BASE, "/skribl-pad")
    page.wait_for_timeout(800)
    page.evaluate("() => { window.SkriblHints && window.SkriblHints.hide(); }")
    # 4:3, the cards' shape, through the editor's own Canvas picker (free while
    # the canvas is empty). Pad otherwise picks a shape from the window.
    page.evaluate("""() => { const t = window.SkriblCanvasSizes, id = t.SIZES.find(s => s.label === '4:3').id;
        document.querySelector(`#canvasSeg button[data-size='${id}']`).click(); }""")
    page.wait_for_timeout(300)
    run(page, DEMOS[name]())
    payload = page.evaluate("""() => { const p = serializeSkribl();
        for (const k of ['draftId', 'createdAt', 'updatedAt', 'title', 'userId']) delete p[k];
        // The base layer is an empty PNG on a canvas nothing was pasted into:
        // ~25 KB of transparent pixels per example. Strokes are the drawing.
        for (const f of p.frames) delete f.baseSnapshot;
        return p; }""")
    ctx.close()
    if errs:
        raise SystemExit(f"{name}: page errors {errs[:2]}")
    pts = sum(len(f.get("strokes") or []) for f in payload["frames"])
    path = OUT / f"{name}.json"
    path.write_text(json.dumps(payload, separators=(",", ":")))
    f0 = payload["frames"][0]
    print(f"{name:10s} {pts:5d} points  {f0['strokes'][-1]['t'] / 1000:5.1f} s  "
          f"{payload['canvasSize']['cssWidth']}x{payload['canvasSize']['cssHeight']}  "
          f"{path.stat().st_size:7,d} B  {path.relative_to(ROOT)}")


if __name__ == "__main__":
    from playwright.sync_api import sync_playwright
    OUT.mkdir(parents=True, exist_ok=True)
    names = sys.argv[1:] or list(DEMOS)
    with sync_playwright() as p:
        b = p.chromium.launch()
        for n in names:
            make(b, n)
        b.close()
