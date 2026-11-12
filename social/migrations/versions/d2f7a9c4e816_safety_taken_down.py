"""Safety: taken down (phase 1, piece 5: your Reports page).

docs/SOCIAL-SITE.md, section 5, build order item 5, from the owner's "all
yes" on the Safety mock (Nov 12): an admin takes down a person or a post, and
it is hidden for everybody else at once, with a copy kept. One column on each
of two tables, nullable, on the site's own chain:

  social_people.taken_down_at   when an admin took the person down
  social_posts.taken_down_at    when an admin took the post down

Nullable, with no default and no index (the pages filter on it beside the
indexes they already use), so no data work and nothing to hold a deploy;
the downgrade drops them.

Revision ID: d2f7a9c4e816
Revises: c8e1d4a7b905
Create Date: 2026-11-12
"""
from alembic import op
import sqlalchemy as sa

revision = "d2f7a9c4e816"
down_revision = "c8e1d4a7b905"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("social_people") as t:
        t.add_column(sa.Column("taken_down_at", sa.DateTime(timezone=True), nullable=True))
    with op.batch_alter_table("social_posts") as t:
        t.add_column(sa.Column("taken_down_at", sa.DateTime(timezone=True), nullable=True))


def downgrade():
    with op.batch_alter_table("social_posts") as t:
        t.drop_column("taken_down_at")
    with op.batch_alter_table("social_people") as t:
        t.drop_column("taken_down_at")
