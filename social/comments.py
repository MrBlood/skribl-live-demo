"""Comments (phase 2, its first piece; docs/SOCIAL-SITE.md "Built: phase 2,
comments"), from the comments mock and the owner's "all yes on both" (Nov 12),
and on every drawing since the owner's yes the same day ("Comments on every
drawing, however it was made, so whatever you open has the comment box").

    /p/<id>/comments          POST: a comment on a post, or a reply to one at
                              any depth (JSON: {words, payload, answer_to});
                              its card comes back, to go in place. GET: the
                              next page of the post's comments, for Load more
                              ({html, next}).
    /b/<skribl_id>/comments   the same, on a drawing shown outside a post.
    /c/<id>                   a comment's or a reply's own page (the comment
                              thread, step 1): the way to it, it as big as a
                              post, its replies.
    /c/<id>/delete            your own comment, gone; or, on your own post
                              or drawing, anybody's, removed from it; one
                              with replies under it keeps its place, so
                              they stay (retire; JSON).

WHAT A COMMENT IS ON (On, below): a post, or a drawing shown outside a post
(a skribl one of the site's people showed in the gallery from the Pad or Flip
on its own page, with a page of its own at /b/<id>; the site has no row for
it, so a comment keeps its skribl's public id). The two look the same to
people, and whatever they open has the same comments. ITS PAGE DECIDES WHO
MAY SEE IT, AND ITS COMMENTS FOLLOW THE PAGE: a post's (on_post), a
drawing's (on_drawing, through posts.bloob: public, its author one of the
site's people, no block either way, nothing taken down but to its maker). A
drawing gone (deleted, or taken down for everybody else) takes its comments
with its page: none is shown, counted, answered or reported.

ON ITS OWN PAGE (post.html, _comments.html): "Comments" and how many, and at
the heading's end a round icon (a bubble with a plus) that opens the box
(your face, the words, Draw, Flip, Post), folded away until asked for: a
sheet from the bottom of a phone, gliding open under the heading on a desk
(the owner, Nov 13: "The comment needs to be an icon not a card"). Then the
comments newest first; "Say the first thing" where they will be, at none.

THE THREAD (the comment thread, step 1; the owner's yes, Nov 17, to the
Read More Replies mock; docs/SOCIAL-SITE.md section 18): every comment in a
bubble, its row under it (Reply and ⋯). A REPLY KEEPS THE REPLY IT ANSWERS
(answers_id, at any depth; parent_id is the comment its conversation hangs
under, so a page reads a conversation by one index; a reply from before has
none and answers its comment: answered()). ONE LEVEL, EVERYWHERE (the owner,
Nov 17: "What I want is a list of direct replies first. If you click the
reply it opens up the tree level", then "Yes, build it"): a list shows only
the direct replies to what its page is about, the post's comments or a
comment's replies, each alone (_fold), with the count by its talk cloud,
every reply under it at any depth that the viewer may see, and under it
its conversation followed down in the same column, BLUESKY'S WAY with our
look (the owner's yes, Nov 18: _chains): its first reply, the first reply
to that, ten deep, then "Read N more replies"; a tap on it opens its own
page. EVERY COMMENT
AND REPLY HAS A PAGE (/c/<id>, comment.html): the way to it above
(the_way), it as big as a post, then its own direct replies where a post's
comments stand (replies_of); the box there replies to it. Each comment's ⋯,
"This comment": Copy link and Share… (its own page), then on your own Delete
comment; on somebody else's on your own post or drawing, Remove from my post
and Report this comment; on anybody else's, Report this comment. A link to a
comment lands where it shows (landing()): a comment on its post's or
drawing's page, a reply on the page of what it answers.

WHO MAY COMMENT: somebody signed in who is not taken down, with no block
either way with the author of the post or the drawing; an answer also with
none with the author of the comment it answers. The route refuses anybody
else kindly, and neither the box nor its icon is shown to them. Signed out,
the comments are readable, and the icon raises a small sheet ("Say
something?") whose Sign in comes back to the page with the box open.

WHAT IS SHOWN, AND COUNTED: nothing by anybody hidden from the viewer (a
block either way, or taken down: safety.hidden_ids), nor any reply under one
that is, at any depth; a comment taken down only to its author, with the
note. The same rules count (counts(), a recursive read: Home's card, and the
section's heading), and Activity's rows follow them (chain_shown), so a
number never promises a comment the page will not show.

SOMEBODY YOU MUTED (mutes; the owner's C): their comment or answer is one
quiet line in its place, "Someone you muted said something. Show" ("…
answered." for an answer), the eye where their face was; Show opens it for
that visit (comments.js). thread() marks it (`quiet`); it is still shown and
still counted, so the numbers add up, and the answers under it, by others,
stay as they are.

MENTIONS (mentions.py; the owner's "All yes", Nov 15): an @handle in a
comment's or an answer's words that is somebody is a link to their page, and
they are told in Activity. Written with the comment, in the same
transaction; read once a page for all its comments (named()).

DELETING IS REAL, AND SAID IN CODE, AND KIND (retire; the owner's yes, Nov
17, to "the place stays"): a comment or a reply goes with its words, its
drawing and its mentions; one with somebody's replies under it keeps a
quiet place, nobody's ("This reply was deleted", or "removed" from a post or
drawing by its author), and theirs stay; a place with nothing left under it
goes. A post goes with its comments (posts.drop_post), a drawing
deleted through the site with its comments (posts.bloob_delete), an account
with its comments (kindly, a place where somebody else's replies hang) and
every comment on what it owned (accounts.delete_person; owner_id is on the
row, so nothing asks
Skribl whose a drawing was). The schema's ON DELETE CASCADEs are a net under
that, never the way: SQLite enforces them only where Skribl's pragma hook is
on.

A DRAWING ANSWER (the second part; the mock's 6): the drawing Draw or Flip
handed back in compose mode, posted through Skribl's create_post in the same
request, and so the same transaction, as the row that keeps its id (as
posts.post_new posts a post's). It is UNLISTED, whatever the payload says: a
drawing answer belongs to its conversation, reachable by its link and listed
nowhere. Its title is the comment's first words. A comment needs words or a
drawing. It goes with its comment (Skribl's delete_post, as its author:
_drop_drawings), and is withheld with it when an admin takes it down.

THROUGH SKRIBL'S SEAMS ONLY: create_post, delete_post, describe_posts and
their exceptions (documented names, verify_social section 8), and the in-post
player's macros. Every state-changing request shows the site's token and
Origin and is limited per person (security.LIMITS, "comment") before it reads
anything through the request's session (security.over).
"""
import base64
from datetime import datetime, timezone

import sqlalchemy as sa
import sqlalchemy.orm  # noqa: F401  (sa.orm.aliased)
from flask import jsonify, render_template, request, url_for

from .accounts import _json_error, _rests
from .models import Comment, Person, Post, as_utc, first_name, new_public_id
from .safety import between, hidden_ids
from .security import current_person, origin_ok, over, site, token_ok

#: Comments a page, newest first; Load more brings the next.
PAGE = 20

#: The most answers one page reads (every answer under its comments, oldest
#: first): a hard limit, as every list here has one.
ANSWERS_MAX = 1000


# ---- what a comment is on ------------------------------------------------------

class On:
    """What comments hang on, as its page shows it to one viewer: a post (its
    row), or a drawing shown outside a post (its skribl's public id, and
    Skribl's description of it, `sk`); and whose it is (`owner`, a person
    row). Built by on_post and on_drawing, which have already decided that
    the viewer may see it."""
    __slots__ = ("owner", "post", "drawing", "sk")

    def __init__(self, owner, post=None, drawing=None, sk=None):
        self.owner, self.post, self.drawing, self.sk = owner, post, drawing, sk

    @property
    def key(self):
        """("p", the post's internal id) or ("s", the drawing's public id):
        what counts() answers by."""
        return ("p", self.post.id) if self.post is not None else ("s", self.drawing)

    def where(self, c=Comment):
        """The comments on it, as SQL."""
        return c.post_id == self.post.id if self.post is not None else c.drawing_id == self.drawing

    def row(self):
        """What a new comment on it says it is on."""
        return {"post_id": self.post.id if self.post is not None else None,
                "drawing_id": self.drawing, "owner_id": self.owner.id}

    @property
    def down(self):
        """Taken down (it, or its author), or a drawing its maker hid from the
        Gallery (link-only, the eye on their own Gallery tab, Nov 14): there
        for its author alone, taking nothing new."""
        if self.owner.taken_down_at is not None:
            return True
        if self.post is not None:
            return self.post.taken_down_at is not None
        return (self.sk or {}).get("visibility") != "public"

    def open_to(self, viewer):
        """Whether `viewer` may say anything on it: it is there for everybody
        (not taken down, nor its author), and no block stands between them
        either way. (Its page is shown to its author when taken down; it
        takes nothing new then.)"""
        return not self.down and not between(viewer, self.owner)

    def page(self):
        """Its own page's address."""
        if self.post is not None:
            return url_for("social.post_page", public_id=self.post.public_id)
        return url_for("social.bloob_page", skribl_id=self.drawing)


def on_post(viewer, public_id=None, post_id=None):
    """A post (by its address, or its internal id) as its page shows it to
    `viewer`, or None: not there, a block either way, or taken down (it, or
    its author) and not theirs."""
    q = sa.select(Post, Person).join(Person, Person.id == Post.person_id)
    q = q.where(Post.id == post_id) if post_id is not None else q.where(Post.public_id == str(public_id or ""))
    found = site().session().execute(q).first()
    if found is None:
        return None
    post, owner = found
    mine = viewer is not None and viewer.id == owner.id
    if between(viewer, owner) or (not mine and (post.taken_down_at is not None or owner.taken_down_at is not None)):
        return None
    return On(owner, post=post)


def on_drawing(viewer, skribl_id):
    """A drawing shown outside a post, as its page shows it to `viewer`
    (posts.bloob), or None: gone, not public (kept private, or link-only or
    taken down and not theirs), not by one of the site's people, a block
    either way, or a post's drawing, whose comments are its post's."""
    from .posts import bloob
    sid = str(skribl_id or "")
    if not sid or site().session().execute(sa.select(Post.id).where(Post.skribl_id == sid)).first() is not None:
        return None
    got = bloob(sid, viewer)
    if got is None:
        return None
    sk, who = got
    return On(who, drawing=sid, sk=sk)


def on_of(c, viewer):
    """What comment row `c` is on, as its page shows it to `viewer`, or None."""
    return on_post(viewer, post_id=c.post_id) if c.post_id is not None else on_drawing(viewer, c.drawing_id)


# ---- what a viewer is shown -------------------------------------------------

def _shown(q, viewer, hidden, c=Comment):
    """The page's rules, on a query of comments: nobody hidden from the
    viewer, and nothing taken down but the viewer's own. A PLACE (gone) is
    nobody's and stands for what hangs under it: it passes, and a list
    shows it only while something it may show hangs there (_fold)."""
    mine = viewer.id if viewer is not None else -1
    ok = sa.or_(c.taken_down_at.is_(None), c.person_id == mine)
    if hidden:
        ok = sa.and_(ok, c.person_id.notin_(sorted(hidden)))
    return q.where(sa.or_(c.gone.isnot(None), ok))


def may_comment(viewer):
    """Whether `viewer` may say anything new: signed in, not taken down."""
    if viewer is None:
        return False
    return site().session().execute(
        sa.select(Person.taken_down_at).where(Person.id == viewer.id)).scalar() is None


def _cursor(c):
    """Where a page of comments ended, naming no internal id."""
    raw = f"{int(as_utc(c.created_at).timestamp() * 1_000_000)}.{c.public_id}"
    return base64.urlsafe_b64encode(raw.encode()).rstrip(b"=").decode()


def _uncursor(text):
    try:
        raw = base64.urlsafe_b64decode((text or "") + "=" * (-len(text or "") % 4)).decode()
        us, key = raw.split(".", 1)
        return datetime.fromtimestamp(int(us) / 1_000_000, tz=timezone.utc), key
    except (ValueError, TypeError, UnicodeDecodeError):
        return None


def answered(c):
    """The id of what reply `c` answers: the reply it was written to, or,
    for one from before replies kept that (or with nothing), its comment."""
    return c.answers_id if c.answers_id is not None else c.parent_id


def gone_words(reply, how):
    """What a place says (the owner's yes, Nov 17): "This reply was deleted",
    "This comment was removed"."""
    return f"This {'reply' if reply else 'comment'} was {'removed' if how == 'removed' else 'deleted'}"


def _item(c, who, muted):
    return {"c": c, "who": who, "sk": None, "quiet": who is not None and who.id in muted, "more": 0,
            "gone": gone_words(c.parent_id is not None, c.gone) if c.gone is not None else None}


def _kept(item):
    """Whether an item is shown: a comment always; a place only while
    something it may show hangs under it."""
    return item["c"].gone is None or bool(item["more"])


def _conversations(root_ids, viewer, hidden):
    """Every reply in the conversations under the top-level comments
    `root_ids` that the page's rules show `viewer` (nobody hidden from them,
    nothing taken down but their own), oldest first, (Comment, Person) rows:
    one read, by the conversation's own index, at most ANSWERS_MAX."""
    if not root_ids:
        return []
    q = (sa.select(Comment, Person).outerjoin(Person, Person.id == Comment.person_id)
         .where(Comment.parent_id.in_(sorted(set(root_ids))))
         .order_by(Comment.created_at, Comment.public_id).limit(ANSWERS_MAX))
    return site().session().execute(_shown(q, viewer, hidden)).all()


def _kids(rows):
    """Each one's direct replies in a conversation's `rows`, oldest first,
    by the internal id of what they answer."""
    kids = {}
    for c, _ in rows:
        kids.setdefault(answered(c), []).append(c)
    return kids


def _fold(tops, rows):
    """ONE LEVEL (the owner, Nov 17): each of `tops` (items) is shown alone,
    nothing nested under it, with "more": how many replies hang under it, at
    any depth, that the viewer may see, from its conversation's `rows` (the
    page's rules already applied). A reply counts only where what it answers
    does: one under a reply the page leaves out (somebody hidden from the
    viewer) is left out, and every reply under it. A PLACE (a deleted reply)
    is walked through and counted as nothing. Since Nov 18 "more" is the
    count beside its talk cloud too."""
    kids = _kids(rows)
    for t in tops:
        n, todo = 0, [t["c"].id]
        while todo:
            for c in kids.get(todo.pop(), ()):
                n += c.gone is None
                todo.append(c.id)
        t["more"] = n


def thread(on, viewer, before=None, limit=PAGE):
    """A page of the comments on `on` (a post or a drawing) for `viewer`:
    (items, next cursor or None). Newest first, each alone (_fold): {"c":
    the comment, "who": its author, "more": how many replies hang under it,
    "quiet": whether the viewer muted its author (it folds to one line)}."""
    from .mutes import muted_ids
    hidden = hidden_ids(viewer)
    muted = muted_ids(viewer)
    sess = site().session()
    q = (sa.select(Comment, Person).outerjoin(Person, Person.id == Comment.person_id)
         .where(on.where(), Comment.parent_id.is_(None))
         .order_by(Comment.created_at.desc(), Comment.public_id.desc()).limit(limit + 1))
    q = _shown(q, viewer, hidden)
    at = _uncursor(before) if before else None
    if at is not None:
        when, key = at
        q = q.where(sa.or_(Comment.created_at < when,
                           sa.and_(Comment.created_at == when, Comment.public_id < key)))
    rows = sess.execute(q).all()
    tops, more = rows[:limit], len(rows) > limit
    items = [_item(c, who, muted) for c, who in tops]
    if items:
        convo = _conversations([i["c"].id for i in items], viewer, hidden)
        _fold(items, convo)
        items = [i for i in items if _kept(i)]
        every = items + _chains(items, convo, muted)
        described(every, viewer)
        named(every)
        hearts(every, viewer)
        shares(every, viewer, on.open_to(viewer))
    return items, (_cursor(tops[-1][0]) if more and tops else None)


def named(items):
    """WHOM EACH ONE'S WORDS MENTION (mentions.py), put on its item as
    "mentions" ({as typed, in small letters: their handle now}, which said()
    makes links of): every comment and answer of a page in one read."""
    from .mentions import links
    got = links(comments=[i["c"].id for i in items])
    for i in items:
        i["mentions"] = got.get(("c", i["c"].id), {})
    return items


def described(items, viewer):
    """Each drawing answer's size, line and plays as Skribl describes them
    for `viewer` (describe_posts, at most 200 a call), put on its item as
    "sk": None where it cannot be had (deleted or withheld since)."""
    from skribl import describe_posts
    ids = [i["c"].skribl_id for i in items if i["c"].skribl_id]
    seen_sk = {}
    for k in range(0, len(ids), 200):
        seen_sk.update(describe_posts(ids[k:k + 200], viewer_id=viewer.public_id if viewer else None))
    for i in items:
        i["sk"] = seen_sk.get(i["c"].skribl_id) if i["c"].skribl_id else None
    return items


def hearts(items, viewer):
    """EACH ONE'S HEART (the comment thread, step 2): how many likes `viewer`
    is shown on it and whether one is theirs (likes.stats, one read for the
    lot), put on its item as "likes". A place has none: nobody's, nothing to
    like."""
    from .likes import stats
    ids = [i["c"].id for i in items if i["c"].gone is None]
    got = stats(viewer, comments=ids) if ids else {}
    for i in items:
        i["likes"] = got.get(("c", i["c"].id), {"n": 0, "mine": False})
    return items


def counts(viewer, posts=(), drawings=()):
    """{("p", a post's internal id) or ("s", a drawing's public id): how many
    comments and replies `viewer` is shown on it}, by the page's own rules,
    one query for each kind asked: nothing by anybody hidden, nothing taken
    down but their own, and no reply under one that is not shown, at any
    depth. A RECURSIVE READ from the comments down (each step by the reply's
    own index), so a reply counts only where every one above it shows, as
    a list counts it (_fold). A PLACE is walked through and counted as
    nothing. A post or a drawing with none is not in it."""
    hidden = hidden_ids(viewer)
    out = {}
    for kind, col, ids in (("p", Comment.post_id, posts), ("s", Comment.drawing_id, drawings)):
        ids = [i for i in dict.fromkeys(ids or ()) if i is not None]
        if not ids:
            continue
        top = _shown(sa.select(Comment.id.label("id"), col.label("on"), Comment.gone.label("gone"))
                     .where(col.in_(ids), Comment.parent_id.is_(None)), viewer, hidden)
        shown = top.cte(f"shown_{kind}", recursive=True)
        rep = sa.orm.aliased(Comment)
        step = _shown(sa.select(rep.id, shown.c.on, rep.gone).join(
            shown, sa.or_(rep.answers_id == shown.c.id,
                          sa.and_(rep.answers_id.is_(None), rep.parent_id == shown.c.id))),
            viewer, hidden, c=rep)
        shown = shown.union_all(step)
        q = sa.select(shown.c.on, sa.func.count()).where(shown.c.gone.is_(None)).group_by(shown.c.on)
        out.update({(kind, k): n for k, n in site().session().execute(q).all()})
    return out


def chain_shown(comments, viewer):
    """The ids among `comments` (Comment rows) whose way up the page's rules
    show `viewer`: every reply each answers, and its comment, by nobody
    hidden from them and not taken down but their own. A reply under one
    hidden from them is hidden with it, at any depth, as a list counts it
    (_fold). One read of the conversations they are in."""
    comments = list(comments)
    roots = sorted({c.parent_id for c in comments if c.parent_id is not None})
    if not roots:
        return {c.id for c in comments}
    hidden = hidden_ids(viewer)
    mine = viewer.id if viewer is not None else -1
    info = {r[0]: r for r in site().session().execute(
        sa.select(Comment.id, Comment.answers_id, Comment.parent_id, Comment.person_id, Comment.taken_down_at)
        .where(sa.or_(Comment.parent_id.in_(roots), Comment.id.in_(roots)))).all()}
    out = set()
    for c in comments:
        up, good, steps = answered(c), True, 0
        while up is not None and steps <= len(info):
            r = info.get(up)
            if r is None or r[3] in hidden or (r[4] is not None and r[3] != mine):
                good = False
                break
            up, steps = (r[1] if r[1] is not None else r[2]), steps + 1
        if good:
            out.add(c.id)
    return out


def landing(rows):
    """WHERE A COMMENT SHOWS, for a link to it (Activity, Your Reports): {its
    internal id: the address of the page whose list shows it, with
    #c-<its public id>}, for comment rows `rows` (Comment, and its post's
    public id or None). A comment shows on its post's or its drawing's page;
    a reply on the page of what it answers, as one of that one's own direct
    replies (one level, everywhere). One read for what they answer."""
    rows = list(rows)
    ups = sorted({answered(c) for c, _ in rows if c.parent_id is not None})
    pid = dict(site().session().execute(
        sa.select(Comment.id, Comment.public_id).where(Comment.id.in_(ups))).all()) if ups else {}
    out = {}
    for c, post_public in rows:
        if c.parent_id is not None and pid.get(answered(c)):
            page = url_for("social.comment_page", public_id=pid[answered(c)])
        elif c.post_id is not None:
            if post_public is None:
                continue              # its post is not there: nowhere to land
            page = url_for("social.post_page", public_id=post_public)
        else:
            page = url_for("social.bloob_page", skribl_id=c.drawing_id)
        out[c.id] = page + "#c-" + c.public_id
    return out


def count_on(on, viewer):
    """How many comments and answers `viewer` is shown on `on`."""
    asked = {"posts": [on.post.id]} if on.post is not None else {"drawings": [on.drawing]}
    return counts(viewer, **asked).get(on.key, 0)


def _one_shown(c, who, viewer, hidden):
    if c.gone is not None:
        return True               # a place is nobody's: it stands for what hangs under it
    return who.id not in hidden and (c.taken_down_at is None or (viewer is not None and viewer.id == c.person_id))


def seen(public_id, viewer, whole=False):
    """One comment as `viewer` meets it on its page: {"c", "who", "on",
    "owner", "top", "chain"} (on: what it is on; top: the comment its
    conversation hangs under, or itself; chain: the way to it, the comment
    and each reply it answers down to the one right above it, as (Comment,
    Person) rows), or None for one not there, on a post or a drawing they
    cannot see, or hidden from them: its author's, or anybody's on the way
    to it. ONE READ for the whole conversation, whatever the depth. With
    `whole`, also "rows": every reply in it the page's rules show `viewer`
    (_conversations), for its own page."""
    sess = site().session()
    found = sess.execute(sa.select(Comment, Person).outerjoin(Person, Person.id == Comment.person_id)
                         .where(Comment.public_id == str(public_id or ""))).first()
    if found is None:
        return None
    c, who = found
    on = on_of(c, viewer)
    if on is None:
        return None
    hidden = hidden_ids(viewer)
    if not _one_shown(c, who, viewer, hidden):
        return None
    root = c.parent_id if c.parent_id is not None else c.id
    convo = {c.id: (c, who)}
    if c.parent_id is not None or whole:
        q = (sa.select(Comment, Person).outerjoin(Person, Person.id == Comment.person_id)
             .where(sa.or_(Comment.id == root, Comment.parent_id == root)))
        convo.update({r[0].id: (r[0], r[1]) for r in sess.execute(q).all()})
    chain, at = [], c
    while at.parent_id is not None:
        up = convo.get(answered(at))
        if up is None or not _one_shown(up[0], up[1], viewer, hidden):
            return None
        chain.insert(0, up)
        at = up[0]
    got = {"c": c, "who": who, "on": on, "owner": on.owner, "top": chain[0][0] if chain else c, "chain": chain}
    if whole:
        got["rows"] = _conversations([root], viewer, hidden)
    return got


# ---- deleting ------------------------------------------------------------------

def _drop_drawings(where):
    """The drawings of the comments `where` names, deleted in Skribl as their
    authors (delete_post): a drawing answer goes with its comment. One already
    gone is gone."""
    from skribl import SkriblNotFound, delete_post
    rows = site().session().execute(
        sa.select(Comment.skribl_id, Person.public_id).join(Person, Person.id == Comment.person_id)
        .where(where, Comment.skribl_id.isnot(None))).all()
    for skribl_id, author in rows:
        try:
            delete_post(skribl_id, author_id=author)
        except SkriblNotFound:
            pass


def _drop(where):
    """Every comment `where` names, their drawings, their mentions and their
    likes (mentions.py, likes.py: said here, every way a comment goes, never
    left to a cascade)."""
    from .bookmarks import drop_comment_bookmarks
    from .likes import drop_comment_likes
    from .mentions import drop_comment_mentions
    from .reposts import drop_comment_reposts
    _drop_drawings(where)
    drop_comment_mentions(where)
    ids = [r[0] for r in site().session().execute(sa.select(Comment.id).where(where))]
    drop_comment_likes(ids)
    # Its reposts and bookmarks go, its quotes let go of it (the comment thread, step 3).
    drop_comment_reposts(ids)
    drop_comment_bookmarks(ids)
    site().session().execute(sa.delete(Comment).where(where).execution_options(synchronize_session=False))


def retire(ids, how="deleted"):
    """COMMENTS THAT GO, KINDLY (the comment thread; the owner's yes, Nov 17,
    to "the place stays"): each of `ids` (internal ids) goes, and its words,
    its drawing (in Skribl, as its author) and its mentions with it. One with
    replies under it that stay keeps its row as a PLACE: nobody's (person_id
    none), its words and its drawing gone, `gone` saying how ("deleted" by
    its author or with their account, "removed" from their post or drawing
    by its author), so those replies stay where they are. A place with
    nothing left under it goes too, and so on up the way. Answers {"places":
    the public ids now places, "dropped": the public ids of places that went
    up the way}. One read of the conversations they are in. Flushes
    nothing: the caller does, with whatever else goes in the same
    transaction."""
    from .mentions import drop_comment_mentions
    ids = set(ids)
    out = {"places": [], "dropped": []}
    if not ids:
        return out
    sess = site().session()
    roots = {r[0] if r[0] is not None else r[1] for r in sess.execute(
        sa.select(Comment.parent_id, Comment.id).where(Comment.id.in_(sorted(ids)))).all()}
    rows = {r[0]: r for r in sess.execute(
        sa.select(Comment.id, Comment.public_id, Comment.answers_id, Comment.parent_id, Comment.gone)
        .where(sa.or_(Comment.id.in_(sorted(roots)), Comment.parent_id.in_(sorted(roots))))).all()}
    ids &= set(rows)
    kids = {}
    for cid, _, ans, par, _ in rows.values():
        if par is not None:
            kids.setdefault(ans if ans is not None else par, []).append(cid)

    def stays_under(cid):
        """Whether a reply stays under `cid`: one not going, and not a place."""
        todo = list(kids.get(cid, ()))
        while todo:
            k = todo.pop()
            if k not in ids and rows[k][4] is None:
                return True
            todo.extend(kids.get(k, ()))
        return False
    places = {i for i in ids if stays_under(i)}
    going = ids - places
    if ids:
        from .bookmarks import drop_comment_bookmarks
        from .likes import drop_comment_likes
        from .reposts import drop_comment_reposts
        _drop_drawings(Comment.id.in_(sorted(ids)))
        drop_comment_mentions(Comment.id.in_(sorted(ids)))
        # Its likes go too, a place's with them: a place is nobody's, nothing to like.
        drop_comment_likes(ids)
        # ...and its reposts and bookmarks; its quotes let go of it, each
        # saying it is gone (the comment thread, step 3).
        drop_comment_reposts(ids)
        drop_comment_bookmarks(ids)
    if places:
        sess.execute(sa.update(Comment).where(Comment.id.in_(sorted(places)))
                     .values(words="", skribl_id=None, person_id=None, gone=how, taken_down_at=None)
                     .execution_options(synchronize_session=False))
    if going:
        sess.execute(sa.delete(Comment).where(Comment.id.in_(sorted(going))).execution_options(synchronize_session=False))
    # UP THE WAY: a place with nothing left under it goes too.
    left = {k: r for k, r in rows.items() if k not in going}
    while True:
        under = set()
        for cid, _, ans, par, _ in left.values():
            if par is not None:
                under.add(ans if ans is not None else par)
        empty = [k for k, r in left.items() if (r[4] is not None or k in places) and k not in under]
        if not empty:
            break
        sess.execute(sa.delete(Comment).where(Comment.id.in_(sorted(empty))).execution_options(synchronize_session=False))
        for k in empty:
            if k not in places:
                out["dropped"].append(left[k][1])
            left.pop(k)
    out["places"] = sorted(rows[k][1] for k in places if k in left)
    return out


def drop_post_comments(post_id):
    """Every comment and answer on a post, and their drawings
    (posts.drop_post, before the post)."""
    _drop(Comment.post_id == post_id)


def drop_drawing_comments(skribl_id):
    """Every comment and answer on a drawing shown outside a post, and their
    drawings (posts.bloob_delete, once the drawing is gone)."""
    _drop(Comment.drawing_id == str(skribl_id))


def move_drawing_comments(skribl_id, post_id):
    """ONE DRAWING, ONE CONVERSATION (docs/SOCIAL-SITE.md section 17; the
    owner's "Yes", Nov 14): every comment and answer on a drawing shown
    outside a post, onto the post it is now in (posts.post_new, an older
    drawing posted through the composer's Yours), in the same transaction as
    the post's row. One UPDATE: each row keeps its words, its drawing, its
    author, its time, its answers and whom it answers, and only says the post
    instead of the drawing (both columns in one statement, so the database's
    "exactly one" holds at every step). Its owner is the same person. What
    Activity said of them it says of the post now, at their own times, so
    nothing is new again and nobody is told twice. Flushes nothing."""
    site().session().execute(
        sa.update(Comment).where(Comment.drawing_id == str(skribl_id))
        .values(post_id=post_id, drawing_id=None).execution_options(synchronize_session=False))


def drop_owner_comments(person_id):
    """Every comment and answer on what a person owned, their posts and
    their drawings (accounts.delete_person, before the person): a drawing of
    theirs stays in Skribl, but its page is gone with them."""
    _drop(Comment.owner_id == person_id)


def drop_person_comments(person_id):
    """Everything a person said (accounts.delete_person, before the person),
    kindly (retire): one with somebody else's replies under it keeps its
    place, nobody's, and theirs stay."""
    ids = [r[0] for r in site().session().execute(sa.select(Comment.id).where(Comment.person_id == person_id))]
    retire(ids, "deleted")


# ---- the routes ------------------------------------------------------------------

def replies_of(got, viewer):
    """A COMMENT'S OWN REPLIES, for its own page (seen(..., whole=True)):
    (items, how many). Its direct replies stand where a post's comments do,
    oldest first, each with its count and its conversation followed down
    under it (_chains: Bluesky's way); how many is every reply under it, at
    any depth, that the viewer may see."""
    from .mutes import muted_ids
    muted = muted_ids(viewer)
    rows = got["rows"]
    tops = [_item(c, who, muted) for c, who in rows if answered(c) == got["c"].id]
    _fold(tops, rows)
    tops = [t for t in tops if _kept(t)]
    every = tops + _chains(tops, rows, muted)
    described(every, viewer)
    named(every)
    hearts(every, viewer)
    shares(every, viewer, way_open(got, viewer) and got["c"].taken_down_at is None)
    # A place counts as nothing (_fold's rule).
    return tops, len([t for t in tops if t["c"].gone is None]) + sum(t["more"] for t in tops)


#: How far a conversation is followed down under a comment, before "Read N
#: more replies" (Bluesky's default, its linear view: LINEAR_VIEW_BELOW).
CHAIN_MAX = 10


def _chains(items, rows, muted):
    """BLUESKY'S WAY, OUR LOOK (the owner's yes, Nov 18, after reading
    Bluesky's own thread code): under each of `items` (a list's comments or
    a comment's replies, already folded), its conversation followed down in
    the same column, never stepping in: its first reply (oldest, so it reads
    as a conversation; Bluesky picks its "top"), then the first reply to
    that, and so on, CHAIN_MAX deep ("chain"). A place in the way is walked
    through while something hangs under it (_kept). Where the last one
    there still has replies under it, "Read N more replies" opens its own
    page ("chain_more": that one, with its "more"). Its other replies show
    only in their count, as on Bluesky. Answers every item it made, for
    reading their cards at once."""
    who = {c.id: p for c, p in rows}
    kids = _kids(rows)
    made = []
    for it in items:
        chain, cur = [], it
        while len(chain) < CHAIN_MAX:
            nxt = None
            for c in kids.get(cur["c"].id, ()):
                cand = _item(c, who.get(c.id), muted)
                _fold([cand], rows)
                if _kept(cand):
                    nxt = cand
                    break
            if nxt is None:
                break
            chain.append(nxt)
            cur = nxt
        last = chain[-1] if chain else it
        it["chain"] = chain
        it["chain_more"] = last if len(chain) == CHAIN_MAX and last["more"] else None
        made += chain
    return made


def tally(way, viewer):
    """HOW MANY UNDER EACH, ALL THE WAY UP (Nov 18): {public id:
    every reply under it, at any depth, that `viewer` may see} for each of
    `way` (Comments of one conversation, its comment first), read once a
    reply has come or gone, so a list shows every count it holds rightly.
    One read for the conversation; one not there any more counts nothing."""
    if not way:
        return {}
    root = way[0].parent_id if way[0].parent_id is not None else way[0].id
    rows = _conversations([root], viewer, hidden_ids(viewer))
    items = [{"c": c} for c in way]
    _fold(items, rows)
    return {i["c"].public_id: i["more"] for i in items}


def section(on, viewer, skribl_blueprint="skribl", focus=None):
    """What a page needs for its comments, a post's or a drawing's: the first
    page, the cursor after it, how many there are, whether the viewer may add
    one, and the addresses its script uses (the Pad's and Flip's in compose
    mode, for a drawing answer: no gallery tick). On a comment's own page
    (`focus`: seen(..., whole=True)) its replies stand where the comments
    do (replies_of), all of them (no Load more), and the box replies to it."""
    if focus is None:
        items, nxt = thread(on, viewer)
        count = count_on(on, viewer)
    else:
        (items, count), nxt = replies_of(focus, viewer), None
    if on.post is not None:
        new = url_for("social.comment_new", public_id=on.post.public_id)
        more = url_for("social.comments_more", public_id=on.post.public_id)
    else:
        new = url_for("social.bloob_comment_new", skribl_id=on.drawing)
        more = url_for("social.bloob_comments_more", skribl_id=on.drawing)
    return {"cards": items, "next": nxt,
            "count": count,
            # A place takes no reply: nothing is there to reply to.
            "can": may_comment(viewer) and on.open_to(viewer) and (focus is None or focus["c"].gone is None),
            "post_mine": viewer is not None and viewer.id == on.owner.id,
            # A comment's own page: what its box replies to, and whose it is.
            "subject": focus["c"].public_id if focus is not None else None,
            # A place's own page takes no reply from anybody: no box, no icon.
            "closed": focus is not None and focus["c"].gone is not None,
            # Whom the box says something to ("Say something to Mira", or on
            # a comment's own page "Reply to Eli"), and the signed-out sheet's
            # "you can reply to Mira": the first name, as the heart's sheet
            # says it.
            "first": first_name((focus["who"] if focus is not None else on.owner).display_name)
            if focus is None or focus["who"] is not None else "",
            "new": new, "more": more,
            "drop": url_for("social.comment_delete", public_id="__ID__"),
            "pad": url_for(skribl_blueprint + ".skribl_editor", compose=1),
            "flip": url_for(skribl_blueprint + ".skribl_flip", compose=1),
            # Signing in comes back to the page with the box open (#say:
            # comments.js), and nothing is posted until Post.
            "signin": url_for("social.signin", next=(
                url_for("social.comment_page", public_id=focus["c"].public_id) if focus is not None
                else on.page()) + "#say")}


def still(sid, sk, skribl_blueprint="skribl", height=48):
    """A DRAWING'S SMALL STILL PICTURE, IN ITS OWN SHAPE, on the way to a
    comment (its own page): its poster (the share card) behind a box
    `height` px tall, showing the drawing's own area, as Activity cuts a
    square from it (activity._pic: lib/sharecard.js drawingRect's sums and
    rounding, the card 1200 x 630, the drawing's area 1092 x 492 above an
    84px foot, the plate's hairline 3px in). None when Skribl does not
    describe it (deleted or withheld since)."""
    import math
    if not sid or not sk:
        return None
    w, h = int(sk.get("canvas_w") or 0), int(sk.get("canvas_h") or 0)
    if not (0 < w <= 8192 and 0 < h <= 8192):
        w, h = 1092, 492
    sc = min(1092 / w, 492 / h)
    dw, dh = math.floor(w * sc + 0.5), math.floor(h * sc + 0.5)
    if min(dw, dh) < 13:
        dw, dh = 1092, 492
    x, y = math.floor((1200 - dw) / 2 + 0.5) + 3, math.floor((546 - dh) / 2 + 0.5) + 3
    cw, ch = dw - 6, dh - 6
    k = height / ch
    return {"src": url_for(skribl_blueprint + ".skribl_poster", public_id=sid), "w": max(1, round(cw * k)),
            "h": height, "size": f"{1200 * k:.2f}px auto", "at": f"{-x * k:.2f}px {-y * k:.2f}px"}


def the_way(got, viewer, skribl_blueprint="skribl"):
    """THE WAY TO A COMMENT, above it on its own page, small: what it is on
    (the post, or the drawing), then the comment and each reply it answers,
    down to the one right above it. Each {"who", "when", "words", "pic" (a
    drawing's still: still()), "href" (its own page)}."""
    from skribl import describe_posts
    on = got["on"]
    if on.post is not None:
        first = {"who": on.owner, "when": on.post.created_at, "words": on.post.words, "sid": on.post.skribl_id,
                 "href": on.page()}
    else:
        sk = on.sk or {}
        first = {"who": on.owner, "when": as_utc(datetime.fromisoformat(sk["created_at"])) if sk.get("created_at")
                 else None, "words": sk.get("title") or "", "sid": on.drawing, "href": on.page()}
    way = [first] + [{"who": who, "when": c.created_at if c.gone is None else None, "words": c.words, "sid": c.skribl_id,
                      "gone": gone_words(c.parent_id is not None, c.gone) if c.gone is not None else None,
                      "href": url_for("social.comment_page", public_id=c.public_id)} for c, who in got["chain"]]
    sids = [w["sid"] for w in way if w["sid"]]
    sk = describe_posts(sids, viewer_id=viewer.public_id if viewer else None) if sids else {}
    for w in way:
        w["pic"] = still(w["sid"], sk.get(w["sid"]), skribl_blueprint) if w["sid"] else None
    return way


def way_open(got, viewer):
    """Whether what a comment (comments.seen's `got`) is on is open to
    `viewer` and nothing on the way to it is taken down: where it, and its
    replies, can be reposted, quoted and kept (reposts.comment_open)."""
    return got["on"].open_to(viewer) and not any(c.taken_down_at is not None for c, _ in got["chain"])


def shares(items, viewer, open_=True):
    """EACH ONE'S REPOST AND BOOKMARK (the comment thread, step 3; the owner's
    yes to "A Comment Shared", Nov 17): how many reposts and quotes `viewer`
    is shown on it and whether a repost is theirs (reposts.stats), whether it
    is their bookmark (bookmarks.marked, theirs alone, never a count), and
    whether it can be shared at all ("shareable": as reposts.comment_open
    asks, where `open_` says what it is on is open to them and nothing on the
    way to it is taken down; never a place, nor one taken down), put on its
    item. One read of each for the lot."""
    from .bookmarks import marked
    from .reposts import stats
    ids = [i["c"].id for i in items if i["c"].gone is None]
    got = stats(viewer, comments=ids) if ids else {}
    kept = marked(viewer, comments=ids) if ids else set()
    for i in items:
        c = i["c"]
        i["reposts"] = got.get(("c", c.id), {"n": 0, "mine": False})
        i["marked"] = ("c", c.id) in kept
        i["shareable"] = bool(open_) and c.gone is None and c.taken_down_at is None
    return items


def world_cards(entries, viewer):
    """A COMMENT OR A REPLY OUT IN THE WORLD (the comment thread, step 3; the
    owner's yes to A in "A Comment Shared", Nov 17), reposted on Home's
    Following and a person's Posts tab, or kept in their Bookmarks: a card
    for each of `entries` ("comment", "who", and a repost's "by"), in their
    order, or None for one this viewer is not shown. Each as its own page
    shows it to them (seen: one hidden from them, or anything on the way to
    it, has none; never a place): THE WAY TO IT above (the_way: what it is on,
    then each comment it answers, so nobody's words travel without what they
    are about), it (its face, name, @handle and when; its words; its drawing
    as a post's), and its row: how many replies (every one under it they may
    see, at any depth), its repost and how many, its heart and how many, its
    ⋯ (a tap on its ground opens its page). A few reads a card; a page has few."""
    from .accounts import profile_url
    from .mutes import muted_ids
    from .reports import site_bp
    muted = muted_ids(viewer)
    gots = []
    for e in entries:
        got = seen(e["comment"].public_id, viewer, whole=True)
        gots.append(got if got is not None and got["c"].gone is None else None)
    items = [_item(got["c"], got["who"], muted) for got in gots if got is not None]
    if not items:
        return [None for _ in entries]
    for it, got in zip(items, [g_ for g_ in gots if g_ is not None]):
        _fold([it], got["rows"])
    described(items, viewer)
    named(items)
    hearts(items, viewer)
    shares(items, viewer)
    made = iter(items)
    out = []
    for e, got in zip(entries, gots):
        if got is None:
            out.append(None)
            continue
        it = next(made)
        c, who = it["c"], it["who"]
        down = c.taken_down_at is not None or who.taken_down_at is not None
        it["shareable"] = it["shareable"] and not down and way_open(got, viewer)
        by = e.get("by")
        out.append({
            "kind": "c", "c": c, "who": who, "it": it, "down": down,
            "way": the_way(got, viewer, site_bp()),
            "url": url_for("social.comment_page", public_id=c.public_id),
            "delete": url_for("social.comment_delete", public_id=c.public_id),
            "mine": viewer is not None and viewer.id == c.person_id,
            "muted": who.id in muted,
            "profile": profile_url(who.handle),
            # Repost, Quote and Bookmark where it can be shared (as on a post:
            # what is open to everybody); its heart wherever it is not taken
            # down. The row's names are a post's card's, so its macros serve.
            "markable": it["shareable"], "marked": it["marked"],
            "reposts": it["reposts"],
            "repost": url_for("social.repost_comment", public_id=c.public_id),
            "quoted_url": url_for("social.quoted_comment", public_id=c.public_id),
            "replies": it["more"],
            "by": by, "by_me": by is not None and viewer is not None and by.id == viewer.id})
    return out


def _cards(items, viewer, can, post_mine):
    return render_template("social/_comment_cards.html", items=items, can=can, post_mine=post_mine, me=viewer)


def register(bp, skribl_blueprint="skribl"):
    """Add the comments' routes to the site's blueprint."""

    @bp.get("/c/<public_id>")
    @_rests()
    def comment_page(public_id):
        """A COMMENT OR A REPLY ON A PAGE OF ITS OWN (the comment thread, step
        1; the owner's yes, Nov 17): every one has one, so any of them can be
        linked and shared, and a tap on it opens it, in a list and in a
        conversation followed down under one. The way to it above, small
        (what it is on, then each one
        it answers); it, as big as a post, its row and its full time; its
        direct replies under it, each alone (one level, everywhere). One
        hidden from the viewer, or anything on the way to it, is as gone as
        one not there."""
        from .accounts import _page
        from .mutes import muted_ids
        from .security import csrf_token
        me = current_person()
        got = seen(public_id, me, whole=True)
        if got is None:
            return _page("post_gone.html", 404, here="post")
        it = _item(got["c"], got["who"], muted_ids(me))
        shares(hearts(named(described([it], me)), me), me, way_open(got, me))
        cm = section(got["on"], me, skribl_blueprint, focus=got)
        return _page("comment.html", here="post", it=it, way=the_way(got, me, skribl_blueprint), cm=cm,
                     on_page=got["on"].page(), token=csrf_token(), on_post=got["on"].post is not None,
                     signin_here=url_for("social.signin", next=url_for("social.comment_page", public_id=public_id)))

    def new_comment(find):
        """A comment, or an answer under one, on what `find(me)` says the
        request is about (an On it may comment on, or None: gone)."""
        if not origin_ok() or not token_ok():
            return _json_error("stale", 403)
        me = current_person()
        if me is None:
            return _json_error("signed_out", 401)
        if over("comment", "person|" + me.public_id):
            return _json_error("limited", 429)
        if not may_comment(me):
            # Taken down (Your Reports): nothing new is shared from the account.
            return _json_error("taken_down", 403)
        body = request.get_json(silent=True)
        if not isinstance(body, dict):
            return _json_error("empty", 400)
        from .posts import check_words, title_from
        words, problem = check_words(body.get("words"))
        if problem:
            return _json_error(problem, 400)
        payload = body.get("payload")
        if payload is not None and not isinstance(payload, dict):
            return _json_error("empty", 400)
        if not words and payload is None:
            # A comment says something, or draws it.
            return _json_error("empty", 400)
        on = find(me)
        if on is None or not on.open_to(me):
            # Not there, taken down, or a block either way: gone, as its page is.
            return _json_error("gone", 404)
        parent = answers = to = None
        if body.get("answer_to") is not None:
            got = seen(body.get("answer_to"), me)
            if (got is None or got["on"].key != on.key or got["c"].taken_down_at is not None
                    or got["c"].gone is not None or any(c.taken_down_at is not None for c, _ in got["chain"])):
                # Not there, hidden, taken down, or a place (nothing to reply to).
                return _json_error("gone", 404)
            # A REPLY KEEPS THE REPLY IT ANSWERS (the comment thread, step 1):
            # answers_id, at any depth; parent_id the comment its conversation
            # hangs under; and whom it answers (notifications: Activity tells them).
            parent, answers, to = got["top"], got["c"], got["c"].person_id
        made = None
        if payload is not None:
            from skribl import SkriblRejected, SkriblUnavailable, create_post
            drawing = dict(payload)
            # A DRAWING ANSWER IS NOBODY'S GALLERY POST, whatever the payload
            # says: unlisted (its link works, it is listed nowhere), titled by
            # the comment's first words, no caption.
            drawing["visibility"] = "unlisted"
            drawing["title"] = title_from(words)
            drawing.pop("caption", None)
            try:
                made = create_post(drawing, author_id=me.public_id)
            except SkriblRejected as exc:
                return _json_error("rejected", exc.status if 400 <= exc.status < 500 else 400,
                                   message=exc.message)
            except SkriblUnavailable:
                return _json_error("busy", 503)
        sess = site().session()
        row = Comment(public_id=new_public_id(8), person_id=me.id,
                      parent_id=parent.id if parent is not None else None,
                      answers_id=answers.id if answers is not None else None, to_person_id=to, words=words or "",
                      skribl_id=made.public_id if made is not None else None, **on.row())
        sess.add(row)
        sess.flush()
        # MENTIONS (mentions.py): the people its words name, in the same
        # transaction as the comment.
        from .mentions import write_comment
        write_comment(row)
        sess.flush()
        # A NUDGE, once the request commits (push.py): to whom it answers,
        # and to whose post or drawing it is on, where Activity has a row.
        from .push import note
        note(on.owner.id, me.id, "replies")
        note(to, me.id, "replies")
        who = sess.get(Person, me.id)
        # New, theirs, on what they may say something on: nothing on it yet,
        # and it can be shared (shares(): no repost, no bookmark).
        html = _cards(named(described([{"c": row, "who": who, "sk": None, "more": 0,
                                         "likes": {"n": 0, "mine": False}, "reposts": {"n": 0, "mine": False},
                                         "marked": False, "shareable": True}], me)), me, True,
                      me.id == on.owner.id)
        # "under": the comment or the reply it answers: on its own page the
        # reply lands last in its list; anywhere else it continues that one's
        # conversation where it is followed down to it (Bluesky's way), or
        # its count takes it. "page": that one's own page, where the reply
        # shows. "counts": every reply under it and under each one above it,
        # now, for the counts beside their talk clouds.
        return jsonify({"ok": True, "comment": row.public_id,
                        "under": answers.public_id if answers is not None else None,
                        "page": url_for("social.comment_page", public_id=answers.public_id) if answers is not None
                        else None,
                        "counts": tally([c for c, _ in got["chain"]] + [got["c"]], me) if answers is not None else {},
                        "html": html, "count": count_on(on, me)})

    def more_comments(on, me):
        """The next page of the comments on `on`, as their cards (Load more)."""
        if on is None:
            return _json_error("gone", 404)
        items, nxt = thread(on, me, before=request.args.get("before"))
        can = may_comment(me) and on.open_to(me)
        return jsonify({"html": _cards(items, me, can, me is not None and me.id == on.owner.id), "next": nxt})

    @bp.post("/p/<public_id>/comments")
    @_rests(json_answer=True)
    def comment_new(public_id):
        """A comment on a post, or an answer under one of its comments."""
        return new_comment(lambda me: on_post(me, public_id=public_id))

    @bp.get("/p/<public_id>/comments")
    @_rests(json_answer=True)
    def comments_more(public_id):
        """The next page of a post's comments, as their cards (Load more)."""
        me = current_person()
        return more_comments(on_post(me, public_id=public_id), me)

    @bp.post("/b/<skribl_id>/comments")
    @_rests(json_answer=True)
    def bloob_comment_new(skribl_id):
        """A comment on a drawing shown outside a post, or an answer under one
        of its comments. Under the drawing's lock (posts.drawing_lock), so a
        comment never lands on a drawing as it moves into a post."""
        from .posts import drawing_lock

        def find(me):
            drawing_lock(skribl_id)
            return on_drawing(me, skribl_id)
        return new_comment(find)

    @bp.get("/b/<skribl_id>/comments")
    @_rests(json_answer=True)
    def bloob_comments_more(skribl_id):
        """The next page of a drawing's comments, as their cards (Load more)."""
        me = current_person()
        return more_comments(on_drawing(me, skribl_id), me)

    @bp.post("/c/<public_id>/delete")
    @_rests(json_answer=True)
    def comment_delete(public_id):
        """Your own comment, gone; or, on your own post or drawing, anybody's,
        removed from it. Kindly (retire): one with replies under it keeps its
        place, and theirs stay. Answers whether it stayed as a place, its
        words then, the places that went with it up the way, and how many
        each one still there on the way to it has under it now."""
        if not origin_ok() or not token_ok():
            return _json_error("stale", 403)
        me = current_person()
        if me is None:
            return _json_error("signed_out", 401)
        sess = site().session()
        c = sess.execute(sa.select(Comment).where(Comment.public_id == str(public_id or ""))).scalar_one_or_none()
        if c is None or c.gone is not None or me.id not in (c.person_id, c.owner_id):
            # Somebody else's, on somebody else's: as gone as one not there.
            return _json_error("gone", 404)
        asked = {"posts": [c.post_id]} if c.post_id is not None else {"drawings": [c.drawing_id]}
        key = ("p", c.post_id) if c.post_id is not None else ("s", c.drawing_id)
        how = "deleted" if me.id == c.person_id else "removed"
        reply = c.parent_id is not None
        # The way to it, read before it goes: each one above it shows how
        # many are under it, and one fewer counts now.
        pre = seen(c.public_id, me)
        way = [x for x, _ in pre["chain"]] if pre is not None else []
        went = retire([c.id], how)
        sess.flush()
        return jsonify({"ok": True, "count": counts(me, **asked).get(key, 0),
                        "place": c.public_id in went["places"], "dropped": went["dropped"],
                        "counts": tally(way, me), "words": gone_words(reply, how)})

    return bp
