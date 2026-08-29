"""v224 — the four host seams from the outside review, exercised end to end.

Findings #3, #4, #7 and #8 were all one shape of bug: the package DOCUMENTED an
extension point that the code did not actually have, or shipped a demo value as
if it were a product behaviour. Each is now a real seam, and this suite is what
stops them from becoming documentation again.

  #3  set_feed_filter      — the feed filtered on the visibility COLUMN and
                             never consulted the host's visibility policy, so a
                             post the policy denied still disclosed its title,
                             caption, author and public id through the listing.
  #4  csrf=False           — `current_user_id` without a CSRF verifier used to
                             log a warning. It now refuses, with csrf=False as
                             the explicit declaration for token-authenticated
                             hosts. (The refusal itself is asserted in
                             verify_txcontract.py; what is proved HERE is that
                             the declaration produces a working application.)
  #7  set_visibility_values— the model has no DB CHECK constraint so a host can
                             add "draft" or "moderated" without a migration, and
                             the docs said so, while the create endpoint rejected
                             every one of them.
  #8  set_author_resolver  — the API answered {"username": "demo-user"} for every
                             author in every deployment, beside the real id.

WHAT #3 DOES AND DOES NOT FIX, stated here because a suite that leaves this
implicit is how the next reader over-reads it. Skribl cannot guess a host's
authorization SQL, so the fix is a seam the host installs, not an automatic
one. Without a feed filter the feed still lists every PUBLIC post — which is
its documented behaviour and correct for the ordinary case, where a host policy
restricts private and unlisted posts that the feed already excludes. A host
whose policy can deny a PUBLIC post (a block list, a moderation queue) must
install the filter, and this suite proves the filter works and pages correctly
when it does. The assertions below say so in both directions on purpose.

In-process throwaway apps over one temp SQLite file, in the style of
verify_privacy.py. No server, no browser.
"""
import json
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("SECRET_KEY", "harness-hostseams")

from flask import Flask                                    # noqa: E402
from flask_sqlalchemy import SQLAlchemy                    # noqa: E402
import sqlalchemy as sa                                    # noqa: E402
import skribl                                              # noqa: E402
import skribl.models                                       # noqa: E402
from skribl.models import SkriblPost                       # noqa: E402

results = []


def check(name, ok, detail=""):
    results.append((bool(ok), name))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  — {detail}" if detail else ""))


DB_URL = f"sqlite:///{tempfile.mkdtemp()}/hostseams.db"


def host_app(viewer, **seams):
    """A pretend host. Every one of these authenticates with a closure, not a
    cookie, so csrf=False is the honest declaration — which is finding #4's
    opt-out being used for real rather than merely being asserted to exist."""
    a = Flask(f"host-{viewer}-{len(seams)}")
    a.config["SQLALCHEMY_DATABASE_URI"] = DB_URL
    a.config["SECRET_KEY"] = "harness-hostseams"
    d = SQLAlchemy()
    d.init_app(a)
    skribl.init_skribl(a, session=lambda: d.session,
                       current_user_id=(lambda: viewer), csrf=False, **seams)
    skribl.models.attach_to_metadata(d.metadata)

    @a.after_request
    def _commit(resp):
        if resp.status_code < 500:
            d.session.commit()
        return resp

    return a, d


def body(title, visibility="public"):
    return {"title": title, "visibility": visibility,
            "strokes": [], "strokeGroups": []}


_boot, _bootdb = host_app(1)
with _boot.app_context():
    _bootdb.create_all()


print("\n#4 — csrf=False produces a WORKING app, not merely a quiet one")
# The refusal is asserted in verify_txcontract. The risk with a fail-closed
# change is the opposite one: an opt-out that silences the error and then
# breaks something. Every app in this suite is built through it, so if the
# declaration were inert the whole file would fail — but assert it directly
# rather than leave it as a side effect.
app_a, db_a = host_app(7)
c_a = app_a.test_client()
r = c_a.post("/api/skribls", json=body("declared-csrf-off"))
check("a csrf=False host can post", r.status_code == 201,
      f"{r.status_code} {r.get_data(as_text=True)[:100]}")
_pid = r.get_json()["id"]
with app_a.app_context():
    _owner = db_a.session.execute(
        sa.text("select user_id from skribl_posts where public_id = :p"),
        {"p": _pid}).first()[0]
check("…and its current_user_id still decides authorship", _owner == 7,
      f"user_id={_owner}")
check("no CSRF token is issued when the host declined one",
      app_a.blueprints["skribl"].skribl_csrf is None,
      "csrf=False records a decision; it does not install a no-op validator")


print("\n#8 — the author block says what Skribl knows, and nothing it doesn't")
r = c_a.get(f"/api/skribls/{_pid}")
author = r.get_json()["author"]
check("the default author block carries the real id", author.get("id") == 7,
      json.dumps(author))
check("AND NO INVENTED USERNAME", "username" not in author,
      "'demo-user' was returned for every author in every deployment")

app_b, _ = host_app(7, author_resolver=lambda uid: {
    "username": f"user{uid}", "displayName": "Real Person", "avatar": None})
author = app_b.test_client().get(f"/api/skribls/{_pid}").get_json()["author"]
check("a host resolver's fields appear", author.get("username") == "user7"
      and author.get("displayName") == "Real Person", json.dumps(author))
check("…alongside the id, not instead of it", author.get("id") == 7)

app_c, _ = host_app(7, author_resolver=lambda uid: {"id": 999, "username": "x"})
author = app_c.test_client().get(f"/api/skribls/{_pid}").get_json()["author"]
check("a resolver CANNOT overwrite the id",
      author.get("id") == 7 and author.get("username") == "x",
      f"{json.dumps(author)} — the id is what the host's own policy was handed")

app_d, _ = host_app(7, author_resolver=lambda uid: None)
author = app_d.test_client().get(f"/api/skribls/{_pid}").get_json()["author"]
check("a resolver returning nothing degrades to the default, not a 500",
      author == {"id": 7}, json.dumps(author))
# The seam is app-local like the visibility policy. Two Skribl apps in one
# process must not share author naming — that is the bug set_visibility_policy
# was reshaped to avoid, and a new global would reintroduce it.
author = c_a.get(f"/api/skribls/{_pid}").get_json()["author"]
check("AND IT IS APP-LOCAL — the first app is unaffected", "username" not in author,
      json.dumps(author))


print("\n#7 — a host can add a visibility state without a migration")
r = c_a.post("/api/skribls", json=body("a draft", visibility="draft"))
check("an unextended app still rejects an unknown visibility",
      r.status_code == 400, str(r.status_code))

app_e, db_e = host_app(7, visibility_values=("draft", "moderated"))
c_e = app_e.test_client()
r = c_e.post("/api/skribls", json=body("a draft", visibility="draft"))
check("an app that registered 'draft' accepts it", r.status_code == 201,
      f"{r.status_code} {r.get_data(as_text=True)[:100]}")
draft_id = r.get_json()["id"] if r.status_code == 201 else None
with app_e.app_context():
    stored = db_e.session.execute(
        sa.text("select visibility from skribl_posts where public_id = :p"),
        {"p": draft_id}).first()
check("…and stores the string it was given, not a coerced default",
      stored and stored[0] == "draft", str(stored))
for built_in in SkriblPost.VISIBILITIES:
    r = c_e.post("/api/skribls", json=body(f"still-{built_in}", visibility=built_in))
    check(f"registering extras does not displace the built-in '{built_in}'",
          r.status_code == 201, str(r.status_code))
r = c_e.post("/api/skribls", json=body("nope", visibility="wharrgarbl"))
check("and a state nobody registered is still refused", r.status_code == 400,
      "widening the set is not the same as removing the check")
check("the extras are app-local too",
      c_a.post("/api/skribls", json=body("d2", visibility="draft")).status_code == 400)
# The column is String(16). A longer value accepted here would surface as a
# database error on somebody's first post instead of at the misconfigured line.
for _bad, _why in ((("x" * 17,), "17 characters against a String(16) column"),
                   (("",), "an empty visibility string")):
    try:
        skribl.models.set_visibility_values(_bad, app=app_e)
        check(f"refused at configuration time: {_why}", False, "it was accepted")
    except ValueError as exc:
        check(f"refused at configuration time: {_why}", True, str(exc)[:90])
check("exactly 16 characters is allowed — the guard is the column, not a taste",
      skribl.models.set_visibility_values(("x" * 16,), app=app_e) is None)
skribl.models.set_visibility_values(("draft", "moderated"), app=app_e)
# The documented consequence, asserted rather than left to the reader: the
# built-in feed lists "public" only, so a custom state is invisible to it
# unless the host also installs a feed filter.
feed = c_e.get("/api/skribls").get_json()
check("a custom state does NOT appear in the built-in feed",
      all(item["id"] != draft_id for item in feed["items"]),
      "documented: the feed lists public posts; a custom state needs a filter")


print("\n#3 — the feed can finally be filtered in SQL by the host")
app_pub, db_pub = host_app(11)
c_pub = app_pub.test_client()
ids = []
for n in range(6):
    ids.append(c_pub.post("/api/skribls", json=body(f"public-{n}")).get_json()["id"])
listed = [i["id"] for i in c_pub.get("/api/skribls").get_json()["items"]]
check("with no filter installed, the feed lists every public post",
      set(ids) <= set(listed), f"{len(listed)} listed")
check("…which is the honest starting point: this is a SEAM, not an automatic fix",
      True, "a host whose policy can deny a PUBLIC post must install the filter")

# A host that hides posts by a blocked author. This is exactly the case the
# visibility COLUMN cannot express and the visibility policy could not reach.
BLOCKED = 11


def hide_blocked(q, viewer):
    return q.filter(SkriblPost.user_id != BLOCKED)


app_f, _ = host_app(12, feed_filter=hide_blocked)
c_f = app_f.test_client()
after = c_f.get("/api/skribls").get_json()
check("the installed filter removes those rows from the listing",
      all(i["id"] not in ids for i in after["items"]),
      f"{len(after["items"])} rows survive")
check("…and it removed the TITLES too, not just the payloads",
      not any(i["title"].startswith("public-") for i in after["items"]),
      "the disclosure was the listing metadata, not the drawing")

# The reason the seam is SQL and not a post-fetch drop. Page through with a
# filter that hides most rows: a correct implementation returns full pages and
# a cursor that points at a row the viewer actually saw.
mixed = []
app_g, _ = host_app(13)
c_g = app_g.test_client()
for n in range(8):
    mixed.append(c_g.post("/api/skribls", json=body(f"visible-{n}")).get_json()["id"])

app_h, _ = host_app(14, feed_filter=hide_blocked)
c_h = app_h.test_client()
page1 = c_h.get("/api/skribls?limit=3").get_json()
check("a filtered feed still returns FULL pages", len(page1["items"]) == 3,
      f"{len(page1['items'])} rows — a post-fetch drop returns short ones")
check("…and a cursor", bool(page1.get("next_cursor")), str(page1.get("next_cursor"))[:40])
seen = [i["id"] for i in page1["items"]]
cursor, guard = page1.get("next_cursor"), 0
while cursor and guard < 10:
    pg = c_h.get(f"/api/skribls?limit=3&cursor={cursor}").get_json()
    seen += [i["id"] for i in pg["items"]]
    cursor, guard = pg.get("next_cursor"), guard + 1
check("paging reaches every visible post exactly once",
      sorted(seen) == sorted(set(seen)) and set(mixed) <= set(seen),
      f"{len(seen)} rows over {guard + 1} pages, {len(set(seen))} distinct")
check("and never a hidden one", not any(i in ids for i in seen),
      "a filter that leaks on page 2 is not a filter")

# The mutation check for this section: without the filter, the same client
# would see the hidden rows. If it would not, nothing above tested the seam.
check("MUTATION — an app WITHOUT the filter does see those same rows",
      any(i["id"] in ids for i in c_g.get("/api/skribls?limit=50").get_json()["items"]),
      "otherwise the rows were absent for some other reason")

# Raising is deliberately not caught: a broken feed filter must fail loudly
# rather than fall back to listing everything.
def explodes(q, viewer):
    raise RuntimeError("host filter is broken")


app_i, _ = host_app(15, feed_filter=explodes)
# The 500 below is the assertion, so its traceback is expected output rather
# than a problem — silence it so a real error in this suite stays visible.
import logging  # noqa: E402
app_i.logger.setLevel(logging.CRITICAL)
try:
    resp = app_i.test_client().get("/api/skribls")
    check("a raising filter does NOT fall back to an unfiltered feed",
          resp.status_code >= 500, f"HTTP {resp.status_code}")
except RuntimeError:
    check("a raising filter does NOT fall back to an unfiltered feed", True,
          "it propagated")
try:
    skribl.models.set_feed_filter("not callable", app=app_i)
    check("a non-callable filter is refused at configuration time", False)
except TypeError as exc:
    check("a non-callable filter is refused at configuration time", True, str(exc))


bad = [r for r in results if not r[0]]
print(f"\n{'=' * 62}\n{len(results) - len(bad)}/{len(results)} passed"
      + ("" if not bad else "  FAILURES: " + ", ".join(r[1] for r in bad)))
sys.exit(1 if bad else 0)
