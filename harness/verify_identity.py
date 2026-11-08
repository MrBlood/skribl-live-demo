"""SK-AUD-013 — the app has an identity to a browser and a Home Screen.

The acquisition audit of v302 added Skribl to an iPhone's Home Screen and got
a screenshot for an icon, a browser-default splash and the OS's chrome colour
around a page that had chosen its own: no web app manifest, no touch icon, no
theme-color anywhere on the principal pages. The share card had been an
identity for a LINK since v102; the pages had none for themselves.

What ships: one route, `/manifest.webmanifest` (a route, not a static file,
so its URLs follow the blueprint's mount point), three PNG icons (since v320,
Blooby waving on lilac, drawn by `harness/tools/blooby.py icon`; since the third
icon round, standing on the owner's white star), and one partial (`_skribl_app_identity.html`) that the Pad,
Flip, the player and the library include and the feed -- a host's page that is
not Skribl -- does not. The theme-color meta carries BOTH grounds as data-
attributes, so the theme boot (before first paint) and lib/theme.js (on a
switch) re-stamp it without holding a colour of their own, and the browser's
chrome follows the page's theme rather than the OS's alone.

HOW IT IS PINNED. Every URL the manifest and the pages emit is FETCHED and
its bytes decoded: an icon is a PNG of the size its tag declares, or the
manifest is describing a file that is not there. The two grounds in
skribl.core.THEME_GROUND are compared with the stylesheet's own --surface-base
in each ramp, so the Python copy cannot drift from the CSS. The feed's absence
is asserted as well as the four pages' presence -- a partial that leaked into
the host demo would pass a presence-only census. And the theme follow is
driven live: a page opened with light stored reads the light ground before
any deferred script has run, and switching from the library flips it back.

Calibrated on the tree before the fix (every page pin red, the route 404)
and on: the partial dropped from one page; the manifest naming an icon that
is not there; THEME_GROUND['light'] typed wrong; the boot's re-stamp removed;
theme.js's re-stamp removed; the partial included by the feed.
"""
import io
import json
import os
import pathlib
import re
import sys
import urllib.error
import urllib.request
from assertions import make_check

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
BASE = os.environ.get("SKRIBL_BASE", "http://127.0.0.1:5001")

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("SKIP: playwright is not installed")
    sys.exit(0)
try:
    from PIL import Image
except ImportError:
    print("SKIP: Pillow is not installed")
    sys.exit(0)

import browsing  # noqa: E402

results = []
check = make_check(results)


def get(path):
    """(status, headers, bytes) for a GET; a 4xx/5xx is a status, not a crash."""
    url = path if path.startswith("http") else BASE + path
    try:
        with urllib.request.urlopen(url, timeout=20) as r:
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), b""


def png_size(data):
    try:
        im = Image.open(io.BytesIO(data))
        return im.format, im.size
    except Exception:            # noqa: BLE001 -- not an image is the finding
        return None, None


from skribl.core import THEME_GROUND  # noqa: E402

# --------------------------------------------------------------------------
print("IDENTITY — the grounds in Python are the stylesheet's, not a second copy")
css = (ROOT / "skribl" / "static" / "styles.css").read_text(encoding="utf-8")
bases = re.findall(r"--surface-base:\s*(#[0-9a-fA-F]{6})", css)
check("styles.css declares --surface-base in two ramps", len(bases) >= 2, str(bases))
check("THEME_GROUND['dark'] is the dark ramp's --surface-base",
      bases and THEME_GROUND["dark"].lower() == bases[0].lower(),
      f"{THEME_GROUND['dark']} vs {bases[:1]}")
check("THEME_GROUND['light'] is the light ramp's --surface-base",
      len(bases) >= 2 and THEME_GROUND["light"].lower() == bases[1].lower(),
      f"{THEME_GROUND['light']} vs {bases[1:2]}")

# --------------------------------------------------------------------------
print("\nIDENTITY — the manifest is served, and everything it names is there")
st, hdr, raw = get("/manifest.webmanifest")
check("GET /manifest.webmanifest is 200", st == 200, str(st))
check("...as application/manifest+json",
      "manifest+json" in hdr.get("Content-Type", ""), hdr.get("Content-Type", ""))
try:
    man = json.loads(raw or b"{}")
except ValueError:
    man = {}
check("it names the app", man.get("name") == "Skribl" and bool(man.get("short_name")),
      json.dumps({k: man.get(k) for k in ("name", "short_name")}))
check("it opens standalone", man.get("display") == "standalone", str(man.get("display")))
st_start, _, _ = get(man.get("start_url", "/nowhere"))
check("its start_url is a page that serves", st_start == 200,
      f"{man.get('start_url')} -> {st_start}")
check("its scope contains its start_url",
      isinstance(man.get("scope"), str) and str(man.get("start_url", "")).startswith(man["scope"]),
      f"scope {man.get('scope')!r} start {man.get('start_url')!r}")
check("its colours are the page's dark ground",
      man.get("theme_color") == THEME_GROUND["dark"]
      and man.get("background_color") == THEME_GROUND["dark"],
      json.dumps({k: man.get(k) for k in ("theme_color", "background_color")}))
icons = man.get("icons") or []
check("it carries at least a 192 and a 512 icon",
      {i.get("sizes") for i in icons} >= {"192x192", "512x512"},
      str([i.get("sizes") for i in icons]))
for ic in icons:
    st_i, hdr_i, data = get(ic.get("src", "/nowhere"))
    fmt, size = png_size(data)
    want = tuple(int(n) for n in str(ic.get("sizes", "0x0")).split("x"))
    check(f"icon {ic.get('sizes')} is served as the PNG it declares",
          st_i == 200 and "image/png" in hdr_i.get("Content-Type", "")
          and fmt == "PNG" and size == want,
          f"{ic.get('src')} -> {st_i} {hdr_i.get('Content-Type')} {fmt} {size}")

# --------------------------------------------------------------------------
print("\nIDENTITY — the icon is Blooby, waving on a white star, on lilac that deepens to its edge")
# THE OWNER'S PICK (v320): Blooby waving on a lilac tile, option J of the mocks,
# drawn from his strokes by `harness/tools/blooby.py icon`. The checks above
# hold an icon to its size and format and would pass on a blank square, or on
# the wordmark it replaced. These read the PIXELS: the tile at all four corners
# is the lilac blooby.py names, his body's purple covers a real share of it, and
# his dark outline is there. The tile colour is read from blooby.py, the one
# place it is written.
# THE STAR (owner, the third icon round: "Soft white. And premium"): he stands
# on the six-point star of the owner's star icon, in white, its points running
# off the tile. So the top centre, which used to be ground all the way down, is
# now the star's top point, and the ground's deepening is read where the lilac
# still runs in from the edge: the wedge between two points at the middle of
# the left edge, clear of his arm.
_bsrc = (ROOT / "harness" / "tools" / "blooby.py").read_text(encoding="utf-8")
_m_tile = re.search(r'^ICON_TILE = "(#[0-9a-fA-F]{6})"', _bsrc, re.M)
TILE = tuple(int(_m_tile.group(1)[i:i + 2], 16) for i in (1, 3, 5)) if _m_tile else None
check("blooby.py names the icon's tile colour", TILE is not None)
# ...AND ITS EDGE (owner, N4): the lilac deepens toward the tile's edge, so the
# corners are ICON_EDGE, and the ground is lighter -- nearer the lilac -- the
# further in it is read. Both colours are read from blooby.py.
_m_edge = re.search(r'^ICON_EDGE = "(#[0-9a-fA-F]{6})"', _bsrc, re.M)
EDGE = tuple(int(_m_edge.group(1)[i:i + 2], 16) for i in (1, 3, 5)) if _m_edge else None
check("blooby.py names the colour the tile deepens to", EDGE is not None)
_near = lambda a, b, tol: all(abs(x - y) <= tol for x, y in zip(a, b))
_srcs = [ic.get("src") for ic in icons]
_st_p, _, _pad = get("/skribl-pad")
_m_t = re.search(r'<link[^>]+rel="apple-touch-icon"[^>]+href="([^"]+)"', _pad.decode("utf-8", "replace"))
if _m_t:
    _srcs.append(_m_t.group(1))
for _src in _srcs:
    _st, _, _data = get(_src or "/nowhere")
    try:
        _im = Image.open(io.BytesIO(_data)).convert("RGB")
    except Exception:            # noqa: BLE001 -- not an image is the finding
        check(f"{_src}: decodes", False)
        continue
    _w, _h = _im.size
    _corners = [_im.getpixel(xy) for xy in ((1, 1), (_w - 2, 1), (1, _h - 2), (_w - 2, _h - 2))]
    _raw = _im.tobytes()        # RGB triples; getdata() is deprecated in Pillow 12
    _px = [tuple(_raw[i:i + 3]) for i in range(0, len(_raw), 3)]
    _body = sum(1 for c in _px if _near(c, (124, 92, 255), 45)) / len(_px)
    _ink = sum(1 for c in _px if sum(c) < 200) / len(_px)
    _name = _src.split("/")[-1].split("?")[0]
    # Beside him, at the middle of the left edge, the tile is ground a fifth of the way in.
    _col = [_im.getpixel((round(_w * f), _h // 2)) for f in (0.01, 0.05, 0.10)]
    _lum = [sum(c) for c in _col]
    # Above his head, at the top centre, is the star's top point.
    _top = [_im.getpixel((_w // 2, round(_h * f))) for f in (0.02, 0.08, 0.15)]
    check(f"{_name}: the tile deepens to the edge colour at every corner",
          EDGE is not None and all(_near(c, EDGE, 8) for c in _corners), f"corners {_corners}")
    check(f"{_name}: ...and lightens toward the middle, staying lilac",
          TILE is not None and _lum[0] < _lum[1] < _lum[2]
          and all(c[2] > max(c[0], c[1]) for c in _col), f"left edge inward {_col}")
    check(f"{_name}: he stands on the owner's white star -- its top point is above his head",
          all(min(c) >= 245 for c in _top), f"top centre downward {_top}")
    check(f"{_name}: Blooby is on it -- his purple body and his dark outline",
          _body > 0.15 and _ink > 0.01, f"body {_body:.1%}, outline {_ink:.1%}")

# --------------------------------------------------------------------------
print("\nIDENTITY — every principal page carries it, and the host demo does not")
_body = {"title": "identity fixture", "payload": {"v": 1, "canvas": {"w": 100, "h": 100},
                                                  "strokes": []}}
_req = urllib.request.Request(BASE + "/api/skribls", data=json.dumps(_body).encode(),
                              headers={"Content-Type": "application/json"})
with urllib.request.urlopen(_req) as _r:
    _pid = json.loads(_r.read())["id"]

TAG_MANIFEST = re.compile(r'<link[^>]+rel="manifest"[^>]+href="([^"]+)"')
TAG_THEME = re.compile(r'<meta[^>]+name="theme-color"[^>]+content="([^"]+)"')
TAG_TOUCH = re.compile(r'<link[^>]+rel="apple-touch-icon"[^>]+href="([^"]+)"')
TAG_ICON = re.compile(r'<link[^>]+rel="icon"[^>]+href="([^"]+)"')

for path, label in (("/skribl-pad", "Pad"), ("/flip", "Flip"),
                    (f"/s/{_pid}", "the player"), ("/library", "the library"),
                    ("/gallery", "the gallery")):
    st_p, _, html = get(path)
    html = html.decode("utf-8", "replace")
    m_man, m_thm = TAG_MANIFEST.search(html), TAG_THEME.search(html)
    m_tch, m_ico = TAG_TOUCH.search(html), TAG_ICON.search(html)
    check(f"{label} links the manifest", st_p == 200 and bool(m_man), f"{path} -> {st_p}")
    if m_man:
        st_m, hdr_m, _ = get(m_man.group(1))
        check(f"{label}: ...and the link resolves to it",
              st_m == 200 and "manifest+json" in hdr_m.get("Content-Type", ""),
              f"{m_man.group(1)} -> {st_m}")
    check(f"{label} declares the dark ground as its theme-color",
          bool(m_thm) and m_thm.group(1) == THEME_GROUND["dark"],
          m_thm.group(1) if m_thm else "no theme-color meta")
    for name, m in (("apple-touch-icon", m_tch), ("icon", m_ico)):
        if not m:
            check(f"{label} carries an {name}", False, "tag absent")
            continue
        st_i, hdr_i, data = get(m.group(1))
        fmt, size = png_size(data)
        check(f"{label}'s {name} is a PNG that serves",
              st_i == 200 and fmt == "PNG" and size and size[0] >= 180,
              f"{m.group(1)} -> {st_i} {fmt} {size}")

st_f, _, feed = get("/feed")
feed = feed.decode("utf-8", "replace")
check("the feed — a host's page — carries NONE of it",
      st_f == 200 and not TAG_MANIFEST.search(feed) and not TAG_THEME.search(feed)
      and not TAG_TOUCH.search(feed),
      "a partial that reached the host demo would pass a presence-only census")

# --------------------------------------------------------------------------
print("\nIDENTITY — the browser's chrome follows the page's theme, before paint and on a switch")
with sync_playwright() as p:
    b = p.chromium.launch()
    # LIGHT STORED, OS DARK: the boot must re-stamp the meta before first
    # paint, exactly as it stamps data-theme. Read the moment <body> APPEARS,
    # through a MutationObserver armed by an init script -- NOT at
    # DOMContentLoaded, which fires AFTER every deferred script has run, so
    # lib/theme.js had already re-stamped it and the first version of this
    # pin stayed green with the boot's re-stamp deleted (the calibration run
    # said so; a check that cannot go red is not a check). When <body> is
    # parsed the <head> is complete and no deferred script has run yet.
    ctx = b.new_context(color_scheme="dark")
    ctx.add_init_script("""(() => {
      try { localStorage.setItem('skribl_theme_v1', 'light'); } catch (e) {}
      const mo = new MutationObserver(() => {
        if (!document.body) return;
        const m = document.querySelector('meta[name="theme-color"]');
        window.__themeColorAtBody = m ? m.content : null;
        mo.disconnect();
      });
      mo.observe(document, { childList: true, subtree: true });
    })();""")
    pg = ctx.new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    browsing.goto(pg, BASE, "/skribl-pad")
    early = pg.evaluate("() => window.__themeColorAtBody")
    check("with light stored, the Pad's theme-color is the light ground before any deferred script",
          early == THEME_GROUND["light"], f"{early!r} as <body> was parsed")
    check("...and data-theme was stamped light alongside it",
          pg.evaluate("() => document.documentElement.getAttribute('data-theme')") == "light")
    # THE SWITCH, through the library the theme control drives.
    pg.evaluate("() => window.SkriblTheme.set('dark')")
    now = pg.evaluate("() => document.querySelector('meta[name=\"theme-color\"]').content")
    check("switching to dark re-stamps it to the dark ground",
          now == THEME_GROUND["dark"], repr(now))
    pg.evaluate("() => window.SkriblTheme.set('light')")
    now = pg.evaluate("() => document.querySelector('meta[name=\"theme-color\"]').content")
    check("...and back to light re-stamps the light ground", now == THEME_GROUND["light"], repr(now))
    check("no page errors", not errs, "; ".join(errs[:2]))
    ctx.close()

    # GETTING ONTO THE HOME SCREEN (owner, mocks H1 + H2). The icon above is
    # what a person gets; this is how they find the way to it, since an iPhone
    # never offers. lib/homescreen.js decides who sees what, so each case is a
    # device: an iPhone tab sees the banner and the row, the same iPhone with
    # Skribl already on its Home Screen sees neither, and a desktop sees
    # neither. Visibility is asked of the paint (elementFromPoint), not a rect.
    print("\nADD TO HOME SCREEN — who is told, and how")
    _IPHONE = ("Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 "
               "(KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1")
    _PAINTED = """(id) => { const e = document.getElementById(id); if (!e || e.hidden) return false;
        const r = e.getBoundingClientRect(); if (!r.width) return false;
        const h = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
        return !!(h && e.contains(h)); }"""

    def _tap(page_, id_):
        """Press a control only if it is really there to press, so a tree where
        it is missing reports each later check red instead of hanging on a
        click that can never land and printing nothing."""
        if page_.evaluate(_PAINTED, id_):
            page_.click("#" + id_)
            page_.wait_for_timeout(500)

    def _phone(standalone=False):
        c = b.new_context(viewport={"width": 390, "height": 844}, is_mobile=True,
                          has_touch=True, user_agent=_IPHONE)
        if standalone:
            c.add_init_script("Object.defineProperty(navigator, 'standalone', { get: () => true });")
        return c

    hc = _phone()
    hp = hc.new_page()
    herr = []
    hp.on("pageerror", lambda e: herr.append(str(e)))
    browsing.goto(hp, BASE, "/skribl-pad")
    hp.wait_for_timeout(1700)
    check("an iPhone tab on the Pad is shown the Home Screen card",
          hp.evaluate(_PAINTED, "homeScreenBanner"))
    _tb = hp.evaluate("""() => { const a = document.getElementById('homeScreenBanner').getBoundingClientRect(),
        t = document.getElementById('toolBar').getBoundingClientRect(); return [a.bottom, t.top]; }""")
    check("...sitting above the tools, not over them", _tb[0] <= _tb[1], str(_tb))
    _tap(hp, "homeScreenBannerOpen")
    _steps = hp.evaluate("() => [...document.querySelectorAll('#homeScreenSteps .hs-list li')].map(l => l.textContent.replace(/\\s+/g, ' ').trim())")
    check("...and tapping it opens the steps: Share, Add to Home Screen, Add",
          hp.evaluate(_PAINTED, "homeScreenSteps") and len(_steps) == 3
          and "Share" in _steps[0] and "Add to Home Screen" in _steps[1] and _steps[2] == "Tap Add",
          str(_steps))
    hp.keyboard.press("Escape")
    hp.wait_for_timeout(300)
    browsing.goto(hp, BASE, "/skribl-pad")
    hp.wait_for_timeout(1700)
    check("...and the card is once: put away, it does not come back on the next visit",
          not hp.evaluate(_PAINTED, "homeScreenBanner"))
    hp.click("#menuBtn")
    hp.wait_for_timeout(700)
    check("the ⋯ menu keeps an Add to Home Screen row for later",
          hp.evaluate(_PAINTED, "homeScreenItem"))
    _tap(hp, "homeScreenItem")
    check("...which closes the menu and opens the same steps",
          hp.evaluate(_PAINTED, "homeScreenSteps"))
    _tap(hp, "homeScreenDone")
    browsing.goto(hp, BASE, "/flip")
    hp.click("#moreBtn")
    hp.wait_for_timeout(700)
    check("Flip's ⋯ menu has the row too", hp.evaluate(_PAINTED, "homeScreenItem"))
    check("...and no card on Flip, which a person reaches from the Pad",
          hp.locator("#homeScreenBanner").count() == 0)
    check("no page errors on an iPhone", not herr, "; ".join(herr[:2]))
    hc.close()

    hc = _phone()
    hp = hc.new_page()
    browsing.goto(hp, BASE, "/skribl-pad")
    hp.wait_for_timeout(1700)
    _bb = hp.locator("#canvas").bounding_box()
    hp.mouse.move(_bb["x"] + 60, _bb["y"] + 80)
    hp.mouse.down()
    hp.mouse.move(_bb["x"] + 160, _bb["y"] + 120)
    hp.mouse.up()
    hp.wait_for_timeout(300)
    check("drawing under the card puts it away for good",
          not hp.evaluate(_PAINTED, "homeScreenBanner")
          and hp.evaluate("() => localStorage.getItem('skribl_homescreen_hint_v1')") == "1")
    hc.close()

    hc = _phone(standalone=True)
    hp = hc.new_page()
    browsing.goto(hp, BASE, "/skribl-pad")
    hp.wait_for_timeout(1700)
    hp.click("#menuBtn")
    hp.wait_for_timeout(700)
    check("already on the Home Screen: no card and no row",
          not hp.evaluate(_PAINTED, "homeScreenBanner") and not hp.evaluate(_PAINTED, "homeScreenItem"))
    hc.close()

    hc = b.new_context(viewport={"width": 1280, "height": 900})
    hp = hc.new_page()
    browsing.goto(hp, BASE, "/skribl-pad")
    hp.wait_for_timeout(1700)
    hp.click("#menuBtn")
    hp.wait_for_timeout(700)
    check("a desktop is told nothing: no card and no row",
          not hp.evaluate(_PAINTED, "homeScreenBanner") and not hp.evaluate(_PAINTED, "homeScreenItem"))
    browsing.goto(hp, BASE, "/skribl-pad?compose=1")
    check("...and an editor opened from a composer carries none of it",
          hp.locator("#homeScreenItem, #homeScreenBanner, #homeScreenSteps").count() == 0)
    hc.close()
    b.close()

# --------------------------------------------------------------------------
print("\nBLOOBY AROUND THE APP — the words alone on an empty canvas, Blooby thinking where something can't be shown")
# THE OWNER'S PICKS from the Blooby mock: where a link's drawing can't be
# shown, and where the Library's list didn't load, Blooby thinking, his
# question mark, where the circled ! and the crossed cloud were. Each is the
# badge blooby.py draws, the Home Screen icon in small with the whole star, so
# his own lilac comes with him onto any ground. Asked of what is PAINTED: the
# share of the picture's box that is his lilac and purple, in a screenshot.
# THE EMPTY CANVAS HAS THE WORDS AND NO PICTURE: Blooby with his pen stood
# above them (#474) until the owner took him off after v323 ("It's too much"),
# on the Pad and Flip; since the owner's pick after the "Empty canvas ideas"
# mock, your hand writes them (YOUR HAND WRITES THE WORDS, below), and that
# drawing of the words is the only svg the hint holds. Asked of the hint itself
# (no other picture in it), of its words' place (the canvas's middle; 40px
# below it while he stood there) and of their ink once written, in a
# screenshot: the hint takes no pointer events, so elementFromPoint sees
# straight through it. They leave at the first stroke.
_SHOWN = """(sel) => { const i = document.querySelector(sel); if (!i) return null;
    i.scrollIntoView({ block: 'center' }); const r = i.getBoundingClientRect();
    return { src: (i.getAttribute('src') || '').split('?')[0].split('/').pop(),
             box: [r.left, r.top, r.width, r.height], done: i.complete && i.naturalWidth > 0 }; }"""


def _lilac(pg, box):
    """The share of `box` painted in the badge's colours: blue over red and green."""
    if not box or box[2] < 8 or box[3] < 8:
        return 0.0
    shot = Image.open(io.BytesIO(pg.screenshot(clip={"x": box[0], "y": box[1], "width": box[2], "height": box[3]}))).convert("RGB")
    raw = shot.tobytes()
    px = [raw[i:i + 3] for i in range(0, len(raw), 3)]
    return sum(1 for r, g, b_ in px if b_ > r + 12 and b_ > g + 12) / max(1, len(px))


# The empty canvas's words: no picture among them, where they sit against the
# canvas's middle, and their box to look for ink in.
_HINT = """(o) => { const h = document.getElementById(o.hint), c = document.querySelector(o.cv); if (!h || !c) return null;
    const cr = c.getBoundingClientRect(), r = [...h.querySelectorAll('span')].map(s => s.getBoundingClientRect()).filter(x => x.width);
    const pics = h.querySelectorAll('img, svg:not(.canvas-empty-hand), picture').length;
    if (!r.length) return { pictures: pics, off: null, box: null };
    const top = Math.min(...r.map(x => x.top)), bot = Math.max(...r.map(x => x.bottom));
    const left = Math.min(...r.map(x => x.left)), right = Math.max(...r.map(x => x.right));
    return { pictures: pics,
             off: Math.round((top + bot) / 2 - (cr.top + cr.height / 2)), box: [left, top, right - left, bot - top] }; }"""


def _written(pg, timeout=8000):
    """Once your hand has written the words (lib/handwords.js), or at once where it has not."""
    try:
        pg.wait_for_function("""() => { const s = document.querySelector('.canvas-empty-hand');
            return !s || s.getAttribute('data-state') === 'done'; }""", timeout=timeout)
    except Exception:
        pass
    pg.wait_for_timeout(200)


def _inked(pg, box):
    """The share of `box` that differs from its own commonest colour: words painted there, or not."""
    if not box or box[2] < 8 or box[3] < 8:
        return 0.0
    shot = Image.open(io.BytesIO(pg.screenshot(clip={"x": box[0], "y": box[1], "width": box[2], "height": box[3]}))).convert("RGB")
    ground = max(shot.getcolors(1 << 20), key=lambda c: c[0])[1]
    raw = shot.tobytes()
    px = [raw[i:i + 3] for i in range(0, len(raw), 3)]
    return sum(1 for q in px if sum(abs(q[k] - ground[k]) for k in range(3)) > 60) / max(1, len(px))


with sync_playwright() as p:
    b = p.chromium.launch()
    for theme in ("light", "dark"):
        c = b.new_context(viewport={"width": 402, "height": 874}, color_scheme=theme)
        pg = c.new_page()
        browsing.goto(pg, BASE, "/skribl-pad")
        pg.evaluate("() => window.SkriblHints && window.SkriblHints.hide && window.SkriblHints.hide()")
        _written(pg)
        s = pg.evaluate(_HINT, {"hint": "canvasEmptyHint", "cv": "#canvas"})
        ink = _inked(pg, s and s["box"])
        check(f"Pad, {theme}: 'Draw anything' on the empty canvas, no other picture, painted at its middle",
              bool(s) and s["pictures"] == 0 and s["off"] is not None and abs(s["off"]) <= 3 and ink > 0.02,
              f"{s} ink {ink:.1%}")
        if theme == "light":
            cv = pg.locator("#canvas").bounding_box()
            pg.mouse.move(cv["x"] + cv["width"] * 0.15, cv["y"] + cv["height"] * 0.12)
            pg.mouse.down()
            for k in range(1, 9):
                pg.mouse.move(cv["x"] + cv["width"] * (0.15 + 0.03 * k), cv["y"] + cv["height"] * 0.12)
            pg.mouse.up()
            pg.wait_for_timeout(700)
            after = _inked(pg, s and s["box"])
            check("Pad: ...and the words leave at the first stroke",
                  bool(s) and s["box"] is not None and after < 0.005, f"ink {after:.1%} after a stroke")
        c.close()
    c = b.new_context(viewport={"width": 402, "height": 874}, color_scheme="light")
    pg = c.new_page()
    browsing.goto(pg, BASE, "/flip")
    pg.evaluate("() => window.SkriblHints && window.SkriblHints.hide && window.SkriblHints.hide()")
    _written(pg)
    s = pg.evaluate(_HINT, {"hint": "flipEmptyHint", "cv": "#pad"})
    ink = _inked(pg, s and s["box"])
    check("Flip: 'Draw page 1' the same way, no other picture, painted at the canvas's middle",
          bool(s) and s["pictures"] == 0 and s["off"] is not None and abs(s["off"]) <= 3 and ink > 0.02,
          f"{s} ink {ink:.1%}")
    c.close()
    for theme in ("light", "dark"):
        c = b.new_context(viewport={"width": 402, "height": 874}, color_scheme=theme)
        pg = c.new_page()
        browsing.goto(pg, BASE, f"/s/not-a-real-id?theme={theme}", require_boot=False)
        pg.wait_for_selector("#playerError:not([hidden])", timeout=10000)
        pg.wait_for_timeout(300)
        s = pg.evaluate(_SHOWN, "#playerError img")
        share = _lilac(pg, s and s["box"])
        check(f"a link whose drawing isn't there, {theme}: Blooby thinking above the words, painted",
              bool(s) and s["src"] == "blooby-think.webp" and s["done"] and share > 0.5, f"{s} lilac {share:.0%}")
        c.close()
    # The Library's list not answering: a signed-in page (the host's user) whose
    # listing is refused -- the path verify_library drives for its words.
    c = b.new_context(viewport={"width": 402, "height": 874}, color_scheme="light")
    c.route("**/api/skribls?**", lambda r: r.fulfill(status=503, body="{}", content_type="application/json"))

    def _signed_in(route):
        r = route.fetch()
        route.fulfill(response=r, body=r.text().replace('data-skribl-me=""', 'data-skribl-me="identity-user"'))
    c.route("**/library**", _signed_in)
    pg = c.new_page()
    browsing.goto(pg, BASE, "/library", require_boot=False)
    pg.wait_for_selector("#stageError:not([hidden])", timeout=10000)
    pg.wait_for_timeout(300)
    s = pg.evaluate(_SHOWN, "#stageError img")
    share = _lilac(pg, s and s["box"])
    check("the Library when its list didn't load: the same thinking Blooby, painted",
          bool(s) and s["src"] == "blooby-think.webp" and s["done"] and share > 0.5, f"{s} lilac {share:.0%}")
    c.close()
    b.close()

print("\nYOUR HAND WRITES THE WORDS — on an empty canvas, every time; the snail once in a site's post box")
# The owner's pick after the "Empty canvas ideas" mock ("Go, all yes";
# lib/handwords.js): "Draw anything" (Flip: "Draw page 1") writes itself in the
# owner's own hand, recorded through the real Text tool
# (harness/tools/make_handwords.py), every time the words appear, and the
# first stroke un-writes it. Asked of the drawing's own path and state (it
# grows while it writes), of what is PAINTED in its box (a screenshot), of its
# colour against the words' and of the words a screen reader is given. In a
# site's post box, once on a device, How it works' snail (Flip: the ball) draws
# itself faintly above them; automation meets it only when it asks
# (window.__skriblOnceForce), as with the hello.
_HAND = """() => { const h = document.getElementById('canvasEmptyHint') || document.getElementById('flipEmptyHint');
    const s = h && h.querySelector('svg.canvas-empty-hand'); if (!s) return null;
    const p = s.querySelector('path'), r = s.getBoundingClientRect(), said = h.firstElementChild.querySelector('.vis-hidden');
    return { state: s.getAttribute('data-state'), d: (p.getAttribute('d') || '').length, box: [r.left, r.top, r.width, r.height],
             said: said ? said.textContent.trim() : null, aria: s.getAttribute('aria-hidden'),
             stroke: getComputedStyle(p).stroke, words: getComputedStyle(h.firstElementChild).color,
             hidden: h.classList.contains('hidden'), opacity: +getComputedStyle(h).opacity }; }"""
_ONCE = """() => { const o = document.getElementById('hintOnce'); if (!o) return null; const r = o.getBoundingClientRect();
    const t = (document.getElementById('canvasEmptyHint') || document.getElementById('flipEmptyHint')).firstElementChild.getBoundingClientRect();
    const cv = (document.getElementById('canvas') || document.getElementById('pad')).getBoundingClientRect();
    const b = o.querySelector('.skribl-inline'), pl = b && b._skriblInline, st = pl ? pl.state() : null;
    return { on: o.classList.contains('is-on'), hidden: o.hidden, opacity: +getComputedStyle(o).opacity,
             box: [r.left, r.top, r.width, r.height], above: Math.round(t.top - r.bottom),
             centre: Math.round((r.left + r.width / 2) - (cv.left + cv.width / 2)),
             src: (o.getAttribute('data-src') || '').split('?')[0].split('/').pop(),
             player: st ? { state: st.state, at: Math.round(st.elapsedMs), total: Math.round(st.totalMs) } : null }; }"""
_FIRST_LOOK = """() => { const s = document.querySelector('.canvas-empty-hand'), o = document.getElementById('hintOnce');
    return [s && s.getAttribute('data-state'), !!o && o.classList.contains('is-on')]; }"""


def _rewrite(pg):
    """The words hide and show again, as the editors do it (the class they set):
    your hand writes them from the start. Two steps, so the module sees both."""
    h = "(document.getElementById('canvasEmptyHint') || document.getElementById('flipEmptyHint'))"
    pg.evaluate(f"() => {h}.classList.add('hidden')")
    pg.wait_for_timeout(60)
    pg.evaluate(f"() => {h}.classList.remove('hidden')")


def _scribble(pg, sel, q=None):
    """A short stroke low on the canvas, as a finger would make it (`q`: the frame it is in)."""
    cv = (q or pg).locator(sel).bounding_box()
    x, y = cv["x"] + cv["width"] * 0.25, cv["y"] + cv["height"] * 0.8
    pg.mouse.move(x, y); pg.mouse.down()
    for k in range(1, 10):
        pg.mouse.move(x + cv["width"] * 0.05 * k, y - 3 * k)
    pg.mouse.up()


def _compose(pg, ed="pad"):
    """A site's post box (/feed's composer), the Pad in its frame, or Flip as the Pad's own row takes it there."""
    browsing.goto(pg, BASE, "/feed")
    pg.click("#padBtn")
    pg.wait_for_function("() => { const f = document.getElementById('padFrame'); const w = f && f.contentWindow;"
                         " return !!(w && w.__skriblBoot && w.__skriblBoot.pad); }", timeout=30000)
    fr = next(f for f in pg.frames if "compose=1" in f.url)
    if ed == "flip":
        fr.evaluate("() => { location.href = '/flip?compose=1'; }")
        pg.wait_for_function("() => { const w = document.getElementById('padFrame').contentWindow;"
                             " return !!(w && w.__skriblBoot && w.__skriblBoot.flip && /flip/.test(w.location.pathname)); }", timeout=30000)
        fr = next(f for f in pg.frames if "/flip" in f.url and "compose=1" in f.url)
    return fr


def _in_page(pg, box):
    """A box in the post box's frame, where it is on the page."""
    if not box:
        return None
    f = pg.evaluate("() => { const r = document.getElementById('padFrame').getBoundingClientRect(); return [r.left, r.top]; }")
    return [box[0] + f[0], box[1] + f[1], box[2], box[3]]


def _first_look(pg, fr):
    """The words' state and the snail's, every 50 ms until the snail shows."""
    seq = []
    for _ in range(200):
        seq.append(tuple(fr.evaluate(_FIRST_LOOK)))
        if seq[-1][1]:
            break
        pg.wait_for_timeout(50)
    return seq


with sync_playwright() as p:
    b = p.chromium.launch()
    for route, name, sel, words in (("/skribl-pad", "Pad", "#canvas", "Draw anything"), ("/flip", "Flip", "#pad", "Draw page 1")):
        c = b.new_context(viewport={"width": 402, "height": 874}, color_scheme="dark")
        pg = c.new_page()
        browsing.goto(pg, BASE, route)
        pg.evaluate("() => window.SkriblHints && window.SkriblHints.hide && window.SkriblHints.hide()")
        _written(pg)
        _rewrite(pg)
        pg.wait_for_timeout(400)
        early = pg.evaluate(_HAND)
        _written(pg)
        late = pg.evaluate(_HAND)
        painted = _inked(pg, late and late["box"])
        check(f"{name}: your hand writes '{words}' (it grows as it writes) and it stays, painted",
              bool(early) and bool(late) and early["state"] == "writing" and 0 < early["d"] < late["d"] * 0.7
              and late["state"] == "done" and painted > 0.03,
              f"{early and (early['state'], early['d'])} at 400 ms, {late and (late['state'], late['d'])} written; painted {painted:.1%}")
        check(f"{name}: ...in the words' own grey, and a screen reader is still given the words",
              bool(late) and late["stroke"] == late["words"] and late["said"] == words and late["aria"] == "true",
              str(late and {k: late[k] for k in ("stroke", "words", "said", "aria")}))
        _scribble(pg, sel)
        pg.wait_for_timeout(120)
        mid = pg.evaluate(_HAND)
        pg.wait_for_timeout(700)
        gone = pg.evaluate(_HAND)
        left = _inked(pg, late and late["box"])
        check(f"{name}: ...the first stroke un-writes them, seen, and then they go",
              bool(mid) and bool(gone) and late is not None and mid["state"] == "unwriting" and 0 < mid["d"] < late["d"]
              and mid["opacity"] > 0.95 and gone["state"] == "away" and gone["d"] == 0 and gone["hidden"] and left < 0.005,
              f"{mid and (mid['state'], mid['d'], mid['opacity'])} at 120 ms, {gone and (gone['state'], gone['d'])} at 820 ms; painted {left:.1%}")
        if name == "Pad":
            pg.click("#undoBtn")
            pg.wait_for_timeout(300)
            again = pg.evaluate(_HAND)
            _written(pg)
            again2 = pg.evaluate(_HAND)
            check("Pad: when the canvas is empty again (Undo), your hand writes them again from the start",
                  bool(again) and bool(again2) and again["state"] == "writing" and again["d"] < again2["d"] * 0.7
                  and again2["state"] == "done" and _inked(pg, again2["box"]) > 0.03,
                  f"{again and (again['state'], again['d'])} at 300 ms, {again2 and (again2['state'], again2['d'])} written")
        c.close()
    c = b.new_context(viewport={"width": 402, "height": 874}, color_scheme="dark", reduced_motion="reduce")
    pg = c.new_page()
    browsing.goto(pg, BASE, "/skribl-pad")
    pg.evaluate("() => window.SkriblHints && window.SkriblHints.hide && window.SkriblHints.hide()")
    _rewrite(pg)
    pg.wait_for_timeout(40)
    now_ = pg.evaluate(_HAND)
    check("Reduce Motion: the words are there whole at once, not written",
          bool(now_) and now_["state"] == "done" and now_["d"] > 4000, str(now_ and (now_["state"], now_["d"])))
    c.close()
    # THE FIRST-OPEN HELLO covers the canvas: under it your hand waits, blank,
    # and writes once the hello has gone (lib/hello.js takes its element out).
    c = b.new_context(viewport={"width": 402, "height": 874}, color_scheme="dark")
    pg = c.new_page()
    pg.goto(BASE + "/skribl-pad?hello=again")
    under, after = [], []
    for _ in range(140):
        r = pg.evaluate("() => { const s = document.querySelector('.canvas-empty-hand'); return { hello: !!document.getElementById('skriblHello'),"
                        " state: s && s.getAttribute('data-state'), d: s ? (s.querySelector('path').getAttribute('d') || '').length : -1 }; }")
        (under if r["hello"] else after).append((r["state"], r["d"]))
        if any(st == "done" for st, _ in after):
            break
        pg.wait_for_timeout(100)
    check("with the first-open hello on screen your hand waits, blank, and writes once the hello has gone",
          bool(under) and all(d <= 0 for _, d in under) and any(st == "writing" for st, _ in after) and any(st == "done" for st, _ in after),
          f"under the hello {sorted(set(under), key=str)[:3]}; after it {after[:4]} ... {after[-1:]}")
    c.close()
    # IF IT NEVER COMES (the module not served): the typed words wait unseen
    # for it, then show on their own -- asked of the stylesheet's own clock.
    c = b.new_context(viewport={"width": 402, "height": 874}, color_scheme="dark")
    c.route("**/lib/handwords.js*", lambda r: r.fulfill(status=404, body="", content_type="text/plain"))
    pg = c.new_page()
    browsing.goto(pg, BASE, "/skribl-pad")
    pg.evaluate("() => window.SkriblHints && window.SkriblHints.hide && window.SkriblHints.hide()")
    r = pg.evaluate("""() => { const t = document.getElementById('canvasEmptyHint').firstElementChild;
        const alpha = () => { const m = getComputedStyle(t).color.match(/[\\d.]+/g); return m.length > 3 ? +m[3] : 1; };
        const a = t.getAnimations().find(x => x.animationName === 'canvas-empty-late');
        if (!a) return { animation: false, now: alpha() };
        a.pause(); a.currentTime = 600; const at600 = alpha(); a.currentTime = 1600; const at1600 = alpha(); a.finish();
        return { animation: true, at600, at1600, hand: !!document.querySelector('.canvas-empty-hand') }; }""")
    pg.wait_for_timeout(200)
    s = pg.evaluate(_HINT, {"hint": "canvasEmptyHint", "cv": "#canvas"})
    ink = _inked(pg, s and s["box"])
    check("if your hand never comes, the typed words wait unseen for it, then show on their own, painted",
          r.get("animation") and r["at600"] == 0 and r["at1600"] > 0.3 and not r["hand"] and ink > 0.02, f"{r} ink {ink:.1%}")
    c.close()
    # WORDS IT HAS NO RECORDING OF keep their typed letters, at once.
    c = b.new_context(viewport={"width": 402, "height": 874}, color_scheme="dark")

    def _other_words(route):
        r = route.fetch()
        route.fulfill(response=r, body=r.text().replace("<span>Draw anything</span>", "<span>Draw something</span>"))
    c.route("**/skribl-pad", _other_words)
    pg = c.new_page()
    browsing.goto(pg, BASE, "/skribl-pad")
    r = pg.evaluate("""() => { const h = document.getElementById('canvasEmptyHint'), t = h.firstElementChild, cs = getComputedStyle(t);
        const m = cs.color.match(/[\\d.]+/g); return { typed: h.classList.contains('is-typed'), hand: !!h.querySelector('.canvas-empty-hand'),
        animation: cs.animationName, alpha: m.length > 3 ? +m[3] : 1, text: t.textContent.trim() }; }""")
    check("words it has no recording of keep their typed letters, at once",
          r["text"] == "Draw something" and r["typed"] and not r["hand"] and r["animation"] == "none" and r["alpha"] > 0.3, str(r))
    c.close()
    # THE SNAIL, ONCE, IN A SITE'S POST BOX.
    c = b.new_context(viewport={"width": 402, "height": 874}, color_scheme="dark")
    c.add_init_script("window.__skriblOnceForce = true;")
    pg = c.new_page()
    fr = _compose(pg, "pad")
    seq = _first_look(pg, fr)
    on_at = next((i for i, (_, on) in enumerate(seq) if on), None)
    check("in a site's post box, the first time: your hand writes the words, then the snail comes",
          on_at is not None and seq[on_at][0] == "done" and any(st == "writing" for st, _ in seq[:on_at]),
          f"{len(seq)} looks; the snail at {on_at}; the words then {seq[on_at][0] if on_at is not None else None}")
    pg.wait_for_timeout(5600)
    o = fr.evaluate(_ONCE)
    drawn = _inked(pg, _in_page(pg, o and o["box"]))
    check("...it draws itself above them, centred, faint, and rests",
          bool(o) and o["on"] and 20 <= o["above"] <= 40 and abs(o["centre"]) <= 2 and abs(o["opacity"] - 0.45) < 0.02
          and bool(o["player"]) and o["player"]["state"] != "playing" and o["player"]["at"] >= o["player"]["total"] - 30 and drawn > 0.01,
          f"{o and {k: o[k] for k in ('on', 'above', 'centre', 'opacity', 'player', 'src')}}; drawn {drawn:.1%}")
    _scribble(pg, "#canvas", fr)
    pg.wait_for_timeout(800)
    o2 = fr.evaluate(_ONCE)
    swept = _inked(pg, _in_page(pg, o and o["box"]))
    check("...and the first stroke sweeps it away",
          bool(o2) and not o2["on"] and o2["hidden"] and swept < 0.005, f"{o2 and (o2['on'], o2['hidden'])}; drawn {swept:.1%}")
    fr.evaluate("() => location.reload()")
    pg.wait_for_function("() => { const w = document.getElementById('padFrame').contentWindow;"
                         " return !!(w && w.__skriblBoot && w.__skriblBoot.pad); }", timeout=30000)
    fr = next(f for f in pg.frames if "compose=1" in f.url)
    _written(fr)
    pg.wait_for_timeout(1500)
    o3 = fr.evaluate(_ONCE)
    check("...once on a device: opened again, it does not come",
          bool(o3) and not o3["on"] and o3["hidden"], str(o3 and (o3["on"], o3["hidden"])))
    c.close()
    c = b.new_context(viewport={"width": 402, "height": 874}, color_scheme="dark")
    c.add_init_script("window.__skriblOnceForce = true;")
    pg = c.new_page()
    browsing.goto(pg, BASE, "/skribl-pad")
    _written(pg)
    pg.wait_for_timeout(1500)
    check("outside a post box it never comes (the editor alone carries none of it)",
          pg.evaluate("() => !document.getElementById('hintOnce') && !window.SkriblInline"), "")
    c.close()
    c = b.new_context(viewport={"width": 402, "height": 874}, color_scheme="dark")
    c.add_init_script("window.__skriblOnceForce = true;")
    pg = c.new_page()
    fr = _compose(pg, "flip")
    seq = _first_look(pg, fr)
    pg.wait_for_timeout(600)
    o = fr.evaluate(_ONCE)
    check("Flip in a post box: 'Draw page 1' in your hand, then the bouncing ball above it",
          bool(seq) and seq[-1][1] and seq[-1][0] == "done" and bool(o) and o["src"] == "hint-ball.json" and 20 <= o["above"] <= 40,
          f"{seq[-1:]}; {o and {k: o[k] for k in ('above', 'src', 'opacity')}}")
    c.close()
    c = b.new_context(viewport={"width": 402, "height": 874}, color_scheme="dark", reduced_motion="reduce")
    c.add_init_script("window.__skriblOnceForce = true;")
    pg = c.new_page()
    fr = _compose(pg, "pad")
    _first_look(pg, fr)
    pg.wait_for_timeout(400)
    o = fr.evaluate(_ONCE)
    check("Reduce Motion: the snail is there whole, still, and faint",
          bool(o) and o["on"] and bool(o["player"]) and o["player"]["state"] != "playing"
          and o["player"]["at"] >= o["player"]["total"] - 30 and abs(o["opacity"] - 0.45) < 0.02,
          str(o and {k: o[k] for k in ("on", "player", "opacity")}))
    c.close()
    b.close()

print("\nBLOOBY CHEERS — once a drawing has posted, on the Posted! band, in both editors")
# The owner's pick from the Blooby mock ("Cheer is best"), and then the posted
# moment's ("maybe an animated blooby jumping up with his hands in the
# air?"; A, the band): after a real post the sheet's band shows Blooby, who
# jumps and stays cheering over "Posted!", and the line under it says what is
# true then -- anyone with the link can watch it (the server's default is
# unlisted; the sheet only ever adds public) -- in each editor's own words: the
# Pad's drawings draw themselves, Flip's play. Opened again, the sheet is back
# to how it starts. A save kept on this device only (the post failed) does not
# cheer, and compose mode, where nothing is posted yet, has no band at all.
# PAINTED, and painted as HIM: the band is the badge's purple too, so a box
# showing the bare band would read as lilac. His badge has what the band has
# not, the white star he stands on and his dark drawn line; both are counted
# (in his 80px box at 1x, about 7% and 0.5% of it; the bare band has none).
# The jump itself, pose by pose, is verify_postmoment's.
_POSTED = """() => { const d = document.getElementById('postDone'), j = document.getElementById('postJump');
    const box = e => { if (!e || !e.getClientRects().length) return null;
      const r = e.getBoundingClientRect(); return [r.left, r.top, r.width, r.height]; };
    const t = document.querySelector('#postSheet .export-head'), tt = t && t.firstChild && t.firstChild.nodeType === 3 ? t.firstChild : null;
    return { shown: !!d && !d.hidden, src: j ? (j.getAttribute('src') || '').split('?')[0].split('/').pop() : null,
             done: !!j && j.complete && j.naturalWidth > 0, cheer: box(j && j.parentElement),
             head: d && !d.hidden ? document.getElementById('postDoneHead').textContent : (tt ? tt.nodeValue : null),
             headBox: box(document.getElementById('postDoneHead')),
             line: d && !d.hidden ? document.getElementById('postDoneLine').textContent.trim()
                   : (document.getElementById('postSub') || {}).textContent }; }"""


def _badge(pg, box):
    """His badge's own paint in `box`: the share of the white star and of his dark line."""
    if not box or box[2] < 8 or box[3] < 8:
        return 0.0, 0.0
    shot = Image.open(io.BytesIO(pg.screenshot(clip={"x": box[0], "y": box[1], "width": box[2], "height": box[3]}))).convert("RGB")
    raw = shot.tobytes()
    px = [raw[i:i + 3] for i in range(0, len(raw), 3)]
    white = sum(1 for r, g, b_ in px if min(r, g, b_) > 225) / max(1, len(px))
    dark = sum(1 for r, g, b_ in px if max(r, g, b_) < 70) / max(1, len(px))
    return white, dark


def _post_from(b, path, canvas, theme="light", viewport=None, die=False):
    """A fresh editor, one stroke, Post, and the sheet once it has answered."""
    c = b.new_context(viewport=viewport or {"width": 402, "height": 874}, color_scheme=theme)
    pg = c.new_page()
    browsing.goto(pg, BASE, f"{path}?theme={theme}")
    pg.evaluate("() => { if (window.SkriblHints) window.SkriblHints.hide(); }")
    if die:
        pg.route("**/api/skribls**", lambda r: r.abort() if r.request.method == "POST" else r.continue_())
    bx = pg.locator(canvas).bounding_box()
    pg.mouse.move(bx["x"] + bx["width"] * 0.3, bx["y"] + bx["height"] * 0.3)
    pg.mouse.down()
    pg.mouse.move(bx["x"] + bx["width"] * 0.6, bx["y"] + bx["height"] * 0.5, steps=10)
    pg.mouse.up()
    pg.wait_for_timeout(300)
    if path == "/skribl-pad":
        pg.click("#recordBtn")
        pg.wait_for_timeout(400)
    pg.click("#postBtn")
    pg.wait_for_timeout(500)
    pg.fill("#postTitleInput", "Cheer probe")
    pg.click("#postSubmitBtn")
    pg.wait_for_selector("#postResult:not([hidden])" if not die else "#postStatus:not([hidden])", timeout=15000)
    pg.wait_for_timeout(2500 if die else 1400)   # his jump is 0.8 s; he stays cheering
    return c, pg


def _over(r):
    """His box over "Posted!", centred on it, nothing overlapping."""
    if not (r["cheer"] and r["headBox"]):
        return False
    x, y, w, h = r["cheer"]
    hx, hy, hw, _ = r["headBox"]
    return y + h <= hy and abs((x + w / 2) - (hx + hw / 2)) <= 2


with sync_playwright() as p:
    b = p.chromium.launch()
    for theme in ("light", "dark"):
        c, pg = _post_from(b, "/skribl-pad", "#canvas", theme)
        r = pg.evaluate(_POSTED)
        white, dark = _badge(pg, r["cheer"])
        check(f"Pad, {theme}: after a post Blooby cheers on the band over 'Posted!', painted as his badge, and the line says anyone "
              "with the link can watch it draw itself",
              r["shown"] and r["src"] == "blooby-jump.webp" and r["done"] and white > 0.04 and dark > 0.002 and r["head"] == "Posted!"
              and r["line"] == "Anyone with the link can watch it draw itself." and _over(r),
              f"{ {k: r[k] for k in ('shown', 'src', 'head', 'line')} } star {white:.0%} line {dark:.1%} over {_over(r)}")
        if theme == "light":
            pg.keyboard.press("Escape")
            pg.wait_for_timeout(500)
            pg.click("#postBtn")
            pg.wait_for_timeout(600)
            again = pg.evaluate(_POSTED)
            check("...and opened again, the sheet is back to how it starts: no band, its first title and line",
                  not again["shown"] and again["head"] == "Post your Skribl"
                  and again["line"] == "Add a title and share it to Skribl",
                  f"{ {k: again[k] for k in ('shown', 'head', 'line')} }")
        c.close()
    c, pg = _post_from(b, "/skribl-pad", "#canvas", "light", {"width": 1280, "height": 900})
    r = pg.evaluate(_POSTED)
    white, dark = _badge(pg, r["cheer"])
    check("Pad on a desk: he cheers over the words there too, painted as his badge",
          r["shown"] and r["head"] == "Posted!" and _over(r) and white > 0.04 and dark > 0.002,
          f"cheer {r['cheer']} head {r['headBox']} star {white:.0%} line {dark:.1%}")
    c.close()
    c, pg = _post_from(b, "/flip", "#pad", "light")
    r = pg.evaluate(_POSTED)
    white, dark = _badge(pg, r["cheer"])
    check("Flip: the same cheer after a post, and its line says anyone with the link can watch it play",
          r["shown"] and r["src"] == "blooby-jump.webp" and r["done"] and white > 0.04 and dark > 0.002 and r["head"] == "Posted!"
          and r["line"] == "Anyone with the link can watch it play." and _over(r),
          f"{ {k: r[k] for k in ('shown', 'src', 'head', 'line')} } star {white:.0%} line {dark:.1%} over {_over(r)}")
    c.close()
    c, pg = _post_from(b, "/skribl-pad", "#canvas", "light", die=True)
    r = pg.evaluate(_POSTED)
    check("a drawing kept on this device only (the post failed) gets no cheer, and the line stays",
          not r["shown"] and r["line"] == "Add a title and share it to Skribl",
          f"{ {k: r[k] for k in ('shown', 'head', 'line')} }")
    c.close()
    b.close()

# Compose mode posts nothing, so the sheet carries no band and no posted line:
# asked of the served markup's elements, not of words.
_cmp = {}
for _path in ("/skribl-pad?compose=1", "/flip?compose=1"):
    _html = urllib.request.urlopen(BASE + _path, timeout=20).read().decode()
    _cmp[_path] = (bool(re.search(r'<div\b[^>]*\bid="postDone"', _html)),
                   bool(re.search(r'\bid="postDoneLine"', _html)))
check("compose mode, where nothing is posted yet, has no band and no posted line, in either editor",
      _cmp and all(v == (False, False) for v in _cmp.values()), str(_cmp))

bad = [r for r in results if not r[0]]
print("\n" + "=" * 62)
print(f"{len(results) - len(bad)}/{len(results)} passed"
      + ("  FAILURES: " + ", ".join(r[1] for r in bad) if bad else ""))
sys.exit(1 if bad else 0)
