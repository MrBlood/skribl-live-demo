import math, struct, wave, json
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:5001"
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
def check(name, ok, detail=""):
    results.append((ok, name)); print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  — {detail}" if detail else ""))

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
    url = pg.evaluate("() => { const i=document.getElementById('flipShareUrl'); return i && i.value; }")
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

    pl.evaluate("() => { const b=document.getElementById('playBtn'); if(b) b.click(); }")
    pl.wait_for_timeout(1500)
    wa = pl.evaluate("""() => ({ src: typeof _waLoopSource!=='undefined' && !!_waLoopSource,
                                dur: typeof _waLoopDuration!=='undefined' ? _waLoopDuration : null,
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
          wa["src"] and wa["state"] == "running", json.dumps(wa))
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
# THE LOOP-DETAIL MAGNIFICATION IS A STEPPER, AND IT REACHES 32x
#
# It was four cells -- 1x 2x 4x 8x -- costing 179px, which forced the focus row
# and the zoom row onto separate lines. The stepper is 94px and both fit on one
# line from 390px up.
#
# THE CEILING WAS THE REAL DEFECT. The finest nudge step is 0.01s and the old
# 8x could not resolve it: on a 330px waveform one step is 0.94px for a 20s loop
# and 0.39px for a 60s one. The tool offered a nudge you could not see. A
# four-cell control could not afford two more levels; a stepper extends for
# free, which is the stronger argument for it.
#
# The buttons carry magnifier glyphs rather than plain signs. A leading
# magnifier beside plain ones was measured at 118px and put the bar back onto
# two lines at 390 -- identifying the control would have cost the space the
# change was made to save.
# ============================================================================
print("\nZOOM STEPPER — one line, and enough magnification to see a 0.01s step")
with sync_playwright() as _zp:
    _zb = _zp.chromium.launch()
    try:
        zp = _zb.new_page(viewport={"width": 430, "height": 1200})
        zp.goto(BASE + "/flip", wait_until="load")
        zp.wait_for_timeout(1200)
        zp.set_input_files("#musicInput", WAV)
        zp.wait_for_timeout(4500)
        zp.evaluate("() => _flipDrawerCtl.open('music')")
        zp.wait_for_timeout(700)
        _t = zp.query_selector("#fineTuneToggle")
        if _t:
            _t.click(); zp.wait_for_timeout(800)

        bar = zp.evaluate(
            "() => { const b = document.querySelector('.zoom-mag-bar');"
            " if (!b) return null;"
            " return { h: Math.round(b.getBoundingClientRect().height),"
            "          kids: [...b.children].map(e =>"
            "                 Math.round(e.getBoundingClientRect().width)) }; }")
        check("the loop-detail bar exists", bar is not None, "nothing to measure")
        if bar:
            check("focus and zoom share one line at phone width",
                  bar["h"] < 50,
                  f"bar is {bar['h']}px tall with children {bar['kids']} — four "
                  "zoom cells cost 179px and pushed it to two rows")
            check("...and the stepper is the compact one",
                  len(bar["kids"]) == 2 and bar["kids"][1] <= 110,
                  f"{bar['kids']} — a leading magnifier measured 118px and wraps")

        # THE LADDER. Each press must halve the window and move the readout, and
        # the ends must stop rather than wrap.
        seen = []
        for _ in range(8):
            st = zp.evaluate(
                "() => ({ mag: zoomMag,"
                " label: document.getElementById('zoomMagVal').textContent,"
                " win: +getZoomWindow().duration.toFixed(4),"
                " outDis: document.getElementById('zoomMagOut').disabled,"
                " inDis: document.getElementById('zoomMagIn').disabled })")
            seen.append(st)
            if st["inDis"]:
                break
            zp.click("#zoomMagIn"); zp.wait_for_timeout(200)
        mags = [s["mag"] for s in seen]
        check("the ladder climbs 1 to 32 by doubling",
              mags == [1, 2, 4, 8, 16, 32], str(mags))
        check("every step actually narrows the window",
              all(seen[i + 1]["win"] < seen[i]["win"] for i in range(len(seen) - 1)),
              str([s["win"] for s in seen]) + " — a readout that changes while "
              "the view does not is worse than no control")
        check("the readout tracks the level",
              all(s["label"].startswith(str(s["mag"])) for s in seen),
              str([(s["mag"], s["label"]) for s in seen]))
        check("zoom-out is disabled at the bottom and only there",
              seen[0]["outDis"] is True
              and all(not s["outDis"] for s in seen[1:]),
              str([(s["mag"], s["outDis"]) for s in seen]))
        check("zoom-in is disabled at the top and only there",
              seen[-1]["inDis"] is True
              and all(not s["inDis"] for s in seen[:-1]),
              str([(s["mag"], s["inDis"]) for s in seen]))

        # THE POINT OF 32x: a 0.01s nudge has to be visible on the waveform.
        px = zp.evaluate(
            "() => { const w = document.getElementById('zoomTrackWrap');"
            " const width = w.getBoundingClientRect().width;"
            " return (0.01 / (getZoomWindow().duration / width)); }")
        check("at full magnification a 0.01s step is more than a pixel wide",
              px > 1.5,
              f"{px:.2f}px — the finest nudge is 0.01s, and at the old 8x "
              "ceiling that was under a pixel on any loop over ~4s")
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
