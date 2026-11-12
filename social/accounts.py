"""Accounts on the site: invite-only, passkeys alone (phase 1, piece 2).

The owner's answers for this piece ("all yes", Nov 10): built on the demo's
own address for invited people now (their passkeys are made again after the
move to a domain, so no host is written anywhere); passkeys alone, no email
yet; invite-only until a lawyer has read the terms.

    /join#<code>                     an invite: a name, a handle, "I'm 13 or
                                     older", a passkey, and signed in
    /signin                          "Sign in with a passkey": the passkey
                                     says whose it is, nothing typed
    /signout, /signout/everywhere    this browser; every browser
    /you                             name and handle, the passkeys (add,
                                     rename, remove, never the last), sign
                                     out, delete the account
    /invites                         admins only, a 404 to anyone else: make
                                     a join link (once, 14 days), a recovery
                                     link for a named person (once, an hour),
                                     the unused ones, revoke
    /recover#<code>                  a recovery link: adds a passkey to the
                                     person it was made for, and signs in

A LINK'S CODE IS AFTER THE #, which a browser keeps to itself: the page reads
it and sends it in the body of a POST (check, options, verify), so no access
log, proxy log or Referer ever holds it. Only its SHA-256 is stored.

THE FIRST PERSON. SKRIBL_SOCIAL_FIRST_INVITE is a code that works as a join
link only while the site has no people, compared in constant time, and the
person it makes is an admin. Spent, it is a used invite row with that code's
hash, so two people racing for it cannot both win. `flask social invite`
prints a join link from a shell (cli.py).

EVERY STATE-CHANGING REQUEST passes security.guard() (its Origin is ours and
it carries this browser's token) and then its limit, before it reads anything
(security.over: on SQLite a read held open would keep the limit's own commit
waiting). The passkey ceremonies are JSON, with the token in a header, and a
challenge bound to this browser and used once. Nothing here commits: the host
commits the request (app.py), and an answer of 500 or more is rolled back.

A SITE WHOSE TABLES CANNOT BE READ RESTS: its pages say so kindly (503), and
nobody is signed in, while the Pad, Flip and the rest of the demo go on.
"""
import functools
import hashlib
import hmac
import json
import re
import secrets
import unicodedata
from datetime import datetime, timedelta

import sqlalchemy as sa
from flask import (abort, current_app, g, jsonify, redirect, render_template, request,
                   url_for)
from werkzeug.routing import BuildError

from . import passkeys
from .models import (BIO_LINES, BIO_MAX, Challenge, Invite, Passkey, Person, Post, as_utc,
                     new_person_id, new_public_id, utcnow)
from .security import (client_subject, csrf_token, current_person, guard, origin_ok, over,
                       public_origin, sign_in, sign_out, site, token_ok)

JOIN_FOR = timedelta(days=14)
RECOVER_FOR = timedelta(hours=1)

HANDLE_RE = re.compile(r"[A-Za-z][A-Za-z0-9_]{2,19}")
#: Handles kept for the site itself, or that would read as if they were.
RESERVED = frozenset("""
    admin administrator api app blooby edit explore help home invite invites join
    me mod moderator moderators new null official root security settings signin
    signout signup site skribl skribls social staff static support system team you
    """.split())
#: Bidi controls and other invisible formatting: a name may not hide in them.
#: The joiner inside emoji sequences (U+200D) stays allowed.
_ALLOWED_FORMAT = {"‍"}


def _hash_code(code):
    return hashlib.sha256(("invite|" + code).encode()).hexdigest()


# ---- the words come from the templates; these are their keys --------------

def _json_error(key, status, **extra):
    return jsonify({"error": key, **extra}), status


def _page(name, status=200, **ctx):
    resp = current_app.response_class(render_template("social/" + name, **ctx), status=status,
                                      mimetype="text/html")
    resp.headers["Cache-Control"] = "no-store"
    return resp


def _resting(json_answer):
    """The site's tables cannot be read: say so once in the log, kindly on
    the page, and roll back whatever the request had started."""
    try:
        site().session().rollback()
    except Exception:            # noqa: BLE001 -- resting already; nothing more to undo
        pass
    site().say_once("resting", "the site's tables could not be read or written, so sign-in "
                               "rests (503) until they can. Are they built? python -m alembic "
                               "-c social/alembic.ini upgrade head")
    if json_answer:
        return _json_error("resting", 503)
    return _page("resting.html", 503, here="resting", hide_nav=True)


def _rests(json_answer=False):
    def wrap(view):
        @functools.wraps(view)
        def inner(*a, **kw):
            try:
                return view(*a, **kw)
            except sa.exc.SQLAlchemyError:
                current_app.logger.debug("site view %s failed on the database", view.__name__,
                                         exc_info=True)
                return _resting(json_answer)
        return inner
    return wrap


def _refused_page():
    """A form that did not come from the site's own page in this browser
    (or a page that went stale): never blamed on the person."""
    return _page("stale.html", 403, here="stale", hide_nav=True)


def _limited_page():
    return _page("limited.html", 429, here="limited", hide_nav=True)


def _safe_next(raw):
    """Where to go after signing in: a path on this site, or Home."""
    if (isinstance(raw, str) and raw.startswith("/") and not raw.startswith("//")
            and "\\" not in raw and len(raw) <= 300 and not any(c in raw for c in "\r\n\t")):
        return raw
    return url_for("social.home")


# ---- what a person types ----------------------------------------------------

def check_handle(raw):
    h = (raw if isinstance(raw, str) else "").strip()
    if h.startswith("@"):
        h = h[1:]
    if not HANDLE_RE.fullmatch(h):
        return None, "handle_shape"
    if h.lower() in RESERVED:
        return None, "handle_reserved"
    return h, None


def check_name(raw, limit=40):
    """A name as people will see it, or why not. Anything but text is no name
    (a body can say anything; it is answered, never a 500)."""
    n = " ".join(unicodedata.normalize("NFC", raw if isinstance(raw, str) else "").split())
    if not n:
        return None, "name_empty"
    if len(n) > limit:
        return None, "name_long"
    if _hidden_in(n):
        return None, "name_chars"
    return n, None


def _hidden_in(text):
    """Whether `text` holds a character nobody can see or that turns the text
    around (controls, bidi and other invisible formatting, unassigned or
    private code points). A line break is a bio's own, and is allowed there."""
    for ch in text:
        if ch == "\n":
            continue
        cat = unicodedata.category(ch)
        if cat in ("Cc", "Co", "Cs", "Cn") or (cat == "Cf" and ch not in _ALLOWED_FORMAT):
            return True
    return False


def check_bio(raw):
    """A few lines about a person (piece 3), as people will see them, or why
    not: plain text, at most BIO_MAX characters on at most BIO_LINES lines,
    each line's spaces tidied and blank lines run together, nothing hidden or
    turned around (as a name). Empty is allowed: no bio. Links are not made
    into links (not yet): a bio is shown as the words typed. Anything but text
    is no bio, answered, never a 500."""
    text = unicodedata.normalize("NFC", raw if isinstance(raw, str) else "")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = []
    for line in text.split("\n"):
        line = " ".join(line.split())
        if line or (lines and lines[-1]):
            lines.append(line)
    while lines and not lines[-1]:
        lines.pop()
    bio = "\n".join(lines)
    if not bio:
        return None, None
    if len(bio) > BIO_MAX:
        return None, "bio_long"
    if len(lines) > BIO_LINES:
        return None, "bio_lines"
    if _hidden_in(bio):
        return None, "bio_chars"
    return bio, None


def _body():
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


def _rp_or_error():
    try:
        return passkeys.rp(), None
    except passkeys.NoName:
        return None, _json_error("no_name", 400)
    except passkeys.Elsewhere:
        return None, _json_error("elsewhere", 400)


# ---- invites ----------------------------------------------------------------

def make_invite(sess, kind, *, created_by_id=None, for_person_id=None):
    """A new link's code (shown once) and its row (which keeps only a hash)."""
    code = secrets.token_urlsafe(16)
    now = utcnow()
    inv = Invite(public_id=new_public_id(), code_hash=_hash_code(code), kind=kind,
                 for_person_id=for_person_id, created_by_id=created_by_id, created_at=now,
                 expires_at=now + (JOIN_FOR if kind == "join" else RECOVER_FOR))
    sess.add(inv)
    sess.flush()
    return code, inv


def _find_invite(sess, code, kind):
    if not code or len(code) > 200:
        return None
    inv = sess.execute(sa.select(Invite).where(Invite.code_hash == _hash_code(code))).scalar_one_or_none()
    if inv is None or inv.kind != kind or inv.used_at is not None or as_utc(inv.expires_at) <= utcnow():
        return None
    return inv


def _is_first_invite(sess, code):
    """The bootstrap code, while the site has nobody: compared in constant
    time, and only once the code is long enough to mean something."""
    first = site().first_invite
    if not first or not code:
        return False
    same = hmac.compare_digest(hashlib.sha256(code.encode()).digest(),
                               hashlib.sha256(first.encode()).digest())
    if not same:
        return False
    return sess.execute(sa.select(Person.id).limit(1)).first() is None


def _claim(sess, inv, person_id):
    """Spend an invite: only while it is unused and in date. Two people
    finishing one link at once: one gets it, the other is told it is gone."""
    now = utcnow()
    done = sess.execute(sa.update(Invite)
                        .where(Invite.id == inv.id, Invite.used_at.is_(None), Invite.expires_at > now)
                        .values(used_at=now, used_by_id=person_id)
                        .execution_options(synchronize_session=False))
    return done.rowcount == 1


def link_for(code, kind):
    """The whole link, on the address this request came to, the code after
    the # (which a browser never sends to a server: no log sees it)."""
    return public_origin() + url_for("social.join" if kind == "join" else "social.recover") + "#" + code


def drop_face(public_id, face_id):
    """Delete a face skribl the site posted for `public_id`, through Skribl's
    documented seam (delete_post, docs/INTEGRATION.md "Taking one back"), as
    its author: in the request's transaction, which commits with the row
    that stops naming it. One already gone (deleted in the Library, say) is
    gone: nothing to do."""
    if not face_id:
        return False
    from skribl import SkriblNotFound, delete_post
    try:
        delete_post(face_id, author_id=public_id)
    except SkriblNotFound:
        return False
    return True


def delete_person(sess, person_id):
    """REAL DELETION (docs/SOCIAL-SITE.md, section 3, rule 9): the person,
    their passkeys, the invites they made, the recovery links made for them,
    the invite they came in by, ceremonies in progress, their bio with their
    row, their drawn face (the skribl the site posted for it, through
    Skribl's delete_post), their posts, the words and the drawings both
    (piece 4: the site posted those too), and their blocks, both ways
    (piece 5); a report that names them stays, naming nobody. Flushes; the
    request commits.
    (Their other skribls are Skribl's, and docs/INTEGRATION.md has no seam
    for a host to take an author's drawings away in one go: they stay, and
    the confirm page says so.)"""
    row = sess.execute(sa.select(Person.public_id, Person.face_id).where(Person.id == person_id)).first()
    if row is not None:
        drop_face(row.public_id, row.face_id)
        from .posts import drop_post
        for post in sess.execute(sa.select(Post).where(Post.person_id == person_id)).scalars().all():
            drop_post(row.public_id, post)
    sess.execute(sa.delete(Challenge).where(Challenge.person_id == person_id))
    invites = sa.select(Invite.id).where(sa.or_(Invite.created_by_id == person_id,
                                               Invite.for_person_id == person_id,
                                               Invite.used_by_id == person_id))
    ids = [r[0] for r in sess.execute(invites)]
    if ids:
        sess.execute(sa.delete(Challenge).where(Challenge.invite_id.in_(ids)))
        sess.execute(sa.delete(Invite).where(Invite.id.in_(ids)))
    sess.execute(sa.delete(Passkey).where(Passkey.person_id == person_id))
    # Their blocks go, both ways (piece 5). The reports that name them stay,
    # as a record, naming nobody: whose it was, who sent it, who handled it.
    from .models import Block, Report
    sess.execute(sa.delete(Block).where(sa.or_(Block.blocker_id == person_id, Block.blocked_id == person_id)))
    for col in (Report.about_id, Report.reporter_id, Report.handled_by_id):
        sess.execute(sa.update(Report).where(col == person_id).values({col.key: None}))
    sess.execute(sa.delete(Person).where(Person.id == person_id))
    sess.flush()


def describe_author(user_id):
    """For Skribl's author resolver: a site person's name and handle, the
    address of their profile (`url`, which Skribl's Gallery card links their
    name to), and their drawn face when they have one (`face`, which the card
    shows in the avatar's circle: docs/INTEGRATION.md), or None for any id
    that is not one of the site's people. Read as the signed-in person is
    (security.read_aside: beside the request's own work, never deadlocking
    SQLite), and never a failure that reaches Skribl's page."""
    from .models import PERSON_PREFIX
    if not isinstance(user_id, str) or not user_id.startswith(PERSON_PREFIX):
        return None
    if "social" not in current_app.extensions:
        return None
    t = Person.__table__
    from .security import read_aside
    try:
        rows = read_aside(sa.select(t.c.handle, t.c.display_name, t.c.face_id, t.c.face_w, t.c.face_h)
                          .where(t.c.public_id == user_id))
        row = rows[0] if rows else None
    except sa.exc.SQLAlchemyError:
        site().say_once("unread-authors", "the site could not read its people for a drawing's "
                                          "author: those drawings show no name until it can")
        return None
    if row is None:
        return None
    out = {"username": row.handle, "display_name": row.display_name}
    url = profile_url(row.handle)
    if url:
        out["url"] = url
    if row.face_id:
        out["face"] = {"id": row.face_id, "w": row.face_w or 1, "h": row.face_h or 1}
    return out


def profile_url(handle):
    """A person's profile, /social/@<handle> where the site is mounted: a
    path, which the Gallery resolves against the page it is on. None where no
    address can be built (no request: a shell), so a name is still said."""
    try:
        return url_for("social.profile", handle=handle)
    except (RuntimeError, BuildError):
        return None


# ---- the routes ---------------------------------------------------------------

def register(bp):
    """Add the account pages to the site's blueprint."""

    def me_or_signin():
        person = current_person()
        if person is None:
            return None, redirect(url_for("social.signin", next=request.path), 303)
        return person, None

    # -- sign in ----------------------------------------------------------------

    @bp.get("/signin")
    def signin():
        """Sign in: "Sign in with a passkey", nothing typed (discoverable)."""
        person = current_person()
        nxt = _safe_next(request.args.get("next"))
        if person is not None:
            return redirect(nxt, 303)
        note = {"1": "out", "all": "out_all"}.get(request.args.get("out", ""))
        return _page("signin.html", here="signin", hide_nav=True, note=note, next_url=nxt,
                     token=csrf_token())

    @bp.post("/signin/options")
    @_rests(json_answer=True)
    def signin_options():
        """The challenge a passkey signs to sign in (JSON)."""
        if not origin_ok() or not token_ok():
            return _json_error("stale", 403)
        if over("signin", client_subject()):
            return _json_error("limited", 429)
        where, err = _rp_or_error()
        if err:
            return err
        challenge = passkeys.begin("signin")
        return jsonify({"options": passkeys.authentication_options(challenge, rp_id=where[0])})

    @bp.post("/signin/verify")
    @_rests(json_answer=True)
    def signin_verify():
        """The passkey's answer: checked, then signed in (JSON)."""
        if not origin_ok() or not token_ok():
            return _json_error("stale", 403)
        where, err = _rp_or_error()
        if err:
            return err
        row = passkeys.take("signin")
        if row is None:
            return _json_error("expired", 400)
        sess = site().session()
        try:
            parsed = passkeys.read_assertion(_body().get("credential"))
            key = sess.execute(sa.select(Passkey).where(Passkey.credential_id == parsed.raw_id)
                               ).scalar_one_or_none()
            if key is None or key.rp_id != where[0]:
                return _json_error("unknown", 400)
            person = sess.get(Person, key.person_id)
            if person is None or (parsed.response.user_handle is not None
                                  and not hmac.compare_digest(parsed.response.user_handle,
                                                              person.user_handle)):
                return _json_error("unknown", 400)
            ok = passkeys.verify_assertion(parsed, row.challenge, rp_id=where[0], origin=where[1],
                                           public_key=key.public_key, sign_count=int(key.sign_count))
        except passkeys.Refused as no:
            return _json_error(no.key, 400)
        key.sign_count = ok.new_sign_count
        key.backed_up = bool(ok.credential_backed_up)
        key.last_used_at = utcnow()
        sign_in(person)
        return jsonify({"ok": True, "go": _safe_next(_body().get("next"))})

    @bp.post("/signout")
    def signout():
        """Sign out of this browser."""
        if not origin_ok() or not token_ok():
            return _refused_page()
        sign_out()
        return redirect(url_for("social.signin", out="1"), 303)

    @bp.post("/signout/everywhere")
    @_rests()
    def signout_everywhere():
        """Sign out of every browser: the person's generation goes up one, and
        every cookie that carries the old one is nobody's."""
        if not origin_ok() or not token_ok():
            return _refused_page()
        person = current_person()
        if person is None:
            return redirect(url_for("social.signin"), 303)
        sess = site().session()
        sess.execute(sa.update(Person).where(Person.id == person.id)
                     .values(session_gen=Person.session_gen + 1)
                     .execution_options(synchronize_session=False))
        sign_out()
        return redirect(url_for("social.signin", out="all"), 303)

    # -- join ---------------------------------------------------------------------
    #
    # THE CODE NEVER TRAVELS IN AN ADDRESS THE SERVER SEES. A link is
    # /social/join#<code>: a browser keeps what follows the # to itself, so
    # the code is in no access log, proxy log or Referer on the way. The page
    # reads it and posts it (check, then options and verify), in the body.

    def _code():
        code = _body().get("code")
        return code if isinstance(code, str) and 0 < len(code) <= 200 else ""

    @bp.get("/join")
    def join():
        """An invite link's page: its script checks the code (after the #)."""
        return _page("join.html", here="join", hide_nav=True, token=csrf_token())

    @bp.post("/join/check")
    @_rests(json_answer=True)
    def join_check():
        """Whether an invite's code still lets somebody in (JSON): one answer,
        404, for used, run out, revoked and never made alike."""
        if not origin_ok() or not token_ok():
            return _json_error("stale", 403)
        code = _code()
        if over("link-look", client_subject()) or over("invite-use", "code|" + _hash_code(code)):
            return _json_error("limited", 429)
        sess = site().session()
        first = _is_first_invite(sess, code)
        if not first and _find_invite(sess, code, "join") is None:
            return _json_error("gone", 404)
        return jsonify({"ok": True, "first": first})

    @bp.post("/join/options")
    @_rests(json_answer=True)
    def join_options():
        """Check the name, handle and age, then the challenge for a new
        passkey (JSON)."""
        if not origin_ok() or not token_ok():
            return _json_error("stale", 403)
        code = _code()
        if over("join", client_subject()) or over("invite-use", "code|" + _hash_code(code)):
            return _json_error("limited", 429)
        where, err = _rp_or_error()
        if err:
            return err
        sess = site().session()
        first = _is_first_invite(sess, code)
        inv = None if first else _find_invite(sess, code, "join")
        if not first and inv is None:
            return _json_error("gone", 410)
        body = _body()
        name, name_err = check_name(body.get("name"))
        handle, handle_err = check_handle(body.get("handle"))
        errors = {k: v for k, v in (("name", name_err), ("handle", handle_err)) if v}
        if body.get("age13") is not True:
            errors["age13"] = "age"
        if not errors and sess.execute(sa.select(Person.id).where(Person.handle_key == handle.lower())).first():
            errors["handle"] = "handle_taken"
        if errors:
            return _json_error("fields", 400, fields=errors)
        user_handle = secrets.token_bytes(32)
        challenge = passkeys.begin("join", invite_id=inv.id if inv else None,
                                   data={"handle": handle, "name": name, "first": first,
                                         "age_at": utcnow().isoformat(),
                                         "user_handle": user_handle.hex()})
        return jsonify({"options": passkeys.registration_options(
            challenge, rp_id=where[0], user_handle=user_handle, handle=handle, display_name=name)})

    @bp.post("/join/verify")
    @_rests(json_answer=True)
    def join_verify():
        """The new passkey: checked, the person made, the invite spent, and
        signed in (JSON)."""
        if not origin_ok() or not token_ok():
            return _json_error("stale", 403)
        code = _code()
        where, err = _rp_or_error()
        if err:
            return err
        row = passkeys.take("join")
        if row is None:
            return _json_error("expired", 400)
        sess = site().session()
        data = json.loads(row.data or "{}")
        first = bool(data.get("first"))
        if first:
            if not _is_first_invite(sess, code):
                return _json_error("gone", 410)
        else:
            inv = sess.get(Invite, row.invite_id) if row.invite_id else None
            if inv is None or inv.code_hash != _hash_code(code) or _find_invite(sess, code, "join") is None:
                return _json_error("gone", 410)
        credential = _body().get("credential")
        try:
            made = passkeys.verify_registration(credential, row.challenge, rp_id=where[0], origin=where[1])
        except passkeys.Refused as no:
            return _json_error(no.key, 400)
        person = Person(public_id=new_person_id(), handle=data["handle"], handle_key=data["handle"].lower(),
                        display_name=data["name"], user_handle=bytes.fromhex(data["user_handle"]),
                        is_admin=first, session_gen=1,
                        age_confirmed_at=datetime.fromisoformat(data["age_at"]), created_at=utcnow())
        try:
            with sess.begin_nested():
                sess.add(person)
                sess.flush()
                if first:
                    # The first invite, spent: a used row with its hash, which
                    # a second person racing for it cannot also write.
                    now = utcnow()
                    sess.add(Invite(public_id=new_public_id(), code_hash=_hash_code(code), kind="join",
                                    created_at=now, expires_at=now, used_at=now, used_by_id=person.id))
                    sess.flush()
                elif not _claim(sess, inv, person.id):
                    raise _Gone()
                sess.add(Passkey(public_id=new_public_id(), person_id=person.id,
                                 credential_id=made.credential_id, public_key=made.credential_public_key,
                                 sign_count=made.sign_count, transports=passkeys.transports_of(credential),
                                 rp_id=where[0], backed_up=bool(made.credential_backed_up),
                                 nickname=passkeys.default_nickname(request.user_agent.string, ()),
                                 created_at=utcnow(), last_used_at=utcnow()))
                sess.flush()
        except sa.exc.IntegrityError:
            taken = sess.execute(sa.select(Person.id).where(Person.handle_key == data["handle"].lower())).first()
            return (_json_error("fields", 409, fields={"handle": "handle_taken"}) if taken
                    else _json_error("gone", 410))
        except _Gone:
            return _json_error("gone", 410)
        sign_in(person)
        return jsonify({"ok": True, "go": url_for("social.home")})

    # -- recovery: a link that adds a passkey to a named person's account --------

    @bp.get("/recover")
    def recover():
        """A recovery link's page: its script checks the code (after the #),
        then adds a passkey to the account the link was made for."""
        return _page("recover.html", here="recover", hide_nav=True, token=csrf_token())

    @bp.post("/recover/check")
    @_rests(json_answer=True)
    def recover_check():
        """Whose account a recovery link's code is for, while it works (JSON);
        404 alike for every link that does not."""
        if not origin_ok() or not token_ok():
            return _json_error("stale", 403)
        code = _code()
        if over("link-look", client_subject()) or over("invite-use", "code|" + _hash_code(code)):
            return _json_error("limited", 429)
        sess = site().session()
        inv = _find_invite(sess, code, "recover")
        person = sess.get(Person, inv.for_person_id) if inv and inv.for_person_id else None
        if person is None:
            return _json_error("gone", 404)
        return jsonify({"ok": True, "handle": person.handle})

    @bp.post("/recover/options")
    @_rests(json_answer=True)
    def recover_options():
        """The challenge for a new passkey on the link's account (JSON)."""
        if not origin_ok() or not token_ok():
            return _json_error("stale", 403)
        code = _code()
        if over("recover", client_subject()) or over("invite-use", "code|" + _hash_code(code)):
            return _json_error("limited", 429)
        where, err = _rp_or_error()
        if err:
            return err
        sess = site().session()
        inv = _find_invite(sess, code, "recover")
        person = sess.get(Person, inv.for_person_id) if inv and inv.for_person_id else None
        if person is None:
            return _json_error("gone", 410)
        have = [k.credential_id for k in sess.execute(
            sa.select(Passkey).where(Passkey.person_id == person.id)).scalars()]
        challenge = passkeys.begin("recover", person_id=person.id, invite_id=inv.id)
        return jsonify({"options": passkeys.registration_options(
            challenge, rp_id=where[0], user_handle=person.user_handle, handle=person.handle,
            display_name=person.display_name, exclude=have)})

    @bp.post("/recover/verify")
    @_rests(json_answer=True)
    def recover_verify():
        """The new passkey: checked, added to the link's account, the link
        spent, and signed in (JSON)."""
        if not origin_ok() or not token_ok():
            return _json_error("stale", 403)
        code = _code()
        where, err = _rp_or_error()
        if err:
            return err
        row = passkeys.take("recover")
        if row is None:
            return _json_error("expired", 400)
        sess = site().session()
        inv = sess.get(Invite, row.invite_id) if row.invite_id else None
        if (inv is None or inv.code_hash != _hash_code(code) or inv.for_person_id != row.person_id
                or _find_invite(sess, code, "recover") is None):
            return _json_error("gone", 410)
        person = sess.get(Person, row.person_id)
        if person is None:
            return _json_error("gone", 410)
        credential = _body().get("credential")
        try:
            made = passkeys.verify_registration(credential, row.challenge, rp_id=where[0], origin=where[1])
        except passkeys.Refused as no:
            return _json_error(no.key, 400)
        names = [k.nickname for k in sess.execute(sa.select(Passkey).where(Passkey.person_id == person.id)).scalars()]
        try:
            with sess.begin_nested():
                if not _claim(sess, inv, person.id):
                    raise _Gone()
                sess.add(Passkey(public_id=new_public_id(), person_id=person.id,
                                 credential_id=made.credential_id, public_key=made.credential_public_key,
                                 sign_count=made.sign_count, transports=passkeys.transports_of(credential),
                                 rp_id=where[0], backed_up=bool(made.credential_backed_up),
                                 nickname=passkeys.default_nickname(request.user_agent.string, names),
                                 created_at=utcnow(), last_used_at=utcnow()))
                sess.flush()
        except (_Gone, sa.exc.IntegrityError):
            return _json_error("gone", 410)
        sign_in(person)
        return jsonify({"ok": True, "go": url_for("social.you")})

    # -- you ----------------------------------------------------------------------

    @bp.get("/you")
    @_rests()
    def you():
        """You: your name and handle, your passkeys, signing out, deleting."""
        person, away = me_or_signin()
        if away:
            return away
        sess = site().session()
        keys = sess.execute(sa.select(Passkey).where(Passkey.person_id == person.id)
                            .order_by(Passkey.created_at, Passkey.id)).scalars().all()
        note = request.args.get("note")
        from .safety import blocked_people
        return _page("you.html", here="you", me=person, keys=keys, token=csrf_token(),
                     blocked=blocked_people(person),
                     note=note if note in ("added", "renamed", "removed", "last", "name",
                                           "unblocked", "limited") else None)

    @bp.post("/you/passkeys/options")
    @_rests(json_answer=True)
    def passkey_add_options():
        """The challenge for another passkey on your account (JSON)."""
        if not origin_ok() or not token_ok():
            return _json_error("stale", 403)
        person = current_person()
        if person is None:
            return _json_error("signed_out", 401)
        if over("passkey-add", "person|" + person.public_id):
            return _json_error("limited", 429)
        where, err = _rp_or_error()
        if err:
            return err
        sess = site().session()
        me = sess.get(Person, person.id)
        have = [k.credential_id for k in sess.execute(
            sa.select(Passkey).where(Passkey.person_id == person.id)).scalars()]
        challenge = passkeys.begin("add", person_id=person.id)
        return jsonify({"options": passkeys.registration_options(
            challenge, rp_id=where[0], user_handle=me.user_handle, handle=me.handle,
            display_name=me.display_name, exclude=have)})

    @bp.post("/you/passkeys/verify")
    @_rests(json_answer=True)
    def passkey_add_verify():
        """The new passkey: checked and added to your account (JSON)."""
        if not origin_ok() or not token_ok():
            return _json_error("stale", 403)
        person = current_person()
        if person is None:
            return _json_error("signed_out", 401)
        where, err = _rp_or_error()
        if err:
            return err
        row = passkeys.take("add")
        if row is None or row.person_id != person.id:
            return _json_error("expired", 400)
        credential = _body().get("credential")
        try:
            made = passkeys.verify_registration(credential, row.challenge, rp_id=where[0], origin=where[1])
        except passkeys.Refused as no:
            return _json_error(no.key, 400)
        sess = site().session()
        names = [k.nickname for k in sess.execute(sa.select(Passkey).where(Passkey.person_id == person.id)).scalars()]
        try:
            with sess.begin_nested():
                sess.add(Passkey(public_id=new_public_id(), person_id=person.id,
                                 credential_id=made.credential_id, public_key=made.credential_public_key,
                                 sign_count=made.sign_count, transports=passkeys.transports_of(credential),
                                 rp_id=where[0], backed_up=bool(made.credential_backed_up),
                                 nickname=passkeys.default_nickname(request.user_agent.string, names),
                                 created_at=utcnow()))
                sess.flush()
        except sa.exc.IntegrityError:
            return _json_error("already", 409)
        return jsonify({"ok": True, "go": url_for("social.you", note="added")})

    def _my_key(person, key_id):
        sess = site().session()
        key = sess.execute(sa.select(Passkey).where(Passkey.public_id == key_id,
                                                    Passkey.person_id == person.id)).scalar_one_or_none()
        if key is None:
            abort(404)
        return sess, key

    @bp.post("/you/passkeys/<key_id>/rename")
    @_rests()
    def passkey_rename(key_id):
        """Give one of your passkeys a name you will know it by."""
        if not origin_ok() or not token_ok():
            return _refused_page()
        person, away = me_or_signin()
        if away:
            return away
        sess, key = _my_key(person, key_id)
        name, err = check_name(request.form.get("nickname"))
        if err:
            return redirect(url_for("social.you", note="name"), 303)
        key.nickname = name
        return redirect(url_for("social.you", note="renamed"), 303)

    @bp.post("/you/passkeys/<key_id>/remove")
    @_rests()
    def passkey_remove(key_id):
        """Remove one of your passkeys, never the last: an account with none
        could not be signed in to."""
        if not origin_ok() or not token_ok():
            return _refused_page()
        person, away = me_or_signin()
        if away:
            return away
        sess, key = _my_key(person, key_id)
        # The person's row locked first (PostgreSQL; SQLite has one writer
        # anyway), so two removals at once cannot each see the other's key
        # and leave the account with none.
        sess.execute(sa.select(Person.id).where(Person.id == person.id).with_for_update())
        count = sess.execute(sa.select(sa.func.count()).select_from(Passkey)
                             .where(Passkey.person_id == person.id)).scalar()
        if count <= 1:
            return redirect(url_for("social.you", note="last"), 303)
        sess.delete(key)
        sess.flush()
        return redirect(url_for("social.you", note="removed"), 303)

    @bp.get("/you/delete")
    @_rests()
    def delete_account():
        """Delete your account: what goes and what stays, said first."""
        person, away = me_or_signin()
        if away:
            return away
        sess = site().session()
        n_keys = sess.execute(sa.select(sa.func.count()).select_from(Passkey)
                              .where(Passkey.person_id == person.id)).scalar()
        n_links = sess.execute(sa.select(sa.func.count()).select_from(Invite)
                               .where(Invite.created_by_id == person.id, Invite.used_at.is_(None))).scalar()
        n_posts = sess.execute(sa.select(sa.func.count()).select_from(Post)
                               .where(Post.person_id == person.id)).scalar()
        return _page("delete.html", here="you", me=person, n_keys=n_keys, n_links=n_links,
                     n_posts=n_posts, token=csrf_token(), wrong=False)

    @bp.post("/you/delete")
    @_rests()
    def delete_account_now():
        """Delete it, for real, once the handle is typed to say so."""
        if not origin_ok() or not token_ok():
            return _refused_page()
        person, away = me_or_signin()
        if away:
            return away
        typed = (request.form.get("confirm") or "").strip()
        if typed.startswith("@"):
            typed = typed[1:]
        if not hmac.compare_digest(typed.lower().encode(), person.handle.lower().encode()):
            sess = site().session()
            n_keys = sess.execute(sa.select(sa.func.count()).select_from(Passkey)
                                  .where(Passkey.person_id == person.id)).scalar()
            n_links = sess.execute(sa.select(sa.func.count()).select_from(Invite)
                                   .where(Invite.created_by_id == person.id, Invite.used_at.is_(None))).scalar()
            n_posts = sess.execute(sa.select(sa.func.count()).select_from(Post)
                                   .where(Post.person_id == person.id)).scalar()
            return _page("delete.html", 400, here="you", me=person, n_keys=n_keys, n_links=n_links,
                         n_posts=n_posts, token=csrf_token(), wrong=True)
        delete_person(site().session(), person.id)
        sign_out()
        return _page("deleted.html", here="deleted", hide_nav=True)

    # -- invites: admins only -------------------------------------------------------

    def _admin():
        """The signed-in admin, or the same 404 any missing page gives: the
        same words and the same headers (the site's own are held back from
        it), so the page cannot be told from one that is not there."""
        person = current_person()
        if person is None or not person.is_admin:
            g.social_hidden = True
            abort(404)
        return person

    def _invites_page(person, status=200, made=None, made_kind=None, made_for=None, unknown=None):
        sess = site().session()
        now = utcnow()
        # Links nobody used before they ran out are deleted as the list is read.
        sess.execute(sa.delete(Invite).where(Invite.used_at.is_(None), Invite.expires_at <= now)
                     .execution_options(synchronize_session=False))
        rows = sess.execute(sa.select(Invite, Person.handle)
                            .outerjoin(Person, Person.id == Invite.for_person_id)
                            .where(Invite.used_at.is_(None))
                            .order_by(Invite.created_at.desc(), Invite.id.desc()).limit(100)).all()
        return _page("invites.html", status, here="invites", me=person, waiting=rows, made=made,
                     made_kind=made_kind, made_for=made_for, unknown=unknown, token=csrf_token())

    @bp.get("/invites")
    @_rests()
    def invites():
        """Invites (admins only): make a link, see the unused ones, revoke."""
        person = _admin()
        return _invites_page(person)

    @bp.post("/invites")
    @_rests()
    def invites_make():
        """Make a join link: works once, for 14 days."""
        person = _admin()
        if not origin_ok() or not token_ok():
            return _refused_page()
        if over("invite-make", "person|" + person.public_id):
            return _limited_page()
        code, _inv = make_invite(site().session(), "join", created_by_id=person.id)
        return _invites_page(person, made=link_for(code, "join"), made_kind="join")

    @bp.post("/invites/recover")
    @_rests()
    def invites_recover():
        """Make a recovery link for a named person: works once, for an hour,
        and adds a passkey to their account."""
        person = _admin()
        if not origin_ok() or not token_ok():
            return _refused_page()
        if over("invite-make", "person|" + person.public_id):
            return _limited_page()
        handle, err = check_handle(request.form.get("handle"))
        sess = site().session()
        who = None if err else sess.execute(sa.select(Person).where(Person.handle_key == handle.lower())
                                            ).scalar_one_or_none()
        if who is None:
            shown = (request.form.get("handle") or "").strip().lstrip("@")[:20]
            return _invites_page(person, status=404, unknown=shown or "?")
        code, _inv = make_invite(sess, "recover", created_by_id=person.id, for_person_id=who.id)
        return _invites_page(person, made=link_for(code, "recover"), made_kind="recover", made_for=who.handle)

    @bp.post("/invites/<invite_id>/revoke")
    @_rests()
    def invites_revoke(invite_id):
        """Revoke an unused link: it stops working, and its row goes."""
        person = _admin()
        if not origin_ok() or not token_ok():
            return _refused_page()
        sess = site().session()
        inv = sess.execute(sa.select(Invite).where(Invite.public_id == invite_id,
                                                   Invite.used_at.is_(None))).scalar_one_or_none()
        if inv is not None:
            sess.execute(sa.delete(Challenge).where(Challenge.invite_id == inv.id))
            sess.delete(inv)
            sess.flush()
        return redirect(url_for("social.invites"), 303)

    return bp


class _Gone(Exception):
    """The invite was spent by somebody else a moment ago."""
