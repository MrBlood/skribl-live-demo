"""v138: prefix-aware media backfill, and repair of v137's false associations

A NEW revision, because e4b7c9a15d2f has been released. This is the second time
that lesson has had to be learned in this project: the v135 backfill was first
added by editing 86171614cb85 in place, and then the v137 corrections were added
by editing e4b7c9a15d2f in place. Both times the change was correct for a
database that had never run the revision, and a no-op for every database that
had — which is precisely the set that needed it. `alembic upgrade head` on a
v137 installation sees current == head and executes nothing.

NEVER edit a released migration. Add a revision. `verify_migrations.py` now
builds a database at the exact released v137 head and asserts that upgrading
runs something.

This revision does two things.

1. ADD the associations e4b7c9a15d2f missed. Its URL pattern required
   "/media/<key>" at the start of the path, so it did not recognise
   "/skribl/media/<key>" — and the local store builds URLs with
   url_for("skribl.media"), so every deployment mounted under a url_prefix
   stored exactly that form. Those installations upgraded and still had no
   association rows, leaving their own media 404ing.

2. REMOVE the associations e4b7c9a15d2f invented. Its slot walker included
   frames[i].thumbnail, which the application has never had — the runtime walker
   does not process it and the client writes the share thumbnail once, at the
   top level. Because POST deliberately preserves unknown fields, an attacker
   could persist {"frames": [{"thumbnail": "/media/<victim-key>"}]} in a public
   post, and that migration promoted the invented field into a real
   authorisation row. Correcting the code does not delete rows already written.

   The deletion is conservative: a (post_id, key) pair is removed ONLY when the
   key appears in that post's per-frame thumbnail slot AND appears in none of
   its legitimate slots. A post that genuinely uses an object keeps its row.

Revision ID: b21f7ae0c93d
Revises: e4b7c9a15d2f
"""
import json
import re

from alembic import op
import sqlalchemy as sa

revision = "b21f7ae0c93d"
down_revision = "e4b7c9a15d2f"
branch_labels = None
depends_on = None

# Anchored at both ends, key validated, and tolerant of any mount prefix in
# front of "/media/". Prose that merely mentions a key is still not a reference.
_MEDIA_URL = re.compile(
    r"^"
    r"(?:[a-z][a-z0-9+.-]*://[^/\s]+)?"      # optional scheme + host
    r"(?:/[A-Za-z0-9._~%-]+)*"                # optional mount prefix segments
    r"/media/([0-9a-f]{64}\.[a-z0-9]{2,4})"   # the object itself
    r"$")


def _key_of(value):
    if not isinstance(value, str):
        return None
    m = _MEDIA_URL.match(value.strip())
    return m.group(1) if m else None


def _slot_values(payload):
    """The REAL media slots, mirroring skribl.validation._iter_media_items.

    Top-level thumbnail, top-level music.data and photo.data, and music.data /
    photo.data inside each frame. There is no frames[i].thumbnail.
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
            if isinstance(frame, dict):
                for name in ("music", "photo"):
                    yield from slot(frame, name)


def _frame_thumbnail_values(payload):
    """The INVALID slot e4b7c9a15d2f walked, so its rows can be identified."""
    if not isinstance(payload, dict):
        return
    frames = payload.get("frames")
    if isinstance(frames, list):
        for frame in frames:
            if isinstance(frame, dict):
                yield frame.get("thumbnail")


def upgrade():
    conn = op.get_bind()

    existing = {(pid, key) for pid, key in conn.execute(sa.text(
        "SELECT post_id, media_key FROM skribl_post_media"))}

    to_add, to_remove = [], []
    for post_id, payload_text in conn.execute(sa.text(
            "SELECT id, CAST(payload_json AS TEXT) FROM skribl_posts")):
        if not payload_text:
            continue
        try:
            payload = json.loads(payload_text)
        except (ValueError, TypeError):
            continue

        legitimate = {k for k in (_key_of(v) for v in _slot_values(payload)) if k}
        invented = {k for k in (_key_of(v) for v in _frame_thumbnail_values(payload)) if k}

        for key in legitimate:
            if (post_id, key) not in existing:
                to_add.append({"p": post_id, "k": key})

        # Only rows attributable SOLELY to the invalid slot.
        for key in invented - legitimate:
            if (post_id, key) in existing:
                to_remove.append({"p": post_id, "k": key})

    if to_add:
        conn.execute(sa.text(
            "INSERT INTO skribl_post_media (post_id, media_key)"
            " VALUES (:p, :k)"), to_add)
    if to_remove:
        conn.execute(sa.text(
            "DELETE FROM skribl_post_media"
            " WHERE post_id = :p AND media_key = :k"), to_remove)


def downgrade():
    # Not reversible in a meaningful sense: re-adding the associations this
    # revision deleted would restore an authorisation hole, and deleting the
    # ones it added would 404 live media.
    pass
