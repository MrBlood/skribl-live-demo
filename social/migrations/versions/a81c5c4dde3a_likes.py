"""Likes: a heart on a post or a drawing, its count, and who (the owner's D on
the likes mock, Nov 13; docs/SOCIAL-SITE.md, "Built: likes").

One table on the site's own chain (social_alembic_version); nothing of
Skribl's is read or altered. social_likes is shaped as social_comments is:

  post_id      the post it is on, or nothing for one on a drawing
  drawing_id   the drawing shown outside a post it is on, by its skribl's
               public id (Skribl's: the site keeps no row for a drawing)
  ck_social_likes_on_one   exactly one of the two
  owner_id     whose the post or the drawing is (its maker)
  person_id    who liked it
  at_ms        where the drawing's replay was when the heart was tapped while
               it played, on the drawing's own clock; nothing when it was not
               playing (it counts all the same)
  created_at

A person likes a thing once: unique on (person_id, post_id) and on
(person_id, drawing_id), an empty id never colliding with another. Indexed as
the pages read it: a thing's likes newest first (its count, and who liked
it), and whose, newest first (Activity's likes on what you made). Every
foreign key cascades, the net under deleting in code (likes.py).

The downgrade drops the table.

Revision ID: a81c5c4dde3a
Revises: c276c1445bc1
Create Date: 2026-11-13
"""
from alembic import op
import sqlalchemy as sa

revision = "a81c5c4dde3a"
down_revision = "c276c1445bc1"
branch_labels = None
depends_on = None

BigId = sa.BigInteger().with_variant(sa.Integer(), "sqlite")

#: On a post or on a drawing: exactly one (social/models.py says the same).
ON_ONE = "(post_id IS NOT NULL AND drawing_id IS NULL) OR (post_id IS NULL AND drawing_id IS NOT NULL)"


def upgrade():
    op.create_table(
        "social_likes",
        sa.Column("id", BigId, primary_key=True),
        sa.Column("post_id", BigId, sa.ForeignKey("social_posts.id", ondelete="CASCADE"), nullable=True),
        sa.Column("drawing_id", sa.String(length=32), nullable=True),
        sa.Column("owner_id", BigId, sa.ForeignKey("social_people.id", ondelete="CASCADE"), nullable=False),
        sa.Column("person_id", BigId, sa.ForeignKey("social_people.id", ondelete="CASCADE"), nullable=False),
        sa.Column("at_ms", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(ON_ONE, name="ck_social_likes_on_one"),
    )
    op.create_index("ix_social_likes_person_post", "social_likes", ["person_id", "post_id"], unique=True)
    op.create_index("ix_social_likes_person_drawing", "social_likes", ["person_id", "drawing_id"], unique=True)
    op.create_index("ix_social_likes_post_created", "social_likes", ["post_id", "created_at"])
    op.create_index("ix_social_likes_drawing_created", "social_likes", ["drawing_id", "created_at"])
    op.create_index("ix_social_likes_owner_created", "social_likes", ["owner_id", "created_at"])


def downgrade():
    op.drop_index("ix_social_likes_owner_created", table_name="social_likes")
    op.drop_index("ix_social_likes_drawing_created", table_name="social_likes")
    op.drop_index("ix_social_likes_post_created", table_name="social_likes")
    op.drop_index("ix_social_likes_person_drawing", table_name="social_likes")
    op.drop_index("ix_social_likes_person_post", table_name="social_likes")
    op.drop_table("social_likes")
