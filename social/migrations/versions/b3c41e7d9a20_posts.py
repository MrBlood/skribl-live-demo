"""Posts: a person's words and a skribl (phase 1, piece 4).

docs/SOCIAL-SITE.md, section 5, build order item 4, from the owner's "all
yes" on the phase 1 mocks and on piece 4's choices (Nov 11). One new table on
the site's own chain (social_alembic_version); nothing of Skribl's is read or
altered:

  social_posts   public_id   the post's address (/social/p/<public_id>)
                 person_id   who posted it; goes with them (ON DELETE CASCADE,
                             and accounts.delete_person deletes it first, with
                             its skribl, so a database without the cascade
                             loses nothing)
                 words       plain text, up to 500 characters, maybe none
                 skribl_id   the skribl it holds (Skribl's public id), posted
                             through create_post in the same request
                 created_at  when

Indexed as the pages read it: by address (unique), the feed newest first
(created_at, public_id), a person's own newest first ("More from"), and by
skribl. A new table, so no data work and nothing to hold a deploy; the
downgrade drops it.

Revision ID: b3c41e7d9a20
Revises: fa82723cacc4
Create Date: 2026-11-11
"""
from alembic import op
import sqlalchemy as sa

revision = "b3c41e7d9a20"
down_revision = "fa82723cacc4"
branch_labels = None
depends_on = None

BigId = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade():
    op.create_table(
        "social_posts",
        sa.Column("id", BigId, primary_key=True),
        sa.Column("public_id", sa.String(length=24), nullable=False),
        sa.Column("person_id", BigId, sa.ForeignKey("social_people.id", ondelete="CASCADE"), nullable=False),
        sa.Column("words", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("skribl_id", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_social_posts_public_id", "social_posts", ["public_id"], unique=True)
    op.create_index("ix_social_posts_created", "social_posts", ["created_at", "public_id"])
    op.create_index("ix_social_posts_person_created", "social_posts", ["person_id", "created_at"])
    op.create_index("ix_social_posts_skribl_id", "social_posts", ["skribl_id"])


def downgrade():
    op.drop_index("ix_social_posts_skribl_id", table_name="social_posts")
    op.drop_index("ix_social_posts_person_created", table_name="social_posts")
    op.drop_index("ix_social_posts_created", table_name="social_posts")
    op.drop_index("ix_social_posts_public_id", table_name="social_posts")
    op.drop_table("social_posts")
