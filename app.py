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


# Markers that say "this is not somebody's laptop". Detection used to be
# `RENDER` or `FLASK_ENV=production` — two names for one platform and one
# convention — so a deployment on Fly, Heroku, Cloud Run, App Service, ECS or a
# plain gunicorn on a VM silently got an EPHEMERAL SECRET_KEY, different in
# every worker. Nothing announces that; it shows up as sessions that drop,
# CSRF tokens rejected by the worker that did not mint them, and a rate limiter
# whose identity HMAC differs per process. (Outside review, low severity.)
#
# The detection is deliberately POSITIVE — it looks for evidence of a
# deployment rather than for evidence of a laptop. A missing marker therefore
# still gets the permissive dev path, which is what keeps `python -c "from app
# import app"` and one-off scripts working. Adding a marker tightens; it never
# loosens.
_PLATFORM_MARKERS = (
    "RENDER",                       # Render
    "DYNO",                         # Heroku
    "FLY_APP_NAME",                 # Fly.io
    "K_SERVICE",                    # Google Cloud Run
    "WEBSITE_SITE_NAME",            # Azure App Service
    "KUBERNETES_SERVICE_HOST",      # any Kubernetes pod
    "ECS_CONTAINER_METADATA_URI",   # AWS ECS
    "ECS_CONTAINER_METADATA_URI_V4",
    "AWS_EXECUTION_ENV",            # AWS Lambda / Fargate
)

#: Application servers that mean "more than one worker is plausible". The
#: Werkzeug dev server is deliberately absent: it is the one that means the
#: opposite. The ASGI names are here because this app is reachable through an
#: adapter, and a deployment that bothered with one is not a laptop.
_APP_SERVERS = ("gunicorn", "uwsgi", "waitress", "mod_wsgi", "hypercorn",
                "uvicorn")


def _looks_like_production():
    # PURE DETECTION. This used to return False when
    # SKRIBL_ALLOW_EPHEMERAL_SECRET=1, which coupled two unrelated decisions:
    # the flag is a promise about the SECRET KEY ("this is single-process, an
    # ephemeral key is fine"), but folding it in here also silently reverted the
    # rate limiter to the per-process memory backend on a real multi-worker
    # deploy — N times the configured budget, with no signal. (Outside review of
    # v263, M1.) The flag is now consulted ONLY where the secret is chosen, so a
    # deployment that opts into an ephemeral secret still gets the shared rate
    # backend it needs. A genuine single-process throwaway on a laptop is not
    # detected as production here anyway, so it keeps the light memory backend.
    if os.environ.get("SKRIBL_ENV", "").strip().lower() == "production":
        return True
    if os.environ.get("FLASK_ENV", "").strip().lower() == "production":
        return True
    if any(os.environ.get(name) for name in _PLATFORM_MARKERS):
        return True
    # gunicorn and uWSGI both advertise themselves here, and both have already
    # imported this module by the time create_app() runs under them.
    software = os.environ.get("SERVER_SOFTWARE", "").lower()
    if any(name in software for name in _APP_SERVERS):
        return True
    import sys
    return any(name in sys.modules for name in ("gunicorn", "uwsgi"))


def create_app():
    app = Flask(__name__)

    # SECRET_KEY: never fall back to a shared, guessable constant. Require it
    # wherever this looks like a real deployment; in local/dev generate a strong
    # random per-process key so `flask run` still works without configuration.
    import secrets
    secret_key = os.environ.get("SECRET_KEY")
    # A PLACEHOLDER is as dangerous as an empty value, and more so, because it
    # passes the `if not secret_key` guard and boots. `.env.example` ships
    # `SECRET_KEY=change-me`; copied verbatim it is a PUBLICLY KNOWN signing
    # key, and anyone who has read this repo can forge a session cookie or a
    # CSRF token against a deployment running it. So production must reject the
    # known placeholders too, not only the empty string. (Outside review of
    # v263, H2.) Match is case-insensitive and trims quotes/space a .env leaves.
    _placeholder = (secret_key or "").strip().strip("'\"").lower() in {
        "", "change-me", "changeme", "change_me", "changemetoo",
        "your-secret-key", "your-secret-key-here", "secret", "secret-key",
        "replace-me", "todo", "xxx", "placeholder",
    }
    if _placeholder:
        # The ephemeral opt-out lives HERE, not in _looks_like_production, so it
        # affects only the secret and never the rate backend (M1).
        _opt_out = os.environ.get("SKRIBL_ALLOW_EPHEMERAL_SECRET") == "1"
        if _looks_like_production() and not _opt_out:
            raise RuntimeError(
                "SECRET_KEY must be set to a real secret in production. This "
                "process looks like a real deployment (see "
                "_looks_like_production), and either an empty value or the "
                "known placeholder from .env.example is unsafe: a shared or "
                "guessable key lets anyone forge a Flask session, a CSRF "
                "double-submit token, or the rate limiter's identity HMAC. "
                "Generate one, e.g. `python -c \"import secrets; "
                "print(secrets.token_urlsafe(32))\"`, or set "
                "SKRIBL_ALLOW_EPHEMERAL_SECRET=1 if this really is a "
                "single-process throwaway.")
        secret_key = secrets.token_urlsafe(32)
    app.config["SECRET_KEY"] = secret_key

    # RATE LIMITER: the library defaults to the in-memory backend, which is
    # per-PROCESS. Behind two gunicorn workers that is two independent limiters
    # granting twice the configured budget, and it resets on every deploy. The
    # library keeps that default because it is right for a single-process
    # unauthenticated dev run and changing it would alter existing deployments;
    # choosing for a DEPLOYMENT is the host's job, and this is the host.
    #
    # So: where this looks like production and the operator has not chosen, pick
    # the durable shared backend. An explicit SKRIBL_RATE_BACKEND always wins,
    # including an explicit "memory". (Outside review, low severity.)
    if _looks_like_production() and not os.environ.get("SKRIBL_RATE_BACKEND"):
        app.config["SKRIBL_RATE_BACKEND"] = "db"

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
    _backend = os.environ.get("SKRIBL_MEDIA_BACKEND", "inline")
    if _backend == "local":
        from flask import url_for
        media_store = skribl.storage.LocalDiskStore(
            os.environ.get("SKRIBL_MEDIA_ROOT",
                           os.path.join(app.instance_path, "media")),
            lambda key: url_for("skribl.media", key=key))
    elif _backend == "s3":
        # Objects are served through /media/<key> so the visibility check on
        # that route still applies — see the note above S3Store. Credentials
        # come from the environment and are never logged.
        from flask import url_for
        media_store = skribl.storage.S3Store(
            os.environ.get("SKRIBL_S3_BUCKET"),
            lambda key: url_for("skribl.media", key=key),
            region=os.environ.get("SKRIBL_S3_REGION", "us-east-1"),
            endpoint=os.environ.get("SKRIBL_S3_ENDPOINT"),
            access_key=os.environ.get("AWS_ACCESS_KEY_ID"),
            secret_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
            session_token=os.environ.get("AWS_SESSION_TOKEN"),
            prefix=os.environ.get("SKRIBL_S3_PREFIX", ""))
    elif _backend != "inline":
        # An unrecognised backend used to leave media_store None, which is the
        # 'inline' path — so `SKRIBL_MEDIA_BACKEND=S3` or a typo silently stored
        # every blob back in the database instead of the bucket the operator
        # asked for, discovered only when payload_json started ballooning.
        # Fail fast on an unknown value. (Outside review of v263, M3.)
        raise RuntimeError(
            f"Unknown SKRIBL_MEDIA_BACKEND {_backend!r}; expected one of "
            f"'inline', 'local', 's3'.")

    skribl.init_skribl(app, session=lambda: db.session,
                       url_prefix=url_prefix, static_url_path=static_url_path,
                       csrf=csrf, media_store=media_store,
                       # Shared-cache opt-in for /media and the share card.
                       # OFF unless the deployment declares it: visibility is
                       # revocable, and `public` cache headers outlive a
                       # revocation. See docs/INTEGRATION.md.
                       public_media_cache=os.environ.get(
                           "SKRIBL_PUBLIC_MEDIA_CACHE", "").strip().lower()
                           in ("1", "true", "yes"),
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

    # TRANSACTION OWNERSHIP (docs/INTEGRATION.md): this app — the HOST — owns
    # the per-request transaction. Skribl's routes flush and use savepoints but
    # never commit or roll back the shared session; the db-backed rate limiter
    # runs on its own sessions entirely. So the commit that makes a POST's rows
    # durable happens HERE, once, per request:
    #
    #   * after_request, not teardown_request: teardown runs after the response
    #     has left, so a commit failure there could not change the status the
    #     client already received. Here it raises before the response is sent
    #     and the client gets the 500 it deserves.
    #   * skipped for 5xx: the request already failed; its pending rows must
    #     die, and the teardown rollback below is what kills them.
    #   * the teardown rollback is a no-op after a successful commit and the
    #     safety net after everything else — including exceptions that never
    #     reached after_request at all.
    @app.after_request
    def _commit_request_transaction(response):
        if response.status_code < 500:
            db.session.commit()
        return response

    @app.teardown_request
    def _rollback_request_transaction(exc):
        db.session.rollback()

    @app.cli.command("init-db")
    def init_db():
        db.create_all()
        print("Initialized database.")

    return app


app = create_app()
