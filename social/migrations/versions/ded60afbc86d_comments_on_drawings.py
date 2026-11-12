"""Comments on every drawing (the owner's yes, Nov 12: "Comments on every
drawing, however it was made, so whatever you open has the comment box").

docs/SOCIAL-SITE.md, section 10. A comment belonged to a post; now it belongs
to a post, or to a drawing shown outside a post (/social/b/<skribl_id>: a
skribl the site has no row of its own for). On social_comments, on the site's
own chain (social_alembic_version); nothing of Skribl's is read or altered:

  post_id      the post it is on: nullable now, nothing for one on a drawing
  drawing_id   the drawing it is on, by its skribl's public id (Skribl's), or
               nothing for one on a post (new)
  owner_id     whose the post or the drawing is (new): deleting their account
               takes every comment on what they owned (accounts.delete_person,
               in code; ON DELETE CASCADE is the net under it), and a block
               either way with them is read from the row, never asked of
               Skribl. Filled for every comment already here from its post's
               author, then NOT NULL.
  ck_social_comments_on_one   exactly one of post_id and drawing_id.

Indexed as the pages read it: a drawing's comments newest first (drawing_id,
created_at), and by owner (deleting an account, and the cascade). A comment
whose post is not there could not be shown or filled in; none can exist (the
foreign key's cascade, and posts.drop_post before it), and one that somehow
did is deleted rather than stop the chain at NOT NULL.

The downgrade deletes the comments on drawings (there is no post for them to
be on; their drawing answers stay in Skribl, unlisted, as nothing on this
chain may touch Skribl's tables), then drops what the upgrade added, and
post_id is NOT NULL again.

Revision ID: ded60afbc86d
Revises: b7d4e2f9a618
Create Date: 2026-11-12
"""
from alembic import op
import sqlalchemy as sa

revision = "ded60afbc86d"
down_revision = "b7d4e2f9a618"
branch_labels = None
depends_on = None

BigId = sa.BigInteger().with_variant(sa.Integer(), "sqlite")

#: On a post or on a drawing: exactly one (social/models.py says the same).
ON_ONE = "(post_id IS NOT NULL AND drawing_id IS NULL) OR (post_id IS NULL AND drawing_id IS NOT NULL)"


def upgrade():
    with op.batch_alter_table("social_comments") as t:
        t.add_column(sa.Column("drawing_id", sa.String(length=32), nullable=True))
        t.add_column(sa.Column("owner_id", BigId, nullable=True))
    comments = sa.table("social_comments", sa.column("post_id", BigId), sa.column("owner_id", BigId))
    posts = sa.table("social_posts", sa.column("id", BigId), sa.column("person_id", BigId))
    op.execute(comments.delete().where(~sa.exists().where(posts.c.id == comments.c.post_id)))
    op.execute(comments.update().values(
        owner_id=sa.select(posts.c.person_id).where(posts.c.id == comments.c.post_id).scalar_subquery()))
    with op.batch_alter_table("social_comments") as t:
        t.alter_column("post_id", existing_type=BigId, nullable=True)
        t.alter_column("owner_id", existing_type=BigId, nullable=False)
        t.create_foreign_key("fk_social_comments_owner_id", "social_people", ["owner_id"], ["id"],
                             ondelete="CASCADE")
        t.create_check_constraint("ck_social_comments_on_one", ON_ONE)
    op.create_index("ix_social_comments_drawing_created", "social_comments", ["drawing_id", "created_at"])
    op.create_index("ix_social_comments_owner_id", "social_comments", ["owner_id"])


def downgrade():
    comments = sa.table("social_comments", sa.column("drawing_id", sa.String(length=32)))
    op.execute(comments.delete().where(comments.c.drawing_id.isnot(None)))
    op.drop_index("ix_social_comments_owner_id", table_name="social_comments")
    op.drop_index("ix_social_comments_drawing_created", table_name="social_comments")
    with op.batch_alter_table("social_comments") as t:
        t.drop_constraint("ck_social_comments_on_one", type_="check")
        t.drop_constraint("fk_social_comments_owner_id", type_="foreignkey")
        t.drop_column("owner_id")
        t.drop_column("drawing_id")
        t.alter_column("post_id", existing_type=BigId, nullable=False)
