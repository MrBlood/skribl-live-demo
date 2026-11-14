"""Drafts saved to the author's account (v316).

The owner's words: "a way to save skribl drafts (not on my machine as a file),
so I could just click the pen to add a skribl to the post, load the saved
skribl, then add it to post." A draft is the editor's own draft serialisation
(the object a .skribl backup holds) stored against a signed-in author.

WHAT A DRAFT IS NOT. It is not a post: no share link, no player, no listing, no
visibility. Nobody but its author can list, read, overwrite or delete it, and
every refusal of somebody else's draft is the same NotFound a missing one gets,
so the routes cannot leak which ids exist.

THE SAME BOUNDS A POST HAS. A draft passes the three payload checks a post
passes (structure, media, everything else), because a draft is a post that has
not happened yet and the column it lands in is the same kind of column. On top
of that, SKRIBL_MAX_DRAFTS per author (default 25), because drafts carry their
photo and music inline and would otherwise grow without anyone noticing.

NO COMMIT HERE, as everywhere in this package: the host owns the transaction
(docs/INTEGRATION.md, "Transaction ownership").
"""
import base64
import binascii
import hashlib
import json
import re
import secrets
from datetime import datetime, timezone

import sqlalchemy as sa

from .core import MAX_TITLE_CHARS, _env_int
from .models import SkriblDraft, normalise_user_id, session
from .validation import (_validate_payload_complexity, _validate_payload_extra,
                         media_refusal)

DRAFT_KINDS = ("pad", "flip")
# A list thumbnail, not a picture: a JPEG data URL a few kilobytes long. The
# cap refuses anything that is clearly not that.
MAX_THUMBNAIL_CHARS = 200_000


def max_drafts():
    return _env_int("SKRIBL_MAX_DRAFTS", 25, minimum=1)


def max_draft_bytes():
    """One author's drafts together (v317, security review). The count cap
    alone let 25 drafts of the full payload size sit in the database -- about
    625 MB for one account. 200 MB is ten drafts at the post-size ceiling and
    hundreds of ordinary ones."""
    return _env_int("SKRIBL_MAX_DRAFT_BYTES", 200 * 1024 * 1024, minimum=64 * 1024)


# A thumbnail is shown in an <img>, so an SVG could not run there -- but it is
# stored for the author and could be anything that starts "data:image/". Only
# the three raster types the editors make, their bytes checked, as posts do.
_THUMB = re.compile(r"^data:image/(jpeg|png|webp);base64,([A-Za-z0-9+/]+={0,2})$")
_THUMB_MAGIC = {"jpeg": (b"\xff\xd8\xff",), "png": (b"\x89PNG\r\n\x1a\n",), "webp": (b"RIFF",)}
_PNG_END = b"\x00\x00\x00\x00IEND\xaeB`\x82"


def _thumbnail_ok(thumbnail):
    """WHOLE, NOT ONLY ITS FIRST BYTES (the PRE-331 review's 11): the check
    decoded the first 48 bytes, so a PNG cut off after its signature (26
    bytes, the reviewer's) was stored. A thumbnail is made by an editor's
    canvas and is always whole, so it is decoded whole (it is at most
    MAX_THUMBNAIL_CHARS) and must end as its kind ends: a PNG its IEND chunk
    after an IHDR first, a JPEG its end-of-image marker, a WebP the length
    its RIFF header states. A post's image is held to less on purpose
    (validation.py: an unreadable header is accepted there); a draft's
    thumbnail is only ever ours."""
    m = _THUMB.match(thumbnail)
    if not m:
        return False
    try:
        raw = base64.b64decode(m.group(2), validate=True)
    except (binascii.Error, ValueError):
        return False
    kind = m.group(1)
    if not raw.startswith(_THUMB_MAGIC[kind]):
        return False
    if kind == "png":
        return raw[12:16] == b"IHDR" and raw.endswith(_PNG_END)
    if kind == "jpeg":
        return raw.endswith(b"\xff\xd9")
    return raw[8:12] == b"WEBP" and int.from_bytes(raw[4:8], "little") + 8 == len(raw)


def _one_save_at_a_time(owner):
    """ONE SAVE AT A TIME PER AUTHOR (the PRE-331 review's 2). A save reads
    the author's draft count and bytes, then writes, and nothing held the
    two together: on PostgreSQL saves at once could each see room for one
    more and all write. verify_postgres measured it: twelve 40 KB saves at
    once under a budget one fits stored two to four. A transaction-scoped
    advisory lock keyed on the author, as ratelimit takes on a poster, makes
    each save's reads and write one step; it is held on the host's session
    until the request commits, so the next save counts this one. Taken after
    the drawing is validated, so the slow part does not queue. On SQLite the
    file's one writer already serialises the writes."""
    s = session()
    if s.get_bind().dialect.name != "postgresql":
        return
    n = int.from_bytes(hashlib.sha256(("skribl-drafts:" + str(owner)).encode()).digest()[:8], "big", signed=True)
    s.execute(sa.text("SELECT pg_advisory_xact_lock(:n)"), {"n": n})


class DraftRejected(Exception):
    def __init__(self, message, status=400, detail=None):
        super().__init__(message)
        self.message = message
        self.status = status
        self.detail = detail   # as SkriblRejected's: the field's version


class DraftConflict(DraftRejected):
    """A save made from an older copy than the one stored (the v321 audit's
    SK-AUD-004): the same draft open on two devices, and the second save
    would have replaced the first without a word. `current` is the stored
    draft's summary, so the client can say what happened."""
    def __init__(self, current):
        super().__init__("This draft was changed somewhere else since you opened it.", status=409)
        self.current = current


class DraftBusy(DraftRejected):
    """Another write held the database while this save was being made (SQLite's
    one writer at a time: the v328 audit's AUD-002). Nothing was saved and
    nothing was lost; saving again a moment later goes through, or meets a
    real conflict and is answered as one."""
    def __init__(self):
        super().__init__("Another save is being made right now. Try again in a moment.", status=409)


class DraftNotFound(Exception):
    message = "Draft not found."


def _owner(author_id):
    if author_id is None:
        raise DraftRejected("Sign in to save drafts to your account.", status=401)
    return normalise_user_id(author_id)


def _validate(payload, kind, title, thumbnail):
    if not isinstance(payload, dict):
        raise DraftRejected("The draft must be a JSON object.")
    if kind not in DRAFT_KINDS:
        raise DraftRejected("Unknown draft kind.")
    if title is not None and not isinstance(title, str):
        raise DraftRejected("The title must be text.")
    title = (title or "").strip() or "Untitled Skribl"
    if len(title) > MAX_TITLE_CHARS:
        raise DraftRejected(f"That title is longer than {MAX_TITLE_CHARS} characters.")
    if thumbnail is not None:
        if (not isinstance(thumbnail, str) or len(thumbnail) > MAX_THUMBNAIL_CHARS
                or not _thumbnail_ok(thumbnail)):
            raise DraftRejected("The draft's picture could not be used.")
    error = _validate_payload_complexity(payload)
    if error:
        raise DraftRejected(error)
    media = media_refusal(payload, verb="save")
    if media:
        raise DraftRejected(media[0], detail=media[1])
    error = _validate_payload_extra(payload)
    if error:
        raise DraftRejected(error)
    return title


def _summary(d):
    return {"id": d.public_id, "kind": d.kind, "title": d.title,
            "thumbnail": d.thumbnail, "sizeBytes": d.size_bytes,
            "createdAt": d.created_at.isoformat() if d.created_at else None,
            "updatedAt": d.updated_at.isoformat() if d.updated_at else None}


def list_drafts(author_id):
    """The author's drafts, newest first, WITHOUT payloads.

    A HOST'S SEAM TOO (skribl.__all__; Nov 14, for the Skribl site's profile,
    its Drafts tab): a page of the host's that is the person's own lists
    their drafts with this, by the id its current_user_id hands Skribl for
    them, and links each to the editor that made it with ?draft=<id> (the
    editors' own hand-off, which asks before replacing work on the canvas).
    Each is {id, kind ("pad" or "flip"), title, thumbnail (the editor's own
    small picture, a data: URL, or None), sizeBytes, createdAt, updatedAt},
    newest saved first. Reads only, on the host's session: it flushes and
    commits nothing. Nobody (None) is refused (DraftRejected, 401), as the
    route refuses them: a page of drafts is somebody's own."""
    owner = _owner(author_id)
    # The list carries no payloads, so none is read: a drafts sheet opened at
    # the cap pulled every full drawing over the database connection to discard
    # it (v317, security review).
    rows = (session().query(SkriblDraft).options(sa.orm.defer(SkriblDraft.payload_json))
            .filter(SkriblDraft.user_id == owner)
            .order_by(SkriblDraft.updated_at.desc(), SkriblDraft.id.desc()).all())
    return [_summary(d) for d in rows]


def _find(owner, public_id):
    if not isinstance(public_id, str) or not public_id or len(public_id) > 32:
        raise DraftNotFound()
    d = session().query(SkriblDraft).filter(SkriblDraft.public_id == public_id).first()
    if d is None or d.user_id != owner:
        raise DraftNotFound()
    return d


def get_draft(author_id, public_id):
    d = _find(_owner(author_id), public_id)
    out = _summary(d)
    out["payload"] = d.payload_json
    return out


def _instant(v):
    """A timestamp as one instant, whatever its spelling. SQLite hands back the
    naive UTC it stored and a fresh row carries the aware value (PF-006), so a
    draft's own updatedAt read twice can differ as TEXT while naming the same
    moment; compared as text, a device conflicted with its own last save."""
    if isinstance(v, str):
        try:
            v = datetime.fromisoformat(v.replace("Z", "+00:00"))
        except ValueError:
            return None
    if v is None:
        return None
    return v if v.tzinfo else v.replace(tzinfo=timezone.utc)


def save_draft(author_id, payload, *, kind, title=None, thumbnail=None, public_id=None,
               base_updated_at=None):
    """Create a draft, or overwrite the author's own when `public_id` is given.

    `base_updated_at` is the updatedAt of the copy the client opened. Given,
    the overwrite happens only if the stored draft is still that copy, and
    raises DraftConflict otherwise. Two saves arriving together cannot both
    pass it: on PostgreSQL the row is locked for the comparison, and on SQLite
    the file's one writer lets one write and the other is DraftBusy (below).
    Absent (an older client, a host's own code), the overwrite is
    unconditional, as it always was."""
    owner = _owner(author_id)
    title = _validate(payload, kind, title, thumbnail)
    _one_save_at_a_time(owner)
    if public_id is not None and base_updated_at is not None:
        if not isinstance(base_updated_at, str):
            raise DraftRejected("'baseUpdatedAt' must be the draft's updatedAt.")
        locked = (session().query(SkriblDraft).filter(SkriblDraft.public_id == public_id)
                  .with_for_update().populate_existing().first())
        if locked is None or locked.user_id != owner:
            raise DraftNotFound()
        if _instant(locked.updated_at) != _instant(base_updated_at):
            raise DraftConflict(_summary(locked))
    # The thumbnail is stored beside the payload, so it counts too (the
    # PRE-331 review's 10: up to MAX_THUMBNAIL_CHARS a draft, outside the
    # quota). A draft saved before this keeps its old size until saved again.
    size = len(json.dumps(payload, separators=(",", ":"))) + len(thumbnail or "")
    now = datetime.now(timezone.utc)
    s = session()
    held = (s.query(sa.func.coalesce(sa.func.sum(SkriblDraft.size_bytes), 0))
            .filter(SkriblDraft.user_id == owner)
            .filter(SkriblDraft.public_id != (public_id or "")).scalar())
    if held + size > max_draft_bytes():
        raise DraftRejected(
            "Your saved drafts are using all the space they have. Delete one to save another.",
            status=409)
    if public_id is not None:
        d = _find(owner, public_id)
        # A SAVE THAT MEETS ANOTHER WRITE IS TOLD SO, NEVER A 500 (the v328
        # audit's AUD-002). On SQLite every request is a real transaction
        # (models.py's BEGIN recipe), so its reads hold the file's read lock
        # until it ends; two saves that have both read and then both write
        # deadlock, and SQLite fails one of them, at once or after its busy
        # timeout. The row lock above is PostgreSQL's alone. The lock is the whole file's,
        # so what this save met may be any write, not another save of this
        # draft: it is answered as busy, not as a conflict, and the editor says
        # so and keeps the drawing. A Save after it meets the stored draft as
        # it then is, and a real conflict is answered as one.
        # One UPDATE statement, not the ORM's flush: a flush that fails marks
        # the host's session for rollback, and the host's commit after this
        # answer would then be the 500 instead.
        try:
            s.query(SkriblDraft).filter(SkriblDraft.id == d.id).update(
                {SkriblDraft.kind: kind, SkriblDraft.title: title,
                 SkriblDraft.payload_json: payload, SkriblDraft.thumbnail: thumbnail,
                 SkriblDraft.size_bytes: size, SkriblDraft.updated_at: now},
                synchronize_session="evaluate")
        except sa.exc.OperationalError as exc:
            if "locked" not in str(exc.orig).lower():
                raise
            raise DraftBusy()
        return _summary(d)
    count = s.query(SkriblDraft).filter(SkriblDraft.user_id == owner).count()
    if count >= max_drafts():
        raise DraftRejected(
            f"You have {count} saved drafts, which is the limit. Delete one to save another.",
            status=409)
    d = SkriblDraft(public_id=secrets.token_urlsafe(12), user_id=owner, kind=kind,
                    title=title, payload_json=payload, thumbnail=thumbnail,
                    size_bytes=size, created_at=now, updated_at=now)
    s.add(d)
    s.flush()
    return _summary(d)


def delete_draft(author_id, public_id):
    d = _find(_owner(author_id), public_id)
    session().delete(d)
    session().flush()
