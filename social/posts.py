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
from flask import current_app, jsonify, redirect, render_template, request, url_for

from .accounts import _hidden_in, _json_error, _page, _rests, profile_url
from .safety import between
from .models import PERSON_PREFIX, WORDS_MAX, Person, Post, as_utc, new_public_id
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
NOTES = ("deleted", "deleted_drawing", "blocked")


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


def _cursor(entry):
    """Where a page of the feed ended: its time and which card, in a form
    that names no internal id. A post's card is p<its address>, a drawing
    shown outside a post s<its skribl's address>."""
    at = as_utc(entry["at"])
    raw = f"{int(at.timestamp() * 1_000_000)}.{entry['key']}"
    return base64.urlsafe_b64encode(raw.encode()).rstrip(b"=").decode()


def _uncursor(text):
    """(time, card) from _cursor, or None. A cursor from before drawings came
    to Home names a post's address alone (11 letters): it is a post's."""
    try:
        raw = base64.urlsafe_b64decode((text or "") + "=" * (-len(text or "") % 4)).decode()
        us, key = raw.split(".", 1)
        if not (len(key) == 12 and key[0] in "ps"):
            key = "p" + key
        return datetime.fromtimestamp(int(us) / 1_000_000, tz=timezone.utc), key
    except (ValueError, TypeError, UnicodeDecodeError):
        return None


def _entry(post, who):
    return {"kind": "p", "at": as_utc(post.created_at), "key": "p" + post.public_id, "post": post, "who": who}


def _posts_before(at, limit, person=None, hidden=frozenset(), viewer=None):
    """A page of posts (and their authors) older than `at`, newest first:
    (rows, more). Every post at the very time of a drawing's card comes after
    it (p < s), so a drawing's cursor keeps them all. Nobody in `hidden` (a
    block either way, or taken down: safety.hidden_ids) is in it, nor a post
    taken down, but to its own author (`viewer`), who sees it with the note."""
    q = (sa.select(Post, Person).join(Person, Post.person_id == Person.id)
         .order_by(Post.created_at.desc(), Post.public_id.desc()).limit(limit + 1))
    if person is not None:
        q = q.where(Post.person_id == person.id)
    if hidden:
        q = q.where(Post.person_id.notin_(sorted(hidden)))
    mine = viewer.id if viewer is not None else -1
    q = q.where(sa.or_(Post.taken_down_at.is_(None), Post.person_id == mine))
    if at is not None:
        when, key = at
        if key.startswith("s"):
            q = q.where(Post.created_at <= when)
        else:
            q = q.where(sa.or_(Post.created_at < when,
                               sa.and_(Post.created_at == when, Post.public_id < key[1:])))
    rows = site().session().execute(q).all()
    return rows[:limit], len(rows) > limit


def _drawings_before(at, limit, viewer, person=None, hidden=frozenset()):
    """A page of the drawings the site's people (or one of them) showed in
    Skribl's gallery and not in a post, older than `at`, newest first, each
    with its author: (entries, more). Through Skribl's list_public_posts,
    whose feed filter leaves out the people a block hides (the host installs
    it: app.py); nobody in `hidden` is let through here either, whatever
    the host installed."""
    from skribl import list_public_posts
    before = None
    if at is not None:
        when, key = at
        before = (when, key[1:] if key.startswith("s") else "")
    who_kw = {"author": person.public_id} if person is not None else {"author_prefix": PERSON_PREFIX}
    items, more = list_public_posts(before=before, limit=limit,
                                    viewer_id=viewer.public_id if viewer is not None else None, **who_kw)
    if not items:
        return [], more
    sess = site().session()
    ids = [i["id"] for i in items]
    in_posts = set(sess.execute(sa.select(Post.skribl_id).where(Post.skribl_id.in_(ids))).scalars())
    authors = {p.public_id: p for p in sess.execute(
        sa.select(Person).where(Person.public_id.in_({i["user_id"] for i in items}))).scalars()}
    return [{"kind": "s", "at": as_utc(datetime.fromisoformat(i["created_at"])), "key": "s" + i["id"],
             "sk": i, "who": authors[i["user_id"]]}
            for i in items if i["id"] not in in_posts and i["user_id"] in authors
            and authors[i["user_id"]].id not in hidden], more


def feed_page(before=None, limit=PAGE, viewer=None, person=None):
    """A page of Home's feed: everyone's posts and the drawings the site's
    people showed in the gallery outside a post (made with Make, or the Pad
    on its own), newest first, after `before` (a cursor); or one person's
    (More from). (entries, next cursor or None). A drawing that is a post's
    shows once, as the post."""
    from .safety import hidden_ids
    at = _uncursor(before) if before else None
    hidden = hidden_ids(viewer)
    posts, more_p = _posts_before(at, limit, person, hidden, viewer)
    drawings, more_s = _drawings_before(at, limit, viewer, person, hidden)
    out = sorted([_entry(p, who) for p, who in posts] + drawings, key=lambda e: (e["at"], e["key"]), reverse=True)
    page = out[:limit]
    more = len(out) > limit or more_p or more_s
    return page, (_cursor(page[-1]) if more and page else None)


def cards(entries, viewer):
    """What each card shows: the post (a drawing shown outside a post is a
    post whose words are its title), its author, and its drawing's size, line and plays
    as Skribl describes them for `viewer` (None where it cannot be had:
    deleted or withheld since); where it goes, and its Delete."""
    from skribl import describe_posts
    entries = [e if isinstance(e, dict) else _entry(*e) for e in entries]
    drawings = describe_posts([e["post"].skribl_id for e in entries if e["kind"] == "p"],
                              viewer_id=viewer.public_id if viewer else None)
    out = []
    for e in entries:
        who = e["who"]
        if e["kind"] == "p":
            p = e["post"]
            sk = drawings.get(p.skribl_id)
            url = url_for("social.post_page", public_id=p.public_id)
            gone = url_for("social.post_delete", public_id=p.public_id)
        else:
            sk = e["sk"]
            p = _Shown(public_id="b-" + sk["id"], words=_title_words(sk.get("title")), skribl_id=sk["id"],
                       created_at=e["at"])
            url = url_for("social.bloob_page", skribl_id=sk["id"])
            gone = url_for("social.bloob_delete", skribl_id=sk["id"])
        # TAKEN DOWN (piece 5): only its maker is ever shown it, with the note.
        down = (getattr(p, "taken_down_at", None) is not None or (sk or {}).get("visibility") == "withheld"
                or getattr(who, "taken_down_at", None) is not None)
        out.append({"post": p, "who": who, "sk": sk, "kind": e["kind"], "down": down,
                    "plays": plays_text(sk["views"]) if sk else None,
                    "url": url, "delete": gone,
                    "profile": profile_url(who.handle),
                    "mine": viewer is not None and viewer.id == who.id})
    return out


def _title_words(title):
    """A drawing's title, the words its maker gave it in the Pad's sheet, as
    a card's words; none for Skribl's own stand-in for no title."""
    title = (title or "").strip()
    return "" if title in ("", "Untitled Skribl") else title


class _Shown:
    """A drawing shown outside a post, as a card reads a post: its address
    (b-<the skribl's>, so no post's can match it), its title for its words,
    its skribl, when."""
    __slots__ = ("public_id", "words", "skribl_id", "created_at")

    def __init__(self, **kw):
        for k, v in kw.items():
            setattr(self, k, v)


@_rests()
def home_page(skribl_blueprint="skribl"):
    """Home for somebody signed in: the composer, with the editors' compose
    addresses (?gallery=1: the author ticks "Show in the Skribls gallery" in
    their sheet), and the first page of the feed. None for nobody signed in,
    whose Home is the first visit."""
    me = current_person()
    if me is None:
        return None
    rows, nxt = feed_page(viewer=me)
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
        if site().session().execute(sa.select(Person.taken_down_at).where(Person.id == me.id)).scalar() is not None:
            # Taken down (piece 5): nothing new is shared from the account.
            return _json_error("taken_down", 403)
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
        rows, nxt = feed_page(request.args.get("before"), viewer=me)
        html = render_template("social/_post_cards.html", cards=cards(rows, me), me=me)
        return jsonify({"html": html, "next": nxt})

    @bp.get("/p/<public_id>")
    @_rests()
    def post_page(public_id):
        """A post on a page of its own: it plays by itself (posts.js)."""
        sess = site().session()
        found = sess.execute(sa.select(Post, Person).join(Person, Post.person_id == Person.id)
                             .where(Post.public_id == public_id)).first()
        me = current_person()
        mine = found is not None and me is not None and found[1].id == me.id
        if (found is None or between(me, found[1])
                or (not mine and (found[0].taken_down_at is not None or found[1].taken_down_at is not None))):
            # A block, either way, or a takedown makes it as gone as a deleted
            # one, to all but its author.
            return _page("post_gone.html", 404, here="post")
        return _post_page(cards([found], me)[0], me)

    @bp.get("/b/<skribl_id>")
    @_rests()
    def bloob_page(skribl_id):
        """A drawing one of the site's people showed in the gallery outside a
        post, on a page of its own: a post's page without words. A drawing
        that is a post's goes to its post; anything else is a kind 404."""
        from skribl import describe_posts
        sess = site().session()
        post = sess.execute(sa.select(Post).where(Post.skribl_id == skribl_id)).scalar_one_or_none()
        if post is not None:
            return redirect(url_for("social.post_page", public_id=post.public_id))
        me = current_person()
        sk = describe_posts([skribl_id], viewer_id=me.public_id if me else None).get(skribl_id)
        who = None
        author = str((sk or {}).get("user_id") or "")
        # Its maker still sees one taken down (withheld), with the note.
        shown = (sk or {}).get("visibility") == "public" or (
            (sk or {}).get("visibility") == "withheld" and me is not None and author == me.public_id)
        if sk and shown and author.startswith(PERSON_PREFIX):
            who = sess.execute(sa.select(Person).where(Person.public_id == author)).scalar_one_or_none()
        if who is None or between(me, who) or (who.taken_down_at is not None and (me is None or me.id != who.id)):
            return _page("post_gone.html", 404, here="post")
        entry = {"kind": "s", "at": as_utc(datetime.fromisoformat(sk["created_at"])), "key": "s" + sk["id"],
                 "sk": sk, "who": who}
        return _post_page(cards([entry], me)[0], me)

    def _post_page(card, me):
        """A post's page, or a drawing's: More from its author, posts and
        drawings alike, newest first."""
        others, _ = feed_page(limit=MORE + 1, viewer=me, person=card["who"])
        key = ("s" + card["post"].skribl_id) if card["kind"] == "s" else ("p" + card["post"].public_id)
        others = [e for e in others if e["key"] != key][:MORE]
        # The page's token for everybody: Report is anybody's (piece 5).
        return _page("post.html", here="post", card=card, more=cards(others, me) if others else [],
                     share_url=public_origin() + card["url"], token=csrf_token())

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

    @bp.post("/b/<skribl_id>/delete")
    @_rests(json_answer=True)
    def bloob_delete(skribl_id):
        """Your own drawing, shown outside a post, gone (Skribl's delete_post,
        as its author). A post's drawing goes with its post, never alone."""
        if not origin_ok() or not token_ok():
            return _json_error("stale", 403)
        me = current_person()
        if me is None:
            return _json_error("signed_out", 401)
        from skribl import SkriblNotFound, delete_post
        sess = site().session()
        if sess.execute(sa.select(Post.id).where(Post.skribl_id == skribl_id)).first() is not None:
            return _json_error("gone", 404)
        try:
            # Somebody else's is SkriblNotFound too, on purpose (docs/INTEGRATION.md).
            delete_post(skribl_id, author_id=me.public_id)
        except SkriblNotFound:
            return _json_error("gone", 404)
        sess.flush()
        return jsonify({"ok": True, "go": url_for("social.home", note="deleted_drawing")})


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
