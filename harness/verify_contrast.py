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
  Post, How it works (Ask's home, its answers, an answer; lib/ask.js), the
  little book and Draw along (lib/book.js, lib/drawalong.js), Tune, a
  button's card, a Show me step and the name tags (lib/learncard.js).

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
import struct
import sys
import wave

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
     dict(menu="menuSheet", help="helpItem", export="exportItem", report="reportItem", photo="#photoInput")),
    ("Flip", "/flip", "moreBtn", "#pad",
     dict(menu="moreMenu", help="miInfo", export="miExport", report="miReport", photo="#imageInput")),
)

# A picture and a song to load into the photo and music drawers.
_im = Image.new("RGB", (300, 300), (243, 240, 255))
_pb = io.BytesIO(); _im.save(_pb, "PNG"); PNG = _pb.getvalue()
_wb = io.BytesIO()
with wave.open(_wb, "wb") as _w:
    _w.setnchannels(1); _w.setsampwidth(2); _w.setframerate(22050)
    _w.writeframes(b"".join(struct.pack("<h", int(8000 * math.sin(i / 8))) for i in range(22050 * 4)))
WAV = _wb.getvalue()

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
    // EACH LINE OF EACH TEXT ITS OWN BOX. One box round all of an element's
    // text took in what sat between its lines: main's CI (wider fonts than
    // this box) wrapped an entry Ask had found, and the box round its first
    // line and its last reached the lit "loop" between them, so grey words
    // were read against the lilac of a word they were not on (4.20).
    let op = 1; for (let a = el; a && a.nodeType === 1; a = a.parentElement) op *= parseFloat(getComputedStyle(a).opacity);
    const c = rgb(cs.color);
    if (c[3] * op < 0.01) continue;   // not painted: a bubble shown only while dragging
    const name = el.id ? '#' + el.id : el.tagName.toLowerCase() + (el.classList.length ? '.' + [...el.classList].slice(0, 2).join('.') : '');
    for (const t of texts) { const r = document.createRange(); r.selectNodeContents(t);
      for (const q of r.getClientRects()) { if (!q.width || !q.height) continue;
        const box = {l: q.left, t: q.top, r: q.right, b: q.bottom};
        if (box.r <= 0 || box.b <= 0 || box.l >= innerWidth || box.t >= innerHeight || box.b > floor) continue;
        // painted, not merely laid out: what is on top at the box's centre is this or inside it
        const at = document.elementFromPoint((box.l + box.r) / 2, (box.t + box.b) / 2);
        if (!at || !(el === at || el.contains(at) || at.contains(el))) continue;
        out.push({ name, text: t.textContent.trim().slice(0, 28), box,
                   ink: [c[0], c[1], c[2], c[3] * op], px: parseFloat(cs.fontSize), w: parseInt(cs.fontWeight, 10) });
      } }
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
                     '.help-tip', '.help-search', '.export-opt', '.tune-row', '.post-card', '.ask-list', '.accordion-header', '.post-preview',
                     '.bk-pic', '.ask-go', '.menu-start', '.export-nameinput', '.post-input', '.bk-back',
                     '.smooth-seg', '.media-tabs', '.photo-fit-group', '.reposition-btn', '.clear-drawer-btn', '.edge-controls']) {
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
        # On a slow runner a fixed wait was not enough: Post was still disabled
        # and the click timed out (main's CI, after v324). So end the take
        # whenever it shows, and wait for Post itself.
        q.wait_for_function("""() => {
          if (document.body.classList.contains('recording')) document.getElementById('recordBtn').click();
          return !document.getElementById('postBtn').disabled; }""", timeout=15000)
        q.click("#postBtn"); q.wait_for_timeout(900)

    def answers():
        via(ids["help"], 1200)()
        q.fill("#helpSearch", "loop"); q.wait_for_timeout(700)

    def answer():
        via(ids["help"], 1200)()
        q.click("#askOften [data-answer]"); q.wait_for_timeout(900)

    def book():
        via(ids["help"], 1200)()
        q.click("#askTour"); q.wait_for_timeout(600)
        q.click("#bkNext"); q.wait_for_timeout(1500)       # the drawing page: Draw along shows

    def along():
        book()
        q.click("#bkAlong"); q.wait_for_timeout(1200)

    def step():
        answer()
        q.click("#askAnswer .ask-show"); q.wait_for_timeout(1500)

    def tune():
        q.click("#tuneBtn"); q.wait_for_timeout(700)

    # THE DOCK'S DRAWERS AS THEY ARE USED (after v324, the drawers mock): the
    # draw drawer unfolded, Photo with a picture in it, Music with a song, on
    # Trim and on Fine-tune. Opened empty, six lines too faint to read were
    # never in view to be measured.
    def drawer():
        browsing.pad_drawer(q, "draw"); q.wait_for_timeout(500)
        if q.evaluate("() => { const m = document.getElementById('drawerDetentMore'); return !!m && !!m.getClientRects().length && getComputedStyle(m).display !== 'none'; }"):
            q.click("#drawerDetentMore"); q.wait_for_timeout(900)

    def photo():
        browsing.pad_drawer(q, "photo"); q.wait_for_timeout(400)
        q.set_input_files(ids["photo"], {"name": "photo.png", "mimeType": "image/png", "buffer": PNG})
        q.wait_for_timeout(1500)

    def music(fine):
        def f():
            browsing.pad_drawer(q, "music"); q.wait_for_timeout(400)
            q.set_input_files("#musicInput", {"name": "song.wav", "mimeType": "audio/wav", "buffer": WAV})
            q.wait_for_function("() => typeof currentAudioBuffer !== 'undefined' && !!currentAudioBuffer", timeout=20000)
            q.wait_for_timeout(700)
            if fine:
                q.click("#fineTuneToggle"); q.wait_for_timeout(900)
        return f

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
            ("The little book", book, "#bookRoot .bk"), ("Draw along", along, ".da-pill"),
            ("Tune", tune, "#tuneShell"),
            ("The draw drawer", drawer, "#drawPanel"), ("Photo, with a picture", photo, "#mediaCard"),
            ("Music, Trim", music(False), "#mediaCard"), ("Music, Fine-tune", music(True), "#mediaCard"),
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

# THE DRAWER'S EDGE SHOWS (owner, after v324: "I can't really see the edges
# of the drawer"). The page's pixel just outside a drawer's left edge, against
# the strongest of the drawer's first three columns there: the dock's glass
# measured 1.01:1 in light, no edge at all; the menu's card line is 1.53 in
# light and 1.29 in dark. At the phone's 2x, the draw drawer and the photo card.
print("\nTHE DRAWERS' EDGE")
with sync_playwright() as p:
    b = p.chromium.launch()
    for name, route, btn, canvas, ids in EDITORS:
        for scheme in ("light", "dark"):
            c = b.new_context(color_scheme=scheme, **PHONE)
            q = c.new_page()
            for what, root in (("draw", "#drawPanel"), ("photo", "#mediaCard")):
                if ONLY and "edge" not in ONLY:
                    continue
                browsing.goto(q, BASE, route); q.wait_for_timeout(700)
                q.evaluate("() => window.SkriblHints && window.SkriblHints.hide()")
                browsing.pad_drawer(q, what); q.wait_for_timeout(700)
                r = q.evaluate("(s) => { const b = document.querySelector(s).getBoundingClientRect(); return [b.left, b.top, b.height]; }", root)
                im = Image.open(io.BytesIO(q.screenshot())).convert("RGB")
                X, Y = round(r[0] * 2), round((r[1] + min(r[2], 120) / 2) * 2)
                page = im.getpixel((X - 8, Y))
                rim = max((im.getpixel((X + k, Y)) for k in range(3)), key=lambda px: abs(lum(px) - lum(page)))
                check(f"{name}, {scheme}: the {what} drawer's edge shows against the page (1.25:1 or more)",
                      ratio(rim, page) >= 1.25, f"page {page} edge {rim} {ratio(rim, page):.2f}")
            c.close()
    b.close()

# CONSISTENCY, asserted where the answer is already decided: Pad and Flip
# wear the same sheet and the same cards (one product, two editors: any
# difference is drift), and every sheet the menu opens is the menu's paper.
print("\nCONSISTENCY")
DRAWERS = ("Tune", "The draw drawer", "Photo, with a picture", "Music, Trim", "Music, Fine-tune")
PAPER = ("the menu", "New", "Settings", "Your drafts", "Export", "Report a problem", "Post",
         "Ask", "Ask, its answers", "Ask, an answer", "The little book")
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
          len(grounds) >= (2 if ONLY else 22) and len(set(grounds.values())) == 1,
          "; ".join(f"{n} {l}: {g}" for (n, l), g in sorted(grounds.items())))

    # ONE LOOK ON THE PAPER (owner, after v324: the sheets mock, "All yes").
    # Every pick-one track on the menu's sheets (the Pad | Flip switch, New's
    # shapes, Theme, Tips, Canvas) and Export's options are the menu's white
    # card, the colour of the tiles; and each kind of thing has one corner:
    # a sheet 22, a card 16, a button or field 12.
    tile = ((census.get(("Pad", scheme, "the menu")) or {}).get("cards", {}).get(".menu-tile") or {}).get("bg")
    cardlike = {(n, l, sel): census[(n, sc, l)]["cards"][sel]["bg"] for (n, sc, l) in census
                for sel in (".seg", ".export-opt", ".smooth-seg", ".media-tabs", ".photo-fit-group", ".reposition-btn",
                            ".clear-drawer-btn", ".edge-controls")
                if sc == scheme and l in ("the menu", "New", "Settings", "Export") + DRAWERS and census[(n, sc, l)]
                and sel in census[(n, sc, l)]["cards"]}
    check(f"{scheme}: every choice on the menu's sheets and in the dock's drawers, and Export's options, is a white card "
          f"like the menu's tiles ({len(cardlike)} read)",
          bool(tile) and len(cardlike) >= (1 if ONLY else 20) and set(cardlike.values()) == {tile},
          f"tile {tile}; " + "; ".join(f"{n} {l} {sel}: {v}" for (n, l, sel), v in sorted(cardlike.items()) if v != tile))
    KIND = {".menu-tile": "16px", ".menu-list": "16px", ".sdrafts-this": "16px", ".sdrafts-files": "16px", ".learn-card": "16px",
            ".ask-tour": "16px", ".ask-best-card": "16px", ".ask-list": "16px", ".help-tip": "16px", ".accordion-header": "16px",
            ".export-opt": "16px", ".post-preview": "16px", ".bk-pic": "16px", ".sdrafts-row": "16px",
            ".seg": "12px", ".help-search": "12px", ".ask-go": "12px", ".menu-start": "12px", ".export-nameinput": "12px",
            ".post-input": "12px", ".bk-back": "12px", ".smooth-seg": "12px", ".media-tabs": "12px", ".photo-fit-group": "12px",
            ".reposition-btn": "12px", ".clear-drawer-btn": "12px", ".edge-controls": "12px"}
    # The dock's drawers and Tune are the menu's paper too (the drawers mock, C).
    paper = (census.get(("Pad", scheme, "the menu")) or {}).get("sheet", {}).get("bg")
    drawers = {(n, l): census[(n, sc, l)]["sheet"]["bg"] for (n, sc, l) in census
               if sc == scheme and l in DRAWERS and census[(n, sc, l)]}
    check(f"{scheme}: every drawer the dock opens, and Tune, is the menu's paper ({len(drawers)} read)",
          bool(paper) and len(drawers) >= (1 if ONLY else 10) and set(drawers.values()) == {paper},
          f"paper {paper}; " + "; ".join(f"{n} {l}: {g}" for (n, l), g in sorted(drawers.items()) if g != paper))
    off, seen = [], 0
    for (n, sc, l), cz in census.items():
        if sc != scheme or l not in PAPER + DRAWERS or not cz:
            continue
        seen += 1
        # A sheet is 22; a drawer is a card in the dock, 16 (Tune spans the top, square).
        want = "22px" if l in PAPER else ("0px" if l == "Tune" else "16px")
        if cz["sheet"]["r"] != want:
            off.append(f"{n} {l} sheet {cz['sheet']['r']}")
        off += [f"{n} {l} {sel} {v['r']}" for sel, v in cz["cards"].items() if sel in KIND and v["r"] != KIND[sel]]
    check(f"{scheme}: one corner per kind on the menu's sheets and the dock's drawers: a sheet 22, a drawer or card 16, "
          f"a button or field 12 ({seen} read)",
          seen >= (1 if ONLY else 32) and not off, "; ".join(sorted(set(off)))[:400])

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
