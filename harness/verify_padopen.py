#!/usr/bin/env python3
"""A long drawing opens in the Pad without a freeze (the posting mock's 2b).

THE PROMISE, in the mock the owner answered "all yes": "Opening a long
drawing in Pad stops freezing too." Before it, opening the two-hour piece
held the page for its paint, and on a desk a second time a moment later: the
canvas grew to the screen and painted the whole drawing again.

WHAT IS ASKED, AND HOW IT IS READ
  * ONE PAINT: paintStrokesStatic is counted on the drawing (its calls with
    the drawing's own points) from the file's pick until well after the ink
    is whole: once, phone and desk, and on the desk the canvas is at the size
    its screen asks for (it grew before the paint, not after it).
  * IN SLICES, the CPU 4x slower, phone and desk: the ink is laid over many
    frames and shown as it goes (partway the canvas holds some of it, not
    all), and no task from the pick to the ink whole, the file's arrival and
    the autosave after it included, runs as long as a third of painting the
    drawing in one call on the same page. Measured against the one call, not
    a number of milliseconds: the box this runs on sets both.
  * THE SAME INK: what the slices leave is, pixel for pixel, what one call
    leaves, see-through ink (the stroke layers) included. The drawing's
    see-through strokes are few enough to be layered (lib/strokelayers.js
    BUDGET), and the row says so: one in five of them, the first draft's
    mix, put the whole paint over the budget, so no slice ever went through
    the layers and two breaks of them stayed green.
  * A PRESS OR A KEY FINISHES IT AT ONCE: a stroke drawn while the drawing
    is still being laid lands on the whole drawing (the canvas is then the
    drawing and the stroke, as one call paints them, as it is for the same
    stroke drawn once the ink is whole), and a key finds the canvas whole
    when its own handlers run.
  * A RELOAD (the autosave brings the long drawing back): laid in slices
    too, painted once, no task from the autosave's read to the ink whole as
    long as a third of the one call, and the same ink.
  * A SHORT DRAWING is the one call it always was, whole when it is opened.
  * THE PAD'S OWN PLAYER (#skribl=, player mode) paints a long drawing in
    whole calls, never in slices, as it did. (It paints it three times, on
    main as here: once on load and twice more as its canvas grows. That is
    the player's own, and this change leaves it as it was.) Two things keep
    it whole: its paint runs while app.js loads, before editor_draft.js and
    padPaint exist, and padPaint itself paints in one call in player mode.
    Either alone holds the row, so its break takes both away.
"""
import json
import math
import os
import sys
import tempfile

from assertions import make_check
import browsing

try:
    from playwright.sync_api import sync_playwright
except ImportError as exc:
    print(f"SUITE-SKIPPED: {exc}")
    print("No assertions were executed. This is NOT evidence the Pad opens a long drawing without a freeze.")
    raise SystemExit(77)

BASE = os.environ.get("SKRIBL_BASE", "http://127.0.0.1:5001")
results = []
check = make_check(results, with_detail=True)

PHONE = dict(viewport={"width": 402, "height": 874}, device_scale_factor=2, is_mobile=True, has_touch=True)
DESK = dict(viewport={"width": 1280, "height": 900}, device_scale_factor=1)
W, H = 816, 612
SLICE_FROM = 20000       # editor_draft.js PAD_SLICE_FROM
LONG_N = 60000

# For calibration: PADOPEN_PART=one,slices,press,reload,short runs only those parts.
PART = [p for p in (os.environ.get("PADOPEN_PART") or "").split(",") if p]


def part(name):
    return not PART or name in PART


def summarise_and_exit():
    bad = [r for r in results if not r[0]]
    print(f"\n{'=' * 62}\n{len(results) - len(bad)}/{len(results)} passed"
          + ("" if not bad else "  FAILURES: " + ", ".join(r[1] for r in bad)))
    sys.exit(1 if bad else 0)


def drawing(n, seed=11):
    """Strokes shaped like a pointer's (each tapering with pressure), from a
    fixed seed, one in 64 of them see-through ink: about 21 in the long
    drawing, under the stroke layers' budget of 24, so they are layered."""
    s = seed

    def rnd():
        nonlocal s
        s = (s * 16807) % 2147483647
        return s / 2147483647
    cols = ["#7c5cff", "#1d1a2b", "#1d1a2b", "#ff7a59"]
    pts, groups, t = [], [], 0.0
    while len(pts) < n:
        m = 15 + int(rnd() * 60)
        x, y = 60 + rnd() * 690, 50 + rnd() * 510
        ang, curv, step = rnd() * 6.283, (rnd() - 0.5) * 0.12, 3 + rnd() * 5
        w, col = [2, 3, 4, 6, 10][int(rnd() * 5)], cols[int(rnd() * 4)]
        if len(groups) % 64 == 5:
            col = "rgba(124, 92, 255, 0.45)"
        k = 0
        for i in range(m):
            if len(pts) >= n:
                break
            f = i / (m - 1)
            q = {"x": round(x, 2), "y": round(y, 2), "color": col,
                 "size": round(w * (0.35 + 0.65 * math.sin(math.pi * f)) + 0.3, 2), "t": round(t)}
            if i == 0:
                q["start"] = True
            pts.append(q)
            k += 1
            ang += curv
            x = min(810, max(5, x + math.cos(ang) * step))
            y = min(606, max(5, y + math.sin(ang) * step))
            t += 1000 / 55
        groups.append(k)
        t += 150 + rnd() * 650
    return pts, groups


def skribl_file(n, title):
    pts, groups = drawing(n)
    body = {"version": 1, "title": title, "strokes": pts, "strokeGroups": groups,
            "background": {"color": "#f6f2ea"}, "canvasSize": {"cssWidth": W, "cssHeight": H}}
    fd, path = tempfile.mkstemp(suffix=".skribl")
    with os.fdopen(fd, "w") as f:
        json.dump(body, f)
    return path, body


# From the page's first moment: long tasks, every frame, when the drawing is
# read from storage (a reload's autosave, inside editor_draft.js; the Pad's own
# player's post), and paintStrokesStatic counted on the drawing, with when its
# ink is whole. The count goes in at that read, so the paint right after it is
# seen, and by hand (window.__poWrap) before a file is picked.
WATCH = """(() => { const po = window.__po = { paints: [], modes: [], whole: null, sliced: null, lt: [], fr: [], read: null };
  try { new PerformanceObserver(l => { for (const e of l.getEntries()) po.lt.push([e.startTime, e.duration]); })
    .observe({ type: 'longtask', buffered: true }); } catch (e) {}
  window.__poWrap = () => { if (window.__ps || typeof window.paintStrokesStatic !== 'function') return;
    const f = window.__ps = window.paintStrokesStatic;
    window.paintStrokesStatic = function (arr, whole) {
      if (!arr || arr.length < %d) return f.apply(this, arguments);
      po.paints.push(performance.now()); po.modes.push(!!whole); po.sliced = !!whole;
      if (!whole) { const r = f.call(this, arr); po.whole = performance.now(); return r; }
      return f.call(this, arr, function () { po.whole = performance.now(); return whole.apply(this, arguments); });
    }; };
  const g = Storage.prototype.getItem;
  Storage.prototype.getItem = function (k) {
    if (k === 'skribl_autosave_v1' || /^skribl_post_/.test(k)) {
      window.__poWrap(); if (po.read == null && window.__ps) po.read = performance.now(); }
    return g.apply(this, arguments); };
  document.addEventListener('pointerdown', () => { if (po.downWhole == null) po.downWhole = po.whole != null; }, true);
  document.addEventListener('keydown', () => { if (po.keyWhole == null) po.keyWhole = po.whole != null; }, true);
  const tick = (now) => { po.fr.push(now); requestAnimationFrame(tick); };
  requestAnimationFrame(tick); })()""" % SLICE_FROM

# The canvas, every pixel folded into one number, and how many are inked.
INK = """() => { const cv = document.getElementById('canvas'), x = cv.getContext('2d');
  const d = x.getImageData(0, 0, cv.width, cv.height).data; let h = 2166136261, ink = 0;
  for (let i = 0; i < d.length; i += 4) { if (d[i + 3]) ink++; h = Math.imul(h ^ d[i] ^ (d[i + 1] << 8) ^ (d[i + 2] << 16) ^ (d[i + 3] << 24), 16777619); }
  return { hash: h >>> 0, ink }; }"""

# The canvas small: how many of its cells hold ink.
SOME = """() => { const cv = document.getElementById('canvas'), s = document.createElement('canvas');
  s.width = 64; s.height = 48; const x = s.getContext('2d'); x.drawImage(cv, 0, 0, 64, 48);
  const d = x.getImageData(0, 0, 64, 48).data; let n = 0; for (let i = 3; i < d.length; i += 4) if (d[i] > 8) n++;
  return { n, whole: window.__po.whole != null }; }"""

# The same drawing painted again at once, by the unwrapped function, on the
# same canvas: the pixels that differ from what was there, and the time it
# took (the one call, its flush included); and whether its see-through ink
# goes through the stroke layers (on, and under their budget), or the
# same-ink rows would not be asking about the layers at all.
AGAIN = """() => { const cv = document.getElementById('canvas'), x = cv.getContext('2d'), f = window.__ps || paintStrokesStatic;
  const sl = window.SkriblStrokeLayers, layered = strokeLayersOn() && !!sl && !sl.overBudget(strokes, parseStrokeAlpha, anyStrokeAlpha)
    && strokes.some(p => p.start && parseStrokeAlpha(p.color) < 1);
  const a = x.getImageData(0, 0, cv.width, cv.height).data;
  const t = performance.now(); clearAndRestore(() => f(strokes)); x.getImageData(0, 0, 1, 1); const ms = performance.now() - t;
  const b = x.getImageData(0, 0, cv.width, cv.height).data; let n = 0, ink = 0;
  for (let i = 0; i < a.length; i += 4) { if (b[i + 3]) ink++;
    if (a[i] !== b[i] || a[i + 1] !== b[i + 1] || a[i + 2] !== b[i + 2] || a[i + 3] !== b[i + 3]) n++; }
  return { differ: n, ink, ms, layered }; }"""


def waited(pg, cond, timeout):
    """True once cond holds; False, not a crash, so a break shows as the row
    it breaks."""
    try:
        pg.wait_for_function(cond, timeout=timeout, polling=50)
        return True
    except Exception:
        return False


def pad(b, view, rate=1, path="/"):
    c = b.new_context(**view)
    pg = c.new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.add_init_script(WATCH)
    browsing.goto(pg, BASE, path)
    pg.evaluate("() => window.SkriblHints && window.SkriblHints.hide && window.SkriblHints.hide()")
    if rate != 1:
        c.new_cdp_session(pg).send("Emulation.setCPUThrottlingRate", {"rate": rate})
    return c, pg, errs


def pick(pg, path):
    """The file opened through the Pad's own input; returns the moment."""
    pg.evaluate("() => { window.__poWrap(); const po = window.__po; po.paints = []; po.modes = []; po.whole = null; po.sliced = null;"
                " po.downWhole = null; po.keyWhole = null; po.t0 = performance.now(); }")
    pg.set_input_files("#draftInput", path)
    return waited(pg, "() => window.__po.paints.length > 0", 60000)


def tasks(po, start, end):
    return [d for t, d in po["lt"] if start <= t <= end]


def frames(po, start, end):
    return len([1 for t in po["fr"] if start <= t <= end])


with sync_playwright() as p:
    b = p.chromium.launch()
    LONG, _ = skribl_file(LONG_N, "Two hours")
    SHORT, _ = skribl_file(2000, "A doodle")
    try:
        if part("one"):
            print("\nONE PAINT, and the canvas at its size")
            for name, view in (("phone", PHONE), ("desk", DESK)):
                c, pg, errs = pad(b, view)
                picked = pick(pg, LONG)
                whole = waited(pg, "() => window.__po.whole != null", 60000 if picked else 1500)
                pg.wait_for_timeout(1500)
                po = pg.evaluate("() => window.__po")
                size = pg.evaluate("() => ({ growth: canvasGrowth, grown: grownTo(_growWant), w: canvas.width, want: _growWant })")
                if name == "desk":
                    check("desk: the long drawing is painted once on opening, the canvas grown to its screen first",
                          whole and len(po["paints"]) == 1 and size["grown"] and size["growth"] > 1,
                          f"{len(po['paints'])} paints; {size}")
                else:
                    check("phone: the long drawing is painted once on opening",
                          whole and len(po["paints"]) == 1 and size["grown"], f"{len(po['paints'])} paints; {size}")
                again = pg.evaluate(AGAIN)
                check(f"{name}: the ink laid in slices is, pixel for pixel, what one call lays (see-through ink and all)",
                      whole and again["ink"] > 10000 and again["layered"] and again["differ"] == 0, str(again))
                check(f"{name}: no page errors while it opens", not errs, "; ".join(errs[:2]))
                c.close()

        if part("slices"):
            print("\nIN SLICES, the CPU 4x slower")
            for name, view in (("phone", PHONE), ("desk", DESK)):
                c, pg, errs = pad(b, view, rate=4)
                picked = pick(pg, LONG)
                # Partway: the canvas holds some of the ink and not all.
                waited(pg, "() => window.__po.fr.filter(t => t > window.__po.paints[0]).length >= 15 || window.__po.whole != null",
                       120000 if picked else 1500)
                mid = pg.evaluate(SOME)
                whole = waited(pg, "() => window.__po.whole != null", 180000 if picked else 1500)
                pg.wait_for_timeout(2500)
                end = pg.evaluate(SOME)
                po = pg.evaluate("() => window.__po")
                again = pg.evaluate(AGAIN)
                first = po["paints"][0] if po["paints"] else 0
                n_fr = frames(po, first, po["whole"] or 0)
                tk = tasks(po, po.get("t0", 0), (po["whole"] or 0) + 2500)
                check(f"{name}: the long drawing's ink is laid over many frames, the page answering between them",
                      whole and po["sliced"] and n_fr >= 10, f"{n_fr} frames between the paint's start and the ink whole")
                check(f"{name}: ...shown as it goes: partway, the canvas holds some of the ink, not all",
                      not mid["whole"] and 0 < mid["n"] < end["n"] * 0.95, f"{mid} of {end['n']} inked cells")
                check(f"{name}: ...and no task from the file's pick to the ink whole (its autosave too) runs a third of the one call",
                      whole and max(tk or [0]) <= again["ms"] / 3,
                      f"one call {again['ms']:.0f} ms; the tasks {[round(x) for x in sorted(tk, reverse=True)[:8]]} ({len(tk)} over 50 ms)")
                check(f"{name}: no page errors", not errs, "; ".join(errs[:2]))
                c.close()

        if part("press"):
            print("\nA PRESS OR A KEY FINISHES IT AT ONCE")
            # The control: the same stroke drawn once the ink is whole.
            def stroke(pg):
                box = pg.locator("#canvas").bounding_box()
                x0, y0 = box["x"] + box["width"] * 0.3, box["y"] + box["height"] * 0.4
                pg.mouse.move(x0, y0)
                pg.mouse.down()
                for i in range(24):
                    pg.mouse.move(x0 + i * 9, y0 + math.sin(i / 3) * 18)
                pg.mouse.up()
                pg.wait_for_timeout(600)
            c, pg, errs = pad(b, DESK, rate=4)
            picked = pick(pg, LONG)
            waited(pg, "() => window.__po.whole != null", 180000 if picked else 1500)
            pg.wait_for_timeout(500)
            stroke(pg)
            control = pg.evaluate(AGAIN)
            c.close()
            c, pg, errs = pad(b, DESK, rate=4)
            picked = pick(pg, LONG)
            waited(pg, "() => window.__po.fr.filter(t => t > window.__po.paints[0]).length >= 15 || window.__po.whole != null",
                   120000 if picked else 1500)
            before = pg.evaluate("() => window.__po.whole != null")
            stroke(pg)
            po = pg.evaluate("() => window.__po")
            mid = pg.evaluate(AGAIN)
            check("a stroke drawn while the drawing is still being laid: when the press reaches the page, the ink is whole",
                  picked and not before and po["downWhole"] is True, f"whole before the press {before}; at the press {po['downWhole']}")
            check("...and the stroke lands on the whole drawing: the canvas is the drawing and the stroke, as one call paints them",
                  picked and not before and mid["differ"] <= control["differ"],
                  f"{mid['differ']} pixels differ from one call (the same stroke once the ink was whole: {control['differ']})")
            check("no page errors through the stroke", not errs, "; ".join(errs[:2]))
            c.close()
            c, pg, errs = pad(b, DESK, rate=4)
            picked = pick(pg, LONG)
            waited(pg, "() => window.__po.fr.filter(t => t > window.__po.paints[0]).length >= 15 || window.__po.whole != null",
                   120000 if picked else 1500)
            before = pg.evaluate("() => window.__po.whole != null")
            pg.keyboard.press("Shift")
            pg.wait_for_timeout(300)
            po = pg.evaluate("() => window.__po")
            check("a key pressed while it is being laid finds the canvas whole when its own handlers run",
                  picked and not before and po["keyWhole"] is True, f"whole before the key {before}; at the key {po['keyWhole']}")
            c.close()

        if part("reload"):
            print("\nA RELOAD brings the long drawing back")
            c, pg, errs = pad(b, DESK)
            picked = pick(pg, LONG)
            waited(pg, "() => window.__po.whole != null", 60000 if picked else 1500)
            saved = waited(pg, "() => (localStorage.getItem('skribl_autosave_v1') || '').length > 100000", 20000)
            c.new_cdp_session(pg).send("Emulation.setCPUThrottlingRate", {"rate": 4})
            pg.reload(wait_until="load")
            whole = waited(pg, "() => window.__po.read != null && window.__po.whole != null", 180000 if saved else 1500)
            pg.wait_for_timeout(2500)
            po = pg.evaluate("() => window.__po")
            again = pg.evaluate(AGAIN)
            n_fr = frames(po, po["paints"][0] if po["paints"] else 0, po["whole"] or 0)
            tk = tasks(po, po["read"] or 0, (po["whole"] or 0) + 2500)
            check("the drawing came back from the autosave (the case is real)", saved and whole and again["ink"] > 10000,
                  f"saved {saved}, read at {po['read']}, ink {again['ink']}")
            check("...laid in slices over many frames, and painted once",
                  whole and po["sliced"] and n_fr >= 10 and len(po["paints"]) == 1, f"{n_fr} frames; {len(po['paints'])} paints")
            check("...no task from the autosave's read to the ink whole runs a third of the one call",
                  whole and max(tk or [0]) <= again["ms"] / 3,
                  f"one call {again['ms']:.0f} ms; the tasks {[round(x) for x in sorted(tk, reverse=True)[:8]]}")
            check("...and its ink is what one call lays (see-through ink and all)",
                  whole and again["layered"] and again["differ"] == 0, str(again))
            check("no page errors through the reload", not errs, "; ".join(errs[:2]))
            c.close()

        if part("short"):
            print("\nA SHORT DRAWING, AND THE PAD'S OWN PLAYER")
            c, pg, errs = pad(b, DESK)
            pg.evaluate("() => { window.__poWrap(); const f = window.__ps; window.__calls = [];"
                        " window.paintStrokesStatic = function (arr, whole) { window.__calls.push([arr ? arr.length : 0, !!whole]); return f.apply(this, arguments); }; }")
            pg.set_input_files("#draftInput", SHORT)
            waited(pg, "() => window.__calls.some(c => c[0] === 2000)", 20000)
            pg.wait_for_timeout(800)
            calls = [x for x in pg.evaluate("() => window.__calls") if x[0] == 2000]
            check("a short drawing is the one call it always was: whole when it is opened",
                  calls == [[2000, False]], str(calls))
            c.close()
            pts, groups = drawing(25000)
            post = {"title": "Two hours", "skribl": {"version": 1, "strokes": pts, "strokeGroups": groups,
                    "background": {"color": "#f6f2ea"}, "canvasSize": {"cssWidth": W, "cssHeight": H}}}
            c, pg, errs = pad(b, DESK)
            pg.evaluate("(post) => localStorage.setItem('skribl_post_padopen', JSON.stringify(post))", post)
            pg.goto("about:blank")   # a new page, not a hash change on this one
            pg.goto(BASE + "/#skribl=padopen", wait_until="load")
            played = waited(pg, "() => document.body.classList.contains('player-mode') && window.__po.paints.length > 0", 20000)
            pg.wait_for_timeout(1000)
            po = pg.evaluate("() => window.__po")
            check("the Pad's own player (#skribl=) paints a long drawing whole, never in slices, as it did",
                  played and po["modes"] and not any(po["modes"]),
                  f"played {played}; {len(po['paints'])} paints, sliced {po['modes']}")
            c.close()
    finally:
        for f in (LONG, SHORT):
            try:
                os.unlink(f)
            except OSError:
                pass
    b.close()

summarise_and_exit()
