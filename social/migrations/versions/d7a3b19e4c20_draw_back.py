"""Draw back (the owner's "All yes", Nov 19; DECISIONS.md, "Draw back,
mocked"): a post that answers a drawing by drawing with it.

On the site's own chain (social_alembic_version); nothing of Skribl's is read
or altered.

  social_posts
    is_drawback          a draw-back, kept for good (as is_quote is).
    drawn_on_id          the post it draws back on, while it is there
                         (fk_social_posts_drawn_on_id, ON DELETE SET NULL).
    drawn_on_owner_id    whose that post is (fk_social_posts_drawn_on_owner_id,
                         ON DELETE SET NULL).
    ix_social_posts_drawn_on_id               a post's draw-backs.
    ix_social_posts_drawn_on_owner_created    Activity's, newest first.

NO DATA WORK: every post there is no draw-back.

The downgrade drops the three columns: a draw-back stays a post with its
drawing, which already holds both hands.

Revision ID: d7a3b19e4c20
Revises: c0b35ced9777
Create Date: 2026-11-19
"""
from alembic import op
import sqlalchemy as sa

revision = "d7a3b19e4c20"
down_revision = "c0b35ced9777"
branch_labels = None
depends_on = None

BigId = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade():
    with op.batch_alter_table("social_posts") as t:
        t.add_column(sa.Column("is_drawback", sa.Boolean(), nullable=False, server_default=sa.false()))
        t.add_column(sa.Column("drawn_on_id", BigId, nullable=True))
        t.add_column(sa.Column("drawn_on_owner_id", BigId, nullable=True))
        t.create_foreign_key("fk_social_posts_drawn_on_id", "social_posts", ["drawn_on_id"], ["id"],
                             ondelete="SET NULL", postgresql_not_valid=True)
        t.create_foreign_key("fk_social_posts_drawn_on_owner_id", "social_people", ["drawn_on_owner_id"], ["id"],
                             ondelete="SET NULL", postgresql_not_valid=True)
    op.create_index("ix_social_posts_drawn_on_id", "social_posts", ["drawn_on_id"])
    op.create_index("ix_social_posts_drawn_on_owner_created", "social_posts", ["drawn_on_owner_id", "created_at"])


def downgrade():
    op.drop_index("ix_social_posts_drawn_on_owner_created", table_name="social_posts")
    op.drop_index("ix_social_posts_drawn_on_id", table_name="social_posts")
    with op.batch_alter_table("social_posts") as t:
        t.drop_constraint("fk_social_posts_drawn_on_owner_id", type_="foreignkey")
        t.drop_constraint("fk_social_posts_drawn_on_id", type_="foreignkey")
        t.drop_column("drawn_on_owner_id")
        t.drop_column("drawn_on_id")
        t.drop_column("is_drawback")
