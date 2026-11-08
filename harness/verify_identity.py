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
import time
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

    # THE CARD'S ICON WAITS FOR THE PAGE (FUTURE 6af, Nov 8). Hidden, it still
    # downloaded during a first open: 26 KB a slow phone needed for scripts.
    # It is now asked for once the page has loaded, and the card waits for it
    # (a moment at most). Asked exactly: the icon is held until the card asks
    # for it to be decoded, then let through 150 ms later, so a card that does
    # not wait shows an empty square, and one that waits shows the icon.
    hc = _phone()
    hc.add_init_script("""(() => {
        const dec = HTMLImageElement.prototype.decode;
        HTMLImageElement.prototype.decode = function () {
          if (this.closest && this.closest('#homeScreenBanner') && !window.__iconAsked) window.__iconAsked = performance.now();
          return dec.apply(this, arguments);
        };
        document.addEventListener('DOMContentLoaded', () => {
          const b = document.getElementById('homeScreenBanner'); if (!b) return;
          new MutationObserver(() => {
            if (b.hidden || window.__cardShown) return;
            const i = b.querySelector('img');
            window.__cardShown = { complete: i.complete, width: i.naturalWidth };
          }).observe(b, { attributes: true, attributeFilter: ['hidden'] });
        });
      })()""")
    hp = hc.new_page()
    _held = []
    hp.route("**/icon-192.png*", lambda r: _held.append(r))
    hp.goto(BASE + "/skribl-pad", wait_until="commit")
    _t0 = time.monotonic()
    while time.monotonic() - _t0 < 6:
        _st = hp.evaluate("() => [window.__iconAsked || null, !!window.__cardShown, performance.now()]")
        if _held and ((_st[0] is not None and _st[2] - _st[0] >= 150) or time.monotonic() - _t0 > 4):
            for _r in _held:
                _r.continue_()
            _held.clear()
        if _st[1]:
            break
        hp.wait_for_timeout(50)
    for _r in _held:
        _r.continue_()
    hp.wait_for_timeout(200)
    _ic = hp.evaluate("""() => { const e = performance.getEntriesByType('resource').find(r => /icon-192/.test(r.name));
        return { asked: e ? Math.round(e.startTime) : null, load: Math.round(performance.getEntriesByType('navigation')[0].loadEventStart),
                 shown: window.__cardShown || null }; }""")
    check("the card's icon is not downloaded during the first open: it is asked for once the page has loaded",
          _ic["asked"] is not None and _ic["asked"] >= _ic["load"], f"icon asked for at {_ic['asked']} ms, the page loaded at {_ic['load']} ms")
    check("...and the card waits for it: when the card shows, its icon is there",
          bool(_ic["shown"]) and _ic["shown"]["complete"] and _ic["shown"]["width"] > 0, str(_ic["shown"]))
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

print("\nTHE CALM OPEN — your hand's words already written, written once under the hello; the pen hops after a wait; the snail once in a post box")
# The owner's pick after the "Empty canvas ideas" mock (lib/handwords.js):
# "Draw anything" (Flip: "Draw page 1") in the owner's own hand, recorded
# through the real Text tool (harness/tools/make_handwords.py). Then THE CALM
# OPEN (owner: "it has to be subtle cuz it happens a lot. And the letters
# drawing themselves is already starting to get annoying. I like the font
# though"; then "Yes calm"): the editors draw the words into the page already
# written (skribl_hand_words), so they are there on the first frame; they
# write themselves only under the first-open hello, once; the first stroke
# fades them with the line under them instead of un-writing them; and the pen
# gives one tiny hop when the editor was a wait to open (lib/penswoosh.js).
# Asked of the drawing's own path and state on every frame from the first
# paint, of what is PAINTED in its box (a screenshot), of its colour against
# the words' and of the words a screen reader is given; the hop, of the pen
# button's place on every frame. In a site's post box, once on a device, How
# it works' snail (Flip: the ball) draws itself faintly above the words;
# automation meets it, and the hop, only when it asks (window.__skriblOnceForce,
# window.__skriblHopForce), as with the hello.
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
# The words on every animation frame from the first paint: the drawing's state,
# its path's length (0 while blank) and the hint's opacity (its fade).
_HAND_FRAMES = """(() => { const rows = []; window.__handRows = rows;
  const tick = (t) => { const h = document.getElementById('canvasEmptyHint') || document.getElementById('flipEmptyHint');
    const s = h && h.querySelector('svg.canvas-empty-hand'), p = s && s.querySelector('path');
    rows.push({ t: Math.round(t), hint: !!h, state: s ? s.getAttribute('data-state') : null,
                d: p ? (p.getAttribute('d') || '').length : -1, op: h ? +(+getComputedStyle(h).opacity).toFixed(3) : null,
                seen: s ? +getComputedStyle(s).opacity : 0,
                hello: !!document.getElementById('skriblHello') && document.documentElement.hasAttribute('data-hello-comes') });
    if (rows.length < 3000) requestAnimationFrame(tick); };
  requestAnimationFrame(tick); })();"""
# A PAGE THAT DID NOT DRAW THEM (a template without skribl_hand_words): the
# editors' markup with the drawing taken back out, the typed words (or WORDS)
# where it was.
_DRAWN = re.compile(r'<span style="width: \d+px"><svg class="canvas-empty-hand".*?</svg><span class="vis-hidden">(.*?)</span></span>', re.S)


def _undrawn(words=None):
    def handler(route):
        r = route.fetch()
        body = _DRAWN.sub(lambda m: f"<span>{words or m.group(1)}</span>", r.text()).replace("canvas-empty-hint is-hand", "canvas-empty-hint")
        route.fulfill(response=r, body=body)
    return handler


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


_SLOW_LOOK = """() => { const h = document.getElementById('canvasEmptyHint') || document.getElementById('flipEmptyHint');
    if (!h) return null; const t = h.firstElementChild, m = getComputedStyle(t).color.match(/[\\d.]+/g);
    const a = m && m.length > 3 ? +m[3] : 1, s = h.querySelector('.canvas-empty-hand'), o = document.getElementById('hintOnce');
    return { typed: !t.querySelector('.vis-hidden') && a > 0.05 ? +a.toFixed(2) : 0, hand: s ? (s.getAttribute('data-state') || 'page') : '-',
             d: s && +getComputedStyle(s).opacity > 0.01 ? (s.querySelector('path').getAttribute('d') || '').length : 0, cls: h.className, boot: !!(window.__skriblBoot && (window.__skriblBoot.pad || window.__skriblBoot.flip)),
             once: o ? (o.hidden ? 'hidden' : (o.classList.contains('is-on') ? 'is-on' : 'shown')) : '-' }; }"""


def _slow_open(pg, route, hold, ms, until, secs=10, free_also=("/inlineplayer.js",)):
    """Open ROUTE with scripts HELD back MS ms (HOLD "others": every script but
    the hand's and FREE_ALSO; "hand": the hand's alone), reading the words
    every 50 ms until UNTIL(look) or SECS. Held, not slowed: the requests wait
    until released, as late as a slow first open made them. The in-post
    player is never held, so a snail that does not wait for the editor shows
    early, where it would have."""
    held, free = [], [False]

    def _gate(r):
        u = r.request.url
        mine = "/lib/handwords.js" in u
        if free[0] or (hold == "others" and (mine or any(f in u for f in free_also))) or (hold == "hand" and not mine):
            r.continue_()
        else:
            held.append(r)
    pg.route("**/static/skribl/**/*.js*", _gate)
    t0 = time.monotonic()
    pg.goto(BASE + route, wait_until="commit")
    looks = []
    while time.monotonic() - t0 < secs:
        if not free[0] and (time.monotonic() - t0) * 1000 >= ms:
            free[0] = True
            for r in held:
                r.continue_()
        try:
            look = pg.evaluate(_SLOW_LOOK)
        except Exception:
            look = None
        if look is not None:
            look["t"] = round(time.monotonic() - t0, 2)
        looks.append(look)
        if look and until(look):
            break
        pg.wait_for_timeout(50)
    if not free[0]:
        free[0] = True
        for r in held:
            r.continue_()
    return looks


def _reopened(pg, ed):
    """The post box's editor opened again (its frame reloaded), once the NEW
    page has booted and your hand has written the words. The page being left
    keeps its boot mark until the new one replaces it, so a wait for the mark
    alone can pass on the old page and read the new one too early: a "does not
    come" row that cannot go red. Marking the old page first rules that out."""
    pg.evaluate("() => { const w = document.getElementById('padFrame').contentWindow; w.__skStale = 1; w.location.reload(); }")
    pg.wait_for_function("(ed) => { const w = document.getElementById('padFrame').contentWindow; return !!(w && !w.__skStale"
                         " && w.__skriblBoot && w.__skriblBoot[ed] && w.document.readyState === 'complete'); }", arg=ed, timeout=30000)
    fr = next(f for f in pg.frames if "compose=1" in f.url)
    _written(fr)
    return fr


def _stays_away(pg, fr, ms=3000):
    """The snail's state MS after the words are written, or the moment it
    shows: where it would come, it is on within a second of them."""
    for _ in range(ms // 100):
        o = fr.evaluate(_ONCE)
        if o and o["on"]:
            return o
        pg.wait_for_timeout(100)
    return fr.evaluate(_ONCE)


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
        c.add_init_script(_HAND_FRAMES)
        pg = c.new_page()
        browsing.goto(pg, BASE, route)
        pg.evaluate("() => window.SkriblHints && window.SkriblHints.hide && window.SkriblHints.hide()")
        _written(pg)
        late = pg.evaluate(_HAND)
        rows = pg.evaluate("() => window.__handRows")
        first = next((r for r in rows if r["hint"]), None)
        wrote = [r for r in rows if r["state"] == "writing"]
        painted = _inked(pg, late and late["box"])
        check(f"{name}: '{words}' is there already written in your hand on its first frame, never written in front of you, painted",
              bool(first) and bool(late) and late["state"] == "done" and late["d"] > 4000 and first["d"] == late["d"]
              and first["seen"] > 0.99 and not wrote and painted > 0.03,
              f"first frame {first and (first['state'], first['d'], first['seen'])}; {len(wrote)} frames writing; "
              f"then {late and (late['state'], late['d'])}; painted {painted:.1%}")
        check(f"{name}: ...in the words' own grey, and a screen reader is still given the words",
              bool(late) and late["stroke"] == late["words"] and late["said"] == words and late["aria"] == "true",
              str(late and {k: late[k] for k in ("stroke", "words", "said", "aria")}))
        # THE FIRST STROKE: the words go with the line under them, in the
        # hint's own fade, whole while they fade (they used to un-write).
        n0 = pg.evaluate("() => window.__handRows.length")
        _scribble(pg, sel)
        pg.wait_for_timeout(800)
        fade = pg.evaluate("(n) => window.__handRows.slice(n)", n0)
        gone = pg.evaluate(_HAND)
        left = _inked(pg, late and late["box"])
        showing = [r for r in fade if r["op"] is not None and r["op"] > 0.02]
        steps = [a["op"] - z["op"] for a, z in zip(fade, fade[1:]) if a["op"] is not None and z["op"] is not None]
        check(f"{name}: ...the first stroke fades them with the line under them, whole while they fade, and then they go",
              bool(fade) and bool(gone) and late is not None and all(r["d"] == late["d"] for r in showing)
              and not any(r["state"] == "unwriting" for r in fade) and sum(1 for s in steps if s > 0.001) >= 4
              and max(steps, default=1) < 0.5 and gone["state"] == "away" and gone["hidden"] and gone["opacity"] == 0 and left < 0.005,
              f"while showing: path {sorted(set(r['d'] for r in showing))[:3]} (whole {late and late['d']}); "
              f"states {sorted(set(str(r['state']) for r in fade))}; {sum(1 for s in steps if s > 0.001)} frames fading, "
              f"biggest step {max(steps, default=1):.2f}; then {gone and (gone['state'], gone['hidden'], gone['opacity'])}; painted {left:.1%}")
        if name == "Pad":
            n1 = pg.evaluate("() => window.__handRows.length")
            pg.click("#undoBtn")
            pg.wait_for_timeout(700)
            back = pg.evaluate("(n) => window.__handRows.slice(n)", n1)
            again = pg.evaluate(_HAND)
            check("Pad: when the canvas is empty again (Undo), the words come back whole, not written again",
                  bool(again) and late is not None and again["state"] == "done" and again["d"] == late["d"]
                  and not any(r["state"] == "writing" for r in back) and _inked(pg, again["box"]) > 0.03,
                  f"{again and (again['state'], again['d'])}; {sum(1 for r in back if r['state'] == 'writing')} frames writing")
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
    # THE FIRST-OPEN HELLO covers the canvas, and is the one time your words
    # write themselves (a welcome): under it the page's drawing waits unseen,
    # and your hand writes it once the hello has gone (lib/hello.js takes its
    # element out). The hello comes once on a device (its own key), so the
    # next open has them simply there. Asked as a person meets it: the hello
    # called for (window.__skriblHelloForce), not played again by ?hello=again.
    c = b.new_context(viewport={"width": 402, "height": 874}, color_scheme="dark")
    c.add_init_script("window.__skriblHelloForce = true;")
    c.add_init_script(_HAND_FRAMES)
    pg = c.new_page()
    # The module held back 0.6 s, so there are frames before it takes over, as
    # on a slow open: the page's drawing must wait unseen through them too.
    held = []
    pg.route("**/lib/handwords.js*", lambda r: held.append(r))
    pg.goto(BASE + "/skribl-pad", wait_until="commit")
    t_go = time.monotonic()
    under, after = [], []
    for _ in range(140):
        if held and time.monotonic() - t_go > 0.6:
            for r in held:
                r.continue_()
            held.clear()
        r = pg.evaluate("() => { const s = document.querySelector('.canvas-empty-hand'); return { hello: !!document.getElementById('skriblHello'),"
                        " state: s && s.getAttribute('data-state'), d: s ? (s.querySelector('path').getAttribute('d') || '').length : -1,"
                        " seen: s ? +getComputedStyle(s).opacity : 0 }; }")
        (under if r["hello"] else after).append((r["state"], r["d"] if r["seen"] > 0.01 else 0))
        if any(st == "done" for st, _ in after):
            break
        pg.wait_for_timeout(100)
    early = [(r["state"], r["d"]) for r in pg.evaluate("() => window.__handRows") if r["hello"] and r["seen"] > 0.01 and r["d"] > 0]
    check("the first time on a device, under the hello the words wait unseen, and your hand writes them once it has gone",
          bool(under) and all(d <= 0 for _, d in under) and not early and any(st == "writing" for st, _ in after) and any(st == "done" for st, _ in after),
          f"under the hello (state, path seen) {sorted(set(under), key=str)[:3]}; frames they showed under it {len(early)} {early[:2]}; "
          f"after it {after[:4]} ... {after[-1:]}")
    for r in held:
        r.continue_()
    pg.unroute("**/lib/handwords.js*")
    pg.goto(BASE + "/skribl-pad")
    pg.wait_for_function("() => window.__skriblBoot && window.__skriblBoot.pad", timeout=30000)
    _written(pg)
    rows = pg.evaluate("() => window.__handRows")
    nxt = pg.evaluate(_HAND)
    comes = pg.evaluate("() => document.documentElement.hasAttribute('data-hello-comes')")
    check("...once: the next open (the hello seen) has them simply there, never written",
          not comes and bool(nxt) and nxt["state"] == "done" and nxt["d"] > 4000 and not any(r["state"] in ("writing", "waiting") for r in rows),
          f"hello coming {comes}; {nxt and (nxt['state'], nxt['d'])}; states {sorted(set(str(r['state']) for r in rows))}")
    c.close()
    # IF THE MODULE NEVER COMES (not served): the words are in the page, drawn
    # whole, and nothing waits for it.
    c = b.new_context(viewport={"width": 402, "height": 874}, color_scheme="dark")
    c.route("**/lib/handwords.js*", lambda r: r.fulfill(status=404, body="", content_type="text/plain"))
    pg = c.new_page()
    browsing.goto(pg, BASE, "/skribl-pad")
    pg.evaluate("() => window.SkriblHints && window.SkriblHints.hide && window.SkriblHints.hide()")
    pg.wait_for_timeout(300)
    s = pg.evaluate(_HAND)
    ink = _inked(pg, s and s["box"])
    check("if the module never comes, the words are still there: drawn into the page, whole, painted",
          bool(s) and s["state"] is None and s["d"] > 4000 and s["said"] == "Draw anything" and ink > 0.02,
          f"{s and (s['state'], s['d'], s['said'])}; ink {ink:.1%}")
    c.close()
    # A PAGE THAT DID NOT DRAW THEM (a template without the helper): the module
    # draws them itself, whole, at once.
    c = b.new_context(viewport={"width": 402, "height": 874}, color_scheme="dark")
    c.route("**/skribl-pad", _undrawn())
    pg = c.new_page()
    browsing.goto(pg, BASE, "/skribl-pad")
    _written(pg)
    s = pg.evaluate(_HAND)
    check("a page that did not draw them: the module draws them itself, whole at once, not written",
          bool(s) and s["state"] == "done" and s["d"] > 4000 and s["said"] == "Draw anything",
          str(s and (s["state"], s["d"], s["said"])))
    c.close()
    # ...AND IF THE MODULE NEVER COMES THERE EITHER: the typed words wait unseen
    # for it, then show on their own -- asked of the stylesheet's own clock.
    c = b.new_context(viewport={"width": 402, "height": 874}, color_scheme="dark")
    c.route("**/lib/handwords.js*", lambda r: r.fulfill(status=404, body="", content_type="text/plain"))
    c.route("**/skribl-pad", _undrawn())
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
    check("...and if the module never comes there, the typed words wait unseen for it, then show on their own, painted",
          r.get("animation") and r["at600"] == 0 and r["at1600"] > 0.3 and not r["hand"] and ink > 0.02, f"{r} ink {ink:.1%}")
    c.close()
    # WORDS IT HAS NO RECORDING OF keep their typed letters, at once.
    c = b.new_context(viewport={"width": 402, "height": 874}, color_scheme="dark")

    c.route("**/skribl-pad", _undrawn("Draw something"))
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
    check("in a site's post box, the first time: the words are there, already written, then the snail comes",
          on_at is not None and seq[on_at][0] == "done" and not any(st == "writing" for st, _ in seq[:on_at]),
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
    fr = _reopened(pg, "pad")
    o3 = _stays_away(pg, fr)
    check("...once on a device: opened again, it does not come",
          bool(o3) and not o3["on"] and o3["hidden"], str(o3 and (o3["on"], o3["hidden"])))
    # ONE EACH. A post box opens on the Pad and Flip is its ⋯ row away, so
    # with one mark for both the snail spent the ball's once and the ball never
    # came there (the owner: "I don't see snail or ball"). Same device, same
    # post box: the snail seen, Flip still has its ball, once.
    fr.evaluate("() => { location.href = '/flip?compose=1'; }")
    pg.wait_for_function("() => { const w = document.getElementById('padFrame').contentWindow;"
                         " return !!(w && w.__skriblBoot && w.__skriblBoot.flip && /flip/.test(w.location.pathname)); }", timeout=30000)
    fr = next(f for f in pg.frames if "/flip" in f.url and "compose=1" in f.url)
    seq = _first_look(pg, fr)
    o4 = fr.evaluate(_ONCE)
    check("...and the snail seen, Flip in the same post box still has its ball",
          bool(seq) and seq[-1][1] and bool(o4) and o4["src"] == "hint-ball.json",
          f"{seq[-1:]}; {o4 and (o4['on'], o4['hidden'], o4['src'])}")
    fr = _reopened(pg, "flip")
    o5 = _stays_away(pg, fr)
    check("...once too: Flip opened again, the ball does not come",
          bool(o5) and not o5["on"] and o5["hidden"], str(o5 and (o5["on"], o5["hidden"])))
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
    # THE BALL'S ENDING (owner: "Maybe on last bounce it splatters into small
    # parts that disappear?", then "Yes, build it, all yes"): three bounces by
    # the drawing's own Flip loop, a splat on the fourth landing, and then the
    # box itself goes, floor and all. Asked of the recording (what plays) and
    # of the page (the box gone, nothing PAINTED where it was).
    rec = fr.evaluate("""async () => { const d = await (await fetch(document.getElementById('hintOnce').getAttribute('data-src'))).json();
        return { pages: d.frames.length, loop: d.loop || null, held: d.frames.slice(15).map(f => f.hold || 1),
                 lastPts: d.frames[d.frames.length - 1].strokes.length, firstPts: d.frames[0].strokes.length }; }""")
    box = _in_page(pg, o and o["box"])
    gone_at = None
    for _ in range(100):                     # the whole of it plays in about 5 s at its speed
        oo = fr.evaluate(_ONCE)
        if oo and not oo["on"]:
            gone_at = oo; break
        pg.wait_for_timeout(100)
    pg.wait_for_timeout(500)
    left = _inked(pg, box)
    oo = fr.evaluate(_ONCE)
    check("...three bounces by its own loop, a splat on the fourth landing, and then it is gone: the box fades, nothing left",
          rec["pages"] == 22 and rec["loop"] == {"from": 0, "to": 9, "times": 3} and rec["held"][0] == 3 and min(rec["held"]) >= 2
          and rec["lastPts"] < rec["firstPts"] and bool(gone_at) and bool(oo) and oo["hidden"] and left < 0.005,
          f"recording {rec}; gone {bool(gone_at)}, hidden {oo and oo['hidden']}; painted where it was {left:.2%}")
    c.close()
    c = b.new_context(viewport={"width": 402, "height": 874}, color_scheme="dark", reduced_motion="reduce")
    c.add_init_script("window.__skriblOnceForce = true;")
    pg = c.new_page()
    fr = _compose(pg, "flip")
    _written(fr)
    o = _stays_away(pg, fr)
    kept = fr.evaluate("() => { try { return localStorage.getItem('skribl.once.v1.flip'); } catch (e) { return 'unreadable'; } }")
    check("Reduce Motion: Flip's ball does not come (it ends gone, so there is no still picture of it), and its once is kept",
          bool(o) and not o["on"] and o["hidden"] and kept is None, f"{o and (o['on'], o['hidden'])}; once mark {kept!r}")
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
    # A SLOW FIRST OPEN (the owner: "it shows the old draw anything while it
    # loads"). Behind the editors' hundred-odd deferred scripts, the live site
    # wrote the words 5 to 9 s in, after the typed ones' 1.2 s safety net had
    # shown them, and then took those away. Since the calm open the words are
    # in the page itself, already written, from the first look.
    # Scripts here are HELD, not slowed: their requests wait until released.
    for route, name in (("/skribl-pad", "Pad"), ("/flip", "Flip")):
        c = b.new_context(viewport={"width": 402, "height": 874}, color_scheme="dark")
        pg = c.new_page()
        looks = _slow_open(pg, route, "others", 3000, until=lambda l: l and l["hand"] == "done" and l["boot"])
        first = next((l for l in looks if l), None)
        seen = max((l["typed"] for l in looks if l), default=0)
        wrote = [l["t"] for l in looks if l and l["hand"] == "writing"]
        check(f"{name}, its scripts held back 3 s: the words are there already written from the first look, and typed ones never show",
              bool(first) and not first["boot"] and first["d"] > 4000 and all(l["d"] == first["d"] for l in looks if l) and not wrote and seen == 0,
              f"first look at {first and first['t']} s: {first and (first['hand'], first['d'])} (editor booted then: {first and first['boot']}); "
              f"paths seen {sorted(set(l['d'] for l in looks if l))}; writing at {wrote[:3]}; typed words at most {seen}")
        c.close()
    c = b.new_context(viewport={"width": 402, "height": 874}, color_scheme="dark")
    pg = c.new_page()
    # UNTIL THE HAND HAS DECIDED, not a fixed time after its file is let go:
    # keep the words (is-typed) or write them (a hand state). On a busy runner
    # its script ran later than 1.2 s after release (main red after #796,
    # sqlite 6/6: no class yet at 3.2 s, the words still standing), and a
    # look that ends before the decision cannot tell "not yet" from "never".
    looks = _slow_open(pg, "/skribl-pad", "hand", 2000, until=lambda l: l and l["t"] > 3.2 and l["hand"] == "done")
    first = next((l for l in looks if l), None)
    took = next((l["t"] for l in looks if l and l["hand"] == "done"), None)
    check("...and the hand's own file held back 2 s: the words are there, whole, all along, and it takes them over as they are",
          bool(first) and first["d"] > 4000 and all(l["d"] == first["d"] and l["typed"] == 0 and l["hand"] in ("page", "done") for l in looks if l)
          and took is not None and took >= 2.0,
          f"first look {first and (first['t'], first['hand'], first['d'])}; states {sorted(set(l['hand'] for l in looks if l))}; "
          f"paths {sorted(set(l['d'] for l in looks if l))}; taken over at {took} s")
    c.close()
    # The snail waits for the editor: the Pad's canvas moved 11 px when its
    # scripts ran, and Flip's stage was 154 px tall until flip.js laid it out.
    for route, name in (("/skribl-pad?compose=1", "Pad"), ("/flip?compose=1", "Flip")):
        c = b.new_context(viewport={"width": 402, "height": 874}, color_scheme="dark")
        c.add_init_script("window.__skriblOnceForce = true;")
        pg = c.new_page()
        _slow_open(pg, route, "others", 3000, until=lambda l: l and l["once"] == "is-on")
        pg.wait_for_timeout(400)
        o = pg.evaluate(_ONCE)
        check(f"{name}, its scripts held back 3 s: the {'snail' if name == 'Pad' else 'ball'} still comes, above the words and centred",
              bool(o) and o["on"] and 20 <= o["above"] <= 40 and abs(o["centre"]) <= 2,
              str(o and {k: o[k] for k in ("on", "above", "centre", "box")}))
        c.close()

    # THE PEN HOPS WHEN YOU HAD TO WAIT FOR IT (lib/penswoosh.js; the calm
    # open): one tiny hop as the editor is ready, when that was more than a
    # second after the page began; on an everyday open, nothing moves. Asked
    # of the pen button's place on every frame. Automation meets it only when
    # it asks (window.__skriblHopForce), so these ask, but one.
    _PEN = """(() => { const rows = []; window.__penRows = rows; const tick = (t) => { const b = document.getElementById('penToolBtn');
        if (b) rows.push([Math.round(t), +b.getBoundingClientRect().top.toFixed(2)]); if (rows.length < 900) requestAnimationFrame(tick); };
      requestAnimationFrame(tick); })();"""
    _BOOTED = "() => !!(window.__skriblBoot && (window.__skriblBoot.pad || window.__skriblBoot.flip))"

    def _hop(route, force=True, held_ms=1500, reduce=False, hello=False):
        """The pen button on every frame of an open: HELD_MS > 0 holds the editor's
        own script back that long (a wait); 0 is an everyday open, the second
        visit, its files from the cache. {"up", "down" (px), "ms" in the air, "ready" ms}."""
        c = b.new_context(viewport={"width": 402, "height": 874}, color_scheme="dark", reduced_motion="reduce" if reduce else "no-preference")
        if hello:
            c.add_init_script("window.__skriblHelloForce = true;")
        else:
            c.add_init_script("try { localStorage.setItem('skribl.hello.v2', '1'); } catch (e) {}")
        if force:
            c.add_init_script("window.__skriblHopForce = true;")
        c.add_init_script(_PEN)
        pg = c.new_page()
        if held_ms:
            held, free = [], [False]

            def _gate(r):
                if free[0]:
                    r.continue_()
                else:
                    held.append(r)
            pg.route("**/static/skribl/app.js*", _gate)
            pg.route("**/static/skribl/flip.js*", _gate)
            pg.goto(BASE + route, wait_until="commit")
            pg.wait_for_timeout(held_ms)
            free[0] = True
            for r in held:
                r.continue_()
        else:
            pg.goto(BASE + route)
            pg.wait_for_function(_BOOTED, timeout=30000)
            pg.goto("about:blank")
            pg.goto(BASE + route)
        pg.wait_for_function(_BOOTED, timeout=30000)
        pg.wait_for_timeout(900)
        rows = pg.evaluate("() => window.__penRows")
        ready = pg.evaluate("() => Math.round(performance.getEntriesByType('navigation')[0].domContentLoadedEventStart)")
        c.close()
        rest = rows[-1][1]
        air = [t for t, y in rows if abs(y - rest) > 0.25]
        return {"up": round(rest - min(y for _, y in rows), 2), "down": round(max(y for _, y in rows) - rest, 2),
                "ms": (air[-1] - air[0]) if air else 0, "ready": ready}
    for route, name in (("/skribl-pad", "Pad"), ("/flip", "Flip")):
        h = _hop(route)
        check(f"{name}, an open that made you wait (its script held 1.5 s): the pen gives one tiny hop as it is ready, and is home within half a second",
              4 <= h["up"] <= 6 and h["down"] <= 1.5 and 100 <= h["ms"] <= 500 and h["ready"] > 1000, str(h))
        h = _hop(route, held_ms=0)
        check(f"{name}, an everyday open (the second visit, its files already here): nothing moves (a hop only after a second's wait)",
              (h["up"] == 0 and h["down"] == 0) if h["ready"] <= 1000 else h["up"] >= 4, str(h))
    h = _hop("/flip", reduce=True)
    check("Reduce Motion: no hop, even after a wait", h["up"] == 0 and h["down"] == 0 and h["ready"] > 1000, str(h))
    h = _hop("/skribl-pad", hello=True)
    check("under the first-open hello: no hop (the hello is the welcome, and the words write themselves)",
          h["up"] == 0 and h["down"] == 0 and h["ready"] > 1000, str(h))
    h = _hop("/skribl-pad", force=False)
    check("automation that does not ask never meets it, so nothing else measures the pen in the air",
          h["up"] == 0 and h["down"] == 0 and h["ready"] > 1000, str(h))

    # THE CANVAS IN ITS PLACE FROM THE FIRST FRAME (the calm open, part 2;
    # _skribl_fit_boot.html, _skribl_fit_early.html). Flip opened on a
    # 300x150 box that jumped to full size when its scripts were done, and its
    # page row changed under it; the Pad's canvas settled (26px on a phone, a
    # 4:3 guess turning square on a desk). On the slow phone network, read on
    # every animation frame from the first paint: the canvas from the first
    # frame it is shown (its place and size), the bar under it, and Flip's
    # page row (its height and which of its controls show).
    _NET = {"offline": False, "latency": 100, "downloadThroughput": 3 * 1024 * 1024 / 8, "uploadThroughput": 750 * 1024 / 8}
    _FIRST_FRAMES = """(() => { const rows = []; window.__fitRows = rows;
      const tick = (t) => { const c = document.getElementById('pad') || document.getElementById('canvas');
        const w = document.querySelector('.flip-wrap') || document.querySelector('.canvas-wrap');
        const dk = document.querySelector('.flip-tools') || document.getElementById('toolBar'), sw = document.querySelector('.strip-wrap');
        const h = document.getElementById('flipEmptyHint') || document.getElementById('canvasEmptyHint'), r = c && c.getBoundingClientRect();
        const row = sw ? [...sw.querySelectorAll('.pagebar .pb, .addcol .addbtn')].filter(e => e.getBoundingClientRect().width > 1).map(e => e.id).join(',') : '';
        rows.push({ t: Math.round(t), shown: !!w && getComputedStyle(w).visibility === 'visible',
          r: r ? [r.left, r.top, r.width, r.height].map(v => Math.round(v * 10) / 10) : null,
          dock: dk ? Math.round(dk.getBoundingClientRect().top) : null, strip: sw ? Math.round(sw.getBoundingClientRect().height) : null, row: row,
          words: !!h && getComputedStyle(h).visibility === 'visible' && +getComputedStyle(h).opacity > 0.02,
          ready: !!(window.__skriblBoot && (window.__skriblBoot.pad || window.__skriblBoot.flip)) });
        if (rows.length < 1200) requestAnimationFrame(tick); };
      requestAnimationFrame(tick); })();"""
    _DEVS = {"phone": dict(viewport={"width": 402, "height": 874}, is_mobile=True, has_touch=True), "desk": dict(viewport={"width": 1280, "height": 820})}

    def _first_frames(c, route, cpu=1):
        """ROUTE opened on the slow phone network in context C (at CPU times slower); every frame from the first paint
        to 1.5 s after the editor is ready."""
        c.add_init_script(_FIRST_FRAMES)
        pg = c.new_page()
        cdp = c.new_cdp_session(pg)
        cdp.send("Network.enable")
        cdp.send("Network.emulateNetworkConditions", _NET)
        if cpu > 1:
            cdp.send("Emulation.setCPUThrottlingRate", {"rate": cpu})
        pg.goto(BASE + route, wait_until="commit")
        pg.wait_for_function(_BOOTED, timeout=60000)
        pg.wait_for_timeout(1500)
        rows = pg.evaluate("() => window.__fitRows")
        pg.close()
        return rows

    def _held_still(rows):
        """{"first": the canvas on the first frame it is shown, "moves", "bar", "strips", "rows": the page row's controls seen,
        "words": frames the words are painted on, by their paint (shown and not faded out), not by their class}."""
        shown = [x for x in rows if x["shown"] and x["r"]]
        # SHOWN EARLY, not merely still: a canvas kept hidden until the editor is ready would never move either,
        # and the page would show an empty space for seconds. How long it was in the page, unseen, before it showed:
        # time, not frames, as a person sees it (a slower phone draws fewer frames over the same wait).
        made = next((x["t"] for x in rows if x["r"]), None)
        return {"first": shown[0]["r"] if shown else None, "ready_seen": any(x["ready"] for x in shown),
                "shown_before_ready": bool(shown) and not shown[0]["ready"],
                "hidden_ms": (shown[0]["t"] - made) if shown and made is not None else None,
                "moves": [(a["t"], a["r"], z["r"]) for a, z in zip(shown, shown[1:]) if a["r"] != z["r"]][:3],
                "bar": sorted(set(x["dock"] for x in shown if x["dock"] is not None)),
                "strips": sorted(set(x["strip"] for x in shown if x["strip"] is not None)),
                "rows": sorted(set(x["row"] for x in shown)), "words": sum(1 for x in shown if x["words"]),
                "words_first": bool(shown) and shown[0]["words"]}
    for route, name in (("/flip", "Flip"), ("/skribl-pad", "Pad")):
        for dev, theme in (("phone", "dark"), ("desk", "light")):
            c = b.new_context(color_scheme=theme, service_workers="block", **_DEVS[dev])
            c.add_init_script("try { localStorage.setItem('skribl.hello.v2', '1'); } catch (e) {}")
            s = _held_still(_first_frames(c, route))
            c.close()
            check(f"{name} on a slow {dev}, {theme}: from the first frame it is shown, the canvas is in its place at its size and never moves; "
                  + ("the bar and the page row (its height and its controls) hold still" if name == "Flip" else "the bar holds still"),
                  bool(s["first"]) and s["ready_seen"] and s["shown_before_ready"] and s["hidden_ms"] <= 400 and not s["moves"]
                  and len(s["bar"]) == 1 and (name != "Flip" or (len(s["strips"]) == 1 and len(s["rows"]) == 1)), str(s))
    # A DRAFT YOU COME BACK TO, in another shape and with a drawing on it: its
    # own shape from the first frame (the shape note beside the draft), and the
    # words never shown over a canvas whose drawing is coming. Opened again at
    # a slower phone's pace (CPU 4x): there a frame landed between the Pad's
    # app.js, which laid out a new drawing's shape, and editor_draft.js, which
    # put the draft's back; and the words, hidden by their class, were still
    # painted through their 0.3 s fade over the canvas.
    for route, name, sel in (("/skribl-pad", "Pad", "#canvas"), ("/flip", "Flip", "#pad")):
        c = b.new_context(color_scheme="dark", service_workers="block", **_DEVS["phone"])
        c.add_init_script("try { localStorage.setItem('skribl.hello.v2', '1'); } catch (e) {}")
        pg = c.new_page()
        browsing.goto(pg, BASE, route)
        pg.evaluate("() => window.SkriblHints && window.SkriblHints.hide && window.SkriblHints.hide()")
        pg.evaluate("() => document.querySelector('#canvasSeg button[data-size=\"square\"]').click()")
        pg.wait_for_timeout(400)
        _scribble(pg, sel)
        pg.wait_for_timeout(2500)          # the autosave, and the shape noted beside it
        drawn = pg.evaluate(f"() => {{ const r = document.querySelector('{sel}').getBoundingClientRect(); return [r.width, r.height]; }}")
        pg.close()
        s = _held_still(_first_frames(c, route, cpu=4))
        c.close()
        check(f"{name}: a draft you come back to (square, drawn on) is in its own shape from the first frame, never moves, and the words never show",
              bool(s["first"]) and s["shown_before_ready"] and abs(s["first"][2] - drawn[0]) < 1 and abs(s["first"][3] - drawn[1]) < 1
              and not s["moves"] and s["words"] == 0,
              f"drawn at {drawn}; {s}")
    # A SITE'S POST BOX (compose): a new drawing every time, in its place from
    # the first frame with its words, though a draft in another shape, drawn
    # on, is noted on the device: a post box keeps no draft, so it is not laid
    # out in that one's shape (the early fit's guard, and lib/chromefit.js
    # noted()'s for the Pad's own start).
    for route, name in (("/flip?compose=1", "Flip"), ("/skribl-pad?compose=1", "Pad")):
        c = b.new_context(color_scheme="dark", service_workers="block", **_DEVS["phone"])
        c.add_init_script("try { const n = JSON.stringify({ w: 707, h: 707, pages: 1, ink: true });"
                          " localStorage.setItem('skribl.shape.v1.pad', n); localStorage.setItem('skribl.shape.v1.flip', n); } catch (e) {}")
        s = _held_still(_first_frames(c, route))
        c.close()
        check(f"{name} in a post box (a square draft noted on the device): a new drawing in its place from the first frame it is shown, "
              "its words there with it, and nothing under it moves",
              bool(s["first"]) and s["ready_seen"] and s["shown_before_ready"] and s["hidden_ms"] <= 400 and not s["moves"]
              and s["words_first"] and abs(s["first"][2] - s["first"][3]) > 1
              and len(s["bar"]) == 1 and (name != "Flip" or (len(s["strips"]) == 1 and len(s["rows"]) == 1)), str(s))
    # THE LETTER SHEET keeps no draft either (editor_draft.js PAD_DRAFT_OFF):
    # the Pad's square draft noted on the device leaves its canvas the shape it
    # always has (a phone's tall one), not the draft's.
    c = b.new_context(color_scheme="dark", service_workers="block", **_DEVS["phone"])
    c.add_init_script("try { localStorage.setItem('skribl.hello.v2', '1');"
                      " localStorage.setItem('skribl.shape.v1.pad', JSON.stringify({ w: 707, h: 707, ink: true })); } catch (e) {}")
    pg = c.new_page()
    browsing.goto(pg, BASE, "/skribl-pad?letters=1")
    lt = pg.evaluate("() => { const c = document.getElementById('canvas'); return [c.width, c.height, document.body.classList.contains('letters-mode')]; }")
    c.close()
    check("the letter sheet (the Pad's square draft noted on the device) keeps its own tall canvas, not the draft's shape",
          lt[2] and lt[1] > lt[0] * 1.3, str(lt))
    # A SHAPE LEFT BEHIND, noted with no draft beside it, is dropped by the
    # open that finds it, so the next lays out a new drawing's shape again
    # (noted once, in the tab's first load only).
    for route, name, kind, sel in (("/skribl-pad", "Pad", "pad", "#canvas"), ("/flip", "Flip", "flip", "#pad")):
        c = b.new_context(color_scheme="dark", service_workers="block", **_DEVS["phone"])
        c.add_init_script("try { localStorage.setItem('skribl.hello.v2', '1'); if (!sessionStorage.getItem('cal-left')) {"
                          " sessionStorage.setItem('cal-left', '1'); localStorage.setItem('skribl.shape.v1." + kind + "',"
                          " JSON.stringify({ w: 707, h: 707, pages: 1, ink: true })); } } catch (e) {}")
        pg = c.new_page()
        browsing.goto(pg, BASE, route)
        left = pg.evaluate("(k) => localStorage.getItem(k)", "skribl.shape.v1." + kind)
        browsing.goto(pg, BASE, route)
        nxt = pg.evaluate("(s) => { const r = document.querySelector(s).getBoundingClientRect(); return [r.width, r.height]; }", sel)
        c.close()
        check(f"{name}: a shape noted with no draft beside it is dropped by the open that finds it, and the next open is a new drawing's shape",
              left is None and nxt[1] > nxt[0] * 1.3, f"the note after the first open: {left}; the next open's canvas {nxt}")
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
