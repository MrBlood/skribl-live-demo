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
import weakref
try:
    import fcntl                      # POSIX advisory file locks
except ImportError:                   # pragma: no cover - non-POSIX host
    fcntl = None
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


def _trusted_proxies():
    """Proxy depth, app-local where the app chose (config > env) — v201
    review, F7: caps/backend/HMAC went app-local while proxy topology stayed a
    process constant, so two apps behind different ingress paths could not
    both be configured correctly."""
    try:
        val = current_app.config.get("SKRIBL_TRUSTED_PROXIES")
    except RuntimeError:
        val = None
    if val is None:
        return _TRUSTED_PROXIES
    try:
        return max(0, int(val))
    except (TypeError, ValueError):
        return _TRUSTED_PROXIES
# Module-level FALLBACK only, for code running outside any application
# context. Inside an app, buckets and lock live in app.extensions["skribl"]
# (v201 review, F2): the module-global dict had no app identity in its key, so
# two applications in one process pooled attempt/post counts per client IP —
# fifty attempts against permissive app A instantly exhausted strict app B's
# budget for the same visitor. Same cross-app coupling class the session and
# db-limiter sessionmaker fixes removed; the memory backend now matches.
_rate_buckets = {}
_rate_lock = Lock()


def _mem_state():
    """(buckets, lock) for the current app, or the module fallback."""
    try:
        ext = current_app.extensions.setdefault("skribl", {})
    except RuntimeError:
        return _rate_buckets, _rate_lock
    if "rate_buckets" not in ext:
        ext["rate_buckets"] = {}
        ext["rate_lock"] = Lock()
    return ext["rate_buckets"], ext["rate_lock"]


def _client_ip():
    # Trusting X-Forwarded-For unconditionally let any caller pick a fresh
    # rate-limit key per request AND stuff _rate_buckets with attacker-chosen
    # keys. It is now consulted ONLY when SKRIBL_TRUSTED_PROXIES declares how many
    # proxies sit in front of us, and we take the entry that many hops from the
    # RIGHT — everything further left is client-supplied and worthless. (Review #3)
    trusted = _trusted_proxies()
    if trusted > 0:
        fwd = request.headers.get("X-Forwarded-For", "")
        if fwd:
            parts = [p.strip() for p in fwd.split(",") if p.strip()]
            if len(parts) >= trusted:
                candidate = parts[-trusted]
                # A trusted but misconfigured edge can still forward junk, which
                # would land straight in the bucket map as an attacker-chosen key.
                # Handles IPv6 too. (Review round 2, #3)
                try:
                    return str(ipaddress.ip_address(candidate))
                except ValueError:
                    return request.remote_addr or "unknown"
    return request.remote_addr or "unknown"


def _rate_limited(ip, kind="posts"):
    if _rate_backend() == "db":
        return _db_rate_limited(ip, kind)
    # kind='attempts' is charged on every request (flood protection); kind='posts'
    # is charged only when a post commits, via _rate_record_post. Separate buckets
    # so a burst of 400s cannot exhaust the posting allowance. (Review #7)
    # Only 'attempts' goes through here now; post slots are reserved atomically by
    # _rate_reserve_post. Entries are timestamps here and (timestamp, token) pairs
    # in the posts bucket, so read element 0 either way.
    cap = _rate_cap(kind)
    now = time.monotonic()
    buckets, lock = _mem_state()
    with lock:
        bucket = buckets.setdefault((kind, ip), deque())
        while bucket and now - (bucket[0][0] if isinstance(bucket[0], tuple) else bucket[0]) > _RATE_WINDOW_SECONDS:
            bucket.popleft()
        if len(bucket) >= cap:
            return True
        if kind == "attempts":
            bucket.append(now)
        # Opportunistic cleanup so the dict can't grow without bound: expire
        # aged entries in every bucket, then drop the empty buckets.
        if len(buckets) > 1000:
            for bkey, q in list(buckets.items()):
                while q and now - (q[0][0] if isinstance(q[0], tuple) else q[0]) > _RATE_WINDOW_SECONDS:
                    q.popleft()
                if not q:
                    del buckets[bkey]
        return False


# Process-wide defaults, resolved at import as before. What is NEW (v200
# follow-up review, F5): both are overridable PER APP through app.config, and
# the HMAC fallback reads the app's configured SECRET_KEY — v200's env-only
# read meant a host that set app.config["SECRET_KEY"] in Python (the way the
# integration guide shows) still could not enable the db backend without
# duplicating the secret into the process environment before importing Skribl.
_RATE_BACKEND = os.environ.get("SKRIBL_RATE_BACKEND", "memory").strip().lower()
if _RATE_BACKEND not in ("memory", "db"):
    raise RuntimeError("SKRIBL_RATE_BACKEND must be 'memory' or 'db'.")

# A dedicated key, NOT SECRET_KEY: rotating the session secret would otherwise
# silently reset every quota as a side effect. Falls back to SECRET_KEY so an
# existing deploy keeps working. The db backend refuses to OPERATE without one
# of them — with a public default salt the IPv4 space is trivially
# precomputed, which would make the hashing decorative. (Review round 7, #9;
# the check moved from import time to first use, where app config is visible.)
_RATE_HMAC_KEY = (os.environ.get("SKRIBL_RATE_HMAC_KEY")
                  or os.environ.get("SECRET_KEY") or "")


def _rate_backend():
    """'memory' or 'db', app-local where the app chose (config > env)."""
    try:
        val = current_app.config.get("SKRIBL_RATE_BACKEND")
    except RuntimeError:
        val = None
    val = (val or _RATE_BACKEND).strip().lower()
    if val not in ("memory", "db"):
        raise RuntimeError("SKRIBL_RATE_BACKEND must be 'memory' or 'db'.")
    return val


def _rate_hmac_key():
    """The identity-hash key: explicit app config > env > app SECRET_KEY > env
    SECRET_KEY. Raises on the db backend with no key at all."""
    cfg_key = cfg_secret = None
    try:
        cfg_key = current_app.config.get("SKRIBL_RATE_HMAC_KEY")
        cfg_secret = current_app.config.get("SECRET_KEY")
    except RuntimeError:
        pass
    key = (cfg_key or os.environ.get("SKRIBL_RATE_HMAC_KEY")
           or cfg_secret or os.environ.get("SECRET_KEY") or b"")
    if not key:
        raise RuntimeError(
            "SKRIBL_RATE_HMAC_KEY (or SECRET_KEY) is required when "
            "SKRIBL_RATE_BACKEND=db — the stored identity hash needs a "
            "private key.")
    return key


def _rate_key(ip):
    # Flask supports SECRET_KEY as str OR bytes (v201 review, F3): the str
    # assumption made the first db-limited request of a bytes-secret host die
    # in AttributeError. Anything else is a configuration error, said plainly.
    key = _rate_hmac_key()
    if isinstance(key, str):
        key = key.encode("utf-8")
    elif not isinstance(key, bytes):
        raise RuntimeError("SKRIBL_RATE_HMAC_KEY/SECRET_KEY must be str or "
                           f"bytes, got {type(key).__name__}.")
    return hmac.new(key, str(ip).encode(), hashlib.sha256).hexdigest()


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
            sm = _make_rate_sessionmaker(engine)
            ext["rate_sessionmaker"] = sm
            ext["rate_engine"] = engine
        return sm
    sm = _rate_sessionmakers.get(id(engine))
    if sm is None:
        sm = _rate_sessionmakers[id(engine)] = _make_rate_sessionmaker(engine)
    return sm


def _bounded(s):
    """Bound THIS limiter session's SQLite lock wait, then return it.

    pysqlite's default busy timeout is ~5 seconds. The limiter deliberately
    writes from its own connection while the host may hold the file's write
    lock (failed-request teardown; see routes._finish_parked_reservation), so
    an un-bounded wait turns that ordinary collision into a five-second stall
    per failed request. Session.connection() pins the connection to this
    session's transaction, so the PRAGMA governs every statement that
    follows; 200 ms is generous for a contended commit and converts the
    truly-blocked case into a fast OperationalError that the teardown
    containment logs and RATE_PENDING_TTL reconciles (v202 review, F1).
    Applied to the LIMITER's sessions only — the host engine's behaviour is
    the host's.

    v210 (v209 review F4): applied per CONNECTION, not per session. A session
    that commits and then keeps working — the reserve path does
    lock-identity, COMMIT, insert, COMMIT; the tombstone sweep commits
    mid-request — may be handed a different pooled connection after the
    commit, on which busy_timeout is pysqlite's 5 s default again. The
    original one-shot PRAGMA therefore governed the first statement group and
    silently not the second. Now every checkout of a limiter-engine
    connection is bounded by an engine-level listener, installed once per
    engine, so it cannot be forgotten by a caller and cannot lapse across a
    commit. The direct PRAGMA below is kept as belt-and-braces for the very
    first statement on a connection that pre-dates the listener."""
    conn = s.connection()
    if conn.dialect.name == "sqlite":
        _bound_engine(conn.engine)
        conn.exec_driver_sql("PRAGMA busy_timeout=200")
    return s


_bounded_engines = weakref.WeakSet()


def _bound_engine(engine):
    """Attach the busy_timeout bound at checkout, once per limiter engine.

    'checkout' fires on every pool checkout, so a session that commits and
    continues on a fresh connection is bounded again without anyone having
    to remember to call _bounded() a second time.
    """
    if engine in _bounded_engines:
        return
    _bounded_engines.add(engine)

    @sa.event.listens_for(engine, "checkout")
    def _bound_on_checkout(dbapi_conn, connection_record, connection_proxy):
        try:
            cur = dbapi_conn.cursor()
            cur.execute("PRAGMA busy_timeout=200")
            cur.close()
        except Exception:
            pass


def _make_rate_sessionmaker(engine):
    return sa.orm.sessionmaker(bind=engine)


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
    That is why `RateEvent`'s docstring used to say "verified under SQLite and
    threads; NOT yet verified on PostgreSQL across processes" — the guarantee
    did not hold. (It no longer says that: verify_postgres.py has proven it
    across four gunicorn worker processes since v211, and the docstring was
    corrected in v225 after an outside reviewer believed the stale version.)

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


# ---- releases that could not be delivered --------------------------------
# v207 review F2, owner decision: option (a) — a failed post must not also
# cost you quota.
#
# THE SHAPE OF THE BUG. The failure path already RELEASES the slot: on a
# failed request routes._finish_parked_reservation calls _rate_release_post,
# which deletes the pending row. What fails is the DELIVERY of that delete.
# Flask runs blueprint teardowns before app teardowns, so when the host's
# commit fails its rollback has not run yet and it still holds SQLite's single
# write lock; the limiter's bounded busy_timeout (see _bounded) turns the
# collision into a fast OperationalError, teardown logs it, and the row stays
# 'pending' — counting against that poster until RATE_PENDING_TTL. With
# SKRIBL_RATE_MAX_POSTS=1 that is a full lockout, for two minutes, because a
# post of OURS failed.
#
# WHY NOT JUST RETRY THE WRITE. The write is failing precisely because another
# writer holds the file. A second attempt is the same coin flip, so it cannot
# make immediate retry MECHANICALLY true — which is the contract the owner
# chose. The release is therefore recorded where no writer is needed, in
# process memory, and _db_rate_count() subtracts tombstoned ids from the
# count. The row itself is deleted by the next request that can get the
# writer (_sweep_tombstones), so the store is a deferral, not a shadow ledger.
#
# SCOPE, stated rather than implied. This makes immediate retry mechanically
# true WITHIN THE PROCESS THAT TOOK THE RESERVATION — the same scope the
# reservation itself claims (_rate_reserve_post: internally correct
# single-process, explicitly not distributed, #13). With several workers on
# one SQLite file another worker still counts the row until it is swept or
# ages out, i.e. exactly the v208 behaviour: never worse, better in the
# single-process case that is the SQLite deployment. Entries older than
# RATE_PENDING_TTL are dropped, because past that the row has stopped
# counting as pending and the tombstone has nothing left to do.
#
# INVARIANT THIS DEPENDS ON — read before adding a deleter. RateEvent.id is a
# plain INTEGER PRIMARY KEY, i.e. SQLite's rowid, and SQLite REUSES rowids once
# the highest row is gone. An id-keyed tombstone whose row had vanished could
# therefore silently exempt somebody else's new reservation. It cannot happen
# today because a tombstoned row has exactly one deleter: _sweep_tombstones,
# which drops the tombstone in the same breath. The stale janitor cannot reach
# it inside the tombstone's life (it deletes rows older than the one-hour
# window; tombstones die at RATE_PENDING_TTL, 120 s), and a release that
# SUCCEEDS never tombstones. Any new code that deletes pending rows must drop
# the matching tombstone too, or key the store on something SQLite does not
# recycle. Pinned in verify_txcontract.
_rate_tombstones = {}
_tombstone_lock = Lock()


def _tombstone_store(engine=None):
    """The dead-reservation map for this app/engine.

    Resolved exactly like _rate_sessionmaker — app-local first, engine-keyed
    module fallback — so two Skribl apps in one process never subtract each
    other's ids (row ids are only unique within a database).
    """
    if engine is None:
        engine = session().get_bind()
    try:
        ext = current_app.extensions.get("skribl")
    except RuntimeError:            # outside any application context
        ext = None
    if ext is not None:
        store = ext.get("rate_tombstones")
        if store is None or ext.get("rate_tombstone_engine") is not engine:
            store = ext["rate_tombstones"] = {}
            ext["rate_tombstone_engine"] = engine
        return store
    return _rate_tombstones.setdefault(id(engine), {})


def _tombstone_add(token, engine=None):
    store = _tombstone_store(engine)
    with _tombstone_lock:
        store[token] = time.monotonic()


def _tombstone_ids(store):
    """Live tombstones, pruning any that have outlived the pending TTL."""
    now = time.monotonic()
    with _tombstone_lock:
        for tok, at in list(store.items()):
            if now - at > RATE_PENDING_TTL:
                del store[tok]
        return list(store)


# ---- durable release journal (SQLite only) -----------------------------
# v211 (v210 review F3, owner: option A — durable, uniform). The in-memory
# tombstone is process-local: another worker on the same SQLite file, or this
# process after a restart, does not have it and counts the stranded row
# until sweep or TTL. The durable record must NOT be another write to the same
# SQLite database — the whole reason we are here is that that write failed
# because a host transaction holds the single writer, and a second statement
# against the same file is F2 under a different name. So the record goes to a
# SIDECAR JOURNAL next to the database file: an append of one line, which
# needs no database lock and survives the process. Any worker's next
# reservation — the moment it holds a writer of its own — reads the journal,
# sweeps those ids, and truncates it. Crash semantics: an append that did not
# land is a release that will age out at TTL (v208 behaviour, never worse);
# an append that landed is applied by whoever next reserves, in any process.
# The journal is SQLite-only: PostgreSQL's release write does not collide, and
# the cross-worker guarantee there is pinned live in verify_postgres.
#
# APPEND AND TAKE MUST NOT INTERLEAVE. take() reads the whole file and then
# truncates it; without a lock, an append that lands between the read and the
# truncate is discarded UNREAD — that release record is lost and its pending row
# counts against the quota until TTL, producing false 429s. (Outside review of
# v264, #3.) An exclusive advisory lock held across the whole of each append and
# each take serialises them, so every appended line is read by exactly one take
# before any truncate. The lock is on a sidecar `.lock` file, not the journal
# itself, so a truncate can never race a lock held on the fd being truncated.
def _journal_lock_path(engine):
    p = _journal_path(engine)
    return (p + ".lock") if p else None


class _JournalLock:
    """Exclusive advisory lock for the duration of a with-block. A no-op where
    fcntl is unavailable (non-POSIX) or the lock file cannot be opened, which
    degrades to the previous best-effort behaviour rather than failing a
    release."""
    def __init__(self, engine):
        self._fh = None
        if fcntl is None:
            return
        path = _journal_lock_path(engine)
        if not path:
            return
        try:
            self._fh = open(path, "a+")
        except OSError:
            self._fh = None

    def __enter__(self):
        if self._fh is not None:
            try:
                fcntl.flock(self._fh.fileno(), fcntl.LOCK_EX)
            except OSError:
                pass
        return self

    def __exit__(self, *exc):
        if self._fh is not None:
            try:
                fcntl.flock(self._fh.fileno(), fcntl.LOCK_UN)
            finally:
                self._fh.close()
                self._fh = None
        return False


def _journal_path(engine):
    try:
        if engine.dialect.name != "sqlite":
            return None
        db = engine.url.database
        if not db or db == ":memory:":
            return None
        return db + ".rate-release.journal"
    except Exception:
        return None


def _journal_append(engine, token):
    path = _journal_path(engine)
    if not path:
        return False
    try:
        with _JournalLock(engine):
            with open(path, "a") as fh:
                fh.write(f"{int(token)} {int(time.time())}\n")
                fh.flush()
                os.fsync(fh.fileno())
        return True
    except Exception:
        return False


def _journal_peek(engine):
    """Non-truncating read of live journal ids (for counting)."""
    path = _journal_path(engine)
    if not path or not os.path.exists(path):
        return []
    ids, cutoff = [], int(time.time()) - int(RATE_PENDING_TTL)
    try:
        with open(path) as fh:
            for line in fh:
                parts = line.split()
                if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit() and int(parts[1]) >= cutoff:
                    ids.append(int(parts[0]))
    except Exception:
        return []
    return ids


def _journal_take(engine):
    """Read and TRUNCATE the journal; return the live ids it held. Entries
    older than RATE_PENDING_TTL are dropped (the row has stopped counting as
    pending anyway). Truncating before sweeping is safe: a sweep that then
    fails leaves the ids in this process's memory tombstone and they are
    re-journaled by the next failed release or simply age out — never
    counted against anyone in the meantime, because they are also added to
    the in-memory store below."""
    path = _journal_path(engine)
    if not path or not os.path.exists(path):
        return []
    ids, cutoff = [], int(time.time()) - int(RATE_PENDING_TTL)
    try:
        with _JournalLock(engine):
            with open(path, "r+") as fh:
                for line in fh:
                    parts = line.split()
                    if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit() and int(parts[1]) >= cutoff:
                        ids.append(int(parts[0]))
                fh.seek(0)
                fh.truncate()
    except Exception:
        return []
    return ids


def _sweep_tombstones(s):
    """Delete tombstoned rows now that this session HAS a writer.

    Best-effort and bounded, for the same reason the stale-row janitor below
    is: this runs inside somebody's request, and a janitor must never take the
    tenant's keys down with it. A failed sweep keeps the tombstones, so the
    count stays correct and the next request tries again.

    EVERYTHING is inside the guard, including reading RATE_CLEANUP_BATCH and
    resolving the store. An earlier draft sliced by RATE_CLEANUP_BATCH before
    the try and verify_review's injected-cleanup-failure pin caught it
    immediately — the reservation is already COMMITTED by the time we get
    here, so an exception escaping this function strands the very row it came
    to collect.
    """
    try:
        engine = s.get_bind()
        store = _tombstone_store(engine)
        # Apply the durable journal first: releases recorded by ANY process
        # (another worker, or this one before a restart) become this
        # process's tombstones now, so they stop counting immediately here
        # too, and get swept below while we hold a writer.
        for tok in _journal_take(engine):
            with _tombstone_lock:
                store.setdefault(tok, time.monotonic())
        dead = _tombstone_ids(store)[:RATE_CLEANUP_BATCH]
        if not dead:
            return
        s.query(RateEvent).filter(RateEvent.id.in_(dead)).delete(
            synchronize_session=False)
        s.commit()
    except Exception:
        try:
            s.rollback()
        except Exception:
            pass
        return
    with _tombstone_lock:
        for tok in dead:
            store.pop(tok, None)


def _db_rate_count(s, bucket, key_hash):
    # Committed rows count for the whole window; pending ones only while they are
    # still plausibly in flight, so an abandoned reservation ages out fast.
    pending_cutoff = datetime.now(timezone.utc) - timedelta(seconds=RATE_PENDING_TTL)
    q = (s.query(RateEvent)
         .filter(RateEvent.bucket == bucket,
                 RateEvent.key_hash == key_hash,
                 RateEvent.created_at >= _rate_cutoff(),
                 sa.or_(RateEvent.state == "committed",
                        RateEvent.created_at >= pending_cutoff)))
    # A released-but-undeletable reservation is not in flight and must not be
    # charged to anyone (F2). Only ever post reservations, so this is a no-op
    # for the attempts bucket.
    engine = s.get_bind()
    store = _tombstone_store(engine)
    # Counting runs BEFORE reserving: worker B's first request after worker
    # A's failure must not count A's stranded row, so the journal is read
    # here as well as in the sweep. Reading is a non-truncating peek.
    for tok in _journal_peek(engine):
        with _tombstone_lock:
            store.setdefault(tok, time.monotonic())
    dead = _tombstone_ids(store)
    if dead:
        q = q.filter(RateEvent.id.notin_(dead))
    return q.count()


def _db_rate_limited(ip, kind):
    try:
        return _db_rate_limited_locked(ip, kind)
    except sa.exc.OperationalError:
        # THE SAME BUG AS _db_rate_reserve_post BELOW, IN THE OTHER BUCKET, and
        # it outlived that fix by nine releases because the fix was applied one
        # function down rather than to both writers.
        #
        # v264 caught the locked store while reserving a POST slot and turned it
        # into a refusal. It did not touch this function, which charges the
        # ATTEMPTS bucket — and attempts are charged on EVERY request, before a
        # post slot is ever reserved. So the earlier fix moved the 500 rather
        # than removing it: under contention the request now dies here instead,
        # one step sooner, with the same symptom.
        #
        # Proven by the server log rather than reasoned about. The failing
        # statement's own parameters name the bucket:
        #     [parameters: ('attempts', 'ceb36866...', ..., 'committed')]
        #     sqlite3.OperationalError: database is locked
        # The harness's twelve-threads-for-two-slots test (#13b) reported
        #     [201, 201, 429, 429, 429, 500, 500, 500, 500, 500, 500, 500]
        # against an assertion demanding only 201 and 429. It passes on an idle
        # machine, which is why every local run was green while CI's loaded
        # two-core sqlite job failed on it every time.
        #
        # REFUSING IS THE SAFE DIRECTION, and it is the same one v264 chose: a
        # limiter that cannot record an attempt must not wave the attempt
        # through. Failing OPEN here would be worse than the 500 it replaces —
        # it would let anyone who can induce write contention bypass the flood
        # protection this bucket exists to provide. The cost is a poster
        # occasionally told to retry while the store is briefly contended,
        # which is exactly what 429 means, instead of being shown a server
        # error for a Skribl still safely in their browser.
        current_app.logger.warning(
            "skribl: limiter store unavailable while charging an attempt; "
            "refusing this request (429) rather than admitting an unrecorded "
            "attempt.")
        return True


def _db_rate_limited_locked(ip, kind):
    cap = _rate_cap(kind)
    key_hash = _rate_key(ip)
    with _rate_sessionmaker()() as s:
        _bounded(s)
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
    try:
        return _db_rate_reserve_post_locked(ip, key_hash)
    except sa.exc.OperationalError:
        # The store could not be written — on SQLite, essentially always
        # "database is locked" from another poster holding the write lock.
        #
        # _bounded() sets a SHORT busy_timeout precisely so this surfaces in
        # milliseconds as an exception rather than blocking. That was the
        # intended half of the design; the other half was missing. The caller
        # (routes.py: `post_token = _rate_reserve_post(client_ip)`) treats None
        # as "refused" and returns 429, but nothing translated a locked store
        # into None, so the exception propagated and Flask answered 500.
        #
        # Concurrency this heavy does not arise on a fast single machine, which
        # is why it was invisible: the harness's twelve-threads-for-two-slots
        # test passes locally. On a loaded 2-core CI runner it reproduces every
        # time, and the first CI run that ever executed reported
        #   [201, 201, 429, 429, 429, 429, 429, 429, 429, 500, 500, 500]
        # against an assertion demanding only 201 and 429.
        #
        # Refusing is the correct direction and the one the suite asks for
        # ("refuses the rest under concurrency rather than over-accepting"): a
        # limiter that cannot account for a slot must not hand one out. The
        # degradation is a poster occasionally told to try again while the
        # store is contended, which is what 429 means, instead of being shown
        # a server error for a Skribl that is still safely in their browser.
        # Quota still leaks only downward, briefly, and the log line says so.
        current_app.logger.warning(
            "skribl: limiter store unavailable while reserving a post slot; "
            "refusing this request (429) rather than granting an unaccounted "
            "slot.")
        return None


def _db_rate_reserve_post_locked(ip, key_hash):
    with _rate_sessionmaker()() as s:
        _bounded(s)
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
        # This session has a writer, which is the thing the failed release
        # lacked — so pay off any deferred releases here (F2).
        #
        # Best-effort, for the same reason the janitor below is: the slot is
        # ALREADY COMMITTED at this point and the token has not reached the
        # route. An exception escaping here would be caught by the locked-store
        # guard around this block and turned into a 429, while the committed
        # pending row went on counting against the poster until the TTL — the
        # caller would be refused for a slot it actually holds. Paying off
        # someone else's deferred release is never worth that.
        try:
            _sweep_tombstones(s)
        except Exception:
            try:
                s.rollback()
            except Exception:
                pass
        # Opportunistic cleanup, BOUNDED. An unbounded delete inside a user
        # request can hold locks and spike latency for whoever happens to
        # trigger it after a quiet period. Capped per request; the remainder is
        # collected by subsequent requests. A scheduled job is still the better
        # answer at scale. (Review round 7, #8)
        if secrets.randbelow(50) == 0:
            # STRICTLY best-effort (v200 follow-up review, F6 / v199 F15): the
            # reservation above is already COMMITTED, but the token has not
            # reached the route yet — a cleanup exception here used to escape,
            # the route never received a token to release, and the committed
            # pending row sat counting against the poster until the TTL. A
            # janitor must never take the tenant's keys down with it.
            try:
                stale = (s.query(RateEvent.id)
                         .filter(RateEvent.created_at < _rate_cutoff())
                         .limit(RATE_CLEANUP_BATCH).all())
                if stale:
                    s.query(RateEvent).filter(
                        RateEvent.id.in_([r[0] for r in stale])).delete(
                        synchronize_session=False)
                    s.commit()
            except Exception:
                try:
                    s.rollback()
                except Exception:
                    pass
        return token


def _db_rate_release_post(ip, token):
    if token is None:
        return
    try:
        with _rate_sessionmaker()() as s:
            _bounded(s)
            s.query(RateEvent).filter(RateEvent.id == token).delete()
            s.commit()
    except Exception:
        # The delete could not be delivered — on SQLite, almost always because
        # the host still holds the write lock on the failure path. The slot is
        # released in memory instead (F2, option (a)); the row goes with the
        # next sweep. RE-RAISED, not swallowed: teardown's log line saying
        # which degradation happened is load-bearing (v202 review, F1+F2), and
        # the caller already contains it.
        _tombstone_add(token)
        try:
            _journal_append(session().get_bind(), token)
        except Exception:
            pass
        raise


def _db_rate_commit_post(token):
    # Promote the reservation, on the limiter's own transaction. ORDERING (the
    # authoritative story; v202 review, F4): promotion happens in BLUEPRINT
    # TEARDOWN, after the host's before-response commit has made the post
    # durable and closed the host transaction — never mid-request, where a
    # second SQLite writer deadlocks against the host's open transaction. The
    # caller (routes._finish_parked_reservation) proves the host transaction
    # is closed before calling, and contains any exception from here: a
    # promotion failure leaves the row 'pending', which counts within
    # RATE_PENDING_TTL and then ages out. The RuntimeError below is therefore
    # a logged anomaly, not a request-visible one.
    if token is None:
        return
    with _rate_sessionmaker()() as s:
        _bounded(s)
        updated = (s.query(RateEvent)
                   .filter(RateEvent.id == token)
                   .update({"state": "committed"}))
        if updated != 1:
            raise RuntimeError("Post rate-limit reservation disappeared before commit.")
        s.commit()


def _rate_commit_post(token):
    if _rate_backend() == "db":
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
    if _rate_backend() == "db":
        return _db_rate_reserve_post(ip)
    now = time.monotonic()
    buckets, lock = _mem_state()
    with lock:
        bucket = buckets.setdefault(("posts", ip), deque())
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
    if _rate_backend() == "db":
        return _db_rate_release_post(ip, token)
    buckets, lock = _mem_state()
    with lock:
        bucket = buckets.get(("posts", ip))
        if not bucket:
            return
        for i, entry in enumerate(bucket):
            if entry[1] is token:
                del bucket[i]
                return
