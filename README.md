# Skribl Live Demo

Server-backed Flask app for **Skribl Pad** (record-and-replay drawing) and
**Skribl Flip** (frame-by-frame animation), plus a public player for sharing.
🩸 Built with help from a friend, Cal.

Current version: **v321** (`SKRIBL_VERSION` in `skribl/core.py`; the archive filename is derived from it)

## Dropping Skribl into your own Flask app — start here

**There is a worked one you can run:** `python examples/host_app/app.py`, then
<http://127.0.0.1:5055/>. It is a separate Flask site with its own users and
posts that mounts Skribl under `/skribl`, composes with a server-side form, and
plays the result inline. `harness/verify_example.py` drives it in a browser, so
it cannot quietly stop working. See `examples/README.md`.

**[`docs/INTEGRATION.md`](docs/INTEGRATION.md)** is the guide. It opens with a
complete working example — about ten lines — and every claim in it is exercised
by `harness/verify_integration.py`, which mounts Skribl into a throwaway host
application and checks the contract from the outside. Run it in seconds, no
browser required:

```bash
python3 harness/verify_integration.py
```

Skribl is a blueprint. It takes a database session and, optionally, a callable
that identifies the current user; it does not own your app, models,
authentication or templates. The three things that catch people out — attaching
Skribl's tables to your metadata, passing a `url_prefix`, and the `index_route`
default — are called out near the top of that guide.

## Verifying this archive

```bash
sha256sum -c SHA256SUMS      # every file in the archive, run from this directory
```

`SHA256SUMS` covers every file in the archive and excludes itself. It does **not** cover the ZIP
container — the archive's external SHA-256 travels with the delivery, because a
file cannot contain its own digest.

`harness/LAST-RUN.txt` records the harness invocation in full: context header
(timestamp, versions, database reset, command) and the machine-generated
aggregate. Every hash in that file is a **source-tree** hash and is labelled
with the build it belongs to — none of them is an archive hash.

## Reviewing this project — start here

1. **`START-HERE.md`** — the working brief: architecture, invariants, and the
   known-open list.
2. **`DECISIONS.md`** — why the tree is the way it is, one entry per change,
   newest at the bottom (its version log explains the repeated numbers).
   `docs/HANDOFF.md` is the v100–v131 archive and stops there by design.
3. **`docs/INTEGRATION.md`** — how this gets embedded into a larger Flask app.
   Rewritten and verified; see the section at the top of this file.
4. **`harness/README.md`** — the test suites and how to run them.
5. **`DECISIONS.md`** — the decisions that are the owner's to confirm, and the
   reasoning record behind the current shape.

A note on the docs: prose claims have gone stale before and `harness/verify_docs.py`
now exists to catch the classes that did. **When a doc and the code disagree,
trust the code and fix the doc.**

That warning is deliberately scoped to the narrative docs. `harness/RELEASE.md`
and `SHA256SUMS` are generated, and `docs/INTEGRATION.md` is pinned by
`verify_integration.py` — when prose and those disagree, the generated artefact
and the suite are right.

## Layout

```
app.py                     Host app: Flask, DB, secret key; registers the blueprint
skribl/                    The blueprint package — everything Skribl owns
  routes.py                HTTP routes (API + pages)
  models.py                SQLAlchemy models; attach_to_metadata for a host
  validation.py            Payload + media validation and resource caps
  mediameta.py             What a post must not carry: photo location, tags, file names
  security.py              CSP, CSRF double-submit, security headers
  storage.py               Media stores: inline, local disk, S3
  mediareport.py           `python -m skribl.mediareport`: media bytes held, read-only
  ratelimit.py             Per-IP quota (memory or shared DB backend)
  core.py                  SKRIBL_VERSION and shared constants
  templates/skribl/        Jinja templates + shared _skribl_*.html partials
  static/
    app.js                 Pad + player
    flip.js                Flip
    inlineplayer.js/.css   The in-post player — a Skribl inside a host's feed
    gallery.js             The public gallery page over the listing
    library.js             The profile's Skribls tab: the stage and whose list it is
    posted.css             The posted list's rules, loaded by the editors and the profile
    editor_compose.js      Compose mode: attach a Skribl to a host's draft post
    lib/sharecard.js       Where the drawing sits inside /s/<id>/card.png
    lib/postedcard.js      Compositing that card — editors only
    styles.css, flip.css   Pad/shared styles, Flip styles
    lib/                   Modules shared across surfaces (audioloop, holdtiming, …)
    gifenc.min.js          Vendored GIF encoder (build command in its banner)
    mp4-muxer.min.js       Vendored MP4 muxer
docs/                      Handoff, integration guide, refactor notes
harness/                   Browser test suites (Playwright) + release tooling
```

## Routes

<!-- GEN:ROUTES -->
| route | purpose |
|---|---|
| `/` | Standalone-site root, registered only when index_route=True. |
| `GET /api/drafts` | The signed-in author's saved drafts: a list, no payloads. |
| `POST /api/drafts` | Save a draft to the signed-in author's account. |
| `DELETE /api/drafts/<draft_id>` | Delete one of your saved drafts. |
| `GET /api/drafts/<draft_id>` | Open one of your saved drafts, with its payload. |
| `PUT /api/drafts/<draft_id>` | Overwrite one of your saved drafts; 409 with conflict:true if it changed since `baseUpdatedAt`. |
| `GET /api/skribls` | Feed-shaped listing: metadata only, cursor-paginated. |
| `POST /api/skribls` | Create a post. |
| `DELETE /api/skribls/<id>` | Take a post down — by its author, or with the revocation key issued at post time. |
| `GET /api/skribls/<id>` | Fetch one post as JSON. |
| `PATCH /api/skribls/<id>` | Revoke, or re-publish. |
| `POST /api/skribls/<id>/report` | Report a post: one reason from a closed set, into the operator's queue. |
| `GET /api/skribls/meta` | Metadata for ids the caller already holds. |
| `/build.json` | The build the server is serving now (skribl.build_id), for the Home Screen app's "new version" check. |
| `/feed` | The demo host page: the in-post player and composer over the real listing. |
| `/flip` | Flip — the frame-by-frame animator. |
| `/gallery` | The public gallery: every Skribl its author chose to show, newest first. |
| `/library` | The profile's Skribls tab: what you posted, with a full transport that goes full screen. |
| `/manifest.webmanifest` | The web app manifest a Home Screen install reads: name, icons, colours and where it opens. |
| `GET /media/<key>` | Serve a content-addressed blob. |
| `/s/<id>` | The public player a shared link opens. |
| `/s/<id>/card.png` | The share-card image link unfurls use. |
| `/s/<id>/poster` | The idle poster the in-post player and the library tiles show: the drawing, or a blank canvas — never the branded card. |
| `/skribl-pad` | Pad — the record-and-replay editor. |
| `/sw.js` | The service worker that opens the editors with no signal (network first, always). |
<!-- /GEN:ROUTES -->

Generated by `harness/gen_docs.py` from `skribl/routes.py` — each purpose is
the handler's own docstring, so a renamed or removed route rewrites its row.

This demo app (`app.py`, not the blueprint) adds two more, and only when
`SKRIBL_DEMO_IDENTITY` and a `SKRIBL_DEMO_LOGIN_KEY` of 16+ characters are both
set: `/demo-login?key=<key>` signs the visiting browser in as that identity (a
signed session cookie), and `/demo-logout` signs it out. Everybody else stays
anonymous; see `.env.example`.

## The in-post player

A Skribl inside somebody else's post — the shape it takes in a feed, as opposed
to the full player a shared `/s/<id>` link opens. A host embeds it in two lines:

```jinja
{% from 'skribl/_skribl_inline_player.html'
     import skribl_inline_assets, skribl_inline %}
{{ skribl_inline_assets() }}          {# once per page #}
{{ skribl_inline(post.skribl_id) }}   {# once per post #}
```

Idle, a post is one cached image — the poster at `/s/<id>/poster`, the share
card's drawing without its brand strip — and a play button; nothing is fetched
until somebody taps. Playing, it redraws the drawing with a progress
hairline and a nib at the pen. There are two viewer controls and only two —
**mute** (page-wide, session-remembered; sound starts off, muted) and **loop** (per post,
on by default; turning it off stops the drawing at its last frame and stops the
music with it). One Skribl plays at a time, and scrolling one out of view
settles it.
`/feed` is that page, live, over whatever this deployment has posted publicly.

**Drawing one from a host's composer.** `?compose=1` opens the Pad as an
attachment editor: "Add to post" hands the payload back over `postMessage` and
publishes nothing, so re-editing is free and an abandoned draft leaves nothing
behind. The host posts once, when the author posts. `/feed` demonstrates the
whole flow — pad icon, overlay, attach, re-edit, post — and
`skribl/static/feed.js` is written to be read as the host-side recipe.

`harness/verify_inline.py` is the proof — including that the in-post player and
the sealed player, playing the same posted drawing from the same clock, are at
the same point and have drawn the same thing. The wet/dry compositor gap that
header used to describe is closed as of v279; the one after it — every
drawing that is not 16:9 shown stretched, because the canvas was sized in a way
that let the box clamp each axis on its own — as of v305; and the third — a
background photo hard-coded to `cover`, so a photo the author FITTED was
letterboxed in the editor and on `/s/<id>` and cropped in every feed box — as
of v306, by reading `lib/photofit.js` rather than writing a fourth copy of the
arithmetic.

and the fourth — a background photo's **opacity and blur**, which the editor
and `/s/<id>` apply as CSS on a real `<img>` and a feed box, having only a
canvas, applied not at all — as of v307. A photo composed at 40% painted
opaque in every feed and every host embed; one composed soft painted sharp.

There is no known rendering difference now, and that sentence has been wrong
here before: it was written while the opacity gap was open and stated in
`inlineplayer.js`'s own header three lines from the code. What makes it
checkable rather than hopeful is that each closure has a pin that goes red
without it — see `harness/verify_inline.py`, `skribl/static/inlineplayer.js`
for the measurements, and `docs/INTEGRATION.md` for the host-side details.

## The profile's Skribls tab, and the public gallery

`/library` is a page ABOUT the drawings rather than a feed of them: one stage
with a full transport — play, restart, scrub, loop, mute, full screen, copy
link — and beside it the list of what you posted, one row per Skribl with its
poster, a title search, a filter (all / in the gallery / link only) and the
actions: copy or share the link, switch the post in or out of the gallery,
Delete, Copy key. "Your Skribl Library" in both editors' menus opens it. Whose it is
depends on the deployment: with no accounts it is the list this browser kept
(`lib/posted.js`), unlisted posts included; with a host's signed-in user it is
`GET /api/skribls?user_id=<me>`. The stage is the same in-post player, driven
through the handle it exposes, so the profile cannot disagree with the feed or
the shared link about how a drawing replays, and it fetches ONE payload at a
time — the row's picture is the poster, and `GET /api/skribls` returns metadata
precisely so a listing never has to carry payloads.

`/gallery` is the public page: every Skribl whose author ticked "Show in the
public gallery" on the post sheet, on the in-post player, with New and Hot tabs
(Hot is plays in the last seven days), a title/caption search, and Report on
every tile. `harness/verify_library.py`, `verify_gallery.py`, `verify_hot.py`
and `verify_tilereport.py` are the proof.

## Local setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt          # dev
# reproducible/hash-checked install:
# pip install -r constraints.txt --require-hashes
python -m alembic upgrade head           # the schema, by migration
flask --app app.py run
```

Build the schema with `alembic upgrade head`, not `flask init-db`: `init-db` is
`create_all()`, which stamps no migration, so the first `upgrade head` after it
fails on tables that already exist.

Then open <http://127.0.0.1:5000/> or <http://127.0.0.1:5000/flip>.

## Running the tests

<!-- HARNESS-COUNTS -->
**PASS WITH SKIPS — 10572 assertions across 118 reporting suites (120 on disk, 2 skipped), none failing** on sqlite as of v321 (tree `23105ebb2dac`).

These totals are generated by `harness/stamp_docs.py` from `harness/LAST-RUN.txt` — never typed. `verify_docs.py` fails if any doc disagrees with the recorded run.

Skipped in that run: verify_mp4.py, verify_postgres.py. A skipped suite contributes zero assertions and is not evidence of coverage.
<!-- /HARNESS-COUNTS -->
verify_postgres.py needs a live PostgreSQL. The suites drive a real headless
Chromium against a real server — several verify exported files at the byte level
(GIF dimensions, frame counts, per-frame delays) rather than checking UI state.

```bash
pip install -r requirements.txt -r harness/requirements.txt   # the app, then the harness's own
python -m playwright install chromium
./harness/run_harness.sh verify_gifenc.py verify_canvas.py    # or any subset
```

`run_harness.sh` starts its own server on port 5001 and raises the post rate limit
so suites don't throttle each other. See `harness/README.md` for the full list and
the known gotchas.

Two things the sandbox **cannot** verify, so they need a real browser:

- **MP4 export.** Headless Chromium has `VideoEncoder` but no avc1, so the H.264
  path can't run here. The capability gate and the WebM fallback are covered,
  and the `mp4` CI job runs the suite on real Chrome and writes the attestation
  `harness/RELEASE.md` reports on its `mp4 (H.264)` line.
- **CSP in Safari and Firefox.** Verified in Chromium only. Deploy once with
  `SKRIBL_CSP=report-only` to check.

## Configuration

All optional in development, where safe defaults apply. **`SECRET_KEY` is required in production** — the app refuses to boot on an empty or placeholder value where it detects a real deployment. See `.env.example`.

| Variable | Default | Purpose |
| --- | --- | --- |
| `SECRET_KEY` | — | Flask secret — **required in production**, random per-process in dev |
| `DATABASE_URL` | sqlite | Postgres in production |
| `MAX_CONTENT_LENGTH` | 25000000 | Whole-request cap |
| `SKRIBL_CSP` | `on` | `on` / `report-only` / `off` |
| `SKRIBL_MAX_AUDIO_BYTES` | 12000000 | Per-item audio cap |
| `SKRIBL_MAX_IMAGE_BYTES` | 8000000 | Per-item image cap |
| `SKRIBL_RATE_MAX_POSTS` | 20 | Posts per IP per hour |
| `SKRIBL_MAX_DRAFTS` | 25 | Saved drafts one signed-in author keeps |
| `SKRIBL_MAX_DRAFT_BYTES` | 209715200 | All of one author's saved drafts together (200 MB) |

## Deploy

```bash
pip install -r constraints.txt --require-hashes
python -m alembic upgrade head && gunicorn app:app
```

Migrate, then serve, on every deploy: a schema change that never ran is how the
v269 outage happened. On Render both run from the dashboard's **Start
Command** (Render does not read the `Procfile`); START-HERE.md's "Running it"
has the details.

Templates and `app.py` must deploy together — the CSP nonce lives in both, and a
header without the matching `nonce` attribute blocks the inline config script.
Static files carry `?v=` cache-busts that are bumped only when that file changes.
