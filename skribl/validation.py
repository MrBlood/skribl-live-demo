"""Payload validation: media data URLs, and structural complexity limits.

Moved verbatim from app.py. No database or Flask coupling here at all.
"""
import base64
import math
import re

from .core import MAX_CARD_BYTES, _DATA_URL_IMAGE_RE, _env_int

def _decode_data_url_image(data_url):
    # Returns (raw_bytes, mimetype) for a PNG or JPEG data URL, or None if the
    # value is missing/malformed/an unsupported type (webp, gif, svg, …) so the
    # caller falls back to the static card.
    if not isinstance(data_url, str):
        return None
    m = _DATA_URL_IMAGE_RE.match(data_url.strip())
    if not m:
        return None
    try:
        raw = base64.b64decode(m.group(2), validate=True)
    except Exception:
        return None
    return raw, "image/" + m.group(1)


def _payload_has_audio(payload):
    # Whether a posted Skribl carries actual audio bytes. Frame-aware: audio lives
    # at the top level on a legacy Skribl, or inside a frame on a frame-format one
    # (a classic Skribl is a 1-frame Skribl). A settings-only/empty music dict
    # ({}) doesn't count. Pure + import-light so it can be unit-tested headless.
    if not isinstance(payload, dict):
        return False
    music = payload.get("music")
    if not isinstance(music, dict) or not music.get("data"):
        music = None
        frames = payload.get("frames")
        if isinstance(frames, list):
            for frame in frames:
                if isinstance(frame, dict):
                    m = frame.get("music")
                    if isinstance(m, dict) and m.get("data"):
                        music = m
                        break
    return bool((music or {}).get("data"))


# --- Server-side media validation (INTEGRATION §7) ---------------------------
# The post endpoint is public and unauthenticated, and every media item arrives as
# a base64 data URL inside payload_json. Until now the only limit was
# MAX_CONTENT_LENGTH on the whole request, so a single post could carry ~24 MB of
# arbitrary blob — any type, valid base64 or not — straight into the JSON column.
# At the current rate limit that is ~480 MB/hour/IP into a free-tier Postgres.
#
# These caps are per-item and deliberately generous: a trimmed loop is a couple of
# MB (see the v102 note: a 42s WAV with an 8s loop posts 1.41 MB) and a background
# photo is well under 8 MB. They are env-tunable so a deploy can tighten them
# without a code change.
#
# Type handling is an ALLOW-LIST of top-level types (audio/*, image/*) with SVG
# explicitly excluded — SVG is the one image type that carries script, and nothing
# the client produces is SVG. Subtypes are otherwise left open on purpose: `music`
# is whatever audio file the user picked (mpeg/wav/ogg/mp4/flac/…), and narrowing
# that would reject legitimate uploads for no security gain.
#
# Dimensions and audio duration are covered too, as far as they can be read from
# a header without a decoder — see the resource-limit section below for exactly
# where that stops.
MAX_AUDIO_BYTES = _env_int("SKRIBL_MAX_AUDIO_BYTES", 12_000_000, minimum=1024)
MAX_IMAGE_BYTES = _env_int("SKRIBL_MAX_IMAGE_BYTES", 8_000_000, minimum=1024)

_MEDIA_DATA_URL_RE = re.compile(r"^data:([a-zA-Z]+)/([a-zA-Z0-9.+-]+);base64,(.*)$", re.DOTALL)


# STRICT image allow-list (review round 2, #1). The first pass matched prefixes
# only and left unknown subtypes unchecked, which meant image/avif or image/tiff
# with arbitrary bytes was stored unverified, and a RIFF/WAVE body passed as WebP
# because only the first four bytes were compared. Both are closed: an unlisted
# subtype is now REJECTED, and WebP is checked as a container (RIFF....WEBP), not
# a prefix.
# BMP was dropped in v116 rather than added to the Pad's pickers: the Pad drawers
# only ever offered jpeg/png/gif/webp, so keeping BMP meant two policies wearing
# one comment. Nothing the client produces is BMP. (Review round 6, #6)
ALLOWED_IMAGE_SUBTYPES = {"png", "jpeg", "jpg", "gif", "webp"}


def _valid_image_signature(sub_type, raw):
    """Header/container check ONLY — deliberately not full image validation.

    This proves the declared subtype matches the leading bytes. It does NOT prove
    the file decodes, and a truncated b"\x89PNG\r\n\x1a\n" with no IHDR passes.
    Completeness and decompression cost are still NOT checked; that needs a real
    decoder (Pillow) with resource limits. Declared DIMENSIONS are checked, but
    separately and from the header only — see _image_dimensions. The error
    message says "does not match the declared container" for that reason.
    (Review round 4, #3; dimensions added in v224.)
    """
    if sub_type == "png":
        return raw.startswith(b"\x89PNG\r\n\x1a\n")
    if sub_type in ("jpeg", "jpg"):
        return raw.startswith(b"\xff\xd8\xff")
    if sub_type == "gif":
        return raw.startswith((b"GIF87a", b"GIF89a"))
    if sub_type == "webp":
        # RIFF is a generic container: WAV and AVI share the first four bytes.
        # The format is only established by the WEBP fourcc at offset 8.
        return len(raw) >= 12 and raw.startswith(b"RIFF") and raw[8:12] == b"WEBP"
    return False
# Audio the client can decode. Narrower than 'any audio/*' per review #6, but
# deliberately generous — these are the containers a file picker actually yields.
ALLOWED_AUDIO_SUBTYPES = {
    "wav", "x-wav", "wave", "vnd.wave", "mpeg", "mp3", "mp4", "x-m4a", "m4a",
    "aac", "ogg", "opus", "webm", "flac", "x-flac",
}


def _valid_audio_signature(sub_type, raw):
    """Container check for declared audio. (Review round 4, #2)

    Round 3 allow-listed subtypes but never looked at the bytes, so
    b"this is not a WAV" passed as audio/wav. Like the image checks, this proves
    the CONTAINER, not that a complete file decodes — see the note on
    _valid_image_signature.

    Two of these are container-FAMILY checks, not proof of audio, and should be
    described that way (review round 5, #4):
      - webm: the EBML magic identifies Matroska/WebM generally. A video-only
        WebM or a Matroska file declared audio/webm will pass.
      - mp4/x-m4a/m4a/aac: the `ftyp` box identifies ISO Base Media Format. A
        video MP4 or an HEIF/HEIC container declared audio/mp4 will pass.
    Distinguishing tracks and codecs needs a real media parser, which is out of
    scope here. What these DO close is the arbitrary-bytes case.
    """
    if sub_type in ("wav", "x-wav", "wave", "vnd.wave"):
        return len(raw) >= 12 and raw.startswith(b"RIFF") and raw[8:12] == b"WAVE"
    if sub_type in ("flac", "x-flac"):
        return raw.startswith(b"fLaC")
    if sub_type in ("ogg", "opus"):
        return raw.startswith(b"OggS")
    if sub_type == "webm":
        return raw.startswith(b"\x1a\x45\xdf\xa3")          # EBML
    if sub_type in ("mpeg", "mp3"):
        # ID3 tag, or an MPEG audio frame sync (11 set bits).
        return raw.startswith(b"ID3") or (len(raw) >= 2 and raw[0] == 0xFF and (raw[1] & 0xE0) == 0xE0)
    if sub_type in ("mp4", "x-m4a", "m4a"):
        return len(raw) >= 12 and raw[4:8] == b"ftyp"
    if sub_type == "aac":
        # ADTS sync, or an MP4/ftyp container mislabelled as aac by a picker.
        return (len(raw) >= 2 and raw[0] == 0xFF and (raw[1] & 0xF0) == 0xF0) or \
               (len(raw) >= 12 and raw[4:8] == b"ftyp")
    return False


# --- Media resource limits (outside review, #5) ------------------------------
# The container checks above prove the declared type matches the leading bytes.
# They say nothing about what DECODING the file costs. A 40 kB PNG can declare
# 30000x30000 in its IHDR — the classic decompression bomb — and every browser
# that opens the post then allocates ~3.6 GB for it. Bytes are not a proxy for
# that: the whole point of a bomb is that it is small.
#
# Dimensions sit in the header of all four accepted image formats, so they can be
# read WITHOUT a decoder and without a new dependency. The parsers below are
# fixed-offset (png/gif/webp) or bounded-scan (jpeg), read-only, and never
# allocate beyond the slice they were handed — a crafted file cannot turn the
# scan into the denial of service the scan exists to prevent.
#
# Where this stops, stated as plainly as the signature checks state theirs:
#   - A parser that cannot locate the header returns None and the item is
#     ACCEPTED. These caps reject DECLARED bombs, not malformed files. A file
#     whose header will not parse does not decode either, and rejecting on
#     "unparseable" would turn every rarer corner of these formats into a 400.
#   - The declared size is not proof of the encoded size. A truncated PNG still
#     declares its full dimensions; that is exactly the case this rejects.
#   - Audio duration is parseable for WAV ONLY, whose header states the byte rate
#     outright. For compressed audio (mp3/aac/ogg/opus/flac/webm) duration is
#     bounded ONLY by MAX_AUDIO_BYTES, because deriving it needs a real decoder.
#     A 12 MB Opus file can be an hour long and is accepted by design.
MAX_IMAGE_EDGE = _env_int("SKRIBL_MAX_IMAGE_EDGE", 8192, minimum=16)
MAX_IMAGE_PIXELS = _env_int("SKRIBL_MAX_IMAGE_PIXELS", 40_000_000, minimum=1024)
MAX_AUDIO_SECONDS = _env_int("SKRIBL_MAX_AUDIO_SECONDS", 900, minimum=1)


def _png_dimensions(raw):
    # IHDR is mandatory and must be the FIRST chunk, so the offsets are fixed.
    if len(raw) < 24 or raw[12:16] != b"IHDR":
        return None
    return (int.from_bytes(raw[16:20], "big"), int.from_bytes(raw[20:24], "big"))


def _gif_dimensions(raw):
    # Logical screen descriptor, little-endian, immediately after the signature.
    if len(raw) < 10:
        return None
    return (int.from_bytes(raw[6:8], "little"), int.from_bytes(raw[8:10], "little"))


def _webp_dimensions(raw):
    # Three sub-formats share the RIFF/WEBP container and each states its size
    # differently. VP8X (extended: animation, alpha) is checked first because its
    # CANVAS size is what a decoder allocates, whatever the frames inside do.
    if len(raw) < 21:
        return None
    fourcc = raw[12:16]
    if fourcc == b"VP8X":
        if len(raw) < 30:
            return None
        return (int.from_bytes(raw[24:27], "little") + 1,
                int.from_bytes(raw[27:30], "little") + 1)
    if fourcc == b"VP8 ":
        # Lossy: 3-byte frame tag, the 0x9d012a start code, then 14-bit w/h.
        if len(raw) < 30 or raw[23:26] != b"\x9d\x01\x2a":
            return None
        return (int.from_bytes(raw[26:28], "little") & 0x3FFF,
                int.from_bytes(raw[28:30], "little") & 0x3FFF)
    if fourcc == b"VP8L":
        if len(raw) < 25 or raw[20] != 0x2F:
            return None
        bits = int.from_bytes(raw[21:25], "little")
        return ((bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1)
    return None


# Sentinel: the scan gave up at a resource cap before reaching an SOF, so the
# dimensions are UNKNOWN AND THE FILE IS SUSPICIOUS. This is not the same as
# None. None means "there is no readable SOF here" — a truncated or structurally
# broken file, which a browser cannot decode into a bomb either, so it is
# accepted (see the section note). _UNSCANNABLE means "an SOF may well sit just
# past where we stopped looking", which is exactly the shape of the outside
# review's bypass: 64 empty APP0 segments followed by an SOF0 declaring
# 65535x65535. The browser has no 64-segment limit and decodes the bomb; our
# bounded scan quit one segment early and, returning None, ACCEPTED it. A scan
# that stops at its own safety cap must fail CLOSED, or the cap is the bypass.
_UNSCANNABLE = object()

# A JPEG states its size in an SOF segment, which sits after an arbitrary number
# of metadata segments (EXIF, ICC, comments). The walk is bounded twice — by
# segment count and by byte offset — so the scan cost stays flat regardless of
# what the file claims. A real photo reaches its SOF in a handful of segments
# and a few KB; the caps are set far above that, so hitting one is itself the
# signal that the file is not a real photo.
_JPEG_MAX_SEGMENTS = 128
_JPEG_MAX_SCAN = 1 << 20            # 1 MB of headers before an SOF is already absurd
# 0xC0-0xCF are SOF markers EXCEPT C4 (Huffman tables), C8 (reserved) and CC
# (arithmetic coding conditioning), which are not frame headers.
_JPEG_SOF_MARKERS = frozenset(
    list(range(0xC0, 0xC4)) + list(range(0xC5, 0xC8))
    + list(range(0xC9, 0xCC)) + list(range(0xCD, 0xD0))
)


def _jpeg_dimensions(raw):
    # The cap check is INSIDE the loop and returns the sentinel, so the reason
    # the walk ended is preserved: ran out of data (truncated -> None -> accept)
    # is distinguished from hit a safety cap (-> _UNSCANNABLE -> reject). The
    # old `while ... and segments < CAP` folded both into a single fall-through
    # None, which is the bypass.
    i, segments, n = 2, 0, len(raw)
    while i + 9 <= n:
        if segments >= _JPEG_MAX_SEGMENTS or i >= _JPEG_MAX_SCAN:
            return _UNSCANNABLE                  # gave up before an SOF — refuse
        if raw[i] != 0xFF:
            return None                          # not where a marker should be
        marker = raw[i + 1]
        if marker == 0xFF:                       # fill byte; markers may be padded
            i += 1
            continue
        if marker == 0x01 or 0xD0 <= marker <= 0xD8:
            i += 2                               # standalone: carries no length
            continue
        if marker in (0xD9, 0xDA):
            return None                          # entropy data begins; no SOF seen
        length = int.from_bytes(raw[i + 2:i + 4], "big")
        if length < 2:
            return None
        if marker in _JPEG_SOF_MARKERS:
            # SOF payload: length(2) precision(1) height(2) width(2).
            return (int.from_bytes(raw[i + 7:i + 9], "big"),
                    int.from_bytes(raw[i + 5:i + 7], "big"))
        i += 2 + length
        segments += 1
    return None                                  # ran out of data, no SOF — accept


def _image_dimensions(sub_type, raw):
    """(width, height) read from the header, or None when it cannot be read.

    None means ACCEPT — see the section note. Callers must not treat it as zero.

    A non-positive result reads as UNPARSEABLE, not as a rejection. A 0x0 image
    is degenerate, not a bomb: the client draws nothing and moves on, while a
    header full of zeros is exactly what a stub fixture or a truncated file
    looks like. Rejecting it would spend a 400 on the one case that costs
    nothing to render.
    """
    if sub_type == "png":
        dims = _png_dimensions(raw)
    elif sub_type == "gif":
        dims = _gif_dimensions(raw)
    elif sub_type == "webp":
        dims = _webp_dimensions(raw)
    elif sub_type in ("jpeg", "jpg"):
        dims = _jpeg_dimensions(raw)
    else:
        return None
    if dims is _UNSCANNABLE:
        return _UNSCANNABLE                      # propagate: caller must refuse
    if dims is None or dims[0] < 1 or dims[1] < 1:
        return None
    return dims


_WAV_MAX_CHUNKS = 32


def _wav_duration_seconds(raw):
    """Seconds from the WAV header, or None when it cannot be read cheaply.

    `fmt ` states the byte rate outright, so duration is data-chunk size over
    byte rate with nothing decoded. The chunk walk is bounded like the JPEG one.
    """
    n, i, chunks = len(raw), 12, 0
    byte_rate = data_bytes = None
    while i + 8 <= n and chunks < _WAV_MAX_CHUNKS:
        cid = raw[i:i + 4]
        size = int.from_bytes(raw[i + 4:i + 8], "little")
        body = i + 8
        if cid == b"fmt " and size >= 16 and body + 16 <= n:
            byte_rate = int.from_bytes(raw[body + 8:body + 12], "little")
        elif cid == b"data":
            # A streamed WAV declares 0, and a crafted one can declare a size
            # past the end. What actually ARRIVED is the honest number for both.
            data_bytes = min(size, n - body) if size else (n - body)
            break
        i = body + size + (size & 1)             # RIFF chunks are word-aligned
        chunks += 1
    if not byte_rate or data_bytes is None:
        return None
    return data_bytes / float(byte_rate)


def _audio_duration_seconds(sub_type, raw):
    """Seconds, or None when the container does not state it cheaply (see above).

    None means ACCEPT: for every compressed container the only cap is bytes.
    """
    if sub_type in ("wav", "x-wav", "wave", "vnd.wave"):
        return _wav_duration_seconds(raw)
    return None


def _validate_media_data_url(value, expected_type, max_bytes, label):
    # Returns None if acceptable, else a human-readable error string. Pure and
    # import-light (re + base64) so it can be unit-tested headless.
    if value is None:
        return None
    if not isinstance(value, str):
        return f"'{label}' must be a data URL string."
    m = _MEDIA_DATA_URL_RE.match(value.strip())
    if not m:
        return f"'{label}' must be a base64 data URL."
    top, sub_type, b64 = m.group(1).lower(), m.group(2).lower(), m.group(3)
    if top != expected_type:
        return f"'{label}' must be {expected_type}/*, got {top}/{sub_type}."
    if top == "image" and sub_type in ("svg+xml", "svg"):
        return f"'{label}' may not be SVG."
    # Size from the base64 length before decoding, so an oversize payload is
    # rejected without spending the CPU to decode it.
    approx = (len(b64) * 3) // 4
    if approx > max_bytes:
        return f"'{label}' is too large ({approx // 1000} kB; limit {max_bytes // 1000} kB)."
    try:
        raw = base64.b64decode(b64, validate=True)
    except Exception:
        return f"'{label}' is not valid base64."
    # Review #6: syntax + declared type + size said nothing about the BYTES.
    # 'data:image/png;base64,' (empty) and b'not a png' declared as PNG both
    # sailed through. Reject empty payloads and check the magic number, so the
    # declared container has to match what was actually sent.
    if not raw:
        return f"'{label}' is empty."
    if top == "image":
        if sub_type not in ALLOWED_IMAGE_SUBTYPES:
            return f"'{label}' has an unsupported image format ({sub_type})."
        if not _valid_image_signature(sub_type, raw):
            return f"'{label}' does not match the declared {sub_type} container."
        dims = _image_dimensions(sub_type, raw)
        if dims is _UNSCANNABLE:
            # The header could not be scanned within the bomb-check's own cost
            # bounds. A real photo never needs that many segments; refusing is
            # the whole point of the bounded scan (outside review of v263, H1).
            return (f"'{label}' declares more header than can be scanned; "
                    f"refused as a potential decompression bomb.")
        if dims is not None:
            w, h = dims
            if w > MAX_IMAGE_EDGE or h > MAX_IMAGE_EDGE:
                return (f"'{label}' is too large ({w}x{h}; limit "
                        f"{MAX_IMAGE_EDGE} px per side).")
            if w * h > MAX_IMAGE_PIXELS:
                return (f"'{label}' has too many pixels ({w * h}; limit "
                        f"{MAX_IMAGE_PIXELS}).")
    if top == "audio":
        if sub_type not in ALLOWED_AUDIO_SUBTYPES:
            return f"'{label}' has an unsupported audio format ({sub_type})."
        if not _valid_audio_signature(sub_type, raw):
            return f"'{label}' does not match the declared {sub_type} container."
        seconds = _audio_duration_seconds(sub_type, raw)
        if seconds is not None and seconds > MAX_AUDIO_SECONDS:
            return (f"'{label}' is too long ({int(seconds)}s; limit "
                    f"{MAX_AUDIO_SECONDS}s).")
    return None


def _iter_media_items(payload):
    # Yields (value, expected_type, max_bytes, label) for every media item in a
    # payload, top-level and per-frame. Frame-format Skribls carry media on their
    # frames (a classic Skribl is a 1-frame Skribl), so both must be walked.
    def scan(container, where):
        if not isinstance(container, dict):
            return
        for key, kind, cap in (("music", "audio", MAX_AUDIO_BYTES),
                               ("photo", "image", MAX_IMAGE_BYTES)):
            item = container.get(key)
            if isinstance(item, dict) and item.get("data") is not None:
                yield item["data"], kind, cap, f"{where}{key}.data"
        # baseSnapshot: Pad serialises the pre-recording canvas as a data URL
        # at the root, and the frame format reserves the same slot per frame
        # (f0.baseSnapshot falls back to payload.baseSnapshot in the player).
        # It used to be walked by NOTHING — the one media slot that was neither
        # validated, capped, nor externalised, so an uncapped inline image rode
        # every such payload into the row and back out of every GET. Same
        # image rules and cap as `photo`, since it is one. (Outside review, P1.)
        snap = container.get("baseSnapshot")
        if snap is not None:
            yield snap, "image", MAX_IMAGE_BYTES, f"{where}baseSnapshot"

    yield from scan(payload, "")
    thumb = payload.get("thumbnail")
    if thumb is not None:
        yield thumb, "image", MAX_CARD_BYTES, "thumbnail"
    frames = payload.get("frames")
    if isinstance(frames, list):
        # No slice here any more. The old frames[:200] silently skipped media on
        # frame 201+, so an oversize payload could smuggle unvalidated media past
        # the check entirely. The frame COUNT is now capped up front by
        # _validate_payload_complexity, which runs before this. (Review #2)
        for i, frame in enumerate(frames):
            yield from scan(frame, f"frames[{i}].")


# --- Structural complexity limits (review #8) --------------------------------
# MAX_CONTENT_LENGTH caps BYTES, which says nothing about rendering cost: a small
# payload can still describe a canvas or a point count that will pin a phone.
# These are deliberately far above anything the editors produce — they exist to
# stop hand-built payloads, not to constrain real drawings.
MAX_FRAMES = _env_int("SKRIBL_MAX_FRAMES", 200, minimum=1)
MAX_POINTS_PER_FRAME = _env_int("SKRIBL_MAX_POINTS_PER_FRAME", 20_000, minimum=1)
MAX_TOTAL_POINTS = _env_int("SKRIBL_MAX_TOTAL_POINTS", 200_000, minimum=1)
MAX_GROUPS_PER_FRAME = _env_int("SKRIBL_MAX_GROUPS_PER_FRAME", 5_000, minimum=1)
MAX_HOLD = _env_int("SKRIBL_MAX_HOLD", 8, minimum=1)
MAX_CANVAS_EDGE = _env_int("SKRIBL_MAX_CANVAS_EDGE", 4096, minimum=16)
COORD_LIMIT = 100_000
MAX_BRUSH = 500


def _finite(n):
    return isinstance(n, (int, float)) and not isinstance(n, bool) and math.isfinite(n)


def _validate_points(points, label, budget):
    if not isinstance(points, list):
        return f"'{label}' must be a list.", budget
    if len(points) > MAX_POINTS_PER_FRAME:
        return (f"'{label}' has too many points ({len(points)}; limit "
                f"{MAX_POINTS_PER_FRAME}).", budget)
    budget -= len(points)
    if budget < 0:
        return f"Too many points overall (limit {MAX_TOTAL_POINTS}).", budget
    for index, p in enumerate(points):
        # Non-object entries used to be skipped (round 2, #6), and coordinates
        # used to be optional (round 6, #1) — so {} and {"x": 10} were "valid"
        # while every renderer dereferences p.x/p.y directly (drawDot, drawLine,
        # nib positioning), turning them into undefined mid-canvas. Both editors
        # always emit x and y, verified against real serialised payloads, so
        # requiring them costs nothing legitimate.
        if not isinstance(p, dict):
            return f"'{label}[{index}]' must be an object.", budget
        for axis in ("x", "y"):
            if axis not in p:
                return f"'{label}[{index}].{axis}' is required.", budget
            v = p[axis]
            # NaN/Infinity arrive via hand-built JSON and imported drafts, and
            # poison every downstream bounds calculation silently.
            if not _finite(v):
                return f"'{label}[{index}].{axis}' must be finite.", budget
            if abs(v) > COORD_LIMIT:
                return f"'{label}[{index}].{axis}' is out of range.", budget
        size = p.get("size")
        if size is not None and (not _finite(size) or size <= 0 or size > MAX_BRUSH):
            return f"'{label}' has an out-of-range brush size.", budget
    return None, budget


def _validate_stroke_groups(groups, label, stroke_count):
    """Group entries are per-stroke point counts; they must account for exactly
    the points present. Applied to BOTH the classic root-level payload and each
    frame — round 3 only covered frames, so a classic Pad payload could carry
    `strokeGroups: [{"unexpected": "object"}]` unchecked. (Review round 4, #1)

    Entries must be STRICTLY POSITIVE. v114 allowed 0 on the theory that a
    degenerate stroke could emit one; that was wrong, and checking the editors
    disproves it — Flip sets curCount=1 at stroke start (flip.js:428) before
    pushing it (flip.js:460), and the Pad only pushes under
    `currentStroke.length > 0` (app.js:610, 627). Neither can emit a zero.

    Worse, a zero is actively harmful: Flip's undo does
    `splice(strokes.length - n, n)`, so n=0 removes nothing while still consuming
    a group — a no-op undo entry. `strokeGroups: [0, 1]` passes an exact-sum check
    against one point, and `[0,0,0,0]` passes against an empty frame, which would
    let a crafted payload plant thousands of dead undo steps.
    (Review round 5, #1)
    """
    if groups is None:
        # Optional only for an empty strokes array. Otherwise the stroke
        # boundaries that undo and reconstruction depend on would simply be
        # absent, which a crafted payload could do deliberately. Both editors
        # always serialise the array. (Review round 6, #2)
        if stroke_count == 0:
            return None
        return f"'{label}' is required when its strokes array contains points."
    if not isinstance(groups, list):
        return f"'{label}' must be a list."
    if len(groups) > MAX_GROUPS_PER_FRAME:
        return f"'{label}' has too many entries."
    total = 0
    for index, value in enumerate(groups):
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            return f"'{label}[{index}]' must be a positive whole number of points."
        total += value
        if total > stroke_count:
            return f"'{label}' describes more points than its strokes array."
    if total != stroke_count:
        return (f"'{label}' accounts for {total} points, but the strokes array "
                f"contains {stroke_count}.")
    return None


def _validate_payload_complexity(payload):
    """Bytes are capped elsewhere; this caps STRUCTURE. Returns an error or None."""
    cs = payload.get("canvasSize")
    if cs is not None:
        # "huge", [], {}, and half-specified objects used to pass. The client
        # ignores them, but these are public persisted payloads and the schema
        # should mean something. (Review round 6, #8)
        if not isinstance(cs, dict):
            return "'canvasSize' must be an object."
        missing = {"cssWidth", "cssHeight"} - set(cs)
        if missing:
            return "'canvasSize' must contain cssWidth and cssHeight."
        for key in ("cssWidth", "cssHeight"):
            v = cs.get(key)
            # Pixel counts, so whole numbers only — 0.5 and 4095.75 were
            # accepted before and left the client to coerce. (Review round 4, #6)
            if isinstance(v, bool) or not isinstance(v, int) or v < 1 or v > MAX_CANVAS_EDGE:
                return (f"'canvasSize.{key}' must be a whole number between 1 and "
                        f"{MAX_CANVAS_EDGE}.")
    budget = MAX_TOTAL_POINTS
    root_strokes = payload.get("strokes", [])
    err, budget = _validate_points(root_strokes, "strokes", budget)
    if err:
        return err
    if isinstance(root_strokes, list):
        err = _validate_stroke_groups(payload.get("strokeGroups"), "strokeGroups",
                                      len(root_strokes))
        if err:
            return err
    frames = payload.get("frames")
    if frames is None:
        return None
    if not isinstance(frames, list):
        return "'frames' must be a list."
    if len(frames) == 0:
        # No editor produces an empty list: Pad sends no frames key at all and
        # Flip always has at least a page. An empty list only arrives hand-made.
        return "'frames' must contain at least one frame."
    # fps rides beside frames, so it is validated here. The player reads
    # payload.fps || 12, so a bad fps does not crash — a negative one silently
    # freezes the post on page one forever. Flip's editor only produces 6/12/24;
    # 1..60 is the accepted band, bools excluded (a bool IS an int in Python).
    fps = payload.get("fps")
    if fps is not None:
        if isinstance(fps, bool) or not isinstance(fps, (int, float)) \
                or not math.isfinite(fps) or fps < 1 or fps > 60:
            return "'fps' must be a number between 1 and 60."
    if len(frames) > MAX_FRAMES:
        return f"At most {MAX_FRAMES} frames are allowed (got {len(frames)})."
    for i, frame in enumerate(frames):
        # Non-dict entries used to be skipped in silence by the media walker.
        if not isinstance(frame, dict):
            return f"'frames[{i}]' must be an object."
        frame_strokes = frame.get("strokes", [])
        err, budget = _validate_points(frame_strokes, f"frames[{i}].strokes", budget)
        if err:
            return err
        if isinstance(frame_strokes, list):
            err = _validate_stroke_groups(frame.get("strokeGroups"),
                                          f"frames[{i}].strokeGroups", len(frame_strokes))
            if err:
                return err
        hold = frame.get("hold")
        if hold is not None:
            # Integer only — fractional holds are not a supported concept and the
            # finite-range check alone allowed 1.5. (Review round 2, #6)
            if isinstance(hold, bool) or not isinstance(hold, int):
                return f"'frames[{i}].hold' must be a whole number."
            if hold < 1 or hold > MAX_HOLD:
                return f"'frames[{i}].hold' must be between 1 and {MAX_HOLD}."
    return None


def _validate_payload_media(payload):
    # First error wins; returns None when everything is acceptable.
    for value, kind, cap, label in _iter_media_items(payload):
        err = _validate_media_data_url(value, kind, cap, label)
        if err:
            return err
    return None
