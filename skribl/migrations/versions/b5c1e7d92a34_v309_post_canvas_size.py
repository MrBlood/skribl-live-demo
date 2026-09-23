"""v309: how big the drawing is.

WHY A COLUMN AND NOT A LOOK AT THE PAYLOAD, for the third time on this row and
for the same measured reason as `kind`/`pages` before it: the listing endpoint
defers `payload_json` on purpose (9.75 ms against 1.04 ms for a page of fifty),
so a tile cannot ask what shape the drawing is.

WHAT IT BUYS. The idle tile shows the share CARD, and the card CONTAINS the
drawing: a 4:3 drawing inside a 1200x630 card leaves 110px of card ground and
the card's plate border on each visible side, so a gallery of tiles showed a
picture inside a frame inside a card (owner: "fix the share card bands too").
The client can crop the card back to just the drawing -- lib/sharecard.js
drawingRect() has been the arithmetic since the card was written -- given the
drawing's size, which is what these two columns carry.

NULLABLE, and the null is honest rather than lazy. `canvasSize` is OPTIONAL in
a payload and always has been: a Skribl authored before Pad had a size picker
simply has none, and lib/canvassizes.js supplies the default at play time. A
row this backfill cannot answer stays NULL, and a null renders as the BAND crop
the tile used before this column -- never as a guessed 4:3, which would frame
the picture wrongly instead of framing it widely. Same rule as `has_audio` and
`kind` on the same row.

THE BACKFILL RUNS IN SQL. The v307 revision beside this one records what
happened when its first version read every payload into Python to compute two
small numbers from it: `payload_json` is the multi-megabyte column the whole
design exists to avoid loading, and the deploy died with

    ==> Out of memory (used over 512Mi)

before gunicorn started. So the work happens where the data already is. Both
engines can read JSON without handing it over and BOTH ARE TESTED --
verify_migrations drives this on SQLite, verify_postgres runs the whole chain
against a real PostgreSQL in CI -- which is what makes a dialect branch safe
here rather than a correctness hazard.

The Python loop survives as the fallback for any other engine, chunked small
enough that it cannot repeat that failure.

BOTH EDGES OR NEITHER. A width without a height frames nothing and would make
a client invent the missing number; every branch below writes the pair or
writes neither, and the feed serialiser refuses a half-filled row on the way
out as well.

Scoped to SkriblBase.metadata like every other revision here -- it never
touches a host's tables.
"""
from alembic import op
import sqlalchemy as sa

revision = "b5c1e7d92a34"
down_revision = "a2f6c8b30e14"
branch_labels = None
depends_on = None

# Small on purpose: this path only runs on an engine neither branch below
# knows, and 200 of these is what ran a 512 MB box out of memory.
CHUNK = 10

# Matches MAX_CANVAS_EDGE at the time of this revision. FROZEN on purpose --
# an Alembic revision describes the schema at the moment it ran, so importing
# validation.MAX_CANVAS_EDGE would make this migration's behaviour change
# whenever that constant is edited, and a tree three releases from now would
# replay its own history differently.
MAX_EDGE = 4096


def _canvas(payload):
    """A COPY of validation._payload_canvas, frozen for the same reason."""
    if not isinstance(payload, dict):
        return (None, None)
    cs = payload.get("canvasSize")
    if not isinstance(cs, dict):
        return (None, None)
    w, h = cs.get("cssWidth"), cs.get("cssHeight")
    for v in (w, h):
        if isinstance(v, bool) or not isinstance(v, int) or v < 1 or v > MAX_EDGE:
            return (None, None)
    return (w, h)


def upgrade():
    op.add_column("skribl_posts", sa.Column("canvas_w", sa.Integer(), nullable=True))
    op.add_column("skribl_posts", sa.Column("canvas_h", sa.Integer(), nullable=True))

    bind = op.get_bind()
    dialect = bind.dialect.name

    # EVERY BRANCH ENCODES THE SAME RULE as _canvas() above: an object under
    # `canvasSize` holding two whole numbers in 1..MAX_EDGE, or nothing at all.
    # verify_migrations asserts the SQL agrees with the Python on every shape --
    # a missing key, a string, a float, a zero, an over-large edge, one edge
    # present and the other not -- which is the only thing that keeps three
    # spellings of one rule honest.
    if dialect == "postgresql":
        # NOTHING THAT CAN RAISE GOES IN THIS WHERE CLAUSE, and the first
        # version of this revision is why the deploy died rather than shipped.
        #
        # It read like a funnel: check the payload is an object, then that
        # `canvasSize` is an object, then that the two edges are numbers, THEN
        # cast them. PostgreSQL does not evaluate AND in the order it is
        # written -- the planner sorts quals by estimated cost -- so the casts
        # ran against values the guards above them had not yet rejected. On a
        # gallery holding one post whose cssWidth is an object, that is
        #
        #     invalid input syntax for type numeric: "{"a":1}"
        #
        # and `alembic upgrade head` gates gunicorn, so the deploy exited 1 and
        # Render kept serving the previous build. EXPLAIN says it plainly: the
        # regex was hoisted ABOVE every json_typeof guard.
        #
        # So this clause now contains only predicates that cannot raise on any
        # JSON value, in any order: `IS NULL`, `json_typeof` (total on valid
        # json), and a regex on `#>>` (which yields NULL rather than erroring
        # when the path does not resolve, including into a scalar or an array).
        #
        # THE CAST MOVED TO THE SET LIST, which is evaluated only for rows the
        # WHERE has selected -- that order IS guaranteed. `^[0-9]{1,4}$` is what
        # makes it total: digits only, so no float, no exponent, no string; at
        # most four of them, so the value cannot overflow an int. MAX_EDGE is
        # 4096 and frozen, so four digits always covers every legal size; the
        # statement after this one clears anything outside the range, on plain
        # integer comparisons that cannot raise either.
        bind.execute(sa.text("""
            UPDATE skribl_posts SET
              canvas_w = (payload_json #>> '{canvasSize,cssWidth}')::int,
              canvas_h = (payload_json #>> '{canvasSize,cssHeight}')::int
            WHERE canvas_w IS NULL
              AND json_typeof(payload_json) = 'object'
              AND json_typeof(payload_json->'canvasSize') = 'object'
              AND json_typeof(payload_json #> '{canvasSize,cssWidth}') = 'number'
              AND json_typeof(payload_json #> '{canvasSize,cssHeight}') = 'number'
              AND (payload_json #>> '{canvasSize,cssWidth}') ~ '^[0-9]{1,4}$'
              AND (payload_json #>> '{canvasSize,cssHeight}') ~ '^[0-9]{1,4}$'
        """))
        # The range, on the columns rather than on the JSON: 0 and 9999 pass
        # the regex and are not legal sizes. Integer comparisons, so this one
        # is order-proof by construction.
        bind.execute(sa.text(
            "UPDATE skribl_posts SET canvas_w = NULL, canvas_h = NULL "
            "WHERE canvas_w < 1 OR canvas_h < 1 "
            "OR canvas_w > :edge OR canvas_h > :edge"), {"edge": MAX_EDGE})
    elif dialect == "sqlite":
        # json_type(...) = 'integer' is the whole-number test: SQLite reports
        # 'real' for 612.5 and 'text' for "612", so a float or a numeric string
        # falls out here exactly as it does in Python.
        bind.execute(sa.text("""
            UPDATE skribl_posts SET
              canvas_w = json_extract(payload_json, '$.canvasSize.cssWidth'),
              canvas_h = json_extract(payload_json, '$.canvasSize.cssHeight')
            WHERE canvas_w IS NULL
              AND json_valid(payload_json)
              AND json_type(payload_json) = 'object'
              AND json_type(payload_json, '$.canvasSize') = 'object'
              AND json_type(payload_json, '$.canvasSize.cssWidth') = 'integer'
              AND json_type(payload_json, '$.canvasSize.cssHeight') = 'integer'
              AND json_extract(payload_json, '$.canvasSize.cssWidth')
                    BETWEEN 1 AND :edge
              AND json_extract(payload_json, '$.canvasSize.cssHeight')
                    BETWEEN 1 AND :edge
        """), {"edge": MAX_EDGE})
    else:
        # The fallback, for an engine neither branch knows. This is the shape
        # that ran a box out of memory, so it is chunked to CHUNK and nothing
        # else uses it.
        posts = sa.table("skribl_posts",
                         sa.column("id", sa.Integer),
                         sa.column("payload_json", sa.JSON),
                         sa.column("canvas_w", sa.Integer),
                         sa.column("canvas_h", sa.Integer))
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
                w, h = _canvas(row[1])
                if w is None:
                    continue
                bind.execute(
                    sa.update(posts).where(posts.c.id == row[0])
                      .values(canvas_w=w, canvas_h=h)
                )
            last = rows[-1][0]

    # NO SWEEP-UP DEFAULT HERE, and that is the difference from v307. `kind`
    # had an honest answer for a payload it could not read ('pad', which is
    # what every player shows one); a canvas size does not. A row the branches
    # above could not classify keeps its NULL, and the tile frames it the way
    # it did before this column existed.
    #
    # Belt and braces for a half-written row: if one branch ever lands a width
    # without a height, neither is usable, so clear both rather than serve a
    # number the client would have to complete by guessing.
    #
    # NO TEST CAN REDDEN THIS LINE TODAY, and saying so is the point. Every
    # branch above writes the pair or writes neither -- each SQL statement
    # requires both keys before it updates, the Python loop skips a row it
    # could not read whole, and the PostgreSQL range clear nulls the two
    # together -- so removing this changes nothing that verify_migrations can
    # see, and a mutation proved exactly that. It stays as a guard on a FUTURE
    # branch, not as a claim anything is verified here. What the suite does
    # pin is the outcome: no row leaves this revision carrying one edge alone.
    bind.execute(sa.text(
        "UPDATE skribl_posts SET canvas_w = NULL, canvas_h = NULL "
        "WHERE canvas_w IS NULL OR canvas_h IS NULL"))


def downgrade():
    op.drop_column("skribl_posts", "canvas_h")
    op.drop_column("skribl_posts", "canvas_w")
