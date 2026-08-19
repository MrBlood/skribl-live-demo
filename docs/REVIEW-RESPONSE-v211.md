# v211 — the v210 developer review, closed; iPhone audio confirmed

**The owner reports audio working on the iPhone.** That is the hardware
confirmation the v209→v210 arc was built to earn, and it licenses the release
wording the project adopted: *mechanism corrected; playback verified on
device.* Shared links that were silent for three builds now play.

This build closes all four findings and the hardening item from the v210
developer review, plus one owner-reported desktop bug (Space+drag drew a
line). Every fix is pinned behaviourally and mutation-tested against the
historical mistake, per the project's rule.

## F1 — Flip kept the pre-fix fire-and-forget Web Audio shape → CLOSED

Verified in the tree before touching it: `flip.js` `startWebAudioLoop()` was
the v208 shape verbatim — `resume()` not awaited, source constructed and
started on a possibly-suspended context, `true` returned, native fallback
suppressed. The fix was ported to Pad in v209 and never to Flip. Now Flip has
Pad's contract: no source until the context reports `running`; a generation
counter so a late start cannot overtake Stop; and an `onFail` handoff so
native `<audio>` is reachable *asynchronously* — on rejection, on a
`resume()` that never settles (600 ms timeout; iOS leaves it pending), or on
a resume that lands on a still-suspended context. All three Flip callers
(`startMusic`, Preview Loop, Test Seam) had their native path made callable.
**Pinned** with the reviewer's exact counterexample — a suspended context
whose `resume()` never settles — on Flip, Pad, and the shared player: no
`createBufferSource`, no `start()`, native `play()` called.

## F2 — the crop/decode readiness race, both editors → CLOSED

Confirmed: `mediaBusy` is cleared by the FileReader's `onload`;
`decodeAudioData` is a separate promise chain; `mediaBusy == 0 &&
currentAudioBuffer == null` is a real window, and a post in it silently
shipped the whole song. Same readiness/decode split as Bug A, on the write
side. **Fix:** the decode promise is retained (`window._skriblDecodePending`)
and `submit()` (Pad) / `shareSkribl()` (Flip) await it — normally already
settled. A music payload with no buffer at post time now *warns*; it is a
decode failure, not a race. **Pinned** by holding `decodeAudioData`
unresolved, reaching the submit-enabled state, submitting, releasing the
decode, and reading the posted WAV's own header: 20 s ships, not 30.
Mutation (remove the await) ships 30 s. The pin never consults `trimEnd`.

## F3 — the failed-post quota release across workers/restarts → CLOSED (option A, uniform)

The owner chose **A — durable**, for a larger site. The reviewer corrected a
claim I made on the way: "on Postgres this finding doesn't exist" was an
architectural inference, and this project has been burned by exactly that
move repeatedly. So PostgreSQL got the two-worker test **first**:

- **PostgreSQL — proven unchanged.** `verify_postgres.py` now launches a
  harness-owned gunicorn host (`harness/f3_host.py` — `app.py` grows no
  test hook) with two real workers on the live database; commit failure is
  injected on worker A by request header; every response carries its worker
  pid. Worker B's immediate retry is 201; **two real successes fit a cap-2
  bucket and a third is limited** (the discriminator — a counted stranded row
  would leave room for only one). 20/20. The production-scale backend already
  had the semantics; v211 makes them a tested contract.
- **SQLite — made durable, not with a second write to the locked file.**
  The reviewer's caution was exact: another row in the same locked database
  is F2 under a different statement. The release is recorded in a **sidecar
  journal** beside the DB file (`<db>.rate-release.journal`, one fsync'd
  appended line, no database lock). Counting peeks the journal; the next
  reservation on *any* worker applies it while holding a writer and
  truncates it. Crash semantics stated: an append that didn't land ages out
  at TTL (v208 behaviour, never worse); one that did is applied by whoever
  next reserves. **Pinned**: restart (all process-local state discarded,
  fresh app on the same file, retry accepted, row swept, journal truncated)
  and two live workers on one file (B accepts, never having had A's memory).
  **Counterexample**: delete the journal between failure and retry → B
  counts the row → 429. The v209 memory-only counterexample was updated to
  drop the journal too, because the journal now rescues it — which is the
  point.
- **Documented** in `docs/INTEGRATION.md`: uniform contract, mechanism per
  backend, PostgreSQL recommended for multi-worker/scale, SQLite correct for
  small single-file deployments.

## F4 — `_FK_ENGINES` populated before listener installation completed → CLOSED

The v209 fix moved the add past the AUTOCOMMIT refusal but left it *before*
the two listener registrations; if either raised, the engine stayed recorded
and every retry returned False. The v209 pin only attacked the refusal —
one exception point generalised to the whole install. Now the add is the last
statement after both registrations. **Pinned** by making the second
`listens_for` raise: engine not recorded, retry installs. Mutation (add moved
back) fails both.

## H1 — shared-player resume rejection/hang fallback → CLOSED

Parity with the editor: when Web Audio cannot unlock, `paStartAtElapsed`
hands off to the `<audio>` element `loadSkribl` already creates, aligned to
the drawing position; `paStop` pauses it. **Pinned** on a posted skribl under
a never-settling resume. One fixture trap worth recording: a 400 ms stroke
*ended* before the 600 ms unlock timeout, `audioPause → paStop` bumped the
generation, and the fallback correctly refused to start music after the end
— it looked like a regression until the generation was traced. The fixture
is 3 s now.

## Owner: Space+drag drew a line on desktop → CLOSED

Two bugs stacked. The grab-pan intercept was gated on `zoom > 1`, so at 100%
the drag fell through to the drawing tool — the wrong failure even with
nothing to pan; Space means "hand, not pen". And Flip draws on `pointerdown`,
which fires *before* the `mousedown` the intercept listened for, so even
magnified a capture-phase `mousedown` was too late there. The fix that
matters is at the **stroke start**: both editors refuse to begin a stroke
while Space is held, at any zoom.

One correction made during the release run, caught by `verify_keys`: on Flip,
Space is **play/stop when not zoomed** by design, and the pan registration
was scoped to be mutually exclusive with it. The first v211 draft dropped that
scope so Space+drag would "pan" at 100% on Flip too — which made a Space
keydown both a play toggle and a pan arm, exactly the double-owner collision
the registry exists to catch. Restored: Flip pans only when zoomed, plays when
not, and the draw-suppression lives in `pointerdown` where it is correct at
any zoom. Pad, which has no Space-to-play, keeps Space as always-grab.
**Pinned** the way the owner found it — hold Space, drag, count strokes: zero
at 100% and magnified on both editors, drawing resumes on release, and on
Flip the held Space did not toggle playback. Mutation (old gate back) fails
`pad@100%` and passes `pad@magnified`.

## Ratchet

146,911 — owner: set to fit. The ~2,060 B editor-only Web Audio loop
externalisation is now clearly worth its own build.

## Gates

audiostate 29 (+13) · txcontract 66 (+12) · postgres 20 (+6, live, two
workers) · ux 294 (+10) · cssplit 18 (+1, computed-style radii) · keys 9 ·
docs 34 · seam 121 · player-isolation 20.
