"""Frame bitmaps: a static page is rasterised at most once per playback.

WHY THIS EXISTS. A generated in-between is thousands of stroke points and both
playback surfaces repainted every one of them on every visit. Measured at 4x
CPU throttle (roughly a mid-range phone) on the owner's real 46-page file: one
11,826-point in-between costs ~215ms against a 41.7ms slot at 24fps, and a
1.92s loop took 6.2s of wall clock. The v260/v261 exposure thinning reduced
that to ~123ms per page — better, and still three times the slot. No point
budget can make re-rasterising the same static picture every loop fit a phone;
the picture does not change, so painting it more than once per playback is the
bug. With the bitmap cache the same file's cached loops measured 1911ms and
1916ms against a 1917ms nominal.

WHAT IS PINNED HERE, and why each assertion looks the way it does:

  * The blit shows THE SAME PIXELS as the paint it replaced, asserted as exact
    data-URL equality — but only after asserting the canvas is displayed 1:1,
    because at any other scale the capture is legitimately resampled and exact
    equality would be a lie about what the design promises.
  * A vacuity guard sits between the two halves of the identity check: the
    bitmap must actually EXIST before the second paint, otherwise "the second
    paint matches the first" is true of a build with no cache at all.
  * The scheduler must not use a rasterisation cost to time a blit. This is
    asserted on the recorded number (a blit REPLACES the frame's book entry),
    because the failure it guards is invisible on an unthrottled desktop: the
    stale estimate makes cached loops RUSH, and wall-clock is the wrong
    assertion on shared CI hardware.
  * Memory rules are asserted from the side that can lose: the light page must
    NOT be cached, the store must refuse past its byte ceiling, and a failed
    capture must CLOSE the store rather than retry every frame.
"""
import os
import pathlib
import sys

BASE = os.environ.get("SKRIBL_BASE", "http://127.0.0.1:5001")
ROOT = pathlib.Path(__file__).resolve().parents[1]
TPL = ROOT / "skribl" / "templates" / "skribl"

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("SKIP: playwright is not installed")
    sys.exit(0)

results = []


def check(name, ok, detail=""):
    results.append((bool(ok), name))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  — {detail}" if detail else ""))


print("\nTEMPLATES — both playback surfaces load the shared rule")
# The recurring failure shape of this codebase is a fix that lands on one
# surface: the editor got fast and every shared link stayed slow, or the other
# way round. The lib file existing proves nothing about who loads it.
for tpl in ("skribl_flip.html", "skribl_player.html"):
    src = (TPL / tpl).read_text(encoding="utf-8")
    check(f"{tpl} loads lib/framebitmap.js",
          "lib/framebitmap.js" in src,
          "the surface that misses this one keeps the phone stall")

# A heavy page: above MIN_POINTS so it earns a bitmap. 1,600 points in 8 runs.
HEAVY = """(() => {
  const s = [], g = [];
  for (let r = 0; r < 8; r++) {
    for (let k = 0; k < 200; k++)
      s.push({x: 20 + k * 1.7, y: 30 + r * 30 + Math.sin(k / 9) * 8,
              color: '#26b0ff', size: 4, t: k, erase: false, start: k === 0});
    g.push(200);
  }
  return {strokes: s, strokeGroups: g};
})()"""
# A light page: far below MIN_POINTS, must repaint every visit and must NOT
# spend cache bytes.
LIGHT = """(() => {
  const s = [];
  for (let k = 0; k < 40; k++)
    s.push({x: 30 + k * 8, y: 60, color: '#e5484d', size: 5, t: k,
            erase: false, start: k === 0});
  return {strokes: s, strokeGroups: [40]};
})()"""

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1000, "height": 800})
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(BASE + "/flip", wait_until="load")
    pg.wait_for_function(
        "typeof frames !== 'undefined' && typeof playPaint === 'function'"
        " && !!window.SkriblFrameBitmap")

    print("\nTHE RULES — thresholds and ceilings, from the side that can lose")
    rules = pg.evaluate("""() => {
        const FB = window.SkriblFrameBitmap;
        const out = {};
        // Never upscaled: a 400-wide backing displayed at 800 captures at 400.
        out.noUpscale = FB.captureSize(400, 300, 800, 600);
        // Display-bounded: a 1600-wide backing shown in a 400 column captures
        // at 400 — this is the rule that keeps a phone's cache small.
        out.displayCap = FB.captureSize(1600, 1200, 400, 300);
        // Aspect survives the rounding.
        out.aspect = FB.captureSize(816, 612, 360, 270);
        const s = FB.store();
        out.refusesLight = !FB.wants(s, FB.MIN_POINTS - 1, 100, 100);
        out.acceptsHeavy = FB.wants(s, FB.MIN_POINTS, 100, 100);
        s.bytes = FB.MAX_BYTES - 100 * 100 * 4 + 1;
        out.refusesPastCap = !FB.wants(s, FB.MIN_POINTS, 100, 100);
        s.bytes = FB.MAX_BYTES - 100 * 100 * 4;
        out.acceptsAtCap = FB.wants(s, FB.MIN_POINTS, 100, 100);
        // A failed capture closes the store: null is not a canvas, drawImage
        // throws, and a store that kept retrying under memory pressure would
        // be making the pressure.
        const s2 = FB.store();
        out.failReturnsNull = FB.capture(s2, 'k', null, 64, 64) === null;
        out.failCloses = s2.closed === true;
        out.closedRefuses = !FB.wants(s2, FB.MIN_POINTS * 10, 8, 8);
        return out; }""")
    check("a capture is never upscaled past the backing store",
          rules["noUpscale"] == {"w": 400, "h": 300}, str(rules["noUpscale"]))
    check("a capture is bounded by the displayed size",
          rules["displayCap"] == {"w": 400, "h": 300},
          f"{rules['displayCap']} — this rule is what keeps a 46-page phone cache "
          f"tens of MB instead of hundreds")
    check("the capture keeps the frame's aspect",
          abs(rules["aspect"]["h"] / rules["aspect"]["w"] - 612 / 816) < 0.01,
          str(rules["aspect"]))
    check("a page under MIN_POINTS is refused", rules["refusesLight"])
    check("a page at MIN_POINTS is accepted", rules["acceptsHeavy"])
    check("a capture that would cross MAX_BYTES is refused",
          rules["refusesPastCap"] and rules["acceptsAtCap"],
          "past it, frames paint direct — slower, never broken")
    check("a failed capture returns null and CLOSES the store",
          rules["failReturnsNull"] and rules["failCloses"] and rules["closedRefuses"],
          "a store that retried every frame under memory pressure would be "
          "making the pressure")

    print("\nIDENTITY — the blit is the paint, pixel for pixel")
    # 400x300 in a 1000px viewport displays at 1:1, so the capture IS the
    # backing store and exact equality is the honest claim. Assert the scale
    # first: at any other scale this whole block would be measuring resampling.
    ident = pg.evaluate(f"""() => {{
        applyCanvasSize(400, 300, {{silent: true}});
        sizeStage();
        frames.length = 0;
        frames.push({HEAVY}, {LIGHT});
        idx = 0; buildStrip(); render();
        const rect = pad.getBoundingClientRect();
        const FB = window.SkriblFrameBitmap;
        playBitmaps = FB.store();
        idx = 0;
        playPaint();                       // paints, and should capture
        const held = !!FB.get(playBitmaps, frames[0]);
        const direct = pad.toDataURL();
        playPaint();                       // must blit the capture
        const blit = pad.toDataURL();
        idx = 1;
        playPaint();                       // light page: paints, must NOT capture
        const lightHeld = !!FB.get(playBitmaps, frames[1]);
        const bytes = playBitmaps.bytes;
        playBitmaps = null;
        return {{scale1: Math.abs(rect.width - 400) < 0.5, held: held,
                 same: direct === blit, lightHeld: lightHeld, bytes: bytes}}; }}""")
    check("the fixture displays at 1:1 (the identity claim is only honest there)",
          ident["scale1"])
    check("the first paint of a heavy page fills the cache",
          ident["held"],
          "without this the equality below is vacuously true of a build with "
          "no cache at all")
    check("the blit shows exactly the pixels the paint showed",
          ident["same"], "compared as full data URLs")
    check("a light page is painted but never cached",
          not ident["lightHeld"] and ident["bytes"] == 400 * 300 * 4,
          f"store holds {ident['bytes']} bytes — one heavy capture, nothing else")

    print("\nPLAYBACK — the second loop stops rasterising")
    loop = pg.evaluate(f"""() => new Promise(res => {{
        frames.length = 0;
        frames.push({LIGHT}, {HEAVY}, {LIGHT.replace("'#e5484d'", "'#2f9e44'")});
        idx = 0; fps = 24; buildStrip(); render();
        const paints = [];                 // strokes.length of every real paint
        const _pf = paintFrame;
        window.paintFrame = function(c, strokes) {{ paints.push(strokes.length); return _pf(c, strokes); }};
        const rec = [];
        const _step = playStep;
        window.playStep = function() {{
            const t0 = performance.now(); _step();
            rec.push(performance.now() - t0);
            if (rec.length === frames.length * 3 + 1) {{
                const heavyCost1 = rec[1];              // heavy page, first paint
                const heavyBook = framePaintMs[1];       // after two blits
                const alive = !!playBitmaps;
                // Restore BEFORE stop(): stop() itself repaints the editor view
                // through buildStrip()/render(), and counting those would blame
                // playback for paints the editor legitimately owes.
                window.playStep = _step; window.paintFrame = _pf;
                stop();
                res({{paints: paints.slice(), heavyCost1: heavyCost1,
                     heavyBook: heavyBook, aliveDuring: alive,
                     droppedAfter: playBitmaps === null}});
            }}
        }};
        play();
    }})""")
    heavy_paints = [n for n in loop["paints"] if n >= 1500]
    light_paints = [n for n in loop["paints"] if n < 1500]
    check("the heavy page is rasterised exactly once across three loops",
          len(heavy_paints) == 1,
          f"{len(heavy_paints)} rasterisations — every one after the first is "
          f"the phone stall")
    check("the light pages repaint every loop (the once-only claim is not vacuous)",
          len(light_paints) >= 6,
          f"{len(light_paints)} light paints — playback really looped, and "
          f"MIN_POINTS really spared them the cache")
    check("a blit replaces the frame's cost book entry instead of blending in",
          loop["heavyBook"] is not None and loop["heavyBook"] < loop["heavyCost1"] * 0.5,
          f"book says {loop['heavyBook']:.2f}ms vs {loop['heavyCost1']:.2f}ms first "
          f"paint — a 60/40 blend of the two makes every cached loop rush, "
          f"measured at 1.5s for a 1.92s loop")
    check("the store lives during playback and is dropped by stop()",
          loop["aliveDuring"] and loop["droppedAfter"],
          "playback-scoped: the memory is freed the moment it stops earning")

    print("\nINVALIDATION — a resize orphans the captures")
    inv = pg.evaluate("""() => {
        playBitmaps = window.SkriblFrameBitmap.store();
        applyCanvasSize(640, 480, {silent: true});
        const dropped = playBitmaps === null;
        applyCanvasSize(400, 300, {silent: true});
        return dropped; }""")
    check("applyCanvasSize drops the play store",
          inv, "a capture is a CW x CH composite; blitting it after a resize "
               "paints the wrong picture at the wrong size")

    print("\nPLAYER — the surface a shared link actually plays on")
    # Posted through the API so the check is deterministic (verify_hold's
    # pattern). Three frames, the middle one heavy, loop enabled, and the
    # paint counter installed BEFORE pressing play.
    post = pg.request.post(BASE + "/api/skribls", data={
        "title": "framecache harness", "playbackMode": "flip", "fps": 24,
        "canvasSize": {"cssWidth": 400, "cssHeight": 300, "dpr": 1},
        "frames": pg.evaluate(f"""() => {{
            const heavy = {HEAVY}, light = {LIGHT};
            return [light, heavy, light]; }}""")})
    pid = post.json().get("id")
    check("the fixture posts", bool(pid), str(pid))
    if pid:
        pl = b.new_page(viewport={"width": 1000, "height": 800})
        perrs = []
        pl.on("pageerror", lambda e: perrs.append(str(e)))
        pl.goto(f"{BASE}/s/{pid}", wait_until="load")
        pl.wait_for_function("!!window.SkriblFrameBitmap"
                             " && typeof paintStrokesStatic === 'function'")
        pcounts = pl.evaluate("""() => new Promise(res => {
            const paints = [];
            const _ps = paintStrokesStatic;
            window.paintStrokesStatic = function(arr) { paints.push(arr.length); return _ps(arr); };
            document.getElementById('playerLoopBtn').click();
            document.getElementById('playerPlayBtn').click();
            // 3 frames at 24fps loop in 125ms; a second covers ~8 cycles.
            setTimeout(() => {
                window.paintStrokesStatic = _ps;
                res(paints.slice()); }, 1000);
        })""")
        heavy_pl = [n for n in pcounts if n >= 1500]
        light_pl = [n for n in pcounts if 0 < n < 1500]
        check("player: the heavy frame is rasterised exactly once across the loops",
              len(heavy_pl) == 1,
              f"{len(heavy_pl)} rasterisations over {len(pcounts)} paints — a "
              f"viewer's phone replays every loop, and v259's memo only "
              f"stopped repaints of the frame already on screen")
        check("player: light frames repaint every cycle (looping really happened)",
              len(light_pl) >= 4, f"{len(light_pl)} light paints")
        check("player: no page errors", not perrs, "; ".join(perrs[:2]))
        pl.close()

    check("no Flip page errors across the whole feature", not errs, "; ".join(errs[:2]))
    b.close()

bad = [r for r in results if not r[0]]
print(f"\n{'='*62}\n{len(results)-len(bad)}/{len(results)} passed" +
      ("" if not bad else "  FAILURES: " + ", ".join(r[1] for r in bad)))
sys.exit(1 if bad else 0)
