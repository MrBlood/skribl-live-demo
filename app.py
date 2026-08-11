"""Standalone host for Skribl.

Everything that was Skribl now lives in the `skribl` package as a blueprint.
What is left here is the HOST's job, and it is exactly the job the social-media
site will do instead: own the Flask app, own the database, own the secret key,
and register the blueprint.

The blueprint is registered with no url_prefix and the default static_url_path,
so every URL this serves is identical to v131's. Moving Skribl under /skribl is
a one-line change here — see init_skribl's arguments — and requires no edit to
any template, any client script, or any route.
"""
import os

from flask import Flask
from flask_sqlalchemy import SQLAlchemy

import skribl
import skribl.models
import skribl.security
import skribl.storage
from skribl.core import _env_int

# The ONLY SQLAlchemy instance in the tree. Skribl no longer owns one; it is
# handed this one's session below, which is what a host app will do too.
db = SQLAlchemy()


def create_app():
    app = Flask(__name__)

    # SECRET_KEY: never fall back to a shared, guessable constant. Require it in
    # production (Render sets RENDER=true); in local/dev generate a strong random
    # per-process key so `flask run` still works without configuration.
    import secrets
    secret_key = os.environ.get("SECRET_KEY")
    if not secret_key:
        in_production = bool(os.environ.get("RENDER")) or os.environ.get("FLASK_ENV") == "production"
        if in_production:
            raise RuntimeError("SECRET_KEY must be set in production.")
        secret_key = secrets.token_urlsafe(32)
    app.config["SECRET_KEY"] = secret_key

    database_url = os.environ.get("DATABASE_URL", "sqlite:///skribl_demo.db")

    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    elif database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql+psycopg://", 1)

    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    # Free-tier Postgres drops idle connections; pre_ping checks liveness and
    # transparently reconnects instead of erroring on the first stale request.
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {"pool_pre_ping": True}
    app.config["MAX_CONTENT_LENGTH"] = _env_int("MAX_CONTENT_LENGTH", 25_000_000, minimum=1024)

    db.init_app(app)

    # The integration contract, exercised by the standalone host exactly as a
    # host application would exercise it.
    # Where Skribl mounts. Unset (the default) reproduces v131's root-level URLs
    # exactly. A host application passes its own prefix here — this is the entire
    # change required to move Skribl, because no template and no client script
    # refers to a route by literal path any more.
    url_prefix = os.environ.get("SKRIBL_URL_PREFIX") or None
    if url_prefix:
        # Blueprint static must move with it, or the assets 404 under the prefix.
        static_url_path = "/static"
    else:
        static_url_path = "/static/skribl"

    # CSRF is OPT-IN, and off by default. Standalone Skribl is unauthenticated,
    # so there is no session to protect and turning it on only breaks existing
    # API clients — which is exactly what happened when it was defaulted on:
    # every harness suite that posts without a token got a 403. A host that
    # authenticates this endpoint MUST switch it on; nobody else should.
    # verify_csrf.py boots its own instance with SKRIBL_CSRF_PROTECT=1.
    csrf = None
    if os.environ.get("SKRIBL_CSRF_PROTECT", "0") == "1":
        csrf = skribl.security.double_submit_csrf()

    # Media backend. 'inline' (default) is v131: base64 data URLs stay inside
    # payload_json. 'local' externalises them to content-addressed files served
    # by the blueprint. An S3 deployment subclasses MediaStore and passes it in.
    media_store = None
    if os.environ.get("SKRIBL_MEDIA_BACKEND", "inline") == "local":
        from flask import url_for
        media_store = skribl.storage.LocalDiskStore(
            os.environ.get("SKRIBL_MEDIA_ROOT",
                           os.path.join(app.instance_path, "media")),
            lambda key: url_for("skribl.media", key=key))

    skribl.init_skribl(app, session=lambda: db.session,
                       url_prefix=url_prefix, static_url_path=static_url_path,
                       csrf=csrf, media_store=media_store,
                       # THIS demo is a standalone site, so it wants Skribl on
                       # its homepage. A host application embedding Skribl does
                       # not, and the default is False for exactly that reason.
                       index_route=True)

    # So a single db.create_all() covers Skribl's tables too. Optional — see
    # skribl.models.attach_to_metadata; an Alembic host would migrate
    # SkriblBase.metadata separately instead.
    skribl.models.attach_to_metadata(db.metadata)

    # Standalone only: Skribl is the entire site here, so an unrouted 404 is
    # still Skribl's and must carry the restrictive default. A host application
    # owns its own 404s and must not call this.
    skribl.security.install_standalone_security(app)

    @app.cli.command("init-db")
    def init_db():
        db.create_all()
        print("Initialized database.")

    return app


app = create_app()
