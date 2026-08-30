"""v232 — Smudge and Blur: the same sweep, two different verbs.

WHY BLUR NEARLY DID NOT EXIST. A frame is `{strokes, strokeGroups}` — a flat
array of `{x, y, color, size, t, erase, start}`. Liquify works because
displacement is expressible in a format made of points. You cannot blur a
polyline by moving its points, there is no raster layer to convolve, and adding
one is a format change the player must honour.

The way through is a detail of `paintStatic()`: a stroke whose FIRST point is
opaque is painted by `paintSeg` with each point's OWN colour and OWN size. So
per-point colour is honoured, and blur becomes sayable in this format — fade a
point toward the ground it sits on and widen it. It reads as defocus on line
art and the player renders it identically, because the player runs the same
paint path.

WHAT IT IS NOT, asserted here so nobody later mistakes it for a raster blur: it
cannot soften a photograph underneath, and it fades toward the page's background
colour rather than toward whatever is actually behind the line.

THE ASSERTION THAT MATTERS MOST is the one about sample rate. The obvious
implementation fades a little on every pointermove, which makes the tool's
strength a property of the HARDWARE — a 240Hz phone blurs several times harder
than a 60Hz laptop for the same gesture, and v230's coalesced sampling made that
worse on purpose. Measured before it was fixed, one short swipe took #ffffff to
rgb(87,89,92).

Saturating the accumulation was the obvious repair and it was NOT enough — it
bounds the maximum while a 4-event sweep still lands somewhere different from a
40-event one. What fixes it is accruing per PIXEL TRAVELLED: distance is the
quantity a brush physically deposits against, and it is the same number however
often the OS sampled the finger. Measured across that change, the gap between a
4-event and a 40-event sweep went from 117/255 to 6/255.

All of which is invisible in a screenshot, and is the thing most likely to be
"simplified" back out by someone who reads the accumulator as ceremony.
"""
import os
import sys

BASE = os.environ.get("SKRIBL_BASE", "http://127.0.0.1:5001")

try:
    from playwright.sync_api import sync_playwright
except ImportError:                                    # pragma: no cover
    print("SKIP: playwright is not installed")
    sys.exit(0)

results = []


def check(name, ok, detail=""):
    results.append((bool(ok), name))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  — {detail}" if detail else ""))


SNAP = """() => { const f = frame();
  return { pts: f.strokes.length, groups: f.strokeGroups.length,
           xs: f.strokes.map(p => Math.round(p.x * 10) / 10),
           ys: f.strokes.map(p => Math.round(p.y * 10) / 10),
           sizes: f.strokes.map(p => p.size),
           cols: f.strokes.map(p => p.color) }; }"""


def line(page, cx, cy):
    page.mouse.move(cx - 90, cy)
    page.mouse.down()
    for i in range(1, 10):
        page.mouse.move(cx - 90 + i * 20, cy)
    page.mouse.up()
    page.wait_for_timeout(300)


with sync_playwright() as p:
    br = p.chromium.launch()
    try:
        page = br.new_page(viewport={"width": 1280, "height": 900})
        errs = []
        page.on("pageerror", lambda e: errs.append(str(e)))
        page.goto(BASE + "/flip", wait_until="networkidle")
        page.wait_for_timeout(700)

        print("\nTHE LIB — arithmetic three tools share")
        check("lib/brushfield.js is loaded on Flip",
              page.evaluate("() => typeof window.SkriblBrushField") == "object",
              "a lib the template does not list is a lib that does not exist")
        for tool in ("smudge", "blur"):
            check(f"{tool} is in Flip's tool registry",
                  tool in page.evaluate("() => SkriblFlipTools.list()"),
                  str(page.evaluate("() => SkriblFlipTools.list()")))

        # Falloff. Sharpness is what separates Smudge from Liquify: same
        # traversal, a fingertip instead of a field.
        w = page.evaluate("""() => {
          const B = window.SkriblBrushField;
          return { centre: B.weight(0, 100, 1), edge: B.weight(100, 100, 1),
                   outside: B.weight(400, 100, 1),
                   soft: B.weight(25, 100, 1), sharp: B.weight(25, 100, 2.2) };
        }""")
        check("the falloff is 1 at the centre and 0 at the rim",
              w["centre"] == 1 and w["edge"] == 0 and w["outside"] == 0,
              str(w))
        check("a sharper falloff concentrates the effect under the touch",
              w["sharp"] < w["soft"],
              f"sharp={w['sharp']:.3f} soft={w['soft']:.3f} — this is the whole "
              "difference between Smudge and Liquify; equal, they are one tool "
              "shipped twice")

        # The colour mixer has to survive every form a colour takes here, and
        # refuse the ones it does not understand rather than guessing black.
        mixed = page.evaluate("""() => {
          const B = window.SkriblBrushField;
          return { hex: B.mix('#ffffff', '#000000', 0.5),
                   keepsAlpha: B.mix('rgba(255, 0, 0, 0.4)', '#000000', 0.5),
                   junk: B.mix('not-a-colour', '#000000', 0.5),
                   zero: B.mix('#ffffff', '#000000', 0) };
        }""")
        check("it mixes hex toward a target",
              mixed["hex"] == "rgb(128, 128, 128)", str(mixed["hex"]))
        check("...preserves an alpha the stroke already carried",
              "0.4" in mixed["keepsAlpha"],
              f"{mixed['keepsAlpha']} — blur must not quietly make a "
              "see-through stroke opaque")
        check("...and leaves a colour it cannot parse alone",
              mixed["junk"] == "not-a-colour",
              f"{mixed['junk']} — a parser that guesses turns one bad string "
              "into a silhouette")

        b = page.locator("#pad").bounding_box()
        cx, cy = b["x"] + b["width"] / 2, b["y"] + b["height"] / 2

        print("\nSMUDGE — it moves ink and does not lay any")
        line(page, cx, cy)
        before = page.evaluate(SNAP)
        page.evaluate("() => setTool('smudge')")
        page.wait_for_timeout(200)
        page.mouse.move(cx, cy)
        page.mouse.down()
        for i in range(1, 7):
            page.mouse.move(cx, cy - i * 8)
        page.mouse.up()
        page.wait_for_timeout(400)
        after = page.evaluate(SNAP)
        check("smudge displaces points that were under the brush",
              after["ys"] != before["ys"],
              "nothing moved — the sweep did not reach the ink")
        check("...and subdivides so the pull curves instead of kinking",
              after["pts"] > before["pts"],
              f"{before['pts']} -> {after['pts']} points; two vertices in a "
              "brush can only bend into a corner")
        check("smudge lays NO new stroke of its own",
              after["groups"] == before["groups"],
              f"{before['groups']} -> {after['groups']} groups — a tool that "
              "works on existing ink must not also draw")
        # THE REPORT THAT SENT THIS BACK: "3rd is smudge. Looks like liquefy."
        # It did, because it WAS — displacement with two constants changed. Real
        # smudged paint thins as it travels: there is only so much pigment and
        # dragging spreads it over more area. So smudge also fades and widens
        # what it carries, which is the difference a user actually sees.
        smeared = sum(1 for a, q in zip(after["cols"], before["cols"]) if a != q)
        check("smudge SMEARS as well as displacing",
              smeared > 0,
              f"{smeared} points recoloured — displacement alone is Liquify, "
              "and changing its constants gives you a sharper Liquify, not a "
              "different tool")


        # The smear needs per-point scratch state, and points are serialised
        # wholesale into every saved draft and shared Skribl. A scratch field
        # parked on the point would ride into the payload and past the server's
        # validator; it lives in a WeakMap keyed by the point instead.
        keys = page.evaluate("() => Object.keys(frame().strokes[2] || {})")
        check("smudge leaves no scratch fields on the points",
              all(not k.startswith("_") for k in keys),
              f"{keys} — a point is a payload field, not a scratchpad")

        page.evaluate("() => undoStroke()")
        page.wait_for_timeout(400)
        u = page.evaluate(SNAP)
        check("one undo restores the frame exactly",
              u["xs"] == before["xs"] and u["ys"] == before["ys"]
              and u["pts"] == before["pts"] and u["cols"] == before["cols"],
              "the snapshot undo has to cover the inserted points AND the smear")

        # ---- HOW FAR THE SMEAR ACTUALLY GOES --------------------------------
        # The check above is `smeared > 0`, which passes at every setting there
        # is -- including the one that sent this tool back with "looks like
        # liquefy". What a user sees is the MAGNITUDE: how far the dragged ink
        # gets toward the ground and how much wider it spreads.
        #
        # Its own gesture, and a long one on purpose. The smear accrues per pixel
        # travelled and saturates at 1, so a short drag reaches only part of the
        # response curve and the numbers below would be measuring the gesture
        # rather than the constants.
        # RESET IN-PAGE, NOT BY RELOADING. The editor persists its draft in
        # IndexedDB, so a reload RESTORES whatever the previous section left --
        # clearing localStorage does not touch it. The smear section measured a
        # 25.5px "source stroke" that way, against the 7px line it had just
        # drawn, because the section before it had left blurred halo passes in
        # the draft; it passed for one commit purely because of what happened to
        # run in front of it. Emptying the frame and pinning the brush is exact
        # and depends on no persistence layer at all.
        page.evaluate("""() => { frames.forEach(f => { f.strokes.length = 0;
            f.strokeGroups.length = 0; }); size = 7; setTool('pen'); render(); }""")
        page.wait_for_timeout(200)
        _bb = page.locator("#pad").bounding_box()
        _mx, _my = _bb["x"] + _bb["width"] / 2, _bb["y"] + _bb["height"] / 2
        line(page, _mx, _my)
        _src = page.evaluate("""() => { const f = frame();
            return { size: f.strokes[0].size, col: f.strokes[0].color }; }""")
        page.evaluate("() => setTool('smudge')"); page.wait_for_timeout(200)
        page.mouse.move(_mx - 30, _my); page.mouse.down()
        for _r in range(4):
            for _i in range(0, 24): page.mouse.move(_mx - 30 + _r * 18, _my + _i * 3)
            for _i in range(23, -1, -1): page.mouse.move(_mx - 30 + _r * 18, _my + _i * 3)
        page.mouse.up(); page.wait_for_timeout(350)
        _mag = page.evaluate("""(src) => {
            const f = frame();
            const rgb = (c) => { const m = String(c).match(/rgba?\((\d+)\s*,\s*(\d+)\s*,\s*(\d+)/i);
              if (m) return [+m[1], +m[2], +m[3]];
              const h = String(c).replace('#','');
              return /^[0-9a-f]{6}/i.test(h)
                ? [parseInt(h.slice(0,2),16), parseInt(h.slice(2,4),16), parseInt(h.slice(4,6),16)] : null; };
            const a = rgb(src.col), g = rgb(bgColor);
            if (!a || !g) return null;
            let fade = 0, spread = 0;
            for (const p of f.strokes) {
              const c = rgb(p.color);
              if (c) {
                // How far this point travelled from the ink toward the ground,
                // on whichever channel separates them most.
                let best = 0;
                for (let k = 0; k < 3; k++) {
                  const span = g[k] - a[k];
                  if (Math.abs(span) > 40) best = Math.max(best, (c[k] - a[k]) / span);
                }
                fade = Math.max(fade, best);
              }
              if (p.size) spread = Math.max(spread, p.size / src.size);
            }
            return { fade: +fade.toFixed(3), spread: +spread.toFixed(2) }; }""", _src)
        check("the rubbed gesture produced a measurable smear at all",
              _mag is not None and _mag["fade"] > 0 and _mag["spread"] > 1,
              f"{_mag} — with no smear the two bounds below are vacuous")
        # 0.32 / 0.45 were the shipped values until v257 and reach 0.32 and 1.45.
        # 0.55 / 0.9 reach 0.55 and 1.9. The bounds sit between the two pairs, so
        # reverting the response curve fails here by name rather than silently
        # making the tool look like Liquify again.
        check("dragged ink gets far enough toward the ground to READ as smeared",
              _mag is not None and _mag["fade"] >= 0.45,
              f"{_mag} — the values this replaced top out at 0.32, which is the "
              f"setting that was reported as 'looks like liquefy'")
        check("...and spreads far enough to read as thinning pigment",
              _mag is not None and _mag["spread"] >= 1.7,
              f"{_mag} — the values this replaced top out at 1.45x")

        print("\nBLUR — fades and widens, because it cannot convolve")
        page.evaluate("() => { localStorage.clear(); }")
        page.reload(wait_until="networkidle")
        page.wait_for_timeout(800)
        b = page.locator("#pad").bounding_box()
        cx, cy = b["x"] + b["width"] / 2, b["y"] + b["height"] / 2
        line(page, cx, cy)
        before = page.evaluate(SNAP)
        page.evaluate("() => setTool('blur')")
        page.wait_for_timeout(200)
        page.mouse.move(cx - 40, cy)
        page.mouse.down()
        for i in range(1, 6):
            page.mouse.move(cx - 40 + i * 12, cy)
        page.mouse.up()
        page.wait_for_timeout(400)
        after = page.evaluate(SNAP)
        # v256: BLUR IS A HALO NOW, so it emits passes and the arrays grow. The
        # old shape of this section pinned "adds and removes NO points", which
        # was correct for a tool that recoloured in place -- and recolouring in
        # place is precisely why it never softened anything.
        check("blur emits halo passes rather than only recolouring",
              after["groups"] > before["groups"] and after["pts"] > before["pts"],
              f"{before['pts']}/{before['groups']} -> {after['pts']}/{after['groups']} "
              f"— a stroke point is a solid round dab, so nothing done to its "
              f"colour can feather an edge; expanded translucent copies can")
        check("...and the page it leaves is well-formed",
              page.evaluate("""() => { const f = frame();
                return f.strokeGroups.reduce((a,b)=>a+b,0) === f.strokes.length
                    && f.strokes.filter(p=>p.start).length === f.strokeGroups.length; }"""),
              "groups must account for every point and every run start exactly once")
        # THE COST THAT MADE THIS AFFORDABLE. paintStatic gives every TRANSLUCENT
        # stroke its own offscreen layer -- clear, redraw, composite -- against a
        # LAYER_BUDGET of 24, and past the budget the whole frame paints direct
        # and every other stroke on it changes. Writing the halo's alpha as an
        # 8-digit hex dodges that entirely: alphaOf, which is the layering test,
        # only recognises rgba(), while the canvas still renders '#rrggbbaa'
        # translucent. Four passes per blurred stroke in rgba() form would blow
        # the budget after six strokes.
        _cost = page.evaluate("""() => { const f = frame();
            return { layerable: layerableCount(f.strokes), budget: LAYER_BUDGET,
                     hexAlpha: f.strokes.some(p => /^#[0-9a-f]{8}$/i.test(p.color)),
                     rgba: f.strokes.filter(p => /^rgba[(]/i.test(p.color)).length }; }""")
        check("the halo costs NOTHING against the stroke-layer budget",
              _cost["layerable"] == 0 and _cost["hexAlpha"] and _cost["rgba"] == 0,
              f"{_cost} — in rgba() form these same passes would each take an "
              f"offscreen layer and flip the frame to direct painting")


        # ---- THE ASSERTION WHOSE ABSENCE LET A FADE SHIP AS A BLUR ----------
        # Every check above this point reads POINT DATA -- sizes grew, colours
        # changed, groups account for their points. All of them passed for years
        # against a tool that did no blurring at all: it mixed each point toward
        # the background and widened it, which makes a line dimmer and fatter
        # with the same knife-sharp edge. Softening an edge is the one thing the
        # word promises, and no property of the stroke list can see whether it
        # happened. This one is measured in PIXELS, off a screenshot.
        #
        # The metric is the FEATHERED BAND: rows in a vertical slice through the
        # line whose brightness sits between the background and the core, i.e.
        # the transition. A real defocus widens it and lowers the peak, because
        # it spreads the same ink over more area. The old tool measured 5 rows
        # before a drag and 5 rows after.
        import io as _io
        from PIL import Image as _Image
        def _slice(_png, _x):
            _im = _Image.open(_io.BytesIO(_png)).convert("RGB")
            _px = _im.load()
            return [_px[_x, _y][0] for _y in range(_im.size[1])], _im.size
        def _feather(_col, _y0, _y1):
            _seg = _col[_y0:_y1]
            _lo, _hi = min(_seg), max(_seg)
            if _hi - _lo < 15: return None
            _sp = _hi - _lo
            return { "peak": _hi,
                     "core": sum(1 for _v in _seg if _v >= _lo + 0.85 * _sp),
                     "feather": sum(1 for _v in _seg if _lo + 0.15 * _sp <= _v < _lo + 0.85 * _sp) }

        # RESET IN-PAGE, NOT BY RELOADING. The editor persists its draft in
        # IndexedDB, so a reload RESTORES whatever the previous section left --
        # clearing localStorage does not touch it. This section measured a
        # 25.5px "source stroke" that way, against the 7px line it had just
        # drawn, because the section before it had left blurred halo passes in
        # the draft; it passed for one commit purely because of what happened to
        # run in front of it. Emptying the frame and pinning the brush is exact
        # and depends on no persistence layer at all.
        page.evaluate("""() => { frames.forEach(f => { f.strokes.length = 0;
            f.strokeGroups.length = 0; }); size = 7; setTool('pen'); render(); }""")
        page.wait_for_timeout(200)
        _b = page.locator("#pad").bounding_box()
        _cx, _cy = _b["x"] + _b["width"] / 2, _b["y"] + _b["height"] / 2
        line(page, _cx, _cy)
        _shot0 = page.locator("#pad").screenshot()
        _mid = int((_cx - _b["x"]))
        _c0, _sz = _slice(_shot0, _mid)
        _yc = int(_cy - _b["y"])
        _pre = _feather(_c0, max(0, _yc - 45), min(_sz[1], _yc + 45))
        # The stroke's own width, read BEFORE the blur. After it, every run is
        # translucent -- the core included -- so there is nothing left in the
        # frame to call the baseline; the first version of the check below asked
        # for the widest opaque run, got 0, and divided by it.
        _srcSize = page.evaluate("() => Math.max(...frame().strokes.map(p => p.size || 0))")
        page.evaluate("() => setTool('blur')"); page.wait_for_timeout(200)
        page.mouse.move(_cx - 80, _cy); page.mouse.down()
        for _r in range(3):
            for _i in range(0, 21): page.mouse.move(_cx - 80 + _i * 8, _cy)
            for _i in range(20, -1, -1): page.mouse.move(_cx - 80 + _i * 8, _cy)
        page.mouse.up(); page.wait_for_timeout(400)
        _shot1 = page.locator("#pad").screenshot()
        _c1, _ = _slice(_shot1, _mid)
        _post = _feather(_c1, max(0, _yc - 45), min(_sz[1], _yc + 45))
        check("the line was on screen to measure, before and after",
              bool(_pre) and bool(_post),
              f"{_pre} -> {_post} — a slice with no contrast makes every "
              f"comparison below vacuous")
        # A RATIO ALONE DOES NOT SEPARATE THE CASES, which is why there is a
        # floor as well. Restoring the old soft-edge scale (0.55x the brush
        # instead of 2.4x) measures 1 -> 4 feathered rows against the shipped
        # 2 -> 8: both are a 4x gain, so a ratio test passes a blur that barely
        # softens anything. The absolute band is what the eye reads.
        check("BLUR ACTUALLY SOFTENS THE EDGE",
              bool(_pre) and bool(_post)
              and _post["feather"] >= _pre["feather"] * 2 and _post["feather"] >= 6,
              f"feathered rows {_pre and _pre['feather']} -> {_post and _post['feather']} "
              f"— the tool this replaced measured 5 -> 5: it dimmed and fattened "
              f"the line and never touched the transition, which is the whole "
              f"meaning of the word. The old soft-edge scale reaches 4.")
        # AND THE SAME THING IN THE DATA, where it is exact rather than sampled.
        # The widest halo pass has to be meaningfully wider than the stroke it
        # softens: the old scale put it at 1.55x a 7px line, the shipped one at
        # 3.4x. This is the check that actually dies when the scale is reverted;
        # the pixel measurement above is the one that says it MATTERS.
        _widest = page.evaluate("() => Math.max(...frame().strokes.map(p => p.size || 0))")
        _spread = { "srcSize": round(_srcSize, 1), "widest": round(_widest, 1),
                    "ratio": round(_widest / max(0.001, _srcSize), 2) }
        check("the widest halo pass is far wider than the stroke it softens",
              _srcSize > 0 and _spread["ratio"] >= 2.5,
              f"{_spread} — 1.55x on the scale this replaced, 3.4x on the one "
              f"that ships; below about 2.5x the passes overlap too closely to "
              f"read as a falloff at all")
        check("...and the peak comes DOWN, because defocus spreads ink",
              bool(_pre) and bool(_post) and _post["peak"] < _pre["peak"],
              f"peak {_pre and _pre['peak']} -> {_post and _post['peak']}")
        # BEADING IS THE FAILURE MODE OF THE FIX. A hex-alpha pass is painted
        # direct, so translucent dabs COMPOUND where they overlap; at the source
        # line's own point spacing that drew a visible string of circles. The
        # cure is density, and density then needs the alpha paid back or the
        # line comes out brighter than it started. Ripple along the line's own
        # axis catches both: a beaded line oscillates, a smooth one does not.
        # DENSITY, ASSERTED ON ITS OWN CONTRACT RATHER THAN ON A PICTURE.
        #
        # A hex-alpha pass is painted DIRECT -- that is the point of writing the
        # alpha as hex, since the layered path is what costs LAYER_BUDGET -- and
        # direct painting makes translucent dabs COMPOUND where they overlap. At
        # the source line's own point spacing that draws a visible string of
        # circles, so every halo run is resampled until its samples sit well
        # inside a dab width and the overlap is uniform rather than periodic.
        #
        # TWO VISUAL METRICS WERE TRIED FIRST AND BOTH ARE GONE. Brightness along
        # the centre row scored the beaded build 1.0 and the shipped one 6.4, and
        # lit-height per column scored them 0.064 and 0.072: both ranked the
        # BROKEN version as the better one, because at the centre a beaded line
        # and a smooth one are equally white and the beads bulge at an edge that
        # a 60/255 threshold barely resolves. A check that prefers the bug is
        # worse than no check, so what is pinned here is the property
        # densification actually guarantees -- spacing relative to dab width --
        # which is exact, cheap, and dies the moment the resampling is removed.
        _space = page.evaluate("""() => { const f = frame(); let a = 0, worst = 0, runs = 0;
            for (const n of f.strokeGroups) {
              const seg = f.strokes.slice(a, a + n); a += n;
              // Halo passes are the translucent ones; the untouched runs are the
              // user's own opaque strokes and are deliberately left alone.
              const al = seg[0] && /^#[0-9a-f]{8}$/i.test(seg[0].color)
                ? parseInt(seg[0].color.slice(7), 16) / 255 : 1;
              if (al >= 1 || seg.length < 3) continue;
              runs++;
              let wide = 0; for (const q of seg) wide = Math.max(wide, q.size || 0);
              for (let k = 1; k < seg.length; k++) {
                const d = Math.hypot(seg[k].x - seg[k-1].x, seg[k].y - seg[k-1].y);
                worst = Math.max(worst, d / Math.max(0.001, wide));
              }
            }
            return { runs: runs, worstGapOverWidth: +worst.toFixed(3) }; }""")
        check("there are translucent passes to measure",
              _space["runs"] > 0,
              f"{_space} — with no halo runs the spacing check below is vacuous")
        check("every halo sample sits well inside a dab width",
              _space["worstGapOverWidth"] < 0.35,
              f"{_space} — the widest gap between consecutive samples, as a "
              f"fraction of the dab drawn there; undensified this is about 0.5 "
              f"and each overlap shows as a bead")

        # THE ONE THAT WOULD ROT SILENTLY. One long sweep and one short one over
        # the same ink must land in the same place, or the tool's strength is a
        # property of the device's sample rate.
        rates = page.evaluate("""async () => {
          const run = (steps) => {
            localStorage.clear();
            frames.length = 0; frames.push({strokes: [], strokeGroups: [], hold: 1});
            idx = 0;
            const f = frame(), now = performance.now();
            for (let i = 0; i < 10; i++)
              f.strokes.push({ x: 100 + i * 12, y: 200, color: '#ffffff',
                               size: 6, t: now + i, erase: false, start: i === 0 });
            f.strokeGroups.push(10);
            setTool('blur');
            fieldBegin({ x: 100, y: 200 }, 'Blur');
            for (let k = 1; k <= steps; k++)
              blurMove({ x: 100 + (220 * k / steps), y: 200 });
            fieldEnd();
            return f.strokes[4].color;
          };
          return { few: run(4), many: run(40) };
        }""")
        import re as _re
        def _chan(c):
            return [int(v) for v in _re.findall(r"\d+", c)[:3]]
        gap = max(abs(a - b) for a, b in zip(_chan(rates["few"]), _chan(rates["many"])))
        # NOT exact equality, and the tolerance is doing real work rather than
        # papering over a miss. Weight varies across the brush, so integrating
        # it from 4 samples cannot equal integrating it from 40 — that residual
        # is arithmetic, not a bug. Measured: 117/255 apart when the accrual was
        # per EVENT, 6/255 apart once it was per pixel travelled. A threshold of
        # 16 accepts the sampling residual and still fails the real defect by a
        # factor of seven.
        check("a fast sweep and a slow one converge on the same blur",
              gap <= 16,
              f"4 events -> {rates['few']}, 40 events -> {rates['many']}, "
              f"largest channel gap {gap} — a per-EVENT delta makes a 240Hz "
              "phone blur several times harder than a 60Hz laptop for the same "
              "gesture, and v230's coalesced sampling raised that rate on "
              "purpose. Accrue per pixel travelled instead.")

        print("\nOVER A PHOTO — the limit, said out loud instead of silently")
        # These tools move and recolour STROKE POINTS. A photograph is not
        # strokes, so sweeping one does nothing -- which is correct and looks
        # broken. Reported from the live demo on a drawing made over a photo.
        # Softening the photo itself needs a raster layer the frame format does
        # not have; what CAN be fixed is the silence.
        page.reload(wait_until="networkidle")
        page.wait_for_timeout(800)
        page.evaluate("""() => { localStorage.clear();
          frames.length = 0; frames.push({ strokes: [], strokeGroups: [], hold: 1 });
          idx = 0; render(); }""")
        noisy = page.evaluate("""async () => {
          const c = document.createElement('canvas'); c.width = 900; c.height = 700;
          const g = c.getContext('2d'); const im = g.createImageData(900, 700);
          for (let i = 0; i < im.data.length; i += 4) {
            const v = (Math.random() * 255) | 0;
            im.data[i] = v; im.data[i+1] = (v*7)%255; im.data[i+2] = (v*13)%255;
            im.data[i+3] = 255;
          }
          g.putImageData(im, 0, 0);
          const blob = await new Promise(r => c.toBlob(r, 'image/png'));
          return Array.from(new Uint8Array(await blob.arrayBuffer()));
        }""")
        page.evaluate("""(bytes) => {
          const f = new File([new Uint8Array(bytes)], 'noise.png', { type: 'image/png' });
          const dt = new DataTransfer(); dt.items.add(f);
          const input = document.getElementById('imageInput');
          input.files = dt.files;
          input.dispatchEvent(new Event('change', { bubbles: true }));
        }""", noisy)
        page.wait_for_timeout(1800)
        check("the photo is on screen and the page has no ink",
              page.evaluate("() => photoShowing()") is True
              and page.evaluate("() => frame().strokes.length") == 0,
              "without both, this section is testing the empty-canvas path")

        b = page.locator("#pad").bounding_box()
        cx, cy = b["x"] + b["width"] / 2, b["y"] + b["height"] / 2
        page.evaluate("() => setTool('smudge')")
        page.wait_for_timeout(200)
        page.mouse.move(cx - 60, cy)
        page.mouse.down()
        for i in range(1, 7):
            page.mouse.move(cx - 60 + i * 18, cy)
        page.mouse.up()
        page.wait_for_timeout(400)
        note = page.locator("#flipChip").text_content()
        check("smudging a photo SAYS it works on strokes, not the photo",
              "photo" in note.lower(),
              f"{note!r} — the sweep correctly does nothing, and doing nothing "
              "without saying why is how a tool gets reported as broken")
        check("...and it still lays no stroke of its own",
              page.evaluate("() => frame().strokes.length") == 0,
              "explaining the limit must not turn the tool into a pen")

        # ---- SILENCE IS A BUG, and it had one case covered out of two ----
        # v240 gave these tools a note for a photo showing, because the owner
        # reported the tool looking broken. The commoner case was left mute:
        # a drag that simply missed the ink. Same silence, same conclusion,
        # and no photo required to reach it -- which is why an audit that drove
        # every tool on an empty canvas found three tools doing nothing and
        # saying nothing.
        print("\nSILENCE — a tool that does nothing has to say why")
        # TAKE THE PHOTO BACK OFF FIRST. The block above deliberately leaves
        # one attached, and photoShowing() short-circuits to the photo note --
        # so without this the checks below pass or fail on the WRONG message
        # and prove nothing about the case they are named for.
        # Through the app's own removeBgImage(), not by assigning to the
        # module state: _fieldPhotoNoted is a const and bgImage has a teardown
        # (thumbnails, autosave) that a bare null assignment skips.
        page.evaluate("""() => {
            removeBgImage();
            for (const k in _fieldPhotoNoted) delete _fieldPhotoNoted[k];
            for (const k in _fieldMissNoted) delete _fieldMissNoted[k];
            render();
        }""")
        page.wait_for_timeout(250)
        check("the photo is off again, so these cases test what they name",
              page.evaluate("() => photoShowing()") is False,
              "photoShowing() still true — every check below would read the "
              "photo note instead")
        chip_now = lambda: page.evaluate(
            "() => { const e = document.getElementById('flipChip');"
            " return e.classList.contains('show') ? e.textContent : null; }")
        pad_box = page.eval_on_selector(
            "#pad", "e => { const r = e.getBoundingClientRect();"
            " return { x: r.x, y: r.y, w: r.width, h: r.height }; }")

        for _tool in ("smudge", "blur"):
            page.evaluate("""() => { frames.length = 1; frames[0].strokes = [];
                frames[0].strokeGroups = []; fi = 0;
                for (const k in _fieldMissNoted) delete _fieldMissNoted[k];
                render(); }""")
            page.evaluate("(t) => setTool(t)", _tool)
            line(page, pad_box["x"] + pad_box["w"] / 2, pad_box["y"] + pad_box["h"] / 2)
            page.wait_for_timeout(200)
            msg = chip_now()
            check(f"{_tool}: an EMPTY canvas is explained, not ignored",
                  bool(msg) and "draw something first" in msg, repr(msg))
            check(f"{_tool}: ...and explaining it lays no stroke",
                  page.evaluate("() => frame().strokes.length") == 0,
                  "a note must not turn the tool into a pen")

        # THE OTHER HALF, and the one a real user hits: ink exists, the drag
        # missed it. The wording has to differ -- "draw something first" is
        # wrong and faintly insulting when there is a drawing on screen.
        for _tool in ("smudge", "blur"):
            page.evaluate("""() => { frames.length = 1; frames[0].strokes = [];
                frames[0].strokeGroups = []; fi = 0; render(); setTool("pen"); }""")
            line(page, pad_box["x"] + pad_box["w"] * 0.35, pad_box["y"] + pad_box["h"] * 0.15)
            drawn = page.evaluate("() => frame().strokes.length")
            page.evaluate("() => { for (const k in _fieldMissNoted) delete _fieldMissNoted[k]; }")
            page.evaluate("(t) => setTool(t)", _tool)
            line(page, pad_box["x"] + pad_box["w"] * 0.35, pad_box["y"] + pad_box["h"] * 0.85)
            msg = chip_now()
            check(f"{_tool}: a drag that MISSED the ink says so",
                  bool(msg) and "over your lines" in msg,
                  f"{msg!r} with {drawn} points on the page")
            check(f"{_tool}: and does not claim the canvas is empty when it "
                  "is not", not (msg and "draw something first" in msg),
                  f"{msg!r} — there is a drawing on screen")

        check("no page error through any of it", not errs, "; ".join(errs[:2]))
    finally:
        br.close()

bad = [r for r in results if not r[0]]
print(f"\n{'=' * 62}\n{len(results) - len(bad)}/{len(results)} passed"
      + ("" if not bad else "  FAILURES: " + ", ".join(n for _, n in bad)))
sys.exit(1 if bad else 0)
