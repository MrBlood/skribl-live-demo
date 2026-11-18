"""The comment thread, step 1: a reply keeps the reply it answers (the owner's
yes, Nov 17, to the Read More Replies mock; docs/SOCIAL-SITE.md section 18).

On the site's own chain (social_alembic_version); nothing of Skribl's is read
or altered. One column on social_comments, and its index:

  answers_id   the comment or the reply this one answers, at any depth;
               nothing for a comment on the post. parent_id stays what it
               was, the top-level comment the whole conversation hangs under,
               so a page still reads a conversation by one index. Goes with
               what it answers (ON DELETE CASCADE, the net under the code's
               own deleting, as parent_id's is).
  ix_social_comments_answers_created   a reply's own replies, oldest first.

THE REPLIES ALREADY HERE STAY AT THE FIRST LEVEL, AS NOW: each answered
something under its comment, and which reply is not written anywhere (only
whom: to_person_id), so their column stays empty, and the code reads an
empty one as answering its comment (comments.answered). NO DATA WORK IN THE
MIGRATION (v309's lesson): a column added nullable with no default, its
foreign key and its index; no row of any table read or written, so a deploy
waits on no data.

The downgrade drops the index and the column: a reply to a reply goes back to
sitting under its comment, as every answer did, and nothing is deleted.

Revision ID: 3b76663f9417
Revises: 7db36bfedef0
Create Date: 2026-11-17
"""
from alembic import op
import sqlalchemy as sa

revision = "3b76663f9417"
down_revision = "7db36bfedef0"
branch_labels = None
depends_on = None

BigId = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade():
    with op.batch_alter_table("social_comments") as t:
        t.add_column(sa.Column("answers_id", BigId, nullable=True))
        t.create_foreign_key("fk_social_comments_answers_id", "social_comments", ["answers_id"], ["id"],
                             ondelete="CASCADE")
    op.create_index("ix_social_comments_answers_created", "social_comments", ["answers_id", "created_at"])


def downgrade():
    op.drop_index("ix_social_comments_answers_created", table_name="social_comments")
    with op.batch_alter_table("social_comments") as t:
        t.drop_constraint("fk_social_comments_answers_id", type_="foreignkey")
        t.drop_column("answers_id")
