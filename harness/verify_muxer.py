import _layout
"""v103 — Flip loads the VENDORED mp4-muxer, and the MP4 capability gate degrades
cleanly when the codec isn't available.

Flip used to pull mp4-muxer from jsdelivr via `await import(...)` while the Pad
loaded a vendored copy of the SAME library from static/skribl/ — so the two
surfaces ran different versions (5.1.5 vs 5.2.2) and Flip's MP4 path was dead
anywhere the CDN was blocked. Flip now loads the same vendored file.

Note on scope: headless Chromium here exposes VideoEncoder but does NOT support
avc1 (`isConfigSupported` -> false), so the actual H.264 encode cannot run. That
makes this a test of the GATE and the fallback, not of the encoder. The gate
returning false is the same path Firefox takes, which the handoff has listed as
unverified — so it is worth pinning even though the encode isn't reachable.
"""
import os, sys
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:5001"

# This suite needs the vendored muxer, which lives in the REPO and is not shipped
# in the handoff zip (the zip carries only changed files). Fail with something
# readable rather than a wall of "Mp4Muxer is undefined".
_MUXER = _layout.vendored("mp4-muxer.min.js")
if _MUXER is None:
    sys.exit("SKIP: static/skribl/mp4-muxer.min.js not present.\n"
             "      It is vendored in the repo but excluded from handoff zips.\n"
             "      Copy it in from the repo to run this suite.")

results = []
def check(name, ok, detail=""):
    results.append((ok, name))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  — {detail}" if detail else ""))

API = """() => ({
    hasGlobal: typeof window.Mp4Muxer !== 'undefined',
    hasMuxer: !!(window.Mp4Muxer && window.Mp4Muxer.Muxer),
    hasTarget: !!(window.Mp4Muxer && window.Mp4Muxer.ArrayBufferTarget)
})"""

with sync_playwright() as p:
    br = p.chromium.launch()
    ctx = br.new_context(viewport={"width": 1280, "height": 900})

    print("\nVENDORED MUXER — loads with the CDN unreachable")
    flip_errors, pad_errors = [], []
    flip = ctx.new_page(); flip.on("pageerror", lambda e: flip_errors.append(str(e)))
    flip.goto(BASE + "/flip", wait_until="load"); flip.wait_for_timeout(1500)

    f = flip.evaluate(API)
    check("Flip exposes window.Mp4Muxer", f["hasGlobal"])
    check("Flip has Muxer", f["hasMuxer"])
    check("Flip has ArrayBufferTarget", f["hasTarget"])
    check("no Flip page errors from the vendored script", not flip_errors,
          "; ".join(flip_errors[:2]))

    pad = ctx.new_page(); pad.on("pageerror", lambda e: pad_errors.append(str(e)))
    pad.goto(BASE + "/", wait_until="load"); pad.wait_for_timeout(1500)
    d = pad.evaluate(API)
    check("Pad exposes the same global", d["hasGlobal"] and d["hasMuxer"] and d["hasTarget"])
    check("both surfaces agree on the API shape", f == d, f"flip {f} vs pad {d}")

    # The whole point of vendoring: no jsdelivr request for the muxer. gifenc is
    # still CDN-only, so filter to the muxer specifically.
    reqs = []
    flip2 = ctx.new_page()
    flip2.on("request", lambda r: reqs.append(r.url))
    flip2.goto(BASE + "/flip", wait_until="load"); flip2.wait_for_timeout(1500)
    cdn_muxer = [u for u in reqs if "mp4-muxer" in u and "jsdelivr" in u]
    local_muxer = [u for u in reqs if "mp4-muxer" in u and "127.0.0.1" in u]
    check("no CDN request for mp4-muxer", not cdn_muxer, str(cdn_muxer[:1]))
    check("the muxer is served from our own origin", bool(local_muxer),
          local_muxer[0] if local_muxer else "none")

    print("\nCAPABILITY GATE — declines cleanly when avc1 is unsupported")
    h264 = flip.evaluate("""async () => {
        try { const r = await VideoEncoder.isConfigSupported(
                {codec:'avc1.42001f', width:640, height:460, bitrate:2000000});
              return !!r.supported; } catch (e) { return false; } }""")
    check("this browser genuinely lacks avc1 (so the gate is under test)", not h264,
          f"isConfigSupported -> {h264}")

    picked = flip.evaluate("async () => await pickAvcCodec(640, 460)")
    check("pickAvcCodec returns falsy, not a bogus codec", not picked, repr(picked))

    gated = flip.evaluate("async () => await exportViaWebCodecsMp4()")
    check("Flip's MP4 path returns false rather than throwing", gated is False, repr(gated))
    check("no page errors from the declined export", not flip_errors,
          "; ".join(flip_errors[:2]))

    # The Pad's export lives in an IIFE, so webcodecsMp4Ready/expectedVideoFormat
    # aren't reachable from here the way Flip's standalone equivalents are. That
    # asymmetry is the "IIFE vs standalone" divergence INTEGRATION §3 calls out as
    # blocking the export de-dupe — assert it explicitly so the next attempt it
    # is structural, then test the Pad through its UI instead.
    check("Pad's export internals are IIFE-scoped (not globals, unlike Flip's)",
          pad.evaluate("() => typeof webcodecsMp4Ready === 'undefined'"))

    # Draw something so the video button isn't disabled, then read the label the
    # Pad writes from expectedVideoFormat().
    box = pad.locator("#canvas").bounding_box()
    pad.mouse.move(box["x"] + 80, box["y"] + 80); pad.mouse.down()
    for i in range(30):
        pad.mouse.move(box["x"] + 80 + i * 5, box["y"] + 100)
    pad.mouse.up()
    pad.wait_for_timeout(300)
    pad.evaluate("() => document.getElementById('exportOverlay').hidden = false")
    pad.evaluate("() => { const b = document.getElementById('exportBtn'); if (b) b.click(); }")
    pad.wait_for_timeout(1200)
    label = pad.evaluate("""() => {
        const t = document.querySelector('#exportVideo .export-opt-title');
        return t ? t.textContent.trim() : null; }""")
    check("Pad's export label promises WebM, not MP4 it can't deliver",
          label is not None and "MP4" not in label,
          f"label = {label!r}")

    print("\nFALLBACK — MediaRecorder is what actually carries the export here")
    mr = pad.evaluate("""() => {
        if (typeof MediaRecorder === 'undefined') return null;
        return ['video/mp4;codecs=avc1', 'video/webm;codecs=vp9', 'video/webm']
            .filter(t => MediaRecorder.isTypeSupported(t)); }""")
    check("MediaRecorder has at least one usable type", bool(mr), str(mr))

    # v104: gifenc is vendored too, so this flipped from "undefined, and that is
    # handled" to "present". The encoder itself is exercised in verify_gifenc.py;
    # all this needs to pin is that the second vendored library didn't disturb the
    # first, and that no jsdelivr script origin survives on the page.
    print("\nGIFENC — vendored as of v104 (encoder covered by verify_gifenc.py)")
    check("window.gifenc is present, not CDN-dependent",
          flip.evaluate("() => typeof (window.gifenc||{}).GIFEncoder") == "function")
    check("Flip still loaded and ran with both libraries", flip.evaluate("() => Array.isArray(frames)"))
    check("no jsdelivr request of any kind remains",
          not [u for u in reqs if "jsdelivr" in u], str([u for u in reqs if "jsdelivr" in u][:1]))

    br.close()

ok = sum(1 for o, _ in results if o)
print("\n" + "=" * 60)
print(f"{ok}/{len(results)} passed")
for o, n in results:
    if not o:
        print(f"  FAILED: {n}")
raise SystemExit(0 if ok == len(results) else 1)
