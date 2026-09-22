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

THE BACKFILL RUNS IN SQL, AND THE FIRST VERSION OF IT TOOK THE SITE DOWN.

It read every payload into Python, 200 rows at a time, to compute two small
values from them. `payload_json` is the multi-megabyte column this entire
design exists to avoid loading -- the listing defers it for exactly that
reason, and the paragraph above says so four lines up. On the demo's real data
that is hundreds of megabytes in one chunk:

    Running upgrade d8e1f4a2b7c3 -> a2f6c8b30e14, v307: ...
    ==> Out of memory (used over 512Mi)

The Procfile is `alembic upgrade head && gunicorn app:app`, so the deploy died
before the server started and the host kept serving the previous build. Two
merged releases sat invisible for hours.

So the work happens where the data already is. Both engines can read JSON
without handing it over, they just spell it differently, and BOTH ARE TESTED:
verify_migrations drives this on SQLite and verify_postgres runs the whole
chain against a real PostgreSQL in CI. That is what makes a dialect branch
safe here -- the objection to writing one was that a migration correct on one
engine is wrong, and the answer is to exercise both rather than to avoid the
branch and load the column instead.

The Python loop survives as the fallback for any other engine, chunked small
enough that it cannot repeat the failure above.

Scoped to SkriblBase.metadata like every other revision here -- it never
touches a host's tables.
"""
from alembic import op
import sqlalchemy as sa

revision = "a2f6c8b30e14"
down_revision = "d8e1f4a2b7c3"
branch_labels = None
depends_on = None

# Small on purpose: this path only runs on an engine neither branch below
# knows, and 200 of these is what ran a 512 MB box out of memory.
CHUNK = 10


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
    dialect = bind.dialect.name

    # EVERY BRANCH ENCODES THE SAME THREE RULES as _kind()/_pages() above, which
    # are themselves a copy of the test the players use: an explicit
    # playbackMode wins; otherwise more than one frame means flip; otherwise
    # pad. A one-page Flip document is a replay, and every player already says
    # so. verify_migrations asserts the SQL agrees with the Python on every
    # shape, which is the only thing that keeps four spellings honest.
    if dialect == "postgresql":
        bind.execute(sa.text("""
            UPDATE skribl_posts SET
              pages = CASE WHEN json_typeof(payload_json->'frames') = 'array'
                           THEN GREATEST(json_array_length(payload_json->'frames'), 1)
                           ELSE 1 END,
              kind = CASE
                       WHEN payload_json->>'playbackMode' = 'flip' THEN 'flip'
                       WHEN payload_json->>'playbackMode' IS NOT NULL THEN 'pad'
                       WHEN json_typeof(payload_json->'frames') = 'array'
                            AND json_array_length(payload_json->'frames') > 1 THEN 'flip'
                       ELSE 'pad' END
            WHERE kind IS NULL AND json_typeof(payload_json) = 'object'
        """))
    elif dialect == "sqlite":
        bind.execute(sa.text("""
            UPDATE skribl_posts SET
              pages = CASE WHEN json_type(payload_json, '$.frames') = 'array'
                           THEN MAX(json_array_length(payload_json, '$.frames'), 1)
                           ELSE 1 END,
              kind = CASE
                       WHEN json_extract(payload_json, '$.playbackMode') = 'flip' THEN 'flip'
                       WHEN json_extract(payload_json, '$.playbackMode') IS NOT NULL THEN 'pad'
                       WHEN json_type(payload_json, '$.frames') = 'array'
                            AND json_array_length(payload_json, '$.frames') > 1 THEN 'flip'
                       ELSE 'pad' END
            WHERE kind IS NULL AND json_valid(payload_json)
              AND json_type(payload_json) = 'object'
        """))
    else:
        # The fallback, for an engine neither branch knows. This is the shape
        # that ran a box out of memory, so it is chunked to CHUNK and nothing
        # else uses it.
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

    # ANYTHING THE JSON PATH COULD NOT CLASSIFY -- a payload that is not an
    # object, or is not valid JSON at all. _kind() answers 'pad' for exactly
    # those, so this is the same rule and not a second one. Runs on every
    # engine, and on a healthy table touches nothing.
    bind.execute(sa.text(
        "UPDATE skribl_posts SET kind = 'pad', pages = 1 WHERE kind IS NULL"))


def downgrade():
    op.drop_column("skribl_posts", "pages")
    op.drop_column("skribl_posts", "kind")
