"""The things a screenshot shows instantly and 1,745 assertions did not.

WHY THIS EXISTS. Three of the last four faults reaching users were visual, and
every one of them passed a full green harness:

  * the editor rendered its header and toolbar over EMPTY SPACE until app.js
    ran, because `.canvas-wrap` was 0px wide until JS sized it;
  * the player showed a 300x150 box — the unstyled <canvas> default — in the
    middle of the page for the same reason;
  * the player CROPPED shared links, setting the wrap to the authored 816px
    inside a 718px column so `overflow: hidden` ate ~100px of drawing.

The suites were thorough about behaviour and blind to appearance. Ink was
counted, playback was driven, page errors were caught — and a viewer looking at
a blank rectangle would have passed all of it.

WHY NOT PIXEL BASELINES. Committed reference PNGs compared per-pixel are the
obvious answer and the wrong one here: font rasterisation, antialiasing and GPU
compositing differ between this container, a developer's laptop and CI, so the
baselines fail for reasons that have nothing to do with the product. A suite
that cries wolf gets its failures ignored, which is worse than no suite — this
tree already learned that lesson from a summary parser that turned failures into
crashes.

WHAT IT DOES INSTEAD. Asserts the GEOMETRY a screenshot would have revealed, all
of which is environment-independent:

  * nothing the user is meant to see is zero-sized or the unstyled default;
  * nothing overflows a clipping ancestor (the crop);
  * the surface is not blank BEFORE app.js runs (both editor and player);
  * the page does not scroll sideways at any width.

Each is checked across viewports, because two of the three bugs above only
appeared at particular widths — the crop needed a viewport WIDER than the app
column, which no fixture had.
"""
import math
import sys

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:5001"
VIEWPORTS = [(1600, 950), (1280, 900), (1023, 931), (830, 914), (420, 850)]

results = []


def check(name, ok, detail=""):
    results.append((bool(ok), name))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  — {detail}" if detail else ""))


# The default size of a <canvas> with no width/height attribute. Seeing this on
# screen means JS has not sized it — it is what both blank-canvas bugs looked
# like, and it is a specific enough number to assert on directly.
UNSTYLED_CANVAS = [300, 150]

FRAME = """() => {
  const w = document.querySelector('.canvas-wrap');
  const c = document.getElementById('canvas');
  if (!w || !c) return null;
  const wr = w.getBoundingClientRect(), cr = c.getBoundingClientRect();
  const cs = getComputedStyle(w);
  return {
    wrap: [Math.round(wr.width), Math.round(wr.height)],
    canvas: [Math.round(cr.width), Math.round(cr.height)],
    // A clipping ancestor turns any overflow into drawing the viewer never sees.
    clipped: Math.round(cr.width) > Math.round(wr.width) + 0.5
          || Math.round(cr.height) > Math.round(wr.height) + 0.5,
    painted: cs.backgroundColor !== 'rgba(0, 0, 0, 0)' && cs.visibility !== 'hidden'
             && parseFloat(cs.opacity || '1') > 0.01,
    offscreen: wr.right < 1 || wr.bottom < 1 || wr.left > window.innerWidth - 1,
    hScroll: document.documentElement.scrollWidth > window.innerWidth + 2,
  };
}"""


def frame_checks(pg, label, vw):
    g = pg.evaluate(FRAME)
    check(f"{label} @{vw}: the canvas frame has a real size",
          g and g["wrap"][0] > 50 and g["wrap"][1] > 50,
          f"wrap {g and g['wrap']} — a zero-sized frame is an empty page")
    check(f"{label} @{vw}: it is not the unstyled canvas default",
          g and g["wrap"] != UNSTYLED_CANVAS and g["canvas"] != UNSTYLED_CANVAS,
          f"{UNSTYLED_CANVAS} means nothing sized it")
    check(f"{label} @{vw}: the drawing is not clipped by its wrapper",
          g and not g["clipped"],
          f"canvas {g and g['canvas']} in wrap {g and g['wrap']} — "
          "overflow:hidden makes the difference invisible, not smaller")
    check(f"{label} @{vw}: the frame is actually painted",
          g and g["painted"] and not g["offscreen"],
          "present in the DOM but transparent or off-screen is still blank")
    check(f"{label} @{vw}: the page does not scroll sideways",
          g and not g["hScroll"],
          "horizontal scroll means something is wider than the viewport")
    return g


def scribble(pg, n=40):
    box = pg.locator("#canvas").bounding_box()
    cx, cy = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
    pg.mouse.move(cx, cy)
    pg.mouse.down()
    for i in range(n):
        a = (i / n) * math.pi * 4
        r = 20 + (i / n) * min(90, box["width"] / 4)
        pg.mouse.move(cx + math.cos(a) * r, cy + math.sin(a) * r * 0.7)
        if i % 5 == 0:
            pg.wait_for_timeout(70)
    pg.mouse.up()


with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={"width": 1280, "height": 900})

    print("VISUAL — the editor is not blank before app.js runs")
    # THE regression. app.js blocked entirely is exactly the window a real
    # visitor sits in while it downloads, and it is what the user photographed.
    for vw, vh in ((1280, 900), (420, 850)):
        pg = ctx.new_page()
        pg.set_viewport_size({"width": vw, "height": vh})
        pg.route("**/app.js*", lambda route: route.abort())
        pg.goto(BASE + "/", wait_until="load")
        pg.wait_for_timeout(500)
        frame_checks(pg, "editor pre-JS", vw)
        pg.close()

    print("\nVISUAL — the editor, settled")
    pg = ctx.new_page()
    pg.goto(BASE + "/", wait_until="load")
    pg.wait_for_timeout(1200)
    for vw, vh in VIEWPORTS:
        pg.set_viewport_size({"width": vw, "height": vh})
        pg.wait_for_timeout(350)
        frame_checks(pg, "editor", vw)
    pg.set_viewport_size({"width": 1280, "height": 900})
    pg.wait_for_timeout(300)

    print("\nVISUAL — author and post, so the player has something real to show")
    pg.click("#recordBtn")
    pg.wait_for_timeout(400)
    scribble(pg)
    pg.wait_for_timeout(400)
    pg.click("#recordBtn")
    pg.wait_for_timeout(600)
    pg.click("#postBtn")
    pg.wait_for_timeout(800)
    pg.fill("#postTitleInput", "visual")
    pg.click("#postSubmitBtn")
    pg.wait_for_timeout(6000)
    link = pg.evaluate("""() => {
        const v = [...document.querySelectorAll('*')].map(e => e.value || e.href || '')
          .find(v => typeof v === 'string' && v.includes('/s/'));
        return v || null; }""")
    check("posting produced a share link (fixture)", bool(link), "no /s/ URL found")
    pg.close()

    if not link:
        print(f"\n{'=' * 62}\n0/1 passed  FAILURES: fixture")
        b.close()
        sys.exit(1)

    print("\nVISUAL — the player is not blank before app.js runs")
    for vw, vh in ((1280, 900), (420, 850)):
        pl = ctx.new_page()
        pl.set_viewport_size({"width": vw, "height": vh})
        pl.route("**/app.js*", lambda route: route.abort())
        pl.goto(link, wait_until="load")
        pl.wait_for_timeout(500)
        frame_checks(pl, "player pre-JS", vw)
        pl.close()

    print("\nVISUAL — the player, settled, across widths")
    # The crop needed a viewport WIDER than .app's max-width. 1600 and 1280 are
    # both wider; 420 is narrower. Checking only one width hid this for months.
    pl = ctx.new_page()
    pl.goto(link, wait_until="load")
    pl.wait_for_timeout(3000)
    for vw, vh in VIEWPORTS:
        pl.set_viewport_size({"width": vw, "height": vh})
        pl.wait_for_timeout(400)
        frame_checks(pl, "player", vw)

    print("\nVISUAL — the player's own controls are visible")
    ctrl = pl.evaluate("""() => {
        const ids = ['playerPlayBtn', 'playerRestartBtn', 'playerLoopBtn'];
        return ids.map(id => {
          const e = document.getElementById(id);
          if (!e) return [id, 'missing'];
          const r = e.getBoundingClientRect();
          const cs = getComputedStyle(e);
          return [id, (r.width > 8 && r.height > 8 && cs.visibility !== 'hidden'
                       && parseFloat(cs.opacity || '1') > 0.01) ? 'visible' : 'not visible'];
        }); }""")
    check("play, restart and loop are all on screen",
          all(state == "visible" for _, state in ctrl), str(ctrl))
    pl.close()
    b.close()

bad = [r for r in results if not r[0]]
print(f"\n{'=' * 62}\n{len(results) - len(bad)}/{len(results)} passed"
      + ("" if not bad else "  FAILURES: " + ", ".join(n for _, n in bad)))
sys.exit(1 if bad else 0)
