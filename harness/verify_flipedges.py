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
  * a tile's x says its arm out loud and names its page;
  * the pen lands where it is put out to the canvas's edges (FUTURE 6r): the
    canvas wears a 2px frame and the drawing fills its inside, and the pen was
    read as a share of the whole box, frame and all, so a pen a pixel in from
    an edge landed about 2px further in. Each edge on a desk and a phone, the
    left and top zoomed to 200% (the frame at the zoom's scale); the
    eyedropper reads the ink under the pen at the edge; artwork dragged moves
    as far as the pointer went; the replay's dot over the drawing's corner
    sits on that corner. The drawing's box is read from the frame's own width
    (getComputedStyle), at the zoom's scale.
"""
import math
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


# The drawing's own box on the screen: the canvas's box less its frame (its
# border, read from the style), at the scale the zoom shows it.
INNER = """() => { const c = document.getElementById('pad'), r = c.getBoundingClientRect(), cs = getComputedStyle(c);
  const s = c.offsetWidth ? r.width / c.offsetWidth : 1;
  const bl = (parseFloat(cs.borderLeftWidth) || 0) * s, br = (parseFloat(cs.borderRightWidth) || 0) * s;
  const bt = (parseFloat(cs.borderTopWidth) || 0) * s, bb = (parseFloat(cs.borderBottomWidth) || 0) * s;
  return { left: r.left + bl, top: r.top + bt, right: r.right - br, bottom: r.bottom - bb,
           width: r.width - bl - br, height: r.height - bt - bb, CW, CH, frame: bl / s }; }"""


def edge_points(pg, edges, touch=False):
    """A pen put one screen pixel in from each named edge of the drawing's own
    box (at a whole pixel), moved 30px inward; the stroke's first point
    against where that pixel is in the drawing's units."""
    out = {}
    for e in edges:
        m = pg.evaluate(INNER)
        ux, uy = m["CW"] / m["width"], m["CH"] / m["height"]
        mx, my = round(m["left"] + m["width"] * 0.43), round(m["top"] + m["height"] * 0.47)
        x, y, dx, dy = {"left": (math.ceil(m["left"] + 1), my, 30, 0), "right": (math.floor(m["right"] - 1), my, -30, 0),
                        "top": (mx, math.ceil(m["top"] + 1), 0, 30), "bottom": (mx, math.floor(m["bottom"] - 1), 0, -30)}[e]
        want = [(x - m["left"]) * ux, (y - m["top"]) * uy]
        n = pg.evaluate("() => frame().strokes.length")
        if touch:
            pg.touchscreen.tap(x, y)
        else:
            pg.mouse.move(x, y)
            pg.mouse.down()
            for k in range(1, 7):
                pg.mouse.move(x + dx * k / 6, y + dy * k / 6)
            pg.mouse.up()
        pg.wait_for_timeout(120)
        got = pg.evaluate("(n) => { const p = frame().strokes[n]; return p ? [p.x, p.y] : null; }", n)
        out[e] = (got, want)
    return out


def edges_ok(out, tol=0.25):
    return all(g and abs(g[0] - w[0]) <= tol and abs(g[1] - w[1]) <= tol for g, w in out.values())


def edges_say(out):
    return "; ".join(f"{e}: at {[round(v, 2) for v in g] if g else None}, under the pen {[round(v, 2) for v in w]}"
                     for e, (g, w) in out.items())


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

    # ---------------------------------------------------------------------
    print("\nFLIP — the pen lands where it is put, out to the canvas's edges")
    ctx, pg, errs = flip(b)
    pg.evaluate("() => setTool('pen')")
    out = edge_points(pg, ["left", "right", "top", "bottom"])
    frame_px = pg.evaluate(INNER)["frame"]
    check("desk: a pen a pixel in from each edge of the drawing lands a pixel's worth from that edge",
          frame_px > 0 and edges_ok(out), f"the frame {frame_px}px; " + edges_say(out))
    # THE EYEDROPPER, the ink under the pen at the edge: a band of red 3 units
    # wide along the drawing's left edge, read a pixel in from it (about 1 to
    # 2.3 units in; the frame's 2px put the reading past the band).
    pg.evaluate("""() => { const f = frame(); const n = 12;
      for (let k = 0; k < n; k++) f.strokes.push({ x: 1.5, y: 40 + k * 40, color: '#e01010', size: 3, t: 0, start: k === 0 });
      f.strokeGroups.push(n); render(); }""")
    m = pg.evaluate(INNER)
    picked = pg.evaluate("""(at) => { const was = color; sampleColorAt({ clientX: at[0], clientY: at[1] }); const got = color;
      setColor(was); return got; }""", [math.ceil(m["left"] + 1), round(m["top"] + m["height"] * 0.5)])
    check("desk: the eyedropper reads the ink under the pen a pixel in from the edge",
          picked.lower() in ("#e01010",), f"picked {picked} a pixel in from the left edge, over a 3-unit red band")
    # ARTWORK DRAGGED moves as far as the pointer went, in the drawing's units.
    pg.evaluate("() => setTool('artmove')")
    m = pg.evaluate(INNER)
    x0, y0 = round(m["left"] + m["width"] * 0.3), round(m["top"] + m["height"] * 0.4)
    pg.mouse.move(x0, y0)
    pg.mouse.down()
    for k in range(1, 9):
        pg.mouse.move(x0 + 320 * k / 8, y0 + 160 * k / 8)
    pg.mouse.up()
    pg.wait_for_timeout(150)
    moved = pg.evaluate("() => [moveDx, moveDy]")
    want = [320 * m["CW"] / m["width"], 160 * m["CH"] / m["height"]]
    check("desk: artwork dragged moves as far as the pointer went, in the drawing's units",
          abs(moved[0] - want[0]) <= 0.25 and abs(moved[1] - want[1]) <= 0.25,
          f"moved {[round(v, 2) for v in moved]}; the pointer went {[round(v, 2) for v in want]}")
    pg.keyboard.press("Escape")
    pg.wait_for_timeout(200)
    # THE REPLAY'S DOT over the drawing's top-left corner sits on that corner.
    dot = pg.evaluate("""() => { const was = playing; playing = true;
      revealNib({ strokes: [{ x: 0, y: 0 }, { x: 0, y: 0 }] }, 1); playing = was;
      const n = document.querySelector('.flip-wrap .player-nib'), w = n.parentElement.getBoundingClientRect();
      return [w.left + parseFloat(n.style.left), w.top + parseFloat(n.style.top)]; }""")
    m = pg.evaluate(INNER)
    pg.evaluate("() => { const n = document.querySelector('.flip-wrap .player-nib'); if (n) n.hidden = true; }")
    check("desk: the replay's dot over the drawing's corner sits on that corner",
          abs(dot[0] - m["left"]) <= 0.25 and abs(dot[1] - m["top"]) <= 0.25,
          f"the dot at {[round(v, 2) for v in dot]}; the corner {[round(m['left'], 2), round(m['top'], 2)]}")
    # ZOOMED TO 200%, the left and top edges: the frame at the zoom's scale.
    pg.evaluate("() => setTool('pen')")
    pg.evaluate("() => { ZoomView.enable(); ZoomView.zoomAt(2, 0, 0); }")
    pg.wait_for_timeout(300)
    zoom = pg.evaluate("() => ZoomView.get().zoom")
    out = edge_points(pg, ["left", "top"])
    check("desk, zoomed to 200%: the pen a pixel in from the left and top edges lands a pixel's worth from them",
          zoom >= 1.99 and edges_ok(out), f"zoom {zoom}; " + edges_say(out))
    check("no page errors through the edges on a desk", not errs, "; ".join(errs[:2]))
    ctx.close()
    ctx, pg, errs = flip(b, PHONE)
    pg.evaluate("() => setTool('pen')")
    out = edge_points(pg, ["left", "right", "top", "bottom"], touch=True)
    check("phone: a finger a pixel in from each edge of the drawing lands a pixel's worth from that edge",
          edges_ok(out), edges_say(out))
    check("no page errors through the edges on a phone", not errs, "; ".join(errs[:2]))
    ctx.close()
    b.close()

passed = sum(1 for ok, _ in results if ok)
bad = [name for ok, name in results if not ok]
print("\n" + "=" * 62)
print(f"{passed}/{len(results)} passed" + ("" if not bad else "\nFAILURES:\n  - " + "\n  - ".join(bad)))
sys.exit(1 if bad else 0)
