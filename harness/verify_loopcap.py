"""v102 — the two audio-payload bugs from the v101 QA writeup.

(a) Flip ignored its own 20s loop cap on load: decodeForWaveform set
    trimEnd = audioDuration, so a 42s file loaded as a 42s "loop".
(b) Flip posted the ENTIRE uncut file; the Pad crops to the loop first via
    buildTrimmedLoopWav().

The pre-existing suites only checked that a loop string was present, so neither
bug would have failed them. These assertions pin the numbers instead.
"""
import base64, json, math, struct, wave
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:5001"
LONG = "/tmp/long42.wav"

# 42s stereo — the exact case from the writeup. Long enough that an uncropped
# post is many MB and an 8s loop is obviously smaller.
with wave.open(LONG, "wb") as _w:
    _w.setnchannels(2); _w.setsampwidth(2); _w.setframerate(44100)
    _buf = bytearray()
    for _i in range(42 * 44100):
        _v = int(12000 * math.sin(2 * math.pi * 220 * _i / 44100))
        _buf += struct.pack("<hh", _v, _v)
    _w.writeframes(bytes(_buf))

RAW_WAV_BYTES = len(open(LONG, "rb").read())

results = []
def check(name, ok, detail=""):
    results.append((ok, name))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  — {detail}" if detail else ""))

def scribble(pg, box, seed, n=120):
    cx, cy = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
    pg.mouse.move(cx, cy); pg.mouse.down()
    for i in range(n):
        a = (i / n) * math.pi * 6 + seed; r = 20 + (i / n) * 140
        pg.mouse.move(cx + math.cos(a) * r, cy + math.sin(a) * r * 0.7)
    pg.mouse.up()

with sync_playwright() as p:
    br = p.chromium.launch(args=["--autoplay-policy=no-user-gesture-required"])
    ctx = br.new_context(viewport={"width": 1280, "height": 900})
    pg = ctx.new_page()
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))

    # ---------------------------------------------------------------- (a) cap
    print("\n(a) FLIP — loop defaults to the first 20s, not the whole track")
    pg.goto(BASE + "/flip", wait_until="load"); pg.wait_for_timeout(700)
    pg.evaluate("() => localStorage.clear()")
    pg.reload(wait_until="load"); pg.wait_for_timeout(700)

    pg.set_input_files("#musicInput", LONG); pg.wait_for_timeout(6000)

    st = pg.evaluate("() => ({ dur: audioDuration, s: trimStart, e: trimEnd })")
    check("42s file decoded", 41.5 < st["dur"] < 42.5, f"audioDuration {st['dur']:.2f}s")
    check("loop is capped at 20s on load (was 42s)",
          abs((st["e"] - st["s"]) - 20) < 0.01,
          f"trim {st['s']:.2f}–{st['e']:.2f} = {st['e'] - st['s']:.2f}s")
    check("loop starts at the head of the track", abs(st["s"]) < 0.01, f"trimStart {st['s']:.2f}")

    # The drag handlers' invariant must now hold at load too, not just on touch.
    check("matches the invariant every drag handler enforces",
          pg.evaluate("() => (trimEnd - trimStart) <= MAX_LOOP_SECONDS + 1e-9"))

    # An over-cap value forced in from anywhere (stale draft, re-add meta) gets
    # clamped by the central choke point in updateTrimUI.
    over = pg.evaluate("""() => { trimStart = 0; trimEnd = 40; updateTrimUI();
                                  return { s: trimStart, e: trimEnd }; }""")
    check("an over-cap loop is clamped, wherever it came from",
          abs((over["e"] - over["s"]) - 20) < 0.01,
          f"forced 0–40 -> {over['s']:.2f}–{over['e']:.2f}")

    # --------------------------------------------------------- (b) post size
    print("\n(b) FLIP — posts the cropped loop, not the whole file")
    pg.evaluate("() => { trimStart = 2; trimEnd = 10; updateTrimUI(); }")  # 8s loop
    box = pg.locator("#pad").bounding_box()
    scribble(pg, box, 0.0)
    for k in range(1, 3):
        pg.evaluate("addFrame(false)"); pg.wait_for_timeout(60); scribble(pg, box, k * 1.1)
    pg.wait_for_timeout(200)

    payload = pg.evaluate("() => buildSharePayload()")
    music = payload["frames"][0]["music"]
    check("music still rides on frame 0", music is not None)

    b64 = music["data"].split(",", 1)[1]
    posted_bytes = len(base64.b64decode(b64))
    check("posted audio is the 8s loop, not the 42s file",
          posted_bytes < RAW_WAV_BYTES * 0.30,
          f"{posted_bytes/1e6:.2f} MB posted vs {RAW_WAV_BYTES/1e6:.2f} MB raw")

    # A POSTED loop is MONO at the SOURCE rate — buildPostedLoopWav, not
    # buildTrimmedLoopWav. 8s mono 16-bit @44.1k = 8 * 44100 * 2 + 44 header.
    # The old expectation here was 8 * 44100 * 4 (stereo) and it is kept below
    # as the thing that must NOT come back: dropping the downmix reproduces it
    # exactly, which is the only way this stays pinned.
    #
    # NOT 22.05 kHz. Resampling halves this again and puts an audible click on
    # every loop repeat — decodeAudioData resamples to the AudioContext rate and
    # zero-pads the edges, so the clip's end stops joining its start.
    # verify_audio.py's seam assertion is what catches it (1.32x -> 12.36x); the
    # reasoning is in the header of lib/postedaudio.js.
    expect = 8 * 44100 * 2
    was_stereo = 8 * 44100 * 4
    check("posted clip is exactly the loop length, mono at the source rate",
          abs(posted_bytes - expect) < 44100 * 2 * 0.05,
          f"{posted_bytes} bytes vs {expect} expected (~8.0s mono @44.1k)")
    check("...and is NOT the stereo bake the export path still uses",
          posted_bytes < was_stereo * 0.6,
          f"{posted_bytes} bytes vs {was_stereo} in stereo — dropping the downmix lands back on the larger number")

    # Read the format out of the WAV header itself rather than trusting the byte
    # count: a stereo clip at half the rate has the SAME size as a mono clip at
    # full rate, so size alone cannot tell the intended bake from a wrong one.
    hdr = base64.b64decode(b64)[:44]
    ch, rate = struct.unpack("<H", hdr[22:24])[0], struct.unpack("<I", hdr[24:28])[0]
    check("the posted WAV header says mono", ch == 1, f"numChannels = {ch}")
    check("the posted WAV header keeps the source rate", rate == 44100, f"sampleRate = {rate}")

    check("trim rebased to 0..loopLen (the clip IS the loop)",
          abs(music["trimStart"]) < 1e-6 and abs(music["trimEnd"] - 8) < 0.05,
          f"trimStart {music['trimStart']} trimEnd {music['trimEnd']:.2f}")
    check("data URL is a WAV", music["data"].startswith("data:audio/wav;base64,"))

    # The EXPORT bake is deliberately NOT downmixed. If these ever converge, the
    # comment in editor_export.js is wrong and a user's downloaded video quietly
    # lost half its channels.
    exp_url = pg.evaluate("() => { const b = buildTrimmedLoopWav(); return b && b.dataUrl; }")
    exp_hdr = base64.b64decode(exp_url.split(",", 1)[1])[:44]
    exp_ch = struct.unpack("<H", exp_hdr[22:24])[0]
    exp_rate = struct.unpack("<I", exp_hdr[24:28])[0]
    check("the EXPORT bake keeps the channel count the post gives up",
          exp_ch == 2 and exp_rate == 44100,
          f"export {exp_ch}ch @{exp_rate} vs posted {ch}ch @{rate}")

    # ------------------------------------------------ (b) crossfade is baked
    print("\n(b) crossfade is folded in once, not sent for re-application")
    pg.evaluate("() => { loopCrossfadeMs = 120; }")
    m2 = pg.evaluate("() => buildSharePayload().frames[0].music")
    check("crossfadeMs dropped from the posted music (fold is baked in)",
          "crossfadeMs" not in m2 or m2["crossfadeMs"] in (0, None),
          f"crossfadeMs = {m2.get('crossfadeMs')!r}")
    check("clip shortened by exactly the crossfade (8.00s - 120ms)",
          abs(m2["trimEnd"] - 7.88) < 0.02, f"{m2['trimEnd']:.3f}s")

    # ---------------------------------------------- draft keeps the full file
    print("\nregression — the DRAFT still keeps the full sample")
    ser = pg.evaluate("() => serializeFlip()")
    draft_bytes = len(base64.b64decode(ser["music"].split(",", 1)[1]))
    check("draft still holds all 42s so the loop can be re-trimmed",
          draft_bytes >= RAW_WAV_BYTES * 0.9,
          f"{draft_bytes/1e6:.2f} MB in the draft")

    # ------------------------------------------------------ Pad unchanged
    print("\nregression — the Pad is unaffected by the shared-lib move")
    pad = ctx.new_page()
    pad_errors = []
    pad.on("pageerror", lambda e: pad_errors.append(str(e)))
    pad.goto(BASE + "/", wait_until="load"); pad.wait_for_timeout(700)
    pad.evaluate("() => localStorage.clear()")
    pad.reload(wait_until="load"); pad.wait_for_timeout(700)
    pad.set_input_files("#musicInput", LONG); pad.wait_for_timeout(6000)
    pst = pad.evaluate("() => ({ dur: audioDuration, s: trimStart, e: trimEnd })")
    check("Pad still defaults to a 20s loop",
          abs((pst["e"] - pst["s"]) - 20) < 0.01,
          f"trim {pst['s']:.2f}–{pst['e']:.2f}")
    check("Pad's buildTrimmedLoopWav still works through the lib",
          pad.evaluate("""() => { const r = buildTrimmedLoopWav();
                                  return !!r && r.dataUrl.startsWith('data:audio/wav') && r.duration > 19; }"""))
    check("both WAV encoders resolve through the lib on the Pad",
          pad.evaluate("""() => typeof window.SkriblAudioLoop.encodeWavFromChannels === 'function'
                             && typeof window.SkriblAudioLoop.audioBufferToWavDataURL === 'function'"""))

    check("no Flip page errors", not errors, "; ".join(errors[:2]))
    check("no Pad page errors", not pad_errors, "; ".join(pad_errors[:2]))

    br.close()

ok = sum(1 for o, _ in results if o)
print("\n" + "=" * 60)
print(f"{ok}/{len(results)} passed")
for o, n in results:
    if not o:
        print(f"  FAILED: {n}")
raise SystemExit(0 if ok == len(results) else 1)
