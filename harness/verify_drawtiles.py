#!/usr/bin/env python3
"""The draw drawer's four tiles (lib/drawtiles.js), on the Pad and on Flip.

The owner picked this from four mocked shapes ("In place", Joined: "go ahead,
build it. Keep it kind"): under the colour, four tiles -- Brush, Size, Feel,
Eraser -- each a little picture of what it holds now in the pen's colour; a tap
opens its choices in place, joined to the tile as one shape; the same tile
closes them. No chevron and no back button. The ⋯ menu's colours, role for
role ("flow between menus. Same color scheme").

The rows:

  EVERY TOOL. Each control the drawer had is in a tile, hidden until its tile
  opens and then painted where a finger lands (elementFromPoint, not a rect):
  the four brushes, the size slider and four quick sizes, opacity, the three
  smoothings, the two pressures, the three eraser widths, and Flip's Draw-on.

  THE CHOICES DO WHAT THEY SAY. Each one changes the editor's own state (the
  brush, the size and its readout, opacity, smoothing, pressure, the eraser,
  Draw-on) and the tile's words follow.

  ONE SHAPE. The open tile reaches over the gap into its card, and what is
  painted on the seam is the tile; its bottom edge is the card's colour. No
  line shows there, read on the screenshot's pixels in light and dark (the
  card's dark top light, a 1px inset, once showed under the open tile), and
  at an end the card's edge runs unbroken. The tiles and the card are the
  menu's card, an unchosen choice the menu's paper, the chosen one the one
  tint.

  NOTHING PAINTS OUTSIDE THE DRAWER. Built first, Pad still handed these four
  groups to the pill slider, whose pill, with no track, hung from a far
  ancestor and painted a column of tint down the whole page under the chosen
  choice. Asked of every element in the drawer: none reaches past it.

  THE PEN'S COLOUR. The pictures are painted in it, and follow it.

  KIND, NOT JUMPY. Closing folds the choices away over frames before they go
  (read on every frame); under Reduce Motion they go at once. A drawer shut
  and opened again starts with four tiles.

  THE PHONE. The drawer opens at half: Color and the tiles, Clear out of the
  way. Opening a tile goes to full, the choices on screen and Clear with them.

  THE KEYS. A group of choices is one Tab stop, and the arrows move the choice.

Checked red per component: see DECISIONS.md for which mutation turned which
row red.
"""
import os
import sys
from assertions import make_check

BASE = os.environ.get("SKRIBL_BASE", "http://127.0.0.1:5001")
results = []
check = make_check(results, detail_on_pass=False)


def summarise_and_exit():
    bad = [r for r in results if not r[0]]
    print(f"\n{'=' * 62}\n{len(results) - len(bad)}/{len(results)} passed"
          + ("" if not bad else "  FAILURES: " + ", ".join(r[1] for r in bad)))
    sys.exit(1 if bad else 0)


try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("SKIP: playwright is not installed")
    sys.exit(0)
import browsing  # noqa: E402
import waits  # noqa: E402

PHONE = dict(viewport={"width": 402, "height": 874}, device_scale_factor=2, is_mobile=True, has_touch=True)
DESK = dict(viewport={"width": 1280, "height": 860}, device_scale_factor=1)
PINK = "#ff48b0"
# For calibration: DRAWTILES_ONLY=Pad (or Flip) and DRAWTILES_QUICK=1 (one theme
# per device) run the part that matters in about a minute. A real run sets neither.
ONLY = os.environ.get("DRAWTILES_ONLY", "")
QUICK = os.environ.get("DRAWTILES_QUICK") == "1"

ED = {
    "/skribl-pad": {"name": "Pad", "drawer": "() => openDrawer('draw')", "close": "() => openDrawer(null)",
                    "pen": "(h) => setPenColor(h)", "size": "#brushSizeRange", "sizeVal": "#brushSizeVal",
                    "opacity": "() => strokeOpacity", "smooth": "() => smoothingAlpha", "clear": "#clearDrawerBtn"},
    "/flip": {"name": "Flip", "drawer": "() => _flipDrawerCtl.open('draw')", "close": "() => closePop()",
              "pen": "(h) => setColor(h)", "size": "#size", "sizeVal": "#sizeVal",
              "opacity": "() => strokeOpacity", "smooth": "() => smoothingAlpha", "clear": "#clear"},
}

TOOLS = {
    "brush": ["[data-brush=pen]", "[data-brush=marker]", "[data-brush=pencil]", "[data-brush=airbrush]"],
    "size": ["SIZE", "[data-size='2']", "[data-size='5']", "[data-size='12']", "[data-size='24']", "#opacitySlider"],
    "feel": ["[data-smooth=off]", "[data-smooth=low]", "[data-smooth=high]", "[data-pressure=off]", "[data-pressure=on]"],
    "eraser": ["[data-eraser='2']", "[data-eraser='3']", "[data-eraser='5']"],
}

PAINTED = """(sel) => { const el = document.querySelector(sel); if (!el) return 'missing';
  el.scrollIntoView({ block: 'center' });
  const r = el.getBoundingClientRect(); if (!r.width || !r.height) return 'no box';
  const at = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
  return !!(at && (el === at || el.contains(at))); }"""

STATE = """() => { const t = {}; document.querySelectorAll('.dp-tile').forEach(b => {
  t[b.dataset.dp] = { open: b.getAttribute('aria-expanded'), v: b.querySelector('.dp-v').textContent }; });
  const shown = [...document.querySelectorAll('.dp-panel')].filter(p => !p.hidden).map(p => p.dataset.dp);
  return { tiles: t, shown }; }"""

# Resolve a token as the drawer paints it.
TOKEN = """(name) => { const d = document.createElement('div'); d.style.background = 'var(' + name + ')';
  document.getElementById('drawPanel').appendChild(d); const v = getComputedStyle(d).backgroundColor; d.remove(); return v; }"""

# Pixels on a picture near a colour, and pixels of anything opaque.
INKED = """([sel, hex]) => { const c = document.querySelector(sel); if (!c || !c.width) return null;
  const x = c.getContext('2d').getImageData(0, 0, c.width, c.height).data;
  const r = parseInt(hex.slice(1, 3), 16), g = parseInt(hex.slice(3, 5), 16), b = parseInt(hex.slice(5, 7), 16);
  let near = 0, any = 0;
  for (let i = 0; i < x.length; i += 4) { if (x[i + 3] < 128) continue; any++;
    if (Math.abs(x[i] - r) + Math.abs(x[i + 1] - g) + Math.abs(x[i + 2] - b) < 60) near++; }
  return { near, any }; }"""

# Every element in the drawer that reaches past the drawer's own box.
OUTSIDE = """() => { const p = document.getElementById('drawPanel'), R = p.getBoundingClientRect(), out = [];
  for (const el of p.querySelectorAll('*')) { if (!el.getClientRects().length) continue;
    const r = el.getBoundingClientRect(); if (!r.width || !r.height) continue;
    if (r.left < R.left - 2 || r.right > R.right + 2 || r.top < R.top - 2 || r.bottom > R.bottom + 2) {
      // a control's own tap band (::before) is not a box; scrolled content inside a fitted drawer is clipped
      if (getComputedStyle(p).overflowY !== 'visible' && r.left >= R.left - 2 && r.right <= R.right + 2) continue;
      out.push((el.id || el.className || el.tagName) + ' ' + Math.round(r.top) + '..' + Math.round(r.bottom)); } }
  return out; }"""


def fresh(b, route, opts, scheme="dark", reduce=False):
    c = b.new_context(color_scheme=scheme, reduced_motion="reduce" if reduce else "no-preference", **opts)
    q = c.new_page()
    errs = []
    q.on("pageerror", lambda e: errs.append(str(e)))
    browsing.goto(q, BASE, route)
    q.evaluate("() => { window.SkriblHints && SkriblHints.hide && SkriblHints.hide(); }")
    return c, q, errs


def open_drawer(q, route):
    q.evaluate(ED[route]["drawer"]); waits.settle(q, 600)


def tile(q, k, ms=500):
    q.evaluate("(k) => document.querySelector(`.dp-tile[data-dp=${k}]`).click()", k)
    q.wait_for_timeout(ms)


# THE SEAM, AS PAINTED. In dark the card's drop lights its top edge from
# inside (--menu-card-drop's 1px inset), one row under its border, and the open
# tile covered only the border: that row showed under the tile as a faint line,
# 8 levels over the card. Read on a screenshot, not on styles: the largest step
# from the card's colour over the rows from the tile's bottom border to 3px into
# the card, across the tile's inside; and, where the tile is at an end, the
# smallest step on the card's side edge at the joint (0 is a break in the edge,
# which a cover the tile's whole width paints).
JOINT = """([t, p]) => { t = document.querySelector(t); p = document.querySelector(p);
  let a = t.getBoundingClientRect();
  if (a.bottom < 8 || a.bottom > innerHeight - 8) { t.scrollIntoView({ block: 'center', behavior: 'instant' }); a = t.getBoundingClientRect(); }
  const z = p.getBoundingClientRect();
  return { a: [a.left, a.top, a.right, a.bottom], z: [z.left, z.top, z.right, z.bottom], card: getComputedStyle(p).backgroundColor }; }"""


def seam(q, tsel, psel, dpr):
    import io
    import re
    from PIL import Image
    j = q.evaluate(JOINT, [tsel, psel])
    a, z = j["a"], j["z"]
    card = [int(v) for v in re.findall(r"\d+", j["card"])[:3]]
    x0, y0 = min(a[0], z[0]) - 2, a[3] - 6
    im = Image.open(io.BytesIO(q.screenshot(clip={"x": x0, "y": y0, "width": max(a[2], z[2]) + 2 - x0, "height": 14}))).convert("RGB")
    w, h = im.size

    def step(x, y):
        c = im.getpixel((min(w - 1, max(0, int((x - x0) * dpr))), min(h - 1, max(0, int((y - y0) * dpr)))))
        return max(abs(c[i] - card[i]) for i in range(3))
    inside = [a[0] + 2 + i / dpr for i in range(int((a[2] - a[0] - 4) * dpr))]
    worst = max(step(x, a[3] - 1 + i / dpr) for i in range(int(4 * dpr)) for x in inside)
    edges = {side: min(step(col, a[3] - 4 + i / dpr) for i in range(int(8 * dpr)))
             for side, xa, xz, col in (("left", a[0], z[0], a[0] + .5 / dpr), ("right", a[2], z[2], a[2] - .5 / dpr))
             if abs(xa - xz) < .75}
    return worst, edges


with sync_playwright() as pw:
    b = waits.instrument(pw.chromium.launch())

    for route, e in ED.items():
        nm = e["name"]
        if ONLY and nm != ONLY:
            continue
        sizesel = e["size"]
        tools = dict(TOOLS)
        tools["size"] = [sizesel if s == "SIZE" else s for s in TOOLS["size"]]
        if nm == "Flip":
            tools["feel"] = TOOLS["feel"] + ["#drawOnBtn"]

        for dev, opts in (("desk", DESK), ("phone", PHONE)):
            for scheme in (("dark",) if QUICK else ("light", "dark")):
                who = f"{nm}, {dev}, {scheme}"
                print(f"\n{who.upper()}")
                c, q, errs = fresh(b, route, opts, scheme)
                open_drawer(q, route)
                st = q.evaluate(STATE)
                check(f"{who}: the drawer opens on four tiles, none open",
                      sorted(st["tiles"]) == ["brush", "eraser", "feel", "size"]
                      and all(t["open"] == "false" for t in st["tiles"].values()) and not st["shown"], str(st))

                # ---------------------------------------------------- every tool
                for k, sels in tools.items():
                    hidden = [s for s in sels if q.evaluate(PAINTED, s) is True]
                    check(f"{who}: {k}'s choices are out of the way until {k} is tapped", not hidden, str(hidden))
                    tile(q, k, 700)
                    st = q.evaluate(STATE)
                    check(f"{who}: tapping {k} opens its choices, and only its", st["shown"] == [k]
                          and st["tiles"][k]["open"] == "true", str(st))
                    gone = [s for s in sels if q.evaluate(PAINTED, s) is not True]
                    check(f"{who}: every one of {k}'s choices is painted where a finger lands ({len(sels)})", not gone, str(gone))

                    # ONE SHAPE, measured on the tile that is open.
                    j = q.evaluate("""(k) => { const t = document.querySelector(`.dp-tile[data-dp=${k}]`),
                        p = document.querySelector(`.dp-panel[data-dp=${k}]`), a = t.getBoundingClientRect(), z = p.getBoundingClientRect();
                        const at = document.elementFromPoint(a.left + a.width / 2, z.top + 0.5);
                        return { over: a.bottom - z.top, seam: !!(at && t.contains(at)),
                                 edge: getComputedStyle(t).borderBottomColor, card: getComputedStyle(p).backgroundColor,
                                 tile: getComputedStyle(t).backgroundColor }; }""", k)
                    check(f"{who}: {k}'s tile and its choices are one shape: the tile runs into the card, "
                          "the seam painted by the tile in the card's colour",
                          j["over"] >= 0.5 and j["seam"] and j["edge"] == j["card"] and j["tile"] == j["card"], str(j))
                    worst, edges = seam(q, f".dp-tile[data-dp={k}]", f".dp-panel[data-dp={k}]", opts.get("device_scale_factor", 1))
                    check(f"{who}: no line shows where {k}'s tile meets its card (painted pixels: the rows at the "
                          "joint are the card's colour), and at an end the card's edge runs unbroken",
                          worst <= 2 and all(v >= 4 for v in edges.values()) and (k not in ("brush", "eraser") or len(edges) == 1),
                          f"largest step from the card at the joint {worst} (2 at most); the edge's smallest {edges} (4 at least)")
                    out = q.evaluate(OUTSIDE)
                    check(f"{who}: with {k} open, nothing in the drawer paints outside it", not out, "; ".join(out[:4]))

                # ---------------------------------------------------- the menu's colours
                card, paper, tint = (q.evaluate(TOKEN, t) for t in ("--menu-card", "--menu-paper", "--seg-on-fill"))
                tile(q, "brush", 700)
                cols = q.evaluate("""() => { const s = el => getComputedStyle(el).backgroundColor;
                    return { tiles: [...document.querySelectorAll('.dp-tile')].map(s),
                             panel: s(document.getElementById('dpBrush')),
                             chosen: s(document.querySelector('#brushSeg .active')),
                             other: s(document.querySelector('#brushSeg [data-brush=marker]')),
                             drawer: s(document.getElementById('drawPanel')) }; }""")
                check(f"{who}: tiles and card are the menu's card, a choice the menu's paper, the chosen one the one tint, "
                      "on the menu's paper",
                      set(cols["tiles"]) == {card} and cols["panel"] == card and cols["other"] == paper
                      and cols["chosen"] == tint and cols["drawer"] == paper,
                      f"{cols} vs card {card} paper {paper} tint {tint}")

                # ---------------------------------------------------- closing
                tile(q, "brush", 0)
                st = q.evaluate(STATE)
                check(f"{who}: the same tile closes it (said at once)", st["tiles"]["brush"]["open"] == "false", str(st))
                q.wait_for_timeout(500)
                st = q.evaluate(STATE)
                check(f"{who}: ...and the choices are gone, four tiles again", not st["shown"], str(st))
                tile(q, "feel", 400); tile(q, "eraser", 600)
                st = q.evaluate(STATE)
                check(f"{who}: one tile for another: only the new one is open", st["shown"] == ["eraser"]
                      and st["tiles"]["feel"]["open"] == "false", str(st))
                q.evaluate(e["close"]); q.wait_for_timeout(500)
                open_drawer(q, route)
                st = q.evaluate(STATE)
                check(f"{who}: shut and opened again, the drawer starts on four tiles", not st["shown"]
                      and all(t["open"] == "false" for t in st["tiles"].values()), str(st))
                check(f"{who}: no page errors", not errs, "; ".join(errs[:2]))
                c.close()

        # ======================================================== the choices work
        print(f"\n{nm.upper()}: THE CHOICES DO WHAT THEY SAY")
        c, q, errs = fresh(b, route, DESK)
        open_drawer(q, route)
        tile(q, "brush"); q.click("#brushSeg [data-brush=marker]"); q.wait_for_timeout(200)
        st = q.evaluate(STATE)
        check(f"{nm}: Marker is the brush, and the tile says so",
              q.evaluate("() => SkriblBrush.name()") == "marker" and st["tiles"]["brush"]["v"] == "Marker", str(st))
        tile(q, "size"); q.click("[data-size='12']"); q.wait_for_timeout(200)
        st = q.evaluate(STATE)
        sv = q.evaluate(f"() => [document.querySelector('{sizesel}').value, document.querySelector('{e['sizeVal']}').textContent]")
        check(f"{nm}: Bold sets the size to 12, the editor's own readout follows, and so does the tile",
              sv == ["12", "12px"] and st["tiles"]["size"]["v"].startswith("12px")
              and q.evaluate("() => document.querySelector('[data-size=\"12\"]').getAttribute('aria-pressed')") == "true",
              f"{sv} {st['tiles']['size']}")
        q.evaluate("() => { const s = document.getElementById('opacitySlider'); s.value = 60; s.dispatchEvent(new Event('input', { bubbles: true })); }")
        q.wait_for_timeout(200)
        st = q.evaluate(STATE)
        check(f"{nm}: opacity 60% is the stroke's, and the Size tile says so",
              abs(q.evaluate(e["opacity"]) - 0.6) < 1e-6 and st["tiles"]["size"]["v"] == "12px · 60%", str(st["tiles"]["size"]))
        tile(q, "feel"); q.click("[data-smooth=high]"); q.click("[data-pressure=off]"); q.wait_for_timeout(200)
        st = q.evaluate(STATE)
        check(f"{nm}: High smoothing and pressure Off are the editor's, and the Feel tile says Smooth high",
              q.evaluate(e["smooth"]) == q.evaluate("() => SkriblSmoothing.alphaFor('high')")
              and q.evaluate("() => SkriblPressure.enabled()") is False and st["tiles"]["feel"]["v"] == "Smooth high", str(st["tiles"]["feel"]))
        if nm == "Flip":
            q.click("#drawOnBtn"); q.wait_for_timeout(200)
            check("Flip: Draw-on switches on from Feel", q.evaluate("() => document.getElementById('drawOnBtn').getAttribute('aria-checked')") == "true")
        tile(q, "eraser"); q.click("[data-eraser='5']"); q.wait_for_timeout(200)
        st = q.evaluate(STATE)
        check(f"{nm}: the eraser is 5x the pen, and the tile says so",
              q.evaluate("() => SkriblEraser.eraserMult()") == 5 and st["tiles"]["eraser"]["v"] == "5× pen", str(st["tiles"]["eraser"]))

        # ---------------------------------------------------- the keys
        tile(q, "brush")
        stops = q.evaluate("() => [...document.querySelectorAll('#brushSeg button')].filter(b => b.tabIndex === 0).map(b => b.dataset.brush)")
        q.focus("#brushSeg [data-brush=marker]"); q.keyboard.press("ArrowRight"); q.wait_for_timeout(150)
        check(f"{nm}: the brushes are one Tab stop (the chosen one), and an arrow moves the choice",
              stops == ["marker"] and q.evaluate("() => SkriblBrush.name()") == "pencil", f"stops {stops}")

        # ---------------------------------------------------- the pen's colour
        before = q.evaluate(INKED, [".dp-tile[data-dp=brush] canvas", PINK])
        q.evaluate(e["pen"], PINK); q.wait_for_timeout(400)
        after = q.evaluate(INKED, [".dp-tile[data-dp=brush] canvas", PINK])
        choice = q.evaluate(INKED, ["#brushSeg [data-brush=marker] canvas", PINK])
        check(f"{nm}: the pictures are painted in the pen's colour and follow it (pink pixels before, after, on a choice)",
              before and after and choice and before["near"] == 0 and after["near"] > 40 and choice["near"] > 40,
              f"{before} {after} {choice}")
        check(f"{nm}: no page errors", not errs, "; ".join(errs[:2]))
        c.close()

        # ======================================================== kind transitions
        print(f"\n{nm.upper()}: KIND, NOT JUMPY")
        c, q, errs = fresh(b, route, DESK)
        open_drawer(q, route)
        tile(q, "feel", 600)
        seen = q.evaluate("""() => new Promise(done => { const p = document.getElementById('dpFeel'), out = [];
            document.querySelector('.dp-tile[data-dp=feel]').click();
            const t0 = performance.now();
            (function f() { out.push(p.hidden ? -1 : +getComputedStyle(p).opacity);
              if (performance.now() - t0 < 450) requestAnimationFrame(f); else done(out); })(); })""")
        shown = [o for o in seen if o >= 0]
        mid = [o for o in shown if 0.05 < o < 0.95]
        check(f"{nm}: closing folds the choices away over frames, never brighter, then they go",
              len(mid) >= 2 and all(a >= b - 1e-3 for a, b in zip(shown, shown[1:])) and seen[-1] == -1,
              f"{len(seen)} frames, {len(mid)} between, {[round(o, 2) for o in seen[:14]]}")
        c.close()
        c, q, errs = fresh(b, route, DESK, reduce=True)
        open_drawer(q, route)
        q.evaluate("() => document.querySelector('.dp-tile[data-dp=feel]').click()")
        anim = q.evaluate("() => document.getElementById('dpFeel').getAnimations().length")
        q.wait_for_timeout(300)
        tile(q, "feel", 0)
        gone = q.evaluate("() => new Promise(r => requestAnimationFrame(() => r(document.getElementById('dpFeel').hidden)))")
        check(f"{nm}: under Reduce Motion the choices neither unfold nor fold: they are there, then not",
              anim == 0 and gone is True, f"{anim} animations as it opened, hidden next frame {gone}")
        c.close()

        # ======================================================== the phone's detent
        print(f"\n{nm.upper()}: THE PHONE")
        c, q, errs = fresh(b, route, PHONE)
        open_drawer(q, route); q.wait_for_timeout(600)
        half = q.evaluate(f"""() => ({{ full: document.getElementById('drawPanel').classList.contains('detent-full'),
            tiles: !!document.querySelector('.dp-tile').offsetParent, clear: !!document.querySelector('{e["clear"]}').offsetParent }})""")
        check(f"{nm}: on a phone the drawer opens at half: Color and the tiles, Clear out of the way",
              half == {"full": False, "tiles": True, "clear": False}, str(half))
        tile(q, "size", 1600)
        full = q.evaluate(f"""() => {{ const p = document.getElementById('dpSize').getBoundingClientRect();
            const vh = window.visualViewport ? visualViewport.height : innerHeight;
            return {{ full: document.getElementById('drawPanel').classList.contains('detent-full'),
                     onScreen: p.top >= 0 && p.bottom <= vh + 1, clear: !!document.querySelector('{e["clear"]}').offsetParent }}; }}""")
        check(f"{nm}: opening a tile takes the drawer to full, its choices on screen and Clear with them",
              full == {"full": True, "onScreen": True, "clear": True}, str(full))
        check(f"{nm}: no page errors", not errs, "; ".join(errs[:2]))
        c.close()

    b.close()

summarise_and_exit()
