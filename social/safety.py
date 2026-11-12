"""Safety (phase 1, piece 5; docs/SOCIAL-SITE.md section 5, build order item
5), from the owner's "all yes" on the Safety mock (Nov 12).

    /report             a report of somebody, a post, a drawing shown
                        outside a post, or a comment (phase 2): a reason from
                        REASONS, and a note if they wrote one, into the
                        admins' queue (JSON). From
                        anybody who can see the thing, signed in or not: a
                        child's safety must never wait on an account.
    /@<handle>/block    block them: both ways, and quietly (JSON).
    /@<handle>/unblock  lift your block (JSON from a sheet, or a form from
                        Settings, which comes back to Settings).

A REPORT IS A ROW, NEVER AN ACTION. Nothing is hidden because somebody
reported it, so a flood of reports takes nothing down; it can only fill the
queue, and the limit bounds even that. An admin looks and decides. Who
reported a thing is kept for the admins' eyes only; one reporter makes one
row for one thing (a keyed hash of the person, or for somebody signed out
their address), and a second report of it is answered like the first. You
can only report what you could see: a thing that is not there, or that a
block hides from you, is "gone", as it is to the page.

A BLOCK IS BOTH WAYS, AND QUIET. While one stands, neither person sees the
other's posts or drawings, and the one blocked meets an empty profile where
the blocker's was, as if nobody had that name; nobody is told. The blocker
still finds the blocked person's profile, saying they are blocked, with
Unblock. It reaches every page that shows either of them:

  * the site's own pages: Home's feed, a post's page, a drawing's page, More
    from, and the profile (blocked_ids, below, one query a request);
  * Skribl's pages, which the site does not draw: Explore's gallery and a
    profile's skribls (its listing), and a drawing's own link page, its
    share card, its picture and its payload (visible_to), through the two
    seams Skribl gives every host for exactly this (docs/INTEGRATION.md: a
    feed filter and a visibility policy). The host installs them, as it
    does the author resolver, asking hidden_authors (app.py does).

THE WORDS ARE THE PAGES'. The reasons are said here once, as the sheets
show them; everything else the sheets say is in the templates.
"""
import hashlib
import hmac

import sqlalchemy as sa
from flask import g, has_request_context, jsonify, redirect, request, url_for

from .accounts import HANDLE_RE, _hidden_in, _json_error, _rests
from .models import (PERSON_PREFIX, REPORT_NOTE_MAX, Block, Person, Post, Report,
                     new_public_id)
from .security import client_subject, current_person, origin_ok, over, read_aside, site, token_ok

#: The reasons each kind of report may give, in the order its sheet lists
#: them (the first is the one picked when the sheet opens), with the words.
#: A post's and a drawing's are the Gallery's own, and "A child's safety";
#: a person's are a person's (the owner's "all yes", Nov 12).
REASONS = {
    "person": (("fake", "Spam or a fake account"),
               ("abuse", "Abusive or hateful"),
               ("impersonation", "Pretending to be someone"),
               ("under13", "Under 13"),
               ("child_safety", "A child’s safety"),
               ("other", "Something else")),
    "post": (("spam", "Spam or misleading"),
             ("abuse", "Abusive or hateful"),
             ("copyright", "Copies someone else’s work"),
             ("child_safety", "A child’s safety"),
             ("other", "Something else")),
}
REASONS["drawing"] = REASONS["post"]
#: A comment's are a post's (phase 2, comments).
REASONS["comment"] = REASONS["post"]

#: The kinds this route takes.
KINDS = ("person", "post", "drawing", "comment")


# ---- who is blocked, both ways ----------------------------------------------

def blocked_ids(person):
    """The ids of everybody `person` has blocked or been blocked by: those
    the pages show neither of them. Read once a request, for the person
    signed in; empty for nobody."""
    if person is None:
        return frozenset()
    cache = g.setdefault("social_blocked", {}) if has_request_context() else {}
    if person.id in cache:
        return cache[person.id]
    t = Block.__table__
    rows = site().session().execute(
        sa.union(sa.select(t.c.blocked_id.label("pid")).where(t.c.blocker_id == person.id),
                 sa.select(t.c.blocker_id.label("pid")).where(t.c.blocked_id == person.id))).all()
    out = frozenset(r.pid for r in rows)
    cache[person.id] = out
    return out


def taken_down_ids():
    """The ids of the people an admin has taken down (Your Reports), read
    once a request: all they made is hidden from everybody but them."""
    cache = g.setdefault("social_down", {}) if has_request_context() else {}
    if "ids" not in cache:
        t = Person.__table__
        cache["ids"] = frozenset(r.id for r in read_aside(sa.select(t.c.id).where(t.c.taken_down_at.isnot(None))))
    return cache["ids"]


def hidden_ids(person):
    """The ids of everybody whose posts and drawings the site's pages hide
    from `person` (None for nobody signed in): a block either way, and
    anybody taken down, except themselves."""
    return (blocked_ids(person) | taken_down_ids()) - ({person.id} if person is not None else set())


def hidden_authors(viewer_id):
    """For Skribl's hooks (the host installs them: app.py, and
    docs/SOCIAL-SITE.md "A block reaches Skribl's pages"): the public ids of
    everybody whose drawings Skribl's pages hide from this viewer (Skribl's
    current user id, or None): a block either way, for one of the site's
    people, and anybody an admin has taken down, for everybody but
    themselves. Read once a request (read_aside), beside Skribl's own work,
    so never on a second connection once that work has read."""
    me = viewer_id if isinstance(viewer_id, str) and viewer_id.startswith(PERSON_PREFIX) else None
    cache = g.setdefault("social_hidden_public", {}) if has_request_context() else {}
    if me in cache:
        return cache[me]
    t = Person.__table__
    out = {r.public_id for r in read_aside(sa.select(t.c.public_id).where(t.c.taken_down_at.isnot(None)))}
    if me is not None:
        b, mine_t, other = Block.__table__, Person.__table__.alias("me"), Person.__table__.alias("other")
        mine = sa.select(mine_t.c.id).where(mine_t.c.public_id == me).scalar_subquery()
        out |= {r.pid for r in read_aside(sa.union(
            sa.select(other.c.public_id.label("pid")).join(b, b.c.blocked_id == other.c.id)
            .where(b.c.blocker_id == mine),
            sa.select(other.c.public_id.label("pid")).join(b, b.c.blocker_id == other.c.id)
            .where(b.c.blocked_id == mine)))}
        out.discard(me)
    out = frozenset(out)
    cache[me] = out
    return out


def between(a, b):
    """Whether a block stands between person rows (or snapshots) a and b,
    either way."""
    if a is None or b is None or a.id == b.id:
        return False
    return b.id in blocked_ids(a)


def i_blocked(me, who):
    """Whether `me` blocked `who` (the row the blocker can lift)."""
    if me is None or who is None:
        return False
    return site().session().execute(
        sa.select(Block.id).where(Block.blocker_id == me.id, Block.blocked_id == who.id)).first() is not None


def blocked_people(person):
    """The people `person` has blocked, newest first, for Settings."""
    return site().session().execute(
        sa.select(Person).join(Block, Block.blocked_id == Person.id)
        .where(Block.blocker_id == person.id)
        .order_by(Block.created_at.desc(), Block.id.desc())).scalars().all()


# ---- reports ------------------------------------------------------------------

def reporter_key(me):
    """A keyed hash of who is reporting: the person signed in, or for somebody
    signed out the address they report from. Never the thing itself."""
    who = ("person|" + me.public_id) if me is not None else ("addr|" + client_subject())
    return hmac.new(site().key, ("report|" + who).encode(), hashlib.sha256).hexdigest()


def _person_by_handle(handle):
    h = (handle or "").strip().lstrip("@")
    if not HANDLE_RE.fullmatch(h):
        return None
    return site().session().execute(sa.select(Person).where(Person.handle_key == h.lower())).scalar_one_or_none()


def _reported(kind, target, me):
    """(stored target, whose it is) for a thing `me` can see, or None: a
    person by handle, a post by its address, a drawing shown outside a post
    by its skribl's, a comment by its address. Gone, never made, or hidden
    by a block: None."""
    sess = site().session()
    if kind == "comment":
        # As its page shows it to them, a post's or a drawing's (comments.seen):
        # never your own, nor one taken down.
        from .comments import seen
        got = seen(target, me)
        if (got is None or got["c"].taken_down_at is not None or got["who"].taken_down_at is not None
                or (me is not None and got["who"].id == me.id)):
            return None
        return got["c"].public_id, got["who"]
    if kind == "person":
        who = _person_by_handle(target)
        if who is None or who.taken_down_at is not None or (me is not None and (who.id == me.id or between(me, who))):
            return None
        return who.public_id, who
    if kind == "post":
        found = sess.execute(sa.select(Post, Person).join(Person, Post.person_id == Person.id)
                             .where(Post.public_id == str(target or ""))).first()
        if (found is None or found[0].taken_down_at is not None or found[1].taken_down_at is not None
                or (me is not None and (found[1].id == me.id or between(me, found[1])))):
            return None
        return found[0].public_id, found[1]
    if kind == "drawing":
        from skribl import describe_posts
        sid = str(target or "")
        if not sid or sess.execute(sa.select(Post.id).where(Post.skribl_id == sid)).first() is not None:
            return None
        sk = describe_posts([sid], viewer_id=me.public_id if me else None).get(sid)
        if not sk or sk.get("visibility") != "public" or not str(sk.get("user_id") or "").startswith(PERSON_PREFIX):
            return None
        who = sess.execute(sa.select(Person).where(Person.public_id == sk["user_id"])).scalar_one_or_none()
        if who is None or who.taken_down_at is not None or (me is not None and (who.id == me.id or between(me, who))):
            return None
        return sid, who
    return None


def check_note(raw):
    """A report's note as the admins will read it: plain text, its spaces
    tidied, at most REPORT_NOTE_MAX characters; None for none. Anything but
    text, too long, or with a hidden character: why not."""
    if raw is None:
        return None, None
    if not isinstance(raw, str):
        return None, "note_bad"
    note = " ".join(raw.split())
    if len(note) > REPORT_NOTE_MAX:
        return None, "note_long"
    if _hidden_in(note):
        return None, "note_chars"
    return (note or None), None


def register(bp):
    """Add Safety's routes to the site's blueprint."""

    @bp.post("/report")
    @_rests(json_answer=True)
    def report():
        """A report into the admins' queue: {kind, target, reason, note}."""
        if not origin_ok() or not token_ok():
            return _json_error("stale", 403)
        me = current_person()
        subject = ("person|" + me.public_id) if me is not None else ("addr|" + client_subject())
        if over("report", subject):
            return _json_error("limited", 429)
        body = request.get_json(silent=True)
        if not isinstance(body, dict) or body.get("kind") not in KINDS:
            return _json_error("bad", 400)
        kind = body["kind"]
        if body.get("reason") not in {k for k, _ in REASONS[kind]}:
            return _json_error("bad", 400)
        note, problem = check_note(body.get("note"))
        if problem:
            return _json_error(problem, 400)
        found = _reported(kind, body.get("target"), me)
        if found is None:
            return _json_error("gone", 404)
        target, who = found
        sess = site().session()
        key = reporter_key(me)
        if sess.execute(sa.select(Report.id).where(Report.kind == kind, Report.target == target,
                                                   Report.reporter_key == key)).first() is None:
            try:
                with sess.begin_nested():
                    sess.add(Report(public_id=new_public_id(), kind=kind, target=target, about_id=who.id,
                                    reason=body["reason"], note=note,
                                    reporter_id=me.id if me is not None else None, reporter_key=key))
                    sess.flush()
            except sa.exc.IntegrityError:
                pass            # the same reporter, at the same instant: one row is the answer
        return jsonify({"ok": True}), 202

    @bp.post("/@<handle>/block")
    @_rests(json_answer=True)
    def block(handle):
        """Block somebody: both ways, quietly."""
        if not origin_ok() or not token_ok():
            return _json_error("stale", 403)
        me = current_person()
        if me is None:
            return _json_error("signed_out", 401)
        if over("block", "person|" + me.public_id):
            return _json_error("limited", 429)
        who = _person_by_handle(handle)
        if who is None or who.id == me.id:
            return _json_error("gone", 404)
        sess = site().session()
        if not i_blocked(me, who):
            try:
                with sess.begin_nested():
                    sess.add(Block(blocker_id=me.id, blocked_id=who.id))
                    sess.flush()
            except sa.exc.IntegrityError:
                pass            # blocked already, a moment ago
        return jsonify({"ok": True, "handle": who.handle})

    @bp.post("/@<handle>/unblock")
    @_rests()
    def unblock(handle):
        """Lift your block. From a sheet (JSON) or from Settings (a form,
        which comes back to Settings)."""
        form = not request.is_json
        if not origin_ok() or not token_ok():
            return _json_error("stale", 403) if not form else redirect(url_for("social.you"), 303)
        me = current_person()
        if me is None:
            return _json_error("signed_out", 401) if not form else redirect(url_for("social.signin"), 303)
        if over("block", "person|" + me.public_id):
            return _json_error("limited", 429) if not form else redirect(url_for("social.you", note="limited"), 303)
        who = _person_by_handle(handle)
        if who is not None:
            site().session().execute(sa.delete(Block).where(Block.blocker_id == me.id, Block.blocked_id == who.id))
            site().session().flush()
        if form:
            if request.form.get("back") == "profile" and who is not None:
                return redirect(url_for("social.profile", handle=who.handle), 303)
            return redirect(url_for("social.you", note="unblocked") + "#blockedTitle", 303)
        return jsonify({"ok": True})

    return bp
