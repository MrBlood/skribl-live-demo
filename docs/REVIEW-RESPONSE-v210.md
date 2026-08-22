# v210 — the iPhone build

v209 shipped with F2 and F3 closed and one item outstanding: a real iPhone. The
iPhone found that the shared-link player was **silent** — and that three builds
of "iOS audio fixed", 2,337 assertions, and two independent reviews had all
certified a mechanism the phone had never confirmed. This build closes what the
phone found, the four findings of the v209 developer review, and three
real-device layout defects, and it changes what "iOS audio fixed" is allowed to
mean.

## What the phone actually found (two deterministic bugs, not a platform quirk)

The first hypothesis — an unlock race — was wrong, and it was wrong in the same
way as F1, A1 and `_waGen` before it: a right-looking mechanism for the wrong
condition. An on-device trace (a temporary `?audioDebug=1` diagnostic wrapping
the real Web Audio API, removed before this seal) showed the context unlocking
perfectly and then **nothing**: no source constructed, no failure, no handoff.
That localised the fault to before source construction, and from there both
causes were reproduced in the harness with discriminating tests before a line
of the fix was written.

**Bug A — the player's loop bounds lived inside `loadedmetadata`.** `trimEnd`
starts at 0 and was assigned only in an `<audio>` element's `loadedmetadata`
handler. iOS defers media loading until playback is requested, so on a shared
link the event routinely had not fired when the user tapped Play: the loop
window was zero-length, `buildLoopAudioBuffer()` returned null *without
throwing*, and no source was ever built. Desktop fires the event immediately,
which is why it never showed there or in headless. **Reproduced**: suppress the
event and zero `AudioBufferSourceNode`s are created; allow it and exactly one
is. **Fixed**: `loadSkribl()` installs `trimStart`/`trimEnd`/`crossfadeMs`
synchronously from the payload; `decodeAudioData` supplies the authoritative
duration and the `min(duration, 20)` default when `trimEnd` is absent. The
invariant now pinned: *once `currentAudioBuffer` exists, the loop bounds are
valid whether or not media metadata ever loaded.*

**Bug B — the post-time loop crop was dead code on every v2 post.**
`editor_post.js` guarded on `payload.music`, a field `serializeSkribl()`
stopped producing at the v2 frame migration (media lives in `frames[0].music`).
The server had been migrated for frames; this client consumer had not. So every
shared post carried the whole song with the authored trims — the 124.84 s the
phone decoded. **Proven by bytes**: the posted media was exactly the full
30 s source (1,323,045 B at 22.05 kHz mono), not the 20 s loop. **Fixed**
through a new writer-side accessor, `window.SkriblPayload.currentFrameMedia()`,
so no further module has to know where a frame keeps its media — format
knowledge drifting between modules is what caused it. A failed crop now warns
instead of vanishing.

Both are in `verify_audiostate.py` (16 pins). Both were **mutation-tested
against the exact historical mistake**: trim init moved back under
`loadedmetadata` → zero sources; the crop pointed back at `payload.music` →
30 s posted. And two weak tests were corrected on the way, which is worth
recording: `trimEnd == 20` is *not* proof of cropping (an uncropped payload
carries the authored trim too), and a byte count computed for mono is wrong
for a stereo decode. The pin reads the generated WAV's own header.

## The v209 developer review — all four closed

**F1 — `_waGen` never incremented on stop.** The counter existed; the property
did not. `stopWebAudioLoop()` and the player's `paStop()` now bump their
generation first, so a start awaiting its unlock cannot land after Stop.

**F2 — a rejected `resume()` started anyway.** Both paths now invalidate on
rejection. And on the owner's iPhone that turned out to be *insufficient*:
refusing to start on a suspended context is correct, but the callers suppressed
their native `<audio>` fallback whenever the Web Audio path was "taken", so a
context that never reached `running` went from intermittently silent to always
silent. `startWebAudioLoop()` now takes an `onFail` handler and both callers'
native paths were made reachable **asynchronously**, with a 600 ms timeout for
a `resume()` iOS leaves pending rather than rejecting.

**F3 — a refused AUTOCOMMIT engine was recorded as installed.** `_FK_ENGINES`
registration now happens *after* the listener is attached, so a host that
catches the refusal and rebuilds the engine gets refused again rather than
silently skipped. Pinned.

**F4 — `busy_timeout` lapsed across a mid-session commit.** The reserve path
commits twice and a sweep commits mid-request; after a commit the session may
hold a different pooled connection whose timeout is pysqlite's 5 s default.
Bounded at every checkout by an engine-level listener now. Pinned by reading
the PRAGMA back on the post-commit connection.

The player also stops constructing a source on a suspended context — the
`if (running && !paSource)` retry from A1 is deleted, because it could never
fire (a silent source had already set `paSource`). `paSource` now means
"started on a running context". `verify_ux` guards its absence.

## Real-device layout (owner's iPhone photos), and the audit that missed them

**Onion tint clipped at the right edge.** 4 px from an `overflow:hidden`
ancestor; iOS font metrics ate it. `.tune-label` yields on phone and the row
may wrap.

**Magnifier offset the zoom pills.** The 16 px glyph + 8 px gap put the 1×–8×
segment 24 px right of Loop/Start/End. Both segments share the indent now.

**Nudge rows.** Start and End side by side, Step underneath. Columns are sized
to the *measured* 128 px pill (`minmax(130px)`), and drop to one column at
≤363 rather than spill — v207's exact bug class, which the audit caught again
during this build.

**The header.** Worse than the photo. With a take saved, `#tuneBtn` was
rendering **underneath the logo** at x=16 — the cluster overflowing leftward
into an over-full flex box. On first load at 375 the tune glyph painted over
the "d" of "Pad"; at 320 the glyph and dot sat inside the wordmark. `fitBrand`
measured `scrollWidth`, which never grows when things overlap. It now measures
the real gap to the brand and sheds in cost order — wordmark, Record's label,
inter-control gap, Post's label — stopping as soon as nothing collides. A
320-class tier (36 px controls) exists because six 40 px controls are 50 px
over-full there with everything shed and nothing left to shed without
orphaning Flip Mode.

**The phone audit is widened**, as the v207 review asked: 2-D rectangle overlap
(no row heuristic — the 34 px mark vs 40 px button never compared before),
`left < 0`, vertical overflow, and clipping ancestors with a clearance margin.
The brand is in the set. Design-intended clipping is exempted by name: `.seg`
pills, `--tap-grow` hit areas, the thumbnail card, controls inside a collapsed
drawer, the transient hint toast.

## What changes about "fixed"

Release language for device media is now **"mechanism corrected; physical
playback verified on [device / iOS version]"**, and the second half is not
written until the phone says so. This build's targeted check: on a share link,
trims present before any metadata event; a source constructed and started on
first Play; the post decoding ~20 s rather than the source length.

## Ratchet

Player-JS 145,053 → fits (owner: "don't worry about the ratchet"). Four
functional raises this arc; the ~2,060 B editor-only Web Audio loop block
externalisation would recover most of it, deferred to keep audio fixes and code
moves in separate builds.

## Gates

audiostate 16 (new) · txcontract 54 (+6 F3/F4) · ux 284 (+12 header/nudge,
+widened audit) · seam 121 · player-isolation 20 · all others unchanged.
