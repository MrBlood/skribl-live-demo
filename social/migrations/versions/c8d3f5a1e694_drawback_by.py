"""Her say: who can draw back on a post, its maker's own choice (the owner's
"All yes to everything", Nov 20; DECISIONS.md, "Her say, mocked" and "Her
say: who can draw back").

On the site's own chain (social_alembic_version); nothing of Skribl's is read
or altered.

  social_posts
    drawback_by    who can draw back on it, as its maker chose: None for
                   everyone signed in, "follow" for the people its maker
                   follows, "nobody" for nobody else. Its maker always can.

NO DATA WORK: every post there stays open to everyone, as it was.

The downgrade drops the column: every post is open to everyone again. The
draw-backs made meanwhile stay.

Revision ID: c8d3f5a1e694
Revises: a4c9e1b7d352
Create Date: 2026-11-20
"""
from alembic import op
import sqlalchemy as sa

revision = "c8d3f5a1e694"
down_revision = "a4c9e1b7d352"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("social_posts") as t:
        t.add_column(sa.Column("drawback_by", sa.String(8), nullable=True))


def downgrade():
    with op.batch_alter_table("social_posts") as t:
        t.drop_column("drawback_by")
