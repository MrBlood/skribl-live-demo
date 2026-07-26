# Skribl — Roadmap (Pad + Flip)

Status legend: [ ] todo  ·  [~] partial  ·  [x] done

## Shared / platform
- [x] One shared data model (frame-format); player handles replay + flip.
- [x] Shared "How it works" partial (`_skribl_help.html`).
- [x] App-wide scrollbar + button styling in `styles.css`.
- [x] **Componentize templates (INTEGRATION step 2).** Export sheet + Draw/Image/
      Music drawers + zoom HUD + player shell all extracted into shared partials,
      `{% include %}`d by Pad + Flip (+ Player for the shell). Behavior-preserving.
- [x] **Pad/Flip desktop consistency.** Flip control sizes match the Pad at
      >640px; drawer-open toggles share one translucent "lit" state across apps.
- [ ] **Auth**: `POST /api/skribls` stamps `user_id=1` (TODO in code). Wire real
      current-user once accounts exist.
- [ ] **DB durability**: posts are SQLAlchemy rows; confirm migrations + backups
      for production. Media are base64 data URLs inside `payload_json` — large.
      Consider object storage (S3/GCS) for audio/image blobs, store URLs instead.
- [ ] **Rate limiting** is a naive in-memory per-IP counter — replace with Redis
      or a real limiter for multi-process/serverless deploys. Note it is raised to
      100000 during harness runs (it was silently throttling the posting suites at
      20/hour), so no suite covers it.
- [~] **Abuse/moderation**: posts are public + unauthenticated. **Media is now
      validated server-side (v105)** — type allow-list (SVG excluded), base64
      checked, per-item byte caps beyond the whole-request `MAX_CONTENT_LENGTH`.
      Report/hide and content review hooks remain before a social launch.
- [x] **CSP (v105)** — nonce-based, enforced, no `unsafe-inline`/`unsafe-eval` in
      `script-src`. Deliberately no `frame-ancestors`, so the iframe embed keeps
      working. `SKRIBL_CSP=report-only|off` to stage or disable.

## Skribl Pad
- [x] Undo next to "Clear drawing" (snapshot restore).
- [ ] Make the ⋯ "Clear all" (resetAll, wipes media) undoable too, or add a
      confirm-with-preview.
- [ ] Redo for the clear-undo (currently one-shot restore).
- [ ] Multi-take editing UI polish (reorder/trim takes).
- [ ] Export parity with Flip (GIF/MP4 of the replay) — currently PNG + WebM.

## Flip
- [x] Full parity build (zoom, audio loop, scrub, GIF, MP4, draw-on, sharing, polish).
- [x] Draw-on + Grid relocated to the Draw drawer as labeled switches.
- [x] **Transparent GIF** — the export sheet's Background/Transparent toggle now
      works on Flip (strokes-only + `rgba4444`/`oneBitAlpha`/transparent index).
      **Verified for real in v104**: every frame carries the transparency flag and
      disposal 2, byte-parsed off an actual exported GIF.
- [x] Export sheet unified with the Pad; GIF card + bg toggle grouped into one tray.
- [x] **Player round-trip QA** — DONE (v101). Posted multi-frame Flips animate WITH
      SOUND at `/s/<id>`, verified live in headless Chromium: measured audio signal
      (peak 0.4256 off an AnalyserNode), gapless Web Audio path in use, and the
      crossfade seam checked numerically via OfflineAudioContext (zero-run 0
      samples, seam delta 1.32x the mid-loop control).
- [ ] Frame tools: duplicate/reorder pages (drag in the strip), copy/paste a page.
- [ ] Per-frame duration (hold frames) instead of a single global fps.
- [ ] Onion-skin depth (more than one frame back) + color-tinted onion.
- [ ] Export options UI: size/quality + frame range (transparent GIF now done).
- [ ] Bigger canvases / aspect-ratio choice (currently fixed 640x460).

## Audio payload bugs found during v101 QA — ALL FIXED (v102)
- [x] **Flip ignores its own 20s loop cap on load.** Fixed: `MAX_LOOP_SECONDS`
      constant; `decodeForWaveform` + `ensureAudio` default to the first 20s
      (matching the Pad); `updateTrimUI` clamps centrally so load, restore,
      re-add and drag all share one choke point. Decision taken: the loop
      defaults to the FIRST 20s, not the whole track.
- [x] **Flip posts the entire uncut file.** Fixed: the two WAV encoders and
      `buildTrimmedLoopWav` moved into `lib/audioloop.js` (encoders byte-identical
      to app.js's); `flip.js` shims them and `buildSharePayload` crops, rebases
      trim to `0..loopLen` and drops `crossfadeMs` (fold already baked in).
      Measured 1.41 MB vs 7.41 MB on a 42s file with an 8s loop. Drafts still
      keep the full sample.
- [x] **Pad can persist a garbage loop.** Fixed: `currentMusicMeta()` refuses to
      serialize trim numbers before the decode has produced them — it keeps a
      previously saved loop for the same file, else writes null trims so the
      load-time defaults apply.
- [!] **Not a bug — do not "fix" this.** A short loop right after a file is added
      is usually `setLoopToDrawingLength()`, the intended "loop matches your
      drawing" default. A `durationchange` handler was written this session on the
      theory that `loadedmetadata` reports a provisional duration; a direct probe
      disproved it (`NaN -> 42` in one step) and the handler was reverted.
      `verify_race.py` now pins the drawing-length default so it isn't mistaken
      for corruption again.

## Known caveats to close
- [ ] WebCodecs MP4 unsupported browsers silently fall back to WebM — surface which
      format the user will get before they export.
- [x] **GIF/MP4 no longer depend on CDN modules.** Both `mp4-muxer` (v103) and
      `gifenc` (v104) are vendored into `static/skribl/` and loaded as classic
      scripts. Offline-safe, no third-party runtime dependency, and **zero
      off-origin requests** on any surface — asserted in `verify_gifenc.py`.
- [~] Flip inline-JS/CSS split — DONE (v98). Flip's inline `<style>`->`flip.css`
      and inline `<script>`->`flip.js` (both `static/skribl/`), byte-identical to
      the originals, harness green. Step 3b shared libs: **audioloop DONE (v99)** —
      the crossfade DSP (`buildLoopChannels`/`buildLoopAudioBuffer`) now lives once
      in `lib/audioloop.js`, both files shim it. **WAV encoders + buildTrimmedLoopWav DONE (v102)** — both surfaces now crop
      posted audio through the same code. **zoom** (288 vs 75 lines),
      **strokes** (different signatures), **export** (IIFE vs standalone), and the
      `startWebAudioLoop` state-mutators REMAIN — divergent / stateful, so they're a
      reconciliation needing browser QA (no runtime golden in-sandbox).
- [x] **INTEGRATION step 4 — DONE (v103 + v104).** mp4-muxer vendored on both
      surfaces in v103; gifenc vendored in v104 as a global-publishing IIFE built
      from the npm tarball's own src (reproduce command is in the file's banner).
      The jsdelivr `script-src` is gone, so the CSP work is unblocked — note that
      inline `<script>` blocks remain, so a strict policy still needs nonces.
- [x] ~~Ship `static/skribl/og-card.png`~~ — already in the repo; the v101 zip was
      just incomplete. Not a bug.
- [ ] Two `exportGIF` copies exist (Pad `exportGif` in an `app.js` IIFE, Flip
      `exportGIF` in `flip.js`) — both transparent-capable, but different structure/
      names. Converge during step 3b's `export.js` reconciliation (last, riskiest).
