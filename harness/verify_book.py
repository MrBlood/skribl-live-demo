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
  7. EVERY RECORDING SHOWS WHOLE (owner: "the viewport cuts off the videos on
     the how it works book. you should double check all the videos"; the
     clips mock, A). lib/learncard.js's picture() puts the same phone
     recordings in the book, on the button cards and in Ask's answers, so
     every place it puts one is walked, phone and desk: the whole clip
     painted to its edges and corners, inside an outline of its own shape at
     today's size; the book's picture one height on every page; each clip's
     ratio its poster's.

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

# 7. Each recording placed: the clip's painted rect, worked out from its own
# size and the video's object-fit and object-position, then cut by the
# video's box, every box round it that clips, and the screen. Painted means
# elementFromPoint finds the video at the clip's edges and corners (inside
# its rounded corners), so a frame that clips it, a scroller, a sheet over it
# or the screen's edge all turn it red. bars: the gap between the clip and the
# outline drawn round it, across and down (negative: the clip spills past it).
WHOLE = """(sel) => Promise.all([...document.querySelectorAll(sel)].filter(v => v.getClientRects().length).map(v =>
  new Promise(res => { if (v.videoWidth) res(); else { v.addEventListener('loadedmetadata', () => res(), { once: true }); setTimeout(res, 8000); } })
  .then(() => {
    const cs = getComputedStyle(v), r = v.getBoundingClientRect(), px = k => parseFloat(cs[k]) || 0;
    const bx = { l: r.left + px('borderLeftWidth') + px('paddingLeft'), t: r.top + px('borderTopWidth') + px('paddingTop'),
                 w: r.width - px('borderLeftWidth') - px('borderRightWidth') - px('paddingLeft') - px('paddingRight'),
                 h: r.height - px('borderTopWidth') - px('borderBottomWidth') - px('paddingTop') - px('paddingBottom') };
    const vw = v.videoWidth, vh = v.videoHeight, fit = cs.objectFit;
    if (!vw || !vh) return { clip: (v.currentSrc || v.src || '?').split('/').pop(), vw, vh, seen: 0, miss: 8, bars: [0, 0], w: 0 };
    let sx = bx.w / vw, sy = bx.h / vh;
    if (fit === 'contain') sx = sy = Math.min(sx, sy);
    else if (fit === 'scale-down') sx = sy = Math.min(sx, sy, 1);
    else if (fit === 'cover') sx = sy = Math.max(sx, sy);
    else if (fit === 'none') sx = sy = 1;
    const cw = vw * sx, ch = vh * sy;
    const [ox, oy] = cs.objectPosition.split(' ').map((p, i) => p.endsWith('%') ? parseFloat(p) / 100 * (i ? bx.h - ch : bx.w - cw) : parseFloat(p));
    const c = { l: bx.l + ox, t: bx.t + oy, r: bx.l + ox + cw, b: bx.t + oy + ch };
    let L = Math.max(c.l, bx.l, 0), T = Math.max(c.t, bx.t, 0), R = Math.min(c.r, bx.l + bx.w, innerWidth), B = Math.min(c.b, bx.t + bx.h, innerHeight);
    for (let a = v.parentElement; a; a = a.parentElement) {
      const o = getComputedStyle(a); if (o.overflowX === 'visible' && o.overflowY === 'visible') continue;
      const q = a.getBoundingClientRect(); L = Math.max(L, q.left); T = Math.max(T, q.top); R = Math.min(R, q.right); B = Math.min(B, q.bottom);
    }
    const d = 2 + 0.3 * (parseFloat(cs.borderTopLeftRadius) || 0), mx = (c.l + c.r) / 2, my = (c.t + c.b) / 2;
    const pts = [[mx, c.t + 2], [mx, c.b - 2], [c.l + 2, my], [c.r - 2, my], [c.l + d, c.t + d], [c.r - d, c.t + d], [c.l + d, c.b - d], [c.r - d, c.b - d]];
    return { clip: (v.currentSrc || v.src).split('/').pop().split('?')[0].replace(/-(light|dark)[.](mp4|webm)$/, ''), vw, vh,
             w: Math.round(r.width * 10) / 10, seen: Math.round(1000 * Math.max(0, R - L) * Math.max(0, B - T) / (cw * ch)) / 10,
             miss: pts.filter(([x, y]) => document.elementFromPoint(x, y) !== v).length,
             bars: [Math.round((bx.w - cw) * 10) / 10, Math.round((bx.h - ch) * 10) / 10] };
  })))"""
BKPIC = """() => { const p = document.getElementById('bkPic'); if (!p || p.hidden || !p.firstElementChild) return null;
  const r = p.getBoundingClientRect(), k = p.firstElementChild.getBoundingClientRect();
  return { kind: p.firstElementChild.className, h: Math.round(r.height * 10) / 10, w: Math.round(r.width * 10) / 10,
           inner: p.clientWidth, kw: Math.round(k.width * 10) / 10 }; }"""
RATIOS = """() => Promise.all([...document.querySelectorAll('.learn-clip')].map(f => Promise.all(['light', 'dark'].map(t =>
  new Promise(res => { const i = new Image(); i.onload = () => res(i.naturalWidth / i.naturalHeight); i.onerror = () => res(0); i.src = f.getAttribute('data-poster-' + t); })))
  .then(([l, d]) => { const r = (f.getAttribute('data-ratio') || '').split('/').map(Number);
    return { clip: f.getAttribute('data-clip-name'), ratio: r.length === 2 && r[1] ? r[0] / r[1] : 0, light: l, dark: d }; })))"""
ASK = """(id) => { document.getElementById('askAnswer').innerHTML = '';
  const r = document.createElement('button'); r.setAttribute('data-answer', id); r.hidden = true;
  document.getElementById('helpWatch').appendChild(r); r.click(); r.remove(); }"""
# Every place picture() puts a recording, by editor: Flip's book, cards and
# answers have only the clips its How it works holds. Walked to the letter, so
# a place that stops being reached is a red row, not a smaller sample.
PLACES = {
    "Pad": ["book speed", "book music", "book post", "card #mediaOpenBtn photo", "card #postBtn post", "ask music",
            "ask speed", "ask takes", "ask post", "ask export", "ask photo"],
    "Flip": ["book music", "book post", "card #postBtn post", "ask music", "ask post"],
}
TODAY = {"book": 150, "card": 112, "ask": 150}   # the phone's width before the fix: it grows its frame, not shrinks


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


def clip_walk(q):
    """Each recording, where picture() puts it: the book's pages (and the
    picture's box on every page), the button cards, Ask's answers."""
    found, pics = {}, []
    open_book(q)
    pages = q.evaluate("() => SkriblBook.pages")
    for i in range(pages):
        pic = q.evaluate(BKPIC)
        if pic:
            pics.append(pic)
        for m in q.evaluate(WHOLE, "#bkPic .lc-phone video"):
            found[f"book {m['clip']}"] = m
        if i < pages - 1:
            q.click("#bkNext"); q.wait_for_timeout(500)
    q.evaluate("() => SkriblBook.close('draw')"); q.wait_for_timeout(400)
    for sel in ("#mediaOpenBtn", "#postBtn"):
        if q.evaluate("(s) => !document.querySelector(s)", sel):
            continue
        q.evaluate("(s) => SkriblLearnCard.open(s)", sel); q.wait_for_timeout(600)
        for m in q.evaluate(WHOLE, ".lc-card .lc-phone video"):
            found[f"card {sel} {m['clip']}"] = m
        q.evaluate("() => SkriblLearnCard.close()"); q.wait_for_timeout(250)
    q.evaluate("() => openHelpDrawer()"); q.wait_for_timeout(700)
    for aid in ("music", "speed", "takes", "post", "export", "photo"):
        q.evaluate(ASK, aid); q.wait_for_timeout(600)
        for m in q.evaluate(WHOLE, ".ask-answer-pic .lc-phone video"):
            found[f"ask {aid}" if m["clip"] == aid else f"ask {aid} {m['clip']}"] = m
    q.evaluate("() => closeHelpDrawer && closeHelpDrawer()"); q.wait_for_timeout(300)
    return found, pics


def clip_rows(q, name, n, view):
    found, pics = clip_walk(q)
    say = "; ".join(f"{k} {m['seen']}% miss {m['miss']} bars {m['bars']} w {m['w']}" for k, m in found.items())
    check(f"{name} ({view}): every screen recording shows whole, painted to its edges and corners: "
          f"the book, the button cards and Ask's answers ({len(PLACES[name])} places)",
          sorted(found) == sorted(PLACES[name]) and all(m["seen"] >= 99.9 and m["miss"] == 0 for m in found.values()),
          f"walked {sorted(found)}; {say}")
    check(f"{name} ({view}): ...each in an outline of its own shape (no gap, no spill), at today's size or bigger",
          bool(found) and all(abs(m["bars"][0]) <= 1 and abs(m["bars"][1]) <= 1 and m["w"] >= TODAY[k.split()[0]] - 0.5
                              for k, m in found.items()), say)
    hs = [p["h"] for p in pics]
    desk = view.startswith("desk")
    shape = "the drawing's 4:3" if desk else "the tall phone whole"
    check(f"{name} ({view}): the book's picture is one height on all {n} pages ({shape}), and no example is wider than its page",
          len(pics) == n and max(hs) - min(hs) <= 1 and all(p["kw"] <= p["inner"] + 0.5 for p in pics)
          and (not desk or all(abs(p["h"] - p["w"] * 3 / 4) <= 2 for p in pics)), str(pics))


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

        # 7. Every recording whole, on a phone in light...
        c, q, errs = fresh(b, PHONE, route)
        rs = q.evaluate(RATIOS)
        off = [r for r in rs if not (r["light"] and r["dark"] and abs(r["ratio"] / r["light"] - 1) < 0.005 and abs(r["ratio"] / r["dark"] - 1) < 0.005)]
        check(f"{name}: each of its {len(rs)} clips carries its recording's own ratio (both themes' posters)", len(rs) >= 5 and not off, str(off or rs))
        clip_rows(q, name, n, "phone, light")
        check(f"{name}: no page errors walking the recordings", not errs, "; ".join(errs[:2]))
        c.close()

        # On a desk, a dialog in the middle.
        c, q, errs = fresh(b, DESK, route, scheme="dark")
        open_book(q)
        geo = q.evaluate("""() => { const r = document.querySelector('#bookRoot .bk').getBoundingClientRect();
          return { left: Math.round(r.left), right: Math.round(r.right), top: Math.round(r.top), bottom: Math.round(r.bottom), w: Math.round(r.width), vw: innerWidth, vh: innerHeight }; }""")
        check(f"{name}: on a desk the book is a dialog in the middle, at most 560px wide, clear of the edges",
              abs((geo["left"] + geo["right"]) / 2 - geo["vw"] / 2) <= 1 and geo["w"] <= 560 and geo["top"] > 20 and geo["bottom"] < geo["vh"] - 20, str(geo))
        q.evaluate("() => SkriblBook.close('draw')"); q.wait_for_timeout(400)
        clip_rows(q, name, n, "desk, dark")   # ...and on a desk in dark
        check(f"{name}: no page errors on a desk", not errs, "; ".join(errs[:2]))
        c.close()
    b.close()

bad = [r for r in results if not r[0]]
print(f"\n{'=' * 62}\n{len(results) - len(bad)}/{len(results)} passed"
      + ("" if not bad else "  FAILURES: " + ", ".join(r[1] for r in bad)))
sys.exit(1 if bad else 0)
