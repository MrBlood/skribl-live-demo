#!/usr/bin/env python3
"""Record the screen clips How it works plays -- from the real app, both themes.

    python3 harness/tools/make_help_clips.py            # every clip
    python3 harness/tools/make_help_clips.py music      # just these

Some things are shown by the screen rather than by a drawing (adding a song,
posting), so these are short silent videos of the real editor at phone size,
with a soft finger dot over every tap and drag. Captured at 2x with the
browser's own screencast (Playwright's video recorder captures at 1x, which is
soft on a phone), cropped to the part of the screen that matters, and encoded
H.264 with ffmpeg so every iPhone plays them. One per theme, so a clip always
matches the app around it: skribl/static/help/clips/<name>-<dark|light>.mp4.

Needs the local server (harness/bootstrap.sh) and ffmpeg.
"""
import base64
import io
import math
import os
import pathlib
import struct
import subprocess
import sys
import tempfile
import wave

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE.parent))
import browsing  # noqa: E402

OUT = ROOT / "skribl" / "static" / "help" / "clips"
BASE = os.environ.get("SKRIBL_BASE", "http://127.0.0.1:5001")
# Phone WIDTH, so the phone layout; a tall screen, so opening a drawer never
# scrolls the page and a fixed crop holds the whole gesture.
VW, VH, DPR = 390, 1300, 2

# The finger: a soft disc that follows the pointer and presses in. It is part
# of the page while recording, so it is in the frames, exactly where the
# pointer went.
# A press also sends out a purple ripple: the owner could not see the buttons
# being pushed in the first Post clip, and a pale disc on a pale button is
# nearly invisible in the light theme, so the disc carries a dark outer ring.
FINGER = """() => {
  const f = document.createElement('div'); f.id = 'clipFinger';
  f.style.cssText = 'position:fixed;left:0;top:0;width:34px;height:34px;margin:-17px 0 0 -17px;' +
    'border-radius:50%;background:rgba(255,255,255,.34);' +
    'box-shadow:0 0 0 2px rgba(255,255,255,.8),0 0 0 3.5px rgba(20,16,40,.45),0 4px 14px rgba(0,0,0,.35);' +
    'pointer-events:none;z-index:2147483647;opacity:0;transition:opacity .18s, transform .12s;';
  document.body.appendChild(f);
  const at = e => { f.style.left = e.clientX + 'px'; f.style.top = e.clientY + 'px'; f.style.opacity = 1; };
  const ripple = e => {
    const r = document.createElement('div');
    r.style.cssText = 'position:fixed;left:' + e.clientX + 'px;top:' + e.clientY + 'px;width:44px;height:44px;' +
      'margin:-22px 0 0 -22px;border-radius:50%;border:3px solid rgba(124,92,255,.85);pointer-events:none;' +
      'z-index:2147483646;transform:scale(.5);opacity:1;transition:transform .5s ease-out, opacity .5s ease-out;';
    document.body.appendChild(r);
    requestAnimationFrame(() => requestAnimationFrame(() => { r.style.transform = 'scale(1.7)'; r.style.opacity = 0; }));
    setTimeout(() => r.remove(), 600);
  };
  addEventListener('pointermove', at, true);
  addEventListener('pointerdown', e => { at(e); f.style.transform = 'scale(.82)'; ripple(e); }, true);
  addEventListener('pointerup', () => { f.style.transform = ''; }, true);
  window.__fingerHide = () => { f.style.opacity = 0; };
}"""


def song():
    """Four seconds of a plucked bass line: a real waveform to trim."""
    buf, sr = io.BytesIO(), 22050
    with wave.open(buf, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        frames = []
        for i in range(sr * 6):
            t = i / sr; beat = t % 0.5
            env = math.exp(-beat * 7) * (1.0 if int(t / 0.5) % 4 != 3 else 0.55)
            v = env * (math.sin(2 * math.pi * 82 * t) + 0.4 * math.sin(2 * math.pi * 164 * t))
            frames.append(struct.pack("<h", int(max(-1, min(1, v * 0.7)) * 30000)))
        w.writeframes(b"".join(frames))
    return buf.getvalue()


class Recorder:
    def __init__(self, page):
        self.page = page
        self.cdp = page.context.new_cdp_session(page)
        self.frames = []
        self.marks = {}
        self.cdp.on("Page.screencastFrame", self._frame)

    def _frame(self, ev):
        self.frames.append((ev["metadata"]["timestamp"], base64.b64decode(ev["data"])))
        try:
            self.cdp.send("Page.screencastFrameAck", {"sessionId": ev["sessionId"]})
        except Exception:
            pass

    def start(self):
        vp = self.page.viewport_size
        self.cdp.send("Page.startScreencast", {"format": "png", "maxWidth": vp["width"] * DPR, "maxHeight": vp["height"] * DPR,
                                                "everyNthFrame": 1})

    def mark(self, name):
        """Note the moment, on the frames' clock, for a camera move."""
        self.marks[name] = self.frames[-1][0] if self.frames else 0.0

    def stop(self):
        self.cdp.send("Page.stopScreencast")


def glide(page, a, b, ms=500, steps=24):
    page.mouse.move(*a)
    for i in range(1, steps + 1):
        t = 0.5 - 0.5 * math.cos(math.pi * i / steps)
        page.mouse.move(a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
        page.wait_for_timeout(ms // steps)


def tap(page, sel, before=380, after=520):
    box = page.locator(sel).bounding_box()
    x, y = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
    glide(page, (x + 60, y + 90), (x, y), before)
    page.mouse.down(); page.wait_for_timeout(170); page.mouse.up()
    page.wait_for_timeout(after)
    return x, y


def center(page, sel):
    b = page.locator(sel).bounding_box()
    return b["x"] + b["width"] / 2, b["y"] + b["height"] / 2


# ---- the clips ---------------------------------------------------------------
# Each returns the crop, in CSS px of the viewport: (x, y, w, h), 4:3.
def clip_music(page, rec):
    # THE WHOLE PHONE SCREEN, every tap on it (owner: the zoomed clips did not
    # "reveal the screen"): open the drawer, Music, add a song, set the loop.
    rec.start(); page.wait_for_timeout(400)
    tap(page, "#mediaOpenBtn", after=450)
    tap(page, "#mediaTabMusic", after=450)
    drop = page.locator("#musicInput").evaluate("i => { const z = i.closest('label, .drop, .media-drop, .pending-row') || i.parentElement; const r = z.getBoundingClientRect(); return [r.x + r.width / 2, r.y + r.height / 2]; }")
    glide(page, (drop[0] + 50, drop[1] + 80), drop, 420)
    page.mouse.down(); page.wait_for_timeout(110); page.mouse.up()
    page.set_input_files("#musicInput", {"name": "Bassline.wav", "mimeType": "audio/wav", "buffer": song()})
    page.wait_for_function("() => typeof currentAudioBuffer !== 'undefined' && !!currentAudioBuffer", timeout=20000)
    page.wait_for_timeout(500)
    hx, hy = center(page, "#handleEnd")
    glide(page, (hx + 40, hy + 70), (hx, hy), 420)
    page.mouse.down()
    glide(page, (hx, hy), (hx - 120, hy), 900)
    page.mouse.up(); page.wait_for_timeout(300)
    sx, sy = center(page, "#handleStart")
    glide(page, (hx - 120, hy), (sx, sy), 420)
    page.mouse.down()
    glide(page, (sx, sy), (sx + 50, sy), 700)
    page.mouse.up(); page.wait_for_timeout(250)
    page.evaluate("window.__fingerHide()"); page.wait_for_timeout(800)
    rec.stop()
    return (0, 0, page.viewport_size["width"], page.viewport_size["height"])


def clip_post(page, rec):
    # A drawing to post, drawn off camera: the Draw card's cat (artworks.py),
    # quickly -- only the posting is filmed.
    import artdraw
    import artworks
    page.evaluate("""() => { const t = window.SkriblCanvasSizes, id = t.SIZES.find(s => s.label === '4:3').id;
        document.querySelector(`#canvasSeg button[data-size='${id}']`).click(); }""")
    page.wait_for_timeout(300)
    artdraw.draw(page, artworks.cat(), tempo=3.0)
    # End the take, as you would before posting: the header shows Done, not
    # Post, while a take is being recorded.
    page.evaluate("() => { if (recording) endRecordingTake(); }")
    page.wait_for_timeout(600)
    # Ending the take says "Take saved" in a toast; it belongs to the drawing,
    # which was done off camera, so it is put away before filming starts.
    page.evaluate("() => { try { toast.hidden = true; } catch (e) {} }")
    # THE WHOLE PHONE SCREEN: the tap on Post, the sheet, the title, the
    # sheet's Post button and "Posted!" all in one frame. A zoomed camera
    # panning after the finger lost it off the bottom (owner).
    rec.start(); page.wait_for_timeout(400)
    tap(page, "#postBtn", after=550)
    rec.mark("sheet")
    tx, ty = center(page, "#postTitleInput")
    glide(page, (tx + 60, ty + 80), (tx, ty), 600)
    page.mouse.down(); page.wait_for_timeout(120); page.mouse.up()
    page.keyboard.type("Cat", delay=80)
    page.wait_for_timeout(250)
    rec.mark("submit")
    page.wait_for_timeout(500)
    tap(page, "#postSubmitBtn", before=500, after=250)
    page.wait_for_selector("#postResult:not([hidden])", timeout=15000)
    page.evaluate("window.__fingerHide()"); page.wait_for_timeout(1100)
    rec.stop()
    return (0, 0, page.viewport_size["width"], page.viewport_size["height"])


# ---- Flip's own tools ---------------------------------------------------------
# Select and Liquify change strokes already on the page, and a page stores only
# where its points ended up, so a replay could not show the move or the warp.
# These are filmed from the editor instead: the drawing is made off camera with
# real pen input (artdraw.py), and only the tool's gesture is on screen.
def flip_ready(page):
    """Flip at 4:3 on paper with the pen, as the illustrations are drawn."""
    import artdraw
    page.evaluate("""() => { const t = window.SkriblCanvasSizes, id = t.SIZES.find(s => s.label === '4:3').id;
        const b = document.querySelector(`[data-size='${id}']`); if (b) b.click(); }""")
    page.wait_for_timeout(300)
    page.evaluate(f"""() => {{ setBg('{artdraw.PAPER}'); onion = false;
        if (window.SkriblPressure) SkriblPressure.setEnabled(true); shelfSetTool('pen'); }}""")
    page.wait_for_timeout(200)
    return page.evaluate("() => [CW, CH]")


def flip_draw(page, strokes, logical):
    import artdraw
    artdraw.draw(page, strokes, canvas="#pad", logical=logical, tempo=3.0, pause_tempo=4.0,
                 set_ink=lambda pg, c, s: pg.evaluate("([c, s]) => { color = c; size = s; }", [c, s]))
    # While a pen is down the editor fades and tucks its chrome, and it eases
    # back after the last stroke, moving the pad about 13px: a frame measured
    # before it settles is off by that much for the rest of the clip.
    page.wait_for_timeout(1500)
    # The fingertip followed the off-camera pen; it starts the clip hidden.
    page.evaluate("() => window.__fingerHide && window.__fingerHide()")


PAD_WATCH = """() => { window.__padYs = []; const c = document.getElementById('pad'); let last = null;
  (function tick() { const y = c.getBoundingClientRect().y;
    if (y !== last) { __padYs.push([Date.now() / 1000, y]); last = y; }
    requestAnimationFrame(tick); })(); }"""


def follow_pad(page, crop):
    """The crop as a camera that moves WITH the pad. Selecting on Flip grows
    the tool-hint line above the canvas to two lines, which moves the pad up
    26px mid-clip: the app doing its job, so the camera follows it on the same
    frame instead, and the drawing holds still in the clip. Times are the
    page's wall clock, which is the clock the screencast frames carry."""
    x, y, w, h = crop
    ys = page.evaluate("() => window.__padYs || []")
    if not ys:
        return crop
    y0 = ys[0][1]
    keys = [(ys[0][0], y)]
    for (ta, ya), (tb, yb) in zip(ys, ys[1:]):
        keys += [(tb - 0.001, y + (ya - y0)), (tb, y + (yb - y0))]
    return (x, w, h, keys) if len(keys) > 1 else crop


def on_pad(page, logical):
    """Logical canvas units -> page coordinates, and the 4:3 crop round the pad."""
    b = page.locator("#pad").bounding_box()
    k = b["width"] / logical[0]
    to = lambda x, y: (b["x"] + x * k, b["y"] + y * k)
    # The largest 4:3 frame INSIDE the pad: on a phone the pad can be a little
    # short of 4:3, and a frame sized from its width alone took in the page
    # below it.
    # Inset past the pad's rounded corners and edge, which are page, not paper.
    w = min(b["width"] - 16, (b["height"] - 16) * 4 / 3)
    w = int(w) // 4 * 4; h = w * 3 // 4
    return to, (b["x"] + (b["width"] - w) / 2, b["y"] + (b["height"] - h) / 2, w, h)


def clip_liquify(page, rec):
    import math
    from artdraw import INK, PURPLE, Stroke as S
    logical = flip_ready(page)
    lines = []
    for i, (y, c) in enumerate(((236, PURPLE), (306, INK), (376, "#ff6f91"))):
        pts = [(150 + 516 * k / 12, y + 10 * math.sin(k / 12 * 2 * math.pi + i * 0.8)) for k in range(13)]
        lines.append(S(pts, "contour", c, size=11, weight=[(0, 0.6), (0.5, 1.0), (1, 0.6)]))
    flip_draw(page, lines, logical)
    page.evaluate("() => shelfSetTool('liquify')"); page.wait_for_timeout(300)
    to, crop = on_pad(page, logical)
    page.evaluate(PAD_WATCH)
    rec.start(); page.wait_for_timeout(500)
    # One unhurried pull down through all three lines, then a second, shorter
    # one beside it: the lines bend with the finger and keep their order.
    for (x0, y0, x1, y1, ms) in ((350, 170, 380, 450, 1300), (520, 440, 500, 250, 1000)):
        a, b = to(x0, y0), to(x1, y1)
        glide(page, (a[0] + 40, a[1] - 60), a, 350)
        page.mouse.down()
        glide(page, a, b, ms, steps=40)
        page.mouse.up(); page.wait_for_timeout(300)
    page.evaluate("window.__fingerHide()"); page.wait_for_timeout(900)
    rec.stop()
    return follow_pad(page, crop)


def clip_select(page, rec):
    import math
    from artdraw import PURPLE, Stroke as S
    logical = flip_ready(page)

    def heart(side, cx=250, cy=300, k=7.5):
        pts = []
        for i in range(19):
            a = min(math.pi, math.pi * i / 16) * side
            x = 16 * math.sin(a) ** 3
            y = 13 * math.cos(a) - 5 * math.cos(2 * a) - 2 * math.cos(3 * a) - math.cos(4 * a)
            pts.append((cx + k * x, cy - k * y))
        return pts
    flip_draw(page, [S(heart(-1), "contour", PURPLE, size=22), S(heart(+1), "contour", PURPLE, size=22)], logical)
    page.evaluate("() => shelfSetTool('select')"); page.wait_for_timeout(300)
    to, crop = on_pad(page, logical)
    page.evaluate(PAD_WATCH)
    rec.start(); page.wait_for_timeout(500)
    # A box round the heart, then the heart carried across the page.
    a, b = to(110, 165), to(395, 430)
    glide(page, (a[0] + 50, a[1] - 40), a, 350)
    page.mouse.down(); glide(page, a, b, 900, steps=30); page.mouse.up()
    page.wait_for_timeout(450)
    c, d = to(250, 300), to(560, 290)
    glide(page, b, c, 450)
    page.mouse.down(); glide(page, c, d, 1100, steps=40); page.mouse.up()
    page.wait_for_timeout(350)
    page.evaluate("window.__fingerHide()"); page.wait_for_timeout(900)
    rec.stop()
    return follow_pad(page, crop)


def tap_at(page, pt, before=380, after=500):
    glide(page, (pt[0] + 50, pt[1] + 70), pt, before)
    page.mouse.down(); page.wait_for_timeout(170); page.mouse.up()
    page.wait_for_timeout(after)


def sweep(page, pts, ms):
    """A finger down, along a path, and up: a brush tool's gesture."""
    glide(page, (pts[0][0] + 40, pts[0][1] - 50), pts[0], 350)
    page.mouse.down()
    per = ms // max(1, len(pts) - 1)
    for a, b in zip(pts, pts[1:]):
        glide(page, a, b, per, steps=max(6, per // 30))
    page.mouse.up(); page.wait_for_timeout(300)


def clip_fill(page, rec):
    import math
    from artdraw import INK, Stroke as S
    logical = flip_ready(page)
    cloud = []
    for k in range(61):
        a = 2 * math.pi * 1.06 * k / 60 - math.pi / 2
        r = 105 + 18 * abs(math.sin(2.5 * a))
        cloud.append((300 + 1.2 * r * math.cos(a), 300 + 0.85 * r * math.sin(a)))
    circle = [(590 + 85 * math.cos(2 * math.pi * 1.08 * k / 40), 300 + 85 * math.sin(2 * math.pi * 1.08 * k / 40))
              for k in range(41)]
    # Closed and full weight end to end, so the outline holds the fill.
    flip_draw(page, [S(cloud, "contour", INK, size=10, taper=(0, 0)),
                     S(circle, "contour", INK, size=10, taper=(0, 0))], logical)
    page.evaluate("() => { shelfSetTool('fill'); color = '#7c5cff'; }"); page.wait_for_timeout(300)
    page.evaluate(PAD_WATCH)
    to, crop = on_pad(page, logical)
    rec.start(); page.wait_for_timeout(500)
    tap_at(page, to(300, 300), after=700)
    page.evaluate("() => { color = '#ff6f91'; }")
    tap_at(page, to(590, 300), after=700)
    page.evaluate("window.__fingerHide()"); page.wait_for_timeout(900)
    rec.stop()
    return follow_pad(page, crop)


def clip_smudge(page, rec):
    from artdraw import INK, PURPLE, Stroke as S
    logical = flip_ready(page)
    stripes = [S([(160, y), (408, y + 4), (656, y)], "contour", c, size=26, taper=(0.04, 0.04))
               for y, c in ((236, PURPLE), (300, "#ff6f91"), (364, INK))]
    flip_draw(page, stripes, logical)
    page.evaluate("() => shelfSetTool('smudge')"); page.wait_for_timeout(300)
    page.evaluate(PAD_WATCH)
    to, crop = on_pad(page, logical)
    rec.start(); page.wait_for_timeout(500)
    sweep(page, [to(300, 200), to(320, 300), to(340, 410)], 1300)
    sweep(page, [to(520, 410), to(500, 300), to(480, 200)], 1100)
    page.evaluate("window.__fingerHide()"); page.wait_for_timeout(900)
    rec.stop()
    return follow_pad(page, crop)


def clip_blur(page, rec):
    from artdraw import INK, Stroke as S
    logical = flip_ready(page)
    zig = [(150 + 52 * k, 250 if k % 2 else 350) for k in range(11)]
    flip_draw(page, [S(zig, "contour", INK, size=12, taper=(0.03, 0.06))], logical)
    page.evaluate("() => shelfSetTool('blur')"); page.wait_for_timeout(300)
    page.evaluate(PAD_WATCH)
    to, crop = on_pad(page, logical)
    rec.start(); page.wait_for_timeout(500)
    # Back and forth over the right half; the left stays sharp beside it.
    sweep(page, [to(430, 300), to(660, 290), to(440, 310), to(650, 300)], 2200)
    page.evaluate("window.__fingerHide()"); page.wait_for_timeout(900)
    rec.stop()
    return follow_pad(page, crop)


def clip_stamp(page, rec):
    import math
    from artdraw import PURPLE, Stroke as S
    logical = flip_ready(page)
    star = []
    for k in range(11):
        r = 46 if k % 2 == 0 else 20
        a = -math.pi / 2 + math.pi * k / 5
        star.append((170 + r * math.cos(a), 170 + r * math.sin(a)))
    flip_draw(page, [S(star, "contour", PURPLE, size=12, taper=(0, 0))], logical)
    # Saved as a stamp off camera: select it, Stamp. The clip is the placing.
    to, _ = on_pad(page, logical)
    page.evaluate("() => shelfSetTool('select')"); page.wait_for_timeout(300)
    a, b = to(100, 100), to(240, 240)
    page.mouse.move(*a); page.mouse.down(); page.mouse.move(*b, steps=12); page.mouse.up()
    page.wait_for_timeout(400)
    page.locator("#sbStamp").click(); page.wait_for_timeout(400)
    page.evaluate("() => { setTool('stamp'); const p = document.getElementById('stampPop'); if (p) p.hidden = true;"
                  " try { SkriblHints && SkriblHints.hide(); } catch (e) {} }")
    page.wait_for_timeout(1500)
    page.evaluate(PAD_WATCH)
    to, crop = on_pad(page, logical)
    rec.start(); page.wait_for_timeout(500)
    for pt in ((380, 260), (560, 380), (660, 200), (300, 430)):
        tap_at(page, to(*pt), before=330, after=380)
    page.evaluate("window.__fingerHide()"); page.wait_for_timeout(900)
    rec.stop()
    return follow_pad(page, crop)


def clip_artmove(page, rec):
    import math
    from artdraw import INK, PURPLE, Stroke as S
    logical = flip_ready(page)

    def heart(side, cx=230, cy=290, k=6.5):
        pts = []
        for i in range(19):
            a = min(math.pi, math.pi * i / 16) * side
            x = 16 * math.sin(a) ** 3
            y = 13 * math.cos(a) - 5 * math.cos(2 * a) - 2 * math.cos(3 * a) - math.cos(4 * a)
            pts.append((cx + k * x, cy - k * y))
        return pts
    star = []
    for k in range(11):
        r = 40 if k % 2 == 0 else 17
        a = -math.pi / 2 + math.pi * k / 5
        star.append((380 + r * math.cos(a), 220 + r * math.sin(a)))
    flip_draw(page, [S(heart(-1), "contour", PURPLE, size=18), S(heart(+1), "contour", PURPLE, size=18),
                     S(star, "contour", INK, size=10, taper=(0, 0))], logical)
    page.evaluate("() => shelfSetTool('artmove')"); page.wait_for_timeout(300)
    page.evaluate(PAD_WATCH)
    to, crop = on_pad(page, logical)
    rec.start(); page.wait_for_timeout(500)
    # The whole page's drawing moves together, wherever the drag starts.
    sweep(page, [to(300, 300), to(470, 330)], 1300)
    page.evaluate("window.__fingerHide()"); page.wait_for_timeout(900)
    rec.stop()
    return follow_pad(page, crop)


CLIPS = {"music": clip_music, "post": clip_post, "select": clip_select, "liquify": clip_liquify,
         "smudge": clip_smudge, "blur": clip_blur, "fill": clip_fill, "stamp": clip_stamp,
         "artmove": clip_artmove}
# The editor a clip is filmed in, when not Pad.
ROUTE = {k: "/flip" for k in ("select", "liquify", "smudge", "blur", "fill", "stamp", "artmove")}
# Where a clip is recorded, when not the tall phone screen above.
VIEWPORT = {"music": (390, 844), "post": (390, 844)}   # a phone's own screen, all of it


# Driving a 2x page makes every gesture take about half again as long as it
# was scripted to, so clips play back at this rate to move at a hand's speed
# (a touch brisker since the owner asked for shorter clips).
SPEED = 1.6


def held(frames, i):
    """How long frame i is shown. A still moment (a decode, a settle) holds at
    most 0.5 s: the clip shows the gesture, not the waiting. The last, 1 s."""
    ts = frames[i][0]
    nxt = frames[i + 1][0] if i + 1 < len(frames) else ts + 1.0
    return min(1.0 if i + 1 == len(frames) else 0.5, max(0.001, nxt - ts))


def clock(frames, t):
    """A moment on the recording's clock, on the clip's (stills shortened)."""
    out = 0.0
    for i, (ts, _) in enumerate(frames):
        d = held(frames, i)
        if t <= ts + d:
            return out + max(0.0, min(d, t - ts))
        out += d
    return out


def encode(frames, crop, out):
    if len(crop) == 4 and isinstance(crop[3], list):
        # (x, w, h, [(t, y), ...]): the camera holds at each framing and eases
        # to the next, written as the first framing plus one eased move per
        # pair of points -- a sum, so any number of moves needs no nesting.
        x, w, h = [round(v * DPR) for v in crop[:3]]
        keys = [(clock(frames, kt), round(ky * DPR)) for kt, ky in crop[3]]
        y = str(keys[0][1])
        for (ta, ya), (tb, yb) in zip(keys, keys[1:]):
            if yb == ya:
                continue
            u = f"clip((t-{ta:.3f})/{max(0.001, tb - ta):.3f}\\,0\\,1)"
            y += f"+({yb - ya})*{u}*{u}*(3-2*{u})"
    else:
        x, y, w, h = [round(v * DPR) for v in crop]
    with tempfile.TemporaryDirectory() as d:
        lst = []
        for i, (ts, png) in enumerate(frames):
            p = pathlib.Path(d) / f"f{i:05d}.png"; p.write_bytes(png)
            lst.append(f"file '{p}'\nduration {held(frames, i):.4f}")
        lst.append(f"file '{pathlib.Path(d) / f'f{len(frames) - 1:05d}.png'}'")
        (pathlib.Path(d) / "list.txt").write_text("\n".join(lst))
        # At the crop's own 2x pixels, never scaled down: a downscale is what
        # softened the interface text in the first clips.
        w, h = w // 2 * 2, h // 2 * 2
        # A whole phone screen is 780 px wide at 2x; 600 keeps its text crisp
        # full screen at a fraction of the bytes. A canvas crop stays native.
        fit = ",scale=600:-2:flags=lanczos" if w > 700 else ""
        vf = f"crop={w}:{h}:{x}:{y},setpts=PTS/{SPEED}{fit},fps=30,format=yuv420p"
        src = ["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(pathlib.Path(d) / "list.txt"), "-vf", vf]
        subprocess.run(src + ["-c:v", "libx264", "-profile:v", "high", "-crf", "21", "-preset", "slow",
                              "-movflags", "+faststart", "-an", str(out)], check=True)
        # And VP9 for browsers without H.264 (Linux Chromium, some Firefox):
        # lib/helplearn.js asks canPlayType and fetches only the one it can play.
        subprocess.run(src + ["-c:v", "libvpx-vp9", "-crf", "34", "-b:v", "0", "-row-mt", "1", "-deadline", "good",
                              "-an", str(out.with_suffix(".webm"))], check=True)
    # The poster: the clip's last moment, where the gesture has landed. Shown
    # until the video plays, and instead of it when reduced motion is asked for.
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-sseof", "-0.4", "-i", str(out), "-frames:v", "1",
                    "-q:v", "4", str(out.with_suffix(".jpg"))], check=True)


def make(browser, name, dark):
    vw, vh = VIEWPORT.get(name, (VW, VH))
    ctx = browser.new_context(viewport={"width": vw, "height": vh}, device_scale_factor=DPR,
                              color_scheme="dark" if dark else "light")
    page = ctx.new_page()
    errs = []
    page.on("pageerror", lambda e: errs.append(str(e)))
    browsing.goto(page, BASE, ROUTE.get(name, "/skribl-pad"))
    page.wait_for_timeout(900)
    page.evaluate("() => { window.SkriblHints && window.SkriblHints.hide(); }")
    page.evaluate(FINGER)
    rec = Recorder(page)
    crop = CLIPS[name](page, rec)
    ctx.close()
    if errs:
        raise SystemExit(f"{name}: page errors {errs[:2]}")
    out = OUT / f"{name}-{'dark' if dark else 'light'}.mp4"
    encode(rec.frames, crop, out)
    print(f"{out.stem:14s} {len(rec.frames):4d} frames  mp4 {out.stat().st_size:8,d} B  webm {out.with_suffix('.webm').stat().st_size:8,d} B")


if __name__ == "__main__":
    from playwright.sync_api import sync_playwright
    OUT.mkdir(parents=True, exist_ok=True)
    names = sys.argv[1:] or list(CLIPS)
    with sync_playwright() as p:
        # A real 2x surface: the screencast follows the compositor's scale, and
        # emulated device_scale_factor alone still hands back 1x frames.
        b = p.chromium.launch(args=[f"--force-device-scale-factor={DPR}"])
        for n in names:
            for dark in (True, False):
                make(b, n, dark)
        b.close()
