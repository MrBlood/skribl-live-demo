"""v203: pending-media claims — durable ownership the orphan sweep can see.

WHY A TABLE. Media bytes are written to the store before the post's
SkriblPostMedia association row, and that row commits in the HOST's transaction.
Between the orphan sweeper's reference check and its delete, a post can reuse an
object the sweeper listed as long-dead and the sweeper deletes it a moment
before the association commits — a permanent media 404 on a live post. No
delete-time check can see an uncommitted association, so a re-check cannot close
the window; the poster needs to record a claim that is COMMITTED independently
of the host transaction, visible to the sweeper the instant it is written.

SHAPE. media_key names the object; expires_at bounds a poster that crashed
between claiming and committing. No foreign key: a claim names an object, not a
post, and is transient reservation state pruned by expiry rather than post
lifecycle. Both columns indexed — media_key for the sweeper's per-key lookup,
expires_at for pruning.

Scoped to SkriblBase.metadata like every other revision here — it never touches
a host's tables.
"""
from alembic import op
import sqlalchemy as sa

revision = "f7c2e0a934d1"
down_revision = "d3f8b12c9a67"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "skribl_pending_media",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("media_key", sa.String(length=80), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_skribl_pending_media_media_key",
                    "skribl_pending_media", ["media_key"])
    op.create_index("ix_skribl_pending_media_expires_at",
                    "skribl_pending_media", ["expires_at"])


def downgrade():
    op.drop_index("ix_skribl_pending_media_expires_at",
                  table_name="skribl_pending_media")
    op.drop_index("ix_skribl_pending_media_media_key",
                  table_name="skribl_pending_media")
    op.drop_table("skribl_pending_media")
