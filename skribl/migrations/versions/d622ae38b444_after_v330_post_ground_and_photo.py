"""After v330: what the drawing is painted on -- its ground, and whether it is on a picture.

WHY COLUMNS AND NOT A LOOK AT THE PAYLOAD, for the fifth time on this row and
for the same measured reason as `kind`, `pages`, `canvas_w`/`canvas_h` and
`line_json`. A host's tile lays the box around a drawing in the drawing's own
ground, and since the owner's "Yes to both, build them" (Nov 14) a drawing
made on a picture (a photo, or the picture the Pad began on) keeps that
picture, blurred, at its sides. describe_posts read both out of the payload,
by the database, on every page of a feed, and on PostgreSQL the payload is
plain `json`: every path read re-parses the whole drawing. Measured on PG 16,
24 drawings of 0.7 MB to 4.7 MB: the ground's two reads cost 80-260 ms a page,
the picture's four more 310-425 ms. Two small columns cost nothing to read.

    ground     "#rrggbb", or "" when the drawing has none a page could use
    on_photo   whether the player lays a picture under the drawing

NULLABLE, and null means "not read yet". New posts carry both from the moment
this ships (creation.py, by the player's own rules); a post from before has
NULL, and describe_posts reads that one from its drawing as it did, until
`python -m skribl.backfill_ground --write` fills it in.

AND THEREFORE NO DATA WORK HERE, which is v309's lesson, learned with two
outages: `Procfile` runs `alembic upgrade head` before the server starts, so
nothing in a revision may read the payloads. Adding a nullable column with no
default is a catalogue update -- no rewrite, nothing to run out of memory or
time. The backfill is batched, resumable and safe to interrupt, and nothing
breaks if it is never run.

Scoped to SkriblBase.metadata like every other revision here -- it never
touches a host's tables.
"""
from alembic import op
import sqlalchemy as sa

revision = "d622ae38b444"
down_revision = "a7d2c4e9b153"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("skribl_posts", sa.Column("ground", sa.String(length=7), nullable=True))
    op.add_column("skribl_posts", sa.Column("on_photo", sa.Boolean(), nullable=True))


def downgrade():
    op.drop_column("skribl_posts", "on_photo")
    op.drop_column("skribl_posts", "ground")
