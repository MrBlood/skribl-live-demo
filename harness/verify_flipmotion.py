"""Hold-to-riffle scrubbing, and the motion path drawn over the pages.

WHY THESE TWO NEED GUARDING, specifically.

SCRUB cannot go through go(). buildStrip() destroys and rebuilds every tile in
the page strip — each with its own <canvas> and listeners — and redraws every
thumbnail. That is fine for a click and ruinous sixteen times a second, so the
riffle uses goFast() and rebuilds the strip once on key-up. The failure mode if
someone "simplifies" that back to go() is not an exception: it is a strip that
stutters and thumbnails that flicker, which no existing assertion would notice.
So this checks the OUTCOME — that a hold moves many pages and that every
thumbnail is still intact afterwards.

Building it also uncovered two live faults, both of which this pins:

  * ArrowLeft/ArrowRight ALREADY had a handler. Adding a second meant one press
    advanced TWO pages. A tap must move exactly one.
  * `typingTarget` existed three times in flip.js with different definitions —
    one omitted SELECT, one was scoped inside the pan/zoom block where nothing
    else could see it. A shortcut firing while the user is inside a dropdown is
    the bug that produces; so is a ReferenceError on every arrow press.

GUIDES are a view overlay drawn onto the LIVE pad, which is the one surface that
is neither a thumbnail nor an export. That makes "it never reaches anything
published" the assertion that matters — a guide baked into a shared link or a
GIF would be a permanent artefact of a temporary drawing aid. The eyedropper is
the sharp edge: it samples the live pad, so without care it picks the guide's
own colour instead of the drawing's.
"""
import math
import sys

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:5001"

results = []


def check(name, ok, detail=""):
    results.append((bool(ok), name))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  — {detail}" if detail else ""))


# The guide is drawn in a blue-violet no default brush or backdrop uses, so
# counting pixels where blue clearly leads red AND green isolates it.
GUIDE_PX = """(sel) => {
  const c = sel ? document.querySelector(sel) : document.getElementById('pad');
  if (!c) return -1;
  const d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data;
  let n = 0;
  for (let i = 0; i < d.length; i += 4) {
    if (d[i+3] > 10 && d[i+2] > d[i] + 35 && d[i+2] > d[i+1] + 35) n++;
  }
  return n;
}"""


def blob(pg, box, fx, fy):
    cx = box["x"] + box["width"] * fx
    cy = box["y"] + box["height"] * fy
    pg.mouse.move(cx, cy)
    pg.mouse.down()
    for i in range(12):
        a = (i / 12) * math.pi * 2
        pg.mouse.move(cx + math.cos(a) * 24, cy + math.sin(a) * 24)
    pg.mouse.up()


with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1100, "height": 950})
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(BASE + "/flip", wait_until="load")
    pg.wait_for_timeout(1200)

    # Eight pages, the drawing accelerating left to right so the spacing between
    # guide dots is visibly uneven — an even path would not prove much.
    box = pg.locator("#pad").bounding_box()
    PAGES = 8
    for k in range(PAGES):
        blob(pg, box, min(0.12 + 0.028 * k * k, 0.86), 0.55 - 0.03 * k)
        pg.wait_for_timeout(140)
        if k < PAGES - 1:
            pg.evaluate("() => addFrame(false)")
            pg.wait_for_timeout(160)
    PAGES_FIXTURE_POINTS = pg.evaluate("() => frames[0].strokes.length")
    check("fixture built the pages", pg.evaluate("() => frames.length") == PAGES,
          f"{pg.evaluate('() => frames.length')} pages")

    print("\nSCRUB — a tap is one page, a hold is a riffle")
    pg.evaluate("() => go(0)")
    pg.wait_for_timeout(250)
    pg.keyboard.press("ArrowRight")
    pg.wait_for_timeout(250)
    tapped = pg.evaluate("() => idx")
    check("one press advances exactly one page", tapped == 1,
          f"landed on {tapped} — two handlers on the same key double-step")

    pg.evaluate("() => go(0)")
    pg.wait_for_timeout(200)
    pg.keyboard.down("ArrowRight")
    pg.wait_for_timeout(900)
    held = pg.evaluate("() => idx")
    pg.keyboard.up("ArrowRight")
    pg.wait_for_timeout(400)
    check("holding it riffles well past a single step", held >= 4,
          f"reached page {held} in 900ms — a hold that steps once is not a riffle")
    check("releasing leaves the page where the riffle stopped",
          pg.evaluate("() => idx") == held, "the page moved after key-up")

    print("\nSCRUB — the strip survives being driven at flip rate")
    check("every page still has its thumbnail",
          pg.evaluate("() => document.getElementById('strip').querySelectorAll('canvas').length") == PAGES,
          "goFast() must not rebuild the strip; buildStrip() runs once on key-up")
    check("the strip marks the page actually being shown",
          pg.evaluate("""() => [...document.getElementById('strip').children]
                              .findIndex(e => e.classList.contains('on'))""") == held)

    # Counting the rebuilds, not just inspecting the result. A riffle that calls
    # buildStrip() per page still ENDS with an intact strip — it is merely slow
    # and flickery — so every outcome assertion above passes while the thing the
    # design exists to prevent is happening. This is the one that catches it.
    pg.evaluate("""() => {
        window.__bs = 0;
        const orig = window.buildStrip;
        window.__bsOrig = orig;
        window.buildStrip = function () { window.__bs++; return orig.apply(this, arguments); };
    }""")
    pg.evaluate("() => go(0)")
    pg.wait_for_timeout(200)
    pg.evaluate("() => { window.__bs = 0; }")
    pg.keyboard.down("ArrowRight")
    pg.wait_for_timeout(900)
    pg.keyboard.up("ArrowRight")
    pg.wait_for_timeout(400)
    rebuilds = pg.evaluate("() => window.__bs")
    moved = pg.evaluate("() => idx")
    check("a riffle rebuilds the page strip at most once, not per page",
          rebuilds <= 1 and moved >= 4,
          f"{rebuilds} rebuilds across {moved} pages — buildStrip() destroys every "
          "tile, its canvas and its listeners, and redraws every thumbnail")
    pg.evaluate("() => { window.buildStrip = window.__bsOrig; }")

    print("\nSCRUB — a stroke belongs to the page it STARTED on")
    # Reported from the live demo on a phone, as a refusal to share:
    #   'frames[0].strokeGroups' accounts for 0 points, but the strokes array
    #   contains 3.
    # endStroke() and every step after the first point called frame(), which
    # re-reads the CURRENT index — so changing page mid-stroke pushed the
    # remaining points and the group count onto whichever page had become
    # current. One page ended with points and no group, another with a group and
    # no points, and the server correctly refused the payload.
    #
    # The server invariant existed and was right; nothing on the CLIENT checked
    # that the two counts stay in step across an interleaved action. Every
    # fixture drew a stroke and THEN changed page. None did both at once, which
    # is the same gap as the strip-rebuild one: correct final states, untested
    # interleavings.
    COUNTS = """() => frames.map(f => [f.strokes.length,
                    (f.strokeGroups || []).reduce((a, b) => a + b, 0)])"""
    pg.evaluate("() => go(0)")
    pg.wait_for_timeout(250)
    _box = pg.locator("#pad").bounding_box()
    _cx = _box["x"] + _box["width"] * 0.4
    _cy = _box["y"] + _box["height"] * 0.28
    pg.mouse.move(_cx, _cy)
    pg.mouse.down()
    for i in range(3):
        pg.mouse.move(_cx + i * 12, _cy + i * 6)
    pg.keyboard.press("ArrowRight")      # riffle away WHILE the pointer is down
    pg.wait_for_timeout(250)
    pg.mouse.up()
    pg.wait_for_timeout(400)
    _c = pg.evaluate(COUNTS)
    check("changing page mid-stroke leaves every page self-consistent",
          all(pts == acc for pts, acc in _c),
          f"[points, points accounted for] per page: {_c} — a page with points "
          "and no group cannot be shared")

    # And the same interleaving must not corrupt what the payload reports.
    _pay = pg.evaluate("""() => buildSharePayload().frames.map(f =>
        [f.strokes.length, (f.strokeGroups || []).reduce((a, b) => a + b, 0)])""")
    check("and the share payload agrees with itself",
          all(pts == acc for pts, acc in _pay), f"payload: {_pay}")

    # A plain stroke must still be recorded normally — the fix must not have
    # simply stopped recording.
    pg.evaluate("() => go(0)")
    pg.wait_for_timeout(200)
    _before = pg.evaluate(COUNTS)[0][0]
    pg.mouse.move(_cx, _cy + 90)
    pg.mouse.down()
    for i in range(6):
        pg.mouse.move(_cx + i * 14, _cy + 90)
    pg.mouse.up()
    pg.wait_for_timeout(400)
    _after = pg.evaluate(COUNTS)[0]
    check("an ordinary stroke is still recorded, and accounted for",
          _after[0] > _before and _after[0] == _after[1],
          f"{_before} -> {_after}")

    # Put the fixture back. The two strokes above land on page 0 and move its
    # centre of mass, which the spacing assertions further down read — a test
    # that quietly changes the fixture for the tests after it is its own bug.
    pg.evaluate("() => { go(0); undoStroke(); undoStroke(); }")
    pg.wait_for_timeout(400)
    check("the fixture is restored for the assertions that follow",
          pg.evaluate(COUNTS)[0][0] == PAGES_FIXTURE_POINTS,
          f"page 0 has {pg.evaluate(COUNTS)[0][0]} points, expected "
          f"{PAGES_FIXTURE_POINTS} — later spacing checks read this page")

    print("\nSCRUB — the ends are ends")
    pg.keyboard.down("ArrowLeft")
    pg.wait_for_timeout(1400)
    pg.keyboard.up("ArrowLeft")
    pg.wait_for_timeout(400)
    check("holding back stops at the first page and does not wrap",
          pg.evaluate("() => idx") == 0, f"idx {pg.evaluate('() => idx')}")

    print("\nGUIDES — off by default, drawn when asked")
    pg.evaluate("() => go(3)")
    pg.wait_for_timeout(300)
    off = pg.evaluate(GUIDE_PX, None)
    check("nothing is drawn while the guides are off", off == 0, f"{off} guide pixels")
    pg.evaluate("() => setTune(true)")
    pg.wait_for_timeout(350)
    pg.click("#arcGuideBtn")
    pg.wait_for_timeout(300)
    pg.evaluate("() => setTune(false)")
    pg.wait_for_timeout(400)
    on = pg.evaluate(GUIDE_PX, None)
    check("switching them on draws a path", on > 100, f"{on} guide pixels")
    check("the control reports its state to assistive tech",
          pg.get_attribute("#arcGuideBtn", "aria-checked") == "true")
    # ...and reports it VISUALLY with a class the stylesheet actually styles.
    # The handler used to toggle 'on' while flip.css lights .onion-tint via
    # .active — aria flipped, the canvas drew guides, and the switch looked
    # permanently off. Computed color, not class name, so renaming the class
    # in CSS+JS together stays legal while a re-split fails here.
    lit = pg.evaluate("""() => {
        const b = document.getElementById('arcGuideBtn');
        const rest = document.createElement('button');
        rest.className = 'onion-tint'; b.parentElement.appendChild(rest);
        const a = getComputedStyle(b).color, r = getComputedStyle(rest).color;
        rest.remove(); return a !== r; }""")
    check("...and the switch itself lights up while the guides are on", lit,
          "computed color of the enabled switch equals the resting style")

    print("\nGUIDES — the path tracks the drawing, and spacing shows speed")
    cents = pg.evaluate("""() => frames.map(f => {
        const c = frameCentroid(f); return c ? Math.round(c.x) : null; })""")
    check("every page yields a centre of mass", all(c is not None for c in cents), str(cents))
    gaps = [cents[i + 1] - cents[i] for i in range(len(cents) - 1)]
    check("the path advances in the direction the drawing moves",
          all(g >= 0 for g in gaps), f"gaps {gaps}")
    check("uneven spacing survives into the guide (this fixture accelerates)",
          max(gaps) > min(gaps) * 2,
          f"gaps {gaps} — even gaps would mean the spacing chart says nothing")

    print("\nGUIDES — never reach anything published")
    # THE assertion. A guide baked into a thumbnail, an export or a shared link
    # would be a permanent artefact of a temporary drawing aid.
    thumbs = pg.evaluate("""() => {
        const out = [];
        document.getElementById('strip').querySelectorAll('canvas').forEach(c => {
          const d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data;
          let n = 0;
          for (let i = 0; i < d.length; i += 4)
            if (d[i+3] > 10 && d[i+2] > d[i] + 35 && d[i+2] > d[i+1] + 35) n++;
          out.push(n);
        });
        return out; }""")
    check("no guide pixel appears in any thumbnail", sum(thumbs) == 0, f"{thumbs}")
    check("the posted payload carries no guide state",
          "arcGuides" not in pg.evaluate("() => JSON.stringify(buildSharePayload())"),
          "view state must not be persisted or posted")

    print("\nARTWORK vs OVERLAYS — colour picking reads the drawing, not the aids")
    # The pad is a PRESENTATION surface: artwork plus editor overlays. Anything
    # that reads a colour or writes a file must read the ARTWORK stage instead.
    #
    # This was a live bug before the stage existed, and NOT the one that was
    # noticed: fixing the motion guides with a suppress-and-repaint flag left
    # onion skin sampling untouched. Measured then — draw a red ring, add a
    # page, sample where only the onion shows — the eyedropper returned #561317,
    # the onion's red at reduced alpha over the backdrop, a colour present
    # nowhere in the artwork. Patching per overlay would have needed repeating
    # for every future one; the assertion below is written against the RULE.
    pg.evaluate("() => go(0)")
    pg.wait_for_timeout(200)
    pg.evaluate("() => setColor('#ff2020')")
    pg.wait_for_timeout(150)
    blob(pg, box, 0.30, 0.5)
    pg.wait_for_timeout(250)
    pg.evaluate("() => addFrame(false)")
    pg.wait_for_timeout(300)
    pg.evaluate("() => setColor('#ffffff')")
    pg.wait_for_timeout(150)
    blob(pg, box, 0.75, 0.5)
    pg.wait_for_timeout(350)
    check("onion skin is showing (fixture)", pg.evaluate("() => onion") is True)

    # The reddest pixel on the pad can only be onion skin: nothing on this page
    # is red, and the guide is violet.
    spot = pg.evaluate("""() => {
        const c = document.getElementById('pad');
        const d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data;
        let best = -1, at = null;
        for (let i = 0, px = 0; i < d.length; i += 4, px++) {
          const sc = d[i] - Math.max(d[i+1], d[i+2]);
          if (sc > best) { best = sc; at = [px % c.width, (px / c.width) | 0, best]; }
        }
        return at; }""")
    check("the onion skin is visible on the pad (fixture)", spot and spot[2] > 20,
          f"reddest pixel scores {spot and spot[2]}")
    picked = pg.evaluate("""(pt) => {
        const c = document.getElementById('pad'), b = c.getBoundingClientRect();
        const ev = { clientX: b.left + pt[0] * (b.width / c.width),
                     clientY: b.top + pt[1] * (b.height / c.height) };
        const before = color; sampleColorAt(ev); return { before, after: color }; }""", spot)
    check("sampling an ONION pixel does not pick the onion's colour",
          picked["after"].lower() in ("#0d0f14", "#ffffff", "#ff2020"),
          f"picked {picked['after']} — a ghost of the previous page is not artwork")

    print("\nARTWORK vs OVERLAYS — and the guides get the same rule for free")
    # It reads the live pad, the one surface guides are drawn on.
    picked = pg.evaluate("""async () => {
        const c = document.getElementById('pad');
        const ct = frameCentroid(frames[idx]);
        const r = c.getBoundingClientRect();
        const ev = { clientX: r.left + ct.x * (r.width / c.width) / (window.devicePixelRatio || 1),
                     clientY: r.top + ct.y * (r.height / c.height) / (window.devicePixelRatio || 1) };
        const before = color;
        sampleColorAt(ev);
        return { before, after: color }; }""")
    check("sampling on the guide does not pick the guide's colour",
          picked["after"].lower() not in ("#7d7dff", "#a08cff"),
          f"picked {picked['after']} — the pad must be repainted without guides first")
    check("guides are still shown after sampling",
          pg.evaluate(GUIDE_PX, None) > 100, "the suppression flag was not cleared")

    check("no page errors throughout", not errs, "; ".join(errs[:2]))
    pg.close()
    b.close()

bad = [r for r in results if not r[0]]
print(f"\n{'=' * 62}\n{len(results) - len(bad)}/{len(results)} passed"
      + ("" if not bad else "  FAILURES: " + ", ".join(n for _, n in bad)))
sys.exit(1 if bad else 0)
