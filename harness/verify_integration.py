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
import json
import sys
from pathlib import Path
from assertions import make_check

# Same idiom as verify_migrations.py: the suite imports the package under test.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

results = []


check = make_check(results)


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

# THE GUIDE'S OWN EXAMPLE, RUN AS WRITTEN. docs/INTEGRATION.md opens with "The
# smallest thing that works" and calls it the whole integration; nothing ran
# it. Every host this suite builds commits in after_request, so none of them
# could see what a site copying that block got (v316, a from-scratch host
# outside the repo): POST /api/skribls answered 201, the editor said Posted!,
# and no row was ever written — the contract says the host commits, and the
# block showed no commit. The code is lifted out of the document itself, so
# the guide cannot drift from what is checked; only its database moves to a
# temporary file, and durability is read on a separate connection.
print("\nINTEGRATION — the guide's smallest example, copied verbatim, keeps a post")
import re as _re, sqlite3 as _sqlite3, tempfile as _tempfile, os as _os
_guide = (ROOT / "docs" / "INTEGRATION.md").read_text(encoding="utf-8")
_sec = _guide.split("## The smallest thing that works", 1)[1]
_m = _re.search(r"```python\n(.*?)```", _sec, _re.S)
check("the guide's smallest example is a python block under its heading", bool(_m))
if _m:
    _dbfile = _os.path.join(_tempfile.mkdtemp(), "guide.db")
    _src = _m.group(1)
    check("...and it names the database the reader will see", '"sqlite:///site.db"' in _src,
          "the substitution below would silently not happen")
    _src = _src.replace('"sqlite:///site.db"', repr("sqlite:///" + _dbfile))
    _ns = {"__name__": "guide_example"}
    exec(compile(_src, "docs/INTEGRATION.md#smallest", "exec"), _ns)
    _gc = _ns["app"].test_client()
    _r = _gc.post("/skribl/api/skribls", json=payload(title="from the guide"))
    _rows = _sqlite3.connect(_dbfile).execute("select count(*) from skribl_posts").fetchone()[0]
    check("a post made through it is still there after the request",
          _r.status_code == 201 and _rows == 1,
          f"POST {_r.status_code}, rows on a fresh connection: {_rows} — a 201 with "
          "no row is a host that never commits: the example has to show the commit")

# ...and the same block, from an EMPTY folder holding nothing but a copy of
# skribl/. The guide says that directory is the whole runtime; a template, a
# static file or a module that quietly lives elsewhere in this repository
# would pass every in-tree suite and fail the first site that vendors it.
print("\nINTEGRATION — skribl/ alone, copied into an empty project, runs the guide's example")
if _m:
    import shutil as _shutil, subprocess as _subprocess
    _proj = _tempfile.mkdtemp()
    _shutil.copytree(ROOT / "skribl", _os.path.join(_proj, "skribl"),
                     ignore=_shutil.ignore_patterns("__pycache__"))
    with open(_os.path.join(_proj, "hostapp.py"), "w", encoding="utf-8") as _f:
        _f.write(_m.group(1))
    _probe = (
        "import hostapp, json\n"
        "c = hostapp.app.test_client()\n"
        "pages = {u: c.get(u).status_code for u in ('/skribl/skribl-pad', '/skribl/flip', '/skribl/library', '/skribl/gallery', '/skribl/feed')}\n"
        "r = c.post('/skribl/api/skribls', json=" + repr(payload(title="vendored")) + ")\n"
        "url = (r.get_json() or {}).get('url', '')\n"
        "static = c.get('/skribl/static/skribl/app.js').status_code\n"
        "print(json.dumps({'pages': pages, 'post': r.status_code, 'player': c.get(url).status_code if url else None, 'static': static}))\n")
    _env = dict(_os.environ, PYTHONPATH=_proj)
    _p = _subprocess.run([sys.executable, "-c", _probe], cwd=_proj, env=_env,
                         capture_output=True, text=True, timeout=120)
    try:
        import json as _json
        _res = _json.loads(_p.stdout.strip().splitlines()[-1])
    except Exception:
        _res = None
    check("every page, a post, its player and a static file answer from the vendored copy",
          bool(_res) and all(v == 200 for v in _res["pages"].values())
          and _res["post"] == 201 and _res["player"] == 200 and _res["static"] == 200,
          str(_res) if _res else (_p.stderr.strip().splitlines() or ["no output"])[-1][:300])

# A host with Flask-WTF's CSRFProtect switched on site-wide refused every
# Skribl post with a 400 (v316, the from-scratch host): Flask-WTF checks POSTs
# before Skribl's view runs and reads only its own header names. The guide now
# carries a recipe; this runs it, lifted from the page, with CSRFProtect on.
print("\nINTEGRATION — the guide's Flask-WTF recipe: the page's token posts, no token is refused")
try:
    import flask_wtf  # noqa: F401  (harness/requirements.txt names it)
    _have_wtf = True
except ImportError:
    _have_wtf = False
check("Flask-WTF is installed, so this section runs (harness/requirements.txt)", _have_wtf)
_wsec = _guide.split("already runs Flask-WTF's `CSRFProtect`", 1)
_wm = _re.search(r"```python\n(.*?)```", _wsec[1], _re.S) if len(_wsec) == 2 else None
check("the recipe is a python block after its paragraph", bool(_wm))
if _have_wtf and _wm:
    _wapp = Flask("guide_wtf")
    _wapp.config.update(SQLALCHEMY_DATABASE_URI="sqlite:///:memory:", SECRET_KEY="host-secret")
    _wdb = SQLAlchemy(_wapp)
    skribl.models.attach_to_metadata(_wdb.metadata)
    _wns = {"app": _wapp, "db": _wdb, "skribl": skribl}
    exec(compile(_wm.group(1), "docs/INTEGRATION.md#flask-wtf", "exec"), _wns)

    @_wapp.after_request
    def _wcommit(resp):
        if resp.status_code < 500:
            _wdb.session.commit()
        return resp

    with _wapp.app_context():
        _wdb.create_all()
    _wc = _wapp.test_client()
    _page = _wc.get("/skribl/skribl-pad").get_data(as_text=True)
    _tm = _re.search(r"window\.SKRIBL_CSRF_TOKEN = (\"[^\"]*\")", _page)
    _tok = json.loads(_tm.group(1)) if _tm else ""
    check("the editor page renders Flask-WTF's token", bool(_tok), repr(_tok)[:60])
    _no = _wc.post("/skribl/api/skribls", json=payload(title="no token"))
    _yes = _wc.post("/skribl/api/skribls", json=payload(title="with token"),
                    headers={"X-Skribl-CSRF": _tok})
    check("with CSRFProtect on, a post carrying the page's token is created, one without is refused",
          _yes.status_code == 201 and _no.status_code in (400, 403),
          f"with token {_yes.status_code}, without {_no.status_code}")

# A host that sets its OWN Content-Security-Policy on every response (Flask-
# Talisman's default does, `default-src 'self'`) replaced Skribl's on Skribl's
# pages: its after_request runs after the blueprint's, and Skribl only
# setdefault()s. The editor's nonced inline scripts, inline styles and data:
# images were all blocked and nothing could be posted (v316, a from-scratch
# host). Skribl now has the last word on its OWN pages and none on the host's.
# Emulated with a plain handler rather than Talisman, registered both BEFORE
# and AFTER Skribl is mounted: which one runs last depends on that order.
print("\nINTEGRATION — Skribl's pages keep Skribl's CSP under a host that sets its own")
HOST_CSP = "default-src 'self'; object-src 'none'"
for _when in ("before", "after"):
    _capp = Flask("csp_host_" + _when)
    _capp.config.update(SQLALCHEMY_DATABASE_URI="sqlite:///:memory:", SECRET_KEY="k")
    _cdb = SQLAlchemy(_capp)
    skribl.models.attach_to_metadata(_cdb.metadata)

    def _host_csp(resp):
        resp.headers["Content-Security-Policy"] = HOST_CSP
        return resp
    if _when == "before":
        _capp.after_request(_host_csp)
    skribl.init_skribl(_capp, session=lambda: _cdb.session, url_prefix="/skribl")
    if _when == "after":
        _capp.after_request(_host_csp)

    @_capp.route("/")
    def _chome():
        return "host"
    with _capp.app_context():
        _cdb.create_all()
    _cc = _capp.test_client()
    _pr = _cc.get("/skribl/skribl-pad")
    _pcsp = _pr.headers.get("Content-Security-Policy", "")
    _nm = _re.search(r'nonce="([^"]+)"', _pr.get_data(as_text=True))
    check(f"host handler registered {_when} Skribl: the editor carries Skribl's policy, with the page's nonce",
          bool(_nm) and f"'nonce-{_nm.group(1)}'" in _pcsp and _pcsp != HOST_CSP, _pcsp[:90])
    check(f"host handler registered {_when} Skribl: the host's own page keeps the host's policy",
          _cc.get("/").headers.get("Content-Security-Policy") == HOST_CSP)

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
# Text since v279 — see docs/INTEGRATION.md. An integer host is unaffected
# everywhere except a raw read of the column, which this is.
#
# `str(owner)`, AND THE ARGUMENT IS LOAD-BEARING. v311 found this reading
# `str == "42"` -- a comparison between the builtin TYPE and a string, which is
# False forever, so the row had been unable to answer its own question since a
# comment pass stripped the `(owner)`. That pass was removing `(owner, vNNN)`
# attribution parentheticals from PROSE; here the same three characters were an
# argument list. Nothing about the host seam had broken; the instrument had.
# It is the failure CLAUDE.md names -- do not edit mechanically where prose and
# code interleave -- and the only thing that caught it was a full battery,
# because this suite is not on the pull-request gate.
check("current_user_id decides authorship", str(owner) == "42",
      f"stored user_id={owner!r}")

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
