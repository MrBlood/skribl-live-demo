"""How the replies under a comment show, as each person picked (Settings,
"Replies"; the owner's "All yes", Nov 28, to the tree mock; comments.py,
"THE TREE").

On the site's own chain (social_alembic_version); nothing of Skribl's is read
or altered:

  social_people.replies_view   'line' or 'tree', as they last picked in
                               Settings; nothing until they pick (In a line,
                               where everyone starts)

NO DATA WORK: every account starts with nothing picked.

The downgrade drops the column.

Revision ID: c9e4a7b2f815
Revises: d3a8f1c6e2b4
Create Date: 2026-11-28
"""
from alembic import op
import sqlalchemy as sa

revision = "c9e4a7b2f815"
down_revision = "d3a8f1c6e2b4"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("social_people") as t:
        t.add_column(sa.Column("replies_view", sa.String(length=8), nullable=True))


def downgrade():
    with op.batch_alter_table("social_people") as t:
        t.drop_column("replies_view")
