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
  current_user_id  callable returning the poster's id, or None. Defaults to a
                   callable returning 1, which is v131's hardcoded behaviour —
                   see the TODO it replaces. Skribl never imports flask_login.

What the host does NOT need to give up: its own CSP (Skribl's is attached to the
blueprint, not the app), its own error handlers, its own template namespace
(everything lives under templates/skribl/), or its own static route.

Tables: `skribl.models.SkriblBase.metadata` covers exactly Skribl's two tables,
so the host can migrate them with its own Alembic setup.
"""
import hashlib
import os

from flask import Blueprint, url_for

from .core import SKRIBL_VERSION
from .models import SkriblBase, bind_session, create_all, session
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
                     static_url_path="/static/skribl", current_user_id=None):
    """Build the Skribl blueprint. See the module docstring for the contract."""
    if session is not None:
        bind_session(session)

    bp = Blueprint(
        "skribl", __name__,
        template_folder="templates",
        static_folder="static",
        static_url_path=static_url_path,
        url_prefix=url_prefix,
    )
    bp.skribl_current_user_id = current_user_id or (lambda: 1)
    bp.add_app_template_global(
        lambda filename: asset_url(bp, filename), name="skribl_asset")
    register_routes(bp)
    register_security(bp, SKRIBL_VERSION)
    return bp


def init_skribl(app, **kwargs):
    """Build the blueprint and register it on `app`. Returns the blueprint."""
    bp = create_blueprint(**kwargs)
    app.register_blueprint(bp)
    return bp
