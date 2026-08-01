# Skribl -> Flask social-media site: integration & efficiency plan

Goal: drop Skribl (Pad + Flip + Player) into a larger Flask app cleanly, with the
duplicated markup pulled into shared components. Sequenced so each step is small,
testable, and reversible (the same way the shared help partial was done).

## 1. Package as a Flask **Blueprint**
Today `app.py` builds the whole app. Repackage Skribl as a self-contained blueprint
the host app registers:

```
skribl/
  __init__.py            # create_blueprint() -> Blueprint("skribl", ..., url_prefix="/skribl")
  routes.py              # the 7 routes, current-user aware
  models.py              # SkriblPost (host app owns db = SQLAlchemy())
  api.py                 # POST /api/skribls, GET /api/skribls/<id>
  templates/skribl/      # editor, flip, player, and _partials/*
  static/skribl/         # app.js, styles.css, vendor/*
```

- Namespace templates under `templates/skribl/` and static under `static/skribl/`
  so nothing collides with the host app.
- `create_blueprint(db, login_manager=None, config=None)` so the host injects its
  own DB session, auth, and settings instead of Skribl owning a global app.
- Routes become `skribl.pad`, `skribl.flip`, `skribl.player`, etc.; use
  `url_for("skribl.player", public_id=...)`.

## 2. Componentize the templates (biggest DRY win) — DONE
All shared markup is now extracted into partials, each `{% include %}`d with a
`kind` var ('pad'|'flip') where the surfaces differ. Extractions are
behavior-preserving (verified by golden token-diff vs pre-extraction markup):

```
templates/                         # flat layout today (see note); files are:
  _skribl_help.html            [x] "How it works"              (Pad + Flip)
  _skribl_export.html          [x] PNG/Video/GIF + bg toggle   (Pad + Flip)
  _skribl_draw_drawer.html     [x] color/brush/bg/smoothing/opacity/grid/draw-on/clear
  _skribl_music_drawer.html    [x] waveform trim + fine-tune loop
  _skribl_image_drawer.html    [x] fit/reposition/zoom/opacity/blur/reset
  _skribl_zoom_hud.html        [x] magnify pill (identical both apps, no kind branch)
  _skribl_player_controls.html [x] player shell (Pad editor + Player)
```

Note: partials live **flat in `templates/`** (matching how `_skribl_help.html` was
done), not the `templates/skribl/_partials/` shown in §1 — that namespacing lands
with the blueprint (§1). Each extraction was verified with the Jinja-render +
dup-id + div-balance harness plus a byte-for-byte golden diff of the rendered panel
on each surface, so every id `app.js`/Flip's JS binds to is unchanged.

## 3. Split Flip's inline JS/CSS
Flip *was* one 148 KB self-contained file (great for standalone, wrong for a shared
codebase).

### 3a. Inline `<style>`/`<script>` split — DONE (v98)
- Inline `<style>` -> `static/skribl/flip.css` (307 lines, braces 191/191).
- Inline `<script>` -> `static/skribl/flip.js` (1469 lines, `node --check` clean).
- `skribl_flip.html` now `{{ url_for('static', filename='skribl/flip.css') }}` +
  `<script src=".../flip.js"></script>` in the SAME positions (classic script at
  end of `<body>`, no `defer`/`type=module`, so DOM-ready + lazy `window.gifenc`
  ordering is byte-for-byte preserved). The CDN module-loader (`window.gifenc` /
  `window.Mp4Muxer`) stays inline — it's step 4's (vendoring) target.
- Behavior-preserving proof: both extracted files are **byte-identical** to the
  original inline blocks (golden diff vs the pre-split zip); render harness stays
  green (Flip divs 238/238 balanced — down from 241 only because three `<div>`
  substrings that lived inside `innerHTML` JS strings moved out of the template text
  into `flip.js`; the runtime DOM is unchanged). Template shrank 1920 -> 142 lines.

### 3b. Shared JS libs with `app.js` — RECONCILIATION, not a de-dupe (was mis-scoped)
INTENDED: extract the Web Audio loop engine, zoom controller, stroke rendering, and
export code to `static/skribl/lib/` (`audioloop.js`, `zoom.js`, `strokes.js`,
`export.js`) and import from both. Still the single biggest maintenance win.

REALITY (measured v98 — diffed the actual implementations, don't trust "duplicated"):
- **audioloop** (`buildLoopChannels` + `buildLoopAudioBuffer`): **DONE (v99).**
  **Extended v102** with `audioBufferToWavDataURL`, `encodeWavFromChannels` and
  `buildTrimmedLoopWav`, so loop *cropping* is shared too, not just the crossfade
  DSP. The encoders are byte-identical to app.js's originals; the state-object
  contract matches `buildLoopAudioBuffer`. app.js -84 lines / +3 shims. This is
  what let Flip stop posting whole uncut files.
  Extracted to `static/skribl/lib/audioloop.js` (`window.SkriblAudioLoop`); app.js +
  flip.js each keep a 1-line shim passing their own audio globals
  (`currentAudioBuffer/audioCtx/trimStart/trimEnd/loopCrossfadeMs`). Proven
  behavior-preserving headless (lib body byte-identical to originals; golden diff
  shows the only change in each file is those two defs -> shims; `node --check` +
  harness green). NOTE `startWebAudioLoop`/`stopWebAudioLoop` were left per-file:
  identical text but they mutate `_waLoopSource`/`_waLoopStartCtx`/`_waLoopDuration`
  state, so sharing them needs a stateful lib object, not a pure extraction.
  Still needs a browser audio smoke test on Pad + Flip + Player.
- **zoom** (`initCanvasZoom`/`ZoomView`): **divergent** — `app.js` 288 lines
  (6280-6567) vs `flip.js` 75 lines (380-454). Not a de-dupe; needs a designed
  common API + per-surface behavior reconciliation.
- **strokes** (`app.js paintStrokesStatic(strokeArr)` vs `flip.js paintStatic(c,
  strokeArr)`): **divergent signatures** (implicit module `ctx` vs passed-in `c`).
  Reconcile to one signature.
- **export** (`app.js` `exportGif` inside an `initExport()` IIFE + `exportViaWebCodecsMp4`
  vs `flip.js` standalone `exportGIF`/`exportWebM`/`exportPNG`): **divergent
  structure and names**. The two `exportGIF` copies are at transparent-GIF *feature*
  parity, but the surrounding encoder/progress/IIFE plumbing differs, so this is a
  reconciliation, not a straight merge. Converge last.

VERIFICATION GAP — CLOSED (v101). The sandbox DOES have Flask (+ `flask_sqlalchemy`
from PyPI) and a headless Chromium via Playwright. `harness/` runs the app on SQLite
and drives all three surfaces, so runtime equivalence CAN now be checked here:
- `verify_audio.py`  post -> `/s/<id>` with sound + numeric crossfade seam check
- `verify_lib.py`    audioloop shared on every surface + load-order negative test
- `verify_fix.py`    autosave quota fallback + regressions
- `verify_amber.py`  amber media state + re-add cards
- `verify_dots.py`   amber toolbar dots and card colours
- `verify_loopcap.py` (v102) 20s loop cap + cropped post payload
- `verify_race.py`    (v102) Pad pre-decode autosave race
95 assertions total. NOTE: the server and the tests must run in ONE shell
invocation — background processes don't survive between tool calls in a sandbox.
The audioloop extraction is now runtime-verified end to end. The remaining 3b work
(zoom / strokes / export / `startWebAudioLoop` state) can be done against this
harness with real before/after canvas and audio assertions rather than `node --check`
alone. `app.js` is no longer pristine (amber state, 12 lines) but the player flip
branch is untouched.

## 4. Vendor the CDN modules — DONE (v103 mp4-muxer, v104 gifenc)
Both live flat in `static/skribl/` (not the `vendor/` subdir sketched above —
matching where `mp4-muxer.min.js` already was), loaded as classic `<script src>`
on Pad and Flip:
- `mp4-muxer.min.js` -> `window.Mp4Muxer` (v103; the Pad already had it, Flip was
  on CDN 5.1.5 against the Pad's 5.2.2).
- `gifenc.min.js` -> `window.gifenc` (v104). Upstream is ESM+CJS only, so this is
  a global-publishing IIFE built from the published tarball's own `src/` with
  esbuild; the reproduce command (tarball sha256, esbuild version, flags) is a
  banner comment in the file.

Payoff, all asserted in `verify_gifenc.py` / `verify_muxer.py`: no third-party
runtime dependency, works offline, **zero off-origin requests on any surface**,
and both surfaces provably run one version of each library. It also made GIF
export testable in-sandbox for the first time — see §"harness" below.

Remaining for CSP (§7): vendoring removed the third-party *origin*, but inline
`<script>` blocks (the `SKRIBL_MODE` config, Jinja-injected data) are still there,
so a strict policy needs nonces or hashes.

## 5. Data, media & scale
- **Move blobs out of the DB.** Audio/image are base64 data URLs inside
  `payload_json` today — rows get multi-MB. Store media in object storage (S3/GCS),
  keep only URLs in the payload. Add a size cap per Skribl.
- Keep `normalizeSkribl()` as the single read path (it already unifies legacy +
  frame formats and surfaces frame-0 media).
- Add `created_at`, `user_id` (real), `visibility`, and indexes for feeds.

## 6. Auth & social hooks
- Replace `user_id=1` with the host's current user on post.
- Add ownership + delete/edit endpoints; add report/moderation.
- Feed/profile: query `SkriblPost` by user; the player already embeds cleanly
  (no `X-Frame-Options`/CSP frame-ancestors set, by design) for feed cards.
- Share cards (`/s/<id>/card.png`) already give OG unfurls for social posts.

## 7. Security to revisit at launch
- [x] **CSP — DONE (v105).** Nonce-based `script-src 'self' 'nonce-…'`, no
  `unsafe-inline`, no `unsafe-eval`. The two inline config blocks carry a
  per-request nonce from `flask.g`. `style-src` keeps `'unsafe-inline'` because 51
  `style="..."` attributes cannot be nonced; `connect-src` must include `data:`
  because `app.js` fetches data URLs for audio. **No `frame-ancestors`** — the
  player is iframe-embedded by design. Toggle with `SKRIBL_CSP=report-only|off`.
  See `verify_csp.py`.
- [x] **Validate/limit uploaded media server-side — DONE (v105)** for *type and
  bytes*: allow-list of `audio/*` / `image/*` with SVG excluded, base64 validated,
  per-item caps (12 MB audio / 8 MB image / 2 MB thumbnail, env-tunable), walked
  across top-level, per-frame and thumbnail slots. **Dimensions and duration are
  still not checked** — they need real decoding and a dependency the app lacks.
  See `verify_media.py`.
- [~] Rate limiting: v117 added a database-backed backend
  (`SKRIBL_RATE_BACKEND=db`) that is shared across workers and survives restarts,
  using the existing DB rather than new infrastructure. **Default is still
  `memory` (per-process)** — set it on the deploy. Redis or edge limiting remains
  preferable at scale. Covered by `verify_review.py` for both backends.

## Suggested sequence
1. Blueprint wrapper (no behavior change) + template/static namespacing.
2. [DONE] Export sheet + all drawers + zoom HUD + player shell extracted as partials.
3. [PARTIAL] 3a Split Flip inline JS/CSS out — DONE (flip.css/flip.js, verified).
   3b Shared JS libs — audioloop DONE (lib/audioloop.js, both files shimmed),
   extended v102 with the WAV encoders + buildTrimmedLoopWav;
   zoom/strokes/export + startWebAudioLoop REMAIN and need browser QA (they mutate
   per-file module state — reconciliation, not de-dupe). See §3.
4. [DONE] Vendor CDN modules (v103 + v104); CSP added (v105) — see §7.
5. Media -> object storage; real auth + moderation; feed queries.

Each of 1-4 is internal refactor with a green-to-green check (render + harness).
Step 5 is the actual "social site" surface area and depends on the host app.
