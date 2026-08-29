"""v230 — Fill, and the constraint that shaped it.

WHY THIS TOOL IS INTERESTING. A Skribl frame is `{strokes, strokeGroups}` — a
flat array of `{x, y, color, size, t, erase, start}` — and the player replays
those points and nothing else. There is no fill primitive. Adding one is a
format change the player must honour, which is the owner's call, so Fill earns
its place by producing STROKES, the way Shape already turns a drag into a path.

The saving is that `paintSeg()` draws `drawLine(prev -> point)` at
`lineWidth = size`, so a horizontal band of the region costs TWO POINTS, not one
per pixel. That is the difference between a tap that emits ~50 points and one
that blows the server's 20,000-point-per-frame limit outright, and it is the
single fact the whole design rests on. It is asserted below.

WHAT ROTS QUIETLY HERE, and what each section is really for:

  * A fill that leaks past its boundary still LOOKS like a fill in a screenshot
    if you only check the inside. Both sides are measured.
  * Round caps overshoot each run by size/2. Without the inset, every fill
    grows a halo the width of the brush — visible only where the region meets a
    line, which is everywhere that matters and nowhere a "did it fill?" check
    looks.
  * Tolerance anchored to the NEIGHBOUR rather than the seed lets a gradient
    walk the whole canvas: every step is within tolerance of the last while the
    end is nothing like the start. A fill that escapes its region passes any
    assertion that only asks whether the seed point changed colour.
  * One tap must be ONE undo. The fill lands as many groups on purpose; if undo
    pops them one at a time the tool is unusable, and nothing about the pixels
    would tell you.
  * strokeGroups must account for every point or the server refuses the share
    with "accounts for N points, but the strokes array contains M". A tool that
    pushes points and forgets a group count is caught here rather than by a
    user trying to post.
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


STATE = "() => ({ pts: frame().strokes.length, groups: frame().strokeGroups.length })"
PIX = """([x, y]) => { const d = ctx.getImageData(Math.round(x * DPR), Math.round(y * DPR), 1, 1).data;
                      return [d[0], d[1], d[2], d[3]]; }"""

with sync_playwright() as p:
    br = p.chromium.launch()
    try:
        page = br.new_page(viewport={"width": 1280, "height": 900})
        errs = []
        page.on("pageerror", lambda e: errs.append(str(e)))
        page.goto(BASE + "/flip", wait_until="networkidle")
        page.wait_for_timeout(700)

        print("\nTHE LIB — geometry, separable from the canvas")
        check("lib/floodfill.js is loaded on Flip",
              page.evaluate("() => typeof window.SkriblFloodFill") == "object",
              "a lib the template does not list is a lib that does not exist")
        check("fill is in Flip's tool registry",
              "fill" in page.evaluate("() => SkriblFlipTools.list()"),
              str(page.evaluate("() => SkriblFlipTools.list()")))

        # A run is two points, and that is the entire cost model. Asserted on
        # the pure function so it cannot drift behind a canvas.
        pts = page.evaluate("""() => SkriblFloodFill.points({y: 10, x0: 0, x1: 100}, 8)""")
        check("a run costs TWO points, not one per pixel",
              len(pts) == 2, f"{pts} — per-pixel rasterising would put a single "
              "tap over the server's 20,000-point frame limit")
        check("...and they are inset for the round caps",
              abs(pts[0]["x"] - 4) < 0.01 and abs(pts[1]["x"] - 96) < 0.01,
              f"{pts} — round caps extend size/2 past each end, so a run drawn "
              "to its true extent bleeds half a brush past the boundary")
        short = page.evaluate("""() => SkriblFloodFill.points({y: 5, x0: 0, x1: 3}, 8)""")
        check("a run shorter than its own width collapses to a dot",
              len(short) == 1, f"{short} — inset past itself it would draw "
              "backwards; drawDot paints one point at the same width")

        print("\nTHE TOLERANCE IS ANCHORED TO THE SEED, NOT THE NEIGHBOUR")
        # A horizontal gradient. Neighbour-relative tolerance walks it end to
        # end because each step is tiny; seed-relative stops where the colour
        # has actually travelled far enough.
        walked = page.evaluate("""() => {
          const W = 256, H = 8;
          const img = new ImageData(W, H);
          for (let y = 0; y < H; y++)
            for (let x = 0; x < W; x++) {
              const i = (y * W + x) * 4;
              img.data[i] = x; img.data[i+1] = x; img.data[i+2] = x; img.data[i+3] = 255;
            }
          const r = SkriblFloodFill.runs(img, 0, 4, { tolerance: 8, rowStep: 4 });
          let maxX = 0;
          for (const run of r.runs) if (run.x1 > maxX) maxX = run.x1;
          return { maxX: maxX, filled: r.filled };
        }""")
        check("a gradient does not let the fill walk the whole canvas",
              walked["maxX"] < 60,
              f"reached x={walked['maxX']} of 255 — neighbour-relative tolerance "
              "spreads forever across a gradient; seed-relative stops")

        print("\nON THE CANVAS — it fills inside and stops at the line")
        b = page.locator("#pad").bounding_box()
        cx, cy = b["x"] + b["width"] / 2, b["y"] + b["height"] / 2
        page.mouse.move(cx - 90, cy - 70)
        page.mouse.down()
        for pt in ((cx + 90, cy - 70), (cx + 90, cy + 70), (cx - 90, cy + 70), (cx - 90, cy - 70)):
            page.mouse.move(pt[0], pt[1])
        page.mouse.up()
        page.wait_for_timeout(400)
        before = page.evaluate(STATE)
        inside_before = page.evaluate(PIX, [cx - b["x"], cy - b["y"]])

        page.evaluate("() => setTool('fill')")
        page.wait_for_timeout(200)
        check("the fill tool takes a pointer cursor, not the brush ring",
              page.evaluate("() => pad.style.cursor") == "crosshair",
              "'none' hides the system cursor for a brush ring fill never draws")

        page.mouse.click(cx, cy)
        page.wait_for_timeout(700)
        after = page.evaluate(STATE)
        inside_after = page.evaluate(PIX, [cx - b["x"], cy - b["y"]])
        outside = page.evaluate(PIX, [cx - b["x"] - 150, cy - b["y"]])

        check("the inside of the box changed colour",
              inside_after != inside_before and inside_after[0] > 200,
              f"{inside_before} -> {inside_after}")
        check("and the outside did NOT",
              outside == inside_before,
              f"{outside} vs {inside_before} — a fill that escapes its region "
              "still looks right if you only sample the inside")

        added_pts = after["pts"] - before["pts"]
        added_grp = after["groups"] - before["groups"]
        check("the fill is cheap — two points per band",
              added_pts == added_grp * 2 and added_pts < 400,
              f"{added_pts} points across {added_grp} bands")

        print("\nONE TAP IS ONE UNDO")
        page.evaluate("() => undoStroke()")
        page.wait_for_timeout(400)
        u = page.evaluate(STATE)
        check("a single undo takes the whole fill back",
              u == before,
              f"{u} vs {before} — the fill lands as many groups on purpose; "
              f"popping them one at a time would need {added_grp} undos")
        page.evaluate("() => redoStroke()")
        page.wait_for_timeout(400)
        r = page.evaluate(STATE)
        check("and a single redo puts it back",
              r == after, f"{r} vs {after}")

        print("\nTHE SHARE INVARIANT — groups account for every point")
        acc = page.evaluate("""() => { const f = frame();
            return [f.strokeGroups.reduce((a, b) => a + b, 0), f.strokes.length]; }""")
        check("strokeGroups accounts for every point on the page",
              acc[0] == acc[1],
              f"{acc[0]} of {acc[1]} — the server refuses a share whose groups "
              "and points disagree, and this is the exact shape of that bug")

        check("no page error through any of it", not errs, "; ".join(errs[:2]))
    finally:
        br.close()

bad = [r for r in results if not r[0]]
print(f"\n{'=' * 62}\n{len(results) - len(bad)}/{len(results)} passed"
      + ("" if not bad else "  FAILURES: " + ", ".join(n for _, n in bad)))
sys.exit(1 if bad else 0)
