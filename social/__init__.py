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

No accounts yet, so no You, no tables and no migrations. When the site has
tables they are named social_... with their own migration chain, so Skribl's
chain stays Skribl's alone.

ONE SKRIBL, SHARED. init_social() plugs the site into the app Skribl is
already mounted on, so a drawing made in its Pad is a skribl on the site. It is
not a second Skribl beside the first (the stand-in at /host is that, on
purpose, as skribls.net would be).

IT REACHES SKRIBL ONLY THROUGH THE SEAMS ANY HOST USES (docs/INTEGRATION.md):
the in-post player's macros, the Gallery section's macros, Skribl's signature,
the skribl_asset() global init_skribl adds, and url_for of Skribl's pages. It
imports nothing from the skribl package, and Skribl never imports it. Anything
the site needs from Skribl, every host gets (docs/SOCIAL-SITE.md, section 1).
verify_social section 8 reads both directions, and the Skribl templates and
files the site names.

    import skribl, social
    skribl.init_skribl(app, session=lambda: db.session, ...)
    social.init_social(app)                       # after it; at /social

The demo's app.py does exactly this (SKRIBL_SOCIAL=0 leaves the site out).
"""
import hashlib
import os

from flask import Blueprint, render_template, request, url_for

__all__ = ["init_social"]

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


def init_social(app, *, url_prefix="/social", skribl_blueprint="skribl"):
    """Register the site on `app`, where Skribl is mounted already. Returns
    the blueprint.

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
        """The site's Home: in phase 1's first piece, the first visit for everyone."""
        return render_template("social/home.html", here="home")

    @bp.get("/explore")
    def explore():
        """Explore: Skribl's own Gallery section, in the site's frame."""
        return render_template("social/explore.html", here="explore")

    # Context for the site's own pages only (a blueprint processor, not an
    # app-wide one): Skribl's pages never see these names.
    @bp.context_processor
    def _site_context():
        return {"social_asset": social_asset,
                "skribl_bp": skribl_blueprint,
                # Make's two doors, Skribl's own pages, from its own routes.
                "pad_url": url_for(skribl_blueprint + ".skribl_editor"),
                "flip_url": url_for(skribl_blueprint + ".skribl_flip")}

    @bp.after_request
    def _headers(resp):
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
    return bp
