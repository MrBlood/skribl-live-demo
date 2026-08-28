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
import copy
import datetime
import email.utils
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
    "audio/vnd.wave": ".wav",
    "audio/mpeg": ".mp3", "audio/mp3": ".mp3", "audio/ogg": ".ogg",
    "audio/opus": ".opus",
    "audio/webm": ".weba",
    "audio/mp4": ".m4a", "audio/m4a": ".m4a", "audio/x-m4a": ".m4a",
    "audio/aac": ".aac",
    "audio/flac": ".flac", "audio/x-flac": ".flac",
    "image/png": ".png",
    "image/jpeg": ".jpg", "image/jpg": ".jpg",
    "image/webp": ".webp",
    "image/gif": ".gif",
    # PARITY WITH VALIDATION, pinned by verify_mimeparity.py. Every subtype in
    # validation's ALLOWED_* sets must map here: an accepted type absent from
    # this table fell through to ".bin" and was served back as
    # application/octet-stream — bytes the validator had proved were FLAC
    # arriving at the player as a type <audio> refuses to probe. Seven accepted
    # spellings (flac, x-flac, opus, m4a, x-m4a, vnd.wave, image/jpg) sat in
    # that gap. (Outside review, P1.)
}


#: The canonical type for each stored extension. Several MIME spellings map to
#: one extension (audio/wav, audio/x-wav and audio/wave are all .wav), so this
#: is deliberately not the inverse of _EXT: it names the ONE type each
#: extension is served as. Aliases therefore normalise, and the same bytes are
#: served identically whichever spelling the uploader happened to send.
_TYPE_FOR_EXT = {
    ".wav": "audio/wav", ".mp3": "audio/mpeg", ".ogg": "audio/ogg",
    ".opus": "audio/opus", ".flac": "audio/flac",
    ".weba": "audio/webm", ".m4a": "audio/mp4", ".aac": "audio/aac",
    ".png": "image/png", ".jpg": "image/jpeg", ".webp": "image/webp",
    ".gif": "image/gif",
}


_MEDIA_LABEL_RE = re.compile(
    r"^(?:frames\[(?P<frame>\d+)\]\.)?(?:(?P<slot>photo|music)\.data"
    r"|(?P<snap>baseSnapshot|thumbnail))$")


def is_data_url(value):
    # .strip(): validation strips before validating, so a whitespace-padded
    # data URL is ACCEPTED there — and used to be missed HERE, leaving the
    # validated media inline in payload_json with no association row on an
    # externalizing deployment (v200 follow-up review, F4 / v199 F12). The two
    # parsers must accept the same strings or the "externalizing store removes
    # validated media from the DB" invariant quietly fails per-item.
    return isinstance(value, str) and bool(_DATA_URL_RE.match(value.strip()))


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
        # Normalize EXACTLY as validation does — strip, lowercase the MIME —
        # before the _EXT lookup (F4). Validation accepts `  data:Audio/WAV `
        # as audio/wav; looking up the raw "Audio/WAV" here missed the table
        # and served the validated bytes back as .bin/octet-stream, undoing
        # the MIME-parity fix one request at a time. The mapping key stays the
        # ORIGINAL string (externalise replaces by equality on it).
        header, _, b64 = data_url.strip().partition(",")
        content_type = (header[5:].split(";")[0] or "application/octet-stream")
        content_type = content_type.strip().lower()
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
            # Content-addressed: the bytes are already identical, so there is
            # nothing to write — but the object's AGE is load-bearing, and
            # returning here used to leave it untouched.
            #
            # OUTSIDE REVIEW v223 #1, a data-loss race. sweep_orphans treats age
            # as the only thing separating "abandoned" from "not finished yet".
            # Reusing an object older than the grace period therefore handed the
            # sweeper a key that looks long dead while a post is actively
            # claiming it: the association row is still inside the caller's
            # uncommitted transaction, the sweeper's query cannot see it, and the
            # bytes are deleted a moment before the post commits. The post
            # succeeds and its media 404s forever.
            #
            # Touching it makes the reuse look exactly like a fresh write, which
            # is what it is as far as the grace period is concerned.
            try:
                os.utime(path, None)
            except OSError:
                pass          # read-only or exotic fs; stat_key still re-checks
            return
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
        try:
            with open(tmp, "wb") as fh:
                fh.write(raw)
            os.replace(tmp, path)
        except BaseException:
            # Best-effort unlink (v200 follow-up review, F9 / v199 F18):
            # iter_keys deliberately ignores .part files, so without this an
            # ordinary write/replace failure (disk full, permissions) left a
            # temp file that NOTHING would ever reclaim — invisible to the
            # sweep by design, growing with every failed request. A crash
            # between write and unlink can still strand one; that residue is a
            # maintenance concern (documented in INTEGRATION.md), not a
            # per-request leak.
            try:
                os.remove(tmp)
            except OSError:
                pass
            raise
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
                # Yield only files sitting at THIS store's canonical sharded
                # path (root/ab/cd/abcd….ext). A file anywhere else under the
                # root — a co-tenant's tree, a stray README, a misplaced copy
                # — is not something this store wrote, and surfacing it by
                # basename made it look exactly like an orphan to
                # sweep_orphans. The sweep also refuses non-KEY_RE names
                # (see its NAMESPACE GUARD); this keeps the store's own
                # inventory honest rather than relying on that alone.
                full = os.path.join(sub, name)
                if full != self._paths(name)[1]:
                    continue
                yield name, os.path.getmtime(full)

    def stat_key(self, key):
        """Current mtime of one key, or None. The sweeper re-checks this
        immediately before deleting, so an object reused between being LISTED
        and being deleted is spared. Cheap: one stat."""
        try:
            return os.path.getmtime(self._paths(key)[1])
        except OSError:
            return None

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


#: A stored key is exactly a hex digest plus an extension THIS MODULE CAN
#: WRITE. Anything else is rejected before it can reach the filesystem — this is
#: the path-traversal guard, and it is an allowlist rather than a "../"
#: blocklist on purpose.
#:
#: OUTSIDE REVIEW v223 #2. This was `[a-z0-9]{2,4}`, which is not "a known
#: extension" however firmly the comment said so: it admits .html, .txt, .json,
#: .exe and several hundred other strings Skribl cannot emit. That matters
#: because sweep_orphans uses this as its OWNERSHIP guard before deleting — see
#: its NAMESPACE GUARD note — so in a shared root, or under an S3 prefix shorter
#: than a co-tenant's, a hex-named object of theirs with any short extension was
#: ours to delete. The existing co-tenant test passed throughout because both
#: objects it plants are rejected for other reasons (a slash, a non-hex stem);
#: neither varies the one field that decides this.
#:
#: Derived from _TYPE_FOR_EXT so the two cannot drift: an extension Skribl can
#: write is servable, and nothing else is.
KEY_RE = re.compile(r"^[0-9a-f]{64}\.(?:%s)$"
                    % "|".join(re.escape(e[1:]) for e in sorted(_TYPE_FOR_EXT)))


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

    # Rewrite ONLY the paths the media walker classified as media (v201
    # review, F5). The old walk replaced ANY string equal to a mapped data URL
    # anywhere in the document — but the API deliberately preserves unknown
    # keys for forward compatibility, so an extension field that happened to
    # hold the same string as photo.data was silently rewritten across the
    # validation/storage abstraction boundary: validation decides what is
    # media, storage must not overrule it by value coincidence. The walker's
    # labels have a fixed grammar (root or frames[i], then photo.data /
    # music.data / baseSnapshot), pinned by _MEDIA_LABEL_RE so a new media
    # slot added to _iter_media_items without a matching setter fails loudly
    # here instead of silently staying inline.
    payload = copy.deepcopy(payload)   # rebuilt, never the tracked original
    for value, _kind, _cap, label in iter_media(payload):
        if not isinstance(value, str) or value not in mapping:
            continue
        pm = _MEDIA_LABEL_RE.match(label)
        if pm is None:
            raise RuntimeError(
                f"externalise_payload has no setter for media label {label!r}"
                " — teach _MEDIA_LABEL_RE about the new slot.")
        container = payload
        if pm.group("frame") is not None:
            container = container["frames"][int(pm.group("frame"))]
        if pm.group("snap"):
            container[pm.group("snap")] = mapping[value]
        else:
            container[pm.group("slot")]["data"] = mapping[value]

    # Return the KEYS the store reported — never parsed back out of a URL.
    return payload, sorted(keys)



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
        # `limit` caps posts SCANNED, exactly. It used to be checked only
        # after a whole batch committed, so limit=10 with batch=100 scanned —
        # and converted, and COMMITTED — up to 100 posts: a "careful first
        # run" flag that overshot by an order of magnitude on the run where
        # being careful mattered. The fetch itself now never asks for more
        # than the remaining allowance. (Outside review follow-up.)
        take = batch
        if limit is not None:
            take = min(batch, limit - scanned)
            if take <= 0:
                break
        rows = (session().query(SkriblPost)
                .filter(SkriblPost.id > last_id)
                .order_by(SkriblPost.id)
                .limit(take).all())
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

    A thin wrapper over sweep_orphans_report() kept at its original signature
    and return type, because every existing caller wants exactly the list.
    Anything running this as a scheduled job wants the counts instead — see
    sweep_orphans_report and the `python -m skribl.sweep` entry point.
    """
    return sweep_orphans_report(store, session, older_than_seconds, dry_run)["removed"]


def sweep_orphans_report(store, session, older_than_seconds=86400, dry_run=True):
    """The sweep, plus the numbers that make it operable. (Outside review, #6.)

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

    NAMESPACE GUARD (outside review, P1). Only keys that are SKRIBL-SHAPED —
    KEY_RE: a 64-hex content digest plus a known extension, no slashes — are
    even candidates. A store view can see more than this deployment wrote: an
    S3 prefix shorter than a co-tenant's ("" beside "tenant-a/") lists the
    co-tenant's objects with their namespace still in the name, and a local
    root can contain someone's stray files. Every one of those is by
    definition unreferenced by OUR association table, so the old code's next
    step was to delete it. Anything that is not shaped like ours is not ours
    to reclaim, whatever it is.

    BOUNDED MEMORY. The reference check used to load every media_key in the
    table into one Python set — fine at a thousand posts, an OOM at the scale
    the sweep exists for. Candidates are now collected in chunks and checked
    with one IN() query per chunk: memory is O(chunk), queries are O(n/chunk),
    and the store side was already paginated.

    Do NOT try to make the object store and the database one distributed
    transaction. Objects are immutable, associations are authoritative, and a
    periodic sweep is the honest reconciliation.

    WHY THE COUNTS EXIST. Returning only the removed keys made the sweep
    unobservable in the one way that matters: a run that removes nothing is
    indistinguishable from a run that never saw anything, and a store view
    listing a co-tenant's namespace looked exactly like an empty bucket. Every
    branch that DECLINES to delete is now counted separately, so a deployment
    can tell "nothing to reclaim" from "the credentials see the wrong prefix"
    from "the grace period is swallowing everything" without adding logging to
    a library. Every value is JSON-serialisable so a job can ship the dict
    straight to whatever collects its metrics.

    A FAILED DELETE IS NO LONGER A FAILED SWEEP. `store.delete_key` used to run
    uncaught, so one object a bucket policy refuses aborted the whole run and
    left every later orphan in place — and the key was already in the returned
    list, which reported a deletion that did not happen. Failures are collected
    per key and the sweep continues; `removed` now means removed.
    """
    started = time.time()
    cutoff = started - max(0, older_than_seconds)
    removed = []
    errors = []
    stats = {"listed": 0, "skipped_foreign": 0, "skipped_young": 0,
             "skipped_referenced": 0, "skipped_reused": 0, "chunks": 0}
    chunk = []

    def flush_chunk():
        if not chunk:
            return
        stats["chunks"] += 1
        referenced = {row[0] for row in
                      session.query(SkriblPostMedia.media_key)
                      .filter(SkriblPostMedia.media_key.in_(chunk)).all()}
        for key in chunk:
            if key in referenced:
                stats["skipped_referenced"] += 1
                continue
            # RE-CHECK THE AGE, immediately before deleting. Listing and
            # deleting are separated by a reference query over up to 500 keys;
            # a post can reuse a listed object inside that window, and reuse now
            # refreshes the object's age (see put_bytes). Without this, the
            # touch only narrows the race rather than closing the ordering the
            # outside review described. A store that cannot answer says None and
            # gets the old behaviour.
            _stat = getattr(store, "stat_key", None)
            if _stat is not None:
                _now = _stat(key)
                if _now is not None and _now > cutoff:
                    stats["skipped_reused"] += 1
                    continue        # became young: a reuse is in flight
            if dry_run:
                removed.append(key)
                continue
            try:
                store.delete_key(key)
            except Exception as exc:
                # Deliberately broad: the store is host-supplied and may raise
                # anything. The sweep's job is to reclaim what it can and report
                # what it could not, not to decide which backend errors are
                # fatal. No key material or credential is in the message.
                errors.append({"key": key, "error": f"{type(exc).__name__}: {exc}"})
                continue
            removed.append(key)
        chunk.clear()

    for key, mtime in store.iter_keys():
        stats["listed"] += 1
        if not KEY_RE.match(key or ""):
            stats["skipped_foreign"] += 1
            continue
        if mtime > cutoff:
            stats["skipped_young"] += 1
            continue
        chunk.append(key)
        if len(chunk) >= 500:
            flush_chunk()
    flush_chunk()
    report = {
        "dry_run": bool(dry_run),
        "older_than_seconds": max(0, older_than_seconds),
        "removed": removed,
        "removed_count": len(removed),
        "delete_errors": errors,
        "delete_error_count": len(errors),
        "duration_seconds": round(time.time() - started, 3),
    }
    report.update(stats)
    # Candidates are what survived BOTH cheap filters and reached the reference
    # query — derived rather than counted so it can never disagree with them.
    report["candidates"] = (stats["listed"] - stats["skipped_foreign"]
                            - stats["skipped_young"])
    return report


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
        # key. The HEAD used to turn a repost into no upload at all — and left
        # the object's LastModified untouched, which is the S3 half of OUTSIDE
        # REVIEW v223 #1: sweep_orphans reads age as "abandoned vs not finished
        # yet", so reusing an old orphan handed the sweeper bytes that look long
        # dead while a post was mid-commit on them. See LocalDiskStore.put_bytes.
        #
        # A SELF-COPY, not a re-upload. Both refresh LastModified; the copy
        # keeps the property this dedupe exists for — a repost costs no upload
        # — which verify_s3 asserts outright. The first draft of this fix
        # re-PUT the bytes and broke that assertion, which is the repo's rule
        # about not moving a ratchet to fit your own commit doing its job: the
        # answer was to make the fix testable rather than to relax the test, so
        # the S3 double now implements COPY.
        status, _body, _h = self._request("HEAD", self._path(key))
        if status == 200:
            status, body, _h = self._request(
                "PUT", self._path(key),
                extra_headers={"x-amz-copy-source": self._path(key),
                               "x-amz-metadata-directive": "REPLACE",
                               "content-type": content_type or "application/octet-stream"})
            if status in (200, 201):
                return
            # A backend without COPY must not silently skip the refresh, or the
            # race this fixes comes back invisibly. Fall through and re-upload.
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

    def stat_key(self, key):
        """Current LastModified of one key as epoch seconds, or None.

        The sweeper re-checks this immediately before deleting, so an object
        reused between being LISTED and being deleted is spared. An
        unparseable or missing stamp reads as NOW for the same reason
        iter_keys does it: the safe direction is "too new to touch".
        """
        status, _body, headers = self._request("HEAD", self._path(key))
        if status != 200:
            return None
        stamp = ""
        for k, v in (headers or {}).items():
            if k.lower() == "last-modified":
                stamp = v
                break
        if not stamp:
            return time.time()
        try:
            return email.utils.parsedate_to_datetime(stamp).timestamp()
        except (TypeError, ValueError):
            return time.time()

    def delete_key(self, key):
        status, body, _h = self._request("DELETE", self._path(key))
        if status not in (200, 204, 404):
            raise RuntimeError(f"S3 DELETE {key} failed: {status} {body[:200]!r}")
