"""Skribl's two tables, and the session seam.

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
from datetime import datetime, timezone

from sqlalchemy import (Boolean, Column, DateTime, Index, Integer, JSON,
                        String)
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
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
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
    )


class SkriblPost(SkriblBase):
    __tablename__ = "skribl_posts"

    id = Column(Integer, primary_key=True)
    public_id = Column(String(32), unique=True, nullable=False, index=True)
    user_id = Column(Integer, nullable=True)
    title = Column(String(80), nullable=False)
    caption = Column(String(300), nullable=True)
    payload_json = Column(JSON, nullable=False)
    has_audio = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)


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


def session():
    if _session_factory is None:
        raise RuntimeError(
            "Skribl has no database session. The host must call "
            "skribl.init_skribl(session=lambda: db.session) before serving.")
    return _session_factory()


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
