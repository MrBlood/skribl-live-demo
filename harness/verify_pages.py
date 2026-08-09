"""v107 — onion-skin depth + tint, page reorder / copy-paste, and clear redo.

Three items off ROADMAP's Flip and Pad feature lists.

Everything here is view-only or in-memory: onion depth/tint are session state that
is deliberately NOT persisted or posted, and reorder/paste mutate the existing
`frames` array. **No payload field is added and no format changes**, so a v107
Skribl opens in an older player and vice versa. That is asserted below rather than
assumed, because it is the property that keeps per-frame duration and variable
canvas sizes (the two remaining features) honest when they land — those two DO
change the format, and this suite is the baseline they will have to preserve.
"""
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:5001"

results = []
def check(name, ok, detail=""):
    results.append((bool(ok), name))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  — {detail}" if detail else ""))


def draw(pg, sel, x0, y0, n=18):
    b = pg.locator(sel).bounding_box()
    pg.mouse.move(b["x"] + x0, b["y"] + y0)
    pg.mouse.down()
    for i in range(n):
        pg.mouse.move(b["x"] + x0 + i * 8, b["y"] + y0 + (i % 4) * 6)
    pg.mouse.up()
    pg.wait_for_timeout(120)


# Counts pixels that differ from the backdrop, so "is onion drawing more?" is
# measured off the canvas rather than inferred from state. Note it CANNOT key on
# alpha: drawBackdrop() paints an opaque background, so every pixel reads 255 and
# an alpha-based count silently returns the whole canvas for every input.
INK = """() => {
    const cv = document.getElementById('pad');
    const g = cv.getContext('2d');
    const d = g.getImageData(0, 0, cv.width, cv.height).data;
    const br = d[0], bg = d[1], bb = d[2];      // top-left pixel is backdrop
    let n = 0;
    for (let i = 0; i < d.length; i += 4) {
        if (Math.abs(d[i]-br) + Math.abs(d[i+1]-bg) + Math.abs(d[i+2]-bb) > 18) n++;
    }
    return n; }"""

with sync_playwright() as p:
    br = p.chromium.launch()
    ctx = br.new_context(viewport={"width": 1280, "height": 900})
    flip = ctx.new_page()
    errs = []
    flip.on("pageerror", lambda e: errs.append(str(e)))
    flip.goto(BASE + "/flip", wait_until="load")
    flip.wait_for_timeout(1000)

    # Four pages, each with a different amount of ink so reordering is visible.
    for i in range(4):
        flip.evaluate("() => addFrame()")
        draw(flip, "#pad", 70 + i * 30, 90, n=10 + i * 6)

    print("\nONION — depth and tint")
    # v129: onion depth/tint moved out of the header into the settings drawer, so
    # they are opened rather than revealed, and the row DIMS when onion is off
    # instead of hiding (hiding made the panel jump height while toggling).
    flip.click("#tuneBtn")
    flip.wait_for_timeout(350)
    check("the settings drawer opens",
          flip.evaluate("() => document.getElementById('tuneShell').classList.contains('open')"))
    check("onion depth/tint live there and are reachable",
          flip.evaluate("""() => document.getElementById('onionDepthSeg').getBoundingClientRect().width > 0
                            && document.getElementById('onionTintBtn').getBoundingClientRect().width > 0"""))
    flip.evaluate("() => setOnion(false)")
    flip.wait_for_timeout(200)
    check("the onion row dims when onion is off, without changing the panel height",
          flip.evaluate("() => document.getElementById('tuneOnionRow').classList.contains('muted')"))
    flip.evaluate("() => setOnion(true)")
    flip.wait_for_timeout(200)
    check("and undims when it is back on",
          flip.evaluate("() => !document.getElementById('tuneOnionRow').classList.contains('muted')"))

    flip.click('#onionDepthSeg button[data-depth="1"]')
    flip.wait_for_timeout(250)
    ink1 = flip.evaluate(INK)
    flip.click('#onionDepthSeg button[data-depth="3"]')
    flip.wait_for_timeout(250)
    ink3 = flip.evaluate(INK)
    check("depth control sets the state", flip.evaluate("() => onionDepth") == 3)
    check("depth 3 actually paints more than depth 1 (measured on canvas)",
          ink3 > ink1, f"{ink1} px -> {ink3} px")

    before_tint = flip.evaluate(INK)
    flip.click("#onionTintBtn")
    flip.wait_for_timeout(250)
    check("tint toggles", flip.evaluate("() => onionTint") is True)
    check("tint repaints without changing coverage (silhouette recolour, not extra ink)",
          abs(flip.evaluate(INK) - before_tint) < max(40, before_tint * 0.02),
          f"{before_tint} -> {flip.evaluate(INK)}")
    tinted = flip.evaluate("""() => {
        const cv=document.getElementById('pad'), g=cv.getContext('2d');
        const d=g.getImageData(0,0,cv.width,cv.height).data;
        let warm=0;
        for(let i=0;i<d.length;i+=4){ if(d[i+3]>8 && d[i]>d[i+2]+30) warm++; }
        return warm; }""")
    check("tinted onion frames are visibly warm-coloured", tinted > 0, f"{tinted} warm px")

    flip.evaluate("() => { go(0); }")
    flip.wait_for_timeout(250)
    check("depth clamps to the pages that exist (no onion on page 1)",
          flip.evaluate("() => idx") == 0 and not errs, "; ".join(errs[:1]))
    # The header must keep its overflow menu reachable — the reason the drawer
    # exists. Asserted at a phone width, where it used to be pushed off screen.
    check("the more-menu stays on screen with the drawer open",
          flip.evaluate("""() => document.getElementById('moreBtn').getBoundingClientRect().right
                            <= innerWidth + 1"""))
    flip.click("#tuneBtn")
    # Wait for the grid-template-rows transition to actually SETTLE rather than
    # sleeping a fixed 300ms and hoping. The fixed wait was a race: it read
    # 0.015625 on one run and 2.234375 on another — the second is a fifth of a
    # visible pixel-row, not rounding noise, and a tolerance would have hidden a
    # genuinely unfinished animation. Poll until the height stops changing.
    flip.evaluate("() => { window.__stableH = null; window.__stableN = 0; }")
    flip.wait_for_function("""() => {
        const h = document.getElementById('tuneShell').getBoundingClientRect().height;
        if (window.__stableH === h) { window.__stableN += 1; }
        else { window.__stableH = h; window.__stableN = 0; }
        return window.__stableN >= 3;
    }""", polling=100, timeout=8000)
    # v130: the drawer animates (grid-template-rows), so state is a CLASS, not the
    # hidden attribute — and closed must mean zero height, not merely not-open.
    check("the drawer closes again",
          flip.evaluate("() => !document.getElementById('tuneShell').classList.contains('open')"))
    # EXACT zero, restored. This assertion was intermittently reading 0.015625,
    # then 2.234375, then 16.328125 under load — and the first reading invited a
    # sub-pixel tolerance, which would have been the wrong fix: the larger
    # numbers show the drawer was simply still animating. The cause was the
    # fixed 300ms sleep above, not fractional geometry. With a real settle-wait
    # the height is exactly 0 every time, so the original strict claim stands.
    _h = flip.evaluate("() => document.getElementById('tuneShell').getBoundingClientRect().height")
    check("and collapses to exactly zero height, leaving no sliver under the header",
          _h == 0, str(_h))
    check("it sits directly under the header, not adrift elsewhere on the page",
          flip.evaluate("""() => { const h=document.querySelector('.header').getBoundingClientRect();
              const s=document.getElementById('tuneShell').getBoundingClientRect();
              return Math.abs(s.top - h.bottom) < 12; }"""))
    flip.evaluate("() => { go(frames.length-1); }")
    flip.wait_for_timeout(200)

    print("\nPAGES — reorder, copy, paste")
    order = flip.evaluate("() => frames.map(f => f.strokes.length)")
    cur = flip.evaluate("() => idx")
    flip.evaluate("() => movePage(idx, -1)")
    flip.wait_for_timeout(250)
    moved = flip.evaluate("() => frames.map(f => f.strokes.length)")
    expected = order[:]
    expected[cur - 1], expected[cur] = expected[cur], expected[cur - 1]
    check("move left swaps the two pages", moved == expected, f"{order} -> {moved}")
    check("the page you were on stays the page you're on",
          flip.evaluate("() => idx") == cur - 1, f"idx {cur} -> {flip.evaluate('() => idx')}")

    # v124: per-page controls moved OUT of the tile into #pagebar, so the guards
    # are asserted there. The thumbnail carries no controls at all now.
    flip.evaluate("() => go(0)"); flip.wait_for_timeout(250)
    check("Move-left is disabled on the first page",
          flip.evaluate("() => document.getElementById('pbLeft').disabled"))
    flip.evaluate("() => go(frames.length-1)"); flip.wait_for_timeout(250)
    check("Move-right is disabled on the last page",
          flip.evaluate("() => document.getElementById('pbRight').disabled"))
    check("the toolbar names the selected page",
          "Page " in flip.evaluate("() => document.getElementById('pbWho').textContent"),
          flip.evaluate("() => document.getElementById('pbWho').textContent"))
    check("no controls overlay the thumbnail any more",
          flip.evaluate("() => !document.querySelector('.frame-ops')"))
    # VISIBLE targets only. This selected every .pb on the page, which now
    # includes the move bar's buttons while it is hidden — a hidden element has
    # zero height, so the check failed on controls that were not on screen.
    # Filtering by offsetParent keeps it honest either way: when the move bar
    # IS open, its buttons are measured like any other.
    check("toolbar targets are at least 38px (were 18px in-tile)",
          flip.evaluate("""() => [...document.querySelectorAll('.pb')]
              .filter(b => b.offsetParent !== null)
              .every(b => b.getBoundingClientRect().height >= 38)"""))
    # margin-left:auto resolves to a pixel value, so assert the OUTCOME — a real
    # gap between Delete and its neighbour — rather than the declaration.
    check("Delete is visually separated from the other actions",
          flip.evaluate("""() => { const d=document.getElementById('pbDel').getBoundingClientRect();
              const h=document.getElementById('pbHold').getBoundingClientRect();
              return d.left - h.right > 16; }"""),
          flip.evaluate("""() => Math.round(document.getElementById('pbDel').getBoundingClientRect().left
              - document.getElementById('pbHold').getBoundingClientRect().right) + 'px gap'"""))

    flip.evaluate("() => { pageClip = null; buildStrip(); }")
    check("no paste button before anything is copied",
          flip.evaluate("() => !document.getElementById('addpaste')"))
    flip.click("#pbCopy")
    flip.wait_for_timeout(300)
    check("copy fills the clipboard", flip.evaluate("() => !!pageClip"))
    check("and the paste button appears", flip.evaluate("() => !!document.getElementById('addpaste')"))

    n0 = flip.evaluate("() => frames.length")
    at = flip.evaluate("() => idx")
    flip.click("#addpaste")
    flip.wait_for_timeout(300)
    check("paste inserts a page", flip.evaluate("() => frames.length") == n0 + 1,
          f"{n0} -> {flip.evaluate('() => frames.length')}")
    check("pasted page lands right after the current one",
          flip.evaluate("() => idx") == at + 1)

    # The clipboard must hand out independent copies, or editing one pasted page
    # silently edits every other paste of it.
    flip.click("#addpaste")
    flip.wait_for_timeout(300)
    check("pasting twice gives two independent pages",
          flip.evaluate("""() => {
              const a = frames[idx], b = frames[idx-1];
              if (!a.strokes.length) return false;
              a.strokes[0].x = -999;
              return b.strokes[0].x !== -999; }"""))

    print("\nFORMAT — none of this touched the payload")
    payload = flip.evaluate("() => JSON.stringify(serializeFlip())")
    for field in ("onionDepth", "onionTint", "pageClip"):
        check(f"no '{field}' leaks into the posted payload", field not in payload)
    check("no Flip page errors across the whole feature set", not errs, "; ".join(errs[:2]))

    print("\nPAD — Undo now offers Redo (v106 was one-shot)")
    pad = ctx.new_page()
    pad_errs = []
    pad.on("pageerror", lambda e: pad_errs.append(str(e)))
    pad.goto(BASE + "/", wait_until="load")
    pad.wait_for_timeout(1000)
    draw(pad, "#canvas", 80, 80, n=24)
    pad.evaluate("() => document.getElementById('recordBtn').click()")
    pad.wait_for_timeout(700)
    n_before = pad.evaluate("() => strokes.length")
    pad.evaluate("() => { document.getElementById('clearMenuItem').click(); }")
    pad.evaluate("() => { document.getElementById('clearMenuItem').click(); }")
    pad.wait_for_timeout(600)
    check("cleared", pad.evaluate("() => strokes.length") == 0)
    pad.click(".toast-action")          # Undo
    pad.wait_for_timeout(800)
    check("Undo restores", pad.evaluate("() => strokes.length") == n_before)
    redo = pad.evaluate("""() => { const b=document.querySelector('.toast-action');
                                   return b ? b.textContent : null; }""")
    check("the restore toast now offers Redo", redo == "Redo", repr(redo))
    pad.click(".toast-action")          # Redo
    pad.wait_for_timeout(800)
    check("Redo clears again", pad.evaluate("() => strokes.length") == 0)
    again = pad.evaluate("""() => { const b=document.querySelector('.toast-action');
                                    return b ? b.textContent : null; }""")
    check("and Redo re-offers Undo, so it toggles either way", again == "Undo", repr(again))
    check("no Pad page errors", not pad_errs, "; ".join(pad_errs[:2]))

    # -----------------------------------------------------------------------
    print("\nSTRIP SCROLL — a restored draft opens with its page in view")
    #
    # THE BUG. buildStrip() rebuilds the strip's children, which resets
    # scrollLeft to 0. applyPayload() restores idx but nothing scrolled, so a
    # 62-page animation reopened on page 62 with the strip parked at page 1 —
    # the active tile highlighted somewhere off-screen. addFrame() was the only
    # caller that scrolled, so the fix existed and was never shared.
    #
    # Measured as GEOMETRY — the active tile's box against the strip's box —
    # because scrollLeft alone cannot tell you whether the tile is visible.
    sp = br.new_page(viewport={"width": 900, "height": 900})
    sp_errs = []
    sp.on("pageerror", lambda e: sp_errs.append(str(e)))
    sp.goto(f"{BASE}/flip", wait_until="load")
    sp.wait_for_timeout(1200)

    sp.evaluate("() => { for (let i = 0; i < 40; i++) addFrame(false); }")
    sp.wait_for_timeout(600)
    total = sp.evaluate("() => frames.length")
    check("a long animation was built", total > 30, str(total))

    # Draw one stroke so the draft is non-empty and autosave keeps it.
    box = sp.locator("#pad").bounding_box()
    sp.mouse.move(box["x"] + 60, box["y"] + 60)
    sp.mouse.down()
    sp.mouse.move(box["x"] + 140, box["y"] + 120, steps=6)
    sp.mouse.up()
    sp.wait_for_timeout(1200)
    saved_idx = sp.evaluate("() => idx")
    check("the draft was left on a late page", saved_idx > 30, str(saved_idx))

    sp.reload(wait_until="load")
    sp.wait_for_timeout(1800)
    check("the restored draft reopens on the same page",
          sp.evaluate("() => idx") == saved_idx,
          f"{sp.evaluate('() => idx')} vs {saved_idx}")

    vis = sp.evaluate("""() => {
      const el = strip.children[idx];
      if (!el) return null;
      const a = el.getBoundingClientRect(), b = strip.getBoundingClientRect();
      return { visible: a.left >= b.left - 2 && a.right <= b.right + 2,
               scrollLeft: strip.scrollLeft };
    }""")
    check("the active tile is within the strip's viewport after a refresh",
          vis and vis["visible"],
          f"active tile is off-screen; strip.scrollLeft = "
          f"{vis['scrollLeft'] if vis else '?'}")
    check("and the strip is not parked at the far left",
          vis and vis["scrollLeft"] > 0,
          "scrollLeft is 0 while a late page is active")
    check("no JS errors during restore", not sp_errs, "; ".join(sp_errs[:2]))
    sp.close()

    br.close()

ok = sum(1 for o, _ in results if o)
print("\n" + "=" * 60)
print(f"{ok}/{len(results)} passed")
for o, n in results:
    if not o:
        print(f"  FAILED: {n}")
raise SystemExit(0 if ok == len(results) else 1)
