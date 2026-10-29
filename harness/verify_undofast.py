"""Undo on the Pad without painting the whole drawing again (polish list item 2).

THE COST (Phase 1, measured). A history state is the stroke list and its base,
never pixels: a full canvas copy per stroke once pinned half a gigabyte
(makeHistoryState, app.js). So every Undo painted the whole drawing again, and
on a two-hour piece (145,200 points) that was 1.6 to 1.9 s at this box's own
pace, every press. Now each stroke, as it is laid, is copied into one of three
canvases kept for it (padUndoKeep, editor_draw.js), and Undo and Redo put a
drawing back from its copy when its points, base, size and stroke layers are
the ones the copy was taken of (padUndoRestore). Anything else repaints as
before.

WHAT IS ASKED, AND HOW IT IS READ
  * Undo, twice, and Redo, put back exactly the canvas from before: every pixel
    of the bitmap, read with getImageData and compared with what the canvas
    held at that moment while it was being drawn. And none of them paints the
    drawing again: paintStrokesStatic is counted.
  * Further back than the copies reach, Undo paints as it did, once.
  * A copy is never put back on a canvas that has changed size since: the
    window grows, the canvas is made again at the new size (app.js
    growCanvasNow), and Undo paints rather than lay the old size's pixels on it.
  * The copies are three canvases, reused, however many strokes are laid.

Pad only: Flip's Undo works on one page (flip.js undoStroke), and its pages
are drawn from their own caches.
"""
import os
import sys

from assertions import make_check
import browsing

try:
    from playwright.sync_api import sync_playwright
except ImportError as exc:
    print(f"SUITE-SKIPPED: {exc}")
    print("No assertions were executed. This is NOT evidence Undo puts a drawing back.")
    raise SystemExit(77)

BASE = os.environ.get("SKRIBL_BASE", "http://127.0.0.1:5001")
results = []
check = make_check(results, with_detail=True)

# Every pixel of the bitmap, folded into one number, and the bitmap's size.
PIX = """() => { const c = document.getElementById('canvas');
  const d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data; let h = 2166136261 >>> 0;
  for (let i = 0; i < d.length; i++) h = Math.imul(h ^ d[i], 16777619) >>> 0;
  return [h, c.width, c.height]; }"""
# paintStrokesStatic's calls, counted from here on.
COUNT = """() => { window.__paints = 0; const f = window.paintStrokesStatic;
  if (!f.__counted) { window.paintStrokesStatic = function () { window.__paints++; return f.apply(this, arguments); };
    window.paintStrokesStatic.__counted = true; } }"""


def stroke(pg, box, k):
    """One stroke through real pointer events, each a little different."""
    x0, y0 = box["x"] + 60 + k * 30, box["y"] + 90 + k * 45
    pg.mouse.move(x0, y0)
    pg.mouse.down()
    for i in range(28):
        pg.mouse.move(x0 + i * 7, y0 + (i % 7) * 4 + k * 2)
        pg.wait_for_timeout(12)
    pg.mouse.up()
    pg.wait_for_timeout(250)


def undo(pg, which="#undoBtn"):
    pg.evaluate("(s) => { window.__paints = 0; document.querySelector(s).click(); }", which)
    pg.wait_for_timeout(250)
    return pg.evaluate(PIX), pg.evaluate("() => window.__paints")


with sync_playwright() as p:
    b = p.chromium.launch()

    print("\nUNDO — a drawing the canvas held a moment ago comes back from its copy")
    pg = b.new_page(viewport={"width": 1280, "height": 900})
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    browsing.goto(pg, BASE, "/")
    pg.evaluate("() => window.SkriblHints && window.SkriblHints.hide && window.SkriblHints.hide()")
    box = pg.locator("#canvas").bounding_box()
    # The canvas as it stood before each stroke, read while it was drawn.
    before = []
    for k in range(5):
        before.append(pg.evaluate(PIX))
        stroke(pg, box, k)
    after5 = pg.evaluate(PIX)
    pg.evaluate(COUNT)
    u1, n1 = undo(pg)
    u2, n2 = undo(pg)
    r1, m1 = undo(pg, "#redoBtn")
    check("Undo puts back every pixel from before the last stroke, and paints nothing again",
          u1 == before[4] and n1 == 0, f"pixels match {u1 == before[4]} ({u1[1]}x{u1[2]}); repaints {n1}")
    check("...and so does a second Undo, for the stroke before",
          u2 == before[3] and n2 == 0, f"pixels match {u2 == before[3]}; repaints {n2}")
    check("...and Redo puts that stroke back the same way",
          r1 == before[4] and m1 == 0, f"pixels match {r1 == before[4]}; repaints {m1}")
    # Two Undos more: the first is to a drawing whose copy is still kept (the
    # one Redo just left), the second is past what three copies reach.
    undo(pg)
    u4, n4 = undo(pg)
    check("past what the copies reach, Undo paints the drawing as before, once",
          n4 == 1 and u4[1:] == before[2][1:], f"repaints {n4}; size {u4[1:]}")
    kept = pg.evaluate("() => [_padKept.length, new Set(_padKept.map(k => k.c)).size]")
    check("the copies are three canvases, reused, after five strokes",
          kept[0] == 3 and kept[1] == 3, f"kept {kept[0]}, distinct canvases {kept[1]}")
    check("no page errors through Undo and Redo", not errs, "; ".join(errs[:2]))
    pg.close()

    print("\nUNDO — never a copy of another drawing with as many points")
    # An edit that keeps the number of points: the select tool's move (and the
    # recolour) push the drawing as it was, then put NEW point objects where
    # the old ones were (editor_draw.js). Done here through the same calls.
    pg = b.new_page(viewport={"width": 1280, "height": 900})
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    browsing.goto(pg, BASE, "/")
    pg.evaluate("() => window.SkriblHints && window.SkriblHints.hide && window.SkriblHints.hide()")
    box = pg.locator("#canvas").bounding_box()
    for k in range(3):
        stroke(pg, box, k)
    unmoved = pg.evaluate(PIX)
    pg.evaluate("""() => { undoStack.push(makeHistoryState()); undoBtn.disabled = false; redoStack = [];
      strokes = strokes.map((pt, i) => i < 20 ? Object.assign({}, pt, { x: pt.x + 60 }) : pt);
      clearAndRestore(() => paintStrokesStatic(strokes)); }""")
    pg.wait_for_timeout(250)
    moved = pg.evaluate(PIX)
    pg.evaluate(COUNT)
    ub, nb = undo(pg)
    rb, mb = undo(pg, "#redoBtn")
    check("the edit moved ink (the case is real)", moved != unmoved, "")
    check("Undo of the edit puts back the drawing from before it, from its copy",
          ub == unmoved and nb == 0, f"pixels match {ub == unmoved}; repaints {nb}")
    check("...and Redo, to the edited drawing (as many points, other ones, and no copy of it), paints it rather than lay the old copy on it",
          mb == 1 and rb == moved, f"repaints {mb}; pixels match the edit {rb == moved}, match the old copy {rb == unmoved}")
    check("no page errors through the edit", not errs, "; ".join(errs[:2]))
    # The base and the stroke layers, asked of padUndoRestore directly: the
    # drawing just laid has its copy (the control), and the same points on
    # another base (a new take, a cleared or restored drawing re-base it,
    # app.js), or with the stroke layers switched off, do not.
    stroke(pg, box, 3)
    asked = pg.evaluate("""() => { const st = makeHistoryState();
      const own = padUndoRestore(st);
      const other = padUndoRestore(Object.assign({}, st, { base: 'data:image/png;base64,AAAA' }));
      window.SKRIBL_STROKE_LAYERS = false; const unlayered = padUndoRestore(st); delete window.SKRIBL_STROKE_LAYERS;
      return { own, other, unlayered }; }""")
    check("a copy is put back for its own drawing, and not on another base or with the stroke layers switched off",
          asked == {"own": True, "other": False, "unlayered": False}, str(asked))
    pg.close()

    print("\nUNDO — never a copy of another size")
    pg = b.new_page(viewport={"width": 900, "height": 820})
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    browsing.goto(pg, BASE, "/")
    pg.evaluate("() => window.SkriblHints && window.SkriblHints.hide && window.SkriblHints.hide()")
    box = pg.locator("#canvas").bounding_box()
    for k in range(3):
        stroke(pg, box, k)
    w0 = pg.evaluate("() => document.getElementById('canvas').width")
    # A wider window: the canvas is made again at its new size once the page
    # is still (app.js growCanvasWhenStill).
    pg.set_viewport_size({"width": 1700, "height": 1000})
    pg.wait_for_timeout(1500)
    w1 = pg.evaluate("() => document.getElementById('canvas').width")
    pg.evaluate(COUNT)
    ug, ng = undo(pg)
    check("the window grew and the canvas with it (the case is real)", w1 > w0, f"{w0} -> {w1}")
    check("...and Undo then paints the drawing at the new size, never the old size's copy",
          ng == 1 and ug[1] == w1, f"repaints {ng}; canvas {ug[1]} wide")
    check("no page errors when the canvas grows", not errs, "; ".join(errs[:2]))
    pg.close()
    b.close()

bad = [r for r in results if not r[0]]
print(f"\n{'=' * 62}\n{len(results) - len(bad)}/{len(results)} passed"
      + ("" if not bad else "  FAILURES: " + ", ".join(r[1] for r in bad)))
sys.exit(1 if bad else 0)
