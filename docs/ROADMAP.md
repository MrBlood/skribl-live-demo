# Skribl — Roadmap (Pad + Flip)

Status legend: [ ] todo  ·  [~] partial  ·  [x] done

## Shared / platform
- [ ] **Exact-quota rate limiting — OPEN, and a deliberate non-decision (v134).**
      The limiter guarantees AT MOST `SKRIBL_RATE_MAX_POSTS`, not exactly it:
      insert -> commit -> count -> delete-if-over means concurrent racers can all
      withdraw and under-admit. Making it exact needs serialized slot allocation
      (advisory lock on bucket+key_hash, a counter row with SELECT ... FOR UPDATE,
      serializable + retry, or Redis with a Lua script). All serialize a client's
      posting to buy exactness nothing requires. **Only build this if the product
      decides the number must mean what it says**; the current fail-closed bias is
      correct for abuse prevention. Two suites asserted exactness for ~10 versions
      and passed on luck — corrected in v134, don't reintroduce that assertion.
- [ ] **Edge rate limiting.** The source comments already note this is the better
      answer for raw flood protection than anything in the app process.
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
- [~] **Rate limiting** — a shared-store backend landed in v117. Set
      `SKRIBL_RATE_BACKEND=db` and the quota is shared across gunicorn workers and
      survives deploys, keyed by a salted hash of the client identity (never a raw
      IP). **The default is still `memory`, which is per-process** — flip it on the
      deploy or the production quota remains per-worker. Redis/edge limiting is
      still the answer at real scale. The shared harness raises the cap to 100000,
      but `verify_review.py` starts its own low-quota servers and covers both
      backends, including that a restarted process still sees the quota spent.
- [~] **Abuse/moderation**: posts are public + unauthenticated. **Media is now
      validated server-side (v105)** — type allow-list (SVG excluded), base64
      checked, per-item byte caps beyond the whole-request `MAX_CONTENT_LENGTH`.
      Report/hide and content review hooks remain before a social launch.
- [x] **CSP (v105)** — nonce-based, enforced, no `unsafe-inline`/`unsafe-eval` in
      `script-src`. Deliberately no `frame-ancestors`, so the iframe embed keeps
      working. `SKRIBL_CSP=report-only|off` to stage or disable.

## Skribl Pad
- [x] **DONE (v132) — stylus pressure.** Optional per-point `p` (0..1), read only
      by `pointWidth()`, written only by a pen, byte-identical payloads for mouse
      and finger. Width multiplier is centred so neutral pressure is a no-op.
      Covered by `verify_pressure.py` (38 assertions).
- [ ] **Migrate the Pad to pointer events — NEW, opened by v132.** The Pad is
      bound to mouse/touch, so it reads pressure from `Touch.force` and gets
      Apple Pencil on iOS but **not** desktop drawing tablets, which report
      through `PointerEvent` only. Flip already uses pointer events and has no
      such gap. The migration also touches pinch-to-zoom and the window-level
      mouseup commit path, so it is a refactor with real regression surface, not
      a one-liner. Do it deliberately or not at all.
- [ ] **A control to disable pressure — NEW, opened by v132.** There is no way to
      turn it off. The v133 drawer is now the obvious home for it: add a "Pen
      pressure" switch under a Drawing group. Not built in v133 because the
      pressure capture itself has still never touched real hardware, and a switch
      for an unverified feature is premature.
- [x] Undo next to "Clear drawing" (snapshot restore).
- [x] **DONE (v106)** — the ⋯ "Clear all" (resetAll, wipes media) is now undoable:
      snapshot via `serializeSkribl()`, restore via `loadSkribl()`, offered as an
      Undo button in the toast. Media returns too. Superseded item:
- [~] Make the ⋯ "Clear all" (resetAll, wipes media) undoable too, or add a
      confirm-with-preview.
- [x] **DONE (v107)** — Redo for the clear-undo. Undo offers Redo, Redo re-offers
      Undo, so it toggles either way.
- [ ] **Multi-take reorder/trim — RE-SCOPED (v110), not polish.** There is no takes
      data model: `endRecordingTake()` appends into the same flat `strokes` /
      `strokeGroups` arrays, so nothing addresses "a take". This needs (a) a takes
      structure with segment boundaries and per-take timing, and (b) a product
      decision on what reordering means for replay timing and recorded timestamps.
      Design first, then build.
- [x] **ALREADY DONE — the item was stale.** The export sheet is a shared partial,
      so the Pad has offered PNG + Video (MP4/WebM) + GIF for several versions;
      `exportGif()` (app.js) animates the replay and `verify_gifenc.py` has been
      exporting a 19-frame Pad GIF since v104. Nothing was built for this.

## Flip
- [x] **DONE (v133) — settings drawer reorganised.** Speed, Canvas, Onion skin,
      Pages behind and Tint are one grouped list; the ⋯ menu holds actions only.
      Canvas moved out of that menu and became a dropdown. Onion keeps its header
      shortcut and gained a mirrored switch in the drawer.
- [ ] **Tint row wraps at phone width — cosmetic, open.** "colour older pages
      warmer" goes to two lines under 400px, making that row 59px against 46px
      for every other row. Signed off as acceptable; shorten the hint if it starts
      to read as lumpy.
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
- [x] **DONE (v107 + v109)** — duplicate (already existed), reorder, copy/paste,
      and **drag-to-reorder in the strip (v109)**, pointer-based so it works with
      touch and pen. The button-based move remains for keyboard/test reach.
- [x] **DONE (v109)** — per-page hold of 1–4 base-fps slots, cycled from the page
      op bar with an always-visible badge. Additive to the payload: written only
      when > 1, absent reads as 1, so old and new Skribls interoperate both ways.
- [x] **DONE (v107)** — onion depth 1–3 at decreasing alpha, plus an optional
      warm-to-cool tint by distance. Controls appear beside the onion switch only
      while onion is on.
- [x] **DONE (v108)** — export sheet now has Size (Full/Medium/Small) and a
      first–last page range, shared by GIF, WebM and MP4 via `exDims()`/`exRange()`.
      Note the GIF default changed from a forced 480px downscale to native; Medium
      reproduces the old output exactly.
- [x] **DONE (v110)** — 4:3 / 16:9 / 1:1 / 9:16 presets from the ⋯ menu. Needed no
      format change: `canvasSize` was already in the payload and already honoured
      by the player. Strokes keep their coordinates, so resizing crops the view
      rather than distorting artwork, and switching back restores the framing.

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
- [ ] **Pressure has never touched real hardware (v132).** There is no stylus in
      the sandbox, so `verify_pressure.py` covers the width maths, the clamping
      and the byte-identity rule, but never the line that reads `Touch.force` or
      `PointerEvent.pressure`. Needs an Apple Pencil (Pad, iOS Safari) and a pen
      on a pointer-events device (Flip). Until then the feature is verified in
      every respect except the one that made it worth building.
- [x] **DONE (v106)** — WebCodecs-MP4-unsupported browsers no longer fall back to
      WebM silently. Both surfaces label the export button with the container they
      will actually produce ("Video (MP4)" / "Video (WebM)") and say it in the
      description. Flip had no such label at all before; the Pad named only MP4.
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
