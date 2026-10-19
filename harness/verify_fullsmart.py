#!/usr/bin/env python3
"""Every full screen's bar takes its colours from the drawing under it.

THE OWNER, from the measured full-screen mock: "A, smart fade and yes to all".
The Gallery card's smart fade (verify_cardfade) carried to the bars that lie
over a drawing in full screen: the Gallery's and the Library's (one bar,
lib/fullbar.js), the link page's (#playerBar) and Pad's and Flip's
(lib/watchfull.js, which wears the link page's band). One reading for all of
them and the card, lib/smartfade.js. Before it, the Gallery's near-black
scrim moved a pale drawing's empty paper 4.9:1 and sank the time into it
(1.0:1 on its worst pixel), and a light page's white fog on the link page
moved a dark drawing 3.4:1.

WHAT IS ASKED, every row read off PAINTED PIXELS:
  * On a pale drawing's empty paper the fade cannot be seen, and on a dark
    drawing under a light page it is not a fog.
  * Every word on the bar reads on what is under it: the worst pixel under
    its letters, the other controls away, at 4.5:1 or more. Over lines of ink
    running right under the words too, which is their faint halo's job; the
    Gallery's words sit where the fade is strong enough without it, so there
    the halo is asked to lift what is under the letters.
  * Each glass control takes the tone of what is under it: light glass over a
    light ground, dark over a dark one, and it turns with the page's theme.
  * A title crossing a tall drawing's edge on a desk sits in a capsule, which
    carries its words over both sides.
  * A photo under the drawing as a picture of its own (the Pad's) keeps the
    scrim: nothing is set on a guess.

THE PHONE IS THE OWNER'S, 402x874, with the Fullscreen API taken away as
Safari has it for anything but a video, so full screen is the pinned stand-in
(lib/immersive.js). The desk has the real API.

HOW A ROW IS READ, as verify_cardfade does: the bar is shot with its words
see-through over the drawing, its other controls away (what the letters sit
on), with its contents hidden (the fade alone), and away (the drawing alone).
Where the words paint is where the shot as shown differs from the
see-through one. Contrast is WCAG's, pixel against pixel; 1.00 is the same
colour. The pen's glowing dot, which rides above everything while a drawing
plays and hides once it ends, is set aside: on the link page's phone it sat
on the time's last digit at 3.4:1, and no fade can reach it.
"""
import base64
import io
import json
import math
import os
import re
import sys
import urllib.request

from assertions import make_check
import browsing

try:
    from playwright.sync_api import sync_playwright
    from PIL import Image, ImageChops
except ImportError as exc:
    print(f"SUITE-SKIPPED: {exc}")
    print("No assertions were executed. This is NOT evidence full screen's fade works.")
    raise SystemExit(77)

BASE = os.environ.get("SKRIBL_BASE", "http://127.0.0.1:5001")
results = []
check = make_check(results, with_detail=True)
TAG = "fs" + os.urandom(3).hex()

PHONE = dict(viewport={"width": 402, "height": 874}, device_scale_factor=2, is_mobile=True, has_touch=True)
DESK = dict(viewport={"width": 1280, "height": 900}, device_scale_factor=1)
NO_API = """(() => { try {
  Object.defineProperty(Document.prototype, 'fullscreenEnabled', { get: () => false, configurable: true });
  Object.defineProperty(Document.prototype, 'webkitFullscreenEnabled', { get: () => false, configurable: true }); } catch (e) {}
  try { delete Element.prototype.requestFullscreen; } catch (e) {}
  try { delete Element.prototype.webkitRequestFullscreen; } catch (e) {} })();"""

# ------------------------------------------------------------------ fixtures
W, H = 402, 760
GROUND = {"paper": "#f6f2ea", "dark": "#0f1014", "lines": "#f6f2ea", "darklines": "#0f1014"}


def _strokes(name):
    """Ink where the controls lie: the drawing's foot is crossed on purpose."""
    out, t = [], [0]

    def stroke(fn, n, color, base):
        for i in range(n):
            u = i / (n - 1)
            x, y = fn(u)
            out.append({"x": round(x, 1), "y": round(y, 1), "color": color, "t": t[0], "start": i == 0,
                        "size": round(base * (0.35 + 0.8 * math.sin(math.pi * u) ** 0.8), 2)})
            t[0] += 14
        t[0] += 200

    if name == "paper":     # a hill, and grass through the foot
        stroke(lambda u: (-10 + 422 * u, 520 - 140 * math.sin(math.pi * u) ** 1.4), 60, "#2a2340", 9)
        for k in range(9):
            stroke(lambda u, k=k: (20 + k * 44 + 8 * u, 750 - 90 * u), 12, "#2f7d4f", 6)
    elif name in ("lines", "darklines"):    # lines of ink right under the words, 4px every 11px
        y = H * 0.80
        while y < H * 0.995:
            for i in range(40):
                u = i / 39
                out.append({"x": round(-6 + (W + 12) * u, 1), "y": round(y + 3 * math.sin(u * 7), 1), "t": t[0],
                            "color": "#2a2340" if name == "lines" else "#c9bcff", "start": i == 0, "size": 4.0})
                t[0] += 10
            t[0] += 100
            y += 11
    else:                   # waves through the foot
        for k, c in enumerate(["#7c5cff", "#a593ff", "#c9bcff"]):
            stroke(lambda u, k=k: (-10 + 422 * u, 600 + k * 56 + 20 * math.sin(u * 9 + k)), 60, c, 11 - 2 * k)
    return out


def post(name, title):
    pts = _strokes(name)
    groups, n = [], 0
    for i, p in enumerate(pts):
        if p["start"] and i:
            groups.append(n); n = 0
        n += 1
    groups.append(n)
    body = {"title": title, "version": 2, "schemaVersion": 2, "visibility": "public",
            "playbackMode": "replay", "canvasSize": {"cssWidth": W, "cssHeight": H},
            "frames": [{"strokes": pts, "strokeGroups": groups, "background": {"color": GROUND[name]}}]}
    req = urllib.request.Request(BASE + "/api/skribls", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=30).read())["id"]


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
    return tuple(int(float(v)) for v in re.findall(r"[\d.]+", css)[:3])


def frames(pg, n=2):
    pg.evaluate(f"() => new Promise(r => {{ let k = {n}; const f = () => (--k ? requestAnimationFrame(f) : r()); requestAnimationFrame(f); }})")


class Bar:
    """One full screen's bar, the drawing under it, and its shots. `sel` finds
    the bar; `words` are its words, `glass` its controls (selectors). The
    shots' rules are stronger than any the bar has, so they win."""

    def __init__(self, pg, sel, words, glass, keep=None):
        self.pg, self.sel, self.words, self.glass = pg, sel, words, glass
        # What the words sit on that is the bar's own: the title's capsule.
        held = f"{sel}.__s.__s.__s.__s :is({keep}) {{ visibility: visible !important; }}" if keep else ""
        # The pen's glowing dot rides above the bar while a drawing plays and
        # hides once it ends; no fade can reach it, so it is set aside.
        pg.add_style_tag(content=f"""
.player-nib, .skribl-inline-nib {{ visibility: hidden !important; }}
{sel} {{ transition: none !important; }}
.chrome-asleep :is(.player-bar, .player-btn.full-exit, .skfull) {{ opacity: 1 !important; }}
{sel}.__w.__w.__w.__w :is({words}), {sel}.__w.__w.__w.__w :is({words}) * {{ color: transparent !important; }}
{sel}.__s.__s.__s.__s * {{ visibility: hidden !important; }}
{sel}.__s.__s.__s.__s :is({words}), {sel}.__s.__s.__s.__s :is({words}) * {{ visibility: visible !important; color: transparent !important; }}
{held}
{sel}.__b.__b.__b.__b > * {{ visibility: hidden !important; }}
{sel}.__g.__g.__g.__g, {sel}.__g.__g.__g.__g *, {sel}.__g.__g.__g.__g::before {{ visibility: hidden !important; }}
""")
        r = pg.evaluate(f"() => {{ const r = document.querySelector('{sel}').getBoundingClientRect(); return [r.left, r.top, r.right, r.bottom]; }}")
        vw, vh = pg.viewport_size["width"], pg.viewport_size["height"]
        top = max(0, r[1] - 60)
        self.bar = r
        self.clip = {"x": 0, "y": top, "width": vw, "height": vh - top}

    def state(self):
        return self.pg.evaluate(f"""() => {{ const b = document.querySelector('{self.sel}'), R = e => {{ const r = e.getBoundingClientRect(); return [r.left, r.top, r.right, r.bottom]; }};
          const ws = [...b.querySelectorAll('{self.words}')].filter(e => e.getClientRects().length && e.textContent.trim())
            .map(e => ({{ r: R(e), ink: getComputedStyle(e).color, text: e.textContent.trim(), tone: e.classList.contains('t-light') ? 'light' : e.classList.contains('t-dark') ? 'dark' : null, cap: e.classList.contains('cap') }}));
          const gs = [...b.querySelectorAll('{self.glass}')].filter(e => e.getClientRects().length)
            .map(e => ({{ r: R(e), name: e.getAttribute('aria-label') || e.className, tone: e.classList.contains('t-light') ? 'light' : e.classList.contains('t-dark') ? 'dark' : null }}));
          return {{ smart: b.classList.contains('is-smart'), scrim: getComputedStyle(b).backgroundImage, words: ws, glass: gs, bar: R(b) }}; }}""")

    def shot(self, mode=""):
        self.pg.evaluate(f"(m) => {{ const b = document.querySelector('{self.sel}'); b.classList.remove('__w', '__s', '__b', '__g'); if (m) b.classList.add(m); }}", mode)
        frames(self.pg)
        im = Image.open(io.BytesIO(self.pg.screenshot(clip=self.clip))).convert("RGB")
        self.pg.evaluate(f"() => document.querySelector('{self.sel}').classList.remove('__w', '__s', '__b', '__g')")
        return im

    def px(self, im, x, y):
        k = im.width / self.clip["width"]
        return im.getpixel((min(im.width - 1, max(0, int((x - self.clip["x"]) * k))),
                            min(im.height - 1, max(0, int((y - self.clip["y"]) * k)))))

    def words_worst(self, bare=False):
        """Each word's ink against what is under its letters (the other
        controls away), where its letters paint. (worst, where, count); with
        `bare`, also the worst against the bar away, where no halo is."""
        st, shown, see, solo = self.state(), self.shot(), self.shot("__w"), self.shot("__s")
        away = self.shot("__b") if bare else None
        k = shown.width / self.clip["width"]
        worst, where, n, worst_away = 99.0, "", 0, 99.0
        for w in st["words"]:
            ink, r = rgb(w["ink"]), w["r"]
            y = r[1]
            while y < r[3]:
                x = r[0]
                while x < r[2]:
                    a, b = self.px(shown, x, y), self.px(see, x, y)
                    if sum(abs(i - j) for i, j in zip(a, b)) > 30:
                        v = ratio(ink, self.px(solo, x, y)); n += 1
                        if v < worst:
                            worst, where = v, w["text"][:16]
                        if away:
                            worst_away = min(worst_away, ratio(ink, self.px(away, x, y)))
                    x += 1 / k
                y += 1 / k
        return (worst, where, n, worst_away) if bare else (worst, where, n)

    def fade_moves(self, y=None):
        """How far the fade moves what is painted along the bar's top row:
        the median contrast between the fade alone and the bar away."""
        a, b = self.shot("__b"), self.shot("__g")
        y = y if y is not None else self.bar[1] + 8
        v = sorted(ratio(self.px(a, x, y), self.px(b, x, y)) for x in range(int(self.bar[0]) + 2, int(self.bar[2]) - 2, 2))
        return v[len(v) // 2]


def gallery(b, view, theme, title):
    """The Gallery's full screen of one post, paused near its end."""
    pg = b.new_page(color_scheme=theme, **view)
    if view is PHONE:
        pg.add_init_script(NO_API)
    browsing.goto(pg, BASE, "/gallery")
    pg.wait_for_timeout(1200)
    tile = pg.locator(".tile", has_text=title).first
    tile.scroll_into_view_if_needed(); pg.wait_for_timeout(300)
    tile.evaluate("t => t.classList.add('ctl-on')")
    tile.locator(".skfull-card .skfull-full").first.click(); pg.wait_for_timeout(1200)
    tile.evaluate("""t => { const s = t.querySelector('.tileStage'), b = s.querySelector('.skfull:not(.skfull-card) .skfull-play');
        if (b.getAttribute('aria-label') === 'Pause') b.click(); }""")
    pg.wait_for_timeout(300)
    tile.evaluate("""t => { const tr = t.querySelector('.tileStage .skfull:not(.skfull-card) .skfull-track'), r = tr.getBoundingClientRect();
        tr.dispatchEvent(new MouseEvent('click', { bubbles: true, clientX: r.left + r.width * 0.985, clientY: r.top + r.height / 2 })); }""")
    pg.wait_for_timeout(700)
    tile.evaluate("t => t.querySelector('.tileStage').setAttribute('data-fs-probe', '')")
    return pg, Bar(pg, "[data-fs-probe] .skfull:not(.skfull-card)", ".skfull-time, .skfull-title, .skfull-by",
                   ".skfull-btn:not(.skfull-play)", keep=".skfull-words")


def link(b, view, theme, sid):
    """A shared link's full screen, paused near its end."""
    pg = b.new_page(color_scheme=theme, **view)
    if view is PHONE:
        pg.add_init_script(NO_API)
    browsing.goto(pg, BASE, "/s/" + sid)
    pg.wait_for_timeout(1000)
    pg.evaluate("() => document.getElementById('playerFullBtn').click()"); pg.wait_for_timeout(1200)
    pg.evaluate("() => { const b = document.getElementById('playerPlayBtn'); if (b.getAttribute('aria-label') === 'Pause') b.click(); }")
    pg.wait_for_timeout(300)
    pg.evaluate("""() => { const tr = document.getElementById('playerProgress'), r = tr.getBoundingClientRect();
        for (const t of ['pointerdown', 'pointerup', 'click']) tr.dispatchEvent(new PointerEvent(t, { bubbles: true,
          clientX: r.left + r.width * 0.985, clientY: r.top + r.height / 2, pointerId: 1, isPrimary: true })); }""")
    pg.wait_for_timeout(700)
    pg.evaluate("() => { const b = document.getElementById('playerPlayBtn'); if (b.getAttribute('aria-label') === 'Pause') b.click(); }")
    pg.wait_for_timeout(300)
    return pg, Bar(pg, "#playerBar", ".player-time > span, .rl-drawn, .rl-m, .rl-skip", ".player-btn:not(.primary), .rl-speed")


def pad(b, theme, photo=False):
    """The Pad's own full screen on a desk: long strokes on its paper swatch,
    the last along the foot, played and paused near its end."""
    pg = b.new_page(color_scheme=theme, **DESK)
    browsing.goto(pg, BASE, "/skribl-pad")
    pg.evaluate("() => { try { localStorage.clear(); } catch (e) {} }")
    browsing.goto(pg, BASE, "/skribl-pad")
    pg.wait_for_timeout(800)
    pg.evaluate("() => window.SkriblHints && window.SkriblHints.hide()")
    pg.evaluate("() => { const b = document.querySelector('.bg-swatch[data-bg=\"#f6f2ea\"]'); if (b) b.click(); }")
    if photo:
        im = Image.new("RGB", (300, 220), (190, 120, 70))
        buf = io.BytesIO(); im.save(buf, "PNG")
        browsing.pad_drawer(pg, "photo"); pg.wait_for_timeout(400)
        pg.set_input_files("#photoInput", {"name": "p.png", "mimeType": "image/png", "buffer": buf.getvalue()})
        pg.wait_for_timeout(1500)
        browsing.pad_drawer(pg, "photo"); pg.wait_for_timeout(300)
    bx = pg.locator("#canvas").bounding_box()
    for yy, amp, ph in ((0.45, 0.05, 0), (0.70, 0.06, 1.3), (0.94, 0.03, 0.6)):
        x0, x1 = bx["x"] + bx["width"] * 0.06, bx["x"] + bx["width"] * 0.94
        pg.mouse.move(x0, bx["y"] + bx["height"] * yy); pg.mouse.down()
        for s in range(1, 31):
            u = s / 30
            pg.mouse.move(x0 + (x1 - x0) * u, bx["y"] + bx["height"] * (yy + amp * math.sin(ph + u * 9)), steps=2)
        pg.mouse.up(); pg.wait_for_timeout(120)
    pg.evaluate("() => { if (typeof endRecordingTake === 'function' && recording) endRecordingTake(); }")
    pg.wait_for_timeout(300)
    pg.evaluate("() => document.getElementById('playBtn').click()"); pg.wait_for_timeout(300)
    pg.evaluate("() => document.querySelector('#padLine .full-btn').click()"); pg.wait_for_timeout(1200)
    pg.mouse.move(40, 40); pg.mouse.move(70, 70)
    pg.evaluate("() => { const b = document.querySelector('.watch-band .watch-play'); if (b && b.getAttribute('aria-label') === 'Pause') b.click(); }")
    pg.wait_for_timeout(300)
    pg.evaluate("""() => { const tr = document.getElementById('playScrub'), r = tr.getBoundingClientRect();
        for (const t of ['pointerdown', 'pointerup', 'click']) tr.dispatchEvent(new PointerEvent(t, { bubbles: true,
          clientX: r.left + r.width * 0.985, clientY: r.top + r.height / 2, pointerId: 1, isPrimary: true })); }""")
    pg.wait_for_timeout(700)
    pg.evaluate("() => { const b = document.querySelector('.watch-band .watch-play'); if (b && b.getAttribute('aria-label') === 'Pause') b.click(); }")
    pg.wait_for_timeout(300)
    return pg, Bar(pg, ".watch-band", ".rl-drawn, .rl-m, .rl-skip", ".player-btn:not(.primary), .rl-speed, .full-btn")


def flip(b, theme):
    """Flip's own full screen on a desk: long strokes on a dark ground, the
    last along the foot, paused. Dark under a light page, where the band was a
    white fog."""
    pg = b.new_page(color_scheme=theme, **DESK)
    browsing.goto(pg, BASE, "/flip")
    pg.evaluate("() => { try { localStorage.clear(); } catch (e) {} }")
    browsing.goto(pg, BASE, "/flip")
    pg.wait_for_timeout(800)
    pg.evaluate("() => window.SkriblHints && window.SkriblHints.hide()")
    pg.evaluate("() => setBg('#0d0f14')")
    bx = pg.locator("#pad").bounding_box()
    for yy, amp, ph in ((0.45, 0.05, 0), (0.70, 0.06, 1.3), (0.94, 0.03, 0.6)):
        x0, x1 = bx["x"] + bx["width"] * 0.06, bx["x"] + bx["width"] * 0.94
        pg.mouse.move(x0, bx["y"] + bx["height"] * yy); pg.mouse.down()
        for s in range(1, 31):
            u = s / 30
            pg.mouse.move(x0 + (x1 - x0) * u, bx["y"] + bx["height"] * (yy + amp * math.sin(ph + u * 9)), steps=2)
        pg.mouse.up(); pg.wait_for_timeout(120)
    pg.evaluate("() => { if (typeof play === 'function' && !playing) play(); }"); pg.wait_for_timeout(400)
    pg.evaluate("() => document.querySelector('#flipSpeeds .full-btn').click()"); pg.wait_for_timeout(1200)
    pg.mouse.move(40, 40); pg.mouse.move(70, 70)
    pg.evaluate("() => { const b = document.querySelector('.watch-band .watch-play'); if (b && b.getAttribute('aria-label') === 'Pause') b.click(); }")
    pg.wait_for_timeout(500)
    return pg, Bar(pg, ".watch-band", ".rl-drawn, .rl-m, .rl-skip", ".player-btn:not(.primary), .full-btn")


def tones(st, which):
    return [g["tone"] for g in st["glass"] if which(g)]


# ------------------------------------------------------------------ the rows
# One part at a time, for calibrating: FULLSMART_ONLY=gallery,desk,link,pad,flip,photo
ONLY = [x for x in os.environ.get("FULLSMART_ONLY", "").split(",") if x]


def on(section):
    return not ONLY or section in ONLY


ids = {n: post(n, f"Full fade {n} {TAG}") for n in ("paper", "dark", "lines", "darklines")}
TALL = f"Full fade tall drawing {TAG}"
post("paper", TALL)

with sync_playwright() as p:
    b = p.chromium.launch()

    if on("gallery"):
        print("\nFULL SCREEN FADE — the Gallery's full screen, on a phone")
        pg, bar = gallery(b, PHONE, "dark", f"Full fade paper {TAG}")
        st = bar.state()
        moved = bar.fade_moves()
        check("Gallery, phone: a pale drawing's bar takes the drawing's colours (is-smart, no scrim)",
              st["smart"] and st["scrim"] == "none", f"{st['smart']}, {st['scrim'][:40]}")
        check("Gallery, phone: the fade cannot be seen on the drawing's empty paper (1.10 or less)",
              moved <= 1.10, f"{moved:.2f} along the bar's top row; the scrim moved it 4.9")
        worst, where, n = bar.words_worst()
        check("Gallery, phone: every word reads on the paper under it (4.5:1 or more on its worst pixel)",
              n > 20 and worst >= 4.5, f"{worst:.2f} at '{where}', {n} pixels under letters")
        tl = [w["tone"] for w in st["words"] if w["text"].startswith("0:")]
        check("Gallery, phone: the time over the paper wears the dark ink of a light ground",
              tl and all(t == "light" for t in tl), str(tl))
        pg.close()

        pg, bar = gallery(b, PHONE, "dark", f"Full fade dark {TAG}")
        worst, where, n = bar.words_worst()
        check("Gallery, phone: on a dark drawing every word reads too (4.5:1 or more)",
              n > 20 and worst >= 4.5, f"{worst:.2f} at '{where}'")
        st = bar.state()
        gl = tones(st, lambda g: True)
        check("Gallery, phone: over the dark around the drawing, the controls are dark glass",
              gl and all(t == "dark" for t in gl), str([(g["name"], g["tone"]) for g in st["glass"]]))
        pg.close()

        # Here the words sit where the fade is strong enough to carry them
        # over a line of ink alone, so this asks what the halo does under them.
        pg, bar = gallery(b, PHONE, "light", f"Full fade lines {TAG}")
        worst, where, n, bare = bar.words_worst(bare=True)
        check("Gallery, phone: over lines of ink, the words' halo lifts what is under their letters (0.5:1 or more)",
              n > 20 and worst >= 4.5 and worst - bare >= 0.5, f"{worst:.2f} at '{where}', {bare:.2f} without it")
        pg.close()

    if on("desk"):
        print("\nFULL SCREEN FADE — the Gallery on a desk: a tall drawing, narrower than the bar")
        # A pale drawing on a dark page: the title runs from the dark beside it
        # onto the paper, light on one side and dark on the other.
        WHO = ("() => { const w = document.querySelector('[data-fs-probe] .skfull-words'); return w ? { cap: w.classList.contains('cap'), "
               "tone: w.classList.contains('t-light') ? 'light' : w.classList.contains('t-dark') ? 'dark' : null } : null; }")
        pg, bar = gallery(b, DESK, "dark", TALL)
        st, who = bar.state(), pg.evaluate(WHO)
        check("Gallery, desk: the title crossing the drawing's edge sits in its capsule",
              bool(who) and who["cap"], str(who))
        worst, where, n = bar.words_worst()
        check("Gallery, desk: every word reads, the title in its capsule included (4.5:1 or more)",
              n > 20 and worst >= 4.5, f"{worst:.2f} at '{where}'")
        left = tones(st, lambda g: g["r"][2] < st["bar"][0] + 300)
        check("Gallery, desk, dark page: the controls beside the drawing are dark glass",
              left and all(t == "dark" for t in left), str(left))
        pg.evaluate("() => document.documentElement.setAttribute('data-theme', 'light')")
        pg.wait_for_timeout(400)
        st2, who2 = bar.state(), pg.evaluate(WHO)
        left2 = tones(st2, lambda g: g["r"][2] < st2["bar"][0] + 300)
        check("Gallery, desk: a theme turn turns them, light glass on the light page",
              left2 and all(t == "light" for t in left2), str(left2))
        check("Gallery, desk: on the light page the title is over light on both sides, and has no capsule",
              bool(who2) and not who2["cap"], str(who2))
        pg.close()

    if on("link"):
        print("\nFULL SCREEN FADE — a shared link's full screen")
        for view, vname in ((PHONE, "phone"), (DESK, "desk")):
            pg, bar = link(b, view, "light", ids["dark"])
            st = bar.state()
            moved = bar.fade_moves()
            check(f"Link page, {vname}, light page: a dark drawing's band is no white fog (is-smart, 1.10 or less)",
                  st["smart"] and moved <= 1.10, f"{st['smart']}, {moved:.2f}; the fog moved it 3.4")
            worst, where, n = bar.words_worst()
            check(f"Link page, {vname}: every word reads on the dark drawing (4.5:1 or more)",
                  n > 20 and worst >= 4.5, f"{worst:.2f} at '{where}'")
            pg.close()
            pg, bar = link(b, view, "dark", ids["paper"])
            st = bar.state()
            moved = bar.fade_moves()
            check(f"Link page, {vname}, dark page: a pale drawing's band is no grey band (is-smart, 1.10 or less)",
                  st["smart"] and moved <= 1.10, f"{st['smart']}, {moved:.2f}")
            worst, where, n = bar.words_worst()
            check(f"Link page, {vname}: every word reads on the paper (4.5:1 or more)",
                  n > 20 and worst >= 4.5, f"{worst:.2f} at '{where}'")
            pg.close()
        # Lines of ink right under the words: what their halo is for. Without
        # it the worst pixel read 3.7 (dark lines on paper, phone) and 3.9
        # (pale lines on a dark drawing, desk).
        for view, vname, theme, kind, what in ((PHONE, "phone", "light", "lines", "dark lines of ink on paper"),
                                               (DESK, "desk", "dark", "darklines", "pale lines on a dark drawing")):
            pg, bar = link(b, view, theme, ids[kind])
            worst, where, n = bar.words_worst()
            check(f"Link page, {vname}: every word reads over {what} running under it (4.5:1 or more)",
                  n > 20 and worst >= 4.5, f"{worst:.2f} at '{where}'")
            pg.close()

    if on("pad"):
        print("\nFULL SCREEN FADE — Pad's own full screen, on a desk")
        pg, bar = pad(b, "dark")
        st = bar.state()
        moved = bar.fade_moves()
        check("Pad: its band takes the paper's colours (is-smart, the fade unseen on the paper, 1.10 or less)",
              st["smart"] and moved <= 1.10, f"{st['smart']}, {moved:.2f}")
        worst, where, n = bar.words_worst()
        check("Pad: every word in its band reads on the drawing (4.5:1 or more)",
              n > 20 and worst >= 4.5, f"{worst:.2f} at '{where}'")
        gl = st["glass"]
        check("Pad: the band's controls over the paper are light glass",
              gl and all(g["tone"] == "light" for g in gl), str([(g["name"][:20], g["tone"]) for g in gl]))
        pg.close()

    if on("flip"):
        print("\nFULL SCREEN FADE — Flip's own full screen, on a desk")
        pg, bar = flip(b, "light")
        st = bar.state()
        moved = bar.fade_moves()
        check("Flip, light page: its dark page's band is no white fog (is-smart, 1.10 or less)",
              st["smart"] and moved <= 1.10, f"{st['smart']}, {moved:.2f}")
        pg.close()

    if on("photo"):
        print("\nFULL SCREEN FADE — a photo under the drawing keeps the scrim")
        pg, bar = pad(b, "dark", photo=True)
        st = bar.state()
        check("Pad with a photo: nothing is set on a guess (no is-smart, the scrim stands)",
              not st["smart"] and "gradient" in st["scrim"], f"{st['smart']}, {st['scrim'][:50]}")
        pg.close()
    b.close()

print("\n" + "=" * 62)
passed = sum(1 for r in results if r[0])
print(f"{passed}/{len(results)} passed" + ("" if passed == len(results) else
      "  FAILURES: " + ", ".join(r[1] for r in results if not r[0])))
sys.exit(0 if passed == len(results) else 1)
