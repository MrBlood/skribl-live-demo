"""The in-between: ONE pose partway, not the whole path at once.

WHAT THIS PINS THAT verify_tween DOES NOT. Motion Smear and the in-between share
a resampler and a refusal and nothing else. Motion Smear's suite protects the
UNEVEN SMEAR — the property of integrating every instant between two poses.
This one protects the opposite property: that a single instant comes out looking
like a drawing somebody could have made.

AND IT PINS THE PROPERTY, NOT THE IMPLEMENTATION. "Does the animation look
right" is not a thing Playwright can assert, and pretending otherwise is how a
suite ends up protecting an algorithm instead of an outcome. What CAN be
measured is the handful of geometric invariants that a visibly-melted in-between
always violates, and each assertion below was measured failing before the code
that makes it pass was written:

    a closed shape's perimeter through the middle  -13.2% -> -1.7%  (phase)
    a swinging limb's length through the middle    -18.1% ->  0.0%  (similarity)
    points on the generated page                    5,184 ->    64  (one pose)

Each number is the real before-and-after from the bake-off the feature was
designed against, and each is the difference between a drawing and a mess.

AND ONE OF THEM WAS WRONG FIRST, which is the more useful record. The closed
path started as two circles begun half a turn apart -- the case where index
pairing collapses the drawing to a single dot, so it looked like the harshest
fixture available. It passed with the phase search deleted. A circle is the one
closed shape where a phase offset IS a rotation, and the similarity fit models
rotation exactly, so it repaired the phase error as a side effect and the
assertion pinned nothing. The fixture is a loop with no rotational symmetry now,
and the measure is perimeter rather than radius, because radius did not move
either (2.2% against 2.3%) while perimeter moved 1.7% against 13.2%.

THE CASE THIS DELIBERATELY DOES NOT PIN is a pose redrawn with its strokes in a
different ORDER. Pairing is by drawing order, as Motion Smear's is, and no
assertion here claims otherwise: a matcher is a separate job. What is pinned is
that the Help says so.
"""

import os
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


# A CLOSED PATH HAS NO FIRST POINT, which is the whole of this fixture: the same
# loop on both pages, begun half way round on the second. Paired by index, every
# point meets one on the far side of the shape.
#
# AND IT IS DELIBERATELY NOT A CIRCLE. The first version of this fixture was two
# circles begun half a turn apart, which looks like the harshest possible case --
# every point meets its antipode and the drawing collapses to a single dot. It
# cannot tell the two mechanisms apart. On a circle a phase offset IS a rotation,
# and the similarity fit models rotation exactly, so it repairs the phase error
# as a side effect and the assertion passed with the phase search deleted.
# Measured on a loop with no rotational symmetry, where a phase offset is not any
# rigid motion: perimeter holds to -1.7% with the phase search and falls -13.2%
# without it.
LOOP = """(phase) => {
  const mk = (cx, start) => {
    const pts = [], N = 60;
    for (let i = 0; i <= N; i++) {
      const a = start + (i / N) * Math.PI * 2;
      const r = 60 + 14 * Math.sin(3 * a) + 8 * Math.cos(5 * a);
      pts.push({ x: cx + Math.cos(a) * r, y: 300 + Math.sin(a) * r,
                 color: '#ffffff', size: 6, t: i, erase: false });
    }
    pts[0].start = true;
    return { strokes: pts, strokeGroups: [pts.length], hold: 1 };
  };
  frames.length = 0;
  frames.push(mk(200, 0));
  frames.push(mk(400, phase));
  idx = 0; buildStrip(); render();
}"""

# A limb rotating about a fixed shoulder. Interpolating its vertices one by one
# walks each down a straight line, so the limb cuts the chord of its own arc and
# comes out SHORT — visibly shrinking through the middle of the swing.
LIMB = """(deg) => {
  const mk = (d) => {
    const a = d * Math.PI / 180, pts = [];
    for (let i = 0; i <= 10; i++) {
      const r = 20 + i * 12;
      pts.push({ x: 300 + Math.cos(a) * r, y: 200 + Math.sin(a) * r,
                 color: '#ffffff', size: 6, t: i, erase: false });
    }
    pts[0].start = true;
    return { strokes: pts, strokeGroups: [pts.length], hold: 1 };
  };
  frames.length = 0;
  frames.push(mk(0));
  frames.push(mk(deg));
  idx = 0; buildStrip(); render();
}"""

# Perimeter. A shape blended with a shifted copy of itself cuts its own corners
# and comes out shorter, which mean radius does not see: measured, radius moved
# 2.2% -> 2.3% between a correct and a wrongly-phased midpoint while perimeter
# moved 1.7% -> 13.2%. Measure the thing that actually moves.

LENGTH = """(f) => {
  const pts = frames[f].strokes;
  let L = 0;
  for (let i = 1; i < pts.length; i++)
    L += Math.hypot(pts[i].x - pts[i-1].x, pts[i].y - pts[i-1].y);
  return L;
}"""

# Two identical pages, built fresh, so the last-page test owns its own state.
ONE_PAIR = """() => {
  const one = { strokes: [
    { x: 100, y: 100, color: '#ffffff', size: 6, t: 0, erase: false, start: true },
    { x: 200, y: 200, color: '#ffffff', size: 6, t: 1, erase: false }],
    strokeGroups: [2], hold: 1 };
  frames.length = 0;
  frames.push(one, JSON.parse(JSON.stringify(one)));
  idx = 0; buildStrip(); render();
}"""


with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1100, "height": 900})
    errs = []
    page.on("pageerror", lambda e: errs.append(str(e)))
    browsing.goto(page, BASE, "/flip")

    print("IN-BETWEEN — one pose, inserted between two")
    check("Flip booted", page.evaluate("() => !!(window.__skriblBoot && window.__skriblBoot.flip)"),
          "; ".join(errs[:2]))

    # The control. Named separately from Motion Smear's because they are two
    # features, and read from the DOM rather than from the source that writes it.
    btn = page.evaluate("""() => {
      const el = document.getElementById('addinbetween');
      if (!el) return null;
      return { label: (el.textContent || '').trim(), title: el.title || '' }; }""")
    check("the filmstrip carries an In-between control", bool(btn), "no #addinbetween")
    check("...labelled In-between", bool(btn) and btn["label"] == "In-between", str(btn))
    check("...and it is not the smear wearing the name",
          bool(btn) and "exposure" not in btn["title"].lower()
          and "smear" not in btn["title"].lower(), str(btn))

    print("\nA CLOSED PATH: the shape has to survive the middle")
    page.evaluate(LOOP, 3.14159265358979)         # begun half way round
    r_src = page.evaluate(LENGTH, 0)
    page.evaluate("() => addInbetween()")
    page.wait_for_timeout(300)
    check("a page was inserted BETWEEN the two poses",
          page.evaluate("() => frames.length") == 3
          and page.evaluate("() => idx") == 1,
          str(page.evaluate("() => ({ n: frames.length, idx })")))
    r_mid = page.evaluate(LENGTH, 1)
    # -13.2% is what index pairing produces here: the loop is averaged with the
    # far side of itself and the contour caves in. The -1.7% the aligned one
    # spends is arc-length resampling, which every path through this code pays.
    check("the closed shape keeps its perimeter through the middle",
          abs(r_mid - r_src) / r_src < 0.05,
          f"{r_mid:.1f}px against the drawn {r_src:.1f}px "
          f"({100 * (r_mid - r_src) / r_src:+.1f}%) — pairing by index across a "
          f"phase offset averages the loop with the far side of itself")
    check("...and it is still ONE stroke, not a scribble",
          page.evaluate("() => frames[1].strokeGroups.length") == 1,
          str(page.evaluate("() => frames[1].strokeGroups")))

    print("\nA SWINGING LIMB: it has to keep its length")
    page.evaluate(LIMB, 70)
    l_src = page.evaluate(LENGTH, 0)
    page.evaluate("() => addInbetween()")
    page.wait_for_timeout(300)
    l_mid = page.evaluate(LENGTH, 1)
    # Measured at -18.1% before the similarity fit: the limb visibly shortens at
    # the middle of its own swing, which reads as the drawing being damaged
    # rather than as motion.
    check("the limb keeps its length through the middle of a 70-degree swing",
          abs(l_mid - l_src) / l_src < 0.02,
          f"{l_mid:.1f}px against the drawn {l_src:.1f}px "
          f"({100 * (l_mid - l_src) / l_src:+.1f}%) — walking each vertex down a "
          f"straight line cuts the chord of the arc")
    # Halfway means halfway: the far end should sit near the bisector, not at
    # either pose. Without this, "keeps its length" would also pass on a pose
    # that simply copied A.
    ang = page.evaluate("""() => {
      const e = frames[1].strokes[frames[1].strokes.length - 1];
      return Math.atan2(e.y - 200, e.x - 300) * 180 / Math.PI; }""")
    check("...and it is genuinely halfway round, not a copy of either pose",
          abs(ang - 35) < 6, f"{ang:.1f} degrees, wanted about 35")

    print("\nIT IS ONE POSE, AND THAT IS WHAT MAKES IT CHEAP")
    src_pts = page.evaluate("() => frames[0].strokes.length")
    mid_pts = page.evaluate("() => frames[1].strokes.length")
    check("the generated page is about one source page, not a multiple of it",
          mid_pts <= src_pts * 1.2 + 4,
          f"{mid_pts} points against a source page of {src_pts}")
    # The contrast is the point of the feature existing separately: the same two
    # poses through Motion Smear are the whole path, many times over.
    page.evaluate("() => { frames.splice(1, 1); idx = 0; buildStrip(); render(); }")
    page.evaluate("() => addTween()")
    page.wait_for_timeout(300)
    smear_pts = page.evaluate("() => frames[1].strokes.length")
    # INVERTED IN v297. This asserted that a smear of the same motion is MANY
    # TIMES heavier than an in-between -- which was true, and was the defect.
    # A smear is now a lead pose plus a few coarse ghosts, so the two are close
    # by construction, and the old pin could only go green again by putting the
    # 6,960-point exposure back. CLAUDE.md names this shape: an assertion that
    # can only pass while the work is outstanding is a TODO in a test's
    # clothing. Guarding the ground instead -- a smear costs a small multiple of
    # the pose it is built around, and going back to an exposure fails here.
    check("...and the smear of the same motion costs a small multiple of it",
          smear_pts <= mid_pts * 4,
          f"smear {smear_pts} against in-between {mid_pts} — a smear that "
          f"costs several times a pose is an exposure again")

    print("\nWHAT IT REFUSES, AND WHAT IT SAYS")
    page.evaluate("""() => {
      const one = { strokes: [
        { x: 100, y: 100, color: '#ffffff', size: 6, t: 0, erase: false, start: true },
        { x: 200, y: 200, color: '#ffffff', size: 6, t: 1, erase: false }],
        strokeGroups: [2], hold: 1 };
      const two = { strokes: [
        { x: 100, y: 100, color: '#ffffff', size: 6, t: 0, erase: false, start: true },
        { x: 200, y: 200, color: '#ffffff', size: 6, t: 1, erase: false },
        { x: 300, y: 100, color: '#ffffff', size: 6, t: 2, erase: false, start: true },
        { x: 350, y: 200, color: '#ffffff', size: 6, t: 3, erase: false }],
        strokeGroups: [2, 2], hold: 1 };
      frames.length = 0; frames.push(one, two); idx = 0; buildStrip(); render(); }""")
    page.evaluate("() => addInbetween()")
    # INVERTED IN v296, for the same reason as its twin in verify_tween: this
    # asserted that a different NUMBER of strokes is refused, which was the
    # wall the owner hit on every hand-drawn pose. Strokes pair by shape now
    # and one with no partner is carried rather than guessed at, so the pin
    # guards the achievement instead of remembering the limitation.
    check("a different number of strokes now produces a pose",
          page.evaluate("() => frames.length") == 3,
          "the count wall is what v296 removed; refusing here is the old "
          "behaviour, not a safety net")
    msg = page.evaluate("() => (document.getElementById('flipChip')||{}).textContent") or ""
    check("...and nothing refuses on the count any more",
          "number of strokes" not in msg.lower(), repr(msg))

    # ITS OWN STATE, not whatever the block above left behind. That block used
    # to leave two frames and this one relied on it; now that it leaves three,
    # "go to the last page" landed on a page that HAS a next one and an
    # in-between was added where a refusal was expected. A test that depends on
    # its predecessor's leftovers is measuring the predecessor.
    page.evaluate(ONE_PAIR)
    page.evaluate("() => { go(frames.length - 1); }")
    _n = page.evaluate("() => frames.length")
    page.evaluate("() => addInbetween()")
    page.wait_for_timeout(300)
    msg = page.evaluate("() => (document.getElementById('flipChip')||{}).textContent") or ""
    check("on the last page it explains there is no next pose",
          page.evaluate("() => frames.length") == _n and "BETWEEN" in msg, repr(msg))

    print("\nORDINARY STROKE DATA — the player has learned nothing new")
    page.evaluate(LIMB, 70)
    page.evaluate("() => addInbetween()")
    page.wait_for_timeout(300)
    shape = page.evaluate("""() => {
      const f = frames[1], allowed = ['x','y','color','size','t','erase','start'];
      const bad = new Set();
      for (const s of f.strokes) for (const k of Object.keys(s))
        if (!allowed.includes(k)) bad.add(k);
      const total = f.strokeGroups.reduce((a, b) => a + b, 0);
      return { bad: [...bad], groupsSumToStrokes: total === f.strokes.length,
               starts: f.strokes.filter(s => s.start).length,
               colors: [...new Set(f.strokes.map(s => s.color))] }; }""")
    check("no point carries a field outside the stroke schema",
          not shape["bad"], ", ".join(shape["bad"]))
    check("strokeGroups accounts for every point",
          shape["groupsSumToStrokes"], str(shape))
    check("exactly one start per run, so the server does not reject the page",
          shape["starts"] == 1, str(shape))
    # A halfway COLOUR is a colour the artist never picked. Geometry is what is
    # being interpolated; style holds.
    check("the colour is held rather than blended into a third colour",
          shape["colors"] == ["#ffffff"], str(shape["colors"]))

    print("\nTHE HELP SAYS WHAT IT CANNOT DO")
    help_txt = page.evaluate("""() => {
      const tips = [...document.querySelectorAll('.help-tip')];
      const t = tips.find(e => (e.querySelector('.help-pill')||{}).textContent === 'In-between');
      return t ? t.textContent.replace(/\\s+/g, ' ') : null; }""")
    check("the Help has an In-between entry of its own", bool(help_txt), "no tip found")
    check("...and it names drawing ORDER as the thing to keep",
          bool(help_txt) and "order" in help_txt.lower(),
          (help_txt or "")[-200:] + " — pairing is by drawing order and a "
          "redrawn pose in another order pairs wrongly; the Help is the only "
          "place that can say so")
    check("...and it points at Motion Smear for the whole path",
          bool(help_txt) and "motion smear" in help_txt.lower(),
          (help_txt or "")[-200:])

    # ---------------------------------------------------------------- v296
    # AN ERASED PAGE IS THE SAME PAGE TO BOTH BUTTONS.
    #
    # tweenMismatch counts visible ink since v296, and buildInbetween read
    # tweenRuns — so the guard passed on 2 while the loop walked 4, pairing
    # the replacement's partner against the stroke it replaced and indexing
    # past the end of the other page when the erased page came first. Both
    # readings of "the strokes of this page" have to be the same reading.
    print("\nERASED PAGES — the in-between pairs the ink, like the smear")
    ERASED = """(order) => {
      const run = (x0,y0,x1,y1,n,erase,size) => { const o=[];
        for(let i=0;i<=n;i++) o.push({ x:x0+(x1-x0)*i/n, y:y0+(y1-y0)*i/n,
          size: size||6, color:'#ffffff', erase: !!erase, t:0 }); return o; };
      const mk = runs => { const f={strokes:[],strokeGroups:[],hold:1};
        runs.forEach(r => { r.forEach((q,i)=>{ const c={...q};
          if(i===0) c.start=true; else delete c.start; f.strokes.push(c); });
          f.strokeGroups.push(r.length); }); return f; };
      const clean  = mk([ run(120,60,120,300,10), run(60,260,200,140,10) ]);
      const erased = mk([ run(120,70,120,310,10), run(70,250,210,130,10),
                          run(68,252,212,128,24,true,30), run(64,242,216,138,10) ]);
      // ORDER MATTERS to the bug: with the erased page FIRST the old code
      // walked four runs against two and read rb[2] as undefined.
      frames.length = 0;
      frames.push(order === 'erasedFirst' ? erased : clean);
      frames.push(order === 'erasedFirst' ? clean : erased);
      idx = 0; actionLog.length = 0; redoStack.length = 0;
      buildStrip(); render();
      let out = null, threw = null;
      try { out = buildInbetween(frames[0], frames[1], 0.5); }
      catch (e) { threw = String(e); }
      return { threw: threw, groups: out ? out.strokeGroups.length : null,
               points: out ? out.strokes.length : null,
               erasePoints: out ? out.strokes.filter(q => q.erase).length : null };
    }"""
    for order in ("cleanFirst", "erasedFirst"):
        r = page.evaluate(ERASED, order)
        check(f"an in-between is built with the erased page {order[:-5]}",
              r["threw"] is None and r["groups"] is not None,
              f"threw {r['threw']}; the two readings of the page disagree")
        check(f"...over the TWO strokes you can see, not the four it holds ({order[:-5]})",
              r["groups"] == 2,
              f"{r['groups']} groups in the pose; an eraser or the stroke it "
              f"removed is being interpolated as if it were drawn")
        check(f"...and the pose carries no eraser ({order[:-5]})",
              r["erasePoints"] == 0,
              f"{r['erasePoints']} eraser points in a single generated POSE, "
              f"which is one crisp drawing and has nothing to rub out")

    # THE BUTTON, NOT THE BUILDER, and on pages whose stroke counts differ.
    #
    # buildInbetween pairs index for index. That was safe while tweenMismatch
    # required the two pages to hold the same number of strokes -- and v296
    # REMOVED that requirement, correctly, because pairing by SHAPE made it
    # wrong: the owner draws the next pose by hand and it has a different
    # number of strokes. buildTween got the matcher. addInbetween did not, and
    # called the builder on the raw pages.
    #
    # So adding one stroke to a page shifted every pairing after it -- a line
    # paired with a hexagon, a hexagon with a circle -- and where the first page
    # had MORE runs than the second, rb[s] was undefined and the builder THREW.
    # The owner found it in one drawing: "I added a vertical stroke to slide 1
    # then put an in-between and this?"
    #
    # Driven through addInbetween because that is the surface that was broken;
    # calling buildInbetween directly would pass on a tree with the bug in it.
    _SHAPES = """(which) => {
      const run = (pts) => pts.map((p, i) => ({ x: p[0], y: p[1],
          color: '#ffffff', size: 6, t: i, erase: false, start: i === 0 }));
      const poly = (cx, cy, r, n, rot) => { const o = [];
        for (let i = 0; i <= n; i++) { const a = rot + i * 2 * Math.PI / n;
          o.push([cx + r * Math.cos(a), cy + r * Math.sin(a)]); } return o; };
      const vline = (x, y0, y1) => { const o = [];
        for (let i = 0; i <= 12; i++) o.push([x, y0 + (y1 - y0) * i / 12]);
        return o; };
      const page = (runs) => { const f = { strokes: [], strokeGroups: [], hold: 1 };
        for (const r of runs) { r.forEach(q => f.strokes.push(q));
                                f.strokeGroups.push(r.length); } return f; };
      const hexA = run(poly(220, 300, 70, 6, 0)), cirA = run(poly(430, 330, 60, 24, 0));
      const hexB = run(poly(250, 300, 70, 6, 0.15)), cirB = run(poly(470, 330, 60, 24, 0));
      const line = run(vline(180, 250, 560));
      const A = which === 'extraOnFirst' ? page([line, hexA, cirA]) : page([hexA, cirA]);
      const B = which === 'extraOnSecond' ? page([hexB, cirB, line]) : page([hexB, cirB]);
      frames = [A, B]; idx = 0; fps = 24; subdiv = 1; selSpans = [];
      buildStrip(); render();
      const before = frames.length;
      let threw = null;
      try { addInbetween(); } catch (e) { threw = String(e); }
      if (frames.length === before) return { threw, made: false };
      const g = frames[1];
      /* HOW ROUND IS EACH RUN? A hexagon paired with a hexagon stays a hexagon;
         a hexagon paired with a LINE comes out a slack arc. Corner count is the
         discriminator: the number of vertices where direction turns sharply. */
      const corners = [];
      let at = 0;
      for (let k = 0; k < g.strokeGroups.length; k++) {
        const n = g.strokeGroups[k], seg = g.strokes.slice(at, at + n);
        at += n;
        let turns = 0;
        for (let i = 1; i + 1 < seg.length; i++) {
          const ax = seg[i].x - seg[i-1].x, ay = seg[i].y - seg[i-1].y;
          const bx = seg[i+1].x - seg[i].x, by = seg[i+1].y - seg[i].y;
          const la = Math.hypot(ax, ay), lb = Math.hypot(bx, by);
          if (la < 1e-6 || lb < 1e-6) continue;
          const cos = (ax * bx + ay * by) / (la * lb);
          if (cos < 0.85) turns++;             // a real corner, not a smooth bend
        }
        corners.push(turns);
      }
      return { threw, made: true, runs: g.strokeGroups.length, corners };
    }"""
    for _which, _label in (("extraOnFirst", "a stroke added to the FIRST page"),
                           ("extraOnSecond", "a stroke added to the SECOND page")):
        _r = page.evaluate(_SHAPES, _which)
        check(f"In-between survives {_label}",
              _r["threw"] is None and _r["made"],
              f"threw {_r['threw']}; pairing index for index runs off the end "
              f"of the shorter page")
        # THE TWO DIRECTIONS DIFFER, AND THAT IS THE RULE, NOT A BUG. This
        # check asserted 3 runs both ways on its first run and went red on the
        # second -- and the CHECK was what was wrong.

        # An in-between goes between this page and the next, and the pose is
        # derived from this one. A stroke that exists only on THIS page is
        # drawn once at full strength: it is on the page you are inserting
        # after, so it is on screen at the midpoint. A stroke that exists only
        # on the NEXT page is not drawn: it has not been drawn yet, and the
        # half-way pose is before it exists. Draw both and a stroke appears an
        # instant early; draw neither and one vanishes for a frame.
        _want = 3 if _which == "extraOnFirst" else 2
        check(f"...and keeps the strokes that are on the page ({_which})",
              _r.get("runs") == _want,
              f"{_r.get('runs')} runs in the pose, expected {_want} — a stroke "
              f"with no partner on THIS page is drawn once, not dropped; one "
              f"that exists only on the NEXT page is not drawn yet")
        # THE SHAPES SURVIVE. One hexagon (its corners) and one near-circle
        # (none). Mis-paired, the hexagon melts toward a line and the circle
        # toward a hexagon, and this goes red.
        # THE WHOLE MULTISET, NOT ITS ENDS. This read `_c[-1] >= 5 and
        # _c[0] <= 1` first, and PASSED on the mis-pairing it exists to catch:
        # with the line interpolated toward the hexagon the counts are [0,5,5],
        # whose ends are still 0 and 5. Exactly one cornered run is the claim,
        # so exactly one is what is counted.
        _c = sorted(_r.get("corners") or [])
        _cornered = [n for n in _c if n >= 5]
        _smooth = [n for n in _c if n <= 1]
        check(f"...and each shape is still itself ({_which})",
              len(_c) == _want and len(_cornered) == 1
              and len(_smooth) == _want - 1,
              f"corner counts {_c} — expected exactly ONE cornered run (the "
              f"hexagon) and {_want - 1} smooth"
              + (" (the circle and the straight line)" if _want == 3
                 else " (the circle)")
              + "; a second cornered run is a stroke interpolated toward the "
              + "wrong partner")

    # A GENERATED POSE IS A VALID INPUT TO THE GENERATOR, which is what the
    # owner did -- "an inbetween between an actual stroke and another
    # in-between" -- and it is why his page looked so thoroughly scrambled
    # rather than merely wrong. Chaining does not CAUSE the mis-pairing, but it
    # compounds it: the generated page carries the wrong pairing forward, and
    # the next in-between pairs wrongly again. Measured on the tree he was
    # using, a hexagon and a circle against a page with one stroke added:
    #
    #   step 1   hexagon -> a 13-point run with NO corners (melted to the line)
    #            circle  -> a 25-point run with 5 (melted to the hexagon)
    #   step 2   the corner counts swap again -- it re-mangles every round
    #
    # Aligned, the chain is stable: step 2 produces the same shape profile as
    # step 1, which is the property pinned here.
    _CHAIN = """() => {
      const run = (pts) => pts.map((p, i) => ({ x: p[0], y: p[1],
          color: '#ffffff', size: 6, t: i, erase: false, start: i === 0 }));
      const poly = (cx, cy, r, n, rot) => { const o = [];
        for (let i = 0; i <= n; i++) { const a = rot + i * 2 * Math.PI / n;
          o.push([cx + r * Math.cos(a), cy + r * Math.sin(a)]); } return o; };
      const vline = (x, y0, y1) => { const o = [];
        for (let i = 0; i <= 12; i++) o.push([x, y0 + (y1 - y0) * i / 12]);
        return o; };
      const page = (runs) => { const f = { strokes: [], strokeGroups: [], hold: 1 };
        for (const r of runs) { r.forEach(q => f.strokes.push(q));
                                f.strokeGroups.push(r.length); } return f; };
      const profile = (f) => { const out = []; let at = 0;
        for (let k = 0; k < f.strokeGroups.length; k++) {
          const n = f.strokeGroups[k], seg = f.strokes.slice(at, at + n); at += n;
          let turns = 0;
          for (let i = 1; i + 1 < seg.length; i++) {
            const ax = seg[i].x - seg[i-1].x, ay = seg[i].y - seg[i-1].y;
            const bx = seg[i+1].x - seg[i].x, by = seg[i+1].y - seg[i].y;
            const la = Math.hypot(ax, ay), lb = Math.hypot(bx, by);
            if (la < 1e-6 || lb < 1e-6) continue;
            if ((ax*bx + ay*by) / (la*lb) < 0.85) turns++;
          }
          out.push(n + ':' + turns);
        } return out.join(','); };
      // The extra stroke sits on the LATER page, the ordering that produces a
      // picture instead of running off the end.
      const A = page([run(poly(220, 300, 70, 6, 0)), run(poly(430, 330, 60, 24, 0))]);
      const C = page([run(vline(180, 250, 560)), run(poly(250, 300, 70, 6, 0.15)),
                      run(poly(470, 330, 60, 24, 0))]);
      frames = [A, C]; idx = 0; fps = 24; subdiv = 1; selSpans = [];
      buildStrip(); render();
      let threw = null;
      try { addInbetween(); } catch (e) { threw = String(e); }
      if (frames.length < 3) return { threw, first: null, again: null };
      const first = profile(frames[1]);
      idx = 0;
      const before = frames.length;
      try { addInbetween(); } catch (e) { threw = threw || String(e); }
      return { threw, first,
               again: frames.length > before ? profile(frames[1]) : null };
    }"""
    _ch = page.evaluate(_CHAIN)
    check("an in-between can be built AGAINST a generated pose",
          _ch["threw"] is None and _ch["again"] is not None,
          f"threw {_ch['threw']}; a generated page has to be a valid input to "
          f"the generator — the owner chains them")
    check("...and chaining is stable, not a fresh mangling each round",
          _ch["first"] is not None and _ch["first"] == _ch["again"],
          f"first pass {_ch['first']}, chained pass {_ch['again']} — the same "
          f"shapes must come back; a changed profile is the pairing shifting "
          f"again on a page that was already generated")

    # ---------------------------------------------------------------- v299
    # UNDO ON AN IN-BETWEEN, WHICH FAILS DIFFERENTLY FROM UNDO ON A SMEAR.
    #
    # Both buttons carried the same defect — neither wrote to actionLog, so
    # undoStroke fell through to its generic tail and popped the last stroke
    # group off the page `idx` had just moved onto. But the VISIBLE outcome
    # differs, so verify_tween's assertion does not cover this one: a smear page
    # holds a pose plus many ghost runs, and losing one group leaves a trail
    # with no head. An in-between page holds ONE crisp pose, so losing its only
    # group leaves a BLANK PAGE in the middle of the flip, and pressing undo
    # again then starts eating the artist's own drawing on the page before.
    # That is the scenario pinned here, on the surface that can produce it.
    # ---------------------------------------------------------------- v299
    # A ZERO STROKE-GROUP KILLED THE BUTTON, SILENTLY.
    #
    # A group is a stroke's point count and must be strictly positive --
    # skribl/validation.py says so at length and enforces it at POST, naming the
    # editors that cannot emit one. healFrame is the gate for the paths the
    # SERVER NEVER SEES: the autosave, a restored draft, a hand-edited .skribl.
    # Its only test was that the entries SUM to the point count, and [0, 10]
    # sums to 10 exactly as [10] does. Downstream, tweenShapeCost reads r[0].x
    # of the empty run that produces, and BOTH generative buttons died on an
    # uncaught TypeError with no chip: a dead button and no reason given.
    #
    # Two assertions because there are two guards, and they are reachable
    # separately. The frame here is pushed STRAIGHT into frames, bypassing
    # healFrame, so the button surviving is tweenVisible's doing; healFrame is
    # measured on its own return value.
    print("\nA ZERO GROUP — healed at the gate, and harmless past it")

    _zero = page.evaluate("""() => {
      const line = (y, n) => { const o = [];
        for (let i = 0; i < n; i++) o.push({ x: 100 + i*15, y: y, size: 6,
          color: '#ffffff', erase: false, t: 0, ...(i === 0 ? {start:true} : {}) });
        return o; };
      const mk = (y) => ({ strokes: line(y, 10), strokeGroups: [0, 10], hold: 1 });
      const healed = healFrame(mk(200));
      frames.length = 0; frames.push(mk(200)); frames.push(mk(320));
      idx = 0; fps = 12; subdiv = 1; selSpans = [];
      actionLog.length = 0; redoStack.length = 0;
      buildStrip(); render();
      const before = frames.length;
      let threw = null;
      try { addInbetween(); } catch (e) { threw = e.constructor.name + ': ' + e.message; }
      return { healed: healed.strokeGroups, healedPts: healed.strokes.length,
               threw: threw, made: frames.length > before,
               chip: (document.getElementById('flipChip') || {}).textContent };
    }""")
    check("healFrame drops a zero group rather than carrying it",
          _zero["healed"] == [10] and _zero["healedPts"] == 10,
          f"{_zero['healed']} over {_zero['healedPts']} points — [0, 10] sums to "
          f"10 exactly as [10] does, so a sum check alone lets it through")
    check("...and a frame that still carries one does not kill the button",
          _zero["threw"] is None and _zero["made"] is True,
          f"threw {_zero['threw']!r}, made={_zero['made']} — the matcher read "
          f"r[0].x of an empty run and the button died with no chip")
    check("...and the page it makes says so",
          bool(_zero["chip"]), f"{_zero['chip']!r}")

    # ---------------------------------------------------------------- v299
    # A SHAPE THAT TURNED IS FITTED AS TURNED.
    #
    # ibPhase picks which rotation of a closed path lines up with pose A. It
    # used to score candidates by raw point distance and hand the winner to
    # ibFit -- backwards, because for a shape that has turned, the pairing whose
    # points land nearest in page coordinates is the one that explains the turn
    # away. An L rotated a half-turn was fitted at 2.8 degrees carrying 44.42px
    # of residual when 180 degrees at 0.00px was available, and the half-way
    # pose came out a melted bean resembling neither end.
    #
    # ASSERT THE FITTED ANGLE, NOT THE PICTURE. Point counts and page sizes are
    # the same either way -- that is precisely how this survived a corpus render
    # -- so the discriminator is what the fit CONCLUDED. A half-turn must read as
    # a half-turn and the residual must go to zero, because for a rigid rotation
    # there is nothing left over once the turn is accounted for.
    print("\nPHASE — the fit is scored after the rotation, not before it")

    _rot = page.evaluate("""() => {
      // An L, and the same L turned a half-turn about its own centre. A closed
      // path, so there is a phase to get wrong.
      const poly = (pts, per) => { const o=[];
        for(let s=0;s<pts.length-1;s++){ const a=pts[s], b=pts[s+1];
          for(let i=(s?1:0);i<=per;i++){ const u=i/per;
            o.push({x:a[0]+(b[0]-a[0])*u, y:a[1]+(b[1]-a[1])*u,
                    size:6, color:'#ffffff', erase:false, t:0}); } }
        return o; };
      const L = poly([[260,300],[450,300],[450,340],[300,340],[300,410],[260,410],[260,300]], 8);
      const spin = (r, cx, cy, ang) => { const c=Math.cos(ang), s=Math.sin(ang);
        return r.map(p => Object.assign({}, p,
          { x: cx + (p.x-cx)*c - (p.y-cy)*s, y: cy + (p.x-cx)*s + (p.y-cy)*c })); };
      const mk = (r) => { const f={strokes:[],strokeGroups:[],hold:1};
        r.forEach((q,i)=>{ const c=Object.assign({},q);
          if(i===0) c.start=true; else delete c.start; f.strokes.push(c); });
        f.strokeGroups.push(r.length); return f; };
      const A = mk(L), B = mk(spin(L, 353, 353, Math.PI));
      const ra = tweenVisible(A).ink, rb = tweenVisible(B).ink;
      const n = Math.max(ra[0].length, rb[0].length);
      const pa = tweenResample(ra[0], n);
      const pb = ibPhase(pa, tweenResample(rb[0], n));
      const T = ibFit(pa, pb);
      const loc = ibUnapply(pb, T);
      let e = 0;
      for(let i=0;i<n;i++) e += Math.hypot(loc[i].x-pa[i].x, loc[i].y-pa[i].y);
      return { deg: Math.abs(T.angle) * 180 / Math.PI, scale: T.scale, resid: e/n };
    }""")
    check("a half-turn is fitted as a half-turn",
          abs(_rot["deg"] - 180) < 1.0,
          f"fitted {_rot['deg']:.2f}° — scored before the fit this reads "
          f"2.8°, and the in-between is a melted bean")
    check("...and a rigid turn leaves nothing to interpolate",
          _rot["resid"] < 0.5 and abs(_rot["scale"] - 1.0) < 0.02,
          f"residual {_rot['resid']:.2f}px, scale {_rot['scale']:.3f} — a shape "
          f"that only turned has no residual; 44px of it is the turn being "
          f"spent on deformation instead")

    # THE OTHER HALF, and the reason residual alone is not the score. A CIRCLE
    # is rotationally symmetric, so every spin of it fits with about the same
    # residual -- there is no "better" correspondence for the fit to find, and
    # scored on residual alone the winner is arbitrary. Measured: a circle whose
    # second pose merely STARTS half a turn round is claimed as a 180-degree
    # rotation. The circle did not spin; the pen began somewhere else on it, and
    # that is the exact case this whole function exists to absorb.
    #
    # The penalty on |angle| is what breaks the tie, and this pin is what keeps
    # it: a future simplification to "just minimise residual" looks right on the
    # half-turn above and silently makes every symmetric shape spin.
    _sym = page.evaluate("""() => {
      const circle = (cx,cy,r,n,a0) => { const o=[];
        for(let i=0;i<=n;i++){ const a=a0 + 2*Math.PI*i/n;
          o.push({x:cx+r*Math.cos(a), y:cy+r*Math.sin(a),
                  size:6, color:'#ffffff', erase:false, t:0}); } return o; };
      const mk = (r) => { const f={strokes:[],strokeGroups:[],hold:1};
        r.forEach((q,i)=>{ const c=Object.assign({},q);
          if(i===0) c.start=true; else delete c.start; f.strokes.push(c); });
        f.strokeGroups.push(r.length); return f; };
      // Same circle, same place. Only where the pen STARTED differs.
      const A = mk(circle(300, 300, 88, 40, 0));
      const B = mk(circle(300, 300, 88, 40, Math.PI));
      const ra = tweenVisible(A).ink, rb = tweenVisible(B).ink;
      const n = Math.max(ra[0].length, rb[0].length);
      const pa = tweenResample(ra[0], n);
      const T = ibFit(pa, ibPhase(pa, tweenResample(rb[0], n)));
      return { deg: T.angle * 180 / Math.PI, closed: ibClosed(pa) };
    }""")
    check("the symmetric-shape fixture really is a closed path",
          _sym["closed"] is True,
          "an open path takes the direction-only branch and pins nothing here")
    check("a circle drawn from a different start point did NOT spin",
          abs(_sym["deg"]) < 30,
          f"fitted {_sym['deg']:.1f}° — every spin of a circle fits equally "
          f"well, so residual alone picks one at random and the in-between "
          f"rotates a shape that never moved")

    # ---------------------------------------------------------------- v300
    # THE PLAINEST THING THE FEATURE DOES, and until now the only one of the
    # corpus's expectations with no assertion behind it: a drawing that MOVED
    # and did nothing else. The half-turn above pins the case with a rotation in
    # it and the circle pins the case with none; neither says where the ink
    # lands, and "lands half way" is the whole promise of a middle pose.
    #
    # An outside review of v299 asked the corpus to state a per-case
    # expectation rather than only a picture. Five of its six were already
    # gated here -- the tap, the erased hole, the timing of the carve, the
    # rigid turn, the density sweep -- and this was the gap.
    #
    # TWO READINGS, BECAUSE THEY FAIL SEPARATELY. Where the ink LANDED is
    # ibApply's business; what the fit CONCLUDED is ibFit's. Measured, with
    # ibApply's centroid lerp removed, the middle pose sits on top of the first
    # one -- 90px out -- and the fit still reads a perfect translation, because
    # nothing about the fit was touched.
    #
    # AND RECORDED AT TWO DENSITIES, because that is what the second reading is
    # for. The same L, one pose taken at four times the samples along two of its
    # arms: identical geometry, different recording. With tweenResample walking
    # by INDEX instead of arc length the even pair is still exact -- it is
    # uniformly sampled, so the two rules agree -- and the lopsided pair reads a
    # 38.7 degree turn, a scale of 0.57 and 122px of residual on a drawing that
    # only slid sideways. One fixture at one density cannot see it.
    print("\nA DRAWING THAT ONLY MOVED lands half way, however it was recorded")

    TRANS = """(lopsided) => {
      // An L, and the same L 180 right and 90 down. Nothing else differs.
      const seg = (a, b, per) => { const o = [];
        for (let i = 0; i <= per; i++) { const u = i / per;
          o.push({ x: a[0] + (b[0]-a[0])*u, y: a[1] + (b[1]-a[1])*u,
                   size: 6, color: '#ffffff', erase: false, t: 0 }); } return o; };
      const L = (dx, dy, lop) => {
        const P = [[200,200],[440,200],[440,260],[300,260],[300,400],[200,400]];
        const out = [];
        for (let s = 0; s < P.length - 1; s++) {
          const per = lop ? (s < 2 ? 48 : 6) : 16;
          const r = seg([P[s][0]+dx, P[s][1]+dy], [P[s+1][0]+dx, P[s+1][1]+dy], per);
          for (let i = (s ? 1 : 0); i < r.length; i++) out.push(r[i]);
        }
        return out; };
      const mk = (r) => { const f = { strokes: [], strokeGroups: [], hold: 1 };
        r.forEach((q, i) => { const c = Object.assign({}, q);
          if (i === 0) c.start = true; else delete c.start; f.strokes.push(c); });
        f.strokeGroups.push(r.length); return f; };
      const A = mk(L(0, 0, false)), B = mk(L(180, 90, !!lopsided));
      // The centre a person would point at: the middle of the INK, weighted by
      // how much ink there is, not the mean of however many samples recorded it.
      const arc = (r) => { let tot = 0, cx = 0, cy = 0;
        for (let i = 1; i < r.length; i++) {
          const d = Math.hypot(r[i].x - r[i-1].x, r[i].y - r[i-1].y);
          tot += d; cx += (r[i].x + r[i-1].x) / 2 * d;
                    cy += (r[i].y + r[i-1].y) / 2 * d; }
        return tot > 0 ? { x: cx/tot, y: cy/tot } : { x: r[0].x, y: r[0].y }; };
      frames.length = 0; frames.push(A); frames.push(B);
      idx = 0; fps = 12; subdiv = 1; selSpans = [];
      actionLog.length = 0; redoStack.length = 0;
      buildStrip(); render();
      const n0 = frames.length;
      addInbetween();
      if (frames.length <= n0) return { made: false };
      const g = frames[1];
      const ca = arc(A.strokes), cb = arc(B.strokes), cg = arc(g.strokes);
      // What the fit concluded, read the way the half-turn pin above reads it.
      const ra = tweenVisible(A).ink, rb = tweenVisible(B).ink;
      const nn = Math.max(ra[0].length, rb[0].length);
      const pa = tweenResample(ra[0], nn);
      const pb = ibPhase(pa, tweenResample(rb[0], nn));
      const T = ibFit(pa, pb);
      const loc = ibUnapply(pb, T);
      let e = 0;
      for (let i = 0; i < nn; i++) e += Math.hypot(loc[i].x - pa[i].x, loc[i].y - pa[i].y);
      return { made: true, dx: cg.x - (ca.x + cb.x) / 2, dy: cg.y - (ca.y + cb.y) / 2,
               deg: Math.abs(T.angle) * 180 / Math.PI, scale: T.scale, resid: e / nn };
    }"""

    _tr = { "even": page.evaluate(TRANS, False),
            "lopsided": page.evaluate(TRANS, True) }
    check("both translation fixtures produced an in-between",
          all(v.get("made") is True for v in _tr.values()), str(_tr))
    _far = { k: (round(v.get("dx", 999), 2), round(v.get("dy", 999), 2))
             for k, v in _tr.items()
             if not v.get("made") or max(abs(v["dx"]), abs(v["dy"])) > 2.0 }
    check("a drawing that only moved is drawn half way between, to the pixel",
          not _far,
          f"{_far} — the middle pose belongs at the midpoint of the two "
          f"centres. Without ibApply's centroid lerp it sits on top of the "
          f"first pose, 90px away, which reads as the drawing not moving "
          f"until it jumps")
    _bent = { k: (round(v.get("deg", 999), 2), round(v.get("scale", 0), 4),
                  round(v.get("resid", 999), 2))
              for k, v in _tr.items()
              if not v.get("made") or v["deg"] > 1.0
              or abs(v["scale"] - 1.0) > 0.02 or v["resid"] > 0.5 }
    check("...and it is fitted as a move: no turn, no scale, nothing left over",
          not _bent,
          f"{_bent} — a slide has no rotation and no size change in it. "
          f"Sampled by index rather than arc length the lopsided pose fits as "
          f"a 38.7 degree turn at 0.57 scale carrying 122px of residual, and "
          f"the evenly-recorded pair cannot tell you so")

    print("\nUNDO — an in-between is one action, and undoing it is not a blank page")

    _iu = page.evaluate("""() => {
      const pt = (x, y) => ({ x: x, y: y, size: 6, color: '#ffffff',
                              erase: false, t: 0 });
      const mk = (x) => { const f = { strokes: [], strokeGroups: [], hold: 1 };
        for (let i = 0; i <= 14; i++) {
          const q = pt(x, 200 + i * 12); if (i === 0) q.start = true;
          f.strokes.push(q); }
        f.strokeGroups.push(15); return f; };
      frames.length = 0; frames.push(mk(200)); frames.push(mk(400));
      idx = 0; fps = 12; subdiv = 1; selSpans = [];
      actionLog.length = 0; redoStack.length = 0;
      buildStrip(); render();
      const before = frames.length;
      addInbetween();
      if (frames.length === before) return { made: false };
      const madeGroups = frames[idx].strokeGroups.length;
      undoStroke();
      return { made: true, madeGroups: madeGroups, pages: frames.length,
               idx: idx, fps: fps, subdiv: subdiv,
               holds: frames.map(f => f.hold),
               // Every page still carries the drawing it was made with.
               groupsPerPage: frames.map(f => f.strokeGroups.length),
               pointsPerPage: frames.map(f => f.strokes.length) };
    }""")
    check("the fixture generated an in-between at all", _iu.get("made") is True,
          str(_iu))
    check("undo removes the in-between page rather than emptying it",
          _iu.get("pages") == 2 and 0 not in (_iu.get("groupsPerPage") or [0]),
          f"{_iu} — an in-between holds ONE group, so popping it left a blank "
          f"page sitting in the middle of the flip")
    check("...and both of the artist's own pages are untouched",
          _iu.get("pointsPerPage") == [15, 15],
          f"{_iu.get('pointsPerPage')} — a second undo used to start eating the "
          f"drawing on the page before")
    check("...and the carve is undone with it",
          _iu.get("fps") == 12 and _iu.get("subdiv") == 1
          and _iu.get("holds") == [1, 1], str(_iu))

    # ---------------------------------------------------------------- v299
    # ONE POSE TAKEN SLOWLY, THE NEXT TAKEN FAST.
    #
    # tweenHeldStill decides whether a paired stroke is interpolated or carried
    # across from this page untouched, and it walked its loop to the SHORTER of
    # the two runs while parameterising by the FIRST. Where the first was the
    # denser, the parameter never reached 1 and only the leading fraction of the
    # stroke was ever compared. An arm swung 40 degrees, drawn with 400 points
    # and redrawn with 4, presented 0.4px of movement against a 6px brush and
    # was declared still.
    #
    # WHY THIS IS NOT verify_tween's ASSERTION IN A DIFFERENT SUITE. The two
    # buttons are two call sites into tweenAlign and they spend `unpaired`
    # differently: the smear puts the stroke in `still` and draws it once, so
    # what is lost there is the trail, measurable as the spread of angles it was
    # laid down at. Here the stroke is appended to the generated page from THIS
    # pose, so what is lost is the half-way position -- there is no trail to
    # measure and no angles to spread. Measured on the broken tree: 0.0 degrees
    # where 20.0 was drawn, with the strokeGroup counts IDENTICAL either way,
    # which is why the measure has to be geometric.
    print("\nTWO DENSITIES: a stroke is not 'still' because it was drawn carefully")

    # 100px arm against a 500px body -- past the 4x the matcher's length guard
    # allows, so the two cannot cross-pair and this stays a test of the
    # still/moved measure rather than of the matcher.
    page.evaluate("""() => {
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
      idx = 0; buildStrip(); render();
    }""")
    ARM = """(f) => {
      const fr = frames[f]; let at = 0, best = null;
      for (const g of fr.strokeGroups) {
        const r = fr.strokes.slice(at, at + g); at += g;
        let L = 0;
        for (let i = 1; i < r.length; i++) L += Math.hypot(r[i].x-r[i-1].x, r[i].y-r[i-1].y);
        if (L >= 200) continue;                     // the body, not the arm
        best = { deg: Math.atan2(r[r.length-1].y - r[0].y,
                                 r[r.length-1].x - r[0].x) * 180/Math.PI, len: L };
      }
      return best;
    }"""
    _a0 = page.evaluate(ARM, 0)
    page.evaluate("() => addInbetween()")
    page.wait_for_timeout(300)
    _amid = page.evaluate(ARM, 1)
    _a2 = page.evaluate(ARM, 2)
    check("the two poses were interpolated at all",
          _amid is not None and page.evaluate("() => frames.length") == 3,
          f"{_amid} — no arm on the generated page")
    check("the arm sits half way through its swing, not where this page left it",
          _amid is not None and abs(_amid["deg"] - 20) < 5,
          f"{_amid['deg']:.1f}deg between the drawn {_a0['deg']:.1f} and "
          f"{_a2['deg']:.1f} — landing on {_a0['deg']:.1f} means the arm was "
          f"called held still and carried across from this pose untouched, "
          f"which is the in-between quietly leaving out the thing that moved"
          if _amid else str(_amid))
    check("...and it kept its length getting there",
          _amid is not None and abs(_amid["len"] - _a0["len"]) / _a0["len"] < 0.05,
          f"{_amid['len']:.1f}px against the drawn {_a0['len']:.1f}px"
          if _amid else str(_amid))

    # ---------------------------------------------------------------- v299
    # A TAP IS ORDINARY DRAWING, and the in-between had three separate ways of
    # mishandling one. TWO MECHANISMS, in two functions, so they are mutated and
    # asserted separately below -- an all-or-nothing revert shows red for one of
    # them while the other's assertion pins nothing.
    #
    #   buildInbetween   `if (n < 2) continue` dropped a dot paired with a dot
    #                    without a word; where the pages held NOTHING but dots it
    #                    then refused the whole in-between, with a message saying
    #                    the pages needed drawing on them.
    #   ibFit            tested pa's spread about its centroid and not pb's, and
    #                    pb is the side ibUnapply DIVIDES BY. A dot resampled to
    #                    a run is n copies of one point, whose centroid comes
    #                    back as 399.99999999999994 -- so the fitted scale is
    #                    4.1e-31 rather than 0, sails past `T.scale || 1`, and
    #                    1/4.1e-31 puts the stroke at x = 1.04e17.
    #
    # A DOT IS NOT AN EDGE CASE HERE. It paints a filled disc of the pen's width
    # (measured: 482 ink pixels at size 12), tweenMatch exempts it from the
    # length guard on purpose so it can pair with the run it becomes, and
    # tweenResample carries a branch for it. Every part of the machinery supports
    # a dot except the two that had to emit one.
    print("\nA TAP: the in-between has to carry one, and both ways round")

    DOTS = """(kind) => {
      const pt = (x,y,s) => ({ x:x, y:y, color:'#ffffff', size:(s||6), t:0, erase:false });
      const seg = (x0,y0,x1,y1,n) => { const o = [];
        for (let i = 0; i < n; i++) { const t = i/(n-1);
          o.push(pt(x0+(x1-x0)*t, y0+(y1-y0)*t)); }
        o[0].start = true; return o; };
      const dot = (x,y,s) => { const p = pt(x,y,s||12); p.start = true; return [p]; };
      const mk = (runs) => ({ strokes: [].concat(...runs),
                              strokeGroups: runs.map(r => r.length), hold: 1 });
      const pages = {
        // A line that plainly moves, and a tap that moves with it.
        withLine: [[seg(100,100,300,100,20), dot(400,300)],
                   [seg(100,200,300,200,20), dot(400,500)]],
        // Nothing on either page BUT a tap.
        only:     [[dot(200,200)], [dot(400,400)]],
        // A line becoming a tap, and the same two drawings the other way round.
        runToDot: [[seg(200,200,300,300,12)], [dot(400,400)]],
        dotToRun: [[dot(200,200)], [seg(200,200,300,300,12)]]
      }[kind];
      frames.length = 0;
      frames.push(mk(pages[0])); frames.push(mk(pages[1]));
      idx = 0; buildStrip(); render();
      const before = frames.length;
      let threw = null;
      try { addInbetween(); } catch (e) { threw = e.constructor.name + ': ' + e.message; }
      if (frames.length <= before)
        return { made: false, threw: threw,
                 chip: (document.getElementById('flipChip') || {}).textContent };
      let at = 0; const groups = [];
      for (const n of frames[1].strokeGroups) {
        const r = frames[1].strokes.slice(at, at + n); at += n;
        let L = 0;
        for (let i = 1; i < r.length; i++) L += Math.hypot(r[i].x-r[i-1].x, r[i].y-r[i-1].y);
        groups.push({ n: n, len: L,
                      cx: r.reduce((s,p) => s+p.x, 0)/n, cy: r.reduce((s,p) => s+p.y, 0)/n,
                      deg: Math.atan2(r[n-1].y - r[0].y, r[n-1].x - r[0].x) * 180/Math.PI });
      }
      return { made: true, threw: threw, groups: groups };
    }"""

    # ---- mechanism 1: buildInbetween emits the dot instead of skipping it ----
    _dl = page.evaluate(DOTS, "withLine")
    _dots = [g for g in (_dl.get("groups") or []) if g["n"] == 1]
    check("a tap paired with a tap is ON the generated page",
          len(_dots) == 1,
          f"{_dl} — both poses carry [20, 1] and the in-between carries what is "
          f"listed here. A dropped tap says nothing and leaves no trace")
    check("...and it sits half way between the two taps",
          bool(_dots) and abs(_dots[0]["cx"] - 400) < 2 and abs(_dots[0]["cy"] - 400) < 2,
          f"{_dots} — drawn at (400,300) and (400,500)")

    _do = page.evaluate(DOTS, "only")
    check("a page holding NOTHING but a tap still gets an in-between",
          _do.get("made") is True,
          f"{_do} — refusing here told the artist the pages needed drawing on "
          f"them while they were looking at the drawing on them")

    # ---- mechanism 2: ibFit refuses a fit it cannot compute ------------------
    # CENTROID AND DIRECTION, because they fail differently and only one of them
    # is the 1e17. With the tap on the SECOND page the stroke leaves the canvas;
    # with the tap on the FIRST page it stays put and comes out ROTATED, because
    # the angle is atan2 of the same dust. Same two drawings, opposite order.
    _r2d = page.evaluate(DOTS, "runToDot")
    _d2r = page.evaluate(DOTS, "dotToRun")
    _g1 = (_r2d.get("groups") or [None])[0]
    _g2 = (_d2r.get("groups") or [None])[0]
    check("a line becoming a tap stays ON the canvas",
          _g1 is not None and abs(_g1["cx"] - 325) < 2 and abs(_g1["cy"] - 325) < 2,
          f"{_g1} — the two poses are centred at (250,250) and (400,400), so the "
          f"middle of them is (325,325). A fitted scale of 4.1e-31 inverted to "
          f"2.4e30 and put this at 1.04e17, which draws as a blank page")
    check("...and a tap becoming a line points the way the line does",
          _g2 is not None and abs(_g2["deg"] - 45) < 10,
          f"{_g2} — the line it is turning into runs at 45deg. An angle fitted "
          f"from float dust came out at -45: the right length, in the right "
          f"place, square across the stroke it is supposed to be becoming")
    check("...and the two orders are mirror images, as the drawings are",
          _g1 is not None and _g2 is not None
          and abs(_g1["len"] - _g2["len"]) < 1,
          f"{_g1['len'] if _g1 else None} against {_g2['len'] if _g2 else None} — "
          f"the same two drawings in the other order must spend the same ink")

    # ---------------------------------------------------------------- v299
    # WHERE IN TIME THE MIDDLE POSE LANDS.
    #
    # carveForInsert took ONE slot off the pose however long the pose was held.
    # At hold 2 and 3 that is the evenest cut available; at 4 and above it is
    # not, and the badge offers x4 directly, so it is one tap away on a fresh
    # document. A page held x4 put its midpoint 250ms into a 333ms interval
    # instead of 167ms; held x8, 583 of 667. The geometry was right and the
    # timing was not, which reads as the first pose hanging and then a flicker.
    #
    # SWEPT, NOT SAMPLED. One fixture at one hold cannot tell "takes a slot"
    # from "takes half", because at hold 2 and 3 the two rules agree -- and
    # those are the holds every other fixture in this suite uses. The sweep is
    # what separates them.
    #
    # THE SUM IS NOT A SECOND READING OF THE SPLIT. It is green under the old
    # rule AND the new one -- both spend exactly what the pose held -- and it
    # goes red on a HALF-APPLIED fix, which is the state this change passes
    # through: measured, with carveForInsert splitting and this caller still
    # writing a hard 1, the pair came out SHORTER than the pose had been and
    # every page after it moved. The midpoint check catches that too; this one
    # says which of the two things went wrong.
    print("\nTHE CARVE: a middle pose has to land in the middle")

    SWEEP = """() => {
      const seg = (y) => { const o = [];
        for (let i = 0; i < 10; i++)
          o.push({ x: 100 + i*15, y: y, color: '#ffffff', size: 6, t: 0, erase: false });
        o[0].start = true; return o; };
      const mk = (y, h) => ({ strokes: seg(y), strokeGroups: [10], hold: h });
      const rows = [];
      for (let H = 1; H <= 8; H++) {
        frames.length = 0; frames.push(mk(200, H)); frames.push(mk(420, 1));
        idx = 0; fps = 12; subdiv = 1; selSpans = [];
        actionLog.length = 0; redoStack.length = 0;
        buildStrip(); render();
        const before = frames.length;
        addInbetween();
        if (frames.length <= before) { rows.push({ H: H, made: false }); continue; }
        // Post-carve the pose may have been doubled, so the interval to split
        // is what the pair occupies now -- which is the thing that must equal
        // what the pose occupied on its own.
        rows.push({ H: H, made: true, pose: frames[0].hold, gen: frames[1].hold,
                    was: H * (subdiv || 1) });
      }
      return rows;
    }"""
    _sw = page.evaluate(SWEEP)
    _off = [r for r in _sw if not r["made"] or abs(r["pose"] - r["gen"]) > 1]
    check("the in-between lands at the middle of the interval at EVERY hold",
          not _off,
          "; ".join(f"hold {r['H']} -> {r.get('pose')}:{r.get('gen')}" for r in _off)
          + " — taking one slot off the pose centres the midpoint only while the "
            "pose is held 2 or 3. A page held x4 is one tap away")
    _sum = [r for r in _sw if r["made"] and r["pose"] + r["gen"] != r["was"]]
    check("...without the pair occupying more than the pose did alone",
          not _sum,
          "; ".join(f"hold {r['H']} -> {r['pose']}+{r['gen']} against {r['was']}"
                    for r in _sum)
          + " — a longer pair moves every page after it, which is the bug the "
            "carve exists to prevent")

    # ---------------------------------------------------------------- v300
    # WHAT YOU RUBBED OUT STAYS RUBBED OUT.
    #
    # buildInbetween walks tweenVisible(a).ink and nothing walked .erase, so a
    # line with a rubbed-out middle came back SOLID on the generated page and
    # the hole returned on the next one. Measured on corpus case 18's geometry:
    # the page held one run with erase false, and the middle of the gap painted
    # 8 dark pixels where it should paint none.
    #
    # THE SMEAR'S ANSWER IS NOT THIS ONE, and the difference is the assertion.
    # buildTween carries erasers through unsampled, at the position drawn,
    # because a smear is many copies of one pose. An in-between is ONE pose, so
    # if the erased stroke moved its hole must move with it -- carrying at A's
    # position would leave the hole at y=300 while the line sits at y=365, and
    # the line would read solid anyway. That is why the second check below is
    # about WHERE the hole is, not merely that there is one.
    #
    # MEASURED OPAQUE AND DARK, not dark. The first version of this read only
    # the red channel and reported MORE ink after the hole was restored:
    # destination-out leaves r=0, a=0, which is indistinguishable from black
    # unless the alpha is checked. The instrument was wrong in the direction
    # that would have hidden the fix.
    print("\nERASURE — a hole the artist made does not heal in the middle")

    ERASE = """(only) => {
      const L=(x0,y0,x1,y1,n,o)=>{const a=[];for(let i=0;i<=n;i++){const t=i/n;
        a.push(Object.assign({x:x0+(x1-x0)*t, y:y0+(y1-y0)*t, color:'#141414',
                              size:7, erase:false, t:i}, o||{}));}
        a[0].start=true; return a;};
      const mk=(runs)=>{const f={strokes:[],strokeGroups:[],hold:1};
        runs.forEach(r=>{r.forEach((p,i)=>{const q=Object.assign({},p);
          if(i===0)q.start=true; else delete q.start; f.strokes.push(q);});
          f.strokeGroups.push(r.length);}); return f;};
      const rub=(y)=>L(300,y,420,y,16,{erase:true,size:34});
      // `only` drops the eraser from the SECOND page, which is the case that
      // has no partner to move toward.
      const A = mk([ L(120,300,600,300,40), rub(300) ]);
      const B = only ? mk([ L(120,430,600,430,40) ])
                     : mk([ L(120,430,600,430,40), rub(430) ]);
      frames.length=0; frames.push(A); frames.push(B);
      idx=0; fps=12; subdiv=1; selSpans=[];
      actionLog.length=0; redoStack.length=0; buildStrip(); render();
      const n0=frames.length;
      addInbetween();
      if(frames.length<=n0) return {made:false};
      const g=frames[1];
      let at=0; const runs=[];
      for(const n of g.strokeGroups){ const r=g.strokes.slice(at,at+n); at+=n;
        runs.push({n:n, erase:!!r[0].erase, y:Math.round(r[0].y)}); }
      const c=document.getElementById('c')||document.querySelector('canvas');
      const cx=c.getContext('2d');
      cx.setTransform(1,0,0,1,0,0);
      cx.fillStyle='#ffffff'; cx.fillRect(0,0,c.width,c.height);
      paintStatic(cx, g.strokes);
      const d=cx.getImageData(0,0,c.width,c.height).data;
      const col=(x)=>{let k=0; for(let y=0;y<c.height;y++){
        const i=(y*c.width+(x|0))*4; if(d[i+3]>128 && d[i]<128) k++; } return k;};
      return { made:true, runs:runs, gap:col(360), left:col(200), right:col(520) };
    }"""

    _er = page.evaluate(ERASE, False)
    check("an in-between of two rubbed-out lines keeps the hole",
          _er.get("made") and _er["gap"] == 0,
          f"{_er.get('gap')} opaque dark pixels through the middle of the gap "
          f"— the artist rubbed it out on both pages and the generated one "
          f"filled it back in")
    check("...while the line either side of it is still there",
          _er.get("made") and _er["left"] > 0 and _er["right"] > 0,
          f"left {_er.get('left')} right {_er.get('right')} — a blank page "
          f"would pass the check above for the wrong reason")
    _rub = [r for r in (_er.get("runs") or []) if r["erase"]]
    check("...and the hole MOVED with the line, rather than staying where it was",
          len(_rub) == 1 and abs(_rub[0]["y"] - 365) <= 2,
          f"{_rub} — drawn at y=300 and y=430, so the one pose between them "
          f"holds its hole at 365. Carrying the eraser across unsampled, which "
          f"is what the smear does, would leave it at 300 with the line at 365")

    _only = page.evaluate(ERASE, True)
    _orub = [r for r in (_only.get("runs") or []) if r["erase"]]
    check("an eraser with no partner on the next page is carried as drawn",
          len(_orub) == 1 and abs(_orub[0]["y"] - 300) <= 2,
          f"{_orub} — a hole made on THIS page is on the page you are "
          f"inserting after, so it comes through where it was put")

    # ---------------------------------------------------------------- v300
    # THE PHASE SEARCH HAD A SCALING CLIFF, and this gates the work rather than
    # the clock.
    #
    # ibPhase's coarse pass is 48 probes whatever the drawing holds, but the
    # refinement walked EVERY offset in +/- stride, and stride is n/24 -- so
    # the refinement grew with the point count while each probe is itself
    # O(n). Quadratic. Measured on a six-stroke figure before the change:
    #
    #     points per stroke     300    600   1200   2400
    #     ibPhase, ms          1.28   2.67   7.93   26.7
    #     the button, ms         50     84    167    353
    #
    # NOT A STOPWATCH, DELIBERATELY. This project already learned what a
    # wall-clock pin is worth: verify_pages' cold > warm*3 failed twice on
    # trees whose own sqlite job passed, both times because the box was busy,
    # and DECISIONS records that a pin which goes red when the machine is
    # loaded reports on the machine rather than on the tree. So the assertion
    # counts ibFit CALLS, which is the work the algorithm actually does and is
    # identical on every machine.
    #
    #     ibFit calls      300    600   1200   2400
    #     shipped           75     99    149    249      doubling: linear
    #     now               68     72     78     84      +6: logarithmic
    print("\nPHASE SEARCH — the work must not grow with the drawing")

    _cost = page.evaluate("""() => {
      const loop = (n, spin) => { const o = [];
        for (let i = 0; i < n; i++) { const a = spin + i/n*2*Math.PI;
          const r = 90 + 22*Math.sin(3*a) + 12*Math.cos(5*a);
          o.push({ x: 353 + Math.cos(a)*r, y: 353 + Math.sin(a)*r, size: 6 }); }
        o.push(Object.assign({}, o[0])); return o; };
      const real = window.ibFit;
      const count = (n) => {
        const pa = tweenResample(loop(n, 0), n), pb = tweenResample(loop(n, 1.9), n);
        let calls = 0;
        window.ibFit = function(){ calls++; return real.apply(null, arguments); };
        try { ibPhase(pa, pb); } finally { window.ibFit = real; }
        return calls;
      };
      const small = count(600), large = count(2400);

      /* AND THE CHEAPER SEARCH MUST STILL FIND THE ANSWER. Checked at 300
         points, where EVERY spin can be afforded -- a truly exhaustive sweep,
         step of one, not a coarse reference. An earlier version of this used
         step = n/240 and reported the search beating its own oracle by 71%,
         which meant the oracle was the weaker instrument, not that the search
         was inspired.

         AND AT 600 RATHER THAN 300, because 300 does not discriminate: with
         IB_PHASE_BRACKETS dropped to 1 this suite stayed green there, and a
         check that cannot go red is not evidence. 600 is the contour and
         phase offset where refining only the BEST coarse bracket lands in a
         local minimum. Measured on this exact fixture: 8.02% off the
         exhaustive answer with one bracket, 0.00% with three. */
      const n = 600;
      const pa = tweenResample(loop(n, 0), n), pb = tweenResample(loop(n, 1.9), n);
      const cands = [pb, pb.slice().reverse()];
      let cx = 0, cy = 0; for (const p of pa){ cx += p.x/n; cy += p.y/n; }
      let rad = 0; for (const p of pa) rad += Math.hypot(p.x-cx, p.y-cy)/n;
      const score = (q) => { const T = real(pa, q), loc = ibUnapply(q, T); let e = 0;
        for (let i = 0; i < n; i++) e += Math.hypot(loc[i].x-pa[i].x, loc[i].y-pa[i].y);
        return e/n + IB_TURN_PENALTY*Math.abs(T.angle)*rad; };
      let bc = Infinity;
      for (let o = 0; o < 2; o++) for (let k = 0; k < n; k++) {
        const c = score(ibSpin(cands[o], k)); if (c < bc) bc = c; }
      const chosen = score(ibPhase(pa, pb));
      return { small: small, large: large, chosen: chosen, exhaustive: bc,
               penalty: (chosen - bc) / Math.max(bc, 1e-9) };
    }""")

    check("the phase search's work barely grows when the drawing gets four "
          "times denser",
          _cost["large"] < _cost["small"] * 1.5,
          f"{_cost['small']} fits at 600 points, {_cost['large']} at 2400 — "
          f"x{_cost['large']/max(_cost['small'],1):.1f}. Walking every offset in "
          f"a window of n/24 made this linear, and each probe is itself O(n)")
    check("...and it still finds what an exhaustive sweep of every spin finds",
          _cost["penalty"] < 0.01,
          f"{_cost['chosen']:.3f} against {_cost['exhaustive']:.3f} over all 1200 "
          f"spins at 600 points ({_cost['penalty']*100:+.1f}%) — cheaper is only "
          f"worth having if it lands in the same place")

    check("no uncaught error across the whole session", not errs, "; ".join(errs[:3]))
    browser.close()

bad = [r for r in results if not r[0]]
print(f"\n{'=' * 62}\n{len(results) - len(bad)}/{len(results)} passed"
      + ("" if not bad else "  FAILURES: " + ", ".join(n for _, n in bad)))
sys.exit(1 if bad else 0)
