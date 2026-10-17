#!/usr/bin/env python3
"""Every word on every sheet, read against what is painted behind it.

The owner, after the menu's paper and the How it works mock (after v323): "I
think we are drifting. We need to check contrasts and consistency on all our
changes, and future changes."

A11Y 6 measures tokens and a list of rules; A11Y 6d the pages with their own
sheets. Neither opened the editors' sheets one by one and read every word on
the colour actually under it, so a new paper could pass both while a line on
it did not. This suite does, on Pad and Flip, light and dark, a phone and a
desk, for each surface a person can open:

  the menu (main, New, Settings), Your drafts, Export, Report a problem,
  Post, How it works (Ask's home, its answers, an answer; lib/ask.js), Tune,
  a button's card, a Show me step and the name tags (lib/learncard.js).

THE GROUND IS READ FROM PIXELS, NOT STYLES: the surface is photographed once
with every word made transparent, and each word's ground is the colour
painted inside its own box there (the worst of nine points, inset a pixel).
Glass, scrims, tints and shadows are all in that photograph; no chain of
computed backgrounds is guessed at. The ink is the computed colour, its alpha
and its ancestors' opacity laid over that ground.

WCAG AA: 4.5:1, or 3:1 for large text (24px, or 18.66px at 700). A disabled
control is exempt (WCAG 1.4.3). Each surface also reports its own colours
(the sheet and its cards) under CONSISTENCY, for reading side by side.
"""
import io
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
    from PIL import Image
except ImportError:
    print("SKIP: playwright is not installed")
    sys.exit(0)

PHONE = dict(viewport={"width": 402, "height": 874}, device_scale_factor=2, is_mobile=True, has_touch=True)
DESK = dict(viewport={"width": 1333, "height": 906}, device_scale_factor=1)
ONLY = [s for s in os.environ.get("CONTRAST_ONLY", "").split("|") if s]   # labels, "|" between

# (editor, route, menu button, canvas, ids that differ by editor)
EDITORS = (
    ("Pad", "/skribl-pad", "menuBtn", "#canvas",
     dict(menu="menuSheet", help="helpItem", export="exportItem", report="reportItem")),
    ("Flip", "/flip", "moreBtn", "#pad",
     dict(menu="moreMenu", help="miInfo", export="miExport", report="miReport")),
)

HIDE_TEXT = """* { color: transparent !important; -webkit-text-fill-color: transparent !important;
  text-shadow: none !important; caret-color: transparent !important; }
::placeholder { color: transparent !important; }"""

# Every visible element holding words, inside the open surface: its box (the
# union of its text nodes' rects), its ink with alpha and inherited opacity,
# and the size WCAG reads.
WORDS = r"""(root) => {
  const R = document.querySelector(root); if (!R) return null;
  const rgb = (s) => { const m = s.match(/[\d.]+/g); if (!m) return [0,0,0,0];
    const n = m.map(Number); if (s.startsWith('color(')) return [n[0]*255, n[1]*255, n[2]*255, n.length > 3 ? n[3] : 1];
    return [n[0], n[1], n[2], n.length > 3 ? n[3] : 1]; };
  // A sheet's edge fade (How it works' sticky ::after) paints over words on
  // their way out of view; those are not being read, so its band is skipped.
  const fa = getComputedStyle(R, '::after');
  const fade = fa.content !== 'none' && fa.position === 'sticky' ? parseFloat(fa.height) || 0 : 0;
  const floor = Math.min(innerHeight, R.getBoundingClientRect().bottom) - fade;
  const out = [];
  for (const el of R.querySelectorAll('*')) {
    const texts = [...el.childNodes].filter(n => n.nodeType === 3 && n.textContent.trim());
    if (!texts.length) continue;
    if (el.closest('[hidden], [aria-hidden="true"], :disabled, [aria-disabled="true"], svg')) continue;
    const cs = getComputedStyle(el);
    if (cs.visibility !== 'visible') continue;
    let box = null;
    for (const t of texts) { const r = document.createRange(); r.selectNodeContents(t);
      for (const q of r.getClientRects()) { if (!q.width || !q.height) continue;
        box = box ? {l: Math.min(box.l, q.left), t: Math.min(box.t, q.top), r: Math.max(box.r, q.right), b: Math.max(box.b, q.bottom)}
                  : {l: q.left, t: q.top, r: q.right, b: q.bottom}; } }
    if (!box || box.r <= 0 || box.b <= 0 || box.l >= innerWidth || box.t >= innerHeight || box.b > floor) continue;
    // painted, not merely laid out: what is on top at the box's centre is this or inside it
    const at = document.elementFromPoint((box.l + box.r) / 2, (box.t + box.b) / 2);
    if (!at || !(el === at || el.contains(at) || at.contains(el))) continue;
    let op = 1; for (let a = el; a && a.nodeType === 1; a = a.parentElement) op *= parseFloat(getComputedStyle(a).opacity);
    const c = rgb(cs.color);
    const name = el.id ? '#' + el.id : el.tagName.toLowerCase() + (el.classList.length ? '.' + [...el.classList].slice(0, 2).join('.') : '');
    out.push({ name, text: texts.map(t => t.textContent.trim()).join(' ').slice(0, 28), box,
               ink: [c[0], c[1], c[2], c[3] * op], px: parseFloat(cs.fontSize), w: parseInt(cs.fontWeight, 10) });
  }
  return out;
}"""

# The surface's own colours and its cards', for the consistency table.
CENSUS = r"""(root) => {
  const R = document.querySelector(root); if (!R) return null;
  const s = (el) => { const cs = getComputedStyle(el); return { bg: cs.backgroundColor, edge: cs.borderTopWidth !== '0px' ? cs.borderTopColor : 'none',
    r: cs.borderTopLeftRadius, blur: cs.backdropFilter }; };
  const cards = {};
  for (const sel of ['.menu-tile', '.menu-list', '.seg', '.sdrafts-row', '.sdrafts-files', '.sdrafts-this', '.learn-card', '.ask-row', '.ask-tour', '.ask-best-card',
                     '.help-tip', '.help-search', '.export-opt', '.tune-row', '.post-card']) {
    const el = [...R.querySelectorAll(sel)].find(e => e.getClientRects().length);
    if (el) cards[sel] = s(el);
  }
  return { sheet: s(R), cards };
}"""


def lum(c):
    def lin(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    return 0.2126 * lin(c[0]) + 0.7152 * lin(c[1]) + 0.0722 * lin(c[2])


def ratio(a, b):
    x, y = lum(a), lum(b)
    return (max(x, y) + 0.05) / (min(x, y) + 0.05)


# A ground still changing colour does not move a word, so the stillness read
# below cannot see it: main's CI caught an entry Ask had just opened, in a
# section still opening, at 4.20 (Pad, dark, phone) where it settles above
# 4.5. Every finite animation and transition inside the surface has finished
# before the photograph, up to 2.5s; endless ones (a spinner) are not waited on.
SETTLED = r"""(root) => new Promise(res => { const R = document.querySelector(root), t0 = performance.now();
  (function poll() {
    const busy = !!R && document.getAnimations().some(a => a.playState === 'running' && a.effect && a.effect.target
      && R.contains(a.effect.target) && isFinite(a.effect.getComputedTiming().endTime));
    if (!busy || performance.now() - t0 > 2500) res(!busy); else setTimeout(poll, 50);
  })(); })"""


def measure(q, root, scale):
    q.evaluate(SETTLED, root)
    # A sheet still gliding (How it works scrolls smoothly) moves its words
    # between the read and the photograph; read again until they hold still.
    for _ in range(6):
        words = q.evaluate(WORDS, root)
        if words is None:
            return None, []
        style = q.add_style_tag(content=HIDE_TEXT)
        q.wait_for_timeout(60)
        im = Image.open(io.BytesIO(q.screenshot())).convert("RGB")
        style.evaluate("s => s.remove()")
        if [w["box"] for w in q.evaluate(WORDS, root) or []] == [w["box"] for w in words]:
            break
        q.wait_for_timeout(400)
    low = []
    for w in words:
        b = w["box"]
        l, t, r, bt = (max(0, b["l"]) + 1) * scale, (max(0, b["t"]) + 1) * scale, (min(b["r"], im.width / scale) - 1) * scale, (min(b["b"], im.height / scale) - 1) * scale
        if r <= l or bt <= t:
            continue
        worst = None
        for i in range(3):
            for j in range(3):
                ground = im.getpixel((int(l + (r - l) * (i + .5) / 3), int(t + (bt - t) * (j + .5) / 3)))
                a = w["ink"][3]
                ink = [w["ink"][k] * a + ground[k] * (1 - a) for k in range(3)]
                v = ratio(ink, ground)
                worst = v if worst is None else min(worst, v)
        need = 3 if (w["px"] >= 24 or (w["px"] >= 18.66 and w["w"] >= 700)) else 4.5
        w["ratio"] = round(worst, 2)
        if worst < need:
            low.append(f'{w["name"]} "{w["text"]}" {worst:.2f}<{need}')
    return words, low


def surfaces(name, ids, q, canvas, btn):
    """Each surface: (label, how to open it from a fresh page, its root)."""
    m = "#" + ids["menu"]

    def menu():
        q.evaluate(f"() => document.getElementById('{btn}').click()")
        q.wait_for_timeout(700)

    def page(go):
        def f():
            menu()
            q.click(f'{m} [data-menu-go="{go}"]')
            q.wait_for_timeout(500)
        return f

    def via(item, wait=900):
        def f():
            menu()
            q.click(f"#{item}")
            q.wait_for_timeout(wait)
        return f

    def post():
        bx = q.locator(canvas).bounding_box()
        cx, cy = bx["x"] + bx["width"] / 2, bx["y"] + bx["height"] / 2
        q.mouse.move(cx - 60, cy); q.mouse.down()
        for i in range(30):
            q.mouse.move(cx - 60 + i * 4, cy + math.sin(i / 4) * 40)
            q.wait_for_timeout(10)
        q.mouse.up(); q.wait_for_timeout(400)
        # Pad records from the first stroke; Done ends the take and brings Post back.
        q.evaluate("() => { if (document.body.classList.contains('recording')) document.getElementById('recordBtn').click(); }")
        q.wait_for_timeout(600)
        q.click("#postBtn"); q.wait_for_timeout(900)

    def answers():
        via(ids["help"], 1200)()
        q.fill("#helpSearch", "loop"); q.wait_for_timeout(700)

    def answer():
        via(ids["help"], 1200)()
        q.click("#askOften [data-answer]"); q.wait_for_timeout(900)

    def step():
        answer()
        q.click("#askAnswer .ask-show"); q.wait_for_timeout(1500)

    def tune():
        q.click("#tuneBtn"); q.wait_for_timeout(700)

    # The card on the button and the name tags (lib/learncard.js), which the
    # page only shows to automation that asks (see the context's init script).
    def card():
        q.evaluate("() => window.SkriblLearnCard.open('#penToolBtn')"); q.wait_for_timeout(900)

    def names():
        q.evaluate("() => window.SkriblLearnCard.tags(true)"); q.wait_for_timeout(400)

    return (("the menu", menu, m), ("New", page("new"), m), ("Settings", page("settings"), m),
            ("Your drafts", via("openCloudDraftItem"), "#savedDraftsSheet"),
            ("Export", via(ids["export"]), "#exportSheet"), ("Report a problem", via(ids["report"]), "#reportSheet"),
            ("Post", post, "#postSheet"),
            ("Ask", via(ids["help"], 1500), "#helpDrawer .help-drawer-inner"),
            ("Ask, its answers", answers, "#helpDrawer .help-drawer-inner"),
            ("Ask, an answer", answer, "#helpDrawer .help-drawer-inner"),
            ("Tune", tune, "#tuneShell"),
            ("A button's card", card, ".lc-card"), ("A Show me step", step, ".lc-card"),
            ("Name every button", names, ".lc-tags"))


census = {}
with sync_playwright() as p:
    b = p.chromium.launch()
    for name, route, btn, canvas, ids in EDITORS:
        print(f"\n{name.upper()}")
        for scheme in ("light", "dark"):
            for dev, opts in (("phone", PHONE), ("desk", DESK)):
                c = b.new_context(color_scheme=scheme, **opts)
                c.add_init_script("window.__skriblLearnForce = true;"
                                  "try { localStorage.setItem('skribl.learncard.note.v1', '1'); } catch (e) {}")
                q = c.new_page()
                for label, opener, root in surfaces(name, ids, q, canvas, btn):
                    if ONLY and label not in ONLY:
                        continue
                    where = f"{name}, {scheme}, {dev}: {label}"
                    try:
                        browsing.goto(q, BASE, route)
                        q.wait_for_timeout(700)
                        q.evaluate("() => window.SkriblHints && window.SkriblHints.hide()")
                        opener()
                        q.evaluate("() => document.activeElement && document.activeElement.blur()")
                        words, low = measure(q, root, opts.get("device_scale_factor", 1))
                    except Exception as e:
                        check(f"{where} opened and was read", False, repr(e)[:160])
                        continue
                    if words is None:
                        check(f"{where} opened and was read", False, f"no {root}")
                        continue
                    check(f"{where}: every word clears AA on what is painted behind it ({len(words)} read)",
                          bool(words) and not low, "; ".join(low[:6]) + (f" (+{len(low) - 6} more)" if len(low) > 6 else ""))
                    if dev == "phone":
                        census[(name, scheme, label)] = q.evaluate(CENSUS, root)
                c.close()
    b.close()

# CONSISTENCY, asserted where the answer is already decided: Pad and Flip
# wear the same sheet and the same cards (one product, two editors: any
# difference is drift), and every sheet the menu opens is the menu's paper.
print("\nCONSISTENCY")
PAPER = ("the menu", "New", "Settings", "Your drafts", "Export", "Report a problem", "Post",
         "Ask", "Ask, its answers", "Ask, an answer")
for scheme in ("light", "dark"):
    labels = sorted({k[2] for k in census if k[1] == scheme})
    for label in labels:
        pad, flip = census.get(("Pad", scheme, label)), census.get(("Flip", scheme, label))
        if not (pad and flip):
            continue
        diff = [f"sheet: {pad['sheet']} vs {flip['sheet']}"] if pad["sheet"] != flip["sheet"] else []
        diff += [f"{k}: {pad['cards'][k]} vs {flip['cards'][k]}" for k in pad["cards"]
                 if k in flip["cards"] and pad["cards"][k] != flip["cards"][k]]
        check(f"{scheme}: {label} looks the same on Pad and Flip", not diff, "; ".join(diff)[:300])
    grounds = {(n, label): census[(n, scheme, label)]["sheet"]["bg"] for (n, sc, label) in census
               if sc == scheme and label in PAPER and census[(n, sc, label)]}
    check(f"{scheme}: every sheet the menu opens is one paper ({len(grounds)} read)",
          len(grounds) >= (2 if ONLY else 20) and len(set(grounds.values())) == 1,
          "; ".join(f"{n} {l}: {g}" for (n, l), g in sorted(grounds.items())))

print("\nEach surface's own colours, for reading side by side")
for (name, scheme, label), cz in sorted(census.items(), key=lambda kv: (kv[0][1], kv[0][2], kv[0][0])):
    if not cz:
        continue
    sh = cz["sheet"]
    print(f"  {scheme:5} {label:26} {name:4}  sheet {sh['bg']} blur={sh['blur']} r={sh['r']}")
    for sel, v in cz["cards"].items():
        print(f"  {'':5} {'':26} {'':4}    {sel:15} {v['bg']} edge={v['edge']} r={v['r']}")

bad = [r for r in results if not r[0]]
print(f"\n{'=' * 62}\n{len(results) - len(bad)}/{len(results)} passed\n{'=' * 62}")
sys.exit(1 if bad else 0)
