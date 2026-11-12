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


print("\n#6ah — set_source_resolver: where each skribl was posted, said by the host")
# "From a post" on a page of skribls (FUTURE 6ah, the owner's pick A for the
# Skribls section): Skribl knows a public id and nothing of the host's posts,
# so the host says, through a resolver handed the PAGE'S ids at once.
_src_calls = []


def _posts_of(ids):
    _src_calls.append(list(ids))
    out = {}
    for _n, _i in enumerate(ids):
        out[_i] = ["/posts/%d" % _n, "https://site.example/p/%d" % _n, "javascript:alert(1)",
                   "//elsewhere.example/x", "/\\elsewhere.example", " /posts/ x", 42, None][_n % 8]
    return out


app_s, _ = host_app(7, source_resolver=_posts_of)
c_s = app_s.test_client()
for _i in range(8):
    assert c_s.post("/api/skribls", json=body(f"sourced-{_i}")).status_code == 201
_src_calls.clear()
_page = c_s.get("/api/skribls?limit=50").get_json()["items"]
_sent = {i["id"]: i.get("source") for i in _page}
check("ONE CALL FOR THE PAGE, with every id on it, not a call per tile",
      len(_src_calls) == 1 and sorted(_src_calls[0]) == sorted(_sent),
      f"{len(_src_calls)} call(s) for {len(_sent)} tiles")
_given = _posts_of(list(_src_calls[0])) if _src_calls else {}
_kept = {i: u for i, u in _given.items() if _sent.get(i)}
check("a path on the site and an http(s) address are passed on as `source`",
      all(_sent[i] == {"url": _given[i]} for i in _kept)
      and {u.split("/")[0] for u in _kept.values()} >= {"", "https:"}, json.dumps(_kept))
check("...and a script, another site's //, a backslash path, a space, a number or nothing are not",
      all(_sent[i] is None for i, u in _given.items()
          if not (isinstance(u, str) and (u.startswith("/posts/") and " " not in u or u.startswith("https://")))),
      json.dumps({i: _given[i] for i in _given if _sent.get(i) is None}))
_one = next(iter(_kept), None)
_single = c_s.get(f"/api/skribls/{_one}").get_json() if _one else {}
check("a skribl read on its own says where it was posted, as the listing does",
      bool(_one) and _single.get("source") == {"url": _given[_one]}, json.dumps(_single.get("source")))
# Before any other app installs one: a resolver kept for every app would be
# the last one installed, and this asks the first app with that one live.
check("AND IT IS APP-LOCAL: an app without the seam carries no `source`",
      all("source" not in i for i in c_a.get("/api/skribls?limit=50").get_json()["items"])
      and "source" not in c_a.get(f"/api/skribls/{_one}").get_json())
app_s2, _ = host_app(7, source_resolver=lambda ids: ["/posts/1"])
try:
    _r2 = app_s2.test_client().get("/api/skribls?limit=50")
    _ok2, _why2 = (_r2.status_code == 200 and all("source" not in i for i in _r2.get_json()["items"]),
                   str(_r2.status_code))
except Exception as _exc:                       # a host's bug must not take the listing down
    _ok2, _why2 = False, f"{type(_exc).__name__}: {_exc}"
check("a resolver that answers with something other than a mapping says nothing, not a 500", _ok2, _why2)


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

# A POLICY WITHOUT A MATCHING FILTER LEAKS NOTHING (the PRE-331 review's 3).
# The filter is how a host keeps the listing in step, in SQL; a host that
# installed only a policy listed the titles, ids and authors of posts the
# policy refuses. Under a policy each row is asked visible_to too, and a
# page that loses rows is filled from the rows after them, so pages stay
# full; a cursor names its row's time and id, so it is only ever taken
# from a row the viewer was shown. New and Hot both, a few rows a page,
# so the six refused posts fall across a page.
import base64 as _b64                                             # noqa: E402
app_p, db_p = host_app(16)
skribl.set_visibility_policy(lambda post, v: False if post.user_id == str(BLOCKED) else None, app=app_p)
try:
    with app_p.app_context():
        hidden_rows = {str(r.id) for r in db_p.session.query(SkriblPost).filter(SkriblPost.public_id.in_(ids))}
    c_p = app_p.test_client()

    def _walk(client, sort, size):
        pg = client.get(f"/api/skribls?limit={size}{sort}").get_json()
        pages, cursors = [[i["id"] for i in pg["items"]]], []
        while pg.get("next_cursor") and len(pages) < 60:
            cursors.append(pg["next_cursor"])
            pg = client.get(f"/api/skribls?limit={size}{sort}&cursor={pg['next_cursor']}").get_json()
            pages.append([i["id"] for i in pg["items"]])
        return pages, cursors
    for _sort in ("", "&sort=hot"):
        # Every post the policy allows: what an app with no policy lists, less
        # the refused. Read from the listing itself so it counts what this
        # database holds, whatever the sections above posted.
        allowed = [i for i in sum(_walk(c_g, _sort, 50)[0], []) if i not in ids]
        pages, cursors = _walk(c_p, _sort, 3)
        seen_p = sum(pages, [])
        named = {_b64.urlsafe_b64decode(c + "=" * (-len(c) % 4)).decode().rpartition("|")[2] for c in cursors}
        _name = "Hot" if _sort else "New"
        check(f"{_name}: a policy with no matching feed filter keeps the posts it refuses off every page, and lists every other post once, in order",
              seen_p == allowed and len(allowed) > len(mixed),
              f"{len(seen_p)} listed over {len(pages)} pages of {len(allowed)} allowed; refused ones listed: {sum(i in ids for i in seen_p)}")
        check(f"{_name}: ...its pages are full, and no cursor names a row it did not show",
              all(len(x) == 3 for x in pages[:-1]) and not (named & hidden_rows),
              f"page sizes {[len(x) for x in pages]}; cursors naming a refused row: {len(named & hidden_rows)}")
finally:
    skribl.set_visibility_policy(None, app=app_p)

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
# The "Your Skribls" tip (named "Your Skribl Library" since v314) described the browser-held model unconditionally:
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

    # Keyed on the tip's own PILL, not the words: since v314 the name
    # ("Your Skribl Library") is also the menu row's text a few lines away.
    _PILL = '<span class="help-pill">Your Skribl Library</span>'
    check(f"the probe is real: {_surface} renders the Your Skribl Library tip at all",
          _PILL in _anon_html and _PILL in _in_html,
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
           "SKRIBL_DEMO_IDENTITY_VERIFIED", "SKRIBL_CSRF_PROTECT", "SKRIBL_DEMO_LOGIN_KEY",
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

    # WITHOUT A LOGIN KEY, NOBODY IS SIGNED IN (v317, security review). The
    # handle used to be EVERY visitor's identity: a stranger could delete the
    # owner's posts and read their drafts. Unkeyed, the demo fails SAFE --
    # boots, anonymous -- rather than refusing to boot a live service.
    _env(SKRIBL_DEMO_IDENTITY="bigballbaron", SKRIBL_CSRF_PROTECT="1", SKRIBL_DEMO_LOGIN_KEY=None)
    _nokey = _appmod.create_app()
    with _nokey.test_request_context("/"):
        _who = _nokey.blueprints["skribl"].skribl_current_user_id()
    check("an identity with no login key signs NOBODY in (it boots, anonymous)", _who is None, repr(_who))

    # AND ON, ONLY THE BROWSER THAT PRESENTED THE KEY IS THE USER.
    _KEY = "harness-demo-login-key-0123456789"
    _env(SKRIBL_DEMO_IDENTITY="bigballbaron", SKRIBL_CSRF_PROTECT="1",
         SKRIBL_DEMO_LOGIN_KEY=_KEY,
         SKRIBL_DEMO_IDENTITY_NAME="Mr. B",
         SKRIBL_DEMO_IDENTITY_AVATAR="https://media.example.test/skull.png",
         SKRIBL_DEMO_IDENTITY_URL="https://example.test/u/bigballbaron",
         SKRIBL_DEMO_IDENTITY_VERIFIED="1")
    _on = _appmod.create_app()
    # Over https: the session cookie is Secure, and a test client over http
    # would neither send it back nor show whether the flag is set.
    class _Https:
        def __init__(self, c): self.c = c
        def get(self, url): return self.c.get(url, base_url="https://localhost")
        def post(self, url, **kw): return self.c.post(url, base_url="https://localhost", **kw)
    _stranger = _Https(_on.test_client())
    _owner = _Https(_on.test_client())
    with _on.test_request_context("/"):
        from flask import url_for as _u
        _drafts_url = _u("skribl.list_saved_drafts")
        _pad_url = _u("skribl.skribl_editor")
    check("a stranger is not the owner: their drafts list is refused",
          _stranger.get(_drafts_url).status_code == 401, _drafts_url)
    # THE KEY IS POSTED FROM A FORM, NEVER READ FROM THE ADDRESS (the
    # PRE-331 review's 5; the owner, Nov 3: "all yes"). /demo-login?key=
    # put it in history, proxy logs and referrers; an old bookmark now
    # lands on the page and signs nobody in.
    _page = _stranger.get("/demo-login?key=" + _KEY)
    check("a key in the address signs nobody in: an old bookmark shows the sign-in page",
          _page.status_code == 200 and b'name="key"' in _page.data and b'method="post"' in _page.data
          and _stranger.get(_drafts_url).status_code == 401, f"{_page.status_code}")
    # A TEXT CONTROL UNDER 16px MAKES iOS MAGNIFY THE PAGE (WORKING-AGREEMENTS).
    # This page is not in verify_a11y's census (it exists only with a demo
    # identity), so its one field is read here, from the rule that sizes it.
    import re as _re
    _sized = _re.search(r"input\{[^}]*font-size:(\d+(?:\.\d+)?)px", _page.data.decode())
    check("the key field is at least 16px, so iPhone does not magnify the page",
          bool(_sized) and float(_sized.group(1)) >= 16, _sized.group(0)[-24:] if _sized else "no size")
    _wrong = _stranger.post("/demo-login", data={"key": "wrong-key-wrong-key"})
    check("a wrong key is refused on the page (403), kindly, and signs nobody in",
          _wrong.status_code == 403 and "didn\u2019t match".encode() in _wrong.data
          and _stranger.get(_drafts_url).status_code == 401, f"{_wrong.status_code}")
    _login = _owner.post("/demo-login", data={"key": _KEY})
    check("the right key, posted, signs THAT browser in (and only it), and the address it lands on carries no key",
          _login.status_code == 303 and _KEY not in (_login.headers.get("Location") or "")
          and _owner.get(_drafts_url).status_code == 200
          and _stranger.get(_drafts_url).status_code == 401, f"login {_login.status_code} -> {_login.headers.get('Location')}")
    _signed_page = _owner.get("/demo-login")
    check("...and the page says who is signed in, with Sign out as a button that posts",
          b"signed in as Mr. B" in _signed_page.data and b'action="/demo-logout"' in _signed_page.data
          and b'<form method="post" action="/demo-logout">' in _signed_page.data, "")
    _ck = _login.headers.get("Set-Cookie", "")
    check("...with a cookie scripts cannot read, other sites cannot send, and plain http never carries",
          "HttpOnly" in _ck and "SameSite=Lax" in _ck and "Secure" in _ck, _ck[-120:])
    with _owner.c.session_transaction(base_url="https://localhost") as _st:
        _mark = _st.get("skribl_demo")
    from flask import session as _sess
    with _on.test_request_context("/"):
        _sess["skribl_demo"] = _mark
        _signed = _on.blueprints["skribl"].skribl_current_user_id()
    check("with it set, the signed-in browser is one user",
          _signed == "bigballbaron", "this id is what goes on a new post's user_id")
    # THE COOKIE CARRIES A MARK OF THE KEY, NOT THE NAME (third review). A
    # cookie saying only the handle outlived the key: rotating a leaked key
    # signed nobody out. Both halves are pinned -- a session holding the bare
    # handle (what every pre-fix cookie held) is nobody, and the SAME cookie
    # presented to an app with a rotated key and the same SECRET_KEY is nobody.
    with _on.test_request_context("/"):
        _sess["skribl_demo"] = "bigballbaron"
        _bare = _on.blueprints["skribl"].skribl_current_user_id()
    check("a session holding just the handle signs nobody in",
          _bare is None and _mark and _mark != "bigballbaron", repr(_bare))
    _env(SKRIBL_DEMO_LOGIN_KEY=_KEY + "-rotated")
    _rot = _appmod.create_app()
    _env(SKRIBL_DEMO_LOGIN_KEY=_KEY)
    with _rot.test_request_context("/"):
        _sess["skribl_demo"] = _mark
        _after = _rot.blueprints["skribl"].skribl_current_user_id()
    check("rotating SKRIBL_DEMO_LOGIN_KEY signs out every browser the old key signed in",
          _after is None, repr(_after))
    # THE BINDING, THROUGH THE WIRING THE DEMO ACTUALLY RUNS (third review).
    # verify_csrf drives the signed triple with a binder it installs itself;
    # this is init_skribl's own `_binder(current_user_id)`. Without it every
    # token is bound to nobody, and one minted for a signed-out page passes
    # for the signed-in owner.
    def _csrf_of(client):
        client.c.get(_pad_url, base_url="https://localhost")
        ck = client.c.get_cookie("skribl_csrf", domain="localhost")
        return ck.value if ck else ""

    # Sent from a client with NO cookie jar, carrying exactly the owner's
    # session and the token under test: a jar would add its own skribl_csrf
    # beside the one in the header, and the check would measure the jar.
    _bare_client = _on.test_client(use_cookies=False)

    def _draft_with(client, tok, addr="198.51.100.20"):
        sess = client.c.get_cookie("session", domain="localhost")
        return _bare_client.post(_drafts_url, base_url="https://localhost", json={"kind": "pad", "payload": {}},
                                 headers={"X-Skribl-CSRF": tok,
                                          "Cookie": f"session={sess.value}; skribl_csrf={tok}"},
                                 environ_base={"REMOTE_ADDR": addr}).status_code
    _anon_tok = _csrf_of(_Https(_on.test_client()))
    _own_tok = _csrf_of(_owner)
    _borrowed = _draft_with(_owner, _anon_tok)
    _own = _draft_with(_owner, _own_tok)
    check("a CSRF token minted for a signed-out page is refused for the signed-in owner (init_skribl binds it)",
          _anon_tok and _borrowed == 403 and _own not in (403, 401), f"borrowed {_borrowed}, own {_own}, anon token {bool(_anon_tok)}")
    # FORGED REQUESTS SPEND NOTHING (third review). The attempts charge came
    # before the CSRF check, so another site's auto-submitting forms could
    # use up the owner's hourly budget and lock them out of saving.
    _on.config["SKRIBL_RATE_MAX_ATTEMPTS"] = 3
    _forged = [_draft_with(_owner, "forged", addr="198.51.100.21") for _ in range(4)]
    _after_forged = _draft_with(_owner, _own_tok, addr="198.51.100.21")
    _on.config.pop("SKRIBL_RATE_MAX_ATTEMPTS", None)
    check("forged writes are refused before they are charged: the owner's budget is intact after them",
          _forged == [403] * 4 and _after_forged not in (403, 429), f"forged {_forged}, then {_after_forged}")
    # ...AND A FORGED GZIPPED BODY IS NOT INFLATED (the PRE-331 review's 4):
    # it is left compressed for its route's 403, which reads no body. A body
    # that inflating refuses tells them apart: 403, not the inflate's 400.
    _sck = _owner.c.get_cookie("session", domain="localhost")
    _forged_gz = _bare_client.post(_drafts_url, base_url="https://localhost", data=b"not gzip",
                                   content_type="application/json",
                                   headers={"X-Skribl-CSRF": "forged", "Content-Encoding": "gzip",
                                            "Cookie": f"session={_sck.value}; skribl_csrf=forged"},
                                   environ_base={"REMOTE_ADDR": "198.51.100.22"}).status_code
    check("a forged gzipped write is refused without being inflated (403, not the inflate's 400)",
          _forged_gz == 403, str(_forged_gz))
    # SIGNING OUT IS A BUTTON (the review's 14): a link, which another site
    # can make a browser follow, signs nobody out; the posted button does.
    _owner.get("/demo-logout")
    _still = _owner.get(_drafts_url).status_code
    _out = _owner.post("/demo-logout")
    check("a link to /demo-logout signs nobody out; the Sign out button (a POST) does",
          _still == 200 and _out.status_code == 303 and _owner.get(_drafts_url).status_code == 401,
          f"after the link {_still}; the button {_out.status_code}")
    # Guesses at the key spend the attempts budget: at the cap, even the right
    # key is turned away, so it cannot be tried at request speed.
    _on.config["SKRIBL_RATE_MAX_ATTEMPTS"] = 3
    _guesser = _on.test_client()
    _from = {"REMOTE_ADDR": "203.0.113.77"}     # a fresh bucket, not this run's
    _codes = [_guesser.post("/demo-login", data={"key": f"guess-{i:02d}-guess-guess"}, base_url="https://localhost",
                            environ_base=_from).status_code for i in range(3)]
    _codes.append(_guesser.post("/demo-login", data={"key": _KEY}, base_url="https://localhost",
                                environ_base=_from).status_code)
    check("guessing the key is rate limited (429 once the attempts budget is spent)",
          _codes == [403, 403, 403, 429], str(_codes))
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

# ---------------------------------------------------------------------------
print("\nDRAFTS ON THE SERVER — a byte budget per author, and a list that reads no drawings (v317)")
# The count cap alone let one account hold 25 full payloads (~625 MB); and the
# list, which returns no payloads, loaded every one of them to discard it.
import sqlalchemy as _sa                                          # noqa: E402
_saved2 = {k: os.environ.get(k) for k in ("SKRIBL_MAX_DRAFT_BYTES", "DATABASE_URL", "SECRET_KEY",
                                          "SKRIBL_ALLOW_EPHEMERAL_SECRET", "SKRIBL_DEMO_IDENTITY")}
try:
    _env(DATABASE_URL=DB_URL, SECRET_KEY="harness-drafts-budget", SKRIBL_ALLOW_EPHEMERAL_SECRET="1",
         SKRIBL_DEMO_IDENTITY=None, SKRIBL_MAX_DRAFT_BYTES=str(64 * 1024))
    _da = _appmod.create_app()
    _pl = {"version": 1, "strokeGroups": [900],
           "strokes": [{"x": i % 500, "y": i % 400, "t": i, "color": "#ffffff", "size": 4} for i in range(900)]}
    with _da.app_context():
        _appmod.db.create_all()
        from skribl import drafts as _drafts
        _one = _drafts.save_draft("budget-user", _pl, kind="pad", title="one")
        _refused = None
        try:
            _drafts.save_draft("budget-user", _pl, kind="pad", title="two")
        except _drafts.DraftRejected as e:
            _refused = (e.status if hasattr(e, "status") else None, str(e))
        check("a draft past the author's byte budget is refused (409, with words to act on)",
              _refused is not None and _refused[0] == 409 and "Delete one" in _refused[1], repr(_refused))
        _over = _drafts.save_draft("budget-user", _pl, kind="pad", title="one again", public_id=_one["id"])
        check("...while overwriting a draft already inside it still works", _over["title"] == "one again", "")
        _other = _drafts.save_draft("someone-else", _pl, kind="pad", title="theirs")
        check("...and the budget is per author", bool(_other.get("id")), "")
        # THE THUMBNAIL COUNTS (the PRE-331 review's 10): stored beside the
        # payload, up to 200,000 characters a draft, it was outside the budget.
        # A drawing that fits alone, with a whole PNG that does not.
        import base64 as _b64, json as _json, struct as _st, zlib as _zl  # noqa: E401
        def _png_url(n):
            def chunk(t, d):
                return _st.pack(">I", len(d)) + t + d + _st.pack(">I", _zl.crc32(t + d) & 0xffffffff)
            rows = b"".join(b"\x00" + os.urandom(n * 3) for _ in range(n))
            raw = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", _st.pack(">IIBBBBB", n, n, 8, 2, 0, 0, 0))
                   + chunk(b"IDAT", _zl.compress(rows)) + chunk(b"IEND", b""))
            return "data:image/png;base64," + _b64.b64encode(raw).decode()
        _pl_chars = len(_json.dumps(_pl, separators=(",", ":")))
        _n = 16
        while len(_png_url(_n)) < 64 * 1024 - _pl_chars + 2048:
            _n += 8
        _pic = _png_url(_n)
        _tref = None
        try:
            _drafts.save_draft("pictured-user", _pl, kind="pad", title="with its picture", thumbnail=_pic)
        except _drafts.DraftRejected as e:
            _tref = (e.status, str(e))
        check("a thumbnail counts toward the byte budget: a drawing that fits alone, with a picture that does not, is refused (409)",
              _tref is not None and _tref[0] == 409,
              f"the drawing {_pl_chars} chars, the picture {len(_pic)}, the budget {64 * 1024}: {_tref!r}")
        _alone = _drafts.save_draft("pictured-user", _pl, kind="pad", title="without it")
        check("...while the same drawing without the picture saves", bool(_alone.get("id")), "")
        _stmts = []
        _eng = _appmod.db.engine
        def _grab(conn, cursor, statement, *a):
            _stmts.append(statement)
        _sa.event.listen(_eng, "before_cursor_execute", _grab)
        try:
            _appmod.db.session.expire_all()
            _items = _drafts.list_drafts("budget-user")
        finally:
            _sa.event.remove(_eng, "before_cursor_execute", _grab)
        _read = [x for x in _stmts if "skribl_drafts" in x]
        check("the drafts list reads no payloads from the database",
              _items and _read and not any("payload_json" in x for x in _read), " | ".join(_read)[:200])
        # The unauthenticated metadata route loaded up to 50 whole drawings.
        _stmts.clear()
        _sa.event.listen(_eng, "before_cursor_execute", _grab)
        try:
            with _da.test_request_context("/"):
                from flask import url_for as _u2
                _meta_url = _u2("skribl.get_skribl_meta", ids="abcdefghijk,bcdefghijkl")
            _mr = _da.test_client().get(_meta_url)
        finally:
            _sa.event.remove(_eng, "before_cursor_execute", _grab)
        _mread = [x for x in _stmts if "skribl_posts" in x]
        check("the posts-by-id metadata route reads no drawings either",
              _mr.status_code == 200 and _mread and not any("payload_json" in x for x in _mread),
              f"{_mr.status_code} " + " | ".join(_mread)[:160])
    # Draft writes spend the attempts budget posts do. Two allowed, the third
    # refused -- before any sign-in or CSRF is even looked at.
    _da.config["SKRIBL_RATE_MAX_ATTEMPTS"] = 2
    _dc = _da.test_client()
    with _da.test_request_context("/"):
        from flask import url_for as _u3
        _durl = _u3("skribl.create_saved_draft")
    _codes = [_dc.post(_durl, json={}, environ_base={"REMOTE_ADDR": "192.0.2.77"}).status_code for _ in range(3)]
    check("draft writes are rate limited like posts (the third inside the window is 429)",
          _codes[2] == 429 and 429 not in _codes[:2], str(_codes))
    # TAKE-DOWNS AND VISIBILITY CHANGES SPEND IT TOO (the PRE-331 review's 7):
    # each is a lookup and a key check, and nothing bounded how many one
    # connection could ask for. An id nobody has, so the first two are the
    # ordinary 404; a fresh address each, so neither row spends the other's.
    with _da.test_request_context("/"):
        _takeurl = _u3("skribl.delete_skribl", public_id="nobody-has-this-id")
    _del = [_dc.delete(_takeurl, environ_base={"REMOTE_ADDR": "192.0.2.78"}).status_code for _ in range(3)]
    _vis = [_dc.patch(_takeurl, json={"visibility": "public"},
                      environ_base={"REMOTE_ADDR": "192.0.2.79"}).status_code for _ in range(3)]
    check("take-downs and visibility changes are rate limited like other writes (the third is 429)",
          _del == [404, 404, 429] and _vis == [404, 404, 429], f"DELETE {_del}, PATCH {_vis}")
    # Rate limits key IPv6 by its /64: one subscriber holds the whole block.
    from skribl.ratelimit import _subject as _subj
    check("rate limits count an IPv6 /64 as one client, and an IPv4-mapped address as its IPv4",
          _subj("2001:db8:1:2::1") == _subj("2001:db8:1:2:ffff::9") != _subj("2001:db8:1:3::1")
          and _subj("::ffff:203.0.113.9") == "203.0.113.9" and _subj("198.51.100.7") == "198.51.100.7",
          f"{_subj('2001:db8:1:2::1')} {_subj('::ffff:203.0.113.9')}")
finally:
    for _k, _v in _saved2.items():
        _env(**{_k: _v})

# ---------------------------------------------------------------------------
print("\nNO DATABASE IN PRODUCTION — a refusal, not a SQLite file (v321 preflight, PF-022)")
# Unset, DATABASE_URL fell back to a SQLite file on a host whose disk most
# platforms rebuild on every deploy: every post gone at the next push, nothing
# in any log. Render is the marker used, because Render is where this runs.
_saved3 = {k: os.environ.get(k) for k in ("DATABASE_URL", "SECRET_KEY", "RENDER",
                                          "SKRIBL_ALLOW_SQLITE", "SKRIBL_ALLOW_EPHEMERAL_SECRET")}
try:
    _env(DATABASE_URL=None, SECRET_KEY="harness-no-database-" + "x" * 24, RENDER="1",
         SKRIBL_ALLOW_SQLITE=None, SKRIBL_ALLOW_EPHEMERAL_SECRET=None)
    try:
        _appmod.create_app()
        _refused = ""
    except RuntimeError as _e:
        _refused = str(_e)
    check("in production with no DATABASE_URL the app refuses to boot, and says which setting",
          "DATABASE_URL" in _refused and "SKRIBL_ALLOW_SQLITE" in _refused, _refused[:120] or "it booted")
    _env(SKRIBL_ALLOW_SQLITE="1")
    try:
        _appmod.create_app()
        _booted = True
    except RuntimeError:
        _booted = False
    check("...unless the deployment says a local file is what it means", _booted)
    _env(RENDER=None, SKRIBL_ALLOW_SQLITE=None)
    try:
        _appmod.create_app()
        _dev = True
    except RuntimeError:
        _dev = False
    check("...and a laptop with no DATABASE_URL still boots on SQLite", _dev)
finally:
    for _k, _v in _saved3.items():
        _env(**{_k: _v})

# ---------------------------------------------------------------------------
print("\nA READ-ONLY DATABASE — a post is still served, its play not counted (the PRE-331 review's 15)")
# A post read counts a play by writing, and a database that would not take
# the write (read only, a replica) made the read a 500 while the listing
# beside it served. The count is best effort now: the reader gets the post.
_saved4 = {k: os.environ.get(k) for k in ("DATABASE_URL", "SECRET_KEY", "SKRIBL_ALLOW_EPHEMERAL_SECRET")}
try:
    _ro_file = f"{tempfile.mkdtemp()}/readonly.db"
    _env(DATABASE_URL=f"sqlite:///{_ro_file}", SECRET_KEY="harness-read-only-" + "x" * 24)
    _rw = _appmod.create_app()
    with _rw.app_context():
        _appmod.db.create_all()
    _rwc = _rw.test_client()
    _pid = _rwc.post("/api/skribls", json=body("read only")).get_json()["id"]
    _env(DATABASE_URL=f"sqlite:///file:{_ro_file}?mode=ro&uri=true")
    _ro = _appmod.create_app()
    _ro.logger.setLevel(logging.CRITICAL)    # its one warning is expected here
    _reads = [_ro.test_client().get(f"/api/skribls/{_pid}", environ_base={"REMOTE_ADDR": f"198.51.100.{50 + _i}"})
              for _i in range(2)]

    def _plays():
        return next((i.get("views") for i in _rwc.get("/api/skribls?limit=80").get_json()["items"]
                     if i["id"] == _pid), None)
    _after_ro = _plays()
    _rwc.get(f"/api/skribls/{_pid}", environ_base={"REMOTE_ADDR": "198.51.100.60"})
    _after_rw = _plays()
    check("on a database that will not take a write, a post is still served, twice; its plays are not counted",
          [r.status_code for r in _reads] == [200, 200]
          and all((r.get_json() or {}).get("id") == _pid for r in _reads) and _after_ro == 0,
          f"{[r.status_code for r in _reads]}; plays after: {_after_ro}")
    check("...and the same read where the write is taken counts one, so the zero above measures something",
          _after_rw == 1, f"plays {_after_rw}")
finally:
    for _k, _v in _saved4.items():
        _env(**{_k: _v})

# ---------------------------------------------------------------------------
print("\nTHE HOST'S BRAND — its mark, label and hello on Skribl's editors, per request (brand_resolver)")
# The owner's yes (Nov 12): at the site's own address the Pad and Flip say
# the site's name, at the top and in the first-open hello; everywhere else
# they say skribl. Skribl cannot know a host's address or its mark, so it is
# a seam (skribl/brand.py, docs/INTEGRATION.md "Your brand on Skribl's
# editors"): the host answers per request, and an answer of nothing is
# Skribl as it is, BYTE FOR BYTE. Read from what the server sends, through
# throwaway hosts in this process. The site's own wiring and what is painted
# are verify_hello's (its site section).
import re as _re                                                    # noqa: E402
from flask import request as _request                              # noqa: E402

_HM = ('<svg class="host-mark" aria-hidden="true" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 50 34" '
       'fill="none" stroke="currentColor" stroke-width="2.3"><g transform="skewX(-8)">'
       '<path d="M 4,23.4 C 10,8 20,8 26,23.4 C 32,8 42,8 46,23.4 C 45,28 43,31 41,33"/>'
       '<path class="host-dot" stroke="#ff6f91" d="M 48.0,23.0 C 48.4,22.5 48.9,22.8 48.6,23.3"/></g></svg>')
_BRAND = {"mark": _HM, "label": "Example", "hello": "/static/example/hello.json?v=1", "hello_key": "example.hello.v1"}
_tmpl = tempfile.mkdtemp()
with open(os.path.join(_tmpl, "hostmark.html"), "w", encoding="utf-8") as _fh:
    _fh.write('<svg class="host-tmpl" viewBox="0 0 40 30" stroke="currentColor"><path d="M 2,23 L 38,23"/></svg>'
              '<!-- rendered in {{ request.host }} -->')


def _brand_host(resolver=None, **kw):
    """A throwaway host as host_app's, with templates of its own, and the
    brand seam given at init (or, with `later`, set afterwards)."""
    later = kw.pop("later", None)
    a = Flask(f"host-brand-{len(results)}", template_folder=_tmpl)
    a.config["SQLALCHEMY_DATABASE_URI"] = DB_URL
    a.config["SECRET_KEY"] = "harness-hostseams"
    a.testing = True                          # so a wrong answer raises here, where the suite sees it
    d = SQLAlchemy()
    d.init_app(a)
    skribl.init_skribl(a, session=lambda: d.session, csrf=False,
                       **({"brand_resolver": resolver} if resolver is not None else {}))
    if later is not None:
        skribl.set_brand_resolver(later, app=a)
    return a


def _page(app, route, host="brand.example"):
    """The page as sent, its nonce taken out; a page that raised says what."""
    try:
        r = app.test_client().get(route, base_url="http://" + host)
    except Exception as exc:  # noqa: BLE001 (a red row, not a stopped suite)
        return 500, f"raised {exc!r}"
    return r.status_code, _re.sub(r'nonce="[^"]*"', 'nonce="N"', r.get_data(as_text=True))


def _for_host(answer, host="brand.example"):
    return lambda: answer if _request.host == host else None


_plain = _brand_host()
_quiet = _brand_host(lambda: None)
_empty = _brand_host(lambda: {})
_brand = _brand_host(_for_host(_BRAND))
_later = _brand_host(later=_for_host(_BRAND))
_tpl = _brand_host(_for_host({"mark_template": "hostmark.html", "label": "Example"}))
_mark_only = _brand_host(_for_host({"mark": _HM, "label": "Example"}))
_hello_only = _brand_host(_for_host({"label": "Example", "hello": "/static/example/hello.json",
                                     "hello_key": "example.hello.v1"}))
_EDITORS = (("/skribl-pad", "Pad", "101"), ("/flip", "Flip", "95"))
_plainp = {r: _page(_plain, r) for r, _, _ in _EDITORS}
check("(setup) the Pad and Flip render in a throwaway host, with Skribl's own mark and hello",
      all(st == 200 and f'id="skink-m{sw}"' in h and "getItem('skribl.hello.v2')" in h and "brand-own" not in h
          for r, _, sw in _EDITORS for st, h in [_plainp[r]]),
      "; ".join(f"{r}: {_plainp[r][0]}" for r, _, _ in _EDITORS))
_same = {name: all(_page(app, r, host) == _page(_plain, r, host) for r, _, _ in _EDITORS)
         for name, app, host in (("answering None", _quiet, "brand.example"),
                                 ("answering an empty mapping", _empty, "brand.example"),
                                 ("answering for another address", _brand, "other.example"))}
check("no brand, an answer of None, an empty answer, or an answer for another address: the Pad and Flip "
      "are Skribl's, byte for byte", all(_same.values()), str(_same))
for _route, _mode, _sw in _EDITORS:
    _st, _h = _page(_brand, _route)
    _slot = _re.search(r'<span class="brand-own" style="--brand-own-units: ([\d.]+)">(.*?)</span>', _h, _re.S)
    _header = _h.split('<div class="header">', 1)[-1].split("</div>", 1)[0] if '<div class="header">' in _h else ""
    check(f"{_mode}, at the host's address: its mark stands where the signature stood, its markup as given, "
          "the box's height in the hand's units read from its viewBox (34); the signature is not in the header",
          _st == 200 and _slot is not None and _slot.group(1) == "34" and _slot.group(2) == _HM
          and f'id="skink-m{_sw}"' not in _h and _slot.start() < _h.find("brand-tag"),
          f"{_st}; slot {_slot.group(1) if _slot else None}; Skribl's signature in the page: {f'skink-m{_sw}' in _h}")
    # The lockup and the heading only: the rest of the page is Skribl's own
    # words (its menu's version line, How it works), which stay Skribl's.
    check(f"{_mode}: the lockup and the page's one heading name it: 'Example {_mode}'",
          f'aria-label="Example {_mode}" title="Example {_mode}"' in _h
          and _re.findall(r'<h1[^>]*>([^<]*)</h1>', _h) == [f"Example {_mode}"]
          and f'aria-label="Skribl {_mode}" title=' not in _h,
          f"heading {_re.findall(r'<h1[^>]*>([^<]*)</h1>', _h)}")
    check(f"{_mode}: its hello: the head reads the host's key, not Skribl's; the hello's drawing is the "
          "host's, its key handed to lib/hello.js, and it is named 'Example's signature'",
          "getItem('example.hello.v1')" in _h and "skribl.hello.v2" not in _h
          and 'data-hello="/static/example/hello.json?v=1" data-hello-key="example.hello.v1"' in _h
          and 'aria-label="Example\'s signature"' in _h,
          f"head {_re.findall(r'getItem[(]([^)]*)[)]', _h)[:3]}; hello {_re.findall(r'data-hello(?:-key)?=\"[^\"]*\"', _h)}")
    check(f"{_mode}: set afterwards (set_brand_resolver(fn, app=app)), the same page as given at init",
          _page(_later, _route) == (_st, _h))
_pad = _page(_brand, "/skribl-pad")[1]
check("Skribl's own signature stays where it is not the header's: 'made with' under the Pad's player",
      'id="skink-m65"' in _pad and 'aria-label="Skribl"' in _pad,
      "the brand is the editors' header and hello, not Skribl's player")
_tp = _page(_tpl, "/flip")[1]
check("a mark by a template the host names: rendered in the request, in the slot, at the hand's height when "
      "its box is the hand's (30)",
      '<span class="brand-own" style="--brand-own-units: 30"><svg class="host-tmpl"' in _tp
      and "<!-- rendered in brand.example -->" in _tp and 'aria-label="Example Flip"' in _tp
      and "getItem('skribl.hello.v2')" in _tp, "a brand with no hello keeps Skribl's")
_mo, _ho = _page(_mark_only, "/skribl-pad")[1], _page(_hello_only, "/skribl-pad")[1]
check("a brand of a mark alone keeps Skribl's hello and key; of a hello alone, Skribl's mark and name",
      "brand-own" in _mo and "getItem('skribl.hello.v2')" in _mo and "brand/hello.json" in _mo
      and "data-hello-key" not in _mo
      and "brand-own" not in _ho and 'id="skink-m101"' in _ho and 'aria-label="Skribl Pad"' in _ho
      and "getItem('example.hello.v1')" in _ho and 'aria-label="Example\'s signature"' in _ho)

# A WRONG ANSWER FAILS LOUDLY, on the first page that asks, naming what is
# wrong: never half a brand, and never a key or an address written into the
# page that could break out of where it is written.
_WRONG = {
    "a hello without its key": {"label": "X", "hello": "/h.json"},
    "a key without its hello": {"label": "X", "mark": _HM, "hello_key": "x.v1"},
    "Skribl's own key": dict(_BRAND, hello_key="skribl.hello.v2"),
    "a key with a quote in it": dict(_BRAND, hello_key="x');alert(1);('"),
    "a hello on another site": dict(_BRAND, hello="https://elsewhere.example/hello.json"),
    "a hello at //host": dict(_BRAND, hello="//elsewhere.example/hello.json"),
    "a hello with a quote in it": dict(_BRAND, hello='/h.json" onload="x'),
    "an unknown key": dict(_BRAND, colour="#fff"),
    "a mark and a template": dict(_BRAND, mark_template="hostmark.html"),
    "no label": {"mark": _HM},
    "a label alone": {"label": "X"},
    "a label of 41 characters": dict(_BRAND, label="x" * 41),
    "a mark drawn at another scale": dict(_BRAND, mark=_HM.replace('viewBox="0 0 50 34"', 'viewBox="0 0 300 150"')),
    "an answer that is not a mapping": ["mark"],
}
_loud = {}
for _why, _ans in _WRONG.items():
    try:
        _brand_host(lambda _a=_ans: _a).test_client().get("/skribl-pad")
        _loud[_why] = "rendered"
    except (ValueError, TypeError) as exc:
        _loud[_why] = None if "brand" in str(exc) else f"raised, unnamed: {exc}"
check("a wrong answer fails loudly on the first page that asks, saying what is wrong: "
      + ", ".join(_WRONG), not any(_loud.values()), str({k: v for k, v in _loud.items() if v}))
try:
    skribl.set_brand_resolver("not callable", app=_plain)
    check("a resolver that is not callable is refused when it is set", False)
except TypeError as exc:
    check("a resolver that is not callable is refused when it is set", True, str(exc))
check("it is a documented name: set_brand_resolver in skribl.__all__, and init_skribl takes brand_resolver",
      "set_brand_resolver" in skribl.__all__ and callable(getattr(skribl, "set_brand_resolver", None)))
# SKRIBL NAMES NO HOST. The seam's own code and markup name nobody, and
# nothing under skribl/ names the site's address, mark, hello or blush: the
# site reaches Skribl through the seam, never the other way (verify_social
# section 8 holds the imports).
_seam_files = [os.path.join(ROOT, "skribl", "brand.py"),
               os.path.join(ROOT, "skribl", "templates", "skribl", "_skribl_brand_own.html")]
_named = [f for f in _seam_files if "blooby" in open(f, encoding="utf-8").read().lower()]
_site_words = _re.compile(r"blooby\.app|blooby-hello|blooby\.hello|_blooby_mark|brand-blooby|blooby-blush", _re.I)
_leaks = []
for _dir, _subs, _files in os.walk(os.path.join(ROOT, "skribl")):
    _subs[:] = [x for x in _subs if x != "__pycache__"]
    for _f in _files:
        if _f.endswith((".py", ".html", ".js", ".css")):
            _fp = os.path.join(_dir, _f)
            if _site_words.search(open(_fp, encoding="utf-8", errors="ignore").read()):
                _leaks.append(os.path.relpath(_fp, ROOT))
check("Skribl names no host: the seam's code and markup name nobody, and nothing under skribl/ names the "
      "site's address, mark, hello or blush", not _named and not _leaks, f"named in {_named}; {_leaks}")

bad = [r for r in results if not r[0]]
print(f"\n{'=' * 62}\n{len(results) - len(bad)}/{len(results)} passed"
      + ("" if not bad else "  FAILURES: " + ", ".join(r[1] for r in bad)))
sys.exit(1 if bad else 0)
