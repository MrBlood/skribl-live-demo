#!/usr/bin/env python3
"""The little book and Draw along (lib/book.js, lib/drawalong.js; owner,
after v323: the little book mock, "Yes to all as long as it's kind"). Each
row holds a promise, on the Pad and on Flip:

  1. IT NEVER OPENS BY ITSELF. Ask's New here? opens it, on page 1, its
     example playing, focus on Next.
  2. A SHEET THAT FITS ITS PAGE on a phone (the drawing stays in view above
     it); a dialog in the middle on a desk.
  3. THE PAGES TURN by Next, Back, a swipe and the arrow keys; the dots say
     where you are; Draw along is on a drawing page and only there; the
     last page says Start drawing and leaves you drawing.
  4. CLOSING IS KIND: Escape or the x goes back to How it works.
  5. DRAW ALONG lays the drawing's strokes on your canvas, the pill under
     the header; any real stroke counts and the next one shows, a tap does
     not; Skip moves on; Done and Escape put it away.
  6. THE GUIDE IS NEVER THE DRAWING: it is its own layer, and after Done the
     drawing holds what you drew and nothing of the guide.

Touch is real touch (CDP), so the editor draws what a finger would. Visible
means painted: elementFromPoint.
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
EDITORS = (("Pad", "/skribl-pad", 6), ("Flip", "/flip", 5))

PAINTED = """(sel) => { const e = document.querySelector(sel); if (!e) return false;
  const r = e.getBoundingClientRect(); if (!r.width || !r.height) return false;
  const at = document.elementFromPoint(r.left + r.width / 2, r.top + Math.min(r.height / 2, 20));
  return !!at && (e === at || e.contains(at)); }"""
BOOK = """() => { const r = document.getElementById('bookRoot');
  return { open: !r.hidden, kick: document.getElementById('bkKick').textContent,
           next: document.getElementById('bkNext').textContent, back: !document.getElementById('bkBack').hidden,
           along: !document.getElementById('bkAlong').hidden, on: [...document.querySelectorAll('#bkDots i')].findIndex(i => i.classList.contains('on')),
           example: !!document.querySelector('#bkPic .lc-stage, #bkPic .lc-phone'),
           help: !document.getElementById('helpDrawer').hidden, focus: document.activeElement && document.activeElement.id }; }"""
ALONG = """() => { const g = document.querySelector('.da-guide'), p = document.querySelector('.da-pill');
  const cv = document.getElementById('canvas') || document.getElementById('pad');
  const r = e => { if (!e) return null; const b = e.getBoundingClientRect(); return [Math.round(b.left), Math.round(b.top), Math.round(b.width), Math.round(b.height)]; };
  const head = document.querySelector('.header');
  return { guide: !!g, inLayer: !!g && !!g.closest('#zoomLayer'), guideBox: r(g), canvasBox: r(cv),
           pill: !!p, pillTop: p ? Math.round(p.getBoundingClientRect().top) : null, headBottom: head ? Math.round(head.getBoundingClientRect().bottom) : 0,
           where: p ? p.querySelector('.da-where').textContent : '', state: window.SkriblDrawAlong && SkriblDrawAlong.state() }; }"""


def fresh(b, opts, route, scheme="light"):
    c = b.new_context(color_scheme=scheme, **opts)
    c.add_init_script("try { localStorage.setItem('skribl.learncard.note.v1', '1'); } catch (e) {}")
    q = c.new_page()
    errs = []
    q.on("pageerror", lambda e: errs.append(str(e)))
    browsing.goto(q, BASE, route)
    q.wait_for_timeout(900)
    q.evaluate("() => window.SkriblHints && window.SkriblHints.hide()")
    return c, q, errs


def open_book(q):
    q.evaluate("() => openHelpDrawer()")
    q.wait_for_timeout(700)
    q.click("#askTour")
    q.wait_for_timeout(1500)


def stroke(q, cdp, pts):
    cdp.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [{"x": pts[0][0], "y": pts[0][1]}]})
    for x, y in pts[1:]:
        cdp.send("Input.dispatchTouchEvent", {"type": "touchMove", "touchPoints": [{"x": x, "y": y}]})
        q.wait_for_timeout(16)
    cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
    q.wait_for_timeout(300)


with sync_playwright() as p:
    b = p.chromium.launch()
    for name, route, n in EDITORS:
        print(f"\n{name}")
        c, q, errs = fresh(b, PHONE, route)

        # 1. never by itself, then New here?
        q.wait_for_timeout(1500)
        check(f"{name}: the little book never opens by itself",
              q.evaluate("() => document.getElementById('bookRoot').hidden") is True)
        open_book(q)
        bk = q.evaluate(BOOK)
        check(f"{name}: New here? opens the little book on page 1 of {n}, its example playing, How it works stepping aside, focus on Next",
              bk["open"] and bk["kick"].endswith(f"1 of {n}") and bk["example"] and not bk["help"] and bk["focus"] == "bkNext"
              and not bk["back"], str(bk))
        check(f"{name}: ...painted: its title and Next", q.evaluate(PAINTED, "#bkTitle") and q.evaluate(PAINTED, "#bkNext"))
        geo = q.evaluate("""() => { const r = document.querySelector('#bookRoot .bk').getBoundingClientRect();
          return { top: Math.round(r.top), bottom: Math.round(r.bottom), left: Math.round(r.left), right: Math.round(r.right), vw: innerWidth, vh: innerHeight }; }""")
        check(f"{name}: on a phone it is a sheet that fits its page, the drawing in view above it",
              geo["left"] == 0 and geo["right"] == geo["vw"] and geo["bottom"] == geo["vh"] and geo["top"] >= 0.1 * geo["vh"], str(geo))
        check(f"{name}: page 1 has no Draw along (it isn't a drawing to trace)", not bk["along"], str(bk))

        # 3. turning
        q.click("#bkNext"); q.wait_for_timeout(500)
        b2 = q.evaluate(BOOK)
        check(f"{name}: Next turns to page 2, the dots following, Back there, and Draw along on this drawing page",
              b2["kick"].endswith(f"2 of {n}") and b2["on"] == 1 and b2["back"] and b2["along"], str(b2))
        box = q.locator("#bookRoot .bk-body").bounding_box()
        cdp = c.new_cdp_session(q)
        y = box["y"] + 60
        stroke(q, cdp, [(box["x"] + box["width"] - 30 - i * 25, y) for i in range(10)])
        b3 = q.evaluate(BOOK)
        q.keyboard.press("ArrowLeft"); q.wait_for_timeout(300)
        b4 = q.evaluate(BOOK)
        check(f"{name}: a swipe to the left turns forward, and the left arrow turns back",
              b3["kick"].endswith(f"3 of {n}") and b4["kick"].endswith(f"2 of {n}"), f"{b3['kick']} then {b4['kick']}")

        # 4. closing goes back to How it works
        q.keyboard.press("Escape"); q.wait_for_timeout(600)
        v = q.evaluate("() => ({ book: !document.getElementById('bookRoot').hidden, help: !document.getElementById('helpDrawer').hidden, home: !document.getElementById('helpWatch').hidden })")
        check(f"{name}: Escape closes the book and goes back to How it works, on Ask's home",
              not v["book"] and v["help"] and v["home"], str(v))
        q.click("#askTour"); q.wait_for_timeout(800)
        q.click("#bookRoot [data-book-close].help-close"); q.wait_for_timeout(600)
        v = q.evaluate("() => ({ book: !document.getElementById('bookRoot').hidden, help: !document.getElementById('helpDrawer').hidden })")
        check(f"{name}: the x does the same", not v["book"] and v["help"], str(v))

        # the last page
        q.click("#askTour"); q.wait_for_timeout(800)
        for _ in range(n - 1):
            q.click("#bkNext"); q.wait_for_timeout(150)
        last = q.evaluate(BOOK)
        q.click("#bkNext"); q.wait_for_timeout(600)
        v = q.evaluate("() => ({ book: !document.getElementById('bookRoot').hidden, help: !document.getElementById('helpDrawer').hidden })")
        check(f"{name}: the last page says Start drawing, and it leaves you drawing (the book and How it works put away)",
              last["next"] == "Start drawing" and not v["book"] and not v["help"], f"{last['next']!r} {v}")

        # 5. Draw along
        cv = "#canvas" if name == "Pad" else "#pad"
        before = q.evaluate(f"() => document.querySelector('{cv}').toDataURL()")
        open_book(q)
        q.click("#bkNext"); q.wait_for_timeout(400)
        q.click("#bkAlong"); q.wait_for_timeout(1200)
        a = q.evaluate(ALONG)
        check(f"{name}: Draw along puts the book away and lays the cat on your canvas, in the zoom layer, over the drawing exactly",
              q.evaluate("() => document.getElementById('bookRoot').hidden") is True and a["guide"] and a["inLayer"]
              and a["guideBox"] == a["canvasBox"], str(a))
        check(f"{name}: ...with the pill under the header, painted, at the first of the cat's strokes",
              a["pill"] and a["pillTop"] >= a["headBottom"] and q.evaluate(PAINTED, ".da-pill .da-done")
              and a["where"] == f"the cat · 1 of {a['state']['n']}" and a["state"]["n"] > 20, str(a))
        r = q.locator(cv).bounding_box()
        cx, cy = r["x"] + r["width"] * 0.3, r["y"] + r["height"] * 0.7
        stroke(q, cdp, [(cx + i * 6, cy - i * 4) for i in range(12)])
        a1 = q.evaluate(ALONG)
        cdp.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [{"x": cx, "y": cy}]})
        cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
        q.wait_for_timeout(300)
        a2 = q.evaluate(ALONG)
        check(f"{name}: any real stroke counts and the next one shows; a tap does not",
              a1["state"]["k"] == 1 and a2["state"]["k"] == 1 and a1["where"].startswith("the cat · 2 of"), f"{a1['state']} then {a2['state']}")
        q.click(".da-skip"); q.wait_for_timeout(200)
        check(f"{name}: Skip moves on a stroke", q.evaluate(ALONG)["state"]["k"] == 2)
        q.click(".da-done"); q.wait_for_timeout(300)
        a3 = q.evaluate(ALONG)
        after = q.evaluate(f"() => document.querySelector('{cv}').toDataURL()")
        check(f"{name}: Done puts the guide and the pill away", not a3["guide"] and not a3["pill"] and a3["state"] is None, str(a3))
        # 6. never the drawing: the canvas changed only by the stroke drawn;
        # a planted guide pixel would change it everywhere the cat is.
        diff = q.evaluate("""([cv, before]) => new Promise(res => { const a = new Image(); a.onload = () => {
            const c = document.querySelector(cv), w = c.width, h = c.height, o = document.createElement('canvas'); o.width = w; o.height = h;
            const g = o.getContext('2d'); g.drawImage(a, 0, 0); const A = g.getImageData(0, 0, w, h).data, B = c.getContext('2d').getImageData(0, 0, w, h).data;
            let n = 0; for (let i = 0; i < A.length; i += 4) if (Math.abs(A[i] - B[i]) + Math.abs(A[i + 1] - B[i + 1]) + Math.abs(A[i + 2] - B[i + 2]) > 30) n++;
            res({ changed: n, of: w * h }); }; a.src = before; })""", [cv, before])
        check(f"{name}: the drawing holds your stroke and nothing of the guide (a little ink changed, not the cat)",
              0 < diff["changed"] < 0.02 * diff["of"], str(diff))
        # Escape puts it away too.
        open_book(q); q.click("#bkNext"); q.wait_for_timeout(300); q.click("#bkAlong"); q.wait_for_timeout(900)
        q.keyboard.press("Escape"); q.wait_for_timeout(300)
        check(f"{name}: Escape puts Draw along away", not q.evaluate(ALONG)["guide"])
        check(f"{name}: no page errors", not errs, "; ".join(errs[:2]))
        c.close()

        # On a desk, a dialog in the middle.
        c, q, errs = fresh(b, DESK, route, scheme="dark")
        open_book(q)
        geo = q.evaluate("""() => { const r = document.querySelector('#bookRoot .bk').getBoundingClientRect();
          return { left: Math.round(r.left), right: Math.round(r.right), top: Math.round(r.top), bottom: Math.round(r.bottom), w: Math.round(r.width), vw: innerWidth, vh: innerHeight }; }""")
        check(f"{name}: on a desk the book is a dialog in the middle, at most 560px wide, clear of the edges",
              abs((geo["left"] + geo["right"]) / 2 - geo["vw"] / 2) <= 1 and geo["w"] <= 560 and geo["top"] > 20 and geo["bottom"] < geo["vh"] - 20, str(geo))
        check(f"{name}: no page errors on a desk", not errs, "; ".join(errs[:2]))
        c.close()
    b.close()

bad = [r for r in results if not r[0]]
print(f"\n{'=' * 62}\n{len(results) - len(bad)}/{len(results)} passed"
      + ("" if not bad else "  FAILURES: " + ", ".join(r[1] for r in bad)))
sys.exit(1 if bad else 0)
