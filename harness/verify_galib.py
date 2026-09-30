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
  MENU            glass (a real backdrop-filter, the chosen fill), a popover
                  under the ••• on a desktop, a full-bleed sheet on a phone.
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

    # ========================================================= DELETE FLOWS
    print("\nGALIB 2 -- the draft bin asks without moving; a posted Delete holds its arm")
    pg = open_page(ctx, "/library#drafts")
    pg.wait_for_timeout(900)
    BIN = """() => { const d = document.querySelector('#draftsList .draft-del');
      const row = d.closest('.draft-row'), m = row.querySelector('.draft-meta'), r = d.getBoundingClientRect();
      return { w: r.width, h: r.height, x: r.left, armed: d.classList.contains('armed'),
               meta: m.textContent, live: m.getAttribute('aria-live'), label: d.getAttribute('aria-label'),
               ink: getComputedStyle(d).color }; }"""
    b0 = pg.evaluate(BIN)
    pg.click("#draftsList .draft-del >> nth=0")
    pg.wait_for_timeout(250)
    b1 = pg.evaluate(BIN)
    check("library: the armed bin keeps its 44px box and its place",
          b1["armed"] and b0["w"] == b1["w"] == 44 and b0["h"] == b1["h"] == 44 and b0["x"] == b1["x"],
          f"{b0} -> {b1}")
    check("library: the question is on the meta line, which speaks, and the bin's ink turns",
          b1["meta"] != b0["meta"] and "again" in b1["meta"] and b1["live"] == "polite"
          and b1["label"].startswith("Tap again") and b1["ink"] != b0["ink"], f"{b0} -> {b1}")
    pg.keyboard.press("Tab"); pg.wait_for_timeout(200)
    check("library: focus leaving the bin disarms it", not pg.evaluate(BIN)["armed"])
    pg.click("#draftsList .draft-del >> nth=0"); pg.wait_for_timeout(200)
    pg.mouse.click(5, 400); pg.wait_for_timeout(200)
    b2 = pg.evaluate(BIN)
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
    pg.mouse.click(5, 400); pg.wait_for_timeout(200)
    check("library: ...and a tap elsewhere disarms it",
          pg.evaluate("() => document.querySelector('.posted-delete').dataset.armed") == "", "")
    pg.close()

    # The editors' saved-drafts sheet is the same row.
    pg = open_page(ctx, "/skribl-pad")
    pg.evaluate("() => SkriblSavedDrafts.open()")
    pg.wait_for_timeout(900)
    SB = """() => { const d = document.querySelector('#savedDraftsSheet .sdrafts-del'); const r = d.getBoundingClientRect();
      const m = d.closest('.sdrafts-row').querySelector('.sdrafts-meta');
      return { w: r.width, h: r.height, x: r.left, armed: d.classList.contains('armed'), meta: m.textContent,
               live: m.getAttribute('aria-live') }; }"""
    s0 = pg.evaluate(SB)
    pg.click("#savedDraftsSheet .sdrafts-del >> nth=0"); pg.wait_for_timeout(250)
    s1 = pg.evaluate(SB)
    check("the Pad's drafts sheet: the armed bin keeps its box, and its meta line asks",
          s1["armed"] and s0["w"] == s1["w"] == 44 and s0["x"] == s1["x"] and "again" in s1["meta"]
          and s1["live"] == "polite", f"{s0} -> {s1}")
    pg.keyboard.press("Tab"); pg.wait_for_timeout(200)
    check("the Pad's drafts sheet: focus leaving the bin disarms it", not pg.evaluate(SB)["armed"])
    pg.close()

    # ================================================================ MENU
    print("\nGALIB 3 -- the page menu is the Pad's glass: a popover on a desktop, a sheet on a phone")
    MENU = """() => { const s = document.getElementById('pageMenu'), b = document.getElementById('pageMenuBtn');
      const sr = s.getBoundingClientRect(), br = b.getBoundingClientRect(), cs = getComputedStyle(s);
      const scrim = getComputedStyle(document.getElementById('pageMenuOverlay'), '::before');
      return { right: sr.right - br.right, gap: sr.top - br.bottom, w: sr.width, left: sr.left,
               bottom: innerHeight - sr.bottom, vw: innerWidth, bf: cs.backdropFilter, bg: cs.backgroundColor,
               shadow: cs.boxShadow, weight: getComputedStyle(s.querySelector('.pm-item')).fontWeight,
               scrim: scrim.backgroundColor, scrimBf: scrim.backdropFilter }; }"""
    for path in ("/gallery", "/library"):
        for theme, alpha in (("dark", 0.78), ("light", 0.9)):
            pg = open_page(ctx, path, theme)
            pg.click("#pageMenuBtn"); pg.wait_for_timeout(500)
            m = pg.evaluate(MENU)
            a = _rgba(m["bg"])[1]
            check(f"{path} {theme}: the menu is glass -- blur(14px), a {alpha} fill, the rim, 600 rows, a blurred .4 dim",
                  "blur(14px)" in m["bf"] and abs(a - alpha) < 0.011 and "0px 0px 0px 1px" in m["shadow"]
                  and m["weight"] == "600" and "blur(2px)" in m["scrimBf"] and abs(_rgba(m["scrim"])[1] - 0.4) < 0.01, str(m))
            if theme == "dark":
                check(f"{path}: on a desktop it is a 300px popover under the ••• -- right edges flush, 8px below",
                      abs(m["right"]) <= 1 and abs(m["gap"] - 8) <= 1 and abs(m["w"] - 300) <= 1, str(m))
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
    print("\nGALIB 4 -- one header card and one lockup on both pages")
    HEAD = """() => { const t = document.querySelector('.top'), cs = getComputedStyle(t);
      const tag = getComputedStyle(document.querySelector('.brand .tag'));
      const mk = getComputedStyle(document.querySelector('#galleryMake, #libMake'));
      return { pos: cs.position, bf: cs.backdropFilter, shadow: cs.boxShadow, radius: cs.borderTopLeftRadius,
               top: t.getBoundingClientRect().top, over: document.documentElement.scrollWidth - innerWidth,
               clip: t.scrollWidth - t.clientWidth, bg: cs.backgroundColor,
               lockup: [document.querySelector('.brand .brand-mark').getBoundingClientRect().height,
                        tag.fontWeight, tag.fontSize, tag.letterSpacing, mk.fontWeight, mk.fontSize] }; }"""
    lockups = {}
    for path in ("/gallery", "/library"):
        pg = open_page(ctx, path)
        pg.evaluate("window.scrollTo(0, 600)"); pg.wait_for_timeout(300)
        h = pg.evaluate(HEAD)
        lockups[path] = h["lockup"]
        check(f"{path}: the header is a glass card, sticky, still 12px from the top once scrolled",
              h["pos"] == "sticky" and "blur(14px)" in h["bf"] and "0px 0px 0px 1px" in h["shadow"]
              and h["radius"] == "16px" and abs(h["top"] - 12) <= 1, str(h))
        pg.close()
        pg = open_page(phone, path)
        pg.evaluate("window.scrollTo(0, 600)"); pg.wait_for_timeout(300)
        h = pg.evaluate(HEAD)
        check(f"{path} at 390: the card is solid and pinned, and nothing overflows",
              h["pos"] == "sticky" and h["bf"] == "none" and _rgba(h["bg"])[1] == 1.0
              and abs(h["top"] - 6) <= 1 and h["over"] <= 0 and h["clip"] <= 0, str(h))
        pg.close()
    check("ONE lockup: mark height, word weight/size/tracking and Make one's weight/size agree on both pages",
          lockups["/gallery"] == lockups["/library"]
          and lockups["/gallery"][0] == 24 and lockups["/gallery"][1:] == ["700", "11px", "1.76px", "600", "13px"],
          str(lockups))

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
    MENU_TEXT = ['.pm-text', '.pm-sub', '.pm-label', '.pm-version', '.pm-seg > button']
    REPORT_TEXT = ['#reportTitle', '.sheet-card > p', '.reasons legend', '.reason', 'label > .sheet-status',
                   '.sheet-status > span', '.sheet-actions .btn']
    for form, kw in (("desktop", DESK), ("phone", PHONE)):
        dsf = kw.get("device_scale_factor", 1)
        for theme in ("light", "dark"):
            c2 = b.new_context(storage_state=state, color_scheme=theme, **kw)
            for path in ("/gallery", "/library"):
                pg = open_page(c2, path, theme)
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
    print("\nGALIB 7 -- at 390, no dead tap between a row's actions")
    pg = open_page(phone, "/library")
    pg.wait_for_timeout(600)
    gaps = pg.evaluate("""() => { const out = [];
      for (const strip of document.querySelectorAll('.posted-actions')) {
        const bs = [...strip.querySelectorAll('button')].filter(b => b.getClientRects().length);
        if (bs.length < 2) continue;
        bs[0].scrollIntoView({ block: 'center' });
        for (let i = 0; i + 1 < bs.length; i++) {
          const a = bs[i].getBoundingClientRect(), c = bs[i + 1].getBoundingClientRect();
          if (Math.abs(a.top - c.top) > 2) continue;           // wrapped onto the next line
          const y = a.top + a.height / 2;
          for (let x = Math.ceil(a.right) - 1; x <= Math.floor(c.left) + 1; x++) {
            const hit = document.elementFromPoint(x, y);
            if (!hit || !hit.closest || !hit.closest('.posted-actions button')) out.push(Math.round(x) + ':' + (hit ? (hit.className.baseVal !== undefined ? hit.tagName : hit.className) : 'none'));
          }
        }
      }
      return { dead: out.length, sample: out.slice(0, 6),
               strips: document.querySelectorAll('.posted-actions').length }; }""")
    check("library at 390: every point between two row actions lands on one of them",
          gaps["strips"] >= 3 and gaps["dead"] == 0, str(gaps))
    pg.close()

    # ========================================================= LIBRARY PLAY
    print("\nGALIB 8 -- the library's Play is quiet, like the Pad's")
    for theme in ("dark", "light"):
        pg = open_page(ctx, "/library", theme)
        pl = pg.evaluate("""() => { const cs = getComputedStyle(document.getElementById('btnPlay'));
          return { img: cs.backgroundImage, shadow: cs.boxShadow, bg: cs.backgroundColor, ink: cs.color }; }""")
        rgb = _rgba(pl["bg"])[0]
        check(f"/library {theme}: Play has no accent gradient, no glow, and a neutral ground",
              pl["img"] == "none" and pl["shadow"] == "none" and max(rgb) - min(rgb) < 24, str(pl))
        pg.close()

    phone.close()
    ctx.close()
    b.close()

passed = sum(1 for ok, _ in results if ok)
bad = [name for ok, name in results if not ok]
print("\n" + "=" * 62)
print(f"{passed}/{len(results)} passed" + ("" if not bad else "\nFAILURES:\n  - " + "\n  - ".join(bad)))
sys.exit(1 if bad else 0)
