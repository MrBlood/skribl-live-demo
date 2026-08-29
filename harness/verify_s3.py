"""Does the S3 backend actually speak S3 — and does it keep private media private?

`skribl/storage.py` carried an S3 "subclass hook" for eight versions: a docstring
saying `put_bytes` and `url_for_key` were all a real object store needed. That
was true and it was not an implementation, and FUTURE.md names implementing it
as the single highest-leverage piece of work left, because payloads are ~476 KB
inline in Postgres and that is the ceiling on layers, on longer animations, and
on more than a handful of users.

THE FAKE BUCKET VERIFIES THE SIGNATURE. A double that accepts any request tests
nothing about SigV4 — the code could send no Authorization header at all and
pass. This one recomputes the signature from the canonical request and returns
403 when it does not match, so a broken signing chain fails here rather than in
production against a real bucket. It is deliberately strict about the two things
that are easy to get subtly wrong and impossible to notice locally: the payload
hash must equal the body actually sent, and the signed headers must be the ones
actually present.

WHAT IS NOT TESTED HERE: Amazon. This proves the requests are well-formed and
correctly signed, not that S3 accepts them — nothing in this sandbox can reach
a real bucket. That gap is real and is recorded in START-HERE rather than
papered over. MinIO or a bucket with a test prefix closes it in about a minute.

THE SECURITY ASSERTION IS THE ONE THAT MATTERS MOST. The obvious S3 design puts
the bucket URL in the payload, and `routes.media` used to say an S3 deployment
"never routes through here" — which would route around the authorisation that
route exists for. Externalising media had already made a PRIVATE Skribl's audio
retrievable by anyone holding the URL once; a second backend doing it again
would be the same bug with a different name. So this posts a private Skribl with
media, and requires a stranger to be refused.
"""
import base64
import hashlib
import hmac
import email.utils
from urllib.parse import unquote
import json
import os
import pathlib
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
import xml.sax.saxutils as _sx
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from skribl.storage import S3Store, sweep_orphans  # noqa: E402

APP_PORT = 5036
S3_PORT = 5037
BASE = f"http://127.0.0.1:{APP_PORT}"
AK, SK, REGION, BUCKET = "AKIAHARNESS", "harness-secret-key", "eu-west-2", "skribl-test"

results = []


def check(name, ok, detail=""):
    results.append((bool(ok), name))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  — {detail}" if detail else ""))


# --------------------------------------------------------------------------
# A bucket that checks its own auth.
# --------------------------------------------------------------------------
OBJECTS = {}           # key -> (bytes, content_type, mtime)
SEEN = []              # (method, path, signed_headers) for assertions below
LOCK = threading.Lock()


def _signing_key(datestamp):
    k = hmac.new(("AWS4" + SK).encode(), datestamp.encode(), hashlib.sha256).digest()
    k = hmac.new(k, REGION.encode(), hashlib.sha256).digest()
    k = hmac.new(k, b"s3", hashlib.sha256).digest()
    return hmac.new(k, b"aws4_request", hashlib.sha256).digest()


class Bucket(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):
        pass

    def _authorise(self, body):
        auth = self.headers.get("Authorization") or ""
        if not auth.startswith("AWS4-HMAC-SHA256 "):
            return "no SigV4 Authorization header"
        try:
            parts = dict(p.strip().split("=", 1)
                         for p in auth[len("AWS4-HMAC-SHA256 "):].split(","))
            cred, signed_headers, signature = (parts["Credential"],
                                               parts["SignedHeaders"],
                                               parts["Signature"])
        except Exception as e:
            return f"unparseable Authorization: {e}"
        akid, datestamp, region, service, terminator = cred.split("/")
        if akid != AK or region != REGION or service != "s3" or terminator != "aws4_request":
            return f"wrong credential scope: {cred}"
        amzdate = self.headers.get("x-amz-date") or ""
        if not amzdate.startswith(datestamp):
            return f"x-amz-date {amzdate} outside scope {datestamp}"
        # The payload hash must describe the body that actually arrived.
        declared = self.headers.get("x-amz-content-sha256") or ""
        if declared != hashlib.sha256(body).hexdigest():
            return "x-amz-content-sha256 does not match the body sent"
        names = signed_headers.split(";")
        canonical_headers = ""
        for n in names:
            v = self.headers.get(n)
            if v is None:
                return f"signed header {n!r} was not sent"
            canonical_headers += f"{n}:{v.strip()}\n"
        path, _, query = self.path.partition("?")
        canonical = "\n".join([self.command, path, query, canonical_headers,
                               signed_headers, declared])
        scope = f"{datestamp}/{REGION}/s3/aws4_request"
        to_sign = "\n".join(["AWS4-HMAC-SHA256", amzdate, scope,
                             hashlib.sha256(canonical.encode()).hexdigest()])
        expect = hmac.new(_signing_key(datestamp), to_sign.encode(),
                          hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expect, signature):
            return "signature mismatch"
        with LOCK:
            SEEN.append((self.command, path, signed_headers))
        return None

    def _send(self, code, body=b"", ctype="application/xml", last_modified=None):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        # Real S3 returns Last-Modified on GET/HEAD, and storage.S3Store.stat_key
        # reads it to re-check an object's age immediately before the sweeper
        # deletes it. Without this header stat_key reads every object as NEW —
        # the safe direction, but it would mean an S3 sweep silently stops
        # collecting anything, so the double has to serve it.
        if last_modified is not None:
            self.send_header("Last-Modified",
                             email.utils.formatdate(last_modified, usegmt=True))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _key(self):
        path = self.path.partition("?")[0]
        want = f"/{BUCKET}/"
        return path[len(want):] if path.startswith(want) else None

    def _handle(self):
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else b""
        bad = self._authorise(body)
        if bad:
            return self._send(403, f"<Error><Message>{_sx.escape(bad)}</Message></Error>".encode())
        path, _, query = self.path.partition("?")
        if self.command == "GET" and "list-type=2" in query:
            items = []
            for k, (raw, _ct, mtime) in sorted(OBJECTS.items()):
                stamp = time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime(mtime))
                items.append(f"<Contents><Key>{_sx.escape(k)}</Key>"
                             f"<LastModified>{stamp}</LastModified>"
                             f"<Size>{len(raw)}</Size></Contents>")
            xml = ('<?xml version="1.0" encoding="UTF-8"?>'
                   '<ListBucketResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/">'
                   "<IsTruncated>false</IsTruncated>" + "".join(items) +
                   "</ListBucketResult>")
            return self._send(200, xml.encode())
        key = self._key()
        if key is None:
            return self._send(404, b"<Error/>")
        if self.command in ("GET", "HEAD"):
            hit = OBJECTS.get(key)
            if not hit:
                return self._send(404, b"<Error><Code>NoSuchKey</Code></Error>")
            return self._send(200, hit[0], hit[1], last_modified=hit[2])
        if self.command == "PUT":
            # A COPY is a PUT carrying x-amz-copy-source. S3Store uses a
            # self-copy to REFRESH an object's LastModified when content
            # addressing means there are no new bytes to write — see
            # put_bytes and OUTSIDE REVIEW v223 #1. Without COPY here that
            # fix would be untestable, which is the only reason it was first
            # written as a full re-upload.
            src = self.headers.get("x-amz-copy-source")
            if src:
                # Keys in OBJECTS carry the prefix, exactly as _key() leaves
                # them, so strip the copy-source the same way _key() does.
                _src = unquote(src)
                _want = f"/{BUCKET}/"
                src_key = (_src[len(_want):] if _src.startswith(_want)
                           else _src.lstrip("/"))
                with LOCK:
                    hit = OBJECTS.get(src_key)
                    if not hit:
                        return self._send(404, b"<Error><Code>NoSuchKey</Code></Error>")
                    OBJECTS[src_key] = (hit[0], hit[1], time.time())
                return self._send(200, b"<CopyObjectResult/>")
            with LOCK:
                OBJECTS[key] = (body, self.headers.get("content-type") or "", time.time())
            return self._send(200)
        if self.command == "DELETE":
            with LOCK:
                OBJECTS.pop(key, None)
            return self._send(204)
        return self._send(405)

    do_GET = do_PUT = do_HEAD = do_DELETE = _handle


bucket = ThreadingHTTPServer(("127.0.0.1", S3_PORT), Bucket)
threading.Thread(target=bucket.serve_forever, daemon=True).start()

store = S3Store(BUCKET, lambda key: f"/media/{key}", region=REGION,
                endpoint=f"http://127.0.0.1:{S3_PORT}",
                access_key=AK, secret_key=SK, prefix="media/")

WAV = (b"RIFF" + (36 + 8).to_bytes(4, "little") + b"WAVEfmt " +
       (16).to_bytes(4, "little") + (1).to_bytes(2, "little") +
       (1).to_bytes(2, "little") + (8000).to_bytes(4, "little") +
       (16000).to_bytes(4, "little") + (2).to_bytes(2, "little") +
       (16).to_bytes(2, "little") + b"data" + (8).to_bytes(4, "little") + b"\0" * 8)
PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==")

print("\nS3 — the object store, against a bucket that checks the signature")
key = store.key_for(WAV, "audio/wav")
store.put_bytes(WAV, "audio/wav", key)
check("a signed PUT is accepted and stores the bytes",
      OBJECTS.get("media/" + key) and OBJECTS["media/" + key][0] == WAV,
      f"{len(OBJECTS)} object(s); a 403 here means the signing chain is wrong")
check("the object is stored under the configured prefix",
      "media/" + key in OBJECTS, f"keys: {list(OBJECTS)[:2]}")
got = store.read(key)
check("GET returns the bytes byte-for-byte", got and got[0] == WAV,
      f"{len(got[0]) if got else 0} B of {len(WAV)} B")
check("and the content type is DERIVED from the key, not the bucket's metadata",
      got and got[1] == "audio/wav",
      f"{got and got[1]} — a bucket's stored type can be set by anything that "
      f"ever had write access")
check("a missing key reads as None rather than raising",
      store.read("0" * 64 + ".wav") is None)

before = len(SEEN)
store.put_bytes(WAV, "audio/wav", key)
# CHANGED IN v224, and deliberately — flagged rather than quietly adjusted.
# This asserted "no PUT was issued", using the method as a proxy for "the bytes
# were not re-uploaded". A self-copy IS an HTTP PUT (x-amz-copy-source, empty
# body), so put_bytes refreshing an object's LastModified to close the sweep
# race in OUTSIDE REVIEW v223 #1 breaks the proxy while satisfying the intent
# exactly. The assertion now measures the intent: no request may carry the
# object's bytes. That is STRICTER than the old form — a body-carrying PUT
# fails it whatever the method — and it is why the S3 double learned COPY
# instead of this test learning to accept an upload.
_uploads = [s for s in SEEN[before:]
            if s[0] == "PUT" and "x-amz-copy-source" not in (s[2] or "")]
check("re-storing identical bytes uploads nothing",
      not _uploads,
      f"{[s[0] for s in SEEN[before:]]} — content addressing means a repost "
      f"costs a HEAD and at most a metadata copy, never an upload")
check("...and the repost still refreshes the object's age, or the sweep race returns",
      any(s[0] == "PUT" and "x-amz-copy-source" in (s[2] or "")
          for s in SEEN[before:]),
      f"{[s[0] for s in SEEN[before:]]} — an object reused by a new post must "
      f"stop looking old to sweep_orphans")

listed = dict(store.iter_keys())
check("LIST pages and strips the prefix back off",
      key in listed and all(not k.startswith("media/") for k in listed),
      f"{list(listed)[:2]} — sweep_orphans matches these against media_key")
check("LIST timestamps parse to a usable mtime",
      isinstance(listed.get(key), float) and listed[key] > time.time() - 3600,
      f"{listed.get(key)} — an unparseable stamp must read as NEW, or "
      f"sweep_orphans collects it")

store.delete_key(key)
check("DELETE removes the object", "media/" + key not in OBJECTS)
store.delete_key(key)
check("deleting a key that is already gone is not an error", True,
      "a sweep re-run must be safe")

# A wrong secret must be REFUSED — otherwise every assertion above is vacuous.
bad_store = S3Store(BUCKET, lambda k: k, region=REGION,
                    endpoint=f"http://127.0.0.1:{S3_PORT}",
                    access_key=AK, secret_key="wrong", prefix="media/")
refused = False
try:
    bad_store.put_bytes(WAV, "audio/wav", key)
except RuntimeError as e:
    refused = "403" in str(e)
check("NEGATIVE CONTROL: a bad secret is refused by the bucket", refused,
      "if this passes, the fake bucket is not checking anything and neither "
      "is this suite")

# --------------------------------------------------------------------------
# End to end through the app, which is where the security question lives.
# --------------------------------------------------------------------------
env = dict(os.environ,
           DATABASE_URL=f"sqlite:///{tempfile.mkdtemp()}/s3.db",
           SKRIBL_MEDIA_BACKEND="s3",
           SKRIBL_S3_BUCKET=BUCKET, SKRIBL_S3_REGION=REGION,
           SKRIBL_S3_ENDPOINT=f"http://127.0.0.1:{S3_PORT}",
           SKRIBL_S3_PREFIX="media/",
           AWS_ACCESS_KEY_ID=AK, AWS_SECRET_ACCESS_KEY=SK,
           SKRIBL_RATE_MAX_POSTS="100000", SKRIBL_RATE_MAX_ATTEMPTS="100000",
           # Cache assertions below pin the OPTED-IN behaviour; the default
           # (private, no-store) is pinned by verify_mediaauthz.py.
           SKRIBL_PUBLIC_MEDIA_CACHE="1",
           SECRET_KEY="harness-s3")
subprocess.run([sys.executable, "-c",
                "from app import app, db; app.app_context().push(); db.create_all()"],
               cwd=ROOT, env=env, check=True, capture_output=True)
proc = subprocess.Popen([sys.executable, "-m", "flask", "--app", "app", "run",
                         "--port", str(APP_PORT), "--no-reload"],
                        cwd=ROOT, env=env,
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
deadline = time.time() + 25
while time.time() < deadline:
    try:
        with socket.create_connection(("127.0.0.1", APP_PORT), 0.5):
            break
    except OSError:
        time.sleep(0.3)
else:
    proc.kill()
    sys.exit("SKIP: instance did not start.")


def post(payload):
    req = urllib.request.Request(BASE + "/api/skribls", method="POST",
                                 data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


def get(path):
    try:
        with urllib.request.urlopen(BASE + path, timeout=20) as r:
            return r.status, r.read(), dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read() or b"", dict(e.headers or {})


def frame_payload(visibility="public"):
    # Media is {"data": ...}, not a bare string — see _iter_media_items. A bare
    # string is not media as far as validation is concerned, so it is never
    # externalised, and a fixture that uses one proves nothing about storage.
    return {"title": f"s3 {visibility}", "schemaVersion": 2,
            "visibility": visibility,
            "frames": [{"strokes": [{"x": 5, "y": 5, "color": "#fff", "size": 4,
                                     "t": 0, "erase": False, "start": True}],
                        "strokeGroups": [1], "baseSnapshot": None,
                        "background": {"color": "#101418"},
                        "music": {"data": "data:audio/wav;base64," + base64.b64encode(WAV).decode()},
                        "photo": {"data": "data:image/png;base64," + base64.b64encode(PNG).decode(),
                                  "fit": "cover", "opacity": 1}}]}


try:
    print("\nS3 — a post through the app, and what the payload carries")
    status, body = post(frame_payload())
    check("a post with media is accepted", status == 201, f"{status} {body}")
    pid = body.get("id")
    status, raw, _h = get(f"/api/skribls/{pid}")
    doc = json.loads(raw or b"{}")
    blob = json.dumps(doc)
    urls = sorted(set(__import__("re").findall(r"/media/[0-9a-f]{64}\.[a-z0-9]{2,4}", blob)))
    check("the payload carries no inline media at all",
          "data:audio" not in blob and "data:image" not in blob,
          "externalising means the bytes left payload_json")
    check("it carries APP urls, not bucket urls",
          len(urls) == 2 and "amazonaws" not in blob and str(S3_PORT) not in blob,
          f"{urls} — a bucket URL cannot ask who is looking")
    check("and both objects are in the bucket under the prefix",
          all("media/" + u.rsplit("/", 1)[-1] in OBJECTS for u in urls),
          f"{sorted(OBJECTS)[:2]}")
    if urls:
        status, served, headers = get(urls[0])
        key0 = urls[0].rsplit("/", 1)[-1]
        check("the media serves through the app, out of the bucket",
              status == 200 and served == OBJECTS["media/" + key0][0],
              f"{status}, {len(served)} B, {headers.get('Content-Type')}")
        check("a public post's media is cached immutably",
              "immutable" in (headers.get("Cache-Control") or ""),
              headers.get("Cache-Control"))
        check("and is never sniffable",
              headers.get("X-Content-Type-Options") == "nosniff")
    status, _b, _h = get("/media/" + "0" * 64 + ".wav")
    check("a well-formed key nothing references is 404, not a bucket miss",
          status == 404, str(status))

    # ------------------------------------------------------------------
    # THE ASSERTION THIS SUITE EXISTS FOR.
    #
    # The standalone app is unauthenticated, so it REFUSES to create a private
    # post — there would be no owner. Private media therefore has to be reached
    # the way verify_privacy.py reaches it: throwaway in-process apps sharing
    # one database, each with a different current_user_id. Without this, the S3
    # backend's authorisation is untested, and the obvious S3 design (bucket
    # URLs in the payload) would pass every other assertion in this file while
    # serving a private Skribl's audio to anyone holding the link.
    # ------------------------------------------------------------------
    print("\nS3 — who may read a private post's media")
    from flask import Flask, url_for
    from flask_sqlalchemy import SQLAlchemy
    import skribl
    import skribl.models

    _url = f"sqlite:///{tempfile.mkdtemp()}/s3priv.db"

    def _app_as(viewer):
        a = Flask(__name__)
        a.config["SQLALCHEMY_DATABASE_URI"] = _url
        a.config["SECRET_KEY"] = "harness-s3-priv"
        d = SQLAlchemy()
        d.init_app(a)
        skribl.init_skribl(
            a, session=lambda: d.session, current_user_id=(lambda: viewer),
            # v224: identity here is a closure over a local variable, not a
            # cookie, so this fixture is not CSRF-able. csrf=False is how a host
            # declares that, and the fail-closed rule (outside review #4)
            # requires it to be said rather than assumed.
            csrf=False,
            media_store=S3Store(BUCKET, lambda key: url_for("skribl.media", key=key),
                                region=REGION, endpoint=f"http://127.0.0.1:{S3_PORT}",
                                access_key=AK, secret_key=SK, prefix="media/"))
        skribl.models.attach_to_metadata(d.metadata)

        # HOST-OWNED COMMIT, per the transaction contract. This fixture never
        # wired one and still worked — because pysqlite's fake savepoints were
        # committing at RELEASE. With real transactions (v202 BEGIN recipe)
        # the flushed post vanished at request teardown and every downstream
        # check went vacuous. The fixture now commits like a real host.
        @a.after_request
        def _commit(resp):
            if resp.status_code < 500:
                d.session.commit()
            return resp

        @a.teardown_request
        def _rollback(exc):
            d.session.rollback()
        return a, d

    _author, _d = _app_as(1)
    with _author.app_context():
        _d.create_all()
    _r = _author.test_client().post("/api/skribls", json=frame_payload("private"))
    check("user 1 creates a private post with media", _r.status_code == 201,
          str(_r.status_code) + " " + str(_r.get_json()))
    _doc = json.loads(json.dumps(_author.test_client().get(
        f"/api/skribls/{(_r.get_json() or {}).get('id')}").get_json() or {}))
    _priv_urls = sorted(set(__import__("re").findall(
        r"/media/[0-9a-f]{64}\.[a-z0-9]{2,4}", json.dumps(_doc))))
    check("FIXTURE GATE: the private post's media was externalised",
          len(_priv_urls) == 2,
          f"{_priv_urls} — with nothing externalised the checks below are vacuous")
    if _priv_urls:
        _owner = _author.test_client().get(_priv_urls[0])
        check("its owner can read it", _owner.status_code == 200,
              str(_owner.status_code))
        check("and it is never cached by a shared cache",
              "no-store" in (_owner.headers.get("Cache-Control") or ""),
              _owner.headers.get("Cache-Control"))
        for _viewer, _label in ((999, "a different user"), (None, "an anonymous viewer")):
            _a, _ = _app_as(_viewer)
            _resp = _a.test_client().get(_priv_urls[0])
            check(f"{_label} is refused the private post's media",
                  _resp.status_code == 404,
                  f"{_resp.status_code} — content addressing makes bytes "
                  f"immutable, not public; a bucket URL would have served these")
finally:
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except Exception:
        proc.kill()
    bucket.shutdown()

bad = [n for ok, n in results if not ok]
print("\n" + "=" * 62)
print(f"{len(results) - len(bad)}/{len(results)} passed"
      + (f"  FAILURES: {', '.join(bad)}" if bad else ""))
sys.exit(1 if bad else 0)
