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


def enter_move(pg):
    """Enter Move-artwork mode through whatever currently opens it.

    v226 moved Artwork out of the page bar and into the tool shelf, and this
    file clicked `#pbArt` in nine places. What the suite actually tests is the
    MODE — capture, offset, scope, undo — none of which changed. Routing every
    entry through one helper means the next time the control moves, this file
    changes on one line instead of nine.
    """
    pg.evaluate("() => setTool('artmove')")
    assert pg.evaluate("() => moveMode") is True, "move mode did not start"


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
    check("Artwork lives in the TOOL SHELF, not the page bar (v226)",
          pg.evaluate("() => !!(window.SkriblFlipTools "
                      "&& window.SkriblFlipTools.has('artmove'))")
          and not pg.evaluate("() => !!document.querySelector('#pagebar #pbArt')"),
          "it moves the DRAWING, not the page — filing it beside Copy, Hold "
          "and Delete was the mistake v226 corrected")

    enter_move(pg)
    pg.wait_for_timeout(350)
    # Measured, not read off the property. `pagebar.hidden` was True in every
    # build of this feature while the bar stayed on screen 55px tall: [hidden]
    # is a UA rule and `.pagebar{display:flex}` is an author rule, so the author
    # rule won. This assertion passed for four versions against a visibly broken
    # surface because it asked the DOM what it had been told, not what it drew.
    check("the page bar is replaced, not added to",
          pg.evaluate("() => { const pb = document.getElementById('pagebar');"
                      " return pb.offsetParent === null"
                      " && pb.getBoundingClientRect().height === 0"
                      " && getComputedStyle(pb).display === 'none'; }") is True
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

    enter_move(pg)
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
    enter_move(pg)
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
    enter_move(pg)
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

    # ---- the transform bar's own geometry ---------------------------------
    # Everything below measures what is drawn. The scope pill's height used to
    # come from `font: inherit` -> `line-height: inherit`, so it followed the
    # VIEWER'S installed font: the same stylesheet rendered it at 20px in
    # headless Chromium and 23px on a Mac, while .pb — which states a height —
    # matched exactly. A control that size cannot be asserted at all.
    print("\nMOVE — the transform bar's geometry")
    pg.set_viewport_size({"width": 900, "height": 1000})
    pg.wait_for_timeout(300)
    if not pg.is_visible("#movebar"):
        enter_move(pg)
        pg.wait_for_timeout(300)

    geom = pg.evaluate("""() => {
        const h = s => { const e = document.querySelector(s);
                         return e ? +e.getBoundingClientRect().height.toFixed(1) : null; };
        return { seg: h('#mbScope'), pill: h('#mbScope .seg-slider'),
                 sel: h('#mbScope button.on'), offset: h('#mbOffset'),
                 reset: h('#mbReset'), done: h('#mbDone') }; }""")

    check("the scope pill and the offset readout are the same height",
          geom["seg"] == geom["offset"],
          f"they report state as a pair; got {geom['seg']} and {geom['offset']}")
    check("the pill states a height rather than inheriting one",
          geom["seg"] == 30,
          f"expected 30, got {geom['seg']} — an inherited height varies by font")
    # The highlight is what the eye reads, and it is NOT the container: it is
    # inset 3px top and bottom inside a 1px border, so it always lands 8px
    # under. Asserting only the container missed a 12px highlight sitting in a
    # row of 38px buttons.
    check("the selection highlight fills the selected button",
          geom["pill"] is not None and geom["sel"] is not None
          and abs(geom["pill"] - geom["sel"]) <= 1,
          f"highlight {geom['pill']} against button {geom['sel']}")
    check("the highlight is over half the height of the buttons beside it",
          geom["pill"] is not None and geom["pill"] >= geom["reset"] / 2,
          f"highlight {geom['pill']} against .pb {geom['reset']}")
    check("Reset and Done are the same size as each other",
          geom["reset"] == geom["done"],
          f"{geom['reset']} and {geom['done']}")

    # ---- the bar fits, at every width a phone actually reports -------------
    # .pagebar is `overflow-x: auto`, so a bar that is too wide does not clip —
    # it becomes scrollable and Done leaves the screen, which is easy to miss.
    # scrollWidth against clientWidth, never a sum of child widths: the flex row
    # shrinks .mb-offset before anything overflows, so arithmetic reports room
    # that is not there.
    print("\nMOVE — the transform bar fits every phone width")
    # The page label is DYNAMIC, so measuring whatever page happens to be
    # selected proves nothing: "Page 3" is far narrower than "Pages 108-162" on
    # a long animation. Force the widest label the feature can produce. The bar
    # is overflow-x:auto, so a bar that is too wide does not clip — it scrolls
    # and takes Done off screen, which is easy to miss.
    pg.evaluate("() => { const w = document.getElementById('mbWho');"
                " if (w) w.textContent = 'Pages 108\u2013162'; }")
    for width in (320, 360, 375, 390, 393, 414, 430, 568, 844):
        pg.set_viewport_size({"width": width, "height": 900})
        pg.wait_for_timeout(250)
        pg.evaluate("() => { const w = document.getElementById('mbWho');"
                    " if (w) w.textContent = 'Pages 108\u2013162'; }")
        fit = pg.evaluate("""() => { const bar = document.getElementById('movebar');
            const d = document.getElementById('mbDone').getBoundingClientRect();
            return { over: bar.scrollWidth > bar.clientWidth,
                     off: d.right > bar.getBoundingClientRect().right + 1,
                     sw: bar.scrollWidth, cw: bar.clientWidth }; }""")
        check(f"the bar does not scroll at {width}px",
              not fit["over"], f"scrollWidth {fit['sw']} against clientWidth {fit['cw']}")
        check(f"Done is on screen at {width}px", not fit["off"])
    pg.set_viewport_size({"width": 900, "height": 1000})

    # ---- typing an exact offset -------------------------------------------
    # Dragging answers "about there"; typing answers "exactly 40 across". The
    # two write the same moveDx/moveDy, so the assertions below check that a
    # typed offset is indistinguishable from a dragged one: same readout, same
    # Reset, same single undo entry.
    print("\nMOVE — typing an exact offset")
    pg.set_viewport_size({"width": 900, "height": 1000})
    pg.wait_for_timeout(250)
    if not pg.is_visible("#movebar"):
        enter_move(pg)
        pg.wait_for_timeout(300)
    pg.click("#mbReset")
    pg.wait_for_timeout(200)
    base = pts(pg, 0)

    check("the offset readout is operable, not just a label",
          pg.evaluate("() => document.getElementById('mbOffset').tagName") == "BUTTON"
          and bool(pg.get_attribute("#mbOffset", "aria-label")),
          "a span cannot be focused or announced as something you can act on")

    pg.click("#mbOffset")
    pg.wait_for_timeout(250)
    check("activating it opens an entry box, focused and pre-selected",
          pg.is_visible("#mbOffsetInput")
          and pg.evaluate("() => document.activeElement.id") == "mbOffsetInput"
          and pg.input_value("#mbOffsetInput") == "0, 0",
          "it must open ready to type over, not ready to append to")

    # The field takes BOTH coordinates in one box, so the keyboard it summons has
    # to be able to produce a separator AND a minus. inputmode="numeric" offers
    # digits only on a phone: no comma, and on most keyboards no minus, which
    # makes a negative offset — half the useful moves — impossible to type at
    # all. `decimal` is not the fix either; it adds a decimal POINT. Asserted
    # rather than reviewed because nothing else in the tree reads this attribute,
    # and it fails on unmodified v179.
    _im = (pg.get_attribute("#mbOffsetInput", "inputmode") or "").lower()
    check("the offset field asks for a keyboard that can type a comma and a minus",
          _im == "text",
          f'inputmode={_im!r} — "numeric" and "decimal" both hide the separator')

    # And the parser must accept whatever that fuller keyboard lets someone
    # produce, or the fix just moves the failure one step later.
    _accepts = pg.evaluate("""() => {
        const r = {};
        for (const s of ['40, -12', '40,-12', '40 -12', '-40, -12', '1.5, -2.5'])
          r[s] = !!parseOffsetEntry(s);
        r['banana'] = !!parseOffsetEntry('banana');
        return r; }""")
    check("the parser takes every form that keyboard allows, and still rejects junk",
          all(_accepts[k] for k in _accepts if k != "banana") and not _accepts["banana"],
          str(_accepts))

    pg.fill("#mbOffsetInput", "40, -12")
    pg.keyboard.press("Enter")
    pg.wait_for_timeout(350)
    moved = [(round(a[0] - c[0], 6), round(a[1] - c[1], 6)) for a, c in zip(pts(pg, 0), base)]
    check("a typed offset moves every point by exactly that amount",
          moved and len(set(moved)) == 1 and moved[0] == (40.0, -12.0),
          f"got {sorted(set(moved))[:3]}")
    check("and the readout agrees with what was typed",
          pg.text_content("#mbOffset").strip() == "40, -12")
    check("the entry box closes after committing", not pg.is_visible("#mbOffsetInput"))

    # Escape inside the box is a different scope from Escape on the canvas.
    # Without stopPropagation the document-level handler cancels the whole move,
    # so abandoning a typo would silently throw the drag away too.
    pg.click("#mbOffset")
    pg.wait_for_timeout(200)
    pg.fill("#mbOffsetInput", "999, 999")
    pg.keyboard.press("Escape")
    pg.wait_for_timeout(300)
    check("Escape in the entry box abandons the typo, not the move",
          pg.is_visible("#movebar")
          and pg.text_content("#mbOffset").strip() == "40, -12",
          "Escape must not fall through to the move-cancel handler")

    pg.click("#mbOffset")
    pg.wait_for_timeout(200)
    pg.fill("#mbOffsetInput", "banana")
    pg.keyboard.press("Enter")
    pg.wait_for_timeout(300)
    check("an unparseable entry is refused rather than half-obeyed",
          pg.text_content("#mbOffset").strip() == "40, -12",
          "salvaging a number out of nonsense moves the drawing somewhere unintended")

    pg.click("#mbReset")
    pg.wait_for_timeout(250)
    check("Reset clears a typed offset like any other",
          same(pts(pg, 0), base) and pg.text_content("#mbOffset").strip() == "0, 0")

    pg.click("#mbOffset")
    pg.wait_for_timeout(200)
    pg.fill("#mbOffsetInput", "25, 25")
    pg.keyboard.press("Enter")
    pg.wait_for_timeout(250)
    pg.click("#mbDone")
    pg.wait_for_timeout(300)
    pg.click("#undo")
    pg.wait_for_timeout(400)
    check("undo reverses a typed move exactly, as it does a dragged one",
          same(pts(pg, 0), base),
          "typing must produce the same single inverse-offset undo entry")

    check("leaving move mode never strands an open entry box",
          pg.evaluate("""() => { const i = document.getElementById('mbOffsetInput');
              setTool('artmove');
              document.getElementById('mbOffset').click();
              document.getElementById('mbDone').click();
              return i.hidden === true; }"""),
          "its blur handler would otherwise commit into a move that had ended")

    # ---- composed state transitions ---------------------------------------
    # Every dimension of this feature was tested in isolation and passed. The
    # break was in the COMPOSITION: move first, THEN change the target set. An
    # external abuse pass found it by trying two valid actions in sequence.
    print("\nMOVE — changing scope while an offset is live")
    pg.set_viewport_size({"width": 900, "height": 1000})
    pg.wait_for_timeout(250)
    if pg.is_visible("#movebar"):
        pg.keyboard.press("Escape")
        pg.wait_for_timeout(250)
    while pg.evaluate("() => frames.length") < 3:
        pg.click("#addblank")
        pg.wait_for_timeout(250)
        draw(pg, box)
    pg.evaluate("() => { idx = 0; buildStrip(); render(); }")
    pg.wait_for_timeout(250)
    o0, o1, o2 = pts(pg, 0), pts(pg, 1), pts(pg, 2)

    def delta(i, orig):
        return sorted({(round(a[0] - c[0], 6), round(a[1] - c[1], 6))
                       for a, c in zip(pts(pg, i), orig)})

    enter_move(pg)
    pg.wait_for_timeout(300)
    pg.click("#mbOffset")
    pg.wait_for_timeout(200)
    pg.fill("#mbOffsetInput", "40, 0")
    pg.keyboard.press("Enter")
    pg.wait_for_timeout(300)
    check("one page, offset applied once", delta(0, o0) == [(40.0, 0.0)], f"{delta(0, o0)}")

    pg.click("#mbScope button[data-scope='after']")
    pg.wait_for_timeout(350)
    # This is the regression. The origin used to be re-captured from points the
    # preview had ALREADY translated, so the current page took the offset twice
    # and landed on 80 while pages newly in scope took it once.
    check("widening scope does not apply the offset to the current page twice",
          delta(0, o0) == [(40.0, 0.0)],
          f"page 1 is at {delta(0, o0)} — 80 means the origin was re-read from the preview")
    check("and pages newly in scope get the same offset, not a different one",
          delta(1, o1) == [(40.0, 0.0)] and delta(2, o2) == [(40.0, 0.0)],
          f"page 2 {delta(1, o1)}, page 3 {delta(2, o2)}")

    pg.click("#mbScope button[data-scope='one']")
    pg.wait_for_timeout(350)
    check("narrowing scope restores the pages that left the set",
          delta(1, o1) == [(0.0, 0.0)] and delta(2, o2) == [(0.0, 0.0)],
          "pages leaving scope must go back to their originals, not stay put")
    check("and leaves the remaining page on exactly the chosen offset",
          delta(0, o0) == [(40.0, 0.0)], f"{delta(0, o0)}")

    for _ in range(3):
        pg.click("#mbScope button[data-scope='after']")
        pg.wait_for_timeout(200)
        pg.click("#mbScope button[data-scope='one']")
        pg.wait_for_timeout(200)
    check("repeated scope switching does not accumulate",
          delta(0, o0) == [(40.0, 0.0)] and delta(1, o1) == [(0.0, 0.0)],
          f"page 1 {delta(0, o0)}, page 2 {delta(1, o1)}")

    pg.click("#mbReset")
    pg.wait_for_timeout(250)
    check("Reset after a scope switch returns every page to its original",
          delta(0, o0) == [(0.0, 0.0)] and delta(1, o1) == [(0.0, 0.0)]
          and delta(2, o2) == [(0.0, 0.0)])

    pg.click("#mbScope button[data-scope='after']")
    pg.wait_for_timeout(200)
    pg.mouse.move(box["x"] + 150, box["y"] + 150)
    pg.mouse.down()
    pg.mouse.move(box["x"] + 190, box["y"] + 150, steps=6)
    pg.mouse.up()
    pg.wait_for_timeout(250)
    pg.click("#mbScope button[data-scope='one']")
    pg.wait_for_timeout(250)
    pg.keyboard.press("Escape")
    pg.wait_for_timeout(300)
    check("Escape after a scope switch cancels back to the originals",
          delta(0, o0) == [(0.0, 0.0)] and delta(1, o1) == [(0.0, 0.0)]
          and delta(2, o2) == [(0.0, 0.0)],
          "a cancelled move must leave nothing behind on any page")

    # ---- a transform session owns a stable set of pages --------------------
    # moveOrigin is keyed by array index, so any page operation mid-move makes
    # index i stop identifying the captured page. A reorder could apply one
    # page's coordinates to another page's strokes.
    print("\nMOVE — page structure is frozen while a move is live")
    enter_move(pg)
    pg.wait_for_timeout(300)
    pg.click("#mbOffset")
    pg.wait_for_timeout(200)
    pg.fill("#mbOffsetInput", "30, 0")
    pg.keyboard.press("Enter")
    pg.wait_for_timeout(300)
    before_n, before_idx = pg.evaluate("() => [frames.length, idx]")

    pg.evaluate("() => go(1)")
    pg.wait_for_timeout(250)
    check("selecting another page is refused during a move",
          pg.evaluate("() => idx") == before_idx,
          "commitMove recomputes its targets from idx, so the undo record "
          "would name a page that was never previewed")
    pg.evaluate("() => addFrame(false)")
    pg.wait_for_timeout(250)
    pg.evaluate("() => delFrame(0)")
    pg.wait_for_timeout(250)
    pg.evaluate("() => movePageTo(0, 1)")
    pg.wait_for_timeout(250)
    check("adding, deleting and reordering pages are refused during a move",
          pg.evaluate("() => frames.length") == before_n
          and pg.evaluate("() => idx") == before_idx,
          "index identity must hold for the life of the transaction")
    check("and the preview is still exactly the offset that was typed",
          delta(0, o0) == [(30.0, 0.0)], f"{delta(0, o0)}")

    pg.click("#mbDone")
    pg.wait_for_timeout(300)
    check("page operations work again once the move is committed",
          pg.evaluate("() => { go(1); return idx; }") == 1)
    pg.evaluate("() => go(0)")
    pg.wait_for_timeout(200)

    # ---- a move that undoes must redo -------------------------------------
    print("\nMOVE — undo and redo are symmetric")
    pg.click("#undo")
    pg.wait_for_timeout(350)
    check("undo reverses the committed move", delta(0, o0) == [(0.0, 0.0)])
    pg.click("#redo")
    pg.wait_for_timeout(350)
    check("redo reapplies it, rather than doing nothing or replaying a stroke",
          delta(0, o0) == [(30.0, 0.0)],
          f"{delta(0, o0)} — a move on the undo history owes a redo")
    pg.click("#undo")
    pg.wait_for_timeout(300)
    check("and the pair can be repeated", delta(0, o0) == [(0.0, 0.0)])

    # ---- scope is legible, and refusals are spoken -------------------------
    print("\nMOVE — the interface says what is happening")
    pg.set_viewport_size({"width": 900, "height": 1000})
    pg.wait_for_timeout(250)
    pg.evaluate("() => { idx = 0; buildStrip(); render(); }")
    pg.wait_for_timeout(200)
    if not pg.is_visible("#movebar"):
        enter_move(pg)
        pg.wait_for_timeout(300)
    n_pages = pg.evaluate("() => frames.length")

    check("the bar names the page being moved",
          pg.text_content("#mbWho").strip() == "Page 1",
          "the move bar REPLACES the page bar, so entering Move is the moment "
          "page identity would otherwise be lost")
    check("and only that page is marked in the filmstrip",
          pg.evaluate("() => document.querySelectorAll('.frame.in-scope').length") == 1)

    pg.click("#mbScope button[data-scope='after']")
    pg.wait_for_timeout(300)
    check("widening the scope renames the range",
          pg.text_content("#mbWho").strip() == f"Pages 1\u2013{n_pages}",
          f"got {pg.text_content('#mbWho').strip()!r}")
    check("and marks exactly the affected pages in the filmstrip",
          pg.evaluate("() => document.querySelectorAll('.frame.in-scope').length") == n_pages,
          "the strip shows scope better than a text selector, and costs no bar width")
    check("the scope control reads as language, not shorthand",
          "&" not in pg.text_content("#mbScope"),
          f"got {pg.text_content('#mbScope').strip()!r}")

    # A control frozen for correctness still invites the tap. Refusing in
    # silence looks like a broken app; saying why is the difference.
    before = pg.evaluate("() => idx")
    pg.click(".frame:nth-child(2)")
    pg.wait_for_timeout(300)
    check("a frozen page control explains itself instead of looking dead",
          pg.evaluate("() => idx") == before
          and "move" in pg.text_content("#flipChip").lower(),
          f"chip said {pg.text_content('#flipChip')!r}")

    # The DRAG path, not the tap: a real drag sets _pdragSuppressClick, so the
    # click handler that explains the refusal never runs. This was the one page
    # operation that failed in total silence during a move, and it is the one
    # most likely to be tried — found on a real device, not by the suite.
    pg.evaluate("() => { const c = document.getElementById('flipChip');"
                " if (c) c.textContent = ''; }")
    thumb = pg.query_selector(".frame:nth-child(2)") or pg.query_selector(".frame")
    box_t = thumb.bounding_box()
    pg.mouse.move(box_t["x"] + box_t["width"] / 2, box_t["y"] + box_t["height"] / 2)
    pg.mouse.down()
    pg.mouse.move(box_t["x"] + box_t["width"] * 1.6, box_t["y"] + box_t["height"] / 2, steps=8)
    pg.mouse.up()
    pg.wait_for_timeout(350)
    check("dragging a thumbnail during a move explains the refusal",
          "move" in (pg.text_content("#flipChip") or "").lower(),
          f"chip said {pg.text_content('#flipChip')!r} — a drag never reaches "
          "the click handler, so it needs its own message")

    check("the duplicate action is named for what it does",
          "Duplicate" in pg.text_content("#addcopy"),
          "draw, duplicate, nudge, duplicate is the animation loop; the button "
          "did exactly that under the label '+ Page'")

    pg.click("#mbOffset")
    pg.wait_for_timeout(200)
    pg.fill("#mbOffsetInput", "15, 0")
    pg.keyboard.press("Enter")
    pg.wait_for_timeout(200)
    pg.click("#mbDone")
    pg.wait_for_timeout(250)
    pg.click("#undo")
    pg.wait_for_timeout(350)
    check("undoing a move says so, because it is not a stroke",
          "undone" in pg.text_content("#flipChip").lower()
          and "move" in pg.text_content("#flipChip").lower(),
          f"chip said {pg.text_content('#flipChip')!r}")
    pg.click("#redo")
    pg.wait_for_timeout(350)
    check("and redoing it says so too",
          "redone" in pg.text_content("#flipChip").lower(),
          f"chip said {pg.text_content('#flipChip')!r}")
    pg.click("#undo")
    pg.wait_for_timeout(250)

    check("no JS errors across the composed transitions", not errs, "; ".join(errs[:2]))
    b.close()

summarise_and_exit()
