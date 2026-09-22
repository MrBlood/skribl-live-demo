"""v307: which editor made it, and how many pages.

WHY A COLUMN AND NOT A LOOK AT THE PAYLOAD. The listing endpoint defers
`payload_json` on purpose -- measured at 9.75 ms against 1.04 ms for a page of
fifty -- so a tile has no way to ask what it is showing. The gallery therefore
drew neither pen nor book and there was no way to tell a Flip from a replay
(owner). Denormalised at post time from the same payload `has_audio` comes
from, in the same tick, by `_payload_kind` / `_payload_pages` in validation.py.

NULLABLE, on purpose. A NOT NULL column with no server default fails exactly on
the databases that matter (the v132 lesson), and there is no honest default
here: 'pad' would be a guess printed as a fact on every row that predates the
column. So: nullable, backfilled below, and a null that survives renders as
NOTHING in every client -- the same rule the row's own has_audio follows.

THE BACKFILL READS EVERY PAYLOAD ONCE, and that is the cost of not shipping a
badge that works only for posts made after the upgrade. In Python rather than
in SQL, because the two engines spell JSON extraction differently
(`payload_json->>'playbackMode'` against `json_extract(...)`) and a migration
that is correct on one of them is a migration that is wrong. Chunked by id so
a large table is not held in memory at once; `payload_json` is the only heavy
column and only one chunk of it is live at a time.

If this ever gets slow enough to matter, the dialect-native expression is the
answer, guarded by `op.get_bind().dialect.name` with this loop as the fallback.
It is not written that way today because nothing has measured a need for it and
two code paths would both have to stay correct.

Scoped to SkriblBase.metadata like every other revision here -- it never
touches a host's tables.
"""
from alembic import op
import sqlalchemy as sa

revision = "a2f6c8b30e14"
down_revision = "d8e1f4a2b7c3"
branch_labels = None
depends_on = None

CHUNK = 200


def _pages(payload):
    if not isinstance(payload, dict):
        return 1
    frames = payload.get("frames")
    return max(1, len(frames)) if isinstance(frames, list) else 1


def _kind(payload):
    """A COPY of validation._payload_kind, and deliberately so.

    A migration describes the schema at the moment it ran. Importing the
    application's version would make this revision's behaviour change whenever
    that function is edited, so a tree three refactors from now would replay
    its own history differently. Alembic revisions are frozen; this is what
    frozen looks like.
    """
    if not isinstance(payload, dict):
        return "pad"
    mode = payload.get("playbackMode")
    if mode:
        return "flip" if mode == "flip" else "pad"
    return "flip" if _pages(payload) > 1 else "pad"


def upgrade():
    op.add_column("skribl_posts", sa.Column("kind", sa.String(length=8), nullable=True))
    op.add_column("skribl_posts", sa.Column("pages", sa.Integer(), nullable=True))

    bind = op.get_bind()
    posts = sa.table("skribl_posts",
                     sa.column("id", sa.Integer),
                     sa.column("payload_json", sa.JSON),
                     sa.column("kind", sa.String),
                     sa.column("pages", sa.Integer))
    last = 0
    while True:
        rows = bind.execute(
            sa.select(posts.c.id, posts.c.payload_json)
              .where(posts.c.id > last)
              .order_by(posts.c.id)
              .limit(CHUNK)
        ).fetchall()
        if not rows:
            break
        for row in rows:
            payload = row[1]
            bind.execute(
                sa.update(posts).where(posts.c.id == row[0])
                  .values(kind=_kind(payload), pages=_pages(payload))
            )
        last = rows[-1][0]


def downgrade():
    op.drop_column("skribl_posts", "pages")
    op.drop_column("skribl_posts", "kind")
