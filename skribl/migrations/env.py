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


def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
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
