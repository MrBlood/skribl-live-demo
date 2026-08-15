"""Media storage: base64 in the database, or blobs behind a URL.

v131 keeps audio and images as base64 data URLs inside `payload_json`. A single
post runs to megabytes, base64 costs 33% over the raw bytes in the database and
in every backup, and the database ends up doing a blob store's job badly.

This suite boots its own instance with SKRIBL_MEDIA_BACKEND=local and proves the
externalised path end to end, then proves the DEFAULT instance is untouched —
because the default is deliberately still inline. A storage change to a system
holding real posts has to be opted into, and the assertion that it has NOT
silently changed is as important as the assertion that it works.

What matters here:
  * A posted data URL is replaced by a URL, and the payload stops carrying the
    bytes.
  * The stored blob comes back byte-identical, with the content type it was
    stored with — never sniffed from the filename.
  * Keys are content-addressed, so the same media posted twice is stored once.
  * A key cannot be used to read anything outside the store. This is the one
    assertion where a failure is a filesystem read primitive, not a bug.
  * Existing inline posts keep working, because a real deployment will hold both.
"""
import base64
import hashlib
import json
import os
import socket
import pathlib
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PORT = 5010
BASE = f"http://127.0.0.1:{PORT}"
API = BASE + "/api/skribls"

results = []
def check(name, ok, detail=""):
    results.append((ok, name)); print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  — {detail}" if detail else ""))


# A minimal, real WAV: the server signature-checks media, so random bytes are
# rejected before they could ever reach the store.
def wav_bytes(n_samples=800):
    data = b"\x00\x00" * n_samples
    hdr = (b"RIFF" + (36 + len(data)).to_bytes(4, "little") + b"WAVEfmt " +
           (16).to_bytes(4, "little") + (1).to_bytes(2, "little") +
           (1).to_bytes(2, "little") + (44100).to_bytes(4, "little") +
           (88200).to_bytes(4, "little") + (2).to_bytes(2, "little") +
           (16).to_bytes(2, "little") + b"data" + len(data).to_bytes(4, "little"))
    return hdr + data


WAV = wav_bytes()
WAV_URL = "data:audio/wav;base64," + base64.b64encode(WAV).decode()

MEDIA_ROOT = tempfile.mkdtemp()
tmp = tempfile.mkdtemp()
env = dict(os.environ,
           SKRIBL_MEDIA_BACKEND="local",
           SKRIBL_MEDIA_ROOT=MEDIA_ROOT,
           DATABASE_URL=f"sqlite:///{tmp}/media.db",
           SKRIBL_RATE_MAX_POSTS="100000",
           SKRIBL_RATE_MAX_ATTEMPTS="100000",
           # This suite pins the OPTED-IN cache behaviour; the default
           # (private, no-store) is pinned by verify_mediaauthz.py.
           SKRIBL_PUBLIC_MEDIA_CACHE="1",
           SECRET_KEY="harness-storage-suite")
subprocess.run([sys.executable, "-c",
                "from app import app, db; app.app_context().push(); db.create_all()"],
               cwd=ROOT, env=env, check=True, capture_output=True)
proc = subprocess.Popen([sys.executable, "-m", "flask", "--app", "app", "run",
                         "--port", str(PORT), "--no-reload"],
                        cwd=ROOT, env=env,
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
deadline = time.time() + 25
while time.time() < deadline:
    try:
        with socket.create_connection(("127.0.0.1", PORT), 0.5):
            break
    except OSError:
        time.sleep(0.3)
else:
    proc.kill()
    sys.exit(f"SKIP: media instance did not start on port {PORT}.")


def post(payload):
    req = urllib.request.Request(API, method="POST",
                                 data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


def fetch(path):
    try:
        with urllib.request.urlopen(BASE + path, timeout=20) as r:
            return r.status, r.read(), dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read(), dict(e.headers or {})


try:
    frame = {"strokes": [], "strokeGroups": [], "background": {"color": "#101418"},
             "music": {"data": WAV_URL, "loop": True}}

    print("\nSTORAGE — a posted data URL is externalised")
    st, created = post({"title": "media probe", "visibility": "public",
                        "frames": [frame]})
    check("the post succeeds with media", st == 201, str(st))
    sid = created.get("id")

    st, body, _ = fetch(f"/api/skribls/{sid}")
    check("the post reads back", st == 200, str(st))
    doc = json.loads(body)
    music = ((doc.get("skribl") or {}).get("frames") or [{}])[0].get("music") or {}
    stored_url = music.get("data")
    check("the payload no longer carries a data URL",
          isinstance(stored_url, str) and not stored_url.startswith("data:"),
          (stored_url or "")[:40])
    check("it carries a URL into the media store",
          isinstance(stored_url, str) and "/media/" in stored_url,
          str(stored_url)[:60])
    # The whole point: the row got small.
    check("the payload is now far smaller than the media it references",
          len(body) < len(WAV), f"payload {len(body)}B vs media {len(WAV)}B")

    print("\nSTORAGE — the blob comes back intact")
    st, blob, headers = fetch(stored_url)
    check("the media URL serves 200", st == 200, str(st))
    check("the bytes are IDENTICAL to what was posted", blob == WAV,
          f"{len(blob)}B vs {len(WAV)}B")
    check("served with the content type it was stored with",
          headers.get("Content-Type", "").startswith("audio/wav"),
          headers.get("Content-Type", ""))
    check("served with nosniff", headers.get("X-Content-Type-Options") == "nosniff")
    # Immutable PUBLIC caching only when every referencing post is public AND
    # the deployment opted in (SKRIBL_PUBLIC_MEDIA_CACHE, set above). Content
    # addressing makes the bytes unchanging; it does not make them public,
    # visibility is revocable, and a shared cache does not re-check
    # authorisation — hence the opt-in. Default behaviour is pinned in
    # verify_mediaauthz.py.
    check("public media is cached immutably (behind the opt-in)",
          "immutable" in headers.get("Cache-Control", ""),
          headers.get("Cache-Control", ""))

    print("\nSTORAGE — keys are content-addressed")
    digest = hashlib.sha256(WAV).hexdigest()
    check("the key is the SHA-256 of the content", digest in stored_url,
          stored_url[-24:])
    st2, created2 = post({"title": "same media again", "visibility": "public",
                          "frames": [frame]})
    st, body2, _ = fetch(f"/api/skribls/{created2['id']}")
    url2 = ((json.loads(body2).get("skribl") or {}).get("frames") or [{}])[0].get("music", {}).get("data")
    check("the same media posted twice yields the SAME url", url2 == stored_url,
          f"{url2} vs {stored_url}")
    on_disk = sum(1 for _, _, files in os.walk(MEDIA_ROOT)
                  for f in files if not f.endswith(".type"))
    check("and is stored ONCE on disk, not twice", on_disk == 1, f"{on_disk} files")

    print("\nSTORAGE — a key cannot escape the store")
    for bad, label in [("../../../../etc/passwd", "path traversal"),
                       ("..%2f..%2fetc%2fpasswd", "encoded traversal"),
                       ("a" * 64 + ".wav", "well-formed but absent key"),
                       ("not-a-key", "malformed key"),
                       (digest, "digest with no extension")]:
        st, _, _ = fetch("/media/" + bad)
        check(f"{label} is refused", st == 404, str(st))

    print("\nSTORAGE — a media key cannot be claimed by an unrelated post")
    # THE FORGERY. Authorisation used to be
    # CAST(payload_json AS TEXT) LIKE '%<key>%', and the API deliberately
    # preserves unknown JSON fields — so anyone who learned a private object's
    # key could paste it into a field of their OWN post and be handed a
    # "reference" to it. Authorisation by string containment is not
    # authorisation. It is an exact association row now, and this proves a
    # post that merely MENTIONS a key gains nothing.
    st, victim = post({"title": "owner of the object", "visibility": "public",
                       "frames": [frame]})
    st, vbody, _ = fetch(f"/api/skribls/{victim['id']}")
    vurl = ((json.loads(vbody).get("skribl") or {})
            .get("frames") or [{}])[0].get("music", {}).get("data", "")
    vkey = vurl.rsplit("/", 1)[-1]
    check("the victim post owns a media key", bool(vkey), vkey[:20])

    # A post that names the key in an arbitrary field, with no media of its own.
    st, forger = post({"title": "forger", "visibility": "public",
                       "stolen_reference": vkey,
                       "notes": f"see /media/{vkey}",
                       "frames": [{"strokes": [], "strokeGroups": [],
                                   "background": {"color": "#101418"}}]})
    check("a post naming someone else's key is accepted (unknown fields are kept)",
          st == 201, str(st))
    st, fbody, _ = fetch(f"/api/skribls/{forger['id']}")
    check("and the key really is preserved in its payload",
          vkey in fbody.decode("utf-8", "replace"),
          "if this fails the test proves nothing — the string must survive")

    import sqlite3
    _con = sqlite3.connect(f"{tmp}/media.db")
    # Several earlier posts legitimately stored this same WAV — content
    # addressing means one object, many real owners — so what matters is not the
    # total but whether the FORGER is among them.
    _total = _con.execute("select count(*) from skribl_post_media where media_key=?",
                          (vkey,)).fetchone()[0]
    _forger_rows = _con.execute(
        "select count(*) from skribl_post_media m join skribl_posts p"
        " on p.id = m.post_id where m.media_key = ? and p.public_id = ?",
        (vkey, forger["id"])).fetchone()[0]
    check("the forger has NO association with the key it merely names",
          _forger_rows == 0,
          f"{_forger_rows} rows — naming a key must not grant a reference")
    check("the posts that genuinely stored the object still do",
          _total >= 1, f"{_total} legitimate association rows")

    print("\nSTORAGE — inline posts still work")
    # A deployment that switches backends keeps every post made before the
    # switch, so both forms must read back.
    st, legacy = post({"title": "no media", "frames": [
        {"strokes": [], "strokeGroups": [], "background": {"color": "#101418"}}]})
    check("a post with no media is unaffected", st == 201, str(st))
    st, body, _ = fetch(f"/api/skribls/{legacy['id']}")
    check("and reads back cleanly", st == 200, str(st))

    print("\nSTORAGE — the DEFAULT deployment is still inline")
    # This is the assertion that stops the storage change arriving by surprise.
    shared = os.environ.get("SKRIBL_BASE", "http://127.0.0.1:5001")
    try:
        req = urllib.request.Request(shared + "/api/skribls", method="POST",
                                     data=json.dumps({"title": "inline default",
                                                      "frames": [frame]}).encode(),
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=20) as r:
            ref = json.loads(r.read())
        with urllib.request.urlopen(f"{shared}/api/skribls/{ref['id']}", timeout=20) as r:
            d = json.loads(r.read())
        inline = ((d.get("skribl") or {}).get("frames") or [{}])[0].get("music", {}).get("data", "")
        check("the default harness instance still stores media INLINE",
              inline.startswith("data:"),
              "default changed to external without being asked")
    except urllib.error.URLError as e:
        check("the default harness instance still stores media INLINE", False,
              f"could not reach the shared server: {e}")

finally:
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()

# ---- a crash between the two writes must not change how bytes are served ---
# put_bytes() renamed the body into place and THEN wrote a `.type` sidecar. A
# crash between those two steps left the media permanently present without its
# metadata, and permanently so: every later call starts with
# `if os.path.exists(path): return`, so nothing ever repairs the sidecar, and
# read() falls back to application/octet-stream. One crash silently changes how
# that object is served forever. Two writers of identical bytes could also race
# over the sidecar.
try:
    import sys as _sys, tempfile
    # This suite drives the store through a subprocess server, so the
    # package is not on the path here the way it is in verify_privacy.
    _sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
    from skribl.storage import LocalDiskStore

    _root = tempfile.mkdtemp(prefix="skribl-store-")
    _store = LocalDiskStore(_root, lambda k: "/media/" + k)
    _raw = b"RIFF....WAVEfmt data"
    _key = _store.key_for(_raw, "audio/wav")
    _store.put_bytes(_raw, "audio/wav", _key)

    got = _store.read(_key)
    check("a stored object reads back with its real content type",
          got is not None and got[1] == "audio/wav",
          f"got {got[1] if got else None!r}")

    # Simulate the crash: the body landed, the sidecar never did.
    for _p in pathlib.Path(_root).rglob("*.type"):
        _p.unlink()
    got = _store.read(_key)
    check("and still does when no sidecar is present",
          got is not None and got[1] == "audio/wav",
          f"got {got[1] if got else None!r} — a crash between the body and its "
          "metadata must not permanently change the served type")

    _store.put_bytes(_raw, "audio/wav", _key)
    got = _store.read(_key)
    check("re-storing identical bytes is still correct afterwards",
          got is not None and got[1] == "audio/wav",
          f"got {got[1] if got else None!r}")

    # Aliases normalise: the same bytes offered as audio/x-wav are the same
    # object and must be served identically, not as whichever alias arrived
    # first.
    _k2 = _store.key_for(_raw, "audio/x-wav")
    _store.put_bytes(_raw, "audio/x-wav", _k2)
    got2 = _store.read(_k2)
    check("an aliased content type serves as the canonical one",
          got2 is not None and got2[1] == "audio/wav",
          f"got {got2[1] if got2 else None!r}")
except Exception as _e:      # noqa: BLE001
    check("the local store's crash behaviour is testable", False, repr(_e))

# ---- orphan media -----------------------------------------------------------
# Objects are written BEFORE the transaction recording the association commits,
# so a failed or abandoned commit leaves bytes nothing points at. Content
# addressing means that never corrupts valid data, but it accumulates.
try:
    import time as _time
    from skribl.storage import sweep_orphans

    class _FakeQuery:
        # sweep_orphans checks references in CHUNKS now — one IN() query per
        # chunk instead of one all-keys set (bounded memory at scale) — so the
        # fake grows a filter() that narrows to the requested keys.
        def __init__(self, rows): self._rows = rows
        def filter(self, clause):
            wanted = set(clause.right.value)
            return _FakeQuery([r for r in self._rows if r[0] in wanted])
        def all(self): return self._rows

    class _FakeSession:
        def __init__(self, keys): self._keys = [(k,) for k in keys]
        def query(self, *_a, **_k): return _FakeQuery(self._keys)

    _root2 = tempfile.mkdtemp(prefix="skribl-sweep-")
    _s2 = LocalDiskStore(_root2, lambda k: "/media/" + k)
    _kept = _s2.key_for(b"kept-bytes", "image/png")
    _orph = _s2.key_for(b"orphan-bytes", "image/png")
    _s2.put_bytes(b"kept-bytes", "image/png", _kept)
    _s2.put_bytes(b"orphan-bytes", "image/png", _orph)

    # Nothing is old enough yet: an object written seconds ago may belong to a
    # transaction still in flight, and sweeping it would delete the media of a
    # post being created right now.
    fresh = sweep_orphans(_s2, _FakeSession([_kept]), older_than_seconds=3600)
    check("a recently written orphan is left alone",
          fresh == [],
          f"would have removed {fresh} — age is the only thing separating "
          "'orphan' from 'not committed yet'")

    old = sweep_orphans(_s2, _FakeSession([_kept]), older_than_seconds=0)
    check("an aged orphan is identified", old == [_orph], f"got {old}")
    check("and a referenced object never is", _kept not in old)

    check("dry run does not delete", _s2.read(_orph) is not None,
          "the default must not remove user data")

    done = sweep_orphans(_s2, _FakeSession([_kept]), older_than_seconds=0,
                         dry_run=False)
    check("with dry_run=False the orphan is gone",
          done == [_orph] and _s2.read(_orph) is None)
    check("and the referenced object survives", _s2.read(_kept) is not None,
          "a sweep that takes live media with it is worse than the leak")
except Exception as _e3:      # noqa: BLE001
    check("orphan sweeping is testable", False, repr(_e3))

bad = [r for r in results if not r[0]]
print(f"\n{'='*62}\n{len(results)-len(bad)}/{len(results)} passed" +
      ("" if not bad else "  FAILURES: " + ", ".join(r[1] for r in bad)))
