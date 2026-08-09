"""Move artwork — dragging a page's drawing to new coordinates.

WHAT IT IS. A page operation, not a drawing tool: it lives in the page bar with
Copy, Hold and Delete, and the page bar becomes the transform bar while a move
is live. That placement is deliberate — the tool row is full on a phone, and a
second bar would push the filmstrip off screen exactly when it is needed to
judge the move.

WHY UNDO STORES AN OFFSET, NOT A SNAPSHOT. A translation is exactly reversible,
so undoing is applying -dx,-dy to the same points. With '& after' selected on a
62-page animation a snapshot would copy every affected page; two numbers cost
nothing and cannot drift. This suite asserts the round trip returns the ORIGINAL
coordinates, not merely something close.

WHY AN ACTION LOG. Flip's undo pops stroke groups. Without recording the order
of actions, undo after "draw, move" would pop the stroke and silently leave the
move — undoing something the user did not do last.
"""
import os
import sys

BASE = os.environ.get("SKRIBL_BASE", "http://127.0.0.1:5001")
results = []


def check(name, ok, detail=""):
    results.append((bool(ok), name))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  — {detail}" if detail and not ok else ""))


def summarise_and_exit():
    bad = [r for r in results if not r[0]]
    print(f"\n{'=' * 62}\n{len(results) - len(bad)}/{len(results)} passed"
          + ("" if not bad else "  FAILURES: " + ", ".join(r[1] for r in bad)))
    sys.exit(1 if bad else 0)


try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("  [SKIP] playwright unavailable — this suite needs a browser")
    summarise_and_exit()


def draw(pg, box, x0=70, y0=70):
    pg.mouse.move(box["x"] + x0, box["y"] + y0)
    pg.mouse.down()
    pg.mouse.move(box["x"] + x0 + 160, box["y"] + y0 + 50, steps=8)
    pg.mouse.move(box["x"] + x0 + 70, box["y"] + y0 + 120, steps=8)
    pg.mouse.up()
    pg.wait_for_timeout(200)


def same(a, b, tol=1e-6):
    """Equal to within a millionth of a canvas unit.

    NOT bit-exact, and cannot be: adding dx then subtracting it is not
    guaranteed to reproduce the original float. 163.66762177650432 came back as
    163.6676217765043 — a difference of 2e-14 canvas units, which is roughly a
    ten-trillionth of a pixel. Demanding exact equality here would be asserting
    a property of IEEE 754 rather than a property of the feature."""
    if len(a) != len(b):
        return False
    return all(abs(p[0] - q[0]) < tol and abs(p[1] - q[1]) < tol
               for p, q in zip(a, b))


def pts(pg, i=None):
    """RAW coordinates, not rounded.

    Rounding before differencing produces off-by-one deltas from a perfectly
    uniform translation — the first version of this suite reported the drawing
    as 'distorted' when every point had in fact moved by exactly the same
    fractional offset."""
    expr = "() => frames[%s].strokes.map(p => [p.x, p.y])" % (
        "idx" if i is None else str(i))
    return pg.evaluate(expr)


with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 393, "height": 852})
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(f"{BASE}/flip", wait_until="load")
    pg.wait_for_timeout(1350)
    box = pg.locator("#pad").bounding_box()

    print("MOVE — entering and leaving the mode")
    draw(pg, box)
    check("the Artwork button is in the page bar",
          pg.evaluate("() => !!document.querySelector('#pagebar #pbArt')"),
          "it is a page operation and belongs with Copy, Hold and Delete")

    pg.click("#pbArt")
    pg.wait_for_timeout(350)
    check("the page bar is replaced, not added to",
          pg.evaluate("() => document.getElementById('pagebar').hidden") is True
          and pg.is_visible("#movebar"),
          "two bars would push the filmstrip off a phone screen")
    check("the canvas advertises the drag", "grab" in pg.evaluate(
        "() => getComputedStyle(document.getElementById('pad')).cursor"))

    print("\nMOVE — dragging moves the drawing and draws nothing")
    before = pts(pg)
    groups = pg.evaluate("() => frames[idx].strokeGroups.length")
    pg.mouse.move(box["x"] + 180, box["y"] + 140)
    pg.mouse.down()
    pg.mouse.move(box["x"] + 240, box["y"] + 180, steps=10)
    pg.mouse.up()
    pg.wait_for_timeout(250)
    after = pts(pg)
    check("the drawing moved", not same(after, before))
    check("and no stroke was added",
          pg.evaluate("() => frames[idx].strokeGroups.length") == groups,
          "the drag laid down a line instead of moving the page")
    deltas = {(round(a[0] - bp[0], 6), round(a[1] - bp[1], 6))
              for a, bp in zip(after, before)}
    check("every point moved by the SAME offset", len(deltas) == 1,
          f"{len(deltas)} distinct offsets — the drawing was distorted, "
          "not translated")
    check("the offset readout is not zero", pg.inner_text("#mbOffset") != "0, 0",
          pg.inner_text("#mbOffset"))

    print("\nMOVE — Reset, Escape and Done")
    pg.click("#mbReset")
    pg.wait_for_timeout(250)
    check("Reset returns the drawing exactly", same(pts(pg), before),
          "Reset is 'offset zero', so it must land on the original")

    pg.mouse.move(box["x"] + 180, box["y"] + 140)
    pg.mouse.down()
    pg.mouse.move(box["x"] + 220, box["y"] + 165, steps=8)
    pg.mouse.up()
    pg.wait_for_timeout(200)
    pg.keyboard.press("Escape")
    pg.wait_for_timeout(300)
    check("Escape cancels the move", same(pts(pg), before),
          "Escape must abandon, not commit — it means abandon everywhere else here")
    check("and leaves the mode", pg.evaluate("() => moveMode") is False)

    pg.click("#pbArt")
    pg.wait_for_timeout(300)
    pg.mouse.move(box["x"] + 180, box["y"] + 140)
    pg.mouse.down()
    pg.mouse.move(box["x"] + 245, box["y"] + 185, steps=10)
    pg.mouse.up()
    pg.wait_for_timeout(200)
    moved = pts(pg)
    pg.click("#mbDone")
    pg.wait_for_timeout(300)
    check("Done commits the move", same(pts(pg), moved))
    check("and restores the page bar",
          pg.evaluate("() => document.getElementById('pagebar').hidden") is False)

    print("\nMOVE — undo is an exact inverse, and respects order")
    pg.click("#undo")
    pg.wait_for_timeout(300)
    check("undo returns the ORIGINAL coordinates", same(pts(pg), before),
          "an offset undo must land exactly, not approximately")

    # draw, then move, then undo -> the MOVE goes, the stroke stays.
    draw(pg, box, 90, 100)
    after_draw = pts(pg)
    pg.click("#pbArt")
    pg.wait_for_timeout(300)
    pg.mouse.move(box["x"] + 180, box["y"] + 140)
    pg.mouse.down()
    pg.mouse.move(box["x"] + 230, box["y"] + 170, steps=8)
    pg.mouse.up()
    pg.wait_for_timeout(200)
    pg.click("#mbDone")
    pg.wait_for_timeout(250)
    pg.click("#undo")
    pg.wait_for_timeout(300)
    check("undo after draw-then-move undoes the MOVE, not the stroke",
          same(pts(pg), after_draw),
          "without an action log, undo pops the stroke and leaves the move")

    print("\nMOVE — scope")
    pg.evaluate("() => { addFrame(true); addFrame(true); go(0); }")
    pg.wait_for_timeout(350)
    p0, p1 = pts(pg, 0), pts(pg, 1)
    pg.click("#pbArt")
    pg.wait_for_timeout(300)
    pg.click("#mbScope button[data-scope='after']")
    pg.wait_for_timeout(250)
    pg.mouse.move(box["x"] + 180, box["y"] + 140)
    pg.mouse.down()
    pg.mouse.move(box["x"] + 225, box["y"] + 170, steps=8)
    pg.mouse.up()
    pg.wait_for_timeout(250)
    check("'& after' moves later pages too", not same(pts(pg, 1), p1),
          "the scope toggle did not extend the move")
    check("and moves them by the same offset",
          [(round(a[0] - c[0], 6), round(a[1] - c[1], 6))
           for a, c in zip(pts(pg, 0), p0)][:1]
          == [(round(a[0] - c[0], 6), round(a[1] - c[1], 6))
              for a, c in zip(pts(pg, 1), p1)][:1],
          "pages drifted apart instead of moving together")
    pg.click("#mbDone")
    pg.wait_for_timeout(250)
    pg.click("#undo")
    pg.wait_for_timeout(350)
    check("undo reverses a multi-page move exactly",
          same(pts(pg, 0), p0) and same(pts(pg, 1), p1))

    check("no JS errors across the whole flow", not errs, "; ".join(errs[:2]))
    b.close()

summarise_and_exit()
