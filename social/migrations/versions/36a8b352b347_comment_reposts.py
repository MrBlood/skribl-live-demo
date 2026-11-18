"""The comment thread, step 3: repost, quote and bookmark a comment (the
owner's yes, Nov 17, to the Read More Replies mock, "the same choices as a
post", and to A Comment Shared: A, the way to it above, and quoting it;
docs/SOCIAL-SITE.md section 18).

On the site's own chain (social_alembic_version); nothing of Skribl's is read
or altered.

  social_reposts
    post_id        may be nothing now: a repost of a comment has none.
    comment_id     the comment or reply reposted. Goes with it (ON DELETE
                   CASCADE, the net under the code's own deleting).
    ck_social_reposts_on_one   a post or a comment, exactly one (on
                   PostgreSQL added NOT VALID: every row there has a post).
    ix_social_reposts_person_comment   once a person a comment (unique).
    ix_social_reposts_comment_id       a comment's: its count, its going.
  social_posts
    quoted_comment_id   the comment or reply a quote shows small. No foreign
                   key: social_comments points at social_posts already, and
                   a host's create_all sorts the two tables by their keys;
                   every way a comment goes lets go of it in code, as a
                   quoted drawing's id is let go of.
    ck_social_posts_quotes_one   a post, a drawing or a comment, at most one
                   (it said a post or a drawing; on PostgreSQL the old CHECK
                   goes and the new one is added NOT VALID).
    ix_social_posts_quoted_comment_id   a comment's quotes.
  social_bookmarks
    comment_id     the comment or reply kept (ON DELETE CASCADE).
    ck_social_bookmarks_on_one   a post, a drawing or a comment, exactly one
                   (NOT VALID on PostgreSQL).
    ix_social_bookmarks_person_comment   once a person a comment (unique).
    ix_social_bookmarks_comment_id       a comment's: its going.

NO DATA WORK (v309's lesson): columns added nullable with no default, a
NOT NULL let go, foreign keys, CHECKs swapped, indexes; no row of any table
read or written.

The downgrade refuses while a repost, a quote or a bookmark of a comment is
there (none of the old rules has room for one; nothing here deletes them),
saying so before it changes anything; without one, it drops what the upgrade
added and puts the old rules back.

Revision ID: 36a8b352b347
Revises: 5beec18dc5fe
Create Date: 2026-11-17
"""
from alembic import context, op
import sqlalchemy as sa

revision = "36a8b352b347"
down_revision = "5beec18dc5fe"
branch_labels = None
depends_on = None

BigId = sa.BigInteger().with_variant(sa.Integer(), "sqlite")

#: social/models.py says the same.
REPOSTS_ON_ONE = "(post_id IS NULL) <> (comment_id IS NULL)"
QUOTES_ONE = ("(CASE WHEN quoted_post_id IS NULL THEN 0 ELSE 1 END + CASE WHEN quoted_drawing_id IS NULL THEN 0 ELSE 1 END"
              " + CASE WHEN quoted_comment_id IS NULL THEN 0 ELSE 1 END) <= 1")
BOOKMARK_ON_ONE = ("(CASE WHEN post_id IS NULL THEN 0 ELSE 1 END + CASE WHEN drawing_id IS NULL THEN 0 ELSE 1 END"
                   " + CASE WHEN comment_id IS NULL THEN 0 ELSE 1 END) = 1")
#: What they said before.
QUOTES_WAS = "quoted_post_id IS NULL OR quoted_drawing_id IS NULL"
BOOKMARK_WAS = "(post_id IS NOT NULL AND drawing_id IS NULL) OR (post_id IS NULL AND drawing_id IS NOT NULL)"


def upgrade():
    with op.batch_alter_table("social_reposts") as t:
        t.add_column(sa.Column("comment_id", BigId, nullable=True))
        t.alter_column("post_id", existing_type=BigId, nullable=True)
        t.create_foreign_key("fk_social_reposts_comment_id", "social_comments", ["comment_id"], ["id"],
                             ondelete="CASCADE")
        t.create_check_constraint("ck_social_reposts_on_one", REPOSTS_ON_ONE, postgresql_not_valid=True)
    op.create_index("ix_social_reposts_person_comment", "social_reposts", ["person_id", "comment_id"], unique=True)
    op.create_index("ix_social_reposts_comment_id", "social_reposts", ["comment_id"])
    with op.batch_alter_table("social_posts") as t:
        t.add_column(sa.Column("quoted_comment_id", BigId, nullable=True))
        t.drop_constraint("ck_social_posts_quotes_one", type_="check")
        t.create_check_constraint("ck_social_posts_quotes_one", QUOTES_ONE, postgresql_not_valid=True)
    op.create_index("ix_social_posts_quoted_comment_id", "social_posts", ["quoted_comment_id"])
    with op.batch_alter_table("social_bookmarks") as t:
        t.add_column(sa.Column("comment_id", BigId, nullable=True))
        t.create_foreign_key("fk_social_bookmarks_comment_id", "social_comments", ["comment_id"], ["id"],
                             ondelete="CASCADE")
        t.drop_constraint("ck_social_bookmarks_on_one", type_="check")
        t.create_check_constraint("ck_social_bookmarks_on_one", BOOKMARK_ON_ONE, postgresql_not_valid=True)
    op.create_index("ix_social_bookmarks_person_comment", "social_bookmarks", ["person_id", "comment_id"], unique=True)
    op.create_index("ix_social_bookmarks_comment_id", "social_bookmarks", ["comment_id"])


def downgrade():
    if not context.is_offline_mode():
        bind = op.get_bind()
        held = [what for what, sql in (
            ("a repost of a comment", "SELECT 1 FROM social_reposts WHERE comment_id IS NOT NULL LIMIT 1"),
            ("a quote of a comment", "SELECT 1 FROM social_posts WHERE quoted_comment_id IS NOT NULL LIMIT 1"),
            ("a bookmark of a comment", "SELECT 1 FROM social_bookmarks WHERE comment_id IS NOT NULL LIMIT 1"))
            if bind.execute(sa.text(sql)).first() is not None]
        if held:
            raise RuntimeError("The site holds " + ", ".join(held) + ", which going down has no room for. Nothing"
                               " here deletes them: stay at 36a8b352b347.")
    op.drop_index("ix_social_bookmarks_comment_id", table_name="social_bookmarks")
    op.drop_index("ix_social_bookmarks_person_comment", table_name="social_bookmarks")
    with op.batch_alter_table("social_bookmarks") as t:
        t.drop_constraint("ck_social_bookmarks_on_one", type_="check")
        t.create_check_constraint("ck_social_bookmarks_on_one", BOOKMARK_WAS)
        t.drop_constraint("fk_social_bookmarks_comment_id", type_="foreignkey")
        t.drop_column("comment_id")
    op.drop_index("ix_social_posts_quoted_comment_id", table_name="social_posts")
    with op.batch_alter_table("social_posts") as t:
        t.drop_constraint("ck_social_posts_quotes_one", type_="check")
        t.create_check_constraint("ck_social_posts_quotes_one", QUOTES_WAS)
        t.drop_column("quoted_comment_id")
    op.drop_index("ix_social_reposts_comment_id", table_name="social_reposts")
    op.drop_index("ix_social_reposts_person_comment", table_name="social_reposts")
    with op.batch_alter_table("social_reposts") as t:
        t.drop_constraint("ck_social_reposts_on_one", type_="check")
        t.drop_constraint("fk_social_reposts_comment_id", type_="foreignkey")
        t.alter_column("post_id", existing_type=BigId, nullable=False)
        t.drop_column("comment_id")
