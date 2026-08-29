"""v109 — drag-to-reorder, and per-page hold (the first payload-format change).

`hold` is the first new payload field since the frame format itself, so the whole
suite is built around one rule: **it must be additive in both directions.**

  - A page with no `hold` reads as 1, so every Skribl posted before v109 plays
    exactly as it always did.
  - `hold` is written ONLY when it is greater than 1, so an animation with no
    holds serialises to the same bytes as before — asserted below by comparing a
    real payload against the pre-v109 shape.
  - A v109 payload opened by an older player degrades to uniform timing rather
    than breaking, because an unknown field is simply ignored.

Timing is verified off the GIF byte stream: per-frame delays are readable there,
which makes the exported file the oracle for what "hold" actually means. A state
check would prove nothing about the encoders.
"""
from playwright.sync_api import sync_playwright

import os
BASE = os.environ.get("SKRIBL_BASE", "http://127.0.0.1:5001")

results = []
def check(name, ok, detail=""):
    results.append((bool(ok), name))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  — {detail}" if detail else ""))


def gif_delays(b):
    """Per-frame delay (centiseconds) in order, straight out of the file."""
    flags = b[10]
    pos = 13
    if flags & 0x80:
        pos += 3 * 2 ** ((flags & 7) + 1)
    delays, pending = [], None
    while pos < len(b):
        blk = b[pos]
        if blk == 0x21:
            label = b[pos + 1]
            pos += 2
            size = b[pos]
            data = b[pos + 1:pos + 1 + size]
            pos += 1 + size
            while b[pos]:
                pos += 1 + b[pos]
            pos += 1
            if label == 0xF9:
                pending = data[1] | (data[2] << 8)
        elif blk == 0x2C:
            lf = b[pos + 9]
            pos += 10
            if lf & 0x80:
                pos += 3 * 2 ** ((lf & 7) + 1)
            pos += 1
            while b[pos]:
                pos += 1 + b[pos]
            pos += 1
            delays.append(pending)
            pending = None
        else:
            break
    return delays


def draw(pg, x0, n=10):
    b = pg.locator("#pad").bounding_box()
    pg.mouse.move(b["x"] + x0, b["y"] + 90)
    pg.mouse.down()
    for i in range(n):
        pg.mouse.move(b["x"] + x0 + i * 7, b["y"] + 95)
    pg.mouse.up()
    pg.wait_for_timeout(80)


with sync_playwright() as p:
    br = p.chromium.launch()
    ctx = br.new_context(viewport={"width": 1280, "height": 950}, accept_downloads=True)
    pg = ctx.new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(BASE + "/flip", wait_until="load")
    pg.wait_for_timeout(900)
    for i in range(3):
        pg.evaluate("() => addFrame()")
        draw(pg, 70 + i * 25, 8 + i * 5)
    total = pg.evaluate("() => frames.length")

    print("\nDRAG-TO-REORDER")
    before = pg.evaluate("() => frames.map(f => f.strokes.length)")
    tiles = pg.locator("#strip .frame")
    src = tiles.nth(total - 1).bounding_box()
    dst = tiles.nth(1).bounding_box()
    pg.mouse.move(src["x"] + src["width"] / 2, src["y"] + src["height"] / 2)
    pg.mouse.down()
    for k in range(12):
        pg.mouse.move(src["x"] + src["width"] / 2 + (dst["x"] - src["x"]) * (k + 1) / 12,
                      src["y"] + src["height"] / 2)
    pg.mouse.up()
    pg.wait_for_timeout(400)
    after = pg.evaluate("() => frames.map(f => f.strokes.length)")
    check("dragging the last page onto slot 2 moves it there",
          after[1] == before[-1] and len(after) == len(before), f"{before} -> {after}")
    check("the dragged page stays selected", pg.evaluate("() => idx") == 1,
          f"idx={pg.evaluate('() => idx')}")
    order = pg.evaluate("() => frames.map(f => f.strokes.length)")
    tiles.nth(2).click()
    pg.wait_for_timeout(250)
    check("a plain tap still selects instead of reordering",
          pg.evaluate("() => frames.map(f => f.strokes.length)") == order
          and pg.evaluate("() => idx") == 2)

    print("\nHOLD — defaults and clamping (read defensively, never trusted)")
    check("a page with no hold field reads as 1",
          pg.evaluate("() => frameHold({strokes:[],strokeGroups:[]})") == 1)
    check("hold 0 clamps up to 1", pg.evaluate("() => frameHold({hold:0})") == 1)
    check("a negative hold clamps to 1", pg.evaluate("() => frameHold({hold:-3})") == 1)
    check("garbage clamps to 1", pg.evaluate("() => frameHold({hold:'banana'})") == 1)
    check("an absurd hold clamps down to MAX_HOLD",
          pg.evaluate("() => frameHold({hold:999})") == pg.evaluate("() => MAX_HOLD"))
    check("null frame is safe", pg.evaluate("() => frameHold(null)") == 1)

    print("\nHOLD — the UI cycles and shows it")
    pg.evaluate("() => { go(0); }")
    pg.wait_for_timeout(200)
    # v226: the page-bar Hold button retired and the BADGE on the tile is the
    # control. It was already showing the value the button cycled, on the tile
    # the value belonged to — two pieces of interface for one fact, and the
    # better-placed one was the one you could not press.
    seq = []
    for _ in range(5):
        pg.locator("#strip .frame").nth(0).locator(".holdbadge").click()
        pg.wait_for_timeout(180)
        seq.append(pg.evaluate("() => frameHold(frames[0])"))
    check("the tile's hold badge cycles 2,3,4 then wraps to 1", seq == [2, 3, 4, 1, 2], str(seq))
    check("a held page shows its badge without hovering",
          pg.evaluate("() => !!strip.children[0].querySelector('.holdbadge')")
          and pg.locator("#strip .frame").nth(0).locator(".holdbadge").is_visible())
    pg.evaluate("() => { frames[0].hold = 1; buildStrip(); }")
    pg.wait_for_timeout(150)
    # The badge still EXISTS at hold 1 — it has to, or there would be no way to
    # start a hold from the strip, which is exactly why a button used to. What
    # changes is that it is marked idle and CSS hides it unless the tile is
    # active, hovered or focused. Page 0 is the active page here, so it shows.
    check("at the default hold the badge is marked idle, not removed",
          pg.evaluate("() => strip.children[0]"
                      ".querySelector('.holdbadge').classList.contains('idle')"),
          "a badge that only appears once a hold is set cannot START one")
    check("...and an idle badge on a NON-active tile is hidden",
          not pg.locator("#strip .frame").nth(1).locator(".holdbadge").is_visible(),
          "x1 on every tile would be noise on a strip that shows drawings")

    print("\nPAYLOAD — additive in both directions")
    plain = pg.evaluate("() => JSON.stringify(serializeFlip({media:false}))")
    check("with no holds, the payload contains no 'hold' key at all",
          '"hold"' not in plain, "hold present" if '"hold"' in plain else "clean")
    pg.evaluate("() => { frames[1].hold = 3; buildStrip(); }")
    pg.wait_for_timeout(150)
    held = pg.evaluate("() => JSON.parse(JSON.stringify(serializeFlip({media:false}))).frames.map(f => f.hold)")
    check("a held page writes hold, the others stay absent",
          held[1] == 3 and held[0] is None and held[2] is None, str(held))
    check("frame shape is otherwise unchanged",
          pg.evaluate("""() => { const f=serializeFlip({media:false}).frames[0];
              return ['strokes','strokeGroups','background'].every(k => k in f); }"""))
    check("copy/paste carries the hold with the page",
          pg.evaluate("() => { const c = deepCopy(frames[1]); return frameHold(c); }") == 3)

    # THE HALF THIS SUITE WAS MISSING, and the bug that hid in it for months.
    # Everything above proves a hold is WRITTEN. Nothing asked whether it comes
    # BACK — and it did not: applyPayload rebuilt every current-format frame
    # through healFrame, which returned {strokes, strokeGroups} and dropped the
    # hold on the floor. Set a page to x3, save a draft, reopen it, and the
    # timing was silently gone. The same path restores the AUTOSAVE, so an
    # ordinary reload lost it too. Found by hand while generating a demo file
    # whose key poses were meant to be held, not by any assertion here.
    #
    # A round trip is the only shape that catches this: serialise, throw the
    # live state away, load it back, and read the hold off the RESTORED frames.
    payload = pg.evaluate("() => JSON.parse(JSON.stringify(serializeFlip({media:false})))")
    restored = pg.evaluate("""(d) => {
      frames.length = 0;
      frames.push({ strokes: [], strokeGroups: [], hold: 1 });   // wipe the state first
      applyPayload(d);
      return frames.map(f => frameHold(f));
    }""", payload)
    check("a hold SURVIVES a save and load",
          restored[1] == 3,
          f"{restored} — written faithfully and dropped on the way back in is "
          f"the shape a write-only test cannot see")
    check("...and the unheld pages come back at the default",
          restored[0] == 1 and restored[2] == 1, str(restored))

    print("\nTIMING — read out of the exported GIF, not off the state")
    fps = pg.evaluate("() => fps")
    base_cs = round(round(1000 / fps) / 10)
    pg.evaluate("() => { frames.forEach(f => f.hold = 1); frames[1].hold = 3; buildStrip(); }")
    pg.evaluate("() => openExportSheet()")
    pg.wait_for_timeout(400)
    with pg.expect_download(timeout=60000) as dl:
        pg.click("#exportGif")
    delays = gif_delays(open(dl.value.path(), "rb").read())
    check("one delay per page", len(delays) == total, f"{len(delays)} vs {total}")
    check("the held page lasts 3x the others",
          delays[1] == base_cs * 3 and delays[0] == base_cs,
          f"{delays} (base {base_cs}cs)")
    check("total GIF duration grows by exactly the extra holds",
          sum(delays) == base_cs * (total + 2), f"sum {sum(delays)}cs")

    print("\nPLAYER — a held Skribl plays; a pre-v109 one is untouched")
    # Posted through the API rather than the UI so the check is deterministic and
    # doesn't depend on the share flow's timing.
    def post(frames_payload):
        r = ctx.request.post(BASE + "/api/skribls", data={
            "title": "hold harness", "playbackMode": "flip", "fps": 12,
            "canvasSize": {"cssWidth": 640, "cssHeight": 460, "dpr": 1},
            "frames": frames_payload})
        return r.json().get("id")

    stroke = [{"x": 40, "y": 40}, {"x": 200, "y": 120}]
    held_id = post([{"strokes": stroke, "strokeGroups": [2]},
                    {"strokes": stroke, "strokeGroups": [2], "hold": 3},
                    {"strokes": stroke, "strokeGroups": [2]}])
    old_id = post([{"strokes": stroke, "strokeGroups": [2]},
                   {"strokes": stroke, "strokeGroups": [2]},
                   {"strokes": stroke, "strokeGroups": [2]}])
    check("a payload carrying hold is accepted by the API", bool(held_id), str(held_id))
    check("a pre-v109 payload (no hold anywhere) is still accepted", bool(old_id), str(old_id))

    for label, pid in (("held", held_id), ("pre-v109", old_id)):
        player = ctx.new_page()
        perrs = []
        player.on("pageerror", lambda e, _p=perrs: _p.append(str(e)))
        player.goto(f"{BASE}/s/{pid}", wait_until="load")
        player.wait_for_timeout(1800)
        check(f"the {label} Skribl loads in the player with no errors",
              not perrs, "; ".join(perrs[:2]))
        check(f"the {label} Skribl renders its frames",
              player.evaluate("() => !!document.getElementById('canvas')"))
        player.close()

    check("no Flip page errors across the whole feature", not errs, "; ".join(errs[:2]))

    br.close()

print("\nPAGE BAR — what it says, and where it now exists at all")
# HISTORY, because the premise of this section inverted. It was written when
# every .pb-tx label hid below 560px, which left "×1" bare and left Move as two
# unlabelled arrows in a bar that also read "Page 10 / 12" — they looked like
# page navigation while actually reordering the animation. It therefore ran at a
# PHONE viewport, where the labels were gone.
#
# v227 removed the page bar from the compact surface entirely, and compact is
# every width at or below 640 — which is every width the label-hiding rules
# applied to. So the bar is never icon-only any more, and running this section
# at 390px measured a bar inside a display:none ancestor: querySelector still
# finds hidden markup, so most of these assertions were passing VACUOUSLY and
# only the one that asked about LAYOUT noticed.
#
# ⚑ FOLLOW-UP, worth a look but not fixed here: the `.pb` label-hiding rules in
# flip.css are now unreachable for the same reason. Dead CSS, to be removed with
# the rest of the breakpoint migration rather than piecemeal.
#
# It runs at a REGULAR width now, where the bar exists — and the compact half of
# the claim is asserted first, since "the bar is gone here" is the change.
with sync_playwright() as _p:
    _b = _p.chromium.launch()
    _pgc = _b.new_page(viewport={"width": 390, "height": 844})
    _pgc.goto(f"{BASE}/flip", wait_until="load")
    _pgc.wait_for_timeout(1300)
    check("at phone width there is no page bar to be icon-only",
          _pgc.evaluate("() => getComputedStyle("
                        "document.getElementById('pagebar')).display") == "none",
          "v227: the compact surface carries these operations on the tile")
    check("...and the tile carries the operations instead",
          _pgc.evaluate("() => document.querySelectorAll('#strip .pageops').length") > 0,
          "verify_compactops.py holds that surface in full")
    _pgc.close()

    _pg = _b.new_page(viewport={"width": 900, "height": 844})
    _errs = []
    _pg.on("pageerror", lambda e: _errs.append(str(e)))
    _pg.goto(f"{BASE}/flip", wait_until="load")
    _pg.wait_for_timeout(1300)
    _pg.evaluate("() => { addFrame(false); addFrame(false); }")
    _pg.wait_for_timeout(400)

    check("the bar is here at a regular width",
          _pg.evaluate("() => getComputedStyle("
                       "document.getElementById('pagebar')).display") != "none",
          "everything below measures the bar, so it has to be laid out")
    check("its labels are visible, which is the premise that inverted",
          _pg.evaluate("() => getComputedStyle("
                       "document.querySelector('#pbCopy .pb-tx')).display") != "none",
          "the icon-only case no longer exists — see the note above")
    check("#pbCopy carries a glyph beside its label",
          _pg.evaluate("() => !!document.querySelector('#pbCopy .pb-glyph svg')"),
          "the glyphs still do work even with the words present")
    check("#pbCopy's glyph is actually rendered",
          _pg.evaluate("() => { const g = document.querySelector('#pbCopy .pb-glyph');"
                       " return g && g.offsetParent !== null"
                       " && g.getBoundingClientRect().width > 4; }"),
          "present in markup but not laid out")

    # The Move buttons carry ONLY an arrow. A page RECTANGLE was once added
    # beside the arrow and reverted — at 11px a tiny rect renders as a zero, so
    # the buttons read "◀ 0". v207 replaced the ◀/▶ TEXT arrows with SVG
    # chevrons (so the page bar is uniformly SVG, no mixed text/SVG glyphs);
    # the chevron IS the arrow, not an extra glyph. Pin the real concern: no
    # <rect> in the Move glyph, and the arrow is a single chevron path.
    for _id in ("pbLeft", "pbRight"):
        _g = _pg.evaluate(f"""() => {{ const g = document.querySelector('#{_id} .pb-glyph svg'); if (!g) return null;
            return {{ rects: g.querySelectorAll('rect').length, paths: g.querySelectorAll('path').length }}; }}""")
        check(f"#{_id} glyph is a chevron arrow, not a page rectangle that reads as a zero",
              _g is not None and _g["rects"] == 0 and _g["paths"] == 1,
              f"{_g} — a <rect> here renders as a 0 at this size")
        check(f"#{_id} still names its action for assistive tech",
              "move" in (_pg.get_attribute(f"#{_id}", "aria-label") or "").lower(),
              _pg.get_attribute(f"#{_id}", "aria-label"))

    # The original concern here was that flip.js rewrites .pb-ic's textContent on
    # every render, so a glyph placed inside it would survive the first paint
    # and vanish on the first page change. v226 moved the hold to the tile, and
    # the concern moved with it and got SHARPER: buildStrip() rebuilds every
    # badge from scratch on every render, so the value has to come from the
    # frame each time rather than from the DOM that was there before.
    _pg.evaluate("() => { idx = 0; buildStrip(); render(); }")
    _pg.wait_for_timeout(200)
    _pg.locator("#strip .frame").nth(0).locator(".holdbadge").click()
    _pg.wait_for_timeout(250)
    # pbLeft, not pbRight: two addFrame() calls leave idx on the LAST page, so
    # "move right" is correctly disabled there and Playwright waits forever.
    _pg.evaluate("() => { idx = frames.length - 1; buildStrip(); render(); }")
    _pg.click("#pbLeft")
    _pg.wait_for_timeout(250)
    _pg.evaluate("() => { idx = 0; buildStrip(); render(); }")
    _pg.wait_for_timeout(300)
    check("the hold survives re-renders and page changes",
          _pg.evaluate("() => frameHold(frames[0])") == 2,
          "buildStrip rebuilds every badge, so the value must come from the frame")
    check("the hold count still reads as a multiplier",
          "\u00d7" in (_pg.locator("#strip .frame").nth(0)
                       .locator(".holdbadge").inner_text() or ""),
          _pg.locator("#strip .frame").nth(0).locator(".holdbadge").inner_text())
    check("aria-label still names the action for screen readers",
          "move" in (_pg.get_attribute("#pbLeft", "aria-label") or "").lower(),
          _pg.get_attribute("#pbLeft", "aria-label"))
    check("no JS errors at phone width", not _errs, "; ".join(_errs[:2]))
    _b.close()

# ----------------------------------------------------------------------
# v237 — an expensive frame must not distort its NEIGHBOURS' timing.
#
# Everything above this proves a hold is written and read correctly. None of
# it asks whether the frames come out on screen for the length of time they
# were promised, and that is where the bug was: the scheduler waited a flat
# interval AFTER painting, so each frame stayed up for its interval plus
# whatever the NEXT frame cost to draw. With every page costing the same that
# is invisible. Put a blurred in-between (~6,000 points) next to a key page
# (45) and the key page held half again as long as it should.
#
# The suites for hold all passed throughout. A suite that only tests the
# direction a feature works passes forever while the feature is broken.
# ----------------------------------------------------------------------
print("\nPLAYBACK EVENNESS — a heavy frame must not stretch its neighbours")
with sync_playwright() as _p2:
    _b2 = _p2.chromium.launch()
    _t = _b2.new_page(viewport={"width": 1000, "height": 860})
    _terrs = []
    _t.on("pageerror", lambda e: _terrs.append(str(e)))
    _t.goto(BASE + "/flip", wait_until="load")
    _t.wait_for_timeout(1200)

    # Light poses with one genuinely expensive frame between them, built with
    # the app's own in-between so the cost is the real thing.
    made = _t.evaluate("""() => {
      const mk = (dy) => { const pts = [];
        for (let i = 0; i <= 40; i++)
          pts.push({ x: 120 + i * 6, y: 200 + dy, color: '#ffffff', size: 6,
                     t: i * 4, erase: false, start: i === 0 });
        return { strokes: pts, strokeGroups: [pts.length], hold: 1 }; };
      const a = mk(0), b = mk(140);
      const tw = buildTween(a, b);
      if (!tw) return null;
      frames = [a, tw, b, mk(70), mk(30)];
      idx = 0; buildStrip(); render();
      return { heavy: tw.strokes.length, light: a.strokes.length }; }""")
    check("a heavy frame was built to test with", made is not None, str(made))

    if made:
        # Anti-vacuity: if the "heavy" frame is not actually expensive to paint,
        # evenness is free and the assertions below prove nothing.
        cost = _t.evaluate("""() => {
          const one = (i) => { idx = i; const t0 = performance.now();
            for (let k = 0; k < 4; k++) render();
            return (performance.now() - t0) / 4; };
          return { heavy: +one(1).toFixed(2), light: +one(0).toFixed(2) }; }""")
        check("the heavy frame really is far more expensive to paint",
              cost["heavy"] > cost["light"] * 8,
              f"heavy {cost['heavy']}ms vs light {cost['light']}ms — "
              f"too close for this test to mean anything")

        # Time frames as the viewer sees them: gap between successive paints.
        rows = _t.evaluate("""() => new Promise(res => {
          const marks = [], orig = window.render;
          window.render = function(){ const r = orig.apply(this, arguments);
            marks.push({ t: performance.now(), i: idx }); return r; };
          fps = 12; play();
          setTimeout(() => { stop(); window.render = orig;
            const out = [];
            for (let k = 1; k < marks.length; k++)
              out.push({ i: marks[k-1].i, ms: marks[k].t - marks[k-1].t });
            res(out); }, 4000); })""")
        check("playback actually advanced through several frames",
              len(rows) >= 12, f"only {len(rows)} frame changes")

        if len(rows) >= 12:
            # Drop the first pass: an unpainted frame's cost is estimated, and
            # the estimate converges once each frame has been drawn.
            # Drop the first pass (an unpainted frame's cost is estimated, and
            # the estimate converges once each frame has been drawn) AND the
            # last sample, which straddles the stop() call and so measures
            # teardown rather than a frame. Leaving it in made this a flake:
            # it read 253ms on one run and passed on the next by timing luck.
            steady = rows[6:-1]
            target = 1000.0 / 12
            worst = max(abs(r["ms"] - target) for r in steady)
            heavy = [r["ms"] for r in steady if r["i"] == 1]
            near = [r["ms"] for r in steady if r["i"] == 0]
            check("no frame runs more than 25% off its target once warmed up",
                  worst < target * 0.25,
                  f"worst deviation {worst:.0f}ms from {target:.0f}ms target")
            check("the page BEFORE the heavy frame is not stretched by it",
                  near and abs(sum(near)/len(near) - target) < target * 0.25,
                  f"held {sum(near)/len(near):.0f}ms against a {target:.0f}ms target"
                  if near else "never sampled")
            check("and the heavy frame itself holds its own interval",
                  heavy and abs(sum(heavy)/len(heavy) - target) < target * 0.25,
                  f"held {sum(heavy)/len(heavy):.0f}ms against a {target:.0f}ms target"
                  if heavy else "never sampled")
    # ------------------------------------------------------------------
    # v239 — a hold must land on the page that DECLARES it, and must keep
    # working after the first time round the loop.
    #
    # Everything above proves a hold is written, read, and round-trips. None of
    # it watched a hold actually happen during playback, and two defects were
    # sitting on one line:
    #   * the delay was taken from frames[playI] AFTER playStep() advanced it,
    #     so a hold stretched the page BEFORE the one carrying it;
    #   * playI is never wrapped, so from the second loop on frames[playI] is
    #     undefined, frameHold() falls back to 1, and every hold in the
    #     document is silently ignored for the rest of playback.
    # The second one is why this has to measure a LATER pass, not the first.
    # ------------------------------------------------------------------
    print("\nHOLD IN PLAYBACK — on the right page, and on every pass")
    # _b2, not br: br belongs to an earlier sync_playwright() context that has
    # already exited, so using it here raises "Event loop is closed". This
    # block was verified standalone, in its own context, which is precisely
    # the arrangement that hides the mistake.
    hb = _b2.new_page(viewport={"width": 900, "height": 820})
    hb_errs = []
    hb.on("pageerror", lambda e: hb_errs.append(str(e)))
    hb.goto(BASE + "/flip", wait_until="load")
    hb.wait_for_timeout(900)
    built = hb.evaluate("""() => {
      const mk = (dy) => { const p = [];
        for (let i = 0; i < 8; i++)
          p.push({ x: 150 + i * 20, y: 150 + dy, color: '#ffffff', size: 10,
                   t: i * 3, erase: false, start: i === 0 });
        return { strokes: p, strokeGroups: [p.length], hold: 1 }; };
      frames = [mk(0), mk(40), mk(80), mk(120), mk(160), mk(200)];
      frames[2].hold = 2;                     // one page, held double
      idx = 0; buildStrip(); render();
      return frames.map(f => f.hold); }""")
    check("a document with one held page was built", built == [1, 1, 2, 1, 1, 1],
          str(built))

    rows = hb.evaluate("""() => new Promise(res => {
      const marks = [], orig = window.render;
      window.render = function(){ const r = orig.apply(this, arguments);
        marks.push({ t: performance.now(), i: idx }); return r; };
      fps = 12; play();
      setTimeout(() => { stop(); window.render = orig;
        const out = [];
        for (let k = 1; k < marks.length; k++)
          out.push({ i: marks[k-1].i, ms: marks[k].t - marks[k-1].t });
        res(out); }, 4200); })""")

    # 7 hold-units per loop at 12fps is ~583ms, so 4.2s is several loops. Drop
    # the first pass entirely: that is the only one the pre-fix code got even
    # partly right, and measuring it would hide the wrap defect.
    later = rows[8:]
    seen = set(r["i"] for r in later)
    check("playback looped, so a pass AFTER the first was measured",
          len(rows) >= 16 and len(seen) >= 5,
          f"{len(rows)} frame changes, {len(seen)} distinct pages — the wrap "
          f"defect only shows after the first loop")

    def _med(idx_):
        v = sorted(r["ms"] for r in later if r["i"] == idx_)
        return v[len(v)//2] if v else None

    target = 1000.0 / 12
    held, before, plain = _med(2), _med(1), _med(4)
    check("the held page is on screen for TWO frame slots",
          held is not None and abs(held - target*2) < target*0.35,
          f"page 2 held {held:.0f}ms, expected {target*2:.0f}ms"
          if held else "never sampled")
    check("and the page BEFORE it is not the one being stretched",
          before is not None and abs(before - target) < target*0.35,
          f"page 1 held {before:.0f}ms, expected {target:.0f}ms — the hold "
          f"landed on the wrong page" if before else "never sampled")
    check("an ordinary page still gets exactly one slot",
          plain is not None and abs(plain - target) < target*0.35,
          f"page 4 held {plain:.0f}ms, expected {target:.0f}ms" if plain else "never sampled")
    check("no JS errors during held playback", not hb_errs, "; ".join(hb_errs[:2]))
    hb.close()

    check("no JS errors during timed playback", not _terrs, "; ".join(_terrs[:2]))
    _b2.close()

ok = sum(1 for o, _ in results if o)
print("\n" + "=" * 60)
print(f"{ok}/{len(results)} passed")
for o, n in results:
    if not o:
        print(f"  FAILED: {n}")
raise SystemExit(0 if ok == len(results) else 1)
