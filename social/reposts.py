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
    /c/<public_id>/repost   POST {reposted}: a comment's or a reply's (the
                        comment thread, step 3), as a post's
    /c/<public_id>/quoted   a comment or a reply, small, for the composer

THE ROW UNDER A POST: comment · repost · heart · ⋯ (no Open ›), the repost
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
from .models import PERSON_PREFIX, Person, Post, Repost, as_utc, first_name
from .safety import hidden_ids
from .security import current_person, origin_ok, over, site, token_ok


# ---- how many, and whether one is yours ----------------------------------------

def stats(viewer, posts=(), drawings=(), comments=()):
    """{("p", a post's internal id), ("s", a drawing's public id) or ("c", a
    comment's internal id; the comment thread, step 3): {"n": how many
    reposts and quotes `viewer` is shown, "mine": whether a repost is
    theirs}}, for every thing asked: one grouped read of reposts for posts
    and one for comments, one of a post's quotes, one of a drawing's and one
    of a comment's, nobody hidden from `viewer` counted, a quote taken down
    only for its own author."""
    hidden = sorted(hidden_ids(viewer))
    mine_id = viewer.id if viewer is not None else -1
    out = {}
    pids = [i for i in dict.fromkeys(posts or ()) if i is not None]
    sids = [i for i in dict.fromkeys(drawings or ()) if i]
    cids = [i for i in dict.fromkeys(comments or ()) if i is not None]
    for kind, ids in (("p", pids), ("s", sids), ("c", cids)):
        for i in ids:
            out[(kind, i)] = {"n": 0, "mine": False}
    sess = site().session()
    for kind, col, ids in (("p", Repost.post_id, pids), ("c", Repost.comment_id, cids)):
        if not ids:
            continue
        q = (sa.select(col, sa.func.count(), sa.func.max(sa.case((Repost.person_id == mine_id, 1), else_=0)))
             .where(col.in_(ids)).group_by(col))
        if hidden:
            q = q.where(Repost.person_id.notin_(hidden))
        for k, n, m in sess.execute(q).all():
            out[(kind, k)]["n"] += int(n)
            out[(kind, k)]["mine"] = bool(m)
    for kind, col, ids in (("p", Post.quoted_post_id, pids), ("s", Post.quoted_drawing_id, sids),
                           ("c", Post.quoted_comment_id, cids)):
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
    and author; a comment's, "kind" "c", the comment and its author) with
    "by", who reposted it, at the repost's time, keyed r<the post's address>
    (or the comment's: posts._cursor). `among` (Home's Following, a subquery
    of people's ids): theirs, and the viewer's own; `person` (their Posts
    tab): theirs. Never a post taken down, nor anybody in `hidden` on either
    end (the caller's: a block either way and taken down; on Home, the muted
    too, so a repost by somebody you muted, or of their post, stays away).
    A COMMENT OR A REPLY REPOSTED (the comment thread, step 3; the owner's yes
    to "A Comment Shared", Nov 17) comes in the same read, by the same rules:
    never a place (nobody's), nor one taken down; the way to it, and what it
    is on, its card reads by the page's rules (comments.world_cards)."""
    from .models import Comment
    by = sa.orm.aliased(Person)
    # What a repost is of, the post's or the comment's: its address, its author.
    addr = sa.func.coalesce(Post.public_id, Comment.public_id)
    q = (sa.select(Repost.created_at, Post, Comment, Person, by)
         .outerjoin(Post, Post.id == Repost.post_id)
         .outerjoin(Comment, Comment.id == Repost.comment_id)
         .join(Person, Person.id == sa.func.coalesce(Post.person_id, Comment.person_id))
         .join(by, by.id == Repost.person_id)
         .where(sa.or_(sa.and_(Repost.post_id.isnot(None), Post.taken_down_at.is_(None)),
                       sa.and_(Repost.comment_id.isnot(None), Comment.taken_down_at.is_(None), Comment.gone.is_(None))))
         .order_by(Repost.created_at.desc(), addr.desc()).limit(limit + 1))
    if person is not None:
        q = q.where(Repost.person_id == person.id)
    if among is not None:
        q = q.where(sa.or_(Repost.person_id.in_(among), Repost.person_id == (viewer.id if viewer is not None else -1)))
    hid = sorted(hidden)
    if hid:
        q = q.where(Repost.person_id.notin_(hid), Person.id.notin_(hid))
    if at is not None:
        # The one cursor (posts._cursor), Home's order: newest first, and at
        # one moment a drawing shown outside a post (s), then the reposts
        # (r), then the posts (p), each by its address (gallery._after).
        q = q.where(_after(Repost.created_at, addr, "r", at))
    rows = site().session().execute(q).all()
    out = []
    for when, post, c, who, rb in rows[:limit]:
        if post is not None:
            out.append({"kind": "p", "at": as_utc(when), "key": "r" + post.public_id, "post": post, "who": who, "by": rb})
        else:
            out.append({"kind": "c", "at": as_utc(when), "key": "r" + c.public_id, "comment": c, "who": who, "by": rb})
    return out, len(rows) > limit


def once(page):
    """THE SAME POST TWICE IN ONE PAGE SHOWS ONCE, the newest: a post, and its
    reposts by the people you follow (or two of theirs), are one card, the
    first of them in the page's own order (newest first). A comment reposted
    twice too (the comment thread, step 3)."""
    seen, out = set(), []
    for e in page:
        k = (("p", e["post"].id) if e.get("kind") == "p" and "post" in e
             else ("c", e["comment"].id) if e.get("kind") == "c" else None)
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
        self._hands = None               # the quoted two-hands draw-backs' states (_both), read once
        self._both_lines = {}
        self.owners = {}
        quotes = [p for p in posts if getattr(p, "is_quote", False)]
        pids = sorted({p.quoted_post_id for p in quotes if p.quoted_post_id is not None})
        sess = site().session()
        if pids:
            for post, who in sess.execute(sa.select(Post, Person).join(Person, Person.id == Post.person_id)
                                          .where(Post.id.in_(pids))).all():
                self.posts[post.id] = (post, who)
        # A QUOTE SHOWS THE DRAWING IT LEADS TO, HOWEVER DEEP (the owner's "all
        # yes" to "Just a Border", Nov 16, A): a quoted post with no drawing of
        # its own that is itself a quote leads on, to the drawing its own
        # original has, through as many quotes as it takes, and shows it as a
        # quote of a drawing does. The chain ends at a drawing, at a post this
        # viewer may not see, or at words alone; a level of posts is read at a
        # time, LEAD_DEPTH levels at most.
        self.leads = {}                  # a quoted post's id -> ("p" | "s", the drawing it leads to)
        known = dict(self.posts)
        step = [(pid, pid) for pid, (post, _who) in self.posts.items()
                if not post.skribl_id and getattr(post, "is_quote", False)]
        for _depth in range(LEAD_DEPTH):
            nxt, want = [], set()
            for pid, root in step:
                post, who = known[pid]
                if pid != root:
                    if not self._shown_post(post, who):
                        continue                 # a post this viewer may not see: the chain ends
                    if post.skribl_id:
                        self.leads[root] = ("p", post.skribl_id)
                        continue
                    if not getattr(post, "is_quote", False):
                        continue                 # words alone: nothing further
                if post.quoted_drawing_id:
                    self.leads[root] = ("s", post.quoted_drawing_id)
                elif post.quoted_post_id is not None:
                    nxt.append((post.quoted_post_id, root))
                    if post.quoted_post_id not in known:
                        want.add(post.quoted_post_id)
            if want:
                for post, who in sess.execute(sa.select(Post, Person).join(Person, Person.id == Post.person_id)
                                              .where(Post.id.in_(sorted(want)))).all():
                    known[post.id] = (post, who)
            step = [(pid, root) for pid, root in nxt if pid in known]
            if not step:
                break
        self.drawing_ids = sorted({p.quoted_drawing_id for p in quotes if p.quoted_drawing_id}
                                  | {sid for kind, sid in self.leads.values() if kind == "s"})
        # A QUOTED COMMENT OR REPLY (the comment thread, step 3) shows as its
        # page would show it to this viewer (comments.seen: nobody hidden on
        # the way to it, what it is on theirs to see, nothing taken down but
        # their own), never a place. A few reads each; a page has few.
        self.comments = {}               # a quoted comment's id -> comments.seen's
        cids = sorted({p.quoted_comment_id for p in quotes if getattr(p, "quoted_comment_id", None)})
        if cids:
            from .comments import seen
            from .models import Comment
            for cid, pid in sess.execute(sa.select(Comment.id, Comment.public_id).where(Comment.id.in_(cids))).all():
                got = seen(pid, viewer)
                if got is not None and got["c"].gone is None:
                    self.comments[cid] = got
        self.skribls = ([post.skribl_id for post, _ in self.posts.values() if post.skribl_id] + self.drawing_ids
                        + [sid for kind, sid in self.leads.values() if kind == "p"]
                        + [got["c"].skribl_id for got in self.comments.values() if got["c"].skribl_id])

    def _shown_post(self, post, who):
        """The page's rule (comments.on_post): no block either way, nobody
        taken down, nothing taken down, but to its own author."""
        mine = self.viewer is not None and self.viewer.id == who.id
        if who.id in self.hidden:
            return False
        return mine or (post.taken_down_at is None and who.taken_down_at is None)

    def card(self, quote, described, makers):
        """The small card of one quote post: {"gone": True} ("what":
        "comment" for a comment's), or {"url", "who", "words", "at", "sk" (its
        drawing as Skribl describes it, or None), "says" (what its ▶ says:
        "drawn in 15 sec", "3 pages", or ""), and for a comment "on" (what
        it is on: on_words)}.
        `described` is the page's describe_posts, `makers` {public id: person}
        for the drawings' makers."""
        from .gallery import says
        cid = getattr(quote, "quoted_comment_id", None)
        if cid is not None:
            # A comment or a reply: gone once it went (GONE_COMMENT) or is
            # hidden from them, "This comment is gone." (the mock's words).
            got = self.comments.get(cid)
            if got is None:
                return {"gone": True, "what": "comment"}
            return _comment_small(got, described.get(got["c"].skribl_id) if got["c"].skribl_id else None)
        if quote.quoted_post_id is not None and quote.quoted_post_id in self.posts:
            post, who = self.posts[quote.quoted_post_id]
            if not self._shown_post(post, who):
                return {"gone": True}
            sk = described.get(post.skribl_id) if post.skribl_id else self.lead(post.id, described, makers)
            sk = _hands_line(post, self._both(post, sk, described))
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

    def _both(self, post, sk, described):
        """A QUOTED TWO-HANDS DRAW-BACK (drawback.py) shows what its card
        shows this viewer: while her drawing is shown to them, the picture of
        both (hands_picture) and the line the two make together, never his
        strokes alone; otherwise, his own drawing as it is. Read once for the
        page's quoted posts, the first time one is asked."""
        if sk is None or not getattr(post, "two_hands", False):
            return sk
        if self._hands is None:
            from .posts import hands_lines, hands_states
            twos = [p for p, _who in self.posts.values() if getattr(p, "two_hands", False)]
            self._hands = hands_states(twos, self.viewer, described)
            self._both_lines = hands_lines([pid for pid, st in self._hands.items() if st["view"] == "both"])
        st = self._hands.get(post.id)
        if not st or st["view"] != "both":
            return sk
        return dict(sk, line=self._both_lines.get(post.id) or sk.get("line"),
                    poster=url_for("social.hands_picture", skribl_id=post.skribl_id))

    def lead(self, pid, described, makers):
        """The drawing a quoted post with none of its own leads to (A), as
        `described` has it, or None. One outside a post is shown as a quote of
        it would be: by one of the site's people this viewer may see, and
        shown to them (_drawing_shown); a post's own drawing, with its post."""
        kind, sid = self.leads.get(pid, (None, None))
        sk = described.get(sid) if sid else None
        if sk is None:
            return None
        if kind == "s":
            who = makers.get(str(sk.get("user_id") or ""))
            if who is None or who.id in self.hidden or not _drawing_shown(sk, self.viewer):
                return None
        return sk


#: How many quotes deep a quote's small card looks for the drawing it leads to.
LEAD_DEPTH = 12

#: WHAT A QUOTE OF A COMMENT KEEPS ONCE THE COMMENT HAS GONE (the comment
#: thread, step 3): no comment is 0 (ids start at 1), so it reads as gone and
#: still says what it quoted: "This comment is gone." (A quoted post's own key
#: goes to NULL, and its card says "This post is gone."; a comment's has no
#: key to let it go, a cycle the host's create_all cannot sort, and SQLite
#: may give a deleted comment's id to the next one, so it is never left.)
GONE_COMMENT = 0


def _hands_line(post, sk):
    """A quoted draw-back says its hands' own times together, as its card
    does (posts.hands_said; the walkthrough's mocks, choice 6), never the
    joined drawing's, in which the first hand's part plays squeezed. One from
    before the hands were kept says what its drawing says."""
    from .drawback import read_hands
    h = read_hands(getattr(post, "hands_json", None)) if getattr(post, "is_drawback", False) else None
    if not h or len(h) < 2 or not sk or not sk.get("line"):
        return sk
    return dict(sk, line=dict(sk["line"], drawn=sum(ms for _, ms in h)))


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
    if on.post is not None and sk is None and getattr(on.post, "is_quote", False):
        # A quote of a quote shows the drawing it leads to (A), here as the
        # post being written will show it: the page's own Quoted, for one.
        from types import SimpleNamespace
        q = Quoted([SimpleNamespace(is_quote=True, quoted_post_id=on.post.id, quoted_drawing_id=None)], me)
        described = describe_posts(q.skribls, viewer_id=me.public_id) if q.skribls else {}
        sk = q.lead(on.post.id, described, makers_of(described, q.drawing_ids))
    if on.post is not None:
        sk = _hands_line(on.post, sk)
        return {"gone": False, "url": on.page(), "who": on.owner, "words": on.post.words or "",
                "at": on.post.created_at, "sk": sk, "says": _says(sk, says)}
    return {"gone": False, "url": on.page(), "who": on.owner, "words": _title_words((sk or {}).get("title")),
            "at": _made(sk or {}), "sk": sk, "says": _says(sk, says)}


def comment_open(me, public_id):
    """A comment or a reply `me` may repost or quote (the comment thread,
    step 3), as comments.seen gives it, or None: one they may see (nobody
    hidden on the way to it), on a post or a drawing open to them, neither
    it nor anything on the way to it taken down, and no place (nobody's)."""
    from .comments import seen
    got = seen(public_id, me)
    if (got is None or not got["on"].open_to(me) or got["c"].gone is not None or got["c"].taken_down_at is not None
            or any(c.taken_down_at is not None for c, _ in got["chain"])):
        return None
    return got


def on_words(on):
    """What a comment out in the world says it is on (the comment thread,
    step 3): "On Ben’s post", "On Ben’s drawing"."""
    first = first_name(on.owner.display_name)
    return f"On {first}\u2019s {'post' if on.post is not None else 'drawing'}"


def comment_small(got, me):
    """A comment or a reply, small, as a quote of it shows it (A Comment
    Shared, the owner's yes, Nov 17): its author's name and @handle and when,
    what it is on ("On Ben’s post"), its words (two lines at most), and its
    drawing's still with "drawn in", one link to its own page."""
    from skribl import describe_posts
    c = got["c"]
    return _comment_small(got, describe_posts([c.skribl_id], viewer_id=me.public_id if me else None).get(c.skribl_id)
                          if c.skribl_id else None)


def _comment_small(got, sk):
    """comment_small's card, its drawing `sk` as Skribl describes it."""
    from .gallery import says
    c = got["c"]
    return {"gone": False, "url": url_for("social.comment_page", public_id=c.public_id), "who": got["who"],
            "words": c.words or "", "at": c.created_at, "sk": sk, "says": _says(sk, says), "on": on_words(got["on"])}


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


def drop_comment_reposts(ids):
    """The comments `ids` (internal ids) going, or keeping their places (the
    comment thread, step 3; comments.retire and comments._drop): their
    reposts go, and their quotes let go of them (GONE_COMMENT), each saying
    "This comment is gone.". A place is nobody's, nothing to repost or
    quote."""
    ids = sorted(set(ids or ()))
    if ids:
        _drop(Repost.comment_id.in_(ids))
        _let_go(Post.quoted_comment_id.in_(ids), quoted_comment_id=GONE_COMMENT, quoted_owner_id=None)


def drop_person_reposts(person_id):
    """Every repost a person made, and every repost of what they owned; the
    quotes of what they owned letting go of it (accounts.delete_person)."""
    _drop(sa.or_(Repost.person_id == person_id, Repost.owner_id == person_id))
    _let_go(sa.and_(Post.quoted_owner_id == person_id, Post.quoted_comment_id.isnot(None)),
            quoted_comment_id=GONE_COMMENT, quoted_owner_id=None)
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
            # A NUDGE, where their device has Reposts and quotes on (push.py).
            from .push import note
            note(on.owner.id, me.id, "reposts")
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

    @bp.post("/c/<public_id>/repost")
    @_rests(json_answer=True)
    def repost_comment(public_id):
        """This person's repost of a comment or a reply (the comment thread,
        step 3), made or undone: {reposted}. One they may see, no place,
        nothing taken down (comment_open); undone, their own goes whatever
        became of it since."""
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
        from .comments import may_comment
        from .models import Comment
        sess = site().session()
        got = comment_open(me, public_id)
        if body["reposted"]:
            if not may_comment(me):
                return _json_error("taken_down", 403)
            if got is None:
                return _json_error("gone", 404)
            c = got["c"]
            mine = sa.and_(Repost.comment_id == c.id, Repost.person_id == me.id)
            if sess.execute(sa.select(Repost.id).where(mine)).first() is None:
                try:
                    with sess.begin_nested():
                        sess.add(Repost(person_id=me.id, comment_id=c.id, owner_id=c.person_id))
                        sess.flush()
                except sa.exc.IntegrityError:
                    pass            # reposted a moment ago, from another tap: one repost
            # A NUDGE, where their device has Reposts and quotes on (push.py).
            from .push import note
            note(c.person_id, me.id, "reposts")
        else:
            cid = sa.select(Comment.id).where(Comment.public_id == str(public_id)).scalar_subquery()
            gone = sess.execute(sa.delete(Repost).where(Repost.person_id == me.id, Repost.comment_id == cid)
                                .execution_options(synchronize_session=False)).rowcount
            if not gone and got is None:
                return _json_error("gone", 404)
        sess.flush()
        n = stats(me, comments=[got["c"].id])[("c", got["c"].id)]["n"] if got is not None else 0
        return jsonify({"ok": True, "reposted": body["reposted"], "n": n})

    @bp.get("/c/<public_id>/quoted")
    @_rests(json_answer=True)
    def quoted_comment(public_id):
        """A comment or a reply, small, as a quote of it shows it (the
        composer's; the comment thread, step 3)."""
        me = current_person()
        if me is None:
            return _json_error("signed_out", 401)
        got = comment_open(me, public_id)
        if got is None:
            return _json_error("gone", 404)
        html = render_template("social/_quote.html", q=comment_small(got, me), me=me)
        resp = jsonify({"html": html.strip()})
        resp.headers["Cache-Control"] = "private, no-store"
        return resp

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
