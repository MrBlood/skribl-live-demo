"""Profiles and drawn faces: a bio, and a face, on each person (phase 1, piece 3).

docs/SOCIAL-SITE.md, section 5, build order item 3, the owner's "all yes" on
the phase 1 mocks ("Faces that draw themselves"). Four columns on
social_people, all nullable, so every person already here simply has no bio
and no face yet:

  bio       a few lines about them, plain text (160 characters, 4 lines)
  face_id   the public id of the skribl they drew as their face, posted
            unlisted through Skribl's create_post in the same request
  face_w    its canvas size, which the face player frames its still picture
  face_h    from

No new table and no index: nothing is looked up by a bio or a face (a profile
is found by handle_key, a drawing's author by public_id, both indexed since
d605f778356a). Columns added to the site's own table on the site's own chain
(social_alembic_version): nothing of Skribl's is read or altered. No data work,
so it cannot hold a deploy. The downgrade takes the four away again, through a
batch (SQLite rebuilds the table to drop a column).

Revision ID: fa82723cacc4
Revises: d605f778356a
Create Date: 2026-11-11
"""
from alembic import op
import sqlalchemy as sa

revision = "fa82723cacc4"
down_revision = "d605f778356a"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("social_people") as batch:
        batch.add_column(sa.Column("bio", sa.String(length=160), nullable=True))
        batch.add_column(sa.Column("face_id", sa.String(length=32), nullable=True))
        batch.add_column(sa.Column("face_w", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("face_h", sa.Integer(), nullable=True))


def downgrade():
    with op.batch_alter_table("social_people") as batch:
        batch.drop_column("face_h")
        batch.drop_column("face_w")
        batch.drop_column("face_id")
        batch.drop_column("bio")
