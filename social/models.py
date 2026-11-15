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

__all__ = ["SocialBase", "Person", "PersonWord", "Passkey", "Invite", "Challenge", "RateEvent", "Post",
           "Comment", "Like", "Bookmark", "Repost", "Mention", "Follow", "Mute", "Block", "Report", "PERSON_PREFIX",
           "WORD_MAX",
           "BIO_MAX",
           "BIO_LINES",
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


#: THEIR NAME IN SMALL LETTERS (mentions: the list under an @, "anybody whose
#: name starts with it"): an index of an expression, so it sits outside the
#: class, where the column can be named. Since finding people (PersonWord,
#: below) it is read for an @ alone, the list's first rows by name.
sa.Index("ix_social_people_name_key", sa.func.lower(Person.display_name))

#: How long a way of finding somebody is kept (PersonWord.word_key): a name is
#: 40 characters at most, and folding it (people.fold) seldom makes it longer.
WORD_MAX = 64

#: A way of finding somebody, as people.fold makes it: in byte order on both
#: engines. SQLite compares text byte by byte (its BINARY collation), and on
#: PostgreSQL the column is in the "C" collation, so there too a search's
#: range (every key from what was typed to the next letter after it) holds
#: exactly the keys that start with it, never one more or one less, whatever
#: language the database itself sorts in.
WordKey = sa.String(WORD_MAX).with_variant(sa.String(WORD_MAX, collation="C"), "postgresql")


class PersonWord(SocialBase):
    """A way somebody is found (finding people: the map, part two, item 5;
    the owner's "All yes" on the finding-people mock, Nov 15): their name
    from each of its words on ("theo park", "park"), and their @handle
    ("theo_p"), each folded (people.fold: small letters, accents put aside,
    anything that is not a letter or a digit one space). A search, and the
    list under an @, read the keys that start with what was typed, on
    ix_social_people_words_key; so "pa" finds Theo Park by the start of his
    last name, and "ar" finds nobody by the middle of it.

    WRITTEN IN CODE WHENEVER A NAME IS SET (people.write_words): joining
    (accounts.py) and Edit profile (profiles.py), in the same transaction as
    the name, the old keys taken away first, so a name changed is found by its
    new words and never its old. Nothing else sets a name or a handle. The
    people who were here before this table are filled in code, never by a
    migration (people.fill: `flask social words`, which gunicorn.conf.py runs
    once each start, after the site's chain).

    DELETING IS REAL AND SAID IN CODE (accounts.delete_person); the ON DELETE
    CASCADE is the net under it."""
    __tablename__ = "social_people_words"

    id = sa.Column(BigId, primary_key=True)
    #: Whose way it is.
    person_id = sa.Column(BigId, sa.ForeignKey("social_people.id", ondelete="CASCADE"), nullable=False)
    #: The way, folded: a name from one of its words on, or the @handle.
    word_key = sa.Column(WordKey, nullable=False)

    __table_args__ = (
        #: A search: every key from what was typed on, in order, then who.
        sa.Index("ix_social_people_words_key", "word_key", "person_id"),
        #: A person's own: written again with their name, read through your
        #: follows (the people you follow first), and once a person a key.
        sa.Index("ix_social_people_words_person", "person_id", "word_key", unique=True),
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
    ("More from"), each by an index of its own.

    A QUOTE POST (the map, part two, item 3; the owner's "All yes" on the
    reposts mock, Nov 14) is a post that shows another one small inside it:
    a post (quoted_post_id) or a drawing shown outside a post
    (quoted_drawing_id, the skribl's own public id), at most one of the two,
    and whose it is (quoted_owner_id: Activity's "Rook quoted your post", and
    deleting an account, never ask Skribl). Its words, its own drawing, or
    both: a quote of words alone has no skribl of its own (skribl_id is then
    None, and only a quote may be without one: ck_social_posts_drawn_or_quote).
    A QUOTE OUTLIVES WHAT IT QUOTES: is_quote is kept for good, while the
    links go when the original does (ON DELETE SET NULL, said in code first:
    reposts.py), so its small card can still say "This post is gone.", kindly.
    """
    __tablename__ = "social_posts"

    id = sa.Column(BigId, primary_key=True)
    public_id = sa.Column(sa.String(24), nullable=False)
    person_id = sa.Column(BigId, sa.ForeignKey("social_people.id", ondelete="CASCADE"), nullable=False)
    #: Plain text as typed, tidied (posts.check_words); may be empty.
    words = sa.Column(sa.String(WORDS_MAX), nullable=False, default="", server_default="")
    #: The post's drawing, Skribl's; None only for a quote of words alone.
    skribl_id = sa.Column(sa.String(32), nullable=True)
    created_at = sa.Column(sa.DateTime(timezone=True), nullable=False, default=utcnow)
    #: TAKEN DOWN by an admin (piece 5): when. Hidden from everybody but its
    #: author, who sees it with the note; its skribl withheld in Skribl. A
    #: copy is kept: nothing is deleted by it.
    taken_down_at = sa.Column(sa.DateTime(timezone=True), nullable=True)
    #: HIDDEN FROM THE GALLERY by its maker (the eye on their own Gallery tab,
    #: the owner's "Yes, the eye in view", Nov 14): when. Its drawing leaves
    #: the Gallery of everyone, the first visit and their Gallery as anybody
    #: else sees it; the post stays on Home, in their Posts and everywhere a
    #: post is. None: in the Gallery. The site's own: Skribl's visibility of
    #: the drawing is untouched (gallery.py).
    gallery_hidden_at = sa.Column(sa.DateTime(timezone=True), nullable=True)
    #: A QUOTE POST (above): whether it is one, for good, whatever became of
    #: what it quotes.
    is_quote = sa.Column(sa.Boolean(), nullable=False, default=False, server_default=sa.false())
    #: The post it quotes, while that post is there.
    quoted_post_id = sa.Column(BigId, sa.ForeignKey("social_posts.id", ondelete="SET NULL",
                                                    name="fk_social_posts_quoted_post_id"), nullable=True)
    #: The drawing shown outside a post it quotes (its skribl's public id),
    #: while it is one: posted through the composer's Yours, it is the post's
    #: (quoted_post_id), as its hearts and comments are.
    quoted_drawing_id = sa.Column(sa.String(32), nullable=True)
    #: Whose the post or the drawing it quotes is (its maker).
    quoted_owner_id = sa.Column(BigId, sa.ForeignKey("social_people.id", ondelete="SET NULL",
                                                     name="fk_social_posts_quoted_owner_id"), nullable=True)

    __table_args__ = (
        #: A drawing, or a quote (whose words may be all it has).
        sa.CheckConstraint("skribl_id IS NOT NULL OR is_quote", name="ck_social_posts_drawn_or_quote"),
        #: A quote shows one thing small: a post, or a drawing.
        sa.CheckConstraint("quoted_post_id IS NULL OR quoted_drawing_id IS NULL", name="ck_social_posts_quotes_one"),
        sa.Index("ix_social_posts_public_id", "public_id", unique=True),
        sa.Index("ix_social_posts_created", "created_at", "public_id"),
        sa.Index("ix_social_posts_person_created", "person_id", "created_at"),
        sa.Index("ix_social_posts_skribl_id", "skribl_id"),
        #: A post's quotes: its count, and its going (the links set to none).
        sa.Index("ix_social_posts_quoted_post_id", "quoted_post_id"),
        #: A drawing's quotes: its count, and its moving into a post.
        sa.Index("ix_social_posts_quoted_drawing_id", "quoted_drawing_id"),
        #: Quotes of what a person made, newest first: Activity, and deleting
        #: an account.
        sa.Index("ix_social_posts_quoted_owner_created", "quoted_owner_id", "created_at"),
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
        #: Who liked, newest first: your profile's Likes tab (the map's step 4).
        sa.Index("ix_social_likes_person_created", "person_id", "created_at"),
    )


class Bookmark(SocialBase):
    """A bookmark (the map, part two, item 2; the owner's "All yes" on the
    bookmarks mock, Nov 14): one person keeping a post, or a drawing shown
    outside a post, to come back to, once; "Remove bookmark" takes it away,
    and the row goes. Shaped as a like is: on a post (post_id) or a drawing
    (drawing_id, the skribl's own public id), exactly one
    (ck_social_bookmarks_on_one), and owner_id is whose that post or drawing
    is, kept on the row so a block and deleting an account never ask Skribl.
    A person keeps a thing once: the two unique indexes (an id is empty on
    the other kind, and empties never collide).

    YOURS ALONE, AND NOBODY IS TOLD (bookmarks.py): your own page's
    Bookmarks tab reads them, newest first, by the person's own index; no
    page counts them, and Activity never reads them.

    DELETING IS REAL AND SAID IN CODE (bookmarks.py, from posts.drop_post,
    posts.bloob_delete and accounts.delete_person): a post or a drawing goes
    with its bookmarks, an account with its own and every bookmark on what it
    owned. The ON DELETE CASCADEs are the net under that, as for likes."""
    __tablename__ = "social_bookmarks"

    id = sa.Column(BigId, primary_key=True)
    #: The post it keeps, or None for one on a drawing shown outside a post.
    post_id = sa.Column(BigId, sa.ForeignKey("social_posts.id", ondelete="CASCADE"), nullable=True)
    #: The drawing it keeps (shown outside a post), by its skribl's public id.
    drawing_id = sa.Column(sa.String(32), nullable=True)
    #: Whose the post or the drawing is (its maker).
    owner_id = sa.Column(BigId, sa.ForeignKey("social_people.id", ondelete="CASCADE"), nullable=False)
    #: Who kept it.
    person_id = sa.Column(BigId, sa.ForeignKey("social_people.id", ondelete="CASCADE"), nullable=False)
    created_at = sa.Column(sa.DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        #: On a post or on a drawing: exactly one.
        sa.CheckConstraint("(post_id IS NOT NULL AND drawing_id IS NULL) OR (post_id IS NULL AND drawing_id IS NOT NULL)",
                           name="ck_social_bookmarks_on_one"),
        #: Once a person, once a thing.
        sa.Index("ix_social_bookmarks_person_post", "person_id", "post_id", unique=True),
        sa.Index("ix_social_bookmarks_person_drawing", "person_id", "drawing_id", unique=True),
        #: Yours, newest first: your own page's Bookmarks tab.
        sa.Index("ix_social_bookmarks_person_created", "person_id", "created_at"),
        #: A thing's: deleting a post or a drawing, and a drawing's moving
        #: into a post, take its bookmarks by these.
        sa.Index("ix_social_bookmarks_post_id", "post_id"),
        sa.Index("ix_social_bookmarks_drawing_id", "drawing_id"),
        #: Whose: deleting an account takes every bookmark on what it owned.
        sa.Index("ix_social_bookmarks_owner_id", "owner_id"),
    )


class Repost(SocialBase):
    """A repost (the map, part two, item 3; the owner's "All yes" on the
    reposts mock, Nov 14): one person showing a post (somebody's, or their
    own) to the people who follow them, once; "Undo repost" takes it away,
    and the row goes. ONE DRAWING, ONE CONVERSATION: a repost is no post of
    its own. It shows the original, on Home's Following for the people who
    follow the reposter and on the reposter's Posts tab, with "Mira Lopez
    reposted" at the top of the original's own card, its hearts and comments
    the original's (reposts.py). A drawing shown outside a post is reposted
    by nobody (only its maker posts it); it can be quoted.

    owner_id is whose the post is (its author), kept on the row so a block,
    Activity ("Mira reposted your post") and deleting an account never ask
    anything else. A person reposts a post once (the unique pair).

    DELETING IS REAL AND SAID IN CODE (reposts.py, from posts.drop_post and
    accounts.delete_person): a post goes with its reposts, an account with
    its own and every repost of what it owned. The ON DELETE CASCADEs are
    the net under that, as for likes."""
    __tablename__ = "social_reposts"

    id = sa.Column(BigId, primary_key=True)
    #: Who reposted it.
    person_id = sa.Column(BigId, sa.ForeignKey("social_people.id", ondelete="CASCADE"), nullable=False)
    #: The post reposted (the original).
    post_id = sa.Column(BigId, sa.ForeignKey("social_posts.id", ondelete="CASCADE"), nullable=False)
    #: Whose the post is (its author).
    owner_id = sa.Column(BigId, sa.ForeignKey("social_people.id", ondelete="CASCADE"), nullable=False)
    created_at = sa.Column(sa.DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        #: Once a person, once a post.
        sa.Index("ix_social_reposts_person_post", "person_id", "post_id", unique=True),
        #: A person's, newest first: their Posts tab, and Home's Following.
        sa.Index("ix_social_reposts_person_created", "person_id", "created_at"),
        #: A post's: its count, and its going.
        sa.Index("ix_social_reposts_post_id", "post_id"),
        #: Whose, newest first: Activity's reposts of what you made.
        sa.Index("ix_social_reposts_owner_created", "owner_id", "created_at"),
    )


class Mention(SocialBase):
    """A mention (the map, part two, item 4; the owner's "All yes" on the
    mentions mock, Nov 15): an @handle in a post's words, or in a comment's
    or an answer's, that is somebody. Written in the same transaction as the
    post or the comment (mentions.py), the first ten people named in it
    (mentions.MOST), and never changed after: posts and comments can't be
    edited.

    WHO, AND AS TYPED: person_id is who was mentioned, `typed` the handle as
    it was typed (without the @). The words keep their own spelling, and the
    link goes to the person by their id, so a handle that changes later
    never breaks an old mention: "@as-typed" still opens their page.

    ON A POST OR ON A COMMENT, exactly one (ck_social_mentions_on_one). by_id
    is who wrote it; owner_id whose the post is, or what the comment is on (a
    post or a drawing shown outside a post), kept on the row as a comment
    keeps it, so deleting an account never asks anything else.

    TOLD IN ACTIVITY, worked out at read time (activity.py), never kept as a
    row of its own: "Rook mentioned you". Once a person a post, and once a
    person a comment (the two unique indexes).

    DELETING IS REAL AND SAID IN CODE (mentions.py, from posts.drop_post,
    comments' every delete and accounts.delete_person): a post or a comment
    goes with its mentions, an account with the mentions of it and every
    mention it wrote. The ON DELETE CASCADEs are the net under that."""
    __tablename__ = "social_mentions"

    id = sa.Column(BigId, primary_key=True)
    #: Who was mentioned.
    person_id = sa.Column(BigId, sa.ForeignKey("social_people.id", ondelete="CASCADE"), nullable=False)
    #: Who wrote the words.
    by_id = sa.Column(BigId, sa.ForeignKey("social_people.id", ondelete="CASCADE"), nullable=False)
    #: The post whose words mention them, or None for a comment's.
    post_id = sa.Column(BigId, sa.ForeignKey("social_posts.id", ondelete="CASCADE"), nullable=True)
    #: The comment (or answer) whose words mention them, or None for a post's.
    comment_id = sa.Column(BigId, sa.ForeignKey("social_comments.id", ondelete="CASCADE"), nullable=True)
    #: Whose the post is, or what the comment is on (its maker).
    owner_id = sa.Column(BigId, sa.ForeignKey("social_people.id", ondelete="CASCADE"), nullable=False)
    #: The handle as it was typed, without the @.
    typed = sa.Column(sa.String(20), nullable=False)
    created_at = sa.Column(sa.DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        #: In a post or in a comment: exactly one.
        sa.CheckConstraint("(post_id IS NOT NULL AND comment_id IS NULL) OR (post_id IS NULL AND comment_id IS NOT NULL)",
                           name="ck_social_mentions_on_one"),
        #: Once a person, once a post or a comment.
        sa.Index("ix_social_mentions_person_post", "person_id", "post_id", unique=True),
        sa.Index("ix_social_mentions_person_comment", "person_id", "comment_id", unique=True),
        #: Theirs, newest first: Activity's "mentioned you", and the bell's dot.
        sa.Index("ix_social_mentions_person_created", "person_id", "created_at"),
        #: A post's and a comment's: the links in their words (one read a
        #: page), and their going.
        sa.Index("ix_social_mentions_post_id", "post_id"),
        sa.Index("ix_social_mentions_comment_id", "comment_id"),
        #: Who wrote them, and whose: deleting an account.
        sa.Index("ix_social_mentions_by_id", "by_id"),
        sa.Index("ix_social_mentions_owner_id", "owner_id"),
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
    (their Followers list, the counts on their page, and Activity's
    "followed you", since you last looked and before)."""
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


class Mute(SocialBase):
    """One person muting another (phase 2, mutes; the owner's "Yes to all" on
    the mute mock, C, quiet everywhere, Nov 13): what the muted person makes
    stops reaching the one who muted them (their posts and drawings leave
    Home and Explore, their comments fold to a line with Show, their likes,
    comments and follows leave Activity), while their page and their posts
    stay open to them (mutes.py). ONE WAY AND QUIET: nothing changes for the
    person muted, and they are never told; who muted whom is only ever the
    muter's to see (Settings, Muted).

    One row a pair (unique), and nobody mutes themselves
    (ck_social_mutes_not_self). Unmuting deletes the row: nothing about a
    mute is kept once it is lifted, and nothing it quieted was ever deleted
    (Activity and the comments are read each time), so all of it comes back.
    It never touches a follow, either way (the owner's rule 3), and a block
    leaves it standing: lift the block and they are still muted, as it was.

    Indexed by whose and when, newest first (Settings' list), by the pair
    (the once-a-request read of whom a person muted, and one row a pair), and
    by whom (deleting an account, both ways, and the cascade's own net).
    Deleting an account takes its rows both ways, in code (accounts.
    delete_person); the ON DELETE CASCADEs are the net under that."""
    __tablename__ = "social_mutes"

    id = sa.Column(BigId, primary_key=True)
    #: Who muted.
    muter_id = sa.Column(BigId, sa.ForeignKey("social_people.id", ondelete="CASCADE"), nullable=False)
    #: Whom.
    muted_id = sa.Column(BigId, sa.ForeignKey("social_people.id", ondelete="CASCADE"), nullable=False)
    #: When.
    created_at = sa.Column(sa.DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        #: Nobody mutes themselves.
        sa.CheckConstraint("muter_id <> muted_id", name="ck_social_mutes_not_self"),
        #: One row a pair; whom a person muted, read once a request.
        sa.Index("ix_social_mutes_pair", "muter_id", "muted_id", unique=True),
        #: Whom a person muted, newest first (Settings).
        sa.Index("ix_social_mutes_muter_created", "muter_id", "created_at"),
        #: Who muted a person (deleting an account, both ways).
        sa.Index("ix_social_mutes_muted_id", "muted_id"),
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
