"""The composer (docs/SOCIAL-SITE.md section 17, part two's first piece; the
owner's "Yes", Nov 14 at about 8 AM MST, to the mock drawn beside Bluesky's
new-post screen, B: one "Yours" in the tools; then, about 2:45 PM, one
drawing, one conversation).

    /make/yours     "Use one you made": a page of the picker's tiles, as
                    {html, next, tab} (JSON), yours alone. ?tab=drafts, the
                    drafts Skribl keeps on your account (list_drafts), each
                    opening in the editor that made it, over the composer;
                    ?tab=drawings (?before= for the next page), the drawings
                    you shared outside a post, as the Gallery's tiles
                    (gallery.loose_page), each attached as it is, its hearts
                    and comments coming with it when it is posted
                    (posts.post_new).

ONE COMPOSER, EVERYWHERE. Make, in the bar on a phone and the rail on a
desk, opens it on every page of the site with the bar (_compose.html, which
base.html carries for somebody signed in); Home's row ("Say something, then
draw it…") opens the same sheet. A phone's sheet rises almost to the top; a
desk's is a card in the middle. Cancel at the top left, Post at the top
right, dim until a drawing is attached (a post is words and one drawing,
the words optional). Your face beside "Say something…", the field taking
the keyboard as the sheet rises. Under the words the drawing, playing, with
Edit drawing and Remove (an older drawing has no Edit: it is posted as it
is, so its conversation can come with it). Along the bottom Draw, Flip and
Yours, and the characters left. compose.js holds the moving parts.

Every share from Make is a post. The composer is built so a quote post can
open it with the post attached (part two's item 3): what is attached is one
thing of a kind (a drawing made here, a draft, an older drawing; a post,
then), and compose.js asks each kind for what Post sends.

Signed out there is no composer (no account to post as): Make keeps its two
doors into Skribl's own Pad and Flip (_make.html), whose own share stays
Skribl's, so "No account needed to look, or to make one" stays true.

THROUGH SKRIBL'S SEAMS ONLY: list_drafts (documented, verify_social section
8), the editors' addresses with their documented compose flags and
?draft=<id>, and lib/composehost.js's openDraft.
"""
from flask import jsonify, render_template, request

from .accounts import _json_error, _rests
from .security import current_person

#: The picker's two lists, in its pill's order.
TABS = ("drafts", "drawings")


def register(bp, skribl_blueprint="skribl"):
    """Add the composer's route to the site's blueprint."""

    @bp.get("/make/yours")
    @_rests(json_answer=True)
    def compose_yours():
        """A page of "Use one you made": your drafts, or your drawings shared
        outside a post (?before=, the next page of them), as the picker's
        tiles: {html, next, tab}. Yours alone: nobody signed in is a 401."""
        from . import gallery, profiles
        me = current_person()
        if me is None:
            return _json_error("signed_out", 401)
        tab = request.args.get("tab")
        if tab not in TABS:
            return _json_error("bad", 400)
        before = request.args.get("before") or None
        drafts, tiles, nxt = [], [], None
        if tab == "drafts":
            if not before:
                drafts = profiles.draft_tiles(me, skribl_blueprint)
        else:
            entries, nxt = gallery.loose_page(me, before)
            tiles = gallery.tiles(entries, me) if entries else []
        html = render_template("social/_compose_tiles.html", tab=tab, drafts=drafts, tiles=tiles,
                               items_only=bool(before))
        resp = jsonify({"html": html, "next": nxt, "tab": tab})
        # One person's own: no cache keeps it.
        resp.headers["Cache-Control"] = "private, no-store"
        return resp

    return bp
