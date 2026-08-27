"""Light mode: the setting, the flash, and the one thing that must NOT follow it.

Skribl was drawn dark. The palette, the two brand marks, the accent purple and
every shadow in the sheet were chosen against a near-black ground, and v230/v232
moved 179 neutral literals into `:root` so a second ramp could exist at all.
This suite guards the four things that make that ramp a feature rather than a
liability.

1. IT IS OPT-IN. There is deliberately no `@media (prefers-color-scheme: light)`
   rule. A first pass had one, and it flipped every user on a light desktop —
   including this harness's headless Chromium, which reports `light` — into a
   theme nobody had asked for. Following the OS is a product decision the owner
   has not made, so the assertion here is that the default load is dark no
   matter what the OS says. Both media preferences are emulated, because a rule
   that only misfires under one of them is exactly what got shipped last time.

2. IT DOES NOT FLASH. The setting lives in localStorage, which no stylesheet can
   read. Every script in both templates is deferred (verify_surfaces.py pins
   that), so if the attribute were stamped by lib/theme.js the browser would
   already have painted a dark frame — a black flash on every navigation, for
   the users who chose light specifically to avoid one. The inline boot script
   in <head> is what prevents it, and the test for it is to serve the page with
   EVERY external script blocked: if the theme is still right, nothing deferred
   was needed to get it.

3. THE CANVAS DOES NOT FOLLOW IT. This is the load-bearing rule and the reason
   the whole job was scoped to "chrome only". A drawing's ground is part of the
   drawing — it is what gets exported, posted, and seen by other people — so a
   UI preference must never repaint it. The check is a pixel one, taken from the
   middle of the canvas in both themes: a token that leaks into the canvas would
   change it, and no amount of reading CSS would tell you that as plainly.

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
import pathlib
import re
import sys

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


def check(name, ok, detail=""):
    results.append((bool(ok), name))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  — {detail}" if detail else ""))


# ---------------------------------------------------------------- static ----
css = CSS.read_text(encoding="utf-8")


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
# which follows no theme, so its ink must not follow one either — and having it
# in :root as a named token is what makes that a visible decision rather than a
# literal somebody missed.
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
# white in both themes) and so is #0d0f14 (the canvas, which is the document's
# colour and follows no theme).
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

check("no prefers-color-scheme rule flips the default for anyone",
      "prefers-color-scheme" not in re.sub(r"/\*.*?\*/", "", css, flags=re.S),
      "following the OS would move every user on a light desktop to a theme "
      "they never chose — light is a setting someone turns on")

print("\nTHEME — both surfaces carry the same switch, wired to the same key")
for name in ("skribl_editor.html", "skribl_flip.html"):
    html = (TPL / name).read_text(encoding="utf-8")
    check(f"{name}: has a Theme row",
          'id="themeSeg"' in html and ">Theme<" in html)
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


with sync_playwright() as p:
    browser = p.chromium.launch()

    for label, path in SURFACES:
        print(f"\nTHEME [{label}] — the default is dark whatever the OS says")
        for scheme in ("light", "dark"):
            page = browser.new_page(viewport={"width": 1000, "height": 900},
                                    color_scheme=scheme)
            page.goto(BASE + path, wait_until="load")
            page.wait_for_timeout(500)
            page.evaluate("() => { for (const k of Object.keys(localStorage))"
                          " if (k.indexOf('skribl') === 0) localStorage.removeItem(k); }")
            page.reload(wait_until="load")
            page.wait_for_timeout(700)
            attr = page.evaluate("() => document.documentElement.getAttribute('data-theme')")
            bg = parse(page.evaluate(
                "() => getComputedStyle(document.body).backgroundColor"))
            check(f"{label}: an OS set to {scheme} still loads dark",
                  attr is None and bg is not None and lum(bg) < 60,
                  f"data-theme={attr!r} body luminance {lum(bg):.0f}")
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
        naked.route("**/*.js", lambda route: route.abort())
        naked.goto(BASE + path, wait_until="domcontentloaded")
        check(f"{label}: light is applied with EVERY script file blocked",
              naked.evaluate("() => document.documentElement.getAttribute('data-theme')") == "light",
              "if this needs a deferred script, users who chose light get a "
              "black flash on every single navigation")
        naked.close()

        print(f"THEME [{label}] — the chrome flips and the canvas does not")
        dark_px = None
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
            # A real pixel from the middle of the drawing surface, not the CSS
            # value: the canvas is painted by the app, so only its bitmap can
            # say whether the theme reached it.
            px = page.evaluate("""() => {
              const c = document.querySelector('canvas');
              if (!c || !c.width) return null;
              const g = c.getContext('2d', { willReadFrequently: true });
              const d = g.getImageData(Math.floor(c.width / 2),
                                       Math.floor(c.height / 2), 1, 1).data;
              return [d[0], d[1], d[2], d[3]];
            }""")
            shots[mode]["px"] = px
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
        check(f"{label}: the CANVAS pixel is IDENTICAL in both themes",
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
            + ' .icon-btn, .tool-btn, .tool-open, .menu-item, .flip-menu-item');
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
          const sel = '.menu-row-label, .fm-label, .menu-item span,'
                    + ' .flip-menu-item .mi-tx, .menu-item.danger span,'
                    + ' .flip-menu-item.danger .mi-tx, .header .btn-label,'
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

    print("\nTHEME — one setting, shared by the two surfaces")
    page = browser.new_page(viewport={"width": 1000, "height": 900})
    page.goto(BASE + "/", wait_until="load")
    page.wait_for_timeout(600)
    page.evaluate("() => window.SkriblTheme.set('light')")
    page.goto(BASE + "/flip", wait_until="load")
    page.wait_for_timeout(700)
    check("light chosen on Pad is light on Flip",
          page.evaluate("() => document.documentElement.getAttribute('data-theme')") == "light",
          "Tips is one setting for both editors and so is this — being asked "
          "twice for the same preference is being asked once too often")
    page.evaluate("() => window.SkriblTheme.set('dark')")
    page.wait_for_timeout(200)
    check("...and turning it off on Flip turns it off",
          page.evaluate("() => document.documentElement.getAttribute('data-theme')") is None
          and page.evaluate(f"() => localStorage.getItem('{KEY}')") == "dark")

    print("\nTHEME — a browser that refuses storage still renders")
    page2 = browser.new_page(viewport={"width": 1000, "height": 900})
    page2.add_init_script("""
      Object.defineProperty(window, 'localStorage', {
        configurable: true,
        get() { throw new Error('SecurityError: storage is disabled'); }
      });
    """)
    errs = []
    page2.on("pageerror", lambda e: errs.append(str(e)))
    page2.goto(BASE + "/", wait_until="load")
    page2.wait_for_timeout(900)
    check("a page whose localStorage throws on ACCESS still loads dark",
          page2.evaluate("() => document.documentElement.getAttribute('data-theme')") is None,
          "; ".join(errs[:2]) or "falls back to the app as it has always looked")
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
