"""Comments: words, and answers one level under them (phase 2, comments).

docs/SOCIAL-SITE.md, "Built: phase 2, comments", from the owner's "all yes on
both" (Nov 12) to the comments mock. One new table on the site's own chain
(social_alembic_version); nothing of Skribl's is read or altered:

  social_comments  public_id   the comment's own address (#c-<public_id> on
                               its post's page; /social/c/<public_id>/delete)
                   post_id     the post it is on; goes with it (ON DELETE
                               CASCADE, and posts.drop_post deletes them first,
                               in code, so a database without the cascade
                               loses nothing)
                   person_id   who wrote it; goes with them (the same, through
                               accounts.delete_person)
                   parent_id   the top-level comment an answer sits under, or
                               nothing for a comment (answers are one level
                               deep); goes with it
                   words       plain text, up to 500 characters, maybe none
                               when a drawing says it
                   skribl_id   a drawing answer's skribl (Skribl's public id),
                               posted unlisted through create_post in the same
                               request; nothing for words alone
                   created_at  when
                   taken_down_at  when an admin took it down (Your Reports)

Indexed as the pages read it: by address (unique), a post's comments newest
first (post_id, created_at), a comment's answers oldest first (parent_id,
created_at), a person's own (deleting an account), and by skribl (a drawing
answer, found from its drawing). A new table, so no data work and nothing to
hold a deploy; the downgrade drops it.

Revision ID: e4b8c2a91f37
Revises: d2f7a9c4e816
Create Date: 2026-11-12
"""
from alembic import op
import sqlalchemy as sa

revision = "e4b8c2a91f37"
down_revision = "d2f7a9c4e816"
branch_labels = None
depends_on = None

BigId = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade():
    op.create_table(
        "social_comments",
        sa.Column("id", BigId, primary_key=True),
        sa.Column("public_id", sa.String(length=24), nullable=False),
        sa.Column("post_id", BigId, sa.ForeignKey("social_posts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("person_id", BigId, sa.ForeignKey("social_people.id", ondelete="CASCADE"), nullable=False),
        sa.Column("parent_id", BigId, sa.ForeignKey("social_comments.id", ondelete="CASCADE"), nullable=True),
        sa.Column("words", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("skribl_id", sa.String(length=32), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("taken_down_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_social_comments_public_id", "social_comments", ["public_id"], unique=True)
    op.create_index("ix_social_comments_post_created", "social_comments", ["post_id", "created_at"])
    op.create_index("ix_social_comments_parent_created", "social_comments", ["parent_id", "created_at"])
    op.create_index("ix_social_comments_person_id", "social_comments", ["person_id"])
    op.create_index("ix_social_comments_skribl_id", "social_comments", ["skribl_id"])


def downgrade():
    for name in ("ix_social_comments_skribl_id", "ix_social_comments_person_id",
                 "ix_social_comments_parent_created", "ix_social_comments_post_created",
                 "ix_social_comments_public_id"):
        op.drop_index(name, table_name="social_comments")
    op.drop_table("social_comments")
