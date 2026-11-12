"""Your Reports (phase 1, piece 5; the owner's "all yes" on the Safety mock,
Nov 12): what people reported, for the site's admins, and their two answers.

    /reports             the open reports, a card per thing reported: a
                         child's safety first, blurred until opened; then the
                         newest. Admins only: anybody else gets the same 404
                         as a page that is not there (Invites' rule).
    /reports/down        Take it down: hidden for everybody at once, a copy
                         kept, its reports closed (a form).
    /reports/keep        Keep it: its reports closed, nothing hidden (a form).

ONE QUEUE FROM TWO. The site's own reports (social_reports: somebody, a post,
a drawing shown outside a post, a comment) and Skribl's (what people reported on
Skribl's own pages: the Gallery's tiles on Explore, a drawing's link page),
read through Skribl's documented seams (list_reports, close_reports,
set_post_visibility: docs/INTEGRATION.md, "Your own reports page"). A post's
drawing reported on Explore is the post's card; anything else Skribl's
queue holds is a drawing's.

TAKING IT DOWN keeps everything. A person: their profile is nobody's to
everybody else, and all they made is hidden (they can still sign in, see
their own with the note, and delete their account). A post: hidden from
everybody but its author, its skribl withheld in Skribl. A drawing: withheld
in Skribl. A comment (phase 2): hidden from everybody but its author, and
neither shown nor counted under its post. Its maker sees "Taken down: it
broke the rules" on it. Nothing is deleted, and every report on it is
closed, saying who answered and when.

A CHILD'S SAFETY: its card says what the law may ask (in the US, reporting
to NCMEC) and that the owner's lawyer sets that up; taking it down keeps the
copy the law may ask to be kept.
"""
import sqlalchemy as sa
from flask import abort, g, redirect, request, url_for

from .accounts import _page, _rests, profile_url
from .models import PERSON_PREFIX, Comment, Person, Post, Report, utcnow
from .safety import REASONS
from .security import csrf_token, current_person, origin_ok, site, token_ok

#: Each reason's words, whatever kind it was given for.
WORDS = {k: w for kind in REASONS.values() for k, w in kind}
WORDS.setdefault("other", "Something else")

#: The notes the page says once, on the way back (?note=).
NOTES = ("down", "kept", "gone")


def _admin():
    """The signed-in admin, or the same 404 a missing page gives."""
    me = current_person()
    if me is None or not me.is_admin:
        g.social_hidden = True
        abort(404)
    return me


def open_count():
    """How many things wait in the queue, the site's and Skribl's."""
    try:
        return len(queue())
    except sa.exc.SQLAlchemyError:
        return 0


def queue():
    """The open reports, a card each: a child's safety first, then newest.
    Each card: kind, target, who (the person it is about, or None), what
    (the post or drawing, or None), reasons [(words, count)], count, notes
    [(who wrote it or None, the note)], reporters (names, or "somebody signed
    out" / "somebody on Explore"), child, latest."""
    from skribl import describe_posts, list_reports
    sess = site().session()
    cards = {}

    def card(kind, target):
        return cards.setdefault((kind, target), {"kind": kind, "target": target, "reasons": {}, "count": 0,
                                                 "notes": [], "reporters": [], "child": False, "latest": None})

    rows = sess.execute(sa.select(Report, Person).outerjoin(Person, Person.id == Report.reporter_id)
                        .where(Report.state == "open")
                        .order_by(Report.created_at.desc(), Report.id.desc())).all()
    for r, by in rows:
        c = card(r.kind, r.target)
        c["reasons"][r.reason] = c["reasons"].get(r.reason, 0) + 1
        c["count"] += 1
        name = by.display_name if by is not None else None
        c["reporters"].append(name or "somebody signed out")
        if r.note:
            c["notes"].append((name, r.note))
        c["child"] = c["child"] or r.reason == "child_safety"
        when = r.created_at
        c["latest"] = when if c["latest"] is None or when > c["latest"] else c["latest"]
    for grp in list_reports(limit=500):
        post = sess.execute(sa.select(Post).where(Post.skribl_id == grp["id"])).scalar_one_or_none()
        # A drawing answer reported on Skribl's own link page is its comment's.
        said_on = None if post is not None else sess.execute(
            sa.select(Comment).where(Comment.skribl_id == grp["id"])).scalar_one_or_none()
        c = (card("post", post.public_id) if post is not None else
             card("comment", said_on.public_id) if said_on is not None else card("drawing", grp["id"]))
        for reason, n in grp["reasons"].items():
            c["reasons"][reason] = c["reasons"].get(reason, 0) + n
        c["count"] += grp["count"]
        c["reporters"] += ["somebody on Explore"] * grp["count"]
        c["notes"] += [(None, n) for n in grp["notes"]]
        c["child"] = c["child"] or grp["child_safety"]
        from datetime import datetime
        when = datetime.fromisoformat(grp["latest"])
        if c["latest"] is not None and c["latest"].tzinfo is None:
            when = when.replace(tzinfo=None)
        c["latest"] = when if c["latest"] is None or when > c["latest"] else c["latest"]

    # What each card is about, as the admin will see it.
    out = []
    skribls = [c["target"] for c in cards.values() if c["kind"] == "drawing"]
    posts = {p.public_id: (p, who) for p, who in sess.execute(
        sa.select(Post, Person).join(Person, Person.id == Post.person_id)
        .where(Post.public_id.in_([c["target"] for c in cards.values() if c["kind"] == "post"]))).all()}
    skribls += [p.skribl_id for p, _ in posts.values()]
    said = {cm.public_id: (cm, who, post) for cm, who, post in sess.execute(
        sa.select(Comment, Person, Post).join(Person, Person.id == Comment.person_id)
        .join(Post, Post.id == Comment.post_id)
        .where(Comment.public_id.in_([c["target"] for c in cards.values() if c["kind"] == "comment"]))).all()}
    seen = describe_posts(skribls) if skribls else {}
    people = {p.public_id: p for p in sess.execute(sa.select(Person).where(Person.public_id.in_(
        [c["target"] for c in cards.values() if c["kind"] == "person"]
        + [str((seen.get(t) or {}).get("user_id") or "") for t in skribls]))).scalars()}
    for c in cards.values():
        c["reasons"] = sorted(((WORDS.get(k, k), n) for k, n in c["reasons"].items()),
                              key=lambda x: (x[0] != WORDS["child_safety"], -x[1]))
        if c["kind"] == "person":
            c["who"] = people.get(c["target"])
            c["what"] = None
            c["url"] = profile_url(c["who"].handle) if c["who"] else None
        elif c["kind"] == "post":
            p, who = posts.get(c["target"], (None, None))
            c["who"], c["what"] = who, p
            c["poster"] = url_for(site_bp() + ".skribl_poster", public_id=p.skribl_id) if p else None
            c["url"] = url_for("social.post_page", public_id=p.public_id) if p else None
        elif c["kind"] == "comment":
            # A COMMENT'S CARD (phase 2): its words, whose it is, and a link to
            # it on its post's page.
            cm, who, on = said.get(c["target"], (None, None, None))
            c["who"], c["what"] = who, cm
            c["url"] = (url_for("social.post_page", public_id=on.public_id) + "#c-" + cm.public_id) if cm else None
            # A drawing answer's card shows its picture; words alone, whose face.
            c["poster"] = (url_for(site_bp() + ".skribl_poster", public_id=cm.skribl_id)
                           if cm is not None and cm.skribl_id else None)
        else:
            sk = seen.get(c["target"]) or {}
            c["who"] = people.get(str(sk.get("user_id") or ""))
            c["what"] = sk or None
            c["poster"] = url_for(site_bp() + ".skribl_poster", public_id=c["target"])
            c["url"] = (url_for("social.bloob_page", skribl_id=c["target"])
                        if str(sk.get("user_id") or "").startswith(PERSON_PREFIX) else
                        url_for(site_bp() + ".skribl_player", public_id=c["target"]))
        out.append(c)
    from .models import as_utc
    out.sort(key=lambda c: (not c["child"], -(as_utc(c["latest"]).timestamp() if c["latest"] else 0)))
    return out


def site_bp():
    return getattr(g, "social_skribl_bp", None) or "skribl"


def _withhold(skribl_id):
    """Skribl's operator state for a drawing: hidden from everybody but its
    signed-in author (set_post_visibility, as an operator). Gone already:
    nothing to hide."""
    from skribl import SkriblNotFound, set_post_visibility
    try:
        set_post_visibility(skribl_id, "withheld", require_author=False)
    except SkriblNotFound:
        pass


def answer(kind, target, me, down):
    """Take it down (down=True) or keep it: every open report on it closed,
    saying who and when; and when taken down, hidden as the module says.
    False if there is no such card."""
    from skribl import close_reports
    sess = site().session()
    now = utcnow()
    if kind == "person":
        who = sess.execute(sa.select(Person).where(Person.public_id == target)).scalar_one_or_none()
        if who is None:
            return False
        if down and who.taken_down_at is None:
            who.taken_down_at = now
    elif kind == "post":
        p = sess.execute(sa.select(Post).where(Post.public_id == target)).scalar_one_or_none()
        if p is None:
            return False
        if down:
            if p.taken_down_at is None:
                p.taken_down_at = now
            _withhold(p.skribl_id)
        close_reports(p.skribl_id)
    elif kind == "drawing":
        if down:
            _withhold(target)
        close_reports(target)
    elif kind == "comment":
        cm = sess.execute(sa.select(Comment).where(Comment.public_id == target)).scalar_one_or_none()
        if cm is None:
            return False
        if down and cm.taken_down_at is None:
            cm.taken_down_at = now
        if cm.skribl_id:
            # A drawing answer: withheld with its comment, and what was
            # reported of it on Skribl's own pages closed with it.
            if down:
                _withhold(cm.skribl_id)
            close_reports(cm.skribl_id)
    else:
        return False
    sess.execute(sa.update(Report).where(Report.kind == kind, Report.target == target, Report.state == "open")
                 .values(state="taken_down" if down else "kept", handled_at=now, handled_by_id=me.id))
    sess.flush()
    return True


def register(bp, skribl_blueprint="skribl"):
    """Add Your Reports to the site's blueprint."""

    @bp.before_request
    def _which_skribl():
        g.social_skribl_bp = skribl_blueprint

    @bp.get("/reports")
    @_rests()
    def reports():
        """The open reports, for an admin."""
        me = _admin()
        note = request.args.get("note")
        return _page("reports.html", here="reports", me=me, cards=queue(), token=csrf_token(),
                     note=note if note in NOTES else None)

    def _answer(down):
        me = _admin()
        if not origin_ok() or not token_ok():
            return _page("stale.html", 403, here="stale", hide_nav=True)
        ok = answer(request.form.get("kind") or "", request.form.get("target") or "", me, down)
        return redirect(url_for("social.reports", note=("down" if down else "kept") if ok else "gone"), 303)

    @bp.post("/reports/down")
    @_rests()
    def reports_down():
        """Take it down: hidden for everybody at once, a copy kept."""
        return _answer(True)

    @bp.post("/reports/keep")
    @_rests()
    def reports_keep():
        """Keep it: its reports closed, nothing hidden."""
        return _answer(False)

    return bp
