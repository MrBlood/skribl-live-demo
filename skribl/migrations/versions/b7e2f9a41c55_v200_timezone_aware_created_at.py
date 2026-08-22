"""v200: created_at becomes timezone-aware in the schema.

THE PROOF THIS ANSWERS (outside review). On PostgreSQL the columns were
TIMESTAMP WITHOUT TIME ZONE; on SQLite a stored aware UTC datetime reloaded as
tzinfo=None. Every value ever written IS UTC — the defaults have always been
datetime.now(timezone.utc) — but the schema didn't say so, and a naive
isoformat() ("2026-08-14T12:00:00") is a string javascript's Date() parses as
LOCAL time: every post's age shifted by the viewer's offset.

TWO HALVES. This migration makes the SCHEMA say UTC where the dialect can
(TIMESTAMPTZ on PostgreSQL, with AT TIME ZONE 'UTC' so existing naive values
are reinterpreted as the UTC they already were, not shifted). SQLite has no
zone-aware storage — its half is skribl.models.as_utc(), which every
serialisation path now routes through, so a naive value read back is labelled
as the UTC it is before it leaves the process. Neither half alone closes the
review's proof; together they do, and verify_apiedges pins the wire format.
"""
from alembic import op
import sqlalchemy as sa

revision = "b7e2f9a41c55"
down_revision = "a9d4c31e7b02"
branch_labels = None
depends_on = None

_TABLES = ("skribl_posts", "skribl_rate_events", "skribl_idempotency")


def upgrade():
    if op.get_bind().dialect.name != "postgresql":
        # SQLite stores DATETIME as text either way; there is no zone to add.
        # The Python-side as_utc() carries the semantics there.
        return
    for table in _TABLES:
        op.alter_column(table, "created_at",
                        type_=sa.DateTime(timezone=True),
                        postgresql_using="created_at AT TIME ZONE 'UTC'")


def downgrade():
    if op.get_bind().dialect.name != "postgresql":
        return
    for table in _TABLES:
        op.alter_column(table, "created_at",
                        type_=sa.DateTime(timezone=False),
                        postgresql_using="created_at AT TIME ZONE 'UTC'")
