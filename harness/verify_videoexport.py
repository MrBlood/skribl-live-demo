"""The video both editors make where WebCodecs cannot make an MP4 (MediaRecorder
to WebM): it carries the music, it holds each page for its own time, and an
empty recording is never called a success.

The v321 outside audit (SK-AUD-001/002/003) ran Flip's exportWebM() in an
isolated Chromium and found: one video stream and no audio under a sheet that
says "Your animation, with music"; three pages decoded as four (red, red,
green, blue), because the first page was painted before recording started and
again on the first tick; and, with a recorder that produced nothing, a 0-byte
download and "Animation exported". The Pad mixed its music in but shared the
blind finish. Both now record through lib/videorecord.js.

WHAT IS ASKED, AND HOW IT IS READ
  * Tracks are read from the downloaded file itself: a small EBML walk over the
    WebM finds each TrackEntry's TrackType (1 video, 2 audio) and counts the
    video track's blocks -- one block per frame the encoder was given.
  * Frames are counted against the export's own plan: three pages at hold 1 and
    one loop are three units, so three frames, the first not doubled.
  * The failures are driven with a stand-in MediaRecorder that produces no
    data, raises an error, or produces bytes that are not a WebM; each must
    download nothing and say so, on both editors.
  * And one that hands back a WebM header with no frame behind it (after
    v325): the kind of file Chromium's recorder once made on a loaded
    machine. It passed the signature check, downloaded and said "Animation
    exported"; now the file must hold a frame.
  * And Gecko's recorder (after v326), as Firefox's first run on CI found it:
    asked for a type that names an audio codec when there is no audio track,
    it waits for one and never stops, so both editors sat at "Recording…". A
    stand-in that does the same goes in on each editor with no music: each
    must ask for a type with no audio codec, and its frames must come out.
  * Gecko's requestFrame is on the stream, not the track: with it moved there,
    Flip's three pages must still be three pushes and three frames (Firefox
    sampled the canvas instead, and kept about half). And a recorder that
    never answers its stop is given up on at the limit, saying so, with Cancel
    working while the stop is waited for, on both editors.
"""
import math
import os
import struct
import sys
import time

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


def wav_bytes(seconds, rate=22050):
    n = int(seconds * rate)
    body = b"".join(struct.pack("<h", int(9000 * math.sin(2 * math.pi * 440 * i / rate))) for i in range(n))
    return (b"RIFF" + struct.pack("<I", 36 + len(body)) + b"WAVEfmt "
            + struct.pack("<IHHIIHH", 16, 1, 1, rate, rate * 2, 2, 16)
            + b"data" + struct.pack("<I", len(body)) + body)


AUD = wav_bytes(3.0)

# EBML ids: containers walked into, leaves read.
SEGMENT, CLUSTER, TRACKS, TRACKENTRY, BLOCKGROUP = 0x18538067, 0x1F43B675, 0x1654AE6B, 0xAE, 0xA0
TRACKNUMBER, TRACKTYPE, SIMPLEBLOCK, BLOCK = 0xD7, 0x83, 0xA3, 0xA1


def _vint(b, i, marker):
    first, mask, n = b[i], 0x80, 1
    while n <= 8 and not first & mask:
        mask >>= 1
        n += 1
    v = first if marker else first & (mask - 1)
    for k in range(1, n):
        v = (v << 8) | b[i + k]
    return v, n


def webm(data):
    """{tracks: {number: type}, blocks: {number: count}} from a WebM's bytes.
    Containers are entered rather than skipped, which also copes with the
    unknown-size Segment and Clusters MediaRecorder writes."""
    tracks, blocks, cur, i = {}, {}, {}, 0
    while i < len(data) - 2:
        try:
            eid, a = _vint(data, i, True)
            size, b = _vint(data, i + a, False)
        except IndexError:
            break
        body = i + a + b
        if eid in (SEGMENT, CLUSTER, TRACKS, BLOCKGROUP):
            i = body
            continue
        if eid == TRACKENTRY:
            if cur.get("n"):
                tracks[cur["n"]] = cur.get("t")
            cur = {}
            i = body
            continue
        if eid in (TRACKNUMBER, TRACKTYPE):
            v = int.from_bytes(data[body:body + size], "big")
            cur["n" if eid == TRACKNUMBER else "t"] = v
        elif eid in (SIMPLEBLOCK, BLOCK):
            tn, _ = _vint(data, body, False)
            blocks[tn] = blocks.get(tn, 0) + 1
        i = body + size
    if cur.get("n"):
        tracks[cur["n"]] = cur.get("t")
    return {"tracks": tracks, "blocks": blocks}


def kinds(info):
    return sorted({1: "video", 2: "audio"}.get(t, str(t)) for t in info["tracks"].values())


def video_frames(info):
    return sum(c for n, c in info["blocks"].items() if info["tracks"].get(n) == 1)


PAGES = """(o) => { frames.length = 0;
  for (let k = 0; k < o.n; k++) { const f = newFrame(); const pts = [];
    for (let j = 0; j < 14; j++) pts.push({ x: CW * (0.1 + 0.2 * k) + j * 6, y: CH * 0.2 + j * 20, color: o.colors[k], size: 12, t: j * 5, start: j === 0 });
    f.strokes.push(...pts); f.strokeGroups.push(pts.length); frames.push(f); }
  fps = o.fps; exLoops = 1; idx = 0; buildStrip(); render(); updateToolState(); }"""

def _el(eid, payload):
    n = len(payload)
    return eid + (bytes([0x80 | n]) if n < 0x7F else bytes([0x40 | (n >> 8), n & 0xFF])) + payload


# What Chromium's recorder hands back when it stops before its first frame: an
# EBML header, a Segment of unknown size, its Info and Tracks (one video
# track), and no Cluster -- every byte valid, no frame anywhere.
HEADER_ONLY = (_el(b"\x1a\x45\xdf\xa3", _el(b"\x42\x86", b"\x01") + _el(b"\x42\x82", b"webm"))
               + b"\x18\x53\x80\x67\x01\xff\xff\xff\xff\xff\xff\xff"
               + _el(b"\x15\x49\xa9\x66", _el(b"\x2a\xd7\xb1", b"\x0f\x42\x40"))
               + _el(b"\x16\x54\xae\x6b", _el(b"\xae", _el(b"\xd7", b"\x01") + _el(b"\x83", b"\x01")
                                                 + _el(b"\x86", b"V_VP9"))))

# A MediaRecorder that records nothing, raises an error, hands back bytes that
# are not a video, a WebM header with no frame behind it, or never answers its
# stop at all. Installed over the real one for one export.
FAKE = """(mode) => { window.__RealMR = window.__RealMR || window.MediaRecorder;
  class Fake { constructor(stream, o) { this.state = 'inactive'; this.mimeType = (o && o.mimeType) || 'video/webm'; }
    static isTypeSupported() { return true; }
    start() { this.state = 'recording'; }
    stop() { this.state = 'inactive'; setTimeout(() => {
      if (mode === 'stall') return;          // never answers: no data, no stop
      if (mode === 'error' && this.onerror) this.onerror({ error: { name: 'EncodingError' } });
      const bytes = mode === 'garbage' ? 'not a video at all'
        : mode === 'headeronly' ? new Uint8Array(window.__headerOnly) : new Uint8Array([0x1a, 0x45, 0xdf, 0xa3, 1, 2, 3, 4]);
      if (mode !== 'empty' && this.ondataavailable) this.ondataavailable({ data: new Blob([bytes]) });
      if (this.onstop) this.onstop(); }, 30); } }
  window.MediaRecorder = Fake; }"""
REAL = "() => { if (window.__RealMR) window.MediaRecorder = window.__RealMR; }"
# GECKO'S RECORDER, as Firefox's first run on CI found it (after v326): asked
# for a type that names an audio codec when the stream has no audio track, it
# waits for one, and never starts or stops. Otherwise it is the real one.
# Every type it is asked for is kept in __asked.
GECKO = """() => { window.__RealMR = window.__RealMR || window.MediaRecorder; const Real = window.__RealMR;
  window.__asked = [];
  class Gecko {
    constructor(stream, o) { const t = (o && o.mimeType) || ''; window.__asked.push(t);
      this.mimeType = t; this.state = 'inactive';
      this.real = /opus/.test(t) && !stream.getAudioTracks().length ? null : new Real(stream, o); }
    static isTypeSupported(t) { return Real.isTypeSupported(t); }
    start() { this.state = 'recording'; const r = this.real; if (!r) return;
      r.ondataavailable = (e) => this.ondataavailable && this.ondataavailable(e);
      r.onerror = (e) => this.onerror && this.onerror(e);
      r.onstop = () => { this.state = 'inactive'; if (this.onstop) this.onstop(); };
      r.start(); }
    stop() { if (this.real) this.real.stop(); else this.state = 'inactive'; } }
  window.MediaRecorder = Gecko; }"""
# GECKO'S requestFrame, which is the canvas stream's, not its track's: moved
# there, counting each push in __pushed.
GECKO_SHAPE = """() => { const P = HTMLCanvasElement.prototype, cs = P.captureStream;
  window.__pushed = 0;
  P.captureStream = function (fps) { const s = cs.call(this, fps), t = s.getVideoTracks()[0];
    if (t && typeof t.requestFrame === 'function') { const rf = t.requestFrame.bind(t);
      Object.defineProperty(t, 'requestFrame', { value: undefined });
      s.requestFrame = function () { window.__pushed++; rf(); }; }
    return s; };
  window.__undoGecko = () => { P.captureStream = cs; }; }"""
# The MP4 path, told it can encode video and cannot encode AAC.
NO_AAC = """() => { const M = window.SkriblMp4; window.__realMp4 = window.__realMp4 || { prepare: M.prepare, aac: M.aacSupported };
  window.__aacAsked = false;
  M.prepare = async (w, h) => ({ w: w, h: h, codec: 'avc1.42001f' });
  M.aacSupported = async () => { window.__aacAsked = true; return false; }; }"""
REAL_MP4 = """() => { const M = window.SkriblMp4, r = window.__realMp4; if (r) { M.prepare = r.prepare; M.aacSupported = r.aac; } }"""


def flip_page(b):
    ctx = b.new_context(viewport={"width": 1100, "height": 800}, accept_downloads=True)
    pg = ctx.new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    browsing.goto(pg, BASE, "/flip")
    pg.wait_for_timeout(800)
    pg.evaluate("() => window.SkriblHints && window.SkriblHints.hide()")
    return ctx, pg, errs


def flip_export(pg, timeout=20000):
    with pg.expect_download(timeout=timeout) as dl:
        pg.evaluate("() => exportWebM()")
    data = open(dl.value.path(), "rb").read()
    pg.wait_for_timeout(200)
    return data, pg.evaluate("() => document.getElementById('flipChip').textContent")


def no_download(pg, trigger, wait=1500):
    got = []
    pg.on("download", lambda d: got.append(d))
    pg.evaluate(trigger)
    pg.wait_for_timeout(wait)
    return got


with sync_playwright() as p:
    b = p.chromium.launch()

    print("\nFLIP -- the WebM carries its frames and its music")
    ctx, pg, errs = flip_page(b)
    pg.evaluate(PAGES, {"n": 3, "fps": 4, "colors": ["#ff2020", "#20c020", "#2040ff"]})
    plain, plain_chip = flip_export(pg)
    pinfo = webm(plain)
    check("a WebM with no music on has one video track and no audio",
          kinds(pinfo) == ["video"], f"{pinfo['tracks']}")
    check("three pages at one beat each are three frames: the first page is not doubled",
          video_frames(pinfo) == 3, f"{video_frames(pinfo)} video frames, blocks {pinfo['blocks']}")
    check("...and the chip says it was exported", plain_chip == "Animation exported", plain_chip)

    pg.evaluate(GECKO)
    try:
        gk, gk_chip = flip_export(pg, timeout=15000)
        gk_said = f"{video_frames(webm(gk))} video frames, chip '{gk_chip}'"
        gk_ok = video_frames(webm(gk)) == 3 and gk_chip == "Animation exported"
    except Exception as e:
        gk_said, gk_ok = f"no video in 15 s ({type(e).__name__})", False
        pg.evaluate("() => { exporting = false; exportHide(); }")
    asked = pg.evaluate("() => window.__asked")
    pg.evaluate(REAL)
    check("with Gecko's recorder (it waits for any audio track a type names), Flip with no music asks for "
          "a type with no audio codec, and its three frames come out",
          gk_ok and bool(asked) and not any("opus" in t for t in asked), f"{gk_said}; asked {asked}")

    pg.evaluate(GECKO_SHAPE)
    try:
        gs, _ = flip_export(pg, timeout=15000)
        gs_n = video_frames(webm(gs))
    except Exception as e:
        gs_n = f"no video ({type(e).__name__})"
        pg.evaluate("() => { exporting = false; exportHide(); }")
    pushed = pg.evaluate("() => window.__pushed")
    pg.evaluate("() => window.__undoGecko()")
    check("with Gecko's requestFrame (on the stream, not the track), Flip pushes each of its three pages: "
          "three pushes, three frames", pushed == 3 and gs_n == 3, f"{pushed} pushes, {gs_n} video frames")

    pg.set_input_files("#musicInput", {"name": "t.wav", "mimeType": "audio/wav", "buffer": AUD})
    pg.wait_for_function("() => !!musicData && !!currentAudioBuffer", timeout=15000)
    pg.evaluate(PAGES, {"n": 3, "fps": 4, "colors": ["#ff2020", "#20c020", "#2040ff"]})
    on = pg.evaluate("() => musicEnabled && !musicMuted")
    withm, withm_chip = flip_export(pg)
    minfo = webm(withm)
    check("with music on, the WebM has a video track AND an audio track",
          on and kinds(minfo) == ["audio", "video"], f"music on: {on}, tracks {minfo['tracks']}")
    check("...the audio track carries sound, block after block, and the video still has its three frames",
          sum(c for n, c in minfo["blocks"].items() if minfo["tracks"].get(n) == 2) >= 5 and video_frames(minfo) == 3,
          str(minfo["blocks"]))
    check("...and the chip says simply that it was exported", withm_chip == "Animation exported", withm_chip)

    # THE ROUTE THE AUDIT'S FINDING TAKES IN REAL LIFE (the owner's note on
    # SK-AUD-001): music on is what sends Flip to the WebM, because the MP4
    # declines when the browser cannot encode AAC rather than ship a silent
    # MP4. Driven through exportVideo() -- the Video button's own route -- with
    # the MP4 path told it CAN encode video and CANNOT encode AAC, so the
    # decline happens at that exact line and nowhere earlier.
    pg.evaluate(NO_AAC)
    with pg.expect_download(timeout=20000) as dl:
        pg.evaluate("() => exportVideo()")
    route = webm(open(dl.value.path(), "rb").read())
    asked = pg.evaluate("() => window.__aacAsked")
    check("music on and no AAC: the Video button's own route asks about AAC, declines the MP4, "
          "and the WebM it falls back to carries the music",
          asked and kinds(route) == ["audio", "video"] and dl.value.suggested_filename.endswith(".webm"),
          f"AAC asked {asked}, tracks {route['tracks']}, file {dl.value.suggested_filename}")
    pg.evaluate(REAL_MP4)
    pg.wait_for_timeout(600)

    print("\nFLIP -- an empty or broken recording is not a success")
    hdr = webm(HEADER_ONLY)
    check("(the fixture) the header-only WebM walks as one video track and no frame",
          hdr["tracks"] == {1: 1} and not hdr["blocks"], str(hdr))
    pg.evaluate("(b) => { window.__headerOnly = b; }", list(HEADER_ONLY))
    for mode, why in (("empty", "records nothing"), ("error", "raises an error"), ("garbage", "returns bytes that are not a video"),
                      ("headeronly", "returns a WebM header with no frame behind it")):
        pg.evaluate(FAKE, mode)
        got = no_download(pg, "() => exportWebM()")
        msg = pg.evaluate("() => document.getElementById('flipChip').textContent")
        pg.evaluate(REAL)
        check(f"Flip: a recorder that {why} downloads nothing and says the video came out empty",
              not got and msg.startswith("The video came out empty") and not pg.evaluate("() => exporting"),
              f"{len(got)} download(s), chip '{msg}'")
    # THE STOP IS WAITED FOR, NOT TRUSTED (lib/videorecord.js, after v326).
    pg.evaluate(FAKE, "stall")
    t0 = time.monotonic()
    pg.evaluate("() => exportWebM()")
    try:
        pg.wait_for_function("() => !exporting", timeout=25000)
        waited = round(time.monotonic() - t0, 1)
    except Exception:
        waited = None
        pg.evaluate("() => { exporting = false; exportHide(); }")
    msg = pg.evaluate("() => document.getElementById('flipChip').textContent")
    check("Flip: a recorder that never answers its stop is given up on at the limit (15 s), and says so",
          waited is not None and 14 <= waited <= 20 and msg.startswith("The video came out empty"),
          f"gave up after {waited} s, chip '{msg}'")
    pg.evaluate("() => exportWebM()")
    pg.wait_for_timeout(1800)                    # every frame in, the stop asked for
    t0 = time.monotonic()
    pg.click("#flipExportCancel")
    try:
        pg.wait_for_function("() => !exporting", timeout=5000)
        took = round(time.monotonic() - t0, 2)
    except Exception:
        took = None
        pg.evaluate("() => { exporting = false; exportHide(); }")
    msg = pg.evaluate("() => document.getElementById('flipChip').textContent")
    pg.evaluate(REAL)
    check("Flip: Cancel works while that stop is waited for", took is not None and took < 1.5 and msg == "Export cancelled",
          f"closed after {took} s, chip '{msg}'")
    check("Flip: no page errors", not errs, "; ".join(errs[:2]))
    ctx.close()

    print("\nTHE PAD -- the same finish")
    ctx = b.new_context(viewport={"width": 1100, "height": 800}, accept_downloads=True)
    pg = ctx.new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    browsing.goto(pg, BASE, "/")
    box = pg.locator("#canvas").bounding_box()
    pg.mouse.move(box["x"] + 80, box["y"] + 120)
    pg.mouse.down()
    for i in range(30):
        pg.mouse.move(box["x"] + 80 + i * 8, box["y"] + 120 + math.sin(i / 4) * 30)
        pg.wait_for_timeout(16)
    pg.mouse.up()
    pg.wait_for_timeout(300)
    pg.evaluate("() => { if (recording) endRecordingTake(); }")
    pg.wait_for_timeout(300)

    def pad_export_trigger():
        return """() => { document.getElementById('exportItem').click();
            setTimeout(() => document.getElementById('exportVideo').click(), 300); }"""

    with pg.expect_download(timeout=30000) as dl:
        pg.evaluate(pad_export_trigger())
    good = webm(open(dl.value.path(), "rb").read())
    check("the Pad's video still exports, with its frames, and no music track when it has no music",
          kinds(good) == ["video"] and video_frames(good) > 3, f"{good['tracks']} {good['blocks']}")
    pg.wait_for_timeout(1200)
    pg.evaluate(GECKO)
    try:
        with pg.expect_download(timeout=15000) as dl:
            pg.evaluate(pad_export_trigger())
        gk = webm(open(dl.value.path(), "rb").read())
        gk_said, gk_ok = f"{gk['tracks']} {gk['blocks']}", kinds(gk) == ["video"] and video_frames(gk) > 3
    except Exception as e:
        gk_said, gk_ok = f"no video in 15 s ({type(e).__name__})", False
        pg.evaluate("""() => { ['exportVideo', 'exportPng'].forEach((id) => { document.getElementById(id).disabled = false; });
            document.getElementById('exportProgress').hidden = true; }""")
    asked = pg.evaluate("() => window.__asked")
    pg.evaluate(REAL)
    check("the Pad, with Gecko's recorder and no music: it asks for a type with no audio codec, and its frames come out",
          gk_ok and bool(asked) and not any("opus" in t for t in asked), f"{gk_said}; asked {asked}")
    pg.evaluate("() => { const o = document.getElementById('exportOverlay'); if (o && !o.hidden) document.getElementById('exportCancel').click(); }")
    pg.wait_for_timeout(1200)
    # The same route as Flip's: a song on, the MP4 told there is no AAC.
    pg.set_input_files("#musicInput", {"name": "t.wav", "mimeType": "audio/wav", "buffer": AUD})
    pg.wait_for_function("() => document.getElementById('musicUploadBtn').classList.contains('loaded')", timeout=15000)
    pg.evaluate("() => { const o = document.getElementById('exportOverlay'); if (o && !o.hidden) document.getElementById('exportCancel').click(); }")
    pg.wait_for_timeout(400)
    pg.evaluate(NO_AAC)
    with pg.expect_download(timeout=30000) as dl:
        pg.evaluate(pad_export_trigger())
    padm = webm(open(dl.value.path(), "rb").read())
    check("the Pad, music on and no AAC: the WebM carries the music (the same exporter as Flip's)",
          pg.evaluate("() => window.__aacAsked") and kinds(padm) == ["audio", "video"], f"{padm['tracks']} {padm['blocks']}")
    pg.evaluate(REAL_MP4)
    pg.wait_for_timeout(1200)
    pg.evaluate("(b) => { window.__headerOnly = b; }", list(HEADER_ONLY))
    for mode, why in (("empty", "records nothing"), ("garbage", "returns bytes that are not a video"),
                      ("headeronly", "returns a WebM header with no frame behind it")):
        pg.evaluate(FAKE, mode)
        got = no_download(pg, pad_export_trigger(), wait=6000)
        msg = pg.evaluate("() => document.getElementById('toast').textContent")
        btn = pg.evaluate("() => document.getElementById('exportVideo').disabled")
        pg.evaluate(REAL)
        check(f"the Pad: a recorder that {why} downloads nothing, says so, and gives the button back",
              not got and msg.startswith("The video came out empty") and not btn,
              f"{len(got)} download(s), toast '{msg}', button disabled {btn}")
        pg.evaluate("() => { const o = document.getElementById('exportOverlay'); if (o && !o.hidden) document.getElementById('exportCancel').click(); }")
        pg.wait_for_timeout(600)
    pad_back = """() => { ['exportVideo', 'exportPng'].forEach((id) => { document.getElementById(id).disabled = false; });
        document.getElementById('exportProgress').hidden = true; }"""
    pg.evaluate(FAKE, "stall")
    pg.evaluate("() => { document.getElementById('toast').textContent = ''; }")
    t0 = time.monotonic()
    pg.evaluate(pad_export_trigger())
    try:
        pg.wait_for_function("() => document.getElementById('toast').textContent.startsWith('The video came out empty')"
                             " && !document.getElementById('exportVideo').disabled", timeout=25000)
        waited = round(time.monotonic() - t0, 1)
    except Exception:
        waited = None
        pg.evaluate(pad_back)
    check("the Pad: a recorder that never answers its stop is given up on at the limit (15 s), says so, "
          "and gives the button back", waited is not None and 14 <= waited <= 20, f"gave up after {waited} s")
    pg.evaluate(pad_export_trigger())
    pg.wait_for_timeout(2500)                    # every frame in, the stop asked for
    t0 = time.monotonic()
    pg.click("#exportCancel")
    try:
        pg.wait_for_function("() => document.getElementById('exportProgress').hidden"
                             " && !document.getElementById('exportVideo').disabled", timeout=5000)
        took = round(time.monotonic() - t0, 2)
    except Exception:
        took = None
        pg.evaluate(pad_back)
    pg.evaluate(REAL)
    check("the Pad: Cancel works while that stop is waited for, and gives the button back",
          took is not None and took < 1.5, f"closed after {took} s")
    check("the Pad: no page errors", not errs, "; ".join(errs[:2]))
    ctx.close()
    b.close()

print("\n" + "=" * 62)
passed = sum(1 for r in results if r[0])
print(f"{passed}/{len(results)} passed" + ("" if passed == len(results) else
      "  FAILURES: " + ", ".join(r[1] for r in results if not r[0])))
sys.exit(0 if passed == len(results) else 1)
