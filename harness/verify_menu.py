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
     to the other editor. How it works opens Ask: one field, no tabs.
  4. PAGES. New opens its page with focus on Back; Escape comes back to the
     main page with focus on New; every opening starts on the main page.
  5. NEW SKRIBL, one tap after the shape: the drawing goes, the canvas takes
     the shape picked, and Undo brings back both the drawing and its shape.
  6. YOUR DRAFTS holds the name and the .skribl file both ways; the name opens
     the name drawer and puts the sheet away.
  7. TWO SETTINGS, TWO ICONS: the menu's Settings wears a gear, the header's
     sliders are named Tune on both editors.
  8. THE FIRST SAVE ASKS FOR A NAME, filled in and selected; backing out leaves
     the drawing unnamed and unsaved, one tap keeps the name and saves, and the
     next Save is quiet.
  9. THE MENU'S PAPER (the colour mock, B2): the sheet is solid, not glass,
     and every card's edge shows against it, light and dark. On B as first
     mocked, How it works' lilac fill met the lilac sheet with no line between
     (owner's screenshot); read from the pixels on each side of the edge.

Visible means painted: elementFromPoint inside the thing, not its rect.
"""
import math
import io
import os
import re
import sys

from assertions import make_check
import browsing

BASE = os.environ.get("SKRIBL_BASE", "http://127.0.0.1:5001")
results = []
check = make_check(results, detail_on_pass=False)

try:
    from playwright.sync_api import sync_playwright
    from PIL import Image
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
EDGE = """() => { const s = """ + SHEET + """, l = s.querySelector('.menu-list'), r = l.getBoundingClientRect(),
  cs = getComputedStyle(s); return {x: r.left, y: r.top + 32, blur: cs.backdropFilter, bg: cs.backgroundColor}; }"""
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
                if dev == "desk":
                    # The menu's room inside its edge (owner, after v324: the
                    # sheets mock, "All yes"): 6px put the switch nearly on it.
                    room = q.evaluate("""() => { const m = [...document.querySelectorAll('#menuSheet, #moreMenu')].find(e => e.getClientRects().length);
                      const s = m.querySelector('.menu-editor-seg').getBoundingClientRect(), r = m.getBoundingClientRect(), cs = getComputedStyle(m);
                      return { pad: cs.padding, top: Math.round(s.top - r.top - parseFloat(cs.borderTopWidth)) }; }""")
                    check(f"{name}, desk, {scheme}: the menu has 12px of room inside its edge, so the switch clears the top",
                          room["pad"] == "12px" and room["top"] >= 12, str(room))
                if dev == "phone":
                    # 9. the paper: solid, and the list's edge shows. At the
                    # phone's 2x, the pixel 3px outside the list (the sheet),
                    # its 1px border, and How it works' fill just inside.
                    e = q.evaluate(EDGE)
                    im = Image.open(io.BytesIO(q.screenshot())).convert("RGB")
                    X, Y = round(e["x"] * 2), round(e["y"] * 2)
                    out, rim, fill = im.getpixel((X - 6, Y)), im.getpixel((X, Y)), im.getpixel((X + 20, Y))
                    dist = lambda u, v: sum(abs(i - j) for i, j in zip(u, v))
                    solid = e["blur"] == "none" and e["bg"].startswith("rgb(")
                    check(f"{name}, {scheme}: the menu is solid paper, and How it works' card edge shows against it",
                          solid and max(dist(rim, out), dist(fill, out)) >= 30,
                          f"blur={e['blur']} bg={e['bg']} sheet={out} edge={rim} fill={fill}")
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
            pp = q.evaluate("""() => { const d = getComputedStyle(document.getElementById('savedDraftsSheet')), m = getComputedStyle(""" + SHEET + """);
              return { drafts: d.backgroundColor, menu: m.backgroundColor, blur: d.backdropFilter }; }""")
            check(f"{name}: Your drafts is on the menu's paper", pp["drafts"] == pp["menu"] and pp["blur"] == "none", str(pp))
            if not d["name"]:
                return
            q.click("#nameItem", timeout=3000)
            q.wait_for_timeout(700)
            nm = q.evaluate("() => ({ drawer: document.getElementById('nameShell').classList.contains('open'),"
                            " sheet: !document.getElementById('savedDraftsSheet').hidden })")
            check(f"{name}: the name opens the name drawer and puts the drafts sheet away", nm["drawer"] and not nm["sheet"], str(nm))

        def icons():
            ic = q.evaluate("""() => ({ gear: document.querySelector('#menuSettingsItem > svg').innerHTML,
              tune: document.querySelector('#tuneBtn svg').innerHTML,
              name: document.getElementById('tuneBtn').getAttribute('aria-label'),
              title: document.querySelector('#tunePanel .tune-title').textContent.trim() })""")
            check(f"{name}: Settings in the menu and the header's sliders wear different icons; the sliders are named Tune",
                  ic["gear"] != ic["tune"] and "circle" in ic["gear"] and ic["name"] == "Tune" and ic["title"] == "Tune",
                  f"same icon: {ic['gear'] == ic['tune']}, name {ic['name']!r}, title {ic['title']!r}")

        BOX = """() => { const i = document.getElementById('skriblName');
          return { open: document.getElementById('nameShell').classList.contains('open'), value: i.value,
                   selected: i.selectionEnd - i.selectionStart, label: document.getElementById('nameDone').textContent }; }"""
        TITLES = "() => SkriblSavedDrafts.list().then(xs => xs.map(x => x.title))"

        def first_save():
            scribble(q, cv)
            if name == "Pad":
                q.evaluate("() => { if (recording) document.getElementById('recordBtn').click(); }")
                q.wait_for_timeout(300)
            # Empty, or the date name a reopened drawing brings back: no name yet.
            was = q.evaluate("() => document.getElementById('skriblName').value")
            open_menu(q, btn)
            q.click("#saveCloudDraftItem", timeout=3000)
            q.wait_for_timeout(700)
            ask = q.evaluate(BOX)
            check(f"{name}: the first Save asks for a name, the date name filled in and selected, its button Save",
                  ask["open"] and ask["value"].startswith("Skribl") and ask["selected"] == len(ask["value"]) and ask["label"] == "Save",
                  str(ask))
            q.keyboard.press("Escape")
            q.wait_for_timeout(500)
            out = [q.evaluate(BOX), q.evaluate(TITLES)]
            check(f"{name}: backing out leaves the name as it was and saves nothing",
                  not out[0]["open"] and out[0]["value"] == was and out[1] == [], f"was {was!r}: {out}")
            open_menu(q, btn)
            q.click("#saveCloudDraftItem", timeout=3000)
            q.wait_for_timeout(700)
            q.click("#nameDone", timeout=3000)
            q.wait_for_timeout(1200)
            kept = q.evaluate(TITLES)
            check(f"{name}: one tap keeps the date name and saves", len(kept) == 1 and kept[0].startswith("Skribl"), str(kept))
            open_menu(q, btn)
            q.click("#saveCloudDraftItem", timeout=3000)
            q.wait_for_timeout(1200)
            again = [q.evaluate(BOX)["open"], q.evaluate(TITLES)]
            check(f"{name}: the next Save is quiet: no question, the same draft", not again[0] and again[1] == kept, str(again))

        for label, fn in (("the pages", pages), ("New Skribl", new_skribl), ("Your drafts", drafts),
                          ("the icons", icons), ("the first Save", first_save)):
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

        # 4. THE SWITCH GLIDES BEFORE IT GOES (owner's iPhone, after v323:
        # "never shows the button move, then boom you're in flip"). A tap on
        # the other editor puts the pill under it while this page is still
        # up, then the other editor arrives; and it was fetched ahead.
        c = b.new_context(**PHONE)
        # The arriving page says whether it came in by a cross-fade (KIND
        # TRANSITIONS, styles.css @view-transition): pagereveal carries one.
        c.add_init_script("window.addEventListener('pagereveal', (e) => { window.__faded = !!e.viewTransition; });")
        q = c.new_page()
        browsing.goto(q, BASE, route)
        q.wait_for_timeout(800)
        q.evaluate("() => window.SkriblHints && window.SkriblHints.hide()")
        other = "#flipBtn" if name == "Pad" else "#padBtn"
        there = q.evaluate("(s) => new URL(document.querySelector(s).href).pathname", other)
        try:
            q.wait_for_selector('link[rel="prefetch"][data-editor-ahead]', state="attached", timeout=8000)
            ahead = q.evaluate("() => new URL(document.querySelector('link[rel=\"prefetch\"][data-editor-ahead]').href).pathname")
        except Exception:
            ahead = None
        check(f"{name}: the other editor's page is fetched ahead, once this one has settled",
              ahead is not None and ahead.rstrip("/") == there.rstrip("/"), str(ahead))
        open_menu(q, btn)
        # A page that leaves at once takes this evaluation with it: that is
        # the failure this row exists for, said as one.
        try:
            glide = q.evaluate("""(sel) => new Promise(res => { const a = document.querySelector(sel), pill = a.parentElement.querySelector('.seg-slider');
                a.click();
                setTimeout(() => { const p = pill.getBoundingClientRect(), o = a.getBoundingClientRect();
                  res({ under: Math.abs((p.left + p.width / 2) - (o.left + o.width / 2)) < 4, path: location.pathname }); }, 265); })""", other)
        except Exception as e:
            glide = {"under": False, "path": "left at once: " + str(e)[:60]}
        try:
            q.wait_for_url(lambda u: u.split("?")[0].rstrip("/").endswith(there.rstrip("/")), timeout=5000)
            arrived = True
        except Exception:
            arrived = False
        check(f"{name}: a tap on the other editor slides the pill under it while this page is still up, then goes there",
              glide["under"] and glide["path"].rstrip("/") == route.rstrip("/") and arrived, f"{glide}, arrived {arrived}")
        q.wait_for_timeout(400)
        faded = q.evaluate("() => window.__faded") if arrived else None
        check(f"{name}: ...and the other editor fades in over this one, not a cut", faded is True, str(faded))
        c.close()

        # 3. How it works opens Ask (piece two, FUTURE.md 6p): the tabs it
        # had are gone, so the field is the first thing, empty, on Ask's home.
        c = b.new_context(**PHONE)
        q = c.new_page()
        browsing.goto(q, BASE, route)
        q.wait_for_timeout(800)
        q.evaluate("() => { window.SkriblHints && window.SkriblHints.hide(); openHelpDrawer(); }")
        q.wait_for_timeout(900)
        t = q.evaluate("""() => { const f = document.getElementById('helpSearch'), home = document.getElementById('helpWatch');
          return { tabs: document.querySelectorAll('#helpDrawer [role=tab]').length, field: !!f && f.offsetParent !== null && f.value === '',
                   home: !!home && !home.hidden, tour: !!document.getElementById('askTour') }; }""")
        check(f"{name}: How it works opens Ask: one empty field on Ask's home, no tabs",
              t["tabs"] == 0 and t["field"] and t["home"] and t["tour"], str(t))
        c.close()

        # 4. Your drafts' rows (owner's iPhone, after v324: "Weird border"). A
        # saved row is as wide as the cards above and below it, and a focused
        # row's ring is drawn INSIDE the row: the old ring sat 3px outside the
        # open button, shorter than the card, and the list's clip cut its left
        # edge. Read as a painted pixel just inside the row's left edge.
        for scheme in ("light", "dark"):
            c = b.new_context(color_scheme=scheme, **PHONE)
            q = c.new_page()
            browsing.goto(q, BASE, route)
            q.wait_for_timeout(800)
            q.evaluate("() => window.SkriblHints && window.SkriblHints.hide()")
            scribble(q, cv)
            open_menu(q, btn)
            q.click("#openCloudDraftItem", timeout=3000)
            q.wait_for_timeout(800)
            q.click("#savedDraftsSheet .sdrafts-save", timeout=3000)
            q.wait_for_timeout(900)
            if q.locator("#nameShell.open").count():
                q.click("#nameDone", timeout=3000)
                q.wait_for_timeout(900)
            if q.locator("#savedDraftsSheet").is_hidden():
                open_menu(q, btn)
                q.click("#openCloudDraftItem", timeout=3000)
            q.locator("#savedDraftsSheet .sdrafts-open").first.wait_for(timeout=5000)
            q.wait_for_timeout(600)
            w = q.evaluate("""() => { const s = document.getElementById('savedDraftsSheet');
              const wd = sel => { const e = s.querySelector(sel); return e ? [Math.round(e.getBoundingClientRect().left), Math.round(e.getBoundingClientRect().right)] : null; };
              return { row: wd('.sdrafts-row'), mine: wd('.sdrafts-this'), files: wd('.sdrafts-files') }; }""")
            check(f"{name} {scheme}: a saved draft's row is as wide as the cards above and below it",
                  w["row"] and w["row"] == w["mine"] == w["files"], str(w))
            # Keyboard focus: Tab onto the row's open button from the bin above it.
            q.focus("#savedDraftsSheet .sdrafts-row .sdrafts-del")
            q.keyboard.press("Shift+Tab")
            q.wait_for_timeout(300)
            r = q.evaluate("""() => { const o = document.querySelector('#savedDraftsSheet .sdrafts-open'), row = o.parentElement,
              b = row.getBoundingClientRect(), p = document.createElement('i');
              p.style.color = 'var(--focus-ring)'; document.body.appendChild(p); const ring = getComputedStyle(p).color; p.remove();
              return { fv: o.matches(':focus-visible'), x: b.left, y: b.top + b.height / 2, ring }; }""")
            im = Image.open(io.BytesIO(q.screenshot(clip={"x": r["x"], "y": r["y"] - 2, "width": 6, "height": 4}))).convert("RGB")
            px = im.getpixel((2, 4))   # 1 css px inside the row's left edge (2x)
            want = tuple(round(float(v)) for v in re.findall(r"[\d.]+", r["ring"])[:3])
            check(f"{name} {scheme}: a focused draft row's ring is painted inside the row, its left edge not cut",
                  r["fv"] and sum(abs(a - b_) for a, b_ in zip(px, want)) < 60, f"focus-visible {r['fv']}, pixel {px}, ring {want}")
            c.close()

    check("Pad and Flip show the same menu, tile for tile and row for row",
          orders.get("Pad") and orders.get("Pad") == orders.get("Flip"), f"Pad {orders.get('Pad')}, Flip {orders.get('Flip')}")
    b.close()

bad = [r for r in results if not r[0]]
print(f"\n{'=' * 62}\n{len(results) - len(bad)}/{len(results)} passed"
      + ("" if not bad else "  FAILURES: " + ", ".join(r[1] for r in bad)))
sys.exit(1 if bad else 0)
