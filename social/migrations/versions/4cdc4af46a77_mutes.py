"""Mutes: who muted whom (the owner's "Yes to all" on the mute mock, C, quiet
everywhere, Nov 13; docs/SOCIAL-SITE.md, "Built: mutes").

On the site's own chain (social_alembic_version); nothing of Skribl's is read
or altered:

  social_mutes              one row a pair:
    muter_id                who muted
    muted_id                whom
    created_at              when
    ck_social_mutes_not_self     nobody mutes themselves

Unique on the pair (the once-a-request read of whom a person muted, and one
row a pair); indexed by whose, newest first (Settings' Muted), and by whom
(deleting an account takes its mutes both ways). Unmuting deletes the row.
Both foreign keys cascade, the net under deleting in code (mutes.py,
accounts.delete_person).

The downgrade drops the table.

Revision ID: 4cdc4af46a77
Revises: 1757a4385be8
Create Date: 2026-11-13
"""
from alembic import op
import sqlalchemy as sa

revision = "4cdc4af46a77"
down_revision = "1757a4385be8"
branch_labels = None
depends_on = None

BigId = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade():
    op.create_table(
        "social_mutes",
        sa.Column("id", BigId, primary_key=True),
        sa.Column("muter_id", BigId, sa.ForeignKey("social_people.id", ondelete="CASCADE"), nullable=False),
        sa.Column("muted_id", BigId, sa.ForeignKey("social_people.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("muter_id <> muted_id", name="ck_social_mutes_not_self"),
    )
    op.create_index("ix_social_mutes_pair", "social_mutes", ["muter_id", "muted_id"], unique=True)
    op.create_index("ix_social_mutes_muter_created", "social_mutes", ["muter_id", "created_at"])
    op.create_index("ix_social_mutes_muted_id", "social_mutes", ["muted_id"])


def downgrade():
    op.drop_index("ix_social_mutes_muted_id", table_name="social_mutes")
    op.drop_index("ix_social_mutes_muter_created", table_name="social_mutes")
    op.drop_index("ix_social_mutes_pair", table_name="social_mutes")
    op.drop_table("social_mutes")
