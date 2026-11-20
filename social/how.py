"""How it works, the site's own page (the owner's "All yes", Nov 19, to a
door from the site to How it works; DECISIONS.md, "How it works, from the
site"). Until then the site had no door to any help: its menu's own note
said "No Help row until there is a Help page."

    /how    How it works: what the site is in one line, three drawings that
            draw themselves (a drawing, a draw-back, a Flip), what people
            often ask, and the editors' own How it works at its foot.

Anybody can read it, signed in or not: the ☰'s first row on a phone, a tab
above Settings (above Sign in, before that) in a desk's rail.

THE EXAMPLES ARE FILES, NOT POSTS, so they are there on a site with no posts
yet: Skribl's own cat and its bouncing Flip (its help's demos, named with
skribl_asset as the layers allow), and the site's own draw-back
(static/how/drawback.json: that cat, and a ball of yarn drawn on it with a
real pen through the composer's Pad, joined as the site joins every
draw-back, drawback.py). PARTS is each hand's drawing time in that example,
in the order they play, as its post's row kept them: what its play button
says, since the joined drawing plays hers squeezed.
"""
from .accounts import _page, _rests
from .security import current_person

#: The draw-back example's two hands, in ms: hers (Skribl's cat, 15 sec as
#: it was drawn) and the answer's (6 sec), as the post it was made in kept
#: them (posts.hands). verify_socialapp reads both off the files.
PARTS = (15000, 6000)


def register(bp):
    """Add How it works to the site's blueprint."""

    @bp.get("/how")
    @_rests()
    def how():
        """How it works, the site's own page."""
        return _page("how.html", here="how", me=current_person(), parts=",".join(str(p) for p in PARTS))

    return bp
