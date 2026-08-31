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

from .core import MAX_CAPTION_CHARS, MAX_TITLE_CHARS
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

    Concurrency: reservation is insert-then-count, which is NOT a database
    constraint — no unique index or CHECK enforces "at most N active slots".
    What makes it correct on PostgreSQL is a TRANSACTION-SCOPED ADVISORY LOCK
    keyed on the client identity (`pg_advisory_xact_lock`, see
    ratelimit._rate_reserve_post): requests sharing an identity serialise, so
    the count each one runs is taken with no other reservation for that identity
    in flight, while unrelated posters never contend. It releases on commit or
    rollback, including if the process dies mid-request. On SQLite it is a no-op
    because writes are already serialised by the single-writer lock.

    Without it the failure was not over-admission but the opposite: twelve
    concurrent posts against a quota of two all inserted before any count ran,
    every request saw 12 > 2, every request withdrew, and ZERO were admitted.
    SQLite hid that completely. (Review round 7, #5)

    VERIFIED ON POSTGRESQL ACROSS PROCESSES since v211 — `verify_postgres.py`
    runs four real gunicorn WORKER PROCESSES against live PostgreSQL, releases
    twelve requests through a barrier against a quota of two, and asserts both
    no over-admission (exactly two post rows) and no under-admission (the quota
    was actually used), with worker PIDs compared before and after so a respawn
    cannot mask the result. It holds for THAT configuration only — one
    PostgreSQL version, default isolation, gunicorn's default worker model, one
    burst, no induced failures — and the suite prints that scope itself.

    This docstring used to end "Verified under SQLite and threads; NOT yet
    verified on PostgreSQL across processes", and used to deny that any advisory
    lock existed — both written before the fix above and never revisited. An
    outside reviewer of the v224 archive read them, took them at face value, and
    filed a MEDIUM finding asking for a test that already existed, against a
    mechanism described as weaker than it is. Stale prose does not just mislead
    a reader — it spends a reviewer's attention on work already done, and it
    understated a security-relevant guarantee. `verify_docs.py` now gates this
    claim against the assertion that proves it, and scans this file to do it.

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


#: Extra visibility states a host has taught this application about. The model
#: deliberately has no DB CHECK constraint so a host can add "draft",
#: "moderated" or "scheduled" without a Skribl migration — but until v224 the
#: CREATE API rejected anything outside VISIBILITIES, so the documented
#: extensibility only worked for rows the host wrote itself. Outside review #7
#: called that contradiction, correctly. This is the seam that resolves it.
_EXTRA_VISIBILITIES = ()


def set_visibility_values(values, app=None):
    """Widen the set of visibility strings POST /api/skribls will accept.

    Same app-local shape as set_visibility_policy: with `app`, only that
    application sees them. Skribl's own three are always accepted and cannot be
    removed — narrowing the built-ins would change what an existing payload
    means, which is not an extension.

    A host adding a state is also taking on what it MEANS: visible_to() decides
    reads through the visibility policy, and the built-in feed lists only
    "public". A custom state is invisible to the feed unless the host also
    installs a feed filter (see set_feed_filter).
    """
    vals = tuple(str(v) for v in (values or ()))
    for v in vals:
        # 16 because that is String(16) on SkriblPost.visibility. A longer
        # value would be accepted here and then truncated or rejected by the
        # database at INSERT — a configuration error surfacing as a 500 on
        # somebody's first post rather than at the line that made it.
        if not v or len(v) > 16:
            raise ValueError(
                f"visibility value {v!r} must be 1-16 characters — the column "
                "holding it is String(16)")
    if app is not None:
        app.extensions.setdefault("skribl", {})["visibility_values"] = vals
        return
    global _EXTRA_VISIBILITIES
    _EXTRA_VISIBILITIES = vals


def visibility_values():
    """Every visibility string this application accepts on create."""
    extra = _EXTRA_VISIBILITIES
    try:
        from flask import current_app
        local = current_app.extensions.get("skribl", {}).get(
            "visibility_values", _POLICY_UNSET)
        if local is not _POLICY_UNSET:
            extra = local
    except (ImportError, RuntimeError):
        pass
    return tuple(SkriblPost.VISIBILITIES) + tuple(extra or ())


#: A host-supplied SQL predicate for the FEED, applied inside the query.
_FEED_FILTER = None


def set_feed_filter(fn, app=None):
    """Install `fn(query, viewer_id) -> query` for GET /api/skribls.

    WHY THIS EXISTS AND WHY IT IS SQL. visible_to() — and through it the host's
    visibility policy — guards the payload endpoint, the player page, the share
    card and the media endpoint. It did NOT guard the feed, which filtered on
    the visibility COLUMN alone. A host policy that denies a viewer therefore
    still disclosed the post's existence, title, caption, author id, timestamp
    and public id through the listing (outside review #3).

    The fix cannot be "run the policy over the rows we fetched": the feed is
    keyset-paginated, so dropping rows after the fact returns short pages,
    makes `next_cursor` describe a row the viewer never saw, and turns "no
    results" into an ambiguity between "end of feed" and "everything on this
    page was denied". Authorization that pages correctly has to be part of the
    query. The host contributes a predicate; Skribl composes it.

    The callable receives the SQLAlchemy query with Skribl's own visibility
    filter already applied, and must return a query. Raising is not caught:
    a broken feed filter should fail loudly, not fall back to showing
    everything.
    """
    if fn is not None and not callable(fn):
        raise TypeError("feed filter must be callable or None")
    if app is not None:
        app.extensions.setdefault("skribl", {})["feed_filter"] = fn
        return
    global _FEED_FILTER
    _FEED_FILTER = fn


def feed_filter():
    try:
        from flask import current_app
        local = current_app.extensions.get("skribl", {}).get(
            "feed_filter", _POLICY_UNSET)
        if local is not _POLICY_UNSET:
            return local
    except (ImportError, RuntimeError):
        pass
    return _FEED_FILTER


#: A host-supplied author serialiser. Skribl knows a user_id and nothing else.
_AUTHOR_RESOLVER = None


def set_author_resolver(fn, app=None):
    """Install `fn(user_id) -> dict` to describe a post's author.

    The API used to return {"id": <real id>, "username": "demo-user"} for every
    post in every deployment (outside review #8) — a literal left from the demo,
    contradicting the real id beside it. Skribl has no user table and cannot
    invent a name, so the honest default is to return the id alone and let the
    host add what it knows.

    `id` IS NOT OVERRIDABLE. Whatever the resolver returns, the id in the
    response stays the user_id Skribl stored on the post. It is the value the
    host's own visibility policy is handed and the value it wrote; letting a
    display-name lookup silently change it would make the identifier in the
    response mean something different from the identifier the authorization
    decisions used. A host that wants to publish a different handle adds its
    own key for it.
    """
    if fn is not None and not callable(fn):
        raise TypeError("author resolver must be callable or None")
    if app is not None:
        app.extensions.setdefault("skribl", {})["author_resolver"] = fn
        return
    global _AUTHOR_RESOLVER
    _AUTHOR_RESOLVER = fn


def author_dict(user_id):
    """{"id": ...} plus whatever the host's resolver adds."""
    fn = _AUTHOR_RESOLVER
    try:
        from flask import current_app
        local = current_app.extensions.get("skribl", {}).get(
            "author_resolver", _POLICY_UNSET)
        if local is not _POLICY_UNSET:
            fn = local
    except (ImportError, RuntimeError):
        pass
    out = {"id": user_id}
    if fn is not None:
        extra = fn(user_id)
        if isinstance(extra, dict):
            out.update(extra)
            out["id"] = user_id      # authoritative — see the docstring
    return out


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
    # Widths come from core so the API check, the editors' maxlength and the
    # column cannot drift apart again — see the note there.
    title = Column(String(MAX_TITLE_CHARS), nullable=False)
    caption = Column(String(MAX_CAPTION_CHARS), nullable=True)
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

class SkriblPendingMedia(SkriblBase):
    """A short-lived, COMMITTED claim on a media object during a post.

    THE RACE IT CLOSES (outside review of v263/v264/v265, H3). Media bytes are
    written to the store BEFORE the post's SkriblPostMedia association row, and
    that row commits inside the HOST's transaction — so between the orphan
    sweeper's reference check and its delete, a post can reuse an object the
    sweeper listed as long-dead, and the sweeper deletes it a moment before the
    association commits. No delete-time check can see an UNCOMMITTED association,
    so touch-and-re-check (v223/v264) narrows the window but cannot close it.

    A pending claim is the durable ownership the sweeper CAN see: the poster
    writes one — committed independently of the host transaction, so it is
    visible immediately — for every object it is about to reference, and the
    sweeper spares any object carrying an unexpired claim. The claim ages out by
    `expires_at` (a post completes in milliseconds; the TTL only bounds a poster
    that crashed between claiming and committing), so nothing has to delete it
    on the happy path and a rolled-back post's claim simply expires.

    No foreign key: a claim names an object, not a post, and outlives neither —
    it is transient reservation state, pruned by expiry, not post lifecycle.
    """
    __tablename__ = "skribl_pending_media"

    id = Column(Integer, primary_key=True)
    media_key = Column(String(80), nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)


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
    if getattr(getattr(engine, "dialect", None), "name", None) != "sqlite":
        _FK_ENGINES.add(engine)          # nothing to install; remember we looked
        return False                     # PostgreSQL and friends: nothing to do
    # v208 (v207 review F1): SQLAlchemy 2.x does NOT surface the configured
    # mode on `dialect.isolation_level` — that stays None for a real
    # `create_engine(..., isolation_level="AUTOCOMMIT")`. The configured
    # on-connect mode lives on `dialect._on_connect_isolation_level`. The old
    # single check therefore never fired against the exact configuration it
    # was written to refuse: the guard was dead code. Check both locations.
    _iso = (getattr(engine.dialect, "_on_connect_isolation_level", None)
            or getattr(engine.dialect, "isolation_level", None) or "")
    if str(_iso).upper() == "AUTOCOMMIT":
        # The host EXPLICITLY chose driver-level autocommit (v202 review, F3).
        # Installing the explicit-BEGIN recipe would contradict that choice —
        # and Skribl's savepoint contract cannot hold without real
        # transactions — so refuse loudly instead of silently doing either.
        # NOT recorded in _FK_ENGINES (v209 review F3). It used to be added
        # before this check, so a refused engine was marked "installed": if the
        # host caught the RuntimeError and rebuilt the same engine object
        # without AUTOCOMMIT, or two Skribl apps shared one engine, the second
        # attempt returned False silently and no listener was ever attached —
        # a SQLite engine running Skribl with neither the FK pragma nor the
        # explicit-BEGIN recipe, which is precisely the state the guard exists
        # to prevent. Registration is the LAST step now, after the listener is
        # actually attached.
        raise RuntimeError(
            "Skribl cannot run on a SQLite engine configured with "
            "isolation_level='AUTOCOMMIT': its transaction contract needs "
            "real transactions (see docs/INTEGRATION.md, 'SQLite transaction "
            "mode').")

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
        # (An engine created with isolation_level="AUTOCOMMIT" is detected
        # BEFORE these listeners install — see the guard in
        # _install_sqlite_fk — because emitting BEGINs against a deliberately
        # autocommit engine would contradict the host's explicit choice.)
        try:
            cur.execute("PRAGMA foreign_keys=ON")
        finally:
            cur.close()

    @event.listens_for(engine, "begin")
    def _real_begin(conn):
        try:
            conn.exec_driver_sql("BEGIN")
        except Exception as e:
            # DELIBERATE COEXISTENCE (v202 review, F3): a host that installed
            # its own BEGIN-emitting recipe before Skribl would double-BEGIN
            # here. "cannot start a transaction within a transaction" in that
            # one shape means the host already began — which is the outcome
            # this listener wants — so it is tolerated. Anything else is a
            # real error and raises.
            if "within a transaction" not in str(e).lower():
                raise

    # v211 (v210 review F4): registered ONLY here, after BOTH listeners are
    # attached. Before, the add sat between the AUTOCOMMIT check and the
    # listener registrations; if either registration raised, the engine was
    # left recorded as installed and every later attempt returned False —
    # a SQLite engine running with neither pragma nor BEGIN recipe, silently.
    # The v209 fix moved the add past the refusal; this moves it past the
    # whole installation, which is what the comment claimed all along.
    _FK_ENGINES.add(engine)
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
