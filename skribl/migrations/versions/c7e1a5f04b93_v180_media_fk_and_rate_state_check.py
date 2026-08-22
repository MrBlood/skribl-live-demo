"""v180: put the stable invariants in the schema.

Authorisation for /media/<key> is decided by the skribl_post_media association
table, and the package explicitly expects a host application to touch the same
database and possibly construct models itself. Application validation is
therefore not the only thing that can write these rows, and an invariant that
matters to authorisation should not live only in Python.

WHAT THIS ADDS

  * a FOREIGN KEY from skribl_post_media.post_id to skribl_posts.id, ON DELETE
    CASCADE. An association whose post no longer exists cannot authorise
    anything, and leaving such rows behind means the orphan sweep sees their
    media as still referenced — the leak the sweep exists to close. Cascade is
    the semantics deletion will want when it arrives: the post goes, its
    associations go, and storage.sweep_orphans() then reclaims the bytes.

  * a CHECK on skribl_rate_events.state, which is 'pending' or 'committed' and
    nothing else. A third value would count as neither and quietly stop
    consuming a quota slot.

WHAT THIS DELIBERATELY DOES NOT ADD

  A CHECK on skribl_posts.visibility. VISIBILITIES is enforced by the API
  rather than the database SPECIFICALLY so a host can add its own states
  without a Skribl migration, and v180 made SkriblPost.visible_to() fail closed
  on states it does not recognise, with skribl.set_visibility_policy() as the
  way to open them. A CHECK constraint would take that extensibility away again
  — the host could no longer store 'draft' at all — and would do it at the
  layer that is hardest to change. The reviewer offered CHECK *or* an
  extensible policy; the policy was chosen, so the CHECK must not follow.

ORPHAN ROWS FIRST

  The FK cannot be created while a row violates it, and this database has never
  had a delete path, so in practice there are none. "In practice" is not a
  migration strategy: the offending rows are removed first, and they are rows
  that already authorise nothing.

BATCH MODE

  SQLite cannot ALTER TABLE ADD CONSTRAINT, so batch_alter_table recreates the
  table. On PostgreSQL the same call is a plain ALTER. The live database is
  PostgreSQL; the harness runs SQLite; both paths are exercised.
"""
import sqlalchemy as sa
from alembic import op

revision = "c7e1a5f04b93"
down_revision = "f0a3d81b47e2"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()

    # Rows whose post is gone authorise nothing and would block the constraint.
    op.execute(sa.text(
        "DELETE FROM skribl_post_media WHERE post_id NOT IN "
        "(SELECT id FROM skribl_posts)"
    ))

    with op.batch_alter_table("skribl_post_media") as batch:
        batch.create_foreign_key(
            "fk_post_media_post", "skribl_posts",
            ["post_id"], ["id"], ondelete="CASCADE",
        )

    # A state outside this pair counts as neither pending nor committed, so it
    # holds no quota slot and is never cleaned up as one.
    op.execute(sa.text(
        "UPDATE skribl_rate_events SET state = 'committed' "
        "WHERE state NOT IN ('pending', 'committed')"
    ))
    with op.batch_alter_table("skribl_rate_events") as batch:
        batch.create_check_constraint(
            "ck_rate_state", "state IN ('pending', 'committed')"
        )

    del bind


def downgrade():
    with op.batch_alter_table("skribl_rate_events") as batch:
        batch.drop_constraint("ck_rate_state", type_="check")
    with op.batch_alter_table("skribl_post_media") as batch:
        batch.drop_constraint("fk_post_media_post", type_="foreignkey")
