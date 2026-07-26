import base64
import os
import re
import secrets
import time
from collections import deque
from datetime import datetime, timezone
from threading import Lock

from flask import Flask, g, jsonify, redirect, render_template, request, url_for
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


# Decode a client-generated share-card thumbnail stored in the payload as an
# image data URL back into raw bytes for the card route. Accepts PNG or JPEG:
# the card was historically PNG and is JPEG now (opaque 1200x630, no alpha to
# lose — ~5x smaller), and old PNG posts must keep unfurling, so both are served.
# The subtype is captured so the route can send a matching Content-Type. Kept
# pure and import-light (base64 + re only, no DB/Flask) so it can be unit-tested
# headless. Returns None on anything malformed so the caller can fall back to the
# static branded card instead of erroring.
_DATA_URL_IMAGE_RE = re.compile(r"^data:image/(png|jpeg);base64,(.+)$", re.DOTALL)

# public_id slugs come from secrets.token_urlsafe(8) → 11 chars of [A-Za-z0-9_-].
# Checking the format up front (range is generous for future length changes)
# keeps junk out of DB lookups and template injection surface entirely. Routes
# keep their existing render-always / fallback contracts on a mismatch — this
# only short-circuits the lookup, it never changes what a URL renders.
_PUBLIC_ID_RE = re.compile(r"^[A-Za-z0-9_-]{6,64}$")


def _valid_public_id(public_id):
    return isinstance(public_id, str) and bool(_PUBLIC_ID_RE.match(public_id))


# Hard ceiling for the share-card image served by /s/<id>/card.png. A real
# 1200x630 thumbnail is a few hundred KB; anything much larger in the payload
# is malformed or hostile, and serving (and CDN-caching) it on every unfurl
# would be a cheap amplification. Oversize falls back to the static card.
MAX_CARD_BYTES = 2_000_000

# Naive in-memory per-IP rate limit for POST /api/skribls: N posts per rolling
# window, per process. Not distributed, resets on deploy — deliberately minimal.
# It exists to stop the trivial abuse case (one client looping max-size posts
# until free-tier Postgres fills), not to be real infrastructure; replace with
# proper limiting when auth lands (roadmap #5).
_RATE_WINDOW_SECONDS = 3600
_RATE_MAX_POSTS = int(os.environ.get("SKRIBL_RATE_MAX_POSTS", 20))
_rate_buckets = {}
_rate_lock = Lock()


def _client_ip():
    # On Render the app sits behind a proxy: remote_addr is the proxy, and the
    # real client is the first entry of X-Forwarded-For.
    fwd = request.headers.get("X-Forwarded-For", "")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.remote_addr or "unknown"


def _rate_limited(ip):
    now = time.monotonic()
    with _rate_lock:
        bucket = _rate_buckets.setdefault(ip, deque())
        while bucket and now - bucket[0] > _RATE_WINDOW_SECONDS:
            bucket.popleft()
        if len(bucket) >= _RATE_MAX_POSTS:
            return True
        bucket.append(now)
        # Opportunistic cleanup so the dict can't grow without bound: expire
        # aged entries in every bucket, then drop the empty buckets.
        if len(_rate_buckets) > 1000:
            for key, q in list(_rate_buckets.items()):
                while q and now - q[0] > _RATE_WINDOW_SECONDS:
                    q.popleft()
                if not q:
                    del _rate_buckets[key]
        return False


def _decode_data_url_image(data_url):
    # Returns (raw_bytes, mimetype) for a PNG or JPEG data URL, or None if the
    # value is missing/malformed/an unsupported type (webp, gif, svg, …) so the
    # caller falls back to the static card.
    if not isinstance(data_url, str):
        return None
    m = _DATA_URL_IMAGE_RE.match(data_url.strip())
    if not m:
        return None
    try:
        raw = base64.b64decode(m.group(2), validate=True)
    except Exception:
        return None
    return raw, "image/" + m.group(1)


def _payload_has_audio(payload):
    # Whether a posted Skribl carries actual audio bytes. Frame-aware: audio lives
    # at the top level on a legacy Skribl, or inside a frame on a frame-format one
    # (a classic Skribl is a 1-frame Skribl). A settings-only/empty music dict
    # ({}) doesn't count. Pure + import-light so it can be unit-tested headless.
    if not isinstance(payload, dict):
        return False
    music = payload.get("music")
    if not isinstance(music, dict) or not music.get("data"):
        music = None
        frames = payload.get("frames")
        if isinstance(frames, list):
            for frame in frames:
                if isinstance(frame, dict):
                    m = frame.get("music")
                    if isinstance(m, dict) and m.get("data"):
                        music = m
                        break
    return bool((music or {}).get("data"))


# --- Server-side media validation (INTEGRATION §7) ---------------------------
# The post endpoint is public and unauthenticated, and every media item arrives as
# a base64 data URL inside payload_json. Until now the only limit was
# MAX_CONTENT_LENGTH on the whole request, so a single post could carry ~24 MB of
# arbitrary blob — any type, valid base64 or not — straight into the JSON column.
# At the current rate limit that is ~480 MB/hour/IP into a free-tier Postgres.
#
# These caps are per-item and deliberately generous: a trimmed loop is a couple of
# MB (see the v102 note: a 42s WAV with an 8s loop posts 1.41 MB) and a background
# photo is well under 8 MB. They are env-tunable so a deploy can tighten them
# without a code change.
#
# Type handling is an ALLOW-LIST of top-level types (audio/*, image/*) with SVG
# explicitly excluded — SVG is the one image type that carries script, and nothing
# the client produces is SVG. Subtypes are otherwise left open on purpose: `music`
# is whatever audio file the user picked (mpeg/wav/ogg/mp4/flac/…), and narrowing
# that would reject legitimate uploads for no security gain.
#
# NOT covered here: dimensions and duration, which need real decoding (Pillow /
# an audio decoder) and a dependency this app does not have. Bytes and type are
# the cheap 90%.
MAX_AUDIO_BYTES = int(os.environ.get("SKRIBL_MAX_AUDIO_BYTES", 12_000_000))
MAX_IMAGE_BYTES = int(os.environ.get("SKRIBL_MAX_IMAGE_BYTES", 8_000_000))

_MEDIA_DATA_URL_RE = re.compile(r"^data:([a-zA-Z]+)/([a-zA-Z0-9.+-]+);base64,(.*)$", re.DOTALL)


def _validate_media_data_url(value, expected_type, max_bytes, label):
    # Returns None if acceptable, else a human-readable error string. Pure and
    # import-light (re + base64) so it can be unit-tested headless.
    if value is None:
        return None
    if not isinstance(value, str):
        return f"'{label}' must be a data URL string."
    m = _MEDIA_DATA_URL_RE.match(value.strip())
    if not m:
        return f"'{label}' must be a base64 data URL."
    top, sub, b64 = m.group(1).lower(), m.group(2).lower(), m.group(3)
    if top != expected_type:
        return f"'{label}' must be {expected_type}/*, got {top}/{sub}."
    if top == "image" and sub in ("svg+xml", "svg"):
        return f"'{label}' may not be SVG."
    # Size from the base64 length before decoding, so an oversize payload is
    # rejected without spending the CPU to decode it.
    approx = (len(b64) * 3) // 4
    if approx > max_bytes:
        return f"'{label}' is too large ({approx // 1000} kB; limit {max_bytes // 1000} kB)."
    try:
        base64.b64decode(b64, validate=True)
    except Exception:
        return f"'{label}' is not valid base64."
    return None


def _iter_media_items(payload):
    # Yields (value, expected_type, max_bytes, label) for every media item in a
    # payload, top-level and per-frame. Frame-format Skribls carry media on their
    # frames (a classic Skribl is a 1-frame Skribl), so both must be walked.
    def scan(container, where):
        if not isinstance(container, dict):
            return
        for key, kind, cap in (("music", "audio", MAX_AUDIO_BYTES),
                               ("photo", "image", MAX_IMAGE_BYTES)):
            item = container.get(key)
            if isinstance(item, dict) and item.get("data") is not None:
                yield item["data"], kind, cap, f"{where}{key}.data"

    yield from scan(payload, "")
    thumb = payload.get("thumbnail")
    if thumb is not None:
        yield thumb, "image", MAX_CARD_BYTES, "thumbnail"
    frames = payload.get("frames")
    if isinstance(frames, list):
        for i, frame in enumerate(frames[:200]):   # bounded: don't walk forever
            yield from scan(frame, f"frames[{i}].")


def _validate_payload_media(payload):
    # First error wins; returns None when everything is acceptable.
    for value, kind, cap, label in _iter_media_items(payload):
        err = _validate_media_data_url(value, kind, cap, label)
        if err:
            return err
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

    # A payload over MAX_CONTENT_LENGTH makes Flask raise 413 before the view
    # runs. Return JSON (not Flask's raw HTML page) so the post composer's error
    # path — which reads {error} off a 4xx body — can show an actionable message
    # instead of a bare "rejected (413)". The composer stays open on error, so
    # the user can drop the photo / shorten the loop and retry.
    @app.errorhandler(413)
    def _payload_too_large(_error):
        return jsonify({
            "error": "This Skribl is too large to post. Try a smaller photo or a shorter audio loop."
        }), 413

    @app.get("/")
    def home():
        return render_template("skribl_editor.html")

    @app.get("/skribl-pad")
    def skribl_editor():
        return render_template("skribl_editor.html")

    @app.get("/flip")
    def skribl_flip():
        # Flip Mode — the frame-by-frame animation editor (standalone page for now;
        # folds into the pad as an in-app mode in a later phase).
        return render_template("skribl_flip.html")

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
            post = None
            if _valid_public_id(public_id):
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
            post = None
            if _valid_public_id(public_id):
                post = SkriblPost.query.filter_by(public_id=public_id).first()
            if post is not None:
                payload = post.payload_json or {}
                thumb = payload.get("thumbnail") if isinstance(payload, dict) else None
                decoded = _decode_data_url_image(thumb)
                # Size cap: see MAX_CARD_BYTES. Oversize → static fallback below.
                if decoded is not None and len(decoded[0]) > MAX_CARD_BYTES:
                    decoded = None
                if decoded is not None:
                    data, mimetype = decoded
                    resp = app.response_class(data, mimetype=mimetype)
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
        # Rate limit first, before any body parsing. 429 is a 4xx, so the
        # composer's existing error path surfaces this message verbatim and
        # correctly refuses to fake a success (see sendSkribl).
        if _rate_limited(_client_ip()):
            return jsonify({
                "error": "You're posting too fast — please wait a while and try again."
            }), 429

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

    # --- Content Security Policy ---------------------------------------------
    # Deferred until v105 for a good reason: while gifenc/mp4-muxer came from
    # jsdelivr, any workable policy needed a third-party script-src, and the app
    # also had inline <script type="module"> loaders. Vendoring both libraries
    # (v103/v104) removed the last off-origin script AND the last inline module,
    # so a genuinely strict script-src is now possible.
    #
    # What made this cheap: the templates have ZERO inline event handlers
    # (onclick=...), zero javascript: URLs, and only two inline <script> blocks
    # (the SKRIBL_MODE config in the editor and player). Those two get a
    # per-request nonce. Note that a nonce DISABLES 'unsafe-inline' for scripts
    # in CSP2+ browsers, which is exactly what we want — but it also means any
    # inline handler added later will silently stop firing. verify_csp.py fails
    # loudly if one appears.
    #
    # Deliberate looseness, each load-bearing:
    #   style-src 'unsafe-inline'  — 51 style="..." attributes across the
    #       templates. Style ATTRIBUTES cannot be nonced (a nonce only covers
    #       <style> blocks), so this is required until they're refactored. Much
    #       lower risk than inline script, and there is no user-controlled style
    #       injection surface here.
    #   connect-src data:          — NOT optional. app.js fetches data: URLs
    #       directly (`fetch(data.music.data)`, `fetch(built.dataUrl)`) to get
    #       audio into an ArrayBuffer. Omitting this breaks music loading on the
    #       player and the WAV/MP4 build path, silently.
    #   img-src/media-src data: blob: — canvas toDataURL, new Audio(dataUrl),
    #       and createObjectURL for downloads and playback.
    #
    # NO frame-ancestors, on purpose. The roadmap embeds the player in an iframe
    # on skribls.net, and the previous note here warned that a blanket deny would
    # break that. Omitting the directive leaves framing unrestricted, matching the
    # existing (deliberate) absence of X-Frame-Options. Do not "harden" this
    # without checking the embed first.
    #
    # SKRIBL_CSP=off disables it; SKRIBL_CSP=report-only sends the policy as
    # Content-Security-Policy-Report-Only, so a deploy can watch for violations
    # before enforcing. Default is enforcing.
    csp_mode = os.environ.get("SKRIBL_CSP", "on").strip().lower()

    @app.before_request
    def _make_csp_nonce():
        # Per-request, per-response nonce. Generated for every request (not just
        # rendered ones) so the header and the template can never disagree.
        g.csp_nonce = secrets.token_urlsafe(16)

    @app.context_processor
    def _expose_csp_nonce():
        return {"csp_nonce": getattr(g, "csp_nonce", "")}

    @app.after_request
    def _security_headers(resp):
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        if csp_mode != "off":
            nonce = getattr(g, "csp_nonce", "")
            policy = "; ".join([
                "default-src 'self'",
                f"script-src 'self' 'nonce-{nonce}'",
                "style-src 'self' 'unsafe-inline'",
                "img-src 'self' data: blob:",
                "media-src 'self' data: blob:",
                "connect-src 'self' data: blob:",
                "font-src 'self'",
                "worker-src 'self' blob:",
                "base-uri 'self'",
                "form-action 'self'",
                "object-src 'none'",
            ])
            header = ("Content-Security-Policy-Report-Only"
                      if csp_mode == "report-only" else "Content-Security-Policy")
            resp.headers.setdefault(header, policy)
        return resp

    @app.get("/api/skribls/<public_id>")
    def get_skribl(public_id):
        if not _valid_public_id(public_id):
            return jsonify({"error": "Skribl not found."}), 404
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
