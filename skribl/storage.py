"""Where media actually lives.

v131 stores audio and images as base64 data URLs INSIDE `payload_json`. That is a
fine demo and a dead end for a platform:

  * A single post routinely runs to megabytes. A feed of fifty is a hundred
    megabytes of JSON, which is why the listing endpoint had to exclude payloads
    entirely rather than merely trim them.
  * Base64 costs 33% over the raw bytes, in the database, in every backup, and
    in every row that crosses the wire.
  * The database becomes a blob store, so it cannot be sized, cached, or served
    by a CDN like one.
  * It is why the Content-Security-Policy has to allow `connect-src data:`.

This module externalises those blobs behind a small interface, so the payload
carries a URL instead of a megabyte. Backends:

  inline  DEFAULT. Exactly v131 — the data URL stays in the payload and nothing
          is written anywhere. Chosen as the default deliberately: this is a
          storage change to a system holding real posts, and it must be opted
          into, not arrive by upgrade.
  local   Content-addressed files on disk, served by the blueprint. Right for a
          single-host deployment and for proving the path end to end.
  s3      An S3-compatible bucket (S3Store, at the foot of this file). Objects
          are served through the app's own /media/<key>, NOT as bucket URLs, so
          the visibility check on that route still applies — see the note above
          the class. A deployment that already runs boto3 can still subclass
          MediaStore and pass its own store in; that hook has not moved.

Keys are the SHA-256 of the CONTENT, so identical media is stored once no matter
how many posts carry it — the same photo reposted by fifty people costs one
file — and a stored object can be cached immutably forever, because a different
byte is a different key.
"""
import base64
import datetime
import hashlib
import hmac
import os
import re
import time
import urllib.error
import urllib.request
import uuid
import xml.etree.ElementTree as ET
from urllib.parse import quote, urlsplit

_DATA_URL_RE = re.compile(r"^data:([-\w.+]+/[-\w.+]+)?;base64,", re.IGNORECASE)

# Extension is cosmetic — content type is served from a sidecar, never sniffed
# from the name — but it makes the storage directory legible to a human.
_EXT = {
    "audio/wav": ".wav", "audio/x-wav": ".wav", "audio/wave": ".wav",
    "audio/mpeg": ".mp3", "audio/mp3": ".mp3", "audio/ogg": ".ogg",
    "audio/webm": ".weba", "audio/mp4": ".m4a", "audio/aac": ".aac",
    "image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp",
    "image/gif": ".gif",
}


#: The canonical type for each stored extension. Several MIME spellings map to
#: one extension (audio/wav, audio/x-wav and audio/wave are all .wav), so this
#: is deliberately not the inverse of _EXT: it names the ONE type each
#: extension is served as. Aliases therefore normalise, and the same bytes are
#: served identically whichever spelling the uploader happened to send.
_TYPE_FOR_EXT = {
    ".wav": "audio/wav", ".mp3": "audio/mpeg", ".ogg": "audio/ogg",
    ".weba": "audio/webm", ".m4a": "audio/mp4", ".aac": "audio/aac",
    ".png": "image/png", ".jpg": "image/jpeg", ".webp": "image/webp",
    ".gif": "image/gif",
}


def is_data_url(value):
    return isinstance(value, str) and bool(_DATA_URL_RE.match(value))


class MediaStore:
    """Interface. `externalise` is shared; backends implement two methods."""

    #: Set False by backends that leave the payload untouched.
    externalises = True

    def put_bytes(self, raw, content_type, key):        # pragma: no cover
        raise NotImplementedError

    def url_for_key(self, key):                          # pragma: no cover
        raise NotImplementedError

    def iter_keys(self):                                 # pragma: no cover
        """Every key this backend holds. Needed to find orphans.

        Not implemented here on purpose: an object store answers it with a
        paginated LIST, and pretending a generic implementation exists would
        invite one that loads a bucket into memory.
        """
        raise NotImplementedError

    def delete_key(self, key):                           # pragma: no cover
        raise NotImplementedError

    def key_for(self, raw, content_type):
        return hashlib.sha256(raw).hexdigest() + _EXT.get(content_type, ".bin")

    def put_data_url(self, data_url):
        """Store the blob a data URL carries; return (url, key).

        Returns the KEY as well as the URL. It used to return only the URL, and
        externalise_payload() recovered the key with url.rsplit("/", 1)[-1] —
        which works for "/media/<key>.wav" and breaks for anything real. An S3
        presigned URL is "https://bucket/path/<key>.wav?X-Amz-Signature=...",
        so the recovered "key" carried the entire query string: a 149-character
        association for a 68-character object, too long for String(80) on
        PostgreSQL, and not equal to the key it is supposed to authorise.

        An authorisation identifier must never be derived from its presentation
        URL. The store knows the key; it returns it.

        The data URL has ALREADY been validated by validation.py — decoded,
        signature-checked, size-capped — before it reaches here. This does not
        re-validate, and must never be called on unvalidated input.
        """
        header, _, b64 = data_url.partition(",")
        content_type = (header[5:].split(";")[0] or "application/octet-stream")
        raw = base64.b64decode(b64, validate=False)
        key = self.key_for(raw, content_type)
        self.put_bytes(raw, content_type, key)
        return self.url_for_key(key), key


class InlineStore(MediaStore):
    """v131: leave the data URL exactly where it is."""

    externalises = False

    def put_data_url(self, data_url):
        return data_url, None


class LocalDiskStore(MediaStore):
    """Content-addressed files under a directory, served by the blueprint.

    Content type is DERIVED from the key's extension (see _TYPE_FOR_EXT and
    the note in put_bytes) rather than stored beside the object. It used to
    be written to a `.type` sidecar rather than guessed from the
    extension when serving. Sniffing a stored file's type is how an uploaded
    image ends up served as text/html.
    """

    def __init__(self, root, url_builder):
        self.root = root
        self._url_builder = url_builder
        os.makedirs(self.root, exist_ok=True)

    def _paths(self, key):
        # Two-level fan-out: tens of thousands of files in one directory is slow
        # to list and unpleasant on some filesystems.
        sub = os.path.join(self.root, key[:2], key[2:4])
        return sub, os.path.join(sub, key), os.path.join(sub, key + ".type")

    def put_bytes(self, raw, content_type, key):
        sub, path, type_path = self._paths(key)
        if os.path.exists(path):
            return                      # content-addressed: already identical
        os.makedirs(sub, exist_ok=True)
        # Write to a temp name and rename, so a crash mid-write cannot leave a
        # truncated file sitting at a key that claims to be complete.
        # Unique per writer. Every writer previously used the same "<key>.part",
        # so concurrent POSTs of the same object raced: one process renamed the
        # shared temp file out from under the others and they died in
        # os.replace() with FileNotFoundError. Measured at 17 failures in 20
        # simultaneous writes. Content addressing means the bytes are identical,
        # so the race was pure collateral damage — a 500 for a request that had
        # done nothing wrong.
        tmp = f"{path}.{os.getpid()}.{uuid.uuid4().hex}.part"
        with open(tmp, "wb") as fh:
            fh.write(raw)
        os.replace(tmp, path)
        # NO sidecar. The content type used to be written to `<key>.type` after
        # this rename, which made the object and its metadata two writes and
        # therefore not atomic together: a crash in between left the body
        # present without its type, permanently, because every later call
        # begins `if os.path.exists(path): return` and nothing ever repaired
        # it. read() then served application/octet-stream forever. Two writers
        # of identical bytes could also race over that second file.
        #
        # The type is now derived from the key's extension, which is not a
        # guess: key_for() builds the key from the VALIDATED content type, and
        # _KEY_RE rejects any key that is not a hex digest plus a known
        # extension before it can reach the filesystem. One file, one atomic
        # rename, nothing to repair.

    def url_for_key(self, key):
        return self._url_builder(key)

    def iter_keys(self):
        for sub, _dirs, files in os.walk(self.root):
            for name in files:
                if name.endswith(".part") or name.endswith(".type"):
                    continue        # a temp file mid-write, or an old sidecar
                yield name, os.path.getmtime(os.path.join(sub, name))

    def delete_key(self, key):
        _, path, type_path = self._paths(key)
        for target in (path, type_path):
            try:
                os.remove(target)
            except OSError:
                pass

    def read(self, key):
        """-> (bytes, content_type), or None. Key is validated by the caller."""
        _, path, _type_path = self._paths(key)
        if not os.path.isfile(path):
            return None
        # Derived, not read from a second file. Any `.type` sidecar left by an
        # older build is simply ignored — no migration, and no object can be
        # left half-described by a crash.
        ext = os.path.splitext(key)[1].lower()
        content_type = _TYPE_FOR_EXT.get(ext, "application/octet-stream")
        with open(path, "rb") as fh:
            return fh.read(), content_type


#: A stored key is exactly a hex digest plus a known extension. Anything else is
#: rejected before it can reach the filesystem — this is the path-traversal
#: guard, and it is an allowlist rather than a "../" blocklist on purpose.
KEY_RE = re.compile(r"^[0-9a-f]{64}\.[a-z0-9]{2,4}$")


def externalise_payload(payload, store, iter_media):
    """Replace every validated data URL in `payload` with a stored URL.

    Returns (payload, [stored_key, ...]). The payload is rebuilt rather than mutated in
    place, because it is a SQLAlchemy-tracked JSON column on the way in and
    mutating a nested dict there is how a stray flush writes something nobody
    asked for.
    """
    if not store.externalises:
        return payload, []

    mapping = {}
    keys = set()
    for value, _kind, _cap, _label in iter_media(payload):
        if is_data_url(value) and value not in mapping:
            url, key = store.put_data_url(value)
            mapping[value] = url
            if key:
                # A SET, not a list. Deduplication was by the ORIGINAL DATA-URL
                # STRING, so two spellings of identical bytes — audio/wav and
                # audio/x-wav are both accepted by validation — produced two
                # entries mapping to ONE content key. The caller then inserted
                # that key twice against a unique index, the IntegrityError was
                # mistaken for a public_id collision, and the request retried
                # five times before failing with "Could not allocate a unique
                # id" — a misleading 503 for a post whose id was never the
                # problem.
                keys.add(key)
    if not mapping:
        return payload, []

    def walk(node):
        if isinstance(node, dict):
            return {k: walk(v) for k, v in node.items()}
        if isinstance(node, list):
            return [walk(v) for v in node]
        return mapping.get(node, node) if isinstance(node, str) else node

    # Return the KEYS the store reported — never parsed back out of a URL.
    return walk(payload), sorted(keys)



# Module level, not inside the function: models does not import storage, so
# there is no cycle, and verify_seam.py's name resolution cannot see imports
# hidden inside a function body — which is exactly what it is there to catch.
from .models import SkriblPost, SkriblPostMedia  # noqa: E402

def backfill_media(store, session, iter_media, batch=100, after_id=0,
                   limit=None, dry_run=True):
    """Move media out of payloads that were written while the store was inline.

    Returns a dict: see the keys at the bottom of this function.

    WHY THIS EXISTS. Flipping the default only changes what NEW posts do.
    Everything already in the table keeps its base64 in `payload_json` forever,
    which is the row size the change was made to fix. A mixed table is correct
    and supported — `verify_storage.py` asserts inline posts keep working — but
    "supported" is not "reclaimed", and without this the saving applies only to
    posts nobody has made yet.

    WHY dry_run DEFAULTS TO TRUE, and what a dry run must NOT do. This rewrites
    rows holding real user media, so the caller says `dry_run=False`
    deliberately — the same rule `sweep_orphans` follows. Note that a dry run
    also must not call `put_data_url`: that writes bytes. It counts what WOULD
    move by walking the same media slots, so a rehearsal on a large table costs
    nothing but reads. A "dry run" that fills a disk is not one.

    IDEMPOTENT AND RESUMABLE, because it will be interrupted. It commits per
    batch and reports the last id it finished, so a run that dies at post 40,000
    resumes with `after_id=` instead of starting over.

    What makes resume safe is that THE PAYLOAD IS THE PROGRESS MARKER, and it
    moves in the same transaction as the association rows it justifies. A batch
    that dies rolls back both, so the post is found still inline next time and
    converted exactly once; a batch that committed leaves no data URL for
    `externalise_payload` to replace, so a second pass skips it. There is no
    separate bookkeeping to get out of step with the data.

    NOT SAFE TO RUN TWICE AT ONCE. Two concurrent backfills over the same range
    both read a post as inline and both insert its associations; one commits and
    the other aborts its batch on the unique index. Nothing is corrupted — the
    objects are content-addressed and the loser rolls back — but the run dies
    partway for no useful reason. Run one.

    THE ORDERING HAZARD IS THE SAME ONE THE POST PATH HAS, and it is not fixed
    here. Objects are written to the store BEFORE the transaction recording
    their associations commits, so an interrupted batch can leave bytes nothing
    points at. That is exactly what `sweep_orphans` reconciles, and it is why
    that function has a grace period — do not run a sweep with a short
    `older_than_seconds` while a backfill is in flight, or it will delete media
    belonging to a batch that has not committed yet.

    DOES NOT TOUCH ANYTHING ELSE. No visibility, no timestamps, no ids. The only
    column written is `payload_json`, and the only rows added are associations.
    """
    if not store.externalises:
        # An inline store would report every post as convertible and convert
        # none of them, because externalise_payload returns the payload
        # untouched. Refuse rather than return a reassuring zero.
        raise ValueError(
            "backfill_media needs an externalising store; the configured one "
            f"({type(store).__name__}) leaves payloads alone. Set "
            "SKRIBL_MEDIA_BACKEND before running this.")

    scanned = converted = 0
    inline_bytes = 0
    keys_written = set()
    last_id = after_id

    while True:
        rows = (session().query(SkriblPost)
                .filter(SkriblPost.id > last_id)
                .order_by(SkriblPost.id)
                .limit(batch).all())
        if not rows:
            break

        for post in rows:
            scanned += 1
            last_id = post.id
            payload = post.payload_json or {}

            pending = [v for v, _k, _c, _l in iter_media(payload)
                       if is_data_url(v)]
            if not pending:
                continue
            converted += 1
            # Size the SAVING from the data URLs themselves, before anything is
            # written, so the number is the same on a dry run and a real one.
            inline_bytes += sum(len(v) for v in set(pending))

            if dry_run:
                continue

            stored_payload, media_keys = externalise_payload(
                payload, store, iter_media)
            post.payload_json = stored_payload
            # Inserted unconditionally. The first version checked for an
            # existing association first, to survive "a previous batch wrote
            # rows and then died" — and that state cannot occur: the payload
            # rewrite and its association rows commit in ONE transaction, so a
            # batch that dies rolls back both and the post is found still
            # inline on resume. The check was therefore an unreachable branch
            # that no assertion could cover, which mutation testing showed by
            # deleting it and changing nothing.
            #
            # It also did not protect the one case that CAN produce a duplicate
            # — two backfills running at once — because a read-then-insert is
            # a race, not a guard. That case is unsupported and stated in the
            # docstring rather than half-defended here.
            for key in media_keys:
                keys_written.add(key)
                session().add(SkriblPostMedia(post_id=post.id, media_key=key))

        if not dry_run:
            session().commit()

        if limit is not None and scanned >= limit:
            break

    return {
        "scanned": scanned,            # posts examined
        "converted": converted,        # posts that had (or have) inline media
        "inline_bytes": inline_bytes,  # base64 bytes that left, or would
        "keys": sorted(keys_written),  # objects written this run
        "last_id": last_id,            # resume with after_id=this
        "dry_run": dry_run,
    }


def sweep_orphans(store, session, older_than_seconds=86400, dry_run=True):
    """Delete stored objects that no post references. Returns the keys.

    WHY THIS IS NEEDED. Media is written BEFORE the transaction that records
    the association commits. The association rows are transactional; the object
    store is not. A failed or abandoned commit therefore leaves bytes nothing
    points at. Content addressing means this never corrupts valid data — an
    orphan is simply unreachable — but at scale, failed jobs and abandoned
    posts accumulate storage indefinitely.

    WHY A GRACE PERIOD, and why it defaults to a day. An object written
    seconds ago may belong to a transaction that has not committed yet.
    Sweeping on the association table alone would delete the media of a post
    being created concurrently. Age is the only thing that distinguishes
    "orphan" from "not finished yet", so anything younger than
    `older_than_seconds` is left alone regardless.

    WHY dry_run DEFAULTS TO TRUE. This deletes user data. A maintenance job
    that removes things by default is one typo away from removing the wrong
    things; the caller says `dry_run=False` deliberately.

    Do NOT try to make the object store and the database one distributed
    transaction. Objects are immutable, associations are authoritative, and a
    periodic sweep is the honest reconciliation.
    """
    referenced = {row[0] for row in session.query(SkriblPostMedia.media_key).all()}
    cutoff = time.time() - max(0, older_than_seconds)
    removed = []
    for key, mtime in store.iter_keys():
        if key in referenced or mtime > cutoff:
            continue
        removed.append(key)
        if not dry_run:
            store.delete_key(key)
    return removed


# --- S3 -----------------------------------------------------------------------
#
# WHY THIS IS NOT boto3. requirements.txt is hash-locked in constraints.txt for
# one cp312 environment, and adding a dependency the size of botocore to a
# deployment in order to issue four HTTP verbs is a bad trade — especially when
# the four are PUT, GET, DELETE and LIST against a single bucket. SigV4 is about
# sixty lines and is specified precisely; it is below. A deployment that already
# runs boto3 for other reasons can subclass MediaStore instead and pass its own
# store in — that hook has not moved.
#
# WHY OBJECTS ARE SERVED THROUGH THE APP, and this is the important part.
# The obvious S3 design hands the bucket URL out in the payload, and the
# docstring on `routes.media` used to say exactly that: "an S3-backed deployment
# hands out bucket URLs and never routes through here." That would route around
# the authorisation on that route — the one added because externalising media
# had made a PRIVATE Skribl's audio and images retrievable by anyone holding the
# URL. Re-introducing that with a different backend is the same bug wearing a
# different hat.
#
# So `url_for_key` returns the app's own /media/<key> URL, exactly as the local
# store does, and the route authorises against the post that owns the object
# before reading it. The cost is that bytes cross the app rather than going
# straight from the bucket. The answer to that is a CDN in front of /media/<key>
# — the response is already `immutable` and cached for a year when every
# referencing post is public, and `private, no-store` when one is not, which is
# the distinction a bucket URL cannot make.
#
# PRESIGNED URLS ARE NOT AN ALTERNATIVE HERE. The URL is written into
# payload_json and lives as long as the post; a presigned URL expires. A post
# whose media 403s a week later is worse than one that costs a little egress.
class S3Store(MediaStore):
    """Content-addressed objects in an S3-compatible bucket.

    Path-style addressing (`<endpoint>/<bucket>/<key>`), because it is what
    MinIO, Ceph, R2 and every test double speak, and because a bucket name with
    a dot in it breaks virtual-host style TLS.
    """

    def __init__(self, bucket, url_builder, region="us-east-1", endpoint=None,
                 access_key=None, secret_key=None, session_token=None,
                 prefix="", timeout=15):
        if not bucket:
            raise RuntimeError("SKRIBL_S3_BUCKET is required for the s3 backend.")
        self.bucket = bucket
        self._url_builder = url_builder
        self.region = region or "us-east-1"
        self.endpoint = (endpoint or f"https://s3.{self.region}.amazonaws.com").rstrip("/")
        self.access_key = access_key
        self.secret_key = secret_key
        self.session_token = session_token
        # A prefix lets one bucket hold several deployments. Normalised here so
        # callers cannot produce "//" or a key that escapes it.
        self.prefix = (prefix or "").strip("/")
        if self.prefix:
            self.prefix += "/"
        self.timeout = timeout

    # -- signing ---------------------------------------------------------------
    def _sign(self, method, path, query, payload, headers=None):
        """Return headers carrying a SigV4 Authorization for this request.

        `path` is the already-encoded absolute path, `query` the canonical
        (sorted, encoded) query string or "".
        """
        host = urlsplit(self.endpoint).netloc
        now = datetime.datetime.now(datetime.timezone.utc)
        amzdate = now.strftime("%Y%m%dT%H%M%SZ")
        datestamp = now.strftime("%Y%m%d")
        payload_hash = hashlib.sha256(payload or b"").hexdigest()

        hdrs = dict(headers or {})
        hdrs["host"] = host
        hdrs["x-amz-content-sha256"] = payload_hash
        hdrs["x-amz-date"] = amzdate
        if self.session_token:
            hdrs["x-amz-security-token"] = self.session_token

        signed = sorted(k.lower() for k in hdrs)
        canonical_headers = "".join(f"{k}:{str(hdrs[k]).strip()}\n" for k in signed)
        signed_headers = ";".join(signed)
        canonical = "\n".join([method, path, query, canonical_headers,
                               signed_headers, payload_hash])
        scope = f"{datestamp}/{self.region}/s3/aws4_request"
        to_sign = "\n".join(["AWS4-HMAC-SHA256", amzdate, scope,
                             hashlib.sha256(canonical.encode()).hexdigest()])

        def _hmac(key, msg):
            return hmac.new(key, msg.encode(), hashlib.sha256).digest()

        k = _hmac(("AWS4" + (self.secret_key or "")).encode(), datestamp)
        k = _hmac(k, self.region)
        k = _hmac(k, "s3")
        k = _hmac(k, "aws4_request")
        signature = hmac.new(k, to_sign.encode(), hashlib.sha256).hexdigest()
        hdrs["Authorization"] = (
            f"AWS4-HMAC-SHA256 Credential={self.access_key}/{scope}, "
            f"SignedHeaders={signed_headers}, Signature={signature}")
        return hdrs

    def _request(self, method, path, query="", body=None, extra_headers=None):
        headers = self._sign(method, path, query, body or b"", extra_headers)
        url = self.endpoint + path + (("?" + query) if query else "")
        req = urllib.request.Request(url, data=body, method=method)
        for k, v in headers.items():
            req.add_header(k, v)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                return r.status, r.read(), dict(r.headers)
        except urllib.error.HTTPError as e:
            return e.code, e.read() or b"", dict(e.headers or {})

    def _path(self, key):
        return "/" + quote(f"{self.bucket}/{self.prefix}{key}", safe="/~")

    # -- MediaStore ------------------------------------------------------------
    def put_bytes(self, raw, content_type, key):
        # Content-addressed: identical bytes are already there under the same
        # key, so a HEAD that finds one turns a repost into no upload at all.
        # The same skip the local store gets from os.path.exists.
        status, _body, _h = self._request("HEAD", self._path(key))
        if status == 200:
            return
        status, body, _h = self._request(
            "PUT", self._path(key), body=raw,
            extra_headers={"content-type": content_type or "application/octet-stream"})
        if status not in (200, 201):
            raise RuntimeError(f"S3 PUT {key} failed: {status} {body[:200]!r}")

    def url_for_key(self, key):
        # The app's own URL, NOT the bucket's. See the note above this class.
        return self._url_builder(key)

    def read(self, key):
        """-> (bytes, content_type), or None. Key is validated by the caller."""
        status, body, headers = self._request("GET", self._path(key))
        if status == 404:
            return None
        if status != 200:
            raise RuntimeError(f"S3 GET {key} failed: {status}")
        # DERIVED from the key's extension, exactly as the local store does, and
        # deliberately not the bucket's stored Content-Type: the key is built
        # from the VALIDATED type and KEY_RE has already constrained the
        # extension, whereas a bucket's metadata can be set by anything that
        # ever had write access. Serving an uploaded object as whatever it
        # claims to be is how an image becomes text/html.
        ext = os.path.splitext(key)[1].lower()
        return body, _TYPE_FOR_EXT.get(ext, "application/octet-stream")

    def iter_keys(self):
        """Paginated LIST. Yields (key, mtime) for sweep_orphans.

        Continuation-token paging rather than one call: a bucket is not a
        directory and the interface note on MediaStore.iter_keys exists to stop
        exactly the implementation that loads one into memory.
        """
        import datetime
        import xml.etree.ElementTree as ET

        token = None
        ns = "{http://s3.amazonaws.com/doc/2006-03-01/}"
        while True:
            parts = ["list-type=2", "max-keys=1000"]
            if self.prefix:
                parts.append("prefix=" + quote(self.prefix, safe=""))
            if token:
                parts.append("continuation-token=" + quote(token, safe=""))
            query = "&".join(sorted(parts))
            status, body, _h = self._request(
                "GET", "/" + quote(self.bucket, safe="/~"), query=query)
            if status != 200:
                raise RuntimeError(f"S3 LIST failed: {status} {body[:200]!r}")
            root = ET.fromstring(body)
            for c in root.findall(f"{ns}Contents"):
                name = (c.findtext(f"{ns}Key") or "")
                if self.prefix and name.startswith(self.prefix):
                    name = name[len(self.prefix):]
                if not name:
                    continue
                stamp = c.findtext(f"{ns}LastModified") or ""
                try:
                    mtime = datetime.datetime.fromisoformat(
                        stamp.replace("Z", "+00:00")).timestamp()
                except ValueError:
                    # Unparseable timestamp must read as NEW, not as ancient:
                    # sweep_orphans deletes anything older than the grace
                    # period, and 0 would make every such object collectable.
                    mtime = time.time()
                yield name, mtime
            if (root.findtext(f"{ns}IsTruncated") or "").lower() != "true":
                return
            token = root.findtext(f"{ns}NextContinuationToken")
            if not token:
                return

    def delete_key(self, key):
        status, body, _h = self._request("DELETE", self._path(key))
        if status not in (200, 204, 404):
            raise RuntimeError(f"S3 DELETE {key} failed: {status} {body[:200]!r}")
