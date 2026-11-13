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

__all__ = ["SocialBase", "Person", "Passkey", "Invite", "Challenge", "RateEvent", "Post",
           "Comment", "Like", "Follow", "Block", "Report", "PERSON_PREFIX", "BIO_MAX", "BIO_LINES",
           "WORDS_MAX", "REPORT_KINDS", "REPORT_STATES", "REPORT_NOTE_MAX", "HOME_FEEDS",
           "new_person_id", "new_public_id", "as_utc", "utcnow", "attach_to_metadata"]

#: What every person's public id starts with. A demo identity never does.
PERSON_PREFIX = "site:"

#: A bio's most characters, and its most lines (accounts.check_bio).
BIO_MAX = 160
BIO_LINES = 4

#: A post's words, at most (posts.check_words): the owner's "all yes" (Nov 11).
WORDS_MAX = 500

#: What a report can be about (safety.py): somebody, a post, a drawing shown
#: outside a post, and a comment (with comments, phase 2's first piece).
REPORT_KINDS = ("person", "post", "drawing", "comment")

#: Where a report stands: waiting, looked at and kept, or taken down.
REPORT_STATES = ("open", "kept", "taken_down")

#: A report's note, at most (Skribl's own report note is 300 too).
REPORT_NOTE_MAX = 300

#: What Home can open on (follows; Home's pill): the people you follow and
#: you, or everyone's posts.
HOME_FEEDS = ("following", "everyone")

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
    #: Which Terms they agreed to by joining (rules.TERMS_VERSION, the line on
    #: Join), and when they pressed Join. None for people who joined before
    #: Join said so (Nov 12): they were never asked.
    terms_version = sa.Column(sa.String(16), nullable=True)
    terms_agreed_at = sa.Column(sa.DateTime(timezone=True), nullable=True)
    created_at = sa.Column(sa.DateTime(timezone=True), nullable=False, default=utcnow)
    #: A few lines about them, plain text (piece 3, profiles): at most
    #: BIO_MAX characters and BIO_LINES lines, no invisible or bidi
    #: characters (accounts.check_bio). None until they write one.
    bio = sa.Column(sa.String(BIO_MAX), nullable=True)
    #: THEIR DRAWN FACE (piece 3): the public id of a skribl they drew in the
    #: Pad's face mode, posted UNLISTED through Skribl's create_post in the
    #: same request as this row's update, and its canvas size (the face
    #: player frames its still picture from it). None until they draw one; a
    #: new one replaces it, and the old skribl is deleted (delete_post).
    face_id = sa.Column(sa.String(32), nullable=True)
    face_w = sa.Column(sa.Integer(), nullable=True)
    face_h = sa.Column(sa.Integer(), nullable=True)
    #: TAKEN DOWN by an admin (piece 5, Your Reports): when. Their profile is
    #: nobody's to everybody else and all they made is hidden; they can still
    #: sign in, see their own with the note, and delete their account. None
    #: until then; nothing is deleted by it.
    taken_down_at = sa.Column(sa.DateTime(timezone=True), nullable=True)
    #: WHEN THEY LAST LOOKED AT ACTIVITY (phase 2, notifications; the owner's
    #: "all yes", Nov 12): what came after it is new, and the bell has its
    #: dot. None until they first look: then everything is new.
    activity_seen_at = sa.Column(sa.DateTime(timezone=True), nullable=True)
    #: WHAT HOME OPENS ON (follows; the owner's "Yes to all", Nov 13): one of
    #: HOME_FEEDS, as they last picked on Home's pill, kept with the account so
    #: it holds on every device. None until they pick: then Following once
    #: they follow somebody, and Everyone before that (follows.home_shows).
    home_feed = sa.Column(sa.String(12), nullable=True)

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


class Post(SocialBase):
    """A post (piece 4): a person's words and a skribl. The skribl is Skribl's,
    posted through create_post in the same request as this row, which keeps
    only its public id; the words are the site's. Deleting a post deletes
    both, in one transaction (Skribl's delete_post); so does deleting the
    account. The feed reads newest first, and a person's own newest first
    ("More from"), each by an index of its own."""
    __tablename__ = "social_posts"

    id = sa.Column(BigId, primary_key=True)
    public_id = sa.Column(sa.String(24), nullable=False)
    person_id = sa.Column(BigId, sa.ForeignKey("social_people.id", ondelete="CASCADE"), nullable=False)
    #: Plain text as typed, tidied (posts.check_words); may be empty.
    words = sa.Column(sa.String(WORDS_MAX), nullable=False, default="", server_default="")
    skribl_id = sa.Column(sa.String(32), nullable=False)
    created_at = sa.Column(sa.DateTime(timezone=True), nullable=False, default=utcnow)
    #: TAKEN DOWN by an admin (piece 5): when. Hidden from everybody but its
    #: author, who sees it with the note; its skribl withheld in Skribl. A
    #: copy is kept: nothing is deleted by it.
    taken_down_at = sa.Column(sa.DateTime(timezone=True), nullable=True)

    __table_args__ = (
        sa.Index("ix_social_posts_public_id", "public_id", unique=True),
        sa.Index("ix_social_posts_created", "created_at", "public_id"),
        sa.Index("ix_social_posts_person_created", "person_id", "created_at"),
        sa.Index("ix_social_posts_skribl_id", "skribl_id"),
    )


class Comment(SocialBase):
    """A comment on a post, or an answer to one (phase 2, comments; the
    owner's "all yes on both", Nov 12): a person's words and, since its
    second part, maybe a drawing. Answers sit ONE level under a comment:
    parent_id is always a top-level comment's id, so answering an answer
    puts the new one under the same comment (comments.py). The post's own
    page reads its comments newest first and each comment's answers oldest
    first, each by an index of its own.

    ON A POST, OR ON A DRAWING (the owner's yes, Nov 12: "Comments on every
    drawing, however it was made"): a comment belongs to a post (post_id),
    or to a drawing shown outside a post (drawing_id, the skribl's own
    public id: Skribl's, so the site has no row of its own for it). Exactly
    one of the two, which the database holds too (ck_social_comments_on_one).
    An answer is on what its comment is on. owner_id is whose that post or
    drawing is, kept on the comment either way, so deleting an account and
    a block never need to ask Skribl whose a drawing was.

    DELETING IS REAL AND SAID IN CODE (comments.py, posts.drop_post,
    posts.bloob_delete, accounts.delete_person): a comment goes with its
    answers, a post or a drawing with its comments, an account with its
    comments, the answers under them and every comment on what it owned.
    The ON DELETE CASCADEs below are the database's net under that, never
    the way: SQLite enforces them only where Skribl's pragma hook is on."""
    __tablename__ = "social_comments"

    id = sa.Column(BigId, primary_key=True)
    public_id = sa.Column(sa.String(24), nullable=False)
    #: The post it is on, or None for one on a drawing shown outside a post.
    post_id = sa.Column(BigId, sa.ForeignKey("social_posts.id", ondelete="CASCADE"), nullable=True)
    #: The drawing it is on (shown outside a post: /social/b/<it>), by its
    #: skribl's public id, or None for one on a post.
    drawing_id = sa.Column(sa.String(32), nullable=True)
    #: Whose the post or the drawing is: deleting their account takes every
    #: comment on what they owned, and a block either way with them closes it.
    owner_id = sa.Column(BigId, sa.ForeignKey("social_people.id", ondelete="CASCADE",
                                              name="fk_social_comments_owner_id"), nullable=False)
    person_id = sa.Column(BigId, sa.ForeignKey("social_people.id", ondelete="CASCADE"), nullable=False)
    #: The top-level comment an answer sits under; None for a comment.
    parent_id = sa.Column(BigId, sa.ForeignKey("social_comments.id", ondelete="CASCADE"), nullable=True)
    #: WHOM AN ANSWER ANSWERS (notifications): the author of the comment or the
    #: answer whose Answer was pressed. parent_id cannot say it: an answer to
    #: an answer sits under the same top-level comment, whoever wrote that.
    #: Activity's "answered your comment" reads it. None for a comment; set to
    #: nothing, in code, when that person's account goes (ON DELETE SET NULL
    #: is the net).
    to_person_id = sa.Column(BigId, sa.ForeignKey("social_people.id", ondelete="SET NULL",
                                                  name="fk_social_comments_to_person_id"), nullable=True)
    #: Plain text as typed, tidied (posts.check_words); may be empty when a
    #: drawing says it.
    words = sa.Column(sa.String(WORDS_MAX), nullable=False, default="", server_default="")
    #: A drawing answer (the second part): a skribl posted UNLISTED through
    #: create_post in the same request as this row, deleted with it
    #: (delete_post). None for words alone.
    skribl_id = sa.Column(sa.String(32), nullable=True)
    created_at = sa.Column(sa.DateTime(timezone=True), nullable=False, default=utcnow)
    #: TAKEN DOWN by an admin (Your Reports): when. Hidden from everybody but
    #: its author, who sees it with the note; nothing is deleted by it.
    taken_down_at = sa.Column(sa.DateTime(timezone=True), nullable=True)

    __table_args__ = (
        #: On a post or on a drawing: exactly one.
        sa.CheckConstraint("(post_id IS NOT NULL AND drawing_id IS NULL) OR (post_id IS NULL AND drawing_id IS NOT NULL)",
                           name="ck_social_comments_on_one"),
        sa.Index("ix_social_comments_public_id", "public_id", unique=True),
        sa.Index("ix_social_comments_post_created", "post_id", "created_at"),
        sa.Index("ix_social_comments_drawing_created", "drawing_id", "created_at"),
        sa.Index("ix_social_comments_parent_created", "parent_id", "created_at"),
        sa.Index("ix_social_comments_person_id", "person_id"),
        #: Whose it is, newest first: Activity's comments on what you own, and
        #: the bell's dot (since you last looked); deleting an account by it.
        sa.Index("ix_social_comments_owner_created", "owner_id", "created_at"),
        #: Answers to you, newest first: Activity's "answered your comment".
        sa.Index("ix_social_comments_to_created", "to_person_id", "created_at"),
        sa.Index("ix_social_comments_skribl_id", "skribl_id"),
    )


class Like(SocialBase):
    """A like (phase 2, likes; the owner's D on the likes mock, Nov 13): one
    person liking a post, or a drawing shown outside a post, once; tapping the
    heart again unlikes, and the row goes. Shaped as a comment is: on a post
    (post_id) or a drawing (drawing_id, the skribl's own public id), exactly
    one (ck_social_likes_on_one), and owner_id is whose that post or drawing
    is, kept on the row so a block, Activity and deleting an account never ask
    Skribl. A person likes a thing once: the two unique indexes (a post's or a
    drawing's id is empty on the other kind, and empties never collide).

    EACH LIKE KEEPS ITS MOMENT: at_ms is where the drawing's replay was when
    the heart was tapped while it played, on the drawing's own clock (the
    in-post player's playhead seam), or nothing when it was not playing; such
    a like counts all the same.

    DELETING IS REAL AND SAID IN CODE (likes.py, from posts.drop_post,
    posts.bloob_delete and accounts.delete_person): a post or a drawing goes
    with its likes, an account with its own and every like on what it owned.
    The ON DELETE CASCADEs are the net under that, as for comments."""
    __tablename__ = "social_likes"

    id = sa.Column(BigId, primary_key=True)
    #: The post it is on, or None for one on a drawing shown outside a post.
    post_id = sa.Column(BigId, sa.ForeignKey("social_posts.id", ondelete="CASCADE"), nullable=True)
    #: The drawing it is on (shown outside a post), by its skribl's public id.
    drawing_id = sa.Column(sa.String(32), nullable=True)
    #: Whose the post or the drawing is (its maker).
    owner_id = sa.Column(BigId, sa.ForeignKey("social_people.id", ondelete="CASCADE"), nullable=False)
    #: Who liked it.
    person_id = sa.Column(BigId, sa.ForeignKey("social_people.id", ondelete="CASCADE"), nullable=False)
    #: Where the drawing was, in ms on its own replay clock, when the heart was
    #: tapped while it played; None when it was not playing.
    at_ms = sa.Column(sa.Integer(), nullable=True)
    created_at = sa.Column(sa.DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        #: On a post or on a drawing: exactly one.
        sa.CheckConstraint("(post_id IS NOT NULL AND drawing_id IS NULL) OR (post_id IS NULL AND drawing_id IS NOT NULL)",
                           name="ck_social_likes_on_one"),
        #: Once a person, once a thing.
        sa.Index("ix_social_likes_person_post", "person_id", "post_id", unique=True),
        sa.Index("ix_social_likes_person_drawing", "person_id", "drawing_id", unique=True),
        #: A thing's likes, newest first: its count, and who liked it.
        sa.Index("ix_social_likes_post_created", "post_id", "created_at"),
        sa.Index("ix_social_likes_drawing_created", "drawing_id", "created_at"),
        #: Whose, newest first: Activity's likes on what you made.
        sa.Index("ix_social_likes_owner_created", "owner_id", "created_at"),
    )


class Follow(SocialBase):
    """One person following another (phase 2, follows; the owner's "Yes to
    all" on the follow mock, B, Nov 13): their new drawings show first on the
    follower's Home. Who follows whom is only ever the person's own to see
    (follows.py).

    ONE ROW A PAIR, FOR AS LONG AS THEY BOTH STAY (unique on the pair), and
    nobody follows themselves (ck_social_follows_not_self). created_at is when
    the follower FIRST followed. Unfollowing sets ended_at and keeps the row,
    so that following again (ended_at back to nothing, created_at kept) never
    tells them twice: Activity reads created_at. Every read of who follows
    whom takes ended_at IS NULL.

    A BLOCK ENDS IT BOTH WAYS, and for good: the rows go (safety.py), so
    lifting the block brings nothing back. Deleting an account takes its rows
    both ways, in code (accounts.delete_person); the ON DELETE CASCADEs are
    the net under that.

    Indexed both ways, newest first: whom a person follows (their Following
    list, and Home's Following, through the pair), and who follows a person
    (their Followers list, their "Followed by…" line, and Activity's "followed
    you", since you last looked and before)."""
    __tablename__ = "social_follows"

    id = sa.Column(BigId, primary_key=True)
    #: Who follows.
    follower_id = sa.Column(BigId, sa.ForeignKey("social_people.id", ondelete="CASCADE"), nullable=False)
    #: Whom.
    followed_id = sa.Column(BigId, sa.ForeignKey("social_people.id", ondelete="CASCADE"), nullable=False)
    #: When they first followed (kept through an unfollow and a follow again).
    created_at = sa.Column(sa.DateTime(timezone=True), nullable=False, default=utcnow)
    #: When they unfollowed; None while they follow.
    ended_at = sa.Column(sa.DateTime(timezone=True), nullable=True)

    __table_args__ = (
        #: Nobody follows themselves.
        sa.CheckConstraint("follower_id <> followed_id", name="ck_social_follows_not_self"),
        #: One row a pair.
        sa.Index("ix_social_follows_pair", "follower_id", "followed_id", unique=True),
        #: Whom a person follows, newest first.
        sa.Index("ix_social_follows_follower_created", "follower_id", "created_at"),
        #: Who follows a person, newest first.
        sa.Index("ix_social_follows_followed_created", "followed_id", "created_at"),
    )


class Block(SocialBase):
    """One person blocking another (Safety, piece 5; the owner's "all yes",
    Nov 12): both ways, and quietly. While a row stands neither sees the
    other's posts, drawings or profile, and the blocked person is never told.
    Only the blocker lifts it (Unblock, in Settings). It goes with either
    account (ON DELETE CASCADE)."""
    __tablename__ = "social_blocks"

    id = sa.Column(BigId, primary_key=True)
    blocker_id = sa.Column(BigId, sa.ForeignKey("social_people.id", ondelete="CASCADE"), nullable=False)
    blocked_id = sa.Column(BigId, sa.ForeignKey("social_people.id", ondelete="CASCADE"), nullable=False)
    created_at = sa.Column(sa.DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        sa.Index("ix_social_blocks_pair", "blocker_id", "blocked_id", unique=True),
        sa.Index("ix_social_blocks_blocked_id", "blocked_id"),
    )


class Report(SocialBase):
    """One report of something on the site (Safety, piece 5): somebody, a post,
    a drawing shown outside a post, or a comment, with a reason from a closed
    set (safety.REASONS) and a note if they wrote one. A row in the admins'
    queue, never an action by itself: nothing is hidden until an admin takes
    it down. Who reported it (reporter_id) is for the admins' eyes only;
    reporter_key is a keyed hash of the reporter (a person, or for somebody
    signed out their address), so one reporter makes one row for one thing.
    A report outlives the thing it is about: whose it was (about_id) is set
    to nothing when their account goes, and the report stays a record."""
    __tablename__ = "social_reports"

    id = sa.Column(BigId, primary_key=True)
    public_id = sa.Column(sa.String(24), nullable=False)
    kind = sa.Column(sa.String(12), nullable=False)
    #: What is reported, by its own public id: a person's (site:...), a
    #: post's, a drawing's (Skribl's), a comment's.
    target = sa.Column(sa.String(40), nullable=False)
    #: Whose it is: the person reported, or the one who made the thing.
    about_id = sa.Column(BigId, sa.ForeignKey("social_people.id", ondelete="SET NULL"), nullable=True)
    reason = sa.Column(sa.String(16), nullable=False)
    note = sa.Column(sa.String(REPORT_NOTE_MAX), nullable=True)
    reporter_id = sa.Column(BigId, sa.ForeignKey("social_people.id", ondelete="SET NULL"), nullable=True)
    reporter_key = sa.Column(sa.String(64), nullable=False)
    state = sa.Column(sa.String(12), nullable=False, default="open", server_default="open")
    created_at = sa.Column(sa.DateTime(timezone=True), nullable=False, default=utcnow)
    handled_at = sa.Column(sa.DateTime(timezone=True), nullable=True)
    handled_by_id = sa.Column(BigId, sa.ForeignKey("social_people.id", ondelete="SET NULL"), nullable=True)

    __table_args__ = (
        sa.CheckConstraint("kind IN ('person', 'post', 'drawing', 'comment')", name="ck_social_reports_kind"),
        sa.CheckConstraint("state IN ('open', 'kept', 'taken_down')", name="ck_social_reports_state"),
        sa.Index("ix_social_reports_public_id", "public_id", unique=True),
        sa.Index("ix_social_reports_once", "kind", "target", "reporter_key", unique=True),
        sa.Index("ix_social_reports_state_created", "state", "created_at"),
        sa.Index("ix_social_reports_about_id", "about_id"),
        sa.Index("ix_social_reports_reporter_id", "reporter_id"),
        sa.Index("ix_social_reports_handled_by_id", "handled_by_id"),
    )


def attach_to_metadata(metadata):
    """Put the site's tables on a host's metadata, so its create_all() makes
    them too (the demo's `flask init-db` and the harness's fresh databases).
    A host that migrates runs social/migrations instead; not both."""
    for table in SocialBase.metadata.tables.values():
        if table.name not in metadata.tables:
            table.to_metadata(metadata)
