"""Motion Smear: a generated page that looks like a long exposure.

THE BUTTON SAID "IN-BETWEEN" UNTIL v295 AND THE EFFECT NEVER WAS ONE. An
in-between, to an animator, is a single intermediate POSE; this integrates
the WHOLE PATH between two poses into one page, deliberately, and every
property pinned below is a property of doing that. Renaming it is the whole
of that change: not one assertion here moved, because nothing about the
effect moved. This file keeps its name, and so does `addtween` -- an
internal name for an algorithm nobody is replacing. The prose below still says
"in-between" throughout: it narrates what was decided when it was decided, and
rewriting it would make the history read as though the name had always been
right. Where a paragraph described something that no longer EXISTS rather than
something since renamed, it has been corrected and says so.

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

THE FADE IS AN 8-DIGIT HEX, AND THAT IS A PERFORMANCE DECISION, NOT A STYLE ONE.
Both renderers decide whether to give a translucent stroke its own offscreen
layer by matching the rgba() FUNCTION form — alphaOf in flip.js,
parseStrokeAlpha in app.js, which is also the PLAYER's renderer — and neither
matches a hex, while canvas accumulates #rrggbbaa either way. An exposure is 27
samples of every stroke, so a six-limb figure was 162 translucent strokes and
~486 full-canvas operations per frame: 221 ms against a 12 fps budget of 83 ms,
versus 5.8 ms as hex. Layering is also simply wrong for this content — it exists
to stop a stroke compounding at its own overlaps, and an exposure IS compounding
overlaps.

So this suite pins the RENDER COST, not the colour string. Teaching alphaOf to
understand hex would make exposures slow again — not broken, just slow, which is
exactly the kind of regression that ships — and a test on the string could stay
green while the heuristic around it changed.

A FIX THAT ONLY APPLIES TO NEW DATA LEAVES EVERY USER WHO ALREADY HIT THE BUG
STILL HITTING IT. That happened three times in this one feature, each time
reported again from the same phone after a fix had shipped. Hence: paintStatic
carries a cost ceiling so pages built BEFORE the hex change paint direct
(218 ms -> 5.1 ms) while a hand-drawn frame with six see-through strokes still
layers — a ceiling, not a ban, and both halves are asserted. A "Rebuild
in-betweens" menu item did the other half, re-running the generator over pages
already built; it was REMOVED in v290 at the owner's call, on the grounds that a
page which should be lighter is re-added rather than rebuilt. The ceiling is
what carries old pages now, and it is the half that is pinned.

TWO CEILINGS, NOT ONE, AND ONLY ONE IS FIXED. The postable limit is a constant
(MAX_POINTS_PER_FRAME, 20,000). The render allowance is 1000/fps, so the same
exposure that is comfortable at 12 fps has half the slot at 24 — which is how a
document already inside the point budget still stalled. The plan fits both and
never drops below TWEEN_MIN_SAMPLES, so the exposure coarsens rather than the
document becoming unshareable.

RECOGNISING A GENERATED PAGE TOOK THREE SIGNALS, because nothing in the format
marked one and a false positive overwrites somebody's drawing: 8-digit hex ink,
neighbours that still interpolate, and a run count that is an exact multiple of
the source's. That heuristic went with Rebuild in v290 and nothing here asserts
it. Since v295 a generated page IS marked, though not in the format: the editor
keeps a recipe beside the frame in a WeakMap, which is what lets the draft store
{k, n, passes} instead of the points. It is deliberately not a field on the
frame — see "the frame itself is still strokes/strokeGroups/hold" below.

NO BUDGET CLOSES A DEVICE GAP, which is why the frame bitmap cache exists.
At 4x CPU throttle one in-between cost ~215 ms against a 41.7 ms slot. The frame
is STATIC, so lib/framebitmap.js captures a heavy page's first paint and every
later visit is one drawImage, on both playback surfaces. Only pages past 1,500
points earn a bitmap, captures happen at the displayed resolution, and past
64 MB — or one failed allocation — frames paint direct: slower, never broken.
The play timer estimates a BLIT for cached frames, because subtracting a
rasterisation cost that can no longer happen made cached loops rush.

NO BLUR, DELIBERATELY. 26 unblurred samples are most of the way to the
photograph and cost nothing, and the faint ribbing reads as a DRAWN in-between,
which suits an app that looks like a printed zine. A real gaussian is one render
attribute away — ctx.filter carries it and works in this engine — but that
attribute is a contract the PLAYER would have to honour too, which is the same
trap the `pressure` note in flip.js records. A decision to make on purpose, not
a default to slide in.
"""
import os
import re
import sys
from assertions import make_check
import browsing

BASE = os.environ.get("SKRIBL_BASE", "http://127.0.0.1:5001")

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("SKIP: playwright is not installed")
    sys.exit(0)

results = []


check = make_check(results)


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
    browsing.goto(page, BASE, "/flip")

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
    # SAMPLES ARE WHAT IS FADED, and since v296 a generated page holds two
    # kinds of stroke: the exposure's samples, and the strokes that did not
    # move, carried through once at full strength. Indexing by position would
    # tie this to the order they happen to be emitted in; alpha is what
    # actually distinguishes them, so that is what selects here.
    faded = [_alpha(q.get("color")) for q in tw["strokes"] if _alpha(q.get("color")) < 1]
    solid = [q for q in tw["strokes"] if _alpha(q.get("color")) >= 1]
    check("the samples are faded, not solid",
          faded and all(0 < a < 0.5 for a in faded),
          f"alphas {sorted(set(round(a, 3) for a in faded))[:4]} — solid samples "
          f"would read as stacked copies, not an exposure")
    check("...and the page also carries strokes at FULL strength",
          bool(solid),
          "every stroke is faded, so nothing was held still — the parts that "
          "did not move are supposed to come through as ink, not as 27 "
          "translucent copies of themselves")

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
    # A SAMPLE's colour, not strokes[0]. Since v296 the first strokes on a
    # generated page are the ones that did NOT move, carried through at full
    # strength — and '#ffffff' is the right answer for those, which made this
    # read as a regression when it was reading the wrong stroke.
    form = page.evaluate("""() => {
      const q = frames[1].strokes.find(z => /^#[0-9a-f]{8}$/i.test(z.color)
                                         || /rgba/i.test(z.color));
      return q ? q.color : frames[1].strokes[0].color;
    }""")
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
    # THE FALLOFF, MEASURED ON THE SAMPLES. This read every group as a sample
    # and labelled them by position (g % 2 — arm, foot, arm, foot). Since v296
    # a generated page also carries the strokes that did NOT move, once each,
    # so that alternation no longer holds and the labels landed on the wrong
    # strokes. Samples are the faded groups; carried strokes are the solid
    # ones, and telling them apart by alpha does not care what order they are
    # emitted in.
    # BY POSITION, NOT BY ALPHA — and this is the third classifier this check
    # has had. It began as `g % 2`, which v296 broke by emitting the strokes
    # that did not move first; it became "faded is a sample, solid was held
    # still", which v297 broke by giving the page a solid LEAD pose at the
    # midpoint. Alpha and emission order are both implementation detail. The
    # arm's third point sits at x=200 and the foot's at x=140 in both poses,
    # and neither moves in x, so position tells them apart whatever the page
    # is built out of.
    spread = page.evaluate("""() => {
      const f = frames[1];
      const arm = [], foot = [];
      let at = 0;
      for (let g = 0; g < f.strokeGroups.length; g++) {
        const n = f.strokeGroups[g], p = f.strokes[at + 2];
        if (p) (p.x > 170 ? arm : foot).push(p.y);
        at += n;
      }
      const rng = a => a.length ? Math.max(...a) - Math.min(...a) : 0;
      return { arm: rng(arm), foot: rng(foot), armN: arm.length, footN: foot.length };
    }""")
    # AS A RATIO, not as a pixel count. The old threshold was 100px, which only
    # made sense while the page was an exposure spanning the WHOLE travel; a
    # light page trails back from a lead at the midpoint, so the same uneven
    # blur covers less ground. Unevenness is the property — it is what makes
    # this look like motion rather than a double exposure — and a ratio still
    # says it when the span changes again.
    check("the part that moved FAR is spread across the page",
          spread["arm"] > 20 and spread["arm"] > 8 * max(spread["foot"], 1),
          f"arm spans {spread['arm']:.0f}px against the foot's "
          f"{spread['foot']:.0f}px over {spread['armN']} arm groups")
    # WHICH WAY DOES THE TRAIL POINT? Nothing asked, and the first version of
    # the light page got it backwards: the pose sits at the midpoint but the
    # ghosts spanned the WHOLE travel, so the faintest of them landed AHEAD of
    # it and the trail read as pointing the wrong way. Caught by looking at a
    # render, which is not a thing that happens reliably. A ghost is history: it
    # belongs between where the object was and where the pose now is, never past.
    _dir = page.evaluate("""() => {
      const mk = (x) => ({ strokes: [
          { x: x,      y: 100, color: '#ffffff', size: 6, t: 0, erase: false, start: true },
          { x: x + 20, y: 100, color: '#ffffff', size: 6, t: 1, erase: false },
          { x: x + 40, y: 100, color: '#ffffff', size: 6, t: 2, erase: false }],
        strokeGroups: [3], hold: 1 });
      frames.length = 0; frames.push(mk(100), mk(400));   // travels +300 in x
      idx = 0; fps = 24; subdiv = 1; selSpans = [];
      buildStrip(); render();
      const before = frames.length;
      addTween();
      if (frames.length === before) return null;
      const g = frames[1];
      const faded = [], solid = [];
      for (const q of g.strokes)
        (/^#[0-9a-f]{8}$/i.test(q.color || '') && !/ff$/i.test(q.color) ? faded : solid).push(q.x);
      return { trailMax: faded.length ? Math.max(...faded) : null,
               trailMin: faded.length ? Math.min(...faded) : null,
               leadMax: solid.length ? Math.max(...solid) : null,
               n: faded.length };
    }""")
    check("the trail sits BEHIND the pose, never past it",
          _dir and _dir["n"] > 0 and _dir["trailMax"] <= _dir["leadMax"] + 0.5,
          f"trail reaches x={_dir and _dir['trailMax']} against a pose ending at "
          f"x={_dir and _dir['leadMax']} — ink ahead of the pose is a trail "
          f"pointing the wrong way")
    check("...and it reaches back toward where the object came from",
          _dir and _dir["trailMin"] < _dir["leadMax"] - 20,
          f"trail starts at x={_dir and _dir['trailMin']} with the pose ending "
          f"at x={_dir and _dir['leadMax']} — a trail that does not reach back "
          f"is not a trail")

    # HOW FAR APART THE GHOSTS LAND IS THE WHOLE EFFECT, and until v297 it was
    # a constant 6 of them however wide the brush. On a ball drawn that way the
    # 6 landed inside the ball's own silhouette and read as one smear; on the
    # owner's hairline crossing the page the same 6 landed 18px apart with
    # nothing to bridge them, and the page read as SIX SEPARATE LINES. So the
    # spacing is what is pinned, not the count: two brushes over the SAME
    # travel, and the thin one has to ask for more.
    #
    # Brush 8 rather than 3 on purpose -- SMEAR_TRAIL_MAX caps a hairline, and
    # a pin written on top of the cap would be pinning the cap.
    _sp = page.evaluate("""() => {
      const mk = (x, size) => ({ strokes: [
          { x: x,      y: 100, color: '#ffffff', size, t: 0, erase: false, start: true },
          { x: x + 20, y: 100, color: '#ffffff', size, t: 1, erase: false },
          { x: x + 40, y: 100, color: '#ffffff', size, t: 2, erase: false }],
        strokeGroups: [3], hold: 1 });
      const run = (size) => {
        frames.length = 0; frames.push(mk(100, size), mk(400, size));  // +300 in x
        idx = 0; fps = 24; subdiv = 1; selSpans = [];
        buildStrip(); render();
        const before = frames.length;
        addTween();
        if (frames.length === before) return null;
        // A ghost is one faded run; its position is its first point's x.
        const g = frames[1]; const xs = []; let at = 0, alpha = 0;
        for (let k = 0; k < g.strokeGroups.length; k++) {
          const q = g.strokes[at];
          if (q && /^#[0-9a-f]{8}$/i.test(q.color || '') && !/ff$/i.test(q.color)) {
            xs.push(q.x);
            alpha = Math.max(alpha, parseInt(q.color.slice(7, 9), 16) / 255);
          }
          at += g.strokeGroups[k];
        }
        xs.sort((u, v) => u - v);
        let gap = 0;
        for (let k = 1; k < xs.length; k++) gap = Math.max(gap, xs[k] - xs[k - 1]);
        return { n: xs.length, gap, alpha, size };
      };
      return { thin: run(8), thick: run(40) };
    }""")
    _thin, _thick = (_sp or {}).get("thin"), (_sp or {}).get("thick")
    check("ghosts land no further apart than the brush is wide",
          _thin and _thick
          and _thin["gap"] <= _thin["size"] and _thick["gap"] <= _thick["size"],
          f"an 8px brush left {_thin and round(_thin['gap'], 1)}px between ghosts "
          f"and a 40px brush {_thick and round(_thick['gap'], 1)}px — a gap wider "
          f"than the brush is a row of repeats, not a smear")
    check("...so a thinner brush asks for more of them over the same travel",
          _thin and _thick and _thin["n"] > _thick["n"],
          f"8px brush drew {_thin and _thin['n']} ghosts, 40px brush "
          f"{_thick and _thick['n']} — the same count for both is the constant "
          f"this replaced")
    # AND MORE GHOSTS MUST NOT COST BRIGHTNESS. Dividing a fixed ink budget by
    # the count was the first way this was written, and it dimmed the owner's
    # ball from the 0.20 they had just asked for to 0.109: ghosts only stack
    # where the brush covers the same pixel, which the spacing above already
    # holds constant.
    check("...and asking for more of them does not dim the trail",
          _thin and _thick and _thin["alpha"] >= 0.10 and _thick["alpha"] >= 0.10,
          f"brightest ghost was {_thin and round(_thin['alpha'], 3)} at 8px and "
          f"{_thick and round(_thick['alpha'], 3)} at 40px — a trail that fades "
          f"as it lengthens is a budget divided by the count")

    check("...and the part that barely moved barely spreads",
          spread["foot"] <= 4,
          f"foot spans {spread['foot']:.0f}px — it moved 2px between the poses, "
          f"so ink spread wider than that is the smear inventing motion")

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

    print("\nMISMATCHED COUNTS — accepted since v296, not refused")
    # INVERTED, DELIBERATELY. This block used to assert that pages with a
    # different NUMBER of strokes produce NO page, and that the refusal names
    # the two counts. Both were true and both are now the opposite of what the
    # tool should do: the counts were the wall the owner hit every time he drew
    # the next pose by hand -- "this one has 5, the next has 7" -- and strokes
    # are paired by shape since v296, with an unpartnered stroke drawn once.
    #
    # An assertion that can only pass while the limitation STANDS is a record of
    # the limitation, not a guard on the tool. So it guards the achievement now:
    # this pair must produce a page, and the page must contain the stroke that
    # had no partner rather than dropping it.
    # A FIXTURE WHERE THE RIGHT ANSWER IS NOT IN DOUBT. The first version of
    # this was two 2-point strokes against two more, close enough together that
    # the runner-up test declined them — defensibly, since a person would
    # hesitate too. A pin whose correct answer is arguable measures the pin.
    # This is a figure of two clear strokes against the same figure plus an
    # extra mark: the two that correspond are obvious, and the extra one has no
    # partner and must simply be drawn once.
    page.evaluate("""() => {
      const run = (x0,y0,x1,y1,n) => { const o=[];
        for(let i=0;i<=n;i++) o.push({ x:x0+(x1-x0)*i/n, y:y0+(y1-y0)*i/n,
          size:6, color:'#ffffff', erase:false, t:i, start:i===0 }); return o; };
      const mk = runs => { const f={strokes:[],strokeGroups:[],hold:1};
        runs.forEach(r=>{ r.forEach((q,i)=>{ const c={...q};
          if(i===0) c.start=true; else delete c.start; f.strokes.push(c); });
          f.strokeGroups.push(r.length); }); return f; };
      frames.length = 0;
      frames.push(mk([ run(120,60,120,240,12), run(120,120,60,180,10) ]));
      frames.push(mk([ run(120,60,120,240,12), run(120,120,180,180,10),
                       run(220,60,250,90,6) ]));
      idx = 0; selSpans = []; buildStrip(); render();
    }""")
    page.evaluate("() => addTween()")
    page.wait_for_timeout(300)
    check("one stroke against two now PRODUCES a page",
          page.evaluate("() => frames.length") == 3,
          "the count wall is what v296 removed; refusing here is the old "
          "behaviour, not a safety net")
    check("...and the refusal message is gone with it",
          "number of strokes" not in (page.evaluate(
              "() => (document.getElementById('flipChip')||{}).textContent") or "").lower(),
          "the chip is still explaining a rule the tool no longer has")

    # AND WHAT IS STILL DECLINED: two drawings with nothing in common, where
    # every pairing would be a guess. This is the pin that stops "pair anything
    # with anything" from satisfying the two above.
    page.evaluate("""() => {
      frames.length = 0;
      frames.push({ strokes: [{x:10,y:10,color:'#fff',size:6,t:0,erase:false,start:true},
                              {x:14,y:14,color:'#fff',size:6,t:1,erase:false}],
                    strokeGroups: [2], hold: 1 });
      frames.push({ strokes: [{x:300,y:300,color:'#fff',size:6,t:0,erase:false,start:true},
                              {x:20,y:290,color:'#fff',size:6,t:1,erase:false},
                              {x:295,y:20,color:'#fff',size:6,t:2,erase:false},
                              {x:30,y:30,color:'#fff',size:6,t:3,erase:false}],
                    strokeGroups: [4], hold: 1 });
      idx = 0; selSpans = []; buildStrip(); render();
    }""")
    _before = page.evaluate("() => frames.length")
    page.evaluate("() => addTween()")
    page.wait_for_timeout(300)
    check("a tiny mark against a huge scrawl is still declined",
          page.evaluate("() => frames.length") == _before,
          "pairing these would smear a 4px mark across the whole page, which "
          "reads as a bug in the tool rather than a limit of the idea")

    # THE HELP HAS TO AGREE WITH THE TOOL. It said "It needs the same strokes on
    # both pages, so duplicate and move rather than redrawing from scratch" --
    # advice that was correct until v255 and is now the opposite of true. A wrong
    # answer in the help is worse than no answer: it tells someone the workflow
    # they want is unsupported when it is the one that just started working.
    _help = page.evaluate("""() => {
      const tips = [...document.querySelectorAll('.help-tip')];
      const t = tips.find(e => (e.querySelector('.help-pill')||{}).textContent === 'Motion Smear');
      return t ? t.textContent.replace(/\\s+/g, ' ') : null; }""")
    check("the help describes the effect's ACTUAL requirement",
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

    # ---------------------------------------------------------------- v295
    # THE DRAFT DOES NOT STORE THE POINTS. A smear is up to 27 samples of every
    # stroke, four passes deep, and the autosave wrote every one of them as
    # JSON: 722 KB for one page, so seven of them fill a 5 MB origin quota and
    # autosave dies for good. Reported from a phone, with no media loaded at
    # all, as QuotaExceededError "even without media".
    #
    # The page is reproducible from its two neighbours and its sample plan, so
    # the draft stores that instead. What is pinned here is the SIZE (the whole
    # point), the ROUND TRIP (it has to come back the same), the three ways it
    # must refuse to use a recipe, and the file format it must stay out of.
    print("\nMOTION SMEAR — the draft stores a recipe, not the points")
    page.evaluate(POSES, 150)
    page.evaluate("() => addTween()")
    page.wait_for_timeout(400)
    _sz = page.evaluate("""() => ({
        full: JSON.stringify(serializeFlip()).length,
        lean: JSON.stringify(serializeFlip({recipes: true})).length }) """)
    # 61x WAS A MEASUREMENT OF THE BLOAT, NOT OF THE RECIPE. It was taken when a
    # generated page was an exposure -- 27 samples over 4 blur passes of every
    # stroke -- so storing the recipe instead skipped an enormous page. v297 made
    # the page itself light, and most of that 61x is now banked in the page
    # rather than in the recipe. Holding the old ratio would mean the only way
    # to pass is to put the bloat back.
    check("the smear still costs less as a recipe than as points",
          _sz["lean"] < _sz["full"],
          f"{_sz['full']:,} bytes written out against {_sz['lean']:,} as a recipe")

    # THE ROUND TRIP IS THE WHOLE RISK. The strokes are not stored, so a rebuild
    # that comes back different is a page the artist cannot get back.
    _rt = page.evaluate("""() => {
      const sig = f => f.strokes.length + '/' + f.strokes.slice(0, 80)
        .map(p => Math.round(p.x) + ',' + Math.round(p.y)).join('|');
      const was = sig(frames[1]), wasN = frames.length, wasPts = frames[1].strokes.length;
      const d = JSON.parse(JSON.stringify(serializeFlip({recipes: true})));
      // PROVE A RECIPE WAS INVOLVED. Without this, the assertion below passes on
      // a draft that stored the points -- true of every draft ever written, and
      // silent about the rebuild. Measured: it stayed green with recipes
      // switched off entirely, which makes it an assertion about round trips in
      // general rather than about the thing this change added.
      const viaRecipe = !!(d.frames[1] && d.frames[1].gen);
      applyPayload(d);
      // ASKED OF THE BEHAVIOUR, not of the frame. The recipe lives in a
      // WeakMap beside the page precisely so it is not a field on it, so
      // "is it re-stamped" can only honestly mean "does saving again still
      // produce a recipe" -- which is the property anyone cares about.
      return { viaRecipe, same: sig(frames[1]) === was, pages: frames.length === wasN,
               pts: frames[1].strokes.length, wasPts,
               posePts: frames[0].strokes.length,
               restamped: !!serializeFlip({recipes: true}).frames[1].gen }; }""")
    check("the draft really did store a recipe rather than the points",
          _rt["viaRecipe"], str(_rt))
    check("a recipe restores the same page, point for point",
          _rt["viaRecipe"] and _rt["same"] and _rt["pages"], str(_rt))
    # Against what it HAD, not an absolute: this fixture's poses are six points
    # each, so a threshold tuned on the stick figure called a correct 648-point
    # rebuild a placeholder.
    # A FLOOR RELATIVE TO THE POSES, not an absolute. 20 was tuned when a
    # generated page was an exposure and could not be small; a light page on
    # this fixture's six-point poses is legitimately fifteen points, and the
    # absolute floor started calling a correct rebuild a placeholder. What the
    # check is actually for is that the rebuild is not EMPTY and is not a stub:
    # it has to come back with what it had, and with at least a drawing in it.
    check("...and it is a real page again, not a placeholder",
          _rt["pts"] == _rt["wasPts"] and _rt["pts"] >= _rt["posePts"],
          f"{_rt['pts']} points against the {_rt['wasPts']} it had, "
          f"and a pose of {_rt['posePts']}")
    check("...re-stamped, so the next save is a recipe too",
          _rt["restamped"],
          "paying full price once and for ever after is the bug this replaces")

    # Three refusals. Each is the safe direction: writing the strokes costs only
    # the bytes the recipe was trying to save, while a wrongly-trusted recipe
    # rebuilds a page from pages that are no longer the ones it came from.
    _edit = page.evaluate("""() => {
      frames[1].strokes.push({x:10,y:10,color:'#ff0000',size:5,t:0,erase:false,start:true});
      frames[1].strokeGroups.push(1);
      const o = serializeFlip({recipes: true}).frames[1];
      return { recipe: !!o.gen, strokes: Array.isArray(o.strokeGroups) }; }""")
    check("a page that has been drawn on is written out in full",
          not _edit["recipe"] and _edit["strokes"], str(_edit))

    page.evaluate(POSES, 150)
    page.evaluate("() => addTween()")
    page.wait_for_timeout(400)
    _nb = page.evaluate("""() => {
      frames[0].strokes.push({x:5,y:5,color:'#00ff00',size:5,t:0,erase:false,start:true});
      frames[0].strokeGroups.push(1);
      const o = serializeFlip({recipes: true}).frames[1];
      return { recipe: !!o.gen, strokes: Array.isArray(o.strokeGroups) }; }""")
    check("a page whose NEIGHBOUR moved is written out in full",
          not _nb["recipe"] and _nb["strokes"], str(_nb))

    # saveDraft() writes the format the Pad reads and a person keeps on disk.
    check("the .skribl file carries no recipe, only ordinary stroke data",
          not page.evaluate("() => serializeFlip().frames.some(f => !!f.gen)"),
          "a recipe in the file format is a schema change for every other reader")

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
    TWEEN_POINT_CAP_EXPECT = page.evaluate("() => TWEEN_POINT_CAP")
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
    # INVERTED IN v297, and this is the shape CLAUDE.md warns about: the old pin
    # could only pass while a generated page was heavy enough to need rationing.
    # It asserted that a page gets LIGHTER at 24fps than at 12 -- true of an
    # exposure, whose sample count came out of the render budget, and the budget
    # shrinks as the slot does. A light page is a lead pose plus six fixed
    # ghosts: a few hundred points at any rate, nowhere near the ceiling, so
    # there is nothing left to ration and nothing to vary. Making it vary again
    # would mean putting the weight back.
    #
    # So the guarantee is now the stronger one: the page costs the SAME at any
    # playback rate, and is far under the cap at all of them. A page that grew
    # with the rate, or crept toward the ceiling, still fails here.
    check("a generated page costs the same at any playback rate, and stays light",
          _gen["12"] == _gen["24"] and _gen["24"] < TWEEN_POINT_CAP_EXPECT,
          f"{_gen['12']} points at 12fps vs {_gen['24']} at 24 "
          f"(ceiling {TWEEN_POINT_CAP_EXPECT:,})")

    # v261's REBUILD IN-BETWEENS section left with the feature (v290, owner's call).

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

    # ---------------------------------------------------------------- v296
    # THE SMEAR COUNTS WHAT YOU CAN SEE.
    #
    # Reported with a picture: duplicate a page, rub the diagonal out, draw a
    # new one, and the refusal says "this one has 2, the next has 4". Erasing
    # does not remove a stroke, it ADDS one -- the rubbed-out stroke is still
    # in the frame and the rub is a stroke on top of it -- so the count the
    # rule used was never the count on screen.
    #
    # The fixture is built by ERASING, not by writing an erase:true array by
    # hand, because the defect is a property of what the eraser leaves behind.
    print("\nERASED PAGES — pairing reads the drawing, not the frame")
    ERASED = """() => {
      const run = (x0,y0,x1,y1,n,erase,size) => { const o=[];
        for(let i=0;i<=n;i++) o.push({ x:x0+(x1-x0)*i/n, y:y0+(y1-y0)*i/n,
          size: size||6, color:'#ffffff', erase: !!erase, t:0,
          start: i===0 }); return o; };
      const mk = runs => { const f={strokes:[],strokeGroups:[],hold:1};
        runs.forEach(r => { r.forEach((q,i)=>{ const c={...q};
          if(i===0) c.start=true; else delete c.start; f.strokes.push(c); });
          f.strokeGroups.push(r.length); }); return f; };
      // Page 1: a vertical and a diagonal. Two strokes, nothing erased.
      const one = mk([ run(120,60,120,300,10), run(60,260,200,140,10) ]);
      // Page 2: the same two, then a rub ALONG the diagonal, then its
      // replacement. Four groups in the frame; two lines on the screen.
      const two = mk([ run(120,60,120,300,10), run(60,260,200,140,10),
                       run(58,262,202,138,24,true,30), run(54,252,206,148,10) ]);
      frames.length = 0; frames.push(one); frames.push(two);
      idx = 0; actionLog.length = 0; redoStack.length = 0;
      buildStrip(); render();
      return { groups: frames.map(f => f.strokeGroups.length),
               ink: frames.map(f => tweenVisible(f).ink.length) };
    }"""
    shape = page.evaluate(ERASED)
    check("the fixture is the reported one: 2 groups against 4",
          shape["groups"] == [2, 4],
          f"frame groups are {shape['groups']} — the fixture no longer reproduces "
          f"the report, so nothing below is testing it")
    check("...and both pages read as TWO strokes of visible ink",
          shape["ink"] == [2, 2],
          f"visible ink is {shape['ink']}; an eraser and the stroke it removed "
          f"are still being counted as strokes the artist drew")
    check("so the reported workflow is offered a smear, not a refusal",
          page.evaluate("() => tweenMismatch(frames[0], frames[1])") is None,
          str(page.evaluate("() => tweenMismatch(frames[0], frames[1])")))

    # AN ERASER IS NEVER SAMPLED. Where the counts happened to line up it was
    # smeared like ink -- measured at 1,188 eraser points in a 3,564-point
    # exposure -- which drags a hole through the drawing. It is carried once
    # instead, so what was rubbed out stays rubbed out.
    made = page.evaluate("""() => {
      const out = buildTween(frames[0], frames[1]);
      if(!out) return null;
      let erased = 0, runs = 0, at = 0;
      for(const n of out.strokeGroups){
        if(out.strokes[at].erase){ runs++; erased += n; }
        at += n;
      }
      return { points: out.strokes.length, erasePoints: erased, eraseRuns: runs };
    }""")
    check("a smear is built from the erased pair at all", made is not None,
          "buildTween refused a pair tweenMismatch accepted")
    # frames[0] carries no eraser, so nothing should be carried: the exposure of
    # a clean first page is clean.
    check("...and it samples no eraser: zero eraser points from a clean pose",
          made and made["erasePoints"] == 0,
          f"{made and made['erasePoints']} eraser points came from a page that "
          f"has none — they are being paired and sampled as ink")

    # THE OTHER DIRECTION, and it is the one that stops "just drop the erasers"
    # from satisfying everything above: smear FROM the erased page and the rub
    # has to survive, once, unsampled.
    back = page.evaluate("""() => {
      const out = buildTween(frames[1], frames[0]);
      if(!out) return null;
      let erased = 0, runs = 0, at = 0;
      for(const n of out.strokeGroups){
        if(out.strokes[at].erase){ runs++; erased += n; }
        at += n;
      }
      const src = tweenVisible(frames[1]).erase;
      return { erasePoints: erased, eraseRuns: runs,
               srcRuns: src.length, srcPoints: src.reduce((t, r) => t + r.length, 0) };
    }""")
    check("what you rubbed out stays rubbed out: the eraser is carried",
          back and back["eraseRuns"] == back["srcRuns"] and back["eraseRuns"] > 0,
          f"{back and back['eraseRuns']} eraser runs carried from a page with "
          f"{back and back['srcRuns']} — dropping them fills the hole back in")
    check("...ONCE, not once per sample",
          back and back["erasePoints"] == back["srcPoints"],
          f"{back and back['erasePoints']} eraser points from a source holding "
          f"{back and back['srcPoints']} — a swept hole, which is the defect")

    # ORDER MATTERS. An eraser only removes what was drawn BEFORE it; testing a
    # stroke against every eraser in the frame would delete the stroke drawn to
    # REPLACE a rubbed-out one, which is the whole of the reported workflow.
    order = page.evaluate("""() => {
      const f = frames[1];
      const ink = tweenVisible(f).ink;
      // The replacement was drawn last and crosses the rubbed-out area.
      return { count: ink.length, lastIsReplacement: ink.length ? true : false };
    }""")
    # THE REPLACEMENT RETRACES THE RUB, which is the whole point of this pin and
    # the reason it sits where it does: the fixture's new diagonal is the old
    # one rotated ~6 degrees about its midpoint, so every one of its points
    # lies inside the 30px band the eraser swept. Draw it anywhere else -- an
    # up-diagonal that merely CROSSES the rub, as the first version had -- and
    # testing against every eraser instead of the later ones passes happily,
    # measured. It is also the ordinary way people work: rub a line out, draw
    # it again slightly differently.
    check("a stroke drawn AFTER the rub survives it",
          order["count"] == 2,
          f"{order['count']} ink strokes; the replacement drawn over the rubbed "
          f"area is being treated as rubbed out itself")

    # ---------------------------------------------------------------- v296
    # AIMED AT THE PART THAT MOVES.
    print("\nAIMED — the selection is the argument the effect wanted")
    FIG = """(deg) => {
      const line=(x0,y0,x1,y1,n)=>{const o=[];for(let i=0;i<=n;i++)
        o.push({x:x0+(x1-x0)*i/n,y:y0+(y1-y0)*i/n,size:6,color:'#ffffff',t:0});return o;};
      const rot=(pts,cx,cy,d)=>{const r=d*Math.PI/180,c=Math.cos(r),sn=Math.sin(r);
        return pts.map(q=>({...q,x:cx+(q.x-cx)*c-(q.y-cy)*sn,y:cy+(q.x-cx)*sn+(q.y-cy)*c}));};
      const runs=[line(240,60,240,180,12), line(240,188,240,380,12),
                  rot(line(240,240,240,380,10),240,240,deg), line(240,380,320,500,10)];
      const f={strokes:[],strokeGroups:[],hold:1};
      runs.forEach(r=>{r.forEach((q,i)=>{const c={...q};
        if(i===0)c.start=true; else delete c.start; f.strokes.push(c);});
        f.strokeGroups.push(r.length);});
      return f;
    }"""
    SETUP = """([mk, deg, sel]) => {
      const f = new Function('return ' + mk)();
      frames.length = 0; frames.push(f(20)); frames.push(f(deg));
      idx = 0; actionLog.length = 0; redoStack.length = 0;
      /* A NEW DOCUMENT HAS A NEW TIME GRID. applyPayload sets fps and subdiv for
         a document it loads; this block builds one by hand and has to do the
         same. Without it the three documents below share whatever rate the
         previous one left behind -- and an in-between takes its slot by doubling
         the rate, so the third was planned against 4x the first. The smear's
         sample count comes from tweenRenderCap(fps), so that is not a cosmetic
         difference: it is a different page, and the pin comparing the whole page
         against the all-selected one was reading it. */
      fps = 12; subdiv = 1;
      const v = tweenVisible(frames[0]);
      selSpans = sel === null ? [] : sel.map(i => v.inkSpans[i]);
      buildStrip(); render();
      const before = frames.length;
      addTween();
      if(frames.length === before) return null;
      const g = frames[1];
      /* HOW MANY TIMES DOES A STILL POINT APPEAR? Asked directly, rather than
         inferred from the page's point count. The old check decomposed the
         total as (still + a whole number of samples), which only holds while
         every moving stroke is emitted the same number of times -- an
         exposure's shape. A light page is a lead plus a handful of coarse
         ghosts, so the arithmetic stopped meaning anything. The PROPERTY it
         was defending is untouched and can just be counted. */
      let stillMax = 0;
      if (sel !== null) {
        const src = frames[0], at0 = [];
        let acc = 0;
        for (const c of src.strokeGroups) { at0.push(acc); acc += c; }
        /* WHOLE RUNS, not points. Counting points that share a coordinate said
           an unaimed stroke appeared twice on this fixture -- a stick figure
           whose limbs meet, so the aimed stroke's lead lands exactly on a joint
           the unaimed strokes also occupy. A run is only a copy of a source run
           if EVERY one of its points matches, which a coincidence does not do. */
        const runs = [];
        let at = 0;
        for (const cnt of g.strokeGroups) { runs.push(g.strokes.slice(at, at + cnt)); at += cnt; }
        const same = (r, from, cnt) => r.length === cnt && r.every((q, i) =>
          Math.abs(q.x - src.strokes[from + i].x) < 0.01 &&
          Math.abs(q.y - src.strokes[from + i].y) < 0.01);
        src.strokeGroups.forEach((cnt, gi) => {
          if (sel.indexOf(gi) >= 0) return;          // aimed: it is smeared
          stillMax = Math.max(stillMax,
            runs.filter(r => same(r, at0[gi], cnt)).length);
        });
      }
      return { points: g.strokes.length, groups: g.strokeGroups.length, stillMax,
               recipe: (function(){ const r = genRecipe.get(g);
                 return r ? { n: r.n, passes: r.passes, aim: r.aim || null } : null; })() };
    }"""
    whole = page.evaluate(SETUP, [FIG, -125, None])
    armed = page.evaluate(SETUP, [FIG, -125, [2]])
    check("a smear with nothing selected is the whole page, as before",
          whole and whole["recipe"] and whole["recipe"]["aim"] is None,
          f"{whole and whole['recipe']} — an empty selection must not aim anything")
    check("selecting one stroke aims the smear at it",
          armed and armed["recipe"] and armed["recipe"]["aim"] == [2],
          f"{armed and armed['recipe']} — the selection was not read")
    check("...and the page is lighter for it",
          armed and whole and armed["points"] < whole["points"],
          f"{armed and armed['points']} aimed vs {whole and whole['points']} whole")
    check("...because a stroke that was not aimed at appears exactly once",
          armed and armed["stillMax"] == 1,
          f"an unaimed stroke appears {armed and armed['stillMax']} "
          f"times — more than once means it is being sampled like the ones that "
          f"moved, which costs its brightness for no trail")

    # SELECTING EVERYTHING IS NOT A SPECIAL CASE, and this is the pin that stops
    # "aim at nothing" from satisfying the three above.
    allsel = page.evaluate(SETUP, [FIG, -125, [0, 1, 2, 3]])
    check("selecting every stroke is the whole page again",
          allsel and allsel["recipe"] and allsel["recipe"]["aim"] is None
          and allsel["points"] == whole["points"],
          f"{allsel and allsel['recipe']}, {allsel and allsel['points']} points "
          f"against {whole and whole['points']}")

    # THE AIM IS PART OF THE RECIPE, or a stored page comes back un-aimed. This
    # drives the real round trip rather than reading the WeakMap.
    #
    # RE-ARMED FIRST, deliberately. The select-everything case above leaves an
    # UNAIMED page in frames[1], and running the round trip on that reported
    # "the aim did not survive" against code that was fine — the test's own
    # ordering, caught by this pin on its first run.
    page.evaluate(SETUP, [FIG, -125, [2]])
    trip = page.evaluate("""() => {
      const json = JSON.stringify(serializeFlip({ recipes: true }));
      const stored = JSON.parse(json).frames[1];
      const was = frames[1].strokes.length;
      applyPayload(JSON.parse(json));
      return { viaRecipe: !!(stored && stored.gen), aim: stored && stored.gen && stored.gen.aim,
               was: was, now: frames[1] ? frames[1].strokes.length : null };
    }""")
    check("an aimed page is stored as a recipe", trip["viaRecipe"],
          "it was written out in full, so this proves nothing about the recipe")
    check("...whose aim survives the draft", trip["aim"] == [2],
          f"gen.aim is {trip['aim']} — the rebuild would un-aim the page")
    check("...and it rebuilds to the SAME page, not a whole-page smear",
          trip["was"] == trip["now"],
          f"{trip['was']} points saved, {trip['now']} rebuilt — a draft that "
          f"reloads different from the one it stored")

    # ---------------------------------------------------------------- v296
    # PAIRED BY SHAPE, AND AIMED WITHOUT BEING ASKED.
    print("\nMATCHING — which stroke is which, and which of them moved")
    FIGM = """(deg, extra) => {
      const line=(x0,y0,x1,y1,n)=>{const o=[];for(let i=0;i<=n;i++)
        o.push({x:x0+(x1-x0)*i/n,y:y0+(y1-y0)*i/n,size:6,color:'#ffffff',erase:false,t:0});return o;};
      const circ=(cx,cy,r)=>{const o=[];for(let i=0;i<=28;i++){const a=i/28*Math.PI*2;
        o.push({x:cx+Math.cos(a)*r,y:cy+Math.sin(a)*r,size:6,color:'#ffffff',erase:false,t:0});}return o;};
      const rot=(q,cx,cy,d)=>{const r=d*Math.PI/180,c=Math.cos(r),sn=Math.sin(r);
        return q.map(z=>({...z,x:cx+(z.x-cx)*c-(z.y-cy)*sn,y:cy+(z.x-cx)*sn+(z.y-cy)*c}));};
      const runs=[circ(240,140,48), line(240,188,240,380,12),
                  rot(line(240,240,240,380,10),240,240,deg), line(240,380,320,500,10)];
      if(extra) runs.push(line(300,120,340,140,6));
      const f={strokes:[],strokeGroups:[],hold:1};
      runs.forEach(r=>{r.forEach((q,i)=>{const c={...q};
        if(i===0)c.start=true; else delete c.start; f.strokes.push(c);});
        f.strokeGroups.push(r.length);});
      return f;
    }"""
    def pose(deg, extra=False, scramble=False, shift=0, reverse_arm=False):
        return page.evaluate("""([mk,deg,extra,scr,shift,revArm]) => {
          const f = new Function('return ' + mk)()(deg, extra);
          if(shift) f.strokes.forEach(q => { q.x += shift; });
          if(revArm){
            const runs=[]; let at=0;
            f.strokeGroups.forEach(n=>{ runs.push(f.strokes.slice(at,at+n)); at+=n; });
            runs[2].reverse();
            const g={strokes:[],strokeGroups:[],hold:1};
            runs.forEach(r=>{ r.forEach((q,i)=>{const c={...q};
              if(i===0)c.start=true; else delete c.start; g.strokes.push(c);});
              g.strokeGroups.push(r.length); });
            return g;
          }
          if(!scr) return f;
          // redraw the SAME pose with its strokes in another order
          const runs=[]; let at=0;
          f.strokeGroups.forEach(n=>{ runs.push(f.strokes.slice(at,at+n)); at+=n; });
          const order=[3,0,2,1].concat(runs.length>4?[4]:[]);
          const g={strokes:[],strokeGroups:[],hold:1};
          order.forEach(k=>{ const r=runs[k]; r.forEach((q,i)=>{const c={...q};
            if(i===0)c.start=true; else delete c.start; g.strokes.push(c);});
            g.strokeGroups.push(r.length); });
          return g;
        }""", [FIGM, deg, extra, scramble, shift, reverse_arm])

    def smear(a, b):
        return page.evaluate("""([a,b]) => {
          frames.length = 0; frames.push(a); frames.push(b);
          idx = 0; selSpans = []; actionLog.length = 0; redoStack.length = 0;
          buildStrip(); render();
          const n = frames.length;
          addTween();
          if(frames.length === n) return { refused: true,
            chip: (document.getElementById('flipChip')||{}).textContent };
          return { refused: false, points: frames[1].strokes.length,
                   groups: frames[1].strokeGroups.length,
                   chip: (document.getElementById('flipChip')||{}).textContent };
        }""", [a, b])

    plain = smear(pose(20), pose(-125))
    check("an arm swinging 145 degrees is smeared", not plain["refused"], str(plain))

    # ASSERT THE PAIRING, NOT THE PAGE SIZE. The first version of this block
    # checked that a scrambled-order pose produced a page of about the same
    # number of points as an in-order one -- and a WRONG pairing produces a
    # page of about the same size too, so three of four mutations passed it:
    # pairing by drawing order, comparing in page coordinates instead of about
    # each page's centre, and ignoring that a limb may be redrawn backwards.
    # All three were invisible to it. The pairing itself is what this measures
    # now, which is the mechanism rather than a shadow of it.
    def pairing(a, b):
        return page.evaluate("""([a,b]) => {
          const ia = tweenVisible(a).ink, ib = tweenVisible(b).ink;
          return tweenMatch(ia, ib).map(m => m ? { j: m.j, rev: !!m.reversed } : null);
        }""", [a, b])

    # ---------------------------------------------------------------- v300
    # THE INVARIANT, NOT A PATCH: two drawings with identical geometry and
    # completely different sampling must produce the same correspondence.
    #
    # This is v298's V19, open through v299 and recorded as open in DECISIONS
    # before it was closed. Two mechanisms, both fixed, both mutated below:
    # tweenCentred weighted the page centre by POINT COUNT, and
    # tweenShapeCost sampled at t * (r.length - 1), a VERTEX fraction.
    #
    # THE FIXTURE IS CORPUS CASE 19's GEOMETRY, because that is the case known
    # to fail: three IDENTICAL circles with the middle one moved. Identical
    # shapes make shape cost tie, so position is the only thing left to
    # separate them — and position is exactly what a density-weighted centre
    # gets wrong. Measured on the shipped v299 tree: 11 of these 64
    # combinations returned the wrong correspondence, hand/hand among them,
    # which is the [1, 0, 2] the corpus recorded and nobody read.
    #
    # EVERY COMBINATION, not a diagonal. Two pages are recorded independently
    # in life, so a fix that only worked when both were sampled alike would
    # pass a diagonal sweep and fail a person.
    print("\nSAMPLING INVARIANCE — the same drawing, recorded differently")

    _inv = page.evaluate("""() => {
      const circle = (cx, cy, r) => (t) => ({ x: cx + r*Math.cos(2*Math.PI*t),
                                              y: cy + r*Math.sin(2*Math.PI*t) });
      const A_S = [circle(180,353,55), circle(353,353,55), circle(526,353,55)];
      const B_S = [circle(180,353,55), circle(353,180,55), circle(526,353,55)];
      const even = (f, n) => Array.from({length:n}, (_, i) => f(i/(n-1)));
      // Half the points crammed into the first 15% of the arc: a pen that
      // started slowly and then swept. This is the one the index-fraction
      // sampler could not survive.
      const clump = (f, n) => Array.from({length:n}, (_, i) => {
        const u = i/(n-1); return f(u < 0.5 ? u*0.3 : 0.15 + (u-0.5)*1.7); });
      const phase = (f, n) => Array.from({length:n}, (_, i) => f(((i/(n-1))+0.33)%1));
      let s = 20260917;
      const rnd = () => (s = (s*1103515245 + 12345) & 0x7fffffff) / 0x7fffffff;
      const mk = (runs) => { const f = {strokes:[], strokeGroups:[], hold:1}; let t = 0;
        runs.forEach(r => { r.forEach((p,i) => { const q = {x:p.x, y:p.y, size:6,
            color:'#ffffff', erase:false, t:t}; t += 16; if(i===0) q.start = true;
            f.strokes.push(q); }); f.strokeGroups.push(r.length); });
        return f; };
      const recipes = {
        even:      (S) => S.map(f => even(f, 60)),
        lopsided:  (S) => [even(S[0], 8), even(S[1], 400), even(S[2], 8)],
        lopsidedB: (S) => [even(S[0], 400), even(S[1], 8), even(S[2], 400)],
        hand:      (S) => S.map(f => { const step = 3 + rnd()*15;
                     return even(f, Math.max(4, Math.round(2*Math.PI*55/step))); }),
        clustered: (S) => S.map((f,i) => clump(f, 30 + i*120)),
        phased:    (S) => S.map(f => phase(f, 70)),
        sparse:    (S) => S.map(f => even(f, 6)),
        dense:     (S) => S.map(f => even(f, 500))
      };
      const names = Object.keys(recipes);
      const wrong = [];
      let n = 0;
      for (const na of names) for (const nb of names) {
        n++;
        const A = mk(recipes[na](A_S)), B = mk(recipes[nb](B_S));
        const p = tweenMatch(tweenVisible(A).ink, tweenVisible(B).ink)
                    .map(m => m === null ? null : m.j);
        if (JSON.stringify(p) !== '[0,1,2]') wrong.push(na + '/' + nb + ' -> ' + JSON.stringify(p));
      }
      return { total: n, wrong: wrong };
    }""")
    check("the same drawing recorded 64 ways pairs the same way every time",
          _inv["wrong"] == [],
          f"{len(_inv['wrong'])} of {_inv['total']} combinations disagree: "
          + "; ".join(_inv["wrong"][:6])
          + " — identical geometry, different pen speed. Density is a property "
            "of how it was observed, not of the drawing")

    # AND THE SECOND MECHANISM NEEDS ITS OWN PIN, because the sweep above does
    # not reach it: with the page centre fixed, the 64 combinations pass even
    # with the old vertex-index sampler restored. Measured, so this is not a
    # guess — the mutation was run and stayed green, which is the moment a
    # change becomes unproven rather than proven.
    #
    # So the property is asserted where it lives. The SAME curve, sampled
    # evenly and sampled with half its points crammed into the first eighth of
    # its arc, must cost the same against a fixed target: the drawing did not
    # change, only the pen speed. Measured on this fixture:
    #
    #     vertex-index sampler     35.3 -> 84.9     58% drift
    #     arc-length sampler       36.6 -> 36.6      0.05% drift
    #
    # A plateau three orders of magnitude wide, not a tuned edge.
    _sc = page.evaluate("""() => {
      const curve  = (t) => ({ x: 150 + 300*t,
                               y: 300 + 120*Math.sin(t*Math.PI*1.6) - 90*t*t });
      const target = (t) => ({ x: 150 + 300*t,
                               y: 330 + 100*Math.sin(t*Math.PI*1.6) - 70*t*t });
      const even  = (f,n) => Array.from({length:n}, (_,i) => f(i/(n-1)));
      const clump = (f,n) => Array.from({length:n}, (_,i) => {
        const u = i/(n-1); return f(u < 0.5 ? u*0.25 : 0.125 + (u-0.5)*1.75); });
      const T = even(target, 60);
      const a = tweenShapeCost(even(curve, 60), T).cost;
      const b = tweenShapeCost(clump(curve, 60), T).cost;
      return { even: a, clumped: b, drift: Math.abs(a-b)/Math.max(a,b) };
    }""")
    check("shape cost is read along the ARC, so clustering inside a stroke "
          "does not change it",
          _sc["drift"] < 0.02,
          f"{_sc['even']:.1f} evenly sampled against {_sc['clumped']:.1f} "
          f"clustered — {_sc['drift']*100:.1f}% drift on one curve that did not "
          f"move. Half way through the point list is not half way along the "
          f"drawing")

    inorder = pairing(pose(20), pose(-125))
    check("in drawing order, every stroke pairs with its own partner",
          [m and m["j"] for m in inorder] == [0, 1, 2, 3], str(inorder))

    # SCRAMBLED: the same four strokes, recorded in the order 3,0,2,1. Pairing
    # by index would return 0,1,2,3 and be wrong for three of the four.
    scram = pairing(pose(20), pose(-125, scramble=True))
    check("redrawn in ANOTHER STROKE ORDER, they still pair by shape",
          [m and m["j"] for m in scram] == [1, 3, 2, 0],
          f"{scram} — pairing by the order your hand took is what put the "
          f"outline with the mouth")

    # TRAVELLED: the whole figure moves 90px right. Comparing in page
    # coordinates pairs each stroke with whatever is now nearest, which is the
    # wrong stroke; comparing about each page's own centre does not.
    moved = pairing(pose(20), pose(20, shift=90))
    check("when the WHOLE drawing travels, every stroke still finds itself",
          [m and m["j"] for m in moved] == [0, 1, 2, 3],
          f"{moved} — measured about each page's own centre, or 'which stroke "
          f"is nearest' is answered by the wrong stroke")

    # BACKWARDS: one limb recorded end-to-start. It is the same limb, and the
    # interpolation has to know, or the stroke turns itself inside out.
    # THE SAME POSE, with the arm recorded end-to-start. Comparing it against a
    # pose rotated 145 degrees — which the first version of this pin did — asks
    # the wrong question: reversing a straight line is close to flipping it 180
    # degrees, so on that pair the UN-reversed comparison genuinely wins and
    # rev:False is the right answer. The reversal has to be the only difference
    # for the flag to mean anything.
    back = pairing(pose(20), pose(20, reverse_arm=True))
    check("a limb redrawn BACKWARDS pairs with itself, and is flagged reversed",
          [m and m["j"] for m in back] == [0, 1, 2, 3]
          and back[2] and back[2]["rev"] is True,
          f"{back} — without the flag the stroke interpolates end-to-start "
          f"and turns inside out on the way across")
    # WHAT THIS DOES NOT COVER, recorded rather than left to be discovered:
    # it pins the FLAG, not the use of it. A mutation that computes the flag
    # correctly and then ignores it downstream passes, because every stroke in
    # this fixture is straight — reversing a straight line interpolates it
    # along itself, which looks identical. Catching that needs a curved stroke,
    # and no fixture here has one.

    # A 4px mark and a scrawl across the whole page: nothing about them is the
    # same stroke, and the length guard is what says so.
    junk = page.evaluate("""() => ({
      strokes: [{x:10,y:10,size:6,color:'#fff',erase:false,t:0,start:true},
                {x:13,y:13,size:6,color:'#fff',erase:false,t:1}],
      strokeGroups: [2], hold: 1 })""")
    scrawl = page.evaluate("""() => ({
      strokes: [{x:300,y:300,size:6,color:'#fff',erase:false,t:0,start:true},
                {x:20,y:290,size:6,color:'#fff',erase:false,t:1},
                {x:295,y:20,size:6,color:'#fff',erase:false,t:2},
                {x:30,y:30,size:6,color:'#fff',erase:false,t:3}],
      strokeGroups: [4], hold: 1 })""")
    # AND NOTHING PAIRS WITH ANYTHING: the pin that stops "pair everything"
    # from satisfying all of the above.
    nothing = pairing(junk, scrawl)
    check("a 4px mark pairs with nothing on a page-wide scrawl",
          nothing == [None], str(nothing))

    # THE PAGE SAYS WHAT IT DID. Reported with a picture: a generated page that
    # "is just a copy of slide 1" — which is exactly what a smear looks like
    # when nothing travelled far enough to leave a trail, and the chip said
    # "Motion smear added" either way. There was no way for the artist, or for
    # me reading the screenshot, to tell a working smear of a small motion from
    # a page with nothing to smear.
    print("\nWHAT THE PAGE SAYS IT DID")
    said = smear(pose(20), pose(-125))
    check("a smear that moved one stroke says so, and says what it kept",
          said["chip"] and "1 stroke moved" in said["chip"]
          and "drawn once" in said["chip"], repr(said["chip"]))
    same = smear(pose(20), pose(20))
    check("two pages that look the same say THAT, rather than 'added'",
          same["chip"] and "nothing moved far enough" in same["chip"].lower(),
          f"{same['chip']!r} — a page that looks like a copy of the one before "
          f"it needs to say why, or it reads as the tool being broken")

    # ---------------------------------------------------------------- v299
    # UNDO TAKES THE PAGE BACK, AND THE CARVE WITH IT.
    #
    # addTween inserted a page and cleared the redo stack but never wrote to
    # actionLog, so undoStroke fell through to its generic tail — which pops the
    # last stroke GROUP off the current page, and after `idx++` the current page
    # is the generated one. Undo silently ate the crisp pose and left the trail
    # behind it, while the chip still read "Motion smear added". The note at
    # flip.js's matcher justifies a known mispairing risk with the words "undo
    # is one tap"; this is what made that true.
    #
    # PAGE COUNT IS THE DISCRIMINATOR, not the point count. A mutation that
    # removes the page but forgets the carve leaves the document running at
    # double fps with one page missing, so fps/subdiv/holds are asserted too —
    # they are the half of the action that has no visible page to notice.
    print("\nUNDO — a generated page is one action, not a stroke")

    def gen_undo(a, b, fn):
        return page.evaluate("""([a,b,fn]) => {
          frames.length = 0; frames.push(a); frames.push(b);
          idx = 0; fps = 12; subdiv = 1; selSpans = [];
          actionLog.length = 0; redoStack.length = 0;
          buildStrip(); render();
          const snap = () => ({ pages: frames.length, idx: idx, fps: fps,
                                subdiv: subdiv, holds: frames.map(f => f.hold),
                                groups: frames[idx] ? frames[idx].strokeGroups.length : -1 });
          window[fn]();
          const added = snap();
          undoStroke();
          const undone = snap();
          redoStroke();
          return { added: added, undone: undone, redone: snap(),
                   chip: (document.getElementById('flipChip')||{}).textContent };
        }""", [a, b, fn])

    _u = gen_undo(pose(20), pose(-125), "addTween")
    check("a smear is added as ONE action, and undo takes the page away",
          _u["added"]["pages"] == 3 and _u["undone"]["pages"] == 2,
          f"added {_u['added']['pages']} pages, undo left {_u['undone']['pages']} — "
          f"undo used to pop a stroke group off the generated page instead, "
          f"deleting the pose and keeping the trail")
    check("...and puts the carve back with it",
          _u["undone"]["fps"] == 12 and _u["undone"]["subdiv"] == 1
          and _u["undone"]["holds"] == [1, 1],
          f"{_u['undone']} — carving for the insert doubled fps and every hold; "
          f"removing the page without those leaves the document faster than the "
          f"artist left it")
    check("...and the page the artist was on is the one they land on",
          _u["undone"]["idx"] == 0, str(_u["undone"]["idx"]))
    check("...and redo restores the page AND the carve exactly",
          _u["redone"] == _u["added"],
          f"{_u['redone']} vs {_u['added']}")

    # ---------------------------------------------------------------- v299
    # A STROKE THAT MOVED, DECLARED STILL BECAUSE IT WAS DRAWN CAREFULLY.
    #
    # tweenHeldStill decides whether a paired stroke is smeared or carried
    # across once at full strength, and it walked `i < min(a.length, b.length)`
    # while computing its parameter as `i / (a.length - 1)`. With a denser than
    # b the loop ended long before the parameter reached 1, so it compared the
    # LEADING FRACTION of a and called the rest of the stroke unexamined.
    #
    # Measured here: one pose taken slowly (400 points) and the next taken fast
    # (4 points), the arm swung 40 degrees so its tip travels 68px against a 6px
    # brush. The old measure compared 1% of the arc, found 0.4px of movement and
    # sent the arm to `still` -- drawn ONCE, no trail, while the body beside it
    # smeared normally. The motion the button exists to show is the motion it
    # dropped, and it dropped it silently.
    #
    # THE FIXTURE'S TWO STROKES ARE 100px AND 500px, more than the 4x the
    # matcher's length guard allows, so they cannot cross-pair. That keeps this
    # an assertion about the still/moved measure and not about the matcher.
    #
    # ANGULAR SPREAD, NOT SAMPLE COUNT, is what makes this go red: a dropped arm
    # and a smeared one both put ink on the page, and both leave the strokeGroup
    # count identical. What separates them is that a smear lays the arm down at
    # a range of angles. Measured: 0 faded copies spanning 0 degrees before,
    # 3 spanning 15 after.
    print("\nA CAREFULLY DRAWN STROKE THAT MOVED — it is not 'still'")

    _dense = page.evaluate("""() => {
      const seg = (x0,y0,x1,y1,n) => { const pts = [];
        for (let i = 0; i < n; i++) { const t = i/(n-1);
          pts.push({ x: x0+(x1-x0)*t, y: y0+(y1-y0)*t, color: '#ffffff',
                     size: 6, t: i, erase: false }); }
        pts[0].start = true; return pts; };
      const arm = (deg, n) => seg(300, 200,
        300 + 100*Math.cos(deg*Math.PI/180), 200 + 100*Math.sin(deg*Math.PI/180), n);
      const body = (dx) => seg(300+dx, 220, 300+dx, 720, 60);
      const mk = (runs) => ({ strokes: [].concat(...runs),
                              strokeGroups: runs.map(r => r.length), hold: 1 });
      frames.length = 0;
      frames.push(mk([body(0),  arm(0, 400)]));     // taken slowly
      frames.push(mk([body(40), arm(40, 4)]));      // taken fast
      idx = 0; fps = 12; subdiv = 1; selSpans = [];
      actionLog.length = 0; redoStack.length = 0;
      buildStrip(); render();
      const before = frames.length;
      addTween();
      if (frames.length <= before) return { made: false };
      // Every copy of the ARM on the generated page, by arc length, with the
      // alpha that says whether it is a smear sample or ink carried across.
      const fr = frames[1]; let at = 0, faded = 0, solid = 0; const angles = [];
      for (const g of fr.strokeGroups) {
        const r = fr.strokes.slice(at, at + g); at += g;
        let L = 0;
        for (let i = 1; i < r.length; i++) L += Math.hypot(r[i].x-r[i-1].x, r[i].y-r[i-1].y);
        if (L >= 200) continue;                     // the body, not the arm
        const c = String(r[0].color || '');
        const alpha = (c.length === 9 && c[0] === '#') ? parseInt(c.slice(7,9),16)/255 : 1;
        if (alpha < 1) faded++; else solid++;
        angles.push(Math.atan2(r[r.length-1].y - r[0].y, r[r.length-1].x - r[0].x) * 180/Math.PI);
      }
      return { made: true, faded: faded, solid: solid,
               spread: angles.length ? Math.max(...angles) - Math.min(...angles) : 0 };
    }""")

    check("the fixture smeared at all", _dense.get("made") is True, str(_dense))
    check("a stroke drawn at 400 points and redrawn at 4 is still SMEARED",
          _dense.get("faded", 0) >= 1,
          f"{_dense} — every copy of the arm is at full strength, so it was "
          f"declared held still and carried across once. It swung 40 degrees")
    check("...and the smear spans the angles it swung through",
          _dense.get("spread", 0) >= 5,
          f"spread {_dense.get('spread')}deg — ink on the page is not a smear; "
          f"a dropped arm and a smeared one both leave the group count alone, "
          f"and only the spread of angles tells them apart")

    # THE PROPERTY UNDERNEATH BOTH SCENARIOS, pinned directly: the verdict is
    # about the drawing, so it cannot depend on how either page was sampled --
    # nor on which of the two the caller named first, which is the form the
    # defect actually took.
    #
    # AND THE SECOND HALF IS NOT REDUNDANT — it is the one that was WRITTEN
    # SECOND, because the first fix for this defect failed it. Walking both
    # strokes over the whole arc and by a shared parameter, but reading each at
    # the nearest VERTEX to that parameter, makes the quantisation the answer:
    # on the 200px line below, 4 vertices against 512 land up to 33px apart on
    # a stroke nobody touched. Measured on exactly that version, against
    # exactly these two assertions: 0 of 81 asymmetric, and 42 of 81 identical
    # gestures reported MOVED. Everything else in both suites stayed green,
    # including the scenarios above -- this check is the whole of what stands
    # between the tree and a fix that trades one sampling artifact for another.
    _prop = page.evaluate("""() => {
      const line = (n, deg) => { const o = [];
        for (let i = 0; i < n; i++) { const t = i/(n-1);
          o.push({ x: 100 + 200*t*Math.cos(deg*Math.PI/180),
                   y: 100 + 200*t*Math.sin(deg*Math.PI/180), size: 6 }); }
        return o; };
      let pairs = 0, asym = 0, copies = 0, copyMoved = 0;
      for (let na = 2; na <= 512; na *= 2) for (let nb = 2; nb <= 512; nb *= 2) {
        pairs++;
        // The same gesture at two densities: nothing moved, whatever the counts.
        copies++;
        if (!tweenHeldStill(line(na, 0), line(nb, 0))) copyMoved++;
        // And a real 30-degree swing, asked both ways round.
        if (tweenHeldStill(line(na, 0), line(nb, 30))
            !== tweenHeldStill(line(nb, 30), line(na, 0))) asym++;
      }
      return { pairs: pairs, asym: asym, copies: copies, copyMoved: copyMoved };
    }""")
    check("the still/moved verdict does not depend on argument order",
          _prop["asym"] == 0,
          f"{_prop['asym']} of {_prop['pairs']} density pairs answered "
          f"differently when the two pages were swapped — the same two poses, "
          f"a different answer depending on which one the caller passed first")
    check("...nor on how densely either pose was recorded",
          _prop["copyMoved"] == 0,
          f"{_prop['copyMoved']} of {_prop['copies']} identical gestures were "
          f"called MOVED because the two recordings hold different point counts. "
          f"Geometry describes the drawing; sampling describes how we observed it")

    # ---------------------------------------------------------------- v299
    # WHERE IN TIME THE SMEAR LANDS — and this is the smear's OWN assertion,
    # not a copy of the in-between's, because carveForInsert reports the slots
    # it freed and each button spends them at its own call site. Both said
    # `t.hold = 1` and both had to stop. Mutated one at a time: fixing either
    # caller alone leaves the other's sweep red.
    #
    # The carve took ONE slot off the pose however long the pose was held, which
    # is the evenest cut available at hold 2 and 3 and not above them. The badge
    # offers x4 directly, so a hold of 4 is one tap away on a fresh document: at
    # 12fps its smear landed 250ms into a 333ms interval instead of 167ms, and
    # at x8, 583 of 667.
    #
    # SWEPT, NOT SAMPLED: at hold 2 and 3 "take a slot" and "take half" agree,
    # and those are the holds every other fixture here uses. Only the sweep
    # separates the two rules.
    print("\nTHE CARVE — a smear has to land in the middle of the interval")

    _csw = page.evaluate("""() => {
      const seg = (y) => { const o = [];
        for (let i = 0; i < 10; i++)
          o.push({ x: 100 + i*15, y: y, color: '#ffffff', size: 6, t: 0, erase: false });
        o[0].start = true; return o; };
      const mk = (y, h) => ({ strokes: seg(y), strokeGroups: [10], hold: h });
      const rows = [];
      for (let H = 1; H <= 8; H++) {
        // The stroke MOVES 220px, so a refusal cannot be mistaken for a split.
        frames.length = 0; frames.push(mk(200, H)); frames.push(mk(420, 1));
        idx = 0; fps = 12; subdiv = 1; selSpans = [];
        actionLog.length = 0; redoStack.length = 0;
        buildStrip(); render();
        const before = frames.length;
        addTween();
        if (frames.length <= before) { rows.push({ H: H, made: false }); continue; }
        rows.push({ H: H, made: true, pose: frames[0].hold, gen: frames[1].hold,
                    was: H * (subdiv || 1) });
      }
      return rows;
    }""")
    _coff = [r for r in _csw if not r["made"] or abs(r["pose"] - r["gen"]) > 1]
    check("the smear lands at the middle of the interval at EVERY hold",
          not _coff,
          "; ".join(f"hold {r['H']} -> {r.get('pose')}:{r.get('gen')}" for r in _coff)
          + " — one slot off the pose centres it only while the pose is held 2 "
            "or 3, and the badge offers x4")
    _csum = [r for r in _csw if r["made"] and r["pose"] + r["gen"] != r["was"]]
    check("...without the pair occupying more than the pose did alone",
          not _csum,
          "; ".join(f"hold {r['H']} -> {r['pose']}+{r['gen']} against {r['was']}"
                    for r in _csum)
          + " — green under the old rule and the new one alike: both spend "
            "exactly what the pose held. What reddens it is a HALF-APPLIED fix "
            "— measured, with carveForInsert splitting and this caller still "
            "writing a hard 1, the pair came out shorter than the pose had been "
            "and every page after it moved")

    # ---------------------------------------------------------------- v299
    # THE SMEAR DIES ON A ZERO GROUP TOO, and separately.
    #
    # Same defect, its own call site: a group is a stroke's point count and must
    # be strictly positive, healFrame's only test was that the entries SUM to
    # the point count, and [0, 10] sums like [10]. tweenShapeCost then read
    # r[0].x of the empty run. verify_inbetween pins the gate and the In-between
    # button; this pins Motion Smear, because the two buttons are two call sites
    # and a fix to one is not a fix to the other -- which is exactly how the
    # generated-page undo turned out to need an assertion on each.
    print("\nA ZERO GROUP — the smear survives one too")

    _z = page.evaluate("""() => {
      const line = (y, n) => { const o = [];
        for (let i = 0; i < n; i++) o.push({ x: 100 + i*15, y: y, size: 6,
          color: '#ffffff', erase: false, t: 0, ...(i === 0 ? {start:true} : {}) });
        return o; };
      // The stroke MOVES between the pages, so there is something to smear and
      // a refusal cannot be mistaken for surviving.
      const mk = (y) => ({ strokes: line(y, 10), strokeGroups: [0, 10], hold: 1 });
      frames.length = 0; frames.push(mk(200)); frames.push(mk(420));
      idx = 0; fps = 12; subdiv = 1; selSpans = [];
      actionLog.length = 0; redoStack.length = 0;
      buildStrip(); render();
      const before = frames.length;
      let threw = null;
      try { addTween(); } catch (e) { threw = e.constructor.name + ': ' + e.message; }
      return { threw: threw, made: frames.length > before,
               chip: (document.getElementById('flipChip') || {}).textContent };
    }""")
    check("a zero group does not kill Motion Smear",
          _z["threw"] is None and _z["made"] is True,
          f"threw {_z['threw']!r}, made={_z['made']} — an uncaught TypeError "
          f"here leaves the button dead with nothing said")
    check("...and it still produces a smear, not a refusal",
          bool(_z["chip"]) and "nothing moved" not in (_z["chip"] or "").lower(),
          f"{_z['chip']!r} — the stroke travels 220px, so a refusal would mean "
          f"the empty run had eaten the motion rather than the button")

    check("no uncaught error across the whole session", not errs, "; ".join(errs[:3]))
    browser.close()

bad = [r for r in results if not r[0]]
print(f"\n{'=' * 62}\n{len(results) - len(bad)}/{len(results)} passed"
      + ("" if not bad else "  FAILURES: " + ", ".join(n for _, n in bad)))
sys.exit(1 if bad else 0)
