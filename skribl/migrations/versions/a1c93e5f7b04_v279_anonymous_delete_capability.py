"""v279: a revocation capability for posts that have no owner.

WHY. v278 shipped delete_post() and set_post_visibility(), authorised by
matching skribl_posts.user_id against the host's signed-in user. An audit of
that release pointed out that the DEPLOYED standalone product cannot reach any
of it — app.py passes no current_user_id, so there is no author to match and
the destructive routes are not even registered. Somebody who publishes the
wrong drawing on the live site has no way to withdraw it. The mechanism was
built; the product contract was not.

WHAT THIS ADDS. One nullable column holding the SHA-256 of a secret minted at
creation time for posts with no author. The raw secret is returned exactly once
in the create response and never stored, so a database leak cannot be turned
into the ability to delete the posts it describes.

NULLABLE, AND THAT IS THE MIGRATION'S WHOLE RISK PROFILE. Every existing row
gets NULL, which means "no capability" — those posts are exactly as revocable
as they were yesterday, which for anonymous ones is not at all. This does not
retroactively grant anyone anything and it cannot lock anyone out. Backfilling
tokens for existing rows would be pointless: there is nobody to hand them to,
since the token only has value in the browser that created the post.

REVERSIBLE. Downgrade drops the column. Any tokens issued in between stop
working, which is the honest consequence of removing the feature rather than
something to paper over.

Revision ID: a1c93e5f7b04
Revises: e9f4a7c31b28
"""
import sqlalchemy as sa
from alembic import op

revision = "a1c93e5f7b04"
down_revision = "e9f4a7c31b28"
branch_labels = None
depends_on = None


# 64 hex characters is exactly a SHA-256 digest. Sized to the thing it holds
# rather than rounded up to a comfortable power of two, so a value that does
# not fit is a value that is not a SHA-256 and should fail loudly.
_LEN = 64


def _has_column(bind, table, column):
    """True if the column is already there.

    The v269 hotfix in this same chain exists because a production database was
    stamped at head without the chain running, so "the previous revision
    definitely applied" is not an assumption this project gets to make. Checked
    rather than assumed, which also makes this revision safe to re-run.
    """
    insp = sa.inspect(bind)
    return column in {c["name"] for c in insp.get_columns(table)}


def upgrade():
    bind = op.get_bind()
    if not _has_column(bind, "skribl_posts", "delete_token_hash"):
        op.add_column(
            "skribl_posts",
            sa.Column("delete_token_hash", sa.String(_LEN), nullable=True),
        )


def downgrade():
    bind = op.get_bind()
    if _has_column(bind, "skribl_posts", "delete_token_hash"):
        op.drop_column("skribl_posts", "delete_token_hash")
