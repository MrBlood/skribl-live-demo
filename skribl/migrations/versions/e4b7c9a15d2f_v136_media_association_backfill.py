"""v136: backfill post-media associations for pre-v135 local media

A SEPARATE revision, deliberately. The backfill was originally added by editing
the already-released v135 revision (86171614cb85) in place. A database that had
actually run v135 is stamped at that revision, so `alembic upgrade head` sees
itself as current and never executes the added code — the fix would have run
only on databases that never had the problem, and silently skipped every
deployment that did. Never edit a distributed migration; add one.

WHAT IT DOES. SKRIBL_MEDIA_BACKEND=local has been supported since v132, so a
live database can hold posts whose payloads reference "/media/<key>" objects.
From v135 those objects are authorised through skribl_post_media, and an object
with no association rows is treated as orphaned and 404s. This adopts the
associations those payloads already imply.

WHAT IT DOES NOT DO. It does not scan the serialised JSON for anything shaped
like a media key. An earlier draft did, with

    re.compile(r"/media/([0-9a-f]{64}\\.[a-z0-9]{2,4})")

against CAST(payload_json AS TEXT), and that RECREATES THE EXACT FORGERY v135
was written to eliminate: the API deliberately preserves unknown fields, so a
legacy payload containing {"notes": "see /media/<someone-elses-key>.wav"} would
have been promoted into a genuine authorisation relationship. Substring matching
is not a reference. This walks the real media slots only — the same slots the
application's own media walker uses.

Revision ID: e4b7c9a15d2f
Revises: 86171614cb85
"""
import json
import re

from alembic import op
import sqlalchemy as sa

revision = "e4b7c9a15d2f"
down_revision = "86171614cb85"
branch_labels = None
depends_on = None

# A stored media URL, and nothing else. Anchored: the whole value must be the
# URL, so a key mentioned inside a sentence is not a reference.
_MEDIA_URL = re.compile(r"^(?:https?://[^\s]+)?/media/([0-9a-f]{64}\.[a-z0-9]{2,4})$")


def _key_of(value):
    """-> media key if `value` IS a stored media URL, else None."""
    if not isinstance(value, str):
        return None
    m = _MEDIA_URL.match(value.strip())
    return m.group(1) if m else None


def _media_slots(payload):
    """Yield the values of the REAL media slots, mirroring the app's walker.

    Only these positions have ever held media:
        thumbnail
        music.data, photo.data                  (top level, legacy shape)
        frames[i].music.data, frames[i].photo.data
    Anything else in the payload is a field the API preserved on the author's
    behalf and carries no ownership meaning.
    """
    if not isinstance(payload, dict):
        return

    def slot(container, name):
        node = container.get(name)
        if isinstance(node, dict):
            yield node.get("data")

    yield payload.get("thumbnail")
    for name in ("music", "photo"):
        yield from slot(payload, name)

    frames = payload.get("frames")
    if isinstance(frames, list):
        for frame in frames:
            if not isinstance(frame, dict):
                continue
            yield frame.get("thumbnail")
            for name in ("music", "photo"):
                yield from slot(frame, name)


def upgrade():
    conn = op.get_bind()

    existing = set()
    for post_id, media_key in conn.execute(sa.text(
            "SELECT post_id, media_key FROM skribl_post_media")):
        existing.add((post_id, media_key))

    pairs = []
    seen = set()
    for post_id, payload_text in conn.execute(sa.text(
            "SELECT id, CAST(payload_json AS TEXT) FROM skribl_posts")):
        if not payload_text:
            continue
        try:
            payload = json.loads(payload_text)
        except (ValueError, TypeError):
            # An unparseable payload cannot be shown to reference anything.
            # Skipping is correct: the alternative is guessing.
            continue
        for value in _media_slots(payload):
            key = _key_of(value)
            if key and (post_id, key) not in seen and (post_id, key) not in existing:
                seen.add((post_id, key))
                pairs.append({"p": post_id, "k": key})

    if pairs:
        conn.execute(sa.text(
            "INSERT INTO skribl_post_media (post_id, media_key)"
            " VALUES (:p, :k)"), pairs)


def downgrade():
    # Intentionally not deleting rows. There is no way to tell an association
    # this migration created from one the application wrote afterwards, and
    # removing a real one would 404 live media.
    pass
