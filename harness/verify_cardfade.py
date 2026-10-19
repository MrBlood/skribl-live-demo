#!/usr/bin/env python3
"""The Gallery card's fade takes its colours from the drawing under it.

THE OWNER, at the card's controls over a pale drawing: "The fade has to be like
the glass with smart fade, sampling the background for the fade colors and
making it subtle. It's so obvious and ugly when it's wrong." Then, of the mock's
option A: "Smart fade is good." The fixed near-black scrim turned a pale
drawing's empty paper grey under the controls (6.7:1 against the same paper
without the bar), spread a dark band over the card's own edges, and left the
time's words at 2.6:1 on it.

WHAT IS ASKED, every row read off PAINTED PIXELS, never off a class name:
  * On a pale drawing the fade cannot be seen on its empty paper, and the time
    reads on it; the buttons are light glass there, dark glass on a dark
    drawing, and every icon reads on its own button.
  * The fade stays inside the drawing's round corners: the card's colour just
    outside them is the same with the bar up as with it away.
  * On a phone the row sits inside the drawing, not over the card's edge.
  * At rest, before anything plays, the same holds, read off the card image.
  * On a desk, where a tall drawing is narrower than the row, the card's colour
    beside it is untouched, the controls over it take ITS tone, and they turn
    when the page's theme does.
  * A drawing that cannot be read keeps the scrim: nothing is set on a guess.
  * Mute steps aside on a silent drawing, on the card and in full screen,
    from the first paint, so the row does not change at the first tap (the
    owner: yes).

THE FIXTURES are drawn for this: ink under the controls on purpose (grass, a
signature under the time, a sea line), each with a card image of its own the
way a post from the app has one. Titles carry a token per run, because the
gallery lists what every other suite posted publicly too.

HOW A ROW IS READ. The bar is shown three ways and shot each time: with its
time's words see-through (what is painted behind them), with its controls
hidden (the fade alone), and away (the drawing alone). Contrast is WCAG's,
pixel against pixel; 1.00 means the two are the same colour.
"""
import base64
import io
import json
import math
import os
import struct
import sys
import urllib.request
import wave

from assertions import make_check
import browsing

try:
    from playwright.sync_api import sync_playwright
    from PIL import Image, ImageDraw
except ImportError as exc:
    print(f"SUITE-SKIPPED: {exc}")
    print("No assertions were executed. This is NOT evidence the card's fade works.")
    raise SystemExit(77)

BASE = os.environ.get("SKRIBL_BASE", "http://127.0.0.1:5001")
results = []
check = make_check(results, with_detail=True)
TAG = "cf" + os.urandom(3).hex()

PHONE = dict(viewport={"width": 402, "height": 874}, device_scale_factor=2, is_mobile=True, has_touch=True)
DESK = dict(viewport={"width": 1280, "height": 900}, device_scale_factor=2)

# ------------------------------------------------------------------ fixtures
W, H = 402, 760
GROUND = {"paper": "#f6f2ea", "dark": "#0f1014", "sky": "#bfe3ff"}


def _wav():
    b = io.BytesIO()
    w = wave.open(b, "wb")
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(8000)
    w.writeframes(b"".join(struct.pack("<h", int(6000 * math.sin(i / 7))) for i in range(16000)))
    w.close()
    return "data:audio/wav;base64," + base64.b64encode(b.getvalue()).decode()


def _strokes(name):
    """Ink where the controls lie: the bottom eighth is crossed on purpose."""
    out, t = [], [0]

    def stroke(fn, n, color, base):
        for i in range(n):
            u = i / (n - 1)
            x, y = fn(u)
            out.append({"x": round(x, 1), "y": round(y, 1), "color": color, "t": t[0], "start": i == 0,
                        "size": round(base * (0.35 + 0.8 * math.sin(math.pi * u) ** 0.8), 2)})
            t[0] += 14
        t[0] += 200

    if name == "paper":     # a hill, grass through the foot, a signature under the time
        stroke(lambda u: (-10 + 422 * u, 590 - 120 * math.sin(math.pi * u) ** 1.4), 60, "#2a2340", 9)
        for k in range(9):
            stroke(lambda u, k=k: (20 + k * 44 + 8 * u, 740 - 70 * u), 12, "#2f7d4f", 6)
        stroke(lambda u: (250 + 120 * u, 715 + 14 * math.sin(u * 18) - 6 * u), 40, "#7c5cff", 6)
    elif name == "dark":    # waves through the foot
        for k, c in enumerate(["#7c5cff", "#a593ff", "#c9bcff"]):
            stroke(lambda u, k=k: (-10 + 422 * u, 610 + k * 52 + 20 * math.sin(u * 9 + k)), 60, c, 11 - 2 * k)
    else:                   # sky: a sea line under the time, the darkest ink there
        stroke(lambda u: (-10 + 422 * u, 640 + 10 * math.sin(u * 14)), 60, "#1b3a8a", 8)
        stroke(lambda u: (-10 + 422 * u, 735 + 8 * math.sin(u * 16)), 60, "#1b3a8a", 7)
    return out


def _card(name, pts):
    """The post's card image, 1200x630, the drawing where lib/sharecard.js
    drawingRect() puts it: what a post from the app carries."""
    sc = min(1092 / W, 492 / H)
    dw, dh = round(W * sc), round(H * sc)
    dx, dy = round((1200 - dw) / 2), round((630 - 84 - dh) / 2)
    img = Image.new("RGB", (1200, 630), (11, 13, 18))
    g = ImageDraw.Draw(img)
    g.rounded_rectangle((dx, dy, dx + dw, dy + dh), radius=18, fill=GROUND[name])
    run = []
    for p in pts + [{"start": True}]:
        if p.get("start") and run:
            g.line([(dx + q["x"] * sc, dy + q["y"] * sc) for q in run], fill=run[0]["color"],
                   width=max(1, round(run[len(run) // 2]["size"] * sc)), joint="curve")
            run = []
        if "x" in p:
            run.append(p)
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def post(name, sound=True, title=None):
    pts = _strokes(name)
    groups, n = [], 0
    for i, p in enumerate(pts):
        if p["start"] and i:
            groups.append(n); n = 0
        n += 1
    groups.append(n)
    frame = {"strokes": pts, "strokeGroups": groups, "background": {"color": GROUND[name]}}
    if sound:
        frame["music"] = {"data": _wav(), "name": "t.wav", "trimStart": 0, "trimEnd": 2}
    title = title or f"Card fade {name} {TAG}"
    body = {"title": title, "version": 2, "schemaVersion": 2, "visibility": "public",
            "playbackMode": "replay", "canvasSize": {"cssWidth": W, "cssHeight": H},
            "frames": [frame], "thumbnail": _card(name, pts)}
    req = urllib.request.Request(BASE + "/api/skribls", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    json.loads(urllib.request.urlopen(req, timeout=30).read())
    return title


# ------------------------------------------------------------------ reading
def _lin(c):
    c /= 255
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def lum(p):
    return 0.2126 * _lin(p[0]) + 0.7152 * _lin(p[1]) + 0.0722 * _lin(p[2])


def ratio(a, b):
    la, lb = lum(a), lum(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def rgb(css):
    import re
    return tuple(int(float(v)) for v in re.findall(r"[\d.]+", css)[:3])


# Stronger than any rule the bar has, so they win against the variant's own.
SHOW = """
.skfull.skfull-card { transition: none !important; }
.skfull.skfull-card.__w.__w .skfull-time.skfull-time.skfull-time { color: transparent !important; }
.skfull.skfull-card.__b.__b .skfull-row > * { visibility: hidden !important; }
.skfull.skfull-card.__g.__g, .skfull.skfull-card.__g.__g *, .skfull.skfull-card.__g.__g::before { visibility: hidden !important; }
"""
GEOM = """(t) => {
  const bar = t.querySelector('.skfull.skfull-card'), box = t.querySelector('.skribl-inline');
  const cv = box.querySelector('.skribl-inline-canvas'), img = box.querySelector('.skribl-inline-poster');
  const R = e => { const r = e.getBoundingClientRect(); return [r.left, r.top, r.right, r.bottom]; };
  const live = cv && !cv.hidden;
  let d, plate = 0;
  if (live) d = R(cv);
  else { const p = img.getBoundingClientRect(), s = p.width / 1200, q = img._d;
         d = [p.left + (q[0] + 2) * s, p.top + (q[1] + 2) * s, p.left + (q[0] + q[2] - 2) * s, p.top + (q[1] + q[3] - 2) * s];
         plate = (18 - 2) * s; }
  const btn = c => { const e = bar.querySelector('.skfull-' + c); return e && { r: R(e), ink: getComputedStyle(e).color }; };
  return { live, plate, bar: R(bar), box: R(box), stage: R(t.querySelector('.tileStage')), drawing: d,
           time: R(bar.querySelector('.skfull-dur')), timeInk: getComputedStyle(bar.querySelector('.skfull-dur')).color,
           play: R(bar.querySelector('.skfull-play')), loop: btn('loop'), mute: btn('mute'), full: btn('full'),
           radius: parseFloat(getComputedStyle(box).borderBottomLeftRadius), border: parseFloat(getComputedStyle(box).borderBottomWidth),
           scrim: getComputedStyle(bar).backgroundImage, smart: bar.classList.contains('is-smart') }; }"""


def frames(pg, n=2):
    pg.evaluate(f"() => new Promise(r => {{ let k = {n}; const f = () => (--k ? requestAnimationFrame(f) : r()); requestAnimationFrame(f); }})")


class Card:
    """One card on the page, its bar shown, and its shots."""

    def __init__(self, pg, title, phone, play=True):
        self.pg = pg
        self.tile = pg.locator(".tile", has_text=title).first
        self.tile.scroll_into_view_if_needed()
        pg.wait_for_timeout(300)
        if play:
            box = self.tile.locator(".skribl-inline").first
            (box.tap() if phone else box.click())
            pg.wait_for_timeout(900)
            self.up()
            self.tile.locator(".skfull-card .skfull-play").first.click()
            pg.wait_for_timeout(250)
            # The last frame: the whole drawing, its ink under the controls.
            self.tile.evaluate("""t => { const tr = t.querySelector('.skfull-card .skfull-track'), r = tr.getBoundingClientRect();
              tr.dispatchEvent(new MouseEvent('click', { bubbles: true, clientX: r.right - 0.5, clientY: r.top + r.height / 2 })); }""")
            pg.wait_for_timeout(500)
        self.up()
        pg.wait_for_timeout(300)
        self.g = self.tile.evaluate(GEOM)
        s = self.g["stage"]
        self.clip = {"x": s[0] - 4, "y": s[1], "width": s[2] - s[0] + 8, "height": s[3] - s[1] + 4}

    def up(self):
        self.tile.evaluate("t => t.classList.add('ctl-on')")

    def shot(self, mode=""):
        self.up()
        self.tile.evaluate("(t, m) => { const b = t.querySelector('.skfull.skfull-card'); b.classList.remove('__w', '__b', '__g'); if (m) b.classList.add(m); }", mode)
        frames(self.pg)
        im = Image.open(io.BytesIO(self.pg.screenshot(clip=self.clip))).convert("RGB")
        self.tile.evaluate("t => t.querySelector('.skfull.skfull-card').classList.remove('__w', '__b', '__g')")
        return im

    def px(self, im, x, y):
        k = im.width / self.clip["width"]
        return im.getpixel((min(im.width - 1, int((x - self.clip["x"]) * k)), min(im.height - 1, int((y - self.clip["y"]) * k))))

    def time_worst(self):
        """The time's colour against every pixel painted behind its words."""
        bg = self.shot("__w")
        ink, t = rgb(self.g["timeInk"]), self.g["time"]
        worst, y = 99.0, t[1] + 2
        while y < t[3] - 2:
            x = t[0] + 0.5
            while x < t[2] - 0.5:
                worst = min(worst, ratio(ink, self.px(bg, x, y)))
                x += 0.5
            y += 0.5
        return worst

    def fade_moves(self, x0, x1, y):
        """How far the fade moves what is painted, along one row: the median
        contrast between the bar's fade alone and the bar away."""
        a, b = self.shot("__b"), self.shot("__g")
        v = sorted(ratio(self.px(a, x, y), self.px(b, x, y)) for x in frange(x0, x1, 1))
        return v[len(v) // 2] if v else None, a, b

    def fill(self, im, which):
        """A button's own fill: the middle value of a ring inside its edge."""
        r = self.g[which]["r"]
        cx, cy, R = (r[0] + r[2]) / 2, (r[1] + r[3]) / 2, (r[2] - r[0]) / 2
        ring = [self.px(im, cx + R * f * math.cos(a), cy + R * f * math.sin(a))
                for a in [i * math.pi / 15 for i in range(30)] for f in (0.66, 0.74, 0.82)]
        return tuple(sorted(p[i] for p in ring)[len(ring) // 2] for i in range(3))


def outside_corners(c, bare, gone, x0, x1, y1, rad):
    """Points just outside the drawing's two bottom rounds (2.5px past the
    arc, inside its square corner): where a rectangle of fade would paint the
    drawing's paper over the card. The largest change there, bar fade alone
    against bar away."""
    out = []
    for side, cx in ((-1, x0 + rad), (1, x1 - rad)):
        cy = y1 - rad
        for a in range(15, 80, 8):
            t = math.radians(a)
            x, y = cx + side * (rad + 2.5) * math.cos(t), cy + (rad + 2.5) * math.sin(t)
            out.append(ratio(c.px(bare, x, y), c.px(gone, x, y)))
    return max(out), len(out)


def frange(a, b, step):
    x = a
    while x < b:
        yield x
        x += step


def open_gallery(b, view, theme):
    pg = b.new_page(color_scheme=theme, **view)
    browsing.goto(pg, BASE, "/gallery")
    pg.wait_for_timeout(1500)
    pg.add_style_tag(content=SHOW)
    return pg


# ------------------------------------------------------------------ the rows
titles = {n: post(n) for n in ("paper", "dark", "sky")}
titles["silent"] = post("paper", sound=False, title=f"Card fade silent {TAG}")

# The Fullscreen API taken away, so full screen is the page's own CSS state
# (lib/immersive.js's fallback, iOS Safari's only one): the same bar, testable.
NO_API = """(() => { try {
  Object.defineProperty(Document.prototype, 'fullscreenEnabled', { get: () => false, configurable: true });
  Object.defineProperty(Document.prototype, 'webkitFullscreenEnabled', { get: () => false, configurable: true }); } catch (e) {}
  try { delete Element.prototype.requestFullscreen; } catch (e) {}
  try { delete Element.prototype.webkitRequestFullscreen; } catch (e) {} })();"""
MUTE = """(t) => { const card = t.querySelector('.skfull.skfull-card'), full = t.querySelector('.skfull:not(.skfull-card)');
  const m = b => { const e = b && b.querySelector('.skfull-mute'); return e ? e.getClientRects().length > 0 : null; };
  const x = s => { const e = card.querySelector(s); return e ? Math.round(e.getBoundingClientRect().left * 10) / 10 : null; };
  return { card: m(card), full: m(full), row: [x('.skfull-play'), x('.skfull-loop'), x('.skfull-full')] }; }"""

with sync_playwright() as p:
    b = p.chromium.launch()

    print("\nCARD FADE — a pale drawing, played, on a phone")
    pg = open_gallery(b, PHONE, "dark")
    c = Card(pg, titles["paper"], phone=True)
    g = c.g
    d = g["drawing"]
    ym = (g["bar"][1] + g["bar"][3]) / 2
    moved, bare, gone = c.fade_moves(d[0] + 3, d[2] - 3, ym)
    check("on a pale drawing the fade cannot be seen on its empty paper (the bar's middle, 1.00 is none)",
          moved is not None and moved <= 1.10,
          f"median {moved:.2f} between the fade alone and the bar away; the near-black scrim was 6.7")
    tw = c.time_worst()
    check("...and the time's words read on it, every pixel behind them at 4.5:1 or more",
          tw >= 4.5, f"worst {tw:.2f}:1 ({g['timeInk']}); 12px words, 4.5 is the floor")
    shown = c.shot()
    fills = {k: c.fill(shown, k) for k in ("loop", "mute", "full")}
    check("...and the buttons beside it are light glass (each button's own fill)",
          all(lum(v) > 0.5 for v in fills.values()),
          ", ".join(f"{k} {lum(v):.2f}" for k, v in fills.items()) + " (relative luminance; light glass is over 0.5)")
    icons = {k: ratio(rgb(g[k]["ink"]), fills[k]) for k in fills}
    check("...and every icon reads on its own button, 3:1 or more",
          min(icons.values()) >= 3, ", ".join(f"{k} {v:.2f}:1" for k, v in icons.items()))
    # Just outside the drawing's bottom corners, on the card's own colour:
    # where a rectangle of fade would have painted the paper over the round.
    rad, bw, bx = g["radius"], g["border"], g["box"]
    worst, npts = outside_corners(c, bare, gone, bx[0] + bw, bx[2] - bw, bx[3] - bw, rad - bw)
    check("...and the fade stays inside the drawing's round corners (the card's colour just outside them is untouched)",
          worst <= 1.05, f"largest change {worst:.2f} over {npts} points outside the two corners")
    check("...and on a phone the row sits inside the drawing, not over the card's edge",
          g["play"][0] >= d[0] + 2 and g["time"][2] <= d[2] - 2,
          f"play's left {g['play'][0]:.1f} and time's right {g['time'][2]:.1f} against the drawing {d[0]:.1f}..{d[2]:.1f}")
    pg.close()

    print("\nCARD FADE — a dark drawing and a sky, played, on a phone, on a light page")
    pg = open_gallery(b, PHONE, "light")
    c = Card(pg, titles["dark"], phone=True)
    shown = c.shot()
    fills = {k: c.fill(shown, k) for k in ("loop", "mute", "full")}
    check("on a dark drawing the buttons are dark glass",
          all(lum(v) < 0.2 for v in fills.values()),
          ", ".join(f"{k} {lum(v):.2f}" for k, v in fills.items()) + " (dark glass is under 0.2)")
    tw = c.time_worst()
    check("...and the time reads on it", tw >= 4.5, f"worst {tw:.2f}:1")
    c = Card(pg, titles["sky"], phone=True)
    tw = c.time_worst()
    check("on a pale sky with a dark sea line under the time, the time reads", tw >= 4.5,
          f"worst {tw:.2f}:1; the near-black scrim left it at 2.9")
    pg.close()

    print("\nCARD FADE — at rest, read off the card image, on a phone")
    pg = open_gallery(b, PHONE, "dark")
    c = Card(pg, titles["paper"], phone=True, play=False)
    check("at rest the card image is what is showing (nothing has played)", not c.g["live"])
    shown = c.shot()
    fills = {k: c.fill(shown, k) for k in ("loop", "full")}
    check("...and on a pale drawing the buttons are light glass, read off the card image",
          all(lum(v) > 0.5 for v in fills.values()),
          ", ".join(f"{k} {lum(v):.2f}" for k, v in fills.items()))
    d, ym = c.g["drawing"], (c.g["bar"][1] + c.g["bar"][3]) / 2
    moved, bare, gone = c.fade_moves(d[0] + 3, d[2] - 3, ym)
    check("...and the fade cannot be seen on its empty paper", moved is not None and moved <= 1.10, f"median {moved:.2f}")
    worst, npts = outside_corners(c, bare, gone, d[0], d[2], d[3], c.g["plate"])
    check("...and it keeps to the card image's own rounder corners (the plate's)",
          worst <= 1.05, f"largest change {worst:.2f} over {npts} points outside the plate's {c.g['plate']:.1f}px rounds")
    c = Card(pg, titles["dark"], phone=True, play=False)
    shown = c.shot()
    fills = {k: c.fill(shown, k) for k in ("loop", "full")}
    check("...and on a dark one, dark glass", all(lum(v) < 0.2 for v in fills.values()),
          ", ".join(f"{k} {lum(v):.2f}" for k, v in fills.items()))
    pg.close()

    print("\nCARD FADE — a tall drawing on a desk card, narrower than the row")
    pg = open_gallery(b, DESK, "light")
    pg.evaluate("() => document.documentElement.setAttribute('data-theme', 'light')")
    c = Card(pg, titles["paper"], phone=False)
    g, d = c.g, c.g["drawing"]
    ym = (g["bar"][1] + g["bar"][3]) / 2
    left = (g["stage"][0] + 20, d[0] - 4)
    a = c.shot("__b"); z = c.shot("__g")
    side = sorted(ratio(c.px(a, x, ym), c.px(z, x, ym)) for x in frange(left[0], left[1], 1))
    check("on a desk the card's own colour beside the drawing is untouched by the fade",
          side and side[-1] <= 1.05, f"largest change {side[-1]:.2f} across the card beside the drawing; the scrim was 7.0 on a light page")
    # MUTE, NOT LOOP: Repeat is lit by default, and its violet tint over a
    # dark card reads dark in either glass, so a Loop that never turned
    # passed the row below (calibration: the theme watch removed, still green).
    shown = c.shot()
    over = c.fill(shown, "mute")
    check("...and a control over the card's colour takes ITS tone: light glass on a light page",
          lum(over) > 0.5, f"Mute's fill {lum(over):.2f}, over the card beside the drawing")
    tw = c.time_worst()
    check("...and the time over it reads", tw >= 4.5, f"worst {tw:.2f}:1")
    # The page's theme turns: the card's colour with it, and the control too.
    pg.evaluate("() => document.documentElement.setAttribute('data-theme', 'dark')")
    pg.wait_for_timeout(400)
    c.g = c.tile.evaluate(GEOM)
    shown = c.shot()
    over = c.fill(shown, "mute")
    check("...and when the page turns dark, that control turns to dark glass with it",
          lum(over) < 0.2, f"Mute's fill {lum(over):.2f} after the theme turned")
    pg.close()

    print("\nCARD FADE — a drawing that cannot be read keeps the scrim")
    pg = open_gallery(b, PHONE, "dark")
    c = Card(pg, titles["paper"], phone=True)
    smart_before = c.g["smart"]
    # As a card or a canvas holding another origin's picture answers: reading
    # its pixels throws (a tainted canvas's SecurityError). Read again on the
    # next change of state, which is when the bar reads. THE MECHANISM, NOT A
    # NAME: a stub on one method went quiet when the reading moved.
    c.tile.evaluate("""() => { CanvasRenderingContext2D.prototype.getImageData = function () {
      throw new DOMException('The canvas has been tainted by cross-origin data.', 'SecurityError'); }; }""")
    c.tile.locator(".skfull-card .skfull-play").first.click()
    pg.wait_for_timeout(400)
    c.tile.locator(".skfull-card .skfull-play").first.click()
    pg.wait_for_timeout(400)
    c.up()
    g2 = c.tile.evaluate(GEOM)
    check("a card that read its drawing wears the smart fade", smart_before)
    check("...and once its drawing cannot be read, the near-black scrim is back, not a guess",
          (not g2["smart"]) and "rgba(6, 7, 10" in g2["scrim"], f"smart {g2['smart']}, background {g2['scrim'][:60]}")
    pg.close()

    print("\nCARD FADE — Mute steps aside on a silent drawing, on the card and in full screen")
    pg = b.new_page(color_scheme="dark", **PHONE)
    pg.add_init_script(NO_API)
    browsing.goto(pg, BASE, "/gallery")
    pg.wait_for_timeout(1500)
    pg.add_style_tag(content=SHOW)
    quiet = pg.locator(".tile", has_text=titles["silent"]).first
    loud = pg.locator(".tile", has_text=titles["paper"]).first
    quiet.scroll_into_view_if_needed(); pg.wait_for_timeout(400)
    quiet.evaluate("t => t.classList.add('ctl-on')"); pg.wait_for_timeout(200)
    rest = quiet.evaluate(MUTE)
    loud.scroll_into_view_if_needed(); pg.wait_for_timeout(400)
    loud.evaluate("t => t.classList.add('ctl-on')"); pg.wait_for_timeout(200)
    said = loud.evaluate(MUTE)
    check("at rest, before anything plays, a silent drawing's card has no Mute",
          rest["card"] is False, f"Mute painted: {rest['card']}")
    check("...and a drawing with sound keeps its Mute", said["card"] is True, f"Mute painted: {said['card']}")
    quiet.scroll_into_view_if_needed(); pg.wait_for_timeout(300)
    quiet.locator(".skribl-inline").first.tap(); pg.wait_for_timeout(1200)
    quiet.evaluate("t => t.classList.add('ctl-on')"); pg.wait_for_timeout(200)
    played = quiet.evaluate(MUTE)
    # THE BUTTONS, NOT THE SCRUBBER: the time grows from "0:05" to "0:01 /
    # 0:05" when a card plays, as it always has, and the scrubber gives way
    # to it. A Mute that left only once the drawing loaded would take 46px
    # out from under Full screen at that tap; so would a row placed from the
    # card image's plate, 2.6px inside the drawing (this row caught both).
    check("...and the first tap does not move a button (Play, Repeat, Full screen where they were)",
          all(a is not None and b is not None and abs(a - b) <= 0.5 for a, b in zip(rest["row"], played["row"])),
          f"left edges {rest['row']} at rest, {played['row']} playing")
    check("...and playing, still no Mute", played["card"] is False, f"Mute painted: {played['card']}")
    quiet.locator(".skfull-card .skfull-full").first.click(); pg.wait_for_timeout(900)
    quiet.evaluate("t => { const s = t.querySelector('.tileStage'); s.dispatchEvent(new PointerEvent('pointermove', { bubbles: true })); }")
    pg.wait_for_timeout(200)
    big = quiet.evaluate(MUTE)
    check("...and in full screen its bar has no Mute either", big["full"] is False, f"Mute painted in full screen: {big['full']}")
    pg.close()
    b.close()

print("\n" + "=" * 62)
passed = sum(1 for r in results if r[0])
print(f"{passed}/{len(results)} passed" + ("" if passed == len(results) else
      "  FAILURES: " + ", ".join(r[1] for r in results if not r[0])))
sys.exit(0 if passed == len(results) else 1)
