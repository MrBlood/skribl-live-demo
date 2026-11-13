"""Follows: who follows whom, and what Home opens on (the owner's "Yes to
all" on the follow mock, B, Nov 13; docs/SOCIAL-SITE.md, "Built: follows").

On the site's own chain (social_alembic_version); nothing of Skribl's is read
or altered:

  social_follows            one row a pair:
    follower_id             who follows
    followed_id             whom
    created_at              when they first followed
    ended_at                when they unfollowed, or nothing while they
                            follow: the row is kept, so following again
                            never tells them twice (Activity reads
                            created_at)
    ck_social_follows_not_self   nobody follows themselves
  social_people.home_feed   what Home opens on, 'following' or 'everyone',
                            as they last picked on its pill; nothing until
                            they pick

Unique on the pair; indexed both ways, newest first: whom a person follows
(their Following list, and Home's Following through the pair) and who
follows a person (their Followers, their "Followed by…" line, Activity).
Both foreign keys cascade, the net under deleting in code (follows.py,
accounts.delete_person, safety.py's block).

The downgrade drops the table and the column.

Revision ID: 1757a4385be8
Revises: a81c5c4dde3a
Create Date: 2026-11-13
"""
from alembic import op
import sqlalchemy as sa

revision = "1757a4385be8"
down_revision = "a81c5c4dde3a"
branch_labels = None
depends_on = None

BigId = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade():
    op.create_table(
        "social_follows",
        sa.Column("id", BigId, primary_key=True),
        sa.Column("follower_id", BigId, sa.ForeignKey("social_people.id", ondelete="CASCADE"), nullable=False),
        sa.Column("followed_id", BigId, sa.ForeignKey("social_people.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("follower_id <> followed_id", name="ck_social_follows_not_self"),
    )
    op.create_index("ix_social_follows_pair", "social_follows", ["follower_id", "followed_id"], unique=True)
    op.create_index("ix_social_follows_follower_created", "social_follows", ["follower_id", "created_at"])
    op.create_index("ix_social_follows_followed_created", "social_follows", ["followed_id", "created_at"])
    with op.batch_alter_table("social_people") as t:
        t.add_column(sa.Column("home_feed", sa.String(length=12), nullable=True))


def downgrade():
    with op.batch_alter_table("social_people") as t:
        t.drop_column("home_feed")
    op.drop_index("ix_social_follows_followed_created", table_name="social_follows")
    op.drop_index("ix_social_follows_follower_created", table_name="social_follows")
    op.drop_index("ix_social_follows_pair", table_name="social_follows")
    op.drop_table("social_follows")
