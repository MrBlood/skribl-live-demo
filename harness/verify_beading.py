"""v225 — a translucent stroke must survive a repaint unchanged.

Outside review of v224, finding R2, and the reviewer was right to rank it: the
project's own reviewer notes described this fix and admitted **it is not pinned
by an assertion**. Saying so is not a substitute for a test.

THE BUG. `selRepaint()` was the one repaint in the editor still passing the raw
`drawDot`/`drawLine` painters straight to `replayTimelineToCanvas`. Live drawing
takes the "wet" path, where a see-through stroke is composited once as a whole;
the raw replay repaints it segment by segment, so the stroke's own overlaps
stack back into beads at every captured point. An Air-brush line came back
mottled. And `setTool()` calls `SkriblSelectTool.clear()` on EVERY tool change,
so simply picking the eraser re-beaded the whole canvas without erasing
anything.

WHY IT NEEDED A NEW SUITE. Nothing else here can see it. It is not a geometry
change (`verify_layout` measures boxes), not a structural one (`verify_lib`,
`verify_surfaces` read source), and not a stroke-data change (`verify_dots`,
`verify_strokegroups` read arrays) — THE STROKES ARE BYTE-IDENTICAL BEFORE AND
AFTER, which this suite asserts rather than assumes. Only the pixels differ.

WHAT IS MEASURED, AND THE TRAP IN MEASURING IT. Not a screenshot diff, which
fails on an antialiasing difference and teaches everyone to ignore it. The
metric is the ALPHA PROFILE of the ink: the spread between the most and least
opaque lit pixel of one translucent stroke. Flat translucent stroke, narrow
spread; beaded stroke, bright where overlaps stacked and dim between, so the
spread widens.

It must be read from the ALPHA CHANNEL. The first draft of this file read the
red channel and measured a spread of ZERO on a visibly correct stroke: the
canvas is transparent-backed — the dark ground is CSS behind it — so
`getImageData` returns STRAIGHT (un-premultiplied) RGBA and a 22%-alpha white
stroke reads r=255, a=56. The colour channels are saturated and carry no
coverage information at all. This project has now met premultiplied-vs-straight
alpha three times in three different disguises.

The profile also ignores non-grey pixels, because a marquee selection paints a
purple outline (rgba(124,92,255,0.95)) and that outline is not ink. Reading it
made the first draft report a spread of 138 for a repaint that was perfect.

THE MUTATION IS THE POINT. One section repaints through the raw painters, which
is the pre-fix code path, and REQUIRES the profile to change materially. Without
it every assertion here could pass on a canvas that never repainted at all.
"""
import os
import sys
from assertions import make_check
import browsing

BASE = os.environ.get("SKRIBL_BASE", "http://127.0.0.1:5001")

try:
    from playwright.sync_api import sync_playwright
except ImportError:                                   # pragma: no cover
    print("SKIP: playwright is not installed")
    sys.exit(0)

results = []


check = make_check(results)


# Alpha channel, grey pixels only. See the module docstring for why both.
_PROFILE_BODY = """
  const c = document.getElementById('canvas');
  const g = c.getContext('2d', { willReadFrequently: true });
  const d = g.getImageData(0, 0, c.width, c.height).data;
  let lit = 0, mass = 0, min = 255, max = 0;
  for (let i = 0; i < d.length; i += 4) {
    const a = d[i + 3];
    if (a <= 8) continue;                       // bare canvas
    const r = d[i], gr = d[i + 1], b = d[i + 2];
    if (Math.abs(r - gr) > 12 || Math.abs(gr - b) > 12) continue;   // not ink
    lit++; mass += a;
    if (a < min) min = a;
    if (a > max) max = a;
  }
  return { lit, mass, min: lit ? min : 0, max,
           spread: lit ? max - min : 0,
           mean: lit ? Math.round(mass / lit) : 0 };
"""
PROFILE = "() => {" + _PROFILE_BODY + "}"


def draw_airbrush(page, box):
    """One dense Air-brush stroke, drawn the way a person draws one.

    Air-brush because it is the preset from the bug report: alpha 0.22, width
    2.6x. Dense because beading comes from consecutive points overlapping, which
    is what every real stroke does and what the raw replay re-stacks.
    """
    before = page.evaluate("() => strokes.length")
    cx = box["x"] + box["width"] / 2
    cy = box["y"] + box["height"] / 2
    n, step = 90, 4
    page.mouse.move(cx - (n * step) / 2, cy)
    page.mouse.down()
    for i in range(1, n + 1):
        page.mouse.move(cx - (n * step) / 2 + i * step, cy)
    page.mouse.up()
    page.wait_for_timeout(150)
    after = page.evaluate("() => strokes.length")
    assert after > before, f"setup drew nothing ({before} -> {after})"
    return after - before


with sync_playwright() as p:
    br = p.chromium.launch()
    try:
        page = br.new_page(viewport={"width": 1280, "height": 950})
        browsing.goto(page, BASE, "/")

        print("\nSETUP — one 22%-alpha stroke, drawn with the mouse")
        check("stroke layers are ON, which is what this fix protects",
              page.evaluate("() => strokeLayersOn()") is True,
              "with them off there is no compositor and nothing to test")
        check("the Air-brush preset is the one from the bug report",
              page.evaluate("() => !!(window.SkriblBrush && "
                            "window.SkriblBrush.PRESETS.airbrush)"),
              "alpha 0.22, width 2.6x")
        page.evaluate("() => { window.SkriblBrush.setBrush('airbrush'); "
                      "setTool('pen'); }")
        box = page.locator("#canvas").bounding_box()
        pts = draw_airbrush(page, box)
        ink = page.evaluate("() => strokes[5] && strokes[5].color")
        check("the captured stroke really is translucent",
              isinstance(ink, str) and "0.22" in ink,
              f"{pts} points, colour {ink!r} — if this is opaque the whole "
              "suite would pass vacuously")

        wet = page.evaluate(PROFILE)
        check("the stroke landed and reads as ink",
              wet["lit"] > 500, f"{wet['lit']} lit px, mean alpha {wet['mean']}")
        check("the WET profile is flat — composited once, no stacking",
              wet["spread"] <= 60 and wet["mean"] < 120,
              f"alpha {wet['min']}..{wet['max']} (spread {wet['spread']}), "
              f"mean {wet['mean']}")

        # Everything below repaints the SAME stroke data. If the strokes
        # themselves changed, a pixel difference would prove nothing.
        sig = page.evaluate("() => JSON.stringify(strokes)")

        print("\nREPAINT — a marquee selection repaints the whole drawing")
        # SkriblSelectTool.end() calls selRepaint() after a marquee. A rectangle
        # this large selects everything, whatever coordinate space it is in.
        page.evaluate("""() => {
          SkriblSelectTool.begin({ x: -10000, y: -10000 });
          SkriblSelectTool.end({ x: 10000, y: 10000 });
        }""")
        page.wait_for_timeout(120)
        after_sel = page.evaluate(PROFILE)
        check("the repaint ran over a real selection",
              page.evaluate("() => SkriblSelectTool.hasSelection()"),
              "otherwise selRepaint was never reached and this proves nothing")
        check("the strokes are byte-identical across the repaint",
              page.evaluate("() => JSON.stringify(strokes)") == sig,
              "so any pixel change can only be a RENDERING change")
        check("REPAINT DID NOT BEAD: the alpha spread held",
              abs(after_sel["spread"] - wet["spread"]) <= 12,
              f"wet {wet['spread']} -> repainted {after_sel['spread']}")
        check("...and the ink is the same weight, not re-stacked",
              abs(after_sel["mean"] - wet["mean"]) <= 6,
              f"mean alpha {wet['mean']} -> {after_sel['mean']}")

        print("\nTOOL CHANGE — the path that made picking the eraser re-bead")
        page.evaluate("() => SkriblSelectTool.clear()")
        page.wait_for_timeout(120)
        after_clear = page.evaluate(PROFILE)
        check("clearing the selection repainted from the same strokes",
              page.evaluate("() => JSON.stringify(strokes)") == sig)
        check("A TOOL CHANGE DID NOT BEAD: the alpha spread held",
              abs(after_clear["spread"] - wet["spread"]) <= 12,
              f"wet {wet['spread']} -> after tool change {after_clear['spread']}")
        check("...and the ink is the same weight",
              abs(after_clear["mean"] - wet["mean"]) <= 6,
              f"mean alpha {wet['mean']} -> {after_clear['mean']}")

        print("\nMUTATION — the pre-fix path, run on purpose, must look WORSE")
        # The old selRepaint body: raw painters straight into the replay loop,
        # no compositor. If this produces the same picture then the compositor
        # is doing nothing and every assertion above is decoration.
        beaded = page.evaluate("""() => {
          clearAndRestore(() => {
            const tl = buildPlaybackTimeline();
            replayTimelineToCanvas(tl, 0, Infinity, drawDot, drawLine);
          });""" + _PROFILE_BODY + "}")
        check("the raw-painter replay DOES bead — a heavier, wider profile",
              beaded["mean"] > after_clear["mean"] + 20,
              f"composited mean {after_clear['mean']} vs raw {beaded['mean']} "
              "— if these match, the compositor is not doing anything")
        check("...and it saturates where overlaps stack",
              beaded["max"] > after_clear["max"] + 20,
              f"max alpha composited {after_clear['max']} vs raw {beaded['max']}")
        check("...from the very same stroke data",
              page.evaluate("() => JSON.stringify(strokes)") == sig,
              "the difference is the painter, not the drawing")

        print("\nRESTORE — the composited path recovers it exactly")
        healed = page.evaluate("""() => {
          clearAndRestore(() => {
            const tl = buildPlaybackTimeline();
            const comp = makeStrokeCompositor(ctx, canvas);
            replayTimelineToCanvas(tl, 0, Infinity, comp.dotFn, comp.lineFn);
            comp.finish();
            comp.present();
          });""" + _PROFILE_BODY + "}")
        check("routing the same replay through the compositor restores it",
              abs(healed["mean"] - wet["mean"]) <= 6
              and abs(healed["spread"] - wet["spread"]) <= 12,
              f"mean {wet['mean']} -> beaded {beaded['mean']} -> "
              f"healed {healed['mean']}")

        print("\nTHE SMEAR'S GHOSTS ON THIS SURFACE — app.js draws the Pad "
              "AND the sealed /s/ player")
        # paintStrokesStatic is where the player renders a Flip document's
        # frames, so a smear posted to a share link came through here. Its
        # ghosts are see-through runs whose alpha is an 8-digit hex, and
        # parseStrokeAlpha -- which decides the wet layer -- reads rgba() only,
        # so the compositor above never saw one however the flag was set.
        #
        # BOTH FLAG SETTINGS, because the compositor branch is the default and a
        # fix that only worked with layers off would be a fix nobody gets. The
        # first draft of this suite's Flip section measured only one path.
        _ap = page.evaluate("""() => {
          const COL = '#ffffff2e';                     // 46/255
          const seg = [];
          for (let k = 0; k < 24; k++)
            seg.push({ x: 80 + k * 11, y: 120 + (k % 3) * 7, color: COL,
                       size: 9, t: k, erase: false, start: k === 0 });
          const read = () => {
            const d = ctx.getImageData(0, 0, canvas.width, canvas.height).data;
            let lit = 0, max = 0;
            for (let i = 3; i < d.length; i += 4) {
              if (d[i] <= 8) continue; lit++; if (d[i] > max) max = d[i]; }
            return { lit, max };
          };
          const run = (layers) => {
            window.SKRIBL_STROKE_LAYERS = layers;
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            paintStrokesStatic(seg);
            return read();
          };
          const on = run(true), off = run(false);
          // THE MUTATION, in the suite: the pre-fix emission, run on purpose.
          window.SKRIBL_STROKE_LAYERS = true;
          ctx.clearRect(0, 0, canvas.width, canvas.height);
          for (let i = 0; i < seg.length; i++) {
            const q = seg[i];
            if (i === 0) drawDot(q.x, q.y, q.color, q.size, false);
            else { const v = seg[i-1];
                   drawLine(v.x, v.y, q.x, q.y, q.color, q.size, false); }
          }
          const raw = read();
          return { written: 0x2e, on, off, raw };
        }""")
        check("the pre-fix painter DOES stack a ghost above its own alpha here",
              _ap and _ap["raw"]["max"] > _ap["written"] + 12,
              f"written {_ap and _ap['written']}, raw painter reached "
              f"{_ap and _ap['raw']['max']} — this check is not exercising it")
        check("...and paintStrokesStatic holds it AT that alpha, layers ON",
              _ap and _ap["on"]["max"] <= _ap["written"] + 4,
              f"written {_ap and _ap['written']}, painted "
              f"{_ap and _ap['on']['max']} with the compositor engaged")
        check("...and with layers OFF, which is the other branch",
              _ap and _ap["off"]["max"] <= _ap["written"] + 4,
              f"written {_ap and _ap['written']}, painted "
              f"{_ap and _ap['off']['max']} on the direct path")
        check("...covering the same ground either way",
              _ap and abs(_ap["on"]["lit"] - _ap["raw"]["lit"]) <= _ap["raw"]["lit"] * 0.02
              and _ap["on"]["lit"] == _ap["off"]["lit"],
              f"raw {_ap and _ap['raw']['lit']} lit, layers-on "
              f"{_ap and _ap['on']['lit']}, layers-off {_ap and _ap['off']['lit']}")

        # ---------------------------------------------------------------- v302
        # AND THE RUN A FIELD TOOL LEFT BEHIND, WHICH IS A DIFFERENT POPULATION.
        # Everything above is a UNIFORM run: one colour, one width, so uniformRun
        # gives it a single path and a single path cannot stack against itself.
        # Smudge writes per-point colour AND size, so that route closes and the
        # walk takes over -- and the walk is what stacks. Measured in Flip on a
        # smeared ring: 3-5 distinct colours, 11-17 distinct sizes, and alphaMin
        # equal to alphaMax in every touched run, because mix() preserves the
        # hex-8 alpha. That equality is the whole licence for wetRunFn.
        #
        # PINNED DIFFERENTLY FROM THE FLIP SIDE ON PURPOSE. flip.js is asserted
        # on the vertex-to-midpoint ripple, because there the mesh is what the
        # artist sees. Here the reachable claim is the ceiling: this surface
        # renders a posted document, and what matters is that a stranger's copy
        # is not brighter than the ink the author wrote.
        _fp = page.evaluate("""() => {
          const seg = [];
          for (let k = 0; k < 24; k++)
            seg.push({ x: 80 + k * 11, y: 120 + (k % 3) * 7,
                       // same alpha throughout, everything else moving -- which
                       // is exactly the shape a smudge leaves
                       color: (k % 2 ? '#ffffff2e' : '#e8e8e82e'),
                       size: 9 + (k % 5), t: k, erase: false, start: k === 0 });
          const read = () => {
            const d = ctx.getImageData(0, 0, canvas.width, canvas.height).data;
            let lit = 0, max = 0;
            for (let i = 3; i < d.length; i += 4) {
              if (d[i] <= 8) continue; lit++; if (d[i] > max) max = d[i]; }
            return { lit, max };
          };
          const sl = window.SkriblStrokeLayers;
          const notOnePath = sl && !sl.uniformRun(seg, anyStrokeAlpha);
          const oneAlpha = sl && sl.uniformAlpha(seg, anyStrokeAlpha);
          window.SKRIBL_STROKE_LAYERS = true;
          ctx.clearRect(0, 0, canvas.width, canvas.height);
          paintStrokesStatic(seg);
          const on = read();
          // the pre-fix emission for THIS run, run on purpose
          ctx.clearRect(0, 0, canvas.width, canvas.height);
          for (let i = 0; i < seg.length; i++) {
            const q = seg[i];
            if (i === 0) drawDot(q.x, q.y, q.color, q.size, false);
            else { const v = seg[i-1];
                   drawLine(v.x, v.y, q.x, q.y, q.color, q.size, false); }
          }
          const raw = read();
          return { written: 0x2e, notOnePath: !!notOnePath, oneAlpha: oneAlpha,
                   on: on, raw: raw };
        }""")
        check("a field-tool run is NOT one path, yet is one alpha",
              _fp and _fp["notOnePath"] and 0 < (_fp["oneAlpha"] or 0) < 1,
              f"uniformRun says one-path={not (_fp and _fp['notOnePath'])}, "
              f"uniformAlpha={_fp and _fp['oneAlpha']} — if this run took the "
              f"path route the checks below would pass without the fix")
        check("the pre-fix painter DOES stack this one above its own alpha",
              _fp and _fp["raw"]["max"] > _fp["written"] + 12,
              f"written {_fp and _fp['written']}, raw painter reached "
              f"{_fp and _fp['raw']['max']} — this check is not exercising it")
        check("...and paintStrokesStatic holds it AT that alpha, layers ON",
              _fp and _fp["on"]["max"] <= _fp["written"] + 4,
              f"written {_fp and _fp['written']}, painted "
              f"{_fp and _fp['on']['max']} — a posted Skribl must not show a "
              f"stranger brighter ink than its author wrote")
        # LAYERS OFF IS NOT FIXED HERE AND MUST NOT CLAIM TO BE. A run of one
        # colour is a single path either way; a run of many needs a layer to be
        # composited once, and turning layers off is the setting that says paint
        # direct and let it compound. Recorded rather than asserted green.
        check("...covering the same ground as the walk did",
              _fp and abs(_fp["on"]["lit"] - _fp["raw"]["lit"])
                      <= _fp["raw"]["lit"] * 0.02,
              f"raw {_fp and _fp['raw']['lit']} lit, layers-on "
              f"{_fp and _fp['on']['lit']} — compositing must not shrink the ink")

        # ---------------------------------------------------------------- v302b
        # AND THIS SURFACE COUNTS THOSE RUNS AGAINST THE BUDGET TOO. The first
        # v302 taught wetRunFn to layer a field run and taught nothing to count
        # it: `_over` read rgba() only, so a page of forty smudged ghosts put
        # forty full-canvas bakes on every frame -- and on the hold-reveal path
        # that is every animation tick. The stall the shared budget was
        # introduced to close, reopened by the fix for the mesh. Found by review
        # after the seal. Pinned at the boundary from both sides.
        _pb = page.evaluate("""() => {
          const run = (y) => { const seg = [];
            for(let i = 0; i < 24; i++)
              seg.push({ x: 80 + i*11, y: y, color: (i % 2 ? '#ffffff2e' : '#e8e8e82e'),
                         size: 9 + (i % 5), t: i, erase: false, start: i === 0 });
            return seg; };
          // runs 20 px apart so none overlaps its neighbour: the max alpha read
          // below is then one run's own, not two composited
          const doc = (k) => { const out = [];
            for(let s = 0; s < k; s++) out.push.apply(out, run(30 + s*20)); return out; };
          const read = () => { const d = ctx.getImageData(0, 0, canvas.width, canvas.height).data;
            let max = 0; for(let i = 3; i < d.length; i += 4) if(d[i] > max) max = d[i]; return max; };
          const paint = (arr) => { window.SKRIBL_STROKE_LAYERS = true;
            ctx.clearRect(0, 0, canvas.width, canvas.height); paintStrokesStatic(arr); return read(); };
          const sl = window.SkriblStrokeLayers;
          return { written: 0x2e, budget: sl.BUDGET,
                   over25: sl.overBudget(doc(25), parseStrokeAlpha, anyStrokeAlpha),
                   over24: sl.overBudget(doc(24), parseStrokeAlpha, anyStrokeAlpha),
                   max25: paint(doc(25)), max24: paint(doc(24)) };
        }""")
        check("the shared predicate counts a field run: 25 is over, 24 is not",
              _pb and _pb["over25"] is True and _pb["over24"] is False,
              f"{_pb} — with anyAlphaFn ignored, no number of field runs is ever over")
        check("...so at 25 the player paints direct rather than baking 25 layers",
              _pb and _pb["max25"] > _pb["written"] + 12,
              f"written {_pb and _pb['written']}, painted {_pb and _pb['max25']} — "
              f"still layering past the budget, which is the stall on a share link")
        check("...and at 24 it still holds each run at its alpha",
              _pb and _pb["max24"] <= _pb["written"] + 4,
              f"written {_pb and _pb['written']}, painted {_pb and _pb['max24']} — "
              f"a budget that refuses everything would pass the check above alone")

        # ------------------------------------------------------------------
        print("\nTHE SMEAR'S GHOSTS — the same beading, in the one path "
              "neither compositor reaches")
        # A Motion Smear ghost is a translucent stroke whose alpha rides in an
        # 8-DIGIT HEX colour. Both surfaces' layering parsers match rgba() only,
        # deliberately -- a generated page on a per-stroke round trip is the
        # stall v239 fixed -- so no compositor ever sees a ghost, and painted
        # dot-then-line-per-segment it stacked against itself at every joint.
        # Written at alpha 46/255 it came out at 83, and the trail wore a ladder
        # of bright bands. A single canvas path cannot stack against itself and
        # costs FEWER calls than the walk, so it needs no budget.
        #
        # Measured on the ghost alone, not on the page: the pose is opaque and
        # would set `max` by itself.
        flip = br.new_page(viewport={"width": 1280, "height": 950})
        browsing.goto(flip, BASE, "/flip")
        _bd = flip.evaluate("""() => {
          const mk = (x) => ({ strokes: Array.from({ length: 24 }, (_, k) => ({
              x: x + k * 11, y: 120 + (k % 3) * 7, color: '#ffffff', size: 9,
              t: k, erase: false, start: k === 0 })),
            strokeGroups: [24], hold: 1 });
          frames.length = 0; frames.push(mk(80), mk(360));
          idx = 0; fps = 24; subdiv = 1; selSpans = [];
          buildStrip(); render();
          const before = frames.length;
          addTween();
          if (frames.length === before) return null;
          // The brightest ghost: written alpha highest, so stacking shows most.
          const g = frames[1];
          let at = 0, seg = null, best = -1, written = 0;
          for (let k = 0; k < g.strokeGroups.length; k++) {
            const q = g.strokes[at];
            if (q && /^#[0-9a-f]{8}$/i.test(q.color || '') && !/ff$/i.test(q.color)) {
              const av = parseInt(q.color.slice(7, 9), 16);
              if (av > best) { best = av; written = av;
                               seg = g.strokes.slice(at, at + g.strokeGroups[k]); }
            }
            at += g.strokeGroups[k];
          }
          if (!seg) return null;
          const shot = (paint) => {
            const cv = document.createElement('canvas');
            cv.width = CW; cv.height = CH;
            const c = cv.getContext('2d', { willReadFrequently: true });
            paint(c);
            const d = c.getImageData(0, 0, cv.width, cv.height).data;
            let lit = 0, max = 0;
            for (let i = 3; i < d.length; i += 4) {
              if (d[i] <= 8) continue; lit++; if (d[i] > max) max = d[i]; }
            return { lit, max };
          };
          const now = shot(c => paintStatic(c, seg));
          // The pre-fix path, run on purpose: dot, then a line per segment.
          const raw = shot(c => {
            for (let i = 0; i < seg.length; i++) {
              const q = seg[i];
              if (i === 0) drawDot(c, q.x, q.y, q.color, q.size, false);
              else { const v = seg[i-1];
                     drawLine(c, v.x, v.y, q.x, q.y, q.color, q.size, false); }
            }
          });
          return { written, now, raw, pts: seg.length };
        }""")
        check("the smear produced a see-through ghost to measure",
              _bd and _bd["pts"] > 2 and _bd["written"] > 8,
              f"no ghost, or too faint to read: {_bd}")
        # THE MUTATION IS IN THE SUITE, as above: the raw path is run on purpose
        # and REQUIRED to look worse, so this cannot pass on a blank canvas.
        check("the pre-fix painter DOES stack the ghost above its own alpha",
              _bd and _bd["raw"]["max"] > _bd["written"] + 12,
              f"written {_bd and _bd['written']}, raw painter reached "
              f"{_bd and _bd['raw']['max']} — if these match, this check is "
              f"not exercising the beading")
        check("...and the painter in use holds it AT the alpha it was written",
              _bd and _bd["now"]["max"] <= _bd["written"] + 4,
              f"written {_bd and _bd['written']}, painted "
              f"{_bd and _bd['now']['max']} — ink brighter than it was written "
              f"is a run compounding against itself")
        check("...without losing any of the stroke",
              _bd and abs(_bd["now"]["lit"] - _bd["raw"]["lit"]) <= _bd["raw"]["lit"] * 0.02,
              f"{_bd and _bd['raw']['lit']} lit pixels became "
              f"{_bd and _bd['now']['lit']} — one path must cover the same "
              f"ground, not a thinner line")
        # THE PLAYER'S HALF OF THIS IS PINNED WHERE THE PLAYER ACTUALLY RUNS.
        # Its parseStrokeAlpha matches rgba() only too, so before this change it
        # beaded exactly as the editor did -- the surfaces-disagree shape this
        # project keeps meeting. Asserting it from /flip would mean reaching for
        # a painter this page does not load, which is a check that passes by
        # being unreachable. verify_inline drives the real player; the ceiling
        # is pinned there.
        flip.close()

    finally:
        br.close()

bad = [r for r in results if not r[0]]
print(f"\n{'=' * 62}\n{len(results) - len(bad)}/{len(results)} passed"
      + ("" if not bad else "  FAILURES: " + ", ".join(r[1] for r in bad)))
sys.exit(1 if bad else 0)
