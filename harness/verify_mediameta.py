"""What a posted Skribl must not carry, and the server limits beside it (v321 preflight).

THE FINDING (PF-012). A Flip posted its background photo byte for byte: a
GPS-tagged JPEG came back from GET /api/skribls/<id> with its coordinates and
the phone's make and model, readable by anyone holding the link. Both editors
also published the photo's and the song's original file names.
skribl/mediameta.py removes both, at create_post() for every new post and on
the way out of GET /api/skribls/<id> for every post stored before it.

AND FOUR SERVER FINDINGS FROM THE SAME PREFLIGHT, each driven here:
  * PF-014 a junk string inside a stroke POINT rode past the extra-content cap
    (a 3 MB string, 3 KB gzipped, stored and served whole);
  * PF-013 an operator's takedown (`--visibility private`) was undone by the
    post's own author with their key -- `withheld` is the operator's state now;
  * PF-015 an out-of-range listing cursor was a 500;
  * PF-017 the payload GET sent no Cache-Control at all.

In-process: the standalone app on a temp SQLite file, driven with Flask's test
client. No server, no browser -- so it can sit in the PR gate.
"""
import base64
import io
import json
import os
import struct
import sys
import tempfile
import wave
from pathlib import Path

from assertions import make_check

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

results = []
check = make_check(results, with_detail=True)

try:
    from PIL import Image, PngImagePlugin
    from PIL.TiffImagePlugin import IFDRational
except ImportError:
    print("SKIP: Pillow is not installed (harness/requirements.txt)")
    sys.exit(0)

_tmp = tempfile.mkdtemp()
os.environ.update(DATABASE_URL=f"sqlite:///{_tmp}/mediameta.db", SECRET_KEY="harness-mediameta",
                  SKRIBL_RATE_MAX_POSTS="100000", SKRIBL_RATE_MAX_ATTEMPTS="100000")

from app import create_app                                          # noqa: E402
from skribl.mediameta import STRIPPED, strip_audio, strip_image      # noqa: E402
from skribl.models import SkriblPost, session                        # noqa: E402
from skribl.deletion import hash_delete_token, set_post_visibility   # noqa: E402

app = create_app()
with app.app_context():
    import app as _app_module
    _app_module.db.create_all()
client = app.test_client()

PERSONAL = (b"Elm Rd", b"Grandma", b"Apple", b"iPhone 17", b"xmpmeta", b"Main Street",
            b"recorded at home")


def leaks(raw):
    return [p.decode() for p in PERSONAL if p in raw]


def gps_exif(orientation=None):
    exif = Image.new("RGB", (8, 8)).getexif()
    exif[0x010F] = "Apple"
    exif[0x0110] = "iPhone 17"
    if orientation:
        exif[0x0112] = orientation
    exif[0x8825] = {1: "N", 2: (IFDRational(40, 1), IFDRational(44, 1), IFDRational(5468, 100)),
                    3: "W", 4: (IFDRational(73, 1), IFDRational(59, 1), IFDRational(1068, 100))}
    return exif.tobytes()


def picture(w=48, h=32):
    im = Image.new("RGB", (w, h), (30, 120, 220))
    for x in range(0, w, 6):
        for y in range(h):
            im.putpixel((x, y), (250, 220, 40))
    return im


def pixels(raw):
    im = Image.open(io.BytesIO(raw))
    im.load()
    return im.convert("RGBA").tobytes()


def gps_of(raw):
    return dict(Image.open(io.BytesIO(raw)).getexif().get_ifd(0x8825))


def jpeg(**kw):
    buf = io.BytesIO()
    picture().save(buf, format="JPEG", quality=90, **kw)
    return buf.getvalue()


def insert_segment(raw, marker, body):
    """The same JPEG with one more segment straight after SOI."""
    return raw[:2] + bytes((0xFF, marker)) + struct.pack(">H", len(body) + 2) + body + raw[2:]


# ---------------------------------------------------------------- 1. images
print("\nIMAGES — location and names leave; the picture and its orientation stay")
src = jpeg(exif=gps_exif(orientation=6))
src = insert_segment(src, 0xE1, b"http://ns.adobe.com/xap/1.0/\x00<x:xmpmeta>GPSLatitude 40,44N</x:xmpmeta>")
src = insert_segment(src, 0xFE, b"shot at 12 Elm Rd")
src = insert_segment(src, 0xED, b"Photoshop 3.0\x008BIM Grandma")
src_motion = src + b"ftypmp42 ... Grandma's video ..."           # a "motion photo" tail
out = strip_image(src_motion)
im = Image.open(io.BytesIO(out))
check("JPEG: the GPS block is gone", not gps_of(out), str(gps_of(out)) or "none")
check("JPEG: make, model, XMP, comment and Photoshop/IPTC text are gone", not leaks(out),
      f"before {leaks(src_motion)}, after {leaks(out)}")
check("JPEG: the orientation survives, alone", im.getexif().get(0x0112) == 6 and len(im.getexif()) == 1,
      f"orientation {im.getexif().get(0x0112)}, {len(im.getexif())} tag(s) left")
check("JPEG: whatever followed the end of the image is cut", out.endswith(b"\xff\xd9"),
      f"{len(src_motion) - len(out)} bytes removed")
check("JPEG: every pixel is the same", pixels(out) == pixels(src))
prog = jpeg(exif=gps_exif(orientation=3), progressive=True)
pout = strip_image(prog)
check("JPEG, progressive: tags gone, orientation and pixels kept",
      not leaks(pout) and not gps_of(pout) and Image.open(io.BytesIO(pout)).getexif().get(0x0112) == 3
      and pixels(pout) == pixels(prog), f"leaks {leaks(pout)}")
plain = jpeg()
check("a JPEG with nothing to remove comes back byte for byte", strip_image(plain) == plain)

buf = io.BytesIO()
info = PngImagePlugin.PngInfo()
info.add_text("Comment", "shot at 12 Elm Rd")
info.add_itxt("Location", "Grandma", zip=True)
picture().save(buf, format="PNG", pnginfo=info, exif=gps_exif(orientation=6))
png = buf.getvalue()
pout = strip_image(png)
check("PNG: text, iTXt and EXIF tags are gone", not leaks(pout) and not gps_of(pout),
      f"before {leaks(png)}, after {leaks(pout)}")
check("PNG: the orientation survives and the pixels are the same",
      Image.open(io.BytesIO(pout)).getexif().get(0x0112) == 6 and pixels(pout) == pixels(png))

buf = io.BytesIO()
picture().save(buf, format="WEBP", lossless=True, exif=gps_exif(orientation=6),
               xmp=b"<x:xmpmeta>GPSLatitude 40,44N</x:xmpmeta>")
webp = buf.getvalue()
wout = strip_image(webp)
check("WebP: EXIF reduced to orientation, XMP gone",
      not leaks(wout) and not gps_of(wout) and Image.open(io.BytesIO(wout)).getexif().get(0x0112) == 6,
      f"before {leaks(webp)}, after {leaks(wout)}")
check("WebP: the pixels are the same, and the container's own size is right",
      pixels(wout) == pixels(webp) and wout[:4] == b"RIFF" and wout[8:12] == b"WEBP"
      and struct.unpack("<I", wout[4:8])[0] == len(wout) - 8)

buf = io.BytesIO()
frames = [picture().convert("P"), picture().transpose(Image.FLIP_LEFT_RIGHT).convert("P")]
frames[0].save(buf, format="GIF", save_all=True, append_images=frames[1:], duration=100,
               loop=0, comment=b"12 Elm Rd")
gif = buf.getvalue()
gout = strip_image(gif)
gim = Image.open(io.BytesIO(gout))
check("GIF: the comment is gone, both frames and the loop stay",
      not leaks(gout) and getattr(gim, "n_frames", 1) == 2 and gim.info.get("loop") == 0,
      f"before {leaks(gif)}, after {leaks(gout)}, {getattr(gim, 'n_frames', 1)} frames")
for name, junk in (("a cut-off JPEG", b"\xff\xd8\xff\xe1\x00"), ("empty", b""), ("text", b"not an image")):
    try:
        same = strip_image(junk) == junk
    except Exception as e:                                            # noqa: BLE001
        same = False
        junk = repr(e).encode()
    check(f"an unreadable image ({name}) comes back untouched, never raises", same, junk[:40])


# ---------------------------------------------------------------- 2. audio
print("\nAUDIO — tags leave; the samples stay")
FRAME = b"\xff\xfb\x90\x64" + bytes(413)           # one MPEG-1 Layer III frame, silent
id3v2 = (b"ID3\x03\x00\x00" + bytes((0, 0, 0, 25))
         + b"TIT2" + struct.pack(">I", 15) + b"\x00\x00" + b"123 Main Street")
id3v1 = b"TAG" + b"123 Main Street".ljust(30, b"\x00") + bytes(95)
mp3 = id3v2 + FRAME * 4 + id3v1
mout = strip_audio(mp3)
check("MP3: the ID3v2 and ID3v1 tags are gone", not leaks(mout) and mout.startswith(b"\xff\xfb"),
      f"{len(mp3)} -> {len(mout)} bytes")
check("MP3: every frame is still there, and nothing else", mout == FRAME * 4)


def box(kind, body):
    return struct.pack(">I", len(body) + 8) + kind + body


udta = box(b"udta", box(b"\xa9nam", b"123 Main Street") + box(b"\xa9xyz", b"+40.7484-073.9857/"))
meta = box(b"meta", bytes(4) + box(b"ilst", box(b"\xa9ART", b"Aaron's iPhone 17")))
trak = box(b"trak", box(b"tkhd", bytes(84)) + box(b"udta", box(b"name", b"Elm Rd")))
moov = box(b"moov", box(b"mvhd", bytes(100)) + trak + udta + meta)
mdat = box(b"mdat", b"AUDIO-SAMPLES" * 20)
m4a = box(b"ftyp", b"M4A \x00\x00\x02\x00isomiso2") + moov + mdat
m4out = strip_audio(m4a)
check("M4A: the title, location and artist boxes are gone", not leaks(m4out) and b"+40.7484" not in m4out,
      f"before {leaks(m4a)}, after {leaks(m4out)}")
check("M4A: not one byte moved -- same length, the samples at the same offset",
      len(m4out) == len(m4a) and m4out.index(b"AUDIO-SAMPLES") == m4a.index(b"AUDIO-SAMPLES"))
check("M4A: the three metadata boxes became `free`", m4out.count(b"free") == 3, f"{m4out.count(b'free')} free boxes")

wbuf = io.BytesIO()
with wave.open(wbuf, "wb") as w:
    w.setnchannels(1)
    w.setsampwidth(2)
    w.setframerate(8000)
    w.writeframes(struct.pack("<200h", *range(200)))
wav = wbuf.getvalue()
listc = b"LIST" + struct.pack("<I", 4 + 8 + 16) + b"INFO" + b"INAM" + struct.pack("<I", 16) + b"recorded at home"
WAV_TAGGED = b"RIFF" + struct.pack("<I", len(wav) - 8 + len(listc)) + wav[8:] + listc
wout = strip_audio(WAV_TAGGED)
with wave.open(io.BytesIO(wout)) as w:
    same_samples = w.readframes(w.getnframes()) == struct.pack("<200h", *range(200))
check("WAV: the LIST/INFO chunk is gone and every sample reads back", not leaks(wout) and same_samples,
      f"{len(WAV_TAGGED)} -> {len(wout)} bytes")

vorbis = struct.pack("<I", 4) + b"test" + struct.pack("<I", 1) + struct.pack("<I", 13) + b"TITLE=Elm Rd!"
flac = (b"fLaC" + b"\x00" + (34).to_bytes(3, "big") + bytes(34)
        + bytes((0x80 | 4,)) + len(vorbis).to_bytes(3, "big") + vorbis + b"FRAMES")
fout = strip_audio(flac)
head = 4 + 4 + 34
check("FLAC: the comment block became padding of the same length",
      not leaks(fout) and len(fout) == len(flac) and fout[head] & 0x7F == 1 and fout[head] & 0x80
      and fout.endswith(b"FRAMES"), f"block type {fout[head] & 0x7F}")
ogg = b"OggS" + bytes(20) + b"TITLE=Elm Rd"
check("Ogg passes through unchanged (a recorded gap, not a handled format)", strip_audio(ogg) == ogg)


# ---------------------------------------------------------------- 3. through the API
print("\nTHROUGH THE API — what a viewer of the link receives")


def data_url(mime, raw):
    return f"data:{mime};base64," + base64.b64encode(raw).decode("ascii")


def decoded(item):
    return base64.b64decode(item["data"].split(",", 1)[1])


GPS_JPEG = jpeg(exif=gps_exif(orientation=6))
POINTS = [{"x": 10 + i * 4, "y": 20, "color": "#ffffff", "size": 6, "t": i * 16, "start": i == 0}
          for i in range(12)]


def flip_body():
    return {"title": "metadata probe", "visibility": "public", "playbackMode": "flipbook", "fps": 12,
            "frames": [{"strokes": POINTS, "strokeGroups": [len(POINTS)],
                        "photo": {"data": data_url("image/jpeg", GPS_JPEG),
                                  "name": "IMG_4821 home backyard.jpg", "fit": "cover"},
                        "music": {"data": data_url("audio/wav", WAV_TAGGED),
                                  "name": "Kitchen at 12 Elm Rd.wav", "trimStart": 0, "trimEnd": 0.02}},
                       {"strokes": POINTS, "strokeGroups": [len(POINTS)]}],
            "canvasSize": {"cssWidth": 816, "cssHeight": 612}}


def pad_body():
    return {"title": "metadata probe pad", "strokes": POINTS, "strokeGroups": [len(POINTS)],
            "photo": {"data": data_url("image/jpeg", GPS_JPEG), "name": "IMG_4821 home backyard.jpg"},
            "music": {"data": data_url("audio/wav", WAV_TAGGED), "name": "Kitchen at 12 Elm Rd.wav"}}


def media_of(sk):
    out = {}
    for c in [sk] + list(sk.get("frames") or []):
        for k in ("photo", "music"):
            if isinstance(c.get(k), dict) and c[k].get("data"):
                out.setdefault(k, c[k])
    return out


for label, body in (("Flip (media on a page)", flip_body()), ("Pad (media at the root)", pad_body())):
    r = client.post("/api/skribls", json=body)
    check(f"{label}: posted", r.status_code == 201, f"HTTP {r.status_code} {r.get_data(as_text=True)[:120]}")
    pid = (r.get_json() or {}).get("id")
    g = client.get(f"/api/skribls/{pid}")
    media = media_of((g.get_json() or {}).get("skribl", {}))
    photo, music = media.get("photo"), media.get("music")
    raw = decoded(photo) if photo else b""
    check(f"{label}: the photo a viewer gets has no location in it",
          bool(raw) and not gps_of(raw) and not leaks(raw),
          f"GPS {gps_of(raw) if raw else 'n/a'}, text {leaks(raw) if raw else 'n/a'}")
    check(f"{label}: ...and is the same picture, still upright",
          bool(raw) and Image.open(io.BytesIO(raw)).getexif().get(0x0112) == 6 and pixels(raw) == pixels(GPS_JPEG))
    check(f"{label}: no file name anywhere in what a viewer gets",
          b"backyard" not in g.get_data() and b"Elm Rd" not in g.get_data()
          and bool(photo) and "name" not in photo and bool(music) and "name" not in music)
    check(f"{label}: the song's tags are gone and its samples read back",
          bool(music) and not leaks(decoded(music)) and wave.open(io.BytesIO(decoded(music))).getnframes() == 200)
    check(f"{label}: never kept by a shared cache", g.headers.get("Cache-Control") == "private, no-store",
          repr(g.headers.get("Cache-Control")))
    with app.app_context():
        stored = session().query(SkriblPost).filter_by(public_id=pid).one().payload_json
    check(f"{label}: the STORED post holds neither, and says it was stripped",
          stored.get(STRIPPED) is True and b"backyard" not in json.dumps(stored).encode()
          and not leaks(decoded(media_of(stored)["photo"])))

print("\nA POST STORED BEFORE THIS — stripped on the way out, its row left alone")
with app.app_context():
    s = session()
    s.add(SkriblPost(public_id="legacy0001A", title="before", payload_json=flip_body(),
                     visibility="public", delete_token_hash=hash_delete_token("k" * 43)))
    s.commit()
g = client.get("/api/skribls/legacy0001A")
media = media_of((g.get_json() or {}).get("skribl", {}))
raw = decoded(media["photo"]) if media.get("photo") else b""
check("a legacy post's photo is served without its location", bool(raw) and not gps_of(raw) and not leaks(raw))
check("...and without its file names", b"backyard" not in g.get_data() and b"Elm Rd" not in g.get_data())
with app.app_context():
    row = session().query(SkriblPost).filter_by(public_id="legacy0001A").one().payload_json
check("...and the GET wrote nothing back: a read stays a read",
      "IMG_4821 home backyard.jpg" in json.dumps(row) and STRIPPED not in row)
body = flip_body()
before = json.dumps(body, sort_keys=True)
client.post("/api/skribls", json=body)
check("the caller's own dict is not edited by posting it", json.dumps(body, sort_keys=True) == before)


# ---------------------------------------------------------------- 4. points
print("\nPOINTS — what a point carries beyond x, y and size is measured too")
for label, body in (
        ("a 3 MB string on one point",
         {"strokes": [{"x": 0, "y": 0, "j": "A" * 3_000_000}], "strokeGroups": [1]}),
        ("a 400 kB colour on a page's point",
         {"frames": [{"strokes": [{"x": 0, "y": 0, "color": "B" * 400_000}], "strokeGroups": [1]}]}),
        ("an object where a time goes",
         {"strokes": [{"x": 0, "y": 0, "t": {"k": "C" * 300_000}}], "strokeGroups": [1]})):
    r = client.post("/api/skribls", json=body)
    check(f"{label} is refused", r.status_code == 400 and "extra content" in r.get_data(as_text=True),
          f"HTTP {r.status_code} {r.get_data(as_text=True)[:90]}")
r = client.post("/api/skribls", json={"strokes": [{"x": 0, "y": 0, "pressure": 0.5}], "strokeGroups": [1]})
check("a small unknown key an older client wrote still posts", r.status_code == 201, f"HTTP {r.status_code}")
demos = sorted((ROOT / "skribl" / "static" / "help" / "demos").glob("*.json"))
refused = [d.name for d in demos
           if client.post("/api/skribls", json=json.loads(d.read_text())).status_code != 201]
check("every example drawing in How it works still posts", bool(demos) and not refused,
      f"{len(demos)} examples; refused: {refused}")


# ---------------------------------------------------------------- 5. withheld
print("\nWITHHELD — an operator's takedown stays down")
r = client.post("/api/skribls", json={"strokes": POINTS, "strokeGroups": [len(POINTS)], "visibility": "public"})
pid, tok = r.get_json()["id"], r.get_json()["deleteToken"]
with app.app_context():
    set_post_visibility(pid, SkriblPost.WITHHELD, require_author=False)
    session().commit()
check("withheld: gone for a visitor", client.get(f"/api/skribls/{pid}").status_code == 404)
r = client.patch(f"/api/skribls/{pid}", json={"visibility": "public", "deleteToken": tok})
check("the author's key cannot put it back up", r.status_code == 400 and "withdrawn" in r.get_data(as_text=True),
      f"HTTP {r.status_code} {r.get_data(as_text=True)[:100]}")
with app.app_context():
    vis = session().query(SkriblPost).filter_by(public_id=pid).one().visibility
check("...and it is still withheld", vis == SkriblPost.WITHHELD, vis)
r = client.patch(f"/api/skribls/{pid}", json={"visibility": "public", "deleteToken": "x" * 43})
check("nobody else learns why: a wrong key gets the 404 a missing post gets", r.status_code == 404,
      f"HTTP {r.status_code}")
r = client.post("/api/skribls", json={"strokes": POINTS, "strokeGroups": [len(POINTS)], "visibility": "withheld"})
check("no post can be created withheld", r.status_code == 400, f"HTTP {r.status_code}")
r = client.post("/api/skribls", json={"strokes": POINTS, "strokeGroups": [len(POINTS)], "visibility": "unlisted"})
p2, t2 = r.get_json()["id"], r.get_json()["deleteToken"]
r = client.patch(f"/api/skribls/{p2}", json={"visibility": "withheld", "deleteToken": t2})
check("and an author cannot choose it", r.status_code == 400, f"HTTP {r.status_code}")
r = client.delete(f"/api/skribls/{pid}", json={"deleteToken": tok})
check("the author can still delete a withheld post, which takes it down further",
      r.status_code in (200, 204), f"HTTP {r.status_code}")


# ---------------------------------------------------------------- 6. cursors
print("\nCURSORS — a number past 64 bits is an unusable cursor, not a crash")


def b64(s):
    return base64.urlsafe_b64encode(s.encode()).decode().rstrip("=")


for label, q in (("hot, huge score", "sort=hot&cursor=" + b64("hot|99999999999999999999999|1")),
                 ("hot, huge id", "sort=hot&cursor=" + b64("hot|1|99999999999999999999999")),
                 ("new, huge id", "cursor=" + b64("2026-10-09T00:00:00+00:00|99999999999999999999999")),
                 ("hot, negative", "sort=hot&cursor=" + b64("hot|-5|1"))):
    r = client.get("/api/skribls?" + q)
    check(f"{label}: 400", r.status_code == 400, f"HTTP {r.status_code}")
r = client.get("/api/skribls?cursor=" + b64("2026-10-09T00:00:00+00:00|5"))
check("a real cursor still pages", r.status_code == 200, f"HTTP {r.status_code}")

print(f"\n{'=' * 62}")
bad = [r for r in results if not r[0]]
print(f"{len(results) - len(bad)}/{len(results)} passed")
for r in bad:
    print(f"  FAILED: {r[1]} — {r[2] if len(r) > 2 else ''}")
sys.exit(1 if bad else 0)
