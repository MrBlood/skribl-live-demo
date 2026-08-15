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
