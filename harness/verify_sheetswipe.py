#!/usr/bin/env python3
"""verify_sheetswipe: every menu goes away, and a swipe on one never reloads the page (v317).

The owner, on a phone: "menus should always go down or away easily. Some of
these menus, I hit the drawer grip and they stay, I swipe it down and
accidentally reload the page."

Driven on a phone-sized touch screen, per surface, per page -- the Pad's and
Flip's copies of the shared export sheet are two instances (WORKING-AGREEMENTS:
a population that spans routes carries the route in its identity):

  1  THE GRABBER, tapped, closes the sheet (the page menu's did nothing).
  2  A SWIPE DOWN from the sheet's top follows the finger and closes it, and the
     touch is the sheet's: the move is cancelled (preventDefault), which is
     what keeps the page from scrolling under it and the browser from
     starting a pull-to-refresh.
  3  A SHORT, SLOW pull is not a dismissal: the sheet stays and settles back.
  4  WHILE OPEN the page does not pull to refresh (html overscroll-behavior-y
     is none); CLOSED it is the page it always was (auto).
  5  THE DRAW DRAWER'S GRIP, tapped, closes the drawer (it toggled half and
     full, and on a phone that read as a drawer that would not go away).
  6  IT EASES AWAY (the owner: "when those menus close shouldn't they ease
     closed?"). Sampled part-way through, a closing sheet is still on screen
     and lower than it was -- by the grabber, and from where a swipe left it --
     and it is gone once the slide is over. Four of these vanished before.
     With reduced motion it goes at once.
"""
import os
import sys

from assertions import make_check
import browsing
import waits

try:
    from playwright.sync_api import sync_playwright
except Exception as exc:                                   # pragma: no cover
    print(f"SUITE-SKIPPED: playwright unavailable ({exc})")
    raise SystemExit(77)

BASE = os.environ.get("SKRIBL_BASE", "http://127.0.0.1:5001")
results = []
check = make_check(results)

TOUCH = """([sel, type, x, y]) => {
  const el = document.querySelector(sel);
  const t = new Touch({identifier: 7, target: el, clientX: x, clientY: y});
  const empty = (type === 'touchend' || type === 'touchcancel');
  const ev = new TouchEvent(type, {touches: empty ? [] : [t], targetTouches: empty ? [] : [t],
    changedTouches: [t], bubbles: true, cancelable: true, view: window});
  el.dispatchEvent(ev);
  return ev.defaultPrevented;
}"""

OVERSCROLL = "() => getComputedStyle(document.documentElement).overscrollBehaviorY"

# Part-way through a close, sampled IN THE PAGE (no Python round trip between
# the act and the look, so a loaded machine cannot sample after the hide), and
# by PAINT: what elementFromPoint finds just inside the sheet's top edge. A
# leaving sheet takes no taps (pointer-events: none), which elementFromPoint
# honours, so the probe lends it pointer-events for the one call.
MID = """async ([sel, act, grab, x, y, ms]) => {
  const s = document.querySelector(sel);
  const top0 = s.getBoundingClientRect().top;
  if (act === 'grab') document.querySelector(grab).click();
  else {
    const t = new Touch({identifier: 7, target: s, clientX: x, clientY: y});
    s.dispatchEvent(new TouchEvent('touchend', {touches: [], targetTouches: [], changedTouches: [t],
      bubbles: true, cancelable: true, view: window}));
  }
  await new Promise(r => setTimeout(r, ms));
  const r = s.getBoundingClientRect();
  const pe = s.style.pointerEvents; s.style.pointerEvents = 'auto';
  const hit = document.elementFromPoint(r.left + r.width / 2, Math.min(innerHeight - 2, r.top + 12));
  s.style.pointerEvents = pe;
  return { top0, top: r.top, painted: !!(hit && (hit === s || s.contains(hit))),
           laidOut: s.getClientRects().length > 0, offBottom: r.top >= innerHeight };
}"""
# 130 ms: past the slow start of the spring curve the self-animating sheets
# use (0.35 s), and well before a slideOut's 220 ms hide.
EASE_MS = 130
# A flick: 45px in three quick moves, then let go -- under the 80px line, so
# only the speed can close it.
FLICK = """async ([sel, x, y]) => {
  const s = document.querySelector(sel);
  const fire = (type, yy) => { const t = new Touch({identifier: 7, target: s, clientX: x, clientY: yy});
    const empty = type === 'touchend';
    s.dispatchEvent(new TouchEvent(type, {touches: empty ? [] : [t], targetTouches: empty ? [] : [t],
      changedTouches: [t], bubbles: true, cancelable: true, view: window})); };
  fire('touchstart', y);
  for (const d of [15, 30, 45]) { await new Promise(r => setTimeout(r, 6)); fire('touchmove', y + d); }
  fire('touchend', y + 45);
}"""

# (page, name, route, how to open it, the sheet, is it closed?, its grabber)
SHEETS = [
    ("Pad", "the ⋯ menu", "/skribl-pad", "() => document.getElementById('menuBtn').click()",
     "#menuSheet", "() => document.getElementById('menuOverlay').hidden", "#menuSheet .menu-handle"),
    ("Pad", "the export sheet", "/skribl-pad",
     "() => { document.getElementById('menuBtn').click(); document.getElementById('exportItem').click(); }",
     "#exportSheet", "() => !document.getElementById('exportOverlay').classList.contains('open')",
     "#exportSheet .menu-handle"),
    ("Pad", "the report sheet", "/skribl-pad",
     "() => { document.getElementById('menuBtn').click(); document.getElementById('reportItem').click(); }",
     "#reportSheet", "() => document.getElementById('reportOverlay').hidden", None),
    ("Pad", "your drafts", "/skribl-pad", "() => window.SkriblSavedDrafts.open()",
     "#savedDraftsSheet", "() => { const s = document.getElementById('savedDraftsSheet'); return !s || s.hidden; }", "#savedDraftsSheet .sdrafts-grab"),
    ("Flip", "the ⋯ menu", "/flip", "() => document.getElementById('moreBtn').click()",
     "#moreMenu", "() => document.getElementById('moreMenu').hidden", "#moreMenu .menu-handle"),
    ("Flip", "the export sheet", "/flip",
     "() => { document.getElementById('moreBtn').click(); document.getElementById('miExport').click(); }",
     "#exportSheet", "() => !document.getElementById('exportOverlay').classList.contains('open')",
     "#exportSheet .menu-handle"),
    ("Flip", "your drafts", "/flip", "() => window.SkriblSavedDrafts.open()",
     "#savedDraftsSheet", "() => { const s = document.getElementById('savedDraftsSheet'); return !s || s.hidden; }", "#savedDraftsSheet .sdrafts-grab"),
    ("Library", "the page menu", "/library", "() => document.getElementById('pageMenuBtn').click()",
     "#pageMenu", "() => document.getElementById('pageMenuOverlay').hidden", "#pageMenu .pm-grab"),
    # Every sheet attached, on every route it is attached on (third review:
    # these three were attached and never driven).
    ("Pad", "the post sheet", "/skribl-pad",
     "() => { const b = document.getElementById('postBtn'); b.disabled = false; b.click(); }",
     "#postSheet", "() => document.getElementById('postOverlay').hidden", "#postSheet .menu-handle"),
    ("Flip", "the report sheet", "/flip",
     "() => { document.getElementById('moreBtn').click(); document.getElementById('miReport').click(); }",
     "#reportSheet", "() => document.getElementById('reportOverlay').hidden", None),
    # The Pad's post sheet, on Flip since Flip posts through it (owner:
    # "shouldn't flip and pad look the same?"). Flip will not open it on an
    # empty page, so the opener gives the page a stroke first, and lets the
    # editor wake Post for it as a drawn stroke does.
    ("Flip", "the post sheet", "/flip",
     "() => { frames[0].strokes.push({x:40,y:40,color:'#ffffff',size:6,t:1,start:true},"
     "{x:120,y:90,color:'#ffffff',size:6,t:2}); frames[0].strokeGroups.push(2); render(); updateToolState();"
     " document.getElementById('postBtn').click(); }",
     "#postSheet", "() => document.getElementById('postOverlay').hidden", "#postSheet .menu-handle"),
    ("Gallery", "the page menu", "/gallery", "() => document.getElementById('pageMenuBtn').click()",
     "#pageMenu", "() => document.getElementById('pageMenuOverlay').hidden", "#pageMenu .pm-grab"),
]

def fresh(b, route, height=664):
    ctx = b.new_context(viewport={"width": 390, "height": height}, has_touch=True, is_mobile=True,
                        device_scale_factor=2)
    pg = ctx.new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    browsing.goto(pg, BASE, route)
    waits.settle(pg, 900)
    pg.evaluate("() => { window.SkriblHints && window.SkriblHints.hide(); }")
    return ctx, pg, errs


def open_sheet(pg, how, closed):
    # Only when shut: some openers toggle, and a mutated grabber leaves it open.
    if pg.evaluate(closed):
        pg.evaluate(how)
        waits.settle(pg, 500)
    return not pg.evaluate(closed)


def top_point(pg, sel):
    r = pg.locator(sel).bounding_box()
    return r["x"] + r["width"] / 2, r["y"] + 20


with sync_playwright() as p:
    b = waits.instrument(p.chromium.launch())
    for page, name, route, how, sel, closed, grab in SHEETS:
        who = f"{page}: {name}"
        print(f"\n{who}")
        ctx, pg, errs = fresh(b, route)
        before = pg.evaluate(OVERSCROLL)

        check(f"{who} opens", open_sheet(pg, how, closed))
        check(f"{who}: open, the page does not pull to refresh",
              pg.evaluate(OVERSCROLL) == "none", f"overscroll-behavior-y = {pg.evaluate(OVERSCROLL)!r}")

        # 1 the grabber
        if grab:
            mid = pg.evaluate(MID, [sel, "grab", grab, 0, 0, EASE_MS])
            pg.wait_for_timeout(450)
            check(f"{who}: tapping the grabber eases it down rather than snapping it away",
                  mid["painted"] and mid["top"] > mid["top0"] + 10,
                  f"{EASE_MS}ms in: painted={mid['painted']}, top {round(mid['top0'])} -> {round(mid['top'])}")
            check(f"{who}: tapping the grabber closes it", pg.evaluate(closed) is True)
            check(f"{who}: closed, the page is the page it was (overscroll {before!r})",
                  pg.evaluate(OVERSCROLL) == before, f"now {pg.evaluate(OVERSCROLL)!r}")
            open_sheet(pg, how, closed)

        # 3 a short, slow pull stays
        x, y = top_point(pg, sel)
        pg.evaluate(TOUCH, [sel, "touchstart", x, y]); pg.wait_for_timeout(110)
        pg.evaluate(TOUCH, [sel, "touchmove", x, y + 15]); pg.wait_for_timeout(110)
        pg.evaluate(TOUCH, [sel, "touchmove", x, y + 30]); pg.wait_for_timeout(110)
        pg.evaluate(TOUCH, [sel, "touchend", x, y + 30]); pg.wait_for_timeout(450)
        check(f"{who}: a short slow pull leaves it open, settled back",
              pg.evaluate(closed) is False and pg.evaluate(f"() => document.querySelector('{sel}').style.transform") == "",
              f"closed={pg.evaluate(closed)}")

        # 2b the first pixels, and a sideways drag
        # A real phone decides between page scroll / pull-to-refresh and the
        # page's own handling on the FIRST move; a move left uncancelled there
        # makes every later one uncancellable. Synthetic events are always
        # cancellable, so what is asserted is that the first 3px is claimed.
        pg.evaluate(TOUCH, [sel, "touchstart", x, y])
        first = pg.evaluate(TOUCH, [sel, "touchmove", x, y + 3])
        pg.evaluate(TOUCH, [sel, "touchend", x, y + 3]); pg.wait_for_timeout(60)
        check(f"{who}: the first 3px of a pull down is the sheet's already (the page never starts a reload)",
              first is True, f"defaultPrevented={first}")
        pg.evaluate(TOUCH, [sel, "touchstart", x - 60, y])
        side1 = pg.evaluate(TOUCH, [sel, "touchmove", x - 30, y + 8])
        side2 = pg.evaluate(TOUCH, [sel, "touchmove", x + 60, y + 24])
        moved = pg.evaluate(f"() => document.querySelector('{sel}').style.transform")
        pg.evaluate(TOUCH, [sel, "touchend", x + 60, y + 24]); pg.wait_for_timeout(300)
        check(f"{who}: a mostly sideways drag that drifts down is left alone (not dragged, not cancelled, not closed)",
              not side2 and not moved and pg.evaluate(closed) is False,
              f"cancelled={side1},{side2} transform={moved!r} closed={pg.evaluate(closed)}")

        # 2 the swipe
        pg.evaluate(TOUCH, [sel, "touchstart", x, y]); pg.wait_for_timeout(30)
        pg.evaluate(TOUCH, [sel, "touchmove", x, y + 40]); pg.wait_for_timeout(30)
        taken = pg.evaluate(TOUCH, [sel, "touchmove", x, y + 140])
        follows = pg.evaluate(f"() => document.querySelector('{sel}').style.transform")
        mid = pg.evaluate(MID, [sel, "end", None, x, y + 140, EASE_MS])
        pg.wait_for_timeout(450)
        # Still laid out and lower: on screen and painted, or a short sheet
        # already carried off the bottom edge -- never snapped away in place.
        check(f"{who}: let go past the line, it carries on down from the finger (no jump back, no vanish)",
              mid["laidOut"] and mid["top"] > mid["top0"] + 5 and (mid["painted"] or mid["offBottom"]),
              f"{EASE_MS}ms after release: painted={mid['painted']}, top {round(mid['top0'])} -> {round(mid['top'])}")
        check(f"{who}: a swipe down follows the finger", "translateY(140px)" in (follows or ""), repr(follows))
        check(f"{who}: ...and the touch is the sheet's, not the page's (the move is cancelled: no scroll, no reload)",
              taken is True, f"defaultPrevented={taken}")
        check(f"{who}: ...and it closes", pg.evaluate(closed) is True)
        # The flick: short of the line, closed by its speed alone.
        if open_sheet(pg, how, closed):
            fx, fy = top_point(pg, sel)
            pg.evaluate(FLICK, [sel, fx, fy]); pg.wait_for_timeout(450)
            check(f"{who}: a quick flick short of the line still closes it", pg.evaluate(closed) is True, "")
        else:
            check(f"{who}: reopens for the flick", False, "")
        check(f"{who}: no page errors", not errs, "; ".join(errs[:2]))
        ctx.close()

    # 6 reduced motion: no slide, gone at once
    print("\nreduced motion")
    rctx = b.new_context(viewport={"width": 390, "height": 664}, has_touch=True, is_mobile=True,
                         reduced_motion="reduce")
    rpg = rctx.new_page()
    browsing.goto(rpg, BASE, "/flip"); rpg.wait_for_timeout(900)
    rpg.evaluate("() => document.getElementById('moreBtn').click()"); rpg.wait_for_timeout(500)
    ropen = rpg.evaluate("() => !document.getElementById('moreMenu').hidden")
    rpg.evaluate("() => document.querySelector('#moreMenu .menu-handle').click()"); rpg.wait_for_timeout(30)
    check("with reduced motion, Flip's menu closes at once rather than sliding",
          ropen is True and rpg.evaluate("() => document.getElementById('moreMenu').hidden") is True,
          f"opened first: {ropen}")
    rctx.close()

    # 7 the edges a finger finds (v317 review)
    print("\nedges")
    TWO = """([sel, x, y]) => { const el = document.querySelector(sel);
      const t1 = new Touch({identifier: 7, target: el, clientX: x, clientY: y});
      const t2 = new Touch({identifier: 8, target: el, clientX: x + 40, clientY: y});
      el.dispatchEvent(new TouchEvent('touchstart', {touches: [t1, t2], targetTouches: [t1, t2],
        changedTouches: [t2], bubbles: true, cancelable: true, view: window})); }"""
    ctx, pg, errs = fresh(b, "/skribl-pad")
    open_sheet(pg, "() => document.getElementById('menuBtn').click()", "() => document.getElementById('menuOverlay').hidden")
    x, y = top_point(pg, "#menuSheet")
    pg.evaluate(TOUCH, ["#menuSheet", "touchstart", x, y]); pg.evaluate(TOUCH, ["#menuSheet", "touchmove", x, y + 60])
    was = pg.evaluate("() => document.getElementById('menuSheet').style.transform")
    pg.evaluate(TWO, ["#menuSheet", x, y + 60]); pg.wait_for_timeout(60)
    check("a second finger mid-drag puts the sheet back (it was left stuck part-way down)",
          "translateY(60px)" in (was or "")
          and pg.evaluate("() => document.getElementById('menuSheet').style.transform") == "", f"dragging first: {was!r}")
    # A quick pull, a pause, a lift: put it back, not a flick.
    pg.evaluate(TOUCH, ["#menuSheet", "touchstart", x, y])
    for k in range(1, 5):
        pg.evaluate(TOUCH, ["#menuSheet", "touchmove", x, y + k * 12])
    pg.wait_for_timeout(250)
    pg.evaluate(TOUCH, ["#menuSheet", "touchend", x, y + 48]); pg.wait_for_timeout(450)
    check("pull, pause, let go is 'put it back', not a flick",
          pg.evaluate("() => document.getElementById('menuOverlay').hidden") is False, "")
    # Scrolled down, a pull on the first rows scrolls back up instead of closing.
    # The menu fits a 664px phone since its tiles (after v323), so this is a
    # short window's: 480 tall, where it still scrolls.
    ctx.close()
    ctx, pg, errs = fresh(b, "/skribl-pad", height=480)
    open_sheet(pg, "() => document.getElementById('menuBtn').click()", "() => document.getElementById('menuOverlay').hidden")
    x, y = top_point(pg, "#menuSheet")
    can = pg.evaluate("() => { const s = document.getElementById('menuSheet'); s.scrollTop = 120; return s.scrollTop; }")
    pg.evaluate(TOUCH, ["#menuSheet", "touchstart", x, y])
    first = pg.evaluate(TOUCH, ["#menuSheet", "touchmove", x, y + 3])
    pg.evaluate(TOUCH, ["#menuSheet", "touchmove", x, y + 120])
    moved = pg.evaluate("() => document.getElementById('menuSheet').style.transform")
    pg.evaluate(TOUCH, ["#menuSheet", "touchend", x, y + 120]); pg.wait_for_timeout(450)
    check("in a menu scrolled down, a pull on its top rows is a scroll, not a dismiss",
          can > 0 and first is False and not moved
          and pg.evaluate("() => document.getElementById('menuOverlay').hidden") is False,
          f"scrollTop={can} claimed={first} transform={moved!r}")
    ctx.close()
    # A pull during the entrance is the sheet's too (it used to scroll the page).
    ctx, pg, errs = fresh(b, "/flip")
    pg.evaluate("() => document.getElementById('moreBtn').click()"); pg.wait_for_timeout(40)
    ent = pg.evaluate("""() => { const m = document.getElementById('moreMenu');
        return { running: m.getAnimations().some(a => a.playState === 'running'), sheet: SkriblSheetSwipe.isBottomSheet(m) }; }""")
    xe, ye = top_point(pg, "#moreMenu")
    pg.evaluate(TOUCH, ["#moreMenu", "touchstart", xe, ye])
    early = pg.evaluate(TOUCH, ["#moreMenu", "touchmove", xe, ye + 3])
    pg.evaluate(TOUCH, ["#moreMenu", "touchend", xe, ye + 3])
    check("a pull while the sheet is still rising is the sheet's (claimed), not the page's",
          ent["running"] and ent["sheet"] and early is True, f"{ent} claimed={early}")
    ctx.close()
    # A leaving sheet takes no taps.
    ctx, pg, errs = fresh(b, "/flip")
    open_sheet(pg, "() => document.getElementById('moreBtn').click()", "() => document.getElementById('moreMenu').hidden")
    pg.evaluate("() => document.querySelector('#moreMenu .menu-handle').click()"); pg.wait_for_timeout(60)
    check("a sheet easing away takes no more taps",
          pg.evaluate("() => getComputedStyle(document.getElementById('moreMenu')).pointerEvents") == "none", "")
    ctx.close()
    # Landscape phone: Flip's dropdown runs off the bottom and is not a sheet.
    lctx = b.new_context(viewport={"width": 844, "height": 390}, has_touch=True, is_mobile=True)
    lpg = lctx.new_page(); browsing.goto(lpg, BASE, "/flip"); lpg.wait_for_timeout(900)
    lpg.evaluate("() => document.getElementById('moreBtn').click()"); lpg.wait_for_timeout(500)
    lopen = lpg.evaluate("() => !document.getElementById('moreMenu').hidden")
    lx, ly = top_point(lpg, "#moreMenu")
    lpg.evaluate(TOUCH, ["#moreMenu", "touchstart", lx, ly])
    ltake = lpg.evaluate(TOUCH, ["#moreMenu", "touchmove", lx, ly + 3])
    lpg.evaluate(TOUCH, ["#moreMenu", "touchmove", lx, ly + 120])
    lmoved = lpg.evaluate("() => document.getElementById('moreMenu').style.transform")
    lpg.evaluate(TOUCH, ["#moreMenu", "touchend", lx, ly + 120]); lpg.wait_for_timeout(450)
    check("on a landscape phone Flip's dropdown is not taken for a bottom sheet (a pull is not claimed, dragged or closed)",
          lopen is True and ltake is False and not lmoved
          and lpg.evaluate("() => !document.getElementById('moreMenu').hidden") is True,
          f"open={lopen} claimed={ltake} transform={lmoved!r}")
    lctx.close()

    # 6b a quick second tap reopens a menu that is still easing away
    print("\nreopen mid-slide")
    # Open = not hidden AND resting on screen, read from the page, not from
    # the library's private timer.
    for page, route, btn, handle, is_open in (
        ("Flip", "/flip", "moreBtn", "#moreMenu .menu-handle",
         "() => { const m = document.getElementById('moreMenu'); return !m.hidden && m.getBoundingClientRect().top < innerHeight - 80; }"),
        ("Library", "/library", "pageMenuBtn", "#pageMenu .pm-grab",
         "() => { const m = document.getElementById('pageMenu'); return !document.getElementById('pageMenuOverlay').hidden && m.getBoundingClientRect().top < innerHeight - 80; }"),
        # The Pad's overlay stayed unhidden, full-screen, for the slide and ate
        # the tap (third review) -- so its second tap is a real pointer at the
        # button's spot, which a script's .click() would walk straight past.
        ("Pad", "/skribl-pad", "menuBtn", "#menuSheet .menu-handle",
         "() => { const o = document.getElementById('menuOverlay'); return !o.hidden && o.classList.contains('open') && document.getElementById('menuSheet').getBoundingClientRect().top < innerHeight - 80; }")):
        ctx, pg, errs = fresh(b, route)
        pg.evaluate(f"() => document.getElementById('{btn}').click()"); pg.wait_for_timeout(500)
        sheet_sel = handle.split(" ")[0]
        # The precondition, read from the page: it IS on its way out (lower
        # than it rests, still laid out). Without it a grabber that did nothing
        # and a button that only opens would pass this check. Waited for frame
        # by frame, up to 200 ms, because each sheet's curve starts at its own
        # pace -- a fixed instant read the Pad's slow start as "not moving".
        leaving = pg.evaluate(f"""async () => {{ const m = document.querySelector('{sheet_sel}');
            const top0 = m.getBoundingClientRect().top;
            document.querySelector('{handle}').click();
            const t0 = performance.now();
            while (performance.now() - t0 < 200) {{
              await new Promise(r => requestAnimationFrame(r));
              if (m.getClientRects().length > 0 && m.getBoundingClientRect().top > top0 + 2) return true;
            }}
            return false; }}""")
        if page == "Pad":
            bb = pg.locator(f"#{btn}").bounding_box()
            pg.mouse.click(bb["x"] + bb["width"] / 2, bb["y"] + bb["height"] / 2)
        else:
            pg.evaluate(f"() => document.getElementById('{btn}').click()")
        pg.wait_for_timeout(500)
        check(f"{page}: tapping the menu button again while the menu eases away brings it back",
              leaving is True and pg.evaluate(is_open) is True, f"was leaving={leaving}")
        ctx.close()

    # 7 Post cannot be swiped away mid-send (canClose): the request is held
    # open so "mid-send" lasts as long as the check needs.
    print("\nPad: the post sheet while posting")
    ctx, pg, errs = fresh(b, "/skribl-pad")
    held = []
    pg.route("**/api/skribls", lambda route: held.append(route) if route.request.method == "POST" else route.continue_())
    box = pg.locator("#canvas").bounding_box()
    pg.mouse.move(box["x"] + 60, box["y"] + 60); pg.mouse.down()
    pg.mouse.move(box["x"] + 160, box["y"] + 120, steps=6); pg.mouse.up(); pg.wait_for_timeout(400)
    open_sheet(pg, "() => { const b = document.getElementById('postBtn'); b.disabled = false; b.click(); }",
               "() => document.getElementById('postOverlay').hidden")
    pg.evaluate("() => document.getElementById('postSubmitBtn').click()")
    pg.wait_for_timeout(400)
    # Sending, by the state the sheet shows: the status row is up and the
    # button is spent. (The "Posting…" words are in the markup all along.)
    sending = pg.evaluate("() => !document.getElementById('postStatus').hidden && document.getElementById('postSubmitBtn').disabled")
    x, y = top_point(pg, "#postSheet")
    pg.evaluate(TOUCH, ["#postSheet", "touchstart", x, y]); pg.wait_for_timeout(30)
    pg.evaluate(TOUCH, ["#postSheet", "touchmove", x, y + 40]); pg.wait_for_timeout(30)
    pg.evaluate(TOUCH, ["#postSheet", "touchmove", x, y + 160])
    pg.evaluate(TOUCH, ["#postSheet", "touchend", x, y + 160]); pg.wait_for_timeout(450)
    pg.evaluate("() => document.querySelector('#postSheet .menu-handle').click()"); pg.wait_for_timeout(450)
    check("Pad: mid-send, neither a swipe nor the grabber closes the post sheet",
          sending and pg.evaluate("() => document.getElementById('postOverlay').hidden") is False,
          f"sending={sending}")
    for r in held:                             # the held send ends here, answered
        r.abort()
    ctx.close()

    # 8 a lane for the scroll bar. iOS paints its bar OVER the list, 8 px in
    # from the right edge, so a card that runs to the edge has the thumb on its
    # border (owner's iPhone, after v317). Headless Chromium gives its bar a
    # gutter and cannot show the overlap, so what is pinned is the property
    # the fix governs: every card stops short of the lane.
    print("\nPad: your drafts leave the scroll bar a lane")
    ctx, pg, errs = fresh(b, "/skribl-pad")
    box = pg.locator("#canvas").bounding_box()
    pg.mouse.move(box["x"] + 60, box["y"] + 60); pg.mouse.down()
    pg.mouse.move(box["x"] + 160, box["y"] + 140, steps=6); pg.mouse.up(); pg.wait_for_timeout(300)
    for _ in range(6):
        pg.evaluate("async () => { SkriblSavedDrafts.forget(); await SkriblSavedDrafts.save(); }")
    pg.evaluate("() => SkriblSavedDrafts.open()"); pg.wait_for_timeout(900)
    lane = pg.evaluate("""() => { const l = document.querySelector('#savedDraftsSheet .sdrafts-list');
        const edge = l.getBoundingClientRect().right;
        const rows = [...l.querySelectorAll('.sdrafts-row')].map(r => Math.round(edge - r.getBoundingClientRect().right));
        return { rows, scrolls: l.scrollHeight > l.clientHeight }; }""")
    check("Pad: every draft card stops at least 10 px short of the list's right edge, where iOS draws its bar",
          len(lane["rows"]) >= 6 and min(lane["rows"]) >= 10, str(lane))
    ctx.close()

    # 5 the draw drawer's grip
    for page, route in (("Pad", "/skribl-pad"), ("Flip", "/flip")):
        who = f"{page}: the draw drawer"
        print(f"\n{who}")
        ctx, pg, errs = fresh(b, route)
        # The pen, tapped again, on both editors since the dock redesign: the
        # colour button this used to look for is gone from both bars.
        opened = pg.locator("#penToolBtn").count() == 1
        if opened:
            browsing.pad_drawer(pg, "draw", settle=600)
        is_open = pg.evaluate("() => !document.getElementById('drawPanel').hidden")
        check(f"{who} opens from its tool", opened and is_open)
        check(f"{who}: open, the page does not pull to refresh",
              pg.evaluate(OVERSCROLL) == "none", f"{pg.evaluate(OVERSCROLL)!r}")
        h = pg.locator("#drawPanel .drawer-detent-handle").bounding_box()
        pg.touchscreen.tap(h["x"] + h["width"] / 2, h["y"] + h["height"] / 2)
        pg.wait_for_timeout(500)
        check(f"{who}: tapping the grip closes it",
              pg.evaluate("() => document.getElementById('drawPanel').hidden") is True)
        check(f"{who}: no page errors", not errs, "; ".join(errs[:2]))
        ctx.close()

    # 5b THE FULL DRAWER'S GRIP IS ON SCREEN, AND IT IS THE GRIP THAT CLOSES
    # IT. Expanding scrolled the drawer's END into view, which on a short phone
    # carried its top -- the grip -- under the sticky header: at 390x664 Flip's
    # grip sat at y 3-27 behind a header at 6-66, and section 6's tap "worked"
    # only because a tap on the header is an outside tap. So: what is PAINTED
    # at the grip's centre (a rect is not a paint), at four heights; still
    # painted after the drawer is scrolled to its last control; and the close
    # counted on the grip itself, not merely observed.
    # The WHOLE grip, top edge to bottom edge: Flip's own open-scroll once
    # settled 9-15px past the end at 700-720px, leaving the centre painted and
    # the top edge under the header -- a centre-only probe called that green.
    GRIP = """() => { const h = document.querySelector('#drawPanel .drawer-detent-handle').getBoundingClientRect();
        const hit = y => { const at = document.elementFromPoint(h.left + h.width / 2, y); return !!(at && at.closest('.drawer-detent-handle')); };
        return { y: Math.round(h.top), hit: hit(h.top + 2) && hit(h.top + h.height / 2) && hit(h.bottom - 2) }; }"""
    for page, route in (("Pad", "/skribl-pad"), ("Flip", "/flip")):
        for hgt in (600, 664, 720, 844):
            who = f"{page}: the full draw drawer at 390x{hgt}"
            print(f"\n{who}")
            # Loaded at that height, not resized to it: Flip sizes its canvas
            # at load, and a resized page never formed the 720px case.
            ctx, pg, errs = fresh(b, route, hgt)
            browsing.pad_drawer(pg, "draw", settle=600)
            pg.evaluate("""() => { window.__gripUps = 0;
                document.querySelector('#drawPanel .drawer-detent-handle').addEventListener('pointerup', () => window.__gripUps++);
                document.querySelector('#drawPanel .dp-tile[data-dp=feel]').click(); }""")
            waits.settle(pg, 1700)
            g = pg.evaluate(GRIP)
            check(f"{who}: expanded, the whole grip is painted, edge to edge", g["hit"], str(g))
            # The dock above it is painted too, not pushed into the header's band
            # (glass over glass: its icons showed through the logo and Post).
            dock = pg.evaluate("""() => { const d = document.querySelector('#toolBar, .flip-tools'); const r = d.getBoundingClientRect();
                const pen = document.getElementById('penToolBtn').getBoundingClientRect();
                const at = document.elementFromPoint(pen.left + pen.width / 2, pen.top + 3);
                const h = document.querySelector('.header').getBoundingClientRect();
                return { top: Math.round(r.top), header: Math.round(h.bottom), pen: !!(at && at.closest('#penToolBtn')) }; }""")
            check(f"{who}: ...and the dock above it is clear of the header, its pen tool painted",
                  dock["pen"] and dock["top"] >= dock["header"], str(dock))
            # Down to the drawer's last control, as a person reaching Clear all pages does.
            last = pg.evaluate("""() => { const all = [...document.querySelectorAll('#drawPanel button')].filter(e => e.offsetParent);
                const c = all[all.length - 1]; c.scrollIntoView({ block: 'end' }); return c.id || c.className; }""")
            pg.wait_for_timeout(400)
            hit = pg.evaluate("""() => { const all = [...document.querySelectorAll('#drawPanel button')].filter(e => e.offsetParent);
                const c = all[all.length - 1], r = c.getBoundingClientRect();
                const at = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
                return !!(at && c.contains(at)); }""")
            g2 = pg.evaluate(GRIP)
            check(f"{who}: scrolled to its last control, that control and the grip are both painted",
                  hit and g2["hit"], f"last {last!r} painted {hit}, grip {g2}")
            hb = pg.locator("#drawPanel .drawer-detent-handle").bounding_box()
            pg.touchscreen.tap(hb["x"] + hb["width"] / 2, hb["y"] + hb["height"] / 2)
            pg.wait_for_timeout(600)
            shut = pg.evaluate("() => ({ hidden: document.getElementById('drawPanel').hidden, ups: window.__gripUps })")
            check(f"{who}: a tap on the grip closes it -- the grip's own tap, not an outside one",
                  shut["hidden"] is True and shut["ups"] == 1, str(shut))
            check(f"{who}: no page errors", not errs, "; ".join(errs[:2]))
            ctx.close()

    # 6 THE PAGE GOES HOME (owner, from an iPhone: the page "bounced back too
    # high ... stuck out of view about the header's size ... and header menu
    # is gone"). On a phone an open drawer scrolls the PAGE to show itself;
    # Flip never scrolled back on close, and nothing caught a page left
    # scrolled with nothing open. Asked as what is PAINTED at the header's
    # middle, because a header scrolled off the top keeps its rect.
    HOME = """() => { const h = document.querySelector('.header'); const r = h.getBoundingClientRect();
        const at = document.elementFromPoint(r.left + r.width / 2, Math.max(1, r.top + r.height / 2));
        return { y: Math.round(window.scrollY), painted: !!(at && h.contains(at)) }; }"""
    for page, route in (("Pad", "/skribl-pad"), ("Flip", "/flip")):
        who = f"{page}: the page"
        print(f"\n{who}")
        ctx, pg, errs = fresh(b, route)
        browsing.pad_drawer(pg, "draw", settle=600)
        pg.evaluate("() => { const m = document.querySelector('#drawPanel .dp-tile[data-dp=feel]'); if (m) m.click(); }")
        pg.wait_for_timeout(1500)
        opened_y = pg.evaluate("() => Math.round(window.scrollY)")
        check(f"{who}: the full draw drawer scrolled the page to show itself (precondition)",
              opened_y > 0, f"scrollY {opened_y} -- without this the next check asks nothing")
        h = pg.locator("#drawPanel .drawer-detent-handle").bounding_box()
        pg.touchscreen.tap(h["x"] + h["width"] / 2, h["y"] + h["height"] / 2)
        pg.wait_for_timeout(1200)
        home = pg.evaluate(HOME)
        # Chromium also gets here by itself -- the page clamps as the drawer
        # shrinks -- so this pins the outcome, not Flip's own scroll home (a
        # mutation removing it stays green). The check below is the pin.
        check(f"{who}: closing the drawer brings it home, the header painted on screen",
              home["y"] == 0 and home["painted"], str(home))
        # STUCK WITH NOTHING OPEN: the iPhone state, made by hand. The page is
        # given room it should not have and left scrolled; a finger lifts.
        pg.evaluate("() => { document.body.style.paddingBottom = '400px'; window.scrollTo(0, 90); }")
        pg.wait_for_timeout(100)
        stuck = pg.evaluate(HOME)
        pg.evaluate("() => window.dispatchEvent(new TouchEvent('touchend', { touches: [] }))")
        pg.wait_for_timeout(700)
        back = pg.evaluate(HOME)
        check(f"{who}: left scrolled with nothing open, it goes home once the touch ends",
              stuck["y"] > 0 and back["y"] == 0 and back["painted"],
              f"stuck {stuck} -> {back}")
        # ...AND LEAVES AN OPEN DRAWER ALONE: the snap is for a page with no
        # reason to be scrolled, never one showing a drawer.
        browsing.pad_drawer(pg, "draw", settle=600)
        pg.evaluate("() => window.scrollTo(0, 90)")
        pg.evaluate("() => window.dispatchEvent(new TouchEvent('touchend', { touches: [] }))")
        pg.wait_for_timeout(700)
        kept = pg.evaluate("() => Math.round(window.scrollY)")
        check(f"{who}: with a drawer open it does not pull the page away from it",
              kept > 0, f"scrollY {kept}")
        check(f"{who}: no page errors", not errs, "; ".join(errs[:2]))
        ctx.close()

    # 7 THE MUSIC DRAWER'S MORE (owner: "Clicking this moves the arrow but
    # doesn't show you what's there"). Fine-tune was a row under Preview Loop
    # that opened below the fold, then a level (Simple, Adjust, Fine-tune), and
    # is More now (lib/musicdrawer.js): the strip stays above it, and opening
    # More must put what it opens ON SCREEN.
    import wave as _wave, struct as _struct, math as _math, io as _io
    _buf = _io.BytesIO()
    with _wave.open(_buf, "wb") as _w:
        _w.setnchannels(1); _w.setsampwidth(2); _w.setframerate(22050)
        _w.writeframes(b"".join(_struct.pack("<h", int(8000 * _math.sin(i / 8))) for i in range(22050 * 4)))
    for page, route in (("Pad", "/skribl-pad"), ("Flip", "/flip")):
        who = f"{page}: the music drawer"
        print(f"\n{who}")
        ctx, pg, errs = fresh(b, route)
        browsing.pad_drawer(pg, "music", settle=500)
        pg.set_input_files("#musicInput", {"name": "t.wav", "mimeType": "audio/wav", "buffer": _buf.getvalue()})
        pg.wait_for_function("() => typeof currentAudioBuffer !== 'undefined' && !!currentAudioBuffer", timeout=20000)
        pg.wait_for_timeout(600)
        # ONE COLOUR RULE FOR THE SAME SOUND (owner: "the colors are
        # different"): the timeline draws the song in the accent, the loop's
        # peaks solid and the rest of the song faint, and the Restart view
        # the same accent. Read off the timeline's own pixels in the song's
        # middle band: the most accent-coloured pixel inside a middle loop
        # and outside it, before its start.
        pg.evaluate("() => { trimStart = audioDuration * 0.25; trimEnd = audioDuration * 0.75; updateTrimUI(); }")
        pg.wait_for_timeout(700)
        ink = pg.evaluate("""() => { const c = document.getElementById('musicTlCanvas'), x = c.getContext('2d'), k = c.width / c.clientWidth;
            const y0 = Math.round(60 * k), y1 = Math.round(100 * k), w = c.width;
            const d = x.getImageData(0, y0, w, y1 - y0).data, rows = y1 - y0;
            const most = (x0, x1) => { let best = -999;
              for (let X = Math.floor(x0); X < Math.floor(x1); X++) for (let Y = 0; Y < rows; Y++) {
                const i = (Y * w + X) * 4; if (d[i + 3] > 200) best = Math.max(best, d[i + 2] - d[i]); }
              return best; };
            const card = getComputedStyle(document.getElementById('musicTimeline')).getPropertyValue('--menu-card').trim();
            return { inside: most(w * 0.35, w * 0.65), outside: most(w * 0.015, w * 0.07), card: card }; }""")
        check(f"{who}: the timeline draws the loop's peaks in the accent, solid, and the rest of the song faint",
              ink["inside"] > 110 and 30 < ink["outside"] < ink["inside"] - 40,
              f"blue over red at the most accented pixel: inside the loop {ink['inside']}, before it {ink['outside']} (the card {ink['card']})")
        # More (it was Fine-tune; its tile keeps the id) opens the Restart
        # view among the rest: what opened comes ON SCREEN, its first part
        # painted, without a scroll by hand.
        pg.click("#fineTuneToggle")
        pg.wait_for_timeout(1600)
        ft = pg.evaluate("""() => { const z = document.getElementById('musicSmooth').getBoundingClientRect(), d = document.getElementById('fineTuneBody').getBoundingClientRect();
            const vh = window.visualViewport ? visualViewport.height : innerHeight;
            const hit = document.elementFromPoint(z.left + z.width / 2, z.top + z.height / 2);
            return { open: document.getElementById('fineTuneToggle').getAttribute('aria-expanded'),
                     strip: document.getElementById('musicTimeline').getBoundingClientRect().height,
                     top: Math.round(d.top), bottom: Math.round(z.bottom), vh: Math.round(vh),
                     painted: !!(hit && hit.closest('#musicSmooth')) }; }""")
        check(f"{who}: More is open, and the timeline stays above what it opens",
              ft["open"] == "true" and ft["strip"] > 0, str(ft))
        check(f"{who}: ...and what More opens is ON SCREEN, painted, without a scroll by hand",
              ft["top"] >= 0 and ft["bottom"] <= ft["vh"] and ft["painted"], str(ft))
        pg.click("#fineTuneToggle")
        pg.wait_for_timeout(700)
        back = pg.evaluate("() => ({ strip: document.getElementById('musicTimeline').getBoundingClientRect().height,"
                           " hidden: document.getElementById('fineTuneBody').hidden })")
        check(f"{who}: closing More keeps the timeline and puts what More holds away", back["strip"] > 0 and back["hidden"] is True, str(back))
        # ROOM BETWEEN THE LOOP PANEL'S ROWS (owner: "things just seem close
        # together"). Measured before at 390: the loop detail's handle caps
        # touched its zoom bar (0px) and sat 2px over Scroll. Every gap down
        # what More opens is >= 8px, the Restart view's own box included.
        pg.click("#fineTuneToggle")
        pg.wait_for_timeout(1200)
        gaps = pg.evaluate("""() => { const q = s => document.querySelector('#musicDetail ' + s).getBoundingClientRect();
            // A switch row by its words: its 8px of padding above and below is
            // the row's own air, so two switch rows in a row touch box to box
            // with 16px between what they say.
            const sw = (id) => document.getElementById(id).closest('.mt-switch').querySelector('.mt-switch-words').getBoundingClientRect();
            const rows = [['smooth restart', sw('musicSmooth')], ['restart view', q('#musicRestart')], ['its hint', q('#musicRvHint')],
                          ['length', q('.crossfade-row')], ['hear the restart', q('#testSeamBtn')], ['tap', q('.mt-tap-row')],
                          ['start/end', q('.edge-group')], ['each press', q('.mt-step')], ['cut on silence', sw('musicCut')], ['lock', sw('musicLock')]];
            return rows.slice(1).map((r, i) => [rows[i][0] + ' -> ' + r[0], Math.round(r[1].top - rows[i][1].bottom)]); }""")
        check(f"{who}: every row of what More opens has at least 8px above it",
              all(g >= 8 for _, g in gaps), str(gaps))
        # NO LEAP WHEN MORE CLOSES (owner, of the old Fine-tune: "when you're in
        # fine tune and switch back to trim it snaps back"). More ends below
        # the screen, so its tile is reached by scrolling back up to it, and
        # from there closing makes the page several hundred px shorter: the
        # browser would clamp the scroll in ONE frame. lib/drawerdetent.js's
        # shrinkGently glides it instead: no frame may move the tile more than
        # a third of the whole move (it was 120px of a 238-262px glide, back to
        # Adjust; More's is about 700px, and the browser's own glide over that
        # moved 171px in one frame at its fastest), nor 120px on a short one.
        # On the owner's phone, 402x874: at 664 tall a control 400px above the
        # screen is Playwright scrolling it into view first (a 706px "leap" of
        # its own), and the clamp is too small there for this rule to see; at
        # 874 it is hundreds of px.
        pg.set_viewport_size({"width": 402, "height": 874})
        pg.wait_for_timeout(300)
        pg.evaluate("() => window.scrollTo(0, 1e6)")
        pg.wait_for_timeout(800)
        pg.evaluate("""() => { const s = document.getElementById('fineTuneToggle'), h = document.querySelector('.header');
            const top = h && ['sticky', 'fixed'].includes(getComputedStyle(h).position) ? h.getBoundingClientRect().bottom : 0;
            const over = s.getBoundingClientRect().top - top - 10; if (over < 0) window.scrollBy(0, over); }""")
        pg.wait_for_timeout(600)
        pg.evaluate("""() => { window._ftLog = []; const t0 = performance.now(), seg = document.getElementById('fineTuneToggle');
            const f = () => { _ftLog.push([performance.now(), seg.getBoundingClientRect().top]); if (performance.now() - t0 < 1500) requestAnimationFrame(f); };
            requestAnimationFrame(f); }""")
        pg.click("#fineTuneToggle")
        pg.wait_for_timeout(1700)
        log = pg.evaluate("_ftLog")
        steps = [(abs(b2[1] - a2[1]), b2[0] - a2[0]) for a2, b2 in zip(log, log[1:])]
        total = abs(log[-1][1] - log[0][1]) if log else 0
        big = max(steps) if steps else (0, 0)
        check(f"{who}: closing More from the drawer's end, its tile glides rather than leaps",
              len(log) > 10 and big[0] <= max(120, total / 3) and total > 50,
              f"largest single-frame move {round(big[0])}px in a {round(big[1])}ms frame, total {round(total)}px over {len(log)} frames")
        check(f"{who}: no page errors", not errs, "; ".join(errs[:2]))
        ctx.close()
    b.close()

passed = sum(1 for ok, _ in results if ok)
bad = [n for ok, n in results if not ok]
print("\n" + "=" * 62)
print(f"{passed}/{len(results)} passed"
      + ("" if not bad else "\nFAILURES:\n  - " + "\n  - ".join(bad)))
sys.exit(1 if bad else 0)
