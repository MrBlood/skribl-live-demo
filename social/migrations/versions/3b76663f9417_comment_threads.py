"""The comment thread, step 1: a reply keeps the reply it answers (the owner's
yes, Nov 17, to the Read More Replies mock; docs/SOCIAL-SITE.md section 18).

On the site's own chain (social_alembic_version); nothing of Skribl's is read
or altered. On social_comments:

  answers_id   the comment or the reply this one answers, at any depth;
               nothing for a comment on the post. parent_id stays what it
               was, the top-level comment the whole conversation hangs under,
               so a page still reads a conversation by one index. Goes with
               what it answers (ON DELETE CASCADE, the net under the code's
               own deleting, as parent_id's is).
  ix_social_comments_answers_created   a reply's own replies, oldest first.
  gone         A PLACE (the owner's yes, Nov 17, to "the place stays"): a
               comment or reply deleted while replies hung under it keeps its
               row, quietly, "deleted" or "removed", so they stay where they
               are; nothing for a comment.
  person_id    may be nothing now: a place is nobody's (its words, its
               drawing and whose it was are gone).
  ck_social_comments_someones   somebody's, or a place.

THE REPLIES ALREADY HERE STAY AT THE FIRST LEVEL, AS NOW: each answered
something under its comment, and which reply is not written anywhere (only
whom: to_person_id), so their column stays empty, and the code reads an
empty one as answering its comment (comments.answered). NO DATA WORK IN THE
MIGRATION (v309's lesson): two columns added nullable with no default, a
foreign key, an index, person_id let be nothing, and one CHECK (on
PostgreSQL added NOT VALID: no row read, nothing scanned under the lock);
no row of any table read or written, so a deploy waits on no data.

The downgrade refuses while a place is there, saying so before it changes
anything (one row asked for): person_id is NOT NULL again going down, and a
place is nobody's; nothing here deletes the conversations hanging from one.
Without places it drops what the upgrade added: a reply to a reply goes back
to sitting under its comment, as every answer did, and nothing is deleted.

Revision ID: 3b76663f9417
Revises: 7db36bfedef0
Create Date: 2026-11-17
"""
from alembic import context, op
import sqlalchemy as sa

revision = "3b76663f9417"
down_revision = "7db36bfedef0"
branch_labels = None
depends_on = None

BigId = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


#: Somebody's, or a place (social/models.py says the same).
SOMEONES = "person_id IS NOT NULL OR gone IS NOT NULL"


def upgrade():
    with op.batch_alter_table("social_comments") as t:
        t.add_column(sa.Column("answers_id", BigId, nullable=True))
        t.add_column(sa.Column("gone", sa.String(length=8), nullable=True))
        t.alter_column("person_id", existing_type=BigId, nullable=True)
        t.create_foreign_key("fk_social_comments_answers_id", "social_comments", ["answers_id"], ["id"],
                             ondelete="CASCADE")
        t.create_check_constraint("ck_social_comments_someones", SOMEONES, postgresql_not_valid=True)
    op.create_index("ix_social_comments_answers_created", "social_comments", ["answers_id", "created_at"])


def downgrade():
    if not context.is_offline_mode() and op.get_bind().execute(
            sa.text("SELECT 1 FROM social_comments WHERE gone IS NOT NULL LIMIT 1")).first() is not None:
        raise RuntimeError("social_comments holds places (a comment deleted while replies hung under it, nobody's),"
                           " and going down needs a person on every comment. Nothing here deletes the conversations"
                           " hanging from them: stay at 3b76663f9417.")
    op.drop_index("ix_social_comments_answers_created", table_name="social_comments")
    with op.batch_alter_table("social_comments") as t:
        t.drop_constraint("ck_social_comments_someones", type_="check")
        t.drop_constraint("fk_social_comments_answers_id", type_="foreignkey")
        t.alter_column("person_id", existing_type=BigId, nullable=False)
        t.drop_column("gone")
        t.drop_column("answers_id")
