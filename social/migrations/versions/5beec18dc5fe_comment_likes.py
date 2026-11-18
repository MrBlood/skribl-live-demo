"""The comment thread, step 2: likes on comments (the owner's yes, Nov 17, to
the Read More Replies mock, "the same choices as a post"; docs/SOCIAL-SITE.md
section 18).

On the site's own chain (social_alembic_version); nothing of Skribl's is read
or altered. On social_likes:

  comment_id     the comment or reply it is on; nothing for a post's or a
                 drawing's. Goes with it (ON DELETE CASCADE, the net under
                 the code's own deleting: likes.drop_comment_likes).
  ck_social_likes_on_one   a post, a drawing or a comment, exactly one (it
                 said a post or a drawing). On PostgreSQL the old CHECK goes
                 and the new one is added NOT VALID: no row read under the
                 lock, and every row there, a post's or a drawing's, is one
                 the new CHECK allows.
  ix_social_likes_person_comment    once a person, once a comment (unique).
  ix_social_likes_comment_created   a comment's likes, newest first.

NO DATA WORK (v309's lesson): a column added nullable with no default, its
foreign key, a CHECK swapped, two indexes; no row of any table read or
written.

The downgrade refuses while a like on a comment is there (the old CHECK has
no room for one; nothing here deletes them), saying so before it changes
anything; without one, it drops what the upgrade added and puts the old
CHECK back.

Revision ID: 5beec18dc5fe
Revises: 3b76663f9417
Create Date: 2026-11-17
"""
from alembic import context, op
import sqlalchemy as sa

revision = "5beec18dc5fe"
down_revision = "3b76663f9417"
branch_labels = None
depends_on = None

BigId = sa.BigInteger().with_variant(sa.Integer(), "sqlite")

#: A post, a drawing or a comment: exactly one (social/models.py LIKE_ON_ONE).
ON_ONE = ("(CASE WHEN post_id IS NULL THEN 0 ELSE 1 END + CASE WHEN drawing_id IS NULL THEN 0 ELSE 1 END"
          " + CASE WHEN comment_id IS NULL THEN 0 ELSE 1 END) = 1")
#: What it said before: a post or a drawing.
WAS = "(post_id IS NOT NULL AND drawing_id IS NULL) OR (post_id IS NULL AND drawing_id IS NOT NULL)"


def upgrade():
    with op.batch_alter_table("social_likes") as t:
        t.add_column(sa.Column("comment_id", BigId, nullable=True))
        t.create_foreign_key("fk_social_likes_comment_id", "social_comments", ["comment_id"], ["id"],
                             ondelete="CASCADE")
        t.drop_constraint("ck_social_likes_on_one", type_="check")
        t.create_check_constraint("ck_social_likes_on_one", ON_ONE, postgresql_not_valid=True)
    op.create_index("ix_social_likes_person_comment", "social_likes", ["person_id", "comment_id"], unique=True)
    op.create_index("ix_social_likes_comment_created", "social_likes", ["comment_id", "created_at"])


def downgrade():
    if not context.is_offline_mode() and op.get_bind().execute(
            sa.text("SELECT 1 FROM social_likes WHERE comment_id IS NOT NULL LIMIT 1")).first() is not None:
        raise RuntimeError("social_likes holds likes on comments, which going down has no room for. Nothing here"
                           " deletes them: stay at 5beec18dc5fe.")
    op.drop_index("ix_social_likes_comment_created", table_name="social_likes")
    op.drop_index("ix_social_likes_person_comment", table_name="social_likes")
    with op.batch_alter_table("social_likes") as t:
        t.drop_constraint("ck_social_likes_on_one", type_="check")
        t.create_check_constraint("ck_social_likes_on_one", WAS)
        t.drop_constraint("fk_social_likes_comment_id", type_="foreignkey")
        t.drop_column("comment_id")
