"""The in-post line's two numbers: how long it took to draw, and where a viewer starts.

WHY COLUMNS AND NOT A LOOK AT THE PAYLOAD, for the fourth time on this row and
for the same measured reason as `kind`, `pages` and `canvas_w`/`canvas_h`: the
listing endpoint defers `payload_json` on purpose, so a post in a feed cannot
ask how long its drawing took. And it has to: under every post now sits the
Pad's line, "Drawn in 15 sec · watching at 1x", before anybody presses play
(the owner's pick for the in-post player, "all yes").

NULLABLE, and the null is honest. A Flip has no drawn time (its line counts
pages), and every post from before this column has none until the backfill
reaches it; the line says what it can without one, never a guessed number.

AND THEREFORE NO DATA WORK HERE, which is v309's lesson, learned with two
outages: `Procfile` runs `alembic upgrade head` before the server starts, so
nothing in a revision may read the payloads. Adding nullable columns with no
default is a catalogue update -- no rewrite, nothing to run out of memory or
time. New posts carry both from the moment this ships (creation.py); old ones
fill in when somebody runs `python -m skribl.backfill_line --write`, which is
batched, resumable and safe to interrupt.

Scoped to SkriblBase.metadata like every other revision here -- it never
touches a host's tables.
"""
from alembic import op
import sqlalchemy as sa

revision = "a7d2c4e9b153"
down_revision = "c3e8a1f5d706"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("skribl_posts", sa.Column("drawn_ms", sa.Integer(), nullable=True))
    op.add_column("skribl_posts", sa.Column("play_speed", sa.String(length=8), nullable=True))


def downgrade():
    op.drop_column("skribl_posts", "play_speed")
    op.drop_column("skribl_posts", "drawn_ms")
