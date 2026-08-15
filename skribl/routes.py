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

from flask import (abort, current_app, g, jsonify, redirect, render_template,
                   request, url_for)
import hashlib

import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError

from .core import (MAX_CARD_BYTES, OG_DEFAULT_DESCRIPTION, OG_DEFAULT_TITLE,
                   SKRIBL_VERSION, _og_meta, _valid_public_id)
from .models import (SkriblIdempotency, SkriblPost, SkriblPostMedia,
                     _visibility_policy, as_utc, session)
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


def _idempotency_hash(raw_key, viewer_id):
    """sha256('<author>|<key>'), or None when the header is absent/unusable.

    Author-scoped so one client's key can never resolve to another's post.
    Keys are bounded (1-200 chars) — an unbounded header would otherwise be a
    free write amplifier into an indexed column.
    """
    if not raw_key or not isinstance(raw_key, str):
        return None
    raw_key = raw_key.strip()
    if not raw_key or len(raw_key) > 200:
        return None
    if viewer_id is None:
        # ANONYMOUS CALLERS GET NO IDEMPOTENCY (v200 follow-up review, F2).
        # v200 scoped them all to one literal namespace, which made the header
        # a shared capability: any two anonymous clients sending the same key
        # resolved to the SAME post — the second caller receiving the first's
        # id and share URL, a disclosure for unlisted posts. The property
        # "one client's key can never resolve to another's post" needs a
        # client identity to scope by, and an anonymous request has none the
        # server can trust. A host that authenticates gets replay protection
        # from the author scope; anonymous lost-response retries fall back to
        # v199 behaviour (a duplicate post), which is an annoyance, not a leak.
        return None
    return hashlib.sha256(f"u{viewer_id}|{raw_key}".encode()).hexdigest()


def _idempotent_replay(idem_hash, fingerprint):
    """The stored response for this key, or None if the key is unused.

    200, not 201: the post already existed when THIS request arrived. The body
    matches the original create response, so a client that missed the first
    answer can proceed identically. A mapping whose post has been deleted
    (the FK cascades) simply no longer exists, and the retry creates anew —
    which is right: the thing the key named is gone.
    """
    row = (session().query(SkriblIdempotency)
           .filter_by(key_hash=idem_hash).first())
    if row is None:
        return None
    if (row.request_fingerprint is not None
            and fingerprint is not None
            and row.request_fingerprint != fingerprint):
        # The key exists but names a DIFFERENT request (v201 review, F4).
        # Refuse rather than silently answer with the old post; a NULL stored
        # fingerprint is a pre-v202 row and replays as originally promised.
        return jsonify({"error": "This Idempotency-Key was already used with "
                                 "a different request body."}), 409
    post = session().query(SkriblPost).options(
        sa.orm.defer(SkriblPost.payload_json)).filter_by(id=row.post_id).first()
    if post is None:
        return None
    return jsonify({
        "id": post.public_id,
        "url": url_for(".skribl_player", public_id=post.public_id),
        "idempotentReplay": True,
    }), 200


def register_routes(bp, *, index_route=False):
    @bp.teardown_request
    def _finish_parked_reservation(exc):
        # POST-SLOT BOOKKEEPING LIVES HERE, after the host transaction ended.
        # Two reasons, one per database:
        #   * Correctness everywhere: the host owns the request transaction
        #     (docs/INTEGRATION.md), so only after it resolves do we know
        #     whether the post landed. Success -> promote the reservation;
        #     any failure — including the host's before-response commit
        #     raising — -> release it, so a failed request does not hold a
        #     slot for the whole window.
        #   * Liveness on SQLite: with real transactions (see models.py's
        #     BEGIN recipe), the host's open write transaction and the
        #     limiter's independent session are two writers on one file; a
        #     promote or release issued mid-request deadlocks against the
        #     very rows it is accounting for. Teardown is after COMMIT or
        #     ROLLBACK, where the lock is free.
        # A teardown-time promotion failure leaves the row 'pending', which
        # still counts within RATE_PENDING_TTL and then ages out — quota can
        # only leak DOWNWARD, briefly, and only if the limiter's own store is
        # failing. This ordering is also why the integration contract requires
        # the host commit BEFORE the response (after_request), never in
        # teardown: a teardown-committing host resolves its transaction after
        # this hook has already had to decide.
        reservation = g.pop("_skribl_post_reservation", None)
        if reservation is None:
            return
        ip, token, succeeded = reservation
        if succeeded and exc is None:
            _rate_commit_post(token)
        else:
            _rate_release_post(ip, token)

    # errorhandler, NOT app_errorhandler: the app_ variant is APPLICATION-WIDE by
    # Flask's own definition, so a host's unrelated oversized upload would have
    # received Skribl's JSON "This Skribl is too large to post" message. Scoped
    # here, it answers only for Skribl's routes.
    @bp.errorhandler(413)
    def _payload_too_large(_error):
        return jsonify({
            "error": "This Skribl is too large to post. Try a smaller photo or a shorter audio loop."
        }), 413

    # Registered ONLY when the host asks for it. Unconditionally claiming "/"
    # meant mounting Skribl silently replaced a host application's homepage —
    # Flask resolves duplicate rules by registration order and the blueprint
    # wins. See create_blueprint(index_route=...).
    if index_route:
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
            # A savepoint, not a rollback: this route is render-always by
            # design, so a database error must not take the page down — but the
            # old `session().rollback()` recovery threw away the HOST's pending
            # work along with our failed read (docs/INTEGRATION.md). Rolling
            # back to a savepoint reopens the transaction for whoever owns it
            # while touching nothing the host had already done.
            with session().begin_nested():
                post = None
                if _valid_public_id(public_id):
                    # Same reason as the feed: this route renders a shell with
                    # the title and caption in the Open Graph tags and nothing
                    # else. The template never references the payload — the
                    # client fetches it separately from /api/skribls/<id> — so
                    # loading it here pulled the whole drawing and its base64
                    # media over the database connection for every view of
                    # every shared link, to discard it.
                    post = (session().query(SkriblPost)
                            .options(sa.orm.defer(SkriblPost.payload_json))
                            .filter_by(public_id=public_id).first())
                # Treat a post the viewer may not read as absent: the shell
                # still renders (this route is render-always by design), the
                # client's fetch 404s, and the visitor gets the standard error
                # panel. What must NOT happen is a private Skribl's title and
                # caption being served to a social scraper in the Open Graph
                # tags.
                if post is not None and not post.visible_to(bp.skribl_current_user_id()):
                    post = None
                if post is not None:
                    title, caption = post.title, post.caption
        except Exception:
            # The savepoint has already unwound; the outer transaction — and
            # anything the host had pending on it — is untouched and remains
            # the host's to finish.
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
            # Savepoint for the same reason as the player shell above: recover
            # from OUR failed read without rolling back the host's transaction.
            with session().begin_nested():
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
                    if decoded is None and isinstance(thumb, str):
                        # EXTERNALISED thumbnail. With an externalising store
                        # the payload holds the STORED URL, not a data URL —
                        # so every card on such a deployment silently fell
                        # back to the generic branded image. Resolution goes
                        # through this post's OWN association rows, matching
                        # each key's presentation URL by equality (v200
                        # follow-up review, F8): parsing a key out of the URL
                        # string reintroduced exactly the derive-authz-from-
                        # presentation mistake put_data_url() was changed to
                        # avoid, and broke silently for any custom store whose
                        # URLs carry a CDN path or query string. A store whose
                        # URLs are non-deterministic (signed, expiring) simply
                        # falls back to the branded card — documented, and
                        # strictly no worse than v199. Bounded by the post's
                        # association fan-out, and still under the visibility
                        # check made above and the size cap below.
                        _store = bp.skribl_media_store
                        if (callable(getattr(_store, "read", None))
                                and callable(getattr(_store, "url_for_key",
                                                     None))):
                            _keys = [row[0] for row in
                                     session().query(SkriblPostMedia.media_key)
                                     .filter_by(post_id=post.id).all()]
                            for _key in _keys:
                                try:
                                    if _store.url_for_key(_key) != thumb:
                                        continue
                                    _got = _store.read(_key)
                                except Exception:
                                    break
                                if isinstance(_got, tuple):
                                    decoded = (_got[0], _got[1])
                                break
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
                        # Public caching only behind the same deployment
                        # opt-in as /media/<key>, for the same reason:
                        # visibility is revocable and a shared cache does not
                        # re-check. visible_to(None) — the ONE predicate again
                        # — so a host policy refusing this post refuses the
                        # cache hint too.
                        if (post.visibility == "public"
                                and post.visible_to(None)
                                and bp.skribl_public_media_cache):
                            resp.headers["Cache-Control"] = "public, max-age=86400"
                        else:
                            resp.headers["Cache-Control"] = "private, no-store"
                        return resp
        except Exception:
            # The savepoint already unwound; the host's transaction is intact.
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
                "error": ("Too many requests from this connection. Nothing was "
                          "lost — wait a little and try again.")
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

        # IDEMPOTENCY (outside review, P1). A response lost in transit leaves
        # the client unable to tell "never happened" from "happened and I
        # missed the answer"; a bare retry then duplicates the post. With an
        # Idempotency-Key header the retry resolves to the SAME post. The
        # lookup runs BEFORE the post-slot reservation, so a replayed success
        # costs no second quota slot. Scoped per author (see
        # SkriblIdempotency); opt-in, so clients without the header behave
        # exactly as before.
        idem_hash = _idempotency_hash(request.headers.get("Idempotency-Key"),
                                      bp.skribl_current_user_id())
        idem_fp = None
        if idem_hash is not None:
            # The fingerprint binds the key to THIS body (v201 review, F4):
            # same key + same fingerprint replays, same key + different
            # fingerprint is refused — never a silent replay of an older post
            # under a reused key. Raw post-inflate bytes: exactly what the
            # parser will see.
            idem_fp = hashlib.sha256(request.get_data(cache=True)).hexdigest()
            prior = _idempotent_replay(idem_hash, idem_fp)
            if prior is not None:
                return prior

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
                # Says the limit, and says the work is safe. The old copy —
                # "you're posting too fast, please wait" — reads as a scolding
                # and leaves the real question ("did I just lose my animation?")
                # unanswered, which is the part that actually alarms someone.
                "error": ("You've hit the posting limit for now. Your Skribl is "
                          "still here — try again in a little while.")
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
                try:
                    # A SAVEPOINT per attempt, not a commit: the request's
                    # transaction belongs to the HOST (docs/INTEGRATION.md). A
                    # public_id collision surfaces at flush — the UNIQUE
                    # violation does not wait for commit — and rolling back to
                    # the savepoint discards only this attempt's rows, never
                    # whatever the host has pending on the same session.
                    with session().begin_nested():
                        post = SkriblPost(
                            public_id=candidate,
                            # The host injects its own resolver via
                            # create_blueprint(current_user_id=...). The default
                            # is ANONYMOUS (None) — not 1, which would have made
                            # every visitor the owner of user 1's private posts.
                            user_id=author_id,
                            title=title,
                            caption=caption,
                            payload_json=stored_payload,
                            has_audio=has_audio,
                            visibility=visibility,
                        )
                        session().add(post)
                        # Flush to get the post id, then record one association
                        # row per stored object — under the SAME savepoint, so a
                        # failed attempt leaves neither behind. An orphan
                        # association would authorise an object on behalf of a
                        # post that does not exist.
                        session().flush()
                        for _key in media_keys:
                            session().add(SkriblPostMedia(post_id=post.id,
                                                          media_key=_key))
                        if idem_hash is not None:
                            # Same savepoint, same (host-owned) transaction as
                            # the post: durable together or not at all, which
                            # is the property a retry needs.
                            session().add(SkriblIdempotency(
                                key_hash=idem_hash, post_id=post.id,
                                request_fingerprint=idem_fp))
                        session().flush()
                except IntegrityError as ie:
                    # RETRY BOUNDARY (outside review follow-up). Retrying is
                    # only correct for the ONE violation a fresh public_id can
                    # cure. This handler used to retry on ANY IntegrityError —
                    # which is how the media-key dedup bug (see
                    # externalise_payload) burned five attempts on a
                    # constraint no new id could satisfy and surfaced as
                    # "Could not allocate a unique id": five wasted inserts
                    # and a diagnosis pointing at the wrong table.
                    diag = str(getattr(ie, "orig", ie))
                    if idem_hash is not None and "key_hash" in diag:
                        # The idempotency index refused the KEY: a concurrent
                        # duplicate won. Resolve to the winner — same
                        # fingerprint rule as the fast path, so a concurrent
                        # DIFFERENT body under the same key gets the 409, not
                        # the other request's post.
                        prior = _idempotent_replay(idem_hash, idem_fp)
                        if prior is not None:
                            return prior
                    if "public_id" not in diag:
                        # Some other constraint. A new candidate cannot fix
                        # it; let the generic handler report THIS error.
                        raise
                    continue
                public_id = candidate
                created = True
                # ALL post-slot bookkeeping happens in TEARDOWN, after the
                # host's transaction has closed (see _finish_parked_reservation
                # for the full why): the rows here are FLUSHED, not committed,
                # and on SQLite the host's open write transaction and the
                # limiter's own session cannot both hold the write lock — a
                # promote or release issued now deadlocks the very request it
                # accounts for. So the reservation is parked with its outcome,
                # and teardown promotes on success or releases on failure.
                g._skribl_post_reservation = (client_ip, post_token, True)
                break
        except Exception:
            # No rollback here: the session and its transaction are the host's
            # (see docs/INTEGRATION.md). The savepoints above have already
            # unwound this route's own rows; deciding the fate of the outer
            # transaction — including whatever the host had pending before this
            # request — is the host's teardown's job, and app.py does exactly
            # that for the standalone deployment.
            raise
        finally:
            if not created and post_token is not None:
                # Parked for teardown, NOT released here: on the failure path
                # the host session may hold this request's flushed-then-
                # poisoned writes, and a limiter delete on a second SQLite
                # connection blocks against that open transaction. Teardown
                # runs after the host transaction ends, where the release is
                # cheap and safe.
                g._skribl_post_reservation = (client_ip, post_token, False)

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

        Any store that can `read` a key is served HERE, through the
        authorisation below — including S3. The gate used to be
        `isinstance(store, LocalDiskStore)`, with a docstring saying an
        S3-backed deployment "hands out bucket URLs and never routes through
        here". That is precisely the shape of the bug this route was written to
        close: externalising media had made a private Skribl's audio and images
        retrievable by anyone holding the URL. A bucket URL cannot ask who is
        looking, so an S3 store returns an app URL and arrives here like the
        rest. See the note above S3Store.
        """
        store = bp.skribl_media_store
        if not callable(getattr(store, "read", None)) or not KEY_RE.match(key or ""):
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
        # ONE predicate for all four surfaces. Payload, card and player ask
        # SkriblPost.visible_to(); this route used to hard-code a
        # public/unlisted/owner allowlist in SQL instead — so a host's
        # visibility policy (set_visibility_policy) was consulted everywhere
        # EXCEPT here. A policy granting its own 'draft' state got a 404 for
        # the media of a post it had just served, and — the dangerous
        # direction — a policy REVOKING readability (moderated, blocked) was
        # ignored and the media served anyway. (Outside review, P0.)
        #
        # With no policy installed, the built-in rule is still evaluated as a
        # single EXISTS — no rows materialised, constant cost regardless of
        # fan-out (the .limit(25)/.limit(1000) false-404 history above). With a
        # policy installed the rule is host Python, so the referencing posts
        # are streamed (payload deferred, batched, no arbitrary cap) and
        # visible_to() is asked post by post, short-circuiting on the first
        # grant. The worst case — every reference refused — walks the full
        # fan-out; that is the honest cost of a Python policy, and it is paid
        # only by deployments that installed one.
        if _visibility_policy() is None:
            readable = sa.select(SkriblPostMedia.id).join(
                SkriblPost, SkriblPost.id == SkriblPostMedia.post_id).where(
                SkriblPostMedia.media_key == key,
                # Allowlist, not "!= private": this must agree with
                # SkriblPost.visible_to, which refuses states it does not know.
                # A query that says "anything but private" would hand out the
                # media of a host-defined 'draft' post while the post itself
                # was refused.
                sa.or_(SkriblPost.visibility.in_(("public", "unlisted")),
                       sa.and_(SkriblPost.user_id == viewer,
                               sa.literal(viewer is not None))))
            granted = session().query(readable.exists()).scalar()
        else:
            granted = False
            refs = (session().query(SkriblPost)
                    .join(SkriblPostMedia,
                          SkriblPost.id == SkriblPostMedia.post_id)
                    .filter(SkriblPostMedia.media_key == key)
                    .options(sa.orm.defer(SkriblPost.payload_json))
                    .yield_per(100))
            for ref in refs:
                if ref.visible_to(viewer):
                    granted = True
                    break
        if not granted:
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
        # ...and only behind the deployment's explicit opt-in. Visibility is
        # REVOCABLE: a post can go public -> private, and a shared cache never
        # re-runs visible_to(), so "public, immutable" turns a revocation into
        # a promise the cache keeps breaking until it expires. The default is
        # therefore private, no-store for EVERYTHING served through an
        # authorisation check; a deployment that accepts the revocation window
        # says so with public_media_cache=True / SKRIBL_PUBLIC_MEDIA_CACHE=1.
        # (Outside review, P0: no shared-public cache responses for
        # viewer-dependent or revocable authorisation without a declaration.)
        public_only = False
        if bp.skribl_public_media_cache:
            if _visibility_policy() is None:
                non_public = sa.select(SkriblPostMedia.id).join(
                    SkriblPost, SkriblPost.id == SkriblPostMedia.post_id).where(
                    SkriblPostMedia.media_key == key,
                    SkriblPost.visibility != "public")
                public_only = not session().query(non_public.exists()).scalar()
            else:
                # A policy can refuse a 'public' post, so under a policy the
                # question is asked the only way it can be answered: is every
                # referencing post readable by an ANONYMOUS viewer? First
                # refusal wins.
                public_only = True
                refs = (session().query(SkriblPost)
                        .join(SkriblPostMedia,
                              SkriblPost.id == SkriblPostMedia.post_id)
                        .filter(SkriblPostMedia.media_key == key)
                        .options(sa.orm.defer(SkriblPost.payload_json))
                        .yield_per(100))
                for ref in refs:
                    if not ref.visible_to(None):
                        public_only = False
                        break
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

        # DEFER THE PAYLOAD. feed_dict() already refuses to serialise it — its
        # docstring is explicit that a feed of fifty multi-megabyte payloads is
        # a hundred megabytes of JSON — but the RESPONSE being clean did nothing
        # about the QUERY, which loaded every payload from the database and threw
        # it away. Measured on twelve modest posts: 3,046,610 B read per request,
        # 9.75 ms against 1.04 ms deferred. At the 100-row cap with real posts
        # that is hundreds of megabytes over the database connection, per feed
        # request, to render metadata.
        q = session().query(SkriblPost).options(sa.orm.defer(SkriblPost.payload_json))

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
            "createdAt": as_utc(post.created_at).isoformat(),
            "author": {
                "id": post.user_id,
                "username": "demo-user"
            },
            "skribl": payload
        })
