"""Reposts and quote posts (the map, part two, item 3; docs/SOCIAL-SITE.md
section 17), from the reposts mock and the owner's "All yes" (Nov 14, about
7:35 PM Mountain): one drawing, one conversation, and a quote is a repost
with your own words, or your own drawing.

    /p/<id>/repost      POST {reposted}: this person's repost of a post, made
                        or undone (JSON: {ok, reposted, n}: n is how many
                        reposts and quotes the post's row now says to them)
    /p/<id>/quoted      the post, small, as the composer shows it under the
                        words of a quote (JSON {html}); 404 to anybody who
                        may not quote it
    /b/<skribl_id>/quoted   the same, for a drawing shown outside a post

THE ROW UNDER A POST: comment · repost · heart · ⋯ · Open ›, the repost
saying how many reposts and quotes there are (none at zero), lit in the
small violet ink once the repost is yours. Share is in the ⋯ (Share… and Copy
link were there already). A tap raises a small sheet, one card: "Repost"
("Show it to the people who follow you"), or once it is yours "Undo repost"
("Take it off your page and your followers’ Home"), and "Quote" ("Repost it
with your own words, or a drawing"), which opens the composer with the post
small under the words (compose.js). No toast: the row lights and its count
moves, as the heart's does; Undo is the sheet's own row (posts.js).

A REPOST IS NO POST OF ITS OWN (one drawing, one conversation): it shows the
original's own card, its author, words, drawing, hearts and comments, with
"Mira Lopez reposted" at its top ("You reposted" for yours), on Home's
Following for the people who follow the reposter and on the reposter's
Posts tab. Everyone shows posts only. The same post twice in one page (a
post, and somebody you follow reposting it; two of them reposting it) shows
once, the newest (posts.feed_page). Nobody reposts a drawing shown outside a
post (only its maker posts it); it can be quoted.

A QUOTE IS A POST (social_posts.is_quote) with the original small inside it:
its author's name and @handle, its words (two lines at most), its drawing as
the Gallery's still picture with "drawn in", a tap opening the original. Its
own words, its own drawing, or both. A QUOTE OUTLIVES WHAT IT QUOTES: once
the original is gone, or hidden from the person looking (a block either
way, it or its maker taken down, a drawing deleted or made link-only), the
small card says "This post is gone." and nothing more.

WHO MAY REPOST OR QUOTE: somebody signed in, not taken down, on a post (or,
to quote, a drawing) open to them (comments.On: there for everybody, no
block either way with its maker), as a like. Your own too. Undoing your own
repost always works, by the address alone, whatever became of the post.

COUNTED BY THE VIEWER, as likes are: reposts and quotes by anybody hidden
from them (a block either way, or taken down) are neither shown nor
counted; a quote taken down counts for nobody but its author. A mute
changes no number. Home's cards ask once for all of them (stats()).

WHO IS TOLD (activity.py): the original's author, in Activity, "Mira
reposted your post" (to the post; several since you last looked, one row)
and "Rook quoted your post" (to the quote, its words under it). Undo takes
the repost and its row away; nothing is kept but the repost itself. Quiet
for anybody muted, as likes are; neither lights the bell's dot (nothing to
answer).

DELETING IS REAL, AND SAID IN CODE: a post goes with its reposts, and every
quote of it lets go of it (posts.drop_post); a drawing deleted through the
site lets go of its quotes (posts.bloob_delete); an account goes with its
own reposts and every repost of what it owned, and the quotes of what it
owned let go (accounts.delete_person). The foreign keys (CASCADE, SET NULL)
are the net. An older drawing posted through the composer's Yours takes its
quotes onto the post (move_drawing_quotes), as its hearts and comments.

Every state-changing request shows the site's token and Origin and is limited
per person (security.LIMITS, "repost") before it reads anything.
"""
import sqlalchemy as sa
import sqlalchemy.orm  # noqa: F401  (sa.orm.aliased)
from flask import jsonify, render_template, request, url_for

from .accounts import _json_error, _rests
from .gallery import _after
from .models import PERSON_PREFIX, Person, Post, Repost, as_utc
from .safety import hidden_ids
from .security import current_person, origin_ok, over, site, token_ok


# ---- how many, and whether one is yours ----------------------------------------

def stats(viewer, posts=(), drawings=()):
    """{("p", a post's internal id) or ("s", a drawing's public id): {"n": how
    many reposts and quotes `viewer` is shown, "mine": whether a repost is
    theirs}}, for every thing asked: one grouped read of reposts (posts
    only), one of a post's quotes and one of a drawing's, nobody hidden from
    `viewer` counted, a quote taken down only for its own author."""
    hidden = sorted(hidden_ids(viewer))
    mine_id = viewer.id if viewer is not None else -1
    out = {}
    pids = [i for i in dict.fromkeys(posts or ()) if i is not None]
    sids = [i for i in dict.fromkeys(drawings or ()) if i]
    for i in pids:
        out[("p", i)] = {"n": 0, "mine": False}
    for i in sids:
        out[("s", i)] = {"n": 0, "mine": False}
    sess = site().session()
    if pids:
        q = (sa.select(Repost.post_id, sa.func.count(),
                       sa.func.max(sa.case((Repost.person_id == mine_id, 1), else_=0)))
             .where(Repost.post_id.in_(pids)).group_by(Repost.post_id))
        if hidden:
            q = q.where(Repost.person_id.notin_(hidden))
        for pid, n, m in sess.execute(q).all():
            out[("p", pid)]["n"] += int(n)
            out[("p", pid)]["mine"] = bool(m)
    for kind, col, ids in (("p", Post.quoted_post_id, pids), ("s", Post.quoted_drawing_id, sids)):
        if not ids:
            continue
        q = (sa.select(col, sa.func.count()).where(col.in_(ids))
             .where(sa.or_(Post.taken_down_at.is_(None), Post.person_id == mine_id)).group_by(col))
        if hidden:
            q = q.where(Post.person_id.notin_(hidden))
        for k, n in sess.execute(q).all():
            out[(kind, k)]["n"] += int(n)
    return out


def stat_on(on, viewer):
    """stats() for one post or drawing (a comments.On)."""
    asked = {"posts": [on.post.id]} if on.post is not None else {"drawings": [on.drawing]}
    return stats(viewer, **asked)[on.key]


# ---- the feed: Home's Following, and a person's Posts tab ------------------------

def reposts_before(at, limit, viewer, hidden=frozenset(), among=None, person=None):
    """A page of reposts older than `at`, newest first, as feed entries:
    (entries, more). Each entry is the ORIGINAL's card ("kind" "p", its post
    and author) with "by", who reposted it, at the repost's time, keyed r<the
    post's address> (posts._cursor). `among` (Home's Following, a subquery of
    people's ids): theirs, and the viewer's own; `person` (their Posts tab):
    theirs. Never a post taken down, nor anybody in `hidden` on either end
    (the caller's: a block either way and taken down; on Home, the muted
    too, so a repost by somebody you muted, or of their post, stays away)."""
    by = sa.orm.aliased(Person)
    q = (sa.select(Repost.created_at, Post, Person, by)
         .join(Post, Post.id == Repost.post_id)
         .join(Person, Person.id == Post.person_id)
         .join(by, by.id == Repost.person_id)
         .where(Post.taken_down_at.is_(None))
         .order_by(Repost.created_at.desc(), Post.public_id.desc()).limit(limit + 1))
    if person is not None:
        q = q.where(Repost.person_id == person.id)
    if among is not None:
        q = q.where(sa.or_(Repost.person_id.in_(among), Repost.person_id == (viewer.id if viewer is not None else -1)))
    hid = sorted(hidden)
    if hid:
        q = q.where(Repost.person_id.notin_(hid), Post.person_id.notin_(hid))
    if at is not None:
        # The one cursor (posts._cursor), Home's order: newest first, and at
        # one moment a drawing shown outside a post (s), then the reposts
        # (r), then the posts (p), each by its address (gallery._after).
        q = q.where(_after(Repost.created_at, Post.public_id, "r", at))
    rows = site().session().execute(q).all()
    return ([{"kind": "p", "at": as_utc(when), "key": "r" + post.public_id, "post": post, "who": who, "by": rb}
             for when, post, who, rb in rows[:limit]], len(rows) > limit)


def once(page):
    """THE SAME POST TWICE IN ONE PAGE SHOWS ONCE, the newest: a post, and its
    reposts by the people you follow (or two of theirs), are one card, the
    first of them in the page's own order (newest first)."""
    seen, out = set(), []
    for e in page:
        k = ("p", e["post"].id) if e.get("kind") == "p" and "post" in e else None
        if k is not None and k in seen:
            continue
        if k is not None:
            seen.add(k)
        out.append(e)
    return out


# ---- a quote post's small card -------------------------------------------------

class Quoted:
    """What the quote posts in a page of cards show small: read once for the
    page (posts.cards), the originals' rows in one read and their drawings in
    the page's one describe_posts. `skribls` are the drawings to describe."""

    def __init__(self, posts, viewer):
        self.viewer = viewer
        self.hidden = hidden_ids(viewer)
        self.posts = {}
        self.owners = {}
        quotes = [p for p in posts if getattr(p, "is_quote", False)]
        pids = sorted({p.quoted_post_id for p in quotes if p.quoted_post_id is not None})
        sess = site().session()
        if pids:
            for post, who in sess.execute(sa.select(Post, Person).join(Person, Person.id == Post.person_id)
                                          .where(Post.id.in_(pids))).all():
                self.posts[post.id] = (post, who)
        self.drawing_ids = sorted({p.quoted_drawing_id for p in quotes if p.quoted_drawing_id})
        self.skribls = [post.skribl_id for post, _ in self.posts.values() if post.skribl_id] + self.drawing_ids

    def _shown_post(self, post, who):
        """The page's rule (comments.on_post): no block either way, nobody
        taken down, nothing taken down, but to its own author."""
        mine = self.viewer is not None and self.viewer.id == who.id
        if who.id in self.hidden:
            return False
        return mine or (post.taken_down_at is None and who.taken_down_at is None)

    def card(self, quote, described, makers):
        """The small card of one quote post: {"gone": True}, or {"url", "who",
        "words", "at", "sk" (its drawing as Skribl describes it, or None),
        "says" (what its ▶ says: "drawn in 15 sec", "3 pages", or "")}.
        `described` is the page's describe_posts, `makers` {public id: person}
        for the drawings' makers."""
        from .gallery import says
        if quote.quoted_post_id is not None and quote.quoted_post_id in self.posts:
            post, who = self.posts[quote.quoted_post_id]
            if not self._shown_post(post, who):
                return {"gone": True}
            sk = described.get(post.skribl_id) if post.skribl_id else None
            return {"gone": False, "url": url_for("social.post_page", public_id=post.public_id), "who": who,
                    "words": post.words or "", "at": post.created_at, "sk": sk, "says": _says(sk, says)}
        sid = quote.quoted_drawing_id
        if sid:
            sk = described.get(sid)
            who = makers.get(str((sk or {}).get("user_id") or ""))
            if sk is None or who is None or who.id in self.hidden or not _drawing_shown(sk, self.viewer):
                return {"gone": True}
            from .posts import _title_words
            return {"gone": False, "url": url_for("social.bloob_page", skribl_id=sid), "who": who,
                    "words": _title_words(sk.get("title")), "at": _made(sk), "sk": sk, "says": _says(sk, says)}
        return {"gone": True}


def _says(sk, says):
    """What the small card's ▶ says: a Flip its pages, a drawing "drawn in"
    and how long (the in-post player's own words at rest)."""
    words, pages = says(sk)
    if not words:
        return ""
    return words if pages else "drawn in " + words


def _made(sk):
    from datetime import datetime
    try:
        return as_utc(datetime.fromisoformat(str(sk.get("created_at"))))
    except (TypeError, ValueError):
        return None


def _drawing_shown(sk, viewer):
    """A drawing shown outside a post as its own page shows it (posts.bloob's
    rule): public, or the viewer's own kept link-only or taken down, by one
    of the site's people."""
    author = str((sk or {}).get("user_id") or "")
    vis = (sk or {}).get("visibility")
    mine = viewer is not None and author == viewer.public_id
    return author.startswith(PERSON_PREFIX) and (vis == "public" or (vis in ("withheld", "unlisted") and mine))


def makers_of(described, sids):
    """{a person's public id: their row} for the makers of the drawings
    `sids` as `described` (one read)."""
    ids = {str((described.get(s) or {}).get("user_id") or "") for s in sids}
    ids = {i for i in ids if i.startswith(PERSON_PREFIX)}
    if not ids:
        return {}
    return {p.public_id: p for p in site().session().execute(
        sa.select(Person).where(Person.public_id.in_(sorted(ids)))).scalars()}


def quotable(me, kind, oid):
    """What `me` may quote, as a comments.On, or None: a post or a drawing
    shown outside a post open to them (no block either way, not taken down,
    a drawing public), as a like asks."""
    from .comments import on_drawing, on_post
    on = on_post(me, public_id=oid) if kind == "p" else on_drawing(me, oid)
    if on is None or not on.open_to(me):
        return None
    return on


def small_of(on, me):
    """The small card of a post or a drawing `on` (a comments.On), as a quote
    of it shows it to `me`: for the composer."""
    from skribl import describe_posts
    from .gallery import says
    from .posts import _title_words
    sid = on.post.skribl_id if on.post is not None else on.drawing
    sk = (describe_posts([sid], viewer_id=me.public_id).get(sid) if sid else None) if on.sk is None else on.sk
    if on.post is not None:
        return {"gone": False, "url": on.page(), "who": on.owner, "words": on.post.words or "",
                "at": on.post.created_at, "sk": sk, "says": _says(sk, says)}
    return {"gone": False, "url": on.page(), "who": on.owner, "words": _title_words((sk or {}).get("title")),
            "at": _made(sk or {}), "sk": sk, "says": _says(sk, says)}


# ---- deleting, and one drawing's moving into a post ------------------------------

def _drop(where):
    site().session().execute(sa.delete(Repost).where(where).execution_options(synchronize_session=False))


def _let_go(where, **values):
    site().session().execute(sa.update(Post).where(where).values(**values)
                             .execution_options(synchronize_session=False))


def drop_post_reposts(post_id):
    """A post's reposts, and its quotes letting go of it (posts.drop_post,
    before the post): each quote stays, saying it is gone."""
    _drop(Repost.post_id == post_id)
    _let_go(Post.quoted_post_id == post_id, quoted_post_id=None, quoted_owner_id=None)


def drop_drawing_quotes(skribl_id):
    """A drawing shown outside a post deleted (posts.bloob_delete, once it is
    gone): its quotes let go of it."""
    _let_go(Post.quoted_drawing_id == str(skribl_id), quoted_drawing_id=None, quoted_owner_id=None)


def move_drawing_quotes(skribl_id, post_id):
    """ONE DRAWING, ONE CONVERSATION (likes.move_drawing_likes' twin): the
    quotes of a drawing shown outside a post quote the post it is now in.
    Flushes nothing."""
    _let_go(Post.quoted_drawing_id == str(skribl_id), quoted_post_id=post_id, quoted_drawing_id=None)


def drop_person_reposts(person_id):
    """Every repost a person made, and every repost of what they owned; the
    quotes of what they owned letting go of it (accounts.delete_person)."""
    _drop(sa.or_(Repost.person_id == person_id, Repost.owner_id == person_id))
    _let_go(Post.quoted_owner_id == person_id, quoted_post_id=None, quoted_drawing_id=None, quoted_owner_id=None)


# ---- the routes ------------------------------------------------------------------

def register(bp):
    """Add the reposts' routes to the site's blueprint."""

    @bp.post("/p/<public_id>/repost")
    @_rests(json_answer=True)
    def repost_post(public_id):
        """This person's repost of a post, made or undone: {reposted}."""
        if not origin_ok() or not token_ok():
            return _json_error("stale", 403)
        me = current_person()
        if me is None:
            return _json_error("signed_out", 401)
        if over("repost", "person|" + me.public_id):
            return _json_error("limited", 429)
        body = request.get_json(silent=True)
        if not isinstance(body, dict) or not isinstance(body.get("reposted"), bool):
            return _json_error("bad", 400)
        from .comments import may_comment, on_post
        sess = site().session()
        on = on_post(me, public_id=public_id)
        if body["reposted"]:
            if not may_comment(me):
                # Taken down (Your Reports): nothing new from the account.
                return _json_error("taken_down", 403)
            if on is None or not on.open_to(me):
                # Not there, taken down, or a block either way: gone, as its page is.
                return _json_error("gone", 404)
            mine = sa.and_(Repost.post_id == on.post.id, Repost.person_id == me.id)
            if sess.execute(sa.select(Repost.id).where(mine)).first() is None:
                try:
                    with sess.begin_nested():
                        sess.add(Repost(person_id=me.id, post_id=on.post.id, owner_id=on.owner.id))
                        sess.flush()
                except sa.exc.IntegrityError:
                    pass            # reposted a moment ago, from another tap: one repost
        else:
            # YOUR OWN, UNDONE whatever became of the post since; one that was
            # never made is gone only if the post is.
            post = sa.select(Post.id).where(Post.public_id == str(public_id)).scalar_subquery()
            gone = sess.execute(sa.delete(Repost).where(Repost.person_id == me.id, Repost.post_id == post)
                                .execution_options(synchronize_session=False)).rowcount
            if not gone and on is None:
                return _json_error("gone", 404)
        sess.flush()
        n = stat_on(on, me)["n"] if on is not None else 0
        return jsonify({"ok": True, "reposted": body["reposted"], "n": n})

    def quoted(kind, oid):
        """The small card a quote of it shows, for the composer: {html}."""
        me = current_person()
        if me is None:
            return _json_error("signed_out", 401)
        on = quotable(me, kind, oid)
        if on is None:
            return _json_error("gone", 404)
        html = render_template("social/_quote.html", q=small_of(on, me), me=me)
        resp = jsonify({"html": html.strip()})
        resp.headers["Cache-Control"] = "private, no-store"
        return resp

    @bp.get("/p/<public_id>/quoted")
    @_rests(json_answer=True)
    def quoted_post(public_id):
        """A post, small, as a quote of it shows it (the composer's)."""
        return quoted("p", public_id)

    @bp.get("/b/<skribl_id>/quoted")
    @_rests(json_answer=True)
    def quoted_drawing(skribl_id):
        """A drawing shown outside a post, small, as a quote of it shows it."""
        return quoted("s", skribl_id)

    return bp
