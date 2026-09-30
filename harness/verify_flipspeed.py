#!/usr/bin/env python3
"""verify_flipspeed: Flip keeps up with a finger on a busy page (v317).

The owner, on a phone: "It draws the stroke, but it takes 3 seconds, then falls
further behind on every stroke." render() repainted the backdrop, the onion
skin and every stroke on the page on every pointer move, so the cost of a move
grew with the ink already there -- 7 ms a move on the first stroke, 37 ms by
the twentieth at a 4x CPU throttle on a 1062x1888 canvas, where a frame has 16.
v314 measured the same: not a regression, a page that got busy.

The live-stroke cache (flip.js, above render()) paints what cannot change
during a stroke once, at pen-down. This suite pins the two things that matter:

  1  SPEED, by what is painted rather than by the clock: while a stroke is
     drawn on a page of twenty, each move paints the live stroke only.
  2  THE PICTURE, by pixels: mid-stroke, the pad matches an independent full
     repaint of the same page (paintUnder + paintFrame, the functions render()
     uses when the cache is off) for a pen, a see-through pen, the eraser, the
     onion skin over earlier pages, the mirror, and a page sitting exactly on
     the layer budget. After pen-up the pad matches EXACTLY, every case.

A pen stroke is painted straight over a flattened bitmap, which is associative
with painting it on its own layer but not bit-identical: each draw rounds to
8 bits in a different space, and the error grows with the number of draws that
land on one pixel. That is the only tolerance here (ROUNDING, below), and the
eraser's path (its own layer, three copies) has none.

ROUNDING is set by what it has to separate, not by the last reading. It used
to BE the last reading: 2/255, taken on one canvas size. #289 moved this
suite's 1100x860 window from a 944x531 canvas to 816x612, where the unchanged
cache reads 3 with the mirror on, and main went red on a cache that had not
changed. Across eight windows (six canvas sizes in device pixels, pixel ratios
1 to 3) the cache reads at most 3 (the mirror), 2 (the onion skin, a pen) and
1 (a see-through pen). One mutation per part of
the cache sets the other end: the onion missing reads 19 (this fixture's onion
lies under the page's own ink, so only its edges show), a flipped layer budget
45, the finished ink or the live stroke's reflections missing 242. Each of
those is still red at ROUNDING.
"""
import math
import os
import sys

from assertions import make_check
import browsing

try:
    from playwright.sync_api import sync_playwright
except Exception as exc:                                   # pragma: no cover
    print(f"SUITE-SKIPPED: playwright unavailable ({exc})")
    raise SystemExit(77)

BASE = os.environ.get("SKRIBL_BASE", "http://127.0.0.1:5001")
results = []
check = make_check(results)

# Clear of the worst rounding measured (3) and of the faintest defect this
# suite can produce (19); the docstring has both readings.
ROUNDING = 8

# The pad against an independent full repaint of the same page, in device pixels.
COMPARE = """() => {
  const pad = document.getElementById('pad'), w = pad.width, h = pad.height;
  const got = pad.getContext('2d').getImageData(0, 0, w, h).data;
  const cv = document.createElement('canvas'); cv.width = w; cv.height = h;
  const c = cv.getContext('2d'); c.setTransform(DPR, 0, 0, DPR, 0, 0);
  paintUnder(c); paintFrame(c, frame().strokes);
  const exp = c.getImageData(0, 0, w, h).data;
  let n = 0, m = 0;
  for (let i = 0; i < got.length; i++) { const d = Math.abs(got[i] - exp[i]); if (d) { n++; if (d > m) m = d; } }
  return { differ: n, most: m, cached: _liveUsable(), flat: !!(_liveCache && _liveCache.flat) };
}"""


def open_flip(b, **ctx_kw):
    ctx = b.new_context(**ctx_kw)
    pg = ctx.new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    browsing.goto(pg, BASE, "/flip")
    pg.wait_for_timeout(800)
    pg.evaluate("() => { window.SkriblHints && window.SkriblHints.hide();"
                " try { localStorage.removeItem('skribl_flip_autosave_v1'); } catch (e) {} }")
    return ctx, pg, errs


def geometry(pg):
    box = pg.locator("#pad").bounding_box()
    return box, box["x"] + box["width"] / 2, box["y"] + box["height"] / 2


def stroke(pg, k, lift=True, moves=24):
    box, cx, cy = geometry(pg)
    x0 = cx - box["width"] * 0.36
    y = cy - box["height"] * 0.36 + (k % 18) * box["height"] * 0.04
    pg.mouse.move(x0, y)
    pg.mouse.down()
    for i in range(moves):
        pg.mouse.move(x0 + i * box["width"] * 0.03, y + math.sin(i / 3 + k) * box["height"] * 0.08)
    if lift:
        pg.mouse.up()
        pg.wait_for_timeout(60)


def crossing(pg, lift=False):
    """A stroke that crosses every earlier one, top to bottom."""
    box, cx, cy = geometry(pg)
    pg.mouse.move(cx, cy - box["height"] * 0.4)
    pg.mouse.down()
    for i in range(30):
        pg.mouse.move(cx + math.sin(i / 4) * box["width"] * 0.1, cy - box["height"] * 0.4 + i * box["height"] * 0.027)
    if lift:
        pg.mouse.up()


with sync_playwright() as p:
    b = p.chromium.launch()

    # ------------------------------------------------------------------ 1
    print("\n1 — A MOVE PAINTS THE LIVE STROKE, NOT THE PAGE")
    ctx, pg, errs = open_flip(b, viewport={"width": 390, "height": 844}, has_touch=True,
                              device_scale_factor=3)
    for k in range(20):
        stroke(pg, k)
    pg.evaluate("""() => { window.__segs = 0; const f = window.paintSeg;
        window.paintSeg = function () { window.__segs++; return f.apply(this, arguments); };
        window.__renders = 0; const r = window.render;
        window.render = function () { window.__renders++; return r.apply(this, arguments); }; }""")
    box, cx, cy = geometry(pg)
    pg.mouse.move(cx - 60, cy + 30)
    pg.mouse.down()
    pg.evaluate("() => { window.__segs = 0; window.__renders = 0; }")
    for i in range(20):
        pg.mouse.move(cx - 60 + i * 6, cy + 30 + math.sin(i / 3) * 15)
    per = pg.evaluate("() => ({ segs: window.__segs, renders: window.__renders, cached: _liveUsable() })")
    pg.mouse.up()
    pg.wait_for_timeout(200)
    check("on a page of twenty strokes, the stroke being drawn uses the cache",
          per["cached"] is True, str(per))
    check("and each move repaints ONE stroke, not twenty-one",
          per["renders"] >= 15 and 1 <= per["segs"] <= per["renders"],
          f"{per['segs']} strokes painted over {per['renders']} moves")
    after = pg.evaluate(COMPARE)
    check("pen-up leaves the page exactly as a full repaint draws it",
          after["differ"] == 0 and after["cached"] is False, str(after))
    ctx.close()

    # ------------------------------------------------------------------ 2
    print("\n2 — MID-STROKE, THE PAD IS THE PAGE (pixels, not a description)")
    CASES = [
        ("a pen", "() => { color = '#ff3366'; }", "stroke", True),
        ("a see-through pen, across its own kind",
         "() => { color = 'rgba(40,160,255,0.5)'; }", "crossing", True),
        ("the eraser, across ink", "() => { color = '#ffffff'; }", "erase", False),
        ("the onion skin over two earlier pages", "() => { color = '#33ff99'; onion = true; }", "onion", True),
        ("the mirror, both ways", "() => { color = '#ffcc00'; SkriblMirror.setMode('both'); }", "stroke", True),
    ]
    for name, setup, kind, flat in CASES:
        ctx, pg, errs = open_flip(b, viewport={"width": 1100, "height": 860}, device_scale_factor=2)
        pg.evaluate(setup)
        if kind == "onion":
            for page in range(2):
                for k in range(4):
                    stroke(pg, k + page * 4)
                pg.evaluate("() => addFrame()")
                pg.wait_for_timeout(150)
        for k in range(8):
            stroke(pg, k)
        if kind == "erase":
            pg.evaluate("() => { erasing = true; }")
            crossing(pg)
        elif kind == "crossing":
            crossing(pg)
        else:
            stroke(pg, 11, lift=False)
        mid = pg.evaluate(COMPARE)
        pg.mouse.up()
        pg.wait_for_timeout(200)
        end = pg.evaluate(COMPARE)
        if flat:
            check(f"{name}: mid-stroke, the cached pad matches a full repaint within rounding ({ROUNDING}/255)",
                  mid["cached"] and mid["flat"] and mid["most"] <= ROUNDING,
                  f"{mid['differ']} channels differ, most by {mid['most']}; cached={mid['cached']}")
        else:
            check(f"{name}: mid-stroke, the cached pad matches a full repaint EXACTLY",
                  mid["cached"] and not mid["flat"] and mid["differ"] == 0,
                  f"{mid['differ']} channels differ, most by {mid['most']}; cached={mid['cached']}")
        check(f"{name}: after pen-up, exactly", end["differ"] == 0 and not end["cached"], str(end))
        check(f"{name}: no page errors", not errs, "; ".join(errs[:2]))
        pg.evaluate("() => { SkriblMirror.setMode('off'); }")
        ctx.close()

    # ------------------------------------------------------------------ 3
    print("\n3 — ON THE LAYER BUDGET, THE STROKE REPAINTS IN FULL")
    ctx, pg, errs = open_flip(b, viewport={"width": 1100, "height": 860}, device_scale_factor=1)
    budget = pg.evaluate("() => LAYER_BUDGET")
    pg.evaluate("() => { color = 'rgba(255,80,40,0.45)'; }")
    for k in range(budget):
        stroke(pg, k, moves=8)
    n_layer = pg.evaluate("() => layerableCount(frame().strokes, strokeAlphaOf)")
    crossing(pg)
    mid = pg.evaluate(COMPARE)
    pg.mouse.up()
    check(f"a page holding exactly {budget} see-through strokes is at the budget",
          n_layer == budget, f"{n_layer} layerable")
    check("the stroke that would tip it over skips the cache, and the pad is the page exactly",
          mid["cached"] is False and mid["differ"] == 0, str(mid))
    ctx.close()
    b.close()

passed = sum(1 for ok, _ in results if ok)
bad = [n for ok, n in results if not ok]
print("\n" + "=" * 62)
print(f"{passed}/{len(results)} passed"
      + ("" if not bad else "\nFAILURES:\n  - " + "\n  - ".join(bad)))
sys.exit(1 if bad else 0)
