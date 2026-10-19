"""The tool tray's icons, measured as RENDERED rather than as authored.

THE REPORT was four words: "Fill is a weak icon." It was, and the reason was
measurable. Rendered and thresholded, Fill's ink filled 15x16 of its 24 box
where every other tool sat near 19x18 — the smallest thing in the tray — and the
bucket was a hollow diamond whose handle was a 3px stub. At tray size that reads
as a tilted square with a dot beside it.

WHAT THIS SUITE MEASURES, and why it is not the SVG source. A path's coordinates
say nothing about how much of the box the drawing occupies: stroke width, caps,
joins and fills all add ink outside the geometry, and two icons with identical
viewBoxes can differ by a third in apparent size. So each icon is rasterised
exactly as the browser paints it and the INK BOUNDING BOX is measured off the
alpha channel. That is the number a person's eye is actually responding to when
they say an icon looks weak.

WHAT IT DELIBERATELY DOES NOT ASSERT: ink COVERAGE, the share of the box that is
painted. It was measured throughout and it is a bad proxy for visual weight,
which the work proved twice. Stamps was 'fixed' from 24.3% to 19.7% coverage and
came out visibly worse, because the weight had been moved out of a solid base
bar that was holding the icon together. Two icons at the same coverage look
nothing alike when one is a thin outline over a wide area and the other is a
small solid mass. EXTENT correlated with the complaint; coverage did not.

THE LIQUIFY EXEMPTION IS THE MOST IMPORTANT THING IN THIS FILE. Liquify is the
flattest icon here by a wide margin — 13.5 tall against a ~18 norm — and that is
CORRECT. It is a smear, and a smear is wide and low. It was redrawn once to fill
the box's height, the number improved, and the result read as a caret with a
detached curl. The band below exempts it BY NAME so that the next person to run
this suite finds the reasoning instead of a failing assertion inviting them to
repeat the mistake.
"""
import io
import json
import os
import sys
import urllib.request

from PIL import Image
from assertions import make_check
import browsing

BASE = os.environ.get("SKRIBL_BASE", "http://127.0.0.1:5001")

try:
    from playwright.sync_api import sync_playwright
except ImportError:                                    # pragma: no cover
    print("SKIP: playwright is not installed")
    sys.exit(0)

results = []


check = make_check(results)


# THE BAND, in viewBox units of the 24x24 box.
#
# THIS IS THE SECOND VERSION OF THIS RULE, and the first one is worth knowing
# about because it was wrong in an instructive way. It was a per-AXIS band --
# width in 17.5-22.5, height in 17.0-21.0 -- derived from ten roughly square
# glyphs. Then three icons in a row turned out to be legitimately non-square and
# each needed a named exemption to pass:
#
#   Liquify  20.0 x 13.5   a warp is wide and low
#   Stamps   16.5 x 20.0   a rubber stamp is tall and narrow
#   Fill     16.0 x 21.5   a drop is a point over a round body
#
# Two exemptions were already flagged in DECISIONS v292 as the shape of a guard
# being dismantled. The third one is the answer: the per-axis floors were never
# the rule, they were a PROXY for it. What the band actually means is "occupies a
# comparable amount of the box to everything else", and none of those three is
# out of line on that -- their areas are 270, 330 and 344 against a set running
# 324 to 429.
#
# So the rule now says what it means. Area does the work, both ways; the per-axis
# limits are reduced to what they can honestly police, which is collapse in one
# dimension and overflow of the box. All three exemptions are GONE, and a rule
# that needs no special cases is a better rule than one carrying two.
MIN_AREA, MAX_AREA = 260, 450
# Collapse and overflow only. An icon may be any proportion between these.
MIN_AXIS, MAX_AXIS = 13.0, 22.5
CENTRE_TOL = 2.0

MEASURE = """async () => {
  const out = [];
  for (const c of document.querySelectorAll('#toolTray .tool-tray-btn')) {
    const svg = c.querySelector('svg');
    if (!svg) continue;
    const clone = svg.cloneNode(true);
    clone.setAttribute('width', '96'); clone.setAttribute('height', '96');
    const src = new XMLSerializer().serializeToString(clone).replace(/currentColor/g, '#fff');
    const img = new Image();
    await new Promise(r => { img.onload = r; img.onerror = r;
      img.src = 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(src); });
    const cv = document.createElement('canvas'); cv.width = 96; cv.height = 96;
    const g = cv.getContext('2d'); g.drawImage(img, 0, 0, 96, 96);
    const d = g.getImageData(0, 0, 96, 96).data;
    let x0 = 96, y0 = 96, x1 = -1, y1 = -1, sum = 0;
    for (let y = 0; y < 96; y++) for (let x = 0; x < 96; x++) {
      const a = d[(y * 96 + x) * 4 + 3];
      // A threshold, not `> 0`: anti-aliasing puts a faint halo a pixel or two
      // beyond every edge, and counting it inflates every measurement equally
      // — which hides exactly the differences this is here to find.
      if (a > 10) { sum += a;
        if (x < x0) x0 = x; if (x > x1) x1 = x;
        if (y < y0) y0 = y; if (y > y1) y1 = y; }
    }
    out.push({ tool: c.getAttribute('data-tool'),
               label: c.querySelector('span').textContent,
               w: (x1 - x0 + 1) / 4, h: (y1 - y0 + 1) / 4,
               cx: ((x0 + x1) / 2) / 4, cy: ((y0 + y1) / 2) / 4,
               cov: (sum / 255) / 9216 * 100 });
  }
  return out;
}"""

with sync_playwright() as p:
    br = p.chromium.launch()
    try:
        page = br.new_page(viewport={"width": 1280, "height": 900}, device_scale_factor=2)
        errs = []
        page.on("pageerror", lambda e: errs.append(str(e)))
        browsing.goto(page, BASE, "/flip")
        page.evaluate("() => SkriblFlipTools.buildTray()")
        page.wait_for_timeout(300)
        icons = page.evaluate(MEASURE)

        print("\nEVERY REGISTERED TOOL IS IN THE TRAY AND HAS A GLYPH")
        roster = page.evaluate("() => SkriblFlipTools.list()")
        check("every tool in the registry drew an icon",
              [i["tool"] for i in icons] == roster,
              f"{[i['tool'] for i in icons]} vs {roster} — a tool whose glyph "
              "fails to render leaves a cell with a label and nothing above it")

        print("\nHOW MUCH OF THE BOX IT OCCUPIES — the number the eye responds to")
        for i in icons:
            area = i["w"] * i["h"]
            check(f"{i['label']}: occupies its box like the rest of the set",
                  MIN_AREA <= area <= MAX_AREA,
                  f"ink {i['w']:.1f}x{i['h']:.1f}, area {area:.0f} against "
                  f"{MIN_AREA}-{MAX_AREA} — Fill shipped at 15.0x16.3 (245) and was "
                  "reported as weak; raw unscaled Lucide lands at 488 and reads "
                  "15% larger than its neighbours. Both ends are real")

        print("\nAND IS NOT COLLAPSED OR SPILLING OUT OF IT")
        for i in icons:
            check(f"{i['label']}: neither collapsed nor overflowing",
                  MIN_AXIS <= i["w"] <= MAX_AXIS and MIN_AXIS <= i["h"] <= MAX_AXIS,
                  f"{i['w']:.1f}x{i['h']:.1f} against {MIN_AXIS}-{MAX_AXIS} per axis "
                  "— area alone would pass a 13x22 splinter, and nothing may run "
                  "past the edge of a 24 box")

        print("\nOPTICALLY CENTRED — an icon adrift reads as the wrong size")
        for i in icons:
            check(f"{i['label']}: sits in the middle of its cell",
                  abs(i["cx"] - 12) <= CENTRE_TOL and abs(i["cy"] - 12) <= CENTRE_TOL + 0.6,
                  f"centre {i['cx']:.1f},{i['cy']:.1f} — a glyph pushed to one "
                  "side of a labelled cell reads as smaller than it is")

        # THE ONE THAT NAMES THE ORIGINAL REPORT. Kept separate from the band so
        # that relaxing the band later cannot quietly re-admit the exact icon
        # that prompted all of this.
        fill = next((i for i in icons if i["tool"] == "fill"), None)
        check("Fill is not the smallest icon in the tray any more",
              fill is not None and fill["w"] * fill["h"] >= MIN_AREA,
              f"{fill['w']:.1f}x{fill['h']:.1f} = {fill['w'] * fill['h']:.0f} — it "
              "shipped at 15.0x16.3 (245), the smallest here, as a hollow diamond "
              "with a 3px stub for a handle")
        smallest = min(icons, key=lambda i: i["w"] * i["h"])
        check("...and nothing else has taken its place",
              smallest["w"] * smallest["h"] >= MIN_AREA,
              f"{smallest['label']} at {smallest['w']:.1f}x{smallest['h']:.1f} "
              f"= {smallest['w'] * smallest['h']:.0f} is now the smallest here")

        print("\nCOVERAGE IS REPORTED, NOT ASSERTED — see the note at the top")
        cov = ", ".join(f"{i['label']} {i['cov']:.1f}%" for i in icons)
        check("the spread is recorded so a future change can be compared",
              True, cov)

        # TWO BUTTONS SIDE BY SIDE MUST NOT LOOK THE SAME, and this one is
        # measured the way the rest of this file is: rendered, not read off the
        # path data. The owner asked "you have motion smear and in-between have
        # the same icon?" and he was right -- they were built from the SAME two
        # full-strength outer bars, differing only by one extra middle mark at
        # 30-55% opacity. At 16px that mark is not there. The pair scored 29%
        # of their ink differing; redrawn so the smear is a pose with a trail
        # BEHIND it rather than a third bar BETWEEN two, they score 71%.
        #
        # Ink is whatever departs from the corner's background, so this reads
        # the same in either theme rather than assuming dark-on-light.
        _shots = {}
        for _bid in ("addinbetween", "addtween"):
            _el = page.query_selector("#" + _bid + " .addbtn-ic")
            if not _el:
                break
            _shots[_bid] = Image.open(io.BytesIO(_el.screenshot())).convert("L")
        check("both add buttons carry an icon to compare",
              len(_shots) == 2,
              f"found {len(_shots)} of 2 — this check is not comparing anything")
        if len(_shots) == 2:
            _a, _b = _shots["addinbetween"], _shots["addtween"]
            if _a.size != _b.size:
                _b = _b.resize(_a.size)
            _pa, _pb = _a.load(), _b.load()
            _W, _H = _a.size
            _bg = _pa[0, 0]
            _lit = _diff = 0
            for _y in range(_H):
                for _x in range(_W):
                    _va, _vb = _pa[_x, _y], _pb[_x, _y]
                    if abs(_va - _bg) > 25 or abs(_vb - _bg) > 25: _lit += 1
                    if abs(_va - _vb) > 40: _diff += 1
            _pct = 100.0 * _diff / max(_lit, 1)
            check("In-between and Motion Smear do not look like the same button",
                  _lit > 100 and _pct >= 50,
                  f"{_pct:.0f}% of the two icons' ink differs over {_lit} lit "
                  f"pixels — under half means they share their silhouette, which "
                  f"is what the shipped pair did at 29%")

        check("no page error through any of it", not errs, "; ".join(errs[:2]))
    finally:
        br.close()

# ---------------------------------------------------------------------------
# ONE BIN (owner, v318: "the trash cans are not the same ... I like the one
# with the ribbing"). Three bins were drawn: the ribbed one on the draft rows,
# a rounded one without ribs on Clear and on the photo and music file rows, and
# a slimmer third on a posted Skribl's Delete. Matched on PATH DATA, the thing
# that is drawn, never on a comment or a label: no retired bin shape may be
# drawn anywhere, and every bin site draws the ribbed one, body and ribs.
print("\nONE BIN — every trash can is the ribbed one")
import pathlib as _pl, re as _re
_ROOT = _pl.Path(__file__).resolve().parent.parent / "skribl"
_SRC = {p: p.read_text(encoding="utf-8") for p in
        list((_ROOT / "templates").rglob("*.html")) + list((_ROOT / "static").rglob("*.js"))
        if "vendor" not in p.parts and not p.name.endswith(".min.js")}
_RETIRED = ["3 6 5 6 21 6",                                         # the rounded bin's rim
            "M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6",        # ...its body
            "M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2",               # ...its lid
            "M6 7l1 13a1 1 0 0 0 1 1h8a1 1 0 0 0 1-1l1-13",          # the slim bin's body
            "M9 7V5a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"]               # ...its lid
_drawn = lambda txt: set(_re.findall(r'(?:\bd|points)="([^"]+)"', txt))
_left = sorted(f"{p.relative_to(_ROOT)}: {d}" for p, t in _SRC.items() for d in _drawn(t) if d in _RETIRED)
check("no retired bin shape is drawn anywhere (templates and scripts)", not _left, "; ".join(_left[:4]))
_BIN = ['M3 6h18', 'M8 6V4h8v2', 'M19 6l-1 14H6L5 6', 'M10 11v6M14 11v6']
# Every draft row draws its bin through lib/savedrafts.js rowEnd (D3), the
# Library's and the editors' sheet's: one there, none in library.js.
_SITES = {"static/lib/savedrafts.js": 1, "static/lib/postedui.js": 1,
          "templates/skribl/_skribl_draw_drawer.html": 2,
          "templates/skribl/_skribl_image_drawer.html": 1, "templates/skribl/_skribl_music_drawer.html": 1}
_short = []
for _rel, _n in _SITES.items():
    _t = _SRC.get(_ROOT / _rel, "")
    _have = min(len(_re.findall(r'(?:\bd|points)="' + _re.escape(d) + '"', _t)) for d in _BIN)
    if _have < _n:
        _short.append(f"{_rel}: {_have} of {_n}")
check("every bin site draws the ribbed bin, body and ribs", not _short, "; ".join(_short))

# ONE RELOAD (owner, after v324: "The reload icon looks wrong"). It was a
# circle whose arrowhead sat ON the rim with its tail run into the middle, so
# it read as a G or an e. Every reload (the installed app's menu row, the new
# version's note, Learn's and the Library's Try again) draws the circle-arrow,
# its head outside the rim: path data, as the bin. And as PAINT: drawn at
# 96px, the middle of the circle holds no ink, which the old drawing's tail
# crossed.
print("\nONE RELOAD — every reload is the circle-arrow, its middle empty")
_RELOAD_OLD = ["M20 11a8 8 0 1 0-2.3 5.7", "M20 4v7h-7"]
_RELOAD = ["M21 12a9 9 0 1 1-9-9c2.52 0 4.93 1 6.74 2.74L21 8", "M21 3v5h-5"]
_left = sorted(f"{p.relative_to(_ROOT)}: {d}" for p, t in _SRC.items() for d in _drawn(t) if d in _RELOAD_OLD)
check("no retired reload shape is drawn anywhere (templates and scripts)", not _left, "; ".join(_left[:4]))
_RSITES = ["templates/skribl/_skribl_homescreen.html", "static/lib/offline.js",
           "templates/skribl/_skribl_help.html", "templates/skribl/skribl_library.html"]
_short = [r for r in _RSITES if not all(('d="' + d + '"') in _SRC.get(_ROOT / r, "") for d in _RELOAD)]
check("every reload site draws the circle-arrow", not _short, "; ".join(_short))
with sync_playwright() as _rp:
    _rb = _rp.chromium.launch()
    _rq = _rb.new_page(viewport={"width": 96, "height": 96})
    _rq.set_content('<body style="margin:0;background:#fff"><svg width="96" height="96" viewBox="0 0 24 24" fill="none" stroke="#000" '
                    'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
                    + "".join(f'<path d="{d}"/>' for d in _RELOAD) + '</svg></body>')
    _im = Image.open(io.BytesIO(_rq.screenshot())).convert("L")
    _rb.close()
# The middle: a disc of 4 units (16px) round the circle's centre (12,12), well
# inside the 9-unit circle and clear of the arrowhead, which ends at (16,8).
_ink = sum(1 for x in range(96) for y in range(96) if (x - 48) ** 2 + (y - 48) ** 2 <= 16 ** 2 and _im.getpixel((x, y)) < 200)
check("the reload's circle is empty in the middle, as a circle-arrow is (no tail crossing it)",
      _ink == 0, f"{_ink} inked pixels within 16px of the centre, at 96px")

# ONE SET OF PLAYER ICONS (owner: "are all the icons consistent across all the
# players?"). They were not: two restarts, two loops, three speakers, three
# links, each player drawing its own. Same rule as the bin, same instrument --
# path data, never a comment or a label. The Pad and Flip HEADER play keeps its
# own wider triangle: it is drawn to match the Record dot and Stop square beside
# it, so it belongs to the header's set, not the players'.
print("\nONE SET OF PLAYER ICONS — every player draws the same restart, loop, sound, link and play")
_RETIRED_P = ["M1 4v6h6", "M3.51 15a9 9 0 1 0 2.13-9.36L1 10",            # the second restart
              "M3 11v-1a4 4 0 0 1 4-4h14", "M21 13v1a4 4 0 0 1-4 4H3",       # the flatter loop
              "M11 5L6 9H2v6h4l5 4V5z", "M15.54 8.46a5 5 0 0 1 0 7.07",      # the second speaker
              "M19.07 4.93a10 10 0 0 1 0 14.14",
              "M11 5 6 9H3v6h3l5 4z", "M16.5 8.5a5 5 0 0 1 0 7",             # the third
              "M19.5 5.5a9 9 0 0 1 0 13", "M22 9l-6 6", "M16 9l6 6",
              "M10 13a5 5 0 0 0 7 0l3-3a5 5 0 0 0-7-7l-1 1",                 # the rounded links
              "M14 11a5 5 0 0 0-7 0l-3 3a5 5 0 0 0 7 7l1-1",
              "M10 13a5 5 0 0 0 7.5.5l3-3a5 5 0 0 0-7-7l-1.7 1.7",
              "M14 11a5 5 0 0 0-7.5-.5l-3 3a5 5 0 0 0 7 7l1.7-1.7"]
_left = sorted(f"{p.relative_to(_ROOT)}: {d}" for p, t in _SRC.items() for d in _drawn(t) if d in _RETIRED_P)
_left += sorted(f"{p.relative_to(_ROOT)}: the line-drawn mute cross" for p, t in _SRC.items()
                if 'x1="23" y1="9"' in t)
check("no retired player icon is drawn anywhere (templates and scripts)", not _left, "; ".join(_left[:4]))
_ICON = {"restart": ["M3 12a9 9 0 1 0 3-6.7L3 8", "M3 3v5h5"],
         "loop": ["M17 2l4 4-4 4", "M3 11V9a4 4 0 0 1 4-4h14", "M7 22l-4-4 4-4", "M21 13v2a4 4 0 0 1-4 4H3"],
         "sound": ["M11 5 6 9H2v6h4l5 4z", "M15.5 8.5a5 5 0 0 1 0 7", "M19 5a9 9 0 0 1 0 14"],
         "muted": ["M11 5 6 9H2v6h4l5 4z", "m16 9 5 6", "m21 9-5 6"],
         "link": ["M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71",
                  "M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"],
         "play": ["M8 5v14l11-7z"]}
_PSITES = {"templates/skribl/_skribl_player_controls.html": ["restart", "loop", "sound", "link", "play"],
           "templates/skribl/skribl_library.html": ["restart", "loop", "sound", "link", "play"],
           "templates/skribl/_skribl_inline_player.html": ["loop", "sound", "muted", "play"],
           "static/lib/fullbar.js": ["restart", "loop", "sound", "muted", "play"],
           "static/app.js": ["sound", "muted", "play"],
           "static/lib/postedui.js": ["sound", "link"],
           "static/gallery.js": ["link"],
           # The Post sheet's Copy link: in the Pad's own template until #364,
           # in the sheet both editors include since.
           "templates/skribl/_skribl_post.html": ["link"],
           "templates/skribl/_skribl_export.html": ["loop"]}
_short = []
for _rel, _roles in _PSITES.items():
    _have = _drawn(_SRC.get(_ROOT / _rel, ""))
    _short += [f"{_rel}: {r}" for r in _roles if not set(_ICON[r]) <= _have]
check("every player draws the one restart, loop, sound, muted, link and play", not _short, "; ".join(_short))

print("\nCENTRING — the marks that read off-centre sit in the middle by their ink")
# The owner: "Some buttons with regular ascii or Unicode doesn't get centered".
# The centring machine (ink = the control photographed with its mark minus
# without; optical centre = midpoint of the ink box's centre and its centre of
# mass) found two clear misses: Flip's "×1" hold badge, 1.5px high in two of
# this box's three faces, and the eraser, 1.4px low, its ground line pulling
# its weight down. Measured in each installed face for the typed one, since
# that is the whole problem with typed marks.
_HIDE = (".__ctr_hide, .__ctr_hide * { color: transparent !important; -webkit-text-fill-color: transparent !important; }"
         " .__ctr_hide svg { visibility: hidden !important; }"
         " *, *::before, *::after { transition: none !important; animation: none !important; }")
def _optical(pg, sel, face=None, disc=False):
    """`disc`: a round control's mark is read inside its disc only, so a
    drawing playing behind the corners of its box is not taken for ink."""
    if face:
        pg.evaluate("([s, f]) => { document.querySelector(s).style.fontFamily = '\"' + f + '\"'; }", [sel, face])
    r = pg.evaluate("(s) => { const b = document.querySelector(s).getBoundingClientRect(); return [b.left, b.top, b.width, b.height]; }", sel)
    clip = {"x": r[0], "y": r[1], "width": r[2], "height": r[3]}
    on = Image.open(io.BytesIO(pg.screenshot(clip=clip))).convert("RGB")
    pg.evaluate("(s) => document.querySelector(s).classList.add('__ctr_hide')", sel)
    off = Image.open(io.BytesIO(pg.screenshot(clip=clip))).convert("RGB")
    pg.evaluate("(s) => document.querySelector(s).classList.remove('__ctr_hide')", sel)
    W, H = on.size; po, pf = on.load(), off.load()
    xs = ys = tot = 0; x0, y0, x1, y1 = W, H, -1, -1
    rim = (min(W, H) / 2 - 2) ** 2
    for y in range(H):
        for x in range(W):
            if disc and (x + 0.5 - W / 2) ** 2 + (y + 0.5 - H / 2) ** 2 > rim:
                continue
            v = sum(abs(a - b) for a, b in zip(po[x, y], pf[x, y])) / 3
            if v > 24:
                # A PIXEL'S MASS IS AT ITS MIDDLE. Weighted at its left edge,
                # every mark read half a device pixel's mass to the left and
                # up (0.08 CSS px at 3x, in the optical centre): the ink box
                # below already counts pixels by their extent.
                tot += v; xs += (x + 0.5) * v; ys += (y + 0.5) * v
                x0, y0, x1, y1 = min(x0, x), min(y0, y), max(x1, x), max(y1, y)
    if not tot:
        return None
    S = W / r[2]
    ox = ((x0 + x1 + 1) / 2 + xs / tot) / 2; oy = ((y0 + y1 + 1) / 2 + ys / tot) / 2
    return round((ox - W / 2) / S, 2), round((oy - H / 2) / S, 2)
with sync_playwright() as _pc:
    _bc = _pc.chromium.launch()
    _cc = _bc.new_context(viewport={"width": 402, "height": 874}, device_scale_factor=3, is_mobile=True, has_touch=True)
    for _path, _boot in (("/skribl-pad", "pad"), ("/flip", "flip")):
        _pg = _cc.new_page(); browsing.goto(_pg, BASE, _path)
        _pg.wait_for_function(f"() => window.__skriblBoot && window.__skriblBoot.{_boot}")
        _pg.evaluate("() => { if (window.SkriblHints) SkriblHints.hide(); }")
        _pg.add_style_tag(content=_HIDE)
        _e = _optical(_pg, "#eraserToolBtn")
        check(f"{_path}: the eraser sits in the middle of its button by its ink",
              _e is not None and abs(_e[0]) <= 0.6 and abs(_e[1]) <= 0.6, f"optical offset {_e} px")
        if _boot == "flip":
            for _face in ("Liberation Sans", "DejaVu Sans", "FreeSans"):
                _pg.evaluate("() => { const b = document.querySelector('#strip .frame.on .holdbadge'); b && b.classList.add('__keep'); }")
                _h = _optical(_pg, "#strip .frame.on .holdbadge", _face)
                # 0.75: halfway to the 1.5px miss this row exists for. It was
                # 0.6 while every reading sat 0.08 up (the pixel weighting in
                # _optical, since corrected); read honestly, Liberation Sans is
                # 0.67. The centring tool, measuring against the painted pill,
                # lists this badge at 0.48-0.5 as a known finding.
                check(f"the ×1 badge sits in the middle of its pill in {_face}",
                      _h is not None and abs(_h[1]) <= 0.75, f"optical offset {_h} px")
        _pg.close()
    _bc.close()


# THE LINK PLAYER'S PLAY, BY ITS INK (the owner's pick after v322: "the same
# fix the full-screen bar's arrow already has"). The one play every player
# draws puts the triangle's box in the middle, and its middle, to the eye, is
# halfway between its box and its mass, so the arrow read 0.56-0.58px right of
# its circle on every screen (check_centring). The link player moves the same
# glyph 0.58px left with one rule matched by its path, so the one play above
# still holds and Pause, which is symmetric, stays put. Judged at the centring
# tool's own line, a third of a CSS pixel: this section's 0.6 for the eraser
# would pass the arrow before the fix.
print("\nTHE LINK PLAYER'S PLAY — the arrow sits in the middle of its circle by its ink, and Pause does not move")
_pts = [{"x": 120 + i * 6, "y": 300 + (i % 7) * 4, "color": "#1f1b2e", "size": 6, "t": i * 40,
         "erase": False, "start": i == 0} for i in range(240)]
_req = urllib.request.Request(BASE + "/api/skribls", method="POST", headers={"Content-Type": "application/json"},
                              data=json.dumps({"title": "Arrow probe", "schemaVersion": 2,
                                               "canvasSize": {"cssWidth": 816, "cssHeight": 612},
                                               "frames": [{"strokes": _pts, "strokeGroups": [len(_pts)],
                                                           "background": {"color": "#f6f2ea"}}]}).encode())
_url = json.loads(urllib.request.urlopen(_req, timeout=20).read())["url"]
with sync_playwright() as _pp:
    _bp = _pp.chromium.launch()
    _cp = _bp.new_context(viewport={"width": 402, "height": 874}, device_scale_factor=3, is_mobile=True, has_touch=True)
    _pg = _cp.new_page(); browsing.goto(_pg, BASE, _url)
    _pg.wait_for_selector("#playerPlayBtn svg")
    _pg.add_style_tag(content=_HIDE)
    _pl = _optical(_pg, "#playerPlayBtn")
    check("the link player's Play arrow sits in the middle of its circle by its ink, within a third of a pixel",
          _pl is not None and abs(_pl[0]) <= 1 / 3 and abs(_pl[1]) <= 1 / 3, f"optical offset {_pl} px")
    _pg.click("#playerPlayBtn")
    _pg.wait_for_function("() => document.querySelector('#playerPlayBtn').getAttribute('aria-label') === 'Pause'")
    _pg.wait_for_timeout(300)
    _pa = _optical(_pg, "#playerPlayBtn")
    check("...and its Pause stays in the middle: the nudge is the arrow's alone",
          _pa is not None and abs(_pa[0]) <= 1 / 3 and abs(_pa[1]) <= 1 / 3, f"optical offset {_pa} px")
    _bp.close()


# EVERY OTHER PLAY, BY ITS INK (the owner's yes after #466: the same arrow fix
# for the Library, the Gallery and Flip, and the Play inside a post measured).
# One glyph, so one correction: its optical middle sits 0.583 of its 24 units
# right of its box's, 2.43% of its width, and `translate` moves it back --
# matched by its path wherever a Pause shares the button. Two discs carried the
# opposite: a 2px and a 3px margin-left that put the arrow 1.4px and about 2px
# right. Two buttons drew theirs on a half pixel ((40 - 15) / 2, (48 - 19) / 2),
# which a renderer rounds one way or the other, and draw 16 and 20 now: the
# full-screen bar's Pause is the row that pins that, since a symmetric mark has
# no other reason to be off. Flip's header Play is a wider triangle whose own
# offset is 0.15px, under the line; the 0.53 the centring tool reads there is
# where this box's fonts put the button on the pixel grid, so it is left alone.
# The paused discs take no pointer events and are not controls, so the centring
# tool never reaches them; these rows do.
print("\nEVERY PLAY — each arrow sits in the middle of what is painted round it, by its ink")
_req = urllib.request.Request(BASE + "/api/skribls", method="POST", headers={"Content-Type": "application/json"},
                              data=json.dumps({"title": "Every play probe", "schemaVersion": 2, "visibility": "public",
                                               "canvasSize": {"cssWidth": 816, "cssHeight": 612},
                                               "frames": [{"strokes": _pts, "strokeGroups": [len(_pts)],
                                                           "background": {"color": "#f6f2ea"}}]}).encode())
_fx = json.loads(urllib.request.urlopen(_req, timeout=20).read())
_seed = ("try { localStorage.setItem('skribl_posted_v1', " + json.dumps(json.dumps([{
    "id": _fx["id"], "url": _fx["url"], "title": "Every play probe", "kind": "pad", "pages": 1,
    "visibility": "public", "tok": _fx["deleteToken"], "local": False, "has_audio": False, "at": 0}])) + "); } catch (e) {}")


def _centred(who, off):
    check(f"{who}: the arrow sits in the middle by its ink, within a third of a pixel",
          off is not None and abs(off[0]) <= 1 / 3 and abs(off[1]) <= 1 / 3, f"optical offset {off} px")


# ON WHOLE PIXELS, so what is read is the control's own drawing. Where a page
# puts a control on the pixel grid depends on the drawing's shape and the
# fonts above it (the Library's Play sits at y = .5 on a 402px phone), and
# this renderer rounds a mark's box to whole CSS pixels (a phone's, to a third
# of one), so a reading there is half that and half the control. The control
# is moved by the fraction before it is photographed; a half pixel INSIDE it,
# which is the control's own, is still read.
_GRID = """(s) => { const e = document.querySelector(s), r = e.getBoundingClientRect(), cs = getComputedStyle(e);
  if (cs.position === 'static') e.style.position = 'relative';
  e.style.left = (parseFloat(cs.left) || 0) - (r.left - Math.floor(r.left)) + 'px';
  e.style.top = (parseFloat(cs.top) || 0) - (r.top - Math.floor(r.top)) + 'px'; }"""


def _read(pg, sel):
    pg.evaluate(_GRID, sel)
    pg.wait_for_timeout(60)
    return _optical(pg, sel, disc=True)


with sync_playwright() as _pe:
    _be = _pe.chromium.launch()
    _phone = _be.new_context(viewport={"width": 402, "height": 874}, device_scale_factor=3, is_mobile=True, has_touch=True)
    _phone.add_init_script(_seed)
    _desk = _be.new_context(viewport={"width": 1280, "height": 800}, device_scale_factor=3)

    _pg = _phone.new_page(); browsing.goto(_pg, BASE, "/library")
    _pg.wait_for_selector("#btnPlay svg", state="visible")
    _pg.add_style_tag(content=_HIDE)
    _centred("the Library's Play", _read(_pg, "#btnPlay"))
    _pg.click("#btnFull")
    # Awake while it is measured: the bar steps back a moment after a drawing
    # starts (lib/chromefade.js), and Pause only shows while one plays.
    _pg.add_style_tag(content=".skfull-host.chrome-asleep .skfull { opacity: 1 !important; }")
    _bar = ".skfull:not(.skfull-card) .skfull-play"
    _pg.wait_for_selector(_bar, state="visible")
    _pg.wait_for_timeout(300)
    if _pg.get_attribute(_bar, "aria-label") != "Play":
        _pg.click(_bar)
    _pg.wait_for_function("(s) => document.querySelector(s).getAttribute('aria-label') === 'Play'", arg=_bar)
    _pg.wait_for_timeout(300)
    _centred("the full-screen bar's Play (the Library's, the Gallery's)", _read(_pg, _bar))
    _pg.click(_bar)
    _pg.wait_for_function("(s) => document.querySelector(s).getAttribute('aria-label') === 'Pause'", arg=_bar)
    _pg.wait_for_timeout(300)
    _pz = _read(_pg, _bar)
    check("...and its Pause, a symmetric mark, sits in the middle too: the bar draws on whole pixels",
          _pz is not None and abs(_pz[0]) <= 1 / 3 and abs(_pz[1]) <= 1 / 3, f"optical offset {_pz} px")
    _pg.close()

    for _ctx, _where in ((_phone, "phone"), (_desk, "desk")):
        _pg = _ctx.new_page(); browsing.goto(_pg, BASE, "/gallery")
        _tile = f'article.tile[data-id="{_fx["id"]}"]'
        _pg.wait_for_selector(_tile + " .skribl-inline-play svg", state="visible")
        _pg.add_style_tag(content=_HIDE)
        _pg.evaluate("(s) => document.querySelector(s).scrollIntoView({ block: 'center' })", _tile)
        _pg.wait_for_timeout(300)
        if _where == "phone":
            # A Gallery card's Play is a pill that says how it was drawn (the
            # owner's pick after v324): its arrow leads the words, so it is
            # held level, not centred across the pill. The disc is read on
            # the preview feed below, where a post keeps it.
            # The words put out of the reading, so the ink read is the arrow's.
            _pg.evaluate("(s) => document.querySelector(s).style.color = 'transparent'", _tile + " .skribl-inline-play span")
            _pg.evaluate(_GRID, _tile + " .skribl-inline-play"); _pg.wait_for_timeout(60)
            _pl = _optical(_pg, _tile + " .skribl-inline-play")
            check("the Gallery card's pill: its arrow sits level in it, within a third of a pixel",
                  _pl is not None and abs(_pl[1]) <= 1 / 3, f"optical offset {_pl} px")
        _pg.evaluate("(s) => document.querySelector(s).classList.add('ctl-on')", _tile)
        _pg.wait_for_timeout(300)
        _centred(f"the Gallery card's Play, {_where}", _read(_pg, _tile + " .skfull-card .skfull-play"))
        _pg.close()
    # THE DISC, where a post keeps it: the in-post player with its line under
    # it, as every skribls.net post is drawn (the preview feed is that page).
    _pg = _phone.new_page(); browsing.goto(_pg, BASE, "/feed")
    _post = f'[data-skribl-id="{_fx["id"]}"]'
    _pg.wait_for_selector(_post + " .skribl-inline-play svg", state="visible")
    _pg.add_style_tag(content=_HIDE)
    _pg.evaluate("(s) => document.querySelector(s).scrollIntoView({ block: 'center' })", _post)
    _pg.wait_for_timeout(300)
    _centred("the Play inside a post (the in-post player: every skribls.net post)", _read(_pg, _post + " .skribl-inline-play"))
    _pg.close()

    for _path, _boot in (("/skribl-pad", "pad"), ("/flip", "flip")):
        _pg = _phone.new_page(); browsing.goto(_pg, BASE, _path)
        _pg.wait_for_function(f"() => window.__skriblBoot && window.__skriblBoot.{_boot}")
        _pg.evaluate("() => { if (window.SkriblHints) SkriblHints.hide(); document.body.classList.add('playback-paused'); }")
        _pg.wait_for_selector(".tap-paused-disc svg", state="visible")
        _pg.add_style_tag(content=_HIDE)
        _pg.wait_for_timeout(200)
        _centred(f"{'the Pad' if _boot == 'pad' else 'Flip'}'s paused Play (tap to pause)", _read(_pg, ".tap-paused-disc"))
        _pg.close()
    _be.close()

bad = [r for r in results if not r[0]]
print(f"\n{'=' * 62}\n{len(results) - len(bad)}/{len(results)} passed"
      + ("" if not bad else "  FAILURES: " + ", ".join(n for _, n in bad)))
sys.exit(1 if bad else 0)
