"""The rules, in plain words (phase 1, piece 5, its third part; the owner's
"all yes" on the Safety mock, Nov 12): three short pages, each saying it is a
draft that a lawyer reads before the site opens to everyone.

    /terms      Terms: your drawings are yours, who can join, be kind, and
                what happens when something is reported (the mock's own words)
    /privacy    Privacy: what is kept, what is not done, who sees what, and
                what goes when you leave
    /rules      Community rules: the few rules, with examples, one for each
                reason a report can give

Anybody can read them, signed in or not. Join links them under its age box,
and Settings at its foot. What each says about the site is what the code does
(docs/SOCIAL-SITE.md, "Built: piece 5, the rules"); what only a lawyer can
say is in docs/LAWYER-NOTE.md, for the owner's lawyer.
"""
from .accounts import _page, _rests
from .security import current_person

#: The three pages, in the order their pills show them: (route, name).
PAGES = (("terms", "Terms"), ("privacy", "Privacy"), ("rules", "Community rules"))


def register(bp):
    """Add the three rules pages to the site's blueprint."""

    def page(which):
        return _page("rules.html", here="rules", me=current_person(), page=which, heading=dict(PAGES)[which],
                     pages=PAGES)

    @bp.get("/terms")
    @_rests()
    def terms():
        """Terms, a plain-words draft."""
        return page("terms")

    @bp.get("/privacy")
    @_rests()
    def privacy():
        """Privacy, a plain-words draft."""
        return page("privacy")

    @bp.get("/rules")
    @_rests()
    def rules():
        """Community rules, a plain-words draft."""
        return page("rules")

    return bp
