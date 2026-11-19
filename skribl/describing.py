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
never anything a page would read as more than a colour. AND WHETHER IT IS ON
A PICTURE (Nov 14, the owner's "Yes to both, build them"): `on_photo`, so a
host can show a photo drawing's own picture at its sides. Both are columns
written at post time; a post from before them is read from the drawing until
`python -m skribl.backfill_ground` fills them in.

AND WHAT IS PLAYED MOST (Nov 14, for the Skribl site's Gallery, Hot): the
gallery's Hot is plays counted in the last seven days, from Skribl's own
record of them; recent_plays() hands a host that count as a subquery to join
to its own posts, so the host's Hot is one query on its own rows, with its
own rules, paged by its own cursor.

AND WHAT PEOPLE SHARED OUTSIDE A HOST'S POSTS (Nov 14, for the Skribl site's
Gallery of every skribl: the owner's "I thought gallery was only skribls (pad
or flip)?"): a host's gallery can list its people's skribls beside its own
posts, in one order. shared_skribls() hands a host the shared ones as a
subquery to read beside its own rows (each skribl's id, author, title, time
and visibility; no payload), so the host's gallery is its own query, its own
rules and its own cursor, and never a query of Skribl's tables.

Reads only, on the host's session: it flushes nothing and commits nothing.
"""
import base64
import copy
from datetime import datetime, timedelta, timezone

import sqlalchemy as sa

from .core import HOT_DAYS
from .creation import _installed_media_store
from .mediameta import STRIPPED, strip_payload
from .storage import _MEDIA_LABEL_RE, KEY_RE, is_data_url
from .validation import _iter_media_items
from .models import SkriblPost, SkriblView, apply_feed_filter, normalise_user_id, session
# The one spelling of a ground a page may use, the rule creation.py writes the
# column by (validation.py, beside the payload's other columns).
from .validation import _ground

#: The most ids one call reads, in one query: a page of a feed, with room.
MAX_DESCRIBE = 200


def describe_posts(public_ids, *, viewer_id=None):
    """{public_id: item} for the skribls in `public_ids` that `viewer_id` may
    see, the listing's own item for each (id, title, caption, kind, pages,
    canvas_w, canvas_h, line, views, user_id, visibility, created_at), its
    `ground`: the colour the drawing is painted on, "#rrggbb", or None, and
    `on_photo`: whether it is made on a picture, True or False.

    ground      as the player paints a drawing's first page (inlineplayer.js:
                frames[0]'s background colour, else the payload's own, the
                way a payload from before frames carries it), validated: a
                hex colour, lowercase, six digits (a three-digit one written
                out), and None for anything else, so a host can set it as a
                value of its own CSS (a tile's box, around a drawing whose
                shape is not the box's) and never meet anything but a colour.
    on_photo    whether the player lays a picture under the drawing: the
                first page's photo, or the picture the Pad began on (its
                base snapshot), a page's or the payload's own. A host shows
                the drawing's own picture at its sides (the Skribl site's
                tiles: a copy of the plate, blurred, behind it).

    NO PAYLOAD CROSSES, AND FOR A POST MADE SINCE THE COLUMNS NONE IS READ.
    Both are columns, written at post time by the player's own rules
    (validation._payload_ground, _payload_on_photo). Only where a column is
    NULL, a post from before them, does the database read that one from the
    drawing, at its paths in the JSON (SQLite's json_extract, PostgreSQL's
    #>>), inside a CASE, so a row with its column never parses its payload
    (on PostgreSQL the payload is plain `json`, and every path read re-parses
    the whole drawing); the picture's paths in the player's order, in a
    coalesce that stops at the first one there. `python -m
    skribl.backfill_ground` fills the columns in. The payload is deferred, as
    the listing's is, and it is all one query.

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

    def at(*path):
        # A path's text, an empty one read as none, as the player's || does.
        return sa.func.nullif(pj[path].as_string(), "")
    # THE COLUMNS, AND THE DRAWING ONLY WHERE ONE IS NULL (a post from before
    # them, until backfill_ground reaches it): a CASE, which evaluates its
    # branch only for the rows that take it. The ground as #899 read it,
    # frames[0]'s, else the top level's; the picture, the first of the
    # player's four places that is there.
    ground = sa.case((SkriblPost.ground.is_(None),
                      sa.func.coalesce(at("frames", 0, "background", "color"), pj[("background", "color")].as_string())),
                     else_=SkriblPost.ground)
    on_photo = sa.case((SkriblPost.on_photo.is_(None),
                        sa.func.coalesce(at("frames", 0, "photo", "data"), at("frames", 0, "baseSnapshot"),
                                         at("photo", "data"), at("baseSnapshot")).is_not(None)),
                       else_=SkriblPost.on_photo)
    rows = (session().query(SkriblPost, ground, on_photo).options(sa.orm.defer(SkriblPost.payload_json))
            .filter(SkriblPost.public_id.in_(ids)).all())
    return {p.public_id: dict(p.feed_dict(), ground=_ground(g), on_photo=bool(o))
            for p, g, o in rows if p.visible_to(viewer_id)}



def read_payload(public_id, *, viewer_id=None, inline_media=False):
    """A skribl's drawing (its payload, as the player is handed it), for a
    host that builds on one: the Skribl site's Draw back, which lays the
    original under a new drawing and posts the two as one (DECISIONS.md,
    "Draw back, mocked"). None for an id that is not there, or that
    `viewer_id` may not see (SkriblPost.visible_to, the rule every read
    follows), saying nothing of which.

    A copy, never the row's own JSON, and stripped as the payload route
    strips one (strip_payload: a photo's location, a file's name), so what
    a host builds from it carries nothing the route would not have served.
    No play is counted: reading is not watching.

    inline_media  its picture and its music as data (data URLs) where the
                  store keeps them apart, read back from the store by their
                  keys, so a host can post them again in a new drawing (the
                  Skribl site's Draw back on a drawing with a photo or music:
                  the author's background and music, the owner's yes, Nov 19).
                  The store keeps content once, so posting them again costs no
                  more room. The picture of the paper a take began on
                  (baseSnapshot) is left as it is. One that cannot be read is
                  left as its address."""
    if not isinstance(public_id, str) or not public_id or len(public_id) > 32:
        return None
    post = session().query(SkriblPost).filter_by(public_id=public_id).first()
    if post is None or not post.visible_to(viewer_id):
        return None
    payload = copy.deepcopy(post.payload_json or {})
    if not isinstance(payload, dict):
        return None
    if not payload.get(STRIPPED):
        payload = strip_payload(payload)
    payload.pop("thumbnail", None)
    if inline_media:
        _inline_media(payload)
    return payload


def _inline_media(payload):
    """Each photo's and song's address in Skribl's store, in `payload`, back
    as a data URL (read_payload's inline_media), in place."""
    store = _installed_media_store()
    if not callable(getattr(store, "read", None)):
        return
    for value, _kind, _cap, label in list(_iter_media_items(payload)):
        pm = _MEDIA_LABEL_RE.match(label)
        if pm is None or pm.group("snap") or not isinstance(value, str) or not value or is_data_url(value):
            continue
        key = value.split("?", 1)[0].rstrip("/").rsplit("/", 1)[-1]
        if not KEY_RE.match(key):
            continue
        got = store.read(key)
        if not got:
            continue
        raw, content_type = got
        container = payload["frames"][int(pm.group("frame"))] if pm.group("frame") is not None else payload
        container[pm.group("slot")]["data"] = "data:%s;base64,%s" % (content_type, base64.b64encode(raw).decode("ascii"))

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


def shared_skribls(*, author=None, author_prefix=None, link_only=False):
    """The skribls people shared, as a SUBQUERY for a host to read beside its
    own posts: a gallery of everything its people shared, in a post or not,
    in one order (after v330, for the Skribl site's Gallery of every skribl,
    the owner's "I thought gallery was only skribls (pad or flip)?", Nov 14).
    One row per skribl: its public id as `skribl_id`, `user_id`, `title`,
    `created_at` and `visibility`. No payload is read.

    THE PUBLIC ONES, the gallery's own rule ("public": what the author put in
    the gallery). Never unlisted, private or withheld, but:

    link_only       with `author` alone: their link-only (unlisted) ones too,
                    for a page that is that author's ALONE, where they choose
                    what is in the gallery (Skribl's own listing shows an
                    author everything they own the same way: GET
                    /api/skribls?user_id= for its author). Without `author`
                    it is refused (ValueError): nobody's link-only skribls are
                    listed to everybody.
    author          only this author's (their user id, as the host hands it).
    author_prefix   only authors whose ids start with this (a host whose
                    people's ids share a prefix: the site's are "site:...").

    It says nothing of who may see a drawing beyond that: joined to the
    host's own people, the host's rules (its blocks, mutes and takedowns)
    decide what is shown, and describe_posts, for the ones it shows, applies
    the visibility policy as every read does. A skribl the host also holds a
    row for (a post's drawing) is in it too: a host showing both shows it
    once, by its own rows. So is anything else the host posted for its people
    (a face, a reply's drawing): a host leaves out what its rows say is not a
    gallery's. It runs nothing until the host's query does and reads no
    payload; on the posts' (visibility, created_at) and (user_id,
    created_at) indexes:

        shared = skribl.shared_skribls(author_prefix="site:")
        rows = (sa.select(shared.c.skribl_id, shared.c.created_at, Person)
                .join(Person, Person.public_id == shared.c.user_id)
                .where(~sa.exists().where(Post.skribl_id == shared.c.skribl_id))
                .order_by(shared.c.created_at.desc(), shared.c.skribl_id.desc()))
    """
    if link_only and author is None:
        raise ValueError("link_only lists one author's own skribls, on a page that is theirs alone: name the author")
    q = sa.select(SkriblPost.public_id.label("skribl_id"), SkriblPost.user_id.label("user_id"),
                  SkriblPost.title.label("title"), SkriblPost.created_at.label("created_at"),
                  SkriblPost.visibility.label("visibility"))
    if link_only:
        q = q.where(SkriblPost.visibility.in_(("public", "unlisted")))
    else:
        q = q.where(SkriblPost.visibility == "public")
    if author is not None:
        q = q.where(SkriblPost.user_id == normalise_user_id(author))
    if author_prefix:
        q = q.where(SkriblPost.user_id.like(_like_prefix(str(author_prefix)), escape="\\"))
    return q.subquery("skribl_shared")
