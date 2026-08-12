"""Skribl as a Flask blueprint.

    from skribl import init_skribl
    init_skribl(app, session=lambda: db.session)

`init_skribl` is the whole integration contract. What the host must supply:

  session          callable returning the host's SQLAlchemy Session. Skribl uses
                   the host's session so a Skribl post and a host feed row commit
                   in ONE transaction. Required.
  url_prefix       where the surfaces mount. None (default) reproduces v131's
                   root-level URLs exactly; "/skribl" is the likely host value.
  static_url_path  URL for Skribl's own static files, DEFAULT "/static/skribl"
                   so v131 asset URLs are byte-identical. A host that wants them
                   under the prefix passes "/static".
  current_user_id  callable returning the signed-in user's id, or None.
                   DEFAULTS TO ANONYMOUS (`lambda: None`). It used to default to
                   `lambda: 1`; once visible_to() started consulting it that made
                   every visitor user 1, so user 1's private posts were readable
                   by everyone. It is both the author stamp on POST and the
                   viewer identity for authorisation, so it must be the truth.
                   Skribl never imports flask_login.

What the host does NOT need to give up: its own CSP (Skribl's is attached to the
blueprint, not the app), its own error handlers, its own template namespace
(everything lives under templates/skribl/), or its own static route.

Tables: `skribl.models.SkriblBase.metadata` covers exactly Skribl's three
tables (posts, rate events, post-media associations),
so the host can migrate them with its own Alembic setup.
"""
import hashlib
import os

from flask import Blueprint, url_for

from .core import SKRIBL_VERSION
from .models import SkriblBase, bind_session, create_all, session, set_visibility_policy
from .routes import register_routes
from .security import register_security

__all__ = ["create_blueprint", "init_skribl", "SKRIBL_VERSION",
           "SkriblBase", "create_all", "session"]


_ASSET_CACHE = {}


def asset_url(bp, filename):
    """url_for the blueprint's static file, cache-busted by its CONTENT.

    The cache-bust used to be a hand-typed query string: styles.css?v=124,
    app.js?v=121, audioloop.js?v=102, flip.js?v=131 — four numbers, maintained by
    memory, that nothing checked. verify_version.py explicitly SKIPS them, and
    Playwright starts every run with a cold cache, so a stale bust is invisible
    to the harness by construction. A returning user would silently run old JS
    against a new server.

    This is the same fix already applied to SKRIBL_VERSION, which drifted nine
    releases for the same reason: single-source it, derive it, stop trusting
    anyone to remember. Keyed on (mtime, size) so a rebuilt file re-hashes but a
    served request does not re-read the file every time.
    """
    path = os.path.join(bp.static_folder, filename)
    try:
        st = os.stat(path)
        key = (path, st.st_mtime_ns, st.st_size)
    except OSError:
        # Missing file: let url_for produce the URL and let the 404 be visible,
        # rather than masking it with a fabricated bust.
        return url_for(".static", filename=filename)
    cached = _ASSET_CACHE.get(path)
    if cached is None or cached[0] != key:
        with open(path, "rb") as fh:
            digest = hashlib.sha256(fh.read()).hexdigest()[:8]
        _ASSET_CACHE[path] = (key, digest)
        cached = _ASSET_CACHE[path]
    return url_for(".static", filename=filename, v=cached[1])


def create_blueprint(session=None, url_prefix=None,
                     static_url_path="/static/skribl", current_user_id=None,
                     csrf=None, media_store=None, index_route=False):
    """Build the Skribl blueprint. See the module docstring for the contract.

    `session` is REQUIRED. It defaulted to None, which made the documented
    contract unenforced: models.session() falls back to the process-wide
    binding when an app has none of its own, so a second application
    initialised without one could reach whichever database the last app to
    pass a session had bound. That is the cross-application coupling the
    per-app extension storage exists to prevent, reached through the door left
    open for it. A missing session now fails at startup rather than surfacing
    later as a query against somebody else's data.

    Construction without one, for tests that never touch the database, is
    explicit: pass `session=False`.

    `index_route` defaults to FALSE, and that default is the drop-in contract.
    The blueprint used to register `GET /` unconditionally — a second copy of
    the Pad editor, there so the standalone demo had a landing page. Mounted
    into a host application without a url_prefix, that route SILENTLY REPLACED
    the host's own homepage: Flask resolves duplicate rules by registration
    order, and the blueprint is registered first. A host lost its front page by
    installing a drawing widget, with no error to explain it.

    The demo asks for it explicitly (see app.py). A host that genuinely wants
    Skribl at its root passes `index_route=True` and means it.
    """
    if session is False:
        session = None          # deliberate, not forgotten
    elif session is None:
        raise ValueError(
            "skribl needs a database session: pass session=lambda: db.session "
            "to init_skribl()/create_blueprint(). For a test blueprint that "
            "never queries, pass session=False to say so explicitly.")
    if session is not None:
        bind_session(session)

    bp = Blueprint(
        "skribl", __name__,
        template_folder="templates",
        static_folder="static",
        static_url_path=static_url_path,
        url_prefix=url_prefix,
    )
    # Defaults to ANONYMOUS, not to user 1.
    #
    # It used to default to `lambda: 1`, a stand-in for v131's hardcoded
    # user_id=1 on POST. That was fine as an author stamp and catastrophic as a
    # viewer identity: once `visible_to()` started consulting it, EVERY visitor
    # to the standalone app was user 1, so every private post owned by user 1 was
    # readable by everyone — and anyone could request user 1's feed. "Private"
    # was enforced correctly against an identity that was a lie.
    #
    # None means "nobody is signed in", which is the truth for an unauthenticated
    # deployment, and it is what the authorization rule is written against.
    bp.skribl_current_user_id = current_user_id or (lambda: None)
    # csrf is a THREE-element tuple: (prepare, issue, validate).
    #
    #   prepare()            called in before_request. Resolves the token and
    #                        puts it on `g` so the TEMPLATE can render it. It
    #                        must happen here: a token established in
    #                        after_request arrives after the template has already
    #                        rendered, so the page ships an empty token and every
    #                        post is then refused.
    #   issue(response)      called in after_request. Sets the cookie. Returns
    #                        the response.
    #   validate(request)    -> bool. Called before any mutating handler.
    #
    # It began life as a two-element (issue, validate) pair and grew `prepare`
    # when the ordering bug above was found; the docs kept saying "pair", so a
    # host following them would have hit an IndexError. Use
    # skribl.security.double_submit_csrf(), which returns the triple.
    #
    # None keeps v131 behaviour exactly: no token issued, no check performed,
    # which is right for an UNAUTHENTICATED deployment and wrong the moment one
    # authenticates.
    bp.skribl_csrf = csrf
    # Where media lives. Defaults to inline, i.e. exactly v131: the data URL
    # stays in payload_json. A storage change to a system holding real posts is
    # opted into, never inherited by upgrading.
    from .storage import InlineStore
    bp.skribl_media_store = media_store or InlineStore()
    # Registered on the blueprint's Jinja environment, not the application's.
    # add_app_template_global() would expose skribl_asset to every template in
    # the host app, and calling it there builds a relative endpoint from outside
    # the blueprint — the same BuildError as the context processor above.
    @bp.context_processor
    def _expose_asset_helper():
        return {"skribl_asset": lambda filename: asset_url(bp, filename)}
    register_routes(bp, index_route=index_route)
    register_security(bp, SKRIBL_VERSION)
    return bp


def init_skribl(app, **kwargs):
    """Build the blueprint and register it on `app`. Returns the blueprint."""
    bp = create_blueprint(**kwargs)
    # Store the session factory PER APPLICATION. A module-level global meant the
    # most recently initialised app won for the whole process; see
    # skribl.models.session().
    _sess = kwargs.get("session")
    app.extensions.setdefault("skribl", {})["session"] = None if _sess is False else _sess
    app.register_blueprint(bp)
    # Make the foreign key this package declares actually apply on SQLite, which
    # ignores ON DELETE CASCADE unless the pragma is set per connection. Done
    # HERE rather than at import time so a process that merely imports skribl
    # without mounting it does not have its host's behaviour changed underneath
    # it, and AFTER the session is registered so the pragma can be attached to
    # the engine Skribl was actually given rather than to every engine in the
    # process. Idempotent, inert on PostgreSQL, opt-out with
    # SKRIBL_SQLITE_FOREIGN_KEYS=0 — see skribl.models for the scope note.
    from .models import enable_sqlite_foreign_keys
    enable_sqlite_foreign_keys(app)
    return bp
