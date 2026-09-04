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
    check("the author stamp is the id the host passed, not a guess",
          _durable("SELECT user_id FROM skribl_posts LIMIT 1") == 7,
          str(_durable("SELECT user_id FROM skribl_posts LIMIT 1")))

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

bad = [(n, d) for ok, n, d in results if not ok]
print("\n" + "=" * 62)
print(f"{len(results) - len(bad)}/{len(results)} passed"
      + (("  FAILURES: " + "; ".join(f"{n} ({d})" for n, d in bad)) if bad else ""))
sys.exit(1 if bad else 0)
