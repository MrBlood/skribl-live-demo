#!/usr/bin/env python3
"""Skribl says hi: the first time Skribl opens, on any screen (lib/hello.js, FUTURE.md 6m).

The owner's picks, each a row below. The mark writes itself with the real pen,
the i's dot drops in and bounces into place over the i, and the ink lifts away
into the canvas in the order it was written, on the page's own ground, sharp
on the screen's pixel grid. Once only; a tap, a click or a key skips it (and
does nothing else); a still hello under Reduce Motion; the same on Flip with
one "seen" for both; on a desk as on a phone; never in a composer's frame;
nothing fetched when it does not come; and one welcome at a time, so the
button cards' first note waits for another visit.

The mark is the header's own (owner, after v327: "look at the dot on the i.
It's to the right?"), read before any browser: the header's dot straight above
the i's top before the skew, and the hello's drawing on the header's paths,
dot and all (harness/tools/make_hello.py draws it from them).

Automation never meets it unless it asks (window.__skriblHelloForce): every
other suite opens a fresh browser and would otherwise find it over its first
canvas. So this suite asks, and one row proves that without asking it stays
away.

Visible means PAINTED: elementFromPoint at the screen's middle lands inside
it. Gone means removed, and the canvas painted there again. Over the i is read
off the canvas's own pixels; the way out off the screen's, the animation held
at its start and at its middle.

A slow line is a row too: when the player is not here within hello.js's LATE
it does not come that time and is not marked seen, so the next open shows it.
The v327 seal run met that path by accident, on a server's first page (see the
warm-up below), and read it as a failure; this row meets it on purpose. So is
a slow line for the page's own scripts: the hello brings the hold timing with
the player, or it played its drawing as plain pages, all at once (after v327).
And an empty cache on 3G, as a private window has: its files asked for first,
or they queued behind the editor's and it missed its window.
"""
import base64
import io
from array import array
import json
import math
import os
import re
import sys
import time
from assertions import make_check

BASE = os.environ.get("SKRIBL_BASE", "http://127.0.0.1:5001")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HELLO_JSON = os.path.join(ROOT, "skribl", "static", "brand", "hello.json")
KEY = "skribl.hello.v2"
sys.path.insert(0, os.path.join(ROOT, "harness", "tools"))
results = []
check = make_check(results, detail_on_pass=False)


def summarise_and_exit():
    bad = [r for r in results if not r[0]]
    print(f"\n{'=' * 62}\n{len(results) - len(bad)}/{len(results)} passed"
          + ("" if not bad else "  FAILURES: " + ", ".join(r[1] for r in bad)))
    sys.exit(1 if bad else 0)


try:
    from playwright.sync_api import sync_playwright
    from PIL import Image, ImageChops
except ImportError:
    print("SKIP: playwright or Pillow is not installed")
    sys.exit(0)
import make_hello  # noqa: E402  the header's paths, and where the hello's drawing puts them

LEAN = math.tan(math.radians(8))
NEAR = 0.3            # of the mark's units: over the i, and on the header's paths


# ------------------------------------------------------------------ the mark
def header_dot():
    """The header's dot against its i, before the skew (where over is straight
    up): how far the dot's middle is from the i's top, in the mark's units, +
    toward the b. The i's top is the turn in the line nearest under the dot,
    where it stops rising and falls again."""
    word, dot, _, _ = make_hello.mark()
    w, d = make_hello.cubic(word, 24), make_hello.cubic(dot, 24)
    dx = (min(p[0] for p in d) + max(p[0] for p in d)) / 2
    dy = (min(p[1] for p in d) + max(p[1] for p in d)) / 2
    tops = [w[i] for i in range(1, len(w) - 1)
            if w[i][1] < w[i - 1][1] and w[i][1] <= w[i + 1][1] and w[i][1] > dy]
    top = min(tops, key=lambda p: abs(p[0] - dx))
    return round(dx - top[0], 3), top


def _to_line(p, line):
    best = float("inf")
    for (ax, ay), (bx, by) in zip(line, line[1:]):
        vx, vy = bx - ax, by - ay
        t = max(0.0, min(1.0, ((p[0] - ax) * vx + (p[1] - ay) * vy) / ((vx * vx + vy * vy) or 1)))
        best = min(best, math.hypot(p[0] - ax - t * vx, p[1] - ay - t * vy))
    return best


def on_the_mark(path):
    """The hello's drawing against the header's paths, placed as make_hello.py
    places them: the farthest either line strays from the other (each way, so
    a mark with more to it than the drawing shows too), and how far its dot at
    rest is from the mark's dot, both in the mark's units."""
    d = json.load(open(path))
    cs = d["canvasSize"]
    word, _, dot, _, s = make_hello.fit(cs["cssWidth"], cs["cssHeight"])
    drawn = [(p["x"], p["y"]) for p in d["frames"][0]["strokes"]]
    far = max(max(_to_line(p, word) for p in drawn), max(_to_line(p, drawn) for p in word)) / s
    last = d["frames"][-1]["strokes"]
    lx = (min(p["x"] for p in last) + max(p["x"] for p in last)) / 2
    ly = (min(p["y"] for p in last) + max(p["y"] for p in last)) / 2
    fx, fy = sum(p[0] for p in dot) / len(dot), sum(p[1] for p in dot) / len(dot)
    return round(far, 3), round(math.hypot(lx - fx, ly - fy) / s, 3)


# ------------------------------------------------------------------ pixels
def _png(data_url_or_bytes):
    raw = data_url_or_bytes
    if not raw or raw == "data:,":
        return None                                     # gone, or nothing to draw on
    if isinstance(raw, str):
        raw = base64.b64decode(raw.split(",", 1)[1])
    return Image.open(io.BytesIO(raw)).convert("RGBA")


def _pieces(im, least=30):
    """The separate pieces of ink (alpha over half): (labels, [(id, pixels, x0, y0, x1, y1)]), biggest first."""
    w, h = im.size
    mask = im.getchannel("A").point(lambda v: 1 if v > 128 else 0).tobytes()
    if mask.count(1) > w * h // 4:                      # a ground, not a line: one piece, unread
        return None, [(0, mask.count(1), 0, 0, w - 1, h - 1)]
    label = array("H", bytes(2 * w * h))
    out, nid, i = [], 0, mask.find(1)
    while i != -1:
        if not label[i]:
            nid += 1
            label[i] = nid
            stack, n, x0, y0, x1, y1 = [i], 0, w, h, 0, 0
            while stack:
                j = stack.pop()
                n += 1
                x, y = j % w, j // w
                x0, y0, x1, y1 = min(x0, x), min(y0, y), max(x1, x), max(y1, y)
                for k in ((j - 1) if x else -1, (j + 1) if x + 1 < w else -1, j - w, j + w):
                    if 0 <= k < w * h and mask[k] and not label[k]:
                        label[k] = nid
                        stack.append(k)
            if n >= least:
                out.append((nid, n, x0, y0, x1, y1))
        i = mask.find(1, i + 1)
    return label, sorted(out, key=lambda c: -c[1])


def dot_over_i(im, unit):
    """Read off the drawn pixels: the dot against the i under it, along the
    i's 8-degree lean, in the mark's units (+ toward the b). `unit` is the
    canvas pixels to one of the mark's units. None when there is no dot."""
    if im is None:
        return None, "gone before it could be read"
    w, h = im.size
    label, pieces = _pieces(im)
    if len(pieces) != 2:
        return None, f"{len(pieces)} piece(s) of ink"
    word, dot = pieces
    cx, cy = (dot[2] + dot[4]) / 2, (dot[3] + dot[5]) / 2
    # Under the dot, the turn at the top of a line: a peak, the line falling
    # away on both sides of it, nearest the dot. Not any line that passes
    # beside the dot (ink at its height: the b's tall stem, just to the
    # right), and not the slope up to one (the b's edge, rising toward it).
    ends = {}
    for x in range(max(0, int(cx - 3.5 * unit)), min(w, int(cx + 3.5 * unit) + 1)):
        if any(label[y * w + x] == word[0] for y in range(dot[3], dot[5] + 1)):
            continue
        y = next((y for y in range(dot[5] + 1, h) if label[y * w + x] == word[0]), None)
        if y is not None:
            ends[x] = y
    k = max(2, int(0.6 * unit))
    peaks = [x for x in ends if all(x + d in ends and ends[x] <= ends[x + d] for d in range(-k, k + 1))]
    if not peaks:
        return None, "no i under the dot"
    peak = min(peaks, key=lambda x: abs(x - cx))
    top = ends[peak]
    cols = [x for x in ends if abs(x - peak) <= 1.2 * unit]
    xs = [x for y in range(top, min(h, top + int(1.2 * unit))) for x in cols if label[y * w + x] == word[0]]
    tx = sum(xs) / len(xs)
    cusp = top + 1.15 * unit                            # the line's turn, half the pen under its ink's top
    off = (cx - (tx + LEAN * (cusp - cy))) / unit
    return round(off, 3), f"dot at ({cx:.0f}, {cy:.0f}), the i's top at ({tx:.0f}, {top})"


def _lum(rgb):
    c = [v / 255 for v in rgb[:3]]
    c = [v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in c]
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def contrast(a, b):
    la, lb = _lum(a), _lum(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def _hex(s):
    s = s.strip().lstrip("#")
    return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))


def _rgb(s):
    return tuple(int(float(v)) for v in s[s.index("(") + 1:s.index(")")].split(",")[:3])


def exit_read(a, b, ground):
    """The way out, held at its start (a) and at its middle (b), off the
    screen's own pixels: the ink of the word's first letters and of its last,
    how far the last rose (a share of the height) and how soft their edge
    went (edge pixels to ink)."""
    g = Image.new("RGB", a.size, ground)
    da, db = (ImageChops.difference(im.convert("RGB"), g).convert("L") for im in (a, b))
    box = da.point(lambda v: 255 if v > 40 else 0).getbbox()
    if not box:
        return {"left": (0, 0), "right": (0, 0), "rise": 0, "soft": (0, 0), "start": "no ink"}
    x0, _, x1, _ = box
    span, h = x1 - x0, a.size[1]
    left, right = (x0, 0, x0 + int(0.3 * span), h), (x1 - int(0.3 * span), 0, x1, h)

    def part(d, box):
        crop = d.crop(box)
        near = crop.point(lambda v: 255 if v > 40 else 0)
        n = near.histogram()[255]
        edge = crop.point(lambda v: 255 if 15 < v <= 40 else 0).histogram()[255]
        rows = near.resize((1, h), Image.BOX).tobytes()
        mid = sum(y * v for y, v in enumerate(rows)) / max(1, sum(rows))
        return n, mid, edge / max(1, n)
    la, lb, ra, rb = part(da, left), part(db, left), part(da, right), part(db, right)
    return {"left": (la[0], lb[0]), "right": (ra[0], rb[0]), "rise": round((ra[1] - rb[1]) / h, 4),
            "soft": (round(ra[2], 3), round(rb[2], 3))}


# ------------------------------------------------------------------ before any browser
print("SKRIBL SAYS HI — the first open, on any screen")
off, top = header_dot()
check(f"the header's dot is over the i: straight above the i's top {top} before the skew, within {NEAR} "
      "of the mark's units", abs(off) <= NEAR, f"{off:+} of the mark's units (+ toward the b)")
far, dot_off = on_the_mark(HELLO_JSON)
check(f"the hello writes the header's own mark: its line within {NEAR} of the mark's units of the header's, "
      "its dot at rest on the header's dot", far <= NEAR and dot_off <= NEAR,
      f"its line strays {far}, its dot is {dot_off} away (make_hello.py draws it from the template)")
HELLO = json.load(open(HELLO_JSON))
CSS_W = HELLO["canvasSize"]["cssWidth"]
PEN = HELLO["frames"][0]["strokes"][0]["size"] / make_hello.mark()[3]     # canvas points to one of the mark's units
SWEEP = sorted({p["color"] for p in HELLO["frames"][0]["strokes"]} | {p["color"] for p in HELLO["frames"][-1]["strokes"]})

PHONE = dict(viewport={"width": 402, "height": 874}, device_scale_factor=3, is_mobile=True, has_touch=True,
             screen={"width": 402, "height": 874})
DESK = dict(viewport={"width": 1333, "height": 906})
FORCE = "window.__skriblHelloForce = true;"
# `ink`: count the ink in the drawing too (a sample of every 97th pixel), a
# read of the whole canvas, so only where a row needs it.
ST = """(ink) => { const h = document.getElementById('skriblHello'), c = h && h.querySelector('canvas');
  const st = h && h.querySelector('.skribl-hello-stage');
  const at = document.elementFromPoint(innerWidth / 2, innerHeight / 2), d = devicePixelRatio;
  const r = st && st.getBoundingClientRect(), cr = c && c.getBoundingClientRect();
  const p = h && window.SkriblInline ? SkriblInline.players().find(q => q.el && h.contains(q.el)) : null;
  const s = p ? p.state() : {};
  let n = 0, corner = null;
  if (c && c.width) { try { const x = c.getContext('2d'); corner = x.getImageData(0, 0, 1, 1).data[3];
    if (ink) { const img = x.getImageData(0, 0, c.width, c.height).data;
      for (let i = 3; i < img.length; i += 4 * 97) if (img[i] > 128) n++; } } catch (e) {} }
  const cs = h ? getComputedStyle(h) : null;
  return { here: !!h, painted: !!h && !h.hidden && !!at && h.contains(at), on: !!h && h.classList.contains('is-on'),
           leaving: !!h && h.classList.contains('is-leaving'), evaporating: !!h && h.classList.contains('is-evaporating'),
           bg: cs ? cs.backgroundColor : null, image: cs ? cs.backgroundImage : null,
           ground: getComputedStyle(document.documentElement).getPropertyValue('--surface-base').trim(),
           corner: corner, ink: n,
           stage: r ? [r.left, r.top, r.width, r.height].map(v => +(v * d).toFixed(2)) : null,
           box: r ? [r.left, r.top, r.width, r.height] : null,
           fill: r && cr ? [cr.left - r.left, cr.top - r.top, cr.width - r.width, cr.height - r.height].map(v => +(v * d).toFixed(2)) : null,
           px: c ? [c.width, c.height] : null, moved: c ? getComputedStyle(c).transform : null,
           canvasThere: !!at && (at.id === 'canvas' || at.id === 'pad' || !!(at.closest && at.closest('.canvas-wrap, .flip-wrap'))),
           seen: (() => { try { return localStorage.getItem('""" + KEY + """'); } catch (e) { return 'n/a'; } })(),
           state: s.state || null, el: Math.round(s.elapsedMs || 0), total: Math.round(s.totalMs || 0) }; }"""
BITMAP = "() => { const c = document.querySelector('#skriblHello canvas'); return c ? c.toDataURL('image/png') : null; }"
# The canvas's own pixels at a moment of the drawing, read in the same breath
# as the clock: once the drawing is `t` ms in, its picture then.
WORD = """(t) => { const h = document.getElementById('skriblHello'), c = h && h.querySelector('canvas');
  const p = h && SkriblInline.players().find(q => q.el && h.contains(q.el));
  const el = p ? Math.round(p.state().elapsedMs) : -1;
  return el >= t ? { el: el, png: c.toDataURL('image/png') } : { el: el }; }"""
# Hold the way out at its start the moment it begins, before a frame of it is
# drawn (the ink's lifting and the ground's fade, every one of them), and say
# where the drawing was then. Armed while the hello plays; the suite waits for it.
HOLD = """() => { const h = document.getElementById('skriblHello');
  const p = SkriblInline.players().find(q => q.el && h.contains(q.el));
  new MutationObserver((m, o) => { if (!h.classList.contains('is-leaving')) return; o.disconnect();
    const all = h.getAnimations({ subtree: true });
    for (const x of all) { x.pause(); x.currentTime = 0; }
    window.__helloHeld = { el: Math.round(p.state().elapsedMs), total: Math.round(p.state().totalMs),
                           moving: all.filter(x => x.effect && x.effect.target !== h).map(x => x.transitionProperty || x.animationName).sort(),
                           evaporating: h.classList.contains('is-evaporating') }; })
    .observe(h, { attributes: true, attributeFilter: ['class'] }); }"""
# All of them moved to `ms` into the way out.
AT = """(ms) => { const h = document.getElementById('skriblHello'); if (!h) return 0;
  for (const x of h.getAnimations({ subtree: true })) x.currentTime = ms;
  return +getComputedStyle(h).opacity; }"""
GO = """() => { const h = document.getElementById('skriblHello'); if (h) for (const x of h.getAnimations({ subtree: true })) x.play(); }"""


def _open(ctx, route, force=True, fetched=None):
    if force:
        ctx.add_init_script(FORCE)
    q = ctx.new_page()
    if fetched is not None:
        q.on("request", lambda r: fetched.append(r.url) if "/brand/hello.json" in r.url else None)
    q.goto(BASE + route, wait_until="load")
    return q


def _until(q, cond, ms, ink=False):
    t0 = time.time()
    while (time.time() - t0) * 1000 < ms:
        s = q.evaluate(ST, ink)
        if cond(s):
            return s, round((time.time() - t0) * 1000)
        q.wait_for_timeout(40)
    return q.evaluate(ST, ink), None


def _sharp(s):
    """The box on whole screen pixels, the drawing filling it a whole number of
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
    # Pad's 107 files here), and the player waits in that queue: on a server's
    # first page the hello came about 0.2 s inside its 4 s, and in the v327
    # seal run, where this suite had a fresh server to itself, it missed. This
    # suite is about the hello, not a cold server, so both editors are opened
    # once in a context of their own; every row below still opens a fresh browser.
    w = b.new_context(**PHONE)
    for route in ("/skribl-pad", "/flip"):
        _open(w, route)
    w.close()

    for scheme in ("light", "dark"):
        c = b.new_context(color_scheme=scheme, **PHONE)
        got = []
        q = _open(c, "/skribl-pad", fetched=got)
        s, ms = _until(q, lambda s: s["painted"] and s["on"], 8000)
        ground = _hex(s["ground"]) if s["ground"] else None
        least = min(contrast(_hex(k), ground) for k in SWEEP) if ground else 0
        check(f"Pad, phone, {scheme}: the first open shows it over the whole screen, on the page's own ground, "
              "through a drawing with no ground of its own, every colour of the mark's sweep at least 3:1 on it",
              ms is not None and s["bg"] and _rgb(s["bg"]) == ground and s["image"] == "none"
              and s["corner"] == 0 and least >= 3.0,
              f"ground {s['ground']}, painted {s['bg']} {s['image']}, corner alpha {s['corner']}, "
              f"the sweep at least {least:.2f}:1, after {ms} ms")
        if scheme == "light":
            ok, why = _sharp(s)
            check("...sharp: its box on whole screen pixels and as wide as the screen, the drawing filling it "
                  "a whole number of its pixels to each (one to one here: twice would be 10 million)",
                  ok and round(s["stage"][2]) == 1206, why)
            check("...and the first open is remembered as seen", s["seen"] == "1", str(s["seen"]))
            # The mark writes itself, and the dot is not there until it has.
            q.evaluate(HOLD)
            H = q.evaluate("(f) => SkriblHold.pageMs(f, 12)", HELLO["frames"][0])
            early, _ = _until(q, lambda s: s["el"] >= 300, 4000, ink=True)
            t0 = time.time()
            late = q.evaluate(WORD, H - 300)
            while "png" not in late and time.time() - t0 < 4:
                q.wait_for_timeout(30)
                late = q.evaluate(WORD, H - 300)
            word = _png(late["png"]) if "png" in late else None
            pieces = _pieces(word)[1] if word else []
            whole = sum(1 for v in word.tobytes()[3::4 * 97] if v > 128) if word else 0   # as ST samples it
            check(f"...the mark writes itself first ({H} ms), its dot not there until it has",
                  early["el"] < 0.6 * H and early["ink"] < 0.6 * whole and late["el"] < H and len(pieces) == 1,
                  f"at {early['el']} ms {early['ink']} ink samples, at {late['el']} ms {whole} "
                  f"in {len(pieces)} piece(s) of ink")
            # Then the dot, and the way out, held at its start the moment it begins.
            try:
                q.wait_for_function("() => window.__helloHeld", timeout=8000)
            except Exception:
                pass
            held = q.evaluate("() => window.__helloHeld || null") or {"el": -1, "total": 0, "moving": [], "evaporating": False}
            end = _png(q.evaluate(BITMAP))
            box = q.evaluate("() => { const st = document.querySelector('#skriblHello .skribl-hello-stage'); if (!st) return null;"
                             " const r = st.getBoundingClientRect(); return { x: r.left, y: r.top, width: r.width, height: r.height }; }")
            a = _png(q.screenshot(clip=box, scale="css")) if box else None
            mid = q.evaluate(AT, 450)
            bb = _png(q.screenshot(clip=box, scale="css")) if box else None
            q.evaluate(GO)
            off2, why2 = dot_over_i(end, PEN * end.size[0] / CSS_W if end else 1)
            check(f"...then the dot drops in and comes to rest over the i, along its lean, within {NEAR} "
                  "of the mark's units (read off the canvas's pixels)",
                  off2 is not None and abs(off2) <= NEAR, f"{off2} of the mark's units (+ toward the b): {why2}")
            e = exit_read(a, bb, ground) if a and bb else {"left": (0, 0), "right": (0, 0), "rise": 0, "soft": (0, 0), "start": "gone"}
            check("...it goes once the dot is at rest, the ink lifting away in the order it was written: halfway, "
                  "the first letters gone and the last still there, risen and softened, the ground still whole",
                  held["evaporating"] and sorted("mask" if "mask-position" in n else n for n in held["moving"]) == ["filter", "mask", "transform"]
                  and e["left"][0] > 0
                  and held["el"] >= held["total"] - 250
                  and e["left"][1] <= 0.15 * e["left"][0] and e["right"][1] >= 0.6 * e["right"][0]
                  and e["rise"] >= 0.005 and e["soft"][1] >= 1.5 * e["soft"][0] + 0.02 and mid >= 0.98,
                  f"left at {held['el']} of {held['total']} ms (evaporating {held['evaporating']}, moving "
                  f"{held['moving']}); halfway {e}, the ground's opacity {mid}")
            s2, ms2 = _until(q, lambda s: not s["here"], 3000)
            check("...then it is gone, the canvas there again",
                  ms2 is not None and s2["canvasThere"], f"{s2} after a further {ms2} ms")
            q.reload(wait_until="load")
            q.wait_for_timeout(2500)
            again = q.evaluate(ST, False)
            check("...and never again: the next open goes straight to the canvas",
                  not again["painted"] and again["canvasThere"] and len(got) == 1,
                  f"{again}, the hello fetched {len(got)} time(s)")
        c.close()

    # A tap skips it, what is written holds while it goes, and the tap draws nothing.
    c = b.new_context(**PHONE)
    q = _open(c, "/skribl-pad")
    s, ms = _until(q, lambda s: s["painted"] and s["on"] and s["el"] >= 500, 8000)
    q.touchscreen.tap(201, 437)
    h1 = q.evaluate(ST, True)
    q.wait_for_timeout(300)
    h2 = q.evaluate(ST, True)
    s2, ms2 = _until(q, lambda s: not s["here"], 1500)
    ink = q.evaluate("() => { const h = document.getElementById('canvasEmptyHint'); return h && !h.classList.contains('hidden'); }")
    check("a tap skips it at once (gone within its way out), what was written holds while it goes, "
          "and the tap draws nothing on the canvas",
          ms is not None and h1["state"] == "paused" and h2["ink"] == h1["ink"] and ms2 is not None
          and ms2 <= 1400 and ink,
          f"after the tap {h1['state']} with {h1['ink']} ink samples, 0.3 s on {h2['ink']}; gone after a further "
          f"{ms2} ms; words still up: {ink}")
    c.close()

    # Reduce Motion: a still hello, the finished mark with its dot in place, then it just fades.
    c = b.new_context(reduced_motion="reduce", **PHONE)
    q = _open(c, "/skribl-pad")
    s, ms = _until(q, lambda s: s["painted"] and s["on"], 8000)
    still, why = (None, "no canvas")
    if ms is not None:
        im = _png(q.evaluate(BITMAP))
        still, why = dot_over_i(im, PEN * im.size[0] / CSS_W if im else 1)
    states = set()
    t0 = time.time()
    while time.time() - t0 < 1.2:
        states.add(q.evaluate(ST, False)["state"])
        q.wait_for_timeout(100)
    s1, _ = _until(q, lambda s: s["leaving"] or not s["here"], 4000)
    s2, ms2 = _until(q, lambda s: not s["here"], 4000)
    check("Reduce Motion: a still hello (never playing), the finished mark with its dot over the i, "
          "then it just fades, with nothing lifting away, and is gone",
          ms is not None and still is not None and abs(still) <= NEAR and "playing" not in states
          and s1["leaving"] and not s1["evaporating"] and ms2 is not None,
          f"the still's dot {still} ({why}), states {sorted(map(str, states))}, leaving {s1['leaving']} "
          f"lifting away {s1['evaporating']}, gone after a further {ms2} ms")
    c.close()

    # A slow line: the player held for 5 s, past its 4. The page's load waits
    # for that script, so this open waits only for the page's own parse.
    c = b.new_context(**PHONE)
    c.add_init_script(FORCE)
    held_js = []
    c.route("**/inlineplayer.js*", lambda r: held_js.append(r))
    q = c.new_page()
    q.goto(BASE + "/skribl-pad", wait_until="domcontentloaded")
    q.wait_for_timeout(5000)
    s = q.evaluate(ST, False)
    for r in held_js:
        r.continue_()
    c.unroute("**/inlineplayer.js*")
    q.wait_for_timeout(1000)
    s1 = q.evaluate(ST, False)
    q.reload(wait_until="load")
    s2, ms2 = _until(q, lambda s: s["painted"] and s["on"], 8000)
    check("a slow line: the player 5 s late, it does not come (the canvas there, nothing marked seen, "
          "and not when the player does arrive), and the next open shows it",
          len(held_js) == 1 and not s["painted"] and s["canvasThere"] and s["seen"] is None
          and not s1["painted"] and s1["seen"] is None and ms2 is not None and s2["seen"] == "1",
          f"held {len(held_js)}; at 5 s {s}; once it came {s1}; next open {s2} after {ms2} ms")
    c.close()

    # A slow line for the page's own scripts: the first of them after the
    # hello held, and scripts deferred run in order, so every one behind it
    # waits too, the page's own copy of the hold timing among them, while the
    # player and the drawing come quickly. (Holding them all queued the
    # hello's own files behind them.) The hello brings the hold timing with
    # the player; without it the mark played as plain pages, all at once and
    # gone in 0.8 s.
    c = b.new_context(**PHONE)
    c.add_init_script(FORCE)
    srcs = [u.split("?")[0] for u in re.findall(r'<script src="([^"]+)" defer', c.request.get(BASE + "/skribl-pad").text())]
    at = next((k for k, u in enumerate(srcs) if u.endswith("/lib/hello.js")), -1)
    behind = srcs[at + 1] if 0 <= at < len(srcs) - 1 else None
    hold_after = behind is not None and any(u.endswith("/lib/holdtiming.js") for u in srcs[at + 2:])
    held_page = []
    c.route(lambda url: behind is not None and url.split("?")[0].endswith(behind), lambda r: held_page.append(r))
    q = c.new_page()
    q.goto(BASE + "/skribl-pad", wait_until="commit")
    plan, t0 = None, time.time()
    while plan is None and time.time() - t0 < 6:
        plan = q.evaluate("""() => { const h = document.getElementById('skriblHello');
            const p = h && window.SkriblInline && SkriblInline.players().find(x => x.el && h.contains(x.el));
            return p ? { total: Math.round(p.state().totalMs), pageRan: typeof window.openDrawer === 'function' } : null; }""")
        if plan is None:
            q.wait_for_timeout(50)
    for r in held_page:
        r.continue_()
    q.wait_for_function("() => !!window.SkriblHold", timeout=8000)
    timed = q.evaluate("(d) => Math.round(SkriblHold.plan(d.frames, d.fps || 12, d.loop).cycle)", HELLO)
    check("a slow line for the page's own scripts: the hello brings the hold timing with the player, so the mark "
          f"still writes itself in its own time ({timed} ms), never as plain pages all at once",
          hold_after and len(held_page) == 1 and plan is not None and not plan["pageRan"] and plan["total"] == timed,
          f"held {behind} ({len(held_page)}), the hold timing behind it: {hold_after}; the hello's player {plan}")
    c.close()

    # An empty cache on a slow line, as a first visit in a private window on
    # a phone meets it (owner: "Why does it not show every time in
    # incognito"): 3G as DevTools has it. The hello's three files were asked
    # for after the editor's hundred-odd scripts and came with them, 6.5 s
    # into its 4, so it did not come; asked for first, they are here within
    # its first second and it plays while the editor is still loading. The
    # hold timing is asked for twice, the page's copy and the hello's, so
    # its first arrival is the hello's.
    c = b.new_context(**PHONE)
    c.add_init_script(FORCE)
    q = c.new_page()
    cdp = c.new_cdp_session(q)
    cdp.send("Network.enable")
    cdp.send("Network.emulateNetworkConditions", {"offline": False, "latency": 300,
                                                  "downloadThroughput": 0.78e6 / 8, "uploadThroughput": 0.33e6 / 8})
    q.goto(BASE + "/skribl-pad", wait_until="commit", timeout=60000)
    q.wait_for_function("() => !!document.body", timeout=30000)
    s3, ms3 = _until(q, lambda s: (s["painted"] and s["on"]) or not s["here"], 15000)
    q.wait_for_load_state("domcontentloaded", timeout=60000)
    tm = q.evaluate("""() => { const ends = n => performance.getEntriesByType('resource').filter(e => e.name.includes(n)).map(e => e.responseEnd);
        const late = n => Math.max(0, ...ends(n)), first = n => ends(n).length ? Math.min(...ends(n)) : Infinity;
        return { own: Math.round(Math.max(late('/inlineplayer.js'), first('/lib/holdtiming.js'), late('/brand/hello.json'))),
                 page: Math.round(performance.getEntriesByType('navigation')[0].domContentLoadedEventEnd) }; }""")
    check("an empty cache on a slow line (3G), as a first visit in a private window: the hello still comes, "
          "its own files asked for first and here before the editor's own scripts",
          ms3 is not None and s3["painted"] and tm["own"] < tm["page"],
          f"came {s3['painted']} after {ms3} ms (here {s3['here']}); its files by {tm['own']} ms, the page's by {tm['page']} ms")
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
    check("...and seen once is seen for both: the Pad does not show it again", not pad["painted"] and pad["seen"] == "1", str(pad))
    c.close()

    # A desk: the same first hello, at twice its screen's pixels; any key skips
    # it, and the key does nothing else (the Pad's E is the eraser).
    c = b.new_context(**DESK)
    q = _open(c, "/skribl-pad")
    s, ms = _until(q, lambda s: s["painted"] and s["on"], 8000)
    ok, why = _sharp(s)
    check("a desk: the first open shows it too, full height, at twice its screen's pixels",
          ms is not None and ok and s["px"][0] == 2 * round(s["stage"][2]), why)
    q.keyboard.press("e")
    s2, ms2 = _until(q, lambda s: not s["here"], 1500)
    tool = q.evaluate("() => tool")
    q.keyboard.press("e")
    after = q.evaluate("() => tool")
    check("...a key skips it, and does nothing else: the E that skipped it left the pen in hand "
          "(and the next E takes the eraser)",
          ms2 is not None and tool == "pen" and after == "eraser", f"gone after {ms2} ms; tool {tool}, then {after}")
    c.close()

    # One welcome at a time, on a desk too: the visit it says hi, the button
    # cards' first note (lib/learncard.js, asked for here) waits for another.
    c = b.new_context(**DESK)
    c.add_init_script("window.__skriblLearnForce = true;")
    q = _open(c, "/skribl-pad")
    s, ms = _until(q, lambda s: s["painted"] and s["on"], 8000)
    notes = []
    t0 = time.time()
    while time.time() - t0 < 6:
        notes.append(q.evaluate("() => !!document.querySelector('.lc-note')"))
        q.wait_for_timeout(200)
    gone = q.evaluate("() => !document.getElementById('skriblHello')")
    check("one welcome at a time, on a desk too: the visit it says hi, the button cards' first note "
          "waits for another visit",
          ms is not None and gone and not any(notes), f"came after {ms} ms; gone {gone}; a note up {any(notes)}")
    c.close()

    # Where it never comes, and fetches nothing.
    for name, opts, route, force in (("a composer's frame (?compose=1)", PHONE, "/skribl-pad?compose=1", True),
                                     ("automation that does not ask", PHONE, "/skribl-pad", False)):
        c = b.new_context(**opts)
        got = []
        q = _open(c, route, force=force, fetched=got)
        q.wait_for_timeout(3000)
        s = q.evaluate(ST, False)
        check(f"never in {name}, and nothing of it is fetched" if "frame" in name else f"never to {name}, and nothing of it is fetched",
              not s["here"] and s["seen"] != "1" and not got, f"{s}, fetched {got}")
        c.close()

    b.close()

summarise_and_exit()
