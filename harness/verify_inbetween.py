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
    check("...where the smear of the same motion is many times heavier",
          smear_pts > mid_pts * 8,
          f"smear {smear_pts} against in-between {mid_pts} — if these are close, "
          f"one of the two is not doing its job")

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
    page.wait_for_timeout(300)
    check("a different number of strokes is refused rather than guessed at",
          page.evaluate("() => frames.length") == 2,
          "inventing a pairing produces a mess that reads as a broken tool")
    msg = page.evaluate("() => (document.getElementById('flipChip')||{}).textContent") or ""
    check("...and the refusal names an in-between, not a smear",
          "in-between" in msg.lower() and "smear" not in msg.lower(), repr(msg))

    page.evaluate("() => { go(1); }")
    page.evaluate("() => addInbetween()")
    page.wait_for_timeout(300)
    msg = page.evaluate("() => (document.getElementById('flipChip')||{}).textContent") or ""
    check("on the last page it explains there is no next pose",
          page.evaluate("() => frames.length") == 2 and "BETWEEN" in msg, repr(msg))

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

    check("no uncaught error across the whole session", not errs, "; ".join(errs[:3]))
    browser.close()

bad = [r for r in results if not r[0]]
print(f"\n{'=' * 62}\n{len(results) - len(bad)}/{len(results)} passed"
      + ("" if not bad else "  FAILURES: " + ", ".join(n for _, n in bad)))
sys.exit(1 if bad else 0)
