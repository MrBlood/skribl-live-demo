"""Frame bitmaps: a static page is rasterised at most once per playback.

WHY THIS EXISTS. A generated in-between is thousands of stroke points and both
playback surfaces repainted every one of them on every visit. Measured at 4x
CPU throttle (roughly a mid-range phone) on a real 46-page file: one
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
  * NOTHING HERE ENDS ON A CLOCK. Both playback sections run until the work
    they are measuring has demonstrably happened -- the Flip one counts its
    own steps, the player one counts the light repaints that three loops must
    produce -- because a fixed window measures the runner and calls it the
    cache. The player section learned this the expensive way in v305; the
    comment above it has the incident.
"""
import os
import pathlib
import sys
from assertions import make_check

BASE = os.environ.get("SKRIBL_BASE", "http://127.0.0.1:5001")
ROOT = pathlib.Path(__file__).resolve().parents[1]
TPL = ROOT / "skribl" / "templates" / "skribl"

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("SKIP: playwright is not installed")
    sys.exit(0)

results = []


check = make_check(results)


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
        let bookAtFirstBlit = null;
        const _step = playStep;
        window.playStep = function() {{
            const t0 = performance.now(); _step();
            rec.push(performance.now() - t0);
            // The heavy page's FIRST blit is the only moment where replacing
            // and blending are provably far apart: a 60/40 blend still carries
            // >=60% of the rasterisation cost here, while by the second blit
            // the EMA has decayed enough to sneak under any workable bound —
            // which is exactly how a mutation of this rule survived once.
            if (rec.length === frames.length + 2) bookAtFirstBlit = framePaintMs[1];
            if (rec.length === frames.length * 3 + 1) {{
                const heavyCost1 = rec[1];              // heavy page, first paint
                const heavyBook = bookAtFirstBlit;
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
          f"book says {loop['heavyBook']:.2f}ms right after the first blit vs "
          f"{loop['heavyCost1']:.2f}ms first paint — a 60/40 blend keeps >=60% "
          f"of the stale cost at that moment, and the stale cost is what makes "
          f"every cached loop rush (measured: 1.5s for a 1.92s loop)")
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
        # COUNTED, NOT TIMED — and this is the second time this file has had to
        # learn it. The Flip section above ends on its own step counter; this
        # one used to run the player for a flat 1000ms and then assert that at
        # least 4 light paints had landed in it. That is a wall-clock
        # assertion, which THIS SUITE'S OWN DOCSTRING calls the wrong one to
        # make on shared CI hardware, and it behaved exactly as the docstring
        # predicts: on 2026-09-21 it went red on one runner (21/23, both player
        # assertions together) while a second runner passed the same commit in
        # the same minutes. Nothing was wrong with the tree, and no amount of
        # raising the number would have fixed it -- a threshold on elapsed time
        # reports the runner, not the cache.
        #
        # So the observation ends when the WORK is done instead. The paint
        # pattern is fully determined: neither light page is ever cached (both
        # sit below MIN_POINTS), so each one repaints on every cycle, while the
        # heavy page rasterises once and is blitted from then on. Three loops
        # is therefore exactly 6 light paints, whenever they happen to arrive.
        # Waiting for the 6th is waiting for three real loops.
        #
        # The deadline that remains is a BACKSTOP, not a threshold, and
        # reaching it is reported as its own failure ("playback did not
        # progress") rather than being allowed to surface as an undercount
        # that reads like a cache bug.
        #
        # Both instruments were measured on one page under CDP CPU throttling,
        # which is what finally reproduced the CI failure -- eight spinners on
        # four cores did not, and that wrong guess is why this is written down:
        #
        #     throttle   v306 (1s window)    v306 (count to 6)   now
        #        1x      PASS  light=16      PASS    354ms       PASS   344ms
        #       20x      PASS  light=8       PASS    893ms       PASS
        #       50x      FAIL  light=1       PASS   2204ms       PASS
        #      100x      FAIL  light=1 h=0   PASS   6547ms       PASS  6265ms
        #      200x      FAIL  light=1       FAIL   deadline     PASS 16980ms
        #
        # The 100x row is the first CI failure exactly: heavy 0 and light 1, so
        # BOTH player assertions went red together. THE 200x ROW IS THE SECOND
        # ONE, and it was predicted in this comment before it happened -- "at
        # that starvation three loops genuinely do not fit 15s". The postgres
        # CI job is that starved: it runs the whole battery beside a PostgreSQL
        # service container, and it went red on the SEALED v306 tree while the
        # sqlite job and two local batteries on the same tree passed.
        #
        # Writing down that a threshold will fail, and leaving the threshold,
        # is not a mitigation. The window is 30s now, but the window is no
        # longer what decides the verdict -- see below.
        # AND THEN THE BACKSTOP FIRED ON A RUNNER, WHICH IS THE ROW ABOVE.
        # The 200x line predicted it in writing -- "at that starvation three
        # loops genuinely do not fit 15s" -- and the postgres CI job is that
        # starved: it runs the whole battery beside a PostgreSQL service
        # container, and it went red on the sealed v306 tree while the sqlite
        # job and two local batteries on the same tree passed.
        #
        # THE REAL MISTAKE WAS MAKING THE VERDICT DEPEND ON HOW MANY LOOPS FIT,
        # not the size of the number. "The heavy frame is rasterised exactly
        # once" is true of two loops and of thirty; the loop count is only
        # there to stop the claim being vacuous. So the run now collects for as
        # long as it needs, stops early once it has plenty, and asserts on
        # WHAT IT GOT: at least MIN_LIGHT light paints for evidence, and
        # exactly one rasterisation however many loops that turned out to be.
        # A slow runner now produces a smaller but still valid observation
        # instead of a failure, and only a player that cannot manage two loops
        # in 30s fails -- which is a playback failure and says so.
        #
        # CALIBRATED ON BOTH ARMS, by driving the paths rather than trusting
        # them. Asking for 999 light paints so the DEADLINE ends the run
        # collected 24 loops in 3s and both rows still passed on what was
        # there: the verdict does not depend on how the observation ended.
        # Cutting the window to 1.2s under 200x throttle collected 1 light
        # paint, and both rows went red naming a playback failure rather than
        # a cache bug -- including the "exactly once" row, which is gated on
        # having enough evidence so that a vacuous one cannot read as a pass.
        #
        # The reduced-loop path could NOT be reached by throttling alone: past
        # about 500x an earlier wait_for_function in this suite times out
        # first, so the MIN_LOOPS floor is a margin rather than a road this
        # runs down. Said plainly because an unexercised branch is worth
        # nothing, and this one was exercised the other way.
        #
        # AND THEN IT WENT RED A THIRD TIME, ON THE SAME LANE, AND THE CLOCK
        # WAS NOT WHAT DID IT. v311's postgres job reported 21/23 with both
        # player rows red again, while the sqlite job, a full local battery and
        # the sealed release run on the identical tree all reported 23/23.
        # Everything above would have you raise a number again. The cause is a
        # RACE, and it was in this file from the day the section was written:
        #
        #   the probe above waits for `window.SkriblFrameBitmap` and
        #   `paintStrokesStatic`, and BOTH exist the moment app.js is parsed --
        #   while the transport is bound at the END of `initPlayer()`, which is
        #   an async IIFE that first does `await fetch('/api/skribls/<id>')`.
        #
        # So the probe can pass while #playerLoopBtn and #playerPlayBtn are
        # still inert, and a `.click()` on an inert button is not an error: it
        # dispatches, nothing listens, playback never starts, and the run ends
        # on the deadline with one stray light paint and no rasterisation.
        # THAT IS THE EXACT CI SIGNATURE -- "heavy 0 and light 1, so BOTH
        # player assertions went red together" -- which the table above filed
        # under starvation because a slow machine and a lost click look the
        # same from the far end of a paint counter.
        #
        # PROVED BY MAKING THE LANE, NOT BY WAITING FOR IT. `GET
        # /api/skribls/<id>` was given a 2.5s sleep -- one temporary line in
        # skribl/routes.py, reverted after -- which is what a runner mid-
        # checkpoint serves, and the whole suite was run on both sides of it:
        #
        #   suite     GET /api/skribls/<id>    result
        #   before    12ms (normal)            23/23
        #   before    +2500ms                  21/23  light=1 heavy=0 deadline
        #   after     +2500ms                  23/23  armed after 27 clicks
        #   after     12ms (normal)            23/23  armed after 2 clicks
        #
        # The red row is the CI failure verbatim, down to "no page errors"
        # passing beside it. And the fix is not an anaesthetic -- both arms of
        # the verdict were driven on the FIXED suite, per component:
        #
        #   player never reads the cache (hit = null)   22/23  3 rasterisations
        #     ...and "playback really looped" stays GREEN, because the cache
        #        is what broke, not the playback
        #   Play bound but inert (handler does nothing) 21/23  NEVER ARMED
        #     ...which is the branch below saying so in words, exercised
        #        rather than merely written down
        #
        # Also measured, and left alone deliberately: the same probe-then-click
        # shape is in verify_hold, verify_player_isolation, verify_audiostate
        # and verify_audiosession, which reach the transport through
        # Playwright's click() -- it waits for a button to be VISIBLE and never
        # for a listener. None of them is red, so none of them is fixed here.
        # Written down so the next red on one of them is read in a minute
        # instead of a session.
        #
        # The window is a few milliseconds locally, which is why this survived
        # at all: Playwright's own round trip usually outruns a local fetch.
        # The postgres job is where it does not -- that lane runs the whole
        # battery beside a service container whose checkpoints wrote for 106s,
        # 112s and 74s during the v311 run, and the one request this page
        # cannot start without is a READ OF THAT DATABASE.
        #
        # THE FIX IS TO ASK THE MECHANISM, NOT THE CLOCK. The run now arms the
        # transport instead of assuming it: it clicks, reads back the state the
        # handler itself sets (`aria-pressed` on Loop, `aria-label` on Play --
        # nothing else in the tree writes either), and clicks again until the
        # player says it is looping and playing. A button that is not bound yet
        # simply gets asked again 100ms later. Loop is still pressed before
        # Play, because the arming step only reaches Play once Loop reads true.
        #
        # `arms` is carried out with the result and named in both details, so
        # the next failure on this lane says which of the two it is: a run that
        # never armed is a player that would not start, and a run that armed
        # and still came up short is the starvation the table above describes.
        # The deadline stays a backstop at 30s and stays out of the verdict.
        LOOPS = 3
        WANT_LIGHT = LOOPS * 2
        MIN_LOOPS = 2
        MIN_LIGHT = MIN_LOOPS * 2
        pstate = pl.evaluate("""(want) => new Promise(res => {
            const paints = [];
            const _ps = paintStrokesStatic;
            const t0 = performance.now();
            let arms = 0;
            const done = (reason) => {
                window.paintStrokesStatic = _ps;
                res({paints: paints.slice(), reason: reason, arms: arms,
                     armed: lp.getAttribute('aria-pressed') === 'true'
                            && pp.getAttribute('aria-label') === 'Pause',
                     ms: Math.round(performance.now() - t0)});
            };
            window.paintStrokesStatic = function(arr) {
                paints.push(arr.length);
                const light = paints.filter(n => n > 0 && n < 1500).length;
                if (light >= want) setTimeout(() => done('looped'), 0);
                return _ps(arr);
            };
            const lp = document.getElementById('playerLoopBtn');
            const pp = document.getElementById('playerPlayBtn');
            /* Read back what the handler writes, not what the markup ships:
               the template already carries aria-pressed="false" and
               aria-label="Play", so only a CHANGE proves a listener ran. */
            const beat = () => {
                const looped = lp.getAttribute('aria-pressed') === 'true';
                const going = pp.getAttribute('aria-label') === 'Pause';
                if (looped && going) return;
                arms++;
                if (!looped) lp.click(); else pp.click();
                setTimeout(beat, 100);
            };
            beat();
            setTimeout(() => done('deadline'), 30000);
        })""", WANT_LIGHT)
        pcounts = pstate["paints"]
        heavy_pl = [n for n in pcounts if n >= 1500]
        light_pl = [n for n in pcounts if 0 < n < 1500]
        _loops_seen = len(light_pl) // 2
        _armed = ("the transport armed after %d click(s)" % pstate["arms"]
                  if pstate["armed"] else
                  "THE TRANSPORT NEVER ARMED after %d click(s) — the player "
                  "never reported itself looping and playing, so this is a "
                  "player that would not start, not a cache result"
                  % pstate["arms"])
        check("player: playback really looped (the once-only claim is not vacuous)",
              len(light_pl) >= MIN_LIGHT,
              f"{len(light_pl)} light paints — about {_loops_seen} loop(s) — in "
              f"{pstate['ms']}ms, ended by {pstate['reason']}; {_armed}. Fewer "
              f"than {MIN_LOOPS} loops is a playback failure, NOT evidence "
              f"about the cache: the assertion below would be vacuous on a "
              f"player that never replayed anything")
        check("player: the heavy frame is rasterised exactly once, however many "
              "loops ran",
              len(light_pl) >= MIN_LIGHT and len(heavy_pl) == 1,
              f"{len(heavy_pl)} rasterisations over {len(pcounts)} paints in "
              f"about {_loops_seen} loop(s); {_armed} — a viewer's phone "
              f"replays every loop, and v259's memo only stopped repaints of "
              f"the frame already on screen. The count is read from the run "
              f"rather than assumed, so a slow machine shortens the evidence "
              f"instead of inventing a cache bug")
        check("player: no page errors", not perrs, "; ".join(perrs[:2]))
        pl.close()

    check("no Flip page errors across the whole feature", not errs, "; ".join(errs[:2]))
    b.close()

bad = [r for r in results if not r[0]]
print(f"\n{'='*62}\n{len(results)-len(bad)}/{len(results)} passed" +
      ("" if not bad else "  FAILURES: " + ", ".join(r[1] for r in bad)))
sys.exit(1 if bad else 0)
