#!/usr/bin/env python3
"""New Skribl, and the way back, on both editors (the owner's yes, Q4).

After New Skribl the Pad said "New Skribl" with an Undo beside it, and Undo
said "Restored" with a Redo. Flip said nothing: its way back was Undo clear,
inside the pages drawer, where nobody who had just left the menu would look.
The owner: "Flip shows the same chip, from the same code." It does now, through
lib/newundo.js, and each editor is driven the same way here:

  * Start says New Skribl, with an Undo.
  * Undo brings the drawing back: its strokes, its name and its shape. It
    says Restored, with a Redo.
  * Redo is the Start again, on the shape New Skribl picked. The Pad's kept
    the old drawing's shape, so its Redo was not the new drawing.
  * The words are the same on both, in the same order.
  * Flip's chip, once faded, cannot take a tap meant for the page under it.

Each row was red on one editor or the other before.
"""
import os
import sys

from assertions import make_check
import browsing

try:
    from playwright.sync_api import sync_playwright
except ImportError as exc:
    print(f"SUITE-SKIPPED: {exc}")
    print("No assertions were executed. This is NOT evidence New Skribl has a way back.")
    raise SystemExit(77)

BASE = os.environ.get("SKRIBL_BASE", "http://127.0.0.1:5001")
results = []
check = make_check(results, with_detail=True)

# Each editor: its menu, its Start, its canvas, where it speaks, and how many
# strokes it holds.
ED = {
    "Pad": {"path": "/", "menu": "#menuBtn", "start": "#clearMenuItem", "canvas": "#canvas", "say": "#toast",
            "strokes": "() => strokes.length"},
    "Flip": {"path": "/flip", "menu": "#moreBtn", "start": "#miClearAll", "canvas": "#pad", "say": "#flipChip",
             "strokes": "() => frames.reduce((n, f) => n + f.strokes.length, 0)"},
}
SAID = """(sel) => { const t = document.querySelector(sel); if (!t) return null;
  const a = t.querySelector('.toast-action');
  return { text: [...t.childNodes].filter(n => n.nodeType === 3).map(n => n.textContent).join('').trim(),
           action: a ? a.textContent.trim() : null }; }"""
# The shape twice: the one the canvas has, and the one the shape row in
# Settings lights, which the next New Skribl opens on. "square/tall" is a
# square canvas under a row saying Tall.
SHAPE = """(ed) => { const b = document.querySelector('#canvasSeg button.on');
  const real = ed === 'Pad' ? SkriblCanvasSizes.idFor(authoredW, authoredH) : currentSizeId();
  return (b ? b.dataset.size : null) + '/' + real; }"""


def stroke(pg, sel):
    r = pg.evaluate("(s) => { const b = document.querySelector(s).getBoundingClientRect(); return { x: b.x, y: b.y }; }", sel)
    pg.mouse.move(r["x"] + 60, r["y"] + 60); pg.mouse.down()
    for k in range(14):
        pg.mouse.move(r["x"] + 60 + k * 9, r["y"] + 60 + k * 4); pg.wait_for_timeout(16)
    pg.mouse.up(); pg.wait_for_timeout(300)
    if sel == "#canvas":
        # The Pad records from the first stroke and keeps New Skribl's Start
        # back until the take is done.
        pg.click("#recordBtn"); pg.wait_for_timeout(600)


def set_apart(pg, host, btn):
    """A button's own fill against the glass round it, as PAINTED: the commonest
    colour inside the button, and the commonest in the host outside every
    button (words and corners are the few). (ratio, button, glass), or None."""
    import io
    from collections import Counter
    from PIL import Image
    r = pg.evaluate("""([h, b]) => { const H = document.querySelector(h), B = H && H.querySelector(b); if (!H || !B) return null;
      const o = H.getBoundingClientRect(), at = e => { const q = e.getBoundingClientRect(); return [q.left - o.left, q.top - o.top, q.width, q.height]; };
      return { host: [o.left, o.top, o.width, o.height], btn: at(B), btns: [...H.querySelectorAll('button')].map(at) }; }""", [host, btn])
    if not r or r["host"][2] < 4 or r["host"][3] < 4:
        return None
    im = Image.open(io.BytesIO(pg.screenshot(clip=dict(zip(("x", "y", "width", "height"), r["host"]))))).convert("RGB")
    inside = lambda x, y, q: q[0] <= x < q[0] + q[2] and q[1] <= y < q[1] + q[3]
    fill, glass = Counter(), Counter()
    for y in range(im.size[1]):
        for x in range(im.size[0]):
            if inside(x, y, r["btn"]):
                fill[im.getpixel((x, y))] += 1
            elif not any(inside(x, y, q) for q in r["btns"]):
                glass[im.getpixel((x, y))] += 1
    if not fill or not glass:
        return None
    f_, g_ = fill.most_common(1)[0][0], glass.most_common(1)[0][0]
    lin = lambda v: v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
    lum = lambda c: sum(k * lin(ch / 255) for k, ch in zip((0.2126, 0.7152, 0.0722), c))
    a, b = lum(f_), lum(g_)
    return (round((max(a, b) + 0.05) / (min(a, b) + 0.05), 3), f_, g_)


def act(pg, sel):
    """Press the button in the toast or the chip, as a finger would: where it is painted."""
    at = pg.evaluate("""(s) => { const a = document.querySelector(s + ' .toast-action'); if (!a) return null;
      const r = a.getBoundingClientRect(); return { x: r.x + r.width / 2, y: r.y + r.height / 2 }; }""", sel)
    if not at:
        return False
    pg.mouse.click(at["x"], at["y"]); pg.wait_for_timeout(500)
    return True


words = {}
with sync_playwright() as p:
    b = p.chromium.launch()
    for name, e in ED.items():
        print(f"\nNEW SKRIBL, AND THE WAY BACK — {name}")
        pg = b.new_page(viewport={"width": 1100, "height": 820})
        errs = []
        pg.on("pageerror", lambda x: errs.append(str(x)))
        browsing.goto(pg, BASE, e["path"])
        pg.evaluate("() => window.SkriblHints && window.SkriblHints.hide()")
        stroke(pg, e["canvas"])
        pg.evaluate("() => window.SkriblName && window.SkriblName.set('Undo me')")
        was_shape, was_strokes = pg.evaluate(SHAPE, name), pg.evaluate(e["strokes"])
        want = "tall" if not was_shape.startswith("tall/") else "square"

        pg.click(e["menu"]); pg.wait_for_timeout(300)
        pg.click("#menuNewTile"); pg.wait_for_timeout(300)
        pg.click(f'#newSizeSeg > button[data-size="{want}"]'); pg.wait_for_timeout(150)
        pg.click(e["start"]); pg.wait_for_timeout(500)
        said = [pg.evaluate(SAID, e["say"])]
        new_shape, new_strokes = pg.evaluate(SHAPE, name), pg.evaluate(e["strokes"])
        check(f"{name}: Start makes a new drawing on the shape it picked, and says New Skribl, with an Undo",
              was_strokes > 0 and new_strokes == 0 and new_shape == f"{want}/{want}"
              and said[0] == {"text": "New Skribl", "action": "Undo"},
              f"strokes {was_strokes} -> {new_strokes}, shape {was_shape} -> {new_shape} (picked {want}), said {said[0]}")
        # ITS UNDO STANDS APART FROM THE GLASS (No dinge): the toast and Flip's
        # chip are clear glass, and a second button on it its own fill, read
        # as painted in both themes. On the violet glass the solid violet sat
        # 1.07:1 in dark, so there it steps up.
        # Dark is read with the page's drawing on its light ground, where the
        # glass (6% see-through) is lightest: the harder case for a button
        # lighter than the glass. One shade up (#3d326b) read 1.03:1 there.
        th0 = pg.evaluate("() => document.documentElement.getAttribute('data-theme')")
        apart = {}
        for th in ("light", "dark"):
            pg.evaluate("(t) => document.documentElement.setAttribute('data-theme', t)", th)
            pg.wait_for_timeout(250)
            apart[th] = set_apart(pg, e["say"], ".toast-action")
        pg.evaluate("(t) => t ? document.documentElement.setAttribute('data-theme', t) : document.documentElement.removeAttribute('data-theme')", th0)
        pg.wait_for_timeout(150)
        check(f"{name}: ...its Undo stands apart from the glass it sits on by its own fill, 1.08:1 or more, painted, light and dark",
              len(apart) == 2 and all(v and v[0] >= 1.08 for v in apart.values()), str(apart))

        undone = act(pg, e["say"])
        said.append(pg.evaluate(SAID, e["say"]))
        back = {"strokes": pg.evaluate(e["strokes"]), "shape": pg.evaluate(SHAPE, name),
                "name": pg.evaluate("() => window.SkriblName.get()")}
        check(f"{name}: Undo brings the drawing back, its strokes, its name and its shape, and says Restored, with a Redo",
              undone and back == {"strokes": was_strokes, "shape": was_shape, "name": "Undo me"}
              and said[1] == {"text": "Restored", "action": "Redo"},
              f"pressed {undone}; back {back}, was {was_strokes} strokes on {was_shape}; said {said[1]}")

        redone = act(pg, e["say"])
        said.append(pg.evaluate(SAID, e["say"]))
        again = {"strokes": pg.evaluate(e["strokes"]), "shape": pg.evaluate(SHAPE, name)}
        check(f"{name}: Redo is the Start again, on the shape New Skribl picked, and offers its Undo again",
              redone and again == {"strokes": 0, "shape": f"{want}/{want}"} and said[2] == {"text": "New Skribl", "action": "Undo"},
              f"pressed {redone}; {again}, picked {want}; said {said[2]}")
        words[name] = said

        if name == "Flip":
            # The chip lets the page have every touch, and its button takes its
            # own back (.toast-action). Faded, the button must go with it.
            pg.evaluate("() => { const c = document.getElementById('flipChip'); clearTimeout(c._t); c.classList.remove('show'); }")
            pg.wait_for_timeout(450)
            gone = pg.evaluate("""() => { const a = document.querySelector('#flipChip .toast-action'); if (!a) return { gone: true };
              const r = a.getBoundingClientRect(), hit = document.elementFromPoint(r.x + r.width / 2, r.y + r.height / 2);
              a.focus(); return { hit: hit === a, focused: document.activeElement === a, vis: getComputedStyle(a).visibility }; }""")
            check("Flip: once the chip has faded, its Undo takes no tap and no focus", gone.get("gone") or
                  (not gone["hit"] and not gone["focused"]), str(gone))
        check(f"{name}: no page errors", not errs, "; ".join(errs[:2]))
        pg.close()
    b.close()

check("the Pad and Flip say the same words in the same order (one offer, lib/newundo.js)",
      words.get("Pad") == words.get("Flip") and words.get("Pad"), f"Pad {words.get('Pad')}; Flip {words.get('Flip')}")

bad = [r for r in results if not r[0]]
print(f"\n{'=' * 62}\n{len(results) - len(bad)}/{len(results)} passed"
      + ("" if not bad else "  FAILURES: " + ", ".join(r[1] for r in bad)))
sys.exit(1 if bad else 0)
