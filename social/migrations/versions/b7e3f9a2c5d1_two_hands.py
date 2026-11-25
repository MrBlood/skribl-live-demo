"""Draw back, two hands: a draw-back that keeps its maker's strokes alone
and points to the drawing it answered (the owner's "all yes", Nov 25, to the
Two Hands mock: its nine answers, A each, and its first step, behind the
owner's switch; docs/SOCIAL-SITE.md section 41).

On the site's own chain (social_alembic_version); nothing of Skribl's is read
or altered.

  social_posts
    two_hands            true when the post's drawing holds its maker's
                         strokes alone (the site lays the original's under
                         them as it plays); false on every post until the
                         owner's switch is on, and on every post from before
    drawn_on_skribl_id   the drawing it answered, as it was: Skribl's id

  social_two_hands       what a two-hands draw-back keeps beside its own
                         drawing, one row a post, going with the post: the
                         picture it rests on while the drawing it answered is
                         there (both hands), and the line both hands make

NO DATA WORK: every draw-back from before stays as it is, one joined drawing
(the eighth answer).

The downgrade drops the table and the two columns. A two-hands draw-back
made meanwhile then plays its maker's strokes alone, as it would once the
drawing it answered had gone.

Revision ID: b7e3f9a2c5d1
Revises: a4d7e2b9c1f6
Create Date: 2026-11-25
"""
from alembic import op
import sqlalchemy as sa

revision = "b7e3f9a2c5d1"
down_revision = "a4d7e2b9c1f6"
branch_labels = None
depends_on = None

BigId = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade():
    with op.batch_alter_table("social_posts") as t:
        t.add_column(sa.Column("two_hands", sa.Boolean(), nullable=False, server_default=sa.false()))
        t.add_column(sa.Column("drawn_on_skribl_id", sa.String(32), nullable=True))
    op.create_table(
        "social_two_hands",
        sa.Column("post_id", BigId, sa.ForeignKey("social_posts.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("picture", sa.Text(), nullable=True),
        sa.Column("line_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade():
    op.drop_table("social_two_hands")
    with op.batch_alter_table("social_posts") as t:
        t.drop_column("drawn_on_skribl_id")
        t.drop_column("two_hands")
