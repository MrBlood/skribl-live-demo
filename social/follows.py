"""Following people (phase 2, follows; docs/SOCIAL-SITE.md "Built: follows"),
from the follow mock and the owner's "Yes to all" (Nov 13): B, yours alone;
and the counts, from the quick-patterns mock's A (the owner's "Yes on
everything", Nov 13, the map's step 5), which replaced B's "no counts, ever".

    /@<handle>/follow   POST {following}: follow them, or not (JSON: {ok,
                        following, counts}: counts is their page's counts as
                        it shows them to you, follow_counts' own markup); a
                        yes or a no, never "toggle", so a retry cannot flip
                        it twice
    /home/show          POST {show}: what Home opens on, "following" or
                        "everyone", kept for the account (JSON)

COUNTS ON EVERY PROFILE (counts()): under the @handle, "3 followers · 2
following"; "New here" while nobody follows them yet, never "0 followers";
a following count only when it isn't zero. THE LISTS STAY YOURS ALONE: on
your own page the counts open them (Followers | Following, newest first,
with when; they took the place of "Followed by…"), and on anybody else's
the counts are words, not links: nobody but you is ever sent your lists,
not in the page and not in its source.

COUNTED BY THE VIEWER, as likes are: anybody hidden from you (a block
either way, or taken down: safety.hidden_ids) is in no count and no list,
and in nobody's Following. A mute changes no number (mutes.py): somebody
you muted who follows them is counted, as their like is.

WHO MAY FOLLOW: somebody signed in and not taken down, anybody else who is
there for them (not taken down, no block either way), never themselves; the
token and Origin first, then the limit (security.LIMITS, "follow"). A tap on
Following asks once ("Unfollow Theo?"); nobody is told either way.

FOLLOWING AGAIN DOESN'T TELL THEM TWICE: unfollowing keeps the row with the
time it ended (Follow.ended_at), so following again keeps the first time,
and Activity, which reads it, has nothing new to say. A BLOCK ENDS IT BOTH
WAYS AND FOR GOOD: the rows go (end_between, from safety.py's block), so
lifting the block brings nothing back, and the route refuses a follow while
it stands. DELETING AN ACCOUNT takes its follows both ways, in code
(drop_person_follows, from accounts.delete_person); the ON DELETE CASCADEs
are the net.

HOME'S FOLLOWING (home_items): the people you follow and you, newest first,
nothing ranked; then "You're caught up with the people you follow" and
Fresh from everyone (everybody else's, so nothing shows twice), so Home
never runs out. Somebody who follows nobody gets a kind card ("You're not
following anyone yet", Look around) and everyone's. One read of posts on
their indexes (the people you follow as a subquery, never a list sent per
card), as Everyone's page reads them: posts only, as all of Home (the map's
step 3; a drawing shown outside a post keeps its own page and its maker's).
Home opens on Following
once you follow somebody, on Everyone before that, and on your own pick
once you make one (Person.home_feed).
"""
import sqlalchemy as sa
from flask import jsonify, render_template, request

from .accounts import _json_error, _rests
from .models import HOME_FEEDS, Follow, Person, utcnow
from .safety import _person_by_handle, between, hidden_ids
from .security import current_person, origin_ok, over, site, token_ok

#: The most people each list shows, newest first (the line's count is exact).
WHO_MAX = 200

#: Activity reads at most this many follows of you, newest first.
ACTIVITY_READ = 300


def _on():
    """A follow that stands (not ended)."""
    return Follow.ended_at.is_(None)


def is_following(me, who):
    """Whether `me` follows `who` now."""
    if me is None or who is None or me.id == who.id:
        return False
    return site().session().execute(
        sa.select(Follow.id).where(Follow.follower_id == me.id, Follow.followed_id == who.id, _on())).first() is not None


def followed_ids(me):
    """SQL: the ids of the people `me` follows now (a subquery, for Home's
    read of their posts)."""
    return sa.select(Follow.followed_id).where(Follow.follower_id == me.id, _on())


def circle(me):
    """The people `me` follows now that the pages show them (nobody hidden):
    [(id, public_id)]."""
    hid = sorted(hidden_ids(me))
    q = (sa.select(Person.id, Person.public_id).join(Follow, Follow.followed_id == Person.id)
         .where(Follow.follower_id == me.id, _on()))
    if hid:
        q = q.where(Person.id.notin_(hid))
    return [tuple(r) for r in site().session().execute(q).all()]


def _people(me, which, *cols):
    """`cols` of the rows of `which` ("followers": who follows `me`;
    "following": whom they follow) as SQL, the person on the other end
    joined when a column of theirs is asked; nobody hidden from `me`."""
    hid = sorted(hidden_ids(me))
    if which == "followers":
        mine, other = Follow.followed_id, Follow.follower_id
    else:
        mine, other = Follow.follower_id, Follow.followed_id
    q = sa.select(*cols).select_from(Follow)
    if any(c is Person for c in cols):
        q = q.join(Person, Person.id == other)
    q = q.where(mine == me.id, _on())
    if hid:
        q = q.where(other.notin_(hid))
    return q


def people(me, which, limit=WHO_MAX):
    """Who follows `me` ("followers") or whom they follow ("following"),
    newest first: [(follow, person)], nobody hidden from them."""
    q = _people(me, which, Follow, Person).order_by(Follow.created_at.desc(), Follow.id.desc()).limit(limit)
    return site().session().execute(q).all()


def how_many(me, which):
    """How many people the lists hold, counted as they show them."""
    return int(site().session().execute(_people(me, which, sa.func.count())).scalar() or 0)


def counts(viewer, who):
    """A profile's counts as `viewer` is shown them (None: signed out):
    {"followers": how many follow `who`, "following": how many they follow}.
    COUNTED BY THE VIEWER, as a like's count is: nobody hidden from the
    viewer (a block either way, or taken down: safety.hidden_ids) is
    counted; a mute changes no number. On your own page they are your lists'
    lengths (how_many). One read, both counts on the follows' own indexes."""
    hid = sorted(hidden_ids(viewer))

    def n(mine, other):
        q = sa.select(sa.func.count()).select_from(Follow).where(mine == who.id, _on())
        if hid:
            q = q.where(other.notin_(hid))
        return q.scalar_subquery()
    row = site().session().execute(sa.select(n(Follow.followed_id, Follow.follower_id),
                                             n(Follow.follower_id, Follow.followed_id))).one()
    return {"followers": int(row[0] or 0), "following": int(row[1] or 0)}


def for_owner(me, n):
    """What your own page shows of follows, and nobody else's: both lists,
    for the sheet its counts open (`n`, counts()'s for you), on the tab of
    the first count it shows. None for nobody signed in, and with nobody
    either way, when no count opens anything."""
    if me is None or not (n["followers"] or n["following"]):
        return None
    return {"followers": people(me, "followers"), "following": people(me, "following"),
            "tab": "followers" if n["followers"] else "following"}


def of_me(me, hidden, limit=ACTIVITY_READ):
    """The follows of `me` as Activity has them: those that stand, newest
    first, nobody in `hidden`: [(follow, person)]."""
    q = (sa.select(Follow, Person).join(Person, Person.id == Follow.follower_id)
         .where(Follow.followed_id == me.id, _on()))
    hid = sorted(hidden)
    if hid:
        q = q.where(Follow.follower_id.notin_(hid))
    q = q.order_by(Follow.created_at.desc(), Follow.id.desc()).limit(limit)
    return site().session().execute(q).all()


# ---- ending and deleting ----------------------------------------------------------

def end_between(a_id, b_id):
    """A block's: every follow between two people, both ways, gone (so lifting
    the block brings none back)."""
    site().session().execute(sa.delete(Follow).where(sa.or_(
        sa.and_(Follow.follower_id == a_id, Follow.followed_id == b_id),
        sa.and_(Follow.follower_id == b_id, Follow.followed_id == a_id))).execution_options(synchronize_session=False))


def drop_person_follows(person_id):
    """An account's follows, both ways (accounts.delete_person)."""
    site().session().execute(sa.delete(Follow).where(
        sa.or_(Follow.follower_id == person_id, Follow.followed_id == person_id)).execution_options(synchronize_session=False))


# ---- Home: Following and Everyone -------------------------------------------------

def home_shows(me):
    """What Home opens on for `me`: their own pick, once they have made one;
    else Following once they follow somebody, and Everyone before that."""
    picked = site().session().execute(sa.select(Person.home_feed).where(Person.id == me.id)).scalar()
    if picked in HOME_FEEDS:
        return picked
    return "following" if circle(me) else "everyone"


#: How a page of Following says where it ended: the people you follow and
#: you ("f."), then everybody else ("e."), each followed by Home's own cursor
#: (posts._cursor); "e." alone is everybody else's from the start. Home's
#: own cursors (Everyone's, and Following's for somebody who follows nobody,
#: which is everyone's) are never one of these: a base64 word has no dot.
_FOLLOWING, _REST = "f.", "e."

#: When the people you follow run out part-way down a page, at least this
#: many of everybody else's follow on it.
_REST_MIN = 5

#: How many pages of everybody else's a page reads, at most, looking for one
#: that is not all the people you follow.
_REST_TRIES = 4


def is_following_cursor(raw):
    return isinstance(raw, str) and raw[:2] in (_FOLLOWING, _REST)


def _rest(me, ids, before, limit):
    """Everybody else's (not `ids`: the people `me` follows, and them), newest
    first, as Everyone's pages have them: (entries, Everyone's cursor or None)."""
    from .posts import feed_page
    out, nxt = [], before
    for _ in range(_REST_TRIES):
        page, nxt = feed_page(nxt, limit=limit, viewer=me)
        out += [e for e in page if e["who"].id not in ids]
        if out or not nxt:
            break
    return out, nxt


def home_items(me, show, before=None):
    """A page of Home's `show` for `me`: (items, next cursor or None, show).
    Each item is a card's entry, or a marker: {"extra": "none"} (you follow
    nobody yet), {"extra": "caught"} (the people you follow end here) or
    {"extra": "fresh"} (everybody else's from here). A cursor of Following's
    own says which part it is in."""
    from .posts import PAGE, _cursor, feed_page
    if show != "following" or me is None:
        page, nxt = feed_page(before, viewer=me)
        return page, nxt, "everyone"
    if before and not is_following_cursor(before):
        # Somebody who follows nobody: Following is everyone's, under the card.
        page, nxt = feed_page(before, viewer=me)
        return page, nxt, "following"
    them = circle(me)
    if not them:
        if before:
            # Following's own cursor, from before they stopped following
            # everybody: everyone's carries on from there, the card not again.
            page, nxt = feed_page(before[len(_FOLLOWING):] or None, viewer=me)
            return page, nxt, "following"
        page, nxt = feed_page(None, viewer=me)
        return [{"extra": "none"}, {"extra": "fresh"}] + page, nxt, "following"
    ids = {pid for pid, _ in them} | {me.id}
    if before and before.startswith(_REST):
        page, nxt = _rest(me, ids, before[len(_REST):] or None, PAGE)
        return page, (_REST + nxt if nxt else None), "following"
    page, nxt = feed_page(before[len(_FOLLOWING):] if before else None, viewer=me, among=followed_ids(me))
    if nxt:
        return page, _FOLLOWING + nxt, "following"
    rest, rnxt = _rest(me, ids, None, max(PAGE - len(page), _REST_MIN))
    items = page + [{"extra": "caught"}]
    if rest or rnxt:
        items += [{"extra": "fresh"}] + rest
    return items, (_REST + rnxt if rnxt else None), "following"


def home_cards(items, me):
    """`items` with each entry made a card (posts.cards: one read of each
    kind for all of them), the markers as they are."""
    from .posts import cards
    entries = [i for i in items if "extra" not in i]
    made = iter(cards(entries, me)) if entries else iter(())
    return [i if "extra" in i else next(made) for i in items]


# ---- the routes ---------------------------------------------------------------------

def register(bp):
    """Add the follows' routes to the site's blueprint."""

    @bp.post("/@<handle>/follow")
    @_rests(json_answer=True)
    def follow(handle):
        """Follow somebody, or stop: {following: true or false}."""
        if not origin_ok() or not token_ok():
            return _json_error("stale", 403)
        me = current_person()
        if me is None:
            return _json_error("signed_out", 401)
        if over("follow", "person|" + me.public_id):
            return _json_error("limited", 429)
        from .comments import may_comment
        if not may_comment(me):
            # Taken down (Your Reports): nothing new from the account.
            return _json_error("taken_down", 403)
        body = request.get_json(silent=True)
        if not isinstance(body, dict) or not isinstance(body.get("following"), bool):
            return _json_error("bad", 400)
        who = _person_by_handle(handle)
        if who is None or who.id == me.id or who.taken_down_at is not None or between(me, who):
            # Nobody by that name, yourself, taken down, or a block either way.
            return _json_error("gone", 404)
        sess = site().session()
        pair = sa.and_(Follow.follower_id == me.id, Follow.followed_id == who.id)
        if body["following"]:
            row = sess.execute(sa.select(Follow).where(pair)).scalar_one_or_none()
            if row is None:
                try:
                    with sess.begin_nested():
                        sess.add(Follow(follower_id=me.id, followed_id=who.id))
                        sess.flush()
                except sa.exc.IntegrityError:
                    pass            # followed a moment ago, from another tap: one row
            elif row.ended_at is not None:
                # Following again: the first time stays, so they aren't told twice.
                row.ended_at = None
        else:
            sess.execute(sa.update(Follow).where(pair, _on()).values(ended_at=utcnow())
                         .execution_options(synchronize_session=False))
        sess.flush()
        # THE COUNTS FOLLOW THE TAP: their page's counts as it shows them to
        # you, in its own markup (follows.js puts them in while unseen).
        return jsonify({"ok": True, "following": is_following(me, who),
                        "counts": render_template("social/_follow_counts.html", n=counts(me, who), mine=False)})

    @bp.post("/home/show")
    @_rests(json_answer=True)
    def home_show():
        """What Home opens on, as picked on its pill: {show}."""
        if not origin_ok() or not token_ok():
            return _json_error("stale", 403)
        me = current_person()
        if me is None:
            return _json_error("signed_out", 401)
        if over("home-pick", "person|" + me.public_id):
            return _json_error("limited", 429)
        body = request.get_json(silent=True)
        show = body.get("show") if isinstance(body, dict) else None
        if show not in HOME_FEEDS:
            return _json_error("bad", 400)
        site().session().execute(sa.update(Person).where(Person.id == me.id).values(home_feed=show))
        site().session().flush()
        return jsonify({"ok": True, "show": show})

    return bp
