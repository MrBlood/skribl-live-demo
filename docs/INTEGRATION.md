# Integrating Skribl into a Flask application

Skribl is a Flask **blueprint**. You give it a database session and, optionally,
a way to identify the current user. It does not own your app, your models, your
authentication or your templates.

Every claim on this page is exercised by `harness/verify_integration.py`, which
mounts Skribl into a throwaway host application — not into the demo — and holds
it to this contract. If the guide and the suite ever disagree, the suite is
right.

The planning record that used to live here was retired in the v263 cleanup; it lives in git history.

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
    GET  /skribl/feed                     PREVIEW of the in-post player — below
    GET  /skribl/library                  the profile's Skribls tab — below

**`/library` is registered by the blueprint whether you want it or not**, like
`/feed`. It is the profile's Skribls tab: your listing, with a full transport —
play, restart, scrub, loop, mute, copy link — around one stage, and a grid of
share cards beside it. The stage is the same in-post player driven through its
exposed handle, so the profile cannot disagree with the feed or with `/s/<id>`
about how a drawing replays, and it fetches ONE payload at a time.

It reads `GET /api/skribls` and nothing else, so it shows whatever this
deployment has, under the same visibility rules every other reader gets. It
takes no arguments and reaches no database of its own, so leaving it unlinked is
enough if you do not want it. Until recently it drew its own invented tiles;
`harness/verify_library.py` is what replaced the warning that used to be here.

**It shows the listing, not "your" listing.** `GET /api/skribls?user_id=<id>`
is the per-author filter, and Skribl has no identity of its own to fill it in
with — `create_blueprint(current_user_id=...)` is where yours arrives. A real
profile tab passes the author being viewed; this page passes nothing, and so
shows the public listing.

`url_for("skribl.skribl_player", public_id=...)` builds links. Skribl builds its
own share URLs the same way, so they are correct under any prefix.

## Putting a Skribl inside your own posts

`/s/<id>` is a PAGE — the app shell, the full transport, ~150 KB of JavaScript.
That is right for a shared link and wrong for a feed of twenty posts. The
in-post player is the other shape:

```jinja
{% from 'skribl/_skribl_inline_player.html'
     import skribl_inline_assets, skribl_inline %}

{{ skribl_inline_assets() }}          {# once per page, in <head> #}
...
{{ skribl_inline(post.skribl_id) }}   {# once per post #}
```

`GET /skribl/feed` is that, live, over your own `GET /api/skribls`. It is a
demonstration, not a dependency: the two macros above are the product and they
work without it.

**What it costs and when.** `skribl_inline_assets()` pulls five files —
`inlineplayer.css`, `inlineplayer.js`, and the shared rule modules
`lib/canvassizes.js`, `lib/holdtiming.js` and `lib/sharecard.js` — under 26 KB
served, ratcheted by `harness/verify_inline.py`. Per post, idle, it costs ONE
image: the share card at `/s/<id>/card.png`, about 20 KB, which your CDN can
cache. `GET /api/skribls/<id>` is
issued on the first tap and never again for that post. Do not prefetch it: that
endpoint returns the whole payload, base64 audio included.

**What a viewer gets.** Tap to play, tap to pause. The drawing redraws itself
with a progress hairline along the bottom edge and a nib at the pen. Two
controls, and only two — no scrub, no speed, no frame-step; those live on
`/s/<id>`:

- **Mute**, off by default and **page-wide**: sound is environmental, so
  unmuting one post unmutes the feed for that session (`sessionStorage`).
- **Loop**, on by default and **per post**: repeating is a property of the
  drawing in front of you, not a statement about the next one. Turning it off
  leaves the drawing on its last frame — and stops the music with it, in the
  same call, so a finished drawing can never be left with a loop playing under
  it.

One Skribl plays at a time, page-wide. Scrolling a playing post out of view
settles it. A post whose payload will not load says so rather than sitting dead.

**Three things to know before you wire it up.**

*Your composer decides visibility, and the default is not public.* `POST
/api/skribls` defaults to `"visibility": "unlisted"` — reachable by link, listed
nowhere — because that is what a link-sharing product should default to. Skribl's
own Pad composer has no visibility control, so nothing posted from it ever
appears in `GET /api/skribls`. If your feed is meant to list posts, your composer
sends `"visibility": "public"`.

*The macros need one name in your Jinja environment.* `init_skribl()` adds
`skribl_asset` as an app-wide template global — the only name Skribl puts in your
environment — because the macros render on YOUR view, where Skribl's blueprint
context processor does not run. It is added, never overwritten: if you already
define `skribl_asset`, yours survives and the macros will not build. If you
registered the blueprint under a name other than `skribl`, pass it:
`{{ skribl_inline(id, bp='drawings') }}`.

*The poster is the share card, cropped, and the crop is imperfect.*
`/s/<id>/card.png` is a 1200x630 Open Graph card — the drawing inside a bordered
box under a "Skribl Pad" wordmark — because that is what it was built for, and it
is the only per-post image the server has. Shown whole it reads as an advert
twenty times down a feed, so the idle post crops it back to the drawing. The
vertical crop is exact; the horizontal one is a 16:9 window, which is the widest
canvas a drawing can have, so it can only ever remove the card's ground and never
the picture. A narrower drawing therefore still shows some of the card's frame
either side. A tight per-post crop needs the canvas size where the listing can
reach it — a real column on the post, not a field inside `payload_json`, which
`GET /api/skribls` defers on purpose. That is a schema change and it has not been
made.

## Drawing one from your own composer

Your composer has a row of attachment buttons — photo, video, GIF, poll. One of
them is a Skribl. Pressing it opens the Pad over your feed; the author draws;
"Add to post" puts the drawing on the draft; pressing the button again reopens
the editor with it; your Post button publishes the lot.

**The rule: compose mode publishes nothing.** It hands your composer the
PAYLOAD, not an id. This is not a preference — the alternative is broken twice:
`POST /api/skribls` is create-only, so "publish on Add, republish on edit" makes
every edit orphan the previous skribl and spend another slot of the author's
posting quota; and an abandoned draft would leave a published, shareable skribl
behind that you have no way to withdraw. Hold the payload, exactly as you hold
an image attachment, and post once.

**The editor.** `GET /skribl-pad?compose=1`, in an iframe. An iframe even
though it is your own origin: the Pad is a whole application with its own
stylesheet and thirty-odd scripts, and putting that inline in your feed has the
two fight over every generic class name. Set the `src` when the button is
pressed, not in your markup — otherwise every visitor downloads a drawing tool
they never opened.

**The handshake**, four messages, all `postMessage`:

    editor -> host   skribl:compose:ready    up; send a payload if re-editing
    host   -> editor skribl:compose:load     {payload} put this back on canvas
    editor -> host   skribl:compose:done     {payload, preview, hasAudio}
    editor -> host   skribl:compose:cancel   closed without attaching

Target your own origin, never `'*'`, and check `e.origin` on the way in — a
wildcard hands the author's drawing to whatever page is framing the editor. If
you run Skribl on a different origin from your feed, set
`window.SKRIBL_COMPOSE_ORIGIN` on the editor page to your feed's origin.

**Showing the draft.** `SkriblInline.attach(el, payload)` renders a payload with
no id — the real in-post player, on a drawing that is not posted yet. Use it
rather than the `preview` PNG for the attachment itself: a composer that
previews a thumbnail is previewing something other than what it will publish.
The `preview` is there for a chip or a list row where a full player is too much.

**Posting.** One `POST /api/skribls` with the payload, plus whatever your post
needs: `title` (what `/s/<id>` unfurls with), `caption`, and
`"visibility": "public"` — the API defaults to `unlisted`, and a feed's composer
is exactly the caller that means otherwise. Store the returned `id` on your post
row and render it with `{{ skribl_inline(post.skribl_id) }}`.

`GET /feed` is all of the above, working, in about 150 lines of
`skribl/static/feed.js` — that file is written to be read as the host-side
recipe. `harness/verify_compose.py` drives it end to end and counts the POSTs.

**What compose mode does NOT change:** the payload. `editor_post.js` has one
`buildPostPayload()` and both endings call it, so a skribl your composer
attaches is byte-for-byte what the Pad would have posted — same serialisation,
same share-card thumbnail, same mono audio bake.

**What it does not render.** The wet/dry stroke compositor. A stroke authored
below 100% opacity beads at its overlaps here where it does not on `/s/<id>`.
Everything else — Pad replays, Flip documents with their per-page holds, the
background colour, a photo or base-snapshot underlay, the posted audio loop —
plays. The header of `skribl/static/inlineplayer.js` says why the gap is there
and what it would take to close it.

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

**The feed does not call your policy — install a filter if it must.** The
listing filters on `visibility == 'public'` in SQL and stops there. Running your
Python predicate over the fetched rows would break the keyset pagination the
feed depends on: short pages, and a `next_cursor` describing a row the viewer
never saw. So authorization that pages correctly has to be part of the *query*,
and since v224 you can contribute one:

```python
from skribl.models import SkriblPost

def hide_blocked(query, viewer_id):
    return query.filter(SkriblPost.user_id.notin_(blocked_authors_for(viewer_id)))

skribl.init_skribl(app, ..., feed_filter=hide_blocked)   # or set_feed_filter(fn, app=app)
```

Your callable receives the query with Skribl's own visibility filter already
applied and returns a query. Raising is **not** caught — a broken feed filter
should fail loudly rather than fall back to listing everything.

Whether you need one depends on your policy. If it only restricts private and
unlisted posts, the feed already excludes those and there is nothing to do. If
it can deny a **public** post — a block list, a moderation queue — then without
a filter that post still appears as metadata (title, caption, author id,
timestamp; never payload or image). `verify_hostseams.py` pins both directions.

**Two smaller seams alongside it.**

```python
skribl.init_skribl(
    app, ...,
    # Extra visibility states. Skribl's three (public/unlisted/private) are
    # always accepted and cannot be removed; the column is String(16), so
    # values are 1-16 characters. A custom state is invisible to the built-in
    # feed unless your feed_filter includes it.
    visibility_values=("draft", "moderated"),
    # Skribl has no user table, so the author block is {"id": <user_id>} and
    # nothing else. Add what you know. The id is not overridable: it is the
    # value your own visibility policy is handed.
    author_resolver=lambda uid: {"username": name_of(uid)},
)
```

**CSRF is required once you pass `current_user_id`, and refusing is the point.**
Cookie authentication plus no CSRF verifier means any third-party page can post
as your logged-in user, so `create_blueprint`/`init_skribl` now **raises** for
that combination rather than logging a warning nobody reads. Pass
`csrf=skribl.security.double_submit_csrf(...)`, or `csrf=False` to declare that
your authentication is not cookie-based (a bearer token cannot be ridden, and
such a host is not wrong).

## Database and migrations

Skribl ships Alembic migrations for its own five tables (`skribl_posts`,
`skribl_post_media`, `skribl_rate_events`, `skribl_idempotency`,
`skribl_pending_media`). Two supported approaches:

* **You own migrations.** Call `attach_to_metadata(db.metadata)` and let your
  Alembic autogenerate pick the tables up with everything else.
* **Skribl owns its migrations.** Run `alembic upgrade head` against
  `skribl/migrations` with `DATABASE_URL` set. Current head: `b7e2f9a41c55`.

Do not do both for the same tables.

## Configuration

The `SKRIBL_*` environment variables cover ceilings (frames, points, canvas
edge, image bytes/dimensions/pixels, audio bytes and WAV duration), rate
limiting, CSP, CSRF, embed origins, trusted proxies and the media backend. Each
is defined with its default beside the code that reads it — `skribl/core.py`,
`skribl/validation.py`, `skribl/ratelimit.py`, `skribl/storage.py` — rather than
counted here, because a count typed in prose is a number that rots.

Two notes worth having in advance:

* `SKRIBL_MODE` is **not** a server switch. It is a client-side template flag
  distinguishing editor from player, and it gates nothing on the server.
* Every ceiling is **process-wide**. There is no per-user quota seam yet.
* The 20-second audio loop ceiling is enforced in the CLIENT only. Since v224
  the server also caps duration (`SKRIBL_MAX_AUDIO_SECONDS`, default 900) — but
  **for WAV only**, whose header states its byte rate outright. For every
  compressed container (mp3, aac, ogg, opus, flac, webm) duration is bounded by
  `SKRIBL_MAX_AUDIO_BYTES` alone, because deriving it needs a real decoder. A 12
  MB Opus file can be an hour long and is accepted by design. Treat the 20
  seconds as an interface affordance, not policy.
* Image *dimensions* are capped as well as bytes (`SKRIBL_MAX_IMAGE_EDGE`,
  `SKRIBL_MAX_IMAGE_PIXELS`), read from the container header without a decoder.
  This rejects a declared decompression bomb — a 66-byte PNG whose IHDR says
  30000x30000. An image whose header cannot be parsed is **accepted**: a file
  that will not parse does not decode either, and a 400 on every rarer corner of
  these formats costs more than it buys.
* Title and caption have ONE limit each (`skribl.core.MAX_TITLE_CHARS`,
  `MAX_CAPTION_CHARS`), which is also the column width and the rendered
  `maxlength`. Over it is a 400. Before v224 the server silently truncated,
  which returned 201 with the user's text quietly missing.

## Maintenance jobs

**Reclaiming orphaned media.** Media bytes are written *before* the transaction
recording their association commits, so a failed or abandoned post leaves
objects nothing points at. Content addressing means this never corrupts valid
data — an orphan is simply unreachable — but at scale it accumulates.

```bash
python -m skribl.sweep --app yourapp:create_app                 # rehearse
python -m skribl.sweep --app yourapp:create_app --json          # for metrics
python -m skribl.sweep --app yourapp:create_app --delete        # reclaim
```

`--app` takes `module:attribute` like `FLASK_APP` does; a callable attribute is
called as a factory. It reads the store *your app is using* rather than
rebuilding one from the environment, which could point at a different root.

Dry run is the default and `--delete` is spelled out in full, because the
failure mode of getting it wrong is gone user media. `--older-than` (default
86400) is the grace period, and it is the safety that matters most: an object
minutes old may belong to a post being created right now, so combining
`--delete` with a grace period under an hour additionally requires
`--i-know-the-grace-period-is-short`. Do not run a short sweep while a
`backfill_media` is in flight.

Exit codes, because a scheduled job is read by its status: **0** it ran
(including "found nothing", including a dry run), **1** it ran and at least one
delete failed, **2** it could not run at all. `--json` prints one object with
the removed keys and a count for every branch that *declined* to delete —
foreign namespace, inside grace, referenced, reused mid-sweep — so a run that
reclaims nothing tells you which. Call `storage.sweep_orphans_report()` directly
if you would rather schedule it in-process.

This is not a daemon and does not schedule itself; cadence is your cron's job.

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
python3 harness/verify_integration.py        # no browser, seconds
```

It builds a host app, mounts Skribl, and checks the homepage is not stolen,
prefixes namespace every route including generated share links, attached
metadata produces tables, `current_user_id` decides authorship, a visibility
policy is enforced and — importantly — that *clearing* it restores the defaults.
A policy that is never consulted passes every test that only checks the default,
so it is installed, proven to change the outcome, then removed and proven to
stop mattering.
