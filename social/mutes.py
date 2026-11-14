"""Muting (phase 2, mutes; docs/SOCIAL-SITE.md "Built: mutes"), from the mute
mock and the owner's "Yes to all" (Nov 13): C, quiet everywhere, and rule 3,
mute and follow kept apart.

    /@<handle>/mute     mute them (JSON: {ok, muted, following}); nothing is
                        asked first, and the page offers Undo
    /@<handle>/unmute   unmute them (JSON from the ⋯, the toast's Undo or the
                        line on their page; a form from Settings, which comes
                        back to Settings)

MUTE IS A BREAK FROM SOMEBODY, NOT A WALL. One rule: what comes to you goes
quiet, and what you go to stays.

WHAT COMES TO YOU GOES QUIET (muted_ids, read once a request):
  * Home, Following and Everyone: their posts and drawings (posts.feed_page,
    in its query; a feed of one person's, More from, keeps them);
  * The Gallery (Explore: gallery.py, in its own query), and Skribl's
    listings of everybody's: their drawings,
    through the feed filter the host installs (muted_authors; app.py asks it
    only for a listing of everybody's, never for one person's own: Skribl
    tells the filter which, docs/INTEGRATION.md);
  * comments, on what you read and on your own: theirs fold to one quiet
    line, "Someone you muted said something. Show" (comments.thread marks
    them; comments.js opens one for the visit);
  * Activity: their comments, answers, likes and follows leave it, and never
    light the bell's dot (activity.py).
WHAT YOU GO TO STAYS: their page (which says "You muted Theo · Unmute" to you
alone), their posts and their drawings' pages, More from, their skribls on
their page. The visibility policy is untouched: a mute never hides a page.

COUNTS AND "LIKED BY…" STAY TRUE, for everybody and for you: a mute changes
what reaches you, never a number (a folded comment is counted, their like
is in the count and in "Liked by…", their follow in "Followed by…").

ONE WAY, AND QUIET. Nothing changes on their side, and nobody is told: their
page, posts, counts and who follows them look the same to them and to
everybody else. Who you muted is yours alone (Settings, Muted).

MUTE AND FOLLOW STAY APART (the owner's rule 3). Muting never unfollows, so
nothing changes on their side, not even their own list of who follows them;
the route says whether you follow them, so the toast can say "You still
follow them." Their posts stay out of Home, Following too, until you unmute.

A BLOCK is the strong tool, and leaves a mute standing: somebody you muted
and then blocked is listed under Blocked (Muted lists nobody a block either
way, or a takedown, hides); unblock them and they are still muted.

WHO MAY MUTE: somebody signed in; anybody who is there for them (not taken
down, no block either way), never themselves; the token and Origin first,
then the limit (security.LIMITS, "mute": 60 an hour, mutes and unmutes
alike). Unmuting lifts your own row, whoever it named.

DELETING AN ACCOUNT takes its mutes, both ways, in code (drop_person_mutes,
from accounts.delete_person); the ON DELETE CASCADEs are the net.
"""
import sqlalchemy as sa
from flask import g, has_request_context, jsonify, redirect, request, url_for

from .accounts import _json_error, _rests
from .models import PERSON_PREFIX, Mute, Person
from .safety import _person_by_handle, between, hidden_ids
from .security import current_person, origin_ok, over, read_aside, site, token_ok


def _muted(public_id):
    """(ids, public ids) of everybody the person with this public id muted: ONE
    READ A REQUEST, shared by the site's pages (muted_ids) and the host's feed
    filter (muted_authors), so Home asks it once whatever it shows; beside the
    request's own work (read_aside), on the people's public-id index and the
    pair's."""
    cache = g.setdefault("social_muted", {}) if has_request_context() else {}
    if public_id in cache:
        return cache[public_id]
    m, me, other = Mute.__table__, Person.__table__.alias("me"), Person.__table__.alias("other")
    rows = read_aside(sa.select(m.c.muted_id, other.c.public_id)
                      .join(me, me.c.id == m.c.muter_id).join(other, other.c.id == m.c.muted_id)
                      .where(me.c.public_id == public_id))
    out = (frozenset(r[0] for r in rows), frozenset(r[1] for r in rows))
    cache[public_id] = out
    return out


def muted_ids(person):
    """The ids of everybody `person` muted (a person row or the request's
    snapshot; None for nobody, whose set is empty), read once a request."""
    if person is None:
        return frozenset()
    return _muted(person.public_id)[0]


def _forget():
    """A mute or an unmute was written: this request reads them afresh."""
    if has_request_context():
        g.pop("social_muted", None)


def i_muted(me, who):
    """Whether `me` muted `who`."""
    if me is None or who is None or me.id == who.id:
        return False
    return who.id in muted_ids(me)


def muted_authors(viewer_id):
    """For the host's feed filter (app.py; docs/SOCIAL-SITE.md "Built:
    mutes"): the public ids of everybody this viewer (Skribl's current user
    id, or None) muted, for a listing of everybody's to leave out. Empty for
    anybody who is not one of the site's people. The same read as
    muted_ids', once a request."""
    me = viewer_id if isinstance(viewer_id, str) and viewer_id.startswith(PERSON_PREFIX) else None
    if me is None:
        return frozenset()
    return _muted(me)[1]


def muted_people(person):
    """The people `person` muted, newest first, for Settings: nobody a block
    either way or a takedown hides (they are under Blocked, or nobody's, and
    come back here once that is lifted)."""
    hid = sorted(hidden_ids(person))
    q = (sa.select(Person).join(Mute, Mute.muted_id == Person.id).where(Mute.muter_id == person.id)
         .order_by(Mute.created_at.desc(), Mute.id.desc()))
    if hid:
        q = q.where(Person.id.notin_(hid))
    return site().session().execute(q).scalars().all()


def drop_person_mutes(person_id):
    """An account's mutes, both ways (accounts.delete_person)."""
    site().session().execute(sa.delete(Mute).where(
        sa.or_(Mute.muter_id == person_id, Mute.muted_id == person_id)).execution_options(synchronize_session=False))


def register(bp):
    """Add the mutes' routes to the site's blueprint."""

    @bp.post("/@<handle>/mute")
    @_rests(json_answer=True)
    def mute(handle):
        """Mute somebody: quiet everywhere, for you alone. Nothing is asked
        first (the page offers Undo), and they aren't told."""
        if not origin_ok() or not token_ok():
            return _json_error("stale", 403)
        me = current_person()
        if me is None:
            return _json_error("signed_out", 401)
        if over("mute", "person|" + me.public_id):
            return _json_error("limited", 429)
        who = _person_by_handle(handle)
        if who is None or who.id == me.id or who.taken_down_at is not None or between(me, who):
            # Nobody by that name, yourself, taken down, or a block either way.
            return _json_error("gone", 404)
        sess = site().session()
        if sess.execute(sa.select(Mute.id).where(Mute.muter_id == me.id, Mute.muted_id == who.id)).first() is None:
            try:
                with sess.begin_nested():
                    sess.add(Mute(muter_id=me.id, muted_id=who.id))
                    sess.flush()
            except sa.exc.IntegrityError:
                pass            # muted a moment ago, from another tap: one row
        sess.flush()
        _forget()
        # RULE 3: a mute never touches a follow; the toast says if one stands.
        from .follows import is_following
        return jsonify({"ok": True, "muted": True, "following": is_following(me, who)})

    @bp.post("/@<handle>/unmute")
    @_rests()
    def unmute(handle):
        """Unmute somebody: everything comes back, just as it was. From the ⋯,
        the toast's Undo or the line on their page (JSON), or from Settings (a
        form, which comes back to Settings)."""
        form = not request.is_json
        if not origin_ok() or not token_ok():
            return _json_error("stale", 403) if not form else redirect(url_for("social.you"), 303)
        me = current_person()
        if me is None:
            return _json_error("signed_out", 401) if not form else redirect(url_for("social.signin"), 303)
        if over("mute", "person|" + me.public_id):
            return _json_error("limited", 429) if not form else redirect(url_for("social.you", note="limited"), 303)
        who = _person_by_handle(handle)
        if who is not None:
            site().session().execute(sa.delete(Mute).where(Mute.muter_id == me.id, Mute.muted_id == who.id)
                                     .execution_options(synchronize_session=False))
            site().session().flush()
        _forget()
        if form:
            return redirect(url_for("social.you", note="unmuted") + "#mutedTitle", 303)
        return jsonify({"ok": True, "muted": False})

    return bp
