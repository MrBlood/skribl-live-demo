#!/usr/bin/env python3
"""One music editor on both editors (owner: "it needs to be the same music
editor on both pad and flip").

The drawer's markup was one file and its arithmetic was shared, but every
control's wiring was written twice, once for the Pad and once for Flip, and the
copies had drifted. lib/musicdrawer.js is the one copy now. Each row below is
driven on BOTH editors, and each was red on one of them before:

  * Crossfade carried a playing preview over to the new join on Flip only;
  * Test Seam played the join on the Pad and the loop's top, twice, on Flip,
    and with a crossfade set the Pad played the whole clip three times;
  * Preview Loop's fallback played the baked clip on the Pad and the raw
    track, where no crossfade is heard, on Flip;
  * the Pad saved a trim only when the finger was let go ON the strip;
  * Match Drawing Time counted Flip's pages at one frame each, holds and all,
    and set a 0.5 s loop on a Flip with nothing drawn;
  * the switch, off, left the Pad's gapless loop and any preview playing, and
    on again mid-Play the Pad's music did not come back;
  * the Pad dropped a switched-off track from its draft and autosave (the song
    was lost), where Flip kept it;
  * a new track kept the Pad's last zoom, focus and scroll;
  * the Pad's Preview Loop played at the replay's speed, pitch and all;
  * Flip took a photo named song.mp3 as far as a failed decode;
  * Flip's Play left a preview playing under it;
  * Flip's file input was invisible and still reached by Tab, and the two
    editors named the step size's buttons differently (Each tap's, now).

Rows that pass on the old code too pin what must not change: the side that
was already right.
"""
import io
import json
import math
import os
import pathlib
import re
import struct
import sys
import urllib.request
import wave

from assertions import make_check
import browsing

try:
    from playwright.sync_api import sync_playwright
except ImportError as exc:
    print(f"SUITE-SKIPPED: {exc}")
    print("No assertions were executed. This is NOT evidence the music drawer is one.")
    raise SystemExit(77)

BASE = os.environ.get("SKRIBL_BASE", "http://127.0.0.1:5001")
ROOT = pathlib.Path(__file__).resolve().parent.parent
STATIC = ROOT / "skribl" / "static"
TPL = ROOT / "skribl" / "templates" / "skribl"
results = []
check = make_check(results, with_detail=True)
EDITORS = (("Pad", "/"), ("Flip", "/flip"))


def _wav(seconds=6.0, rate=22050, f0=220.0):
    buf = io.BytesIO()
    w = wave.open(buf, "wb")
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate)
    w.writeframes(b"".join(struct.pack("<h", int(9000 * math.sin(2 * math.pi * (f0 + 30 * i / rate) * i / rate)))
                           for i in range(int(seconds * rate))))
    w.close()
    return buf.getvalue()


TRACK = {"name": "tone.wav", "mimeType": "audio/wav", "buffer": _wav()}
TRACK2 = {"name": "other.wav", "mimeType": "audio/wav", "buffer": _wav(5.0, f0=330.0)}
# A photo's bytes under a song's name: the type says what it is.
PNG = bytes.fromhex("89504e470d0a1a0a0000000d4948445200000001000000010806000000"
                    "1f15c4890000000d49444154789c6300010000050001"
                    "0d0a2db40000000049454e44ae426082")

# Flip's pages, each drawn, each held `hold` frames (lib/holdtiming.js).
PAGES = """(o) => { frames.length = 0;
  for (let k = 0; k < o.n; k++) { const f = newFrame(); const pts = [];
    for (let j = 0; j < 12; j++) pts.push({ x: CW * (0.1 + 0.2 * k) + j * 6, y: CH * 0.3 + j * 12, color: '#7c5cff', size: 10, t: j * 5, start: j === 0 });
    f.strokes.push(...pts); f.strokeGroups.push(pts.length); if (o.hold > 1) f.hold = o.hold; frames.push(f); }
  fps = o.fps; idx = 0; buildStrip(); render(); updateToolState(); }"""

STOREKEY = {"Pad": "skribl_autosave_v1", "Flip": "skribl_flip_autosave_v1"}
SAVED_END = "(k) => { try { const d = JSON.parse(localStorage.getItem(k) || 'null'); return d && d.musicMeta ? d.musicMeta.trimEnd : null; } catch (e) { return 'unreadable'; } }"


def take(pg):
    """The Pad: one slow stroke, about two seconds, recorded, so there is a
    drawing that is still playing when a row looks."""
    box = pg.evaluate("() => { const r = document.getElementById('canvas').getBoundingClientRect(); return { x: r.x, y: r.y }; }")
    pg.mouse.move(box["x"] + 80, box["y"] + 80); pg.mouse.down()
    for k in range(40):
        pg.mouse.move(box["x"] + 80 + k * 6, box["y"] + 80 + k * 3); pg.wait_for_timeout(50)
    pg.mouse.up()
    pg.wait_for_timeout(300)
    pg.click("#recordBtn"); pg.wait_for_timeout(700)


PLAY = {"Pad": "#playBtn", "Flip": "#play"}


def editor(b, name, path, *, init=None, drawn=True, track=True, level="fine"):
    pg = b.new_page(viewport={"width": 1280, "height": 900})
    if init:
        pg.add_init_script(init)
    browsing.goto(pg, BASE, path)
    pg.evaluate("() => window.SkriblHints && window.SkriblHints.hide()")
    if drawn:
        if name == "Pad":
            take(pg)
        else:
            pg.evaluate(PAGES, {"n": 2, "fps": 12, "hold": 1})
    if track:
        browsing.pad_drawer(pg, "music")
        pg.set_input_files("#musicInput", TRACK)
        pg.wait_for_function("() => document.getElementById('musicUploadBtn').classList.contains('loaded') && !!currentAudioBuffer",
                             timeout=20000)
        pg.wait_for_timeout(400)
        # The same loop on both, the whole 6 s track with a clean cut: a new
        # track starts on Skribl's pick (fitted to the Pad's drawing, with a
        # smooth restart), which is right and not what these ask, and the pick
        # has its own suite (verify_musiclevels.py).
        pg.evaluate("() => { trimStart = 0; trimEnd = audioDuration; loopCrossfadeMs = 0; setCrossfadeUI(); updateTrimUI(); }")
        # Most rows press a control only Fine-tune shows (Hear the whole loop,
        # Smooth restart's length), so they start there, as a person would.
        if level:
            pg.click({"simple": "#musicLevelSimple", "adjust": "#fineTuneTrim", "fine": "#fineTuneToggle"}[level])
            pg.wait_for_timeout(450)
            browsing.wait_scroll_still(pg)   # Fine-tune glides its waveform into view
    return pg


def slide(pg, sel, value):
    pg.evaluate("([s, v]) => { const e = document.querySelector(s); e.value = String(v); e.dispatchEvent(new Event('input', { bubbles: true })); }",
                [sel, value])


def fine(pg):
    pg.evaluate("() => { const t = document.getElementById('fineTuneToggle'); if (t.getAttribute('aria-pressed') !== 'true') t.click(); }")
    pg.wait_for_timeout(450)


print("\nMUSIC — one drawer, in the source")
_tpl = {n: (TPL / f).read_text(encoding="utf-8") for n, f in (("Pad", "skribl_editor.html"), ("Flip", "skribl_flip.html"))}
_js = {"Pad": "\n".join([(STATIC / "app.js").read_text(encoding="utf-8")] +
                        [f.read_text(encoding="utf-8") for f in sorted(STATIC.glob("editor_*.js"))]),
       "Flip": (STATIC / "flip.js").read_text(encoding="utf-8")}
_code = {k: re.sub(r"(?m)^\s*//.*$", "", re.sub(r"/\*.*?\*/", "", v, flags=re.S)) for k, v in _js.items()}
check("both editors load lib/musicdrawer.js and wire their drawer through it",
      all("lib/musicdrawer.js" in _tpl[n] and "SkriblMusicDrawer.wire(" in _code[n] for n in _tpl),
      {n: ("lib/musicdrawer.js" in _tpl[n], "SkriblMusicDrawer.wire(" in _code[n]) for n in _tpl})
_COPIES = ("dragHandle", "dragRangeWindow", "dragZoomHandle", "dragZoomPan", "nudgeTrim", "updateNudgeStepLabel",
           "setLoopToDrawingLength", "startLoopPreview", "startLoopPreviewNative", "stopSeamTest",
           "playBuiltLoopPreview", "previewTick", "stepZoomMag", "syncZoomFocusButtons", "initZoomMagControl",
           "initFineTuneMode")
_own = {n: sorted(f for f in _COPIES if re.search(r"(?m)^\s*(?:async\s+)?function\s+" + f + r"\s*\(", _code[n])) for n in _code}
_built = {n: [m for m in ("zoom-pan-row", "crossfade-row") if m in _code[n]] for n in _code}
check("neither editor keeps its own copy of a drawer control, nor builds the Scroll or Crossfade row",
      not any(_own.values()) and not any(_built.values()), {"functions": _own, "rows by script": _built})
_served = {}
for _n, _p in EDITORS:
    with urllib.request.urlopen(BASE.rstrip("/") + _p) as _r:
        _served[_n] = _r.read().decode("utf-8")
check("the Scroll and Crossfade rows are in the drawer's markup as served, on both",
      all(s.count('id="zoomPanSlider"') == 1 and s.count('id="crossfadeSlider"') == 1 for s in _served.values()),
      {n: (s.count('id="zoomPanSlider"'), s.count('id="crossfadeSlider"')) for n, s in _served.items()})
check("the Pad's dead \"Plays for\" label is gone (the loop's summary wrote over it on the first trim)",
      "matchDrawingLabel" not in _served["Pad"] and "matchDrawingLabel" not in _code["Pad"],
      "the span, and the three writers that never found it")

with sync_playwright() as p:
    b = p.chromium.launch()

    print("\nMUSIC — the same markup on both")
    _marks = {}
    for _n, _p in EDITORS:
        pg = editor(b, _n, _p, drawn=False, track=False)
        _marks[_n] = pg.evaluate("""() => {
            const q = (id) => document.getElementById(id), inp = q('musicInput');
            const out = (el) => !el || getComputedStyle(el).display === 'none' || el.tabIndex < 0;
            return { inputs: document.querySelectorAll('#musicInput').length,
                     inPanel: !!(inp && inp.closest('#musicPanel')), musicOutOfTab: out(inp),
                     othersOutOfTab: ['imageInput', 'photoInput', 'draftInput'].every(i => out(q(i))),
                     steps: [...document.querySelectorAll('#musicStepSeg button')].map(b => b.dataset.step + ':' + b.textContent) }; }""")
        pg.close()
    check("one #musicInput, the drawer's own, out of the Tab order on both (Flip's was invisible and reached by Tab)",
          all(m["inputs"] == 1 and m["inPanel"] and m["musicOutOfTab"] for m in _marks.values()),
          {n: (m["inputs"], m["inPanel"], m["musicOutOfTab"]) for n, m in _marks.items()})
    check("...and Flip's photo and backup inputs are out of it too",
          all(m["othersOutOfTab"] for m in _marks.values()), {n: m["othersOutOfTab"] for n, m in _marks.items()})
    check("Each tap's steps are named the same on both",
          _marks["Pad"]["steps"] == _marks["Flip"]["steps"] and len(_marks["Pad"]["steps"]) == 4,
          {n: m["steps"] for n, m in _marks.items()})

    print("\nMUSIC — Crossfade, Preview Loop and Test Seam")
    for _n, _p in EDITORS:
        pg = editor(b, _n, _p)
        pg.click("#previewLoopBtn"); pg.wait_for_timeout(700)
        a = pg.evaluate("() => { const s = _waLoop.source(); window.__src = s; return s ? s.buffer.duration : null; }")
        slide(pg, "#crossfadeSlider", 200); pg.wait_for_timeout(500)
        z = pg.evaluate("() => { const s = _waLoop.source(); return { fresh: !!s && s !== window.__src, dur: s ? s.buffer.duration : null, on: previewingLoop }; }")
        check(f"{_n}: Crossfade carries a playing Preview Loop over to the new join",
              a is not None and z["fresh"] and z["on"] and z["dur"] is not None and z["dur"] < a - 0.15,
              f"clip {a} s before, after: {z}")
        pg.click("#previewLoopBtn"); pg.wait_for_timeout(200)
        # Test Seam with the crossfade still set: the playhead, read on every
        # frame, should start in the clip's last 1.25 s, come round, and stop.
        pg.evaluate("""() => { window.__seen = []; const ph = document.getElementById('playhead');
            const t0 = performance.now();
            (function tick() { window.__seen.push([performance.now() - t0, ph.hidden ? null : parseFloat(ph.style.left), previewingLoop]);
              if (performance.now() - t0 < 4500) requestAnimationFrame(tick); })(); }""")
        pg.click("#testSeamBtn"); pg.wait_for_timeout(4800)
        seen = pg.evaluate("() => window.__seen")
        tr = pg.evaluate("() => [trimStart, trimEnd, audioDuration, loopCrossfadeMs]")
        shown = [v for _, v, _ in seen if v is not None]
        clip_end = (tr[1] - tr[3] / 1000) / tr[2] * 100
        first_ok = bool(shown) and shown[0] >= (clip_end - (1.25 + 0.3) / tr[2] * 100)
        came_round = any(shown[j] < shown[j - 1] - 5 for j in range(1, len(shown)))   # it went back
        stopped = bool(seen) and seen[-1][2] is False and seen[-1][1] is None
        check(f"{_n}: Test Seam plays the join, crossfade and all: the loop's end, then its start, then it stops",
              first_ok and came_round and stopped,
              f"first {shown[:1]} (join at {clip_end:.0f}%), came round {came_round}, stopped {stopped}, "
              f"{len(shown)} frames with the playhead shown")
        pg.close()

    HANG = """
      const AC = window.AudioContext || window.webkitAudioContext;
      Object.defineProperty(AC.prototype, 'state', { configurable: true, get() { return 'suspended'; } });
      AC.prototype.resume = function () { return new Promise(() => {}); };   // never settles
      window.__plays = [];
      const play = HTMLMediaElement.prototype.play;
      HTMLMediaElement.prototype.play = function () {
        window.__plays.push({ loop: this.loop, track: typeof audioEl !== 'undefined' && this === audioEl });
        return play.apply(this, arguments); };"""
    for _n, _p in EDITORS:
        pg = editor(b, _n, _p, init=HANG)
        pg.evaluate("() => { window.__plays = []; document.getElementById('previewLoopBtn').click(); }")
        pg.wait_for_timeout(1300)
        plays = pg.evaluate("() => window.__plays")
        check(f"{_n}: with no Web Audio, Preview Loop loops the baked clip (the posted loop), not the raw track",
              any(x["loop"] and not x["track"] for x in plays) and not any(x["track"] for x in plays), str(plays))
        pg.close()

    for _n, _p in EDITORS:
        pg = editor(b, _n, _p)
        if _n == "Pad":
            pg.evaluate("() => { replayRate = 2; }")
        pg.click("#previewLoopBtn"); pg.wait_for_timeout(700)
        rate = pg.evaluate("() => { const s = _waLoop.source(); return s ? s.playbackRate.value : null; }")
        check(f"{_n}: Preview Loop plays the loop as posted, at 1x, whatever the replay's speed",
              rate == 1, f"playbackRate {rate} with the replay at {'2x' if _n == 'Pad' else 'its own pace'}")
        pg.close()

    print("\nMUSIC — the loop's edges are saved where they land")
    for _n, _p in EDITORS:
        pg = editor(b, _n, _p)
        pg.wait_for_timeout(1800)                        # the add's own save lands first
        before = pg.evaluate(SAVED_END, STOREKEY[_n])
        r = pg.evaluate("() => { const h = document.getElementById('handleEnd').getBoundingClientRect(), t = document.getElementById('musicTrack').getBoundingClientRect();"
                        " return { hx: h.x + h.width / 2, hy: h.y + h.height / 2, tx: t.x, tw: t.width, ty: t.y + t.height }; }")
        pg.mouse.move(r["hx"], r["hy"]); pg.mouse.down()
        pg.mouse.move(r["tx"] + r["tw"] * 0.5, r["hy"], steps=8)
        pg.mouse.move(r["tx"] + r["tw"] * 0.25, r["ty"] + 140, steps=6)    # off the strip
        pg.mouse.up()
        pg.wait_for_timeout(1900)
        live, after = pg.evaluate("() => trimEnd"), pg.evaluate(SAVED_END, STOREKEY[_n])
        check(f"{_n}: a loop's edge dragged and let go off the strip is saved",
              isinstance(after, (int, float)) and abs(after - live) < 0.02 and abs(live - (before or 0)) > 0.3,
              f"saved {before} before, {after} after; the loop's end is {live}")
        pg.close()

    print("\nMUSIC — Fit my drawing (it was Match Drawing Time)")
    pg = editor(b, "Pad", "/")
    want = pg.evaluate("() => getPlaybackDuration() / 1000")
    pg.click("#matchDrawingBtn"); pg.wait_for_timeout(200)
    got = pg.evaluate("() => trimEnd - trimStart")
    check("Pad: Fit my drawing sets the loop to the replay's length",
          abs(got - max(0.5, min(want, 6))) < 0.02, f"loop {got:.2f} s for a {want:.2f} s replay")
    pg.close()
    pg = editor(b, "Flip", "/flip", drawn=False)
    pg.evaluate(PAGES, {"n": 3, "fps": 12, "hold": 8})
    pg.click("#matchDrawingBtn"); pg.wait_for_timeout(200)
    got = pg.evaluate("() => trimEnd - trimStart")
    check("Flip: Fit my animation counts each page at its own length (three pages held 8 at 12 fps is 2 s)",
          abs(got - 2.0) < 0.02, f"loop {got:.2f} s; pages over fps would say 0.25, and the 0.5 s floor")
    pg.close()
    pg = editor(b, "Flip", "/flip", drawn=False)
    before = pg.evaluate("() => trimEnd - trimStart")
    off = pg.evaluate("() => { const f = document.getElementById('matchDrawingBtn'); f.click(); return f.disabled; }")
    pg.wait_for_timeout(200)
    got = pg.evaluate("() => trimEnd - trimStart")
    check("Flip: with nothing drawn, Fit my animation is off and leaves the loop alone, as the Pad's does",
          off and abs(got - before) < 0.001, f"disabled {off}; {before:.2f} s -> {got:.2f} s")
    pg.close()

    print("\nMUSIC — the switch")
    for _n, _p in EDITORS:
        pg = editor(b, _n, _p)
        pg.click(PLAY[_n]); pg.wait_for_timeout(600)
        on = pg.evaluate("() => _waLoop.playing()")
        pg.evaluate("() => document.getElementById('musicToggle').click()"); pg.wait_for_timeout(250)
        off = pg.evaluate("() => ({ wa: _waLoop.playing(), el: !audioEl || audioEl.paused, play: playing })")
        check(f"{_n}: the switch, off, silences Play's music while the drawing plays on",
              on and not off["wa"] and off["el"] and off["play"], f"music playing before: {on}; after: {off}")
        pg.close()
    for _n, _p in EDITORS:
        pg = editor(b, _n, _p)
        pg.evaluate("() => document.getElementById('musicToggle').click()"); pg.wait_for_timeout(150)
        pg.click(PLAY[_n]); pg.wait_for_timeout(500)
        quiet = pg.evaluate("() => _waLoop.playing()")
        pg.evaluate("() => document.getElementById('musicToggle').click()"); pg.wait_for_timeout(500)
        back = pg.evaluate("() => ({ wa: _waLoop.playing(), play: playing, on: musicEnabled })")
        check(f"{_n}: switched on again mid-Play, the music comes back",
              not quiet and back["wa"] and back["play"] and back["on"], f"before {quiet}, after {back}")
        pg.close()
    for _n, _p in EDITORS:
        pg = editor(b, _n, _p)
        pg.click("#previewLoopBtn"); pg.wait_for_timeout(600)
        pg.evaluate("() => document.getElementById('musicToggle').click()"); pg.wait_for_timeout(250)
        st = pg.evaluate("() => ({ wa: _waLoop.playing(), on: previewingLoop, btn: document.getElementById('previewLoopBtn').textContent })")
        check(f"{_n}: the switch, off, stops a preview, and Hear the whole loop says so",
              not st["wa"] and not st["on"] and st["btn"] == "Hear the whole loop", str(st))
        pg.close()

    print("\nMUSIC — a switched-off track is kept, and left out of a post")
    pg = editor(b, "Pad", "/")
    pg.evaluate("() => document.getElementById('musicToggle').click()"); pg.wait_for_timeout(200)
    snap = pg.evaluate("() => { const m = serializeSkribl().frames[0].music; return m ? { data: !!m.data, enabled: m.enabled } : null; }")
    meta = pg.evaluate("() => { const m = currentMusicMeta(); return m ? m.enabled : 'none'; }")
    check("Pad: a draft keeps a switched-off track, marked off, as Flip's does (it was dropped, song and all)",
          snap is not None and snap["data"] and snap["enabled"] is False, str(snap))
    check("Pad: the autosave remembers the switch", meta is False, f"musicMeta.enabled {meta!r}")
    pg.evaluate("() => { window.__draft = serializeSkribl(); }")
    pg.evaluate("() => document.getElementById('musicToggle').click()"); pg.wait_for_timeout(150)   # on again...
    pg.evaluate("() => loadSkribl(window.__draft)")                                                 # ...then the draft
    try:   # a draft that dropped its track has nothing to wait for
        pg.wait_for_function("() => document.getElementById('musicUploadBtn').classList.contains('loaded')", timeout=8000)
    except Exception:
        pass
    pg.wait_for_timeout(500)
    back = pg.evaluate("() => ({ on: musicEnabled, sw: document.getElementById('musicToggle').getAttribute('aria-checked'),"
                       " meta: document.getElementById('musicBtnMeta').textContent })")
    check("Pad: the draft opens with its track switched off, and the row says Muted",
          back["on"] is False and back["sw"] == "false" and back["meta"].startswith("Muted"), str(back))
    pg.evaluate("() => { window.SkriblCompose = { deliver: (p) => { window.__posted = p; } }; }")
    pg.click("#postBtn"); pg.wait_for_timeout(500)
    pg.fill("#postTitleInput", "switched off")
    pg.click("#postSubmitBtn")
    pg.wait_for_function("() => !!window.__posted", timeout=20000)
    posted = pg.evaluate("() => window.SkriblPayload.currentFrameMedia(window.__posted).music")
    check("Pad: the post leaves the switched-off track out", posted is None, f"music in the post: {str(posted)[:80]}")
    pg.close()
    pg = editor(b, "Flip", "/flip")
    pg.evaluate("() => document.getElementById('musicToggle').click()"); pg.wait_for_timeout(200)
    fl = pg.evaluate("() => ({ post: buildSharePayload().frames[0].music || null, kept: !!musicData })")
    check("Flip: the post leaves the switched-off track out, and the track stays", fl["post"] is None and fl["kept"], str(fl)[:120])
    pg.close()

    print("\nMUSIC — a new track, a new view")
    for _n, _p in EDITORS:
        pg = editor(b, _n, _p)
        fine(pg)
        pg.click("#zoomMagIn"); pg.click("#zoomMagIn"); slide(pg, "#zoomPanSlider", 800); pg.wait_for_timeout(150)
        moved = pg.evaluate("() => [zoomMag, zoomFocus]")
        pg.set_input_files("#musicInput", TRACK2)
        pg.wait_for_function("() => Math.abs(audioDuration - 5) < 0.05", timeout=20000); pg.wait_for_timeout(500)
        v = pg.evaluate("() => ({ mag: zoomMag, focus: zoomFocus, center: zoomCenter, val: document.getElementById('zoomMagVal').textContent,"
                        " lit: [...document.querySelectorAll('.zoom-mag-btn.on')].map(b => b.dataset.focus) })")
        check(f"{_n}: a new track starts on its whole loop at 1x (the last song's zoom and scroll were kept)",
              moved[0] > 1 and moved[1] == "free" and v["mag"] == 1 and v["focus"] == "loop" and v["center"] is None
              and v["val"] == "1×" and v["lit"] == ["loop"], f"before {moved}, after {v}")
        pg.close()

    print("\nMUSIC — Flip's own")
    for _n, _p in EDITORS:
        pg = editor(b, _n, _p, track=False)
        browsing.pad_drawer(pg, "music")
        pg.set_input_files("#musicInput", {"name": "song.mp3", "mimeType": "image/png", "buffer": PNG})
        pg.wait_for_timeout(600)
        said = pg.evaluate("() => (document.getElementById('flipChip') || document.getElementById('toast')).textContent")
        loaded = pg.evaluate("() => document.getElementById('musicUploadBtn').classList.contains('loaded')")
        check(f"{_n}: a photo named song.mp3 is refused by its type, in the same words",
              "not supported for audio" in said and not loaded, f"said {said!r}, loaded {loaded}")
        pg.close()
    for _n, _p in EDITORS:
        pg = editor(b, _n, _p)
        pg.click("#previewLoopBtn"); pg.wait_for_timeout(500)
        pg.click(PLAY[_n]); pg.wait_for_timeout(400)
        st = pg.evaluate("() => ({ on: previewingLoop, btn: document.getElementById('previewLoopBtn').textContent, play: playing })")
        check(f"{_n}: Play stops a preview first, so one thing plays", st["play"] and not st["on"] and st["btn"] == "Hear the whole loop", str(st))
        pg.close()
    b.close()

bad = [r for r in results if not r[0]]
print(f"\n{'=' * 62}\n{len(results) - len(bad)}/{len(results)} passed"
      + ("" if not bad else "  FAILURES: " + ", ".join(r[1] for r in bad)))
sys.exit(1 if bad else 0)
