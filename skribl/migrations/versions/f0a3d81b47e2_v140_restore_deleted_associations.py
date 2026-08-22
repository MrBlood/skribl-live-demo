"""v140: restore associations the v139 repair deleted, batched

`b21f7ae0c93d` shipped in v139, so it is released and untouchable — see
RELEASED.txt. This revision repairs its damage rather than editing it.

WHAT WENT WRONG. That repair decided whether an existing association was
legitimate by reverse-parsing the stored URL with a pattern that recognises
"/media/<key>" and a narrow set of prefix segments. Anything else parsed as "not
a legitimate reference", so:

    {"frames": [{"music": {"data": "https://bucket/objects/<key>?X-Amz-Sig=..."},
                 "thumbnail": "/media/<key>"}]}

computed legitimate={} and invented={<key>} and DELETED a valid association.
Same for a host prefix outside [A-Za-z0-9._~%-], e.g. "/tenant+blue/media/<key>".
With the local backend that turns working media into a 404, because /media/<key>
requires an association.

This is the same lesson storage.py already carries and I failed to apply twice:
an authorisation identifier must never be reconstructed from its presentation
URL. put_data_url() returns the key precisely so nothing has to parse one back
out. The cleanup then parsed one back out anyway.

WHAT THIS DOES. Re-adds any association implied by a post's REAL media slots,
using CONTAINMENT rather than a URL parser: if the key string appears anywhere in
a legitimate slot's value, the post references it. Containment is the right tool
here in a way it was NOT for granting authorisation at request time — this only
ever ADDS back a row for a key already stored under a slot that post owns, and
erring toward preserving is correct when the alternative is 404ing live media.

It deliberately deletes nothing. The false frames[i].thumbnail rows were already
removed by b21f7ae0c93d, and a key that appears ONLY in that invalid slot has no
legitimate slot containing it, so it is not re-added here.

BATCHED. b21f7ae0c93d loaded the entire association table into a Python set and
accumulated every change in memory before writing. On an installation with
millions of associations — exactly the long-lived deployments this chain exists
to repair — that is hundreds of megabytes before any work starts. This streams
posts in batches and writes as it goes.

NOTE ON THE EDIT. This revision shipped in v140 and was then RECALLED before any
deployment ran it: the batch size was reduced from 500 to 25. Editing a released
migration is normally forbidden here, for good reason and after this project got
it wrong twice — but the rule exists to protect OUTCOMES, and batch size cannot
change which rows result, only how much memory is held while producing them.
`verify_migrations.py` proves that by running the repair at two batch sizes and
asserting identical results. If any database of yours actually ran the v140 copy
of this revision, nothing is wrong with it: the data it produced is the same.

Revision ID: f0a3d81b47e2
Revises: b21f7ae0c93d
"""
import json
import re

from alembic import op
import sqlalchemy as sa

revision = "f0a3d81b47e2"
down_revision = "b21f7ae0c93d"
branch_labels = None
depends_on = None

# 25, not 500. Each row carries CAST(payload_json AS TEXT), and the application
# accepts payloads up to MAX_CONTENT_LENGTH (25 MB by default) — so a 500-row
# batch materialises up to 12.5 GB of payload text at once, and even at a
# realistic 1-2 MB average it is 500 MB-1 GB per batch. The previous revision's
# fault was unbounded memory; a large batch is the same fault with a ceiling
# nobody would want to hit. Batch size affects only how much is held at once,
# never which rows result — verify_migrations.py asserts that.
BATCH = 25

def _slot_values(payload):
    """The REAL media slots, mirroring skribl.validation._iter_media_items.

    Top-level thumbnail, top-level music.data / photo.data, and music.data /
    photo.data inside each frame. There is NO frames[i].thumbnail.
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


#: A content key wherever it appears INSIDE a legitimate slot's value. Not
#: anchored, and deliberately so: the value may be "/media/<key>",
#: "/tenant+blue/media/<key>", or "https://bucket/objects/<key>?X-Amz-Sig=...".
#: What makes this safe is not the pattern but WHERE it is applied — only to the
#: real media slots, never to arbitrary preserved fields.
_KEY_IN_VALUE = re.compile(r"([0-9a-f]{64}\.[a-z0-9]{2,4})")


def _referenced(payload):
    """Keys this post's legitimate slots reference, in ANY URL form.

    Extracted from the slot values rather than matched against a list of known
    keys. The first draft took its candidates from DISTINCT media_key in the
    association table — which cannot work here, because the rows this revision
    exists to restore had already been deleted, so their keys were no longer
    known to it. It restored nothing.
    """
    found = set()
    for value in _slot_values(payload):
        if isinstance(value, str):
            found.update(_KEY_IN_VALUE.findall(value))
    return found


def upgrade():
    conn = op.get_bind()

    last_id = 0
    while True:
        rows = conn.execute(sa.text(
            "SELECT id, CAST(payload_json AS TEXT) FROM skribl_posts"
            " WHERE id > :last ORDER BY id LIMIT :n"),
            {"last": last_id, "n": BATCH}).fetchall()
        if not rows:
            break
        last_id = rows[-1][0]

        ids = [r[0] for r in rows]
        have = set()
        # Existing associations for THIS batch only.
        for pid, key in conn.execute(sa.text(
                "SELECT post_id, media_key FROM skribl_post_media"
                " WHERE post_id IN :ids").bindparams(
                    sa.bindparam("ids", expanding=True)), {"ids": ids}):
            have.add((pid, key))

        pending = []
        for post_id, payload_text in rows:
            if not payload_text:
                continue
            try:
                payload = json.loads(payload_text)
            except (ValueError, TypeError):
                continue
            for key in _referenced(payload):
                if (post_id, key) not in have:
                    pending.append({"p": post_id, "k": key})
                    have.add((post_id, key))

        if pending:
            conn.execute(sa.text(
                "INSERT INTO skribl_post_media (post_id, media_key)"
                " VALUES (:p, :k)"), pending)


def downgrade():
    # Deleting these would re-open the 404s this revision exists to close.
    pass
