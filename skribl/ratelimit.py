"""Rate limiting: in-memory (per-process) and database-backed (shared).

TRANSACTION OWNERSHIP (see docs/INTEGRATION.md). The db backend runs on its OWN
sessionmaker, opened against the same engine as the host's session but never
sharing its transaction. This is load-bearing twice over:

  1. Accounting must survive the request failing. An attempt is charged whether
     or not the request goes on to succeed — that is the flood protection — so
     the charge cannot ride in a transaction the host may roll back. With the
     old shared session, a host rolling back a failed request erased the very
     rows that were supposed to record the failure.

  2. The limiter must not commit the host's work. A commit on the shared
     session here used to commit whatever the HOST had pending on it —
     the outside review proved a host's uncommitted row was made durable by a
     limiter bookkeeping commit. The limiter now cannot reach the host's
     transaction at all.

The sessionmaker is app-local (in app.extensions["skribl"]), resolved lazily
from the bound session's engine, so two Skribl apps in one process do not share
limiter state through a module global. The memory backend is untouched — it
never had a transaction to own.
"""
import hashlib
import ipaddress
import hmac
import os
import secrets
import time
from collections import deque
from datetime import datetime, timedelta, timezone
from threading import Lock

import sqlalchemy as sa
from flask import current_app, request

from .core import RATE_CLEANUP_BATCH, RATE_PENDING_TTL, _env_int
from .models import RateEvent, session

_RATE_WINDOW_SECONDS = 3600
_RATE_MAX_POSTS = _env_int("SKRIBL_RATE_MAX_POSTS", 20)


def _rate_cap(kind):
    """The cap for `kind`, APP-LOCAL where the app chose one.

    app.config["SKRIBL_RATE_MAX_POSTS"] / ["SKRIBL_RATE_MAX_ATTEMPTS"] win over
    the process-wide env values, so two Skribl apps in one process can run
    different budgets — the env read at import time was a per-process seam
    wearing per-app clothing (outside review, P1). Outside any app context the
    env values stand, exactly as before.
    """
    name = ("SKRIBL_RATE_MAX_ATTEMPTS" if kind == "attempts"
            else "SKRIBL_RATE_MAX_POSTS")
    default = _RATE_MAX_ATTEMPTS if kind == "attempts" else _RATE_MAX_POSTS
    try:
        val = current_app.config.get(name)
    except RuntimeError:            # outside any application context
        return default
    if val is None:
        return default
    try:
        return max(1, int(val))
    except (TypeError, ValueError):
        return default
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
    cap = _rate_cap(kind)
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


# Fallback for code running outside an application context, keyed by engine so
# two engines never share a sessionmaker even without an app to hang one on.
_rate_sessionmakers = {}


def _rate_sessionmaker():
    """The limiter's own sessionmaker: same engine as the host, separate
    transactions. App-local first; engine-keyed module fallback second."""
    engine = session().get_bind()
    ext = None
    try:
        ext = current_app.extensions.get("skribl")
    except RuntimeError:            # outside any application context
        pass
    if ext is not None:
        sm = ext.get("rate_sessionmaker")
        if sm is None or ext.get("rate_engine") is not engine:
            sm = sa.orm.sessionmaker(bind=engine)
            ext["rate_sessionmaker"] = sm
            ext["rate_engine"] = engine
        return sm
    sm = _rate_sessionmakers.get(id(engine))
    if sm is None:
        sm = _rate_sessionmakers[id(engine)] = sa.orm.sessionmaker(bind=engine)
    return sm


def _db_lock_identity(s, key_hash):
    """Serialise the reserve-then-count window, per identity.

    THE BUG THIS FIXES. Reservation was: INSERT, COMMIT, COUNT, withdraw if over.
    Between the commit and the count, other requests commit their own rows. With
    twelve concurrent posts against a quota of two, all twelve inserts land
    before any count runs, every request sees 12 > 2, and every request
    withdraws — admitting ZERO instead of two.

    SQLite hid this completely: its single-writer lock serialises the commits, so
    requests effectively queue and the count each one sees is correct. On
    PostgreSQL, which actually runs them in parallel, the window is wide open.
    That is why `RateEvent`'s docstring said "verified under SQLite and threads;
    NOT yet verified on PostgreSQL across processes" — the guarantee did not hold.

    A transaction-scoped advisory lock serialises only requests sharing an
    identity, so unrelated posters never contend. It is released automatically on
    commit or rollback, including if the process dies mid-request. On SQLite this
    is a no-op because writes are already serialised.

    `s` is a LIMITER session (from _rate_sessionmaker), never the host's: the
    lock must release when the limiter's accounting transaction ends, not hang
    on until whenever the host decides to commit the request.
    """
    if s.get_bind().dialect.name != "postgresql":
        return
    # pg_advisory_xact_lock takes a signed 64-bit key; derive one from the
    # identity hash so the lock is per-poster, not global.
    n = int.from_bytes(hashlib.sha256(key_hash.encode()).digest()[:8],
                       "big", signed=True)
    s.execute(sa.text("SELECT pg_advisory_xact_lock(:n)"), {"n": n})


def _db_rate_count(s, bucket, key_hash):
    # Committed rows count for the whole window; pending ones only while they are
    # still plausibly in flight, so an abandoned reservation ages out fast.
    pending_cutoff = datetime.now(timezone.utc) - timedelta(seconds=RATE_PENDING_TTL)
    return (s.query(RateEvent)
            .filter(RateEvent.bucket == bucket,
                    RateEvent.key_hash == key_hash,
                    RateEvent.created_at >= _rate_cutoff(),
                    sa.or_(RateEvent.state == "committed",
                           RateEvent.created_at >= pending_cutoff))
            .count())


def _db_rate_limited(ip, kind):
    cap = _rate_cap(kind)
    key_hash = _rate_key(ip)
    with _rate_sessionmaker()() as s:
        if kind != "attempts":
            return _db_rate_count(s, kind, key_hash) >= cap
        _db_lock_identity(s, key_hash)
        row = RateEvent(bucket=kind, key_hash=key_hash)
        s.add(row)
        # flush, NOT commit: the row gets its id and participates in our own
        # count, while the transaction (and the advisory lock with it) stays
        # open until the decision is made. Committing here is what opened the
        # race.
        s.flush()
        if _db_rate_count(s, kind, key_hash) > cap:
            s.delete(row)
            s.commit()
            return True
        s.commit()
        return False


def _db_rate_reserve_post(ip):
    key_hash = _rate_key(ip)
    with _rate_sessionmaker()() as s:
        _db_lock_identity(s, key_hash)
        row = RateEvent(bucket="posts", key_hash=key_hash, state="pending")
        s.add(row)
        s.flush()
        if _db_rate_count(s, "posts", key_hash) > _rate_cap("posts"):
            s.delete(row)
            s.commit()
            return None
        s.commit()
        token = row.id
        # Opportunistic cleanup, BOUNDED. An unbounded delete inside a user
        # request can hold locks and spike latency for whoever happens to
        # trigger it after a quiet period. Capped per request; the remainder is
        # collected by subsequent requests. A scheduled job is still the better
        # answer at scale. (Review round 7, #8)
        if secrets.randbelow(50) == 0:
            stale = (s.query(RateEvent.id)
                     .filter(RateEvent.created_at < _rate_cutoff())
                     .limit(RATE_CLEANUP_BATCH).all())
            if stale:
                s.query(RateEvent).filter(
                    RateEvent.id.in_([r[0] for r in stale])).delete(
                    synchronize_session=False)
                s.commit()
        return token


def _db_rate_release_post(ip, token):
    if token is None:
        return
    with _rate_sessionmaker()() as s:
        s.query(RateEvent).filter(RateEvent.id == token).delete()
        s.commit()


def _db_rate_commit_post(token):
    # Promote the reservation, on the limiter's own transaction. This used to
    # ride in the SAME transaction as the post insert so a bookkeeping failure
    # could not 500 a request whose post was already durable. The ordering now
    # provides the same guarantee the other way round: promotion happens BEFORE
    # the request's transaction commits, so a promotion failure aborts the
    # request while the post is still pending — and if the request then fails,
    # a committed 'posts' charge for a post that never landed is the
    # conservative outcome the contract allows (a failed request still counts).
    if token is None:
        return
    with _rate_sessionmaker()() as s:
        updated = (s.query(RateEvent)
                   .filter(RateEvent.id == token)
                   .update({"state": "committed"}))
        if updated != 1:
            raise RuntimeError("Post rate-limit reservation disappeared before commit.")
        s.commit()


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
        if len(bucket) >= _rate_cap("posts"):
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
