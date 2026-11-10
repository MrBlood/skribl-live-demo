"""Alembic environment for THE SITE'S tables only (social/models.py).

Scoped to SocialBase.metadata, with a version table of its own, so
`alembic -c social/alembic.ini upgrade head` can never touch Skribl's tables
or Skribl's stamp (alembic_version), and an autogenerate never proposes
dropping a table that is not the site's. Skribl's chain (skribl/migrations,
the root alembic.ini) is the same shape and knows nothing of this one.
"""
from logging.config import fileConfig
import os

from alembic import context
from sqlalchemy import engine_from_config, pool

from social.models import SocialBase

#: The site's stamp. Skribl's is alembic_version; the two never share one.
VERSION_TABLE = "social_alembic_version"

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# DATABASE_URL wins over the ini file, as it does for the app and for
# Skribl's chain, and is spelled the way they spell it.
_url = os.environ.get("DATABASE_URL")
if _url:
    if _url.startswith("postgresql://"):
        _url = _url.replace("postgresql://", "postgresql+psycopg://", 1)
    elif _url.startswith("postgres://"):
        _url = _url.replace("postgres://", "postgresql+psycopg://", 1)
    # %% because the Config is a ConfigParser: a '%' in the URL (an encoded
    # password) would otherwise raise an error that carries the URL, password
    # and all, into the deploy log (Skribl's chain learned it: PF-021).
    config.set_main_option("sqlalchemy.url", _url.replace("%", "%%"))


def _ensure_sqlite_dir(url):
    """Make the folder a SQLite file lives in (instance/ is made by Flask on
    demand, and not by Alembic)."""
    if not url.startswith("sqlite"):
        return
    path = url.split("///", 1)[-1].split("?", 1)[0]
    if not path or path == ":memory:":
        return
    directory = os.path.dirname(os.path.abspath(path))
    if directory:
        os.makedirs(directory, exist_ok=True)


_ensure_sqlite_dir(config.get_main_option("sqlalchemy.url") or "")

target_metadata = SocialBase.metadata


def include_object(obj, name, type_, reflected, compare_to):
    """Only the site's own tables: Skribl's, a host's and the other chain's
    stamp are none of this chain's business."""
    if type_ == "table":
        return name in target_metadata.tables
    return True


def run_migrations_offline():
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        include_object=include_object,
        version_table=VERSION_TABLE,
        literal_binds=True,
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
            version_table=VERSION_TABLE,
            render_as_batch=True,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
