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

BASE = os.environ.get("SKRIBL_BASE", "http://127.0.0.1:5001")

try:
    from playwright.sync_api import sync_playwright
except ImportError:                                   # pragma: no cover
    print("SKIP: playwright is not installed")
    sys.exit(0)

results = []


def check(name, ok, detail=""):
    results.append((bool(ok), name))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  — {detail}" if detail else ""))


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
        page.goto(BASE + "/", wait_until="networkidle")
        page.wait_for_timeout(400)

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
    finally:
        br.close()

bad = [r for r in results if not r[0]]
print(f"\n{'=' * 62}\n{len(results) - len(bad)}/{len(results)} passed"
      + ("" if not bad else "  FAILURES: " + ", ".join(r[1] for r in bad)))
sys.exit(1 if bad else 0)
