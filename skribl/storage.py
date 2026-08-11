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
  s3      Subclass hook. `put_bytes` and `url_for_key` are the only two methods a
          real object store needs to implement.

Keys are the SHA-256 of the CONTENT, so identical media is stored once no matter
how many posts carry it — the same photo reposted by fifty people costs one
file — and a stored object can be cached immutably forever, because a different
byte is a different key.
"""
import base64
import hashlib
import os
import re
import time
import uuid

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
from .models import SkriblPostMedia  # noqa: E402

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
