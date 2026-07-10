import base64
import os
import re
import secrets
from datetime import datetime, timezone

from flask import Flask, jsonify, redirect, render_template, request, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError


db = SQLAlchemy()


class SkriblPost(db.Model):
    __tablename__ = "skribl_posts"

    id = db.Column(db.Integer, primary_key=True)
    public_id = db.Column(db.String(32), unique=True, nullable=False, index=True)
    user_id = db.Column(db.Integer, nullable=True)
    title = db.Column(db.String(80), nullable=False)
    caption = db.Column(db.String(300), nullable=True)
    payload_json = db.Column(db.JSON, nullable=False)
    has_audio = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)


# Open Graph title/description for a shared Skribl, with generic fallbacks.
# Kept pure and import-free (no DB, no Flask context) so it can be unit-tested
# headless — the route feeds it the post's fields (or None on a miss/error).
OG_DEFAULT_TITLE = "Skribl Pad"
OG_DEFAULT_DESCRIPTION = "A drawing that replays in time with music."


def _og_meta(title, caption):
    og_title = (title or "").strip() or OG_DEFAULT_TITLE
    og_description = (caption or "").strip() or OG_DEFAULT_DESCRIPTION
    return og_title, og_description


# Decode a client-generated share-card thumbnail stored in the payload as a PNG
# data URL ("data:image/png;base64,...") back into raw bytes for the card route.
# Kept pure and import-light (base64 + re only, no DB/Flask) so it can be unit-
# tested headless. Returns None on anything malformed so the caller can fall back
# to the static branded card instead of erroring.
_DATA_URL_PNG_RE = re.compile(r"^data:image/png;base64,(.+)$", re.DOTALL)


def _decode_data_url_png(data_url):
    if not isinstance(data_url, str):
        return None
    m = _DATA_URL_PNG_RE.match(data_url.strip())
    if not m:
        return None
    try:
        return base64.b64decode(m.group(1), validate=True)
    except Exception:
        return None


def create_app():
    app = Flask(__name__)

    # SECRET_KEY: never fall back to a shared, guessable constant. Require it in
    # production (Render sets RENDER=true); in local/dev generate a strong random
    # per-process key so `flask run` still works without configuration.
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
    app.config["MAX_CONTENT_LENGTH"] = int(os.environ.get("MAX_CONTENT_LENGTH", 25_000_000))

    db.init_app(app)

    @app.get("/")
    def home():
        return render_template("skribl_editor.html")

    @app.get("/skribl-pad")
    def skribl_editor():
        return render_template("skribl_editor.html")

    @app.get("/s/<public_id>")
    def skribl_player(public_id):
        # Server-render Open Graph / Twitter card metadata so shared links unfurl
        # with the Skribl's title + caption — social scrapers don't run the client
        # JS that fills those in. The lookup is best-effort: on a missing post or a
        # transient DB error we fall back to generic tags and still render the same
        # shell, so the existing client flow (which handles missing/invalid) is
        # unchanged. This route stays render-always; it never 404s the page.
        title = caption = None
        try:
            post = SkriblPost.query.filter_by(public_id=public_id).first()
            if post is not None:
                title, caption = post.title, post.caption
        except Exception:
            try:
                db.session.rollback()
            except Exception:
                pass
        og_title, og_description = _og_meta(title, caption)
        return render_template(
            "skribl_player.html",
            public_id=public_id,
            og_title=og_title,
            og_description=og_description,
            # Per-Skribl card: the card route serves the drawing's own thumbnail
            # (stored at post time) and falls back to the static branded card on a
            # miss, so this URL always resolves — and being unique per id, it also
            # stops every shared link from unfurling with the same generic image.
            og_image=url_for("skribl_card", public_id=public_id, _external=True),
            og_url=url_for("skribl_player", public_id=public_id, _external=True),
        )

    @app.get("/s/<public_id>/card.png")
    def skribl_card(public_id):
        # Serve the per-Skribl share-card thumbnail generated client-side at post
        # time and stored in the payload. Best-effort and render-always: on a
        # missing post, missing/'malformed thumbnail, or a transient DB error we
        # redirect to the static branded card so the og:image never 404s.
        try:
            post = SkriblPost.query.filter_by(public_id=public_id).first()
            if post is not None:
                payload = post.payload_json or {}
                thumb = payload.get("thumbnail") if isinstance(payload, dict) else None
                data = _decode_data_url_png(thumb)
                if data is not None:
                    resp = app.response_class(data, mimetype="image/png")
                    # Immutable once posted; let scrapers/CDNs cache by URL.
                    resp.headers["Cache-Control"] = "public, max-age=86400"
                    return resp
        except Exception:
            try:
                db.session.rollback()
            except Exception:
                pass
        return redirect(url_for("static", filename="skribl/og-card.png"))

    @app.post("/api/skribls")
    def create_skribl():
        payload = request.get_json(silent=True)

        # Permissive shape validation: the frontend contract is a JSON object
        # (see serializeSkribl). Reject only gross type violations so version
        # bumps and unknown keys keep working; the request body size is already
        # capped by MAX_CONTENT_LENGTH.
        if not isinstance(payload, dict):
            return jsonify({"error": "Body must be a JSON object."}), 400
        for key in ("strokes", "strokeGroups"):
            if key in payload and not isinstance(payload[key], list):
                return jsonify({"error": f"'{key}' must be a list."}), 400
        for key in ("photo", "music", "background", "canvasSize"):
            if key in payload and payload[key] is not None and not isinstance(payload[key], dict):
                return jsonify({"error": f"'{key}' must be an object or null."}), 400
        if payload.get("baseSnapshot") is not None and not isinstance(payload.get("baseSnapshot"), str):
            return jsonify({"error": "'baseSnapshot' must be a string or null."}), 400

        title = (payload.get("title") or "Untitled Skribl").strip()[:80]
        caption = (payload.get("caption") or "").strip()[:300]
        has_audio = bool(payload.get("music"))

        # Retry on the rare public_id collision instead of 500-ing.
        public_id = None
        for _attempt in range(5):
            candidate = secrets.token_urlsafe(8)
            post = SkriblPost(
                public_id=candidate,
                user_id=1,  # TODO: real current_user once auth lands (roadmap #5)
                title=title,
                caption=caption,
                payload_json=payload,
                has_audio=has_audio,
            )
            db.session.add(post)
            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                continue
            public_id = candidate
            break

        if public_id is None:
            return jsonify({"error": "Could not allocate a unique id; please retry."}), 503

        return jsonify({
            "id": public_id,
            "url": f"/s/{public_id}"
        }), 201

    @app.get("/api/skribls/<public_id>")
    def get_skribl(public_id):
        post = SkriblPost.query.filter_by(public_id=public_id).first_or_404()

        # Shallow-copy so we don't mutate the SQLAlchemy-tracked JSON column
        # (which could otherwise be flushed back to the DB on this GET).
        payload = dict(post.payload_json or {})
        payload["title"] = post.title
        payload["caption"] = post.caption
        # The share-card thumbnail is served by /s/<id>/card.png, so the player
        # doesn't need it in the envelope — drop it to keep the GET lean.
        payload.pop("thumbnail", None)

        return jsonify({
            "id": post.public_id,
            "title": post.title,
            "caption": post.caption,
            "hasAudio": post.has_audio,
            "createdAt": post.created_at.isoformat(),
            "author": {
                "id": post.user_id,
                "username": "demo-user"
            },
            "skribl": payload
        })

    @app.cli.command("init-db")
    def init_db():
        db.create_all()
        print("Initialized database.")

    return app


app = create_app()
