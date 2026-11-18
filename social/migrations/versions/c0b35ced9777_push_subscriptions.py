"""Push notifications: a device that may be nudged (the owner's "All yes" to
Blooby's Nudges, Nov 18; docs/SOCIAL-SITE.md, "Built: push notifications").

On the site's own chain (social_alembic_version); nothing of Skribl's is read
or altered.

  social_push_subscriptions
    person_id      whose device it is. Goes with them (ON DELETE CASCADE,
                   the net under push.drop_person_pushes).
    endpoint       the push service's address for the device: once in the
                   table (ix_social_push_subscriptions_endpoint, unique).
    p256dh, auth   the keys a nudge is sealed with for that device.
    gen            the person's session_gen when it was made: Sign out
                   everywhere moves that on, and an older device is never
                   nudged.
    browser        a hash of the sign-in that made it: signing out of that
                   browser takes its nudges with it.
    replies, mentions, likes, follows, reposts, badge
                   the device's own switches, starting at the dot's rule
                   (replies, mentions and the number on the icon on).
    created_at
    told_up_to     the time of the newest Activity row a nudge told the
                   device about: a row no newer is never told again.
    ix_social_push_subscriptions_person_id   a person's devices.

NO DATA WORK: a new table, empty.

The downgrade drops the table: the devices forget they were nudged, and turn
nudges on again from Settings or Activity's card.

Revision ID: c0b35ced9777
Revises: 36a8b352b347
Create Date: 2026-11-18
"""
from alembic import op
import sqlalchemy as sa

revision = "c0b35ced9777"
down_revision = "36a8b352b347"
branch_labels = None
depends_on = None

BigId = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade():
    op.create_table(
        "social_push_subscriptions",
        sa.Column("id", BigId, primary_key=True),
        sa.Column("person_id", BigId, sa.ForeignKey("social_people.id", ondelete="CASCADE"), nullable=False),
        sa.Column("endpoint", sa.String(1024), nullable=False),
        sa.Column("p256dh", sa.String(128), nullable=False),
        sa.Column("auth", sa.String(64), nullable=False),
        sa.Column("gen", sa.Integer(), nullable=False),
        sa.Column("browser", sa.String(64), nullable=False),
        sa.Column("replies", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("mentions", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("likes", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("follows", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("reposts", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("badge", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("told_up_to", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_social_push_subscriptions_endpoint", "social_push_subscriptions", ["endpoint"], unique=True)
    op.create_index("ix_social_push_subscriptions_person_id", "social_push_subscriptions", ["person_id"])


def downgrade():
    op.drop_index("ix_social_push_subscriptions_person_id", table_name="social_push_subscriptions")
    op.drop_index("ix_social_push_subscriptions_endpoint", table_name="social_push_subscriptions")
    op.drop_table("social_push_subscriptions")
