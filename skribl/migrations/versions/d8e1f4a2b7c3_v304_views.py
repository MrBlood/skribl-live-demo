"""v304: plays, counted -- the rows behind the gallery's Hot.

WHY A TABLE AND A COLUMN. "Hot" has to mean something a person cannot game
by holding refresh, so a view is a ROW keyed by (post, client hash, UTC day)
with a unique index: the same client fetching the same post's payload twice
in a day is one view. The post carries a running total (views_total) so a
listing can show a count without a join; the seven-day count the gallery
ranks by is computed from the rows.

views_total is added NOT NULL with a server default of 0, so a populated
table takes it (the v132 lesson: a NOT NULL column with no default fails
exactly on the databases that matter).

Scoped to SkriblBase.metadata like every other revision here -- it never
touches a host's tables.
"""
from alembic import op
import sqlalchemy as sa

revision = "d8e1f4a2b7c3"
down_revision = "c4d9e2f7a1b6"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("skribl_posts",
                  sa.Column("views_total", sa.Integer(), nullable=False, server_default="0"))
    op.create_table(
        "skribl_views",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("post_id", sa.Integer(), nullable=False),
        sa.Column("viewer_hash", sa.String(length=64), nullable=False),
        sa.Column("day", sa.String(length=10), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["post_id"], ["skribl_posts.id"],
                                name="fk_view_post", ondelete="CASCADE"),
    )
    op.create_index("ix_skribl_views_post_id", "skribl_views", ["post_id"])
    op.create_index("ix_view_unique", "skribl_views",
                    ["post_id", "viewer_hash", "day"], unique=True)
    op.create_index("ix_skribl_views_created", "skribl_views", ["created_at"])


def downgrade():
    op.drop_index("ix_skribl_views_created", table_name="skribl_views")
    op.drop_index("ix_view_unique", table_name="skribl_views")
    op.drop_index("ix_skribl_views_post_id", table_name="skribl_views")
    op.drop_table("skribl_views")
    op.drop_column("skribl_posts", "views_total")
