"""Private means private — on EVERY read surface, not just the feed.

This suite exists because of a shipped bug. `verify_feed.py` asserted that a
private post does not appear in the public timeline, those assertions passed, and
that was taken as proof that privacy worked. It was not. `visibility` was a
filter on ONE endpoint while three other surfaces returned private content to
anybody holding the id:

    GET /api/skribls/<id>        returned the complete payload
    GET /s/<id>                  served title + caption in the Open Graph tags
    GET /s/<id>/card.png         served the drawing's own thumbnail

The thumbnail one is the worst: it leaks the artwork itself, not merely the fact
that a post exists.

The lesson generalises, so this suite is organised by SURFACE rather than by
rule: any future read path must be added here. A rule enforced in one place is a
filter, not an access control.

Ownership note: the standalone app resolves the current user to 1 and stamps
posts with 1, so a post made here IS the viewer's own. That makes the
author-can-read case testable but NOT the other-user case — for that the rule is
unit-tested directly against the model, which needs no server.
"""
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

BASE = os.environ.get("SKRIBL_BASE", "http://127.0.0.1:5001")
API = BASE + "/api/skribls"

results = []
def check(name, ok, detail=""):
    results.append((ok, name)); print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  — {detail}" if detail else ""))


def post(title, visibility):
    body = {"title": title, "caption": "SECRET-CAPTION-" + visibility,
            "visibility": visibility,
            "frames": [{"strokes": [], "strokeGroups": [],
                        "background": {"color": "#101418"}}]}
    req = urllib.request.Request(API, method="POST",
                                 data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, {}


def get(path):
    try:
        with urllib.request.urlopen(BASE + path, timeout=20) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read() or b""


# ---------------------------------------------------------------- the rule
print("\nPRIVACY — the rule itself, unit-tested without a server")
from skribl.models import SkriblPost

_p = SkriblPost(user_id=7)
for vis, anon, author, other in [("public", True, True, True),
                                 ("unlisted", True, True, True),
                                 ("private", False, True, False)]:
    _p.visibility = vis
    check(f"{vis}: anonymous reader {'may' if anon else 'may NOT'} read",
          _p.visible_to(None) is anon)
    check(f"{vis}: the author may read", _p.visible_to(7) is author)
    check(f"{vis}: a DIFFERENT user {'may' if other else 'may NOT'} read",
          _p.visible_to(9) is other,
          "this is the case a single-user harness cannot exercise over HTTP")

# ---- states this package did not define -----------------------------------
# VISIBILITIES is enforced by the API rather than a DB constraint SPECIFICALLY
# so a host application can add its own states without a Skribl migration. The
# model comment invites that. But the rule read "anything that is not private
# is readable", so a host adding 'draft', 'moderated', 'blocked' or 'scheduled'
# would create posts hidden from the feed and readable by anyone holding the id
# — a listing filter pretending to be an access control, which is the exact
# mistake this suite exists to prevent, one layer up.
#
# Extensibility of the VOCABULARY has to come with extensibility of the POLICY,
# and the default for an unrecognised state must be to refuse.
for unknown in ("draft", "moderated", "blocked", "scheduled", ""):
    _u = SkriblPost(user_id=7)
    _u.visibility = unknown
    check(f"a host-defined {unknown or '(empty)'!r} state is NOT readable by a stranger",
          _u.visible_to(None) is False and _u.visible_to(9) is False,
          "unknown states must fail closed; a new state should be invisible "
          "until someone decides otherwise, not public until someone notices")
    check(f"and {unknown or '(empty)'!r} is still readable by its author",
          _u.visible_to(7) is True,
          "failing closed must not lock an author out of their own post")

# The escape hatch has to work, or "fail closed" just means "cannot extend".
from skribl.models import set_visibility_policy

_d = SkriblPost(user_id=7)
_d.visibility = "followers"
set_visibility_policy(lambda post, viewer_id: True if post.visibility == "followers" else None)
check("a host policy can open one of its own states",
      _d.visible_to(None) is True)
_priv = SkriblPost(user_id=7)
_priv.visibility = "private"
check("and returning None leaves the built-in rules alone",
      _priv.visible_to(9) is False and _priv.visible_to(7) is True,
      "a host should only have to describe the states it added")

set_visibility_policy(lambda post, viewer_id: False)
_pub = SkriblPost(user_id=7)
_pub.visibility = "public"
check("a host policy can also CLOSE a built-in state",
      _pub.visible_to(None) is False,
      "moderation needs to be able to take something down")

set_visibility_policy(None)
check("clearing the policy restores the defaults",
      _pub.visible_to(None) is True and _d.visible_to(None) is False)

try:
    set_visibility_policy("not callable")
    _raised = False
except TypeError:
    _raised = True
check("a non-callable policy is refused at install time, not at read time",
      _raised, "a policy that explodes mid-request fails open or 500s")

check("the model's own default is 'unlisted', matching route and migration",
      SkriblPost.__table__.c.visibility.default.arg == "unlisted",
      str(SkriblPost.__table__.c.visibility.default.arg))

# ---------------------------------------------------------- the surfaces
print("\nPRIVACY — every read surface, for a PRIVATE post")
# Posted by user 1; the standalone viewer is also user 1, so this post is the
# viewer's OWN. Every surface must therefore ALLOW it — the deny case is covered
# by the unit tests above.
# The standalone app is UNAUTHENTICATED — current_user_id() is None — so it has
# no owner to give a private post to. Creating one would produce a Skribl nobody
# could ever read, including its own maker. It must be refused, not accepted.
st, priv = post("private probe", "private")
check("an anonymous deployment REFUSES to create a private post", st == 400,
      f"{st} — a private post with no owner is write-only")
check("the refusal is a 400, not a silent success", st != 201, str(st))
# The allow-path for a real author is exercised over HTTP in the cross-viewer
# section below, which supplies a genuine current_user_id.

print("\nPRIVACY — a PUBLIC post stays fully readable")
st, pub = post("public probe", "public")
pub_id = pub.get("id")
for path, label in [(f"/api/skribls/{pub_id}", "API read"),
                    (f"/s/{pub_id}", "player page")]:
    st, _ = get(path)
    check(f"public post: {label} is 200", st == 200, str(st))

print("\nPRIVACY — an UNLISTED post is link-reachable but unlisted")
st, unl = post("unlisted probe", "unlisted")
unl_id = unl.get("id")
st, _ = get(f"/api/skribls/{unl_id}")
check("unlisted: readable by link", st == 200, str(st))
st, feed = get("/api/skribls?limit=100")
listed = {i["id"] for i in json.loads(feed).get("items", [])}
check("unlisted: absent from the public timeline", unl_id not in listed)
check("public: present in the public timeline", pub_id in listed)

print("\nPRIVACY — an unknown id is indistinguishable from a forbidden one")
st_missing, _ = get("/api/skribls/definitely-not-a-real-id")
check("an id that was never issued returns 404, not 403", st_missing == 404,
      str(st_missing))
check("so a refusal cannot be used to confirm an id exists",
      st_missing == 404,
      "403 on forbidden vs 404 on missing would be an enumeration oracle")

print("\nPRIVACY — a DIFFERENT viewer, over HTTP, on every surface")
# The shared harness server resolves the current user to 1 and stamps posts with
# 1, so over HTTP it can only ever exercise the ALLOW path. That is precisely the
# blind spot that let the original bug ship: the deny path was never requested.
# So build throwaway apps in-process with a different current_user_id and hit
# every surface as somebody else.
import tempfile
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import skribl
import skribl.models

_tmp = tempfile.mkdtemp()
_url = f"sqlite:///{_tmp}/privacy.db"


def _app_as(viewer):
    a = Flask(__name__)
    a.config["SQLALCHEMY_DATABASE_URI"] = _url
    a.config["SECRET_KEY"] = "harness-privacy"
    d = SQLAlchemy()
    d.init_app(a)
    skribl.init_skribl(a, session=lambda: d.session,
                       current_user_id=(lambda: viewer))
    skribl.models.attach_to_metadata(d.metadata)
    return a, d


_author_app, _db = _app_as(1)
with _author_app.app_context():
    _db.create_all()
_r = _author_app.test_client().post("/api/skribls", json={
    "title": "cross-viewer probe", "caption": "TOP-SECRET-CAPTION",
    "visibility": "private",
    "frames": [{"strokes": [], "strokeGroups": [],
                "background": {"color": "#101418"}}]})
check("a private post is created by user 1", _r.status_code == 201, str(_r.status_code))
_pid = (_r.get_json() or {}).get("id")

for _viewer, _label in [(999, "a different user"), (None, "an anonymous viewer")]:
    _a, _ = _app_as(_viewer)
    _c = _a.test_client()
    _api = _c.get(f"/api/skribls/{_pid}")
    _pg = _c.get(f"/s/{_pid}")
    _card = _c.get(f"/s/{_pid}/card.png")
    check(f"{_label}: the API read is 404", _api.status_code == 404,
          str(_api.status_code))
    check(f"{_label}: the caption does NOT appear in the player's OG tags",
          b"TOP-SECRET-CAPTION" not in _pg.data,
          "private title/caption served to a social scraper")
    check(f"{_label}: the card falls back to the generic image",
          _card.status_code in (302, 301)
          and "og-card" in _card.headers.get("Location", ""),
          f"{_card.status_code} {_card.headers.get('Location', '')[-20:]}"
          + "  — the thumbnail IS the drawing")

# Rebuild the author's app. The process-global session that made this necessary
# is FIXED as of v135 — the factory now lives in app.extensions["skribl"], so
# each application resolves its own and building app B no longer redirects app
# A's queries. Kept as a distinct app because that is what the assertion is
# about: an author reading their own post through their own application.
_author_app2, _ = _app_as(1)
_own = _author_app2.test_client()
check("the author is still not locked out of their own post",
      _own.get(f"/api/skribls/{_pid}").status_code == 200,
      str(_own.get(f"/api/skribls/{_pid}").status_code))
check("and still sees their own caption",
      b"TOP-SECRET-CAPTION" in _own.get(f"/s/{_pid}").data)

# ------------------------------------------------- the surfaces are complete
print("\nPRIVACY — no read surface escapes the rule")
_routes = (ROOT / "skribl" / "routes.py").read_text(encoding="utf-8")
# Every handler that loads a post by public_id must consult visible_to. If a new
# read surface is added without it, this fails — which is the failure mode that
# produced this suite in the first place.
_loads = _routes.count("filter_by(public_id=public_id)")
_guards = _routes.count("visible_to(")
check("every by-id post lookup is paired with a visibility check",
      _guards >= _loads, f"{_loads} lookups, {_guards} guards")
check("the guard is used on at least three surfaces", _guards >= 3, str(_guards))

bad = [r for r in results if not r[0]]
print(f"\n{'='*62}\n{len(results)-len(bad)}/{len(results)} passed" +
      ("" if not bad else "  FAILURES: " + ", ".join(r[1] for r in bad)))
