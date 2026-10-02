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
FINGER = """() => {
  const f = document.createElement('div'); f.id = 'clipFinger';
  f.style.cssText = 'position:fixed;left:0;top:0;width:34px;height:34px;margin:-17px 0 0 -17px;' +
    'border-radius:50%;background:rgba(255,255,255,.34);box-shadow:0 0 0 2px rgba(255,255,255,.75),0 4px 14px rgba(0,0,0,.35);' +
    'pointer-events:none;z-index:2147483647;opacity:0;transition:opacity .18s, transform .12s;';
  document.body.appendChild(f);
  const at = e => { f.style.left = e.clientX + 'px'; f.style.top = e.clientY + 'px'; f.style.opacity = 1; };
  addEventListener('pointermove', at, true);
  addEventListener('pointerdown', e => { at(e); f.style.transform = 'scale(.82)'; }, true);
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
    page.mouse.down(); page.wait_for_timeout(110); page.mouse.up()
    page.wait_for_timeout(after)
    return x, y


def center(page, sel):
    b = page.locator(sel).bounding_box()
    return b["x"] + b["width"] / 2, b["y"] + b["height"] / 2


# ---- the clips ---------------------------------------------------------------
# Each returns the crop, in CSS px of the viewport: (x, y, w, h), 4:3.
def clip_music(page, rec):
    rec.start(); page.wait_for_timeout(500)
    tap(page, "#mediaOpenBtn")
    tap(page, "#mediaTabMusic")
    drop = page.locator("#musicInput").evaluate("i => { const z = i.closest('label, .drop, .media-drop, .pending-row') || i.parentElement; const r = z.getBoundingClientRect(); return [r.x + r.width / 2, r.y + r.height / 2]; }")
    glide(page, (drop[0] + 50, drop[1] + 80), drop, 420)
    page.mouse.down(); page.wait_for_timeout(110); page.mouse.up()
    page.set_input_files("#musicInput", {"name": "Bassline.wav", "mimeType": "audio/wav", "buffer": song()})
    page.wait_for_function("() => typeof currentAudioBuffer !== 'undefined' && !!currentAudioBuffer", timeout=20000)
    page.wait_for_timeout(900)
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
    page.evaluate("window.__fingerHide()"); page.wait_for_timeout(1100)
    rec.stop()
    tabs = page.locator("#mediaTabMusic").bounding_box()
    w = VW; h = round(w * 3 / 4)
    return (0, max(0, tabs["y"] - 10), w, h)


def clip_post(page, rec):
    # A drawing to post, drawn off camera by the same steps as the Draw example.
    import make_help_demos as demos
    page.evaluate("""() => { const t = window.SkriblCanvasSizes, id = t.SIZES.find(s => s.label === '4:3').id;
        document.querySelector(`#canvasSeg button[data-size='${id}']`).click(); }""")
    page.wait_for_timeout(300)
    demos.run(page, demos.demo_draw())
    # End the take, as you would before posting: the header shows Done, not
    # Post, while a take is being recorded.
    page.evaluate("() => { if (recording) endRecordingTake(); }")
    page.wait_for_timeout(600)
    rec.start(); page.wait_for_timeout(400)
    tap(page, "#postBtn", after=700)
    tx, ty = center(page, "#postTitleInput")
    glide(page, (tx + 60, ty + 80), (tx, ty), 380)
    page.mouse.down(); page.wait_for_timeout(100); page.mouse.up()
    page.keyboard.type("Sunny day", delay=90)
    rec.mark("pan")
    page.wait_for_timeout(450)
    tap(page, "#postSubmitBtn", before=700, after=300)
    page.wait_for_selector("#postResult:not([hidden])", timeout=15000)
    page.evaluate("window.__fingerHide()"); page.wait_for_timeout(1600)
    rec.stop()
    # The camera follows the finger: on the title while it is typed, then a
    # glide down to Post and "Posted!". Readable in a card on a phone, which a
    # frame holding the whole sheet would not be.
    lab = page.locator("#postTitleInput").bounding_box()
    res = page.locator("#postResult").bounding_box()
    w = VW; h = round(w * 3 / 4)
    y0 = max(0, lab["y"] - 30); y1 = max(y0, res["y"] + res["height"] + 14 - h)
    return (0, w, h, [(rec.marks["pan"], y0), (rec.marks["pan"] + 0.9, y1)])


CLIPS = {"music": clip_music, "post": clip_post}
# Where a clip is recorded, when not the tall phone screen above.
VIEWPORT = {}


# Driving a 2x page makes every gesture take about half again as long as it
# was scripted to, so clips play back at this rate to move at a hand's speed.
SPEED = 1.5


def held(frames, i):
    """How long frame i is shown. A still moment (a decode, a settle) holds at
    most 0.7 s: the clip shows the gesture, not the waiting. The last, 1.2 s."""
    ts = frames[i][0]
    nxt = frames[i + 1][0] if i + 1 < len(frames) else ts + 1.2
    return min(1.2 if i + 1 == len(frames) else 0.7, max(0.001, nxt - ts))


def clock(frames, t):
    """A moment on the recording's clock, on the clip's (stills shortened)."""
    out = 0.0
    for i, (ts, _) in enumerate(frames):
        d = held(frames, i)
        if t <= ts + d:
            return out + max(0.0, min(d, t - ts))
        out += d
    return out


def encode(frames, crop, out, size=(640, 480)):
    if len(crop) == 4 and isinstance(crop[3], list):
        # (x, w, h, [(t_a, y_a), (t_b, y_b)]): an eased pan between two framings.
        x, w, h = [round(v * DPR) for v in crop[:3]]
        (ta, ya), (tb, yb) = crop[3]
        ta, tb = clock(frames, ta), clock(frames, tb)
        ya, yb = round(ya * DPR), round(yb * DPR)
        u = f"clip((t-{ta:.3f})/{tb - ta:.3f}\\,0\\,1)"
        y = f"{ya}+({yb - ya})*{u}*{u}*(3-2*{u})"
    else:
        x, y, w, h = [round(v * DPR) for v in crop]
    with tempfile.TemporaryDirectory() as d:
        lst = []
        for i, (ts, png) in enumerate(frames):
            p = pathlib.Path(d) / f"f{i:05d}.png"; p.write_bytes(png)
            lst.append(f"file '{p}'\nduration {held(frames, i):.4f}")
        lst.append(f"file '{pathlib.Path(d) / f'f{len(frames) - 1:05d}.png'}'")
        (pathlib.Path(d) / "list.txt").write_text("\n".join(lst))
        vf = f"crop={w}:{h}:{x}:{y},setpts=PTS/{SPEED},scale={size[0]}:{size[1]}:flags=lanczos,fps=30,format=yuv420p"
        src = ["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(pathlib.Path(d) / "list.txt"), "-vf", vf]
        subprocess.run(src + ["-c:v", "libx264", "-profile:v", "high", "-crf", "23", "-preset", "slow",
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
