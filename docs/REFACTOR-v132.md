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
