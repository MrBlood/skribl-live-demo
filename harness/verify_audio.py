import math, struct, wave, json
from playwright.sync_api import sync_playwright
from assertions import make_check
import browsing
import os

BASE = os.environ.get("SKRIBL_BASE", "http://127.0.0.1:5001")
WAV = "/tmp/seam.wav"

# 6s tone with a deliberately MISMATCHED start/end level, so a naive butt-splice
# would click audibly. If the crossfade works, the seam is smooth anyway.
with wave.open(WAV, "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(44100)
    buf = bytearray()
    for i in range(6 * 44100):
        env = 0.25 + 0.75 * (i / (6 * 44100))          # ramps up across the file
        v = int(20000 * env * math.sin(2 * math.pi * 220 * i / 44100))
        buf += struct.pack("<hh", v, v)
    w.writeframes(bytes(buf))

# Installed before any page script: taps every AudioBufferSourceNode into an
# analyser so we can measure real signal, not just assert a node exists.
TAP = """
window.__tapMax = 0;
window.__srcs = 0;
(function () {
  const Orig = window.AudioContext || window.webkitAudioContext;
  function Tapped() {
    const ctx = new Orig();
    window.__ctx = ctx;
    const an = ctx.createAnalyser(); an.fftSize = 2048; an.connect(ctx.destination);
    window.__an = an;
    const orig = ctx.createBufferSource.bind(ctx);
    ctx.createBufferSource = function () {
      const n = orig();
      window.__srcs++;
      const oc = n.connect.bind(n);
      n.connect = function (d) { try { oc(an); } catch (e) {} return oc(d); };
      return n;
    };
    return ctx;
  }
  Tapped.prototype = Orig.prototype;
  window.AudioContext = Tapped; window.webkitAudioContext = Tapped;
})();
"""

def scribble(pg, box, seed, n=160):
    cx, cy = box["x"]+box["width"]/2, box["y"]+box["height"]/2
    pg.mouse.move(cx, cy); pg.mouse.down()
    for i in range(n):
        a=(i/n)*math.pi*6+seed; r=20+(i/n)*150
        pg.mouse.move(cx+math.cos(a)*r, cy+math.sin(a)*r*0.7)
    pg.mouse.up()

results = []
check = make_check(results)

with sync_playwright() as p:
    b = p.chromium.launch(args=["--autoplay-policy=no-user-gesture-required",
                                "--use-fake-device-for-media-stream"])
    ctx = b.new_context(viewport={"width":1280,"height":900})
    ctx.add_init_script(TAP)
    pg = ctx.new_page()
    errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))

    # ---------- build + post a 4-page flip with a trimmed, crossfaded loop ----------
    print("\nSTEP 3 — post a multi-page Flip with a track")
    pg.goto(BASE+"/flip", wait_until="load"); pg.wait_for_timeout(700)
    pg.evaluate("() => localStorage.clear()")
    box = pg.locator("#pad").bounding_box()
    scribble(pg, box, 0.0)
    for k in range(1,4):
        pg.evaluate("addFrame(false)"); pg.wait_for_timeout(70); scribble(pg, box, k*1.3)
    pg.set_input_files("#musicInput", WAV); pg.wait_for_timeout(4000)
    # a real trimmed loop with a crossfade — exercises buildLoopChannels
    pg.evaluate("() => { trimStart=1.0; trimEnd=4.0; loopCrossfadeMs=120; updateTrimUI(); scheduleSave(); }")
    pg.wait_for_timeout(1200)
    print(f"  loop {pg.evaluate('() => (trimEnd-trimStart).toFixed(2)')}s, crossfade "
          f"{pg.evaluate('() => loopCrossfadeMs')}ms")

    pg.evaluate("shareSkribl()"); pg.wait_for_timeout(9000)
    url = pg.evaluate("() => { const u = (SkriblPosted.list()[0] || {}).url || ''; return u ? new URL(u, location.href).href : ''; }")
    check("posted and got a share url", bool(url), url or "none")

    # ---------- the unverified path: does it flip WITH SOUND at /s/<id> ----------
    print("\n  at the player")
    pl = ctx.new_page(); plerrs = []
    pl.on("pageerror", lambda e: plerrs.append(str(e)))
    pl.goto(url, wait_until="load"); pl.wait_for_timeout(2500)

    import urllib.request
    api = json.load(urllib.request.urlopen(BASE + "/api/skribls/" + url.rsplit("/",1)[1], timeout=15))
    sk = api["skribl"]; f0 = sk["frames"][0]
    meta = {"mode": sk.get("playbackMode"), "frames": len(sk["frames"]),
            "music": bool(f0.get("music")), "hasAudio": api.get("hasAudio")}
    check("posted payload is a multi-frame flip with music",
          meta["frames"] > 1 and meta["mode"] == "flip" and meta["music"], json.dumps(meta))

    # THE VISITOR'S PLAY, #playerPlayBtn, and the link page's own loop bed. This
    # clicked #playBtn until the music preview carve: Pad's Play, which the
    # link page keeps inside a header it never shows (display: none), so no
    # visitor can press it. It ran Pad's replay here, with Pad's music loop,
    # which is editor_music.js's now and never loaded on this page: it
    # measured a path nobody can take, and not the one they do.
    if pl.get_attribute("#playerPlayBtn", "aria-label") != "Pause":
        pl.click("#playerPlayBtn")
    pl.wait_for_timeout(1500)
    wa = pl.evaluate("""() => ({ sources: window.__srcs || 0,
                                state: typeof audioCtx!=='undefined' && audioCtx ? audioCtx.state : null })""")
    # sample the analyser while it plays
    peak = 0.0; hashes = []
    for _ in range(14):
        pl.wait_for_timeout(350)
        peak = max(peak, pl.evaluate("""() => { if(!window.__an) return 0;
            const a=new Float32Array(window.__an.fftSize); window.__an.getFloatTimeDomainData(a);
            let m=0; for(const v of a) m=Math.max(m,Math.abs(v)); return m; }"""))
        hashes.append(pl.evaluate("""() => { const c=document.querySelector('canvas');
            return c ? c.toDataURL().slice(-28) : null; }"""))

    check("frames animate", len(set(hashes)) > 1, f"{len(set(hashes))}/14 distinct canvas states")
    check("AUDIO IS PLAYING (non-silent signal at the graph output)", peak > 0.01,
          f"peak amplitude {peak:.4f}")
    check("gapless path in use (Web Audio, not <audio> fallback)",
          wa["sources"] > 0 and wa["state"] == "running", json.dumps(wa))
    check("no player page errors", not plerrs, "; ".join(plerrs[:2]))

    # ---------- numeric seam check: render 3 loop iterations offline ----------
    print("\n  crossfade seam (numeric, not by ear)")
    seam = pl.evaluate("""async () => {
        const buf = buildLoopAudioBuffer();
        if (!buf) return { error: 'no loop buffer' };
        const sr = buf.sampleRate, n = buf.length;
        const off = new OfflineAudioContext(buf.numberOfChannels, n*3, sr);
        const s = off.createBufferSource(); s.buffer = buf; s.loop = true;
        s.connect(off.destination); s.start(0);
        const out = await off.startRendering();
        const d = out.getChannelData(0);
        const maxDelta = (from, to) => { let m = 0;
            for (let i = from; i < to; i++) m = Math.max(m, Math.abs(d[i+1] - d[i])); return m; };
        const W = 64;
        const seamDelta = maxDelta(n - W, n + W);              // across the loop point
        const ctrlDelta = maxDelta(Math.floor(n/2) - W, Math.floor(n/2) + W);  // mid-loop control
        // a gap would show as a run of consecutive zeros at the seam
        let zeroRun = 0, worst = 0;
        for (let i = n - W; i < n + W; i++) { if (d[i] === 0) { zeroRun++; worst = Math.max(worst, zeroRun); } else zeroRun = 0; }
        return { loopSeconds: +(n/sr).toFixed(3), seamDelta: +seamDelta.toFixed(5),
                 ctrlDelta: +ctrlDelta.toFixed(5), longestZeroRun: worst,
                 ratio: +(seamDelta/(ctrlDelta||1e-9)).toFixed(2) };
    }""")
    print(f"     {json.dumps(seam)}")
    if "error" not in seam:
        check("no silence gap at the loop point", seam["longestZeroRun"] <= 1,
              f"longest zero run {seam['longestZeroRun']} samples")
        check("no click at the seam (delta comparable to mid-loop)", seam["ratio"] < 3.0,
              f"seam {seam['seamDelta']} vs control {seam['ctrlDelta']} (ratio {seam['ratio']}x)")

    check("no editor page errors", not errs, "; ".join(errs[:2]))
    b.close()

# ============================================================================
# THE CLOSE-UP IS THE RESTART VIEW, AND A 0.01s MOVE SHOWS IN IT
#
# The loop detail's magnifier was there so that a small move could be seen:
# at its old 8x ceiling a 0.01s step was 0.94px for a 20s loop on a 330px
# waveform, a move offered that nobody could see, so it went to 32x. Step 2
# took the loop detail out, and the Restart view (lib/musicrestart.js) does
# its close-up job: the end's last 0.6s beside the start's first 0.6s, the
# same scale however long the loop is. So the measure is the same and the
# instrument is new: a beat painted on the end's side, read from what was
# painted, moves by more than a pixel and a half when the end is typed
# 0.01s later, on a 430px phone. Cut on silence off and a clean cut, so the
# end moves only by what was typed.
# ============================================================================
print("\nTHE RESTART VIEW \u2014 a 0.01s move shows in it, at phone width")
with sync_playwright() as _zp:
    _zb = _zp.chromium.launch()
    try:
        zp = _zb.new_page(viewport={"width": 430, "height": 1200})
        browsing.goto(zp, BASE, "/flip")
        zp.set_input_files("#musicInput", WAV)
        zp.wait_for_timeout(4500)
        zp.evaluate("() => _flipDrawerCtl.open('music')")
        zp.wait_for_timeout(700)
        _t = zp.query_selector("#fineTuneToggle")
        if _t:
            _t.click(); zp.wait_for_timeout(800)
        zp.evaluate(
            "() => { const c = document.getElementById('musicCut');"
            " if (c && c.getAttribute('aria-checked') === 'true') c.click();"
            " musicTempo = { bpm: 120, phase: 0 }; trimStart = 0; trimEnd = 4.25;"
            " loopCrossfadeMs = 0; setCrossfadeUI(); updateTrimUI(); }")
        zp.evaluate("() => document.getElementById('musicRestart').scrollIntoView({ block: 'center' })")
        zp.wait_for_timeout(500)
        # The beat at 4s, on the end's side of the line, as painted.
        BEAT = ("() => { const r = document.getElementById('musicRestart'), p = r && r._painted;"
                " const b = p && p.beats.find((b) => b[0] === 'end' && Math.abs(b[2] - 4) < 1e-6);"
                " return { half: r ? r.clientWidth / 2 : 0, x: b ? b[1] : null,"
                "          end: p ? +p.end[1].toFixed(3) : null }; }")
        before = zp.evaluate(BEAT)
        check("the Restart view paints the end's beat", before["x"] is not None,
              f"{before} \u2014 nothing painted on the end's side to read")
        zp.fill("#endReadout", "4.260"); zp.press("#endReadout", "Enter")
        zp.wait_for_timeout(500)
        after = zp.evaluate(BEAT)
        moved = (before["x"] - after["x"]) if before["x"] is not None and after["x"] is not None else 0
        check("a 0.01s move of the end is more than a pixel and a half there",
              after["end"] == 4.26 and moved > 1.5,
              f"the end went {before['end']} to {after['end']} and its beat moved {moved:.2f}px "
              f"(half {before['half']}px) \u2014 the finest typed move has to show where the "
              "join is lined up")
        zp.close()
    finally:
        _zb.close()

bad = [r for r in results if not r[0]]
print(f"\n{'='*62}\n{len(results)-len(bad)}/{len(results)} passed" +
      ("" if not bad else "  FAILURES: " + ", ".join(r[1] for r in bad)))

# These suites printed their failures and then exited 0. run_harness.sh takes
# ok/FAIL from the EXIT CODE, so a failing run was reported as "ok — 32/33
# passed" and the aggregate counted it as PASS with a failed assertion inside.
# Eight suites shared this hole, verify_amber among them — which is very likely
# what the "flake" earlier in this session actually was.



import sys
sys.exit(1 if bad else 0)
