"""The MP4 export HAPPY path — encode, mux, and check the container.

`verify_muxer.py` already covers the GATE thoroughly: that `pickAvcCodec` returns
falsy on a browser without H.264, that Flip's MP4 path declines rather than
throwing, that the Pad's label promises WebM rather than MP4 it cannot deliver.
What has never been exercised, since v103, is the path where the encoder EXISTS
and an MP4 is actually produced.

That needs a browser with WebCodecs and an H.264 encoder. Playwright's bundled
Chromium does not ship one — `typeof VideoEncoder` is undefined — which is
precisely why this was never verified. So this suite SKIPS rather than pretending,
and CI runs it on a browser that does have it.

Read the skip literally: a skipped run contributes zero assertions and proves
nothing about MP4. It is not a pass.
"""
import json
import os
import sys

SKIP_EXIT = 77

results = []
def check(name, ok, detail=""):
    results.append((ok, name)); print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  — {detail}" if detail else ""))


def skip(reason):
    print(f"SUITE-SKIPPED: {reason}")
    raise SystemExit(SKIP_EXIT)


try:
    from playwright.sync_api import sync_playwright
except ImportError:
    skip("playwright is not installed")

BASE = os.environ.get("SKRIBL_BASE", "http://127.0.0.1:5001")
CHANNEL = os.environ.get("SKRIBL_BROWSER_CHANNEL") or None

with sync_playwright() as p:
    launch = {"channel": CHANNEL} if CHANNEL else {}
    browser = p.chromium.launch(**launch)
    page = browser.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(BASE + "/flip", wait_until="load")
    page.wait_for_timeout(1500)

    caps = page.evaluate("""async () => {
        if (typeof VideoEncoder === 'undefined') return {webcodecs: false};
        const out = {webcodecs: true, codecs: {}};
        for (const c of ['avc1.42001f', 'avc1.4d0028', 'avc1.640028']) {
            try { out.codecs[c] = !!(await VideoEncoder.isConfigSupported(
                {codec: c, width: 320, height: 240, bitrate: 800000, framerate: 30})).supported; }
            catch (e) { out.codecs[c] = false; }
        }
        return out;
    }""")

    if not caps.get("webcodecs"):
        browser.close()
        skip("this browser has no WebCodecs VideoEncoder — set "
             "SKRIBL_BROWSER_CHANNEL=chrome, or run the CI job that does")
    usable = [c for c, ok in caps.get("codecs", {}).items() if ok]
    if not usable:
        browser.close()
        skip(f"WebCodecs present but no H.264 profile is supported: {caps['codecs']}")

    print(f"\nMP4 — encoder available ({', '.join(usable)})")
    check("the page picks a codec rather than declining",
          bool(page.evaluate("() => typeof pickAvcCodec === 'function' && pickAvcCodec()")),
          "pickAvcCodec returned falsy on a browser that DOES support H.264")

    # Encode a handful of synthetic frames through the same vendored muxer the
    # export path uses, and inspect the container it produces. This exercises
    # encoder -> muxer -> bytes, which is the half that has never run.
    result = page.evaluate("""async (codec) => {
        const {Muxer, ArrayBufferTarget} = window.Mp4Muxer;
        const target = new ArrayBufferTarget();
        const W = 320, H = 240, FPS = 10, N = 12;
        const muxer = new Muxer({
            target, fastStart: 'in-memory',
            video: {codec: 'avc', width: W, height: H, frameRate: FPS}
        });
        let encoded = 0, encErr = null;
        const enc = new VideoEncoder({
            output: (chunk, meta) => { muxer.addVideoChunk(chunk, meta); encoded++; },
            error: e => { encErr = String(e); }
        });
        enc.configure({codec, width: W, height: H, bitrate: 800000, framerate: FPS});

        const cv = document.createElement('canvas');
        cv.width = W; cv.height = H;
        const ctx = cv.getContext('2d');
        for (let i = 0; i < N; i++) {
            ctx.fillStyle = i % 2 ? '#101418' : '#e0c060';
            ctx.fillRect(0, 0, W, H);
            ctx.fillStyle = '#ffffff';
            ctx.fillRect((i * 20) % W, 100, 40, 40);
            const frame = new VideoFrame(cv, {timestamp: (i * 1e6) / FPS,
                                              duration: 1e6 / FPS});
            enc.encode(frame, {keyFrame: i === 0});
            frame.close();
        }
        await enc.flush();
        enc.close();
        muxer.finalize();
        const buf = new Uint8Array(target.buffer);

        // Walk the top-level boxes: 4-byte big-endian size, 4-char type.
        const boxes = [];
        let off = 0;
        const dv = new DataView(buf.buffer);
        while (off + 8 <= buf.length && boxes.length < 24) {
            const size = dv.getUint32(off);
            const type = String.fromCharCode(buf[off+4], buf[off+5], buf[off+6], buf[off+7]);
            boxes.push({type, size});
            if (size < 8) break;
            off += size;
        }
        return {bytes: buf.length, encoded, encErr, boxes,
                brand: String.fromCharCode(buf[8], buf[9], buf[10], buf[11])};
    }""", usable[0])

    check("the encoder produced chunks", result["encoded"] > 0,
          f"{result['encoded']} chunks")
    check("no encoder error", not result["encErr"], str(result["encErr"]))
    check("the muxer produced a non-trivial file", result["bytes"] > 1024,
          f"{result['bytes']} bytes")

    types = [b["type"] for b in result["boxes"]]
    check("the file starts with an ftyp box", types[:1] == ["ftyp"], str(types[:3]))
    check("the brand is an ISO-BMFF/MP4 brand",
          result["brand"].startswith(("isom", "mp42", "avc1", "iso")),
          repr(result["brand"]))
    check("it contains a moov box (without it nothing can play the file)",
          "moov" in types, str(types))
    check("it contains an mdat box (the actual samples)", "mdat" in types, str(types))
    check("box sizes tile the file exactly, with no gap or overrun",
          sum(b["size"] for b in result["boxes"]) == result["bytes"],
          f"boxes sum {sum(b['size'] for b in result['boxes'])} vs file {result['bytes']}")
    check("fastStart put moov BEFORE mdat, so the file streams",
          "moov" in types and "mdat" in types
          and types.index("moov") < types.index("mdat"),
          str(types))
    check("no page errors during the export", not errors, "; ".join(errors[:2]))

    browser.close()

bad = [r for r in results if not r[0]]
print(f"\n{'='*62}\n{len(results)-len(bad)}/{len(results)} passed" +
      ("" if not bad else "  FAILURES: " + ", ".join(r[1] for r in bad)))
