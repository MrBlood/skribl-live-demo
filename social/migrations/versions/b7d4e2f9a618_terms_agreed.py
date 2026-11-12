"""Which Terms a person agreed to by joining, and when (the owner's "all
yes" to A, Nov 12: Join says "Joining means you agree to the Terms and the
Community rules. Privacy says what we keep.").

Two columns on social_people, nullable, on the site's own chain:

  terms_version    rules.TERMS_VERSION when they pressed Join
  terms_agreed_at  when they pressed it

Nullable, with no default: people who joined before Join said so were never
asked, and their rows say nothing rather than something made up. No index
(nothing reads by them yet), no data work, nothing to hold a deploy; the
downgrade drops them.

Revision ID: b7d4e2f9a618
Revises: e4b8c2a91f37
Create Date: 2026-11-12
"""
from alembic import op
import sqlalchemy as sa

revision = "b7d4e2f9a618"
down_revision = "e4b8c2a91f37"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("social_people") as t:
        t.add_column(sa.Column("terms_version", sa.String(length=16), nullable=True))
        t.add_column(sa.Column("terms_agreed_at", sa.DateTime(timezone=True), nullable=True))


def downgrade():
    with op.batch_alter_table("social_people") as t:
        t.drop_column("terms_agreed_at")
        t.drop_column("terms_version")
