"""Your hand (skribl/static/editor_letters.js, /skribl-pad?letters=1): the
letter sheet the owner said "All yes" to, made every person's own ("Yes to
all", then "Yes" to the Your hand mock). Each row holds a promise:

  1. THE PAGE: someone new meets the start (what happens, Start with a,
     Open a copy); Start puts them on a with the sheet's two bars painted and
     the Pad's chrome hidden, the letter's box between the bars; the plain Pad
     has none of it.
  2. A LETTER IS A PERFORMANCE: drawn with real pointer events, a letter is
     kept with each point's time from its first, its pauses kept, the plain
     pen's width and colour, one entry per stroke; Next lights up at the
     first stroke.
  3. THE GUIDES AND THE MODEL: four lines where the sheet says, painted under
     the ink, never part of it; the faint model fits them (a lowercase to the
     x-height, a capital to the cap height).
  4. NEXT, BACK, REDO: Next moves on and arms the next letter; Back puts the
     last letter on the canvas to add to, and a stroke added lands after its
     last, not at its start; Redo clears it and its toast brings it back; a
     new stroke takes the offer away.
  5. THE LINE WRITES ITSELF: the letter just drawn writes itself into the
     line, read on every frame (still under Reduce Motion); the last letter
     drawn ends on the tiles, the whole line writing itself over a faint copy.
  6. YOUR PAD IS UNTOUCHED: the Pad's draft, brush and mirror are what they
     were, and the sheet drew with the plain pen, unmirrored, all the same.
  7. FINISH LATER, AND COMING BACK: Finish later goes to the plain Pad, and
     the sheet opens again on the letter it left, with its strokes.
  8. THE SET, POSTED AND READ BACK: from the tiles, Post your letters posts
     what is drawn as "My letters", and harness/tools/letterfont.py reads
     every letter back from the server, the same strokes, places to a
     thousandth of a cap height, and times; a set of 30 comes back as its 30,
     the rest empty; closing the post sheet brings the tiles back.
  9. WORDS YOU CAN READ: the bars' and the pages' words against what is
     painted behind them, light and dark, phone and desk; every button 44px.
 10. KEYS: arrows move between letters, undo takes back a stroke, and the
     Pad's letter keys (the eraser, the pen's size) do nothing here.
 11. THE FIRST 30, AND READY: the letters come a to z, then . , ! ?; the
     30th opens Ready, once; Add the rest goes on with A, 31 of 92.
 12. THE TILES: every letter in its group with its count; tap one to draw it
     again, the old one faint behind it and kept until Done (Cancel keeps
     it); tap a + to add one.
 13. A COPY, AND STARTING OVER: Save a copy makes a file with every letter;
     Start over clears them and Undo brings them back; Open a copy puts a
     saved hand back; a file that is not a hand changes nothing, and says so.

For calibration, LETTERS_PART=<words of a part's label> runs that part alone.
A real run sets none.
"""
import json
import math
import os
import sys
import tempfile
import urllib.request
from pathlib import Path

from assertions import make_check
import browsing

sys.path.insert(0, str(Path(__file__).resolve().parent / "tools"))
import letterfont  # noqa: E402

BASE = os.environ.get("SKRIBL_BASE", "http://127.0.0.1:5001")
results = []
check = make_check(results, detail_on_pass=True)

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("SKIP: playwright is not installed")
    sys.exit(0)

PART = os.environ.get("LETTERS_PART", "")
PHONE = dict(viewport={"width": 402, "height": 874}, device_scale_factor=2, is_mobile=True, has_touch=True)
DESK = dict(viewport={"width": 1280, "height": 860})
URL = "/skribl-pad?letters=1"
KEY = "skribl.letters.v1"
QUICK = list("abcdefghijklmnopqrstuvwxyz") + [".", ",", "!", "?"]
UP = "() => !!window.SkriblLetters && !!SkriblLetters.view()"
DRAWING = "() => !!window.SkriblLetters && SkriblLetters.view() === 'draw' && !!SkriblLetters.box()"
# The current letter's box and lines on screen.
BOXPX = """() => { const L = SkriblLetters, b = L.box(), ln = L.lines();
  const r = canvas.getBoundingClientRect(), lg = getCanvasLogicalSize();
  const kx = r.width / lg.width, ky = r.height / lg.height;
  return { left: r.left + b.x * kx, top: r.top + b.y * ky, w: b.w * kx, h: b.h * ky, lines: ln,
           canvas: [r.left, r.top, r.right, r.bottom] }; }"""


def part(label):
    if PART and PART.lower() not in label.lower():
        return False
    print("\n" + label)
    return True


def open_sheet(b, *, theme="light", dev=PHONE, seed=None, once="", reduce=False, start=True):
    """A fresh browser on the sheet; `seed` is a store put in place before it loads
    (and only before the first load, so a reload shows what the sheet kept).
    With no letters the start comes first, and `start` presses Start with a."""
    kw = dict(dev)
    if reduce:
        kw["reduced_motion"] = "reduce"
    c = b.new_context(color_scheme=theme, **kw)
    init = ""
    if seed is not None:
        init += "localStorage.setItem(%s, %s);" % (json.dumps(KEY), json.dumps(json.dumps(seed)))
    if init or once:
        c.add_init_script("if (!sessionStorage.getItem('lt-seeded')) { sessionStorage.setItem('lt-seeded', '1');"
                          + init + once + "}")
    q = c.new_page()
    errors = []
    q.on("pageerror", lambda e: errors.append(str(e)[:160]))
    q.on("console", lambda m: errors.append(m.text[:160]) if m.type == "error" else None)
    q._lt_errors = errors
    browsing.goto(q, BASE, URL + "&theme=" + theme)
    q.wait_for_function(UP)
    q.wait_for_timeout(250)
    if start and q.evaluate("SkriblLetters.view()") == "start":
        q.click("text=Start with a")
        q.wait_for_function(DRAWING)
        q.wait_for_timeout(200)
    return c, q


def stroke(q, pts, step_ms=6):
    q.mouse.move(*pts[0])
    q.mouse.down()
    for p in pts[1:]:
        q.mouse.move(*p)
        if step_ms:
            q.wait_for_timeout(step_ms)
    q.mouse.up()
    q.wait_for_timeout(60)


def letter_a(q, pause_ms=450):
    """An a, as a hand would: a bowl, a pause, a stem. Returns the screen box."""
    B = q.evaluate(BOXPX)
    L, H = B["lines"], B["h"]
    base, xl = B["top"] + L["base"] * H, B["top"] + L["x"] * H
    cx, r = B["left"] + B["w"] / 2, (base - xl) / 2
    bowl = [(cx + 0.8 * r * math.cos(2 * math.pi * k / 24), (base + xl) / 2 + r * math.sin(2 * math.pi * k / 24))
            for k in range(25)]
    stroke(q, bowl)
    q.wait_for_timeout(pause_ms)
    stroke(q, [(cx + 0.8 * r, xl + y) for y in range(0, int(base - xl) + 1, 8)])
    q.wait_for_timeout(150)
    return B


def a_line(q, frac=0.5):
    """One short stroke across the middle of the box."""
    B = q.evaluate(BOXPX)
    y = B["top"] + B["h"] * frac
    stroke(q, [(B["left"] + B["w"] * 0.35 + k * 6, y + (k % 3)) for k in range(20)])
    q.wait_for_timeout(150)


def stored(q, bid=None):
    st = q.evaluate("SkriblLetters.store()")
    return st if bid is None else st["g"].get(bid)


def sub_text(q):
    return q.evaluate("document.getElementById('ltSub').textContent")


def painted_in(q, sel, x, y):
    return q.evaluate("([s, x, y]) => { const e = document.elementFromPoint(x, y), t = document.querySelector(s);"
                      " return !!e && !!t && t.contains(e); }", [sel, x, y])


def centre(q, sel):
    return q.evaluate("(s) => { const r = document.querySelector(s).getBoundingClientRect();"
                      " return [r.left + r.width / 2, r.top + r.height / 2, r.width, r.height, r.top, r.bottom]; }", sel)


def page_button(q, text):
    return q.locator(".lt-page button", has_text=text).first


# ---------------------------------------------------------------------------
# A whole set without drawing 92 letters by hand: shapes made here, in the
# store's own form, inside the box the page gives. Three of them are drawn to
# make the reading back work: R's first stroke starts left of its box, W is
# far wider than its cell, and i's dot and the full stop are a single point.
def synth_set(box, lines, color="#7c5cff", only=None):
    x0, y0, w, h = box["x"], box["y"], box["w"], box["h"]
    cap = (lines["base"] - lines["cap"]) * h
    base = y0 + lines["base"] * h
    xh = (lines["base"] - lines["x"]) * h
    ids = letterfont.BOX_IDS
    kinds = (["lower"] * 26 + ["upper"] * 26 + ["digit"] * 10 + ["mark"] * 16
             + ["accent"] * 5 + ["again"] * 9)
    out = {}
    for k, (bid, kind) in enumerate(zip(ids, kinds)):
        if only is not None and bid not in only:
            continue
        cx = x0 + w / 2 + ((k * 37) % 21 - 10)
        strokes = []

        def line(ax, ay, bx, by, n=None):
            n = n or max(2, int(math.hypot(bx - ax, by - ay) / 5))
            return [(ax + (bx - ax) * i / n, ay + (by - ay) * i / n) for i in range(n + 1)]

        def ring(mx, my, rx, ry, turn=1.0):
            return [(mx + rx * math.cos(2 * math.pi * turn * i / 24), my + ry * math.sin(2 * math.pi * turn * i / 24))
                    for i in range(25)]

        ch = bid[0]
        if kind in ("lower", "again"):
            top = base - (cap if ch in "bdfhklt" else xh)
            bottom = base + (0.3 * cap if ch in "gjpqy" else 0)
            strokes.append(ring(cx, base - xh / 2, 0.38 * xh, xh / 2))
            strokes.append(line(cx + 0.38 * xh, top, cx + 0.38 * xh, bottom))
            if ch in "ij":
                strokes.append([(cx + 0.38 * xh, base - xh - 0.25 * cap)])
        elif kind in ("upper", "digit"):
            if bid == "W":
                strokes.append(line(cx - 1.1 * cap, base - cap, cx - 0.5 * cap, base))
                strokes.append(line(cx - 0.5 * cap, base, cx + 1.1 * cap, base - cap))
            else:
                left = (x0 - 12 if bid == "R" else cx - 0.3 * cap)
                strokes.append(line(max(1.0, left), base - cap, cx - 0.3 * cap, base))
                strokes.append(ring(cx, base - 0.72 * cap, 0.3 * cap, 0.25 * cap, 0.5))
        elif kind == "mark":
            if ch in ".":
                strokes.append([(cx, base)])
            elif ch in ",;":
                strokes.append(line(cx, base, cx - 0.05 * cap, base + 0.15 * cap))
            else:
                y = {"'": 0.9, '"': 0.9, "-": 0.4, "+": 0.4}.get(ch, 0.6)
                strokes.append(line(cx, base - y * cap, cx + 0.05 * cap, base - (y - 0.3) * cap))
        else:  # accent
            strokes.append(line(cx - 0.1 * cap, base - xh - 0.12 * cap, cx + 0.12 * cap, base - xh - 0.3 * cap))
        p, n, t = [], [], 0
        for si, st in enumerate(strokes):
            if si:
                t += 180 + (k * 53 + si * 31) % 300
            for j, (x, y) in enumerate(st):
                if j:
                    t += 8
                wv = 6 * (0.85 + 0.3 * abs(math.sin(0.37 * j + k)))
                p.append([round(x, 2), round(y, 2), round(wv, 2), t])
            n.append(len(st))
        out[bid] = {"p": p, "n": n, "b": [round(x0, 2), round(y0, 2), round(w, 2), round(h, 2)],
                    "l": [lines["cap"], lines["x"], lines["base"], lines["desc"]], "c": color}
    return {"v": 1, "o": 2, "at": None, "mode": "tiles", "r": True, "g": out}


def normalise(g):
    """A stored letter as the reader gives it back: cap heights, x from its ink
    centre, y up from its baseline, its width, its time."""
    cap = (g["l"][2] - g["l"][0]) * g["b"][3]
    gb = g["b"][1] + g["l"][2] * g["b"][3]
    xs = [q[0] for q in g["p"]]
    mid = (min(xs) + max(xs)) / 2
    out, k = [], 0
    for n in g["n"]:
        st = []
        for _ in range(n):
            q = g["p"][k]
            k += 1
            st.append([(q[0] - mid) / cap, (gb - q[1]) / cap, q[2] / cap, q[3]])
        out.append(st)
    return out


def read_back(q, want):
    """Post what the tiles hold, read it back from the server, and compare."""
    page_button(q, "Post your letters").click()
    q.wait_for_function("() => !document.getElementById('postOverlay').hidden")
    q.wait_for_timeout(500)
    titled = q.evaluate("document.getElementById('postTitleInput').value") == "My letters"
    res = browsing.submit_post(q)
    back = env = None
    if res["url"]:
        pid = res["url"].rstrip("/").split("/s/")[-1]
        env = json.loads(urllib.request.urlopen(BASE + "/api/skribls/" + pid, timeout=30).read())
        back = letterfont.decode(env)
    split_bad, worst = [], [0.0, 0.0, 0.0, 0]
    if back:
        for bid in letterfont.BOX_IDS:
            exp = normalise(want[bid]) if bid in want else []
            got = back["letters"].get(bid, [])
            if [len(s) for s in exp] != [len(s) for s in got]:
                split_bad.append(bid)
                continue
            for se, sg in zip(exp, got):
                for pe, pg in zip(se, sg):
                    for i in range(4):
                        worst[i] = max(worst[i], abs(pe[i] - pg[i]))
    return titled, res, back, env, split_bad, worst


with sync_playwright() as p:
    b = p.chromium.launch()
    c0, q0 = open_sheet(b)
    BOX, LN = q0.evaluate("SkriblLetters.box()"), q0.evaluate("SkriblLetters.lines()")
    c0.close()

    # ------------------------------------------------------------------ 1
    if part("LETTERS 1 — the page: the start, then the sheet's bars and none of the Pad's"):
        c, q = open_sheet(b, start=False)
        st = q.evaluate("""() => ({ view: SkriblLetters.view(), title: (document.querySelector('.lt-ptitle') || {}).textContent,
          start: [...document.querySelectorAll('.lt-page button')].map(b => b.textContent),
          bars: [document.getElementById('ltTop'), document.getElementById('ltFoot')].map(e => e.checkVisibility()) })""")
        check("someone new meets the start: Your hand, Start with a, Open a copy, and no bars yet",
              st["view"] == "start" and st["title"] == "Your hand" and "Start with a" in st["start"]
              and "Open a copy" in st["start"] and not any(st["bars"]), json.dumps(st))
        q.click("text=Start with a")
        q.wait_for_function(DRAWING)
        q.wait_for_timeout(200)
        tx, ty, tw, th, ttop, tbot = centre(q, "#ltTop")
        fx, fy, fw, fh, ftop, fbot = centre(q, "#ltFoot")
        check("Start puts them on a: the top bar and the bottom bar are painted",
              painted_in(q, "#ltTop", tx, ty) and painted_in(q, "#ltFoot", fx, fy))
        # The Pad's header and dock: hidden, not merely covered (the phone's
        # top bar would cover the header either way, so a paint test there
        # could not go red); the desk test below reads the paint.
        vis = q.evaluate("""() => ['.header', '#toolBar', '#canvasEmptyHint', '.zoom-hud'].map(s => {
          const e = document.querySelector(s); return !!e && e.checkVisibility({ visibilityProperty: true }); })""")
        check("the Pad's header, dock, empty-canvas words and zoom pill are hidden", not any(vis), json.dumps(vis))
        check("it says what to draw: 'Draw your letters', 'a · 1 of 30'",
              q.evaluate("document.getElementById('ltTitle').textContent") == "Draw your letters"
              and sub_text(q).replace(" ", " ") == "a · 1 of 30", sub_text(q))
        check("Next and Back wait (nothing drawn, nothing before)",
              q.evaluate("document.getElementById('ltNext').disabled && document.getElementById('ltBack').disabled"))
        B = q.evaluate(BOXPX)
        check("the letter's box lies on the canvas, clear of both bars",
              B["top"] >= tbot and B["top"] + B["h"] <= ftop
              and B["left"] >= B["canvas"][0] and B["left"] + B["w"] <= B["canvas"][2],
              f"box {round(B['top'])}..{round(B['top'] + B['h'])}, bars end {round(tbot)} and start {round(ftop)}")
        check("no error on the way in", not q._lt_errors, "; ".join(q._lt_errors[:2]))
        c.close()
        # On a desk the bars are panels in the middle, so the header's ends
        # are open to the eye: nothing of the Pad's is painted there.
        c, q = open_sheet(b, dev=DESK)
        hdr = q.evaluate("(() => { const r = document.querySelector('.header').getBoundingClientRect(); return [r.left, r.top, r.width, r.height]; })()")
        spots = [(hdr[0] + 30, hdr[1] + hdr[3] / 2), (hdr[0] + hdr[2] - 30, hdr[1] + hdr[3] / 2)]
        check("desk: nothing of the Pad's header is painted beside the top bar",
              not any(painted_in(q, ".header", x, y) for x, y in spots), f"read at {[(round(x), round(y)) for x, y in spots]}")
        c.close()
        c = b.new_context(**PHONE)
        q = c.new_page()
        browsing.goto(q, BASE, "/skribl-pad")
        plain = q.evaluate("""() => ({ top: !!document.getElementById('ltTop'), api: !!window.SkriblLetters,
          mode: document.body.classList.contains('letters-mode'), guides: !!document.getElementById('ltGuides'),
          css: [...document.styleSheets].some(s => /letters\\.css/.test(s.href || '')) })""")
        check("the plain Pad has none of it: no bars, no guides, no sheet, no stylesheet",
              not any(plain.values()), json.dumps(plain))
        c.close()

    # ------------------------------------------------------------------ 2
    if part("LETTERS 2 — a letter is a performance"):
        c, q = open_sheet(b)
        B = q.evaluate(BOXPX)
        L, H = B["lines"], B["h"]
        base, xl = B["top"] + L["base"] * H, B["top"] + L["x"] * H
        cx, r = B["left"] + B["w"] / 2, (base - xl) / 2
        stroke(q, [(cx + 0.8 * r * math.cos(2 * math.pi * k / 24), (base + xl) / 2 + r * math.sin(2 * math.pi * k / 24))
                   for k in range(25)])
        q.wait_for_timeout(150)
        lit = not q.evaluate("document.getElementById('ltNext').disabled")
        q.wait_for_timeout(450)
        stroke(q, [(cx + 0.8 * r, xl + y) for y in range(0, int(base - xl) + 1, 8)])
        q.wait_for_timeout(200)
        check("Next lights up at the first stroke", lit)
        g = stored(q, "a")
        ok = bool(g)
        check("the a is kept as it is drawn, one entry per stroke", ok and len(g["n"]) == 2 and sum(g["n"]) == len(g["p"]),
              g and f"strokes {g['n']}")
        if ok:
            ts = [pt[3] for pt in g["p"]]
            n1 = g["n"][0]
            check("its time runs from its first point and never back", ts[0] == 0 and all(b2 >= a2 for a2, b2 in zip(ts, ts[1:])),
                  f"{ts[0]}..{ts[-1]} ms")
            check("the pause between its strokes is kept", ts[n1] - ts[n1 - 1] >= 400, f"{ts[n1] - ts[n1 - 1]} ms")
            check("drawn with the plain pen: one width, Skribl purple",
                  {pt[2] for pt in g["p"]} == {6} and g["c"] == "#7c5cff", f"widths {sorted({pt[2] for pt in g['p']})}, {g['c']}")
            bx = q.evaluate("SkriblLetters.box()")
            check("it keeps the box and the lines it was drawn to",
                  all(abs(a2 - b2) < 0.02 for a2, b2 in zip(g["b"], [bx["x"], bx["y"], bx["w"], bx["h"]]))
                  and g["l"] == [0.16, 0.334, 0.74, 0.94], f"{g['b']} {g['l']}")
        c.close()

    # ------------------------------------------------------------------ 3
    def model_box(q):
        return q.evaluate("""() => { const g = document.getElementById('ltGuides'), L = SkriblLetters;
          const b = L.box(), ln = L.lines(), lg = getCanvasLogicalSize(), ky = g.height / lg.height, kx = g.width / lg.width;
          const d = g.getContext('2d').getImageData(0, 0, g.width, g.height).data, W = g.width;
          const ys = Object.values(ln).map(f => (b.y + f * b.h) * ky); let top = Infinity, bottom = -Infinity;
          for (let y = Math.round(b.y * ky); y < (b.y + b.h) * ky; y++) { if (ys.some(v => Math.abs(v - y) < 4)) continue;
            for (let x = Math.round((b.x + b.w * 0.02) * kx); x < (b.x + b.w * 0.98) * kx; x += 2) {
              const v = d[(y * W + x) * 4 + 3]; if (v > 8 && v < 70) { top = Math.min(top, y); bottom = Math.max(bottom, y); break; } } }
          return { top, bottom, cap: (b.y + ln.cap * b.h) * ky, x: (b.y + ln.x * b.h) * ky, base: (b.y + ln.base * b.h) * ky, at: L.at() }; }""")

    if part("LETTERS 3 — the guides and the faint model"):
        for theme in ("light", "dark"):
            c, q = open_sheet(b, theme=theme)
            info = q.evaluate("""() => { const g = document.getElementById('ltGuides'), cv = canvas, L = SkriblLetters;
              const b = L.box(), ln = L.lines(), lg = getCanvasLogicalSize();
              const ky = g.height / lg.height, kx = g.width / lg.width;
              const d = g.getContext('2d').getImageData(0, 0, g.width, g.height).data, W = g.width;
              const a = (x, y) => d[(Math.round(y) * W + Math.round(x)) * 4 + 3];
              const lineAt = (f) => { const y = (b.y + f * b.h) * ky; let m = 0;
                for (let dy = -3; dy <= 3; dy++) for (let x = (b.x + 2) * kx; x < (b.x + 40) * kx; x++) m = Math.max(m, a(x, y + dy)); return m; };
              const lines = {}; for (const k of ['cap', 'x', 'base', 'desc']) lines[k] = lineAt(ln[k]);
              const between = lineAt((ln.cap + ln.x) / 2);
              const z = (el) => +getComputedStyle(el).zIndex || 0;
              return { lines, between, sameLayer: g.parentNode === cv.parentNode && g.parentNode.id === 'zoomLayer',
                       under: z(g) < z(cv), pe: getComputedStyle(g).pointerEvents }; }""")
            check(f"{theme}: four lines where the sheet says, none between",
                  all(v > 60 for v in info["lines"].values()) and info["between"] < 8,
                  f"{info['lines']}, between {info['between']}")
            check(f"{theme}: the guides are under the ink and take no pointer",
                  info["sameLayer"] and info["under"] and info["pe"] == "none")
            mb = model_box(q)
            capd = mb["base"] - mb["cap"]
            check(f"{theme}: the model a fits the x-height and the baseline",
                  abs(mb["top"] - mb["x"]) <= 0.05 * capd and abs(mb["bottom"] - mb["base"]) <= 0.05 * capd,
                  f"top {round(mb['top'] - mb['x'], 1)}px from the x-line, bottom {round(mb['bottom'] - mb['base'], 1)}px from the baseline (cap {round(capd)}px)")
            # Painted where a person sees it: the cap line's row is tinted in a
            # screenshot, against a clean row beside it.
            from io import BytesIO
            try:
                from PIL import Image
                img = Image.open(BytesIO(q.screenshot())).convert("RGB")
                B = q.evaluate(BOXPX)
                dpr = img.width / q.viewport_size["width"]
                yl = round((B["top"] + B["lines"]["cap"] * B["h"]) * dpr)
                xs = range(round((B["left"] + 4) * dpr), round((B["left"] + B["w"] * 0.15) * dpr))
                tint = lambda yy: sum(img.getpixel((x, yy))[2] - img.getpixel((x, yy))[1] for x in xs) / len(xs)
                check(f"{theme}: the cap line is painted on screen", tint(yl) - tint(yl + round(12 * dpr)) > 6,
                      f"blue over green {round(tint(yl), 1)} on the line, {round(tint(yl + round(12 * dpr)), 1)} beside it")
            except ImportError:
                check(f"{theme}: the cap line is painted on screen (Pillow is needed)", False)
            c.close()
        # A capital fits the cap line.
        seed = synth_set(BOX, LN, only=["a"])
        seed.update({"mode": "seq", "at": 26})
        c, q = open_sheet(b, seed=seed)
        q.wait_for_function(DRAWING)
        mb = model_box(q)
        capd = mb["base"] - mb["cap"]
        check("the model A fits the cap height and the baseline",
              mb["at"] == 26 and abs(mb["top"] - mb["cap"]) <= 0.04 * capd and abs(mb["bottom"] - mb["base"]) <= 0.04 * capd,
              f"top {round(mb['top'] - mb['cap'], 1)}px, bottom {round(mb['bottom'] - mb['base'], 1)}px (cap {round(capd)}px)")
        c.close()

    # ------------------------------------------------------------------ 4
    if part("LETTERS 4 — Next, Back, Redo"):
        c, q = open_sheet(b)
        letter_a(q)
        a_pts = len(stored(q, "a")["p"])
        q.click("#ltNext")
        q.wait_for_timeout(300)
        st = q.evaluate("({ at: SkriblLetters.at(), n: strokes.length, rec: recording, now: +document.getElementById('ltBar').getAttribute('aria-valuenow') })")
        check("Next moves on to b, its canvas clear and ready, one of 30 drawn",
              st["at"] == 1 and st["n"] == 0 and st["rec"] and st["now"] == 1
              and sub_text(q).startswith("b · 2 of 30"), json.dumps(st) + " " + sub_text(q))
        q.click("#ltBack")
        q.wait_for_timeout(300)
        st = q.evaluate("({ at: SkriblLetters.at(), n: strokes.length, rec: recording })")
        check("Back puts the a on the canvas to add to", st["at"] == 0 and st["n"] == a_pts and st["rec"], json.dumps(st))
        B = q.evaluate(BOXPX)
        base = B["top"] + B["lines"]["base"] * B["h"]
        stroke(q, [(B["left"] + B["w"] * 0.3, base + 6), (B["left"] + B["w"] * 0.7, base + 6)])
        q.wait_for_timeout(200)
        g = stored(q, "a")
        k = sum(g["n"][:-1])
        check("a stroke added later lands after the letter's last, not at its start",
              len(g["n"]) == 3 and g["p"][k][3] > g["p"][k - 1][3] + 500,
              f"strokes {g['n']}, new stroke at {g['p'][k][3]} ms after {g['p'][k - 1][3]}")
        q.click("#ltRedo")
        q.wait_for_timeout(300)
        toast = q.evaluate("(() => { const t = document.getElementById('toast'), a = t.querySelector('.toast-action');"
                           " return { shown: !t.hidden, text: t.firstChild && t.firstChild.textContent, action: a && a.textContent }; })()")
        check("Redo clears the a, and says so with a way back",
              stored(q, "a") is None and q.evaluate("strokes.length") == 0 and toast["shown"]
              and toast["text"] == "Cleared" and toast["action"] == "Undo", json.dumps(toast))
        q.click("#toast .toast-action")
        q.wait_for_timeout(300)
        g2 = stored(q, "a")
        check("Undo brings the a back whole", bool(g2) and g2["n"] == g["n"] and q.evaluate("strokes.length") == sum(g["n"]))
        q.click("#ltRedo")
        q.wait_for_timeout(250)
        stroke(q, [(B["left"] + B["w"] * 0.4, base - 40), (B["left"] + B["w"] * 0.6, base - 40)])
        q.wait_for_timeout(350)
        gone = q.evaluate("(() => { const t = document.getElementById('toast'); return t.hidden || !t.classList.contains('show'); })()")
        check("a new stroke takes the offer away", gone)
        c.close()

    # ------------------------------------------------------------------ 5
    if part("LETTERS 5 — the line writes itself"):
        FRAMES = """() => new Promise(done => { const out = []; const t0 = performance.now();
          (function f() { const p = document.querySelector('#ltPreview path[data-letter="a"]');
            out.push(p ? (p.getAttribute('d') || '').length : -1);
            if (performance.now() - t0 > 3500) done(out); else requestAnimationFrame(f); })(); })"""
        for reduce in (False, True):
            c, q = open_sheet(b, reduce=reduce)
            letter_a(q)
            full = q.evaluate("document.querySelector('#ltPreview path[data-letter=\"a\"]').getAttribute('d').length")
            q.evaluate("document.getElementById('ltNext').click()")
            frames = q.evaluate(FRAMES)
            steps = len(set(v for v in frames if v >= 0))
            if not reduce:
                check("the a writes itself into the line, point after point",
                      frames[0] < 0.5 * full and frames[-1] == full and steps >= 6
                      and all(b2 >= a2 for a2, b2 in zip(frames, frames[1:])),
                      f"{frames[0]} of {full} at the first frame, {steps} steps, ends {frames[-1]}")
            else:
                check("under Reduce Motion it is there at once, still", frames[0] == full and steps == 1,
                      f"{frames[0]} of {full} at the first frame")
            c.close()
        # The last letter: the tiles, and the whole line over a faint copy.
        almost = synth_set(BOX, LN)
        del almost["g"]["h2"]
        almost.update({"mode": "seq", "at": letterfont.BOX_IDS.index("h2")})
        c, q = open_sheet(b, seed=almost)
        q.wait_for_function(DRAWING)
        a_line(q)
        q.click("#ltNext")
        q.wait_for_function("() => SkriblLetters.view() === 'tiles'")
        first = q.evaluate("""() => { const ps = [...document.querySelectorAll('.lt-pline path')];
          const faint = ps.filter(p => p.getAttribute('stroke-opacity') === '.22'), ink = ps.filter(p => p.hasAttribute('data-letter'));
          return { faint: faint.length, ink: ink.length, written: ink.filter(p => (p.getAttribute('d') || '').length > 0).length }; }""")
        took = q.evaluate("""(n) => new Promise(done => { const t0 = performance.now();
          (function f() { const ink = [...document.querySelectorAll('.lt-pline path[data-letter]')];
            const w = ink.filter(p => (p.getAttribute('d') || '').length > 0).length;
            if (w >= n || performance.now() - t0 > 15000) done([w, Math.round(performance.now() - t0)]); else requestAnimationFrame(f); })(); })""", first["ink"])
        check("the last letter ends on the tiles, the whole line writing itself over a faint copy, in seconds",
              first["faint"] == first["ink"] and first["ink"] >= 28 and first["written"] < first["ink"]
              and took[0] == first["ink"] and took[1] < 9000,
              f"{first['ink']} letters, {first['faint']} faint, {first['written']} written at once, all {took[0]} in {took[1]} ms")
        c.close()

    # ------------------------------------------------------------------ 6
    if part("LETTERS 6 — your Pad is untouched"):
        DRAFT = json.dumps({"v": 1, "strokes": [], "note": "the owner's drawing"})
        once = ("localStorage.setItem('skribl_autosave_v1', %s); localStorage.setItem('skribl_brush', 'marker');"
                " localStorage.setItem('skribl_mirror', 'vertical');") % json.dumps(DRAFT)
        c, q = open_sheet(b, once=once)
        letter_a(q)
        q.click("#ltNext")
        q.wait_for_timeout(300)
        B = q.evaluate(BOXPX)
        base = B["top"] + B["lines"]["base"] * B["h"]
        stroke(q, [(B["left"] + B["w"] * 0.45, base - 120), (B["left"] + B["w"] * 0.45, base)])
        q.wait_for_timeout(1800)   # past the Pad's autosave debounce, had it been running
        kept = q.evaluate("[localStorage.getItem('skribl_autosave_v1'), localStorage.getItem('skribl_brush'), localStorage.getItem('skribl_mirror')]")
        check("the Pad's draft is byte for byte what it was", kept[0] == DRAFT, (kept[0] or "")[:60])
        check("the brush and the mirror are still the owner's", kept[1] == "marker" and kept[2] == "vertical", f"{kept[1]}, {kept[2]}")
        g = stored(q, "a")
        check("and the letters were drawn with the plain pen, unmirrored",
              g["c"] == "#7c5cff" and {pt[2] for pt in g["p"]} == {6} and len(g["n"]) == 2,
              f"{g['c']}, widths {sorted({pt[2] for pt in g['p']})[:3]}, strokes {g['n']}")
        c.close()

    # ------------------------------------------------------------------ 7
    if part("LETTERS 7 — Finish later, and coming back"):
        c, q = open_sheet(b)
        B = q.evaluate(BOXPX)
        base = B["top"] + B["lines"]["base"] * B["h"]
        stroke(q, [(B["left"] + B["w"] * 0.4, base - 90), (B["left"] + B["w"] * 0.55, base)])
        q.wait_for_timeout(150)
        pts = len(stored(q, "a")["p"])
        q.click("#ltLater")
        try:
            q.wait_for_url("**/skribl-pad", timeout=6000)
            q.wait_for_function("() => !!(window.__skriblBoot && window.__skriblBoot.pad)")
        except Exception:
            pass   # the check below says where it went instead
        plain = q.evaluate("({ top: !!document.getElementById('ltTop'), mode: document.body.classList.contains('letters-mode') })")
        check("Finish later goes to the plain Pad", q.url.endswith("/skribl-pad") and not plain["top"] and not plain["mode"], q.url)
        browsing.goto(q, BASE, URL)
        q.wait_for_function(UP)
        q.wait_for_timeout(250)
        st = q.evaluate("({ view: SkriblLetters.view(), at: SkriblLetters.at(), n: strokes.length, rec: recording, next: !document.getElementById('ltNext').disabled })")
        check("coming back opens the same letter with its stroke",
              st["view"] == "draw" and st["at"] == 0 and st["n"] == pts and st["rec"] and st["next"], json.dumps(st))
        c.close()

    # ------------------------------------------------------------------ 8
    if part("LETTERS 8 — the set, posted and read back"):
        full_set = synth_set(BOX, LN)
        c, q = open_sheet(b, seed=full_set)
        q.wait_for_function("() => SkriblLetters.view() === 'tiles'")
        titled, res, back, env, split_bad, worst = read_back(q, full_set["g"])
        check("from the tiles, Post your letters opens the post sheet, titled My letters", titled)
        check("it posts", res["status"] == 201 and bool(res["url"]), json.dumps(res)[:200])
        if back:
            check("every letter comes back with its own strokes (R starting wide, W wider, the dots)",
                  not split_bad and len([k for k, v in back["letters"].items() if v]) == 92, ", ".join(split_bad[:8]) or "92 letters")
            check("each in the same place to a thousandth of a cap height, the same width, the same times",
                  worst[0] < 1e-3 and worst[1] < 1e-3 and worst[2] < 1e-4 and worst[3] == 0,
                  f"x {worst[0]:.6f}, y {worst[1]:.6f}, width {worst[2]:.6f} cap heights, t {worst[3]} ms")
            frame = env["skribl"]["frames"][0]
            pts = frame["strokes"]
            firsts, k = [], 0
            for bid in letterfont.BOX_IDS:
                g = full_set["g"][bid]
                firsts.append((pts[k]["t"], pts[k + len(g["p"]) - 1]["t"]))
                k += len(g["p"])
            gaps = [b2[0] - a2[1] for a2, b2 in zip(firsts, firsts[1:])]
            check("posted one after another, each at its own pace, a breath apart", min(gaps) == 300 and max(gaps) == 300,
                  f"gaps {min(gaps)}..{max(gaps)} ms")
        q.keyboard.press("Escape")
        try:
            q.wait_for_function("() => SkriblLetters.view() === 'tiles'", timeout=5000)
        except Exception:
            pass
        check("closing the post sheet brings the tiles back", q.evaluate("SkriblLetters.view()") == "tiles",
              q.evaluate("SkriblLetters.view()"))
        c.close()
        # A hand of 30: the 30 come back, the rest are empty.
        thirty = synth_set(BOX, LN, only=QUICK)
        c, q = open_sheet(b, seed=thirty)
        q.wait_for_function("() => SkriblLetters.view() === 'tiles'")
        titled, res, back, env, split_bad, worst = read_back(q, thirty["g"])
        got = sorted(k for k, v in (back or {"letters": {}})["letters"].items() if v)
        check("a hand of 30 posts its 30, each in its own place, and the other 62 come back empty",
              res["status"] == 201 and back is not None and got == sorted(QUICK) and not split_bad
              and worst[0] < 1e-3 and worst[1] < 1e-3 and worst[3] == 0,
              f"{len(got)} letters back; {', '.join(split_bad[:6]) or 'no letter split wrong'}; x {worst[0]:.6f}")
        c.close()

    # ------------------------------------------------------------------ 9
    if part("LETTERS 9 — words you can read"):
        LUM = """(c) => { const m = c.match(/[\\d.]+/g).map(Number); const f = v => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); };
          return 0.2126 * f(m[0]) + 0.7152 * f(m[1]) + 0.0722 * f(m[2]); }"""
        RATIOS = """([LUM, sels]) => { const lum = eval(LUM);
          const ground = (el) => { for (let e = el; e; e = e.parentElement) { const bg = getComputedStyle(e).backgroundColor;
            if (bg && !/rgba\\(.*,\\s*0\\)$/.test(bg) && bg !== 'transparent') return bg; } return 'rgb(255,255,255)'; };
          const out = {};
          for (const [k, sel] of sels) { const el = document.querySelector(sel); if (!el) continue;
            const a = lum(getComputedStyle(el).color), g = lum(ground(el)), r = el.getBoundingClientRect();
            out[k] = { ratio: (Math.max(a, g) + 0.05) / (Math.min(a, g) + 0.05), h: r.height, w: r.width }; }
          return out; }"""
        BARS = [["title", "#ltTitle"], ["sub", "#ltSub"], ["later", "#ltLater"], ["redo", "#ltRedo"], ["back", "#ltBack"], ["next", "#ltNext"]]
        PAGE = [["ptitle", ".lt-ptitle"], ["psub", ".lt-psub"], ["done", ".lt-pdone"], ["primary", ".lt-primary"], ["second", ".lt-second"],
                ["link", ".lt-link"], ["head", ".lt-gh"], ["count", ".lt-gh span"], ["tile", ".lt-tile:not(.empty)"], ["intro", ".lt-intro p"],
                ["small", ".lt-small"], ["step", ".lt-steps li"], ["num", ".lt-steps i"]]
        TAPS = "() => [...document.querySelectorAll('.lt-page button, .lt-btn, .lt-later')].filter(b => b.checkVisibility()).map(b => { const r = b.getBoundingClientRect(); return Math.min(r.width, r.height); })"
        for dev_name, dev in (("phone", PHONE), ("desk", DESK)):
            for theme in ("light", "dark"):
                words, taps = {}, []
                c, q = open_sheet(b, theme=theme, dev=dev, start=False)
                words.update({"start " + k: v for k, v in q.evaluate(RATIOS, [LUM, PAGE]).items()})
                taps += q.evaluate(TAPS)
                q.click("text=Start with a")
                q.wait_for_function(DRAWING)
                letter_a(q)
                words.update(q.evaluate(RATIOS, [LUM, BARS]))
                taps += q.evaluate(TAPS)
                c.close()
                seed = synth_set(BOX, LN, only=QUICK[:29])
                seed.update({"mode": "seq", "at": letterfont.BOX_IDS.index("?"), "r": False})
                c, q = open_sheet(b, theme=theme, dev=dev, seed=seed)
                q.wait_for_function(DRAWING)
                a_line(q)
                q.click("#ltNext")
                q.wait_for_function("() => SkriblLetters.view() === 'ready'")
                words.update({"ready " + k: v for k, v in q.evaluate(RATIOS, [LUM, PAGE]).items()})
                taps += q.evaluate(TAPS)
                c.close()
                # The tiles, as a person with a hand meets them (Ready's Write
                # with it goes back to Text now, so the page opens on its own).
                c, q = open_sheet(b, theme=theme, dev=dev, seed=synth_set(BOX, LN, only=QUICK))
                q.wait_for_function("() => SkriblLetters.view() === 'tiles'")
                words.update({"tiles " + k: v for k, v in q.evaluate(RATIOS, [LUM, PAGE]).items()})
                taps += q.evaluate(TAPS)
                c.close()
                low = {k: round(v["ratio"], 1) for k, v in words.items() if v["ratio"] < 4.5}
                lowest = min(words.items(), key=lambda kv: kv[1]["ratio"])
                check(f"{dev_name} {theme}: every word on the bars and the pages reads 4.5:1 or more",
                      not low and len(words) >= 20, low or f"{len(words)} words, the lowest {lowest[0]} at {round(lowest[1]['ratio'], 1)}:1")
                check(f"{dev_name} {theme}: every button is 44px and up", min(taps) >= 44, f"smallest {round(min(taps), 1)}px of {len(taps)}")

    # ------------------------------------------------------------------ 10
    if part("LETTERS 10 — keys"):
        c, q = open_sheet(b, dev=DESK)
        q.keyboard.press("e")
        q.keyboard.press("]")
        q.wait_for_timeout(100)
        st = q.evaluate("({ tool, size })")
        check("the Pad's letter keys do nothing here (the eraser, the pen's size)", st["tool"] == "pen" and st["size"] == 6, json.dumps(st))
        B = q.evaluate(BOXPX)
        base = B["top"] + B["lines"]["base"] * B["h"]
        stroke(q, [(B["left"] + B["w"] * 0.45, base - 100), (B["left"] + B["w"] * 0.45, base)])
        stroke(q, [(B["left"] + B["w"] * 0.40, base - 50), (B["left"] + B["w"] * 0.50, base - 50)])
        q.wait_for_timeout(150)
        q.keyboard.press("Control+z")
        q.wait_for_timeout(250)
        g = stored(q, "a")
        check("Ctrl+Z takes back the last stroke, and the letter follows", g and len(g["n"]) == 1 and q.evaluate("strokes.length") == g["n"][0],
              g and f"strokes {g['n']}")
        q.keyboard.press("ArrowRight")
        q.wait_for_timeout(250)
        at1 = q.evaluate("SkriblLetters.at()")
        q.keyboard.press("ArrowLeft")
        q.wait_for_timeout(250)
        check("the arrows move between letters", at1 == 1 and q.evaluate("SkriblLetters.at()") == 0)
        c.close()

    # ------------------------------------------------------------------ 11
    if part("LETTERS 11 — the first 30, and Ready"):
        c, q = open_sheet(b, start=False)
        order = q.evaluate("SkriblLetters.order()")
        check("the letters come a to z, then . , ! ?, then the rest from A",
              order[:30] == QUICK and order[30] == "A" and sorted(order) == sorted(letterfont.BOX_IDS), " ".join(order[:32]))
        c.close()
        seed = synth_set(BOX, LN, only=QUICK[:29])
        seed.update({"mode": "seq", "at": letterfont.BOX_IDS.index("?"), "r": False})
        c, q = open_sheet(b, seed=seed)
        q.wait_for_function(DRAWING)
        on30 = sub_text(q)
        a_line(q)
        q.click("#ltNext")
        try:
            q.wait_for_function("() => SkriblLetters.view() !== 'draw'", timeout=5000)
        except Exception:
            pass   # the check below says what came instead
        r = q.evaluate("""() => ({ view: SkriblLetters.view(), title: (document.querySelector('.lt-ptitle') || {}).textContent,
          buttons: [...document.querySelectorAll('.lt-page button')].map(b => b.textContent) })""")
        check("the 30th letter opens Ready: Add the rest and Write with it",
              on30.startswith("? question mark · 30 of 30") and r["view"] == "ready" and r["title"] == "Your hand is ready"
              and "Add the rest · 62" in r["buttons"] and "Write with it" in r["buttons"], f"{on30} / {json.dumps(r)}")
        if r["view"] == "ready":
            page_button(q, "Add the rest").click()
            q.wait_for_function(DRAWING)
        check("Add the rest goes on with A, 31 of 92", sub_text(q).startswith("A · 31 of 92"), sub_text(q))
        q.click("#ltBack")
        q.wait_for_timeout(250)
        a_line(q, 0.6)
        q.click("#ltNext")
        q.wait_for_timeout(400)
        check("and Ready comes once: Next from the 30th again goes on to A",
              q.evaluate("SkriblLetters.view()") == "draw" and sub_text(q).startswith("A ·"), f"{q.evaluate('SkriblLetters.view()')} {sub_text(q)}")
        c.close()

    # ------------------------------------------------------------------ 12
    if part("LETTERS 12 — the tiles"):
        full_set = synth_set(BOX, LN)
        c, q = open_sheet(b, seed=full_set)
        q.wait_for_function("() => SkriblLetters.view() === 'tiles'")
        t = q.evaluate("""() => ({ tiles: document.querySelectorAll('.lt-tile').length, empty: document.querySelectorAll('.lt-tile.empty').length,
          heads: [...document.querySelectorAll('.lt-gh')].map(h => h.textContent), sub: document.querySelector('.lt-psub').textContent,
          drawn: [...document.querySelectorAll('.lt-tile:not(.empty) path')].filter(p => (p.getAttribute('d') || '').length > 10).length })""")
        check("every letter on the tiles, drawn in its own hand, under its group and count",
              t["tiles"] == 92 and t["empty"] == 0 and t["drawn"] == 92 and t["heads"][0] == "Letters26 of 26"
              and len(t["heads"]) == 7 and t["sub"].startswith("92 of 92"), json.dumps(t)[:220])
        before = stored(q, "g")
        q.click(".lt-tile[data-id='g']")
        q.wait_for_function(DRAWING)
        q.wait_for_timeout(200)
        one = q.evaluate("""() => ({ mode: SkriblLetters.mode(), n: strokes.length, sub: document.getElementById('ltSub').textContent,
          buttons: [...document.querySelectorAll('.lt-btn')].map(b => b.textContent + (b.disabled ? ' (off)' : '')),
          ghost: (() => { const g = document.getElementById('ltGuides'), d = g.getContext('2d').getImageData(0, 0, g.width, g.height).data;
            // The old letter's faint ink, read AWAY from the guide lines, which
            // are as faint (a count across them passed with no letter there).
            const L = SkriblLetters, b = L.box(), ln = L.lines(), lg = getCanvasLogicalSize(), ky = g.height / lg.height;
            const ys = Object.values(ln).map(f => (b.y + f * b.h) * ky);
            let n = 0; for (let y = 0; y < g.height; y++) { if (ys.some(v => Math.abs(v - y) < 5)) continue;
              for (let x = 0; x < g.width; x += 2) { const a = d[(y * g.width + x) * 4 + 3]; if (a > 70 && a < 140) n++; } }
            return n; })() })""")
        check("tap g: it waits to be drawn again, the old one faint behind it, Redo, Cancel, Done",
              one["mode"] == "one" and one["n"] == 0 and one["sub"].startswith("g · draw it again")
              and one["buttons"] == ["Redo (off)", "Cancel", "Done (off)"] and one["ghost"] > 200, json.dumps(one))
        a_line(q)
        kept_mid = stored(q, "g") == before
        q.click("#ltBack")
        q.wait_for_function("() => SkriblLetters.view() === 'tiles'")
        check("Cancel keeps the old g, even after a stroke", kept_mid and stored(q, "g") == before)
        q.click(".lt-tile[data-id='g']")
        q.wait_for_function(DRAWING)
        a_line(q)
        q.click("#ltNext")
        q.wait_for_function("() => SkriblLetters.view() === 'tiles'")
        after = stored(q, "g")
        check("Done keeps the new g", after and after != before and len(after["n"]) == 1, after and f"strokes {after['n']}")
        c.close()
        thirty = synth_set(BOX, LN, only=QUICK)
        c, q = open_sheet(b, seed=thirty)
        q.wait_for_function("() => SkriblLetters.view() === 'tiles'")
        e = q.evaluate("() => ({ empty: document.querySelectorAll('.lt-tile.empty').length, label: document.querySelector('.lt-tile[data-id=\"Q\"]').getAttribute('aria-label') })")
        q.click(".lt-tile[data-id='Q']")
        q.wait_for_function(DRAWING)
        add = sub_text(q)
        a_line(q)
        q.click("#ltNext")
        q.wait_for_function("() => SkriblLetters.view() === 'tiles'")
        check("a letter not drawn shows a +, and tapping it adds it",
              e["empty"] == 62 and e["label"] == "Add Q" and add.startswith("Q · add it") and stored(q, "Q") is not None
              and q.evaluate("document.querySelectorAll('.lt-tile.empty').length") == 61, f"{json.dumps(e)} / {add}")
        c.close()

    # ------------------------------------------------------------------ 13
    if part("LETTERS 13 — a copy, and starting over"):
        full_set = synth_set(BOX, LN)
        c, q = open_sheet(b, seed=full_set)
        q.wait_for_function("() => SkriblLetters.view() === 'tiles'")
        with q.expect_download() as dl:
            page_button(q, "Save a copy").click()
        d = dl.value
        tmp = Path(tempfile.mkdtemp()) / "my-hand.skriblhand"
        d.save_as(str(tmp))
        copy = json.loads(tmp.read_text())
        check("Save a copy makes a file with every letter, as it is kept",
              d.suggested_filename == "my-hand.skriblhand" and copy.get("type") == "skribl-hand"
              and copy.get("g") == full_set["g"], f"{d.suggested_filename}, {len(copy.get('g', {}))} letters")
        page_button(q, "Start over").click()
        q.wait_for_function("() => SkriblLetters.view() === 'start'")
        empty = len(stored(q)["g"]) == 0
        q.click("#toast .toast-action")
        q.wait_for_function("() => SkriblLetters.view() === 'tiles'")
        check("Start over clears them, and its Undo brings every one back",
              empty and stored(q)["g"] == full_set["g"])
        page_button(q, "Start over").click()
        q.wait_for_function("() => SkriblLetters.view() === 'start'")
        q.set_input_files("#ltOpenCopy", str(tmp))
        q.wait_for_function("() => SkriblLetters.view() === 'tiles'")
        check("Open a copy puts a saved hand back", stored(q)["g"] == full_set["g"])
        bad = Path(tempfile.mkdtemp()) / "not-a-hand.json"
        bad.write_text(json.dumps({"type": "something-else", "v": 1, "g": {"a": {"p": [[0, 0, 1, 0]], "n": [1]}}}))
        q.set_input_files("#ltOpenCopy", str(bad))
        q.wait_for_timeout(600)
        said = q.evaluate("(() => { const t = document.getElementById('toast'); return t.hidden ? '' : t.textContent; })()")
        check("a file that isn't a hand changes nothing, and says so",
              stored(q)["g"] == full_set["g"] and "isn’t a copy of a hand" in said, said)
        c.close()

    b.close()

passed = sum(1 for r in results if r[0])
print(f"\n{passed}/{len(results)} passed")
sys.exit(0 if passed == len(results) else 1)
