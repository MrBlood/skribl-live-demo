#!/usr/bin/env python3
"""Every full screen puts its controls away while a drawing plays: the link
page, the Gallery and the Library, on a phone and on a desk.

THE OWNER, at the full-screen mock: the controls step back a moment after the
drawing starts and come back when the mouse moves or a finger taps ("I like
your picks"), and "make the first tap on a faded phone just reveal the
controls without pausing, matching how video apps work". The editors took it
first (verify_watchfull, once a section of verify_parity); this asks the same
of the three surfaces that show a posted drawing. All of them use one module,
lib/chromefade.js, so they are asked in the same words.

WHAT IS ASKED, ON EACH SURFACE AND SCREEN
  * The drawing has the whole screen: nothing is kept under it for the bar,
    which lies over its foot while it is up. On the Library too, which used
    to frame its drawing in a 16:9 box at a fraction of the screen.
  * After a quiet spell while it plays, the bar and the x are not on screen,
    and the drawing plays on.
  * Paused from somewhere other than the screen -- a key, a remote -- they come
    back: the surface tells the fade its state changed.
  * A finger's first tap on the drawing brings them back and does not pause
    it. On a desk a mouse's move does that, and its click is a pause.
  * With them up, the next tap pauses, as it does on the page.
  * Paused, they stay up past the next quiet spell.
  * Watched to its end with repeat off, they come up as it ends, then step
    back after a quiet spell like any other, so the finished drawing is seen
    whole (the owner, after the full-screen A/B: the drawing fills the screen,
    so when they are up they lie over its foot). A first tap or a move brings
    them back without starting it again, and a scrub back from there is a
    pause like any other: finished means stopped AT THE END, not stopped
    after playing.
  * On the link page, a short drawing that repeats keeps them away from lap
    to lap. Every lap used to bring them back, which on a drawing shorter
    than the quiet spell meant they never left.

THE CLOCK CLEARS THE PLAYHEAD, asked here because this suite opens the link
page's full screen on both screens: at a drawing's end the scrubber's head,
which pokes past its bar with a ring, sat on the last digit of the clock under
it. Asked of what each one paints, not of their boxes.

VISIBLE MEANS PAINTED. A faded control keeps its rect, so each one is asked of
elementFromPoint at a point inside it (WORKING-AGREEMENTS, "a rect is not a
paint").

THE PHONE IS THE OWNER'S, 402x874, with the Fullscreen API taken away as
Safari has it for anything but a video, so the pinned stand-in is what goes
full screen there. The desk has the real API.
"""
import io
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


def post(rings=6):
    """Six rings of 60 points, 25 ms apart: about nine seconds of drawing, long
    enough to play through two quiet spells. Public, so the Gallery lists it.
    One ring is a drawing of 1.5 seconds, shorter than a quiet spell."""
    pts = []
    for k in range(rings):
        for i in range(60):
            a = i / 59 * math.pi * 2
            pts.append({"x": 408 + math.cos(a) * (60 + k * 40), "y": 306 + math.sin(a) * (40 + k * 30),
                        "color": "#7c5cff", "size": 10, "t": (k * 60 + i) * 25, "start": i == 0})
    body = {"title": "Steps back", "version": 2, "schemaVersion": 2, "visibility": "public",
            "playbackMode": "replay", "frames": [{"strokes": pts, "strokeGroups": [60] * rings}],
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
    # Full screen plays it, as the Gallery's does (library.js syncFull).
    pg.evaluate("() => document.getElementById('btnFull').click()")
    pg.wait_for_timeout(1200)


INLINE = "document.querySelector('{root} .skribl-inline')._skriblInline"
# Per surface: finished (stopped at the end), the way to its end (repeat off,
# five seconds of the nine left, playing), and a scrub back to the middle.
_IN = {r: INLINE.format(root=r) for r in ("[data-fade-probe]", ".stageCanvasWrap")}
ENDS = {
    "The link page": (
        "() => document.getElementById('playerPlayBtn').getAttribute('aria-label') === 'Play'"
        " && parseFloat(document.getElementById('playerProgressFill').style.width) >= 99.9",
        """async () => { const l = document.getElementById('playerLoopBtn');
            if (l.getAttribute('aria-pressed') === 'true') l.click();
            await window.__skriblPlayerSeek(4 / 9); document.getElementById('playerPlayBtn').click(); }""",
        "() => window.__skriblPlayerSeek(0.5)"),
}
for _name, _root in (("The Gallery", "[data-fade-probe]"), ("The Library", ".stageCanvasWrap")):
    ENDS[_name] = (
        "() => { const s = " + _IN[_root] + ".state(); return s.state === 'paused' && s.totalMs > 0 && s.elapsedMs >= s.totalMs; }",
        "() => { const p = " + _IN[_root] + "; p.setLoop(false); p.seek(p.state().totalMs * 4 / 9); p.toggle(); }",
        "() => { const p = " + _IN[_root] + "; p.seek(p.state().totalMs / 2); }")
SURFACES = [
    ("The link page", link_in, ".canvas-wrap", "#playerBar", "#playerFullExit", ".canvas-wrap > canvas",
     "() => document.getElementById('playerPlayBtn').getAttribute('aria-label') === 'Pause'",
     "() => document.getElementById('playerPlayBtn').click()", True),
    ("The Gallery", gallery_in, "[data-fade-probe]", ":scope > .player-bar", ":scope > .player-btn.full-exit",
     ".skribl-inline-canvas",
     "() => " + INLINE.format(root="[data-fade-probe]") + ".state().state === 'playing'",
     "() => " + INLINE.format(root="[data-fade-probe]") + ".toggle()", True),
    ("The Library", library_in, ".stageCanvasWrap", ":scope > .player-bar", ":scope > .player-btn.full-exit",
     ".skribl-inline-canvas",
     "() => " + INLINE.format(root=".stageCanvasWrap") + ".state().state === 'playing'",
     "() => " + INLINE.format(root=".stageCanvasWrap") + ".toggle()", True),
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
    fin, to_end, back = ENDS[name]
    pg.evaluate(to_end)
    pg.wait_for_timeout(QUIET_MS)
    last = st()                        # its last seconds, playing, with them away
    for _ in range(60):
        if pg.evaluate(fin):
            break
        pg.wait_for_timeout(100)
    pg.wait_for_timeout(400)           # the bar's beat sees it on its next turn
    ends = st()
    check(f"{who}: watched to its end, they come up as it ends (away while it played its last seconds)",
          last["asleep"] and last["playing"] and pg.evaluate(fin) and not ends["asleep"] and ends["bar"],
          f"last seconds {last}; ended {ends}")
    pg.wait_for_timeout(QUIET_MS)
    rest = st()
    check(f"{who}: finished, they step back after a quiet spell, and the finished drawing is whole",
          rest["asleep"] and rest["bar"] is False and rest["x"] is False and pg.evaluate(fin), str(rest))
    if finger:
        pg.touchscreen.tap(px, py)
    else:
        pg.mouse.move(px, py)
    pg.wait_for_timeout(400)
    again = st()
    check(f"{who}: " + ("a finger's first tap on the finished drawing brings them back and does not start it again"
                        if finger else "a mouse that moves over the finished drawing brings them back"),
          not again["asleep"] and again["bar"] and pg.evaluate(fin), str(again))
    pg.evaluate(back)
    pg.wait_for_timeout(QUIET_MS)
    scrub = st()
    check(f"{who}: from there, a scrub back to the middle is a pause: they stay up past a quiet spell",
          not scrub["asleep"] and scrub["bar"] and not scrub["playing"] and not pg.evaluate(fin), str(scrub))
    check(f"{who}: no page errors", not errs, "; ".join(errs[:2]))
    ctx.close()


def laps(b, fx, finger):
    """A drawing shorter than the quiet spell, repeating as it does by default:
    the bar stays away through the laps that follow. The link page told the
    fade at every lap that its state had changed, so they came back each time,
    and on this drawing never left. Sampled every 200 ms over three laps, with
    the progress bar read alongside to prove the laps happened."""
    who = f"The link page ({'phone' if finger else 'desk'})"
    ctx = b.new_context(**(PHONE if finger else DESK))
    pg = ctx.new_page()
    if finger:
        pg.add_init_script(NO_API)
    link_in(pg, fx)
    if not finger:
        pg.mouse.move(2, 2)
    pg.wait_for_timeout(QUIET_MS)
    seen = []
    for _ in range(25):
        seen.append(pg.evaluate("""() => [document.querySelector('.canvas-wrap').classList.contains('chrome-asleep'),
            parseFloat(document.getElementById('playerProgressFill').style.width) || 0]"""))
        pg.wait_for_timeout(200)
    away = [a for a, _ in seen]
    wraps = sum(1 for (_, f0), (_, f1) in zip(seen, seen[1:]) if f1 < f0 - 20)
    check(f"{who}: a short drawing that repeats keeps them away from lap to lap",
          all(away) and wraps >= 2, f"{wraps} laps; " + "".join("z" if a else "U" for a in away))
    ctx.close()


def clock(b, fx, finger):
    """THE CLOCK CLEARS THE PLAYHEAD. In full screen the band's 11px gap and the
    clock's -10px pull, set for the old 6px track, left the clock 1px under the
    scrubber's 30px bar, and the head pokes 3px past the bar with a 2px ring:
    at a drawing's end, where a finished drawing rests, it sat on the last
    digit. Three shots of the clock's row: as shown, the head away, the digits
    see-through. Where the first two differ the head paints; where the first
    and third differ the digits do; no pixel may be both."""
    from PIL import Image, ImageChops
    who = f"The link page ({'phone' if finger else 'desk'})"
    ctx = b.new_context(**(PHONE if finger else DESK))
    pg = ctx.new_page()
    if finger:
        pg.add_init_script(NO_API)
    link_in(pg, fx)
    # Paused, then to its very end with a press at the track's far edge (a
    # paused seek stays paused, so nothing moves between the shots), and the
    # band kept up for them (the stepping back is the rest of this suite's).
    pg.evaluate("() => { const b = document.getElementById('playerPlayBtn'); if (b.getAttribute('aria-label') === 'Pause') b.click(); }")
    pg.wait_for_timeout(300)
    pg.evaluate("""() => { const tr = document.getElementById('playerProgress'), r = tr.getBoundingClientRect();
        for (const t of ['pointerdown', 'pointerup', 'click']) tr.dispatchEvent(new PointerEvent(t, { bubbles: true,
          clientX: r.right - 0.5, clientY: r.top + r.height / 2, pointerId: 1, isPrimary: true })); }""")
    pg.wait_for_timeout(900)
    pg.add_style_tag(content=".chrome-asleep :is(.player-bar, .player-btn.full-exit) { opacity: 1 !important; transition: none !important; }")
    box = pg.evaluate("""() => { const t = document.querySelector('#playerBar .player-time'), h = document.querySelector('#playerProgress .rl-head');
        if (!t || !h) return null; const a = t.getBoundingClientRect(), c = h.getBoundingClientRect();
        const x0 = Math.min(a.left, c.left) - 4, y0 = Math.min(a.top, c.top) - 4;
        return { x: Math.max(0, x0), y: Math.max(0, y0), width: Math.max(a.right, c.right) + 4 - Math.max(0, x0),
                 height: Math.max(a.bottom, c.bottom) + 4 - Math.max(0, y0), at: document.getElementById('playerAt').textContent,
                 dur: document.getElementById('playerDur').textContent, head: Math.round(parseFloat(h.style.left) || 0) }; }""")
    if not box:
        check(f"{who}: at a drawing's end, the playhead clears the clock's digits", False, "no clock or no head")
        ctx.close()
        return
    clip = {k: box[k] for k in ("x", "y", "width", "height")}
    shot = lambda: Image.open(io.BytesIO(pg.screenshot(clip=clip))).convert("RGB")
    def away(css):
        h = pg.add_style_tag(content=css); pg.wait_for_timeout(80)
        im = shot()
        h.evaluate("e => e.remove()"); pg.wait_for_timeout(80)
        return im
    shown = shot()
    no_head = away("#playerProgress .rl-head { visibility: hidden !important; }")
    no_digits = away("#playerAt, #playerDur { color: transparent !important; }")
    def mask(a, c):
        d = ImageChops.difference(a, c).tobytes()
        return [d[i] + d[i + 1] + d[i + 2] > 30 for i in range(0, len(d), 3)]
    head, digits = mask(shown, no_head), mask(shown, no_digits)
    both = sum(1 for h, d in zip(head, digits) if h and d)
    check(f"{who}: at a drawing's end, the playhead and its ring clear the clock's digits",
          both == 0 and sum(head) > 0 and sum(digits) > 20,
          f"{both} pixels both; the head paints {sum(head)}, the digits {sum(digits)}; "
          f"the clock reads {box['at']} of {box['dur']}, the head at {box['head']}%")
    ctx.close()


print("\nFULL SCREEN STEPS BACK — the link page, the Gallery and the Library")
with sync_playwright() as p:
    b = p.chromium.launch()
    fx = post()
    for name, go_in, root, bar, x, cv, playing, toggle, whole in SURFACES:
        for finger in (True, False):
            walk(b, fx, name, go_in, root, bar, x, cv, playing, toggle, whole, finger)
    short = post(rings=1)
    for finger in (True, False):
        laps(b, short, finger)
    print("\nTHE CLOCK CLEARS THE PLAYHEAD — the link page, at a drawing's end")
    for finger in (True, False):
        clock(b, short, finger)
    b.close()

print("\n" + "=" * 62)
passed = sum(1 for r in results if r[0])
print(f"{passed}/{len(results)} passed" + ("" if passed == len(results) else
      "  FAILURES: " + ", ".join(r[1] for r in results if not r[0])))
sys.exit(0 if passed == len(results) else 1)
