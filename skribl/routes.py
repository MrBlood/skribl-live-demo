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
import binascii
import os
import secrets
from datetime import datetime

from flask import (abort, current_app, jsonify, redirect, render_template,
                   request, url_for)
import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError

from .core import (MAX_CARD_BYTES, OG_DEFAULT_DESCRIPTION, OG_DEFAULT_TITLE,
                   SKRIBL_VERSION, _og_meta, _valid_public_id)
from .models import SkriblPost, SkriblPostMedia, session
from .storage import KEY_RE, LocalDiskStore, externalise_payload
from .ratelimit import (_client_ip, _rate_commit_post, _rate_limited,
                        _rate_release_post, _rate_reserve_post)
from .validation import (_decode_data_url_image, _iter_media_items,
                         _payload_has_audio,
                         _validate_payload_complexity, _validate_payload_media)


# --- feed cursors -----------------------------------------------------------
# Opaque to clients on purpose: an obviously-decodable "offset=40" invites
# clients to construct their own, which then breaks the moment the pagination
# strategy changes. This encodes the sort tuple, nothing secret, so it needs no
# signing — a forged cursor can only select a different page of data the caller
# is already allowed to see.
def _encode_cursor(post):
    raw = f"{post.created_at.isoformat()}|{post.id}".encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _decode_cursor(cursor):
    """-> (datetime, int), or None if the cursor is unusable."""
    try:
        pad = "=" * (-len(cursor) % 4)
        raw = base64.urlsafe_b64decode(cursor + pad).decode("utf-8")
        created, _, ident = raw.rpartition("|")
        return datetime.fromisoformat(created), int(ident)
    except (ValueError, TypeError, binascii.Error, UnicodeDecodeError):
        return None


def register_routes(bp):
    # errorhandler, NOT app_errorhandler: the app_ variant is APPLICATION-WIDE by
    # Flask's own definition, so a host's unrelated oversized upload would have
    # received Skribl's JSON "This Skribl is too large to post" message. Scoped
    # here, it answers only for Skribl's routes.
    @bp.errorhandler(413)
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
            # Treat a post the viewer may not read as absent: the shell still
            # renders (this route is render-always by design), the client's
            # fetch 404s, and the visitor gets the standard error panel. What
            # must NOT happen is a private Skribl's title and caption being
            # served to a social scraper in the Open Graph tags.
            if post is not None and not post.visible_to(bp.skribl_current_user_id()):
                post = None
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
            # The thumbnail IS the drawing. Serving it for a private post leaks
            # the content itself, not merely its existence — so fall through to
            # the generic branded card exactly as for a missing post.
            if post is not None and not post.visible_to(bp.skribl_current_user_id()):
                post = None
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
                    # NEVER `public` for a post that is not public. A shared
                    # CDN or proxy would cache the authorised author's thumbnail
                    # and then serve it to unauthorised viewers without ever
                    # re-running visible_to(). The thumbnail IS the drawing.
                    if post.visibility == "public":
                        resp.headers["Cache-Control"] = "public, max-age=86400"
                    else:
                        resp.headers["Cache-Control"] = "private, no-store"
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

        # CSRF. Only enforced when the host wired a validator — an
        # unauthenticated deployment has nothing to protect, and refusing posts
        # from a client that was never given a token would just break it.
        if bp.skribl_csrf and not bp.skribl_csrf[2](request):
            return jsonify({"error": "Request could not be verified. "
                                     "Please reload the page and try again."}), 403

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

        # Visibility. Defaults to "unlisted", NOT "public": that is exactly what a
        # v131 post already was — reachable by its share link, listed nowhere —
        # so existing clients that never send this field keep their current
        # behaviour instead of silently becoming feed content.
        visibility = payload.get("visibility", "unlisted")
        if visibility not in SkriblPost.VISIBILITIES:
            return jsonify({"error": "Unknown visibility."}), 400
        author_id = bp.skribl_current_user_id()
        # "private" means "the author only", so it is meaningless without an
        # author. Allowing it anonymously creates a post nobody can ever read —
        # including the person who just made it, since visible_to(None) denies a
        # post whose user_id is None. Refuse instead of silently making a
        # write-only Skribl.
        if visibility == "private" and author_id is None:
            return jsonify({
                "error": "A private Skribl needs a signed-in author."
            }), 400

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
            # Externalise media AFTER validation and INSIDE the try. Validation
            # decodes, signature-checks and size-caps every data URL first, so
            # nothing unproven is ever written to the store. And it sits inside
            # the try/finally because it was previously outside it: an exception
            # from externalise_payload (disk full, permissions) escaped with the
            # rate-limit slot still held for the whole window.
            stored_payload, media_keys = externalise_payload(
                payload, bp.skribl_media_store, _iter_media_items)

            for _attempt in range(5):
                candidate = secrets.token_urlsafe(8)
                post = SkriblPost(
                    public_id=candidate,
                    # The host injects its own resolver via
                    # create_blueprint(current_user_id=...). The default is
                    # ANONYMOUS (None) — not 1, which would have made every
                    # visitor the owner of user 1's private posts.
                    user_id=author_id,
                    title=title,
                    caption=caption,
                    payload_json=stored_payload,
                    has_audio=has_audio,
                    visibility=visibility,
                )
                session().add(post)
                # Flush to get the post id, then record one association row per
                # stored object — in the SAME transaction, so a failed commit
                # leaves neither behind. An orphan association would authorise an
                # object on behalf of a post that does not exist.
                session().flush()
                for _key in media_keys:
                    session().add(SkriblPostMedia(post_id=post.id,
                                                  media_key=_key))
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

    @bp.get("/media/<key>")
    def media(key):
        """Serve a content-addressed blob.

        Only meaningful for the local store; an S3-backed deployment hands out
        bucket URLs and never routes through here.
        """
        store = bp.skribl_media_store
        if not isinstance(store, LocalDiskStore) or not KEY_RE.match(key or ""):
            abort(404)

        # AUTHORISE, do not merely validate the key shape.
        #
        # This route previously served any object whose key was well-formed and
        # present on disk, with no reference to the post that owns it. So with
        # SKRIBL_MEDIA_BACKEND=local, a private Skribl's audio and images were
        # retrievable by anyone holding the URL — and the URL is handed out in
        # the payload. Externalising media silently routed around the visibility
        # rule the other three surfaces enforce.
        #
        # A key is content-addressed, so the same object can be referenced by
        # several posts; the viewer needs only ONE of them to be readable.
        viewer = bp.skribl_current_user_id()
        # Indexed equality join through skribl_post_media. This was a
        # CAST(payload_json AS TEXT) LIKE '%key%' scan, which was FORGEABLE (the
        # API preserves unknown JSON fields, so anyone could paste a private
        # object's key into their own public post and be granted a "reference"),
        # unindexed (a full scan of every payload on every blob request), and
        # capped at 25 rows with no ORDER BY (so a widely-referenced object could
        # 404 for someone genuinely authorised). See SkriblPostMedia.
        # Authorisation as a single EXISTS. No rows are materialised at all,
        # so the cost is constant no matter how many posts reference a
        # content-addressed object.
        #
        # This has now been wrong twice in the same way. `.limit(25)` on whole
        # posts, then `.limit(1000)` on two columns — both arbitrary caps with no
        # ORDER BY, so an authorised private reference sitting beyond the cap
        # produced a false 404 for its own owner. A cap is not a fix for
        # unbounded fan-out; not materialising the fan-out is.
        readable = sa.select(SkriblPostMedia.id).join(
            SkriblPost, SkriblPost.id == SkriblPostMedia.post_id).where(
            SkriblPostMedia.media_key == key,
            sa.or_(SkriblPost.visibility != "private",
                   sa.and_(SkriblPost.user_id == viewer,
                           sa.literal(viewer is not None))))
        if not session().query(readable.exists()).scalar():
            # Either referenced by no post at all (orphaned) or by none this
            # viewer may read. Same 404 either way: a different answer for the
            # two cases would confirm the object exists.
            abort(404)

        found = store.read(key)
        if found is None:
            abort(404)
        raw, content_type = found
        resp = current_app.response_class(raw, mimetype=content_type)
        # Content-addressed, so the bytes at this URL can never change: cache
        # forever. This is the whole point of hashing the content for the key.
        # Only cache publicly when EVERY referencing post is public. Content
        # addressing makes the bytes immutable, but it does not make them
        # public, and a shared cache does not re-check authorisation.
        # Cache policy: a second, independent EXISTS. Public only when NO
        # referencing post is non-public.
        non_public = sa.select(SkriblPostMedia.id).join(
            SkriblPost, SkriblPost.id == SkriblPostMedia.post_id).where(
            SkriblPostMedia.media_key == key,
            SkriblPost.visibility != "public")
        public_only = not session().query(non_public.exists()).scalar()
        if public_only:
            resp.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        else:
            resp.headers["Cache-Control"] = "private, no-store"
        # Never let a stored blob be re-interpreted as something executable.
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["Content-Disposition"] = "inline"
        return resp

    @bp.get("/api/skribls")
    def list_skribls():
        """Feed-shaped listing: metadata only, cursor-paginated.

        NOT offset-paginated. OFFSET makes the database walk and discard every
        skipped row, so page 50 costs fifty times page 1, and a post created
        mid-scroll shifts every subsequent page and duplicates an item. A
        keyset cursor on (created_at, id) is O(log n) at any depth and stable
        under concurrent writes, which a live feed always has.

        The payload is deliberately absent — see SkriblPost.feed_dict.
        """
        viewer = bp.skribl_current_user_id()

        try:
            limit = int(request.args.get("limit", 20))
        except (TypeError, ValueError):
            return jsonify({"error": "limit must be a number."}), 400
        # Capped: the limit is attacker-controlled, and an uncapped one is a
        # request for the entire table.
        limit = max(1, min(limit, 100))

        q = session().query(SkriblPost)

        author = request.args.get("user_id")
        if author is not None:
            try:
                author = int(author)
            except (TypeError, ValueError):
                return jsonify({"error": "user_id must be a number."}), 400
            q = q.filter(SkriblPost.user_id == author)
            # Private posts are visible on their author's own listing, and only
            # there. Unlisted stay out of listings entirely — they are reachable
            # by link, which is what "unlisted" means.
            if viewer is not None and author == viewer:
                q = q.filter(SkriblPost.visibility.in_(("public", "private")))
            else:
                q = q.filter(SkriblPost.visibility == "public")
        else:
            q = q.filter(SkriblPost.visibility == "public")

        cursor = request.args.get("cursor")
        if cursor:
            parsed = _decode_cursor(cursor)
            if parsed is None:
                return jsonify({"error": "Invalid cursor."}), 400
            c_created, c_id = parsed
            # Strict keyset comparison on the same tuple the sort uses, so a row
            # is never skipped or repeated when timestamps collide.
            q = q.filter(sa.tuple_(SkriblPost.created_at, SkriblPost.id)
                         < sa.tuple_(c_created, c_id))

        q = q.order_by(SkriblPost.created_at.desc(), SkriblPost.id.desc())

        # Over-fetch by one to learn whether another page exists, without a
        # second COUNT query over the whole filtered set.
        rows = q.limit(limit + 1).all()
        has_more = len(rows) > limit
        rows = rows[:limit]

        return jsonify({
            "items": [r.feed_dict() for r in rows],
            "next_cursor": (_encode_cursor(rows[-1]) if (rows and has_more) else None),
        })

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
        # 404, NOT 403: a 403 would confirm the id exists, which is a disclosure
        # in itself. An unauthorised reader gets the same answer as for an id
        # that was never issued.
        if not post.visible_to(bp.skribl_current_user_id()):
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
