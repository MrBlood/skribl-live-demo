"""Comments (phase 2, its first piece; docs/SOCIAL-SITE.md "Built: phase 2,
comments"), from the comments mock and the owner's "all yes on both" (Nov 12).

    /p/<id>/comments    POST: a comment on a post, or an answer to one (JSON:
                        {words, payload, answer_to}); its card comes back, to
                        go in place. GET: the next page of the post's
                        comments, for Load more ({html, next}).
    /c/<id>/delete      your own comment, gone, its answers with it; or, on
                        your own post, anybody's, removed from it (JSON).

ON A POST'S OWN PAGE (post.html, _comments.html): "Comments" and how many,
the box on top (your face, the words, Post), then the comments newest first,
each with its answers under it, oldest first. ANSWERS ARE ONE LEVEL DEEP:
answering an answer puts the new one under the same comment (parent_id is
always a top-level comment's), and Answer brings the box to that comment
(comments.js). Each comment's ⋯: on your own, Delete comment; on somebody
else's on your own post, Remove from my post and Report comment; on anybody
else's, Report comment.

WHO MAY COMMENT: somebody signed in who is not taken down, with no block
either way with the post's author; an answer also with none with the author
of the comment it answers. The route refuses anybody else kindly, and the
box is not shown to them. Signed out, the comments are readable, and "Sign
in to answer" stands where the box would be.

WHAT IS SHOWN, AND COUNTED: nothing by anybody hidden from the viewer (a
block either way, or taken down: safety.hidden_ids), nor the answers under a
comment that is; a comment taken down only to its author, with the note.
The same rules count (counts(): Home's card, and the section's heading), so
a number never promises a comment the page will not show.

DELETING IS REAL, AND SAID IN CODE: a comment goes with its answers
(drop_comments), a post with its comments (posts.drop_post), an account with
its comments and every answer under them (accounts.delete_person). The
schema's ON DELETE CASCADEs are a net under that, never the way: SQLite
enforces them only where Skribl's pragma hook is on.

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
from .models import Comment, Person, Post, as_utc, new_public_id
from .safety import between, hidden_ids
from .security import current_person, origin_ok, over, site, token_ok

#: Comments a page, newest first; Load more brings the next.
PAGE = 20

#: The most answers one page reads (every answer under its comments, oldest
#: first): a hard limit, as every list here has one.
ANSWERS_MAX = 1000


# ---- what a viewer is shown -------------------------------------------------

def _shown(q, viewer, hidden, c=Comment):
    """The page's rules, on a query of comments: nobody hidden from the
    viewer, and nothing taken down but the viewer's own."""
    mine = viewer.id if viewer is not None else -1
    if hidden:
        q = q.where(c.person_id.notin_(sorted(hidden)))
    return q.where(sa.or_(c.taken_down_at.is_(None), c.person_id == mine))


def post_open(post, owner, viewer):
    """Whether `viewer` may say anything on this post: it is there for
    everybody (not taken down, nor its author), and no block stands between
    them either way. (Its page is shown to its author when taken down; it
    takes nothing new then.)"""
    return (post.taken_down_at is None and owner.taken_down_at is None
            and not between(viewer, owner))


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


def thread(post, viewer, before=None, limit=PAGE):
    """A page of a post's comments for `viewer`: (items, next cursor or None).
    Newest first; each item {"c": the comment, "who": its author, "answers":
    its answers as items, oldest first}."""
    hidden = hidden_ids(viewer)
    sess = site().session()
    q = (sa.select(Comment, Person).join(Person, Person.id == Comment.person_id)
         .where(Comment.post_id == post.id, Comment.parent_id.is_(None))
         .order_by(Comment.created_at.desc(), Comment.public_id.desc()).limit(limit + 1))
    q = _shown(q, viewer, hidden)
    at = _uncursor(before) if before else None
    if at is not None:
        when, key = at
        q = q.where(sa.or_(Comment.created_at < when,
                           sa.and_(Comment.created_at == when, Comment.public_id < key)))
    rows = sess.execute(q).all()
    tops, more = rows[:limit], len(rows) > limit
    items = [{"c": c, "who": who, "answers": [], "sk": None} for c, who in tops]
    if items:
        by = {i["c"].id: i for i in items}
        aq = (sa.select(Comment, Person).join(Person, Person.id == Comment.person_id)
              .where(Comment.parent_id.in_(sorted(by)))
              .order_by(Comment.created_at, Comment.public_id).limit(ANSWERS_MAX))
        for c, who in sess.execute(_shown(aq, viewer, hidden)).all():
            by[c.parent_id]["answers"].append({"c": c, "who": who, "answers": [], "sk": None})
        described(items + [a for i in items for a in i["answers"]], viewer)
    return items, (_cursor(tops[-1][0]) if more and tops else None)


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


def counts(post_ids, viewer):
    """{post id: how many comments and answers `viewer` is shown on it}, for
    posts' internal ids, by the page's own rules, in one query: nothing by
    anybody hidden, nothing taken down but their own, no answer under a
    comment that is not shown."""
    ids = [i for i in dict.fromkeys(post_ids or ()) if i is not None]
    if not ids:
        return {}
    hidden = hidden_ids(viewer)
    mine = viewer.id if viewer is not None else -1
    par = sa.orm.aliased(Comment)
    q = (sa.select(Comment.post_id, sa.func.count()).select_from(Comment)
         .outerjoin(par, par.id == Comment.parent_id)
         .where(Comment.post_id.in_(ids)).group_by(Comment.post_id))
    q = _shown(q, viewer, hidden)
    under = sa.or_(par.taken_down_at.is_(None), par.person_id == mine)
    if hidden:
        under = sa.and_(under, par.person_id.notin_(sorted(hidden)))
    q = q.where(sa.or_(Comment.parent_id.is_(None), under))
    return {pid: n for pid, n in site().session().execute(q).all()}


def _one_shown(c, who, viewer, hidden):
    return who.id not in hidden and (c.taken_down_at is None or (viewer is not None and viewer.id == c.person_id))


def seen(public_id, viewer):
    """One comment as `viewer` meets it on its post's page: {"c", "who",
    "post", "owner", "top"} (top: the comment it sits under, or itself), or
    None for one not there, on a post they cannot see, or hidden from them
    (its author's, or the comment it sits under's)."""
    sess = site().session()
    owner = sa.orm.aliased(Person)
    found = sess.execute(sa.select(Comment, Person, Post, owner)
                         .join(Person, Person.id == Comment.person_id)
                         .join(Post, Post.id == Comment.post_id)
                         .join(owner, owner.id == Post.person_id)
                         .where(Comment.public_id == str(public_id or ""))).first()
    if found is None:
        return None
    c, who, post, own = found
    mine = viewer is not None and viewer.id == own.id
    if between(viewer, own) or (not mine and (post.taken_down_at is not None or own.taken_down_at is not None)):
        return None
    hidden = hidden_ids(viewer)
    if not _one_shown(c, who, viewer, hidden):
        return None
    top = c
    if c.parent_id is not None:
        par = sess.execute(sa.select(Comment, Person).join(Person, Person.id == Comment.person_id)
                           .where(Comment.id == c.parent_id)).first()
        if par is None or not _one_shown(par[0], par[1], viewer, hidden):
            return None
        top = par[0]
    return {"c": c, "who": who, "post": post, "owner": own, "top": top}


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


def drop_comments(ids):
    """Comments, by their internal ids, gone with every answer under them,
    and their drawings. Flushes nothing: the caller does, with whatever else
    goes in the same transaction."""
    ids = sorted(set(ids))
    if not ids:
        return
    which = sa.or_(Comment.id.in_(ids), Comment.parent_id.in_(ids))
    _drop_drawings(which)
    site().session().execute(sa.delete(Comment).where(which).execution_options(synchronize_session=False))


def drop_post_comments(post_id):
    """Every comment and answer on a post, and their drawings
    (posts.drop_post, before the post)."""
    _drop_drawings(Comment.post_id == post_id)
    site().session().execute(sa.delete(Comment).where(Comment.post_id == post_id)
                             .execution_options(synchronize_session=False))


def drop_person_comments(person_id):
    """Everything a person said, and every answer under their comments
    (accounts.delete_person, before the person)."""
    ids = [r[0] for r in site().session().execute(sa.select(Comment.id).where(Comment.person_id == person_id))]
    drop_comments(ids)


# ---- the routes ------------------------------------------------------------------

def section(post, owner, viewer, skribl_blueprint="skribl"):
    """What a post's page needs for its comments: the first page, the
    cursor after it, how many there are, whether the viewer may add one, and
    the addresses its script uses (the Pad's and Flip's in compose mode, for
    a drawing answer: no gallery tick)."""
    items, nxt = thread(post, viewer)
    return {"cards": items, "next": nxt,
            "count": counts([post.id], viewer).get(post.id, 0),
            "can": may_comment(viewer) and post_open(post, owner, viewer),
            "post_mine": viewer is not None and viewer.id == owner.id,
            "new": url_for("social.comment_new", public_id=post.public_id),
            "more": url_for("social.comments_more", public_id=post.public_id),
            "drop": url_for("social.comment_delete", public_id="__ID__"),
            "pad": url_for(skribl_blueprint + ".skribl_editor", compose=1),
            "flip": url_for(skribl_blueprint + ".skribl_flip", compose=1),
            "signin": url_for("social.signin", next=url_for("social.post_page", public_id=post.public_id))}


def _cards(items, viewer, can, post_mine):
    return render_template("social/_comment_cards.html", items=items, can=can, post_mine=post_mine, me=viewer)


def register(bp):
    """Add the comments' routes to the site's blueprint."""

    def _post(public_id):
        return site().session().execute(
            sa.select(Post, Person).join(Person, Person.id == Post.person_id)
            .where(Post.public_id == str(public_id or ""))).first()

    @bp.post("/p/<public_id>/comments")
    @_rests(json_answer=True)
    def comment_new(public_id):
        """A comment on a post, or an answer under one of its comments."""
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
        found = _post(public_id)
        if found is None or not post_open(found[0], found[1], me):
            # Not there, taken down, or a block either way: gone, as its page is.
            return _json_error("gone", 404)
        post, owner = found
        parent = None
        if body.get("answer_to") is not None:
            got = seen(body.get("answer_to"), me)
            if (got is None or got["post"].id != post.id or got["c"].taken_down_at is not None
                    or got["top"].taken_down_at is not None):
                return _json_error("gone", 404)
            # ONE LEVEL DEEP: an answer to an answer sits under the same comment.
            parent = got["top"]
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
        row = Comment(public_id=new_public_id(8), post_id=post.id, person_id=me.id,
                      parent_id=parent.id if parent is not None else None, words=words or "",
                      skribl_id=made.public_id if made is not None else None)
        sess.add(row)
        sess.flush()
        who = sess.get(Person, me.id)
        html = _cards(described([{"c": row, "who": who, "answers": [], "sk": None}], me), me, True,
                      me.id == owner.id)
        return jsonify({"ok": True, "comment": row.public_id,
                        "under": parent.public_id if parent is not None else None,
                        "html": html, "count": counts([post.id], me).get(post.id, 0)})

    @bp.get("/p/<public_id>/comments")
    @_rests(json_answer=True)
    def comments_more(public_id):
        """The next page of a post's comments, as their cards (Load more)."""
        me = current_person()
        found = _post(public_id)
        mine = found is not None and me is not None and found[1].id == me.id
        if (found is None or between(me, found[1])
                or (not mine and (found[0].taken_down_at is not None or found[1].taken_down_at is not None))):
            return _json_error("gone", 404)
        post, owner = found
        items, nxt = thread(post, me, before=request.args.get("before"))
        can = may_comment(me) and post_open(post, owner, me)
        return jsonify({"html": _cards(items, me, can, mine), "next": nxt})

    @bp.post("/c/<public_id>/delete")
    @_rests(json_answer=True)
    def comment_delete(public_id):
        """Your own comment, gone with its answers; or, on your own post,
        anybody's, removed from it."""
        if not origin_ok() or not token_ok():
            return _json_error("stale", 403)
        me = current_person()
        if me is None:
            return _json_error("signed_out", 401)
        sess = site().session()
        found = sess.execute(sa.select(Comment, Post).join(Post, Post.id == Comment.post_id)
                             .where(Comment.public_id == str(public_id or ""))).first()
        if found is None or me.id not in (found[0].person_id, found[1].person_id):
            # Somebody else's, on somebody else's post: as gone as one not there.
            return _json_error("gone", 404)
        c, post = found
        drop_comments([c.id])
        sess.flush()
        return jsonify({"ok": True, "count": counts([post.id], me).get(post.id, 0)})

    return bp
