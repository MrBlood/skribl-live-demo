"""The one pill: every pick-one control wears the same sliding tint, and it shows.

THE DECISION. The owner chose one pill for every pick-one control in the
product ("a on the pill"): a 12px track with a 3px inset, a 9px pill that
slides, a soft tint under the selected option, one label weight. It replaced
five shapes that had grown one per family -- a 999px capsule round a 9px pill
on the GIF background, a solid slab with white words on Flip's tool tray, an
underline on the library's tabs, monospace chips, and the dock's own.

WHAT THIS PINS, per (route, control) -- a shared id on two pages is two
controls, and each is measured where it lives:

  1. ONE PILL. Each track holds exactly one pill element, it is placed
     (data-pill), and it covers the selected option to half a pixel. The
     pills were placed from integer offsets on fractional flex options and
     overhung by a whole pixel at phone widths; the Pad's draw drawer carried
     two pills, one stuck at opacity 0.
  2. THE SHAPE. Concentric: the track's corner is the pill's plus the inset
     the pill sits at. Editor and page tracks are 12 / 3 / 9; the dock is the
     one pill at the dock's scale and keeps only the rule. The fill is the
     tint token, no shadow; every label is 600, selected or not; the selected
     label is the selected-ink token.
  3. CONTRAST, PAINTED. Every option's label against what is ACTUALLY behind
     it, read from pixels (the tint composited over the track over whatever
     glass is under that) -- at least 4.5:1, both themes. The light theme's
     selected ink measured 4.37:1 on the tint before the token moved.
  4. THE FALLBACK. Take the pill away (no data-pill) and the selected option
     still paints the tint itself: a track the script never reaches still
     shows its choice.
  5. FORCED COLOURS. Backgrounds are replaced there, so the tint says
     nothing; the selected option of every control must carry an edge an
     unselected one does not.
  6. The shape picker's track hugs its options when a knob widens the pop.
  7. The selection defects the pick-one census found, each driven through
     the path a person takes (or the restore a draft takes).

Checked red on the tree before the one pill, and per component by mutation;
DECISIONS.md records which mutation each section was shown red on.
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

try:
    from playwright.sync_api import sync_playwright
    from PIL import Image
except ImportError:
    print("SKIP: playwright or Pillow is not installed")
    sys.exit(0)

results = []
check = make_check(results)

# Calibration only: narrow a run to some sections, themes or forms while a
# mutation is being shown red. A normal run sets none of these and runs all.
_ONLY = set(filter(None, os.environ.get("ONEPILL_SECTIONS", "").split(",")))
THEMES = tuple(filter(None, os.environ.get("ONEPILL_THEMES", "dark,light").split(",")))
FORMS = tuple(filter(None, os.environ.get("ONEPILL_FORMS", "desk,phone").split(",")))


def want(section):
    return not _ONLY or section in _ONLY

# 1x1 PNG, for a restored draft that carries a photo.
PNG = ("data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlE"
       "QVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==")
_buf = io.BytesIO()
_w = wave.open(_buf, "wb"); _w.setnchannels(1); _w.setsampwidth(2); _w.setframerate(8000)
_w.writeframes(b"".join(struct.pack("<h", int(3000 * math.sin(i * 0.1))) for i in range(8000 * 6)))
_w.close()
AUD = _buf.getvalue()

# Every track visible AND painted right now. "Painted" is asked of the page
# (elementFromPoint at the track's centre lands inside it), not of a rect:
# a track in a closed drawer keeps its geometry.
CENSUS = r"""() => {
  const TR = '.seg, .smooth-seg, .gif-seg, .photo-fit-group, .seg-track, #toolGroup';
  const PILLS = ':scope > .seg-slider, :scope > .photo-fit-slider, :scope > .tool-slider';
  const probe = (host, prop) => { const d = document.createElement('span');
    d.style.cssText = 'position:absolute;visibility:hidden;' + prop; host.appendChild(d);
    const cs = getComputedStyle(d); const v = { bg: cs.backgroundColor, ink: cs.color }; d.remove(); return v; };
  const out = [];
  for (const g of document.querySelectorAll(TR)) {
    const r = g.getBoundingClientRect();
    if (r.width < 8 || r.height < 8) continue;
    const cx = r.left + r.width / 2, cy = r.top + r.height / 2;
    if (cx < 0 || cy < 0 || cx > innerWidth || cy > innerHeight) continue;
    const hit = document.elementFromPoint(cx, cy);
    if (!hit || !(g === hit || g.contains(hit))) continue;
    const pills = g.querySelectorAll(PILLS);
    const btns = [...g.children].filter(b => b.tagName === 'BUTTON' && b.getBoundingClientRect().width > 0);
    const sel = btns.find(b => b.classList.contains('on') || b.classList.contains('active')
      || b.getAttribute('aria-selected') === 'true'
      || (g.matches('.seg-track') && b.getAttribute('aria-pressed') === 'true'));
    const p = pills[0];
    const pr = p ? p.getBoundingClientRect() : null, sr = sel ? sel.getBoundingClientRect() : null;
    const tok = probe(g.parentNode, 'background:var(--seg-on-fill);color:var(--seg-on-ink)');
    const key = g.id || ((g.parentNode.closest('[id]') || {}).id || '?') + ' .' + g.className.trim().split(/\s+/).join('.');
    out.push({
      key, pills: pills.length, placed: g.hasAttribute('data-pill'),
      dx: pr && sr ? +(pr.left - sr.left).toFixed(2) : null,
      dw: pr && sr ? +(pr.width - sr.width).toFixed(2) : null,
      dy: pr && sr ? +Math.max(Math.abs(pr.top - (r.top + g.clientTop + parseFloat(getComputedStyle(g).paddingTop))),
                               Math.abs(pr.bottom - (r.bottom - g.clientTop - parseFloat(getComputedStyle(g).paddingBottom)))).toFixed(2) : null,
      trackR: parseFloat(getComputedStyle(g).borderTopLeftRadius),
      inset: pr ? +(pr.top - r.top - g.clientTop).toFixed(2) : null,
      pillR: p ? parseFloat(getComputedStyle(p).borderTopLeftRadius) : null,
      pillBg: p ? getComputedStyle(p).backgroundColor : null,
      pillShadow: p ? getComputedStyle(p).boxShadow : null,
      pillOpacity: p ? getComputedStyle(p).opacity : null,
      tokBg: tok.bg, tokInk: tok.ink,
      dock: g.id === 'toolGroup',
      selInk: sel ? getComputedStyle(sel).color : null,
      hasSel: !!sel,
      btns: btns.map(b => { const bb = b.getBoundingClientRect(); const cs = getComputedStyle(b);
        return { t: (b.textContent || '').trim().slice(0, 16), w: cs.fontWeight, ink: cs.color,
                 sel: b === sel, x: bb.left, y: bb.top, width: bb.width, height: bb.height,
                 text: !!(b.textContent || '').trim() }; }),
    });
  }
  return out;
}"""

RGB = r"""(s) => { const d = document.createElement('i'); d.style.color = s; document.body.appendChild(d);
  const v = getComputedStyle(d).color; d.remove(); return v; }"""


def parse(c):
    n = [float(v) for v in c[c.index("(") + 1:c.index(")")].replace("/", ",").split(",") if v.strip()]
    return (n + [1.0])[:4] if len(n) == 3 else n[:4]


def lum(rgb):
    def f(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(rgb[0]) + 0.7152 * f(rgb[1]) + 0.0722 * f(rgb[2])


def ratio(a, b):
    la, lb = lum(a), lum(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def painted_bg(page, b):
    """The colour actually painted behind a label: the mode of the option's
    pixels, away from its corners (the label's ink is the minority)."""
    x, y, w, h = b["x"] + 3, b["y"] + 3, b["width"] - 6, b["height"] - 6
    if w < 4 or h < 4:
        return None
    img = Image.open(io.BytesIO(page.screenshot(clip={"x": x, "y": y, "width": w, "height": h}))).convert("RGB")
    cols = img.getcolors(1 << 20)
    return max(cols)[1] if cols else None


seen = set()


def audit(page, route, theme, form, state):
    groups = page.evaluate(CENSUS)
    for g in groups:
        ident = (route, g["key"])
        tag = f"{route} {g['key']} [{theme} {form}{', ' + state if state else ''}]"
        first = ident not in seen
        seen.add(ident)
        check(f"ONE PILL: {tag} holds exactly one pill", g["pills"] == 1, f"{g['pills']} pill elements")
        if not g["hasSel"]:
            # a data-role="focus" group has a free state: nothing chosen, no pill.
            check(f"ONE PILL: {tag} with nothing chosen shows no pill",
                  not g["placed"] or g["pillOpacity"] == "0", str(g["placed"]))
            continue
        check(f"PLACED: {tag} has its pill placed and covering the selected option (to a quarter pixel: whole-pixel placement is off by a half)",
              g["placed"] and g["dx"] is not None and abs(g["dx"]) <= 0.25 and abs(g["dw"]) <= 0.25 and g["dy"] <= 0.25,
              f"placed={g['placed']} dx={g['dx']} dw={g['dw']} dy={g['dy']}")
        check(f"SHAPE: {tag} is concentric (track corner = pill corner + inset)",
              g["inset"] is not None and abs(g["trackR"] - g["inset"] - g["pillR"]) <= 0.5,
              f"track {g['trackR']} inset {g['inset']} pill {g['pillR']}")
        if not g["dock"]:
            check(f"SHAPE: {tag} is 12 / 3 / 9", (g["trackR"], g["inset"], g["pillR"]) == (12, 3, 9),
                  f"{g['trackR']} / {g['inset']} / {g['pillR']}")
            weights = sorted({b["w"] for b in g["btns"] if b["text"]})
            check(f"SHAPE: {tag} sets every label at 600, selected or not", weights in ([], ["600"]), str(weights))
        check(f"SHAPE: {tag} fills the pill with the tint token and no shadow",
              g["pillBg"] == g["tokBg"] and g["pillShadow"] == "none", f"{g['pillBg']} vs {g['tokBg']}; {g['pillShadow']}")
        check(f"SHAPE: {tag} inks the selected option with the selected-ink token",
              g["selInk"] == g["tokInk"], f"{g['selInk']} vs {g['tokInk']}")
        worst = None
        for b in g["btns"]:
            bg = painted_bg(page, b)
            if bg is None:
                continue
            ink = parse(b["ink"])
            a = ink[3]
            fg = tuple(ink[i] * a + bg[i] * (1 - a) for i in range(3))
            r = ratio(fg, bg)
            if worst is None or r < worst[0]:
                worst = (round(r, 2), b["t"] or "(icon)", "selected" if b["sel"] else "unselected", bg)
        if worst:
            check(f"CONTRAST: {tag} every label clears 4.5:1 on what is painted behind it",
                  worst[0] >= 4.5, f"worst {worst}")


with sync_playwright() as p:
    browser = p.chromium.launch()

    def ctx_for(theme, form, forced=False):
        vp, dsf = ({"width": 1400, "height": 900}, 1) if form == "desk" else ({"width": 390, "height": 844}, 1)
        c = browser.new_context(viewport=vp, device_scale_factor=dsf, color_scheme=theme,
                                has_touch=form == "phone", is_mobile=form == "phone",
                                forced_colors="active" if forced else "none")
        c.add_init_script(f"try{{localStorage.setItem('skribl_theme_v1','{theme}')}}catch(e){{}}")
        return c

    def settle(q, ms=700):
        q.wait_for_timeout(ms)

    def draw(q, canvas):
        bb = q.query_selector(canvas).bounding_box()
        q.mouse.move(bb["x"] + 40, bb["y"] + 60); q.mouse.down()
        for i in range(12):
            q.mouse.move(bb["x"] + 40 + i * 8, bb["y"] + 60 + i * 3)
        q.mouse.up(); settle(q, 400)

    def menu_rows(q):
        # A phone's menu is a sheet taller than the screen: each row is
        # measured where a thumb would scroll it to.
        for sid in ("themeSeg", "hintSeg", "canvasSeg"):
            q.evaluate("(i) => document.getElementById(i).scrollIntoView({block: 'center'})", sid)
            settle(q, 450)
            yield "menu"

    def editor_states(q, ed):
        """Yield (state name) after opening each place a pill lives."""
        phone = q.viewport_size["width"] < 641
        yield "dock"
        browsing.pad_drawer(q, "draw")
        if phone and q.is_visible("#drawerDetentMore"):
            q.click("#drawerDetentMore"); settle(q, 400)
        q.click("#brushSeg [data-brush='marker']"); settle(q)
        yield "draw drawer"
        q.click("#brushSeg [data-brush='pen']")
        browsing.pad_drawer_close(q)
        if ed == "pad":
            q.click("#shapeToolBtn")
        else:
            q.evaluate("() => shelfSetTool('shape')")
        q.wait_for_selector("#shapePop:not([hidden])", timeout=3000)
        q.click("#shapeSeg [data-shape='poly']"); settle(q)
        yield "shape picker"
        q.click("#shapeSeg [data-shape='line']"); settle(q, 200)
        q.evaluate("() => { document.getElementById('shapePop').hidden = true; }")
        if ed == "pad":
            q.click("#penToolBtn"); settle(q, 300); browsing.pad_drawer_close(q)
        else:
            q.evaluate("() => setTool('pen')")
        q.click("#tuneBtn"); q.wait_for_selector("#tuneShell.open", timeout=3000)
        if q.get_attribute("#gridBtn", "aria-checked") != "true":
            q.click("#gridBtn")
        if ed == "flip" and q.get_attribute("#onion", "aria-checked") != "true":
            q.click("#onion")
        settle(q)
        yield "tune"
        q.click("#tuneBtn"); settle(q, 500)
        browsing.pad_drawer(q, "photo")
        q.set_input_files("#photoInput" if ed == "pad" else "#imageInput",
                          {"name": "p.png", "mimeType": "image/png",
                           "buffer": __import__("base64").b64decode(PNG.split(",", 1)[1])})
        q.wait_for_function("() => document.getElementById('photoUploadBtn').classList.contains('loaded')", timeout=20000)
        q.click(".photo-fit-group .photo-fit-btn:nth-of-type(2)"); settle(q)
        yield "photo drawer"
        browsing.pad_drawer(q, "music")
        q.set_input_files("#musicInput", {"name": "t.wav", "mimeType": "audio/wav", "buffer": AUD})
        q.wait_for_function("() => document.getElementById('musicUploadBtn').classList.contains('loaded')", timeout=20000)
        settle(q, 500)
        if q.get_attribute("#fineTuneToggle", "aria-expanded") != "true":
            q.click("#fineTuneToggle")
        settle(q)
        q.evaluate("() => { const b = document.querySelector('.zoom-mag-bar'); if (b) b.scrollIntoView({block: 'center'}); }")
        settle(q, 300)
        yield "music drawer"
        browsing.pad_drawer_close(q)
        if ed == "flip":
            q.click("#toolMoreBtn"); q.wait_for_selector("#toolTray:not([hidden])", timeout=3000); settle(q)
            yield "tray"
            q.evaluate("() => _flipDrawerCtl.open(null)"); settle(q, 400)
            q.evaluate("() => setTool('artmove')"); settle(q)
            yield "move bar"
            q.evaluate("() => setTool('pen')"); settle(q, 300)
            q.click("#moreBtn"); settle(q)
            yield from menu_rows(q)
            q.keyboard.press("Escape"); settle(q, 500)
            draw(q, "#pad")
            q.click("#addcopy"); settle(q, 400)   # a GIF needs two pages; its Background shows then
            q.click("#moreBtn"); settle(q)
            q.click("#miExport"); settle(q, 900)
            yield "export"
        else:
            q.click("#menuBtn"); settle(q)
            yield from menu_rows(q)
            q.keyboard.press("Escape"); settle(q, 500)
            # The GIF background shows once there is a drawing to export.
            draw(q, "#canvas")
            q.evaluate("() => { document.getElementById('menuBtn').click(); }"); settle(q)
            q.click("#exportItem"); settle(q, 900)
            yield "export"

    def page_states(q, name):
        yield "page"
        q.click("#pageMenuBtn"); settle(q)
        yield "page menu"

    # ---------------------------------------------------------------- 1-3
    if want("census"):
        print("\nONE PILL — one placed pill, the one shape, contrast painted (both themes, desk and phone)")
        for theme in THEMES:
            for form in FORMS:
                for route in ("/skribl-pad", "/flip", "/gallery", "/library"):
                    c = ctx_for(theme, form)
                    q = c.new_page()
                    if route in ("/skribl-pad", "/flip"):
                        browsing.goto(q, BASE, route)
                        q.evaluate("() => window.SkriblHints && window.SkriblHints.hide && window.SkriblHints.hide()")
                        states = editor_states(q, "pad" if route == "/skribl-pad" else "flip")
                    else:
                        q.goto(BASE + route, wait_until="load")
                        states = page_states(q, route)
                    settle(q)
                    try:
                        for st in states:
                            audit(q, route, theme, form, st)
                    except Exception as e:
                        check(f"ONE PILL: {route} [{theme} {form}] could be driven through every state", False, repr(e)[:300])
                    c.close()
        must = {("/skribl-pad", k) for k in ("toolGroup", "paintTargetSeg", "smoothSeg", "brushSeg", "pressureSeg",
                                              "eraserSeg", "shapeSeg", "gridDensitySeg", "mirrorSeg", "pauseSeg",
                                              "speedSeg", "photoFitGroup", "themeSeg", "hintSeg", "canvasSeg")}
        must |= {("/flip", k) for k in ("toolGroup", "paintTargetSeg", "smoothSeg", "brushSeg", "pressureSeg",
                                         "eraserSeg", "shapeSeg", "fps", "gridDensitySeg", "mirrorSeg",
                                         "smearWeightSeg", "onionDepthSeg", "photoFitGroup", "themeSeg", "hintSeg",
                                         "canvasSeg", "mbScope", "exportSizeSeg", "exportLoopsSeg")}
        missing = sorted(m for m in must if m not in seen)
        check("ONE PILL: the census reached every control it names (a control not measured is not passing)",
              not missing, f"not reached: {missing}; reached {len(seen)}")
        for route, extra in (("/skribl-pad", ("zoom-seg", "gif-seg")), ("/flip", ("zoom-seg", "gif-seg"))):
            check(f"ONE PILL: {route}'s script-built and sheet-borne tracks were measured: {', '.join(extra)}",
                  all(any(k[0] == route and e in k[1] for k in seen) for e in extra),
                  str(sorted(k[1] for k in seen if k[0] == route)))
        check("ONE PILL: the gallery's New / Hot, the library's tabs and filter, and both page menus were measured",
              sum(1 for k in seen if k[0] in ("/gallery", "/library")) >= 5,
              str(sorted(k for k in seen if k[0] in ("/gallery", "/library"))))

    # ---------------------------------------------------------------- tray tile
    if want("tray"):
        print("\nTRAY — Flip's selected tool tile is the tint, not a slab")
        for theme in THEMES:
            c = ctx_for(theme, "desk"); q = c.new_page()
            browsing.goto(q, BASE, "/flip"); settle(q)
            q.click("#toolMoreBtn"); q.wait_for_selector("#toolTray:not([hidden])", timeout=3000); settle(q)
            t = q.evaluate("""() => { const b = document.querySelector('#toolTray .tool-tray-btn.active');
              const d = document.createElement('span'); d.style.cssText = 'background:var(--seg-on-fill);color:var(--seg-on-ink)';
              document.body.appendChild(d); const tk = getComputedStyle(d); const v = { bg: tk.backgroundColor, ink: tk.color }; d.remove();
              if (!b) return null; const cs = getComputedStyle(b); const r = b.getBoundingClientRect();
              return { bg: cs.backgroundColor, ink: cs.color, r: cs.borderTopLeftRadius, tok: v,
                       box: { x: r.left, y: r.top, width: r.width, height: r.height } }; }""")
            check(f"TRAY [{theme}]: the selected tile wears the tint, the selected ink and a 9px corner",
                  t and t["bg"] == t["tok"]["bg"] and t["ink"] == t["tok"]["ink"] and t["r"] == "9px", str(t))
            if t:
                bg = painted_bg(q, t["box"]); fg = parse(t["ink"])
                r = ratio(fg[:3], bg) if bg else 0
                check(f"TRAY [{theme}]: the selected tile's label clears 4.5:1 on what is painted", r >= 4.5, f"{r:.2f} on {bg}")
            c.close()

    # ---------------------------------------------------------------- 4
    if want("fallback"):
        print("\nFALLBACK — with no pill placed, the selected option paints the tint itself")
        for route in ("/skribl-pad", "/flip", "/gallery", "/library"):
            c = ctx_for("dark", "desk"); q = c.new_page()
            if route in ("/skribl-pad", "/flip"):
                browsing.goto(q, BASE, route)
                q.click("#tuneBtn"); q.wait_for_selector("#tuneShell.open", timeout=3000)
            else:
                q.goto(BASE + route, wait_until="load")
            settle(q)
            fb = q.evaluate("""() => { const out = [];
              const d = document.createElement('span'); d.style.cssText = 'background:var(--seg-on-fill)';
              document.body.appendChild(d); const tint = getComputedStyle(d).backgroundColor; d.remove();
              for (const g of document.querySelectorAll('[data-pill]')) {
                const r = g.getBoundingClientRect(); if (!r.width) continue;
                const sel = g.querySelector(':scope > button.on, :scope > button.active, :scope > .tool-btn.active, :scope > button[aria-selected="true"], :scope > button[aria-pressed="true"]');
                if (!sel) continue;
                const before = getComputedStyle(sel).backgroundColor;
                const pill = g.querySelector(':scope > .seg-slider, :scope > .photo-fit-slider, :scope > .tool-slider');
                // Read the settled state, not the first frame of the fade.
                if (pill) pill.style.transition = 'none';
                g.removeAttribute('data-pill');
                out.push({ key: g.id || g.className.split(' ')[0], before, after: getComputedStyle(sel).backgroundColor,
                           pillOpacity: pill ? getComputedStyle(pill).opacity : null, tint });
                if (pill) pill.style.transition = '';
                if (window.SkriblSegSlider) window.SkriblSegSlider.place(g);
              } return out; }""")
            for f in fb:
                check(f"FALLBACK: {route} {f['key']} — unplaced, the selected option is the tint and the pill is not painted",
                      f["after"] == f["tint"] and f["pillOpacity"] == "0", str(f))
                check(f"FALLBACK: {route} {f['key']} — placed, the option itself is clear (no doubled tint)",
                      f["before"] in ("rgba(0, 0, 0, 0)", "transparent"), f["before"])
            check(f"FALLBACK: {route} had placed pills to take away", len(fb) >= (1 if route == "/gallery" else 2), str(len(fb)))
            c.close()

    # ---------------------------------------------------------------- 5
    if want("forced"):
        print("\nFORCED COLOURS — the selected option carries an edge the others do not")
        EDGE = r"""() => { const TR = '.seg, .smooth-seg, .gif-seg, .photo-fit-group, .seg-track, #toolGroup, #toolTray';
          const e = b => { const c = getComputedStyle(b); return (c.outlineStyle !== 'none' ? parseFloat(c.outlineWidth) : 0); };
          const out = [];
          for (const g of document.querySelectorAll(TR)) {
            const kids = [...g.querySelectorAll(':scope > button, :scope .tool-tray-btn')].filter(b => b.getBoundingClientRect().width > 0);
            const sel = kids.find(b => b.classList.contains('on') || b.classList.contains('active') || b.getAttribute('aria-selected') === 'true' || (g.matches('.seg-track') && b.getAttribute('aria-pressed') === 'true'));
            const off = kids.find(b => b !== sel);
            if (!sel || !off) continue;
            const cs = getComputedStyle(sel);
            out.push({ key: g.id || g.className.split(' ')[0], on: e(sel), off: e(off), col: cs.outlineColor });
          } return out; }"""
        for route in ("/skribl-pad", "/flip", "/gallery", "/library"):
            c = ctx_for("dark", "desk", forced=True); q = c.new_page()
            if route in ("/skribl-pad", "/flip"):
                browsing.goto(q, BASE, route); settle(q)
                q.click("#tuneBtn"); q.wait_for_selector("#tuneShell.open", timeout=3000); settle(q, 400)
                rows = q.evaluate(EDGE)
                q.click("#tuneBtn"); settle(q, 400)
                browsing.pad_drawer(q, "draw"); settle(q, 400)
                rows += q.evaluate(EDGE)
                browsing.pad_drawer_close(q)
                if route == "/flip":
                    q.click("#toolMoreBtn"); q.wait_for_selector("#toolTray:not([hidden])", timeout=3000); settle(q, 400)
                    rows += q.evaluate(EDGE)
            else:
                q.goto(BASE + route, wait_until="load"); settle(q)
                rows = q.evaluate(EDGE)
                q.click("#pageMenuBtn"); settle(q)
                rows += q.evaluate(EDGE)
            keys = set()
            for r in rows:
                if (r["key"]) in keys:
                    continue
                keys.add(r["key"])
                check(f"FORCED: {route} {r['key']} — the selected option's edge is heavier than an unselected one's",
                      r["on"] >= 2 and r["on"] > r["off"], str(r))
            need = {"toolGroup", "smoothSeg", "brushSeg", "mirrorSeg"} if route != "/gallery" and route != "/library" else set()
            if route == "/flip":
                need |= {"toolTray", "fps"}
            check(f"FORCED: {route} measured the controls it must (and at least two)",
                  need <= keys and len(keys) >= 2, f"measured {sorted(keys)}")
            c.close()

    # ---------------------------------------------------------------- 6
    if want("shape"):
        print("\nSHAPE PICKER — the track hugs its options when a knob widens the pop")
        for route, ed in (("/skribl-pad", "pad"), ("/flip", "flip")):
            c = ctx_for("dark", "desk"); q = c.new_page()
            browsing.goto(q, BASE, route); settle(q)
            if ed == "pad":
                q.click("#shapeToolBtn")
            else:
                q.evaluate("() => shelfSetTool('shape')")
            q.wait_for_selector("#shapePop:not([hidden])", timeout=3000)
            for kind in ("line", "rect", "poly"):
                q.click(f"#shapeSeg [data-shape='{kind}']"); settle(q, 200)
                q.evaluate("() => { document.getElementById('shapePop').hidden = false; }"); settle(q, 400)
                h = q.evaluate("""() => { const g = document.getElementById('shapeSeg'); const r = g.getBoundingClientRect();
                  const b = [...g.querySelectorAll(':scope > button')].filter(x => x.getBoundingClientRect().width);
                  const last = b[b.length - 1].getBoundingClientRect(), first = b[0].getBoundingClientRect();
                  return { right: +(r.right - last.right).toFixed(2), left: +(first.left - r.left).toFixed(2) }; }""")
                check(f"SHAPE PICKER: {route} with {kind} — no dead track after the last option",
                      abs(h["right"] - h["left"]) <= 1, str(h))
            c.close()

    # ---------------------------------------------------------------- 7
    if want("selection"):
        print("\nSELECTION — the defects the pick-one census found")
        for route, ed in (("/skribl-pad", "pad"), ("/flip", "flip")):
            c = ctx_for("dark", "desk"); q = c.new_page()
            browsing.goto(q, BASE, route); settle(q)
            # (a) a custom background paints a mark when chosen.
            browsing.pad_drawer(q, "draw")
            q.click("#paintTargetSeg [data-target='background']"); settle(q, 400)
            q.evaluate("""() => { const i = document.getElementById('customBgInput'); i.value = '#2a6f4e';
              i.dispatchEvent(new Event('input', { bubbles: true })); }""")
            q.evaluate("() => document.getElementById('customBgBtn').scrollIntoView({block: 'center'})")
            settle(q, 700)
            el = q.query_selector("#customBgBtn"); bb = el.bounding_box()
            clipbox = {"x": bb["x"] - 5, "y": bb["y"] - 5, "width": bb["width"] + 10, "height": bb["height"] + 10}
            on = q.screenshot(clip=clipbox)
            act = q.evaluate("() => document.getElementById('customBgBtn').classList.contains('active')")
            q.click("#bgGroup .bg-swatch[data-bg]"); settle(q, 300)
            off = q.screenshot(clip=clipbox)
            _a = Image.open(io.BytesIO(on)).convert("RGB").tobytes()
            _b = Image.open(io.BytesIO(off)).convert("RGB").tobytes()
            diff = sum(1 for k in range(0, min(len(_a), len(_b)), 3)
                       if max(abs(_a[k + i] - _b[k + i]) for i in range(3)) > 40)
            check(f"(a) {route}: a chosen custom background is marked, in pixels", act and diff > 30,
                  f"active={act}, {diff} pixels differ from the unchosen swatch")
            q.click("#paintTargetSeg [data-target='stroke']"); settle(q, 300)
            # (b) a pen colour no preset names rings the custom swatch.
            q.evaluate("(h) => (typeof setPenColor === 'function' ? setPenColor : setColor)(h)", "#3d8f7a")
            st = q.evaluate("""() => ({ custom: document.getElementById('customColorBtn').classList.contains('active'),
              n: document.querySelectorAll('#colorGroup .color-dot.active').length })""")
            check(f"(b) {route}: an unnamed pen colour rings the custom swatch, and only it",
                  st["custom"] and st["n"] == 1, str(st))
            browsing.pad_drawer_close(q)
            # (d) the open Tune button keeps its tint.
            tb = q.query_selector("#tuneBtn").bounding_box()
            mid = {"x": tb["x"] + 4, "y": tb["y"] + tb["height"] / 2 - 2, "width": 4, "height": 4}
            shut = Image.open(io.BytesIO(q.screenshot(clip=mid))).convert("RGB").getpixel((1, 1))
            q.click("#tuneBtn"); settle(q, 600)
            opened = Image.open(io.BytesIO(q.screenshot(clip=mid))).convert("RGB").getpixel((1, 1))
            check(f"(d) {route}: the open Tune button is tinted, in pixels",
                  max(abs(shut[i] - opened[i]) for i in range(3)) >= 12, f"shut {shut} open {opened}")
            q.click("#tuneBtn"); settle(q, 400)
            # (c)(g) the loop view's focus follows the state, with the class the seg reads.
            browsing.pad_drawer(q, "music")
            q.set_input_files("#musicInput", {"name": "t.wav", "mimeType": "audio/wav", "buffer": AUD})
            q.wait_for_function("() => document.getElementById('musicUploadBtn').classList.contains('loaded')", timeout=20000)
            settle(q, 500)
            if q.get_attribute("#fineTuneToggle", "aria-expanded") != "true":
                q.click("#fineTuneToggle"); settle(q, 500)
            q.click(".zoom-seg [data-focus='start']"); settle(q, 300)
            lit = "() => [...document.querySelectorAll('.zoom-seg [data-focus]')].filter(b => b.classList.contains('on') || b.classList.contains('active')).map(b => b.dataset.focus)"
            check(f"(c) {route}: choosing Start lights Start", q.evaluate(lit) == ["start"], str(q.evaluate(lit)))
            if ed == "flip":
                q.evaluate("() => { const s = document.getElementById('zoomPanSlider'); s.value = '700'; s.dispatchEvent(new Event('input', { bubbles: true })); }")
                settle(q, 300)
                check(f"(c) {route}: a free pan leaves no focus lit", q.evaluate(lit) == [], str(q.evaluate(lit)))
                q.click(".zoom-seg [data-focus='end']"); settle(q, 200)
                q.set_input_files("#musicInput", {"name": "u.wav", "mimeType": "audio/wav", "buffer": AUD})
                settle(q, 1500)
                check(f"(g) {route}: a new track lights Loop, the focus it resets to", q.evaluate(lit) == ["loop"],
                      str(q.evaluate(lit)))
            browsing.pad_drawer_close(q)
            if ed == "flip":
                # (e) a canvas no preset names says its size; (f) an unnamed fps says its rate.
                q.evaluate("() => { applyCanvasSize(700, 500); }")
                q.click("#moreBtn"); settle(q)
                n = q.evaluate("""() => { const s = document.getElementById('canvasSeg'); const note = document.getElementById('canvasSegNote');
                  return { on: s.querySelectorAll('button.on').length, note: note && !note.hidden ? note.textContent : null }; }""")
                check("(e) /flip: a canvas no preset names lights none and says its size",
                      n["on"] == 0 and n["note"] and "700" in n["note"] and "500" in n["note"], str(n))
                q.keyboard.press("Escape"); settle(q, 400)
                q.evaluate("() => { fps = 8; if (typeof syncFpsSeg === 'function') syncFpsSeg(); }")
                f = q.evaluate("""() => { const g = document.getElementById('fps');
                  return { on: g.querySelectorAll('button.on').length, hint: g.closest('.tune-row').querySelector('.tune-hint').textContent }; }""")
                check("(f) /flip: an fps no button names lights none and says the rate", f["on"] == 0 and "8" in f["hint"], str(f))
            else:
                # (h)(i) a restored draft marks its background and its fit.
                for bg, which in (("#2A6F4E", "custom"), ("#FFFFFF", "preset")):
                    r = q.evaluate("""(bg) => { loadSkribl({ version: 2, strokes: [], background: { color: bg },
                        photo: { data: '""" + PNG + """', fit: 'fill' } });
                      const on = [...document.querySelectorAll('#bgGroup .bg-swatch.active')];
                      const c = document.getElementById('customBgBtn');
                      return { on: on.map(b => b.id || b.dataset.bg), customColor: c.style.getPropertyValue('--custom-color') }; }""", bg)
                    settle(q, 300)
                    if which == "custom":
                        check("(h) /skribl-pad: a restored custom background marks the custom swatch, in its colour",
                              r["on"] == ["customBgBtn"] and r["customColor"].lower() == "#2a6f4e", str(r))
                    else:
                        check("(h) /skribl-pad: a restored upper-case preset marks that preset, and only it",
                              r["on"] == ["#ffffff"], str(r))
                settle(q, 500)
                fit = q.evaluate("() => [...document.querySelectorAll('.photo-fit-btn.active')].map(b => b.dataset.fit)")
                check("(i) /skribl-pad: a restored fit spelled 'fill' lights Stretch", fit == ["stretch"], str(fit))
            c.close()

    browser.close()

bad = [r for r in results if not r[0]]
print(f"\n{'=' * 62}\n{len(results) - len(bad)}/{len(results)} passed"
      + ("" if not bad else "  FAILURES: " + ", ".join(n for _, n in bad)))
sys.exit(1 if bad else 0)
