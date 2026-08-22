# v132 — Skribl becomes a Flask blueprint

Two changes, in this order, each verified against the harness before the next
started. Numbers below are from real runs on Chromium 141.0.7390.37 — the same
build recorded in `harness/LAST-RUN.txt`.

## Baseline reproduced first

Pristine v131, this machine: **632 assertions, 18 suites, all green**
(`verify_postgres.py` excluded — no live PostgreSQL). Every claim below is
measured against that number, not against the number in the README.

## Step 1 — the URL seam

**The bug this closes.** The Pad and Player set `window.SKRIBL_API_BASE`, but as
a hardcoded `"/api/skribls"` literal. Flip had **no config block at all**, so
`flip.js` hardcoded both `fetch('/api/skribls')` and a `'/s/' + id` fallback.
A `url_prefix` would therefore have broken posting on Flip *silently*: the
harness drives the root prefix too, so all 632 assertions would have stayed
green while production posting 404'd.

- `skribl_flip.html` gains a nonced config block, matching the other two.
- All three read `skribl_api_base` / `skribl_player_base`, derived from
  `url_for()` in the context processor. No route literal survives in a template.
- `flip.js:1251,1254` and `app.js:5696` read the injected globals, with no
  literal fallbacks — a missing config now fails loudly instead of quietly
  posting to the wrong origin.

Result: **632/632**, unchanged. Shippable on its own, and it is what makes the
prefix move a one-line registration change.

## Step 2 — the blueprint

`app.py`: **1202 lines -> 81**. What remains is only the host's job — Flask app,
secret key, database URL, register the blueprint. That is exactly what the
social platform will do instead.

    skribl/__init__.py    61   create_blueprint() / init_skribl() + the contract
    skribl/core.py        87   version, OG defaults, id validation, env parsing
    skribl/models.py     151   the two tables, and the session seam
    skribl/ratelimit.py  226   in-memory + database-backed limiting
    skribl/validation.py 387   media signatures + structural complexity
    skribl/security.py   243   embed origins + CSP
    skribl/routes.py     263   the seven routes

Bodies were sliced out of `app.py` by line range rather than retyped, so the
moved code is byte-identical apart from the mechanical edits listed below.

### Three substantive changes, not just repackaging

**1. Off flask_sqlalchemy.** The models were declared on a module-level
`db = SQLAlchemy()` that Skribl owned. A host with its own `db` would have had
two SQLAlchemy instances: two MetaDatas, two sessions, **no shared transaction**
— a Skribl post could commit while the host's feed row rolled back. They are now
plain SQLAlchemy 2.0 models on `SkriblBase`, with the session injected:

    skribl.init_skribl(app, session=lambda: db.session)

`SkriblBase.metadata` is exported for Alembic. `attach_to_metadata()` is an
optional bridge for hosts that want one `db.create_all()`. `Model.query` is kept
as a thin shim over the injected session so existing query sites read the same.

**2. CSP is blueprint-scoped.** It was an app-wide `after_request`, which in a
host app would either clobber the platform's policy or be clobbered by it. It
now attaches to the blueprint, covering Skribl's routes and Skribl's static
files and nothing else. `verify_csp.py` passes 31/31 under it, including the
assertion that static assets carry the headers.

One consequence, handled explicitly: a 404 on an unrouted path no longer reaches
Skribl's `after_request`. Standalone, that 404 is still Skribl's and must not be
framable, so `app.py` calls `install_standalone_security(app)`. **A host must not
call it** — its own 404s are its own to police. This is the one place where
"Skribl is the whole site" and "Skribl is a component" genuinely differ, and it
is now a one-line, documented choice rather than an accident.

**3. The auth seam exists.** `user_id=1` is now `bp.skribl_current_user_id()`,
injectable via `create_blueprint(current_user_id=...)` and defaulting to a
callable returning 1, so standalone behaviour is unchanged. Skribl never imports
`flask_login`.

### URLs did not move

The blueprint registers with no `url_prefix` and `static_url_path` defaulting to
`/static/skribl`. Every URL, including asset URLs, is byte-identical to v131.
Moving to `/skribl` is now a keyword argument in `app.py`.

Result: **632/632, all 18 suites** — identical to the v131 baseline.

### The prefix move, proven

`SKRIBL_URL_PREFIX` mounts Skribl anywhere. `NEW harness/verify_prefix.py`
(26 assertions) boots a second instance at `/skribl` on its own port and drives
it with a real browser: all three surfaces answer under the prefix and 404 at
the root, blueprint static follows, the injected config carries prefixed routes,
a post round-trips end to end, and the CSP still applies.

It found a bug the root-prefix suites structurally could not: the 201 response
body returned a hardcoded `f"/s/{public_id}"`. The client trusts that value for
the share link, so every share from a mounted instance would have pointed at the
host's root. Now `url_for(".skribl_player", ...)`.

## Harness changes, and why they were necessary

Five suites asserted on the source **layout** rather than on behaviour, and the
package move broke them. Each was made layout-agnostic rather than re-pointed,
so one harness runs against both the pre- and post-refactor trees and the
comparison stays honest:

- **NEW `harness/_layout.py`** — resolves `TEMPLATES_DIR`, `STATIC_DIR`,
  `template()` and `vendored()` against either layout.
- `verify_muxer.py`, `verify_gifenc.py` — filesystem guards for the vendored
  libraries. These SKIP with exit 1 when the file is missing, so the runner
  correctly reported a problem rather than silently passing.
- `verify_version.py` — read `SKRIBL_VERSION` out of `app.py`, and globbed
  `templates/`. Now pins the constant, wherever it lives.
- `verify_review.py` — imported helpers as `import app as A` and read
  `static/skribl/*.js`. Now goes through a facade over the package with
  **write-through `__setattr__`**: several assertions monkeypatch module globals
  (`_TRUSTED_PROXIES`, rate caps), and without write-through the patch would
  land on the facade and the assertion would pass for the wrong reason.
- `run_harness.sh:46` — grepped `SKRIBL_VERSION` from `app.py`, so the run
  header printed a **blank version**. Now checks `skribl/core.py` too.

## Two standing guards added

**`harness/verify_seam.py`** (41 assertions, source-only — no server, no
browser). Section 1 fails if a route literal reappears in client JS, if any
surface stops being handed its routes, if a config block loses its nonce, if a
hand-typed `?v=` bust returns, or if the route layer rebuilds a share URL by
hand. Section 2 sweeps every module for module-level names no import provides —
the check that would have caught all five NameErrors below in seconds.

**Asset cache-busts are now content-derived.** `styles.css?v=124`,
`app.js?v=121`, `audioloop.js?v=102`, `flip.js?v=131` were four hand-typed
numbers that nothing verified: `verify_version.py` explicitly skips them and
Playwright starts every run cold, so a stale bust was invisible to the harness
*by construction*. A returning user would have run old JS against a new server.
`skribl_asset()` derives the bust from a SHA-256 of the file, cached on
(mtime, size). Verified live: editing a file changes its bust.

`verify_review.py` had an assertion pinning `v='121'` literally — the very
number it was meant to protect, requiring a hand edit every release. It now
tests the mechanism and accepts either form, so it is valid on both trees.

## Found along the way

- **Four latent `NameError`s** that the harness had not yet reached, caught by a
  static sweep of unresolved module-level names rather than by a test:
  `MAX_CARD_BYTES` (validation), `RATE_PENDING_TTL` and `RATE_CLEANUP_BATCH`
  (rate limiter — these were config sitting in the validation block, now in
  `core.py`), `ipaddress`, and `IntegrityError`. Only the first was reachable by
  an existing suite; the other three would have surfaced in production.
- **`verify_pages.py` has a flaky assertion.** "collapses to exactly zero height"
  failed once at `0.015625` (1/64 px) and passed on three subsequent runs. It is
  a sub-pixel rounding race in the collapse measurement, not a regression — it
  wants a tolerance, or a wait on transition end.
- **A timed-out harness run leaves a server bound to 5001**, and the next run
  then tests against the *stale tree* while reporting green. This cost a cycle
  and produced three false failures. FIXED: `run_harness.sh` now clears the port
  and refuses to run if something else still holds it.
- The zero-height assertion in `verify_pages.py` now tolerates half a pixel
  rather than demanding exact zero. FIXED.

## Not done

- `verify_postgres.py` (14 assertions) — needs a live PostgreSQL.
- The README/HANDOFF/harness-README assertion counts are still three different
  numbers, and `SHA256SUMS` still claims 50 files where it covers 52. The
  version/count stanza wants generating, not editing.
- MP4 export still never exercised in a real Chrome.
- The tree hash in `LAST-RUN.txt` still cannot be reproduced from a shipped
  archive, because four doc files are edited after the run that records it.


## Final tally

**699 assertions, 20 suites, all green**, on both the root mount and a `/skribl`
mount. That is the v131 baseline of 632 plus `verify_seam.py` (41) and
`verify_prefix.py` (26). The seam-only tree passes the same shared harness.


## PostgreSQL: run at last, and one real finding

A live PostgreSQL 16.14 was installed, so `verify_postgres.py` ran for the first
time (**14/14**) and the whole harness ran against Postgres rather than SQLite.

**`verify_postgres.py` had a vacuously passing assertion.** It resolved the
rate-limit identity with `import app; print(app._rate_key(...))` and, on a
non-zero exit, swallowed the failure into `KEY_HASH = ""`. Both the committed
and pending queries then matched zero rows, so "no reservation was stranded in
pending" passed *because nothing was found*, not because nothing was stranded.
The probe now tries both layouts and SKIPS loudly rather than reporting on an
identity it could not resolve.

**The runner could not actually run against PostgreSQL.** It overwrote any
supplied `DATABASE_URL` with a temp SQLite file unless `SKRIBL_KEEP_DB=1`, which
also gave up fresh-database isolation — and the banner still printed `sqlite`,
so a Postgres run silently was not one. Engine choice and isolation are now
independent: an explicit `DATABASE_URL` is honoured and reset by dropping and
recreating Skribl's tables.

**The finding: the database-backed rate limiter over-rejects on PostgreSQL.**
With `SKRIBL_RATE_BACKEND=db` and a quota of 2 against a fresh identity:

    SQLite      201 201 429      correct
    PostgreSQL  201 429 429      v132, one slot lost
    PostgreSQL  429 429 429      v131, every slot lost

`verify_review.py`'s twelve-way fresh-bucket race admits 2 on SQLite and **0** on
PostgreSQL, deterministically, on both trees. This is **pre-existing and not
caused by the refactor** — v131 is worse than v132. It is also precisely what
`RateEvent`'s own docstring warned about: *"Verified under SQLite and threads;
NOT yet verified on PostgreSQL across processes. Treat the guarantee as 'biased
safe', not proven."* It is now verified, and the bias is real.

Direction of the bias is safe — it refuses too much, never admits too much, so
there is no over-admission hole. But on a deployment backed by Postgres it can
lock out legitimate posters, and at v131's behaviour it refuses *everything*
once the DB backend is on. The memory backend (the default) is unaffected, which
is why this never showed up in production.

Worth noting the shape of it: `verify_postgres.py` passes 14/14 because it
spawns gunicorn and exercises admission counting, while this path is the
in-request reserve on a fresh identity. Two adjacent behaviours, one covered.

## Final tally

**713 assertions, 21 suites** — the v131 baseline of 632, plus `verify_seam.py`
(41), `verify_prefix.py` (26) and `verify_postgres.py` (14), which had never run.

- On SQLite: all 21 suites green.
- On PostgreSQL: 20 of 21 green; `verify_review.py` 275/277, failing only the
  two assertions of the pre-existing limiter bug above.

## Repository setup

**Commit everything except `SHA256SUMS`.** It is a delivery artifact for zip
archives; git content-hashes every file already, so committing it is redundant,
it churns on every commit, conflicts on every merge, and a stale manifest
asserting wrong digests is worse than no manifest. Now in `.gitignore`, along
with `harness/.pg_gunicorn.log`. The existing Python template already excludes
`instance/`, `__pycache__`, `.env` and `.venv`. Verified with `git add -A`
against a fresh checkout: 63 files tracked, no secrets, nothing stray.

**`.gitattributes`** marks the two vendored libraries `linguist-vendored`, so
GitHub's language stats describe the code written here rather than reporting the
project as mostly minified JavaScript, and pins `*.sh` to LF (CRLF would break
run_harness.sh's shebang).

**The tree hash is reproducible now.** Its two branches were hashing DIFFERENT
FILE SETS: `git ls-files` lists tracked files INCLUDING `harness/LAST-RUN.txt`
and `SHA256SUMS`, while the `find` fallback excluded them. Inside a checkout the
hash therefore covered the very file the run was writing, so it could never be
reproduced — which is why the shipped v131 archive's recorded hash could not be
re-derived. Both paths now apply the same exclusions, via `_tree_files` /
`_tree_hash`. Verified: two consecutive runs in a checkout produce an identical
hash, and it matches the hash computed outside a checkout, so the branches agree.

**A dirty working copy is now labelled.** `Git commit: c2ecb96-dirty` when there
are uncommitted changes. A clean-looking SHA over an edited tree is exactly the
kind of claim this banner exists to prevent.

**`.github/workflows/harness.yml`** runs the full `run_harness.sh` — not a
subset — on both engines: SQLite, and PostgreSQL 16 as a service container with
a `pg_isready` health check. The Postgres job is `continue-on-error` with the
known limiter failure documented inline; remove that once the limiter is fixed.
Both jobs upload `LAST-RUN.txt` as an artifact.

## v133 — the integration blockers

All five Tier-1 items. Every number below is from a real run on both engines.

### 1. The rate limiter admitted ZERO under concurrency (fixed)

An earlier draft of this document reported this as "PostgreSQL over-rejects,
pre-existing, v131 is worse." Two of those three claims were wrong, and the
correction matters more than the original:

The cause is CONCURRENCY, not PostgreSQL. Reservation was INSERT → COMMIT →
COUNT → withdraw-if-over. With twelve simultaneous posts against a quota of two,
all twelve inserts commit before any count runs; every request then sees 12 > 2
and withdraws its own row. Zero admitted, not two. SQLite hid it completely by
serialising writes, so the requests effectively queued and each count was
correct. A sequential test on PostgreSQL also passes — the bug needs contention.

Fixed with a transaction-scoped advisory lock keyed on the identity hash, plus
`flush()` instead of `commit()` so the whole reserve-and-count happens inside one
transaction. The lock serialises only requests sharing an identity, so unrelated
posters never contend, and it is released on commit, rollback, or process death.

  before   [429] x12    zero admitted
  after    [201, 201, 429 x10]    correct, and 14/14 across 4 gunicorn processes

### 2. The feed (NEW: GET /api/skribls, verify_feed.py, 24 assertions)

Skribl could not back a feed at all: the only read returned the full payload.

* Keyset cursor pagination on `(created_at, id)`, not OFFSET — offset makes the
  database walk and discard every skipped row, and duplicates or skips items
  whenever a post lands mid-scroll, which is a live feed's normal state. Pinned
  by inserting a post BETWEEN pages and asserting zero overlap.
* A `visibility` column with three states, not a boolean. "Not in the feed" and
  "not reachable by link" are different products, and collapsing them would
  break every share link already issued.
* Payloads are structurally absent. A feed row measures 161 bytes.

### 3. CSRF (NEW: verify_csrf.py, 13 assertions)

`double_submit_csrf()` — dependency-free, `compare_digest`, SameSite=Lax.
Verified against cookie-without-header, wrong header, and header-without-cookie.

OPT-IN, off by default. Defaulting it ON broke 24 assertions across other
suites, every one a token-less POST getting a correct 403 — which is the right
signal: standalone Skribl is unauthenticated, so CSRF protects nothing there and
only breaks existing clients. A host that authenticates the endpoint must switch
it on. The suite boots its own instance rather than changing the shared one.

Also caught here: the token was first issued in `after_request`, which runs AFTER
the template renders, so pages shipped an empty `window.SKRIBL_CSRF_TOKEN` and
every post was refused. Split into before/after hooks.

### 4. Migrations (NEW: skribl/migrations, verify_migrations.py, 13 assertions)

Alembic scoped to `SkriblBase.metadata`, with `include_object` filtering, so a
host's tables are never touched and autogenerate cannot propose dropping them —
both asserted against a database containing a host table.

Two revisions, deliberately: the baseline describes the v131 schema EXACTLY
(autogenerate folded v132 in; it was stripped back out) so an existing
deployment can `alembic stamp` it and upgrade, rather than being told to create
tables it already has. The v132 revision adds `visibility` with
`server_default='unlisted'` — without one, adding a NOT NULL column to a
populated table fails, and every existing post is such a row. 'unlisted' is the
correct backfill: 'public' would retroactively publish every Skribl ever made.

`verify_postgres.py` started returning 500s the moment `visibility` landed,
because it reuses a long-lived database and `create_all()` cannot add a column
to an existing table. That is precisely the failure migrations prevent, so the
suite now runs the real chain and every PostgreSQL run dogfoods it.

### 5. Media out of the database (NEW: skribl/storage.py, verify_storage.py, 21)

Backends: `inline` (DEFAULT — exactly v131), `local`, and a subclass hook for S3
needing only `put_bytes` and `url_for_key`. Default is inline on purpose: a
storage change to a system holding real posts is opted into, never inherited,
and one assertion exists solely to prove the default has NOT silently changed.

* Keys are the SHA-256 of the CONTENT, so identical media is stored once however
  many posts carry it, and a blob can be cached `immutable` forever.
* Externalisation happens AFTER validation. Order matters: writing first would
  let an attacker place arbitrary bytes in the store.
* Content type is served from a sidecar, never sniffed from the filename.
* Keys are matched against an allowlist (`^[0-9a-f]{64}\.[a-z0-9]{2,4}$`), not a
  "../" blocklist. Traversal, encoded traversal, and malformed keys all 404.
* `flip.js:1110` was the ONLY place either client cracked a data URL open
  structurally; it now handles both forms. Everywhere else assigns to a `src` or
  fetches, and both work unchanged.

### Final tally

**805 assertions, 25 suites, green on SQLite and PostgreSQL.**
v131's 632, plus verify_seam (42), verify_prefix (26), verify_feed (24),
verify_storage (21), verify_csrf (13), verify_migrations (13), verify_postgres
(14, which had never run before this work).

### Still open

* `app.js` remains 6,589 lines. Step 3b reconciliation recovers ~1,300; the
  payload win comes from splitting out READ-ONLY PLAYER (498 lines) so viewers
  stop downloading the editor.
* MP4 export has still never run in a real browser.
* An S3 backend is a hook, not an implementation.
* `connect-src data:` can narrow once a deployment runs on external media, but
  the default is still inline so the policy cannot tighten yet.

## v134 — Tier 2

### The run record was never machine-generated

`run_harness.sh` did not write `harness/LAST-RUN.txt`. The file shipped in the
v131 archive was assembled BY HAND from the script's stdout. That single fact
explains two things previously treated as separate puzzles: why the recorded tree
hash could never be reproduced, and why three different assertion totals ended up
in three different documents. A record typed by a person drifts from the run it
describes; "machine-generated" in the banner was aspirational.

The runner now emits it — full RUN CONTEXT header plus aggregate — and
`harness/stamp_docs.py` stamps the docs from it into a marked stanza.
`--check` exits 1 on drift. 646/19, 615/18 and 345/17 are now one generated line.

### A full single-invocation run used to hang

`timeout 600` was already in the suite loop and never fired: it signals only its
DIRECT child, while a suite's Playwright browsers keep the output pipe open, so
the shell blocks on the read after python is gone. Now `setsid` plus
`timeout -k 15`, tearing down the whole process group.

Never hit before because `LAST-RUN.txt` shows the harness has only ever run in
BATCHES — so the configuration CI uses is the one that was never exercised.

### MP4 has a path to verification

The reason it went unverified since v103 is concrete: Playwright's bundled
Chromium has no `VideoEncoder` at all, and real Chrome has WebCodecs but reports
no supported H.264 profile (`avc1.42001f`, `avc1.4d0028`, `avc1.640028` all
false). `verify_mp4.py` encodes twelve frames, muxes them, and walks the
container — ftyp first, moov and mdat present, box sizes tiling the file exactly,
moov before mdat so it streams. It SKIPS where no encoder exists, and a third CI
job runs it on real Chrome with a step that FAILS if it only skipped.

### app.js: measured, not split

The split was NOT attempted. The measurement that would justify it now exists as
a permanent guard (`verify_seam.py` section 3):

    player-reachable  86 functions / 1339 lines
    editor-only      129 functions / 2467 lines

Every `/s/<id>` visitor downloads the eraser cursor, export pipeline, post
composer and autosave machinery in order to watch a drawing.

Why it was not done here: the READ-ONLY PLAYER section is 498 lines, but its own
comment is accurate — it reuses `loadSkribl()` and `replayTimelineToCanvas()`, so
it is not a clean cut. And 2,783 of app.js's 6,589 lines sit OUTSIDE any function,
in top-level IIFE code whose hoisting order is what makes the split dangerous.
Doing it badly with no runway left to verify would be worse than not doing it.

The guard is a RATCHET, not a target: it fails if editor-only code migrates into
the player's reachable set, which is how a split quietly becomes impossible.

### The split was ATTEMPTED and REVERTED — read this before trying again

A first cut was built and backed out. The attempt is worth more than the
measurement, because it disproved the method.

**What was tried.** Reachability from the READ-ONLY PLAYER section gave 129
editor-only functions. Of those, 91 are referenced by app.js's TOP-LEVEL
statements — `addEventListener('click', openExport)` evaluates the identifier at
load, so those cannot move while the wiring stays. The other 38 (642 lines) were
extracted to `app-editor.js`, loaded `defer` by the editor template only and NOT
by the player template.

**Result.** Both files passed `node --check`. `verify_pages.py` then failed:
after Clear, the Undo toast never appeared, and the click timed out at 30s.
Reverted; the tree is green again at 6,596 lines.

**Why it failed, and this is the important part.** The call graph was built with a
REGEX (`\bname\s*\(`). That misses real call sites — optional chaining, calls
through an alias or object property, references inside template strings, handlers
passed by name to something the regex did not model. So functions the player
genuinely needs were classified editor-only. `skriblPostHeaders`,
`ensureStrokeLayers`, `presentWet` and `beginWetStroke` all moved, and the
wet-layer functions are core stroke rendering that the player's replay path
reaches.

**Do not retry with a regex call graph.** A textual approximation is fine for
MEASURING the size of the prize and useless for deciding what is safe to move.

### The AST step was built, and it DISPROVES the paragraph above

The advice used to continue: "the next attempt needs a real JS parser building a
real reference graph — an AST pass over app.js is a few hours of work and would
have caught every one of these." That was a hypothesis stated as a fact. It has
now been built (`harness/tools/refgraph.js`, acorn, declarations at any depth,
every identifier in a load position attributed to its enclosing declaration) and
it is **wrong on both counts**:

* Its own proposed acceptance gate — the AST player-reachable set must be a
  strict superset of the regex one — **FAILS**. Three names present in the regex
  set are absent from the AST set.
* All four functions the attempt wrongly moved — `skriblPostHeaders`,
  `ensureStrokeLayers`, `presentWet`, `beginWetStroke` — are **still classified
  editor-only by the AST**. A parser would have moved every one of them again.

**Because the diagnosis was wrong.** Those four are not misclassified. Read the
call sites: `ensureStrokeLayers`, `presentWet` and `beginWetStroke` are reached
only from the live pointer handlers, and the player's replay path goes through
`makeStrokeCompositor` instead — they genuinely are editor-only. `skriblPostHeaders`
is now called from `editor_post.js`. The classification was right and the move
still broke, so the fault was never the call graph.

The fault was **load order**. `app-editor.js` was loaded `defer` after `app.js`
while `app.js`'s own top-level statements still named those bindings, and the
failure that surfaced was editor-side (`verify_pages`, the Undo toast after
Clear) — not a player regression at all. Every cut that has SUCCEEDED since
(`editor_export`, `editor_post`, `editor_menu`, `editor_music`, `editor_photo`)
moved statements rather than bindings and loaded after `app.js`. That is also
what item 3 of the v190 deploy notes warns about.

**Revised order. Step 2 was always the real work; step 1 was never the blocker:**
  1. ~~Build the reference graph with an AST~~ — done, and it does not decide
     safety. Use it, like the regex, to size the prize only.
  2. Move top-level wiring into explicit init functions so hoisting stops being
     load-bearing. This is the whole job.
  3. Only then draw the module boundary.

### And the target does not close even if step 2 is done perfectly

Measured, this tree: the player downloads 231,106 B of JavaScript across four
files. `verify_player_isolation.py` targets 153,600, so the gap is 77,506 B.
Every editor-only function in `app.js`, by the AST graph, is 71,633 B. Move
**all** of them — including the ~34 KB that step 2 exists to unpin — and the
player lands at 159,473 B. **Still 5,873 B over.**

Extraction cannot reach 153,600, because what is left is not functions: roughly
88 KB of `app.js` is top-level wiring and comments, outside every function body.
Reaching the target means `app.js` stops being the player's file at all — a
separate player entry point — not another cut. Anyone continuing this should
either commit to that or move the number and say why, because a target the
available method provably cannot reach is the failure mode the ratchets were
written to prevent.

The section-3 ratchet in `verify_seam.py` stays, with the caveat that its numbers
are a regex approximation: treat 2467/1339 as an order-of-magnitude estimate of
the prize, not as a safe-to-move list.

## External review — seven findings, all confirmed, all fixed

An outside review found seven issues. Every one reproduced. Notes on cause:

1. **Private posts were not private.** `visibility` was enforced on the FEED and
   nowhere else. `GET /api/skribls/<id>` returned the whole payload, `/s/<id>`
   served title+caption in the Open Graph tags, and `/s/<id>/card.png` served the
   drawing's own thumbnail — that last one leaks the artwork, not just its
   existence. Fixed with one rule, `SkriblPost.visible_to(viewer)`, applied to
   all three. Returns 404 rather than 403 so a refusal is not an enumeration
   oracle. **Cause: `verify_feed.py` asserted privacy on the listing only, passed,
   and produced false confidence. A rule enforced in one place is a filter.**
2. **`@bp.app_context_processor` + relative `url_for`.** Application-wide by
   Flask's definition, so it ran for host templates, where `url_for(".create_skribl")`
   raises BuildError. `add_app_template_global("skribl_asset")` had the same
   defect. Both are blueprint-scoped now. **Cause: I scoped the CSP to the
   blueprint, wrote a comment congratulating myself, and never audited for the
   other app-wide hooks I had chosen deliberately.**
3. **Rejected posts burned quota.** The visibility check returned 400 AFTER
   `_rate_reserve_post()` and BEFORE the `try/finally`, and media was written to
   the store before that rejection. Validation now precedes reservation, and
   externalisation moved inside the try.
4. **`@bp.app_errorhandler(413)`** answered for the host's routes. Now
   `errorhandler`.
5. **`visibility` ORM default was `"public"`** while the route and migration said
   `unlisted` — a host constructing `SkriblPost` directly would silently publish.
6. **CSRF documented as a pair, implemented as a triple.** It grew `prepare` when
   the token-ordering bug was fixed and the docs were not updated.
7. **The harness accounting was itself unverifiable.** `stamp_docs.py`'s generated
   text promised a `verify_docs.py` that did not exist, ARCHIVE-README claimed a
   suite count that was wrong, and `--check` reported all three docs stale.

**Two new suites.** `verify_privacy.py` (33) is organised by SURFACE, not by
rule, and includes an in-process section that hits every read path as a DIFFERENT
user and as an anonymous one — the deny path the shared harness structurally
cannot exercise, because it posts and views as the same user. That blind spot is
what let the bug ship. `verify_docs.py` (10) checks the stanza is current, that
no document names a suite that does not exist, that hand-typed suite counts match
disk, and that every requirement appears in the lockfile.

**Found while fixing:** `skribl.models.bind_session()` is module-global, so each
`init_skribl()` re-binds the session for the whole process. Harmless in
production — a process hosts one Skribl — but two blueprints in one process would
share a session. Documented in verify_privacy.py where it bit the test.

## Second external review — six findings, all confirmed

1. **"Private" was not private in the standalone app.** `current_user_id`
   defaulted to `lambda: 1` — a stand-in for v131's hardcoded author stamp. Fine
   as an author id, catastrophic as a VIEWER id: once `visible_to()` consulted
   it, every visitor WAS user 1, so user 1's private posts were readable by
   everyone. The rule was enforced correctly against an identity that was a lie.
   Default is now `lambda: None` — anonymous, which is the truth for an
   unauthenticated deployment.
2. **A private post with no owner is now refused (400).** Previously creatable
   and then unreadable by its own maker, since `visible_to(None)` denies a post
   whose `user_id` is None. A write-only Skribl is not a feature.
3. **`/media/<key>` bypassed visibility completely.** It checked key SHAPE and
   file existence, never which post referenced the object. Externalising media
   silently routed around the rule the other three surfaces enforce. It now
   resolves the referencing posts and requires at least one to be visible to the
   caller; an orphaned object is a 404.
4. **Private responses were marked publicly cacheable.** `card.png` sent
   `public, max-age=86400` and `/media/<key>` sent `public, immutable` regardless
   of visibility, so a shared CDN could cache an authorised author's thumbnail
   and serve it onward without re-running `visible_to()`. Both now send
   `private, no-store` unless every referencing post is public.
5. **`stamp_docs.py` could stamp "all green" over a failed run.** It parsed only
   the `ok` lines and emitted the phrase unconditionally. It now parses failures
   and writes "RUN NOT GREEN — N suite(s) failed" instead.
6. **The provenance flow was circular.** `verify_docs.py` runs inside the suite
   loop, so it validated the PREVIOUS record, which the runner then overwrote.
   And the tree hash covered README.md, harness/README.md and docs/HANDOFF.md —
   the very files `stamp_docs.py` rewrites afterwards, so recording a result
   changed the tree whose hash had just been recorded. Fixed both ways: the
   generated documents are excluded from the hash, and the runner stamps
   immediately after writing the record. Verified: the hash is now identical
   before and after stamping.

### Not fixed — known limitation

**The session factory is process-global.** `skribl.models.bind_session()` is
module scope, so each `init_skribl()` re-binds it for the whole process and
creating app B makes app A's routes query B's database. One Skribl per process is
safe, which covers production and the standalone app; multiple app instances in
one process (some test factories, multi-tenant WSGI) are NOT. Fixing it properly
means resolving the session per-request from the blueprint rather than a module
global. Documented rather than half-done.

## v135 — third external review

All six findings fixed. The first three shared one root cause and one fix.

**Media authorisation was a substring search.** `/media/<key>` matched
`CAST(payload_json AS TEXT) LIKE '%key%'`. The API deliberately preserves unknown
JSON fields, so anyone who learned a private object's key could paste it into a
field of their OWN public post and be handed a "reference" to it. It was also an
unindexed full scan of every payload on every blob request — reintroducing the
hot table-wide read that externalising media was meant to remove — and it was
capped at 25 rows with no ORDER BY, so a widely-referenced object could 404 for
a genuinely authorised reader.

Replaced with an exact association table, `skribl_post_media(post_id, media_key)`,
written in the same transaction as the post and queried by indexed equality.
`verify_storage.py` now proves the forgery: a post that names another post's key
in an arbitrary field is accepted (unknown fields are still preserved) and gains
**zero** association rows.

**Local media writes raced.** Every writer used the same `<key>.part` temp name,
so concurrent posts of the same object renamed it out from under each other —
17 failures in 20 simultaneous writes, measured by the reviewer. Now
`<key>.<pid>.<uuid>.part`. Content addressing meant the bytes were identical, so
the race was pure collateral damage: a 500 for a request that had done nothing
wrong.

**The process-global session is fixed, not just documented.** The factory now
lives in `app.extensions["skribl"]`, so each application resolves its own; the
module global remains only as a fallback outside an application context.
Previously, creating app B redirected app A's routes at B's database.

**Stale comments corrected.** `__init__.py` still said `current_user_id` defaults
to 1 and `routes.py` still said standalone behaviour was unchanged. Both describe
the anonymous default now.

### Provenance

The recorded tree hash did not match the shipped tree in the last two archives.
The reviewer diagnosed it exactly: the source was tested, then
`docs/REFACTOR-v132.md` — this file — was edited before packaging. Less alarming
than a post-test code edit, but the claim was still false.

The generated documents were already excluded from the hash. This one is not
generated, it is written by hand, and writing it is always the last thing that
happens. So the fix is procedural rather than technical: **all documentation is
finished BEFORE the final harness run, and the archive is built from that run.**

### Version

`SKRIBL_VERSION` is now **v135**, and the archive is named from the constant.
Previous deliveries were labelled v132/v133/v134 in filenames while the code
inside still declared v131 — the same drift as the archive named v137 containing
v131, and as the editor version that drifted nine releases. The name is derived
from the constant now, not typed alongside it.

## v135.1 — fourth external review

**Upgrading would have 404'd every existing external media object.** The v135
migration created `skribl_post_media` but never populated it, while
`SKRIBL_MEDIA_BACKEND=local` has been supported since v132. A live database can
therefore hold posts referencing `/media/<key>` objects with zero association
rows — and v135 treats an object with no rows as orphaned. The migration now
walks existing payloads, extracts the exact keys and backfills them.
`verify_migrations.py` missed this because its legacy fixture used
`payload_json='{}'`: it proved a populated table upgrades, never a populated
table holding MEDIA. It now seeds a real pre-v135 local-media post.

**Two MIME spellings of identical bytes produced a misleading 503.**
`externalise_payload()` deduplicated by the original DATA-URL STRING, so
`audio/wav` and `audio/x-wav` — both accepted by validation — mapped to one
content key recorded twice against a unique index. The resulting IntegrityError
was mistaken for a public_id collision, retried five times, and surfaced as
"Could not allocate a unique id" for a post whose id was never the problem.
Deduplication is now by content key, returned as a set.

**Storage returns the key, instead of it being parsed back out of a URL.**
`put_data_url()` knew the key and threw it away; `externalise_payload()` then
recovered it with `url.rsplit("/", 1)[-1]`. That works for `/media/<key>.wav` and
fails for a presigned S3 URL, where the "key" swallows the whole query string —
a 149-character association for a 68-character object, too long for `String(80)`
on PostgreSQL and not equal to the key it authorises. An authorisation
identifier must never be derived from its presentation URL.

**The media authorisation query no longer materialises whole posts.** It selected
the mapped entity with `.all()`, so a single GET of a popular object could pull
ten thousand full `payload_json` values into Python to read two columns — the
exact bulk read that externalising media exists to prevent. It now selects only
`(visibility, user_id)`, stops at the first readable row, and decides caching
with an `EXISTS`. (The earlier `.limit(25)` avoided the load but was wrong: an
authorised reference could fall outside an arbitrary, unordered 25.)

**Documentation drift the checker was not catching.** README said "Current
version v118" against code at v135, pointed at `app.py` for a constant that
lives in `skribl/core.py`, and claimed SHA256SUMS "covers all 50 files" when it
covers 82. `skribl/__init__.py` said two model tables when there are three, and
`verify_privacy.py` still described the process-global session bug that v135
fixed. All corrected — and `verify_docs.py` now asserts each of those classes:
stated version against the constant, file-count claims against the manifest, the
documented location of SKRIBL_VERSION, and the model-table count.

**On the archive name.** The previous note said the filename deliberately carries
no version, then the delivery was named `skribl-v135.zip`. Both cannot be true.
The name is DERIVED from the constant now, and `verify_docs.py` fails if the
README's stated version disagrees with it. A version in the name is fine; a
version in the name that nothing checks is not.

## v137 — fifth external review

**Editing a released migration meant the fix never ran where it was needed.**
The v135 backfill was added by modifying revision `86171614cb85` IN PLACE. A
database that actually ran v135 is stamped at that revision, so `alembic upgrade
head` sees itself as current and skips the added code entirely — the fix
executed only on databases that never had the problem. `86171614cb85` is
restored to as-released, and the backfill is a new revision, `e4b7c9a15d2f`.
`verify_migrations.py` previously started at the PRE-v135 revision, proving
v132→v136 and saying nothing about v135→v136; it now migrates to the released
v135 revision, seeds it, and upgrades from there.

**The backfill recreated the very forgery v135 removed.** It scanned
`CAST(payload_json AS TEXT)` for anything matching `/media/<64 hex>.<ext>`. The
API preserves unknown fields, so a legacy payload holding
`{"notes": "see /media/<someone-elses-key>.wav"}` would have been promoted into a
real authorisation row. The backfill now parses the JSON and walks only the
actual media slots — thumbnail, music.data, photo.data, and the same inside each
frame — with an ANCHORED pattern, so the whole value must BE the URL. Pinned by a
regression that seeds a forger post and asserts it gains nothing.

**CI's "full harness" ran zero tests and reported PASS.** Both jobs invoked
`./harness/run_harness.sh` with no arguments; the suite loop ran zero times and
the script printed "PASS — every requested suite exited 0" and exited 0, because
every one of the zero requested suites did pass. Confirmed by running it. A bare
invocation now defaults to `verify_*.py`, and an empty list is a hard error.
`verify_docs.py` asserts both.

**The row cap was wrong twice in the same way.** `.limit(25)` on whole posts
became `.limit(1000)` on two columns — still arbitrary, still unordered, so a
private reference beyond the cap 404s for its own owner. Authorisation is now a
single `EXISTS`, with a second independent `EXISTS` for the cache policy. Nothing
is materialised, so the cost is constant regardless of fan-out. A cap is not a
fix for unbounded fan-out; not materialising the fan-out is.

**PostgreSQL migration check now uses an empty database.** `run_harness.sh`
resets the supplied database with `metadata.create_all()`, leaving the tables
present with no `alembic_version` row, so the baseline revision would then try to
create tables that already existed.

**Doc drift:** `models.py` said two tables (there are three), and
`docs/INTEGRATION.md` still described `create_blueprint(db, login_manager=...)`,
a signature planned before the blueprint existed and bearing no resemblance to
the real contract. Both corrected.

## v138 — sixth external review

**Prefixed deployments were still missed by the backfill.** The URL pattern
required `/media/<key>` at the START of the path, but the local store builds URLs
with `url_for("skribl.media")`, so a blueprint mounted at `/skribl` stores
`/skribl/media/<key>`. Mounting under a prefix is part of the integration
contract, so a v132-v134 deployment running local media behind a prefix would
have upgraded and still had zero association rows — its own media still 404ing.
The pattern now accepts any mount prefix while staying anchored at both ends with
the key validated, so prose containing a key is still not a reference.

**The backfill trusted a media slot the application never had.** It walked
`frames[i].thumbnail`. The runtime walker has no such slot — `captureCurrentFrame()`
never writes one and the share thumbnail is added once at the top level — and
because POST preserves unknown fields, an attacker could have persisted
`{"frames": [{"thumbnail": "/media/<victim-key>"}]}` in a public post. The
backfill would then have promoted that invented field into a real authorisation
row: the same forgery, one slot narrower. Removed.

The lesson is the same one twice: a migration that reconstructs authorisation
must mirror the walker that ACTUALLY RAN in the versions being migrated, not a
plausible schema. Both forgeries are now seeded and asserted against in
`verify_migrations.py`.

**"PASS WITH SKIPS" was published as "all green."** The runner distinguishes the
two; the stanza generator decided on failures alone, so a skipped suite produced
a headline claiming green followed, a few lines later, by a note that a skip is
not evidence of coverage — two contradictory claims in one generated block. It
now reports three states. This matters more than it looks now that a bare run
expands to every suite: a SQLite run ordinarily skips the PostgreSQL suite and a
Chromium without an H.264 encoder skips the MP4 suite, so PASS WITH SKIPS is the
NORMAL outcome, not an edge case.

## v139 — seventh external review

**I made the same mistake twice.** v138 fixed the v137 migration by editing
`e4b7c9a15d2f` IN PLACE — one round after documenting, in this very file, that
the v135 backfill had been broken by editing `86171614cb85` in place, and writing
"NEVER edit a distributed migration; add a revision." A database already stamped
at `e4b7c9a15d2f` sees current == head and runs nothing, so both v138 corrections
reached only databases that never had the problem.

`e4b7c9a15d2f` is restored byte-for-byte to its released contents, and the
corrections are a new revision, `b21f7ae0c93d`, which does two things:

* **ADDS** the associations the released migration missed — its pattern required
  `/media/<key>` at the start of the path, so every deployment mounted under a
  url_prefix stored `/skribl/media/<key>` and was skipped entirely.
* **REMOVES** the associations it invented. Its walker included
  `frames[i].thumbnail`, a slot the application has never had, so a public post
  carrying `{"frames": [{"thumbnail": "/media/<victim-key>"}]}` was promoted into
  a real authorisation row. Correcting the code does not delete rows the old code
  already wrote. The deletion is conservative: a pair is removed only when the
  key appears in the invalid slot AND in none of that post's legitimate slots.

**Two guards, because being told twice is enough.**

`skribl/migrations/RELEASED.txt` freezes the SHA-256 of every released revision,
and `verify_migrations.py` fails if any digest changes or if a revision on disk
is unlisted. Editing a released migration is now a test failure rather than a
silent no-op discovered by a reviewer.

And the suite now builds a database at the EXACT released v137 head — running the
original `e4b7c9a15d2f` — then upgrades. It asserts that a new revision actually
runs, that the prefixed deployment's media is adopted, that the false
per-frame-thumbnail row is removed, and that the genuine association survives.
The previous test started at v135 and ran to head, which proves v135→current and
is blind to v137→v138, where "edited in place" shows up as zero revisions run.

## v140 — eighth external review

**The v139 repair could delete a VALID association.** It decided whether an
existing row was legitimate by reverse-parsing the stored URL, so any
presentation form its pattern did not recognise computed as "not a legitimate
reference" and the row was removed. Both cases reproduce:

    {"music": {"data": "https://bucket/objects/<key>?X-Amz-Signature=..."},
     "thumbnail": "/media/<key>"}          -> legitimate={}, DELETED
    {"music": {"data": "/tenant+blue/media/<key>"}, ...}   -> DELETED

With the local backend that turns working media into a 404. This is the third
time the same principle has been violated in this project, and `storage.py`
already carries it in a docstring: an authorisation identifier must never be
reconstructed from its presentation URL — `put_data_url()` returns the key
precisely so nothing has to parse one back out. The cleanup parsed one anyway.

`b21f7ae0c93d` shipped in v139 and is released, so it was NOT edited. A new
revision, `f0a3d81b47e2`, restores what it deleted: any association implied by a
post's REAL media slots, using containment rather than a URL parser. Containment
is right here in a way it was NOT for granting authorisation at request time —
it only ever re-adds a row for a key already stored under a slot that post owns,
and erring toward preserving is correct when the alternative is 404ing live
media. A key appearing ONLY in the invalid frames[i].thumbnail slot has no
legitimate slot containing it, so the forgery is not resurrected.

The first draft of this revision restored nothing: it took its candidate keys
from DISTINCT media_key in the association table, which cannot work when the
rows being restored had already been deleted and their keys were no longer
known to it. Keys are extracted from the slot values themselves now.

**The repair is batched.** `b21f7ae0c93d` loaded the entire association table
into a Python set and accumulated every change in memory before writing —
hundreds of megabytes on exactly the long-lived installations this chain exists
to repair. `f0a3d81b47e2` streams posts 500 at a time, queries associations for
that batch only, and writes as it goes.

**RELEASED.txt now covers six revisions**, and the immutability guard passed on
this change — the released files were untouched, which is what it is for.

## v141 — ninth external review

**Batch size reduced from 500 to 25, and v140 recalled.** Each row carries
`CAST(payload_json AS TEXT)`, and the application accepts payloads up to
MAX_CONTENT_LENGTH (25 MB default) — so a 500-row batch materialises up to
12.5 GB at once, and 500 MB-1 GB at a realistic average. The previous revision's
fault was unbounded memory; a 500-row batch is the same fault with a ceiling
nobody would want to reach.

This required EDITING a released revision, which is otherwise forbidden here
after getting it wrong twice. The justification is narrow and testable: the rule
protects OUTCOMES, and batch size cannot change which rows result, only how much
is held while producing them. That is now proved rather than asserted —
`verify_migrations.py` runs the repair at batch sizes 1, 7 and 50 against the
same fixture and asserts identical associations. v140 was recalled before any
deployment ran it, and RELEASED.txt records the one digest change and why.

**Opaque custom-store URLs remain unrecoverable, and that is now documented.**
The repair reads the key out of the stored URL, which works for the local backend
(always `/media/<key>`) and S3-style URLs carrying the key in the path, but not
for `https://cdn.example/download?id=token`. No later revision can derive a key
that appears nowhere.

The severity is lower than it first appears, and the reason is worth stating:
`/media/<key>` refuses unless the store is a `LocalDiskStore`, so associations
gate NOTHING for a custom or S3 backend — those URLs are served by the bucket or
CDN and never reach Skribl. A lost row there is a data-integrity blemish, not a
media outage. For the one backend where associations DO gate access, the key is
always in the URL and reconstruction is complete. Documented in ARCHIVE-README
with the operator remedy: restore from a pre-v139 backup.
