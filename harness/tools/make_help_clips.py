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
    # The drawer is opened off camera: the clip is about the song, so it opens
    # on "Add music" and spends its seconds on the waveform.
    page.locator("#mediaOpenBtn").click(); page.wait_for_timeout(500)
    page.locator("#mediaTabMusic").click(); page.wait_for_timeout(500)
    rec.start(); page.wait_for_timeout(350)
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
    # Framed on the panel in use, edge to edge of its content.
    tabs = page.locator("#mediaTabMusic").bounding_box()
    x0 = 12; w = VW - 2 * x0; h = round(w * 3 / 4)
    return (x0, max(0, tabs["y"] - 8), w, h)


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
    # THE CAMERA FOLLOWS THE FINGER, so every press is on screen: on the
    # header while Post is tapped, down to the title as it is typed, then to
    # the sheet's own Post button for the last tap and "Posted". The owner
    # could not see the buttons being pushed when the clip opened on the title.
    w = VW - 24; h = round(w * 3 / 4)
    ya = 0
    rec.start(); page.wait_for_timeout(400)
    tap(page, "#postBtn", after=550)
    rec.mark("sheet")
    tx, ty = center(page, "#postTitleInput")
    glide(page, (tx + 60, ty + 80), (tx, ty), 600)
    page.mouse.down(); page.wait_for_timeout(120); page.mouse.up()
    page.keyboard.type("Cat", delay=80)
    # Where things sit WHILE they are used: posting reflows the sheet, so a
    # measure taken at the end frames them wrong.
    lab = page.locator("#postTitleInput").bounding_box()
    sub = page.locator("#postSubmitBtn").bounding_box()
    yb = max(0, lab["y"] - 24)
    yc = max(yb, sub["y"] + sub["height"] + 20 - h)
    page.wait_for_timeout(250)
    rec.mark("submit")
    page.wait_for_timeout(500)
    tap(page, "#postSubmitBtn", before=500, after=250)
    page.wait_for_selector("#postResult:not([hidden])", timeout=15000)
    page.evaluate("window.__fingerHide()"); page.wait_for_timeout(1100)
    rec.stop()
    m = rec.marks
    return (12, w, h, [(m["sheet"], ya), (m["sheet"] + 0.8, yb), (m["submit"], yb), (m["submit"] + 0.8, yc)])


CLIPS = {"music": clip_music, "post": clip_post}
# Where a clip is recorded, when not the tall phone screen above.
VIEWPORT = {}


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
        vf = f"crop={w}:{h}:{x}:{y},setpts=PTS/{SPEED},fps=30,format=yuv420p"
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
    browsing.goto(page, BASE, "/skribl-pad")
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
