"""Drawn letters (the owner's yes, Nov 26, A for all six; DECISIONS.md,
"Drawn letters, mocked"; social/letters.py).

On the site's own chain (social_alembic_version); nothing of Skribl's is read
or altered.

  social_letters                 one row a letter: who sent it to whom, its
                                 drawing (Skribl's, visibility "letter"), the
                                 letter it was written back on, where this
                                 hand starts, when it was opened, deleted
                                 from each side, taken down
  social_push_subscriptions
    letters                      a device's switch for a new letter, on by
                                 default (the owner's yes, Nov 26)
  social_reports                 a report may be of a letter: the kind's CHECK
                                 takes 'letter'

NO DATA WORK beyond the new column's default: every device starts with
letters on, as a new one does.

The downgrade drops the table and the column, and puts the CHECK back as it
was, after removing any report of a letter (a row the old CHECK refuses).
Their drawings stay in Skribl, readable by nobody (an unknown state is its
author's alone).

Revision ID: d3a8f1c6e2b4
Revises: b7e3f9a2c5d1
Create Date: 2026-11-26
"""
from alembic import op
import sqlalchemy as sa

revision = "d3a8f1c6e2b4"
down_revision = "b7e3f9a2c5d1"
branch_labels = None
depends_on = None

BigId = sa.BigInteger().with_variant(sa.Integer(), "sqlite")

_KINDS_BEFORE = "kind IN ('person', 'post', 'drawing', 'comment')"
_KINDS_AFTER = "kind IN ('person', 'post', 'drawing', 'comment', 'letter')"


def upgrade():
    op.create_table(
        "social_letters",
        sa.Column("id", BigId, primary_key=True),
        sa.Column("public_id", sa.String(24), nullable=False),
        sa.Column("sender_id", BigId, sa.ForeignKey("social_people.id", ondelete="CASCADE"), nullable=False),
        sa.Column("recipient_id", BigId, sa.ForeignKey("social_people.id", ondelete="CASCADE"), nullable=False),
        sa.Column("skribl_id", sa.String(32), nullable=False),
        sa.Column("written_on_id", BigId, sa.ForeignKey("social_letters.id", ondelete="SET NULL",
                                                        name="fk_social_letters_written_on_id"), nullable=True),
        sa.Column("hand_at_ms", sa.Integer(), nullable=True),
        sa.Column("hands_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sender_deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("recipient_deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("taken_down_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("sender_id <> recipient_id", name="ck_social_letters_not_self"),
    )
    op.create_index("ix_social_letters_public_id", "social_letters", ["public_id"], unique=True)
    op.create_index("ix_social_letters_recipient_created", "social_letters", ["recipient_id", "created_at"])
    op.create_index("ix_social_letters_sender_created", "social_letters", ["sender_id", "created_at"])
    op.create_index("ix_social_letters_skribl_id", "social_letters", ["skribl_id"])
    op.create_index("ix_social_letters_written_on_id", "social_letters", ["written_on_id"])
    with op.batch_alter_table("social_push_subscriptions") as t:
        t.add_column(sa.Column("letters", sa.Boolean(), nullable=False, server_default=sa.true()))
    with op.batch_alter_table("social_reports") as t:
        t.drop_constraint("ck_social_reports_kind", type_="check")
        t.create_check_constraint("ck_social_reports_kind", _KINDS_AFTER)


def downgrade():
    op.execute("DELETE FROM social_reports WHERE kind = 'letter'")
    with op.batch_alter_table("social_reports") as t:
        t.drop_constraint("ck_social_reports_kind", type_="check")
        t.create_check_constraint("ck_social_reports_kind", _KINDS_BEFORE)
    with op.batch_alter_table("social_push_subscriptions") as t:
        t.drop_column("letters")
    op.drop_index("ix_social_letters_written_on_id", table_name="social_letters")
    op.drop_index("ix_social_letters_skribl_id", table_name="social_letters")
    op.drop_index("ix_social_letters_sender_created", table_name="social_letters")
    op.drop_index("ix_social_letters_recipient_created", table_name="social_letters")
    op.drop_index("ix_social_letters_public_id", table_name="social_letters")
    op.drop_table("social_letters")
