"""Activity: who said something on your posts, and who answered you (the
owner's "all yes" to the notifications mock, Nov 12; docs/SOCIAL-SITE.md,
"Built: notifications").

The list is worked out from the comments themselves; there is no table of
notifications to keep in step with them. On the site's own chain
(social_alembic_version); nothing of Skribl's is read or altered:

  social_people.activity_seen_at   when they last looked at Activity:
                                   what came after it is new, and the
                                   bell has its dot. Nothing until they
                                   first look, so everything is new then.
  social_comments.to_person_id     whom an answer answers: the author of
                                   the comment or answer whose Answer was
                                   pressed (parent_id cannot say it: an
                                   answer to an answer sits under the same
                                   top-level comment). ON DELETE SET NULL,
                                   the net under accounts.delete_person,
                                   which sets it to nothing in code.

Every answer already here is filled from the comment it sits under: until
now an answer kept nothing else, so an answer to an answer is said to answer
the comment it sits under. A comment (no parent) answers nobody.

Indexed as Activity and the bell's dot read them, newest first: by whose it
is (owner_id, created_at), which takes the place of the owner's own index
(owner_id alone: the new one starts with it, so deleting an account and the
cascade still use it), and by whom it answers (to_person_id, created_at).

The downgrade puts the owner's own index back and drops what the upgrade
added.

Revision ID: c276c1445bc1
Revises: ded60afbc86d
Create Date: 2026-11-12
"""
from alembic import op
import sqlalchemy as sa

revision = "c276c1445bc1"
down_revision = "ded60afbc86d"
branch_labels = None
depends_on = None

BigId = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade():
    with op.batch_alter_table("social_people") as t:
        t.add_column(sa.Column("activity_seen_at", sa.DateTime(timezone=True), nullable=True))
    with op.batch_alter_table("social_comments") as t:
        t.add_column(sa.Column("to_person_id", BigId, nullable=True))
        t.create_foreign_key("fk_social_comments_to_person_id", "social_people", ["to_person_id"], ["id"],
                             ondelete="SET NULL")
    comments = sa.table("social_comments", sa.column("id", BigId), sa.column("parent_id", BigId),
                        sa.column("person_id", BigId), sa.column("to_person_id", BigId))
    par = comments.alias("par")
    op.execute(comments.update().where(comments.c.parent_id.isnot(None)).values(
        to_person_id=sa.select(par.c.person_id).where(par.c.id == comments.c.parent_id).scalar_subquery()))
    op.drop_index("ix_social_comments_owner_id", table_name="social_comments")
    op.create_index("ix_social_comments_owner_created", "social_comments", ["owner_id", "created_at"])
    op.create_index("ix_social_comments_to_created", "social_comments", ["to_person_id", "created_at"])


def downgrade():
    op.drop_index("ix_social_comments_to_created", table_name="social_comments")
    op.drop_index("ix_social_comments_owner_created", table_name="social_comments")
    op.create_index("ix_social_comments_owner_id", "social_comments", ["owner_id"])
    with op.batch_alter_table("social_comments") as t:
        t.drop_constraint("fk_social_comments_to_person_id", type_="foreignkey")
        t.drop_column("to_person_id")
    with op.batch_alter_table("social_people") as t:
        t.drop_column("activity_seen_at")
