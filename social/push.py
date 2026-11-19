"""Push notifications, called nudges on the site (the owner's "All yes" to
Blooby's Nudges, Nov 18; docs/SOCIAL-SITE.md, "Built: push notifications").
The alerts a phone or a computer shows when Blooby isn't open.

    /sw.js              the service worker (push-sw.js): shows a nudge, puts
                        the number on the icon, opens what a tap is for
    /push/subscribe     this device may be nudged (Activity's card, Settings)
    /push/state         what this device is nudged for, if anything
    /push/prefs         one of its switches
    /push/test          a nudge to this device now (Settings' Send me a test
                        nudge), and what its push service answered
    /push/unsubscribe   this device, no longer

THE DOT'S RULE (A). What buzzes is what lights the bell's dot: a reply to
you, something said on your post, a mention. Likes, follows, reposts and
quotes wait in Activity, unless a device's own switch says otherwise
(models.PUSH_DEFAULTS; Settings has a switch a kind).

A NUDGE IS ACTIVITY'S ROW, WORD FOR WORD. When something happens to
somebody, their Activity is read as their page would read it, and the newest
new row of that kind is what the nudge says (activity.sentence: "Ana replied
to your comment", "Mira and 2 others said something on your post"), with its
words under it, or a drawn reply's "Tap to watch it draw.", and a tap opens
the row's own link. So whatever Activity leaves out (a block either way, a
takedown, somebody you muted, a comment deleted meanwhile) never buzzes
either: no row, no nudge. A row that gathers several (three comments on one
post) keeps one tag, so the phone puts the newest in place of the last
rather than stacking three, and one Topic, so a phone that was off is handed
the newest only. A device is never told about a row older than the newest it
was told about (told_up_to), so something that makes no row of its own (a
muted person's comment) cannot buzz an older one again.

AFTER THE COMMIT, NEVER BEFORE (note()). The host commits a request's work
once, at its end. Who should hear about it is written on the session as the
work is done, and only a commit that went through sends anything, from a
small pool of threads of its own, so a reply never waits on Apple or Google,
and a request that failed tells nobody.

WHERE A NUDGE MAY GO (endpoint_ok): only to the push services browsers use
(Apple's, Google's, Mozilla's, Microsoft's), over https, never following a
redirect. A browser hands over its push service's address; anything else
handed over is refused, so nobody can make the site send to an address of
their choosing.

IT LIVES WITH THE SIGN-IN (models.PushSubscription). Signing out here takes
this browser's nudges with it, Sign out everywhere takes them all, and a
device somebody else signs in on stops being nudged for the one before
(/push/state, which push.js asks once each new sign-in).

SEALED FOR THE DEVICE ALONE (RFC 8291's aes128gcm) and SIGNED AS THE SITE
(VAPID, RFC 8292), with the cryptography package passkeys already brought:
nothing new to install. The signing key is the deployment's own
SOCIAL_VAPID_KEY if it sets one, else made from its SECRET_KEY, the same
every time for the same secret: nothing new to keep or set. Push services
charge nothing.

Pad and Flip don't change: nudges are the site's.
"""
import base64
import concurrent.futures
import hashlib
import hmac
import json
import os
import struct
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import timedelta
from pathlib import Path

import sqlalchemy as sa
import sqlalchemy.orm  # noqa: F401  (sa.orm.Session, for the commit's event)
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from flask import current_app, jsonify, request, url_for

from .accounts import _json_error, _rests
from .models import PUSH_DEFAULTS, PUSH_KINDS, Person, PushSubscription, as_utc, utcnow
from .security import current_person, origin_ok, over, public_origin, read_cookie, site, token_ok

#: The switch each of Activity's rows is under (models.PUSH_KINDS).
SWITCH_OF = {"comment": "replies", "answer": "replies", "answer_drawing": "replies", "drawing": "replies",
             "mention": "mentions", "like": "likes", "like_comment": "likes", "follow": "follows",
             "repost": "reposts", "repost_comment": "reposts", "quote": "reposts", "quote_comment": "reposts"}
SWITCHES = ("replies", "mentions", "likes", "follows", "reposts")

#: The push services browsers use: a nudge goes to one of these, or nowhere.
PUSH_HOSTS = ("push.apple.com", "fcm.googleapis.com", "android.googleapis.com",
              "push.services.mozilla.com", "notify.windows.com")

#: A person's devices at most; the oldest goes when another comes.
DEVICES_MAX = 10
#: A nudge's words at most: Activity shows two lines; a lock screen, fewer.
WORDS_MAX = 160
#: How long a push service holds a nudge for a phone that is off: a day.
TTL = 86400
#: A row as new as the event that asked for it: the request's few moments.
FRESH = timedelta(seconds=30)
#: What a test nudge says (Settings' Send me a test nudge; the owner's yes, Nov 18).
TEST_TITLE = "Hello from Blooby"
#: Its words name the device as push.js does (the owner, Nov 18, after the
#: first one on their iPhone: "it doesn't show in activity"): a tap opens
#: Settings, where it was sent from, never Activity, which has nothing of it.
TEST_BODY = "Nudges work on this {device}."
TEST_BODY_ANY = "Nudges work here."
TEST_DEVICES = ("phone", "tablet", "computer")

_HERE = Path(__file__).resolve().parent
_P256_ORDER = 0xFFFFFFFF00000000FFFFFFFFFFFFFFFFBCE6FAADA7179E84F3B9CAC2FC632551
_keys = {}
_lock = threading.Lock()
_pool = None
_listening = False
_skribl_blueprint = "skribl"


def _b64(raw):
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _unb64(text):
    text = (text or "").strip()
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


# ---- the site's signing key (VAPID) -------------------------------------------

def vapid_key(app=None):
    """The site's signing key for nudges: SOCIAL_VAPID_KEY (a PEM, or 32
    bytes in base64url) when the deployment sets one; else made from its
    SECRET_KEY, the same for the same secret. A new SECRET_KEY is a new key:
    the push services refuse the devices made under the old one (404 or 410,
    and they go), and push.js makes this device again where it finds the key
    changed."""
    app = app or current_app._get_current_object()
    raw = (app.config.get("SOCIAL_VAPID_KEY") or os.environ.get("SOCIAL_VAPID_KEY") or "").strip()
    secret = app.config.get("SECRET_KEY") or app.secret_key or ""
    secret = secret.encode() if isinstance(secret, str) else secret
    which = hashlib.sha256(raw.encode() if raw else b"secret|" + secret).hexdigest()
    with _lock:
        key = _keys.get(which)
        if key is None:
            if raw.startswith("-----BEGIN"):
                key = serialization.load_pem_private_key(raw.encode(), password=None)
            else:
                seed = _unb64(raw) if raw else HKDF(hashes.SHA256(), 32, salt=b"blooby push",
                                                    info=b"vapid p-256 v1").derive(secret)
                key = ec.derive_private_key(int.from_bytes(seed, "big") % (_P256_ORDER - 1) + 1, ec.SECP256R1())
            _keys[which] = key
    return key


def public_key(app=None):
    """The key a browser subscribes with (applicationServerKey), base64url."""
    return _b64(vapid_key(app).public_key().public_bytes(serialization.Encoding.X962,
                                                         serialization.PublicFormat.UncompressedPoint))


def vapid_header(endpoint, subject):
    """The Authorization header that says the site sent it (RFC 8292): a
    JWT for the push service's origin, good for twelve hours, signed ES256."""
    parts = urllib.parse.urlsplit(endpoint)
    head = _b64(json.dumps({"typ": "JWT", "alg": "ES256"}, separators=(",", ":")).encode())
    claims = _b64(json.dumps({"aud": f"{parts.scheme}://{parts.netloc}", "exp": int(time.time()) + 12 * 3600,
                              "sub": subject}, separators=(",", ":")).encode())
    der = vapid_key().sign(f"{head}.{claims}".encode(), ec.ECDSA(hashes.SHA256()))
    r, s = decode_dss_signature(der)
    return f"vapid t={head}.{claims}.{_b64(r.to_bytes(32, 'big') + s.to_bytes(32, 'big'))}, k={public_key()}"


# ---- sealed for the device alone (RFC 8291, aes128gcm) --------------------------

def seal(p256dh, auth, plain):
    """`plain` sealed for the device whose keys these are: a key of our own
    for this nudge alone, a secret shared with the device's, and one
    aes128gcm record (RFC 8188) under it."""
    ua_public = _unb64(p256dh)
    secret = _unb64(auth)
    mine = ec.generate_private_key(ec.SECP256R1())
    as_public = mine.public_key().public_bytes(serialization.Encoding.X962,
                                               serialization.PublicFormat.UncompressedPoint)
    shared = mine.exchange(ec.ECDH(), ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), ua_public))
    ikm = HKDF(hashes.SHA256(), 32, salt=secret, info=b"WebPush: info\x00" + ua_public + as_public).derive(shared)
    salt = os.urandom(16)
    cek = HKDF(hashes.SHA256(), 16, salt=salt, info=b"Content-Encoding: aes128gcm\x00").derive(ikm)
    nonce = HKDF(hashes.SHA256(), 12, salt=salt, info=b"Content-Encoding: nonce\x00").derive(ikm)
    body = AESGCM(cek).encrypt(nonce, plain + b"\x02", None)
    return salt + struct.pack(">I", 4096) + bytes([len(as_public)]) + as_public + body


# ---- where a nudge may go --------------------------------------------------------

def _test_origin():
    """A harness's stand-in for a push service (verify_socialpush): an http
    origin on this machine, honoured only where the environment names it and
    never on a deployment (Render sets RENDER)."""
    origin = (os.environ.get("SOCIAL_PUSH_TEST_ORIGIN") or "").strip().rstrip("/")
    if not origin or os.environ.get("RENDER"):
        return None
    parts = urllib.parse.urlsplit(origin)
    return origin if parts.scheme == "http" and parts.hostname in ("127.0.0.1", "localhost") else None


def endpoint_ok(endpoint):
    """An address a nudge may be sent to: a push service's, over https."""
    if not isinstance(endpoint, str) or not endpoint or len(endpoint) > 1024:
        return False
    try:
        parts = urllib.parse.urlsplit(endpoint)
        port = parts.port
    except ValueError:
        return False
    if parts.username or parts.password or not parts.path.startswith("/"):
        return False
    test = _test_origin()
    if test and endpoint.startswith(test + "/"):
        return True
    host = (parts.hostname or "").lower()
    return (parts.scheme == "https" and port in (None, 443)
            and any(host == h or host.endswith("." + h) for h in PUSH_HOSTS))


def _key_ok(text, size):
    if not isinstance(text, str) or not text or len(text) > 200:
        return False
    try:
        raw = _unb64(text)
    except (ValueError, TypeError):
        return False
    return len(raw) == size and (size != 65 or raw[:1] == b"\x04")


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **kw):
        return None


def _reason(raw):
    """A push service's own word for a refusal, short: Apple's and Google's
    "reason" (BadJwtToken, ...), else the start of what it said."""
    text = raw.decode("utf-8", "replace") if isinstance(raw, bytes) else str(raw or "")
    try:
        got = json.loads(text)
        text = str(got.get("reason") or got.get("error") or got.get("message") or text) if isinstance(got, dict) else text
    except ValueError:
        pass
    text = " ".join("".join(ch for ch in text if ch.isprintable()).split())
    return text[:80]


def _send(endpoint, p256dh, auth, payload, topic, subject):
    """One nudge to one device: (its push service's answer, 201 when taken,
    or None when it could not be asked; the service's own word when it said
    no)."""
    data = seal(p256dh, auth, json.dumps(payload, separators=(",", ":")).encode())
    headers = {"TTL": str(TTL), "Content-Encoding": "aes128gcm", "Content-Type": "application/octet-stream",
               "Urgency": "normal", "Topic": topic, "Authorization": vapid_header(endpoint, subject)}
    handlers = [_NoRedirect]
    test = _test_origin()
    if test and endpoint.startswith(test + "/"):
        handlers.append(urllib.request.ProxyHandler({}))
    req = urllib.request.Request(endpoint, data=data, headers=headers, method="POST")
    try:
        with urllib.request.build_opener(*handlers).open(req, timeout=10) as resp:
            return resp.status, ""
    except urllib.error.HTTPError as exc:
        try:
            said = exc.read(1024)
        except OSError:
            said = b""
        return exc.code, _reason(said)
    except (urllib.error.URLError, OSError, ValueError) as exc:
        return None, _reason(getattr(exc, "reason", exc))


#: Whose push service an address is, for the words a test nudge says.
SERVICES = (("push.apple.com", "Apple"), ("fcm.googleapis.com", "Google"), ("android.googleapis.com", "Google"),
            ("push.services.mozilla.com", "Mozilla"), ("notify.windows.com", "Microsoft"))


def service_of(endpoint):
    """"Apple", "Google", "Mozilla" or "Microsoft", else "the push service"."""
    host = (urllib.parse.urlsplit(endpoint or "").hostname or "").lower()
    return next((name for h, name in SERVICES if host == h or host.endswith("." + h)), "the push service")


# ---- what a nudge says ------------------------------------------------------------

def body_of(row):
    """Under the sentence: a drawn reply's invitation, else their words in
    quotes as Activity shows them, cut short for a lock screen."""
    if row["kind"] in ("answer_drawing", "drawing"):
        return "Tap to watch it draw."
    words = " ".join((row.get("words") or "").split())
    if not words:
        return ""
    if len(words) > WORDS_MAX:
        words = words[:WORDS_MAX - 1].rstrip() + "…"
    return f"“{words}”"


def tag_of(row):
    """What a nudge takes the place of: the same kind on the same page (a
    post's comments, a conversation's answers, a post's likes); a mention, a
    quote and a drawing each their own."""
    one = row["kind"] in ("mention", "quote", "quote_comment", "answer_drawing", "drawing")
    return f"{row['kind']}:{row['href'] if one else row['href'].split('#', 1)[0]}"


def switches_of(row):
    """The switches a row is under: its kind's, and Mentions where it names
    you too (a quote of yours that mentions you)."""
    return {SWITCH_OF.get(row["kind"], "replies")} | ({"mentions"} if row.get("mentioned") else set())


def nudges_for(person, since, wanted):
    """For each switch in `wanted`, `person`'s newest new row under it in
    Activity, if it is as new as `since`: [(payload, switches, when)], the
    oldest first, so the newest shows on top."""
    from .activity import QUIET_KINDS, listing, sentence
    fresh, _ = listing(person, _skribl_blueprint)
    picked = []
    for want in SWITCHES:
        if want not in wanted:
            continue
        for row in fresh:                       # newest first
            if as_utc(row["when"]) < since - FRESH:
                break
            if want in switches_of(row):
                if all(row is not p for p in picked):
                    picked.append(row)
                break
    dot = sum(1 for r in fresh if r["kind"] not in QUIET_KINDS or r.get("mentioned"))
    out = []
    for row in sorted(picked, key=lambda r: as_utc(r["when"])):
        out.append(({"title": sentence(row), "body": body_of(row), "url": row["href"], "tag": tag_of(row),
                     "icon": url_for("social.static", filename="blooby-icon-192.png"), "badge": dot},
                    switches_of(row), as_utc(row["when"])))
    return out


# ---- after the commit, never before ----------------------------------------------

def note(person_id, actor_id, switch):
    """`person_id` may want a nudge under `switch` about what this request
    did, once its work is committed. Never the one who did it."""
    if not _listening or not person_id or person_id == actor_id or switch not in SWITCHES:
        return
    try:
        info = site().session().info
        info.setdefault("social_push", {}).setdefault(person_id, set()).add(switch)
        if "social_push_at" not in info:
            info["social_push_at"] = (current_app._get_current_object(), request.url_root,
                                      public_origin() + url_for("social.home"), utcnow())
    except Exception:            # noqa: BLE001 -- a nudge is never worth a failed request
        current_app.logger.debug("push: could not note %s", person_id, exc_info=True)


def _listen():
    global _listening
    with _lock:
        if _listening:
            return
        _listening = True

    @sa.event.listens_for(sa.orm.Session, "after_commit")
    def _committed(session):
        plan = session.info.pop("social_push", None)
        at = session.info.pop("social_push_at", None)
        if plan and at and not at[0].config.get("SOCIAL_PUSH_OFF"):
            _workers().submit(_work, at[0], at[1], at[2], plan, at[3])

    @sa.event.listens_for(sa.orm.Session, "after_soft_rollback")
    def _rolled_back(session, previous_transaction):
        # Only the request's own end: a savepoint undone (a like tapped twice
        # at once) leaves its other notes standing, and a note whose row did
        # not stand finds nothing to say (nudges_for reads what committed).
        if previous_transaction.nested or previous_transaction.parent is not None:
            return
        session.info.pop("social_push", None)
        session.info.pop("social_push_at", None)


def _workers():
    """Two threads for the whole process, made the first time a nudge is
    due (after gunicorn's fork, never before it)."""
    global _pool
    with _lock:
        if _pool is None:
            _pool = concurrent.futures.ThreadPoolExecutor(max_workers=2, thread_name_prefix="social-push")
        return _pool


def _work(app, base, subject, plan, since):
    """The nudges in `plan` ({person id: switches}), on a session of its own:
    read, then sent with no transaction open (on SQLite a read holds the
    file's lock, and a push service can take seconds), then written."""
    try:
        with app.test_request_context("/", base_url=base):
            sess = site().session()
            try:
                sends, gone = _due(sess, plan, since)
            finally:
                sess.rollback()
            told = []
            for sub_id, endpoint, p256dh, auth, payload, topic, when in sends:
                if sub_id in gone:
                    continue
                status, reason = _send(endpoint, p256dh, auth, payload, topic, subject)
                if status in (404, 410):       # the device is gone
                    gone.add(sub_id)
                elif status is not None and 200 <= status < 300:
                    told.append((sub_id, when))
                else:                          # said no, or could not be asked: in the log, never on a page
                    app.logger.warning("push: %s answered %s %s", service_of(endpoint), status, reason)
            if not (told or gone):
                return
            t = PushSubscription.__table__
            try:
                for sub_id, when in told:
                    sess.execute(t.update().where(t.c.id == sub_id, sa.or_(t.c.told_up_to.is_(None),
                                                                           t.c.told_up_to < when))
                                 .values(told_up_to=when))
                if gone:
                    sess.execute(t.delete().where(t.c.id.in_(sorted(gone))))
                sess.commit()
            finally:
                sess.rollback()
    except Exception:            # noqa: BLE001 -- best effort: a nudge missed is never a page broken
        app.logger.warning("push: nudges were not sent", exc_info=True)


def _due(sess, plan, since):
    """([(device id, endpoint, p256dh, auth, payload, topic, when)], {device
    ids gone}): what to send to whom. A device from before Sign out
    everywhere is gone; somebody taken down is told nothing."""
    devices = {}
    for sub in sess.execute(sa.select(PushSubscription)
                            .where(PushSubscription.person_id.in_(sorted(plan)))).scalars():
        devices.setdefault(sub.person_id, []).append(sub)
    sends, gone = [], set()
    for pid, subs in devices.items():
        person = sess.get(Person, pid)
        if person is None or person.taken_down_at is not None:
            continue
        gone |= {s.id for s in subs if s.gen != person.session_gen}
        live = [s for s in subs if s.gen == person.session_gen]
        if not live:
            continue
        for payload, switches, when in nudges_for(person, since, plan[pid]):
            topic = _b64(hashlib.sha256(payload["tag"].encode()).digest())[:32]
            for sub in live:
                if not any(getattr(sub, k) for k in switches):
                    continue
                if sub.told_up_to is not None and as_utc(sub.told_up_to) >= when:
                    continue
                sends.append((sub.id, sub.endpoint, sub.p256dh, sub.auth,
                              dict(payload, badge=payload["badge"] if sub.badge else None), topic, when))
    return sends, gone


# ---- devices ----------------------------------------------------------------------

def browser_mark():
    """Which browser's sign-in this is, as a keyed hash of its cookie's own
    random part: kept on a device so signing out there takes its nudges."""
    data = read_cookie() or {}
    return hmac.new(site().key, ("push|" + str(data.get("s", ""))).encode(), hashlib.sha256).hexdigest()


def page_mark():
    """What a signed-in page tells push.js about its sign-in: a new one asks
    /push/state once (the device follows it, or stops being somebody
    else's). Not the browser mark itself, nor anything of the person's."""
    return hmac.new(site().key, ("push-page|" + browser_mark()).encode(), hashlib.sha256).hexdigest()[:16]


def _prefs(sub):
    return {k: bool(getattr(sub, k)) for k in PUSH_KINDS}


def drop_person_pushes(person_id, sess=None):
    """Every device of an account's (accounts.delete_person; Sign out everywhere)."""
    (sess or site().session()).execute(sa.delete(PushSubscription).where(PushSubscription.person_id == person_id)
                                       .execution_options(synchronize_session=False))


def drop_browser_pushes(person_id):
    """The devices this browser's sign-in made (signing out here)."""
    site().session().execute(sa.delete(PushSubscription).where(PushSubscription.person_id == person_id,
                                                               PushSubscription.browser == browser_mark())
                             .execution_options(synchronize_session=False))


def _device(endpoint):
    if not isinstance(endpoint, str) or not endpoint or len(endpoint) > 1024:
        return None
    return site().session().execute(sa.select(PushSubscription)
                                    .where(PushSubscription.endpoint == endpoint)).scalar_one_or_none()


# ---- the routes -------------------------------------------------------------------

def register(bp, skribl_blueprint="skribl"):
    """Add the nudges' routes to the site's blueprint, and listen for commits."""
    global _skribl_blueprint
    _skribl_blueprint = skribl_blueprint
    _listen()
    worker = (_HERE / "static" / "push-sw.js").read_text(encoding="utf-8")

    @bp.get("/sw.js")
    def push_worker():
        """The service worker (push-sw.js), from the site's own folder, so
        its scope is the site's."""
        resp = current_app.response_class(worker, mimetype="text/javascript")
        resp.headers["Cache-Control"] = "no-cache"
        return resp

    def _asked():
        """(me, body, refusal): a JSON request from the site's own page, by
        somebody signed in, under the limit."""
        if not origin_ok() or not token_ok():
            return None, None, _json_error("stale", 403)
        me = current_person()
        if me is None:
            return None, None, _json_error("signed_out", 401)
        if over("push", "person|" + me.public_id):
            return None, None, _json_error("limited", 429)
        body = request.get_json(silent=True)
        return me, body if isinstance(body, dict) else {}, None

    @bp.post("/push/subscribe")
    @_rests(json_answer=True)
    def push_subscribe():
        """This device may be nudged: what the browser handed over, kept with
        this sign-in, starting at the dot's rule (the same person's device
        keeps its switches; somebody else's starts again)."""
        me, body, refused = _asked()
        if refused:
            return refused
        endpoint, keys = body.get("endpoint"), body.get("keys")
        if not endpoint_ok(endpoint):
            return _json_error("endpoint", 400)
        if not isinstance(keys, dict) or not _key_ok(keys.get("p256dh"), 65) or not _key_ok(keys.get("auth"), 16):
            return _json_error("keys", 400)
        sess = site().session()
        sub = _device(endpoint)
        if sub is None:
            sub = PushSubscription(endpoint=endpoint, person_id=me.id, **PUSH_DEFAULTS)
            sess.add(sub)
        elif sub.person_id != me.id:
            sub.person_id = me.id
            sub.told_up_to = None
            for k, v in PUSH_DEFAULTS.items():
                setattr(sub, k, v)
        sub.p256dh, sub.auth = keys["p256dh"], keys["auth"]
        sub.gen, sub.browser = me.session_gen, browser_mark()
        sess.flush()
        extra = sess.execute(sa.select(PushSubscription.id).where(PushSubscription.person_id == me.id)
                             .order_by(PushSubscription.created_at.desc(), PushSubscription.id.desc())
                             .offset(DEVICES_MAX)).scalars().all()
        if extra:
            sess.execute(sa.delete(PushSubscription).where(PushSubscription.id.in_(extra))
                         .execution_options(synchronize_session=False))
        return jsonify({"ok": True, "on": _prefs(sub)})

    @bp.post("/push/state")
    @_rests(json_answer=True)
    def push_state():
        """What this device is nudged for, with this sign-in: its switches,
        or nothing. A device kept for somebody else, or from before Sign out
        everywhere, is nobody's now: this browser is signed in as `me`."""
        me, body, refused = _asked()
        if refused:
            return refused
        sub = _device(body.get("endpoint"))
        if sub is None:
            return jsonify({"ok": True, "on": None})
        if sub.person_id != me.id or sub.gen != me.session_gen:
            site().session().delete(sub)
            site().session().flush()
            return jsonify({"ok": True, "on": None})
        sub.browser = browser_mark()
        site().session().flush()
        return jsonify({"ok": True, "on": _prefs(sub)})

    @bp.post("/push/prefs")
    @_rests(json_answer=True)
    def push_prefs():
        """One of this device's switches: {endpoint, kind, on}."""
        me, body, refused = _asked()
        if refused:
            return refused
        kind, on = body.get("kind"), body.get("on")
        if kind not in PUSH_KINDS or not isinstance(on, bool):
            return _json_error("kind", 400)
        sub = _device(body.get("endpoint"))
        if sub is None or sub.person_id != me.id:
            return _json_error("gone", 404)
        setattr(sub, kind, on)
        site().session().flush()
        return jsonify({"ok": True, "on": _prefs(sub)})

    @bp.post("/push/test")
    @_rests(json_answer=True)
    def push_test():
        """A nudge to this device now, to see one arrive (Settings' Send me a
        test nudge): what its push service answered, said on the page. It
        asks the push service while the request waits, holding nothing of
        the database's while it does; a device the service says is gone goes."""
        if not origin_ok() or not token_ok():
            return _json_error("stale", 403)
        me = current_person()
        if me is None:
            return _json_error("signed_out", 401)
        if over("push-test", "person|" + me.public_id):
            return _json_error("limited", 429)
        body = request.get_json(silent=True)
        body = body if isinstance(body, dict) else {}
        sub = _device(body.get("endpoint"))
        if sub is None or sub.person_id != me.id or sub.gen != me.session_gen:
            return _json_error("gone", 404)
        said = (TEST_BODY.format(device=body["device"]) if body.get("device") in TEST_DEVICES else TEST_BODY_ANY)
        endpoint, p256dh, auth = sub.endpoint, sub.p256dh, sub.auth
        sess = site().session()
        sess.rollback()                     # nothing written yet: let go of the database meanwhile
        payload = {"title": TEST_TITLE, "body": said, "url": url_for("social.you"), "tag": "test",
                   "icon": url_for("social.static", filename="blooby-icon-192.png"), "badge": None}
        status, reason = _send(endpoint, p256dh, auth, payload, "test", public_origin() + url_for("social.home"))
        who = service_of(endpoint)
        if status in (404, 410):
            sess.execute(sa.delete(PushSubscription).where(PushSubscription.endpoint == endpoint)
                         .execution_options(synchronize_session=False))
            sess.flush()
            return jsonify({"ok": False, "gone": True, "who": who, "status": status})
        if status is not None and 200 <= status < 300:
            return jsonify({"ok": True, "who": who, "status": status})
        current_app.logger.warning("push: a test nudge: %s answered %s %s", who, status, reason)
        return jsonify({"ok": False, "who": who, "status": status, "reason": reason})

    @bp.post("/push/unsubscribe")
    @_rests(json_answer=True)
    def push_unsubscribe():
        """This device, no longer."""
        me, body, refused = _asked()
        if refused:
            return refused
        sub = _device(body.get("endpoint"))
        if sub is not None and sub.person_id == me.id:
            site().session().delete(sub)
            site().session().flush()
        return jsonify({"ok": True})

    return bp
