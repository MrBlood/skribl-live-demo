"""Posts of words alone (the owner's "I like your pick", Nov 16, to A on the
words-only mock: "a person should be allowed to post without a drawing or
flip"; docs/SOCIAL-SITE.md section 17).

On the site's own chain (social_alembic_version); nothing of Skribl's is read
or altered. One CHECK on social_posts, made wider:

  ck_social_posts_drawn_or_quote        goes: a drawing, or a quote
  ck_social_posts_drawn_quoted_or_said  comes: a drawing, a quote, or words
                                        (a post of words alone)

THE CONSTRAINT ONLY: no row is read or written on the way up. Every row there
holds the old rule, so it holds the wider new one; PostgreSQL adds it NOT
VALID (it holds for every row written from now on, and no scan waits under
the table's lock); SQLite batch mode rebuilds social_posts in place with it,
its rows copied as they are.

The downgrade puts the old rule back, so it refuses while a post of words
alone is there, saying so before it changes anything (one row asked for):
those are posts people made, and nothing here deletes them. (SQLite runs no
DDL in a transaction, so a refusal part-way would leave the table half
changed; asking first leaves it whole.)

Revision ID: 7db36bfedef0
Revises: e8f5594cb16f
Create Date: 2026-11-16
"""
from alembic import context, op
import sqlalchemy as sa

revision = "7db36bfedef0"
down_revision = "e8f5594cb16f"
branch_labels = None
depends_on = None

#: social/models.py says the same.
DRAWN_OR_QUOTE = "skribl_id IS NOT NULL OR is_quote"
DRAWN_QUOTED_OR_SAID = "skribl_id IS NOT NULL OR is_quote OR words <> ''"


def upgrade():
    with op.batch_alter_table("social_posts") as t:
        t.drop_constraint("ck_social_posts_drawn_or_quote", type_="check")
        t.create_check_constraint("ck_social_posts_drawn_quoted_or_said", DRAWN_QUOTED_OR_SAID,
                                  postgresql_not_valid=True)


def downgrade():
    if not context.is_offline_mode() and op.get_bind().execute(
            sa.text("SELECT 1 FROM social_posts WHERE skribl_id IS NULL AND NOT is_quote LIMIT 1")).first() is not None:
        raise RuntimeError("social_posts holds posts of words alone (no drawing and no quote), and going down needs a"
                           " drawing or a quote on every post. Nothing here deletes a post: take those away first,"
                           " or stay at 7db36bfedef0.")
    with op.batch_alter_table("social_posts") as t:
        t.drop_constraint("ck_social_posts_drawn_quoted_or_said", type_="check")
        t.create_check_constraint("ck_social_posts_drawn_or_quote", DRAWN_OR_QUOTE, postgresql_not_valid=True)
