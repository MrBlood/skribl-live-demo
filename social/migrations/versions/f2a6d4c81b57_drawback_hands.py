"""Draw back: whose hands a draw-back holds and how long each drew, so its
line can say "Drawn in 15 sec + 5 sec" and its play button "Ana + Theo · 20
sec" (DECISIONS.md, "What a draw-back says").

On the site's own chain (social_alembic_version); nothing of Skribl's is read
or altered.

  social_posts
    hands_json    JSON, [[person id, ms], ...] in the order they play; None
                  for a post that is not a draw-back, and for every draw-back
                  from before this column.

NO DATA WORK: a draw-back from before is said from the two drawings' stored
lines while its original is there (drawback.hands_from_lines), and as before
once it is not.

The downgrade drops the column: every draw-back says its drawing's own
"drawn in" again, as before.

Revision ID: f2a6d4c81b57
Revises: e5c1f7a2d903
Create Date: 2026-11-19
"""
from alembic import op
import sqlalchemy as sa

revision = "f2a6d4c81b57"
down_revision = "e5c1f7a2d903"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("social_posts") as t:
        t.add_column(sa.Column("hands_json", sa.Text(), nullable=True))


def downgrade():
    with op.batch_alter_table("social_posts") as t:
        t.drop_column("hands_json")
