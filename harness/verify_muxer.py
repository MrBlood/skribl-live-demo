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
(Since Chrome 153, Playwright 1.63, Oct 30, headless Chromium does encode avc1;
the rows below drive encode() with stand-in encoders either way.)
"""
import os, sys
from playwright.sync_api import sync_playwright
from assertions import make_check

BASE = os.environ.get("SKRIBL_BASE", "http://127.0.0.1:5001")

# This suite needs the vendored muxer, which lives in the REPO and is not shipped
# in the handoff zip (the zip carries only changed files). Fail with something
# readable rather than a wall of "Mp4Muxer is undefined".
_MUXER = _layout.vendored("mp4-muxer.min.js")
if _MUXER is None:
    sys.exit("SKIP: static/skribl/mp4-muxer.min.js not present.\n"
             "      It is vendored in the repo but excluded from handoff zips.\n"
             "      Copy it in from the repo to run this suite.")

results = []
check = make_check(results)

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
    # mp4-muxer is no longer a <script> tag on either editor: 9,504 B encoded
    # that only matters when somebody exports an MP4, so it is fetched on the
    # click via skriblLoadVendor(). These ask for it first — the guarantees
    # (our own origin, same API on both surfaces) are unchanged.
    def load_muxer(page):
        page.evaluate("() => window.skriblLoadVendor('mp4muxer')")
        page.wait_for_timeout(200)

    flip.goto(BASE + "/flip", wait_until="load"); flip.wait_for_timeout(1500)
    load_muxer(flip)

    f = flip.evaluate(API)
    check("Flip exposes window.Mp4Muxer", f["hasGlobal"])
    check("Flip has Muxer", f["hasMuxer"])
    check("Flip has ArrayBufferTarget", f["hasTarget"])
    check("no Flip page errors from the vendored script", not flip_errors,
          "; ".join(flip_errors[:2]))

    pad = ctx.new_page(); pad.on("pageerror", lambda e: pad_errors.append(str(e)))
    pad.goto(BASE + "/", wait_until="load"); pad.wait_for_timeout(1500)
    load_muxer(pad)
    d = pad.evaluate(API)
    check("Pad exposes the same global", d["hasGlobal"] and d["hasMuxer"] and d["hasTarget"])
    check("both surfaces agree on the API shape", f == d, f"flip {f} vs pad {d}")

    # The whole point of vendoring: no jsdelivr request for the muxer. gifenc is
    # still CDN-only, so filter to the muxer specifically.
    reqs = []
    flip2 = ctx.new_page()
    flip2.on("request", lambda r: reqs.append(r.url))
    flip2.goto(BASE + "/flip", wait_until="load"); flip2.wait_for_timeout(1500)
    load_muxer(flip2)
    cdn_muxer = [u for u in reqs if "mp4-muxer" in u and "jsdelivr" in u]
    local_muxer = [u for u in reqs if "mp4-muxer" in u and "127.0.0.1" in u]
    check("no CDN request for mp4-muxer", not cdn_muxer, str(cdn_muxer[:1]))
    check("the muxer is served from our own origin", bool(local_muxer),
          local_muxer[0] if local_muxer else "none")

    print("\nCAPABILITY GATE — the MP4 path matches what the browser can do")
    # This block used to ASSERT that the browser lacked avc1 ("this browser
    # genuinely lacks avc1, so the gate is under test"). That held on the
    # sandbox Chromium and on the owner's machine, and it is how the suite was
    # written -- but it is an assertion about the ENVIRONMENT, not about this
    # code, and it is false on a browser that ships H.264. The first CI run
    # that ever executed the harness failed exactly here, 15/18, because
    # GitHub's Chromium does support avc1. A test that only passes on browsers
    # missing a codec is not testing the gate; it is testing the runner.
    #
    # So the capability is now MEASURED and both sides are asserted. Whichever
    # branch runs, the claim is the same one that always mattered: the code's
    # answer agrees with the browser's. Each branch contributes two assertions
    # so the total does not move with the runner.
    h264 = flip.evaluate("""async () => {
        try { const r = await VideoEncoder.isConfigSupported(
                {codec:'avc1.42001f', width:640, height:460, bitrate:2000000});
              return !!r.supported; } catch (e) { return false; } }""")
    print(f"  (this browser {'HAS' if h264 else 'lacks'} avc1)")

    picked = flip.evaluate("async () => await pickAvcCodec(640, 460)")
    # The invariant the old environment assertion was reaching for, stated so
    # that it holds on any runner: the code's answer tracks the browser's
    # capability. Offering MP4 where it cannot be encoded, or declining where
    # it can, are both failures — and this catches either without caring which
    # browser is running. It also keeps the suite at 18 assertions on every
    # runner, so the count stays comparable across environments.
    check("pickAvcCodec's answer agrees with the browser's real capability",
          bool(picked) == h264, f"isConfigSupported -> {h264}, pickAvcCodec -> {picked!r}")
    if h264:
        check("pickAvcCodec returns a real avc1 codec where H.264 exists",
              isinstance(picked, str) and picked.startswith("avc1"), repr(picked))
        # Not merely truthy: a codec string the browser itself will accept.
        # Handing the encoder a plausible-looking profile it cannot use is the
        # failure this pair exists to catch, in both directions.
        ok = flip.evaluate("""async (c) => {
            try { const r = await VideoEncoder.isConfigSupported(
                    {codec:c, width:640, height:460, bitrate:2000000});
                  return !!r.supported; } catch (e) { return false; } }""", picked)
        check("...and the browser accepts the exact profile it picked", ok,
              f"pickAvcCodec chose {picked!r}, which isConfigSupported rejects")
    else:
        check("pickAvcCodec returns falsy, not a bogus codec", not picked, repr(picked))
        gated = flip.evaluate("async () => await exportViaWebCodecsMp4()")
        check("Flip's MP4 path returns false rather than throwing", gated is False, repr(gated))
    check("no page errors from the capability probe", not flip_errors,
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

    # Gifenc is vendored too, so this flipped from "undefined, and that is
    # handled" to "present". The encoder itself is exercised in verify_gifenc.py;
    # all this needs to pin is that the second vendored library didn't disturb the
    # first, and that no jsdelivr script origin survives on the page.
    print("\nGIFENC — vendored as of v104 (encoder covered by verify_gifenc.py)")
    # Both codecs are lazy now, so ask for the second one too. The point of this
    # assertion is unchanged: loading one vendored library must not disturb the
    # other, and neither may come from a CDN.
    flip.evaluate("() => window.skriblLoadVendor('gifenc')")
    flip.wait_for_timeout(200)
    check("window.gifenc is present once asked for, not CDN-dependent",
          flip.evaluate("() => typeof (window.gifenc||{}).GIFEncoder") == "function")
    check("Flip still loaded and ran with both libraries", flip.evaluate("() => Array.isArray(frames)"))
    check("no jsdelivr request of any kind remains",
          not [u for u in reqs if "jsdelivr" in u], str([u for u in reqs if "jsdelivr" in u][:1]))

    # THE AAC CONFIG, NOT A DESCRIPTOR AROUND IT (after v325, the owner's
    # iPhone exports). The music on an iPhone MP4 was all there, but the file's
    # esds held a whole MPEG-4 ES_Descriptor where the two-byte
    # AudioSpecificConfig belongs: Safari's AudioEncoder hands back the
    # descriptor as decoderConfig.description, and the muxer wrapped it again.
    # Apple's player coped; ffmpeg read the wrapper's first byte as the config
    # ("audio object type 0") and so does every player built on it. SAFARI is
    # that description, read out of the owner's file. The export's own encode()
    # is driven with stand-in encoders (no H.264 is needed for the container),
    # so this pins the wiring, not only the helper.
    print("\nMP4 AUDIO — the file carries the AAC config itself, as Safari or Chrome describes it")
    SAFARI = "038080802200000004808080144014001800000000000000000005808080021190068080800102"
    ENCODE = """async (desc) => {
      await window.skriblLoadVendor('mp4muxer');
      const hex = (h) => Uint8Array.from(h.match(/../g).map(x => parseInt(x, 16)));
      const RealVE = window.VideoEncoder, RealAE = window.AudioEncoder;
      class FakeVE { constructor(o) { this.o = o; this.encodeQueueSize = 0; } configure(c) { this.c = c; }
        encode(f, opt) { const first = !this.sent; this.sent = true;
          this.o.output(new EncodedVideoChunk({ type: first || (opt && opt.keyFrame) ? 'key' : 'delta', timestamp: f.timestamp,
                                                duration: 33333, data: new Uint8Array(16) }),
            first ? { decoderConfig: { codec: this.c.codec, codedWidth: this.c.width, codedHeight: this.c.height,
                                       description: new Uint8Array([1, 0x42, 0, 0x1f, 0xff, 0xe0, 0]) } } : undefined); }
        async flush() {} close() {} }
      class FakeAE { constructor(o) { this.o = o; } configure(c) { this.c = c; }
        encode(a) { const first = !this.sent; this.sent = true;
          this.o.output(new EncodedAudioChunk({ type: 'key', timestamp: a.timestamp, duration: 21333, data: new Uint8Array(24) }),
            first ? { decoderConfig: { codec: 'mp4a.40.2', sampleRate: this.c.sampleRate,
                                       numberOfChannels: this.c.numberOfChannels, description: hex(desc) } } : undefined); }
        async flush() {} close() {} }
      window.VideoEncoder = FakeVE; window.AudioEncoder = FakeAE;
      try {
        const c = document.createElement('canvas'); c.width = 64; c.height = 64;
        const buf = new OfflineAudioContext(2, 48000, 48000).createBuffer(2, 4800, 48000);
        const out = await window.SkriblMp4.encode({ ready: { MM: window.Mp4Muxer, avcCodec: 'avc1.42001f', w: 64, h: 64 },
          canvas: c, durationSec: 0.2, audio: buf, drawFrame: async () => {}, aborted: () => false, progress: () => {} });
        return Array.from(new Uint8Array(out));
      } catch (e) { return String(e); }
      finally { window.VideoEncoder = RealVE; window.AudioEncoder = RealAE; } }"""

    def dsi(mp4):
        """The esds's DecoderSpecificInfo: what a player reads as the AudioSpecificConfig."""
        if not isinstance(mp4, list):
            return mp4
        b = bytes(mp4)
        i = b.find(b"esds")
        if i < 0:
            return None
        def desc(j):
            tag, j, n = b[j], j + 1, 0
            while True:
                c = b[j]; j += 1; n = (n << 7) | (c & 0x7F)
                if not c & 0x80:
                    return tag, j, j + n
        tag, s, e = desc(i + 8)                     # ES_Descriptor, after the box's version and flags
        tag, s, e = desc(s + 3)                     # DecoderConfigDescriptor
        tag, s, e = desc(s + 13)                    # DecoderSpecificInfo
        return b[s:e].hex() if tag == 5 else None

    got = dsi(flip.evaluate(ENCODE, SAFARI))
    check("Safari's description: the file's AAC config is the two bytes 11 90 (AAC-LC, 48 kHz, stereo), not the descriptor around them",
          got == "1190", f"DecoderSpecificInfo {got!r}")
    got = dsi(flip.evaluate(ENCODE, "1190"))
    check("Chrome's description (already the config) is written exactly as it came",
          got == "1190", f"DecoderSpecificInfo {got!r}")

    # NO B-FRAMES (Firefox 155, Oct 30). Firefox's encoder, given the High
    # profile the export asked for first, sent frames out of the order they
    # show in; the vendored muxer threw ("Timestamps must be monotonically
    # increasing") inside the encoder's own callback, where nothing caught it,
    # and the export finished a file of 29 frames out of 83. Two things now:
    # the first profile asked for is Baseline, which has no B-frames; and an
    # encoder that sends them anyway stops the export as an error, which both
    # editors answer with a WebM. The stand-in encoder answers on a later tick,
    # as a real one does: one that answered inside encode() would throw
    # straight into the loop and could not tell the old code from the new.
    print("\nMP4 VIDEO — no frame out of order reaches the muxer")
    PICK = """async (yes) => { const real = VideoEncoder.isConfigSupported;
      VideoEncoder.isConfigSupported = async (c) => ({ supported: yes === 'all' || yes.includes(c.codec) });
      try { return await window.SkriblMp4.pickAvcCodec(816, 612); } finally { VideoEncoder.isConfigSupported = real; } }"""
    got = flip.evaluate(PICK, "all")
    check("the first H.264 profile asked for is Baseline, which has no B-frames",
          isinstance(got, str) and got.startswith("avc1.42"), repr(got))
    got = flip.evaluate(PICK, ["avc1.640028"])
    check("...and a browser with only High still gets High (and the guard below)", got == "avc1.640028", repr(got))
    REORDER = """async (swap) => {
      await window.skriblLoadVendor('mp4muxer');
      const RealVE = window.VideoEncoder; const errs = []; const onErr = (e) => errs.push(String(e.message || e));
      window.addEventListener('error', onErr);
      class LateVE { constructor(o) { this.o = o; this.encodeQueueSize = 0; this.held = []; this.n = 0; } configure(c) { this.c = c; }
        send(ts, i) { const o = this.o, c = this.c;
          setTimeout(() => o.output(new EncodedVideoChunk({ type: i === 0 ? 'key' : 'delta', timestamp: ts, duration: 33333, data: new Uint8Array(16) }),
            i === 0 ? { decoderConfig: { codec: c.codec, codedWidth: c.width, codedHeight: c.height,
                                         description: new Uint8Array([1, 0x42, 0, 0x1f, 0xff, 0xe0, 0]) } } : undefined), 0); }
        encode(f) { const i = this.n++;
          if (!swap || i === 0) { this.send(f.timestamp, i); return; }
          this.held.push([f.timestamp, i]);
          if (this.held.length === 2) { const [a, b] = this.held; this.held = []; this.send(b[0], a[1]); this.send(a[0], b[1]); } }
        async flush() { this.held.forEach(([t, i]) => this.send(t, i)); this.held = []; await new Promise(r => setTimeout(r, 30)); } close() {} }
      window.VideoEncoder = LateVE;
      try {
        const c = document.createElement('canvas'); c.width = 64; c.height = 64;
        const out = await window.SkriblMp4.encode({ ready: { MM: window.Mp4Muxer, avcCodec: 'avc1.42e028', w: 64, h: 64 },
          canvas: c, durationSec: 0.3, audio: null, drawFrame: async () => {}, aborted: () => false, progress: () => {} });
        await new Promise(r => setTimeout(r, 50));
        return { file: out ? out.byteLength : 0, errs };
      } catch (e) { await new Promise(r => setTimeout(r, 50)); return { threw: String(e.message || e), errs }; }
      finally { window.VideoEncoder = RealVE; window.removeEventListener('error', onErr); } }"""
    got = flip.evaluate(REORDER, True)
    check("an encoder that sends frames out of order stops the export as an error (the editors then make a WebM)",
          "threw" in got and "file" not in got, str(got))
    check("...and nothing throws on the page where no one catches it", not got.get("errs"), str(got))
    got = flip.evaluate(REORDER, False)
    check("frames in order, answered on a later tick as a real encoder does, still make the file",
          got.get("file", 0) > 0 and not got.get("errs") and "threw" not in got, str(got))

    br.close()

ok = sum(1 for o, _ in results if o)
print("\n" + "=" * 60)
print(f"{ok}/{len(results)} passed")
for o, n in results:
    if not o:
        print(f"  FAILED: {n}")
raise SystemExit(0 if ok == len(results) else 1)
