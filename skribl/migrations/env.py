"""Alembic environment for Skribl's tables ONLY.

Deliberately scoped to `SkriblBase.metadata`, so `alembic upgrade head` here can
never touch a host application's tables — and `--autogenerate` never proposes
dropping them, which is what happens when a component points Alembic at a
metadata object it does not own.

A host running its own Alembic keeps its own chain and adds this one as a
separate version path, so the two schemas stay independently versioned.
"""
from logging.config import fileConfig
import os

from alembic import context
from sqlalchemy import engine_from_config, pool

from skribl.models import SkriblBase

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# DATABASE_URL wins over the ini file, so deploys configure the same way the app
# does rather than needing a second source of truth.
_url = os.environ.get("DATABASE_URL")
if _url:
    if _url.startswith("postgresql://"):
        _url = _url.replace("postgresql://", "postgresql+psycopg://", 1)
    elif _url.startswith("postgres://"):
        _url = _url.replace("postgres://", "postgresql+psycopg://", 1)
    config.set_main_option("sqlalchemy.url", _url)

def _ensure_sqlite_dir(url):
    """Create the directory a SQLite file lives in.

    Flask makes instance/ on demand; Alembic does not, and instance/ is
    gitignored — so `alembic upgrade head` on a fresh clone failed with
    "unable to open database file" before the app had ever been run. Migrations
    are the FIRST command in the documented startup sequence, so this was the
    first thing a new deployment hit.
    """
    if not url.startswith("sqlite"):
        return
    path = url.split("///", 1)[-1].split("?", 1)[0]
    if not path or path == ":memory:":
        return
    directory = os.path.dirname(os.path.abspath(path))
    if directory:
        os.makedirs(directory, exist_ok=True)


_ensure_sqlite_dir(config.get_main_option("sqlalchemy.url") or "")

target_metadata = SkriblBase.metadata


def include_object(obj, name, type_, reflected, compare_to):
    """Ignore anything that is not ours.

    Without this, autogenerate against a host database sees the host's tables as
    'not in metadata' and cheerfully writes DROP TABLE for every one of them.
    """
    if type_ == "table":
        return name in target_metadata.tables
    return True


def run_migrations_offline():
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        include_object=include_object,
        literal_binds=True,
        # SQLite cannot ALTER most things in place; batch mode rebuilds the table
        # instead, so the same migration runs on SQLite and PostgreSQL.
        render_as_batch=True,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def _repair_stamped_over_drift(connection):
    """Create baseline tables a stamp claims exist, so the chain can run AT ALL.

    THE PRODUCTION FAILURE THIS FIXES (2026-09-01, first deploy that ever ran
    migrations — Render ignores the Procfile, so `alembic upgrade head` had
    never executed there). The database was stamped at the v131 baseline
    (6aa1de24dda3) without the baseline's DDL having run: `upgrade head`
    started from the stamp and crashed INSIDE c7e1a5f04b93 (v180), whose
    backfill UPDATEs skribl_rate_events — UndefinedTable. The head-position
    repair revision (e9f4a7c31b28) can never help with that, because the
    chain dies before reaching it.

    Editing v180 to skip a missing table is forbidden — released revisions
    are frozen (RELEASED.txt; a database already stamped past an edited
    revision never re-runs it). This pre-flight is the one place that runs
    BEFORE the chain on every invocation, so it is where a stamped-over
    database gets the baseline tables the stamp promised, in their BASELINE
    shape — naive timestamps, no check constraint — so v180 and v200 then
    apply their alters exactly as they would have originally.

    Strictly gated: only when a stamp EXISTS (a fresh database has no
    alembic_version and must get its tables from the baseline revision
    itself, never from here) and only for a table that is MISSING. On every
    healthy database this reads two booleans and does nothing.
    """
    import sqlalchemy as sa
    try:
        _repair_stamped_over_drift_inner(connection, sa)
    finally:
        # CRITICAL: even the read-only inspection above opens an implicit
        # transaction on this connection, and Alembic will not manage a
        # transaction it finds already begun — observed as `alembic stamp`
        # printing success while alembic_version never appeared (the write
        # rolled back when the connection closed). The pre-flight must hand
        # Alembic a connection with NO transaction in flight.
        connection.commit()


def _repair_stamped_over_drift_inner(connection, sa):
    insp = sa.inspect(connection)
    if not insp.has_table("alembic_version"):
        return
    stamped = connection.execute(
        sa.text("SELECT version_num FROM alembic_version")).scalar()
    if not stamped:
        return
    meta = sa.MetaData()
    if not insp.has_table("skribl_posts"):
        sa.Table(
            "skribl_posts", meta,
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("public_id", sa.String(32), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=True),
            sa.Column("title", sa.String(80), nullable=False),
            sa.Column("caption", sa.String(300), nullable=True),
            sa.Column("payload_json", sa.JSON(), nullable=False),
            sa.Column("has_audio", sa.Boolean(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Index("ix_skribl_posts_public_id", "public_id", unique=True),
        )
        print(f"[env.py pre-flight] stamp {stamped[:12]} present but "
              "skribl_posts missing — creating it in v131 baseline shape.")
    if not insp.has_table("skribl_rate_events"):
        sa.Table(
            "skribl_rate_events", meta,
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("bucket", sa.String(16), nullable=False),
            sa.Column("key_hash", sa.String(64), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("state", sa.String(10), nullable=False),
            sa.Index("ix_rate_bucket_key_time", "bucket", "key_hash",
                     "created_at"),
            sa.Index("ix_rate_created_at", "created_at"),
        )
        print(f"[env.py pre-flight] stamp {stamped[:12]} present but "
              "skribl_rate_events missing — creating it in v131 baseline "
              "shape (v180/v200 in the chain will then alter it normally).")
    if meta.tables:
        meta.create_all(connection)


def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        _repair_stamped_over_drift(connection)
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
            render_as_batch=True,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
