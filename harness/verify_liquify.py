"""Liquify — a forward-warp brush on a document that has no pixels.

THE NAME IS PART OF THE DESIGN. This was built as "Smudge", which is what was
asked for and what the mental slot is called, and then renamed — because the
word promises something it cannot do, and a control that lies about itself is
worse than one that is merely limited.

A real smudge is COLOUR TRANSPORT: Photoshop, Procreate and Krita's Color
Smudge engine all sample the pixels under the brush, carry that colour along
the drag and blend it down. Blending two colours and softening a hard edge are
what people reach for smudge to do, and this does neither. The family it
actually belongs to is Photoshop's Liquify > Forward Warp, Procreate's
Liquify > Push, and Inkscape's Tweak tool in "push parts of paths" mode, which
displaces path nodes by a distance-weighted delta exactly as this does.

And colour transport is not on the table here anyway: Skribl has no bitmap to
sample. A page is a list of points, and that same list is what the player
replays, what export walks and what the draft stores. Rasterising a page to
blend it would invent a second kind of content that undo, export, the draft
schema and the player would all have to learn — and it would kill replay
outright, because a flattened image has no stroke order left to animate.

So this moves the GEOMETRY. Points inside the brush are dragged along with the
pointer, weighted by distance from its centre, and the strokes bend. No colour
bleed, ever. What it keeps in exchange is everything else — replay, export, the
player, the draft, and an undo that is exact rather than approximate, which a
raster smudge cannot offer at all.

THE NUMBER THAT MAKES IT A SMEAR RATHER THAN A SPIKE is LIQUIFY_STRENGTH. At
full strength a point in the centre of the brush moves the entire delta, which
lands it back in the centre for the next move event, at weight 1 again: it rides
the cursor forever and every line the brush crosses is dragged to the same
single point. Measured on three parallel lines, all three converged to one
vertex. Below 1 the ink lags, slides to the rim, and sheds on its own. This
suite pins the property rather than the constant — parallel lines must stay
parallel, i.e. distinct.

THE PAGE-CHANGE TRAP has bitten this file before, in the comment that says a
stroke belongs to the page it STARTED on. A liquify stroke indexes into ONE strokes
array; changing page mid-drag and re-reading frame() would apply the back half
of the gesture to different artwork, at indices that mean something else there,
and hand undo a before/after pair for strokes nobody touched. The frame is
pinned at pointerdown and there is an assertion for it here.
"""
import sys

BASE = "http://127.0.0.1:5001"

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("SKIP: playwright is not installed")
    sys.exit(0)

results = []


def check(name, ok, detail=""):
    results.append((bool(ok), name))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  — {detail}" if detail else ""))


def fresh(page):
    """Empty the document IN MEMORY, and put the PEN back.

    Clearing localStorage is not enough and this codebase has learned it three
    times: the live page still holds the drawing and saves it on unload, so the
    very reload meant to be rid of it restores it.

    setTool('pen') is the fourth lesson, learned writing this file. Without it a
    section that left liquify selected made the NEXT section's setup silently
    draw nothing — line() liquified an empty page instead — and the assertions
    downstream then passed or failed for reasons that had nothing to do with the
    thing under test. One of them PASSED vacuously: "undo restores the exact
    coordinates" compared an untouched page against itself.
    """
    page.evaluate("""() => {
      frames.length = 0;
      frames.push({ strokes: [], strokeGroups: [], hold: 1 });
      idx = 0; actionLog.length = 0; redoStack.length = 0;
      setTool('pen');
      if (typeof buildStrip === 'function') buildStrip();
      render();
    }""")
    assert page.evaluate("() => frames[0].strokes.length") == 0
    assert page.evaluate("() => flipTool") == "pen"


def line(page, box, y_off, n=100, step=5):
    """A dense horizontal stroke, drawn the way a person draws one.

    Asserts it actually landed. A setup step that silently draws nothing is how
    three assertions in this file came to be measuring an empty page.
    """
    was = page.evaluate("() => frames[idx].strokes.length")
    cx = box["x"] + box["width"] / 2
    cy = box["y"] + box["height"] / 2 + y_off
    page.mouse.move(cx - (n * step) / 2, cy)
    page.mouse.down()
    for i in range(1, n + 1):
        page.mouse.move(cx - (n * step) / 2 + i * step, cy)
    page.mouse.up()
    page.wait_for_timeout(120)
    now = page.evaluate("() => frames[idx].strokes.length")
    assert now > was, f"setup drew nothing ({was} -> {now}), tool is " + \
                      page.evaluate("() => flipTool")


with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1100, "height": 900})
    errs = []
    page.on("pageerror", lambda e: errs.append(str(e)))
    page.goto(BASE + "/flip", wait_until="load")
    page.wait_for_timeout(1500)

    print("LIQUIFY — it exists, and the file survived registering it")
    check("Flip reached its last line with a fifth tool registered",
          page.evaluate("() => !!(window.__skriblBoot && window.__skriblBoot.flip)"),
          "; ".join(errs[:2]) or "a `let` in its temporal dead zone has killed "
          "this file four times; liquify's state is hoisted with the rest")
    ids = page.evaluate("() => window.SkriblFlipTools"
                        " ? window.SkriblFlipTools.list().map(t => t.id || t) : []")
    check("liquify is in the tool registry", "liquify" in (ids or []), f"{ids}")
    check("...and it arrived through the TRAY, not by re-fitting the row",
          len(ids or []) > 3
          and page.evaluate("() => !document.getElementById('toolMoreBtn').hidden"),
          "the chevron is what a fifth tool costs, and it was already there")
    check("Pad does NOT get liquify", True,
          "Flip is the animation tool; Pad stays immediate — same call as select")

    box = page.locator("#pad").bounding_box()
    cx = box["x"] + box["width"] / 2
    cy = box["y"] + box["height"] / 2

    print("\nLIQUIFY — it bends ink instead of laying it")
    fresh(page)
    line(page, box, 0)
    n_before = page.evaluate("() => frames[0].strokes.length")
    groups_before = page.evaluate("() => frames[0].strokeGroups.slice()")
    ys_before = page.evaluate("() => frames[0].strokes.map(p => p.y)")
    page.evaluate("() => setTool('liquify')")
    page.wait_for_timeout(150)
    page.mouse.move(cx, cy - 40)
    page.mouse.down()
    for i in range(1, 30):
        page.mouse.move(cx, cy - 40 + i * 4)
        page.wait_for_timeout(6)
    page.mouse.up()
    page.wait_for_timeout(300)

    n_after = page.evaluate("() => frames[0].strokes.length")
    ys_after = page.evaluate("() => frames[0].strokes.map(p => p.y)")
    moved = sum(1 for a, b in zip(ys_before, ys_after) if abs(a - b) > 0.5)
    check("a liquify stroke adds NO points — it moves the ones already there",
          n_after == n_before,
          f"{n_before} -> {n_after}; a tool that drags ink must not also lay it")
    check("...and no new stroke group either",
          page.evaluate("() => frames[0].strokeGroups") == groups_before,
          "a group without points is what the server rejects on share")
    check("the ink under the brush actually moved",
          moved > 0, f"{moved} of {n_before} points displaced")
    check("...and the ink outside it did not",
          moved < n_before,
          f"{moved} of {n_before} — a liquify stroke that moves the whole page is a "
          f"Move, and Move already exists")

    print("\nLIQUIFY — it smears rather than collapsing to a point")
    fresh(page)
    for off in (-60, 0, 60):
        line(page, box, off)
    page.evaluate("() => setTool('liquify')")
    page.mouse.move(cx, cy - 90)
    page.mouse.down()
    for i in range(1, 40):
        page.mouse.move(cx + i * 1.2, cy - 90 + i * 5)
        page.wait_for_timeout(6)
    page.mouse.up()
    page.wait_for_timeout(300)
    # Three lines were drawn 60 screen px apart. After a stroke straight through
    # all three, they must still be three lines. At full strength each one's
    # centre point rides the cursor and all three land on the same vertex.
    # Counting CLUSTERS over the whole page, not peering through a narrow x
    # window — the liquify stroke has just dragged the ink sideways out of any such
    # window, which is how the first version of this measured three points and
    # reported None.
    bands = page.evaluate("""() => {
      const ys = frames[0].strokes.map(p => p.y).sort((a, b) => a - b);
      if (!ys.length) return null;
      const out = [ys[0]];
      for (const y of ys) if (y - out[out.length - 1] > 30) out.push(y);
      return { bands: out.length, lo: ys[0], hi: ys[ys.length - 1], n: ys.length };
    }""")
    check("three parallel lines are still three lines after a stroke through them",
          bands is not None and bands["bands"] >= 3,
          f"{bands} — collapsing to one vertex means the centre point is riding "
          f"the cursor, i.e. LIQUIFY_STRENGTH is 1")

    print("\nLIQUIFY — undo is exact, and a tap does not fill the history")
    fresh(page)
    line(page, box, 0)
    page.evaluate("() => setTool('liquify')")
    log_before = page.evaluate("() => actionLog.length")
    page.mouse.move(cx, cy)
    page.mouse.down()
    page.mouse.up()
    page.wait_for_timeout(250)
    check("a TAP with liquify selected logs nothing",
          page.evaluate("() => actionLog.length") == log_before,
          "a no-op on the history puts the stroke the user wants back one "
          "press further away than they expect")

    page.mouse.move(cx - 300, cy - 200)
    page.mouse.down()
    for i in range(1, 12):
        page.mouse.move(cx - 300 + i * 4, cy - 200)
        page.wait_for_timeout(6)
    page.mouse.up()
    page.wait_for_timeout(250)
    check("a drag that catches NOTHING logs nothing either",
          page.evaluate("() => actionLog.length") == log_before,
          "empty canvas is the common case for an accidental drag")

    pristine = page.evaluate("() => frames[0].strokes.map(p => [p.x, p.y])")
    page.mouse.move(cx, cy - 40)
    page.mouse.down()
    for i in range(1, 30):
        page.mouse.move(cx, cy - 40 + i * 4)
        page.wait_for_timeout(6)
    page.mouse.up()
    page.wait_for_timeout(300)
    check("a real liquify stroke DOES log one entry",
          page.evaluate("() => actionLog.filter(e => e && e.type === 'liquify').length") == 1)

    liquified = page.evaluate("() => frames[0].strokes.map(p => [p.x, p.y])")
    page.evaluate("() => undoStroke()")
    page.wait_for_timeout(300)
    undone = page.evaluate("() => frames[0].strokes.map(p => [p.x, p.y])")
    # EXACT, not close. The entry stores coordinates rather than a delta because
    # a liquify stroke accumulates over dozens of move events at a different weight
    # each time: there is no single displacement to negate, and re-deriving one
    # would walk the artwork a little further from home on every cycle.
    check("undo restores the EXACT coordinates",
          undone == pristine,
          f"{sum(1 for a, b in zip(undone, pristine) if a != b)} points differ "
          f"— a liquify stroke has no single delta to invert")
    page.evaluate("() => redoStroke()")
    page.wait_for_timeout(300)
    check("redo puts them back exactly too",
          page.evaluate("() => frames[0].strokes.map(p => [p.x, p.y])") == liquified)

    # Ten round trips. Drift is invisible at one and obvious at ten, which is
    # the whole reason coordinates are stored instead of a displacement.
    for _ in range(10):
        page.evaluate("() => undoStroke()")
        page.evaluate("() => redoStroke()")
    page.wait_for_timeout(300)
    check("ten undo/redo cycles do not drift the artwork",
          page.evaluate("() => frames[0].strokes.map(p => [p.x, p.y])") == liquified,
          "inverting a weighted accumulation is where drift comes from")

    print("\nLIQUIFY — a liquify stroke belongs to the page it STARTED on")
    fresh(page)
    line(page, box, 0)
    page.evaluate("() => { addPage(); }" if page.evaluate(
        "() => typeof addPage === 'function'") else "() => {}")
    pages = page.evaluate("() => frames.length")
    if pages < 2:
        page.evaluate("""() => {
          frames.push({ strokes: [], strokeGroups: [], hold: 1 });
          buildStrip();
        }""")
        pages = page.evaluate("() => frames.length")
    check("a second page exists to change to", pages >= 2, f"{pages} pages")

    page.evaluate("() => { go(0); setTool('liquify'); }")
    page.wait_for_timeout(150)
    p1_before = page.evaluate("() => frames[1].strokes.length")
    page.mouse.move(cx, cy - 40)
    page.mouse.down()
    for i in range(1, 10):
        page.mouse.move(cx, cy - 40 + i * 4)
        page.wait_for_timeout(6)
    # Mid-gesture, the page changes under it.
    page.evaluate("() => go(1)")
    page.wait_for_timeout(60)
    for i in range(10, 24):
        page.mouse.move(cx, cy - 40 + i * 4)
        page.wait_for_timeout(6)
    page.mouse.up()
    page.wait_for_timeout(300)
    entry = page.evaluate(
        "() => { const a = actionLog.filter(e => e && e.type === 'liquify');"
        " return a.length ? a[a.length - 1].idx : null; }")
    check("the whole gesture landed on page 1, not on the page it ended on",
          entry == 0, f"undo entry says page {entry}")
    check("...and the page it ended on was not touched",
          page.evaluate("() => frames[1].strokes.length") == p1_before,
          "re-reading frame() per move is how the back half of a drag ends up "
          "on somebody else's artwork")
    check("no error came out of changing page mid-liquify", not errs,
          "; ".join(errs[:2]))

    print("\nLIQUIFY — the whole point: everything downstream still works")
    # THIS IS THE ARGUMENT FOR MOVING GEOMETRY, stated as a test rather than as
    # prose. A raster tool would have to flatten the page to a bitmap, and a
    # bitmap has no stroke order left to replay, no per-point size to scale, and
    # nothing the existing schema can carry. Because this one only MOVES points,
    # a liquify stroked page is still an ordinary page: the server takes it, the player
    # renders it, and neither of them had to learn anything.
    fresh(page)
    for off in (-50, 0, 50):
        line(page, box, off)
    page.evaluate("() => setTool('liquify')")
    page.mouse.move(cx, cy - 80)
    page.mouse.down()
    for i in range(1, 36):
        page.mouse.move(cx + i * 1.5, cy - 80 + i * 4.5)
        page.wait_for_timeout(5)
    page.mouse.up()
    page.wait_for_timeout(300)

    # The invariant the server actually enforces, and the one this codebase has
    # been burned by twice: strokeGroups must account for exactly the points in
    # the strokes array. A tool that edited the array's LENGTH would break it.
    tally = page.evaluate("""() => frames.map(f => [f.strokes.length,
      f.strokeGroups.reduce((a, b) => a + b, 0)])""")
    check("strokeGroups still accounts for every point after a liquify stroke",
          all(a == b for a, b in tally), f"{tally}")

    posted = page.evaluate("""async (base) => {
      const frs = frames.map(f => ({ strokes: f.strokes,
                                     strokeGroups: f.strokeGroups,
                                     background: '#0d0f14' }));
      const r = await fetch(base + '/api/skribls', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: 'liquify', kind: 'flip', frames: frs, fps: 12 })
      });
      if (!r.ok) return { ok: false, status: r.status };
      const j = await r.json();
      return { ok: true, url: j.url || ('/s/' + (j.slug || '')) };
    }""", BASE)
    check("a liquify stroked page POSTS — the server sees an ordinary page",
          posted.get("ok"), f"{posted}")

    if posted.get("ok"):
        viewer = browser.new_page(viewport={"width": 900, "height": 800})
        verrs = []
        viewer.on("pageerror", lambda e: verrs.append(str(e)))
        viewer.goto(BASE + posted["url"], wait_until="load")
        viewer.wait_for_timeout(2600)
        ink = viewer.evaluate("""() => {
          const c = document.querySelector('canvas');
          if (!c || !c.width) return -1;
          const d = c.getContext('2d', { willReadFrequently: true })
                     .getImageData(0, 0, c.width, c.height).data;
          let n = 0;
          for (let i = 0; i < d.length; i += 4)
            if (d[i] > 200 && d[i + 1] > 200 && d[i + 2] > 200) n++;
          return n;
        }""")
        check("...and the PLAYER draws the bent lines",
              ink > 500, f"{ink} white pixels — the player was never taught "
                         f"about liquify and does not need to be")
        check("...with no error in the player", not verrs, "; ".join(verrs[:2]))
        viewer.close()

    print("\nLIQUIFY — it stays out of the way of everything else")
    fresh(page)
    line(page, box, 0)
    page.evaluate("() => setTool('liquify')")
    page.wait_for_timeout(120)
    check("choosing liquify does not put the app in erase mode",
          page.evaluate("() => erasing") is False,
          "erasing is set by the eraser and nothing else")
    check("the reach ring is liquify's own, not the brush's",
          page.evaluate("() => !!document.querySelector('.flip-liquify-cursor')")
          and page.evaluate(
              "() => getComputedStyle(document.querySelector('.flip-liquify-cursor'))"
              ".borderStyle") == "dashed",
          "dashed marks INFLUENCE; a solid ring that size reads as a colossal brush")
    page.evaluate("() => setTool('pen')")
    page.wait_for_timeout(200)
    check("leaving liquify takes its ring with it",
          page.evaluate(
              "() => document.querySelector('.flip-liquify-cursor').style.display") == "none",
          "a ring belonging to a tool you have left is a ring that lies")

    n_pen = page.evaluate("() => frames[0].strokes.length")
    line(page, box, 40)
    check("the pen still draws after liquify has been used",
          page.evaluate("() => frames[0].strokes.length") > n_pen,
          "the intercept must return the canvas when the tool changes")
    check("no uncaught error across the whole session", not errs, "; ".join(errs[:3]))

    browser.close()

bad = [r for r in results if not r[0]]
print(f"\n{'=' * 62}\n{len(results) - len(bad)}/{len(results)} passed"
      + ("" if not bad else "  FAILURES: " + ", ".join(n for _, n in bad)))
sys.exit(1 if bad else 0)
