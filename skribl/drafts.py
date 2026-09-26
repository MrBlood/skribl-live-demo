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
import json
import secrets
from datetime import datetime, timezone

from .core import MAX_TITLE_CHARS, _env_int
from .models import SkriblDraft, normalise_user_id, session
from .validation import (_validate_payload_complexity, _validate_payload_extra,
                         _validate_payload_media)

DRAFT_KINDS = ("pad", "flip")
# A list thumbnail, not a picture: a JPEG data URL a few kilobytes long. The
# cap refuses anything that is clearly not that.
MAX_THUMBNAIL_CHARS = 200_000


def max_drafts():
    return _env_int("SKRIBL_MAX_DRAFTS", 25, minimum=1)


class DraftRejected(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.message = message
        self.status = status


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
        if (not isinstance(thumbnail, str) or not thumbnail.startswith("data:image/")
                or len(thumbnail) > MAX_THUMBNAIL_CHARS):
            raise DraftRejected("The draft's picture could not be used.")
    for check in (_validate_payload_complexity, _validate_payload_media,
                  _validate_payload_extra):
        error = check(payload)
        if error:
            raise DraftRejected(error)
    return title


def _summary(d):
    return {"id": d.public_id, "kind": d.kind, "title": d.title,
            "thumbnail": d.thumbnail, "sizeBytes": d.size_bytes,
            "createdAt": d.created_at.isoformat() if d.created_at else None,
            "updatedAt": d.updated_at.isoformat() if d.updated_at else None}


def list_drafts(author_id):
    """The author's drafts, newest first, WITHOUT payloads."""
    owner = _owner(author_id)
    rows = (session().query(SkriblDraft).filter(SkriblDraft.user_id == owner)
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


def save_draft(author_id, payload, *, kind, title=None, thumbnail=None, public_id=None):
    """Create a draft, or overwrite the author's own when `public_id` is given."""
    owner = _owner(author_id)
    title = _validate(payload, kind, title, thumbnail)
    size = len(json.dumps(payload, separators=(",", ":")))
    now = datetime.now(timezone.utc)
    s = session()
    if public_id is not None:
        d = _find(owner, public_id)
        d.kind, d.title, d.payload_json = kind, title, payload
        d.thumbnail, d.size_bytes, d.updated_at = thumbnail, size, now
        s.flush()
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
