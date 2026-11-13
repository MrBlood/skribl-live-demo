"""Profiles with drawn faces (phase 1, piece 3; docs/SOCIAL-SITE.md section 5,
build order item 3, the owner's "all yes" on the phase 1 mocks).

    /@<handle>      a person's profile: their drawn face, big, drawing itself
                    once (Skribl's face player, 4x, still under Reduce
                    Motion), their name, @handle and a few lines about them,
                    and their public skribls as Skribl's own Gallery, newest
                    first. Handles are case-insensitive; nobody by that name
                    (never made, or deleted) is one kind not-found.
    /you/edit       Edit profile: your name and a few lines about you.
    /you/face       Draw your face: the drawing the Pad hands back in its face
                    mode (?compose=1&face=1, through lib/composehost.js on your
                    profile), kept as your face (JSON).

"FACES THAT DRAW THEMSELVES: everyone's picture is a skribl they draw of
themselves." A face is a skribl like any other, posted through Skribl's
create_post (docs/INTEGRATION.md, "When your composer is a form") in the same
request, and so the same transaction, as the row that names it: the two are
kept together or not at all. It is UNLISTED: a face is somebody's picture, not
a gallery post, so no listing shows it (Skribl's own, or the profile's, which
asks for the public ones only). Redrawing replaces it, and the old face is
deleted through Skribl's delete_post, as its author. Deleting the account
takes it too (accounts.delete_person).

THROUGH SKRIBL'S SEAMS ONLY: create_post, delete_post and their exceptions
from the package (documented names, verify_social section 8), the Gallery
section's macro with its author filter, the face player's macros, the Pad's
address with its documented compose flags. Nothing posts here that is not the
person's own, and every state-changing request shows the site's token and
Origin, and is limited per person (security.LIMITS), before it reads anything
through the request's session (security.over).
"""
import sqlalchemy as sa
from flask import jsonify, redirect, request, url_for

from .accounts import (HANDLE_RE, _json_error, _page, _rests, check_bio, check_name, drop_face,
                       profile_url)
from .models import Person
from .safety import between, i_blocked
from .security import csrf_token, current_person, origin_ok, over, public_origin, site, token_ok

#: The most a face may weigh on its way here: the Pad's whole payload, its
#: share card and any photo under the drawing included (Skribl's own caps on
#: each part still apply in create_post). Every other request to the site
#: stops at 64 KiB (social.SITE_MAX_BODY).
FACE_MAX_BODY = 16 * 1024 * 1024

#: The notes a profile says once, on the way back from saving (?note=).
NOTES = ("saved", "face")


def _person_by_handle(handle):
    """The person a handle names, however it is written, or None (a handle
    that could never be one included)."""
    h = (handle or "").strip()
    if not HANDLE_RE.fullmatch(h):
        return None
    return site().session().execute(
        sa.select(Person).where(Person.handle_key == h.lower())).scalar_one_or_none()


def register(bp, skribl_blueprint="skribl"):
    """Add the profile pages to the site's blueprint. `skribl_blueprint` is
    the name Skribl was registered under (init_social's), for the Pad's
    address."""

    @bp.get("/@<handle>")
    @_rests()
    def profile(handle):
        """A person's profile: their face drawing itself, their name, handle
        and bio, and their public skribls (Skribl's own Gallery, theirs only)."""
        who = _person_by_handle(handle)
        if who is None:
            # Said back only when it could be a handle: a page must not
            # repeat whatever an address was made to say.
            said = handle if HANDLE_RE.fullmatch(handle or "") else None
            return _page("nobody.html", 404, here="nobody", handle=said)
        me = current_person()
        mine = me is not None and me.id == who.id
        # A BLOCK (piece 5): to somebody you blocked, your profile is nobody's,
        # the same page as a handle never made; to you, theirs says you
        # blocked them, with Unblock, and shows nothing they made.
        blocked_them = not mine and i_blocked(me, who)
        if not mine and ((not blocked_them and between(me, who)) or who.taken_down_at is not None):
            # A block they made, or a takedown: nobody's, to anybody else.
            return _page("nobody.html", 404, here="nobody", handle=who.handle)
        note = request.args.get("note") if mine else None
        # FOLLOWS (B, yours alone): on somebody else's page only whether you
        # follow them; on your own, who follows you and whom you follow, for
        # your eyes and nobody else's.
        from .follows import for_owner, is_following
        # MUTES (C): their page is what you go to, so it stays; to you alone it
        # says "You muted Theo · Unmute", and its ⋯ says Unmute.
        from .mutes import i_muted
        # Your own profile is You's page; somebody else's is none of the
        # bar's places, so no tab says it is. The page's token for everybody:
        # Report is anybody's, Block anybody's signed in (piece 5).
        return _page("profile.html", here="you" if mine else "profile", who=who, mine=mine,
                     blocked_them=blocked_them,
                     following=not mine and not blocked_them and is_following(me, who),
                     muted=not mine and not blocked_them and i_muted(me, who),
                     fl=for_owner(me) if mine else None,
                     signin_here=url_for("social.signin", next=profile_url(who.handle)),
                     share_url=public_origin() + profile_url(who.handle),
                     token=csrf_token(),
                     note=note if note in NOTES else None,
                     face_compose=(url_for(skribl_blueprint + ".skribl_editor", compose=1, face=1)
                                   if mine else None))

    @bp.get("/you/edit")
    @_rests()
    def edit_profile():
        """Edit profile: your name and a few lines about you."""
        me = current_person()
        if me is None:
            return redirect(url_for("social.signin", next=request.path), 303)
        row = site().session().get(Person, me.id)
        return _page("edit.html", here="you", who=row, form_name=row.display_name,
                     form_bio=row.bio or "", errors={}, token=csrf_token())

    @bp.post("/you/edit")
    @_rests()
    def edit_profile_save():
        """Save your name and bio, or say kindly what to change."""
        if not origin_ok() or not token_ok():
            return _page("stale.html", 403, here="stale", hide_nav=True)
        me = current_person()
        if me is None:
            return redirect(url_for("social.signin", next=url_for("social.edit_profile")), 303)
        if over("profile-edit", "person|" + me.public_id):
            return _page("limited.html", 429, here="limited", hide_nav=True)
        raw_name, raw_bio = request.form.get("name"), request.form.get("bio")
        name, name_err = check_name(raw_name)
        bio, bio_err = check_bio(raw_bio)
        errors = {k: v for k, v in (("name", name_err), ("bio", bio_err)) if v}
        sess = site().session()
        row = sess.get(Person, me.id)
        if errors:
            # What they typed comes back as they typed it, with what to
            # change said under its field.
            return _page("edit.html", 400, here="you", who=row,
                         form_name=raw_name if isinstance(raw_name, str) else "",
                         form_bio=raw_bio if isinstance(raw_bio, str) else "", errors=errors,
                         token=csrf_token())
        row.display_name, row.bio = name, bio
        sess.flush()
        return redirect(profile_url(row.handle) + "?note=saved", 303)

    @bp.post("/you/face")
    @_rests(json_answer=True)
    def face_save():
        """Keep the drawing the Pad's face mode handed back as your face: a
        skribl, posted unlisted, its id on your row, in one commit; the old
        face deleted (JSON)."""
        if not origin_ok() or not token_ok():
            return _json_error("stale", 403)
        me = current_person()
        if me is None:
            return _json_error("signed_out", 401)
        if over("face", "person|" + me.public_id):
            return _json_error("limited", 429)
        body = request.get_json(silent=True)
        payload = body.get("payload") if isinstance(body, dict) else None
        if not isinstance(payload, dict):
            return _json_error("no_face", 400)
        from skribl import SkriblRejected, SkriblUnavailable, create_post
        sess = site().session()
        row = sess.get(Person, me.id)
        drawing = dict(payload)
        # A FACE IS NOBODY'S GALLERY POST, whatever the payload says: unlisted
        # (reachable by its own link, listed nowhere), titled as a face, no
        # caption. The Pad's face mode asks none of these; a body can say
        # anything, so they are set here, not trusted.
        drawing["visibility"] = "unlisted"
        drawing["title"] = f"{row.display_name}’s face"
        drawing["caption"] = ""
        # A FACE CARRIES NO PHOTO (Trace a photo, the owner's yes, Nov 11):
        # in the Pad's face mode a photo is a guide to trace, and the Pad
        # leaves it out of the drawing and its card. One sent anyway is
        # dropped here, from every frame and the legacy mirror, so a face is
        # the person's own lines. (The card is the browser's picture, as
        # every skribl's is.)
        drawing["photo"] = None
        if isinstance(drawing.get("frames"), list):
            drawing["frames"] = [dict(f, photo=None) if isinstance(f, dict) else f
                                 for f in drawing["frames"]]
        try:
            made = create_post(drawing, author_id=row.public_id)
        except SkriblRejected as exc:
            return _json_error("rejected", exc.status if 400 <= exc.status < 500 else 400,
                               message=exc.message)
        except SkriblUnavailable:
            return _json_error("busy", 503)
        old = row.face_id
        row.face_id = made.public_id
        row.face_w = made.post.canvas_w
        row.face_h = made.post.canvas_h
        sess.flush()
        if old and old != made.public_id:
            drop_face(row.public_id, old)
        return jsonify({"ok": True, "face": made.public_id,
                        "go": profile_url(row.handle) + "?note=face"})

    return bp
