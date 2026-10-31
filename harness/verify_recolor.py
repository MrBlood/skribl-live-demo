#!/usr/bin/env python3
"""Recolor: a line already drawn takes the pen's colour (lib/recolor.js), on
the Pad and on Flip. The owner, of the mock: "I love the recolor too", every
choice yes.

The rows, each the owner's choice or a fault found building it:

  THE BUTTON. Recolor sits beside the eyedropper in the drawer both editors
  share, the pair at the end of the Pen | Background row: in the colour row
  they made it eleven items, which shut the phone's gaps to 7px at 402 and
  overlapped them at 320 -- the crowding the owner sent back once. The row is
  nine colours again, read for its gaps at 320, 390 and 402.

  THE MODE. Tapping it closes the drawer; its bar takes the dock's row, the
  dock's own controls out of reach under it and the canvas where it was; the
  bar's colour is the pen's, and a colour picked from it closes the drawer
  again; Done and Escape give the dock back.

  THE POINTER. On a desk the mode's crosshair is over the canvas, and stays
  after a colour is picked from the bar: on Flip it vanished there (the
  owner's desktop check R3), and on the Pad a loaded drawing's lock would say
  'not-allowed'.

  A TAP recolours the line under it, the topmost where two cross, keeping its
  opacity, and nothing else; a tap on nothing changes nothing and leaves no
  undo step; an eraser's line is never hit; the first finger of a pinch
  recolours nothing. A DRAG recolours each line it crosses, and one Undo takes
  the whole drag back.

  THE COLOUR RUNS from the finger: partway through, the line's far end still
  shows its old colour on the screen and its near end the new one; at the end
  it is all new and the overlay that drew the run is gone. Under Reduce Motion
  it is new at once, with no overlay.

  THE PAD KEEPS THE MOMENT (app.js `recolors`, for the replay): the line, its
  old and new colour, the drawing's length then, and the take's clock while a
  take records. A post carries it and the server keeps it; a draft carries it
  through a reload; and a recolour that was undone never comes back on a
  reload (its redo is left out of the draft rather than rebuilt wrong).

  FLIP: one undo step a gesture; the page's thumbnail follows the colour; a
  fill's bands are one line; a generated page that was recoloured is saved as
  it now looks, not as the recipe that would undo it; and the Select bar's
  Color gives every selected line the pen's colour in one step, its count a
  bare number on a phone so the row fits.

  A replay and the eraser key end the mode.
"""
import io
import json
import re
import os
import sys
import urllib.request
from assertions import make_check

BASE = os.environ.get("SKRIBL_BASE", "http://127.0.0.1:5001")
results = []
check = make_check(results, detail_on_pass=False)


def summarise_and_exit():
    bad = [r for r in results if not r[0]]
    print(f"\n{'=' * 62}\n{len(results) - len(bad)}/{len(results)} passed"
          + ("" if not bad else "  FAILURES: " + ", ".join(r[1] for r in bad)))
    sys.exit(1 if bad else 0)


try:
    from playwright.sync_api import sync_playwright
    from PIL import Image
except ImportError:
    print("SKIP: playwright or Pillow is not installed")
    sys.exit(0)
import browsing  # noqa: E402
import waits  # noqa: E402

PHONE = dict(viewport={"width": 402, "height": 874}, device_scale_factor=2, is_mobile=True, has_touch=True)
DESK = dict(viewport={"width": 1280, "height": 860}, device_scale_factor=1)
INK, PINK, GREEN = "#1f1b2e", "#ff48b0", "#00a95c"


# ------------------------------------------------------------- the drawing
def _line(x0, y0, x1, y1, color, size, t0, n=24, erase=False):
    pts = []
    for k in range(n):
        f = k / (n - 1)
        p = {"x": x0 + (x1 - x0) * f, "y": y0 + (y1 - y0) * f, "color": color, "size": size, "t": t0 + k * 16}
        if k == 0:
            p["start"] = True
        if erase:
            p["erase"] = True
        pts.append(p)
    return pts


def drawing():
    """Inside 500x600, so it lies on the Pad's 816x612 and on Flip's narrow
    page alike. g0 a line across; g1 crossing it later (on top where they
    cross); g2 see-through; g3 an eraser's stroke; g4-g6 three short lines a
    drag can cross; g7 a long line to watch a run along."""
    lines = [
        _line(60, 200, 480, 200, INK, 10, 0),
        _line(270, 60, 270, 340, INK, 10, 1000),
        _line(60, 380, 480, 380, "rgba(124, 92, 255, 0.5)", 14, 2000),
        _line(60, 430, 480, 430, "#f6f2ea", 30, 3000, erase=True),
        _line(120, 470, 120, 560, INK, 8, 4000, n=8),
        _line(200, 470, 200, 560, INK, 8, 5000, n=8),
        _line(280, 470, 280, 560, INK, 8, 6000, n=8),
        _line(40, 30, 490, 30, INK, 12, 7000, n=60),
    ]
    pts = [p for l in lines for p in l]
    return {"version": 2, "schemaVersion": 2, "playbackMode": "replay", "pauseMode": "tight",
            "frames": [{"strokes": pts, "strokeGroups": [len(l) for l in lines],
                        "baseSnapshot": None, "background": {"color": "#f6f2ea"}, "photo": None, "music": None}],
            "canvasSize": {"cssWidth": 816, "cssHeight": 612, "dpr": 1}, "title": "Recolor test"}


# What each editor calls its drawing, its canvas and its undo.
ED = {
    "/skribl-pad": {"cv": "canvas", "pts": "strokes", "groups": "strokeGroups", "rc": "SkriblPadRecolor",
                    "undo": "#undoBtn", "drawer": "() => openDrawer('draw')", "drawerOpen": "() => _padDrawerCtl.isOpen('draw')",
                    "dock": "#toolBar", "pen": "(h) => setPenColor(h)", "logical": "getCanvasLogicalSize()"},
    "/flip": {"cv": "pad", "pts": "frame().strokes", "groups": "frame().strokeGroups", "rc": "_recolor",
              "undo": "#undo", "drawer": "() => _flipDrawerCtl.open('draw')", "drawerOpen": "() => _flipDrawerCtl.isOpen('draw')",
              "dock": ".flip-tools", "pen": "(h) => setColor(h)", "logical": "({ width: CW, height: CH })"},
}


def load(q, route, d):
    if route == "/skribl-pad":
        q.evaluate("(d) => loadSkribl(d)", d)
    else:
        q.evaluate("""(d) => { const f = d.frames[0]; frames[0].strokes = f.strokes.map(p => Object.assign({}, p));
            frames[0].strokeGroups = f.strokeGroups.slice(); setBg(f.background.color); render(); buildStrip(); }""", d)
    q.wait_for_timeout(300)


def colours(q, route):
    """The first point's colour of each line, and whether every point of each agrees."""
    e = ED[route]
    return q.evaluate(f"""() => {{ const P = {e['pts']}, G = {e['groups']}; let a = 0;
        return G.map(n => {{ const c = P[a].color, same = P.slice(a, a + n).every(p => p.color === c); a += n; return same ? c : 'MIXED'; }}); }}""")


def screen_of(q, route, x, y):
    """Drawing units to the page's CSS px."""
    e = ED[route]
    return q.evaluate(f"""([x, y]) => {{ const r = {e['cv']}.getBoundingClientRect(), lg = {e['logical']};
        return {{ x: r.left + x * r.width / lg.width, y: r.top + y * r.height / lg.height }}; }}""", [x, y])


def tap(q, route, x, y):
    s = screen_of(q, route, x, y)
    q.touchscreen.tap(s["x"], s["y"])


def drag(q, route, pts, cdp, fingers=1):
    s = [screen_of(q, route, x, y) for x, y in pts]
    def touch(t, a):
        cdp.send("Input.dispatchTouchEvent", {"type": t, "touchPoints": a})
    touch("touchStart", [{"x": s[0]["x"], "y": s[0]["y"], "id": 1}])
    steps = 16
    for i in range(1, len(s)):
        for k in range(1, steps + 1):
            x = s[i - 1]["x"] + (s[i]["x"] - s[i - 1]["x"]) * k / steps
            y = s[i - 1]["y"] + (s[i]["y"] - s[i - 1]["y"]) * k / steps
            touch("touchMove", [{"x": x, "y": y, "id": 1}])
            q.wait_for_timeout(12)
    touch("touchEnd", [])


def armed(q, route):
    return q.evaluate(f"() => !!({ED[route]['rc']} && {ED[route]['rc']}.isArmed())")


def undo_depth(q, route):
    return q.evaluate("() => undoStack.length") if route == "/skribl-pad" else q.evaluate("() => actionLog.length")


def fresh(b, route, ctx_opts=PHONE, reduce=False):
    c = b.new_context(reduced_motion="reduce" if reduce else "no-preference", **ctx_opts)
    q = c.new_page()
    browsing.goto(q, BASE, route)
    q.evaluate("() => { window.SkriblHints && SkriblHints.hide && SkriblHints.hide(); }")
    return c, q


with sync_playwright() as pw:
    b = waits.instrument(pw.chromium.launch())

    # ================================================================ the button
    print("\nTHE BUTTON — beside the eyedropper, at the end of the Pen | Background row, on both")
    for route in ED:
        c, q = fresh(b, route)
        q.evaluate(ED[route]["drawer"]); q.wait_for_timeout(500)
        m = q.evaluate("""() => { const e = document.getElementById('eyedropperBtn'), r = document.getElementById('recolorBtn'),
            s = document.getElementById('paintTargetSeg'); if (!e || !r || !s) return null;
            const a = e.getBoundingClientRect(), z = r.getBoundingClientRect(), k = s.getBoundingClientRect();
            return { pair: e.parentElement === r.parentElement && e.nextElementSibling === r,
                     row: Math.abs((a.top + a.bottom) / 2 - (k.top + k.bottom) / 2) <= 1.5 && Math.abs((z.top + z.bottom) / 2 - (k.top + k.bottom) / 2) <= 1.5,
                     right: a.left > k.right && z.left > a.right, label: r.getAttribute('aria-label'), pressed: r.getAttribute('aria-pressed') }; }""")
        check(f"{route}: Recolor is the eyedropper's neighbour, the pair centred on the Pen | Background row",
              bool(m) and m["pair"] and m["row"] and m["right"], json.dumps(m))
        check(f"{route}: Recolor says what it is and is not pressed at rest",
              bool(m) and m["label"] == "Recolor lines" and m["pressed"] == "false", json.dumps(m))
        q.evaluate("() => document.querySelector('#paintTargetSeg [data-target=background]').click()"); q.wait_for_timeout(200)
        hid = q.evaluate("() => { const t = document.getElementById('colorTools'); return !!t && t.hidden && !t.offsetWidth; }")
        check(f"{route}: the two colour tools go with the pen's colours when Background is chosen", hid)
        c.close()
    for w in (320, 390, 402):
        c = b.new_context(viewport={"width": w, "height": 800}, device_scale_factor=2, is_mobile=True, has_touch=True)
        q = c.new_page(); browsing.goto(q, BASE, "/skribl-pad")
        q.evaluate("() => openDrawer('draw')"); q.wait_for_timeout(500)
        g = q.evaluate("""() => { const it = [...document.getElementById('colorGroup').children].filter(e => e.offsetWidth).map(e => e.getBoundingClientRect());
            return { n: it.length, min: Math.min(...it.slice(1).map((r, i) => r.left - it[i].right)) }; }""")
        need = 4 if w < 360 else 10
        check(f"at {w}px the colour row is the nine colours, at least {need}px apart", g["n"] == 9 and g["min"] >= need, json.dumps(g))
        # The touch area is the ::before ring (styles.css --tap-grow): each tool
        # 44 or more, and the two rings meet without crossing, so a tap at the
        # seam cannot reach the wrong one.
        t = q.evaluate("""() => { const e = document.getElementById('eyedropperBtn'), r = document.getElementById('recolorBtn');
            const g = el => { const b = el.getBoundingClientRect(), i = parseFloat(getComputedStyle(el, '::before').inset) || 0;
              return { l: b.left + i, r: b.right - i, w: b.width - 2 * i, h: b.height - 2 * i }; };
            const a = g(e), z = g(r); return { eye: Math.round(a.w), recolor: Math.round(z.w), tall: Math.round(Math.min(a.h, z.h)), cross: Math.round((a.r - z.l) * 10) / 10 }; }""")
        check(f"at {w}px each colour tool is 44px or more to the touch, and the two touch areas do not cross",
              min(t["eye"], t["recolor"], t["tall"]) >= 44 and t["cross"] <= 0, json.dumps(t))
        c.close()

    # ================================================================== the mode
    print("\nTHE MODE — the bar takes the dock's row; the colour is the pen's; Done and Escape give the dock back")
    for route in ED:
        e = ED[route]
        c, q = fresh(b, route)
        load(q, route, drawing())
        cv0 = q.evaluate(f"() => {{ const r = {e['cv']}.getBoundingClientRect(); return [r.left, r.top, r.width, r.height]; }}")
        q.evaluate(e["drawer"]); q.wait_for_timeout(500)
        q.click("#recolorBtn"); q.wait_for_timeout(450)
        m = q.evaluate(f"""() => {{ const bar = document.querySelector('.recolor-bar'), d = document.querySelector('{e['dock']}');
            const br = bar.getBoundingClientRect(), dr = d.getBoundingClientRect(), pen = document.getElementById('penToolBtn').getBoundingClientRect();
            const hit = document.elementFromPoint(pen.left + pen.width / 2, pen.top + pen.height / 2);
            const cv = {e['cv']}.getBoundingClientRect();
            return {{ fit: Math.abs(br.left - dr.left) <= 1 && Math.abs(br.right - dr.right) <= 1 && Math.abs(br.top - dr.top) <= 1 && Math.abs(br.bottom - dr.bottom) <= 1,
                     shown: getComputedStyle(bar).visibility === 'visible' && !bar.inert, penHit: !!hit && !!hit.closest('#penToolBtn'),
                     penVis: getComputedStyle(document.getElementById('penToolBtn')).visibility,
                     inBar: !!hit && bar.contains(hit) || hit === bar, drawer: ({e['drawerOpen']})(),
                     cv: [cv.left, cv.top, cv.width, cv.height], pressed: document.getElementById('recolorBtn').getAttribute('aria-pressed'),
                     say: (bar.querySelector('.recolor-say') || {{}}).textContent }}; }}""")
        check(f"{route}: Recolor closes the drawer and its bar takes the dock's row",
              m["fit"] and m["shown"] and not m["drawer"], json.dumps(m))
        check(f"{route}: the dock's own pen is out of reach under the bar, for a finger and for the keyboard",
              not m["penHit"] and m["penVis"] == "hidden", json.dumps(m))
        check(f"{route}: the canvas stays where it was", all(abs(a - b_) <= 0.5 for a, b_ in zip(cv0, m["cv"])), f"{cv0} -> {m['cv']}")
        # On a touch screen it says the hold too (the lens; the AIMING rows).
        check(f"{route}: the bar says what to do and Recolor is pressed",
              m["say"] == "Tap a line, or hold to aim" and m["pressed"] == "true", json.dumps(m))
        q.evaluate(f"() => ({e['pen']})('{PINK}')"); q.wait_for_timeout(150)
        q.click(".recolor-swatch"); q.wait_for_timeout(450)
        opened = q.evaluate(e["drawerOpen"])
        q.evaluate("() => { const d = [...document.querySelectorAll('#colorGroup .color-dot[data-color]')].find(x => x.dataset.color.toLowerCase() === '#00a95c'); d.click(); }")
        q.wait_for_timeout(450)
        after = q.evaluate(f"""() => ({{ open: ({e['drawerOpen']})(), dot: getComputedStyle(document.querySelector('.recolor-dot')).backgroundColor,
                                       armed: {e['rc']}.isArmed() }})""")
        check(f"{route}: the bar's colour opens the drawer, and a colour picked there closes it, the bar following",
              opened and not after["open"] and after["armed"] and after["dot"] == "rgb(0, 169, 92)", f"opened {opened}, {after}")
        q.click(".recolor-done"); q.wait_for_timeout(400)
        gone = q.evaluate(f"""() => {{ const bar = document.querySelector('.recolor-bar'), pen = document.getElementById('penToolBtn').getBoundingClientRect();
            const hit = document.elementFromPoint(pen.left + pen.width / 2, pen.top + pen.height / 2);
            return {{ armed: {e['rc']}.isArmed(), hidden: getComputedStyle(bar).visibility === 'hidden' && bar.inert, pen: !!hit && !!hit.closest('#penToolBtn') }}; }}""")
        check(f"{route}: Done gives the dock back", not gone["armed"] and gone["hidden"] and gone["pen"], json.dumps(gone))
        q.evaluate(f"() => {e['rc']}.arm()"); q.wait_for_timeout(250)
        q.keyboard.press("Escape"); q.wait_for_timeout(250)
        check(f"{route}: Escape ends it too", not armed(q, route))
        c.close()

    # =============================================================== the pointer
    print("\nTHE POINTER — on a desk the mode's crosshair is over the canvas, and stays after a colour change")
    # The owner, on Flip: "as soon as I change the color, the pointer
    # dissapears over the canvas." The mode puts the pen's ring away, and
    # Flip's colour pick set the pen's cursor ('none', for the ring) after the
    # mode had set its own. Flip's row is that scenario. The Pad set them the
    # other way round and could not lose it; its row asks the same of a loaded
    # drawing, whose lock writes 'not-allowed' on the canvas, which is the
    # stylesheet's rule doing the work (styles.css, flip.css: body.recoloring).
    for route in ED:
        e = ED[route]
        c, q = fresh(b, route, DESK)
        load(q, route, drawing())
        q.evaluate(e["drawer"]); q.wait_for_timeout(400)
        q.click("#recolorBtn"); q.wait_for_timeout(400)

        def pointer(x, y):
            s = screen_of(q, route, x, y)
            q.mouse.move(s["x"] + 40, s["y"] + 40)
            q.mouse.move(s["x"], s["y"], steps=4); q.wait_for_timeout(120)
            return q.evaluate("""([x, y]) => { const h = document.elementFromPoint(x, y);
                return { on: h && (h.id || h.className), cursor: h && getComputedStyle(h).cursor }; }""", [s["x"], s["y"]])
        was = pointer(300, 300)
        check(f"{route}: in Recolor the pointer over the canvas is a crosshair",
              armed(q, route) and was["cursor"] == "crosshair", json.dumps(was))
        q.click(".recolor-swatch"); q.wait_for_timeout(400)
        q.evaluate("() => [...document.querySelectorAll('#colorGroup .color-dot[data-color]')].find(x => x.dataset.color.toLowerCase() === '#00a95c').click()")
        q.wait_for_timeout(400)
        now = pointer(300, 300)
        check(f"{route}: ...and still is after a new colour from the bar",
              armed(q, route) and now["cursor"] == "crosshair", json.dumps(now))
        c.close()

    # ==================================================================== a tap
    print("\nA TAP — the line under it, the topmost, its opacity kept; nothing for nothing; never an eraser; no pinch")
    for route in ED:
        e = ED[route]
        c, q = fresh(b, route)
        load(q, route, drawing())
        q.evaluate(f"() => {{ ({e['pen']})('{GREEN}'); {e['rc']}.arm(); }}"); q.wait_for_timeout(300)
        c0 = colours(q, route)
        u0 = undo_depth(q, route)
        tap(q, route, 160, 300); q.wait_for_timeout(500)          # empty canvas
        check(f"{route}: a tap on nothing changes nothing and leaves no undo step",
              colours(q, route) == c0 and undo_depth(q, route) == u0, f"undo {u0} -> {undo_depth(q, route)}")
        tap(q, route, 270, 200); q.wait_for_timeout(500)          # where g0 and g1 cross: g1 is on top
        c1 = colours(q, route)
        check(f"{route}: a tap where two lines cross recolours the one on top, and only it",
              c1[1] == GREEN and c1[0] == INK and all(c1[i] == c0[i] for i in range(len(c0)) if i != 1), json.dumps(c1))
        tap(q, route, 400, 380); q.wait_for_timeout(500)          # the see-through line
        check(f"{route}: a see-through line takes the colour and keeps its opacity",
              colours(q, route)[2] == "rgba(0, 169, 92, 0.5)", colours(q, route)[2])
        tap(q, route, 400, 430); q.wait_for_timeout(500)          # the eraser's stroke
        check(f"{route}: an eraser's stroke is never hit", colours(q, route)[3] == c0[3], colours(q, route)[3])
        # Pinch: one finger down on a line, then a second; neither lifts as a tap.
        cdp = c.new_cdp_session(q)
        s1, s2 = screen_of(q, route, 120, 515), screen_of(q, route, 420, 300)
        cdp.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [{"x": s1["x"], "y": s1["y"], "id": 1}]})
        q.wait_for_timeout(60)
        cdp.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [{"x": s1["x"], "y": s1["y"], "id": 1}, {"x": s2["x"], "y": s2["y"], "id": 2}]})
        q.wait_for_timeout(60)
        cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
        q.wait_for_timeout(400)
        check(f"{route}: the first finger of a pinch recolours nothing", colours(q, route)[4] == INK, colours(q, route)[4])
        c.close()

    # =================================================================== a drag
    print("\nA DRAG — each line it crosses, once; one Undo takes it all back")
    for route in ED:
        e = ED[route]
        c, q = fresh(b, route)
        load(q, route, drawing())
        q.evaluate(f"() => {{ ({e['pen']})('{PINK}'); {e['rc']}.arm(); }}"); q.wait_for_timeout(300)
        c0 = colours(q, route)
        u0 = undo_depth(q, route)
        drag(q, route, [(80, 515), (330, 515)], c.new_cdp_session(q)); q.wait_for_timeout(600)
        c1 = colours(q, route)
        check(f"{route}: a drag recolours the three lines it crosses and no other",
              c1[4] == c1[5] == c1[6] == PINK and all(c1[i] == c0[i] for i in range(len(c0)) if i not in (4, 5, 6)), json.dumps(c1))
        check(f"{route}: the drag is one step of undo", undo_depth(q, route) == u0 + 1, f"{u0} -> {undo_depth(q, route)}")
        if route == "/skribl-pad":
            # One gesture, one moment: a replay runs the three together.
            ks = q.evaluate("() => recolors.map(r => r.k)")
            check(f"{route}: the three it crossed are kept as one moment", ks == [0, 0, 0], json.dumps(ks))
        q.click(".recolor-undo"); q.wait_for_timeout(400)
        check(f"{route}: one Undo, from the bar, takes the whole drag back", colours(q, route) == c0, json.dumps(colours(q, route)))
        c.close()

    # ================================================================= the run
    print("\nTHE RUN — the colour runs along the line from the finger; at once under Reduce Motion")

    # Read on every frame IN the page, from the overlay that draws the run:
    # a screenshot lands a frame or ten late, and how late is the machine's.
    # Where the overlay is opaque the screen shows it (it lies over the
    # drawing, which already wears the new colour); where it is clear, the
    # drawing shows through.
    PROBE = """([x0, x1, y]) => new Promise(done => {
        const t0 = performance.now(), out = [];
        (function f(now) {
          try {
            const o = document.querySelector('.recolor-run');
            if (o && o.width) {
              // backing px a drawing unit (Flip's CW is a lexical global, the Pad's size a function)
              const u = o.width / (typeof CW !== 'undefined' ? CW : getCanvasLogicalSize().width);
              const g = o.getContext('2d');
              const near = [...g.getImageData(Math.round(x0 * u), Math.round(y * u), 1, 1).data];
              const far = [...g.getImageData(Math.round(x1 * u), Math.round(y * u), 1, 1).data];
              out.push({ dt: Math.round(now - t0), near, far, on: true });
            } else out.push({ dt: Math.round(now - t0), on: false });
          } catch (err) { out.push({ dt: Math.round(now - t0), on: false, err: String(err) }); }
          if (now - t0 < 700) requestAnimationFrame(f); else done(out);
        })(t0);
      })"""

    def near(a, b_, tol=40):
        return sum(abs(x - y) for x, y in zip(a, b_)) <= tol

    INK_RGB, G_RGB = (31, 27, 46), (0, 169, 92)
    for route in ED:
        e = ED[route]
        c, q = fresh(b, route)
        load(q, route, drawing())
        q.evaluate(f"() => {{ ({e['pen']})('{GREEN}'); {e['rc']}.arm(); }}"); q.wait_for_timeout(300)
        # The probe starts before the tap, so it sees the run's first frame.
        q.evaluate("(probe) => { window.__rcProbe = (new Function('return ' + probe))()([50, 485, 30]); }", PROBE)
        tap(q, route, 45, 30)
        out = q.evaluate("() => window.__rcProbe")
        mid = [f for f in out if f["on"]]
        part = [f for f in mid if f["far"][3] > 200 and near(f["far"][:3], INK_RGB) and f["near"][3] == 0]
        later = [f for f in out if f["dt"] > 520]
        check(f"{route}: partway, the near end shows the new colour and the far end still the old",
              len(part) >= 3, f"{len(part)} of {len(mid)} frames with the overlay; first {mid[:1]}")
        check(f"{route}: then the far end takes it too, and the run's overlay goes",
              bool(later) and not any(f["on"] for f in later) and not q.evaluate("() => !!document.querySelector('.recolor-run')"),
              f"{len(later)} late frames, overlay {[f['on'] for f in later][:3]}")
        sf = screen_of(q, route, 485, 30)
        im = Image.open(io.BytesIO(q.screenshot(clip={"x": sf["x"] - 1, "y": sf["y"] - 1, "width": 3, "height": 3}))).convert("RGB")
        check(f"{route}: and the screen shows the new colour at the far end", near(im.getpixel((im.width // 2, im.height // 2)), G_RGB),
              str(im.getpixel((im.width // 2, im.height // 2))))
        c.close()
        c, q = fresh(b, route, reduce=True)
        load(q, route, drawing())
        q.evaluate(f"() => {{ ({e['pen']})('{GREEN}'); {e['rc']}.arm(); }}"); q.wait_for_timeout(300)
        q.evaluate("(probe) => { window.__rcProbe = (new Function('return ' + probe))()([50, 485, 30]); }", PROBE)
        tap(q, route, 45, 30)
        out = q.evaluate("() => window.__rcProbe")
        cs = colours(q, route)
        check(f"{route}: under Reduce Motion the line is new at once, with no overlay ever",
              cs[7] == GREEN and not any(f["on"] for f in out), f"{cs[7]}, overlay frames {sum(1 for f in out if f['on'])}")
        c.close()

    # ======================================================== the Pad's record
    print("\nTHE PAD KEEPS THE MOMENT — for the replay; through a post, a draft and an undo")
    c, q = fresh(b, "/skribl-pad")
    load(q, "/skribl-pad", drawing())
    q.evaluate(f"() => {{ setPenColor('{PINK}'); SkriblPadRecolor.arm(); }}"); q.wait_for_timeout(300)
    tap(q, "/skribl-pad", 150, 200); q.wait_for_timeout(450)
    r = q.evaluate("() => JSON.parse(JSON.stringify(recolors))")
    n = q.evaluate("() => strokes.length")
    check("a recolour on a finished take is kept: the line, its colours, the drawing's length, its moment, no clock",
          len(r) == 1 and r[0]["g"] == 0 and r[0]["was"] == INK and r[0]["to"] == PINK and r[0]["n"] == n and r[0].get("k") == 0
          and "t" not in r[0] and 0 <= r[0]["at"] < 24, json.dumps(r))
    q.evaluate("() => { SkriblPadRecolor.disarm(); beginRecording(true); }"); q.wait_for_timeout(700)
    q.evaluate(f"() => {{ setPenColor('{GREEN}'); SkriblPadRecolor.arm(); }}"); q.wait_for_timeout(200)
    tap(q, "/skribl-pad", 400, 380); q.wait_for_timeout(400)
    r = q.evaluate("() => JSON.parse(JSON.stringify(recolors))")
    clock = q.evaluate("() => Date.now() - startTime")
    check("one made while a take records carries the take's clock, and is the next moment",
          len(r) == 2 and isinstance(r[1].get("t"), (int, float)) and 300 <= r[1]["t"] <= clock and r[1].get("k") == 1,
          json.dumps(r[1:]) + f" clock {clock}")
    q.evaluate("() => { SkriblPadRecolor.disarm(); endRecordingTake(); }"); q.wait_for_timeout(300)
    pay = q.evaluate("() => serializeSkribl()")
    check("a post carries them, in its frame", len(pay["frames"][0].get("recolors") or []) == 2, json.dumps(pay["frames"][0].get("recolors")))
    req = urllib.request.Request(BASE + "/api/skribls", data=json.dumps(pay).encode(), headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            made = json.loads(resp.read())
        sid = made.get("id") or made.get("skribl", {}).get("id")
        with urllib.request.urlopen(BASE + f"/api/skribls/{sid}", timeout=20) as resp:
            got = json.loads(resp.read())
        gp = got.get("skribl") or {}
        gp = json.loads(gp) if isinstance(gp, str) else gp
        kept = (gp.get("frames") or [{}])[0].get("recolors")
        check("the server takes the post and gives the recolours back", kept == pay["frames"][0]["recolors"], json.dumps(kept)[:200])
    except Exception as ex:  # noqa: BLE001 -- the failure is the finding
        check("the server takes the post and gives the recolours back", False, repr(ex)[:300])
    q.evaluate("() => writeAutosave()"); q.wait_for_timeout(200)
    q.reload(wait_until="load"); waits.settle(q, 1500)
    back = q.evaluate("() => ({ n: recolors.length, c: strokes.length && strokes[0].color })")
    check("a draft brings them back with the colours on a reload", back["n"] == 2 and back["c"] == PINK, json.dumps(back))
    # The reload rebuilds Undo a line at a time (editor_draft.js). A line
    # undone there takes with it the recolours made after it, which a line
    # drawn next would otherwise put in the middle of its own replay.
    try:
        q.wait_for_function("() => !document.getElementById('undoBtn').disabled", timeout=5000)
        q.evaluate("() => document.getElementById('undoBtn').click()"); q.wait_for_timeout(300)
        after = q.evaluate("() => ({ n: recolors.length, g: strokeGroups.length })")
    except Exception as ex:  # noqa: BLE001 -- the failure is the finding
        after = {"error": repr(ex)[:160]}
    check("after the reload, Undo of the last line keeps no recolour made after it", after.get("n") == 0, json.dumps(after))
    c.close()
    # An undone recolour, then a reload: the drawing as it stands, never the undone colour.
    c, q = fresh(b, "/skribl-pad")
    load(q, "/skribl-pad", drawing())
    q.evaluate(f"() => {{ setPenColor('{PINK}'); SkriblPadRecolor.arm(); }}"); q.wait_for_timeout(300)
    tap(q, "/skribl-pad", 150, 200); q.wait_for_timeout(450)
    q.click(".recolor-undo"); q.wait_for_timeout(300)
    q.evaluate("() => writeAutosave()"); q.wait_for_timeout(200)
    q.reload(wait_until="load"); waits.settle(q, 1500)
    s = screen_of(q, "/skribl-pad", 150, 200)
    im = Image.open(io.BytesIO(q.screenshot(clip={"x": s["x"] - 1, "y": s["y"] - 1, "width": 3, "height": 3}))).convert("RGB")
    st = q.evaluate("() => ({ c: strokes[0].color, n: recolors.length })")
    check("a recolour undone before a reload stays undone after it, on the canvas too",
          st["c"] == INK and st["n"] == 0 and near(im.getpixel((im.width // 2, im.height // 2)), INK_RGB),
          f"{st}, pixel {im.getpixel((im.width // 2, im.height // 2))}")
    # A fresh take paints the lines so far into its base and starts the list of
    # points again; their recolours go with them, or they would name the new
    # take's lines by the old ones' numbers.
    fresh_take = q.evaluate(f"""() => {{ setPenColor('{PINK}'); SkriblPadRecolor.arm(); return true; }}""")
    tap(q, "/skribl-pad", 150, 200); q.wait_for_timeout(450)
    had = q.evaluate("() => { SkriblPadRecolor.disarm(); const n = recolors.length; beginRecording(false); return { had: n, now: recolors.length, pts: strokes.length }; }")
    q.evaluate("() => endRecordingTake()")
    check("a fresh take starts with no recolours, its old lines being its base now",
          fresh_take and had["had"] == 1 and had["now"] == 0 and had["pts"] == 0, json.dumps(had))
    c.close()

    # =================================================================== Flip
    print("\nFLIP — one step a gesture; the thumbnail; a fill is one line; a generated page keeps it; Select's Color")
    c, q = fresh(b, "/flip")
    load(q, "/flip", drawing())
    q.evaluate(f"() => {{ setColor('{GREEN}'); _recolor.arm(); }}"); q.wait_for_timeout(300)
    thumb0 = q.evaluate("() => { const cv = document.querySelector('#strip .frame canvas'); return cv && cv.toDataURL(); }")
    tap(q, "/flip", 150, 200); q.wait_for_timeout(500)
    last = q.evaluate("() => { const m = actionLog[actionLog.length - 1]; return m && [m.type, m.label]; }")
    check("a recolour is one page entry of undo, named for what it did", last == ["selframe", "Recolor"], json.dumps(last))
    thumb1 = q.evaluate("() => { const cv = document.querySelector('#strip .frame canvas'); return cv && cv.toDataURL(); }")
    check("the page's thumbnail follows the colour", bool(thumb0) and thumb0 != thumb1)
    # A fill: a closed box, filled, then one tap on the fill.
    q.evaluate("""() => { const f = frame(); const box = [[80,600],[300,600],[300,800],[80,800],[80,600]];
        const pts = []; for (let k = 0; k < box.length; k++) pts.push({ x: box[k][0], y: box[k][1], color: '#1f1b2e', size: 6, t: 90000 + k * 20, start: k === 0 });
        f.strokes.push(...pts); f.strokeGroups.push(pts.length); render(); }""")
    q.evaluate("() => { _recolor.disarm(); setColor('#ff6c2f'); setTool('fill'); }"); q.wait_for_timeout(150)
    tap(q, "/flip", 190, 700); q.wait_for_timeout(400)
    bands = q.evaluate("""() => { const f = frame(), G = f.strokeGroups; let a = 0, n = 0; const cols = new Set();
        G.forEach(k => { if (f.strokes[a].color === '#ff6c2f') { n++; } a += k; }); return n; }""")
    q.evaluate(f"() => {{ setTool('pen'); setColor('{PINK}'); _recolor.arm(); }}"); q.wait_for_timeout(200)
    tap(q, "/flip", 190, 700); q.wait_for_timeout(500)
    filled = q.evaluate("""() => { const f = frame(), G = f.strokeGroups; let a = 0, n = 0, left = 0;
        G.forEach(k => { const c = f.strokes[a].color; if (c === '#ff48b0') n++; if (c === '#ff6c2f') left++; a += k; }); return [n, left]; }""")
    check("a fill's bands are one line: a tap on it recolours every band", bands >= 3 and filled[1] == 0 and filled[0] >= bands,
          f"{bands} bands; after the tap {filled[0]} pink, {filled[1]} still orange")
    c.close()
    # A generated page, recoloured, is saved as it now looks.
    c, q = fresh(b, "/flip")
    load(q, "/flip", drawing())
    q.evaluate("() => { addFrame(true); const f = frame(); f.strokes.forEach(p => { p.x += 40; }); render(); go(0); }"); q.wait_for_timeout(300)
    q.evaluate("() => { go(0); addTween(); }"); q.wait_for_timeout(600)
    gi = q.evaluate("() => frames.findIndex(f => !!genRecipe.get(f))")
    if gi < 0:
        check("a recoloured tween page is saved as it now looks, not as its recipe", False, "no generated page was made")
    else:
        q.evaluate(f"(i) => {{ go(i); setColor('{GREEN}'); _recolor.arm(); }}", gi); q.wait_for_timeout(300)
        tap(q, "/flip", 150 + 20, 200); q.wait_for_timeout(500)
        saved = q.evaluate("(i) => { const d = serializeFlip({ recipes: true }); const f = d.frames[i]; return { gen: !!f.gen, green: (f.strokes || []).some(p => p.color === '#00a95c') }; }", gi)
        check("a recoloured tween page is saved as it now looks, not as its recipe", (not saved["gen"]) and saved["green"], json.dumps(saved))
    c.close()
    # Select's Color, and its count on a phone and a desk.
    for opts, label in ((PHONE, "a phone"), (DESK, "a desk")):
        c, q = fresh(b, "/flip", ctx_opts=opts)
        load(q, "/flip", drawing())
        q.evaluate(f"""() => {{ setColor('{GREEN}'); setTool('select'); const g = frames[0].strokeGroups; let at = 0; const sp = [];
            for (let i = 0; i < g.length; i++) {{ if (i >= 4 && i <= 6) sp.push([at, at + g[i]]); at += g[i]; }}
            selSpans = sp; syncSelBar(); selRender(null); }}"""); q.wait_for_timeout(250)
        who = q.evaluate("() => document.getElementById('sbWho').innerText.trim()")
        fits = q.evaluate("""() => { const bar = document.getElementById('selbar'), r = bar.getBoundingClientRect();
            return [...bar.querySelectorAll('button')].filter(b => !b.hidden && b.offsetWidth).every(b => { const x = b.getBoundingClientRect(); return x.left >= r.left - 0.5 && x.right <= r.right + 0.5; }); }""")
        want = "3" if opts is PHONE else "3 strokes"
        check(f"on {label} the Select bar's count reads '{want}' and every button fits", who == want and fits, f"{who!r}, fits {fits}")
        if opts is PHONE:
            u0 = undo_depth(q, "/flip")
            q.click("#sbColor"); q.wait_for_timeout(500)
            cs = colours(q, "/flip")
            check("Color gives every selected line the pen's colour, and nothing else", cs[4] == cs[5] == cs[6] == GREEN and cs[0] == INK, json.dumps(cs))
            check("...in one step of undo", undo_depth(q, "/flip") == u0 + 1, f"{u0} -> {undo_depth(q, '/flip')}")
            dot = q.evaluate("() => getComputedStyle(document.querySelector('#sbColor .sb-color-dot')).backgroundColor")
            check("Color's glyph is the pen's colour", dot == "rgb(0, 169, 92)", dot)
        c.close()

    # ===================================================== the button's drop
    # The owner, after v329: the three drops were "kind of confusing looking"
    # at their real size; C of the mock: one drop lands on the line and the
    # line takes its colour from there, in the PEN'S colour. Read off the
    # PAINTED button, both editors, both themes, for every swatch the palette
    # offers: the drop wears the pen's colour, the line starts in the button's
    # grey and ends in the pen's colour, and the drop reads 3:1 against the
    # button (a pale pen is outlined in the grey, lib/recolor.js). Recolor's
    # tip in How it works is told the same colour.
    print("\nTHE BUTTON'S DROP — in the pen's colour, a line that takes it, and readable on every pen")
    from PIL import Image

    def _lum(rgb):
        c = [v / 255 for v in rgb]
        c = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
        return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]

    def _ratio(a, b_):
        hi, lo = sorted((_lum(a), _lum(b_)), reverse=True)
        return (hi + 0.05) / (lo + 0.05)

    def _rgb(css):
        return tuple(int(v) for v in re.findall(r"\d+", css)[:3])
    for route in ED:
        for theme in ("light", "dark"):
            c = b.new_context(color_scheme=theme, **{**PHONE, "device_scale_factor": 4})
            q = c.new_page()
            browsing.goto(q, BASE, route)
            q.evaluate("() => { window.SkriblHints && SkriblHints.hide && SkriblHints.hide(); }")
            q.evaluate(ED[route]["drawer"]); q.wait_for_timeout(600)
            ground = _rgb(q.evaluate("() => getComputedStyle(document.getElementById('recolorBtn')).backgroundColor"))
            grey = _rgb(q.evaluate("() => getComputedStyle(document.getElementById('recolorBtn')).color"))
            pens = q.evaluate("() => [...document.querySelectorAll('#colorGroup .color-dot[data-color]')].map(d => d.dataset.color.toLowerCase())")
            wrong, flat, faint, tip = [], [], [], []
            for pen in pens:
                q.evaluate("(h) => document.querySelector(`#colorGroup .color-dot[data-color='${h}' i]`).click()", pen)
                q.wait_for_timeout(120)
                # Flip's colour popout closes on a pick (it covers the canvas):
                # open it again to read the button.
                if not q.locator("#recolorBtn").is_visible():
                    q.evaluate(ED[route]["drawer"]); q.wait_for_timeout(500)
                ink = tuple(int(pen[i:i + 2], 16) for i in (1, 3, 5))
                im = Image.open(io.BytesIO(q.locator("#recolorBtn svg").screenshot())).convert("RGB")
                w, h = im.size
                px = im.load()
                near = lambda p_, c_: sum((p_[i] - c_[i]) ** 2 for i in range(3)) < 40 ** 2
                drop = sum(1 for y in range(int(h * 0.55)) for x in range(int(w * 0.6)) if near(px[x, y], ink))
                line_l = sum(1 for y in range(int(h * 0.55), h) for x in range(int(w * 0.33)) if near(px[x, y], grey))
                line_r = sum(1 for y in range(int(h * 0.55), h) for x in range(int(w * 0.55), w) if near(px[x, y], ink))
                legible = sum(1 for y in range(int(h * 0.55)) for x in range(int(w * 0.6)) if _ratio(px[x, y], ground) >= 3)
                if drop < 20:
                    wrong.append((pen, drop))
                if line_l < 6 or line_r < 6:
                    flat.append((pen, line_l, line_r))
                if legible < 40:
                    faint.append((pen, legible, round(_ratio(ink, ground), 2)))
                t = q.evaluate("() => { const s = document.querySelector('.help-tip .rc-inks'); return s ? s.style.getPropertyValue('--recolor-ink') : null; }")
                if t != pen:
                    tip.append((pen, t))
            check(f"{route} {theme}: the Recolor button's drop wears the pen's colour, for every swatch",
                  len(pens) >= 7 and not wrong, f"{len(pens)} pens; not in the drop: {wrong}")
            check(f"{route} {theme}: ...and its line starts grey and ends in the pen's colour",
                  not flat, f"(pen, grey px at the start, pen px at the end): {flat}")
            check(f"{route} {theme}: ...and the drop reads 3:1 against the button on every pen, a pale one outlined",
                  not faint, f"against rgb{ground}, (pen, px at 3:1+, the pen's own ratio): {faint}")
            check(f"{route} {theme}: ...and Recolor's tip in How it works is told the same colour",
                  not tip, f"(pen, the tip's colour): {tip}")
            c.close()

    # ================================================================== the ends
    # ================================================================ aiming
    # THE LENS (the owner: "the recolor should have the same magnifier as color
    # picker, but just so you can pick the stroke"; the lens mock, "All yes").
    # Three thin lines 12 units apart (about 5px on a phone): a finger covers
    # all three. A finger held still brings up the lens above it, the line
    # under it lit; sliding chooses another; letting go recolours the one lit
    # and no other, one step of undo. A quick tap is still a tap; a second
    # finger while aiming changes nothing. Near the top of the screen the lens
    # stands beside the finger. A mouse lights the line it would catch, with
    # no lens, and a click takes that line. The bar's Redo puts back what its
    # Undo took.
    print("\nAIMING — hold still for the lens, slide, let go; a tap is a tap; a mouse lights the line; Redo")
    AIM_Y = (250, 262, 274, 290, 306)      # three to aim among; one for a tap, one for Redo

    def aiming_drawing():
        d = drawing()
        f = d["frames"][0]
        extra = [_line(100, y, 420, y, INK, 3, 9000 + k * 1000, n=30) for k, y in enumerate(AIM_Y)]
        extra.append(_line(100, 22, 420, 22, INK, 3, 15000, n=30))        # a line along the top edge
        for l in extra:
            f["strokes"] += l
            f["strokeGroups"].append(len(l))
        return d

    AIM = """() => { const r = %s; return r && r.aimState ? r.aimState() : { aiming: false, lit: null, lens: null, none: true }; }"""
    LENSPX = """(which) => { const c = document.querySelector('.recolor-lens canvas'); if (!c || c.closest('[hidden]')) return null;
        const x = c.getContext('2d'), w = c.width, h = c.height, R = (53 + 5.5 / 2) / (53 + 5.5 + 1) * w / 2;
        const at = (dy) => [...x.getImageData(Math.round(w / 2), Math.round(h / 2 + dy * R), 1, 1).data].slice(0, 3);
        return { top: at(-1), bottom: at(1) }; }"""

    def near_rgb(px, hexc, tol=40):
        return px is not None and sum(abs(a - int(hexc[i:i + 2], 16)) for a, i in zip(px, (1, 3, 5))) <= tol

    def touch_at(cdp, t, pts):
        cdp.send("Input.dispatchTouchEvent", {"type": t, "touchPoints": [{"x": x, "y": y, "id": k + 1} for k, (x, y) in enumerate(pts)]})

    for route in ED:
        e = ED[route]
        rc = e["rc"]
        c, q = fresh(b, route)
        load(q, route, aiming_drawing())
        q.evaluate(f"() => {{ ({e['pen']})('{GREEN}'); {rc}.arm(); }}"); q.wait_for_timeout(300)
        n0 = len(colours(q, route))
        gA, gB, gC, gD, gE = n0 - 6, n0 - 5, n0 - 4, n0 - 3, n0 - 2
        cdp = c.new_cdp_session(q)
        A, C = screen_of(q, route, 260, AIM_Y[0]), screen_of(q, route, 260, AIM_Y[2])
        u0 = undo_depth(q, route)
        touch_at(cdp, "touchStart", [(A["x"], A["y"])]); q.wait_for_timeout(120)
        early = q.evaluate(AIM % rc)
        q.wait_for_timeout(450)
        s1 = q.evaluate(AIM % rc)
        px = q.evaluate(LENSPX, None)
        lens = s1 and s1["lens"]
        check(f"{route}: a finger held still brings up the lens (not at once: a tap is not a hold), the line under it lit",
              not early["aiming"] and early["lens"] is None and s1["aiming"] and s1["lit"] == [gA, gA] and lens is not None,
              f"early {early}, then {s1}")
        check(f"{route}: the lens stands above the finger, clear of the fingertip and whole on the screen",
              bool(lens) and lens["top"] + lens["height"] <= A["y"] - 22 + 0.5 and lens["top"] >= 0 and lens["left"] >= 0
              and lens["left"] + lens["width"] <= 402 and abs(lens["left"] + lens["width"] / 2 - A["x"]) <= 1, f"{lens}, finger at {A}")
        check(f"{route}: its ring says before and after: the line's colour above, the pen's below",
              px is not None and near_rgb(px["top"], INK) and near_rgb(px["bottom"], GREEN), str(px))
        steps = 8
        for k in range(1, steps + 1):
            touch_at(cdp, "touchMove", [(A["x"], A["y"] + (C["y"] - A["y"]) * k / steps)]); q.wait_for_timeout(16)
        q.wait_for_timeout(120)
        s2 = q.evaluate(AIM % rc)
        mid = colours(q, route)
        check(f"{route}: sliding chooses another line, and nothing changes while aiming",
              s2 and s2["aiming"] and s2["lit"] == [gC, gC] and mid[gA] == mid[gB] == mid[gC] == INK, f"{s2}; {mid[gA:gC + 1]}")
        touch_at(cdp, "touchEnd", []); q.wait_for_timeout(600)
        s3, c3 = q.evaluate(AIM % rc), colours(q, route)
        check(f"{route}: letting go gives the lit line the colour, and no other, one step of undo, the lens gone",
              c3[gC] == GREEN and c3[gA] == INK and c3[gB] == INK and undo_depth(q, route) == u0 + 1
              and s3 and not s3["aiming"] and s3["lens"] is None and s3["lit"] is None, f"{c3[gA:gC + 1]}, undo {u0} -> {undo_depth(q, route)}, {s3}")
        # Each row below reads only what its own gesture did, against the
        # drawing just before it, on a line of its own where it needs one.
        D = screen_of(q, route, 260, AIM_Y[3])
        c_before = colours(q, route)
        # Read at 150ms: still a quick tap (the lens waits 330), and past the
        # moment Flip's press keeps the page busy (over 60ms), so a lens that
        # came at once would show here.
        touch_at(cdp, "touchStart", [(D["x"], D["y"])]); q.wait_for_timeout(150)
        mid_tap = q.evaluate(AIM % rc)
        touch_at(cdp, "touchEnd", []); q.wait_for_timeout(600)
        c4 = colours(q, route)
        check(f"{route}: a quick tap is still a tap: the line under it, at once, and no lens on the way",
              c_before[gD] == INK and c4[gD] == GREEN and all(c4[i] == c_before[i] for i in range(len(c4)) if i != gD)
              and not mid_tap["aiming"] and mid_tap["lens"] is None, f"{c_before[gD]} -> {c4[gD]}, during {mid_tap}")
        u1, c_before = undo_depth(q, route), colours(q, route)
        touch_at(cdp, "touchStart", [(A["x"], A["y"])]); q.wait_for_timeout(500)
        held = q.evaluate(AIM % rc)
        touch_at(cdp, "touchStart", [(A["x"], A["y"]), (A["x"] + 120, A["y"] + 40)]); q.wait_for_timeout(80)
        pinch = q.evaluate(AIM % rc)
        touch_at(cdp, "touchEnd", []); q.wait_for_timeout(500)
        check(f"{route}: a second finger while aiming changes nothing and puts the lens away",
              held["aiming"] and not pinch["aiming"] and pinch["lens"] is None
              and colours(q, route) == c_before and undo_depth(q, route) == u1, f"held {held}, then {pinch}; undo {u1} -> {undo_depth(q, route)}")
        # THE BAR'S REDO: after a tap of its own and the bar's Undo, on, and it
        # puts the colour back; then off, with nothing left to put back.
        E = screen_of(q, route, 260, AIM_Y[4])
        touch_at(cdp, "touchStart", [(E["x"], E["y"])]); q.wait_for_timeout(60); touch_at(cdp, "touchEnd", []); q.wait_for_timeout(600)
        r0 = q.evaluate("() => { const r = document.querySelector('.recolor-redo'); return r ? [r.disabled, r.getAttribute('aria-label'), !!r.getClientRects().length] : null; }")
        ct = colours(q, route)
        q.click(".recolor-undo"); q.wait_for_timeout(400)
        r1 = q.evaluate("() => (document.querySelector('.recolor-redo') || {}).disabled")
        cu = colours(q, route)
        if q.evaluate("() => !!document.querySelector('.recolor-redo')"):
            q.click(".recolor-redo"); q.wait_for_timeout(400)
        r2 = q.evaluate("() => (document.querySelector('.recolor-redo') || {}).disabled")
        cr = colours(q, route)
        check(f"{route}: the bar has Redo beside Undo: off with nothing to put back, on after Undo, and it puts the colour back",
              r0 == [True, "Redo", True] and ct[gE] == GREEN and cu[gE] == INK and r1 is False and cr[gE] == GREEN and r2 is True,
              f"{r0}, tap {ct[gE]}, undo {cu[gE]} redo-off {r1}, redo {cr[gE]} then off {r2}")
        c.close()
        # NEAR THE TOP: a phone on its side, a line along the drawing's top edge.
        c = b.new_context(viewport={"width": 844, "height": 390}, device_scale_factor=2, is_mobile=True, has_touch=True)
        q = c.new_page(); browsing.goto(q, BASE, route)
        q.evaluate("() => { window.SkriblHints && SkriblHints.hide && SkriblHints.hide(); }")
        load(q, route, aiming_drawing())
        q.evaluate(f"() => {{ ({e['pen']})('{GREEN}'); {rc}.arm(); }}"); q.wait_for_timeout(300)
        T = screen_of(q, route, 260, 22)
        cdp = c.new_cdp_session(q)
        touch_at(cdp, "touchStart", [(T["x"], T["y"])]); q.wait_for_timeout(500)
        st = q.evaluate(AIM % rc)
        touch_at(cdp, "touchEnd", []); q.wait_for_timeout(300)
        lz = st["lens"]
        clear = bool(lz) and (lz["left"] >= T["x"] + 22 - 0.5 or lz["left"] + lz["width"] <= T["x"] - 22 + 0.5)
        check(f"{route}: near the top of the screen the lens stands beside the finger, whole on the screen",
              bool(lz) and T["y"] - 22 - 153 < 6 and clear and lz["top"] >= 0 and lz["top"] + lz["height"] <= 390
              and lz["left"] >= 0 and lz["left"] + lz["width"] <= 844, f"finger at {T}, lens {lz}")
        c.close()
        # A MOUSE lights the line it would catch, with no lens; a click takes it.
        c, q = fresh(b, route, ctx_opts=DESK)
        load(q, route, aiming_drawing())
        q.evaluate(f"() => {{ ({e['pen']})('{GREEN}'); {rc}.arm(); }}"); q.wait_for_timeout(300)
        A, C = screen_of(q, route, 260, AIM_Y[0]), screen_of(q, route, 260, AIM_Y[2])
        q.mouse.move(A["x"] - 40, A["y"] - 40); q.mouse.move(A["x"], A["y"], steps=5); q.wait_for_timeout(150)
        h1 = q.evaluate(AIM % rc)
        lit_px = q.evaluate("""([x, y]) => { const c = document.querySelector('.recolor-light'); if (!c || !c.isConnected) return null;
            const r = c.getBoundingClientRect(), k = c.width / r.width;
            return c.getContext('2d').getImageData(Math.round((x - r.left) * k), Math.round((y - r.top - 4) * k), 1, 1).data[3]; }""", [A["x"], A["y"]])
        q.mouse.move(C["x"], C["y"], steps=5); q.wait_for_timeout(150)
        h2 = q.evaluate(AIM % rc)
        say = q.evaluate("() => document.querySelector('.recolor-say').textContent")
        check(f"{route}: on a desk the line under the pointer lights up as it moves, with no lens",
              h1["lit"] == [gA, gA] and h2["lit"] == [gC, gC] and h2["lens"] is None and not h2["aiming"]
              and lit_px is not None and lit_px > 0 and say == "Tap a line to recolor", f"{h1}, {h2}, light alpha {lit_px}, says {say!r}")
        q.mouse.click(C["x"], C["y"]); q.wait_for_timeout(500)
        c6 = colours(q, route)
        q.mouse.move(2, 2, steps=3); q.wait_for_timeout(200)
        h3 = q.evaluate(AIM % rc)
        check(f"{route}: a click takes the lit line, and the light goes when the pointer leaves the drawing",
              c6[gC] == GREEN and c6[gA] == INK and h3["lit"] is None, f"{c6[gA:gC + 1]}, {h3}")
        c.close()

    # The bar's words and buttons stay inside it on the smallest phone, two
    # lines at most, the words 13px or more.
    for route in ED:
        e = ED[route]
        for w in (320, 402):
            c = b.new_context(viewport={"width": w, "height": 760}, device_scale_factor=2, is_mobile=True, has_touch=True)
            q = c.new_page(); browsing.goto(q, BASE, route)
            q.evaluate("() => { window.SkriblHints && SkriblHints.hide && SkriblHints.hide(); }")
            q.evaluate(f"() => {e['rc']}.arm()"); q.wait_for_timeout(400)
            m = q.evaluate("""() => { const bar = document.querySelector('.recolor-bar'), s = bar.querySelector('.recolor-say'), br = bar.getBoundingClientRect();
                const kids = [...bar.children].filter(k => k.getClientRects().length).map(k => k.getBoundingClientRect());
                const sr = s.getBoundingClientRect(), cs = getComputedStyle(s);
                return { inside: kids.every(k => k.left >= br.left - 0.5 && k.right <= br.right + 0.5 && k.top >= br.top - 0.5 && k.bottom <= br.bottom + 0.5),
                         lines: Math.round(sr.height / parseFloat(cs.lineHeight)), size: parseFloat(cs.fontSize) }; }""")
            check(f"{route}: [{w}] the bar's words and buttons, Redo with them, all inside it, two lines at most, 13px or more",
                  m["inside"] and m["lines"] <= 2 and m["size"] >= 13, json.dumps(m))
            c.close()

    print("\nTHE ENDS — a replay and the eraser key end the mode")
    for route in ED:
        e = ED[route]
        c, q = fresh(b, route)
        load(q, route, drawing())
        if route == "/flip":
            q.evaluate("() => { addFrame(true); go(0); }"); q.wait_for_timeout(200)
        q.evaluate(f"() => {e['rc']}.arm()"); q.wait_for_timeout(200)
        q.evaluate("() => (typeof play === 'function' && document.getElementById('play') ? play() : document.getElementById('playBtn').click())")
        q.wait_for_timeout(300)
        check(f"{route}: a replay ends the mode", not armed(q, route))
        q.evaluate("() => (typeof stop === 'function' && document.getElementById('play') ? stop() : (playing && document.getElementById('playBtn').click()))")
        q.wait_for_timeout(300)
        q.evaluate(f"() => {e['rc']}.arm()"); q.wait_for_timeout(200)
        q.locator("body").focus()
        q.keyboard.press("e"); q.wait_for_timeout(200)
        check(f"{route}: the eraser key ends it", not armed(q, route))
        c.close()
    b.close()

summarise_and_exit()
