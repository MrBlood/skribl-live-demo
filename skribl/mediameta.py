"""What a posted Skribl must not carry: where a photo was taken, what a file was called.

WHY THIS EXISTS (v321 preflight, PF-012). A Flip with a background photo
posted that photo byte for byte. A GPS-tagged JPEG came back from
GET /api/skribls/<id> with its coordinates and the phone's make and model
intact, for anyone holding the link; and both editors published the photo's
and the song's original file names, which on an iPhone can be the street a
voice memo was recorded on. The Pad re-encodes photos, which drops the tags,
but keeps the original bytes whenever re-encoding would not be smaller.

THE SERVER IS WHERE THIS IS ENFORCED, because it is the one place every
client's post passes through: both editors, an older cached page, a host's
own composer. create_post() calls strip_payload() after validation and before
anything is stored, so no stored post carries what this removes.

WHAT IS REMOVED, AND WHAT IS KEPT. Metadata is removed by STRUCTURE, never by
re-encoding: no pixel and no sample changes, so nothing here can make a photo
look worse or a song sound different.

  * JPEG: every APPn segment except JFIF (APP0), an ICC colour profile (APP2)
    and Adobe's colour transform (APP14); comments; anything after the end of
    the image (a "motion photo" appends a whole video there). EXIF goes, but
    its ORIENTATION is written back on its own: a portrait phone photo stores
    landscape pixels and a tag saying "turn me", and a viewer that lost the
    tag would show it on its side.
  * PNG: every chunk except the ones that draw the picture or set its colour;
    an eXIf chunk is replaced by orientation alone, as above.
  * WebP: XMP; EXIF reduced to orientation.
  * GIF: comments and XMP.
  * MP3: ID3v2 and ID3v1 tags and an APEv2 tag.
  * MP4/M4A/AAC-in-MP4: the user-data and metadata boxes (udta, meta: title,
    artist, the location atom) are renamed `free` and zeroed IN PLACE, so not
    one byte moves and the sample tables' absolute offsets stay true.
  * WAV: every chunk but fmt, fact, data and the loop/cue chunks.
  * FLAC: Vorbis comments, pictures and application blocks become padding of
    the same length.
  * Ogg/Opus and WebM pass through unchanged. Rewriting either means
    re-paging (Ogg's page checksums) or rewriting EBML element sizes; neither
    editor produces them from a recording, and that gap is recorded rather
    than papered over.

ANYTHING THAT DOES NOT PARSE IS RETURNED AS IT CAME. Validation has already
proved the container's signature and size; a file this cannot walk is
unusual, and losing someone's media is the one outcome worse than the one
this guards against. verify_mediameta.py holds every format above to removing
what it says it removes, and to the media still decoding afterwards.
"""
import base64
import re
import struct

_DATA_URL_RE = re.compile(r"^\s*data:([^;,]+)((?:;[^;,]*)*);base64,(.*)$", re.S | re.I)

ORIENTATION_TAG = 0x0112


# --- EXIF: keep the orientation, drop the rest ---------------------------------

def _exif_orientation(tiff):
    """The Orientation value in a TIFF/EXIF blob's first IFD, or None."""
    try:
        if tiff[:2] == b"II":
            e = "<"
        elif tiff[:2] == b"MM":
            e = ">"
        else:
            return None
        if struct.unpack(e + "H", tiff[2:4])[0] != 42:
            return None
        off = struct.unpack(e + "I", tiff[4:8])[0]
        count = struct.unpack(e + "H", tiff[off:off + 2])[0]
        for i in range(min(count, 512)):
            base = off + 2 + 12 * i
            tag, typ, n = struct.unpack(e + "HHI", tiff[base:base + 8])
            if tag == ORIENTATION_TAG and typ == 3 and n >= 1:
                value = struct.unpack(e + "H", tiff[base + 8:base + 10])[0]
                return value if 1 <= value <= 8 else None
    except (struct.error, IndexError):
        return None
    return None


def _orientation_tiff(value):
    """A minimal big-endian TIFF holding Orientation and nothing else."""
    return (b"MM\x00\x2a\x00\x00\x00\x08"          # header, IFD0 at 8
            + b"\x00\x01"                          # one entry
            + struct.pack(">HHIHH", ORIENTATION_TAG, 3, 1, value, 0)
            + b"\x00\x00\x00\x00")                 # no next IFD


def _kept_orientation(tiff):
    """The TIFF to write back for `tiff`: orientation alone, or None when there
    is nothing worth keeping (absent, or 1, which is the default)."""
    value = _exif_orientation(tiff)
    if value is None or value == 1:
        return None
    return _orientation_tiff(value)


# --- images -------------------------------------------------------------------

def _jpeg(raw):
    if raw[:2] != b"\xff\xd8":
        return raw
    out = bytearray(b"\xff\xd8")
    i, n = 2, len(raw)
    while i < n:
        if raw[i] != 0xFF:
            return raw
        while i < n and raw[i] == 0xFF:      # fill bytes before a marker
            i += 1
        if i >= n:
            return raw
        m = raw[i]
        i += 1
        if m == 0xD9:                         # end of image: drop what follows
            out += b"\xff\xd9"
            return bytes(out)
        if 0xD0 <= m <= 0xD7 or m == 0x01:    # markers with no length
            out += bytes((0xFF, m))
            continue
        if i + 2 > n:
            return raw
        length = (raw[i] << 8) | raw[i + 1]
        if length < 2 or i + length > n:
            return raw
        seg = raw[i:i + length]
        body = seg[2:]
        keep = True
        if 0xE0 <= m <= 0xEF:
            if m == 0xE0:
                keep = body.startswith(b"JFIF\x00")
            elif m == 0xE2:
                keep = body.startswith(b"ICC_PROFILE\x00")
            elif m == 0xEE:
                keep = body.startswith(b"Adobe")
            elif m == 0xE1 and body.startswith(b"Exif\x00\x00"):
                kept = _kept_orientation(body[6:])
                if kept is not None:
                    app1 = b"Exif\x00\x00" + kept
                    out += b"\xff\xe1" + struct.pack(">H", len(app1) + 2) + app1
                keep = False
            else:
                keep = False
        elif m == 0xFE:                       # comment
            keep = False
        if keep:
            out += bytes((0xFF, m)) + seg
        i += length
        if m == 0xDA:
            # Entropy-coded data runs to the next marker that is not a byte
            # stuffing (FF 00) or a restart (FF D0-D7).
            k = i
            while True:
                k = raw.find(b"\xff", k)
                if k < 0 or k + 1 >= n:
                    return raw                # no end of image: not ours to cut
                nxt = raw[k + 1]
                if nxt == 0x00 or 0xD0 <= nxt <= 0xD7:
                    k += 2
                    continue
                if nxt == 0xFF:
                    k += 1
                    continue
                break
            out += raw[i:k]
            i = k
    return raw


_PNG_SIG = b"\x89PNG\r\n\x1a\n"
# Chunks that draw the picture or say how its colours read. Everything else,
# text and time and EXIF above all, is left out.
_PNG_KEEP = {b"IHDR", b"PLTE", b"IDAT", b"IEND", b"tRNS", b"cHRM", b"gAMA",
             b"iCCP", b"sBIT", b"sRGB", b"cICP", b"mDCV", b"cLLI", b"bKGD",
             b"pHYs", b"acTL", b"fcTL", b"fdAT"}


def _png_chunk(kind, data):
    import zlib
    return (struct.pack(">I", len(data)) + kind + data
            + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF))


def _png(raw):
    if not raw.startswith(_PNG_SIG):
        return raw
    out = bytearray(_PNG_SIG)
    i, n = 8, len(raw)
    while i + 12 <= n:
        length = struct.unpack(">I", raw[i:i + 4])[0]
        kind = raw[i + 4:i + 8]
        end = i + 12 + length
        if end > n:
            return raw
        if kind in _PNG_KEEP:
            out += raw[i:end]
        elif kind == b"eXIf":
            kept = _kept_orientation(raw[i + 8:i + 8 + length])
            if kept is not None:
                out += _png_chunk(b"eXIf", kept)
        i = end
        if kind == b"IEND":
            return bytes(out)
    return raw


def _webp(raw):
    if len(raw) < 12 or raw[:4] != b"RIFF" or raw[8:12] != b"WEBP":
        return raw
    chunks = []
    i, n = 12, len(raw)
    while i + 8 <= n:
        kind = raw[i:i + 4]
        size = struct.unpack("<I", raw[i + 4:i + 8])[0]
        end = i + 8 + size + (size & 1)
        if i + 8 + size > n:
            return raw
        chunks.append((kind, raw[i + 8:i + 8 + size]))
        i = end
    out = []
    removed_exif = removed_xmp = kept_exif = False
    for kind, data in chunks:
        if kind == b"XMP ":
            removed_xmp = True
            continue
        if kind == b"EXIF":
            tiff = data[6:] if data.startswith(b"Exif\x00\x00") else data
            kept = _kept_orientation(tiff)
            removed_exif = True
            if kept is not None:
                out.append((kind, kept))
                kept_exif = True
            continue
        out.append((kind, data))
    if not (removed_exif or removed_xmp):
        return raw
    body = bytearray(b"WEBP")
    for kind, data in out:
        if kind == b"VP8X" and len(data) >= 1:
            flags = data[0]
            flags &= ~0x04                     # XMP present
            if not kept_exif:
                flags &= ~0x08                 # EXIF present
            data = bytes((flags,)) + data[1:]
        body += kind + struct.pack("<I", len(data)) + data
        if len(data) & 1:
            body += b"\x00"
    return b"RIFF" + struct.pack("<I", len(body)) + bytes(body)


def _gif(raw):
    if raw[:6] not in (b"GIF87a", b"GIF89a") or len(raw) < 13:
        return raw
    n = len(raw)

    def sub_blocks(j):
        while True:
            if j >= n:
                return -1
            size = raw[j]
            j += 1
            if size == 0:
                return j
            j += size

    flags = raw[10]
    i = 13
    if flags & 0x80:
        i += 3 * (2 ** ((flags & 0x07) + 1))
    out = bytearray(raw[:i])
    while i < n:
        b = raw[i]
        if b == 0x3B:                          # trailer
            out.append(0x3B)
            return bytes(out)
        if b == 0x21 and i + 1 < n:            # extension
            label = raw[i + 1]
            end = sub_blocks(i + 2)
            if end < 0:
                return raw
            drop = label == 0xFE                # comment
            if label == 0xFF and raw[i + 3:i + 14] == b"XMP DataXMP":
                drop = True
            if not drop:
                out += raw[i:end]
            i = end
            continue
        if b == 0x2C:                          # image
            if i + 10 > n:
                return raw
            j = i + 10
            lflags = raw[i + 9]
            if lflags & 0x80:
                j += 3 * (2 ** ((lflags & 0x07) + 1))
            end = sub_blocks(j + 1)            # +1: LZW minimum code size
            if end < 0:
                return raw
            out += raw[i:end]
            i = end
            continue
        return raw
    return raw


# --- audio --------------------------------------------------------------------

def _syncsafe(b):
    return (b[0] << 21) | (b[1] << 14) | (b[2] << 7) | b[3]


def _mp3(raw):
    data = raw
    # Leading ID3v2 tags (there can be more than one).
    for _ in range(8):
        if len(data) >= 10 and data[:3] == b"ID3":
            size = _syncsafe(data[6:10]) + 10
            if data[5] & 0x10:                 # footer present
                size += 10
            if size > len(data):
                return raw
            data = data[size:]
        else:
            break
    # Trailing tags, in the order they nest: ID3v1 (128), Lyrics/TAG+ are not
    # handled, APEv2 sits before ID3v1 when both are present.
    if len(data) >= 128 and data[-128:-125] == b"TAG":
        data = data[:-128]
        if len(data) >= 227 and data[-227:-223] == b"TAG+":
            data = data[:-227]
    if len(data) >= 32 and data[-32:-24] == b"APETAGEX":
        size = struct.unpack("<I", data[-20:-16])[0]
        flags = struct.unpack("<I", data[-12:-8])[0]
        total = size + (32 if flags & 0x80000000 else 0)
        if 0 < total <= len(data):
            data = data[:-total]
    return data


_MP4_CONTAINERS = {b"moov", b"trak", b"mdia", b"minf"}
_MP4_METADATA = {b"udta", b"meta"}


def _mp4(raw):
    if len(raw) < 12 or raw[4:8] != b"ftyp":
        return raw
    buf = bytearray(raw)
    changed = [False]

    def walk(start, end, depth):
        i = start
        while i + 8 <= end:
            size = struct.unpack(">I", buf[i:i + 4])[0]
            kind = bytes(buf[i + 4:i + 8])
            header = 8
            if size == 1:
                if i + 16 > end:
                    return False
                size = struct.unpack(">Q", buf[i + 8:i + 16])[0]
                header = 16
            elif size == 0:
                size = end - i
            if size < header or i + size > end:
                return False
            if kind in _MP4_METADATA:
                # Rename to `free` and zero the body: same length, so no
                # offset anywhere in the file moves.
                buf[i + 4:i + 8] = b"free"
                buf[i + header:i + size] = bytes(size - header)
                changed[0] = True
            elif kind in _MP4_CONTAINERS and depth < 8:
                if not walk(i + header, i + size, depth + 1):
                    return False
            i += size
        return True

    if not walk(0, len(buf), 0):
        return raw
    return bytes(buf) if changed[0] else raw


_WAV_KEEP = {b"fmt ", b"fact", b"data", b"cue ", b"smpl", b"inst"}


def _wav(raw):
    if len(raw) < 12 or raw[:4] != b"RIFF" or raw[8:12] != b"WAVE":
        return raw
    out = bytearray(b"WAVE")
    i, n = 12, len(raw)
    dropped = False
    while i + 8 <= n:
        kind = raw[i:i + 4]
        size = struct.unpack("<I", raw[i + 4:i + 8])[0]
        end = i + 8 + size
        if end > n:
            # A writer that never patched the data size, or a truncated file:
            # keep the rest as it is.
            if kind == b"data":
                out += raw[i:]
                i = n
                break
            return raw
        pad = size & 1
        if kind in _WAV_KEEP:
            out += raw[i:end] + (raw[end:end + pad] if pad else b"")
        else:
            dropped = True
        i = end + pad
    if not dropped:
        return raw
    return b"RIFF" + struct.pack("<I", len(out)) + bytes(out)


def _flac(raw):
    if raw[:4] != b"fLaC":
        return raw
    buf = bytearray(raw)
    i, n = 4, len(buf)
    changed = False
    while i + 4 <= n:
        head = buf[i]
        last, kind = head & 0x80, head & 0x7F
        length = (buf[i + 1] << 16) | (buf[i + 2] << 8) | buf[i + 3]
        if i + 4 + length > n:
            return raw
        if kind in (2, 4, 6):                  # application, comments, picture
            buf[i] = last | 1                   # -> padding
            buf[i + 4:i + 4 + length] = bytes(length)
            changed = True
        i += 4 + length
        if last:
            break
    return bytes(buf) if changed else raw


def strip_image(raw):
    """`raw` with location and other personal metadata removed (see above)."""
    if raw[:2] == b"\xff\xd8":
        return _jpeg(raw)
    if raw.startswith(_PNG_SIG):
        return _png(raw)
    if raw[:4] == b"RIFF" and raw[8:12] == b"WEBP":
        return _webp(raw)
    if raw[:6] in (b"GIF87a", b"GIF89a"):
        return _gif(raw)
    return raw


def strip_audio(raw):
    if raw[:3] == b"ID3" or (len(raw) >= 2 and raw[0] == 0xFF and (raw[1] & 0xE0) == 0xE0):
        return _mp3(raw)
    if len(raw) >= 12 and raw[4:8] == b"ftyp":
        return _mp4(raw)
    if raw[:4] == b"RIFF" and raw[8:12] == b"WAVE":
        return _wav(raw)
    if raw[:4] == b"fLaC":
        return _flac(raw)
    return raw


def _strip_data_url(value, kind):
    m = _DATA_URL_RE.match(value) if isinstance(value, str) else None
    if not m:
        return value
    try:
        raw = base64.b64decode(m.group(3), validate=False)
    except (ValueError, TypeError):
        return value
    clean = strip_image(raw) if kind == "photo" else strip_audio(raw)
    if clean == raw or not clean:
        return value
    return f"data:{m.group(1)}{m.group(2)};base64," + base64.b64encode(clean).decode("ascii")


# Keys a client has used for a file's own name on a media item.
_NAME_KEYS = ("name", "fileName", "filename")

#: Set on every payload create_post() stores, so GET /api/skribls/<id> knows
#: the post was stripped on the way in. A post stored before v321 lacks it and
#: is stripped on the way out instead.
STRIPPED = "metadataStripped"


def strip_payload(payload):
    """`payload` with every photo's and song's metadata and file name removed.
    Called by create_post() after validation, before storage.

    Copies only the containers it changes -- the root, the frames list and
    the frames and media items that carry media -- never the strokes, which can
    be 200,000 points: a deep copy of those cost more than the stripping."""
    def media(item, key):
        if not isinstance(item, dict):
            return item
        out = {k: v for k, v in item.items() if k not in _NAME_KEYS}
        if isinstance(out.get("data"), str):
            out["data"] = _strip_data_url(out["data"], key)
        return out

    def scan(container):
        if not isinstance(container, dict):
            return container
        if not any(k in container for k in ("photo", "music", "photoMeta", "musicMeta")):
            return container
        out = dict(container)
        for key in ("photo", "music"):
            if key in out:
                out[key] = media(out[key], key)
        for key in ("photoMeta", "musicMeta"):
            if isinstance(out.get(key), dict):
                out[key] = {k: v for k, v in out[key].items() if k not in _NAME_KEYS}
        return out

    if not isinstance(payload, dict):
        return payload
    out = scan(payload)
    frames = payload.get("frames")
    if isinstance(frames, list):
        if out is payload:
            out = dict(payload)
        out["frames"] = [scan(f) for f in frames]
    return out
