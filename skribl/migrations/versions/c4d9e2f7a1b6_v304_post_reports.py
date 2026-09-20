"""v304: reports -- a queue of what people said should not be in the gallery.

WHY A TABLE. The public gallery is the first place strangers meet each
other's work, and the owner's direction for it was "opt-in, with Report on
every tile". A report has to outlive the request that made it and reach an
operator who was not there: a row, read by `python -m skribl.takedown
--reports`, is the smallest thing that does.

SHAPE. post_id names the post (FK, cascade, so a deleted post takes its
reports with it); reason is one of a closed set the API enforces; note is
optional and bounded like a caption; reporter_hash is the rate limiter's
salted hash of the client, never an address, and (post_id, reporter_hash) is
unique so one reader reporting one post twice is one row; state is 'open'
until an operator resolves it. Indexed by (state, created_at) for the queue.

Scoped to SkriblBase.metadata like every other revision here -- it never
touches a host's tables.
"""
from alembic import op
import sqlalchemy as sa

revision = "c4d9e2f7a1b6"
down_revision = "b7d240ac91e3"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "skribl_reports",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("post_id", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(length=24), nullable=False),
        sa.Column("note", sa.String(length=300), nullable=True),
        sa.Column("reporter_hash", sa.String(length=64), nullable=False),
        sa.Column("state", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["post_id"], ["skribl_posts.id"],
                                name="fk_report_post", ondelete="CASCADE"),
    )
    op.create_index("ix_skribl_reports_post_id", "skribl_reports", ["post_id"])
    op.create_index("ix_report_unique", "skribl_reports",
                    ["post_id", "reporter_hash"], unique=True)
    op.create_index("ix_skribl_reports_state_created", "skribl_reports",
                    ["state", "created_at"])


def downgrade():
    op.drop_index("ix_skribl_reports_state_created", table_name="skribl_reports")
    op.drop_index("ix_report_unique", table_name="skribl_reports")
    op.drop_index("ix_skribl_reports_post_id", table_name="skribl_reports")
    op.drop_table("skribl_reports")
