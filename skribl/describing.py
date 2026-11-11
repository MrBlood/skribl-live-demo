"""What a host's feed needs to show the skribls its posts hold, read on the
server (after v330, for the Skribl site's posts, piece 4; every host gets it).

A host that keeps its own posts stores a skribl's public id on each and shows
it with skribl_inline(). The player takes the drawing's shape and says its
line ("Drawn in 15 sec") before anybody presses play when it is handed the
drawing's size and line, and a feed says how many plays a drawing has had
(docs/INTEGRATION.md, "Putting a Skribl inside your own posts"). Those live
on Skribl's rows, and Skribl's models are not something a host imports, so
describe_posts() hands them over by public id: for each, the listing's own
item (SkriblPost.feed_dict()), so a host's feed and Skribl's listing can
never disagree about a drawing.

Reads only, on the host's session: it flushes nothing and commits nothing.
"""
from .models import SkriblPost, session

#: The most ids one call reads, in one query: a page of a feed, with room.
MAX_DESCRIBE = 200


def describe_posts(public_ids, *, viewer_id=None):
    """{public_id: item} for the skribls in `public_ids` that `viewer_id` may
    see, the listing's own item for each (id, title, caption, kind, pages,
    canvas_w, canvas_h, line, views, user_id, visibility, created_at); no
    payload is read.

    viewer_id   the person looking, as the host hands Skribl its current
                user id, or None for nobody. The rule is the one every read
                of a skribl follows (SkriblPost.visible_to): public and
                unlisted for anyone, anything else for its author alone.

    A skribl deleted, withheld or private to somebody else is simply absent,
    and the host's box for it still renders: the player says the drawing is
    not here anymore. Ids that are not strings, repeats, and any past the
    first MAX_DESCRIBE are left out.
    """
    ids = [i for i in dict.fromkeys(public_ids or ()) if isinstance(i, str) and i][:MAX_DESCRIBE]
    if not ids:
        return {}
    rows = session().query(SkriblPost).filter(SkriblPost.public_id.in_(ids)).all()
    return {p.public_id: p.feed_dict() for p in rows if p.visible_to(viewer_id)}
