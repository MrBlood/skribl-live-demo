"""v316: drafts saved to the author's account.

WHY A TABLE. The owner wanted to save a drawing "not on my machine as a file",
so it can be opened later from a host's post composer and added to a post. A
draft belongs to a signed-in author and to nobody else: it has no share link,
no player, no listing, and the routes answer 404 to anyone but its owner.

payload_json is the editor's own draft serialisation (the object a .skribl
backup file holds), bounded by the same payload checks a post passes, and by
SKRIBL_MAX_DRAFTS per author. thumbnail is a small JPEG data URL for the list.

A new table only; nothing existing is altered. Scoped to SkriblBase.metadata
like every other revision here -- it never touches a host's tables.
"""
from alembic import op
import sqlalchemy as sa

revision = "c3e8a1f5d706"
down_revision = "b5c1e7d92a34"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "skribl_drafts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("public_id", sa.String(length=32), nullable=False),
        sa.Column("user_id", sa.String(length=255), nullable=False),
        sa.Column("kind", sa.String(length=8), nullable=False),
        sa.Column("title", sa.String(length=80), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("thumbnail", sa.Text(), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_skribl_drafts_public_id", "skribl_drafts", ["public_id"], unique=True)
    op.create_index("ix_skribl_drafts_user_id", "skribl_drafts", ["user_id"])
    op.create_index("ix_skribl_drafts_user_updated", "skribl_drafts", ["user_id", "updated_at"])


def downgrade():
    op.drop_index("ix_skribl_drafts_user_updated", table_name="skribl_drafts")
    op.drop_index("ix_skribl_drafts_user_id", table_name="skribl_drafts")
    op.drop_index("ix_skribl_drafts_public_id", table_name="skribl_drafts")
    op.drop_table("skribl_drafts")
