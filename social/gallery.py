"""The Gallery of everyone (docs/SOCIAL-SITE.md section 16, step 3; the
owner's "Your picks are great" to the Gallery mock, Nov 13), and since the
owner's "I thought gallery was only skribls (pad or flip)?" (Nov 14, "Yes,
your picks") the Gallery of every skribl: every drawing and Flip the site's
people shared, in a post or not, two across on a phone and three on a desk,
each tile one link: a post's to its post, one shown outside a post to its
own page (/b/<id>).

    /explore            the Gallery: Following | Everyone on top (signed in:
                        Home's own pill; signed out, as Home, none), New and
                        Hot and a search under it, then the tiles, newest
                        first, and Load more.
    /explore/more       a page of it as its tiles (JSON {html, next}): the
                        next one (?before=, Load more), or the first of a new
                        pick (?show=, ?sort=, ?q=).

EVERY SKRIBL OF THE SITE'S PEOPLE. A post is words (maybe none) and one
drawing or Flip; a drawing shown outside a post (the Pad's own "Show in the
Skribls gallery", or anything shared before posts) is the same tile, opening
its own page. Never a face, a comment's drawing, or a drawing kept link-only
(none of them is shared in the gallery), nor one by somebody not on the site
(Skribl's own /gallery keeps those). TWO READS, ONE ORDER: the site's own
posts, on their indexes, and the drawings shown outside them, through
Skribl's shared_skribls() (a subquery of the shared ones, read beside the
site's own people, never a query of Skribl's tables), each a page long and in
the same order, merged here into one page; so New and Hot hold both kinds,
and Load more walks both by one cursor. Skribl is asked only what a tile
shows of a drawing (describe_posts, through posts.cards) and, under Hot, its
plays.

HIDDEN FROM THE GALLERY by its maker (the eye on their own Gallery tab, the
owner's "Yes, the eye in view", Nov 14): a post's drawing by the site's own
flag on the post (Post.gallery_hidden_at; the post stays on Home and in their
Posts), one shown outside a post by its Skribl visibility (public "In the
gallery", unlisted "Link only"). Out of the Gallery of everyone, the first
visit and their Gallery as anybody else sees it; in their own, faded, with
the crossed eye (tiles(..., eye=True)).

WHO IS IN IT, as Home's lists (posts.feed_page): nobody a block hides either
way and nobody muted, in both reads, so its pages stay whole; Following is
the people you follow and you, Everyone everybody. TAKEN DOWN IS OUT for
everybody, its maker too: a post or a person taken down, and a drawing
Skribl withholds or no longer has. The Gallery is the site's public wall;
its maker still sees it, with the note, on Home and on its own page.

NEW is newest first, by Home's own cursor (it names no internal id: a post's
address or a drawing's). HOT is plays in the last seven days, most first,
the newest first among equals, as Skribl's gallery's Hot
(skribl.recent_plays, a subquery joined to both reads); its cursor holds the
moment the first page was ranked at, so one scroll-through is one order.
SEARCH is a post's words, a drawing's title, and its maker's name and
@handle.

THROUGH SKRIBL'S SEAMS ONLY: shared_skribls, recent_plays and describe_posts
(documented names, verify_social section 8), the poster's own address, the
face player's macro. Reads only: nothing here writes (the eye's routes are
posts.py's).
"""
import base64
from datetime import datetime, timezone

import sqlalchemy as sa
from flask import jsonify, render_template, request, url_for

from .accounts import _rests
from .models import PERSON_PREFIX, Person, Post, as_utc
from .security import csrf_token, current_person, site

#: A page of tiles: twelve rows of two on a phone, eight of three on a desk.
PAGE = 24

#: The most a search may say, as Skribl's gallery's box (its maxlength).
Q_MAX = 80

SHOWS = ("following", "everyone")
SORTS = ("new", "hot")

#: How a Hot cursor starts: a New one (Home's) is a base64 word, with no dot.
_HOT = "h."


def wants(args, me):
    """(show, sort, q) as the address asks for them, made safe: Following
    only for somebody signed in, Everyone otherwise; New unless Hot; the
    search's spaces tidied, at most Q_MAX characters."""
    show = args.get("show")
    show = show if (show in SHOWS and me is not None) else "everyone"
    sort = args.get("sort")
    sort = sort if sort in SORTS else "new"
    q = " ".join(str(args.get("q") or "").split())[:Q_MAX]
    return show, sort, q


def _like(text):
    """A LIKE pattern for `text` anywhere, its own % and _ escaped as letters."""
    return "%" + text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"


def _us(when):
    return int(as_utc(when).timestamp() * 1_000_000)


def _at(us):
    return datetime.fromtimestamp(int(us) / 1_000_000, tz=timezone.utc)


def _hot_cursor(n, entry, as_of):
    """Where a page of Hot ended: its plays, its time, which tile (a post's
    address or a drawing's, p or s first, as Home's cursor names a card), and
    the moment it was ranked at."""
    raw = f"{int(n)}|{_us(entry['at'])}|{entry['key']}|{_us(as_of)}"
    return _HOT + base64.urlsafe_b64encode(raw.encode()).rstrip(b"=").decode()


def _hot_uncursor(text):
    """(plays, time, tile, the moment ranked at), or None. A cursor from before
    the Gallery held drawings outside posts names a post's address alone (11
    letters): it is a post's."""
    try:
        body = text[len(_HOT):]
        raw = base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)).decode()
        n, us, key, of = raw.split("|")
        if not (key and len(key) <= 24):
            return None
        if not (len(key) == 12 and key[0] in "ps"):
            key = "p" + key
        return int(n), _at(us), key, _at(of)
    except (ValueError, TypeError, UnicodeDecodeError, OverflowError, OSError):
        return None


def _after(when_col, id_col, kind, at):
    """The rows of one read (`kind`, "p" or "s") that come after the tile a
    cursor names, newest first: older, or at that very moment and after it.
    Home's order: at one moment a drawing shown outside a post comes before
    the posts (p < s), so a post's cursor leaves out every drawing of its
    moment and a drawing's keeps every post of it."""
    when, key = at
    if kind != key[0]:
        return when_col <= when if kind < key[0] else when_col < when
    return sa.or_(when_col < when, sa.and_(when_col == when, id_col < key[1:]))


def _reads(viewer, show="everyone", q="", person=None, mine=False):
    """The two reads a page of the Gallery is made of, each before its order
    and its page: (posts, drawings, the drawings' columns). THE POSTS, the
    site's own, with their makers; THE DRAWINGS SHOWN OUTSIDE A POST, through
    Skribl's shared_skribls(), with their makers, the site's people: never a
    post's drawing (a post shows it), a face or a comment's drawing.

    Both alike: nobody a block hides either way, nobody `viewer` muted (a
    list of everybody's; one person's page is what they went to, and keeps
    them), nobody taken down; Following, the people `viewer` follows and
    theirs; a search, its words in the post's words or the drawing's title,
    or the maker's name or @handle. ONE PERSON'S (`person`, their Gallery
    tab): theirs alone. What is HIDDEN FROM THE GALLERY (a post's flag, a
    drawing kept link-only) is out, but for its maker on their own (`mine`),
    who sees it faded with the eye."""
    from skribl import shared_skribls
    from .follows import followed_ids
    from .models import Comment
    from .mutes import muted_ids
    from .safety import hidden_ids
    hidden = hidden_ids(viewer) | (muted_ids(viewer) if person is None else frozenset())

    def theirs(sel, words):
        sel = sel.where(Person.taken_down_at.is_(None))
        if hidden:
            sel = sel.where(Person.id.notin_(sorted(hidden)))
        if show == "following" and viewer is not None and person is None:
            sel = sel.where(sa.or_(Person.id.in_(followed_ids(viewer)), Person.id == viewer.id))
        if q:
            handle = q[1:] if q.startswith("@") else q
            sel = sel.where(sa.or_(words.ilike(_like(q), escape="\\"),
                                   Person.display_name.ilike(_like(q), escape="\\"),
                                   Person.handle.ilike(_like(handle), escape="\\")))
        return sel

    posts = (sa.select(Post, Person).join(Person, Post.person_id == Person.id)
             .where(Post.taken_down_at.is_(None)))
    if not mine:
        posts = posts.where(Post.gallery_hidden_at.is_(None))
    if person is not None:
        posts = posts.where(Post.person_id == person.id)
    posts = theirs(posts, Post.words)

    shared = (shared_skribls(author=person.public_id, link_only=mine) if person is not None
              else shared_skribls(author_prefix=PERSON_PREFIX))
    # Skribl's stand-in for no title is no words to search.
    title = sa.case((shared.c.title == "Untitled Skribl", ""), else_=shared.c.title)
    drawings = (sa.select(shared.c.skribl_id, shared.c.created_at, shared.c.visibility, Person)
                .select_from(shared).join(Person, Person.public_id == shared.c.user_id)
                .where(~sa.exists().where(Post.skribl_id == shared.c.skribl_id),
                       ~sa.exists().where(Comment.skribl_id == shared.c.skribl_id),
                       sa.or_(Person.face_id.is_(None), Person.face_id != shared.c.skribl_id)))
    drawings = theirs(drawings, title)
    return posts, drawings, shared.c


def _read(viewer, show="everyone", sort="new", q="", before=None, limit=PAGE, person=None, mine=False):
    """A page of the Gallery: (entries, next cursor or None), newest first or
    Hot, both reads a page long in the same order, merged into one. Each
    entry as posts.cards() reads one: a post's (kind "p"), or a drawing shown
    outside a post (kind "s", its skribl's id and visibility; cards() asks
    Skribl the rest). A cursor names its own order (a Hot one starts "h.");
    one that cannot be read ends the list rather than starting it again."""
    from .posts import _cursor, _entry, _uncursor
    posts, drawings, d = _reads(viewer, show, q, person, mine)
    sess = site().session()

    def drawing(row, hot=None):
        sid, made, vis, who = row[:4]
        return {"kind": "s", "at": as_utc(made), "key": "s" + sid, "sk": {"id": sid, "visibility": vis},
                "who": who, "hot": hot}

    if (before or "").startswith(_HOT) or (not before and sort == "hot"):
        from skribl import recent_plays
        at = _hot_uncursor(before) if before else None
        if before and at is None:
            return [], None
        as_of = at[3] if at else datetime.now(timezone.utc)
        plays = recent_plays(as_of=as_of)
        hot = sa.func.coalesce(plays.c.plays, 0)
        posts = (posts.add_columns(hot.label("hot")).outerjoin(plays, plays.c.skribl_id == Post.skribl_id)
                 .order_by(hot.desc(), Post.created_at.desc(), Post.public_id.desc()))
        drawings = (drawings.add_columns(hot.label("hot")).outerjoin(plays, plays.c.skribl_id == d.skribl_id)
                    .order_by(hot.desc(), d.created_at.desc(), d.skribl_id.desc()))
        if at:
            n, when, key, _ = at
            posts = posts.where(sa.or_(hot < n, sa.and_(hot == n, _after(Post.created_at, Post.public_id, "p", (when, key)))))
            drawings = drawings.where(sa.or_(hot < n, sa.and_(hot == n, _after(d.created_at, d.skribl_id, "s", (when, key)))))
        both = ([dict(_entry(p, who), hot=int(n_)) for p, who, n_ in sess.execute(posts.limit(limit + 1)).all()]
                + [drawing(r, int(r[4])) for r in sess.execute(drawings.limit(limit + 1)).all()])
        both.sort(key=lambda e: (e["hot"], e["at"], e["key"]), reverse=True)
        page_ = both[:limit]
        return page_, (_hot_cursor(page_[-1]["hot"], page_[-1], as_of) if (len(both) > limit and page_) else None)
    at = _uncursor(before) if before else None
    if before and at is None:
        return [], None
    posts = posts.order_by(Post.created_at.desc(), Post.public_id.desc())
    drawings = drawings.order_by(d.created_at.desc(), d.skribl_id.desc())
    if at:
        posts = posts.where(_after(Post.created_at, Post.public_id, "p", at))
        drawings = drawings.where(_after(d.created_at, d.skribl_id, "s", at))
    both = ([_entry(p, who) for p, who in sess.execute(posts.limit(limit + 1)).all()]
            + [drawing(r) for r in sess.execute(drawings.limit(limit + 1)).all()])
    both.sort(key=lambda e: (e["at"], e["key"]), reverse=True)
    page_ = both[:limit]
    return page_, (_cursor(page_[-1]) if (len(both) > limit and page_) else None)


def page(viewer, show="everyone", sort="new", q="", before=None, limit=PAGE):
    """A page of the Gallery of everyone for `viewer`: (entries, next cursor
    or None), both kinds in one order (_read)."""
    return _read(viewer, show, sort, q, before, limit)


def person_page(person, viewer, before=None, limit=PAGE):
    """A page of ONE PERSON'S GALLERY (their profile's Gallery tab, the map's
    step 4): every drawing and Flip they have shared, in a post or not,
    newest first, (entries, next cursor or None), as the Gallery of everyone
    reads them (_read) with one person in it: nobody a block hides either
    way, a mute changing nothing (their page is what the viewer went to). A
    face, a comment's drawing and what is taken down are never in it. What
    they hid from the Gallery is in it only for them (their own page, where
    the eye is), and so are their drawings kept link-only."""
    from .posts import _uncursor
    if before and (len(before) > 200 or _uncursor(before) is None):
        # A cursor that cannot be read ends the list, never starts it again.
        return [], None
    mine = viewer is not None and viewer.id == person.id
    return _read(viewer, "everyone", "new", "", before, limit, person=person, mine=mine)


def duration_words(ms):
    """How long a drawing took, as the in-post player says it at rest
    (lib/replayline.js words(): its rounding, Math.round, is half up): "15
    sec", "4 min", "1 hr 5 min"."""
    ms = max(0, float(ms or 0))
    s, m = int(ms / 1000 + 0.5), int(ms / 60000 + 0.5)
    if s < 60:
        return f"{max(1, s)} sec"
    if m < 60:
        return f"{m} min"
    return f"{m // 60} hr" + (f" {m % 60} min" if m % 60 else "")


def says(sk):
    """What a tile's ▶ says, as the play button of the in-post player says it
    at rest (inlineplayer.js, the words of its .is-says pill) without "drawn
    in": a Flip its pages, a drawing how long it took; nothing for a drawing
    whose line Skribl does not know. (words, pages or None)."""
    line = (sk or {}).get("line") or {}
    pages = line.get("pages")
    if isinstance(pages, int) and pages > 1:
        return f"{pages} pages", pages
    drawn = line.get("drawn")
    if isinstance(drawn, (int, float)) and drawn > 0:
        return duration_words(drawn), None
    return "", None


def tiles(entries, viewer, eye=False):
    """What each tile shows: the post's drawing (Skribl's description, for its
    shape, its poster and its ground), what its ▶ says, its maker's face and
    name (as they wrote it, "Mr. Blood", never its first word: the owner's
    "Your picks", Nov 14; social.css cuts it with … only when it doesn't
    fit), its likes and comments (each only when there are some: the
    template's), its post's address and the words a screen reader hears for
    the link. A
    post whose drawing Skribl no longer describes to `viewer` (deleted or
    withheld since) or that is taken down has no tile: the drawing is the
    tile. A DRAWING SHOWN OUTSIDE A POST (kind "s", in the Gallery of
    everyone since Nov 14 as in one person's) is the same tile, opening its
    own page (/b/<id>), its words its title; `kind` says which, so the tile
    names a post only when it is one.

    THE EYE (`eye`: your own Gallery tab, nowhere else; the owner's "Yes,
    the eye in view", Nov 14): each tile also says whether it is hidden from
    the Gallery (a post's by its flag, a drawing shown outside a post by
    being link-only), where its eye sends the change, and what it is called
    to a screen reader; a hidden one's link says so too."""
    from .posts import cards
    out = []
    for c in (cards(entries, viewer) if entries else []):
        sk, who = c["sk"], c["who"]
        if not sk or c["down"]:
            continue
        name = who.display_name
        said, pages = says(sk)
        words = (c["post"].words or "").split("\n", 1)[0].strip()
        likes, comments = int(c["likes"]["n"] or 0), int(c["comments"] or 0)
        label = f"{name}: {words}" if words else (f"A Flip by {name}" if pages else f"A drawing by {name}")
        if said:
            label += ", " + (said if pages else "drawn in " + said)
        if likes:
            label += f", {likes} {'like' if likes == 1 else 'likes'}"
        if comments:
            label += f", {comments} {'comment' if comments == 1 else 'comments'}"
        tile = {"post": c["post"].public_id, "kind": c["kind"], "url": c["url"], "who": who, "name": name,
                "sk": sk, "says": said, "likes": likes, "comments": comments, "label": label}
        if eye and c["mine"]:
            hidden = (getattr(c["post"], "gallery_hidden_at", None) is not None if c["kind"] == "p"
                      else sk.get("visibility") != "public")
            tile.update(hidden=hidden, shown_label=label, hidden_label=label + ", hidden from the Gallery",
                        what=words or ("A Flip" if pages else "A drawing"),
                        eye=(url_for("social.post_gallery", public_id=c["post"].public_id) if c["kind"] == "p"
                             else url_for("social.bloob_gallery", skribl_id=c["post"].skribl_id)))
            if hidden:
                tile["label"] = tile["hidden_label"]
        out.append(tile)
    return out


#: The first visit's tiles (Home signed out): the Gallery's newest six.
FRESH = 6


@_rests()
def first_visit():
    """HOME FOR NOBODY SIGNED IN, the first visit (the owner's B, Nov 14): the
    welcome, Blooby drawing his card, as it was; under "Fresh from everyone"
    the six newest tiles of the Gallery of everyone, as /explore shows them
    signed out (posts only: never a drawing shown outside a post, a face or a
    drawing kept link-only, which are no post), then "See the whole Gallery
    ›". Twice the six are asked, so a drawing withheld since (no tile) leaves
    no gap.

    WHEN THE SITE'S POSTS CANNOT BE READ (its chain failed, the database is
    away) the welcome still stands, without Fresh from everyone (None): it is
    the front page a failed chain never takes down (verify_socialauth 14),
    and saying "nothing here yet" would not be true. The Gallery itself rests,
    as every page of posts does."""
    try:
        entries, _ = page(None, "everyone", "new", "", limit=FRESH * 2)
        fresh = tiles(entries, None)[:FRESH]
    except sa.exc.SQLAlchemyError:
        try:
            site().session().rollback()
        except Exception:            # noqa: BLE001 -- nothing more to undo
            pass
        site().say_once("first-visit", "the site's posts could not be read, so the first visit shows its "
                                       "welcome without Fresh from everyone until they can")
        fresh = None
    return render_template("social/home.html", here="home", fresh=fresh)


@_rests()
def explore_page():
    """The Gallery, its first page for what the address asks (wants())."""
    me = current_person()
    show, sort, q = wants(request.args, me)
    entries, nxt = page(me, show, sort, q)
    # The page's token, signed in, for the ☰'s Sign out (_menu.html), a form
    # as Settings' is.
    return render_template("social/explore.html", here="explore", tiles=tiles(entries, me), next=nxt,
                           show=show, sort=sort, q=q, more_url=url_for("social.explore_more"),
                           token=csrf_token() if me is not None else None)


def register(bp):
    """Add the Gallery's page of tiles to the site's blueprint (the page
    itself is social/__init__.py's explore, which holds without accounts)."""

    @bp.get("/explore/more")
    @_rests(json_answer=True)
    def explore_more():
        """A page of the Gallery as its tiles: {html, next, show, sort, q}."""
        me = current_person()
        show, sort, q = wants(request.args, me)
        before = request.args.get("before") or None
        if before and len(before) > 200:
            before = "?"
        entries, nxt = page(me, show, sort, q, before)
        html = render_template("social/_gallery_tiles.html", tiles=tiles(entries, me))
        return jsonify({"html": html, "next": nxt, "show": show, "sort": sort, "q": q})

    return bp

