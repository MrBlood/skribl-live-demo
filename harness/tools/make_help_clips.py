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

# The finger: a bright point in a soft purple glow, in the family of the
# replay's own pen-tip nib (a dot of the ink's colour in a glow of it), so a
# clip and a replay read as one thing. Owner's pick of three mocked (B). It is
# part of the page while recording, so it is in the frames, exactly where the
# pointer went; it presses in on a tap and sends out a purple bloom, because
# the owner could not see the buttons being pushed in the first Post clip.
# The tool picture Flip draws beside a mouse pointer stays (owner: "so you
# know what it is"); the crosshair beneath it is hidden, since a finger has
# none and it sat inside the fingertip. The app's hover tooltips are hidden
# too: the recorder drives a mouse, and a finger never raises them.
FINGER = """() => {
  const s = document.createElement('style');
  s.textContent = '.flip-brush-cursor,.skribl-tip{display:none!important}';
  document.head.appendChild(s);
  const f = document.createElement('div'); f.id = 'clipFinger';
  f.style.cssText = 'position:fixed;left:0;top:0;width:30px;height:30px;margin:-15px 0 0 -15px;border-radius:50%;' +
    'background:radial-gradient(circle,rgba(255,255,255,.95) 0 5px,rgba(124,92,255,.95) 5.5px 6.8px,' +
    'rgba(124,92,255,.28) 7.5px,rgba(124,92,255,0) 70%);' +
    'pointer-events:none;z-index:2147483647;opacity:0;transition:opacity .18s, transform .14s ease-out;';
  document.body.appendChild(f);
  const at = e => { f.style.left = e.clientX + 'px'; f.style.top = e.clientY + 'px'; f.style.opacity = 1; };
  const ripple = e => {
    const r = document.createElement('div');
    r.style.cssText = 'position:fixed;left:' + e.clientX + 'px;top:' + e.clientY + 'px;width:30px;height:30px;' +
      'margin:-15px 0 0 -15px;border-radius:50%;background:rgba(124,92,255,.28);pointer-events:none;' +
      'z-index:2147483646;transform:scale(.6);opacity:1;transition:transform .55s cubic-bezier(.2,.7,.3,1), opacity .55s ease-out;';
    document.body.appendChild(r);
    requestAnimationFrame(() => requestAnimationFrame(() => { r.style.transform = 'scale(2)'; r.style.opacity = 0; }));
    setTimeout(() => r.remove(), 650);
  };
  addEventListener('pointermove', at, true);
  addEventListener('pointerdown', e => { at(e); f.style.transform = 'scale(.86)'; ripple(e); }, true);
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


def tap(page, sel, before=380, after=520, frm=(60, 90)):
    """`frm`: where the finger comes in from, as an offset. A finger gliding
    across a control with a tooltip raises it, as a mouse would."""
    box = page.locator(sel).bounding_box()
    x, y = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
    glide(page, (x + frm[0], y + frm[1]), (x, y), before)
    page.mouse.down(); page.wait_for_timeout(170); page.mouse.up()
    page.wait_for_timeout(after + TAP_REST)
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



# ---- Flip's techniques -------------------------------------------------------
# These are about the page strip and the playback settings as much as the
# canvas, so like Post and Add music they are filmed as the whole phone
# screen: every tap stays in frame. The poses are drawn off camera with real
# pen input; Onion skin's second pose is drawn on camera, since drawing over
# the ghost IS the technique.
def ring(cx, cy, r, n=28, start=-90):
    import math
    return [(cx + r * math.cos(math.radians(start + 360 * k / n)), cy + r * math.sin(math.radians(start + 360 * k / n)))
            for k in range(n + 1)]


def ball(cx, cy, r=34):
    from artdraw import PURPLE, Stroke as S
    return S(ring(cx, cy, r), "contour", PURPLE, size=10, taper=(0.04, 0.04))


def ground():
    from artdraw import Stroke as S
    return S([(110, 470), (706, 470)], "form", size=6, taper=(0.1, 0.1))


def strip_frame(page, i):
    return f"#strip .frame:nth-child({i + 1})"


def flip_pages(page, poses):
    """Each pose drawn on its own page, then back to page 1."""
    logical = flip_ready(page)
    for k, strokes in enumerate(poses):
        if k:
            page.click("#addblank"); page.wait_for_timeout(400)
        flip_draw(page, strokes, logical)
    page.evaluate("() => go(0)"); page.wait_for_timeout(500)
    page.evaluate("() => window.__fingerHide && window.__fingerHide()")
    return logical


def flip_example(page):
    """Flip's own bouncing ball (the Squash and stretch card), opened as a
    draft and put on paper, onion skin off: a real multi-page animation."""
    import artdraw
    page.set_input_files("#draftInput", str(ROOT / "skribl" / "static" / "help" / "demos" / "flip-bounce.json"))
    page.wait_for_timeout(1500)
    page.evaluate(f"""() => {{ setBg('{artdraw.PAPER}'); if (onion) document.getElementById('onion').click();
        go(0); try {{ toast.hidden = true; }} catch (e) {{}} }}""")
    page.wait_for_timeout(900)
    page.evaluate("() => window.__fingerHide && window.__fingerHide()")


def whole(page):
    return (0, 0, page.viewport_size["width"], page.viewport_size["height"])


def clip_inbetween(page, rec):
    flip_pages(page, [[ground(), ball(240, 190)], [ground(), ball(580, 420)]])
    rec.start(); page.wait_for_timeout(500)
    # One tap and Flip draws the page halfway; then the three pages in turn.
    tap(page, "#addinbetween", after=900)
    for i in (0, 1, 2):
        tap(page, strip_frame(page, i), before=420, after=650)
    page.evaluate("window.__fingerHide()"); page.wait_for_timeout(700)
    rec.stop()
    return whole(page)


def figure(arm):
    """A stick figure waving: the arm is the one stroke that moves."""
    from artdraw import PURPLE, Stroke as S
    return [S(ring(408, 150, 38), "contour", size=8, taper=(0.04, 0.04)),
            S([(408, 190), (408, 330)], "contour", size=8),
            S([(408, 330), (360, 450)], "contour", size=8),
            S([(408, 330), (456, 450)], "contour", size=8),
            S([(408, 230), (350, 300)], "contour", size=8),
            S([(408, 230), arm], "contour", PURPLE, size=9)]


def clip_smear(page, rec):
    flip_pages(page, [figure((520, 120)), figure((540, 330))])
    rec.start(); page.wait_for_timeout(500)
    # The smear page goes between the two poses and Flip moves to it: the arm
    # is a blur of its whole swing, the rest stays sharp.
    tap(page, "#addtween", after=1200)
    for i in (0, 1, 2):
        tap(page, strip_frame(page, i), before=420, after=650)
    page.evaluate("window.__fingerHide()"); page.wait_for_timeout(700)
    rec.stop()
    return whole(page)


def clip_onion(page, rec):
    import artdraw
    logical = flip_ready(page)
    flip_draw(page, [ground(), ball(260, 240)], logical)
    page.click("#addblank"); page.wait_for_timeout(500)
    page.evaluate("() => window.__fingerHide && window.__fingerHide()")
    rec.start(); page.wait_for_timeout(500)
    # Turn it on: the page before shows through, faintly.
    tap(page, "#tuneBtn", after=500, frm=(-90, 30))
    tap(page, "#onion", after=600, frm=(-120, 20))
    tap(page, "#tuneBtn", after=700, frm=(-90, 30))
    # Then the next pose, drawn over the ghost of the first.
    artdraw.draw(page, [ground(), ball(400, 300)], canvas="#pad", logical=logical, tempo=1.5, pause_tempo=2.0,
                 set_ink=lambda pg, c, s: pg.evaluate("([c, s]) => { color = c; size = s; }", [c, s]))
    page.wait_for_timeout(500)
    page.evaluate("window.__fingerHide()"); page.wait_for_timeout(900)
    rec.stop()
    return whole(page)


def clip_hold(page, rec):
    flip_example(page)
    rec.start(); page.wait_for_timeout(500)
    # Page 1 is the top of the bounce: hold it for three beats, then play.
    badge = strip_frame(page, 0) + " .holdbadge"
    tap(page, badge, after=450)
    tap(page, badge, after=600)
    tap(page, "#play", after=2600, frm=(-60, 80))
    page.evaluate("window.__fingerHide()"); page.wait_for_timeout(600)
    rec.stop()
    return whole(page)


def clip_guides(page, rec):
    flip_example(page)
    rec.start(); page.wait_for_timeout(500)
    tap(page, "#tuneBtn", after=500, frm=(-90, 30))
    tap(page, "#arcGuideBtn", after=600, frm=(-120, 20))
    tap(page, "#tuneBtn", after=900, frm=(-90, 30))
    # The dotted path: close dots where the ball is slow, wide where it is fast.
    for i in (2, 4):
        tap(page, strip_frame(page, i), before=420, after=800)
    page.evaluate("window.__fingerHide()"); page.wait_for_timeout(800)
    rec.stop()
    return whole(page)



# ---- Pad's extras ---------------------------------------------------------------
# The rest of what Pad does with a drawing: more takes, the preview speed, a
# photo behind it, and exporting it. The whole phone screen again; the canvas
# on Paper, as every example is drawn.
def pad_ready(page):
    import artdraw
    page.evaluate("""() => { const t = window.SkriblCanvasSizes, id = t.SIZES.find(s => s.label === '4:3').id;
        document.querySelector(`#canvasSeg button[data-size='${id}']`).click(); }""")
    page.wait_for_timeout(300)
    page.evaluate(f"""() => {{ bgColor = '{artdraw.PAPER}'; canvasWrap.style.backgroundColor = bgColor;
        if (typeof updateVignette === 'function') updateVignette();
        if (typeof markBgSwatch === 'function') markBgSwatch(bgColor); setTool('pen');
        if (window.SkriblPressure) SkriblPressure.setEnabled(true); }}""")
    page.wait_for_timeout(200)


def pad_draw(page, strokes, tempo=3.0, end=True):
    import artdraw
    artdraw.draw(page, strokes, tempo=tempo, pause_tempo=max(2.0, tempo))
    if end:
        page.evaluate("() => { if (recording) endRecordingTake(); }")
        page.wait_for_timeout(700)
        page.evaluate("() => { try { toast.hidden = true; } catch (e) {} }")
    page.evaluate("() => window.__fingerHide && window.__fingerHide()")


def flower(k):
    """A flower in two takes: the stem and leaves, then the bloom."""
    from artdraw import PURPLE, Stroke as S
    if k == 0:
        return [S([(408, 520), (402, 420), (410, 320), (408, 250)], "contour", size=9),
                S([(406, 420), (360, 380), (330, 392), (362, 418), (406, 420)], "form", size=7),
                S([(410, 370), (456, 334), (486, 344), (456, 368), (410, 370)], "form", size=7)]
    petals = [S(ring(408 + 46 * __import__("math").cos(a), 210 + 46 * __import__("math").sin(a), 30, n=20), "contour",
                PURPLE, size=8, taper=(0.04, 0.04)) for a in [i * 2 * 3.14159 / 6 for i in range(6)]]
    return petals + [S(ring(408, 210, 18, n=16), "fill", "#ff6f91", size=12, taper=(0.04, 0.04))]


def clip_takes(page, rec):
    pad_ready(page)
    pad_draw(page, flower(0))
    rec.start(); page.wait_for_timeout(500)
    # A second take: Add take, draw, Done. The replay plays them back to back.
    tap(page, "#addTakePill", after=600)
    pad_draw(page, flower(1), tempo=3.2, end=False)
    page.wait_for_timeout(300)
    # While a take records, Record reads Done: tap it to end the take.
    if page.locator("#recordBtn").is_visible():
        tap(page, "#recordBtn", after=700, frm=(-60, 80))
    page.evaluate("() => { if (recording) endRecordingTake(); try { toast.hidden = true; } catch (e) {} }")
    page.wait_for_timeout(400)
    tap(page, "#playBtn", after=3600, frm=(-60, 80))
    page.evaluate("window.__fingerHide()"); page.wait_for_timeout(500)
    rec.stop()
    return whole(page)


def clip_speed(page, rec):
    import artworks
    pad_ready(page)
    pad_draw(page, artworks.snail())
    rec.start(); page.wait_for_timeout(500)
    tap(page, "#tuneBtn", after=500, frm=(-90, 30))
    tap(page, '#speedSeg [data-rate="2"]', after=500, frm=(-80, 40))
    tap(page, "#tuneBtn", after=500, frm=(-90, 30))
    # The replay at double speed: only Play here; what posts is real time.
    tap(page, "#playBtn", after=4000, frm=(-60, 80))
    page.evaluate("window.__fingerHide()"); page.wait_for_timeout(500)
    rec.stop()
    return whole(page)


def sky_photo():
    """A photo to put behind the drawing: an evening sky over hills, made
    here so the clip carries no one's picture."""
    import io as _io
    from PIL import Image, ImageDraw, ImageFilter
    w, h = 1200, 900
    im = Image.new("RGB", (w, h))
    d = ImageDraw.Draw(im)
    for y in range(h):
        u = y / h
        d.line([(0, y), (w, y)], fill=(int(255 - 70 * u), int(196 - 90 * u), int(160 + 40 * u)))
    d.ellipse((760, 260, 940, 440), fill=(255, 236, 190))
    d.polygon([(0, 640), (260, 520), (520, 610), (820, 500), (1200, 600), (1200, 900), (0, 900)], fill=(120, 96, 150))
    d.polygon([(0, 760), (400, 660), (760, 740), (1200, 680), (1200, 900), (0, 900)], fill=(76, 64, 108))
    im = im.filter(ImageFilter.GaussianBlur(1.2))
    buf = _io.BytesIO(); im.save(buf, "JPEG", quality=88)
    return buf.getvalue()


def clip_photo(page, rec):
    import artworks
    pad_ready(page)
    pad_draw(page, artworks.cat())
    rec.start(); page.wait_for_timeout(500)
    tap(page, "#mediaOpenBtn", after=600, frm=(-70, -60))
    tap(page, "#mediaTabPhoto", after=500)
    with page.expect_file_chooser() as fc:
        tap(page, "#photoUploadBtn", after=200)
    fc.value.set_files(files=[{"name": "evening.jpg", "mimeType": "image/jpeg", "buffer": sky_photo()}])
    page.wait_for_timeout(1800)
    tap(page, "#mediaOpenBtn", after=1200, frm=(-70, -60))
    page.evaluate("window.__fingerHide()"); page.wait_for_timeout(600)
    rec.stop()
    return whole(page)


def clip_export(page, rec):
    import artworks
    pad_ready(page)
    pad_draw(page, artworks.cat())
    rec.start(); page.wait_for_timeout(500)
    tap(page, "#menuBtn", after=600, frm=(-60, 80))
    tap(page, "#exportItem", after=800)
    # The choices: a still, a video with its music, a looping GIF.
    tap(page, "#exportGif", after=2600)
    page.evaluate("window.__fingerHide()"); page.wait_for_timeout(600)
    rec.stop()
    return whole(page)



def clip_zoom(page, rec):
    """Zoom, on a desktop: the magnifier in the dock, + and -, and a scroll to
    look around. On a phone it is a two-finger pinch, which one fingertip
    cannot show honestly (owner: yes to filming it on desktop)."""
    import artworks
    pad_ready(page)
    pad_draw(page, artworks.cat())
    # Magnify's one-time tip and toast would stack over the top of the canvas, cut by
    # the crop; the card says what they say.
    page.evaluate("() => { if (window.SkriblHints) SkriblHints.show = () => {}; window.showToast = () => {}; }")
    rec.start(); page.wait_for_timeout(500)
    tap(page, "#magnifyBtn", after=600, frm=(-80, -60))
    tap(page, "#zoomInBtn", after=500, frm=(-60, 40))
    tap(page, "#zoomInBtn", after=700, frm=(0, 0))
    # Zoom always centres; scrolling moves the view round the drawing.
    box = page.locator(".canvas-wrap").first.bounding_box()
    cx, cy = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
    glide(page, (cx + 80, cy + 60), (cx, cy), 400)
    for dx, dy in ((0, -60), (0, -60), (90, 0), (90, 0), (-90, 60), (-90, 60)):
        page.mouse.wheel(dx, dy); page.wait_for_timeout(260)
    page.wait_for_timeout(300)
    tap(page, "#zoomOutBtn", after=450, frm=(-60, 40))
    tap(page, "#zoomOutBtn", after=700, frm=(0, 0))
    page.evaluate("window.__fingerHide()"); page.wait_for_timeout(500)
    rec.stop()
    # The canvas and the dock under it, not the empty desktop either side, so
    # the drawing and the magnifier's controls fill the frame.
    r = page.evaluate("""() => { const a = document.querySelector('.canvas-wrap').getBoundingClientRect();
        const d = document.getElementById('magnifyBtn').closest('[class*="dock"]') || document.getElementById('magnifyBtn');
        const b = d.getBoundingClientRect();
        return [Math.min(a.left, b.left), a.top, Math.max(a.right, b.right), Math.max(a.bottom, b.bottom)]; }""")
    pad = 18
    x0, y0 = max(0, r[0] - pad), max(0, r[1] - pad)
    w = min(page.viewport_size["width"], r[2] + pad) - x0
    h = min(page.viewport_size["height"], r[3] + pad) - y0
    return (x0, y0, int(w) // 2 * 2, int(h) // 2 * 2)


CLIPS = {"music": clip_music, "post": clip_post, "select": clip_select, "liquify": clip_liquify,
         "smudge": clip_smudge, "blur": clip_blur, "fill": clip_fill, "stamp": clip_stamp,
         "artmove": clip_artmove, "inbetween": clip_inbetween, "smear": clip_smear, "onion": clip_onion,
         "hold": clip_hold, "guides": clip_guides, "takes": clip_takes, "speed": clip_speed,
         "photo": clip_photo, "export": clip_export, "zoom": clip_zoom}
# The editor a clip is filmed in, when not Pad.
ROUTE = {k: "/flip" for k in ("select", "liquify", "smudge", "blur", "fill", "stamp", "artmove",
                               "inbetween", "smear", "onion", "hold", "guides")}
# Where a clip is recorded, when not the tall phone screen above.
# A phone's own screen, all of it. The techniques and extras use a SHORTER
# phone (390 x 640): still the whole screen, so every tap stays in frame, but
# less empty page, so they are bigger in their cards (owner: "they're small").
# Post and Add music keep the tall screen their sheets need.
STEPS = ("inbetween", "smear", "onion", "hold", "guides", "takes", "speed", "photo", "export")
VIEWPORT = {k: (390, 844) for k in ("music", "post")}
VIEWPORT.update({k: (390, 640) for k in STEPS})
VIEWPORT["zoom"] = (1024, 768)   # a desktop: the magnifier lives in its dock
# The clips filmed as a whole screen, shown as a phone in a tall card.
SCREEN = ("music", "post", "zoom") + STEPS


# Driving a 2x page makes every gesture take about half again as long as it
# was scripted to, so clips play back at this rate to move at a hand's speed
# (a touch brisker since the owner asked for shorter clips).
SPEED = 1.6
# ...except the whole-screen clips, which teach a sequence of taps and play at
# real speed with a beat after each tap (owner: "they go too fast, it's hard
# to follow").
SCREEN_SPEED = 1.0
TAP_REST = 0


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


def encode(frames, crop, out, speed=None):
    speed = speed or SPEED
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
        vf = f"crop={w}:{h}:{x}:{y},setpts=PTS/{speed}{fit},fps=30,format=yuv420p"
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
    global TAP_REST
    TAP_REST = 350 if name in SCREEN else 0
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
    encode(rec.frames, crop, out, SCREEN_SPEED if name in SCREEN else SPEED)
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
