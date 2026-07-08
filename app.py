import os
import secrets
from datetime import datetime, timezone

from flask import Flask, jsonify, render_template, request
from flask_sqlalchemy import SQLAlchemy


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


def create_app():
    app = Flask(__name__)

    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-me")

    database_url = os.environ.get("DATABASE_URL", "sqlite:///skribl_demo.db")

    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    elif database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql+psycopg://", 1)

    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
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
        return render_template("skribl_player.html", public_id=public_id)

    @app.post("/api/skribls")
    def create_skribl():
        payload = request.get_json(silent=True) or {}

        title = (payload.get("title") or "Untitled Skribl").strip()[:80]
        caption = (payload.get("caption") or "").strip()[:300]

        public_id = secrets.token_urlsafe(8)

        post = SkriblPost(
            public_id=public_id,
            user_id=1,
            title=title,
            caption=caption,
            payload_json=payload,
            has_audio=bool(payload.get("music")),
        )

        db.session.add(post)
        db.session.commit()

        return jsonify({
            "id": public_id,
            "url": f"/s/{public_id}"
        }), 201

    @app.get("/api/skribls/<public_id>")
    def get_skribl(public_id):
        post = SkriblPost.query.filter_by(public_id=public_id).first_or_404()

        payload = post.payload_json or {}
        payload["title"] = post.title
        payload["caption"] = post.caption

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
