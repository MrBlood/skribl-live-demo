"""Does `python -m skribl.mediareport` measure what the database really holds?

The owner asked where photo and music files should live, and the answer turned
on numbers nobody had: how many bytes of media the live database carries, and
how fast that grows. This report is the instrument that answers it, so it gets
calibrated like one: every figure below is checked against posts planted with
KNOWN sizes, so an off-by-a-third base64 miscount (the obvious way to get it
wrong) cannot pass as a measurement.

And it is READ-ONLY, which is the property that makes it safe to paste into a
production shell. That is checked on the database file's bytes, not on the
absence of a write flag in the source.

Runs in-process against a temp SQLite file, CLI driven as a real subprocess. No
server, no browser.
"""
import base64
import datetime
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from assertions import make_check

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

DB_DIR = tempfile.mkdtemp()
DB_PATH = f"{DB_DIR}/mediareport.db"
ENV = dict(os.environ, DATABASE_URL=f"sqlite:///{DB_PATH}",
           SKRIBL_MEDIA_BACKEND="inline", SECRET_KEY="harness-mediareport")
os.environ.update(ENV)

from app import create_app                                        # noqa: E402
from skribl.models import SkriblPost, session                     # noqa: E402
from skribl.mediareport import decoded_len                        # noqa: E402

results = []
check = make_check(results)

app = create_app()
with app.app_context():
    import app as _app_module
    _app_module.db.create_all()


def data_url(mime, n):
    return f"data:{mime};base64," + base64.b64encode(b"\x07" * n).decode()


# Sizes chosen so every base64 padding case is exercised: 3000 % 3 == 0 (no
# padding), 6001 % 3 == 1 ("=="), 302 % 3 == 2 ("=").
PHOTO, MUSIC, FRAME_PHOTO, THUMB = 3000, 6001, 302, 500


def plant():
    with app.app_context():
        s = session()
        sep, oct_ = (datetime.datetime(2026, 9, 3, tzinfo=datetime.timezone.utc),
                     datetime.datetime(2026, 10, 7, tzinfo=datetime.timezone.utc))
        s.add(SkriblPost(public_id="mr-media", title="both", visibility="public",
                         created_at=sep, payload_json={
                             "photo": {"data": data_url("image/png", PHOTO)},
                             "music": {"data": data_url("audio/wav", MUSIC)},
                             "thumbnail": data_url("image/png", THUMB),
                             "frames": [{"photo": {"data": data_url("image/png", FRAME_PHOTO)}}]}))
        # Already externalised: a URL, not a data URL. Counted, never sized —
        # its bytes are not in this database.
        s.add(SkriblPost(public_id="mr-ext", title="ext", visibility="public",
                         created_at=oct_, payload_json={
                             "photo": {"data": "/skribl/media/0123456789abcdef.png"}}))
        s.add(SkriblPost(public_id="mr-none", title="plain", visibility="public",
                         created_at=oct_, payload_json={"strokes": [[1, 2, 3]]}))
        s.commit()


def run(*args):
    p = subprocess.run([sys.executable, "-m", "skribl.mediareport",
                        "--app", "app:create_app", *args],
                       cwd=ROOT, env=ENV, capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr


print("\nMEDIAREPORT — base64 is sized exactly, every padding case")
_bad = [n for n in range(0, 40)
        if decoded_len(data_url("image/png", n)) != n]
check("decoded size equals the real byte count for 0..39 bytes", not _bad,
      f"wrong for {_bad[:8]}")

plant()
with open(DB_PATH, "rb") as fh:
    before = hashlib.sha256(fh.read()).hexdigest()

print("\nMEDIAREPORT — the figures match what was planted")
code, out, err = run("--json")
check("--json exits 0", code == 0, err.strip()[-300:])
r = json.loads(out) if code == 0 else {}
check("counts every post", r.get("posts") == 3, r.get("posts"))
check("a post carries a photo or music wherever it is stored (inline or not)",
      r.get("posts_with_photo_or_music") == 2, r.get("posts_with_photo_or_music"))
_in = r.get("inline", {})
check("photo bytes are the top-level AND the per-frame photo, decoded",
      _in.get("photo") == {"items": 2, "bytes": PHOTO + FRAME_PHOTO, "posts": 1},
      _in.get("photo"))
check("music bytes are decoded, not base64 length",
      _in.get("music") == {"items": 1, "bytes": MUSIC, "posts": 1}, _in.get("music"))
check("the share-card thumbnail is its own line, not folded into photo",
      _in.get("thumbnail", {}).get("bytes") == THUMB, _in.get("thumbnail"))
check("inline total is the sum of the kinds",
      r.get("inline_media_bytes") == PHOTO + FRAME_PHOTO + MUSIC + THUMB,
      r.get("inline_media_bytes"))
check("an already-externalised photo is counted and not sized",
      r.get("externalised_items", {}).get("photo") == 1, r.get("externalised_items"))
check("growth by month: September holds the media, October holds none",
      r.get("by_month") == {"2026-09": {"posts": 1, "media_bytes": PHOTO + FRAME_PHOTO + MUSIC + THUMB},
                            "2026-10": {"posts": 2, "media_bytes": 0}},
      r.get("by_month"))
check("the largest post is named, with its size",
      (r.get("largest") or [{}])[0] == {"public_id": "mr-media",
                                        "media_bytes": PHOTO + FRAME_PHOTO + MUSIC + THUMB},
      r.get("largest"))
check("it names the store and the database it measured",
      r.get("store") == "InlineStore" and r.get("dialect") == "sqlite"
      and (r.get("database_bytes") or 0) > 0,
      {k: r.get(k) for k in ("store", "dialect", "database_bytes")})

print("\nMEDIAREPORT — read-only, and readable")
code, out, err = run()
check("the readable report exits 0 and says it changed nothing",
      code == 0 and "Nothing was changed" in out and "/s/mr-media" in out,
      (out + err)[-300:])
with open(DB_PATH, "rb") as fh:
    after = hashlib.sha256(fh.read()).hexdigest()
check("the database file is byte-identical after two runs", before == after)
code, _out, err = run("--app", "nosuchmodule:app")
check("an app it cannot load is exit 2 with a reason, not a traceback",
      code == 2 and "could not import" in err and "Traceback" not in err, err.strip()[-200:])

passed = sum(1 for ok, _ in results if ok)
bad = [name for ok, name in results if not ok]
print("\n" + "=" * 62)
print(f"{passed}/{len(results)} passed" + ("" if not bad else "\nFAILURES:\n  - " + "\n  - ".join(bad)))
sys.exit(1 if bad else 0)
