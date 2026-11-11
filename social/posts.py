"""Posts (phase 1, piece 4; docs/SOCIAL-SITE.md section 5, build order item
4): a person's words and a skribl, from the approved mocks and the owner's
"all yes" to piece 4's choices (Nov 11).

    /                   Home, signed in: "Say something, then draw it...",
                        then everyone's posts, newest first (Following comes
                        with phase 2). Signed out, Home is the first visit.
    /posts              a post: the words and the drawing the Pad or Flip
                        handed back in compose mode (JSON).
    /feed               the next page of the feed, for Load more (JSON).
    /p/<id>             a post's own page: its drawing plays by itself (sound
                        off, never under Reduce Motion; posts.js), Comments'
                        place kept, More from its author.
    /p/<id>/delete      your own post, gone: its words and its drawing (JSON).

A POST IS WORDS AND A SKRIBL. The skribl is posted through Skribl's
create_post (docs/INTEGRATION.md, "When your composer is a form") in the same
request, and so the same transaction, as the row that names it: kept together
or not at all. Its visibility is what the author ticked in the editor's
sheet (?gallery=1, "Show in the Skribls gallery"): public with the tick,
unlisted (reachable by its link, listed nowhere but here) without. Its title
is the post's first words, its caption only what the author wrote under the
tick ("say the post's words once", the owner, Nov 10).

A feed reads its drawings' sizes, lines and plays through Skribl's
describe_posts (one query a page), for the person looking: a drawing deleted
or withheld since is simply absent, and its post still renders, the player
saying the drawing is not here anymore.

THROUGH SKRIBL'S SEAMS ONLY: create_post, delete_post, describe_posts and
their exceptions (documented names, verify_social section 8), the in-post
player's macros, the editors' addresses with their documented compose flags.
Every state-changing request shows the site's token and Origin and is limited
per person (security.LIMITS) before it reads anything.
"""
import base64
import unicodedata
from datetime import datetime, timezone

import sqlalchemy as sa
from flask import current_app, jsonify, render_template, request, url_for

from .accounts import _hidden_in, _json_error, _page, _rests, profile_url
from .models import WORDS_MAX, Person, Post, as_utc, new_public_id
from .security import csrf_token, current_person, origin_ok, over, public_origin, site, token_ok

#: The most a post may weigh on its way here: the editor's whole payload (a
#: Flip with its music included) and its share card. Skribl's own caps on
#: each part still apply in create_post; the app's MAX_CONTENT_LENGTH (25 MB)
#: stands above it. Every other request to the site stops at 64 KiB.
POST_MAX_BODY = 24 * 1024 * 1024

#: A page of the feed.
PAGE = 20

#: How many of a person's other posts a post's page shows (More from).
MORE = 3

#: A post's title on Skribl's side (what /s/<id> unfurls with): its first
#: words, up to this many characters (Skribl's own cap is the same).
TITLE_MAX = 80

#: The notes Home says once, on the way back (?note=).
NOTES = ("deleted",)


def check_words(raw):
    """A post's words as people will see them, or why not: plain text, at
    most WORDS_MAX characters, each line's spaces tidied and blank lines run
    together, nothing hidden or turned around (as a bio). Empty is allowed:
    a post can be a drawing alone. Anything but text is no words."""
    text = unicodedata.normalize("NFC", raw if isinstance(raw, str) else "")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = []
    for line in text.split("\n"):
        line = " ".join(line.split())
        if line or (lines and lines[-1]):
            lines.append(line)
    while lines and not lines[-1]:
        lines.pop()
    words = "\n".join(lines)
    if len(words) > WORDS_MAX:
        return None, "words_long"
    if _hidden_in(words):
        return None, "words_chars"
    return words, None


def title_from(words):
    """The post's first words, as its skribl's title: the first line, cut at
    a space before TITLE_MAX with an ellipsis; "Untitled Skribl" for none."""
    first = (words or "").split("\n", 1)[0].strip()
    if not first:
        return "Untitled Skribl"
    if len(first) <= TITLE_MAX:
        return first
    cut = first[:TITLE_MAX - 1].rsplit(" ", 1)[0] or first[:TITLE_MAX - 1]
    return cut.rstrip() + "…"


def plays_text(n):
    """A play count as people say it: 1 play, 312 plays, 2.9k plays, 1.2M;
    None for none yet (a page says nothing, a card its own words)."""
    n = int(n or 0)
    if n <= 0:
        return None
    if n == 1:
        return "1 play"
    if n < 1000:
        return f"{n} plays"
    for div, unit in ((1_000_000, "M"), (1000, "k")):
        if n >= div:
            v = n / div
            s = f"{v:.1f}" if v < 10 else f"{v:.0f}"
            return f"{s.rstrip('0').rstrip('.') if '.' in s else s}{unit} plays"
    return f"{n} plays"


def _cursor(row):
    """Where a page of the feed ended: its time and address, in a form that
    names no internal id."""
    at = as_utc(row.created_at)
    raw = f"{int(at.timestamp() * 1_000_000)}.{row.public_id}"
    return base64.urlsafe_b64encode(raw.encode()).rstrip(b"=").decode()


def _uncursor(text):
    try:
        raw = base64.urlsafe_b64decode((text or "") + "=" * (-len(text or "") % 4)).decode()
        us, pid = raw.split(".", 1)
        return datetime.fromtimestamp(int(us) / 1_000_000, tz=timezone.utc), pid
    except (ValueError, TypeError, UnicodeDecodeError):
        return None


def feed_page(before=None, limit=PAGE):
    """A page of everyone's posts, newest first, after `before` (a cursor),
    with their authors: (rows, next cursor or None)."""
    q = (sa.select(Post, Person).join(Person, Post.person_id == Person.id)
         .order_by(Post.created_at.desc(), Post.public_id.desc()).limit(limit + 1))
    at = _uncursor(before) if before else None
    if at is not None:
        when, pid = at
        q = q.where(sa.or_(Post.created_at < when, sa.and_(Post.created_at == when, Post.public_id < pid)))
    rows = site().session().execute(q).all()
    more = len(rows) > limit
    rows = rows[:limit]
    return rows, (_cursor(rows[-1][0]) if more and rows else None)


def cards(rows, viewer):
    """What each post's card shows: the post, its author, and its drawing's
    size, line and plays as Skribl describes them for `viewer` (None where
    it cannot be had: deleted or withheld since)."""
    from skribl import describe_posts
    drawings = describe_posts([p.skribl_id for p, _ in rows],
                              viewer_id=viewer.public_id if viewer else None)
    out = []
    for p, who in rows:
        sk = drawings.get(p.skribl_id)
        out.append({"post": p, "who": who, "sk": sk,
                    "plays": plays_text(sk["views"]) if sk else None,
                    "url": url_for("social.post_page", public_id=p.public_id),
                    "profile": profile_url(who.handle),
                    "mine": viewer is not None and viewer.id == p.person_id})
    return out


@_rests()
def home_page(skribl_blueprint="skribl"):
    """Home for somebody signed in: the composer, with the editors' compose
    addresses (?gallery=1: the author ticks "Show in the Skribls gallery" in
    their sheet), and the first page of the feed. None for nobody signed in,
    whose Home is the first visit."""
    me = current_person()
    if me is None:
        return None
    rows, nxt = feed_page()
    note = request.args.get("note")
    return _page("feed.html", here="home", cards=cards(rows, me), next=nxt, token=csrf_token(),
                 note=note if note in NOTES else None,
                 pad_compose=url_for(skribl_blueprint + ".skribl_editor", compose=1, gallery=1),
                 flip_compose=url_for(skribl_blueprint + ".skribl_flip", compose=1, gallery=1))


def register(bp, skribl_blueprint="skribl"):
    """Add the posts' routes to the site's blueprint."""

    @bp.post("/posts")
    @_rests(json_answer=True)
    def post_new():
        """A post: the words, and the drawing the editor handed back. The
        skribl and the row land in one transaction, or neither does."""
        if not origin_ok() or not token_ok():
            return _json_error("stale", 403)
        me = current_person()
        if me is None:
            return _json_error("signed_out", 401)
        if over("post", "person|" + me.public_id):
            return _json_error("limited", 429)
        body = request.get_json(silent=True)
        if not isinstance(body, dict):
            return _json_error("no_drawing", 400)
        words, problem = check_words(body.get("words"))
        if problem:
            return _json_error(problem, 400)
        payload = body.get("payload")
        if not isinstance(payload, dict):
            return _json_error("no_drawing", 400)
        from skribl import SkriblRejected, SkriblUnavailable, create_post
        drawing = dict(payload)
        # WHAT THE AUTHOR TICKED, AND NOTHING ELSE: public only with the
        # editor's "Show in the Skribls gallery", its caption only with it;
        # the title is the post's own first words (set here, not trusted).
        gallery = drawing.get("visibility") == "public"
        drawing["visibility"] = "public" if gallery else "unlisted"
        drawing["title"] = title_from(words)
        caption = str(drawing.get("caption") or "").strip() if gallery else ""
        if caption:
            drawing["caption"] = caption
        else:
            drawing.pop("caption", None)
        try:
            made = create_post(drawing, author_id=me.public_id)
        except SkriblRejected as exc:
            return _json_error("rejected", exc.status if 400 <= exc.status < 500 else 400,
                               message=exc.message)
        except SkriblUnavailable:
            return _json_error("busy", 503)
        row = Post(public_id=new_public_id(8), person_id=me.id, words=words or "",
                   skribl_id=made.public_id)
        sess = site().session()
        sess.add(row)
        sess.flush()
        return jsonify({"ok": True, "post": row.public_id,
                        "go": url_for("social.post_page", public_id=row.public_id)})

    @bp.get("/feed")
    @_rests(json_answer=True)
    def feed_more():
        """The next page of the feed, as its cards (Load more): {html, next}."""
        me = current_person()
        rows, nxt = feed_page(request.args.get("before"))
        html = render_template("social/_post_cards.html", cards=cards(rows, me), me=me)
        return jsonify({"html": html, "next": nxt})

    @bp.get("/p/<public_id>")
    @_rests()
    def post_page(public_id):
        """A post on a page of its own: it plays by itself (posts.js)."""
        sess = site().session()
        found = sess.execute(sa.select(Post, Person).join(Person, Post.person_id == Person.id)
                             .where(Post.public_id == public_id)).first()
        if found is None:
            return _page("post_gone.html", 404, here="post")
        me = current_person()
        card = cards([found], me)[0]
        others = sess.execute(sa.select(Post, Person).join(Person, Post.person_id == Person.id)
                              .where(Post.person_id == found[0].person_id, Post.id != found[0].id)
                              .order_by(Post.created_at.desc()).limit(MORE)).all()
        return _page("post.html", here="post", card=card, more=cards(others, me) if others else [],
                     share_url=public_origin() + card["url"], token=csrf_token() if me else None)

    @bp.post("/p/<public_id>/delete")
    @_rests(json_answer=True)
    def post_delete(public_id):
        """Your own post, gone: its words and its drawing, in one transaction."""
        if not origin_ok() or not token_ok():
            return _json_error("stale", 403)
        me = current_person()
        if me is None:
            return _json_error("signed_out", 401)
        sess = site().session()
        row = sess.execute(sa.select(Post).where(Post.public_id == public_id)).scalar_one_or_none()
        if row is None or row.person_id != me.id:
            return _json_error("gone", 404)
        drop_post(me.public_id, row)
        sess.flush()
        return jsonify({"ok": True, "go": url_for("social.home", note="deleted")})


def drop_post(author_public_id, row):
    """A post's drawing (Skribl's delete_post, as its author) and its row.
    A drawing already gone is no reason to keep the words. Flushes nothing:
    the caller does, with whatever else goes in the same transaction."""
    from skribl import SkriblNotFound, delete_post
    try:
        delete_post(row.skribl_id, author_id=author_public_id)
    except SkriblNotFound:
        pass
    site().session().delete(row)
