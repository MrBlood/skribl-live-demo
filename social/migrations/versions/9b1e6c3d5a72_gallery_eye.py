"""The eye on your own Gallery tab: a post's drawing hidden from the Gallery
(the owner's "Yes, the eye in view", Nov 14).

On the site's own chain (social_alembic_version); nothing of Skribl's is read
or altered. One column on social_posts, nullable:

  social_posts.gallery_hidden_at   when its maker hid its drawing from the
                                   Gallery (None: in it)

The post stays on Home and in its maker's Posts; only the Gallery of
everyone, the first visit and the maker's Gallery as anybody else sees it
leave it out (social/gallery.py). Nullable, with no default and no index (the
Gallery filters on it beside the indexes it already reads, as it does on
taken_down_at), so no data work and nothing to hold a deploy: every post
there is stays in the Gallery. The downgrade drops it.

Revision ID: 9b1e6c3d5a72
Revises: e3fc16c00d16
Create Date: 2026-11-14
"""
from alembic import op
import sqlalchemy as sa

revision = "9b1e6c3d5a72"
down_revision = "e3fc16c00d16"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("social_posts") as t:
        t.add_column(sa.Column("gallery_hidden_at", sa.DateTime(timezone=True), nullable=True))


def downgrade():
    with op.batch_alter_table("social_posts") as t:
        t.drop_column("gallery_hidden_at")
