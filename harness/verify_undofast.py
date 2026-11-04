"""Undo without painting the whole drawing again, on the Pad and on Flip (polish
list item 2).

THE COST (Phase 1, measured). A history state is the stroke list and its base,
never pixels: a full canvas copy per stroke once pinned half a gigabyte
(makeHistoryState, app.js). So every Undo painted the whole drawing again, and
on a two-hour piece (145,200 points) that was 1.6 to 1.9 s at this box's own
pace, every press. Now each stroke, as it is laid, is copied into one of three
canvases kept for it (padUndoKeep, editor_draw.js), and Undo and Redo put a
drawing back from its copy when its points, base, size and stroke layers are
the ones the copy was taken of (padUndoRestore). Anything else repaints as
before.

FLIP (flip.js, UNDO WITHOUT PAINTING THE PAGE AGAIN). An Undo painted the page,
its thumbnail and the onion skin's page under it: 160 to 230 ms on a page of
20,000 points at this box's pace, 720 to 980 with the CPU 4x slower. A busy
page (from KEEP_MIN_POINTS) is copied, three copies at most, whenever the
frame layer has just been painted with it at rest; an Undo or Redo back to
ink a copy holds, known by content (_inkSig) because Flip's tools edit points
where they lie, lays the copy. The tile keeps a busy page's last three
pictures, and the onion's ghost of a busy page stays painted while that page
is unchanged.

WHAT IS ASKED, AND HOW IT IS READ
  * Undo, twice, and Redo, put back exactly the canvas from before: every pixel
    of the bitmap, read with getImageData and compared with what the canvas
    held at that moment while it was being drawn. And none of them paints the
    drawing again: paintStrokesStatic (Flip: paintStatic) is counted.
  * Further back than the copies reach, Undo paints as it did, once.
  * A copy is never put back on a canvas that has changed size since: the
    window grows, the canvas is made again at the new size (app.js
    growCanvasNow), and Undo paints rather than lay the old size's pixels on it.
  * The copies are three canvases, reused, however many strokes are laid.
  * They are for a busy drawing, from 4,000 points (PAD_KEEP_MIN_POINTS, as
    Flip's KEEP_MIN_POINTS), so the strokes above are laid over one of 4,200
    points opened through the Pad's own file input. A light drawing keeps no
    copy at all (three were 54 MB on a phone), and a stroke laid on one drops
    the copies a busier drawing left.
  * Flip: the page's tile shows the picture it had, the pad shows what a full
    repaint shows (render() is run after, and nothing moves), and each copy
    that matches the page holds exactly the layer a repaint paints. Over a busy
    page in the onion skin, nothing is painted again at all. A light page
    keeps nothing; an edit that keeps the count is told apart by content; a
    copy made with the stroke layers on is not laid with them off; a new
    canvas size, or layers grown with the window, drop every copy; the frame
    layer is never taken mid-stroke, mid-smudge or mid-erase, nor after a
    thumbnail has been painted through it.
"""
import json
import os
import sys
import tempfile

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
# paintStrokesStatic's calls, counted from here on, and the points they were
# handed (window.__painted).
COUNT = """() => { window.__paints = 0; window.__painted = 0; const f = window.paintStrokesStatic;
  if (!f.__counted) { window.paintStrokesStatic = function (a) { window.__paints++;
      window.__painted += (a && a.length) || 0; return f.apply(this, arguments); };
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
    pg.evaluate("(s) => { window.__paints = 0; window.__painted = 0; document.querySelector(s).click(); }", which)
    pg.wait_for_timeout(250)
    return pg.evaluate(PIX), pg.evaluate("() => window.__paints")


# A busy drawing, 4,200 points in 70 lines low on the right, away from where
# stroke() draws; opened through the Pad's own file input, and Keep drawing
# pressed, because an opened drawing is a finished take until then.
BUSY_PTS = []
for _g in range(70):
    for _i in range(60):
        BUSY_PTS.append({"x": 430 + _i * 5, "y": 300 + _g * 4 + (_i % 5), "color": "#1d1a2b",
                         "size": 3, "t": len(BUSY_PTS) * 16})
_fd, BUSY_FILE = tempfile.mkstemp(suffix=".skribl")
os.close(_fd)
with open(BUSY_FILE, "w") as _f:
    json.dump({"version": 2, "schemaVersion": 2, "playbackMode": "replay", "title": "Busy",
               "frames": [{"strokes": BUSY_PTS, "strokeGroups": [60] * 70}],
               "canvasSize": {"cssWidth": 816, "cssHeight": 612}}, _f)


def busy(pg):
    pg.set_input_files("#draftInput", BUSY_FILE)
    pg.wait_for_function(f"() => typeof strokes !== 'undefined' && strokes.length >= {len(BUSY_PTS)}",
                         timeout=20000)
    pg.wait_for_timeout(300)
    pg.click("#addTakePill")
    pg.wait_for_timeout(250)


with sync_playwright() as p:
    b = p.chromium.launch()

    print("\nUNDO — a drawing the canvas held a moment ago comes back from its copy")
    pg = b.new_page(viewport={"width": 1280, "height": 900})
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    browsing.goto(pg, BASE, "/")
    pg.evaluate("() => window.SkriblHints && window.SkriblHints.hide && window.SkriblHints.hide()")
    busy(pg)
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
    p4 = pg.evaluate("() => window.__painted")
    check("past what the copies reach, Undo lays a floor and paints only the strokes above it: every pixel from before",
          n4 == 1 and 0 < p4 < len(BUSY_PTS) and u4 == before[2],
          f"repaints {n4}, {p4} points painted of {len(BUSY_PTS)}+ in the drawing; pixels match {u4 == before[2]}")
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
    busy(pg)
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
    busy(pg)
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
    grown = pg.evaluate("() => [window.__painted, strokes.length, _padFloors.map(f => f.c.width)]")
    check("...and Undo then paints the drawing at the new size, never the old size's copy or floor (all of it, a floor of the new size taken on the way)",
          ng >= 1 and ug[1] == w1 and grown[0] == grown[1] and grown[2] == [w1],
          f"repaints {ng}, {grown[0]} points of {grown[1]}; canvas {ug[1]} wide; floors {grown[2]}")
    # The floor that repaint took is at the deepest state left (the opened
    # drawing), not at the drawing it painted: so the next Undo, a stroke
    # further back, lays it and paints only what is above it.
    ug2, ng2 = undo(pg)
    again = pg.evaluate("() => [window.__painted, strokes.length]")
    check("...and the next Undo, from the floor that repaint took, paints only the stroke above it",
          ng2 == 1 and 0 < again[0] < len(BUSY_PTS), f"repaints {ng2}, {again[0]} points of {again[1]}")
    check("no page errors when the canvas grows", not errs, "; ".join(errs[:2]))
    pg.close()

    print("\nUNDO — a light drawing keeps no copies (phone)")
    # A copy is the whole canvas: 18 MB on a phone, so three were 54 MB for a
    # doodle, and making them held each of the first three strokes' ends. On
    # a blank Pad, five strokes keep nothing and Undo paints as it always did;
    # over a busy drawing they keep their three, and once the drawing is
    # cleared the next stroke drops them, canvases and all.
    pg = b.new_page(viewport={"width": 402, "height": 874}, device_scale_factor=3, is_mobile=True, has_touch=True)
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    browsing.goto(pg, BASE, "/")
    pg.evaluate("() => window.SkriblHints && window.SkriblHints.hide && window.SkriblHints.hide()")
    box = pg.locator("#canvas").bounding_box()
    light = []
    for k in range(5):
        light.append(pg.evaluate(PIX))
        stroke(pg, box, k)
    kept = pg.evaluate("() => [strokes.length, _padKept.length, _padFloors.length]")
    pg.evaluate(COUNT)
    ul, nl = undo(pg)
    check("five strokes on a blank Pad keep no copy of the canvas, and no floor",
          kept[1] == 0 and kept[2] == 0, f"{kept[0]} points; copies {kept[1]}, floors {kept[2]}")
    check("...and Undo paints the drawing from before the last stroke, as it always did",
          nl == 1 and ul == light[4], f"repaints {nl}; pixels match {ul == light[4]}")
    check("no page errors through a light drawing", not errs, "; ".join(errs[:2]))
    pg.close()
    pg = b.new_page(viewport={"width": 402, "height": 874}, device_scale_factor=3, is_mobile=True, has_touch=True)
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    browsing.goto(pg, BASE, "/")
    pg.evaluate("() => window.SkriblHints && window.SkriblHints.hide && window.SkriblHints.hide()")
    busy(pg)
    box = pg.locator("#canvas").bounding_box()
    for k in range(4):
        stroke(pg, box, k)
    heavy = pg.evaluate("() => [strokes.length, _padKept.length, _padKept.map(k => k.c.width * k.c.height),"
                        " _padFloors.length, _padFloors.map(f => f.c.width * f.c.height)]")
    pg.evaluate("() => { window.__keptCv = _padKept.map(k => k.c); window.__floorCv = _padFloors.map(f => f.c); clearCanvas(); }")
    stroke(pg, box, 1)
    after = pg.evaluate("() => [strokes.length, _padKept.length, window.__keptCv.map(c => c.width * c.height),"
                        " _padFloors.length, window.__floorCv.map(c => c.width * c.height)]")
    check("over a busy drawing the strokes keep their three copies and a floor (the case is real)",
          heavy[1] == 3 and all(a > 0 for a in heavy[2]) and heavy[3] == 1 and all(a > 0 for a in heavy[4]),
          f"{heavy[0]} points; copies {heavy[1]}, pixels {heavy[2]}; floors {heavy[3]}, pixels {heavy[4]}")
    check("...and the drawing cleared, the next stroke drops them and lets their canvases go, the floor's too",
          after[1] == 0 and all(a == 0 for a in after[2]) and after[3] == 0 and all(a == 0 for a in after[4]),
          f"{after[0]} points; copies {after[1]}, old canvases' pixels {after[2]}; floors {after[3]}, old floors' pixels {after[4]}")
    check("no page errors through a busy drawing cleared", not errs, "; ".join(errs[:2]))
    pg.close()

    print("\nUNDO — a floor under the history: thirty Undos and back, after a hundred strokes")
    # Undo reaches thirty states down. A floor is kept at or under the deepest
    # (editor_draw.js, A FLOOR UNDER UNDO) and, once the history is full, a
    # NEXT above it, which becomes the floor when the deepest state reaches it;
    # an Undo or Redo the three copies do not hold lays the highest of them and
    # paints only the strokes above it. After a hundred strokes the deepest
    # state has moved seventy up from where the drawing opened: every press
    # must put back every pixel as it was drawn and paint fewer than sixty
    # strokes (twenty-nine of lag at most, thirty of history), never the
    # drawing. Painted from the opening's floor alone it would be seventy and
    # more; from the base, the whole drawing.
    pg = b.new_page(viewport={"width": 1280, "height": 900})
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    browsing.goto(pg, BASE, "/")
    pg.evaluate("() => window.SkriblHints && window.SkriblHints.hide && window.SkriblHints.hide()")
    busy(pg)
    box = pg.locator("#canvas").bounding_box()

    def quick(k):
        """A short stroke through real pointer events, placed by k."""
        x0, y0 = box["x"] + 40 + (k % 9) * 32, box["y"] + 40 + (k % 11) * 22
        pg.mouse.move(x0, y0)
        pg.mouse.down()
        for i in range(1, 7):
            pg.mouse.move(x0 + i * 9, y0 + (i % 3) * 5)
            pg.wait_for_timeout(8)
        pg.mouse.up()
        pg.wait_for_timeout(40)

    # STROKES a press paints: the stroke starts in what it hands the painter.
    STROKES = """() => { window.__ps = 0; const f = window.paintStrokesStatic;
      if (!f.__strokes) { window.paintStrokesStatic = function (a) {
          for (const q of a || []) if (q.start) window.__ps++; return f.apply(this, arguments); };
        window.paintStrokesStatic.__strokes = true; } }"""
    PRESS = "(s) => { window.__ps = 0; document.querySelector(s).click(); return window.__ps; }"
    N = 100
    seen = {}            # the canvas after k strokes, for the last forty-one
    for k in range(N):
        if k >= N - 41:
            seen[k] = pg.evaluate(PIX)
        quick(k)
    seen[N] = pg.evaluate(PIX)
    state = pg.evaluate("() => ({ undo: undoStack.length, groups: strokeGroups.length, floors: _padFloors.length })")
    pg.evaluate(STROKES)
    wrong, painted = [], []
    for j in range(30):                  # back to the canvas after 99, 98, ... 70 strokes
        ps = pg.evaluate(PRESS, "#undoBtn")
        pg.wait_for_timeout(30)
        painted.append(ps)
        if pg.evaluate(PIX) != seen[N - 1 - j]:
            wrong.append(N - 1 - j)
    check("a hundred strokes over the opened drawing: the history is full and two floors are kept (the case is real)",
          state["undo"] == 30 and state["floors"] == 2, str(state))
    check("thirty Undos: each puts back every pixel of the canvas as it was drawn",
          not wrong, f"wrong after {wrong[:6]} strokes" if wrong else "30 of 30")
    check("...and none paints sixty strokes or more: only those above a floor, never the drawing",
          max(painted) < 60, f"strokes painted per press, most {max(painted)}: {painted}")
    wrong, painted = [], []
    for j in range(10):                  # forward to the canvas after 71 ... 80 strokes
        ps = pg.evaluate(PRESS, "#redoBtn")
        pg.wait_for_timeout(30)
        painted.append(ps)
        if pg.evaluate(PIX) != seen[N - 29 + j]:
            wrong.append(N - 29 + j)
    check("ten Redos back up: every pixel as it was drawn, and fewer than sixty strokes painted",
          not wrong and max(painted) < 60, f"wrong {wrong[:6]}; strokes painted per press {painted}")
    check("no page errors through thirty Undos and back", not errs, "; ".join(errs[:2]))
    pg.close()

    print("\nUNDO — a drawing back from a reload takes its floor in its first paint")
    # A draft comes back with its history (editor_draft.js
    # rebuildHistoryForRestore): thirty states and no copy of any of them, so
    # the first Undo after a reload painted the whole drawing (7 s on the
    # two-hour piece with the CPU 4x slower). Its paint now stops at the
    # deepest state, keeps the canvas there as the floor, and paints the last
    # strokes on it. 9,000 points in 150 lines, opened, and twelve strokes on
    # top.
    BIG_PTS = []
    for _g in range(150):
        for _i in range(60):
            BIG_PTS.append({"x": 300 + _i * 7, "y": 120 + _g * 3 + (_i % 5), "color": "#1d1a2b",
                            "size": 2, "t": len(BIG_PTS) * 16, "start": _i == 0})
    _fd, big_file = tempfile.mkstemp(suffix=".skribl")
    os.close(_fd)
    with open(big_file, "w") as _f:
        json.dump({"version": 2, "schemaVersion": 2, "playbackMode": "replay", "title": "Big",
                   "frames": [{"strokes": BIG_PTS, "strokeGroups": [60] * 150}],
                   "canvasSize": {"cssWidth": 816, "cssHeight": 612}}, _f)
    pg = b.new_page(viewport={"width": 1280, "height": 900})
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    browsing.goto(pg, BASE, "/")
    pg.evaluate("() => window.SkriblHints && window.SkriblHints.hide && window.SkriblHints.hide()")
    pg.set_input_files("#draftInput", big_file)
    pg.wait_for_function(f"() => typeof strokes !== 'undefined' && strokes.length >= {len(BIG_PTS)}", timeout=20000)
    pg.wait_for_timeout(300)
    pg.click("#addTakePill")
    pg.wait_for_timeout(250)
    box = pg.locator("#canvas").bounding_box()
    for k in range(12):
        quick(k)
    total = pg.evaluate("() => strokes.length")
    pg.wait_for_function(f"() => {{ const s = readAutosave(); return !!(s && s.strokes && s.strokes.length === {total}); }}",
                         timeout=15000)
    pg.reload(wait_until="load")
    pg.wait_for_function(f"() => typeof strokes !== 'undefined' && strokes.length === {total}", timeout=20000)
    pg.wait_for_timeout(600)
    back = pg.evaluate("() => ({ undo: undoStack.length, deepest: undoStack[0] && undoStack[0].strokes.length,"
                       " floors: _padFloors.map(f => f.n), copies: _padKept.length })")
    pg.evaluate(STROKES)
    # The drawing as it came back is what a reload repaints: its points are
    # written to 0.01 px (lib/pointwrite.js), so its edges are not the
    # canvas's before the reload. Each Undo is read against the whole repaint
    # of the same state on this page, the way every Undo painted before.
    WHOLE = """() => { restoreHistoryState({ image: null, base: preRecordSnapshot, strokes: strokes.slice() });
      const c = document.getElementById('canvas'); const d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data;
      let h = 2166136261 >>> 0; for (let i = 0; i < d.length; i++) h = Math.imul(h ^ d[i], 16777619) >>> 0;
      return [h, c.width, c.height]; }"""
    wrong, painted = [], []
    for j in range(3):                   # back to the drawing after 11, 10, 9 strokes
        ps = pg.evaluate(PRESS, "#undoBtn")
        pg.wait_for_timeout(30)
        painted.append(ps)
        if pg.evaluate(PIX) != pg.evaluate(WHOLE):
            wrong.append(11 - j)
    os.unlink(big_file)
    check("back from a reload: thirty states, no copy, and one floor, at the deepest of them",
          back["undo"] == 30 and back["copies"] == 0 and back["floors"] == [back["deepest"]], str(back))
    check("...and the first Undos after it paint only the strokes above it, never the drawing",
          max(painted) < 31, f"strokes painted per press {painted}")
    check("...putting back every pixel the whole repaint of each paints",
          not wrong, f"wrong after {wrong} strokes" if wrong else "3 of 3")
    check("no page errors through a reload and its Undos", not errs, "; ".join(errs[:2]))
    pg.close()

    print("\nUNDO — strokes above a floor are painted as the whole repaint paints them")
    # The repaint lays see-through strokes in a layer of their own only while
    # the whole drawing has 24 or fewer (lib/strokelayers.js overBudget). The
    # strokes painted above a floor are painted by the whole drawing's count,
    # not by their own few, so an Undo from a floor shows what the whole repaint
    # shows, see-through ink included: a floor is a shortcut, never another
    # picture. Two drawings, opened (the opening paints them as the repaint
    # does), each with six see-through strokes drawn on it: one past the budget
    # (40 see-through lines), where they are laid without a layer, and one under
    # it (10), where they are laid in theirs. Drawn with the pencil, whose width
    # follows speed: a see-through stroke of one width is one path with the
    # layers or without (lib/strokelayers.js uniformRun), so it could not tell.
    for n_see, label in ((40, "past the budget"), (10, "under the budget")):
        SEE_PTS, SEE_GROUPS = [], []
        for _g in range(80):
            _col = "rgba(124, 92, 255, 0.45)" if _g < n_see else "#1d1a2b"
            for _i in range(60):
                SEE_PTS.append({"x": 300 + _i * 7, "y": 120 + _g * 5 + (_i % 4), "color": _col,
                                "size": 4 + (_i % 5), "t": len(SEE_PTS) * 16, "start": _i == 0})
            SEE_GROUPS.append(60)
        _fd, see_file = tempfile.mkstemp(suffix=".skribl")
        os.close(_fd)
        with open(see_file, "w") as _f:
            json.dump({"version": 2, "schemaVersion": 2, "playbackMode": "replay", "title": "See",
                       "frames": [{"strokes": SEE_PTS, "strokeGroups": SEE_GROUPS}],
                       "canvasSize": {"cssWidth": 816, "cssHeight": 612}}, _f)
        pg = b.new_page(viewport={"width": 1280, "height": 900})
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        browsing.goto(pg, BASE, "/")
        pg.evaluate("() => window.SkriblHints && window.SkriblHints.hide && window.SkriblHints.hide()")
        pg.set_input_files("#draftInput", see_file)
        pg.wait_for_function(f"() => typeof strokes !== 'undefined' && strokes.length >= {len(SEE_PTS)}", timeout=20000)
        pg.wait_for_timeout(300)
        pg.click("#addTakePill")
        pg.wait_for_timeout(250)
        box = pg.locator("#canvas").bounding_box()
        pg.evaluate("() => { strokeOpacity = 0.45; SkriblBrush.setBrush('pencil'); }")
        for k in range(6):
            quick(k)
        state = pg.evaluate("""() => { const n = strokeGroups.slice(-6), out = [];
          let a = strokes.length - n.reduce((x, y) => x + y, 0);
          for (const g of n) { out.push(strokes.slice(a, a + g)); a += g; }
          return [SkriblStrokeLayers.overBudget(strokes, parseStrokeAlpha, anyStrokeAlpha),
                  out.every(r => r.every(p => anyStrokeAlpha(p.color) < 1)),
                  out.every(r => new Set(r.map(p => p.size)).size > 1)]; }""")
        pg.evaluate(STROKES)
        wrong, painted = [], []
        for j in range(6):
            ps = pg.evaluate(PRESS, "#undoBtn")
            pg.wait_for_timeout(30)
            painted.append(ps)
            if j >= 2 and pg.evaluate(PIX) != pg.evaluate(WHOLE):
                wrong.append(j + 1)
        os.unlink(see_file)
        check(f"a drawing {label}, six see-through pencil strokes of varying width drawn on it (the case is real)",
              state == [n_see > 24, True, True],
              f"past the budget {state[0]}; the new strokes see-through {state[1]}, each of varying width {state[2]}")
        check(f"...and each Undo past the copies, from the floor, shows every pixel the whole repaint shows ({label})",
              not wrong and max(painted[2:]) < 6, f"Undos that differ {wrong}; strokes painted per press {painted}")
        check(f"no page errors through see-through Undos ({label})", not errs, "; ".join(errs[:2]))
        pg.close()

    print("\nUNDO — a drawing just past the layering budget, its see-through ink on both sides of the floor")
    # Twenty-four see-through lines, the budget exactly, in an opened drawing,
    # then two see-through strokes on top: the drawing is past the budget and
    # its part under the deepest state is not. The repaint in two parts lays
    # that part as the whole would be laid (layers off), and a draft's paint
    # does not split where its parts would be laid differently: each picture is
    # the one-paint picture, read against restoreHistoryState of the same state.
    EDGE_PTS, EDGE_GROUPS = [], []
    for _g in range(120):
        _col = "rgba(124, 92, 255, 0.45)" if _g < 24 else "#1d1a2b"
        for _i in range(60):
            EDGE_PTS.append({"x": 300 + _i * 7, "y": 60 + _g * 4 + (_i % 4), "color": _col,
                             "size": 4 + (_i % 5), "t": len(EDGE_PTS) * 16, "start": _i == 0})
        EDGE_GROUPS.append(60)
    _fd, edge_file = tempfile.mkstemp(suffix=".skribl")
    os.close(_fd)
    with open(edge_file, "w") as _f:
        json.dump({"version": 2, "schemaVersion": 2, "playbackMode": "replay", "title": "Edge",
                   "frames": [{"strokes": EDGE_PTS, "strokeGroups": EDGE_GROUPS}],
                   "canvasSize": {"cssWidth": 816, "cssHeight": 612}}, _f)
    pg = b.new_page(viewport={"width": 900, "height": 820})
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    browsing.goto(pg, BASE, "/")
    pg.evaluate("() => window.SkriblHints && window.SkriblHints.hide && window.SkriblHints.hide()")
    pg.set_input_files("#draftInput", edge_file)
    pg.wait_for_function(f"() => typeof strokes !== 'undefined' && strokes.length >= {len(EDGE_PTS)}", timeout=20000)
    pg.wait_for_timeout(300)
    pg.click("#addTakePill")
    pg.wait_for_timeout(250)
    box = pg.locator("#canvas").bounding_box()
    pg.evaluate("() => { strokeOpacity = 0.45; }")
    for k in range(3):
        quick(k)
    w0 = pg.evaluate("() => document.getElementById('canvas').width")
    pg.set_viewport_size({"width": 1700, "height": 1000})
    pg.wait_for_timeout(1500)
    pg.evaluate(STROKES)
    pg.evaluate(PRESS, "#undoBtn")       # no copy or floor of the new size: the repaint, in two parts
    pg.wait_for_timeout(30)
    budget = pg.evaluate("() => [document.getElementById('canvas').width, SkriblStrokeLayers.overBudget(strokes, parseStrokeAlpha, anyStrokeAlpha),"
                         " SkriblStrokeLayers.overBudget(undoStack[0].strokes, parseStrokeAlpha, anyStrokeAlpha)]")
    two = pg.evaluate(PIX) == pg.evaluate(WHOLE)
    total = pg.evaluate("() => strokes.length")
    pg.wait_for_function(f"() => {{ const s = readAutosave(); return !!(s && s.strokes && s.strokes.length === {total}); }}",
                         timeout=15000)
    pg.reload(wait_until="load")
    pg.wait_for_function(f"() => typeof strokes !== 'undefined' && strokes.length === {total}", timeout=20000)
    pg.wait_for_timeout(600)
    back = pg.evaluate(PIX) == pg.evaluate(WHOLE)
    os.unlink(edge_file)
    check("the canvas grew; the drawing is past the budget and its part under the deepest state is not (the case is real)",
          budget[0] > w0 and budget[1] is True and budget[2] is False, f"{w0} -> {budget[0]}; past the budget: drawing {budget[1]}, under the deepest {budget[2]}")
    check("...and the repaint in two parts, a floor between, shows every pixel one paint shows",
          two, f"same as one paint {two}")
    check("...and back from a reload, the draft's paint shows every pixel one paint shows",
          back, f"same as one paint {back}")
    check("no page errors through a drawing just past the budget", not errs, "; ".join(errs[:2]))
    pg.close()

    print("\nUNDO — no floor is taken with the select tool's outline on the canvas")
    # A press with the select tool pushes a state as a stroke's start does,
    # but the selection's dashed outline is painted on the canvas itself
    # (editor_draw.js selOutline): a floor taken then would carry the outline
    # back into the drawing on an Undo. Asked of padFloorKeep directly, with
    # no floor kept beforehand, so that the push is the one that would take it:
    # under a selection nothing is kept; with the pen and the outline cleared,
    # the same push keeps one (the control).
    pg = b.new_page(viewport={"width": 1280, "height": 900})
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    browsing.goto(pg, BASE, "/")
    pg.evaluate("() => window.SkriblHints && window.SkriblHints.hide && window.SkriblHints.hide()")
    busy(pg)
    box = pg.locator("#canvas").bounding_box()
    pg.evaluate("() => setTool('select')")
    pg.wait_for_timeout(200)
    lg = pg.evaluate("() => getCanvasLogicalSize()")
    sx, sy = box["width"] / lg["width"], box["height"] / lg["height"]
    pg.mouse.move(box["x"] + 420 * sx, box["y"] + 290 * sy)
    pg.mouse.down()
    pg.mouse.move(box["x"] + 600 * sx, box["y"] + 400 * sy, steps=8)
    pg.mouse.up()
    pg.wait_for_timeout(300)
    KEEP = """() => { for (const f of _padFloors) f.c.width = f.c.height = 0; _padFloors.length = 0;
      undoStack.push(makeHistoryState()); padFloorKeep(); return [selGroups.length, _padFloors.length]; }"""
    under = pg.evaluate(KEEP)
    pg.evaluate("() => setTool('pen')")
    pg.wait_for_timeout(300)
    clear = pg.evaluate(KEEP)
    check("a selection is on the canvas, its outline with it (the case is real)", under[0] > 0, f"{under[0]} lines selected")
    check("...and a push then keeps no floor; with the pen, the outline gone, the same push keeps one",
          under[1] == 0 and clear == [0, 1], f"under the selection {under[1]} floors; with the pen {clear[1]}")
    check("no page errors around the select tool", not errs, "; ".join(errs[:2]))
    pg.close()

    # ================================================================ FLIP
    # The pad's bitmap, folded into one number, and the current page's tile.
    FPIX = """() => { const c = document.getElementById('pad');
      const d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data; let h = 2166136261 >>> 0;
      for (let i = 0; i < d.length; i++) h = Math.imul(h ^ d[i], 16777619) >>> 0;
      return [h, c.width, c.height]; }"""
    FTILE = """() => { const c = _tiles()[idx].querySelector('canvas');
      const d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data; let h = 2166136261 >>> 0;
      for (let i = 0; i < d.length; i++) h = Math.imul(h ^ d[i], 16777619) >>> 0;
      return h; }"""
    # paintStatic's calls, counted from here on; and a busy page, made in the
    # document (22-point strokes, two inks), as the bench made it.
    FSETUP = """() => { window.__fp = 0; window.__fn = 0; const f = window.paintStatic;
      if (!f.__counted) { window.paintStatic = function (c, a) { window.__fp++;
          window.__fn += (a && a.length) || 0; return f.apply(this, arguments); };
        window.paintStatic.__counted = true; }
      window.__hash = (c) => { const d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data;
        let h = 2166136261 >>> 0; for (let i = 0; i < d.length; i++) h = Math.imul(h ^ d[i], 16777619) >>> 0; return h; };
      window.__dense = (n, seed) => { const pts = [], groups = []; let k = seed || 0;
        while (pts.length < n) { const len = 22, x0 = 20 + (k * 37) % (CW - 120), y0 = 20 + (k * 53) % (CH - 60);
          for (let i = 0; i < len; i++) pts.push({ x: x0 + i * 4, y: y0 + Math.sin(i / 3) * 9,
            color: k % 5 ? '#1f1b2e' : '#7c5cff', size: 2 + (i % 7) * 0.6, t: pts.length * 20, start: i === 0 });
          groups.push(len); k++; }
        return { pts, groups }; };
      window.__busy = (pages, n) => { for (let i = 0; i < pages; i++) { if (i >= frames.length) frames.push(newFrame());
          const d = __dense(n, i * 7); frames[i].strokes = d.pts; frames[i].strokeGroups = d.groups; }
        buildStrip(); go(pages - 1); render(); refreshAllThumbs(); }; }"""
    # One press of Undo or Redo, with the paints it made, counted inside the
    # press itself (an autosave later is not the press).
    FPRESS = "(id) => { window.__fp = 0; window.__fn = 0; document.getElementById(id).click(); return window.__fp; }"
    # What a full repaint shows, after the press: the pad before and after
    # render(), and each copy matching the page against the layer render()
    # has just painted.
    FTRUE = """() => { const pix = (c) => __hash(c); const fast = pix(document.getElementById('pad'));
      const f = frame(), sig = _inkSig(f); render();
      const slow = pix(document.getElementById('pad')), layer = pix(frameCv);
      const own = _flipKept.filter(k => k.f === f && k.sig === sig);
      return { same: fast === slow, copies: own.length, copiesTrue: own.every(k => pix(k.cv) === layer) }; }"""

    def fopen(b, **kw):
        ctx = b.new_context(**kw)
        pg = ctx.new_page()
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        browsing.goto(pg, BASE, "/flip")
        pg.wait_for_timeout(800)
        pg.evaluate("() => { window.SkriblHints && window.SkriblHints.hide();"
                    " try { localStorage.removeItem('skribl_flip_autosave_v1'); } catch (e) {} }")
        pg.evaluate(FSETUP)
        return ctx, pg, errs

    def fstroke(pg, k, lift=True):
        """One stroke on the pad through real pointer events, each a little different."""
        box = pg.locator("#pad").bounding_box()
        x0, y0 = box["x"] + box["width"] * (0.12 + 0.05 * k), box["y"] + box["height"] * (0.2 + 0.11 * k)
        pg.mouse.move(x0, y0)
        pg.mouse.down()
        for i in range(24):
            pg.mouse.move(x0 + i * box["width"] * 0.025, y0 + ((i % 6) - 3) * box["height"] * 0.01)
            pg.wait_for_timeout(10)
        if lift:
            pg.mouse.up()
            pg.wait_for_timeout(200)

    PHONE = dict(viewport={"width": 402, "height": 874}, device_scale_factor=3, is_mobile=True, has_touch=True)
    BUSY = 6000

    print("\nFLIP UNDO — a busy page comes back from its copy (phone)")
    ctx, pg, errs = fopen(b, **PHONE)
    pg.evaluate("(n) => __busy(1, n)", BUSY)
    pg.wait_for_timeout(300)
    thru = pg.evaluate("() => RS === DPR")
    before, tiles = [], []
    for k in range(5):
        before.append(pg.evaluate(FPIX))
        tiles.append(pg.evaluate(FTILE))
        fstroke(pg, k)
    n1 = pg.evaluate(FPRESS, "undo"); u1, t1 = pg.evaluate(FPIX), pg.evaluate(FTILE); v1 = pg.evaluate(FTRUE)
    n2 = pg.evaluate(FPRESS, "undo"); u2, t2 = pg.evaluate(FPIX), pg.evaluate(FTILE); v2 = pg.evaluate(FTRUE)
    m1 = pg.evaluate(FPRESS, "redo"); r1, s1 = pg.evaluate(FPIX), pg.evaluate(FTILE); w1 = pg.evaluate(FTRUE)
    check("Flip: the layers are at the screen's own ratio here, so a tile is painted through the frame layer (the case is real)",
          thru, "RS is not DPR: the thumbnails go through a layer of their own")
    check("Flip: Undo on a busy page puts back every pixel of the pad from before the last stroke, and paints no ink again",
          u1 == before[4] and n1 == 0, f"pixels match {u1 == before[4]} ({u1[1]}x{u1[2]}); paints {n1}")
    check("...and the page's tile shows the very picture it had then",
          t1 == tiles[4], "the tile differs from the one before the stroke")
    check("...and so does a second Undo, for the stroke before",
          u2 == before[3] and n2 == 0 and t2 == tiles[3], f"pixels {u2 == before[3]}; paints {n2}; tile {t2 == tiles[3]}")
    check("...and Redo puts that stroke back the same way",
          r1 == before[4] and m1 == 0 and s1 == tiles[4], f"pixels {r1 == before[4]}; paints {m1}; tile {s1 == tiles[4]}")
    check("...and each shows what a full repaint shows, from a copy that holds exactly the painted layer",
          all(v["same"] and v["copies"] == 1 and v["copiesTrue"] for v in (v1, v2, w1)), f"{v1} {v2} {w1}")
    # Two Undos more: the first is to ink whose copy is still kept, the second
    # is past what three copies reach (its tile is still among the three kept).
    pg.evaluate(FPRESS, "undo")
    n4 = pg.evaluate(FPRESS, "undo"); p4 = pg.evaluate("() => window.__fn")
    u4, t4 = pg.evaluate(FPIX), pg.evaluate(FTILE); v4 = pg.evaluate(FTRUE)
    check("past what the copies reach, Undo lays the page's floor and paints only the strokes above it, and keeps the page",
          n4 == 1 and 0 < p4 < BUSY and u4 == before[2] and t4 == tiles[2] and v4["same"] and v4["copies"] == 1 and v4["copiesTrue"],
          f"paints {n4}, {p4} points of {BUSY}+; pixels {u4 == before[2]}; tile {t4 == tiles[2]}; {v4}")
    kept = pg.evaluate("() => [_flipKept.length, new Set(_flipKept.map(k => k.cv)).size, _thumbBack.length]")
    check("the copies are three canvases, reused, after five strokes, and the tile keeps three pictures",
          kept == [3, 3, 3], f"copies {kept[0]}, distinct canvases {kept[1]}, pictures {kept[2]}")
    # A thumbnail painted through the frame layer, of another page, and then
    # a keep that checks its tag against the ink: the layer holds the other
    # page's picture now, and must not be kept as this one.
    pg.evaluate("() => { frames.push(newFrame()); const d = __dense(600, 3); const f = frames[frames.length - 1];"
                " f.strokes = d.pts; f.strokeGroups = d.groups; buildStrip(); _flipKept.length = 0; render(); }")
    tk = pg.evaluate("""() => { const tagged = !!_fcvTag; frames[frames.length - 1].strokes[0].x += 7; refreshThumb(frames.length - 1);
      flipKeep(); const f = frame(), sig = _inkSig(f), own = _flipKept.filter(k => k.f === f && k.sig === sig);
      render(); const layer = __hash(frameCv);
      return { tagged, own: own.length, true: own.every(k => __hash(k.cv) === layer) }; }""")
    check("a thumbnail painted through the frame layer is never kept as the page",
          tk["tagged"] and tk["true"] and tk["own"] == 0, str(tk))
    check("no page errors through Flip's Undo and Redo", not errs, "; ".join(errs[:2]))
    ctx.close()

    print("\nFLIP UNDO — a stroke, a fill and a stamp, each undone and redone from copies")
    # The three things that lay new ink keep the page they leave (endStroke,
    # doFill, doStamp), which is what a Redo straight after their Undo comes
    # back to; and a stroke's start keeps the page under it, which is what the
    # first Undo on a page just opened comes back to.
    ctx, pg, errs = fopen(b, **PHONE)
    pg.evaluate("(n) => __busy(1, n)", BUSY)
    pg.wait_for_timeout(300)
    s0 = pg.evaluate(FPIX)
    fstroke(pg, 0)
    s1 = pg.evaluate(FPIX)
    a1 = pg.evaluate(FPRESS, "undo"); p1 = pg.evaluate(FPIX)
    a2 = pg.evaluate(FPRESS, "redo"); p2 = pg.evaluate(FPIX)
    check("the first Undo on a page just opened comes back from the copy its stroke's start kept",
          p1 == s0 and a1 == 0, f"pixels {p1 == s0}; paints {a1}")
    check("...and Redo straight after it, from the copy the stroke's end kept",
          p2 == s1 and a2 == 0, f"pixels {p2 == s1}; paints {a2}")
    box = pg.locator("#pad").bounding_box()
    pg.evaluate("() => setTool('fill')")
    pg.mouse.click(box["x"] + box["width"] * 0.97, box["y"] + box["height"] * 0.98)
    pg.wait_for_timeout(300)
    filled = pg.evaluate("() => [actionLog.length && actionLog[actionLog.length - 1].type, frame().strokes.length]")
    f1 = pg.evaluate(FPIX)
    a3 = pg.evaluate(FPRESS, "undo"); p3 = pg.evaluate(FPIX)
    a4 = pg.evaluate(FPRESS, "redo"); p4 = pg.evaluate(FPIX)
    check("a fill was laid (the case is real)", filled[0] == "fill", str(filled))
    check("Undo of a fill on a busy page comes back from a copy, every pixel", p3 == s1 and a3 == 0,
          f"pixels {p3 == s1}; paints {a3}")
    check("...and its Redo too, from the copy the fill kept", p4 == f1 and a4 == 0, f"pixels {p4 == f1}; paints {a4}")
    pg.evaluate("""() => { stampShelf = [SkriblStamps.fromRuns(
        [[{x:0,y:0,color:'#7c5cff',size:4},{x:40,y:0,color:'#7c5cff',size:4}],
         [{x:0,y:16,color:'#7c5cff',size:4},{x:40,y:16,color:'#7c5cff',size:4}]])];
      stampArmed = 0; setTool('stamp'); syncStampPop(); }""")
    pg.wait_for_timeout(200)
    pg.mouse.click(box["x"] + box["width"] * 0.5, box["y"] + box["height"] * 0.5)
    pg.wait_for_timeout(300)
    stamped = pg.evaluate("() => actionLog.length && actionLog[actionLog.length - 1].label")
    t1 = pg.evaluate(FPIX)
    a5 = pg.evaluate(FPRESS, "undo"); p5 = pg.evaluate(FPIX)
    a6 = pg.evaluate(FPRESS, "redo"); p6 = pg.evaluate(FPIX)
    check("a stamp was placed (the case is real)", stamped == "Stamp", repr(stamped))
    check("Undo and Redo of a stamp on a busy page come back from copies, every pixel",
          p5 == f1 and a5 == 0 and p6 == t1 and a6 == 0, f"undo: pixels {p5 == f1}, paints {a5}; redo: pixels {p6 == t1}, paints {a6}")
    check("no page errors through the stroke, fill and stamp", not errs, "; ".join(errs[:2]))
    ctx.close()

    print("\nFLIP UNDO — over a busy page in the onion skin, nothing is painted again")
    ctx, pg, errs = fopen(b, **PHONE)
    pg.evaluate("(n) => __busy(2, n)", BUSY)
    pg.wait_for_timeout(300)
    on = pg.evaluate("() => [onion, onionDepth, idx]")
    b0 = pg.evaluate(FPIX)
    fstroke(pg, 0)
    no = pg.evaluate(FPRESS, "undo"); uo = pg.evaluate(FPIX); vo = pg.evaluate(FTRUE)
    check("the onion skin shows page 1 under page 2 (the case is real)", on == [True, 1, 1], str(on))
    check("on page 2, Undo puts back every pixel, the ghost of page 1 included, and paints no ink at all",
          uo == b0 and no == 0 and vo["same"], f"pixels {uo == b0}; paints {no}; {vo}")
    # Two pages back: the farther ghost has a canvas of its own.
    pg.evaluate("(n) => { onionDepth = 2; __busy(3, n); }", BUSY)
    pg.wait_for_timeout(300)
    b3 = pg.evaluate(FPIX)
    fstroke(pg, 1)
    n3 = pg.evaluate(FPRESS, "undo"); u3 = pg.evaluate(FPIX); v3 = pg.evaluate(FTRUE)
    g3 = pg.evaluate("() => _ghosts.length")
    check("...and with the onion two pages deep, the farther ghost is kept too: nothing painted, every pixel back",
          u3 == b3 and n3 == 0 and v3["same"] and g3 == 1, f"pixels {u3 == b3}; paints {n3}; ghosts kept {g3}; {v3}")
    check("no page errors over the onion skin", not errs, "; ".join(errs[:2]))
    ctx.close()

    print("\nFLIP UNDO — what is kept, and what never is")
    ctx, pg, errs = fopen(b, **PHONE)
    for k in range(3):
        fstroke(pg, k)
    pg.evaluate(FPRESS, "undo")
    light = pg.evaluate("() => [frame().strokes.length, _flipKept.length, _ghosts.length, _thumbBack.length]")
    check("a light page keeps nothing: no canvas is spent on a page that repaints in a moment",
          light[0] > 0 and light[1:] == [0, 0, 0], f"{light[0]} points; copies, ghosts, pictures {light[1:]}")
    # An edit in place that keeps the count: a selection moved, as the select
    # tool ends a move (translateSpans, then its Undo entry). The next stroke's
    # Undo comes back to the MOVED ink, which has as many points, the same
    # objects, as the ink before the move.
    pg.evaluate("(n) => __busy(1, n)", BUSY)
    fstroke(pg, 0)
    unmoved = pg.evaluate(FPIX)
    pg.evaluate("""() => { const n = frame().strokes.length; const spans = [[n - 60, n]];
      translateSpans(idx, spans, 40, 30); redoStack.length = 0;
      noteAction({ type: 'selmove', idx, spans, dx: 40, dy: 30 }); render(); refreshThumb(idx); }""")
    moved = pg.evaluate(FPIX)
    fstroke(pg, 2)
    ne = pg.evaluate(FPRESS, "undo"); ue = pg.evaluate(FPIX)
    check("the move changed the ink (the case is real)", moved != unmoved, "")
    check("an edit in place is told apart by content: Undo of the next stroke shows the moved ink, from its own copy",
          ue == moved and ne == 0, f"moved {ue == moved}; the ink before the move {ue == unmoved}; paints {ne}")
    # The stroke layers: the copy was made with them on.
    fstroke(pg, 3)
    nl = pg.evaluate("() => { window.SKRIBL_STROKE_LAYERS = false; window.__fp = 0; window.__fn = 0; document.getElementById('undo').click();"
                     " const n = [window.__fp, window.__fn, frame().strokes.length]; delete window.SKRIBL_STROKE_LAYERS; return n; }")
    check("a copy or a floor made with the stroke layers on is not laid with them off: that Undo paints the whole page",
          nl[0] >= 1 and nl[1] == nl[2], f"paints {nl[0]}, {nl[1]} points of {nl[2]}")
    # A new canvas size.
    fstroke(pg, 4)
    had = pg.evaluate("() => _flipKept.length")
    sz = pg.evaluate("""() => { const w = CW, h = CH; applyCanvasSize(Math.round(w * 0.75), Math.round(h * 0.75));
      return [CW !== w, _flipKept.length, _ghosts.length, _fcvTag ? _fcvTag.w === frameCv.width : true]; }""")
    nz = pg.evaluate(FPRESS, "undo")
    wz = pg.evaluate("() => [document.getElementById('pad').width, layerPx(CW)]")
    check("a new canvas size drops every copy and ghost made at the old one",
          had > 0 and sz[0] and sz[1:3] == [0, 0] and sz[3], f"copies before {had}; after {sz}")
    # Two paints: the page, and its tile, which has no picture at this size.
    check("...and Undo then paints the page at the new size, and its tile", nz == 2 and wz[0] == wz[1],
          f"paints {nz}; pad {wz}")
    # Never mid-stroke, mid-erase or mid-smudge: the frame layer is not the
    # page at rest then. Mid-stroke on the static path, which a stroke takes
    # when the live cache cannot be used (one more see-through stroke would
    # tip the page over the layer budget, or the eraser was switched).
    box = pg.locator("#pad").bounding_box()
    fstroke(pg, 1, lift=False)
    mid = pg.evaluate("() => { const was = !!_fcvTag; _liveCache = null; render(); return [drawing, _fcvTag === null]; }")
    pg.mouse.up(); pg.wait_for_timeout(200)
    pg.evaluate("() => { setTool('eraser'); render(); }")
    era0 = pg.evaluate("() => !!_fcvTag")
    fstroke(pg, 2, lift=False)
    era = pg.evaluate("() => [drawing, erasing, !!(_liveCache && !_liveCache.flat), _fcvTag === null]")
    pg.mouse.up(); pg.wait_for_timeout(200)
    pg.evaluate("() => setTool('smudge')")
    pg.mouse.move(box["x"] + box["width"] * 0.3, box["y"] + box["height"] * 0.3)
    pg.mouse.down()
    for i in range(14):
        pg.mouse.move(box["x"] + box["width"] * (0.3 + i * 0.02), box["y"] + box["height"] * 0.3)
        pg.wait_for_timeout(15)
    smu = pg.evaluate("() => [fieldActive, _fcvTag === null]")
    pg.mouse.up(); pg.wait_for_timeout(200)
    check("the frame layer is never taken mid-stroke", mid == [True, True], str(mid))
    check("...nor while erasing, where the stroke is painted into it", era0 and era == [True, True, True, True],
          f"tagged before {era0}; {era}")
    check("...nor mid-smudge, where its runs are painted at a live strength", smu == [True, True], str(smu))
    check("no page errors through the edits", not errs, "; ".join(errs[:2]))
    ctx.close()

    print("\nFLIP UNDO — layers grown with the window drop the copies")
    ctx, pg, errs = fopen(b, viewport={"width": 1000, "height": 760})
    pg.evaluate("(n) => __busy(1, n)", BUSY)
    fstroke(pg, 0)
    fstroke(pg, 1)
    g0 = pg.evaluate("() => [document.getElementById('pad').width, _flipKept.length]")
    pg.set_viewport_size({"width": 1800, "height": 1100})
    pg.wait_for_timeout(1500)
    g1 = pg.evaluate("() => [document.getElementById('pad').width, _flipKept.length]")
    check("the window grew and the layers with it (the case is real)", g1[0] > g0[0] and g0[1] > 0, f"{g0} -> {g1}")
    check("...and the copies made at the old size are dropped", g1[1] == 0, f"{g1[1]} kept")
    check("no page errors as the layers grow", not errs, "; ".join(errs[:2]))
    ctx.close()

    print("\nFLIP UNDO — a floor under a busy page, the tile from the layer, a stroke's start")
    # Flip's Undo has no cap: it takes a page back stroke by stroke to an empty
    # one. A busy page keeps a FLOOR (the page as it stood at a pen stroke's
    # start) and, 30 strokes on, a NEXT (flip.js, A FLOOR UNDER A BUSY PAGE): an
    # Undo or a Redo past the three copies lays the highest that fits and paints
    # only the strokes above it. The page's tile, painted through the same frame
    # layer, is laid from it when the layer already holds the page
    # (_frameHolds), and a stroke's start no longer paints the page into the
    # layer when the layer holds it already (liveBegin). Every pixel is read
    # against render() (FTRUE) and every tile against one painted afresh with
    # the layer untagged (FTILEREF).
    FTILEREF = """() => { const f = frame(), T = _fcvTag, hit = _thumbCache.get(f); _fcvTag = null; _thumbCache.delete(f);
      const cv = document.createElement('canvas'); drawThumb(cv, f); const h = __hash(cv);
      if (hit) _thumbCache.set(f, hit); else _thumbCache.delete(f); render(); return h; }"""

    def fquick(pg, k, lift=True):
        """A short stroke on the pad through real pointer events, placed by k."""
        box = pg.locator("#pad").bounding_box()
        x0 = box["x"] + box["width"] * (0.1 + 0.07 * (k % 9))
        y0 = box["y"] + box["height"] * (0.12 + 0.06 * (k % 13))
        pg.mouse.move(x0, y0)
        pg.mouse.down()
        for i in range(1, 7):
            pg.mouse.move(x0 + i * box["width"] * 0.02, y0 + (i % 3) * box["height"] * 0.008)
            pg.wait_for_timeout(8)
        if lift:
            pg.mouse.up()
            pg.wait_for_timeout(60)

    ctx, pg, errs = fopen(b, **PHONE)
    pg.evaluate("(n) => __busy(1, n)", BUSY)
    pg.wait_for_timeout(300)
    seen, startpts = {}, []
    for k in range(8):
        seen[k] = pg.evaluate(FPIX)
        pg.evaluate("() => { window.__fn = 0; }")
        fquick(pg, k, lift=False)            # pressed and moving: the start has run
        startpts.append(pg.evaluate("() => window.__fn"))
        pg.mouse.up()
        pg.wait_for_timeout(120)
    seen[8] = pg.evaluate(FPIX)
    check("Flip: each of eight strokes' starts on a busy page paints none of the page again, only the stroke",
          max(startpts) < BUSY, f"points painted while each stroke was down: {startpts}")
    wrong, tilewrong, painted, untrue = [], [], [], []
    for j in range(8):                       # back to the page after 7, 6, ... 0 strokes
        pg.evaluate(FPRESS, "undo")
        painted.append(pg.evaluate("() => window.__fn"))
        if pg.evaluate(FPIX) != seen[7 - j]:
            wrong.append(7 - j)
        if pg.evaluate(FTILE) != pg.evaluate(FTILEREF):
            tilewrong.append(7 - j)
        v = pg.evaluate(FTRUE)
        if not v["same"]:
            untrue.append(7 - j)
    check("Flip: eight Undos on a busy page, every pixel of the pad as it was, each what render() paints",
          not wrong and not untrue, f"pixels wrong after {wrong} strokes; unlike render() after {untrue}")
    check("...painting only strokes above a floor, never the page",
          max(painted) < BUSY, f"points painted per press {painted}")
    check("...and each tile the picture a tile painted afresh shows",
          not tilewrong, f"tiles wrong after {tilewrong} strokes" if tilewrong else "8 of 8")
    wrong, painted = [], []
    for j in range(8):                       # forward to the page after 1 ... 8 strokes
        pg.evaluate(FPRESS, "redo")
        painted.append(pg.evaluate("() => window.__fn"))
        if pg.evaluate(FPIX) != seen[j + 1]:
            wrong.append(j + 1)
    check("Flip: eight Redos back, every pixel as it was, never painting the page",
          not wrong and max(painted) < BUSY, f"wrong after {wrong}; points painted per press {painted}")
    # A tile is laid from the layer only while the layer holds the page as it
    # is: a point moved in place (as Recolor and the select tools do), the
    # tile is painted, not laid from the layer as it was.
    moved = pg.evaluate("""() => { const f = frame(); f.strokes[3] = Object.assign({}, f.strokes[3], { x: f.strokes[3].x + 40 });
      refreshThumb(idx); const el = _tiles()[idx].querySelector('canvas'); const shown = __hash(el); return shown; }""")
    moved_ref = pg.evaluate(FTILEREF)
    check("Flip: a tile is never laid from the layer once the page has changed under it",
          moved == moved_ref, "the tile shows the page as it was before the point moved")
    # ...nor the page from a floor: that point lies under every floor, so the
    # next Undo (past the copies, which held the page before the point moved)
    # paints the page as it now is.
    under = pg.evaluate("() => { document.getElementById('undo').click(); return true; }")
    vu = pg.evaluate(FTRUE)
    check("Flip: a point moved under the floors, the next Undo shows what render() shows, never the floor as it was",
          under and vu["same"], str(vu))
    check("no page errors through the floor", not errs, "; ".join(errs[:2]))
    ctx.close()

    print("\nFLIP UNDO — seventy strokes, thirty Undos: the NEXT takes over")
    ctx, pg, errs = fopen(b, **PHONE)
    pg.evaluate("(n) => __busy(1, n)", BUSY)
    pg.wait_for_timeout(300)
    PS = """() => { window.__ps = 0; const f = window.paintStatic;
      if (!f.__strokes) { window.paintStatic = function (c, a) {
          for (const q of a || []) if (q.start) window.__ps++; return f.apply(this, arguments); };
        window.paintStatic.__strokes = true; } }"""
    seen = {}
    for k in range(70):
        if k >= 39:
            seen[k] = pg.evaluate(FPIX)
        fquick(pg, k)
    seen[70] = pg.evaluate(FPIX)
    fl = pg.evaluate("() => _flipFloors.map(F => F.g)")
    groups0 = pg.evaluate("() => frame().strokeGroups.length")
    pg.evaluate(PS)
    wrong, strokes_painted = [], []
    for j in range(30):                      # back to the page after 69 ... 40 strokes
        strokes_painted.append(pg.evaluate("() => { window.__ps = 0; document.getElementById('undo').click(); return window.__ps; }"))
        if pg.evaluate(FPIX) != seen[69 - j]:
            wrong.append(69 - j)
    check("Flip: seventy strokes keep two floors, the NEXT taken thirty strokes on (the case is real)",
          len(fl) == 2 and fl[1] - fl[0] >= 30, f"floors at {fl} strokes, the page now {groups0}")
    check("...and thirty Undos put back every pixel, none painting sixty strokes or more",
          not wrong and max(strokes_painted) < 60, f"wrong after {wrong}; strokes painted per press {strokes_painted}")
    check("no page errors through seventy strokes", not errs, "; ".join(errs[:2]))
    ctx.close()

    print("\nFLIP UNDO — a page opened and undone before it is drawn on")
    # No stroke has started on it, so no floor: the first Undo paints the page
    # in two parts with a floor taken between, thirty strokes under it, and the
    # next lays that floor and paints the strokes above it.
    ctx, pg, errs = fopen(b, **PHONE)
    pg.evaluate("(n) => __busy(1, n)", BUSY)
    pg.wait_for_timeout(300)
    a1 = pg.evaluate(FPRESS, "undo"); q1 = pg.evaluate("() => [window.__fn, frame().strokes.length]")
    v1 = pg.evaluate(FTRUE)
    pg.evaluate(FPRESS, "undo"); q2 = pg.evaluate("() => [window.__fn, frame().strokes.length]")
    v2 = pg.evaluate(FTRUE)
    check("Flip: the first Undo on a page just opened paints it once, in two parts with a floor between",
          a1 == 2 and q1[0] == q1[1] and v1["same"], f"paints {a1}, {q1[0]} points of {q1[1]}; {v1}")
    check("...and the next lays that floor and paints only the strokes above it",
          0 < q2[0] < 60 * 22 and v2["same"], f"{q2[0]} points of {q2[1]}; {v2}")
    check("no page errors through a page undone before it is drawn on", not errs, "; ".join(errs[:2]))
    ctx.close()

    print("\nFLIP UNDO — see-through ink above a floor, past the layering budget and under it")
    for n_see, label in ((40, "past the budget"), (10, "under the budget")):
        ctx, pg, errs = fopen(b, **PHONE)
        pg.evaluate("""(n) => { const f = frame(), pts = [], groups = [];
          for (let g = 0; g < 80; g++) { const col = g < n ? 'rgba(124, 92, 255, 0.45)' : '#1d1a2b';
            for (let i = 0; i < 60; i++) pts.push({ x: 30 + i * 4, y: 40 + g * 4 + (i % 4), color: col,
              size: 4 + (i % 5), t: pts.length * 16, start: i === 0 });
            groups.push(60); }
          f.strokes = pts; f.strokeGroups = groups; buildStrip(); render(); refreshAllThumbs(); }""", n_see)
        pg.wait_for_timeout(300)
        pg.evaluate("() => { strokeOpacity = 0.45; SkriblBrush.setBrush('pencil'); }")
        for k in range(6):
            fquick(pg, k)
        state = pg.evaluate("""() => { const f = frame(), n = f.strokeGroups.slice(-6); let a = f.strokes.length - n.reduce((x, y) => x + y, 0);
          const out = []; for (const g of n) { out.push(f.strokes.slice(a, a + g)); a += g; }
          return [_overBudgetOf(f.strokes), out.every(r => r.every(p => strokeAlphaOf(p.color) < 1)),
                  out.every(r => new Set(r.map(p => p.size)).size > 1)]; }""")
        untrue = []
        for j in range(6):
            pg.evaluate(FPRESS, "undo")
            if j >= 2 and not pg.evaluate(FTRUE)["same"]:
                untrue.append(j + 1)
        check(f"Flip: a page {label}, six see-through pencil strokes of varying width drawn on it (the case is real)",
              state == [n_see > 24, True, True], str(state))
        check(f"...and each Undo past the copies, from the floor, shows every pixel render() shows ({label})",
              not untrue, f"Undos unlike render(): {untrue}")
        check(f"no page errors through see-through Undos on Flip ({label})", not errs, "; ".join(errs[:2]))
        ctx.close()

    b.close()

bad = [r for r in results if not r[0]]
print(f"\n{'=' * 62}\n{len(results) - len(bad)}/{len(results)} passed"
      + ("" if not bad else "  FAILURES: " + ", ".join(r[1] for r in bad)))
sys.exit(1 if bad else 0)
