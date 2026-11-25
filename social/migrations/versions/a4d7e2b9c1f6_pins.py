"""Pins: one post of your own kept first on your page's Posts tab (the owner's
idea, Nov 23; the Pin mock's A and A, the owner's "all yes", Nov 25;
docs/SOCIAL-SITE.md section 40).

One table on the site's own chain (social_alembic_version); nothing of
Skribl's is read or altered. social_pins:

  person_id    whose page it leads (one a person: unique)
  post_id      the post pinned, always their own (pins.py)
  created_at

Indexed as it is read: by person (their page) and by post (deleting one).
Every foreign key cascades, the net under deleting in code (pins.py).

THE TABLE AND ITS INDEXES ONLY: no row of any other table is read or written,
so nothing here waits on the data a deploy finds (the house lesson, v309).

The downgrade drops the table.

Revision ID: a4d7e2b9c1f6
Revises: c8d3f5a1e694
Create Date: 2026-11-25
"""
from alembic import op
import sqlalchemy as sa

revision = "a4d7e2b9c1f6"
down_revision = "c8d3f5a1e694"
branch_labels = None
depends_on = None

BigId = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade():
    op.create_table(
        "social_pins",
        sa.Column("id", BigId, primary_key=True),
        sa.Column("person_id", BigId, sa.ForeignKey("social_people.id", ondelete="CASCADE"), nullable=False),
        sa.Column("post_id", BigId, sa.ForeignKey("social_posts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_social_pins_person_id", "social_pins", ["person_id"], unique=True)
    op.create_index("ix_social_pins_post_id", "social_pins", ["post_id"])


def downgrade():
    op.drop_index("ix_social_pins_post_id", table_name="social_pins")
    op.drop_index("ix_social_pins_person_id", table_name="social_pins")
    op.drop_table("social_pins")
