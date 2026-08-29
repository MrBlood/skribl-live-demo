"""v224 — do the media resource limits stop a decompression bomb, and only that?

Outside review, finding #5. Until now the media checks proved TYPE and BYTES:
the declared subtype had to match the leading bytes, and the base64 had to be
under a size cap. Neither says anything about what DECODING the file costs, and
bytes are not a proxy for it — the whole point of a decompression bomb is that
it is small. A 66-byte PNG whose IHDR declares 30000x30000 passed every check and
every browser that opened the post then allocated ~3.6 GB for it.

validation.py now reads the declared dimensions out of the header of all four
accepted image formats, and the duration out of a WAV's `fmt ` chunk, with no
decoder and no new dependency. This suite is the regression test for that, and
it is deliberately built around one rule learned the hard way in this project
(DECISIONS.md v240): a suite that only tests the direction a feature works
passes forever while the feature is broken. So it runs four ways.

  1. REJECT — a real PNG rewritten to declare a bomb must be refused, by the
     live endpoint and not merely by the pure function.
  2. ACCEPT — a 4x4 sweep of real encoder output (Chromium's PNG/JPEG/WebP
     encoders, the vendored gifenc, and Python's `wave`) must parse to the
     dimensions those encoders were ASKED for. A parser that lies about size is
     a 400 on legitimate posts, which is the worse failure of the two.
  3. THE DOCUMENTED GAPS — the section comment promises that an unparseable
     header is ACCEPTED and that compressed-audio duration is bounded only by
     bytes. Promises in comments rot; these are asserted.
  4. MUTATION — every reject assertion is re-run with the cap lifted, and must
     then PASS. An assertion that survives its own feature being disabled was
     never testing the feature.

Why real encoders and not bytes typed here: laying out a WebP VP8 header by hand
tests my reading of the spec against itself. The VP8 fixtures below are genuine
Chromium bitstreams; the only synthetic files are the bombs, which is the one
place synthesis is the point.
"""
import base64
import io
import json
import os
import struct
import sys
import urllib.error
import urllib.request
import wave
import zlib

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import _layout  # noqa: E402  (harness-local)
from skribl import validation as V  # noqa: E402

BASE = os.environ.get("SKRIBL_BASE", "http://127.0.0.1:5001")
SKIP_EXIT = 77

_GIFENC = _layout.vendored("gifenc.min.js")
if _GIFENC is None:
    sys.exit("SKIP: gifenc.min.js is not vendored, so no real GIF can be built.")

results = []


def check(name, ok, detail=""):
    results.append((bool(ok), name))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  — {detail}" if detail else ""))


def durl(mime, raw):
    return f"data:{mime};base64," + base64.b64encode(raw).decode()


def post(payload):
    req = urllib.request.Request(BASE + "/api/skribls",
                                 data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        body = e.read()
        try:
            return e.code, json.loads(body)
        except Exception:
            return e.code, {"raw": body[:200].decode("utf-8", "replace")}


def frame(**kw):
    f = {"strokes": [], "strokeGroups": [], "background": {"color": "#101418"}}
    f.update(kw)
    return f


def png_declaring(w, h):
    """A structurally valid PNG whose IHDR declares w x h — the bomb shape.

    The IDAT holds one byte. That is the attack: the declared size and the
    encoded size have nothing to do with each other, which is exactly why a
    byte cap cannot see this coming.
    """
    def chunk(tag, data):
        c = tag + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xffffffff)
    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(b"\x00"))
            + chunk(b"IEND", b""))


def wav_of(seconds, rate=8000, channels=1, width=1):
    """A real WAV from the stdlib encoder — not a header typed out here."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(channels)
        w.setsampwidth(width)
        w.setframerate(rate)
        w.writeframes(b"\x00" * int(rate * seconds) * channels * width)
    return buf.getvalue()


# ── Real encoder output ──────────────────────────────────────────────────────
SIZES = [(1, 1), (17, 29), (320, 240), (1237, 911)]


def build_real_images():
    """{(w,h): {subtype: bytes}} straight out of Chromium and gifenc.

    Also returns each WebP re-wrapped as a bare VP8 chunk. Chromium always emits
    the VP8X (extended) container, so without this the lossy branch of
    _webp_dimensions — a different set of offsets entirely — is never executed.
    """
    from playwright.sync_api import sync_playwright
    out = {}
    with sync_playwright() as p:
        br = p.chromium.launch()
        try:
            page = br.new_page()
            page.goto("about:blank")
            page.add_script_tag(content=_GIFENC.read_text())
            for w, h in SIZES:
                per = {}
                for mime, tag in (("image/png", "png"), ("image/jpeg", "jpeg"),
                                  ("image/webp", "webp")):
                    u = page.evaluate("""([w, h, mime]) => {
                        const c = document.createElement('canvas');
                        c.width = w; c.height = h;
                        const x = c.getContext('2d');
                        x.fillStyle = '#c33'; x.fillRect(0, 0, w, h);
                        x.fillStyle = '#39c';
                        x.fillRect(0, 0, Math.max(1, w >> 1), Math.max(1, h >> 1));
                        return c.toDataURL(mime);
                    }""", [w, h, mime])
                    per[tag] = base64.b64decode(u.split(",", 1)[1])
                per["gif"] = base64.b64decode(page.evaluate("""([w, h]) => {
                    const {GIFEncoder, quantize, applyPalette} = window.gifenc;
                    const n = w * h, rgba = new Uint8Array(n * 4);
                    for (let i = 0; i < n; i++) {
                      rgba[i*4] = (i*7) & 255; rgba[i*4+1] = (i*3) & 255;
                      rgba[i*4+2] = 200;       rgba[i*4+3] = 255;
                    }
                    const pal = quantize(rgba, 16);
                    const gif = GIFEncoder();
                    gif.writeFrame(applyPalette(rgba, pal), w, h, {palette: pal});
                    gif.finish();
                    let s = ''; for (const c of gif.bytes()) s += String.fromCharCode(c);
                    return btoa(s);
                }""", [w, h]))
                inner = _extract_riff_chunk(per["webp"], b"VP8 ")
                if inner is not None:
                    body = b"WEBP" + inner
                    per["webp_vp8"] = b"RIFF" + len(body).to_bytes(4, "little") + body
                out[(w, h)] = per
        finally:
            br.close()
    return out


def _extract_riff_chunk(raw, want):
    i = 12
    while i + 8 <= len(raw):
        cid = raw[i:i + 4]
        n = int.from_bytes(raw[i + 4:i + 8], "little")
        if cid == want:
            return raw[i:i + 8 + n + (n & 1)]
        i += 8 + n + (n & 1)
    return None


print("\nSETUP — building fixtures with real encoders")
try:
    REAL = build_real_images()
except Exception as exc:                                  # pragma: no cover
    sys.exit(f"SKIP: could not drive a browser to build fixtures ({exc}).")
check("Chromium and gifenc produced every fixture",
      all(len(v) >= 4 for v in REAL.values()),
      f"{sum(len(v) for v in REAL.values())} files across {len(REAL)} sizes")
check("Chromium's WebP could be re-wrapped as a bare VP8 file",
      all("webp_vp8" in v for v in REAL.values()),
      "without this the lossy branch of the WebP parser is never executed")


print("\nACCEPT — the parsers must agree with the encoders that made the files")
# A 4x4 parameter sweep. A single fixture size proves a parser reads *a* number;
# it does not prove the number is the width. 1x1 and 1237x911 sit either side of
# every byte-boundary these formats have.
for (w, h), per in sorted(REAL.items()):
    for tag in ("png", "jpeg", "gif", "webp", "webp_vp8"):
        raw = per.get(tag)
        if raw is None:
            continue
        sub = "webp" if tag.startswith("webp") else tag
        got = V._image_dimensions(sub, raw)
        check(f"{tag} {w}x{h} parses to its authored size", got == (w, h),
              f"parsed {got}")

for secs, rate, ch, width in ((0.5, 44100, 2, 2), (3.0, 8000, 1, 1), (12.25, 22050, 1, 2)):
    got = V._wav_duration_seconds(wav_of(secs, rate, ch, width))
    check(f"a real {secs}s WAV ({rate}Hz x{ch} {width}B) reads as its own length",
          got is not None and abs(got - secs) < 0.02, f"read {got!r}")

print("\n  …and every one of them is still ACCEPTED by the validator")
for (w, h), per in sorted(REAL.items()):
    for tag, mime in (("png", "image/png"), ("jpeg", "image/jpeg"),
                      ("gif", "image/gif"), ("webp", "image/webp")):
        err = V._validate_media_data_url(durl(mime, per[tag]), "image",
                                         V.MAX_IMAGE_BYTES, "photo.data")
        check(f"a real {tag} {w}x{h} is accepted", err is None, str(err))


print("\nREJECT — a declared bomb must be refused")
BOMBS = [
    ("a 900-megapixel PNG in 70 bytes", 30000, 30000),
    ("a strip 9000px wide (over the edge cap, under the pixel cap)", 9000, 10),
    ("a PNG just over the pixel cap", V.MAX_IMAGE_EDGE, V.MAX_IMAGE_PIXELS // V.MAX_IMAGE_EDGE + 4),
]
for label, w, h in BOMBS:
    raw = png_declaring(w, h)
    err = V._validate_media_data_url(durl("image/png", raw), "image",
                                     V.MAX_IMAGE_BYTES, "photo.data")
    check(f"rejected: {label}", err is not None,
          f"{len(raw)} bytes, declares {w}x{h} — {err}")

_edge_ok = png_declaring(V.MAX_IMAGE_EDGE, 8)
check("the cap is a ceiling, not a fence — exactly MAX_IMAGE_EDGE is allowed",
      V._validate_media_data_url(durl("image/png", _edge_ok), "image",
                                 V.MAX_IMAGE_BYTES, "photo.data") is None)

_long = wav_of(V.MAX_AUDIO_SECONDS + 30)
check("rejected: a WAV longer than MAX_AUDIO_SECONDS",
      V._validate_media_data_url(durl("audio/wav", _long), "audio",
                                 V.MAX_AUDIO_BYTES, "music.data") is not None,
      f"{V.MAX_AUDIO_SECONDS + 30}s at {len(_long)} bytes")


print("\nEND TO END — the live endpoint refuses it, not just the pure function")
# The function being right is worthless if nothing calls it on the path a bomb
# actually takes. Each media slot is posted separately because they are walked
# by different code: baseSnapshot in particular was walked by NOTHING until v116.
_bomb = durl("image/png", png_declaring(30000, 30000))
# The request body IS the payload — `title` rides alongside `frames`, it does not
# wrap them. Getting that wrong is how an end-to-end assertion passes while
# validating an empty payload, so the accept case below shares the exact shape.
for label, payload in (
    ("as a frame photo", {"title": "bomb",
                          "frames": [frame(photo={"data": _bomb, "fit": "cover"})]}),
    ("as a baseSnapshot", {"title": "bomb", "frames": [frame(baseSnapshot=_bomb)]}),
    ("as a root baseSnapshot", {"title": "bomb", "strokes": [], "strokeGroups": [],
                                "baseSnapshot": _bomb}),
    ("as a thumbnail", {"title": "bomb", "frames": [frame()], "thumbnail": _bomb}),
):
    status, body = post(payload)
    check(f"POST /api/skribls refuses a bomb {label}", status == 400,
          f"HTTP {status} — {str(body)[:110]}")

_ok = durl("image/png", REAL[(320, 240)]["png"])
status, body = post({"title": "real photo",
                     "frames": [frame(photo={"data": _ok, "fit": "cover"})]})
check("…and still accepts a real 320x240 photo on the same path",
      status in (200, 201), f"HTTP {status} — {str(body)[:110]}")


print("\nTHE DOCUMENTED GAPS — the comment says ACCEPT here, so prove it does")
# validation.py promises an unparseable header is accepted rather than rejected,
# because a file whose header will not parse does not decode either, and a 400
# on every rare corner of these formats costs more than it buys. Existing
# harness fixtures are exactly these stubs, so this is also what keeps the older
# suites green.
STUBS = [
    ("a PNG signature with no IHDR", "png", b"\x89PNG\r\n\x1a\n" + b"\x00" * 64),
    ("a GIF signature with a zeroed screen descriptor", "gif", b"GIF89a" + b"\x00" * 64),
    ("a RIFF/WEBP with no sub-format chunk", "webp", b"RIFF\x00\x00\x00\x00WEBP" + b"\x00" * 64),
    ("a JPEG SOI with no SOF", "jpeg", b"\xff\xd8\xff" + b"\x00" * 64),
]
for label, sub, raw in STUBS:
    check(f"unparseable reads as unparseable, not as zero: {label}",
          V._image_dimensions(sub, raw) is None)
    check(f"…and is therefore accepted: {label}",
          V._validate_media_data_url(durl("image/" + sub, raw), "image",
                                     V.MAX_IMAGE_BYTES, "photo.data") is None)

# The other documented gap, stated so nobody reads the WAV check as a general
# audio-duration check: compressed containers are bounded by BYTES alone.
for sub in ("mpeg", "ogg", "flac", "webm", "mp4"):
    check(f"audio/{sub} duration is honestly reported as unknown",
          V._audio_duration_seconds(sub, b"\x00" * 4096) is None,
          "deriving it needs a decoder; MAX_AUDIO_BYTES is the only cap")


print("\nMUTATION — lift the cap and every reject above must turn into a pass")
# The point of this project's v240 lesson: an assertion that still passes with
# the feature disabled was never testing the feature. Each cap is raised in turn
# and the same fixture re-validated; anything that stays rejected was being
# rejected for some other reason and its assertion above proves nothing.
_saved = (V.MAX_IMAGE_EDGE, V.MAX_IMAGE_PIXELS, V.MAX_AUDIO_SECONDS)
try:
    V.MAX_IMAGE_EDGE = 10 ** 9
    V.MAX_IMAGE_PIXELS = 10 ** 18
    for label, w, h in BOMBS:
        err = V._validate_media_data_url(durl("image/png", png_declaring(w, h)),
                                         "image", V.MAX_IMAGE_BYTES, "photo.data")
        check(f"with the caps lifted, this is accepted again: {label}",
              err is None, f"still rejected by something else — {err}")
    V.MAX_AUDIO_SECONDS = 10 ** 9
    check("with the duration cap lifted, the long WAV is accepted again",
          V._validate_media_data_url(durl("audio/wav", _long), "audio",
                                     V.MAX_AUDIO_BYTES, "music.data") is None)
finally:
    V.MAX_IMAGE_EDGE, V.MAX_IMAGE_PIXELS, V.MAX_AUDIO_SECONDS = _saved
check("the caps were restored after the mutation pass",
      (V.MAX_IMAGE_EDGE, V.MAX_IMAGE_PIXELS, V.MAX_AUDIO_SECONDS) == _saved)


print("\nBOUNDED — the parsers must not become the attack they prevent")
# _jpeg_dimensions walks a segment chain a crafted file controls. It is bounded
# by segment count AND byte offset; without both, a file of 0xFF 0xE0 0x00 0x02
# repeated is a scan the length of the payload on every post.
_pathological = b"\xff\xd8" + (b"\xff\xe0\x00\x02" * 200_000)
import time  # noqa: E402  (only needed for this one assertion)
_t0 = time.time()
_res = V._jpeg_dimensions(_pathological)
_ms = (time.time() - _t0) * 1000
check("a 800 kB chain of empty JPEG segments is walked in bounded time",
      _res is None and _ms < 50, f"{_ms:.2f} ms over {len(_pathological)} bytes")

_wav_pathological = b"RIFF\x00\x00\x00\x00WAVE" + (b"junk\x00\x00\x00\x00" * 100_000)
_t0 = time.time()
_res = V._wav_duration_seconds(_wav_pathological)
_ms = (time.time() - _t0) * 1000
check("a WAV of 100,000 empty chunks is walked in bounded time",
      _res is None and _ms < 50, f"{_ms:.2f} ms")


bad = [r for r in results if not r[0]]
print(f"\n{'=' * 62}\n{len(results) - len(bad)}/{len(results)} passed"
      + ("" if not bad else "  FAILURES: " + ", ".join(r[1] for r in bad)))
sys.exit(1 if bad else 0)
