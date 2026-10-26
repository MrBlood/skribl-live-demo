#!/usr/bin/env python3
"""A bigger canvas, sharp (the owner's B, "All yes"): on a big window the
drawing shows bigger than the size it was drawn at, and stays sharp.

The owner: "Is there any way that when canvas opens on a desktop it can have
a full screen button so it opens over everything else to full screen? So if
you're on a giant screen the editor/canvas can be huge?" The mock showed
today's canvas at 694x521 on every desk, a fifth of a 1920 screen, held there
by the 720px column; B lets the canvas's row reach past the column to the
page's edges and draws the drawing again at the size it shows rather than
stretching it. A (draw in full screen) builds on this.

The rows, on both editors:

  THE SIZE. On a 1920x945 and a 2560x1300 window, in light and dark, the
  canvas shows as big as the window allows past 1:1, as the mock measured
  (the Pad's cat 1017x763 and 1491x1118, Flip's Blooby card 752x564 and
  1225x919), and its bitmap is the size it shows (inside Flip's frame), to the
  pixel, so it is sharp. The row the
  canvas sits in spans the page, while the header and the dock stay in the
  column, and nothing scrolls sideways. The page is one surface: read on the
  screenshot's pixels, the page at the window's edge is the page beside the
  canvas (the column's edges and the darker page beside it would cut across
  the row).

  PIXEL FOR PIXEL. Grown, the screen shows the bitmap one pixel for one: a
  1px line put into it comes out one screen pixel, full dark, on both editors
  at 1x. (Flip's frame, 2px a side, squeezed a bitmap grown to its outside into
  its inside, and every line came out two pixels at half.) At 2x and 1.25x the
  canvas inside its frame is its bitmap's size in the screen's pixels, to the
  page's 1/64px; where it lands on the screen is the browser's there (half a
  pixel off, it blends), so those are measured by size. And a page is laid on
  Flip's grown pad pixel for pixel: the pad is the page's own layer over the
  ground. (Laid through the transform it was stretched by a fraction of a
  pixel; a page played from Flip's cache is pinned in verify_framecache.)

  THE DRAWING DOES NOT CHANGE. A stroke on a grown canvas lands under the
  pen, in the drawing's own units, and the payload's canvasSize is the size it
  was drawn at. A new drawing starts in the shape a 720px column would give it.
  Flip's fill makes the same runs on a grown canvas as on one that is not.

  WHAT LEAVES IT STAYS THE DRAWING'S SIZE. The Pad's PNG, its GIF and its post
  card, and Flip's GIF and its page tiles, are the sizes a small window makes.

  THE RINGS AND THE PICK. The Pad's eraser ring and Flip's pen ring are the
  width the stroke will be on the grown canvas, and the eyedropper picks the
  ink under the pen.

  SETTLING, KINDLY. A window made smaller and big again keeps the drawing to
  the pixel, and the canvas is never blank while its bitmap is made again
  (read on every frame). A window dragged through many sizes remakes the
  bitmap once, when it stops. A resize while the pen is down waits for the
  pen to lift, and the stroke is whole. A zoom that changes the screen's ratio
  without a resize remakes the bitmap at the new ratio, and a stroke drawn at
  once, before that, still lands under the pen.

  A PHONE IS AS IT WAS, and the bitmap never holds more than a phone at 3x
  already carries (Flip: what it draws at on a 2x screen); past that the
  canvas still shows bigger.

For calibration: BIGCANVAS_PART=size (pixels, drawing, files, fill, rings,
settle, phone, caps) runs one part, and BIGCANVAS_ONLY=Pad (or Flip) one editor. A real
run sets neither.
"""
import json
import os
import struct
import sys

from assertions import make_check

BASE = os.environ.get("SKRIBL_BASE", "http://127.0.0.1:5001")
results = []
check = make_check(results, with_detail=True)


def summarise_and_exit():
    bad = [r for r in results if not r[0]]
    print(f"\n{'=' * 62}\n{len(results) - len(bad)}/{len(results)} passed"
          + ("" if not bad else "  FAILURES: " + ", ".join(r[1] for r in bad)))
    sys.exit(1 if bad else 0)


try:
    from playwright.sync_api import sync_playwright
except ImportError as exc:
    print(f"SUITE-SKIPPED: {exc}")
    print("No assertions were executed. This is NOT evidence the canvas grows sharp on a big window.")
    raise SystemExit(77)
import browsing  # noqa: E402
from io import BytesIO  # noqa: E402
from PIL import Image  # noqa: E402

ONLY = os.environ.get("BIGCANVAS_ONLY", "")
PART = os.environ.get("BIGCANVAS_PART", "")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEMO = {"Pad": json.load(open(os.path.join(ROOT, "skribl/static/help/demos/cat.json"))),
        "Flip": json.load(open(os.path.join(ROOT, "skribl/static/help/demos/flip-blooby-card.json")))}
ROUTE = {"Pad": "/skribl-pad", "Flip": "/flip"}
LOAD = {"Pad": "(d) => { loadSkribl(d); }", "Flip": "(d) => { applyFlipDraftObject(d); }"}
CANVAS = {"Pad": "canvas", "Flip": "pad"}
ROW = {"Pad": ".canvas-area", "Flip": ".flip-stage"}
DOCK = {"Pad": "#toolBar", "Flip": ".flip-tools"}
# Measured on the mock (the owner's yes was to these): the demo drawings at
# their own sizes, on the two screens' browser windows.
SHOWN = {("Pad", 1920): (1017, 763), ("Pad", 2560): (1491, 1118),
         ("Flip", 1920): (752, 564), ("Flip", 2560): (1225, 919)}
WINDOWS = {1920: (1920, 945), 2560: (2560, 1300)}
# Flip at 1920 has no room past 1:1 (its page bar and strip stay under the
# canvas), so it shows smaller than drawn; the growth rows ask the 2560.
EDITORS = [e for e in ("Pad", "Flip") if not ONLY or e == ONLY]


def part(name):
    return not PART or PART == name


def eds(name):
    return EDITORS if part(name) else []


# The canvas as shown and as held, the screen's ratio, and the editor's ratio.
# Inside Flip's frame (its border) is where the drawing shows; the Pad has none.
READ = """(id) => { const c = document.getElementById(id), r = c.getBoundingClientRect(), s = getComputedStyle(c);
  const bl = parseFloat(s.borderLeftWidth) || 0, bt = parseFloat(s.borderTopWidth) || 0;
  return { shown: [Math.round(r.width), Math.round(r.height)], at: [r.left, r.top, r.width, r.height], frame: [bl, bt],
           inner: [r.width - bl - (parseFloat(s.borderRightWidth) || 0), r.height - bt - (parseFloat(s.borderBottomWidth) || 0)],
           bitmap: [c.width, c.height], dpr: devicePixelRatio,
           ratio: typeof canvasRatio === 'function' && id === 'canvas' ? canvasRatio() : (typeof RS !== 'undefined' ? RS : null),
           drawn: id === 'canvas' ? [authoredW, authoredH] : [CW, CH] }; }"""
# Where the row, the header and the dock are, and whether the page scrolls sideways.
BOXES = """(o) => { const box = (s) => { const e = document.querySelector(s); if (!e) return null; const r = e.getBoundingClientRect(); return [r.left, r.width]; };
  const se = document.scrollingElement;
  return { row: box(o.row), header: box('.header'), dock: box(o.dock), body: document.body.clientWidth,
           sideways: se.scrollWidth - se.clientWidth, wide: document.body.classList.contains('canvas-wide') }; }"""
# A point of ink in the drawing, as a share of the canvas, found by looking.
FIND_INK = """(id) => { const c = document.getElementById(id), g = c.getContext('2d');
  const d = g.getImageData(0, 0, c.width, c.height).data, W = c.width, H = c.height;
  for (let y = Math.round(H * 0.3); y < H * 0.7; y += 2) for (let x = Math.round(W * 0.3); x < W * 0.7; x += 2) {
    let ok = true;
    for (let dy = -2; dy <= 2 && ok; dy++) for (let dx = -2; dx <= 2 && ok; dx++) if (d[((y + dy) * W + x + dx) * 4 + 3] < 250) ok = false;
    if (ok) return [x / W, y / H]; }
  return null; }"""


def editor(b, name, w, h, theme="light", demo=True, **extra):
    c = b.new_context(viewport={"width": w, "height": h}, color_scheme=theme, accept_downloads=True, **extra)
    pg = c.new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    browsing.goto(pg, BASE, ROUTE[name])
    pg.evaluate("() => localStorage.clear()")
    pg.evaluate("() => window.SkriblHints && window.SkriblHints.hide && window.SkriblHints.hide()")
    if demo:
        pg.evaluate(LOAD[name], DEMO[name])
    pg.wait_for_timeout(1300)
    return c, pg, errs


CAP = {"Pad": 3, "Flip": 2}


def held(name, m):
    """The bitmap's width this editor should hold for what it shows: the shown size in
    the screen's pixels past 1:1 (to its ceiling), the drawing's own under it. Flip's
    is the size inside its frame."""
    grow = max(1.0, min(m["shown"][0] / m["drawn"][0], CAP[name] / m["dpr"]))
    if name == "Flip":
        grow = max(1.0, min(m["inner"][0] / m["drawn"][0], CAP[name] / min(m["dpr"], 2)))
        return int(m["drawn"][0] * min(m["dpr"], 2) * grow + 1e-6)
    return round(m["drawn"][0] * m["dpr"] * grow)


# The drawing at 400x300, so even a small window has room to grow it, settled.
SMALL = {"Pad": "() => { establishEditorCanvas(400, 300); layoutEditorCanvas(); }",
         "Flip": "() => { applyCanvasSize(400, 300, {silent: true}); sizeStage(); }"}
SETTLED = {"Pad": "() => grownTo(_growWant)", "Flip": "() => layersGrownTo(_growWant)"}
# Whatever sits over the canvas (the grid, the starter words, the pen's dot)
# hidden, and any pattern behind it, so a screenshot shows the bitmap alone.
BARE = """(id) => { const c = document.getElementById(id), r = c.getBoundingClientRect();
  for (const el of document.querySelectorAll('body *')) { if (el === c || el.contains(c)) continue;
    const q = el.getBoundingClientRect(); if (q.right > r.left && q.left < r.right && q.bottom > r.top && q.top < r.bottom) el.style.visibility = 'hidden'; }
  for (let p = c; p; p = p.parentElement) p.style.backgroundImage = 'none'; }"""
# A 1px black line every 40 of the bitmap's own pixels, put straight into it.
LINES = """(id) => { const c = document.getElementById(id), g = c.getContext('2d');
  g.save(); g.setTransform(1, 0, 0, 1, 0, 0); g.globalCompositeOperation = 'copy'; g.fillStyle = '#fff'; g.fillRect(0, 0, c.width, c.height);
  g.globalCompositeOperation = 'source-over'; g.fillStyle = '#000';
  for (let x = 5; x < c.width - 4; x += 40) g.fillRect(x, 0, 1, c.height); g.restore(); }"""
STILL = "(id) => { const g = document.getElementById(id).getContext('2d'); return [g.getImageData(5, 9, 1, 1).data[0], g.getImageData(6, 9, 1, 1).data[0]]; }"
# Three strokes in dark ink on a fresh page, the page painted, and the pad read
# against the page's own layer over the ground (Flip paints a page through it).
LAID = """() => { frames.length = 0; const f = newFrame();
  for (const [y0, y1, size, col] of [[0.2, 0.8, 9, '#1d1b2e'], [0.75, 0.3, 4, '#5a2fd4'], [0.5, 0.55, 16, '#0e3b2a']]) {
    const pts = [];
    for (let j = 0; j < 40; j++) pts.push({ x: CW * (0.1 + 0.8 * j / 39), y: CH * (y0 + (y1 - y0) * j / 39) + Math.sin(j / 5) * CH * 0.04,
                                            color: col, size: size, t: j * 8, start: j === 0 });
    f.strokes.push(...pts); f.strokeGroups.push(pts.length); }
  frames.push(f); idx = 0; buildStrip(); render();
  const W = pad.width, H = pad.height, P = ctx.getImageData(0, 0, W, H).data, F = fctx.getImageData(0, 0, W, H).data;
  const g = [P[0], P[1], P[2]];
  let worst = 0, inked = 0;
  for (let i = 0; i < P.length; i += 4) { const a = F[i + 3] / 255; if (a < 0.125) continue; inked++;
    for (let k = 0; k < 3; k++) worst = Math.max(worst, Math.abs(P[i + k] - (F[i + k] * a + g[k] * (1 - a)))); }
  return { grown: W > CW, inked: inked, worst: Math.round(worst), ground: g, bitmap: [W, H],
           over: [CW * RS - Math.floor(CW * RS + 1e-6), CH * RS - Math.floor(CH * RS + 1e-6)] }; }"""


# The pad kept, and later read against it away from the band at the foot where
# a stroke is under way: a page painted from the live layers holds still.
SNAP = "() => { window.__snap = ctx.getImageData(0, 0, pad.width, pad.height); }"
STILL_UNDER = """() => { const W = pad.width, H = pad.height, a = window.__snap.data, b = ctx.getImageData(0, 0, W, H).data, band = Math.floor(H * 0.88);
  let worst = 0, n = 0;
  for (let i = 0; i < band * W * 4; i += 4) { const d = Math.max(Math.abs(a[i] - b[i]), Math.abs(a[i + 1] - b[i + 1]), Math.abs(a[i + 2] - b[i + 2]));
    if (d > worst) worst = d; if (d > 2) n++; }
  return { worst: worst, n: n, live: _liveUsable(), drawing: drawing, erasing: erasing }; }"""


def small(pg, name):
    pg.evaluate(SMALL[name])
    pg.wait_for_function(SETTLED[name], timeout=10000)
    pg.wait_for_timeout(300)
    return pg.evaluate(READ, CANVAS[name])


def lines_on_screen(pg, name):
    """Each line where it should land on the screen, as (pixels dark, darkest), and
    whether the lines were still in the bitmap after the screenshot."""
    cid = CANVAS[name]
    pg.evaluate(BARE, cid)
    pg.evaluate(LINES, cid)
    m = pg.evaluate(READ, cid)
    shot = Image.open(BytesIO(pg.screenshot(animations="disabled"))).convert("L")
    still = pg.evaluate(STILL, cid) == [0, 255]
    d = m["dpr"]
    L, T = m["at"][0] + m["frame"][0], m["at"][1] + m["frame"][1]
    W, H = m["inner"]
    y = int((T + H / 2) * d)
    out = []
    for bx in range(5, m["bitmap"][0] - 4, 40):
        sx = (L + (bx + 0.5) * W / m["bitmap"][0]) * d
        win = [255 - shot.getpixel((x, y)) for x in range(int(sx) - 3, int(sx) + 4)]
        out.append((sum(1 for v in win if v > 12), max(win)))
    return out, still, m


def stroke(pg, pts, steps=6):
    pg.mouse.move(*pts[0]); pg.mouse.down()
    for p in pts[1:]:
        pg.mouse.move(*p, steps=steps)
    pg.mouse.up()


def png_size(path):
    raw = open(path, "rb").read(24)
    return struct.unpack(">II", raw[16:24])


def gif_size(path):
    raw = open(path, "rb").read(10)
    return raw[6] | (raw[7] << 8), raw[8] | (raw[9] << 8)


with sync_playwright() as sp:
    b = sp.chromium.launch()

    # ================= THE SIZE =================
    if part("size"):
        print("THE SIZE: as big as the window allows, sharp, on one surface")
    for name in eds("size"):
        for scr, (w, h) in WINDOWS.items():
            for theme in ("light", "dark"):
                c, pg, errs = editor(b, name, w, h, theme)
                m = pg.evaluate(READ, CANVAS[name])
                want = SHOWN[(name, scr)]
                tag = f"{name}, a {w}x{h} window, {theme}"
                check(f"{tag}: the canvas shows at the size the mock measured",
                      abs(m["shown"][0] - want[0]) <= 2 and abs(m["shown"][1] - want[1]) <= 2,
                      f"{m['shown'][0]}x{m['shown'][1]}, the mock {want[0]}x{want[1]}, drawn at {m['drawn'][0]}x{m['drawn'][1]}")
                # Sharp: the bitmap is what shows (inside Flip's frame), to the pixel.
                past = m["shown"][0] > m["drawn"][0]
                inner = [round(v * m["dpr"]) for v in m["inner"]]
                check(f"{tag}: the bitmap is the size it shows, to the pixel" + (" (past 1:1, so it grew)" if past else " (under 1:1, the drawing's own)"),
                      (m["bitmap"] == inner) if past
                      else (m["bitmap"][0] == round(m["drawn"][0] * m["dpr"])),
                      f"bitmap {m['bitmap'][0]}x{m['bitmap'][1]} for {inner[0]}x{inner[1]} showing (inside the frame) at {m['dpr']}x")
                bx = pg.evaluate(BOXES, {"row": ROW[name], "dock": DOCK[name]})
                check(f"{tag}: the canvas's row spans the page; the header and the dock stay in the column; nothing scrolls sideways",
                      bx["row"] and abs(bx["row"][1] - bx["body"]) <= 1 and abs(bx["row"][0]) <= 12
                      and bx["header"] and bx["header"][1] <= 720 and bx["dock"] and bx["dock"][1] <= 720
                      and bx["sideways"] <= 0,
                      f"row {bx['row']}, page {bx['body']}, header {bx['header']}, dock {bx['dock']}, sideways {bx['sideways']}")
                # One surface, on the pixels, at the foot of the window (under
                # the dock, and under the glow, which has faded by then): the
                # window's edge, and either side of the column's edge. Today the
                # column is lighter than the page beside it, by 9 levels in dark.
                img = Image.open(BytesIO(pg.screenshot())).convert("RGB")
                col = pg.evaluate("() => document.querySelector('.app').getBoundingClientRect().left")
                y = h - 6
                px = [img.getpixel((x, y)) for x in (4, int(col) - 3, int(col) + 3)]
                near = max(abs(px[i][k] - px[j][k]) for i in range(3) for j in range(3) for k in range(3))
                check(f"{tag}: the page is one surface: the window's edge and either side of the column's edge are one colour",
                      bx["wide"] and near <= 2,
                      f"edge {px[0]}, outside the column {px[1]}, inside it {px[2]} ({near} apart), body.canvas-wide {bx['wide']}")
                check(f"{tag}: no page errors", not errs, "; ".join(errs[:2]))
                c.close()

    # ================= PIXEL FOR PIXEL =================
    if part("pixels"):
        print("PIXEL FOR PIXEL: the screen shows the bitmap one for one")
    for name in eds("pixels"):
        c, pg, errs = editor(b, name, 2560, 1300, demo=False)
        got, still, m = lines_on_screen(pg, name)
        crisp = sum(1 for n, pk in got if n == 1 and pk >= 250)
        check(f"{name}: grown at 1x, the screen shows the bitmap pixel for pixel: a 1px line put in it is one screen pixel, full dark",
              m["bitmap"][0] > m["drawn"][0] and still and len(got) >= 12 and crisp == len(got),
              f"{crisp} of {len(got)} lines crisp (pixels dark, darkest: {got[:2]} ... {got[len(got) // 2]}); "
              f"bitmap {m['bitmap'][0]}x{m['bitmap'][1]}, {m['inner'][0]:.2f}x{m['inner'][1]:.2f} inside the frame; lines kept {still}")
        c.close()
    for name, w, h, dpr in (("Pad", 640, 600, 2), ("Pad", 1440, 900, 1.25), ("Flip", 1000, 800, 1.25)):
        if name not in eds("pixels"):
            continue
        c, pg, errs = editor(b, name, w, h, demo=False, device_scale_factor=dpr)
        m = small(pg, name)
        dev = [v * dpr for v in m["inner"]]
        check(f"{name}: grown at {dpr}x, the canvas inside its frame is its bitmap's size in the screen's pixels, to the page's 1/64px",
              m["bitmap"][0] > m["drawn"][0] * dpr and all(0 <= dev[i] - m["bitmap"][i] < 0.05 for i in (0, 1)),
              f"{dev[0]:.3f}x{dev[1]:.3f} screen pixels for a {m['bitmap'][0]}x{m['bitmap'][1]} bitmap ({m['drawn'][0]}x{m['drawn'][1]} drawn, {w}x{h})")
        c.close()
    # Laid through the transform, a layer is stretched only where CW*RS runs
    # half a pixel or more past its whole pixels (under that the browser lays
    # it one for one anyway), so these rows ask a ratio that does, both ways:
    # 400x300 at 1.25x on a 1000x800 window, 691.67 by 518.75.
    if "Flip" in eds("pixels"):
        c, pg, errs = editor(b, "Flip", 1000, 800, demo=False, device_scale_factor=1.25)
        small(pg, "Flip")
        r = pg.evaluate(LAID)
        check("Flip: grown, a page is laid on the pad pixel for pixel: the pad is the page's own layer over the ground",
              r["grown"] and min(r["over"]) >= 0.5 and r["inked"] > 2000 and r["worst"] <= 3,
              f"{r['inked']} inked pixels, the worst {r['worst']} levels from the layer over the ground {r['ground']}; "
              f"bitmap {r['bitmap']}, the drawing {[round(v, 2) for v in r['over']]}px past its whole pixels")
        # While the pen is down the page comes from the live layers, laid on
        # the same way: it holds still under the pen, to the pixel.
        for tool in ("pen", "eraser"):
            pg.evaluate("(t) => setTool(t)", tool)
            pg.evaluate(SNAP)
            m = pg.evaluate(READ, "pad")
            L, T, W, H = m["at"]
            y = T + H * 0.96
            pg.mouse.move(L + W * 0.3, y); pg.mouse.down()
            for k in range(1, 7):
                pg.mouse.move(L + W * (0.3 + 0.05 * k), y, steps=2)
            pg.wait_for_timeout(150)
            st = pg.evaluate(STILL_UNDER)
            pg.mouse.up(); pg.wait_for_timeout(200)
            check(f"Flip: grown, with the {tool} down the page under it holds still to the pixel (the live layers laid on one for one)",
                  st["live"] and st["drawing"] and st["erasing"] == (tool == "eraser") and st["worst"] <= 2,
                  f"the worst {st['worst']} levels off, {st['n']} pixels more than 2; painted from the live layers {st['live']}")
        check("Flip: no page errors laying a page", not errs, "; ".join(errs[:2]))
        c.close()

    # ================= THE DRAWING DOES NOT CHANGE =================
    if part("drawing"):
        print("THE DRAWING: under the pen, in its own units, in the shape it always started in")
    for name in eds("drawing"):
        c, pg, errs = editor(b, name, 2560, 1300, demo=False)
        m = pg.evaluate(READ, CANVAS[name])
        L, T, W, H = m["at"]
        n0 = pg.evaluate("() => strokes.length" if name == "Pad" else "() => frame().strokes.length")
        stroke(pg, [(L + W * 0.3, T + H * 0.5), (L + W * 0.5, T + H * 0.5), (L + W * 0.7, T + H * 0.6)])
        pg.wait_for_timeout(300)
        got = pg.evaluate(("(n) => { const p = strokes[n]; return p ? [p.x, p.y] : null; }" if name == "Pad"
                           else "(n) => { const p = frame().strokes[n]; return p ? [p.x, p.y] : null; }"), n0)
        want = [m["drawn"][0] * 0.3, m["drawn"][1] * 0.5]
        # The pen's own colour at the stroke's middle (Flip's pad holds its
        # ground in the bitmap too, so an opaque pixel alone says nothing).
        ink = pg.evaluate("""(id) => { const c = document.getElementById(id);
          const d = c.getContext('2d').getImageData(Math.round(c.width * 0.5), Math.round(c.height * 0.5), 1, 1).data;
          const h = (typeof color === 'string' ? color : '#000000').replace('#', '');
          const pen = [0, 2, 4].map(i => parseInt(h.slice(i, i + 2), 16));
          return { px: [d[0], d[1], d[2], d[3]], pen: pen, off: Math.max(...pen.map((v, i) => Math.abs(v - d[i]))) }; }""",
                          CANVAS[name])
        check(f"{name}: a stroke on the grown canvas lands under the pen, in the drawing's own units, and its ink is there",
              m["bitmap"][0] > m["drawn"][0] and got and abs(got[0] - want[0]) <= 0.6 and abs(got[1] - want[1]) <= 0.6
              and ink["off"] <= 24 and ink["px"][3] > 200,
              f"first point {got}, under the pen {[round(v, 2) for v in want]}; at the stroke's middle {ink['px']}, the pen {ink['pen']}; "
              f"bitmap {m['bitmap'][0]} for {m['drawn'][0]} drawn")
        size = pg.evaluate("() => { const p = serializeSkribl(); return p.canvasSize; }" if name == "Pad"
                           else "() => serializeFlip({ media: false }).canvasSize")
        check(f"{name}: the payload says the size it was drawn at",
              size and size.get("cssWidth") == m["drawn"][0] and size.get("cssHeight") == m["drawn"][1],
              f"{size} for {m['drawn']}")
        check(f"{name}: no page errors drawing on a grown canvas", not errs, "; ".join(errs[:2]))
        c.close()
        # The shape a new drawing starts in: the big window's against a window
        # the column's own width, the same height.
        shapes = []
        for w in (2560, 760):
            c, pg, _ = editor(b, name, w, 1300, demo=False)
            shapes.append(pg.evaluate("() => SkriblCanvasSizes.idFor(authoredW, authoredH)" if name == "Pad"
                                      else "() => SkriblCanvasSizes.idFor(CW, CH)"))
            c.close()
        check(f"{name}: a new drawing on a big window starts in the shape a 720px column gives it",
              shapes[0] == shapes[1], f"{shapes[0]} on a 2560 window, {shapes[1]} on a 760")

    # ================= WHAT LEAVES IT =================
    if part("files"):
        print("THE FILES: the drawing's own size, from a grown canvas")
    if "Pad" in eds("files"):
        sizes = {}
        for w, h in ((1280, 720), (2560, 1300)):
            c, pg, errs = editor(b, "Pad", w, h)
            grown = pg.evaluate("() => canvasRatio() / devicePixelRatio")
            pg.evaluate("() => { document.getElementById('exportSheet').hidden = false; }")
            with pg.expect_download(timeout=60000) as dl:
                pg.evaluate("() => document.getElementById('exportPng').click()")
            png = png_size(dl.value.path())
            with pg.expect_download(timeout=120000) as dl2:
                pg.evaluate("() => document.getElementById('exportGif').click()")
            gif = gif_size(dl2.value.path())
            card = pg.evaluate("() => { const c = window.skriblPreviewCanvas(); return [c.width, c.height]; }")
            sizes[w] = {"grown": grown, "png": png, "gif": gif, "card": card}
            c.close()
        small, big = sizes[1280], sizes[2560]
        check("Pad: from a grown canvas the PNG, the GIF and the post card are the sizes a small window makes",
              small["grown"] == 1 and big["grown"] > 1.5
              and big["png"] == small["png"] == (816, 612) and big["gif"] == small["gif"] and big["card"] == small["card"] == [816, 612],
              f"at 1280 (grown {small['grown']:.2f}): PNG {small['png']}, GIF {small['gif']}, card {small['card']}; "
              f"at 2560 (grown {big['grown']:.2f}): PNG {big['png']}, GIF {big['gif']}, card {big['card']}")
    if "Flip" in eds("files"):
        sizes = {}
        for w, h in ((1280, 720), (2560, 1300)):
            c, pg, errs = editor(b, "Flip", w, h)
            grown = pg.evaluate("() => RS / DPR")
            tile = pg.evaluate("() => { const t = document.querySelector('.strip canvas'); return t ? [t.width, t.height] : null; }")
            pg.evaluate("() => openExportSheet()"); pg.wait_for_timeout(300)
            with pg.expect_download(timeout=180000) as dl:
                pg.click("#exportGif")
            sizes[w] = {"grown": grown, "gif": gif_size(dl.value.path()), "tile": tile}
            c.close()
        small, big = sizes[1280], sizes[2560]
        check("Flip: from a grown canvas the GIF and the page tiles are the sizes a small window makes",
              small["grown"] == 1 and big["grown"] > 1.4 and big["gif"] == small["gif"] == (816, 612)
              and big["tile"] == small["tile"] and big["tile"] is not None,
              f"at 1280 (grown {small['grown']:.2f}): GIF {small['gif']}, tile {small['tile']}; "
              f"at 2560 (grown {big['grown']:.2f}): GIF {big['gif']}, tile {big['tile']}")

    # ================= FLIP'S FILL =================
    if "Flip" in eds("fill"):
        print("FLIP'S FILL: the same runs on any screen")
        BOX = """() => { applyCanvasSize(816, 612); const f = frame(); f.strokes.length = 0; f.strokeGroups.length = 0;
          const box = [[245,184],[571,184],[571,428],[245,428],[245,184]]; let t = 0;
          for (let k = 0; k < box.length - 1; k++) { const a = box[k], q = box[k+1];
            for (let i = 0; i <= 20; i++) f.strokes.push({ x: a[0] + (q[0]-a[0]) * i / 20, y: a[1] + (q[1]-a[1]) * i / 20,
              color: '#141414', size: 6, t: t++, start: k === 0 && i === 0 }); }
          f.strokeGroups.push(f.strokes.length); render(); }"""
        runs = {}
        for w, h in ((1280, 720), (2560, 1300)):
            c, pg, errs = editor(b, "Flip", w, h, demo=False)
            pg.evaluate(BOX); pg.wait_for_timeout(700)
            grown = pg.evaluate("() => RS / DPR")
            n0 = pg.evaluate("() => frame().strokes.length")
            pg.evaluate("() => doFill({ x: 408, y: 306 })"); pg.wait_for_timeout(300)
            runs[w] = (grown, pg.evaluate("(n) => { const s = frame().strokes.slice(n); return [s.length, frame().strokeGroups.length - 1, "
                                          "Math.round(s.reduce((m, p) => m + p.size, 0) * 100) / 100]; }", n0))
            c.close()
        check("Flip: a fill on a grown canvas makes the runs it makes on one that is not",
              runs[1280][0] == 1 and runs[2560][0] > 1.4 and runs[1280][1] == runs[2560][1] and runs[1280][1][0] > 20,
              f"at 1280 (grown {runs[1280][0]:.2f}): {runs[1280][1]} (points, runs, widths); "
              f"at 2560 (grown {runs[2560][0]:.2f}): {runs[2560][1]}")

    # ================= THE RINGS AND THE PICK =================
    if part("rings"):
        print("THE RINGS AND THE PICK: the stroke's width, the ink under the pen")
    for name in eds("rings"):
        # The Pad's demo is a finished take, which locks the canvas (no ring
        # shows on it), so the Pad draws its own ink to ring and to pick.
        c, pg, errs = editor(b, name, 2560, 1300, demo=(name == "Flip"))
        m = pg.evaluate(READ, CANVAS[name])
        L, T, W, H = m["at"]
        if name == "Pad":
            pg.evaluate("() => { size = 24; }")
            stroke(pg, [(L + W * 0.35, T + H * 0.5), (L + W * 0.65, T + H * 0.5)], steps=12)
            pg.wait_for_timeout(300)
            pg.evaluate("() => { const e = document.getElementById('eraserToolBtn'); if (e) e.click(); }")
            pg.mouse.move(L + W * 0.4, T + H * 0.4); pg.mouse.move(L + W * 0.41, T + H * 0.41); pg.wait_for_timeout(200)
            ring = pg.evaluate("""() => { const e = document.getElementById('eraserCursor'), r = canvas.getBoundingClientRect();
              return [e.style.display, e.getBoundingClientRect().width, _eraserSize(size, true) * r.width / authoredW]; }""")
            pg.evaluate("() => { const p = document.getElementById('penToolBtn'); if (p) p.click(); }")
        else:
            pg.mouse.move(L + W * 0.4, T + H * 0.4); pg.mouse.move(L + W * 0.41, T + H * 0.41); pg.wait_for_timeout(200)
            ring = pg.evaluate("""() => { const e = document.querySelector('.flip-brush-cursor'), r = pad.getBoundingClientRect();
              return [e.style.display, e.getBoundingClientRect().width, Math.max(2, size * r.width / CW)]; }""")
        check(f"{name}: on a grown canvas the ring is the width the {'eraser' if name == 'Pad' else 'pen'} will be",
              ring[0] == "block" and abs(ring[1] - ring[2]) <= 0.6 and m["bitmap"][0] > m["drawn"][0],
              f"ring {ring[1]:.2f}px shown ({ring[0]}), the stroke {ring[2]:.2f}px, grown to {m['bitmap'][0]} for {m['drawn'][0]}")
        # The pick: the colour of the ink under the pen, on the grown canvas.
        at = pg.evaluate(FIND_INK, CANVAS[name])
        want = pg.evaluate("""(o) => { const c = document.getElementById(o.id), d = c.getContext('2d')
          .getImageData(Math.round(c.width * o.at[0]), Math.round(c.height * o.at[1]), 1, 1).data;
          return '#' + [d[0], d[1], d[2]].map(v => v.toString(16).padStart(2, '0')).join(''); }""", {"id": CANVAS[name], "at": at})
        # As a person picks: the Draw drawer, the eyedropper, the lens, a click.
        pg.evaluate("() => setPenColor ? setPenColor('#00a95c') : null" if name == "Pad" else "() => setColor('#00a95c')")
        browsing.pad_drawer(pg, "draw", settle=400)
        pg.click("#eyedropperBtn"); pg.wait_for_timeout(400)
        r = pg.evaluate(READ, CANVAS[name])["at"]                 # the drawer may have moved the page
        pg.mouse.move(r[0] + r[2] * at[0] - 30, r[1] + r[3] * at[1] - 30)
        pg.mouse.click(r[0] + r[2] * at[0], r[1] + r[3] * at[1]); pg.wait_for_timeout(300)
        got = pg.evaluate("() => color")
        check(f"{name}: on a grown canvas the eyedropper's lens picks the ink under it",
              at is not None and isinstance(got, str) and got.lower() == want.lower(),
              f"picked {got} where the ink is {want} (at {[round(v, 3) for v in at]})")
        c.close()

    # ================= SETTLING =================
    if part("settle"):
        print("SETTLING: the drawing kept, never blank, once at the end, never mid-stroke, a zoom followed")
    for name in eds("settle"):
        c, pg, errs = editor(b, name, 2560, 1300)
        cv = CANVAS[name]
        snap = """(id) => { const c = document.getElementById(id); return c.toDataURL(); }"""
        pg.set_viewport_size({"width": 1280, "height": 720}); pg.wait_for_timeout(800)
        before = pg.evaluate(snap, cv)
        small = pg.evaluate(READ, cv)
        pg.set_viewport_size({"width": 2560, "height": 1300}); pg.wait_for_timeout(800)
        big = pg.evaluate(READ, cv)
        pg.set_viewport_size({"width": 1280, "height": 720}); pg.wait_for_timeout(800)
        after = pg.evaluate(snap, cv)
        check(f"{name}: a window made big and small again keeps the drawing to the pixel",
              big["bitmap"][0] > small["bitmap"][0] and before == after,
              f"{small['bitmap']} -> {big['bitmap']} -> back; the same pixels: {before == after}")
        # Never blank: an ink point read on every frame while the window grows
        # and the bitmap is made again.
        at = pg.evaluate(FIND_INK, cv)
        pg.evaluate("""(o) => { window.__inkLog = []; const c = document.getElementById(o.id);
          (function tick() { const d = c.getContext('2d').getImageData(Math.round(c.width * o.at[0]), Math.round(c.height * o.at[1]), 1, 1).data;
            window.__inkLog.push([c.width, d[3]]); if (window.__inkLog.length < 150) requestAnimationFrame(tick); })(); }""",
                    {"id": cv, "at": at})
        pg.set_viewport_size({"width": 2560, "height": 1300}); pg.wait_for_timeout(2600)
        log = pg.evaluate("() => window.__inkLog")
        widths = sorted(set(w for w, a in log))
        blank = [w for w, a in log if a < 128]
        check(f"{name}: while the bitmap is made again the canvas is never blank (read on every frame)",
              at is not None and len(widths) >= 2 and not blank,
              f"{len(log)} frames over the bitmaps {widths}; {len(blank)} with no ink at the drawing's ink point {at}")
        # Once at the end: a window dragged through eight sizes.
        made = ("() => { window.__made = 0; const f = establishEditorCanvas; establishEditorCanvas = function () { window.__made++; return f.apply(this, arguments); }; }"
                if name == "Pad" else
                "() => { window.__made = 0; const f = growLayersNow; growLayersNow = function () { window.__made++; return f.apply(this, arguments); }; }")
        pg.evaluate(made)
        for k in range(8):
            pg.set_viewport_size({"width": 1700 + k * 100, "height": 900 + k * 50}); pg.wait_for_timeout(40)
        pg.wait_for_timeout(900)
        n = pg.evaluate("() => window.__made")
        end = pg.evaluate(READ, cv)
        check(f"{name}: a window dragged through eight sizes makes the bitmap once, when it stops, at the size it stops at",
              n == 1 and abs(end["bitmap"][0] - held(name, end)) <= 2,
              f"made {n} times; at the end {end['bitmap'][0]} for {end['shown'][0]} shown (wants {held(name, end)})")
        c.close()
        # Mid-stroke: the pen down through a resize, on a canvas that takes
        # ink (the Pad's demo is a finished take, which locks it).
        c, pg, errs = editor(b, name, 2560, 1300, demo=(name == "Flip"))
        m = pg.evaluate(READ, cv)
        L, T, W, H = m["at"]
        n0 = pg.evaluate("() => strokes.length" if name == "Pad" else "() => frame().strokes.length")
        pg.mouse.move(L + W * 0.2, T + H * 0.2); pg.mouse.down()
        pg.mouse.move(L + W * 0.25, T + H * 0.25, steps=4)
        pg.set_viewport_size({"width": 1920, "height": 945}); pg.wait_for_timeout(700)
        during = pg.evaluate(f"() => document.getElementById('{cv}').width")
        pg.mouse.move(L + W * 0.3, T + H * 0.3, steps=4); pg.mouse.up(); pg.wait_for_timeout(900)
        after = pg.evaluate(READ, cv)
        n1 = pg.evaluate("() => strokes.length" if name == "Pad" else "() => frame().strokes.length")
        check(f"{name}: a resize with the pen down waits for the pen to lift, and the stroke is whole",
              during == m["bitmap"][0] and abs(after["bitmap"][0] - held(name, after)) <= 2
              and after["bitmap"][0] != m["bitmap"][0] and n1 - n0 >= 6,
              f"bitmap {m['bitmap'][0]} before, {during} with the pen down, {after['bitmap'][0]} after for {after['shown'][0]} shown "
              f"(wants {held(name, after)}); {n1 - n0} points in the stroke")
        check(f"{name}: no page errors settling", not errs, "; ".join(errs[:2]))
        c.close()
    if "Pad" in eds("settle"):
        # A zoom: the screen's ratio changes with no resize at all.
        c, pg, errs = editor(b, "Pad", 1920, 945, demo=False)
        cdp = c.new_cdp_session(pg)
        cdp.send("Emulation.setDeviceMetricsOverride", {"width": 1920, "height": 945, "deviceScaleFactor": 1.25, "mobile": False})
        # At once, before the bitmap is made again: the pen's point.
        m = pg.evaluate(READ, "canvas")
        L, T, W, H = m["at"]
        n0 = pg.evaluate("() => strokes.length")
        stroke(pg, [(L + W * 0.6, T + H * 0.2), (L + W * 0.62, T + H * 0.22)], steps=2)
        first = pg.evaluate("(n) => { const p = strokes[n]; return p ? [p.x, p.y] : null; }", n0)
        pg.wait_for_timeout(1200)
        z = pg.evaluate(READ, "canvas")
        want = [m["drawn"][0] * 0.6, m["drawn"][1] * 0.2]
        check("Pad: a zoom with no resize: a stroke at once lands under the pen, and the bitmap is made at the new ratio",
              first and abs(first[0] - want[0]) <= 1 and abs(first[1] - want[1]) <= 1
              and z["dpr"] == 1.25 and abs(z["bitmap"][0] - z["shown"][0] * 1.25) <= 2,
              f"first point {first} under the pen {[round(v, 1) for v in want]}; at {z['dpr']}x the bitmap {z['bitmap'][0]} "
              f"for {z['shown'][0]} shown (wants {z['shown'][0] * 1.25:.0f})")
        c.close()

    # ================= A PHONE, AND THE CEILING =================
    if part("phone"):
        print("A PHONE: as it was")
    for name in eds("phone"):
        c, pg, errs = editor(b, name, 402, 874, device_scale_factor=3, is_mobile=True, has_touch=True)
        m = pg.evaluate(READ, CANVAS[name])
        wide = pg.evaluate("() => document.body.classList.contains('canvas-wide')")
        held = 3 if name == "Pad" else 2
        check(f"{name}: on a phone the canvas is as it was: under 1:1, its bitmap the drawing at the screen's ratio, no reach",
              m["shown"][0] < m["drawn"][0] and m["bitmap"][0] == round(m["drawn"][0] * held) and not wide,
              f"{m['shown']} shown, bitmap {m['bitmap']} for {m['drawn']} at {held}x, canvas-wide {wide}")
        c.close()
    if part("caps"):
        print("THE CEILING: never more than a phone at 3x carries (Flip: a 2x screen)")
    for name in eds("caps"):
        c, pg, errs = editor(b, name, 2560, 1300, device_scale_factor=2)
        m = pg.evaluate(READ, CANVAS[name])
        cap = 3 if name == "Pad" else 2
        check(f"{name}: on a 2x desk the bitmap stops at {cap}x the drawing, and the canvas still shows bigger",
              m["shown"][0] > m["drawn"][0] * 1.4 and abs(m["bitmap"][0] - m["drawn"][0] * cap) <= 2,
              f"{m['shown'][0]} shown, bitmap {m['bitmap'][0]} for {m['drawn'][0]} drawn ({m['bitmap'][0] / m['drawn'][0]:.2f}x)")
        c.close()

    b.close()

summarise_and_exit()
