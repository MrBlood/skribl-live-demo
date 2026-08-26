"""Select on Flip: marquee a subset of one page, then drag it.

WHY THIS IS SAFE ON FLIP AND WAS NOT ON PAD, which is the whole reason the tool
exists here and nowhere else. v219 pulled Select from Pad because Pad records a
timed performance: moving points that were already recorded made replay draw a
stroke at its NEW position at its OLD timestamp. Flip has no timeline within a
page — playback reveals strokes in index order — so moving a point changes only
where it is, never when. Flip's own Move mode has translated whole pages this
way since v213.

Two properties carry the design and are pinned hardest:

  * WHOLE STROKES, NEVER FRAGMENTS. The marquee selects by GROUP: a box that
    clips a stroke in the middle takes all of it or none of it. Moving half a
    stroke and leaving the rest is not what drawing a box round some artwork
    means, and `strokeGroups` would still account for points that had walked
    away from their run.

  * UNDO IS AN OPERATION, NOT A SNAPSHOT. Pad had to clone the selected point
    objects BEFORE snapshotting, or `strokes.slice()` aliased them and undo
    silently restored the moved position — its own comment calls this out at
    length. Flip's actionLog stores what was done, so undo is the same
    translation with the sign flipped and there is nothing to alias. Pinned by
    moving, undoing and redoing and comparing every point against its original.

PAD MUST NOT GET THE TOOL. v219's reasoning still holds there, so the last
section asserts Pad's registry does not list it — otherwise a future "make the
surfaces match" would quietly reintroduce the bug v219 removed.
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


SNAP = "() => frames[idx].strokes.map(p => [Math.round(p.x), Math.round(p.y)])"


def stroke(page, pts):
    box = page.locator("#pad").bounding_box()
    page.mouse.move(box["x"] + pts[0][0], box["y"] + pts[0][1])
    page.mouse.down()
    for x, y in pts[1:]:
        page.mouse.move(box["x"] + x, box["y"] + y, steps=4)
    page.mouse.up()
    page.wait_for_timeout(150)


def drag(page, a, b, steps=10):
    box = page.locator("#pad").bounding_box()
    page.mouse.move(box["x"] + a[0], box["y"] + a[1])
    page.mouse.down()
    page.mouse.move(box["x"] + b[0], box["y"] + b[1], steps=steps)
    page.mouse.up()
    page.wait_for_timeout(250)


def fresh(page):
    """Flip autosaves and restores on load, so a section that just drew leaves
    its strokes waiting for the next one — the marquee in the last section was
    catching a restored square as well as the new one, and reported two
    selections where the test meant one. Clear the draft and reload."""
    page.goto(BASE + "/flip", wait_until="load")
    page.wait_for_timeout(200)
    page.evaluate("() => { for (const k of Object.keys(localStorage))"
                  " if (k.indexOf('skribl') === 0) localStorage.removeItem(k); }")
    page.reload(wait_until="load")
    page.wait_for_timeout(450)


def two_shapes(page):
    """A square top-left and a triangle to its right, far enough apart that a
    marquee round one cannot touch the other."""
    stroke(page, [(110, 120), (200, 120), (200, 210), (110, 210), (110, 120)])
    stroke(page, [(380, 260), (470, 260), (425, 180), (380, 260)])


with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 900, "height": 800})
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))

    print("SELECT — the tool is reachable and loads its geometry")
    fresh(page)
    check("lib/selection.js is loaded on Flip",
          page.evaluate("() => !!window.SkriblSelect"),
          "the geometry lib shipped on Pad only until v227")
    check("select is in Flip's tool registry",
          page.evaluate("() => window.SkriblFlipTools.list()")
          == ["pen", "eraser", "shape", "select"],
          str(page.evaluate("() => window.SkriblFlipTools.list()")))
    check("a fourth tool pushed the shelf into overflow",
          page.evaluate("() => window.SkriblFlipTools.overflowing()"),
          "the tray exists precisely so this costs the row nothing")
    page.click("#toolMoreBtn")
    page.wait_for_timeout(250)
    check("it has a cell in the tray",
          page.locator(".tool-tray-btn[data-tool='select']").count() == 1)
    page.click(".tool-tray-btn[data-tool='select']")
    page.wait_for_timeout(250)
    check("picking it makes it the active tool",
          page.evaluate("() => flipTool") == "select",
          str(page.evaluate("() => flipTool")))
    check("and promotes it onto the shelf",
          "selectToolBtn" in page.evaluate(
              "() => [...document.querySelectorAll('#toolGroup .tool-btn')]"
              ".filter(b => !b.hidden).map(b => b.id)"))

    print("\nSELECT — the marquee takes whole strokes and only the ones it covers")
    fresh(page)
    two_shapes(page)
    groups = page.evaluate("() => frames[idx].strokeGroups.slice()")
    before = page.evaluate(SNAP)
    check("two strokes were drawn", len(groups) == 2, str(groups))
    page.evaluate("() => setTool('select')")
    page.wait_for_timeout(200)
    drag(page, (80, 90), (240, 240))          # round the square only
    spans = page.evaluate("() => selSpans.map(s => s.slice())")
    check("exactly one stroke is selected", len(spans) == 1, str(spans))
    check("and the span covers that stroke whole, not a fragment",
          spans == [[0, groups[0]]], f"{spans} against groups {groups}")

    print("\nSELECT — dragging moves the selection and nothing else")
    drag(page, (155, 165), (255, 265))        # +100, +100
    after = page.evaluate(SNAP)
    n = groups[0]
    sel_dx = {a[0] - b[0] for a, b in zip(after[:n], before[:n])}
    sel_dy = {a[1] - b[1] for a, b in zip(after[:n], before[:n])}
    rest = [[a[0] - b[0], a[1] - b[1]] for a, b in zip(after[n:], before[n:])]
    check("every point of the selected stroke moved by the same delta",
          len(sel_dx) <= 2 and len(sel_dy) <= 2,
          f"dx {sorted(sel_dx)}, dy {sorted(sel_dy)} — a spread means the drag "
          f"was applied more than once to some points")
    check("it actually moved", sel_dx and max(sel_dx) > 50, str(sorted(sel_dx)))
    check("the unselected stroke did not move",
          all(d == [0, 0] for d in rest), str(rest))

    print("\nSELECT — undo is exact, and so is redo")
    entry = page.evaluate("() => actionLog[actionLog.length - 1]")
    check("the drag left one selmove entry on the action log",
          isinstance(entry, dict) and entry.get("type") == "selmove", str(entry))
    check("scoped to this page, not to the whole frame set",
          isinstance(entry, dict) and entry.get("idx") == 0 and "spans" in entry,
          str(entry))
    page.evaluate("() => undoStroke()")
    page.wait_for_timeout(250)
    undone = page.evaluate(SNAP)
    check("undo puts every point back exactly where it started",
          undone == before,
          "Pad needed a clone-before-snapshot dance for this; Flip's undo is the "
          "same translation negated, so there is nothing to alias")
    page.evaluate("() => redoStroke()")
    page.wait_for_timeout(250)
    check("redo reapplies it exactly", page.evaluate(SNAP) == after)

    print("\nSELECT — it does not draw, and leaving it drops the selection")
    fresh(page)
    two_shapes(page)
    n_groups = page.evaluate("() => frames[idx].strokeGroups.length")
    page.evaluate("() => setTool('select')")
    page.wait_for_timeout(150)
    drag(page, (80, 90), (240, 240))
    check("a marquee drag lays down no stroke",
          page.evaluate("() => frames[idx].strokeGroups.length") == n_groups,
          "the tool has to intercept the pointer BEFORE the drawing path, the "
          "same place moveMode does")
    check("something is selected before the tool changes",
          len(page.evaluate("() => selSpans")) >= 1,
          str(page.evaluate("() => selSpans")))
    page.evaluate("() => setTool('pen')")
    page.wait_for_timeout(200)
    check("switching tools clears the selection",
          page.evaluate("() => selSpans.length") == 0,
          "an invisible selection that a later drag would move is worse than "
          "making the user re-pick")

    print("\nSELECT — Pad still does not have it")
    pad = browser.new_page(viewport={"width": 900, "height": 800})
    pad.goto(BASE + "/", wait_until="load")
    pad.wait_for_timeout(400)
    check("Pad's registry does not list select",
          pad.evaluate("() => window.SkriblPadTools.list()") == ["pen", "eraser", "shape"],
          str(pad.evaluate("() => window.SkriblPadTools.list()"))
          + " — v219 removed it because Pad replays on recorded timestamps")
    check("and Pad's shelf shows no select cell",
          pad.locator("#selectToolBtn").count() == 0)
    pad.close()

    check("no page errors anywhere in this suite", not errors, "; ".join(errors[:3]))
    browser.close()

bad = [r for r in results if not r[0]]
print(f"\n{'=' * 62}\n{len(results) - len(bad)}/{len(results)} passed"
      + ("" if not bad else "  FAILURES: " + ", ".join(n for _, n in bad)))
sys.exit(1 if bad else 0)
