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

    Content type is written to a `.type` sidecar rather than guessed from the
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
        with open(type_path, "w", encoding="utf-8") as fh:
            fh.write(content_type)

    def url_for_key(self, key):
        return self._url_builder(key)

    def read(self, key):
        """-> (bytes, content_type), or None. Key is validated by the caller."""
        _, path, type_path = self._paths(key)
        if not os.path.isfile(path):
            return None
        try:
            with open(type_path, encoding="utf-8") as fh:
                content_type = fh.read().strip() or "application/octet-stream"
        except OSError:
            content_type = "application/octet-stream"
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
