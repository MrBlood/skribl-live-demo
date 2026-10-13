#!/usr/bin/env python3
"""Every full screen puts its controls away while a drawing plays: the link
page, the Gallery and the Library, on a phone and on a desk.

THE OWNER, at the full-screen mock: the controls step back a moment after the
drawing starts and come back when the mouse moves or a finger taps ("I like
your picks"), and "make the first tap on a faded phone just reveal the
controls without pausing, matching how video apps work". The editors took it
first (verify_parity, "full screen while it plays"); this asks the same of the
three surfaces that show a posted drawing. All of them use one module,
lib/chromefade.js, so they are asked in the same words.

WHAT IS ASKED, ON EACH SURFACE AND SCREEN
  * The drawing has the whole screen: nothing is kept under it for the bar,
    which lies over its foot while it is up. (The link page and the Gallery.
    The Library frames its drawing in its own 16:9 box, which is its own
    question.)
  * After a quiet spell while it plays, the bar and the x are not on screen,
    and the drawing plays on.
  * Paused from somewhere other than the screen -- a key, a remote -- they come
    back: the surface tells the fade its state changed.
  * A finger's first tap on the drawing brings them back and does not pause
    it. On a desk a mouse's move does that, and its click is a pause.
  * With them up, the next tap pauses, as it does on the page.
  * Paused, they stay up past the next quiet spell.

VISIBLE MEANS PAINTED. A faded control keeps its rect, so each one is asked of
elementFromPoint at a point inside it (WORKING-AGREEMENTS, "a rect is not a
paint").

THE PHONE IS THE OWNER'S, 402x874, with the Fullscreen API taken away as
Safari has it for anything but a video, so the pinned stand-in is what goes
full screen there. The desk has the real API.
"""
import json
import math
import os
import sys
import urllib.request

from assertions import make_check
import browsing

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("SKIP: playwright is not installed")
    sys.exit(0)

BASE = os.environ.get("SKRIBL_BASE", "http://127.0.0.1:5001")
results = []
check = make_check(results, with_detail=True)

PHONE = dict(viewport={"width": 402, "height": 874}, device_scale_factor=2, is_mobile=True, has_touch=True)
DESK = dict(viewport={"width": 1333, "height": 906})
NO_API = """(() => { try {
  Object.defineProperty(Document.prototype, 'fullscreenEnabled', { get: () => false, configurable: true });
  Object.defineProperty(Document.prototype, 'webkitFullscreenEnabled', { get: () => false, configurable: true }); } catch (e) {}
  try { delete Element.prototype.requestFullscreen; } catch (e) {}
  try { delete Element.prototype.webkitRequestFullscreen; } catch (e) {} })();"""
QUIET_MS = 3300          # past lib/chromefade.js's 2.5 s and its 0.35 s fade


def post():
    """Six rings of 60 points, 25 ms apart: about nine seconds of drawing, long
    enough to play through two quiet spells. Public, so the Gallery lists it."""
    pts = []
    for k in range(6):
        for i in range(60):
            a = i / 59 * math.pi * 2
            pts.append({"x": 408 + math.cos(a) * (60 + k * 40), "y": 306 + math.sin(a) * (40 + k * 30),
                        "color": "#7c5cff", "size": 10, "t": (k * 60 + i) * 25, "start": i == 0})
    body = {"title": "Steps back", "version": 2, "schemaVersion": 2, "visibility": "public",
            "playbackMode": "replay", "frames": [{"strokes": pts, "strokeGroups": [60] * 6}],
            "canvasSize": {"cssWidth": 816, "cssHeight": 612}}
    req = urllib.request.Request(BASE + "/api/skribls", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode())


# What is painted, asked of the root's own controls. `null` is a control that
# is not there at all, which no row accepts as "away".
STATE = """([root, bar, x, cv]) => {
  const w = document.querySelector(root);
  const painted = sel => { const el = w && w.querySelector(sel); if (!el) return null;
    const r = el.getBoundingClientRect(); if (!r.width || !r.height) return false;
    const h = document.elementFromPoint(r.left + r.width / 2, r.top + Math.min(r.height / 2, 20));
    return !!(h && el.contains(h)); };
  const c = w && w.querySelector(cv), cr = c ? c.getBoundingClientRect() : null;
  return { asleep: !!(w && w.classList.contains('chrome-asleep')), bar: painted(bar), x: painted(x),
           pad: w ? getComputedStyle(w).paddingBottom : null, vw: innerWidth, vh: innerHeight,
           canvas: cr && [cr.left, cr.top, cr.width, cr.height].map(Math.round) }; }"""


# Each surface: where it lives, how a drawing gets playing in full screen,
# its root, drawing, bar and x, and how it says (and is told) play and pause
# without a touch on the screen.
def link_in(pg, fx):
    browsing.goto(pg, BASE, "/s/" + fx["id"])
    pg.click("#playerPlayBtn")
    pg.wait_for_timeout(300)
    pg.click("#playerFullBtn")
    pg.wait_for_timeout(700)


def gallery_in(pg, fx):
    browsing.goto(pg, BASE, "/gallery")
    pg.wait_for_selector(f"[data-skribl-id='{fx['id']}']", timeout=10000)
    # Full screen PLAYS it there (gallery.js onFs); its footer's button is the way in.
    pg.evaluate("""(id) => { const t = document.querySelector(`[data-skribl-id='${id}']`).closest('.tileStage');
        t.setAttribute('data-fade-probe', ''); t.scrollIntoView({ block: 'center' });
        t.querySelector('.skfull-full').click(); }""", fx["id"])
    pg.wait_for_timeout(1200)


def library_in(pg, fx):
    browsing.goto(pg, BASE, "/library")
    pg.evaluate("""(e) => localStorage.setItem('skribl_posted_v1', JSON.stringify([{ id: e.id, url: e.url,
        title: 'Steps back', kind: 'pad', pages: 1, visibility: 'public', tok: e.deleteToken,
        local: false, has_audio: false, at: Date.now() }]))""", fx)
    browsing.goto(pg, BASE, "/library")
    pg.wait_for_function("() => !document.getElementById('btnFull').disabled", timeout=10000)
    pg.evaluate("() => document.getElementById('btnFull').click()")
    pg.wait_for_timeout(700)
    pg.evaluate("() => document.querySelector('.stageCanvasWrap .skfull:not(.skfull-card) .skfull-play').click()")
    pg.wait_for_timeout(500)


INLINE = "document.querySelector('{root} .skribl-inline')._skriblInline"
SURFACES = [
    ("The link page", link_in, ".canvas-wrap", "#playerBar", "#playerFullExit", ".canvas-wrap > canvas",
     "() => document.getElementById('playerPlayBtn').getAttribute('aria-label') === 'Pause'",
     "() => document.getElementById('playerPlayBtn').click()", True),
    ("The Gallery", gallery_in, "[data-fade-probe]", ".skfull:not(.skfull-card)", ".tileExit",
     ".skribl-inline-canvas",
     "() => " + INLINE.format(root="[data-fade-probe]") + ".state().state === 'playing'",
     "() => " + INLINE.format(root="[data-fade-probe]") + ".toggle()", True),
    ("The Library", library_in, ".stageCanvasWrap", ".skfull:not(.skfull-card)", "#fullExit",
     ".skribl-inline-canvas",
     "() => " + INLINE.format(root=".stageCanvasWrap") + ".state().state === 'playing'",
     "() => " + INLINE.format(root=".stageCanvasWrap") + ".toggle()", False),
]


def walk(b, fx, name, go_in, root, bar, x, cv, playing, toggle, whole, finger):
    who = f"{name} ({'phone' if finger else 'desk'})"
    ctx = b.new_context(**(PHONE if finger else DESK))
    pg = ctx.new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    if finger:
        pg.add_init_script(NO_API)
    go_in(pg, fx)
    sel = [root, bar, x, cv]
    st = lambda: dict(pg.evaluate(STATE, sel), playing=pg.evaluate(playing))   # noqa: E731
    first = st()
    if whole:
        # The fit: the authored 816x612 as big as the screen lets it be. The
        # Gallery's canvas is its box (object-fit: contain), so its whole box
        # is asked of instead.
        if name == "The link page":
            fit = round(min(first["vw"] / 816, first["vh"] / 612) * 816)
            big = abs(first["canvas"][2] - fit) <= 1
        else:
            big = first["canvas"][2] == first["vw"] and first["canvas"][3] == first["vh"]
        check(f"{who}: in full screen the drawing has the whole screen, nothing kept under it for the bar",
              big and first["pad"] == "0px" and first["bar"] and first["playing"], str(first))
    if not finger:
        pg.mouse.move(2, 2)            # parked: a mouse that has not moved since
    pg.wait_for_timeout(QUIET_MS)
    quiet = st()
    check(f"{who}: after a quiet spell while it plays, the bar and the x are away and it plays on",
          quiet["asleep"] and quiet["bar"] is False and quiet["x"] is False and quiet["playing"], str(quiet))
    pg.evaluate(toggle)                # paused by something other than the screen
    pg.wait_for_timeout(400)
    told = st()
    check(f"{who}: paused from elsewhere while they are away, they come back",
          not told["asleep"] and told["bar"] and not told["playing"], str(told))
    pg.evaluate(toggle)
    pg.wait_for_timeout(QUIET_MS)      # playing again, and away again
    c = told["canvas"]
    px, py = c[0] + c[2] / 2, c[1] + c[3] / 3     # on the drawing, above the bar's band
    if finger:
        pg.touchscreen.tap(px, py)
    else:
        pg.mouse.move(px, py)
    pg.wait_for_timeout(400)
    woke = st()
    check(f"{who}: " + ("a finger's first tap on the drawing brings them back and does not pause it"
                        if finger else "a mouse that moves over the drawing brings them back"),
          not woke["asleep"] and woke["bar"] and woke["playing"], str(woke))
    if finger:
        pg.touchscreen.tap(px, py)
    else:
        pg.mouse.click(px, py)
    pg.wait_for_timeout(400)
    pressed = st()
    check(f"{who}: with them up, " + ("the next tap pauses" if finger else "a click pauses"),
          not pressed["playing"], str(pressed))
    if not finger:
        pg.mouse.move(2, 2)
    pg.wait_for_timeout(QUIET_MS)
    later = st()
    check(f"{who}: paused, they stay up past the next quiet spell",
          not later["asleep"] and later["bar"] and not later["playing"], str(later))
    check(f"{who}: no page errors", not errs, "; ".join(errs[:2]))
    ctx.close()


print("\nFULL SCREEN STEPS BACK — the link page, the Gallery and the Library")
with sync_playwright() as p:
    b = p.chromium.launch()
    fx = post()
    for name, go_in, root, bar, x, cv, playing, toggle, whole in SURFACES:
        for finger in (True, False):
            walk(b, fx, name, go_in, root, bar, x, cv, playing, toggle, whole, finger)
    b.close()

print("\n" + "=" * 62)
passed = sum(1 for r in results if r[0])
print(f"{passed}/{len(results)} passed" + ("" if passed == len(results) else
      "  FAILURES: " + ", ".join(r[1] for r in results if not r[0])))
sys.exit(0 if passed == len(results) else 1)
