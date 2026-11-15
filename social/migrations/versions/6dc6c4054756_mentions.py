"""Mentions: an @handle in a post's or a comment's words links to that person
and tells them (the map, part two, item 4; the owner's "All yes" on the
mentions mock, Nov 15; docs/SOCIAL-SITE.md section 17).

On the site's own chain (social_alembic_version); nothing of Skribl's is read
or altered. One table, shaped as a like is, and one index on social_people:

  social_mentions          somebody named in a post's or a comment's words:
    person_id              who was mentioned
    by_id                  who wrote the words
    post_id                the post whose words they are, or nothing
    comment_id             the comment (or answer) whose words they are, or
                           nothing
    ck_social_mentions_on_one   exactly one of the two
    owner_id               whose the post is, or what the comment is on
    typed                  the handle as it was typed, without the @
    created_at
  ix_social_people_name_key    the people's names in small letters (an index
                           of lower(display_name)), for the list under an @:
                           anybody whose name starts with what was typed

Once a person a post and once a person a comment: unique on (person_id,
post_id) and on (person_id, comment_id), an empty id never colliding with
another. Indexed as the pages read it: theirs, newest first (Activity's
"mentioned you", and the bell's dot); a post's and a comment's (the links in
their words, one read a page, and their going); who wrote them and whose
(deleting an account). Every foreign key cascades, the net under deleting in
code (mentions.py).

THE TABLE AND THE INDEXES ONLY: no row of any table is read or written, so
nothing here waits on the data a deploy finds (the house lesson, v309). The
table is new and empty, so its CHECK and its keys hold from the first row
with nothing to scan; the one index on an old table is built from its own
narrow column, as the reposts' were. Posts written before it keep their
words as they were, plain: nothing works mentions out of old words.

The downgrade drops what the upgrade added.

Revision ID: 6dc6c4054756
Revises: 3e7b508ff939
Create Date: 2026-11-15
"""
from alembic import op
import sqlalchemy as sa

revision = "6dc6c4054756"
down_revision = "3e7b508ff939"
branch_labels = None
depends_on = None

BigId = sa.BigInteger().with_variant(sa.Integer(), "sqlite")

#: In a post or in a comment: exactly one (social/models.py says the same).
ON_ONE = "(post_id IS NOT NULL AND comment_id IS NULL) OR (post_id IS NULL AND comment_id IS NOT NULL)"


def upgrade():
    op.create_table(
        "social_mentions",
        sa.Column("id", BigId, primary_key=True),
        sa.Column("person_id", BigId, sa.ForeignKey("social_people.id", ondelete="CASCADE"), nullable=False),
        sa.Column("by_id", BigId, sa.ForeignKey("social_people.id", ondelete="CASCADE"), nullable=False),
        sa.Column("post_id", BigId, sa.ForeignKey("social_posts.id", ondelete="CASCADE"), nullable=True),
        sa.Column("comment_id", BigId, sa.ForeignKey("social_comments.id", ondelete="CASCADE"), nullable=True),
        sa.Column("owner_id", BigId, sa.ForeignKey("social_people.id", ondelete="CASCADE"), nullable=False),
        sa.Column("typed", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(ON_ONE, name="ck_social_mentions_on_one"),
    )
    op.create_index("ix_social_mentions_person_post", "social_mentions", ["person_id", "post_id"], unique=True)
    op.create_index("ix_social_mentions_person_comment", "social_mentions", ["person_id", "comment_id"], unique=True)
    op.create_index("ix_social_mentions_person_created", "social_mentions", ["person_id", "created_at"])
    op.create_index("ix_social_mentions_post_id", "social_mentions", ["post_id"])
    op.create_index("ix_social_mentions_comment_id", "social_mentions", ["comment_id"])
    op.create_index("ix_social_mentions_by_id", "social_mentions", ["by_id"])
    op.create_index("ix_social_mentions_owner_id", "social_mentions", ["owner_id"])
    op.create_index("ix_social_people_name_key", "social_people", [sa.text("lower(display_name)")])


def downgrade():
    op.drop_index("ix_social_people_name_key", table_name="social_people")
    op.drop_index("ix_social_mentions_owner_id", table_name="social_mentions")
    op.drop_index("ix_social_mentions_by_id", table_name="social_mentions")
    op.drop_index("ix_social_mentions_comment_id", table_name="social_mentions")
    op.drop_index("ix_social_mentions_post_id", table_name="social_mentions")
    op.drop_index("ix_social_mentions_person_created", table_name="social_mentions")
    op.drop_index("ix_social_mentions_person_comment", table_name="social_mentions")
    op.drop_index("ix_social_mentions_person_post", table_name="social_mentions")
    op.drop_table("social_mentions")
