"""The Gallery of everyone (docs/SOCIAL-SITE.md section 16, step 3; the
owner's "Your picks are great" to the Gallery mock, Nov 13): Explore lists
the site's own posts as their drawings, two across on a phone and three on a
desk, each tile one link to its post.

    /explore            the Gallery: Following | Everyone on top (signed in:
                        Home's own pill; signed out, as Home, none), New and
                        Hot and a search under it, then the tiles, newest
                        first, and Load more.
    /explore/more       a page of it as its tiles (JSON {html, next}): the
                        next one (?before=, Load more), or the first of a new
                        pick (?show=, ?sort=, ?q=).

POSTS ONLY. A post is words (maybe none) and one drawing or Flip; a drawing
shown outside a post is not in this Gallery (the map's decision 2: it stays
in its author's Gallery, step 4), nor is a face or a drawing kept link-only,
none of which is a post. So the list is read from the site's own posts, in
one query on their indexes, and Skribl is asked only what a tile shows of a
drawing (describe_posts, through posts.cards) and, under Hot, its plays.

WHO IS IN IT, as Home's lists (posts.feed_page): nobody a block hides either
way and nobody muted, in the query, so its pages stay whole; Following is
the people you follow and you, Everyone everybody. TAKEN DOWN IS OUT for
everybody, its maker too: a post or a person taken down, and a drawing
Skribl withholds or no longer has. The Gallery is the site's public wall;
its maker still sees it, with the note, on Home and on its own page.

NEW is newest first, by Home's own cursor (it names no internal id). HOT is
plays in the last seven days, most first, the newest first among equals, as
Skribl's gallery's Hot (skribl.recent_plays, a subquery joined to the posts
here); its cursor holds the moment the first page was ranked at, so one
scroll-through is one order. SEARCH is what the site has of its own: a
post's words, and its maker's name and @handle.

THROUGH SKRIBL'S SEAMS ONLY: recent_plays and describe_posts (documented
names, verify_social section 8), the poster's own address, the face player's
macro. Reads only: nothing here writes.
"""
import base64
from datetime import datetime, timezone

import sqlalchemy as sa
from flask import jsonify, render_template, request, url_for

from .accounts import _rests
from .models import Person, Post, as_utc
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


def _hot_cursor(n, post, as_of):
    raw = f"{int(n)}|{_us(post.created_at)}|{post.public_id}|{_us(as_of)}"
    return _HOT + base64.urlsafe_b64encode(raw.encode()).rstrip(b"=").decode()


def _hot_uncursor(text):
    """(plays, time, post's address, the moment ranked at), or None."""
    try:
        body = text[len(_HOT):]
        raw = base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)).decode()
        n, us, pid, of = raw.split("|")
        if not (pid and len(pid) <= 24):
            return None
        return int(n), _at(us), pid, _at(of)
    except (ValueError, TypeError, UnicodeDecodeError, OverflowError, OSError):
        return None


def _listed(viewer, show, q):
    """The posts the Gallery may show `viewer`, with their makers: nobody a
    block hides or they muted (feed_page's rule for a list of everybody's),
    nothing taken down, a post, a person, for anybody; Following, the people
    they follow and theirs; a search, its words in the post's words, the
    maker's name or @handle."""
    from .follows import followed_ids
    from .mutes import muted_ids
    from .safety import hidden_ids
    sel = (sa.select(Post, Person).join(Person, Post.person_id == Person.id)
           .where(Post.taken_down_at.is_(None), Person.taken_down_at.is_(None)))
    hidden = hidden_ids(viewer) | muted_ids(viewer)
    if hidden:
        sel = sel.where(Post.person_id.notin_(sorted(hidden)))
    if show == "following" and viewer is not None:
        sel = sel.where(sa.or_(Post.person_id.in_(followed_ids(viewer)), Post.person_id == viewer.id))
    if q:
        handle = q[1:] if q.startswith("@") else q
        sel = sel.where(sa.or_(Post.words.ilike(_like(q), escape="\\"),
                               Person.display_name.ilike(_like(q), escape="\\"),
                               Person.handle.ilike(_like(handle), escape="\\")))
    return sel


def page(viewer, show="everyone", sort="new", q="", before=None, limit=PAGE):
    """A page of the Gallery for `viewer`: (entries, next cursor or None).
    Each entry is a post's, as posts.cards() reads one. A cursor names its
    own order (a Hot one starts "h."); one that cannot be read ends the list
    rather than starting it again."""
    from .posts import _cursor, _entry, _uncursor
    sel = _listed(viewer, show, q)
    sess = site().session()
    if (before or "").startswith(_HOT) or (not before and sort == "hot"):
        from skribl import recent_plays
        at = _hot_uncursor(before) if before else None
        if before and at is None:
            return [], None
        as_of = at[3] if at else datetime.now(timezone.utc)
        plays = recent_plays(as_of=as_of)
        hot = sa.func.coalesce(plays.c.plays, 0)
        sel = (sel.add_columns(hot.label("hot")).outerjoin(plays, plays.c.skribl_id == Post.skribl_id)
               .order_by(hot.desc(), Post.created_at.desc(), Post.public_id.desc()))
        if at:
            n, when, pid, _ = at
            sel = sel.where(sa.or_(hot < n, sa.and_(hot == n, sa.or_(
                Post.created_at < when, sa.and_(Post.created_at == when, Post.public_id < pid)))))
        rows = sess.execute(sel.limit(limit + 1)).all()
        more = len(rows) > limit
        rows = rows[:limit]
        nxt = _hot_cursor(rows[-1][2], rows[-1][0], as_of) if (more and rows) else None
        return [_entry(p, who) for p, who, _ in rows], nxt
    at = _uncursor(before) if before else None
    if before and (at is None or not at[1].startswith("p")):
        return [], None
    sel = sel.order_by(Post.created_at.desc(), Post.public_id.desc())
    if at:
        when, key = at
        sel = sel.where(sa.or_(Post.created_at < when,
                               sa.and_(Post.created_at == when, Post.public_id < key[1:])))
    rows = sess.execute(sel.limit(limit + 1)).all()
    more = len(rows) > limit
    entries = [_entry(p, who) for p, who in rows[:limit]]
    return entries, (_cursor(entries[-1]) if (more and entries) else None)


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


def tiles(entries, viewer):
    """What each tile shows: the post's drawing (Skribl's description, for its
    shape and its poster), what its ▶ says, its maker's face and first name,
    its likes and comments (each only when there are some: the template's),
    its post's address and the words a screen reader hears for the link. A
    post whose drawing Skribl no longer describes to `viewer` (deleted or
    withheld since) or that is taken down has no tile: the drawing is the
    tile."""
    from .posts import cards
    out = []
    for c in (cards(entries, viewer) if entries else []):
        sk, who = c["sk"], c["who"]
        if not sk or c["down"]:
            continue
        first = who.display_name.split(" ")[0]
        said, pages = says(sk)
        words = (c["post"].words or "").split("\n", 1)[0].strip()
        likes, comments = int(c["likes"]["n"] or 0), int(c["comments"] or 0)
        label = f"{first}: {words}" if words else (f"A Flip by {first}" if pages else f"A drawing by {first}")
        if said:
            label += ", " + (said if pages else "drawn in " + said)
        if likes:
            label += f", {likes} {'like' if likes == 1 else 'likes'}"
        if comments:
            label += f", {comments} {'comment' if comments == 1 else 'comments'}"
        out.append({"post": c["post"].public_id, "url": c["url"], "who": who, "first": first,
                    "sk": sk, "says": said, "likes": likes, "comments": comments, "label": label})
    return out


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

