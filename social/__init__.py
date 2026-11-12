"""The Skribl site, beside Skribl in the same app (docs/SOCIAL-SITE.md).

THREE LAYERS. Skribl owns everything about a drawing: Pad, Flip, the players,
the Gallery, the posting API. The site owns everything about people: in time,
accounts, profiles, follows, feeds, safety. Hosts mount Skribl. The site is a
host of Skribl like any other, and this package is the site.

PHASE 1, PIECE 1: THE FRAME, READ-ONLY. The Sketchbook look the owner said
"all yes" to (Nov 10), the bar along the bottom of a phone and the rail down
the left of a desk, and three things to do there:

    /social/            Home. For now the first visit, for everyone: Blooby
                        draws his card, "Drawings that draw themselves", Make a
                        skribl and Look around, and the newest public skribls
                        under it.
    /social/explore     Explore: Skribl's own Gallery, New and Hot.
    Make                a small sheet with two doors, Draw into Skribl's Pad
                        and Flip into Skribl's Flip, from the bar, the rail or
                        Home's button. It is not a page.

PHASE 1, PIECE 2: SIGN-IN, invite-only, with passkeys (accounts.py; the
owner's "all yes", Nov 10). Given the host's database session, the site has
accounts: /join#<code>, /signin, /you, /invites (admins), /recover#<code>,
the bar's You (Sign in until then), and its own tables, social_..., built by
a migration chain of their own (social/migrations, social/alembic.ini, its
stamp in social_alembic_version), so Skribl's chain stays Skribl's alone.
Without a session it is the frame alone, as in piece 1.

PHASE 1, PIECE 3: PROFILES WITH DRAWN FACES (profiles.py). /@<handle> is a
person's profile: their face, a skribl they drew of themselves in the Pad's
face mode, drawing itself once (Skribl's face player), their name, handle and
bio, and their public skribls as Skribl's own Gallery section. You is your
own profile, with Edit profile, Draw your face (Redraw my face) and the gear
to the account page (/you, Settings). A face is a skribl the site posts,
unlisted, through Skribl's create_post in the same transaction as the row
that names it; a new one replaces it, and the old one goes through
delete_post.

PHASE 2, COMMENTS (comments.py; the comments mock, the owner's "all yes on
both", Nov 12). A post's own page holds its comments, newest first, each with
its answers one level under it; the box on top for somebody who may comment;
Home's card says how many. So does a drawing's own page (/b/<id>), since the
owner's yes the same day: whatever is opened has them. Deleting a post, a
drawing or an account takes its comments, in code.

PHASE 2, NOTIFICATIONS (activity.py; the notifications mock, the owner's
"all yes", Nov 12). /activity is who said something on your posts and who
answered you, worked out from the comments; a bell at the top right of a
phone's Home and Explore and Activity in a desk's rail take you there, each
with a dot when something is new since you last looked.

ONE SKRIBL, SHARED, PEOPLE TOO. The host hands Skribl the site's signed-in
person as its current user (current_user_id() below) and names them with
describe_author(), so a drawing made in the Pad while signed in is theirs.
The demo's app.py composes both with its own stand-in identity.

ONE SKRIBL, SHARED. init_social() plugs the site into the app Skribl is
already mounted on, so a drawing made in its Pad is a skribl on the site. It is
not a second Skribl beside the first (the stand-in at /host is that, on
purpose, as skribls.net would be).

IT REACHES SKRIBL ONLY THROUGH THE SEAMS ANY HOST USES (docs/INTEGRATION.md):
the in-post player's macros, the Gallery section's macros, the face player's
macros, Skribl's signature, the skribl_asset() global init_skribl adds, url_for
of Skribl's pages (the Pad's with its documented compose flags), and from the
package only documented names: create_post and delete_post with their
exceptions (piece 3, a face). Skribl never imports it. Anything the site needs
from Skribl, every host gets (docs/SOCIAL-SITE.md, section 1). verify_social
section 8 reads both directions, and the Skribl templates and files the site
names.

    import skribl, social
    skribl.init_skribl(app, session=lambda: db.session, ...)
    social.init_social(app, session=lambda: db.session)   # after it; at /social

The demo's app.py does exactly this (SKRIBL_SOCIAL=0 leaves the site out).
"""
import hashlib
import importlib.util
import os

from flask import (Blueprint, abort, current_app, g, has_app_context, has_request_context,
                   render_template, request, url_for)

from .models import PERSON_PREFIX, attach_to_metadata

__all__ = ["init_social", "current_user_id", "describe_author", "hidden_authors",
           "attach_to_metadata", "PERSON_PREFIX"]


def current_user_id():
    """The public id of the person signed in to the site in this request, or
    None (nobody, no request, or no site with accounts on this app). What a
    host hands Skribl as its current user."""
    if not has_request_context() or "social" not in current_app.extensions:
        return None
    from .security import current_user_id as _who
    return _who()


def describe_author(user_id):
    """For Skribl's author resolver: one of the site's people as
    {"username": handle, "display_name": name, "url": their profile, and
    "face": {"id", "w", "h"} once they have drawn one}, else None."""
    if not has_app_context() or "social" not in current_app.extensions:
        return None
    from .accounts import describe_author as _describe
    return _describe(user_id)

def hidden_authors(viewer_id):
    """For Skribl's feed filter and visibility policy (the host installs them,
    as app.py does; docs/SOCIAL-SITE.md "A block reaches Skribl's pages"):
    the public ids of everybody whose drawings Skribl's own pages hide from
    `viewer_id`: a block either way, and anybody an admin has taken down
    (for everybody but themselves). Empty where the site is not running."""
    if not has_app_context() or "social" not in current_app.extensions:
        return frozenset()
    from .safety import hidden_authors as _hidden
    return _hidden(viewer_id)

#: The globals init_skribl() puts in the app's Jinja environment that the
#: site's pages use: skribl_asset for the player's and the Gallery's files,
#: skribl_csrf and skribl_report for the Gallery's report sheet.
_SKRIBL_GLOBALS = ("skribl_asset", "skribl_csrf", "skribl_report")

#: THE SITE'S OWN POLICY, ON ITS OWN PAGES (docs/INTEGRATION.md, "Your site's
#: security headers": Skribl's pages carry Skribl's, and a host's pages keep
#: the host's). Every script here is a file, so there is no nonce. The rest is
#: what Skribl's player and Gallery section need on any page: style
#: attributes, and data: and blob: for images, sound and fetches. The demo's
#: standalone baseline would otherwise give these pages Skribl's policy with
#: an empty nonce, which Chrome reports on every load as an invalid source.
SITE_CSP = "; ".join([
    "default-src 'self'",
    "script-src 'self'",
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data: blob:",
    "media-src 'self' data: blob:",
    "connect-src 'self' data: blob:",
    "font-src 'self'",
    "worker-src 'self' blob:",
    "base-uri 'self'",
    "form-action 'self'",
    "object-src 'none'",
    "frame-ancestors 'self'",
])


#: The most a request to the site's own pages may send (64 KiB).
SITE_MAX_BODY = 64 * 1024


def init_social(app, *, session=None, url_prefix="/social", skribl_blueprint="skribl"):
    """Register the site on `app`, where Skribl is mounted already. Returns
    the blueprint.

    `session` is a callable returning the host's SQLAlchemy session (the one
    Skribl was handed): with it the site has accounts and its own tables;
    without it, the frame alone. The host owns the transaction, as it does
    for Skribl: the site flushes and never commits a request's work.

    `skribl_blueprint` is the name Skribl was registered under, for a host
    that renamed it; the macros take it as `bp` and url_for builds Skribl's
    pages from it. Everything that can fail is asked before the blueprint is
    registered, so a site that does not start leaves the app as it was.
    """
    if skribl_blueprint not in app.blueprints:
        raise RuntimeError(
            "init_social(app) needs Skribl mounted on the same app first: call "
            "skribl.init_skribl(app, ...) before it. The site is a host of "
            "Skribl, not a second Skribl (docs/SOCIAL-SITE.md).")
    missing = [n for n in _SKRIBL_GLOBALS if n not in app.jinja_env.globals]
    if missing:
        raise RuntimeError(
            "init_social(app) needs the template globals init_skribl() adds "
            f"({', '.join(missing)} missing); was Skribl mounted with init_skribl?")
    site = None
    if session is not None:
        # Passkeys are checked by py_webauthn (constraints.txt); without it
        # the site does not start, rather than offering a sign-in that fails.
        if importlib.util.find_spec("webauthn") is None:
            raise RuntimeError("the site's sign-in needs the webauthn package "
                               "(pip install -r constraints.txt --require-hashes)")
        from .security import Site
        site = Site(app, session, url_prefix)

    bp = Blueprint("social", __name__, url_prefix=url_prefix,
                   template_folder="templates", static_folder="static")

    # THE SITE'S OWN FILES, BUSTED BY THEIR CONTENT, the way skribl_asset()
    # busts Skribl's: a changed file gets a new ?v=, so a phone never runs
    # yesterday's script against today's page, and a busted file can be kept
    # for a year. Keyed on (mtime, size) so a request does not re-read it.
    digests = {}

    def digest(filename):
        path = os.path.join(bp.static_folder, filename)
        try:
            st = os.stat(path)
        except OSError:
            return None
        key = (st.st_mtime_ns, st.st_size)
        hit = digests.get(filename)
        if hit is None or hit[0] != key:
            with open(path, "rb") as fh:
                hit = (key, hashlib.sha256(fh.read()).hexdigest()[:8])
            digests[filename] = hit
        return hit[1]

    def social_asset(filename):
        v = digest(filename)
        return url_for("social.static", filename=filename, **({"v": v} if v else {}))

    @bp.get("/")
    def home():
        """The site's Home. Signed in (piece 4): "Say something, then draw
        it...", then everyone's posts, newest first. Otherwise the first visit:
        Blooby's card above the newest public skribls."""
        if site is not None:
            from . import posts
            page = posts.home_page(skribl_blueprint)
            if page is not None:
                return page
        return render_template("social/home.html", here="home")

    @bp.get("/explore")
    def explore():
        """Explore: Skribl's own Gallery section, in the site's frame."""
        return render_template("social/explore.html", here="explore")

    if site is not None:
        from . import accounts, activity, comments, posts, profiles, reports, rules, safety
        accounts.register(bp)
        profiles.register(bp, skribl_blueprint)
        posts.register(bp, skribl_blueprint)
        comments.register(bp)
        activity.register(bp, skribl_blueprint)
        safety.register(bp)
        reports.register(bp, skribl_blueprint)
        rules.register(bp)

        @bp.before_request
        def _small_bodies():
            """A passkey's answer is a few kilobytes and a form's fields fewer:
            anything sent to the site past 64 KiB is refused (413) before it
            is read, rather than parsed at the app's 25 MB limit. By the
            length it declares, whichever page it was sent to (some never
            read their body), and by what is read where it declares none.
            Two pages take more: a drawn face (piece 3) is a whole drawing
            and its share card, up to FACE_MAX_BODY, and a post (piece 4) is
            a whole drawing, a Flip's music included, up to POST_MAX_BODY;
            so is a drawing answer (phase 2, comments), on a post or on a
            drawing."""
            if request.method == "POST":
                cap = {"social.face_save": profiles.FACE_MAX_BODY,
                       "social.post_new": posts.POST_MAX_BODY,
                       "social.comment_new": posts.POST_MAX_BODY,
                       "social.bloob_comment_new": posts.POST_MAX_BODY}.get(request.endpoint, SITE_MAX_BODY)
                request.max_content_length = cap
                if (request.content_length or 0) > cap:
                    abort(413)

    # Context for the site's own pages only (a blueprint processor, not an
    # app-wide one): Skribl's pages never see these names.
    @bp.context_processor
    def _site_context():
        ctx = {"social_asset": social_asset,
               "skribl_bp": skribl_blueprint,
               # Make's two doors, Skribl's own pages, from its own routes.
               "pad_url": url_for(skribl_blueprint + ".skribl_editor"),
               "flip_url": url_for(skribl_blueprint + ".skribl_flip"),
               "accounts": site is not None,
               "me": None}
        if site is not None:
            from .activity import dot_for_request
            from .models import as_utc
            from .safety import REASONS
            from .security import current_person
            ctx["me"] = current_person()
            # Activity's dot (notifications): asked only by a page that shows
            # the bell or the rail, and then once a request.
            ctx["activity_dot"] = dot_for_request
            # What each kind of report may say, in its sheet's order (piece 5).
            ctx["report_reasons"] = REASONS
            # Times are kept in UTC; a page writes them so (an ISO stamp
            # for you.js to show in the person's own zone, and a plain
            # UTC day for a page without scripts).
            ctx["when_iso"] = lambda t: as_utc(t).isoformat() if t else ""
            ctx["when_day"] = lambda t: f"{as_utc(t):%b} {as_utc(t).day}, {as_utc(t).year}" if t else ""
        return ctx

    @bp.after_request
    def _headers(resp):
        if g.get("social_hidden"):
            # A page the asker may not know is there (Invites, to anyone but
            # an admin): its 404 leaves as a missing page's does.
            return resp
        if request.endpoint == "social.static":
            name = (request.view_args or {}).get("filename")
            if (resp.status_code == 200 and name and request.args.get("v")
                    and request.args.get("v") == digest(name)):
                resp.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        elif resp.mimetype == "text/html":
            # A page that holds the Gallery carries a CSRF token for its
            # report sheet, which makes it somebody's (docs/INTEGRATION.md):
            # no shared cache keeps it. no-cache, not no-store, so the back
            # button still restores it whole.
            resp.headers.setdefault("Cache-Control", "private, no-cache")
            # Before any app-wide handler, which a blueprint's always is, so
            # a host's own setdefault leaves this one standing.
            resp.headers.setdefault("Content-Security-Policy", SITE_CSP)
        return resp

    app.register_blueprint(bp)
    if site is not None:
        from .cli import group
        from .security import finish_cookie
        app.extensions["social"] = site
        # App-wide, so a cookie whose sign-in ended elsewhere is cleared on
        # whichever page notices (a Skribl one included), and so the site's
        # own pages set theirs. One look at `g` on every other response.
        app.after_request(finish_cookie)
        if "social" not in app.cli.commands:
            app.cli.add_command(group)
    return bp
