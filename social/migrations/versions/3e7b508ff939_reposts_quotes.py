"""Reposts and quote posts (the map, part two, item 3; the owner's "All yes" on
the reposts mock, Nov 14; docs/SOCIAL-SITE.md section 17).

On the site's own chain (social_alembic_version); nothing of Skribl's is read
or altered. One table, and columns on social_posts:

  social_reposts               one person showing a post to the people who
                               follow them, once:
    person_id                  who reposted it
    post_id                    the post (the original)
    owner_id                   whose the post is (its author)
    created_at
  social_posts.is_quote        a quote post, for good (false for every post
                               there is: the server default, which on
                               PostgreSQL 11 and later is a catalogue entry,
                               no row rewritten)
  social_posts.quoted_post_id  the post it quotes, while it is there (ON
                               DELETE SET NULL: a quote outlives its
                               original, its small card saying it is gone)
  social_posts.quoted_drawing_id   the drawing shown outside a post it
                               quotes, by its skribl's public id
  social_posts.quoted_owner_id whose that is (ON DELETE SET NULL)
  social_posts.skribl_id       no longer required: a quote of words alone has
                               no drawing of its own (dropping NOT NULL is a
                               catalogue change; no row is read)

and two CHECKs: a post has a drawing or is a quote; a quote shows a post or
a drawing, never both. A person reposts a post once (unique on the pair).
Indexed as the pages read them: a person's reposts newest first (their Posts
tab, Home's Following), a post's (its count, its going), whose newest first
(Activity); a post's quotes and a drawing's (the counts, their going and
moving), and quotes of what a person made, newest first (Activity). Every
foreign key is the net under deleting in code (reposts.py).

THE TABLE, THE COLUMNS AND THEIR INDEXES ONLY: nothing reads a drawing or
works anything out from the rows a deploy finds (the house lesson, v309).
PostgreSQL adds the columns and drops NOT NULL in its catalogue, and adds
the four constraints NOT VALID (each holds for every row written from now
on; the rows already there hold nothing in the new columns, so there is
nothing to check them against, and no scan waits under the table's lock);
its three new indexes are built from social_posts' own narrow columns, none
of them JSON. On SQLite batch mode rebuilds social_posts in place with the
constraints, its rows copied as they are.

The downgrade drops what the upgrade added. Going down puts NOT NULL back on
skribl_id, so it refuses while a quote of words alone is there, saying so
before it changes anything (one row asked for, on skribl_id's own index):
those are posts the site has, and nothing here deletes them. (SQLite runs
no DDL in a transaction, so a refusal part-way would leave the table half
changed; asking first leaves it whole.)

Revision ID: 3e7b508ff939
Revises: 224902330f2a
Create Date: 2026-11-14
"""
from alembic import context, op
import sqlalchemy as sa

revision = "3e7b508ff939"
down_revision = "224902330f2a"
branch_labels = None
depends_on = None

BigId = sa.BigInteger().with_variant(sa.Integer(), "sqlite")

#: social/models.py says the same.
DRAWN_OR_QUOTE = "skribl_id IS NOT NULL OR is_quote"
QUOTES_ONE = "quoted_post_id IS NULL OR quoted_drawing_id IS NULL"


def upgrade():
    op.create_table(
        "social_reposts",
        sa.Column("id", BigId, primary_key=True),
        sa.Column("person_id", BigId, sa.ForeignKey("social_people.id", ondelete="CASCADE"), nullable=False),
        sa.Column("post_id", BigId, sa.ForeignKey("social_posts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("owner_id", BigId, sa.ForeignKey("social_people.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_social_reposts_person_post", "social_reposts", ["person_id", "post_id"], unique=True)
    op.create_index("ix_social_reposts_person_created", "social_reposts", ["person_id", "created_at"])
    op.create_index("ix_social_reposts_post_id", "social_reposts", ["post_id"])
    op.create_index("ix_social_reposts_owner_created", "social_reposts", ["owner_id", "created_at"])
    with op.batch_alter_table("social_posts") as t:
        t.add_column(sa.Column("is_quote", sa.Boolean(), nullable=False, server_default=sa.false()))
        t.add_column(sa.Column("quoted_post_id", BigId, nullable=True))
        t.add_column(sa.Column("quoted_drawing_id", sa.String(length=32), nullable=True))
        t.add_column(sa.Column("quoted_owner_id", BigId, nullable=True))
        t.alter_column("skribl_id", existing_type=sa.String(length=32), nullable=True)
        t.create_foreign_key("fk_social_posts_quoted_post_id", "social_posts", ["quoted_post_id"], ["id"],
                             ondelete="SET NULL", postgresql_not_valid=True)
        t.create_foreign_key("fk_social_posts_quoted_owner_id", "social_people", ["quoted_owner_id"], ["id"],
                             ondelete="SET NULL", postgresql_not_valid=True)
        t.create_check_constraint("ck_social_posts_drawn_or_quote", DRAWN_OR_QUOTE, postgresql_not_valid=True)
        t.create_check_constraint("ck_social_posts_quotes_one", QUOTES_ONE, postgresql_not_valid=True)
    op.create_index("ix_social_posts_quoted_post_id", "social_posts", ["quoted_post_id"])
    op.create_index("ix_social_posts_quoted_drawing_id", "social_posts", ["quoted_drawing_id"])
    op.create_index("ix_social_posts_quoted_owner_created", "social_posts", ["quoted_owner_id", "created_at"])


def downgrade():
    if not context.is_offline_mode() and op.get_bind().execute(
            sa.text("SELECT 1 FROM social_posts WHERE skribl_id IS NULL LIMIT 1")).first() is not None:
        raise RuntimeError("social_posts holds quotes of words alone (posts with no drawing of their own), and going"
                           " down needs a drawing on every post. Nothing here deletes a post: take those away first,"
                           " or stay at 3e7b508ff939.")
    op.drop_index("ix_social_posts_quoted_owner_created", table_name="social_posts")
    op.drop_index("ix_social_posts_quoted_drawing_id", table_name="social_posts")
    op.drop_index("ix_social_posts_quoted_post_id", table_name="social_posts")
    with op.batch_alter_table("social_posts") as t:
        t.drop_constraint("ck_social_posts_quotes_one", type_="check")
        t.drop_constraint("ck_social_posts_drawn_or_quote", type_="check")
        t.drop_constraint("fk_social_posts_quoted_owner_id", type_="foreignkey")
        t.drop_constraint("fk_social_posts_quoted_post_id", type_="foreignkey")
        t.alter_column("skribl_id", existing_type=sa.String(length=32), nullable=False)
        t.drop_column("quoted_owner_id")
        t.drop_column("quoted_drawing_id")
        t.drop_column("quoted_post_id")
        t.drop_column("is_quote")
    op.drop_index("ix_social_reposts_owner_created", table_name="social_reposts")
    op.drop_index("ix_social_reposts_post_id", table_name="social_reposts")
    op.drop_index("ix_social_reposts_person_created", table_name="social_reposts")
    op.drop_index("ix_social_reposts_person_post", table_name="social_reposts")
    op.drop_table("social_reposts")
