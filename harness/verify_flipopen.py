#!/usr/bin/env python3
"""A long Flip opens in Flip's editor without a freeze (FUTURE.md 6y).

THE PROMISE, from the Pad's half (verify_padopen.py), "Flip next". Opening a
long Flip (60 pages of 2,400 points) through Flip's own file input held the
page 1.2 s on a desk and 1.4 s on a phone at this box's pace, 5.5 and 8.5 s
with the CPU 4x slower, nearly all of it the page strip painting every page's
picture at once (paintTiles, flip.js).

WHAT IS ASKED, AND HOW IT IS READ
  * AT ONCE, read where the file has been taken in (the "Opened your file"
    chip, the last thing the task that reads it does): every tile is in its
    place, the page you are on has its picture, the tiles still to paint show
    their page's ground (never a blank tile), and only some are painted.
  * IN SLICES, the CPU 4x slower, phone and desk: the other pictures come
    over many frames, the nearest to the page you are on first, and no task
    from the file's pick to the strip whole runs half as long as painting
    the strip in one call on the same page. Measured against the one call,
    not a number of milliseconds: the box this runs on sets both. Half, not
    the Pad's third: the file's own task (reading it, the page you are on)
    is a larger share of a Flip's opening, 853 ms against a one call of
    3,126 on a desk at this box's pace with the CPU 4x slower.
  * THE SAME PICTURES: each tile ends with, pixel for pixel, the picture one
    call paints for its own page.
  * A TAP on a tile not yet painted makes it the page you are on, and its
    picture is there when the tap's own handlers are done.
  * A SHORT FLIP (under 20,000 points, the Pad's PAD_SLICE_FROM) is painted
    whole as it opens, as before.
  * THE DRAFT: the opened Flip is kept as the draft, written in a task of its
    own after the file's (it was a fifth of the opening).
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
    print("No assertions were executed. This is NOT evidence Flip opens a long Flip without a freeze.")
    raise SystemExit(77)

BASE = os.environ.get("SKRIBL_BASE", "http://127.0.0.1:5001")
results = []
check = make_check(results, with_detail=True)

PHONE = dict(viewport={"width": 402, "height": 874}, device_scale_factor=2, is_mobile=True, has_touch=True)
DESK = dict(viewport={"width": 1280, "height": 900}, device_scale_factor=1)
GROUND = (246, 242, 234)   # #f6f2ea, the fixture's ground

# For calibration: FLIPOPEN_PART=slices,tap,short,draft runs only those parts,
# and FLIPOPEN_VIEW=desk (or phone) the slices on that screen only.
PART = [p for p in (os.environ.get("FLIPOPEN_PART") or "").split(",") if p]
VIEW = os.environ.get("FLIPOPEN_VIEW") or ""


def part(name):
    return not PART or name in PART


def page(n, seed):
    """Strokes shaped like a pointer's, tapering with pressure, from a seed."""
    s = seed

    def rnd():
        nonlocal s
        s = (s * 16807) % 2147483647
        return s / 2147483647
    pts, groups, t = [], [], 0.0
    while len(pts) < n:
        m = 15 + int(rnd() * 60)
        x, y = 60 + rnd() * 690, 50 + rnd() * 510
        ang, curv, step = rnd() * 6.283, (rnd() - 0.5) * 0.12, 3 + rnd() * 5
        w, col = [2, 3, 4, 6, 10][int(rnd() * 5)], ["#7c5cff", "#1d1a2b", "#ff7a59"][int(rnd() * 3)]
        k = 0
        for i in range(m):
            if len(pts) >= n:
                break
            q = {"x": round(x, 2), "y": round(y, 2), "color": col,
                 "size": round(w * (0.35 + 0.65 * math.sin(math.pi * i / (m - 1))) + 0.3, 2), "t": round(t)}
            if i == 0:
                q["start"] = True
            pts.append(q)
            k += 1
            ang += curv
            x = min(810, max(5, x + math.cos(ang) * step))
            y = min(606, max(5, y + math.sin(ang) * step))
            t += 1000 / 55
        groups.append(k)
    return pts, groups


def flip_file(pages, per, title):
    frames = []
    for k in range(pages):
        pts, groups = page(per, 11 + k)
        frames.append({"strokes": pts, "strokeGroups": groups})
    doc = {"version": 2, "schemaVersion": 2, "playbackMode": "flip", "fps": 8, "title": title,
           "canvasSize": {"cssWidth": 816, "cssHeight": 612}, "background": {"color": "#f6f2ea"}, "frames": frames}
    fd, path = tempfile.mkstemp(suffix=".skribl")
    with os.fdopen(fd, "w") as f:
        json.dump(doc, f)
    return path


# Long tasks and frames from the first script on; the chip, the tiles'
# painter and its slices wrapped once flip.js has defined them. The snapshot
# at the chip is cheap on purpose (it runs inside the task it reads).
WATCH = """(() => { const fo = window.__fo = { lt: [], fr: [], order: [], slices: 0, whole: null, atOpen: null };
  try { new PerformanceObserver(l => { for (const e of l.getEntries()) fo.lt.push([e.startTime, e.duration]); })
    .observe({ type: 'longtask', buffered: true }); } catch (e) {}
  const tick = (t) => { fo.fr.push(t); requestAnimationFrame(tick); }; requestAnimationFrame(tick);
  window.__foWrap = () => {
    if (window.__foWrapped) return; window.__foWrapped = true;
    const c0 = window.chip; window.chip = function (msg) {
      if (/Opened your file/.test(String(msg))) fo.atOpen = window.__foSnap();
      return c0.apply(this, arguments); };
    const d0 = window.drawThumb; window.drawThumb = function (cv, f, keptOnly) {
      const r = d0.apply(this, arguments);
      if (r && !keptOnly) fo.order.push([performance.now(), frames.indexOf(f)]);
      return r; };
    const s0 = window.stripSlice; window.stripSlice = function () { fo.slices++;
      const r = s0.apply(this, arguments); if (_stripLater === null) fo.whole = performance.now(); return r; };
  };
  window.__foSnap = () => { const tiles = _tiles(); let ground = null;
    for (let i = tiles.length - 1; i >= 0; i--) if (!_thumbCache.has(frames[i])) {
      const cv = tiles[i].querySelector('canvas'); ground = [...cv.getContext('2d').getImageData(cv.width >> 1, 2, 1, 1).data]; break; }
    return { t: performance.now(), tiles: tiles.length, frames: frames.length, idx: idx,
             painted: frames.filter(f => _thumbCache.has(f)).length, here: _thumbCache.has(frames[idx]), ground: ground,
             slot: (localStorage.getItem(AUTOSAVE_KEY) || '').length }; };
})()"""
WHOLE = "() => window.__fo.atOpen && _stripLater === null && frames.every(f => _thumbCache.has(f))"
# The strip in one call, on the same page: every page's picture painted
# afresh into a canvas of its own, timed; then each tile's pixels against
# its own page's fresh picture.
ONE_CALL = """() => { const tiles = [..._tiles()], fresh = [];
  const t = performance.now();
  for (const f of frames) { const cv = document.createElement('canvas'); _thumbCache.delete(f); drawThumb(cv, f); fresh.push(cv); }
  const ms = performance.now() - t;
  const h = (cv) => { const d = cv.getContext('2d').getImageData(0, 0, cv.width, cv.height).data; let x = 2166136261 >>> 0;
    for (let i = 0; i < d.length; i++) x = Math.imul(x ^ d[i], 16777619) >>> 0; return x; };
  let same = 0, inked = 0;
  tiles.forEach((el, i) => { const a = h(el.querySelector('canvas')), b = h(fresh[i]); if (a === b) same++; });
  fresh.forEach((cv) => { const d = cv.getContext('2d').getImageData(0, 0, cv.width, cv.height).data;
    let n = 0; for (let i = 0; i < d.length; i += 16) if (d[i] < 200) n++; if (n > 20) inked++; });
  return { ms, same, inked, n: tiles.length }; }"""


def waited(pg, cond, timeout):
    try:
        pg.wait_for_function(cond, timeout=timeout, polling=50)
        return True
    except Exception:
        return False


def flip(b, view, rate=1):
    c = b.new_context(**view)
    pg = c.new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.add_init_script(WATCH)
    browsing.goto(pg, BASE, "/flip")
    pg.wait_for_timeout(800)
    pg.evaluate("() => { window.SkriblHints && window.SkriblHints.hide && window.SkriblHints.hide();"
                " window.__foWrap(); }")
    if rate != 1:
        c.new_cdp_session(pg).send("Emulation.setCPUThrottlingRate", {"rate": rate})
    return c, pg, errs


def pick(pg, path):
    t0 = pg.evaluate("() => performance.now()")
    pg.set_input_files("#draftInput", path)
    return t0, waited(pg, "() => window.__fo.atOpen != null", 120000)


with sync_playwright() as p:
    b = p.chromium.launch()
    LONG = flip_file(60, 2400, "Long Flip")
    SHORT = flip_file(10, 1000, "Short Flip")
    try:
        if part("slices"):
            print("\nA LONG FLIP, the CPU 4x slower")
            for name, view in (("phone", PHONE), ("desk", DESK)):
                if VIEW and VIEW != name:
                    continue
                c, pg, errs = flip(b, view, rate=4)
                t0, opened = pick(pg, LONG)
                whole = waited(pg, WHOLE, 240000 if opened else 1500)
                pg.wait_for_timeout(1000)
                fo = pg.evaluate("() => window.__fo")
                at = fo["atOpen"] or {}
                one = pg.evaluate(ONE_CALL)
                end = fo["whole"] or at.get("t", 0)
                tk = [d for t, d in fo["lt"] if t0 <= t <= end + 1000]
                later = [i for t, i in fo["order"] if t > at.get("t", 0) and i >= 0]
                d0 = at.get("idx", 0)
                near = all(abs(a - d0) <= abs(b2 - d0) for a, b2 in zip(later, later[1:]))
                n_fr = len([1 for t in fo["fr"] if at.get("t", 0) <= t <= end])
                check(f"{name}: as the file is taken in, every tile is in its place and the page you are on has its picture",
                      opened and at.get("tiles") == 60 and at.get("here") is True, str({k: at.get(k) for k in ("tiles", "idx", "here", "painted")}))
                check(f"{name}: ...the tiles still to paint show their page's ground, never a blank tile",
                      opened and at.get("ground") is not None and tuple(at["ground"][:3]) == GROUND and at["ground"][3] == 255,
                      f"a tile not yet painted reads {at.get('ground')}")
                check(f"{name}: ...and the other pictures come over many frames, the nearest to the page you are on first",
                      whole and at.get("painted", 60) < 60 and fo["slices"] >= 10 and n_fr >= 10 and near,
                      f"{at.get('painted')} painted at once; {fo['slices']} slices over {n_fr} frames; "
                      f"order {later[:8]}{'...' if len(later) > 8 else ''} nearest first {near}")
                check(f"{name}: no task from the file's pick to the strip whole runs half as long as the strip in one call",
                      whole and one["ms"] > 0 and max(tk or [0]) <= one["ms"] / 2,
                      f"one call {one['ms']:.0f} ms; the tasks {[round(x) for x in sorted(tk, reverse=True)[:6]]} ({len(tk)} over 50 ms)")
                check(f"{name}: each tile ends with, pixel for pixel, the picture one call paints for its page",
                      whole and one["same"] == 60 and one["inked"] == 60, str(one))
                check(f"{name}: no page errors while it opens", not errs, "; ".join(errs[:2]))
                c.close()

        if part("tap"):
            print("\nA TAP on a tile not yet painted")
            c, pg, errs = flip(b, DESK, rate=4)
            t0, opened = pick(pg, LONG)
            tap = pg.evaluate("""() => { const i = frames.length - 1, had = _thumbCache.has(frames[i]);
              _tiles()[i].click(); return { had, now: _thumbCache.has(frames[i]), idx, i }; }""") if opened else {}
            check("a tap on a tile not yet painted makes it the page you are on, its picture there when the tap is done",
                  opened and tap.get("had") is False and tap.get("idx") == tap.get("i") and tap.get("now") is True, str(tap))
            check("no page errors through the tap", not errs, "; ".join(errs[:2]))
            c.close()

        if part("short"):
            print("\nA SHORT FLIP")
            c, pg, errs = flip(b, DESK)
            t0, opened = pick(pg, SHORT)
            pg.wait_for_timeout(800)
            fo = pg.evaluate("() => window.__fo")
            at = fo["atOpen"] or {}
            check("a short Flip's strip is painted whole as it opens, in no slices, as before",
                  opened and at.get("tiles") == 10 and at.get("painted") == 10 and fo["slices"] == 0,
                  f"{at.get('painted')} of {at.get('tiles')} painted at once; {fo['slices']} slices")
            check("no page errors", not errs, "; ".join(errs[:2]))
            c.close()

        if part("draft"):
            print("\nTHE DRAFT")
            c, pg, errs = flip(b, DESK)
            t0, opened = pick(pg, LONG)
            pg.wait_for_timeout(1500)
            fo = pg.evaluate("() => window.__fo")
            kept = pg.evaluate("() => { try { return JSON.parse(localStorage.getItem(AUTOSAVE_KEY)).frames.length; } catch (e) { return -1; } }")
            at = fo["atOpen"] or {}
            check("the opened Flip is kept as the draft, every page of it",
                  opened and kept == 60, f"the draft holds {kept} pages")
            check("...written in a task of its own, after the file's",
                  opened and at.get("slot", 0) < 100000, f"the draft was {at.get('slot')} characters as the file's task ended")
            check("no page errors", not errs, "; ".join(errs[:2]))
            c.close()
    finally:
        b.close()
        for f in (LONG, SHORT):
            try:
                os.unlink(f)
            except OSError:
                pass

bad = [r for r in results if not r[0]]
print(f"\n{'=' * 62}\n{len(results) - len(bad)}/{len(results)} passed"
      + ("" if not bad else "  FAILURES: " + ", ".join(r[1] for r in bad)))
sys.exit(1 if bad else 0)
