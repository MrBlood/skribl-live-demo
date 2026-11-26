"""DRAWN LETTERS (the owner's yes, Nov 26, A for all six; DECISIONS.md,
"Drawn letters, mocked" and "Drawn letters: the owner's yes"; FUTURE.md 4,
"messages as drawn letters"). A drawing for one other person, only ever
between the two of you.

    /letters                        Send one: {"to": a handle, "payload"},
                                    or write back: {"written_on": a letter,
                                    "payload"} (JSON)
    /letters/<id>/write-back        For the composer: the letter to lay
                                    under the pen ({payload, first, own}),
                                    as Draw back's way in hands one over
    /letters/<id>/open              The recipient's page started playing it
    /letters/<id>/take-back         The sender, until it is opened: it goes
    /letters/<id>/delete            Gone from your side; from both, it goes
    /letters/@<handle>              The two of you (the pages, part three)

WHO CAN WRITE (choice 1): two people who follow each other, and nobody
across a block (pair_ok). Neither may be taken down. Writing back is
writing, under the same rule.

WHAT A LETTER IS (choice 2): a drawing, the Pad's, words drawn in your own
hand with its Text. A Flip letter is next, on the list; no photos and no
music at first (choice 6), refused at Send with a kind word.

WRITTEN BACK ON (choice 5, Draw back's way; the owner's yes, Nov 26: "A
written-back letter replays theirs in three seconds first (Draw back's
way), then yours at your pace"). The server joins the two from the letter as
Skribl stores it (drawback.join), never from what a browser says it was:
theirs squeezed to OVERTURE_MS when longer, then yours. A letter is ONE
WHOLE DRAWING, as draw-backs were before two hands, so a sheet written back
on several times plays in order; the two of you show each sheet once.

READ BY ITS TWO ALONE. Its drawing is Skribl's with the site's own
visibility, "letter": the host installs readable() as its visibility policy
(app.py, beside the block rule) and holds the state (Skribl's held states:
no author can make a letter public, or a post a letter, through Skribl's own
routes). An admin reads one only once it is reported to them. Never listed:
Skribl's listings show public drawings (and an author's own public, unlisted
and private), the site's pages list post rows, and a letter is neither.

OPENED by a POST from the recipient's page as it starts playing, never on a
GET, so a prefetch opens nothing. TAKE BACK deletes the letter and its
drawing, until it is opened; nothing says when it was. DELETE hides it from
your side; once both have, it goes.

NOT IN ACTIVITY (the envelope has its own dot: dot()), and NOT CHAT: no
typing dots and no "seen".
"""
import json

import sqlalchemy as sa
from flask import jsonify, redirect, request, url_for

from .accounts import _json_error, _rests
from .models import PERSON_PREFIX, Letter, Person, new_public_id, utcnow
from .security import current_person, origin_ok, over, site, token_ok

#: The visibility a letter's drawing has in Skribl: the site's own state.
LETTER = "letter"

#: What a letter's drawing is called in Skribl (it shows nowhere but to its two).
TITLE = "A letter"


# ---- who can write, who can read ----------------------------------------------

def pair_ok(me, who):
    """Whether `me` may write to `who`: two people, both here and neither
    taken down, who follow each other, with no block between them."""
    from .follows import is_following
    from .safety import between
    if me is None or who is None or me.id == who.id:
        return False
    # Read here: the request's own snapshot of `me` carries no takedown.
    if site().session().execute(sa.select(Person.id).where(Person.id.in_((me.id, who.id)),
                                                           Person.taken_down_at.isnot(None)).limit(1)).first():
        return False
    return not between(me, who) and is_following(me, who) and is_following(who, me)


def _mine(letter, me):
    """Whether `letter` is on `me`'s side: theirs to send or to have, and not
    deleted from it."""
    if me is None or letter is None:
        return False
    if letter.sender_id == me.id:
        return letter.sender_deleted_at is None
    if letter.recipient_id == me.id:
        return letter.recipient_deleted_at is None
    return False


def _other_id(letter, me):
    return letter.recipient_id if letter.sender_id == me.id else letter.sender_id


def shown_to(letter, me):
    """Whether `letter` is on `me`'s side and shown to them: not taken down
    (its sender still has it, saying so: taken_down), and no block between
    the two."""
    from .safety import blocked_ids
    if not _mine(letter, me):
        return False
    if letter.taken_down_at is not None and letter.sender_id != me.id:
        return False
    return _other_id(letter, me) not in blocked_ids(me)


def readable(post, viewer_id):
    """THE HOST'S VISIBILITY POLICY FOR A LETTER'S DRAWING (app.py installs
    it beside the block rule): None for every drawing that is not a letter's
    (Skribl's rules and the host's other policies decide); for one that is,
    True for either of its two, on their side and with no block between
    them, or for an admin once it is reported; False for everybody else. A
    drawing marked a letter that no letter names is nobody's."""
    if getattr(post, "visibility", None) != LETTER:
        return None
    vid = str(viewer_id or "")
    if not vid.startswith(PERSON_PREFIX):
        return False
    sess = site().session()
    me = sess.execute(sa.select(Person).where(Person.public_id == vid)).scalar_one_or_none()
    if me is None:
        return False
    rows = sess.execute(sa.select(Letter).where(Letter.skribl_id == post.public_id)).scalars().all()
    if any(shown_to(r, me) for r in rows):
        return True
    if me.is_admin and rows:
        from .models import Report
        ids = [r.public_id for r in rows]
        if sess.execute(sa.select(Report.id).where(Report.kind == "letter", Report.target.in_(ids))
                        .limit(1)).first() is not None:
            return True
    return False


def on(public_id, me):
    """The letter `public_id` as `me` may have it (shown_to), or None."""
    pid = str(public_id or "")
    if not (0 < len(pid) <= 24) or me is None:
        return None
    row = site().session().execute(sa.select(Letter).where(Letter.public_id == pid)).scalar_one_or_none()
    return row if row is not None and shown_to(row, me) else None


def enabled():
    """Whether the host taught Skribl the letter's state, held (app.py does,
    with its policy): without it no letter can be made, and none is offered.
    Held is among the values taught (set_visibility_values refuses else)."""
    from skribl import visibility_held
    return LETTER in visibility_held()


# ---- what the pages read ---------------------------------------------------------

def written_back_ids(ids):
    """Of the letters `ids`, those a letter was written back on: shown inside
    the one written on them, never on their own."""
    if not ids:
        return set()
    t = Letter.__table__
    return {r[0] for r in site().session().execute(
        sa.select(t.c.written_on_id).where(t.c.written_on_id.in_(sorted(ids))).distinct())}


def between_us(me, who):
    """The sheets between `me` and `who`, newest first: every letter either
    sent the other that is on `me`'s side, each sheet once (a letter written
    back on is inside the one written on it, if that one is shown to them)."""
    if me is None or who is None or me.id == who.id:
        return []
    rows = site().session().execute(
        sa.select(Letter).where(sa.or_(sa.and_(Letter.sender_id == me.id, Letter.recipient_id == who.id),
                                       sa.and_(Letter.sender_id == who.id, Letter.recipient_id == me.id)))
        .order_by(Letter.created_at.desc(), Letter.id.desc())).scalars().all()
    shown = [r for r in rows if shown_to(r, me)]
    inside = {r.written_on_id for r in shown if r.written_on_id is not None}
    return [r for r in shown if r.id not in inside]


def unopened(me):
    """Letters to `me` they have not opened, newest first."""
    if me is None:
        return []
    rows = site().session().execute(
        sa.select(Letter).where(Letter.recipient_id == me.id, Letter.opened_at.is_(None),
                                Letter.recipient_deleted_at.is_(None), Letter.taken_down_at.is_(None))
        .order_by(Letter.created_at.desc(), Letter.id.desc())).scalars().all()
    return [r for r in rows if shown_to(r, me)]


def dot(me):
    """The envelope's dot: how many letters wait unopened for `me`."""
    return len(unopened(me))


def hand_at(original, joined):
    """Where the answer's hand starts in `joined` (drawback.join of
    `original` and an answer): the time of its first point, in the drawing's
    own milliseconds. None when the original had no points."""
    from .drawback import _frame0, _points
    n = len(_points(_frame0(original) or {}))
    pts = _points(_frame0(joined) or {})
    if not n or len(pts) <= n:
        return None
    t = pts[n].get("t")
    return int(t) if isinstance(t, (int, float)) and not isinstance(t, bool) else None


# ---- going ------------------------------------------------------------------------

def _drop(row):
    """A letter and its drawing, gone (Skribl's delete_post, as the site:
    who may is the route's to say)."""
    from skribl import SkriblNotFound, delete_post
    sess = site().session()
    sid = row.skribl_id
    sess.execute(sa.update(Letter).where(Letter.written_on_id == row.id).values(written_on_id=None)
                 .execution_options(synchronize_session=False))
    sess.delete(row)
    sess.flush()
    # The drawing goes with its last letter (a drawing is one letter's).
    if sess.execute(sa.select(Letter.id).where(Letter.skribl_id == sid).limit(1)).first() is None:
        try:
            delete_post(sid, require_author=False)
        except SkriblNotFound:
            pass


def drop_person_letters(person_id):
    """Every letter an account sent or received, and their drawings
    (accounts.delete_person): a letter is the two's, and one written back on
    holds both hands, so it goes with either."""
    sess = site().session()
    rows = sess.execute(sa.select(Letter).where(sa.or_(Letter.sender_id == person_id,
                                                       Letter.recipient_id == person_id))
                        .order_by(Letter.id.desc())).scalars().all()
    for row in rows:
        _drop(row)


# ---- the routes -------------------------------------------------------------------

def _refuse_media(payload):
    """Why `payload` can't be a letter yet, or None: a Flip ("pages", the Pad
    first), a photo or music (choice 6), or anything Draw back can't hold."""
    from .drawback import drawable, flip_pages
    if flip_pages(payload) is not None:
        return "pages"
    return drawable(payload, answer=True)


def register(bp, skribl_blueprint="skribl"):
    """Add the letters' routes to the site's blueprint."""

    @bp.post("/letters")
    @_rests(json_answer=True)
    def letter_send():
        """Send a letter ({"to": handle, "payload"}) or write back on one
        ({"written_on": its id, "payload"}). Lands on the two of you."""
        from skribl import SkriblRejected, SkriblUnavailable, create_post, read_payload
        from .drawback import all_points, hands, join, same_shape
        from .safety import _person_by_handle
        if not origin_ok() or not token_ok():
            return _json_error("stale", 403)
        me = current_person()
        if me is None:
            return _json_error("signed_out", 401)
        if not enabled():
            return _json_error("letters_off", 404)
        if over("letter", "person|" + me.public_id):
            return _json_error("limited", 429)
        from .comments import may_comment
        if not may_comment(me):
            return _json_error("taken_down", 403)
        body = request.get_json(silent=True)
        if not isinstance(body, dict):
            return _json_error("no_drawing", 400)
        payload = body.get("payload")
        if not isinstance(payload, dict) or not all_points(payload):
            return _json_error("no_drawing", 400)
        why = _refuse_media(payload)
        if why:
            return _json_error("letter_unsupported", 400, why=why)
        sess = site().session()
        drawing = dict(payload)
        drawing.pop("thumbnailOwn", None)
        written_on = None
        hand_ms = None
        whose = None
        if body.get("written_on") is not None:
            written_on = on(body.get("written_on"), me)
            # Written back on by the one it came to, while it is theirs to have.
            if written_on is None or written_on.recipient_id != me.id or written_on.taken_down_at is not None:
                return _json_error("letter_gone", 404)
            who = sess.get(Person, written_on.sender_id)
            if body.get("to") is not None and (who is None or str(body.get("to")).lstrip("@").lower() != who.handle_key):
                return _json_error("bad", 400)
            if not pair_ok(me, who):
                return _json_error("not_friends", 403)
            original = read_payload(written_on.skribl_id, viewer_id=me.public_id, inline_media=True)
            if original is None:
                return _json_error("letter_gone", 404)
            if any(p.get("erase") for p in all_points(payload)):
                return _json_error("letter_unsupported", 400, why="erase")
            if not same_shape(original, payload):
                return _json_error("letter_shape", 400)
            whose = hands(original, payload, written_on.hands_json, who.id, me.id)
            joined = join(original, drawing)
            hand_ms = hand_at(original, joined)
            drawing = joined
        else:
            who = _person_by_handle(body.get("to"))
            if who is None or not pair_ok(me, who):
                # Nobody by that name, or nobody you may write to: said the same.
                return _json_error("not_friends", 403)
        drawing["visibility"] = LETTER
        drawing["title"] = TITLE
        drawing.pop("caption", None)
        try:
            made = create_post(drawing, author_id=me.public_id)
        except SkriblRejected as exc:
            return _json_error("rejected", exc.status if 400 <= exc.status < 500 else 400, message=exc.message)
        except SkriblUnavailable:
            return _json_error("busy", 503)
        row = Letter(public_id=new_public_id(8), sender_id=me.id, recipient_id=who.id, skribl_id=made.public_id,
                     written_on_id=written_on.id if written_on is not None else None, hand_at_ms=hand_ms,
                     hands_json=json.dumps(whose) if whose else None)
        sess.add(row)
        sess.flush()
        # A NUDGE, where their device has New letters on (push.py; the
        # owner's yes, Nov 26).
        from .push import note
        note(who.id, me.id, "letters")
        return jsonify({"ok": True, "letter": row.public_id,
                        "go": url_for("social.letters_with", handle=who.handle)})

    @bp.get("/letters/<public_id>/write-back")
    @_rests(json_answer=True)
    def letter_write_back(public_id):
        """For the composer: the letter to write back on ({payload, first,
        own}), as Draw back's way in hands a drawing over. The one it came
        to, while they may still write to its sender."""
        from skribl import read_payload
        from .models import first_name
        me = current_person()
        if me is None:
            return _json_error("signed_out", 401)
        row = on(public_id, me)
        if row is None or row.recipient_id != me.id or row.taken_down_at is not None:
            return _json_error("letter_gone", 404)
        who = site().session().get(Person, row.sender_id)
        if not pair_ok(me, who):
            return _json_error("not_friends", 403)
        original = read_payload(row.skribl_id, viewer_id=me.public_id)
        if original is None:
            return _json_error("letter_gone", 404)
        why = _refuse_media(original)
        if why:
            return _json_error("letter_unsupported", 400, why=why)
        resp = jsonify({"payload": original, "first": first_name(who.display_name), "own": False,
                        "to": who.handle})
        resp.headers["Cache-Control"] = "private, no-store"
        return resp

    def _acted(public_id):
        """The letter a POST acts on, for `me`: (me, row) or a refusal."""
        if not origin_ok() or not token_ok():
            return None, None, _json_error("stale", 403)
        me = current_person()
        if me is None:
            return None, None, _json_error("signed_out", 401)
        if over("letter-act", "person|" + me.public_id):
            return None, None, _json_error("limited", 429)
        row = on(public_id, me)
        if row is None:
            return None, None, _json_error("letter_gone", 404)
        return me, row, None

    @bp.post("/letters/<public_id>/open")
    @_rests(json_answer=True)
    def letter_open(public_id):
        """The recipient's page started playing it: opened, once. Nothing
        else says so (no "seen")."""
        me, row, refusal = _acted(public_id)
        if refusal is not None:
            return refusal
        if row.recipient_id == me.id and row.opened_at is None:
            row.opened_at = utcnow()
            site().session().flush()
        return jsonify({"ok": True})

    @bp.post("/letters/<public_id>/take-back")
    @_rests(json_answer=True)
    def letter_take_back(public_id):
        """Its sender takes it back, until it is opened: the letter and its
        drawing go. Opened already: "letter_opened", and it stays."""
        me, row, refusal = _acted(public_id)
        if refusal is not None:
            return refusal
        if row.sender_id != me.id:
            return _json_error("letter_gone", 404)
        if row.opened_at is not None:
            return _json_error("letter_opened", 409)
        _drop(row)
        return jsonify({"ok": True})

    @bp.post("/letters/<public_id>/delete")
    @_rests(json_answer=True)
    def letter_delete(public_id):
        """Gone from your side; once both have deleted it, it goes."""
        me, row, refusal = _acted(public_id)
        if refusal is not None:
            return refusal
        now = utcnow()
        if row.sender_id == me.id:
            row.sender_deleted_at = now
        else:
            row.recipient_deleted_at = now
        if row.sender_deleted_at is not None and row.recipient_deleted_at is not None:
            _drop(row)
        site().session().flush()
        return jsonify({"ok": True})

    @bp.get("/letters/@<handle>")
    @_rests()
    def letters_with(handle):
        """The two of you. Until its page is built (part three), the other
        person's page."""
        return redirect(url_for("social.profile", handle=handle), 303)

    return bp
