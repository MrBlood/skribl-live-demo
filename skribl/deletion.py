"""Taking a Skribl back: deletion and revocation, for both callers.

    from skribl import delete_post, set_post_visibility, SkriblNotFound

    try:
        delete_post(public_id, author_id=current_user.id)
    except SkriblNotFound:
        abort(404)
    else:
        db.session.delete(my_feed_row)
        db.session.commit()

WHY THIS MODULE EXISTS. An external review of v277 put it plainly: the API
"supports creation and reading but no obvious delete, archive, revoke, or
visibility-update operation for an already published Skribl", and for a product
whose whole surface is sharing, that is the gap that matters. People share the
wrong drawing, publish something private, pick the wrong audience, delete the
host post the Skribl was attached to, or are asked to take something down.

THE FOUNDATION WAS ALREADY HERE AND WAS ALREADY TESTED. `SkriblPostMedia`
carries `ON DELETE CASCADE`, `storage.sweep_orphans()` collects the bytes, and
`verify_deletion_foundation.py` runs the whole sequence on PostgreSQL — post a
Skribl with a photo, delete the row, prove `/media/<key>` then REFUSES, prove
the sweeper names and removes the object. Its docstring says the host-controls
proposal "puts delete_skribl() first on the build order" and that the claim
"has never been executed". This module is that function; nothing underneath it
changed.

WHAT THIS IS NOT. It is not a second deletion path. There was no first one, and
there is exactly one here — the HTTP route, when it exists at all, calls these
functions and adds nothing but status codes. That direction is the same one
`creation.py` records, and for the same reason: two functions that both "delete
a post and clean up its associations" is how one of them quietly stops running.

DELETE AND REVOKE ARE DIFFERENT PRODUCTS, and both are offered because the
visibility column already says they are. `delete_post` removes the row: the
share URL 404s, the associations cascade, the bytes become sweepable.
`set_post_visibility` changes who may read it: an unlisted post revoked to
private is still the author's, still in their library, and no longer reachable
by the link they sent. Collapsing the two would force "I regret sharing this"
to mean "destroy it", which is not the same wish.

AUTHORISATION HAPPENS BEFORE ANY DESTRUCTIVE WORK, and it does not tell you
what it refused. A missing post and a post belonging to somebody else raise the
SAME `SkriblNotFound`, so the API cannot be walked to learn which public ids
exist or who owns them. That is why there is no `SkriblForbidden` here: a
distinct exception would be the disclosure, however carefully the route
translated it.

  author_id=None means "the caller has not authenticated anybody" and is
  REFUSED for a post that has an author, rather than treated as a superuser.
  A management command that genuinely must delete anything passes
  `require_author=False`, in code, once — the same shape as `csrf=False`.

  A post whose `user_id` IS NULL — the standalone app's own posts, which have
  no author because nothing signed in — can only be deleted with
  `require_author=False`. Anything else would let any authenticated user of a
  host delete every anonymous post in the table.

TRANSACTIONS ARE THE HOST'S, exactly as in `creation.py`. These functions
flush; they never commit and never roll back the outer transaction. The host's
own row and the Skribl go together or neither does.

THE BYTES ARE NOT DELETED HERE, deliberately. Media objects are content
addressed, so the photo in the post you are deleting may be the same object as
the photo in a post you are not; only a reference count taken across the whole
table can say, and that is `sweep_orphans()`'s job. It is also conservative by
design — `older_than_seconds`, plus the pending-claim protocol
`SkriblPendingMedia` documents — because deleting a live object is unrecoverable
and keeping a dead one costs storage. Deleting bytes inline here would throw all
of that away for the one caller least able to reason about it. What this DOES
guarantee is that the bytes stop being reachable: `/media/<key>` authorises
through the association rows, which are gone with the post.
"""
from .models import (SkriblPost, SkriblPostMedia, session,
                     visibility_values)


class SkriblNotFound(LookupError):
    """No post the caller may act on.

    Raised BOTH for a post that does not exist and for one the caller does not
    own. The conflation is the point — see the module header. Routes should
    answer 404.
    """

    status = 404

    def __init__(self, message="No such Skribl."):
        super().__init__(message)
        self.message = message


class SkriblRefused(ValueError):
    """The operation is not one this post can be asked to perform.

    A visibility value outside the accepted set, in practice. Distinct from
    SkriblNotFound because it says nothing about whether a post exists: the
    caller's own argument was wrong, and it is wrong before any lookup.
    """

    status = 400

    def __init__(self, message):
        super().__init__(message)
        self.message = message


def _authorised_post(public_id, author_id, require_author):
    """The post, or SkriblNotFound. The ONLY lookup either operation uses.

    Written once because "find it" and "check you may have it" must not be two
    steps that a later edit can reorder or half-apply. Every caller below gets
    a post it is already allowed to act on, or an exception.
    """
    post = (session().query(SkriblPost)
            .filter(SkriblPost.public_id == public_id)
            .one_or_none())
    if post is None:
        raise SkriblNotFound()
    if not require_author:
        return post
    # NULL user_id is the standalone app's own posts. Nobody owns them, so
    # nobody may claim them by authenticating; require_author=False is the only
    # way through, and it is a decision written in the host's code.
    if post.user_id is None or author_id is None or post.user_id != author_id:
        raise SkriblNotFound()
    return post


def delete_post(public_id, *, author_id=None, require_author=True):
    """Delete a Skribl. Returns the deleted post's public_id.

    Flushes; does not commit. See the module header for the transaction
    contract, the authorisation rule, and why the media bytes are left to the
    sweeper.

    Raises SkriblNotFound if there is no such post OR the caller does not own
    it — the two are deliberately indistinguishable.
    """
    post = _authorised_post(public_id, author_id, require_author)

    s = session()
    # THE ASSOCIATIONS ARE DELETED EXPLICITLY, NOT LEFT TO THE CASCADE, and the
    # reason is narrower than "SQLite ignores foreign keys" — which it does by
    # default, but which `enable_sqlite_foreign_keys()` already fixes for any
    # app mounted through `init_skribl`. Under that path the declared
    # ON DELETE CASCADE fires and this statement is redundant.
    #
    # It is NOT redundant on the two paths that miss the pragma hook:
    #
    #   * a host that calls create_blueprint() and register_blueprint()
    #     directly — documented as equivalent to init_skribl(), and equivalent
    #     in everything except this, because the hook is installed by
    #     init_skribl and attaches to the engine it was handed;
    #   * a deployment that sets SKRIBL_SQLITE_FOREIGN_KEYS=0, which the hook
    #     honours by design.
    #
    # On either, relying on the cascade leaves the association rows behind. They
    # authorise nothing — /media/<key> joins to the post — but they make
    # `sweep_orphans` count the media as still referenced, so the bytes are
    # never collected: a takedown that leaves the image on disk forever. That is
    # the exact leak enable_sqlite_foreign_keys() was written for, reachable
    # again through a door it does not cover.
    #
    # One indexed statement makes the outcome identical on every backend and on
    # every mounting path, which is worth more than being clever about which
    # configurations need it. verify_deletion.py section 3 runs it with the
    # pragma explicitly OFF.
    (s.query(SkriblPostMedia)
     .filter(SkriblPostMedia.post_id == post.id)
     .delete(synchronize_session=False))
    s.delete(post)
    s.flush()
    return public_id


def set_post_visibility(public_id, visibility, *, author_id=None,
                        require_author=True):
    """Change who may read a Skribl. Returns the post's new visibility.

    `set_post_visibility(pid, "private", author_id=...)` is the REVOKE: the
    post survives, and the link the author already sent stops working for
    everyone but them. `visible_to()` is the single rule that enforces it, and
    it already guards the payload endpoint, the player page, the share card and
    the media route — so revocation takes effect everywhere at once rather than
    needing a new check per surface.

    Flushes; does not commit.
    """
    # Validated BEFORE the lookup, so a bad argument cannot be used to probe
    # which ids exist: it fails the same way whether or not the post is there.
    allowed = visibility_values()
    if visibility not in allowed:
        raise SkriblRefused(
            f"visibility must be one of {', '.join(sorted(allowed))}")

    post = _authorised_post(public_id, author_id, require_author)
    post.visibility = visibility
    session().flush()
    return visibility
