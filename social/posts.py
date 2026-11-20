"""Posts (phase 1, piece 4; docs/SOCIAL-SITE.md section 5, build order item
4): a person's words and a skribl, from the approved mocks and the owner's
"all yes" to piece 4's choices (Nov 11).

    /                   Home, signed in: the pill, Following | Everyone
                        (follows.py), and its posts, newest first; Make is
                        the way to post (compose.py, the owner's "All yes",
                        Nov 14: no box at the top). Signed out, Home is the
                        first visit.
    /posts              a post: the words and the drawing the Pad or Flip
                        handed back in compose mode, or ONE OF YOUR OLDER
                        DRAWINGS (the composer's Yours: {"skribl": its id}),
                        whose hearts and comments come with it (JSON).
    /feed               the next page of the feed, for Load more, or the
                        first of Following or Everyone, for the pill (JSON).
    /p/<id>             a post's own page: its drawing plays by itself (sound
                        off, never under Reduce Motion; posts.js), the
                        draw-backs on it and its comments (comments.py).
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
Since MENTIONS (mentions.py; the owner's "All yes", Nov 15) the words are no
link of their own, since a link cannot hold the links to the people they
name: a tap on them opens the post as the card's ground does (posts.js), a
tap on an @handle in them opens that person's page, and the time is the
post's link.

A POST IS WORDS AND A SKRIBL. The skribl is posted through Skribl's
create_post (docs/INTEGRATION.md, "When your composer is a form") in the same
request, and so the same transaction, as the row that names it: kept together
or not at all. It is unlisted in Skribl (reachable by its link, listed
nowhere but here): the site's Gallery shows a post's drawing by the site's
own flag, and the composer no longer asks the editors for Skribl's gallery
tick (the walkthrough's mocks, choice 2, the owner's "all yes", Nov 19:
the tick fed Skribl's own gallery, which the site has no door to). The
route still keeps what a payload says, public with its caption, as the
posts made with the tick before that are. Its title is the post's first
words ("say the post's words once", the owner, Nov 10).

ONE DRAWING, ONE CONVERSATION (docs/SOCIAL-SITE.md section 17; the owner's
"Yes", Nov 14). A post can be one of your older drawings, one you shared
outside a post (the Pad's own share, or the eye's link-only one): the post's
row names that skribl, so nothing is made in Skribl, and in the same
transaction the drawing's hearts, comments and bookmarks move onto the post
(comments.move_drawing_comments, likes.move_drawing_likes,
bookmarks.move_drawing_bookmarks). Its own page,
/b/<id>, then sends people to the post (bloob_page, as it does for every
post's drawing), so nothing is lost and one drawing never has two
conversations. A drawing in a post is never posted again (that will be a
repost). One its maker hid from the Gallery (link-only) stays hidden there
as a post (gallery_hidden_at), as the eye said.

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
import hashlib
import unicodedata
from datetime import datetime, timezone

import sqlalchemy as sa
from flask import current_app, jsonify, redirect, render_template, request, url_for

from .accounts import _hidden_in, _json_error, _page, _rests, profile_url
from .safety import between
from .models import PERSON_PREFIX, WORDS_MAX, Person, Post, as_utc, first_name, new_public_id, utcnow
from .security import csrf_token, current_person, origin_ok, over, public_origin, site, token_ok

#: The most a post may weigh on its way here: the editor's whole payload (a
#: Flip with its music included) and its share card. Skribl's own caps on
#: each part still apply in create_post; the app's MAX_CONTENT_LENGTH (25 MB)
#: stands above it. Every other request to the site stops at 64 KiB.
POST_MAX_BODY = 24 * 1024 * 1024

#: A page of the feed.
PAGE = 20

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
    that names no internal id. A post's card is p<its address>, a repost's
    r<the original's address> at the repost's time (reposts.py: Home's
    Following and a person's Posts tab), a drawing shown outside a post
    s<its skribl's address> (a Home page opened before Home kept posts only
    can still hold one)."""
    at = as_utc(entry["at"])
    raw = f"{int(at.timestamp() * 1_000_000)}.{entry['key']}"
    return base64.urlsafe_b64encode(raw.encode()).rstrip(b"=").decode()


def _uncursor(text):
    """(time, card) from _cursor, or None. A cursor from before drawings came
    to Home names a post's address alone (11 letters): it is a post's."""
    try:
        raw = base64.urlsafe_b64decode((text or "") + "=" * (-len(text or "") % 4)).decode()
        us, key = raw.split(".", 1)
        if not (len(key) == 12 and key[0] in "prs"):
            key = "p" + key
        return datetime.fromtimestamp(int(us) / 1_000_000, tz=timezone.utc), key
    except (ValueError, TypeError, UnicodeDecodeError):
        return None


#: The most draw-backs a post's page shows in its strip (Draw back, step 2).
BACKS = 12


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
        # A drawing's cursor (s) or a repost's (r) sorts after every post's at
        # its very time, so the posts at that time come next (gallery._after).
        from .gallery import _after
        q = q.where(_after(Post.created_at, Post.public_id, "p", at))
    rows = site().session().execute(q).all()
    return rows[:limit], len(rows) > limit


def feed_page(before=None, limit=PAGE, viewer=None, among=None):
    """A page of Home's feed, newest first, after `before` (a cursor):
    (entries, next cursor or None).

    POSTS ONLY (the map's step 3; the owner's "Yes on everything", Nov 13:
    every share is a post, and Home shows posts): everyone's, or with
    `among` (follows: Home's Following) the people somebody follows and
    theirs, their ids as a subquery (follows.home_items). A drawing shown in
    the gallery outside a post (the Pad's own, or anything shared before
    posts) is on its own page (/b/<id>) and its maker's page, never on Home.
    A cursor from a Home page opened before may name one: it is read as its
    time (_posts_before).

    ONE PERSON'S is not read here any more: a post's page showed "More from"
    its author through this until Nov 20 (the Calm Post Page: the owner's
    "Bluesky looks simpler. Most because there aren't the more from images");
    their page's Posts tab is person_page's, below.

    MUTES (C, quiet everywhere): Home, Following and Everyone alike leave
    out the people the viewer muted, in the query, so its pages stay whole.

    REPOSTS (reposts.py; the owner's "All yes", Nov 14): Home's Following
    (`among`) holds the reposts of the people you follow and yours, merged
    newest first under the one cursor, each the original's card with who
    reposted it; never by somebody muted or of their post. Everyone holds
    posts only. THE SAME POST TWICE IN ONE PAGE SHOWS ONCE, the newest
    (reposts.once): the cursor is where the page ended before that."""
    from .mutes import muted_ids
    from .safety import hidden_ids
    at = _uncursor(before) if before else None
    hidden = hidden_ids(viewer) | muted_ids(viewer)
    posts, more = _posts_before(at, limit, None, hidden, viewer, among)
    out = [_entry(p, who) for p, who in posts]
    if among is not None and viewer is not None:
        from .reposts import reposts_before
        shared, more_r = reposts_before(at, limit, viewer, hidden, among=among)
        out = sorted(out + shared, key=lambda e: (e["at"], e["key"]), reverse=True)
        more = len(out) > limit or more or more_r
    page = out[:limit]
    from .reposts import once
    return once(page), (_cursor(page[-1]) if more and page else None)


def person_page(person, viewer, before=None, limit=PAGE):
    """A page of one person's posts and reposts, newest first, for their
    profile's Posts tab (the map's step 4; reposts, the owner's "All yes",
    Nov 14): (entries, next cursor or None). Their drawings shown outside a
    post are their Gallery's. Home's own cursor and its rules for one
    person's: nobody a block hides either way, nothing taken down but to its
    own author, who sees it with the note (a repost of anything taken down,
    never); a mute leaves it as it is (their page is what the viewer went
    to). A repost is the original's card with "Mira Lopez reposted" ("You
    reposted" on your own); the same post twice in one page shows once."""
    from .reposts import once, reposts_before
    from .safety import hidden_ids
    at = _uncursor(before) if before else None
    if before and at is None:
        return [], None
    hidden = hidden_ids(viewer)
    rows, more = _posts_before(at, limit, person, hidden, viewer)
    shared, more_r = reposts_before(at, limit, viewer, hidden, person=person)
    out = sorted([_entry(p, who) for p, who in rows] + shared, key=lambda e: (e["at"], e["key"]), reverse=True)
    more = len(out) > limit or more or more_r
    page = out[:limit]
    return once(page), (_cursor(page[-1]) if more and page else None)


def drawbacks(posts, viewer):
    """DRAW BACK, for a page of posts (`posts`, the site's rows): {"n": {post
    id: how many draw-backs it has}, "on": {a draw-back's id: {"url", "first",
    "who"} of the post it answers, or {"gone": True} once that post is not
    there for this viewer; with "own" when it is its maker's own}}. Counted
    as the comments are counted: nothing
    taken down, and nobody either side of a block with the viewer. AND
    NOTHING ITS MAKER HID FROM HER POST (Her say, Nov 20: drawn_on_hidden_at),
    for anybody, her too: the count is what everyone sees."""
    from .models import Block
    ids = [p.id for p in posts if getattr(p, "id", None) is not None]
    out = {"n": {}, "on": {}}
    if not ids:
        return out
    sess = site().session()
    q = (sa.select(Post.drawn_on_id, sa.func.count(Post.id))
         .join(Person, Person.id == Post.person_id)
         .where(Post.drawn_on_id.in_(ids), Post.taken_down_at.is_(None), Person.taken_down_at.is_(None),
                Post.drawn_on_hidden_at.is_(None)))
    if viewer is not None:
        q = q.where(~sa.exists().where(sa.or_(sa.and_(Block.blocker_id == viewer.id, Block.blocked_id == Post.person_id),
                                              sa.and_(Block.blocker_id == Post.person_id, Block.blocked_id == viewer.id))))
    out["n"] = dict(sess.execute(q.group_by(Post.drawn_on_id)).all())
    answers = [p for p in posts if getattr(p, "is_drawback", False)]
    on_ids = {p.drawn_on_id for p in answers if p.drawn_on_id is not None}
    rows = {}
    if on_ids:
        for orig, owner in sess.execute(sa.select(Post, Person).join(Person, Person.id == Post.person_id)
                                        .where(Post.id.in_(on_ids))).all():
            hidden = (orig.taken_down_at is not None or owner.taken_down_at is not None
                      or (viewer is not None and between(viewer, owner)))
            rows[orig.id] = None if hidden else {"url": url_for("social.post_page", public_id=orig.public_id),
                                                 "first": first_name(owner.display_name), "who": owner}
    for p in answers:
        got = rows.get(p.drawn_on_id) if p.drawn_on_id is not None else None
        # ON YOUR OWN DRAWING (the owner's "All yes", Nov 19, after "it shows
        # me responding to me"): "Drew back on their own drawing", one face.
        out["on"][p.id] = dict(got, own=got["who"].id == p.person_id) if got else {"gone": True}
    return out


#: HER SAY, WHO CAN DRAW BACK ON A POST: what its maker may choose, in the
#: pill's order. "everyone" is kept as nothing (Post.drawback_by).
WHO = ("everyone", "follow", "nobody")


def drawback_by(post):
    """Who can draw back on `post`, as its maker chose: "everyone" (where
    every post starts, and every post from before the choice), "follow" or
    "nobody"."""
    by = getattr(post, "drawback_by", None)
    return by if by in WHO else "everyone"


def open_to(posts, viewer):
    """HER SAY, WHO CAN DRAW BACK (the owner's "All yes to everything", Nov
    20, to the Her say mock): the ids of those of `posts` (the site's rows)
    whose maker lets `viewer` draw back on them. THE ONE RULE that the row's
    pen, the answer bar's Draw back, the composer's way in (post_drawback)
    and the post itself (_drawing_back) all read:

    - its maker always can, whatever it is set to (on "nobody" too: the
      mock's choice 6);
    - "everyone", where every post starts, is anybody signed in;
    - "follow" is whoever its maker follows NOW (unfollowed, the pen goes;
      what they drew back before stays), read once for the page;
    - "nobody" is nobody else.

    Whether its drawing CAN be drawn back on is another question
    (drawback.drawable), and so is whether the viewer may see the post at
    all (reposts.quotable): this is only her say."""
    out, ask = set(), {}
    for p in posts:
        pid = getattr(p, "id", None)
        if pid is None:
            continue
        by = drawback_by(p)
        if by == "everyone" or (viewer is not None and p.person_id == viewer.id):
            out.add(pid)
        elif by == "follow" and viewer is not None:
            ask.setdefault(p.person_id, []).append(pid)
    if ask:
        from .follows import followers_among
        for maker in followers_among(viewer, list(ask)):
            out.update(ask[maker])
    return out


def hands_said(posts, drawings, viewer):
    """WHAT A DRAW-BACK SAYS OF ITS HANDS (drawback.py; the walkthrough's
    mocks, choice 6, the owner's "all yes", Nov 19), for a page of posts:
    {a draw-back's id: {"parts": [ms, ...] in the order they play, "total":
    their sum, "people": how many people they are, "by": "Ana + Theo" for
    its play button, or None}}. Its line
    says the parts ("Drawn in 15 sec + 5 sec"), its play button who and the
    whole ("Ana + Theo · 20 sec").

    THE NAMES ARE SAID ONLY WHEN EVERY HAND CAN BE NAMED TO THIS VIEWER: each
    still here, not taken down, and no block either way; otherwise the play
    button says the time as any card does. One person's own two sittings
    (a draw-back on their own drawing) name nobody: the card says whose it is.

    FROM BEFORE THE HANDS WERE KEPT (hands_json empty), said from the two
    drawings' stored lines while the original is there and is one hand's
    (drawback.hands_from_lines; `drawings` is the page's describe_posts, the
    original's asked for when it is not on the page); otherwise nothing, and
    the card says what its drawing says, as before."""
    from .drawback import by_words, hands_from_lines, read_hands
    answers = [p for p in posts if getattr(p, "is_drawback", False) and getattr(p, "id", None) is not None]
    if not answers:
        return {}
    sess = site().session()
    got = {p.id: read_hands(getattr(p, "hands_json", None)) for p in answers}
    old = [p for p in answers if not got[p.id] and p.drawn_on_id is not None and p.drawn_on_owner_id is not None]
    if old:
        origs = {o.id: o for o in sess.execute(sa.select(Post).where(Post.id.in_({p.drawn_on_id for p in old}))).scalars()}
        lines = dict(drawings)
        ask = [o.skribl_id for o in origs.values() if o.skribl_id and not o.is_drawback and o.skribl_id not in lines]
        if ask:
            from skribl import describe_posts
            lines.update(describe_posts(ask, viewer_id=viewer.public_id if viewer else None))
        for p in old:
            o = origs.get(p.drawn_on_id)
            if o is None or o.is_drawback or o.taken_down_at is not None:
                continue
            got[p.id] = hands_from_lines((lines.get(o.skribl_id) or {}).get("line"), (lines.get(p.skribl_id) or {}).get("line"),
                                         p.drawn_on_owner_id, p.person_id)
    ids = {pid for h in got.values() if h for pid, _ in h if pid is not None}
    people = {x.id: x for x in sess.execute(sa.select(Person).where(Person.id.in_(ids))).scalars()} if ids else {}
    out = {}
    for p in answers:
        h = got.get(p.id)
        if not h or len(h) < 2:
            continue
        names, seen = [], set()
        for pid, _ in h:
            who = people.get(pid)
            if who is None or who.taken_down_at is not None or (viewer is not None and between(viewer, who)):
                names = None
                break
            if pid not in seen:
                seen.add(pid)
                names.append(first_name(who.display_name))
        out[p.id] = {"parts": [ms for _, ms in h], "total": sum(ms for _, ms in h),
                     # How many people the hands are, for a line with too many
                     # parts to say one by one (one gone counts as one more).
                     "people": len({pid for pid, _ in h if pid is not None}) + sum(1 for pid, _ in h if pid is None),
                     "by": by_words(names) if names and len(names) > 1 else None}
    return out


def said_line(line, said):
    """A draw-back's line as its players are handed it (Skribl's line, with
    what hands_said found): "drawn" the hands' own times together, "parts"
    each of them, "by" who they are. None stays None: Skribl does not know
    the drawing's line."""
    if not line or not said:
        return line
    out = dict(line, drawn=said["total"], parts=said["parts"], people=said["people"])
    if said.get("by"):
        out["by"] = said["by"]
    return out


def cards(entries, viewer, words=True, aligned=False):
    """What each card shows: the post (a drawing shown outside a post is a
    post whose words are its title), its author, and its drawing's size, line,
    plays, ground and whether it is on a picture as Skribl describes them for
    `viewer` (None where it cannot be had: deleted or withheld since, or a
    quote of words alone, which has none); how many comments; where it goes,
    and its Delete. A REPOST's card (reposts.py) is the original's, with who
    reposted it (`by`); a QUOTE's carries the original small (`quote`).
    `words`: whether the cards show their words, whose mentions are then
    read (mentions.links, one read for the page); a tile (the Gallery's, a
    draw-back's) shows none, and reads none. A COMMENT'S CARD (kind "c": a
    comment or a reply reposted, or kept in Bookmarks; the comment thread,
    step 3) is comments.world_cards's, in its place among them; one the
    viewer is not shown has no card, or with `aligned` (one for each entry:
    follows.home_cards puts its markers between them) None in its place."""
    from skribl import describe_posts
    from .comments import counts, world_cards
    from .likes import stats
    from .mutes import muted_ids
    from .reposts import Quoted, makers_of, stats as repost_stats
    every = [e if isinstance(e, dict) else _entry(*e) for e in entries]
    # A COMMENT OR A REPLY OUT IN THE WORLD (the comment thread, step 3:
    # reposted, or kept in Bookmarks) is a card of its own, made by
    # comments.world_cards (the way to it, then it); one this viewer is not
    # shown makes none. The posts and drawings are read together below.
    said_c = iter(world_cards([e for e in every if e["kind"] == "c"], viewer))
    entries = [e for e in every if e["kind"] != "c"]
    # WHOM THIS VIEWER MUTED (mutes): their ⋯ says Unmute. Read once a request.
    muted = muted_ids(viewer)
    # WHAT THE QUOTES QUOTE (reposts): the originals in one read, their
    # drawings in the page's one describe_posts below.
    quoted = Quoted([e["post"] for e in entries if e["kind"] == "p"], viewer)
    # A drawing shown outside a post is asked too, in the same one read: the
    # listing it came from says no ground and no picture, and a tile lays
    # its box in them as a post's does (_gallery.html plate_ground and
    # plate_fill).
    drawings = describe_posts([e["post"].skribl_id if e["kind"] == "p" else e["sk"]["id"] for e in entries]
                              + quoted.skribls, viewer_id=viewer.public_id if viewer else None)
    makers = makers_of(drawings, quoted.drawing_ids)
    # HOW MANY COMMENTS each card says (phase 2; a drawing's too, since every
    # drawing has comments): what its page will show this viewer, so a block
    # or a takedown is neither shown nor counted.
    said = counts(viewer, posts=[e["post"].id for e in entries if e["kind"] == "p"],
                  drawings=[e["sk"]["id"] for e in entries if e["kind"] == "s"])
    # HOW MANY LIKES, and whether one is this viewer's (likes, phase 2): every
    # card's at once, by the same rules (nobody hidden counted).
    liked = stats(viewer, posts=[e["post"].id for e in entries if e["kind"] == "p"],
                  drawings=[e["sk"]["id"] for e in entries if e["kind"] == "s"])
    # WHICH ARE THIS VIEWER'S BOOKMARKS (bookmarks): their ⋯ says Remove
    # bookmark. Theirs alone, and never how many: one read a kind.
    from .bookmarks import marked
    kept = marked(viewer, posts=[e["post"].id for e in entries if e["kind"] == "p"],
                  drawings=[e["sk"]["id"] for e in entries if e["kind"] == "s"])
    # HOW MANY REPOSTS AND QUOTES, and whether a repost is this viewer's
    # (reposts): every card's at once, counted by the same rules.
    shared = repost_stats(viewer, posts=[e["post"].id for e in entries if e["kind"] == "p"],
                          drawings=[e["sk"]["id"] for e in entries if e["kind"] == "s"])
    # WHOM THEIR WORDS MENTION (mentions): every card's in one read, so each
    # @handle that is somebody is a link to them (a drawing's title takes none).
    from .mentions import links
    named = links(posts=[e["post"].id for e in entries if e["kind"] == "p"]) if words else {}
    # DRAW BACK (drawback.py): how many draw-backs each post has, and on a
    # draw-back whose drawing it answers; one read each for the page.
    backs = drawbacks([e["post"] for e in entries if e["kind"] == "p"], viewer)
    # ...and whose maker lets this viewer draw back (Her say: open_to).
    may = open_to([e["post"] for e in entries if e["kind"] == "p"], viewer)
    # ...and what each draw-back says of its hands (hands_said): its line's
    # "drawn in" is their own times, never the joined drawing's, in which
    # hers plays squeezed.
    whose = hands_said([e["post"] for e in entries if e["kind"] == "p"], drawings, viewer)
    made = {}
    for e in entries:
        who = e["who"]
        if e["kind"] == "p":
            p = e["post"]
            sk = drawings.get(p.skribl_id)
            if sk is not None and p.id in whose:
                # Nobody is named once the drawing it answers is gone for this
                # viewer: its card says "Drew back on a drawing" then, and its
                # play button the time alone.
                gone_ = (backs["on"].get(p.id) or {}).get("gone")
                sk = dict(sk, line=said_line(sk.get("line"), dict(whose[p.id], by=None) if gone_ else whose[p.id]))
            url = url_for("social.post_page", public_id=p.public_id)
            gone = url_for("social.post_delete", public_id=p.public_id)
        else:
            # A drawing shown outside a post: as Skribl describes it now (its
            # ground and whether it is on a picture too). The Gallery's read
            # names its id and visibility alone (gallery._read), so one Skribl
            # no longer describes is no card there; an item that came whole
            # (a listing's own) stays as read, its ground and picture not known.
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
        by = e.get("by")
        mine = viewer is not None and viewer.id == who.id
        # WHETHER ITS DRAWING CAN BE DRAWN BACK ON AT ALL (a drawing of one
        # page, no recolours: drawback.drawable). A photo or music is no bar
        # since the owner's yes, Nov 19: a draw-back keeps the author's.
        # Recolours are the post's `undrawable`, read when it was made; a
        # post from before that keeps its pen, answered when opened ("photo"
        # and "music" recorded before the yes bar nothing now).
        can_back = (e["kind"] == "p" and not down and sk is not None and sk.get("kind") == "pad"
                    and getattr(p, "undrawable", None) not in ("pages", "recolors"))
        made[id(e)] = {"post": p, "who": who, "sk": sk, "kind": e["kind"], "down": down,
                       "plays": plays_text(sk["views"]) if sk else None,
                       "comments": said.get(key, 0),
                       "likes": liked.get(key, {"n": 0, "mine": False, "at": None, "marks": []}),
                       "like": (url_for("social.like_post", public_id=p.public_id) if e["kind"] == "p"
                                else url_for("social.like_drawing", skribl_id=p.skribl_id)),
                       "url": url, "delete": gone,
                       # BOOKMARK in its ⋯ where one can be kept (bookmarks.py:
                       # what is open to everybody, as a like): never on what is
                       # taken down, nor a drawing kept link-only, which its maker
                       # alone sees.
                       "markable": not down and (e["kind"] == "p" or (sk or {}).get("visibility") == "public"),
                       "marked": key in kept,
                       # REPOSTS AND QUOTES (reposts.py): how many and whether a
                       # repost is theirs; a post can be reposted and quoted, a
                       # drawing shown outside a post quoted alone, and neither
                       # once taken down or kept link-only (where one can be
                       # bookmarked, one can be quoted).
                       "reposts": shared.get(key, {"n": 0, "mine": False}),
                       "repost": url_for("social.repost_post", public_id=p.public_id) if e["kind"] == "p" else None,
                       "quoted_url": (url_for("social.quoted_post", public_id=p.public_id) if e["kind"] == "p"
                                      else url_for("social.quoted_drawing", skribl_id=p.skribl_id)),
                       # WHO REPOSTED IT, on a repost's card (Home's Following, a
                       # Posts tab): "Mira Lopez reposted", "You reposted".
                       "by": by, "by_me": by is not None and viewer is not None and by.id == viewer.id,
                       "quote": (quoted.card(p, drawings, makers) if getattr(p, "is_quote", False) else None),
                       # MENTIONS (mentions.py): {as typed, in small letters:
                       # their handle now}, which said() makes links of.
                       "mentions": named.get(("p", p.id), {}) if e["kind"] == "p" else {},
                       "profile": profile_url(who.handle),
                       "mine": mine,
                       "muted": who.id in muted,
                       # DRAW BACK: the pen in the row where it can be done
                       # (`can_back`, above) AND ITS MAKER LETS THIS VIEWER
                       # (Her say, Nov 20: open_to; no pen at all for
                       # somebody who can't, as on a Flip), how many there
                       # are, and on a draw-back the post it answers and
                       # whose that is.
                       "drawable": can_back and p.id in may,
                       # HER SAY: on your own post that can be drawn back on,
                       # who you let ("everyone", "follow", "nobody"): the
                       # pill in its ⋯ and the quiet line on its page read
                       # it. None on anybody else's, and where nothing can be
                       # drawn back on (a Flip, words alone).
                       "who_draws": drawback_by(p) if can_back and mine else None,
                       "drawbacks": backs["n"].get(p.id, 0) if e["kind"] == "p" else 0,
                       "drawn_on": backs["on"].get(p.id) if e["kind"] == "p" else None}
    out = []
    for e in every:
        card = next(said_c) if e["kind"] == "c" else made[id(e)]
        if card is not None or aligned:
            out.append(card)
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
    """Home for somebody signed in: the row that opens the composer (the
    composer itself, its editors' compose addresses with them, is on every
    page: _compose.html), and the first page of the feed. None for nobody
    signed in, whose Home is the first visit."""
    me = current_person()
    if me is None:
        return None
    # FOLLOWING OR EVERYONE (follows): their own pick, else Following once
    # they follow somebody, Everyone before that.
    from .follows import home_cards, home_items, home_shows
    items, nxt, show = home_items(me, home_shows(me))
    note = request.args.get("note")
    return _page("feed.html", here="home", cards=home_cards(items, me), next=nxt, show=show, token=csrf_token(),
                 note=note if note in NOTES else None)


def register(bp, skribl_blueprint="skribl"):
    """Add the posts' routes to the site's blueprint."""

    @bp.get("/p/<public_id>/drawback")
    @_rests(json_answer=True)
    def post_drawback(public_id):
        """DRAW BACK, for the composer: the drawing to lay under the pen
        ({payload, first}), open to the person signed in as a like asks
        (reposts.quotable), one its maker lets them draw back on (Her say:
        open_to) and one that can be drawn back on (drawback.drawable);
        "drawback_gone", "drawback_closed" or "drawback_unsupported"
        otherwise. Only what Skribl would serve this viewer (read_payload)."""
        from skribl import read_payload
        from .drawback import drawable
        from .reposts import quotable
        me = current_person()
        if me is None:
            return _json_error("signed_out", 401)
        on = quotable(me, "p", public_id) if 0 < len(public_id) <= 32 else None
        original = (read_payload(on.post.skribl_id, viewer_id=me.public_id)
                    if on is not None and on.post is not None and on.post.skribl_id else None)
        if original is None:
            return _json_error("drawback_gone", 404)
        # HER SAY: closed to them since the page they pressed was made (the
        # pen is not on a page made now). Said kindly, and not why.
        if on.post.id not in open_to([on.post], me):
            return _json_error("drawback_closed", 403)
        why = drawable(original)
        if why:
            return _json_error("drawback_unsupported", 400, why=why)
        resp = jsonify({"payload": original, "first": first_name(on.owner.display_name), "own": on.owner.id == me.id})
        resp.headers["Cache-Control"] = "private, no-store"
        return resp

    @bp.post("/posts")
    @_rests(json_answer=True)
    def post_new():
        """A post: the words, and the drawing the editor handed back, or
        the words alone. The skribl and the row land in one transaction, or
        neither does. A QUOTE
        (reposts.py; the composer's Quote) names what it quotes, {"quote": a
        post's address}, {"quote_drawing": a drawing's id} or (the comment
        thread, step 3) {"quote_comment": a comment's address}, open to them
        as a like asks; its words, its own drawing, or both."""
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
        quoting, refusal = _quoting(me, body)
        if refusal is not None:
            return refusal
        # HER SAY, WHO CAN DRAW BACK ON IT (the composer's quiet line and its
        # pill): {"drawback_by": "follow" or "nobody"}; nothing, or
        # "everyone", leaves it open. Anything else is refused, never read
        # as open: she asked for something.
        by = body.get("drawback_by")
        if by is not None and by not in WHO:
            return _json_error("bad", 400)
        by = None if by == "everyone" else by
        if body.get("draw_back") is not None:
            # DRAW BACK (drawback.py): the answer's strokes, joined here to
            # the original's, never beside a quote or an older drawing.
            if quoting is not None or body.get("skribl") is not None:
                return _json_error("one_drawing", 400)
            joined, refusal = _drawing_back(me, body.get("draw_back"), body.get("payload"))
            if refusal is not None:
                return refusal
            body = dict(body, payload=joined["payload"])
            quoting = joined["columns"]
        if body.get("skribl") is not None:
            # ONE OF YOUR OLDER DRAWINGS (the composer's Yours, Drawings),
            # never beside a new one: a post holds one drawing.
            if body.get("payload") is not None:
                return _json_error("one_drawing", 400)
            return _post_older(me, words, body.get("skribl"), quoting, by)
        payload = body.get("payload")
        if payload is None and (quoting is not None or words):
            # WORDS ALONE: a quote of words alone (the original brings its
            # drawing; with no words it would be a repost, which the sheet's
            # Repost makes), or a post of words alone (the owner's "I like
            # your pick", Nov 16, to A on the words-only mock: a person can
            # post without a drawing or a Flip, as a comment can).
            if not words:
                return _json_error("quote_empty", 400)
            row = Post(public_id=new_public_id(8), person_id=me.id, words=words, skribl_id=None, **(quoting or {}))
            sess = site().session()
            sess.add(row)
            sess.flush()
            mentioned(row)
            return jsonify({"ok": True, "post": row.public_id,
                            "go": url_for("social.post_page", public_id=row.public_id)})
        if payload is None:
            # Nothing at all: no words, no drawing, nothing quoted.
            return _json_error("empty", 400)
        if not isinstance(payload, dict):
            return _json_error("no_drawing", 400)
        from skribl import SkriblRejected, SkriblUnavailable, create_post
        drawing = dict(payload)
        # WHAT THE PAYLOAD SAYS, AND NOTHING ELSE: public only if it says so
        # (the editor's "Show in the Skribls gallery", which this site's
        # composer no longer asks for: the header), its caption only with it;
        # the title is the post's own first words (set here, not trusted).
        gallery = drawing.get("visibility") == "public"
        drawing["visibility"] = "public" if gallery else "unlisted"
        drawing["title"] = title_from(words)
        caption = str(drawing.get("caption") or "").strip() if gallery else ""
        if caption:
            drawing["caption"] = caption
        else:
            drawing.pop("caption", None)
        # WHETHER IT CAN BE DRAWN BACK ON (drawback.drawable), read from the
        # drawing as it is sent, before Skribl stores its media apart.
        from .drawback import drawable
        undrawable = drawable(drawing)
        try:
            made = create_post(drawing, author_id=me.public_id)
        except SkriblRejected as exc:
            return _json_error("rejected", exc.status if 400 <= exc.status < 500 else 400,
                               message=exc.message)
        except SkriblUnavailable:
            return _json_error("busy", 503)
        row = Post(public_id=new_public_id(8), person_id=me.id, words=words or "",
                   skribl_id=made.public_id, undrawable=undrawable, drawback_by=by, **(quoting or {}))
        sess = site().session()
        sess.add(row)
        sess.flush()
        mentioned(row)
        return jsonify({"ok": True, "post": row.public_id,
                        "go": url_for("social.post_page", public_id=row.public_id)})

    def _drawing_back(me, oid, payload):
        """A draw-back's drawing and columns ({"payload", "columns"}), or a
        refusal: the post `oid` names, open to `me` as a like asks
        (reposts.quotable) and one its maker lets them draw back on (Her
        say: open_to, asked again here, so a draw-back begun while it was
        open and posted after it closed is not posted), its drawing one
        they may see and one that can be drawn back on, and `payload` the
        strokes drawn on its shape."""
        import json
        from skribl import read_payload
        from .drawback import _points, drawable, hands, join, same_shape
        from .reposts import quotable
        if not isinstance(oid, str) or not (0 < len(oid) <= 32):
            return None, _json_error("drawback_gone", 404)
        on = quotable(me, "p", oid)
        if on is None or on.post is None or not on.post.skribl_id:
            return None, _json_error("drawback_gone", 404)
        if on.post.id not in open_to([on.post], me):
            return None, _json_error("drawback_closed", 403)
        # Her photo and song as data, to post again with the two (the
        # author's background and music: the owner's yes, Nov 19).
        original = read_payload(on.post.skribl_id, viewer_id=me.public_id, inline_media=True)
        if original is None:
            return None, _json_error("drawback_gone", 404)
        if not isinstance(payload, dict) or not _points((payload.get("frames") or [{}])[0]
                                                        if isinstance(payload.get("frames"), list) else {}):
            return None, _json_error("no_drawing", 400)
        # Whose drawing it is that can't be joined yet, so the composer can
        # say how to fix it (a picture of yours can come out; hers can't).
        why = drawable(original)
        if why:
            return None, _json_error("drawback_unsupported", 400, why=why, on="theirs")
        why = drawable(payload, answer=True)
        if why:
            return None, _json_error("drawback_unsupported", 400, why=why, on="yours")
        # YOU ADD, NEVER ERASE (the owner's "All yes", Nov 19): a draw-back
        # replays as one drawing, so an eraser in his would erase hers too.
        # The Pad turns the eraser off while drawing back; this holds the line.
        if any(p.get("erase") for p in _points(payload["frames"][0])):
            return None, _json_error("drawback_unsupported", 400, why="erase", on="yours")
        if not same_shape(original, payload):
            return None, _json_error("drawback_shape", 400)
        # WHOSE HANDS, AND HOW LONG EACH DREW (drawback.hands; the walkthrough's
        # mocks, choice 6): read from the two drawings before the join squeezes
        # hers, so the line can say "Drawn in 15 sec + 5 sec".
        whose = hands(original, payload, getattr(on.post, "hands_json", None), on.owner.id, me.id)
        return {"payload": join(original, payload),
                "columns": {"is_drawback": True, "drawn_on_id": on.post.id, "drawn_on_owner_id": on.owner.id,
                            "hands_json": json.dumps(whose)}}, None

    def mentioned(row):
        """MENTIONS (mentions.py): the people its words name, written beside
        the post in the same transaction, once its row is flushed (its id and
        its time are the mentions' too)."""
        from .mentions import write_post
        write_post(row)
        site().session().flush()
        # A QUOTE'S NUDGE, where its maker's device has Reposts and quotes on
        # (push.py), or Mentions where it names them too.
        if row.quoted_owner_id is not None:
            from .push import note
            note(row.quoted_owner_id, row.person_id, "reposts")
        # A DRAW-BACK'S NUDGE, under Replies: it answers them, in a drawing.
        if getattr(row, "drawn_on_owner_id", None) is not None:
            from .push import note
            note(row.drawn_on_owner_id, row.person_id, "replies")

    def _quoting(me, body):
        """What a post quotes, as its row's columns, or None for a post that
        quotes nothing: (columns or None, refusal or None). A post (by its
        address), a drawing shown outside a post (by its id, under the
        drawing's lock, so a quote never lands as it moves into a post), or
        since the comment thread's step 3 a comment or a reply (by its
        address: reposts.comment_open), open to them (reposts.quotable: no
        block either way, not taken down, a drawing public); one at most."""
        from .reposts import comment_open, quotable
        post_id, drawing_id, comment_id = body.get("quote"), body.get("quote_drawing"), body.get("quote_comment")
        if post_id is None and drawing_id is None and comment_id is None:
            return None, None
        if sum(x is not None for x in (post_id, drawing_id, comment_id)) > 1:
            return None, _json_error("one_quote", 400)
        if comment_id is not None:
            # A COMMENT OR A REPLY (the comment thread, step 3; the owner's yes
            # to quoting one): one they may see, no place, nothing taken down.
            got = comment_open(me, comment_id) if isinstance(comment_id, str) and 0 < len(comment_id) <= 32 else None
            if got is None:
                return None, _json_error("quote_gone", 404)
            return {"is_quote": True, "quoted_comment_id": got["c"].id, "quoted_owner_id": got["c"].person_id}, None
        oid = post_id if post_id is not None else drawing_id
        if not isinstance(oid, str) or not (0 < len(oid) <= 32):
            return None, _json_error("quote_gone", 404)
        if drawing_id is not None:
            drawing_lock(oid)
        on = quotable(me, "p" if post_id is not None else "s", oid)
        if on is None:
            # Gone, taken down, kept link-only, or a block either way: as gone
            # as one never made, saying nothing of which.
            return None, _json_error("quote_gone", 404)
        return {"is_quote": True, "quoted_post_id": on.post.id if on.post is not None else None,
                "quoted_drawing_id": on.drawing if on.post is None else None,
                "quoted_owner_id": on.owner.id}, None

    def _post_older(me, words, skribl_id, quoting=None, by=None):
        """ONE DRAWING, ONE CONVERSATION: one of `me`'s older drawings as a
        post (the header's rule). The drawing is theirs, shared (public or
        link-only), never a post's, a face or a comment's; taken down
        (withheld) it is nobody's to post. In one transaction: the post's row,
        naming that skribl, and the drawing's hearts, comments and bookmarks
        moved onto it. Nothing is made in Skribl and nothing about the drawing changes
        there: its title, caption and visibility stay its own."""
        from skribl import describe_posts
        from .bookmarks import move_drawing_bookmarks
        from .comments import move_drawing_comments
        from .likes import move_drawing_likes
        from .models import Comment
        from .reposts import move_drawing_quotes
        sid = skribl_id if isinstance(skribl_id, str) else ""
        if not (0 < len(sid) <= 32):
            return _json_error("drawing_gone", 404)
        sk = describe_posts([sid], viewer_id=me.public_id).get(sid)
        sess = site().session()
        if (not sk or str(sk.get("user_id") or "") != me.public_id
                or sk.get("visibility") not in ("public", "unlisted")
                or sess.execute(sa.select(Comment.id).where(Comment.skribl_id == sid).limit(1)).first() is not None
                or sess.execute(sa.select(Person.id).where(Person.id == me.id, Person.face_id == sid)).first()
                is not None):
            # Somebody else's, gone, withheld, a face or a comment's drawing:
            # as gone as one never made, saying nothing of which.
            return _json_error("drawing_gone", 404)
        drawing_lock(sid)
        if sess.execute(sa.select(Post.id).where(Post.skribl_id == sid)).first() is not None:
            # In a post already (posted a moment ago, another tab): sharing
            # it again will be a repost, a step of its own.
            return _json_error("drawing_posted", 409)
        if quoting is not None and quoting.get("quoted_drawing_id") == sid:
            # A post can't quote its own drawing.
            return _json_error("quote_gone", 404)
        # Whether it can be drawn back on (drawback.drawable), read from the
        # drawing as Skribl keeps it.
        from skribl import read_payload
        from .drawback import drawable
        kept = read_payload(sid, viewer_id=me.public_id)
        row = Post(public_id=new_public_id(8), person_id=me.id, words=words or "", skribl_id=sid,
                   # Hidden from the Gallery by its maker (link-only): the
                   # post's drawing stays out of it, as the eye said.
                   gallery_hidden_at=None if sk.get("visibility") == "public" else utcnow(),
                   undrawable=drawable(kept) if kept is not None else None, drawback_by=by, **(quoting or {}))
        sess.add(row)
        sess.flush()
        move_drawing_comments(sid, row.id)
        move_drawing_likes(sid, row.id)
        move_drawing_bookmarks(sid, row.id)
        # ...and its quotes quote the post (reposts: one drawing, one conversation).
        move_drawing_quotes(sid, row.id)
        mentioned(row)
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
        """A post's page, or a drawing's: the draw-backs on it and its
        comments (a post's, or since the owner's yes on Nov 12, a drawing's:
        whatever is opened has them). NO "MORE FROM" its author (the Calm
        Post Page, the owner's "All yes to everything", Nov 20): their face
        and name open their page."""
        from . import comments
        on = (comments.On(card["who"], post=card["post"]) if card["kind"] == "p" else
              comments.On(card["who"], drawing=card["post"].skribl_id, sk=card["sk"]))
        cm = comments.section(on, me, skribl_blueprint)
        # WHO LIKED IT is the maker's alone (likes): the line and the sheet's
        # rows; nothing of likes on what is taken down.
        from .likes import for_maker
        lk = for_maker(on, me) if not card["down"] else None
        # DRAW-BACKS ON IT (Draw back, step 2): newest first, a strip of their
        # drawings under the row, each opening its own page; nobody hidden
        # from this viewer, nothing taken down. HER SAY (Nov 20): one its
        # maker hid from her post (drawn_on_hidden_at) is on nobody's strip
        # but her own, where it stays, faded, with its eye, so she can bring
        # it back. `shown` is how many everyone sees, `hidden` hers alone.
        backs, shown, hidden = [], 0, 0
        if card["kind"] == "p":
            from .safety import hidden_ids
            hid = sorted(hidden_ids(me))
            q = (sa.select(Post, Person).join(Person, Person.id == Post.person_id)
                 .where(Post.drawn_on_id == card["post"].id, Post.taken_down_at.is_(None))
                 .order_by(Post.created_at.desc(), Post.id.desc()).limit(BACKS))
            if hid:
                q = q.where(Post.person_id.notin_(hid))
            if not card["mine"]:
                q = q.where(Post.drawn_on_hidden_at.is_(None))
            got = site().session().execute(q).all()
            backs = [c for c in cards([_entry(pp, who) for pp, who in got], me, words=False) if c and c["sk"]]
            hidden = sum(1 for c in backs if c["post"].drawn_on_hidden_at is not None)
            shown = len(backs) - hidden
        # The page's token for everybody: Report is anybody's (piece 5).
        return _page("post.html", here="post", card=card, backs=backs, backs_shown=shown, backs_hidden=hidden,
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

    def _eye_asked(key="gallery"):
        """(me, in the Gallery or not), or the refusal: the eye's guards, as
        every change's (the token and Origin, signed in, the limit), and a
        body that says {"gallery": true} or false (`key`: a draw-back's eye
        on her strip says {"shown": ...})."""
        if not origin_ok() or not token_ok():
            return None, None, _json_error("stale", 403)
        me = current_person()
        if me is None:
            return None, None, _json_error("signed_out", 401)
        if over("gallery", "person|" + me.public_id):
            return None, None, _json_error("limited", 429)
        body = request.get_json(silent=True)
        want = body.get(key) if isinstance(body, dict) else None
        if not isinstance(want, bool):
            return None, None, _json_error("bad", 400)
        return me, want, None

    @bp.post("/p/<public_id>/drawback-by")
    @_rests(json_answer=True)
    def post_drawback_by(public_id):
        """HER SAY, WHO CAN DRAW BACK ON HER POST (the owner's "All yes to
        everything", Nov 20, to the Her say mock): the pill in her own
        post's ⋯, {"by": "everyone", "follow" or "nobody"}. Hers alone to
        set (anybody else's, or none, is as gone as one never made), on a
        post with a drawing. Nothing else changes: the draw-backs it has
        stay where they are, and nobody is told. The eye's guards (the
        token and Origin, signed in, its limit: a person's own switches)."""
        if not origin_ok() or not token_ok():
            return _json_error("stale", 403)
        me = current_person()
        if me is None:
            return _json_error("signed_out", 401)
        if over("gallery", "person|" + me.public_id):
            return _json_error("limited", 429)
        body = request.get_json(silent=True)
        want = body.get("by") if isinstance(body, dict) else None
        if not isinstance(want, str) or want not in WHO:
            return _json_error("bad", 400)
        sess = site().session()
        row = sess.execute(sa.select(Post).where(Post.public_id == public_id)).scalar_one_or_none()
        if row is None or row.person_id != me.id or not row.skribl_id or row.taken_down_at is not None:
            return _json_error("gone", 404)
        row.drawback_by = None if want == "everyone" else want
        sess.flush()
        return jsonify({"ok": True, "by": want})

    @bp.post("/p/<public_id>/shown")
    @_rests(json_answer=True)
    def drawback_shown(public_id):
        """HER SAY, THE EYE ON HER OWN STRIP (the owner's "All yes to
        everything", Nov 20, to the Her say mock): a draw-back shown on the
        post it draws back on, or hidden from it ({"shown": false}), by that
        post's maker alone. The site's own flag on the draw-back
        (drawn_on_hidden_at): it leaves her post's strip and its count, for
        everybody, and nothing else of it changes (its maker's page, Home,
        its own page, its credit). Nobody is told. One taken down is
        nobody's to change; one whose original is gone has no post to be
        on. Answers how many her post shows now."""
        me, want, refusal = _eye_asked("shown")
        if refusal is not None:
            return refusal
        sess = site().session()
        row = sess.execute(sa.select(Post).where(Post.public_id == public_id)).scalar_one_or_none()
        if (row is None or not row.is_drawback or row.drawn_on_id is None or row.drawn_on_owner_id != me.id
                or row.taken_down_at is not None):
            return _json_error("gone", 404)
        row.drawn_on_hidden_at = None if want else (row.drawn_on_hidden_at or utcnow())
        sess.flush()
        orig = sess.get(Post, row.drawn_on_id)
        n = drawbacks([orig], me)["n"].get(orig.id, 0) if orig is not None else 0
        return jsonify({"ok": True, "shown": want, "n": n})

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
        # ITS COMMENTS, LIKES AND BOOKMARKS GO WITH IT, in code (phase 2,
        # bookmarks): only once delete_post has said it was theirs, since a
        # refused delete still commits.
        from .bookmarks import drop_drawing_bookmarks
        from .comments import drop_drawing_comments
        from .likes import drop_drawing_likes
        from .reposts import drop_drawing_quotes
        drop_drawing_comments(skribl_id)
        drop_drawing_likes(skribl_id)
        drop_drawing_bookmarks(skribl_id)
        # ...and its quotes let go of it, each saying it is gone (reposts).
        drop_drawing_quotes(skribl_id)
        sess.flush()
        return jsonify({"ok": True, "go": url_for("social.home", note="deleted_drawing")})


def drawing_lock(skribl_id):
    """ONE POST A DRAWING, AND ITS CONVERSATION WHOLE (the composer's Yours).
    On PostgreSQL, a transaction-scoped advisory lock keyed on the drawing,
    held until the request commits, taken by every write about a drawing
    shown outside a post: posting it (post_new), and a like or a comment on
    it (likes.set_like, comments.new_comment). Two posts of one drawing at
    once go one after the other, and the second finds it in a post; a like
    or a comment that meets the post waits for it, then finds the drawing a
    post's (gone), or lands first and moves with the rest. Skribl's drafts
    take theirs the same way (skribl/drafts.py). On SQLite the file's one
    writer never lets two such writes both go: the second waits, or is
    refused and changes nothing."""
    s = site().session()
    if s.get_bind().dialect.name != "postgresql":
        return
    n = int.from_bytes(hashlib.sha256(("social-drawing:" + str(skribl_id)).encode()).digest()[:8], "big",
                       signed=True)
    s.execute(sa.text("SELECT pg_advisory_xact_lock(:n)"), {"n": n})


def drop_post(author_public_id, row):
    """A post's comments and answers, its likes, its bookmarks, its reposts
    and its mentions, and its quotes letting go of it (phase 2, bookmarks,
    reposts and mentions, said here and not left to a cascade), its drawing (Skribl's
    delete_post, as its author; a quote of words alone has none) and its
    row. A drawing already gone is no reason to keep the words. Flushes
    nothing: the caller does, with whatever else goes in the same
    transaction."""
    from skribl import SkriblNotFound, delete_post
    from .bookmarks import drop_post_bookmarks
    from .comments import drop_post_comments
    from .likes import drop_post_likes
    from .mentions import drop_post_mentions
    from .reposts import drop_post_reposts
    drop_post_comments(row.id)
    drop_post_likes(row.id)
    drop_post_bookmarks(row.id)
    drop_post_reposts(row.id)
    drop_post_mentions(row.id)
    if row.skribl_id:
        try:
            delete_post(row.skribl_id, author_id=author_public_id)
        except SkriblNotFound:
            pass
    site().session().delete(row)
