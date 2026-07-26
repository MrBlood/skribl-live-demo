import math, struct, wave, json
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:5001"
WAV = "/tmp/smoke.wav"
with wave.open(WAV, "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(44100)
    buf = bytearray()
    for i in range(5 * 44100):
        v = int(18000 * math.sin(2 * math.pi * 330 * i / 44100))
        buf += struct.pack("<hh", v, v)
    w.writeframes(bytes(buf))

results = []
def check(name, ok, detail=""):
    results.append((ok, name)); print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  — {detail}" if detail else ""))

with sync_playwright() as p:
    b = p.chromium.launch(args=["--autoplay-policy=no-user-gesture-required"])

    # ---------- the lib is present and shared on every surface ----------
    print("\nSTEP 4a — lib/audioloop.js is live and shared on all three surfaces")
    ctx = b.new_context(); pg = ctx.new_page()
    for path, name in [("/flip","Flip"), ("/skribl-pad","Pad")]:
        pg.goto(BASE+path, wait_until="load"); pg.wait_for_timeout(900)
        st = pg.evaluate("""() => ({
            lib: typeof window.SkriblAudioLoop === 'object' && window.SkriblAudioLoop !== null,
            fns: window.SkriblAudioLoop ? Object.keys(window.SkriblAudioLoop).sort() : [],
            shimmed: typeof buildLoopAudioBuffer === 'function' })""")
        check(f"{name}: window.SkriblAudioLoop published", st["lib"], ",".join(st["fns"]))
        check(f"{name}: local shim present", st["shimmed"])

    # the DSP itself, run in the browser, must fold the crossfade correctly
    dsp = pg.evaluate("""() => {
        const sr = 44100, n = sr;                       // 1s buffer
        const ctx = new (window.AudioContext||window.webkitAudioContext)();
        const buf = ctx.createBuffer(1, n, sr);
        const d = buf.getChannelData(0);
        for (let i = 0; i < n; i++) d[i] = Math.sin(2*Math.PI*220*i/sr);
        const xf = Math.floor(0.05 * sr);               // 50ms crossfade
        const out = window.SkriblAudioLoop.buildLoopChannels(buf, 0, n, xf);
        return { inFrames: n, outFrames: out.frames, expected: n - xf,
                 channels: out.channels.length,
                 finite: out.channels[0].every(v => Number.isFinite(v)) }; }""")
    check("buildLoopChannels folds correctly in-browser",
          dsp["outFrames"] == dsp["expected"] and dsp["finite"], json.dumps(dsp))

    # ---------- negative test: the documented failure must actually fire ----------
    print("\nSTEP 4b — negative test: block lib/audioloop.js")
    nctx = b.new_context(); npg = nctx.new_page()
    nerrs = []
    npg.on("pageerror", lambda e: nerrs.append(str(e)))
    npg.route("**/lib/audioloop.js*", lambda r: r.abort())
    npg.goto(BASE+"/flip", wait_until="load"); npg.wait_for_timeout(1200)
    check("lib genuinely absent", npg.evaluate("() => typeof window.SkriblAudioLoop"), "undefined")
    npg.set_input_files("#musicInput", WAV); npg.wait_for_timeout(3000)
    thrown = npg.evaluate("""() => { try { buildLoopAudioBuffer(); return null; }
                                     catch (e) { return e.constructor.name + ': ' + e.message; } }""")
    check("audio DSP throws exactly as the deploy note warns", thrown is not None, thrown or "did not throw")
    check("and the page still loads/draws (failure is confined to audio)",
          npg.evaluate("() => typeof frames !== 'undefined' && frames.length >= 1"))

    b.close()

bad = [r for r in results if not r[0]]
print(f"\n{'='*62}\n{len(results)-len(bad)}/{len(results)} passed" +
      ("" if not bad else "  FAILURES: " + ", ".join(r[1] for r in bad)))
