"""Accessibility across every page, out of verify_a11y.py: what is seen and
pressed, page by page.

WHY THIS IS ITS OWN SUITE. verify_a11y.py ran past its 600-second budget on
GitHub's PostgreSQL shard after #663 (its every check passing until the kill:
476s on the run before, 520 on the SQLite shard of the same run, over 600 on
the PostgreSQL one), so the sections that each open a browser of their own
moved here whole, as verify_watchfull.py left verify_parity.py at the v323
seal. verify_a11y.py keeps the keyboard and assistive-technology contracts
that share its one browser (sections 0 to 14, NAMES, 10c and 6c). Nothing
here changed in what it asks.

SECTION 6   — no meaningful text under the AA contrast floor (the stylesheet's
              tokens, on every surface they are used on).
SECTION 15  — the empty-canvas hint and the grid are legible on both editors,
              on any canvas.
SECTION 6d  — the pages with their own sheets: every small text clears 4.5:1
              on what is behind it.
SECTION 16  — Play and Stop are one button, and its name follows its face.
SECTION 17  — a tap leaves nothing lit, on either editor.
SECTION 18  — every control you can see has a name, on a desk as on a phone.
SECTION 17b — every hover rule sits behind the guard, whatever state would
              show it.
SECTION 19  — WAVE's error rules find nothing, on every page, fresh or filled.
SECTION 20  — no words at 10px or under (WAVE's very small text).

Requires a running server:
    ./harness/run_harness.sh verify_a11ypages.py
"""
import json
import math
import pathlib
import re
import struct
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]

from playwright.sync_api import sync_playwright
from assertions import make_check
import browsing
import os

BASE = os.environ.get("SKRIBL_BASE", "http://127.0.0.1:5001")

results = []


check = make_check(results)


# ---------------------------------------------------------------- contrast
def _lin(c):
    c = c / 255.0
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def _lum(hex_):
    h = hex_.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return 0.2126 * _lin(r) + 0.7152 * _lin(g) + 0.0722 * _lin(b)


def ratio(fg, bg):
    a, b = _lum(fg), _lum(bg)
    hi, lo = max(a, b), min(a, b)
    return (hi + 0.05) / (lo + 0.05)


# ---------------------------------------------------------------- media
# A one-second WAV for the music trim's time bubbles (A11Y 20), generated so
# the suite carries no binary fixture. Same shape as verify_a11y's.
def _wav1(rate=8000):
    frames = b"".join(struct.pack("<h", int(12000 * math.sin(2 * math.pi * 440 * i / rate))) for i in range(rate))
    return (b"RIFF" + struct.pack("<I", 36 + len(frames)) + b"WAVEfmt "
            + struct.pack("<IHHIIHH", 16, 1, 1, rate, rate * 2, 2, 16)
            + b"data" + struct.pack("<I", len(frames)) + frames)


# The accessible name as the accessibility tree computes it (verify_a11y's
# NAMES section reads it the same way).
def _ax_name(ctx, pg, sel):
    cdp = ctx.new_cdp_session(pg)
    cdp.send("Accessibility.enable")
    doc = cdp.send("DOM.getDocument", {"depth": -1})
    node = cdp.send("DOM.querySelector",
                    {"nodeId": doc["root"]["nodeId"], "selector": sel})
    if not node.get("nodeId"):
        return "(absent)"
    ax = cdp.send("Accessibility.getPartialAXTree",
                  {"nodeId": node["nodeId"], "fetchRelatives": False})
    for n in ax.get("nodes", []):
        if n.get("ignored"):
            continue
        return (n.get("name") or {}).get("value", "")
    return "(ignored)"


# The two posts verify_a11y made before these sections ran in it, so the pages
# are read as they were there. Every suite starts on a fresh database: without
# the public one, the Gallery and the feed that A11Y 6d reads are empty, and
# their tile's words are never measured.
import urllib.request as _ur
for _title, _vis in (("Modal census fixture", "public"), ("Heading fixture", None)):
    _post = {"frames": [{"strokes": [], "strokeGroups": [], "background": {"color": "#101418"}}],
             "title": _title}
    if _vis:
        _post["visibility"] = _vis
    _req = _ur.Request(BASE + "/api/skribls", method="POST", data=json.dumps(_post).encode(),
                       headers={"Content-Type": "application/json"})
    with _ur.urlopen(_req, timeout=15) as _r:
        _pid = json.loads(_r.read())["id"]     # the last, the share link A11Y 18 reads


# ------------------------------------------------------------------ section 6
print("\nA11Y 6 — no meaningful text under the AA contrast floor")
# Computed from the stylesheet rather than sampled from a screenshot: a token
# used on four surfaces has four ratios, and the failing one is whichever
# surface happens not to be in the screenshot.
_css = (ROOT / "skribl" / "static" / "styles.css").read_text(encoding="utf-8")


def _token(name):
    m = re.search(r"--%s:\s*(#[0-9a-fA-F]{6})" % re.escape(name), _css)
    return m.group(1) if m else None


SURFACES = ["surface-base", "surface-raised", "surface-panel", "surface-control"]
_surf = {s: _token(s) for s in SURFACES}
check("the surface ramp resolves", all(_surf.values()), str(_surf))

# The tokens that CANNOT pass AA — see the note at --text-dim's definition.
# --text-dim survives for disabled controls and placeholders, where the
# requirement does not apply. What this asserts is that nothing a user READS
# uses one, and (below) that one which nothing uses at all does not exist.
#
# The list keeps the names v281 DELETED, deliberately: it is what stops them
# being reintroduced as definitions, and the census below is what tells the
# difference between "gone" and "back, unused, waiting to be picked up".
FAILING = ("text-faint", "text-dim", "text-faint-2")
_body = re.sub(r"/\*.*?\*/", "", _css, flags=re.S)

# The permitted uses: disabled controls and placeholders, where WCAG's text
# contrast requirement does not apply. A ratchet — it may shrink and must never
# grow without a reason written here.
#
# THE FIRST VERSION OF THIS GATE WAS VACUOUS, and only a mutation said so. Its
# exempt pattern included `--text-`, meant to skip the lines that DEFINE the
# tokens — and `var(--text-dim)` contains `--text-`, so it skipped every USE as
# well. Putting a failing token back on .tune-hint left the suite at 37/37.
# The definitions are excluded by shape instead: a definition is `--name:` at
# the start of a declaration, a use is `var(--name)`.
_EXEMPT = re.compile(r":disabled|::placeholder|:not\(:checked\)|\[disabled\]")
_DEFINITION = re.compile(r"^\s*--[a-z0-9-]+\s*:")
_bad = []
for _line in _body.split("\n"):
    if _DEFINITION.match(_line):
        continue
    if not any(f"var(--{t})" in _line for t in FAILING):
        continue
    if _EXEMPT.search(_line):
        continue
    _bad.append(_line.strip()[:90])
check("no readable text uses a token that fails AA",
      not _bad,
      "; ".join(_bad[:4]) + (f" (+{len(_bad) - 4} more)" if len(_bad) > 4 else ""))

# A DEFINED TOKEN IS AN INVITATION. v281 found --text-faint and --text-faint-2
# still in :root — the v278 audit had taken them off the last things they
# coloured (--text-faint-2 was on .accordion-count at 3.47:1) and left the
# definitions behind. Nothing referenced them, so the assertion above was green
# and stayed green; the trap is that the next person wanting faint text reaches
# for the faintest name in the ramp and reintroduces the finding. Both were
# deleted. What must hold from here is narrower than "unused tokens are bad":
# a token on THIS list either earns its place in a context the requirement does
# not reach, or it does not exist.
_defined = {t for t in FAILING
            if re.search(r"^\s*--%s\s*:" % re.escape(t), _css, re.M)}
_used = {t for t in FAILING if f"var(--{t})" in _body}
_idle = sorted(_defined - _used)
check("no failing token is defined with nothing using it",
      not _idle,
      ", ".join("--" + t for t in _idle) +
      " — defined, referenced by no rule, and unable to pass: use it somewhere "
      "the contrast requirement does not reach, or delete the definition"
      if _idle else
      f"{len(_defined)} of {len(FAILING)} defined, each used: " +
      ", ".join("--" + t for t in sorted(_defined)))

_muted = _token("text-muted")
_worst = min(ratio(_muted, s) for s in _surf.values())
check("the token that replaced them clears 4.5:1 on EVERY surface",
      _worst >= 4.5,
      f"worst {_worst:.2f}:1 — a token that passes on the darkest panel and "
      "fails on the lightest one has not fixed anything")

# The empty-canvas hint is the first thing a new person reads, and it sat at
# ~2.4:1 (title) and ~1.8:1 (the line under it) on the canvas — a smudge in
# daylight on the owner's iPhone. It is a hint, so it stays quieter than a
# control, but it is READ, so it clears AA. Measured from the painted colours on
# both editors, over the dark canvas the first Skribl started on.
print("\nA11Y 15 — the empty-canvas hint and the grid are legible on both editors, on any canvas")
_CANVAS = "#0d0f14"
_HINT = """() => [...document.querySelectorAll('.canvas-empty-hint, .canvas-empty-sub')]
    .filter(e => e.closest('.canvas-empty-hint') && getComputedStyle(e).display !== 'none')
    .map(e => [e.className, getComputedStyle(e).color])"""
def _blend(css, bg):
    v = [float(x) for x in re.findall(r"[\d.]+", css)]
    a = v[3] if len(v) > 3 else 1.0
    b = [int(bg[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join("%02x" % round(a * f + (1 - a) * g) for f, g in zip(v[:3], b))
# ...AND ON A LIGHT CANVAS (owner: "the draw anything canvas starter msg
# doesn't show on a light background", "the grid is white"). The canvas is the
# drawing's colour, so on-canvas ink follows the CANVAS, not the theme: each
# canvas swatch the drawer offers is chosen, then the hint is measured over
# it and the grid's painted line is read from the overlay's own pixels.
_GRIDPX = """(id) => { const g = document.getElementById(id); if (!g || !g.width) return null;
    const d = g.getContext('2d').getImageData(0, Math.floor(g.height / 3), 1, 1).data;
    return [d[0], d[1], d[2], d[3]]; }"""
with sync_playwright() as _hp:
    _hb = _hp.chromium.launch()
    for _route, _grid in (("/", "padGrid"), ("/flip", "flipGrid")):
        for _ground in (_CANVAS, "#ffffff", "#f6f2ea"):
            _pg = _hb.new_page(viewport={"width": 390, "height": 844})
            browsing.goto(_pg, BASE, _route)
            # Grid FIRST, then the canvas colour: the grid already showing has
            # to repaint when the ground under it changes. Every ground is
            # CHOSEN, the dark one too: a new drawing starts on the theme's
            # ground (lib/canvasground.js), and this browser's light scheme
            # makes that Paper.
            _pg.evaluate("() => document.getElementById('gridBtn').click()")
            _pg.evaluate("(c) => document.querySelector('.bg-swatch[data-bg=\"' + c + '\"]').click()", _ground)
            _pg.wait_for_timeout(300)
            _found = _pg.evaluate(_HINT)
            _ratios = {c: round(ratio(_blend(col, _ground), _ground), 2) for c, col in _found}
            check(f"{_route} on {_ground}: the hint's title and its line both clear 4.5:1 on the canvas",
                  len(_ratios) == 2 and min(_ratios.values()) >= 4.5, str(_ratios))
            _px = _pg.evaluate(_GRIDPX, _grid)
            _light = _ground != _CANVAS
            _ok = bool(_px) and _px[3] > 0 and ((max(_px[:3]) < 80) if _light else (min(_px[:3]) > 200))
            check(f"{_route} on {_ground}: the grid is drawn in {'dark' if _light else 'light'} ink",
                  _ok, f"grid line pixel {_px}")
            _pg.close()
    _hb.close()

print("\nA11Y 6d — the pages with their own sheets: every small text clears 4.5:1 on what is behind it")
# v321 preflight (PF-009, PF-011): Gallery, Library and Feed carry their own
# stylesheets, which A11Y 6 never read, and a grey there sat at 3.9:1 on its
# tile; Flip's first-run hint put its "How it works" link at 3.5:1 in light.
# Computed, element by element: the text's colour against the first opaque
# ground behind it, alpha composited, in both themes. Disabled controls are
# exempt, as WCAG exempts them (the Feed's demo of a host's own buttons).
_CONTRAST = r"""() => {
  const lin = c => { c /= 255; return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4); };
  const L = ([r, g, b]) => 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b);
  const rgba = s => { const m = s.match(/[\d.]+/g); if (!m) return null; return [+m[0], +m[1], +m[2], m.length > 3 ? +m[3] : 1]; };
  const over = (top, under) => [0, 1, 2].map(i => top[i] * top[3] + under[i] * (1 - top[3]));
  // GLASS OVER A DRAWING HAS NO COMPUTED GROUND: what is behind the Gallery
  // card's pill is the drawing, blurred through it, which no stylesheet
  // knows. Its words are measured on the pixels instead (verify_galib GALIB
  // 9, both tones at 7:1); here it is the one named exemption, not a pass.
  const glass = el => { for (let e = el; e; e = e.parentElement) {
      const cs = getComputedStyle(e); if (cs.backdropFilter !== 'none' && e.closest('.skribl-inline')) return true;
      const c = rgba(cs.backgroundColor); if (c && c[3] >= 1) return false; } return false; };
  const ground = el => { const stack = []; for (let e = el; e; e = e.parentElement) {
      const c = rgba(getComputedStyle(e).backgroundColor); if (c && c[3] > 0) { stack.push(c); if (c[3] >= 1) break; } }
    let g = [255, 255, 255]; for (let i = stack.length - 1; i >= 0; i--) g = stack[i][3] >= 1 ? stack[i].slice(0, 3) : over(stack[i], g);
    return g; };
  const bad = [];
  for (const el of document.querySelectorAll('body *')) {
    if (el.closest('[disabled], [aria-disabled=true], [hidden], canvas, svg')) continue;
    if (!el.checkVisibility({ opacityProperty: true, visibilityProperty: true, contentVisibilityAuto: true })) continue;
    const own = [...el.childNodes].some(n => n.nodeType === 3 && n.textContent.trim());
    if (!own) continue;
    const cs = getComputedStyle(el); if (cs.visibility === 'hidden' || +cs.opacity === 0) continue;
    const size = parseFloat(cs.fontSize), bold = +cs.fontWeight >= 700;
    if (size >= 24 || (bold && size >= 18.66)) continue;
    const fg = rgba(cs.color); if (!fg) continue;
    if (glass(el)) continue;
    const bg = ground(el); const f = fg[3] < 1 ? over(fg, bg) : fg.slice(0, 3);
    const a = L(f), b = L(bg), ratio = (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05);
    if (ratio < 4.5) bad.push((el.className && typeof el.className === 'string' ? '.' + el.className.split(' ')[0] : el.tagName.toLowerCase())
                              + ' "' + el.textContent.trim().slice(0, 18) + '" ' + ratio.toFixed(2));
  }
  return [...new Set(bad)].slice(0, 8); }"""
with sync_playwright() as _px:
    _bx = _px.chromium.launch()
    for _scheme in ("dark", "light"):
        _cx = _bx.new_context(viewport={"width": 402, "height": 874}, color_scheme=_scheme, is_mobile=True, has_touch=True)
        for _path in ("/gallery", "/library", "/feed"):
            _pg = _cx.new_page(); browsing.goto(_pg, BASE, _path); _pg.wait_for_timeout(1500)
            _low = _pg.evaluate(_CONTRAST)
            check(f"{_scheme} {_path}: no small text under 4.5:1", not _low, "; ".join(_low))
            _pg.close()
        # The first-run hint's action, on Flip, where a new visitor meets it.
        _cy = _bx.new_context(viewport={"width": 402, "height": 874}, color_scheme=_scheme, is_mobile=True, has_touch=True)
        _pg = _cy.new_page(); browsing.goto(_pg, BASE, "/flip"); _pg.wait_for_timeout(2500)
        _ha = _pg.evaluate(_CONTRAST.replace("document.querySelectorAll('body *')", "document.querySelectorAll('.skribl-hint *')"))
        _shown = _pg.evaluate("() => !!document.querySelector('.skribl-hint-action') && !!document.querySelector('.skribl-hint-action').offsetParent")
        check(f"{_scheme}: the first-run hint was there to read (the fixture)", _shown)
        check(f"{_scheme}: ...and its How it works link clears 4.5:1 on the hint", not _ha, "; ".join(_ha))
        _cy.close(); _cx.close()
    _bx.close()

# ------------------------------------------------------------------ section 16
print("\nA11Y 16 — Play and Stop are one button, and its name follows its face")
# THE FACE CHANGED AND THE NAME DID NOT. Press Play on either editor and the
# button turns into a square and the word Stop -- and a screen reader went on
# announcing "Play" (Pad) or "Flip it" (Flip), because both editors swapped the
# icon and the word and never touched aria-label. On a phone the word is
# hidden and aria-label is the ONLY name, so VoiceOver read the opposite of
# what the button does (parity audit; owner: "all yes").
#
# THE MECHANISM, NOT THE ATTRIBUTE: the name is read from the accessibility
# tree (_ax_name), and it is compared with the button's own word in each
# state, so the check pins "the name says what the face says" rather than one
# spelling -- the rest word is the editor's to choose. The word has to CHANGE
# between the two states too, or a button that never left rest would pass.
# Each editor is its own row: they are two controllers, and a fix to one is
# no evidence about the other.
#
# AND THE DESK TOOLTIP. lib/tooltip.js moves `title` into data-tip at load,
# so a title written once and never again left the bubble saying "Play" over
# Stop on a laptop. Read where the bubble reads it.
_PLAY_WORD = """(sel) => { const b = document.querySelector(sel);
  const w = b && b.querySelector('.btn-label, span');
  return w ? w.textContent.trim() : null; }"""


def _draw_stroke(pg, sel, steps=25):
    b = pg.locator(sel).bounding_box()
    pg.mouse.move(b["x"] + 60, b["y"] + 80)
    pg.mouse.down()
    for i in range(steps):
        pg.mouse.move(b["x"] + 60 + (i % 40) * 6, b["y"] + 80 + (i // 40) * 30 + (i % 40) * 2)
        pg.wait_for_timeout(16)
    pg.mouse.up()
    pg.wait_for_timeout(300)


def _js_click(pg, sel, settle=500):
    pg.evaluate("(s) => document.querySelector(s).click()", sel)
    pg.wait_for_timeout(settle)


def _ready_to_play(pg, ed, steps=25):
    """A drawing with something to play: a finished take on the Pad, two pages on Flip."""
    pg.evaluate("() => window.SkriblHints && window.SkriblHints.hide()")
    if ed == "Pad":
        _draw_stroke(pg, "#canvas", steps)      # the first stroke on a blank Pad records
        _js_click(pg, "#recordBtn")             # Done
    else:
        _draw_stroke(pg, "#pad", steps)
        _js_click(pg, "#addcopy", 300)
        _draw_stroke(pg, "#pad", steps)


# The Pad's replay watched at 1/4x (its remembered speed, editor_draw.js), so a
# short stroke is still playing whenever this reads it. Flip loops anyway.
_QUARTER = "try{localStorage.setItem('skribl_replay_rate','0.25')}catch(e){}"

with sync_playwright() as _pt:
    _bt = _pt.chromium.launch()
    # ONE PAGE PER EDITOR AND FORM, shared by this section and the next: the
    # two together first cost verify_a11y nearly three minutes against its
    # ten-minute budget, two thirds of it reloading and redrawing the same
    # drawing for every state. Each page is driven by element.click() and its
    # mouse is never left over a control (section 17 says why).
    _pages = {}
    for _ed, _path in (("Pad", "/"), ("Flip", "/flip")):
        for _form, _vp, _mob in (("phone", {"width": 402, "height": 874}, True),
                                 ("desk", {"width": 1280, "height": 860}, False)):
            _cx = _bt.new_context(viewport=_vp, color_scheme="dark", is_mobile=_mob, has_touch=_mob)
            _cx.add_init_script(_QUARTER + "try{localStorage.setItem('skribl_theme_v1','dark')}catch(e){}")
            _pg = _cx.new_page()
            browsing.goto(_pg, BASE, _path)
            _pg.wait_for_timeout(700)
            _ready_to_play(_pg, _ed, steps=60)
            _pages[(_ed, _form)] = (_cx, _pg)

    for _ed, _btn in (("Pad", "#playBtn"), ("Flip", "#play")):
        _cx, _pg = _pages[(_ed, "phone")]
        _rest = (_pg.evaluate(_PLAY_WORD, _btn), _ax_name(_cx, _pg, _btn))
        _js_click(_pg, _btn, 300)
        _on = (_pg.evaluate(_PLAY_WORD, _btn), _ax_name(_cx, _pg, _btn),
               _pg.evaluate("(s) => document.querySelector(s).classList.contains('playing')", _btn))
        _js_click(_pg, _btn, 300)
        _back = (_pg.evaluate(_PLAY_WORD, _btn), _ax_name(_cx, _pg, _btn))
        check(f"{_ed}: pressing Play really turned the button into Stop (the fixture)",
              _on[2] and _on[0] and _on[0] != _rest[0], f"rest word {_rest[0]!r}, playing word {_on[0]!r}")
        check(f"{_ed}: at rest a screen reader hears the word the button shows",
              _rest[1] == _rest[0], f"name {_rest[1]!r}, word {_rest[0]!r}")
        check(f"{_ed}: while it plays a screen reader hears Stop, as the button shows",
              _on[1] == _on[0], f"name {_on[1]!r}, word {_on[0]!r}")
        check(f"{_ed}: ...and after Stop, the name comes back with the word",
              _back[1] == _back[0] == _rest[0], f"name {_back[1]!r}, word {_back[0]!r}")

        # The desk: the tooltip's words, where lib/tooltip.js keeps them.
        _cx, _pg = _pages[(_ed, "desk")]
        _tip = "(s) => document.querySelector(s).getAttribute('data-tip')"
        _tip_rest = _pg.evaluate(_tip, _btn)
        _js_click(_pg, _btn, 300)
        _tip_on = _pg.evaluate(_tip, _btn)
        _js_click(_pg, _btn, 300)
        _tip_back = _pg.evaluate(_tip, _btn)
        check(f"{_ed} desk: the tooltip over the playing button says Stop",
              _tip_on == "Stop", f"data-tip {_tip_on!r} (at rest {_tip_rest!r})")
        check(f"{_ed} desk: ...and says what Play does again once it stops",
              bool(_tip_back) and _tip_back != "Stop" and _tip_back == _tip_rest,
              f"data-tip {_tip_back!r}, was {_tip_rest!r} before playing")

    # -------------------------------------------------------------- section 17
    print("\nA11Y 17 — a tap leaves nothing lit, on either editor")
    # IOS KEEPS :hover ON WHATEVER WAS TAPPED LAST, until the next tap lands
    # somewhere else. So every unguarded hover rule is a highlight that sticks
    # on a phone: Post stayed brightened behind its own sheet, the ⋯ menu's rows
    # stayed tinted, a tapped swatch stayed blown up to 112%, Flip's page tile
    # stayed lifted 2px and its add buttons lit. Twenty rules across
    # styles.css and flip.css, on some sixty controls across the two editors
    # (owner: "nothing stays lit after a tap on iPhone, on both editors").
    #
    # HOW A PHONE IS ASKED. Chromium with touch emulation reports
    # (hover: none), as an iPhone does, and CDP's CSS.forcePseudoState puts the
    # control into :hover without a pointer -- which is exactly the state a tap
    # leaves on iOS. The WHOLE CHAIN is forced, the control and every ancestor,
    # because a real :hover is on all of them: `.frame:hover .del` is a rule
    # on the tile, not on the button. Then the look of the control, its
    # pseudo-elements, its contents and its ancestors is compared with the look
    # before; anything that moved would stay moved after a tap.
    #
    # THREE WAYS THE FIRST VERSION OF THIS WAS BLIND, each now a guard below:
    #   1. A REAL HOVER IN THE BASELINE. Playwright's click leaves the mouse on
    #      the control it clicked, so the "before" already wore its hover and
    #      forcing changed nothing -- Flip's Play and the add buttons read clean
    #      in the very states they had just been pressed in. Controls are driven
    #      with element.click(), the mouse is parked off the page, and the
    #      census refuses to run while anything at all is :hover.
    #   2. TRANSITIONS. A colour that eases over .15s reads its OLD value the
    #      instant :hover is forced. Transitions are switched off for the
    #      census, and running animations held, so before and after are the
    #      same moment.
    #   3. ONLY BUTTONS. Flip's page tiles are bare <div>s that select on a
    #      tap. The population is the stated control selectors PLUS the top of
    #      every cursor:pointer subtree, and only what a finger can reach --
    #      elementFromPoint at its centre lands on it -- because a covered
    #      control cannot be tapped and so cannot stick.
    # A property that changes between two un-forced reads (a playing replay
    # moves its scrubber) is left out rather than blamed on :hover.
    _FREEZE_ON = """() => { const s = document.createElement('style'); s.id = 'a11y17-freeze';
      s.textContent = '*,*::before,*::after{transition:none!important;animation-play-state:paused!important}';
      document.head.appendChild(s); }"""
    _FREEZE_OFF = "() => { const s = document.getElementById('a11y17-freeze'); if (s) s.remove(); }"
    _TAPPABLE = r"""() => {
      document.querySelectorAll('[data-a11y17]').forEach(e => e.removeAttribute('data-a11y17'));
      const pool = new Set(document.querySelectorAll(
        'button, [role="button"], [role="tab"], [role="slider"], a[href], input, select, label, summary'));
      for (const e of document.body.querySelectorAll('*')) {
        if (getComputedStyle(e).cursor !== 'pointer') continue;
        const up = e.parentElement;
        if (up && getComputedStyle(up).cursor === 'pointer') continue;
        pool.add(e);
      }
      const out = [];
      for (const e of pool) {
        const r = e.getBoundingClientRect();
        if (r.width < 2 || r.height < 2) continue;
        if (r.bottom < 0 || r.top > innerHeight || r.right < 0 || r.left > innerWidth) continue;
        const x = Math.min(Math.max(r.left + r.width / 2, 1), innerWidth - 1);
        const y = Math.min(Math.max(r.top + r.height / 2, 1), innerHeight - 1);
        const hit = document.elementFromPoint(x, y);
        if (!hit || !(hit === e || e.contains(hit))) continue;
        e.setAttribute('data-a11y17', String(out.length));
        out.push((e.id ? '#' + e.id : e.tagName.toLowerCase() + (typeof e.className === 'string' && e.className.trim()
                  ? '.' + e.className.trim().split(/\s+/).join('.') : ''))
                 + ' "' + (e.getAttribute('aria-label') || e.getAttribute('data-tip') || e.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 24) + '"');
      }
      return out; }"""
    _CHAIN = """(n) => { document.querySelectorAll('[data-a11y17-up]').forEach(e => e.removeAttribute('data-a11y17-up'));
      const e = document.querySelector('[data-a11y17="' + n + '"]'); if (!e) return 0; let k = 0;
      for (let p = e; p && p !== document.documentElement; p = p.parentElement) { p.setAttribute('data-a11y17-up', ''); k++; }
      return k; }"""
    _LOOK = r"""(n) => {
      const e = document.querySelector('[data-a11y17="' + n + '"]'); if (!e) return null;
      const P = ['backgroundColor', 'backgroundImage', 'color', 'borderTopColor', 'borderRightColor', 'borderBottomColor',
                 'borderLeftColor', 'boxShadow', 'filter', 'transform', 'scale', 'translate', 'opacity', 'outlineStyle',
                 'outlineColor', 'fill', 'stroke', 'textDecorationLine', 'visibility', 'display'];
      const els = [[e, 'self']];
      for (let p = e.parentElement, i = 1; p && p !== document.documentElement; p = p.parentElement, i++) els.push([p, 'up' + i]);
      e.querySelectorAll('*').forEach((d, i) => els.push([d, 'in' + i]));
      const out = {};
      for (const [el, at] of els) {
        const tag = at + ':' + (el.id ? '#' + el.id : el.tagName.toLowerCase()
                    + (typeof el.className === 'string' && el.className.trim() ? '.' + el.className.trim().split(/\s+/)[0] : ''));
        for (const ps of (el === e ? [null, '::before', '::after'] : [null])) {
          const c = getComputedStyle(el, ps);
          for (const k of P) out[tag + (ps || '') + ' ' + k] = c[k];
        }
      }
      return out; }"""

    def _stuck_after_tap(cx, pg):
        """Force :hover along each reachable control's chain; return (hovered, controls, stuck)."""
        pg.mouse.move(-5, -5)
        pg.evaluate(_FREEZE_ON)
        hovered = pg.evaluate("() => document.querySelectorAll(':hover').length")
        names = pg.evaluate(_TAPPABLE)
        cdp = cx.new_cdp_session(pg)
        cdp.send("DOM.enable"); cdp.send("CSS.enable")
        root = cdp.send("DOM.getDocument", {"depth": 0})["root"]["nodeId"]
        stuck = []
        for n, name in enumerate(names):
            if not pg.evaluate(_CHAIN, n):
                continue
            ids = cdp.send("DOM.querySelectorAll", {"nodeId": root, "selector": "[data-a11y17-up]"})["nodeIds"]
            before = pg.evaluate(_LOOK, n)
            for i in ids:
                cdp.send("CSS.forcePseudoState", {"nodeId": i, "forcedPseudoClasses": ["hover"]})
            held = pg.evaluate(_LOOK, n)
            for i in ids:
                cdp.send("CSS.forcePseudoState", {"nodeId": i, "forcedPseudoClasses": []})
            again = pg.evaluate(_LOOK, n)
            if not (before and held and again):
                continue
            moved = [k for k in held if k in before and before[k] == again.get(k) and held[k] != before[k]]
            if moved:
                k = moved[0]
                stuck.append(f"{name}: {k} {before[k][:40]} -> {held[k][:40]}"
                             + (f" (+{len(moved) - 1} more)" if len(moved) > 1 else ""))
        cdp.detach()
        pg.evaluate(_FREEZE_OFF)
        return hovered, len(names), stuck

    def _opened(pg, st, btn, more):
        if st == "rest":
            return True
        if st == "playing":
            return pg.evaluate("(s) => document.querySelector(s).classList.contains('playing')", btn)
        if st in ("pen drawer", "media drawer"):
            return pg.evaluate(browsing._PAD_CUR) == ("draw" if st == "pen drawer" else "music")
        if st == "settings":
            return pg.evaluate("() => !!document.querySelector('#tuneShell.open')")
        if st == "menu":
            return pg.evaluate("(s) => document.querySelector(s).getAttribute('aria-expanded') === 'true'", more)
        return pg.evaluate("""() => { const b = document.getElementById('postSubmitBtn'); if (!b) return false;
          const r = b.getBoundingClientRect(); const h = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
          return !!h && (h === b || b.contains(h)); }""")

    # THE WHOLE WALK IN THE DARK THEME, AND REST AGAIN IN THE LIGHT ONE. A hover
    # rule is guarded or it is not, whichever theme draws it; the light pass
    # is there for a rule only the light theme writes, and none of today's
    # twenty is one -- each showed in the dark walk. Both themes through every
    # state cost a minute more of a suite that has ten.
    _STATES = ("rest", "playing", "pen drawer", "media drawer", "settings", "menu", "post sheet")
    for _ed, _btn, _more in (("Pad", "#playBtn", "#menuBtn"), ("Flip", "#play", "#moreBtn")):
        _cx, _pg = _pages[(_ed, "phone")]
        check(f"{_ed}: the phone reports (hover: none), as an iPhone does (the fixture)",
              _pg.evaluate("() => matchMedia('(hover: none)').matches"))
        for _st in _STATES:
            if _st == "playing":
                _js_click(_pg, _btn, 450)
                # HELD STILL FOR THE CENSUS ON FLIP. Flip turns its pages on a
                # timer, every 83 ms at 12 fps, and the strip outlines the page
                # on screen -- so a turn between the census's reads of one
                # control moved that outline to the next page and read as a
                # stuck hover (the shared-page walk, 11 Oct: a two-page cycle
                # can match `before` and `again` and still differ in `held`).
                # Paused, as a tap on the drawing pauses it, it is still the
                # playing chrome, and still `playing` (checked below).
                if _ed == "Flip":
                    _pg.evaluate("() => pausePlay()")
            elif _st in ("pen drawer", "media drawer"):
                browsing.pad_drawer(_pg, "draw" if _st == "pen drawer" else "music", settle=500)
            elif _st == "settings":
                _js_click(_pg, "#tuneBtn", 500)
            elif _st == "menu":
                _js_click(_pg, _more, 500)
            elif _st == "post sheet":
                _js_click(_pg, "#postBtn", 800)
            _where = f"{_ed} {_st}"
            check(f"{_where}: the state is open, so its census means something (the fixture)",
                  _opened(_pg, _st, _btn, _more))
            _hov, _n, _stuck = _stuck_after_tap(_cx, _pg)
            check(f"{_where}: nothing is really under a pointer, so the before reads clean (the fixture)",
                  _hov == 0, f"{_hov} elements :hover")
            check(f"{_where}: there are controls to tap ({_n})", _n >= 5,
                  f"found {_n}, expected at least 5")
            if _st == "playing":
                check(f"{_where}: still playing when the census ended (the fixture)",
                      _opened(_pg, _st, _btn, _more))
            check(f"{_where}: no control stays lit after a tap", not _stuck, "; ".join(_stuck[:5]))
            # Close behind, so the next state starts from rest.
            if _st == "playing":
                _js_click(_pg, _btn, 300)
            elif _st in ("pen drawer", "media drawer"):
                browsing.pad_drawer_close(_pg, settle=350)
            elif _st == "settings":
                _js_click(_pg, "#tuneBtn", 350)
            elif _st == "menu":
                _pg.keyboard.press("Escape")
                _pg.wait_for_timeout(350)
        _cx.close()

    for _ed, _path in (("Pad", "/"), ("Flip", "/flip")):
        _cx = _bt.new_context(viewport={"width": 402, "height": 874}, color_scheme="light",
                              is_mobile=True, has_touch=True)
        _cx.add_init_script("try{localStorage.setItem('skribl_theme_v1','light')}catch(e){}")
        _pg = _cx.new_page()
        browsing.goto(_pg, BASE, _path)
        _pg.wait_for_timeout(700)
        _ready_to_play(_pg, _ed)
        _hov, _n, _stuck = _stuck_after_tap(_cx, _pg)
        check(f"light {_ed} rest: the census ran clean and found controls (the fixture)",
              _hov == 0 and _n >= 5, f"{_hov} :hover, {_n} controls")
        check(f"light {_ed} rest: no control stays lit after a tap", not _stuck, "; ".join(_stuck[:5]))
        _cx.close()

    # THE OTHER HALF: A MOUSE STILL LIGHTS THEM. Guarding a rule with a media
    # query that never matches -- a typo, `(hover: hove)` -- would pass every
    # row above and take hover away from the desk too. So the same forcing, on
    # a desk, must still MOVE one control from each family the guard went
    # round: the buttons, the menu rows and the swatches in styles.css, the add
    # buttons and the page tiles in flip.css.
    def _lights_on_desk(cx, pg, sel):
        pg.mouse.move(-5, -5)
        pg.evaluate(_FREEZE_ON)
        found = pg.evaluate("""(sel) => { document.querySelectorAll('[data-a11y17]').forEach(e => e.removeAttribute('data-a11y17'));
          const e = document.querySelector(sel); if (!e) return false; e.setAttribute('data-a11y17', '0'); return true; }""", sel)
        moved = []
        if found:
            c = cx.new_cdp_session(pg)
            c.send("DOM.enable"); c.send("CSS.enable")
            root = c.send("DOM.getDocument", {"depth": 0})["root"]["nodeId"]
            pg.evaluate(_CHAIN, 0)
            ids = c.send("DOM.querySelectorAll", {"nodeId": root, "selector": "[data-a11y17-up]"})["nodeIds"]
            before = pg.evaluate(_LOOK, 0)
            for i in ids:
                c.send("CSS.forcePseudoState", {"nodeId": i, "forcedPseudoClasses": ["hover"]})
            held = pg.evaluate(_LOOK, 0)
            for i in ids:
                c.send("CSS.forcePseudoState", {"nodeId": i, "forcedPseudoClasses": []})
            moved = [k for k in held if held[k] != before.get(k)]
            c.detach()
        pg.evaluate(_FREEZE_OFF)
        return found, moved

    for _ed, _steps in (("Pad", ((None, "#postBtn"), ("pen", ".color-dot:not(.active)"),
                                 ("#menuBtn", "#menuNewTile"))),
                        ("Flip", ((None, "#addblank"), (None, ".frame:not(.on)")))):
        _cx, _pg = _pages[(_ed, "desk")]
        for _open, _sel in _steps:
            if _open == "pen":
                browsing.pad_drawer(_pg, "draw", settle=500)
            elif _open:
                _js_click(_pg, _open, 500)
            _found, _moved = _lights_on_desk(_cx, _pg, _sel)
            check(f"{_ed} desk: a mouse over {_sel} still lights it — the guard matches a real hover",
                  _found and bool(_moved), "control not found" if not _found else "forced :hover changed nothing")
        _cx.close()
    _bt.close()


# ------------------------------------------------------------------ section 18
print("\nA11Y 18 — every control you can see has a name, on a desk as on a phone")
# THREE BUTTONS SAID NOTHING ON A DESK: the Pad's Undo and Redo and Flip's
# Eraser. Each carries its word in a hidden span (.undo-label, .tool-btn-label)
# and its name in `title`; lib/tooltip.js, which runs only on a fine pointer,
# moves the title into data-tip and copies it to aria-label only when the
# control has no name otherwise -- and it counted the HIDDEN word as one. So
# the title went and nothing replaced it: on a phone (no tooltip lib) the three
# were "Undo last stroke", "Redo last stroke" and "Erase...", and on a laptop
# a screen reader heard a bare "button". Found comparing the two editors' names
# for the one Play/Stop round; Flip's Undo and Redo had always carried an
# aria-label and were fine.
#
# READ FROM THE ACCESSIBILITY TREE, every visible control in three states of
# both editors at both sizes: whatever the markup does, a name is what the
# tree computes, and an empty one is the defect.
_NAMED = r"""() => { const out = []; let i = 0;
  for (const e of document.querySelectorAll('button, [role="button"], a[href], [role="tab"], [role="switch"], input, select, textarea')) {
    const r = e.getBoundingClientRect(); if (r.width < 2 || r.height < 2) continue;
    let shown = true;
    for (let p = e; p; p = p.parentElement) { const c = getComputedStyle(p); if (c.display === 'none' || c.visibility === 'hidden') { shown = false; break; } }
    if (!shown) continue;
    e.setAttribute('data-a11y18', String(i)); out.push(e.id ? '#' + e.id : e.tagName.toLowerCase() + '.' + String(e.className || '').trim().split(/\s+/).join('.'));
    i++; }
  return out; }"""


def _nameless(cx, pg):
    labels = pg.evaluate(_NAMED)
    cdp = cx.new_cdp_session(pg)
    cdp.send("Accessibility.enable")
    root = cdp.send("DOM.getDocument", {"depth": -1})["root"]["nodeId"]
    bad = []
    for i, lab in enumerate(labels):
        q = cdp.send("DOM.querySelector", {"nodeId": root, "selector": f'[data-a11y18="{i}"]'})
        if not q.get("nodeId"):
            continue
        ax = cdp.send("Accessibility.getPartialAXTree", {"nodeId": q["nodeId"], "fetchRelatives": False})
        for n in ax.get("nodes", []):
            if n.get("ignored"):
                continue
            if not ((n.get("name") or {}).get("value") or "").strip():
                bad.append(lab)
            break
    cdp.detach()
    return len(labels), bad


with sync_playwright() as _pn:
    _bn = _pn.chromium.launch()
    for _form, _vp, _mob in (("desk", {"width": 1280, "height": 860}, False),
                             ("phone", {"width": 402, "height": 874}, True)):
        for _ed, _path, _more in (("Pad", "/", "#menuBtn"), ("Flip", "/flip", "#moreBtn")):
            _cx = _bn.new_context(viewport=_vp, is_mobile=_mob, has_touch=_mob)
            _pg = _cx.new_page()
            browsing.goto(_pg, BASE, _path)
            _pg.wait_for_timeout(700)
            _pg.evaluate("() => window.SkriblHints && window.SkriblHints.hide()")
            for _st in ("rest", "pen drawer", "menu"):
                if _st == "pen drawer":
                    browsing.pad_drawer(_pg, "draw", settle=500)
                elif _st == "menu":
                    browsing.pad_drawer_close(_pg, settle=300)
                    _pg.evaluate("(s) => document.querySelector(s).click()", _more)
                    _pg.wait_for_timeout(500)
                _n, _bad = _nameless(_cx, _pg)
                check(f"{_form} {_ed} {_st}: every control you can see has a name ({_n} read)",
                      _n >= 10 and not _bad, ", ".join(_bad) or f"only {_n} controls found")
            _cx.close()
    _bn.close()


# ------------------------------------------------------------------ section 17b
print("\nA11Y 17b — every hover rule sits behind the guard, whatever state would show it")
# A11Y 17 walks seven states and forces :hover on what it finds there. A hover
# rule on a control in a sheet that walk never opens -- the export sheet, How it
# works, the photo tab, the music trim, the name drawer's Done -- sticks on an
# iPhone all the same, and seventy-three did after the walk went green. So the
# RULE is asked as well as the paint: every style rule whose selector carries
# :hover, in every stylesheet the page loaded, has to sit inside
# @media (hover: hover).
#
# FROM THE CSSOM, WHAT THE BROWSER PARSED: a grep of the files would count a
# selector quoted in a comment, and would not see a rule nested in @supports or
# under CSS nesting. Sheets another origin serves (fonts) cannot be read and
# are not ours. Each page also says how many hover rules it read, so a walk
# that found none cannot pass for one that found them all guarded.
_HOVER_RULES = r"""() => { const bad = []; let seen = 0, sheets = 0;
  const guardOf = (r) => /\(\s*hover\s*:\s*hover\s*\)/.test(r.conditionText || (r.media && r.media.mediaText) || '');
  const walk = (rules, guarded, at) => { for (const r of rules) {
    if (r.type === CSSRule.MEDIA_RULE) { walk(r.cssRules, guarded || guardOf(r), at); continue; }
    if (r.type === CSSRule.STYLE_RULE) {
      if (/:hover/.test(r.selectorText)) { seen++; if (!guarded) bad.push(at + ' ' + r.selectorText); }
      if (r.cssRules && r.cssRules.length) walk(r.cssRules, guarded, at);
      continue; }
    if (r.cssRules) walk(r.cssRules, guarded, at); } };
  for (const s of document.styleSheets) { let rules; try { rules = s.cssRules; } catch (e) { continue; }
    sheets++; walk(rules, false, (s.href || 'inline').split('/').pop().split('?')[0]); }
  return { bad, seen, sheets }; }"""
with sync_playwright() as _ph:
    _bh = _ph.chromium.launch()
    for _name, _path in (("Pad", "/"), ("Flip", "/flip"), ("the player", "/s/" + _pid)):
        _pg = _bh.new_page(viewport={"width": 402, "height": 874})
        browsing.goto(_pg, BASE, _path)
        _pg.wait_for_timeout(500)
        _r = _pg.evaluate(_HOVER_RULES)
        check(f"{_name}: every :hover rule sits inside @media (hover: hover) ({_r['seen']} read in {_r['sheets']} sheets)",
              _r["seen"] >= 10 and not _r["bad"],
              (", ".join(_r["bad"][:6]) + (f" (+{len(_r['bad']) - 6} more)" if len(_r["bad"]) > 6 else ""))
              if _r["bad"] else (f"only {_r['seen']} hover rules read" if _r["seen"] < 10 else "none outside it"))
        _pg.close()
    _bh.close()

# ------------------------------------------------------------------ section 19
print("\nA11Y 19 — WAVE's error rules find nothing, on every page, fresh or filled")
# THE OWNER RAN WAVE (WebAIM's checker) ON THE LIVE PAD after v325: 76 errors
# and an AIM score of 3.3 out of 10. Sixty-nine were icons: WAVE counts an
# inline <svg> as an image, and one that is neither named nor carries
# aria-hidden="true" ITSELF is "missing alternative text" (an aria-hidden
# wrapper does not count for it, so the icons the tree had already hidden by
# their wrapper were counted too). The other seven: three file pickers with no
# name, two empty <label>s around the custom colour dots, the help book's empty
# title, and the Ask answer's aria-labelledby pointing at a heading that only
# existed after a first answer. Every page had its own share (Flip 89, the
# player 13, the Library 12, the feed 4, the Gallery 2).
#
# THE RULES ARE WAVE'S, read the way WAVE reads them, so this goes red where
# the owner's next WAVE run would. Calibrated against WAVE's own report: on
# v325's Pad at phone size it read exactly WAVE's 69, 3, 2, 1 and 1. Its alerts
# (small text, redundant links and titles, video present) are judgement calls,
# not errors, and are not asked here.
#
# FILLED AS WELL AS FRESH: icons are also written by scripts (a Library row, a
# Gallery card, Flip's page strip), so each page is read with something in it.
_WAVE_ERRORS = r"""() => {
  const out = [];
  const who = el => { let anc = ''; for (let n = el.parentElement; n; n = n.parentElement) if (n.id) { anc = ' in #' + n.id; break; }
    const cls = (el.getAttribute('class') || '').trim().split(/\s+/).filter(Boolean)[0];
    return el.tagName.toLowerCase() + (el.id ? '#' + el.id : '') + (cls ? '.' + cls : '') + anc; };
  const txt = el => (el.textContent || '').replace(/\s+/g, ' ').trim();
  const alts = el => [...el.querySelectorAll('img[alt]')].map(i => i.alt).join('').trim();
  document.querySelectorAll('img:not([alt]), input[type=image]:not([alt])').forEach(el => out.push('an image with no alt: ' + who(el)));
  document.querySelectorAll('svg').forEach(el => {
    if (el.getAttribute('aria-hidden') === 'true' || ['presentation', 'none'].includes(el.getAttribute('role'))) return;
    const t = el.querySelector(':scope > title');
    if ((el.getAttribute('aria-label') || '').trim() || (el.getAttribute('aria-labelledby') || '').trim() || (t && t.textContent.trim())) return;
    out.push('an icon neither hidden nor named: ' + who(el.parentElement)); });
  document.querySelectorAll('input:not([type=hidden]):not([type=submit]):not([type=button]):not([type=reset]):not([type=image]), select, textarea').forEach(el => {
    const lb = el.getAttribute('aria-labelledby');
    if ((el.id && document.querySelector('label[for="' + CSS.escape(el.id) + '"]')) || el.closest('label')
        || (el.getAttribute('aria-label') || '').trim() || (lb && lb.split(/\s+/).every(i => document.getElementById(i)))
        || (el.getAttribute('title') || '').trim()) return;
    out.push('a field with no label: ' + who(el)); });
  document.querySelectorAll('label').forEach(el => { if (!txt(el) && !alts(el)) out.push('an empty label: ' + who(el)); });
  document.querySelectorAll('h1,h2,h3,h4,h5,h6').forEach(el => { if (!txt(el) && !alts(el)) out.push('an empty heading: ' + who(el)); });
  document.querySelectorAll('[aria-labelledby],[aria-describedby]').forEach(el => {
    for (const a of ['aria-labelledby', 'aria-describedby']) {
      const miss = (el.getAttribute(a) || '').split(/\s+/).filter(i => i && !document.getElementById(i));
      if (miss.length) out.push(a + ' points at nothing (#' + miss.join(', #') + '): ' + who(el)); } });
  return out; }"""
import urllib.request as _ur
_wbody = {"title": "Wave fixture", "version": 2, "schemaVersion": 2, "visibility": "public",
          "playbackMode": "replay", "canvasSize": {"cssWidth": 816, "cssHeight": 612},
          "frames": [{"strokes": [{"x": 120 + i * 40, "y": 140 + (i % 3) * 30, "color": "#7c5cff",
                                   "size": 12, "t": i * 120} for i in range(12)], "strokeGroups": [12]}]}
with _ur.urlopen(_ur.Request(BASE + "/api/skribls", data=json.dumps(_wbody).encode(),
                             headers={"Content-Type": "application/json"}), timeout=20) as _r:
    _wj = json.loads(_r.read().decode())
# What lib/posted.js writes when a sheet's post succeeds, so the Library has a row.
_wrow = [{"id": _wj["id"], "url": _wj["url"], "title": "Wave fixture", "kind": "pad", "pages": 1,
          "visibility": "public", "tok": _wj["deleteToken"], "local": False, "has_audio": True, "at": 0}]
with sync_playwright() as _pw:
    _bw = _pw.chromium.launch()
    for _size, _opts in (("phone", dict(viewport={"width": 402, "height": 874}, device_scale_factor=2,
                                         is_mobile=True, has_touch=True)),
                         ("desk", dict(viewport={"width": 1280, "height": 900}))):
        _ctx = _bw.new_context(**_opts)
        for _name, _path in (("the Pad", "/"), ("Flip", "/flip"), ("the Gallery", "/gallery"),
                             ("the Library", "/library"), ("the feed", "/feed"),
                             ("a share link", "/s/" + _wj["id"])):
            _pg = _ctx.new_page()
            browsing.goto(_pg, BASE, _path, require_boot=False)
            if _name == "the Library":
                _pg.evaluate("(e) => localStorage.setItem('skribl_posted_v1', JSON.stringify(e))", _wrow)
                _pg.reload(wait_until="load")
            if _name == "Flip":
                _pg.wait_for_timeout(600)
                _pg.evaluate("() => { addFrame(false); addFrame(false); }")
            _pg.wait_for_timeout(1500)
            _f = _pg.evaluate(_WAVE_ERRORS)
            # Filled means filled: a reading of an empty list would pass for one.
            _n = _pg.evaluate("""() => ({ rows: document.querySelectorAll('#postedList .posted-row').length,
                cards: document.querySelectorAll('#galleryList > *').length,
                pages: typeof frames !== 'undefined' ? frames.length : 0 })""")
            _filled = {"the Library": _n["rows"] >= 1, "the Gallery": _n["cards"] >= 1,
                       "Flip": _n["pages"] == 3}.get(_name, True)
            check(f"{_size}, {_name}: none of WAVE's error rules fires",
                  not _f and _filled, ("; ".join(_f[:4]) + (f" (+{len(_f) - 4} more)" if len(_f) > 4 else ""))
                  if _f else ("" if _filled else f"read empty, so it proves nothing: {_n}"))
            _pg.close()
        _ctx.close()
    _bw.close()

print("\nA11Y 20 — no words at 10px or under (WAVE's very small text), and the ones that were are 12px (13 in a drawer)")
# THE 10px WORDS, AT 12px (the owner's pick from the v326 mocks). WAVE calls
# text at 10px or under very small, and these drew it: Flip's tool tray's
# labels, the draw drawer's Recent, the shape card's knobs, How it works' tip
# counts and the music trim's time bubbles. Each page is read at rest and in
# the state that shows each of them, on a phone and on a desk: every text node
# laid out, not see-through, at its computed size, at WAVE's own line (10px or
# under; the 11px words are another question, not asked here). Each rule that
# drew them is then read at the 12px the owner picked; three of them are a dock
# drawer's words (the draw drawer's Recent, the shape card's knobs, the music
# trim's bubbles), a size up again since the drawers' type, B ("all yes"): 13.
#
# AND FLIP'S PAGE STRIP, LAST. At 12px as it sat its words ran into each
# other on a phone's 104px tile (the forever chip under the page's ⋯ and its
# touch box, page 10 and on into the hold badge, the ×1 a pixel off centre in
# two faces), which the first mock, measuring each word alone, did not show.
# The owner picked how it fits from a mock of the strip itself (A: one ⋯ per
# page, in the ✕'s corner); verify_loopui reads its tiles crowded, and its
# words are read here with the rest. (The duration badge is 10px only on a
# phone, where it is hidden.)
_SMALL = r"""() => { const out = new Set();
  const who = el => { let anc = ''; for (let n = el.parentElement; n; n = n.parentElement) if (n.id) { anc = ' in #' + n.id; break; }
    const cls = (el.getAttribute('class') || '').trim().split(/\s+/).filter(Boolean)[0];
    return el.tagName.toLowerCase() + (el.id ? '#' + el.id : '') + (cls ? '.' + cls : '') + anc; };
  const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  for (let t = w.nextNode(); t; t = w.nextNode()) {
    const s = t.textContent.trim(), el = t.parentElement;
    if (!s || !el || el.closest('script, style, title, noscript')) continue;
    const r = el.getBoundingClientRect();
    if (r.width <= 1 || r.height <= 1) continue;
    let o = 1;
    for (let a = el; a; a = a.parentElement) o *= parseFloat(getComputedStyle(a).opacity);
    if (o < 0.05 || getComputedStyle(el).visibility === 'hidden') continue;
    const px = parseFloat(getComputedStyle(el).fontSize);
    if (px <= 10) out.add(who(el) + ' at ' + px + 'px ("' + s.slice(0, 16) + '")'); }
  return [...out]; }"""
# What each rule that drew 10px words computes to, on the first one laid out.
_AT = """(sels) => sels.map(s => { const e = [...document.querySelectorAll(s)].find(e => e.getClientRects().length);
  return [s, e ? parseFloat(getComputedStyle(e).fontSize) : null]; })"""
_WAS10 = {"the draw drawer, with Recent": [".recent-label"], "the shape card, Sides": [".shape-knob label"],
          "How it works, its tip counts": [".accordion-count"], "the music trim, both handles held": [".trim-bubble"],
          "Flip's tool tray": [".tool-tray-btn"], "Flip's page strip": ["#strip .frame .num", "#strip .frame .holdbadge"]}


def _boot20(pg, path, key):
    pg.goto(BASE + path, wait_until="load")
    pg.wait_for_function("(k) => window.__skriblBoot && window.__skriblBoot[k]", arg=key, timeout=10000)
    pg.evaluate("() => { if (window.SkriblHints) window.SkriblHints.hide(); }")
    pg.wait_for_timeout(300)


with sync_playwright() as _pw:
    _b20 = _pw.chromium.launch()
    for _size, _opts in (("phone", dict(viewport={"width": 402, "height": 874}, device_scale_factor=2,
                                         is_mobile=True, has_touch=True)),
                         ("desk", dict(viewport={"width": 1280, "height": 900}))):
        _ctx = _b20.new_context(**_opts)
        _pg = _ctx.new_page()
        _read = {}
        # The Pad at rest, then its drawers.
        _boot20(_pg, "/", "pad")
        _read["the Pad"] = _pg.evaluate(_SMALL)
        browsing.pad_drawer(_pg, "draw")
        _pg.evaluate("() => { const r = document.getElementById('recentRow'); if (r) r.hidden = false; }")
        _pg.wait_for_timeout(200)
        _read["the draw drawer, with Recent"] = _pg.evaluate(_SMALL)
        _at = _pg.evaluate(_AT, _WAS10["the draw drawer, with Recent"])
        _boot20(_pg, "/", "pad")
        _pg.click('[data-tool="shape"]'); _pg.wait_for_timeout(300)
        if _pg.evaluate("() => document.getElementById('shapePop').hidden"):
            _pg.click('[data-tool="shape"]'); _pg.wait_for_timeout(300)
        _pg.evaluate("() => { const b = document.querySelector('#shapeSeg [data-shape=poly]'); if (b) b.click(); }")
        _pg.wait_for_timeout(300)
        _read["the shape card, Sides"] = _pg.evaluate(_SMALL)
        _at += _pg.evaluate(_AT, _WAS10["the shape card, Sides"])
        _boot20(_pg, "/", "pad")
        _pg.evaluate("() => openHelpDrawer()"); _pg.wait_for_timeout(600)
        _pg.evaluate("() => { document.getElementById('helpWatch').hidden = true; document.getElementById('helpLook').hidden = false; }")
        _pg.wait_for_timeout(500)
        _read["How it works, its tip counts"] = _pg.evaluate(_SMALL)
        _at += _pg.evaluate(_AT, _WAS10["How it works, its tip counts"])
        _boot20(_pg, "/", "pad")
        _pg.click("#mediaOpenBtn"); _pg.wait_for_timeout(300)
        _pg.evaluate("() => { const t = document.getElementById('mediaTabMusic'); if (t) t.click(); }")
        _pg.wait_for_timeout(300)
        _pg.set_input_files("#musicInput", {"name": "t.wav", "mimeType": "audio/wav", "buffer": _wav1()})
        _pg.wait_for_function("() => document.getElementById('musicUploadBtn').classList.contains('loaded')", timeout=15000)
        _pg.evaluate("() => document.querySelectorAll('.mt-tl-handle').forEach(h => h.classList.add('dragging'))")
        _pg.wait_for_timeout(300)
        _read["the music trim, both handles held"] = _pg.evaluate(_SMALL)
        _at += _pg.evaluate(_AT, _WAS10["the music trim, both handles held"])
        # The timeline's ends as far out as a finger can take them (the start
        # at its left edge, the end at its right, as an end held in the edge
        # zone is), read before the timeline's next frame puts them back.
        _held = _pg.evaluate("""() => { const st = document.getElementById('musicTlStage'), t = st.getBoundingClientRect();
            document.getElementById('tlStart').style.transform = 'translateX(0px)';
            document.getElementById('tlEnd').style.transform = 'translateX(' + t.width + 'px)';
            return [...st.querySelectorAll('.trim-bubble')].map(b => { const r = b.getBoundingClientRect();
              return [Math.round(r.left - t.left), Math.round(t.right - r.right)]; }); }""")
        # Flip with a few pages, at rest and with its tool tray open.
        _boot20(_pg, "/flip", "flip")
        _pg.evaluate("() => { addFrame(false); addFrame(false); buildStrip(); }")
        _pg.wait_for_timeout(400)
        _read["Flip"] = _pg.evaluate(_SMALL)
        _at += _pg.evaluate(_AT, _WAS10["Flip's page strip"])
        if _pg.evaluate("() => { const m = document.getElementById('toolMoreBtn'); return !!m && !m.hidden; }"):
            _pg.click("#toolMoreBtn"); _pg.wait_for_timeout(500)
        _read["Flip's tool tray"] = _pg.evaluate(_SMALL) if _pg.evaluate(
            "() => { const t = document.getElementById('toolTray'); return !!t && !t.hidden; }") else ["(the tray did not open)"]
        _at += _pg.evaluate(_AT, _WAS10["Flip's tool tray"])
        # The pages with no editor in them, filled.
        for _name, _path in (("the Gallery", "/gallery"), ("a share link", "/s/" + _wj["id"])):
            browsing.goto(_pg, BASE, _path, require_boot=False)
            _pg.wait_for_timeout(1200)
            _read[_name] = _pg.evaluate(_SMALL)
        browsing.goto(_pg, BASE, "/library", require_boot=False)
        _pg.evaluate("(e) => localStorage.setItem('skribl_posted_v1', JSON.stringify(e))", _wrow)
        _pg.reload(wait_until="load"); _pg.wait_for_timeout(1200)
        _read["the Library"] = _pg.evaluate(_SMALL)
        for _where, _small in _read.items():
            check(f"{_size}, {_where}: no words at 10px or under", not _small,
                  "; ".join(_small[:4]) + (f" (+{len(_small) - 4} more)" if len(_small) > 4 else ""))
        _B13 = {".recent-label", ".shape-knob label", ".trim-bubble"}
        _off = [f"{sel} {px}px" for sel, px in _at if px != (13 if sel in _B13 else 12)]
        check(f"{_size}: every rule that drew 10px words is at 12px, or 13 in a dock drawer, each read where it shows",
              len(_at) == sum(len(v) for v in _WAS10.values()) and not _off, "; ".join(_off) or f"{len(_at)} read")
        check(f"{_size}, the timeline's time bubbles stay over it, both ends held at its edges",
              len(_held) == 2 and all(a >= 0 and b >= 0 for a, b in _held), str(_held))
        _ctx.close()
    _b20.close()

passed = sum(1 for ok, _ in results if ok)
bad = [n for ok, n in results if not ok]
print("\n" + "=" * 62)
print(f"{passed}/{len(results)} passed"
      + ("" if not bad else "\nFAILURES:\n  - " + "\n  - ".join(bad)))
sys.exit(1 if bad else 0)
