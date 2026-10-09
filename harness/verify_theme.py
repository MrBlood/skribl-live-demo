"""Light mode: the setting, the flash, and the one thing that must NOT follow it.

Skribl was drawn dark. The palette, the two brand marks, the accent purple and
every shadow in the sheet were chosen against a near-black ground, and v230/v232
moved 179 neutral literals into `:root` so a second ramp could exist at all.
This suite guards the four things that make that ramp a feature rather than a
liability.

1. IT FOLLOWS THE DEVICE UNTIL TOLD OTHERWISE (v292; outside review of v291,
   SK-AUD-014, reversing v232). With nothing stored the chrome follows
   `prefers-color-scheme`; an explicit dark or light ignores it, in both
   directions. The resolution lives in the inline boot and lib/theme.js, NOT
   in a `@media (prefers-color-scheme: light)` rule — the light ramp is one
   block keyed on data-theme="light", and a media rule would be a second copy
   of it to drift. Both OS preferences are emulated for each of the four
   cases, because a rule that only misfires under one of them is exactly what
   nearly shipped in v232.

2. IT DOES NOT FLASH. The setting lives in localStorage, which no stylesheet can
   read. Every script in both templates is deferred (verify_surfaces.py pins
   that), so if the attribute were stamped by lib/theme.js the browser would
   already have painted a dark frame — a black flash on every navigation, for
   the users who chose light specifically to avoid one. The inline boot script
   in <head> is what prevents it, and the test for it is to serve the page with
   EVERY external script blocked: if the theme is still right, nothing deferred
   was needed to get it.

3. A DRAWING DOES NOT FOLLOW IT. This is the load-bearing rule and the reason
   the whole job was scoped to "chrome only". A drawing's ground is part of the
   drawing — it is what gets exported, posted, and seen by other people — so a
   UI preference must never repaint it. What the theme DOES pick is where a new
   drawing starts (owner, of the mock: "Do Paper."): Paper in light, the dark
   canvas in dark, and a canvas with nothing on it yet follows a switch,
   because nothing on it was chosen. A stroke, a ground picked by hand or a
   restored draft ends that. The checks are pixel ones, read off a screenshot:
   the ground is a CSS background under a transparent bitmap, so the bitmap
   cannot say what the theme did to it, and no amount of reading CSS would
   tell you that as plainly as the screen does.

4. THE RAMP CANNOT ROT. The failure mode for a two-theme palette is silent: add
   a token to `:root` next month, forget the light value, and that one control
   keeps its dark colour in light mode while everything around it flips. Rather
   than a hand-kept list of tokens, the assertion is structural — every NEUTRAL
   colour token must be overridden — which lets the accent family and the radii
   and easings through automatically because they are not neutral colours.

The luminance sweep at the end is the coarse net: it walks the chrome of both
surfaces in light mode and fails on any element still painting a dark ground.
That is how the nine translucent `rgba()` surfaces were caught, which the first
pass missed entirely because Phase 1 had only converted `rgba(255,255,255,a)`.
"""
import base64
import pathlib
import re
import sys
from assertions import make_check
import browsing

BASE = "http://127.0.0.1:5001"
ROOT = pathlib.Path(__file__).resolve().parent.parent
CSS = ROOT / "skribl" / "static" / "styles.css"
TPL = ROOT / "skribl" / "templates" / "skribl"

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("SKIP: playwright is not installed")
    sys.exit(0)

results = []


check = make_check(results)


# ---------------------------------------------------------------- static ----
css = CSS.read_text(encoding="utf-8")


# Every script file, matched by PATH. Script URLs carry a cache-buster
# (lib/theme.js?v=3675407e), so the glob "**/*.js" matched none of them and
# "every script blocked" blocked nothing: the no-flash checks passed with the
# inline boot's theme stamp deleted.
SCRIPT_FILE = re.compile(r"\.js(\?|$)")


def token_block(pattern):
    m = re.search(pattern + r"\s*\{(.*?)\n\}", css, re.S | re.M)
    if not m:
        return {}
    return dict(re.findall(r"(--[a-z0-9-]+)\s*:\s*([^;]+);", m.group(1)))


def as_rgb(value):
    """Hex or a bare `r,g,b` triplet — the two forms tokens are written in.

    The triplets exist because nine chrome surfaces are translucent: you cannot
    fade a hex to a percentage inside `rgba()`, so those tokens carry channels
    and the call site supplies the alpha. They are colours and must flip.
    """
    v = value.strip()
    m = re.fullmatch(r"#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})", v)
    if m:
        h = m.group(1)
        if len(h) == 3:
            h = "".join(c * 2 for c in h)
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
    m = re.fullmatch(r"(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})", v)
    if m:
        return tuple(int(x) for x in m.groups())
    return None


print("THEME — the stylesheet has a second ramp, and it is complete")
dark_tokens = token_block(r"^:root")
light_tokens = token_block(r'^:root\[data-theme="light"\]')
check("styles.css defines a light ramp",
      len(light_tokens) > 30,
      f"{len(light_tokens)} tokens overridden under [data-theme=light]")

# Structural rather than curated: a neutral is a colour whose channels are
# within 30 of each other, which is precisely the set that has to flip. The
# accent family (#7c5cff, #5b8cff, #9179ff and the four ui-* aliases of them)
# is chromatic and stays put by design; radii and easings are not colours.
# One exemption, and it is a rule rather than a list: a token named for the
# CANVAS is not chrome. The empty-state hint is painted on the drawing surface,
# whose colour is the drawing's rather than the theme's, so its ink follows the
# ground (.light-bg) and never the theme — and having it in :root as a named
# token is what makes that a visible decision rather than a literal somebody
# missed.
unflipped = []
for name, value in dark_tokens.items():
    if "canvas" in name:
        continue
    rgb = as_rgb(value)
    if rgb and max(rgb) - min(rgb) <= 30 and name not in light_tokens:
        unflipped.append(name)
check("every neutral token in :root is overridden for light",
      not unflipped,
      ", ".join(unflipped[:6]) or "the accent and the non-colour tokens are the "
      "only things left alone, which is what should be left alone")

# The phrase appears twice in the sheet's PROSE, in the paragraph recording why
# there is no such rule. Strip comments before looking for the rule itself.
# The neutral ratchet in verify_surfaces.py covers the greys. It cannot cover
# the CHROMATIC inks, because a red is not a neutral by any measure — and those
# are exactly what phase 1 walked past. The danger red, the warn amber and the
# ok green were every one of them picked against a near-black ground; #f4326f
# measures 3.32:1 on the light menu sheet, and it is what "Clear all" is
# written in. So the rule for ink is stricter than the rule for greys: no
# literal at all. #fff is excluded (it is text on a coloured fill, and stays
# white in both themes) and so is #0d0f14 (the dark canvas, which is the
# document's colour, not the chrome's).
INK = re.compile(r"(?<![-\w])(?:color|fill|stroke)\s*:\s*([^;{}]+)")
stray_ink = {}
for sheet in ("styles.css", "flip.css"):
    body = (CSS.parent / sheet).read_text(encoding="utf-8")
    body = re.sub(r"/\*.*?\*/", "", body, flags=re.S)
    body = re.sub(r"^:root(?:\[[^\]]*\])?\s*\{.*?\n\}", "", body, flags=re.S | re.M)
    found = sorted({h.lower() for m in INK.finditer(body)
                    for h in re.findall(r"#[0-9a-fA-F]{3,6}\b", m.group(1))}
                   - {"#fff", "#ffffff", "#0d0f14"})
    if found:
        stray_ink[sheet] = found
check("every ink in the chrome is a token, not a literal",
      not stray_ink,
      "; ".join(f"{k}: {', '.join(v)}" for k, v in stray_ink.items())
      or "a chromatic literal is a colour that cannot follow the theme, and it "
         "will not show up in a grey audit")

check("no prefers-color-scheme rule in the stylesheet: the ramp is one block, resolved by the boot",
      "prefers-color-scheme" not in re.sub(r"/\*.*?\*/", "", css, flags=re.S),
      "a media rule would be a second copy of the light ramp to drift — the OS "
      "is followed by stamping data-theme, in _skribl_theme_boot.html and lib/theme.js")

print("\nTHEME — both surfaces carry the same switch, wired to the same key")
for name in ("skribl_editor.html", "skribl_flip.html"):
    html = (TPL / name).read_text(encoding="utf-8")
    check(f"{name}: has a Theme row with System, Dark and Light",
          'id="themeSeg"' in html and ">Theme<" in html
          and 'data-theme="system"' in html and 'data-theme="dark"' in html and 'data-theme="light"' in html)
    check(f"{name}: stamps the theme before paint, inline and undeferred",
          "_skribl_theme_boot.html" in html,
          "a deferred script cannot beat the first paint")

boot = (TPL / "_skribl_theme_boot.html").read_text(encoding="utf-8")
lib = (ROOT / "skribl" / "static" / "lib" / "theme.js").read_text(encoding="utf-8")
check("the boot script and the library read the SAME key",
      "skribl_theme_v1" in boot and "skribl_theme_v1" in lib,
      "two copies of a contract are two things to drift")
check("the boot script cannot throw the page down",
      "try{" in boot.replace(" ", "") and "catch" in boot,
      "localStorage throws on ACCESS in Safari private mode, not just on write")


# ------------------------------------------------------------------ live ----
KEY = "skribl_theme_v1"
SURFACES = [("Pad", "/"), ("Flip", "/flip")]


def lum(rgb):
    return 0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]


def opaque(colour):
    m = re.findall(r"[\d.]+", colour or "")
    return len(m) >= 3 and (len(m) < 4 or float(m[3]) > 0.05)


def parse(colour):
    m = re.findall(r"[\d.]+", colour or "")
    if len(m) < 3:
        return None
    return tuple(float(x) for x in m[:3])


def rel(c):
    """WCAG relative luminance, for the contrast ratios below."""
    out = []
    for v in c:
        v = v / 255.0
        out.append(v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4)
    return 0.2126 * out[0] + 0.7152 * out[1] + 0.0722 * out[2]


def ratio(a, b):
    la, lb = rel(a), rel(b)
    if la < lb:
        la, lb = lb, la
    return (la + 0.05) / (lb + 0.05)


# The grounds a drawing can start on (lib/canvasground.js), and the one other
# swatch the checks pick by hand.
PAPER, DARK_GROUND, WHITE = "#f6f2ea", "#0d0f14", "#ffffff"
GROUND_NAME = {PAPER: "Paper", DARK_GROUND: "the dark canvas", WHITE: "White"}
# Where each editor's ground is painted (a CSS background, under the drawing's
# transparent bitmap), and where it is drawn on.
GROUND_EL = {"Pad": ".canvas-wrap", "Flip": "#pad"}
INK_EL = {"Pad": "#canvas", "Flip": "#pad"}

_PIXEL = """async (b64) => {
  const img = new Image(); img.src = 'data:image/png;base64,' + b64; await img.decode();
  const c = document.createElement('canvas'); c.width = img.width; c.height = img.height;
  const x = c.getContext('2d'); x.drawImage(img, 0, 0);
  const d = x.getImageData(img.width >> 1, img.height >> 1, 1, 1).data;
  return [d[0], d[1], d[2]];
}"""


def painted(pg, label, fy=0.22):
    """The colour on SCREEN at the middle of the canvas, fy of the way down —
    above the line the checks draw through the middle, and clear of the
    vignette at the edges. A screenshot, because what covers the ground is the
    screen's business: its rect or its style would say what it should be."""
    b = pg.locator(GROUND_EL[label]).bounding_box()
    x, y = b["x"] + b["width"] / 2, b["y"] + b["height"] * fy
    png = pg.screenshot(clip={"x": x - 2, "y": y - 2, "width": 4, "height": 4})
    return tuple(pg.evaluate(_PIXEL, base64.b64encode(png).decode()))


def near(rgb, hexc, tol=3):
    want = tuple(int(hexc[i:i + 2], 16) for i in (1, 3, 5))
    return rgb is not None and all(abs(a - b) <= tol for a, b in zip(rgb, want))


def draw_line(pg, label):
    """One real stroke across the middle of the editor's canvas."""
    b = pg.locator(INK_EL[label]).bounding_box()
    cx, cy = b["x"] + b["width"] / 2, b["y"] + b["height"] / 2
    pg.mouse.move(cx - 80, cy)
    pg.mouse.down()
    for i in range(1, 9):
        pg.mouse.move(cx - 80 + i * 20, cy + (i % 2) * 4)
    pg.mouse.up()
    pg.wait_for_timeout(300)


# The ground as the app holds it, the swatch it lights, what it would save and
# post, and (Flip) the page's thumbnail in the strip, which paints its ground
# into its own bitmap.
_GROUND_STATE = """() => {
  const f = typeof serializeFlip === 'function' ? serializeFlip({}).frames[0]
                                                : serializeSkribl().frames[0];
  const b = f && f.background;
  const tile = typeof _tiles === 'function' && _tiles()[0] ? _tiles()[0].querySelector('canvas') : null;
  let thumb = null;
  if (tile && tile.width) {
    const d = tile.getContext('2d').getImageData(2, 2, 1, 1).data;
    thumb = [d[0], d[1], d[2]];
  }
  return {
    bg: String(bgColor).toLowerCase(),
    lit: [...document.querySelectorAll('.bg-swatch.active')].map(e => (e.dataset.bg || 'custom').toLowerCase()),
    saved: String((b && b.color) || b).toLowerCase(),
    thumb: thumb
  };
}"""


def ground(pg, label):
    st = pg.evaluate(_GROUND_STATE)
    st["px"] = painted(pg, label)
    return st


def on(st, hexc):
    """Painted, held, lit and saved: the whole of what a ground is."""
    return (near(st["px"], hexc) and st["bg"] == hexc and st["lit"] == [hexc]
            and st["saved"] == hexc)


def theme(pg, mode):
    pg.evaluate("(m) => window.SkriblTheme.set(m)", mode)
    pg.wait_for_timeout(350)


with sync_playwright() as p:
    browser = p.chromium.launch()

    for label, path in SURFACES:
        print(f"\nTHEME [{label}] — nothing stored follows the OS; a choice ignores it")
        for scheme in ("light", "dark"):
            for stored, want in ((None, scheme), ("system", scheme), ("dark", "dark"), ("light", "light")):
                page = browser.new_page(viewport={"width": 1000, "height": 900},
                                        color_scheme=scheme)
                page.goto(BASE + path, wait_until="load")
                page.wait_for_timeout(400)
                page.evaluate("() => { for (const k of Object.keys(localStorage))"
                              " if (k.indexOf('skribl') === 0) localStorage.removeItem(k); }")
                if stored:
                    page.evaluate(f"(v) => localStorage.setItem('{KEY}', v)", stored)
                page.reload(wait_until="load")
                page.wait_for_timeout(700)
                attr = page.evaluate("() => document.documentElement.getAttribute('data-theme')")
                bg = parse(page.evaluate(
                    "() => getComputedStyle(document.body).backgroundColor"))
                _ok = (attr == "light" and bg is not None and lum(bg) > 150) if want == "light" \
                      else (attr is None and bg is not None and lum(bg) < 60)
                check(f"{label}: OS {scheme}, stored {stored or 'nothing'} -> {want}",
                      _ok, f"data-theme={attr!r} body luminance {lum(bg):.0f}")
                _mode = page.evaluate("() => window.SkriblTheme.mode()")
                check(f"{label}: ...and the switch shows the CHOICE, {stored or 'system'}",
                      _mode == (stored or "system") and page.evaluate(
                          f"() => document.querySelector('#themeSeg button.on').dataset.theme") == (stored or "system"),
                      f"mode={_mode!r}")
                page.close()
        # THE OS CHANGES ITS MIND while a system-following page is open.
        page = browser.new_page(viewport={"width": 1000, "height": 900}, color_scheme="dark")
        page.goto(BASE + path, wait_until="load")
        page.wait_for_timeout(400)
        page.evaluate(f"() => localStorage.removeItem('{KEY}')")
        page.reload(wait_until="load")
        page.wait_for_timeout(600)
        page.emulate_media(color_scheme="light")
        page.wait_for_timeout(300)
        check(f"{label}: a system-following page follows the OS when it changes",
              page.evaluate("() => document.documentElement.getAttribute('data-theme')") == "light",
              "the attribute did not follow the media query's change event")
        page.evaluate("() => window.SkriblTheme.set('dark')")
        page.emulate_media(color_scheme="light")
        page.wait_for_timeout(300)
        check(f"{label}: ...and an explicit dark does not",
              page.evaluate("() => document.documentElement.getAttribute('data-theme')") is None)
        page.close()

        print(f"THEME [{label}] — the switch sets it, and it survives a reload")
        page = browser.new_page(viewport={"width": 1000, "height": 900})
        page.goto(BASE + path, wait_until="load")
        page.wait_for_timeout(700)
        page.evaluate("() => { for (const k of Object.keys(localStorage))"
                      " if (k.indexOf('skribl_theme') === 0) localStorage.removeItem(k); }")
        page.evaluate("() => window.SkriblTheme.set('light')")
        page.wait_for_timeout(200)
        check(f"{label}: choosing light stamps the attribute",
              page.evaluate("() => document.documentElement.getAttribute('data-theme')") == "light")
        check(f"{label}: ...and stores it",
              page.evaluate(f"() => localStorage.getItem('{KEY}')") == "light")
        page.reload(wait_until="load")
        page.wait_for_timeout(700)
        check(f"{label}: it is still light after a reload",
              page.evaluate("() => document.documentElement.getAttribute('data-theme')") == "light",
              "a preference that does not survive navigation is not a preference")

        # THE FLASH TEST. Serve the page with every external script blocked: no
        # app.js, no flip.js, no lib/theme.js. If the attribute is still there,
        # the inline head script did it, and the browser therefore never had a
        # frame in which to paint the wrong ground.
        naked = browser.new_page(viewport={"width": 1000, "height": 900},
                                 storage_state=page.context.storage_state())
        naked.route(SCRIPT_FILE, lambda route: route.abort())
        naked.goto(BASE + path, wait_until="domcontentloaded")
        check(f"{label}: light is applied with EVERY script file blocked",
              naked.evaluate("() => document.documentElement.getAttribute('data-theme')") == "light",
              "if this needs a deferred script, users who chose light get a "
              "black flash on every single navigation")
        naked.close()

        # THE WORDMARK IS NOT A TILE. `.brand svg` carries a 34px rounded tile
        # with a drop shadow, meant for the PLAYER's logo — and it was catching
        # Pad's wordmark too. On the near-black header a black shadow over a
        # black ground is invisible, so the mistake survived; light mode drew it
        # as a pale rounded rectangle around the mark's bounding box and SKRIBL
        # PAD looked like a sticker stuck onto the header. Reported from a
        # phone, which is where the two surfaces sit side by side. The pin is
        # PARITY rather than a literal: whatever the marks wear, they wear the
        # same thing, which is the property that was actually broken.
        mark = page.evaluate("""() => {
          const m = document.querySelector('.brand .brand-mark')
                 || document.querySelector('.flip-word .brand-mark');
          if (!m) return null;
          const cs = getComputedStyle(m);
          return { shadow: cs.boxShadow, radius: cs.borderRadius };
        }""")
        check(f"{label}: the wordmark wears no tile — no plate, no drop shadow",
              mark is not None
              and mark["shadow"] in ("none", "")
              and mark["radius"] in ("0px", "", "0px 0px 0px 0px"),
              f"{mark} — a shadow that is invisible on a dark ground is a "
              f"sticker on a light one, and Flip never had one")

        print(f"THEME [{label}] — the chrome flips and a drawing does not")
        # Something on the canvas first: a BLANK canvas follows the theme on
        # purpose (lib/canvasground.js), and what must never move is a drawing.
        draw_line(page, label)
        shots = {}
        for mode in ("dark", "light"):
            page.evaluate("(m) => window.SkriblTheme.set(m)", mode)
            page.wait_for_timeout(400)
            shots[mode] = page.evaluate("""() => {
              const out = {};
              const el = document.querySelector('.header');
              out.header = el ? getComputedStyle(el).backgroundColor : null;
              const t = document.querySelector('.toolbar, .flip-tools');
              out.toolbar = t ? getComputedStyle(t).backgroundColor : null;
              out.body = getComputedStyle(document.body).backgroundColor;
              const c = document.querySelector('canvas');
              out.canvasBg = c ? getComputedStyle(c).backgroundColor : null;
              return out;
            }""")
            # The ground as it is PAINTED. This used to read the middle of the
            # canvas's bitmap, which is transparent: the ground is the CSS
            # background behind it, so the read was the same in both themes
            # whatever the theme did to the ground.
            shots[mode]["px"] = painted(page, label)
        for part in ("header", "toolbar", "body"):
            d, l = parse(shots["dark"][part]), parse(shots["light"][part])
            if d is None or l is None:
                continue
            # Some rows paint nothing of their own — the toolbar is transparent
            # and what you see through it is the body. Comparing rgba(0,0,0,0)
            # to itself says nothing about the theme; the body assertion two
            # lines down is what actually covers that ground.
            if not opaque(shots["dark"][part]) and not opaque(shots["light"][part]):
                continue
            check(f"{label}: the {part} is dark in dark and light in light",
                  lum(d) < 70 < lum(l),
                  f"{lum(d):.0f} -> {lum(l):.0f}")
        check(f"{label}: a drawing's ground is IDENTICAL in both themes",
              shots["dark"]["px"] is not None
              and shots["dark"]["px"] == shots["light"]["px"],
              f"{shots['dark']['px']} vs {shots['light']['px']} — a drawing's "
              f"ground is part of the drawing, and a UI preference must not "
              f"repaint what other people are going to see")

        print(f"THEME [{label}] — nothing in the chrome is left dark")
        page.evaluate("() => window.SkriblTheme.set('light')")
        page.wait_for_timeout(400)
        dark_spots = page.evaluate("""() => {
          const out = [];
          const nodes = document.querySelectorAll(
            '.header, .toolbar, .flip-tools, .pagebar, .menu-sheet, .flip-menu,'
            + ' .drawer, .panel, .filmstrip, .autosave-status, .seg, .btn,'
            + ' .icon-btn, .tool-btn, .tool-open, .menu-item');
          for (const el of nodes) {
            const r = el.getBoundingClientRect();
            if (!r.width || !r.height) continue;
            const bg = getComputedStyle(el).backgroundColor;
            const m = (bg || '').match(/[\\d.]+/g);
            if (!m || m.length < 3) continue;
            const a = m.length > 3 ? parseFloat(m[3]) : 1;
            if (a < 0.35) continue;              // a faint wash reads as its parent
            const L = 0.2126*+m[0] + 0.7152*+m[1] + 0.0722*+m[2];
            // The accent purple is a deliberate dark fill in BOTH themes — it
            // is the brand, it carries white text, and it does not flip.
            const chroma = Math.max(+m[0],+m[1],+m[2]) - Math.min(+m[0],+m[1],+m[2]);
            if (L < 90 && chroma < 40) {
              out.push((el.id || el.className.toString().slice(0, 30)) + ' ' + bg);
            }
          }
          return out;
        }""")
        check(f"{label}: no chrome surface is still painting a dark ground",
              not dark_spots,
              "; ".join(dark_spots[:4]) or "every opaque neutral surface flipped")

        # Legibility. THE THRESHOLD IS NOT AN ABSOLUTE ONE, and the first
        # version of this got that wrong: it demanded 4.5:1 of every label and
        # failed on `.menu-version` at 4.42, which is the version footer — a
        # deliberately tertiary line that is dim in BOTH themes. Passing it
        # would have meant darkening the whole upper half of the light text
        # ramp, i.e. breaking the mirrored relationship on purpose to satisfy a
        # number about something this work did not touch.
        #
        # What light mode is actually answerable for is not regressing. So each
        # element is measured in both themes and light must be at least as
        # legible as dark, with a 3:1 floor underneath — the WCAG level for
        # large text and UI components, below which something is not dim, it is
        # unreadable. An ink tuned for a dark ground that washes out on a light
        # one shows up here as a DROP, which is exactly the defect (#f4326f at
        # 3.32:1 on the menu sheet) that the semantic tokens exist for.
        #
        # THE MENU HAS TO BE OPEN. Its rows are where the smallest, softest
        # text lives, and a hidden element has no rect — the first version swept
        # a closed menu, found nothing on a neutral ground on Flip, and passed
        # at a triumphant 99:1 having measured nothing at all.
        page.click("#menuBtn" if label == "Pad" else "#moreBtn")
        page.wait_for_timeout(400)
        SWEEP = """() => {
          const rel = c => {
            const f = v => { v/=255; return v <= 0.03928 ? v/12.92
                                     : Math.pow((v+0.055)/1.055, 2.4); };
            return 0.2126*f(c[0]) + 0.7152*f(c[1]) + 0.0722*f(c[2]);
          };
          const num = s => { const m=(s||'').match(/[\\d.]+/g);
                             return m && m.length>=3 ? m.slice(0,3).map(Number) : null; };
          const ground = el => {
            for (let n = el; n; n = n.parentElement) {
              const raw = getComputedStyle(n).backgroundColor;
              const m = num(raw), a = (raw.match(/[\\d.]+/g) || []);
              if (m && (a.length < 4 || parseFloat(a[3]) > 0.85)) return m;
            }
            return null;
          };
          const out = {};
          const sel = '.menu-row-label, .menu-item span,'
                    + ' .menu-item .menu-item-text, .menu-item.danger span,'
                    + ' .header .btn-label,'
                    + ' .menu-version, .menu-row-note, .autosave-status';
          let i = 0;
          for (const el of document.querySelectorAll(sel)) {
            const r = el.getBoundingClientRect();
            if (!r.width || !r.height) { i++; continue; }
            const fg = num(getComputedStyle(el).color);
            const bg = ground(el);
            if (!fg || !bg) { i++; continue; }
            const a = rel(fg), b = rel(bg);
            // Keyed by ordinal so the two themes line up element for element.
            out['#' + i] = {
              ratio: (Math.max(a,b)+0.05)/(Math.min(a,b)+0.05),
              what: (el.className.toString().slice(0,26) || el.tagName)
                    + ' ' + getComputedStyle(el).color
                    + ' on rgb(' + bg.join(',') + ')'
            };
            i++;
          }
          return out;
        }"""
        seen = {}
        for mode in ("dark", "light"):
            page.evaluate("(m) => window.SkriblTheme.set(m)", mode)
            page.wait_for_timeout(300)
            seen[mode] = page.evaluate(SWEEP)
        check(f"{label}: the menu rows are actually on screen to be measured",
              len(seen["light"]) >= 6,
              f"{len(seen['light'])} laid-out element(s) — a sweep over a "
              f"closed menu measures nothing and passes")

        # A drop is only a defect if it lands somewhere that matters. The ramp
        # is mirrored by RELATIONSHIP, not by arithmetic — that is the whole
        # design note above the light block — so small movements either way are
        # the point rather than a regression: a first attempt at this failed on
        # 6.72 -> 5.90 and 17.49 -> 17.04, neither of which anyone can see.
        #
        # So: a drop is allowed if what it lands on still clears AA outright,
        # and otherwise it may not lose more than 15%. #f4326f, the defect this
        # is for, went 5.5 -> 3.32 — under AA and down 40%, caught twice over.
        floor, drops = [], []
        for key, light_m in seen["light"].items():
            dark_m = seen["dark"].get(key)
            if light_m["ratio"] < 3.0:
                floor.append(f"{light_m['what']} {light_m['ratio']:.2f}:1")
            if (dark_m and light_m["ratio"] < 4.5
                    and light_m["ratio"] < dark_m["ratio"] * 0.85):
                drops.append(f"{light_m['what']} {dark_m['ratio']:.2f} -> "
                             f"{light_m['ratio']:.2f}")
        check(f"{label}: nothing in light mode falls below 3:1",
              not floor, "; ".join(floor[:4]))
        check(f"{label}: no text is MEANINGFULLY less legible in light than dark",
              not drops,
              "; ".join(drops[:4]) or "an ink tuned for a dark ground washing "
              "out on a light one shows up here as a drop under AA")
        # Printed, not asserted. The two dimmest things on the surface are the
        # version footer (tertiary by design, dim in both themes) and white on
        # the accent (identical in both themes, and older than this work) —
        # neither is a light-mode question, and both are worth a number.
        neutral = [(m["ratio"], m["what"]) for m in seen["light"].values()
                   if "on rgb(124,92,255)" not in m["what"]]
        if neutral:
            r, what = min(neutral)
            print(f"    dimmest light-mode text on a neutral ground: {r:.2f}:1 ({what})")
        page.close()

    print("\nTHEME — a new drawing starts on the theme's ground, and a drawing keeps its own")
    # The owner, of the mock (both editors, phone and desk): "Do Paper." The
    # theme picks only where a NEW drawing starts (rule 3); every check below is
    # on both editors, because each wires lib/canvasground.js on its own.
    _VP = {"width": 1000, "height": 900}
    _STORED = """() => { const r = localStorage.getItem(AUTOSAVE_KEY); if (!r) return false;
        const d = JSON.parse(r);
        return !!((d.strokes && d.strokes.length)
                  || (d.frames && d.frames.some(f => f.strokes && f.strokes.length))); }"""
    for label, path in SURFACES:
        # A NEW DRAWING, nothing stored, in each theme the OS can ask for.
        for scheme, want in (("light", PAPER), ("dark", DARK_GROUND)):
            pg = browser.new_page(viewport=_VP, color_scheme=scheme)
            browsing.goto(pg, BASE, path, settle=400)
            st = ground(pg, label)
            check(f"{label}: a new drawing in the {scheme} theme starts on {GROUND_NAME[want]}: painted, lit, saved",
                  on(st, want), str(st))
            if label == "Flip":
                check(f"Flip: ...and its page in the strip is on {GROUND_NAME[want]} too",
                      near(st["thumb"], want), f"thumbnail {st['thumb']}")
            if scheme == "light":
                # STILL BLANK, so it follows a switch, there and back.
                theme(pg, "dark")
                st = ground(pg, label)
                check(f"{label}: a blank canvas follows the theme to the dark canvas",
                      on(st, DARK_GROUND), str(st))
                theme(pg, "light")
                st = ground(pg, label)
                check(f"{label}: ...and back to Paper", on(st, PAPER), str(st))
                # A STROKE ends that: it is a drawing now, and stays on Paper.
                draw_line(pg, label)
                theme(pg, "dark")
                st = ground(pg, label)
                check(f"{label}: once there is a stroke, the theme never moves the ground",
                      on(st, PAPER), str(st))
            pg.close()

        # A GROUND PICKED BY HAND stays, whatever it is. Two picks are the
        # cases that matter. Paper in the dark theme is the ground the light
        # theme starts on, so a follow that compared colours instead of
        # remembering what it gave would take it for its own after light and
        # back, and paint it dark. Paper in the light theme is the swatch
        # already lit, so only the pick itself says the person chose it.
        for scheme, there, pick in (("light", "dark", WHITE), ("dark", "light", PAPER),
                                    ("light", "dark", PAPER)):
            pg = browser.new_page(viewport=_VP, color_scheme=scheme)
            browsing.goto(pg, BASE, path, settle=400)
            pg.evaluate("(c) => document.querySelector(`.bg-swatch[data-bg=\"${c}\"]`).click()", pick)
            pg.wait_for_timeout(200)
            theme(pg, there)
            theme(pg, scheme)
            st = ground(pg, label)
            check(f"{label}: {GROUND_NAME[pick]} picked by hand in the {scheme} theme is kept through {there} and back",
                  on(st, pick), str(st))
            pg.close()

        # A RESTORED DRAFT keeps its own: drawn on the dark canvas, reopened
        # with the light theme chosen.
        pg = browser.new_page(viewport=_VP, color_scheme="dark")
        browsing.goto(pg, BASE, path, settle=400)
        draw_line(pg, label)
        pg.wait_for_function(_STORED, timeout=10000)
        pg.evaluate("() => window.SkriblTheme.set('light')")
        browsing.goto(pg, BASE, path, settle=400)
        st = ground(pg, label)
        check(f"{label}: a draft drawn on the dark canvas reopens on it in the light theme",
              pg.evaluate("() => document.documentElement.getAttribute('data-theme')") == "light"
              and on(st, DARK_GROUND), str(st))
        pg.close()

        # NEW SKRIBL is a new drawing: it starts on the theme's ground, and
        # its Undo brings back the ground the drawing had.
        pg = browser.new_page(viewport=_VP, color_scheme="light")
        browsing.goto(pg, BASE, path, settle=400)
        pg.evaluate("(c) => document.querySelector(`.bg-swatch[data-bg=\"${c}\"]`).click()", DARK_GROUND)
        draw_line(pg, label)
        if label == "Pad":
            pg.evaluate("() => document.getElementById('menuBtn').click()")
            pg.wait_for_timeout(400)
            pg.evaluate("() => document.getElementById('clearMenuItem').click()")    # arms
            pg.evaluate("() => document.getElementById('clearMenuItem').click()")    # confirms
        else:
            pg.evaluate("() => document.getElementById('miClearAll').click()")
            pg.evaluate("() => document.getElementById('miClearAll').click()")
        pg.wait_for_timeout(600)
        st = ground(pg, label)
        check(f"{label}: New Skribl in the light theme starts on Paper",
              on(st, PAPER), str(st))
        if label == "Pad":
            pg.click(".toast-action")
        else:
            pg.evaluate("() => document.getElementById('clearUndo').click()")
        pg.wait_for_timeout(700)
        st = ground(pg, label)
        check(f"{label}: ...and its Undo brings back the dark canvas the drawing was on",
              on(st, DARK_GROUND), str(st))
        pg.close()

    # NO FLASH OF THE WRONG GROUND. The Pad's canvas is dark in the sheet, and
    # Paper reaches it from a deferred script; with every script blocked, the
    # light theme's own rule has to have put Paper there already. Flip's #pad
    # wears the light chrome's raised surface until its script runs, which is
    # light in this theme and so no flash.
    naked = browser.new_page(viewport=_VP, color_scheme="light")
    naked.route(SCRIPT_FILE, lambda route: route.abort())
    naked.goto(BASE + "/", wait_until="domcontentloaded")
    naked.wait_for_timeout(300)
    _px = painted(naked, "Pad")
    check("Pad: in the light theme the canvas is Paper before any script has run",
          near(_px, PAPER), f"painted {_px} with every script file blocked — a dark "
          f"frame first is a flash on every load of a new drawing")
    naked.close()

    print("\nTHEME — one setting, shared by the two surfaces")
    page = browser.new_page(viewport={"width": 1000, "height": 900})
    browsing.goto(page, BASE, "/")
    page.evaluate("() => window.SkriblTheme.set('light')")
    browsing.goto(page, BASE, "/flip")
    check("light chosen on Pad is light on Flip",
          page.evaluate("() => document.documentElement.getAttribute('data-theme')") == "light",
          "Tips is one setting for both editors and so is this — being asked "
          "twice for the same preference is being asked once too often")
    page.evaluate("() => window.SkriblTheme.set('dark')")
    page.wait_for_timeout(200)
    check("...and turning it off on Flip turns it off",
          page.evaluate("() => document.documentElement.getAttribute('data-theme')") is None
          and page.evaluate(f"() => localStorage.getItem('{KEY}')") == "dark")

    print("\nTHEME — the player follows the URL when it is embedded, and only then")
    # v288, the owner's call: an EMBEDDED player follows its host, and the URL
    # beats everything else; v292: bare, it follows the OS like every page. An in-post box reads the host's tokens (verify_
    # inline pins that); an iframed /s/<id> cannot see the host's attribute or
    # its storage, so the host passes ?theme=light|dark and the boot script
    # stamps it before first paint. The player page never carried the boot
    # script or the light ramp before, so every line here was red on v287.
    import json as _json
    import urllib.request as _ur
    _req = _ur.Request(BASE + "/api/skribls", method="POST",
                       data=_json.dumps({"frames": [{"strokes": [], "strokeGroups": [],
                                                     "background": {"color": "#101418"}}],
                                         "title": "Theme fixture"}).encode(),
                       headers={"Content-Type": "application/json"})
    with _ur.urlopen(_req, timeout=15) as _r:
        _pid = _json.loads(_r.read())["id"]
    _player = "/s/" + _pid

    def _attr(pg_):
        return pg_.evaluate("() => document.documentElement.getAttribute('data-theme')")

    def _body_lum(pg_):
        return lum(parse(pg_.evaluate("() => getComputedStyle(document.body).backgroundColor")))

    # Every page here is opened with an OS set to LIGHT: bare, it follows the
    # OS since v292 — so the bare case reads light, and the parameter cases
    # show the URL winning over both the OS and the stored choice.
    for _q, _want, _why in (("", "light", "no parameter: follows the OS, which says light"),
                            ("?theme=light", "light", "the host said light"),
                            ("?theme=banana", "light", "an unknown value is ignored, and the OS is followed"),
                            ("?theme=dark", None, "the host said dark on a light OS"),
                            ("?theme=light&x=1", "light", "the parameter is read wherever it sits")):
        pg3 = browser.new_page(viewport={"width": 1000, "height": 900}, color_scheme="light")
        pg3.goto(BASE + _player + _q, wait_until="load")
        pg3.wait_for_timeout(600)
        check(f"player {_q or '(bare)'}: {_why}", _attr(pg3) == _want,
              f"data-theme={_attr(pg3)!r}")
        if _want == "light":
            check(f"player {_q}: ...and the chrome is actually light",
                  _body_lum(pg3) > 150, f"body luminance {_body_lum(pg3):.0f}")
        pg3.close()

    # The URL beats a stored preference — for an embed the HOST decides.
    pg3 = browser.new_page(viewport={"width": 1000, "height": 900})
    pg3.goto(BASE + "/", wait_until="load")
    pg3.wait_for_timeout(500)
    pg3.evaluate(f"() => localStorage.setItem('{KEY}', 'light')")
    pg3.goto(BASE + _player + "?theme=dark", wait_until="load")
    pg3.wait_for_timeout(600)
    check("player ?theme=dark overrides a stored light preference",
          _attr(pg3) is None, f"data-theme={_attr(pg3)!r}")
    pg3.goto(BASE + _player, wait_until="load")
    pg3.wait_for_timeout(600)
    check("...and without the parameter the stored preference is back",
          _attr(pg3) == "light", f"data-theme={_attr(pg3)!r}")
    pg3.close()

    # THE PAGES THAT ALSO LOAD lib/theme.js (v315). The player above does not,
    # which is why every row there was green while theme.js's own apply(get())
    # at load undid the parameter a moment later on every page that does --
    # including the compose Pad a host iframes. Sampled after that script has
    # run, with a stored DARK the URL must beat.
    pg4 = browser.new_page(viewport={"width": 1000, "height": 900}, color_scheme="dark")
    pg4.goto(BASE + "/", wait_until="load")
    pg4.evaluate(f"() => localStorage.setItem('{KEY}', 'dark')")
    for _path in ("/", "/flip", "/gallery", "/library", "/skribl-pad?compose=1"):
        _u = _path + ("&" if "?" in _path else "?") + "theme=light"
        pg4.goto(BASE + _u, wait_until="load")
        pg4.wait_for_function("() => !!window.SkriblTheme", timeout=10000)
        pg4.wait_for_timeout(300)
        check(f"{_u}: the URL still wins after lib/theme.js has run",
              _attr(pg4) == "light", f"data-theme={_attr(pg4)!r} with 'dark' stored")
    pg4.evaluate("() => window.SkriblTheme.set('dark')")
    check("...and a choice made in the menu beats the URL for the rest of the page",
          _attr(pg4) is None, f"data-theme={_attr(pg4)!r}")
    pg4.close()

    # No flash: light lands with every script file blocked, so it was the
    # inline boot and not something deferred.
    naked3 = browser.new_page(viewport={"width": 1000, "height": 900})
    naked3.route(SCRIPT_FILE, lambda route: route.abort())
    naked3.goto(BASE + _player + "?theme=light", wait_until="domcontentloaded")
    check("player ?theme=light is applied with EVERY script file blocked",
          _attr(naked3) == "light", "the embed would flash dark before going light")
    naked3.close()

    print("\nTHEME — Loop Detail's waveform follows the theme (owner, light theme)")
    # lib/loopwave.js painted the zoomed waveform's ground as a literal
    # '#161a22' -- dark --surface-well -- in every theme, so in light mode Loop
    # Detail was a black slab inside a light drawer. The canvas's own CSS
    # background is the one owner of that colour now. Pixel-read, both editors:
    # the ground is sampled at the canvas's left edge with the loop placed in
    # the middle of a 6s track, so the sample is context, never the loop tint.
    import io as _io, math as _math, struct as _struct, wave as _wave
    _b = _io.BytesIO()
    with _wave.open(_b, "wb") as _w:
        _w.setnchannels(1); _w.setsampwidth(2); _w.setframerate(8000)
        _w.writeframes(b"".join(_struct.pack("<h", int(6000 * _math.sin(i / 9))) for i in range(8000 * 6)))
    _WAV = _b.getvalue()
    for _nm, _route in (("Pad", "/skribl-pad"), ("Flip", "/flip")):
        _q = browser.new_page(viewport={"width": 1000, "height": 1100})
        _q.goto(BASE + _route + "?theme=light", wait_until="load"); _q.wait_for_timeout(700)
        _q.evaluate("() => window.SkriblHints && window.SkriblHints.hide()")
        browsing.pad_drawer(_q, "music")
        _q.set_input_files("#musicInput", {"name": "t.wav", "mimeType": "audio/wav", "buffer": _WAV})
        _q.wait_for_function("() => typeof currentAudioBuffer !== 'undefined' && !!currentAudioBuffer", timeout=20000)
        _q.evaluate("() => { const t = document.getElementById('fineTuneToggle');"
                    " if (t && t.getAttribute('aria-pressed') !== 'true') t.click(); }")
        _q.wait_for_timeout(500)
        _q.evaluate("() => { trimStart = 2.5; trimEnd = 3.5; updateTrimUI(); }")
        _q.wait_for_timeout(500)
        _px = _q.evaluate("""() => { const c = document.getElementById('zoomWaveformCanvas');
            if (!c || !c.width) return null;
            const d = c.getContext('2d').getImageData(1, 1, 1, 1).data;
            return [d[0], d[1], d[2]]; }""")
        check(f"{_nm}: in light mode, Loop Detail's ground is light, not a dark slab",
              _px is not None and lum(_px) > 150,
              f"ground pixel {_px} — lum {lum(_px) if _px else None}; a dark literal in lib/loopwave.js ignores the theme")
        _q.close()

    print("\nTHEME — a browser that refuses storage still renders, and follows the OS")
    page2 = browser.new_page(viewport={"width": 1000, "height": 900}, color_scheme="light")
    page2.add_init_script("""
      Object.defineProperty(window, 'localStorage', {
        configurable: true,
        get() { throw new Error('SecurityError: storage is disabled'); }
      });
    """)
    errs = []
    page2.on("pageerror", lambda e: errs.append(str(e)))
    browsing.goto(page2, BASE, "/")
    check("a page whose localStorage throws on ACCESS still loads, following the OS (light here)",
          page2.evaluate("() => document.documentElement.getAttribute('data-theme')") == "light",
          "; ".join(errs[:2]) or "with no choice readable, the OS is the choice — in the boot AND the lib, or it flashes")
    check("...and the theme code did not throw",
          not [e for e in errs if "theme" in e.lower() or "storage is disabled" in e],
          "; ".join(errs[:2]))
    page2.close()
    page.close()
    browser.close()

bad = [r for r in results if not r[0]]
print(f"\n{'=' * 62}\n{len(results) - len(bad)}/{len(results)} passed"
      + ("" if not bad else "  FAILURES: " + ", ".join(n for _, n in bad)))
sys.exit(1 if bad else 0)
