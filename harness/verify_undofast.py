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
    check("...and Undo then paints the drawing at the new size, never the old size's copy",
          ng == 1 and ug[1] == w1, f"repaints {ng}; canvas {ug[1]} wide")
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
    kept = pg.evaluate("() => [strokes.length, _padKept.length]")
    pg.evaluate(COUNT)
    ul, nl = undo(pg)
    check("five strokes on a blank Pad keep no copy of the canvas",
          kept[1] == 0, f"{kept[0]} points; copies {kept[1]}")
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
    heavy = pg.evaluate("() => [strokes.length, _padKept.length, _padKept.map(k => k.c.width * k.c.height)]")
    pg.evaluate("() => { window.__keptCv = _padKept.map(k => k.c); clearCanvas(); }")
    stroke(pg, box, 1)
    after = pg.evaluate("() => [strokes.length, _padKept.length, window.__keptCv.map(c => c.width * c.height)]")
    check("over a busy drawing the strokes keep their three copies (the case is real)",
          heavy[1] == 3 and all(a > 0 for a in heavy[2]), f"{heavy[0]} points; copies {heavy[1]}, pixels {heavy[2]}")
    check("...and the drawing cleared, the next stroke drops them and lets their canvases go",
          after[1] == 0 and all(a == 0 for a in after[2]), f"{after[0]} points; copies {after[1]}, old canvases' pixels {after[2]}")
    check("no page errors through a busy drawing cleared", not errs, "; ".join(errs[:2]))
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
    FSETUP = """() => { window.__fp = 0; const f = window.paintStatic;
      if (!f.__counted) { window.paintStatic = function () { window.__fp++; return f.apply(this, arguments); };
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
    FPRESS = "(id) => { window.__fp = 0; document.getElementById(id).click(); return window.__fp; }"
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
    n4 = pg.evaluate(FPRESS, "undo"); u4, t4 = pg.evaluate(FPIX), pg.evaluate(FTILE); v4 = pg.evaluate(FTRUE)
    check("past what the copies reach, Undo paints the page as before, once, and keeps it",
          n4 == 1 and u4 == before[2] and t4 == tiles[2] and v4["same"] and v4["copies"] == 1 and v4["copiesTrue"],
          f"paints {n4}; pixels {u4 == before[2]}; tile {t4 == tiles[2]}; {v4}")
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
    nl = pg.evaluate("() => { window.SKRIBL_STROKE_LAYERS = false; window.__fp = 0; document.getElementById('undo').click();"
                     " const n = window.__fp; delete window.SKRIBL_STROKE_LAYERS; return n; }")
    check("a copy made with the stroke layers on is not laid with them off: that Undo paints",
          nl == 1, f"paints {nl}")
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
    b.close()

bad = [r for r in results if not r[0]]
print(f"\n{'=' * 62}\n{len(results) - len(bad)}/{len(results)} passed"
      + ("" if not bad else "  FAILURES: " + ", ".join(r[1] for r in bad)))
sys.exit(1 if bad else 0)
