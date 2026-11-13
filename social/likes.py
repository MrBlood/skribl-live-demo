"""Likes (phase 2, likes; docs/SOCIAL-SITE.md "Built: likes"), from the likes
mock and the owner's "I like d." (Nov 13): everyone sees how many; who liked
it is only ever the maker's to see.

    /p/<id>/like        POST {liked, at_ms}: this person's like on a post, set
                        or taken back (JSON: {ok, liked, count}; to its maker,
                        "Liked by" and its rows again: by, who)
    /b/<skribl_id>/like the same, on a drawing shown outside a post

THE HEART stays empty until THIS viewer likes it, whatever the count beside it
says; the count is everyone's, and says nothing at zero. One like a person a
thing; the same tap takes it back. You may like your own.

WHO MAY LIKE: somebody signed in, not taken down, on a post or a drawing that
is open to them (comments.On: there for everybody, no block either way with
its maker): the rules a comment follows, read through the same On. Signed out,
the heart raises a small sheet that says how (posts.js's page, likes.js).

COUNTED BY THE VIEWER, as comment counts are: a like by anybody hidden from
them (a block either way, or taken down: safety.hidden_ids) is neither shown
nor counted, on Home's card, a post's page, "Liked by" and Activity alike.
Home's feed asks once for all its cards (stats(): one grouped query a kind).

EACH LIKE KEEPS ITS MOMENT: at_ms, where the drawing's replay was when the
heart was tapped while it played, read from Skribl's in-post player through
its playhead seam (docs/INTEGRATION.md, "Where the playhead is"); nothing when
it was not playing. It counts either way. The pink dots on the line that will
show them come later; nothing here shows a moment but the maker's sheet.

WHO LIKED IT is the maker's alone: on their own post's or drawing's page,
"Liked by Mira, Ada and 3 others" opens the sheet of who, newest first, each
with when and the moment, if one was kept (for_maker()). A like the maker
gives or takes back on their own answers with both again, so the line never
says "you" after they have taken theirs back.

DELETING IS REAL, AND SAID IN CODE, as comments' is: a post goes with its
likes (posts.drop_post), a drawing deleted through the site with its likes
(posts.bloob_delete), an account with its own likes and every like on what it
owned (accounts.delete_person). The ON DELETE CASCADEs are the net.

Every state-changing request shows the site's token and Origin and is limited
per person (security.LIMITS, "like") before it reads anything (security.over).
"""
import sqlalchemy as sa
from flask import jsonify, render_template, request

from .accounts import _json_error, _rests
from .models import Like, Person
from .safety import hidden_ids
from .security import current_person, origin_ok, over, site, token_ok

#: The most people "Liked by" lists (newest first).
WHO_MAX = 200

#: A moment past this is no moment (a day of replay): kept as none.
AT_MAX = 24 * 3600 * 1000


def _col(kind):
    return Like.post_id if kind == "p" else Like.drawing_id


def _where(on):
    """The likes on `on` (a comments.On: a post or a drawing), as SQL."""
    return Like.post_id == on.post.id if on.post is not None else Like.drawing_id == on.drawing


def stats(viewer, posts=(), drawings=()):
    """{("p", a post's internal id) or ("s", a drawing's public id):
    {"n": how many likes `viewer` is shown, "mine": whether one is theirs}},
    for every thing asked, liked or not: one grouped query for each kind
    asked, nobody hidden from `viewer` counted (their own never is)."""
    hidden = sorted(hidden_ids(viewer))
    mine_id = viewer.id if viewer is not None else -1
    out = {}
    for kind, ids in (("p", posts), ("s", drawings)):
        ids = [i for i in dict.fromkeys(ids or ()) if i is not None]
        for i in ids:
            out[(kind, i)] = {"n": 0, "mine": False}
        if not ids:
            continue
        col = _col(kind)
        q = (sa.select(col, sa.func.count(), sa.func.max(sa.case((Like.person_id == mine_id, 1), else_=0)))
             .where(col.in_(ids)).group_by(col))
        if hidden:
            q = q.where(Like.person_id.notin_(hidden))
        for k, n, m in site().session().execute(q).all():
            out[(kind, k)] = {"n": int(n), "mine": bool(m)}
    return out


def stat_on(on, viewer):
    """stats() for one post or drawing."""
    asked = {"posts": [on.post.id]} if on.post is not None else {"drawings": [on.drawing]}
    return stats(viewer, **asked)[on.key]


def who(on, viewer, limit=WHO_MAX):
    """Who liked `on`, as its maker is shown them, newest first: [(like,
    person)], nobody hidden from `viewer`."""
    hidden = sorted(hidden_ids(viewer))
    q = (sa.select(Like, Person).join(Person, Person.id == Like.person_id).where(_where(on))
         .order_by(Like.created_at.desc(), Like.id.desc()).limit(limit))
    if hidden:
        q = q.where(Like.person_id.notin_(hidden))
    return site().session().execute(q).all()


def moment(at_ms):
    """A kept moment as the line says a time: 0:06, 1:12, 1:02:03."""
    if at_ms is None:
        return None
    s = int(at_ms) // 1000
    h, m, s = s // 3600, (s // 60) % 60, s % 60
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def by_line(rows, viewer, n=None, mine=None):
    """The maker's "Liked by" line, from who()'s rows and, when given, how
    many there are (`n`) and whether one is theirs (`mine`), which a long
    list's newest rows cannot say: the first names it says (you first when
    one is yours; all of them up to three, else two) and how many more, and
    the newest three faces. None for none."""
    people = [p for _, p in rows]
    me_id = viewer.id if viewer is not None else None
    n = len(people) if n is None else n
    if not n:
        return None
    mine = any(p.id == me_id for p in people) if mine is None else mine
    names = (["you"] if mine else []) + [p.display_name.split(" ")[0] for p in people if p.id != me_id]
    shown = names[:3] if n <= 3 else names[:2]
    return {"names": shown, "more": max(0, n - len(shown)), "faces": people[:3], "you": bool(mine)}


def for_maker(on, viewer):
    """What the maker's own page shows of who liked `on`: {"rows": who()'s,
    "line": by_line()'s, "moment"}; None for anybody else."""
    if viewer is None or viewer.id != on.owner.id:
        return None
    rows = who(on, viewer)
    got = stat_on(on, viewer)
    return {"rows": rows, "line": by_line(rows, viewer, got["n"], got["mine"]), "moment": moment}


def _at(raw):
    """A moment the page sent, or none: a whole number of ms, 0 to a day."""
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        return None
    if raw != raw or raw < 0 or raw > AT_MAX:
        return None
    return int(round(raw))


# ---- deleting --------------------------------------------------------------------

def _drop(where):
    site().session().execute(sa.delete(Like).where(where).execution_options(synchronize_session=False))


def drop_post_likes(post_id):
    """Every like on a post (posts.drop_post, before the post)."""
    _drop(Like.post_id == post_id)


def drop_drawing_likes(skribl_id):
    """Every like on a drawing shown outside a post (posts.bloob_delete, once
    the drawing is gone)."""
    _drop(Like.drawing_id == str(skribl_id))


def drop_owner_likes(person_id):
    """Every like on what a person owned (accounts.delete_person)."""
    _drop(Like.owner_id == person_id)


def drop_person_likes(person_id):
    """Every like a person gave (accounts.delete_person)."""
    _drop(Like.person_id == person_id)


# ---- the routes ------------------------------------------------------------------

def register(bp):
    """Add the likes' routes to the site's blueprint."""

    def set_like(find):
        """This person's like on what `find(me)` says the request is about
        (a comments.On it is open to, or None: gone), set or taken back."""
        if not origin_ok() or not token_ok():
            return _json_error("stale", 403)
        me = current_person()
        if me is None:
            return _json_error("signed_out", 401)
        if over("like", "person|" + me.public_id):
            return _json_error("limited", 429)
        from .comments import may_comment
        if not may_comment(me):
            # Taken down (Your Reports): nothing new from the account.
            return _json_error("taken_down", 403)
        body = request.get_json(silent=True)
        if not isinstance(body, dict) or not isinstance(body.get("liked"), bool):
            return _json_error("bad", 400)
        on = find(me)
        if on is None or not on.open_to(me):
            # Not there, taken down, or a block either way: gone, as its page is.
            return _json_error("gone", 404)
        sess = site().session()
        mine = sa.and_(_where(on), Like.person_id == me.id)
        if body["liked"]:
            if sess.execute(sa.select(Like.id).where(mine)).first() is None:
                try:
                    with sess.begin_nested():
                        sess.add(Like(person_id=me.id, at_ms=_at(body.get("at_ms")), **on.row()))
                        sess.flush()
                except sa.exc.IntegrityError:
                    pass            # liked a moment ago, from another tap: one like
        else:
            sess.execute(sa.delete(Like).where(mine).execution_options(synchronize_session=False))
        sess.flush()
        got = stat_on(on, me)
        out = {"ok": True, "liked": got["mine"], "count": got["n"]}
        lk = for_maker(on, me)
        if lk is not None:
            # Their own: "Liked by" and its rows as they now stand.
            out["by"] = render_template("social/_liked_by.html", lk=lk, part="by").strip()
            out["who"] = render_template("social/_liked_by.html", lk=lk, part="who").strip()
        return jsonify(out)

    @bp.post("/p/<public_id>/like")
    @_rests(json_answer=True)
    def like_post(public_id):
        """This person's like on a post, set or taken back."""
        from .comments import on_post
        return set_like(lambda me: on_post(me, public_id=public_id))

    @bp.post("/b/<skribl_id>/like")
    @_rests(json_answer=True)
    def like_drawing(skribl_id):
        """This person's like on a drawing shown outside a post, set or taken back."""
        from .comments import on_drawing
        return set_like(lambda me: on_drawing(me, skribl_id))

    return bp
