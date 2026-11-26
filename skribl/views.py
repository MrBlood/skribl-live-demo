"""Retention for `skribl_views` — the rows Hot is computed from.

WHY THIS FILE EXISTS (pre-v305 audit, PRESEAL-003). A play is recorded as one
row per (post, client hash, UTC day) so that Hot can rank by plays in the last
`HOT_DAYS`. Nothing removed those rows. They cascade away when the post is
deleted and not before, so a live post accumulated a pseudonymous viewing
history for its whole life while the product only ever reads a week of it.

`SkriblPost.views_total` already carries the lifetime figure the UI shows, so
the old rows are not the count — they are a record of WHEN a client watched,
kept past any use. Keeping them was nobody's decision; it was the absence of
one. This is that decision, written down: the rows live `VIEW_RETENTION_DAYS`
and then go.

THE HOT WINDOW IS A FLOOR, NOT A SUGGESTION. The cutoff is the OLDER of the
configured retention and `HOT_DAYS`, so a host that sets
`SKRIBL_VIEW_RETENTION_DAYS=1` gets a shorter retention than the default and
still gets a correct Hot, rather than a ranking that quietly starts reading a
window whose rows have been deleted underneath it. Misconfiguration should cost
nothing that cannot be seen.

TWO CALLERS, ON PURPOSE:

  * `purge_views(session)` — the maintenance entrypoint a host schedules,
    alongside `sweep_orphans`. It takes an explicit session and does NOT
    commit, exactly like every other write in this package: the host owns the
    transaction (docs/INTEGRATION.md, "Transaction ownership").

  * an opportunistic call from the route that writes a view, bounded by
    `VIEW_CLEANUP_BATCH` and swallowing its own errors, so a deployment that
    never schedules anything still does not accumulate for ever. This follows
    the rate limiter's janitor, and for the same reason: a cleanup running
    inside somebody's request must never take their request down with it.
"""
from datetime import datetime, timedelta, timezone

import sqlalchemy as sa
from flask import current_app

from .core import HOT_DAYS, VIEW_CLEANUP_BATCH, VIEW_RETENTION_DAYS
from .models import SkriblPost, SkriblView, session
from .ratelimit import _client_ip, _rate_key


def view_cutoff(older_than_days=None):
    """The instant before which view rows may be deleted.

    Never inside the Hot window, whatever is asked for — see the module note.
    """
    days = VIEW_RETENTION_DAYS if older_than_days is None else int(older_than_days)
    return datetime.now(timezone.utc) - timedelta(days=max(days, HOT_DAYS))


def purge_views(s, older_than_days=None, batch=None):
    """Delete view rows past the retention window. Returns how many went.

    Bounded by `batch` (default `VIEW_CLEANUP_BATCH`) so one call cannot turn
    into an unbounded delete on a large table. FLUSHES, NEVER COMMITS: the
    caller's transaction is the caller's.

    Selected by id first and deleted by id, rather than one DELETE with a
    timestamp predicate, so the batch is exactly the rows that were looked at
    — a predicate delete with a LIMIT is not portable across SQLite and
    PostgreSQL, and the two backends disagreeing about how much a "batch" is
    would be a difference nobody would notice until it mattered.
    """
    cutoff = view_cutoff(older_than_days)
    size = VIEW_CLEANUP_BATCH if batch is None else max(1, int(batch))
    ids = [row[0] for row in s.query(SkriblView.id)
           .filter(SkriblView.created_at < cutoff)
           .order_by(SkriblView.id)
           .limit(size).all()]
    if not ids:
        return 0
    (s.query(SkriblView)
     .filter(SkriblView.id.in_(ids))
     .delete(synchronize_session=False))
    s.flush()
    return len(ids)


# ---- A play, counted -----------------------------------------------------
# Moved here from the routes (each note below says why its lines are as they
# are) so that the one count serves both doors: Skribl's own player's fetch
# (routes.py, GET /api/skribls/<id>) and a play a host serves of a drawing it
# composes (count_play, below).

def count_view(post):
    """Count a play; True when it was a new one.

    BEST EFFORT, AND NEVER AT THE READER'S COST (the PRE-331 review's
    15). A post read on a database that will not take the write (read
    only, a replica, a file locked by another writer) was a 500: the
    play's insert failed and took the read with it, while the listing
    beside it served. The count runs inside one savepoint now, so a
    store that refuses it unwinds the count alone; the host's
    transaction is intact and the reader gets the post. Said once per
    app in the log, not once per read.
    """
    s = session()
    try:
        with s.begin_nested():
            counted = _record_view(s, post)
    except sa.exc.SQLAlchemyError as exc:
        ext = current_app.extensions.setdefault("skribl", {})
        if not ext.get("view_count_warned"):
            ext["view_count_warned"] = True
            current_app.logger.warning(
                "skribl: a play could not be counted (%s); the post was "
                "served without it. Said once.", type(exc).__name__)
        return False
    if counted:
        # THE JANITOR RIDES THE WRITE, not the read: only a NEW row
        # triggers it, so the work is proportional to plays rather than
        # to page loads, and it is bounded and best-effort. A deployment
        # that never schedules purge_views() still does not accumulate
        # view rows for ever (PRESEAL-003). In its own savepoint and
        # swallowed on purpose, exactly as the rate limiter's janitor
        # is: a cleanup inside somebody's request must never take their
        # request down with it, and the next play tries again.
        try:
            with s.begin_nested():
                purge_views(s)
        except Exception:                                # pragma: no cover
            pass
    return counted

def _record_view(s, post):
    who = _rate_key(_client_ip())
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    seen = (s.query(SkriblView.id)
            .filter(SkriblView.post_id == post.id, SkriblView.viewer_hash == who,
                    SkriblView.day == day).first())
    if seen is not None:
        return False
    try:
        with s.begin_nested():
            s.add(SkriblView(post_id=post.id, viewer_hash=who, day=day))
            s.flush()
    except sa.exc.IntegrityError:
        return False
    # ATOMIC, NOT READ-MODIFY-WRITE (EXT-P1-4). This was
    # `post.views_total = (post.views_total or 0) + 1`, which reads the
    # value into Python and writes back a number computed from a snapshot.
    # The uniqueness row above stops ONE viewer being counted twice; it
    # does nothing about two DIFFERENT viewers whose requests interleave,
    # and those are exactly the requests a popular post gets. Both read N,
    # both write N+1, one play is gone. Under-counting is silent, permanent
    # and worst on the posts that matter most, and Hot ranks on this
    # column. The database does the addition now, so concurrent increments
    # serialise on the row instead of racing in the application.
    s.query(SkriblPost).filter(SkriblPost.id == post.id).update(
        {SkriblPost.views_total:
            sa.func.coalesce(SkriblPost.views_total, 0) + 1},
        synchronize_session=False)
    return True


def count_play(public_id, viewer_id=None):
    """A PLAY A HOST SERVES, counted as Skribl counts its own player's fetch
    (count_view: once a client a UTC day, the lifetime total moved by the
    database). For a drawing the host composes and plays through the
    player's `api` seam, which Skribl's route never sees: Blooby's two-hands
    draw-back plays Both from the site, so its plays went uncounted
    (DECISIONS.md, "Draw back, two hands"). Only a post the viewer may see
    (`viewer_id`, as read_payload takes it) is counted. True when the play
    was a new one. The host owns the commit, as on every write here."""
    if not public_id:
        return False
    post = session().query(SkriblPost).filter(SkriblPost.public_id == str(public_id)[:32]).first()
    if post is None or not post.visible_to(viewer_id):
        return False
    return count_view(post)
