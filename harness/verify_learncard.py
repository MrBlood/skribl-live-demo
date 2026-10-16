#!/usr/bin/env python3
"""The card on the button (lib/learncard.js; owner, after v323: the button
cards mock, "All yes"). Each row holds a promise, on the Pad and on Flip:

  1. HOLD a button on a touch screen about half a second: its card, with its
     name and its example. A quick tap is still a tap; a finger that moves
     is not a hold; and the lift after the card opens does not also press
     the button. Got it closes it and gives focus back to the button.
  2. HOLDING KEEPS ITS OLD JOBS: a Flip page held still lifts to be dragged
     (and no card opens), the slider's + held still repeats.
  3. REST on a button with a mouse about a second: the same card, "Move away
     to close", and it does close when the pointer leaves. The button's own
     tooltip names it first; it steps aside while the card shows.
  4. "?" NAMES EVERY BUTTON: a tag on each, painted beside its button; a tag
     opens that button's card; Escape puts them away. How it works' "Name
     every button" does the same.
  5. THE FIRST-TIME NOTE shows once: Got it, and a reload brings it no more.
  6. AUTOMATION NEVER MEETS IT unless it asks: without the flag, a hold
     opens nothing (so no other suite is ambushed).
  7. ONE CARD FOR BOTH EDITORS: Pen's card says the same on the Pad and Flip.

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
           ok: !!c.querySelector('.lc-ok'), hint: (c.querySelector('.lc-hint') || {}).textContent || '' }; }"""


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
                pen_lines[name] = card["line"]
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
            q.wait_for_timeout(450)
            early = q.evaluate(TIP)
            q.wait_for_timeout(900)
            card = q.evaluate(CARD)
            late = q.evaluate(TIP)
            check(f"{name}: resting on Eraser shows its tooltip, then grows into its card (Move away to close), the tooltip stepping aside",
                  not early[0] and early[1] and card and card["name"] == "Eraser" and card["hint"] == "Move away to close"
                  and card["painted"] and not late[1], f"early {early}, card {card}, then {late}")
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
            q.add_init_script("try { localStorage.setItem('skribl.hello.v1', '1'); } catch (e) {}")
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
                  first == "Hold any button to see what it does." and not again, f"{first} / again {again}")
            c.close()
        part("note", note)

        # 6. automation
        def auto():
            c, q = fresh(b, PHONE, route, force=False)
            cdp = c.new_cdp_session(q)
            touch_hold(q, cdp, "#penToolBtn", 700)
            check(f"{name}: without asking, automation never meets a card or the note",
                  not q.evaluate("() => !!document.querySelector('.lc-card, .lc-note')"))
            c.close()
        part("automation", auto)

    check("Pen's card says the same on the Pad and Flip", len(pen_lines) == 2 and len(set(pen_lines.values())) == 1, str(pen_lines))
    b.close()

bad = [r for r in results if not r[0]]
print(f"\n{'=' * 62}\n{len(results) - len(bad)}/{len(results)} passed"
      + ("" if not bad else "  FAILURES: " + ", ".join(r[1] for r in bad)))
sys.exit(1 if bad else 0)
