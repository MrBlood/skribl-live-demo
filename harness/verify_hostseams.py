"""The four host seams from the outside review, exercised end to end.

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
from assertions import make_check

results = []


check = make_check(results)


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
# IDS ARE TEXT SINCE v279, so these compare "7" and not 7. The column was
# Integer while docs/INTEGRATION.md advertised "your user id", which locked out
# every host whose identities are UUIDs, ULIDs or an OAuth subject. The change
# is visible in the API too: `author.id` is now a JSON STRING. That is the
# honest shape for an opaque identifier, and it is called out here because a
# host comparing author.id to its own numeric id has to compare as text now.
check("…and its current_user_id still decides authorship", str(_owner) == "7",
      f"user_id={_owner}")
check("no CSRF token is issued when the host declined one",
      app_a.blueprints["skribl"].skribl_csrf is None,
      "csrf=False records a decision; it does not install a no-op validator")


print("\n#8 — the author block says what Skribl knows, and nothing it doesn't")
r = c_a.get(f"/api/skribls/{_pid}")
author = r.get_json()["author"]
check("the default author block carries the real id", author.get("id") == "7",
      json.dumps(author))
check("AND NO INVENTED USERNAME", "username" not in author,
      "'demo-user' was returned for every author in every deployment")

app_b, _ = host_app(7, author_resolver=lambda uid: {
    "username": f"user{uid}", "displayName": "Real Person", "avatar": None})
author = app_b.test_client().get(f"/api/skribls/{_pid}").get_json()["author"]
check("a host resolver's fields appear", author.get("username") == "user7"
      and author.get("displayName") == "Real Person", json.dumps(author))
check("…alongside the id, not instead of it", author.get("id") == "7")

app_c, _ = host_app(7, author_resolver=lambda uid: {"id": 999, "username": "x"})
author = app_c.test_client().get(f"/api/skribls/{_pid}").get_json()["author"]
check("a resolver CANNOT overwrite the id",
      author.get("id") == "7" and author.get("username") == "x",
      f"{json.dumps(author)} — the id is what the host's own policy was handed")

app_d, _ = host_app(7, author_resolver=lambda uid: None)
author = app_d.test_client().get(f"/api/skribls/{_pid}").get_json()["author"]
check("a resolver returning nothing degrades to the default, not a 500",
      author == {"id": "7"}, json.dumps(author))

# ---- #8b: the LISTING carries the author too (v308) -------------------------
# The gallery renders from GET /api/skribls and never fetches a payload until
# somebody presses play, so a grid of tiles had a user_id and no way to turn it
# into a name -- the author block existed on the single-post GET alone. The
# owner's ask ("there needs to be a place on the card where it says who created
# the skribl with their avatar") is a LISTING feature.
_calls = []


def _counting_resolver(uid):
    _calls.append(uid)
    return {"username": f"user{uid}", "display_name": "Real Person",
            "avatar_url": "https://example.test/a.png", "verified": True}


app_l, db_l = host_app(7, author_resolver=_counting_resolver)
c_l = app_l.test_client()
# Three more posts by the same author, so the memo below has something to
# collapse. Four rows, one distinct user_id.
for _i in range(3):
    assert c_l.post("/api/skribls", json=body(f"listed-{_i}")).status_code == 201
_listing = c_l.get("/api/skribls?limit=50").get_json()["items"]
_mine = [i for i in _listing if i.get("user_id") == "7"]
check("every listed post of a described author carries an author block",
      len(_mine) >= 4 and all(i.get("author", {}).get("username") == "user7"
                              for i in _mine),
      f"{len(_mine)} rows, authors "
      f"{[i.get('author', {}).get('username') for i in _mine][:6]}")
check("...with the fields a card draws: name, handle, avatar, the tick",
      all({"display_name", "username", "avatar_url", "verified"}
          <= set(i["author"]) for i in _mine),
      json.dumps(_mine[0].get("author")) if _mine else "no rows")
check("...and the id stays authoritative there as well",
      all(i["author"].get("id") == "7" for i in _mine),
      json.dumps(_mine[0].get("author")) if _mine else "no rows")
# ONE CALL PER DISTINCT AUTHOR, NOT ONE PER ROW. The resolver is the HOST'S
# function and a host's natural implementation is a SELECT, so a page of fifty
# tiles by one author would issue fifty queries for one row. Asserted by
# counting calls, which is the only way to see it: the response is identical
# either way, which is exactly why this would have shipped unnoticed.
_distinct = len(set(_calls))
check("the resolver is called once per DISTINCT author, not once per row",
      len(_calls) == _distinct and _distinct >= 1,
      f"{len(_calls)} calls for {_distinct} distinct id(s) over "
      f"{len(_mine)} rows — a per-row resolver is a query per tile")

# AN ANONYMOUS POST GETS NO AUTHOR KEY AT ALL. Not {"id": null}: the client
# renders an absent author as nothing, and "nobody is named" is the honest
# answer for a post made with no host signed in -- which is every post the
# standalone demo has ever taken.
app_anon, _ = host_app(None, author_resolver=_counting_resolver)
c_anon = app_anon.test_client()
assert c_anon.post("/api/skribls", json=body("no-author-at-all")).status_code == 201
_anon_rows = [i for i in c_anon.get("/api/skribls?limit=50").get_json()["items"]
              if i.get("user_id") is None]
check("an anonymous post carries NO author key, rather than an empty one",
      len(_anon_rows) >= 1 and all("author" not in i for i in _anon_rows),
      f"{len(_anon_rows)} anonymous rows; first = "
      f"{json.dumps(_anon_rows[0])[:160] if _anon_rows else 'none'}")
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
# A note, not a check. The assertion above it does the work; asserting `True`
# after it added a number to the count and proved nothing.
print("    …which is the honest starting point: this is a SEAM, not an "
      "automatic fix — a host whose policy can deny a PUBLIC post must "
      "install the filter")

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
      f"{len(after['items'])} rows survive")
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


print("\nEXT-P1-13 — the help drawer describes the ownership model in force")
# The "Your Skribls" tip described the browser-held model unconditionally:
# "everything you have posted from this browser", Delete working "because this
# browser holds the key", the list "saved in this browser only" and removed by
# clearing site data. Every clause is false once a host signs somebody in --
# the posts belong to the ACCOUNT, they are listed by author, they survive
# clearing site data, and there is no key to keep safe. Copy that confidently
# describes the wrong ownership model is a trust problem: it tells people their
# work is more fragile than it is, or less.
#
# ASSERTED ON BOTH SURFACES AND BOTH MODES. A shared include rendered under two
# identities is two instances until each has been driven -- Pad and Flip both
# include this drawer, and a fix that reached one template's copy of the
# condition would look green on a census that only visited the other.
_KEY_CLAIM = "this browser holds the key"
_ACCOUNT_CLAIM = "belong to your account"

for _route, _surface in (("/skribl-pad", "Pad"), ("/flip", "Flip")):
    _anon_html = host_app(None)[0].test_client().get(_route).get_data(as_text=True)
    _in_html = host_app(7)[0].test_client().get(_route).get_data(as_text=True)

    check(f"the probe is real: {_surface} renders the Your Skribls tip at all",
          "Your Skribls</span>" in _anon_html and "Your Skribls</span>" in _in_html,
          "without the tip present, every assertion below passes vacuously")
    check(f"{_surface}, anonymous: the browser-held model is still described",
          _KEY_CLAIM in _anon_html and _ACCOUNT_CLAIM not in _anon_html,
          "standalone is exactly where that copy is true, and it must not "
          "have been traded away for the signed-in case")
    check(f"{_surface}, signed in: the account model is described instead",
          _ACCOUNT_CLAIM in _in_html and _KEY_CLAIM not in _in_html,
          "the key sentence surviving here is the defect: there is no browser "
          "key, and clearing site data does not remove an account's posts")

# ---------------------------------------------------------------------------
# THE DEMO'S STAND-IN IDENTITY (v308)
#
# Skribl has no user table, so this repo's demo has always posted anonymously
# and its gallery cards have no author to draw. SKRIBL_DEMO_IDENTITY makes the
# demo behave the way skribls.net will -- one signed-in user, described through
# the same set_author_resolver hook -- which is the only way to LOOK at the
# feature here. It is also a deploy-time switch on a live service, and this
# tree has already lost an afternoon to a deploy that failed on startup, so
# both paths through it are exercised rather than reasoned about.
print("\nTHE DEMO IDENTITY — off by default, fails closed, and names its own switch")
import importlib                                                    # noqa: E402
_appmod = importlib.import_module("app")
_saved = {k: os.environ.get(k) for k in
          ("SKRIBL_DEMO_IDENTITY", "SKRIBL_DEMO_IDENTITY_NAME",
           "SKRIBL_DEMO_IDENTITY_AVATAR", "SKRIBL_DEMO_IDENTITY_URL",
           "SKRIBL_DEMO_IDENTITY_VERIFIED", "SKRIBL_CSRF_PROTECT",
           "DATABASE_URL", "SECRET_KEY", "SKRIBL_ALLOW_EPHEMERAL_SECRET")}


def _env(**kw):
    for k, v in kw.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v


try:
    _env(DATABASE_URL=DB_URL, SECRET_KEY="harness-demo-identity",
         SKRIBL_ALLOW_EPHEMERAL_SECRET="1")

    # OFF BY DEFAULT. Unset, nothing in that block runs and the demo is
    # exactly as anonymous as it was -- which matters because the live demo
    # is running without it right now.
    _env(SKRIBL_DEMO_IDENTITY=None, SKRIBL_CSRF_PROTECT=None)
    _off = _appmod.create_app()
    check("with no SKRIBL_DEMO_IDENTITY the demo stays anonymous",
          _off.blueprints["skribl"].skribl_current_user_id() is None,
          "an identity nobody asked for would put a name on every new post")

    # FAILS CLOSED, AND SAYS WHICH SWITCH. init_skribl refuses an id without
    # CSRF (a cookie identity with no CSRF lets any page post as the user);
    # its message cannot know about this env var, so the demo raises first in
    # its own words. A deploy that fails is fine; one that fails unreadably
    # costs an afternoon.
    _env(SKRIBL_DEMO_IDENTITY="bigballbaron", SKRIBL_CSRF_PROTECT=None)
    _msg = ""
    try:
        _appmod.create_app()
    except RuntimeError as e:
        _msg = str(e)
    check("an identity without CSRF is refused, naming SKRIBL_CSRF_PROTECT",
          "SKRIBL_CSRF_PROTECT" in _msg,
          f"raised {_msg[:140]!r} — an operator reads this in a deploy log")

    # AND ON, IT DESCRIBES EXACTLY ONE PERSON.
    _env(SKRIBL_DEMO_IDENTITY="bigballbaron", SKRIBL_CSRF_PROTECT="1",
         SKRIBL_DEMO_IDENTITY_NAME="Mr. B",
         SKRIBL_DEMO_IDENTITY_AVATAR="https://media.example.test/skull.png",
         SKRIBL_DEMO_IDENTITY_URL="https://example.test/u/bigballbaron",
         SKRIBL_DEMO_IDENTITY_VERIFIED="1")
    _on = _appmod.create_app()
    check("with it set, the demo signs one user in",
          _on.blueprints["skribl"].skribl_current_user_id() == "bigballbaron",
          "this id is what goes on a new post's user_id")
    with _on.app_context():
        _me = skribl.models.author_dict("bigballbaron")
        _other = skribl.models.author_dict("somebody-else")
    check("...and describes them with the fields a card draws",
          _me.get("display_name") == "Mr. B" and _me.get("username") == "bigballbaron"
          and _me.get("avatar_url", "").endswith("skull.png")
          and _me.get("verified") is True and _me.get("id") == "bigballbaron",
          json.dumps(_me))
    # ONE ID, ONE ANSWER. A resolver that returned this name for every user_id
    # would be a lie the moment a second author existed -- and `author_dict`
    # puts the REAL id back over anything the resolver returns, so the answer
    # would carry somebody else's id beside this name.
    check("...and nobody else is described as them",
          _other == {"id": "somebody-else"}, json.dumps(_other))
finally:
    for _k, _v in _saved.items():
        _env(**{_k: _v})

bad = [r for r in results if not r[0]]
print(f"\n{'=' * 62}\n{len(results) - len(bad)}/{len(results)} passed"
      + ("" if not bad else "  FAILURES: " + ", ".join(r[1] for r in bad)))
sys.exit(1 if bad else 0)
