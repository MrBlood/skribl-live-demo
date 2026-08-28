"""Transaction ownership: the host owns the request transaction, full stop.

THE BUG THIS PINS (outside review, P0). Skribl's routes and its db-backed rate
limiter used to call commit()/rollback() on the SHARED session the host hands to
init_skribl(). A commit on a shared session commits everything pending on it —
so a host with an uncommitted row of its own, mid-request, had that row made
durable by a drawing widget's bookkeeping. The review proved it: a host row
added and never committed was on disk after one component request.

THE CONTRACT (docs/INTEGRATION.md):
  * Skribl routes flush and use savepoints; they never commit or roll back the
    shared session.
  * The db-backed limiter runs on its OWN sessionmaker (same engine, separate
    transactions), so accounting survives the request failing and never touches
    host work. Its host-pending-row proof needs real concurrency and lives in
    verify_postgres.py; here its side of the contract is pinned statically.
  * The HOST owns the per-request commit. app.py does it for the standalone
    deployment; an embedding host does it however it already does.

Assertions 2-4 fail on the old code because the old create path committed the
shared session: the host's pending row became durable, and the post survived a
host rollback it should have died in. Assertion 1 fails on the old tree by
count: ratelimit.py alone had seven shared-session commits.
"""
import importlib
import os
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

results = []


def check(name, ok, detail=""):
    results.append((bool(ok), name, detail))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  — {detail}" if detail else ""))


print("\nSTATIC — the shared session is never committed or rolled back")
# The review found the violation by grep; keep the same instrument pointed at
# the same files so the violation cannot quietly return. Comments are excluded
# (the contract is DESCRIBED in them, in exactly these words).
for fname in ("ratelimit.py", "routes.py"):
    src = (ROOT / "skribl" / fname).read_text()
    hits = [i + 1 for i, line in enumerate(src.splitlines())
            if not line.lstrip().startswith("#")
            and ("session().commit()" in line or "session().rollback()" in line)]
    check(f"skribl/{fname} never commits/rolls back the shared session",
          not hits, f"lines {hits}" if hits else "")

import sqlalchemy as sa
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

import skribl
import skribl.models

_tmp = tempfile.mkdtemp()
_url = f"sqlite:///{_tmp}/txcontract.db"

host = Flask(__name__)
host.config["SQLALCHEMY_DATABASE_URI"] = _url
host.config["SECRET_KEY"] = "harness-txcontract"
db = SQLAlchemy()
db.init_app(host)
skribl.init_skribl(host, session=lambda: db.session)
skribl.models.attach_to_metadata(db.metadata)

FRAME = {"strokes": [], "strokeGroups": [], "background": {"color": "#101418"}}

with host.app_context():
    db.create_all()
    # A host-owned table, created and committed OUTSIDE the scenario, so the
    # only uncommitted thing in play below is the row the host is mid-writing.
    db.session.execute(sa.text(
        "CREATE TABLE IF NOT EXISTS host_notes (id INTEGER PRIMARY KEY, body TEXT)"))
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


print("\nHOST PENDING WORK — a component request must not make it durable")
with host.app_context():
    db.session.execute(sa.text("INSERT INTO host_notes (body) VALUES ('draft')"))
    # NOT committed. This is the reviewer's exact scenario: the host is midway
    # through its own request when Skribl's endpoint runs.
    r = host.test_client().post("/api/skribls", json={"frames": [FRAME]})
    check("the component request itself succeeds", r.status_code == 201,
          str(r.status_code))
    check("the host's uncommitted row is STILL uncommitted",
          _durable("SELECT COUNT(*) FROM host_notes") == 0,
          f"durable host rows: {_durable('SELECT COUNT(*) FROM host_notes')}")
    check("and the post is not durable either — the route only flushed",
          _durable("SELECT COUNT(*) FROM skribl_posts") == 0,
          f"durable posts: {_durable('SELECT COUNT(*) FROM skribl_posts')}")
    db.session.rollback()
    check("a host rollback therefore takes both with it",
          _durable("SELECT COUNT(*) FROM host_notes") == 0
          and _durable("SELECT COUNT(*) FROM skribl_posts") == 0)

print("\nHOST COMMIT — and when the host commits, both land together")
with host.app_context():
    db.session.execute(sa.text("INSERT INTO host_notes (body) VALUES ('kept')"))
    r = host.test_client().post("/api/skribls", json={"frames": [FRAME]})
    # test_client() runs in its own request context but the scoped session —
    # and its one transaction — is shared, which is the entire subject here.
    db.session.commit()
    check("host row and post are durable after the HOST's commit",
          _durable("SELECT COUNT(*) FROM host_notes") == 1
          and _durable("SELECT COUNT(*) FROM skribl_posts") == 1,
          f"host {_durable('SELECT COUNT(*) FROM host_notes')}, "
          f"posts {_durable('SELECT COUNT(*) FROM skribl_posts')}")

print("\nREQUEST BOUND — a host that set no cap still gets one")
# This host app never set MAX_CONTENT_LENGTH; the blueprint must bound the
# request itself (outside review, P1: "enforce or require a bounded whole
# request"). SKRIBL_MAX_REQUEST_BYTES is read per request, so setting it here
# exercises the blueprint's own limit rather than Werkzeug's.
os.environ["SKRIBL_MAX_REQUEST_BYTES"] = "4096"
try:
    c = host.test_client()
    r = c.post("/api/skribls", json={"frames": [FRAME]})
    check("a small post is unaffected", r.status_code == 201, str(r.status_code))
    big = {"frames": [FRAME], "caption": "z" * 8000}
    r = c.post("/api/skribls", json=big)
    check("a body past the blueprint's own cap is refused (413)",
          r.status_code == 413, str(r.status_code))
    # The test client always computes a Content-Length; blank it in the WSGI
    # environ to simulate a chunked/undeclared body.
    r = c.open("/api/skribls", method="POST", data="{}",
               content_type="application/json",
               environ_overrides={"CONTENT_LENGTH": None})
    check("a mutating request without Content-Length is refused (411)",
          r.status_code == 411, str(r.status_code))
finally:
    del os.environ["SKRIBL_MAX_REQUEST_BYTES"]
with host.app_context():
    db.session.rollback()

print("\nDIRECT REGISTRATION — two blueprints, two apps, two databases")
# F1 (v200 follow-up review): create_blueprint(session=...) used to install
# NOTHING app-locally — only the module-global last-writer-wins binding — so
# two manually registered apps both resolved to whichever session was bound
# LAST. App A read and wrote app B's database. record_once now installs each
# blueprint's factory into its registering app.
import sqlalchemy as _sa
from flask_sqlalchemy import SQLAlchemy as _SQLA


def _direct_app(dburl):
    a = Flask(f"direct-{dburl[-6:]}")
    a.config["SQLALCHEMY_DATABASE_URI"] = dburl
    a.config["SECRET_KEY"] = "harness-direct"
    d = _SQLA()
    d.init_app(a)
    bp = skribl.create_blueprint(session=lambda: d.session)
    a.register_blueprint(bp)
    eng = _sa.create_engine(dburl)
    skribl.models.create_all(eng)
    eng.dispose()

    @a.after_request
    def _c(resp):
        if resp.status_code < 500:
            d.session.commit()
        return resp

    @a.teardown_request
    def _r(exc):
        d.session.rollback()
    return a


_urlA = f"sqlite:///{tempfile.mkdtemp()}/directA.db"
_urlB = f"sqlite:///{tempfile.mkdtemp()}/directB.db"
appA = _direct_app(_urlA)
appB = _direct_app(_urlB)   # bound LAST: the global fallback points at B
rA = appA.test_client().post("/api/skribls", json={"frames": [FRAME]})
rB = appB.test_client().post("/api/skribls", json={"frames": [FRAME]})
check("both directly registered apps accept a post",
      rA.status_code == 201 and rB.status_code == 201,
      f"A {rA.status_code}, B {rB.status_code}")


def _count(dburl):
    eng = _sa.create_engine(dburl)
    try:
        with eng.connect() as c:
            return c.execute(_sa.text(
                "SELECT COUNT(*) FROM skribl_posts")).scalar()
    finally:
        eng.dispose()


check("app A's post landed in A's database, not the last-bound one",
      _count(_urlA) == 1, f"A has {_count(_urlA)} posts")
check("and app B's landed in B's", _count(_urlB) == 1,
      f"B has {_count(_urlB)} posts")

print("\nGZIP EXPANSION — the SAME limit bounds compressed and expanded bytes")
# F3: _bound_request honoured SKRIBL_MAX_REQUEST_BYTES while _inflate_request
# kept its own 25 MB fallback — a tiny gzip expanding past the configured cap
# sailed through.
import gzip as _gzip
import json as _json
os.environ["SKRIBL_MAX_REQUEST_BYTES"] = "4096"
try:
    big = _json.dumps({"frames": [FRAME], "caption": "z" * 20000}).encode()
    packed = _gzip.compress(big, 9)
    check("the probe is real: compressed under the cap, expanded over it",
          len(packed) < 4096 < len(big), f"{len(packed)} -> {len(big)}")
    r = host.test_client().post(
        "/api/skribls", data=packed,
        headers={"Content-Type": "application/json",
                 "Content-Encoding": "gzip"})
    check("a small gzip expanding past SKRIBL_MAX_REQUEST_BYTES is refused",
          r.status_code in (400, 413), str(r.status_code))
finally:
    del os.environ["SKRIBL_MAX_REQUEST_BYTES"]
with host.app_context():
    db.session.rollback()

print("\nFAIL CLOSED — auth configured without CSRF now REFUSES to build")
# v224, outside review #4. This used to log a warning. A warning is the wrong
# instrument for this: `current_user_id` plus cookie authentication and no CSRF
# verifier means any third-party page can post as the logged-in user, and the
# warning went to a logger a host may not have configured, at import time, in a
# stream nobody reads during a deploy. The configuration is now refused.
#
# What makes refusing acceptable is that there IS a legitimate configuration it
# would otherwise break: token/header authentication is not CSRF-able, and such
# a host is not wrong to pass current_user_id with no verifier. So `csrf=False`
# exists to DECLARE that, and the three cases below are the whole contract —
# omitted raises, a verifier is accepted, and the explicit declination is
# accepted. Two of the three are the reason this is not simply a hard error.
try:
    skribl.create_blueprint(session=False, current_user_id=lambda: 7)
    check("current_user_id without csrf is refused", False,
          "create_blueprint returned instead of raising")
except RuntimeError as exc:
    check("current_user_id without csrf is refused", True, str(exc)[:80])
    check("…and the message names both ways out",
          "csrf=skribl.security.double_submit_csrf" in str(exc)
          and "csrf=False" in str(exc),
          "a refusal that does not say what to do is just an outage")

try:
    skribl.create_blueprint(session=False, current_user_id=lambda: 7,
                            csrf=("h", lambda: "t", lambda _r: True))
    check("supplying a csrf verifier is accepted", True)
except RuntimeError as exc:
    check("supplying a csrf verifier is accepted", False, str(exc)[:100])

try:
    skribl.create_blueprint(session=False, current_user_id=lambda: 7, csrf=False)
    check("csrf=False declares non-cookie auth and is accepted", True,
          "a token-authenticated host is not CSRF-able and must not be blocked")
except RuntimeError as exc:
    check("csrf=False declares non-cookie auth and is accepted", False, str(exc)[:100])

# The mutation check: an unauthenticated blueprint must be unaffected. If this
# ALSO raised, the refusal above would be triggering on something other than
# the condition it claims to detect.
try:
    skribl.create_blueprint(session=False)
    check("a blueprint with no current_user_id is untouched by the rule", True)
except RuntimeError as exc:
    check("a blueprint with no current_user_id is untouched by the rule", False,
          str(exc)[:100])

print("\nTEARDOWN COMMIT — why the contract says before-response, not teardown")
# v201 review, F1: a host committing in teardown_request is OUT OF CONTRACT,
# and this demonstrates the reason rather than asserting a wish. The response
# has already left when teardown runs, and Skribl's own teardown — which
# releases the parked quota reservation on failure — cannot observe a failure
# raised by a LATER host teardown. So: client holds a 201, no post is durable,
# and the slot stays spent. The after_request pattern (tested above and used
# by app.py) is the supported topology precisely because none of that happens.
tearApp = Flask("teardown-commit-host")
_ttmp = tempfile.mkdtemp()
tearApp.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{_ttmp}/tear.db"
tearApp.config["SECRET_KEY"] = "harness-teardown"
teardb = SQLAlchemy()
teardb.init_app(tearApp)
skribl.init_skribl(tearApp, session=lambda: teardb.session)
skribl.models.attach_to_metadata(teardb.metadata)
with tearApp.app_context():
    teardb.create_all()


_boom = {"armed": False}


@tearApp.teardown_request
def _teardown_commit(exc):
    if exc is None:
        if _boom["armed"]:
            _boom["armed"] = False
            teardb.session.rollback()    # a failed commit's outcome
        else:
            teardb.session.commit()      # the unsupported topology


r = tearApp.test_client().post("/api/skribls", json={"frames": [FRAME]},
                               environ_overrides={"REMOTE_ADDR": "9.9.9.1"})
check("the unsupported topology LOOKS fine on the happy path",
      r.status_code == 201, str(r.status_code))
# Now the teardown commit fails. The FLAG drives the simulation (a rollback in
# place of the commit — byte-identical outcome to a failed commit: nothing
# durable) because monkeypatching a scoped-session proxy's commit is exactly
# the kind of injection that lies.
_boom["armed"] = True
r = tearApp.test_client().post("/api/skribls", json={"frames": [FRAME]},
                               environ_overrides={"REMOTE_ADDR": "9.9.9.1"})
with tearApp.app_context():
    teardb.session.rollback()
    durable = teardb.session.execute(sa.text(
        "SELECT COUNT(*) FROM skribl_posts")).scalar()
check("the client still received a success", r.status_code == 201,
      str(r.status_code))
check("...for a post that never became durable — the documented hazard",
      durable == 1, f"{durable} durable posts (1 from the happy path only)")

print("\nDB LIMITER + SQLITE — a failed host commit neither hangs nor strands")
# v202 review, F1: blueprint teardown runs BEFORE app teardown, so on a failed
# request the host's rollback has not run when Skribl's bookkeeping fires, and
# a limiter write from a second connection deadlocks against the host's open
# SQLite write transaction. The fix PROVES closure: with the transaction still
# open, the limiter store is not touched and the row is left pending for TTL
# recovery. The memory-backend version of this test is NOT equivalent, hence
# this one: DB backend, real SQLite file, injected commit failure.
os.environ["SKRIBL_RATE_HMAC_KEY"] = "txcontract-db-limiter"
dbl = Flask("db-limiter-host")
_dtmp = tempfile.mkdtemp()
dbl.config.update(SQLALCHEMY_DATABASE_URI=f"sqlite:///{_dtmp}/dbl.db",
                  SECRET_KEY="harness-dbl", SKRIBL_RATE_BACKEND="db",
                  SKRIBL_RATE_MAX_POSTS=5, SKRIBL_RATE_MAX_ATTEMPTS=500)
dbldb = SQLAlchemy()
dbldb.init_app(dbl)
skribl.init_skribl(dbl, session=lambda: dbldb.session)
skribl.models.attach_to_metadata(dbldb.metadata)
with dbl.app_context():
    dbldb.create_all()
_dboom = {"armed": False}


@dbl.after_request
def _dcommit(resp):
    if resp.status_code < 500:
        if _dboom["armed"]:
            _dboom["armed"] = False
            raise RuntimeError("injected host commit failure")
        dbldb.session.commit()
    return resp


@dbl.teardown_request
def _drollback(exc):
    dbldb.session.rollback()


import skribl.ratelimit as _rl2
r = dbl.test_client().post("/api/skribls", json={"frames": [FRAME]})
check("db-limiter happy path posts", r.status_code == 201, str(r.status_code))
_dboom["armed"] = True
import time as _time
_t0 = _time.monotonic()
r = dbl.test_client().post("/api/skribls", json={"frames": [FRAME]})
_elapsed = _time.monotonic() - _t0
check("the injected commit failure returns 5xx", r.status_code >= 500,
      str(r.status_code))
check("...without a lock hang", _elapsed < 4, f"{_elapsed:.2f}s")
with dbl.app_context():
    dbldb.session.rollback()
    durable = dbldb.session.execute(sa.text(
        "SELECT COUNT(*) FROM skribl_posts")).scalar()
    check("no second post is durable", durable == 1, f"{durable}")
    pend = dbldb.session.execute(sa.text(
        "SELECT COUNT(*) FROM skribl_rate_events WHERE bucket='posts' "
        "AND state='pending'")).scalar()
    check("the reservation is in the documented TTL-recoverable state "
          "(pending) or removed", pend in (0, 1), f"pending={pend}")
r = dbl.test_client().post("/api/skribls", json={"frames": [FRAME]})
check("a subsequent request is not blocked", r.status_code == 201,
      str(r.status_code))

print("\nTEARDOWN CONTAINMENT — limiter failures are logged, never raised")
# v202 review, F2: promotion/release exceptions in teardown must be contained
# — a committed post stays a success and an original exception is not masked.
_orig_commit_post = _rl2._db_rate_commit_post
_rl2._db_rate_commit_post = lambda tok: (_ for _ in ()).throw(
    RuntimeError("injected promotion failure"))
try:
    r = dbl.test_client().post("/api/skribls", json={"frames": [FRAME]})
finally:
    _rl2._db_rate_commit_post = _orig_commit_post
check("a teardown PROMOTION failure leaves the request a success",
      r.status_code == 201, str(r.status_code))
_orig_release = _rl2._db_rate_release_post
_rl2._db_rate_release_post = lambda ip, tok: (_ for _ in ()).throw(
    RuntimeError("injected release failure"))
try:
    r = dbl.test_client().post("/api/skribls", json={"caption": 5})
finally:
    _rl2._db_rate_release_post = _orig_release
check("a teardown RELEASE failure does not mask the original 4xx",
      r.status_code == 400, str(r.status_code))
del os.environ["SKRIBL_RATE_HMAC_KEY"]


print("\nF2 — A FAILED POST MUST NOT COST QUOTA (v207 review, owner option (a))")
# The decisive test the reviewer specified: SKRIBL_RATE_MAX_POSTS=1, reserve,
# force the host commit to fail, force the release's bounded write to fail,
# then retry IMMEDIATELY. If the slot was not really released the retry is
# 429 and the poster is locked out for RATE_PENDING_TTL over a failure of
# OURS. The cap is the point: the older regression above runs at 5, where one
# stuck pending slot cannot be observed at all.
#
# The release failure is NOT mocked. A second connection holds a real
# BEGIN IMMEDIATE across teardown, which is the production shape — the host
# still holding SQLite's single write lock, because Flask runs blueprint
# teardowns before app teardowns — and it makes the collision deterministic
# instead of the "pending in (0, 1)" the older test had to allow.
import sqlite3

import skribl.ratelimit as _rl3

_F2_POSTS = "SELECT COUNT(*) FROM skribl_rate_events WHERE bucket='posts'"


def _f2_app(name, cap=1):
    """A capped host on its own SQLite file, with an armable commit failure
    that grabs the write lock on its way out."""
    os.environ["SKRIBL_RATE_HMAC_KEY"] = "txcontract-f2-" + name
    app = Flask("f2-" + name)
    path = f"{tempfile.mkdtemp()}/{name}.db"
    app.config.update(SQLALCHEMY_DATABASE_URI=f"sqlite:///{path}",
                      SECRET_KEY="harness-f2", SKRIBL_RATE_BACKEND="db",
                      SKRIBL_RATE_MAX_POSTS=cap, SKRIBL_RATE_MAX_ATTEMPTS=500)
    db = SQLAlchemy()
    db.init_app(app)
    skribl.init_skribl(app, session=lambda: db.session)
    skribl.models.attach_to_metadata(db.metadata)
    with app.app_context():
        db.create_all()
    state = {"armed": False, "lock": None}

    @app.after_request
    def _commit(resp):
        if resp.status_code < 500:
            if state["armed"]:
                state["armed"] = False
                # Take the write lock the way an un-rolled-back host does and
                # hold it THROUGH teardown, so the limiter's release is a
                # genuine SQLITE_BUSY against a real second writer.
                lk = sqlite3.connect(path, timeout=0)
                lk.isolation_level = None
                lk.execute("BEGIN IMMEDIATE")
                state["lock"] = lk
                raise RuntimeError("injected host commit failure")
            db.session.commit()
        return resp

    @app.teardown_request
    def _rollback(exc):
        db.session.rollback()

    def unlock():
        if state["lock"] is not None:
            state["lock"].execute("ROLLBACK")
            state["lock"].close()
            state["lock"] = None

    return app, db, state, unlock


def _f2_count(app, db, sql):
    with app.app_context():
        db.session.rollback()
        return db.session.execute(sa.text(sql)).scalar()


_a, _adb, _ast, _aunlock = _f2_app("fix")
_ast["armed"] = True
_t0 = _time.monotonic()
r = _a.test_client().post("/api/skribls", json={"frames": [FRAME]})
_f2_elapsed = _time.monotonic() - _t0
check("F2 setup: the injected host commit failure returns 5xx",
      r.status_code >= 500, str(r.status_code))
check("F2 setup: the contended release fails FAST, not on pysqlite's 5 s "
      "default", _f2_elapsed < 4, f"{_f2_elapsed:.2f}s")
_f2_stranded = _f2_count(_a, _adb, _F2_POSTS)
check("F2 setup: the release genuinely could not be delivered — the row is "
      "still physically there, so this tests the real collision",
      _f2_stranded == 1, f"{_f2_stranded} rows")
_aunlock()
r = _a.test_client().post("/api/skribls", json={"frames": [FRAME]})
check("THE CONTRACT: an immediate retry after a failed post is NOT rate "
      "limited, at SKRIBL_RATE_MAX_POSTS=1", r.status_code == 201,
      str(r.status_code))
check("the dead reservation was SWEPT by that retry, not merely hidden from "
      "the count", _f2_count(_a, _adb, _F2_POSTS) == 1,
      f"{_f2_count(_a, _adb, _F2_POSTS)} post rows remain")
check("...and the surviving row is the retry's committed reservation, so the "
      "sweep deleted the dead row and not a live one",
      _f2_count(_a, _adb, _F2_POSTS + " AND state='committed'") == 1,
      "the survivor is not a committed reservation")

# Mutation pin. Same sequence, but the in-memory release record is dropped
# before the retry — which is exactly the v208 behaviour. If this check ever
# goes green, the contract check above has stopped proving anything.
_b, _bdb, _bst, _bunlock = _f2_app("counterexample")
_bst["armed"] = True
r = _b.test_client().post("/api/skribls", json={"frames": [FRAME]})
check("counterexample setup: the host commit failed", r.status_code >= 500,
      str(r.status_code))
_bunlock()
with _b.app_context():
    _rl3._tombstone_store(_bdb.engine).clear()
    # v211: the release is now ALSO journaled to a sidecar file, so dropping
    # memory alone no longer reproduces v208 — the journal rescues the retry
    # (which is the point of it). The counterexample must drop both.
    _jp = _rl3._journal_path(_bdb.engine)
    if _jp and os.path.exists(_jp):
        os.remove(_jp)
_rl3._rate_tombstones.clear()
r = _b.test_client().post("/api/skribls", json={"frames": [FRAME]})
check("COUNTEREXAMPLE: with the release record dropped (memory AND journal), the "
      "stranded pending row DOES limit the retry — so the contract check is real",
      r.status_code == 429, str(r.status_code))

# ---- v211 (v210 review F3, option A): the release must survive a PROCESS
# BOUNDARY on SQLite. Two regressions the reviewer specified, in the shape
# that actually discriminates:
#  (1) RESTART — failure + release in "process 1"; discard ALL process-local
#      state (tombstones, sessionmakers); build a fresh app on the SAME file
#      as "process 2"; immediate retry must be accepted.
#  (2) SECOND WORKER — two live apps on the same file at once; A fails, B
#      retries immediately, never having seen A's memory.
# Both are REAL process-local-state boundaries, not a mock of one: the
# module-level caches are wiped and the sidecar journal is the only thing
# that can carry the release across. Mutation: delete the journal between
# the two halves and both must fail.
print("\nF3 (v211) — the SQLite release survives a process boundary via the sidecar journal")


def _f3_fresh_app(path, name):
    os.environ["SKRIBL_RATE_HMAC_KEY"] = "txcontract-f3pb"
    app = Flask("f3pb-" + name)
    app.config.update(SQLALCHEMY_DATABASE_URI=f"sqlite:///{path}",
                      SECRET_KEY="harness-f3pb", SKRIBL_RATE_BACKEND="db",
                      SKRIBL_RATE_MAX_POSTS=1, SKRIBL_RATE_MAX_ATTEMPTS=500)
    db = SQLAlchemy()
    db.init_app(app)
    skribl.init_skribl(app, session=lambda: db.session)
    skribl.models.attach_to_metadata(db.metadata)
    with app.app_context():
        db.create_all()
    state = {"armed": False, "lock": None}

    @app.after_request
    def _commit(resp):
        if resp.status_code < 500:
            if state["armed"]:
                state["armed"] = False
                lk = sqlite3.connect(path, timeout=0)
                lk.isolation_level = None
                lk.execute("BEGIN IMMEDIATE")
                state["lock"] = lk
                raise RuntimeError("injected host commit failure")
            db.session.commit()
        return resp

    @app.teardown_request
    def _rollback(exc):
        db.session.rollback()

    def unlock():
        if state["lock"] is not None:
            state["lock"].execute("ROLLBACK"); state["lock"].close(); state["lock"] = None

    return app, db, state, unlock


def _forget_process_state():
    """Everything process-local the limiter holds: the memory tombstones and
    the per-engine sessionmakers (which also drop the bounded engines). This
    is what a restart forgets."""
    _rl3._rate_tombstones.clear()
    try:
        _rl3._rate_sessionmakers.clear()
    except Exception:
        pass


# (1) RESTART
_pb_path = f"{tempfile.mkdtemp()}/f3pb.db"
_p1, _p1db, _p1st, _p1unlock = _f3_fresh_app(_pb_path, "proc1")
_p1st["armed"] = True
r = _p1.test_client().post("/api/skribls", json={"frames": [FRAME]})
check("F3 restart setup: process 1's post failed (host commit, lock held)", r.status_code >= 500, str(r.status_code))
_p1unlock()
with _p1.app_context():
    _jpath = _rl3._journal_path(_p1db.engine)
check("F3 restart setup: the release was JOURNALED to the sidecar file",
      _jpath is not None and os.path.exists(_jpath) and os.path.getsize(_jpath) > 0,
      f"journal {_jpath} missing or empty")
with _p1.app_context():
    _stranded = _p1db.session.execute(sa.text(_F2_POSTS + " AND state='pending'")).scalar()
check("F3 restart setup: the stranded pending row is physically in the DB", _stranded == 1, f"{_stranded} pending")
# "restart": forget everything process-local, bring up a fresh app on the same file
_forget_process_state()
_p2, _p2db, _p2st, _p2unlock = _f3_fresh_app(_pb_path, "proc2")
r = _p2.test_client().post("/api/skribls", json={"frames": [FRAME]})
check("F3 RESTART: a fresh process on the same file accepts the immediate retry — the "
      "journaled release is honoured at cap 1", r.status_code == 201, str(r.status_code))
with _p2.app_context():
    _after = _p2db.session.execute(sa.text(_F2_POSTS + " AND state='pending'")).scalar()
check("F3 RESTART: ...and process 2's reservation SWEPT the stranded row while it held a writer",
      _after == 0, f"{_after} pending rows remain")
check("F3 RESTART: ...and truncated the journal once applied",
      (not os.path.exists(_jpath)) or os.path.getsize(_jpath) == 0, "journal still has entries")

# (2) SECOND WORKER (two live apps, same file, at once)
_pb2 = f"{tempfile.mkdtemp()}/f3pb2.db"
_wa, _wadb, _wast, _waunlock = _f3_fresh_app(_pb2, "workerA")
_wb, _wbdb, _wbst, _wbunlock = _f3_fresh_app(_pb2, "workerB")
_wb.test_client().get("/skribl-pad")         # B is live before A fails
_wast["armed"] = True
r = _wa.test_client().post("/api/skribls", json={"frames": [FRAME]})
check("F3 two-worker setup: worker A's post failed", r.status_code >= 500, str(r.status_code))
_waunlock()
# B must not see A's memory tombstone: A's store is app-local (ext), so B's
# app genuinely does not have it. The journal is the only channel.
r = _wb.test_client().post("/api/skribls", json={"frames": [FRAME]})
check("F3 TWO WORKERS: worker B accepts the immediate retry — it never had A's memory; "
      "only the sidecar journal could have told it", r.status_code == 201, str(r.status_code))

# MUTATION of the channel: delete the journal between failure and retry.
_pb3 = f"{tempfile.mkdtemp()}/f3pb3.db"
_ma, _madb, _mast, _maunlock = _f3_fresh_app(_pb3, "mutA")
_mb, _mbdb, _mbst, _mbunlock = _f3_fresh_app(_pb3, "mutB")
_mast["armed"] = True
_ma.test_client().post("/api/skribls", json={"frames": [FRAME]})
_maunlock()
with _ma.app_context():
    _jp3 = _rl3._journal_path(_madb.engine)
if _jp3 and os.path.exists(_jp3):
    os.remove(_jp3)
r = _mb.test_client().post("/api/skribls", json={"frames": [FRAME]})
check("F3 COUNTEREXAMPLE: with the journal deleted, worker B DOES count A's stranded row "
      "(429) — so the journal is the thing carrying the guarantee, not luck",
      r.status_code == 429, str(r.status_code))
del os.environ["SKRIBL_RATE_HMAC_KEY"]

# SQLite reuses rowids, so an id-keyed tombstone whose row was deleted by
# someone else could exempt a later, innocent reservation. The design rests on
# _sweep_tombstones being the only deleter that can touch a tombstoned row,
# and on it dropping the tombstone in the same breath. Pinned here because
# whoever adds the next deleter will read this file, not that comment.
_f2_src = (ROOT / "skribl" / "ratelimit.py").read_text()
check("the sweep drops the tombstone for every row it deletes (rowid reuse)",
      "store.pop(tok, None)" in _f2_src, "the sweep no longer clears the store")
check("a release that SUCCEEDS records no tombstone — one add site only",
      _f2_src.count("_tombstone_add(token)") == 1,
      "tombstones are added on more than one path")

# A failed SWEEP must not escape either. verify_review already pins that the
# stale-row janitor cannot take a request down with it, and it caught exactly
# that bug in the first draft of _sweep_tombstones — RATE_CLEANUP_BATCH was
# read OUTSIDE the guard, and by the time the sweep runs the reservation is
# already committed, so an escape strands the very row it came to collect.
# What that pin does not check is the property F2 depends on: when the sweep
# fails the tombstone must SURVIVE, or the row starts counting again and this
# finding quietly reopens.
class _F2Poison:
    def __index__(self):
        raise RuntimeError("injected sweep failure")


# Cap 2, deliberately: at cap 1 the retry itself consumes the only slot, so a
# third post is limited whether or not the tombstone survived and the check
# discriminates nothing. At 2 the third post succeeds ONLY if the stranded row
# is still uncounted.
_c, _cdb, _cst, _cunlock = _f2_app("sweepfail", cap=2)
_cst["armed"] = True
_c.test_client().post("/api/skribls", json={"frames": [FRAME]})
_cunlock()
_f2_batch = _rl3.RATE_CLEANUP_BATCH
_rl3.RATE_CLEANUP_BATCH = _F2Poison()
try:
    r = _c.test_client().post("/api/skribls", json={"frames": [FRAME]})
finally:
    _rl3.RATE_CLEANUP_BATCH = _f2_batch
check("a failing sweep is CONTAINED — the retry still succeeds",
      r.status_code == 201, str(r.status_code))
_f2_pend = _f2_count(_c, _cdb, _F2_POSTS + " AND state='pending'")
check("...and the dead row is still on disk, since the sweep is what deletes it",
      _f2_pend == 1, f"{_f2_pend} pending")
r = _c.test_client().post("/api/skribls", json={"frames": [FRAME]})
check("...but the RELEASE survived the failed sweep — the stranded row is "
      "still uncounted, so this post is not limited", r.status_code == 201,
      str(r.status_code))
_f2_pend = _f2_count(_c, _cdb, _F2_POSTS + " AND state='pending'")
check("and the next writer collects what the failed sweep left behind — no "
      "pending rows survive it", _f2_pend == 0, f"{_f2_pend} pending")
del os.environ["SKRIBL_RATE_HMAC_KEY"]

print("\nCOEXISTENCE — a host with its own BEGIN recipe still works")
# v202 review, F3: a pre-existing host BEGIN listener must coexist (the
# recognised double-BEGIN shape is tolerated), and Skribl on an AUTOCOMMIT
# engine must refuse loudly rather than contradict the host's choice.
coex = Flask("begin-coexist-host")
_ctmp = tempfile.mkdtemp()
coex.config.update(SQLALCHEMY_DATABASE_URI=f"sqlite:///{_ctmp}/coex.db",
                   SECRET_KEY="harness-coex")
coexdb = SQLAlchemy()
coexdb.init_app(coex)
with coex.app_context():
    _ceng = coexdb.engine
import sqlalchemy as _sa2


@_sa2.event.listens_for(_ceng, "connect")
def _host_iso(dbapi_conn, rec):
    dbapi_conn.isolation_level = None


@_sa2.event.listens_for(_ceng, "begin")
def _host_begin(conn):
    conn.exec_driver_sql("BEGIN")


skribl.init_skribl(coex, session=lambda: coexdb.session)
skribl.models.attach_to_metadata(coexdb.metadata)


@coex.after_request
def _ccommit(resp):
    if resp.status_code < 500:
        coexdb.session.commit()
    return resp


@coex.teardown_request
def _crollback(exc):
    coexdb.session.rollback()


with coex.app_context():
    coexdb.create_all()
r = coex.test_client().post("/api/skribls", json={"frames": [FRAME]})
check("posting through a host with its own BEGIN recipe works",
      r.status_code == 201, str(r.status_code))

print("\nSTANDALONE — app.py owns the per-request commit")
# The other half of the contract. Removing the routes' commits without giving
# app.py one would make every standalone post vanish at request end; this is
# the assertion that catches that half-fix.
_sa_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_sa_tmp}/standalone.db"
os.environ.setdefault("SECRET_KEY", "harness-txcontract-standalone")
A = importlib.import_module("app")
standalone = A.create_app()
with standalone.app_context():
    A.db.create_all()
r = standalone.test_client().post("/api/skribls", json={"frames": [FRAME]})
check("standalone post succeeds", r.status_code == 201, str(r.status_code))
pid = (r.get_json() or {}).get("id")
with A.create_app().app_context():
    row = (A.db.session.query(skribl.models.SkriblPost)
           .filter_by(public_id=pid).first())
    check("and is durable across app contexts — app.py committed it",
          row is not None)

# ---- v208 (v207 review F1): the AUTOCOMMIT refusal, against a REAL engine ----
# The v202/v203 guard checked `dialect.isolation_level`, which SQLAlchemy 2.x
# leaves None for `create_engine(..., isolation_level="AUTOCOMMIT")` — the
# configured mode lives on `dialect._on_connect_isolation_level`. So the guard
# never fired against the exact configuration it was written to refuse. The
# earlier "AUTOCOMMIT" regression built a host with its own explicit-BEGIN
# listener, which is a different shape and never exercised this. Build the real
# thing (no faked attributes) and assert the documented RuntimeError.
print("\nAUTOCOMMIT — a REAL create_engine(isolation_level='AUTOCOMMIT') is refused")
import sqlalchemy as _sa
_ac = _sa.create_engine("sqlite:///:memory:", isolation_level="AUTOCOMMIT")
check("SQLAlchemy reports the AUTOCOMMIT request where the guard must look",
      str(getattr(_ac.dialect, "_on_connect_isolation_level", None)).upper() == "AUTOCOMMIT",
      f"dialect.isolation_level={getattr(_ac.dialect, 'isolation_level', None)!r} "
      f"_on_connect_isolation_level={getattr(_ac.dialect, '_on_connect_isolation_level', None)!r}")
_refused = False
try:
    skribl.models._install_sqlite_fk(_ac)
except RuntimeError as _e:
    _refused = "AUTOCOMMIT" in str(_e)
check("Skribl REFUSES a real AUTOCOMMIT SQLite engine with the documented RuntimeError", _refused,
      "the guard installed its transaction listeners on an autocommit engine")
_ok_engine = _sa.create_engine("sqlite:///:memory:")
check("...and still accepts a default (transactional) SQLite engine",
      skribl.models._install_sqlite_fk(_ok_engine) is True)

# v209 review F3: the refusal must not CONTAMINATE the installed-engine
# registry. The engine used to be added to _FK_ENGINES BEFORE the AUTOCOMMIT
# check raised, so a refused engine was recorded as installed — and any later
# call for the same object returned False silently with no listener attached:
# a SQLite engine running with neither the FK pragma nor the explicit-BEGIN
# recipe, the exact state the guard exists to prevent.
check("F3: a REFUSED engine is not recorded as installed",
      _ac not in skribl.models._FK_ENGINES,
      "the refused AUTOCOMMIT engine sits in _FK_ENGINES")
_refused_again = False
try:
    skribl.models._install_sqlite_fk(_ac)
except RuntimeError:
    _refused_again = True
check("F3: ...so a second attempt is refused again, not silently skipped",
      _refused_again, "the second call returned instead of raising")
check("F3: while an ACCEPTED engine IS recorded (idempotence intact)",
      _ok_engine in skribl.models._FK_ENGINES
      and skribl.models._install_sqlite_fk(_ok_engine) is False)

# v211 (v210 review F4): registration must be the LAST step of a SUCCESSFUL
# install. The v209 fix moved _FK_ENGINES.add past the AUTOCOMMIT refusal, but
# it still sat BEFORE the two listener registrations; if either registration
# raised, the engine stayed recorded as installed and every later call
# returned False — no pragma, no BEGIN recipe, silently. The v209 pin only
# attacked the refusal path (which happens before the add), so it generalised
# one exception point to the whole installation. Attack a listener
# registration instead.
print("\nF4 — a failing listener registration must not leave the engine recorded")
# models.py resolves `event.listens_for` at call time through its own imported
# `event` module object, so that is the name to patch (patching
# sqlalchemy.event.listen missed: listens_for is a separate factory).
_f4_eng = _sa.create_engine("sqlite:///:memory:")
_ev = skribl.models.event
_orig_lf = _ev.listens_for
_calls = {"n": 0}
def _boom_lf(target, identifier, *a, **kw):
    _calls["n"] += 1
    if _calls["n"] == 2:                      # first listener attaches; second registration raises
        raise RuntimeError("injected listener registration failure")
    return _orig_lf(target, identifier, *a, **kw)
_ev.listens_for = _boom_lf
try:
    _raised = False
    try:
        skribl.models._install_sqlite_fk(_f4_eng)
    except RuntimeError as e:
        _raised = "injected" in str(e)
finally:
    _ev.listens_for = _orig_lf
check("F4 setup: the second listener registration really raised", _raised)
check("F4: the engine is NOT recorded as installed after a partial install",
      _f4_eng not in skribl.models._FK_ENGINES, "engine sits in _FK_ENGINES with only one listener")
check("F4: ...so a retry actually installs (returns True), not 'already done'",
      skribl.models._install_sqlite_fk(_f4_eng) is True,
      "retry returned False — the partial install was recorded as complete")

# v209 review F4: the limiter's busy_timeout must survive a mid-session
# COMMIT. _bounded() used to run one PRAGMA on whichever connection the
# session held at that instant; the reserve path commits twice, and after a
# commit SQLAlchemy may hand the session a DIFFERENT pooled connection whose
# timeout is pysqlite's 5 s default. Read the timeout back on the connection
# actually in use after the commit — that is what the second write pays.
print("\nF4 — busy_timeout is bounded on the connection in use AFTER a commit")
import skribl.ratelimit as _rl4
_f4_eng = _sa.create_engine(f"sqlite:///{tempfile.mkdtemp()}/f4.db",
                            poolclass=_sa.pool.QueuePool, pool_size=3)
_f4_sm = _sa.orm.sessionmaker(bind=_f4_eng)
with _f4_sm() as _s:
    _rl4._bounded(_s)
    _first = _s.connection().exec_driver_sql("PRAGMA busy_timeout").scalar()
    _s.commit()
    # Force the pool to hand back a different DBAPI connection: check out a
    # second one on the side so the first cannot simply be reused.
    _side = _f4_eng.raw_connection()
    _second = _s.connection().exec_driver_sql("PRAGMA busy_timeout").scalar()
    _side.close()
check("F4 setup: the first statement group is bounded", _first == 200, str(_first))
check("F4: the connection in use AFTER a commit is bounded too — the second "
      "write does not pay pysqlite's 5 s default", _second == 200,
      f"busy_timeout={_second} on the post-commit connection")
with _f4_sm() as _s2:
    _fresh = _s2.connection().exec_driver_sql("PRAGMA busy_timeout").scalar()
check("F4: any later session on the same engine is bounded without calling "
      "_bounded() at all (engine-level, cannot be forgotten)",
      _fresh == 200, str(_fresh))

bad = [(n, d) for ok, n, d in results if not ok]
print("\n" + "=" * 62)
print(f"{len(results) - len(bad)}/{len(results)} passed"
      + (("  FAILURES: " + "; ".join(f"{n} ({d})" for n, d in bad)) if bad else ""))
sys.exit(1 if bad else 0)
