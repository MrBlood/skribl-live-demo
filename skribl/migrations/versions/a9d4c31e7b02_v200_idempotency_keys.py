"""v200: idempotency keys for POST /api/skribls.

WHY A TABLE. A POST whose response is lost in transit — timeout, dropped
connection, proxy 502 issued after the database commit — leaves the client
unable to distinguish "never happened" from "happened and I missed the answer".
Retrying then duplicates the post and spends a second rate-limit slot. The
`Idempotency-Key` header resolves a retry to the SAME post, and the mapping has
to be durable in the same database, in the same transaction, as the post it
names: anything less (a process-local dict, a TTL cache) re-opens the ambiguity
exactly when it matters, across the worker restart or failover that caused the
lost response in the first place.

SHAPE. key_hash is sha256 of author-scope + client key — author-scoped so one
client's key can never resolve to another's post, hashed so an attacker who
reads the table learns nothing they can replay. UNIQUE, so the concurrent
duplicate loses on the index and resolves to the winner. post_id cascades on
delete: a mapping whose post is gone must stop replaying it.

Scoped to SkriblBase.metadata like every other revision here — this never
touches a host's tables.
"""
from alembic import op
import sqlalchemy as sa

revision = "a9d4c31e7b02"
down_revision = "c7e1a5f04b93"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "skribl_idempotency",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("key_hash", sa.String(length=64), nullable=False),
        sa.Column("post_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["post_id"], ["skribl_posts.id"],
                                ondelete="CASCADE"),
    )
    # UNIQUE INDEX, matching Column(unique=True, index=True) on the model
    # exactly — a UniqueConstraint plus a plain index reads the same but
    # autogenerate flags the drift.
    op.create_index("ix_skribl_idempotency_key_hash", "skribl_idempotency",
                    ["key_hash"], unique=True)
    op.create_index("ix_skribl_idempotency_post_id", "skribl_idempotency",
                    ["post_id"])


def downgrade():
    op.drop_index("ix_skribl_idempotency_post_id",
                  table_name="skribl_idempotency")
    op.drop_index("ix_skribl_idempotency_key_hash",
                  table_name="skribl_idempotency")
    op.drop_table("skribl_idempotency")
