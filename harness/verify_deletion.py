"""skribl.delete_post() / set_post_visibility(): taking a Skribl back.

WHAT THIS IS FOR. An external review of v277 found the API "supports creation
and reading but no obvious delete, archive, revoke, or visibility-update
operation for an already published Skribl". `verify_deletion_foundation.py`
already proves the layer UNDERNEATH — cascade, media unreachability, orphan
sweep — on PostgreSQL, and its docstring says the product operation on top "has
never been executed". This suite is that operation.

THE THREE THINGS WORTH ASSERTING, in the order they can hurt:

  1. AUTHORISATION HAPPENS, AND DISCLOSES NOTHING. A post that does not exist
     and a post belonging to somebody else must be indistinguishable, or the
     endpoint is an oracle for which public ids are real and who owns them.
     Asserted on the EXCEPTION TYPE, the MESSAGE and the HTTP STATUS, because
     any one of the three leaking is the whole leak.

  2. THE DESTRUCTIVE ROUTES DO NOT EXIST WITHOUT AN IDENTITY. Skribl's API is
     unauthenticated by default (DECISIONS #2) and every other route is safe
     under that because the worst a stranger can do is create or read. A DELETE
     on an unauthenticated API erases anything anyone can name. Section 4 asks
     Flask's url_map, not the source, because what ships is the routing table.

  3. IT LEAVES NOTHING BEHIND, WITH THE CASCADE TURNED OFF. The first version
     of this section deleted a post and checked the association rows were gone,
     and PASSED with delete_post's explicit cleanup removed — because
     `init_skribl` installs `enable_sqlite_foreign_keys()` and the declared
     ON DELETE CASCADE fired. It was measuring the pragma hook.
     The explicit delete exists for the paths that MISS that hook: a host
     registering the blueprint directly, or SKRIBL_SQLITE_FOREIGN_KEYS=0. So
     the section now switches `PRAGMA foreign_keys=OFF` on the connection first,
     which is the configuration where relying on the cascade leaves the rows —
     and a left-behind association makes `sweep_orphans` count the media as
     still referenced, so the bytes are never collected.

TRANSACTIONS, as in verify_createpost.py: these functions flush and never
commit, so section 5 checks that a host can still roll the whole thing back.

MUTATION-TESTED. Every section was run against a deliberately broken tree
before being trusted; what each mutation kills is recorded at the section.
"""
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


import sqlalchemy as sa
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

import skribl
import skribl.models
from skribl import (SkriblNotFound, SkriblRefused, create_post, delete_post,
                    set_post_visibility)
from skribl.models import SkriblPost, SkriblPostMedia

_tmp = tempfile.mkdtemp()
_url = f"sqlite:///{_tmp}/deletion.db"

host = Flask(__name__)
host.config["SQLALCHEMY_DATABASE_URI"] = _url
host.config["SECRET_KEY"] = "harness-deletion"
db = SQLAlchemy()
db.init_app(host)
_CURRENT_USER = [None]
# csrf=False for the same reason verify_createpost.py gives: this harness host
# authenticates by a variable rather than a cookie, and the blueprint refuses
# to start unless the choice is made explicitly.
skribl.init_skribl(host, session=lambda: db.session,
                   current_user_id=lambda: _CURRENT_USER[0],
                   csrf=False)
skribl.models.attach_to_metadata(db.metadata)

FRAME = {"strokes": [], "strokeGroups": [], "background": {"color": "#101418"}}


def payload(**over):
    p = {"frames": [dict(FRAME)]}
    p.update(over)
    return p


def make(author, title="t", visibility="public"):
    """A committed post owned by `author`. Returns its public id."""
    made = create_post(payload(title=title, visibility=visibility),
                       author_id=author)
    db.session.commit()
    return made.public_id


with host.app_context():
    db.create_all()

    # ---------------------------------------------------------------- 1
    print("\n1 — AUTHORISATION, AND THAT IT GIVES NOTHING AWAY")
    # MUTATION: raise a distinct SkriblForbidden when user_id != author_id.
    # Kills "someone else's post is refused the same way" on the exception
    # type, and section 4's 404 assertion on the status.
    mine = make(author=7, title="mine")
    theirs = make(author=99, title="theirs")

    try:
        delete_post("nosuchid00", author_id=7)
        missing = None
    except Exception as exc:
        missing = exc
    check("a post that does not exist raises SkriblNotFound",
          isinstance(missing, SkriblNotFound), repr(missing))

    try:
        delete_post(theirs, author_id=7)
        foreign = None
    except Exception as exc:
        foreign = exc
    check("somebody else's post raises the SAME exception type",
          isinstance(foreign, SkriblNotFound), repr(foreign))
    check("...with the SAME message, so the two cannot be told apart",
          missing is not None and foreign is not None
          and str(missing) == str(foreign),
          f"{str(missing)!r} vs {str(foreign)!r} — a different string here is "
          "an oracle for which public ids exist")
    check("...and the post it refused to delete is still there",
          db.session.query(SkriblPost).filter_by(public_id=theirs).count() == 1)

    # An anonymous caller is not a superuser. This is the one that would turn a
    # missing author_id into "delete anything".
    try:
        delete_post(mine, author_id=None)
        anon = None
    except Exception as exc:
        anon = exc
    check("author_id=None is refused, not treated as permission",
          isinstance(anon, SkriblNotFound), repr(anon))

    # A post with no author at all (the standalone app's own) must not become
    # claimable by whoever happens to be signed in to a host.
    orphan_post = make(author=None, title="anonymous")
    try:
        delete_post(orphan_post, author_id=7)
        claimed = None
    except Exception as exc:
        claimed = exc
    check("an author-less post cannot be claimed by an authenticated user",
          isinstance(claimed, SkriblNotFound), repr(claimed))
    check("...but require_author=False can remove it",
          delete_post(orphan_post, require_author=False) == orphan_post
          and (db.session.query(SkriblPost)
               .filter_by(public_id=orphan_post).count() == 0))
    db.session.commit()

    # ---------------------------------------------------------------- 2
    print("\n2 — DELETE REMOVES THE POST")
    # MUTATION: make delete_post return without s.delete(post). Kills both.
    gone = delete_post(mine, author_id=7)
    db.session.commit()
    check("the owner's own post deletes", gone == mine)
    check("...and it is no longer readable",
          db.session.query(SkriblPost).filter_by(public_id=mine).count() == 0)

    # ---------------------------------------------------------------- 3
    # (runs below, outside this app context — it needs a DIFFERENT app)

    # ---------------------------------------------------------------- 4
    print("\n4 — REVOKE: THE LINK STOPS WORKING, THE POST SURVIVES")
    # MUTATION: have set_post_visibility validate AFTER the lookup. Kills
    # "a bad value fails the same way for a post that is not there".
    shared = make(author=7, title="shared", visibility="unlisted")
    row = db.session.query(SkriblPost).filter_by(public_id=shared).one()
    check("an unlisted post is readable by a stranger with the link",
          row.visible_to(None) is True,
          "this is what sharing IS today, and what revoking has to undo")

    new = set_post_visibility(shared, "private", author_id=7)
    db.session.commit()
    row = db.session.query(SkriblPost).filter_by(public_id=shared).one()
    check("revoking to private is accepted", new == "private")
    check("...the stranger with the old link is now refused",
          row.visible_to(None) is False,
          "visible_to() is the single rule the payload endpoint, the player "
          "page, the card and the media route all read, so one write revokes "
          "on every surface at once")
    check("...the author can still read their own", row.visible_to(7) is True)
    check("...and the post still exists — revoke is not delete",
          db.session.query(SkriblPost).filter_by(public_id=shared).count() == 1)

    try:
        set_post_visibility(shared, "nonsense", author_id=7)
        bad = None
    except Exception as exc:
        bad = exc
    check("an unaccepted visibility value is refused", isinstance(bad, SkriblRefused),
          repr(bad))
    try:
        set_post_visibility("nosuchid00", "nonsense", author_id=7)
        bad_missing = None
    except Exception as exc:
        bad_missing = exc
    check("...and a bad value on a MISSING post fails the same way, "
          "so it cannot probe for ids",
          isinstance(bad_missing, SkriblRefused),
          f"{bad_missing!r} — validating after the lookup would answer "
          "SkriblNotFound here and SkriblRefused above, which is the oracle "
          "again in a different coat")
    try:
        set_post_visibility(theirs, "private", author_id=7)
        foreign_rev = None
    except Exception as exc:
        foreign_rev = exc
    check("somebody else's post cannot be revoked either",
          isinstance(foreign_rev, SkriblNotFound), repr(foreign_rev))
    check("...and its visibility is untouched",
          (db.session.query(SkriblPost).filter_by(public_id=theirs)
           .one().visibility) == "public",
          "a refused revoke that still wrote would be worse than one that "
          "raised nothing")

    # ---------------------------------------------------------------- 5
    print("\n5 — THE TRANSACTION IS STILL THE HOST'S")
    # MUTATION: add db.session.commit() inside delete_post. Kills both.
    doomed = make(author=7, title="rollback me")
    delete_post(doomed, author_id=7)
    check("after delete_post the removal is NOT yet durable",
          db.session.query(SkriblPost).filter_by(public_id=doomed).count() == 0,
          "the flush is visible inside the transaction")
    db.session.rollback()
    check("...so the host's rollback brings the post back",
          db.session.query(SkriblPost).filter_by(public_id=doomed).count() == 1,
          "delete_post committing on its own would make a host's abort "
          "unrecoverable — the same contract create_post keeps")


# ---------------------------------------------------------------------- 3
print("\n3 — AND TAKES ITS MEDIA ASSOCIATIONS WITH IT, WITHOUT THE CASCADE")
# WHAT THIS SECTION LOOKED LIKE FIRST, AND WHY IT WAS WORTHLESS. It deleted a
# post in the main app above, checked the association rows were gone, and
# PASSED with the explicit cleanup removed from delete_post. `init_skribl`
# installs `enable_sqlite_foreign_keys()`, so the declared ON DELETE CASCADE
# fired and did the work; the assertion was measuring the pragma hook and
# crediting it to the function under test. Only the mutation said so.
#
# The second attempt ran `PRAGMA foreign_keys=OFF` on the session's connection.
# That does not work either — the pragma is PER CONNECTION, the pool hands the
# connection back on commit, and the hook re-applies it on the next checkout.
# The assertion caught that too, which is the only reason it is not in the tree.
#
# So this runs the REAL uncovered configuration instead of simulating it: a host
# that calls create_blueprint() and register_blueprint() directly. The tree
# documents that as equivalent to init_skribl(), and it is — except that
# init_skribl is where the pragma hook is installed. On this path SQLite ignores
# the declared cascade, which is precisely where delete_post's explicit cleanup
# has to stand on its own.
#
# MUTATION: drop the explicit association delete. Kills the last assertion here
# and nothing in section 2 — which is the point of measuring it apart.
_tmp3 = tempfile.mkdtemp()
direct = Flask(__name__)
direct.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{_tmp3}/direct.db"
direct.config["SECRET_KEY"] = "harness-deletion-direct"
db3 = SQLAlchemy()
db3.init_app(direct)
_bp3 = skribl.create_blueprint(session=lambda: db3.session,
                               current_user_id=lambda: 7, csrf=False)
direct.register_blueprint(_bp3)
skribl.models.attach_to_metadata(db3.metadata)

with direct.app_context():
    db3.create_all()
    _fk = db3.session.execute(sa.text("PRAGMA foreign_keys")).scalar()
    check("registering the blueprint directly leaves SQLite's cascade OFF",
          _fk == 0,
          f"PRAGMA foreign_keys={_fk} — if this is 1 the section below proves "
          "nothing, because the database would clean up regardless. The hook "
          "lives in init_skribl(), which this app deliberately does not call")

    _made = create_post(payload(title="haspic", visibility="public"),
                        author_id=7)
    db3.session.commit()
    _row = (db3.session.query(SkriblPost)
            .filter_by(public_id=_made.public_id).one())
    db3.session.add(SkriblPostMedia(post_id=_row.id, media_key="k/deadbeef"))
    db3.session.commit()
    _pid = _row.id
    check("the fixture has an association to lose",
          db3.session.query(SkriblPostMedia).filter_by(post_id=_pid).count() == 1)

    delete_post(_made.public_id, author_id=7)
    db3.session.commit()
    _left = db3.session.query(SkriblPostMedia).filter_by(post_id=_pid).count()
    check("delete_post removes them itself, with no cascade to help it",
          _left == 0,
          f"{_left} left — an association whose post is gone authorises "
          "nothing, but it makes sweep_orphans count the media as still "
          "referenced, so the bytes are never collected: a takedown that "
          "leaves the image on disk forever")


# ---------------------------------------------------------------------- 6
print("\n6 — THE DESTRUCTIVE ROUTES DO NOT EXIST WITHOUT AN IDENTITY")
# ASKED OF THE ROUTING TABLE, NOT THE SOURCE. What ships is the url_map; a
# source grep would pass on a route registered under a condition that is always
# true. MUTATION: register them unconditionally. Kills the first two.
def _api_methods(bp):
    a = Flask(__name__)
    a.register_blueprint(bp)
    out = set()
    for rule in a.url_map.iter_rules():
        if "/api/skribls/" in rule.rule:
            out |= (rule.methods - {"HEAD", "OPTIONS"})
    return out


_anon_methods = _api_methods(skribl.create_blueprint(session=False))
_auth_methods = _api_methods(skribl.create_blueprint(
    session=False, current_user_id=lambda: 7, csrf=False))

check("an UNAUTHENTICATED deployment exposes no DELETE",
      "DELETE" not in _anon_methods,
      f"{sorted(_anon_methods)} — Skribl's API is unauthenticated by default "
      "(DECISIONS #2); a DELETE under that erases any Skribl anyone can name")
check("...and no PATCH either", "PATCH" not in _anon_methods,
      f"{sorted(_anon_methods)}")
# Gating deletion must not gate anything else. /api/skribls/<id> keeps its GET
# on both; the collection route keeps GET and POST. Measured on the collection
# separately because _api_methods above only looks at the item route.
def _collection_methods(bp):
    a = Flask(__name__)
    a.register_blueprint(bp)
    out = set()
    for rule in a.url_map.iter_rules():
        if rule.rule.endswith("/api/skribls"):
            out |= (rule.methods - {"HEAD", "OPTIONS"})
    return out


check("...and reading an unauthenticated deployment still works",
      "GET" in _anon_methods, f"item route: {sorted(_anon_methods)}")
check("...and listing and posting are untouched by the gate",
      _collection_methods(skribl.create_blueprint(session=False))
      == {"GET", "POST"},
      f"{sorted(_collection_methods(skribl.create_blueprint(session=False)))}")
check("a host that HAS authenticated its users gets DELETE",
      "DELETE" in _auth_methods, f"{sorted(_auth_methods)}")
check("...and PATCH", "PATCH" in _auth_methods, f"{sorted(_auth_methods)}")

# The Python API is always importable — a host calling it from its own view has
# already decided who is asking, which is the same split creation.py makes.
check("the Python API is available either way",
      callable(skribl.delete_post) and callable(skribl.set_post_visibility))


# ---------------------------------------------------------------------- 7
print("\n7 — OVER HTTP, THROUGH A HOST THAT OWNS ITS TRANSACTION")
# The sections above drive the Python API and read the routing table. Neither
# proves the ROUTES work, and the routes are what a host's browser will call.
# This is also the only place the 404-not-403 rule is checked as a STATUS CODE
# rather than an exception type: the disclosure the module avoids in Python can
# be reintroduced by a route that translates it helpfully.
#
# The host commits in after_request, as app.py does and as the transaction
# contract requires — the routes flush and MUST NOT commit the shared session
# (verify_txcontract.py). An earlier draft of delete_skribl did commit, and that
# gate failed it by name.
_tmp7 = tempfile.mkdtemp()
web = Flask(__name__)
web.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{_tmp7}/web.db"
web.config["SECRET_KEY"] = "harness-deletion-web"
db7 = SQLAlchemy()
db7.init_app(web)
_WHO = [7]
skribl.init_skribl(web, session=lambda: db7.session,
                   current_user_id=lambda: _WHO[0], csrf=False)
skribl.models.attach_to_metadata(db7.metadata)


@web.after_request
def _commit(resp):
    if resp.status_code < 500:
        db7.session.commit()
    return resp


@web.teardown_request
def _rollback(exc):
    db7.session.rollback()


with web.app_context():
    db7.create_all()
    _WHO[0] = 7
    mine7 = create_post(payload(title="mine", visibility="unlisted"),
                        author_id=7)
    theirs7 = create_post(payload(title="theirs", visibility="public"),
                          author_id=99)
    db7.session.commit()
    mine7, theirs7 = mine7.public_id, theirs7.public_id

client = web.test_client()

r = client.delete(f"/api/skribls/{theirs7}")
check("DELETE on somebody else's post answers 404, not 403",
      r.status_code == 404,
      f"{r.status_code} — a 403 confirms the id exists, which is the "
      "disclosure the exception type was written to avoid")
with web.app_context():
    check("...and it is still there",
          db7.session.query(SkriblPost).filter_by(public_id=theirs7).count() == 1)

r = client.delete("/api/skribls/nosuchid00")
check("DELETE on a nonexistent id answers 404 too", r.status_code == 404,
      f"{r.status_code}")

r = client.delete(f"/api/skribls/{mine7}")
check("DELETE on your own answers 204", r.status_code == 204,
      f"{r.status_code} {r.data[:120]!r}")
with web.app_context():
    check("...and the host's after_request made it durable",
          db7.session.query(SkriblPost).filter_by(public_id=mine7).count() == 0,
          "the route flushes and the HOST commits — if this is 1, the route "
          "is relying on a commit it is contractually forbidden to make")

# PATCH: revoke, and the shape of what it will accept.
r = client.patch(f"/api/skribls/{theirs7}", json={"visibility": "private"})
check("PATCH on somebody else's post answers 404", r.status_code == 404,
      f"{r.status_code}")

_WHO[0] = 99
r = client.patch(f"/api/skribls/{theirs7}", json={"visibility": "private"})
check("PATCH by the author revokes it", r.status_code == 200,
      f"{r.status_code} {r.data[:160]!r}")
check("...and answers with the new state",
      (r.get_json() or {}).get("visibility") == "private", r.data[:160])
with web.app_context():
    _row = db7.session.query(SkriblPost).filter_by(public_id=theirs7).one()
    check("...the stranger's link is dead", _row.visible_to(None) is False)
    check("...and the post survived", _row.visibility == "private")

r = client.patch(f"/api/skribls/{theirs7}", json={"visibility": "nonsense"})
check("PATCH rejects a visibility outside the accepted set",
      r.status_code == 400, f"{r.status_code}")
r = client.patch(f"/api/skribls/{theirs7}", json={"title": "sneaky"})
check("PATCH refuses to be a general-purpose editor",
      r.status_code == 400,
      f"{r.status_code} — visibility is the only field this route takes; "
      "widening it later should be a decision, not a default")
with web.app_context():
    check("...and the title it refused is unchanged",
          (db7.session.query(SkriblPost).filter_by(public_id=theirs7)
           .one().title) == "theirs")


passed = sum(1 for ok, _, _ in results if ok)
bad = [n for ok, n, _ in results if not ok]
print("\n" + "=" * 62)
print(f"{passed}/{len(results)} passed"
      + ("" if not bad else "\nFAILURES:\n  - " + "\n  - ".join(bad)))
sys.exit(1 if bad else 0)
