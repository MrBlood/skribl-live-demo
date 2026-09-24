"""Onion-skin depth + tint, page reorder / copy-paste, and clear redo.

Three items off the (since-retired) roadmap's Flip and Pad feature lists.

Everything here is view-only or in-memory: onion depth/tint are session state that
is deliberately NOT persisted or posted, and reorder/paste mutate the existing
`frames` array. **No payload field is added and no format changes**, so a v107
Skribl opens in an older player and vice versa. That is asserted below rather than
assumed, because it is the property that keeps per-frame duration and variable
canvas sizes (the two remaining features) honest when they land — those two DO
change the format, and this suite is the baseline they will have to preserve.
"""
import os
from playwright.sync_api import sync_playwright
from assertions import make_check
import browsing

# Overridable so this suite can be pointed at a dev server while the harness
# holds 5001 — otherwise it silently tests the sweep's checkout, not the tree.
BASE = os.environ.get("SKRIBL_BASE", "http://127.0.0.1:5001")

results = []
check = make_check(results)


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
    browsing.goto(flip, BASE, "/flip")
    # The intro toast is a center panel that does NOT auto-dismiss, so it
    # sits over the canvas until closed. Dismiss it before drawing, or every
    # draw() lands on the panel instead of the canvas.
    flip.evaluate("() => { try { localStorage.setItem('skribl_hints_seen_v1',"
                  " JSON.stringify({'flip-intro':1})); } catch(e){} "
                  "const h=document.querySelector('.skribl-hint'); if(h){h.classList.remove('in');h.hidden=true;} }")

    # Four pages, each with a different amount of ink so reordering is visible.
    for i in range(4):
        flip.evaluate("() => addFrame()")
        draw(flip, "#pad", 70 + i * 30, 90, n=10 + i * 6)

    print("\nONION — depth and tint")
    # Onion depth/tint moved out of the header into the settings drawer, so
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
    # The drawer animates (grid-template-rows), so state is a CLASS, not the
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

    # Per-page controls moved OUT of the tile into #pagebar, so the guards
    # are asserted there. The thumbnail carries no controls at all now.
    flip.evaluate("() => go(0)"); flip.wait_for_timeout(250)
    check("Move-left is disabled on the first page",
          flip.evaluate("() => document.getElementById('pbLeft').disabled"))
    flip.evaluate("() => go(frames.length-1)"); flip.wait_for_timeout(250)
    check("Move-right is disabled on the last page",
          flip.evaluate("() => document.getElementById('pbRight').disabled"))
    # The VISIBLE text lost the word "Page" at v237 — it read "Page 21 / 43" and
    # cost 69px in a nowrap bar whose contents already measured 369px inside
    # 340 at a 360px viewport, so the Delete button was clipped off the end. The
    # intent of this assertion is that the bar tells you which page is selected,
    # and that is still true: the number is on screen and the ACCESSIBLE name
    # still reads "Page 21 of 43". Asserting the intent rather than the wording,
    # and asserting BOTH halves so a future tidy-up cannot drop the spoken one.
    _who = flip.evaluate("""() => { const e = document.getElementById('pbWho');
        return { txt: e.textContent.trim(), aria: e.getAttribute('aria-label') }; }""")
    check("the toolbar names the selected page, on screen and to a screen reader",
          any(c.isdigit() for c in _who["txt"]) and "Page" in (_who["aria"] or ""),
          f"{_who} — an abbreviation may shorten how a control LOOKS, never its "
          f"accessible name")
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
    # PbHold retired to the tile's own badge, so Delete's left-hand
    # neighbour is Copy now. Still asserting the OUTCOME — a real gap —
    # rather than which button happens to sit beside it.
    check("Delete is visually separated from the other actions",
          flip.evaluate("""() => { const d=document.getElementById('pbDel').getBoundingClientRect();
              const h=document.getElementById('pbCopy').getBoundingClientRect();
              return d.left - h.right > 16; }"""),
          flip.evaluate("""() => Math.round(document.getElementById('pbDel').getBoundingClientRect().left
              - document.getElementById('pbCopy').getBoundingClientRect().right) + 'px gap'"""))

    flip.evaluate("() => { pageClip = null; buildStrip(); }")
    check("no paste affordance before anything is copied",
          flip.evaluate("() => !document.querySelector('#strip .ghost-paste')"))
    flip.click("#pbCopy")
    flip.wait_for_timeout(300)
    check("copy fills the clipboard", flip.evaluate("() => !!pageClip"))
    check("and a ghost tile appears on the strip", flip.evaluate("() => !!document.querySelector('#strip .ghost-paste')"))

    n0 = flip.evaluate("() => frames.length")
    at = flip.evaluate("() => idx")
    flip.click("#strip .ghost-paste")
    flip.wait_for_timeout(300)
    check("paste inserts a page", flip.evaluate("() => frames.length") == n0 + 1,
          f"{n0} -> {flip.evaluate('() => frames.length')}")
    check("pasted page lands right after the current one",
          flip.evaluate("() => idx") == at + 1)

    # The clipboard must hand out independent copies, or editing one pasted page
    # silently edits every other paste of it.
    flip.click("#strip .ghost-paste")
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
    browsing.goto(pad, BASE, "/")
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
    print("\nTHUMBNAILS — cached on CONTENT, so a rebuild cannot show a stale page")
    # buildStrip() repaints every tile and runs on every insert, delete, reorder
    # and hold tap, so adding one page repainted all of them: measured 555ms on a
    # 31-page document, of which 510ms was thumbnails and 2.1ms was the DOM. The
    # cache removes that. What it must never do is show the artist a thumbnail of
    # a drawing they no longer have, which is why it is keyed on a content
    # signature rather than on a dirty flag somebody has to remember to set.
    _tc = flip.evaluate("""() => {
      const mk = (x) => { const pts = [];
        for (let k = 0; k < 40; k++) pts.push({ x: x + k * 4, y: 100 + (k % 7) * 9,
          color: '#ffffff', size: 6, t: k, erase: false, start: k === 0 });
        return { strokes: pts, strokeGroups: [pts.length], hold: 1 }; };
      frames.length = 0;
      for (let i = 0; i < 12; i++) frames.push(mk(40 + i * 10));
      idx = 0; if (typeof clearSpan === 'function') clearSpan(true);
      buildStrip();
      /* INK, not the data-URL's length. A 88x62 thumbnail of a single stroke is
         about 870 characters, so a "longer than 2,000" blank-check called every
         correct thumbnail empty -- and then the comparison it was guarding had
         nothing left to say. Counting lit pixels is independent of DPR and of
         how well PNG happened to compress. */
      /* BY CLASS, not by child index. The strip carries a trailing ghost "+"
         tile whose class is 'frame ghost-paste', so it matches .frame too and
         an index into either list is not an index into frames -- this read a
         NEIGHBOURING page, which had not changed, and called the cache stale. */
      const tile = i => strip.querySelectorAll('.frame:not(.ghost-paste)')[i].querySelector('canvas');
      const ink = cv => { const c = cv.getContext('2d');
        const d = c.getImageData(0, 0, cv.width, cv.height).data;
        let n = 0; for (let i = 3; i < d.length; i += 4) if (d[i] > 8) n++;
        return n; };
      const shot = i => tile(i).toDataURL();
      const before = shot(3), inkBefore = ink(tile(3));
      const sigBefore = (typeof _thumbSig === 'function') ? String(_thumbSig(frames[3])) : 'n/a';
      // EDITED IN PLACE, which is how every tool in this editor edits a page. A
      // cache keyed only on the frame object would hand back the old picture.
      frames[3].strokes.forEach(q => { q.y += 60; });
      buildStrip();
      const after = shot(3);
      // An untouched page must come back IDENTICAL -- the cache working, not
      // merely not breaking.
      const other = shot(5); buildStrip(); const otherAgain = shot(5);
      const sigAfter = (typeof _thumbSig === 'function') ? String(_thumbSig(frames[3])) : 'n/a';
      return { changed: before !== after, stable: other === otherAgain,
               ink: inkBefore, inkAfter: ink(tile(3)),
               sigMoved: sigBefore !== sigAfter, lens: [before.length, after.length],
               tiles: strip.children.length, nFrames: frames.length }; }""")
    check("a page edited in place gets a fresh thumbnail",
          _tc["changed"],
          f"tile unchanged after the edit — sig moved: {_tc['sigMoved']}, "
          f"ink {_tc['ink']} -> {_tc['inkAfter']}, url {_tc['lens']}, "
          f"{_tc['tiles']} tiles for {_tc['nFrames']} frames")
    check("...and an untouched page redraws identically",
          _tc["stable"], "the same page rebuilt to different pixels")
    check("...and the thumbnails were not blank to begin with",
          _tc["ink"] > 200,
          f"{_tc['ink']} lit pixels — comparing two empty canvases proves nothing")
    # THE SPEED IS THE POINT, AND A CLOCK IS THE WRONG WAY TO ASSERT IT.
    #
    # This was `cold > warm * 3` on wall-clock timings, with a wide margin
    # precisely because CLAUDE.md warns these are noisy under load. The margin
    # was not the problem: the ASSERTION was. It passed every local run and
    # every sqlite CI job, and failed the PostgreSQL job twice on trees whose
    # own sqlite job passed -- that job's database logged 105s and 160s
    # checkpoints mid-run, which is the contention CLAUDE.md documents. A pin
    # that goes red only when the box is busy reports on the box, not the tree,
    # and CANNOT tell the two apart. That makes it useless in both directions:
    # it cried wolf twice, and it would have said nothing if the cache broke on
    # a quiet machine.
    #
    # So this asserts the MECHANISM instead, which is what "repainted only when
    # its page changes" actually means and is exactly as strong on an idle box
    # as on a loaded one. drawThumb stores a NEW entry object every time it
    # repaints, so entry identity is the record of whether a repaint happened:
    #
    #   cold  -- every frame has an entry, and the cache has taken bytes
    #   warm  -- every entry is the SAME OBJECT, and no bytes were added
    #   edit  -- the edited frame's entry is a NEW object, its neighbours' are not
    #
    # No clock, no threshold, no margin to tune.
    _tm = flip.evaluate("""() => {
      const mk = (x) => { const pts = [];
        for (let k = 0; k < 600; k++) pts.push({ x: x + (k % 80) * 9, y: 60 + (k / 80 | 0) * 30,
          color: '#ffffff', size: 5, t: k, erase: false, start: k % 80 === 0 });
        return { strokes: pts, strokeGroups: Array.from({length: 8}, () => 75), hold: 1 }; };
      frames.length = 0;
      for (let i = 0; i < 24; i++) frames.push(mk(30 + i * 3));
      idx = 0;
      const entries = () => frames.map(f => _thumbCache.get(f));
      buildStrip();
      const cold = entries(), coldBytes = _thumbBytes;
      buildStrip();
      const warm = entries(), warmBytes = _thumbBytes;
      // Edit ONE page, well away from index 0, and rebuild.
      const EDIT = 9;
      frames[EDIT].strokes.forEach(q => { q.x += 40; });
      buildStrip();
      const after = entries();
      return {
        n: frames.length,
        cachedCold: cold.filter(Boolean).length,
        coldBytes, warmBytes,
        // Identity, not equality: a repaint replaces the object.
        heldOnWarm: warm.filter((e, i) => e && e === cold[i]).length,
        editedIsNew: !!after[EDIT] && after[EDIT] !== warm[EDIT],
        neighboursHeld: after.filter((e, i) => i !== EDIT && e && e === warm[i]).length,
      }; }""")
    # THE PASTE GHOST SHIFTS EVERY TILE AFTER THE CURRENT PAGE. It is appended
    # inside the page loop, right after `idx`, so strip.children stops lining up
    # with frames the moment the clipboard holds anything — and refreshThumb(i)
    # indexed children directly, repainting frames[i] into frames[i-1]'s tile.
    # Latent until now because buildStrip repaints everything and runs after most
    # things; with thumbnails cached, a tile painted from the wrong page STAYS
    # wrong. Found because the cache's own test read the wrong tile for the same
    # reason.
    _gh = flip.evaluate("""() => {
      const mk = (x) => { const pts = [];
        for (let k = 0; k < 30; k++) pts.push({ x: x + k * 5, y: 120 + (k % 5) * 14,
          color: '#ffffff', size: 7, t: k, erase: false, start: k === 0 });
        return { strokes: pts, strokeGroups: [pts.length], hold: 1 }; };
      frames.length = 0;
      for (let i = 0; i < 6; i++) frames.push(mk(60 + i * 90));
      idx = 0;
      // A copied page puts the ghost on the strip, between page 0 and page 1.
      pageClip = [JSON.parse(JSON.stringify(frames[0]))];
      buildStrip();
      const tiles = () => strip.querySelectorAll('.frame:not(.ghost-paste)');
      const ink = i => { const cv = tiles()[i].querySelector('canvas');
        const d = cv.getContext('2d').getImageData(0,0,cv.width,cv.height).data;
        let n = 0; for (let j = 3; j < d.length; j += 4) if (d[j] > 8) n++;
        return n; };
      const shot = i => tiles()[i].querySelector('canvas').toDataURL();
      const hadGhost = strip.querySelectorAll('.ghost-paste').length === 1;
      // Edit page 4 — well past the ghost — and refresh only that tile.
      const before4 = shot(4), before3 = shot(3);
      frames[4].strokes.forEach(q => { q.x += 120; });
      refreshThumb(4);
      const r = { hadGhost, ink4: ink(4),
                  four: shot(4) !== before4, three: shot(3) !== before3 };
      pageClip = null;
      return r; }""")
    check("the strip carries a paste ghost when the clipboard has pages",
          _gh["hadGhost"], "no ghost — this check is not exercising the shift")
    check("...and refreshing a page past it repaints THAT page's tile",
          _gh["four"] and _gh["ink4"] > 100,
          f"tile 4 unchanged after editing page 4 ({_gh['ink4']} lit pixels) — "
          f"the refresh landed on a different tile")
    check("...and leaves its neighbour alone",
          not _gh["three"],
          "editing page 4 repainted page 3's tile — the index is off by the ghost")

    check("a cold rebuild caches every page's thumbnail",
          _tm and _tm["cachedCold"] == _tm["n"] and _tm["coldBytes"] > 0,
          f"{_tm and _tm['cachedCold']}/{_tm and _tm['n']} pages cached, "
          f"{_tm and _tm['coldBytes']} bytes held — with nothing cached there is "
          f"nothing for the rebuild below to reuse")
    check("rebuilding a strip nobody changed does not repaint it",
          _tm and _tm["heldOnWarm"] == _tm["n"] and _tm["warmBytes"] == _tm["coldBytes"],
          f"{_tm and _tm['heldOnWarm']}/{_tm and _tm['n']} thumbnails survived the "
          f"rebuild as the same entry ({_tm and _tm['coldBytes']} -> "
          f"{_tm and _tm['warmBytes']} bytes) — a replaced entry is a repaint")
    check("...but the page that CHANGED is repainted, and only that one",
          _tm and _tm["editedIsNew"] and _tm["neighboursHeld"] == _tm["n"] - 1,
          f"edited page repainted: {_tm and _tm['editedIsNew']}; "
          f"{_tm and _tm['neighboursHeld']}/{_tm and _tm['n'] - 1} neighbours left "
          f"alone — a cache that never notices an edit shows a drawing nobody has")

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
    sp.evaluate("() => { try { localStorage.setItem('skribl_hints_seen_v1',"
                " JSON.stringify({'flip-intro':1})); } catch(e){} "
                "const h=document.querySelector('.skribl-hint'); if(h){h.classList.remove('in');h.hidden=true;} }")

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

    # ------------------------------------------------------------------
    # v237 — the add controls are reachable from any page.
    #
    # Duplicate / Blank / In-between / Paste all act on the page you are ON:
    # addFrame() and addTween() both splice at idx+1. They used to be the last
    # child of the strip, which scrolls, so on a long flip you had to scroll to
    # the far end to insert after page 2. They now sit ABOVE the strip, outside
    # the scrolling box entirely.
    #
    # The first check here is the anti-vacuity one: on a strip that does not
    # overflow, every tile and every button is trivially "visible" and the rest
    # of this block would pass with the fix removed.
    # ------------------------------------------------------------------
    ac = br.new_page(viewport={"width": 393, "height": 820})
    ac_errs = []
    ac.on("pageerror", lambda e: ac_errs.append(str(e)))
    browsing.goto(ac, BASE, "/flip")
    ac.evaluate("() => { for (let i = 0; i < 14; i++) addFrame(false); go(1); }")
    ac.wait_for_timeout(400)
    ac.evaluate("() => { strip.scrollLeft = 0; }")
    ac.wait_for_timeout(200)

    PROBE = """() => {
      const s = strip, sr = s.getBoundingClientRect();
      const col = document.querySelector('.addcol');
      const seen = {}, names = {};
      for (const id of ['addcopy', 'addblank', 'addtween']) {
        const el = document.getElementById(id);
        const r = el && el.getBoundingClientRect();
        // A hit test, not a bounding-box guess: a button scrolled off the end
        // of the strip still reports left >= 0, so "is it on screen" has to
        // mean "does a click at its centre actually land on it".
        let hit = false;
        if (r && r.width > 4 && r.height > 4
            && r.right <= innerWidth && r.bottom <= innerHeight
            && r.left >= 0 && r.top >= 0) {
          const t = document.elementFromPoint((r.left + r.right) / 2,
                                              (r.top + r.bottom) / 2);
          hit = !!(t && (t === el || el.contains(t)));
        }
        seen[id] = hit;
        // The RENDERED name, not the source that produces it. flip.js carries
        // paragraphs explaining why this button is no longer called the
        // in-between, and a substring search over the file would read the
        // explanation as the thing it is looking for (CLAUDE.md, three times).
        // What a user reads is the label plus the tooltip, so that is what is
        // collected here.
        names[id] = ((el ? el.textContent : '') + ' ' + (el ? el.title : ''))
                      .replace(/\\s+/g, ' ').trim();
      }
      return { seen, names, inStrip: s.contains(col),
               overflows: s.scrollWidth > s.clientWidth + 8,
               scrollLeft: Math.round(s.scrollLeft),
               cols: document.querySelectorAll('.addcol').length }; }"""

    left = ac.evaluate(PROBE)
    check("the strip overflows, so reachability is a real question",
          left["overflows"],
          "strip fits on screen — the rest of this block would be vacuous")
    check("the add controls are NOT inside the scrolling strip",
          not left["inStrip"],
          "they are a child of the box that scrolls, so they scroll with it")
    for _id, _label in (("addcopy", "Duplicate"), ("addblank", "Blank"),
                        ("addtween", "Motion Smear")):
        check(f"{_label} is on screen while page 2 is being edited",
              left["seen"][_id], "the button is not visible")
        check(f"and it is the control that says {_label}",
              _label.lower() in left["names"][_id].lower(),
              f"reads {left['names'][_id]!r}")

    # THE NAME WAS THE PROMISE. This effect integrates the whole path
    # between two poses; "in-between" is an animator's word for one intermediate
    # POSE, which it has never produced. The label was the only thing that said
    # otherwise, so nothing a user can read on these controls may say it again --
    # and the real In-between, when it exists, is a different button.
    for _id in ("addcopy", "addblank", "addtween"):
        check(f"nothing a user reads on {_id} calls it an in-between",
              "in-between" not in left["names"][_id].lower(),
              f"reads {left['names'][_id]!r}")

    # Scroll position must be irrelevant now — that is the whole point.
    ac.evaluate("() => { strip.scrollLeft = strip.scrollWidth; }")
    ac.wait_for_timeout(200)
    right = ac.evaluate(PROBE)
    check("and still on screen at the far end of the strip",
          all(right["seen"].values()), str(right["seen"]))

    # buildStrip() empties `strip`, which used to remove the old column for
    # free. Outside the strip it has to be removed by hand, so rebuilding the
    # strip repeatedly is exactly how a duplicate would pile up.
    ac.evaluate("() => { for (let i = 0; i < 4; i++) buildStrip(); }")
    ac.wait_for_timeout(300)
    _cols = ac.evaluate("() => document.querySelectorAll('.addcol').length")
    check("rebuilding the strip does not leave a second set of controls behind",
          _cols == 1, f"{_cols} copies of the control row")

    # The row must not clip its labels at any supported width; below ~360px it
    # is allowed to wrap to a second line, but never to hide a control.
    for w in (320, 360, 393, 700, 1280):
        ac.set_viewport_size({"width": w, "height": 820})
        ac.wait_for_timeout(250)
        fit = ac.evaluate("""() => {
          const out = [];
          for (const id of ['addcopy', 'addblank', 'addtween']) {
            const el = document.getElementById(id);
            if (!el) continue;
            out.push({ id: id, clipped: el.scrollWidth > el.clientWidth + 1,
                       w: Math.round(el.getBoundingClientRect().width) });
          }
          return out; }""")
        check(f"no control is clipped at {w}px",
              all(not f["clipped"] for f in fit),
              ", ".join(f"{f['id']} {f['w']}px" for f in fit if f["clipped"]))
    ac.set_viewport_size({"width": 393, "height": 820})
    ac.wait_for_timeout(250)

    # ------------------------------------------------------------------
    # v295 — THE STRIP SCROLLS THE WAY A REORDER DRAGS.
    #
    # Reported from a phone: the thumbnails "move super easy, so if you are
    # trying to scroll the strip you might move one of the slides out of order",
    # and tapping one to change pages often did nothing. Both halves are the
    # same cause — a reorder began after SIX pixels of travel, below every
    # platform's touch slop, so a scroll flick was a reorder and a tap that
    # drifted set _pdragSuppressClick and never selected.
    #
    # A threshold alone cannot fix it: any scroll long enough passes any
    # threshold. So the strip itself decides — if its scrollLeft moved while the
    # finger was down, that finger was scrolling and no reorder begins however
    # far the drag goes. These three assertions are the three gestures.
    # ------------------------------------------------------------------
    ac.evaluate("() => { go(0); strip.scrollLeft = 0; "
                "        frames.forEach((f, i) => { f.__tag = i; }); }")
    ac.wait_for_timeout(150)
    tags = "() => frames.map(f => f.__tag).join(',')"
    before = ac.evaluate(tags)

    def tile_box(i):
        return ac.evaluate("""(i) => { const t = strip.querySelectorAll('.frame:not(.ghost-paste)')[i];
            const r = t.getBoundingClientRect();
            return { x: r.left + r.width / 2, y: r.top + r.height / 2 }; }""", i)

    # 1. A SCROLL WINS. Finger down on a tile, the strip scrolls under it, then
    #    the finger travels far enough that the old six-pixel rule would long
    #    since have committed to a reorder.
    b0 = tile_box(0)
    ac.mouse.move(b0["x"], b0["y"]); ac.mouse.down()
    ac.evaluate("() => { strip.scrollLeft = strip.scrollLeft + 40; }")
    ac.mouse.move(b0["x"] + 120, b0["y"], steps=6)
    ac.mouse.up()
    ac.wait_for_timeout(200)
    check("scrolling the strip does not reorder a page",
          ac.evaluate(tags) == before,
          f"{before} became {ac.evaluate(tags)} — the strip scrolled under the "
          f"finger and a page moved anyway")

    # 2. A TAP THAT DRIFTS STILL SELECTS. The other half of the same report.
    ac.evaluate("() => { go(0); strip.scrollLeft = 0; }")
    ac.wait_for_timeout(150)
    b2 = tile_box(2)
    ac.mouse.move(b2["x"], b2["y"]); ac.mouse.down()
    ac.mouse.move(b2["x"] + 9, b2["y"], steps=3)     # inside the slop, over the old 6
    ac.mouse.up()
    ac.wait_for_timeout(250)
    check("a tap that drifts a few pixels still changes page",
          ac.evaluate("() => idx") == 2,
          f"idx is {ac.evaluate('() => idx')} — a drifting tap used to suppress "
          f"its own click and leave you on the page you started from")

    # 3. A DRAG WITHOUT THE HOLD DOES NOTHING — that is the scroll case, and
    #    ignoring it is the entire point.
    #
    #    CALIBRATION, because this one is not held by the mechanism it reads
    #    like. Arming instantly leaves it GREEN: a flick's first pointermove
    #    already exceeds STRIP_JITTER, so the disarm branch kills the drag
    #    before the timer can matter. It is the DISARM this pins, not the hold
    #    length, and it goes red only on the gesture actually reported from the
    #    phone — arm on contact AND never disarm, which is v294. Under that
    #    pair, 1, 2 and 3 all go red together and 4 stays green.
    ac.evaluate("() => { go(0); strip.scrollLeft = 0; }")
    ac.wait_for_timeout(150)
    b0 = tile_box(0); b3 = tile_box(3)
    ac.mouse.move(b0["x"], b0["y"]); ac.mouse.down()
    ac.mouse.move(b3["x"], b3["y"], steps=10)
    ac.mouse.up()
    ac.wait_for_timeout(250)
    check("a drag with no hold first does not reorder",
          ac.evaluate(tags) == before,
          f"{before} became {ac.evaluate(tags)} — a flick across the strip is a "
          f"scroll, and it moved a page")

    # 4. AND A HOLD THEN A DRAG STILL REORDERS, which is the assertion that
    #    stops the three above from being satisfied by breaking reordering.
    ac.evaluate("() => { go(0); strip.scrollLeft = 0; }")
    ac.wait_for_timeout(150)
    b0 = tile_box(0); b3 = tile_box(3)
    ac.mouse.move(b0["x"], b0["y"]); ac.mouse.down()
    ac.wait_for_timeout(550)                 # past the ~400 ms arm
    ac.mouse.move(b3["x"], b3["y"], steps=10)
    ac.mouse.up()
    ac.wait_for_timeout(250)
    check("but a hold and THEN a drag reorders",
          ac.evaluate(tags) != before,
          f"order is still {before} — the fix cannot be 'reordering never "
          f"happens'")

    # 5. SELECTING A RANGE HAS A HOME, and it is not a gesture any more. The
    #    sweep that used to do this shared the strip's scroll direction; it now
    #    sits in a page's own popover beside Move and Copy, which already speak
    #    in spans.
    _ops = ac.evaluate(
        "() => { const t = strip.querySelectorAll('.frame')[3];"
        "        const o = t && t.querySelector('.pageops');"
        "        if (!o) return null;"
        "        o.click();"
        "        return [...document.querySelectorAll('.popmenu button, .pageops-menu button,"
        "                 .pop button, .popover button')].map(b => b.textContent.trim()); }")
    ac.wait_for_timeout(250)
    check("a page's own menu offers to select through it",
          bool(_ops) and any("through here" in l.lower() for l in (_ops or [])),
          f"{_ops} — the sweep gesture is gone, so this is the only way left on "
          f"a touch screen to take a run of pages")

    # The reason reachability matters: the control inserts NEXT TO the page you
    # are on, not at the end. If it appended, scrolling to the end would be the
    # honest interaction and there would be nothing to fix.
    ac.evaluate("() => { go(1); }")
    ac.wait_for_timeout(200)
    before = ac.evaluate("() => frames.length")
    ac.evaluate("() => { document.getElementById('addblank').click(); }")
    ac.wait_for_timeout(400)
    after = ac.evaluate("() => ({ n: frames.length, idx: idx })")
    check("Blank inserts after the current page, not at the end",
          after["n"] == before + 1 and after["idx"] == 2,
          f"length {before} -> {after['n']}, idx now {after['idx']}")
    check("no JS errors while using the add controls", not ac_errs,
          "; ".join(ac_errs[:2]))
    ac.close()

    br.close()

ok = sum(1 for o, _ in results if o)
print("\n" + "=" * 60)
print(f"{ok}/{len(results)} passed")
for o, n in results:
    if not o:
        print(f"  FAILED: {n}")
raise SystemExit(0 if ok == len(results) else 1)
