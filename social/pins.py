"""Pin this post (the owner's idea, Nov 23; the Pin mock's A and A, the
owner's "all yes", Nov 25; docs/SOCIAL-SITE.md section 17): one post of your
own kept first on your page's Posts tab, with a small "Pinned" line, for you
and for anyone who visits.

    /p/<id>/pin     POST {pinned}: your pin on a post of your own, put there
                    or taken away (JSON: {ok, pinned, was}), `was` the address
                    of the post pinned before, which goes back to its place

IN THE ⋯ (A): "Pin to your page" after Bookmark, on your own posts alone
(never a drawing shown outside a post, a comment, or anybody else's post),
and "Unpin from your page" once it is the one. The sheet goes down, and the
site's toast says what happened (and that your other pin went back to its
place, when there was one), with Undo (posts.js).

ONE AT A TIME: a person has one row (unique on person_id), and pinning
another post moves it.

ON YOUR PAGE (A): the pinned post leads the Posts tab, on its first page,
with "Pinned" where "You reposted" would be, and is not shown again further
down (posts.person_page's `skip`). Anybody who visits sees it so, by the
Posts tab's own rules (lead): a block either way, or anybody taken down, and
it is not there; a post taken down, only its author sees it, with the note.
Home is unchanged: newest first.

WHO MAY PIN: somebody signed in, not taken down, on a post of their own that
is not taken down. Taking a pin away always works on your own, by the
address alone: it is yours, whatever became of the post since.

DELETING IS REAL AND SAID IN CODE: a post goes with its pin (drop_post_pin,
from posts.drop_post), an account with its own (drop_person_pin, from
accounts.delete_person). The ON DELETE CASCADEs are the net under that.

Every state-changing request shows the site's token and Origin and is limited
per person (security.LIMITS, "pin") before it reads anything (security.over).
"""
import sqlalchemy as sa
from flask import jsonify, request

from .accounts import _json_error, _rests
from .models import Pin, Post
from .security import current_person, origin_ok, over, site, token_ok


def pinned_id(person):
    """The internal id of the post `person` pinned, or None (nobody, or none)."""
    if person is None:
        return None
    return site().session().execute(sa.select(Pin.post_id).where(Pin.person_id == person.id)).scalar()


def lead(person, viewer):
    """The first entry of `person`'s Posts tab for `viewer`: their pinned post
    as the tab shows a post, marked "pinned", or None. The tab's own rules
    (posts._posts_before): nobody a block hides either way or taken down
    (safety.hidden_ids), and a post taken down only to its own author."""
    from .posts import _entry
    from .safety import hidden_ids
    pid = pinned_id(person)
    if pid is None or person.id in hidden_ids(viewer):
        return None
    row = site().session().execute(
        sa.select(Post).where(Post.id == pid, Post.person_id == person.id)).scalar_one_or_none()
    if row is None or (row.taken_down_at is not None and (viewer is None or viewer.id != person.id)):
        return None
    entry = _entry(row, person)
    entry["pinned"] = True
    return entry


def drop_post_pin(post_id):
    """A post's pin, whoever's page it led (from posts.drop_post)."""
    site().session().execute(sa.delete(Pin).where(Pin.post_id == post_id)
                             .execution_options(synchronize_session=False))


def drop_person_pin(person_id):
    """A person's own pin (from accounts.delete_person)."""
    site().session().execute(sa.delete(Pin).where(Pin.person_id == person_id)
                             .execution_options(synchronize_session=False))


def register(bp):
    """Add the pin's route to the site's blueprint."""

    @bp.post("/p/<public_id>/pin")
    @_rests(json_answer=True)
    def pin_post(public_id):
        """Your pin on a post of your own, put there or taken away. Pinned,
        it replaces the one before (`was`, its address); taken away, it goes
        whatever became of the post since."""
        if not origin_ok() or not token_ok():
            return _json_error("stale", 403)
        me = current_person()
        if me is None:
            return _json_error("signed_out", 401)
        if over("pin", "person|" + me.public_id):
            return _json_error("limited", 429)
        body = request.get_json(silent=True)
        if not isinstance(body, dict) or not isinstance(body.get("pinned"), bool):
            return _json_error("bad", 400)
        sess = site().session()
        row = sess.execute(sa.select(Post).where(Post.public_id == str(public_id))).scalar_one_or_none()
        mine = sess.execute(sa.select(Pin).where(Pin.person_id == me.id)).scalar_one_or_none()
        was = None
        if mine is not None and (row is None or mine.post_id != row.id):
            was = sess.execute(sa.select(Post.public_id).where(Post.id == mine.post_id)).scalar()
        if body["pinned"]:
            from .comments import may_comment
            if not may_comment(me):
                # Taken down (Your Reports): nothing new from the account.
                return _json_error("taken_down", 403)
            if row is None or row.person_id != me.id or row.taken_down_at is not None:
                # Not there, somebody else's, or taken down: gone, as its page is.
                return _json_error("gone", 404)
            if mine is None:
                try:
                    with sess.begin_nested():
                        sess.add(Pin(person_id=me.id, post_id=row.id))
                        sess.flush()
                except sa.exc.IntegrityError:
                    # Pinned a moment ago, from another tap: one pin, moved here.
                    sess.execute(sa.update(Pin).where(Pin.person_id == me.id).values(post_id=row.id)
                                 .execution_options(synchronize_session=False))
            elif mine.post_id != row.id:
                mine.post_id = row.id
        else:
            # YOUR OWN, TAKEN AWAY whatever became of the post since; one that
            # was never pinned is gone only if the post is.
            if mine is not None and row is not None and mine.post_id == row.id:
                sess.delete(mine)
            elif row is None or row.person_id != me.id:
                return _json_error("gone", 404)
            was = None
        sess.flush()
        return jsonify({"ok": True, "pinned": body["pinned"], "was": was})
