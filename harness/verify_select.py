"""Select on Flip: marquee a subset of one page, then move, scale or rotate it.

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

TRANSFORM SCALES STROKE WEIGHT, and that is the reason it is worth having rather
than a curiosity. A point is `{x, y, color, size, t, erase}` and `size` is
PER-POINT, so a scale multiplies weight along with position: shrink a drawing and
its strokes get thinner, instead of the same-weight outline of a smaller shape.
Rotation leaves `size` alone. Both are pinned.

Only the four CORNERS scale, and the scale is uniform. One scalar `size` has no
honest answer for a non-uniform scale — stretch a drawing horizontally and the
verticals would need to be thicker than the horizontals, which one number cannot
express — so edge handles are absent by design rather than missing.

Undo for a transform RESTORES COORDINATES rather than inverting itself, unlike
selmove, which negates its dx/dy. Negating a translate is exact; dividing by a
scale ratio is not, and repeated undo/redo would walk the artwork off its mark.
Pinned by comparing every point, including its size, against the original.

PAD MUST NOT GET THE TOOL. v219's reasoning still holds there, so the last
section asserts Pad's registry does not list it — otherwise a future "make the
surfaces match" would quietly reintroduce the bug v219 removed.
"""
import math
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
# Full precision plus size: the transform pins compare weight as well as
# position, and rounding to whole pixels would hide a scale that missed.
SNAP_FULL = ("() => frames[idx].strokes.map(p => [p.x, p.y, p.size])")


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
    its strokes waiting for the next one — the marquee was catching a restored
    square as well as the new one, and reported two selections where the test
    meant one.

    Clearing localStorage is NOT enough on its own, and that cost a debugging
    round: the live page still holds the drawing in memory, and reloading makes
    it save on the way out — so the draft is written back after the clear and
    restored by the very reload meant to be rid of it. Empty the document first,
    then clear, then reload, so the save-on-unload has nothing to write."""
    page.goto(BASE + "/flip", wait_until="load")
    page.wait_for_timeout(250)
    page.evaluate("() => { frames = [newFrame()]; idx = 0;"
                  " try { buildStrip(); render(); } catch (e) {}"
                  " for (const k of Object.keys(localStorage))"
                  " if (k.indexOf('skribl') === 0) localStorage.removeItem(k); }")
    page.reload(wait_until="load")
    page.wait_for_timeout(450)
    n = page.evaluate("() => frames.reduce((a, f) => a + f.strokes.length, 0)")
    if n:
        raise SystemExit(f"fresh() left {n} points behind — the suite cannot "
                         f"trust any stroke-index assertion after this")


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
    # Exact, not "contains": a roster change is a change to what the product is,
    # and it should cost a deliberate edit here. Liquify joined at v236 — same
    # division as select, since it edits geometry already on the page.
    #
    # ⚑ RATCHET RAISED, v227, FLAGGED FOR THE OWNER — and it is the SECOND copy
    # of this ratchet. verify_tray.py holds the other one, was updated when
    # "artmove" joined, and this file was missed until the release run found it.
    # Two exact rosters in two suites is one more than the mechanism needs;
    # whether they should be one shared assertion is a real question, and the
    # answer is not "delete this one", because a ratchet nobody has to edit is a
    # ratchet that stops meaning anything.
    #
    # ⚑ RATCHET RAISED, v238 — "stamp", and unlike artmove it IS a new
    # capability. Both copies raised together this time.
    #
    # artmove is NOT a new capability. Move artwork has shipped since v124 and
    # lived in the PAGE BAR — the one control in a row about pages that moved
    # the DRAWING. Read it as a control moving house.
    check("select is in Flip's tool registry",
          page.evaluate("() => window.SkriblFlipTools.list()")
          == ["pen", "eraser", "shape", "select", "liquify", "smudge", "blur", "fill",
             "stamp", "artmove"],
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

    print("\nSELECT — the corner handles scale, and weight scales with them")
    fresh(page)
    two_shapes(page)
    groups = page.evaluate("() => frames[idx].strokeGroups.slice()")
    n = groups[0]
    before = page.evaluate(SNAP_FULL)
    page.evaluate("() => setTool('select')")
    page.wait_for_timeout(200)
    check("no handles while nothing is selected",
          page.evaluate("() => selHandles()") is None)
    drag(page, (80, 90), (240, 240))
    h = page.evaluate("() => { const h = selHandles(); return h && {"
                      "corners: h.corners.map(c => ({id:c.id, x:c.x, y:c.y})),"
                      "rot: h.rotate, c: h.centre }; }")
    check("a selection gets four corner handles and a rotate grip",
          h is not None and len(h["corners"]) == 4 and "rot" in h,
          str(h and [c["id"] for c in h["corners"]]))
    to_screen = page.evaluate("() => { const r = pad.getBoundingClientRect();"
                              " return CW / r.width; }")
    se = next(c for c in h["corners"] if c["id"] == "se")
    nw = next(c for c in h["corners"] if c["id"] == "nw")
    # Pull the SE corner out to 1.5x the diagonal from NW, which is the pivot.
    tgt = {"x": nw["x"] + (se["x"] - nw["x"]) * 1.5,
           "y": nw["y"] + (se["y"] - nw["y"]) * 1.5}
    drag(page, (se["x"] / to_screen, se["y"] / to_screen),
               (tgt["x"] / to_screen, tgt["y"] / to_screen), steps=14)
    after = page.evaluate(SNAP_FULL)

    def span(rows, ax):
        return max(r[ax] for r in rows) - min(r[ax] for r in rows)

    grew = span(after[:n], 0) / span(before[:n], 0)
    check("the selection scaled by the drag ratio", 1.4 < grew < 1.6,
          f"x{grew:.2f} against a 1.5 drag")
    weight = (sum(r[2] for r in after[:n]) / sum(r[2] for r in before[:n]))
    check("and stroke weight scaled with it", abs(weight - grew) < 0.05,
          f"geometry x{grew:.2f}, size x{weight:.2f} — a scale that leaves size "
          f"alone gives you a bigger shape drawn with the same pen")
    check("the unselected stroke was not touched",
          after[n:] == before[n:], str(after[n:]))

    print("\nSELECT — undo and redo of a transform are exact, size included")
    entry = page.evaluate("() => actionLog[actionLog.length - 1]")
    check("the drag left one seltransform entry",
          isinstance(entry, dict) and entry.get("type") == "seltransform", str(entry))
    page.evaluate("() => undoStroke()")
    page.wait_for_timeout(250)
    check("undo restores every coordinate AND every size",
          page.evaluate(SNAP_FULL) == before,
          "a transform restores coordinates rather than inverting itself, "
          "because dividing by a scale ratio does not always land back")
    page.evaluate("() => redoStroke()")
    page.wait_for_timeout(250)
    check("redo reapplies it exactly", page.evaluate(SNAP_FULL) == after)

    print("\nSELECT — the rotate grip turns the artwork and leaves weight alone")
    page.evaluate("() => undoStroke()")
    page.wait_for_timeout(250)
    h = page.evaluate("() => { const h = selHandles();"
                      " return h && { rot: h.rotate, c: h.centre }; }")
    rot, cen = h["rot"], h["c"]
    radius = math.hypot(rot["x"] - cen["x"], rot["y"] - cen["y"])
    # Swing the grip from straight up to straight right: a quarter turn.
    tgt = {"x": cen["x"] + radius, "y": cen["y"]}
    drag(page, (rot["x"] / to_screen, rot["y"] / to_screen),
               (tgt["x"] / to_screen, tgt["y"] / to_screen), steps=16)
    turned = page.evaluate(SNAP_FULL)
    check("rotation left stroke weight untouched",
          [r[2] for r in turned[:n]] == [r[2] for r in before[:n]],
          "only a scale changes size; a rotation must not")
    # Every selected point should have swung by about the same angle about the
    # centre. Compare the first and last point's angular change.
    def ang(r):
        return math.atan2(r[1] - cen["y"], r[0] - cen["x"])

    deltas = [(ang(a) - ang(b) + math.pi) % (2 * math.pi) - math.pi
              for a, b in zip(turned[:n], before[:n])]
    spread = max(deltas) - min(deltas)
    check("every point turned by the same angle", spread < 0.05,
          f"spread {spread:.3f} rad — a spread means the rotation was applied "
          f"on top of itself rather than recomputed from the snapshot")
    check("and it actually turned about a quarter", 1.3 < abs(deltas[0]) < 1.85,
          f"{deltas[0]:.2f} rad")
    check("rotation logged a transform too",
          page.evaluate("() => actionLog[actionLog.length - 1].type") == "seltransform")

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

    print("\nSELECT — the selection bar replaces the page bar")
    fresh(page)
    two_shapes(page)
    page.evaluate("() => setTool('select')")
    page.wait_for_timeout(200)
    check("no selection bar while nothing is selected",
          page.evaluate("() => document.getElementById('selbar').hidden"))
    drag(page, (80, 90), (240, 240))
    check("selecting shows the bar",
          not page.evaluate("() => document.getElementById('selbar').hidden"))
    check("and takes the page bar's row rather than adding one",
          page.evaluate("() => document.getElementById('pagebar').hidden"),
          "five more actions do not fit on a 320px phone as extra chrome")
    check("the bar says what is selected",
          page.evaluate("() => document.getElementById('sbWho').textContent") == "1 stroke",
          page.evaluate("() => document.getElementById('sbWho').textContent"))
    check("Paste is absent until there is something to paste",
          page.evaluate("() => document.getElementById('sbPaste').hidden"),
          "a disabled control on a bar this tight is a cell of dead width")

    print("\nSELECT — mirror reflects about the selection's own centre")
    groups = page.evaluate("() => frames[idx].strokeGroups.slice()")
    n = groups[0]
    before = page.evaluate(SNAP_FULL)
    bounds = page.evaluate("() => { const b = selBounds();"
                           " return [b.x, b.y, b.w, b.h]; }")
    cx = bounds[0] + bounds[2] / 2
    page.click("#sbFlipH")
    page.wait_for_timeout(300)
    after = page.evaluate(SNAP_FULL)
    check("every selected point reflects across the centre line",
          all(abs(after[i][0] - (2 * cx - before[i][0])) < 1e-6 for i in range(n)),
          "a mirror that is not about the selection's own centre makes the "
          "artwork jump across the page instead of flipping where it sits")
    check("mirror leaves y alone",
          all(after[i][1] == before[i][1] for i in range(n)))
    check("and leaves stroke weight alone",
          all(after[i][2] == before[i][2] for i in range(n)),
          "a reflection does not change how thick a line is, only which way "
          "it points")
    check("the unselected stroke is untouched", after[n:] == before[n:])
    page.evaluate("() => undoStroke()")
    page.wait_for_timeout(250)
    check("mirror undoes exactly", page.evaluate(SNAP_FULL) == before)

    print("\nSELECT — duplicate leaves the COPY selected")
    fresh(page)
    two_shapes(page)
    page.evaluate("() => setTool('select')")
    page.wait_for_timeout(150)
    drag(page, (80, 90), (240, 240))
    g0 = page.evaluate("() => frames[idx].strokeGroups.slice()")
    page.click("#sbDup")
    page.wait_for_timeout(300)
    g1 = page.evaluate("() => frames[idx].strokeGroups.slice()")
    check("a duplicate appends one group per selected stroke",
          g1 == g0 + [g0[0]], f"{g0} -> {g1}")
    spans = page.evaluate("() => selSpans.map(s => s.slice())")
    check("and the COPY is what stays selected",
          spans and spans[0][0] >= sum(g0),
          f"{spans} against {sum(g0)} points before the copy — selecting the "
          f"original would move it instead, silently, since the two overlap")
    page.evaluate("() => undoStroke()")
    page.wait_for_timeout(250)
    check("duplicate undoes back to the original groups",
          page.evaluate("() => frames[idx].strokeGroups.slice()") == g0)

    print("\nSELECT — cut remembers, and paste can land on another page")
    fresh(page)
    two_shapes(page)
    page.evaluate("() => setTool('select')")
    page.wait_for_timeout(150)
    drag(page, (80, 90), (240, 240))
    g0 = page.evaluate("() => frames[idx].strokeGroups.slice()")
    n0 = page.evaluate("() => frames[idx].strokes.length")
    page.click("#sbCut")
    page.wait_for_timeout(300)
    check("cut removes the selected group and its points",
          page.evaluate("() => frames[idx].strokeGroups.slice()") == g0[1:]
          and page.evaluate("() => frames[idx].strokes.length") == n0 - g0[0],
          f"{g0} -> {page.evaluate('() => frames[idx].strokeGroups.slice()')}")
    check("Paste appears once the clipboard has something",
          not page.evaluate("() => document.getElementById('sbPaste').hidden"),
          "without a clipboard, Cut would be Delete wearing the wrong name")
    page.evaluate("() => undoStroke()")
    page.wait_for_timeout(250)
    check("cut undoes back to every group",
          page.evaluate("() => frames[idx].strokeGroups.slice()") == g0)
    page.evaluate("() => redoStroke()")
    page.wait_for_timeout(250)
    check("and redoes", page.evaluate("() => frames[idx].strokeGroups.slice()") == g0[1:])
    # The point of a clipboard in a flipbook: take artwork off one page and put
    # it on the next.
    page.evaluate("() => addFrame(false)")
    page.wait_for_timeout(300)
    check("a new page starts empty",
          page.evaluate("() => frames[idx].strokeGroups.length") == 0)
    page.evaluate("() => selPaste()")
    page.wait_for_timeout(300)
    check("paste lands the cut artwork on THIS page",
          page.evaluate("() => frames[idx].strokeGroups.slice()") == [g0[0]],
          str(page.evaluate("() => frames[idx].strokeGroups.slice()")))
    check("and selects what it pasted",
          page.evaluate("() => selSpans.length") == 1)

    print("\nSELECT — a selection never crosses pages")
    check("changing page drops the selection",
          page.evaluate("() => { go(0); return selSpans.length; }") == 0,
          "spans are index ranges into ONE page's strokes; carried over they "
          "would point at different artwork, or run off a shorter page")

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
