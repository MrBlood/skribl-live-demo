import base64
import hashlib
import hmac
import ipaddress
import math
import os
import re
import secrets
import time
from collections import deque
from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit
from threading import Lock

from flask import Flask, g, jsonify, redirect, render_template, request, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError


db = SQLAlchemy()


class RateEvent(db.Model):
    """Shared-store rate limiting, so quotas survive a deploy and are shared across
    workers. (Review #13)

    The in-memory limiter is per-process: N gunicorn workers meant N independent
    quotas, and a deploy reset them all. This table is the same limiter backed by
    the database the app already has — no Redis, no new infrastructure.

    The key is a SALTED HASH of the client identity, never the raw IP: rate
    limiting does not need to know who anyone is, and storing addresses in a
    posts database is a privacy cost with no operational benefit.

    Concurrency: a slot is INSERTed and committed first, then counted. Racing
    workers therefore both see both rows and the loser deletes its own, which
    biases towards over-rejection. **This is insert-then-count, not a database
    constraint** — there is no row lock or advisory lock enforcing "at most N
    active slots", and the exact behaviour under PostgreSQL depends on commit
    order and isolation. Verified under SQLite and threads; NOT yet verified on
    PostgreSQL across processes. Treat the guarantee as "biased safe", not proven.
    (Review round 7, #5)

    Crash window (CLOSED in v122): the slot is still written before the post row,
    but as state='pending'. Pending rows only count while they are younger than
    RATE_PENDING_TTL, so a process killed between the two commits costs the client
    that TTL rather than the full hour. A slot is promoted to 'committed' only
    after the post row is durable, which makes "only committed posts spend a slot"
    true beyond the short reservation window. (Review round 7, #6)

    Cost: with this backend every ATTEMPT is a database write, so a malformed
    request flood becomes a write flood. The table is capped by cleanup, not by
    admission. An edge limiter remains preferable for raw flood protection.
    (Review round 7, #7)
    """
    __tablename__ = "skribl_rate_events"

    id = db.Column(db.Integer, primary_key=True)
    bucket = db.Column(db.String(16), nullable=False)          # 'posts' | 'attempts'
    key_hash = db.Column(db.String(64), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    # 'pending' until the post row commits, then 'committed'. A pending row that
    # is never resolved — because the process was killed between the two commits —
    # stops counting after RATE_PENDING_TTL instead of holding a slot for the full
    # hour. That closes the crash window described below. (Review round 7, #6)
    state = db.Column(db.String(10), nullable=False, default="committed")

    # Two indexes for two different access patterns: per-key counting, and the
    # time-ordered cleanup sweep, which the composite index does not serve
    # because it does not lead with created_at. (Review round 7, #8)
    __table_args__ = (
        db.Index("ix_rate_bucket_key_time", "bucket", "key_hash", "created_at"),
        db.Index("ix_rate_created_at", "created_at"),
    )


class SkriblPost(db.Model):
    __tablename__ = "skribl_posts"

    id = db.Column(db.Integer, primary_key=True)
    public_id = db.Column(db.String(32), unique=True, nullable=False, index=True)
    user_id = db.Column(db.Integer, nullable=True)
    title = db.Column(db.String(80), nullable=False)
    caption = db.Column(db.String(300), nullable=True)
    payload_json = db.Column(db.JSON, nullable=False)
    has_audio = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)


# Open Graph title/description for a shared Skribl, with generic fallbacks.
# Kept pure and import-free (no DB, no Flask context) so it can be unit-tested
# headless — the route feeds it the post's fields (or None on a miss/error).
# The version string shown in the Pad's overflow menu. Single-sourced HERE and
# injected into the template, because the literal that used to live in
# skribl_editor.html drifted nine versions (it still read v96 at v105) — nothing
# forced anyone to touch it. Bump this one line per release; verify_version.py
# fails if a hardcoded version reappears in a template.
SKRIBL_VERSION = "v130"

OG_DEFAULT_TITLE = "Skribl Pad"
OG_DEFAULT_DESCRIPTION = "A drawing that replays in time with music."


def _og_meta(title, caption):
    og_title = (title or "").strip() or OG_DEFAULT_TITLE
    og_description = (caption or "").strip() or OG_DEFAULT_DESCRIPTION
    return og_title, og_description


# Decode a client-generated share-card thumbnail stored in the payload as an
# image data URL back into raw bytes for the card route. Accepts PNG or JPEG:
# the card was historically PNG and is JPEG now (opaque 1200x630, no alpha to
# lose — ~5x smaller), and old PNG posts must keep unfurling, so both are served.
# The subtype is captured so the route can send a matching Content-Type. Kept
# pure and import-light (base64 + re only, no DB/Flask) so it can be unit-tested
# headless. Returns None on anything malformed so the caller can fall back to the
# static branded card instead of erroring.
_DATA_URL_IMAGE_RE = re.compile(r"^data:image/(png|jpeg);base64,(.+)$", re.DOTALL)

# public_id slugs come from secrets.token_urlsafe(8) → 11 chars of [A-Za-z0-9_-].
# Checking the format up front (range is generous for future length changes)
# keeps junk out of DB lookups and template injection surface entirely. Routes
# keep their existing render-always / fallback contracts on a mismatch — this
# only short-circuits the lookup, it never changes what a URL renders.
_PUBLIC_ID_RE = re.compile(r"^[A-Za-z0-9_-]{6,64}$")


def _valid_public_id(public_id):
    return isinstance(public_id, str) and bool(_PUBLIC_ID_RE.match(public_id))


# Hard ceiling for the share-card image served by /s/<id>/card.png. A real
# 1200x630 thumbnail is a few hundred KB; anything much larger in the payload
# is malformed or hostile, and serving (and CDN-caching) it on every unfurl
# would be a cheap amplification. Oversize falls back to the static card.
MAX_CARD_BYTES = 2_000_000

# Naive in-memory per-IP rate limit for POST /api/skribls: N posts per rolling
# window, per process. Not distributed, resets on deploy — deliberately minimal.
# It exists to stop the trivial abuse case (one client looping max-size posts
# until free-tier Postgres fills), not to be real infrastructure; replace with
# proper limiting when auth lands (roadmap #5).
def _env_int(name, default, minimum=1, maximum=None):
    # Bare int(os.environ[...]) meant a typo in deployment config crashed the app
    # at import with a traceback naming neither the variable nor the value, and 0
    # or a negative produced a nonsensical limit that looked like a bug elsewhere.
    # Fail loudly, name the variable, clamp the range. (Review #12)
    raw = os.environ.get(name)
    if raw is None or str(raw).strip() == "":
        return default
    try:
        value = int(str(raw).strip())
    except (TypeError, ValueError):
        raise RuntimeError(f"{name} must be an integer, got {raw!r}. Fix the deployment config.")
    if value < minimum:
        raise RuntimeError(f"{name} must be >= {minimum}, got {value}.")
    if maximum is not None and value > maximum:
        raise RuntimeError(f"{name} must be <= {maximum}, got {value}.")
    return value


_RATE_WINDOW_SECONDS = 3600
_RATE_MAX_POSTS = _env_int("SKRIBL_RATE_MAX_POSTS", 20)
# Review #7: a flood of malformed bodies used to burn the same quota as real
# posts, so one bad client could lock out everyone sharing its IP. Every request
# is charged to a large ATTEMPT budget; only a committed post spends a post.
_RATE_MAX_ATTEMPTS = _env_int("SKRIBL_RATE_MAX_ATTEMPTS", max(_RATE_MAX_POSTS * 10, 200))
# Review #3: X-Forwarded-For is attacker-controlled unless an edge overwrites it.
# Default 0 => trust nothing, key on remote_addr. Set to the number of proxies
# actually in front of the app to re-enable header parsing.
_TRUSTED_PROXIES = _env_int("SKRIBL_TRUSTED_PROXIES", 0, minimum=0)
_rate_buckets = {}
_rate_lock = Lock()


def _client_ip():
    # Trusting X-Forwarded-For unconditionally let any caller pick a fresh
    # rate-limit key per request AND stuff _rate_buckets with attacker-chosen
    # keys. It is now consulted ONLY when SKRIBL_TRUSTED_PROXIES declares how many
    # proxies sit in front of us, and we take the entry that many hops from the
    # RIGHT — everything further left is client-supplied and worthless. (Review #3)
    if _TRUSTED_PROXIES > 0:
        fwd = request.headers.get("X-Forwarded-For", "")
        if fwd:
            parts = [p.strip() for p in fwd.split(",") if p.strip()]
            if len(parts) >= _TRUSTED_PROXIES:
                candidate = parts[-_TRUSTED_PROXIES]
                # A trusted but misconfigured edge can still forward junk, which
                # would land straight in the bucket map as an attacker-chosen key.
                # Handles IPv6 too. (Review round 2, #3)
                try:
                    return str(ipaddress.ip_address(candidate))
                except ValueError:
                    return request.remote_addr or "unknown"
    return request.remote_addr or "unknown"


def _rate_limited(ip, kind="posts"):
    if _RATE_BACKEND == "db":
        return _db_rate_limited(ip, kind)
    # kind='attempts' is charged on every request (flood protection); kind='posts'
    # is charged only when a post commits, via _rate_record_post. Separate buckets
    # so a burst of 400s cannot exhaust the posting allowance. (Review #7)
    # Only 'attempts' goes through here now; post slots are reserved atomically by
    # _rate_reserve_post. Entries are timestamps here and (timestamp, token) pairs
    # in the posts bucket, so read element 0 either way.
    cap = _RATE_MAX_ATTEMPTS if kind == "attempts" else _RATE_MAX_POSTS
    now = time.monotonic()
    with _rate_lock:
        bucket = _rate_buckets.setdefault((kind, ip), deque())
        while bucket and now - (bucket[0][0] if isinstance(bucket[0], tuple) else bucket[0]) > _RATE_WINDOW_SECONDS:
            bucket.popleft()
        if len(bucket) >= cap:
            return True
        if kind == "attempts":
            bucket.append(now)
        # Opportunistic cleanup so the dict can't grow without bound: expire
        # aged entries in every bucket, then drop the empty buckets.
        if len(_rate_buckets) > 1000:
            for bkey, q in list(_rate_buckets.items()):
                while q and now - (q[0][0] if isinstance(q[0], tuple) else q[0]) > _RATE_WINDOW_SECONDS:
                    q.popleft()
                if not q:
                    del _rate_buckets[bkey]
        return False


_RATE_BACKEND = os.environ.get("SKRIBL_RATE_BACKEND", "memory").strip().lower()
if _RATE_BACKEND not in ("memory", "db"):
    raise RuntimeError("SKRIBL_RATE_BACKEND must be 'memory' or 'db'.")


# A dedicated key, NOT SECRET_KEY: rotating the session secret would otherwise
# silently reset every quota as a side effect. Falls back to SECRET_KEY so an
# existing deploy keeps working, and the db backend refuses to start without one
# of them — with a public default salt the IPv4 space is trivially precomputed,
# which would make the hashing decorative. (Review round 7, #9)
_RATE_HMAC_KEY = (os.environ.get("SKRIBL_RATE_HMAC_KEY")
                  or os.environ.get("SECRET_KEY") or "")
if _RATE_BACKEND == "db" and not _RATE_HMAC_KEY:
    raise RuntimeError(
        "SKRIBL_RATE_HMAC_KEY (or SECRET_KEY) is required when "
        "SKRIBL_RATE_BACKEND=db — the stored identity hash needs a private key."
    )


def _rate_key(ip):
    return hmac.new(_RATE_HMAC_KEY.encode(), str(ip).encode(), hashlib.sha256).hexdigest()


def _rate_cutoff():
    return datetime.now(timezone.utc) - timedelta(seconds=_RATE_WINDOW_SECONDS)


def _db_rate_count(bucket, key_hash):
    # Committed rows count for the whole window; pending ones only while they are
    # still plausibly in flight, so an abandoned reservation ages out fast.
    pending_cutoff = datetime.now(timezone.utc) - timedelta(seconds=RATE_PENDING_TTL)
    return (RateEvent.query
            .filter(RateEvent.bucket == bucket,
                    RateEvent.key_hash == key_hash,
                    RateEvent.created_at >= _rate_cutoff(),
                    db.or_(RateEvent.state == "committed",
                           RateEvent.created_at >= pending_cutoff))
            .count())


def _db_rate_limited(ip, kind):
    cap = _RATE_MAX_ATTEMPTS if kind == "attempts" else _RATE_MAX_POSTS
    key_hash = _rate_key(ip)
    if kind != "attempts":
        return _db_rate_count(kind, key_hash) >= cap
    row = RateEvent(bucket=kind, key_hash=key_hash)
    db.session.add(row)
    db.session.commit()
    if _db_rate_count(kind, key_hash) > cap:
        db.session.delete(row)
        db.session.commit()
        return True
    return False


def _db_rate_reserve_post(ip):
    key_hash = _rate_key(ip)
    row = RateEvent(bucket="posts", key_hash=key_hash, state="pending")
    db.session.add(row)
    db.session.commit()
    if _db_rate_count("posts", key_hash) > _RATE_MAX_POSTS:
        db.session.delete(row)
        db.session.commit()
        return None
    # Opportunistic cleanup, BOUNDED. An unbounded delete inside a user request
    # can hold locks and spike latency for whoever happens to trigger it after a
    # quiet period. Capped per request; the remainder is collected by subsequent
    # requests. A scheduled job is still the better answer at scale.
    # (Review round 7, #8)
    if secrets.randbelow(50) == 0:
        stale = (db.session.query(RateEvent.id)
                 .filter(RateEvent.created_at < _rate_cutoff())
                 .limit(RATE_CLEANUP_BATCH).all())
        if stale:
            RateEvent.query.filter(RateEvent.id.in_([r[0] for r in stale])).delete(
                synchronize_session=False)
            db.session.commit()
    return row.id


def _db_rate_release_post(ip, token):
    if token is None:
        return
    RateEvent.query.filter(RateEvent.id == token).delete()
    db.session.commit()


def _db_rate_commit_post(token):
    # Promote the reservation once the post row is durable.
    if token is None:
        return
    RateEvent.query.filter(RateEvent.id == token).update({"state": "committed"})
    db.session.commit()


def _rate_commit_post(token):
    if _RATE_BACKEND == "db":
        _db_rate_commit_post(token)


def _rate_reserve_post(ip):
    """Atomically check the post cap AND take a slot. Returns a token, or None.

    Review round 2, #2: checking the cap and recording the post were two separate
    locked operations with validation and a database commit between them, so N
    concurrent requests could all observe room and all commit. The slot is now
    reserved up front and released if the request does not produce a row, which
    makes the single-process limiter internally correct. It does NOT make it
    distributed — see #13.
    """
    if _RATE_BACKEND == "db":
        return _db_rate_reserve_post(ip)
    now = time.monotonic()
    with _rate_lock:
        bucket = _rate_buckets.setdefault(("posts", ip), deque())
        while bucket and now - bucket[0][0] > _RATE_WINDOW_SECONDS:
            bucket.popleft()
        if len(bucket) >= _RATE_MAX_POSTS:
            return None
        token = object()
        bucket.append((now, token))
        return token


def _rate_release_post(ip, token):
    # Give the slot back when validation fails or the commit never happens.
    if token is None:
        return
    if _RATE_BACKEND == "db":
        return _db_rate_release_post(ip, token)
    with _rate_lock:
        bucket = _rate_buckets.get(("posts", ip))
        if not bucket:
            return
        for i, entry in enumerate(bucket):
            if entry[1] is token:
                del bucket[i]
                return


def _decode_data_url_image(data_url):
    # Returns (raw_bytes, mimetype) for a PNG or JPEG data URL, or None if the
    # value is missing/malformed/an unsupported type (webp, gif, svg, …) so the
    # caller falls back to the static card.
    if not isinstance(data_url, str):
        return None
    m = _DATA_URL_IMAGE_RE.match(data_url.strip())
    if not m:
        return None
    try:
        raw = base64.b64decode(m.group(2), validate=True)
    except Exception:
        return None
    return raw, "image/" + m.group(1)


def _payload_has_audio(payload):
    # Whether a posted Skribl carries actual audio bytes. Frame-aware: audio lives
    # at the top level on a legacy Skribl, or inside a frame on a frame-format one
    # (a classic Skribl is a 1-frame Skribl). A settings-only/empty music dict
    # ({}) doesn't count. Pure + import-light so it can be unit-tested headless.
    if not isinstance(payload, dict):
        return False
    music = payload.get("music")
    if not isinstance(music, dict) or not music.get("data"):
        music = None
        frames = payload.get("frames")
        if isinstance(frames, list):
            for frame in frames:
                if isinstance(frame, dict):
                    m = frame.get("music")
                    if isinstance(m, dict) and m.get("data"):
                        music = m
                        break
    return bool((music or {}).get("data"))


# --- Server-side media validation (INTEGRATION §7) ---------------------------
# The post endpoint is public and unauthenticated, and every media item arrives as
# a base64 data URL inside payload_json. Until now the only limit was
# MAX_CONTENT_LENGTH on the whole request, so a single post could carry ~24 MB of
# arbitrary blob — any type, valid base64 or not — straight into the JSON column.
# At the current rate limit that is ~480 MB/hour/IP into a free-tier Postgres.
#
# These caps are per-item and deliberately generous: a trimmed loop is a couple of
# MB (see the v102 note: a 42s WAV with an 8s loop posts 1.41 MB) and a background
# photo is well under 8 MB. They are env-tunable so a deploy can tighten them
# without a code change.
#
# Type handling is an ALLOW-LIST of top-level types (audio/*, image/*) with SVG
# explicitly excluded — SVG is the one image type that carries script, and nothing
# the client produces is SVG. Subtypes are otherwise left open on purpose: `music`
# is whatever audio file the user picked (mpeg/wav/ogg/mp4/flac/…), and narrowing
# that would reject legitimate uploads for no security gain.
#
# NOT covered here: dimensions and duration, which need real decoding (Pillow /
# an audio decoder) and a dependency this app does not have. Bytes and type are
# the cheap 90%.
MAX_AUDIO_BYTES = _env_int("SKRIBL_MAX_AUDIO_BYTES", 12_000_000, minimum=1024)
MAX_IMAGE_BYTES = _env_int("SKRIBL_MAX_IMAGE_BYTES", 8_000_000, minimum=1024)

_MEDIA_DATA_URL_RE = re.compile(r"^data:([a-zA-Z]+)/([a-zA-Z0-9.+-]+);base64,(.*)$", re.DOTALL)


# STRICT image allow-list (review round 2, #1). The first pass matched prefixes
# only and left unknown subtypes unchecked, which meant image/avif or image/tiff
# with arbitrary bytes was stored unverified, and a RIFF/WAVE body passed as WebP
# because only the first four bytes were compared. Both are closed: an unlisted
# subtype is now REJECTED, and WebP is checked as a container (RIFF....WEBP), not
# a prefix.
# BMP was dropped in v116 rather than added to the Pad's pickers: the Pad drawers
# only ever offered jpeg/png/gif/webp, so keeping BMP meant two policies wearing
# one comment. Nothing the client produces is BMP. (Review round 6, #6)
ALLOWED_IMAGE_SUBTYPES = {"png", "jpeg", "jpg", "gif", "webp"}


def _valid_image_signature(sub_type, raw):
    """Header/container check ONLY — deliberately not full image validation.

    This proves the declared subtype matches the leading bytes. It does NOT prove
    the file decodes, and a truncated b"\x89PNG\r\n\x1a\n" with no IHDR passes.
    Dimensions, pixel count, decompression cost and completeness are NOT checked;
    doing so needs a real decoder (Pillow) with resource limits, which is a
    deliberate follow-up rather than something to imply here. The error message
    says "does not match the declared container" for the same reason.
    (Review round 4, #3)
    """
    if sub_type == "png":
        return raw.startswith(b"\x89PNG\r\n\x1a\n")
    if sub_type in ("jpeg", "jpg"):
        return raw.startswith(b"\xff\xd8\xff")
    if sub_type == "gif":
        return raw.startswith((b"GIF87a", b"GIF89a"))
    if sub_type == "webp":
        # RIFF is a generic container: WAV and AVI share the first four bytes.
        # The format is only established by the WEBP fourcc at offset 8.
        return len(raw) >= 12 and raw.startswith(b"RIFF") and raw[8:12] == b"WEBP"
    return False
# Audio the client can decode. Narrower than 'any audio/*' per review #6, but
# deliberately generous — these are the containers a file picker actually yields.
ALLOWED_AUDIO_SUBTYPES = {
    "wav", "x-wav", "wave", "vnd.wave", "mpeg", "mp3", "mp4", "x-m4a", "m4a",
    "aac", "ogg", "opus", "webm", "flac", "x-flac",
}


def _valid_audio_signature(sub_type, raw):
    """Container check for declared audio. (Review round 4, #2)

    Round 3 allow-listed subtypes but never looked at the bytes, so
    b"this is not a WAV" passed as audio/wav. Like the image checks, this proves
    the CONTAINER, not that a complete file decodes — see the note on
    _valid_image_signature.

    Two of these are container-FAMILY checks, not proof of audio, and should be
    described that way (review round 5, #4):
      - webm: the EBML magic identifies Matroska/WebM generally. A video-only
        WebM or a Matroska file declared audio/webm will pass.
      - mp4/x-m4a/m4a/aac: the `ftyp` box identifies ISO Base Media Format. A
        video MP4 or an HEIF/HEIC container declared audio/mp4 will pass.
    Distinguishing tracks and codecs needs a real media parser, which is out of
    scope here. What these DO close is the arbitrary-bytes case.
    """
    if sub_type in ("wav", "x-wav", "wave", "vnd.wave"):
        return len(raw) >= 12 and raw.startswith(b"RIFF") and raw[8:12] == b"WAVE"
    if sub_type in ("flac", "x-flac"):
        return raw.startswith(b"fLaC")
    if sub_type in ("ogg", "opus"):
        return raw.startswith(b"OggS")
    if sub_type == "webm":
        return raw.startswith(b"\x1a\x45\xdf\xa3")          # EBML
    if sub_type in ("mpeg", "mp3"):
        # ID3 tag, or an MPEG audio frame sync (11 set bits).
        return raw.startswith(b"ID3") or (len(raw) >= 2 and raw[0] == 0xFF and (raw[1] & 0xE0) == 0xE0)
    if sub_type in ("mp4", "x-m4a", "m4a"):
        return len(raw) >= 12 and raw[4:8] == b"ftyp"
    if sub_type == "aac":
        # ADTS sync, or an MP4/ftyp container mislabelled as aac by a picker.
        return (len(raw) >= 2 and raw[0] == 0xFF and (raw[1] & 0xF0) == 0xF0) or \
               (len(raw) >= 12 and raw[4:8] == b"ftyp")
    return False


def _validate_media_data_url(value, expected_type, max_bytes, label):
    # Returns None if acceptable, else a human-readable error string. Pure and
    # import-light (re + base64) so it can be unit-tested headless.
    if value is None:
        return None
    if not isinstance(value, str):
        return f"'{label}' must be a data URL string."
    m = _MEDIA_DATA_URL_RE.match(value.strip())
    if not m:
        return f"'{label}' must be a base64 data URL."
    top, sub_type, b64 = m.group(1).lower(), m.group(2).lower(), m.group(3)
    if top != expected_type:
        return f"'{label}' must be {expected_type}/*, got {top}/{sub_type}."
    if top == "image" and sub_type in ("svg+xml", "svg"):
        return f"'{label}' may not be SVG."
    # Size from the base64 length before decoding, so an oversize payload is
    # rejected without spending the CPU to decode it.
    approx = (len(b64) * 3) // 4
    if approx > max_bytes:
        return f"'{label}' is too large ({approx // 1000} kB; limit {max_bytes // 1000} kB)."
    try:
        raw = base64.b64decode(b64, validate=True)
    except Exception:
        return f"'{label}' is not valid base64."
    # Review #6: syntax + declared type + size said nothing about the BYTES.
    # 'data:image/png;base64,' (empty) and b'not a png' declared as PNG both
    # sailed through. Reject empty payloads and check the magic number, so the
    # declared container has to match what was actually sent.
    if not raw:
        return f"'{label}' is empty."
    if top == "image":
        if sub_type not in ALLOWED_IMAGE_SUBTYPES:
            return f"'{label}' has an unsupported image format ({sub_type})."
        if not _valid_image_signature(sub_type, raw):
            return f"'{label}' does not match the declared {sub_type} container."
    if top == "audio":
        if sub_type not in ALLOWED_AUDIO_SUBTYPES:
            return f"'{label}' has an unsupported audio format ({sub_type})."
        if not _valid_audio_signature(sub_type, raw):
            return f"'{label}' does not match the declared {sub_type} container."
    return None


def _iter_media_items(payload):
    # Yields (value, expected_type, max_bytes, label) for every media item in a
    # payload, top-level and per-frame. Frame-format Skribls carry media on their
    # frames (a classic Skribl is a 1-frame Skribl), so both must be walked.
    def scan(container, where):
        if not isinstance(container, dict):
            return
        for key, kind, cap in (("music", "audio", MAX_AUDIO_BYTES),
                               ("photo", "image", MAX_IMAGE_BYTES)):
            item = container.get(key)
            if isinstance(item, dict) and item.get("data") is not None:
                yield item["data"], kind, cap, f"{where}{key}.data"

    yield from scan(payload, "")
    thumb = payload.get("thumbnail")
    if thumb is not None:
        yield thumb, "image", MAX_CARD_BYTES, "thumbnail"
    frames = payload.get("frames")
    if isinstance(frames, list):
        # No slice here any more. The old frames[:200] silently skipped media on
        # frame 201+, so an oversize payload could smuggle unvalidated media past
        # the check entirely. The frame COUNT is now capped up front by
        # _validate_payload_complexity, which runs before this. (Review #2)
        for i, frame in enumerate(frames):
            yield from scan(frame, f"frames[{i}].")


# --- Structural complexity limits (review #8) --------------------------------
# MAX_CONTENT_LENGTH caps BYTES, which says nothing about rendering cost: a small
# payload can still describe a canvas or a point count that will pin a phone.
# These are deliberately far above anything the editors produce — they exist to
# stop hand-built payloads, not to constrain real drawings.
MAX_FRAMES = _env_int("SKRIBL_MAX_FRAMES", 200, minimum=1)
MAX_POINTS_PER_FRAME = _env_int("SKRIBL_MAX_POINTS_PER_FRAME", 20_000, minimum=1)
MAX_TOTAL_POINTS = _env_int("SKRIBL_MAX_TOTAL_POINTS", 200_000, minimum=1)
MAX_GROUPS_PER_FRAME = _env_int("SKRIBL_MAX_GROUPS_PER_FRAME", 5_000, minimum=1)
MAX_HOLD = _env_int("SKRIBL_MAX_HOLD", 8, minimum=1)
MAX_CANVAS_EDGE = _env_int("SKRIBL_MAX_CANVAS_EDGE", 4096, minimum=16)
RATE_CLEANUP_BATCH = _env_int("SKRIBL_RATE_CLEANUP_BATCH", 500, minimum=1)
# How long an unresolved reservation keeps occupying a slot. Long enough for a
# slow post to finish, short enough that a killed process costs seconds not hours.
RATE_PENDING_TTL = _env_int("SKRIBL_RATE_PENDING_TTL", 120, minimum=5)
COORD_LIMIT = 100_000
MAX_BRUSH = 500


def _finite(n):
    return isinstance(n, (int, float)) and not isinstance(n, bool) and math.isfinite(n)


def _validate_points(points, label, budget):
    if not isinstance(points, list):
        return f"'{label}' must be a list.", budget
    if len(points) > MAX_POINTS_PER_FRAME:
        return (f"'{label}' has too many points ({len(points)}; limit "
                f"{MAX_POINTS_PER_FRAME}).", budget)
    budget -= len(points)
    if budget < 0:
        return f"Too many points overall (limit {MAX_TOTAL_POINTS}).", budget
    for index, p in enumerate(points):
        # Non-object entries used to be skipped (round 2, #6), and coordinates
        # used to be optional (round 6, #1) — so {} and {"x": 10} were "valid"
        # while every renderer dereferences p.x/p.y directly (drawDot, drawLine,
        # nib positioning), turning them into undefined mid-canvas. Both editors
        # always emit x and y, verified against real serialised payloads, so
        # requiring them costs nothing legitimate.
        if not isinstance(p, dict):
            return f"'{label}[{index}]' must be an object.", budget
        for axis in ("x", "y"):
            if axis not in p:
                return f"'{label}[{index}].{axis}' is required.", budget
            v = p[axis]
            # NaN/Infinity arrive via hand-built JSON and imported drafts, and
            # poison every downstream bounds calculation silently.
            if not _finite(v):
                return f"'{label}[{index}].{axis}' must be finite.", budget
            if abs(v) > COORD_LIMIT:
                return f"'{label}[{index}].{axis}' is out of range.", budget
        size = p.get("size")
        if size is not None and (not _finite(size) or size <= 0 or size > MAX_BRUSH):
            return f"'{label}' has an out-of-range brush size.", budget
    return None, budget


def _validate_stroke_groups(groups, label, stroke_count):
    """Group entries are per-stroke point counts; they must account for exactly
    the points present. Applied to BOTH the classic root-level payload and each
    frame — round 3 only covered frames, so a classic Pad payload could carry
    `strokeGroups: [{"unexpected": "object"}]` unchecked. (Review round 4, #1)

    Entries must be STRICTLY POSITIVE. v114 allowed 0 on the theory that a
    degenerate stroke could emit one; that was wrong, and checking the editors
    disproves it — Flip sets curCount=1 at stroke start (flip.js:428) before
    pushing it (flip.js:460), and the Pad only pushes under
    `currentStroke.length > 0` (app.js:610, 627). Neither can emit a zero.

    Worse, a zero is actively harmful: Flip's undo does
    `splice(strokes.length - n, n)`, so n=0 removes nothing while still consuming
    a group — a no-op undo entry. `strokeGroups: [0, 1]` passes an exact-sum check
    against one point, and `[0,0,0,0]` passes against an empty frame, which would
    let a crafted payload plant thousands of dead undo steps.
    (Review round 5, #1)
    """
    if groups is None:
        # Optional only for an empty strokes array. Otherwise the stroke
        # boundaries that undo and reconstruction depend on would simply be
        # absent, which a crafted payload could do deliberately. Both editors
        # always serialise the array. (Review round 6, #2)
        if stroke_count == 0:
            return None
        return f"'{label}' is required when its strokes array contains points."
    if not isinstance(groups, list):
        return f"'{label}' must be a list."
    if len(groups) > MAX_GROUPS_PER_FRAME:
        return f"'{label}' has too many entries."
    total = 0
    for index, value in enumerate(groups):
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            return f"'{label}[{index}]' must be a positive whole number of points."
        total += value
        if total > stroke_count:
            return f"'{label}' describes more points than its strokes array."
    if total != stroke_count:
        return (f"'{label}' accounts for {total} points, but the strokes array "
                f"contains {stroke_count}.")
    return None


def _validate_payload_complexity(payload):
    """Bytes are capped elsewhere; this caps STRUCTURE. Returns an error or None."""
    cs = payload.get("canvasSize")
    if cs is not None:
        # "huge", [], {}, and half-specified objects used to pass. The client
        # ignores them, but these are public persisted payloads and the schema
        # should mean something. (Review round 6, #8)
        if not isinstance(cs, dict):
            return "'canvasSize' must be an object."
        missing = {"cssWidth", "cssHeight"} - set(cs)
        if missing:
            return "'canvasSize' must contain cssWidth and cssHeight."
        for key in ("cssWidth", "cssHeight"):
            v = cs.get(key)
            # Pixel counts, so whole numbers only — 0.5 and 4095.75 were
            # accepted before and left the client to coerce. (Review round 4, #6)
            if isinstance(v, bool) or not isinstance(v, int) or v < 1 or v > MAX_CANVAS_EDGE:
                return (f"'canvasSize.{key}' must be a whole number between 1 and "
                        f"{MAX_CANVAS_EDGE}.")
    budget = MAX_TOTAL_POINTS
    root_strokes = payload.get("strokes", [])
    err, budget = _validate_points(root_strokes, "strokes", budget)
    if err:
        return err
    if isinstance(root_strokes, list):
        err = _validate_stroke_groups(payload.get("strokeGroups"), "strokeGroups",
                                      len(root_strokes))
        if err:
            return err
    frames = payload.get("frames")
    if frames is None:
        return None
    if not isinstance(frames, list):
        return "'frames' must be a list."
    if len(frames) > MAX_FRAMES:
        return f"At most {MAX_FRAMES} frames are allowed (got {len(frames)})."
    for i, frame in enumerate(frames):
        # Non-dict entries used to be skipped in silence by the media walker.
        if not isinstance(frame, dict):
            return f"'frames[{i}]' must be an object."
        frame_strokes = frame.get("strokes", [])
        err, budget = _validate_points(frame_strokes, f"frames[{i}].strokes", budget)
        if err:
            return err
        if isinstance(frame_strokes, list):
            err = _validate_stroke_groups(frame.get("strokeGroups"),
                                          f"frames[{i}].strokeGroups", len(frame_strokes))
            if err:
                return err
        hold = frame.get("hold")
        if hold is not None:
            # Integer only — fractional holds are not a supported concept and the
            # finite-range check alone allowed 1.5. (Review round 2, #6)
            if isinstance(hold, bool) or not isinstance(hold, int):
                return f"'frames[{i}].hold' must be a whole number."
            if hold < 1 or hold > MAX_HOLD:
                return f"'frames[{i}].hold' must be between 1 and {MAX_HOLD}."
    return None


def _validate_payload_media(payload):
    # First error wins; returns None when everything is acceptable.
    for value, kind, cap, label in _iter_media_items(payload):
        err = _validate_media_data_url(value, kind, cap, label)
        if err:
            return err
    return None


_CSP_KEYWORD_SOURCES = {"'self'", "'none'"}
_LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}


def _normalise_origin(token):
    parsed = urlsplit(token)
    host = parsed.hostname or ""
    if ":" in host:                      # IPv6 literals need their brackets back
        host = f"[{host}]"
    port = f":{parsed.port}" if parsed.port is not None else ""
    return f"{parsed.scheme}://{host}{port}"


def _is_bare_origin(token):
    """True for scheme://host[:port] and nothing else.

    Round 2 checked a prefix and looked for '/' in the remainder, which let
    ?query, #fragment, user@host and :not-a-port through — several of which
    produce an invalid CSP source expression rather than a safe startup failure.
    Parsed structurally now. Wildcard hosts (https://*.example.com) are valid CSP
    source expressions but are NOT origins, and the variable is named
    EMBED_ORIGINS, so they are rejected as the less surprising policy.
    (Review round 3, #3)
    """
    parsed = urlsplit(token)
    if parsed.scheme not in ("https", "http"):
        return False
    try:
        host = parsed.hostname
        parsed.port                      # raises ValueError on a bad port
    except ValueError:
        return False
    if not host:
        return False
    if parsed.scheme == "http" and host not in _LOCAL_HOSTS:
        return False
    if parsed.username is not None or parsed.password is not None:
        return False
    if parsed.path not in ("", "/"):
        return False
    if parsed.query or parsed.fragment:
        return False
    if "*" in host:
        return False
    return True


def _validate_embed_origins(raw):
    """Whitespace-separated CSP source list for frame-ancestors, or ''.

    Administrator-controlled rather than user-controlled, so this is not a remote
    injection path — but a stray semicolon or comma silently produces an invalid
    or unexpectedly permissive header, which is worse than a startup failure.
    (Review round 2, #5)
    """
    raw = (raw or "").strip()
    if not raw:
        return ""
    if any(ch in raw for ch in (";", ",", "\n", "\r")):
        raise RuntimeError(
            "SKRIBL_EMBED_ORIGINS must be a space-separated list with no "
            f"semicolons, commas or newlines. Got: {raw!r}"
        )
    tokens = raw.split()
    # 'none' is a standalone source expression; combining it with origins yields a
    # policy that does not mean what the administrator intended. (Round 4, #4)
    if "'none'" in tokens and len(tokens) != 1:
        raise RuntimeError("SKRIBL_EMBED_ORIGINS value 'none' must be used alone.")
    if len(tokens) != len(set(tokens)):
        raise RuntimeError("SKRIBL_EMBED_ORIGINS contains duplicate entries.")
    normalised = []
    for token in tokens:
        if token in _CSP_KEYWORD_SOURCES:
            normalised.append(token)
            continue
        if not _is_bare_origin(token):
            raise RuntimeError(
                f"SKRIBL_EMBED_ORIGINS entry {token!r} must be 'self', 'none', or a "
                "bare origin scheme://host[:port] — https, or http only for "
                "localhost/127.0.0.1/[::1]. No path, query, fragment, userinfo or "
                "wildcard host."
            )
        normalised.append(_normalise_origin(token))
    # Canonical form is emitted, not the raw token: one representation for
    # capitalisation, IPv6 brackets, default ports and trailing slashes, so what
    # lands in the header is always a bare origin. (Round 4, #5)
    if len(normalised) != len(set(normalised)):
        raise RuntimeError("SKRIBL_EMBED_ORIGINS contains duplicate origins.")
    return " ".join(normalised)


def create_app():
    app = Flask(__name__)

    # SECRET_KEY: never fall back to a shared, guessable constant. Require it in
    # production (Render sets RENDER=true); in local/dev generate a strong random
    # per-process key so `flask run` still works without configuration.
    secret_key = os.environ.get("SECRET_KEY")
    if not secret_key:
        in_production = bool(os.environ.get("RENDER")) or os.environ.get("FLASK_ENV") == "production"
        if in_production:
            raise RuntimeError("SECRET_KEY must be set in production.")
        secret_key = secrets.token_urlsafe(32)
    app.config["SECRET_KEY"] = secret_key

    database_url = os.environ.get("DATABASE_URL", "sqlite:///skribl_demo.db")

    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    elif database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql+psycopg://", 1)

    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    # Free-tier Postgres drops idle connections; pre_ping checks liveness and
    # transparently reconnects instead of erroring on the first stale request.
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {"pool_pre_ping": True}
    app.config["MAX_CONTENT_LENGTH"] = _env_int("MAX_CONTENT_LENGTH", 25_000_000, minimum=1024)

    db.init_app(app)

    # A payload over MAX_CONTENT_LENGTH makes Flask raise 413 before the view
    # runs. Return JSON (not Flask's raw HTML page) so the post composer's error
    # path — which reads {error} off a 4xx body — can show an actionable message
    # instead of a bare "rejected (413)". The composer stays open on error, so
    # the user can drop the photo / shorten the loop and retry.
    @app.errorhandler(413)
    def _payload_too_large(_error):
        return jsonify({
            "error": "This Skribl is too large to post. Try a smaller photo or a shorter audio loop."
        }), 413

    @app.get("/")
    def home():
        return render_template("skribl_editor.html")

    @app.get("/skribl-pad")
    def skribl_editor():
        return render_template("skribl_editor.html")

    @app.get("/flip")
    def skribl_flip():
        # Flip Mode — the frame-by-frame animation editor (standalone page for now;
        # folds into the pad as an in-app mode in a later phase).
        return render_template("skribl_flip.html")

    @app.get("/s/<public_id>")
    def skribl_player(public_id):
        # Server-render Open Graph / Twitter card metadata so shared links unfurl
        # with the Skribl's title + caption — social scrapers don't run the client
        # JS that fills those in. The lookup is best-effort: on a missing post or a
        # transient DB error we fall back to generic tags and still render the same
        # shell, so the existing client flow (which handles missing/invalid) is
        # unchanged. This route stays render-always; it never 404s the page.
        title = caption = None
        try:
            post = None
            if _valid_public_id(public_id):
                post = SkriblPost.query.filter_by(public_id=public_id).first()
            if post is not None:
                title, caption = post.title, post.caption
        except Exception:
            try:
                db.session.rollback()
            except Exception:
                pass
        og_title, og_description = _og_meta(title, caption)
        return render_template(
            "skribl_player.html",
            public_id=public_id,
            og_title=og_title,
            og_description=og_description,
            # Per-Skribl card: the card route serves the drawing's own thumbnail
            # (stored at post time) and falls back to the static branded card on a
            # miss, so this URL always resolves — and being unique per id, it also
            # stops every shared link from unfurling with the same generic image.
            og_image=url_for("skribl_card", public_id=public_id, _external=True),
            og_url=url_for("skribl_player", public_id=public_id, _external=True),
        )

    @app.get("/s/<public_id>/card.png")
    def skribl_card(public_id):
        # Serve the per-Skribl share-card thumbnail generated client-side at post
        # time and stored in the payload. Best-effort and render-always: on a
        # missing post, missing/'malformed thumbnail, or a transient DB error we
        # redirect to the static branded card so the og:image never 404s.
        try:
            post = None
            if _valid_public_id(public_id):
                post = SkriblPost.query.filter_by(public_id=public_id).first()
            if post is not None:
                payload = post.payload_json or {}
                thumb = payload.get("thumbnail") if isinstance(payload, dict) else None
                decoded = _decode_data_url_image(thumb)
                # Size cap: see MAX_CARD_BYTES. Oversize → static fallback below.
                if decoded is not None and len(decoded[0]) > MAX_CARD_BYTES:
                    decoded = None
                if decoded is not None:
                    data, mimetype = decoded
                    resp = app.response_class(data, mimetype=mimetype)
                    # Immutable once posted; let scrapers/CDNs cache by URL.
                    resp.headers["Cache-Control"] = "public, max-age=86400"
                    return resp
        except Exception:
            try:
                db.session.rollback()
            except Exception:
                pass
        return redirect(url_for("static", filename="skribl/og-card.png"))

    @app.post("/api/skribls")
    def create_skribl():
        # Two budgets (review #7). The ATTEMPT budget is charged on every request
        # and exists to stop request floods; the POST budget is charged only when
        # a post commits, so a burst of malformed bodies can no longer exhaust a
        # shared IP's legitimate posting allowance. Both are checked before any
        # body parsing. 429 is a 4xx, so the composer's existing error path
        # surfaces this verbatim and refuses to fake a success (see sendSkribl).
        client_ip = _client_ip()
        if _rate_limited(client_ip, "attempts"):
            return jsonify({
                "error": "Too many requests — please wait a while and try again."
            }), 429
        # NOTE: the post cap is enforced by _rate_reserve_post immediately before
        # the insert, not here. Checking here and recording after the commit left a
        # window where concurrent requests all saw room and all committed.
        # (Review round 2, #2)

        payload = request.get_json(silent=True)

        # Permissive shape validation: the frontend contract is a JSON object
        # (see serializeSkribl). Reject only gross type violations so version
        # bumps and unknown keys keep working; the request body size is already
        # capped by MAX_CONTENT_LENGTH.
        if not isinstance(payload, dict):
            return jsonify({"error": "Body must be a JSON object."}), 400
        for key in ("strokes", "strokeGroups"):
            if key in payload and not isinstance(payload[key], list):
                return jsonify({"error": f"'{key}' must be a list."}), 400
        for key in ("photo", "music", "background", "canvasSize"):
            if key in payload and payload[key] is not None and not isinstance(payload[key], dict):
                return jsonify({"error": f"'{key}' must be an object or null."}), 400
        if payload.get("baseSnapshot") is not None and not isinstance(payload.get("baseSnapshot"), str):
            return jsonify({"error": "'baseSnapshot' must be a string or null."}), 400
        # Review #1: these went straight to .strip() below, so {"title": 123}
        # raised AttributeError and returned 500 instead of a 400.
        for key in ("title", "caption"):
            value = payload.get(key)
            if value is not None and not isinstance(value, str):
                return jsonify({"error": f"'{key}' must be a string or null."}), 400
        # Review #2/#8: structure is capped BEFORE the media walk, so the walk can
        # safely visit every frame without an arbitrary cutoff.
        complexity_error = _validate_payload_complexity(payload)
        if complexity_error:
            return jsonify({"error": complexity_error}), 400
        # Media: type + per-item size caps. See _validate_payload_media. This is
        # the only place a data URL is vetted before it lands in the JSON column.
        media_error = _validate_payload_media(payload)
        if media_error:
            return jsonify({"error": media_error}), 400
        # Frame-format Skribls carry the drawing under frames[] (a classic Skribl
        # is a 1-frame Skribl). Only a gross type check — keep unknown keys working.
        if "frames" in payload and not isinstance(payload["frames"], list):
            return jsonify({"error": "'frames' must be a list."}), 400

        title = (payload.get("title") or "Untitled Skribl").strip()[:80]
        caption = (payload.get("caption") or "").strip()[:300]
        # True only when there are actual audio bytes, whether stored top-level
        # (legacy) or inside a frame (frame-format). See _payload_has_audio.
        has_audio = _payload_has_audio(payload)

        # Retry on the rare public_id collision instead of 500-ing.
        public_id = None
        # Reserve a post slot atomically, right before the only database write.
        # Released below if no row is produced, so a failed insert doesn't burn
        # quota. This makes the single-process limiter internally correct; it is
        # still not distributed (#13). (Review round 2, #2)
        post_token = _rate_reserve_post(client_ip)
        if post_token is None:
            return jsonify({
                "error": "You're posting too fast — please wait a while and try again."
            }), 429

        # try/finally, not a single release on the id-exhaustion path: ANY other
        # exception from commit() (operational error, lost connection, disk full)
        # used to return 500 with the slot still held for the full window.
        # (Review round 3, #1)
        created = False
        try:
            for _attempt in range(5):
                candidate = secrets.token_urlsafe(8)
                post = SkriblPost(
                    public_id=candidate,
                    user_id=1,  # TODO: real current_user once auth lands (roadmap #5)
                    title=title,
                    caption=caption,
                    payload_json=payload,
                    has_audio=has_audio,
                )
                db.session.add(post)
                try:
                    db.session.commit()
                except IntegrityError:
                    db.session.rollback()
                    continue
                public_id = candidate
                created = True
                break
        except Exception:
            db.session.rollback()
            raise
        finally:
            if created:
                _rate_commit_post(post_token)      # durable now — promote it
            else:
                _rate_release_post(client_ip, post_token)

        if not created:
            return jsonify({"error": "Could not allocate a unique id; please retry."}), 503

        return jsonify({
            "id": public_id,
            "url": f"/s/{public_id}"
        }), 201

    # --- Content Security Policy ---------------------------------------------
    # Deferred until v105 for a good reason: while gifenc/mp4-muxer came from
    # jsdelivr, any workable policy needed a third-party script-src, and the app
    # also had inline <script type="module"> loaders. Vendoring both libraries
    # (v103/v104) removed the last off-origin script AND the last inline module,
    # so a genuinely strict script-src is now possible.
    #
    # What made this cheap: the templates have ZERO inline event handlers
    # (onclick=...), zero javascript: URLs, and only two inline <script> blocks
    # (the SKRIBL_MODE config in the editor and player). Those two get a
    # per-request nonce. Note that a nonce DISABLES 'unsafe-inline' for scripts
    # in CSP2+ browsers, which is exactly what we want — but it also means any
    # inline handler added later will silently stop firing. verify_csp.py fails
    # loudly if one appears.
    #
    # Deliberate looseness, each load-bearing:
    #   style-src 'unsafe-inline'  — 51 style="..." attributes across the
    #       templates. Style ATTRIBUTES cannot be nonced (a nonce only covers
    #       <style> blocks), so this is required until they're refactored. Much
    #       lower risk than inline script, and there is no user-controlled style
    #       injection surface here.
    #   connect-src data:          — NOT optional. app.js fetches data: URLs
    #       directly (`fetch(data.music.data)`, `fetch(built.dataUrl)`) to get
    #       audio into an ArrayBuffer. Omitting this breaks music loading on the
    #       player and the WAV/MP4 build path, silently.
    #   img-src/media-src data: blob: — canvas toDataURL, new Audio(dataUrl),
    #       and createObjectURL for downloads and playback.
    #
    # NO frame-ancestors, on purpose. The roadmap embeds the player in an iframe
    # on skribls.net, and the previous note here warned that a blanket deny would
    # break that. Omitting the directive leaves framing unrestricted, matching the
    # existing (deliberate) absence of X-Frame-Options. Do not "harden" this
    # without checking the embed first.
    #
    # SKRIBL_CSP=off disables it; SKRIBL_CSP=report-only sends the policy as
    # Content-Security-Policy-Report-Only, so a deploy can watch for violations
    # before enforcing. Default is enforcing.
    csp_mode = os.environ.get("SKRIBL_CSP", "on").strip().lower()
    embed_origins = _validate_embed_origins(os.environ.get("SKRIBL_EMBED_ORIGINS", ""))

    @app.before_request
    def _make_csp_nonce():
        # Per-request, per-response nonce. Generated for every request (not just
        # rendered ones) so the header and the template can never disagree.
        g.csp_nonce = secrets.token_urlsafe(16)

    @app.context_processor
    def _expose_template_globals():
        return {"csp_nonce": getattr(g, "csp_nonce", ""),
                "skribl_version": SKRIBL_VERSION}

    @app.after_request
    def _security_headers(resp):
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        if csp_mode != "off":
            nonce = getattr(g, "csp_nonce", "")
            policy = "; ".join([
                "default-src 'self'",
                f"script-src 'self' 'nonce-{nonce}'",
                "style-src 'self' 'unsafe-inline'",
                "img-src 'self' data: blob:",
                "media-src 'self' data: blob:",
                "connect-src 'self' data: blob:",
                "font-src 'self'",
                "worker-src 'self' blob:",
                "base-uri 'self'",
                "form-action 'self'",
                "object-src 'none'",
            ])
            # Review #11 / round 2 #4: this used to test `path.startswith("/s/")`,
            # which also matched /s/<id>/card.png and every 404 under that prefix,
            # so error responses were left framable. Key off the matched endpoint
            # instead — only the HTML player gets the permissive treatment, and
            # only while SKRIBL_EMBED_ORIGINS is unset so an existing embed cannot
            # break on deploy. Card images and errors take the restrictive default.
            # A 404 raised INSIDE skribl_player still carries that endpoint, so the
            # endpoint alone is not enough: only a successful HTML render is the
            # embeddable thing. Errors under /s/ take the restrictive default.
            is_player = request.endpoint == "skribl_player" and resp.status_code == 200
            if is_player:
                if embed_origins:
                    policy += "; frame-ancestors " + embed_origins
            else:
                policy += "; frame-ancestors 'self'"
            header = ("Content-Security-Policy-Report-Only"
                      if csp_mode == "report-only" else "Content-Security-Policy")
            resp.headers.setdefault(header, policy)
        return resp

    @app.get("/api/skribls/<public_id>")
    def get_skribl(public_id):
        if not _valid_public_id(public_id):
            return jsonify({"error": "Skribl not found."}), 404
        post = SkriblPost.query.filter_by(public_id=public_id).first_or_404()

        # Shallow-copy so we don't mutate the SQLAlchemy-tracked JSON column
        # (which could otherwise be flushed back to the DB on this GET).
        payload = dict(post.payload_json or {})
        payload["title"] = post.title
        payload["caption"] = post.caption
        # The share-card thumbnail is served by /s/<id>/card.png, so the player
        # doesn't need it in the envelope — drop it to keep the GET lean.
        payload.pop("thumbnail", None)

        return jsonify({
            "id": post.public_id,
            "title": post.title,
            "caption": post.caption,
            "hasAudio": post.has_audio,
            "createdAt": post.created_at.isoformat(),
            "author": {
                "id": post.user_id,
                "username": "demo-user"
            },
            "skribl": payload
        })

    @app.cli.command("init-db")
    def init_db():
        db.create_all()
        print("Initialized database.")

    return app


app = create_app()
