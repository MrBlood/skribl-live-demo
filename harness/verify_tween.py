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

    print("\nIN-BETWEEN — it refuses rather than guessing")
    page.evaluate("""() => {
      frames.length = 0;
      frames.push({ strokes: [{x:10,y:10,color:'#fff',size:6,t:0,erase:false,start:true},
                              {x:90,y:90,color:'#fff',size:6,t:1,erase:false}],
                    strokeGroups: [2], hold: 1 });
      frames.push({ strokes: [{x:10,y:10,color:'#fff',size:6,t:0,erase:false,start:true},
                              {x:50,y:50,color:'#fff',size:6,t:1,erase:false},
                              {x:90,y:90,color:'#fff',size:6,t:2,erase:false}],
                    strokeGroups: [3], hold: 1 });
      idx = 0; buildStrip(); render();
    }""")
    page.evaluate("() => addTween()")
    page.wait_for_timeout(300)
    check("two pages that do NOT correspond produce no page",
          page.evaluate("() => frames.length") == 2,
          "inventing a pairing would produce a mess that reads as a bug in the "
          "tool rather than a limit of the idea")
    check("...and the refusal says what is needed",
          "same strokes" in (page.evaluate(
              "() => (document.getElementById('flipChip')||{}).textContent") or ""),
          page.evaluate("() => (document.getElementById('flipChip')||{}).textContent"))

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
        check("every width is a multiple of the brush, none below it",
              all(sz >= blur["base"] - 1e-6 for sz in blur["sizes"]),
              str(blur["sizes"]))
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
