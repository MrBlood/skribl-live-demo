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
     two pills, one stuck at opacity 0. Photo | Music, the media card's
     tablist, is a track too, measured with each tab chosen.
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
  8. POPS. A surface floating over the page hides it: the page is swapped
     for a checkerboard and then the board shifted a square, and nothing may
     come through. The shape picker hangs inside the dock, whose own
     backdrop-filter blinded the picker's blur, and let Flip's page strip
     read straight through its 0.78 glass.
  9. FOCUS. A group's one Tab stop is its selected option, so its ring must
     show there: under forced colours (where selection's outline had painted
     over focus) and unforced on the tracks whose overflow: hidden clipped the
     ring to a sliver -- counted in pixels on each side of the option.
 10. HEIGHTS. The library's filter keeps the chip's 34 to the eye.

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
  const TR = '.seg, .smooth-seg, .gif-seg, .photo-fit-group, .seg-track, .media-tabs, #toolGroup';
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
      selText: sel ? (sel.textContent || '').trim() : null,
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
chosen = set()   # (route, control, the selected option's label): Photo | Music is measured with each chosen


def audit(page, route, theme, form, state):
    groups = page.evaluate(CENSUS)
    for g in groups:
        ident = (route, g["key"])
        tag = f"{route} {g['key']} [{theme} {form}{', ' + state if state else ''}]"
        first = ident not in seen
        seen.add(ident)
        chosen.add((route, g["key"], g["selText"]))
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
        if q.get_attribute("#fineTuneToggle", "aria-pressed") != "true":
            q.click("#fineTuneToggle")
        settle(q)
        q.evaluate("() => { const b = document.querySelector('.zoom-mag-bar'); if (b) b.scrollIntoView({block: 'center'}); }")
        settle(q, 300)
        yield "music drawer"
        # The phone's music drawer is taller than the screen and the reach
        # above scrolls the tabs off it: bring them back to measure Music.
        q.evaluate("() => document.getElementById('mediaTabs').scrollIntoView({block: 'center'})")
        settle(q, 300)
        yield "music tabs"
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
                                              "speedSeg", "photoFitGroup", "themeSeg", "hintSeg", "canvasSeg",
                                              "mediaTabs")}
        must |= {("/flip", k) for k in ("toolGroup", "paintTargetSeg", "smoothSeg", "brushSeg", "pressureSeg",
                                         "eraserSeg", "shapeSeg", "fps", "gridDensitySeg", "mirrorSeg",
                                         "smearWeightSeg", "onionDepthSeg", "photoFitGroup", "themeSeg", "hintSeg",
                                         "canvasSeg", "mbScope", "exportSizeSeg", "exportLoopsSeg", "mediaTabs")}
        missing = sorted(m for m in must if m not in seen)
        check("ONE PILL: the census reached every control it names (a control not measured is not passing)",
              not missing, f"not reached: {missing}; reached {len(seen)}")
        for route, extra in (("/skribl-pad", ("zoom-seg", "gif-seg")), ("/flip", ("zoom-seg", "gif-seg"))):
            check(f"ONE PILL: {route}'s script-built and sheet-borne tracks were measured: {', '.join(extra)}",
                  all(any(k[0] == route and e in k[1] for k in seen) for e in extra),
                  str(sorted(k[1] for k in seen if k[0] == route)))
        for route in ("/skribl-pad", "/flip"):
            got = sorted(t for (r, k, t) in chosen if r == route and k == "mediaTabs")
            check(f"ONE PILL: {route}'s Photo | Music was measured with Photo chosen and with Music chosen",
                  "Photo" in got and "Music" in got, str(got))
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
            FB = """() => { const out = [];
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
              } return out; }"""
            fb = q.evaluate(FB)
            if route in ("/skribl-pad", "/flip"):
                # Photo | Music lives in the media card, not in Tune.
                q.click("#tuneBtn"); settle(q, 400)
                browsing.pad_drawer(q, "photo"); settle(q)
                fb += [f for f in q.evaluate(FB) if f["key"] == "mediaTabs"]
                check(f"FALLBACK: {route} had Photo | Music's placed pill to take away",
                      any(f["key"] == "mediaTabs" for f in fb), str([f["key"] for f in fb]))
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
        EDGE = r"""() => { const TR = '.seg, .smooth-seg, .gif-seg, .photo-fit-group, .seg-track, .media-tabs, #toolGroup, #toolTray';
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
                browsing.pad_drawer(q, "photo"); settle(q, 400)
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
            need = {"toolGroup", "smoothSeg", "brushSeg", "mirrorSeg", "mediaTabs"} if route != "/gallery" and route != "/library" else set()
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
            # Closing the last drawer glides the page home (lib/drawers.js holds
            # its height while it does); a rect read mid-glide is the wrong one.
            q.wait_for_function("() => window.scrollY === 0", timeout=5000); settle(q, 100)
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
            if q.get_attribute("#fineTuneToggle", "aria-pressed") != "true":
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

    # ---------------------------------------------------------------- 8
    if want("pops"):
        print("\nPOPS — a surface floating over the page hides what is under it")
        # The page behind each surface is swapped for a checkerboard, then for
        # the same board shifted one square: whatever differs between the two
        # shots came THROUGH the surface. A working blur averages the board to
        # one grey and passes; a translucent fill whose blur never applies (a
        # backdrop-filter inside another is blind to the page) shows it.
        HIDE = r"""(sel) => { const el = document.querySelector(sel); if (!el) return false;
          const st = document.createElement('style'); st.id = '__pops';
          st.textContent = 'html{background:repeating-conic-gradient(#000 0 25%,#fff 0 50%) 0 0/16px 16px !important}'
            + 'html.__pb{background-position:8px 0 !important}';
          document.head.appendChild(st);
          let n = el;
          while (n.parentElement) { const par = n.parentElement;
            for (const s of par.children) if (s !== n && s.tagName !== 'STYLE') s.style.setProperty('visibility', 'hidden', 'important');
            if (par !== document.documentElement) par.style.setProperty('background', 'transparent', 'important');
            n = par; }
          return true; }"""

        def see_through(q, sel):
            if not q.evaluate(HIDE, sel):
                return None
            settle(q, 300)
            r = q.evaluate("(s) => { const r = document.querySelector(s).getBoundingClientRect(); return [r.left, r.top, r.width, r.height]; }", sel)
            box = {"x": r[0] + 16, "y": r[1] + 16, "width": min(r[2] - 32, 360), "height": min(r[3] - 32, 200)}
            a = Image.open(io.BytesIO(q.screenshot(clip=box))).convert("L").tobytes()
            q.evaluate("() => document.documentElement.classList.add('__pb')"); settle(q, 150)
            b = Image.open(io.BytesIO(q.screenshot(clip=box))).convert("L").tobytes()
            return round(sum(abs(a[i] - b[i]) for i in range(len(a))) / max(1, len(a)), 1)

        for theme in THEMES:
            for route, ed in (("/skribl-pad", "pad"), ("/flip", "flip")):
                surfaces = [("the shape picker", "#shapePop"), ("the draw drawer", "#drawPanel"), ("Tune", "#tuneShell")]
                if ed == "flip":
                    surfaces.append(("the tool tray", "#toolTray"))
                for name, sel in surfaces:
                    c = ctx_for(theme, "phone"); q = c.new_page()
                    browsing.goto(q, BASE, route); settle(q)
                    if sel == "#shapePop":
                        if ed == "pad":
                            q.click("#shapeToolBtn")
                        else:
                            q.evaluate("() => shelfSetTool('shape')")
                        q.wait_for_selector("#shapePop:not([hidden])", timeout=3000)
                        q.click("#shapeSeg [data-shape='rect']"); settle(q, 300)
                        q.evaluate("() => { document.getElementById('shapePop').hidden = false; }")
                    elif sel == "#drawPanel":
                        browsing.pad_drawer(q, "draw")
                    elif sel == "#tuneShell":
                        q.click("#tuneBtn"); q.wait_for_selector("#tuneShell.open", timeout=3000)
                    else:
                        q.click("#toolMoreBtn"); q.wait_for_selector("#toolTray:not([hidden])", timeout=3000)
                    settle(q, 500)
                    t = see_through(q, sel)
                    check(f"POPS: {route} {name} [{theme} phone] lets no page through (mean shift <= 6 of 255 when the page moves)",
                          t is not None and t <= 6, f"{t}")
                    c.close()

    # ---------------------------------------------------------------- 9
    if want("focus"):
        print("\nFOCUS — the one Tab stop is the selected option, and its ring shows")
        FOCUS = r"""(sel) => { const b = document.querySelector(sel); if (!b) return null;
          b.focus({ preventScroll: true }); return b.matches(':focus-visible'); }"""

        def ring(q, sel, pad=7):
            """Pixels that change around an option when it takes keyboard focus,
            per side of its box: {top, bottom, left, right, inside}."""
            q.evaluate("() => document.activeElement && document.activeElement.blur()")
            # A focused option with a data-tip shows its tooltip, and those
            # pixels changing would pass the count with no ring at all.
            q.evaluate("""() => { if (document.getElementById('__notips')) return;
              const st = document.createElement('style'); st.id = '__notips';
              st.textContent = '.skribl-tip { display: none !important; }'; document.head.appendChild(st); }""")
            q.evaluate("(s) => document.querySelector(s).scrollIntoView({block: 'center'})", sel)
            settle(q, 350)
            r = q.evaluate("(s) => { const r = document.querySelector(s).getBoundingClientRect(); return [r.left, r.top, r.width, r.height]; }", sel)
            box = {"x": r[0] - pad, "y": r[1] - pad, "width": r[2] + 2 * pad, "height": r[3] + 2 * pad}
            a = Image.open(io.BytesIO(q.screenshot(clip=box))).convert("RGB")
            # Keyboard modality first: after a click, Chromium does not make a
            # script focus visible, whatever focus() is asked.
            q.keyboard.press("Shift")
            fv = q.evaluate(FOCUS, sel); settle(q, 350)
            b = Image.open(io.BytesIO(q.screenshot(clip=box))).convert("RGB")
            q.evaluate("() => document.activeElement && document.activeElement.blur()")
            W, H = a.size; out = {"top": 0, "bottom": 0, "left": 0, "right": 0, "inside": 0, "fv": fv,
                                  "w": round(r[2]), "h": round(r[3])}
            pa, pb = a.load(), b.load()
            for y in range(H):
                for x in range(W):
                    if max(abs(pa[x, y][i] - pb[x, y][i]) for i in range(3)) <= 24:
                        continue
                    if y < pad: out["top"] += 1
                    elif y >= H - pad: out["bottom"] += 1
                    elif x < pad: out["left"] += 1
                    elif x >= W - pad: out["right"] += 1
                    else: out["inside"] += 1
            return out

        # Under forced colours: focus on the SELECTED option must change the screen.
        for route in ("/skribl-pad", "/flip", "/gallery", "/library"):
            c = ctx_for("dark", "desk", forced=True); q = c.new_page()
            if route in ("/skribl-pad", "/flip"):
                browsing.goto(q, BASE, route); settle(q)
                # The dock first, drawer shut: with the pen's drawer open,
                # focusing the pen repaints the dock whatever its outline does.
                probe = [("the dock's tool", "#toolGroup .tool-btn.active"),
                         ("Brush", "#brushSeg > button.on, #brushSeg > button.active"),
                         ("Photo | Music", "#mediaTabs > [aria-selected='true']")]
            else:
                q.goto(BASE + route, wait_until="load"); settle(q)
                probe = ([("New / Hot", ".tabs > button.active, .tabs > [aria-selected='true']")] if route == "/gallery" else
                         [("the filter", ".chips > button[aria-pressed='true']"),
                          ("Skribls / Drafts", ".libtabs-list > [aria-selected='true']")])
            for name, sel in probe:
                if name == "Brush":
                    browsing.pad_drawer(q, "draw"); settle(q, 400)
                if name == "Photo | Music":
                    browsing.pad_drawer(q, "photo"); settle(q, 400)
                sel = q.evaluate("(s) => { const e = document.querySelector(s); if (!e) return null; e.setAttribute('data-fprobe', ''); return '[data-fprobe]'; }", sel)
                if not sel:
                    check(f"FOCUS: {route} {name} — a selected option was found to focus", False, "none"); continue
                d = ring(q, sel)
                total = d["top"] + d["bottom"] + d["left"] + d["right"] + d["inside"]
                check(f"FOCUS: {route} {name} [forced colours] — keyboard focus on the selected option changes the screen",
                      d["fv"] and total >= 40, str(d))
                q.evaluate("() => document.querySelector('[data-fprobe]').removeAttribute('data-fprobe')")
            c.close()

        # Unforced: the ring reaches all four sides of a focused option in the
        # tracks that clipped it (a middle option, so both ends are neighbours).
        for route in ("/skribl-pad", "/flip"):
            c = ctx_for("dark", "desk"); q = c.new_page()
            browsing.goto(q, BASE, route); settle(q)
            browsing.pad_drawer(q, "draw"); settle(q, 400)
            rows = [("Brush", "#brushSeg > button:nth-of-type(2)")]
            d = ring(q, rows[0][1])
            results_rows = [(rows[0][0], d)]
            browsing.pad_drawer(q, "photo")
            q.set_input_files("#photoInput" if route == "/skribl-pad" else "#imageInput",
                              {"name": "p.png", "mimeType": "image/png",
                               "buffer": __import__("base64").b64decode(PNG.split(",", 1)[1])})
            q.wait_for_function("() => document.getElementById('photoUploadBtn').classList.contains('loaded')", timeout=20000)
            settle(q, 500)
            results_rows.append(("Fill / Fit / Stretch", ring(q, ".photo-fit-group .photo-fit-btn:nth-of-type(2)")))
            results_rows.append(("Photo | Music", ring(q, "#mediaTabs > [aria-selected='true']")))
            for name, d in results_rows:
                check(f"FOCUS: {route} {name} — the focus ring shows on all four sides (no track clips it)",
                      d["fv"] and min(d["top"], d["bottom"]) >= d["w"] and min(d["left"], d["right"]) >= d["h"], str(d))
            c.close()

    # ---------------------------------------------------------------- 10
    if want("heights"):
        print("\nHEIGHTS — the library's filter keeps the chip's height")
        for form in FORMS:
            c = ctx_for("dark", form); q = c.new_page()
            q.goto(BASE + "/library", wait_until="load"); settle(q)
            h = q.evaluate("""() => { const t = document.querySelector('.chips'); const b = t.querySelector(':scope > button');
              return { track: t.getBoundingClientRect().height, option: b.getBoundingClientRect().height }; }""")
            check(f"HEIGHTS: /library filter [{form}] — options 34 to the eye (the chip's height, SK-AUD-005's floor), track 42",
                  abs(h["option"] - 34) <= 0.5 and abs(h["track"] - 42) <= 0.5, str(h))
            c.close()

    # ---------------------------------------------------------------- 10
    if want("tints"):
        print("\nTINTS — a ring only where a tint cannot show (owner, Rings and Tints)")
        # Read as the mechanism, not as pixels: the ring was a box-shadow (or a
        # pulsing one), the tint is --seg-on-fill. A probe element resolves the
        # token on the page being measured, so a theme's own value is compared.
        TINT = """() => { const d = document.createElement('div'); d.style.background = 'var(--seg-on-fill)';
            document.body.appendChild(d); const v = getComputedStyle(d).backgroundColor; d.remove(); return v; }"""
        def long_draw(q, canvas):
            # A take long enough to still be playing when it is measured.
            bb = q.query_selector(canvas).bounding_box()
            q.mouse.move(bb["x"] + 40, bb["y"] + 60); q.mouse.down()
            for i in range(50):
                q.mouse.move(bb["x"] + 40 + i * 4, bb["y"] + 60 + (i % 10) * 6); q.wait_for_timeout(30)
            q.mouse.up(); settle(q, 300)
        LOOK = """(sel) => { const e = document.querySelector(sel); if (!e) return null; const c = getComputedStyle(e);
            return { shadow: c.boxShadow, bg: c.backgroundColor, anim: c.animationName, r: parseFloat(c.borderTopLeftRadius) || 0,
                     left: c.borderLeftColor, top: c.borderTopColor, border: c.borderTopColor }; }"""
        for theme in ("dark", "light"):
            c = ctx_for(theme, "phone"); q = c.new_page()
            browsing.goto(q, BASE, "/skribl-pad"); settle(q)
            tint = q.evaluate(TINT)
            q.click("#tuneBtn"); settle(q, 500)
            t = q.evaluate(LOOK, "#tuneBtn")
            check(f"TINTS [{theme}]: the open Tune button wears the tint and no ring",
                  t and t["bg"] == tint and t["shadow"] == "none", f"{t}, tint {tint}")
            q.click("#tuneBtn"); settle(q, 400)
            q.click("#mediaOpenBtn"); settle(q, 500)
            md = q.evaluate(LOOK, "#mediaOpenBtn")
            check(f"TINTS [{theme}]: the open Media button wears the selected tool's tile (owner, B), rounded like it",
                  md and md["bg"] == tint and md["shadow"] == "none" and md["r"] >= 10, f"{md}, tint {tint}")
            q.click("#mediaOpenBtn"); browsing.wait_scroll_still(q); settle(q, 300)
            long_draw(q, "#canvas"); q.click("#recordBtn"); settle(q, 600)
            q.click("#playBtn"); settle(q, 600)
            pb = q.evaluate(LOOK, "#playBtn"); pw = q.evaluate(LOOK, "#playWrap")
            check(f"TINTS [{theme}]: Play while playing is a steady tint, no pulse (phone)",
                  pb and pb["bg"] == tint and pb["anim"] == "none" and pw["anim"] == "none", f"{pb} / wrap {pw}")
            q.click("#menuBtn"); settle(q, 500)
            f = q.evaluate(LOOK, ".menu-item.menu-feature")
            check(f"TINTS [{theme}]: the How it works row keeps its tint and drops its ring",
                  f and f["shadow"] == "none" and f["bg"] not in ("rgba(0, 0, 0, 0)", "transparent"), str(f))
            c.close()

            c = ctx_for(theme, "desk"); q = c.new_page()
            browsing.goto(q, BASE, "/skribl-pad"); settle(q)
            tint = q.evaluate(TINT)
            q.click("#magnifyBtn"); q.mouse.move(5, 5); settle(q, 500)
            mg = q.evaluate(LOOK, "#magnifyBtn")
            check(f"TINTS [{theme}]: Magnify while on wears the selected tool's tile (owner, B), rounded like it",
                  mg and mg["bg"] == tint and mg["shadow"] == "none" and mg["r"] >= 10, f"{mg}, tint {tint}")
            q.click("#magnifyBtn"); settle(q, 400)
            long_draw(q, "#canvas"); q.click("#recordBtn"); settle(q, 600)
            q.click("#playBtn"); q.mouse.move(5, 5); settle(q, 600)   # off the pill: hover films it
            pw = q.evaluate(LOOK, "#playWrap")
            check(f"TINTS [{theme}]: from 641px the whole Stop pill takes the tint, no pulse",
                  pw and pw["bg"] == tint and pw["anim"] == "none" and pw["shadow"] == "none", f"{pw}, tint {tint}")
            c.close()

            c = ctx_for(theme, "phone"); q = c.new_page()
            browsing.goto(q, BASE, "/flip"); settle(q)
            tint = q.evaluate(TINT)
            q.click("#moreBtn"); settle(q, 500)
            m = q.evaluate(LOOK, "#moreBtn")
            check(f"TINTS [{theme}]: Flip's open ⋯ wears the tint and no ring",
                  m and m["bg"] == tint and m["shadow"] == "none", f"{m}, tint {tint}")
            q.keyboard.press("Escape"); settle(q, 400)
            q.click("#mediaOpenBtn"); settle(q, 500)
            fm = q.evaluate(LOOK, "#mediaOpenBtn")
            check(f"TINTS [{theme}]: Flip's open Media button wears the selected tool's tile (owner, B)",
                  fm and fm["bg"] == tint and fm["shadow"] == "none", f"{fm}, tint {tint}")
            q.click("#mediaOpenBtn"); browsing.wait_scroll_still(q); settle(q, 300)
            fr = q.evaluate(LOOK, "#strip .frame.on")
            check(f"TINTS [{theme}]: Flip's current page keeps one 1px ring, without the second outside it",
                  fr and fr["shadow"] == "none" and fr["border"] not in ("rgba(0, 0, 0, 0)",), str(fr))
            draw(q, "#pad"); q.click("#addcopy"); settle(q, 500)   # Play shows from two pages
            q.click("#play"); settle(q, 300)
            fp = q.evaluate(LOOK, ".btn.flip-play.playing"); fw = q.evaluate(LOOK, "#flipPlayWrap")
            check(f"TINTS [{theme}]: Flip's Play while playing is a steady tint, no pulse",
                  fp and fp["anim"] == "none" and fw["anim"] == "none" and tint in (fp["bg"], fw["bg"]),
                  f"{fp} / wrap {fw}, tint {tint}")
            c.close()

        # The Library's playing row: R1, the tint and no edge line (owner).
        # Its page has its own palette and no --seg-on-fill, so the row is
        # read for what it must NOT carry and for a fill that is not the rest's.
        import json as _json, urllib.request as _ur
        _ents = []
        for _t in ("Tint probe A", "Tint probe B"):
            _body = {"frames": [{"strokes": [], "strokeGroups": [], "background": {"color": "#101418"}}],
                     "title": _t, "visibility": "unlisted"}
            _r = _json.loads(_ur.urlopen(_ur.Request(BASE + "/api/skribls", data=_json.dumps(_body).encode(),
                                         headers={"Content-Type": "application/json"}), timeout=15).read())
            _ents.append({"id": _r["id"], "url": "/s/" + _r["id"], "title": _t, "kind": "pad", "pages": 1,
                          "tok": _r["deleteToken"], "at": 1700000000000})
        for theme in ("dark", "light"):
            c = ctx_for(theme, "phone"); q = c.new_page()
            q.goto(BASE + "/library", wait_until="load")
            q.evaluate("(e) => localStorage.setItem('skribl_posted_v1', JSON.stringify(e))", _ents)
            q.reload(wait_until="load"); settle(q, 1500)
            rows = q.evaluate("""() => [...document.querySelectorAll('#postedList .posted-row')].map(r => {
                const c = getComputedStyle(r); return { on: r.classList.contains('active'), shadow: c.boxShadow,
                bg: c.backgroundColor, left: c.borderLeftColor, top: c.borderTopColor }; })""")
            on = [r for r in rows if r["on"]]; off = [r for r in rows if not r["on"]]
            check(f"TINTS [{theme}]: the Library's playing row is a tint with no ring and no edge line (R1)",
                  len(on) == 1 and off and on[0]["shadow"] == "none" and on[0]["left"] == on[0]["top"]
                  and on[0]["bg"] != off[0]["bg"], str(rows))
            c.close()

    browser.close()

bad = [r for r in results if not r[0]]
print(f"\n{'=' * 62}\n{len(results) - len(bad)}/{len(results)} passed"
      + ("" if not bad else "  FAILURES: " + ", ".join(n for _, n in bad)))
sys.exit(1 if bad else 0)
