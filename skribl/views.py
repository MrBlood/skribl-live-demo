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

from .core import HOT_DAYS, VIEW_CLEANUP_BATCH, VIEW_RETENTION_DAYS
from .models import SkriblView


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
