"""SK-AUD-013 — the app has an identity to a browser and a Home Screen.

The acquisition audit of v302 added Skribl to an iPhone's Home Screen and got
a screenshot for an icon, a browser-default splash and the OS's chrome colour
around a page that had chosen its own: no web app manifest, no touch icon, no
theme-color anywhere on the principal pages. The share card had been an
identity for a LINK since v102; the pages had none for themselves.

What ships: one route, `/manifest.webmanifest` (a route, not a static file,
so its URLs follow the blueprint's mount point), three PNG icons (since v320,
Blooby waving on lilac, drawn by `harness/tools/blooby.py icon`), and one partial (`_skribl_app_identity.html`) that the Pad,
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
print("\nIDENTITY — the icon is Blooby, waving on lilac")
# THE OWNER'S PICK (v320): Blooby waving on a lilac tile, option J of the mocks,
# drawn from his strokes by `harness/tools/blooby.py icon`. The checks above
# hold an icon to its size and format and would pass on a blank square, or on
# the wordmark it replaced. These read the PIXELS: the tile at all four corners
# is the lilac blooby.py names, his body's purple covers a real share of it, and
# his dark outline is there. The tile colour is read from blooby.py, the one
# place it is written.
_bsrc = (ROOT / "harness" / "tools" / "blooby.py").read_text(encoding="utf-8")
_m_tile = re.search(r'^ICON_TILE = "(#[0-9a-fA-F]{6})"', _bsrc, re.M)
TILE = tuple(int(_m_tile.group(1)[i:i + 2], 16) for i in (1, 3, 5)) if _m_tile else None
check("blooby.py names the icon's tile colour", TILE is not None)
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
    check(f"{_name}: the tile is lilac to every corner",
          TILE is not None and all(_near(c, TILE, 6) for c in _corners), f"corners {_corners}")
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
    hp.click("#homeScreenBannerOpen")
    hp.wait_for_timeout(300)
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
    hp.click("#homeScreenItem")
    hp.wait_for_timeout(600)
    check("...which closes the menu and opens the same steps",
          hp.evaluate(_PAINTED, "homeScreenSteps"))
    hp.click("#homeScreenDone")
    hp.wait_for_timeout(300)
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

bad = [r for r in results if not r[0]]
print("\n" + "=" * 62)
print(f"{len(results) - len(bad)}/{len(results)} passed"
      + ("  FAILURES: " + ", ".join(r[1] for r in bad) if bad else ""))
sys.exit(1 if bad else 0)
