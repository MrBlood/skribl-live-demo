"""The editor's controls for the loop and the page underneath (Blooby, PR 3).

The owner's card, as a person makes it: draw the card on page 1, Keep under,
select the waving pages, Loop, step it to Forever. verify_loop and verify_under
pin what a post stores and how every surface plays it; this suite pins the
controls that set it, driven the way a person drives them -- real clicks on the
page bar, the strip's chip and the compact ⋯ menu -- and read back from what the
strip draws and what a post would carry.

Sections: the Loop button's cycle (x2 -> x3 -> x4 -> 2 s -> 4 s -> 6 s ->
Forever -> off) on a span, and a new stretch starting over at x2; the strip's
chip as the same control; Keep under as a switch, and refused on the last page;
the strip's marks (the bracket on the loop's pages only, the chip on its first,
the blue edge and "Under" on the page underneath, the pages after a Forever
loop dimmed) each with an accessible name; the compact ⋯ menu's two items; the
loop and the page underneath FOLLOWING their pages through a delete, a move and
an added page; the draft and the post body carrying what the controls set; and
the export sheet stating the file's real length, loop included, and that a
Forever loop is cut.

Calibrated red per component: the button's cycle, the chip, the switch, the
last-page refusal, each mark, the menu items, the following, the export line.
"""
import os
import sys

from assertions import make_check
import browsing

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("SKIP: playwright is not installed")
    sys.exit(0)

BASE = os.environ.get("SKRIBL_BASE", "http://127.0.0.1:5001")
results = []
check = make_check(results)

# Seven pages, each with one stroke so a page is never "empty" to any path.
SETUP = """(n) => { frames = Array.from({ length: n }, (_, k) => { const f = newFrame();
    f.strokes = [{ x: 60 + k * 40, y: 100, color: '#ffffff', size: 6, t: 0, start: true },
                 { x: 60 + k * 40, y: 300, color: '#ffffff', size: 6, t: 0 }];
    f.strokeGroups = [2]; return f; });
  docLoop = null; docUnder = null; idx = 0; spanAnchor = null; buildStrip(); render(); }"""
TILES = "#strip .frame:not(.ghost-paste)"
STATE = "() => ({ loop: docLoop, under: docUnder, n: frames.length })"


def tiles(pg):
    return pg.evaluate("""() => [...document.querySelectorAll('#strip .frame:not(.ghost-paste)')].map(t => ({
        cls: t.className,
        band: !!t.querySelector('.loopband'),
        chip: (t.querySelector('.loopchip') || {}).textContent || null,
        chipName: t.querySelector('.loopchip') ? t.querySelector('.loopchip').getAttribute('aria-label') : null,
        under: !!t.querySelector('.underlabel'),
        underName: t.querySelector('.underlabel') ? t.querySelector('.underlabel').getAttribute('aria-label') : null,
        noplayName: t.querySelector('.noplaymark') ? t.querySelector('.noplaymark').getAttribute('aria-label') : null }))""")


with sync_playwright() as p:
    b = p.chromium.launch()

    print("\nTHE PAGE BAR — Loop steps through every kind and off; Under is a switch")
    ctx = b.new_context(viewport={"width": 1280, "height": 900})
    pg = ctx.new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    browsing.goto(pg, BASE, "/flip")
    pg.evaluate("() => window.SkriblHints && window.SkriblHints.hide()")
    pg.evaluate(SETUP, 7)
    pg.evaluate("() => { idx = 1; buildStrip(); }")
    pg.locator(TILES).nth(4).click(modifiers=["Shift"])          # pages 2-5
    seen = []
    for _ in range(8):
        pg.click("#pbLoop")
        st = pg.evaluate(STATE)
        seen.append(st["loop"])
    want = [{"times": 2}, {"times": 3}, {"times": 4}, {"ms": 2000}, {"ms": 4000}, {"ms": 6000},
            {"forever": True}, None]
    got = [None if l is None else {k: v for k, v in l.items() if k not in ("from", "to")} for l in seen]
    check("Loop on a span steps x2, x3, x4, 2 s, 4 s, 6 s, Forever, then off", got == want, str(got))
    check("...and every step is on the span's pages", all(l is None or (l["from"], l["to"]) == (1, 4) for l in seen),
          str(seen))
    pg.click("#pbLoop")                                             # x2 on 2-5
    pg.evaluate("() => { clearSpan(true); idx = 5; buildStrip(); }")
    pg.click("#pbLoop")
    st = pg.evaluate(STATE)
    check("Loop on a different stretch starts THAT stretch over at x2",
          st["loop"] == {"from": 5, "to": 5, "times": 2}, str(st["loop"]))
    label = pg.locator("#pbLoop .pb-tx").inner_text()
    check("...and the button names the loop it is on", label.strip() == "×2", repr(label))
    # A SELECTION THAT IS NOT THE LOOP SAYS WHICH PAGES A TAP WILL LOOP (owner:
    # a loop of page 2 alone read as "2-7 loops forever" with 2-7 selected).
    pg.evaluate("() => { idx = 1; buildStrip(); }")
    pg.locator(TILES).nth(6).click(modifiers=["Shift"])          # pages 2-7, the loop is on page 6
    label = pg.locator("#pbLoop .pb-tx").inner_text()
    check("with a selection that is not the loop, the button says which pages a tap loops",
          label.strip() == "Loop 2–7", repr(label))
    pg.evaluate("() => { clearSpan(true); buildStrip(); }")

    # The chip on the strip is the same control.
    pg.evaluate("() => { docLoop = { from: 1, to: 4, times: 4 }; idx = 0; buildStrip(); }")
    pg.locator("#strip .loopchip").click()
    st = pg.evaluate(STATE)
    check("the strip's chip steps the loop as the button does", st["loop"] == {"from": 1, "to": 4, "ms": 2000},
          str(st["loop"]))
    # THE OWNER'S TRAP (three saved files in a row): page 2 looped alone, 2-22
    # selected, and the chip tapped -- it stepped page 2's loop. With pages
    # selected the chip loops the SELECTION, keeping the loop's setting.
    pg.evaluate("() => { docLoop = { from: 1, to: 1, forever: true }; idx = 1; buildStrip(); }")
    pg.locator(TILES).nth(5).click(modifiers=["Shift"])          # pages 2-6 selected
    pg.locator("#strip .loopchip").click()
    st = pg.evaluate(STATE)
    check("with pages selected, the chip loops the selection, keeping Forever",
          st["loop"] == {"from": 1, "to": 5, "forever": True}, str(st["loop"]))
    if pg.locator("#strip .loopchip").count():                      # gone, the check above is the report
        pg.locator("#strip .loopchip").click()
    check("...and tapped again on that same stretch, it steps it", pg.evaluate(STATE)["loop"] is None,
          str(pg.evaluate(STATE)["loop"]))
    pg.evaluate("() => { clearSpan(true); docLoop = { from: 1, to: 1, times: 3 }; idx = 1; buildStrip(); }")
    pg.locator(TILES).nth(4).click(modifiers=["Shift"])          # pages 2-5
    pg.click("#pbLoop")
    check("the page bar's Loop moves a loop to the selection with its setting, too",
          pg.evaluate(STATE)["loop"] == {"from": 1, "to": 4, "times": 3}, str(pg.evaluate(STATE)["loop"]))
    pg.evaluate("() => { clearSpan(true); buildStrip(); }")

    # Under: a switch on this page.
    pg.evaluate("() => { docLoop = null; idx = 0; buildStrip(); }")
    pg.click("#pbUnder")
    st = pg.evaluate(STATE)
    check("Keep under makes this page the page under every page after it",
          st["under"] == {"page": 0, "from": 1, "to": 6}, str(st["under"]))
    check("...and the switch says it is on",
          pg.get_attribute("#pbUnder", "aria-checked") == "true")
    pg.click("#pbUnder")
    check("tapped again, it turns off", pg.evaluate(STATE)["under"] is None)
    pg.evaluate("() => { idx = frames.length - 1; buildStrip(); }")
    check("on the last page it is refused: there are no pages after it",
          pg.evaluate("() => document.getElementById('pbUnder').disabled") is True)

    print("\nTHE STRIP — the bracket, the chip, the page underneath, the pages that never play")
    pg.evaluate("() => { docLoop = { from: 1, to: 4, forever: true }; docUnder = { page: 0, from: 1, to: 6 }; idx = 2; buildStrip(); }")
    t = tiles(pg)
    check("the bracket is on the loop's pages and no others",
          [x["band"] for x in t] == [False, True, True, True, True, False, False], str([x["band"] for x in t]))
    check("its ends are marked, so the stretch reads from its ends",
          "loop-first" in t[1]["cls"] and "loop-last" in t[4]["cls"], str([x["cls"] for x in t[1:5]]))
    check("the chip is on the loop's first page only, and says what the loop is",
          [x["chip"] for x in t] == [None, "Forever · 2–5", None, None, None, None, None], str([x["chip"] for x in t]))
    check("...and its accessible name says which pages and that it changes",
          t[1]["chipName"] == "Loop forever on pages 2–5, tap to change", str(t[1]["chipName"]))
    check("the page underneath carries its edge and its name",
          "underpage" in t[0]["cls"] and t[0]["under"]
          and t[0]["underName"] == "Page 1 stays under pages 2–7", str(t[0]))
    check("the pages after a Forever loop are dimmed, and only those",
          ["noplay" in x["cls"] for x in t] == [False, False, False, False, False, True, True],
          str(["noplay" in x["cls"] for x in t]))
    check("...and each says why, to a screen reader",
          t[5]["noplayName"] == "Page 6 never plays: the loop before it is Forever", str(t[5]["noplayName"]))
    # ...AND TO THE EYE, painted, under a selection's frame too: the dimming
    # alone was invisible on thin strokes, and nothing at all once selected.
    pg.evaluate("() => { idx = 1; buildStrip(); }")
    pg.locator(TILES).nth(6).click(modifiers=["Shift"])
    tag = pg.evaluate("""() => [...document.querySelectorAll('#strip .frame')].map(f => {
        const g = f.querySelector('.noplaytag'); if (!g) return null;
        f.scrollIntoView({ block: 'nearest', inline: 'nearest' }); const r = g.getBoundingClientRect();
        // The tag is pointer-events:none (a tap belongs to the tile), and
        // elementFromPoint skips such elements: hit-testable for the probe only.
        g.style.pointerEvents = 'auto';
        const at = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
        g.style.pointerEvents = '';
        return { text: g.textContent, painted: !!(at && g.contains(at)) }; })""")
    check("each page that never plays says \"Won't play\" on its tile, painted, with the pages selected",
          [x and x["text"] for x in tag] == [None, None, None, None, None, "Won’t play", "Won’t play"]
          and all(x["painted"] for x in tag if x), str(tag))
    # The chip names ONE page as a page: the owner's own document, a loop of page
    # 2 alone, read as the 2-7 the selection's label put beside it.
    pg.evaluate("() => { docLoop = { from: 1, to: 1, forever: true }; buildStrip(); }")
    chip1 = pg.evaluate("() => document.querySelector('#strip .loopchip').textContent")
    check("a loop of one page names it, so it cannot read as the selection's range",
          chip1 == "Forever · page 2", repr(chip1))
    pg.evaluate("() => { clearSpan(true); docLoop = { from: 1, to: 4, forever: true }; idx = 2; buildStrip(); }")
    pg.evaluate("() => { docLoop = { from: 1, to: 4, times: 2 }; buildStrip(); }")
    check("a loop that ends leaves every page playing",
          not any("noplay" in x["cls"] for x in tiles(pg)))

    print("\nFOLLOWING THE PAGES — a delete, a move and an added page")
    pg.evaluate("() => { docLoop = { from: 1, to: 4, times: 2 }; docUnder = { page: 0, from: 1, to: 6 }; buildStrip(); }")
    pg.evaluate("() => { clearSpan(true); delFrame(2); }")
    st = pg.evaluate(STATE)
    check("deleting a page inside the loop shrinks it, and the page underneath keeps the rest",
          st["loop"] == {"from": 1, "to": 3, "times": 2} and st["under"] == {"page": 0, "from": 1, "to": 5},
          str(st))
    pg.evaluate("() => { idx = 0; addFrame(false); }")              # a blank page after page 1
    st = pg.evaluate(STATE)
    check("a page added before the loop moves it along, and lands under the card",
          st["loop"] == {"from": 2, "to": 4, "times": 2} and st["under"] == {"page": 0, "from": 1, "to": 6},
          str(st))
    pg.evaluate("() => { idx = frames.length - 1; addFrame(false); }")
    st = pg.evaluate(STATE)
    check("a page added at the end is under the card too (it ran to the last page)",
          st["under"] == {"page": 0, "from": 1, "to": 7}, str(st))
    # KEEP UNDER MEANS "UNDER THE PAGES AFTER IT", so moving the card one page
    # right carries it and keeps it under the pages after it -- the page it
    # passed is now before it, and no longer under it.
    pg.evaluate("() => { movePage(0, 1); }")
    st = pg.evaluate(STATE)
    check("moving the page underneath carries it, still under the pages after it",
          st["under"] == {"page": 1, "from": 2, "to": 7}, str(st))
    pg.evaluate("() => { movePage(1, -1); }")
    check("...and moving it back puts it back", pg.evaluate(STATE)["under"] == {"page": 0, "from": 1, "to": 7},
          str(pg.evaluate(STATE)))
    pg.evaluate("() => { delFrame(0); }")
    check("deleting the page underneath removes it", pg.evaluate(STATE)["under"] is None, str(pg.evaluate(STATE)))

    print("\nTHE DRAFT AND THE POST — what the controls set is what a post carries")
    pg.evaluate(SETUP, 7)
    pg.evaluate("() => { idx = 1; buildStrip(); }")
    pg.locator(TILES).nth(4).click(modifiers=["Shift"])
    for _ in range(7):
        pg.click("#pbLoop")
    pg.evaluate("() => { clearSpan(true); idx = 0; buildStrip(); }")
    pg.click("#pbUnder")
    body = pg.evaluate("() => buildSharePayload()")
    check("the post carries the Forever loop and the page underneath the controls made",
          body.get("loop") == {"from": 1, "to": 4, "forever": True}
          and body.get("under") == {"page": 0, "from": 1, "to": 6}, str({k: body.get(k) for k in ("loop", "under")}))
    draft = pg.evaluate("() => serializeFlip({ media: false })")
    check("...and so does the draft", draft.get("loop") == body.get("loop") and draft.get("under") == body.get("under"),
          str({k: draft.get(k) for k in ("loop", "under")}))

    print("\nTHE EXPORT SHEET — the file's real length, and the Forever cut said out loud")
    line = pg.evaluate("() => { openExportSheet(); return document.getElementById('exportLoopsNote').textContent; }")
    check("a whole-document export with a Forever loop says the loop runs about 10 s a pass",
          "Forever loop runs about 10 s a pass" in line, repr(line))
    # The sheet's Loops setting repeats the whole file, so the length it states
    # is passes x one pass; one pass is the question here.
    one = pg.evaluate("() => exLoopSeconds()")
    check("...and one pass of the file is about 10 s, the loop included -- not one pass of 7 pages",
          9.5 <= one <= 12.5, f"one pass {one}s; the sheet says {line!r}")
    pg.evaluate("() => { docLoop = { from: 1, to: 4, times: 3 }; buildStrip(); }")
    a = pg.evaluate("() => exLoopSeconds()")
    pg.evaluate("() => { docLoop = null; buildStrip(); }")
    z = pg.evaluate("() => exLoopSeconds()")
    check("a x3 loop over 4 of 7 pages makes the file 15/7 as long as one pass",
          abs(a / z - 15 / 7) < 0.01, f"{a}s vs {z}s")
    check("no page errors on the editor", not errs, "; ".join(errs[:2]))
    ctx.close()

    print("\nTHE PHONE — the ⋯ menu carries both")
    ctx = b.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
    pg = ctx.new_page()
    browsing.goto(pg, BASE, "/flip")
    pg.evaluate("() => window.SkriblHints && window.SkriblHints.hide()")
    pg.evaluate(SETUP, 5)
    pg.evaluate("() => { idx = 2; buildStrip(); }")
    def menu():
        pg.locator("#strip .frame.on .pageops").click()
        pg.wait_for_timeout(250)
        return pg.evaluate("() => [...document.querySelectorAll('.pageops-menu .pageops-item')].map(b => b.textContent.trim())")
    items = menu()
    check("the ⋯ menu offers Loop and Keep under", "Loop" in items and "Keep under" in items, str(items))
    pg.locator(".pageops-menu .pageops-item", has_text="Loop").click()
    check("Loop from the menu loops this page", pg.evaluate(STATE)["loop"] == {"from": 2, "to": 2, "times": 2},
          str(pg.evaluate(STATE)))
    items = menu()
    check("...and on the loop it names the next step", "Loop ×3" in items, str(items))
    pg.keyboard.press("Escape")
    pg.evaluate("() => { idx = 0; buildStrip(); }")
    menu()
    pg.locator(".pageops-menu .pageops-item", has_text="Keep under").click()
    check("Keep under from the menu", pg.evaluate(STATE)["under"] == {"page": 0, "from": 1, "to": 4},
          str(pg.evaluate(STATE)))
    pg.keyboard.press("Escape")
    pg.evaluate("() => { docLoop = { from: 1, to: 3, times: 2 }; idx = 2; buildStrip(); }")
    items = menu()
    check("on a looped page the ⋯ menu offers Remove loop (owner: \"How do we undo a loop?\")",
          "Remove loop" in items, str(items))
    if "Remove loop" in items:                                      # absent, the check above is the report
        pg.locator(".pageops-menu .pageops-item", has_text="Remove loop").click()
    check("...and it removes the loop", pg.evaluate(STATE)["loop"] is None, str(pg.evaluate(STATE)["loop"]))
    print("\nTHE HANDLES — drag the loop's ends (owner: \"an easier way of picking the loop ... with the dragging tool\")")
    ctx = b.new_context(viewport={"width": 1400, "height": 1000})
    pg = ctx.new_page()
    browsing.goto(pg, BASE, "/flip")
    pg.evaluate("() => window.SkriblHints && window.SkriblHints.hide()")
    pg.evaluate(SETUP, 6)
    HN = "() => document.querySelectorAll('#strip .loophandle').length"
    check("no loop, no handles", pg.evaluate(HN) == 0, str(pg.evaluate(HN)))
    pg.evaluate("() => { docLoop = { from: 1, to: 3, times: 3 }; idx = 1; buildStrip(); }")
    check("a loop has two handles, named and valued as sliders",
          pg.evaluate("""() => [...document.querySelectorAll('#strip .loophandle')].map(h => [h.getAttribute('role'), h.getAttribute('aria-label'), h.getAttribute('aria-valuenow')])""")
          == [["slider", "Loop start", "2"], ["slider", "Loop end", "4"]])
    # The knob hangs BELOW the tiles (owner: "it would be interfered with by other
    # buttons ... can the handle be longer on the bottom?"), and the tile's own
    # controls along its top are still what a tap there reaches.
    geo = pg.evaluate("""() => { const t = document.querySelectorAll('#strip .frame')[1].getBoundingClientRect();
        const k = document.querySelector('#strip .loophandle.from .lh-knob').getBoundingClientRect();
        const at = document.elementFromPoint(k.left + k.width / 2, k.top + k.height / 2);
        const hit = sel => { const e = document.querySelectorAll('#strip .frame')[1].querySelector(sel); if (!e) return null;
          const r = e.getBoundingClientRect(); const a = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2); return !!(a && e.contains(a)); };
        return { knobTop: Math.round(k.top), tileBottom: Math.round(t.bottom), knobPainted: !!(at && at.closest('.loophandle.from')),
                 badge: hit('.holdbadge'), del: hit('.del') }; }""")
    check("the grab knob hangs below the tiles, painted", geo["knobTop"] >= geo["tileBottom"] and geo["knobPainted"], str(geo))
    check("...and the tile's hold badge and delete are still what a tap on them reaches",
          geo["badge"] is True and geo["del"] is True, str(geo))
    def drag(side, to_tile, edge):
        k = pg.locator(f"#strip .loophandle.{side} .lh-knob").bounding_box()
        t = pg.locator(TILES).nth(to_tile).bounding_box()
        x0, y0 = k["x"] + k["width"] / 2, k["y"] + k["height"] / 2
        x1 = t["x"] + (t["width"] if edge == "right" else 0)
        pg.mouse.move(x0, y0); pg.mouse.down()
        for s_ in range(1, 9): pg.mouse.move(x0 + (x1 - x0) * s_ / 8, y0)
        pg.wait_for_timeout(120)
        mid = pg.evaluate("""(side) => { const b = document.querySelector('#strip .loophandle.' + side + ' .lh-bubble');
            const r = b.getBoundingClientRect(); b.style.pointerEvents = 'auto';
            const a = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2); b.style.pointerEvents = '';
            return { text: b.textContent, painted: !!(a && b.contains(a)) }; }""", side)
        pg.mouse.up(); pg.wait_for_timeout(250)
        return mid
    mid = drag("to", 2, "right")
    check("dragging the end handle in shrinks the loop, keeping its count",
          pg.evaluate(STATE)["loop"] == {"from": 1, "to": 2, "times": 3}, str(pg.evaluate(STATE)["loop"]))
    check("...and while dragging it says the range, painted", mid == {"text": "Pages 2–3", "painted": True}, str(mid))
    drag("from", 4, "left")                                         # past the end, at page 3
    check("the start handle moves the start, and cannot pass the end",
          pg.evaluate(STATE)["loop"] == {"from": 2, "to": 2, "times": 3}, str(pg.evaluate(STATE)["loop"]))
    drag("to", 4, "right")
    check("the end handle grows it again", pg.evaluate(STATE)["loop"] == {"from": 2, "to": 4, "times": 3},
          str(pg.evaluate(STATE)["loop"]))
    pg.locator("#strip .loophandle.from").focus()
    pg.keyboard.press("ArrowLeft")
    check("a focused handle moves with the arrow keys, and keeps the focus",
          pg.evaluate(STATE)["loop"]["from"] == 1
          and pg.evaluate("() => document.activeElement && document.activeElement.matches('.loophandle.from')"),
          str(pg.evaluate(STATE)["loop"]))
    pg.evaluate("() => { idx = 0; buildStrip(); }")
    pg.click("#play"); pg.wait_for_timeout(300)
    n_playing = pg.evaluate(HN)
    pg.click("#play"); pg.wait_for_timeout(300)
    check("while it plays the handles step away, and come back after", n_playing == 0 and pg.evaluate(HN) == 2,
          f"playing {n_playing}, after {pg.evaluate(HN)}")
    # The way out (owner: "How do we undo a loop?"): Delete on a focused handle
    # here; the compact ⋯ menu's "Remove loop" is checked with the menu below.
    pg.locator("#strip .loophandle.to").focus()
    pg.keyboard.press("Delete")
    check("Delete on a focused handle removes the loop, handles and all",
          pg.evaluate(STATE)["loop"] is None and pg.evaluate(HN) == 0, str(pg.evaluate(STATE)["loop"]))
    ctx.close()
    b.close()

bad = [r for r in results if not r[0]]
print(f"\n{'=' * 62}\n{len(results) - len(bad)}/{len(results)} passed"
      + ("" if not bad else "  FAILURES: " + ", ".join(r[1] for r in bad)))
sys.exit(1 if bad else 0)
