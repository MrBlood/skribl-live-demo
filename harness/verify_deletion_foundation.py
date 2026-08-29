"""Does the deletion foundation actually hold?

The host-controls proposal puts delete_skribl() first on the build order and
argues it is cheap ONLY because c7e1a5f04b93's ON DELETE CASCADE and
storage.sweep_orphans() landed first — that before the FK, deleting a post
orphaned its association rows, the sweep treated the media as still referenced,
and the takedown left the image reachable at its URL.

That is the security claim the whole build order rests on. It has never been
executed. This runs it, on PostgreSQL, with the local media backend:

    1. post a Skribl carrying a photo         -> media stored, association written
    2. GET /media/<key>                        -> reachable while referenced
    3. delete the post row (what delete_skribl would do)
    4. associations cascade away
    5. GET /media/<key>                        -> MUST now refuse
    6. sweep_orphans(dry_run=True)             -> names the key
    7. sweep_orphans(dry_run=False)            -> bytes gone from disk

Step 5 is the one that matters. If a deleted post's media stays reachable, then
delete_skribl() is a takedown that does not take anything down.
"""
import base64
import json
import os
import struct
import sys
import urllib.error
import urllib.request
import zlib

BASE = os.environ.get("SKRIBL_BASE", "http://127.0.0.1:5001")
SKIP_EXIT = 77
results = []


def check(name, ok, detail=""):
    results.append((bool(ok), name))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  — {detail}" if detail else ""))


def png_data_url(w=16, h=16):
    rows = b""
    for y in range(h):
        rows += b"\x00" + bytes(v for x in range(w)
                                for v in ((x * 16) % 256, (y * 16) % 256, 200))

    def chunk(tag, data):
        c = tag + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xffffffff)

    raw = (b"\x89PNG\r\n\x1a\n"
           + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(rows)) + chunk(b"IEND", b""))
    return "data:image/png;base64," + base64.b64encode(raw).decode()


def get(url):
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, b""


# This suite is only meaningful with the LOCAL media backend: the inline store
# keeps media inside payload_json, so there is no /media/<key> to revoke and
# nothing for the sweep to reclaim. It cannot simply demand that of the shared
# harness instance, because verify_storage.py asserts the exact opposite — that
# the default instance stores media INLINE. Two suites, contradictory
# environments, and whichever one lost would skip.
#
# So it brings its OWN server, the way verify_review.py does for its quota work.
# A skip is not coverage, and a suite that needs a different configuration from
# the shared one should supply it rather than stand down. An explicit
# SKRIBL_BASE is still honoured for anyone pointing this at their own server.
import contextlib                                            # noqa: E402
import pathlib                                               # noqa: E402
import socket                                                # noqa: E402
import subprocess                                            # noqa: E402
import tempfile                                              # noqa: E402
import time                                                  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def _free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


@contextlib.contextmanager
def local_media_server(media_dir):
    """A server process backed by the local media store."""
    port = _free_port()
    env = dict(os.environ)
    env["SKRIBL_MEDIA_BACKEND"] = "local"
    env["SKRIBL_MEDIA_ROOT"] = str(media_dir)
    env.setdefault("SKRIBL_RATE_MAX_POSTS", "100000")
    proc = subprocess.Popen(
        [sys.executable, "-m", "flask", "--app", "app", "run",
         "--port", str(port), "--no-reload"],
        cwd=str(ROOT), env=env,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    base = "http://127.0.0.1:" + str(port)
    try:
        # Yielding regardless of whether startup worked turns one clear failure
        # into a pile of confusing request errors. Same lesson as verify_review.
        ready = False
        for _ in range(80):
            if proc.poll() is not None:
                raise RuntimeError(
                    "local-media server exited during startup with "
                    + str(proc.returncode))
            try:
                urllib.request.urlopen(base + "/", timeout=1)
                ready = True
                break
            except urllib.error.HTTPError:
                ready = True
                break
            except Exception:
                time.sleep(0.25)
        if not ready:
            raise RuntimeError("local-media server did not become ready")
        yield base
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except Exception:
            proc.kill()


# The variable is SKRIBL_MEDIA_ROOT (see app.py) — NOT SKRIBL_MEDIA_DIR, which
# nothing reads. Getting that name wrong is not cosmetic here: the store falls
# back to instance/media, this suite calls sweep_orphans(dry_run=False) against
# whatever root it is pointed at, and a shared root means deleting media that
# belongs to other suites. Observed doing exactly that — ten objects from
# earlier runs, swept. An isolated root per run is what makes it safe to put a
# destructive suite in the aggregate at all.
_MEDIA_DIR = pathlib.Path(os.environ.get("SKRIBL_MEDIA_ROOT")
                          or tempfile.mkdtemp(prefix="skribl-deletion-"))
_MEDIA_DIR.mkdir(parents=True, exist_ok=True)
os.environ["SKRIBL_MEDIA_BACKEND"] = "local"
os.environ["SKRIBL_MEDIA_ROOT"] = str(_MEDIA_DIR)

_explicit = os.environ.get("SKRIBL_BASE")
_ctx = (contextlib.nullcontext(_explicit) if _explicit
        else local_media_server(_MEDIA_DIR))
BASE = _ctx.__enter__()
# The context manager is entered at module level, so its finally clause would
# never run on sys.exit() — the subprocess would outlive the suite, and a
# stranded server holding a port is exactly what makes the NEXT run test a stale
# tree and report green.
import atexit                                                # noqa: E402
atexit.register(lambda: _ctx.__exit__(None, None, None))
print("local-media server: " + BASE + "  (media dir " + str(_MEDIA_DIR) + ")\n")

strokes = [{"x": 10 + i * 5, "y": 20 + i * 3, "t": i * 16, "size": 5,
            "color": "#7c5cff", "down": i > 0} for i in range(30)]
payload = {"title": "Deletion foundation", "caption": "", "visibility": "public",
           "canvas": {"w": 816, "h": 612},
           "strokes": strokes, "strokeGroups": [len(strokes)],
           "frames": [{"strokes": strokes, "strokeGroups": [len(strokes)], "hold": 1}],
           "photo": {"data": png_data_url(), "name": "bg.png", "fit": "cover"}}

req = urllib.request.Request(BASE + "/api/skribls", data=json.dumps(payload).encode(),
                             headers={"Content-Type": "application/json"}, method="POST")
with urllib.request.urlopen(req, timeout=60) as r:
    created = json.loads(r.read().decode())
public_id = created["id"]
print(f"posted {public_id}\n")

# Anchor on THIS FILE, not the process CWD. run_harness.sh does `cd $ROOT/harness`
# before invoking a suite (line 173), so os.path.abspath(".") resolved to
# harness/ and `from app import ...` raised ModuleNotFoundError — the suite
# crashed before reporting a single assertion. verify_storage.py already uses
# the parents[1] idiom; this now matches it.
import pathlib                                              # noqa: E402
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
os.environ.setdefault("SKRIBL_MEDIA_BACKEND", "local")
from app import app, db                                    # noqa: E402
import skribl.storage as storage                            # noqa: E402
from skribl.models import SkriblPost, SkriblPostMedia       # noqa: E402

with app.app_context():
    post_row = db.session.query(SkriblPost).filter_by(public_id=public_id).one()
    keys = [r[0] for r in db.session.query(SkriblPostMedia.media_key)
            .filter_by(post_id=post_row.id).all()]
    check("the post wrote a media association", len(keys) == 1, f"keys={keys}")
    key = keys[0]

    status, body = get(f"{BASE}/media/{key}")
    check("media is reachable while the post references it",
          status == 200 and len(body) > 0, f"HTTP {status}, {len(body)} bytes")

    store = app.extensions["skribl"].get("store") or storage.LocalDiskStore(
        os.environ.get("SKRIBL_MEDIA_ROOT", os.path.join(app.instance_path, "media")),
        lambda k: "/media/" + k)
    on_disk_before = any(k == key for k, _ in store.iter_keys())
    check("and the bytes are on disk", on_disk_before)

    # --- what delete_skribl() would do ------------------------------------
    db.session.delete(post_row)
    db.session.commit()

    left = db.session.query(SkriblPostMedia).filter_by(post_id=post_row.id).count()
    check("deleting the post cascades its associations away", left == 0,
          f"{left} association row(s) survived — before c7e1a5f04b93 these "
          "stayed, and the sweep then read the media as still referenced")

    status_after, _ = get(f"{BASE}/media/{key}")
    check("THE ONE THAT MATTERS: media is refused once the post is gone",
          status_after in (403, 404),
          f"HTTP {status_after} — a takedown that leaves the image at its URL "
          "is not a takedown")

    # --- the sweep reclaims the bytes -------------------------------------
    dry = storage.sweep_orphans(store, db.session, older_than_seconds=0, dry_run=True)
    check("sweep_orphans names the key as an orphan", key in dry, f"dry run: {dry}")

    still = any(k == key for k, _ in store.iter_keys())
    check("and dry_run really did not delete anything", still)

    wet = storage.sweep_orphans(store, db.session, older_than_seconds=0, dry_run=False)
    gone = not any(k == key for k, _ in store.iter_keys())
    check("a real sweep reclaims the bytes", key in wet and gone,
          f"swept={wet}, still on disk={not gone}")

    # --- the sweep touches ONLY Skribl-shaped keys ------------------------
    # A store view can see more than this deployment wrote: an S3 prefix
    # shorter than a co-tenant's lists the co-tenant's objects, and a local
    # media root can hold stray files. Every one of them is by definition
    # unreferenced by OUR association table, so the pre-guard sweep's next
    # step was TO DELETE THEM. (Outside review, P1.) Plant two non-Skribl
    # objects — a co-tenant-namespaced key and a stray file — age them past
    # any grace period, and require the sweep to leave both alone.
    _root = getattr(store, "root", None)
    if _root:
        _alien1 = os.path.join(_root, "tenant-b")
        os.makedirs(_alien1, exist_ok=True)
        _alien1 = os.path.join(_alien1, "0" * 64 + ".png")
        with open(_alien1, "wb") as _f:
            _f.write(b"co-tenant bytes")
        _alien2 = os.path.join(_root, "README-not-media.txt")
        with open(_alien2, "wb") as _f:
            _f.write(b"stray host file")
        _old = time.time() - 10 * 86400
        os.utime(_alien1, (_old, _old))
        os.utime(_alien2, (_old, _old))
        _wet2 = storage.sweep_orphans(store, db.session,
                                      older_than_seconds=0, dry_run=False)
        check("a co-tenant's namespaced object survives a real sweep",
              os.path.exists(_alien1), f"swept: {_wet2}")
        check("a stray non-Skribl file survives it too",
              os.path.exists(_alien2), f"swept: {_wet2}")
        os.remove(_alien1)
        os.remove(_alien2)

    # --- OUTSIDE REVIEW v223 #2: the guard's extension set -----------------
    # The two objects planted above are rejected for reasons that have nothing
    # to do with their extension: one carries a slash, the other is not 64 hex.
    # They prove the guard works in the two shapes somebody thought of and say
    # nothing about the one where the EXTENSION is the only thing separating a
    # co-tenant's object from ours.
    #
    # KEY_RE was `[0-9a-f]{64}\.[a-z0-9]{2,4}`, so <64hex>.html and <64hex>.txt
    # match it exactly while being nothing Skribl can emit — the writable set is
    # _TYPE_FOR_EXT, twelve extensions. In a shared root or under a short S3
    # prefix, a wet sweep deleted them.
    if _root:
        _alien3 = os.path.join(_root, "ab", "cd")
        os.makedirs(_alien3, exist_ok=True)
        _planted = []
        for _ext in ("html", "txt", "json", "exe"):
            _pth = os.path.join(_alien3, "ab" + "cd" + "e" * 60 + "." + _ext)
            with open(_pth, "wb") as _f:
                _f.write(b"a co-tenant's object, hex-named by coincidence")
            os.utime(_pth, (_old, _old))
            _planted.append((_ext, _pth))
        _wet3 = storage.sweep_orphans(store, db.session,
                                      older_than_seconds=0, dry_run=False)
        _eaten = [e for e, pth in _planted if not os.path.exists(pth)]
        check("a hex-named co-tenant object with a non-Skribl extension survives",
              not _eaten,
              f"deleted {_eaten} — KEY_RE admits any 2-4 char extension, but "
              f"Skribl only ever writes {sorted(storage._TYPE_FOR_EXT)}")
        for _e, _pth in _planted:
            if os.path.exists(_pth):
                os.remove(_pth)

    # --- OUTSIDE REVIEW v223 #1: reuse of an OLD orphan ---------------------
    # The sweep's grace period assumes age separates "abandoned" from "not
    # finished yet". Content addressing breaks that: put_bytes() returns early
    # when the key already exists, so reusing a long-dead orphan does not make
    # it young again. A sweep running while the new association is still
    # uncommitted sees an old, unreferenced object and deletes bytes that a
    # committing post is about to point at — a successful post whose media 404s.
    #
    # Reproduced without threads: the association row is written in a session
    # that has NOT committed, and the sweep runs on a different connection, so
    # it cannot see the row. That is exactly the visibility the race has.
    _raw = b"bytes that already existed as an orphan " + os.urandom(16)
    _key = store.key_for(_raw, "image/png")
    store.put_bytes(_raw, "image/png", _key)
    if _root:
        _kp = store._paths(_key)[1]
        os.utime(_kp, (_old, _old))          # a long-dead orphan
        check("the reused object starts out older than any grace period",
              time.time() - os.path.getmtime(_kp) > 86400,
              "the setup did not age the object, so this proves nothing")

        store.put_bytes(_raw, "image/png", _key)     # the new post re-uploads it

        _swept = storage.sweep_orphans(store, db.session,
                                       older_than_seconds=86400, dry_run=False)
        check("an object a new post is re-using is not swept out from under it",
              os.path.exists(_kp),
              f"deleted {_key[:12]}… — put_bytes() returned early on the existing "
              f"object and left its age untouched, so the grace period never "
              f"applied to the reuse")
        if os.path.exists(_kp):
            os.remove(_kp)

    # --- BLAST RADIUS -----------------------------------------------------
    # The cascade above is only enforced on SQLite because Skribl installs a
    # PRAGMA listener. That listener used to be attached to SQLAlchemy's Engine
    # CLASS, so mounting this blueprint changed foreign-key behaviour for every
    # SQLite connection in the host's process — databases Skribl has never heard
    # of. It is scoped to Skribl's own engine now, and that is the kind of thing
    # that comes back silently, so it is asserted rather than remembered.
    from sqlalchemy import create_engine, text as _text          # noqa: E402
    import skribl.models as _m                                   # noqa: E402

    _dialect = db.session.get_bind().dialect.name
    if _dialect == "sqlite":
        _on = db.session.execute(_text("PRAGMA foreign_keys")).scalar()
        check("Skribl's own engine enforces foreign keys", _on == 1,
              f"PRAGMA foreign_keys={_on} — the cascade above would not hold")

        _host_db = os.path.join(tempfile.mkdtemp(prefix="skribl-hostdb-"), "host.db")
        _host_engine = create_engine("sqlite:///" + _host_db)
        with _host_engine.connect() as _c:
            _off = _c.execute(_text("PRAGMA foreign_keys")).scalar()
        check("an unrelated engine in the same process is NOT touched", _off == 0,
              f"PRAGMA foreign_keys={_off} on a database Skribl was never given "
              "— a blueprint must not reach past its own seam")
        _host_engine.dispose()
    else:
        check(f"no pragma listener is installed on {_dialect}",
              not _m._FK_ENGINES or all(
                  e.dialect.name != "sqlite" for e in _m._FK_ENGINES),
              "the SQLite pragma path should be inert on other engines")
        check("the cascade is enforced by the engine itself here", True,
              f"{_dialect} enforces foreign keys natively")

    check("the opt-out is readable without mounting anything",
          _m._fk_opted_out() is (os.environ.get(
              "SKRIBL_SQLITE_FOREIGN_KEYS", "1") == "0"),
          "SKRIBL_SQLITE_FOREIGN_KEYS=0 is the documented escape hatch")

bad = [r for r in results if not r[0]]
print(f"\n{'='*62}\n{len(results)-len(bad)}/{len(results)} passed"
      + ("" if not bad else "  FAILURES: " + ", ".join(r[1] for r in bad)))
sys.exit(1 if bad else 0)
