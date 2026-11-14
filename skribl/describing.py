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

AND THE GROUND IT IS DRAWN ON (Nov 14, for the Skribl site's tiles: the
owner's phone showed a tall drawing made on the Pad's dark canvas in a tile of
cream paper, cream bars at its sides): each item says the drawing's own
ground, `ground`, the colour its first page is painted on as the player
paints it (inlineplayer.js: frames[0]'s background, else the payload's own),
so a host can lay the box around a drawing in it. A hex colour or nothing,
never anything a page would read as more than a colour.

AND WHAT IS PLAYED MOST (Nov 14, for the Skribl site's Gallery, Hot): the
gallery's Hot is plays counted in the last seven days, from Skribl's own
record of them; recent_plays() hands a host that count as a subquery to join
to its own posts, so the host's Hot is one query on its own rows, with its
own rules, paged by its own cursor.

Reads only, on the host's session: it flushes nothing and commits nothing.
"""
import re
from datetime import datetime, timedelta, timezone

import sqlalchemy as sa

from .core import HOT_DAYS
from .models import SkriblPost, SkriblView, apply_feed_filter, normalise_user_id, session

#: The most ids one call reads, in one query: a page of a feed, with room.
MAX_DESCRIBE = 200

#: A ground a host may lay a box in: a hex colour, three or six digits, as the
#: editors' swatches and colour picker write one (#0d0f14, the Pad's dark).
_GROUND = re.compile(r"#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})")


def _ground(raw):
    """A drawing's ground as `describe_posts` hands it: "#rrggbb", lowercase,
    or None for anything else (none written, a number, a name, a gradient,
    words after the colour). A page lays it in as a value of its own CSS, so
    nothing but a colour ever gets through."""
    m = _GROUND.fullmatch(raw) if isinstance(raw, str) else None
    if not m:
        return None
    h = m.group(1).lower()
    return "#" + (h if len(h) == 6 else "".join(c * 2 for c in h))


def describe_posts(public_ids, *, viewer_id=None):
    """{public_id: item} for the skribls in `public_ids` that `viewer_id` may
    see, the listing's own item for each (id, title, caption, kind, pages,
    canvas_w, canvas_h, line, views, user_id, visibility, created_at) and its
    `ground`: the colour the drawing is painted on, "#rrggbb", or None.

    ground      as the player paints a drawing's first page (inlineplayer.js:
                frames[0]'s background colour, else the payload's own, the
                way a payload from before frames carries it), validated: a
                hex colour, lowercase, six digits (a three-digit one written
                out), and None for anything else, so a host can set it as a
                value of its own CSS (a tile's box, around a drawing whose
                shape is not the box's) and never meet anything but a colour.

    NO PAYLOAD CROSSES. The payload is the multi-megabyte column the listing
    defers; it is deferred here too, and the ground is read by the database
    where it is, at its path in the JSON (SQLite's json_extract,
    PostgreSQL's #>>), in the same one query.

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
    pj = SkriblPost.payload_json
    # frames[0]'s, else the top level's; an empty one is none, as the player's ||.
    ground = sa.func.coalesce(sa.func.nullif(pj[("frames", 0, "background", "color")].as_string(), ""),
                              pj[("background", "color")].as_string())
    rows = (session().query(SkriblPost, ground).options(sa.orm.defer(SkriblPost.payload_json))
            .filter(SkriblPost.public_id.in_(ids)).all())
    return {p.public_id: dict(p.feed_dict(), ground=_ground(g)) for p, g in rows if p.visible_to(viewer_id)}


#: The most one call to list_public_posts returns: a page of a feed, with room.
MAX_LIST = 100

#: The most authors one query of list_public_posts names (`authors`): more
#: are asked in pieces of this many, and the newest of all of them kept.
MAX_AUTHORS = 500


def _like_prefix(prefix):
    """A LIKE pattern for `prefix` and anything after it, the prefix's own %
    and _ escaped so they are letters."""
    return prefix.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"


def list_public_posts(*, author=None, author_prefix=None, authors=None, before=None, limit=20, viewer_id=None):
    """(items, more): the public skribls a gallery would list, newest first,
    as the listing's own items (SkriblPost.feed_dict), for a host's feed of
    its own people's drawings (after v330, for the Skribl site's Home, which
    showed every drawing its people showed until its map's step 3 made Home
    posts only; the site still reads one person's, for More from).

    author          only this author's (their user id, as the host hands it).
    author_prefix   only authors whose ids start with this (a host whose
                    people's ids share a prefix: the site's are "site:...").
    authors         only these authors' (an iterable of user ids, any
                    number: past MAX_AUTHORS they are asked in pieces, one
                    query a piece, and the newest of all kept): a feed of the
                    people somebody follows (the Skribl site's Following). An
                    empty one lists nothing.
    before          (created_at, public_id): only those older, by created_at
                    and then public_id, both descending: the page after the
                    last item shown. A public_id of "" leaves out everything
                    at that very time.
    limit           how many, at most MAX_LIST.
    viewer_id       the person looking, for the host's own visibility policy
                    and feed filter, as the gallery's listing asks them. A
                    filter that names `author` is told `author` (None for
                    `authors` or `author_prefix`): set_feed_filter.

    The rule is the gallery's: public only, the host's feed_filter and
    visibility policy applied, no payload read. `more` says whether there
    are older ones after these. Reads only, on the host's session.
    """
    limit = max(1, min(int(limit), MAX_LIST))
    if authors is not None:
        authors = list(dict.fromkeys(normalise_user_id(a) for a in authors if a is not None))
        if not authors:
            return [], False
        if len(authors) > MAX_AUTHORS:
            # In pieces, each its own newest `limit`: the newest `limit` of all
            # of them are among those, by the listing's own order.
            items, more = [], False
            for k in range(0, len(authors), MAX_AUTHORS):
                got, m = list_public_posts(author=author, author_prefix=author_prefix,
                                           authors=authors[k:k + MAX_AUTHORS], before=before, limit=limit,
                                           viewer_id=viewer_id)
                items += got
                more = more or m
            items.sort(key=lambda i: (i["created_at"], i["id"]), reverse=True)
            return items[:limit], more or len(items) > limit
    q = (session().query(SkriblPost).options(sa.orm.defer(SkriblPost.payload_json))
         .filter(SkriblPost.visibility == "public"))
    if author is not None:
        q = q.filter(SkriblPost.user_id == normalise_user_id(author))
    if authors is not None:
        q = q.filter(SkriblPost.user_id.in_(authors))
    if author_prefix:
        q = q.filter(SkriblPost.user_id.like(_like_prefix(str(author_prefix)), escape="\\"))
    if before is not None:
        when, pid = before
        q = q.filter(sa.or_(SkriblPost.created_at < when,
                            sa.and_(SkriblPost.created_at == when, SkriblPost.public_id < (pid or ""))))
    # The filter is told the one author this listing is narrowed to (`author`),
    # or None for many people's (`authors`, `author_prefix`, or everybody's).
    q = apply_feed_filter(q, viewer_id, author=normalise_user_id(author) if author is not None else None)
    rows = q.order_by(SkriblPost.created_at.desc(), SkriblPost.public_id.desc()).limit(limit + 1).all()
    more = len(rows) > limit
    return [p.feed_dict() for p in rows[:limit] if p.visible_to(viewer_id)], more


def recent_plays(*, as_of=None):
    """The plays counted in the HOT_DAYS (seven) days up to `as_of`, as a
    SUBQUERY for a host to join to its own posts: one row per skribl played
    in that window, its public id as `skribl_id` and how many plays as
    `plays` (a skribl nobody played in it has no row, so join it outer and
    read a missing count as 0). The gallery's own Hot counts the same rows
    (GET /api/skribls?sort=hot): one play per client per post per UTC day.

    as_of   the moment the window ends (now, unsaid): hold one for a whole
            scroll-through, as the gallery's Hot does, so a drawing that
            climbs while somebody scrolls is neither shown twice nor skipped.

    It says nothing of who may see a drawing: joined to the host's own
    rows, those rows' rules decide what is shown, and a skribl the host
    holds no row for never comes into its list. It reads no payload and
    runs nothing until the host's query does; reading it counts no play.
    Joined on the host's session, in the host's own query:

        plays = skribl.recent_plays()
        hot = sa.func.coalesce(plays.c.plays, 0)
        q = (sa.select(Post, hot).outerjoin(plays, plays.c.skribl_id == Post.skribl_id)
             .order_by(hot.desc(), Post.created_at.desc()))
    """
    if as_of is None:
        as_of = datetime.now(timezone.utc)
    since = as_of - timedelta(days=HOT_DAYS)
    return (sa.select(SkriblPost.public_id.label("skribl_id"), sa.func.count(SkriblView.id).label("plays"))
            .join(SkriblView, SkriblView.post_id == SkriblPost.id)
            .where(SkriblView.created_at >= since, SkriblView.created_at <= as_of)
            .group_by(SkriblPost.public_id)
            .subquery("skribl_recent_plays"))
