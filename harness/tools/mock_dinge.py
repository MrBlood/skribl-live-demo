#!/usr/bin/env python3
"""NO DINGE, THE LAST FOUR, MOCKED. The four the last round left on the list
(DECISIONS.md, "The comment thread: the owner's yes (Nov 17)", STILL ON THE
LIST, from No dinge's survey), each needing more than a colour:

  pill   THE PLAY PILL on the Pad and in Flip: a 4.5% grey wash at rest that
         turns violet while playing, so a lilac at rest needs a new playing
         look. Now; A, the second button's lilac at rest; B, clear with the
         lilac edge. Playing, in both, the pressed look a lit toggle wears
         (--press-fill and --press-ring: the link page's Loop on), never solid
         violet, which on the editors is Post's.
  exit   FULL SCREEN'S X: a solid disc by the page's theme (white, or the
         toolbar's near-black), the one control in full screen that does not
         take the drawing's tone. Now; A, the bar's own glass, toned by the
         drawing under it; B, the toasts' clear glass, by the theme.
  dark   THE DARK GLASS over a dark drawing: full screen's bar and the Gallery
         card's (lib/smartfade.js's t-dark): a 14% white, grey over near-black.
         Now; A, a violet glass, its lit toggle a stronger violet with its ring.
  line   FLIP'S OWN SCRUBBER, the 3px line on its strip while it plays: a 14%
         wash. Now; A, the lilac track the Pad's line wears (--btn2-bg).

Not a suite: a tool that serves the app on a fresh database, draws through the
real editors (mouse strokes, recorded on their own clocks), posts two drawings
with card pictures (pale paper, a dark ground), and shoots each spot on the
real pages, light and dark, a touch phone (402x874) and a desk, with each
option laid over today's look as CSS (nothing in the app changes). Every
option's paint is read off the screen: its fill with its contents hidden, what
is under it with it hidden, its mark's ink, and from those the contrasts and
how colourful (OKLCH chroma) each is.

    MOCK_OUT=/tmp/dinge /tmp/skribl-venv/bin/python3 harness/tools/mock_dinge.py

writes MOCK_OUT/shots/<spot>-<where>-<light|dark>-<now|a|b>.png (2x) and
MOCK_OUT/measure.json. MOCK_ONLY=pill,exit,dark,line shoots some.
"""
import base64
import io
import json
import math
import os
import secrets
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "harness"))
import browsing  # noqa: E402

try:
    from playwright.sync_api import sync_playwright
except ImportError as exc:
    print(f"TOOL-SKIPPED: {exc}")
    raise SystemExit(77)

OUT = Path(os.environ.get("MOCK_OUT", "/tmp/dinge"))
(OUT / "shots").mkdir(parents=True, exist_ok=True)
ONLY = [x for x in os.environ.get("MOCK_ONLY", "").split(",") if x]


def want(spot):
    return not ONLY or spot in ONLY


# ---- the app's own server, on a fresh database ---------------------------------
def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


TMP = tempfile.mkdtemp(prefix="mockdinge-")
DB = os.path.join(TMP, "app.db")
LOG = os.path.join(TMP, "server.log")
PORT = free_port()
BASE = f"http://127.0.0.1:{PORT}"
ENV = dict(os.environ, DATABASE_URL=f"sqlite:///{DB}", SECRET_KEY="mock-dinge-" + secrets.token_hex(8),
           SKRIBL_STAND_IN="0", SKRIBL_RATE_MAX_POSTS="100000", SKRIBL_RATE_MAX_ATTEMPTS="100000")
for k in ("SKRIBL_SOCIAL", "SKRIBL_URL_PREFIX", "SKRIBL_FORCE_SECURE_COOKIES", "SKRIBL_DEMO_IDENTITY"):
    ENV.pop(k, None)
subprocess.run([sys.executable, "-c", "from app import app, db; app.app_context().push(); db.create_all()"],
               cwd=ROOT, env=ENV, check=True, capture_output=True, timeout=120)
_logf = open(LOG, "w")
SERVER = subprocess.Popen([sys.executable, "-m", "flask", "--app", "app", "run", "--port", str(PORT), "--no-reload"],
                          cwd=ROOT, env=ENV, stdout=_logf, stderr=subprocess.STDOUT)


def _stop():
    SERVER.terminate()
    try:
        SERVER.wait(10)
    except subprocess.TimeoutExpired:
        SERVER.kill()


import atexit  # noqa: E402
atexit.register(_stop)
for _ in range(120):
    try:
        with urllib.request.urlopen(BASE + "/api/skribls?limit=1", timeout=2) as r:
            if r.status == 200:
                break
    except Exception:  # noqa: BLE001 (not up yet)
        time.sleep(0.25)
else:
    print(f"server on {PORT} did not answer; {open(LOG).read()[-800:]}")
    raise SystemExit(1)

# A PHONE IS A TOUCH PHONE (WORKING-AGREEMENTS): is_mobile and has_touch.
PHONE = dict(viewport={"width": 402, "height": 874}, device_scale_factor=2, is_mobile=True, has_touch=True)
DESK = dict(viewport={"width": 1280, "height": 860}, device_scale_factor=2)
# Safari keeps the Fullscreen API for video: a phone's full screen is the pinned stand-in.
NO_API = """(() => { try {
  Object.defineProperty(Document.prototype, 'fullscreenEnabled', { get: () => false, configurable: true });
  Object.defineProperty(Document.prototype, 'webkitFullscreenEnabled', { get: () => false, configurable: true }); } catch (e) {}
  try { delete Element.prototype.requestFullscreen; } catch (e) {}
  try { delete Element.prototype.webkitRequestFullscreen; } catch (e) {} })();"""

# ---- the options, as CSS laid over today's ---------------------------------------
PILL = {
    "now": "",
    # A: the second button's lilac at rest, the pressed look while playing.
    "a": """
@media (min-width: 641px) {
  .play-wrap, .flip-play-wrap { background: var(--btn2-bg) !important; border-color: transparent !important; }
  .play-wrap:has(.btn.playing), .flip-play-wrap:has(.btn.playing) { background: var(--press-fill) !important;
    box-shadow: inset 0 0 0 1px var(--press-ring) !important; }
  .play-wrap:has(.btn.playing) > .btn.playing { background: transparent !important; color: var(--seg-on-ink) !important; }
}
@media (max-width: 640px) {
  .play-wrap > .btn:is(.play, .flip-play) { background: var(--btn2-bg) !important; border-color: transparent !important; }
  .play-wrap > .btn:is(.play, .flip-play).playing { background: var(--press-fill) !important;
    box-shadow: inset 0 0 0 1px var(--press-ring) !important; color: var(--seg-on-ink) !important; }
}""",
    # B: clear, with the clear glass's lilac edge, at rest; the pressed look while playing.
    "b": """
@media (min-width: 641px) {
  .play-wrap, .flip-play-wrap { background: transparent !important; border-color: var(--chip-line) !important; }
  .play-wrap:has(.btn.playing), .flip-play-wrap:has(.btn.playing) { background: var(--press-fill) !important;
    border-color: transparent !important; box-shadow: inset 0 0 0 1px var(--press-ring) !important; }
  .play-wrap:has(.btn.playing) > .btn.playing { background: transparent !important; color: var(--seg-on-ink) !important; }
}
@media (max-width: 640px) {
  .play-wrap > .btn:is(.play, .flip-play) { background: transparent !important; border-color: var(--chip-line) !important; }
  .play-wrap > .btn:is(.play, .flip-play).playing { background: var(--press-fill) !important; border-color: transparent !important;
    box-shadow: inset 0 0 0 1px var(--press-ring) !important; color: var(--seg-on-ink) !important; }
}""",
}
GLASS_LIGHT = """color: var(--on-canvas-violet) !important; border-color: rgba(255, 255, 255, 0.9) !important;
  background: rgba(255, 255, 255, 0.68) !important;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.9), 0 3px 12px rgba(var(--on-canvas-drop-rgb), 0.14) !important;
  -webkit-backdrop-filter: blur(12px) saturate(1.6); backdrop-filter: blur(12px) saturate(1.6);"""
GLASS_DARK = """color: #fff !important; border-color: rgba(255, 255, 255, 0.26) !important;
  background: rgba(255, 255, 255, 0.14) !important;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.25), 0 3px 12px rgba(var(--on-canvas-drop-rgb), 0.4) !important;
  -webkit-backdrop-filter: blur(12px) saturate(1.6); backdrop-filter: blur(12px) saturate(1.6);"""
EXIT = {
    "now": "",
    # A: the bar's own glass, toned by what is under it (the class is set by the
    # drawing under the X, read off the screen, as lib/smartfade.js tones the bar).
    "a": f".player-btn.full-exit.t-light {{ {GLASS_LIGHT} }}\n.player-btn.full-exit.t-dark {{ {GLASS_DARK} }}",
    # B: the toasts' clear glass, by the page's theme.
    "b": """.player-btn.full-exit { background: var(--chip-glass) !important; border-color: var(--chip-line) !important;
  box-shadow: var(--chip-lift) !important; color: var(--text-primary) !important;
  -webkit-backdrop-filter: blur(8px); backdrop-filter: blur(8px); }""",
}
VIOLET = """background: rgba(124, 92, 255, 0.30) !important; border-color: rgba(201, 188, 255, 0.42) !important;
  color: #fff !important; box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.18), 0 3px 12px rgba(var(--on-canvas-drop-rgb), 0.4) !important;"""
VIOLET_LIT = """background: rgba(124, 92, 255, 0.62) !important; border-color: #c9bcff !important; color: #fff !important;"""
DARK = {
    "now": "",
    # A: the dark glass violet; a lit toggle on it a stronger violet, ringed.
    "a": f"""
.player-bar.is-smart :is(.player-btn, .rl-speed, .full-btn).t-dark, .player-bar.is-smart .rl-repeat.t-dark,
.skfull.is-smart .skfull-btn.t-dark {{ {VIOLET} }}
.player-bar.is-smart :is(.player-btn.active, .full-btn[aria-pressed="true"]).t-dark,
.skfull.is-smart .skfull-loop.on.t-dark {{ {VIOLET_LIT} }}
.player-bar.is-smart .rl-repeat[aria-pressed="true"].t-dark {{ background: rgba(124, 92, 255, 0.62) !important;
  box-shadow: inset 0 0 0 1px #c9bcff, 0 3px 12px rgba(var(--on-canvas-drop-rgb), 0.4) !important; }}""",
}
EXIT["a2"] = (EXIT["a"].split(".player-btn.full-exit.t-dark")[0]
              + ".player-btn.full-exit.t-dark { " + VIOLET
              + " -webkit-backdrop-filter: blur(12px) saturate(1.6); backdrop-filter: blur(12px) saturate(1.6); }")
LINE = {
    "now": "",
    "a": "body.playing .flip-timeline { background: var(--btn2-bg) !important; }",
}


def lay(pg, css):
    """Lay one option's CSS over the page (replacing the last)."""
    pg.evaluate("""css => { let s = document.getElementById('mockopt');
      if (!s) { s = document.createElement('style'); s.id = 'mockopt'; document.head.appendChild(s); }
      s.textContent = css; }""", css)
    frames(pg, 3)


def frames(pg, n=2):
    pg.evaluate(f"() => new Promise(r => {{ let k = {n}; const f = () => (--k ? requestAnimationFrame(f) : r()); requestAnimationFrame(f); }})")


# ---- reading the paint ------------------------------------------------------------
def _lin(c):
    c /= 255
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def lum(p):
    return 0.2126 * _lin(p[0]) + 0.7152 * _lin(p[1]) + 0.0722 * _lin(p[2])


def ratio(a, b):
    la, lb = lum(a), lum(b)
    return round((max(la, lb) + 0.05) / (min(la, lb) + 0.05), 2)


def chroma(p):
    """OKLCH chroma: 0 is grey; the lilac is about 0.04 light, 0.08 dark."""
    r, g, b = (_lin(v) for v in p[:3])
    l_ = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    m_ = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    s_ = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b
    l_, m_, s_ = (math.copysign(abs(v) ** (1 / 3), v) for v in (l_, m_, s_))
    a = 1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_
    bb = 0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_
    return round(math.hypot(a, bb), 3)


HIDE = """
[data-mk] > *, [data-mk] svg { visibility: hidden !important; }
[data-mk], [data-mk] * { color: transparent !important; text-shadow: none !important; }
[data-mg] { visibility: hidden !important; }
"""


def median(im):
    px = list(getattr(im, "get_flattened_data", im.getdata)())
    return tuple(sorted(c[i] for c in px)[len(px) // 2] for i in range(3))


def rect(pg, sel):
    return pg.evaluate("""s => { const e = typeof s === 'string' ? document.querySelector(s) : s; if (!e) return null;
      const r = e.getBoundingClientRect(); return { x: r.left, y: r.top, w: r.width, h: r.height }; }""", sel)


def read(pg, sel, inset=0.3, where=None):
    """The paint of `sel`: its own fill (its contents hidden), what is under it
    (it hidden), and its mark's ink (its computed colour), read off the middle
    of its box (`inset` of each side away from its edge; or `where`, a box)."""
    r = where or rect(pg, sel)
    if not r:
        return None
    clip = {"x": r["x"] + r["w"] * inset, "y": r["y"] + r["h"] * inset,
            "width": max(1, r["w"] * (1 - 2 * inset)), "height": max(1, r["h"] * (1 - 2 * inset))}
    pg.evaluate("""([s, css]) => { let st = document.getElementById('mockhide'); if (!st) { st = document.createElement('style');
      st.id = 'mockhide'; document.head.appendChild(st); } st.textContent = css; document.querySelector(s).setAttribute('data-mk', ''); }""", [sel, HIDE])
    frames(pg)
    fill = median(Image.open(io.BytesIO(pg.screenshot(clip=clip))).convert("RGB"))
    pg.evaluate("s => { const e = document.querySelector(s); e.removeAttribute('data-mk'); e.setAttribute('data-mg', ''); }", sel)
    frames(pg)
    under = median(Image.open(io.BytesIO(pg.screenshot(clip=clip))).convert("RGB"))
    pg.evaluate("s => { document.querySelector(s).removeAttribute('data-mg'); document.getElementById('mockhide').textContent = ''; }", sel)
    frames(pg)
    ink = pg.evaluate("""s => { const e = document.querySelector(s), m = e.querySelector('svg') || e;
      const c = getComputedStyle(m).color; return c.match(/[\\d.]+/g).slice(0, 3).map(Number); }""", sel)
    return {"fill": fill, "under": under, "ink": tuple(int(v) for v in ink),
            "fill_vs_under": ratio(fill, under), "ink_vs_fill": ratio(tuple(int(v) for v in ink), fill),
            "chroma": chroma(fill)}


def shot(pg, name, box, pad=0):
    vw, vh = pg.viewport_size["width"], pg.viewport_size["height"]
    x0, y0 = max(0, box["x"] - pad), max(0, box["y"] - pad)
    x1, y1 = min(vw, box["x"] + box["w"] + pad), min(vh, box["y"] + box["h"] + pad)
    pg.screenshot(path=str(OUT / "shots" / f"{name}.png"), clip={"x": x0, "y": y0, "width": x1 - x0, "height": y1 - y0})


MEASURE = {}


def keep(key, value):
    MEASURE[key] = value
    print(f"  {key}: {json.dumps(value)}", flush=True)


# ---- drawing through the editors ------------------------------------------------------
def strokes_on(pg, sel, rows=((0.30, 0.05, 0.0), (0.52, 0.06, 1.3), (0.74, 0.04, 0.6))):
    """Long strokes across the canvas, as a hand makes them (the editor records
    them on its own clock)."""
    bx = pg.locator(sel).bounding_box()
    for yy, amp, ph in rows:
        x0, x1 = bx["x"] + bx["width"] * 0.1, bx["x"] + bx["width"] * 0.9
        pg.mouse.move(x0, bx["y"] + bx["height"] * yy)
        pg.mouse.down()
        for s in range(1, 41):
            u = s / 40
            pg.mouse.move(x0 + (x1 - x0) * u, bx["y"] + bx["height"] * (yy + amp * math.sin(ph + u * 9)), steps=2)
            pg.wait_for_timeout(14)
        pg.mouse.up()
        pg.wait_for_timeout(150)


def fresh(pg, path):
    browsing.goto(pg, BASE, path)
    pg.evaluate("() => { try { localStorage.clear(); } catch (e) {} }")
    browsing.goto(pg, BASE, path)
    pg.wait_for_timeout(900)
    pg.evaluate("() => window.SkriblHints && window.SkriblHints.hide()")


def pad_ready(b, theme, view):
    pg = b.new_page(color_scheme=theme, **view)
    fresh(pg, "/skribl-pad")
    strokes_on(pg, "#canvas")
    pg.evaluate("() => { if (typeof endRecordingTake === 'function' && recording) endRecordingTake(); }")
    pg.wait_for_timeout(500)
    return pg


def flip_ready(b, theme, view):
    """A Flip of two pages: Play shows once there is a second page."""
    pg = b.new_page(color_scheme=theme, **view)
    fresh(pg, "/flip")
    strokes_on(pg, "#pad")
    pg.evaluate("() => { const b = [...document.querySelectorAll('button')].find(x => /Duplicate/.test(x.textContent) && x.getClientRects().length); if (b) b.click(); }")
    pg.wait_for_timeout(500)
    strokes_on(pg, "#pad", rows=((0.42, 0.08, 2.0),))
    pg.wait_for_timeout(400)
    return pg


# ---- the posted drawings: pale paper and a dark ground, each with its card picture ----------
W, H = 402, 760
GROUND = {"paper": "#f6f2ea", "dark": "#0f1014"}
TAG = secrets.token_hex(2)


def _pts(name):
    out, t = [], [0]

    def stroke(fn, n, color, base):
        for i in range(n):
            u = i / (n - 1)
            x, y = fn(u)
            out.append({"x": round(x, 1), "y": round(y, 1), "color": color, "t": t[0], "start": i == 0,
                        "size": round(base * (0.35 + 0.8 * math.sin(math.pi * u) ** 0.8), 2)})
            t[0] += 14
        t[0] += 200

    if name == "paper":      # a hill with its sun in the top corner, grass through the foot
        stroke(lambda u: (-10 + 422 * u, 590 - 120 * math.sin(math.pi * u) ** 1.4), 60, "#2a2340", 9)
        stroke(lambda u: (330 + 40 * math.cos(u * 2 * math.pi), 60 + 40 * math.sin(u * 2 * math.pi)), 50, "#e0703a", 7)
        for k in range(9):
            stroke(lambda u, k=k: (20 + k * 44 + 8 * u, 740 - 70 * u), 12, "#2f7d4f", 6)
    else:                    # a moon in the top corner, waves through the foot
        stroke(lambda u: (330 + 34 * math.cos(u * 2 * math.pi), 64 + 34 * math.sin(u * 2 * math.pi)), 50, "#c9bcff", 6)
        for k, c in enumerate(["#7c5cff", "#a593ff", "#c9bcff"]):
            stroke(lambda u, k=k: (-10 + 422 * u, 610 + k * 52 + 20 * math.sin(u * 9 + k)), 60, c, 11 - 2 * k)
    return out


def _card(name, pts):
    """The post's card picture, as lib/sharecard.js lays a drawing on it."""
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


def post(name):
    pts = _pts(name)
    groups, n = [], 0
    for i, p in enumerate(pts):
        if p["start"] and i:
            groups.append(n)
            n = 0
        n += 1
    groups.append(n)
    body = {"title": f"Dinge {name} {TAG}", "version": 2, "schemaVersion": 2, "visibility": "public",
            "playbackMode": "replay", "canvasSize": {"cssWidth": W, "cssHeight": H},
            "frames": [{"strokes": pts, "strokeGroups": groups, "background": {"color": GROUND[name]}}],
            "thumbnail": _card(name, pts)}
    req = urllib.request.Request(BASE + "/api/skribls", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=30).read())["id"]


def link_full(b, theme, sid):
    """A posted drawing's link page in full screen on a phone, paused at its end."""
    pg = b.new_page(color_scheme=theme, **PHONE)
    pg.add_init_script(NO_API)
    browsing.goto(pg, BASE, "/s/" + sid)
    pg.wait_for_timeout(1000)
    pg.evaluate("() => document.getElementById('playerFullBtn').click()")
    pg.wait_for_timeout(1200)
    pause = "() => { const b = document.getElementById('playerPlayBtn'); if (b.getAttribute('aria-label') === 'Pause') b.click(); }"
    pg.evaluate(pause)
    pg.wait_for_timeout(300)
    pg.evaluate("""() => { const tr = document.getElementById('playerProgress'), r = tr.getBoundingClientRect();
        for (const t of ['pointerdown', 'pointerup', 'click']) tr.dispatchEvent(new PointerEvent(t, { bubbles: true,
          clientX: r.left + r.width * 0.995, clientY: r.top + r.height / 2, pointerId: 1, isPrimary: true })); }""")
    pg.wait_for_timeout(700)
    pg.evaluate(pause)
    pg.wait_for_timeout(400)
    pg.add_style_tag(content=".player-nib { visibility: hidden !important; } .chrome-asleep :is(.player-bar, .player-btn.full-exit) { opacity: 1 !important; }")
    return pg


def tone_exit(pg):
    """Tone the X by what is under it, as the bar's controls are toned: the
    ground under it read with it hidden; dark where white ink reads better."""
    r = rect(pg, ".player-btn.full-exit")
    clip = {"x": r["x"], "y": r["y"], "width": r["w"], "height": r["h"]}
    pg.evaluate("() => document.querySelector('.player-btn.full-exit').style.visibility = 'hidden'")
    frames(pg)
    under = median(Image.open(io.BytesIO(pg.screenshot(clip=clip))).convert("RGB"))
    pg.evaluate("() => document.querySelector('.player-btn.full-exit').style.visibility = ''")
    dark = ratio((255, 255, 255), under) >= ratio((17, 22, 30), under)
    pg.evaluate("d => { const e = document.querySelector('.player-btn.full-exit'); e.classList.toggle('t-dark', d); e.classList.toggle('t-light', !d); }", dark)
    frames(pg)
    return "dark" if dark else "light"


# ---- the spots -------------------------------------------------------------------------
def spot_pill(b):
    print("\nTHE PLAY PILL", flush=True)
    for theme in ("light", "dark"):
        for where, view in (("phone", PHONE), ("desk", DESK)):
            for ed, ready, sel in (("pad", pad_ready, "#playWrap"), ("flip", flip_ready, "#flipPlayWrap")):
                pg = ready(b, theme, view)
                btn = sel + " > .btn"
                target = sel if where == "desk" else btn
                for state in ("rest", "playing"):
                    if state == "playing":
                        pg.evaluate("s => document.querySelector(s).click()", btn)
                        pg.wait_for_timeout(700)
                    hdr = rect(pg, sel)
                    more = rect(pg, "#moreBtn") or rect(pg, "#menuBtn")
                    box = {"x": hdr["x"] - 20, "y": hdr["y"] - 14, "w": (more["x"] + more["w"] + 14) - (hdr["x"] - 20), "h": hdr["h"] + 28}
                    if where == "phone":
                        box = {"x": 0, "y": hdr["y"] - 14, "w": 402, "h": hdr["h"] + 28}
                    for opt, css in PILL.items():
                        lay(pg, css)
                        shot(pg, f"pill-{ed}-{where}-{state}-{theme}-{opt}", box)
                        m = read(pg, target, inset=0.18 if where == "phone" else 0.3)
                        keep(f"pill/{ed}/{where}/{state}/{theme}/{opt}", m)
                lay(pg, "")
                pg.close()


def spot_exit(b, ids):
    print("\nFULL SCREEN'S X", flush=True)
    for theme in ("light", "dark"):
        for name in ("paper", "dark"):
            pg = link_full(b, theme, ids[name])
            tone = tone_exit(pg)
            r = rect(pg, ".player-btn.full-exit")
            for opt, css in EXIT.items():
                lay(pg, css)
                shot(pg, f"exit-{name}-{theme}-{opt}", {"x": 0, "y": 0, "w": 402, "h": 210})
                keep(f"exit/{name}/{theme}/{opt}", {**read(pg, ".player-btn.full-exit", inset=0.12), "tone": tone})
            lay(pg, "")
            pg.close()


def spot_dark(b, ids):
    print("\nTHE DARK GLASS", flush=True)
    for theme in ("light", "dark"):
        # full screen's bar over the dark drawing
        pg = link_full(b, theme, ids["dark"])
        bar = rect(pg, "#playerBar")
        for opt, css in DARK.items():
            lay(pg, css)
            shot(pg, f"dark-full-{theme}-{opt}", {"x": 0, "y": bar["y"] - 24, "w": 402, "h": 874 - (bar["y"] - 24)})
            for nm, sel in (("restart", "#playerBar .player-btn[aria-label='Restart']"),
                            ("loop", "#playerBar .player-btn[aria-label*='oop']")):
                if pg.evaluate("s => !!document.querySelector(s)", sel):
                    keep(f"dark/full/{nm}/{theme}/{opt}", read(pg, sel, inset=0.12))
        # Loop on: a lit toggle on the glass
        lay(pg, "")
        lit = pg.evaluate("""() => { const b = document.querySelector("#playerBar .player-btn[aria-label*='oop']");
          if (!b) return null; if (!b.classList.contains('active')) b.click(); return b.classList.contains('active'); }""")
        pg.wait_for_timeout(300)
        for opt, css in DARK.items():
            lay(pg, css)
            shot(pg, f"dark-lit-{theme}-{opt}", {"x": 0, "y": bar["y"] - 24, "w": 402, "h": 874 - (bar["y"] - 24)})
            if lit:
                keep(f"dark/lit/{theme}/{opt}", read(pg, "#playerBar .player-btn[aria-label*='oop']", inset=0.12))
        lay(pg, "")
        pg.close()
        # the Gallery card's bar over the dark drawing
        pg = b.new_page(color_scheme=theme, **PHONE)
        browsing.goto(pg, BASE, "/gallery")
        pg.wait_for_timeout(1500)
        tile = pg.locator(".tile", has_text=f"Dinge dark {TAG}").first
        tile.scroll_into_view_if_needed()
        pg.wait_for_timeout(400)
        tile.locator(".skribl-inline").first.tap()
        pg.wait_for_timeout(900)
        tile.evaluate("t => t.classList.add('ctl-on')")
        tile.locator(".skfull-card .skfull-play").first.click()
        pg.wait_for_timeout(250)
        tile.evaluate("""t => { const tr = t.querySelector('.skfull-card .skfull-track'), r = tr.getBoundingClientRect();
          tr.dispatchEvent(new MouseEvent('click', { bubbles: true, clientX: r.right - 0.5, clientY: r.top + r.height / 2 })); }""")
        pg.wait_for_timeout(700)
        tile.evaluate("t => { t.classList.add('ctl-on'); t.setAttribute('data-mock-tile', ''); }")
        try:
            pg.wait_for_function("() => document.querySelector('[data-mock-tile] .skfull.skfull-card').classList.contains('is-smart')", timeout=8000)
        except Exception:  # noqa: BLE001 (the shot says what was painted)
            print("  (the card's bar did not read its drawing in 8s)")
        st = rect(pg, "[data-mock-tile] .tileStage") or rect(pg, "[data-mock-tile] .skribl-inline")
        for opt, css in DARK.items():
            lay(pg, css)
            shot(pg, f"dark-card-{theme}-{opt}", {"x": st["x"], "y": st["y"] + st["h"] - 150, "w": st["w"], "h": 150}, pad=6)
            for nm, sel in (("loop", "[data-mock-tile] .skfull-card .skfull-loop"), ("full", "[data-mock-tile] .skfull-card .skfull-full")):
                keep(f"dark/card/{nm}/{theme}/{opt}", read(pg, sel, inset=0.12))
        lay(pg, "")
        pg.close()


def spot_line(b):
    print("\nFLIP'S SCRUB LINE", flush=True)
    for theme in ("light", "dark"):
        for where, view in (("phone", PHONE), ("desk", DESK)):
            pg = flip_ready(b, theme, view)
            pg.evaluate("() => document.querySelector('#flipPlayWrap > .btn').click()")
            pg.wait_for_timeout(250)
            tl = rect(pg, ".flip-timeline")
            strip = rect(pg, ".strip-wrap")
            box = {"x": strip["x"], "y": tl["y"] - 26, "w": strip["w"], "h": 84}
            # One moment for every shot: the fill held at 45% (a rule, which the
            # player's own inline width cannot outrank).
            hold = "#flipProgressFill { width: 45% !important; transition: none !important; }"
            for opt, css in LINE.items():
                lay(pg, css + hold)
                shot(pg, f"line-{where}-{theme}-{opt}", box)
                # the track's own paint, read at its far end, where no fill has reached
                far = {"x": tl["x"] + tl["w"] * 0.80, "y": tl["y"], "w": tl["w"] * 0.12, "h": tl["h"]}
                m = read(pg, ".flip-timeline", inset=0.0, where=far)
                fill = pg.evaluate("() => getComputedStyle(document.getElementById('flipProgressFill')).backgroundColor.match(/[\\d.]+/g).slice(0, 3).map(Number)")
                m["bar"] = tuple(int(v) for v in fill)
                m["bar_vs_track"] = ratio(m["bar"], m["fill"])
                keep(f"line/{where}/{theme}/{opt}", m)
            lay(pg, "")
            pg.close()


def main():
    ids = {k: post(k) for k in ("paper", "dark")}
    print("posted", ids, flush=True)
    with sync_playwright() as p:
        b = p.chromium.launch()
        if want("pill"):
            spot_pill(b)
        if want("exit"):
            spot_exit(b, ids)
        if want("dark"):
            spot_dark(b, ids)
        if want("line"):
            spot_line(b)
        b.close()
    (OUT / "measure.json").write_text(json.dumps(MEASURE, indent=1))
    print(f"\n{len(MEASURE)} readings; shots in {OUT / 'shots'}")


if __name__ == "__main__":
    main()
