"""Reading the report queue from a host's own admin page (docs/INTEGRATION.md,
"Your own reports page"), after v330: the Skribl site's Reports page (the
owner's "all yes" to Safety, Nov 12) lists what people reported on Skribl's own
pages (the Gallery's tiles, a drawing's link page) beside its own reports.

    list_reports(limit=100)   the open reports, a group per drawing: a
                              child's safety first, then the most reported,
                              each with its reasons, notes and times
    close_reports(public_id)  close one drawing's open reports: looked at

Taking one down is set_post_visibility(id, "withheld", require_author=False),
as `python -m skribl.takedown <id> --visibility withheld` does: hidden from
everybody but its signed-in author, and only an operator lifts it. Neither of
these takes anything down by itself, and nothing here names a reporter: the
queue keeps only a salted hash of who reported (one row per reporter per
drawing). The command-line tool reads the same groups (takedown --reports).

Both read and write through Skribl's session, inside the host's transaction:
they flush and never commit (docs/INTEGRATION.md, "Transactions").
"""
from datetime import timezone

from .models import SkriblPost, SkriblReport, session

__all__ = ["open_reports", "list_reports", "close_reports"]


def open_reports():
    """Every drawing with open reports: any with a report for a child's safety
    first, then most-reported first, newest report first within each:
    [(post, [reports...]), ...]."""
    s = session()
    rows = (s.query(SkriblReport)
            .filter(SkriblReport.state == "open")
            .order_by(SkriblReport.created_at.desc(), SkriblReport.id.desc())
            .all())
    by_post = {}
    for r in rows:
        by_post.setdefault(r.post_id, []).append(r)
    posts = {p.id: p for p in s.query(SkriblPost)
             .filter(SkriblPost.id.in_(list(by_post))).all()} if by_post else {}
    groups = [(posts[pid], rs) for pid, rs in by_post.items() if pid in posts]
    groups.sort(key=lambda g: (not any(r.reason == "child_safety" for r in g[1]), -len(g[1]), g[0].public_id))
    return groups


def _iso(when):
    if when is None:
        return None
    return (when.replace(tzinfo=timezone.utc) if when.tzinfo is None else when).isoformat()


def list_reports(limit=100):
    """The open reports, a group per drawing, in the queue's order: a child's
    safety first, then the most reported. Each group is a dict:

        id            the drawing's public id
        title         its title
        user_id       its author, as your host knows them (or None)
        visibility    where it stands now
        count         how many open reports
        reasons       {reason: how many}, from skribl.core.REPORT_REASONS
        notes         what reporters wrote, newest first (no names: none kept)
        child_safety  True if any report is for a child's safety
        first, latest when the first and the newest report came (ISO, UTC)

    At most `limit` groups (1-500)."""
    limit = max(1, min(int(limit), 500))
    out = []
    for post, rows in open_reports()[:limit]:
        reasons = {}
        for r in rows:
            reasons[r.reason] = reasons.get(r.reason, 0) + 1
        out.append({"id": post.public_id, "title": post.title, "user_id": post.user_id,
                    "visibility": post.visibility, "count": len(rows), "reasons": reasons,
                    "notes": [r.note for r in rows if r.note],
                    "child_safety": "child_safety" in reasons,
                    "first": _iso(min(r.created_at for r in rows)),
                    "latest": _iso(max(r.created_at for r in rows))})
    return out


def close_reports(public_id):
    """Close every open report on one drawing (looked at): how many were
    closed; 0 for none, or for no such drawing. Takes nothing down. Flushes;
    does not commit."""
    s = session()
    post = s.query(SkriblPost).filter(SkriblPost.public_id == str(public_id or "")).one_or_none()
    if post is None:
        return 0
    n = (s.query(SkriblReport)
         .filter(SkriblReport.post_id == post.id, SkriblReport.state == "open")
         .update({"state": "closed"}, synchronize_session=False))
    s.flush()
    return n
