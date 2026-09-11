"""Creating a Skribl post, once, for both callers.

    from skribl import create_post, SkriblRejected

    try:
        made = create_post(payload, author_id=current_user.id)
    except SkriblRejected as exc:
        flash(exc.message)
    else:
        db.session.add(MyFeedRow(skribl_id=made.public_id))
        db.session.commit()

WHY THIS MODULE EXISTS. `POST /api/skribls` is a JSON endpoint, and for a host
whose composer is a browser that is the whole story. It is NOT the whole story
for a host whose composer is a server-side FORM: that host has the payload in
`request.form` on its own view, has already authenticated the author, has
already checked its own CSRF token, and wants the Skribl to land in the SAME
transaction as the feed row that points at it. Telling that host to have its
server POST to its own JSON endpoint means a second request, a second CSRF
dance, a second authentication, and — the part that actually breaks — a
separate transaction, so a failure between the two leaves a Skribl with no post
or a post with no Skribl.

WHAT THIS IS NOT. It is not a second creation path. Everything below used to
live in the body of `create_skribl` in routes.py and was MOVED here, not
retyped; the route now calls this function and does nothing to the payload
itself. That direction matters and is the reason this module is worth its
weight: two functions that both "validate a payload and insert a post" is
precisely the shape of the bug `editor_post.js` records as its own BUG B, where
a post-time step silently stopped running on one of two paths while the
metadata looked identical. `verify_txcontract.py` and `verify_apiedges.py` are
what hold the route to this function.

WHAT STAYED IN THE ROUTE, and why each is HTTP rather than domain:

  * the IP rate limiter — it counts REQUESTS TO SKRIBL'S ENDPOINT. A host
    calling a Python function from its own view is not that. It is also not
    merely inadvisable but IMPOSSIBLE: `_client_ip()` reads the Flask
    `request`, and the reservation's bookkeeping is parked on `g` and resolved
    in a Flask teardown, so a create_post called from a management command or a
    worker has no request to charge and no teardown to settle up in. Proved
    rather than asserted — the mutation that made create_post charge the
    limiter died on "Working outside of request context" before reaching the
    test for it (verify_createpost.py's header). THE HOST OWNS ABUSE CONTROL ON
    ITS OWN PATH.
    This is stated rather than defaulted-to, because a host that assumes it
    inherited Skribl's limiter has an unlimited posting endpoint and no
    indication of it. See docs/INTEGRATION.md.
  * CSRF — the host's form already carried its own token, and Skribl's
    validator is wired to inspect a `request`.
  * the `Idempotency-Key` header, and turning the result into JSON.

TRANSACTIONS ARE UNCHANGED AND STILL THE HOST'S. This function flushes; it
never commits and never rolls back the outer transaction. Each id attempt runs
in its own SAVEPOINT (`begin_nested`), so a public_id collision discards that
attempt's rows and nothing the host had pending. The host commits, and its
feed row commits with the Skribl or neither does.
"""
import secrets

from flask import current_app
from sqlalchemy.exc import IntegrityError

from .core import MAX_CAPTION_CHARS, MAX_TITLE_CHARS, MEDIA_CLAIM_TTL
from .models import (SkriblIdempotency, SkriblPost, SkriblPostMedia,
                     SkriblPendingMedia, normalise_user_id, session,
                     visibility_values)
from .deletion import hash_delete_token
from .storage import claim_media, externalise_payload, pending_media_ready
from .validation import (_iter_media_items, _payload_has_audio,
                         _validate_payload_complexity, _validate_payload_media)


def _installed_media_store():
    """The media store of the registered Skribl blueprint.

    Found by ATTRIBUTE, not by the name "skribl", because a host may register
    the blueprint under another name — `skribl/sweep.py` learned that already
    and this is the same lookup, deliberately. The alternative (defaulting to a
    fresh InlineStore) is worse than failing: photos and audio would be inlined
    into the JSON column on the host's path while the endpoint externalised
    them to disk, so two posts made the same afternoon would be stored two
    different ways and only one of them sweepable.
    """
    app = current_app._get_current_object()
    bp = app.blueprints.get("skribl")
    if bp is None:
        bp = next((b for b in app.blueprints.values()
                   if hasattr(b, "skribl_media_store")), None)
    store = getattr(bp, "skribl_media_store", None) if bp is not None else None
    if store is None:
        raise RuntimeError(
            "skribl.create_post: no Skribl blueprint is registered on this "
            "application, so there is no media store. Call init_skribl(app) "
            "first, or pass media_store= explicitly.")
    return store


class SkriblRejected(Exception):
    """The payload will not be stored, and the reason is safe to show a user.

    `.message` is the SAME string the JSON endpoint puts in its `error` field,
    so a host rendering it into a form has the wording Skribl's own composer
    shows. `.status` is the code the endpoint answers with — 400 for every
    rejection raised here — and exists so the route does not have to map
    exception types back onto numbers.
    """

    status = 400

    def __init__(self, message):
        super().__init__(message)
        self.message = message


class SkriblIdempotencyRace(SkriblRejected):
    """A concurrent request committed first under the same idempotency key.

    Raised INSTEAD of resolving the winner here, because resolving it means
    building a response, which is the route's job and not this module's. The
    route catches this and replays the winner exactly as it does on the fast
    path. A host that passes no idempotency key can never see it.
    """

    status = 409

    def __init__(self):
        super().__init__("A concurrent request is already using this "
                         "idempotency key.")


class SkriblUnavailable(Exception):
    """The post cannot be completed right now, and retrying may work.

    Two causes, both infrastructure rather than the caller's payload, which is
    why they share a 503 and not SkriblRejected's 400: five id attempts all
    collided, or the media reservation could not be written.
    """

    status = 503
    message = "Could not allocate a unique id; please retry."

    def __init__(self, message=None):
        if message:
            self.message = message
        super().__init__(self.message)


class CreatedPost:
    """What a successful creation hands back.

    `post` is the flushed SkriblPost — it HAS an `id` (the insert was flushed
    to get one for the media associations) and it is NOT committed. A host that
    wants to point its own row at the Skribl uses `public_id`; one that wants a
    foreign key uses `post.id`; either way the row it adds afterwards commits in
    the same transaction.

    There is deliberately no `url` here. Building one needs `url_for`, which
    needs an application context and, outside a request, a configured
    SERVER_NAME — neither of which this function should require. The route
    builds the URL from `.skribl_player`, which is also the only way it stays
    correct under a url_prefix, and a host that wants one calls url_for the
    same way.

    `delete_token` is the ONE moment the raw revocation secret exists. It is
    set only for a post with no author (an owned post is authorised by its
    owner and does not need a second, weaker credential), only the SHA-256 of
    it is stored, and it is never recoverable afterwards — losing it means the
    post can no longer be withdrawn. A caller that wants anonymous users to be
    able to take a post back must hand this to them and let them keep it; the
    standalone app stores it beside the local "Your Skribls" entry AND accepts
    one back there, which is the half that makes keeping it worth anything —
    a credential a product can only issue is not a recovery story. See
    `skribl/deletion.py`.
    """

    __slots__ = ("public_id", "post", "media_keys", "delete_token")

    def __init__(self, public_id, post, media_keys, delete_token=None):
        self.public_id = public_id
        self.post = post
        self.media_keys = media_keys
        self.delete_token = delete_token


def create_post(payload, *, author_id=None, media_store=None,
                idempotency=None):
    """Validate `payload` and insert a Skribl post on the host's session.

    payload       the client's JSON object (see serializeSkribl). Visibility,
                  title and caption are read from it, exactly as the endpoint
                  reads them, so a host composes one dict rather than learning
                  a second argument spelling. Note the default is "unlisted",
                  NOT "public" — a host feed wanting listed posts sets
                  payload["visibility"] = "public" itself.
    author_id     the signed-in user's id, or None for anonymous. The endpoint
                  passes its `current_user_id()` resolver's answer; a host
                  passes its own. There is no default resolver here on purpose:
                  a function that guesses the author is how every visitor
                  became user 1 once already (see init_skribl's docstring).
    media_store   where photo/audio bytes are externalised to. Defaults to the
                  blueprint's store when one is installed.
    idempotency   optional (key_hash, request_fingerprint) pair. The endpoint
                  derives these from its header; a host that has its own
                  double-submit guard passes None and no row is written.

    Returns CreatedPost. Raises SkriblRejected for anything the caller can fix,
    SkriblIdempotencyRace when a concurrent request won the key, and
    SkriblUnavailable when five id attempts all collide.
    """
    # ---- shape ------------------------------------------------------------
    # Permissive: the frontend contract is a JSON object. Reject only gross
    # type violations so version bumps and unknown keys keep working; the
    # request body size is capped by MAX_CONTENT_LENGTH on the HTTP path, and
    # a host calling in-process has already chosen to trust its own form.
    if not isinstance(payload, dict):
        raise SkriblRejected("Body must be a JSON object.")
    for key in ("strokes", "strokeGroups"):
        if key in payload and not isinstance(payload[key], list):
            raise SkriblRejected(f"'{key}' must be a list.")
    for key in ("photo", "music", "background", "canvasSize"):
        if key in payload and payload[key] is not None and not isinstance(payload[key], dict):
            raise SkriblRejected(f"'{key}' must be an object or null.")
    if payload.get("baseSnapshot") is not None and not isinstance(payload.get("baseSnapshot"), str):
        raise SkriblRejected("'baseSnapshot' must be a string or null.")
    # Review #1: these went straight to .strip() below, so {"title": 123}
    # raised AttributeError and returned 500 instead of a 400.
    for key in ("title", "caption"):
        value = payload.get(key)
        if value is not None and not isinstance(value, str):
            raise SkriblRejected(f"'{key}' must be a string or null.")
    # Review #2/#8: structure is capped BEFORE the media walk, so the walk can
    # safely visit every frame without an arbitrary cutoff.
    complexity_error = _validate_payload_complexity(payload)
    if complexity_error:
        raise SkriblRejected(complexity_error)
    # Media: type + per-item size caps. See _validate_payload_media. This is
    # the only place a data URL is vetted before it lands in the JSON column.
    media_error = _validate_payload_media(payload)
    if media_error:
        raise SkriblRejected(media_error)
    # Frame-format Skribls carry the drawing under frames[] (a classic Skribl
    # is a 1-frame Skribl). Only a gross type check — keep unknown keys working.
    if "frames" in payload and not isinstance(payload["frames"], list):
        raise SkriblRejected("'frames' must be a list.")

    # ---- visibility, author, text ------------------------------------------
    # Defaults to "unlisted", NOT "public": that is exactly what a v131 post
    # already was — reachable by its share link, listed nowhere — so existing
    # clients that never send this field keep their current behaviour instead
    # of silently becoming feed content.
    visibility = payload.get("visibility", "unlisted")
    # models.visibility_values() = Skribl's three plus anything the host
    # registered with set_visibility_values().
    if visibility not in visibility_values():
        raise SkriblRejected("Unknown visibility.")
    # "private" means "the author only", so it is meaningless without an
    # author. Allowing it anonymously creates a post nobody can ever read —
    # including the person who just made it, since visible_to(None) denies a
    # post whose user_id is None.
    if visibility == "private" and author_id is None:
        raise SkriblRejected("A private Skribl needs a signed-in author.")

    # REJECT, don't truncate. [:80] returned 201 for an over-length title and
    # stored half a sentence, so the caller was told it succeeded and the user
    # lost text with nothing to see.
    # .strip() FIRST, then default: "   " used to survive as '', so the
    # player fell back to the product name while the library said
    # "Untitled Skribl" — one post, two names.
    title = (payload.get("title") or "").strip() or "Untitled Skribl"
    caption = (payload.get("caption") or "").strip()
    for _field, _value, _cap in (("title", title, MAX_TITLE_CHARS),
                                 ("caption", caption, MAX_CAPTION_CHARS)):
        if len(_value) > _cap:
            # The editors show this string to the user as-is (editor_post.js
            # and flip.js surface e.error), so it is written for them, not for
            # a log: no quoted field name, no counts.
            raise SkriblRejected(
                f"{_field.capitalize()}s can be up to {_cap} characters.")
    # True only when there are actual audio bytes, whether stored top-level
    # (legacy) or inside a frame (frame-format). See _payload_has_audio.
    has_audio = _payload_has_audio(payload)

    idem_hash, idem_fp = idempotency if idempotency else (None, None)

    # ---- externalise, then insert -----------------------------------------
    # Externalise media AFTER validation: validation decodes, signature-checks
    # and size-caps every data URL first, so nothing unproven is ever written
    # to the store.
    if media_store is None:
        media_store = _installed_media_store()
    stored_payload, media_keys = externalise_payload(
        payload, media_store, _iter_media_items)

    # Reserve the objects we just wrote BEFORE the association commits (H3).
    # The claim is committed on its own connection, so the orphan sweeper sees
    # it immediately and spares these objects during the window between the
    # bytes landing and this transaction committing.
    #
    # THIS FAILS THE POST RATHER THAN DEGRADING, and it used to do the
    # opposite. The claim was wrapped in `except Exception: pass` and described
    # as best-effort, "degrades to the pre-v266 age re-check". An audit of v278
    # pointed out what that sentence is actually promising: storage.py's own
    # note says the age re-check does NOT close the window — "the sweeper can
    # still delete AFTER a successful utime" — which is precisely why this
    # claim was introduced. So the fallback was a mechanism the tree already
    # documents as insufficient, and the swallow meant a post could be
    # published, committed and durable while pointing at media a concurrent
    # sweep had deleted.
    #
    # The trade is not close. An externalised object nobody ends up
    # referencing is collected safely by the next sweep; a published post with
    # missing media is permanent, user-visible damage that no later job
    # repairs. 503 rather than 400 because nothing is wrong with the payload —
    # the same request is expected to succeed on retry.
    if media_keys:
        try:
            claim_media(session().get_bind(), media_keys, MEDIA_CLAIM_TTL)
        except Exception as exc:
            raise SkriblUnavailable(
                "Media could not be reserved for this post; please retry."
            ) from exc

    # MINTED ONLY FOR A POST NOBODY OWNS. An owned post is authorised by its
    # owner; issuing a capability alongside that would be a second credential
    # to leak for no gain. 32 urlsafe bytes is ~256 bits — this is the whole
    # authorisation for a destructive operation, so it is sized like a secret
    # rather than like the 8-byte public id, which only has to be unguessable
    # enough not to be enumerated.
    delete_token = None
    delete_token_hash = None
    if author_id is None:
        delete_token = secrets.token_urlsafe(32)
        delete_token_hash = hash_delete_token(delete_token)

    for _attempt in range(5):
        candidate = secrets.token_urlsafe(8)
        try:
            # A SAVEPOINT per attempt, not a commit: the transaction belongs to
            # the HOST (docs/INTEGRATION.md). A public_id collision surfaces at
            # flush — the UNIQUE violation does not wait for commit — and
            # rolling back to the savepoint discards only this attempt's rows,
            # never whatever the host has pending on the same session.
            with session().begin_nested():
                post = SkriblPost(
                    public_id=candidate,
                    # ANONYMOUS (None) when the caller has no author — not 1,
                    # which would have made every visitor the owner of user 1's
                    # private posts.
                    user_id=normalise_user_id(author_id),
                    title=title,
                    caption=caption,
                    payload_json=stored_payload,
                    has_audio=has_audio,
                    visibility=visibility,
                    delete_token_hash=delete_token_hash,
                )
                session().add(post)
                # Flush to get the post id, then record one association row per
                # stored object — under the SAME savepoint, so a failed attempt
                # leaves neither behind. An orphan association would authorise
                # an object on behalf of a post that does not exist.
                session().flush()
                for _key in media_keys:
                    session().add(SkriblPostMedia(post_id=post.id,
                                                  media_key=_key))
                # The pending-media claim has done its job the moment the
                # association is in this transaction: from here the association
                # is what protects the object, so drop the claim IN THE SAME
                # SAVEPOINT. On commit the claim is gone and does not linger to
                # protect the object after the post is later deleted; on
                # rollback the delete reverts with everything else and the claim
                # survives as the crashed-poster backstop until its TTL. (v266.)
                # Gate on the table existing: where the v203 migration has NOT
                # been applied skribl_pending_media is absent, no claim was ever
                # written, and there is nothing to clear — but the DELETE runs
                # on the HOST session, so on PostgreSQL a missing-table error
                # here aborts the whole transaction.
                if media_keys and pending_media_ready(session().get_bind()):
                    session().query(SkriblPendingMedia).filter(
                        SkriblPendingMedia.media_key.in_(media_keys)
                    ).delete(synchronize_session=False)
                if idem_hash is not None:
                    # Same savepoint, same (host-owned) transaction as the post:
                    # durable together or not at all, which is the property a
                    # retry needs.
                    session().add(SkriblIdempotency(
                        key_hash=idem_hash, post_id=post.id,
                        request_fingerprint=idem_fp))
                session().flush()
        except IntegrityError as ie:
            # RETRY BOUNDARY. Retrying is only correct for the ONE violation a
            # fresh public_id can cure. This handler used to retry on ANY
            # IntegrityError — which is how the media-key dedup bug burned five
            # attempts on a constraint no new id could satisfy and surfaced as
            # "Could not allocate a unique id": five wasted inserts and a
            # diagnosis pointing at the wrong table.
            diag = str(getattr(ie, "orig", ie))
            if idem_hash is not None and "key_hash" in diag:
                # The idempotency index refused the KEY: a concurrent duplicate
                # won. The CALLER resolves to the winner, because resolving
                # means building a response.
                raise SkriblIdempotencyRace()
            if "public_id" not in diag:
                # Some other constraint. A new candidate cannot fix it; let the
                # caller's generic handler report THIS error.
                raise
            continue
        return CreatedPost(candidate, post, media_keys, delete_token)

    raise SkriblUnavailable()
