"""The in-between: a generated page that looks like a long exposure.

WHAT IT IMITATES. Stop-motion shot with the shutter open while the puppet moves,
so one frame integrates the whole path between two poses. What sells that look is
not blur — it is that the blur is UNEVEN. The feet, which barely travelled, come
out nearly sharp; the arms, which swung furthest, smear away to nothing.

That gradient is why this can be done honestly in a stroke document. Sample the
motion between two pages at N steps and draw every step faintly: a point that
hardly moves lays all N copies on top of each other and stays crisp; a point that
travels far spreads them along its path and goes soft. Nobody authors the
falloff. It is what integrating a motion MEANS, and it falls out of the
arithmetic — which is the property this suite pins, because it is the one that
would be quietly lost if somebody "optimised" the sampling later.

IT IS ORDINARY STROKE DATA. No new field, no raster layer, nothing the player
must learn: opacity already rides inside each point's rgba() and the player
already honours it. So the generated page posts and replays like any other, and
this suite proves that end to end rather than asserting it.

THE POINT BUDGET IS THE HAZARD. Multiplying a page by 27 is exactly how a
feature makes a drawing unpostable — the server refuses a frame over
MAX_POINTS_PER_FRAME (20,000), and it would refuse it at the moment the user
tries to share, having given no earlier warning. N adapts to the page instead of
being a constant, and there are assertions here for both ends of that.

IT REFUSES RATHER THAN GUESSES. Interpolation needs the two pages to correspond
— same strokes, moved — which is what Duplicate-then-drag produces. Two freehand
redraws have nothing to pair, and inventing a pairing would produce a mess that
looks like a bug in the tool rather than a limit of the idea.
"""
import os
import re
import sys

BASE = os.environ.get("SKRIBL_BASE", "http://127.0.0.1:5001")

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("SKIP: playwright is not installed")
    sys.exit(0)

results = []


def check(name, ok, detail=""):
    results.append((bool(ok), name))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  — {detail}" if detail else ""))


# Two corresponding poses, built by writing the arrays directly. Drawing them by
# mouse would be more realistic and less honest: what matters here is that the
# two pages CORRESPOND, and constructing them makes that explicit rather than
# hoping two mouse gestures happened to produce the same structure.
POSES = """(spread) => {
  // one 'limb' of 3 points, plus a 'foot' of 3 that barely moves
  const mk = (armY, footY) => ({
    strokes: [
      { x: 100, y: 100,    color: '#ffffff', size: 6, t: 0, erase: false, start: true },
      { x: 150, y: armY,   color: '#ffffff', size: 6, t: 1, erase: false },
      { x: 200, y: armY,   color: '#ffffff', size: 6, t: 2, erase: false },
      { x: 100, y: 300,    color: '#ffffff', size: 6, t: 3, erase: false, start: true },
      { x: 120, y: footY,  color: '#ffffff', size: 6, t: 4, erase: false },
      { x: 140, y: footY,  color: '#ffffff', size: 6, t: 5, erase: false }
    ],
    strokeGroups: [3, 3], hold: 1
  });
  frames.length = 0;
  frames.push(mk(200, 320));            // arm low,  foot at 320
  frames.push(mk(200 - spread, 322));   // arm HIGH, foot moved 2px
  idx = 0; actionLog.length = 0; redoStack.length = 0;
  buildStrip(); render();
}"""

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1100, "height": 900})
    errs = []
    page.on("pageerror", lambda e: errs.append(str(e)))
    page.goto(BASE + "/flip", wait_until="load")
    page.wait_for_timeout(1500)

    print("IN-BETWEEN — it generates a page between two poses")
    check("Flip booted", page.evaluate("() => !!(window.__skriblBoot && window.__skriblBoot.flip)"),
          "; ".join(errs[:2]))
    page.evaluate(POSES, 150)
    page.evaluate("() => addTween()")
    page.wait_for_timeout(400)
    check("a page was inserted BETWEEN the two poses",
          page.evaluate("() => frames.length") == 3
          and page.evaluate("() => idx") == 1,
          f"{page.evaluate('() => frames.length')} pages, at index "
          f"{page.evaluate('() => idx')}")
    check("...and the two poses are untouched either side of it",
          page.evaluate("() => frames[0].strokes.length") == 6
          and page.evaluate("() => frames[2].strokes.length") == 6,
          "an in-between must not edit what it interpolates")

    tw = page.evaluate("() => frames[1]")
    check("the generated page is made of ordinary strokes",
          len(tw["strokes"]) > 6 and len(tw["strokeGroups"]) > 2,
          f"{len(tw['strokes'])} points in {len(tw['strokeGroups'])} groups")
    check("strokeGroups accounts for every point",
          len(tw["strokes"]) == sum(tw["strokeGroups"]),
          f"{len(tw['strokes'])} vs {sum(tw['strokeGroups'])} — the share-blocking bug")
    check("every sample carries exactly one start flag",
          sum(1 for q in tw["strokes"] if q.get("start")) == len(tw["strokeGroups"]),
          f"{sum(1 for q in tw['strokes'] if q.get('start'))} starts for "
          f"{len(tw['strokeGroups'])} groups — a start partway through a run is "
          f"the shape the server rejects")
    # Asserted on the ALPHA, not on the string form. This checked for "rgba" in
    # the colour until the fade moved to an 8-digit hex for the render cost —
    # the intent (the samples are faded) never changed, only the spelling. A
    # test that pins a spelling fails for the wrong reason and teaches nothing.
    def _alpha(c):
        c = str(c or "")
        if c.startswith("#") and len(c) == 9:
            return int(c[7:9], 16) / 255
        m = re.search(r"rgba\([^)]*,\s*([\d.]+)\s*\)", c)
        return float(m.group(1)) if m else 1.0
    faded = [_alpha(q.get("color")) for q in tw["strokes"]]
    check("the samples are faded, not solid",
          faded and all(0 < a < 0.5 for a in faded),
          f"alphas {sorted(set(round(a, 3) for a in faded))[:4]} — solid samples "
          f"would read as stacked copies, not an exposure")

    print("\nIN-BETWEEN — it has to be cheap enough to PLAY")
    # REPORTED FROM A PHONE: "it takes 2 seconds to play 3 frames". paintStatic
    # gives every translucent stroke its own offscreen layer — clear a full
    # canvas, redraw, composite back — to stop a see-through stroke beading at
    # its own overlaps. An exposure is 27 samples of every stroke, so a six-limb
    # figure is 162 translucent strokes and ~486 full-canvas ops PER FRAME:
    # measured at 221 ms against a 12 fps budget of 83 ms. The render blocks the
    # timer, so the PREVIOUS frame sits on screen while it works, which is what
    # the pauses were.
    #
    # The fade is written as an 8-digit hex rather than rgba() because both
    # renderers decide whether to layer by matching the rgba() FUNCTION form —
    # alphaOf here, parseStrokeAlpha in app.js, which is also the PLAYER's
    # renderer — and neither matches a hex. Canvas honours it and accumulates
    # it either way. 221 ms -> 5.8 ms with no new field and nothing for the
    # player to learn.
    #
    # THIS ASSERTION IS THE ONE THAT KEEPS IT. Teaching alphaOf to understand
    # hex would make exposures slow again — not broken, just slow, which is
    # exactly the kind of regression that ships. A cost budget catches it; an
    # assertion about the colour string would not, because the string could stay
    # the same while the heuristic around it changed.
    ms = page.evaluate("""() => {
      go(1);
      const t0 = performance.now();
      for (let k = 0; k < 10; k++) render();
      return (performance.now() - t0) / 10;
    }""")
    budget = 1000 / 12
    check("an in-between renders well inside one frame at 12 fps",
          ms < budget / 2,
          f"{ms:.1f} ms against a {budget:.0f} ms frame — layered it was 221 ms, "
          f"and the stall showed on the page BEFORE it because the render blocks "
          f"the play timer")
    # AND THE PAGES ALREADY SAVED IN PEOPLE'S DRAFTS. Writing the fade as hex
    # fixed the GENERATOR, which does nothing for an in-between made before that
    # change — it carries rgba() in the draft and still costs 218 ms. Reported a
    # second time from the phone, after the first fix had shipped: "it still
    # pauses on the blurred slides". paintStatic now refuses to layer a frame
    # holding more translucent strokes than a frame budget can pay for, which
    # covers old pages, hand-edited ones, and anything else heavy.
    old_ms = page.evaluate("""() => {
      const f = frames[1];
      for (const q of f.strokes) {
        const m = /^#([0-9a-f]{6})([0-9a-f]{2})$/i.exec(q.color || '');
        if (m) { const n = parseInt(m[1], 16), a = parseInt(m[2], 16) / 255;
          q.color = 'rgba(' + ((n>>16)&255) + ', ' + ((n>>8)&255) + ', '
                  + (n&255) + ', ' + a.toFixed(3) + ')'; }
      }
      go(1);
      const t0 = performance.now();
      for (let k = 0; k < 10; k++) render();
      return (performance.now() - t0) / 10;
    }""")
    check("an in-between saved in the OLD rgba form renders fast too",
          old_ms < budget / 2,
          f"{old_ms:.1f} ms — fixing only the generator leaves every page already "
          f"in somebody's draft broken, which is how this got reported twice")
    check("...but a hand-drawn translucent frame still gets its layers",
          page.evaluate("""() => {
            const st = [], g = [];
            for (let k = 0; k < 6; k++) {
              st.push({x:100+k*40, y:100, color:'rgba(255,255,255,0.35)', size:10,
                       t:k, erase:false, start:true});
              st.push({x:120+k*40, y:300, color:'rgba(255,255,255,0.35)', size:10,
                       t:k+1, erase:false});
              g.push(2);
            }
            return layerableCount(st) <= LAYER_BUDGET;
          }"""),
          "the guard is a cost ceiling, not a ban — six see-through strokes must "
          "still composite properly or the guard has broken ordinary painting")

    page.evaluate(POSES, 150)
    page.evaluate("() => addTween()")
    page.wait_for_timeout(400)
    form = page.evaluate("() => frames[1].strokes[0].color")
    check("...because the fade is an 8-digit hex, not rgba()",
          isinstance(form, str) and form.startswith("#") and len(form) == 9,
          f"{form!r} — rgba() would send every sample through its own "
          f"full-canvas layer, in the editor AND in the player")

    print("\nIN-BETWEEN — the blur is UNEVEN, which is the whole effect")
    # THE PROPERTY THAT MATTERS. The arm travels 150px and the foot 2px, so the
    # arm's samples must spread and the foot's must pile up. If a future change
    # made sampling uniform in SPACE rather than in TIME, or clamped the spread,
    # this is what would catch it — and the picture would silently stop looking
    # like a long exposure while every other assertion here still passed.
    spread = page.evaluate("""() => {
      const f = frames[1];
      const arm = [], foot = [];
      let at = 0;
      for (let g = 0; g < f.strokeGroups.length; g++) {
        const n = f.strokeGroups[g];
        // group 0 of each sample is the arm, group 1 is the foot
        (g % 2 === 0 ? arm : foot).push(f.strokes[at + 2].y);
        at += n;
      }
      const rng = a => Math.max(...a) - Math.min(...a);
      return { arm: rng(arm), foot: rng(foot) };
    }""")
    check("the part that moved FAR is spread across the exposure",
          spread["arm"] > 100, f"arm tip spans {spread['arm']:.0f}px")
    check("...and the part that barely moved stays piled up (nearly sharp)",
          spread["foot"] < 6, f"foot spans {spread['foot']:.0f}px")
    check("the ratio is the falloff, and nobody authored it",
          spread["arm"] > spread["foot"] * 20,
          f"{spread['arm']:.0f}px against {spread['foot']:.0f}px — this is what "
          f"makes it read as a long exposure rather than a smudge")

    print("\nIN-BETWEEN — a HAND-REDRAWN pose (v255)")
    # THE CASE THE FEATURE WAS MOST WANTED FOR AND USED TO REFUSE. Until v255
    # the two pages had to be structurally identical -- same strokes AND the same
    # number of points in each -- which is what Duplicate-then-drag produces.
    # Drawing the next pose by hand is what frame-by-frame animation IS, and a
    # redraw lands a different vertex count every time, so the tool refused the
    # workflow it exists to serve. A stroke is a PATH: resampled along its own
    # arc length it keeps its shape at any vertex count, so the two poses
    # correspond and the exposure arithmetic runs unchanged.
    page.evaluate("""() => {
      const arc = (cx, n, r) => { const o = [];
        for (let i = 0; i <= n; i++) { const a = i * 2 * Math.PI / n;
          o.push({ x: cx + r*Math.cos(a), y: 200 + r*Math.sin(a),
                   color: '#ffffff', size: 6, t: i, erase: false, start: i === 0 }); }
        return o; };
      frames.length = 0;
      const A = arc(150, 37, 40), B = arc(420, 31, 40);
      frames.push({ strokes: A, strokeGroups: [A.length], hold: 1 });
      frames.push({ strokes: B, strokeGroups: [B.length], hold: 1 });
      idx = 0; actionLog.length = 0; redoStack.length = 0; buildStrip(); render();
    }""")
    _before = page.evaluate("() => [frames[0].strokeGroups.slice(), frames[1].strokeGroups.slice()]")
    page.evaluate("() => addTween()")
    page.wait_for_timeout(400)
    _hand = page.evaluate("""() => ({
        pages: frames.length,
        mid: frames[1] ? frames[1].strokes.length : 0,
        poseA: frames[0].strokeGroups.slice(),
        poseB: frames[2] ? frames[2].strokeGroups.slice() : null,
        sums: frames[1] ? frames[1].strokeGroups.reduce((a,b)=>a+b,0) === frames[1].strokes.length : false,
        starts: frames[1] ? frames[1].strokes.filter(p=>p.start).length === frames[1].strokeGroups.length : false })""")
    check("two HAND-DRAWN poses with different point counts now interpolate",
          _hand["pages"] == 3 and _hand["mid"] > 0,
          f"{_before[0]} vs {_before[1]} -> {_hand} — a redrawn pose lands a "
          f"different vertex count every time; requiring them to match refused "
          f"the ordinary way people animate")
    check("...and the two source poses are left exactly as they were drawn",
          _hand["poseA"] == _before[0] and _hand["poseB"] == _before[1],
          f"{_hand['poseA']} vs {_before[0]}, {_hand['poseB']} vs {_before[1]} — "
          f"resampling happens on COPIES; undoing the in-between must not leave "
          f"the artist's own pages rewritten underneath them")
    check("...and the generated page is still well-formed",
          _hand["sums"] and _hand["starts"], str(_hand))

    # A single-point run is an ordinary thing to have on a page, and it has no
    # arc length to walk. It is paired here against a REAL run in the other
    # pose, which is the case that can actually go wrong: n is then the other
    # run's count, and resampling must return that many copies rather than the
    # one point it started with. Written first with a dot on BOTH sides, where
    # n is 1 either way -- so returning the run unchanged was indistinguishable
    # from resampling it, and the assertion could not fail.
    page.evaluate("""() => {
      frames.length = 0;
      frames.push({ strokes: [{x:100,y:100,color:'#ffffff',size:9,t:0,erase:false,start:true}],
                    strokeGroups: [1], hold: 1 });
      frames.push({ strokes: [{x:300,y:200,color:'#ffffff',size:9,t:0,erase:false,start:true},
                              {x:340,y:230,color:'#ffffff',size:9,t:1,erase:false},
                              {x:380,y:200,color:'#ffffff',size:9,t:2,erase:false}],
                    strokeGroups: [3], hold: 1 });
      idx = 0; buildStrip(); render();
    }""")
    page.evaluate("() => addTween()")
    page.wait_for_timeout(350)
    _dot = page.evaluate("""() => { const f = frames[1]; if (!f) return { pages: frames.length };
        return { pages: frames.length, pts: f.strokes.length,
                 runs: [...new Set(f.strokeGroups)],
                 sums: f.strokeGroups.reduce((a,b)=>a+b,0) === f.strokes.length,
                 starts: f.strokes.filter(p=>p.start).length === f.strokeGroups.length }; }""")
    check("a dot paired against a real run resamples UP to that run's count",
          _dot.get("pages") == 3 and _dot.get("runs") == [3],
          f"{_dot} — the dot has no arc length to walk, so it must be emitted as "
          f"n copies; returning it unchanged leaves the two poses mismatched, "
          f"which is the exact bug this change is about")
    check("...and the page it produces is still well-formed",
          bool(_dot.get("sums")) and bool(_dot.get("starts")), str(_dot))

    print("\nIN-BETWEEN — it refuses rather than guessing")
    # WHAT IS STILL DECLINED, and it is now the ONLY thing declined: pages with
    # a different NUMBER of strokes. Pairing three strokes against four means
    # choosing which one has no partner, and that guess would produce a mess
    # that reads as a bug in the tool rather than a limit of the idea.
    page.evaluate("""() => {
      frames.length = 0;
      frames.push({ strokes: [{x:10,y:10,color:'#fff',size:6,t:0,erase:false,start:true},
                              {x:90,y:90,color:'#fff',size:6,t:1,erase:false}],
                    strokeGroups: [2], hold: 1 });
      frames.push({ strokes: [{x:10,y:10,color:'#fff',size:6,t:0,erase:false,start:true},
                              {x:50,y:50,color:'#fff',size:6,t:1,erase:false},
                              {x:10,y:80,color:'#fff',size:6,t:2,erase:false,start:true},
                              {x:90,y:90,color:'#fff',size:6,t:3,erase:false}],
                    strokeGroups: [2, 2], hold: 1 });
      idx = 0; buildStrip(); render();
    }""")
    page.evaluate("() => addTween()")
    page.wait_for_timeout(300)
    check("pages with a different NUMBER of strokes produce no page",
          page.evaluate("() => frames.length") == 2,
          "inventing a pairing would produce a mess that reads as a bug in the "
          "tool rather than a limit of the idea")
    _msg = page.evaluate("() => (document.getElementById('flipChip')||{}).textContent") or ""
    check("...and the refusal says what is needed, with the two counts",
          "number of strokes" in _msg.lower() and "1" in _msg and "2" in _msg,
          f"{_msg!r} — 'the same strokes on both' did not say WHICH of the two "
          f"things it meant, and after v255 only one of them is still required")

    # THE HELP HAS TO AGREE WITH THE TOOL. It said "It needs the same strokes on
    # both pages, so duplicate and move rather than redrawing from scratch" --
    # advice that was correct until v255 and is now the opposite of true. A wrong
    # answer in the help is worse than no answer: it tells someone the workflow
    # they want is unsupported when it is the one that just started working.
    _help = page.evaluate("""() => {
      const tips = [...document.querySelectorAll('.help-tip')];
      const t = tips.find(e => (e.querySelector('.help-pill')||{}).textContent === 'In-between');
      return t ? t.textContent.replace(/\\s+/g, ' ') : null; }""")
    check("the help describes the in-between's ACTUAL requirement",
          _help and "number" in _help.lower() and "same strokes on both" not in _help,
          f"{(_help or '')[-190:]!r} — the old text told people to duplicate "
          f"rather than redraw, which is exactly the workflow v255 unblocked")
    check("...and it still says redrawing the pose is fine",
          _help and "redraw" in _help.lower(), (_help or "")[-190:])

    page.evaluate(POSES, 150)
    page.evaluate("() => go(1)")          # last page: nothing to interpolate TO
    page.evaluate("() => addTween()")
    page.wait_for_timeout(300)
    check("on the last page it explains there is no next pose",
          page.evaluate("() => frames.length") == 2
          and "BETWEEN" in (page.evaluate(
              "() => (document.getElementById('flipChip')||{}).textContent") or ""),
          page.evaluate("() => (document.getElementById('flipChip')||{}).textContent"))

    print("\nIN-BETWEEN — the point budget, at both ends")
    # A page heavy enough that 26 samples would blow the server's 20,000 cap.
    page.evaluate("""() => {
      const pts = [];
      for (let i = 0; i < 900; i++)
        pts.push({ x: 100 + i * 0.5, y: 100 + (i % 40), color: '#ffffff',
                   size: 6, t: i, erase: false, start: i === 0 });
      const mk = dy => ({ strokes: pts.map(q => Object.assign({}, q, {y: q.y + dy})),
                          strokeGroups: [900], hold: 1 });
      frames.length = 0; frames.push(mk(0)); frames.push(mk(120));
      idx = 0; buildStrip(); render();
    }""")
    page.evaluate("() => addTween()")
    page.wait_for_timeout(500)
    made = page.evaluate("() => frames.length === 3 ? frames[1].strokes.length : 0")
    check("a heavy page still gets an in-between",
          made > 0, "refusing outright would be worse than a coarser exposure")
    check("...and it stays under the server's 20,000-point cap",
          0 < made < 20000,
          f"{made} points — 27 samples of this page would be {900*27}, which the "
          f"server would refuse at the moment the user tried to share")

    print("\nIN-BETWEEN — and the server takes it")
    page.evaluate(POSES, 150)
    page.evaluate("() => addTween()")
    page.wait_for_timeout(400)
    posted = page.evaluate("""async (base) => {
      const frs = frames.map(f => ({ strokes: f.strokes, strokeGroups: f.strokeGroups,
                                     background: '#0d0f14' }));
      const r = await fetch(base + '/api/skribls', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: 'tween', kind: 'flip', frames: frs, fps: 12 }) });
      let body = null; try { body = await r.json(); } catch (e) {}
      return { ok: r.ok, status: r.status, body: body };
    }""", BASE)
    check("a document containing an in-between POSTS",
          posted.get("ok"), f"{posted.get('status')} {str(posted.get('body'))[:160]}")
    if posted.get("ok"):
        url = (posted["body"] or {}).get("url") or "/s/" + ((posted["body"] or {}).get("slug") or "")
        viewer = browser.new_page(viewport={"width": 900, "height": 800})
        verrs = []
        viewer.on("pageerror", lambda e: verrs.append(str(e)))
        viewer.goto(BASE + url, wait_until="load")
        viewer.wait_for_timeout(2400)
        check("...and the player renders it, having learnt nothing",
              not verrs, "; ".join(verrs[:2]))
        viewer.close()

        # A FLIP FRAME IS STATIC, SO THE PLAYER MUST NOT REPAINT IT EVERY RAF.
        #
        # requestAnimationFrame runs at the display's rate; a flipbook advances
        # at fps. At 12fps on a 60Hz screen that is four wasted repaints out of
        # every five, and they were invisible for as long as every page cost the
        # same -- a key page paints in 0.4ms. A blurred in-between of the same
        # drawing paints in 41ms, because it is 26 samples of every stroke at
        # several passes each, and five of those is 205ms of work for an 83ms
        # slot. Reported as "it slows way down when it shows the in-between
        # slides", and measured here at 289 full-canvas repaints in three
        # seconds where 36 frames actually changed.
        #
        # Counted through ctx.clearRect, which is what starts every frame paint.
        # The compositor issues more than one per frame, so this is not a frame
        # count -- it is a WASTE count, and the two differ by a constant. The
        # bound is deliberately loose: the fix took it to 73 and the bug sat at
        # 289, so anything under about four times the real frame changes
        # separates them without pinning the constant.
        _lp = browser.new_page(viewport={"width": 900, "height": 800})
        _lerrs = []
        _lp.on("pageerror", lambda e: _lerrs.append(str(e)))
        _lp.goto(BASE + url, wait_until="load")
        _lp.wait_for_timeout(1800)
        _lp.evaluate("""() => { window.__t = [];
            const c = document.querySelector('canvas'); if (!c) return;
            const g = c.getContext('2d'); const oc = g.clearRect.bind(g);
            g.clearRect = function () { window.__t.push(performance.now());
                                        return oc.apply(g, arguments); }; }""")
        _lp.click("#playerLoopBtn")
        _lp.wait_for_timeout(150)
        _lp.click("#playerPlayBtn")
        _lp.wait_for_timeout(3000)
        _paints = _lp.evaluate("() => (window.__t || []).length")
        _spans = _lp.evaluate("""() => { const t = window.__t || []; const g = [];
            for (let i = 1; i < t.length; i++) g.push(t[i] - t[i - 1]);
            return g.filter(x => x > 20).sort((a, b) => a - b); }""")
        _med = round(_spans[len(_spans) // 2], 1) if _spans else None
        check("the looping player actually ran",
              _paints > 20 and _med is not None,
              f"{_paints} paints, median gap {_med} — with no playback the "
              f"bound below passes by doing nothing")
        check("the player does NOT repaint a flip frame it has already drawn",
              _paints < 145,
              f"{_paints} full-canvas repaints in 3s of a 3-page 12fps loop — "
              f"about 36 frames actually change; this measured 289 before the "
              f"memo and 73 after")
        check("...and the frames land at the flipbook's rate, not the display's",
              _med is not None and 60 <= _med <= 120,
              f"median gap {_med}ms — 12fps is 83ms; a gap near 16ms means it "
              f"is painting once per display refresh")
        check("no error from the looping player", not _lerrs, "; ".join(_lerrs[:2]))
        _lp.close()

    print("\nIN-BETWEEN — the exposure is budgeted against the FRAME RATE too")
    # TWEEN_POINT_CAP is the SERVER's limit: what a frame may contain. It says
    # nothing about how long that frame takes to DRAW, and the drawing happens
    # once per appearance inside whatever slot the document's rate leaves.
    #
    # Reported from a real 46-page flip at fps 24 where 22 pages were
    # in-betweens: each was 11,826 points -- 27 samples of a 438-point drawing,
    # exactly what the server cap allows -- and painted in 50ms against a 41.7ms
    # budget. Every other page overran and the flip dragged. The same document
    # at 12fps is comfortable, so this was never the in-between alone but the
    # in-between AND the rate it was asked to play at.
    _fp = page.evaluate("""(per) => {
        const out = {};
        for (const f of [8, 12, 24, 30, 60])
          out[f] = { cap: tweenRenderCap(f), plan: tweenPlan(per, 19, f) };
        return out; }""", 438)
    _n = lambda k: (_fp[k]["plan"] or {}).get("n")
    check("at 12fps and below the exposure is exactly what it always was",
          _fp["8"]["cap"] == _fp["12"]["cap"] and _n("12") is not None
          and _n("12") == _n("8"),
          f"{ {k: v['plan'] and v['plan']['n'] for k, v in _fp.items()} } — the "
          f"server cap binds there, so every in-between already made at 12fps "
          f"keeps the sample count it was generated with")
    # Null-safe throughout: the mutation these exist to catch -- a render ceiling
    # used as the POSTABILITY test -- returns null at 60fps, and indexing that
    # crashed the suite instead of naming the failure.
    check("above 12fps the allowance falls with the slot",
          all(_n(k) is not None for k in ("12", "24", "30", "60"))
          and _n("24") < _n("12") and _n("30") < _n("24") and _n("60") < _n("30"),
          f"{ {k: v['plan'] and v['plan']['n'] for k, v in _fp.items()} } — 24fps "
          f"has half the time 12 does and gets about half the samples")
    # A RENDER HEURISTIC MUST NOT COST A FEATURE. Turning "here is a coarser
    # exposure" into "this page is too heavy for an in-between" would trade the
    # in-between away for a frame rate, so below the floor the render ceiling
    # simply stops applying.
    check("the render budget never refuses a page the server would accept",
          all(_fp[k]["plan"] is not None for k in _fp),
          f"{ {k: v['plan'] for k, v in _fp.items()} } — a null here is a page "
          f"that could be posted and was declined for speed")
    # NULL-SAFE, because the mutation this is here to catch produces nulls: a
    # render ceiling applied as the postability test refuses 60fps outright, and
    # indexing into that null crashed the suite instead of naming the failure.
    check("...and never plans below the floor",
          all(v["plan"] and v["plan"]["n"] + 1 >= 6 for v in _fp.values()),
          f"{ {k: (v['plan'] and v['plan']['n'] + 1) for k, v in _fp.items()} } "
          f"samples — a None is a page that was declined outright")
    # AND IT REACHES THE GENERATED PAGE, not just the plan.
    _gen = page.evaluate("""() => {
        const mk = () => { const s = [], g = [];
          for (let r = 0; r < 6; r++) { const run = [];
            for (let k = 0; k < 40; k++) run.push({x: 60 + k * 8 + r * 3, y: 80 + r * 40,
              color: '#ffffff', size: 5, t: k, erase: false, start: k === 0});
            s.push(...run); g.push(run.length); }
          return { strokes: s, strokeGroups: g, hold: 1 }; };
        const out = {};
        for (const f of [12, 24]) {
          frames.length = 0;
          const a = mk(), b = mk();
          b.strokes = b.strokes.map(q => ({...q, x: q.x + 200}));
          frames.push(a, b); idx = 0; fps = f;
          addTween();
          out[f] = frames[1].strokes.length;
        }
        return out; }""")
    check("a page generated at 24fps really is lighter than the same one at 12",
          _gen["24"] < _gen["12"] * 0.75,
          f"{_gen['12']} points at 12fps vs {_gen['24']} at 24 — the plan has to "
          f"reach buildTween, not just be computable")

    print("\nREBUILD IN-BETWEENS — bringing already-baked pages to the current rate")
    # v260 made the sample count depend on fps, and that only reaches pages made
    # AFTER it. The reported file had 22 in-betweens already baked at 27 samples,
    # which is the reason it dragged. Deleting and re-adding each by hand is the
    # fix nobody should have to perform 22 times.
    #
    # NOTHING MARKS A PAGE AS GENERATED, so this recognises one -- and being
    # wrong means overwriting a drawing. Three things must agree, and the checks
    # below are mostly about the ones that must NOT be touched.
    _rb = page.evaluate("""() => {
        const mkKey = (dx) => { const s = [], g = [];
          for (let r = 0; r < 4; r++) { const run = [];
            for (let k = 0; k < 30; k++) run.push({x: 60 + k * 7 + dx, y: 70 + r * 40,
              color: '#ffffff', size: 5, t: k, erase: false, start: k === 0});
            s.push(...run); g.push(run.length); }
          return { strokes: s, strokeGroups: g }; };
        // Three key poses at 12fps with an in-between between each pair, then
        // the document is moved to 24 and rebuilt -- exactly the reported shape.
        frames.length = 0;
        frames.push(mkKey(0), mkKey(120), mkKey(240));
        idx = 0; fps = 12; buildStrip();
        addTween();                       // between 0 and 1
        idx = 2; addTween();              // between the next pair
        const heavy = frames.map(f => f.strokes.length);
        const keyBefore = [frames[0], frames[2], frames[4]].map(f => f.strokes.length);
        fps = 24;
        const found = [];
        for (let i = 1; i < frames.length - 1; i++) if (tweenLooksGenerated(i)) found.push(i);
        rebuildTweens();
        const light = frames.map(f => f.strokes.length);
        const keyAfter = [frames[0], frames[2], frames[4]].map(f => f.strokes.length);
        const firstChip = (document.getElementById('flipChip') || {}).textContent;
        rebuildTweens();
        const twice = frames.map(f => f.strokes.length);
        return { pages: frames.length, found: found, heavy: heavy, light: light,
                 keyBefore: keyBefore, keyAfter: keyAfter,
                 idempotent: light.every((v, i) => v === twice[i]),
                 firstChip: firstChip,
                 secondChip: (document.getElementById('flipChip') || {}).textContent }; }""")
    check("the fixture has in-betweens to find",
          len(_rb["found"]) == 2 and _rb["pages"] == 5,
          f"{_rb} — with none found every check below passes by doing nothing")
    check("rebuilding at a higher rate makes the in-betweens lighter",
          all(_rb["light"][i] < _rb["heavy"][i] for i in _rb["found"]),
          f"{_rb['heavy']} -> {_rb['light']} at pages {_rb['found']}")
    check("...and does not touch a single hand-drawn page",
          _rb["keyAfter"] == _rb["keyBefore"],
          f"{_rb['keyBefore']} -> {_rb['keyAfter']} — the detector's whole job is "
          f"to be sure, because being wrong here overwrites a drawing")
    check("running it twice changes nothing the second time",
          _rb["idempotent"] and "already right" in (_rb["secondChip"] or ""),
          f"first {_rb['firstChip']!r}, second {_rb['secondChip']!r}")
    # THE DETECTOR, ONE HALF AT A TIME. A single fake page cannot test both
    # rules: the first version built a drawing with the SAME run count as its
    # source, so `copies` came out at 1 and the multiple test rejected it before
    # the colour test was ever consulted -- and removing the colour test left
    # the suite green. Each rule now gets a page only IT can reject.
    _safe = page.evaluate("""() => {
        const src = frames[0];
        const runs = src.strokeGroups.length;
        // (a) shaped exactly like an exposure -- a clean multiple of the source's
        //     run list -- but DRAWN, so its colours are ordinary. Only the colour
        //     rule can reject this one.
        const drawnLikeExposure = { strokes: [], strokeGroups: [] };
        for (let c = 0; c < 8; c++) for (const n of src.strokeGroups) {
          for (let k = 0; k < n; k++) drawnLikeExposure.strokes.push({x: 40 + k, y: 60 + c,
            color: '#26b0ff', size: 3, t: k, erase: false, start: k === 0});
          drawnLikeExposure.strokeGroups.push(n); }
        // (b) 8-digit hex throughout, but NOT a multiple of the source's run
        //     list. Only the multiple rule can reject this one.
        const hexButWrongShape = { strokes: [], strokeGroups: [] };
        for (let r = 0; r < runs * 8 + 1; r++) {
          for (let k = 0; k < 5; k++) hexButWrongShape.strokes.push({x: 40 + k, y: 60 + r,
            color: '#26b0ff80', size: 3, t: k, erase: false, start: k === 0});
          hexButWrongShape.strokeGroups.push(5); }
        const keep = frames[1];
        frames[1] = drawnLikeExposure; const a = tweenLooksGenerated(1);
        frames[1] = hexButWrongShape;  const b = tweenLooksGenerated(1);
        frames[1] = keep;
        return { drawnLikeExposure: a, hexButWrongShape: b,
                 aRuns: drawnLikeExposure.strokeGroups.length,
                 bRuns: hexButWrongShape.strokeGroups.length, srcRuns: runs }; }""")
    check("a DRAWING shaped exactly like an exposure is still rejected",
          _safe["drawnLikeExposure"] is False
          and _safe["aRuns"] % _safe["srcRuns"] == 0,
          f"{_safe} — its run count is a clean multiple, so only the colour rule "
          f"stands between this page and being overwritten")
    check("...and hex ink alone is not enough either",
          _safe["hexButWrongShape"] is False
          and _safe["bRuns"] % _safe["srcRuns"] != 0,
          f"{_safe} — every point is 8-digit hex, so only the run-multiple rule "
          f"rejects it; a blurred drawing is exactly this shape")

    print("\nPAGE BAR — the counter earns its width")
    # "Page 21 / 43" cost 69px in a nowrap bar whose contents already measured
    # 369px inside 340 at 360px wide — the Delete button was clipped off the end
    # before the in-between button existed. This is that fix, pinned.
    page.evaluate("""() => { frames.length = 0;
      for (let i = 0; i < 9; i++) frames.push({strokes:[],strokeGroups:[],hold:1});
      idx = 3; buildStrip(); render(); }""")
    page.wait_for_timeout(300)
    lbl = page.evaluate("""() => { const e = document.getElementById('pbWho');
      return { txt: e.textContent.trim(), aria: e.getAttribute('aria-label'),
               w: Math.round(e.getBoundingClientRect().width) }; }""")
    check("the counter is terse to look at", lbl["txt"] == "4/9", f"{lbl['txt']!r}")
    check("...and complete to listen to",
          lbl["aria"] == "Page 4 of 9",
          f"{lbl['aria']!r} — an abbreviation may shorten the LOOK of a control, "
          f"never its accessible name")

    for w in (320, 360, 393):
        page.set_viewport_size({"width": w, "height": 880})
        page.wait_for_timeout(300)
        fit = page.evaluate("""() => { const b = document.getElementById('pagebar');
          return { w: Math.round(b.getBoundingClientRect().width),
                   sw: Math.round(b.scrollWidth) }; }""")
        check(f"the page bar fits at {w}px",
              fit["sw"] <= fit["w"],
              f"{fit['sw']}px of content in {fit['w']}px — nowrap, so the overflow "
              f"is a clipped button rather than a second row")

    # ------------------------------------------------------------------
    # v237 — the in-between is blurred, and the blur is DRAWN.
    #
    # The point of interest is that this cost points instead of a format
    # contract. The load-bearing assertion in this block is the last one: a
    # blurred in-between must not carry a single field the source strokes did
    # not already have, because that is what lets a Skribl made here open in a
    # player that predates the feature.
    # ------------------------------------------------------------------
    print("\nBLUR — a drawn falloff, not a render attribute")
    blur = page.evaluate("""() => {
      const mk = (dy) => {
        const pts = [];
        for (let i = 0; i <= 40; i++)
          pts.push({ x: 120 + i * 6, y: 200 + dy, color: '#ffffff', size: 6,
                     t: i * 4, erase: false, start: i === 0 });
        return { strokes: pts, strokeGroups: [pts.length], hold: 1 };
      };
      const a = mk(0), b = mk(120);
      const tw = buildTween(a, b);
      if (!tw) return { built: false };
      const sizes = [...new Set(tw.strokes.map(s => +s.size.toFixed(3)))]
                      .sort((x, y) => x - y);
      const alpha = (c) => parseInt(String(c).slice(7, 9) || 'ff', 16);
      // Keys the tween introduced that the source strokes never had.
      const src = new Set(Object.keys(a.strokes[0]));
      const extra = new Set();
      for (const s of tw.strokes)
        for (const k of Object.keys(s)) if (!src.has(k)) extra.add(k);
      return { built: true, points: tw.strokes.length,
               groups: tw.strokeGroups.length,
               groupSum: tw.strokeGroups.reduce((x, v) => x + v, 0),
               sizes: sizes, base: 6,
               firstSize: +tw.strokes[0].size.toFixed(3),
               lastSize: +tw.strokes[tw.strokes.length - 1].size.toFixed(3),
               firstAlpha: alpha(tw.strokes[0].color),
               lastAlpha: alpha(tw.strokes[tw.strokes.length - 1].color),
               extraKeys: [...extra],
               frameKeys: Object.keys(tw).sort(),
               starts: tw.strokes.filter(s => s.start).length }; }""")

    check("an in-between still builds", blur.get("built"), str(blur)[:120])
    if blur.get("built"):
        check("it is drawn at more than one width — there is a falloff at all",
              len(blur["sizes"]) > 1,
              f"only one width ({blur['sizes']}) — that is the unblurred exposure")
        check("no pass is drawn thinner than the brush itself",
              all(sz >= blur["base"] - 1e-6 for sz in blur["sizes"]),
              str(blur["sizes"]))

        # v238 — the halo is a soft EDGE, not a dilation. This is the assertion
        # this suite was missing: the first blur multiplied the brush by up to
        # 3.4x, which reads as a soft edge on a 6px test stroke and as a 200px
        # cloud on a 60px ball. Everything above passed throughout, because
        # nothing asked how wide the halo got RELATIVE to what was blurred.
        # Motion blur does not fatten an object; it smears it along its travel.
        spread = page.evaluate("""() => {
          const mk = (dy, size) => { const pts = [];
            for (let i = 0; i < 10; i++)
              pts.push({ x: 200 + i * 0.5, y: 200 + dy, color: '#ffffff',
                         size: size, t: i * 3, erase: false, start: i === 0 });
            return { strokes: pts, strokeGroups: [pts.length], hold: 1 }; };
          const out = [];
          for (const size of [8, 30, 60, 120]) {
            const tw = buildTween(mk(0, size), mk(150, size));
            if (!tw) { out.push({ size: size, built: false }); continue; }
            const widest = Math.max(...tw.strokes.map(s => s.size));
            out.push({ size: size, built: true, widest: +widest.toFixed(1),
                       grew: +(widest - size).toFixed(1) });
          }
          return out; }""")
        for _s in spread:
            check(f"a {_s['size']}px brush keeps its shape — the halo is an edge, not a cloud",
                  _s.get("built") and _s["grew"] <= 16.0,
                  f"widest pass {_s.get('widest')} on a {_s['size']}px brush "
                  f"(+{_s.get('grew')}px) — it inflates instead of smearing")
        # v240 — a blur pass must be able to CARRY the ink's colour.
        #
        # Canvas composites through premultiplied 8-bit alpha, so a pass at
        # alpha 2/255 stores round(32 * 2/255) = 0 for #ffb020's blue: the blue
        # is gone before compositing starts and an orange ball grows a RED
        # halo. Measured on the canvas — a plain ball reads (255,176,32), the
        # same ball blurred peaked at (240,134,2).
        #
        # Nothing above this asked what COLOUR the blur came out. Every
        # assertion in this block would have passed while the halo was the
        # wrong hue, because they all measure geometry and alpha.
        hue = page.evaluate("""() => {
          const mk = (dy, col) => { const p = [];
            for (let i = 0; i < 10; i++)
              p.push({ x: 250 + i*2, y: 200 + dy, color: col, size: 56,
                       t: i*3, erase: false, start: i === 0 });
            return { strokes: p, strokeGroups: [p.length], hold: 1 }; };
          const out = {};
          for (const col of ['#ffb020', '#f7f2e8']) {
            const tw = buildTween(mk(0, col), mk(150, col));
            frames = [tw]; idx = 0; render();
            const cv = document.getElementById('pad'), g = cv.getContext('2d');
            const W = cv.width, H = cv.height, d = g.getImageData(0,0,W,H).data;
            // The WORST blue/red ratio over pixels that are clearly ink. The
            // core is barely affected by the defect — it is the halo that
            // loses the channel entirely, so a core-only measurement passes
            // while the smear is visibly red. (It did, on the first draft of
            // this check.)
            let worst = 1e9, lit = 0;
            for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
              const i = (y*W+x)*4, r = d[i], b = d[i+2];
              if (r < 60) continue;
              lit++; const br = b / r; if (br < worst) worst = br;
            }
            out[col] = { worstBR: +worst.toFixed(3), lit: lit,
                         alphas: [...new Set(tw.strokes.map(s => String(s.color).slice(7)))].sort(),
                         dark: frameDarkest(mk(0, col)) };
          }
          return out; }""")

        _o = hue["#ffb020"]; _n = hue["#f7f2e8"]
        check("the smear has ink in it at all",
              _o["lit"] > 4000, f"only {_o['lit']} lit pixels — nothing measured")
        # #ffb020 is B/R = 32/255 = 0.125. Measured 0.069 with the guard and
        # 0.004 without it: the blue is not dimmed, it is gone.
        check("a saturated ink keeps its darkest channel through the blur",
              _o["worstBR"] > 0.04,
              f"worst B/R {_o['worstBR']} against a true 0.125 — the halo has "
              f"eaten the blue and the smear renders red")
        # Anti-vacuity: if the pale ink did not keep several passes, "fewer
        # passes on a saturated ink" would be true for a blur that never runs.
        check("a pale ink still gets a real falloff",
              len(_n["alphas"]) >= 3,
              f"only {len(_n['alphas'])} pass(es) on #f7f2e8 — nothing to shed")
        check("and a saturated ink sheds the passes it cannot colour",
              len(_o["alphas"]) < len(_n["alphas"]),
              f"#ffb020 kept {len(_o['alphas'])} of the pale ink's "
              f"{len(_n['alphas'])} — darkest channel {_o['dark']} vs {_n['dark']}")
        check("no pass is emitted at alpha 1/255, which is wrong for every ink",
              all("01" not in v["alphas"] for v in (_o, _n)),
              f"{_o['alphas']} / {_n['alphas']}")

        check("and the soft edge does not vanish on a fine brush",
              spread[0].get("grew", 0) >= 1.5,
              f"only +{spread[0].get('grew')}px on an 8px brush — no falloff left")
        check("the widest pass is drawn FIRST, so the crisp core lands on top",
              blur["firstSize"] > blur["lastSize"],
              f"first {blur['firstSize']} vs last {blur['lastSize']}")
        check("and the widest pass is the faintest",
              blur["firstAlpha"] < blur["lastAlpha"],
              f"alpha {blur['firstAlpha']} vs {blur['lastAlpha']}")
        # The caps the server enforces. MAX_POINTS_PER_FRAME = 20,000 and
        # MAX_GROUPS_PER_FRAME = 5,000; a feature that multiplies a page by
        # samples AND by passes is exactly how a drawing becomes unpostable.
        check("the blurred frame is within the server's point cap",
              blur["points"] <= 20000, f"{blur['points']} points")
        check("and within its group cap — every pass is its own group",
              blur["groups"] <= 5000, f"{blur['groups']} groups")
        check("the groups still sum to the stroke count exactly",
              blur["groupSum"] == blur["points"],
              f"{blur['groupSum']} vs {blur['points']} — the server refuses this")
        check("every stroke begins exactly once",
              blur["starts"] == blur["groups"],
              f"{blur['starts']} starts for {blur['groups']} groups")
        # THE one that matters: no new field, so an older player can draw it.
        check("the blur added NO field the source strokes did not have",
              blur["extraKeys"] == [],
              f"introduced {blur['extraKeys']} — that is a format change, and "
              f"every player would have to honour it")
        check("and the frame itself is still strokes/strokeGroups/hold",
              blur["frameKeys"] == ["hold", "strokeGroups", "strokes"],
              str(blur["frameKeys"]))

    # ------------------------------------------------------------------
    # v246 — SWEEP the axes the renderer is sensitive to.
    #
    # Both blur defects that reached the user lived on axes nothing varied.
    # Every measurement of this feature used a 6px stroke in white ink:
    #   * the halo was a MULTIPLE of the brush, so a 60px ball inflated into a
    #     204px cloud — invisible at 6px, where 3.4x is a 7px soft edge;
    #   * white ink has equal, high channels, the one case where premultiplied
    #     8-bit alpha cannot shift a hue, so the red halo on saturated ink
    #     could not appear.
    # Eleven assertions passed through both. Asserting a feature works at one
    # input says almost nothing; these are invariants over a grid.
    # ------------------------------------------------------------------
    print("\nSWEEP — size x saturation, the two axes the blur bends on")
    grid = page.evaluate("""() => {
      const SIZES = [6, 12, 24, 48, 96, 160];
      const INKS = ['#f7f2e8', '#ffb020', '#2fa8a0', '#14120f', '#ff0000'];
      const mk = (dy, size, col) => { const p = [];
        for (let i = 0; i < 10; i++)
          p.push({ x: 250 + i*2, y: 180 + dy, color: col, size: size,
                   t: i*3, erase: false, start: i === 0 });
        return { strokes: p, strokeGroups: [p.length], hold: 1 }; };
      const srcKeys = new Set(['x','y','color','size','t','erase','start']);
      const out = [];
      for (const size of SIZES) for (const col of INKS) {
        const a = mk(0, size, col), b = mk(140, size, col);
        const tw = buildTween(a, b);
        if (!tw) { out.push({ size, col, built: false }); continue; }
        const sizes = tw.strokes.map(s => s.size);
        const alphas = [...new Set(tw.strokes.map(s => parseInt(String(s.color).slice(7), 16)))];
        const extra = new Set();
        for (const s of tw.strokes) for (const k of Object.keys(s)) if (!srcKeys.has(k)) extra.add(k);
        // render and read the worst surviving ratio of the ink's darkest channel
        frames = [tw]; idx = 0; render();
        const cv = document.getElementById('pad'), g = cv.getContext('2d');
        const W = cv.width, H = cv.height, d = g.getImageData(0,0,W,H).data;
        const m = /^#(..)(..)(..)$/.exec(col).slice(1).map(h => parseInt(h,16));
        const mx = m.indexOf(Math.max(...m));
        let dk = -1, dkv = 1e9;
        for (let c = 0; c < 3; c++) if (m[c] > 0 && m[c] < dkv) { dkv = m[c]; dk = c; }
        const trueRatio = dk >= 0 ? m[dk] / m[mx] : null;
        let worst = 1e9, lit = 0;
        for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
          const i = (y*W+x)*4;
          if (d[i+mx] < 60) continue;
          lit++;
          if (dk >= 0) { const r = d[i+dk] / d[i+mx]; if (r < worst) worst = r; }
        }
        out.push({ size, col, built: true, lit,
                   widest: +Math.max(...sizes).toFixed(2),
                   thinnest: +Math.min(...sizes).toFixed(2),
                   minAlpha: Math.min(...alphas), passes: alphas.length,
                   points: tw.strokes.length, groups: tw.strokeGroups.length,
                   groupSum: tw.strokeGroups.reduce((x,v) => x+v, 0),
                   extra: [...extra],
                   trueRatio: trueRatio === null ? null : +trueRatio.toFixed(3),
                   worstRatio: (dk >= 0 && worst < 1e9) ? +worst.toFixed(3) : null });
      }
      return out; }""")

    _built = [c for c in grid if c.get("built")]
    check("every point on the grid produced an in-between",
          len(_built) == len(grid) and len(grid) == 30,
          f"{len(_built)} of {len(grid)} built (expected 30 cells)")

    def _bad(pred):
        return [f"{c['size']}px {c['col']}" for c in _built if pred(c)]

    # THE assertion the inflation bug needed: the halo is a soft EDGE, and how
    # wide it is must not scale with the object.
    _fat = _bad(lambda c: c["widest"] - c["size"] > 16.0)
    check("the halo stays a bounded edge at every brush size",
          not _fat,
          "inflated at: " + ", ".join(_fat[:6]) +
          f"  (worst +{max((c['widest']-c['size']) for c in _built):.0f}px)")
    check("and no pass is ever drawn thinner than the brush",
          not _bad(lambda c: c["thinnest"] < c["size"] - 1e-6), "")

    # THE assertion the hue bug needed.
    _hued = [c for c in _built if c["worstRatio"] is not None and c["lit"] > 500]
    check("the sweep actually rendered ink to measure",
          len(_hued) >= 18, f"only {len(_hued)} cells had measurable ink")
    _lost = [f"{c['size']}px {c['col']} ({c['worstRatio']} vs {c['trueRatio']})"
             for c in _hued if c["worstRatio"] < c["trueRatio"] * 0.35]
    check("every ink keeps its darkest channel through the blur",
          not _lost, "channel lost at: " + "; ".join(_lost[:5]))
    check("no cell emits a pass at alpha 1/255, which is wrong for every ink",
          not _bad(lambda c: c["minAlpha"] < 2), "")

    # Format and cap invariants, over the whole grid rather than one sample.
    check("strokeGroups sum to the stroke count in every cell",
          not _bad(lambda c: c["groupSum"] != c["points"]), "")
    check("no cell exceeds the server's point or group caps",
          not _bad(lambda c: c["points"] > 20000 or c["groups"] > 5000),
          f"worst {max(c['points'] for c in _built)} points, "
          f"{max(c['groups'] for c in _built)} groups")
    check("no cell introduces a field the source strokes lacked",
          not _bad(lambda c: c["extra"]), "")

    # The budget planner spends leftover budget on blur, never samples on it:
    # the halo's job is closing the gaps BETWEEN samples, so a coarser exposure
    # with a richer falloff would be strictly worse.
    plans = page.evaluate("""() => ({
        light: tweenPlan(41, 1), mid: tweenPlan(400, 12),
        heavy: tweenPlan(900, 30), grouphog: tweenPlan(300, 150),
        absurd: tweenPlan(2400, 90) })""")
    check("a light page gets the full falloff", plans["light"]["passes"] >= 4,
          str(plans["light"]))
    check("a heavier page sheds passes rather than samples",
          plans["heavy"]["passes"] < plans["light"]["passes"]
          and plans["heavy"]["n"] >= 6,
          f"{plans['heavy']} vs {plans['light']}")
    check("a page of many short strokes is bounded by GROUPS, not points",
          (plans["grouphog"]["n"] + 1) * 150 * plans["grouphog"]["passes"] <= 5000,
          str(plans["grouphog"]))
    check("and a page too heavy for any exposure is refused, not truncated",
          plans["absurd"] is None, str(plans["absurd"]))

    check("no uncaught error across the whole session", not errs, "; ".join(errs[:3]))
    browser.close()

bad = [r for r in results if not r[0]]
print(f"\n{'=' * 62}\n{len(results) - len(bad)}/{len(results)} passed"
      + ("" if not bad else "  FAILURES: " + ", ".join(n for _, n in bad)))
sys.exit(1 if bad else 0)
