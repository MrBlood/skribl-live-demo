"""Profiles with drawn faces (phase 1, piece 3; docs/SOCIAL-SITE.md section 5,
build order item 3, the owner's "all yes" on the phase 1 mocks).

    /@<handle>      a person's profile: their drawn face, big, drawing itself
                    once (Skribl's face player, 4x, still under Reduce
                    Motion), their name, @handle, their counts ("3 followers
                    · 2 following", or "New here"; follows.counts) and a few
                    lines about them, and their tabs, Posts first. Handles
                    are case-insensitive; nobody by that name (never made,
                    or deleted) is one kind not-found.
    /@<handle>/gallery, /likes, /drafts
                    the same page on another tab: each tab is a link with
                    its own address, so the back button and a shared link
                    land on it. Likes and Drafts are the owner's alone:
                    anybody else is sent to the person's page.
    /@<handle>/more a tab's first page, or its next (?tab=, ?before=), as
                    its cards or tiles (JSON {html, next, tab}), for the
                    switch and Load more (tabs.js).

A PROFILE'S TABS (the map's step 4, docs/SOCIAL-SITE.md section 16; the
owner's "Yes" to its mock, Nov 14): Posts · Gallery · Likes · Drafts on your
own page, Posts · Gallery on anybody else's, Posts opening first.
  Posts     their posts as Home's one card, newest first (posts.person_page).
  Gallery   every drawing and Flip they shared, as the Gallery's tiles: a
            post's opens its post, one shown outside a post (before posts)
            its own page (gallery.person_page). A face and a drawing kept
            link-only never.
  Likes     yours alone: the posts you liked, newest liked first, as cards
            (likes.liked_page).
  Drafts    yours alone: the drafts Skribl keeps on your account, as tiles,
            each opening the editor that made it with ?draft=<id>, the
            editors' own hand-off (Skribl's list_drafts, docs/INTEGRATION.md
            "A person's drafts on your own page").
Blocks, takedowns and mutes are the profile's own rules, kept as they were:
somebody who blocked you, or anybody taken down, is nobody's page; to
somebody you blocked, their page shows nothing of theirs, tabs included; a
mute hides nothing on the page you went to.
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

THROUGH SKRIBL'S SEAMS ONLY: create_post, delete_post, list_drafts and their
exceptions from the package (documented names, verify_social section 8), the
face player's macros, the Pad's address with its documented compose flags,
and the editors' with ?draft=<id>. Nothing posts here that is not the
person's own, and every state-changing request shows the site's token and
Origin, and is limited per person (security.LIMITS), before it reads anything
through the request's session (security.over).
"""
from datetime import datetime, timezone

import sqlalchemy as sa
from flask import jsonify, redirect, render_template, request, url_for

from .accounts import (HANDLE_RE, _json_error, _page, _rests, check_bio, check_name, drop_face,
                       profile_url)
from .models import Person, as_utc
from .safety import between, i_blocked
from .security import csrf_token, current_person, origin_ok, over, public_origin, site, token_ok

#: A profile's tabs, in their order (the map's step 4): Posts opens first.
TABS = ("posts", "gallery", "likes", "drafts")

#: Yours alone: on your own page and nobody else's, nor in its source.
OWN_TABS = ("likes", "drafts")

#: What each tab is called.
TAB_NAMES = {"posts": "Posts", "gallery": "Gallery", "likes": "Likes", "drafts": "Drafts"}

#: A draft's own small picture, as Skribl keeps it (a raster data: URL it
#: checked when it was saved); anything else is shown as no picture.
_THUMB_KINDS = ("data:image/jpeg;base64,", "data:image/png;base64,", "data:image/webp;base64,")


def tabs_for(mine):
    """The tabs a profile shows: everybody's two, and your own two more."""
    return TABS if mine else TABS[:2]


def tab_url(handle, tab):
    """A tab's own address: the profile's own for Posts, which opens first."""
    if tab == "posts":
        return url_for("social.profile", handle=handle)
    return url_for("social.profile_tab", handle=handle, tab=tab)


def saved_ago(when, now=None):
    """How long ago a draft was saved, in the drafts' one vocabulary (Skribl's
    lib/posted.js ago(), which the editors' Your drafts and the Library say,
    its Math.round as x + 0.5 floored): "just now", "4 min ago", "2 hours
    ago", "3 days ago", "last week", "3 weeks ago", "2 months ago", "a year
    ago"."""
    now = now or datetime.now(timezone.utc)
    s = max(0.0, (now - as_utc(when)).total_seconds())

    def r(x):
        return int(x + 0.5)
    if s < 90:
        return "just now"
    m = s / 60
    if m < 60:
        return f"{r(m)} min ago"
    h = m / 60
    if h < 24:
        return f"{r(h)} hour ago" if r(h) == 1 else f"{r(h)} hours ago"
    d = h / 24
    if d < 7:
        return f"{r(d)} day ago" if r(d) == 1 else f"{r(d)} days ago"
    if d < 14:
        return "last week"
    if d < 56:
        return f"{r(d / 7)} weeks ago"
    if d < 365:
        return f"{max(2, r(d / 30.44))} months ago"
    y = r(d / 365.25)
    return "a year ago" if y == 1 else f"{y} years ago"


def _iso(text):
    """A time Skribl wrote (isoformat; SQLite's without a zone, which is
    UTC), or None."""
    try:
        return as_utc(datetime.fromisoformat(str(text)))
    except (TypeError, ValueError):
        return None


def draft_tiles(me, skribl_blueprint="skribl"):
    """Your drafts as the Drafts tab's tiles (yours alone): Skribl's own list
    (list_drafts, its seam), newest saved first, each with its picture, its
    title, "Pad · saved 2 hours ago" (or Flip), and the editor that made it,
    at its address with ?draft=<id>, where it opens as the editors' own Your
    drafts opens one."""
    from skribl import list_drafts
    out = []
    for d in list_drafts(me.public_id):
        flip = d.get("kind") == "flip"
        title = str(d.get("title") or "").strip() or "Untitled Skribl"
        when = _iso(d.get("updatedAt") or d.get("createdAt"))
        ago = saved_ago(when) if when else None
        editor, where = ("Flip", "Flip") if flip else ("Pad", "the Pad")
        thumb = d.get("thumbnail")
        out.append({"id": d["id"], "kind": "flip" if flip else "pad", "title": title,
                    "thumbnail": thumb if isinstance(thumb, str) and thumb.startswith(_THUMB_KINDS) else None,
                    "url": url_for(skribl_blueprint + (".skribl_flip" if flip else ".skribl_editor"), draft=d["id"]),
                    "line": f"{editor} · saved {ago}" if ago else editor,
                    "label": f"Keep drawing {title} in {where}" + (f", saved {ago}" if ago else "")})
    return out


def tab_view(who, me, mine, tab, before=None, skribl_blueprint="skribl"):
    """What a tab shows `me` on `who`'s page, a page at a time: {"tab",
    "cards" (Posts, Likes), "tiles" (Gallery), "drafts" (Drafts), "next" (the
    cursor of the page after, or None)}. Likes and Drafts are asked only on
    your own page (the caller's to see)."""
    from . import gallery, likes, posts
    out = {"tab": tab, "cards": [], "tiles": [], "drafts": [], "next": None}
    if tab == "posts":
        entries, out["next"] = posts.person_page(who, me, before)
        out["cards"] = posts.cards(entries, me) if entries else []
    elif tab == "gallery":
        entries, out["next"] = gallery.person_page(who, me, before)
        out["tiles"] = gallery.tiles(entries, me)
    elif tab == "likes" and mine:
        entries, out["next"] = likes.liked_page(me, before)
        out["cards"] = posts.cards(entries, me) if entries else []
    elif tab == "drafts" and mine and not before:
        out["drafts"] = draft_tiles(me, skribl_blueprint)
    return out

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

    def whose(handle):
        """(who, me, mine, blocked_them, refusal): the person a profile's
        address names, as `me` may see them. A refusal is the kind 404: nobody
        by that name, or to anybody else a block they made or a takedown."""
        who = _person_by_handle(handle)
        if who is None:
            # Said back only when it could be a handle: a page must not
            # repeat whatever an address was made to say.
            said = handle if HANDLE_RE.fullmatch(handle or "") else None
            return None, None, False, False, _page("nobody.html", 404, here="nobody", handle=said)
        me = current_person()
        mine = me is not None and me.id == who.id
        # A BLOCK (piece 5): to somebody you blocked, your profile is nobody's,
        # the same page as a handle never made; to you, theirs says you
        # blocked them, with Unblock, and shows nothing they made.
        blocked_them = not mine and i_blocked(me, who)
        if not mine and ((not blocked_them and between(me, who)) or who.taken_down_at is not None):
            # A block they made, or a takedown: nobody's, to anybody else.
            return who, me, False, blocked_them, _page("nobody.html", 404, here="nobody", handle=who.handle)
        return who, me, mine, blocked_them, None

    @bp.get("/@<handle>")
    @_rests()
    def profile(handle):
        """A person's profile: their face drawing itself, their name, handle
        and bio, and their tabs, Posts first."""
        return profile_page(handle, "posts")

    @bp.get("/@<handle>/<any(gallery, likes, drafts):tab>")
    @_rests()
    def profile_tab(handle, tab):
        """A person's profile on another of its tabs, at its own address."""
        return profile_page(handle, tab)

    @bp.get("/@<handle>/more")
    @_rests(json_answer=True)
    def profile_more(handle):
        """A tab's first page (a switch), or its next (?before=, Load more):
        {html, next, tab}. The page's own rules: nothing for anybody a
        refusal or a block stands for, and Likes and Drafts the owner's
        alone."""
        who, me, mine, blocked_them, refusal = whose(handle)
        tab = request.args.get("tab")
        if refusal is not None or blocked_them or tab not in tabs_for(mine):
            return _json_error("gone", 404)
        before = request.args.get("before") or None
        if before and len(before) > 200:
            before = "?"
        view = tab_view(who, me, mine, tab, before, skribl_blueprint)
        html = render_template("social/_profile_panel.html", p=view, who=who, mine=mine, items_only=bool(before))
        resp = jsonify({"html": html, "next": view["next"], "tab": tab})
        # One person's own (Likes, Drafts), and the viewer's view of anybody:
        # no cache keeps it.
        resp.headers["Cache-Control"] = "private, no-store"
        return resp

    def profile_page(handle, tab):
        who, me, mine, blocked_them, refusal = whose(handle)
        if refusal is not None:
            return refusal
        if tab not in tabs_for(mine):
            # LIKES AND DRAFTS ARE YOURS ALONE: anybody else (signed out too)
            # is sent to the person's page, which shows neither.
            return redirect(profile_url(who.handle), 302)
        note = request.args.get("note") if mine else None
        # FOLLOWS: the counts on every profile, counted for whoever looks
        # (the quick-patterns mock's A), none on somebody you blocked, whose
        # page shows nothing of theirs; on somebody else's page whether you
        # follow them; on your own, who follows you and whom you follow, the
        # lists your counts open, for your eyes and nobody else's.
        from .follows import counts, for_owner, is_following
        fo_n = counts(me, who) if not blocked_them else None
        # MUTES (C): their page is what you go to, so it stays; to you alone it
        # says "You muted Theo · Unmute", and its ⋯ says Unmute.
        from .mutes import i_muted
        # THE TABS (the map's step 4): the chosen one's first page; nothing
        # of theirs on somebody you blocked. Each tab's own address.
        here_url = tab_url(who.handle, tab)
        tabs = [(t, TAB_NAMES[t], tab_url(who.handle, t)) for t in tabs_for(mine)]
        view = None if blocked_them else tab_view(who, me, mine, tab, None, skribl_blueprint)
        # Your own profile is You's page; somebody else's is none of the
        # bar's places, so no tab says it is. The page's token for everybody:
        # Report is anybody's, Block anybody's signed in (piece 5).
        return _page("profile.html", here="you" if mine else "profile", who=who, mine=mine,
                     blocked_them=blocked_them,
                     following=not mine and not blocked_them and is_following(me, who),
                     muted=not mine and not blocked_them and i_muted(me, who),
                     fo_n=fo_n, fl=for_owner(me, fo_n) if mine else None,
                     tab=tab, tabs=tabs, p=view,
                     signin_here=url_for("social.signin", next=here_url),
                     share_url=public_origin() + profile_url(who.handle),
                     canonical=public_origin() + here_url,
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
