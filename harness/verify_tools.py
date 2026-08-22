"""v213 — the tool work: settings that had no control, and two new tools.

Split out of verify_ux.py, which had reached 366 assertions and a dozen browser
launches and stopped finishing inside a single invocation. A suite that cannot
be run in one go stops being run, which is the failure this project keeps
writing pins against.

REBUILT. The first version of these assertions lived in verify_ux.py and was
destroyed by `git checkout harness/verify_ux.py` against a tree whose only
commit was the v211 baseline — hours of uncommitted work, reverted by a command
reached for as a cleanup. The measured values below were recovered from the run
log of the last green run, so they are the figures the code actually produced
rather than fresh guesses. The lesson is in START-HERE: commit before anything
destructive, and never `git checkout` a file with uncommitted work in it.

WHAT IS PINNED HERE, and the shape each guards against:

  * Stroke layers, eraser width, grid density, pause handling, pressure — five
    behaviours the code already had and no control could reach. Each is
    asserted through the path that USES it (painted pixels, _eraserSize, the
    grid overlay, getPlaybackDuration), never through the control's own aria
    state: a switch that updates itself and nothing else passes every attribute
    check ever written. Mutation-tested at the time; each one's mutation is
    named in its block.

  * Shift-constrain, shortcuts, shapes, mirror — new behaviour. Shapes and
    mirror both generate ORDINARY STROKE POINTS, so the payload format is
    unchanged and the player replays them with the code it already has. The
    schema assertion in the shapes block is what catches that opening up.

  * Parity. Where a thing exists on both surfaces it is checked on both, and
    where the two share a module the assertion goes through the shared entry
    point — verify_parity's re-inline lesson: agreeing today is not the same as
    one implementation.
"""
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:5001"
import math as _math
import re as _re2
import pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]

results = []
def check(name, ok, detail=""):
    results.append((bool(ok), name))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  — {detail}" if detail else ""))


def _ink(pg, sel):
    return pg.evaluate("""(sel) => {
      const c = document.querySelector(sel);
      if (!c || !c.width || !c.height) return {w:0, h:0, ink:0, peak:0};
      const d = c.getContext('2d').getImageData(0,0,c.width,c.height).data;
      let n = 0, peak = 0;
      for (let i = 3; i < d.length; i += 4) { if (d[i] > 8) { n++; if (d[i] > peak) peak = d[i]; } }
      return {w:c.width, h:c.height, ink:n, peak:peak};
    }""", sel)


# ---------------------------------------------------------------------------
# V213c — the Stroke layers row drives the real compositor.
#
# The wet/dry compositor shipped ON and unreachable: strokeLayersOn() reads
# `window.SKRIBL_STROKE_LAYERS !== false`, a global with no control anywhere, so
# the only way to see what it did was to set it by hand in a console. It is what
# stops a see-through stroke compounding at its OWN overlaps into dark beads.
#
# Asserted on PIXELS, not on the global. Flipping a switch that sets a variable
# nothing reads would pass every attribute check ever written; the thing that
# matters is whether a self-crossing stroke beads. Drawn at 35% opacity in a
# figure-eight so the stroke crosses itself twice, then compared on peak alpha.
# Mutation (toggle stops writing the global): peak stayed 89 both ways.
print("\nV213c — Stroke layers row changes compositing, not just a flag")

def _fig8(_pg):
    _bx = _pg.locator("#canvas").bounding_box()
    _cx, _cy = _bx["x"] + 250, _bx["y"] + 200
    _pg.mouse.move(_cx - 80, _cy - 60); _pg.mouse.down()
    for _x, _y in [(0, 0), (80, 60), (-80, 60), (80, -60), (-80, -60), (0, 0)]:
        _pg.mouse.move(_cx + _x, _cy + _y, steps=12)
    _pg.mouse.up(); _pg.wait_for_timeout(250)

with sync_playwright() as _b1:
    _br1 = _b1.chromium.launch()
    _peaks = {}
    for _want_on in (True, False):
        _c1 = _br1.new_context(viewport={"width": 1100, "height": 900})
        _p1 = _c1.new_page()
        _p1.goto(BASE + "/", wait_until="load"); _p1.wait_for_timeout(700)
        _p1.evaluate("() => localStorage.clear()")
        _p1.reload(wait_until="load"); _p1.wait_for_timeout(700)
        _p1.click("#tuneBtn"); _p1.wait_for_timeout(300)
        if _want_on:
            check("V213c the Stroke layers row exists in the tune drawer and defaults ON",
                  _p1.locator("#strokeLayersBtn").count() == 1 and
                  _p1.get_attribute("#strokeLayersBtn", "aria-checked") == "true",
                  f"aria-checked={_p1.get_attribute('#strokeLayersBtn', 'aria-checked')}")
        else:
            _p1.click("#strokeLayersBtn"); _p1.wait_for_timeout(200)
        _p1.click("#tuneBtn"); _p1.wait_for_timeout(250)
        _p1.evaluate("() => { const s=document.getElementById('opacitySlider');"
                     " if(s){ s.value=35; s.dispatchEvent(new Event('input',{bubbles:true})); } }")
        _p1.wait_for_timeout(150)
        _fig8(_p1)
        _peaks[_want_on] = _ink(_p1, "#canvas")
        _p1.close(); _c1.close()

    # Gate: two different pictures cannot be compared on peak alpha.
    check("V213c gate: both runs drew the same figure (ink counts within 5%)",
          _peaks[True]["ink"] > 500 and
          abs(_peaks[True]["ink"] - _peaks[False]["ink"]) <= 0.05 * _peaks[True]["ink"],
          f"on={_peaks[True]['ink']} px, off={_peaks[False]['ink']} px")
    check("V213c turning Stroke layers OFF makes a self-crossing stroke BEAD "
          "(peak alpha stacks well past the stroke's own opacity)",
          _peaks[False]["peak"] > _peaks[True]["peak"] + 40,
          f"peak alpha on={_peaks[True]['peak']}, off={_peaks[False]['peak']}")

    # The same row on Flip. It was Pad-only at first — Flip has the same
    # behaviour (its per-stroke alpha layer in paintStatic) implemented
    # separately and with no control, which is precisely the "one editor has
    # what the other lacks" shape this project keeps hitting. The SETTING is
    # shared via lib/strokelayers.js; the compositing deliberately is not,
    # because Pad composites live mid-stroke and Flip on repaint.
    _c1f = _br1.new_context(viewport={"width": 1100, "height": 900})
    _p1f = _c1f.new_page()
    _p1f.goto(BASE + "/flip", wait_until="load"); _p1f.wait_for_timeout(800)
    _p1f.evaluate("() => localStorage.clear()")
    _p1f.reload(wait_until="load"); _p1f.wait_for_timeout(800)
    _p1f.click("#tuneBtn"); _p1f.wait_for_timeout(300)
    check("V213c flip has the SAME Stroke layers row, defaulting ON",
          _p1f.locator("#strokeLayersBtn").count() == 1 and
          _p1f.get_attribute("#strokeLayersBtn", "aria-checked") == "true",
          f"found {_p1f.locator('#strokeLayersBtn').count()}")
    _p1f.click("#strokeLayersBtn"); _p1f.wait_for_timeout(250)
    check("V213c flip: the row drives the SHARED setting both editors read "
          "(not a second copy that happens to agree)",
          _p1f.evaluate("() => window.SKRIBL_STROKE_LAYERS") is False and
          _p1f.evaluate("() => SkriblStrokeLayers.enabled()") is False,
          f"global={_p1f.evaluate('() => window.SKRIBL_STROKE_LAYERS')}")
    _p1f.close(); _c1f.close()
    _br1.close()


# ---------------------------------------------------------------------------
# V213d — the eraser multiplier is ONE copy, and it is reachable.
#
# The eraser was three times the pen, and that 3 was written out SEVEN times:
# three stroke sites in app.js, two in flip.js, and — the dangerous pair — the
# eraser CURSOR site in each file. A drifted cursor copy leaves the ring lying
# about how much it erases, and the user is aiming with that ring. Same shape as
# MAX_LOOP_SECONDS before lib/looptrim.js.
#
# Asserted through _eraserSize(), the function both editors' draw paths call,
# rather than through the seg's own aria state. Mutation (re-inline Pad's copy):
# the "editor CALLS the lib" assertion STAYED GREEN — it only proves the lib
# loaded — while the draw-path assertion caught it at 30 against a wanted 20.
print("\nV213d — eraser width is one shared constant, wired on both editors")

with sync_playwright() as _b2:
    _br2 = _b2.chromium.launch()
    for _nm, _path, _open in (
        ("pad",  "/",     "() => document.getElementById('colorOpenBtn').click()"),
        ("flip", "/flip", "() => document.getElementById('colorCurrent').click()"),
    ):
        _c2 = _br2.new_context(viewport={"width": 1100, "height": 900})
        _p2 = _c2.new_page()
        _p2.goto(BASE + _path, wait_until="load"); _p2.wait_for_timeout(800)
        _p2.evaluate("() => localStorage.clear()")
        _p2.reload(wait_until="load"); _p2.wait_for_timeout(800)
        _p2.evaluate(_open); _p2.wait_for_timeout(300)

        check(f"V213d {_nm}: the Eraser seg is present (one shared partial "
              f"supplies it to both surfaces)",
              _p2.locator("#eraserSeg").count() == 1,
              f"found {_p2.locator('#eraserSeg').count()}")
        check(f"V213d {_nm}: the editor CALLS lib/erasersize.js "
              f"(behavioural agreement is not one implementation)",
              _p2.evaluate("() => !!(window.SkriblEraser && "
                           "typeof SkriblEraser.sizeFor === 'function')"))
        for _m in (2, 5):
            _p2.evaluate("(m) => { const b = document.querySelector("
                         "'#eraserSeg [data-eraser=\"' + m + '\"]'); if (b) b.click(); }", _m)
            _p2.wait_for_timeout(200)
            _got = _p2.evaluate("() => _eraserSize(10, true)")
            _pen = _p2.evaluate("() => _eraserSize(10, false)")
            check(f"V213d {_nm}: choosing {_m}x drives the DRAW PATH's width, "
                  f"not just the control's own state",
                  _got == 10 * _m and _pen == 10,
                  f"_eraserSize(10, erase)={_got} (want {10 * _m}); pen unchanged at {_pen}")
        _p2.close(); _c2.close()
    _br2.close()


# ---------------------------------------------------------------------------
# V213e — grid cells are square at every canvas preset, and adjustable.
#
# lib/gridoverlay.js hardcoded `cols = 8, rows = 6`. That ratio IS 4:3, so the
# cells were square only on the `classic` preset. On `tall` (9:16) an 8x6 grid
# draws cells about 2.4x taller than wide (measured aspect 0.40) — not an
# alignment guide so much as a distortion of one, on BOTH editors.
#
# MEASURED ON THE PAINTED OVERLAY, not on the numbers the module reports.
# Scanlines are taken at several offsets and the MAX run count used: a scanline
# landing ON a grid line reads as fully inked and yields one run, which is a
# broken probe, not a one-cell grid. That artifact bit this probe on its first
# run and reported a working grid as broken.
#
# Mutation (restore the fixed 8x6): classic stayed GREEN — it was always right
# at 4:3 — while square fell to 0.71 and tall to 0.40.
print("\nV213e — grid cells stay square at every canvas preset")

_CELLS = """(sel) => {
  const o = document.querySelector(sel);
  if (!o || !o.width) return null;
  const d = o.getContext('2d').getImageData(0, 0, o.width, o.height).data;
  const a = (x, y) => d[(y * o.width + x) * 4 + 3];
  // MEDIAN SPACING between grid lines, not a count of them.
  //
  // Counting runs and dividing looked fine and was fragile: on `tall` there are
  // only about four columns, so missing ONE boundary line swings the count 4->3
  // and the aspect 0.99 -> 1.31. It flipped red when an unrelated tune row was
  // added and changed the panel height by a few pixels. Spacing between
  // adjacent lines is unaffected by a missed edge, because the median ignores
  // the one bad gap instead of redistributing it across the whole axis.
  //
  // Several scanline offsets are still used and the DENSEST one wins: a
  // scanline landing exactly ON a grid line reads as fully inked and finds no
  // edges at all, which is a broken probe rather than a one-cell grid.
  function edges(get, n) {
    let best = [];
    for (const f of [0.07,0.19,0.31,0.43,0.57,0.69,0.81]) {
      const at = Math.floor(n * f), found = [];
      for (let i = 1; i < (get === 'v' ? o.width : o.height); i++) {
        const cur = get === 'v' ? a(i, at) : a(at, i);
        const prev = get === 'v' ? a(i-1, at) : a(at, i-1);
        if (cur > 50 && prev <= 50) found.push(i);
      }
      if (found.length > best.length) best = found;
    }
    return best;
  }
  function medianGap(xs) {
    if (xs.length < 2) return 0;
    const g = [];
    for (let i = 1; i < xs.length; i++) g.push(xs[i] - xs[i-1]);
    g.sort((p, q) => p - q);
    return g[Math.floor(g.length / 2)];
  }
  const vx = edges('v', o.height), hy = edges('h', o.width);
  const cw = medianGap(vx), ch = medianGap(hy);
  if (!cw || !ch) return null;
  return {cellW: cw, cellH: ch, cols: Math.round(o.width/cw), rows: Math.round(o.height/ch),
          aspect: +(cw/ch).toFixed(2)};
}"""

with sync_playwright() as _b3:
    _br3 = _b3.chromium.launch()
    _c3 = _br3.new_context(viewport={"width": 1200, "height": 950})
    _p3 = _c3.new_page()
    _p3.goto(BASE + "/", wait_until="load"); _p3.wait_for_timeout(800)
    _p3.evaluate("() => localStorage.clear()")
    _p3.reload(wait_until="load"); _p3.wait_for_timeout(800)
    _p3.click("#tuneBtn"); _p3.wait_for_timeout(250)
    _p3.click("#gridBtn"); _p3.wait_for_timeout(400)

    for _preset in ("classic", "square", "tall"):
        _p3.evaluate("(s) => { const b = document.querySelector("
                     "'#canvasSeg [data-size=\"' + s + '\"]'); if (b) b.click(); }", _preset)
        _p3.wait_for_timeout(700)
        _cell = _p3.evaluate(_CELLS, "#padGrid")
        check(f"V213e grid cells are square on the '{_preset}' canvas "
              f"(the fixed 8x6 made them 4:3-only)",
              _cell is not None and 0.8 <= _cell["aspect"] <= 1.25,
              f"{_cell['cols']}x{_cell['rows']} cells, aspect {_cell['aspect']}"
              if _cell else "no overlay painted")

    _p3.evaluate("() => { const b = document.querySelector("
                 "'#canvasSeg [data-size=\"classic\"]'); if (b) b.click(); }")
    _p3.wait_for_timeout(600)
    _mid = _p3.evaluate(_CELLS, "#padGrid")
    _p3.evaluate("() => { const b = document.querySelector("
                 "'#gridDensitySeg [data-density=\"coarse\"]'); if (b) b.click(); }")
    _p3.wait_for_timeout(500)
    _coarse = _p3.evaluate(_CELLS, "#padGrid")
    check("V213e the density seg repaints the grid with fewer cells",
          _coarse["cols"] < _mid["cols"] and _coarse["aspect"] >= 0.8,
          f"medium {_mid['cols']}x{_mid['rows']} -> coarse {_coarse['cols']}x{_coarse['rows']}")
    _p3.click("#gridBtn"); _p3.wait_for_timeout(300)
    check("V213e ...and the density seg is hidden while the grid is OFF "
          "(a control whose effect cannot be seen)",
          _p3.evaluate("() => document.getElementById('gridDensityGroup').hidden") is True)
    _p3.close(); _c3.close()
    _br3.close()


# ---------------------------------------------------------------------------
# V213f — pause handling is visible, and it travels with the drawing.
#
# `Math.min(gap, 50)` was hardcoded at BOTH gap sites (buildPlaybackTimeline and
# getPlaybackDuration), so the largest single difference between how a drawing
# was made and how it replays was a magic number nobody could see: long thinking
# pauses were silently squeezed to 50ms.
#
# THE ROUND-TRIP IS THE LOAD-BEARING ASSERTION. The PLAYER builds its timeline
# with the same function, so a device-local preference would mean the author's
# Play and a viewer's shared link disagreed about the same Skribl — right for
# whoever changed it, wrong for everyone else. Mutation (loadSkribl stops
# adopting the field): the "written into the payload" assertion STAYED GREEN
# while the author's 1,903ms replay collapsed to 410ms for the viewer.
print("\nV213f — pause handling changes replay, and posts with the drawing")

with sync_playwright() as _b4:
    _br4 = _b4.chromium.launch()
    _c4 = _br4.new_context(viewport={"width": 1100, "height": 900})
    _p4 = _c4.new_page()
    _p4.goto(BASE + "/", wait_until="load"); _p4.wait_for_timeout(800)
    _p4.evaluate("() => localStorage.clear()")
    _p4.reload(wait_until="load"); _p4.wait_for_timeout(800)
    _p4.click("#recordBtn"); _p4.wait_for_timeout(300)

    _bx4 = _p4.locator("#canvas").bounding_box()
    _GAP = 1500
    for _k, (_x0, _y0) in enumerate(((80, 80), (80, 300))):
        _p4.mouse.move(_bx4["x"] + _x0, _bx4["y"] + _y0); _p4.mouse.down()
        for _i in range(1, 12):
            _p4.mouse.move(_bx4["x"] + _x0 + _i * 10, _bx4["y"] + _y0 + _i * 4)
        _p4.mouse.up()
        if _k == 0:
            _p4.wait_for_timeout(_GAP)          # a real idle pause
    _p4.wait_for_timeout(200)
    _p4.click("#recordBtn"); _p4.wait_for_timeout(600)

    _durs = {}
    for _m4 in ("tight", "trim", "keep"):
        _p4.evaluate("(m) => setPauseMode(m)", _m4)
        _durs[_m4] = _p4.evaluate("() => getPlaybackDuration()")

    # GATE: a take with no real pause orders these identically at zero.
    check("V213f gate: the take really contains a long idle pause",
          _durs["keep"] > _GAP * 0.8,
          f"keep total {_durs['keep']}ms against a ~{_GAP}ms pause")
    check("V213f the three pause modes give three different replay lengths, "
          "tight < trim < keep",
          _durs["tight"] < _durs["trim"] < _durs["keep"],
          f"tight={_durs['tight']}ms, trim={_durs['trim']}ms, keep={_durs['keep']}ms")

    _rt = _p4.evaluate("""() => {
      setPauseMode('keep');
      const s = serializeSkribl();
      const authorSaw = getPlaybackDuration();
      setPauseMode('tight');              // a viewer whose browser defaults tight
      loadSkribl(s);                      // ...opens the shared link
      return {carried: s.pauseMode, adopted: pauseMode,
              viewerSees: getPlaybackDuration(), authorSaw: authorSaw};
    }""")
    check("V213f the choice is written into the payload, not just this browser",
          _rt["carried"] == "keep", f"serialized pauseMode={_rt['carried']!r}")
    check("V213f a viewer set to 'tight' replays an author's 'keep' drawing "
          "at the AUTHOR's length (editor preview and shared link agree)",
          _rt["adopted"] == "keep" and _rt["viewerSees"] == _rt["authorSaw"],
          f"adopted={_rt['adopted']!r}, viewer {_rt['viewerSees']}ms "
          f"vs author {_rt['authorSaw']}ms")

    _p4.click("#tuneBtn"); _p4.wait_for_timeout(300)
    _p4.evaluate("() => { const b = document.querySelector("
                 "'#pauseSeg [data-pause=\"trim\"]'); if (b) b.click(); }")
    _p4.wait_for_timeout(250)
    check("V213f the Pauses seg writes through to the drawing's own setting",
          _p4.evaluate("() => pauseMode") == "trim" and
          _p4.evaluate("() => serializeSkribl().pauseMode") == "trim",
          f"pauseMode={_p4.evaluate('() => pauseMode')!r}")
    _p4.close(); _c4.close()
    _br4.close()


# ---------------------------------------------------------------------------
# V213g — the pressure curve is one copy, and it can be turned off.
#
# `PRESSURE_MIN = 0.35` and the line using it existed once per surface,
# identically. The raw read is deliberately NOT shared — Pad is on touch events
# and reads `touch.touchType`/`force`, Flip is on Pointer Events and reads
# `e.pressure`. Only the curve, the floor and the setting are common.
#
# DRIVEN THROUGH EACH SURFACE'S OWN SIZE FUNCTION with a synthetic reading, not
# a fake gesture: Chromium has no Touch constructor supporting touchType, so an
# Apple Pencil stroke cannot be synthesised here at all. That limitation is
# exactly why the off switch is worth having.
# Mutation (toggle ignored): both OFF assertions went red at 5.125/6.75/10.
print("\nV213g — one pressure curve, shared, with a working off switch")

_EXPECT = {0: 10, 0.25: 5.125, 0.5: 6.75, 1.0: 10}   # base 10, floor 0.35

with sync_playwright() as _b5:
    _br5 = _b5.chromium.launch()
    _curves = {}
    for _nm5, _path5, _call5, _open5 in (
        ("pad",  "/",     "(r) => pressureSize({pointerType:'pen', pressure:r}, 10, false)",
         "() => document.getElementById('colorOpenBtn').click()"),
        ("flip", "/flip", "(r) => sizeFor({pointerType:'pen', pressure:r}, 10)",
         "() => document.getElementById('colorCurrent').click()"),
    ):
        _c5 = _br5.new_context(viewport={"width": 1100, "height": 900})
        _p5 = _c5.new_page()
        _p5.goto(BASE + _path5, wait_until="load"); _p5.wait_for_timeout(800)
        _p5.evaluate("() => localStorage.clear()")
        _p5.reload(wait_until="load"); _p5.wait_for_timeout(800)
        _p5.evaluate(_open5); _p5.wait_for_timeout(300)

        check(f"V213g {_nm5}: the Pressure seg is present and the editor CALLS "
              f"lib/pressure.js",
              _p5.locator("#pressureSeg").count() == 1 and
              _p5.evaluate("() => !!(window.SkriblPressure && "
                           "typeof SkriblPressure.sizeFrom === 'function')"))

        _got = {}
        for _raw in (0, 0.25, 0.5, 1.0):
            _got[_raw] = _p5.evaluate(_call5, _raw)
        _curves[_nm5] = _got
        check(f"V213g {_nm5}: pressure scales width on the shared curve, and a "
              f"0 reading means 'no reading yet' rather than a feather touch",
              all(abs(_got[k] - v) < 1e-6 for k, v in _EXPECT.items()),
              f"got {_got}, want {_EXPECT}")

        _p5.evaluate("() => { const b = document.querySelector("
                     "'#pressureSeg [data-pressure=\"off\"]'); if (b) b.click(); }")
        _p5.wait_for_timeout(200)
        _off = [_p5.evaluate(_call5, _r) for _r in (0.25, 0.5, 1.0)]
        check(f"V213g {_nm5}: turning Pressure OFF flattens every reading to the "
              f"nominal width (the escape hatch for a device reporting badly)",
              all(abs(_v - 10) < 1e-6 for _v in _off),
              f"widths at 0.25/0.5/1.0 = {_off}")
        _p5.close(); _c5.close()
    _br5.close()

check("V213g both editors return the SAME width for the same reading "
      "(one curve, not two that happen to agree)",
      _curves["pad"] == _curves["flip"],
      f"pad {_curves['pad']} vs flip {_curves['flip']}")


# ---------------------------------------------------------------------------
# V213h — Shift constrains a stroke to an axis, on both editors.
#
# Anchored at the stroke's FIRST point, not at the previous one. Per-segment
# snapping is the obvious version and it staircases: every point gets its own
# tiny axis and the line wanders. Anchoring at the start keeps every captured
# point on a ray from the anchor, so the path is straight without anything
# having to be un-drawn — which matters because both editors paint live.
#
# MEASURED AS OFF-AXIS ANGLE FROM THE ANCHOR, not as deviation from the
# first-to-last chord. The chord version is what this probe tried first and it
# reported the fix as WORSE (39 -> 54): with 8-way snapping the ray legitimately
# changes mid-drag, so a drag that starts steep rides 45 degrees then flattens
# to 0. Correct behaviour, bent chord. The invariant is that every point sits on
# SOME 45-degree ray. Mutation (constraint made a no-op): 22.4 deg both ways.
print("\nV213h — Shift snaps a stroke to 45-degree axes on both editors")

_OFFAXIS = """(n) => {
  const src = (typeof strokes !== 'undefined' && strokes.length)
    ? strokes : frames.reduce((a,f)=>a.concat(f.strokes), []);
  const pts = src.slice(-n);
  if (pts.length < 3) return null;
  const a = pts[0];
  let worst = 0;
  for (const p of pts.slice(1)) {
    const ang = Math.atan2(p.y-a.y, p.x-a.x) * 180 / Math.PI;
    let off = Math.abs(((ang % 45) + 45) % 45);
    if (off > 22.5) off = 45 - off;
    worst = Math.max(worst, off);
  }
  return {n: pts.length, off: +worst.toFixed(2)};
}"""

def _wobble(_pg, _sel, _shift):
    _bx = _pg.locator(_sel).bounding_box()
    _x0, _y0 = _bx["x"] + 90, _bx["y"] + 160
    _pg.mouse.move(_x0, _y0)
    if _shift: _pg.keyboard.down("Shift")
    _pg.mouse.down()
    for _i in range(1, 25):
        _pg.mouse.move(_x0 + _i * 12, _y0 + _math.sin(_i * 0.9) * 26)
    _pg.mouse.up()
    if _shift: _pg.keyboard.up("Shift")
    _pg.wait_for_timeout(250)

with sync_playwright() as _b6:
    _br6 = _b6.chromium.launch()
    for _nm6, _path6, _sel6 in (("pad", "/", "#canvas"), ("flip", "/flip", "#pad")):
        _res6 = {}
        for _sh in (False, True):
            _c6 = _br6.new_context(viewport={"width": 1100, "height": 900})
            _p6 = _c6.new_page()
            _p6.goto(BASE + _path6, wait_until="load"); _p6.wait_for_timeout(800)
            _p6.evaluate("() => localStorage.clear()")
            _p6.reload(wait_until="load"); _p6.wait_for_timeout(800)
            _wobble(_p6, _sel6, _sh)
            _res6[_sh] = _p6.evaluate(_OFFAXIS, 40)
            _p6.close(); _c6.close()
        # GATE: otherwise "constrained" is indistinguishable from a test that
        # happened to draw a straight line.
        check(f"V213h {_nm6} gate: the same drag WITHOUT Shift really is off-axis",
              _res6[False] and _res6[False]["off"] > 10,
              f"free-hand worst off-axis {_res6[False]['off'] if _res6[False] else None} deg")
        check(f"V213h {_nm6}: with Shift held, every point lies on a 45-degree "
              f"ray from the stroke's start",
              _res6[True] and _res6[True]["off"] < 0.5,
              f"worst off-axis {_res6[True]['off'] if _res6[True] else None} deg "
              f"over {_res6[True]['n'] if _res6[True] else 0} points")
    _br6.close()


# ---------------------------------------------------------------------------
# V213i — tool, size and grid shortcuts on both editors.
#
# Pad had FOUR bound keys in total (Ctrl+Z/Y, Enter, Escape) while Flip already
# answered p/e. LETTERS MATCH FLIP'S, not the b/e most drawing apps use:
# consistency between the two surfaces beats consistency with the outside world
# here, because this project's recurring bug is one editor having what the other
# lacks.
#
# Pad's handler lives in editor_tune.js, which the PLAYER does not load, so
# these cost zero player bytes — and is deliberately NOT registered with
# lib/keyregistry.js, because verify_keys asserts that registry is absent from
# Pad. Flip's ARE registered, because it is loaded there.
#
# THE TYPING GUARD IS THE ASSERTION THAT MATTERS. Mutation (guard removed):
# typing 'peg]]' into a text field switched to the eraser, turned on the grid
# AND bumped the brush size, while all three "the shortcut works" checks passed.
print("\nV213i — tool, size and grid shortcuts on both editors")

with sync_playwright() as _b7:
    _br7 = _b7.chromium.launch()
    for _nm7, _path7, _sizeId, _eraserExpr in (
        ("pad",  "/",     "brushSizeRange", "() => tool === 'eraser'"),
        ("flip", "/flip", "size",           "() => !!erasing"),
    ):
        _c7 = _br7.new_context(viewport={"width": 1100, "height": 900})
        _p7 = _c7.new_page()
        _p7.goto(BASE + _path7, wait_until="load"); _p7.wait_for_timeout(800)
        _p7.evaluate("() => localStorage.clear()")
        _p7.reload(wait_until="load"); _p7.wait_for_timeout(800)

        _sz = lambda: _p7.evaluate("(id) => +document.getElementById(id).value", _sizeId)
        _grid = lambda: _p7.evaluate(
            "() => document.getElementById('gridBtn').classList.contains('active')")

        _p7.keyboard.press("e"); _p7.wait_for_timeout(150)
        _isEraser = _p7.evaluate(_eraserExpr)
        _p7.keyboard.press("p"); _p7.wait_for_timeout(150)
        _isPen = not _p7.evaluate(_eraserExpr)
        check(f"V213i {_nm7}: 'e' and 'p' switch eraser and pen",
              _isEraser and _isPen,
              f"after e eraser={_isEraser}, after p pen={_isPen}")

        _before = _sz()
        for _ in range(3):
            _p7.keyboard.press("]"); _p7.wait_for_timeout(80)
        _up = _sz()
        _p7.keyboard.press("["); _p7.wait_for_timeout(120)
        _down = _sz()
        check(f"V213i {_nm7}: ']' and '[' move the brush size through the "
              f"slider's own input event",
              _up == _before + 3 and _down == _up - 1,
              f"{_before} -> {_up} -> {_down}")

        _p7.keyboard.press("g"); _p7.wait_for_timeout(350)
        _gridOn = _grid()
        _p7.keyboard.press("g"); _p7.wait_for_timeout(350)
        check(f"V213i {_nm7}: 'g' toggles the grid both ways",
              _gridOn and not _grid(),
              f"on={_gridOn}, back off={not _grid()}")

        _rest = (_sz(), _grid(), _p7.evaluate(_eraserExpr))
        _p7.evaluate("""() => { const i = document.createElement('input');
          i.type='text'; i.id='__probe_input'; document.body.appendChild(i); i.focus(); }""")
        _p7.keyboard.type("peg]]")
        _p7.wait_for_timeout(250)
        _after = (_sz(), _grid(), _p7.evaluate(_eraserExpr))
        check(f"V213i {_nm7}: typing 'peg]]' into a TEXT FIELD changes nothing "
              f"(a shortcut that fires while naming a draft eats the letter)",
              _rest == _after, f"{_rest} -> {_after}")
        _p7.close(); _c7.close()
    _br7.close()


# ---------------------------------------------------------------------------
# V213j — line, rectangle and ellipse, as ordinary stroke points.
#
# THE PAYLOAD ASSERTION IS THE IMPORTANT ONE. A Skribl is a flat array of
# {x, y, color, size, t, start, erase} that the player replays. A shape
# PRIMITIVE would mean a schema change, new rendering in the player, and every
# existing post needing to keep working. Generating the outline as points means
# the player draws shapes with the code it already has and never learns they
# exist — so this checks no point carries a field outside that set. If a later
# change starts stamping shapes, that assertion catches the format opening up.
#
# On Flip the extra assertion is sumGroups == strokes.length: Flip's share
# validation REJECTS a frame whose strokeGroups do not account for every point
# ("accounts for 317 points, but the strokes array contains 318"), and a shape
# commits as one run of hundreds of points at once.
#
# The draw drawer is left CLOSED throughout: startDraw treats a canvas tap with
# a drawer open as a dismiss, which silently ate the first shape drag and looked
# exactly like a broken line tool.
print("\nV213j — shapes generate points, and add no payload format")

_SHAPE_GEO = """() => {
  const g = strokeGroups.length ? strokeGroups[strokeGroups.length-1] : 0;
  const pts = strokes.slice(strokes.length - g);
  if (!pts.length) return null;
  const xs = pts.map(p=>p.x), ys = pts.map(p=>p.y);
  const allowed = ['x','y','color','size','t','start','erase'];
  const extra = [];
  for (const p of pts) for (const k of Object.keys(p))
    if (allowed.indexOf(k) === -1 && extra.indexOf(k) === -1) extra.push(k);
  return {n: pts.length, firstIsStart: !!pts[0].start, extra: extra,
          w: Math.round(Math.max(...xs)-Math.min(...xs)),
          h: Math.round(Math.max(...ys)-Math.min(...ys)),
          tSpread: pts[pts.length-1].t - pts[0].t};
}"""
_FGEO = """() => {
  const f = frames[idx];
  const g = f.strokeGroups[f.strokeGroups.length-1] || 0;
  const pts = f.strokes.slice(f.strokes.length-g);
  if(!pts.length) return null;
  const xs=pts.map(p=>p.x), ys=pts.map(p=>p.y);
  return {n:pts.length, total:f.strokes.length,
          sumGroups:f.strokeGroups.reduce((a,b)=>a+b,0), firstStart:!!pts[0].start,
          w:Math.round(Math.max(...xs)-Math.min(...xs)),
          h:Math.round(Math.max(...ys)-Math.min(...ys))};
}"""

def _sdrag(_pg, _sel, _x0, _y0, _x1, _y1, _shift=False):
    _bx = _pg.locator(_sel).bounding_box()
    _pg.mouse.move(_bx["x"]+_x0, _bx["y"]+_y0)
    if _shift: _pg.keyboard.down("Shift")
    _pg.mouse.down()
    for _i in range(1, 13):
        _pg.mouse.move(_bx["x"]+_x0+(_x1-_x0)*_i/12, _bx["y"]+_y0+(_y1-_y0)*_i/12)
        _pg.wait_for_timeout(15)
    _pg.mouse.up()
    if _shift: _pg.keyboard.up("Shift")
    _pg.wait_for_timeout(250)

with sync_playwright() as _b8:
    _br8 = _b8.chromium.launch()
    _c8 = _br8.new_context(viewport={"width": 1200, "height": 950})
    _p8 = _c8.new_page()
    _p8.goto(BASE + "/", wait_until="load"); _p8.wait_for_timeout(800)
    _p8.evaluate("() => localStorage.clear()")
    _p8.reload(wait_until="load"); _p8.wait_for_timeout(800)
    _p8.click("#recordBtn"); _p8.wait_for_timeout(300)

    _geos = {}
    for _kind in ("line", "rect", "ellipse"):
        _p8.evaluate("(k) => document.querySelector("
                     "'#shapeSeg [data-shape=\"' + k + '\"]').click()", _kind)
        _p8.wait_for_timeout(150)
        _sdrag(_p8, "#canvas", 90, 90, 330, 240)
        _geos[_kind] = _p8.evaluate(_SHAPE_GEO)
        check(f"V213j {_kind}: drawing it captures a real run of points, "
              f"the first flagged as a stroke start",
              _geos[_kind] and _geos[_kind]["n"] > 20 and _geos[_kind]["firstIsStart"],
              f"{_geos[_kind]['n'] if _geos[_kind] else 0} points")

    check("V213j picking a shape also SELECTS the shape tool",
          _p8.evaluate("() => tool") == "shape",
          f"tool={_p8.evaluate('() => tool')!r}")
    check("V213j shape points carry NO field outside the replay schema "
          "(a shape primitive would open the payload format)",
          all(g["extra"] == [] for g in _geos.values()),
          "; ".join(f"{k}:{g['extra']}" for k, g in _geos.items()))
    check("V213j shape points are TIMED across the drag, so a shape replays as "
          "a drawing rather than appearing at once",
          all(g["tSpread"] > 50 for g in _geos.values()),
          "; ".join(f"{k}:{g['tSpread']}ms" for k, g in _geos.items()))
    check("V213j a rectangle encloses more outline than a line across the same "
          "drag (the kinds are not all drawing the same thing)",
          _geos["rect"]["n"] > _geos["line"]["n"],
          f"line {_geos['line']['n']} pts, rect {_geos['rect']['n']} pts")

    _p8.evaluate("() => document.querySelector('#shapeSeg [data-shape=\"ellipse\"]').click()")
    _p8.wait_for_timeout(150)
    _sdrag(_p8, "#canvas", 90, 400, 330, 550, True)
    _sq = _p8.evaluate(_SHAPE_GEO)
    check("V213j Shift makes an ellipse a CIRCLE (equal extent on both axes) "
          "even though the drag was not square",
          _sq and abs(_sq["w"] - _sq["h"]) <= 3,
          f"{_sq['w']}x{_sq['h']} from a 240x150 drag")

    # The tool slider was `pen ? 0 : penWidth` — a two-button ASSUMPTION, not a
    # two-button special case. A third tool parked the pill under the second.
    _sl = _p8.evaluate("""() => {
      const s=document.getElementById('toolSlider'), b=document.getElementById('shapeToolBtn');
      const g=document.getElementById('toolGroup');
      return {x: s.style.transform, left: b.offsetLeft - g.offsetLeft,
              w: parseFloat(s.style.width), bw: b.offsetWidth};
    }""")
    check("V213j the tool pill sits under the THIRD tool, not the second "
          "(the old slider maths assumed exactly two)",
          f"translateX({_sl['left']}px)" == _sl["x"] and abs(_sl["w"] - _sl["bw"]) < 1,
          f"slider {_sl['x']} width {_sl['w']}, button at {_sl['left']} width {_sl['bw']}")
    _p8.close(); _c8.close()

    # ---- the same tool on FLIP. Flip repaints the whole frame every time, so
    # its preview is just drawn last; Pad paints incrementally and copies the
    # canvas to preview against. Different mechanism, same shared geometry.
    _c8f = _br8.new_context(viewport={"width": 1200, "height": 950})
    _p8f = _c8f.new_page()
    _p8f.goto(BASE + "/flip", wait_until="load"); _p8f.wait_for_timeout(900)
    _p8f.evaluate("() => localStorage.clear()")
    _p8f.reload(wait_until="load"); _p8f.wait_for_timeout(900)
    for _k in ("line", "rect", "ellipse"):
        _p8f.evaluate("(k) => document.querySelector("
                      "'#shapeSeg [data-shape=\"' + k + '\"]').click()", _k)
        _p8f.wait_for_timeout(150)
        _sdrag(_p8f, "#pad", 90, 90, 330, 240)
        _fg = _p8f.evaluate(_FGEO)
        check(f"V213j flip {_k}: draws the shape and accounts for every point "
              f"(strokeGroups must sum to strokes.length or the share is refused)",
              _fg and _fg["n"] > 20 and _fg["firstStart"] and _fg["sumGroups"] == _fg["total"],
              f"{_fg['n'] if _fg else 0} pts, groups sum {_fg['sumGroups'] if _fg else 0} "
              f"vs {_fg['total'] if _fg else 0} strokes")
    _sdrag(_p8f, "#pad", 90, 400, 330, 550, True)
    _fsq = _p8f.evaluate(_FGEO)
    check("V213j flip: Shift gives a circle, same shared geometry as Pad",
          _fsq and abs(_fsq["w"] - _fsq["h"]) <= 3,
          f"{_fsq['w']}x{_fsq['h']} from a 240x150 drag")
    _fsl = _p8f.evaluate("""() => { const s=document.getElementById('toolSlider'),
      b=document.getElementById('shapeToolBtn'), g=document.getElementById('toolGroup');
      return {x:s.style.transform, left:b.offsetLeft-g.offsetLeft}; }""")
    check("V213j flip: the tool pill sits under the third tool "
          "(Flip carried the same two-button slider assumption)",
          f"translateX({_fsl['left']}px)" == _fsl["x"],
          f"slider {_fsl['x']}, button at {_fsl['left']}")
    _p8f.close(); _c8f.close()
    _br8.close()


# ---------------------------------------------------------------------------
# V213k — mirror drawing, on both editors, as ordinary strokes.
#
# ONE GROUP PER REFLECTION is the assertion that matters. Appending a mirrored
# half onto the original stroke is the obvious implementation and it is wrong:
# the replay joins consecutive points, so the two halves would be linked by a
# line straight across the canvas — the same class of defect as the stray line,
# except baked into the payload rather than a live-draw artifact.
#
# The axis is the CANVAS centre, not the stroke's start: a mirror anchored to
# wherever you touched down drifts between strokes and cannot be aimed.
#
# ONE page per surface, resetting the stroke arrays between modes rather than
# reloading. Three reloads per surface is what pushed the old combined suite
# past a single invocation, and a suite that cannot be run stops being run.
print("\nV213k — mirror reflects across the canvas centre, one group per copy")

_MIR_PAD = """() => ({groups: strokeGroups.length, total: strokes.length,
  sum: strokeGroups.reduce((a,b)=>a+b,0),
  minX: Math.round(Math.min(...strokes.map(p=>p.x))),
  maxX: Math.round(Math.max(...strokes.map(p=>p.x))),
  cw: getCanvasLogicalSize().width})"""
_MIR_FLIP = """() => { const f=frames[idx]; return {groups:f.strokeGroups.length,
  total:f.strokes.length, sum:f.strokeGroups.reduce((a,b)=>a+b,0),
  minX: Math.round(Math.min(...f.strokes.map(p=>p.x))),
  maxX: Math.round(Math.max(...f.strokes.map(p=>p.x))), cw: CW}; }"""

with sync_playwright() as _b9:
    _br9 = _b9.chromium.launch()
    for _nm9, _path9, _sel9, _q9, _rec9 in (
        ("pad", "/", "#canvas", _MIR_PAD, True),
        ("flip", "/flip", "#pad", _MIR_FLIP, False),
    ):
        _seen9 = {}
        _c9 = _br9.new_context(viewport={"width": 1200, "height": 950})
        _p9 = _c9.new_page()
        _p9.goto(BASE + _path9, wait_until="load"); _p9.wait_for_timeout(900)
        _p9.evaluate("() => localStorage.clear()")
        _p9.reload(wait_until="load"); _p9.wait_for_timeout(900)
        if _rec9:
            _p9.click("#recordBtn"); _p9.wait_for_timeout(300)
        for _mode in ("off", "vertical", "both"):
            _p9.evaluate("""() => {
              if (typeof strokes !== 'undefined') { strokes = []; strokeGroups = []; }
              else { frames[idx].strokes = []; frames[idx].strokeGroups = []; }
            }""")
            _p9.evaluate("(m) => document.querySelector("
                         "'#mirrorSeg [data-mirror=\"' + m + '\"]').click()", _mode)
            _p9.wait_for_timeout(200)
            _bx9 = _p9.locator(_sel9).bounding_box()
            _p9.mouse.move(_bx9["x"] + 120, _bx9["y"] + 150); _p9.mouse.down()
            for _i in range(1, 14):
                _p9.mouse.move(_bx9["x"] + 120 + _i * 7, _bx9["y"] + 150 + (_i % 5) * 8)
            _p9.mouse.up(); _p9.wait_for_timeout(250)
            _seen9[_mode] = _p9.evaluate(_q9)
        _p9.close(); _c9.close()

        _off9, _vert, _both = _seen9["off"], _seen9["vertical"], _seen9["both"]
        check(f"V213k {_nm9} gate: the unmirrored stroke stays LEFT of centre "
              f"(otherwise a reflection is indistinguishable from the original)",
              _off9["maxX"] < _off9["cw"] / 2,
              f"stroke spans x {_off9['minX']}-{_off9['maxX']} on a {_off9['cw']}px canvas")
        check(f"V213k {_nm9}: a vertical mirror doubles the points and lands the "
              f"copy at (canvasWidth - x)",
              _vert["total"] == _off9["total"] * 2 and
              abs(_vert["maxX"] - (_off9["cw"] - _off9["minX"])) <= 2,
              f"{_off9['total']} -> {_vert['total']} points, copy max x "
              f"{_vert['maxX']} vs expected {_off9['cw'] - _off9['minX']}")
        check(f"V213k {_nm9}: each reflection is its OWN group, so the replay "
              f"never joins the two halves across the canvas",
              _off9["groups"] == 1 and _vert["groups"] == 2 and _both["groups"] == 4,
              f"groups off={_off9['groups']} vertical={_vert['groups']} both={_both['groups']}")
        check(f"V213k {_nm9}: strokeGroups still accounts for every point in "
              f"every mode (Flip refuses a share when it does not)",
              all(v["sum"] == v["total"] for v in _seen9.values()),
              "; ".join(f"{k}:{v['sum']}/{v['total']}" for k, v in _seen9.items()))
    _br9.close()


# ---------------------------------------------------------------------------
# V213l — preview speed changes the replay CLOCK, and never the drawing.
#
# THE "NOT IN THE PAYLOAD" ASSERTION IS THE POINT, and it is the exact opposite
# of V213f's. Pause handling describes the WORK, so a viewer must get the
# author's choice and it is serialized. Preview speed describes the act of
# REVIEWING — it is zoom, not content — so posting it would impose one author's
# review habits on everyone who opens the link. The two settings sit one row
# apart in the same drawer and go opposite ways on purpose.
#
# Nothing touches the stored `t` values: only the wall-clock-to-timeline
# conversion is scaled, so a fast preview cannot rewrite the timing that IS the
# artifact. Measured as wall clock across a real take rather than by reading the
# rate back — a variable that scales nothing would pass any read-back check.
print("\nV213l — preview speed scales the clock, not the drawing")

import time as _time

with sync_playwright() as _b10:
    _br10 = _b10.chromium.launch()
    _c10 = _br10.new_context(viewport={"width": 1100, "height": 900})
    _p10 = _c10.new_page()
    _p10.goto(BASE + "/", wait_until="load"); _p10.wait_for_timeout(800)
    _p10.evaluate("() => localStorage.clear()")
    _p10.reload(wait_until="load"); _p10.wait_for_timeout(800)
    _p10.click("#recordBtn"); _p10.wait_for_timeout(300)
    _bx10 = _p10.locator("#canvas").bounding_box()
    for _k, (_x0, _y0) in enumerate(((80, 80), (80, 300))):
        _p10.mouse.move(_bx10["x"] + _x0, _bx10["y"] + _y0); _p10.mouse.down()
        for _i in range(1, 12):
            _p10.mouse.move(_bx10["x"] + _x0 + _i * 10, _bx10["y"] + _y0 + _i * 4)
        _p10.mouse.up()
        if _k == 0:
            # A LONG pause on purpose. This was 900ms, giving a ~430ms timeline
            # and wall times of 300-1000ms — small enough that a few frames of
            # rAF jitter could close the gap between 2x and 1x, and it FAILED
            # inside a release batch while passing standalone. Timing assertions
            # want a signal well above the noise, not a looser threshold: a
            # wider tolerance would still pass a build where speed did nothing.
            _p10.wait_for_timeout(2600)
    _p10.wait_for_timeout(200)
    _p10.click("#recordBtn"); _p10.wait_for_timeout(700)

    # KEEP the pause, or this suite's own default defeats this assertion.
    # pauseMode ships as 'tight', which caps every idle gap at 50ms — so the
    # 2,600ms pause drawn above was compressed straight back out and the
    # timeline stayed ~415ms however long the pause got. Lengthening the take
    # without this line did nothing at all, which is a neat demonstration that
    # V213f's feature is real and an easy way to write a timing test that can
    # never be strengthened.
    _p10.evaluate("() => setPauseMode('keep')")
    _tl = _p10.evaluate("() => getPlaybackDuration()")
    _tsBefore = _p10.evaluate("() => strokes.map(s => s.t)")

    _wall = {}
    for _rate in (1, 2, 0.5):
        _p10.evaluate("(r) => setReplayRate(r)", _rate)
        _t0 = _time.time()
        _p10.click("#playBtn")
        _p10.wait_for_function("() => !playing", timeout=20000)
        _wall[_rate] = (_time.time() - _t0) * 1000

    check("V213l gate: the take is long enough that timing dominates jitter "
          "(a short take is what made this assertion flaky in a release batch)",
          _tl > 2000, f"timeline duration {_tl}ms")
    check("V213l 2x replays in about half the wall time of 1x, and 0.5x in "
          "about double (the clock is scaled, not the data)",
          _wall[2] < _wall[1] * 0.75 and _wall[0.5] > _wall[1] * 1.3,
          f"0.5x={_wall[0.5]:.0f}ms, 1x={_wall[1]:.0f}ms, 2x={_wall[2]:.0f}ms")
    check("V213l the stored per-point timings are UNCHANGED by any of it "
          "(the recorded timing is the artifact)",
          _p10.evaluate("() => strokes.map(s => s.t)") == _tsBefore,
          f"{len(_tsBefore)} timestamps compared")
    check("V213l the rate is NOT written into the payload — preview speed "
          "describes reviewing, not the work (contrast V213f's pauseMode)",
          _p10.evaluate("() => Object.keys(serializeSkribl())"
                        ".filter(k => /rate|speed/i.test(k))") == [],
          "no rate/speed key in serializeSkribl()")

    _p10.click("#tuneBtn"); _p10.wait_for_timeout(300)
    _p10.evaluate("() => { const b = document.querySelector("
                  "'#speedSeg [data-rate=\"2\"]'); if (b) b.click(); }")
    _p10.wait_for_timeout(200)
    check("V213l the Preview speed seg writes through to the replay rate",
          _p10.evaluate("() => replayRate") == 2,
          f"replayRate={_p10.evaluate('() => replayRate')}")
    _p10.close(); _c10.close()
    _br10.close()


# ---------------------------------------------------------------------------
# V213m — brush presets, expressed entirely in per-point size and colour.
#
# NO PAYLOAD FIELD, same as shapes and mirror. The player replays by calling
# drawLine with the stored colour and width and has no notion of a brush; a
# preset therefore SHAPES those numbers at capture time and replays identically
# on a player that has never heard of lib/brushes.js. The schema assertion is
# what catches that changing.
#
# THE PENCIL TAPER IS THE ONLY PRESET THAT NEEDS MOTION, and it is measured in
# pixels per POINT rather than per millisecond: Pad captures on mouse/touch move
# and Flip on pointermove at whatever rate the device reports, so a clock-based
# taper would draw the same gesture differently on a 60Hz and a 120Hz screen.
# Pinned by drawing the SAME gesture at two point spacings and requiring the
# fast one to come out narrower.
#
# A stroke's first point resets the taper reference. Carrying it across strokes
# tapers the start of each new line by however far the pointer travelled since
# the last one — on a long reposition, the whole canvas, drawing the first
# segment hairline-thin.
print("\nV213m — brush presets shape width and opacity, not the format")

_BRUSH_Q = """() => {
  const src = (typeof strokes !== 'undefined' && strokes.length) ? strokes : frames[idx].strokes;
  const g = (typeof strokeGroups !== 'undefined' && strokeGroups.length)
    ? strokeGroups[strokeGroups.length-1] : frames[idx].strokeGroups.slice(-1)[0];
  const pts = src.slice(src.length-g);
  const sizes = pts.map(p=>p.size);
  const alpha = c => { const m=/rgba\\([^,]+,[^,]+,[^,]+,\\s*([\\d.]+)\\)/.exec(c); return m?+m[1]:1; };
  const allowed=['x','y','color','size','t','start','erase'];
  const extra=[];
  for(const p of pts) for(const k of Object.keys(p))
    if(allowed.indexOf(k)===-1 && extra.indexOf(k)===-1) extra.push(k);
  return {n:pts.length,
          meanSize:+(sizes.reduce((a,b)=>a+b,0)/sizes.length).toFixed(2),
          alpha:alpha(pts[0].color), extra:extra};
}"""

def _bstroke(_pg, _sel, _fast):
    _b = _pg.locator(_sel).bounding_box()
    _pg.mouse.move(_b["x"]+80, _b["y"]+120); _pg.mouse.down()
    _step = 34 if _fast else 5
    for _i in range(1, 16):
        _pg.mouse.move(_b["x"]+80+_i*_step, _b["y"]+120+(_i % 3)*4)
    _pg.mouse.up(); _pg.wait_for_timeout(250)

with sync_playwright() as _b11:
    _br11 = _b11.chromium.launch()
    for _nm11, _path11, _sel11, _rec11 in (
        ("pad", "/", "#canvas", True), ("flip", "/flip", "#pad", False),
    ):
        _c11 = _br11.new_context(viewport={"width": 1200, "height": 950})
        _p11 = _c11.new_page()
        _p11.goto(BASE + _path11, wait_until="load"); _p11.wait_for_timeout(900)
        _p11.evaluate("() => localStorage.clear()")
        _p11.reload(wait_until="load"); _p11.wait_for_timeout(900)
        if _rec11:
            _p11.click("#recordBtn"); _p11.wait_for_timeout(300)

        _got11 = {}
        for _brush in ("pen", "marker", "pencil", "airbrush"):
            _p11.evaluate("(b) => document.querySelector("
                          "'#brushSeg [data-brush=\"' + b + '\"]').click()", _brush)
            _p11.wait_for_timeout(150)
            _bstroke(_p11, _sel11, False)
            _got11[_brush] = _p11.evaluate(_BRUSH_Q)

        check(f"V213m {_nm11}: the four presets give four different widths "
              f"(marker wider than pen, pencil thinner, airbrush widest)",
              _got11["pencil"]["meanSize"] < _got11["pen"]["meanSize"]
              < _got11["marker"]["meanSize"] < _got11["airbrush"]["meanSize"],
              "; ".join(f"{k}:{v['meanSize']}" for k, v in _got11.items()))
        check(f"V213m {_nm11}: opacity is carried in the stored COLOUR, in the "
              f"same rgba() shape parseStrokeAlpha already reads",
              _got11["pen"]["alpha"] == 1 and _got11["marker"]["alpha"] < 1
              and _got11["airbrush"]["alpha"] < _got11["marker"]["alpha"],
              "; ".join(f"{k}:{v['alpha']}" for k, v in _got11.items()))
        check(f"V213m {_nm11}: no brush writes a field outside the replay schema "
              f"(the player must not need to know brushes exist)",
              all(v["extra"] == [] for v in _got11.values()),
              "; ".join(f"{k}:{v['extra']}" for k, v in _got11.items()))

        # The taper: same gesture, wider point spacing.
        _p11.evaluate("() => document.querySelector("
                      "'#brushSeg [data-brush=\"pencil\"]').click()")
        _p11.wait_for_timeout(150)
        _bstroke(_p11, _sel11, True)
        _fast11 = _p11.evaluate(_BRUSH_Q)
        check(f"V213m {_nm11}: the pencil TAPERS with speed — the same gesture "
              f"drawn faster captures narrower points",
              _fast11["meanSize"] < _got11["pencil"]["meanSize"] * 0.85,
              f"slow {_got11['pencil']['meanSize']} -> fast {_fast11['meanSize']}")
        _p11.close(); _c11.close()
    _br11.close()


# ---------------------------------------------------------------------------
# V213n — selection: marquee a region, move what is inside, undo it.
#
# SELECTION IS BY STROKE GROUP, never by point. A stroke is one gesture; moving
# half of one splits a line down the middle and leaves the replay drawing a
# segment between the halves — the same connecting-line failure as the mirror
# bug, and just as baked into the payload. Groups are what strokeGroups already
# records, so this needed no new bookkeeping, and the point/group totals must
# come out of a move completely unchanged.
#
# THE UNDO ASSERTION IS THE ONE THAT FOUND A REAL BUG. makeHistoryState() does
# `strokes.slice()`, which copies the ARRAY and not the point objects — every
# stroke lives in the snapshot and in `strokes` at the same address. Every other
# writer in this codebase APPENDS points, so nothing had ever mutated an
# existing one and the aliasing had never mattered. A selection move mutates x/y
# in place, so it edited the undo state too and Ctrl+Z restored the moved
# position: a silent no-op that reads as undo being broken rather than the move
# being wrong. Fixed by snapshotting FIRST and only then swapping the selected
# points for clones — cloning first captures the clones and fails identically
# one step later.
print("\nV213n — selection moves whole strokes, and undo really undoes it")

_SEL_Q = """() => ({n:strokes.length, groups:strokeGroups.length,
  sum:strokeGroups.reduce((a,b)=>a+b,0),
  minX:Math.round(Math.min(...strokes.map(p=>p.x))),
  maxX:Math.round(Math.max(...strokes.map(p=>p.x)))})"""

with sync_playwright() as _b12:
    _br12 = _b12.chromium.launch()
    _c12 = _br12.new_context(viewport={"width": 1200, "height": 950})
    _p12 = _c12.new_page()
    _p12.goto(BASE + "/", wait_until="load"); _p12.wait_for_timeout(900)
    _p12.evaluate("() => localStorage.clear()")
    _p12.reload(wait_until="load"); _p12.wait_for_timeout(900)
    _p12.click("#recordBtn"); _p12.wait_for_timeout(300)

    def _sstroke(_x0, _y0):
        _b = _p12.locator("#canvas").bounding_box()
        _p12.mouse.move(_b["x"]+_x0, _b["y"]+_y0); _p12.mouse.down()
        for _i in range(1, 12):
            _p12.mouse.move(_b["x"]+_x0+_i*6, _b["y"]+_y0+(_i % 3)*5)
        _p12.mouse.up(); _p12.wait_for_timeout(200)

    def _sdrag2(_x0, _y0, _x1, _y1):
        _b = _p12.locator("#canvas").bounding_box()
        _p12.mouse.move(_b["x"]+_x0, _b["y"]+_y0); _p12.mouse.down()
        for _i in range(1, 13):
            _p12.mouse.move(_b["x"]+_x0+(_x1-_x0)*_i/12, _b["y"]+_y0+(_y1-_y0)*_i/12)
        _p12.mouse.up(); _p12.wait_for_timeout(350)

    _sstroke(80, 80)      # stroke A, upper left
    _sstroke(80, 400)     # stroke B, lower left
    _two = _p12.evaluate(_SEL_Q)
    check("V213n gate: two separate strokes on the canvas to select between",
          _two["groups"] == 2 and _two["sum"] == _two["n"],
          f"{_two['groups']} groups, {_two['n']} points")

    _p12.evaluate("() => setTool('select')"); _p12.wait_for_timeout(200)
    _sdrag2(50, 50, 300, 200)          # marquee around A only
    check("V213n a marquee drag selects the strokes it touches",
          _p12.evaluate("() => SkriblSelectTool.hasSelection()") is True,
          "selection is live")

    # Drag from the CENTRE of the real selection: guessing a start point in CSS
    # coordinates lands outside the bounds, which correctly begins a NEW marquee
    # and clears the selection — a probe bug that looks exactly like a dead tool.
    _box12 = _p12.locator("#canvas").bounding_box()
    _sc = _p12.evaluate("() => getCanvasLogicalSize().width") / _box12["width"]
    _bb = _p12.evaluate("""() => {
      const xs = strokes.slice(0, strokeGroups[0]).map(p=>p.x);
      const ys = strokes.slice(0, strokeGroups[0]).map(p=>p.y);
      return {cx:(Math.min(...xs)+Math.max(...xs))/2, cy:(Math.min(...ys)+Math.max(...ys))/2};
    }""")
    _before12 = _p12.evaluate(_SEL_Q)
    _sdrag2(_bb["cx"]/_sc, _bb["cy"]/_sc, _bb["cx"]/_sc + 240, _bb["cy"]/_sc)
    _after12 = _p12.evaluate(_SEL_Q)

    check("V213n moving the selection shifts it across the canvas",
          _after12["maxX"] - _before12["maxX"] > 150,
          f"max x {_before12['maxX']} -> {_after12['maxX']}")
    check("V213n ...without changing the point count or the group bookkeeping "
          "(a move must not split or drop a stroke)",
          _after12["n"] == _before12["n"] and
          _after12["groups"] == _before12["groups"] and
          _after12["sum"] == _after12["n"],
          f"{_after12['n']} points / {_after12['groups']} groups / "
          f"groups sum {_after12['sum']}")
    check("V213n the UNSELECTED stroke stays put (a marquee that moves "
          "everything is not a selection)",
          _after12["minX"] == _before12["minX"],
          f"min x unchanged at {_after12['minX']}")

    _p12.click("#undoBtn"); _p12.wait_for_timeout(400)
    _undone = _p12.evaluate(_SEL_Q)
    check("V213n undo restores the pre-move coordinates EXACTLY "
          "(snapshot-then-clone; the other order silently aliases and undo "
          "becomes a no-op)",
          _undone["maxX"] == _before12["maxX"] and _undone["minX"] == _before12["minX"],
          f"max x back to {_undone['maxX']} (was {_before12['maxX']} "
          f"before the move, {_after12['maxX']} after)")

    _p12.evaluate("() => setTool('pen')"); _p12.wait_for_timeout(200)
    check("V213n leaving the Select tool drops the selection "
          "(an invisible selection a later drag would move is worse than "
          "making the user re-pick)",
          _p12.evaluate("() => SkriblSelectTool.hasSelection()") is False)
    _p12.close(); _c12.close()
    _br12.close()


# ---------------------------------------------------------------------------
# V214a — a CANCELLED touch gesture really ends. (External review, v213.)
#
# editor_music.js installed window-level touchmove/touchend pairs for three
# independent drags and cleaned up on touchend ONLY. A browser or OS can CANCEL
# a touch sequence instead of ending it — a system gesture, an incoming call, a
# pointer taken over by scrolling — and a cancelled sequence never fires
# touchend. The move listener therefore stayed installed and the handle stayed
# flagged dragging, so the next unrelated touch went on moving a trim whose
# gesture was already over.
#
# REPRODUCED BEFORE FIXING: after touchcancel, a further move took trimStart
# from 1.129 to 3.386 with .dragging still set.
#
# The reviewer was right that this crosses the project's defences. Several
# neighbouring gestures already handled both (gripEnd in app.js and flip.js,
# endDraw in editor_draw.js), so editor_music.js showed exactly the asymmetry
# the review described — but it was NOT the only place with it. A full-tree
# audit found the same defect family beyond that file: 3 unpaired handlers in
# editor_music.js, 4 in flip.js, 2 in app.js (the Loop Detail pan and the
# playback scrub).
#
# WHAT THAT AUDIT PROVES, PRECISELY. It is a SYNTACTIC pairing: for each file,
# every handler named in an addEventListener('touchend', H) was checked for a
# matching addEventListener('touchcancel', H). So the claim is "every identified
# stateful drag/gesture cleanup handler is now paired" — not that every possible
# touch lifecycle in the application has been proven correct. A cleanup reached
# some other way, or a gesture whose listener is registered dynamically under a
# name this scan does not see, would not appear in it.
#
# NOT asserted by looking for a touchcancel listener in the source, on the
# reviewer's explicit advice and this project's own history: that assertion
# stays green against a listener wired to the wrong cleanup. Each path is driven
# as a real gesture, cancelled, then moved AGAIN — the trim must not follow.
#
# Left deliberately unpaired: the three scheduleAutosave touchend handlers in
# app.js. Those are save triggers, not drag cleanups; nothing keeps state alive
# after them, so pairing would be cargo-culting the shape of the fix.
print("\nV214a — touchcancel ends a drag, on every music gesture path")

_TOUCH = """([sel, type, x, y]) => {
  const el = document.querySelector(sel);
  const t = new Touch({identifier: 1, target: el, clientX: x, clientY: y});
  const empty = (type === 'touchend' || type === 'touchcancel');
  el.dispatchEvent(new TouchEvent(type, {
    touches: empty ? [] : [t], targetTouches: empty ? [] : [t],
    changedTouches: [t], bubbles: true, cancelable: true, view: window}));
}"""
_TSTATE = ("() => ({start:+trimStart.toFixed(3), end:+trimEnd.toFixed(3), "
           "dragging: !!document.querySelector('.dragging')})")

import math as _m, struct as _st, wave as _wv
_TCWAV = "/tmp/v214_tc.wav"
with _wv.open(_TCWAV, "wb") as _w:
    _w.setnchannels(1); _w.setsampwidth(2); _w.setframerate(44100)
    _buf = bytearray()
    for _i in range(12 * 44100):
        _buf += _st.pack("<h", int(16000 * _m.sin(2 * _m.pi * 220 * _i / 44100)))
    _w.writeframes(bytes(_buf))

with sync_playwright() as _b14:
    _br14 = _b14.chromium.launch()
    _c14 = _br14.new_context(viewport={"width": 900, "height": 900}, has_touch=True)
    _p14 = _c14.new_page()
    _p14.goto(BASE + "/", wait_until="load"); _p14.wait_for_timeout(800)
    _p14.evaluate("() => localStorage.clear()")
    _p14.set_input_files("#musicInput", _TCWAV)
    _p14.wait_for_timeout(3000)
    _p14.evaluate("() => openDrawer('music')"); _p14.wait_for_timeout(600)
    _p14.click("#fineTuneToggle"); _p14.wait_for_timeout(500)

    # Three INDEPENDENT gesture paths, so removing cancellation from one
    # reddens only that one. Mutation-tested per path, per the review.
    for _pname, _psel in (("zoom handle", "#zoomHandleStart"),
                          ("trim handle", "#handleStart"),
                          ("range window", "#musicRange")):
        # The RANGE window slides the whole selection, so it needs room on both
        # sides: reset to the full track and it cannot move at all, which makes
        # "unchanged after cancel" true for the wrong reason — the exact class of
        # vacuous pass this review warned about. The handle paths want the full
        # track so they have somewhere to drag TO.
        if _psel == "#musicRange":
            _p14.evaluate("() => { trimStart = 2; trimEnd = 6; updateTrimUI(); }")
        else:
            _p14.evaluate("() => { trimStart = 0; trimEnd = audioDuration; updateTrimUI(); }")
        _p14.wait_for_timeout(150)
        _bx = _p14.locator(_psel).bounding_box()
        if not _bx:
            check(f"V214a {_pname}: element is laid out", False, "no bounding box")
            continue
        _x, _y = _bx["x"] + _bx["width"] / 2, _bx["y"] + _bx["height"] / 2
        _pre = _p14.evaluate(_TSTATE)
        _p14.evaluate(_TOUCH, [_psel, "touchstart", _x, _y]); _p14.wait_for_timeout(70)
        _p14.evaluate(_TOUCH, [_psel, "touchmove", _x + 60, _y]); _p14.wait_for_timeout(70)
        _live = _p14.evaluate(_TSTATE)
        # GATE: if the drag never took hold, "does not move after cancel" is
        # satisfied by a gesture that never started, and proves nothing.
        check(f"V214a {_pname} gate: the drag is live AND has already moved the "
              f"trim (a gesture that never moved makes the check below vacuous)",
              _live["dragging"] is True and
              (_live["start"] != _pre["start"] or _live["end"] != _pre["end"]),
              f"dragging={_live['dragging']}, trim {_pre['start']}-{_pre['end']} "
              f"-> {_live['start']}-{_live['end']}")

        _p14.evaluate(_TOUCH, [_psel, "touchcancel", _x + 60, _y]); _p14.wait_for_timeout(120)
        _atCancel = _p14.evaluate(_TSTATE)
        _p14.evaluate(_TOUCH, [_psel, "touchmove", _x + 190, _y]); _p14.wait_for_timeout(120)
        _after = _p14.evaluate(_TSTATE)

        check(f"V214a {_pname}: a move AFTER touchcancel no longer changes the trim",
              _after["start"] == _atCancel["start"] and _after["end"] == _atCancel["end"],
              f"at cancel {_atCancel['start']}-{_atCancel['end']}, "
              f"after a further move {_after['start']}-{_after['end']}")
        check(f"V214a {_pname}: ...and the dragging state is cleared by the cancel",
              _atCancel["dragging"] is False and _after["dragging"] is False,
              f"dragging at cancel={_atCancel['dragging']}, after={_after['dragging']}")
        # ISOLATE THE PATHS. Every one of these drags puts its listener on
        # WINDOW, so a leak in one keeps firing during the next and all three
        # assertions go red however few paths are actually broken — which is
        # what happened on the first mutation run and would have hidden which
        # path the fix belonged to. A touchend clears anything still installed,
        # because touchend cleanup was never the half that was missing.
        _p14.evaluate(_TOUCH, [_psel, "touchend", _x, _y]); _p14.wait_for_timeout(80)
    _p14.close(); _c14.close()
    _br14.close()


# ---------------------------------------------------------------------------
# V214b — the touch-lifecycle audit itself, as an assertion.
#
# WHY THIS EXISTS. The v214a audit was described as whole-tree and was not: it
# matched `window.addEventListener('touchend', H)` only, so every ELEMENT-LOCAL
# registration was invisible to it. A second review pass then found two the scan
# could never have seen — `sheet.addEventListener` in editor_menu.js (a stateful
# swipe that kept `transition: none` and its translateY, and carried on dragging
# after the cancel: reproduced 50px -> 90px) and `canvasWrap.addEventListener`
# in editor_photo.js (the eraser ring left painted with no finger near it).
#
# The lesson is the one this project keeps relearning in a new costume: an audit
# that matches a RECEIVER NAME is the same mistake as an assertion that matches
# a word instead of a mechanism. So the audit is no longer a thing I ran once
# and reported — it runs every time, over any receiver.
#
# ALLOWLIST, NOT A COUNT. A ratchet on the number of unpaired handlers would go
# green again by pairing something irrelevant. Each remaining one is named, with
# the reason it is not a stateful gesture cleanup.
print("\nV214b — every touchend cleanup is paired with touchcancel")

_TOUCH_ALLOW = {
    # Autosave triggers, not drag cleanups: nothing stays alive after them, so a
    # cancelled touch simply does not schedule a save it did not need to. Pairing
    # these would be copying the shape of the fix rather than its substance.
    ("canvas", "scheduleAutosave"),
    ("musicTrack", "scheduleAutosave"),
    ("zoomTrackWrap", "scheduleAutosave"),
}

_pat_end = _re2.compile(
    r"([A-Za-z_$][\w$.]*)\.addEventListener\(\s*'touchend'\s*,\s*"
    r"([A-Za-z_$][\w$]*|\(\)\s*=>|function)")
_pat_can = _re2.compile(
    r"([A-Za-z_$][\w$.]*)\.addEventListener\(\s*'touchcancel'\s*,\s*"
    r"([A-Za-z_$][\w$]*|\(\)\s*=>|function)")

_unpaired_all = []
for _jf in sorted((ROOT / "skribl" / "static").rglob("*.js")):
    _src = _jf.read_text(encoding="utf-8")
    # Matched by RECEIVER, not by handler name. The menu sheet deliberately uses
    # a DIFFERENT function for cancel — onTouchEnd dismisses the menu past 80px,
    # and a gesture the OS took away must not commit the dismissal the user never
    # finished — so a name-based match flags the correct fix as a defect, which
    # it did on the first run of this assertion.
    #
    # The trade is stated rather than hidden: this asks "does this element handle
    # touchcancel at all", so an element with two gestures where only one is
    # paired would pass. That is a weaker invariant than per-gesture pairing, and
    # it is the reason V214a's per-path BEHAVIOURAL pins exist alongside it. This
    # assertion catches the omission; those catch the semantics.
    _can_receivers = {r for r, _ in _pat_can.findall(_src)}
    for _r, _h in _pat_end.findall(_src):
        if _r in _can_receivers:
            continue
        if (_r, _h) in _TOUCH_ALLOW:
            continue
        _unpaired_all.append(f"{_jf.name}:{_r}.{_h}")

check("V214b every touchend handler on ANY receiver is paired with a "
      "touchcancel handler, or named in the allowlist with a reason",
      _unpaired_all == [],
      "; ".join(_unpaired_all) if _unpaired_all
      else "no unpaired stateful touch cleanups")

# The allowlist must stay honest: an entry that no longer exists is a stale
# exemption that would hide a real one added under the same name later.
_all_js = "\n".join((_f).read_text(encoding="utf-8")
                     for _f in (ROOT / "skribl" / "static").rglob("*.js"))
_stale = [f"{r}.{h}" for r, h in _TOUCH_ALLOW
          if f"{r}.addEventListener('touchend', {h})" not in _all_js]
check("V214b ...and no allowlisted exemption is stale "
      "(an exemption for code that no longer exists hides the next one)",
      _stale == [], "; ".join(_stale) if _stale else "all 3 exemptions still real")


# ---------------------------------------------------------------------------
# V214c — the menu sheet and the eraser cursor survive a cancelled touch.
#
# Both found by a SECOND review pass after v214a was called complete, and both
# invisible to that audit because they register on an ELEMENT rather than on
# window. Behavioural, per path, as with V214a.
#
# The menu sheet is the one that matters: onTouchEnd DISMISSES the menu past
# 80px, so the fix is a separate onTouchCancel that resets and stops. Wiring
# cancel to onTouchEnd — the obvious one-line version, and what the report
# suggested — would let a gesture the OS took away complete a dismissal the user
# never finished. The pin therefore checks the menu is still OPEN afterwards,
# which is what separates "reset" from "commit".
print("\nV214c — a cancelled swipe resets the sheet; a cancelled touch clears the ring")

_SHEET = """() => {
  const s = document.getElementById('menuSheet');
  return {transition: s.style.transition, transform: s.style.transform,
          open: !document.getElementById('menuOverlay').hidden};
}"""

with sync_playwright() as _b15:
    _br15 = _b15.chromium.launch()
    _c15 = _br15.new_context(viewport={"width": 390, "height": 800}, has_touch=True)
    _p15 = _c15.new_page()
    _p15.goto(BASE + "/", wait_until="load"); _p15.wait_for_timeout(800)
    _p15.evaluate("() => localStorage.clear()")

    _p15.click("#menuBtn"); _p15.wait_for_timeout(500)
    _mb = _p15.locator("#menuSheet").bounding_box()
    _mx, _my = _mb["x"] + _mb["width"] / 2, _mb["y"] + 20   # inside the 60px grab zone

    _p15.evaluate(_TOUCH, ["#menuSheet", "touchstart", _mx, _my]); _p15.wait_for_timeout(60)
    _p15.evaluate(_TOUCH, ["#menuSheet", "touchmove", _mx, _my + 50]); _p15.wait_for_timeout(60)
    _mid = _p15.evaluate(_SHEET)
    check("V214c menu gate: the swipe is live and has translated the sheet",
          "translateY" in (_mid["transform"] or "") and _mid["transition"] == "none",
          f"transform={_mid['transform']!r}, transition={_mid['transition']!r}")

    _p15.evaluate(_TOUCH, ["#menuSheet", "touchcancel", _mx, _my + 50]); _p15.wait_for_timeout(120)
    _mcan = _p15.evaluate(_SHEET)
    _p15.evaluate(_TOUCH, ["#menuSheet", "touchmove", _mx, _my + 90]); _p15.wait_for_timeout(120)
    _mafter = _p15.evaluate(_SHEET)

    check("V214c the cancel RESETS the sheet's transform and re-enables its "
          "transition (it kept translateY and transition:none before)",
          _mcan["transform"] in ("", None) and _mcan["transition"] in ("", None),
          f"transform={_mcan['transform']!r}, transition={_mcan['transition']!r}")
    check("V214c ...and a later move no longer drags the cancelled swipe "
          "(reproduced at translateY(50px) -> translateY(90px))",
          _mafter["transform"] in ("", None),
          f"transform after a further move = {_mafter['transform']!r}")
    check("V214c ...and the cancel does NOT dismiss the menu — a gesture the OS "
          "took away must not commit the action the user never finished",
          _mcan["open"] is True and _mafter["open"] is True,
          f"menu open at cancel={_mcan['open']}, after={_mafter['open']}")

    # ---- eraser ring
    _p15.evaluate("() => { const m=document.getElementById('menuOverlay'); if(m) m.hidden=true; }")
    _p15.wait_for_timeout(200)
    _p15.evaluate("() => setTool('eraser')"); _p15.wait_for_timeout(200)
    _cw = _p15.locator(".canvas-wrap").bounding_box()
    _ex, _ey = _cw["x"] + 120, _cw["y"] + 120
    _ring = "() => { const c=document.getElementById('eraserCursor'); return c ? c.style.display : null; }"
    _p15.evaluate(_TOUCH, [".canvas-wrap", "touchstart", _ex, _ey]); _p15.wait_for_timeout(60)
    _p15.evaluate(_TOUCH, [".canvas-wrap", "touchmove", _ex + 40, _ey]); _p15.wait_for_timeout(60)
    _shown = _p15.evaluate(_ring)
    check("V214c eraser gate: the ring is actually shown during the touch",
          _shown == "block", f"display={_shown!r}")
    _p15.evaluate(_TOUCH, [".canvas-wrap", "touchcancel", _ex + 40, _ey]); _p15.wait_for_timeout(150)
    check("V214c a cancelled touch clears the eraser ring "
          "(it stayed painted with no finger near it)",
          _p15.evaluate(_ring) == "none", f"display={_p15.evaluate(_ring)!r}")
    _p15.close(); _c15.close()
    _br15.close()


# ---------------------------------------------------------------------------
# V214d — a SUPERSEDED decode cannot overwrite the current track. (Review #1.)
#
# musicSelectionSeq existed and was checked twice in Pad's selection handler —
# but both checks run BEFORE decodeAudioData is awaited, so they prove the
# selection was current when the decode STARTED, which is not the question. Flip
# had no token in decodeForWaveform at all.
#
# NOT A STALE WAVEFORM. Reproduced with A=3.00s and B=9.00s: on Pad the buffer
# reverted to A while audioDuration still read B, so the track shown and the
# audio the poster crops from were different recordings. On Flip the stale
# completion rewrote audioDuration AND the trim window, resetting the loop to
# the old track's length.
#
# CONTROLLED COMPLETION ORDER, not sleeps. decodeAudioData is gated into a queue
# and released by index, so "B finishes first, A finishes last" is exact rather
# than hoped for — a timing-based version would pass whenever the machine
# happened to order them the other way.
print("\nV214d — an older decode cannot replace a newer track's buffer")

_DGATE = """
window.__dq = [];
(function () {
  const C = window.AudioContext || window.webkitAudioContext;
  const orig = C.prototype.decodeAudioData;
  C.prototype.decodeAudioData = function (ab) {
    const ctx = this;
    return new Promise((res, rej) => {
      window.__dq.push(() => orig.call(ctx, ab).then(res, rej));
    });
  };
})();
window.__release = (i) => { const f = window.__dq[i]; if (f) f(); };
"""
_DSTATE = """() => ({
  buf: currentAudioBuffer ? +currentAudioBuffer.duration.toFixed(2) : null,
  dur: (typeof audioDuration === 'number') ? +audioDuration.toFixed(2) : null,
})"""

import wave as _wv2, struct as _st2, math as _m2
def _mkwav(_path, _secs, _freq):
    with _wv2.open(_path, "wb") as _w:
        _w.setnchannels(1); _w.setsampwidth(2); _w.setframerate(44100)
        _b = bytearray()
        for _i in range(int(_secs * 44100)):
            _b += _st2.pack("<h", int(15000 * _m2.sin(2 * _m2.pi * _freq * _i / 44100)))
        _w.writeframes(bytes(_b))
_WA, _WB = "/tmp/v214_raceA.wav", "/tmp/v214_raceB.wav"
_mkwav(_WA, 3.0, 220); _mkwav(_WB, 9.0, 440)

with sync_playwright() as _b16:
    _br16 = _b16.chromium.launch()
    for _nm16, _path16 in (("pad", "/"), ("flip", "/flip")):
        _c16 = _br16.new_context(viewport={"width": 1100, "height": 900})
        _c16.add_init_script(_DGATE)
        _p16 = _c16.new_page()
        _p16.goto(BASE + _path16, wait_until="load"); _p16.wait_for_timeout(900)
        _p16.evaluate("() => localStorage.clear()")
        _p16.set_input_files("#musicInput", _WA); _p16.wait_for_timeout(700)
        _p16.set_input_files("#musicInput", _WB); _p16.wait_for_timeout(700)

        # GATE: two decodes really are in flight, or "B wins" proves nothing.
        check(f"V214d {_nm16} gate: both decodes are in flight and gated",
              _p16.evaluate("() => window.__dq.length") == 2,
              f"queued {_p16.evaluate('() => window.__dq.length')}")

        _p16.evaluate("() => window.__release(1)"); _p16.wait_for_timeout(700)
        _afterB = _p16.evaluate(_DSTATE)
        check(f"V214d {_nm16} gate: B (9.00s) landed and is the current track",
              _afterB["buf"] == 9.0, f"buffer {_afterB['buf']}s")

        _p16.evaluate("() => window.__release(0)"); _p16.wait_for_timeout(900)
        _afterA = _p16.evaluate(_DSTATE)
        check(f"V214d {_nm16}: A (3.00s) finishing LAST does not replace B's "
              f"buffer — the poster crops from this, so a stale one ships "
              f"different audio than the UI shows",
              _afterA["buf"] == 9.0,
              f"buffer after the superseded decode landed: {_afterA['buf']}s "
              f"(want 9.0)")
        check(f"V214d {_nm16}: ...and buffer and duration still AGREE "
              f"(the split state was buffer=3.00s with duration=9.00s)",
              _afterA["buf"] == _afterA["dur"],
              f"buffer {_afterA['buf']}s vs audioDuration {_afterA['dur']}s")
        _p16.close(); _c16.close()
    _br16.close()


# ---------------------------------------------------------------------------
# V214e — a superseded DOCUMENT load cannot write into the open one. (Review #2.)
#
# loadSkribl() starts five asynchronous chains — the base-snapshot Image, the
# music fetch, loadedmetadata, decodeAudioData, and a deferred writeAutosave —
# and none of them was tied to the document load that created it.
#
# Reproduced: load draft A (3.00s music), load draft B (9.00s), release B's
# decode then A's. A rewrote currentAudioBuffer, audioDuration AND trimEnd to
# A's values while B was the Skribl on screen — the user's open loop window
# replaced by one from a draft they had already navigated away from. That is a
# document-state corruption, not a stale preview: writeAutosave would then
# persist it.
#
# WIDER THAN V214d ON PURPOSE. V214d guards one selection handler; this is a
# generation token stamped once per load and checked at EVERY completion,
# because the failure mode is a callback nobody remembered to guard. The pin
# checks the three values that moved together, so a fix that guards the decode
# and forgets trimEnd still fails.
print("\nV214e — a stale document load cannot overwrite the open Skribl")

_LSTATE = """() => ({
  buf: currentAudioBuffer ? +currentAudioBuffer.duration.toFixed(2) : null,
  dur: (typeof audioDuration === 'number') ? +audioDuration.toFixed(2) : null,
  trimEnd: trimEnd != null ? +trimEnd.toFixed(2) : null,
  // The <audio> ELEMENT too, not just the decoded buffer. loadSkribl replaces
  // audioEl inside the FETCH callback, a separate async chain from the decode —
  // so a pin that only watches currentAudioBuffer leaves the fetch guard
  // untested, which is exactly what the mutation pass found.
  elDur: (audioEl && isFinite(audioEl.duration)) ? +audioEl.duration.toFixed(2) : null,
})"""

_LA, _LB = "/tmp/v214_loadA.wav", "/tmp/v214_loadB.wav"
_mkwav(_LA, 3.0, 220); _mkwav(_LB, 9.0, 440)

with sync_playwright() as _b17:
    _br17 = _b17.chromium.launch()
    _c17 = _br17.new_context(viewport={"width": 1100, "height": 900})
    _p17 = _c17.new_page()
    _p17.goto(BASE + "/", wait_until="load"); _p17.wait_for_timeout(900)
    _p17.evaluate("() => localStorage.clear()")

    _pay = {}
    for _n17, _f17 in (("A", _LA), ("B", _LB)):
        _p17.set_input_files("#musicInput", _f17)
        _p17.wait_for_timeout(2500)
        _pay[_n17] = _p17.evaluate("() => JSON.stringify(serializeSkribl())")

    _p17.evaluate(_DGATE)                       # same decode queue as V214d
    _p17.evaluate("(s) => loadSkribl(JSON.parse(s))", _pay["A"]); _p17.wait_for_timeout(400)
    _p17.evaluate("(s) => loadSkribl(JSON.parse(s))", _pay["B"]); _p17.wait_for_timeout(400)

    check("V214e gate: two document loads are in flight with gated decodes",
          _p17.evaluate("() => window.__dq.length") == 2,
          f"queued {_p17.evaluate('() => window.__dq.length')}")

    _p17.evaluate("() => window.__release(1)"); _p17.wait_for_timeout(700)
    _bState = _p17.evaluate(_LSTATE)
    check("V214e gate: B is loaded and is the document on screen (9.00s)",
          _bState["buf"] == 9.0 and _bState["trimEnd"] == 9.0,
          f"{_bState}")

    _p17.evaluate("() => window.__release(0)"); _p17.wait_for_timeout(900)
    _aState = _p17.evaluate(_LSTATE)
    check("V214e a superseded load's decode does not replace the open Skribl's "
          "buffer, duration OR trim window (all three moved together before)",
          _aState == _bState,
          f"B was {_bState}, after A's stale completion {_aState}")

    # ---- and the FETCH guard, which the scenario above never exercises.
    #
    # Found by the pre-seal mutation pass: removing loadSkribl's fetch guard
    # reddened nothing, because a data: URL fetch resolves long before the
    # second load starts, so A's fetch callback had always already run. The
    # guard was real code with no assertion behind it — decoration, by this
    # project's standard. Gating fetch as well as decode exercises it.
    #
    # It matters because the fetch callback is where audioEl is REPLACED, a
    # separate async chain from the decode: a stale one swaps the <audio>
    # element the transport plays from while the decoded buffer stays correct.
    _p17.evaluate("""() => {
      window.__fq = [];
      const orig = window.fetch;
      window.fetch = function (...a) {
        return new Promise((res, rej) => {
          window.__fq.push(() => orig.apply(window, a).then(res, rej));
        });
      };
      window.__frelease = (i) => { const f = window.__fq[i]; if (f) f(); };
    }""")
    _p17.evaluate("(s) => loadSkribl(JSON.parse(s))", _pay["A"]); _p17.wait_for_timeout(300)
    _p17.evaluate("(s) => loadSkribl(JSON.parse(s))", _pay["B"]); _p17.wait_for_timeout(300)
    check("V214e gate: two media FETCHES are in flight and gated",
          _p17.evaluate("() => window.__fq.length") >= 2,
          f"queued {_p17.evaluate('() => window.__fq.length')}")
    _p17.evaluate("() => window.__frelease(1)"); _p17.wait_for_timeout(500)
    _p17.evaluate("() => { let i = 0; while (window.__dq[i]) { window.__release(i); i++; } }")
    _p17.wait_for_timeout(700)
    _bFetch = _p17.evaluate(_LSTATE)
    _p17.evaluate("() => window.__frelease(0)"); _p17.wait_for_timeout(500)
    _p17.evaluate("() => { let i = 0; while (window.__dq[i]) { window.__release(i); i++; } }")
    _p17.wait_for_timeout(900)
    _aFetch = _p17.evaluate(_LSTATE)
    check("V214e a superseded load's media FETCH does not swap the <audio> "
          "element out from under the open Skribl",
          _aFetch["elDur"] == _bFetch["elDur"] and _aFetch["buf"] == _bFetch["buf"],
          f"before the stale fetch {_bFetch}, after {_aFetch}")

    # ---- and the BASE SNAPSHOT guard, the last of loadSkribl's five.
    #
    # Also found by the pre-seal mutation pass: removing it reddened nothing,
    # because the payloads above carry no baseSnapshot so that callback never
    # ran. A guard protecting a real path with no test behind it is decoration
    # by this project's standard, so the path gets a scenario instead.
    #
    # Two payloads with KNOWN, DIFFERENT snapshot colours, and the same img-src
    # queue used for the Flip image race. A wins the load order; the canvas must
    # still show B's colour, because a stale snapshot painting over the open
    # document is a silent overwrite of the drawing itself.
    _p17.evaluate("""() => {
      window.__iq = [];
      const d = Object.getOwnPropertyDescriptor(HTMLImageElement.prototype, 'src');
      Object.defineProperty(HTMLImageElement.prototype, 'src', {
        configurable: true,
        get(){ return d.get.call(this); },
        set(v){ const self = this; window.__iq.push(() => d.set.call(self, v)); }
      });
      window.__irelease = (i) => { const f = window.__iq[i]; if (f) f(); };
      window.__snap = (css) => {
        const c = document.createElement('canvas');
        const s = getCanvasLogicalSize();
        c.width = s.width; c.height = s.height;
        const g = c.getContext('2d'); g.fillStyle = css; g.fillRect(0, 0, c.width, c.height);
        return c.toDataURL();
      };
      window.__pix = () => {
        const s = getCanvasLogicalSize();
        const d2 = ctx.getImageData(Math.floor(s.width/2), Math.floor(s.height/2), 1, 1).data;
        return [d2[0], d2[1], d2[2]];
      };
    }""")
    _snapA = _p17.evaluate("() => window.__snap('#ff0000')")     # A: red
    _snapB = _p17.evaluate("() => window.__snap('#0000ff')")     # B: blue
    _p17.evaluate("""([a, b, sa, sb]) => {
      const A = JSON.parse(a), B = JSON.parse(b);
      A.baseSnapshot = sa; A.strokes = []; A.strokeGroups = [];
      B.baseSnapshot = sb; B.strokes = []; B.strokeGroups = [];
      window.__snapA = A; window.__snapB = B;
    }""", [_pay["A"], _pay["B"], _snapA, _snapB])
    # RELEASE BY RANGE, not by index. Each loadSkribl enqueues more than one
    # image (the snapshot plus other media), so "index 1 is B's" was wrong and
    # released one of A's — the gate caught it as a black canvas rather than
    # letting the real assertion pass for the wrong reason.
    _p17.evaluate("() => { window.__iq.length = 0; loadSkribl(window.__snapA); }")
    _p17.wait_for_timeout(500)
    _nA = _p17.evaluate("() => window.__iq.length")
    _p17.evaluate("() => loadSkribl(window.__snapB)")
    _p17.wait_for_timeout(500)
    _nAll = _p17.evaluate("() => window.__iq.length")
    check("V214e gate: both base-snapshot images are in flight and gated",
          _nA >= 1 and _nAll > _nA,
          f"A queued {_nA}, then {_nAll - _nA} more for B")
    _p17.evaluate("([a, n]) => { for (let i = a; i < n; i++) window.__irelease(i); }",
                  [_nA, _nAll])
    _p17.wait_for_timeout(700)
    _pixB = _p17.evaluate("() => window.__pix()")
    check("V214e gate: B's snapshot (blue) is the painted canvas",
          _pixB[2] > 200 and _pixB[0] < 60, f"centre pixel rgb{tuple(_pixB)}")
    _p17.evaluate("(a) => { for (let i = 0; i < a; i++) window.__irelease(i); }", _nA)
    _p17.wait_for_timeout(800)
    _pixA = _p17.evaluate("() => window.__pix()")
    check("V214e a superseded load's BASE SNAPSHOT does not paint over the open "
          "Skribl (a silent overwrite of the drawing itself)",
          _pixA == _pixB,
          f"canvas was rgb{tuple(_pixB)}, after A's stale snapshot rgb{tuple(_pixA)}")
    _p17.close(); _c17.close()
    _br17.close()


# ---------------------------------------------------------------------------
# V214f — a restored Flip draft reaches the SAME state as fresh selection.
# (Review #3.)
#
# applyPayload() clears currentAudioBuffer and ensureAudio() only builds the
# <audio> element, so the draft-FILE path restored musicData and a trim window
# with no decoded buffer behind them. The boot/autosave path has always called
# decodeForWaveform(); only loadDraftFile was missing it, which is why a page
# reload looked fine and opening the saved file did not.
#
# THE POST IS THE REAL DAMAGE, not the blank waveform. buildSharePayload()
# crops to the loop ONLY when currentAudioBuffer exists, and otherwise warns to
# the console and ships the whole sample. Measured on a 30s track trimmed to a
# 5s loop: 588,082 B posted after a fresh selection against 3,528,082 B after
# restoring that same draft — both reporting the same 5.00s loop. A user's saved
# work posted six times the audio, with nothing on screen to say so.
#
# COMPARED AGAINST FRESH SELECTION rather than against a fixed number: the
# claim is equivalence between two routes to the same state, so the assertion
# should fail if EITHER route changes.
print("\nV214f — a restored draft posts the same audio as a fresh selection")

_FSTATE = """() => {
  const pay = buildSharePayload();
  const m = (pay.frames && pay.frames[0] && pay.frames[0].music) || null;
  return {
    hasBuffer: !!currentAudioBuffer,
    trim: [trimStart != null ? +trimStart.toFixed(2) : null,
           trimEnd != null ? +trimEnd.toFixed(2) : null],
    postedSecs: m ? +((m.trimEnd - m.trimStart)).toFixed(2) : null,
    postedBytes: m && m.data ? m.data.length : null,
  };
}"""

_FW = "/tmp/v214_flipdraft.wav"
_mkwav(_FW, 30.0, 330)

with sync_playwright() as _b18:
    _br18 = _b18.chromium.launch()
    _c18 = _br18.new_context(viewport={"width": 1200, "height": 950})
    _p18 = _c18.new_page()
    _p18.goto(BASE + "/flip", wait_until="load"); _p18.wait_for_timeout(900)
    _p18.evaluate("() => localStorage.clear()")
    _p18.reload(wait_until="load"); _p18.wait_for_timeout(900)

    _bx18 = _p18.locator("#pad").bounding_box()
    _p18.mouse.move(_bx18["x"] + 80, _bx18["y"] + 80); _p18.mouse.down()
    for _i in range(1, 12):
        _p18.mouse.move(_bx18["x"] + 80 + _i * 9, _bx18["y"] + 80 + (_i % 3) * 6)
    _p18.mouse.up(); _p18.wait_for_timeout(200)

    _p18.set_input_files("#musicInput", _FW); _p18.wait_for_timeout(3500)
    _p18.evaluate("() => { trimStart = 2; trimEnd = 7; updateTrimUI(); }")
    _p18.wait_for_timeout(300)
    _freshS = _p18.evaluate(_FSTATE)

    # GATE: the fresh route must actually be cropping, or "restored matches
    # fresh" is satisfied by both routes shipping the full sample.
    check("V214f gate: a fresh selection crops to the loop before posting",
          _freshS["hasBuffer"] and _freshS["postedSecs"] == 5.0 and
          _freshS["postedBytes"] < 1_500_000,
          f"posted {_freshS['postedBytes']} B for a {_freshS['postedSecs']}s "
          f"loop out of a 30s source")

    _draft18 = _p18.evaluate("() => JSON.stringify(serializeFlip())")
    # The REAL loadDraftFile, not a hand-copied replica of its steps — an inline
    # copy diverged from the code the moment the fix landed and reported the fix
    # as ineffective.
    _p18.evaluate("""(s) => {
      const f = new File([s], 'test.skribl', {type: 'application/json'});
      loadDraftFile(f);
    }""", _draft18)
    _p18.wait_for_timeout(3000)
    _restS = _p18.evaluate(_FSTATE)

    check("V214f a restored draft has the decoded buffer a fresh selection has",
          _restS["hasBuffer"] is True,
          f"hasBuffer fresh={_freshS['hasBuffer']}, restored={_restS['hasBuffer']}")
    check("V214f ...and its trim window survives the round trip",
          _restS["trim"] == _freshS["trim"],
          f"fresh {_freshS['trim']}, restored {_restS['trim']}")
    check("V214f ...and it posts the SAME cropped audio, not the full sample "
          "(588,082 B against 3,528,082 B for the same 5.00s loop)",
          _restS["postedBytes"] == _freshS["postedBytes"] and
          _restS["postedSecs"] == _freshS["postedSecs"],
          f"fresh {_freshS['postedBytes']} B / {_freshS['postedSecs']}s, "
          f"restored {_restS['postedBytes']} B / {_restS['postedSecs']}s")
    _p18.close(); _c18.close()
    _br18.close()


# ---------------------------------------------------------------------------
# V214g — a superseded IMAGE load cannot render into the current one. (Review #4.)
#
# imageSelectionSeq guarded validation and the FileReader but stopped before the
# Image load that populates bgImageObj. Once A's reader had passed, selecting B
# and letting B's Image finish FIRST left bgImageObj — what render() draws —
# as A, while bgImage and the serialized payload were B.
#
# THE ASSERTION IS THAT THE TWO AGREE, not merely that either is B. Preview and
# posted content disagreeing is worse than either being wrong on its own,
# because nothing on screen says so: the user sees A and posts B.
#
# Completion order is forced by delaying every img `src` assignment into a queue
# released by index, the same technique as the decode queue. A=40x40, B=120x120
# so the rendered object is identifiable by naturalWidth alone.
print("\nV214g — a stale image load cannot render over the selected one")

_IGATE = """
window.__iq = [];
(function(){
  const d = Object.getOwnPropertyDescriptor(HTMLImageElement.prototype, 'src');
  Object.defineProperty(HTMLImageElement.prototype, 'src', {
    configurable: true,
    get(){ return d.get.call(this); },
    set(v){ const self = this; window.__iq.push(() => d.set.call(self, v)); }
  });
})();
window.__irelease = (i) => { const f = window.__iq[i]; if (f) f(); };
"""
_ISTATE = """() => ({
  rendered: bgImageObj ? bgImageObj.naturalWidth : null,
  serialized: (() => { const p = buildSharePayload();
      const ph = p.frames && p.frames[0] && p.frames[0].photo;
      return ph && ph.data ? ph.data.length : null; })(),
})"""

import zlib as _zl, struct as _sk
def _mkpng(_path, _w, _h, _rgb):
    _raw = b''.join(b'\x00' + bytes(_rgb) * _w for _ in range(_h))
    def _ch(_t, _d):
        _c = _t + _d
        return _sk.pack('>I', len(_d)) + _c + _sk.pack('>I', _zl.crc32(_c) & 0xffffffff)
    _ihdr = _sk.pack('>IIBBBBB', _w, _h, 8, 2, 0, 0, 0)
    open(_path, 'wb').write(b'\x89PNG\r\n\x1a\n' + _ch(b'IHDR', _ihdr)
                            + _ch(b'IDAT', _zl.compress(_raw)) + _ch(b'IEND', b''))
_IA, _IB = "/tmp/v214_imgA.png", "/tmp/v214_imgB.png"
_mkpng(_IA, 40, 40, (255, 0, 0)); _mkpng(_IB, 120, 120, (0, 0, 255))

with sync_playwright() as _b19:
    _br19 = _b19.chromium.launch()
    _c19 = _br19.new_context(viewport={"width": 1200, "height": 950})
    _p19 = _c19.new_page()
    _p19.goto(BASE + "/flip", wait_until="load"); _p19.wait_for_timeout(900)
    _p19.evaluate("() => localStorage.clear()")
    _p19.reload(wait_until="load"); _p19.wait_for_timeout(900)
    _p19.evaluate(_IGATE)
    _p19.set_input_files("#imageInput", _IA); _p19.wait_for_timeout(600)
    _p19.set_input_files("#imageInput", _IB); _p19.wait_for_timeout(600)

    check("V214g gate: both image loads are in flight and gated",
          _p19.evaluate("() => window.__iq.length") >= 2,
          f"queued {_p19.evaluate('() => window.__iq.length')}")

    _p19.evaluate("() => window.__irelease(1)"); _p19.wait_for_timeout(600)
    _bImg = _p19.evaluate(_ISTATE)
    check("V214g gate: B (120x120) is loaded and rendering",
          _bImg["rendered"] == 120, f"rendered naturalWidth {_bImg['rendered']}")

    _p19.evaluate("() => window.__irelease(0)"); _p19.wait_for_timeout(800)
    _aImg = _p19.evaluate(_ISTATE)
    check("V214g A (40x40) finishing LAST does not become the rendered image",
          _aImg["rendered"] == 120,
          f"rendered naturalWidth after the stale load: {_aImg['rendered']} "
          f"(want 120)")
    check("V214g ...so what the canvas DRAWS and what gets POSTED still agree "
          "(the split showed the user A and serialized B)",
          _aImg["rendered"] == _bImg["rendered"] and
          _aImg["serialized"] == _bImg["serialized"],
          f"before {_bImg}, after the stale load {_aImg}")
    _p19.close(); _c19.close()
    _br19.close()


ok = sum(1 for o, _ in results if o)
bad = [r for r in results if not r[0]]
print(f"\n{'='*62}\n{ok}/{len(results)} passed" +
      ("" if not bad else "  FAILURES: " + ", ".join(r[1] for r in bad)))
import sys
sys.exit(1 if bad else 0)
