"""v279: skribl_posts.user_id becomes opaque text.

WHY. `current_user_id` is documented as "a callable returning your user id"
and the worked example in docs/INTEGRATION.md passes the host's native
`current_user.id` straight through — while the column was Integer. A host whose
users are identified by UUID, ULID, an OAuth subject, an LDAP DN or an email
therefore could not integrate at all: creation failed at flush, and the listing
endpoint coerced `?user_id=` with int() and answered 400 before it queried. An
audit of v278 named it: do not leave the API generic while the schema is not.

Text is the side to settle on for an integration library. Skribl never does
arithmetic on this value, never sorts by it and never joins to a users table it
does not own — it compares it for equality and nothing else. An integer host
loses nothing (42 stores as "42"; every boundary normalises through
models.normalise_user_id), and a textual host gains the ability to integrate.

THE CONVERSION IS THE INTERESTING PART, and it differs by backend.

PostgreSQL will not silently reinterpret an integer column as text: ALTER
COLUMN ... TYPE VARCHAR needs an explicit USING, or the migration errors. The
cast is total — every integer has exactly one text form — so no row is at risk
and no data is lost. 42 becomes '42', which is what normalise_user_id produces
for the same host on the next request, so ownership keeps matching across the
upgrade. That last sentence is the whole reason this is safe to run on a
populated database.

SQLite has no real ALTER COLUMN TYPE and does not need one: its column types
are advisory, an INTEGER column already stores whatever it is given, and
SQLAlchemy reads the declared type from the model rather than the file. The
upgrade is therefore a no-op there, stated rather than skipped by accident.

DOWNGRADE IS LOSSY AND SAYS SO. Going back to Integer works only if every
user_id happens to be numeric; a host that has been running with UUIDs since
the upgrade cannot go back without discarding its authorship. The downgrade
refuses rather than truncating, because a takedown or a delete authorised
against the wrong owner is worse than a failed migration.

Revision ID: b7d240ac91e3
Revises: a1c93e5f7b04
"""
import sqlalchemy as sa
from alembic import op

revision = "b7d240ac91e3"
down_revision = "a1c93e5f7b04"
branch_labels = None
depends_on = None

_LEN = 255


def _dialect(bind):
    return bind.dialect.name


def upgrade():
    bind = op.get_bind()
    name = _dialect(bind)
    if name == "sqlite":
        # SQLite has no ALTER COLUMN TYPE, so this rebuilds the table. It was a
        # no-op in the first draft, on the reasoning that SQLite's types are
        # advisory and the column already accepts text — true at runtime, and
        # the drift check failed it anyway, correctly: the chain's end state
        # then declared INTEGER while the model declared String, so a database
        # built by migration and one built by create_all() disagreed on paper.
        # A schema that only happens to work is the kind that stops working.
        with op.batch_alter_table("skribl_posts") as batch:
            batch.alter_column("user_id",
                               existing_type=sa.Integer(),
                               type_=sa.String(_LEN),
                               existing_nullable=True)
        return
    op.alter_column(
        "skribl_posts", "user_id",
        existing_type=sa.Integer(),
        type_=sa.String(_LEN),
        existing_nullable=True,
        # Required on PostgreSQL; harmless where the dialect ignores it.
        postgresql_using="user_id::varchar(%d)" % _LEN,
    )


def downgrade():
    bind = op.get_bind()
    name = _dialect(bind)
    if name == "sqlite":
        with op.batch_alter_table("skribl_posts") as batch:
            batch.alter_column("user_id",
                               existing_type=sa.String(_LEN),
                               type_=sa.Integer(),
                               existing_nullable=True)
        return
    # Refuse rather than mangle. A non-numeric id cast to integer is either an
    # error or, worse, a silent 0 — and a post whose owner became 0 is a post
    # anybody with user 0 can delete.
    bad = bind.execute(sa.text(
        "SELECT COUNT(*) FROM skribl_posts "
        "WHERE user_id IS NOT NULL AND user_id !~ '^[0-9]+$'"
    )).scalar()
    if bad:
        raise RuntimeError(
            f"{bad} post(s) have a non-numeric user_id; downgrading to Integer "
            "would discard or corrupt their authorship. Reassign or delete them "
            "first if this downgrade is really intended.")
    op.alter_column(
        "skribl_posts", "user_id",
        existing_type=sa.String(_LEN),
        type_=sa.Integer(),
        existing_nullable=True,
        postgresql_using="user_id::integer",
    )
