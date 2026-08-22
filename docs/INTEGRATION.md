# Integrating Skribl into a Flask application

Skribl is a Flask **blueprint**. You give it a database session and, optionally,
a way to identify the current user. It does not own your app, your models, your
authentication or your templates.

Every claim on this page is exercised by `harness/verify_integration.py`, which
mounts Skribl into a throwaway host application — not into the demo — and holds
it to this contract. If the guide and the suite ever disagree, the suite is
right.

The planning record that used to live here is now `docs/INTEGRATION-HISTORY.md`.

---

## The smallest thing that works

```python
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import skribl
import skribl.models

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///site.db"
app.config["SECRET_KEY"] = "..."
db = SQLAlchemy(app)

# 1. Make Skribl's tables visible to YOUR metadata, so your db.create_all()
#    (or your Alembic autogenerate) sees them. Without this you get no tables
#    and NO ERROR — the first request just fails.
skribl.models.attach_to_metadata(db.metadata)

# 2. Mount it. `session` is required; everything else has a default.
skribl.init_skribl(app, session=lambda: db.session, url_prefix="/skribl")

with app.app_context():
    db.create_all()
```

That is the whole integration. You now have:

    GET  /skribl/skribl-pad               the record-and-replay drawing editor
    GET  /skribl/flip                     the frame-by-frame animation editor
    GET  /skribl/s/<public_id>            the public player
    GET  /skribl/s/<public_id>/card.png   share-card image
    POST /skribl/api/skribls              create
    GET  /skribl/api/skribls              feed listing (metadata only)
    GET  /skribl/api/skribls/<id>         one Skribl, with payload
    GET  /skribl/media/<key>              stored media, authorised per post

`url_for("skribl.skribl_player", public_id=...)` builds links. Skribl builds its
own share URLs the same way, so they are correct under any prefix.

## Three things that will bite you if you skip them

**`attach_to_metadata` is not optional in practice.** Skribl's models sit on a
declarative base Skribl owns (`skribl.models.SkriblBase`), deliberately: sharing
your `db.Model` base would couple your migrations to Skribl's. The cost is that
your `db.create_all()` cannot see them until you attach. Skip it and you get an
empty database with no complaint. An Alembic host can instead migrate
`SkriblBase.metadata` separately and never call this.

**Pass a `url_prefix` unless you mean not to.** Without one, Skribl's pages land
at your root: `/skribl-pad`, `/flip`, `/s/<id>`.

**Skribl will not take your homepage.** `GET /` is registered only if you ask
for it with `index_route=True`. This used to be unconditional, and because Flask
resolves duplicate rules by registration order and the blueprint registers
first, mounting Skribl *silently replaced the host's front page*. The default is
now False; the standalone demo opts in explicitly.

## Transaction ownership  <!-- signed off (v201): host-owned transactions, independent limiter accounting, promotion-forfeiture rule as written -->

**The contract: the HOST owns the request transaction.** You hand Skribl your
session; Skribl treats it as yours.

* **Skribl's routes flush; they never commit or roll back your session.** A
  successful `POST /api/skribls` returns with its rows *pending on your
  transaction*. They become durable when **you** commit — and that commit
  MUST happen **before the response is finalized**: `after_request`, or
  unit-of-work middleware that runs before response handoff. **Never in
  `teardown_request`** (v201 review, F1): teardown runs after the response has
  left, so a commit failure there can neither change the status the client
  already received nor be observed by Skribl's own teardown — which will
  already have discarded the quota reservation it would need to release. A
  teardown-time commit therefore yields the worst of both: a 201 the client
  believes, no durable post, and a spent rate-limit slot. This topology is
  OUT OF CONTRACT, and `verify_txcontract.py` demonstrates why. The standalone `app.py` shows the pattern: commit in `after_request`
  for sub-500 responses, rollback in `teardown_request` as the safety net. If
  your host commits nothing, Skribl's posts persist nothing — that is the
  contract working, not a bug.
* **Internal recovery uses savepoints.** Retrying a colliding `public_id`, or
  surviving a failed best-effort read on a render-always route, rolls back to a
  savepoint — never your transaction. Your pending work is untouched by
  anything Skribl does, including Skribl failing.
* **The db-backed rate limiter runs on its own sessions** (same engine, its own
  `sessionmaker`, app-local). Its accounting commits independently, because a
  failed request must still count against quota even when the host rolls the
  request back — that independence is flood protection, not an implementation
  detail. One consequence to know about: if your commit fails *after* the
  handler returned, Skribl's request teardown releases the reserved post slot
  so the client can retry.
* **Maintenance entrypoints are the exception, on purpose.** `backfill_media`
  and `sweep_orphans` take an explicit `session` argument and commit per batch
  — the payload-as-progress-marker resume design requires it. Hand them a
  **dedicated** session (e.g. from `sessionmaker(bind=engine)`), never a live
  request's.

Pinned by `verify_txcontract.py` (host-pending-row scenario, static commit
grep, standalone durability) and `verify_review.py` (limiter semantics).

## The seams

### Shared-cache opt-in (`public_media_cache`)

Everything served through an authorisation check — `/media/<key>`, the share
card — defaults to `Cache-Control: private, no-store`. Passing
`public_media_cache=True` (standalone: `SKRIBL_PUBLIC_MEDIA_CACHE=1`) lets
all-public objects be served `public, immutable` for CDN caching. Two things
the opt-in means, and you must accept BOTH:

1. **Revocation window.** Visibility is revocable; shared caches don't
   re-check. Formerly-public bytes keep serving from caches until they expire.
2. **Incompatible with viewer-dependent DENIAL.** Public-cacheability is
   decided by `visible_to(None)` — "may an anonymous viewer see this?". A
   policy that allows anonymous viewing while denying a *specific* viewer
   (per-viewer blocks, moderation targeting one account) cannot be honoured by
   a shared cache: the blocked viewer's CDN node serves the same cached bytes
   as everyone's. If your policy makes viewer-specific denials, do not enable
   this opt-in.

### SQLite transaction mode (engine-wide, on purpose)

On SQLite engines, Skribl installs two per-engine listeners alongside the
foreign-key pragma: `isolation_level = None` on connect and an explicit
`BEGIN` on transaction begin. **This changes transaction behaviour for the
whole engine — every host table, every component sharing it — not just
Skribl's tables.** It is the canonical SQLAlchemy recipe, and it is not
optional decoration: without it, pysqlite's deferred BEGIN runs Skribl's
savepoints in autocommit and `RELEASE` silently commits — the transaction
ownership contract on this page would be fiction. If your host already
installs its own BEGIN-emitting recipe, the two coexist (a double-BEGIN in
the recognised shape is tolerated). An engine explicitly configured with
`isolation_level="AUTOCOMMIT"` is refused at startup with an error, because
the contract cannot hold there and silently overriding your choice would be
worse. `SKRIBL_SQLITE_FOREIGN_KEYS=0` disables the FK pragma only; the
transaction recipe is not separately disableable, because every documented
guarantee on this page depends on it.

### Failed posts and the rate limiter (`SKRIBL_RATE_BACKEND=db`)

**Contract: after the host POST fails, no worker counts that failed
reservation against an immediate retry.** Uniform across backends; the
mechanism differs because the failure mode does.

- **PostgreSQL** — the release is an ordinary delete in the limiter's own
  session; it does not collide with the host's transaction, so every worker
  sees it at once. This is **pinned live** in `verify_postgres.py`: two
  gunicorn workers on one database, a commit failure injected on worker A,
  an immediate retry on worker B accepted, two real successes filling a
  cap-2 bucket and a third limited. It is the recommended backend for any
  multi-worker or scale deployment, and the guarantee there is a tested
  contract, not an inference.
- **SQLite** — the release delete can be undeliverable at the instant it is
  attempted, because Flask runs blueprint teardowns before app teardowns and
  the host still holds SQLite's single writer. Skribl then records the
  release in two places: process memory (the immediate fast path) and a
  **sidecar journal** next to the database file (`<db>.rate-release.journal`,
  one appended line, no database lock needed). Any worker's next request
  reads the journal when counting and applies it when it next holds a
  writer, so the guarantee survives **another worker on the same file and a
  process restart** — both pinned in `verify_txcontract.py`, with a
  counterexample showing that deleting the journal reinstates the count.
  Deliberately *not* a second write to the same SQLite database: that would
  fail for the same reason the first did. SQLite remains appropriate for
  small, single-file deployments; it is not the recommended shape for scale,
  but it is correct.

### LocalDiskStore temp files

Writes go to a unique `*.part` and rename into place; ordinary write failures
best-effort unlink their temp. A hard crash between write and unlink can still
strand one, and the orphan sweep ignores `*.part` by design — schedule an
occasional `find <media root> -name '*.part' -mtime +1 -delete` alongside your
sweep job.


All are arguments to `create_blueprint()` / `init_skribl()` unless noted.

| seam | default | what it is for |
|---|---|---|
| `session` | **required** | `lambda: db.session`. Pass `session=False` only for a test blueprint that never queries. |
| `url_prefix` | `None` | Mount point. |
| `static_url_path` | `/static/skribl` | Where Skribl's own JS/CSS is served. |
| `current_user_id` | anonymous (`None`) | Callable returning your user id, or None. Decides post authorship and who a visibility policy is asked about. |
| `csrf` | `None` | Your CSRF triple, if you use one. |
| `media_store` | inline | An object storing media out of the payload. See `skribl/storage.py`. |
| `index_route` | `False` | Register `GET /`. Standalone sites only. |

Plus one module-level seam:

```python
skribl.set_visibility_policy(lambda post, viewer_id: True | False | None)
```

Return `None` to defer to Skribl's built-in rules, so you only describe the
states you added. Built-in: `public` and `unlisted` are readable by anyone,
`private` by its author — and **any state Skribl does not define is author-only
until a policy says otherwise.** That default is deliberate: a new state should
be invisible until someone decides, not public until someone notices.

New posts default to `unlisted`. Nothing reaches a feed unless you send
`"visibility": "public"` explicitly.

## Identity and authorisation, worked

```python
skribl.init_skribl(app, session=lambda: db.session, url_prefix="/skribl",
                   current_user_id=lambda: getattr(current_user, "id", None))

# Example: hide anything from a user your site has blocked.
def policy(post, viewer_id):
    if post.user_id in blocked_authors_for(viewer_id):
        return False
    return None          # everything else: Skribl's rules

skribl.set_visibility_policy(policy, app=app)  # app-local; omit app= only in a single-app process
```

The policy is enforced on the payload endpoint and on the share card — the card
*is* the drawing, so serving it for a hidden post would leak the content itself,
not merely its existence.

**One declared limitation.** The feed listing filters on `visibility ==
'public'` in SQL and does **not** call your policy. Running a Python predicate
over a keyset-paginated query would break the pagination it depends on. So a
post your policy refuses can still appear in the feed *as metadata* — title,
author id, timestamp. No payload, no image. If your site needs the feed itself
to obey the policy, that wants a `feed_filter` seam contributing SQL, not a
Python filter; it does not exist yet. `verify_integration.py` pins this
behaviour so it cannot change silently.

## Database and migrations

Skribl ships Alembic migrations for its own four tables (`skribl_posts`,
`skribl_post_media`, `skribl_rate_events`, `skribl_idempotency`). Two supported approaches:

* **You own migrations.** Call `attach_to_metadata(db.metadata)` and let your
  Alembic autogenerate pick the tables up with everything else.
* **Skribl owns its migrations.** Run `alembic upgrade head` against
  `skribl/migrations` with `DATABASE_URL` set. Current head: `b7e2f9a41c55`.

Do not do both for the same tables.

## Configuration

Twenty-two `SKRIBL_*` environment variables cover ceilings (frames, points,
canvas edge, audio and image bytes), rate limiting, CSP, CSRF, embed origins,
trusted proxies and the media backend. They are listed with their defaults in
`skribl/validation.py` and `skribl/ratelimit.py`.

Two notes worth having in advance:

* `SKRIBL_MODE` is **not** a server switch. It is a client-side template flag
  distinguishing editor from player, and it gates nothing on the server.
* Every ceiling is **process-wide**. There is no per-user quota seam yet.
* The 20-second audio loop ceiling is enforced in the CLIENT only. The server
  caps audio *bytes*, not duration — a crafted payload can store a longer loop.
  Treat it as an interface affordance, not policy.

## What stays yours

Authentication, roles, the moderation queue, abuse reports, notifications and
the feed page itself. Skribl has no user table and no concept of staff — it
receives `current_user_id` from you and exposes decisions rather than making
them. An admin UI inside the blueprint would need its own authentication beside
the one you already have, which is how a system ends up with two answers to "is
this person staff?" and an attacker using the weaker one.

`lib/report.js` is a JavaScript **error** reporter for the maintainer. It is not
abuse reporting; users reporting content is a host feature.

## Checking your integration

```bash
python3 harness/verify_integration.py        # 14 assertions, no browser, seconds
```

It builds a host app, mounts Skribl, and checks the homepage is not stolen,
prefixes namespace every route including generated share links, attached
metadata produces tables, `current_user_id` decides authorship, a visibility
policy is enforced and — importantly — that *clearing* it restores the defaults.
A policy that is never consulted passes every test that only checks the default,
so it is installed, proven to change the outcome, then removed and proven to
stop mattering.
