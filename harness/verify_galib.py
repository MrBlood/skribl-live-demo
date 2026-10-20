"""The gallery and the library wear the family's chrome, and behave like it.

WHY A SUITE OF ITS OWN. An audit of v317 held /gallery and /library against
the rules the Pad and Flip already keep and found twenty-two divergences
(DECISIONS.md, "Gallery and library join the family"). The owner chose the
Pad's material for the page menu, the header and the report sheet; the rest
were defects with a rule already written down. Every row here asks the
PAINTED or DRIVEN question, never "a style changed":

  PAINTED FOCUS   every Tab stop on both pages, rows present, paints a ring
                  -- pixels in the band around the control change when it
                  takes focus -- and is the element at its own centre. A11Y 8
                  asks whether a computed style changed, which is why a ring
                  clipped to zero pixels (the gallery's tile player) and the
                  browser's own ring (the library) both passed it.
  DELETE FLOWS    the draft bin asks without moving and without a timer race,
                  on the library and on the editors' sheet; a posted Delete
                  holds its arm past the four seconds it used to give.
  MENU            the editors' paper (after v324: solid, the same paper,
                  white cards with the lilac edge, read off the Pad's own
                  menu), a popover under the ••• on a desktop, a full-bleed
                  sheet on a phone.
  HEADER          one glass card, sticky, on both pages; ONE lockup whose
                  measured values agree across the two; nothing overflows 390.
  REPORT SHEET    a bottom sheet with a grab bar on a phone, a centred card on
                  a desktop, and the grab closes it.
  CONTRAST        every word inside the glass sheets clears AA against the
                  pixels actually behind it (text made transparent, the frame
                  photographed, each text box's pixels measured), both themes.
  ROW ACTIONS     at 390, no point between two row actions answers nothing.
  LIBRARY PLAY    no accent gradient and no glow.

Fixtures are posted through the API with a token unique to this run, and the
library's list is the record lib/posted.js keeps, written into this browser.

Requires a running server:
    ./harness/run_harness.sh verify_galib.py
"""
import json
import os
import re
import statistics
import sys
import urllib.request

from assertions import make_check
import browsing

BASE = os.environ.get("SKRIBL_BASE", "http://127.0.0.1:5001")

try:
    from playwright.sync_api import sync_playwright
    from PIL import Image
except Exception as exc:                                   # pragma: no cover
    print(f"SUITE-SKIPPED: playwright or Pillow unavailable ({exc})")
    print("No assertions were executed. This is NOT evidence the gallery or library works.")
    raise SystemExit(77)

results = []
check = make_check(results)
TAG = "galib" + os.urandom(4).hex()
TMP = f"/tmp/{TAG}"
os.makedirs(TMP, exist_ok=True)

DESK = dict(viewport={"width": 1400, "height": 900})
PHONE = dict(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True)


def post(title, vis="public"):
    pts = [{"x": 120 + i * 40, "y": 140 + (i % 3) * 30, "color": "#ff48b0",
            "size": 12, "t": i * 120} for i in range(12)]
    body = {"title": title, "version": 2, "schemaVersion": 2, "visibility": vis,
            "playbackMode": "replay", "frames": [{"strokes": pts, "strokeGroups": [len(pts)]}],
            "canvasSize": {"cssWidth": 816, "cssHeight": 612}}
    req = urllib.request.Request(BASE + "/api/skribls", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as r:
        j = json.loads(r.read().decode())
    return {"id": j["id"], "url": j["url"], "title": title, "kind": "pad", "pages": 1,
            "visibility": vis, "tok": j["deleteToken"], "local": False, "has_audio": False,
            "at": 0}


def remember(pg, entries):
    """What lib/posted.js writes when a sheet's post succeeds, written here."""
    pg.evaluate("(e) => localStorage.setItem('skribl_posted_v1', JSON.stringify(e))", entries)


def open_page(ctx, path, theme=None):
    pg = ctx.new_page()
    q = ("?theme=" + theme) if theme else ""
    browsing.goto(pg, BASE, path + q, require_boot=False)
    pg.wait_for_timeout(900)
    pg.evaluate("() => { if (window.SkriblHints) window.SkriblHints.hide(); }")
    return pg


# ---------------------------------------------------------------- contrast
TEXT_RECTS = """(sels) => {
  const out = [];
  for (const s of sels) for (const el of document.querySelectorAll(s)) {
    const cs = getComputedStyle(el);
    if (cs.visibility === 'hidden' || !el.getClientRects().length) continue;
    // A box a pixel wide paints no words (a count read out but not drawn),
    // though its text's own rects still report their full width.
    const own = el.getBoundingClientRect(); if (own.width <= 1 || own.height <= 1) continue;
    const rects = [];
    for (const n of el.childNodes) {
      if (n.nodeType !== 3 || !n.textContent.trim()) continue;
      const rg = document.createRange(); rg.selectNodeContents(n);
      for (const r of rg.getClientRects()) if (r.width > 1 && r.bottom > 0 && r.top < innerHeight) rects.push([r.left, r.top, r.right, r.bottom]);
    }
    if (rects.length) out.push({ sel: s, text: el.textContent.trim().slice(0, 24), color: cs.color,
                                 size: parseFloat(cs.fontSize), weight: parseInt(cs.fontWeight, 10), rects });
  }
  return out; }"""
HIDE_TEXT = ("*{color:transparent!important;-webkit-text-fill-color:transparent!important;"
             "text-shadow:none!important;caret-color:transparent!important}"
             "svg,input[type=radio]{visibility:hidden!important}")


def _lin(c):
    c /= 255.0
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def _lum(p):
    return 0.2126 * _lin(p[0]) + 0.7152 * _lin(p[1]) + 0.0722 * _lin(p[2])


def _rgba(s):
    v = [float(x) for x in s[s.index("(") + 1:s.index(")")].replace("/", ",").split(",") if x.strip()]
    return v[:3], (v[3] if len(v) > 3 else 1.0)


def glass_contrast(pg, sels, dsf):
    """The 10th-percentile contrast of each text box against the frame with
    every word made transparent: the pixels the words actually sit on."""
    items = pg.evaluate(TEXT_RECTS, sels)
    h = pg.add_style_tag(content=HIDE_TEXT)
    pg.wait_for_timeout(250)
    path = f"{TMP}/bg.png"
    pg.screenshot(path=path)
    pg.evaluate("(e) => e.remove()", h)
    img = Image.open(path).convert("RGB")
    out = []
    for it in items:
        rgb, a = _rgba(it["color"])
        px = []
        for (l, t, r, b) in it["rects"]:
            box = [int(round(v * dsf)) for v in (l, t, r, b)]
            box = [max(0, box[0]), max(0, box[1]), min(img.width, box[2]), min(img.height, box[3])]
            if box[2] > box[0] and box[3] > box[1]:
                px.extend(img.crop(box).getdata())
        if not px:
            continue
        crs = sorted(((max(_lum(f), _lum(p)) + .05) / (min(_lum(f), _lum(p)) + .05))
                     for p in px[::3] for f in [[rgb[i] * a + p[i] * (1 - a) for i in range(3)]])
        need = 3.0 if (it["size"] >= 24 or (it["size"] >= 18.66 and it["weight"] >= 700)) else 4.5
        out.append((it["text"], round(crs[len(crs) // 10], 2), need))
    return out


# ------------------------------------------------------------ painted focus
FOCUS_STOP = """() => { const el = document.activeElement;
  if (!el || el === document.body) return null;
  const r = el.getBoundingClientRect();
  const cx = Math.min(innerWidth - 1, Math.max(0, r.left + r.width / 2));
  const cy = Math.min(innerHeight - 1, Math.max(0, r.top + r.height / 2));
  const hit = document.elementFromPoint(cx, cy);
  const key = el.id ? '#' + el.id : el.tagName.toLowerCase() + '.' + [...el.classList].join('.')
            + '@' + Math.round(r.top + scrollY);
  return { key, r: [r.left, r.top, r.right, r.bottom],
           onTop: !!hit && (hit === el || el.contains(hit) || hit.contains(el)) }; }"""


def band_change(a, b, r, dsf):
    """Of the pixels in the 6px band straddling the control's edge, how many
    changed between the unfocused and the focused frame."""
    l, t, rr, bb = r
    pad_o, pad_i = 6, 3
    changed = total = 0
    for y in range(int((t - pad_o) * dsf), int((bb + pad_o) * dsf)):
        if y < 0 or y >= a.height:
            continue
        for x in range(int((l - pad_o) * dsf), int((rr + pad_o) * dsf)):
            if x < 0 or x >= a.width:
                continue
            inner = (l + pad_i) * dsf <= x < (rr - pad_i) * dsf and (t + pad_i) * dsf <= y < (bb - pad_i) * dsf
            if inner:
                continue
            total += 1
            pa, pb = a.getpixel((x, y)), b.getpixel((x, y))
            if max(abs(pa[i] - pb[i]) for i in range(3)) > 48:
                changed += 1
    return changed, total


def painted_focus(pg, name, limit=70):
    seen, plain, hidden, stops = set(), [], [], 0
    pg.evaluate("() => { document.activeElement && document.activeElement.blur(); window.scrollTo(0, 0); }")
    for _ in range(limit):
        pg.keyboard.press("Tab")
        pg.wait_for_timeout(60)
        st = pg.evaluate(FOCUS_STOP)
        if st is None or st["key"] in seen:
            if stops:
                break
            continue
        seen.add(st["key"])
        stops += 1
        if not st["onTop"]:
            hidden.append(st["key"])
        pg.screenshot(path=f"{TMP}/f1.png")
        pg.evaluate("() => { window.__galibEl = document.activeElement; document.activeElement.blur(); }")
        pg.wait_for_timeout(60)
        pg.screenshot(path=f"{TMP}/f0.png")
        pg.evaluate("() => window.__galibEl.focus({ preventScroll: true })")
        on, off = Image.open(f"{TMP}/f1.png").convert("RGB"), Image.open(f"{TMP}/f0.png").convert("RGB")
        ch, tot = band_change(off, on, st["r"], 1)
        # A 2px ring round a box lights well over a fifth of a 6+3px band.
        if tot == 0 or ch < max(24, tot * 0.15):
            plain.append(f"{st['key']} ({ch}/{tot})")
    check(f"{name}: Tab walks the page ({stops} stops)", stops >= 8, f"{stops} stops")
    check(f"{name}: every Tab stop PAINTS a ring -- pixels round it change when it takes focus",
          not plain, "no ring painted at: " + "; ".join(plain[:8]))
    check(f"{name}: every Tab stop is the element painted at its own centre (nothing covers it)",
          not hidden, "covered: " + "; ".join(hidden[:8]))


with sync_playwright() as p:
    b = p.chromium.launch()

    # ---- fixtures ---------------------------------------------------------
    # A MID-TONE DRAWING (after v326): a mid-green took the dark glass by its
    # average and its words read 3.7:1; the glass picks by what reads now.
    # And A TALL, PHONE-SHAPED ONE, narrower on a desk than the pill's words.
    # Posted FIRST, so they are the oldest and the Gallery's first screen is
    # what it was (a tall card first left five lines of words on a phone's
    # first screen, where the page's contrast row reads at least six), and in
    # a context of their own, so the Pad's autosave does not carry them into
    # the drafts the Pad saves below.
    _fx = b.new_context(**DESK)
    _fp = open_page(_fx, "/skribl-pad")
    for _t, _bg, _w, _h in (("meadow", "#4f7a2a", 816, 612), ("reed", "#1e1640", 390, 844)):
        _mb = {"title": f"{TAG} {_t}", "version": 2, "schemaVersion": 2, "visibility": "public", "playbackMode": "replay",
               "frames": [{"strokes": [{"x": 60 + i * 20, "y": 120 + (i % 4) * 25, "color": "#ff4fa3", "size": 8, "t": i * 120} for i in range(14)],
                           "strokeGroups": [14], "background": {"color": _bg}}],
               "canvasSize": {"cssWidth": _w, "cssHeight": _h}}
        _fp.evaluate("(d) => loadSkribl(d)", _mb); _fp.wait_for_timeout(1200)
        _mb["thumbnail"] = _fp.evaluate("() => window.SkriblPostedCard.build(window.skriblPreviewCanvas())")
        urllib.request.urlopen(urllib.request.Request(BASE + "/api/skribls", data=json.dumps(_mb).encode(),
                                                      headers={"Content-Type": "application/json"}), timeout=20).read()
    _fx.close()
    mine = [post(f"{TAG} {w}") for w in ("coil", "wave", "tide")] + [post(f"{TAG} private", "unlisted")]
    ctx = b.new_context(**DESK)
    pad = open_page(ctx, "/skribl-pad")
    box = pad.locator("#canvas").bounding_box()
    cx, cy = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
    pad.mouse.move(cx, cy); pad.mouse.down()
    for i in range(20):
        pad.mouse.move(cx + i * 6, cy + (i % 5) * 8)
    pad.mouse.up(); pad.wait_for_timeout(300)
    for t in ("half a tree", "unfinished cat"):
        pad.evaluate("(t) => { SkriblSavedDrafts.forget && SkriblSavedDrafts.forget(); SkriblName.set(t); return SkriblSavedDrafts.save(); }", f"{TAG} {t}")
        pad.wait_for_timeout(500)
    # A DARK DRAWING WITH ITS CARD, for the glass pill: made the way the
    # Pad's Post makes one (the card is what the pill reads its tone off).
    _nb = {"title": f"{TAG} night", "version": 2, "schemaVersion": 2, "visibility": "public", "playbackMode": "replay",
           "frames": [{"strokes": [{"x": 200 + i * 30, "y": 200 + (i % 4) * 25, "color": "#c9b8ff", "size": 10, "t": i * 120} for i in range(14)],
                       "strokeGroups": [14], "background": {"color": "#1e1640"}}],
           "canvasSize": {"cssWidth": 816, "cssHeight": 612}}
    pad.evaluate("(d) => loadSkribl(d)", _nb); pad.wait_for_timeout(1200)
    _nb["thumbnail"] = pad.evaluate("() => window.SkriblPostedCard.build(window.skriblPreviewCanvas())")
    urllib.request.urlopen(urllib.request.Request(BASE + "/api/skribls", data=json.dumps(_nb).encode(),
                                                  headers={"Content-Type": "application/json"}), timeout=20).read()
    remember(pad, mine)
    state = ctx.storage_state(indexed_db=True)
    pad.close()

    # ================================================================ FOCUS
    print("\nGALIB 1 -- every Tab stop on /gallery and /library paints its focus")
    for path in ("/gallery", "/library"):
        pg = open_page(ctx, path)
        pg.wait_for_timeout(600)
        painted_focus(pg, path)
        pg.close()

    # A FINGER SHOWS NO RING (owner's iPhone, after v324: a purple outline round
    # the menu's first row as it opened). The menu moves focus to its first
    # row, and Safari draws :focus-visible for that even after a tap. Chromium
    # cannot be made to, so the two parts are read apart: a pointer marks the
    # page "pointer" (lib/modalfocus.js), and a row whose ring IS showing
    # (reached by a key) paints none once the page is marked so -- the state
    # Safari is in after a tap -- and paints it again after a key.
    RING = """() => { const el = document.activeElement; if (!el || el === document.body) return null;
      const c = getComputedStyle(el); return { fv: el.matches(':focus-visible'), outline: c.outlineStyle,
        how: document.documentElement.getAttribute('data-input'), what: el.className || el.tagName }; }"""
    for path in ("/gallery", "/library"):
        pg = open_page(ctx, path)
        pg.click("#pageMenuBtn"); pg.wait_for_timeout(700)
        how = pg.evaluate("() => document.documentElement.getAttribute('data-input')")
        pg.keyboard.press("Tab"); pg.keyboard.press("Shift+Tab"); pg.wait_for_timeout(150)
        k = pg.evaluate(RING)
        pg.evaluate("() => document.documentElement.setAttribute('data-input', 'pointer')")
        t = pg.evaluate(RING)
        check(f"{path}: a pointer marks the page, and a focused row with its ring showing paints none after a pointer, as on a phone",
              how == "pointer" and t and t["fv"] and t["outline"] == "none", f"after the click {how}; {t}")
        check(f"{path}: ...and a key brings the ring back",
              k and k["fv"] and k["how"] == "key" and k["outline"] != "none", str(k))
        pg.close()

    # ========================================================= DELETE FLOWS
    print("\nGALIB 2 -- a draft's Delete asks without moving; a posted Delete holds its arm")
    # A DESK'S DELETE KEEPS ITS BOX (the v317 bin rule, kept by D3's labelled
    # Delete): armed, it turns red with its word and its size, and the row's
    # second line asks. "Tap again to delete" in the button would have pushed
    # Save file aside, under the next click.
    pg = open_page(ctx, "/library#drafts")
    pg.wait_for_timeout(900)
    DEL = """() => { const d = document.querySelector('#draftsList .draft-del');
      const row = d.closest('.draft-row'), m = row.querySelector('.draft-meta'), r = d.getBoundingClientRect();
      const f = row.querySelector('.draft-file');   // none before D3: the bin stood alone
      return { w: r.width, h: r.height, x: r.left, fx: f ? f.getBoundingClientRect().left : null, armed: d.classList.contains('armed'),
               word: d.textContent.trim(), meta: m.textContent, live: m.getAttribute('aria-live'),
               label: d.getAttribute('aria-label'), ink: getComputedStyle(d).color }; }"""
    b0 = pg.evaluate(DEL)
    pg.click("#draftsList .draft-del >> nth=0")
    pg.wait_for_timeout(250)
    b1 = pg.evaluate(DEL)
    check("library: the armed Delete keeps its word, its box and its place, and so does Save file beside it",
          b1["armed"] and b0["w"] == b1["w"] and b0["h"] == b1["h"] >= 34 and b0["x"] == b1["x"]
          and b0["fx"] is not None and b0["fx"] == b1["fx"] and b0["word"] == b1["word"] == "Delete", f"{b0} -> {b1}")
    check("library: the question is on the meta line, which speaks, and Delete's ink turns",
          b1["meta"] != b0["meta"] and "again" in b1["meta"] and b1["live"] == "polite"
          and b1["label"].startswith("Tap again") and b1["ink"] != b0["ink"], f"{b0} -> {b1}")
    pg.keyboard.press("Tab"); pg.wait_for_timeout(200)
    check("library: focus leaving Delete disarms it", not pg.evaluate(DEL)["armed"])
    pg.click("#draftsList .draft-del >> nth=0"); pg.wait_for_timeout(200)
    pg.mouse.click(5, 400); pg.wait_for_timeout(200)
    b2 = pg.evaluate(DEL)
    check("library: a tap anywhere else disarms it, and the meta line comes back",
          not b2["armed"] and b2["meta"] == b0["meta"], str(b2))
    pg.close()

    pg = open_page(ctx, "/library")
    pg.wait_for_timeout(900)
    pg.click(".posted-delete >> nth=0")
    pg.wait_for_timeout(4600)
    held = pg.evaluate("() => { const d = document.querySelector('.posted-delete'); return { armed: d.dataset.armed, cls: d.className, label: d.getAttribute('aria-label') }; }")
    check("library: a posted Delete is still armed 4.6 s after the first tap (it was a 4 s race)",
          held["armed"] == "1" and "armed" in held["cls"], str(held))
    check("library: ...and its warning says the link stops working at once (no shared caching here)",
          "stops working at once" in (held["label"] or "") and "5 minutes" not in (held["label"] or ""), str(held))
    pg.mouse.click(5, 400); pg.wait_for_timeout(200)
    check("library: ...and a tap elsewhere disarms it",
          pg.evaluate("() => document.querySelector('.posted-delete').dataset.armed") == "", "")
    # A HOST THAT LETS NETWORKS CACHE PUBLIC MEDIA (the page carries
    # data-skribl-shared-cache; verify_mediaauthz pins that the server sets it
    # only then): the confirmation no longer promises "at once" everywhere
    # (owner's pick; SK-AUD-011).
    pg.evaluate("() => document.body.setAttribute('data-skribl-shared-cache', '1')")
    pg.click(".posted-delete >> nth=0"); pg.wait_for_timeout(300)
    cl = pg.evaluate("() => document.querySelector('.posted-delete').getAttribute('aria-label')") or ""
    check("library: on a host that caches public media, the warning says cached copies can take up to 5 minutes",
          "gone from here at once" in cl and "up to 5 minutes" in cl and "cannot be undone" in cl, cl)
    pg.mouse.click(5, 400); pg.wait_for_timeout(200)
    pg.close()

    # The editors' saved-drafts sheet is the same row (D3): its end is the
    # same ⋯, at every width, since the sheet is a phone's width even on a
    # desk; and its menu floats over the list, whose edge would cut it off.
    # The last row's menu reaches past the list's foot, so its words are
    # painted only if it floats.
    SHEET = """() => { const s = document.getElementById('savedDraftsSheet');
      const r = s.querySelector('.sdrafts-row.more-open') || [...s.querySelectorAll('.sdrafts-row')].pop();
      const more = r.querySelector('.draft-more'), mr = more ? more.getBoundingClientRect() : null;
      const list = s.querySelector('.sdrafts-list').getBoundingClientRect();
      const bs = [...r.querySelectorAll('.draft-act')].filter(b => b.getClientRects().length);
      const d = r.querySelector('.draft-del'), dr = d && d.getBoundingClientRect();
      return { more: mr ? [Math.round(mr.width), Math.round(mr.height)] : null, open: r.classList.contains('more-open'),
               words: bs.map(b => b.innerText.trim()), tall: bs.every(b => b.getBoundingClientRect().height >= 44),
               painted: bs.map(b => { const q = b.getBoundingClientRect(), at = document.elementFromPoint(q.left + q.width / 2, q.top + q.height / 2); return !!(at && b.contains(at)); }),
               past: bs.some(b => b.getBoundingClientRect().bottom > list.bottom + 1),
               del: d ? [d.classList.contains('armed'), d.innerText.trim(), Math.round(dr.height), Math.round(dr.top)] : null }; }"""
    for ed, path in (("Pad", "/skribl-pad"), ("Flip", "/flip")):
        pg = open_page(ctx, path)
        pg.evaluate("() => SkriblSavedDrafts.open()")
        pg.wait_for_timeout(900)
        s0 = pg.evaluate(SHEET)
        if s0["more"]:
            pg.locator("#savedDraftsSheet .sdrafts-row").last.locator(".draft-more").click(); pg.wait_for_timeout(250)
        s1 = pg.evaluate(SHEET)
        check(f"the {ed}'s drafts sheet: a row ends in one ⋯, 44px, opening Open, Save a .skribl file and Delete, each 44px tall",
              s0["more"] == [44, 44] and s0["words"] == [] and s1["open"] and s1["words"][1:] == ["Save a .skribl file", "Delete"]
              and s1["words"][0].startswith("Open in ") and s1["tall"], f"{s0} -> {s1}")
        check(f"the {ed}'s drafts sheet: ...the last row's menu reaches past the list's foot and every word is painted (it floats)",
              s1["past"] and len(s1["painted"]) == 3 and all(s1["painted"]), str(s1))
        if s1["open"]:
            pg.locator("#savedDraftsSheet .sdrafts-row.more-open .draft-del").click(); pg.wait_for_timeout(250)
        s2 = pg.evaluate(SHEET)
        check(f"the {ed}'s drafts sheet: Delete asks in place, its word the question, its box and place kept",
              bool(s1["del"]) and bool(s2["del"]) and s2["del"][:2] == [True, "Tap again to delete"]
              and s2["del"][2:] == s1["del"][2:], f"{s1['del']} -> {s2['del']}")
        pg.keyboard.press("Tab"); pg.wait_for_timeout(200)
        check(f"the {ed}'s drafts sheet: focus leaving Delete disarms it",
              not (pg.evaluate(SHEET)["del"] or [True])[0])
        pg.close()

    # ================================================================ MENU
    print("\nGALIB 3 -- the page menu is the editors' menu: their paper and cards, a popover on a desktop, a sheet on a phone")
    # THE EDITORS' PAPER (after v324: the Gallery and Library menu mock, A,
    # "All yes"). It was the Pad's glass; the editors' menu moved to solid
    # lilac paper with white cards after v323, and this one now wears the
    # same, read here off the Pad's own menu in the same theme, not typed.
    MENU = """() => { const s = document.getElementById('pageMenu'), b = document.getElementById('pageMenuBtn');
      const sr = s.getBoundingClientRect(), br = b.getBoundingClientRect(), cs = getComputedStyle(s);
      const scrim = getComputedStyle(document.getElementById('pageMenuOverlay'), '::before');
      const l = s.querySelector('.pm-list'), lc = l ? getComputedStyle(l) : null, t = s.querySelector('.pm-seg');
      return { right: sr.right - br.right, gap: sr.top - br.bottom, w: sr.width, left: sr.left,
               bottom: innerHeight - sr.bottom, vw: innerWidth, bf: cs.backdropFilter, bg: cs.backgroundColor,
               r: cs.borderTopLeftRadius, pad: cs.paddingTop,
               card: lc && lc.backgroundColor, line: lc && lc.borderTopColor, cardR: lc && lc.borderTopLeftRadius,
               places: l ? l.querySelectorAll('a[data-dest]').length : 0, track: t && getComputedStyle(t).backgroundColor,
               weight: getComputedStyle(s.querySelector('.pm-item')).fontWeight,
               scrim: scrim.backgroundColor, scrimBf: scrim.backdropFilter }; }"""
    PAD = """() => { const m = document.getElementById('menuSheet'), l = m.querySelector('.menu-list'), t = m.querySelector('.menu-editor-seg');
      return { bg: getComputedStyle(m).backgroundColor, card: getComputedStyle(l).backgroundColor,
               line: getComputedStyle(l).borderTopColor, track: getComputedStyle(t).backgroundColor }; }"""
    for theme in ("dark", "light"):
        pg = open_page(ctx, "/skribl-pad", theme)
        pg.evaluate("() => document.getElementById('menuBtn').click()"); pg.wait_for_timeout(700)
        pad = pg.evaluate(PAD)
        pg.close()
        for path in ("/gallery", "/library"):
            pg = open_page(ctx, path, theme)
            pg.click("#pageMenuBtn"); pg.wait_for_timeout(500)
            m = pg.evaluate(MENU)
            check(f"{path} {theme}: the menu is the editors' paper -- solid, the Pad's paper, its four places one card "
                  "of the Pad's white with the lilac edge, Theme on that card, 600 rows, a blurred .4 dim",
                  m["bf"] == "none" and m["bg"] == pad["bg"] and m["places"] == 4 and m["card"] == pad["card"]
                  and m["line"] == pad["line"] and m["track"] == pad["card"] and m["weight"] == "600"
                  and "blur(2px)" in m["scrimBf"] and abs(_rgba(m["scrim"])[1] - 0.4) < 0.01, f"{m} pad={pad}")
            if theme == "dark":
                check(f"{path}: on a desktop it is the editors' popover under the ••• -- 336 wide, a 22 corner, "
                      "12px of room, cards at 16, right edges flush, 8px below",
                      abs(m["right"]) <= 1 and abs(m["gap"] - 8) <= 1 and abs(m["w"] - 336) <= 1
                      and m["r"] == "22px" and m["pad"] == "12px" and m["cardR"] == "16px", str(m))
            pg.close()
    phone = b.new_context(storage_state=state, **PHONE)
    for path in ("/gallery", "/library"):
        pg = open_page(phone, path)
        pg.tap("#pageMenuBtn"); pg.wait_for_timeout(600)
        m = pg.evaluate(MENU)
        check(f"{path}: on a phone it is a full-bleed bottom sheet",
              m["left"] == 0 and m["w"] == m["vw"] and abs(m["bottom"]) <= 1, str(m))
        pg.tap("#pageMenu .pm-grab"); pg.wait_for_timeout(600)
        check(f"{path}: ...and its grab bar closes it",
              pg.evaluate("() => document.getElementById('pageMenuOverlay').hidden"))
        pg.close()

    # ============================================================== HEADER
    print("\nGALIB 4 -- one header and one lockup on both pages")
    # THE EDITORS' HEADER (owner, after v324: the mock, C, "All yes"). No card
    # at rest: the controls sit on the page and the mark lines up with the
    # page's own text (the card's padding had set it 14px in, "indented"
    # under the heading), the page's word beside the mark is gone (the heading
    # says it), and once scrolled the ground is a band (the scrolled reads at
    # the end paint it, and its fade frame by frame). Sticky either way, and the band adds no width to the page.
    HEAD = """() => { const t = document.querySelector('.top'), cs = getComputedStyle(t);
      const mk = getComputedStyle(document.querySelector('#galleryMake, #libMake'));
      const a = (c) => { const m = c.match(/[\\d.]+/g); return !m ? 0 : (m.length > 3 ? +m[3] : 1); };
      const paints = (s) => s !== 'none' && (s.match(/rgba?\\([^)]*\\)/g) || []).some(c => a(c) > 0);
      const h1 = document.querySelector('h1, #whoName');
      return { pos: cs.position, fill: a(cs.backgroundColor), shadow: paints(cs.boxShadow), scrolled: t.classList.contains('scrolled'),
               top: Math.round(t.getBoundingClientRect().top), over: document.documentElement.scrollWidth - innerWidth,
               mark: Math.round(document.querySelector('.brand .brand-mark').getBoundingClientRect().left),
               text: h1 ? Math.round(h1.getBoundingClientRect().left) : null, word: !!document.querySelector('.brand .tag'),
               hand: (() => { const w = document.querySelector('.brand .brand-word svg path'), m = document.querySelector('.brand .brand-mark');
                 return w ? [Math.round(w.ownerSVGElement.getBoundingClientRect().height), Math.round(m.getBoundingClientRect().height),
                              Math.round(w.ownerSVGElement.getBoundingClientRect().left - m.getBoundingClientRect().right)] : null; })(),
               lockup: [document.querySelector('.brand .brand-mark').getBoundingClientRect().height, mk.fontWeight, mk.fontSize] }; }"""
    lockups = {}
    for path in ("/gallery", "/library"):
        for dev, c_, pin in (("desk", ctx, 12), ("390", phone, 6)):
            pg = open_page(c_, path)
            h = pg.evaluate(HEAD)
            lockups[path] = h["lockup"]
            check(f"{path} {dev}: at rest the header paints no card, and the mark lines up with the page's text, no word in capitals beside it",
                  h["pos"] == "sticky" and h["fill"] == 0 and not h["shadow"] and not h["scrolled"]
                  and h["text"] is not None and abs(h["mark"] - h["text"]) <= 1 and not h["word"], str(h))
            # THE PAGE'S WORD IN THE SAME HAND (owner, after v324: "when you scroll
            # you don't know where you are ... It should say gallery or library in
            # the same cursive. Same size."): drawn beside the mark, as tall, and
            # as close as "pad" sits on the Pad (within a few px either way).
            check(f"{path} {dev}: the lockup writes the page's word beside the mark, the mark's height, close to it",
                  h["hand"] and h["hand"][0] == h["hand"][1] and -4 <= h["hand"][2] <= 2, str(h["hand"]))
            pg.evaluate("document.body.style.minHeight = '3000px'; window.scrollTo(0, 600)"); pg.wait_for_timeout(500)
            h = pg.evaluate(HEAD)
            check(f"{path} {dev}: scrolled, it is pinned {pin}px from the top on its ground, and nothing overflows",
                  h["pos"] == "sticky" and h["scrolled"] and h["fill"] == 1
                  and abs(h["top"] - pin) <= 1 and h["over"] <= 0, str(h))
            pg.close()
    check("ONE lockup: mark height and Make one's weight/size agree on both pages",
          lockups["/gallery"] == lockups["/library"] and lockups["/gallery"] == [30, "600", "13px"], str(lockups))

    # AT 150% THE ••• WAS OUT OF REACH (owner, L3). A 402pt iPhone at Safari's
    # 150% lays the page out 268px wide; the lockup, Make one and the ••• took
    # about 297, and the ••• sat past the right edge. Below the 320 safety net
    # Make one is a round + now (the Pad's Post at that size), still named
    # Make one; at 320 it keeps its words. Not a phone context: a phone's
    # browser here zooms a too-wide page out to fit, which Safari's Page Zoom
    # does not, and that would hide the very overflow this reads.
    MAKE = """() => { const m = document.getElementById('pageMenuBtn').getBoundingClientRect();
      const k = document.querySelector('#galleryMake, #libMake'), kb = k.getBoundingClientRect();
      const at = document.elementFromPoint(m.left + m.width / 2, m.top + m.height / 2);
      const plus = k.querySelector('.make-plus'), words = k.querySelector('span').getBoundingClientRect();
      return { width: innerWidth, page: document.documentElement.scrollWidth, menu: [Math.round(m.left), Math.round(m.right)],
               reach: !!(at && at.closest('#pageMenuBtn')), make: [Math.round(kb.width), Math.round(kb.height)],
               plus: !!plus && plus.getBoundingClientRect().width > 0, words: Math.round(words.width) }; }"""
    for _w in (268, 320):
        _nc = b.new_context(storage_state=state, viewport={"width": _w, "height": 600}, device_scale_factor=3, has_touch=True)
        for path in ("/gallery", "/library"):
            pg = open_page(_nc, path)
            k = pg.evaluate(MAKE)
            named = pg.get_by_role("link", name="Make one").count()
            if _w == 268:
                check(f"{path} at 150% (268): the ••• is on screen and answers its own centre, the page no wider than the window",
                      k["reach"] and k["menu"][1] <= k["width"] and k["page"] <= k["width"], str(k))
                check(f"{path} at 150% (268): Make one is a round + 44px across, still named Make one",
                      k["plus"] and abs(k["make"][0] - 44) <= 1 and abs(k["make"][1] - 44) <= 1 and k["words"] <= 1 and named == 1,
                      f"{k}, named {named}")
            else:
                check(f"{path} at the 320 safety net: Make one keeps its words",
                      not k["plus"] and k["words"] > 40 and k["reach"] and named == 1, f"{k}, named {named}")
            pg.close()
        _nc.close()

    # ========================================================= REPORT SHEET
    print("\nGALIB 5 -- the report sheet: a bottom sheet on a phone, a centred card on a desktop")
    REP = """() => { const c = document.getElementById('reportForm'), r = c.getBoundingClientRect(), cs = getComputedStyle(c);
      const g = c.querySelector('.pm-grab'), gr = g ? g.getBoundingClientRect() : null;
      return { left: r.left, w: r.width, bottom: innerHeight - r.bottom, cx: r.left + r.width / 2 - innerWidth / 2,
               cy: r.top + r.height / 2 - innerHeight / 2, vw: innerWidth, bf: cs.backdropFilter,
               grab: gr ? gr.height > 0 : false, radius: cs.borderTopLeftRadius + ' ' + cs.borderBottomLeftRadius,
               focusIn: c.contains(document.activeElement) }; }"""
    pg = open_page(phone, "/gallery")
    pg.tap(".tile .tileMore"); pg.wait_for_timeout(400)
    pg.tap(".cmReport"); pg.wait_for_timeout(700)
    r = pg.evaluate(REP)
    check("phone: the report sheet is a full-width glass bottom sheet with a grab bar, focus inside",
          r["left"] == 0 and r["w"] == r["vw"] and abs(r["bottom"]) <= 1 and r["grab"]
          and "blur(14px)" in r["bf"] and r["radius"] == "20px 0px" and r["focusIn"], str(r))
    pg.tap("#reportForm .pm-grab"); pg.wait_for_timeout(600)
    check("phone: the grab bar closes it, and focus goes back to the tile's •••",
          pg.evaluate("() => document.getElementById('reportSheet').hidden && document.activeElement.classList.contains('tileMore')"))
    pg.close()
    pg = open_page(ctx, "/gallery")
    pg.click(".tile .tileMore"); pg.wait_for_timeout(300)
    pg.click(".cmReport"); pg.wait_for_timeout(500)
    r = pg.evaluate(REP)
    check("desktop: the report sheet is a centred glass card with no grab bar",
          abs(r["cx"]) <= 1 and abs(r["cy"]) <= 1 and not r["grab"] and "blur(14px)" in r["bf"]
          and r["radius"] == "16px 16px" and r["focusIn"], str(r))
    pg.keyboard.press("Escape"); pg.wait_for_timeout(400)
    check("desktop: Escape closes it", pg.evaluate("() => document.getElementById('reportSheet').hidden"))
    pg.close()

    # ============================================================= CONTRAST
    print("\nGALIB 6 -- every word inside the glass sheets clears AA on the pixels behind it")
    MENU_TEXT = ['.pm-text', '.pm-sub', '.pm-label', '.pm-version', '.pm-foot-link', '.pm-seg > button']
    PAGE_TEXT = ['h1', '.sub', '.who .bio', '.stat b', '.stat span', '.brand .tag', '.tile .tt', '.tile .tdn', '.tile .tm',
                 '.seg-track > button', '.now .lbl', '.pmeta .ptitle', '.pmeta .prow > span', '.kind', '.telapsed',
                 '.posted-title', '.posted-sub', '.posted-count', '.foot', '.state',
                 # a desk row's own buttons and the note under the list: the
                 # red Delete read 5.1 here while nothing measured it
                 '.posted-actions .posted-lbl', '.posted-foot-note > span', '.posted-clearbtn', '.posted-clearbtn > span']
    REPORT_TEXT = ['#reportTitle', '.sheet-card > p', '.reasons legend', '.reason', 'label > .sheet-status',
                   '.sheet-status > span', '.sheet-actions .btn']
    for form, kw in (("desktop", DESK), ("phone", PHONE)):
        dsf = kw.get("device_scale_factor", 1)
        for theme in ("light", "dark"):
            c2 = b.new_context(storage_state=state, color_scheme=theme, **kw)
            for path in ("/gallery", "/library"):
                pg = open_page(c2, path, theme)
                # PERFECTLY SHARP (owner, after v324: "consistency simplicity
                # elegant and perfectly sharp contrast"). Every word on the page
                # itself reads 7:1 or more against what is behind it, both
                # inks; the action purple's white words (Make one) are the
                # app's, shared with the editors, and held to AA with them.
                res = glass_contrast(pg, PAGE_TEXT, dsf)
                soft = [x for x in res if x[1] < 7]
                check(f"{path} {form} {theme}: every word on the page reads 7:1 or more on real pixels ({len(res)} measured)",
                      len(res) >= 6 and not soft, str(soft[:5]))
                pg.click("#pageMenuBtn"); pg.wait_for_timeout(700)
                res = glass_contrast(pg, MENU_TEXT, dsf)
                bad = [x for x in res if x[1] < x[2]]
                check(f"{path} {form} {theme}: menu words clear AA on real pixels ({len(res)} measured)",
                      len(res) >= 8 and not bad, str(bad[:5]))
                pg.close()
            pg = open_page(c2, "/gallery", theme)
            pg.click(".tile .tileMore"); pg.wait_for_timeout(400)
            res = glass_contrast(pg, [".cmItem span"], dsf)
            bad = [x for x in res if x[1] < x[2]]
            check(f"/gallery {form} {theme}: card menu words clear AA on real pixels ({len(res)} measured)",
                  len(res) >= 3 and not bad, str(bad[:5]))
            pg.click(".cmReport"); pg.wait_for_timeout(700)
            pg.evaluate("() => document.activeElement.blur()")
            res = glass_contrast(pg, REPORT_TEXT, dsf)
            bad = [x for x in res if x[1] < x[2]]
            check(f"/gallery {form} {theme}: report sheet words clear AA on real pixels ({len(res)} measured)",
                  len(res) >= 8 and not bad, str(bad[:5]))
            pg.close()
            c2.close()

    # ========================================================= ROW ACTIONS
    print("\nGALIB 7 -- at 390, one ⋯ a row; its own buttons open under it with their words, no dead tap between them")
    # The owner's pick A after v324 ("all yes"): four unlabelled round icons
    # under each title became one ⋯, and the row's own buttons open under it
    # as its menu -- the same buttons, so Copied, the gallery switch and
    # Delete's second tap are unchanged. Delete is last, past a rule.
    def _tap(loc):
        # Only what is there: without the ⋯ the rows below report red rather
        # than the suite stopping on a 30 s wait.
        if loc.count() and loc.first.is_visible():
            loc.first.tap()
    for theme in ("light", "dark"):
        pg = open_page(phone, "/library", theme)
        pg.wait_for_timeout(600)
        rest = pg.evaluate("""() => { const rows = [...document.querySelectorAll('.posted-row.posted-row-keyed')];
          return { rows: rows.length,
                   dots: rows.filter(r => { const b = r.querySelector('.posted-more'); if (!b) return false;
                     const x = b.getBoundingClientRect(); return x.width >= 44 && x.height >= 44; }).length,
                   strips: rows.filter(r => r.querySelector('.posted-actions').getClientRects().length).length }; }""")
        check(f"library 390 {theme}: every keyed row shows one ⋯, 44px, and no strip of icons",
              rest["rows"] >= 3 and rest["dots"] == rest["rows"] and rest["strips"] == 0, str(rest))
        row = pg.locator(".posted-row.posted-row-keyed").nth(1)
        row.scroll_into_view_if_needed()
        _tap(row.locator(".posted-more")); pg.wait_for_timeout(300)
        m = pg.evaluate("""() => { const r = document.querySelector('.posted-row.more-open'); if (!r) return null;
          const s = r.querySelector('.posted-actions'), sr = s.getBoundingClientRect();
          const bs = [...s.querySelectorAll('button')].filter(b => b.getClientRects().length)
                       .sort((a, b) => a.getBoundingClientRect().top - b.getBoundingClientRect().top);
          let dead = 0;
          // The rule before Delete is the one gap, on purpose (a menu's
          // destructive row stands apart); it is held to its 13px instead.
          const rule = bs.length > 1 ? Math.round(bs[bs.length - 1].getBoundingClientRect().top - bs[bs.length - 2].getBoundingClientRect().bottom) : 0;
          for (let i = 0; i + 2 < bs.length; i++) {
            const a = bs[i].getBoundingClientRect(), c = bs[i + 1].getBoundingClientRect(), x = a.left + a.width / 2;
            for (let y = Math.ceil(a.bottom) - 1; y <= Math.floor(c.top) + 1; y++) {
              const hit = document.elementFromPoint(x, y);
              if (!hit || !hit.closest || !hit.closest('.posted-actions button')) dead++; } }
          return { words: bs.map(b => b.textContent.trim()), last: bs.length && bs[bs.length - 1].classList.contains('posted-delete'),
                   tall: bs.every(b => b.getBoundingClientRect().height >= 44), dead, rule,
                   onScreen: sr.left >= 0 && sr.right <= innerWidth && sr.bottom <= innerHeight,
                   focus: document.activeElement === bs.find(b => b.classList.contains('posted-copy')),
                   expanded: r.querySelector('.posted-more').getAttribute('aria-expanded') }; }""")
        check(f"library 390 {theme}: the ⋯ opens the row's buttons with their words, Delete last, each 44px tall, on screen, the first focused",
              bool(m) and m["words"][:1] == ["Copy link"] and m["last"] and m["tall"] and m["onScreen"] and m["focus"]
              and m["expanded"] == "true" and all(m["words"]), str(m))
        mc = glass_contrast(pg, ['.posted-row.more-open .posted-actions .posted-lbl'], 2)
        check(f"library 390 {theme}: every word in the open menu reads 7:1 or more on real pixels ({len(mc)} measured)",
              len(mc) >= 4 and not [x for x in mc if x[1] < 7], str([x for x in mc if x[1] < 7][:4]))
        check(f"library 390 {theme}: every point between two of its buttons lands on one of them, but for the 13px rule before Delete",
              bool(m) and m["dead"] == 0 and m["rule"] <= 13, str(m and [m["dead"], m["rule"]]))
        pg.keyboard.press("Escape"); pg.wait_for_timeout(200)
        shut = pg.evaluate("() => [!document.querySelector('.posted-row.more-open'), document.activeElement.classList.contains('posted-more')]")
        check(f"library 390 {theme}: Escape closes it and hands focus back to the ⋯", shut == [True, True], str(shut))
        _tap(row.locator(".posted-more")); pg.wait_for_timeout(200)
        pg.mouse.click(5, 120); pg.wait_for_timeout(200)
        check(f"library 390 {theme}: a tap anywhere else closes it",
              pg.evaluate("() => !document.querySelector('.posted-row.more-open')"))
        pg.close()
    # And the menu's Delete is the row's Delete: it arms in place, and the
    # second tap takes the post down.
    pg = open_page(phone, "/library")
    pg.wait_for_timeout(600)
    victim = pg.locator(".posted-row.posted-row-keyed", has_text=f"{TAG} tide")
    victim.scroll_into_view_if_needed()
    _tap(victim.locator(".posted-more")); pg.wait_for_timeout(200)
    _tap(victim.locator(".posted-delete")); pg.wait_for_timeout(300)
    armed = pg.evaluate("""(t) => { const r = [...document.querySelectorAll('.posted-row')].find(e => e.textContent.includes(t));
      const d = r && r.querySelector('.posted-delete'); return d && [d.classList.contains('armed'), d.textContent.trim(), r.classList.contains('more-open')]; }""", f"{TAG} tide")
    ac = glass_contrast(pg, ['.posted-row.more-open .posted-delete.armed .posted-lbl'], 2)
    check("library 390: the armed warning reads 7:1 or more on its red", len(ac) == 1 and ac[0][1] >= 7, str(ac))
    _tap(victim.locator(".posted-delete")); pg.wait_for_timeout(1500)
    gone = pg.evaluate("(t) => ![...document.querySelectorAll('.posted-row')].some(e => e.textContent.includes(t))", f"{TAG} tide")
    check("library 390: the menu's Delete arms in place, saying so, and the second tap takes the post down",
          armed == [True, "Tap again to delete", True] and gone, f"{armed}, gone {gone}")
    pg.close()

    # A DRAFT ROW ENDS AS A POSTED ROW DOES (D3, the owner's pick A): a
    # phone's one ⋯ with Open in Pad (or Flip), Save a .skribl file and
    # Delete, last, under a line; a desk's Save file and Delete. It ended in a
    # bin, so the two lists behaved differently. lib/savedrafts.js rowEnd.
    print("\nGALIB 2b -- a draft row ends as a posted row does: a phone's ⋯, a desk's Save file and Delete")
    _ROW = {"strokes": [{"x": 40 + i * 9, "y": 60 + (i % 4) * 7, "color": "#7c5cff", "size": 6, "t": i * 30} for i in range(16)],
            "strokeGroups": [16], "background": {"color": "#ffffff"}}
    FILE_ME = {"version": 2, "schemaVersion": 2, "playbackMode": "replay", "title": f"{TAG} file me",
               "canvasSize": {"cssWidth": 400, "cssHeight": 300}, "frames": [_ROW]}
    # A Flip draft keeps an in-between page as its recipe (flip.js
    # serializeFlip), which only Flip can draw.
    TWEENED = {"version": 2, "schemaVersion": 2, "playbackMode": "flip", "fps": 8, "title": f"{TAG} tweened",
               "canvasSize": {"cssWidth": 400, "cssHeight": 300},
               "frames": [_ROW, {"gen": {"n": 1}, "background": "#ffffff"}, _ROW]}
    DMENU = """(t) => { const r = [...document.querySelectorAll('#draftsList .draft-row')].find(e => e.textContent.includes(t));
      if (!r) return null; const vis = e => !!(e && e.getClientRects().length);
      const more = r.querySelector('.draft-more'), s = r.querySelector('.draft-acts');
      if (!more || !s) return { missing: true, more: null, open: false, expanded: null, words: [], tall: false, dead: 0,
                                rule: 0, painted: false, onScreen: false, href: '', focus: false, del: [false, ''] };
      const mr = more.getBoundingClientRect(), sr = s.getBoundingClientRect();
      const bs = [...r.querySelectorAll('.draft-act')].filter(vis).sort((a, b) => a.getBoundingClientRect().top - b.getBoundingClientRect().top);
      let dead = 0;
      for (let i = 0; i + 2 < bs.length; i++) {
        const a = bs[i].getBoundingClientRect(), c = bs[i + 1].getBoundingClientRect(), x = a.left + a.width / 2;
        for (let y = Math.ceil(a.bottom) - 1; y <= Math.floor(c.top) + 1; y++) {
          const hit = document.elementFromPoint(x, y);
          if (!hit || !hit.closest || !hit.closest('.draft-act')) dead++; } }
      const rule = bs.length > 1 ? Math.round(bs[bs.length - 1].getBoundingClientRect().top - bs[bs.length - 2].getBoundingClientRect().bottom) : 0;
      return { more: vis(more) ? [Math.round(mr.width), Math.round(mr.height)] : null, open: r.classList.contains('more-open'),
               expanded: more.getAttribute('aria-expanded'), words: bs.map(b => b.innerText.trim()),
               tall: bs.every(b => b.getBoundingClientRect().height >= 44), dead, rule,
               painted: bs.every(b => { const q = b.getBoundingClientRect(), at = document.elementFromPoint(q.left + q.width / 2, q.top + q.height / 2); return !!(at && b.contains(at)); }),
               onScreen: !bs.length || (sr.left >= 0 && sr.right <= innerWidth && sr.bottom <= innerHeight),
               href: (bs[0] && bs[0].getAttribute('href')) || '', focus: !!bs.length && document.activeElement === bs[0],
               del: (() => { const d = r.querySelector('.draft-del'); return [d.classList.contains('armed'), d.innerText.trim()]; })() }; }"""
    seed = open_page(phone, "/library#drafts")
    seed.evaluate("(p) => SkriblSavedDrafts.keep('pad', p.title, p)", FILE_ME)
    seed.evaluate("(p) => SkriblSavedDrafts.keep('flip', p.title, p)", TWEENED)
    seed.close()
    for theme in ("light", "dark"):
        # The theme rides in the query, which must come before the hash, so
        # the tab is chosen by its own control.
        pg = open_page(phone, "/library", theme)
        _tap(pg.locator("#tabDrafts")); pg.wait_for_timeout(700)
        rest = pg.evaluate(DMENU, f"{TAG} file me")
        check(f"drafts 390 {theme}: a draft row ends in one ⋯, 44px, and no buttons beside it",
              bool(rest) and rest["more"] == [44, 44] and rest["words"] == [] and rest["expanded"] == "false", str(rest))
        row = pg.locator("#draftsList .draft-row", has_text=f"{TAG} file me")
        row.scroll_into_view_if_needed()
        _tap(row.locator(".draft-more")); pg.wait_for_timeout(300)
        m = pg.evaluate(DMENU, f"{TAG} file me")
        check(f"drafts 390 {theme}: its ⋯ opens Open in Pad, Save a .skribl file and Delete, each 44px tall, painted, on screen, the first focused",
              bool(m) and m["open"] and m["expanded"] == "true" and m["words"] == ["Open in Pad", "Save a .skribl file", "Delete"]
              and m["tall"] and m["painted"] and m["onScreen"] and m["focus"], str(m))
        check(f"drafts 390 {theme}: ...Open goes to the Pad with the draft, and Delete stands apart, past the 13px rule, with no dead point between the others",
              bool(m) and "?draft=" in m["href"] and 8 <= m["rule"] <= 13 and m["dead"] == 0, str(m and [m["href"], m["rule"], m["dead"]]))
        mc = glass_contrast(pg, ['.draft-row.more-open .draft-act .draft-lbl'], 2)
        check(f"drafts 390 {theme}: every word in the open menu reads 7:1 or more on real pixels ({len(mc)} measured)",
              len(mc) == 3 and not [x for x in mc if x[1] < 7], str(mc))
        _tap(row.locator(".draft-del")); pg.wait_for_timeout(250)
        a = pg.evaluate(DMENU, f"{TAG} file me")
        ac = glass_contrast(pg, ['.draft-row.more-open .draft-del.armed .draft-lbl'], 2)
        check(f"drafts 390 {theme}: the menu's Delete asks in place, the menu still open, reading 7:1 or more on its red",
              bool(a) and a["del"] == [True, "Tap again to delete"] and a["open"] and len(ac) == 1 and ac[0][1] >= 7, f"{a and a['del']}, {ac}")
        pg.keyboard.press("Escape"); pg.wait_for_timeout(200)
        shut = pg.evaluate("() => [!document.querySelector('.draft-row.more-open'), document.activeElement.classList.contains('draft-more')]")
        check(f"drafts 390 {theme}: Escape closes it and hands focus back to the ⋯", shut == [True, True], str(shut))
        _tap(row.locator(".draft-more")); pg.wait_for_timeout(200)
        pg.mouse.click(5, 120); pg.wait_for_timeout(200)
        check(f"drafts 390 {theme}: a tap anywhere else closes it",
              pg.evaluate("() => !document.querySelector('.draft-row.more-open')"))
        pg.close()
    pg = open_page(phone, "/library#drafts")
    pg.wait_for_timeout(600)
    # The newest is listed first, so the tweened Flip draft sits above. Its
    # menu opens down over the row below, so the lower row's menu is opened
    # first and the upper ⋯ is the one tapped while it is open.
    _tap(pg.locator("#draftsList .draft-row", has_text=f"{TAG} file me").locator(".draft-more")); pg.wait_for_timeout(250)
    tw = pg.locator("#draftsList .draft-row", has_text=f"{TAG} tweened")
    tw.scroll_into_view_if_needed()
    _tap(tw.locator(".draft-more")); pg.wait_for_timeout(250)
    t1 = pg.evaluate(DMENU, f"{TAG} tweened")
    t2 = pg.evaluate(DMENU, f"{TAG} file me")
    check("drafts 390: a Flip draft's menu opens it in Flip, and opening one row's menu closes another's",
          bool(t1) and t1["words"][:1] == ["Open in Flip"] and "/flip?draft=" in t1["href"] and t1["open"]
          and bool(t2) and not t2["open"], f"{t1 and [t1['words'], t1['href'], t1['open']]}; file me open {t2 and t2['open']}")
    pg.close()

    # THE LAST ROW AT THE SCREEN'S FOOT (the owner's iPhone, after #538: the
    # last draft's menu opened under its row and past the screen, with only
    # Open in sight). With the screen ending 12px under the last row, its
    # menu stands above its ⋯, inside the screen, every word painted; and so
    # does a posted row's, whose rules it shares.
    FOOT = """(sel) => { const rows = [...document.querySelectorAll(sel)], r = rows[rows.length - 1];
      if (!r) return null; const menu = r.querySelector('.draft-acts, .posted-actions'), more = r.querySelector('.draft-more, .posted-more');
      const bs = [...menu.querySelectorAll('.draft-act, button')].filter(b => b.getClientRects().length);
      const q = menu.getBoundingClientRect(), m = more.getBoundingClientRect();
      return { open: r.classList.contains('more-open'), items: bs.length,
               painted: bs.length > 0 && bs.every(b => { const x = b.getBoundingClientRect(), at = document.elementFromPoint(x.left + x.width / 2, x.top + x.height / 2); return !!(at && b.contains(at)); }),
               inside: q.top >= 0 && Math.round(q.bottom) <= innerHeight, above: Math.round(q.bottom) <= Math.round(m.top) + 1 }; }"""
    for _list, _tab, _sel in (("drafts", "#tabDrafts", "#draftsList .draft-row"), ("posted", "#tabSkribls", ".posted-row.posted-row-keyed")):
        for theme in ("light", "dark"):
            pg = open_page(phone, "/library", theme)
            _tap(pg.locator(_tab)); pg.wait_for_timeout(700)
            last = pg.locator(_sel).last
            if not last.count():
                check(f"{_list} 390 {theme}: the last row's menu, at the screen's foot, stands above its ⋯, inside the screen, every word painted", False, "no rows")
                pg.close(); continue
            last.evaluate("r => r.scrollIntoView({ block: 'end' })"); pg.wait_for_timeout(200)
            _h = pg.evaluate("(sel) => { const rows = [...document.querySelectorAll(sel)]; return Math.round(rows[rows.length - 1].getBoundingClientRect().bottom) + 12; }", _sel)
            pg.set_viewport_size({"width": pg.viewport_size["width"], "height": _h}); pg.wait_for_timeout(300)
            _tap(last.locator(".draft-more, .posted-more")); pg.wait_for_timeout(300)
            ft = pg.evaluate(FOOT, _sel)
            check(f"{_list} 390 {theme}: the last row's menu, at the screen's foot, stands above its ⋯, inside the screen, every word painted",
                  bool(ft) and ft["open"] and ft["items"] >= 3 and ft["inside"] and ft["painted"] and ft["above"], f"{ft}, screen {_h}px")
            pg.close()

    # A desk: the card opens the draft, and the row's end is Save file and
    # Delete. Save file is the file the editor's Save as a file makes, with
    # no editor open; a Flip draft holding an in-between page says why not.
    desk_d = b.new_context(storage_state=state, accept_downloads=True, **DESK)
    seed = open_page(desk_d, "/library#drafts")
    seed.evaluate("(p) => SkriblSavedDrafts.keep('pad', p.title, p)", FILE_ME)
    seed.evaluate("(p) => SkriblSavedDrafts.keep('flip', p.title, p)", TWEENED)
    seed.close()
    for theme in ("light", "dark"):
        pg = open_page(desk_d, "/library", theme)
        pg.click("#tabDrafts"); pg.wait_for_timeout(700)
        d = pg.evaluate(DMENU, f"{TAG} file me")
        check(f"drafts desk {theme}: the row ends in Save file and Delete, painted, 34px or more, and no ⋯",
              bool(d) and d["more"] is None and d["words"] == ["Save file", "Delete"] and d["painted"]
              and all(h >= 34 for h in pg.evaluate("(t) => [...[...document.querySelectorAll('#draftsList .draft-row')].find(e => e.textContent.includes(t)).querySelectorAll('.draft-act')].filter(e => e.getClientRects().length).map(e => e.getBoundingClientRect().height)", f"{TAG} file me")),
              str(d))
        dc = glass_contrast(pg, ['#draftsList .draft-file .draft-lbl', '#draftsList .draft-del .draft-lbl'], 1)
        check(f"drafts desk {theme}: Save file and Delete read 7:1 or more on real pixels ({len(dc)} measured)",
              len(dc) >= 4 and not [x for x in dc if x[1] < 7], str([x for x in dc if x[1] < 7][:4]))
        pg.close()
    pg = open_page(desk_d, "/library#drafts")
    pg.wait_for_timeout(600)
    fbtn = pg.locator("#draftsList .draft-row", has_text=f"{TAG} file me").locator(".draft-file")
    got, body = None, None
    if fbtn.count():
        with pg.expect_download(timeout=15000) as dl:
            fbtn.click()
        got = dl.value
        body = json.loads(open(got.path(), encoding="utf-8").read())
    check("drafts desk: Save file writes the draft as the editor's .skribl file, named for its title, without opening it",
          bool(got) and got.suggested_filename == f"{TAG}-file-me.skribl" and body == FILE_ME and pg.url.endswith("/library#drafts"),
          f"{got and got.suggested_filename}; same as kept: {body == FILE_ME}; at {pg.url}")
    _downloads = []
    pg.on("download", lambda x: _downloads.append(x.suggested_filename))
    trow = pg.locator("#draftsList .draft-row", has_text=f"{TAG} tweened")
    if trow.locator(".draft-file").count():
        trow.locator(".draft-file").click(); pg.wait_for_timeout(1200)
    said = trow.locator(".draft-meta").inner_text() if trow.count() else ""
    check("drafts desk: a Flip draft holding an in-between page writes no file, and its row says only Flip can save it, and where",
          not _downloads and "Only Flip can save this one as a file" in said and "open it there" in said,
          f"downloads {_downloads}; said {said!r}")
    pg.close()
    desk_d.close()

    # The count repeats "N posted" above it, so it is drawn only while a
    # search narrows it, and read out either way; the note about this
    # browser sits under the list, not between the switches and it.
    for dev, c_ in (("desk", ctx), ("390", phone)):
        pg = open_page(c_, "/library")
        pg.wait_for_timeout(600)
        CNT = """() => { const c = document.getElementById('postedCount'), r = c.getBoundingClientRect();
          const rows = [...document.querySelectorAll('#postedList .posted-row')], f = document.querySelector('#postedPanel .posted-foot-top');
          return { text: c.textContent, drawn: r.width > 2 && r.height > 2, live: c.getAttribute('aria-live'),
                   under: !!f && rows.length > 0 && f.getBoundingClientRect().top >= rows[rows.length - 1].getBoundingClientRect().bottom }; }"""
        c0 = pg.evaluate(CNT)
        pg.fill("#postedSearch", "coil"); pg.wait_for_timeout(300)
        c1 = pg.evaluate(CNT)
        check(f"library {dev}: the count is read but not drawn at rest, drawn while a search narrows it, and the note sits under the list",
              "Skribl" in c0["text"] and not c0["drawn"] and c0["live"] == "polite" and " of " in c1["text"] and c1["drawn"] and c0["under"],
              f"{c0} -> {c1}")
        pg.close()

    # ========================================================= LIBRARY PLAY
    print("\nGALIB 8 -- the library's Play is quiet, like the Pad's")
    for theme in ("dark", "light"):
        pg = open_page(ctx, "/library", theme)
        pl = pg.evaluate("""() => { const cs = getComputedStyle(document.getElementById('btnPlay'));
          return { img: cs.backgroundImage, shadow: cs.boxShadow, bg: cs.backgroundColor, ink: cs.color,
                   card: getComputedStyle(document.querySelector('.player')).backgroundColor }; }""")
        rgb = _rgba(pl["bg"])[0]
        # NEUTRAL: grey, or the card it sits on (after v324 the player's
        # controls are the card's white, the app's card, as the editors').
        check(f"/library {theme}: Play has no accent gradient, no glow, and a neutral ground (grey, or its card's)",
              pl["img"] == "none" and pl["shadow"] == "none" and (max(rgb) - min(rgb) < 24 or pl["bg"] == pl["card"]), str(pl))
        pg.close()

    # ======================================================= THE CARD'S PILL
    print("\nGALIB 9 -- a gallery card says how it was drawn, centred on the drawing's foot, off its face")
    # The owner's pick A after v324 ("all yes"): the play button is a pill,
    # "drawn in 1 sec", on the drawing -- the drawing, not the box, which is
    # wider than it two to a row -- and the drawing's middle is the drawing's
    # again. The title is the strong ink. CENTRED ON ITS FOOT SINCE the
    # owner's pick A after v326: in the lower-left corner it ran past a tall
    # drawing's right edge, read as centred while the drawing did not, and
    # on a light page its words sat on the card.
    for dev, c_ in (("desk", ctx), ("390", phone)):
        for theme in ("light", "dark"):
            pg = open_page(c_, "/gallery", theme)
            pl = pg.evaluate("""(tag) => { const t = [...document.querySelectorAll('article.tile')].find(a => a.textContent.includes(tag));
              if (!t) return null; t.scrollIntoView({block: 'center'});
              const box = t.querySelector('[data-skribl-inline]'), play = box.querySelector('.skribl-inline-play'),
                    r = play.getBoundingClientRect(), b = box.getBoundingClientRect();
              // The drawing, letterboxed in the box by its own shape.
              const a = box.dataset.skriblW / box.dataset.skriblH, w = Math.min(b.width, b.height * a), h = w / a;
              const d = { l: b.left + (b.width - w) / 2, r: b.right - (b.width - w) / 2, b: b.bottom - (b.height - h) / 2 };
              const mid = document.elementFromPoint((d.l + d.r) / 2, b.top + b.height / 2);
              const tt = getComputedStyle(t.querySelector('.tt')), ink = getComputedStyle(t.querySelector('.tdn')).color;
              return { words: play.textContent.trim(), inL: Math.round(r.left - d.l), inR: Math.round(d.r - r.right),
                       off: Math.round(((r.left + r.right) / 2 - (d.l + d.r) / 2) * 10) / 10, inB: Math.round(d.b - r.bottom),
                       midFree: !play.contains(mid), size: tt.fontSize, weight: tt.fontWeight, strong: tt.color !== getComputedStyle(t.querySelector('.tm')).color }; }""", f"{TAG} coil")
            check(f"/gallery {dev} {theme}: the card's play says 'drawn in 1 sec', centred on the drawing's foot 8-16px up and inside its edges, the drawing's middle clear, the title 16px in the strong ink",
                  bool(pl) and pl["words"] == "drawn in 1 sec" and abs(pl["off"]) <= 1 and pl["inL"] >= 8 and pl["inR"] >= 8
                  and 8 <= pl["inB"] <= 16 and pl["midFree"]
                  and pl["size"] == "16px" and int(pl["weight"]) >= 600 and pl["strong"], str(pl))
            # ALWAYS INSIDE: a drawing narrower than the pill's words keeps the
            # time, centred, and its name still says how it was drawn. A tall,
            # phone-shaped drawing on a desk, two to a row, is that drawing.
            if dev == "desk":
                nr = pg.evaluate("""(tag) => { const t = [...document.querySelectorAll('article.tile')].find(a => a.textContent.includes(tag));
                  if (!t) return null; t.scrollIntoView({block: 'center'});
                  const box = t.querySelector('[data-skribl-inline]'), play = box.querySelector('.skribl-inline-play'),
                        r = play.getBoundingClientRect(), b = box.getBoundingClientRect();
                  const a = box.dataset.skriblW / box.dataset.skriblH, w = Math.min(b.width, b.height * a);
                  const l = b.left + (b.width - w) / 2, rr = l + w;
                  return { words: play.textContent.trim(), name: box.getAttribute('aria-label'), drawing: Math.round(w),
                           inL: Math.round(r.left - l), inR: Math.round(rr - r.right),
                           off: Math.round(((r.left + r.right) / 2 - (l + rr) / 2) * 10) / 10 }; }""", f"{TAG} reed")
                check(f"/gallery desk {theme}: on a drawing narrower than the words, the pill keeps the time, centred and inside it, and its name still says how it was drawn",
                      bool(nr) and re.fullmatch(r"\d+ sec", nr["words"] or "") is not None and abs(nr["off"]) <= 1
                      and nr["inL"] >= 8 and nr["inR"] >= 8 and "drawn in " + nr["words"] in (nr["name"] or ""), str(nr))
            pg.close()
            # THE PILL PLAYS (owner's iPhone: "When I tap the white button ...
            # I would have to push play to play. I thought that was a play
            # button."). The card's bar rose on the touch, across the pill, and
            # took the tap. A real tap or click at the pill's middle starts the
            # drawing, and the pill is never drawn under the bar.
            if theme == "light":
                pg = open_page(c_, "/gallery", theme)
                sel = pg.evaluate("""(tag) => { const t = [...document.querySelectorAll('article.tile')].find(a => a.textContent.includes(tag));
                  t.scrollIntoView({block: 'center'}); return '[data-skribl-id="' + t.dataset.id + '"]'; }""", f"{TAG} coil")
                pg.wait_for_timeout(300)
                r = pg.evaluate("(s) => { const b = document.querySelector(s + ' .skribl-inline-play').getBoundingClientRect(); return [b.left + b.width / 2, b.top + b.height / 2]; }", sel)
                loop0 = pg.evaluate("(s) => document.querySelector(s).closest('article.tile').querySelector('.skfull-card .skfull-loop').getAttribute('aria-pressed')", sel)
                if dev == "390":
                    pg.touchscreen.tap(r[0], r[1])
                else:
                    pg.mouse.move(r[0], r[1]); pg.wait_for_timeout(400); pg.mouse.click(r[0], r[1])
                pg.wait_for_timeout(700)
                st = pg.evaluate("""(s) => { const b = document.querySelector(s), t = b.closest('article.tile');
                  return { state: b._skriblInline && b._skriblInline.state().state,
                           loop: t.querySelector('.skfull-card .skfull-loop').getAttribute('aria-pressed') }; }""", sel)
                check(f"/gallery {dev}: a {'tap' if dev == '390' else 'click'} on the pill plays the drawing, and does not land on the card's bar",
                      st["state"] == "playing" and st["loop"] == loop0, f"{st}, repeat before {loop0}")
                pg.close()
                pg = open_page(c_, "/gallery", theme)
                pg.evaluate("(tag) => [...document.querySelectorAll('article.tile')].find(a => a.textContent.includes(tag)).scrollIntoView({block: 'center'})", f"{TAG} coil")
                pg.wait_for_timeout(300)
                pg.evaluate("(tag) => [...document.querySelectorAll('article.tile')].find(a => a.textContent.includes(tag)).classList.add('ctl-on')", f"{TAG} coil")
                pg.wait_for_timeout(400)
                both = pg.evaluate("""(tag) => { const t = [...document.querySelectorAll('article.tile')].find(a => a.textContent.includes(tag));
                  return [+getComputedStyle(t.querySelector('.skfull-card')).opacity, +getComputedStyle(t.querySelector('.skribl-inline-veil')).opacity]; }""", f"{TAG} coil")
                check(f"/gallery {dev}: with the card's bar up, the pill steps aside", both[0] == 1 and both[1] == 0, str(both))
                pg.close()

                # SCROLLED AWAY, IT WAITS; BACK, IT CARRIES ON (owner's iPhone
                # after #516: "It goes away even if it's playing and I scroll it
                # out of view"). It was settled back to the start off screen.
                # And a post another one stopped rests on its CARD: the canvas
                # at time zero, the blank page, was left over it ("come back
                # and blank screen").
                pg = open_page(c_, "/gallery", theme)
                pg.add_style_tag(content="body { padding-bottom: 3000px !important; }")   # room to leave
                ids = pg.evaluate("""(tags) => tags.map(tag => '[data-skribl-id="' + [...document.querySelectorAll('article.tile')].find(a => a.textContent.includes(tag)).dataset.id + '"]')""",
                                  [f"{TAG} coil", f"{TAG} wave"])
                sel, other = ids
                ST = """(s) => { const b = document.querySelector(s), r = b.getBoundingClientRect(), st = b._skriblInline.state();
                  const hit = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 3);
                  return { state: st.state, ms: Math.round(st.elapsedMs), at: hit ? hit.tagName + '.' + hit.className : null }; }"""
                pg.evaluate("(s) => document.querySelector(s).scrollIntoView({block: 'center'})", sel); pg.wait_for_timeout(300)
                pg.evaluate("(s) => { const p = document.querySelector(s)._skriblInline; p.setLoop && p.setLoop(true); p.play(); }", sel); pg.wait_for_timeout(900)
                pg.evaluate("() => scrollTo(0, 99999)"); pg.wait_for_timeout(700)
                away = pg.evaluate(ST, sel)
                pg.evaluate("(s) => document.querySelector(s).scrollIntoView({block: 'center'})", sel); pg.wait_for_timeout(700)
                back = pg.evaluate(ST, sel)
                check(f"/gallery {dev}: a playing card scrolled away waits where it was, and carries on drawing when it comes back",
                      away["state"] == "paused" and away["ms"] > 0 and back["state"] == "playing"
                      and back["ms"] >= away["ms"] and (back["at"] or "").startswith("CANVAS"), f"away {away} -> back {back}")
                pg.evaluate("(s) => document.querySelector(s)._skriblInline.play()", other); pg.wait_for_timeout(600)
                rest = pg.evaluate(ST, sel)
                check(f"/gallery {dev}: ...and stopped by another post, it rests on its drawing, not on a blank page",
                      rest["state"] == "idle" and "skribl-inline-poster" in (rest["at"] or ""), str(rest))
                # GLASS (the owner's pick D): light over a light drawing,
                # dark over a dark one, the words 7:1 on the pixels behind.
                # A MID-TONE DRAWING TAKES THE GLASS ITS WORDS READ ON (after
                # v326): by its average the green is dark, and white words on
                # the dark glass over it read 3.7:1.
                gm = pg.evaluate("""(tag) => { const t = [...document.querySelectorAll('article.tile')].find(a => a.textContent.includes(tag));
                  t.scrollIntoView({block: 'center'}); const b = t.querySelector('[data-skribl-inline]');
                  return { id: b.dataset.skriblId, dark: b.classList.contains('is-says-dark') }; }""", f"{TAG} meadow")
                pg.wait_for_timeout(300)
                gmc = glass_contrast(pg, [f'[data-skribl-id="{gm["id"]}"] .skribl-inline-play span'], 2 if dev == "390" else 1)
                check(f"/gallery {dev}: on a mid-tone drawing the pill takes the glass its words read on, 4.5:1 or more",
                      gm["dark"] is False and len(gmc) == 1 and gmc[0][1] >= 4.5, f"{gm}, {gmc}")
                for tag, dark in ((f"{TAG} coil", False), (f"{TAG} night", True)):
                    gs = pg.evaluate("""(tag) => { const t = [...document.querySelectorAll('article.tile')].find(a => a.textContent.includes(tag));
                      t.scrollIntoView({block: 'center'}); const b = t.querySelector('[data-skribl-inline]');
                      return { id: b.dataset.skriblId, dark: b.classList.contains('is-says-dark'),
                               bf: getComputedStyle(b.querySelector('.skribl-inline-play')).backdropFilter }; }""", tag)
                    pg.wait_for_timeout(300)
                    gc = glass_contrast(pg, [f'[data-skribl-id="{gs["id"]}"] .skribl-inline-play span'], 2 if dev == "390" else 1)
                    check(f"/gallery {dev}: the pill is {'dark' if dark else 'light'} glass over a {'dark' if dark else 'light'} drawing, its words 7:1 on the pixels behind",
                          gs["dark"] is dark and "blur" in (gs["bf"] or "") and len(gc) == 1 and gc[0][1] >= 7, f"{gs}, {gc}")
                # Loading, the spinner takes the arrow's place, at the pill's start.
                busy = pg.evaluate("""(s) => { const p = document.querySelector(s + ' .skribl-inline-play'); p.classList.add('is-busy');
                  const sp = getComputedStyle(p, '::after'), w = p.querySelector('span').getBoundingClientRect(), pr = p.getBoundingClientRect();
                  const r = { order: sp.order, arrow: getComputedStyle(p.querySelector('svg')).display, wordsFromLeft: Math.round(w.left - pr.left) };
                  p.classList.remove('is-busy'); return r; }""", sel)
                check(f"/gallery {dev}: while it loads, the spinner sits where the arrow was, ahead of the words",
                      busy["order"] == "-1" and busy["arrow"] == "none" and busy["wordsFromLeft"] >= 20, str(busy))
                pg.close()

    phone.close()
    ctx.close()

    # SCROLLED, NOTHING SHOWS THROUGH THE HEADER (owner, v318, a screenshot of
    # the library a little way down: the page's title read faintly through the
    # pinned glass card, and the card below peeked through the gap above it).
    # Asked of PAINTED pixels, two strips: the gap between the window's top and
    # the card, and a strip inside the card's empty middle. With the page
    # scrolled under them each must be one colour. A rect is not a paint.
    from PIL import Image as _Img
    import io as _io
    def _flat(png, box):
        im = _Img.open(_io.BytesIO(png)).convert("RGB").crop(box)
        px = list(im.getdata())
        return max(max(abs(c[i] - px[0][i]) for i in range(3)) for c in px)
    for _path in ("/library", "/gallery"):
        for _theme in ("dark", "light"):
            for _vw, _vh in ((1280, 700), (390, 700)):
                _c = b.new_context(viewport={"width": _vw, "height": _vh})
                _p = _c.new_page()
                _p.goto(f"{BASE}{_path}?theme={_theme}", wait_until="load"); _p.wait_for_timeout(700)
                # Text and a card edge where the scroll leaves them under the header.
                _p.evaluate("""() => { document.body.style.minHeight = '3000px';
                  const top = document.querySelector('.top'), m = document.createElement('div');
                  m.textContent = 'SCROLLED-UNDER '.repeat(40);
                  m.style.cssText = 'font:700 26px sans-serif;color:#d0d4dc;border:2px solid #d0d4dc;border-radius:16px;padding:8px;margin:10px 0;overflow:hidden;height:160px';
                  top.after(m); }""")
                _p.evaluate("() => window.scrollTo(0, 120)"); _p.wait_for_timeout(500)
                _r = _p.evaluate("""() => { const t = document.querySelector('.top').getBoundingClientRect();
                  const brand = document.querySelector('.top .brand, .top a, .top img').getBoundingClientRect();
                  const right = [...document.querySelectorAll('.top button, .top a')].map(e => e.getBoundingClientRect().left).filter(x => x > brand.right + 40);
                  return { top: t.top, bottom: t.bottom, l: t.left, w: t.width, mid0: brand.right + 24, mid1: (right.length ? Math.min(...right) : t.right) - 24 }; }""")
                _png = _p.screenshot()
                _gap = _flat(_png, (int(_r["l"] + 20), 0, int(_r["l"] + _r["w"] - 20), max(1, int(_r["top"]) - 1)))
                _mid = _flat(_png, (int(_r["mid0"]), int(_r["top"]) + 6, max(int(_r["mid0"]) + 2, int(_r["mid1"])), int(_r["bottom"]) - 6))
                check(f"{_path} {_theme} {_vw}: scrolled, nothing shows above the pinned header",
                      _gap <= 8, f"the gap above the card varies by {_gap}/255 (scrolled content shows through)")
                check(f"{_path} {_theme} {_vw}: scrolled, nothing shows through the header",
                      _mid <= 8, f"a strip inside the header varies by {_mid}/255 (text reads through it)")
                # ...nor BESIDE it: the ground is a band the full width (owner,
                # after v324: "I def don't like the look of the stuff showing
                # under top bar").
                _side = max(_flat(_png, (0, int(_r["top"]) + 4, max(2, int(_r["l"]) - 2), int(_r["bottom"]) - 4)),
                            _flat(_png, (min(_vw - 2, int(_r["l"] + _r["w"]) + 2), int(_r["top"]) + 4, _vw, int(_r["bottom"]) - 4)))
                check(f"{_path} {_theme} {_vw}: scrolled, nothing shows beside the header",
                      _side <= 8, f"the strips beside the header vary by {_side}/255")
                _c.close()

    # THE BAND FADES BY COLOUR ALONE (KIND TRANSITIONS, NEVER JUMPY), read on
    # every animation frame as .scrolled comes and goes, as verify_ux reads the
    # editors': the band is the header's ::before, a strip fixed to the
    # screen that keeps its size, its colour passes through in-between values,
    # and it ends at the header's foot (Safari painted the shadow bands only
    # inside the header's box).
    _BF = """(on) => new Promise(done => { const h = document.querySelector('.top'), out = [];
        h.classList.toggle('scrolled', on); let n = 0;
        const f = () => { const c = getComputedStyle(h, '::before');
          out.push([c.position, c.top, c.height, c.backgroundColor, h.getBoundingClientRect().bottom, getComputedStyle(h).clipPath, c.content]);
          if (++n < 30) requestAnimationFrame(f); else done(out); };
        requestAnimationFrame(f); })"""
    import re as _re
    for _theme in ("light", "dark"):
        _c = b.new_context(viewport={"width": 390, "height": 700})
        _p = _c.new_page()
        _p.goto(f"{BASE}/gallery?theme={_theme}", wait_until="load"); _p.wait_for_timeout(700)
        for _on, _way in ((True, "in"), (False, "out")):
            _fr = _p.evaluate(_BF, _on)
            _clip = sorted({f[5] for f in _fr} - {"none"})
            _rows = []
            for _pos, _top, _hgt, _bg, _foot, _cl, _ct in _fr:
                _m = _re.findall(r"[\d.]+", _bg)
                _al = float(_m[3]) if len(_m) > 3 else (1.0 if _m else 0.0)
                _num = lambda v: float(v[:-2]) if v.endswith("px") else float("nan")   # "auto" when there is no strip
                _t, _h = _num(_top), _num(_hgt)
                _rows.append(((_pos, _t if _t == _t else None, _h if _h == _h else None, _ct != "none"), _al, abs(_t + _h - _foot) <= 1))
            _geo = {r[0] for r in _rows}
            _mid = [r for r in _rows if 0.02 < r[1] < 0.98]
            _bare = [i for i, r in enumerate(_rows) if r[1] > 0.01 and not r[2]]
            check(f"/gallery {_theme}: the header's band is a strip fixed to the screen, fading {_way} by colour alone, ending at the header's foot",
                  len(_geo) == 1 and next(iter(_geo))[0] == "fixed" and next(iter(_geo))[3] and len(_mid) >= 3 and not _bare and not _clip,
                  f"strip {sorted(_geo)[:3]}, {len(_mid)} in-between frames, frames off the foot {_bare[:5]}, clip {_clip}")
        _c.close()
    b.close()

passed = sum(1 for ok, _ in results if ok)
bad = [name for ok, name in results if not ok]
print("\n" + "=" * 62)
print(f"{passed}/{len(results)} passed" + ("" if not bad else "\nFAILURES:\n  - " + "\n  - ".join(bad)))
sys.exit(1 if bad else 0)
