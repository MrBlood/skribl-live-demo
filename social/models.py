"""The site's own tables (docs/SOCIAL-SITE.md, phase 1, piece 2: sign-in).

THEIR OWN BASE AND THEIR OWN CHAIN. Every table here is named social_... and
sits on SocialBase, which the site owns, never on Skribl's base or a host's:
social/migrations is the chain that builds them, with a version table of its
own (social_alembic_version), so Skribl's chain and Skribl's tables are never
touched by it. A host that builds its schema with create_all() (the demo's
`flask init-db`, the harness) attaches these to its metadata with
attach_to_metadata(), as it does Skribl's.

THE SCALE RULES (docs/SOCIAL-SITE.md, section 3), as they apply here:

  * 64-bit ids from the first table, and none of them ever leaves the server:
    a person, a passkey and an invite each have a random public id for
    addresses and forms, so nothing tells the world how many there are.
  * A person's public id is what Skribl stores as the author of a drawing
    (its user_id), stable for ever: "site:" and 26 random letters and
    digits. The prefix keeps it from ever being equal to the demo's own
    identity (app.py refuses a demo identity that starts with it).
  * Every table is written with the indexes its queries use, named here so
    the migration and the models agree (verify_socialauth reads the drift).
  * Times are UTC. SQLite hands them back without a zone; as_utc() says
    what they are.
  * Deleting is real: a person goes with their passkeys and invites
    (accounts.delete_person), not with a flag.
  * An invite code is never stored, only its SHA-256: the link is shown once,
    to the person who made it.
"""
import base64
import secrets
from datetime import datetime, timezone

import sqlalchemy as sa
from sqlalchemy.orm import DeclarativeBase

__all__ = ["SocialBase", "Person", "Passkey", "Invite", "Challenge", "RateEvent",
           "PERSON_PREFIX", "new_person_id", "new_public_id", "as_utc", "utcnow",
           "attach_to_metadata"]

#: What every person's public id starts with. A demo identity never does.
PERSON_PREFIX = "site:"

#: A 64-bit integer key that SQLite will still number by itself: SQLite only
#: fills in an INTEGER PRIMARY KEY, so there it is INTEGER (64 bits wide on
#: SQLite anyway), and BIGINT everywhere else.
BigId = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


class SocialBase(DeclarativeBase):
    """The site's declarative base. Its metadata holds the site's tables and
    nothing else, which is what social/migrations/env.py migrates."""


def utcnow():
    return datetime.now(timezone.utc)


def as_utc(when):
    """A stored time, as UTC. SQLite keeps no zone, so a naive one is UTC."""
    if when is None:
        return None
    return when.replace(tzinfo=timezone.utc) if when.tzinfo is None else when.astimezone(timezone.utc)


def new_public_id(nbytes=12):
    """A random id for an address or a form: url-safe, no padding."""
    return base64.urlsafe_b64encode(secrets.token_bytes(nbytes)).rstrip(b"=").decode()


def new_person_id():
    """site: and 26 lowercase letters and digits (128 random bits, base32)."""
    return PERSON_PREFIX + base64.b32encode(secrets.token_bytes(16)).rstrip(b"=").decode().lower()


class Person(SocialBase):
    """Somebody with an account. Their handle is unique however it is
    written (handle_key is its lowercase), their public id is what Skribl
    knows them by, and session_gen is the number every sign-in cookie carries:
    signing out everywhere adds one, and every cookie with the old number is
    then nobody's."""
    __tablename__ = "social_people"

    id = sa.Column(BigId, primary_key=True)
    public_id = sa.Column(sa.String(40), nullable=False)
    handle = sa.Column(sa.String(20), nullable=False)
    handle_key = sa.Column(sa.String(20), nullable=False)
    display_name = sa.Column(sa.String(40), nullable=False)
    #: The WebAuthn user handle: random bytes the person's passkeys carry, so
    #: a passkey names its account without naming the person.
    user_handle = sa.Column(sa.LargeBinary(32), nullable=False)
    is_admin = sa.Column(sa.Boolean(), nullable=False, default=False, server_default=sa.false())
    session_gen = sa.Column(sa.Integer(), nullable=False, default=1, server_default="1")
    #: When they ticked "I'm 13 or older" (the site's minimum age, section 8).
    age_confirmed_at = sa.Column(sa.DateTime(timezone=True), nullable=False)
    created_at = sa.Column(sa.DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        sa.Index("ix_social_people_public_id", "public_id", unique=True),
        sa.Index("ix_social_people_handle_key", "handle_key", unique=True),
        sa.Index("ix_social_people_user_handle", "user_handle", unique=True),
    )


class Passkey(SocialBase):
    """One passkey of one person. The credential id and public key are the
    authenticator's; sign_count is checked to rise on every sign-in where the
    authenticator keeps one; rp_id is the address it was made on (a passkey
    belongs to one address, so after a move to a domain it is made again)."""
    __tablename__ = "social_passkeys"

    id = sa.Column(BigId, primary_key=True)
    public_id = sa.Column(sa.String(24), nullable=False)
    person_id = sa.Column(BigId, sa.ForeignKey("social_people.id", ondelete="CASCADE"), nullable=False)
    credential_id = sa.Column(sa.LargeBinary(1024), nullable=False)
    public_key = sa.Column(sa.LargeBinary(), nullable=False)
    sign_count = sa.Column(sa.BigInteger(), nullable=False, default=0, server_default="0")
    transports = sa.Column(sa.String(120), nullable=True)
    rp_id = sa.Column(sa.String(253), nullable=False)
    nickname = sa.Column(sa.String(40), nullable=False)
    backed_up = sa.Column(sa.Boolean(), nullable=False, default=False, server_default=sa.false())
    created_at = sa.Column(sa.DateTime(timezone=True), nullable=False, default=utcnow)
    last_used_at = sa.Column(sa.DateTime(timezone=True), nullable=True)

    __table_args__ = (
        sa.Index("ix_social_passkeys_credential_id", "credential_id", unique=True),
        sa.Index("ix_social_passkeys_public_id", "public_id", unique=True),
        sa.Index("ix_social_passkeys_person_id", "person_id"),
    )


class Invite(SocialBase):
    """A link that lets somebody in. 'join' makes an account (14 days);
    'recover' adds a passkey to for_person's account (an hour), the stand-in
    for an emailed sign-in link until there is email. Single use: used_at and
    used_by are set by an UPDATE that only succeeds while used_at is empty, so
    two people cannot both spend one. Only the code's SHA-256 is kept."""
    __tablename__ = "social_invites"

    id = sa.Column(BigId, primary_key=True)
    public_id = sa.Column(sa.String(24), nullable=False)
    code_hash = sa.Column(sa.String(64), nullable=False)
    kind = sa.Column(sa.String(16), nullable=False)
    for_person_id = sa.Column(BigId, sa.ForeignKey("social_people.id", ondelete="CASCADE"), nullable=True)
    created_by_id = sa.Column(BigId, sa.ForeignKey("social_people.id", ondelete="SET NULL"), nullable=True)
    created_at = sa.Column(sa.DateTime(timezone=True), nullable=False, default=utcnow)
    expires_at = sa.Column(sa.DateTime(timezone=True), nullable=False)
    used_at = sa.Column(sa.DateTime(timezone=True), nullable=True)
    used_by_id = sa.Column(BigId, sa.ForeignKey("social_people.id", ondelete="SET NULL"), nullable=True)

    __table_args__ = (
        sa.CheckConstraint("kind IN ('join', 'recover')", name="ck_social_invites_kind"),
        sa.Index("ix_social_invites_code_hash", "code_hash", unique=True),
        sa.Index("ix_social_invites_public_id", "public_id", unique=True),
        sa.Index("ix_social_invites_expires_at", "expires_at"),
        sa.Index("ix_social_invites_for_person_id", "for_person_id"),
        sa.Index("ix_social_invites_created_by_id", "created_by_id"),
        sa.Index("ix_social_invites_used_by_id", "used_by_id"),
    )


class Challenge(SocialBase):
    """A passkey ceremony in progress: the challenge the browser must sign,
    for one browser (sid_hash: the hash of its session id, so a challenge
    asked for in one browser cannot be answered from another), one purpose,
    for five minutes, and used once. `data` holds what the ceremony was asked
    with (a joining person's chosen handle and name, say)."""
    __tablename__ = "social_challenges"

    id = sa.Column(BigId, primary_key=True)
    sid_hash = sa.Column(sa.String(64), nullable=False)
    purpose = sa.Column(sa.String(16), nullable=False)
    challenge = sa.Column(sa.LargeBinary(64), nullable=False)
    person_id = sa.Column(BigId, sa.ForeignKey("social_people.id", ondelete="CASCADE"), nullable=True)
    invite_id = sa.Column(BigId, sa.ForeignKey("social_invites.id", ondelete="CASCADE"), nullable=True)
    data = sa.Column(sa.Text(), nullable=True)
    created_at = sa.Column(sa.DateTime(timezone=True), nullable=False, default=utcnow)
    expires_at = sa.Column(sa.DateTime(timezone=True), nullable=False)

    __table_args__ = (
        sa.Index("ix_social_challenges_sid_purpose", "sid_hash", "purpose", unique=True),
        sa.Index("ix_social_challenges_expires_at", "expires_at"),
    )


class RateEvent(SocialBase):
    """One counted try, for the site's limits (limits.py). The key is a keyed
    hash of who tried (an address, an invite, a person), never the thing."""
    __tablename__ = "social_rate_events"

    id = sa.Column(BigId, primary_key=True)
    bucket = sa.Column(sa.String(24), nullable=False)
    key_hash = sa.Column(sa.String(64), nullable=False)
    created_at = sa.Column(sa.DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        sa.Index("ix_social_rate_bucket_key_time", "bucket", "key_hash", "created_at"),
        sa.Index("ix_social_rate_created_at", "created_at"),
    )


def attach_to_metadata(metadata):
    """Put the site's tables on a host's metadata, so its create_all() makes
    them too (the demo's `flask init-db` and the harness's fresh databases).
    A host that migrates runs social/migrations instead; not both."""
    for table in SocialBase.metadata.tables.values():
        if table.name not in metadata.tables:
            table.to_metadata(metadata)
