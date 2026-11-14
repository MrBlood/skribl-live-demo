"""Your Likes: the posts a person liked, newest liked first (the map's step 4,
a profile's tabs; the owner's "Yes" to the step 4 mock, Nov 14).

On the site's own chain (social_alembic_version); nothing of Skribl's is read
or altered. One index on social_likes, for the read your own profile's Likes
tab makes (likes.liked_page): who liked, newest first.

  ix_social_likes_person_created    person_id, created_at

The table's other indexes serve a thing's likes and whose they are; the
pair's (person_id, post_id) finds yours but not in the order you liked them.

The downgrade drops the index.

Revision ID: e3fc16c00d16
Revises: 4cdc4af46a77
Create Date: 2026-11-14
"""
from alembic import op

revision = "e3fc16c00d16"
down_revision = "4cdc4af46a77"
branch_labels = None
depends_on = None


def upgrade():
    op.create_index("ix_social_likes_person_created", "social_likes", ["person_id", "created_at"])


def downgrade():
    op.drop_index("ix_social_likes_person_created", table_name="social_likes")
