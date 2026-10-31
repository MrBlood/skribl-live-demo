#!/usr/bin/env python3
"""The card on the button (lib/learncard.js; owner, after v323: the button
cards mock, "All yes"). Each row holds a promise, on the Pad and on Flip:

  1. HOLD a button on a touch screen about half a second: its card, with its
     name and its example. A quick tap is still a tap; a finger that moves
     is not a hold; and the lift after the card opens does not also press
     the button. Got it closes it and gives focus back to the button.
  2. HOLDING KEEPS ITS OLD JOBS: a Flip page held still lifts to be dragged
     (and no card opens), the slider's + held still repeats.
  3. REST on a button with a mouse two seconds: the same card, "Move away
     to close", and it does close when the pointer leaves. The button's own
     tooltip names it first, and alone for a while: at a second and a half
     there is still no card (the owner, after v327: it came too quickly,
     at one). It steps aside while the card shows.
  4. "?" NAMES EVERY BUTTON: a tag on each, painted beside its button; a tag
     opens that button's card; Escape puts them away. How it works' "Name
     every button" does the same.
  5. THE FIRST-TIME NOTE shows once: Got it, and a reload brings it no more.
  6. AUTOMATION NEVER MEETS IT unless it asks: without the flag, a hold
     opens nothing (so no other suite is ambushed).
  7. ONE CARD FOR BOTH EDITORS: Pen's card says the same on the Pad and Flip.
  9. FLIP'S TRAY: every tool in it holds its card (the tray's own seven with
     their clip, 4:3), the tray stays open under it and after Got it, and a
     tool used from the tray holds the same card from its place in the bar.
 10. THE DRAW DRAWER'S SIX: the Eyedropper, Recolor and the four tiles hold
     their cards in the words the owner said yes to, clear of their buttons;
     the hold presses nothing and a quick tap still does; resting on a desk
     grows the card, and ? names all six.

Touch is real touch (CDP touch events), so the browser makes the pointer
events a finger would. Visible means painted: elementFromPoint.
"""
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
EDITORS = (("Pad", "/skribl-pad"), ("Flip", "/flip"))
FORCE = "window.__skriblLearnForce = true;"

TIP = """() => { const t = document.querySelector('.skribl-tip'); const tipShown = !!t && !t.hidden && getComputedStyle(t).display !== 'none';
  return [!!document.querySelector('.lc-card'), tipShown]; }"""
CARD = """() => { const c = document.querySelector('.lc-card'); if (!c) return null;
  const r = c.getBoundingClientRect(), at = document.elementFromPoint(r.left + r.width / 2, r.top + 30);
  return { name: c.querySelector('.lc-t').textContent, line: c.querySelector('.lc-line').textContent,
           painted: !!at && c.contains(at), example: !!c.querySelector('.lc-stage, .lc-phone'),
           ok: !!c.querySelector('.lc-ok'), hint: (c.querySelector('.lc-hint') || {}).textContent || '',
           rows: [...c.querySelectorAll('.lc-do > div')].map(d => [d.querySelector('dt').textContent, d.querySelector('dd').textContent]),
           rowsPainted: [...c.querySelectorAll('.lc-do dt')].every(e => { const q = e.getBoundingClientRect(), a = document.elementFromPoint(q.left + 4, q.top + q.height / 2); return !!a && e.contains(a); }) }; }"""


def center(q, sel):
    b = q.locator(sel).first.bounding_box()
    return b["x"] + b["width"] / 2, b["y"] + b["height"] / 2


def touch_hold(q, cdp, sel, ms, move=0):
    x, y = center(q, sel)
    cdp.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [{"x": x, "y": y}]})
    if move:
        q.wait_for_timeout(120)
        cdp.send("Input.dispatchTouchEvent", {"type": "touchMove", "touchPoints": [{"x": x + move, "y": y}]})
    q.wait_for_timeout(ms)
    cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
    q.wait_for_timeout(250)


def fresh(b, opts, route, force=True, scheme="light"):
    c = b.new_context(color_scheme=scheme, **opts)
    if force:
        c.add_init_script(FORCE + "try { localStorage.setItem('skribl.learncard.note.v1', '1'); } catch (e) {}")
    q = c.new_page()
    browsing.goto(q, BASE, route)
    q.wait_for_timeout(900)
    q.evaluate("() => window.SkriblHints && window.SkriblHints.hide()")
    return c, q


pen_lines = {}
with sync_playwright() as p:
    b = p.chromium.launch()
    for name, route in EDITORS:
        print(f"\n{name.upper()}")

        def part(label, fn):
            try:
                fn()
            except Exception as e:
                check(f"{name}: {label} ran to the end", False, repr(e)[:200])

        # 1. hold, tap, move, lift
        def hold():
            c, q = fresh(b, PHONE, route)
            cdp = c.new_cdp_session(q)
            touch_hold(q, cdp, "#penToolBtn", 700)
            card = q.evaluate(CARD)
            check(f"{name}: holding Pen opens its card, painted, with its example and Got it",
                  card and card["name"] == "Pen" and card["painted"] and card["example"] and card["ok"], str(card))
            if card:
                pen_lines[name] = card["line"] + " | " + str(card["rows"])
            # WHAT A TAP DOES (owner: Pen "opens a drawer but it's not
            # mentioned what a fast tap does"): its own row, painted.
            check(f"{name}: Pen's card says what a tap and a sideways drag do, each its own painted row",
                  card and [r[0] for r in card["rows"]] == ["Tap again", "Drag sideways"]
                  and "Colour" in card["rows"][0][1] and card["rowsPainted"], str(card and card["rows"]))
            q.click(".lc-card .lc-ok")
            q.wait_for_timeout(200)
            gone = q.evaluate("() => [!document.querySelector('.lc-card'), document.activeElement && document.activeElement.id]")
            check(f"{name}: Got it closes the card and gives focus back to Pen", gone[0] and gone[1] == "penToolBtn", str(gone))
            # a quick tap is a tap
            touch_hold(q, cdp, "#eraserToolBtn", 80)
            tap = q.evaluate("() => [!!document.querySelector('.lc-card'), document.getElementById('eraserToolBtn').classList.contains('active') || document.getElementById('eraserToolBtn').getAttribute('aria-pressed') === 'true']")
            check(f"{name}: a quick tap on Eraser picks the eraser and opens no card", not tap[0] and tap[1], str(tap))
            # the lift after a card is not a press
            touch_hold(q, cdp, "#penToolBtn", 700)
            lift = q.evaluate("() => [!!document.querySelector('.lc-card'), document.getElementById('eraserToolBtn').classList.contains('active') || document.getElementById('eraserToolBtn').getAttribute('aria-pressed') === 'true']")
            check(f"{name}: lifting after Pen's card opens does not press Pen (the eraser stays picked)", lift[0] and lift[1], str(lift))
            q.evaluate("() => window.SkriblLearnCard.close()")
            # a finger that moves is not a hold
            touch_hold(q, cdp, "#penToolBtn", 700, move=30)
            check(f"{name}: a finger that moves while pressing opens no card",
                  not q.evaluate("() => !!document.querySelector('.lc-card')"))
            c.close()
        part("hold", hold)

        # 2. old jobs
        def jobs():
            c, q = fresh(b, PHONE, route)
            cdp = c.new_cdp_session(q)
            if name == "Flip":
                # a page moves only when there is another page to move past
                q.tap("#addblank")
                q.wait_for_timeout(400)
                q.wait_for_selector("#strip .frame", state="visible")
                x, y = center(q, "#strip .frame")
                cdp.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [{"x": x, "y": y}]})
                q.wait_for_timeout(700)
                lifted = q.evaluate("() => [document.querySelector('#strip .frame').classList.contains('dragging'), !!document.querySelector('.lc-card')]")
                cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
                q.wait_for_timeout(300)
                check("Flip: holding a page still lifts it to move, and opens no card", lifted[0] and not lifted[1], str(lifted))
            c.close()
            # the slider's + is a desk control on the Pad (a finger drags the
            # slider; Flip's sliders have no - and +); held, it repeats
            if name == "Flip":
                return
            c, q = fresh(b, DESK, route)
            q.evaluate("() => document.getElementById('penToolBtn').click()")   # Pen is picked: a click opens its drawer
            q.wait_for_timeout(500)
            # The size slider is in the Size tile's choices since the draw
            # drawer's four tiles (#609), so the tile opens first.
            q.click(".dp-tile[data-dp=size]")
            q.wait_for_timeout(500)
            plus = q.evaluate("() => { const b = [...document.querySelectorAll('.slider-nudge-btn')].find(e => e.getClientRects().length && /increase|\\+|more/i.test((e.getAttribute('aria-label') || '') + e.textContent));"
                              " if (!b) return null; const inp = b.closest('.slider-nudge-wrap').parentElement.querySelector('input[type=range]'); b.id = 'lcPlus'; return inp ? inp.value : null; }")
            if plus is None:
                check(f"{name}: the slider's + is there to hold", False, "no visible + beside a slider")
            else:
                x, y = center(q, "#lcPlus")
                q.mouse.move(x, y); q.mouse.down(); q.wait_for_timeout(1300); q.mouse.up(); q.wait_for_timeout(200)
                after = q.evaluate("() => [document.querySelector('#lcPlus').closest('.slider-nudge-wrap').parentElement.querySelector('input[type=range]').value, !!document.querySelector('.lc-card')]")
                check(f"{name}: holding the slider's + still repeats, and opens no card",
                      float(after[0]) - float(plus) >= 2 * 1 and not after[1], f"{plus} -> {after}")
            c.close()
        part("old jobs", jobs)

        # 3. rest
        def rest():
            c, q = fresh(b, DESK, route)
            x, y = center(q, "#eraserToolBtn")
            q.mouse.move(x, y)
            t0 = q.evaluate("() => performance.now()")
            q.wait_for_timeout(450)
            early = q.evaluate(TIP)
            q.wait_for_function("(t) => performance.now() - t >= 1500", arg=t0)
            still = q.evaluate("(t) => [!!document.querySelector('.lc-card'), Math.round(performance.now() - t)]", t0)
            q.wait_for_function("(t) => performance.now() - t >= 2400", arg=t0)
            card = q.evaluate(CARD)
            late = q.evaluate(TIP)
            check(f"{name}: resting on Eraser shows its tooltip, alone at a second and a half, then grows into its card "
                  "by two and a half (Move away to close), the tooltip stepping aside",
                  not early[0] and early[1] and not still[0] and card and card["name"] == "Eraser" and card["hint"] == "Move away to close"
                  and card["painted"] and not late[1], f"early {early}, a card at {still[1]} ms: {still[0]}, card {card}, then {late}")
            q.mouse.move(40, 300)   # well clear of the button and of its card
            q.wait_for_timeout(600)
            after = q.evaluate("() => !document.querySelector('.lc-card')")
            check(f"{name}: moving away closes it", after)
            c.close()
        part("rest", rest)

        # 4. names
        def names():
            c, q = fresh(b, DESK, route)
            q.keyboard.press("Shift+Slash")
            q.wait_for_timeout(300)
            t = q.evaluate("""() => [...document.querySelectorAll('.lc-tag')].map(t => { const r = t.getBoundingClientRect(), at = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
                                return [t.textContent, !!at && t.contains(at)]; })""")
            want = {"Pen", "Eraser", "Undo", "Redo", "Photo and music", "Tune", "Menu"}
            check(f"{name}: ? puts a painted name tag on every button ({len(t)})",
                  want <= {x[0] for x in t} and all(x[1] for x in t), str(t))
            q.locator(".lc-tag", has_text="Tune").click()
            q.wait_for_timeout(300)
            card = q.evaluate(CARD)
            check(f"{name}: a tag opens that button's card, and the tags go", card and card["name"] == "Tune"
                  and not q.evaluate("() => !!document.querySelector('.lc-tag')"), str(card))
            q.keyboard.press("Escape")
            q.wait_for_timeout(200)
            check(f"{name}: Escape closes the card", not q.evaluate("() => !!document.querySelector('.lc-card')"))
            q.evaluate("() => openHelpDrawer()")
            q.wait_for_timeout(700)
            q.click("#learnNames")
            q.wait_for_timeout(900)
            n = q.evaluate("() => [document.getElementById('helpDrawer').hidden, document.querySelectorAll('.lc-tag').length]")
            check(f"{name}: How it works' Name every button closes How it works and names every button", n[0] and n[1] >= 6, str(n))
            c.close()
        part("names", names)

        # 5. the first-time note, once
        def note():
            c = b.new_context(**PHONE)
            c.add_init_script(FORCE)
            q = c.new_page()
            # a first-use hint up when the note would come (Pad shows none of its own on a first open)
            q.add_init_script("addEventListener('load', () => setTimeout(() => window.SkriblHints && SkriblHints.show('lcTestHint', 'A first-use hint'), 300));")
            browsing.goto(q, BASE, route)
            q.wait_for_timeout(2200)
            # one welcome at a time: with a first-use hint up, the note waits
            both = q.evaluate("() => !!document.querySelector('.lc-note') && [...document.querySelectorAll('.skribl-hint')].some(h => !h.hidden && h.getClientRects().length)")
            check(f"{name}: the note never shows while a first-use hint is up", not both)
            q.evaluate("() => window.SkriblHints && window.SkriblHints.hide()")
            q.wait_for_timeout(2000)
            first = q.evaluate("() => { const n = document.querySelector('.lc-note'); return n && n.querySelector('.lc-line').textContent; }")
            if first:
                q.click(".lc-note .lc-ok")
            q.reload()
            q.wait_for_timeout(2200)
            again = q.evaluate("() => !!document.querySelector('.lc-note')")
            check(f"{name}: the first-time note shows once ('{first}'), and Got it is for good",
                  first == "Hold any button to see what it does. New here? There\u2019s a little book in How it works."
                  and not again, f"{first} / again {again}")
            c.close()
        part("note", note)

        # 5b. the note never covers a sheet: How it works opens over it, and
        # its little book's Draw along stays in reach. verify_words met the
        # note on top of that button once the hello stopped standing in for
        # it on phones; what is painted is asked, never a rect.
        def under():
            c = b.new_context(**PHONE)
            c.add_init_script(FORCE)
            q = c.new_page()
            browsing.goto(q, BASE, route)
            q.wait_for_timeout(1200)
            q.evaluate("() => document.querySelector('.lc-note') || window.SkriblLearnCard.note(true)")
            q.evaluate("() => openHelpDrawer()")
            q.wait_for_timeout(700)
            at = q.evaluate("""() => { const n = document.querySelector('.lc-note'); if (!n) return 'no note';
                const r = n.getBoundingClientRect(), e = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
                return !e ? 'nothing' : e.closest('.lc-note') ? 'the note' : e.closest('#helpDrawer') ? 'How it works' : (e.id || e.className || e.tagName); }""")
            q.click("#askTour")
            q.wait_for_timeout(1200)
            q.click("#bkNext")
            q.wait_for_timeout(400)
            along = q.evaluate("""() => { const a = document.getElementById('bkAlong'); if (!a || a.hidden) return 'no button';
                const r = a.getBoundingClientRect(), e = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
                return !!e && a.contains(e) ? 'in reach' : !e ? 'nothing' : e.closest('.lc-note') ? 'under the note' : (e.className || e.tagName); }""")
            check(f"{name}: the first-time note never covers a sheet: How it works opens over it, and its book's "
                  "Draw along stays in reach", at == "How it works" and along == "in reach",
                  f"at the note's middle with How it works open: {at}; Draw along: {along}")
            c.close()
        part("note under sheets", under)

        # 6. automation
        def auto():
            c, q = fresh(b, PHONE, route, force=False)
            cdp = c.new_cdp_session(q)
            touch_hold(q, cdp, "#penToolBtn", 700)
            check(f"{name}: without asking, automation never meets a card or the note",
                  not q.evaluate("() => !!document.querySelector('.lc-card, .lc-note')"))
            c.close()
        part("automation", auto)

        # 8. EVERY BUTTON THAT OPENS SOMETHING SAYS WHAT A TAP DOES: the
        # buttons whose tap opens a drawer, a picker, a tray or a sheet.
        def taps():
            c, q = fresh(b, PHONE, route)
            missing, seen = [], []
            for sel in ("#penToolBtn", "#eraserToolBtn", "#shapeToolBtn", "#toolMoreBtn", "#mediaOpenBtn",
                        "#postBtn", "#tuneBtn", "#menuBtn", "#moreBtn"):
                if not q.evaluate("(s) => { const e = document.querySelector(s); return !!e && !!e.getClientRects().length; }", sel):
                    continue
                seen.append(sel)
                q.evaluate("(s) => window.SkriblLearnCard.open(s)", sel)
                q.wait_for_timeout(250)
                card = q.evaluate(CARD)
                if not card or not any(r[0].startswith("Tap") for r in card["rows"]):
                    missing.append(f"{sel}: {card and card['rows']}")
                q.evaluate("() => window.SkriblLearnCard.close()")
            check(f"{name}: every button that opens something says on its card what a tap does ({len(seen)} on this page)",
                  len(seen) >= 6 and not missing, "; ".join(missing))
            c.close()
        part("tap rows", taps)

        # 9. FLIP'S TRAY (owner: "make sure you look at ALL the tools because
        # I noticed the tools on flip's ^ menu don't have them"): every tool
        # in it holds its card, the seven of the tray's own with their How it
        # works clip filling the card's 4:3 stage. The tray stays open under
        # the card and after Got it (a tap on a card is the card's own), with
        # the tool's place in focus, and the hold picks no tool. In the tray a
        # tap only picks, so Pen's and the Eraser's rows about their bar
        # buttons are left out there; the ones whose tap opens something say
        # what it opens. A tool used from the tray takes a place in the bar,
        # and holds the same card there; on a desk, resting does the same.
        def tray():
            if name != "Flip":
                return
            TRAY = """() => [...document.querySelectorAll('.tool-tray-btn')].some(e => { const r = e.getBoundingClientRect();
                return r.width && document.elementFromPoint(r.left + 6, r.top + 6) === e; })"""
            CLIP = """() => { const st = document.querySelector('.lc-card .lc-clip'), v = st && st.querySelector('video'); if (!v) return null;
                const sr = st.getBoundingClientRect(), vr = v.getBoundingClientRect(), bw = parseFloat(getComputedStyle(st).borderLeftWidth);
                return { src: v.getAttribute('src') || v.poster || '', ratio: +(sr.width / sr.height).toFixed(3),
                         off: +Math.max(Math.abs(vr.width - (sr.width - 2 * bw)), Math.abs(vr.height - (sr.height - 2 * bw))).toFixed(2) }; }"""
            CLIPS = {"select": "Select", "liquify": "Liquify", "smudge": "Smudge", "blur": "Blur", "fill": "Fill",
                     "stamp": "Stamps", "artmove": "Artwork"}
            c, q = fresh(b, PHONE, route)
            cdp = c.new_cdp_session(q)
            q.tap("#toolMoreBtn")
            q.wait_for_timeout(600)
            seen, wrong, clips, kept = {}, [], [], []
            for tool, title in [("pen", "Pen"), ("eraser", "Eraser"), ("shape", "Shape")] + list(CLIPS.items()):
                if not q.evaluate(TRAY):
                    q.tap("#toolMoreBtn")
                    q.wait_for_timeout(600)
                touch_hold(q, cdp, f'.tool-tray-btn[data-tool="{tool}"]', 700)
                card, clip = q.evaluate(CARD), q.evaluate(CLIP)
                seen[tool] = card and card["rows"]
                if not (card and card["name"] == title and card["painted"] and card["example"] and card["ok"] and card["rowsPainted"]):
                    wrong.append(f"{tool}: {card}")
                if tool in CLIPS and not (clip and f"/{tool}-" in clip["src"] and abs(clip["ratio"] - 4 / 3) < 0.01 and clip["off"] <= 1):
                    clips.append(f"{tool}: {clip}")
                if card:
                    q.tap(".lc-card .lc-ok")
                    q.wait_for_timeout(300)
                    after = q.evaluate("(t) => [!document.querySelector('.lc-card'), document.activeElement && document.activeElement.getAttribute('data-tool'), "
                                       "((document.querySelector('.tool-tray-btn.active') || {}).dataset || {}).tool]", tool)
                    kept.append([tool, q.evaluate(TRAY)] + after)
            check("Flip: every tool in the tray holds its own card, named, painted, with its example and Got it",
                  len(seen) == 10 and not wrong, "; ".join(wrong) or str(sorted(seen)))
            check("Flip: the tray's own seven show their How it works clip, filling the card's 4:3 stage",
                  not clips, "; ".join(clips))
            check("Flip: Got it leaves the tray open with that tool in focus, and holding picked no tool (the pen stays)",
                  len(kept) == 10 and all(k[1] and k[2] and k[3] == k[0] and k[4] == "pen" for k in kept), str(kept))
            check("Flip: in the tray Pen's and the Eraser's cards leave out their bar buttons' rows, and Shape, Stamps "
                  "and Artwork say what a tap opens",
                  seen.get("pen") == [] and seen.get("eraser") == []
                  and all(seen.get(t) and seen[t][0][0] == "Tap" for t in ("shape", "stamp", "artmove")), str(seen))
            # used from the tray, a tool takes a place in the bar: the same card there
            if not q.evaluate(TRAY):
                q.tap("#toolMoreBtn")
                q.wait_for_timeout(600)
            q.tap('.tool-tray-btn[data-tool="liquify"]')
            q.wait_for_timeout(600)
            touch_hold(q, cdp, "#liquifyToolBtn", 700)
            card = q.evaluate(CARD)
            check("Flip: a tool used from the tray holds the same card from its place in the bar",
                  card and card["name"] == "Liquify" and card["painted"] and card["rows"] == seen.get("liquify"), str(card))
            c.close()
            c, q = fresh(b, DESK, route)
            q.click("#toolMoreBtn")
            q.wait_for_timeout(600)
            x, y = center(q, '.tool-tray-btn[data-tool="fill"]')
            q.mouse.move(x, y)
            q.wait_for_timeout(2600)
            card = q.evaluate(CARD)
            q.mouse.move(40, 300)
            q.wait_for_timeout(700)
            gone = q.evaluate("() => !document.querySelector('.lc-card')")
            check("Flip: on a desk, resting on a tool in the tray grows its card (Move away to close), and moving away "
                  "closes it with the tray still open",
                  card and card["name"] == "Fill" and card["hint"] == "Move away to close" and gone and q.evaluate(TRAY),
                  f"{card}; gone {gone}")
            c.close()
        part("the tray", tray)

        # 10. THE DRAW DRAWER'S SIX (owner, after #691: "shouldn't these have
        # help cards?"; the words mock, "All yes"; FUTURE.md 6aa). The two
        # colour tools and the four tiles each hold their card, in the words
        # the owner said yes to, Flip's two differences included (Recolor
        # stops at the change; Feel holds Draw-on): painted, whole on the
        # screen, clear of its own button, which wears the ring. The hold
        # presses nothing: no eyedropper armed, no Recolor, no tile's choices
        # open, the drawer still up. A quick tap still does its job. On a
        # desk, resting does the same, and ? names all six, none on another.
        def drawer():
            DRAWER = "() => openDrawer('draw')" if name == "Pad" else "() => _flipDrawerCtl.open('draw')"
            SIX = [("#eyedropperBtn", "Eyedropper", "Take a colour from your drawing to draw with.",
                    [["Tap", "A lens lands on your drawing"], ["Drag", "Move the lens onto a colour"], ["Let go", "Your pen takes that colour"]]),
                   ("#recolorBtn", "Recolor", "Give lines you’ve drawn your pen’s colour." + ("" if name == "Flip" else " The replay shows them change."),
                    [["Tap a line", "It takes your pen’s colour"], ["Hold", "A lens, to aim at a thin line"],
                     ["Drag across", "Every line you cross"], ["Done", "Back to the pen"]]),
                   ('#drawTiles .dp-tile[data-dp="brush"]', "Brush", "The kind of line you draw, from a clean pen to soft air.",
                    [["Tap", "Pen, Marker, Pencil or Air"]]),
                   ('#drawTiles .dp-tile[data-dp="size"]', "Size", "How thick your line is, and how strong its colour.",
                    [["Tap", "Size and opacity"], ["Quicker", "Drag sideways on Pen"]]),
                   ('#drawTiles .dp-tile[data-dp="feel"]', "Feel", "Steadier lines, and lines that widen as you press with a stylus.",
                    [["Tap", "Smoothing, pressure, Draw-on" if name == "Flip" else "Smoothing and pressure"]]),
                   ('#drawTiles .dp-tile[data-dp="eraser"]', "Eraser size", "How wide the eraser rubs. It grows and shrinks with your pen.",
                    [["Tap", "2×, 3× or 5× the pen"]])]
            PLACE = """(sel) => { const c = document.querySelector('.lc-card'), b = document.querySelector(sel); if (!c) return null;
                const R = c.getBoundingClientRect(), B = b.getBoundingClientRect();
                const words = [...c.querySelectorAll('.lc-t, .lc-line, .lc-do dt, .lc-do dd, .lc-more, .lc-ok, .lc-hint')];
                return { whole: R.left >= 0 && R.top >= 0 && R.right <= innerWidth && R.bottom <= innerHeight,
                         clear: R.right <= B.left || B.right <= R.left || R.bottom <= B.top || B.bottom <= R.top,
                         ringed: b.classList.contains('lc-target'),
                         painted: words.every(e => { const r = e.getBoundingClientRect(), a = document.elementFromPoint(r.left + Math.min(6, r.width / 2), r.top + r.height / 2);
                           return !!a && e.contains(a); }),
                         cut: words.filter(e => e.scrollWidth > e.clientWidth + 1).map(e => e.textContent) }; }"""
            # A button is pressed where it is once it has stopped moving: a
            # tile's choices take the phone's drawer to its full height, and
            # the drawer glides there (a tap read mid-glide missed Flip's
            # Eyedropper).
            STILL = """(sel) => new Promise(done => { const e = document.querySelector(sel); let last = '', n = 0; const t0 = performance.now();
                (function tick() { const r = e.getBoundingClientRect(), k = r.left + ',' + r.top; n = k === last ? n + 1 : 0; last = k;
                  if (n >= 3 || performance.now() - t0 > 2000) done(); else requestAnimationFrame(tick); })(); })"""

            def press(q, cdp, sel, ms):
                q.locator(sel).first.scroll_into_view_if_needed()
                q.evaluate(STILL, sel)
                touch_hold(q, cdp, sel, ms)
            SIDE = """() => ({ armed: document.getElementById('eyedropperBtn').getAttribute('aria-pressed') === 'true',
                recolor: document.body.classList.contains('recoloring'),
                choices: [...document.querySelectorAll('#drawTiles .dp-panel')].filter(p => !p.hidden).map(p => p.dataset.dp),
                drawer: !document.getElementById('drawPanel').hidden })"""
            # Whatever a hold set off is put back before the next button, so
            # each row reads its own button: a pressed Eyedropper veils the
            # drawer, and every later button would be gone with it.
            def put_back(q):
                side = q.evaluate(SIDE)
                if side["armed"] or side["recolor"]:
                    q.keyboard.press("Escape")
                    q.wait_for_timeout(300)
                for k in q.evaluate(SIDE)["choices"]:
                    q.evaluate("(k) => document.querySelector('#drawTiles .dp-tile[data-dp=\"' + k + '\"]').click()", k)
                    q.wait_for_timeout(300)
                if q.evaluate(SIDE)["drawer"] is False:
                    q.evaluate(DRAWER)
                    q.wait_for_timeout(700)
            # Each card's example, by what it loads: a drawing from How it
            # works, or a phone clip in this theme (its poster and its video).
            EXAMPLE = {"Eyedropper": "clips/eyedropper-", "Recolor": "demos/recolor.json", "Brush": "demos/brushes.json",
                       "Size": "clips/size-", "Feel": "clips/feel-", "Eraser size": "demos/eraser.json"}
            c, q = fresh(b, PHONE, route)
            got = []
            q.on("response", lambda r: got.append((r.url.split("?")[0], r.status)))
            cdp = c.new_cdp_session(q)
            q.evaluate(DRAWER)
            q.wait_for_timeout(700)
            pressed = {}
            for sel, nm, line, rows in SIX:
                got.clear()
                press(q, cdp, sel, 700)
                card, at = q.evaluate(CARD), q.evaluate(PLACE, sel)
                for _ in range(25):     # a drawing waits on the player, fetched once
                    shows = sorted({u.split("/help/")[1] for u, st in got if st < 400 and ("/help/demos/" in u or "/help/clips/" in u)})
                    if any(u.startswith(EXAMPLE[nm]) for u in shows):
                        break
                    q.wait_for_timeout(100)
                q.evaluate("() => window.SkriblLearnCard.close()")
                q.wait_for_timeout(200)
                side = q.evaluate(SIDE)
                if side["armed"] or side["recolor"] or side["choices"] or not side["drawer"]:
                    pressed[nm] = side
                    put_back(q)
                check(f"{name}: holding {nm} in the draw drawer opens its card in the words said yes to, painted, whole on the screen and clear of {nm}",
                      bool(card) and bool(at) and card["name"] == nm and card["line"] == line and card["rows"] == rows
                      and card["painted"] and card["rowsPainted"]
                      and at["whole"] and at["clear"] and at["ringed"] and at["painted"] and not at["cut"], f"{card}; {at}")
                kind, stem = EXAMPLE[nm].split("/")
                check(f"{name}: ...and {nm}'s card shows its own example, the {stem.replace('.json', '').rstrip('-')} {'drawing' if kind == 'demos' else 'clip'}",
                      bool(card) and card["example"] and any(u.startswith(EXAMPLE[nm]) for u in shows), f"example {card and card['example']}; loaded {shows}")
            check(f"{name}: ...and none of the six holds presses its button: no eyedropper armed, no Recolor, no tile's choices, the drawer still up",
                  not pressed, str(pressed))
            # A quick tap is still a tap: the Size tile opens its choices, the
            # Eyedropper arms (last: arming veils the drawer).
            press(q, cdp, '#drawTiles .dp-tile[data-dp="size"]', 80)
            tile = q.evaluate(SIDE)["choices"]
            q.evaluate("() => document.querySelector('#drawTiles .dp-tile[data-dp=\"size\"]').click()")
            q.wait_for_timeout(400)
            press(q, cdp, "#eyedropperBtn", 80)
            armed = q.evaluate(SIDE)["armed"]
            nocard = not q.evaluate("() => !!document.querySelector('.lc-card')")
            check(f"{name}: a quick tap is still a tap: Size opens its choices, the Eyedropper arms, and no card opens",
                  tile == ["size"] and armed and nocard, f"choices {tile}, armed {armed}, no card {nocard}")
            c.close()
            # On a desk: resting on a tile grows its card; ? names the six.
            c, q = fresh(b, DESK, route)
            q.evaluate(DRAWER)
            q.wait_for_timeout(700)
            x, y = center(q, '#drawTiles .dp-tile[data-dp="size"]')
            q.mouse.move(x - 30, y - 40)
            q.mouse.move(x, y, steps=4)
            q.wait_for_timeout(2500)
            card = q.evaluate(CARD)
            q.mouse.move(40, 300)
            q.wait_for_timeout(600)
            gone = q.evaluate("() => !document.querySelector('.lc-card')")
            check(f"{name}: on a desk, resting on the Size tile grows its card (Move away to close), and moving away closes it",
                  bool(card) and card["name"] == "Size" and card["hint"] == "Move away to close" and card["painted"] and gone, f"{card}; gone {gone}")
            q.keyboard.press("Shift+Slash")
            q.wait_for_timeout(300)
            tags = q.evaluate("""() => { const t = [...document.querySelectorAll('.lc-tag')].map(e => { const r = e.getBoundingClientRect(),
                  a = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2); return { n: e.textContent, r: [r.left, r.top, r.right, r.bottom], painted: !!a && e.contains(a) }; });
                const over = []; t.forEach((x, i) => t.slice(i + 1).forEach(y => { if (x.r[0] < y.r[2] && y.r[0] < x.r[2] && x.r[1] < y.r[3] && y.r[1] < x.r[3]) over.push(x.n + '/' + y.n); }));
                return { names: t.map(x => x.n), unpainted: t.filter(x => !x.painted).map(x => x.n), over }; }""")
            six = {"Eyedropper", "Recolor", "Brush", "Size", "Feel", "Eraser size"}
            check(f"{name}: with the drawer open, ? names the six too, each tag painted and none on another",
                  six <= set(tags["names"]) and not tags["unpainted"] and not tags["over"], str(tags))
            c.close()
        part("the draw drawer's six", drawer)

    check("Pen's card says the same on the Pad and Flip", len(pen_lines) == 2 and len(set(pen_lines.values())) == 1, str(pen_lines))
    b.close()

bad = [r for r in results if not r[0]]
print(f"\n{'=' * 62}\n{len(results) - len(bad)}/{len(results)} passed"
      + ("" if not bad else "  FAILURES: " + ", ".join(r[1] for r in bad)))
sys.exit(1 if bad else 0)
