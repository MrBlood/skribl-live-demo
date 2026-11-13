"""Who is signed in to the site, and what a request must show to change anything.

THE SITE'S OWN COOKIE, `social_session`: signed (itsdangerous, under a key
derived from the app's SECRET_KEY for the site alone), HttpOnly, SameSite=Lax,
Secure wherever the page arrived over HTTPS, path /, so Skribl's own requests
(the Pad posting) carry it too. It holds three things:

    s   the browser's session id: random, made again at every sign-in, so a
        cookie planted before sign-in is never the one signed in (fixation)
    p   the person's public id, once signed in
    g   the person's sign-in generation when it was made

EVERY REQUEST CHECKS THE GENERATION against the person's row: "Sign out
everywhere" adds one to it, and every cookie made before is then nobody's.
The web servers remember nothing between requests (docs/SOCIAL-SITE.md,
section 3, rule 7): all of it is the cookie and the row.

THE ROW IS READ ON A CONNECTION OF ITS OWN, closed straight away, never through
the request's session: on SQLite an open read holds the file's read lock until
the request commits, and a limiter writing on its own connection later in the
same request (the site's here, or Skribl's when the Pad posts as this person)
would then wait on it. A read that fails (the site's tables not built yet)
signs nobody in and says so once in the log: Skribl's requests never fail
because the site cannot read its own tables.

A STATE-CHANGING REQUEST to the site shows two things (guard()):

    its Origin is the site's own (and where a browser sends no Origin, its
        Sec-Fetch-Site is same-origin), and
    a token bound to this browser's session id: HMAC(key, sid), in the
        X-Social-CSRF header (the passkey ceremonies) or a form's `csrf`.

Another site can make a browser send the cookie; it can neither read the
token nor send our Origin. Every comparison of a secret is constant time.

THE LIMITS (over()) count tries in social_rate_events, keyed by a keyed hash
of who tried (an address, an invite, a person), on a connection of their own
that commits at once: a try that fails still counts, and nothing here commits
the request's own work. Shared by every worker, through the database.
"""
import base64
import hashlib
import hmac
import ipaddress
import os
import secrets
import threading
from datetime import timedelta

import sqlalchemy as sa
import sqlalchemy.orm  # noqa: F401  (sa.orm.scoped_session)
from flask import abort, current_app, g, has_request_context, request
from itsdangerous import BadSignature, URLSafeTimedSerializer

from .models import Person, RateEvent, utcnow

COOKIE = "social_session"
#: How long a sign-in lasts. A passkey makes signing in again one tap.
SIGNED_IN_FOR = 30 * 24 * 3600
#: How long a browser's session id lasts before anybody signs in on it.
SIGNED_OUT_FOR = 24 * 3600
CSRF_HEADER = "X-Social-CSRF"
CSRF_FIELD = "csrf"


class Site:
    """The site's state on one app: app.extensions['social']."""

    def __init__(self, app, session, url_prefix):
        secret = app.config.get("SECRET_KEY") or app.secret_key
        if not secret:
            raise RuntimeError("the site's sign-in needs the app's SECRET_KEY: it signs the "
                               "site's cookie and its CSRF tokens")
        if isinstance(secret, str):
            secret = secret.encode()
        # A key of the site's own, so nothing it signs can be read as
        # something Flask's session or Skribl signed, and the other way about.
        self.key = hmac.new(secret, b"skribl site: sessions, tokens and limits", hashlib.sha256).digest()
        self.serializer = URLSafeTimedSerializer(self.key, salt="social-session")
        self.session = session
        self.url_prefix = url_prefix.rstrip("/")
        self.first_invite = None
        first = (os.environ.get("SKRIBL_SOCIAL_FIRST_INVITE") or "").strip()
        if first and len(first) < 16:
            app.logger.warning("SKRIBL_SOCIAL_FIRST_INVITE (the first person's invite code, "
                               "not a passkey) is shorter than 16 characters, so it lets nobody in. Use a long random one: python3 -c \"import "
                               "secrets; print(secrets.token_urlsafe(24))\"")
        elif first:
            self.first_invite = first
        self._said = set()
        self._said_lock = threading.Lock()

    def engine(self):
        return self.session().get_bind()

    def say_once(self, what, message, *args):
        """A log line said once per process, for a state that would
        otherwise be said on every request."""
        with self._said_lock:
            if what in self._said:
                return
            self._said.add(what)
        current_app.logger.warning(message, *args)


def site():
    return current_app.extensions["social"]


# ---- where the request came from ------------------------------------------

def _trusted_proxies():
    """How many proxies stand in front of the app: the deployment's own
    SKRIBL_TRUSTED_PROXIES (1 on Render), as the app's config or the
    environment says, the setting Skribl's own limits read."""
    val = current_app.config.get("SKRIBL_TRUSTED_PROXIES")
    if val is None:
        val = os.environ.get("SKRIBL_TRUSTED_PROXIES", "0")
    try:
        return max(0, int(val))
    except (TypeError, ValueError):
        return 0


def client_subject():
    """Who a limit counts: the connecting address, or the one the trusted
    proxy saw (that many hops from the right of X-Forwarded-For; anything
    further left is the client's own say). An IPv6 address counts by its /64,
    which one subscriber holds whole."""
    addr = request.remote_addr or "unknown"
    trusted = _trusted_proxies()
    if trusted:
        parts = [p.strip() for p in request.headers.get("X-Forwarded-For", "").split(",") if p.strip()]
        if len(parts) >= trusted:
            addr = parts[-trusted]
    try:
        ip = ipaddress.ip_address(addr)
    except ValueError:
        return "unknown"
    if ip.version == 6:
        if ip.ipv4_mapped:
            return str(ip.ipv4_mapped)
        return str(ipaddress.ip_network(f"{ip}/64", strict=False))
    return str(ip)


def is_https():
    """Whether the page reached the browser over HTTPS: the request itself,
    or the proxy in front of it saying so (Render answers HTTPS and forwards
    plain HTTP with X-Forwarded-Proto). Believing a client that claims HTTPS
    costs nothing: its own cookie gets Secure, and a passkey ceremony then
    expects an https origin, which a browser on plain http never signs."""
    if request.is_secure:
        return True
    proto = request.headers.get("X-Forwarded-Proto", "").split(",")[0].strip().lower()
    if proto == "https":
        return True
    return (os.environ.get("SKRIBL_FORCE_SECURE_COOKIES") or "").strip().lower() in ("1", "true", "yes", "on")


def public_origin():
    """The origin the browser is on: scheme and host, as the request says
    (no host is written into the site: passkeys made on the demo's address
    are made again after the move to a domain)."""
    return ("https" if is_https() else request.scheme) + "://" + request.host


# ---- the cookie -----------------------------------------------------------

def _b64(raw):
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def read_cookie():
    """The cookie's contents if it is ours and not too old, else None."""
    raw = request.cookies.get(COOKIE)
    if not raw or len(raw) > 1024:
        return None
    try:
        data = site().serializer.loads(raw, max_age=SIGNED_IN_FOR)
    except BadSignature:
        return None
    if not isinstance(data, dict) or not isinstance(data.get("s"), str):
        return None
    return data


def _write_cookie(data, max_age):
    g.social_cookie = (site().serializer.dumps(data), max_age)


def finish_cookie(response):
    """App-wide after_request: write or clear the site's cookie, as the
    request decided. Cheap on every other response (one look at g)."""
    if not has_request_context():
        return response
    want = g.pop("social_cookie", None)
    if want is not None:
        value, max_age = want
        if value is None:
            response.delete_cookie(COOKIE, path="/", secure=is_https(), httponly=True, samesite="Lax")
        else:
            response.set_cookie(COOKIE, value, max_age=max_age, path="/", secure=is_https(),
                                httponly=True, samesite="Lax")
        # A response that sets somebody's cookie is theirs alone.
        response.headers["Cache-Control"] = "no-store"
    return response


def browser_sid():
    """This browser's session id, made (and its cookie set) if it has none.
    What this request has already decided the cookie will hold wins over
    what the browser sent."""
    data = g.get("social_fresh") or read_cookie()
    if data:
        return data["s"]
    data = {"s": _b64(secrets.token_bytes(16))}
    g.social_fresh = data
    _write_cookie(data, SIGNED_OUT_FOR)
    return data["s"]


def _signed_out_here(data):
    """The cookie keeps this browser's session id and loses the person: their
    sign-in ended elsewhere (signed out everywhere, or the account is gone).
    The id stays, so a form this page renders still matches its token."""
    keep = {"s": data["s"]}
    g.social_fresh = keep
    _write_cookie(keep, SIGNED_OUT_FOR)


def sid_hash(sid):
    return hashlib.sha256(("sid|" + sid).encode()).hexdigest()


def sign_in(person):
    """A new session id and the person's generation, in a new cookie: what
    the browser held before (a planted cookie included) is not carried on."""
    data = {"s": _b64(secrets.token_bytes(16)), "p": person.public_id, "g": int(person.session_gen)}
    g.social_fresh = data
    g.social_person = _Snapshot(person.id, person.public_id, person.handle, person.display_name,
                                bool(person.is_admin), int(person.session_gen),
                                person.face_id, person.face_w, person.face_h, person.activity_seen_at)
    _write_cookie(data, SIGNED_IN_FOR)
    return data["s"]


def sign_out():
    """The cookie goes. (A copy taken before is still good until "Sign out
    everywhere", as with any signed cookie: that button is the answer.)"""
    g.social_fresh = None
    g.social_person = None
    g.social_cookie = (None, 0)


# ---- who is signed in -----------------------------------------------------

class _Snapshot:
    """What a request needs to know of the signed-in person, read once: who
    they are, their drawn face for the bar's You (piece 3), and when they last
    looked at Activity, for the bell's dot (notifications)."""
    __slots__ = ("id", "public_id", "handle", "display_name", "is_admin", "session_gen",
                 "face_id", "face_w", "face_h", "activity_seen_at")

    def __init__(self, id, public_id, handle, display_name, is_admin, session_gen,
                 face_id=None, face_w=None, face_h=None, activity_seen_at=None):
        self.id, self.public_id, self.handle = id, public_id, handle
        self.display_name, self.is_admin, self.session_gen = display_name, is_admin, session_gen
        self.face_id, self.face_w, self.face_h = face_id, face_w, face_h
        self.activity_seen_at = activity_seen_at


def read_aside(stmt):
    """The rows of one read a request makes beside its own work (who is
    signed in, whose drawing this is), without ever deadlocking SQLite.

    ON A CONNECTION OF ITS OWN, closed at once, while the request's session
    has not begun: a read there would begin the request's transaction and
    hold SQLite's read lock to its end, and a limit's commit (over(), on
    connections of its own) would wait on it.

    ON THE REQUEST'S OWN SESSION once that has begun (main's run after #864:
    verify_socialposts section 9, one run in three side by side here).
    Skribl's SQLite recipe begins every transaction at its first read, so a
    request that has read anything holds the read lock to its end. A second
    connection's read then queues behind any writer waiting to commit, and
    that writer waits for this request's lock: each waits on the other until
    the 5 s busy timeout, the read fails ("database is locked"), and a person
    signed in looked signed out for a page. Through the session, the read
    shares the lock the request already holds."""
    s = site()
    sess = s.session()
    # A host's scoped session (Flask-SQLAlchemy's db.session) is asked for
    # the session it stands for: only that one knows if it has begun.
    real = sess() if isinstance(sess, sa.orm.scoped_session) else sess
    if real.in_transaction():
        return real.execute(stmt).all()
    with s.engine().connect() as conn:
        return conn.execute(stmt).all()


def read_person_row(public_id):
    """The person's row (read_aside), or None."""
    t = Person.__table__
    rows = read_aside(sa.select(t.c.id, t.c.public_id, t.c.handle, t.c.display_name,
                                t.c.is_admin, t.c.session_gen, t.c.face_id, t.c.face_w,
                                t.c.face_h, t.c.activity_seen_at)
                      .where(t.c.public_id == public_id))
    return rows[0] if rows else None


def current_person():
    """The signed-in person for this request, or None. Read once a request.
    A cookie whose generation is not the person's (signed out everywhere),
    or whose person is gone, is cleared on the way out."""
    if not has_request_context() or "social" not in current_app.extensions:
        return None
    if "social_person" in g:
        return g.social_person
    person = None
    data = read_cookie()
    if data and isinstance(data.get("p"), str):
        try:
            row = read_person_row(data["p"])
        except sa.exc.SQLAlchemyError:
            row = False
            site().say_once("unread", "the site could not read its people (social_people): nobody is "
                                      "signed in to the site until it can. Are its tables built? "
                                      "python -m alembic -c social/alembic.ini upgrade head")
        if row:
            if row.session_gen == data.get("g"):
                person = _Snapshot(row.id, row.public_id, row.handle, row.display_name,
                                   bool(row.is_admin), int(row.session_gen),
                                   row.face_id, row.face_w, row.face_h, row.activity_seen_at)
            else:
                _signed_out_here(data)               # signed out everywhere since
        elif row is None:
            _signed_out_here(data)                   # the person is gone
    g.social_person = person
    return person


def current_user_id():
    """The signed-in person's public id, for Skribl (current_user_id), or None."""
    person = current_person()
    return person.public_id if person else None


# ---- what a state-changing request must show ------------------------------

def csrf_token():
    """The token this browser's forms and ceremonies send back."""
    return _b64(hmac.new(site().key, ("csrf|" + browser_sid()).encode(), hashlib.sha256).digest())


def origin_ok():
    """The request came from the site's own pages: its Origin is ours, or,
    where a browser sends none, its Sec-Fetch-Site says same-origin."""
    origin = request.headers.get("Origin")
    if origin is not None:
        return hmac.compare_digest(origin.encode(), public_origin().encode())
    fetch_site = request.headers.get("Sec-Fetch-Site")
    return fetch_site in (None, "same-origin", "none")


def token_ok():
    data = read_cookie()
    sent = request.headers.get(CSRF_HEADER) or request.form.get(CSRF_FIELD) or ""
    if not data or not sent:
        return False
    want = _b64(hmac.new(site().key, ("csrf|" + data["s"]).encode(), hashlib.sha256).digest())
    return hmac.compare_digest(sent.encode(), want.encode())


def guard():
    """Refuse (403) a state-changing request that did not come from the
    site's own page in this browser."""
    if not origin_ok() or not token_ok():
        abort(403)


# ---- the limits -----------------------------------------------------------

#: (most tries, in seconds) for each thing that can be tried too often.
LIMITS = {
    "signin": (30, 3600),          # passkey sign-ins begun, per address
    "join": (20, 3600),            # joins begun, per address
    "recover": (20, 3600),         # recovery ceremonies begun, per address
    "link-look": (60, 3600),       # invite and recovery links opened, per address
    "invite-use": (12, 3600),      # tries on one invite or recovery link
    "passkey-add": (20, 3600),     # passkeys added, per person
    "invite-make": (60, 86400),    # links made, per admin
    "profile-edit": (60, 3600),    # name and bio saved, per person (piece 3)
    "face": (20, 3600),            # faces drawn and kept, per person (piece 3): each one is a skribl
    "post": (40, 3600),            # posts made, per person (piece 4): each one is a skribl
    "report": (30, 3600),          # reports sent, per person, or per address signed out (piece 5)
    "block": (60, 3600),           # blocks and unblocks, per person (piece 5)
    "comment": (60, 3600),         # comments and answers sent, per person (phase 2)
    "like": (120, 3600),           # likes and unlikes, per person (phase 2: the same tap does both)
    "follow": (60, 3600),          # follows and unfollows, per person (follows): nobody follows everyone at once
    "mute": (60, 3600),            # mutes and unmutes, per person (mutes): as follows, nobody mutes and unmutes hundreds a minute
    "home-pick": (120, 3600),      # Home's pill, Following or Everyone, kept for the account (follows)
}
_SWEEP_EVERY = 64


def over(bucket, subject):
    """Count one try at `bucket` by `subject`, and say whether it is past the
    limit (a refused try is not counted). Call it before the request reads
    anything through its own session: on SQLite a read held open there would
    keep this commit waiting.

    WRITTEN FIRST, THEN COUNTED (after v330; the review of piece 2 found it).
    It used to count and then write, so two tries at the same instant could
    each count one under the limit and both be let through. Now each try is
    written and committed, then counted with every try already committed: the
    try counted last sees every try let through before it, so no more than
    the limit are ever let through, on SQLite and on PostgreSQL alike, with no
    lock of either's. A try past the limit takes its own row back out. Tries
    at the very same instant at the limit's edge may both be refused, never
    both let through."""
    cap, window = LIMITS[bucket]
    s = site()
    key = hmac.new(s.key, f"rate|{bucket}|{subject}".encode(), hashlib.sha256).hexdigest()
    t = RateEvent.__table__
    now = utcnow()
    # ONE STATEMENT A TRANSACTION. A transaction that reads and then writes
    # asks SQLite to raise its lock mid-way, and two such at once can each wait
    # on the other: SQLite then fails one at once ("database is locked"), with
    # its try written and never taken back. Written, counted and taken back
    # each on its own, nothing waits on anything it holds.
    with s.engine().begin() as conn:
        mine = conn.execute(t.insert().values(bucket=bucket, key_hash=key, created_at=now)).inserted_primary_key[0]
    with s.engine().connect() as conn:
        n = conn.execute(sa.select(sa.func.count()).select_from(t)
                         .where(t.c.bucket == bucket, t.c.key_hash == key,
                                t.c.created_at >= now - timedelta(seconds=window))).scalar()
    if n > cap:
        with s.engine().begin() as conn:
            conn.execute(t.delete().where(t.c.id == mine))
        return True
    # Rows past the longest window are swept now and then, a bounded batch at
    # a time, so the table does not grow for ever.
    if secrets.randbelow(_SWEEP_EVERY) == 0:
        with s.engine().begin() as conn:
            old = sa.select(t.c.id).where(t.c.created_at < now - timedelta(days=2)).limit(500)
            conn.execute(t.delete().where(t.c.id.in_(old.scalar_subquery())))
    return False
