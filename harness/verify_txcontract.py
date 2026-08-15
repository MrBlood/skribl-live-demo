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

print("\nTRIPWIRE — auth configured without CSRF logs a warning")
import logging


class _Trap(logging.Handler):
    def __init__(self):
        super().__init__()
        self.hits = []

    def emit(self, record):
        self.hits.append(record.getMessage())


_trap = _Trap()
logging.getLogger("skribl").addHandler(_trap)
try:
    skribl.create_blueprint(session=False, current_user_id=lambda: 7)
    check("current_user_id without csrf trips the warning",
          any("csrf" in m.lower() for m in _trap.hits), str(_trap.hits[:1]))
    _trap.hits.clear()
    skribl.create_blueprint(session=False, current_user_id=lambda: 7,
                            csrf=("h", lambda: "t", lambda _r: True))
    check("supplying a csrf verifier silences it", not _trap.hits,
          str(_trap.hits[:1]))
finally:
    logging.getLogger("skribl").removeHandler(_trap)

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

bad = [(n, d) for ok, n, d in results if not ok]
print("\n" + "=" * 62)
print(f"{len(results) - len(bad)}/{len(results)} passed"
      + (("  FAILURES: " + "; ".join(f"{n} ({d})" for n, d in bad)) if bad else ""))
sys.exit(1 if bad else 0)
