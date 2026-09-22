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
from datetime import datetime, timedelta, timezone

from flask import (abort, current_app, g, jsonify, redirect, render_template,
                   request, url_for)
import hashlib

import sqlalchemy as sa

from .core import (HOT_DAYS, MAX_REPORT_NOTE_CHARS, REPORT_REASONS,
                   MAX_CARD_BYTES,
                   OG_DEFAULT_DESCRIPTION, OG_DEFAULT_TITLE, SKRIBL_VERSION,
                   THEME_GROUND, _og_meta, _valid_public_id)
from .models import (SkriblIdempotency, SkriblPost, SkriblPostMedia, SkriblReport, SkriblView,
                     _visibility_policy, as_utc, normalise_user_id,
                     session, feed_filter, author_dict)
from .views import purge_views
from .storage import KEY_RE, LocalDiskStore
from .ratelimit import (_client_ip, _rate_commit_post, _rate_key, _rate_limited,
                        _rate_release_post, _rate_reserve_post)
from .validation import _decode_data_url_image
from .creation import (CLIENT_TOKEN_RE, SkriblIdempotencyRace, SkriblRejected,
                       SkriblUnavailable, create_post)
from .deletion import (SkriblNotFound, SkriblRefused, delete_post,
                       set_post_visibility)


# How long a shared cache may hold an authorisation-dependent response, when a
# deployment has opted into public caching at all.
#
# THIS NUMBER IS THE REVOCATION WINDOW, and it used to be a year. /media/<key>
# answered `public, max-age=31536000, immutable` and the share card
# `public, max-age=86400`, on the reasoning that content-addressed bytes never
# change — which is true of the BYTES and irrelevant to the question a cache is
# actually being asked. What can change is who may read them. An audit of v278
# put it plainly: a one-year immutable response is incompatible with deletion,
# moderation, privacy requests and takedowns, because a CDN keeps serving the
# object without ever reaching Flask again.
#
# `immutable` was the worst of it. It tells a cache not to revalidate even when
# the user reloads, so the one recovery path a person has left is closed too.
# Dropped.
#
# Five minutes is chosen to be short enough that "I deleted it" is true in any
# human timeframe, and long enough to absorb the burst a shared link produces —
# which is the whole reason the opt-in exists. A deployment that needs longer
# needs a CDN purge hook, not a bigger number here, and should keep the default
# (no shared caching at all) until it has one.
PUBLIC_MEDIA_MAX_AGE = 300

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


# HOT'S CURSOR (v304) is its own shape -- "hot|<score>|<id>" -- because the
# keyset it pages by is (seven-day plays, id), not (created_at, id). A cursor
# from one sort handed to the other decodes as unusable, which is a 400, the
# same answer a mangled cursor gets.
MAX_QUERY_CHARS = 80
# HOT_DAYS moved to skribl.core at v305 so skribl/views.py's purge reads the
# same window it must never delete inside of. Imported below with the rest.


def _encode_hot_cursor(score, post_id):
    raw = f"hot|{int(score)}|{int(post_id)}".encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _decode_hot_cursor(cursor):
    """-> (score, id), or None."""
    try:
        pad = "=" * (-len(cursor) % 4)
        raw = base64.urlsafe_b64decode(cursor + pad).decode("utf-8")
        tag, score, ident = raw.split("|")
        if tag != "hot":
            return None
        return int(score), int(ident)
    except (ValueError, TypeError, binascii.Error, UnicodeDecodeError):
        return None


def _like_escape(text):
    """A LIKE pattern from what a person typed: their % and _ are letters."""
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _idempotency_hash(raw_key, viewer_id, client_id=None):
    """sha256('<scope>|<key>'), or None when the header is absent/unusable.

    Scoped so one client's key can never resolve to another's post: by the
    author when there is one, by the client's own capability when there is not.
    Keys are bounded (1-200 chars) — an unbounded header would otherwise be a
    free write amplifier into an indexed column.
    """
    if not raw_key or not isinstance(raw_key, str):
        return None
    raw_key = raw_key.strip()
    if not raw_key or len(raw_key) > 200:
        return None
    if viewer_id is None:
        # AN ANONYMOUS CALLER IS SCOPED BY A CLIENT CAPABILITY, OR NOT AT ALL.
        # v200 scoped every anonymous client to one literal namespace, which
        # made the header a shared capability: two strangers sending the same
        # key resolved to the SAME post, the second receiving the first's id
        # and share URL — a disclosure for unlisted posts (v200 follow-up
        # review, F2). "One client's key can never resolve to another's post"
        # needs an identity to scope by, and for a while the answer was that an
        # anonymous request has none, so a lost-response retry duplicated the
        # post: "an annoyance, not a leak". The acquisition audit of v302 named
        # what that comment missed (SK-AUD-001): the lost response also carried
        # the ONLY copy of the revocation key, so the first post was left live
        # with nobody able to withdraw it.
        # The identity is X-Skribl-Client: a random secret the browser minted
        # once and keeps (lib/posted.js). It is a capability, not a claim —
        # nobody can guess another client's — so scoping by it restores exactly
        # the property F2 demanded, and a request without one, or with a
        # malformed one, gets no namespace and behaves as before.
        cid = _client_capability(client_id)
        if cid is None:
            return None
        return hashlib.sha256(f"c{cid}|{raw_key}".encode()).hexdigest()
    return hashlib.sha256(f"u{viewer_id}|{raw_key}".encode()).hexdigest()


def _client_capability(raw):
    """A client-minted secret from a header, or None when absent/malformed.

    Shared by the idempotency scope (X-Skribl-Client) and the client-minted
    revocation key (X-Skribl-Delete-Token): 32-128 urlsafe-base64 characters,
    the shape secrets.token_urlsafe and getRandomValues both produce. Bounded
    so a header cannot be a write amplifier into an indexed column.
    """
    if not raw or not isinstance(raw, str):
        return None
    raw = raw.strip()
    return raw if CLIENT_TOKEN_RE.match(raw) else None


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
        """Resolve the parked post-slot reservation — promote on success,
        release on failure — WITHOUT assuming teardown ordering.

        On the SUPPORTED topology (host commits before the response), success
        finds the host transaction closed and both operations are cheap. On
        failure paths the host's rollback may not have run yet — Flask runs
        blueprint teardowns before app teardowns — so the limiter's write can
        collide with the host's still-open SQLite transaction. That collision
        is made FAST (bounded busy_timeout on the limiter's SQLite sessions)
        and CONTAINED (caught, logged) rather than divined away: introspecting
        the host session's transaction state under autobegin is guesswork, a
        bounded failed write is mechanics. Quota can leak only downward,
        briefly, only while the limiter's own store is failing or locked, and
        the log line says which (v202 review, F1+F2).

        The RELEASE side no longer costs the poster that wait (v207 review F2,
        owner decision (a)): when the delete cannot be delivered the limiter
        records the release in memory and stops counting the row immediately,
        deleting it on the next request that can get a writer. The exception
        still arrives here and is still logged — the degradation is now a
        deferred delete rather than a held slot. See ratelimit._tombstone_store
        for the scope this does and does not cover.
        """
        reservation = g.pop("_skribl_post_reservation", None)
        if reservation is None:
            return
        ip, token, succeeded = reservation
        try:
            if succeeded and exc is None:
                _rate_commit_post(token)
            else:
                _rate_release_post(ip, token)
        except Exception:
            # The failure-path collision this contains: Flask runs BLUEPRINT
            # teardowns before APP teardowns, so a host whose rollback lives
            # in app teardown (app.py's does) still holds its SQLite write
            # transaction when this fires — and the limiter's write from a
            # second connection hits the lock. The limiter's SQLite sessions
            # carry a SHORT busy_timeout (see _rate_sessionmaker) precisely so
            # that collision resolves in milliseconds as an exception, which
            # lands here, is LOGGED, and leaves the row pending — the
            # RATE_PENDING_TTL reconciliation is the documented and actual
            # degradation. Nothing raises out of teardown: a post the host
            # already committed stays a success, and an original request
            # exception is never masked by bookkeeping (v202 review, F1+F2).
            current_app.logger.exception(
                "skribl: limiter bookkeeping failed in teardown; reservation "
                "%s left pending for TTL recovery.", token)

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
            """Standalone-site root, registered only when index_route=True."""
            return render_template("skribl/skribl_editor.html")

    @bp.get("/skribl-pad")
    def skribl_editor():
        """Pad — the record-and-replay editor."""
        # COMPOSE MODE. ?compose=1 is the Pad opened from a host's post
        # composer — an overlay over their feed, not a page somebody navigated
        # to. It ends in "Add to post", which hands the finished drawing back to
        # the composer and PUBLISHES NOTHING: the host holds the payload on
        # their draft, so re-opening to change it is free and abandoning the
        # draft leaves nothing behind. The single POST happens when the host
        # posts, once. See skribl/static/editor_compose.js.
        #
        # A query flag rather than a separate route: it is the same editor, with
        # the same drawing surface and the same post-time payload work, ending
        # differently. A second route would be a second page to keep in step.
        return render_template("skribl/skribl_editor.html",
                               compose=request.args.get("compose") == "1")

    @bp.get("/flip")
    def skribl_flip():
        """Flip — the frame-by-frame animator."""
        # Flip Mode — the frame-by-frame animation editor (standalone page for now;
        # folds into the pad as an in-app mode in a later phase).
        return render_template("skribl/skribl_flip.html")

    @bp.get("/library")
    def skribl_library():
        """The profile's Skribls tab: what you posted, with a full transport that goes full screen."""
        # Real posts, one payload at a time, played by the shared in-post
        # player -- verify_library.py pins all three. It was a mock until v275,
        # and this comment went on calling it a concept preview of demo drawings
        # for twenty releases after; an outside audit read the comment as
        # current and graded the product on it (SK-AUD-011).
        #
        # WHOSE (v304). Until the gallery, this page read the public listing
        # and called it "Your skribls" -- true only because nothing posted from
        # the editors was ever public, so the page was empty. The gallery made
        # that false the day somebody ticked the box. It is the PROFILE's tab
        # now, and a profile is somebody's: with a host's signed-in user it is
        # GET /api/skribls?user_id=<me> (the listing's own author filter); with
        # no accounts, which is the standalone app, it is what this browser
        # posted -- the same list "Your Skribls" in the menu keeps
        # (lib/posted.js), unlisted posts included, because they are yours.
        # The gallery is the public page; this one never was.
        return render_template("skribl/skribl_library.html",
                               library_user_id=bp.skribl_current_user_id())

    @bp.get("/gallery")
    def skribl_gallery():
        """The public gallery: every Skribl its author chose to show, newest first."""
        # Opt-in, and only opt-in (v304). GET /api/skribls lists posts whose
        # visibility is "public", and the two editors' post sheets send that
        # value only when the author ticks "Show in the public gallery" — a
        # post made without the tick stays unlisted, reachable by its link and
        # listed nowhere. So this page is the listing every host feed reads,
        # rendered on the in-post player, with nothing of its own to filter or
        # invent: what it shows is what people chose. verify_gallery.py drives
        # the choice from both sheets and reads the page.
        # The report sheet's reasons are the API's closed set, rendered from
        # the same tuple, so the sheet cannot offer one the server refuses.
        return render_template("skribl/skribl_gallery.html",
                               report_reasons=REPORT_REASONS,
                               report_note_max=MAX_REPORT_NOTE_CHARS)

    @bp.get("/feed")
    def skribl_feed():
        """The demo host page: the in-post player and composer over the real listing."""
        # PREVIEW ROUTE for the in-post player — the smallest honest host. It
        # renders no posts of its own: the page fetches GET /api/skribls and
        # clones the skribl_inline() macro for each item, so what it shows is
        # whatever this deployment actually has, under the same visibility rules
        # every other reader gets. That is the difference between this and
        # /library above, which draws demo tiles nobody posted.
        #
        # Registered so the component can be seen and driven live
        # (harness/verify_inline.py drives this page). A host does not need this
        # route to embed the player — the two macros in
        # templates/skribl/_skribl_inline_player.html are the product; this is
        # the demonstration of them. Reads no request state and touches no
        # database, so leaving it unlinked is enough if you do not want it.
        return render_template("skribl/skribl_feed.html")

    @bp.get("/manifest.webmanifest")
    def skribl_manifest():
        """The web app manifest a Home Screen install reads: name, icons, colours and where it opens."""
        # A route, not a static file (SK-AUD-013): every URL in it has to
        # follow the blueprint's mount point, and only url_for knows that. The
        # scope is the mount point itself, so the installed app owns Flip, the
        # library and every shared link as well as the Pad it opens on.
        # The icons go through the blueprint's cache-busting asset helper,
        # reached as bp.skribl_asset_url: asset_url lives in __init__, which
        # imports this module, so it is handed across on the blueprint like
        # skribl_media_store rather than imported (verify_seam resolves every
        # name at module level, and a function-local import is invisible to it).
        start = url_for(".skribl_editor")
        body = {
            "name": "Skribl",
            "short_name": "Skribl",
            "description": "Draw a post that plays.",
            "start_url": start,
            "scope": start.rsplit("/", 1)[0] + "/",
            "display": "standalone",
            "background_color": THEME_GROUND["dark"],
            "theme_color": THEME_GROUND["dark"],
            "icons": [
                {"src": bp.skribl_asset_url("icon-192.png"), "sizes": "192x192",
                 "type": "image/png"},
                {"src": bp.skribl_asset_url("icon-512.png"), "sizes": "512x512",
                 "type": "image/png"},
            ],
        }
        resp = jsonify(body)
        resp.mimetype = "application/manifest+json"
        return resp

    @bp.get("/s/<public_id>")
    def skribl_player(public_id):
        """The public player a shared link opens."""
        # Server-render Open Graph / Twitter card metadata so shared links unfurl
        # with the Skribl's title + caption — social scrapers don't run the client
        # JS that fills those in. The lookup is best-effort: on a missing post or a
        # transient DB error we fall back to generic tags and still render the same
        # shell, so the existing client flow (which handles missing/invalid) is
        # unchanged. The SHELL is render-always; the STATUS is not (v290, v287
        # audit SK-BUG-005): a Skribl that is not there, or that this viewer may
        # not see, renders the same page with a 404, so a crawler or a link
        # preview does not cache a 200 for a page with no content and monitoring
        # can tell missing from fine. A failed read is not a missing post — the
        # database's trouble is not the link's — so that path keeps the 200.
        title = caption = None
        found = None            # True: the post is here; False: it is not; None: could not tell
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
                found = post is not None
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
        ), (404 if found is False else 200)

    def _thumbnail_response(public_id):
        """The post's own thumbnail as a response, or None for the caller's fallback.

        One reader for two routes. /s/<id>/card.png is what a link unfurls
        with, and /s/<id>/poster is what the in-post player and the library
        tile show idle; both serve the thumbnail generated client-side at post
        time and stored in the payload, and they part only in what they serve
        when there is none. Best-effort and never an error: on a missing post,
        a missing or malformed thumbnail, or a transient DB error this returns
        None and each route redirects to ITS static fallback, so neither URL
        ever 404s. The visibility check, the externalised-store resolution,
        the size cap and the cache rule are all here, once.
        """
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
                            resp.headers["Cache-Control"] = (
                                f"public, max-age={PUBLIC_MEDIA_MAX_AGE}")
                        else:
                            resp.headers["Cache-Control"] = "private, no-store"
                        return resp
        except Exception:
            # The savepoint already unwound; the host's transaction is intact.
            pass
        return None

    @bp.get("/s/<public_id>/card.png")
    def skribl_card(public_id):
        """The share-card image link unfurls use."""
        # No thumbnail: the branded card. For an unfurl that is the right
        # picture — a link to Skribl, with nothing of the post to show.
        return (_thumbnail_response(public_id)
                or redirect(url_for(".static", filename="og-card.png")))

    @bp.get("/s/<public_id>/poster")
    def skribl_poster(public_id):
        """The idle poster the in-post player and the library tiles show: the drawing, or a blank canvas — never the branded card."""
        # No thumbnail: a blank canvas, 1200x630 like the card so the poster
        # crop (lib/sharecard.js band()) lands the same. The branded card here
        # was the v287 audit's SK-BUG-006: cropped to the drawing's band, every
        # API-created post's tile read "ibl Pad / that replay in time with
        # music", a fragment of an advert where the person's picture belongs.
        # A blank is what "the drawing on its canvas" degrades to when there
        # is no drawing to show.
        return (_thumbnail_response(public_id)
                or redirect(url_for(".static", filename="poster-blank.svg")))

    @bp.post("/api/skribls")
    def create_skribl():
        """Create a post."""
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

        # CSRF, through the same pair the destructive routes use. This was an
        # inline copy of the rule until v299, when DELETE and PATCH gained the
        # check and a second copy would have been a third place for the three
        # to drift apart. See _csrf_ok, below, for when it is enforced at all.
        if not _csrf_ok():
            return _csrf_refusal()

        # IDEMPOTENCY (outside review, P1). A response lost in transit leaves
        # the client unable to tell "never happened" from "happened and I
        # missed the answer"; a bare retry then duplicates the post. With an
        # Idempotency-Key header the retry resolves to the SAME post. The
        # lookup runs BEFORE the post-slot reservation, so a replayed success
        # costs no second quota slot. Scoped per author (see
        # SkriblIdempotency); opt-in, so clients without the header behave
        # exactly as before.
        author_id = bp.skribl_current_user_id()
        idem_hash = _idempotency_hash(request.headers.get("Idempotency-Key"),
                                      author_id,
                                      request.headers.get("X-Skribl-Client"))
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

        # EVERYTHING THE PAYLOAD ITSELF DECIDES IS create_post's, not this
        # route's — validation, visibility, title, media externalisation, the
        # insert and its savepoints. This route contributes only what is HTTP:
        # the two rate budgets, CSRF, the Idempotency-Key header, and JSON. See
        # skribl/creation.py's header for why the split runs exactly there.
        #
        # try/finally, not a single release on the id-exhaustion path: ANY other
        # exception (operational error, lost connection, disk full) used to
        # return 500 with the slot still held for the full window.
        # (Review round 3, #1)
        created = False
        try:
            made = create_post(payload,
                               author_id=author_id,
                               media_store=bp.skribl_media_store,
                               idempotency=((idem_hash, idem_fp)
                                            if idem_hash is not None else None),
                               # The client's own revocation key, if it minted
                               # one (SK-AUD-001; see create_post). Anonymous
                               # only; create_post ignores it for an owner.
                               delete_token=_client_capability(
                                   request.headers.get("X-Skribl-Delete-Token")))
        except SkriblIdempotencyRace:
            # A concurrent request committed first under this key. Resolve to
            # the winner — same fingerprint rule as the fast path, so a
            # concurrent DIFFERENT body under the same key gets the 409, not
            # the other request's post.
            prior = _idempotent_replay(idem_hash, idem_fp)
            if prior is not None:
                return prior
            return jsonify({"error": "A concurrent request is already using "
                                     "this idempotency key."}), 409
        except SkriblRejected as rejected:
            return jsonify({"error": rejected.message}), rejected.status
        except SkriblUnavailable as unavailable:
            return jsonify({"error": unavailable.message}), unavailable.status
        except Exception:
            # No rollback here: the session and its transaction are the host's
            # (see docs/INTEGRATION.md). create_post's savepoints have already
            # unwound this route's own rows; deciding the fate of the outer
            # transaction — including whatever the host had pending before this
            # request — is the host's teardown's job, and app.py does exactly
            # that for the standalone deployment.
            raise
        else:
            created = True
            public_id = made.public_id
            # ALL post-slot bookkeeping happens in TEARDOWN, after the host's
            # transaction has closed (see _finish_parked_reservation for the
            # full why): the rows are FLUSHED, not committed, and on SQLite the
            # host's open write transaction and the limiter's own session cannot
            # both hold the write lock — a promote or release issued now
            # deadlocks the very request it accounts for. So the reservation is
            # parked with its outcome, and teardown promotes on success or
            # releases on failure.
            g._skribl_post_reservation = (client_ip, post_token, True)
        finally:
            if not created and post_token is not None:
                # Parked for teardown, NOT released here: on the failure path
                # the host session may hold this request's flushed-then-
                # poisoned writes, and a limiter delete on a second SQLite
                # connection blocks against that open transaction. Teardown
                # runs after the host transaction ends, where the release is
                # cheap and safe.
                g._skribl_post_reservation = (client_ip, post_token, False)

        body = {
            "id": public_id,
            # Was f"/s/{public_id}" — a root literal, which returned the wrong
            # path the moment Skribl mounted under a prefix. The client trusts
            # this value for the share link, so it has to be built from the
            # route, not from a string. (verify_prefix.py pins it.)
            "url": url_for(".skribl_player", public_id=public_id)
        }
        # THE ONLY TIME THIS VALUE EXISTS. An anonymous post gets a revocation
        # capability; only its SHA-256 is stored, so this response is the sole
        # opportunity to hand the raw token to whoever made the post. A client
        # that discards it has published something it can never withdraw, which
        # is why the standalone app writes it into the local "Your Skribls"
        # entry in the same tick.
        #
        # Absent for an owned post: that one is authorised by its owner and a
        # second credential would only be something else to leak.
        # WHETHER IT HAS SOUND, from the server's own reading of the payload.
        # The client that just posted cannot be trusted to answer this and was
        # never asked: lib/posted.js stored no audio flag at all, so every
        # browser-kept row rendered `has_audio` as undefined and the profile
        # page labelled every one of them SILENT -- including the ones with
        # music (owner, from /library). Same value _payload_has_audio() computed
        # a moment ago and the same one feed_dict() reports, so the row and the
        # listing cannot disagree.
        body["hasAudio"] = bool(made.post.has_audio)
        if made.delete_token:
            body["deleteToken"] = made.delete_token
        return jsonify(body), 201

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
                       # Normalised for the same reason every other comparison
                       # is: the column is text and an integer host passes 42.
                       sa.and_(SkriblPost.user_id == normalise_user_id(viewer),
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
            # Bounded, and NOT immutable — see PUBLIC_MEDIA_MAX_AGE. The bytes
            # are immutable; the permission to read them is not, and only the
            # second one matters to a cache.
            resp.headers["Cache-Control"] = (
                f"public, max-age={PUBLIC_MEDIA_MAX_AGE}")
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
            # NO int() COERCION. It used to parse this and 400 on anything
            # non-numeric, which made the endpoint unusable for a host whose
            # user ids are UUIDs, ULIDs or an OAuth subject — the identities
            # docs/INTEGRATION.md invites, since `current_user_id` is
            # documented as returning "your user id". The column is text now,
            # so the filter compares text; a bounded length is all the
            # validation an opaque identifier can honestly get.
            if len(author) > 255:
                return jsonify({"error": "user_id is too long."}), 400
            author = normalise_user_id(author)
            q = q.filter(SkriblPost.user_id == author)
            # AN AUTHOR'S OWN LISTING SHOWS EVERYTHING THEY OWN (EXT-P1-12).
            # This used to be in_(("public", "private")) under a comment
            # reasoning that "unlisted stay out of listings entirely — they are
            # reachable by link, which is what unlisted means". That is true of
            # PUBLIC listings and false of this one. Unlisted is what a post
            # gets when its author does not tick "Show in the public gallery",
            # which is the default and therefore most posts; the signed-in
            # profile is the page that asks "what have I made"; so the
            # authenticated profile hid nearly everything its owner had, and
            # anyone who lost a link had no way back to their own work.
            #
            # It also split the product in two. With no accounts, "Your
            # Skribls" is what this browser posted, unlisted included, because
            # they are yours (see the /library route). The same sentence has to
            # be true when a host signs somebody in, or "yours" means one thing
            # standalone and another thing mounted.
            #
            # Still only ever for the owner: the branch is already gated on a
            # viewer who IS this author, and the else below is unchanged, so
            # nothing unlisted or private reaches anybody else's request.
            if viewer is not None and author == normalise_user_id(viewer):
                q = q.filter(SkriblPost.visibility.in_(
                    ("public", "unlisted", "private")))
            else:
                q = q.filter(SkriblPost.visibility == "public")
        else:
            q = q.filter(SkriblPost.visibility == "public")

        # SEARCH (v304): a substring of the title or caption, case-folded,
        # bounded, with the person's own % and _ escaped so they are letters.
        # The keyset is unchanged, so a search pages exactly as the listing
        # does; the gallery's box sends it.
        needle = (request.args.get("q") or "").strip()
        if len(needle) > MAX_QUERY_CHARS:
            return jsonify({"error": f"q is longer than {MAX_QUERY_CHARS} characters."}), 400
        if needle:
            pat = "%" + _like_escape(needle) + "%"
            q = q.filter(sa.or_(SkriblPost.title.ilike(pat, escape="\\"),
                                SkriblPost.caption.ilike(pat, escape="\\")))

        # HOT (v304): plays in the last seven days, most first, newest id
        # breaking ties -- computed from skribl_views, never from the
        # running total, so an old post with a big total does not sit on
        # top forever. The default stays New.
        sort = request.args.get("sort", "new")
        if sort not in ("new", "hot"):
            return jsonify({"error": "sort must be new or hot."}), 400
        score = None
        if sort == "hot":
            since = datetime.now(timezone.utc) - timedelta(days=HOT_DAYS)
            recent = (session().query(SkriblView.post_id.label("pid"),
                                      sa.func.count(SkriblView.id).label("n"))
                      .filter(SkriblView.created_at >= since)
                      .group_by(SkriblView.post_id).subquery())
            q = q.outerjoin(recent, recent.c.pid == SkriblPost.id)
            score = sa.func.coalesce(recent.c.n, 0)

        cursor = request.args.get("cursor")
        if cursor and sort == "hot":
            parsed = _decode_hot_cursor(cursor)
            if parsed is None:
                return jsonify({"error": "Invalid cursor."}), 400
            c_score, c_id = parsed
            q = q.filter(sa.or_(score < c_score,
                                sa.and_(score == c_score, SkriblPost.id < c_id)))
        elif cursor:
            parsed = _decode_cursor(cursor)
            if parsed is None:
                return jsonify({"error": "Invalid cursor."}), 400
            c_created, c_id = parsed
            # Strict keyset comparison on the same tuple the sort uses, so a row
            # is never skipped or repeated when timestamps collide.
            q = q.filter(sa.tuple_(SkriblPost.created_at, SkriblPost.id)
                         < sa.tuple_(c_created, c_id))

        # HOST AUTHORIZATION, IN SQL. Everything above filters on the
        # visibility COLUMN. The host's visibility policy — which guards the
        # payload endpoint, the player, the share card and media — was never
        # consulted here, so a post the policy denies still disclosed its
        # existence, title, caption, author and public id through the listing
        # (outside review #3). It has to be part of the QUERY: this feed is
        # keyset-paginated, and dropping rows after the fetch returns short
        # pages and a next_cursor pointing at a row the viewer never saw.
        _ff = feed_filter()
        if _ff is not None:
            q = _ff(q, viewer)

        if score is not None:
            q = q.add_columns(score.label("hot")).order_by(score.desc(), SkriblPost.id.desc())
        else:
            q = q.order_by(SkriblPost.created_at.desc(), SkriblPost.id.desc())

        # Over-fetch by one to learn whether another page exists, without a
        # second COUNT query over the whole filtered set.
        fetched = q.limit(limit + 1).all()
        has_more = len(fetched) > limit
        fetched = fetched[:limit]
        if score is not None:
            rows = [r[0] for r in fetched]
            scores = [int(r[1] or 0) for r in fetched]
            items = []
            for post, n in zip(rows, scores):
                d = post.feed_dict()
                d["views_recent"] = n
                items.append(d)
            nxt = _encode_hot_cursor(scores[-1], rows[-1].id) if (rows and has_more) else None
        else:
            rows = fetched
            items = [r.feed_dict() for r in rows]
            nxt = _encode_cursor(rows[-1]) if (rows and has_more) else None

        return jsonify({"items": items, "next_cursor": nxt})

    def _count_view(post):
        who = _rate_key(_client_ip())
        day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        s = session()
        seen = (s.query(SkriblView.id)
                .filter(SkriblView.post_id == post.id, SkriblView.viewer_hash == who,
                        SkriblView.day == day).first())
        if seen is not None:
            return False
        try:
            with s.begin_nested():
                s.add(SkriblView(post_id=post.id, viewer_hash=who, day=day))
                s.flush()
        except sa.exc.IntegrityError:
            return False
        # ATOMIC, NOT READ-MODIFY-WRITE (EXT-P1-4). This was
        # `post.views_total = (post.views_total or 0) + 1`, which reads the
        # value into Python and writes back a number computed from a snapshot.
        # The uniqueness row above stops ONE viewer being counted twice; it
        # does nothing about two DIFFERENT viewers whose requests interleave,
        # and those are exactly the requests a popular post gets. Both read N,
        # both write N+1, one play is gone. Under-counting is silent, permanent
        # and worst on the posts that matter most, and Hot ranks on this
        # column. The database does the addition now, so concurrent increments
        # serialise on the row instead of racing in the application.
        s.query(SkriblPost).filter(SkriblPost.id == post.id).update(
            {SkriblPost.views_total:
                sa.func.coalesce(SkriblPost.views_total, 0) + 1},
            synchronize_session=False)
        # THE JANITOR RIDES THE WRITE, not the read: only a NEW row triggers
        # it, so the work is proportional to plays rather than to page loads,
        # and it is bounded and best-effort. A deployment that never schedules
        # purge_views() still does not accumulate view rows for ever
        # (PRESEAL-003). Swallowed on purpose, exactly as the rate limiter's
        # janitor is: a cleanup inside somebody's request must never take
        # their request down with it, and the next play tries again.
        try:
            purge_views(s)
        except Exception:                                    # pragma: no cover
            pass
        return True

    @bp.get("/api/skribls/<public_id>")
    def get_skribl(public_id):
        """Fetch one post as JSON."""
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

        # A PLAY, COUNTED (v304). This is the fetch every player makes to
        # play a post -- the in-post player on a tap, the /s/<id> page on
        # load -- so it is where a view is honest. One row per (post, client
        # hash, UTC day), unique, inside a savepoint so a lost race is a
        # duplicate and not a poisoned transaction; the post's running total
        # moves only when a row is new. No address is stored. The host owns
        # the commit, as on every write here; a host that does not commit on
        # GET simply does not count plays.
        _count_view(post)

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
            # Skribl has no user table. It used to answer "demo-user" for
            # every author in every deployment while returning the real id
            # beside it (outside review #8); a host now supplies whatever it
            # knows through models.set_author_resolver().
            "author": author_dict(post.user_id),
            "skribl": payload
        })

    @bp.post("/api/skribls/<public_id>/report")
    def report_skribl(public_id):
        """Report a post: one reason from a closed set, into the operator's queue."""
        # REPORT ON EVERY TILE (v304), and what a report IS: a row in a queue
        # an operator reads (`python -m skribl.takedown --reports`), never an
        # action on the post. Nothing here hides anything, so a flood of
        # reports cannot take a drawing down; it can only fill a queue, and
        # the attempts bucket bounds even that.
        #
        # 404 for a malformed id, an unknown id AND a post the reporter may
        # not read -- the same rule as GET, for the same reason: a 403 would
        # confirm the id exists. You can only report what you could see.
        if not _valid_public_id(public_id):
            return jsonify({"error": "Skribl not found."}), 404
        client_ip = _client_ip()
        if _rate_limited(client_ip, "attempts"):
            return jsonify({"error": "Too many requests. Try again later."}), 429
        if not _csrf_ok():
            return _csrf_refusal()
        post = session().query(SkriblPost).filter_by(public_id=public_id).first()
        if post is None or not post.visible_to(bp.skribl_current_user_id()):
            return jsonify({"error": "Skribl not found."}), 404
        body = request.get_json(silent=True)
        if not isinstance(body, dict):
            return jsonify({"error": "Send a JSON object."}), 400
        reason = body.get("reason")
        if reason not in REPORT_REASONS:
            return jsonify({"error": "reason must be one of: "
                                     + ", ".join(REPORT_REASONS) + "."}), 400
        note = body.get("note")
        if note is not None and not isinstance(note, str):
            return jsonify({"error": "note must be text."}), 400
        note = (note or "").strip()[:MAX_REPORT_NOTE_CHARS] or None
        # WHO, without knowing who: the rate limiter's salted hash of the
        # client, the one identity this package already keeps. One reporter,
        # one post, one row -- a second report from the same hash is answered
        # exactly like the first and writes nothing (ix_report_unique backs
        # the read below against a race, inside a savepoint so a lost race
        # cannot poison the host's transaction).
        who = _rate_key(client_ip)
        s = session()
        existing = (s.query(SkriblReport)
                    .filter(SkriblReport.post_id == post.id,
                            SkriblReport.reporter_hash == who)
                    .first())
        created = False
        if existing is None:
            try:
                with s.begin_nested():
                    s.add(SkriblReport(post_id=post.id, reason=reason, note=note,
                                       reporter_hash=who, state="open"))
                    s.flush()
                created = True
            except sa.exc.IntegrityError:
                created = False
        # NO COMMIT HERE, as on every other write in this file: the host owns
        # the per-request commit (verify_txcontract.py).
        return jsonify({"status": "received", "new": created}), 202

    # ---- taking one back ---------------------------------------------------
    # REGISTERED UNCONDITIONALLY SINCE v279, and the reasoning changed rather
    # than being abandoned. v278 gated these on `skribl_has_identity` because a
    # DELETE on an unauthenticated API is a button marked "erase any Skribl in
    # this deployment". That is still true of an UNAUTHORISED delete — and the
    # gate's cost was that the standalone product, which is the deployed one,
    # could not revoke anything at all. An audit called that out: the mechanism
    # existed and the product contract did not.
    #
    # What makes the route safe without an identity is not the absence of the
    # route, it is the capability. An anonymous post carries a 256-bit secret
    # minted at creation, returned once, stored only as a hash. No token, no
    # deletion — and `_authorised_post` refuses a NULL-owner post to a merely
    # authenticated caller just as firmly as to an anonymous one. So a stranger
    # with a public id still cannot delete anything; the person who made it can.
    #
    # CSRF: create_blueprint refuses to build a blueprint with current_user_id
    # and no explicit csrf decision. An anonymous deployment has no ambient
    # authority to abuse — the token is a bearer credential in the BODY, not a
    # cookie, so a third-party page cannot cause a deletion it does not already
    # hold the secret for.
    #
    # BE PRECISE ABOUT THE OWNED-POST CASE, because this comment used to wave
    # at it with "an authenticated deployment has already settled it" and that
    # is not what settles it. An owned post is authorised by the session
    # cookie, which is exactly the ambient authority CSRF exists to protect.
    #
    # THE VALIDATOR IS NOW CONSULTED HERE TOO, and until v299 it was not: it
    # ran on POST and nowhere else. What protected these two in the meantime
    # was the request SHAPE — DELETE and PATCH with `Content-Type:
    # application/json` are not simple requests, so a cross-origin caller gets
    # a CORS preflight, and this blueprint sends no Access-Control-Allow-*
    # header anywhere (SKRIBL_EMBED_ORIGINS is CSP frame-ancestors, not CORS).
    # The browser refuses before the real request leaves, and a <form> cannot
    # issue either verb at all.
    #
    # THAT PROTECTION WAS REAL AND IT WAS NOT THE ONE NAMED, which is why it
    # is no longer the only one. It lives outside this file and three ordinary
    # changes remove it without touching a line here: adding CORS headers,
    # accepting the token from a query string or form encoding, or a host
    # mounting the blueprint behind something that reflects Origin. An outside
    # review drove the third case end to end — cookie identity, no CSRF header
    # — and got 200 on PATCH and 204 on DELETE against a post it did not own.
    # The clients already send the header (lib/postedui.js, lib/recoverykey.js),
    # so the fix cost one `if` on each route and nothing on the client.
    #
    # Still only enforced when the host WIRED a validator, exactly as POST does:
    # an unauthenticated deployment has no ambient authority to abuse, and
    # refusing a request from a client that was never given a token would break
    # the standalone app for nothing.

    def _csrf_ok():
        return not bp.skribl_csrf or bp.skribl_csrf[2](request)

    def _csrf_refusal():
        return jsonify({"error": "Request could not be verified. "
                                 "Please reload the page and try again."}), 403

    def _submitted_delete_token():
        """The capability from the body, or None.

        Read with silent=True and type-checked: a DELETE with no body at
        all is the ordinary owned-post case, and a non-object root must not
        reach an index. The same shape mistake that made PATCH answer 500
        in v278.
        """
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return None
        tok = data.get("deleteToken")
        return tok if isinstance(tok, str) and tok else None

    @bp.delete("/api/skribls/<public_id>")
    def delete_skribl(public_id):
        """Take a post down — by its author, or with the revocation key issued at post time."""
        # The id shape is checked first so a malformed one cannot reach the
        # query, exactly as GET does.
        if not _valid_public_id(public_id):
            return jsonify({"error": "Skribl not found."}), 404
        if not _csrf_ok():
            return _csrf_refusal()
        try:
            delete_post(public_id,
                        author_id=bp.skribl_current_user_id(),
                        delete_token=_submitted_delete_token())
        except SkriblNotFound as exc:
            # 404 for "no such post" AND for "not yours" — the module
            # raises one exception for both so this route cannot leak the
            # difference even by accident.
            return jsonify({"error": exc.message}), 404
        # NO COMMIT HERE. The first version of this route called
        # session().commit(), and verify_txcontract.py failed it by name —
        # correctly. A commit on the SHARED session commits everything
        # pending on it, so a host with an uncommitted row of its own,
        # mid-request, would have that row made durable by a Skribl
        # deletion. That is the P0 an earlier outside review found and this
        # package was rewritten to stop doing; the fact that deletion is
        # the newest route does not exempt it.
        #
        # The HOST owns the per-request commit — app.py does it in
        # after_request for the standalone deployment, skipping 5xx, with a
        # teardown rollback behind it. delete_post has flushed, so the row
        # is gone as far as this transaction is concerned, and it becomes
        # durable when the host says so.
        #
        # 204: there is nothing left to describe.
        return "", 204

    @bp.patch("/api/skribls/<public_id>")
    def update_skribl_visibility(public_id):
        """Revoke, or re-publish. The only field a post may change."""
        if not _valid_public_id(public_id):
            return jsonify({"error": "Skribl not found."}), 404
        if not _csrf_ok():
            return _csrf_refusal()
        # THE SHAPE IS CHECKED BEFORE ANYTHING IS INDEXED, and the first
        # version of this route did not do that. `"visibility" in body`
        # is true for the JSON array ["visibility"] and for the JSON
        # string "visibility" — membership works on both — and the
        # `body["visibility"]` that followed then raised TypeError, so a
        # malformed-but-valid request came back 500 instead of 400.
        # Reproduced on both roots before this was written.
        #
        # The exact-key test is the other half. The docstring above says
        # visibility is the only field a post may change, and
        # {"visibility": "private", "extra": 1} was accepted with a 200,
        # so the route was looser than its own description. A contract
        # stated in a docstring and not enforced is not a contract.
        body = request.get_json(silent=True)
        # "visibility" is required; "deleteToken" is the optional
        # capability an anonymous author presents instead of ownership.
        # Anything else is refused, so the route stays as narrow as its
        # docstring claims.
        if (not isinstance(body, dict)
                or "visibility" not in body
                or not set(body) <= {"visibility", "deleteToken"}):
            # Deliberately NOT a general-purpose PATCH. Title and caption
            # are part of the posted artefact; visibility is a decision
            # about it, and it is the one the review asked for. Widening
            # this later is a decision, not a default.
            return jsonify({
                "error": "Only 'visibility' can be changed."}), 400
        try:
            new = set_post_visibility(
                public_id, body["visibility"],
                author_id=bp.skribl_current_user_id(),
                delete_token=body.get("deleteToken"))
        except SkriblRefused as exc:
            return jsonify({"error": exc.message}), 400
        except SkriblNotFound as exc:
            return jsonify({"error": exc.message}), 404
        # Flushed, not committed — see the note in delete_skribl above.
        return jsonify({"id": public_id, "visibility": new})
