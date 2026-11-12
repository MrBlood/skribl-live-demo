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
or they queued behind the editor's and it missed its window, and drawn once the
page's own scripts are done, or it froze as each of them ran. And the replay
link: ?hello=again plays it again where it was seen, asking as this suite does.

Its ground first (owner, after the desktop checks: "on a reload it goes to the
canvas first, then goes to the skribl cursive"): read off every frame the
screen makes on a reload of the replay link, the first thing painted is the
hello's ground and nothing of the page shows before the hello. The ground
holds the page only while the page's own scripts come; and if lib/hello.js
never runs it goes by itself. Whether it comes is the head's decision alone
(_skribl_hello_boot.html), with the one key lib/hello.js marks.
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


def on_the_mark(path, look=make_hello.SKRIBL):
    """The hello's drawing against the header's paths, placed as make_hello.py
    places them: the farthest either line strays from the other (each way, so
    a mark with more to it than the drawing shows too), and how far its dot at
    rest is from the mark's dot, both in the mark's units."""
    d = json.load(open(path))
    cs = d["canvasSize"]
    word, _, dot, _, s = make_hello.fit(cs["cssWidth"], cs["cssHeight"], look=look)
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
# Whether it comes is decided in the page's head, before the first paint
# (_skribl_hello_boot.html), and lib/hello.js marks it seen: the one key in
# both, and no second decision in lib/hello.js (no read of what was seen).
# The key is Skribl's own, or a host's own hello's (skribl/brand.py), which
# the one brand hands to both: the head reads it, and the hello's partial
# gives it to lib/hello.js as data-hello-key (verify_hostseams reads both on
# a host's page; the site's part below, in the browser).
_boot = open(os.path.join(ROOT, "skribl", "templates", "skribl", "_skribl_hello_boot.html")).read()
_part = open(os.path.join(ROOT, "skribl", "templates", "skribl", "_skribl_hello.html")).read()
_js = open(os.path.join(ROOT, "skribl", "static", "lib", "hello.js")).read()
_bk = re.findall(r"localStorage\.getItem\('\{\{ skribl_brand\.hello_key if skribl_brand and skribl_brand\.hello_key "
                 r"else '([^']+)' \}\}'\)", _boot)
_jk = re.findall(r"var KEY = el\.getAttribute\('data-hello-key'\) \|\| '([^']+)'", _js)
_pk = re.findall(r'data-hello-key="\{\{ skribl_brand\.hello_key \}\}"', _part)
check("the head decides whether it comes and lib/hello.js marks it seen, with the one key (Skribl's own, or a host's "
      "own hello's, handed to both from the one brand); lib/hello.js decides nothing again",
      _bk == [KEY] and _jk == [KEY] and len(_pk) == 1 and len(re.findall(r"localStorage\.getItem", _boot)) == 1
      and "localStorage.getItem" not in _js,
      f"the head reads {_bk} (or the brand's), lib/hello.js marks {_jk} (or the partial's {len(_pk)}), and reads "
      f"seen itself: {'localStorage.getItem' in _js}")
HELLO = json.load(open(HELLO_JSON))


def dot_pages(d):
    """Each of the dot's pages after the word: how tall it is against how wide,
    and how far its middle is from where it rests, in its own size."""
    last = d["frames"][-1]["strokes"]
    rx = (min(p["x"] for p in last) + max(p["x"] for p in last)) / 2
    ry = (min(p["y"] for p in last) + max(p["y"] for p in last)) / 2
    out = []
    for f in d["frames"][1:]:
        s = f["strokes"]
        if not s:
            out.append(None)
            continue
        x0, x1 = min(p["x"] for p in s), max(p["x"] for p in s)
        y0, y1 = min(p["y"] for p in s), max(p["y"] for p in s)
        out.append((round((y1 - y0 + s[0]["size"]) / (x1 - x0 + s[0]["size"]), 2),
                    round(math.hypot((x0 + x1) / 2 - rx, (y0 + y1) / 2 - ry) / last[0]["size"], 2)))
    return out


# THE WINK (owner: "A, the wink. build it."): settled over the i, the dot
# closes like an eye, a line for one page, half shut either side of it, and
# rests open to the end. Read off the drawing's own pages.
DOTS = dot_pages(HELLO)
SHUT = [k for k, s in enumerate(DOTS) if s and s[0] < 0.3]
WINK = SHUT[0] if len(SHUT) == 1 else None
check("...and once it rests, it winks: shut to a line for one page, half shut either side, open to the end",
      WINK is not None and 0 < WINK < len(DOTS) - 3 and DOTS[WINK][1] < 0.25
      and any(s and s[0] > 0.85 and s[1] < 0.05 for s in DOTS[:WINK - 1])
      and all(DOTS[j] and 0.3 <= DOTS[j][0] < 0.85 and DOTS[j][1] < 0.25 for j in (WINK - 1, WINK + 1))
      and all(s and s[0] > 0.85 and s[1] < 0.05 for s in DOTS[-2:]),
      f"the dot's pages (tall against wide, off its rest): {DOTS}")
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


# THE FADE'S RECORD (Reduce Motion): the hello's opacity on every frame the
# screen makes, whether it is on and leaving, and when the frame came; "gone"
# on the first frame after it leaves the page, with when.
FADE_REC = """window.__fade = []; (function f() {
    const h = document.getElementById('skriblHello');
    if (h) __fade.push([h.classList.contains('is-on'), h.classList.contains('is-leaving'),
                        +getComputedStyle(h).opacity, performance.now()]);
    else if (__fade.length && __fade[__fade.length - 1] !== 'gone') { __fade.push('gone'); window.__goneAt = performance.now(); }
    requestAnimationFrame(f); })();"""
# A frame held this long is the page's thread stalled, not the fade: three
# frames at 60 Hz. The fade coming in is 0.25 s of ease, whose steepest step
# passes a third of the way in about 53 ms.
HELLO_STALL_MS = 50


def read_fade(q):
    """The fade's record, once its last frame has come: "gone" is written on
    the first frame after the hello leaves the page; _until saw it leave, and
    on a busy runner that frame had not come yet (main after #600, both lanes:
    every step green, the record ending a frame early)."""
    try:
        q.wait_for_function("() => (window.__fade || []).slice(-1)[0] === 'gone'", timeout=3000)
    except Exception:  # noqa: BLE001 (the record says it did not end)
        pass
    return q.evaluate("() => [window.__fade, window.__goneAt || null]")


def fade_verdict(fade, gone_at):
    """(ok, frozen, come, go, frames read). Each part with the frame either
    side of it, so a jump at its edge is a step: coming in runs from before it
    is on to its last frame resting; going, from that frame to gone (read as
    nothing). Each part: (frames between, the largest step, whether a step over
    a third came in a frame of ordinary length, the longest frame in ms).
    Frozen: failed, but every step over a third came across a stalled frame."""
    rows = [r for r in fade if r != "gone"]

    def glide(part):
        mid = sum(1 for r in part if 0.05 < r[2] < 0.95)
        steps = [(abs(y[2] - x[2]), (y[3] - x[3]) if x[3] is not None and y[3] is not None else None)
                 for x, y in zip(part, part[1:])]
        step = max((s for s, _ in steps), default=1.0)
        cut = any(s > 0.34 and (dt is None or dt <= HELLO_STALL_MS) for s, dt in steps)
        longest = max((dt for _, dt in steps if dt is not None), default=0.0)
        return mid, round(step, 2), cut, round(longest)

    first_go = next((i for i, r in enumerate(rows) if r[1]), len(rows))
    come = glide(rows[:first_go])
    go = glide(rows[max(first_go - 1, 0):] + ([[False, True, 0.0, gone_at]] if fade[-1:] == ["gone"] else []))
    ok = come[0] >= 3 and come[1] <= 0.34 and go[0] >= 5 and go[1] <= 0.34 and fade[-1:] == ["gone"]
    frozen = (not ok and fade[-1:] == ["gone"] and not come[2] and not go[2]
              and max(come[3], go[3]) > HELLO_STALL_MS)
    return ok, frozen, come, go, len(rows)


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


LEFT = (0, 255, 0)    # the page a reload leaves, painted a colour no Skribl page is


def _seen(png, ground):
    """What one frame of the screen shows: the page being left, a blank
    frame, the PAGE (its header or its dock: anything but the ground along
    the top or the foot, where the hello draws nothing), the hello's ink on
    its ground, or the ground alone."""
    im = _png(png).convert("RGB")
    im = im.resize((im.width // 4, im.height // 4))
    w, h = im.size
    px = im.load()

    def share(y0, y1, test):
        pts = [px[x, y] for y in range(y0, y1) for x in range(0, w, 2)]
        return sum(1 for c in pts if test(c)) / max(1, len(pts))

    def off(c, ref, d):
        return max(abs(a - b) for a, b in zip(c, ref)) > d
    if share(0, h, lambda c: not off(c, LEFT, 30)) > 0.5:
        return "left"
    if share(0, h, lambda c: not off(c, (255, 255, 255), 6)) > 0.95:
        return "blank"
    if max(share(0, h // 12, lambda c: off(c, ground, 40)), share(h - h // 9, h, lambda c: off(c, ground, 40))) > 0.004:
        return "page"
    if share(h // 3, 2 * h // 3, lambda c: off(c, ground, 40)) > 0.001:
        return "hello"
    return "ground"


# ================================================================== THE SITE'S
# BLOOBY. AT BLOOBY.APP (the owner's yes, Nov 12: "On blooby.app, Draw and
# Flip say 'blooby.' too, at the top and in the first-open hello where the
# blush dot drops, splats and becomes the period. The Skribl demo, and
# skribls.net if they take Pad and Flip, keep 'skribl'."). The demo's app
# hands Skribl the site's brand through Skribl's seam (skribl/brand.py) at the
# addresses SKRIBL_SOCIAL_HOME_HOSTS names (app.py, _site_brand), so this part
# boots the demo's own app with that set, on a port of its own, and reads the
# same server at two addresses: the site's (blooby.localhost, this machine's
# own and a secure context, as blooby.app is) and another (127.0.0.1), which
# must be the demo exactly as it is. verify_hostseams holds the seam itself.
# HELLO_PART=site runs this part alone (calibration).
SITE = make_hello.site_look()
SITE_JSON = os.path.join(ROOT, "social", "static", "brand", "blooby-hello.json")
SITE_KEY = "blooby.hello.v1"
SITE_HOST = "blooby.localhost"
SITE_CSS_TEXT = open(os.path.join(ROOT, "social", "static", "social.css"), encoding="utf-8").read()
PURPLE = make_hello._token(SITE_CSS_TEXT, "brand")          # the site's purple: the word
BLUSH = make_hello._token(SITE_CSS_TEXT, "blooby-blush")    # Blooby's blush: the period
REST_PAGES = 3


def site_pages(d):
    """The period's pages after the word, in the mark's own units from where
    it rests (the skew taken out, as make_hello lays them): for each page,
    its strokes as (x, y, w, h), x and y the middle of the stroke's ink, w and
    h its ink's width and height (the pen's included), biggest first."""
    cs = d["canvasSize"]
    _, s, back = make_hello.placer(cs["cssWidth"], cs["cssHeight"], look=SITE, back=True)
    rest = make_hello.cubic(make_hello.mark(SITE)[1], 6)
    rx, ry = sum(q[0] for q in rest) / len(rest), sum(q[1] for q in rest) / len(rest)
    out = []
    for f in d["frames"][1:]:
        strokes, cur = [], []
        for q in f["strokes"]:
            if q.get("start") and cur:
                strokes.append(cur)
                cur = []
            cur.append(q)
        if cur:
            strokes.append(cur)
        page = []
        for st in strokes:
            pts = [back((q["x"], q["y"])) for q in st]
            pen = st[0]["size"] / s
            x0, x1 = min(q[0] for q in pts), max(q[0] for q in pts)
            y0, y1 = min(q[1] for q in pts), max(q[1] for q in pts)
            page.append((round((x0 + x1) / 2 - rx, 2), round((y0 + y1) / 2 - ry, 2),
                         round(x1 - x0 + pen, 2), round(y1 - y0 + pen, 2)))
        out.append(sorted(page, key=lambda t: -t[2] * t[3]))
    return out


def landing_b(pages):
    """Landing B, read off its pages ([] when it reads right, else what is
    wrong): it falls twice, high then nearer, stretched along the fall; lands
    as a splat on the line with three drops thrown up; spreads, the drops
    flying out; pulls in as they fall back; gathers to one stroke still a
    little wide; rounds up a touch; and rests as the period, round and on its
    place, for the last three."""
    bad = []
    if len(pages) != 7 + REST_PAGES:
        return [f"{len(pages)} pages after the word, where landing B has {7 + REST_PAGES}"]
    one = lambda k: len(pages[k]) == 1
    main = lambda k: pages[k][0]
    drops = lambda k: pages[k][1:]
    spread = lambda k: sum(math.hypot(x, y) for x, y, _, _ in drops(k)) / max(1, len(drops(k)))
    if not (one(0) and one(1) and main(0)[1] < -18 and -16 < main(1)[1] < -6
            and main(0)[3] > 1.4 * main(0)[2] and main(1)[3] > 1.4 * main(1)[2]):
        bad.append(f"the fall {pages[:2]}")
    if not all(len(pages[k]) == 4 and main(k)[2] > 2.5 * main(k)[3] and abs(main(k)[1]) < 1.2
               and all(y < 0.6 for _, y, _, _ in drops(k)) for k in (2, 3, 4)):
        bad.append(f"the splat, three drops above it {pages[2:5]}")
    elif not (main(3)[2] > main(2)[2] > main(4)[2] and spread(3) > spread(2) > spread(4)
              and max(abs(y) for _, y, _, _ in drops(4)) < max(abs(y) for _, y, _, _ in drops(2))):
        bad.append(f"spread, then pulled in {[(main(k)[2], round(spread(k), 2)) for k in (2, 3, 4)]}")
    if not (one(5) and 1.2 < main(5)[2] / main(5)[3] < 2.5 and abs(main(5)[1]) < 0.6):
        bad.append(f"gathered {pages[5]}")
    if not (one(6) and main(6)[3] > main(6)[2] and main(6)[1] < 0):
        bad.append(f"rounded up {pages[6]}")
    if not all(one(k) and 0.8 <= main(k)[2] / main(k)[3] <= 1.25 and math.hypot(*main(k)[:2]) <= NEAR
               and pages[k] == pages[-1] for k in range(7, 7 + REST_PAGES)):
        bad.append(f"at rest {pages[7:]}")
    return bad


print("\nTHE SITE'S HELLO — before any browser")
far, dot_off = on_the_mark(SITE_JSON, SITE)
check(f"the site's hello writes the site's own mark (social/_blooby_mark.html): its line within {NEAR} of the "
      "mark's units of the mark's, its period at rest on the mark's period", far <= NEAR and dot_off <= NEAR,
      f"its line strays {far}, its period is {dot_off} away (make_hello.py --site draws it from the template)")
SITE_HELLO = json.load(open(SITE_JSON))
_inks = [sorted({q["color"] for q in f["strokes"]}) for f in SITE_HELLO["frames"]]
check(f"its word is the site's purple ({PURPLE}) and its period Blooby's blush ({BLUSH}), both read from the "
      "site's own tokens (social.css), one colour each",
      _inks[0] == [PURPLE] and all(k == [BLUSH] for k in _inks[1:]), f"the inks, page by page: {_inks}")
SITE_PAGES = site_pages(SITE_HELLO)
_b = landing_b(SITE_PAGES)
check("landing B, read off the drawing's own pages: the period falls twice, stretched along the fall; lands as "
      "a splat on the line, three drops thrown up; spreads; pulls in as they fall back; gathers; rounds up a "
      "touch; and rests as the period, round and on its place, for the last three", not _b,
      "; ".join(_b) or f"{len(SITE_PAGES)} pages")
SITE_UNDER = SITE_HELLO.get("under") == {"page": 0, "from": 1, "to": len(SITE_HELLO["frames"]) - 1}
check("...the word stays under every page of it, and nothing else is on them (the drawing has no ground)",
      SITE_UNDER and all(f.get("background") is None for f in SITE_HELLO["frames"]),
      f"under {SITE_HELLO.get('under')}")


def free_port():
    import socket
    with socket.socket() as so:
        so.bind(("127.0.0.1", 0))
        return so.getsockname()[1]


def site_server():
    """The demo's own app on a port of its own, its database its own, with the
    site at the top of SITE_HOST: what Render serves at blooby.app and at the
    demo's own name, from one server. Returns (port, stop)."""
    import atexit
    import subprocess
    import tempfile
    tmp = tempfile.mkdtemp(prefix="hello-site-")
    env = dict(os.environ, DATABASE_URL="sqlite:///" + os.path.join(tmp, "site.db"),
               SECRET_KEY="verify-hello-site", SKRIBL_STAND_IN="0", SKRIBL_ALLOW_SQLITE="1",
               SKRIBL_SOCIAL_HOME_HOSTS=SITE_HOST, SKRIBL_RATE_MAX_POSTS="100000")
    for k in ("SKRIBL_SOCIAL", "SKRIBL_URL_PREFIX", "SKRIBL_FORCE_SECURE_COOKIES", "SKRIBL_CSRF_PROTECT"):
        env.pop(k, None)
    subprocess.run([sys.executable, "-c", "from app import app, db; app.app_context().push(); db.create_all()"],
                   cwd=ROOT, env=env, check=True, capture_output=True, timeout=120)
    port = free_port()
    log = open(os.path.join(tmp, "server.log"), "w")
    srv = subprocess.Popen([sys.executable, "-m", "flask", "--app", "app", "run", "--port", str(port), "--no-reload"],
                           cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)

    def stop():
        if srv.poll() is None:
            srv.terminate()
            try:
                srv.wait(10)
            except subprocess.TimeoutExpired:
                srv.kill()
    atexit.register(stop)
    import urllib.request
    for _ in range(160):
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/skribls?limit=1", timeout=2) as r:
                if r.status == 200:
                    return port, stop
        except Exception:  # noqa: BLE001 (not up yet)
            time.sleep(0.25)
    stop()
    raise SystemExit(f"the site's server on {port} did not answer: {open(log.name).read()[-600:]}")


# THE LOCKUP, as the page has it: the mark's box and the slot it stands in,
# the word's and the period's strokes, whether each is what is painted at its
# middle, the lockup's name, and every other thing in the header and the dock
# with where it is (so a pair of pages can say nothing else moved).
HEAD = """() => { const b = document.querySelector('.header .brand, .flip-word');
  const own = b.querySelector('.brand-own'), svg = (own || b).querySelector('svg');
  const R = e => { if (!e) return null; const r = e.getBoundingClientRect(); return [r.left, r.top, r.width, r.height].map(v => +v.toFixed(3)); };
  const word = svg && svg.querySelector('path:not(.brand-period)'), dot = svg && svg.querySelector('.brand-period');
  const hit = e => { if (!e) return null; const r = e.getBoundingClientRect();
    const at = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2); return !!at && (at === svg || svg.contains(at)); };
  const rest = [...document.querySelectorAll('.header .brand, .flip-word, .header button, .header a, .header .brand-tag, #toolBar, .flip-tools, #canvas, #pad')]
    .filter(e => e.getClientRects().length && !e.closest('[hidden]')).map(e => (e.id || e.getAttribute('class')) + ' ' + R(e).join(','));
  return { label: b.getAttribute('aria-label'), title: b.getAttribute('title'), h1: document.querySelector('h1').textContent,
           own: !!own, svg: R(svg), slot: R(own || svg), word: word ? getComputedStyle(word).stroke : null,
           dot: dot ? getComputedStyle(dot).stroke : null, dotBox: R(dot), painted: hit(svg), dotPainted: hit(dot),
           gradient: !!(svg && svg.querySelector('linearGradient')), header: R(document.querySelector('.header')), rest: rest }; }"""


def _near(c, ref, d=60):
    return sum((a - b) ** 2 for a, b in zip(c, ref)) <= d * d


def _pixels(im):
    """Every pixel of `im` as a tuple of its bands, in order."""
    raw, n = im.tobytes(), len(im.getbands())
    return [tuple(raw[i:i + n]) for i in range(0, len(raw), n)]


def blush_of(im):
    """A canvas's picture with only its blush kept (ink on nothing), for _pieces."""
    keep = bytearray()
    for c in _pixels(im):
        keep += bytes(c) if c[3] > 128 and _near(c[:3], _hex(BLUSH), 50) else b"\0\0\0\0"
    return Image.frombytes("RGBA", im.size, bytes(keep))


def mark_pixels(png, dot_box_px):
    """The lockup's slot off the screen's own pixels: the ground (its most
    common colour), the word's ink (the most common colour near the purple)
    and the period's (near the blush), how many of each, and whether the
    blush lies on the period's own stroke (its box, a pen either side)."""
    im = _png(png).convert("RGB")
    px = _pixels(im)
    from collections import Counter
    ground = Counter(c for c in px if not _near(c, _hex(PURPLE), 90) and not _near(c, _hex(BLUSH), 90)).most_common(1)[0][0]
    word = [c for c in px if _near(c, _hex(PURPLE))]
    blush = [(i % im.width, i // im.width) for i, c in enumerate(px) if _near(c, _hex(BLUSH), 50)]
    ink = Counter(word).most_common(1)[0][0] if word else None
    x0, y0, x1, y1 = dot_box_px
    on = sum(1 for x, y in blush if x0 <= x <= x1 and y0 <= y <= y1)
    return {"ground": ground, "ink": ink, "word": len(word), "blush": len(blush), "on": on}


# THE HELLO, READ ON EVERY ANIMATION FRAME the screen makes, the way a replay
# is read (verify_glide), from the moment it is on until it is gone: the
# player's clock; the word's ink (its purple, over the whole canvas read a
# quarter size); the period's blush in the box it moves in (its middle and
# its ink's width and height, in the drawing's own pixels); and the way out
# (the ground's opacity, the ink's rise and its edge). Read off the canvas's
# pixels, not the clock: a probe that reads the clock agrees with the bug.
GLIDE = """(r) => new Promise(res => {
  const h = document.getElementById('skriblHello'), c = h && h.querySelector('canvas');
  const p = h && window.SkriblInline && SkriblInline.players().find(x => x.el && h.contains(x.el));
  if (!c || !p) { res(null); return; }
  const k = c.width / r.cssW, box = h.querySelector('.skribl-inline');
  const x0 = Math.max(0, Math.floor(r.box[0] * k)), y0 = Math.max(0, Math.floor(r.box[1] * k));
  const w = Math.min(c.width - x0, Math.ceil((r.box[2] - r.box[0]) * k)), hh = Math.min(c.height - y0, Math.ceil((r.box[3] - r.box[1]) * k));
  const sw = Math.ceil(c.width / 4), sh = Math.ceil(c.height / 4), sm = document.createElement('canvas');
  sm.width = sw; sm.height = sh;
  const sx = sm.getContext('2d', { willReadFrequently: true }), cx = c.getContext('2d');
  const out = [];
  (function f() {
    const t = performance.now();
    if (!document.getElementById('skriblHello')) { out.push(['gone', t]); res(out); return; }
    sx.clearRect(0, 0, sw, sh); sx.drawImage(c, 0, 0, sw, sh);
    const a = sx.getImageData(0, 0, sw, sh).data; let word = 0;
    for (let i = 0; i < a.length; i += 4) if (a[i + 3] > 100 && a[i + 2] > 180 && a[i] < 200) word++;
    const d = cx.getImageData(x0, y0, w, hh).data;
    let n = 0, mnx = 1e9, mxx = -1, mny = 1e9, mxy = -1;
    for (let y = 0, i = 0; y < hh; y++) for (let x = 0; x < w; x++, i += 4)
      if (d[i + 3] > 128 && d[i] > 200 && d[i + 1] < 170 && d[i + 2] > 90 && d[i + 2] < 210) {
        n++; if (x < mnx) mnx = x; if (x > mxx) mxx = x; if (y < mny) mny = y; if (y > mxy) mxy = y; }
    const bs = getComputedStyle(box), m = /matrix\\(([^)]+)\\)/.exec(bs.transform);
    out.push([t, Math.round(p.state().elapsedMs), word, n,
              n ? +(((mnx + mxx) / 2 + x0) / k).toFixed(2) : null, n ? +(((mny + mxy) / 2 + y0) / k).toFixed(2) : null,
              n ? +((mxx - mnx + 1) / k).toFixed(2) : 0, n ? +((mxy - mny + 1) / k).toFixed(2) : 0,
              +getComputedStyle(h).opacity, m ? +m[1].split(',')[5] : 0, parseFloat(bs.maskPosition || bs.webkitMaskPosition) || 0,
              h.classList.contains('is-leaving')]);
    requestAnimationFrame(f);
  })(); })"""


def page_signs(d):
    """Each of the period's pages as the GLIDE record reads one: the middle of
    its blush and its width and height, in the drawing's own pixels."""
    out = []
    for f in d["frames"][1:]:
        s = f["strokes"]
        r = [(q["x"], q["y"], q["size"] / 2) for q in s]
        x0, x1 = min(x - h for x, _, h in r), max(x + h for x, _, h in r)
        y0, y1 = min(y - h for _, y, h in r), max(y + h for _, y, h in r)
        out.append(((x0 + x1) / 2, (y0 + y1) / 2, x1 - x0, y1 - y0))
    return out


def glide_verdict(rec, word_ms, signs):
    """(ok, frozen, parts) for a GLIDE record. Each part is read where it
    moves, and says what it saw:
      word  the word's ink grows point after point: on most frames while the
            clock moves, never still for more than three, and never more than
            a tenth of the word in one frame;
      dot   the period's pages, each frame read as the page it looks most like:
            in order, none skipped, every one seen, none held past one and a
            half times its length and a frame;
      out   the ground fades and the ink rises through the middle on several
            frames, neither by more than a third in a frame of ordinary length.
    Frozen: failed, but every jump came across a frame held past
    HELLO_STALL_MS (the page's thread stalled on a busy runner)."""
    rows = [r for r in rec if r[0] != "gone"]
    gone = rec[-1][1] if rec and rec[-1][0] == "gone" else None
    stalls = [(b[0] - a[0]) for a, b in zip(rows, rows[1:])]
    longest = round(max(stalls, default=0))
    # The word: frames whose clock is inside the word's own time.
    wf = [r for r in rows if not r[11] and 0 < r[1] < word_ms - 30]
    final = max((r[2] for r in rows if not r[11]), default=0)
    moves, holds, run, big, cut = 0, 0, 0, 0.0, False
    for a, b in zip(wf, wf[1:]):
        if b[1] <= a[1]:
            continue
        step = (b[2] - a[2]) / max(1, final)
        big = max(big, step)
        if step > 0.10 and b[0] - a[0] <= HELLO_STALL_MS:
            cut = True
        if b[2] > a[2]:
            moves += 1
            run = 0
        else:
            run += 1
            holds = max(holds, run)
    pairs = sum(1 for a, b in zip(wf, wf[1:]) if b[1] > a[1])
    word = {"frames": len(wf), "moved": round(moves / max(1, pairs), 2), "hold": holds, "largest": round(big, 3)}
    word_ok = len(wf) >= 20 and word["moved"] >= 0.7 and holds <= 3 and big <= 0.10
    # The period: every frame from the word's end until it leaves, as the
    # nearest of its pages (the last three, at rest, are one look).
    df = [r for r in rows if not r[11] and r[1] >= word_ms and r[3] > 0]
    n_rest = REST_PAGES
    look = lambda r: min(range(len(signs)), key=lambda k: math.hypot(r[4] - signs[k][0], r[5] - signs[k][1])
                         + abs(r[6] - signs[k][2]) + abs(r[7] - signs[k][3]))
    seq = [min(look(r), len(signs) - n_rest) for r in df]
    runs = []
    for r, k in zip(df, seq):
        if runs and runs[-1][0] == k:
            runs[-1][2] = r[0]
        else:
            runs.append([k, r[0], r[0]])
    order = [k for k, _, _ in runs]
    page_ms = 1000 / 12
    held = [(k, round(b - a)) for k, a, b in runs[:-1] if b - a > 1.5 * page_ms + 17]
    skip_at = [(a, b) for a, b in zip(order, order[1:]) if b != a + 1]
    jump_stalled = all(any(r2[0] - r1[0] > HELLO_STALL_MS for r1, r2 in zip(df, df[1:]) if r1[0] <= t <= r2[0])
                       for t in [runs[i + 1][1] for i, (a, b) in enumerate(zip(order, order[1:])) if b != a + 1])
    held_stalled = all(any(r2[0] - r1[0] > HELLO_STALL_MS for r1, r2 in zip(df, df[1:]) if a <= r1[0] and r2[0] <= b)
                       for k, a, b in runs[:-1] if b - a > 1.5 * page_ms + 17)
    dot = {"pages": order, "held": held, "skips": skip_at}
    dot_ok = order == list(range(len(signs) - n_rest + 1)) and not held
    # The way out: from the frame before it leaves to the frame it is gone.
    first = next((i for i, r in enumerate(rows) if r[11]), None)
    out = {"frames": 0}
    out_ok = False
    if first is not None and gone is not None:
        tail = rows[max(0, first - 1):]
        o = [(r[8], r[0]) for r in tail] + [(0.0, gone)]
        t0 = rows[max(0, first - 1)][9]
        rise = [(r[9], r[0]) for r in tail]
        end = min(v for v, _ in rise) if rise else 0

        def steps(vals, lo, hi):
            span = (hi - lo) or 1
            mid = sum(1 for v, _ in vals if lo + 0.05 * span < v < hi - 0.05 * span)
            big = max((abs(b[0] - a[0]) / abs(span) for a, b in zip(vals, vals[1:])), default=1.0)
            cut = any(abs(b[0] - a[0]) / abs(span) > 0.34 and b[1] - a[1] <= HELLO_STALL_MS for a, b in zip(vals, vals[1:]))
            return mid, round(big, 2), cut
        fade = steps(o, 0.0, 1.0)
        lift = steps(rise, end, t0) if end < t0 - 0.5 else (0, 1.0, True)
        out = {"frames": len(tail), "fade": fade, "lift": lift}
        out_ok = fade[0] >= 5 and fade[1] <= 0.34 and lift[0] >= 5 and lift[1] <= 0.34
        cut = cut or fade[2] or lift[2]
    ok = word_ok and dot_ok and out_ok
    frozen = not ok and longest > HELLO_STALL_MS and not cut and jump_stalled and held_stalled
    return ok, frozen, {"word": word, "dot": dot, "out": out, "longest frame": longest}


def site_section(p):
    print("\nBLOOBY. AT AN ADDRESS SKRIBL_SOCIAL_HOME_HOSTS NAMES — the site's name on the editors, and its hello")
    port, stop = site_server()
    at_site, at_other = f"http://{SITE_HOST}:{port}", f"http://127.0.0.1:{port}"
    bb = p.chromium.launch(args=[f"--host-resolver-rules=MAP {SITE_HOST} 127.0.0.1"])
    try:
        _site_rows(bb, at_site, at_other)
    finally:
        bb.close()
        stop()


def _site_rows(bb, at_site, at_other):
    # Warm the new server (it strips its scripts on first asking), both
    # editors at both addresses.
    w = bb.new_context(**PHONE)
    for base in (at_site, at_other):
        for route in ("/skribl-pad", "/flip"):
            q = w.new_page()
            q.goto(base + route, wait_until="load")
            q.close()
    w.close()

    # THE LOCKUP: each editor, phone and desk, light and dark, at the site's
    # address and at the other, read as the page has it and as it is painted.
    heads = []
    for dev, opts in (("phone", PHONE), ("desk", DESK)):
        for scheme in ("light", "dark"):
            c = bb.new_context(color_scheme=scheme, **opts)
            for route, mode in (("/skribl-pad", "Pad"), ("/flip", "Flip")):
                pair = {}
                for name, base in (("site", at_site), ("other", at_other)):
                    q = c.new_page()
                    q.goto(base + route, wait_until="load")
                    q.wait_for_timeout(600)
                    h = q.evaluate(HEAD)
                    if name == "site" and h["slot"]:
                        x, y, ww, hh = h["slot"]
                        dpr = q.evaluate("() => devicePixelRatio")
                        png = q.screenshot(clip={"x": x, "y": y - 2, "width": ww, "height": hh + 8}, scale="device")
                        dx, dy, dw, dh = h["dotBox"] or (0, 0, 0, 0)
                        pen = 2.3 * h["svg"][3] / 34
                        h["px"] = mark_pixels(png, [round((dx - pen - x) * dpr), round((dy - pen - y + 2) * dpr),
                                                    round((dx + dw + pen - x) * dpr), round((dy + dh + pen - y + 2) * dpr)])
                    pair[name] = h
                    q.close()
                heads.append((dev, scheme, mode, pair))
            c.close()
    bad, said = [], []
    for dev, scheme, mode, pr in heads:
        s_, o_ = pr["site"], pr["other"]
        px = s_.get("px") or {}
        g = px.get("ground")
        word_c = contrast(px["ink"], g) if px.get("ink") and g else 0
        blush_c = contrast(_hex(BLUSH), g) if g else 0
        said.append(f"{dev} {scheme} {mode}: the word {word_c:.2f}:1, the period {blush_c:.2f}:1")
        ok = (s_["own"] and not s_["gradient"] and s_["painted"] and s_["dotPainted"]
              and s_["word"] == "rgb(%d, %d, %d)" % _hex(PURPLE) and s_["dot"] == "rgb(%d, %d, %d)" % _hex(BLUSH)
              and px.get("word", 0) > 30 and px.get("on", 0) >= 4 and px.get("blush", 0) - px.get("on", 0) <= 2
              and word_c >= 3.0)
        if not ok:
            bad.append(f"{dev} {scheme} {mode}: {json.dumps({k: s_[k] for k in ('own', 'gradient', 'painted', 'dotPainted', 'word', 'dot')})} {px}")
    check("at the site's address the Pad and Flip wear blooby., painted: the word in Skribl's purple, the site's "
          f"({PURPLE}), at 3:1 or more on its ground, and the period in Blooby's blush ({BLUSH}) on its own stroke; "
          "phone and desk, light and dark",
          heads and not bad, "; ".join(bad[:3]) or "; ".join(said))
    bad = []
    for dev, scheme, mode, pr in heads:
        s_, o_ = pr["site"], pr["other"]
        sx, sy, sw, sh = s_["slot"]
        ox, oy, ow, oh = o_["svg"]
        vx, vy, vw, vh = s_["svg"]
        line = (abs(sx - ox) < 0.02 and abs(sy - oy) < 0.02 and abs(sw - ow) < 0.02 and abs(sh - oh) < 0.02
                and abs(vy - oy) < 0.02 and abs(vh - oh * 34 / 30) < 0.05 and abs(vw / vh - 57 / 34) < 0.01)
        if not (line and s_["rest"] == o_["rest"] and s_["header"] == o_["header"]):
            moved = sorted(set(s_["rest"]) ^ set(o_["rest"]))
            bad.append(f"{dev} {scheme} {mode}: the slot {s_['slot']} for skribl's {o_['svg']}, the mark {s_['svg']}; "
                       f"header {s_['header']} / {o_['header']}; moved {moved[:4]}")
    check("...the line where skribl's was: the slot is the signature's own box, the mark at the same scale and "
          "top with its y's tail hung below (34 units for 30), and nothing else in the header or the dock moved",
          heads and not bad, "; ".join(bad[:3]) or f"{len(heads)} pairs of pages")
    bad = [f"{dev} {mode}: {pr['site']['label']!r}, {pr['site']['h1']!r}; other {pr['other']['label']!r}"
           for dev, scheme, mode, pr in heads
           if not (pr["site"]["label"] == pr["site"]["h1"] == f"Blooby {mode}"
                   and pr["other"]["label"] == pr["other"]["h1"] == f"Skribl {mode}")]
    check("...named Blooby there ('Blooby Pad', 'Blooby Flip', the lockup and the page's heading)",
          heads and not bad, "; ".join(bad[:3]))
    bad = [f"{dev} {scheme} {mode}" for dev, scheme, mode, pr in heads
           if not (not pr["other"]["own"] and pr["other"]["gradient"] and pr["other"]["painted"])]
    check("at any other address on the same server, the editors wear the skribl mark, as today",
          heads and not bad, ", ".join(bad))

    # THE HELLO AT THE SITE'S ADDRESS, the first open on a phone, light and
    # dark: the site's own drawing on the page's own ground, sharp, its word
    # at 3:1 or more there and its period's contrast said (the owner's pick).
    firsts = []
    for scheme in ("dark", "light"):
        c = bb.new_context(color_scheme=scheme, **PHONE)
        c.add_init_script(FORCE)
        got = []
        q = c.new_page()
        q.on("request", lambda r, got=got: got.append(r.url.split("?")[0]) if "/brand/" in r.url and "hello" in r.url else None)
        q.goto(at_site + "/skribl-pad", wait_until="load")
        s, ms = _until(q, lambda s: s["painted"] and s["on"], 8000)
        who = q.evaluate("""() => { const h = document.getElementById('skriblHello');
            return { label: h && h.getAttribute('aria-label'), key: h && h.getAttribute('data-hello-key'),
                     site: localStorage.getItem('%s'), skribl: localStorage.getItem('%s') }; }""" % (SITE_KEY, KEY))
        ground = _hex(s["ground"]) if s["ground"] else None
        sharp, why = _sharp(s)
        firsts.append((scheme, ms, got, who, ground, s, sharp, why))
        if scheme == "light":
            break
        c.close()
    bad = []
    for scheme, ms_, got_, who_, ground, s_, sharp, why in firsts:
        if not (ms_ is not None and got_ == [at_site + "/social/static/brand/blooby-hello.json"]
                and who_["label"] == "Blooby's signature" and who_["key"] == SITE_KEY and who_["site"] == "1"
                and who_["skribl"] is None):
            bad.append(f"{scheme}: came after {ms_} ms; fetched {got_}; {who_}")
    check("the first open there says the site's hello: its own drawing (the site's file, and Skribl's not fetched), "
          "named Blooby's signature, remembered by its own key with Skribl's left alone", not bad, "; ".join(bad))
    # The inks the drawing carries (the word's page, the period's pages), so
    # a fainter drawing reads fainter: not the tokens it was meant to use.
    word_inks = {q_["color"] for q_ in SITE_HELLO["frames"][0]["strokes"]}
    dot_inks = {q_["color"] for f_ in SITE_HELLO["frames"][1:] for q_ in f_["strokes"]}
    bad, said = [], []
    for scheme, ms_, got_, who_, ground, s_, sharp, why in firsts:
        wc = min(contrast(_hex(k_), ground) for k_ in word_inks) if ground else 0
        pc = min(contrast(_hex(k_), ground) for k_ in dot_inks) if ground else 0
        said.append(f"{scheme}: the word {wc:.2f}:1, the period {pc:.2f}:1 on {s_['ground']}")
        if not (ms_ is not None and s_["bg"] and _rgb(s_["bg"]) == ground and s_["image"] == "none"
                and s_["corner"] == 0 and wc >= 3.0 and sharp):
            bad.append(f"{scheme}: painted {s_['bg']} {s_['image']}, corner {s_['corner']}, the word {wc:.2f}:1; {why}")
    check("...on the page's own ground, light and dark, through a drawing with no ground of its own, its word at 3:1 "
          "or more there (the blush period said, the owner's pick), and sharp: its box on whole screen pixels",
          not bad, "; ".join(bad) or "; ".join(said))
    H = q.evaluate("(f) => SkriblHold.pageMs(f, 12)", SITE_HELLO["frames"][0]) if ms is not None else 0
    late = q.evaluate(WORD, H - 300) if ms is not None else {}
    t0 = time.time()
    while ms is not None and "png" not in late and time.time() - t0 < 4:
        q.wait_for_timeout(30)
        late = q.evaluate(WORD, H - 300)
    im = _png(late["png"]) if "png" in late else None
    blush_px = sum(1 for c_ in _pixels(im) if c_[3] > 128 and _near(c_[:3], _hex(BLUSH), 50)) if im else -1
    pieces = _pieces(im)[1] if im else []
    check(f"...it writes blooby first ({H} ms), in one stroke of ink, and no blush until the word is written",
          im is not None and late["el"] < H and len(pieces) == 1 and blush_px == 0,
          f"at {late.get('el')} ms: {len(pieces)} piece(s) of ink, {blush_px} blush pixels")
    c.close()

    # IT GLIDES, read on every frame from the moment it is on until it is
    # gone (GLIDE, glide_verdict). A frozen take, every jump across a frame
    # the page's thread held, is taken again, at most twice.
    signs = page_signs(SITE_HELLO)
    allx = [v for sg in signs for v in (sg[0] - sg[2] / 2, sg[0] + sg[2] / 2)]
    ally = [v for sg in signs for v in (sg[1] - sg[3] / 2, sg[1] + sg[3] / 2)]
    region = {"cssW": SITE_HELLO["canvasSize"]["cssWidth"],
              "box": [min(allx) - 12, min(ally) - 12, max(allx) + 12, max(ally) + 12]}
    takes, verdict = 0, (False, True, {})
    while takes < 3 and (takes == 0 or verdict[1]):
        c = bb.new_context(**PHONE)
        c.add_init_script(FORCE)
        q = c.new_page()
        q.goto(at_site + "/skribl-pad", wait_until="load")
        s, ms = _until(q, lambda s: s["painted"] and s["on"], 8000)
        rec = q.evaluate(GLIDE, region) if ms is not None else None
        verdict = glide_verdict(rec or [], H, signs)
        takes += 1
        c.close()
    ok, frozen, parts = verdict
    check("...and it glides, read on every frame the screen makes: the word written point after point, the "
          "period's pages in order (none skipped, none held), and the way out (the ground fading, the ink "
          "rising) through the middle on several frames", ok,
          json.dumps(parts) + (f"; taken {takes} times, a frame having frozen it" if takes > 1 else ""))

    # WHERE IT LANDS, AND THE SPLAT, as the screen paints them: held on each
    # page (the player's seek), read off the canvas's own pixels.
    c = bb.new_context(**PHONE)
    c.add_init_script(FORCE)
    q = c.new_page()
    q.goto(at_site + "/skribl-pad", wait_until="load")
    s, ms = _until(q, lambda s: s["painted"] and s["on"], 8000)
    SEEK = """(t) => { const h = document.getElementById('skriblHello'), c = h && h.querySelector('canvas');
        const p = h && SkriblInline.players().find(q => q.el && h.contains(q.el));
        if (!p) return null; p.seek(t); return [c.toDataURL('image/png'), c.width]; }"""
    looks = {}
    place, s_unit = make_hello.placer(SITE_HELLO["canvasSize"]["cssWidth"], SITE_HELLO["canvasSize"]["cssHeight"], look=SITE)
    rest = make_hello.cubic(make_hello.mark(SITE)[1], 6)
    want = place((sum(q_[0] for q_ in rest) / len(rest), sum(q_[1] for q_ in rest) / len(rest)))
    for name, page in (("splat", 3), ("spread", 4), ("gathered", 6), ("rest", None)):
        got_ = q.evaluate(SEEK, H + (page - 0.5) * 1000 / 12 if page else 1e9) if ms is not None else None
        if not got_:
            looks[name] = None
            continue
        im = _png(got_[0])
        k = got_[1] / SITE_HELLO["canvasSize"]["cssWidth"]
        ps = _pieces(blush_of(im), least=8)[1]
        main_ = ps[0] if ps else None
        looks[name] = None if not main_ else {
            "pieces": len(ps), "wide": round((main_[4] - main_[2] + 1) / (main_[5] - main_[3] + 1), 2),
            "off": round(math.hypot((main_[2] + main_[4]) / 2 / k - want[0], (main_[3] + main_[5]) / 2 / k - want[1]) / s_unit, 3)}
    c.close()
    L = looks
    check(f"...the period lands where the period sits: at rest, one round dot on the mark's period, within {NEAR} of "
          "the mark's units (read off the canvas's pixels)",
          L.get("rest") is not None and L["rest"]["pieces"] == 1 and 0.8 <= L["rest"]["wide"] <= 1.25
          and L["rest"]["off"] <= NEAR, str(L.get("rest")))
    check("...and it splats a little and reforms, as the screen paints it: on landing a splat with three drops, "
          "flatter still as it spreads, then gathered to one",
          all(L.get(k_) is not None for k_ in ("splat", "spread", "gathered"))
          and L["splat"]["pieces"] == 4 and L["splat"]["wide"] > 2.5 and L["spread"]["pieces"] == 4
          and L["spread"]["wide"] > L["splat"]["wide"] and L["gathered"]["pieces"] == 1 and L["gathered"]["wide"] > 1.2,
          str({k_: L.get(k_) for k_ in ("splat", "spread", "gathered")}))

    # ONCE, BY ITS OWN KEY: somebody who met Skribl's hello (its key set in
    # this browser) still meets the site's, a tap skips it, and the next
    # editor at the same address does not show it again.
    c = bb.new_context(**PHONE)
    c.add_init_script(FORCE)
    c.add_init_script("try { localStorage.setItem('%s', '1'); } catch (e) {}" % KEY)
    q = c.new_page()
    q.goto(at_site + "/skribl-pad", wait_until="load")
    s, ms = _until(q, lambda s: s["painted"] and s["on"] and s["el"] >= 400, 8000)
    q.touchscreen.tap(201, 437)
    s2, ms2 = _until(q, lambda s: not s["here"], 1500)
    q.goto(at_site + "/flip", wait_until="load")
    q.wait_for_timeout(2500)
    flip = q.evaluate(ST, False)
    seen = q.evaluate("() => localStorage.getItem('%s')" % SITE_KEY)
    check("once, by its own key: somebody who met Skribl's hello still meets the site's, a tap skips it, and Flip "
          "at the same address does not show it again",
          ms is not None and ms2 is not None and ms2 <= 1400 and not flip["painted"] and flip["canvasThere"] and seen == "1",
          f"came after {ms} ms, gone {ms2} ms after the tap; Flip: hello painted {flip['painted']}; seen {seen}")
    c.close()

    # REDUCE MOTION at the site's address: it keeps still, the finished
    # blooby. with its period in place, and it just fades, in and out.
    takes, fv, still = 0, (False, True, None, None, 0), None
    while takes < 3 and (takes == 0 or fv[1]):
        c = bb.new_context(reduced_motion="reduce", **PHONE)
        c.add_init_script(FORCE)
        c.add_init_script(FADE_REC)
        q = c.new_page()
        q.goto(at_site + "/skribl-pad", wait_until="load")
        s, ms = _until(q, lambda s: s["painted"] and s["on"], 8000)
        if ms is not None and still is None:
            im = _png(q.evaluate(BITMAP))
            k = im.width / SITE_HELLO["canvasSize"]["cssWidth"] if im else 1
            ps = _pieces(blush_of(im), least=8)[1]
            word_px = sum(1 for c_ in _pixels(im)[::7] if c_[3] > 128 and _near(c_[:3], _hex(PURPLE)))
            still = {"word": word_px, "pieces": len(ps),
                     "off": round(math.hypot((ps[0][2] + ps[0][4]) / 2 / k - want[0], (ps[0][3] + ps[0][5]) / 2 / k - want[1])
                                  / s_unit, 3) if ps else None}
        states = set()
        t0 = time.time()
        while time.time() - t0 < 1.0:
            states.add(q.evaluate(ST, False)["state"])
            q.wait_for_timeout(100)
        _until(q, lambda s: not s["here"], 12000)
        fv = fade_verdict(*read_fade(q))
        takes += 1
        c.close()
    ok, frozen, come, go, n = fv
    check("Reduce Motion there: it keeps still, the finished blooby. with its period in place (never playing), "
          "and it just fades, in and out, never there or gone in one frame",
          still is not None and still["word"] > 50 and still["pieces"] == 1 and still["off"] is not None
          and still["off"] <= NEAR and "playing" not in states and ok,
          f"the still: {still}; states {sorted(map(str, states))}; coming in {come}, going {go}, {n} frames"
          + (f"; taken {takes} times, a frame having frozen the fade" if takes > 1 else ""))

    # AT ANY OTHER ADDRESS, the same server's hello is Skribl's: its own file
    # (the one the rows above hold, the bounce and the wink), its own key.
    c = bb.new_context(**PHONE)
    c.add_init_script(FORCE)
    bodies = []
    q = c.new_page()
    q.on("response", lambda r: bodies.append((r.url.split("?")[0], r)) if "/brand/" in r.url and "hello" in r.url else None)
    q.goto(at_other + "/skribl-pad", wait_until="load")
    s, ms = _until(q, lambda s: s["painted"] and s["on"], 8000)
    seen = q.evaluate("() => [localStorage.getItem('%s'), localStorage.getItem('%s')]" % (KEY, SITE_KEY))
    same = [json.loads(r.body()) == HELLO for _, r in bodies] if ms is not None else []
    check("...and its hello there is Skribl's, as today: Skribl's own drawing (the bounce and the wink held above), "
          "remembered by Skribl's key",
          ms is not None and [u for u, _ in bodies] == [at_other + "/static/skribl/brand/hello.json"] and same == [True]
          and seen == ["1", None], f"came after {ms} ms; fetched {[u for u, _ in bodies]}, Skribl's own: {same}; keys {seen}")
    c.close()

    # AND THE DEMO'S OWN PAGES ARE BYTE FOR BYTE AS THEY WERE: the Pad and
    # Flip at any other address are what the same app serves with no site
    # address named at all, read through the app's own test client.
    import subprocess
    import tempfile
    probe = r'''
import json, re, sys
from app import app
c = app.test_client()
out = {}
for h in ("skribl-live-demo.onrender.com", "127.0.0.1:5001", "blooby.example"):
    for r in ("/skribl-pad", "/flip", "/skribl-pad?compose=1", "/flip?compose=1"):
        t = c.get(r, base_url="https://" + h).get_data(as_text=True)
        t = re.sub(r'nonce="[^"]*"', "", t)
        out[h + r] = re.sub(r'(data-skribl-csrf|data-csrf)="[^"]*"', "", t)
print("RESULT " + json.dumps(out))
'''
    got = {}
    for name, homes in (("named", "blooby.example"), ("none", "")):
        with tempfile.TemporaryDirectory() as tmp:
            env = dict(os.environ, DATABASE_URL="sqlite:///" + os.path.join(tmp, "p.db"), SKRIBL_STAND_IN="0",
                       SECRET_KEY="verify-hello-pages", SKRIBL_ALLOW_SQLITE="1", SKRIBL_SOCIAL_HOME_HOSTS=homes)
            env.pop("SKRIBL_CSRF_PROTECT", None)
            r = subprocess.run([sys.executable, "-c", probe], cwd=ROOT, env=env, capture_output=True, text=True, timeout=180)
            line = next((ln for ln in r.stdout.splitlines() if ln.startswith("RESULT ")), None)
            got[name] = json.loads(line[7:]) if line else {}
    keys = [k for k in got.get("none", {}) if not k.startswith("blooby.example")]
    differ = [k for k in keys if got["named"].get(k) != got["none"].get(k)]
    branded = [k for k in got.get("named", {}) if k.startswith("blooby.example") and "brand-own" in got["named"][k]
               and got["named"][k] != got["none"].get(k)]
    check("the demo's own pages, at any address but the site's, are byte for byte what the app serves with no site "
          "address named (the Pad and Flip, on their own and in a composer); at the site's, the site's brand",
          keys and not differ and len(branded) == 4, f"differ: {differ}; branded at the site's: {len(branded)} of 4")


if os.environ.get("HELLO_PART") == "site":
    with sync_playwright() as p:
        site_section(p)
    summarise_and_exit()


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

    # ...AND THE TAP PRESSES NOTHING UNDER IT (found building the hello's
    # mock). It lets go of the pointer as it starts to leave, and a phone
    # makes a tap's click where the finger lifts, on whatever is under it: a
    # tap over the menu at the top right skipped the hello and opened the
    # menu, on the Pad and on Flip. A mouse's click never reached it.
    shut = []
    for route, btn in (("/skribl-pad", "menuBtn"), ("/flip", "moreBtn")):
        c = b.new_context(**PHONE)
        q = _open(c, route)
        s, ms = _until(q, lambda s: s["painted"] and s["on"] and s["el"] >= 500, 8000)
        x, y = q.evaluate("(id) => { const r = document.getElementById(id).getBoundingClientRect(); "
                          "return [r.left + r.width / 2, r.top + r.height / 2]; }", btn)
        q.touchscreen.tap(x, y)
        s2, ms2 = _until(q, lambda s: not s["here"], 1500)
        q.wait_for_timeout(300)
        shut.append((route, ms, ms2, q.evaluate("(id) => document.getElementById(id).getAttribute('aria-expanded')", btn)))
        c.close()
    check("...and that tap presses nothing under it: tapped over the menu, the hello goes and the menu stays shut",
          all(ms is not None and ms2 is not None and was == "false" for _, ms, ms2, was in shut),
          "; ".join(f"{r}: came after {ms} ms, gone {ms2} ms after the tap, the menu open: {was}" for r, ms, ms2, was in shut))

    # ...and the wink as the screen paints it: held on its shut page, the dot
    # is a line; at the end, a dot again.
    c = b.new_context(**PHONE)
    q = _open(c, "/skribl-pad")
    s, ms = _until(q, lambda s: s["painted"] and s["on"], 8000)
    SEEK = """(t) => { const h = document.getElementById('skriblHello'), c = h && h.querySelector('canvas');
        const p = h && SkriblInline.players().find(q => q.el && h.contains(q.el));
        if (!p) return null; p.seek(t); return c.toDataURL('image/png'); }"""
    word_ms = q.evaluate("(f) => SkriblHold.pageMs(f, 12)", HELLO["frames"][0]) if ms is not None else 0
    shapes = []
    for t in ((word_ms + WINK * 1000 / 12 + 40) if WINK is not None else 0, 1e9):
        im = _png(q.evaluate(SEEK, t)) if ms is not None else None
        pieces = _pieces(im)[1] if im else []
        dot = pieces[1] if len(pieces) == 2 else None
        shapes.append(round((dot[5] - dot[3] + 1) / (dot[4] - dot[2] + 1), 2) if dot else None)
    c.close()
    check("...and the screen paints it so: held on that page the dot is a line, and at the end a dot again",
          shapes[0] is not None and shapes[0] < 0.35 and shapes[1] is not None and 0.8 <= shapes[1] <= 1.25,
          f"the dot's height against its width on the canvas: shut {shapes[0]}, at the end {shapes[1]}")

    # Reduce Motion: a still hello, the finished mark with its dot in place, then it just fades.
    c = b.new_context(reduced_motion="reduce", **PHONE)
    # Its opacity on every frame the screen makes, with whether it is on and
    # whether it is leaving and when the frame came, until it is gone: the
    # fade is read, not its class.
    c.add_init_script(FADE_REC)
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
    # THE OWNER'S iPHONE, after v328: "when reduce motion is on the opening
    # skribl doesn't fade away, it just disappears". Both of the stylesheet's
    # Reduce Motion rules take every transition to nothing, the hello's fade
    # with them, so it went in one frame. Read off every frame: coming in and
    # going, it passes through the middle on several frames, and no one frame
    # moves it more than a third of the way (the record: read_fade).
    ok, frozen, come, go, n = fade_verdict(*read_fade(q))
    # A FROZEN TAKE IS TAKEN AGAIN, at most twice: main after #865 read the
    # fade coming in with one step of 0.44, the page's thread held past three
    # frames on a busy runner. Only a take whose every step over a third came
    # across such a frame is taken again; a cut in a frame of ordinary length
    # (the fade gone, as on the owner's iPhone) stays red at once.
    takes = 1
    while frozen and takes < 3:
        c.close()
        c = b.new_context(reduced_motion="reduce", **PHONE)
        c.add_init_script(FADE_REC)
        q = _open(c, "/skribl-pad")
        _until(q, lambda s: s["painted"] and s["on"], 8000)
        _until(q, lambda s: not s["here"], 12000)
        ok, frozen, come, go, n = fade_verdict(*read_fade(q))
        takes += 1
    check("Reduce Motion: the hello fades in and fades away, never there or gone in one frame "
          "(the owner's iPhone: 'it just disappears')", ok,
          f"coming in: {come[0]} frames between, the largest step {come[1]}, the longest frame {come[3]} ms; "
          f"going: {go[0]} frames between, the largest step {go[1]}, the longest frame {go[3]} ms; {n} frames read"
          + (f"; taken {takes} times, a frame having frozen the fade" if takes > 1 else ""))
    c.close()

    # A slow line: the player held for 5 s, past its 4. The page's load waits
    # for that script, so this open waits only for the page's own parse.
    c = b.new_context(**PHONE)
    c.add_init_script(FORCE)
    # Every change to the ground the head laid, on the page's clock.
    c.add_init_script("""window.__cover = []; new MutationObserver(() => window.__cover.push(
        [document.documentElement.getAttribute('data-hello-cover'), Math.round(performance.now())]))
      .observe(document, { attributes: true, attributeFilter: ['data-hello-cover'], subtree: true });""")
    held_js = []
    c.route("**/inlineplayer.js*", lambda r: held_js.append(r))
    q = c.new_page()
    q.goto(BASE + "/skribl-pad", wait_until="domcontentloaded")
    q.wait_for_timeout(5000)
    s = q.evaluate(ST, False)
    cover = q.evaluate("() => window.__cover")
    ready = q.evaluate("() => Math.round(performance.getEntriesByType('navigation')[0].domContentLoadedEventStart)")
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
    # ...and its ground holds the page only while the page's own scripts come,
    # as an app's launch screen does: once they are done it waits a moment for
    # the hello's files, then fades, never the 4 s the hello waits for them.
    t = {k: v for k, v in reversed(cover)}
    lift, gone = t.get("lift"), t.get(None)
    check("...its ground holds the page while the page's own scripts come, then fades once they are done "
          "(within 1.5 s), not when the hello gives up",
          [k for k, _ in cover] == ["up", "lift", None] and lift is not None and ready <= lift <= ready + 1500
          and gone is not None and 300 <= gone - lift <= 1500,
          f"the ground: {cover}; the page ready at {ready} ms")
    c.close()

    # IF lib/hello.js NEVER RUNS (refused here), the head's ground goes by
    # itself: at 8 s, and the canvas is there.
    c = b.new_context(**PHONE)
    c.add_init_script(FORCE)
    c.route("**/lib/hello.js*", lambda r: r.abort())
    q = c.new_page()
    q.goto(BASE + "/skribl-pad", wait_until="load")
    early = q.evaluate(ST, False)
    early_cover = q.evaluate("() => [document.documentElement.getAttribute('data-hello-cover'), Math.round(performance.now())]")
    q.wait_for_function("() => performance.now() > 9500", timeout=20000)
    late = q.evaluate(ST, False)
    late_cover = q.evaluate("() => document.documentElement.getAttribute('data-hello-cover')")
    check("if lib/hello.js never runs, the head's ground holds at first and goes by itself at 8 s, the canvas there",
          early_cover[0] == "up" and not early["canvasThere"] and late_cover is None and late["canvasThere"],
          f"at {early_cover[1]} ms the ground {early_cover[0]}, canvas {early['canvasThere']}; "
          f"at 9.5 s the ground {late_cover}, canvas {late['canvasThere']}")
    c.close()

    # A slow line for the page's own scripts: the first of them after the
    # hello held, and scripts deferred run in order, so every one behind it
    # waits too, the page's own copy of the hold timing among them, while the
    # player and the drawing come quickly. (Holding them all queued the
    # hello's own files behind them.) Its drawing must never play as plain
    # pages, all at once and gone in 0.8 s, which it did when it took the
    # drawing before the hold timing had run: read while they are held (it
    # waits for the page now, so there may be no player yet) and once they
    # come.
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
    TOTAL = """() => { const h = document.getElementById('skriblHello');
        const p = h && window.SkriblInline && SkriblInline.players().find(x => x.el && h.contains(x.el));
        return p ? Math.round(p.state().totalMs) : null; }"""
    totals, ran, t0 = [], False, time.time()
    while time.time() - t0 < 3:
        v = q.evaluate(TOTAL)
        if v is not None:
            totals.append(v)
        ran = ran or q.evaluate("() => typeof window.openDrawer === 'function'")
        q.wait_for_timeout(50)
    for r in held_page:
        r.continue_()
    t0 = time.time()
    while time.time() - t0 < 8:
        v = q.evaluate(TOTAL)
        if v is not None:
            totals.append(v)
            break
        q.wait_for_timeout(50)
    q.wait_for_function("() => !!window.SkriblHold", timeout=8000)
    timed = q.evaluate("(d) => Math.round(SkriblHold.plan(d.frames, d.fps || 12, d.loop).cycle)", HELLO)
    check("a slow line for the page's own scripts: the mark still writes itself in its own time "
          f"({timed} ms), never as plain pages all at once, while they are held and once they come",
          hold_after and len(held_page) == 1 and not ran and bool(totals) and all(t == timed for t in totals),
          f"held {behind} ({len(held_page)}), the hold timing behind it: {hold_after}, the page's scripts ran while "
          f"held: {ran}; the hello's player's totals {sorted(set(totals))}")
    c.close()

    # An empty cache on a slow line, as a first visit in a private window on
    # a phone meets it (owner: "Why does it not show every time in
    # incognito"): 3G as DevTools has it. The hello's three files were asked
    # for after the editor's hundred-odd scripts and came with them, 6.5 s
    # into its 4, so it did not come; asked for first, they are here within
    # its first second. And it draws once the page's own scripts are done:
    # started while they ran, it froze as each one did. The hold timing is
    # asked for twice, the page's copy and the hello's, so its first arrival
    # is the hello's.
    c = b.new_context(**PHONE)
    c.add_init_script(FORCE)
    c.add_init_script("""new MutationObserver((m, o) => { const h = document.getElementById('skriblHello'); if (!h) return;
      o.disconnect(); new MutationObserver((n, w) => { if (h.classList.contains('is-on')) { window.__helloOn = performance.now(); w.disconnect(); } })
        .observe(h, { attributes: true, attributeFilter: ['class'] }); }).observe(document, { childList: true, subtree: true });""")
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
        const nav = performance.getEntriesByType('navigation')[0];
        return { own: Math.round(Math.max(late('/inlineplayer.js'), first('/lib/holdtiming.js'), late('/brand/hello.json'))),
                 page: Math.round(nav.domContentLoadedEventEnd), ready: Math.round(nav.domContentLoadedEventStart),
                 on: window.__helloOn == null ? null : Math.round(window.__helloOn) }; }""")
    check("an empty cache on a slow line (3G), as a first visit in a private window: the hello still comes, "
          "its own files asked for first and here before the editor's own scripts, and it draws once those are done",
          ms3 is not None and s3["painted"] and tm["own"] < tm["page"] and tm["on"] is not None and tm["on"] >= tm["ready"],
          f"came {s3['painted']} after {ms3} ms (here {s3['here']}); its files by {tm['own']} ms, the page's by {tm['page']} ms; "
          f"on at {tm['on']} ms, the page ready at {tm['ready']} ms")
    c.close()

    # The replay link (owner: "Yes to the replay link"): an address with
    # ?hello=again plays it again where it was seen, and asks for it as this
    # suite does (no force here: automation that did not ask never meets
    # it), on both editors; a plain open after it goes straight to the canvas.
    replays = []
    for route in ("/skribl-pad", "/flip"):
        c = b.new_context(**PHONE)
        c.add_init_script("try { localStorage.setItem('%s', '1'); } catch (e) {}" % KEY)
        q = _open(c, route + "?hello=again", force=False)
        s, ms = _until(q, lambda s: s["painted"] and s["on"], 8000)
        q.goto(BASE + route, wait_until="load")
        plain = q.evaluate(ST, False)
        replays.append((route, ms, plain["here"], plain["canvasThere"]))
        c.close()
    check("the replay link: ?hello=again plays it again where it was seen, on the Pad and on Flip, "
          "and a plain open after it goes straight to the canvas",
          all(ms is not None and not here and there for _, ms, here, there in replays),
          "; ".join(f"{r}: came after {ms} ms, then plain open: hello there {here}, canvas {there}"
                    for r, ms, here, there in replays))

    # THE FIRST PAINT IS ITS GROUND (the owner, after the desktop checks: "on
    # a reload it goes to the canvas first, then goes to the skribl cursive
    # with i's dot dropping in"). It shows once the page's scripts and its
    # files are here, and the page had painted the canvas long before; now the
    # head lays its ground over the page before the first paint. Read as the
    # screen paints it, every frame the browser makes, on a reload of the
    # replay link as the owner made it. The page being left is painted a
    # colour no Skribl page is, so its frames are told from the new page's,
    # and only frames after the first of those count: the screen's first
    # frame can be one from before that colour was painted, on a busy machine
    # (the page as it was, read as the new page once beside other suites).
    # And the first of the editor's scripts after the hello's is held 0.8 s,
    # so the time the canvas would show is long enough to see on any machine.
    reloads = []
    for route in ("/skribl-pad", "/flip"):
        c = b.new_context(color_scheme="dark", **DESK)
        srcs = [u.split("?")[0] for u in re.findall(r'<script src="([^"]+)" defer', c.request.get(BASE + route).text())]
        at = next((k for k, u in enumerate(srcs) if u.endswith("/lib/hello.js")), -1)
        behind = srcs[at + 1] if 0 <= at < len(srcs) - 1 else None
        q = _open(c, route + "?hello=again", force=False)
        _until(q, lambda s: s["painted"] and s["on"], 8000)
        q.keyboard.press("Escape")
        _until(q, lambda s: not s["here"], 3000)
        ground = _hex(q.evaluate("() => getComputedStyle(document.documentElement).getPropertyValue('--surface-base').trim()"))
        q.evaluate("() => { document.documentElement.style.background = '#00ff00'; document.body.style.visibility = 'hidden'; }")
        q.evaluate("() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))")
        held = []
        c.route(lambda url: behind is not None and url.split("?")[0].endswith(behind), lambda r: held.append([time.time(), r]))
        cdp = c.new_cdp_session(q)
        frames = []

        def frame(ev, cdp=cdp, frames=frames):
            frames.append(base64.b64decode(ev["data"]))
            try:
                cdp.send("Page.screencastFrameAck", {"sessionId": ev["sessionId"]})
            except Exception:
                pass
        cdp.on("Page.screencastFrame", frame)
        cdp.send("Page.startScreencast", {"format": "png", "everyNthFrame": 1})
        q.wait_for_timeout(150)
        q.reload(wait_until="commit")
        t0, on_at, let_go = time.time(), None, 0
        while time.time() - t0 < 10:
            for h in held:
                if h[1] is not None and time.time() - h[0] >= 0.8:
                    h[1].continue_()
                    h[1] = None
                    let_go += 1
            if on_at is None and q.evaluate("() => { const h = document.getElementById('skriblHello'); "
                                            "return !!h && h.classList.contains('is-on'); }"):
                on_at = time.time()
            if on_at is not None and time.time() - on_at > 0.5:
                break
            q.wait_for_timeout(16)
        cdp.send("Page.stopScreencast")
        kinds = [_seen(f, ground) for f in frames]
        left = "left" in kinds
        seen = [k for k in kinds[kinds.index("left") if left else len(kinds):] if k not in ("left", "blank")]
        reloads.append((route, on_at is not None and left, let_go, seen))
        c.close()
    check("a reload of the replay link on a desk paints the hello's own ground first, and nothing of the page "
          "before the hello, on the Pad and on Flip (every frame the screen made, an editor's script held 0.8 s)",
          all(on and n == 1 and s[:1] == ["ground"] and "hello" in s and "page" not in s for _, on, n, s in reloads),
          "; ".join(f"{r}: the hello came (and the page left was seen) {on}, held {n}; the new page's frames: ground {s.count('ground')}, "
                    f"page {s.count('page')}, hello {s.count('hello')}, first {s[:1]}" for r, on, n, s in reloads))

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
    site_section(p)

summarise_and_exit()
