#!/usr/bin/env python3
"""Blooby says hi: the first time Skribl opens, on any screen (lib/hello.js, FUTURE.md 6m).

The owner's picks, each a row below. His star draws itself and its light comes
on, he walks up from far away onto it, waves once and the picture opens onto
the canvas, in the Home Screen icon's own light, sharp on the screen's pixel
grid; the star's points are points. Once only; a tap, a click or a key skips
him (and does nothing else); a still hello under Reduce Motion; the same on
Flip with one "seen" for both; on a desk as on a phone; never in a composer's
frame; nothing fetched when he does not come.

Automation never meets him unless it asks (window.__skriblHelloForce): every
other suite opens a fresh browser and would otherwise find him over its first
canvas. So this suite asks, and one row proves that without asking he stays
away.

Visible means PAINTED: elementFromPoint at the screen's middle lands inside
him. Gone means removed, and the canvas painted there again.

A slow line is a row too: when his player is not here within hello.js's LATE
he does not come that time and is not marked seen, so the next open shows him.
The v327 seal run met that path by accident, on a server's first page (see the
warm-up below), and read it as a failure; this row meets it on purpose.

The star's points are read off the drawing itself, before any browser: its
star page painted the way the player paints it (a dot at every point, a
round-capped line between neighbours, each point's own size), then measured
square to each point's axis, walking in from the tip.
"""
import json
import math
import os
import sys
import time
from assertions import make_check

BASE = os.environ.get("SKRIBL_BASE", "http://127.0.0.1:5001")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HELLO_JSON = os.path.join(ROOT, "skribl", "static", "brand", "blooby-hello.json")
results = []
check = make_check(results, detail_on_pass=False)


def summarise_and_exit():
    bad = [r for r in results if not r[0]]
    print(f"\n{'=' * 62}\n{len(results) - len(bad)}/{len(results)} passed"
          + ("" if not bad else "  FAILURES: " + ", ".join(r[1] for r in bad)))
    sys.exit(1 if bad else 0)


try:
    from playwright.sync_api import sync_playwright
    from PIL import Image, ImageDraw
except ImportError:
    print("SKIP: playwright or Pillow is not installed")
    sys.exit(0)

# ------------------------------------------------------------------ the star
# The owner's "nubs": a round pen's one closed outline ended every point in a
# ball, and its smoothing pinched a neck behind some. 2 points back from each
# tip the old star was 9.8 to 10.0 points wide, the new 4.9 to 5.9.
K = 8                  # pixels a point
REGROW = 0.6           # points a width may grow again toward the tip (the pen's tremor)
POINT_W = 7.5          # points wide, 2 points back from the tip, at most


def _runs(page):
    out = []
    for p in page["strokes"]:
        if p.get("start") or not out:
            out.append([])
        out[-1].append(p)
    return out


def _white(page, w, h):
    im = Image.new("L", (int(w * K), int(h * K)), 0)
    dr = ImageDraw.Draw(im)
    for s in _runs(page):
        if (s[0].get("color") or "").lower() != "#ffffff":
            continue
        for a, b in zip(s, s[1:]):
            dr.line([(a["x"] * K, a["y"] * K), (b["x"] * K, b["y"] * K)], fill=255,
                    width=max(1, int(round(min(a["size"], b["size"]) * K))))
        for p in s:
            r = p["size"] / 2 * K
            dr.ellipse((p["x"] * K - r, p["y"] * K - r, p["x"] * K + r, p["y"] * K + r), fill=255)
    return im


def _reach(px, size, x, y, ux, uy, d0, step):
    """How far white runs from (x, y) along (ux, uy), stepping over pinholes
    (lilac runs under half a point, invisible at any size he is shown)."""
    d, gap, last = d0, 0.0, d0
    while True:
        u, v = (x + ux * d) * K, (y + uy * d) * K
        if not (0 <= u < size[0] and 0 <= v < size[1]):
            return last
        if px[int(u), int(v)] >= 128:
            gap, last = 0.0, d
        else:
            gap += step
            if gap > 0.5:
                return last
        d += step


def star_points(path):
    """Per point: (how much its width grows again on the way in, its width 2 points back)."""
    d = json.load(open(path))
    page, cs = d["frames"][0], d["canvasSize"]
    im = _white(page, cs["cssWidth"], cs["cssHeight"])
    px = im.load()
    xs = [p["x"] for p in page["strokes"]]
    ys = [p["y"] for p in page["strokes"]]
    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2      # a regular star: the middle of its reach
    out = []
    for k in range(6):
        a = math.radians(-90 + 60 * k)
        ux, uy = math.cos(a), math.sin(a)
        tip = _reach(px, im.size, cx, cy, ux, uy, 10.0, 0.05)
        widths = []
        for i in range(0, 193):                                   # 0 to 48 points back, a quarter at a time
            back = i / 4
            x, y = cx + ux * (tip - back), cy + uy * (tip - back)
            widths.append(_reach(px, im.size, x, y, -uy, ux, 0.0, 1 / K) + _reach(px, im.size, x, y, uy, -ux, 0.0, 1 / K))
        regrow, narrowest = 0.0, float("inf")
        for wdt in reversed(widths):                              # from far back, in to the tip
            narrowest = min(narrowest, wdt)
            regrow = max(regrow, wdt - narrowest)
        out.append((round(regrow, 2), round(widths[8], 2)))
    return out


def star_ms(path):
    """How long the star's page takes to draw itself (lib/holdtiming.js: each
    gap between its points counts up to 250 ms)."""
    pts = json.load(open(path))["frames"][0]["strokes"]
    return sum(min(250, b["t"] - a["t"]) for a, b in zip(pts, pts[1:]) if b["t"] > a["t"])


print("BLOOBY SAYS HI — the first open, on any screen")
tips = star_points(HELLO_JSON)
check("the star's points are points: none pinches and swells again toward its tip, and each is "
      f"under {POINT_W} points wide 2 points back (a pen's end, not a ball)",
      all(r <= REGROW and w <= POINT_W for r, w in tips),
      f"per point (regrowth, width 2 back) in points: {tips}")
STAR_MS = star_ms(HELLO_JSON)

PHONE = dict(viewport={"width": 402, "height": 874}, device_scale_factor=3, is_mobile=True, has_touch=True,
             screen={"width": 402, "height": 874})
DESK = dict(viewport={"width": 1333, "height": 906})
FORCE = "window.__skriblHelloForce = true;"
# `ink`: count the white in his drawing too (a sample of every 97th pixel), a
# read of the whole canvas, so only where a row needs it.
ST = """(ink) => { const h = document.getElementById('skriblHello'), c = h && h.querySelector('canvas');
  const st = h && h.querySelector('.skribl-hello-stage'), g = h && h.querySelector('.skribl-hello-glow');
  const at = document.elementFromPoint(innerWidth / 2, innerHeight / 2), d = devicePixelRatio;
  const r = st && st.getBoundingClientRect(), cr = c && c.getBoundingClientRect();
  const p = h && window.SkriblInline ? SkriblInline.players().find(q => q.el && h.contains(q.el)) : null;
  const s = p ? p.state() : {};
  let white = 0, corner = null;
  if (c && c.width) { try { const x = c.getContext('2d'); corner = x.getImageData(0, 0, 1, 1).data[3];
    if (ink) { const img = x.getImageData(0, 0, c.width, c.height).data;
      for (let i = 0; i < img.length; i += 4 * 97) if (img[i] > 240 && img[i + 1] > 240 && img[i + 2] > 240 && img[i + 3] > 240) white++; } } catch (e) {} }
  return { here: !!h, painted: !!h && !h.hidden && !!at && h.contains(at), on: !!h && h.classList.contains('is-on'),
           leaving: !!h && h.classList.contains('is-leaving'), swell: !!h && h.classList.contains('is-swell'),
           lit: !!g && g.classList.contains('is-lit'),
           bg: h ? getComputedStyle(h).backgroundImage : null, corner: corner, white: white,
           stage: r ? [r.left, r.top, r.width, r.height].map(v => +(v * d).toFixed(2)) : null,
           fill: r && cr ? [cr.left - r.left, cr.top - r.top, cr.width - r.width, cr.height - r.height].map(v => +(v * d).toFixed(2)) : null,
           px: c ? [c.width, c.height] : null, moved: c ? getComputedStyle(c).transform : null,
           canvasThere: !!at && (at.id === 'canvas' || at.id === 'pad' || !!(at.closest && at.closest('.canvas-wrap, .flip-wrap'))),
           seen: (() => { try { return localStorage.getItem('skribl.hello.v1'); } catch (e) { return 'n/a'; } })(),
           state: s.state || null, el: Math.round(s.elapsedMs || 0), total: Math.round(s.totalMs || 0) }; }"""


def _open(ctx, route, force=True, fetched=None):
    if force:
        ctx.add_init_script(FORCE)
    q = ctx.new_page()
    if fetched is not None:
        q.on("request", lambda r: fetched.append(r.url) if "blooby-hello" in r.url else None)
    q.goto(BASE + route, wait_until="load")
    return q


def _until(q, cond, ms):
    t0 = time.time()
    while (time.time() - t0) * 1000 < ms:
        s = q.evaluate(ST, False)
        if cond(s):
            return s, round((time.time() - t0) * 1000)
        q.wait_for_timeout(40)
    return q.evaluate(ST, False), None


def _sharp(s):
    """His box on whole screen pixels, his drawing filling it a whole number of
    its pixels to a screen pixel: twice where the drawing stays within 8
    million pixels, once past that (lib/hello.js's BUDGET). And the canvas
    placed by no transform: the player's own centring is a translate by half,
    which an engine may land between pixels and smooth over."""
    if not s["stage"] or not s["px"]:
        return False, "no stage"
    w, h = round(s["stage"][2]), round(s["stage"][3])
    k = 2 if 4 * w * h <= 8e6 else 1
    grid = all(abs(v - round(v)) <= 0.05 for v in s["stage"])
    ok = grid and s["px"] == [k * w, k * h] and all(abs(v) <= 0.1 for v in s["fill"]) and s["moved"] == "none"
    return ok, (f"stage {s['stage']} screen px, drawing {s['px']} (want {k} x), canvas against the stage "
                f"{s['fill']}, moved by {s['moved']}")


with sync_playwright() as p:
    b = p.chromium.launch()

    # WARM THE SERVER FIRST. A fresh server trims the comments out of each
    # script on its first request (security.py; about 3 s of lexing for the
    # Pad's 107 files here), and his player waits in that queue: on a server's
    # first page he came about 0.2 s inside his 4 s, and in the v327 seal run,
    # where this suite had a fresh server to itself, he missed it. This suite
    # is about him, not a cold server, so both editors are opened once in a
    # context of their own; every row below still opens a fresh browser.
    w = b.new_context(**PHONE)
    for route in ("/skribl-pad", "/flip"):
        _open(w, route)
    w.close()

    for scheme in ("light", "dark"):
        c = b.new_context(color_scheme=scheme, **PHONE)
        got = []
        q = _open(c, "/skribl-pad", fetched=got)
        s, ms = _until(q, lambda s: s["painted"] and s["on"], 8000)
        check(f"Pad, phone, {scheme}: the first open shows him over the whole screen, in the icon's own light "
              "(its lilac deepening to the edge), through a drawing with no ground of its own",
              ms is not None and "radial-gradient" in (s["bg"] or "") and s["corner"] == 0,
              f"{s} after {ms} ms")
        if scheme == "light":
            ok, why = _sharp(s)
            check("...sharp: his box on whole screen pixels and as wide as the screen, his drawing filling it "
                  "a whole number of its pixels to each (one to one here: twice would be 10 million)",
                  ok and round(s["stage"][2]) == 1206, why)
            check("...and the first open is remembered as seen", s["seen"] == "1", str(s["seen"]))
            # The star draws itself first, and its light comes on when it is done.
            first = q.evaluate(ST, True)
            _until(q, lambda s: s["el"] >= STAR_MS + 300, 6000)
            done = q.evaluate(ST, True)
            check(f"...his star draws itself first ({STAR_MS} ms), and its light comes on once it is drawn",
                  first["el"] < STAR_MS - 600 and first["white"] < 0.6 * done["white"] and not first["lit"] and done["lit"],
                  f"at {first['el']} ms: {first['white']} white samples, lit {first['lit']}; "
                  f"at {done['el']} ms: {done['white']}, lit {done['lit']}")
            # The walk-up is 3.3 s after the star, then one wave of the loop's two.
            q.wait_for_timeout(1500)
            mid = q.evaluate(ST, False)
            check("...he is still there through the walk-up, playing",
                  mid["painted"] and mid["state"] == "playing", str(mid))
            s1, _ = _until(q, lambda s: s["leaving"] or not s["here"], 6000)
            check("...he leaves after one wave (the loop's first of two), the picture opening onto the canvas "
                  "a breath larger as it fades",
                  s1["here"] and abs(s1["el"] - (s1["total"] - 1000)) <= 300 and s1["swell"],
                  f"leaving at {s1['el']} ms of {s1['total']}, swelling {s1['swell']}")
            s2, ms2 = _until(q, lambda s: not s["here"], 3000)
            check("...then he fades and is gone, the canvas there again",
                  ms2 is not None and s2["canvasThere"], f"{s2} after a further {ms2} ms")
            q.reload(wait_until="load")
            q.wait_for_timeout(2500)
            again = q.evaluate(ST, False)
            check("...and never again: the next open goes straight to the canvas",
                  not again["painted"] and again["canvasThere"] and len(got) == 1,
                  f"{again}, the hello fetched {len(got)} time(s)")
        c.close()

    # A tap skips him, and the tap draws nothing.
    c = b.new_context(**PHONE)
    q = _open(c, "/skribl-pad")
    s, ms = _until(q, lambda s: s["painted"] and s["on"], 8000)
    q.touchscreen.tap(201, 437)
    s2, ms2 = _until(q, lambda s: not s["here"], 1500)
    ink = q.evaluate("() => { const h = document.getElementById('canvasEmptyHint'); return h && !h.classList.contains('hidden'); }")
    check("a tap skips him at once (gone within the fade), and draws nothing on the canvas",
          ms is not None and ms2 is not None and ms2 <= 1000 and ink, f"gone after {ms2} ms; words still up: {ink}")
    c.close()

    # Reduce Motion: a still hello, its light already on, then the fade.
    c = b.new_context(reduced_motion="reduce", **PHONE)
    q = _open(c, "/skribl-pad")
    s, ms = _until(q, lambda s: s["painted"] and s["on"], 8000)
    states = set()
    t0 = time.time()
    while time.time() - t0 < 1.2:
        states.add(q.evaluate(ST, False)["state"])
        q.wait_for_timeout(100)
    s1, _ = _until(q, lambda s: s["leaving"] or not s["here"], 4000)
    s2, ms2 = _until(q, lambda s: not s["here"], 4000)
    check("Reduce Motion: a still hello (never playing), the star's light on, then he fades, "
          "with no swell, and is gone",
          ms is not None and s["lit"] and "playing" not in states and s1["leaving"] and not s1["swell"]
          and ms2 is not None,
          f"lit {s['lit']}, states {sorted(map(str, states))}, leaving {s1['leaving']} swelling {s1['swell']}, "
          f"gone after a further {ms2} ms")
    c.close()

    # A slow line: his player held for 5 s, past his 4. The page's load waits
    # for that script, so this open waits only for the page's own parse.
    c = b.new_context(**PHONE)
    c.add_init_script(FORCE)
    held = []
    c.route("**/inlineplayer.js*", lambda r: held.append(r))
    q = c.new_page()
    q.goto(BASE + "/skribl-pad", wait_until="domcontentloaded")
    q.wait_for_timeout(5000)
    s = q.evaluate(ST, False)
    for r in held:
        r.continue_()
    c.unroute("**/inlineplayer.js*")
    q.wait_for_timeout(1000)
    s1 = q.evaluate(ST, False)
    q.reload(wait_until="load")
    s2, ms2 = _until(q, lambda s: s["painted"] and s["on"], 8000)
    check("a slow line: his player 5 s late, he does not come (the canvas there, nothing marked seen, "
          "and not when it does arrive), and the next open shows him",
          len(held) == 1 and not s["painted"] and s["canvasThere"] and s["seen"] is None
          and not s1["painted"] and s1["seen"] is None and ms2 is not None and s2["seen"] == "1",
          f"held {len(held)}; at 5 s {s}; once it came {s1}; next open {s2} after {ms2} ms")
    c.close()

    # Flip: the same hello, and one "seen" for both editors.
    c = b.new_context(**PHONE)
    q = _open(c, "/flip")
    s, ms = _until(q, lambda s: s["painted"] and s["on"], 8000)
    check("Flip, phone: the same hello on its first open", ms is not None and _sharp(s)[0], f"{s} after {ms} ms")
    q.touchscreen.tap(201, 437)
    _until(q, lambda s: not s["here"], 1500)
    q.goto(BASE + "/skribl-pad", wait_until="load")
    q.wait_for_timeout(2500)
    pad = q.evaluate(ST, False)
    check("...and seen once is seen for both: the Pad does not show him again", not pad["painted"] and pad["seen"] == "1", str(pad))
    c.close()

    # A desk: the same first hello, at twice its screen's pixels; any key skips
    # him, and the key does nothing else (the Pad's E is the eraser).
    c = b.new_context(**DESK)
    q = _open(c, "/skribl-pad")
    s, ms = _until(q, lambda s: s["painted"] and s["on"], 8000)
    ok, why = _sharp(s)
    check("a desk: the first open shows him too, full height, at twice its screen's pixels",
          ms is not None and ok and s["px"][0] == 2 * round(s["stage"][2]), why)
    q.keyboard.press("e")
    s2, ms2 = _until(q, lambda s: not s["here"], 1500)
    tool = q.evaluate("() => tool")
    q.keyboard.press("e")
    after = q.evaluate("() => tool")
    check("...a key skips him, and does nothing else: the E that skipped him left the pen in hand "
          "(and the next E takes the eraser)",
          ms2 is not None and tool == "pen" and after == "eraser", f"gone after {ms2} ms; tool {tool}, then {after}")
    c.close()

    # Where he never comes, and fetches nothing.
    for name, opts, route, force in (("a composer's frame (?compose=1)", PHONE, "/skribl-pad?compose=1", True),
                                     ("automation that does not ask", PHONE, "/skribl-pad", False)):
        c = b.new_context(**opts)
        got = []
        q = _open(c, route, force=force, fetched=got)
        q.wait_for_timeout(3000)
        s = q.evaluate(ST, False)
        check(f"never in {name}, and nothing of his is fetched" if "frame" in name else f"never to {name}, and nothing of his is fetched",
              not s["painted"] and s["seen"] != "1" and not got, f"{s}, fetched {got}")
        c.close()

    b.close()

summarise_and_exit()
