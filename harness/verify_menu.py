#!/usr/bin/env python3
"""The ⋯ menu, one for both editors (templates/skribl/_skribl_menu.html,
lib/menupages.js; the owner's yes to the menu mock, after v323).

It was fifteen equal rows that scrolled on a phone and on a desk. Each row
below holds a promise the new menu made, on the Pad and on Flip:

  1. IT FITS. On the owner's 402x874 phone and a 1333x906 desk, light and dark,
     the menu does not scroll, no target is under 44px, names are 16px and the
     line under each 14px.
  2. THE SAME MENU. Pad's and Flip's show the same tiles and rows in the same
     order; only the editor lit in the switch differs.
  3. A CHOICE IS THE SLIDING TINT. The switch lights the editor you are in
     with the app's pill (placed by lib/segslider.js); the other is a link
     to the other editor. How it works' tabs are a track of the same pill.
  4. PAGES. New opens its page with focus on Back; Escape comes back to the
     main page with focus on New; every opening starts on the main page.
  5. NEW SKRIBL, one tap after the shape: the drawing goes, the canvas takes
     the shape picked, and Undo brings back both the drawing and its shape.
  6. YOUR DRAFTS holds the name and the .skribl file both ways; the name opens
     the name drawer and puts the sheet away.

Visible means painted: elementFromPoint inside the thing, not its rect.
"""
import math
import os
import sys

from assertions import make_check
import browsing

BASE = os.environ.get("SKRIBL_BASE", "http://127.0.0.1:5001")
results = []
check = make_check(results, detail_on_pass=False)

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("SKIP: playwright is not installed")
    sys.exit(0)

PHONE = dict(viewport={"width": 402, "height": 874}, device_scale_factor=2, is_mobile=True, has_touch=True)
DESK = dict(viewport={"width": 1333, "height": 906})
EDITORS = (("Pad", "/skribl-pad", "menuBtn", "#canvas", "clearMenuItem", "() => [authoredW, authoredH]"),
           ("Flip", "/flip", "moreBtn", "#pad", "miClearAll", "() => [CW, CH]"))
SHEET = "(document.getElementById('menuSheet') || document.getElementById('moreMenu'))"
FIT = """() => { const s = """ + SHEET + """, r = s.getBoundingClientRect();
  const on = e => { if (!e.getClientRects().length || e.closest('[hidden]')) return false;
    const b = e.getBoundingClientRect(), at = document.elementFromPoint(b.left + b.width / 2, b.top + b.height / 2);
    return !!at && (at === e || e.contains(at)); };
  const t = [...s.querySelectorAll('button, a')].filter(on);
  const small = t.filter(e => { const b = e.getBoundingClientRect(); return b.width < 43.5 || b.height < 43.5; })
                 .map(e => e.id || e.textContent.trim().slice(0, 12));
  const it = document.getElementById('openCloudDraftItem');
  return { scrolls: s.scrollHeight > s.clientHeight + 1, top: Math.round(r.top), bottom: Math.round(r.bottom), vh: innerHeight,
           targets: t.length, small, name: getComputedStyle(it).fontSize,
           sub: getComputedStyle(it.querySelector('.menu-item-sub')).fontSize }; }"""
ORDER = """() => { const s = """ + SHEET + """;
  return [...s.querySelectorAll('.menu-page[data-menu-page="main"] :is(.menu-tile, .menu-list > .menu-item:not([hidden]), .menu-foot-link)')]
           .map(e => e.textContent.replace(/\\s+/g, ' ').trim().split(' ').slice(0, 2).join(' ')); }"""
SWITCH = """() => { const seg = document.querySelector('.menu-editor-seg'), lit = seg.querySelector('button.menu-editor.on'),
    link = seg.querySelector('a.menu-editor');
  if (!lit) return { pill: false, lit: null, linkTo: link ? link.getAttribute('href') : null, linkText: null };
  const pill = seg.querySelector(':scope > .seg-slider'), p = pill.getBoundingClientRect(), l = lit.getBoundingClientRect();
  return { pill: seg.hasAttribute('data-pill') && Math.abs(p.left - l.left) < 4 && Math.abs(p.width - l.width) < 8,
           lit: lit.textContent.trim(), linkTo: link ? link.getAttribute('href') : null, linkText: link ? link.textContent.trim() : null }; }"""


def scribble(q, sel):
    bx = q.locator(sel).bounding_box()
    cx, cy = bx["x"] + bx["width"] / 2, bx["y"] + bx["height"] / 2
    q.mouse.move(cx - 60, cy)
    q.mouse.down()
    for i in range(30):
        q.mouse.move(cx - 60 + i * 4, cy + math.sin(i / 4) * 40)
        q.wait_for_timeout(10)
    q.mouse.up()
    q.wait_for_timeout(300)


def open_menu(q, btn):
    q.evaluate(f"() => document.getElementById('{btn}').click()")
    q.wait_for_timeout(700)


with sync_playwright() as p:
    b = p.chromium.launch()
    orders = {}
    for name, route, btn, cv, start, size in EDITORS:
        print(f"\n{name.upper()}")
        # 1. it fits
        for dev, opts in (("phone", PHONE), ("desk", DESK)):
            for scheme in ("light", "dark"):
                c = b.new_context(color_scheme=scheme, **opts)
                q = c.new_page()
                browsing.goto(q, BASE, route)
                q.wait_for_timeout(800)
                q.evaluate("() => window.SkriblHints && window.SkriblHints.hide()")
                open_menu(q, btn)
                f = q.evaluate(FIT)
                check(f"{name}, {dev}, {scheme}: the menu fits without scrolling, every target 44px or more, names 16px over 14px",
                      not f["scrolls"] and f["bottom"] <= f["vh"] and f["targets"] >= 10 and not f["small"]
                      and f["name"] == "16px" and f["sub"] == "14px", str(f))
                if dev == "phone" and scheme == "light":
                    orders[name] = q.evaluate(ORDER)
                    # 3. the switch
                    sw = q.evaluate(SWITCH)
                    other = "/flip" if name == "Pad" else "/skribl-pad"
                    check(f"{name}: the switch lights {name} with the sliding pill; the other editor is a link to it",
                          sw["pill"] and sw["lit"] == name and (sw["linkTo"] or "").startswith(other), str(sw))
                c.close()

        # 4. pages, 5. New Skribl, 6. Your drafts. A step that cannot run (a
        # page that never opened, a button that is not there) is a FAILURE
        # reported, and the rows after it still run.
        def part(label, fn):
            try:
                fn()
            except Exception as e:
                check(f"{name}: {label} ran to the end", False, repr(e)[:200])

        c = b.new_context(**PHONE)
        q = c.new_page()
        errs = []
        q.on("pageerror", lambda e: errs.append(str(e)))
        browsing.goto(q, BASE, route)
        q.wait_for_timeout(800)
        q.evaluate("() => window.SkriblHints && window.SkriblHints.hide()")
        def pages():
            open_menu(q, btn)
            q.click("#menuNewTile", timeout=3000)
            q.wait_for_timeout(400)
            pg = q.evaluate("() => ({ page: SkriblMenuPages.current(), focus: document.activeElement && document.activeElement.className })")
            check(f"{name}: New opens its page, focus on Back", pg["page"] == "new" and "menu-back" in (pg["focus"] or ""), str(pg))
            q.keyboard.press("Escape")
            q.wait_for_timeout(300)
            back = q.evaluate("() => ({ page: SkriblMenuPages.current(), focus: document.activeElement && document.activeElement.id,"
                              " open: !" + SHEET + ".closest('[hidden]') })")
            check(f"{name}: Escape on a page comes back to the menu, focus on New, the menu still open",
                  back["page"] == "main" and back["focus"] == "menuNewTile" and back["open"], str(back))
            # Closed on a page, it opens on the main page again.
            q.evaluate("() => SkriblMenuPages.show('settings', false)")
            q.evaluate(f"() => document.getElementById('{btn}').click()")   # closes
            q.wait_for_timeout(600)
            open_menu(q, btn)
            again = q.evaluate("() => SkriblMenuPages.current()")
            check(f"{name}: every opening starts on the main page", again == "main", again)
            q.evaluate(f"() => document.getElementById('{btn}').click()")
            q.wait_for_timeout(600)

        INK = "() => (typeof strokes !== 'undefined' ? strokes.length : frames.reduce((n, f) => n + f.strokes.length, 0))"

        def new_skribl():
            scribble(q, cv)
            if name == "Pad":
                q.evaluate("() => { if (recording) document.getElementById('recordBtn').click(); }")
                q.wait_for_timeout(300)
            before = q.evaluate(size)
            open_menu(q, btn)
            q.click("#menuNewTile", timeout=3000)
            q.wait_for_timeout(400)
            lit = q.evaluate("() => document.querySelector('#newSizeSeg button.on').dataset.size")
            pick = "square" if lit != "square" else "wide"
            q.click(f'#newSizeSeg button[data-size="{pick}"]', timeout=3000)
            q.wait_for_timeout(200)
            q.click(f"#{start}", timeout=3000)
            q.wait_for_timeout(900)
            after, ink = q.evaluate(size), q.evaluate(INK)
            check(f"{name}: New Skribl with a shape picked starts over on that shape, in one tap",
                  ink == 0 and after != before and abs(after[0] - after[1]) < 2, f"was {before}, now {after}, ink {ink}")
            if name == "Pad":
                q.locator(".toast button, .toast-action").first.click(timeout=3000)
            else:
                q.evaluate("() => document.getElementById('clearUndo').click()")
            q.wait_for_timeout(700)
            undone, ink2 = q.evaluate(size), q.evaluate(INK)
            check(f"{name}: Undo brings back the drawing and its shape",
                  undone == before and ink2 > 0, f"shape {undone} (was {before}), ink {ink2}")

        def drafts():
            open_menu(q, btn)
            q.click("#openCloudDraftItem", timeout=3000)
            q.wait_for_timeout(800)
            d = q.evaluate("""() => { const s = document.getElementById('savedDraftsSheet'), n = document.getElementById('nameItem');
              const r = n.getBoundingClientRect(), at = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
              return { name: !!at && n.contains(at), files: s.querySelectorAll('.sdrafts-files .menu-item').length,
                       thumb: !!s.querySelector('.sdrafts-this-thumb img') }; }""")
            check(f"{name}: Your drafts shows this drawing (picture and name) and the .skribl file both ways",
                  d["name"] and d["files"] == 2 and d["thumb"], str(d))
            if not d["name"]:
                return
            q.click("#nameItem", timeout=3000)
            q.wait_for_timeout(700)
            nm = q.evaluate("() => ({ drawer: document.getElementById('nameShell').classList.contains('open'),"
                            " sheet: !document.getElementById('savedDraftsSheet').hidden })")
            check(f"{name}: the name opens the name drawer and puts the drafts sheet away", nm["drawer"] and not nm["sheet"], str(nm))

        for label, fn in (("the pages", pages), ("New Skribl", new_skribl), ("Your drafts", drafts)):
            # A fresh page each, so one part's break cannot leave the next in its state.
            q.close()
            q = c.new_page()
            q.on("pageerror", lambda e: errs.append(str(e)))
            browsing.goto(q, BASE, route)
            q.wait_for_timeout(800)
            q.evaluate("() => window.SkriblHints && window.SkriblHints.hide()")
            part(label, fn)
        check(f"{name}: no page errors", not errs, "; ".join(errs[:2]))
        c.close()

        # 3. How it works' tabs: the same pill
        c = b.new_context(**PHONE)
        q = c.new_page()
        browsing.goto(q, BASE, route)
        q.wait_for_timeout(800)
        q.evaluate("() => { window.SkriblHints && window.SkriblHints.hide(); openHelpDrawer(); }")
        q.wait_for_timeout(900)
        t = q.evaluate("""() => { const tabs = document.querySelector('.help-tabs'), on = document.getElementById('helpTabWatch');
          const pill = tabs.querySelector(':scope > .seg-slider'), p = pill.getBoundingClientRect(), o = on.getBoundingClientRect();
          return { pill: tabs.hasAttribute('data-pill') && Math.abs(p.left - o.left) < 2 && Math.abs(p.width - o.width) < 2,
                   bg: getComputedStyle(on).backgroundColor }; }""")
        check(f"{name}: How it works' tabs are a track of the same sliding pill, not a solid button",
              t["pill"] and t["bg"] in ("rgba(0, 0, 0, 0)", "transparent"), str(t))
        c.close()

    check("Pad and Flip show the same menu, tile for tile and row for row",
          orders.get("Pad") and orders.get("Pad") == orders.get("Flip"), f"Pad {orders.get('Pad')}, Flip {orders.get('Flip')}")
    b.close()

bad = [r for r in results if not r[0]]
print(f"\n{'=' * 62}\n{len(results) - len(bad)}/{len(results)} passed"
      + ("" if not bad else "  FAILURES: " + ", ".join(r[1] for r in bad)))
sys.exit(1 if bad else 0)
