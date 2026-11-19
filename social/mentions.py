"""Mentions (the map, part two, item 4; docs/SOCIAL-SITE.md section 17), from
the mentions mock and the owner's "All yes" (Nov 15, about 1:45 AM Mountain):
an @handle in a post or a comment links to that person, and tells them.

    /people/suggest?q=<what follows the @>
                        the list under the @ while it is typed (JSON
                        {people: [{handle, name, face}]}, four at most):
                        signed in only (401 otherwise), the site's limit
                        ("people") before anything is read

HOW A MENTION LOOKS (A): in a post's words, a comment's or an answer's, and
a quote's own words (a quote is a post), an @handle that is somebody is a
link to their page, in the small violet ink (--accent-ink), 600, never
underlined (social.css, "MENTIONS"). Nothing else in the words moves. A
handle that is nobody stays plain words, and so does every handle past the
first MOST distinct people in one post or comment. Where the words are
already one link (Activity's peek, a quote's small card, More from's tiles)
they stay plain.

WHAT IS KEPT (models.Mention, social_mentions): who was mentioned and the
handle as typed, written in the same transaction as the post or the comment
(posts.post_new, comments' new_comment) and never changed after: posts and
comments can't be edited, so a mention is fixed once posted. The link goes to
the person by their id, so a handle that changes later never breaks an old
mention ("@as-typed" opens their page as it is now). Posts written before
mentions keep their words plain: nothing works mentions out of old words.

THE WORDS, MADE SAFE FIRST (said()): the words are escaped as any words are,
and only the @handles a post or a comment keeps as its mentions become
links. A page reads every card's (or every comment's) mentions in one read
(links()), as Home's cards read their likes.

THE LIST UNDER THE @ (mentions.js, from the composer and a comment's box,
answers too): people you follow first, then anybody else, each whose handle
or any word of whose name starts with what follows the @, found as the
Gallery's search finds people (people.py, since finding people: the same
ways, the same way), each by name (suggest()); four at most. Nobody a block
hides either way, nobody taken down, never yourself. Each read is on an
index: your follows and their ways of being found, then everybody's ways
(ix_social_people_words_key), walked from where what was typed would sort,
a few rows at most. An @ alone: the people you follow, then anybody, by
name, on the handles' and the names' own indexes (ix_social_people_name_key).

WHO IS TOLD (activity.py): the person mentioned, in Activity, "Rook mentioned
you", a row each, their words under it in quotes; it lights the bell's dot,
as a comment does. Never yourself, never from anybody muted (quiet, as their
comments are), never through a block either way, never about anything taken
down or anything they cannot see. A comment that is already a row for them
(on their post, or answering them) is one row, the comment's; so is a quote
of what they made (the quote's).

DELETING IS REAL AND SAID IN CODE: a post goes with its mentions
(posts.drop_post), a comment with its own (comments._drop, every way a
comment goes), an account with the mentions of it and every mention it wrote
or that sat on what it owned (accounts.delete_person). The ON DELETE
CASCADEs are the net.
"""
import re

import sqlalchemy as sa
from flask import jsonify, render_template, request
from markupsafe import Markup, escape

from .accounts import _json_error, _rests, profile_url
from .models import Comment, Mention, Person, Post
from .safety import hidden_ids
from .security import current_person, over, site

#: An @handle in words: an @ with no letter, digit, _ or @ right before it
#: (not inside an email address or another word), then a handle's shape
#: (accounts.HANDLE_RE), with no letter, digit or _ right after it.
MENTION_RE = re.compile(r"(?<![A-Za-z0-9_@])@([A-Za-z][A-Za-z0-9_]{2,19})(?![A-Za-z0-9_])")

#: The most people linked and told in one post or comment: the first ten
#: distinct, in order; past them, plain words.
MOST = 10

#: What may follow the @ while it is typed: nothing yet, or the start of a
#: handle.
PREFIX_RE = re.compile(r"(?:[A-Za-z][A-Za-z0-9_]{0,19})?")

#: The most people the list shows.
SUGGEST = 4

#: How many rows each walk of the people reads, from where what was typed
#: would sort: what starts with it comes first, so a few are plenty.
WALK = 24


# ---- the words: who they mention --------------------------------------------------

def typed_in(words):
    """The @handles in `words`, each once (by its small letters), in the order
    they first come: [(handle in small letters, as typed)]."""
    seen = {}
    for m in MENTION_RE.finditer(words or ""):
        seen.setdefault(m.group(1).lower(), m.group(1))
    return list(seen.items())


def _people_named(words):
    """The first MOST distinct @handles in `words` that are somebody, in
    order: [(their id, as typed)]."""
    typed = typed_in(words)
    if not typed:
        return []
    found = dict(site().session().execute(
        sa.select(Person.handle_key, Person.id).where(Person.handle_key.in_([k for k, _ in typed]))).all())
    return [(found[k], t) for k, t in typed if k in found][:MOST]


def write_post(post):
    """The mentions in a post's words, written beside it (posts.post_new, in
    the same transaction, once its row is flushed). Flushes nothing."""
    _write(post.words, by_id=post.person_id, owner_id=post.person_id, when=post.created_at, post_id=post.id)


def write_comment(comment):
    """The mentions in a comment's or an answer's words (comments'
    new_comment, the same way). Its owner is whose the post or the drawing it
    is on is. Flushes nothing."""
    _write(comment.words, by_id=comment.person_id, owner_id=comment.owner_id, when=comment.created_at,
           comment_id=comment.id)


def _write(words, by_id, owner_id, when, post_id=None, comment_id=None):
    rows = [{"person_id": pid, "by_id": by_id, "owner_id": owner_id, "typed": typed, "created_at": when,
             "post_id": post_id, "comment_id": comment_id} for pid, typed in _people_named(words)]
    if rows:
        site().session().execute(sa.insert(Mention), rows)
        # A NUDGE, once the request commits (push.py): Activity's "mentioned
        # you" row, or the comment's or the quote's that says it.
        from .push import note
        for row in rows:
            note(row["person_id"], by_id, "mentions")


# ---- the words, as a page shows them -------------------------------------------------

def links(posts=(), comments=()):
    """{("p", a post's internal id) or ("c", a comment's): {a handle as typed,
    in small letters: the person's handle now}} for every post and comment
    asked that mentions anybody: one read for each kind asked (a page asks
    once for all its cards, and once for all its comments)."""
    out = {}
    sess = site().session()
    for kind, col, ids in (("p", Mention.post_id, posts), ("c", Mention.comment_id, comments)):
        ids = [i for i in dict.fromkeys(ids or ()) if i is not None]
        if not ids:
            continue
        q = (sa.select(col, Mention.typed, Person.handle).join(Person, Person.id == Mention.person_id)
             .where(col.in_(ids)))
        for oid, typed, handle in sess.execute(q).all():
            out.setdefault((kind, oid), {})[typed.lower()] = handle
    return out


def said(words, mentioned=None):
    """`words` as a page shows them: escaped, and each @handle that is one of
    `mentioned` ({as typed, in small letters: their handle now}: links()'s)
    a link to that person's page, in the words' own spelling. Plain words
    otherwise: a handle that is nobody, or past the first MOST."""
    words = words or ""
    if not mentioned:
        return escape(words)
    out, at = [], 0
    for m in MENTION_RE.finditer(words):
        handle = mentioned.get(m.group(1).lower())
        if handle is None:
            continue
        out.append(escape(words[at:m.start()]))
        out.append(Markup('<a class="mention" href="{}">@{}</a>').format(profile_url(handle), m.group(1)))
        at = m.end()
    out.append(escape(words[at:]))
    return Markup("").join(out)


# ---- the list under the @ --------------------------------------------------------

def suggest(me, q):
    """Whom the list under the @ offers `me` for `q` (what follows the @, in
    small letters): people they follow first, then anybody else, whose handle
    or any word of whose name starts with it, found as the Gallery's search
    finds people (people.followed, people.others); each by name; SUGGEST at
    most. Nobody a block hides either way (safety.hidden_ids), nobody taken
    down, never themselves. An @ alone: the people they follow, then anybody,
    by name."""
    from .follows import _on
    from .models import Follow
    from .people import fold, followed, others
    sess = site().session()
    away = sorted(hidden_ids(me) | {me.id})
    name = sa.func.lower(Person.display_name)

    def by_name(p):
        return ((p.display_name or "").lower(), p.handle_key)

    nq = fold(q)
    if nq:
        # WITH LETTERS, THE WAYS FINDING PEOPLE READS: the people you follow,
        # through your follows and their ways (each on its index); then
        # anybody else, on everybody's ways' own index, from where the
        # letters sort, WALK people at most; each part by name.
        first = sorted((p for _, p in followed(me, nq)), key=by_name)[:SUGGEST]
        if len(first) >= SUGGEST:
            return first
        rest = sorted((p for _, p in others(me, nq, most=WALK, exclude=me.id)), key=by_name)
        return first + rest[:SUGGEST - len(first)]

    def shown(sel):
        return sel.where(Person.taken_down_at.is_(None), Person.id.notin_(away))
    # AN @ ALONE: the people you follow, by name, on your follows' own index;
    # then anybody else, by name, from the start of the handles' own index and
    # of the names' (a few rows of each).
    mine = sa.select(Person).join(Follow, Follow.followed_id == Person.id).where(Follow.follower_id == me.id, _on())
    first = list(sess.execute(shown(mine).order_by(name, Person.handle_key).limit(SUGGEST)).scalars())
    if len(first) >= SUGGEST:
        return first
    have = {p.id for p in first}
    more = {}
    for col in (Person.handle_key, name):
        walk = shown(sa.select(Person).where(col >= "")).order_by(col).limit(WALK)
        for p in sess.execute(walk).scalars():
            if p.id not in have:
                more[p.id] = p
    rest = sorted(more.values(), key=by_name)
    return first + rest[:SUGGEST - len(first)]


# ---- deleting --------------------------------------------------------------------

def _drop(where):
    site().session().execute(sa.delete(Mention).where(where).execution_options(synchronize_session=False))


def drop_post_mentions(post_id):
    """A post's mentions (posts.drop_post, before the post)."""
    _drop(Mention.post_id == post_id)


def drop_comment_mentions(where):
    """The mentions of every comment `where` names (comments._drop, before the
    comments: every way a comment goes)."""
    _drop(Mention.comment_id.in_(sa.select(Comment.id).where(where).scalar_subquery()))


def drop_person_mentions(person_id):
    """Every mention of a person, every mention they wrote and every one on
    what they owned (accounts.delete_person). The words that named them stay,
    plain: nobody is there to open."""
    _drop(sa.or_(Mention.person_id == person_id, Mention.by_id == person_id, Mention.owner_id == person_id))


# ---- the route -------------------------------------------------------------------

def register(bp):
    """Add the list's route to the site's blueprint."""

    @bp.get("/people/suggest")
    @_rests(json_answer=True)
    def people_suggest():
        """Whom the list under an @ offers: {people: [{handle, name, face}]}."""
        me = current_person()
        if me is None:
            return _json_error("signed_out", 401)
        if over("people", "person|" + me.public_id):
            return _json_error("limited", 429)
        q = str(request.args.get("q") or "")
        q = q[1:] if q.startswith("@") else q
        people = suggest(me, q.lower()) if PREFIX_RE.fullmatch(q) else []
        resp = jsonify({"people": [{"handle": p.handle, "name": p.display_name,
                                    "face": render_template("social/_mention_face.html", who=p).strip()}
                                   for p in people]})
        resp.headers["Cache-Control"] = "private, no-store"
        return resp

    return bp
