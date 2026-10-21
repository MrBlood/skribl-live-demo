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
        check(f"{route}: the bar says what to do and Recolor is pressed",
              m["say"] == "Tap a line to recolor" and m["pressed"] == "true", json.dumps(m))
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

    # ================================================================== the ends
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
