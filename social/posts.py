"""Posts (phase 1, piece 4; docs/SOCIAL-SITE.md section 5, build order item
4): a person's words and a skribl, from the approved mocks and the owner's
"all yes" to piece 4's choices (Nov 11).

    /                   Home, signed in: "Say something, then draw it...",
                        then the pill, Following | Everyone (follows.py),
                        and its posts, newest first. Signed out, Home is the
                        first visit.
    /posts              a post: the words and the drawing the Pad or Flip
                        handed back in compose mode (JSON).
    /feed               the next page of the feed, for Load more, or the
                        first of Following or Everyone, for the pill (JSON).
    /p/<id>             a post's own page: its drawing plays by itself (sound
                        off, never under Reduce Motion; posts.js), its
                        comments (comments.py), More from its author.
    /p/<id>/delete      your own post, gone: its words and its drawing (JSON).
    /b/<skribl_id>      a drawing shown outside a post, on a page of its own:
                        a post's page without words, its comments and all
                        (bloob(): the one rule for the page and its comments).
                        Where every gallery card on the site opens: a post's
                        drawing goes on to its post, and one by somebody not
                        on the site to Skribl's own page for it.
    /b/<skribl_id>/delete  your own such drawing, gone, its comments with it.
    /p/<id>/gallery, /b/<skribl_id>/gallery
                        THE EYE on your own Gallery tab (the owner's "Yes, the
                        eye in view", Nov 14): your post's drawing, or your
                        drawing shown outside a post, in the Gallery or
                        hidden from it (JSON {"gallery": true|false}). A
                        post's by the site's own flag on it (the post stays
                        on Home and in your Posts); a drawing's by its
                        visibility in Skribl, public or link-only, through
                        set_post_visibility as its author.

ON HOME'S CARDS (the owner's yes, Nov 12): the words and the time each open
the card's own page; the face, the name and the @handle the person's; the
comments' icon is there even at none (_post.html, social.css "EASY TO OPEN").

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

THROUGH SKRIBL'S SEAMS ONLY: create_post, delete_post, set_post_visibility,
describe_posts and their exceptions (documented names, verify_social section
8), the in-post
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
from .models import PERSON_PREFIX, WORDS_MAX, Person, Post, as_utc, new_public_id, utcnow
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
    shown outside a post s<its skribl's address> (More from's; a Home page
    opened before Home kept posts only can still hold one)."""
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


def _posts_before(at, limit, person=None, hidden=frozenset(), viewer=None, among=None):
    """A page of posts (and their authors) older than `at`, newest first:
    (rows, more). Every post at the very time of a drawing's card comes after
    it (p < s), so a drawing's cursor keeps them all: read as its time, the
    posts after it come next, none missed and none twice (a Home page opened
    before Home kept posts only may still ask with one). Nobody in `hidden` (a
    block either way, or taken down: safety.hidden_ids) is in it, nor a post
    taken down, but to its own author (`viewer`), who sees it with the note.
    `among` (follows: Home's Following), a subquery of people's ids: only
    theirs, and the viewer's own."""
    q = (sa.select(Post, Person).join(Person, Post.person_id == Person.id)
         .order_by(Post.created_at.desc(), Post.public_id.desc()).limit(limit + 1))
    if person is not None:
        q = q.where(Post.person_id == person.id)
    if among is not None:
        q = q.where(sa.or_(Post.person_id.in_(among), Post.person_id == (viewer.id if viewer is not None else -1)))
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


def _drawings_before(at, limit, viewer, person, hidden=frozenset()):
    """A page of the drawings one person showed in Skribl's gallery and not in
    a post (More from), older than `at`, newest first, each with its author:
    (entries, more). Through Skribl's list_public_posts, narrowed to them,
    whose feed filter leaves out the people a block hides (the host installs
    it: app.py); nobody in `hidden` is let through here either, whatever
    the host installed. Home has none of these since the map's step 3."""
    from skribl import list_public_posts
    before = None
    if at is not None:
        when, key = at
        before = (when, key[1:] if key.startswith("s") else "")
    items, more = list_public_posts(before=before, limit=limit, author=person.public_id,
                                    viewer_id=viewer.public_id if viewer is not None else None)
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


def feed_page(before=None, limit=PAGE, viewer=None, person=None, among=None):
    """A page of a feed, newest first, after `before` (a cursor): (entries,
    next cursor or None).

    HOME'S (no `person`) IS POSTS ONLY (the map's step 3; the owner's "Yes
    on everything", Nov 13: every share is a post, and Home shows posts):
    everyone's, or with `among` (follows: Home's Following) the people
    somebody follows and theirs, their ids as a subquery
    (follows.home_items). A drawing shown in the gallery outside a post (the
    Pad's own, or anything shared before posts) is on its own page
    (/b/<id>), its maker's page and More from, never on Home. A cursor from
    a Home page opened before may name one: it is read as its time
    (_posts_before).

    ONE PERSON'S (`person`: More from, on a post's or a drawing's page) is
    their posts and the drawings they showed in the gallery outside a post,
    newest first; a drawing that is a post's shows once, as the post.

    MUTES (C, quiet everywhere): a feed of everybody's (Home, Following and
    Everyone alike) leaves out the people the viewer muted, in its query, so
    its pages stay whole; one person's (More from) is what the viewer went
    to, and keeps them."""
    from .mutes import muted_ids
    from .safety import hidden_ids
    at = _uncursor(before) if before else None
    hidden = hidden_ids(viewer)
    if person is None:
        hidden = hidden | muted_ids(viewer)
    posts, more = _posts_before(at, limit, person, hidden, viewer, among)
    out = [_entry(p, who) for p, who in posts]
    if person is not None:
        drawings, more_s = _drawings_before(at, limit, viewer, person, hidden)
        out = sorted(out + drawings, key=lambda e: (e["at"], e["key"]), reverse=True)
        more = len(out) > limit or more or more_s
    page = out[:limit]
    return page, (_cursor(page[-1]) if more and page else None)


def person_page(person, viewer, before=None, limit=PAGE):
    """A page of one person's posts, newest first, for their profile's Posts
    tab (the map's step 4): (entries, next cursor or None). Posts only (their
    drawings shown outside a post are their Gallery's), Home's own cursor and
    its rules for one person's: nobody a block hides either way, nothing
    taken down but to its own author, who sees it with the note; a mute
    leaves it as it is (their page is what the viewer went to)."""
    from .safety import hidden_ids
    at = _uncursor(before) if before else None
    if before and at is None:
        return [], None
    rows, more = _posts_before(at, limit, person, hidden_ids(viewer), viewer)
    page = [_entry(p, who) for p, who in rows]
    return page, (_cursor(page[-1]) if more and page else None)


def cards(entries, viewer):
    """What each card shows: the post (a drawing shown outside a post is a
    post whose words are its title), its author, and its drawing's size, line,
    plays, ground and whether it is on a picture as Skribl describes them for
    `viewer` (None where it cannot be had: deleted or withheld since); how
    many comments; where it goes, and its Delete."""
    from skribl import describe_posts
    from .comments import counts
    from .likes import stats
    from .mutes import muted_ids
    entries = [e if isinstance(e, dict) else _entry(*e) for e in entries]
    # WHOM THIS VIEWER MUTED (mutes): their ⋯ says Unmute. Read once a request.
    muted = muted_ids(viewer)
    # A drawing shown outside a post is asked too, in the same one read: the
    # listing it came from says no ground and no picture, and a tile lays
    # its box in them as a post's does (_gallery.html plate_ground and
    # plate_fill).
    drawings = describe_posts([e["post"].skribl_id if e["kind"] == "p" else e["sk"]["id"] for e in entries],
                              viewer_id=viewer.public_id if viewer else None)
    # HOW MANY COMMENTS each card says (phase 2; a drawing's too, since every
    # drawing has comments): what its page will show this viewer, so a block
    # or a takedown is neither shown nor counted.
    said = counts(viewer, posts=[e["post"].id for e in entries if e["kind"] == "p"],
                  drawings=[e["sk"]["id"] for e in entries if e["kind"] == "s"])
    # HOW MANY LIKES, and whether one is this viewer's (likes, phase 2): every
    # card's at once, by the same rules (nobody hidden counted).
    liked = stats(viewer, posts=[e["post"].id for e in entries if e["kind"] == "p"],
                  drawings=[e["sk"]["id"] for e in entries if e["kind"] == "s"])
    out = []
    for e in entries:
        who = e["who"]
        if e["kind"] == "p":
            p = e["post"]
            sk = drawings.get(p.skribl_id)
            url = url_for("social.post_page", public_id=p.public_id)
            gone = url_for("social.post_delete", public_id=p.public_id)
        else:
            # A drawing shown outside a post: as Skribl describes it now (its
            # ground and whether it is on a picture too). The Gallery's read
            # names its id and visibility alone (gallery._read), so one Skribl
            # no longer describes is no card there; the listing's own item
            # (More from's) stays as read, its ground and picture not known.
            sid = e["sk"]["id"]
            got = drawings.get(sid)
            sk = (dict(e["sk"], **got) if got is not None
                  else dict(e["sk"], ground=None, on_photo=False) if "title" in e["sk"] else None)
            p = _Shown(public_id="b-" + sid, words=_title_words((sk or {}).get("title")), skribl_id=sid,
                       created_at=e["at"])
            url = url_for("social.bloob_page", skribl_id=sid)
            gone = url_for("social.bloob_delete", skribl_id=sid)
        # TAKEN DOWN (piece 5): only its maker is ever shown it, with the note.
        down = (getattr(p, "taken_down_at", None) is not None or (sk or {}).get("visibility") == "withheld"
                or getattr(who, "taken_down_at", None) is not None)
        key = ("p", p.id) if e["kind"] == "p" else ("s", p.skribl_id)
        out.append({"post": p, "who": who, "sk": sk, "kind": e["kind"], "down": down,
                    "plays": plays_text(sk["views"]) if sk else None,
                    "comments": said.get(key, 0),
                    "likes": liked.get(key, {"n": 0, "mine": False, "at": None, "marks": []}),
                    "like": (url_for("social.like_post", public_id=p.public_id) if e["kind"] == "p"
                             else url_for("social.like_drawing", skribl_id=p.skribl_id)),
                    "url": url, "delete": gone,
                    "profile": profile_url(who.handle),
                    "mine": viewer is not None and viewer.id == who.id,
                    "muted": who.id in muted})
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


def bloob(skribl_id, viewer):
    """A drawing shown outside a post, as its own page shows it to `viewer`:
    (Skribl's description of it, its author's person row), or None. THE ONE
    RULE its page, its comments (comments.on_drawing) and their routes read:
    Skribl describes it to them (describe_posts: deleted, or withheld or
    private to somebody else, is absent, and so is whatever the host's
    visibility policy hides); it is public, or taken down (withheld) and
    theirs; its author is one of the site's people; no block stands between
    them either way; and its author is not taken down, unless it is them.
    HIDDEN FROM THE GALLERY by its maker (the eye on their own Gallery tab:
    link-only, unlisted, since Nov 14) it is its maker's alone, as their
    Gallery shows it to them: never a face or a comment's drawing, which are
    unlisted too and no page's. Whether it is a post's drawing (whose page is
    the post's) is the caller's to ask first."""
    from skribl import describe_posts
    sid = str(skribl_id or "")
    if not sid:
        return None
    sk = describe_posts([sid], viewer_id=viewer.public_id if viewer else None).get(sid)
    author = str((sk or {}).get("user_id") or "")
    theirs = viewer is not None and author == viewer.public_id
    # Its maker still sees one taken down (withheld), with the note, and one
    # they hid from the Gallery.
    vis = (sk or {}).get("visibility")
    shown = vis == "public" or (vis in ("withheld", "unlisted") and theirs)
    if not (sk and shown and author.startswith(PERSON_PREFIX)):
        return None
    sess = site().session()
    who = sess.execute(sa.select(Person).where(Person.public_id == author)).scalar_one_or_none()
    if who is None or between(viewer, who) or (who.taken_down_at is not None and (viewer is None or viewer.id != who.id)):
        return None
    if vis == "unlisted":
        from .models import Comment
        if who.face_id == sid or sess.execute(sa.select(Comment.id).where(Comment.skribl_id == sid).limit(1)).first():
            return None
    return sk, who


def shown_elsewhere(skribl_id, viewer, skribl_blueprint="skribl"):
    """Skribl's own page for a drawing a gallery shows `viewer` that is
    nobody's on the site (made in Skribl's own Pad, say: Skribl's own /gallery
    lists every public skribl, as the site's first visit did until Nov 14), or
    None. The site has no page for it, so its card opens
    the one it has. Public to them as Skribl describes it (the host's
    visibility policy applied), and its author not one of the site's people,
    whose drawings are bloob()'s alone."""
    from skribl import describe_posts
    sid = str(skribl_id or "")
    if not sid:
        return None
    sk = describe_posts([sid], viewer_id=viewer.public_id if viewer else None).get(sid)
    if not sk or sk.get("visibility") != "public" or str(sk.get("user_id") or "").startswith(PERSON_PREFIX):
        return None
    return url_for(skribl_blueprint + ".skribl_player", public_id=sid)


@_rests()
def home_page(skribl_blueprint="skribl"):
    """Home for somebody signed in: the composer, with the editors' compose
    addresses (?gallery=1: the author ticks "Show in the Skribls gallery" in
    their sheet), and the first page of the feed. None for nobody signed in,
    whose Home is the first visit."""
    me = current_person()
    if me is None:
        return None
    # FOLLOWING OR EVERYONE (follows): their own pick, else Following once
    # they follow somebody, Everyone before that.
    from .follows import home_cards, home_items, home_shows
    items, nxt, show = home_items(me, home_shows(me))
    note = request.args.get("note")
    return _page("feed.html", here="home", cards=home_cards(items, me), next=nxt, show=show, token=csrf_token(),
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
        """The next page of the feed, as its cards (Load more), or the first
        page of Following or Everyone (?show=, Home's pill; follows):
        {html, next, show}. A cursor says which it continues."""
        from .follows import home_cards, home_items, is_following_cursor
        me = current_person()
        before = request.args.get("before") or None
        show = request.args.get("show")
        if before:
            show = "following" if is_following_cursor(before) else "everyone"
        items, nxt, show = home_items(me, show if show in ("following", "everyone") else "everyone", before)
        html = render_template("social/_post_cards.html", cards=home_cards(items, me), me=me)
        return jsonify({"html": html, "next": nxt, "show": show})

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
        post, on a page of its own: a post's page without words, its comments
        and all. EVERY CARD OPENS HERE (the owner's "I thought on card?", Nov
        13): Skribl's Gallery cards open /b/<id> where a page of the site
        holds them (app.py, skribl.set_card_url; the first visit's did until
        Nov 14, none does now), and so does a profile's Gallery tile for a
        drawing shown outside a post (the map's step 4), so one address
        serves every drawing a gallery can show. A post's drawing goes to its post, for
        anybody who may see the post (comments.on_post, the post's own page's
        rule), and is as gone as the post to anybody else, without naming it;
        a drawing by somebody not on the site that the gallery shows them
        (public, made in Skribl's own Pad, say) goes to Skribl's own page for
        it, since the site has none; anything else is a kind 404."""
        sess = site().session()
        me = current_person()
        post = sess.execute(sa.select(Post).where(Post.skribl_id == skribl_id)).scalar_one_or_none()
        if post is not None:
            from .comments import on_post
            if on_post(me, post_id=post.id) is None:
                return _page("post_gone.html", 404, here="post")
            return redirect(url_for("social.post_page", public_id=post.public_id))
        got = bloob(skribl_id, me)
        if got is None:
            elsewhere = shown_elsewhere(skribl_id, me, skribl_blueprint)
            if elsewhere:
                return redirect(elsewhere)
            return _page("post_gone.html", 404, here="post")
        sk, who = got
        entry = {"kind": "s", "at": as_utc(datetime.fromisoformat(sk["created_at"])), "key": "s" + sk["id"],
                 "sk": sk, "who": who}
        return _post_page(cards([entry], me)[0], me)

    def _post_page(card, me):
        """A post's page, or a drawing's: More from its author, posts and
        drawings alike, newest first; and its comments (a post's, or since the
        owner's yes on Nov 12, a drawing's: whatever is opened has them)."""
        others, _ = feed_page(limit=MORE + 1, viewer=me, person=card["who"])
        key = ("s" + card["post"].skribl_id) if card["kind"] == "s" else ("p" + card["post"].public_id)
        others = [e for e in others if e["key"] != key][:MORE]
        from . import comments
        on = (comments.On(card["who"], post=card["post"]) if card["kind"] == "p" else
              comments.On(card["who"], drawing=card["post"].skribl_id, sk=card["sk"]))
        cm = comments.section(on, me, skribl_blueprint)
        # WHO LIKED IT is the maker's alone (likes): the line and the sheet's
        # rows; nothing of likes on what is taken down.
        from .likes import for_maker
        lk = for_maker(on, me) if not card["down"] else None
        # The page's token for everybody: Report is anybody's (piece 5).
        return _page("post.html", here="post", card=card, more=cards(others, me) if others else [],
                     share_url=public_origin() + card["url"], token=csrf_token(), cm=cm, lk=lk,
                     signin_here=url_for("social.signin", next=card["url"]))

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

    def _eye_asked():
        """(me, in the Gallery or not), or the refusal: the eye's guards, as
        every change's (the token and Origin, signed in, the limit), and a
        body that says {"gallery": true} or false."""
        if not origin_ok() or not token_ok():
            return None, None, _json_error("stale", 403)
        me = current_person()
        if me is None:
            return None, None, _json_error("signed_out", 401)
        if over("gallery", "person|" + me.public_id):
            return None, None, _json_error("limited", 429)
        body = request.get_json(silent=True)
        want = body.get("gallery") if isinstance(body, dict) else None
        if not isinstance(want, bool):
            return None, None, _json_error("bad", 400)
        return me, want, None

    @bp.post("/p/<public_id>/gallery")
    @_rests(json_answer=True)
    def post_gallery(public_id):
        """THE EYE on your own post's tile (your own Gallery tab; the owner's
        "Yes, the eye in view", Nov 14): its drawing in the Gallery, or hidden
        from it ({"gallery": false}). The site's own flag on the post
        (gallery_hidden_at): the post stays on Home, in your Posts and
        everywhere a post is, and its drawing's visibility in Skribl is as
        you posted it. Yours alone; one taken down is nobody's to change."""
        me, want, refusal = _eye_asked()
        if refusal is not None:
            return refusal
        sess = site().session()
        row = sess.execute(sa.select(Post).where(Post.public_id == public_id)).scalar_one_or_none()
        if row is None or row.person_id != me.id or row.taken_down_at is not None:
            return _json_error("gone", 404)
        row.gallery_hidden_at = None if want else (row.gallery_hidden_at or utcnow())
        sess.flush()
        return jsonify({"ok": True, "gallery": want})

    @bp.post("/b/<skribl_id>/gallery")
    @_rests(json_answer=True)
    def bloob_gallery(skribl_id):
        """THE EYE on your own drawing shown outside a post: its Skribl
        visibility, public ("In the gallery") or unlisted ("Link only"),
        through Skribl's set_post_visibility as its author, as the Library's
        own switch changes it. Never a post's drawing (its post's eye says),
        a face or a comment's drawing; somebody else's is SkriblNotFound, and
        one Skribl withheld can't be changed by its author."""
        me, want, refusal = _eye_asked()
        if refusal is not None:
            return refusal
        from skribl import SkriblNotFound, SkriblRefused, set_post_visibility
        from .models import Comment
        sess = site().session()
        if (sess.execute(sa.select(Post.id).where(Post.skribl_id == skribl_id)).first() is not None
                or sess.execute(sa.select(Comment.id).where(Comment.skribl_id == skribl_id).limit(1)).first() is not None
                or sess.execute(sa.select(Person.id).where(Person.face_id == skribl_id)).first() is not None):
            return _json_error("gone", 404)
        try:
            set_post_visibility(skribl_id, "public" if want else "unlisted", author_id=me.public_id)
        except SkriblNotFound:
            return _json_error("gone", 404)
        except SkriblRefused:
            return _json_error("taken_down", 403)
        sess.flush()
        return jsonify({"ok": True, "gallery": want})

    @bp.post("/b/<skribl_id>/delete")
    @_rests(json_answer=True)
    def bloob_delete(skribl_id):
        """Your own drawing, shown outside a post, gone (Skribl's delete_post,
        as its author), and its comments with it. A post's drawing goes with
        its post, never alone."""
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
        # ITS COMMENTS AND LIKES GO WITH IT, in code (phase 2): only once
        # delete_post has said it was theirs, since a refused delete still commits.
        from .comments import drop_drawing_comments
        from .likes import drop_drawing_likes
        drop_drawing_comments(skribl_id)
        drop_drawing_likes(skribl_id)
        sess.flush()
        return jsonify({"ok": True, "go": url_for("social.home", note="deleted_drawing")})


def drop_post(author_public_id, row):
    """A post's comments and answers and its likes (phase 2, said here and not
    left to a cascade), its drawing (Skribl's delete_post, as its author) and
    its row. A drawing already gone is no reason to keep the words. Flushes
    nothing: the caller does, with whatever else goes in the same transaction."""
    from skribl import SkriblNotFound, delete_post
    from .comments import drop_post_comments
    from .likes import drop_post_likes
    drop_post_comments(row.id)
    drop_post_likes(row.id)
    try:
        delete_post(row.skribl_id, author_id=author_public_id)
    except SkriblNotFound:
        pass
    site().session().delete(row)
