"""The site's first tables: people, their passkeys, invites (phase 1, piece 2).

Sign-in, invite-only, with passkeys (docs/SOCIAL-SITE.md, section 5, build
order item 2, and the owner's "all yes" of Nov 10). Five tables, each named
social_..., each with the indexes its queries use, on 64-bit keys:

  social_people        a person: public id (what Skribl stores as the author),
                       handle (unique however it is written), name, the
                       WebAuthn user handle, admin, the sign-in generation,
                       when they said they are 13 or older
  social_passkeys      a person's passkeys: credential id, public key, sign
                       count, transports, the address it was made on, a name
  social_invites       join and recovery links: only the code's SHA-256 kept
  social_challenges    passkey ceremonies in progress, one browser, five
                       minutes, used once
  social_rate_events   the counted tries the site's limits read

New tables only, on the site's own chain (social_alembic_version): nothing of
Skribl's is read or altered. No data work, so it cannot hold a deploy.

Revision ID: d605f778356a
Revises:
Create Date: 2026-11-10
"""
from alembic import op
import sqlalchemy as sa

revision = "d605f778356a"
down_revision = None
branch_labels = None
depends_on = None

BigId = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade():
    op.create_table(
        "social_people",
        sa.Column("id", BigId, primary_key=True),
        sa.Column("public_id", sa.String(length=40), nullable=False),
        sa.Column("handle", sa.String(length=20), nullable=False),
        sa.Column("handle_key", sa.String(length=20), nullable=False),
        sa.Column("display_name", sa.String(length=40), nullable=False),
        sa.Column("user_handle", sa.LargeBinary(length=32), nullable=False),
        sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("session_gen", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("age_confirmed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_social_people_public_id", "social_people", ["public_id"], unique=True)
    op.create_index("ix_social_people_handle_key", "social_people", ["handle_key"], unique=True)
    op.create_index("ix_social_people_user_handle", "social_people", ["user_handle"], unique=True)

    op.create_table(
        "social_passkeys",
        sa.Column("id", BigId, primary_key=True),
        sa.Column("public_id", sa.String(length=24), nullable=False),
        sa.Column("person_id", BigId, sa.ForeignKey("social_people.id", ondelete="CASCADE"), nullable=False),
        sa.Column("credential_id", sa.LargeBinary(length=1024), nullable=False),
        sa.Column("public_key", sa.LargeBinary(), nullable=False),
        sa.Column("sign_count", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("transports", sa.String(length=120), nullable=True),
        sa.Column("rp_id", sa.String(length=253), nullable=False),
        sa.Column("nickname", sa.String(length=40), nullable=False),
        sa.Column("backed_up", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_social_passkeys_credential_id", "social_passkeys", ["credential_id"], unique=True)
    op.create_index("ix_social_passkeys_public_id", "social_passkeys", ["public_id"], unique=True)
    op.create_index("ix_social_passkeys_person_id", "social_passkeys", ["person_id"])

    op.create_table(
        "social_invites",
        sa.Column("id", BigId, primary_key=True),
        sa.Column("public_id", sa.String(length=24), nullable=False),
        sa.Column("code_hash", sa.String(length=64), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("for_person_id", BigId, sa.ForeignKey("social_people.id", ondelete="CASCADE"), nullable=True),
        sa.Column("created_by_id", BigId, sa.ForeignKey("social_people.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("used_by_id", BigId, sa.ForeignKey("social_people.id", ondelete="SET NULL"), nullable=True),
        sa.CheckConstraint("kind IN ('join', 'recover')", name="ck_social_invites_kind"),
    )
    op.create_index("ix_social_invites_code_hash", "social_invites", ["code_hash"], unique=True)
    op.create_index("ix_social_invites_public_id", "social_invites", ["public_id"], unique=True)
    op.create_index("ix_social_invites_expires_at", "social_invites", ["expires_at"])
    op.create_index("ix_social_invites_for_person_id", "social_invites", ["for_person_id"])
    op.create_index("ix_social_invites_created_by_id", "social_invites", ["created_by_id"])
    op.create_index("ix_social_invites_used_by_id", "social_invites", ["used_by_id"])

    op.create_table(
        "social_challenges",
        sa.Column("id", BigId, primary_key=True),
        sa.Column("sid_hash", sa.String(length=64), nullable=False),
        sa.Column("purpose", sa.String(length=16), nullable=False),
        sa.Column("challenge", sa.LargeBinary(length=64), nullable=False),
        sa.Column("person_id", BigId, sa.ForeignKey("social_people.id", ondelete="CASCADE"), nullable=True),
        sa.Column("invite_id", BigId, sa.ForeignKey("social_invites.id", ondelete="CASCADE"), nullable=True),
        sa.Column("data", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_social_challenges_sid_purpose", "social_challenges", ["sid_hash", "purpose"], unique=True)
    op.create_index("ix_social_challenges_expires_at", "social_challenges", ["expires_at"])

    op.create_table(
        "social_rate_events",
        sa.Column("id", BigId, primary_key=True),
        sa.Column("bucket", sa.String(length=24), nullable=False),
        sa.Column("key_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_social_rate_bucket_key_time", "social_rate_events", ["bucket", "key_hash", "created_at"])
    op.create_index("ix_social_rate_created_at", "social_rate_events", ["created_at"])


def downgrade():
    op.drop_index("ix_social_rate_created_at", table_name="social_rate_events")
    op.drop_index("ix_social_rate_bucket_key_time", table_name="social_rate_events")
    op.drop_table("social_rate_events")
    op.drop_index("ix_social_challenges_expires_at", table_name="social_challenges")
    op.drop_index("ix_social_challenges_sid_purpose", table_name="social_challenges")
    op.drop_table("social_challenges")
    for name in ("ix_social_invites_used_by_id", "ix_social_invites_created_by_id",
                 "ix_social_invites_for_person_id", "ix_social_invites_expires_at",
                 "ix_social_invites_public_id", "ix_social_invites_code_hash"):
        op.drop_index(name, table_name="social_invites")
    op.drop_table("social_invites")
    op.drop_index("ix_social_passkeys_person_id", table_name="social_passkeys")
    op.drop_index("ix_social_passkeys_public_id", table_name="social_passkeys")
    op.drop_index("ix_social_passkeys_credential_id", table_name="social_passkeys")
    op.drop_table("social_passkeys")
    op.drop_index("ix_social_people_user_handle", table_name="social_people")
    op.drop_index("ix_social_people_handle_key", table_name="social_people")
    op.drop_index("ix_social_people_public_id", table_name="social_people")
    op.drop_table("social_people")
