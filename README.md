# Skribl Live Demo

Server-backed Flask app for **Skribl Pad** (record-and-replay drawing) and
**Skribl Flip** (frame-by-frame animation), plus a public player for sharing.

Current version: **v306** (`SKRIBL_VERSION` in `skribl/core.py`; the archive filename is derived from it)

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
2. **`docs/HANDOFF.md`** — reverse-chronological, one section per version,
   covering what changed, why, and what was *deliberately not* done. It also
   records retracted claims, so read a section fully before trusting an older
   one.
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
  security.py              CSP, CSRF double-submit, security headers
  storage.py               Media stores: inline, local disk, S3
  ratelimit.py             Per-IP quota (memory or shared DB backend)
  core.py                  SKRIBL_VERSION and shared constants
  templates/skribl/        Jinja templates + shared _skribl_*.html partials
  static/
    app.js                 Pad + player (largest file)
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
| `GET /api/skribls` | Feed-shaped listing: metadata only, cursor-paginated. |
| `POST /api/skribls` | Create a post. |
| `DELETE /api/skribls/<id>` | Take a post down — by its author, or with the revocation key issued at post time. |
| `GET /api/skribls/<id>` | Fetch one post as JSON. |
| `PATCH /api/skribls/<id>` | Revoke, or re-publish. |
| `POST /api/skribls/<id>/report` | Report a post: one reason from a closed set, into the operator's queue. |
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
<!-- /GEN:ROUTES -->

Generated by `harness/gen_docs.py` from `skribl/routes.py` — each purpose is
the handler's own docstring, so a renamed or removed route rewrites its row.

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
**mute** (page-wide, session-remembered, off by default) and **loop** (per post,
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
Delete, Copy key. "Your Skribls" in both editors' menus opens it. Whose it is
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
flask --app app.py init-db
flask --app app.py run
```

Then open <http://127.0.0.1:5000/> or <http://127.0.0.1:5000/flip>.

## Running the tests

<!-- HARNESS-COUNTS -->
**PASS WITH SKIPS — 5786 assertions across 102 reporting suites (104 on disk, 2 skipped), none failing** on sqlite as of v306 (tree `9593b8c73721`).

These totals are generated by `harness/stamp_docs.py` from `harness/LAST-RUN.txt` — never typed. `verify_docs.py` fails if any doc disagrees with the recorded run.

Skipped in that run: verify_mp4.py, verify_postgres.py. A skipped suite contributes zero assertions and is not evidence of coverage.
<!-- /HARNESS-COUNTS -->
verify_postgres.py needs a live PostgreSQL. The suites drive a real headless
Chromium against a real server — several verify exported files at the byte level
(GIF dimensions, frame counts, per-frame delays) rather than checking UI state.

```bash
pip install playwright flask_sqlalchemy
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

## Deploy

```bash
gunicorn app:app
```

Templates and `app.py` must deploy together — the CSP nonce lives in both, and a
header without the matching `nonce` attribute blocks the inline config script.
Static files carry `?v=` cache-busts that are bumped only when that file changes.
