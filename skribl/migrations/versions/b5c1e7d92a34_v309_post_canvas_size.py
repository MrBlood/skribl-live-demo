"""v309: how big the drawing is.

WHY A COLUMN AND NOT A LOOK AT THE PAYLOAD, for the third time on this row and
for the same measured reason as `kind`/`pages` before it: the listing endpoint
defers `payload_json` on purpose (9.75 ms against 1.04 ms for a page of fifty),
so a tile cannot ask what shape the drawing is.

WHAT IT BUYS. The idle tile shows the share CARD, and the card CONTAINS the
drawing: a 4:3 drawing inside a 1200x630 card leaves 110px of card ground and
the card's plate border on each visible side, so a gallery of tiles showed a
picture inside a frame inside a card (owner: "fix the share card bands too").
The client crops the card back to just the drawing -- lib/sharecard.js
drawingRect() has been the arithmetic since the card was written -- given the
drawing's size, which is what these two columns carry.

NULLABLE, and the null is honest rather than lazy. `canvasSize` is OPTIONAL in
a payload and always has been: a Skribl authored before Pad had a size picker
simply has none, and lib/canvassizes.js supplies the default at play time. A
row nothing can answer for stays NULL, and a null renders as the BAND crop the
tile used before this column -- never as a guessed 4:3, which would frame the
picture wrongly instead of framing it widely. Same rule as `has_audio` and
`kind` on the same row.

AND THE NULL IS WHY THIS REVISION CARRIES NO DATA WORK. See upgrade(): the
backfill lived here, took the deploy down twice, and now lives in
`skribl/backfill_canvas.py`, where it runs in bounded batches outside the release
path. Because a null is a supported state, a post that has not been backfilled
yet is not broken -- it simply looks the way it did last week.

Scoped to SkriblBase.metadata like every other revision here -- it never
touches a host's tables.
"""
from alembic import op
import sqlalchemy as sa

revision = "b5c1e7d92a34"
down_revision = "a2f6c8b30e14"
branch_labels = None
depends_on = None


def upgrade():
    """TWO COLUMNS, AND NOTHING ELSE. The backfill is `python -m skribl.backfill_canvas`.

    THIS REVISION HAS NOW FAILED A DEPLOY TWICE, and the second time is why
    there is no data work left in it.

    The first failure was a cast running before the guard meant to protect it:
    PostgreSQL sorts WHERE quals by estimated cost, so a funnel written top to
    bottom is not a funnel. `invalid input syntax for type numeric: "{"a":1}"`.
    That was a real bug, and the fix for it lives in the backfill command.

    The second was not a bug in the SQL at all:

        psycopg.OperationalError: consuming input failed:
        SSL error: unexpected eof while reading

    The backend went away mid-statement. Every JSON operator on a `json`
    column detoasts and re-parses the WHOLE document, and that statement
    called five of them per row -- so a table of multi-megabyte drawings was
    parsed five times per row, in a single statement, on a small instance.
    That is the v307 out-of-memory lesson again, moved from Python into the
    database rather than answered.

    THE REAL MISTAKE WAS PUTTING IT HERE AT ALL, and it took two outages to
    see it. `Procfile` is `alembic upgrade head && gunicorn app:app`, so
    anything in this function can take the site down -- and what this function
    was doing is COSMETIC. A null canvas size is a supported state: the column
    is nullable by design and the tile falls back to the band crop, which is
    what every post did before v309 existed. A picture framed a little wide is
    not worth an outage; a schema change that cannot fail is worth a lot.

    So: add the columns, return. Adding a nullable column with no default is a
    catalogue update -- no table rewrite, no payload read, nothing to run out
    of memory or time. New posts carry the size from the moment this ships
    (creation.py). Old ones fill in when somebody runs the backfill, which is
    batched, resumable and safe to interrupt.
    """
    op.add_column("skribl_posts", sa.Column("canvas_w", sa.Integer(), nullable=True))
    op.add_column("skribl_posts", sa.Column("canvas_h", sa.Integer(), nullable=True))


def downgrade():
    op.drop_column("skribl_posts", "canvas_h")
    op.drop_column("skribl_posts", "canvas_w")
