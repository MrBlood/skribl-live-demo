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
    check("the controls appear with onion on",
          flip.evaluate("() => !document.getElementById('onionGroup').hidden"))
    flip.evaluate("() => setOnion(false)")
    flip.wait_for_timeout(200)
    check("and hide with onion off, so the toolbar isn't permanently crowded",
          flip.evaluate("() => document.getElementById('onionGroup').hidden"))
    flip.evaluate("() => setOnion(true)")
    flip.wait_for_timeout(200)

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

    check("move-left is disabled on the first page",
          flip.evaluate("""() => strip.children[0].querySelector('[data-mv="-1"]').disabled"""))
    check("move-right is disabled on the last page",
          flip.evaluate("""() => { const n=frames.length;
              return strip.children[n-1].querySelector('[data-mv="1"]').disabled; }"""))

    flip.evaluate("() => { pageClip = null; buildStrip(); }")
    check("no paste button before anything is copied",
          flip.evaluate("() => !document.getElementById('addpaste')"))
    flip.locator(".frame.on [data-cp]").click(force=True)
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

    br.close()

ok = sum(1 for o, _ in results if o)
print("\n" + "=" * 60)
print(f"{ok}/{len(results)} passed")
for o, n in results:
    if not o:
        print(f"  FAILED: {n}")
raise SystemExit(0 if ok == len(results) else 1)
