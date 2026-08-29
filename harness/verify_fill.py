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
        pts = page.evaluate("""() => SkriblFloodFill.points({y: 10, x0: 0, x1: 100, h: 7})""")
        check("a run costs TWO points, not one per pixel",
              len(pts) == 2, f"{pts} — per-pixel rasterising would put a single "
              "tap over the server's 20,000-point frame limit")
        # ⚑ REVERSED, v233, and deliberately. This used to assert an INSET of
        # half the lineWidth, to stop round caps bleeding past the boundary.
        # That is true of the line's centre row and false everywhere else: a cap
        # is a semicircle, so the stadium narrows toward the top and bottom of a
        # thick line and an inset run leaves its own corners bare. Measured on a
        # filled circle, 52 of 7845 pixels. Runs are drawn full-extent now and
        # the cap bulges outward instead — bleed rather than gaps, which is the
        # trade nobody reports.
        check("...and they run to the region's full extent, not inset",
              abs(pts[0]["x"] - 0) < 0.01 and abs(pts[1]["x"] - 100) < 0.01,
              f"{pts} — inset to the exact extent, a thick run cannot cover its "
              "own corners")
        short = page.evaluate("""() => SkriblFloodFill.points({y: 5, x0: 3, x1: 3, h: 7})""")
        check("a zero-length run collapses to a dot",
              len(short) == 1, f"{short} — drawDot paints one point at the same "
              "width; a one-pixel sliver of region is not an artefact")

        # THE REGRESSION THAT SHIPPED. The first version banded every 6 pixel
        # rows and gave the band the UNION of their extents. On a slope the
        # union is wider than the narrow rows, the cap inset then pulls each
        # run's ends back, and where the region is narrow the run comes out
        # shorter than its own width and collapses to a DOT. Down a diagonal
        # that is a perforated line, which is what the first fill on the live
        # demo drew. Grouping by exact extent is what fixes it, and this is the
        # assertion that says so on the geometry rather than on pixels.
        tri = page.evaluate("""() => {
          // a right triangle: row y spans x from 0 to y
          const W = 64, H = 64;
          const img = new ImageData(W, H);
          for (let y = 0; y < H; y++)
            for (let x = 0; x < W; x++) {
              const i = (y * W + x) * 4, inside = x <= y;
              img.data[i] = inside ? 255 : 0; img.data[i+1] = inside ? 255 : 0;
              img.data[i+2] = inside ? 255 : 0; img.data[i+3] = 255;
            }
          const r = SkriblFloodFill.runs(img, 1, 40, { tolerance: 8 });
          let dots = 0, covered = 0;
          for (const run of r.runs) {
            if (SkriblFloodFill.points(run).length === 1) dots++;
            covered += run.h;
          }
          return { runs: r.runs.length, dots: dots, covered: covered,
                   heights: r.runs.slice(0, 4).map(x => x.h) };
        }""")
        check("a diagonal edge produces one run PER ROW, not a banded union",
              all(h == 1 for h in tri["heights"]),
              f"heights {tri['heights']} — a run taller than the rows whose "
              f"extent it shares is the union that perforated the edge")
        check("...and every row of the region is covered exactly once",
              tri["covered"] == 64,
              f"{tri['covered']} rows covered of 64 — a gap here is a hole in "
              "the fill and an overlap double-darkens a translucent seam")
        # NOT zero, and the distinction is the whole point. This triangle's top
        # rows really are one and two pixels wide, so a dot there is an honest
        # sliver. What the bug produced was a dot in most bands ALONG the slope,
        # where the region is dozens of pixels wide and only the banded union
        # made the run look short. Confining them to the apex is the fix.
        check("collapsed dots are confined to genuinely narrow rows",
              tri["dots"] <= 3,
              f"{tri['dots']} of {tri['runs']} runs collapsed to a point — a "
              "handful at the apex is real geometry; a line of them down the "
              "edge IS the reported dotted line")

        # A flat region is the other half of the same claim: grouping by extent
        # has to be CHEAPER on ordinary shapes, or it has just traded one
        # problem for a bill.
        box = page.evaluate("""() => {
          const W = 64, H = 64;
          const img = new ImageData(W, H);
          for (let y = 0; y < H; y++)
            for (let x = 0; x < W; x++) {
              const i = (y * W + x) * 4, inside = (x > 8 && x < 56 && y > 8 && y < 56);
              img.data[i] = inside ? 255 : 0; img.data[i+1] = inside ? 255 : 0;
              img.data[i+2] = inside ? 255 : 0; img.data[i+3] = 255;
            }
          const r = SkriblFloodFill.runs(img, 32, 32, { tolerance: 8 });
          let tallest = 0;
          for (const run of r.runs) if (run.h > tallest) tallest = run.h;
          return { runs: r.runs.length, tallest: tallest };
        }""")
        # ⚑ CHANGED, v233. This asserted ONE run for a 47-row box and that was
        # the bug's other half: a group that tall is drawn at lineWidth 48 with
        # ROUND caps, so it covers a stadium and leaves ~2px of every corner
        # bare. On a circle, whose widest rows repeat their extent and so form
        # the tallest groups, that read as dashes at the far left and right.
        # Groups are capped at MAX_GROUP_H now, so the claim is bounded height,
        # not minimum count.
        # Bounded height, NOT an exact run count. The count moves whenever the
        # cap or the dilation changes -- it has already moved twice -- and an
        # assertion that has to be edited every time the implementation is
        # tuned stops meaning anything. What must hold is that no group is tall
        # enough for round caps to leave its corners bare.
        check("no run is taller than the cap",
              box["tallest"] <= 3 and box["runs"] > 1,
              f"{box} — an unbounded group is drawn at its own height with "
              "round caps, and a tall stadium cannot cover a rectangle's corners")

        # THE ASSERTION THAT WOULD HAVE CAUGHT THE SECOND ROUND OF THIS BUG.
        # Everything above is about the runs' GEOMETRY. None of it notices that
        # drawLine paints a STADIUM, not a rectangle: near the top and bottom of
        # a thick line the round caps curve inward, so a tall run cannot cover
        # its own corners. A circle's widest rows repeat their extent and so
        # form the tallest groups, which is why the bare corners appeared at the
        # far left and right of a filled circle and nowhere else.
        #
        # So this rasterises the runs exactly as flip.js draws them and counts
        # mask pixels the paint misses. It is the only check here that sees the
        # renderer rather than the plan.
        cover = page.evaluate("""() => {
          const W = 120, H = 120, cx = 60, cy = 60, rr = 50;
          const img = new ImageData(W, H);
          for (let y = 0; y < H; y++)
            for (let x = 0; x < W; x++) {
              const i = (y * W + x) * 4;
              const inside = (x - cx) * (x - cx) + (y - cy) * (y - cy) <= rr * rr;
              img.data[i] = inside ? 255 : 0; img.data[i+1] = inside ? 255 : 0;
              img.data[i+2] = inside ? 255 : 0; img.data[i+3] = 255;
            }
          const r = SkriblFloodFill.runs(img, cx, cy, { tolerance: 8 });
          const cv = document.createElement('canvas'); cv.width = W; cv.height = H;
          const c = cv.getContext('2d');
          c.lineCap = 'round'; c.lineJoin = 'round'; c.strokeStyle = '#fff';
          for (const run of r.runs) {
            const pts = SkriblFloodFill.points(run);
            c.lineWidth = SkriblFloodFill.sizeOf(run);
            c.beginPath();
            if (pts.length === 1) { c.moveTo(pts[0].x, pts[0].y); c.lineTo(pts[0].x, pts[0].y); }
            else { c.moveTo(pts[0].x, pts[0].y); c.lineTo(pts[1].x, pts[1].y); }
            c.stroke();
          }
          const got = c.getImageData(0, 0, W, H).data;
          let missed = 0, area = 0, worstY = -1;
          for (let y = 0; y < H; y++)
            for (let x = 0; x < W; x++) {
              if ((x - cx) * (x - cx) + (y - cy) * (y - cy) > rr * rr) continue;
              area++;
              if (got[(y * W + x) * 4 + 3] < 40) { missed++; if (worstY < 0) worstY = y; }
            }
          return { missed: missed, area: area, runs: r.runs.length };
        }""")
        check("the runs actually COVER the region when painted",
              cover["missed"] <= cover["area"] * 0.002,
              f"{cover['missed']} of {cover['area']} filled pixels left bare "
              f"across {cover['runs']} runs — round caps make a run a stadium, "
              "so a tall group cannot reach its own corners; this is the check "
              "that sees the renderer rather than the plan")

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

        # A CURVED boundary, drawn fresh, because the fringe only exists where
        # anti-aliasing does. The box above is axis-aligned: its edges barely
        # anti-alias, so a fringe check against it passes on a build with the
        # bug in it — verified by mutation, which is the only reason this
        # section exists separately at all.
        page.evaluate("() => { localStorage.clear(); }")
        page.reload(wait_until="networkidle")
        page.wait_for_timeout(800)
        eb = page.locator("#pad").bounding_box()
        ecx, ecy = eb["x"] + eb["width"] / 2, eb["y"] + eb["height"] / 2
        page.evaluate("() => { setTool('shape'); shapeKind = 'ellipse'; }")
        page.wait_for_timeout(200)
        page.mouse.move(ecx - 110, ecy - 90)
        page.mouse.down()
        page.mouse.move(ecx + 110, ecy + 90)
        page.mouse.up()
        page.wait_for_timeout(400)
        page.evaluate("() => setTool('fill')")
        page.wait_for_timeout(200)
        page.mouse.click(ecx, ecy)
        page.wait_for_timeout(700)

        # THE FRINGE, which is what the third round of this report was about.
        # A drawn line is anti-aliased, so the flood stops a pixel or two
        # OUTSIDE its solid core and the two never meet. The fill paints on top
        # of the line, so wherever it fails to reach, the leftover fringe shows
        # as a dark thread just inside the edge — ragged, because the flood's
        # stopping point jitters row to row, which is why it read as DOTTED.
        # GROW is what closes it. Measured on the real canvas rather than on a
        # synthetic mask, because the fringe only exists once something has
        # actually been drawn with anti-aliasing.
        gap = page.evaluate("""() => {
          // Walk outward from the centre along several rays. Between the fill
          // and the stroke there must be no run of BACKGROUND pixels: that gap
          // is the bug, and its width is how visible it was.
          const d = ctx.getImageData(0, 0, pad.width, pad.height).data;
          const W = pad.width, H = pad.height;
          const cx = Math.round(W / 2), cy = Math.round(H / 2);
          const dark = (x, y) => { const i = (y * W + x) * 4;
            return d[i] < 90 && d[i+1] < 90 && d[i+2] < 90; };
          let worst = 0;
          for (let a = 0; a < 24; a++) {
            const th = a * Math.PI / 12;
            let run = 0, seenInk = false, worstRay = 0;
            for (let r = 4; r < Math.min(W, H) / 2; r++) {
              const x = Math.round(cx + Math.cos(th) * r), y = Math.round(cy + Math.sin(th) * r);
              if (x < 0 || y < 0 || x >= W || y >= H) break;
              if (dark(x, y)) { run++; }
              else { if (run > 0 && seenInk) worstRay = Math.max(worstRay, run); run = 0; seenInk = true; }
            }
            worst = Math.max(worst, worstRay);
          }
          return worst;
        }""")
        check("no gap of background survives between the fill and the line",
              gap <= 2,
              f"widest run of background pixels enclosed by ink: {gap} — the "
              "flood stops at the line's anti-aliased fringe, so without GROW "
              "the fill and the line never meet and the fringe shows through "
              "as the dotted thread that was reported three times")

        check("no page error through any of it", not errs, "; ".join(errs[:2]))
    finally:
        br.close()

bad = [r for r in results if not r[0]]
print(f"\n{'=' * 62}\n{len(results) - len(bad)}/{len(results)} passed"
      + ("" if not bad else "  FAILURES: " + ", ".join(n for _, n in bad)))
sys.exit(1 if bad else 0)
