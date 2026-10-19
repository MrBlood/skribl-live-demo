"""Flip's edges a read-only review found before the next seal (after v326).

Driven through the real page with a real mouse or touch, desk and phone where
the two differ. Each section was red on the code before its fix:

  * "Undo clear" works when tapped: the press on it spent the backup (any
    lift on the page did) before its click arrived;
  * a new document starts with no history: Undo after New Skribl pulled a
    deleted page into it, or threw and left every stroke after it throwing;
  * an undo acts on the page it was done on, after a Duplicate shifted the
    pages under it, for a selection's Flip and for a tween;
  * the page bar takes no press during playback on a desk;
  * "Select through here" works on a phone, from the page you were on;
  * after Cut, Paste is within reach on a blank page, and Ctrl+V pastes;
  * the page strip counts pages, not the paste ghost, while a page is copied;
  * a tile's x says its arm out loud and names its page.
"""
import os
import sys

BASE = os.environ.get("SKRIBL_BASE", "http://127.0.0.1:5001")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from assertions import make_check  # noqa: E402

try:
    from playwright.sync_api import sync_playwright
except Exception as exc:                                   # pragma: no cover
    print(f"SUITE-SKIPPED: playwright unavailable ({exc})")
    raise SystemExit(77)

results = []
check = make_check(results)
DESK = dict(viewport={"width": 1280, "height": 860})
PHONE = dict(viewport={"width": 402, "height": 874}, has_touch=True, is_mobile=True, device_scale_factor=3)
SIG = """() => frames.map(f => f.strokes.length ? Math.round(f.strokes[0].x) + ',' + Math.round(f.strokes[0].y) + '/' + f.strokes.length : 'empty')"""
TILES = "#strip .frame:not(.ghost-paste)"


def flip(b, ctx_opts=DESK):
    ctx = b.new_context(**ctx_opts)
    pg = ctx.new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(BASE + "/flip", wait_until="load")
    pg.evaluate("() => localStorage.clear()")
    pg.reload(wait_until="load")
    pg.wait_for_function("() => window.__skriblBoot && window.__skriblBoot.flip", timeout=15000)
    pg.wait_for_timeout(500)
    pg.evaluate("() => window.SkriblHints && window.SkriblHints.hide()")
    return ctx, pg, errs


def stroke(pg, x0, y0, dx=120, dy=40):
    b = pg.locator("#pad").bounding_box()
    pg.mouse.move(b["x"] + x0, b["y"] + y0)
    pg.mouse.down()
    for k in range(1, 12):
        pg.mouse.move(b["x"] + x0 + dx * k / 11, b["y"] + y0 + dy * k / 11)
    pg.mouse.up()
    pg.wait_for_timeout(80)


def drag(pg, x0, y0, x1, y1):
    b = pg.locator("#pad").bounding_box()
    pg.mouse.move(b["x"] + x0, b["y"] + y0)
    pg.mouse.down()
    for k in range(1, 12):
        pg.mouse.move(b["x"] + x0 + (x1 - x0) * k / 11, b["y"] + y0 + (y1 - y0) * k / 11)
    pg.mouse.up()
    pg.wait_for_timeout(150)


def chip(pg):
    return pg.evaluate("() => document.getElementById('flipChip').textContent")


def three_pages(pg):
    stroke(pg, 60, 60)
    pg.click("#addblank")
    stroke(pg, 200, 120, 60, 80)
    pg.click("#addblank")
    stroke(pg, 300, 200, 90, 10)


with sync_playwright() as sp:
    b = sp.chromium.launch()

    print("\nFLIP — Undo clear works when tapped")

    def two_cleared():
        ctx, pg, errs = flip(b)
        stroke(pg, 40, 60)
        pg.click("#addblank")
        stroke(pg, 90, 60)
        pg.evaluate("() => { if (!_flipDrawerCtl.isOpen('draw')) document.getElementById('penToolBtn').click(); }")
        pg.wait_for_timeout(400)
        pg.click("#clear")
        pg.wait_for_timeout(120)
        pg.click("#clear")
        pg.wait_for_timeout(300)
        return ctx, pg, errs

    ctx, pg, errs = two_cleared()
    cleared = pg.evaluate("() => frames.length")
    pg.click("#clearUndo", force=True)               # a real press and lift, then the click
    pg.wait_for_timeout(300)
    back = pg.evaluate("() => frames.length")
    check("Clear all pages, then a tap on Undo clear brings both pages back",
          cleared == 1 and back == 2 and "restored" in chip(pg),
          f"after clear {cleared} page(s); after the tap {back}, chip {chip(pg)!r}")
    check("no page errors around Undo clear", not errs, "; ".join(errs[:2]))
    ctx.close()
    ctx, pg, errs = two_cleared()
    pg.keyboard.press("Control+z")                  # nothing to undo on the empty page
    pg.wait_for_timeout(150)
    kept = pg.evaluate("() => ({ backup: !!clearFramesBackup, disabled: document.getElementById('clearUndo').disabled })")
    check("...and a Ctrl+Z with nothing to undo leaves Undo clear standing",
          kept["backup"] and not kept["disabled"], str(kept))
    ctx.close()

    print("\nFLIP — a new document starts with no history")
    ctx, pg, errs = flip(b)
    three_pages(pg)
    pg.click("#toolMoreBtn")
    pg.wait_for_timeout(300)
    pg.locator("#toolTray [data-tool=fill]").first.click()
    pg.wait_for_timeout(200)
    box = pg.locator("#pad").bounding_box()
    pg.mouse.click(box["x"] + 30, box["y"] + box["height"] - 30)   # a fill on page 3
    pg.wait_for_timeout(600)
    pg.click("#moreBtn")
    pg.wait_for_timeout(400)
    pg.click("#menuNewTile")
    pg.wait_for_timeout(400)
    pg.click("#miClearAll")
    pg.wait_for_timeout(500)
    pg.keyboard.press("Control+z")
    pg.wait_for_timeout(300)
    after = pg.evaluate("() => ({ pages: frames.length, idx, log: actionLog.length })")
    errs_after_undo = list(errs)
    pg.click("#penToolBtn")
    pg.wait_for_timeout(200)
    stroke(pg, 100, 100)
    pg.wait_for_timeout(300)
    check("after New Skribl an Undo finds no old history, and the next stroke draws",
          after["pages"] == 1 and after["idx"] == 0 and after["log"] == 0 and not errs
          and pg.evaluate("() => frames[0].strokeGroups.length") == 1,
          f"{after}; errors after the undo {errs_after_undo[:1]}, after a stroke {errs[:1]}")
    ctx.close()

    print("\nFLIP — an undo acts on the page it was done on, after a Duplicate")
    ctx, pg, errs = flip(b)
    three_pages(pg)
    before = pg.evaluate(SIG)
    pg.evaluate("() => shelfSetTool('select')")
    pg.wait_for_timeout(200)
    drag(pg, 280, 180, 420, 240)                     # a marquee round page C's stroke
    pg.click("#sbFlipH")
    pg.wait_for_timeout(200)
    pg.click("#sbDone")
    pg.wait_for_timeout(200)
    flipped = pg.evaluate(SIG)
    pg.locator(TILES).nth(0).click()
    pg.wait_for_timeout(200)
    pg.click("#addcopy")                             # Duplicate A: B and C shift right
    pg.wait_for_timeout(200)
    pg.click("#undo")
    pg.wait_for_timeout(300)
    undone = pg.evaluate(SIG)
    check("a selection's Flip on page C, undone after Duplicate on A, puts C back and leaves B alone",
          flipped[2] != before[2] and undone == [before[0], before[0], before[1], before[2]],
          f"before {before}; flipped {flipped}; after Duplicate and Undo {undone}")
    ctx.close()
    ctx, pg, errs = flip(b)
    three_pages(pg)
    pg.locator(TILES).nth(1).click()
    pg.wait_for_timeout(200)
    pg.click("#addinbetween")                        # a tween after B
    pg.wait_for_timeout(500)
    tween = pg.evaluate(SIG)
    pg.locator(TILES).nth(0).click()
    pg.wait_for_timeout(200)
    pg.click("#addcopy")
    pg.wait_for_timeout(200)
    pg.click("#undo")
    pg.wait_for_timeout(300)
    undone = pg.evaluate(SIG)
    pg.click("#redo")
    pg.wait_for_timeout(300)
    alias = pg.evaluate("() => frames.some((f, i) => frames.indexOf(f) !== i)")
    check("a tween undone after Duplicate takes the tween, not the artist's page, and Redo makes no alias",
          len(tween) == 4 and undone == [tween[0], tween[0], tween[1], tween[3]] and not alias,
          f"with the tween {tween}; after Duplicate and Undo {undone}; same page twice after Redo: {alias}")
    check("no page errors around undo after a Duplicate", not errs, "; ".join(errs[:2]))
    ctx.close()

    print("\nFLIP — the page bar takes no press during playback (desk)")
    ctx, pg, errs = flip(b)
    for k, x in enumerate((40, 90, 140, 190)):
        if k:
            pg.click("#addblank")
        stroke(pg, x, 60)
    pg.locator(TILES).nth(0).click()
    pg.wait_for_timeout(150)
    pg.click("#play")
    pg.wait_for_timeout(260)
    st = pg.evaluate("""() => ({ playing, del: document.getElementById('pbDel').disabled,
        left: document.getElementById('pbLeft').disabled, pages: frames.length })""")
    pg.click("#pbDel", force=True)
    pg.wait_for_timeout(150)
    pages = pg.evaluate("() => frames.length")
    check("while it plays, Delete and Move are disabled, and a press deletes nothing",
          st["playing"] and st["del"] and st["left"] and pages == 4, f"{st}; pages after a press {pages}")
    ctx.close()

    print("\nFLIP — Select through here, on a phone")
    ctx, pg, errs = flip(b, PHONE)
    for k, x in enumerate((30, 60, 90, 120)):
        if k:
            pg.click("#addblank")
        stroke(pg, x, 60, 80, 30)
    tiles = pg.locator(TILES)
    tiles.nth(0).click()
    pg.wait_for_timeout(200)
    tiles.nth(2).click()                             # page 3: its own ⋯ is the one shown
    pg.wait_for_timeout(200)
    tiles.nth(2).locator(".pageops").click()
    pg.wait_for_timeout(300)
    item = pg.locator(".pageops-menu .pageops-item", has_text="Select through here")
    enabled = item.count() == 1 and item.is_enabled()
    if enabled:
        item.click()
        pg.wait_for_timeout(300)
    span = pg.evaluate("() => pageSpan()")
    check("on page 3, after page 1, Select through here is offered and selects pages 1 to 3",
          enabled and span and span["from"] == 0 and span["to"] == 2, f"enabled {enabled}; span {span}")
    ctx.close()

    print("\nFLIP — after Cut, Paste on a blank page")
    for label, opts in (("desk", DESK), ("phone", dict(viewport={"width": 402, "height": 874}))):
        ctx, pg, errs = flip(b, opts)
        drag(pg, 60, 60, 160, 100)                   # a stroke on page 1
        pg.evaluate("() => shelfSetTool('select')")
        pg.wait_for_timeout(150)
        drag(pg, 40, 40, 200, 130)                   # a marquee round it
        pg.click("#sbCut")
        pg.wait_for_timeout(200)
        pg.click("#addblank")
        pg.wait_for_timeout(250)
        vis = pg.evaluate("""() => { const v = id => { const e = document.getElementById(id); if (!e) return false;
            for (let n = e; n; n = n.parentElement) if (n.hidden) return false; return e.offsetParent !== null; };
            return { paste: v('sbPaste'), cut: v('sbCut') }; }""")
        if vis["paste"]:
            pg.click("#sbPaste")
            pg.wait_for_timeout(200)
        pasted = pg.evaluate("() => frames[idx].strokes.length")
        check(f"{label}: on a new blank page after Cut, the bar offers Paste (not Cut), and Paste lands the strokes",
              vis["paste"] and not vis["cut"] and pasted > 0, f"bar {vis}; strokes on the page {pasted}")
        ctx.close()
    ctx, pg, errs = flip(b)
    drag(pg, 60, 60, 160, 100)
    pg.evaluate("() => shelfSetTool('select')")
    pg.wait_for_timeout(150)
    drag(pg, 40, 40, 200, 130)
    pg.click("#sbCut")
    pg.wait_for_timeout(200)
    pg.click("#addblank")
    pg.wait_for_timeout(200)
    pg.keyboard.press("Control+v")
    pg.wait_for_timeout(200)
    check("desk: ...and Ctrl+V pastes them too", pg.evaluate("() => frames[idx].strokes.length") > 0,
          str(pg.evaluate("() => frames[idx].strokes.length")))
    ctx.close()

    print("\nFLIP — the page strip counts pages, not the paste ghost")
    ctx, pg, errs = flip(b)
    for k, x in enumerate((40, 90, 140, 190, 240)):
        if k:
            pg.click("#addblank")
        stroke(pg, x, 60)
    pg.locator(TILES).nth(0).click()
    pg.wait_for_timeout(150)
    pg.click("#pbCopy")                              # the ghost Paste tile appears after page 1
    pg.wait_for_timeout(200)
    pg.click("#play")
    off = 0
    for _ in range(30):
        pg.wait_for_timeout(37)
        r = pg.evaluate("""() => { const real = [...document.querySelectorAll('#strip .frame:not(.ghost-paste)')];
            const now = [...document.querySelectorAll('#strip .frame.now')];
            return now.length === 1 && real.indexOf(now[0]) === idx; }""")
        off += 0 if r else 1
    pg.click("#play")
    check("with a page copied, the playing outline is on the page that plays at every sample",
          off == 0, f"{off} of 30 samples off")
    ctx.close()

    print("\nFLIP — a tile's x says its arm and names its page")
    ctx, pg, errs = flip(b)
    stroke(pg, 40, 60)
    pg.click("#addblank")
    stroke(pg, 90, 60)
    x = pg.locator(TILES).nth(1).locator(".del")
    name0 = x.get_attribute("aria-label")
    x.click(force=True)
    pg.wait_for_timeout(150)
    said = pg.evaluate("() => (document.getElementById('confirmStatus') || {}).textContent || ''")
    armed = x.get_attribute("aria-label")
    check("the x is named for its page, and its first press is said and shown",
          name0 == "Delete page 2" and said == "Tap again to delete page 2" and armed == "Tap again to delete page 2",
          f"name {name0!r}; said {said!r}; armed name {armed!r}")
    ctx.close()
    b.close()

passed = sum(1 for ok, _ in results if ok)
bad = [name for ok, name in results if not ok]
print("\n" + "=" * 62)
print(f"{passed}/{len(results)} passed" + ("" if not bad else "\nFAILURES:\n  - " + "\n  - ".join(bad)))
sys.exit(1 if bad else 0)
