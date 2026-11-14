"""skribl.create_post(): a host creates a Skribl from its own server-side code.

WHAT THIS IS FOR. `POST /api/skribls` serves a host whose composer is a
browser. A host whose composer is a server-side FORM — skribls.net is one —
has the payload in `request.form` on its own view, has already authenticated
the author and checked its own CSRF token, and needs the Skribl to land in the
SAME transaction as the feed row that points at it. Having its server POST to
its own JSON endpoint gives it a second request, a second auth, and a separate
transaction, so a failure between the two leaves a Skribl with no post or a
post with no Skribl.

THE ASSERTION THAT ACTUALLY MATTERS IS AGREEMENT (section 2). create_post is
not a second creation path — the route calls it — but "the route calls it" is
a fact about today's tree, and the thing that would make this dangerous is the
day someone adds a rule to one caller only. So every rejection below is driven
through BOTH callers from one table and the two answers are compared. That is
the same instrument verify_inline.py points at the two playback
implementations, for the same reason.

MUTATION-TESTED, and one of the three mutations taught something.

  * Section 2, by giving the ROUTE a rejection message create_post does not
    have: "BOTH give the same message" fails and prints both strings.
  * Section 3, by adding session().commit() inside create_post: "nothing is
    durable yet" fails at 1 durable post, and section 4's rollback assertion
    fails with it. (Not "the host's uncommitted row is still uncommitted" —
    that one is inserted after the call and survives this mutation. An
    assertion that does not move under the mutation it is supposed to catch is
    worth knowing about.)
  * Section 5, by making create_post charge the limiter. The FIRST attempt used
    _client_ip(), and it never reached section 5: it crashed in section 3 with
    "Working outside of request context", because _client_ip reads the Flask
    `request`. That is a better argument for this split than the one written in
    creation.py's header — the limiter cannot run outside a request even if
    somebody wanted it to — but it proves nothing about section 5, so the
    mutation was redone with a literal IP. Then the assertion fails at 1
    reservation, which is what section 5 is for.
"""
import os
import pathlib
import re
import sys
import tempfile
from assertions import make_check

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

results = []


check = make_check(results, with_detail=True)


import sqlalchemy as sa
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

import skribl
import skribl.models

_tmp = tempfile.mkdtemp()
_url = f"sqlite:///{_tmp}/createpost.db"

host = Flask(__name__)
host.config["SQLALCHEMY_DATABASE_URI"] = _url
host.config["SECRET_KEY"] = "harness-createpost"
db = SQLAlchemy()
db.init_app(host)
# A host that signs its users in. create_post takes author_id as an ARGUMENT,
# so it does not depend on this — but the ROUTE does, and section 2 compares
# the two, so they have to agree on who the author is.
_CURRENT_USER = [None]
# csrf=False, and the blueprint REFUSES to start without that choice being
# made: configuring current_user_id without a CSRF validator means any
# third-party page can post as the logged-in user (DECISIONS.md #2). This
# harness host authenticates by a variable, not a cookie, so False is the
# honest declaration rather than a way around the guard.
skribl.init_skribl(host, session=lambda: db.session,
                   current_user_id=lambda: _CURRENT_USER[0],
                   csrf=False)
skribl.models.attach_to_metadata(db.metadata)

FRAME = {"strokes": [], "strokeGroups": [], "background": {"color": "#101418"}}


def payload(**over):
    p = {"frames": [dict(FRAME)]}
    p.update(over)
    return p


with host.app_context():
    db.create_all()
    db.session.execute(sa.text(
        "CREATE TABLE IF NOT EXISTS host_posts "
        "(id INTEGER PRIMARY KEY, body TEXT, skribl_id TEXT)"))
    db.session.commit()


def _durable(query):
    # A FRESH connection sees only committed state; the host's own session
    # would see its pending rows and prove nothing.
    eng = sa.create_engine(_url)
    try:
        with eng.connect() as c:
            return c.execute(sa.text(query)).scalar()
    finally:
        eng.dispose()


print("\n1 — THE EXPORT IS THE CONTRACT")
check("skribl.create_post is exported", hasattr(skribl, "create_post"))
check("skribl.SkriblRejected is exported", hasattr(skribl, "SkriblRejected"))
for _name in ("create_post", "SkriblRejected", "CreatedPost",
              "SkriblIdempotencyRace", "SkriblUnavailable"):
    check(f"{_name} is in __all__", _name in skribl.__all__)
# A host reads the docstring to learn the contract; an empty one is a gate that
# passes while the documentation it stands for does not exist.
check("create_post carries a docstring naming author_id",
      "author_id" in (skribl.create_post.__doc__ or ""))

print("\n2 — AGREEMENT: the endpoint and create_post reject the same things")
# One table, two callers. A rule added to either side alone breaks this.
REJECTIONS = [
    ("not an object",            "nope"),
    ("strokes not a list",       payload(strokes="x")),
    ("photo not an object",      payload(photo=[])),
    ("baseSnapshot not a str",   payload(baseSnapshot=5)),
    ("title not a string",       payload(title=123)),
    ("caption not a string",     payload(caption=123)),
    ("frames not a list",        {"frames": "x"}),
    ("unknown visibility",       payload(visibility="banana")),
    ("title too long",           payload(title="z" * 5000)),
    ("caption too long",         payload(caption="z" * 50000)),
]
with host.app_context():
    client = host.test_client()
    for label, body in REJECTIONS:
        r = client.post("/api/skribls", json=body)
        db.session.rollback()
        route_status, route_msg = r.status_code, (r.get_json() or {}).get("error")
        try:
            skribl.create_post(body, author_id=None)
            fn_status, fn_msg = 201, None
        except skribl.SkriblRejected as exc:
            fn_status, fn_msg = exc.status, exc.message
        db.session.rollback()
        check(f"{label}: endpoint rejects it", route_status == 400,
              f"status {route_status}")
        check(f"{label}: create_post raises SkriblRejected", fn_status == 400,
              f"status {fn_status}")
        check(f"{label}: BOTH give the same message", route_msg == fn_msg,
              f"route={route_msg!r} fn={fn_msg!r}")

print("\n2b — WHAT THE USER READS: the rejection is copy, and a title is trimmed")
# The editors surface `error` from a 400 verbatim (editor_post.js, flip.js), so
# the string create_post raises IS the sentence the user sees. It used to be
# "'title' is too long (81 characters; limit 80)." — a log line. The mechanism
# pinned here is the shape, not the wording: no quoted field name, the limit
# stated. Calibrated red on the v287 tree, which quoted the field.
from skribl.core import MAX_TITLE_CHARS as _TCAP
with host.app_context():
    try:
        skribl.create_post(payload(title="z" * (_TCAP + 1)), author_id=None)
        _msg = None
    except skribl.SkriblRejected as exc:
        _msg = exc.message
    db.session.rollback()
    check("an over-length title is refused with a sentence, not a log line",
          _msg is not None and not re.search(r"'\w+'", _msg) and str(_TCAP) in _msg,
          repr(_msg))
    # "   " used to survive .strip() as '' and be stored: the player then fell
    # back to the product name in og:title while the library said "Untitled
    # Skribl". Whitespace is the same as nothing typed.
    _ws = skribl.create_post(payload(title="   \t "), author_id=None)
    check("a whitespace-only title stores as the default, not as ''",
          _ws.post.title == "Untitled Skribl", repr(_ws.post.title))
    db.session.rollback()

print("\n3 — ONE TRANSACTION: the host's row and the Skribl commit together")
with host.app_context():
    made = skribl.create_post(payload(title="From a form"), author_id=7)
    check("create_post returns a public_id",
          isinstance(made.public_id, str) and len(made.public_id) > 4,
          repr(made.public_id))
    check("and the flushed post carries a real primary key",
          isinstance(made.post.id, int), repr(made.post.id))
    check("nothing is durable yet — create_post only flushed",
          _durable("SELECT COUNT(*) FROM skribl_posts") == 0,
          f"durable posts: {_durable('SELECT COUNT(*) FROM skribl_posts')}")
    # This is the whole point: the host points its OWN row at the Skribl and
    # commits once.
    db.session.execute(
        sa.text("INSERT INTO host_posts (body, skribl_id) VALUES (:b, :s)"),
        {"b": "hello", "s": made.public_id})
    check("the host's uncommitted row is still uncommitted",
          _durable("SELECT COUNT(*) FROM host_posts") == 0)
    db.session.commit()
    check("after the HOST's commit both are durable",
          _durable("SELECT COUNT(*) FROM skribl_posts") == 1
          and _durable("SELECT COUNT(*) FROM host_posts") == 1,
          f"posts {_durable('SELECT COUNT(*) FROM skribl_posts')}, "
          f"host {_durable('SELECT COUNT(*) FROM host_posts')}")
    # STORED AS TEXT SINCE v279, so this compares "7" and not 7. The column was
    # Integer while docs/INTEGRATION.md advertised "your user id", which meant a
    # host with UUID or OAuth-subject identities could not integrate at all; an
    # audit of v278 called that out. An integer host is unaffected — 42 stores
    # as "42" and compares equal to "42" everywhere — and this raw SQL read is
    # the one place that difference is visible, because it bypasses the type
    # that normalises it.
    _stamp = _durable("SELECT user_id FROM skribl_posts LIMIT 1")
    check("the author stamp is the id the host passed, not a guess",
          str(_stamp) == "7", repr(_stamp))

print("\n4 — AND A HOST ROLLBACK TAKES THE SKRIBL WITH IT")
with host.app_context():
    before = _durable("SELECT COUNT(*) FROM skribl_posts")
    made2 = skribl.create_post(payload(title="Abandoned"), author_id=7)
    db.session.execute(
        sa.text("INSERT INTO host_posts (body, skribl_id) VALUES ('x', :s)"),
        {"s": made2.public_id})
    db.session.rollback()
    check("a rolled-back host transaction leaves NO Skribl behind",
          _durable("SELECT COUNT(*) FROM skribl_posts") == before,
          f"{_durable('SELECT COUNT(*) FROM skribl_posts')} vs {before}")
    check("and no host row either",
          _durable("SELECT COUNT(*) FROM host_posts") == 1)

print("\n5 — THE HOST OWNS ABUSE CONTROL ON ITS OWN PATH")
# Documented in creation.py's header and in docs/INTEGRATION.md. A host that
# assumes it inherited Skribl's IP limiter has an unlimited posting endpoint
# and no indication of it, so the behaviour is asserted rather than described.
import skribl.ratelimit as _rl
import skribl.routes as _routes
with host.app_context():
    _calls = []
    _real = _rl._rate_reserve_post
    # PATCH BOTH BINDINGS. routes.py does `from .ratelimit import
    # _rate_reserve_post`, so it holds its OWN reference and patching only the
    # ratelimit module would leave the endpoint calling the real function —
    # an assertion that passes while measuring nothing, which is how the first
    # draft of this section reported "0 reservations" for the endpoint too.
    _rl._rate_reserve_post = lambda ip: (_calls.append(ip), _real(ip))[1]
    _routes._rate_reserve_post = _rl._rate_reserve_post
    try:
        skribl.create_post(payload(title="Direct"), author_id=7)
        db.session.rollback()
        check("create_post does NOT charge Skribl's IP post limiter",
              _calls == [], f"{len(_calls)} reservation(s)")
        host.test_client().post("/api/skribls", json=payload())
        db.session.rollback()
        check("...while the HTTP endpoint still does", len(_calls) == 1,
              f"{len(_calls)} reservation(s)")
    finally:
        _rl._rate_reserve_post = _real
        _routes._rate_reserve_post = _real

print("\n6 — VISIBILITY DEFAULTS AND THE ANONYMOUS PRIVATE POST")
with host.app_context():
    made3 = skribl.create_post(payload(title="Default vis"), author_id=7)
    check("visibility defaults to unlisted, NOT public",
          made3.post.visibility == "unlisted", made3.post.visibility)
    db.session.rollback()
    made4 = skribl.create_post(payload(title="Feed", visibility="public"),
                               author_id=7)
    check("a host feed asks for public explicitly and gets it",
          made4.post.visibility == "public", made4.post.visibility)
    db.session.rollback()
    try:
        skribl.create_post(payload(visibility="private"), author_id=None)
        _anon_private = "accepted"
    except skribl.SkriblRejected as exc:
        _anon_private = exc.message
    db.session.rollback()
    check("a private Skribl with no author is refused, not stored unreadable",
          "signed-in author" in _anon_private, _anon_private)

print("\n7 — THE POST A HOST MADE IS A REAL POST, servable by the player")
with host.app_context():
    _CURRENT_USER[0] = 7
    made5 = skribl.create_post(
        payload(title="Servable", visibility="public"), author_id=7)
    pid = made5.public_id
    db.session.commit()
    r = host.test_client().get(f"/s/{pid}")
    check("GET /s/<id> serves the host-created Skribl", r.status_code == 200,
          str(r.status_code))
    check("...and the page carries its title",
          b"Servable" in r.data)
    r = host.test_client().get(f"/api/skribls/{pid}")
    check("GET /api/skribls/<id> returns its payload", r.status_code == 200,
          str(r.status_code))
    check("the payload round-trips the frame",
          isinstance((r.get_json() or {}).get("skribl", {}).get("frames"), list))
    r = host.test_client().get("/api/skribls")
    # The listing envelope key is "items". Reading a key the endpoint does not
    # emit gives an empty list and an assertion that fails for the wrong
    # reason — which is exactly what the first draft did.
    _ids = [s.get("id") for s in (r.get_json() or {}).get("items", [])]
    check("a public host-created Skribl appears in the listing", pid in _ids,
          f"listing had {len(_ids)}")
    _CURRENT_USER[0] = None

print("\n8 — NO BLUEPRINT, NO GUESSING A STORE")
# Defaulting to a fresh InlineStore would be worse than failing: media would be
# inlined into the JSON column on the host's path while the endpoint
# externalised it, so two posts made the same afternoon would be stored two
# different ways and only one of them sweepable.
_bare = Flask("bare")
_bare.config["SQLALCHEMY_DATABASE_URI"] = _url
with _bare.app_context():
    try:
        skribl.create_post(payload(), author_id=1)
        _bare_msg = "accepted"
    except RuntimeError as exc:
        _bare_msg = str(exc)
    except Exception as exc:                       # noqa: BLE001
        _bare_msg = f"{type(exc).__name__}: {exc}"
check("an app with no Skribl blueprint gets a named error, not a silent store",
      "no Skribl blueprint" in _bare_msg, _bare_msg[:90])

print("\n9 — A POST THAT CANNOT RESERVE ITS MEDIA DOES NOT SHIP")
# THE FINDING, from an audit of v278. The pending-media claim exists to close a
# race the tree documents in storage.py: the sweeper can delete an object
# AFTER a successful age-touch, so touching alone is not enough. creation.py
# wrapped the claim in `except Exception: pass` and called it best-effort,
# "degrades to the pre-v266 age re-check" — degrading, that is, to the very
# mechanism the other file says does not work. The result was that a post could
# commit, durable and user-visible, pointing at media a concurrent sweep had
# already removed.
#
# It now raises SkriblUnavailable (503). The trade is asymmetric: an
# externalised object nobody references is collected by the next sweep, while a
# published post with missing media is permanent damage.
#
# Driven by making the claim itself fail, which is the only way to reach the
# branch — the ordinary path succeeds.
import skribl.creation as _creation

_before_ids = None
with host.app_context():
    _before_ids = {r[0] for r in db.session.execute(
        sa.text("SELECT public_id FROM skribl_posts")).all()}

_real_claim = _creation.claim_media


def _broken_claim(*a, **k):
    raise RuntimeError("simulated: the claim table is unreachable")


# A payload carrying media, or media_keys is empty and the branch never runs.
_PNG = ("data:image/png;base64,"
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAE"
        "hQGAhKmMIQAAAABJRU5ErkJggg==")


def _media_payload():
    # baseSnapshot, NOT background.image. The first attempt used the latter and
    # externalise_payload returned NO keys, so `if media_keys:` was false and
    # this whole section passed over a branch it never entered. _iter_media_items
    # walks `music`/`photo` as dicts carrying `.data`, plus a bare-data-URL
    # `baseSnapshot`; a data URL under background.image is not a media slot at
    # all. Verified non-empty before this was trusted.
    return {"frames": [{"strokes": [], "strokeGroups": [],
                        "background": {"color": "#101418"},
                        "baseSnapshot": _PNG}]}


# A REAL STORE, OR THE BRANCH IS UNREACHABLE. The first version of this section
# reported ACCEPTED with the fix in place, because this harness host runs the
# default InlineStore: the data URL stays in the JSON column, externalise_payload
# returns no keys, and `if media_keys:` is false — so the assertion was passing
# over a branch it never entered. A LocalDiskStore is what makes media_keys
# non-empty and the reservation real.
import tempfile as _tf
from skribl.storage import LocalDiskStore as _LDS
_store = _LDS(_tf.mkdtemp(), lambda k: "/media/" + k)

_creation.claim_media = _broken_claim
try:
    with host.app_context():
        try:
            skribl.create_post(_media_payload(), author_id=1,
                               media_store=_store)
            _claim_outcome = "ACCEPTED"
        except Exception as exc:                       # noqa: BLE001
            _claim_outcome = type(exc).__name__
        db.session.rollback()
finally:
    _creation.claim_media = _real_claim

check("a failed media reservation refuses the post",
      _claim_outcome == "SkriblUnavailable",
      f"{_claim_outcome} — swallowing it publishes a post whose media a "
      "concurrent sweep may already have deleted, which no later job repairs")
check("...and it is a 503, not a 400 — the payload was fine",
      getattr(_creation.SkriblUnavailable, "status", None) == 503,
      "a client that retries the same bytes should succeed")

with host.app_context():
    _after_ids = {r[0] for r in db.session.execute(
        sa.text("SELECT public_id FROM skribl_posts")).all()}
check("...and no post row survived the refusal",
      _after_ids == _before_ids,
      f"{sorted(_after_ids - _before_ids)} left behind")

# EXT-P0-1: THE SAME REFUSAL, WITH NOTHING MOCKED. Everything above this line
# replaced claim_media with _broken_claim, which raises. An external audit of
# v305 pointed out what that could and could not prove: it shows the CALLER
# handles a raising helper, and the shipped helper ended `except Exception:
# return 0`, so it never raised and this suite stayed green over a live defect
# for a full release. The mock's failure mode was not the implementation's.
#
# So the reservation is broken in the DATABASE instead and the real function is
# called: the claim table is dropped while the readiness cache still says it is
# there — a mid-flight schema change, or any failing statement — and the post
# must still be refused. If claim_media ever goes back to swallowing, this goes
# red where the mock above cannot.
import sqlalchemy as _sa_p0                                        # noqa: E402
from skribl import storage as _storage_p0                          # noqa: E402
from skribl.models import SkriblPendingMedia as _SPM_p0            # noqa: E402

# A TRIGGER, NOT A DROPPED TABLE, and the difference is the whole scenario.
# Dropping the table breaks everything that touches it, so the post dies of
# some later error and "refused" proves nothing about THIS guard. The audit's
# actual case is narrower and worse: the claim INSERT fails while the table is
# present and readable, so nothing else notices and the post sails on to a
# successful, durable commit pointing at media the sweeper is free to delete.
# A BEFORE INSERT trigger that ABORTs reproduces exactly that -- a real failing
# write from the database itself, with every other statement healthy.
with host.app_context():
    _eng_p0 = db.session.get_bind()
    if not _sa_p0.inspect(_eng_p0).has_table("skribl_pending_media"):
        _SPM_p0.__table__.create(_eng_p0)
    _storage_p0._pending_media_ready.clear()
    _ready_before = _storage_p0.pending_media_ready(_eng_p0)
    with _eng_p0.connect() as _c:
        _c.exec_driver_sql(
            "CREATE TRIGGER _p0_block BEFORE INSERT ON skribl_pending_media "
            "BEGIN SELECT RAISE(ABORT, 'simulated claim-write failure'); END")
        _c.commit()
    try:
        skribl.create_post(_media_payload(), author_id=1, media_store=_store)
        _real_outcome = "ACCEPTED"
    except Exception as exc:                                       # noqa: BLE001
        _real_outcome = type(exc).__name__
    db.session.rollback()
    with _eng_p0.connect() as _c:                  # leave the schema as found
        _c.exec_driver_sql("DROP TRIGGER _p0_block")
        _c.commit()

check("EXT-P0-1 precondition: the gate said the claim table was there",
      _ready_before is True,
      "without this the refusal below could be the designed no-op path")
check("EXT-P0-1: the REAL claim path refusing also refuses the post",
      _real_outcome == "SkriblUnavailable",
      f"{_real_outcome} — this is the assertion the mocked one only looked "
      f"like; a swallowed reservation failure publishes a post whose media a "
      f"concurrent sweep may already have deleted")

# The ordinary path still works — a guard that fails everything is not a fix.
with host.app_context():
    _ok = skribl.create_post(_media_payload(), author_id=1,
                             media_store=_store)
    db.session.commit()
check("a working reservation still posts normally", bool(_ok.public_id),
      "the claim path must only refuse when the claim actually fails")

print("\n10 — AN IDENTITY IS OPAQUE TEXT, WHATEVER SHAPE THE HOST USES")
# THE FINDING, from an audit of v278: docs/INTEGRATION.md documents
# `current_user_id` as "a callable returning your user id" and its worked
# example passes the host's native `current_user.id` straight through — while
# the column was Integer. A host identifying users by UUID, ULID, OAuth subject
# or email could not integrate at all: creation failed at flush and the listing
# endpoint coerced ?user_id= with int() and 400'd before querying.
#
# "Do not leave the API generic while the schema is not." It is text now, and
# these are the shapes that have to work.
_IDS = [
    ("integer", 12345),
    ("numeric string", "12345"),
    ("UUID", "6f1c9a80-3b2e-4d5f-9a11-7c0de2f4b8a3"),
    ("ULID", "01ARZ3NDEKTSV4RRFFQ69G5FAV"),
    ("OAuth subject", "auth0|5f3c2b1a9d8e7f6a5b4c3d2e"),
    ("email", "person@example.com"),
]
with host.app_context():
    for _label, _uid in _IDS:
        try:
            _made = skribl.create_post(payload(title=f"id-{_label}"),
                                       author_id=_uid)
            db.session.commit()
            _row = db.session.query(skribl.models.SkriblPost).filter_by(
                public_id=_made.public_id).one()
            _stored = _row.user_id
            _reads = _row.visible_to(_uid)
            _ok = _stored == str(_uid) and _reads is True
            _detail = f"stored {_stored!r}, author can read: {_reads}"
        except Exception as exc:                       # noqa: BLE001
            _ok, _detail = False, f"{type(exc).__name__}: {exc}"
        check(f"a {_label} author id round-trips", _ok, _detail)

# AN INTEGER HOST MUST NOT NOTICE. 42 in, "42" stored, and ownership still
# matches when the host passes the integer back — which is the whole reason
# both sides of every comparison normalise.
with host.app_context():
    # PRIVATE, or this measures nothing: payload() defaults to "unlisted",
    # which ANY reader may see, so visible_to() returned True for a stranger
    # and the "a different id does not" assertion failed on a post that was
    # never about ownership. Only private makes visible_to an ownership test.
    _m = skribl.create_post(payload(title="int-host", visibility="private"),
                            author_id=42)
    db.session.commit()
    _r = db.session.query(skribl.models.SkriblPost).filter_by(
        public_id=_m.public_id).one()
    check("an integer host still owns its post when it passes an int back",
          _r.visible_to(42) is True and _r.visible_to("42") is True,
          f"int:{_r.visible_to(42)} str:{_r.visible_to('42')}")
    check("...and a DIFFERENT id still does not",
          _r.visible_to(43) is False and _r.visible_to("4") is False,
          "normalising must not make unrelated ids collide")

# None is not an identity and must never become the string "None".
check("None stays None rather than becoming a string",
      skribl.models.normalise_user_id(None) is None,
      'the string "None" would be an owner somebody could authenticate as')

print("\n11 — WHAT A HOST'S FEED READS: describe_posts")
# A host that keeps its own posts (the Skribl site's, piece 4) shows each
# skribl with skribl_inline() and needs its size, line and plays without
# importing Skribl's models. describe_posts() hands over the listing's own
# item, for the person looking, by the rule every read follows.
check("describe_posts is exported, in __all__, and its docstring names viewer_id",
      hasattr(skribl, "describe_posts") and "describe_posts" in skribl.__all__
      and "viewer_id" in (skribl.describe_posts.__doc__ or ""))
with host.app_context():
    _pub = skribl.create_post(payload(title="d-public", visibility="public"), author_id=70)
    _unl = skribl.create_post(payload(title="d-unlisted"), author_id=70)
    _pri = skribl.create_post(payload(title="d-private", visibility="private"), author_id=70)
    db.session.commit()
    _ids = [_pub.public_id, _unl.public_id, _pri.public_id, "no-such-id", _pub.public_id, 7, None]
    _anyone = skribl.describe_posts(_ids)
    _author = skribl.describe_posts(_ids, viewer_id=70)
    _other = skribl.describe_posts(_ids, viewer_id=71)
    check("describe_posts shows anyone the public and the unlisted, its author the private too, and"
          " nobody an id that is not there (repeats and non-strings left out)",
          set(_anyone) == {_pub.public_id, _unl.public_id} and set(_other) == set(_anyone)
          and set(_author) == {_pub.public_id, _unl.public_id, _pri.public_id},
          f"anyone {sorted(_anyone)}; author {sorted(_author)}; another {sorted(_other)}")
    _row = db.session.query(skribl.models.SkriblPost).filter_by(public_id=_pub.public_id).one()
    _item = _anyone.get(_pub.public_id) or {}
    check("...each item is the listing's own (feed_dict), the drawing's ground and whether it is on a picture,"
          " with no payload in it",
          {k: v for k, v in _item.items() if k not in ("ground", "on_photo")} == _row.feed_dict()
          and _item.get("ground") == "#101418" and _item.get("on_photo") is False
          and "payload" not in _item and "payload_json" not in _item
          and {"canvas_w", "canvas_h", "line", "views", "title", "caption"} <= set(_item),
          f"keys {sorted(_item)}; ground {_item.get('ground')!r}; on_photo {_item.get('on_photo')!r}")
    # THE GROUND (Nov 14, the Skribl site's tiles: a tall drawing made on the
    # Pad's dark canvas sat in a tile of cream paper): the colour the drawing
    # is painted on, as the player paints its first page (inlineplayer.js:
    # frames[0]'s background, else the payload's own), and nothing a page
    # could read as more than a colour.
    _grounds = {
        "a frame's": payload(frames=[dict(FRAME, background={"color": "#0D0F14"})]),
        "three digits": payload(frames=[dict(FRAME, background={"color": "#AbC"})]),
        "the top level's": {"strokes": [], "background": {"color": "#f6f2ea"}},
        "the frame's over the top's": payload(frames=[dict(FRAME, background={"color": "#101418"})],
                                              background={"color": "#ffffff"}),
        "an empty frame's, the top's": payload(frames=[dict(FRAME, background={"color": ""})],
                                              background={"color": "#123456"}),
        "words after a colour": payload(frames=[dict(FRAME, background={"color": "#fff; background: url(x)"})]),
        "a rule": payload(frames=[dict(FRAME, background={"color": "red;}body{display:none"})]),
        "a name": payload(frames=[dict(FRAME, background={"color": "red"})]),
        "eight digits": payload(frames=[dict(FRAME, background={"color": "#0d0f14ff"})]),
        "a number": payload(frames=[dict(FRAME, background={"color": 7})]),
        "none": payload(frames=[{"strokes": [], "strokeGroups": []}]),
    }
    _gids = {k: skribl.create_post(v, author_id=72).public_id for k, v in _grounds.items()}
    db.session.commit()
    _seen = []

    def _note(conn, cursor, statement, *rest):
        _seen.append(statement)
    sa.event.listen(db.engine, "before_cursor_execute", _note)
    try:
        _gd = skribl.describe_posts(list(_gids.values()))
    finally:
        sa.event.remove(db.engine, "before_cursor_execute", _note)
    _gsaid = {k: (_gd.get(v) or {}).get("ground", "absent") for k, v in _gids.items()}
    check("its ground is the colour the drawing's first page is painted on, as the player paints it: frames[0]'s"
          " background, else the payload's own (an empty one is none, as the player's ||), a hex colour, lowercase,"
          " six digits (three written out)",
          [_gsaid[k] for k in ("a frame's", "three digits", "the top level's", "the frame's over the top's",
                               "an empty frame's, the top's")]
          == ["#0d0f14", "#aabbcc", "#f6f2ea", "#101418", "#123456"], str(_gsaid))
    check("...and never anything but a colour: words after one, a rule, a name, eight digits, a number or none are"
          " None, so a host can set it as a value of its own CSS",
          all(_gsaid[k] is None for k in ("words after a colour", "a rule", "a name", "eight digits", "a number",
                                         "none")), str(_gsaid))
    _sel = [s_ for s_ in _seen if "skribl_posts" in s_]
    # WHERE THE LOOKS INSIDE SIT (after v330: the ground and the picture are
    # columns, written at post time): every look into the payload is in the
    # branch a CASE takes only when that column is NULL, a post from before
    # the columns; read off the statement's own CASE ... THEN ... ELSE.
    _cases = {c: re.findall(r"CASE WHEN \(skribl_posts\.%s IS NULL\) THEN (.*?) ELSE skribl_posts\.%s END" % (c, c),
                            _sel[0] if _sel else "", re.S) for c in ("ground", "on_photo")}
    _looks = len(re.findall(r"json_extract|#>>", _sel[0], re.I)) if _sel else None
    _guarded = {c: sum(len(re.findall(r"json_extract|#>>", b, re.I)) for b in v) for c, v in _cases.items()}
    check("...read in one query that selects no payload (deferred, as the listing's): the ground and the picture"
          " from their columns, and the drawing only in the branch a CASE takes where a column is NULL (a post from"
          " before them): the ground's two paths there, the picture's four",
          len(_sel) == 1 and not re.search(r"payload_json\s+AS\s", _sel[0], re.I)
          and len(_cases["ground"]) == 1 and len(_cases["on_photo"]) == 1
          and _guarded == {"ground": 2, "on_photo": 4} and _looks == 6,
          f"{len(_sel)} queries; payload selected"
          f" {bool(_sel and re.search(r'payload_json[ ]+AS[ ]', _sel[0], re.I))}; looks inside {_looks},"
          f" in a column's NULL branch {_guarded}")
    _many = skribl.describe_posts([_pub.public_id] * 3 + [f"x{i}" for i in range(500)])
    check("...and an empty or oversized ask reads nothing past its first 200 ids",
          skribl.describe_posts([]) == {} and skribl.describe_posts(None) == {}
          and set(_many) == {_pub.public_id}
          and skribl.describe_posts([f"x{i}" for i in range(200)] + [_pub.public_id]) == {},
          f"many {sorted(_many)}")

print("\n12 — A FEED OF YOUR OWN PEOPLE'S DRAWINGS: list_public_posts")
# A host whose feed shows every drawing its people put in the gallery (the
# Skribl site's Home, after v330): the newest public ones, by one author or by
# a prefix its people's ids share, a page at a time.
check("list_public_posts is exported, in __all__, and its docstring names author_prefix and before",
      hasattr(skribl, "list_public_posts") and "list_public_posts" in skribl.__all__
      and "author_prefix" in (skribl.list_public_posts.__doc__ or "") and "before" in (skribl.list_public_posts.__doc__ or ""))
with host.app_context():
    import time as _t
    _mine = []
    for _i, (_who, _vis) in enumerate((("host:ann", "public"), ("host:ann", "unlisted"), ("host:ann", "private"),
                                        ("other:zed", "public"), ("host:bo", "public"), ("host:ann", "public"))):
        _mine.append((_who, _vis, skribl.create_post(payload(title=f"l{_i}", visibility=_vis), author_id=_who).public_id))
        db.session.commit()
        _t.sleep(0.01)
    _pubs = [pid for who, vis, pid in _mine if vis == "public" and who.startswith("host:")]
    _items, _more = skribl.list_public_posts(author_prefix="host:")
    _ann, _ = skribl.list_public_posts(author="host:ann")
    check("list_public_posts holds the public ones only, newest first: by a prefix its authors share, or by one author;"
          " never unlisted, private, or another prefix's",
          [i["id"] for i in _items] == list(reversed(_pubs)) and not _more
          and [i["id"] for i in _ann] == [_mine[5][2], _mine[0][2]],
          f"by prefix {[i['title'] for i in _items]}; ann {[i['title'] for i in _ann]}")
    _p1, _m1 = skribl.list_public_posts(author_prefix="host:", limit=2)
    from datetime import datetime as _dt
    _last = _p1[-1]
    _p2, _m2 = skribl.list_public_posts(author_prefix="host:", limit=2,
                                        before=(_dt.fromisoformat(_last["created_at"]), _last["id"]))
    # Two at the very same time (l4 and l5), then the ones after that time:
    # from the larger id, the smaller at that time and older; from "", only older.
    _l4 = db.session.query(skribl.models.SkriblPost).filter_by(public_id=_mine[4][2]).one()
    _l5 = db.session.query(skribl.models.SkriblPost).filter_by(public_id=_mine[5][2]).one()
    _l4.created_at = _l5.created_at
    db.session.commit()
    _at = _dt.fromisoformat(_l5.feed_dict()["created_at"])
    _hi, _lo = sorted([_l4.public_id, _l5.public_id], reverse=True)
    _same, _ = skribl.list_public_posts(author_prefix="host:", limit=5, before=(_at, _hi))
    _p0, _ = skribl.list_public_posts(author_prefix="host:", limit=5, before=(_at, ""))
    check("...a page at a time: before (time, id) gives the ones after, two at the very same time ordered by id, and"
          " an id of \"\" leaves out that time; more says there are older ones",
          [i["id"] for i in _p1] == list(reversed(_pubs))[:2] and _m1
          and [i["id"] for i in _p2] == list(reversed(_pubs))[2:] and not _m2
          and [i["id"] for i in _same] == [_lo, _mine[0][2]] and [i["id"] for i in _p0] == [_mine[0][2]],
          f"page 1 {[i['title'] for i in _p1]} more {_m1}; page 2 {[i['title'] for i in _p2]} more {_m2};"
          f" after the larger at that time {[i['title'] for i in _same]}; after that time {[i['title'] for i in _p0]}")
    _row = db.session.query(skribl.models.SkriblPost).filter_by(public_id=_pubs[0]).one()
    _one = next(i for i in _items if i["id"] == _pubs[0])
    for _i in range(101):
        skribl.create_post(payload(title=f"cap{_i}", visibility="public"), author_id="cap:many")
    db.session.commit()
    _cap, _capmore = skribl.list_public_posts(author_prefix="cap:", limit=10 ** 6)
    check("...each item the listing's own (feed_dict), no payload in it, and no more than 100 to a call (of 101)",
          _one == _row.feed_dict() and "payload" not in _one and "payload_json" not in _one
          and len(_cap) == 100 and _capmore,
          f"keys {sorted(_one)}; {len(_cap)} of 101, more {_capmore}")

    # A FEED OF THE PEOPLE SOMEBODY FOLLOWS (after v330, the Skribl site's
    # Following): `authors`, these authors' alone, any number of them.
    _fol = []
    for _i, (_who, _vis) in enumerate((("fol:ann", "public"), ("fol:bo", "public"), ("fol:ann", "unlisted"),
                                        ("fol:cy", "public"), ("fol:ann", "public"))):
        _fol.append((_who, _vis, skribl.create_post(payload(title=f"f{_i}", visibility=_vis), author_id=_who).public_id))
        db.session.commit()
        _t.sleep(0.01)
    _two, _twomore = skribl.list_public_posts(authors=["fol:ann", "fol:cy", "fol:ann"])
    _none, _nonemore = skribl.list_public_posts(authors=[])
    _p1, _m1 = skribl.list_public_posts(authors=["fol:ann", "fol:cy"], limit=2)
    _last = _p1[-1] if _p1 else {"created_at": "2000-01-01T00:00:00", "id": ""}
    _p2, _m2 = skribl.list_public_posts(authors=["fol:ann", "fol:cy"], limit=2,
                                        before=(_dt.fromisoformat(_last["created_at"]), _last["id"]))
    check("list_public_posts(authors=[...]) holds those authors' public ones only, newest first, each once (never"
          " unlisted, never another's); an empty list lists nothing; it pages by before as the rest do; the"
          " docstring names it",
          [i["id"] for i in _two] == [_fol[4][2], _fol[3][2], _fol[0][2]] and not _twomore
          and _none == [] and not _nonemore and [i["id"] for i in _p1] == [_fol[4][2], _fol[3][2]] and _m1
          and [i["id"] for i in _p2] == [_fol[0][2]] and not _m2
          and "authors" in (skribl.list_public_posts.__doc__ or ""),
          f"two {[i['title'] for i in _two]}; none {_none}; page 1 {[i['title'] for i in _p1]} {_m1};"
          f" page 2 {[i['title'] for i in _p2]} {_m2}")
    _older = skribl.create_post(payload(title="many-older", visibility="public"), author_id="many:5").public_id
    db.session.commit()
    _t.sleep(0.01)
    _newer = skribl.create_post(payload(title="many-newer", visibility="public"), author_id="many:550").public_id
    db.session.commit()
    _many = [f"many:{i}" for i in range(600)]
    _all, _allmore = skribl.list_public_posts(authors=_many)
    _top, _topmore = skribl.list_public_posts(authors=_many, limit=1)
    check("...and any number of them: 600 authors are asked in pieces and the newest of all kept, in order, the limit"
          " and more holding across the pieces",
          [i["id"] for i in _all] == [_newer, _older] and not _allmore
          and [i["id"] for i in _top] == [_newer] and _topmore,
          f"all {[i['title'] for i in _all]} {_allmore}; top {[i['title'] for i in _top]} {_topmore}")

    # WHICH LISTING IT IS (after v330, for a host's mute: the Skribl site's): a
    # feed filter that names `author` is told the one author list_public_posts
    # is narrowed to, and None for many people's (`authors`, `author_prefix`);
    # one written for two arguments is called as before.
    _told = []

    def _quiets(q, viewer_id, author=None):
        _told.append(author)
        return q.filter(skribl.models.SkriblPost.user_id != "fol:cy") if author is None else q
    _two_args = []
    skribl.models.set_feed_filter(_quiets, app=host)
    try:
        _ab, _ = skribl.list_public_posts(authors=["fol:ann", "fol:cy"])
        _pre, _ = skribl.list_public_posts(author_prefix="fol:")
        _cy, _ = skribl.list_public_posts(author="fol:cy")
        _plain = list(_told)
        skribl.models.set_feed_filter(lambda q, v: (_two_args.append(v), q)[1], app=host)
        _still, _ = skribl.list_public_posts(author="fol:cy", viewer_id="someone")
    finally:
        skribl.models.set_feed_filter(None, app=host)
    check("a feed filter that names `author` is told the one author list_public_posts is narrowed to (fol:cy's own,"
          " kept) and None for many people's (`authors` and `author_prefix`, fol:cy left out); one written for two"
          " arguments is called as before",
          _plain == [None, None, "fol:cy"] and _fol[3][2] not in [i["id"] for i in _ab + _pre]
          and [i["id"] for i in _cy] == [_fol[3][2]] and _two_args == ["someone"]
          and [i["id"] for i in _still] == [_fol[3][2]],
          f"told {_plain}; two-argument {_two_args}; cy's own {[i['title'] for i in _cy]}")

print("\n13 — WHAT THE DRAWING IS PAINTED ON: two columns, written at post time")
# After v330 (the owner's "Yes to both, build them", Nov 14): a host's tile
# lays the box around a drawing in its own ground, and a drawing made on a
# picture keeps that picture at its sides. describe_posts read both out of the
# payload on every page (on PostgreSQL every path read re-parses the whole
# drawing), so create_post writes them once, as two small columns, by the
# player's own rules (inlineplayer.js adopt(): the first page's colour, else
# the payload's own; its photo, else a base snapshot, the page's or the
# payload's), and the Pad and Flip both post through it.
_PNG = ("data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4nGNg+M8AAAMBAQAY3Y20"
        "AAAAAElFTkSuQmCC")
_painted = {
    # name: (payload, the column's ground, on a picture)
    "a Pad drawing on the Pad's dark": (payload(frames=[dict(FRAME, background={"color": "#0D0F14"})]), "#0d0f14", False),
    "a drawing on a photo": (payload(frames=[dict(FRAME, background={"color": "#f6f2ea"}, photo={"data": _PNG})]),
                             "#f6f2ea", True),
    "on the picture the Pad began on (its page's)": (payload(frames=[{"strokes": [], "strokeGroups": [],
                                                                      "baseSnapshot": _PNG}]), "", True),
    "the payload's own base snapshot beside its pages": (payload(frames=[dict(FRAME, background={"color": "#AbC"})],
                                                                 baseSnapshot=_PNG), "#aabbcc", True),
    "a Flip, a photo under its first page": (payload(playbackMode="flip", fps=12, frames=[
        dict(FRAME, background={"color": "#123456"}, photo={"data": _PNG}), dict(FRAME, background={"color": "#654321"})]),
        "#123456", True),
    "a Flip, a photo under its second page alone": (payload(playbackMode="flip", fps=12, frames=[
        dict(FRAME, background={"color": "#fff"}), dict(FRAME, photo={"data": _PNG})]), "#ffffff", False),
    "a frameless payload from before pages, on a photo": ({"strokes": [], "background": {"color": "#ABCDEF"},
                                                          "photo": {"data": _PNG}}, "#abcdef", True),
    "a frameless payload, plain": ({"strokes": [], "background": {"color": "#f6f2ea"}}, "#f6f2ea", False),
    "the first page's colour over the payload's": (payload(frames=[dict(FRAME, background={"color": "#101418"})],
                                                           background={"color": "#ffffff"}), "#101418", False),
    "an empty first-page colour, the payload's": (payload(frames=[dict(FRAME, background={"color": ""})],
                                                          background={"color": "#123456"}), "#123456", False),
    "a photo with no picture in it": (payload(frames=[dict(FRAME, photo={"fit": "cover"})]), "#101418", False),
    "a bad ground: a name": (payload(frames=[dict(FRAME, background={"color": "red"})]), "", False),
    "a bad ground: words after a colour": (payload(frames=[dict(FRAME, background={"color": "#fff; x: url(y)"})]), "", False),
    "a bad ground: eight digits": (payload(frames=[dict(FRAME, background={"color": "#0d0f14ff"})]), "", False),
    "a bad ground: a number": (payload(frames=[dict(FRAME, background={"color": 7})]), "", False),
}
with host.app_context():
    _pids = {k: skribl.create_post(v[0], author_id=130).public_id for k, v in _painted.items()}
    db.session.commit()
    _cols = {k: tuple(db.session.execute(sa.text("SELECT ground, on_photo FROM skribl_posts WHERE public_id = :p"),
                                         {"p": v}).one()) for k, v in _pids.items()}
_wrong = {k: (_cols[k], v[1:]) for k, v in _painted.items()
          if _cols[k][0] != v[1] or _cols[k][1] is None or bool(_cols[k][1]) != v[2]}
check("create_post writes both columns at post time, by the player's own rules: `ground` the first page's colour,"
      " else the payload's own (an empty one passed over, as the player's ||), lowercase, six digits; `on_photo` the"
      " first page's photo, else a base snapshot, the page's or the payload's (a Pad drawing, a photo drawing, a base"
      " snapshot, a Flip's first page and never its second, a payload from before pages)",
      not _wrong, "; ".join(f"{k}: wrote {w}, wants {x}" for k, (w, x) in _wrong.items())[:600])
check("...and a ground no page could use is \"\", an answer and never NULL (a name, words after a colour, eight"
      " digits, a number), as False is an answer: NULL is kept for a post from before the columns",
      all(_cols[k] == ("", 0) for k in _painted if k.startswith("a bad ground"))
      and all(v[0] is not None and v[1] is not None for v in _cols.values()),
      str({k: _cols[k] for k in _painted if k.startswith("a bad ground")}))
# THE ENDPOINT THE PAD AND FLIP POST THROUGH (POST /api/skribls) is create_post
# too (section 2): the same two columns from the same payloads.
with host.app_context():
    # The route flushes and the host commits (a route never commits the shared
    # session), so it is asked inside the host's own context, as section 2 asks.
    _ep = host.test_client()
    _epids = {k: (_ep.post("/api/skribls", json=dict(_painted[k][0], visibility="public")).get_json() or {}).get("id")
              for k in ("a drawing on a photo", "a Flip, a photo under its first page", "a Pad drawing on the Pad's dark")}
    _epcols = {k: tuple(db.session.execute(sa.text("SELECT ground, on_photo FROM skribl_posts WHERE public_id = :p"),
                                           {"p": v}).one()) if v else None for k, v in _epids.items()}
    db.session.commit()
check("...and the endpoint the Pad and Flip post through writes the same two, from the same payloads (it is"
      " create_post: one place for both editors)",
      all(_epcols[k] is not None and _epcols[k][0] == _painted[k][1] and bool(_epcols[k][1]) == _painted[k][2]
          for k in _epids), str(_epcols))

bad = [(n, d) for ok, n, d in results if not ok]
print("\n" + "=" * 62)
print(f"{len(results) - len(bad)}/{len(results)} passed"
      + (("  FAILURES: " + "; ".join(f"{n} ({d})" for n, d in bad)) if bad else ""))
sys.exit(1 if bad else 0)
