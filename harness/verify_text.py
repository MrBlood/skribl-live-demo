"""Text: words that write themselves (lib/textwrite.js, editor_text.js, Flip's
side in flip.js; FUTURE.md 6ab). The owner said yes to the mock: Text in
Shape's picker, a typing sheet with Style, Size and Speed, the words placed
before they are ink, written with honest timing, one Undo for the line, and
Mirror leaving them alone. Each row holds a promise:

  1. THE LETTERING: Print and Script carry letters, numbers, punctuation and
     the common accents, set on their own baseline at one cap height; Skribl
     is the owner's 92, each letter's time starting at 0 and running forward;
     the license travels with the fonts; all three are served.
  2. THE PICKER: Text is Shape's fifth kind on both editors; picking it
     chooses Shape and Text, puts the picker away, and brings the typing
     sheet straight up, the words in the middle of the drawing that shows.
  3. NOTHING UNTIL WRITE IT: the sheet opens with the field ready, draws
     nothing and arms no take; Close and Escape leave nothing behind; with
     Text chosen, a press opens the sheet again where it was.
  4. PLACED BEFORE INK: typed words show in a box above the sheet, painted
     in the pen's colour, and nothing is ink yet; dragging the box moves the
     words by the drag; they cannot be dragged under the sheet; a press
     elsewhere moves them there without the sheet moving; a colour chosen
     while the sheet is up is the one they show in.
  5. WRITTEN IN TIME: Write it closes the sheet and the words write
     themselves, stroke by stroke over the time the sheet said; each point
     keeps the time the plan gave it on the take's clock, forward only, where
     the preview showed it; a blank Pad's take starts when the words do.
  6. ONE UNDO: Undo takes the whole line back, on the Pad and on Flip, and
     Redo puts it back.
  7. MIRROR LEAVES WORDS ALONE: with Mirror on, the words are written once.
  8. FINISHED EARLY, HONESTLY: anything done while the words write finishes
     them at once with the times they were due, and the Pad's clock moves on
     past them.
  9. SPEED: the sheet says how long the words take; 2x takes half as long and
     1/4x four times; - and + step the stops and stop at the ends.
 10. STYLES AND HANDS: each style is written in itself; with no hand, Yours
     is + Make yours and Skribl is chosen; with one, Yours is chosen, the
     sheet counts its letters, and a letter not drawn comes in Print; a
     hand's letter keeps its own pace, a pause held to a quarter second.
 11. THE DOOR: Make yours and Edit your hand go to Your hand, saying which
     editor; Close, Done and Write with it come back with Text chosen.
 12. FLIP'S PAGE: the words go on the page they were placed on, one Undo
     entry, and on a page that draws itself they write themselves.
 13. WORDS YOU CAN READ: every word on the sheet and the box reads 4.5:1 or
     more against what is behind it, light and dark, phone and desk; the
     field is 16px; every button is 44px (the slider's - and + are the app's
     own); the sheet never covers the words.
 14. KIND TRANSITIONS: the sheet rises over several frames, never a jump,
     and with Reduce Motion is simply there; the dashed box is gone the
     frame the words start writing.
 15. A FINISHED TAKE (the owner's iPhone: the press was refused there):
     choosing Text opens the sheet and a press moves the words, with no
     refusal; Write it carries the take on as Keep drawing does, and one
     Undo takes back only the words.
 16. THE KEYBOARD (the owner's iPhone: the bar over it covered the field):
     with the keyboard up, the sheet sits on it and is only the words and
     Write it, the words above it (with no keyboard up, the whole sheet); the
     keyboard's done key puts it away and writes nothing; when the keyboard
     goes, the sheet comes down and the words come back to where they were
     put; the x and Write it pressed with the keyboard up do what they say;
     on a desk, Enter writes.

For calibration, TEXT_PART=<words of a part's label> runs that part alone.
A real run sets none.
"""
import json
import os
import sys
import urllib.request
from pathlib import Path

from assertions import make_check
import browsing

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "tools"))
import letterfont  # noqa: E402

BASE = os.environ.get("SKRIBL_BASE", "http://127.0.0.1:5001")
ROOT = HERE.parent
FONTS = ROOT / "skribl" / "static" / "fonts"
results = []
check = make_check(results, detail_on_pass=True)

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("SKIP: playwright is not installed")
    sys.exit(0)

PART = os.environ.get("TEXT_PART", "")
PHONE = dict(viewport={"width": 402, "height": 874}, device_scale_factor=2, is_mobile=True, has_touch=True)
DESK = dict(viewport={"width": 1280, "height": 860})
ROUTE = {"pad": "/skribl-pad", "flip": "/flip"}
CANVAS = {"pad": "#canvas", "flip": "#pad"}
UNDO = {"pad": "#undoBtn", "flip": "#undo"}
REDO = {"pad": "#redoBtn", "flip": "#redo"}
TOOLNOW = {"pad": "() => [tool, shapeKind]", "flip": "() => [flipTool, shapeKind]"}
COUNT = {"pad": "() => [strokes.length, strokeGroups.length]",
         "flip": "() => [frame().strokes.length, frame().strokeGroups.length]"}
POINTS = {"pad": "(n0) => strokes.slice(n0).map(p => [p.x, p.y, p.t, p.size, p.color])",
          "flip": "(n0) => frame().strokes.slice(n0).map(p => [p.x, p.y, p.t, p.size, p.color])"}
LOGICAL = {"pad": "() => { const s = getCanvasLogicalSize(); return [s.width, s.height]; }",
           "flip": "() => [CW, CH]"}
PREFS = "skribl.text.v1"
HAND = "skribl.letters.v1"
QUICK = list("abcdefghijklmnopqrstuvwxyz") + [".", ",", "!", "?"]
OWNER = json.loads((FONTS / "text-skribl.json").read_text(encoding="utf-8"))


def part(label):
    if PART and PART.lower() not in label.lower():
        return False
    print("\n" + label)
    return True


def undelta(a, w):
    out, prev = [], [0] * w
    for i in range(0, len(a) - w + 1, w):
        row = [a[i + j] + prev[j] for j in range(w)]
        out.append(row)
        prev = row
    return out


def hand_seed(ids):
    """A Your hand store holding the owner's letters `ids`, drawn in a 200px box."""
    u = OWNER["u"]
    g = {}
    for k in ids:
        p, n = [], []
        for line in OWNER["g"][k]:
            pts = undelta(line, 3)
            n.append(len(pts))
            for x, y, t in pts:
                p.append([round(100 + x / u * 116, 2), round(148 - y / u * 116, 2), 6, t])
        g[k] = {"p": p, "n": n, "b": [0, 0, 200, 200], "l": [0.16, 0.334, 0.74, 0.94], "c": "#7c5cff"}
    return {"v": 1, "o": 2, "at": None, "mode": "tiles", "r": True, "g": g}


def open_editor(b, editor="pad", *, theme="light", dev=PHONE, prefs=None, hand=None, reduce=False, query=""):
    kw = dict(dev)
    if reduce:
        kw["reduced_motion"] = "reduce"
    c = b.new_context(color_scheme=theme, **kw)
    init = ""
    if prefs is not None:
        init += "localStorage.setItem(%s, %s);" % (json.dumps(PREFS), json.dumps(json.dumps(prefs)))
    if hand is not None:
        init += "localStorage.setItem(%s, %s);" % (json.dumps(HAND), json.dumps(json.dumps(hand)))
    if init:
        c.add_init_script("if (!sessionStorage.getItem('tx-seeded')) { sessionStorage.setItem('tx-seeded', '1');" + init + "}")
    q = c.new_page()
    errors = []
    q.on("pageerror", lambda e: errors.append(str(e)[:160]))
    q.on("console", lambda m: errors.append(m.text[:160]) if m.type == "error" else None)
    q._tx_errors = errors
    q._tx_editor = editor
    q._tx_touch = bool(kw.get("has_touch"))
    browsing.goto(q, BASE, ROUTE[editor] + "?theme=" + theme + (("&" + query) if query else ""))
    q.wait_for_function("() => !!window.SkriblText")
    q.wait_for_timeout(300)
    q.evaluate("() => window.SkriblHints && SkriblHints.hide()")
    return c, q


def choose_text(q):
    q.evaluate("() => document.querySelector('#shapeSeg [data-shape=\"text\"]').click()")
    q.wait_for_timeout(100)


def at(q, fx, fy):
    """A point on the canvas, as fractions of its box, on screen."""
    r = q.evaluate("(s) => { const r = document.querySelector(s).getBoundingClientRect(); return [r.left, r.top, r.width, r.height]; }",
                   CANVAS[q._tx_editor])
    return r[0] + fx * r[2], r[1] + fy * r[3]


def tap(q, x, y):
    if q._tx_touch:
        q.touchscreen.tap(x, y)
    else:
        q.mouse.click(x, y)
    q.wait_for_timeout(350)


def draw_line(q, fx0, fy0, fx1, fy1, n=20):
    x0, y0 = at(q, fx0, fy0)
    x1, y1 = at(q, fx1, fy1)
    q.mouse.move(x0, y0)
    q.mouse.down()
    for i in range(1, n + 1):
        q.mouse.move(x0 + (x1 - x0) * i / n, y0 + (y1 - y0) * i / n)
    q.mouse.up()
    q.wait_for_timeout(150)


def type_words(q, words):
    """The words in the field, as typing puts them there; False if no plan
    with ink came of them (the checks after say what came instead)."""
    q.evaluate("(w) => { const f = document.getElementById('txField'); f.value = w; f.dispatchEvent(new Event('input', { bubbles: true })); }", words)
    try:
        q.wait_for_function("() => { const p = SkriblText.plan(); return !!p && p.strokes.length > 0; }", timeout=15000)
    except Exception:
        return False
    q.wait_for_timeout(150)
    return True


def set_speed(q, i):
    q.evaluate("(i) => { const s = document.getElementById('txSpeed'); s.value = String(i); s.dispatchEvent(new Event('input', { bubbles: true })); }", i)
    q.wait_for_timeout(80)


PLAN = """() => { const p = SkriblText.plan(), a = SkriblText.anchor(); if (!p) return null;
  return { ms: p.ms, n: p.strokes.length, pts: p.points, box: p.box, anchor: a, skipped: p.skipped,
           flat: p.strokes.map(s => s.map(q => [q.x, q.y, q.t])) }; }"""
SHEET = """() => { const s = document.getElementById('txSheet'), pl = document.getElementById('txPlace');
  const r = s.getBoundingClientRect(), b = pl.getBoundingClientRect();
  return { open: SkriblText.isOpen(), hidden: s.hidden, top: r.top, focus: document.activeElement && document.activeElement.id,
           place: pl.hidden ? null : [b.left, b.top, b.right, b.bottom],
           out: document.getElementById('txSpeedOut').textContent, go: !document.getElementById('txGo').disabled }; }"""


def waited(q, cond, timeout=15000):
    """True once `cond` holds; False if it never did (the check after says what came instead)."""
    try:
        q.wait_for_function(cond, timeout=timeout)
        return True
    except Exception:
        return False


def write_and_wait(q, timeout=60000):
    q.click("#txGo")
    q.wait_for_function("() => !SkriblText.isWriting()", timeout=timeout)
    q.wait_for_timeout(150)


with sync_playwright() as p:
    b = p.chromium.launch()

    # ------------------------------------------------------------------ 1
    if part("TEXT 1 — the lettering"):
        docs = {k: json.loads((FONTS / ("text-%s.json" % k)).read_text(encoding="utf-8")) for k in ("print", "script", "skribl")}
        need = (list("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")
                + list(".,!?'\"-:;()&@#/+") + list("áéíóúàèñçüöäÉÑÇ"))
        for k in ("print", "script"):
            d = docs[k]
            u = d["u"]
            missing = [ch for ch in need if ch not in d["g"]]
            lows = sorted(min(y for line in d["g"][ch][1:] for y in [pt[1] for pt in undelta(line, 2)]) for ch in "acemnorsuvwz")
            caps = sorted(max(y for line in d["g"][ch][1:] for y in [pt[1] for pt in undelta(line, 2)]) for ch in "BDEFHIKLMNPRTUVWXZ")
            base, cap = lows[len(lows) // 2] / u, caps[len(caps) // 2] / u
            emoji = [ch for ch in d["g"] if ord(ch) > 0x2fff]
            check(f"{k}: letters, numbers, punctuation and the common accents, no emoji",
                  d["kind"] == "font" and not missing and not emoji, f"missing {missing}, emoji {emoji}, {len(d['g'])} glyphs")
            check(f"{k}: on its own baseline at one cap height",
                  abs(base) < 0.02 and abs(cap - 1) < 0.03, f"baseline {base:.3f}, cap {cap:.3f} cap heights")
        d = docs["skribl"]
        times_ok = all(undelta(line, 3)[0][2] >= 0 and all(b2[2] >= a2[2] for a2, b2 in zip(undelta(line, 3), undelta(line, 3)[1:]))
                       for g in d["g"].values() for line in g)
        firsts = [undelta(g[0], 3)[0][2] for g in d["g"].values()]
        check("Skribl: the owner's 92, every one drawn",
              d["kind"] == "hand" and sorted(d["g"]) == sorted(letterfont.BOX_IDS) and all(d["g"][k2] for k2 in d["g"]),
              f"{len(d['g'])} letters")
        check("Skribl: each letter's time starts at 0 and only runs forward",
              times_ok and all(f == 0 for f in firsts), f"first times {sorted(set(firsts))[:5]}")
        ofl = (FONTS / "OFL.txt").read_text(encoding="utf-8")
        check("the SIL Open Font License travels with Print and Script, naming both",
              "SIL OPEN FONT LICENSE" in ofl and "Version 1.1" in ofl and "EMS Readability" in ofl and "EMS Allure" in ofl, f"{len(ofl)} chars")
        served = {}
        for k in ("print", "script", "skribl"):
            with urllib.request.urlopen(BASE + "/static/skribl/fonts/text-%s.json" % k, timeout=30) as r:
                served[k] = (r.status, json.loads(r.read().decode("utf-8")) == docs[k])
        check("all three are served as they are in the tree", all(s == (200, True) for s in served.values()), str(served))

    # ------------------------------------------------------------------ 2
    if part("TEXT 2 — the picker"):
        for editor in ("pad", "flip"):
            c, q = open_editor(b, editor)
            names = q.evaluate("() => [...document.querySelectorAll('#shapeSeg [data-shape]')].map(b => b.textContent.trim())")
            check(f"{editor}: Text is Shape's fifth kind", names == ["Line", "Rect", "Oval", "Poly", "Text"], str(names))
            if "Text" not in names:
                check(f"{editor}: picking it chooses Shape and Text, and puts the picker away", False, "no Text to pick")
                c.close()
                continue
            vis = q.evaluate("() => { const s = document.getElementById('shapeToolBtn'); return !!s && !!s.getClientRects().length; }")
            if vis:
                q.click("#shapeToolBtn")
            else:
                q.click("#toolMoreBtn"); q.wait_for_timeout(400)
                q.click('.tool-tray-btn[data-tool="shape"]'); q.wait_for_timeout(300)
                if q.evaluate("() => document.getElementById('shapePop').hidden"):
                    q.click("#shapeToolBtn")
            q.wait_for_timeout(350)
            q.click('#shapeSeg [data-shape="text"]')
            q.wait_for_timeout(300)
            now = q.evaluate(TOOLNOW[editor])
            pop = q.evaluate("() => document.getElementById('shapePop').hidden")
            check(f"{editor}: picking it chooses Shape and Text, and puts the picker away",
                  now == ["shape", "text"] and pop, f"{now}, picker hidden {pop}")
            q.wait_for_timeout(300)
            up = q.evaluate("""(sel) => { const a = SkriblText.anchor(), c = document.querySelector(sel).getBoundingClientRect();
              const lg = (typeof getCanvasLogicalSize === 'function') ? getCanvasLogicalSize() : { width: CW, height: CH };
              const k = c.width / lg.width, s = document.getElementById('txSheet').getBoundingClientRect();
              if (!a) return { open: SkriblText.isOpen(), a: null };
              const x = c.left + a.x * k, y = c.top + a.y * c.height / lg.height;
              return { open: SkriblText.isOpen(), focus: document.activeElement && document.activeElement.id,
                       seen: x > Math.max(c.left, 0) && x < Math.min(c.right, innerWidth) && y > Math.max(c.top, 0) && y < s.top }; }""",
                            CANVAS[editor])
            check(f"{editor}: ...and the typing sheet comes straight up, the words in the drawing that shows above it",
                  up["open"] and up.get("focus") == "txField" and up.get("seen"), str(up))
            check(f"{editor}: no errors", not q._tx_errors, str(q._tx_errors[:2]))
            c.close()

    # ------------------------------------------------------------------ 3
    if part("TEXT 3 — nothing until Write it"):
        c, q = open_editor(b, "pad")
        n0 = q.evaluate(COUNT["pad"])
        choose_text(q)
        q.wait_for_timeout(300)
        s = q.evaluate(SHEET)
        after = q.evaluate("() => [strokes.length, strokeGroups.length, recording, hasContent]")
        check("choosing Text opens the sheet, the words' field ready",
              s["open"] and not s["hidden"] and s["focus"] == "txField", json.dumps(s)[:160])
        check("...and draws nothing and arms no take", after[:2] == n0 and after[2] is False and after[3] is False, str(after))
        q.click("#txClose")
        q.wait_for_timeout(500)
        s = q.evaluate(SHEET)
        after = q.evaluate("() => [strokes.length, strokeGroups.length, recording, hasContent]")
        check("Close leaves nothing behind", not s["open"] and s["hidden"] and s["place"] is None and after[:3] == n0 + [False], f"{s} {after}")
        tap(q, *at(q, 0.3, 0.3))
        s = q.evaluate(SHEET)
        a = q.evaluate("() => SkriblText.anchor()")
        want = q.evaluate("() => { const lg = getCanvasLogicalSize(); return [lg.width * 0.3, lg.height * 0.3]; }")
        check("with Text chosen, a press opens it again where the press was",
              s["open"] and a is not None and abs(a["x"] - want[0]) <= 2 and abs(a["y"] - want[1]) <= 2, f"{s['open']} {a} for {want}")
        type_words(q, "Hi")
        q.keyboard.press("Escape")
        q.wait_for_timeout(500)
        s = q.evaluate(SHEET)
        after = q.evaluate("() => [strokes.length, strokeGroups.length, recording]")
        check("Escape closes it the same way, the typed words still not ink", not s["open"] and after == n0 + [False], f"{s['open']} {after}")
        c.close()

    # ------------------------------------------------------------------ 4
    if part("TEXT 4 — placed before ink"):
        c, q = open_editor(b, "pad", prefs={"style": "print", "size": "M", "speed": 4})
        draw_line(q, 0.2, 0.15, 0.8, 0.15)
        choose_text(q)
        n0 = q.evaluate(COUNT["pad"])
        tap(q, *at(q, 0.5, 0.3))
        type_words(q, "Hello")
        s = q.evaluate(SHEET)
        ink = q.evaluate("""() => { const c = document.getElementById('txPreview'), d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data;
          let n = 0, col = null; for (let i = 3; i < d.length; i += 4) if (d[i] > 200) { n++; if (!col) col = [d[i-3], d[i-2], d[i-1]]; }
          const pen = penColorFor(color); return { n: n, col: col, pen: pen }; }""")
        hexpen = ink["pen"].lstrip("#")
        pen_rgb = [int(hexpen[i:i + 2], 16) for i in (0, 2, 4)] if len(hexpen) == 6 else None
        check("the words show in a box above the sheet", s["place"] is not None and s["place"][3] <= s["top"] + 0.5,
              f"box {s['place']}, sheet top {s['top']}")
        check("...painted in the pen's colour", ink["n"] > 200 and pen_rgb is not None and ink["col"] is not None
              and max(abs(a - b2) for a, b2 in zip(ink["col"], pen_rgb)) <= 3, f"{ink}")
        check("...and nothing is ink yet", q.evaluate(COUNT["pad"]) == n0, str(q.evaluate(COUNT["pad"])))
        a0 = q.evaluate("() => SkriblText.anchor()")
        k = q.evaluate("() => { const r = canvas.getBoundingClientRect(); return r.width / getCanvasLogicalSize().width; }")
        box = s["place"]
        cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
        q.mouse.move(cx, cy)
        q.mouse.down()
        for i in range(1, 11):
            q.mouse.move(cx - 6 * i, cy - 9 * i)
        q.mouse.up()
        q.wait_for_timeout(120)
        a1 = q.evaluate("() => SkriblText.anchor()")
        moved = (round((a1["x"] - a0["x"]) * k, 1), round((a1["y"] - a0["y"]) * k, 1))
        check("dragging the box moves the words by the drag", abs(moved[0] + 60) <= 1.5 and abs(moved[1] + 90) <= 1.5,
              f"moved {moved}px for a drag of (-60, -90)")
        q.mouse.move(cx - 60, cy - 90)
        q.mouse.down()
        for i in range(1, 16):
            q.mouse.move(cx - 60, cy - 90 + 60 * i)
        q.mouse.up()
        q.wait_for_timeout(120)
        s = q.evaluate(SHEET)
        check("...and cannot be dragged under the sheet", s["place"] is not None and s["place"][3] <= s["top"] + 0.5,
              f"box bottom {s['place'][3] if s['place'] else None}, sheet top {s['top']}")
        # A press elsewhere on the drawing while the sheet is up moves the
        # words there, and the sheet stays where it is (no second entrance).
        px, py = at(q, 0.35, 0.22)
        tops = q.evaluate("""([x, y]) => new Promise(res => { const s = document.getElementById('txSheet'), out = [];
          const r = canvas.getBoundingClientRect(), lg = getCanvasLogicalSize();
          SkriblText.place({ x: (x - r.left) * lg.width / r.width, y: (y - r.top) * lg.height / r.height });
          const t0 = performance.now();
          (function f() { out.push(Math.round(s.getBoundingClientRect().top)); if (performance.now() - t0 < 400) requestAnimationFrame(f); else res(out); })(); })""", [px, py])
        a2 = q.evaluate("() => SkriblText.anchor()")
        want = q.evaluate("([x, y]) => { const r = canvas.getBoundingClientRect(), lg = getCanvasLogicalSize(); return [(x - r.left) * lg.width / r.width, (y - r.top) * lg.height / r.height]; }", [px, py])
        check("a press elsewhere moves the words there, and the sheet stays still",
              abs(a2["x"] - want[0]) <= 1 and abs(a2["y"] - want[1]) <= 1 and len(set(tops)) == 1,
              f"words at {round(a2['x'])},{round(a2['y'])} for a press at {round(want[0])},{round(want[1])}; the sheet at {sorted(set(tops))[:4]}")
        # The pen changed while the sheet is up: the words show in its colour.
        q.evaluate("() => { color = '#e0452b'; }")
        q.wait_for_timeout(200)
        ink2 = q.evaluate("""() => { const c = document.getElementById('txPreview'), d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data;
          for (let i = 3; i < d.length; i += 4) if (d[i] > 200) return [d[i-3], d[i-2], d[i-1]]; return null; }""")
        pen2 = q.evaluate("() => penColorFor(color)").lstrip("#")
        rgb2 = [int(pen2[i:i + 2], 16) for i in (0, 2, 4)] if len(pen2) == 6 else None
        check("the words follow the pen: a colour chosen while the sheet is up is the one they show in",
              ink2 is not None and rgb2 is not None and max(abs(a3 - b3) for a3, b3 in zip(ink2, rgb2)) <= 3, f"preview {ink2}, pen {rgb2}")
        check("no errors", not q._tx_errors, str(q._tx_errors[:2]))
        c.close()

    # ------------------------------------------------------------------ 5
    if part("TEXT 5 — written in time"):
        c, q = open_editor(b, "pad", prefs={"style": "print", "size": "M", "speed": 4})
        choose_text(q)
        tap(q, *at(q, 0.5, 0.35))
        type_words(q, "Hi there")
        plan = q.evaluate(PLAN)
        n0 = q.evaluate(COUNT["pad"])
        q.click("#txGo")
        q.wait_for_timeout(int(plan["ms"] * 0.45))
        mid = q.evaluate("() => [strokes.length, strokeGroups.length, SkriblText.isWriting(), SkriblText.isOpen()]")
        q.wait_for_function("() => !SkriblText.isWriting()", timeout=60000)
        q.wait_for_timeout(150)
        end = q.evaluate("() => [strokes.length, strokeGroups.length, recording]")
        pts = q.evaluate(POINTS["pad"], n0[0])
        check("Write it closes the sheet and the words write themselves, stroke by stroke",
              mid[2] and not mid[3] and n0[1] < mid[1] < n0[1] + plan["n"], f"half way: {mid[1] - n0[1]} of {plan['n']} strokes")
        check("every stroke and point of the plan is kept", end[1] - n0[1] == plan["n"] and len(pts) == plan["pts"],
              f"{end[1] - n0[1]} strokes of {plan['n']}, {len(pts)} points of {plan['pts']}")
        flat = [pt for s in plan["flat"] for pt in s]
        t0 = pts[0][2] - flat[0][2] if pts else 0
        off = max((abs((pt[2] - t0) - f[2]) for pt, f in zip(pts, flat)), default=99)
        forward = all(b2[2] >= a2[2] for a2, b2 in zip(pts, pts[1:]))
        check("each point keeps the time the plan gave it on the take's clock, forward only",
              off <= 1 and forward and t0 >= 0, f"worst {off}ms off, forward {forward}, t0 {t0}")
        where = max((max(abs(pt[0] - (f[0] + plan["anchor"]["x"])), abs(pt[1] - (f[1] + plan["anchor"]["y"]))) for pt, f in zip(pts, flat)), default=99)
        check("...where the preview showed it", where <= 0.01, f"furthest {where} drawing units")
        check("a blank Pad's take starts when the words do", end[2] is True and n0 == [0, 0], f"{n0} -> {end}")
        dur = q.evaluate("() => getPlaybackDuration()")
        check("the replay writes them over about the time the sheet said, pauses tightened",
              plan["ms"] * 0.5 <= dur <= plan["ms"] + 50, f"replay {dur}ms, the sheet's {plan['ms']}ms")
        c.close()

    # ------------------------------------------------------------------ 6
    if part("TEXT 6 — one Undo"):
        for editor in ("pad", "flip"):
            c, q = open_editor(b, editor, prefs={"style": "print", "size": "M", "speed": 8})
            draw_line(q, 0.2, 0.15, 0.8, 0.15)
            n0 = q.evaluate(COUNT[editor])
            choose_text(q)
            tap(q, *at(q, 0.5, 0.35))
            type_words(q, "Hello")
            plan = q.evaluate(PLAN)
            write_and_wait(q)
            n1 = q.evaluate(COUNT[editor])
            q.click(UNDO[editor])
            q.wait_for_timeout(300)
            n2 = q.evaluate(COUNT[editor])
            q.click(REDO[editor])
            q.wait_for_timeout(300)
            n3 = q.evaluate(COUNT[editor])
            check(f"{editor}: one Undo takes the whole line back", n1[1] - n0[1] == plan["n"] and n2 == n0, f"{n0} -> {n1} -> undo {n2}")
            check(f"{editor}: and Redo puts it back", n3 == n1, f"redo {n3}")
            c.close()

    # ------------------------------------------------------------------ 7
    if part("TEXT 7 — Mirror leaves words alone"):
        for editor in ("pad", "flip"):
            c, q = open_editor(b, editor, prefs={"style": "print", "size": "M", "speed": 8})
            q.evaluate("() => SkriblMirror.setMode('vertical')")
            draw_line(q, 0.2, 0.15, 0.4, 0.2)
            n0 = q.evaluate(COUNT[editor])
            choose_text(q)
            tap(q, *at(q, 0.5, 0.35))
            type_words(q, "Hello")
            plan = q.evaluate(PLAN)
            write_and_wait(q)
            n1 = q.evaluate(COUNT[editor])
            check(f"{editor}: with Mirror on, a pen line is mirrored and the words are written once",
                  n0[1] == 2 and n1[1] - n0[1] == plan["n"] and n1[0] - n0[0] == plan["pts"], f"line {n0}, then {n1}, plan {plan['n']}/{plan['pts']}")
            c.close()

    # ------------------------------------------------------------------ 8
    if part("TEXT 8 — finished early, honestly"):
        c, q = open_editor(b, "pad", prefs={"style": "print", "size": "M", "speed": 0})
        choose_text(q)
        tap(q, *at(q, 0.5, 0.35))
        type_words(q, "Hello there")
        plan = q.evaluate(PLAN)
        q.click("#txGo")
        q.wait_for_timeout(600)
        q.keyboard.press("Shift")
        q.wait_for_timeout(100)
        r = q.evaluate("""() => ({ writing: SkriblText.isWriting(), n: strokeGroups.length, pts: strokes.length,
          last: strokes.length ? strokes[strokes.length - 1].t : null, clock: Date.now() - startTime })""")
        pts = q.evaluate(POINTS["pad"], 0)
        flat = [pt for s in plan["flat"] for pt in s]
        t0 = pts[0][2] - flat[0][2] if pts else 0
        off = max((abs((pt[2] - t0) - f[2]) for pt, f in zip(pts, flat)), default=99)
        check("a key while the words write finishes them at once, every stroke with the time it was due",
              not r["writing"] and r["n"] == plan["n"] and r["pts"] == plan["pts"] and off <= 1, f"{r}, worst {off}ms")
        last = r["last"] if r["last"] is not None else 10 ** 9
        check("...and the Pad's clock moves on past them", r["clock"] >= last, f"clock {r['clock']}ms, last point {r['last']}ms")
        # The next line, with the pen: Text would only open the sheet again.
        q.evaluate("() => setTool('pen')")
        n_before = q.evaluate("() => strokeGroups.length")
        draw_line(q, 0.2, 0.8, 0.6, 0.8)
        nxt = q.evaluate("(n) => strokeGroups.length > n ? strokes[strokes.length - strokeGroups[strokeGroups.length - 1]].t : null", n_before)
        check("so the next line comes after the words", nxt is not None and nxt >= last, f"next line starts at {nxt}, words end at {r['last']}")
        c.close()

    # ------------------------------------------------------------------ 9
    if part("TEXT 9 — speed"):
        c, q = open_editor(b, "pad", prefs={"style": "print", "size": "M", "speed": 4})
        choose_text(q)
        tap(q, *at(q, 0.5, 0.35))
        type_words(q, "Happy birthday")
        one = q.evaluate(PLAN)["ms"]
        out1 = q.evaluate(SHEET)["out"]
        set_speed(q, 6)
        two = q.evaluate(PLAN)["ms"]
        set_speed(q, 0)
        quarter = q.evaluate(PLAN)["ms"]
        check("the sheet says how long the words take at 1×", out1 == "1× · %d s" % max(1, round(one / 1000)), f"{out1!r} for {one}ms")
        check("2× takes half as long and ¼× four times", abs(two * 2 - one) <= 4 and abs(quarter - one * 4) <= 8,
              f"1× {one}, 2× {two}, ¼× {quarter}")
        set_speed(q, 4)
        btns = q.evaluate("() => [...document.querySelectorAll('.tx-speed .slider-nudge-btn')].length")
        q.click(".tx-speed .slider-nudge-btn:last-of-type")
        up = q.evaluate("() => [document.getElementById('txSpeed').value, document.getElementById('txSpeedOut').textContent]")
        for _ in range(6):
            q.click(".tx-speed .slider-nudge-btn:last-of-type")
        top = q.evaluate("() => document.getElementById('txSpeed').value")
        for _ in range(12):
            q.click(".tx-speed .slider-nudge-btn:first-of-type")
        bottom = q.evaluate("() => [document.getElementById('txSpeed').value, document.getElementById('txSpeedOut').textContent]")
        check("- and + step the stops, and stop at 4× and ¼×",
              btns == 2 and up[0] == "5" and up[1].startswith("1½×") and top == "8" and bottom[0] == "0" and bottom[1].startswith("¼×"),
              f"{btns} buttons, + gives {up}, top {top}, bottom {bottom}")
        c.close()

    # ------------------------------------------------------------------ 10
    if part("TEXT 10 — styles and hands"):
        c, q = open_editor(b, "pad")
        choose_text(q)
        tap(q, *at(q, 0.5, 0.35))
        type_words(q, "Ab")
        q.wait_for_function("() => [...document.querySelectorAll('#txStyles [data-style]')].filter(b => b.dataset.face === 'drawn').length === 3",
                            timeout=15000)
        row = q.evaluate("""() => [...document.querySelectorAll('#txStyles [data-style]')].map(b => ({ s: b.dataset.style, face: b.dataset.face,
          on: b.classList.contains('on'), pressed: b.getAttribute('aria-pressed'), svg: !!b.querySelector('svg path'), words: b.textContent.trim() }))""")
        check("with no hand: Yours is + Make yours (a way there, not a choice) and Skribl is chosen",
              row[0]["face"] == "make" and row[0]["pressed"] is None and "Make yours" in row[0]["words"]
              and row[1]["on"] and row[1]["pressed"] == "true" and not any(r2["on"] for r2 in row if r2["s"] != "skribl"), json.dumps(row)[:240])
        check("Skribl, Print and Script are each written in themselves", all(r2["svg"] for r2 in row[1:]), json.dumps(row)[:200])
        plans = {}
        for st in ("skribl", "print", "script"):
            q.click(f'#txStyles [data-style="{st}"]')
            q.wait_for_timeout(120)
            plans[st] = q.evaluate(PLAN)
        check("each style writes in its own lettering",
              len({json.dumps(pl["flat"]) for pl in plans.values()}) == 3, {k2: (v["n"], v["pts"]) for k2, v in plans.items()})
        # A hand letter keeps its own pace: Skribl's j, timed by its file, with
        # the pause before its dot (over half a second as drawn) held.
        q.click('#txStyles [data-style="skribl"]')
        type_words(q, "j")
        pl = q.evaluate(PLAN)
        own = 0
        last = None
        for line in OWNER["g"]["j"]:
            for x, y, t in undelta(line, 3):
                if last is not None:
                    own += min(250, max(0, t - last))
                last = t
        raw = max(t for line in OWNER["g"]["j"] for x, y, t in undelta(line, 3))
        check("a hand's letter keeps its own pace, a pause held to a quarter second",
              abs(pl["ms"] - own) <= 2 and own < raw - 250, f"the plan's j takes {pl['ms']}ms; drawn in {raw}ms, {own}ms with its pause held")
        c.close()
        c, q = open_editor(b, "pad", hand=hand_seed(QUICK))
        choose_text(q)
        tap(q, *at(q, 0.5, 0.35))
        type_words(q, "A")
        q.wait_for_function("() => !!document.querySelector('#txStyles [data-style=\"print\"][data-face=\"drawn\"]')", timeout=15000)
        row = q.evaluate("""() => ({ on: [...document.querySelectorAll('#txStyles [data-style]')].filter(b => b.classList.contains('on')).map(b => b.dataset.style),
          note: document.getElementById('txNote').textContent, edit: !document.getElementById('txEdit').hidden,
          hint: document.getElementById('txSpeedHint').textContent })""")
        yours_a = q.evaluate(PLAN)
        q.click('#txStyles [data-style="print"]')
        q.wait_for_timeout(120)
        print_a = q.evaluate(PLAN)
        check("with a hand: Yours is chosen, and the sheet counts its letters",
              row["on"] == ["yours"] and row["note"] == "Your hand, 30 of 92 letters" and row["edit"] and row["hint"] == "1× is your own speed", str(row))
        same = (yours_a["n"] == print_a["n"] and all(len(a2) == len(b2) for a2, b2 in zip(yours_a["flat"], print_a["flat"])))
        check("a letter the hand has not drawn comes in Print", same, f"Yours A {yours_a['n']} strokes, Print A {print_a['n']}")
        check("no errors", not q._tx_errors, str(q._tx_errors[:2]))
        c.close()

    # ------------------------------------------------------------------ 11
    if part("TEXT 11 — the door"):
        c, q = open_editor(b, "pad")
        choose_text(q)
        tap(q, *at(q, 0.5, 0.35))
        q.wait_for_timeout(200)
        q.click('#txStyles [data-style="yours"]')
        q.wait_for_url("**letters=1**", timeout=15000)
        url1 = q.url
        q.wait_for_function("() => !!window.SkriblLetters && SkriblLetters.view() === 'start'", timeout=15000)
        q.click(".lt-ptop .lt-pdone")
        waited(q, "() => !!window.SkriblText && typeof shapeKind !== 'undefined' && shapeKind === 'text'")
        back1 = q.evaluate("() => [location.pathname + location.search, typeof tool !== 'undefined' ? tool : null, typeof shapeKind !== 'undefined' ? shapeKind : null]")
        check("Pad: + Make yours goes to Your hand, saying which editor", "letters=1" in url1 and "back=pad" in url1, url1)
        check("Pad: and Close comes back with Text chosen, the address clean", back1 == ["/skribl-pad", "shape", "text"], str(back1))
        c.close()
        c, q = open_editor(b, "flip", hand=hand_seed(QUICK))
        choose_text(q)
        tap(q, *at(q, 0.5, 0.35))
        q.wait_for_timeout(200)
        q.click("#txEdit")
        q.wait_for_url("**letters=1**", timeout=15000)
        url2 = q.url
        q.wait_for_function("() => !!window.SkriblLetters && SkriblLetters.view() === 'tiles'", timeout=15000)
        q.click(".lt-ptop .lt-pdone")
        chosen = waited(q, "() => !!window.SkriblText && typeof flipTool !== 'undefined' && flipTool === 'shape' && shapeKind === 'text'")
        back2 = q.evaluate("() => location.pathname + location.search")
        check("Flip: Edit your hand goes to Your hand, saying Flip, and Done comes back to Flip with Text chosen",
              "back=flip" in url2 and back2 == "/flip" and chosen, f"{url2} -> {back2}, Text chosen {chosen}")
        c.close()
        # Write with it, from Ready, after the 30th letter.
        seed = hand_seed(QUICK[:29])
        seed.update({"mode": "seq", "at": letterfont.BOX_IDS.index("?"), "r": False})
        c = b.new_context(**PHONE)
        c.add_init_script("if (!sessionStorage.getItem('tx-seeded')) { sessionStorage.setItem('tx-seeded', '1');"
                          + "localStorage.setItem(%s, %s);}" % (json.dumps(HAND), json.dumps(json.dumps(seed))))
        q = c.new_page()
        browsing.goto(q, BASE, "/skribl-pad?letters=1&back=flip")
        q.wait_for_function("() => !!window.SkriblLetters && SkriblLetters.view() === 'draw' && !!SkriblLetters.box()", timeout=15000)
        bx = q.evaluate("""() => { const b = SkriblLetters.box(), r = canvas.getBoundingClientRect(), lg = getCanvasLogicalSize();
          return [r.left + (b.x + b.w * 0.5) * r.width / lg.width, r.top + (b.y + b.h * 0.3) * r.height / lg.height, b.h * r.height / lg.height]; }""")
        q.mouse.move(bx[0], bx[1])
        q.mouse.down()
        for i in range(1, 12):
            q.mouse.move(bx[0] + i, bx[1] + bx[2] * 0.04 * i)
            q.wait_for_timeout(8)
        q.mouse.up()
        q.wait_for_timeout(200)
        q.click("#ltNext")
        q.wait_for_function("() => SkriblLetters.view() === 'ready'", timeout=10000)
        q.click("text=Write with it")
        chosen = waited(q, "() => !!window.SkriblText && typeof flipTool !== 'undefined' && shapeKind === 'text'")
        check("Ready's Write with it goes back to the editor that sent them, Text chosen",
              q.evaluate("() => location.pathname") == "/flip" and chosen, f"{q.url}, Text chosen {chosen}")
        c.close()

    # ------------------------------------------------------------------ 12
    if part("TEXT 12 — Flip's page"):
        c, q = open_editor(b, "flip", prefs={"style": "print", "size": "M", "speed": 4})
        draw_line(q, 0.2, 0.15, 0.8, 0.15)
        q.evaluate("() => { frame().draw = true; }")
        q.click("#addblank")
        q.wait_for_timeout(300)
        q.evaluate("() => go(0)")
        q.wait_for_timeout(200)
        choose_text(q)
        tap(q, *at(q, 0.5, 0.35))
        type_words(q, "Hi")
        plan = q.evaluate(PLAN)
        n0 = q.evaluate(COUNT["flip"])
        write_and_wait(q)
        r = q.evaluate("""(n0) => { const f = frames[0], H = window.SkriblHold;
          const log = actionLog[actionLog.length - 1];
          return { n: [f.strokes.length, f.strokeGroups.length], other: frames[1].strokes.length, idx: idx,
                   entry: log && log.type, label: log && log.label, groups: log && log.groups,
                   ms: H.pageMs(f, 12), half: H.dueCount(f, 0.5), all: f.strokes.length,
                   t: f.strokes.slice(n0[0]).map(p => p.t) }; }""", n0)
        check("the words go on the page they were placed on, as one Undo entry",
              r["n"][1] - n0[1] == plan["n"] and r["other"] == 0 and r["entry"] == "fill" and r["label"] == "Text"
              and r["groups"] == plan["n"], json.dumps({k2: v for k2, v in r.items() if k2 != "t"}))
        flat = [pt for s2 in plan["flat"] for pt in s2]
        off = max((abs((t - r["t"][0]) - f[2]) for t, f in zip(r["t"], flat)), default=99) if r["t"] else 99
        check("each point keeps the time it was written at",
              len(r["t"]) == plan["pts"] and off <= 1, f"{len(r['t'])} points, worst {off}ms off the plan")
        check("on a page that draws itself, they write themselves: half way, part of the page is on",
              r["ms"] > plan["ms"] * 0.5 and 0 < r["half"] < r["all"], f"page {r['ms']}ms, {r['half']} of {r['all']} points at half")
        c.close()

    # ------------------------------------------------------------------ 13
    if part("TEXT 13 — words you can read"):
        LUM = """(c) => { const m = c.match(/[\\d.]+/g).map(Number); const f = v => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); };
          return 0.2126 * f(m[0]) + 0.7152 * f(m[1]) + 0.0722 * f(m[2]); }"""
        # What is painted behind a word: each see-through ground laid over the
        # one under it, down to the first that is solid (a chosen card's tint
        # over the sheet's paper is neither the tint nor the paper).
        RATIOS = """([LUM, sels]) => { const lum = eval(LUM);
          const rgba = (c) => { const m = (c.match(/[\\d.]+/g) || []).map(Number); return [m[0] || 0, m[1] || 0, m[2] || 0, m.length > 3 ? m[3] : 1]; };
          const ground = (el) => { const stack = [];
            for (let e = el; e; e = e.parentElement) { const c = rgba(getComputedStyle(e).backgroundColor);
              if (c[3] > 0) { stack.push(c); if (c[3] >= 0.999) break; } }
            let out = [255, 255, 255];
            for (let i = stack.length - 1; i >= 0; i--) { const c = stack[i]; out = out.map((v, j) => c[j] * c[3] + v * (1 - c[3])); }
            return 'rgb(' + out.map(Math.round).join(',') + ')'; };
          const out = {};
          for (const [k, sel] of sels) { for (const el of document.querySelectorAll(sel)) { if (!el.checkVisibility()) continue;
            const a = lum(getComputedStyle(el).color), g = lum(ground(el));
            const r = (Math.max(a, g) + 0.05) / (Math.min(a, g) + 0.05);
            if (!(k in out) || r < out[k]) out[k] = r; } }
          return out; }"""
        SELS = [["title", "#txTitle"], ["close", "#txClose"], ["field", "#txField"], ["label", ".tx-k"], ["hint", ".tx-hint"],
                ["style", ".tx-style:not(.on)"], ["chosen", ".tx-style.on"], ["make", ".tx-make"], ["note", "#txNote"],
                ["link", "#txEdit"], ["size", "#txSize button:not(.on)"], ["size on", "#txSize button.on"], ["speed", "#txSpeedOut"],
                ["write", "#txGo"], ["drag", ".tx-drag"]]
        TAPS = """() => [...document.querySelectorAll('#txSheet button:not(.slider-nudge-btn), #txSheet a')].filter(b => b.checkVisibility())
          .map(b => { const r = b.getBoundingClientRect(); return [b.id || b.dataset.style || b.dataset.size || b.textContent.trim(), Math.min(r.width, r.height)]; })"""
        for dev_name, dev in (("phone", PHONE), ("desk", DESK)):
            for theme in ("light", "dark"):
                words, taps = {}, []
                for hand in (None, hand_seed(QUICK)):
                    c, q = open_editor(b, "pad", theme=theme, dev=dev, hand=hand)
                    choose_text(q)
                    tap(q, *at(q, 0.5, 0.8))
                    type_words(q, "Hello")
                    q.wait_for_timeout(350)
                    for k2, v in q.evaluate(RATIOS, [LUM, SELS]).items():
                        words[k2] = min(words.get(k2, 99), v)
                    taps += q.evaluate(TAPS)
                    s = q.evaluate(SHEET)
                    fs = q.evaluate("() => parseFloat(getComputedStyle(document.getElementById('txField')).fontSize)")
                    c.close()
                low = {k2: round(v, 2) for k2, v in words.items() if v < 4.5}
                check(f"{dev_name} {theme}: every word on the sheet and the box reads 4.5:1 or more",
                      not low and len(words) >= 14, low or f"{len(words)} kinds of word, the lowest {min(words, key=words.get)} at {round(min(words.values()), 2)}:1")
                small = [t for t in taps if t[1] < 44]
                check(f"{dev_name} {theme}: every button is 44px and up, the field 16px",
                      not small and len(taps) >= 10 and fs >= 16, f"{small or len(taps)} buttons, field {fs}px")
                check(f"{dev_name} {theme}: the sheet never covers the words",
                      s["place"] is not None and s["place"][3] <= s["top"] + 0.5, f"box {s['place']}, sheet top {s['top']}")

    # ------------------------------------------------------------------ 14
    if part("TEXT 14 — kind transitions"):
        RISE = """() => new Promise(res => { const s = document.getElementById('txSheet'), out = [];
          const t0 = performance.now();
          (function f() { if (!s.hidden) out.push(Math.round(s.getBoundingClientRect().top));
            if (performance.now() - t0 < 600) requestAnimationFrame(f); else res(out); })(); })"""
        c, q = open_editor(b, "pad")
        tops = q.evaluate("""() => { const p = new Promise(res => { const s = document.getElementById('txSheet'), out = [];
            const t0 = performance.now();
            (function f() { if (!s.hidden) out.push(Math.round(s.getBoundingClientRect().top));
              if (performance.now() - t0 < 600) requestAnimationFrame(f); else res(out); })(); });
          document.querySelector('#shapeSeg [data-shape="text"]').click();
          return p; }""")
        rest = tops[-1] if tops else None
        moving = [t for t in tops if t != rest]
        steps = [a2 - b2 for a2, b2 in zip(tops, tops[1:])]
        h = q.evaluate("() => document.getElementById('txSheet').getBoundingClientRect().height")
        check("the sheet rises over several frames, never a jump",
              len(set(moving)) >= 4 and all(sv >= 0 for sv in steps) and max(steps or [999]) <= h * 0.45,
              f"{len(set(moving))} places on the way up, biggest step {max(steps or [0])}px of {round(h)}")
        type_words(q, "Hi")
        gone = q.evaluate("""() => new Promise(res => { const pl = document.getElementById('txPlace');
          document.getElementById('txGo').click();
          requestAnimationFrame(() => res({ hidden: pl.hidden, writing: SkriblText.isWriting() })); })""")
        check("the dashed box is gone the frame the words start writing", gone["hidden"] and gone["writing"], str(gone))
        q.wait_for_function("() => !SkriblText.isWriting()", timeout=30000)
        c.close()
        c, q = open_editor(b, "pad", reduce=True)
        tops = q.evaluate("""() => { const p = new Promise(res => { const s = document.getElementById('txSheet'), out = [];
            const t0 = performance.now();
            (function f() { if (!s.hidden) out.push(Math.round(s.getBoundingClientRect().top));
              if (performance.now() - t0 < 400) requestAnimationFrame(f); else res(out); })(); });
          document.querySelector('#shapeSeg [data-shape="text"]').click();
          return p; }""")
        check("with Reduce Motion the sheet is simply there", len(set(tops)) == 1, f"{len(set(tops))} places: {sorted(set(tops))[:5]}")
        c.close()

    # ------------------------------------------------------------------ 15
    if part("TEXT 15 — a finished take"):
        c, q = open_editor(b, "pad", prefs={"style": "print", "size": "M", "speed": 8})
        draw_line(q, 0.2, 0.15, 0.8, 0.15)
        q.click("#recordBtn")
        q.wait_for_timeout(500)
        n0 = q.evaluate("() => [strokes.length, strokeGroups.length, finishedRecording, recording]")
        choose_text(q)
        q.wait_for_timeout(300)
        opened = q.evaluate("() => SkriblText.isOpen()")
        tap(q, *at(q, 0.4, 0.3))
        a = q.evaluate("() => SkriblText.anchor()")
        want = q.evaluate("() => { const lg = getCanvasLogicalSize(); return [lg.width * 0.4, lg.height * 0.3]; }")
        said = q.evaluate("() => { const t = document.getElementById('toast'); return t && !t.hidden ? t.textContent : ''; }")
        check("on a finished take, choosing Text opens the sheet and a press moves the words, refused by nothing",
              n0[2] is True and opened and a is not None and abs(a["x"] - want[0]) <= 2 and abs(a["y"] - want[1]) <= 80
              and "Tap Keep drawing" not in said, f"{n0}, open {opened}, words at {a} for {want}, toast {said!r}")
        type_words(q, "Hi")
        plan = q.evaluate(PLAN)
        write_and_wait(q)
        n1 = q.evaluate("() => [strokes.length, strokeGroups.length, finishedRecording, recording]")
        check("...and Write it carries the take on, as Keep drawing does, the drawing kept",
              n1[3] is True and n1[2] is False and n1[1] - n0[1] == plan["n"] and n1[0] - n0[0] == plan["pts"], f"{n0} -> {n1}")
        q.click("#undoBtn")
        q.wait_for_timeout(300)
        n2 = q.evaluate(COUNT["pad"])
        check("...and one Undo takes back only the words", n2 == n0[:2], f"{n0[:2]} -> {n1[:2]} -> undo {n2}")
        c.close()

    # ------------------------------------------------------------------ 16
    if part("TEXT 16 — the keyboard"):
        # A keyboard as iOS has one: what can be seen is 336px shorter, the
        # page is not. Chromium has no keyboard to open, so this is the
        # visual viewport iOS reports, put in place before the sheet opens.
        KEYBOARD = """() => { const real = window.visualViewport; window.__kb = 336; window.__realVV = real;
          const fake = { get height() { return innerHeight - window.__kb; }, offsetTop: 0, get width() { return innerWidth; },
                         addEventListener: (...a) => real.addEventListener(...a), removeEventListener: (...a) => real.removeEventListener(...a) };
          Object.defineProperty(window, 'visualViewport', { configurable: true, get: () => fake }); }"""
        KEYBOARD_GOES = "() => { window.__kb = 0; window.__realVV.dispatchEvent(new Event('resize')); }"
        TYPING = """() => { const s = document.getElementById('txSheet'), r = s.getBoundingClientRect(), pl = document.getElementById('txPlace');
          const shown = (sel) => { const e = document.querySelector(sel); return !!e && !!e.getClientRects().length; };
          const b = pl.hidden ? null : pl.getBoundingClientRect();
          return { open: SkriblText.isOpen(), typing: s.classList.contains('typing'), bottom: Math.round(r.bottom), top: r.top, edge: innerHeight - 336,
                   field: shown('#txField'), go: shown('#txGo'), style: shown('#txStyles'), size: shown('#txSize'), speed: shown('#txSpeed'),
                   focus: document.activeElement && document.activeElement.id, words: b && [Math.round(b.top), Math.round(b.bottom)] }; }"""
        # No keyboard up (a desk-sized phone with a hardware keyboard, or none
        # shown yet): the whole sheet, the words being typed or not.
        c, q = open_editor(b, "pad", prefs={"style": "print", "size": "M", "speed": 4})
        choose_text(q)
        type_words(q, "Hello")
        q.wait_for_timeout(300)
        t0 = q.evaluate(TYPING)
        check("phone: with no keyboard up, the whole sheet shows while the words are typed",
              t0["focus"] == "txField" and not t0["typing"] and t0["style"] and t0["size"] and t0["speed"], json.dumps(t0))
        c.close()
        c, q = open_editor(b, "pad", prefs={"style": "print", "size": "M", "speed": 4})
        q.evaluate(KEYBOARD)
        n0 = q.evaluate(COUNT["pad"])
        choose_text(q)
        tap(q, *at(q, 0.4, 0.3))
        put = q.evaluate("() => { const lg = getCanvasLogicalSize(); return [lg.width * 0.4, lg.height * 0.3]; }")
        type_words(q, "Hello")
        q.wait_for_timeout(300)
        t = q.evaluate(TYPING)
        check("phone: with the keyboard up, the sheet sits on it",
              abs(t["bottom"] - t["edge"]) <= 1, f"sheet ends at {t['bottom']}, the keyboard starts at {t['edge']}")
        check("...and is only the words and Write it, the words above it",
              t["typing"] and t["field"] and t["go"] and not (t["style"] or t["size"] or t["speed"])
              and t["words"] is not None and t["words"][0] >= 0 and t["words"][1] <= t["top"] + 0.5, json.dumps(t))
        q.keyboard.press("Enter")
        q.wait_for_timeout(400)
        t2 = q.evaluate(TYPING)
        n1 = q.evaluate(COUNT["pad"])
        check("the keyboard's done key puts it away and writes nothing; Style, Size and Speed come back",
              t2["open"] and t2["focus"] != "txField" and not t2["typing"] and t2["style"] and t2["size"] and t2["speed"]
              and n1 == n0 and not q.evaluate("() => SkriblText.isWriting()"), f"{json.dumps(t2)}, strokes {n0} -> {n1}")
        # The keyboard goes: the sheet comes back down, and the words, pushed
        # up while it was lifted, come back to where they were put.
        high = q.evaluate("() => SkriblText.anchor()")
        q.evaluate(KEYBOARD_GOES)
        q.wait_for_timeout(400)
        back = q.evaluate("() => ({ a: SkriblText.anchor(), bottom: Math.round(document.getElementById('txSheet').getBoundingClientRect().bottom), h: innerHeight })")
        check("when the keyboard goes, the sheet comes back down and the words back to where they were put",
              back["bottom"] == back["h"] and back["a"] is not None and abs(back["a"]["x"] - put[0]) <= 1 and abs(back["a"]["y"] - put[1]) <= 1
              and high is not None and high["y"] < put[1] - 20,
              f"pushed up to {high}, then at {back['a']} for {put}; sheet ends at {back['bottom']} of {back['h']}")
        q.evaluate("() => { window.__kb = 336; window.__realVV.dispatchEvent(new Event('resize')); }")
        if q.evaluate("() => SkriblText.isWriting()"):
            q.wait_for_function("() => !SkriblText.isWriting()", timeout=30000)
        # The x and Write it, pressed with the keyboard up: the field keeps
        # its focus until the click, so the sheet does not grow back under
        # the press (the x is at its top, which moves; Write it at its foot).
        if not q.evaluate("() => SkriblText.isOpen()"):
            choose_text(q)
        q.click("#txField")
        q.wait_for_timeout(300)
        t3 = q.evaluate(TYPING)
        q.click("#txClose")
        q.wait_for_timeout(500)
        closed = q.evaluate("() => !SkriblText.isOpen()")
        check("...and the x, pressed with the keyboard up, closes the sheet", t3["typing"] and closed,
              f"typing {t3['typing']}, closed {closed}")
        choose_text(q)
        q.wait_for_timeout(300)
        q.click("#txField")
        q.wait_for_timeout(300)
        t4 = q.evaluate(TYPING)
        q.click("#txGo")
        q.wait_for_timeout(300)
        wrote = q.evaluate("() => SkriblText.isWriting() || !SkriblText.isOpen()")
        waited(q, "() => !SkriblText.isWriting()", 30000)
        n2 = q.evaluate(COUNT["pad"])
        check("...and Write it, pressed with the keyboard up, writes", t4["typing"] and wrote and n2[1] > n1[1],
              f"typing {t4['typing']}, wrote {wrote}, strokes {n1} -> {n2}")
        c.close()
        c, q = open_editor(b, "pad", dev=DESK, prefs={"style": "print", "size": "M", "speed": 8})
        choose_text(q)
        type_words(q, "Hi")
        q.keyboard.press("Enter")
        waited(q, "() => !SkriblText.isOpen()", 5000)
        waited(q, "() => !SkriblText.isWriting()", 30000)
        n1 = q.evaluate(COUNT["pad"])
        check("desk: Enter writes the words", n1[1] > 0, str(n1))
        c.close()

    b.close()

failed = [r for r in results if not r[0]]
print(f"\n{len(results) - len(failed)}/{len(results)} passed")
sys.exit(1 if failed else 0)
