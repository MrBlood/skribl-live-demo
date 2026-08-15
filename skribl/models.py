"""Skribl's three tables, and the session seam.

Decoupled from flask_sqlalchemy deliberately. These models used to be declared
on a module-level `db = SQLAlchemy()` that Skribl owned, which meant a host
application with its own `db` would have had TWO SQLAlchemy instances: two
MetaData objects, two sessions, and no shared transaction — so a Skribl post
could commit while the host's feed row rolled back.

They are now plain SQLAlchemy 2.0 declarative models on a base Skribl owns, and
the SESSION is injected. The host calls `bind_session(lambda: db.session)` with
its own session and gets one transaction across both sets of tables. Standalone,
app.py does exactly the same thing with the only SQLAlchemy instance in the tree.

`SkriblBase.metadata` is exported so a host can create or migrate these tables
with its own tooling (Alembic included) without importing Flask.
"""
import os
import weakref
from datetime import datetime, timezone

from flask import current_app

from sqlalchemy import (Boolean, CheckConstraint, Column, DateTime,
                        ForeignKey, ForeignKeyConstraint, Index, Integer, JSON,
                        String)
from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase


class _QueryProperty:
    """`Model.query`, backed by the injected session.

    flask_sqlalchemy provides this and the codebase (and the harness) used it
    throughout. Keeping it means the query sites read the same as before while
    resolving through whatever session the host owns, instead of a SQLAlchemy
    instance Skribl controls. Plain `session().query(Model)` works identically
    and is what new code should prefer.
    """

    def __get__(self, obj, cls):
        return session().query(cls)


class SkriblBase(DeclarativeBase):
    """Declarative base for Skribl's tables only — never the host's."""

    query = _QueryProperty()


class RateEvent(SkriblBase):
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

    id = Column(Integer, primary_key=True)
    bucket = Column(String(16), nullable=False)          # 'posts' | 'attempts'
    key_hash = Column(String(64), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False,
                        default=lambda: datetime.now(timezone.utc))
    # 'pending' until the post row commits, then 'committed'. A pending row that
    # is never resolved — because the process was killed between the two commits —
    # stops counting after RATE_PENDING_TTL instead of holding a slot for the full
    # hour. That closes the crash window described below. (Review round 7, #6)
    state = Column(String(10), nullable=False, default="committed")

    # Two indexes for two different access patterns: per-key counting, and the
    # time-ordered cleanup sweep, which the composite index does not serve
    # because it does not lead with created_at. (Review round 7, #8)
    __table_args__ = (
        Index("ix_rate_bucket_key_time", "bucket", "key_hash", "created_at"),
        Index("ix_rate_created_at", "created_at"),
        # A third value would count as neither pending nor committed: it would
        # hold no quota slot and never be cleaned up as one.
        CheckConstraint("state IN ('pending', 'committed')", name="ck_rate_state"),
    )


# A host may add visibility states without a Skribl migration (see
# SkriblPost.visible_to). Unknown states fail CLOSED, so a host that means one
# of its own to be readable installs a policy saying so. Returning None defers
# to the built-in rules, which keeps the host's policy to just its own states.
_VISIBILITY_POLICY = None


_POLICY_UNSET = object()   # app-local sentinel: "no per-app choice made"


def set_visibility_policy(fn, app=None):
    """Install `fn(post, viewer_id) -> True | False | None`, or None to clear.

    With `app`, the policy is APP-LOCAL — stored in app.extensions["skribl"],
    seen only by requests of that application — which is what a process
    mounting two Skribl apps needs: one host's 'draft' rules must not decide
    the other host's posts (outside review, P1: runtime seams app-local for
    both registration APIs; init_skribl(visibility_policy=...) routes here).
    Without `app`, this sets the process-wide default exactly as before, which
    every existing caller and the single-app deployment keep relying on. An
    app-local policy, including an explicit app-local None, shadows the
    module default.
    """
    global _VISIBILITY_POLICY
    if fn is not None and not callable(fn):
        raise TypeError("visibility policy must be callable or None")
    if app is not None:
        app.extensions.setdefault("skribl", {})["visibility_policy"] = fn
        return
    _VISIBILITY_POLICY = fn


def _visibility_policy():
    try:
        from flask import current_app
        local = current_app.extensions.get("skribl", {})                            .get("visibility_policy", _POLICY_UNSET)
        if local is not _POLICY_UNSET:
            return local
    except (ImportError, RuntimeError):
        pass
    return _VISIBILITY_POLICY


class SkriblPost(SkriblBase):
    __tablename__ = "skribl_posts"

    id = Column(Integer, primary_key=True)
    public_id = Column(String(32), unique=True, nullable=False, index=True)
    user_id = Column(Integer, nullable=True)
    title = Column(String(80), nullable=False)
    caption = Column(String(300), nullable=True)
    payload_json = Column(JSON, nullable=False)
    has_audio = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True),
                        default=lambda: datetime.now(timezone.utc), nullable=False)

    # Visibility, for a host that renders feeds. Deliberately a small closed set
    # rather than a boolean, because "not in the feed" and "not reachable by link"
    # are different products: an unlisted Skribl is exactly how sharing works
    # today (anyone with the URL can watch it, but it is nobody's timeline), and
    # collapsing that into public/private would break existing share links.
    #   public   — listed in feeds, reachable by link
    #   unlisted — NOT listed, reachable by link. v131's effective behaviour.
    #   private  — listed to nobody, reachable only by its author
    # DEFAULT IS "unlisted", matching the create route and the v132 migration's
    # backfill. It said "public" — so a host constructing SkriblPost directly,
    # without going through the API, would silently publish to the feed. Three
    # places state this default and all three must agree.
    visibility = Column(String(16), default="unlisted", nullable=False)

    __table_args__ = (
        # Feed reads are "this author's posts, newest first" and "the public
        # timeline, newest first". Both are covering-ish index scans with these;
        # without them a feed degrades to a full table scan the moment the table
        # is interesting, which is precisely when it must not.
        Index("ix_skribl_posts_user_created", "user_id", "created_at"),
        Index("ix_skribl_posts_visibility_created", "visibility", "created_at"),
    )

    #: Values `visibility` is allowed to take. Enforced in the API, not by a DB
    #: CHECK constraint, so a host can add its own states without a migration.
    VISIBILITIES = ("public", "unlisted", "private")

    def visible_to(self, viewer_id):
        """Can `viewer_id` (may be None) read this post at all?

        THE RULE, in one place, because it was previously enforced in exactly one
        place — the feed listing — while GET /api/skribls/<id>, the player page
        and the share-card thumbnail all returned private posts to anybody with
        the id. "Private" was a listing filter pretending to be an access control.

          public    anyone
          unlisted  anyone WITH THE LINK — deliberately readable, just not listed
          private   the author only
          anything else — the AUTHOR ONLY

        That last line is the whole point of the rewrite. VISIBILITIES is
        enforced by the API rather than a database constraint precisely so a
        host application can add its own states without a Skribl migration, and
        the rule used to read "anything that is not private is readable". A host
        adding 'draft', 'moderated', 'blocked' or 'scheduled' would therefore
        have created posts that were hidden from the feed and readable by anyone
        holding the id — a listing filter pretending to be an access control,
        which is the exact mistake this method was written to end.

        An extensible VOCABULARY needs an extensible POLICY. A host that means
        one of its own states to be readable says so, by installing a policy:

            skribl.set_visibility_policy(lambda post, viewer_id: ...)

        Returning None from that policy falls through to the rules above, so a
        host only has to describe the states it added. Defaulting to refusal
        means a new state is invisible until someone decides otherwise, rather
        than public until someone notices.
        """
        policy = _visibility_policy()
        if policy is not None:
            decided = policy(self, viewer_id)
            if decided is not None:
                return bool(decided)
        if self.visibility in ("public", "unlisted"):
            return True
        # private, and every state this package does not define
        return viewer_id is not None and self.user_id == viewer_id

    def feed_dict(self):
        """Metadata only — NO payload.

        The payload is the whole point of a Skribl and the whole cost of one: it
        carries base64 audio and images and routinely runs to megabytes. A feed
        of fifty of those is a hundred megabytes of JSON, so the list endpoint
        must never include it. The player fetches the payload for the one Skribl
        it is actually going to play.
        """
        return {
            "id": self.public_id,
            "title": self.title,
            "caption": self.caption,
            "has_audio": bool(self.has_audio),
            "user_id": self.user_id,
            "visibility": self.visibility,
            "created_at": (as_utc(self.created_at).isoformat()
                           if self.created_at else None),
        }



class SkriblIdempotency(SkriblBase):
    """One row per (author, idempotency key): the post a retry must resolve to.

    THE AMBIGUITY THIS CLOSES (outside review, P1). A POST whose response is
    lost in transit — timeout, dropped connection, proxy 502 after the commit —
    leaves the client unable to distinguish "never happened" from "happened and
    I missed the answer". Retrying then either duplicates the post or spends a
    second rate-limit slot on nothing. With an `Idempotency-Key` header, the
    retry finds this row and gets the SAME post back.

    Scoped to the AUTHOR: key_hash = sha256(user_id_or_'anon' + '|' + key), so
    one client's key can never resolve to (or block on) another's post. Rows
    ride the SAME transaction as the post they name — the host owns the commit
    (docs/INTEGRATION.md), so either both are durable or neither is, which is
    exactly the property a retry needs. A concurrent duplicate loses on the
    unique index, rolls back to its savepoint, and reads the winner's row.
    """
    __tablename__ = "skribl_idempotency"

    id = Column(Integer, primary_key=True)
    key_hash = Column(String(64), unique=True, nullable=False, index=True)
    # sha256 of the raw request body (v201 review, F4): a key names an
    # author+REQUEST, not an author+whim. Without this, reusing a key with a
    # DIFFERENT body silently replayed the old post — the editor's edited
    # retry after an ambiguous failure got a 200 for the drawing it replaced.
    # Same key + same fingerprint replays; same key + different fingerprint is
    # a 409. NULL means a pre-v202 row: replayed unconditionally, as written.
    request_fingerprint = Column(String(64), nullable=True)
    post_id = Column(Integer,
                     ForeignKey("skribl_posts.id", ondelete="CASCADE"),
                     nullable=False, index=True)
    created_at = Column(DateTime(timezone=True),
                        default=lambda: datetime.now(timezone.utc),
                        nullable=False)


class SkriblPostMedia(SkriblBase):
    """Exact post -> media-object association.

    Authorisation for /media/<key> was previously a SUBSTRING SEARCH:
    CAST(payload_json AS TEXT) LIKE '%<key>%'. Three things were wrong with it.

    FORGEABLE. The API deliberately preserves unknown JSON fields, so anyone who
    learned a private object's key could paste that key into any field of their
    own public post; the media route then found an "accessible referencing post"
    and served the private object. Authorisation by string containment is not
    authorisation.

    SLOW. It was an unindexed full scan of every payload_json on every blob
    request — reintroducing exactly the hot table-wide read that moving media out
    of the database was meant to eliminate.

    WRONG AT SCALE. It was capped with .limit(25) and no ORDER BY, so a
    content-addressed object referenced by more than 25 posts could 404 for a
    legitimately authorised reader depending on which arbitrary rows came back.

    An exact association fixes all three at once: an indexed equality lookup that
    cannot be spoofed by putting a string somewhere in your own payload.
    """
    __tablename__ = "skribl_post_media"

    id = Column(Integer, primary_key=True)
    post_id = Column(Integer, nullable=False, index=True)
    media_key = Column(String(80), nullable=False, index=True)

    __table_args__ = (
        # One row per (post, object). Content addressing means a post can
        # reference the same object from several slots; it needs one row.
        Index("ix_post_media_unique", "post_id", "media_key", unique=True),
        # Declared here as well as in the v180 migration, or the drift check
        # reports the migration as "ahead" of the models — and create_all()
        # would build a table without the constraint that authorisation
        # depends on. An association whose post is gone authorises nothing and
        # would make the orphan sweep treat its media as still referenced.
        ForeignKeyConstraint(["post_id"], ["skribl_posts.id"],
                             name="fk_post_media_post", ondelete="CASCADE"),
    )

# --- the session seam -------------------------------------------------------
# A callable, not a session: Flask-SQLAlchemy's `db.session` is a scoped session
# proxy that must be resolved inside an application context, so binding the
# object itself at import time would capture the wrong thing.
_session_factory = None


def bind_session(factory):
    """Give Skribl the host's session factory. Call once, at init."""
    global _session_factory
    if not callable(factory):
        raise RuntimeError("bind_session() needs a callable returning a Session.")
    _session_factory = factory


NO_SESSION = object()   # app-local marker: "this app declared session=False"


def session():
    """Resolve the session for the CURRENT application, not the last one bound.

    This used to return `_session_factory()` — one module-level global that every
    init_skribl() overwrote. Creating app B therefore redirected app A's routes
    at B's database: fine for one Skribl per process (production, the standalone
    app), broken for app factories, multi-tenant WSGI, and any test that builds
    more than one instance. It bit verify_privacy.py, which is how it surfaced.

    The factory now lives in app.extensions["skribl"], so each application
    resolves its own. The module global remains only as a fallback for code
    running outside an application context.
    """
    factory = None
    try:
        factory = current_app.extensions.get("skribl", {}).get("session")
    except (ImportError, RuntimeError):
        # No application context — fall through to the process-wide binding.
        pass
    if factory is NO_SESSION:
        # session=False FAILS CLOSED (v201 review, F6). The app declared "this
        # blueprint never queries"; a query reaching here anyway used to fall
        # through to the process-global binding — i.e. to whichever OTHER
        # Skribl app bound its session last. A database-less blueprint must
        # never borrow someone else's database; it must say this, loudly.
        raise RuntimeError(
            "This Skribl blueprint was created with session=False (no "
            "database), but a database query was attempted. Pass a real "
            "session factory if this blueprint should query.")
    if factory is None:
        if _session_factory is None:
            raise RuntimeError(
                "Skribl has no database session. The host must call "
                "skribl.init_skribl(session=lambda: db.session) before serving.")
        factory = _session_factory
    sess = factory()
    # Normally False: init_skribl() resolves the bind eagerly and this is one
    # boolean read per request. It is only True for hosts whose engine did not
    # exist at mount time.
    if _FK_RESOLVE_LATE:
        _fk_install_late(sess)
    return sess


# Engines that already carry the pragma listener. A WeakSet so a host that
# builds and discards engines (tests, app factories) is not leaked into.
_FK_ENGINES = weakref.WeakSet()
# Set only when the engine could not be resolved at init time. The lazy path in
# session() is a fallback, not the normal route, and this keeps it to one
# boolean check per session resolution when it is not needed.
_FK_RESOLVE_LATE = False


def _fk_opted_out():
    return os.environ.get("SKRIBL_SQLITE_FOREIGN_KEYS", "1") == "0"


def _install_sqlite_fk(bind):
    """Attach the pragma listener to ONE engine. Idempotent per engine."""
    engine = getattr(bind, "engine", bind)
    if engine is None or engine in _FK_ENGINES:
        return False
    _FK_ENGINES.add(engine)
    if getattr(getattr(engine, "dialect", None), "name", None) != "sqlite":
        return False                     # PostgreSQL and friends: nothing to do

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record):
        # REAL TRANSACTIONS, or the savepoint contract is fiction. pysqlite's
        # legacy transaction handling defers its BEGIN until the first DML —
        # so a request whose first statement is our SAVEPOINT (a bare POST:
        # begin_nested before any other SQL) ran that SAVEPOINT in autocommit
        # mode, and RELEASE made the rows durable with NO commit ever issued.
        # Found by verify_txcontract's teardown-commit counterexample: an
        # engine "commit" listener counted zero while the row sat committed.
        # This is the canonical SQLAlchemy recipe: take transaction control
        # away from the driver and emit BEGIN ourselves. Installed beside the
        # FK pragma because it is the same class of per-engine SQLite truth.
        dbapi_connection.isolation_level = None
        cur = dbapi_connection.cursor()
        try:
            cur.execute("PRAGMA foreign_keys=ON")
        finally:
            cur.close()

    @event.listens_for(engine, "begin")
    def _real_begin(conn):
        conn.exec_driver_sql("BEGIN")

    return True


def enable_sqlite_foreign_keys(app=None):
    """Make SQLite honour the foreign keys this package declares.

    SQLite defaults `PRAGMA foreign_keys` to OFF, PER CONNECTION. The constraint
    added by revision c7e1a5f04b93 — `skribl_post_media.post_id -> skribl_posts.id`
    ON DELETE CASCADE — is therefore written into the schema and then ignored, so
    on SQLite deleting a post left its association rows behind. Measured before
    this was added: one row survived, `sweep_orphans` consequently read the media
    as still referenced, and the bytes were never reclaimed. That is exactly the
    leak the constraint exists to close, still open on the one engine nobody had
    run the assertion against — PostgreSQL enforces it natively, and that is
    where the suite had always been run.

    Access was NOT exposed by this: `/media/<key>` authorises through an EXISTS
    join to the post, so a deleted post's media is refused (404) whether or not
    the orphan row survives. It is a data-integrity and storage leak.

    SCOPE. This attaches to the ENGINE Skribl was given, not to SQLAlchemy's
    `Engine` class. The earlier version listened on the class, so mounting this
    blueprint turned on foreign-key enforcement for every SQLite connection
    anywhere in the host's process — an unrelated analytics database, a cache, a
    test fixture. A drop-in component should not reach past its own seam to do
    that, and the blast radius is now the one engine Skribl's session is bound
    to. Where that engine IS the host's engine (the normal integration, since
    Skribl deliberately shares the host's session so the two sets of tables
    commit in one transaction) the host's SQLite tables are still covered: the
    pragma is a property of the connection and cannot be narrowed further than
    the engine. That remains a real behaviour change for a SQLite host whose own
    data violates a constraint it declared, and `SKRIBL_SQLITE_FOREIGN_KEYS=0`
    opts out — the constraint then reverts to being declared and unenforced.

    Nothing happens on PostgreSQL, which enforces foreign keys regardless.

    `app` is optional: pass it and the engine is resolved once, at init, before
    the pool has opened anything. Without it — or if resolution fails, e.g. a
    host that configures its database after mounting — installation falls back
    to the first session() resolution.
    """
    global _FK_RESOLVE_LATE
    if _fk_opted_out():
        return False
    if app is not None:
        try:
            with app.app_context():
                factory = (app.extensions.get("skribl", {}).get("session")
                           or _session_factory)
                if factory is not None:
                    return _install_sqlite_fk(factory().get_bind())
        except Exception:
            # A host that has not configured its database yet is not an error
            # here; it just means the engine is not knowable until first use.
            pass
    _FK_RESOLVE_LATE = True
    return False


def _fk_install_late(sess):
    """Fallback path: attach on first use when init could not resolve a bind."""
    if _fk_opted_out():
        return
    try:
        _install_sqlite_fk(sess.get_bind())
    except Exception:
        pass


def as_utc(dt):
    """A timezone-AWARE UTC datetime for a stored created_at, or None.

    The columns are DateTime(timezone=True) as of v200, but two kinds of naive
    value still reach Python: every row written before the migration, and
    everything SQLite returns (its DATETIME affinity has no zone to give back
    — the review's roundtrip proof: tzinfo=None on reload). Every stored value
    IS UTC — the defaults have always been datetime.now(timezone.utc) — so
    naive-means-UTC is a fact of this schema, not a guess. Serialising a naive
    value directly rendered "2026-08-14T12:00:00": a timestamp javascript's
    Date() parses as LOCAL time, shifting every post's age by the viewer's
    offset.
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def create_all(engine):
    """Create Skribl's tables only. Leaves every host table alone."""
    SkriblBase.metadata.create_all(engine)


def attach_to_metadata(metadata):
    """Copy Skribl's table definitions into the host's MetaData.

    Optional, and only for hosts that want a single `db.create_all()` to cover
    Skribl's tables alongside their own. The DDL is identical either way; this
    just makes Skribl's tables visible to the host's metadata-driven tooling.
    Hosts running Alembic should skip this and point their migrations at
    `SkriblBase.metadata` instead, so the two schemas stay independently
    versioned.
    """
    for name, table in SkriblBase.metadata.tables.items():
        if name not in metadata.tables:
            table.to_metadata(metadata)
