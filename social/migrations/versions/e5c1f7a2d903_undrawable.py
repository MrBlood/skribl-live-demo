"""Draw back: why a post's drawing can't be drawn back on yet, so its row
offers no pen there (DECISIONS.md, "Draw back: no pen where it can't be done
yet").

On the site's own chain (social_alembic_version); nothing of Skribl's is read
or altered.

  social_posts
    undrawable    "photo", "music", "pages" or "recolors", read from the
                  drawing as it was posted; None where it can be, and for
                  every post before this column (its pen stays, and opening
                  it says why when it can't).

NO DATA WORK: the posts there keep their pens, as before.

The downgrade drops the column: every post's pen comes back, answered when
opened, as before.

Revision ID: e5c1f7a2d903
Revises: d7a3b19e4c20
Create Date: 2026-11-19
"""
from alembic import op
import sqlalchemy as sa

revision = "e5c1f7a2d903"
down_revision = "d7a3b19e4c20"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("social_posts") as t:
        t.add_column(sa.Column("undrawable", sa.String(length=12), nullable=True))


def downgrade():
    with op.batch_alter_table("social_posts") as t:
        t.drop_column("undrawable")
