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

# Where the sheet is, and whether it is laid out at all, part-way through a close.
SAMPLE = """(sel) => { const s = document.querySelector(sel);
  return { shown: s.getClientRects().length > 0, top: s.getBoundingClientRect().top }; }"""
EASE_MS = 90

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
]

def fresh(b, route):
    ctx = b.new_context(viewport={"width": 390, "height": 664}, has_touch=True, is_mobile=True,
                        device_scale_factor=2)
    pg = ctx.new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    browsing.goto(pg, BASE, route)
    pg.wait_for_timeout(900)
    pg.evaluate("() => { window.SkriblHints && window.SkriblHints.hide(); }")
    return ctx, pg, errs


def open_sheet(pg, how, closed):
    # Only when shut: some openers toggle, and a mutated grabber leaves it open.
    if pg.evaluate(closed):
        pg.evaluate(how)
        pg.wait_for_timeout(500)
    return not pg.evaluate(closed)


def top_point(pg, sel):
    r = pg.locator(sel).bounding_box()
    return r["x"] + r["width"] / 2, r["y"] + 20


with sync_playwright() as p:
    b = p.chromium.launch()
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
            top0 = pg.evaluate(SAMPLE, sel)["top"]
            pg.evaluate(f"() => document.querySelector('{grab}').click()")
            pg.wait_for_timeout(EASE_MS)
            mid = pg.evaluate(SAMPLE, sel)
            pg.wait_for_timeout(450)
            check(f"{who}: tapping the grabber eases it down rather than snapping it away",
                  mid["shown"] and mid["top"] > top0 + 10,
                  f"{EASE_MS}ms in: shown={mid['shown']}, top {round(top0)} -> {round(mid['top'])}")
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
        dragged = pg.evaluate(SAMPLE, sel)["top"]
        pg.evaluate(TOUCH, [sel, "touchend", x, y + 140]); pg.wait_for_timeout(EASE_MS)
        mid = pg.evaluate(SAMPLE, sel)
        pg.wait_for_timeout(450)
        check(f"{who}: let go past the line, it carries on down from the finger (no jump back, no vanish)",
              mid["shown"] and mid["top"] > dragged + 5,
              f"{EASE_MS}ms after release: shown={mid['shown']}, top {round(dragged)} -> {round(mid['top'])}")
        check(f"{who}: a swipe down follows the finger", "translateY(140px)" in (follows or ""), repr(follows))
        check(f"{who}: ...and the touch is the sheet's, not the page's (the move is cancelled: no scroll, no reload)",
              taken is True, f"defaultPrevented={taken}")
        check(f"{who}: ...and it closes", pg.evaluate(closed) is True)
        check(f"{who}: no page errors", not errs, "; ".join(errs[:2]))
        ctx.close()

    # 6 reduced motion: no slide, gone at once
    print("\nreduced motion")
    rctx = b.new_context(viewport={"width": 390, "height": 664}, has_touch=True, is_mobile=True,
                         reduced_motion="reduce")
    rpg = rctx.new_page()
    browsing.goto(rpg, BASE, "/flip"); rpg.wait_for_timeout(900)
    rpg.evaluate("() => document.getElementById('moreBtn').click()"); rpg.wait_for_timeout(500)
    rpg.evaluate("() => document.querySelector('#moreMenu .menu-handle').click()"); rpg.wait_for_timeout(30)
    check("with reduced motion, Flip's menu closes at once rather than sliding",
          rpg.evaluate("() => document.getElementById('moreMenu').hidden") is True)
    rctx.close()

    # 6b a quick second tap reopens a menu that is still easing away
    print("\nreopen mid-slide")
    for page, route, btn, handle, is_open in (
        ("Flip", "/flip", "moreBtn", "#moreMenu .menu-handle",
         "() => !document.getElementById('moreMenu').hidden && !document.getElementById('moreMenu')._slideT"),
        ("Library", "/library", "pageMenuBtn", "#pageMenu .pm-grab",
         "() => !document.getElementById('pageMenuOverlay').hidden && !document.getElementById('pageMenu')._slideT")):
        ctx, pg, errs = fresh(b, route)
        pg.evaluate(f"() => document.getElementById('{btn}').click()"); pg.wait_for_timeout(500)
        pg.evaluate(f"() => document.querySelector('{handle}').click()"); pg.wait_for_timeout(60)
        pg.evaluate(f"() => document.getElementById('{btn}').click()"); pg.wait_for_timeout(500)
        check(f"{page}: tapping the menu button again while the menu eases away brings it back",
              pg.evaluate(is_open) is True)
        ctx.close()

    # 5 the draw drawer's grip
    for page, route in (("Pad", "/skribl-pad"), ("Flip", "/flip")):
        who = f"{page}: the draw drawer"
        print(f"\n{who}")
        ctx, pg, errs = fresh(b, route)
        opened = pg.evaluate("""() => { const b = document.querySelector('.tool-open[data-drawer="draw"], #drawBtn, [aria-controls="drawPanel"]');
            if (b) b.click(); return !!b; }""")
        pg.wait_for_timeout(600)
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
    b.close()

passed = sum(1 for ok, _ in results if ok)
bad = [n for ok, n in results if not ok]
print("\n" + "=" * 62)
print(f"{passed}/{len(results)} passed"
      + ("" if not bad else "\nFAILURES:\n  - " + "\n  - ".join(bad)))
sys.exit(1 if bad else 0)
