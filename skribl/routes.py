"""The seven Skribl routes, as a blueprint.

Route BODIES are unchanged from v131. The mechanical edits are: `@app.get` ->
`@bp.get`, `db.session` -> `session()`, `Model.query` -> `session().query(Model)`,
and `first_or_404()` -> an explicit `abort(404)` (that helper is a
flask_sqlalchemy extension, and Skribl no longer owns a SQLAlchemy instance).

Endpoint names are unchanged, so they become `skribl.home`, `skribl.skribl_player`
and so on once registered. Nothing in the templates or the client JS refers to a
route by literal path any more — see the context processor in __init__.py.
"""
import base64
import os
import secrets

from flask import (abort, current_app, jsonify, redirect, render_template,
                   request, url_for)
from sqlalchemy.exc import IntegrityError

from .core import (MAX_CARD_BYTES, OG_DEFAULT_DESCRIPTION, OG_DEFAULT_TITLE,
                   SKRIBL_VERSION, _og_meta, _valid_public_id)
from .models import SkriblPost, session
from .ratelimit import (_client_ip, _rate_commit_post, _rate_limited,
                        _rate_release_post, _rate_reserve_post)
from .validation import (_decode_data_url_image, _payload_has_audio,
                         _validate_payload_complexity, _validate_payload_media)


def register_routes(bp):
    @bp.app_errorhandler(413)
    def _payload_too_large(_error):
        return jsonify({
            "error": "This Skribl is too large to post. Try a smaller photo or a shorter audio loop."
        }), 413

    @bp.get("/")
    def home():
        return render_template("skribl/skribl_editor.html")

    @bp.get("/skribl-pad")
    def skribl_editor():
        return render_template("skribl/skribl_editor.html")

    @bp.get("/flip")
    def skribl_flip():
        # Flip Mode — the frame-by-frame animation editor (standalone page for now;
        # folds into the pad as an in-app mode in a later phase).
        return render_template("skribl/skribl_flip.html")

    @bp.get("/s/<public_id>")
    def skribl_player(public_id):
        # Server-render Open Graph / Twitter card metadata so shared links unfurl
        # with the Skribl's title + caption — social scrapers don't run the client
        # JS that fills those in. The lookup is best-effort: on a missing post or a
        # transient DB error we fall back to generic tags and still render the same
        # shell, so the existing client flow (which handles missing/invalid) is
        # unchanged. This route stays render-always; it never 404s the page.
        title = caption = None
        try:
            post = None
            if _valid_public_id(public_id):
                post = session().query(SkriblPost).filter_by(public_id=public_id).first()
            if post is not None:
                title, caption = post.title, post.caption
        except Exception:
            try:
                session().rollback()
            except Exception:
                pass
        og_title, og_description = _og_meta(title, caption)
        return render_template(
            "skribl/skribl_player.html",
            public_id=public_id,
            og_title=og_title,
            og_description=og_description,
            # Per-Skribl card: the card route serves the drawing's own thumbnail
            # (stored at post time) and falls back to the static branded card on a
            # miss, so this URL always resolves — and being unique per id, it also
            # stops every shared link from unfurling with the same generic image.
            og_image=url_for(".skribl_card", public_id=public_id, _external=True),
            og_url=url_for(".skribl_player", public_id=public_id, _external=True),
        )

    @bp.get("/s/<public_id>/card.png")
    def skribl_card(public_id):
        # Serve the per-Skribl share-card thumbnail generated client-side at post
        # time and stored in the payload. Best-effort and render-always: on a
        # missing post, missing/'malformed thumbnail, or a transient DB error we
        # redirect to the static branded card so the og:image never 404s.
        try:
            post = None
            if _valid_public_id(public_id):
                post = session().query(SkriblPost).filter_by(public_id=public_id).first()
            if post is not None:
                payload = post.payload_json or {}
                thumb = payload.get("thumbnail") if isinstance(payload, dict) else None
                decoded = _decode_data_url_image(thumb)
                # Size cap: see MAX_CARD_BYTES. Oversize → static fallback below.
                if decoded is not None and len(decoded[0]) > MAX_CARD_BYTES:
                    decoded = None
                if decoded is not None:
                    data, mimetype = decoded
                    resp = current_app.response_class(data, mimetype=mimetype)
                    # Immutable once posted; let scrapers/CDNs cache by URL.
                    resp.headers["Cache-Control"] = "public, max-age=86400"
                    return resp
        except Exception:
            try:
                session().rollback()
            except Exception:
                pass
        return redirect(url_for(".static", filename="og-card.png"))

    @bp.post("/api/skribls")
    def create_skribl():
        # Two budgets (review #7). The ATTEMPT budget is charged on every request
        # and exists to stop request floods; the POST budget is charged only when
        # a post commits, so a burst of malformed bodies can no longer exhaust a
        # shared IP's legitimate posting allowance. Both are checked before any
        # body parsing. 429 is a 4xx, so the composer's existing error path
        # surfaces this verbatim and refuses to fake a success (see sendSkribl).
        client_ip = _client_ip()
        if _rate_limited(client_ip, "attempts"):
            return jsonify({
                "error": "Too many requests — please wait a while and try again."
            }), 429
        # NOTE: the post cap is enforced by _rate_reserve_post immediately before
        # the insert, not here. Checking here and recording after the commit left a
        # window where concurrent requests all saw room and all committed.
        # (Review round 2, #2)

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
        # Review #1: these went straight to .strip() below, so {"title": 123}
        # raised AttributeError and returned 500 instead of a 400.
        for key in ("title", "caption"):
            value = payload.get(key)
            if value is not None and not isinstance(value, str):
                return jsonify({"error": f"'{key}' must be a string or null."}), 400
        # Review #2/#8: structure is capped BEFORE the media walk, so the walk can
        # safely visit every frame without an arbitrary cutoff.
        complexity_error = _validate_payload_complexity(payload)
        if complexity_error:
            return jsonify({"error": complexity_error}), 400
        # Media: type + per-item size caps. See _validate_payload_media. This is
        # the only place a data URL is vetted before it lands in the JSON column.
        media_error = _validate_payload_media(payload)
        if media_error:
            return jsonify({"error": media_error}), 400
        # Frame-format Skribls carry the drawing under frames[] (a classic Skribl
        # is a 1-frame Skribl). Only a gross type check — keep unknown keys working.
        if "frames" in payload and not isinstance(payload["frames"], list):
            return jsonify({"error": "'frames' must be a list."}), 400

        title = (payload.get("title") or "Untitled Skribl").strip()[:80]
        caption = (payload.get("caption") or "").strip()[:300]
        # True only when there are actual audio bytes, whether stored top-level
        # (legacy) or inside a frame (frame-format). See _payload_has_audio.
        has_audio = _payload_has_audio(payload)

        # Retry on the rare public_id collision instead of 500-ing.
        public_id = None
        # Reserve a post slot atomically, right before the only database write.
        # Released below if no row is produced, so a failed insert doesn't burn
        # quota. This makes the single-process limiter internally correct; it is
        # still not distributed (#13). (Review round 2, #2)
        post_token = _rate_reserve_post(client_ip)
        if post_token is None:
            return jsonify({
                "error": "You're posting too fast — please wait a while and try again."
            }), 429

        # try/finally, not a single release on the id-exhaustion path: ANY other
        # exception from commit() (operational error, lost connection, disk full)
        # used to return 500 with the slot still held for the full window.
        # (Review round 3, #1)
        created = False
        try:
            for _attempt in range(5):
                candidate = secrets.token_urlsafe(8)
                post = SkriblPost(
                    public_id=candidate,
                    # Was a hardcoded 1. The host injects its own resolver via
                    # create_blueprint(current_user_id=...); the default still
                    # returns 1, so standalone behaviour is unchanged.
                    user_id=bp.skribl_current_user_id(),
                    title=title,
                    caption=caption,
                    payload_json=payload,
                    has_audio=has_audio,
                )
                session().add(post)
                try:
                    session().commit()
                except IntegrityError:
                    session().rollback()
                    continue
                public_id = candidate
                created = True
                break
        except Exception:
            session().rollback()
            raise
        finally:
            if created:
                _rate_commit_post(post_token)      # durable now — promote it
            else:
                _rate_release_post(client_ip, post_token)

        if not created:
            return jsonify({"error": "Could not allocate a unique id; please retry."}), 503

        return jsonify({
            "id": public_id,
            # Was f"/s/{public_id}" — a root literal, which returned the wrong
            # path the moment Skribl mounted under a prefix. The client trusts
            # this value for the share link, so it has to be built from the
            # route, not from a string. (verify_prefix.py pins it.)
            "url": url_for(".skribl_player", public_id=public_id)
        }), 201

    @bp.get("/api/skribls/<public_id>")
    def get_skribl(public_id):
        if not _valid_public_id(public_id):
            return jsonify({"error": "Skribl not found."}), 404
        post = session().query(SkriblPost).filter_by(public_id=public_id).first()
        # Was first_or_404(), a flask_sqlalchemy Query extension. Skribl no
        # longer owns a SQLAlchemy instance, so the 404 is raised explicitly.
        # Same status, same body, same behaviour.
        if post is None:
            abort(404)

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
