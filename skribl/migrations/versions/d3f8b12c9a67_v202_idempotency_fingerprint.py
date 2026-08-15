"""v202: idempotency rows fingerprint the request they answered.

WHY (v201 review, F4). An idempotency key without a request fingerprint names
an author+key, not an author+REQUEST: the same author reusing key K with a
different body received a 200 replay of the OLD post — plausible in practice,
because the client holds its key across an ambiguous failure, and a user who
edits before retrying sends a semantically different request under the same
key. With the fingerprint, same key + same body replays; same key + different
body is refused with 409 instead of silently answering with the wrong post.

NULL means a row written before this migration: replayed unconditionally,
exactly as those rows were originally promised to behave.
"""
from alembic import op
import sqlalchemy as sa

revision = "d3f8b12c9a67"
down_revision = "b7e2f9a41c55"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("skribl_idempotency",
                  sa.Column("request_fingerprint", sa.String(length=64),
                            nullable=True))


def downgrade():
    op.drop_column("skribl_idempotency", "request_fingerprint")
