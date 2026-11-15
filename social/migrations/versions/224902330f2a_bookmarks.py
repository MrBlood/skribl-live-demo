"""Bookmarks: a post, or a drawing shown outside a post, kept to come back to,
yours alone (the map, part two, item 2; the owner's "All yes" on the bookmarks
mock, Nov 14; docs/SOCIAL-SITE.md section 17).

One table on the site's own chain (social_alembic_version); nothing of
Skribl's is read or altered. social_bookmarks is shaped as social_likes is:

  post_id      the post it keeps, or nothing for one on a drawing
  drawing_id   the drawing shown outside a post it keeps, by its skribl's
               public id (Skribl's: the site keeps no row for a drawing)
  ck_social_bookmarks_on_one   exactly one of the two
  owner_id     whose the post or the drawing is (its maker)
  person_id    who kept it
  created_at

A person keeps a thing once: unique on (person_id, post_id) and on
(person_id, drawing_id), an empty id never colliding with another. Indexed as
the pages read it: yours, newest first (your own page's Bookmarks tab); a
post's and a drawing's (deleting one, and a drawing moving into a post); and
whose (deleting an account). Every foreign key cascades, the net under
deleting in code (bookmarks.py).

THE TABLE AND ITS INDEXES ONLY: no row of any other table is read or written,
so nothing here waits on the data a deploy finds (the house lesson, v309).

The downgrade drops the table.

Revision ID: 224902330f2a
Revises: 9b1e6c3d5a72
Create Date: 2026-11-14
"""
from alembic import op
import sqlalchemy as sa

revision = "224902330f2a"
down_revision = "9b1e6c3d5a72"
branch_labels = None
depends_on = None

BigId = sa.BigInteger().with_variant(sa.Integer(), "sqlite")

#: On a post or on a drawing: exactly one (social/models.py says the same).
ON_ONE = "(post_id IS NOT NULL AND drawing_id IS NULL) OR (post_id IS NULL AND drawing_id IS NOT NULL)"


def upgrade():
    op.create_table(
        "social_bookmarks",
        sa.Column("id", BigId, primary_key=True),
        sa.Column("post_id", BigId, sa.ForeignKey("social_posts.id", ondelete="CASCADE"), nullable=True),
        sa.Column("drawing_id", sa.String(length=32), nullable=True),
        sa.Column("owner_id", BigId, sa.ForeignKey("social_people.id", ondelete="CASCADE"), nullable=False),
        sa.Column("person_id", BigId, sa.ForeignKey("social_people.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(ON_ONE, name="ck_social_bookmarks_on_one"),
    )
    op.create_index("ix_social_bookmarks_person_post", "social_bookmarks", ["person_id", "post_id"], unique=True)
    op.create_index("ix_social_bookmarks_person_drawing", "social_bookmarks", ["person_id", "drawing_id"], unique=True)
    op.create_index("ix_social_bookmarks_person_created", "social_bookmarks", ["person_id", "created_at"])
    op.create_index("ix_social_bookmarks_post_id", "social_bookmarks", ["post_id"])
    op.create_index("ix_social_bookmarks_drawing_id", "social_bookmarks", ["drawing_id"])
    op.create_index("ix_social_bookmarks_owner_id", "social_bookmarks", ["owner_id"])


def downgrade():
    op.drop_index("ix_social_bookmarks_owner_id", table_name="social_bookmarks")
    op.drop_index("ix_social_bookmarks_drawing_id", table_name="social_bookmarks")
    op.drop_index("ix_social_bookmarks_post_id", table_name="social_bookmarks")
    op.drop_index("ix_social_bookmarks_person_created", table_name="social_bookmarks")
    op.drop_index("ix_social_bookmarks_person_drawing", table_name="social_bookmarks")
    op.drop_index("ix_social_bookmarks_person_post", table_name="social_bookmarks")
    op.drop_table("social_bookmarks")
