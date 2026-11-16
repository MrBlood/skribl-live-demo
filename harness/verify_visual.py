"""The things a screenshot shows instantly and 1,745 assertions did not.

WHY THIS EXISTS. Three of the last four faults reaching users were visual, and
every one of them passed a full green harness:

  * the editor rendered its header and toolbar over EMPTY SPACE until app.js
    ran, because `.canvas-wrap` was 0px wide until JS sized it;
  * the player showed a 300x150 box — the unstyled <canvas> default — in the
    middle of the page for the same reason;
  * the player CROPPED shared links, setting the wrap to the authored 816px
    inside a 718px column so `overflow: hidden` ate ~100px of drawing.

The suites were thorough about behaviour and blind to appearance. Ink was
counted, playback was driven, page errors were caught — and a viewer looking at
a blank rectangle would have passed all of it.

WHY NOT PIXEL BASELINES. Committed reference PNGs compared per-pixel are the
obvious answer and the wrong one here: font rasterisation, antialiasing and GPU
compositing differ between this container, a developer's laptop and CI, so the
baselines fail for reasons that have nothing to do with the product. A suite
that cries wolf gets its failures ignored, which is worse than no suite — this
tree already learned that lesson from a summary parser that turned failures into
crashes.

WHAT IT DOES INSTEAD. Asserts the GEOMETRY a screenshot would have revealed, all
of which is environment-independent:

  * nothing the user is meant to see is zero-sized or the unstyled default;
  * nothing overflows a clipping ancestor (the crop);
  * the surface is not blank BEFORE app.js runs (both editor and player);
  * the page does not scroll sideways at any width.

Each is checked across viewports, because two of the three bugs above only
appeared at particular widths — the crop needed a viewport WIDER than the app
column, which no fixture had.
"""
import base64
import math
import struct
import sys
import zlib

from playwright.sync_api import sync_playwright
from assertions import make_check
import browsing
import os

BASE = os.environ.get("SKRIBL_BASE", "http://127.0.0.1:5001")
VIEWPORTS = [(1600, 950), (1280, 900), (1023, 931), (830, 914), (420, 850)]

PNG = "/tmp/visual_photo.png"


def _png(w, h):
    raw = b"".join(b"\x00" + bytes([(x * 7) % 256, (y * 5) % 256, 180, 255][k]
                                   for x in range(w) for k in range(4))
                   for y in range(h))

    def chunk(tag, data):
        body = tag + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xffffffff)

    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw))
            + chunk(b"IEND", b""))


open(PNG, "wb").write(_png(400, 300))

results = []


check = make_check(results)


# The default size of a <canvas> with no width/height attribute. Seeing this on
# screen means JS has not sized it — it is what both blank-canvas bugs looked
# like, and it is a specific enough number to assert on directly.
UNSTYLED_CANVAS = [300, 150]

FRAME = """() => {
  const w = document.querySelector('.canvas-wrap');
  const c = document.getElementById('canvas');
  if (!w || !c) return null;
  const wr = w.getBoundingClientRect(), cr = c.getBoundingClientRect();
  const cs = getComputedStyle(w);
  return {
    wrap: [Math.round(wr.width), Math.round(wr.height)],
    canvas: [Math.round(cr.width), Math.round(cr.height)],
    // A clipping ancestor turns any overflow into drawing the viewer never sees.
    clipped: Math.round(cr.width) > Math.round(wr.width) + 0.5
          || Math.round(cr.height) > Math.round(wr.height) + 0.5,
    painted: cs.backgroundColor !== 'rgba(0, 0, 0, 0)' && cs.visibility !== 'hidden'
             && parseFloat(cs.opacity || '1') > 0.01,
    offscreen: wr.right < 1 || wr.bottom < 1 || wr.left > window.innerWidth - 1,
    hScroll: document.documentElement.scrollWidth > window.innerWidth + 2,
  };
}"""


def frame_checks(pg, label, vw):
    g = pg.evaluate(FRAME)
    check(f"{label} @{vw}: the canvas frame has a real size",
          g and g["wrap"][0] > 50 and g["wrap"][1] > 50,
          f"wrap {g and g['wrap']} — a zero-sized frame is an empty page")
    check(f"{label} @{vw}: it is not the unstyled canvas default",
          g and g["wrap"] != UNSTYLED_CANVAS and g["canvas"] != UNSTYLED_CANVAS,
          f"{UNSTYLED_CANVAS} means nothing sized it")
    check(f"{label} @{vw}: the drawing is not clipped by its wrapper",
          g and not g["clipped"],
          f"canvas {g and g['canvas']} in wrap {g and g['wrap']} — "
          "overflow:hidden makes the difference invisible, not smaller")
    check(f"{label} @{vw}: the frame is actually painted",
          g and g["painted"] and not g["offscreen"],
          "present in the DOM but transparent or off-screen is still blank")
    check(f"{label} @{vw}: the page does not scroll sideways",
          g and not g["hScroll"],
          "horizontal scroll means something is wider than the viewport")
    return g


def scribble(pg, n=40):
    box = pg.locator("#canvas").bounding_box()
    cx, cy = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
    pg.mouse.move(cx, cy)
    pg.mouse.down()
    for i in range(n):
        a = (i / n) * math.pi * 4
        r = 20 + (i / n) * min(90, box["width"] / 4)
        pg.mouse.move(cx + math.cos(a) * r, cy + math.sin(a) * r * 0.7)
        if i % 5 == 0:
            pg.wait_for_timeout(70)
    pg.mouse.up()


with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={"width": 1280, "height": 900})

    print("VISUAL — the editor is not blank before app.js runs")
    # THE regression. app.js blocked entirely is exactly the window a real
    # visitor sits in while it downloads, and it is what the user photographed.
    for vw, vh in ((1280, 900), (420, 850)):
        pg = ctx.new_page()
        pg.set_viewport_size({"width": vw, "height": vh})
        pg.route("**/app.js*", lambda route: route.abort())
        # require_boot=False, case 2: app.js is aborted ON PURPOSE one line up,
        # so this Pad can never set its marker. That is the whole assertion —
        # the editor must not be blank in the window a visitor sits in while
        # app.js downloads, which is the regression a user photographed.
        browsing.goto(pg, BASE, "/", require_boot=False)
        frame_checks(pg, "editor pre-JS", vw)
        pg.close()

    print("\nVISUAL — the editor, settled")
    pg = ctx.new_page()
    browsing.goto(pg, BASE, "/")
    for vw, vh in VIEWPORTS:
        pg.set_viewport_size({"width": vw, "height": vh})
        pg.wait_for_timeout(350)
        frame_checks(pg, "editor", vw)
    pg.set_viewport_size({"width": 1280, "height": 900})
    pg.wait_for_timeout(300)

    print("\nVISUAL — author and post, so the player has something real to show")
    scribble(pg)          # v288: the first stroke arms the take; no idle Record button
    pg.wait_for_timeout(400)
    pg.click("#recordBtn")
    pg.wait_for_timeout(600)
    pg.click("#postBtn")
    pg.wait_for_timeout(800)
    pg.fill("#postTitleInput", "visual")
    posted = browsing.submit_post(pg)
    link = posted["url"]
    check("posting produced a share link (fixture)", bool(link),
          "" if link else f"no /s/ URL; POST {posted['status']}; sheet says {posted['label']!r}; console {posted['console']}")
    pg.close()

    if not link:
        print(f"\n{'=' * 62}\n0/1 passed  FAILURES: fixture")
        b.close()
        sys.exit(1)

    print("\nVISUAL — the player is not blank before app.js runs")
    for vw, vh in ((1280, 900), (420, 850)):
        pl = ctx.new_page()
        pl.set_viewport_size({"width": vw, "height": vh})
        pl.route("**/app.js*", lambda route: route.abort())
        pl.goto(link, wait_until="load")
        pl.wait_for_timeout(500)
        frame_checks(pl, "player pre-JS", vw)
        pl.close()

    print("\nVISUAL — the player, settled, across widths")
    # The crop needed a viewport WIDER than .app's max-width. 1600 and 1280 are
    # both wider; 420 is narrower. Checking only one width hid this for months.
    pl = ctx.new_page()
    pl.goto(link, wait_until="load")
    pl.wait_for_timeout(3000)
    for vw, vh in VIEWPORTS:
        pl.set_viewport_size({"width": vw, "height": vh})
        pl.wait_for_timeout(400)
        frame_checks(pl, "player", vw)

    print("\nVISUAL — the player's own controls are visible")
    ctrl = pl.evaluate("""() => {
        const ids = ['playerPlayBtn', 'playerRestartBtn', 'playerLoopBtn'];
        return ids.map(id => {
          const e = document.getElementById(id);
          if (!e) return [id, 'missing'];
          const r = e.getBoundingClientRect();
          const cs = getComputedStyle(e);
          return [id, (r.width > 8 && r.height > 8 && cs.visibility !== 'hidden'
                       && parseFloat(cs.opacity || '1') > 0.01) ? 'visible' : 'not visible'];
        }); }""")
    check("play, restart and loop are all on screen",
          all(state == "visible" for _, state in ctrl), str(ctrl))
    pl.close()

    print("\nARTWORK STAGE — the rule holds on BOTH surfaces, not one")
    # v196 gave Flip an artwork stage and left Pad alone, which did not make Pad
    # wrong — it made the two DISAGREE, which is worse. Flip's pad carried too much
    # (onion skin and motion guides were sampled); Pad's canvas carried too little
    # (the background photo is a DOM <img> BEHIND it, so an empty pixel fell through
    # to bgColor and the eyedropper could not see the photo at all). Same rule
    # broken in opposite directions.
    #
    # This lives in verify_visual.py rather than verify_flipmotion.py precisely so
    # it cannot be satisfied by fixing one surface: it asserts the same property of
    # each, in one place, in one loop.
    for _label, _path, _input in (("Pad", "/", "#photoInput"), ("Flip", "/flip", None)):
        _pg = ctx.new_page()
        _pg.set_viewport_size({"width": 1100, "height": 950})
        _pg.goto(BASE + _path, wait_until="load")
        _pg.wait_for_timeout(1200)
        _sel = _input or _pg.evaluate(
            """() => { const i = document.querySelector('input[type=file][accept*=image]');
                       return i ? ('#' + i.id) : null; }""")
        if not _sel:
            check(f"{_label}: has a photo input (fixture)", False, "none found")
            _pg.close()
            continue
        _pg.set_input_files(_sel, PNG)
        _pg.wait_for_timeout(2800)
        _bg = _pg.evaluate("() => bgColor")
        # Set a sentinel first. Without it "the result is not the backdrop" also
        # passes when sampling silently does nothing and the pen keeps its
        # default — which is how #ffffff went green here on the first run.
        _pg.evaluate("() => { try { setColor('#010203'); } catch (e) { setPenColor('#010203'); } }")
        _pg.wait_for_timeout(200)
        # Sample an empty spot that sits OVER the photo. The photo is artwork, so
        # the answer must be the photo — never the backdrop showing through.
        _got = _pg.evaluate("""(isPad) => {
            const c = document.getElementById('canvas') || document.getElementById('pad');
            const b = c.getBoundingClientRect();
            if (typeof sampleColorAt !== 'function') return null;
            if (isPad) sampleColorAt(b.width * 0.5, b.height * 0.5);
            else sampleColorAt({ clientX: b.left + b.width * 0.5,
                                 clientY: b.top + b.height * 0.5 });
            return (typeof color !== 'undefined') ? color : null; }""", _label == "Pad")
        check(f"{_label}: the eyedropper actually sampled something",
              _got is not None and _got.lower() != "#010203",
              f"still the sentinel — sampleColorAt did nothing on {_label}, so any "
              "assertion about the VALUE below would pass while testing nothing")
        check(f"{_label}: the eyedropper can see the background photo",
              _got and _got.lower() not in ((_bg or "").lower(), "#010203"),
              f"returned {_got} against a backdrop of {_bg} — the photo IS artwork, "
              "and a sampler that reads only the stroke canvas cannot see it")
        _pg.close()

    # A LIGHT CANVAS KEEPS LIGHT EDGES WHILE A TAKE RECORDS. The Pad's recording
    # state swapped box-shadow wholesale and came after .light-bg, so White and
    # Paper got the dark canvas's grey vignette back with the first stroke --
    # found mocking Paper for the light theme. Asked of the PAINT, not the
    # style: one screenshot of the canvas, its edge band read against its own
    # middle at the same height, above the scribble. No baseline enters it, so
    # no font or GPU difference can either.
    print("\nVISUAL — a light canvas keeps light edges while a take records (Pad)")
    for _name, _hex in (("Paper", "#f6f2ea"), ("White", "#ffffff")):
        _pg = b.new_page(viewport={"width": 402, "height": 874})
        _pg.goto(BASE + "/skribl-pad", wait_until="load"); _pg.wait_for_timeout(700)
        _pg.evaluate("() => window.SkriblHints && window.SkriblHints.hide()")
        _pg.evaluate("(hex) => document.querySelector(`.bg-swatch[data-bg=\"${hex}\"]`).click()", _hex)
        _pg.wait_for_timeout(200)
        scribble(_pg)                  # the first stroke starts a take
        _pg.wait_for_timeout(600)      # past the box-shadow's 0.3s transition
        _w = _pg.evaluate("""() => { const w = document.querySelector('.canvas-wrap'), r = w.getBoundingClientRect();
            return { recording: w.classList.contains('recording'), light: w.classList.contains('light-bg'),
                     x: r.left, y: r.top, w: r.width, h: r.height }; }""")
        _shot = base64.b64encode(_pg.screenshot(clip={"x": _w["x"], "y": _w["y"], "width": _w["w"], "height": _w["h"]})).decode()
        _lum = _pg.evaluate("""async (b64) => {
            const img = new Image(); img.src = 'data:image/png;base64,' + b64; await img.decode();
            const c = document.createElement('canvas'); c.width = img.width; c.height = img.height;
            const x = c.getContext('2d'); x.drawImage(img, 0, 0);
            const L = (px, py) => { const d = x.getImageData(px, py, 1, 1).data; return 0.2126 * d[0] + 0.7152 * d[1] + 0.0722 * d[2]; };
            const y = Math.round(img.height * 0.18);
            return { edge: Math.round((L(10, y) + L(img.width - 11, y)) / 2), middle: Math.round(L(Math.round(img.width / 2), y)) }; }""", _shot)
        check(f"Pad on {_name}: while a take records, the canvas's edge stays within 18 levels of its middle",
              _w["recording"] and _w["light"] and _lum["middle"] - _lum["edge"] <= 18,
              f"{_w['recording']=} {_w['light']=} {_lum}")
        _pg.close()

    # THE CANVAS'S EDGE, ONE SCREEN PIXEL, THE PAD'S ON BOTH (the owner, Nov 15,
    # "The edges", B). On a phone's 3x screen the Pad's light canvas wore three
    # lines along its top (the light theme's mat line, the ring, and a 60%
    # black line that was the dark canvas's white highlight flipped by the
    # theme) and Flip's a 2px grey band, six screen pixels. Asked of the PAINT:
    # a 3x screenshot of the frame's left side and its top, decoded here, and
    # the edge counted as the screen pixels between the page's run and the
    # ground's run that stand 5% apart from both. Light and dark, on Paper and
    # on the dark ground, through the real ground swatch. A dark ground on the
    # light page is its own edge (no line stands apart from both there).
    print("\nVISUAL — the canvas's edge is one screen pixel, the Pad's on Flip too")
    _EDGE = """async ([b64, w, h]) => {
        const img = new Image(); img.src = 'data:image/png;base64,' + b64; await img.decode();
        const c = document.createElement('canvas'); c.width = img.width; c.height = img.height;
        const x = c.getContext('2d'); x.drawImage(img, 0, 0);
        const px = (a, b) => Array.from(x.getImageData(a, b, 1, 1).data.slice(0, 3));
        const ch = v => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); };
        const L = p => 0.2126 * ch(p[0]) + 0.7152 * ch(p[1]) + 0.0722 * ch(p[2]);
        const cr = (p, q) => { const a = L(p), b = L(q); return (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05); };
        const band = (pts, page, ground) => pts.map(([a, b]) => px(a, b)).filter(p => cr(p, page) >= 1.05 && cr(p, ground) >= 1.05);
        // the frame's left side at its middle, and its top at its middle; the clip starts 12 screen px outside
        const midY = Math.round(img.height / 2), midX = Math.round(img.width / 2);
        const side = band([...Array(24).keys()].map(i => [4 + i, midY]), px(0, midY), px(40, midY));
        const top = band([...Array(24).keys()].map(i => [midX, 4 + i]), px(midX, 0), px(midX, 40));
        return { side: side.length, top: top.length, sidePx: side[0] || null, topPx: top[0] || null }; }"""

    def _edge_of(route, scheme, ground):
        _c = b.new_context(viewport={"width": 402, "height": 874}, device_scale_factor=3, is_mobile=True,
                           has_touch=True, color_scheme=scheme, reduced_motion="reduce")
        _q = _c.new_page()
        _q.goto(BASE + route, wait_until="load"); _q.wait_for_timeout(700)
        _q.evaluate("() => window.SkriblHints && window.SkriblHints.hide()")
        _q.evaluate("(hex) => document.querySelector(`.bg-swatch[data-bg=\"${hex}\"]`).click()", ground)
        _q.wait_for_timeout(400)
        _f = _q.evaluate("""(s) => { const r = document.querySelector(s).getBoundingClientRect();
            return { x: r.left, y: r.top, w: r.width, h: r.height }; }""", ".canvas-wrap" if route == "/skribl-pad" else ".flip-wrap")
        # the frame and 12 screen px (4 CSS px) of page round it
        _clip = {"x": _f["x"] - 4, "y": _f["y"] - 4, "width": _f["w"] + 8, "height": _f["h"] + 8}
        _r = _q.evaluate(_EDGE, [base64.b64encode(_q.screenshot(clip=_clip)).decode(), _f["w"], _f["h"]])
        _c.close()
        return _r

    _cases = [(s, g) for s in ("light", "dark") for g in ("#f6f2ea", "#0d0f14")]
    _pad = {f"{s} {g}": _edge_of("/skribl-pad", s, g) for s, g in _cases}
    _flip = {f"{s} {g}": _edge_of("/flip", s, g) for s, g in _cases}
    _near = lambda a, b: bool(a) and bool(b) and max(abs(i - j) for i, j in zip(a, b)) <= 8
    check("the Pad's canvas edge is one screen pixel on a phone, along its top as at its side (no darker line"
          " there), light and dark, on Paper and on the dark ground",
          all(v["side"] <= 1 and v["top"] == v["side"] and (v["side"] == 0 or _near(v["sidePx"], v["topPx"]))
              for v in _pad.values())
          and _pad["light #f6f2ea"]["side"] == 1 and _pad["dark #0d0f14"]["side"] == 1,
          str(_pad))
    check("...and Flip's is the Pad's: the same screen pixels at its side and top in every case, its line within 8"
          " levels of the Pad's",
          all(_flip[k]["side"] == _pad[k]["side"] and _flip[k]["top"] == _pad[k]["top"]
              and (_pad[k]["side"] == 0 or _near(_flip[k]["sidePx"], _pad[k]["sidePx"])) for k in _pad),
          str(_flip))

    # IN FULL SCREEN THE DRAWING IS THE SCREEN: Flip's frame ring steps aside
    # with the rest of the frame, read off the screen's own left edge, through
    # the stand-in full screen a phone without the API gets (lib/watchfull.js).
    _c = b.new_context(viewport={"width": 402, "height": 874}, device_scale_factor=3, is_mobile=True,
                       has_touch=True, color_scheme="light", reduced_motion="reduce")
    _q = _c.new_page()
    _q.goto(BASE + "/flip", wait_until="load"); _q.wait_for_timeout(700)
    _q.evaluate("() => window.SkriblHints && window.SkriblHints.hide()")
    _q.evaluate("() => document.querySelector('.flip-wrap').classList.add('is-immersive-page')")
    _q.wait_for_timeout(400)
    _full = _q.evaluate("""async (b64) => {
        const img = new Image(); img.src = 'data:image/png;base64,' + b64; await img.decode();
        const c = document.createElement('canvas'); c.width = img.width; c.height = img.height;
        const x = c.getContext('2d'); x.drawImage(img, 0, 0); const y = Math.round(img.height / 2);
        return [0, 1, 2, 6].map(i => Array.from(x.getImageData(i, y, 1, 1).data.slice(0, 3))); }""",
        base64.b64encode(_q.screenshot()).decode())
    _c.close()
    check("in full screen Flip's ring steps aside with its frame: the screen's left edge is the drawing's ground",
          all(p == _full[-1] for p in _full[:3]), str(_full))

    b.close()

bad = [r for r in results if not r[0]]
print(f"\n{'=' * 62}\n{len(results) - len(bad)}/{len(results)} passed"
      + ("" if not bad else "  FAILURES: " + ", ".join(n for _, n in bad)))
sys.exit(1 if bad else 0)
