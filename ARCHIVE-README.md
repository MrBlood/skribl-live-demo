# What this archive is

**Source version: `SKRIBL_VERSION = "v141"` (skribl/core.py).**

Read that line first. This archive's contents are built on the **v131** client
code — `app.js`, `flip.js`, `styles.css` and `flip.css` are v131's, with six
small enumerated edits listed below. If you have a later line of work (a v13x
with newer editor/Flip/CSS changes), **this archive does not contain it**, and
merging means bringing those four files here rather than the reverse.

The filename is DERIVED from `SKRIBL_VERSION`, not typed alongside it. Earlier
deliveries were named for a version the code inside did not declare — v132/v133/
v134 archives containing v131, and an archive named v137 containing v131 — which
is the same class of error as the editor's hardcoded version drifting nine
releases, the README claiming v118 while the code said v131, and SHA256SUMS
claiming 50 files while covering 82. A version in the name is fine; a version in
the name that nothing checks is not. `verify_docs.py` now fails if the README's
stated version disagrees with the constant.

## What changed here, versus v131

**The server was repackaged as a Flask blueprint.** `app.py` went from 1,202
lines to 116 and now does only host work. Everything else moved into `skribl/`:

    skribl/__init__.py    create_blueprint() / init_skribl() — the contract
    skribl/routes.py      the routes, incl. the feed and media endpoints
    skribl/models.py      plain SQLAlchemy, injected session, visibility column
    skribl/ratelimit.py   incl. the concurrency fix described below
    skribl/validation.py  moved verbatim from app.py
    skribl/security.py    CSP (blueprint-scoped) + embed origins + CSRF
    skribl/storage.py     media backends: inline (default) / local / S3 hook
    skribl/core.py        version, OG defaults, id validation, env parsing
    skribl/migrations/    Alembic, scoped to Skribl's tables only

**Behavioural changes:**

* Rate limiting no longer admits ZERO under concurrency. Reservation was
  INSERT → COMMIT → COUNT → withdraw; twelve simultaneous posts against a quota
  of two all committed before any count ran, so every request withdrew. SQLite
  hid this by serialising writes. Fixed with a per-identity advisory lock.
* `GET /api/skribls` — feed listing, keyset cursor, payloads excluded.
* `visibility` on posts: public / unlisted / private. **New posts default to
  `unlisted`, and the migration backfills existing posts as `unlisted`.** A
  client must ask for `public` explicitly to appear in a feed. See DECISIONS.
* CSRF seam, opt-in via `SKRIBL_CSRF_PROTECT=1`.
* Media can live outside the database. Default is still `inline` (v131
  behaviour); `SKRIBL_MEDIA_BACKEND=local` externalises it.

**Client edits — the only six.** Re-apply these if you merge newer client files:

    flip.js    window.SKRIBL_API_BASE instead of a hardcoded '/api/skribls'
    flip.js    window.SKRIBL_PLAYER_BASE instead of a hardcoded '/s/'
    flip.js    mediaToArrayBuffer() — handles data URLs AND external URLs
    app.js     skriblPostHeaders() — sends the CSRF header when present
    app.js     removed the '/api/skribls' literal fallback
    templates  skribl_asset() instead of url_for('skribl.static', …)

`harness/verify_seam.py` fails loudly if any of these is missed.

## Running it

    pip install -r constraints.txt --require-hashes   # the pinned lock
    python -m alembic upgrade head                    # NOT create_all(); it cannot ALTER
    gunicorn app:app                                  # or: flask --app app run

`pip install -r requirements.txt` also works and resolves fresh within the
version ranges. What does NOT work is `-r requirements.txt -c constraints.txt`:
the lock carries hashes, that puts pip in --require-hashes mode, and that mode
rejects ranges. The hashes are linux x86_64 / cp312 — regenerate the lock on your
real deployment target.

## Mounting it in a host application

    skribl.init_skribl(
        app,
        session=lambda: db.session,       # the host's session — one transaction
        url_prefix="/skribl",
        static_url_path="/static",
        current_user_id=lambda: current_user.id,
        csrf=your_csrf_triple,            # (prepare, issue, validate) — see below
    )

`csrf` is a THREE-element tuple `(prepare, issue, validate)`, not a pair:

    prepare()          before_request — resolve the token onto `g` so the
                       template can render it (after_request is too late)
    issue(response)    after_request  — set the cookie, return the response
    validate(request)  -> bool        — checked before any mutating handler

`skribl.security.double_submit_csrf()` returns exactly that triple and needs no
dependencies. Enable it with `SKRIBL_CSRF_PROTECT=1` standalone.

That is the whole contract. `harness/verify_prefix.py` proves it works mounted.

## The harness

`./harness/run_harness.sh $(cd harness && ls verify_*.py)` runs every suite;
all; it writes `harness/LAST-RUN.txt` itself now, and `harness/stamp_docs.py`
stamps the totals into the docs so they cannot drift by hand again.

Green on SQLite and PostgreSQL. `verify_mp4.py` SKIPS without a browser that has
an H.264 encoder — a skip contributes zero assertions and is not coverage.

## Known-open — media associations and opaque store URLs

`skribl_post_media` is reconstructed from payloads by the migration chain, and
reconstruction reads the storage key out of the stored URL. That works for the
LOCAL backend, whose URLs are built by `url_for("skribl.media", key=...)` and
therefore always contain the key, and for S3-style URLs that carry the key in the
object path.

It does NOT work for a custom store returning an OPAQUE url such as
`https://cdn.example/download?id=token`, where the key appears nowhere in the
URL. The v139 repair deleted such associations and no later revision can restore
them, because the mapping is gone.

The practical impact is smaller than it sounds, and worth being precise about:
`/media/<key>` refuses unless the store is a `LocalDiskStore`, so associations
gate NOTHING for a custom or S3 backend — those URLs are served by the bucket or
CDN and never routed through Skribl. A lost row for an opaque store is a
data-integrity blemish, not a media outage. For the one backend where
associations DO gate access, the key is always present in the URL and
reconstruction is complete.

If you run a custom store and want the rows back, restore them from a pre-v139
backup; nothing in the chain can derive them.

## Known-open

* `app.js` is still 6,596 lines and serves both the editor and the player. A
  split was attempted and REVERTED; see docs/REFACTOR-v132.md for why the
  regex-based call graph was the wrong tool and what to use instead.
* The S3 media backend is a subclass hook, not an implementation.
* Multi-take has no data model, by design — it is a product decision first.
