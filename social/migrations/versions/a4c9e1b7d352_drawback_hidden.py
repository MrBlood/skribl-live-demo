"""Her say: a draw-back hidden from the post it draws back on, by that post's
maker (the owner's "All yes to everything", Nov 20; DECISIONS.md, "Her say,
mocked" and "Her say: hiding a draw-back").

On the site's own chain (social_alembic_version); nothing of Skribl's is read
or altered.

  social_posts
    drawn_on_hidden_at    when the maker of the post it draws back on hid it
                          from that post (the eye on her own strip); None
                          while it is on her post. The draw-back itself is
                          untouched: its maker's page, Home and its own page
                          show it as before.

NO DATA WORK: every draw-back there stays on the post it draws back on.

The downgrade drops the column: every hidden draw-back is back on its post.

Revision ID: a4c9e1b7d352
Revises: f2a6d4c81b57
Create Date: 2026-11-20
"""
from alembic import op
import sqlalchemy as sa

revision = "a4c9e1b7d352"
down_revision = "f2a6d4c81b57"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("social_posts") as t:
        t.add_column(sa.Column("drawn_on_hidden_at", sa.DateTime(timezone=True), nullable=True))


def downgrade():
    with op.batch_alter_table("social_posts") as t:
        t.drop_column("drawn_on_hidden_at")
