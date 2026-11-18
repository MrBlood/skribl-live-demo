"""Bookmarks (the map, part two, item 2; docs/SOCIAL-SITE.md section 17), from
the bookmarks mock and the owner's "All yes" (Nov 14): a post you want to come
back to, kept on your own page, where only you can see it.

    /p/<id>/bookmark        POST {bookmarked}: this person's bookmark on a post,
                            kept or taken away (JSON: {ok, bookmarked})
    /b/<skribl_id>/bookmark the same, on a drawing shown outside a post

IN THE ⋯ (the mock's A): "Bookmark" at the top of the sheet's first card, its
ribbon drawn in our pen; once kept, "Remove bookmark", the ribbon filled. The
row under a post is unchanged. A tap keeps it (or takes it away), the sheet
goes down and the site's toast says so, with Undo (posts.js). Signed out, a
tap raises the small sheet the heart uses, and nothing is kept.

YOURS ALONE, AND NOBODY IS TOLD: your own page's Bookmarks tab lists them,
newest kept first (marked_page()), and nobody else's page has the tab, nor
anything of it in the page or its source (profiles.py). No Activity row and
no count anywhere: all a page ever says of bookmarks is whether one is the
viewer's own (marked()), and only to them.

WHO MAY BOOKMARK: somebody signed in, not taken down, on a post or a drawing
open to them (comments.On: there for everybody, no block either way with its
maker), as a like. Taking one away always works on your own, by the address
alone: it is yours, whatever became of the thing since.

HIDDEN FROM YOUR LIST, never deleted by it: whatever a block either way hides,
anybody taken down, a post taken down (but your own, with its note, as Home
shows it to you), and a drawing its own page no longer shows you (deleted in
Skribl, made link-only, taken down: posts.bloob's rule). A mute changes
nothing: you chose it. Lift the block and it is back.

ONE DRAWING, ONE CONVERSATION: an older drawing posted through the composer's
Yours takes its bookmarks onto the post with its hearts and comments, in the
same transaction (move_drawing_bookmarks, from posts._post_older).

DELETING IS REAL, AND SAID IN CODE, as likes': a post goes with its bookmarks
(posts.drop_post), a drawing deleted through the site with its bookmarks
(posts.bloob_delete), an account with its own bookmarks and every bookmark on
what it owned (accounts.delete_person). The ON DELETE CASCADEs are the net.

Every state-changing request shows the site's token and Origin and is limited
per person (security.LIMITS, "bookmark") before it reads anything
(security.over).
"""
import base64
from datetime import datetime, timezone

import sqlalchemy as sa
from flask import jsonify, request

from .accounts import _json_error, _rests
from .models import PERSON_PREFIX, Bookmark, Comment, Person, Post, as_utc
from .safety import hidden_ids
from .security import current_person, origin_ok, over, site, token_ok

#: A page of your Bookmarks (your own page's tab), as many as a page of Home.
PAGE = 20

#: The most reads one page of your Bookmarks makes, while what it reads is
#: hidden from you (a drawing made link-only since, say): past them, the page
#: ends there and Load more goes on.
READS = 6


def _col(kind):
    return {"p": Bookmark.post_id, "s": Bookmark.drawing_id, "c": Bookmark.comment_id}[kind]


def _where(on):
    """The bookmarks on `on` (a comments.On: a post or a drawing), as SQL."""
    return Bookmark.post_id == on.post.id if on.post is not None else Bookmark.drawing_id == on.drawing


def marked(viewer, posts=(), drawings=(), comments=()):
    """Which of these things `viewer` keeps: a set of ("p", a post's internal
    id), ("s", a drawing's public id) and ("c", a comment's internal id; the
    comment thread, step 3). One read a kind asked; nothing for nobody signed
    in. Never how many, and never anybody else's."""
    out = set()
    if viewer is None:
        return out
    for kind, ids in (("p", posts), ("s", drawings), ("c", comments)):
        ids = [i for i in dict.fromkeys(ids or ()) if i is not None]
        if not ids:
            continue
        col = _col(kind)
        q = sa.select(col).where(Bookmark.person_id == viewer.id, col.in_(ids))
        out |= {(kind, k) for (k,) in site().session().execute(q).all()}
    return out


# ---- your Bookmarks (your own page's tab) ----------------------------------------

def _key():
    """What orders a page of your Bookmarks after their moment: the thing's
    own address, p<a post's>, s<a drawing's> or c<a comment's>, so a cursor
    names no internal id. The letters are written into the SQL, not sent
    beside it."""
    return sa.func.coalesce(sa.literal_column("'p'", sa.String) + Post.public_id,
                            sa.literal_column("'s'", sa.String) + Bookmark.drawing_id,
                            sa.literal_column("'c'", sa.String) + Comment.public_id)


def _cursor(when, key):
    """Where a page of your Bookmarks ended: the bookmark's moment and its
    thing's address."""
    raw = f"{int(as_utc(when).timestamp() * 1_000_000)}.{key}"
    return base64.urlsafe_b64encode(raw.encode()).rstrip(b"=").decode()


def _uncursor(text):
    """(moment, address) from _cursor, or None."""
    try:
        raw = base64.urlsafe_b64decode((text or "") + "=" * (-len(text or "") % 4)).decode()
        us, key = raw.split(".", 1)
        if not (2 <= len(key) <= 40 and key[0] in "psc"):
            return None
        return datetime.fromtimestamp(int(us) / 1_000_000, tz=timezone.utc), key
    except (ValueError, TypeError, UnicodeDecodeError, OverflowError, OSError):
        return None


def _rows(me, at, limit, hidden):
    """A read of `me`'s bookmarks after `at`, newest first: (moment, address,
    bookmark, post or None, whose). Nobody `hidden` (a block either way, or
    taken down), and no post taken down but `me`'s own. One read, on the
    person's own index (ix_social_bookmarks_person_created)."""
    key = _key()
    q = (sa.select(Bookmark.created_at, key.label("k"), Bookmark, Post, Person, Comment)
         .join(Person, Person.id == Bookmark.owner_id)
         .outerjoin(Post, Post.id == Bookmark.post_id)
         .outerjoin(Comment, Comment.id == Bookmark.comment_id)
         .where(Bookmark.person_id == me.id)
         .where(sa.or_(Bookmark.post_id.is_(None), Post.taken_down_at.is_(None), Post.person_id == me.id))
         # A COMMENT (the comment thread, step 3): never one taken down but your own.
         .where(sa.or_(Bookmark.comment_id.is_(None), Comment.taken_down_at.is_(None), Comment.person_id == me.id))
         .order_by(Bookmark.created_at.desc(), key.desc()).limit(limit))
    if hidden:
        q = q.where(Bookmark.owner_id.notin_(hidden))
    if at is not None:
        when, k = at
        q = q.where(sa.or_(Bookmark.created_at < when, sa.and_(Bookmark.created_at == when, key < k)))
    return site().session().execute(q).all()


def _drawings_shown(me, sids):
    """{a drawing's public id: Skribl's description of it} for those of
    `sids` whose own page shows them to `me` (posts.bloob's rule: public, or
    their own link-only or taken-down one, by one of the site's people), in
    one read (describe_posts)."""
    if not sids:
        return {}
    from skribl import describe_posts
    got = describe_posts(list(dict.fromkeys(sids)), viewer_id=me.public_id)
    out = {}
    for sid, sk in got.items():
        author = str((sk or {}).get("user_id") or "")
        vis = (sk or {}).get("visibility")
        if author.startswith(PERSON_PREFIX) and (vis == "public" or (vis in ("withheld", "unlisted")
                                                                    and author == me.public_id)):
            out[sid] = sk
    return out


def marked_page(me, before=None, limit=PAGE):
    """YOUR BOOKMARKS (your own page's Bookmarks tab; yours alone, on your own
    page and nobody else's): the posts and the drawings shown outside a post
    you kept, newest kept first, as (entries, next cursor or None), each
    entry as posts.cards() reads one. Hidden, never deleted: what a block
    either way hides, anybody taken down, a post taken down but your own (you
    see it with its note, as on Home), a drawing its own page no longer
    shows you. A mute leaves it where it is: you chose it. The cursor names
    the bookmark's moment and the thing's address; one that cannot be read
    ends the list."""
    from .posts import _entry
    if me is None:
        return [], None
    at = _uncursor(before) if before else None
    if before and at is None:
        return [], None
    hidden = sorted(hidden_ids(me))
    entries, last, more = [], at, False
    for _ in range(READS):
        rows = _rows(me, last, limit + 1, hidden)
        shown = _drawings_shown(me, [r.Bookmark.drawing_id for r in rows if r.Bookmark.drawing_id is not None])
        # A COMMENT kept (the comment thread, step 3): while its way up shows
        # to you (comments.chain_shown), as a reply to it would.
        from .comments import chain_shown
        open_c = chain_shown([r.Comment for r in rows if r.Comment is not None], me)
        for r in rows:
            if len(entries) == limit:
                more = True              # one is left after the last taken
                break
            last = (r.created_at, r.k)
            b = r.Bookmark
            if b.post_id is not None:
                entries.append(_entry(r.Post, r.Person))
            elif b.comment_id is not None:
                if r.Comment is not None and r.Comment.id in open_c:
                    entries.append({"kind": "c", "at": as_utc(r.Comment.created_at), "key": "c" + r.Comment.public_id,
                                    "comment": r.Comment, "who": r.Person})
            elif b.drawing_id in shown:
                sk = shown[b.drawing_id]
                when = as_utc(datetime.fromisoformat(sk["created_at"])) if sk.get("created_at") else as_utc(b.created_at)
                entries.append({"kind": "s", "at": when, "key": "s" + b.drawing_id, "sk": sk, "who": r.Person})
        if more or len(rows) <= limit:
            break
        if len(entries) == limit:
            # The page is full at the end of a read: one more read says
            # whether anything follows it.
            more = bool(_rows(me, last, 1, hidden))
            break
    else:
        more = last is not None
    return entries, (_cursor(*last) if more and last else None)


# ---- deleting --------------------------------------------------------------------

def _drop(where):
    site().session().execute(sa.delete(Bookmark).where(where).execution_options(synchronize_session=False))


def drop_post_bookmarks(post_id):
    """Every bookmark on a post (posts.drop_post, before the post)."""
    _drop(Bookmark.post_id == post_id)


def drop_drawing_bookmarks(skribl_id):
    """Every bookmark on a drawing shown outside a post (posts.bloob_delete,
    once the drawing is gone)."""
    _drop(Bookmark.drawing_id == str(skribl_id))


def move_drawing_bookmarks(skribl_id, post_id):
    """ONE DRAWING, ONE CONVERSATION (likes.move_drawing_likes' twin): every
    bookmark on a drawing shown outside a post, onto the post it is now in,
    each keeping its person and its moment, so your Bookmarks keep it where
    it was. The post is new, so no one's bookmark on it can meet theirs on
    the drawing (once a person, once a thing). Flushes nothing."""
    site().session().execute(
        sa.update(Bookmark).where(Bookmark.drawing_id == str(skribl_id))
        .values(post_id=post_id, drawing_id=None).execution_options(synchronize_session=False))


def drop_comment_bookmarks(ids):
    """Every bookmark on the comments `ids` (internal ids; comments.retire
    and comments._drop: one that goes, or keeps its place, nobody's)."""
    ids = sorted(set(ids or ()))
    if ids:
        _drop(Bookmark.comment_id.in_(ids))


def drop_owner_bookmarks(person_id):
    """Every bookmark on what a person owned (accounts.delete_person)."""
    _drop(Bookmark.owner_id == person_id)


def drop_person_bookmarks(person_id):
    """Every bookmark a person kept (accounts.delete_person)."""
    _drop(Bookmark.person_id == person_id)


# ---- the routes ------------------------------------------------------------------

def register(bp):
    """Add the bookmarks' routes to the site's blueprint."""

    def set_mark(find, yours):
        """This person's bookmark on what `find(me)` says the request is about
        (a comments.On it is open to, or None: gone), kept or taken away.
        `yours(me)` is their own bookmark on that address, as SQL: taking one
        away needs nothing else."""
        if not origin_ok() or not token_ok():
            return _json_error("stale", 403)
        me = current_person()
        if me is None:
            return _json_error("signed_out", 401)
        if over("bookmark", "person|" + me.public_id):
            return _json_error("limited", 429)
        body = request.get_json(silent=True)
        if not isinstance(body, dict) or not isinstance(body.get("bookmarked"), bool):
            return _json_error("bad", 400)
        sess = site().session()
        if body["bookmarked"]:
            from .comments import may_comment
            if not may_comment(me):
                # Taken down (Your Reports): nothing new from the account.
                return _json_error("taken_down", 403)
            on = find(me)
            if on is None or not on.open_to(me):
                # Not there, taken down, or a block either way: gone, as its page is.
                return _json_error("gone", 404)
            mine = sa.and_(_where(on), Bookmark.person_id == me.id)
            if sess.execute(sa.select(Bookmark.id).where(mine)).first() is None:
                try:
                    with sess.begin_nested():
                        sess.add(Bookmark(person_id=me.id, **on.row()))
                        sess.flush()
                except sa.exc.IntegrityError:
                    pass            # kept a moment ago, from another tap: one bookmark
        else:
            # YOUR OWN, TAKEN AWAY whatever became of the thing since; one
            # that was never kept is gone only if the thing is.
            gone = sess.execute(sa.delete(Bookmark).where(yours(me))
                                .execution_options(synchronize_session=False)).rowcount
            if not gone and find(me) is None:
                return _json_error("gone", 404)
        sess.flush()
        return jsonify({"ok": True, "bookmarked": body["bookmarked"]})

    @bp.post("/c/<public_id>/bookmark")
    @_rests(json_answer=True)
    def bookmark_comment(public_id):
        """This person's bookmark on a comment or a reply (the comment thread,
        step 3), kept or taken away: one they may see, no place, nothing
        taken down (reposts.comment_open); taken away, their own goes
        whatever became of it since."""
        if not origin_ok() or not token_ok():
            return _json_error("stale", 403)
        me = current_person()
        if me is None:
            return _json_error("signed_out", 401)
        if over("bookmark", "person|" + me.public_id):
            return _json_error("limited", 429)
        body = request.get_json(silent=True)
        if not isinstance(body, dict) or not isinstance(body.get("bookmarked"), bool):
            return _json_error("bad", 400)
        from .comments import may_comment
        from .reposts import comment_open
        sess = site().session()
        got = comment_open(me, public_id)
        if body["bookmarked"]:
            if not may_comment(me):
                return _json_error("taken_down", 403)
            if got is None:
                return _json_error("gone", 404)
            c = got["c"]
            mine = sa.and_(Bookmark.comment_id == c.id, Bookmark.person_id == me.id)
            if sess.execute(sa.select(Bookmark.id).where(mine)).first() is None:
                try:
                    with sess.begin_nested():
                        sess.add(Bookmark(person_id=me.id, comment_id=c.id, owner_id=c.person_id))
                        sess.flush()
                except sa.exc.IntegrityError:
                    pass            # kept a moment ago, from another tap: one bookmark
        else:
            cid = sa.select(Comment.id).where(Comment.public_id == str(public_id)).scalar_subquery()
            gone = sess.execute(sa.delete(Bookmark).where(Bookmark.person_id == me.id, Bookmark.comment_id == cid)
                                .execution_options(synchronize_session=False)).rowcount
            if not gone and got is None:
                return _json_error("gone", 404)
        sess.flush()
        return jsonify({"ok": True, "bookmarked": body["bookmarked"]})

    @bp.post("/p/<public_id>/bookmark")
    @_rests(json_answer=True)
    def bookmark_post(public_id):
        """This person's bookmark on a post, kept or taken away."""
        from .comments import on_post

        def yours(me):
            post = sa.select(Post.id).where(Post.public_id == str(public_id)).scalar_subquery()
            return sa.and_(Bookmark.person_id == me.id, Bookmark.post_id == post)
        return set_mark(lambda me: on_post(me, public_id=public_id), yours)

    @bp.post("/b/<skribl_id>/bookmark")
    @_rests(json_answer=True)
    def bookmark_drawing(skribl_id):
        """This person's bookmark on a drawing shown outside a post, kept or
        taken away. Under the drawing's lock (posts.drawing_lock), so a
        bookmark never lands on a drawing as it moves into a post."""
        from .comments import on_drawing
        from .posts import drawing_lock

        def find(me):
            drawing_lock(skribl_id)
            return on_drawing(me, skribl_id)

        def yours(me):
            return sa.and_(Bookmark.person_id == me.id, Bookmark.drawing_id == str(skribl_id))
        return set_mark(find, yours)

    return bp
