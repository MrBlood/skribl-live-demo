"""Finding people: the Gallery's search box finds people too, by any word of
their name or the start of their @handle (the map, part two, item 5; the
owner's "All yes" on the finding-people mock, Nov 15; docs/SOCIAL-SITE.md
section 17).

On the site's own chain (social_alembic_version); nothing of Skribl's is read
or altered. One table and its two indexes:

  social_people_words      a way somebody is found (social/people.py):
    person_id              whose
    word_key               their name from one of its words on ("theo
                           park", "park") or their @handle, folded: small
                           letters, accents put aside, anything that is not a
                           letter or a digit one space; in the "C" collation
                           on PostgreSQL, so a search's range is byte order
                           there as on SQLite (social/models.py, WordKey)
  ix_social_people_words_key      every key in order, then whose: a search
                           reads the keys that start with what was typed
  ix_social_people_words_person   a person's own, once each: written again
                           with their name, read through your follows

THE TABLE AND ITS INDEXES ONLY: no row of any table is read or written, so
nothing here waits on the data a deploy finds (the house lesson, v309). The
people already on the site are given their words IN CODE, never here: the
site's `flask social words` (social/people.py, fill), which gunicorn.conf.py
runs once each start, right after this chain, and which anybody may run by
hand; batched, committed as it goes, and asking only after the people who
have none, so it can stop and start again.

The downgrade drops what the upgrade added.

Revision ID: e8f5594cb16f
Revises: 6dc6c4054756
Create Date: 2026-11-15
"""
from alembic import op
import sqlalchemy as sa

revision = "e8f5594cb16f"
down_revision = "6dc6c4054756"
branch_labels = None
depends_on = None

BigId = sa.BigInteger().with_variant(sa.Integer(), "sqlite")

#: social/models.py's WordKey, spelled here so the chain never imports the
#: models it builds.
WordKey = sa.String(length=64).with_variant(sa.String(length=64, collation="C"), "postgresql")


def upgrade():
    op.create_table(
        "social_people_words",
        sa.Column("id", BigId, primary_key=True),
        sa.Column("person_id", BigId, sa.ForeignKey("social_people.id", ondelete="CASCADE"), nullable=False),
        sa.Column("word_key", WordKey, nullable=False),
    )
    op.create_index("ix_social_people_words_key", "social_people_words", ["word_key", "person_id"])
    op.create_index("ix_social_people_words_person", "social_people_words", ["person_id", "word_key"], unique=True)


def downgrade():
    op.drop_index("ix_social_people_words_person", table_name="social_people_words")
    op.drop_index("ix_social_people_words_key", table_name="social_people_words")
    op.drop_table("social_people_words")
