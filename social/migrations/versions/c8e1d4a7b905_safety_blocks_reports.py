"""Safety: blocks and reports (phase 1, piece 5).

docs/SOCIAL-SITE.md, section 5, build order item 5, from the owner's "all
yes" on the Safety mock (Nov 12). Two new tables on the site's own chain
(social_alembic_version); nothing of Skribl's is read or altered:

  social_blocks    blocker_id  who blocked; goes with them (ON DELETE CASCADE)
                   blocked_id  who they blocked; goes with them too
                   created_at  when

  social_reports   public_id   the report's own address, for the admins' page
                   kind        person, post, drawing or comment
                   target      the reported thing's public id
                   about_id    whose it is; a report outlives the account it
                               is about (ON DELETE SET NULL), as a record
                   reason      from a closed set (social/safety.py REASONS)
                   note        what the reporter wrote, if anything (300)
                   reporter_id who reported it, for the admins' eyes only
                               (ON DELETE SET NULL)
                   reporter_key a keyed hash of the reporter (a person, or an
                               address for somebody signed out): one reporter,
                               one row for one thing
                   state       open, kept or taken_down
                   created_at, handled_at, handled_by_id

Indexed as they are read: a block by its pair (unique) and by who was
blocked; a report by address (unique), once per reporter per thing
(unique), the queue by state and time, and each person it names. New
tables, so no data work and nothing to hold a deploy; the downgrade drops
them.

Revision ID: c8e1d4a7b905
Revises: b3c41e7d9a20
Create Date: 2026-11-12
"""
from alembic import op
import sqlalchemy as sa

revision = "c8e1d4a7b905"
down_revision = "b3c41e7d9a20"
branch_labels = None
depends_on = None

BigId = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade():
    op.create_table(
        "social_blocks",
        sa.Column("id", BigId, primary_key=True),
        sa.Column("blocker_id", BigId, sa.ForeignKey("social_people.id", ondelete="CASCADE"), nullable=False),
        sa.Column("blocked_id", BigId, sa.ForeignKey("social_people.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_social_blocks_pair", "social_blocks", ["blocker_id", "blocked_id"], unique=True)
    op.create_index("ix_social_blocks_blocked_id", "social_blocks", ["blocked_id"])

    op.create_table(
        "social_reports",
        sa.Column("id", BigId, primary_key=True),
        sa.Column("public_id", sa.String(length=24), nullable=False),
        sa.Column("kind", sa.String(length=12), nullable=False),
        sa.Column("target", sa.String(length=40), nullable=False),
        sa.Column("about_id", BigId, sa.ForeignKey("social_people.id", ondelete="SET NULL"), nullable=True),
        sa.Column("reason", sa.String(length=16), nullable=False),
        sa.Column("note", sa.String(length=300), nullable=True),
        sa.Column("reporter_id", BigId, sa.ForeignKey("social_people.id", ondelete="SET NULL"), nullable=True),
        sa.Column("reporter_key", sa.String(length=64), nullable=False),
        sa.Column("state", sa.String(length=12), nullable=False, server_default="open"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("handled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("handled_by_id", BigId, sa.ForeignKey("social_people.id", ondelete="SET NULL"), nullable=True),
        sa.CheckConstraint("kind IN ('person', 'post', 'drawing', 'comment')", name="ck_social_reports_kind"),
        sa.CheckConstraint("state IN ('open', 'kept', 'taken_down')", name="ck_social_reports_state"),
    )
    op.create_index("ix_social_reports_public_id", "social_reports", ["public_id"], unique=True)
    op.create_index("ix_social_reports_once", "social_reports", ["kind", "target", "reporter_key"], unique=True)
    op.create_index("ix_social_reports_state_created", "social_reports", ["state", "created_at"])
    op.create_index("ix_social_reports_about_id", "social_reports", ["about_id"])
    op.create_index("ix_social_reports_reporter_id", "social_reports", ["reporter_id"])
    op.create_index("ix_social_reports_handled_by_id", "social_reports", ["handled_by_id"])


def downgrade():
    for name in ("ix_social_reports_handled_by_id", "ix_social_reports_reporter_id", "ix_social_reports_about_id",
                 "ix_social_reports_state_created", "ix_social_reports_once", "ix_social_reports_public_id"):
        op.drop_index(name, table_name="social_reports")
    op.drop_table("social_reports")
    op.drop_index("ix_social_blocks_blocked_id", table_name="social_blocks")
    op.drop_index("ix_social_blocks_pair", table_name="social_blocks")
    op.drop_table("social_blocks")
