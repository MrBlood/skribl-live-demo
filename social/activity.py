"""Activity (phase 2, notifications; docs/SOCIAL-SITE.md "Built:
notifications"), from the notifications mock and the owner's "all yes" (Nov
12): A, a bell drawn in our pen at the top right of a phone's Home and
Explore (where Sign in sits before you sign in), and Activity in a desk's
rail after Explore; each with a dot when something is new.

    /activity     who said something on your posts, and who answered you:
                  New, then Earlier, a row each, every row one link to its
                  comment on its page; opening it marks everything seen.

WORKED OUT FROM THE COMMENTS, NOT KEPT. There is no table of notifications to
keep in step with them: the rows are the comments themselves, read by the
rules their own pages read, so a comment deleted, removed or taken down, or
somebody a block or a takedown hides, takes its row with it at once, and
nothing ever has to be swept or forgotten. Two things are kept: when each
person last looked (social_people.activity_seen_at), and whom an answer
answers (social_comments.to_person_id), which parent_id cannot say, since an
answer to an answer sits under the same top-level comment.

WHAT A ROW IS: a comment or an answer, not yours,
  * answering you: "Theo answered your comment", or, with a drawing, "Juno
    answered with a drawing";
  * else on what you own, a post or a drawing shown outside a post: "Mira
    said something on your post", or, with a drawing, "Juno drew something
    on your post".
Several since you last looked on one post (or answering you in one
conversation) are one row, the newest face in front and the newest words
under it, and the row opens the newest: "Mira and 2 others said something
on your post" ("Mira and Theo" for two). A drawing keeps a row of its own,
so its small picture shows. Earlier keeps a row for each, as it was said
(the mock's pictures). The page reads the newest READ comments.

NEVER IN IT: yourself; anybody hidden from you (a block either way, or
taken down: safety.hidden_ids); a comment taken down, or an answer under a
comment you are not shown; anything on a post or a drawing whose page you
cannot see (a block either way with its maker, it or its maker taken down,
a drawing deleted in the Library or no longer public). These are
comments.seen's rules, read for many comments at once: what a row links to
is on its page. A comment deleted or removed is not there to read.

THE DOT (dot()): whether anything is new since they last looked, by the
same rules, asked once a request by a page with the bar or the rail (the
phone's bell on Home and Explore, a desk's rail on every page): newest
first on the two indexes it reads, (owner_id, created_at) and
(to_person_id, created_at), a handful of rows at most, and Skribl asked
only when every new one is on a drawing (whether its page is still there).

SEEN IS OPENING IT: the page reads the list as it stands, then sets the
time it was opened; the rows that were new keep their dot while you are
there, and next time they sit under Earlier. A row's link is its comment on
its page (#c-<id>, a post's or a drawing's), where comments.js makes it
glow a moment and, a drawing answer, draw itself once.

THROUGH SKRIBL'S SEAMS ONLY: describe_posts (whether a drawing's page is
there for the viewer; each small picture's size), and the poster's address
by url_for, as More from's tiles take theirs.
"""
import math

import sqlalchemy as sa
import sqlalchemy.orm  # noqa: F401  (sa.orm.aliased)
from flask import g, redirect, request, url_for

from .accounts import _page, _rests
from .models import PERSON_PREFIX, Comment, Person, Post, as_utc, utcnow
from .safety import hidden_ids
from .security import current_person, site

#: The most comments the page reads, newest first, before they are rows.
READ = 100

#: The most new ones the dot reads, looking for one it may show.
DOT_READ = 20

#: Skribl's describe_posts answers this many ids a call, at most.
_DESCRIBE = 200


# ---- what may be a row ---------------------------------------------------------

def _query(me, hidden, which, since=None, limit=READ):
    """The comments that may be `me`'s rows, newest first: `which` (on what
    they own, or answering them), not theirs, nobody hidden from them, none
    taken down, an answer only under a comment shown to them, on a post
    shown to them (theirs, or nobody hidden's and not taken down); after
    `since`, when given. Whether a drawing's own page is there is Skribl's to
    say (_page_there). Rows: (comment, its author, the post's address, the
    post's skribl), the last two None for a comment on a drawing."""
    c, par = Comment, sa.orm.aliased(Comment)
    hid = sorted(hidden)
    q = (sa.select(c, Person, Post.public_id, Post.skribl_id)
         .join(Person, Person.id == c.person_id)
         .outerjoin(par, par.id == c.parent_id)
         .outerjoin(Post, Post.id == c.post_id)
         .where(which, c.person_id != me.id, c.taken_down_at.is_(None)))
    # The comment an answer sits under, as its page shows it: not taken down
    # (but to its own author), nobody hidden's.
    under = sa.or_(par.taken_down_at.is_(None), par.person_id == me.id)
    # What it is on, as its page shows it: theirs, or not taken down and
    # nobody hidden's (a block either way, its maker taken down).
    there = sa.or_(c.post_id.is_(None), Post.taken_down_at.is_(None))
    if hid:
        q = q.where(c.person_id.notin_(hid))
        under = sa.and_(under, par.person_id.notin_(hid))
        there = sa.and_(there, c.owner_id.notin_(hid))
    q = q.where(sa.or_(c.parent_id.is_(None), under), sa.or_(c.owner_id == me.id, there))
    if since is not None:
        q = q.where(c.created_at > since)
    return q.order_by(c.created_at.desc(), c.id.desc()).limit(limit)


def _read(me, hidden, since=None, limit=READ):
    """Both kinds, newest first, each once (an answer to you on your own post
    is both): [(comment, author, post address, post skribl)]."""
    sess = site().session()
    got = {}
    for which in (Comment.owner_id == me.id, Comment.to_person_id == me.id):
        for row in sess.execute(_query(me, hidden, which, since, limit)).all():
            got.setdefault(row[0].id, tuple(row))
    return sorted(got.values(), key=lambda r: (as_utc(r[0].created_at), r[0].id), reverse=True)[:limit]


def _described(me, ids):
    """Skribl's description of each skribl in `ids` for `me` (describe_posts,
    a call for each 200): {id: item}, absent where it cannot be had."""
    from skribl import describe_posts
    ids = [i for i in dict.fromkeys(ids) if i]
    out = {}
    for k in range(0, len(ids), _DESCRIBE):
        out.update(describe_posts(ids[k:k + _DESCRIBE], viewer_id=me.public_id))
    return out


def _page_there(sk, me):
    """Whether a drawing shown outside a post has its page for `me`, from
    Skribl's description of it (posts.bloob's rule; who its maker is, and a
    block either way, the query has asked already): public, or taken down
    and theirs, by one of the site's people."""
    if not sk:
        return False
    author = str(sk.get("user_id") or "")
    vis = sk.get("visibility")
    return author.startswith(PERSON_PREFIX) and (vis == "public" or (vis == "withheld" and author == me.public_id))


def _drawings_shown(me, drawing_ids, sk):
    """Of `drawing_ids` (what comments are on), those whose page `me` may
    open: not a post's drawing (whose comments are its post's), and there
    (_page_there) by `sk`, Skribl's descriptions."""
    ids = sorted({d for d in drawing_ids if d})
    if not ids:
        return set()
    in_posts = set(site().session().execute(sa.select(Post.skribl_id).where(Post.skribl_id.in_(ids))).scalars())
    return {d for d in ids if d not in in_posts and _page_there(sk.get(d), me)}


# ---- the dot ---------------------------------------------------------------------

def dot(me):
    """Whether anything is new for `me` since they last looked: Activity's
    own rules, a handful of rows at most; Skribl is asked only when every new
    one is on a drawing."""
    since = as_utc(me.activity_seen_at) if getattr(me, "activity_seen_at", None) else None
    rows = _read(me, hidden_ids(me), since, DOT_READ)
    if any(c.drawing_id is None for c, *_ in rows):
        return True
    drawings = [c.drawing_id for c, *_ in rows]
    return bool(drawings) and bool(_drawings_shown(me, drawings, _described(me, drawings)))


def dot_for_request():
    """"new" when something is new for the person signed in, else None:
    asked once a request, however many places show it (a phone's bell and a
    desk's rail are the same page). Activity's own page says "going" itself,
    the dot fading as they look. A dot that cannot be read is no dot, said
    once in the log, never a page that fails."""
    if "social_activity_dot" in g:
        return g.social_activity_dot
    me = current_person()
    got = None
    if me is not None:
        try:
            got = "new" if dot(me) else None
        except sa.exc.SQLAlchemyError:
            site().say_once("activity-dot", "the site could not read what is new for Activity's dot; "
                                            "the bell shows none until it can. Are its tables up to date? "
                                            "python -m alembic -c social/alembic.ini upgrade head")
    g.social_activity_dot = got
    return got


# ---- the rows ----------------------------------------------------------------

def _kind(c, me):
    """What a comment says to `me`: answering them (with a drawing, or
    not), or on what they own (a drawing, or words)."""
    if c.to_person_id == me.id:
        return "answer_drawing" if c.skribl_id else "answer"
    return "drawing" if c.skribl_id else "comment"


def _key(kind, c):
    """Which row a new comment joins: words on one post (or one drawing) are
    one row; answers to you in one conversation (under one comment) are one
    row; a drawing is a row of its own."""
    if kind == "comment":
        return ("on", "p", c.post_id) if c.post_id is not None else ("on", "s", c.drawing_id)
    if kind == "answer":
        return ("to", c.parent_id)
    return ("one", c.id)


def _pic(sid, sk, skribl_blueprint, inner=50):
    """A drawing's small picture: its middle, square, cut from its poster (the
    share card) as More from's tile and a face cut theirs (lib/sharecard.js
    drawingRect's sums and rounding: the card 1200 x 630, its drawing's area
    1092 x 492 above an 84px foot, the plate's hairline 3px in), the poster
    placed behind a box `inner` px across. None when Skribl does not describe
    it (deleted or withheld since): the box keeps the ground a drawing waits
    on."""
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
    q = min(cw, ch)
    left = x + (cw - q) / 2
    top = min(max(y + 0.46 * ch - q / 2, y), y + ch - q)
    k = inner / q
    return {"src": url_for(skribl_blueprint + ".skribl_poster", public_id=sid),
            "size": f"{1200 * k:.2f}px auto", "at": f"{-left * k:.2f}px {-top * k:.2f}px"}


def listing(me, skribl_blueprint="skribl"):
    """(new rows, earlier rows) for `me`, newest first, as Activity shows
    them. Each row: {"kind", "new", "c" (the newest comment, which the row
    opens), "people" (newest first, each once), "names" (their first names),
    "href", "pic"}."""
    since = as_utc(me.activity_seen_at) if getattr(me, "activity_seen_at", None) else None
    items = _read(me, hidden_ids(me))
    drawings = [r[0].drawing_id for r in items if r[0].drawing_id]
    pics = {r[0].id: (r[0].skribl_id or r[3] or r[0].drawing_id) for r in items}
    sk = _described(me, drawings + list(pics.values()))
    shown = _drawings_shown(me, drawings, sk)
    sections = ([], [])
    groups = {}
    for c, who, post_public, _ in items:
        if c.drawing_id is not None and c.drawing_id not in shown:
            continue
        new = since is None or as_utc(c.created_at) > since
        at = 0 if new else 1
        kind = _kind(c, me)
        # GROUPED SINCE YOU LAST LOOKED: Earlier is a row for each, as it was said.
        key = _key(kind, c) if new else ("one", c.id)
        row = groups.get(key)
        if row is None:
            page = (url_for("social.post_page", public_id=post_public) if c.post_id is not None
                    else url_for("social.bloob_page", skribl_id=c.drawing_id))
            row = {"kind": kind, "new": new, "c": c, "people": [], "names": [],
                   "href": page + "#c-" + c.public_id,
                   "pic": _pic(pics[c.id], sk.get(pics[c.id]), skribl_blueprint)}
            groups[key] = row
            sections[at].append(row)
        if all(p.id != who.id for p in row["people"]):
            row["people"].append(who)
            row["names"].append(who.display_name.split(" ")[0])
    return sections


# ---- the page ------------------------------------------------------------------

def register(bp, skribl_blueprint="skribl"):
    """Add Activity's page to the site's blueprint."""

    @bp.get("/activity")
    @_rests()
    def activity():
        """Activity: who said something on your posts, and who answered you."""
        me = current_person()
        if me is None:
            return redirect(url_for("social.signin", next=request.path), 303)
        # SEEN IS OPENING IT. The time is taken before the list is read, so a
        # comment made meanwhile is still new next time.
        now = utcnow()
        fresh, earlier = listing(me, skribl_blueprint)
        sess = site().session()
        sess.execute(sa.update(Person).where(Person.id == me.id).values(activity_seen_at=now))
        sess.flush()
        # The rail's dot (a desk) fades as they look, where there was one.
        g.social_activity_dot = "going" if fresh else None
        return _page("activity.html", here="activity", fresh=fresh, earlier=earlier)

    return bp
