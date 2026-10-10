"""Every sentence in "How it works" is tried, not just written.

WHY THIS EXISTS. The owner, after v317: "build a check so when we go to seal we
check if How it works is updated every time -- a thing where you have to try
what you're describing to make sure it works too." verify_help already checks
that the badges add up and that a handful of features are mentioned; nothing
held the sheet to the app as a whole, and the first pass of this suite found
two sentences that were not true -- the Pad's "Which tool am I using?" named
tools the Pad does not have, and a section cap had hidden most of Flip's tool
tips on a phone.

THREE GATES, all run at the seal (release_run BATCHES):

  1. EVERY TIP IS CLAIMED. Each help pill rendered on the Pad or Flip must
     appear in CLAIMS below, with at least one way of TRYING what it says.
     A new tip with no claim fails; a claim whose tip has gone fails too, so
     the map cannot drift into describing a sheet that no longer exists.

  2. EVERY CLAIM IS REAL. A claim is either
       "verify_x.py::words"  an existing check in that suite, found by reading
                             the suite's check(...) calls with the AST -- a
                             check that names the words, not a comment that
                             happens to. The seal runs every suite and fails
                             on any red, so a claimed check that exists IS a
                             passing demonstration of the tip at the seal.
       "probe:name"          a demonstration in THIS suite, run here, that
                             does what the tip describes through the page's
                             own controls and asserts the result.

  3. EVERY CONTROL IS DESCRIBED. Each row of the ⋯ menu and each tool button
     must be named somewhere in How it works, so a feature cannot ship
     without the sheet learning about it.

Adding a feature therefore means: write its tip, and name the check that
proves it -- or write a probe here. That is the rule the owner asked for.
"""
import ast
import os
import pathlib
import re
import sys

from assertions import make_check
import browsing

BASE = os.environ.get("SKRIBL_BASE", "http://127.0.0.1:5001")
HARNESS = pathlib.Path(__file__).resolve().parent
results = []
check = make_check(results)

# ---------------------------------------------------------------- the claims
# Each tip -> the checks that try it. Pills are matched exactly as rendered.
# Where one pill text names two tips ("Opacity": the stroke's and the photo's),
# the claims cover both.
CLAIMS = {
    # Drawing tools
    "Pen": ["probe:pen", "probe:pen_swoosh"],
    "Eraser": ["verify_pointerpad.py::the eraser ring follows the mouse DURING an erase",
               "verify_input.py::with the stabilizer ON, an eraser point lands where the pointer is"],
    "Shape": ["probe:shape",
              "verify_tools.py::a pentagon drawn from a drag 15% taller than wide comes out with its sides EQUAL"],
    "Brush style": ["probe:brush_style"],
    "Stroke layers": ["verify_tools.py::turning Stroke layers OFF makes a self-crossing stroke BEAD"],
    "Grid": ["probe:grid"],
    "Brush size": ["verify_pressure.py::full force equals the nominal brush size, never exceeds it",
                   "verify_tools.py::move the brush size through the slider's own input event"],
    "Pressure": ["verify_pointerpad.py::a pen stroke's width follows its pressure"],
    "Tween": ["verify_inbetween.py::an in-between can be built AGAINST a generated pose"],
    "Smear": ["verify_beading.py::the smear produced a see-through ghost to measure"],
    "Liquify": ["verify_liquify.py::a real liquify stroke DOES log one entry",
                "verify_smudgeblur.py::Liquify reaches its own size, whatever the brush",
                "verify_tray.py::the size row shows under the tools for Liquify, Smudge and Blur",
                "verify_tray.py::a tool never sized follows the brush"],
    "Smudge": ["verify_smudgeblur.py::smudge displaces points that were under the brush",
               "verify_smudgeblur.py::smudge SMEARS as well as displacing",
               "verify_smudgeblur.py::Smudge wears the same ring",
               "verify_smudgeblur.py::Smudge reaches its own size, whatever the brush"],
    "Blur": ["verify_smudgeblur.py::BLUR ACTUALLY SOFTENS THE EDGE",
             "verify_smudgeblur.py::blurring a line again keeps its colour",
             "verify_smudgeblur.py::up to a limit, past which another blur changes nothing",
             "verify_smudgeblur.py::Blur shows how far it reaches",
             "verify_smudgeblur.py::Blur reaches its own size, whatever the brush",
             "verify_smudgeblur.py::while its size is dragged, the ring stands at its true size"],
    "Fill": ["verify_fill.py::a closed shape fills without crying wolf",
             "verify_fill.py::...and it stopped at the lines rather than flooding the page"],
    "Select": ["verify_beading.py::the repaint ran over a real selection", "probe:select"],
    "Stamps": ["verify_stamps.py::saving puts one stamp on the shelf",
               "verify_stamps.py::choosing Stamps opens the shelf"],
    "Color": ["verify_parity.py::a fresh editor starts on #7c5cff (Skribl purple)",
              "verify_parity.py::apply reports a preset as matched and a custom colour as not",
              "verify_parity.py::recent colours keep the same number on both"],
    "Eyedropper": ["verify_visual.py::the eyedropper actually sampled something",
                   "verify_parity.py::lifting the finger picks what the lens showed",
                   "verify_parity.py::a click on the drawing picks the colour under the lens",
                   "verify_parity.py::Cancel abandons: the pen keeps its colour"],
    "Background": ["probe:background"],
    "Which tool am I using?": ["probe:which_tool"],
    "Tips": ["verify_tips.py::with tips off, nothing is shown", "verify_tips.py::turning tips off on Flip stores it"],
    "Theme": ["verify_theme.py::choosing light stamps the attribute",
              "verify_theme.py::a drawing's ground is IDENTICAL in both themes",
              "verify_theme.py::theme starts on",
              "verify_theme.py::a blank canvas follows the theme to the dark canvas",
              "verify_theme.py::once there is a stroke, the theme never moves the ground"],
    "Canvas": ["verify_canvas.py::strokes survive every resize untouched"],
    "Opacity": ["verify_tools.py::opacity is carried in the stored COLOUR",
                "probe:photo_adjust"],
    "Smoothing": ["verify_parity.py::each smoothing level maps to the same stabilizer strength on both"],
    "Undo & New Skribl": ["verify_ux.py::New Skribl starts a new title, not the last one",
                          "verify_ux.py::...and the saved draft it was, so the next Save updates it",
                          "verify_ux.py::NEW SKRIBL: pages, photo and music all go, as on the Pad",
                          "verify_theme.py::New Skribl in the light theme starts on Paper",
                          "verify_theme.py::its Undo brings back the dark canvas the drawing was on"],
    # Zoom & pan
    "Magnifier": ["probe:magnifier"],
    "Zoom in / out": ["probe:magnifier"],
    "Pinch": ["verify_pointerpad.py::two fingers on the canvas pinch-zoom the view"],
    "Pan (desktop)": ["verify_ux.py::Space+drag does NOT draw"],
    "Move the controls": ["probe:dock"],
    # Recording (Pad)
    "Auto-record": ["verify_ux.py::AUTO-RECORD: the first stroke starts the take"],
    "Two timers": ["probe:takes"],
    "Canvas locks between takes": ["probe:takes"],
    "Add more takes": ["verify_ux.py::F4 setup: Add take started a take", "probe:takes"],
    "Play & scrub": ["verify_scrub.py::a real replay shows the bar",
                     "verify_scrub.py::it is a rounded bar of the drawing's shape",
                     "verify_replayspeed.py::the bar shows the drawing's shape: ink where it was drawn, flat where the artist paused",
                     "verify_replayspeed.py::...and slid up off the bar, the same movement covers a quarter of that (fine scrub)",
                     "verify_replayspeed.py::a sideways drag across the drawing scrubs it",
                     "verify_tappause.py::Pad: a tap on the canvas pauses the replay where it is",
                     "verify_tappause.py::Pad: a second tap carries the replay on from where it paused"],
    "Speed": ["verify_replayspeed.py::...saying how long it took to draw and how fast the preview runs",
              "verify_replayspeed.py::a speed picked mid-play carries on from the same place, then runs at it",
              "verify_replayspeed.py::Fit lands the whole replay in about 30 seconds and is never slower than as drawn",
              "verify_replayspeed.py::the Post sheet asks where viewers start: Auto (chosen), As drawn, Fit, and the speed last previewed",
              "verify_replayspeed.py::where a post starts: none -> as drawn; Auto -> as drawn under a minute of drawing, Fit over it"],
    # Frames (Flip)
    "Move artwork": ["verify_move.py::every point moved by the SAME offset"],
    "Pages": ["verify_pagespan.py::Undo restores every page of the deleted run"],
    "Onion skin": ["verify_flipmotion.py::sampling an ONION pixel does not pick the onion's colour",
                   "verify_pages.py::onion depth/tint live there and are reachable"],
    "fps": ["verify_gifenc.py::frame delay matches the chosen fps"],
    "Draw-on": ["verify_hold.py::a Draw-on page reaches its last stroke before the page turns"],
    "Flip it & scrub": ["probe:flip_play",
                        "verify_tappause.py::Flip: a tap on the canvas pauses the flip on the page it is on",
                        "verify_tappause.py::Flip: a second tap carries the flip on from where it paused"],
    # Music
    "Add a track": ["verify_amber.py::Pad GREEN once a track is attached", "probe:media_tabs",
                    "verify_parity.py::{}: a file dropped anywhere on the card is taken, and the wrong kind is refused"],
    "Loop markers": ["verify_tools.py::the drag is live AND has already moved the trim"],
    "Move the loop": ["probe:loop_move"],
    "Loop Detail": ["verify_parity.py::the fine-tune disclosure opens the loop detail on both"],
    "Crossfade": ["verify_loopcap.py::clip shortened by exactly the crossfade"],
    "Match Drawing Time": ["probe:loop_window"],
    "Preview Loop": ["verify_audiosession.py::Preview Loop puts signal on the audio graph"],
    "Test Seam": ["verify_audio.py::no click at the seam"],
    "Nudge": ["verify_parity.py::a nudge moves the trim edge by the same amount on both"],
    # Background image
    "Add a photo": ["verify_parity.py::loading a photo marks the tab on both", "probe:media_tabs",
                    "verify_parity.py::{}: a file dropped anywhere on the card is taken, and the wrong kind is refused",
                    "verify_parity.py::{}: the bin asks once, then removes -- by pointer and by keyboard"],
    "Fill / Fit / Stretch (image framing)": ["verify_parity.py::both surfaces place a {} photo identically"],
    "Reposition": ["verify_pointerpad.py::a mouse drags the photo in reposition mode"],
    "Zoom": ["probe:photo_adjust"],
    "Blur (the image)": ["probe:photo_adjust", "verify_inline.py::a photo authored BLURRED is soft"],
    "Reset": ["probe:photo_adjust"],
    # Save, export & sharing
    "Autosave": ["verify_pages.py::the restored draft reopens on the same page",
                 "verify_drafts.py::after restore, Post is live"],
    "Saved drafts": ["verify_clouddrafts.py::with storage hung, Save draft still saves",
                     "verify_ux.py::opening a backup file lets go of the saved draft"],
    "Name": ["verify_ux.py::Undo brings the old title back with the drawing, on both editors"],
    "Backups": ["verify_ux.py::FORMAT: a replay .skribl loads in Pad"],
    "Export": ["verify_gifenc.py::Pad exports a valid GIF89a too", "verify_canvas.py::GIF exports at the new canvas size"],
    "Post": ["verify_sheetswipe.py::mid-send, neither a swipe nor the grabber closes the post sheet",
             "verify_createpost.py::the author stamp is the id the host passed"],
    "Your Skribl Library": ["verify_library.py::it reaches Pad, Flip, Your Skribl Library and the gallery"],
    "Photo & music": ["verify_amber.py::the track itself is restored — bytes, not a re-add card"],
    "If media goes missing": ["verify_amber.py::the amber pill NAMES the way out, on a button that says Re-add"],
    "Report a problem": ["verify_library.py::which copies this page's details, and says it did",
                         "verify_amber.py::the report names the refused write and its reason"],
    "Menus & panels": ["verify_sheetswipe.py::tapping the grabber closes it",
                       "verify_sheetswipe.py::a swipe down follows the finger"],
}

# ⋯-menu rows and tool buttons that are named in the sheet by another word.
ALIASES = {"Flip Mode": "Flip", "Skribl Pad": "Pad", "Public gallery": "public gallery",
           "Open a draft…": "Open a draft", "Export…": "Export", "Open a backup…": "backup",
           "Save a backup": "backup", "Name this skribl": "Name this skribl",
           "artmove": "Artwork", "stamp": "Stamps", "More tools": None}


# ------------------------------------------------ gate 2: reading the suites
def check_names(suite):
    """Every check(...) name in a suite, f-strings with {} for their holes."""
    path = HARNESS / suite
    if not path.is_file():
        return None
    names = []
    for n in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(n, ast.Call) and getattr(n.func, "id", None) == "check" and n.args:
            a = n.args[0]
            if isinstance(a, ast.Constant) and isinstance(a.value, str):
                names.append(a.value)
            elif isinstance(a, ast.JoinedStr):
                names.append("".join(v.value if isinstance(v, ast.Constant) else "{}" for v in a.values))
    return names


print("\nCLAIMS — each one names a check that exists, or a probe below")
_cache = {}
_bad_refs = []
for pill, refs in CLAIMS.items():
    if not refs:
        _bad_refs.append(f"{pill}: no claim at all")
    for ref in refs:
        if ref.startswith("probe:"):
            continue
        suite, _, words = ref.partition("::")
        if suite not in _cache:
            _cache[suite] = check_names(suite)
        names = _cache[suite]
        if names is None:
            _bad_refs.append(f"{pill}: {suite} does not exist")
        elif not any(words in nm for nm in names):
            _bad_refs.append(f"{pill}: no check in {suite} says {words!r}")
check("every claimed check exists, by name, in the suite it names",
      not _bad_refs, "; ".join(_bad_refs[:6]))


# --------------------------------------------------------- gate 2: the probes
def fresh(b, path, **kw):
    ctx = b.new_context(viewport=kw.pop("viewport", {"width": 1280, "height": 900}), **kw)
    pg = ctx.new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    browsing.goto(pg, BASE, path)
    pg.evaluate("() => { localStorage.clear(); }")
    browsing.goto(pg, BASE, path)
    pg.wait_for_timeout(600)
    pg.evaluate("() => { window.SkriblHints && SkriblHints.hide(); }")
    return ctx, pg, errs


def canvas_sel(path):
    return "#canvas" if path != "/flip" else "#pad"


def drag(pg, sel, x0, y0, x1, y1, steps=10):
    box = pg.locator(sel).bounding_box()
    pg.mouse.move(box["x"] + x0, box["y"] + y0)
    pg.mouse.down()
    pg.mouse.move(box["x"] + x1, box["y"] + y1, steps=steps)
    pg.mouse.up()
    pg.wait_for_timeout(150)


# Both editors keep a stroke as a run of points, the first marked `start`.
COUNT = {"/skribl-pad": "() => strokes.length", "/flip": "() => frames[idx].strokes.length"}
POINTS = {"/skribl-pad": "(n) => strokes.slice(n).map(q => ({ x: q.x, y: q.y, start: !!q.start }))",
          "/flip": "(n) => frames[idx].strokes.slice(n).map(q => ({ x: q.x, y: q.y, start: !!q.start }))"}
TOOL = {"/skribl-pad": "() => tool", "/flip": "() => flipTool"}
SERIAL = {"/skribl-pad": "() => JSON.stringify(serializeSkribl())",
          "/flip": "() => JSON.stringify(serializeFlip({ recipes: true }))"}
SURFACES = (("Pad", "/skribl-pad"), ("Flip", "/flip"))


def probe_pen(b, nm, path):
    """Picking any colour switches you back to the Pen."""
    ctx, pg, errs = fresh(b, path)
    pg.evaluate("() => document.getElementById('eraserToolBtn').click()")
    before = pg.evaluate(TOOL[path])
    pg.evaluate("() => document.querySelector('#colorGroup .color-dot:not(.active)').click()")
    after = pg.evaluate(TOOL[path])
    ctx.close()
    return before == "eraser" and after == "pen" and not errs, f"eraser -> {before}, after a colour -> {after}"


def probe_shape(b, nm, path):
    """Shape draws a rectangle instead of a freehand stroke."""
    ctx, pg, errs = fresh(b, path)
    pg.evaluate("() => document.getElementById('shapeToolBtn').click()")
    pg.evaluate("() => { const r = document.querySelector('[data-shape=\"rect\"]'); r && r.click(); }")
    n0 = pg.evaluate(COUNT[path])
    # A diagonal drag: freehand, that is a line through the middle of its box.
    drag(pg, canvas_sel(path), 80, 80, 260, 200)
    pts = pg.evaluate(POINTS[path], n0)
    kind = pg.evaluate("() => shapeKind")
    ctx.close()
    if not pts:
        return False, f"kind={kind}, nothing was drawn"
    starts = sum(1 for q in pts if q.get("start"))
    xs, ys = [q["x"] for q in pts], [q["y"] for q in pts]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    # Every point of a rectangle lies on the edge of its own box; a freehand
    # diagonal puts nearly all of them inside it.
    inside = sum(1 for q in pts if min(q["x"] - x0, x1 - q["x"], q["y"] - y0, y1 - q["y"]) > 2)
    big = (x1 - x0) > 100 and (y1 - y0) > 60
    return kind == "rect" and starts == 1 and inside == 0 and big and not errs, \
        f"kind={kind}, one stroke={starts == 1}, {len(pts)} points, {inside} off the edge, box {x1 - x0:.0f}x{y1 - y0:.0f}"


def probe_brush_style(b, nm, path):
    """Marker is wider and see-through at one width; Pen is the plain line."""
    ctx, pg, errs = fresh(b, path)
    last = COUNT[path].replace(".length", "[" + COUNT[path].split("=> ")[1].replace(".length", ".length - 1") + "]")
    drag(pg, canvas_sel(path), 60, 60, 240, 60)
    pen = pg.evaluate(f"() => {{ const s = ({last.split('=> ')[1]}); return {{ w: s.width || s.size, c: s.color, b: s.brush || null }}; }}")
    pg.evaluate("() => document.querySelector('[data-brush=\"marker\"]').click()")
    drag(pg, canvas_sel(path), 60, 140, 240, 140)
    mk = pg.evaluate(f"() => {{ const s = ({last.split('=> ')[1]}); return {{ w: s.width || s.size, c: s.color, b: s.brush || null }}; }}")
    ctx.close()
    wider = (mk["w"] or 0) > (pen["w"] or 0)
    return wider and mk != pen and not errs, f"pen {pen}, marker {mk}"


def probe_grid(b, nm, path):
    """Grid overlays guides; they are never saved into the drawing."""
    ctx, pg, errs = fresh(b, path)
    grid_el = "#padGrid" if path != "/flip" else "#flipGrid"
    drag(pg, canvas_sel(path), 60, 60, 200, 120)
    s0 = pg.evaluate(SERIAL[path])
    pg.evaluate("() => document.getElementById('gridBtn').click()")
    pg.wait_for_timeout(200)
    shown = pg.evaluate(f"() => {{ const g = document.querySelector('{grid_el}'); const cs = g && getComputedStyle(g);"
                        " return !!g && cs.display !== 'none' && cs.visibility !== 'hidden' && parseFloat(cs.opacity) > 0; }")
    s1 = pg.evaluate(SERIAL[path])
    pg.evaluate("() => document.getElementById('gridBtn').click()")
    pg.wait_for_timeout(200)
    hidden = pg.evaluate(f"() => {{ const g = document.querySelector('{grid_el}'); const cs = g && getComputedStyle(g);"
                         " return !g || cs.display === 'none' || parseFloat(cs.opacity) === 0 || !g.classList.contains('on') && !g.classList.contains('show'); }")
    # serialize stamps a fresh draft id and time on every call; the drawing is the rest.
    strip = lambda s: re.sub(r'"(savedAt|createdAt|updatedAt|draftId|title)":"[^"]*"', "", s)
    ctx.close()
    return shown and hidden and strip(s0) == strip(s1) and not errs, \
        f"shown={shown} hidden again={hidden} saved drawing unchanged={strip(s0) == strip(s1)}"


def probe_background(b, nm, path):
    """Background sets the colour behind the drawing, and it is saved with it."""
    ctx, pg, errs = fresh(b, path)
    pg.evaluate("() => document.querySelector('[data-bg=\"#1a0a0a\"]').click()")
    pg.wait_for_timeout(150)
    got = pg.evaluate("() => bgColor")
    saved = "#1a0a0a" in pg.evaluate(SERIAL[path]).lower()
    ctx.close()
    return got.lower() == "#1a0a0a" and saved and not errs, f"bgColor={got}, in the saved drawing={saved}"


def probe_which_tool(b, nm, path):
    """The tool you hold is shown next to the pointer."""
    ctx, pg, errs = fresh(b, path)
    box = pg.locator(canvas_sel(path)).bounding_box()
    if path == "/flip":
        pg.evaluate("() => document.getElementById('smudgeToolBtn').click()")
        badge = ".flip-tool-badge"
    else:
        pg.evaluate("() => document.getElementById('shapeToolBtn').click()")
        badge = "#shapeCursor"
    pg.mouse.move(box["x"] + 120, box["y"] + 120)
    pg.mouse.move(box["x"] + 150, box["y"] + 140, steps=4)
    pg.wait_for_timeout(150)
    shown = pg.evaluate(f"() => {{ const e = document.querySelector('{badge}'); if (!e) return null;"
                        " const g = e.querySelector('svg');"
                        " return getComputedStyle(e).display !== 'none' && !!g && g.childElementCount > 0; }")
    ctx.close()
    return shown is True and not errs, f"{badge} shown with a glyph: {shown}"


def probe_select(b, nm, path):
    """Select: drag a box around part of the drawing to pick it up."""
    if path != "/flip":
        return True, "Flip only"
    ctx, pg, errs = fresh(b, path)
    drag(pg, "#pad", 100, 100, 180, 160)
    pg.evaluate("() => document.getElementById('selectToolBtn').click()")
    drag(pg, "#pad", 60, 60, 260, 220)
    picked = pg.evaluate("() => selSpans.length")
    ctx.close()
    return picked >= 1 and not errs, f"strokes picked up: {picked}"


def probe_magnifier(b, nm, path):
    """Magnifier shows the zoom pill; + zooms in; turning it off returns to 100%."""
    ctx, pg, errs = fresh(b, path)
    pg.evaluate("() => document.getElementById('magnifyBtn').click()")
    pg.wait_for_timeout(250)
    hud = pg.evaluate("() => { const h = document.getElementById('zoomHud'); return !!h && !h.hidden && getComputedStyle(h).display !== 'none'; }")
    val = "() => (document.querySelector('#zoomHud .zoom-val-input, #zoomHud [data-zoom-val], #zoomHud .zoom-val') || {}).value || (document.querySelector('#zoomHud .zoom-val') || {}).textContent || ''"
    z0 = pg.evaluate(val)
    pg.evaluate("() => document.getElementById('zoomInBtn').click()")
    pg.wait_for_timeout(250)
    z1 = pg.evaluate(val)
    pg.evaluate("() => document.getElementById('magnifyBtn').click()")
    pg.wait_for_timeout(250)
    z2 = pg.evaluate(val)
    num = lambda s: float(re.sub(r"[^0-9.]", "", str(s)) or 0)
    ctx.close()
    return hud and num(z1) > num(z0) and num(z2) in (0, 100) and not errs, f"pill={hud} zoom {z0!r} -> {z1!r} -> off {z2!r}"


def probe_dock(b, nm, path):
    """Dragging the pill's grip docks the zoom controls in another corner."""
    ctx, pg, errs = fresh(b, path)
    pg.evaluate("() => document.getElementById('magnifyBtn').click()")
    pg.wait_for_timeout(300)
    hud0 = pg.locator("#zoomHud").bounding_box()
    grip = pg.locator("#zoomGrip").bounding_box()
    vw = pg.viewport_size
    pg.mouse.move(grip["x"] + grip["width"] / 2, grip["y"] + grip["height"] / 2)
    pg.mouse.down()
    tx = 60 if hud0["x"] > vw["width"] / 2 else vw["width"] - 60
    ty = 120 if hud0["y"] > vw["height"] / 2 else vw["height"] - 120
    pg.mouse.move(tx, ty, steps=12)
    pg.mouse.up()
    pg.wait_for_timeout(500)
    hud1 = pg.locator("#zoomHud").bounding_box()
    ctx.close()
    moved = abs(hud1["x"] - hud0["x"]) > 100 or abs(hud1["y"] - hud0["y"]) > 100
    return moved and not errs, f"pill {round(hud0['x'])},{round(hud0['y'])} -> {round(hud1['x'])},{round(hud1['y'])}"


def slow_drag(pg, sel, x0, y0, x1, y1, ms):
    """A drag that takes `ms` of real time, so the drawing has a length."""
    box = pg.locator(sel).bounding_box()
    pg.mouse.move(box["x"] + x0, box["y"] + y0)
    pg.mouse.down()
    n = max(4, ms // 40)
    for i in range(1, n + 1):
        pg.mouse.move(box["x"] + x0 + (x1 - x0) * i / n, box["y"] + y0 + (y1 - y0) * i / n)
        pg.wait_for_timeout(40)
    pg.mouse.up()
    pg.wait_for_timeout(150)


def probe_takes(b, nm, path):
    """Pad: the badge counts drawing time not pauses; a stopped take locks; Add take adds one."""
    if path == "/flip":
        return True, "Pad only"
    ctx, pg, errs = fresh(b, path)
    import time as _t
    t0 = _t.time()
    slow_drag(pg, "#canvas", 60, 60, 260, 90, 1300)
    pg.wait_for_timeout(2500)                      # a pause: on the clock, not in the replay
    slow_drag(pg, "#canvas", 60, 140, 260, 170, 1300)
    wall = _t.time() - t0
    pg.evaluate("() => document.getElementById('recordBtn').click()")
    pg.wait_for_timeout(300)
    badge = pg.evaluate("() => document.getElementById('durationBadge').textContent")
    shown = pg.evaluate("() => !document.getElementById('durationBadge').hidden")
    play_s = pg.evaluate("() => getPlaybackDuration()") / 1000
    n0 = pg.evaluate(COUNT[path])
    drag(pg, "#canvas", 60, 220, 220, 250)
    n1 = pg.evaluate(COUNT[path])
    locked = pg.evaluate("() => document.querySelector('.canvas-wrap').classList.contains('locked')"
                         " && !document.getElementById('addTakePill').hidden")
    pg.evaluate("() => document.getElementById('addTakePill').click()")
    pg.wait_for_timeout(200)
    drag(pg, "#canvas", 60, 300, 220, 330)
    n2 = pg.evaluate(COUNT[path])
    ctx.close()
    m = re.fullmatch(r"(\d+):(\d\d)", badge.strip())
    badge_s = int(m.group(1)) * 60 + int(m.group(2)) if m else -1
    ok = (shown and 2.0 <= play_s < wall - 2.0 and badge_s == int(play_s)
          and locked and n1 == n0 and n2 > n1 and not errs)
    return ok, (f"badge {badge!r} for {play_s:.1f}s of drawing vs {wall:.1f}s on the clock; "
                f"locked={locked}; strokes after Stop {n0} -> {n1}, after Add take {n2}")


def probe_flip_play(b, nm, path):
    """Flip it plays the pages in a loop; the scrub bar reaches any page."""
    if path != "/flip":
        return True, "Flip only"
    ctx, pg, errs = fresh(b, path)
    for i in range(3):
        drag(pg, "#pad", 60 + 40 * i, 60, 120 + 40 * i, 140)
        pg.click("#addblank")
        pg.wait_for_timeout(150)
    seen = set()
    pg.evaluate("() => document.getElementById('play').click()")
    for _ in range(15):
        pg.wait_for_timeout(80)
        seen.add(pg.evaluate("() => (typeof playIdx !== 'undefined' ? playIdx : idx)"))
    playing = pg.evaluate("() => playing")
    # The scrub bar: press at its left end and drag to its right end.
    box = pg.locator("#flipProgress").bounding_box()
    at = []
    if box and box["width"] > 20:
        y = box["y"] + box["height"] / 2
        pg.mouse.move(box["x"] + 2, y)
        pg.mouse.down()
        at.append(pg.evaluate("() => idx"))
        pg.mouse.move(box["x"] + box["width"] - 2, y, steps=10)
        at.append(pg.evaluate("() => idx"))
        pg.mouse.up()
    n = pg.evaluate("() => frames.length")
    pg.evaluate("() => { if (playing) document.getElementById('play').click(); }")
    ctx.close()
    scrubbed = at == [0, n - 1]
    return playing and len(seen) >= 3 and scrubbed and not errs, \
        f"playing={playing}, pages seen while playing {sorted(seen)}, scrub first/last {at} of {n}"


def _with_photo(pg, path):
    import base64
    png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==")
    inp = "#photoInput" if path != "/flip" else "#imageInput"
    pg.set_input_files(inp, {"name": "probe.png", "mimeType": "image/png", "buffer": png})
    pg.wait_for_timeout(1500)


def probe_photo_adjust(b, nm, path):
    """Zoom scales the photo, Opacity fades it, Blur softens it, Reset puts all three back."""
    ctx, pg, errs = fresh(b, path)
    _with_photo(pg, path)
    set_ = """([id, v]) => { const e = document.getElementById(id); if (!e) return false;
        e.value = v; e.dispatchEvent(new Event('input', { bubbles: true })); e.dispatchEvent(new Event('change', { bubbles: true })); return true; }"""
    pg.evaluate("() => { const b = document.querySelector('.photo-fit-btn[data-fit=\"cover\"], [data-fit=\"cover\"]'); b && b.click(); }")
    for idv in (("photoZoom", "200"), ("photoOpacity", "40"), ("photoBlur", "6")):
        pg.evaluate(set_, list(idv))
    pg.wait_for_timeout(250)
    READ = {"/skribl-pad": "() => ({ zoom: photoZoom, opacity: photoOpacityVal_, blur: photoBlur_ })",
            "/flip": "() => ({ zoom: photoZoom, opacity: photoOpacity, blur: photoBlur })"}[path]
    mid = pg.evaluate(READ)
    pg.evaluate("() => document.getElementById('resetPhotoBtn').click()")
    pg.wait_for_timeout(250)
    after = pg.evaluate(READ)
    ctx.close()
    changed = mid["zoom"] > 1.5 and mid["opacity"] < 0.6 and mid["blur"] > 0
    reset = after["zoom"] == 1 and after["opacity"] == 1 and after["blur"] == 0
    return changed and reset and not errs, f"set {mid}, after Reset {after}"


def _with_music(pg, path, seconds=8):
    import io, math, struct, wave
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(8000)
        w.writeframes(b"".join(struct.pack("<h", int(8000 * math.sin(i / 9))) for i in range(8000 * seconds)))
    pg.set_input_files("#musicInput", {"name": "probe.wav", "mimeType": "audio/wav", "buffer": buf.getvalue()})
    pg.wait_for_function("() => typeof audioDuration !== 'undefined' && audioDuration > 0", timeout=20000)
    pg.wait_for_timeout(300)


DRAWING_S = {"/skribl-pad": "() => getPlaybackDuration() / 1000", "/flip": "() => frames.length / fps"}


def probe_loop_window(b, nm, path):
    """Match Drawing Time sets the loop to exactly as long as the drawing plays."""
    ctx, pg, errs = fresh(b, path)
    if path == "/flip":
        for i in range(11):
            drag(pg, "#pad", 60 + 10 * i, 60, 120 + 10 * i, 140)
            pg.click("#addblank")
    else:
        slow_drag(pg, "#canvas", 60, 60, 300, 200, 2600)
        pg.evaluate("() => document.getElementById('recordBtn').click()")
    _with_music(pg, path)
    want = pg.evaluate(DRAWING_S[path])
    floor = pg.evaluate("() => window.SkriblLoopTrim.MIN_LOOP_SECONDS")
    pg.evaluate("() => { trimStart = 0; trimEnd = audioDuration; updateTrimUI(); }")
    pg.evaluate("() => document.getElementById('matchDrawingBtn').click()")
    pg.wait_for_timeout(300)
    got = pg.evaluate("() => ({ s: trimStart, e: trimEnd })")
    ctx.close()
    length = got["e"] - got["s"]
    # Above the loop's floor and under the track, so "matches" is not a clamp.
    ok = floor + 0.2 < want < 7.0 and abs(length - want) < 0.06 and not errs
    return ok, f"loop {length:.2f}s for a drawing that plays {want:.2f}s (the loop's floor is {floor}s)"


def probe_loop_move(b, nm, path):
    """Dragging inside the loop slides the whole window without resizing it."""
    ctx, pg, errs = fresh(b, path)
    _with_music(pg, path)
    browsing.pad_drawer(pg, "music", settle=0)      # Media, then Music (both editors)
    pg.wait_for_timeout(800)
    pg.evaluate("() => { trimStart = 2; trimEnd = 5; updateTrimUI(); }")
    pg.wait_for_timeout(150)
    box = pg.locator("#musicRange").bounding_box()
    before = pg.evaluate("() => ({ s: trimStart, e: trimEnd })")
    x, y = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
    pg.mouse.move(x, y)
    pg.mouse.down()
    pg.mouse.move(x + 60, y, steps=8)
    pg.mouse.up()
    pg.wait_for_timeout(200)
    after = pg.evaluate("() => ({ s: trimStart, e: trimEnd })")
    ctx.close()
    slid = after["s"] > before["s"] + 0.2
    same = abs((after["e"] - after["s"]) - (before["e"] - before["s"])) < 0.02
    return slid and same and not errs, f"loop {before['s']:.2f}-{before['e']:.2f} -> {after['s']:.2f}-{after['e']:.2f}"


def probe_pen_swoosh(b, nm, path):
    """The Pen button shows your ink; tap it again for its options; drag it sideways for size."""
    ctx, pg, errs = fresh(b, path, viewport={"width": 402, "height": 874}, has_touch=True, is_mobile=True)
    ink = """(hexc) => { const c = document.getElementById('penSwoosh'); if (!c || !c.width) return -1;
        const d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data;
        const t = [1, 3, 5].map(i => parseInt(hexc.substr(i, 2), 16)); let n = 0;
        for (let i = 0; i < d.length; i += 4)
          if (Math.abs(d[i] - t[0]) < 40 && Math.abs(d[i + 1] - t[1]) < 40 && Math.abs(d[i + 2] - t[2]) < 40) n++;
        return n; }"""
    cur = browsing._PAD_CUR                      # either editor's drawer controller
    pink0 = pg.evaluate(ink, "#ff48b0")
    pg.click("#penToolBtn"); pg.wait_for_timeout(350)
    opened = pg.evaluate(cur)
    pg.click('#colorGroup .color-dot[data-color="#ff48b0"]'); pg.wait_for_timeout(250)
    pink1 = pg.evaluate(ink, "#ff48b0")
    # Flip closes the drawer on a pick (its long-standing behaviour); the Pad
    # keeps it open, and the pen tapped again closes it.
    if pg.evaluate(cur) == "draw":
        pg.click("#penToolBtn"); pg.wait_for_timeout(350)
    closed = pg.evaluate(cur)
    bb = pg.locator("#penToolBtn").bounding_box(); x, y = bb["x"] + bb["width"] / 2, bb["y"] + bb["height"] / 2
    s0 = pg.evaluate("() => size")
    pg.mouse.move(x, y); pg.mouse.down(); pg.mouse.move(x + 60, y, steps=10); pg.mouse.up(); pg.wait_for_timeout(300)
    s1, after = pg.evaluate("() => size"), pg.evaluate(cur)
    ctx.close()
    ok = pink0 == 0 and pink1 > 20 and opened == "draw" and closed is None and s1 == s0 + 10 and after is None and not errs
    return ok, (f"pink in the swoosh {pink0} -> {pink1} px; pen again opened {opened!r}, again {closed!r}; "
                f"drag +60px: size {s0} -> {s1}, drawer {after!r}")


def probe_media_tabs(b, nm, path):
    """Media opens Photo or Music behind the drawing; the tabs switch; Media again closes."""
    ctx, pg, errs = fresh(b, path, viewport={"width": 402, "height": 874}, has_touch=True, is_mobile=True)
    cur = browsing._PAD_CUR
    vis = "(id) => { const e = document.getElementById(id); return !!e && e.offsetParent !== null; }"
    pg.click("#mediaOpenBtn"); pg.wait_for_timeout(350)
    a = (pg.evaluate(cur), pg.evaluate(vis, "photoUploadBtn"))
    pg.click("#mediaTabMusic"); pg.wait_for_timeout(350)
    m = (pg.evaluate(cur), pg.evaluate(vis, "musicUploadBtn"),
         pg.evaluate("() => document.getElementById('mediaTabMusic').getAttribute('aria-selected')"))
    pg.click("#mediaOpenBtn"); pg.wait_for_timeout(350)
    c = (pg.evaluate(cur), pg.evaluate(vis, "mediaTabs"))
    ctx.close()
    ok = a == ("photo", True) and m == ("music", True, "true") and c == (None, False) and not errs
    return ok, f"Media -> {a}; Music tab -> {m}; Media again -> {c}"


PROBES = {"pen": probe_pen, "pen_swoosh": probe_pen_swoosh, "media_tabs": probe_media_tabs, "shape": probe_shape, "brush_style": probe_brush_style, "grid": probe_grid,
          "background": probe_background, "which_tool": probe_which_tool, "select": probe_select,
          "magnifier": probe_magnifier, "dock": probe_dock, "takes": probe_takes,
          "flip_play": probe_flip_play, "photo_adjust": probe_photo_adjust, "loop_window": probe_loop_window,
          "loop_move": probe_loop_move}

_named = {r[6:] for refs in CLAIMS.values() for r in refs if r.startswith("probe:")}
check("every probe a claim names is written", _named <= set(PROBES), str(sorted(_named - set(PROBES))))

from playwright.sync_api import sync_playwright   # noqa: E402

MENU = """() => [...document.querySelectorAll('#menuSheet .menu-item, #moreMenu .menu-item')]
    .map(b => { const t = b.querySelector('.menu-item-text');
                const n = t ? [...t.childNodes].filter(c => c.nodeType === 3).map(c => c.textContent).join('') : b.textContent;
                return n.replace(/\\s+/g, ' ').trim(); })
    .filter(Boolean)"""
TOOLS = "() => [...document.querySelectorAll('[data-tool]')].map(b => b.getAttribute('data-tool'))"
# Flip's page-bar buttons, by the words ON them: the sheet said "＋ Page" for a
# button that had read "Duplicate" for many releases.
PAGE_BAR = "() => [...document.querySelectorAll('.addbtn')].map(b => b.textContent.replace(/\\s+/g, ' ').trim())"
HELP_TEXT = "() => document.getElementById('helpDrawer').textContent.replace(/\\s+/g, ' ')"
PILLS = "() => [...document.querySelectorAll('#helpDrawer .help-pill')].map(p => p.textContent.trim())"

with sync_playwright() as p:
    b = p.chromium.launch()
    rendered = set()
    for nm, path in SURFACES:
        ctx, pg, errs = fresh(b, path)
        pills = pg.evaluate(PILLS)
        rendered |= set(pills)
        missing = sorted({x for x in pills if x not in CLAIMS})
        check(f"{nm}: every tip in How it works is claimed by a check that tries it",
              len(pills) >= 40 and not missing, f"unclaimed: {missing}")
        # gate 3: every control is described
        text = pg.evaluate(HELP_TEXT).lower()
        # The row that opens this sheet is the one row it need not describe.
        menu = [m for m in pg.evaluate(MENU) if "How it works" not in m and m != "i"]
        tools = pg.evaluate(TOOLS) + pg.evaluate(PAGE_BAR)
        undescribed = []
        for label in menu + tools:
            word = ALIASES.get(label, label)
            if word is None:
                continue
            if word.lower() not in text:
                undescribed.append(label)
        check(f"{nm}: every ⋯ menu row and every tool is named in How it works",
              len(menu) >= 8 and len(tools) >= 3 and not undescribed, f"not described: {undescribed}")
        if path == "/flip":
            # ...and the other direction, for the tip that names buttons by their
            # words: every button the Pages tip names is a button on the page.
            named = pg.evaluate("""() => { const t = [...document.querySelectorAll('#helpDrawer .help-tip')]
                .find(x => x.querySelector('.help-pill').textContent.trim() === 'Pages');
                return t ? [...t.querySelectorAll('.help-desc strong')].map(s => s.textContent.trim()) : null; }""")
            bar = pg.evaluate(PAGE_BAR)
            ghosts = [w for w in (named or []) if w not in bar and w not in ("←", "→", "✕")]
            check("Flip: every page button the Pages tip names is a button on the page",
                  named and not ghosts, f"named {named}, the page bar has {bar}")
        # THE QUICK START'S WAY INTO THE DRAW MENU IS THE ONE THAT WORKS. Flip's
        # step 1 sent people to "the color dot" for a release after the toolbar
        # redesign took that dot away (outside audit V319-007): the steps are
        # not pills, so gate 1 never read them. Any step that sends someone to
        # the Draw menu must send them through the Pen, which probe:pen_swoosh
        # below proves on both editors opens it.
        steps = pg.evaluate("""() => [...document.querySelectorAll('#helpDrawer .help-step .help-desc')]
            .filter(d => /Draw\\s+menu/i.test(d.textContent))
            .map(d => ({ text: d.textContent.replace(/\\s+/g, ' ').trim().slice(0, 80),
                         pen: [...d.querySelectorAll('strong')].some(s => /^Tap Pen again$/i.test(s.textContent.trim())) }))""")
        wrong = [x["text"] for x in steps if not x["pen"]]
        if steps:
            check(f"{nm}: a quick-start step that points at the Draw menu says to tap Pen again",
                  not wrong, f"points elsewhere: {wrong}")
        ctx.close()
    stale = sorted(k for k in CLAIMS if k not in rendered)
    check("no claim describes a tip that is no longer there", not stale, str(stale))

    print("\nPROBES — each one does what its tip says, through the page's own controls")
    for name, fn in PROBES.items():
        for nm, path in SURFACES:
            try:
                ok, detail = fn(b, nm, path)
            except Exception as e:      # a probe that cannot run has not shown anything
                ok, detail = False, f"{type(e).__name__}: {str(e)[:160]}"
            check(f"{nm}: probe:{name} — {fn.__doc__.strip().splitlines()[0]}", ok, detail)
    b.close()

bad = [r for r in results if not r[0]]
print(f"\n{'=' * 62}\n{len(results) - len(bad)}/{len(results)} passed"
      + ("" if not bad else "  FAILURES: " + ", ".join(r[1] for r in bad)))
sys.exit(1 if bad else 0)
