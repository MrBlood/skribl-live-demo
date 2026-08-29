#!/usr/bin/env python3
"""Skribl as a DROP-IN: mount it in a bare host app and hold it to its contract.

Every other suite drives the standalone demo, where Skribl IS the application.
That configuration cannot see the failures an integrator hits, because in it
there is no host to collide with: no host homepage to shadow, no host metadata
to attach to, no host policy to consult. This suite builds a throwaway Flask
application that is NOT app.py and checks the seams from the outside.

It found the homepage collision: the blueprint registered `GET /`
unconditionally, Flask resolves duplicate rules by registration order, the
blueprint is registered first, and so mounting Skribl silently replaced the
host's front page with a drawing editor. No error, no warning.

Runs in-process with Flask's test client — no server, no browser, so it is
fast and has no port to collide on.
"""
import sys
from pathlib import Path

# Same idiom as verify_migrations.py: the suite imports the package under test.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

results = []


def check(name, ok, detail=""):
    results.append((bool(ok), name))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  — {detail}" if detail else ""))


try:
    from flask import Flask
    from flask_sqlalchemy import SQLAlchemy
except ImportError:
    print("SKIP: Flask/flask_sqlalchemy not installed")
    sys.exit(77)

import skribl
import skribl.models


def host_app(**kw):
    """A pretend third-party site. Deliberately NOT app.py."""
    app = Flask(__name__)
    app.config.update(SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
                      SECRET_KEY="host-secret")
    db = SQLAlchemy(app)
    skribl.models.attach_to_metadata(db.metadata)
    skribl.init_skribl(app, session=lambda: db.session, **kw)

    @app.route("/")
    def home():
        return "HOST HOMEPAGE"

    # Host-owned per-request commit, per the contract. This pretend host never
    # committed and still passed — pysqlite's fake savepoints were committing
    # at RELEASE. With v202's real transactions the flushed post evaporates at
    # teardown unless the HOST commits, which is the entire contract.
    @app.after_request
    def _commit(resp):
        if resp.status_code < 500:
            db.session.commit()
        return resp

    @app.teardown_request
    def _rollback(exc):
        db.session.rollback()

    with app.app_context():
        db.create_all()
    return app, db


def strokes(n=20):
    return [{"x": 10 + i, "y": 20 + i, "t": i * 16, "size": 5,
             "color": "#111111", "down": i > 0} for i in range(n)]


def payload(title="t", visibility="public"):
    s = strokes()
    return {"title": title, "caption": "", "visibility": visibility,
            "canvas": {"w": 816, "h": 612}, "strokes": s,
            "strokeGroups": [len(s)],
            "frames": [{"strokes": s, "strokeGroups": [len(s)], "hold": 1}]}


print("INTEGRATION — mounting into a host application")

# THE REGRESSION THIS SUITE EXISTS FOR.
app, db = host_app()
c = app.test_client()
body = c.get("/").get_data(as_text=True)
check("mounting Skribl does not steal the host's homepage",
      "HOST HOMEPAGE" in body,
      f"GET / returned {body[:60]!r} — the blueprint used to register `/` "
      "unconditionally and win on registration order")

check("and Skribl's own pages are still reachable",
      c.get("/skribl-pad").status_code == 200 and c.get("/flip").status_code == 200)

# The opt-in still works, because the standalone demo depends on it.
app2, _ = host_app(index_route=True)
check("index_route=True still puts Skribl at the root for a standalone site",
      app2.test_client().get("/").status_code == 200
      and "HOST HOMEPAGE" not in app2.test_client().get("/").get_data(as_text=True))

# A prefix must namespace EVERY route, including generated share links — a
# share URL built from a root literal is wrong the moment Skribl is mounted
# under a prefix, and the client trusts that value.
app3, _ = host_app(url_prefix="/skribl")
c3 = app3.test_client()
check("a url_prefix namespaces every route",
      c3.get("/skribl/skribl-pad").status_code == 200
      and c3.get("/skribl-pad").status_code == 404)
r = c3.post("/skribl/api/skribls", json=payload())
url = r.get_json().get("url", "") if r.status_code == 201 else ""
check("and the share URL it returns respects the prefix",
      r.status_code == 201 and url.startswith("/skribl/s/"),
      f"returned {url!r}")
check("and that share URL actually resolves",
      bool(url) and c3.get(url).status_code == 200)

print("\nINTEGRATION — the host owns the schema")
# attach_to_metadata is the ONLY thing that makes a host's db.create_all() see
# Skribl's tables; without it the integrator gets zero tables and no error.
bare = Flask(__name__)
bare.config.update(SQLALCHEMY_DATABASE_URI="sqlite:///:memory:", SECRET_KEY="k")
bare_db = SQLAlchemy(bare)
skribl.init_skribl(bare, session=lambda: bare_db.session)
with bare.app_context():
    bare_db.create_all()
    from sqlalchemy import inspect
    without = set(inspect(bare_db.engine).get_table_names())
with app.app_context():
    from sqlalchemy import inspect as _i
    with_attach = set(_i(db.engine).get_table_names())
check("attach_to_metadata is what puts Skribl's tables in the host's metadata",
      not (without & {"skribl_posts"}) and {"skribl_posts", "skribl_post_media",
                                            "skribl_rate_events"} <= with_attach,
      f"without={sorted(without)}, with={sorted(with_attach)} — an integrator "
      "who skips it gets no tables and no error, so this must stay documented")

print("\nINTEGRATION — the host owns identity and visibility")
CURRENT = {"id": 42}
# csrf=False: this pretend host reads its viewer out of a dict, not a cookie.
# v224 requires that be declared rather than assumed (outside review #4).
app4, db4 = host_app(url_prefix="/s", current_user_id=lambda: CURRENT["id"],
                     csrf=False)
c4 = app4.test_client()
pid = c4.post("/s/api/skribls", json=payload("owned")).get_json()["id"]
with app4.app_context():
    owner = db4.session.execute(
        db4.text("select user_id from skribl_posts")).first()[0]
check("current_user_id decides authorship", owner == 42, f"stored user_id={owner}")

# A policy that is never consulted passes every test that only checks the
# default, so install one, prove it changes the outcome, then clear it.
skribl.set_visibility_policy(lambda post, viewer: post.user_id == viewer)
try:
    CURRENT["id"] = 99
    api = c4.get(f"/s/api/skribls/{pid}")
    check("a host visibility policy is enforced on the payload endpoint",
          api.status_code == 404,
          f"HTTP {api.status_code} — the payload is the content; a policy that "
          "does not reach here is decoration")
    card = c4.get(f"/s/s/{pid}/card.png")
    check("and on the share card, which IS the drawing",
          card.status_code in (302, 404), f"HTTP {card.status_code}")

    # DECLARED LIMITATION, pinned so it cannot change silently. The feed
    # filters visibility == 'public' in SQL and never calls visible_to():
    # running a Python policy over a keyset-paginated query would break the
    # pagination. Metadata (title, author, timestamp) can therefore be listed
    # for a post the policy refuses to serve. No payload leaks.
    items = c4.get("/s/api/skribls").get_json()["items"]
    check("DECLARED: the feed lists by visibility only, not by policy",
          len(items) == 1 and all("payload" not in i and "strokes" not in i
                                  for i in items),
          "metadata for a policy-refused post is listed; the payload is not. "
          "If this ever needs to change it needs a feed_filter seam, not a "
          "Python filter over a paginated query")
finally:
    skribl.set_visibility_policy(None)

CURRENT["id"] = 99
check("clearing the policy restores the built-in rules",
      c4.get(f"/s/api/skribls/{pid}").status_code == 200,
      "a public post is readable again once the host policy is removed")

print("\nINTEGRATION — the contract refuses to be used wrongly")
try:
    skribl.create_blueprint()
    check("a missing session fails at startup", False, "it was accepted")
except ValueError:
    check("a missing session fails at startup, not at query time", True)
try:
    skribl.set_visibility_policy("not callable")
    check("a non-callable policy is refused at install time", False)
except TypeError:
    check("a non-callable policy is refused at install time, not per request", True)
finally:
    skribl.set_visibility_policy(None)

bad = [r for r in results if not r[0]]
print("\n" + "=" * 62)
print(f"{len(results) - len(bad)}/{len(results)} passed"
      + ("" if not bad else "  FAILURES: " + ", ".join(r[1] for r in bad)))
sys.exit(1 if bad else 0)
