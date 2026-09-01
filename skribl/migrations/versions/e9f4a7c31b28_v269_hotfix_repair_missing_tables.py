"""v269 hotfix: create any Skribl table a stamp claimed but never built.

THE OUTAGE. Production POST /api/skribls 500s with UndefinedTable:
"skribl_rate_events" does not exist — reported from the live site with Render
logs on 2026-09-01. The table has been in the chain since the v131 baseline,
and the Procfile has run `alembic upgrade head` before gunicorn since v267, so
its absence means one thing: the production alembic_version was STAMPED at (or
near) head without the chain actually executing. The proof is internal to the
chain itself — c7e1a5f04b93 (v180) and b7e2f9a41c55 (v200) both ALTER
skribl_rate_events, so a database that had really run them cannot lack it.

WHY IT SURFACED NOW. Until v268, production silently ran the MEMORY rate
limiter, so the missing table cost nothing. 78b7df3 ("real production
detection, shared limiter") auto-selects the db backend wherever a platform
marker like RENDER is present, which is correct — and turned the latent schema
drift into a 500 on every post. The same drift produced the v267 incident
(skribl_pending_media absent in production though f7c2e0a934d1 creates it);
that one was gated around in app code (#40), which silenced the error without
healing the schema — this revision is the heal.

WHAT IT DOES. For each table in the chain's FINAL state, create it — exactly
in that final shape, indexes, constraints and all — if and only if it does not
exist. On a healthy database (every fresh install, every CI run, the drift
check's scratch database) every table exists and this is a no-op, which is why
autogenerate parity is unaffected. On the drifted production database it
builds precisely what the stamp skipped.

The shapes below are FROZEN COPIES of the chain end-state (baseline + v132
visibility + v180 FK/check + v200 tz-aware timestamps + v200/v202 idempotency
+ v203 pending media), not imports from skribl.models: a migration that reads
current models changes meaning every time the models do, which is the drift
this file exists to repair.

OUT OF SCOPE, deliberately: column- or index-level drift on tables that DO
exist. The evidence (feed and share pages serve fine in production) says
skribl_posts is at least v132-shaped there; if a partial table ever surfaces,
repair it in a revision written against that evidence, not speculatively here.

Scoped to SkriblBase.metadata like every other revision here — it never
touches a host's tables.
"""
from alembic import op
import sqlalchemy as sa

revision = "e9f4a7c31b28"
down_revision = "f7c2e0a934d1"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    have = set(sa.inspect(bind).get_table_names())

    # Dependency order: skribl_posts first — two of the others FK onto it.
    if "skribl_posts" not in have:
        op.create_table(
            "skribl_posts",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("public_id", sa.String(length=32), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=True),
            sa.Column("title", sa.String(length=80), nullable=False),
            sa.Column("caption", sa.String(length=300), nullable=True),
            sa.Column("payload_json", sa.JSON(), nullable=False),
            sa.Column("has_audio", sa.Boolean(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True),
                      nullable=False),
            # server_default matches what a v132-upgraded table carries; a
            # fresh table has no rows for it to backfill, but the schemas
            # should not differ by which path built them.
            sa.Column("visibility", sa.String(length=16), nullable=False,
                      server_default="unlisted"),
        )
        op.create_index("ix_skribl_posts_public_id", "skribl_posts",
                        ["public_id"], unique=True)
        op.create_index("ix_skribl_posts_user_created", "skribl_posts",
                        ["user_id", "created_at"])
        op.create_index("ix_skribl_posts_visibility_created", "skribl_posts",
                        ["visibility", "created_at"])

    if "skribl_rate_events" not in have:
        op.create_table(
            "skribl_rate_events",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("bucket", sa.String(length=16), nullable=False),
            sa.Column("key_hash", sa.String(length=64), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True),
                      nullable=False),
            sa.Column("state", sa.String(length=10), nullable=False),
            sa.CheckConstraint("state IN ('pending', 'committed')",
                               name="ck_rate_state"),
        )
        op.create_index("ix_rate_bucket_key_time", "skribl_rate_events",
                        ["bucket", "key_hash", "created_at"])
        op.create_index("ix_rate_created_at", "skribl_rate_events",
                        ["created_at"])

    if "skribl_post_media" not in have:
        op.create_table(
            "skribl_post_media",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("post_id", sa.Integer(), nullable=False),
            sa.Column("media_key", sa.String(length=80), nullable=False),
            sa.ForeignKeyConstraint(["post_id"], ["skribl_posts.id"],
                                    name="fk_post_media_post",
                                    ondelete="CASCADE"),
        )
        op.create_index("ix_skribl_post_media_post_id", "skribl_post_media",
                        ["post_id"])
        op.create_index("ix_skribl_post_media_media_key", "skribl_post_media",
                        ["media_key"])
        op.create_index("ix_post_media_unique", "skribl_post_media",
                        ["post_id", "media_key"], unique=True)

    if "skribl_idempotency" not in have:
        op.create_table(
            "skribl_idempotency",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("key_hash", sa.String(length=64), nullable=False),
            sa.Column("request_fingerprint", sa.String(length=64),
                      nullable=True),
            sa.Column("post_id", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True),
                      nullable=False),
            sa.ForeignKeyConstraint(["post_id"], ["skribl_posts.id"],
                                    ondelete="CASCADE"),
        )
        op.create_index("ix_skribl_idempotency_key_hash",
                        "skribl_idempotency", ["key_hash"], unique=True)
        op.create_index("ix_skribl_idempotency_post_id",
                        "skribl_idempotency", ["post_id"])

    if "skribl_pending_media" not in have:
        op.create_table(
            "skribl_pending_media",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("media_key", sa.String(length=80), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True),
                      nullable=False),
        )
        op.create_index("ix_skribl_pending_media_media_key",
                        "skribl_pending_media", ["media_key"])
        op.create_index("ix_skribl_pending_media_expires_at",
                        "skribl_pending_media", ["expires_at"])


def downgrade():
    # Irreversible by design: upgrade() created only what was missing, and
    # nothing records which tables those were. Dropping all five here would
    # destroy live data on every database that was healthy. A downgrade past
    # this revision is a no-op, exactly like re-running upgrade on a healthy
    # database.
    pass
