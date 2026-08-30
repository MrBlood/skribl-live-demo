# Skribl — Handoff (v131)

> **v111–v131 are summarised below and documented in full in `REVIEW-RESPONSE.md`**
> **(historical). The CURRENT review responses are `docs/REVIEW-RESPONSE-v201.md`**
> **and `docs/REVIEW-RESPONSE-v200.md`.**
> That file is the primary record for everything after v110: it was written round
> by round against an external code review, so it carries the reasoning, the
> measurements and the things that turned out to be wrong. Read it alongside this.

## v111–v131 at a glance

**Security and correctness (v111–v122), driven by an external review.** Ten rounds.
Payload validation (coordinates required, stroke groups must account for their
points, canvas sizes bounded and integral, media container-checked, SVG refused);
rate limiting rebuilt with an atomic reservation and a pending/committed split;
CSP scoped per route; trusted-proxy handling made safe by default; dependencies
hash-pinned. Several findings were regressions I had introduced myself, and two
were reporting failures rather than code failures — the harness aggregate is now
machine-generated for that reason.

**PostgreSQL concurrency (v123–v125).** For several rounds I claimed PostgreSQL
was unavailable in the build environment. It took two commands to install.
`verify_postgres.py` now runs gunicorn with four worker processes against a live
PostgreSQL 16.14, releases 12 simultaneous posts against a quota of 2, and reads
the row counts out of the database: 2×201, 10×429, two post rows, two committed
rate events, zero pending. Worker liveness is observed per-process, because a
surviving master would not reveal a crashed-and-respawned worker.

**UI and UX (v124–v131), all from screenshots rather than the roadmap.**
- Per-page controls left the thumbnail for a toolbar above the strip: 18×18px
  targets became 38×38, the preview is no longer covered, and Delete moved far
  from Hold (they were ~4px apart, where a mis-tap deleted a page).
- "Re-add" was blurry — a dark text-shadow under dark-on-yellow text, shared from
  a rule meant for white text. Four instances, one fix.
- Flip's "Flip it" matched "Post to Skribl" exactly, so the surface had two
  primary buttons. It now mirrors the Pad's Play in all four respects it was
  missing: subdued styling, a duration badge, hidden until usable, and the
  pulsing ring during playback. Elapsed time ticks while playing.
- The header was 52% document settings on a phone, pushing the ⋯ menu off screen
  at 360px **and** 768px. Speed and onion depth/tint moved into a drawer that
  slides down from the header (`grid-template-rows` 0fr→1fr, so it animates to the
  content's own height), with captions explaining what "6 12 24" and "1 2 3" mean.

**A caveat on the last few rounds:** screenshots stopped rendering back to me, so
v129–v131 were judged entirely on measurement — gap distances, clipping, fit at
four widths. That caught every problem reported, but nobody has visually confirmed
the final state.

## v110 — the last two feature items, and one that turned out not to exist

## v110 — the last two feature items, and one that turned out not to exist
### Variable canvas size — and it needed no format change
Flip was hardcoded to 640x460. But the payload has **always** carried `canvasSize`,
and the player has **always** honoured it (`establishEditorCanvas`, app.js:4129) —
Flip was simply pinned to one of the sizes it could already describe. So unlike
v109's `hold`, this needed no new field, no compat shim and no schema thought.
`applyPayload()` now restores a saved size, which is the only piece that was
actually missing.

Presets: 4:3 (640x460), 16:9 (720x405), 1:1 (560x560), 9:16 (420x640), from the
⋯ menu because it is a document property rather than a tool.

**Stroke coordinates are deliberately NOT rescaled.** A drawing keeps its position
and size on the page; a smaller canvas crops the view rather than silently
distorting artwork, and because the strokes are never destroyed, switching back
restores the framing exactly. That round-trip is asserted.

`applyCanvasSize()` resizes all four layers (`pad`, `onionCv`, `tmpCv`, `frameCv`)
and re-applies the DPR transform — **setting canvas.width resets the context
transform**, so forgetting that half-scales everything. Pinned.

### "How it works" now matches the app
Deferred deliberately since v106 so it could be written once rather than five
times. Both surfaces updated: Flip gains canvas shapes, onion depth/tint, page
move/copy/hold and drag-reorder, per-page timing, and export Size/Pages; the Pad
gains the undoable Clear all. Both now say the video button names the format the
browser will actually produce. `verify_canvas.py` asserts the help text mentions
each feature **and** that Flip-only copy doesn't leak into the Pad's help.

### Multi-take reorder/trim — the item assumes a model that doesn't exist
ROADMAP called this "UI polish". It isn't. There is no takes data structure: only
`endRecordingTake()`, with takes appended into the same flat `strokes` /
`strokeGroups` arrays. "Reorder or trim takes" means first building a takes model
(segment boundaries, per-take timing), then deciding what reordering *means* for
replay timing and for the recorded stroke timestamps — product design, not polish.
**Left open and re-scoped in ROADMAP rather than half-built.** This is the fourth
roadmap item found to misdescribe the code.

## v109 — drag-to-reorder; per-page hold, the first payload change

## v109 — per-page hold is the first new payload field since the frame format
### Drag-to-reorder
Pointer-based (touch and pen, not just mouse). The strip is **not** rebuilt
mid-drag — rebuilding would destroy the element under the pointer and drop the
gesture — so the tile is translated visually and the reorder happens once on
release. A 6px threshold keeps ordinary taps selecting.

`movePage()` is now a thin wrapper over `movePageTo(i,j)`, shared with the buttons.
The drop index is *how many tile centres sit left of the pointer*, minus one if
inserting after its own old slot, because `movePageTo` splices the page out before
splicing it back in. Getting that off by one puts the page in the wrong slot in a
way that looks almost right — it is pinned.

### Per-page hold (`hold`)
A page can now occupy 1–4 base-fps slots instead of always one. Cycled from a ×N
button in the page's op bar; a held page shows an always-visible badge so the
timing of an animation is readable without hovering every tile.

**The compatibility rules, which are the whole point:**
- `frameHold(f)` is the ONLY way hold is read. It never trusts `f.hold` to exist,
  and clamps garbage/0/negative/999 to the 1..MAX_HOLD range. A pre-v109 page has
  no field at all and reads as 1.
- `hold` is **written only when > 1**. An animation with no holds serialises to
  exactly the bytes it did before — asserted, not assumed.
- A v109 payload in an older player degrades to uniform timing, because an
  unknown field is ignored.

Wired through five consumers: Flip's play loop (now self-scheduling timeouts
rather than a fixed `setInterval`, since each step has its own delay), all three
encoders, and the player in `app.js`, which maps elapsed time to a page through a
cumulative hold table (`flipIndexAt`) instead of `floor(t * fps)`.

**A rounding bug this surfaced.** GIF stores delay in centiseconds. Multiplying the
millisecond delay by the hold and then rounding made held pages drift — 3 x 83ms =
249ms rounds to 25cs, not the 24cs three base slots should be. Delay is now
quantised to whole centiseconds *first* and multiplied after, so holds are exact
multiples. Output at hold 1 is unchanged (8cs either way).

Timing is verified off the exported GIF's per-frame delays, since a state check
would prove nothing about what the encoders actually emit.

## v108 — export size + page range; export parity was already done

## v108 — export options, and a stale roadmap item corrected
### Export parity was already achieved — the roadmap was wrong
ROADMAP listed "Export parity with Flip (GIF/MP4 of the replay) — currently PNG +
WebM" as open. It isn't: `_skribl_export.html` is a **shared partial**, so both
surfaces already offer PNG + Video + GIF, the Pad's `exportGif()` (app.js:4563)
animates the replay, and its MP4 path has existed since the WebCodecs work.
`verify_gifenc.py` has been exporting a 19-frame GIF from the Pad since v104.
Ticked off, nothing built. This is the third stale item found this way (after
og-card.png and the "identical" startWebAudioLoop copies) — **check the code before
building against this file.**

### Export size + page range (Flip)
GIF had a hardcoded 480px cap with no way out, and every export always covered
every page. Both are now controls on the export sheet:
- **Size**: Full (native 640x460) / Medium (480) / Small (320).
- **Pages**: first–last, 1-based, clamped on every edit.

**Behaviour change worth knowing:** the default is now **Full**, so GIFs export at
native resolution rather than the old forced 480 downscale — better fidelity, but
bigger files. **Medium reproduces the old output exactly** (480x345). This broke
`verify_gifenc.py`'s size assertion, which had pinned the old constant; updated.

The important structural bit: **one pair of helpers, `exDims()` and `exRange()`,
feeds all three encoders** (GIF, WebM, MP4), so they cannot drift apart on what
"Small" or "pages 2-4" means. `drawFrameTo()` paints in CW/CH coordinates, so the
video paths scale via a single `setTransform` on the recording context rather than
touching every draw call. `exRange()` clamps and swaps reversed input as a backstop
even though the UI clamps too — it is the shared contract, not the UI, that the
encoders rely on.

Verification is byte-level: `verify_exopts.py` exports real GIFs and reads the
dimensions and frame count out of the file, because a size control that only
changes a label would pass any UI-state check. That is only possible because
gifenc was vendored in v104.

Still session-only state: nothing here reaches the payload.

## v107 — onion depth/tint, page reorder + copy/paste, clear redo

## v107 — three features off the UI/UX list
**Nothing here touches the payload format.** Onion depth/tint are session-only view
state; reorder and paste mutate the existing `frames` array. A v107 Skribl opens in
an older player and vice versa — asserted in `verify_pages.py`, not assumed,
because that assertion is the baseline the two REMAINING features (per-frame
duration, variable canvas size) will have to preserve when they land.

### 1. Onion skin: depth 1–3 + colour tint
Was a single boolean showing `idx-1` at alpha 0.28. Now shows up to three pages
back at decreasing alpha (0.30 / 0.17 / 0.10), optionally tinted warm-to-cool by
distance (`#ff5f6d` / `#ff9f43` / `#ffd76a`).

The tint uses `globalCompositeOperation='source-in'` on the offscreen layer, which
repaints the strokes' own pixels and leaves transparent areas alone — a silhouette
recolour rather than a wash over the whole frame. It renders into `onionCv`/`octx`,
which had been **scaffolded in v98 and left unused ever since**, keeping `frameCv`
free for the current frame.

The controls live in a group beside the onion switch that is only present while
onion is on, so the toolbar isn't permanently crowded on narrow screens.

### 2. Pages: reorder + copy/paste
Duplicate already existed (`#addcopy` -> `addFrame(true)`); reorder and copy/paste
did not. Each strip tile now carries a move-left / copy / move-right bar, revealed
on hover or on the active page. Copy fills a `pageClip`, which makes a "＋ Paste"
button appear in the add column; paste inserts after the current page.

Two details worth keeping if this is refactored: `movePage()` keeps `idx` pointing
at the **same page** the user was on rather than the same index — moving a page must
never silently switch which page you're drawing on — and paste goes through
`deepCopy()`, so pasting twice yields independent pages instead of two references
to one. Both are pinned.

### 3. Clear all: Undo now offers Redo
v106's restore was one-shot. Undo now shows a "Redo" that simply re-runs
`clearAllWithUndo()`, which re-snapshots the restored document and re-offers Undo —
so it toggles either way, with no second snapshot to fall out of sync.

### A v106 bug this work surfaced
`showToast()`'s action handler scheduled `hidden = true` 200ms after a click. When
the action showed a *replacement* toast (Undo -> "Restored ... Redo"), that pending
hide fired and hid the new toast almost immediately. v106's test missed it because
`textContent` survives hiding, so a text assertion passed on an invisible element.
Fixed with a single cancellable `toastHideTimer` that a new toast clears on its way
in. If you add another toast-replacing flow, that timer is the thing to respect.

## v106 — UX: honest export labels, undoable Clear all

## v106 — two UX fixes, both about not lying to the user
### 1. Flip now names the video format it will actually produce
The Pad has always labelled its export button with the real container —
"Video (MP4)" or "Video (WebM)" — by probing WebCodecs before rendering the sheet.
**Flip never did.** It said "Video", and on any browser without WebCodecs H.264 it
silently handed you a WebM. That was the last open item in ROADMAP's "Known
caveats to close".

`expectedVideoFormat()` in `flip.js` mirrors `exportVideo()`'s real decision path
with no side effects, including the subtle case that makes this worth doing
properly: when music is present but AAC is unavailable, `exportViaWebCodecsMp4()`
deliberately bails to WebM rather than ship a silent MP4 — so the *label* has to
bail the same way, or it promises MP4 and delivers WebM in exactly the situation
the fallback exists for. It is cheap on purpose: no loop buffer is built, since
`aacSupported()` only needs the sample rate and channel count, which the trimmed
loop inherits from `currentAudioBuffer`. An `_exFmtToken` guard drops stale async
results if the sheet is closed and reopened.

The Pad got a smaller fix in the same spirit: its description named the container
only when the answer was MP4, leaving WebM users with a generic string. Both
surfaces now say it either way.

### 2. "Clear all" is undoable
`resetAll()` wiped strokes, music, photo and background, then called
`clearAutosave()` — so the recovery copy went with it. The two-tap arm guarded the
*accidental* tap; nothing could undo a deliberate one, and it is the single most
destructive action in the app.

It now snapshots through `serializeSkribl()` and restores through `loadSkribl()` —
**the same pair the draft and autosave paths already use**, so media comes back
too and there is no parallel restore logic to keep in sync. Skipped while
`mediaBusy > 0` (same guard `saveDraft()` uses), because the snapshot would
capture a half-loaded photo or track; the clear still happens, just without the
undo offer.

The affordance is new: `showToast()` takes an optional `{ label, onClick }` and
renders a button. Watch out for one trap if you reuse it — `.toast` is
`pointer-events: none` so it never blocks the canvas, which means the button must
re-enable pointer events on itself or it looks clickable and isn't. Toasts with an
action hold for 7s instead of 2.8s, since an offer to undo has to be read and
reached.

### Note for the next session
`updateClearVisibility()` disables the Clear all menu item while `recording` is
true, and drawing auto-starts recording — so a JS `.click()` on it silently does
nothing. That made the first version of `verify_ux.py` look broken rather than
blocked. The suite now stops the recording first and pins both states.

## v105 — CSP enforced; media validated server-side

## v105 — the security half of the roadmap, now that vendoring unblocked it
Two items shipped, both from INTEGRATION §7, both harness-verified. **No static
files changed this session** — `app.js`, `flip.js` and `lib/audioloop.js` are all
untouched, so there are no cache-bust bumps. The changes are `app.py` plus a
`nonce` attribute on two inline `<script>` tags.

### 1. A real Content-Security-Policy
CSP was deferred for as long as gifenc/mp4-muxer came from jsdelivr: any workable
policy needed a third-party `script-src`, and the CDN loaders were themselves
inline `<script type="module">` blocks. Vendoring both (v103/v104) removed the last
off-origin script AND the last inline module, so `script-src` can now be strict.

What made it cheap: the templates have **zero inline event handlers**, zero
`javascript:` URLs, zero inline `<style>` blocks, and only **two** inline
`<script>` blocks (the `SKRIBL_MODE` config in the editor and player). Those two
get a per-request nonce from `flask.g`.

Two traps found while writing it, both of which would have shipped as silent
breakage:
- **`connect-src` must include `data:`.** `app.js` calls `fetch()` directly on
  data URLs (`fetch(data.music.data)`, `fetch(built.dataUrl)`) to get audio into
  an ArrayBuffer. A textbook `connect-src 'self'` breaks music loading on the
  player and the WAV/MP4 build path — with no console error that points at CSP.
- **`style-src` must keep `'unsafe-inline'`.** There are 51 `style="..."`
  attributes across the templates, and a nonce cannot cover style *attributes*,
  only `<style>` blocks. Removing that needs a refactor, not a policy tweak. It is
  much lower risk than inline script and there is no user-controlled style surface.

**No `frame-ancestors`, on purpose.** The player is embedded in an iframe on
skribls.net and the previous note in `app.py` warned that a blanket deny would
break it. Omitting the directive leaves framing unrestricted, matching the
deliberate absence of `X-Frame-Options`. `verify_csp.py` asserts the absence, so
nobody "hardens" it by reflex.

`SKRIBL_CSP=report-only` sends it as `Content-Security-Policy-Report-Only`;
`SKRIBL_CSP=off` disables it. Default is enforcing.

`verify_csp.py` (31 assertions) tests three separate things, because "the header
is present" is the weakest possible claim: the policy SHAPE; that it is actually
ENFORCED (a DOM-inserted un-nonced script is blocked — positive control, so a
header the browser ignores fails); and that it is NON-BREAKING (zero
`securitypolicyviolation` events on all three surfaces, the nonced config scripts
execute, a real GIF still exports over blob:, and `fetch()` of a data: URL works).

### 2. Server-side media validation
`POST /api/skribls` is public and unauthenticated, and all media arrives as base64
data URLs inside `payload_json`. The only limit was `MAX_CONTENT_LENGTH` on the
whole request, so one post could carry ~24 MB of arbitrary blob — any type, valid
base64 or not — into the JSON column. At the current rate limit that is roughly
**480 MB/hour/IP** into a free-tier Postgres.

`_validate_payload_media()` now walks top-level media, per-frame media, and the
thumbnail, checking top-level type (allow-list: `audio/*` for music, `image/*` for
photo/thumbnail, **SVG excluded** — the one image type that carries script),
rejecting malformed base64, and capping bytes per item (12 MB audio / 8 MB image /
2 MB thumbnail, all env-tunable). Size is computed from the base64 length *before*
decoding, so an oversize payload is rejected without spending the CPU.

Subtypes are deliberately left open: `music` is whatever audio file the user
picked, and narrowing it would reject legitimate uploads for no security gain.
**Not covered:** dimensions and duration, which need real decoding (Pillow / an
audio decoder) and a dependency this app does not have. Bytes and type are the
cheap 90%.

> **BOTH SENTENCES ABOVE ARE SUPERSEDED — this is the v105 record, kept as
> written.** v111 replaced the open subtype list with a strict allow-list and
> byte-signature checks per container. v224 added dimensions: they read out of
> the header of all four accepted image formats with no decoder and no new
> dependency, which is what closes the decompression-bomb case a byte cap never
> could — a 66-byte PNG can declare 30000x30000. Duration is now parsed for WAV
> only, and compressed audio remains bytes-bounded exactly as this paragraph
> says. Current behaviour: `skribl/validation.py` and `verify_medialimits.py`.

`verify_media.py` (24 assertions) guards both directions, and the ACCEPT cases
matter more than the REJECT ones — a validator that breaks legitimate posts is
worse than none.

### 3. The version label in the UI had drifted nine releases
The Pad's overflow menu read **"Skribl Pad · v96"** while the app was at v105 — a
hardcoded literal in `skribl_editor.html:80` that nothing forced anyone to update.
Cosmetic, but actively misleading: it is the one place you look to answer "what
version is actually running?" while debugging a deploy, and it was answering wrong.

Now single-sourced as `SKRIBL_VERSION` in `app.py`, injected via the same context
processor that supplies the CSP nonce. **Bump that one line per release.**
`verify_version.py` (17 assertions) fails if a version literal reappears as visible
text in any template, which is the only way this can silently rot again.

Note this is unrelated to the `?v=104` cache-busts, which are deliberately
per-file and only change when that file changes.

### The rate limiter has been quietly throttling the harness
Writing `verify_media.py` tripped `POST /api/skribls`'s 20/hour/IP limit: the suite
posts 24 times, and four assertions failed with 429s that looked exactly like
validation failures. The posting suites together were already sitting *just* under
the cap, so any new posting assertion anywhere would have produced the same mystery.
`run_harness.sh` now exports `SKRIBL_RATE_MAX_POSTS=100000` for determinism. The
trade-off: **the rate limiter is no longer under test** — check it by hand, or run
a suite with the variable set low.

### Deliberately NOT done, with reasons
- **INTEGRATION §1, the Blueprint.** It is step 1 of the suggested sequence, but
  its whole purpose is dropping Skribl into a host app that owns `db` and auth —
  and the signature the plan specifies, `create_blueprint(db, login_manager=None,
  config=None)`, cannot be designed against a host that doesn't exist yet. Doing
  it now means guessing the host's conventions and rewriting later, in exchange
  for adding indirection and deploy risk to a working standalone demo. Recommend
  doing it in the same session as the host integration.
- **§3b zoom / strokes / export / `startWebAudioLoop`.** The docs describe the two
  `startWebAudioLoop` copies as "identical text", which turns out not to be the
  whole story: `app.js:2592` and `flip.js:1412` both read `_waLoopSource` from
  *outside* the functions, and the two `webAudioLoopSongTime` implementations have
  different fallbacks. So sharing them needs a stateful controller object exposing
  an `isRunning()` accessor, not an extraction — confirming the docs' own call that
  this is reconciliation, ranked last and riskiest. The payoff is ~20 de-duplicated
  lines against the most delicate subsystem in the app; CSP and media validation
  were the better use of the same risk budget.
- **Rate limiting → Redis, object storage, auth, moderation.** All infrastructure
  or host decisions, not code changes that can be verified here.

## v104 — gifenc vendored; GIF export verified for the first time

## v104 — INTEGRATION step 4 is DONE, and GIF export is no longer unverified
gifenc was the last CDN dependency. Both surfaces pulled it from jsdelivr as an
ESM module, which meant two things: GIF export was dead anywhere jsdelivr was
blocked, and — because jsdelivr is blocked in this sandbox — **no GIF had ever
been encoded here**, so every prior handoff had to list GIF export as "not
verified, needs a real browser". Both are now fixed.

**The build.** Upstream gifenc ships ESM + CJS only; neither loads as a classic
`<script>`. So `static/skribl/gifenc.min.js` is a global-publishing IIFE built
from the published tarball's own `src/` with esbuild. The exact reproduce command
(tarball URL, sha256, esbuild version, flags) is in a banner comment at the top of
the file — it is a build artifact, so treat that banner as the source of truth
rather than re-deriving it. It publishes `window.gifenc` with the same
`{ GIFEncoder, quantize, applyPalette }` shape the CDN loader did, plus the rest
of the library's named exports; nothing reads those, but they cost nothing.

Both templates now load it exactly the way they load mp4-muxer — Pad with `defer`,
Flip as a classic script before `flip.js`. **No JavaScript logic changed.** Both
files already read `window.gifenc` lazily behind an identical guard, so the only
JS edits were three stale user-facing strings (below).

**Zero off-origin requests now.** With both libraries vendored there is no
third-party script origin left on any surface — asserted, not assumed
(`verify_gifenc.py`). That was the last thing forcing a loose CSP, so the CSP work
in INTEGRATION §7 is unblocked.

**Copy fix.** Three strings told the user to check their internet connection for a
file now served from our own origin: `app.js`'s gate description, and `flip.js`'s
gate description + export chip. They now read "GIF encoder didn't load — try
reloading" and "GIF export needs gifenc.min.js", matching the toast `app.js` was
already showing. `flip.js`'s *share* failure message still mentions the connection
— that one is a real network POST, leave it.

### What the new suite actually proves (`verify_gifenc.py`, 35 assertions)
Unlike `verify_muxer.py`, which can only test the MP4 capability *gate* because
this Chromium has no avc1, this suite **runs the encoder for real**: it drives the
export UI, captures the download, and parses the GIF byte stream.

- **Flip, opaque** — valid GIF89a, 480x345 (the 480px-max-edge downscale), one GIF
  frame per page, NETSCAPE2.0 repeat 0, per-frame delay 8cs matching 12fps.
- **Flip, transparent** — the `rgba4444`/`oneBitAlpha` path: every frame carries
  the transparency flag and disposal method 2, and the bytes differ from the
  opaque encode (3569 vs 6218). **This closes "transparent GIF actually keying out
  on Flip"**, which has been on the not-verified list since it shipped.
- **The Pad** — its `exportGif` is IIFE-scoped, so the suite drives it through the
  UI: 19 frames off a recorded drawing, valid GIF89a, loops forever.
- **Degradation** — with the file blocked at the route level, `window.gifenc` is
  undefined, Flip still boots, the button disables itself, and no page errors fire.

**Still not proven in-sandbox:** MP4. That is unchanged from v103 — headless
Chromium exposes `VideoEncoder` but not avc1, so an actual MP4 still needs a real
Chrome. GIF was the half that could be closed here, and it is closed.

**One doc cleanup:** ROADMAP had a dangling `~~PLACEHOLDER~~` bullet claiming a
missing file 404s the share-card fallback. That is the og-card.png claim the v102
handoff already retracted as wrong (the file is in the repo; `app.py:266` redirects
to it) — the item's name had been struck out but its body left behind. Removed.

## v104 addendum — verified against the FULL repo, and one packaging bug found
Everything above was written from a changed-files zip. The complete repo has since
been checked, and this section records what could only be confirmed with the whole
tree in hand. **v104 was already merged cleanly**: all 18 shared files are
byte-identical to the deliverable, with no repo-side drift.

**The harness ran complete for the first time — 148/148, nothing skipped.** Every
previous run had `verify_muxer.py` SKIPping, because `mp4-muxer.min.js` is
repo-only and never travelled in the zips. With the real tree all nine suites run:
9 + 8 + 18 + 15 + 10 + 18 + 17 + 18 + 35.

Repo-only claims, now checked rather than asserted:
- **The vendored muxer really is 5.2.2**, so v103's rationale holds. It is
  jsDelivr's minified build of `mp4-muxer@5.2.2` — the provenance is in a banner
  comment at the top of the file. (Careful with grep here: Terser re-quotes string
  literals, so a double-quote-only search makes it look like symbols are missing
  that are actually present.)
- **`og-card.png` is present and valid** — 1200x630, the OG-recommended size. That
  closes the v102 retraction for good.
- **`README.md`'s `flask --app app.py init-db` is real** — `app.py:374` defines it.
- **`requirements.txt`** carries Flask, gunicorn, python-dotenv, Flask-SQLAlchemy,
  psycopg[binary] — matching what the notes above insist it must never lose.

### The bug: `.gitignore` silently excludes `lib/audioloop.js`
`.gitignore` line 17 was `lib/`, inherited from the standard Python packaging
template where it means the build directory at the repo root. But an unanchored
gitignore pattern matches a directory of that name **at any depth**, so it also
matched `static/skribl/lib/`. Measured on the real tree: `git add -A` staged 23 of
24 files, and the one silently dropped was `static/skribl/lib/audioloop.js` — the
shared audio library that both surfaces depend on, and which this document already
flags as load-bearing ("if it is missing, posting a cropped loop breaks too, not
just playback"). This is the v101 missing-`app.py` failure mode with a different
file.

**Fixed** by anchoring the rule to the repo root: `lib/` -> `/lib/` (and `lib64/`
-> `/lib64/` for the same reason). Verified both ways — `audioloop.js` is now
staged, and a genuine root-level `lib/` build directory is still ignored. `git add
-A` now stages 24 of 24.

Note the obvious fix does NOT work: adding `!static/skribl/lib/audioloop.js` leaves
the file ignored, because git cannot re-include a file whose parent directory is
excluded. Anchoring the original rule is the correct fix.

**Check your own clone**, since gitignore only affects *untracked* files — if the
file was committed before the rule existed it is tracked and was never at risk:

    git ls-files --error-unmatch static/skribl/lib/audioloop.js

An error there means it is untracked and would be absent from a fresh clone or a
deploy; `git add static/skribl/lib/audioloop.js` fixes it once the rule is anchored.

### `harness/` and `docs/` are now in the repo
They previously existed only inside handoff zips — 148 assertions and the entire
project history riding on files passed hand to hand, which is precisely how v101
lost `app.py`. Both directories are now part of the tree. The harness is dev-only
and does not affect the deploy; `Procfile` still runs `gunicorn app:app`.

## v103 — Flip loads the vendored mp4-muxer (template-only change)
The Pad already vendored mp4-muxer (`skribl_editor.html`, classic `<script src>`).
Flip did not — it pulled **the same library** from jsdelivr via `await import(...)`,
so the two surfaces ran **different versions**: vendored **5.2.2** on the Pad,
CDN **5.1.5** on Flip. And Flip's MP4 export was dead anywhere jsdelivr was
blocked. Flip now loads the vendored file.

**No JavaScript changed.** Both `app.js` and `flip.js` already read the identical
global with the identical guard (`window.Mp4Muxer` -> `.Muxer` / `.ArrayBufferTarget`),
so this is `skribl_flip.html` only: add the `<script src>` the Pad uses, delete the
mp4-muxer `import()`. gifenc stays CDN-only — it is ESM-only, so vendoring it needs
an npm fetch plus a wrapper or a global-publishing dist build. That is the
remaining half of INTEGRATION step 4.

New suite `verify_muxer.py` (17 assertions) proves Flip serves the muxer from our
own origin with zero jsdelivr requests for it, and that both surfaces expose the
same API shape.

**Scope limit, read before trusting this:** headless Chromium here exposes
`VideoEncoder` but does NOT support avc1 (`isConfigSupported` -> false), so the
H.264 encode still cannot run in the sandbox. `verify_muxer.py` tests the
capability GATE and the fallback, not the encoder — `pickAvcCodec` returns falsy,
`exportViaWebCodecsMp4()` returns `false` instead of throwing, and MediaRecorder
(vp9/webm) carries the export. That is the same path Firefox takes, which this
doc had listed as unverified, so it is worth having. **An actual MP4 still has to
be produced in a real Chrome before the export path is considered proven.**

**`static/skribl/mp4-muxer.min.js` is NOT in this zip.** It lives in the repo. The
zip carries changed files only; `verify_muxer.py` exits with a readable SKIP if
the file is absent. Copy it in from the repo to run that suite.

## v102 session summary
The three audio-payload bugs from the v101 QA writeup are fixed and pinned by new
harness assertions. Everything below was verified live in headless Chromium.

**Harness: 112 assertions across 8 suites, all green** (was 60 across 5).

### 0. `app.py` was missing from the v101 zip
The v101 archive shipped 31 files and none of them was `app.py` (no
`requirements.txt` either), so the harness could not start and the app could not
be deployed from it. Both are back in this zip at the app root. **Check they are
in the archive before handing off again** — every suite depends on `app.py`.

`requirements.txt` is the ORIGINAL, restored verbatim — do not regenerate it from
what the app imports. Two of its entries are invisible to this sandbox and easy
to drop by mistake: `gunicorn` is the WSGI server Render runs, and
`psycopg[binary]` is mandatory because `app.py` rewrites `postgresql://` to
`postgresql+psycopg://` (the `+psycopg` dialect is psycopg 3). The sandbox has no
`DATABASE_URL`, so it falls through to SQLite and neither is ever exercised here.
`python-dotenv` is what lets Flask auto-load `.env` locally. The file is
deliberately unpinned.

### 1. Flip's 20s loop cap is enforced at load (bug 1a)
`decodeForWaveform` set `trimEnd = audioDuration`, so a 42s file loaded as a 42s
"loop" and `updateTrimUI`'s 20s default was unreachable.
- New `MAX_LOOP_SECONDS = 20` sits with the trim state; the six bare `20`s in
  `flip.js` now reference it.
- `decodeForWaveform` and `ensureAudio`'s `loadedmetadata` handler default
  `trimEnd` to `trimStart + MAX_LOOP_SECONDS` (matching the Pad's `app.js:2227`).
- `updateTrimUI` gained a single clamp, so **load, draft restore, re-add and drag
  all funnel through one choke point** — the cap can't be bypassed by any path.
- **Decision taken** (this was the open question): the loop defaults to the FIRST
  20 seconds rather than the whole track. The Pad already did exactly this, all
  four drag handlers enforce it, and whole-track-until-touched made the cap
  invisible until a user dragged.

### 2. Flip posts the cropped loop, not the whole file (bug 1b)
`buildSharePayload` sent `data: musicData` — the entire uncut upload.
- Both WAV encoders moved into `lib/audioloop.js`: `audioBufferToWavDataURL` and
  `encodeWavFromChannels` are **byte-identical** to app.js's originals (golden
  diff, ignoring indent). `buildTrimmedLoopWav` joined them, differing only by
  reading its 4 fields from a passed state object — the same shape
  `buildLoopAudioBuffer` has used since v99.
- `app.js` lost 84 lines and gained 3 one-line shims; the golden diff shows
  nothing else changed. `flip.js` got the matching shim.
- `buildSharePayload` now crops, rebases trim to `0..loopLen`, and **drops
  `crossfadeMs`** (the fold is baked into the clip; re-applying it at playback
  would double it). Falls back to the full sample if the buffer isn't decoded or
  encoding throws, so a post never breaks here.
- Measured: a 42s WAV with an 8s loop posts **1.41 MB instead of 7.41 MB**, and
  the clip lands within 44 bytes of exactly 8.0s.
- The draft still keeps the full sample so the loop can be re-trimmed (asserted).

### 3. The Pad can no longer persist a garbage loop (bug 1c)
`audioEl._fileName` is set the moment a file is picked, but `trimEnd` isn't
written until `loadedmetadata` fires — and `trimEnd` starts at `0`
(`app.js:1714`). An autosave in that window serialized `{trimStart: 0,
trimEnd: 0}`, which came back on re-add as the 0.5s minimum-loop clamp and
rendered as "Loop 0:00–0:00" on the pending card.
- New `currentMusicMeta()` replaces the inline `musicMeta:` expression. While the
  duration is unknown it keeps a previously saved loop for the same file if there
  is one, and otherwise writes the name with **null** trim values, so load-time
  defaults apply instead of a bogus loop. The pending card then reads its
  existing "Loop saved" fallback.
- Flip does NOT need this: `decodeForWaveform` installs its 20s default *before*
  applying any saved meta, so a null never reaches the clamp.

### 4. A phantom bug, found and reverted — read this before re-chasing it
Mid-session the race suite showed a 42s file autosaving `trimEnd: 0.886`, which
looked like `loadedmetadata` firing with a provisional duration. A
`durationchange` handler was added to re-derive the loop when the real duration
landed. **It was wrong and has been reverted.** A direct probe of the load path
shows `audioEl.duration` goes `NaN -> 42` in one step (readyState 0 -> 4) and
never reports a partial value. The 0.886 was `setLoopToDrawingLength()` — the
intended "loop matches your drawing" default — firing because the test drew
before loading music. `verify_race.py` now covers that default explicitly so the
next person doesn't mistake it for corruption.

## What this is
**Skribl** is a Flask app with three surfaces that share one data model
("a Skribl is a list of frames; a classic replay is a 1-frame Skribl"):

- **Skribl Pad** — record a drawing as a timed **replay**, add a music loop +
  background image, post to a shareable link. Routes `/` and `/skribl-pad`.
- **Flip** — a **frame-by-frame animator**: draw pages, flip through them, export,
  post. Route `/flip`.
- **Player** — public playback at `/s/<id>` (plays replay *or* flip) + OG share
  card at `/s/<id>/card.png`.

## File inventory & deploy location
| File | Role | Location |
|---|---|---|
| `app.py` | Flask: routes, `POST /api/skribls`, player render, share card, rate limit | app root |
| `skribl_editor.html` | Pad template (Jinja) | `templates/` |
| `skribl_flip.html` | Flip template (Jinja) — loads external `flip.css`+`flip.js` (CDN module-loader still inline) | `templates/` |
| `skribl_player.html` | Player template (Jinja), loads `app.js` | `templates/` |
| `app.js` | Pad **and** player logic (audio DSP + WAV encoders shim `window.SkriblAudioLoop`) | `static/skribl/` |
| `flip.css` | Flip's extracted styles (v98) | `static/skribl/` |
| `flip.js` | Flip's extracted script (v98); audio DSP + loop cropping shim the lib | `static/skribl/` |
| `gifenc.min.js` | **v104** vendored GIF encoder (IIFE build; publishes `window.gifenc`) — Pad + Flip | `static/skribl/` |
| `mp4-muxer.min.js` | Vendored MP4 muxer (`window.Mp4Muxer`) — Pad + Flip. **Repo-only, never in the zips** | `static/skribl/` |
| `lib/audioloop.js` | Shared audio lib: `buildLoopChannels`, `buildLoopAudioBuffer`, **+ v102** `audioBufferToWavDataURL`, `encodeWavFromChannels`, `buildTrimmedLoopWav` | `static/skribl/lib/` |
| `styles.css` | Shared design system (all three surfaces) | `static/skribl/` |
| **Partials** (all `templates/`, all `{% include %}`d): | | |
| `_skribl_help.html` | "How it works" — Pad + Flip | `templates/` |
| `_skribl_export.html` | Export sheet (PNG / Video / GIF + bg toggle) — Pad + Flip | `templates/` |
| `_skribl_draw_drawer.html` | Draw drawer — Pad + Flip | `templates/` |
| `_skribl_image_drawer.html` | Image drawer — Pad + Flip | `templates/` |
| `_skribl_music_drawer.html` | Music drawer (waveform trim + fine-tune loop) — Pad + Flip | `templates/` |
| `_skribl_zoom_hud.html` | Zoom HUD / magnify pill — Pad + Flip | `templates/` |
| `_skribl_player_controls.html` | Player shell — Pad editor + Player | `templates/` |

Include counts: **Pad** all 7 partials; **Flip** 6 (no player shell); **Player** 1.

Loading: Pad + Player load `lib/audioloop.js` then `app.js` (+ `styles.css`).
Flip loads `styles.css` + `flip.css` + `lib/audioloop.js` + `flip.js`. As of v104
both `gifenc` and `mp4-muxer` are vendored classic `<script src>` tags on both
editing surfaces — **no ESM CDN loader, no inline `<script type="module">`, and no
off-origin request anywhere in the app.**

## Harness

<!-- HARNESS-COUNTS -->
**67 assertions across 1 suites, all green** on sqlite as of v245 (tree `4b6d9653ed5e`).

These totals are generated by `harness/stamp_docs.py` from `harness/LAST-RUN.txt` — never typed. `verify_docs.py` fails if any doc disagrees with the recorded run.
<!-- /HARNESS-COUNTS -->
Processes do NOT survive between tool calls in a sandbox, so the server and the
tests must run in one invocation. See `harness/README.md`.

| Suite | Covers | Count |
|---|---|---|
| `verify_audio.py` | post -> `/s/<id>` with sound + numeric crossfade seam | 9 |
| `verify_lib.py` | audioloop shared on every surface + load-order negative test | 8 |
| `verify_fix.py` | autosave quota fallback + regressions | 18 |
| `verify_amber.py` | amber media state + re-add cards | 15 |
| `verify_dots.py` | amber toolbar dots + card colours | 10 |
| `verify_loopcap.py` | **NEW v102** 20s cap + cropped post payload | 18 |
| `verify_race.py` | **NEW v102** Pad pre-decode autosave race | 17 |
| `verify_muxer.py` | vendored muxer + MP4 capability gate | 18 |
| `verify_gifenc.py` | vendored gifenc + **real GIF encode**, both surfaces | 35 |
| `verify_csp.py` | **NEW v105** CSP shape + enforcement + non-breaking | 31 |
| `verify_media.py` | **NEW v105** server-side media type/size validation | 24 |
| `verify_version.py` | **NEW v105** UI version label is single-sourced | 20 |
| `verify_ux.py` | **NEW v106** export format labels + undoable Clear all | 24 |
| `verify_pages.py` | **NEW v107** onion depth/tint, page reorder/copy-paste, redo | 28 |
| `verify_exopts.py` | **NEW v108** export size + page range, byte-verified | 23 |
| `verify_hold.py` | **NEW v109** drag-reorder + per-page hold & payload compat | 26 |
| `verify_canvas.py` | **NEW v110** canvas sizes, round-trip, help-text coverage | 21 |

The strongest single result: after moving the crossfade fold from playback-time
(player) to post-time (Flip), `verify_audio` reports **exactly the same numbers as
the v101 baseline** — `loopSeconds 2.88, seamDelta 0.01407, ctrlDelta 0.01062,
longest zero-run 0, ratio 1.32`. Same DSP, same inputs, same samples.

Note: `verify_amber.py` and `verify_dots.py` used to `shutil.copy` an uploaded
boom-bap WAV that no longer exists in the sandbox. Both now synthesize a 30s
stereo tone that fills the same role (base64 exceeds the ~4.5 MB localStorage
ceiling, which is what drives the amber state), matching `verify_fix.py`'s `BIG`.

## Not verified — still needs a real browser / deploy
- **A real MP4.** Unchanged and now the only export gap: this Chromium has
  `VideoEncoder` but not avc1, so the H.264 encode cannot run here at all.
  `verify_muxer.py` covers the gate and the WebM fallback; producing an actual MP4
  needs a real Chrome.
- WebCodecs MP4 across browsers: Chrome/Edge solid, Safari partial, Firefox ->
  WebM fallback (the fallback path itself is now pinned).
- Desktop button parity / translucent active state / GIF tray — pixel check.
- Audio smoke test on Pad + Flip + Player after the audioloop extraction (v99).
- ~~GIF export~~ / ~~transparent GIF keying out on Flip~~ — **both closed in v104**,
  verified by encoding and byte-parsing real GIFs on both surfaces.

### Retracted from the v102 draft of this doc
`og-card.png` was reported missing. **That was wrong** — it is present in the
repo and the share-card fallback works. It was absent from the v101 zip only.
This is the general hazard: **the handoff zips are not mirrors of the repo.** The
repo also has `Procfile`, `.env.example`, `.gitignore`, `README.md` and the
vendored muxer, none of which have been travelling in the zips. Copy changed
files into the repo; never replace the tree with a zip's contents.

## Deploy checklist — v110 delta
1. **CHANGED static**: `flip.js`, `flip.css`. `app.js` and `styles.css` untouched.
2. **CHANGED templates**: `skribl_flip.html` (canvas picker) and
   `_skribl_help.html` (shared — affects BOTH surfaces' help), plus cache-busts.
3. **Cache-busts**: `flip.js` -> **v110**, `flip.css` -> **v110**. `app.js` stays
   v109, `styles.css` v106, `lib/audioloop.js` v102.
4. **CHANGED**: `app.py` — `SKRIBL_VERSION` -> `"v110"`.
5. **No payload change.** `canvasSize` was already in the format and already
   honoured by the player, so old and new Skribls interoperate untouched.

## Deploy checklist — v109 delta
1. **CHANGED static**: `flip.js`, `flip.css`, and `app.js` (the player's flip
   timing). `styles.css` and `lib/audioloop.js` untouched.
2. **Cache-busts**: `app.js` -> **v109**, `flip.js` -> **v109**, `flip.css` ->
   **v109**. `styles.css` stays v106.
3. **CHANGED**: `app.py` — `SKRIBL_VERSION` -> `"v109"` only.
4. **First payload change since the frame format**, but additive both ways: old
   Skribls play unchanged in the new player, and new ones degrade to uniform
   timing in an old player. **No migration, no version bump in the payload.**
   `schemaVersion` deliberately stays 2 — bumping it would imply a breaking change
   that hasn't happened.
5. `app.js` and `flip.js` should deploy together: a held Skribl posted from a v109
   Flip would play at uniform timing on a v108 player. Not broken, just not what
   the author drew.

## Deploy checklist — v108 delta
1. **CHANGED static**: `flip.js` (exDims/exRange + all three encoders), `flip.css`
   (options styling). `app.js` and `styles.css` are **untouched** this round.
2. **CHANGED templates**: `_skribl_export.html` (Flip-only options block) and the
   cache-bust bumps. Note the partial is shared — the block is inside
   `{% if kind == 'flip' %}`, so the Pad's sheet is unchanged.
3. **Cache-busts**: `flip.js` -> **v108**, `flip.css` -> **v108**. `app.js` stays
   v107, `styles.css` stays v106, `lib/audioloop.js` stays v102.
4. **CHANGED**: `app.py` — `SKRIBL_VERSION` -> `"v108"` only.
5. **No payload change**, no new dependencies, no migrations.

## Deploy checklist — v107 delta
1. **CHANGED static**: `app.js` (clear redo + toast hide-timer fix), `flip.js`
   (onion depth/tint, `movePage`, copy/paste), `flip.css` (new controls).
   `styles.css`, `lib/audioloop.js` and the vendored libraries are untouched.
2. **CHANGED template**: `skribl_flip.html` — the onion controls group, plus
   cache-bust bumps. The editor and player templates change for cache-busts only.
3. **Cache-busts**: `app.js` -> **v107**, `flip.js` -> **v107**, `flip.css` ->
   **v107** (its first bump since v98). `styles.css` stays v106, `lib/audioloop.js`
   stays v102.
4. **CHANGED**: `app.py` — `SKRIBL_VERSION` -> `"v107"` only.
5. No new dependencies, no migrations, **no payload change**.

## Deploy checklist — v106 delta
1. **CHANGED static**: `app.js` (toast action + undoable clear + WebM label),
   `flip.js` (`expectedVideoFormat`), `styles.css` (`.toast-action`).
   `lib/audioloop.js`, `flip.css` and the vendored libraries are untouched.
2. **Cache-busts**: `app.js` -> **v106**, `flip.js` -> **v106**, `styles.css` ->
   **v106** in all three templates. `flip.css` stays v98, `lib/audioloop.js` stays
   v102 — bump only what changed.
3. **CHANGED**: `app.py` — `SKRIBL_VERSION` -> `"v106"` only. No behaviour change.
4. Templates change only for the cache-bust bumps, so the v105 rule still holds:
   ship `app.py` and the templates together.
5. No new dependencies, no migrations, no `requirements.txt` edit.

## Deploy checklist — v105 delta
1. **CHANGED**: `app.py` only, plus a `nonce="{{ csp_nonce }}"` attribute on the
   single inline `<script>` in `skribl_editor.html` and `skribl_player.html`, and
   the version label in `skribl_editor.html` (now `{{ skribl_version }}`).
   **Release ritual: bump `SKRIBL_VERSION` in `app.py`.**
2. **NO static changes.** `app.js`, `flip.js`, `lib/audioloop.js`, `styles.css`,
   `flip.css` are all untouched — **do not bump any cache-bust**. They stay at
   v104 / v102 / v101 / v98 respectively.
3. **The templates and `app.py` must deploy together.** The nonce attribute is
   meaningless without the header, and — more importantly — the header without the
   attribute means the config scripts are BLOCKED and both editing surfaces break
   (`window.SKRIBL_MODE` never gets set). There is no half-deploy that works.
4. **New env knobs**, all optional with safe defaults (see `.env.example`):
   `SKRIBL_CSP` (`on` | `report-only` | `off`), `SKRIBL_MAX_AUDIO_BYTES`,
   `SKRIBL_MAX_IMAGE_BYTES`.
5. **If you want to stage it**, deploy once with `SKRIBL_CSP=report-only`, watch
   for violation reports, then flip to `on`. The harness says enforcing is clean in
   Chromium; report-only exists for the browsers it can't test.
6. Nothing else changed: no new dependencies, no migrations, no `requirements.txt`
   edit. `Procfile` still runs `gunicorn app:app`.

## Deploy checklist — v104 delta
1. **NEW static**: `static/skribl/gifenc.min.js`. It must ship, or GIF export
   disables itself on both surfaces. It ships in *this* zip because the repo does
   not have it yet; from v105 on it is a repo-resident vendor file like
   `mp4-muxer.min.js` and need not travel again.
2. **CHANGED static**: `app.js`, `flip.js` — three user-facing strings only, no
   logic. `lib/audioloop.js` is **unchanged** this session.
3. **CHANGED templates**: `skribl_editor.html` + `skribl_flip.html` swap the gifenc
   CDN module for the vendored `<script src>`; `skribl_player.html` is a cache-bust
   bump only (it loads `app.js`, which changed).
4. **Cache-busts**: `app.js` and `flip.js` -> **v104** in all three templates.
   `lib/audioloop.js` stays **v102**, `styles.css` stays v101, `flip.css` stays v98
   — bump only what changed.
5. **Deploy together / load order** (unchanged but now load-bearing for more):
   `lib/audioloop.js` MUST load BEFORE `app.js` (Pad/Player) and BEFORE `flip.js`
   (Flip). It now carries the WAV encoders as well as the loop DSP, so if it is
   missing, posting a cropped loop breaks too, not just playback. `flip.js` is a
   classic `<script src>` at end of `<body>` — keep it non-`defer`.
6. `app.py` must ship (it was absent from v101's zip).
7. Nothing else changed: `styles.css`, `flip.css`, `lib/audioloop.js` and all 7
   partials are untouched this session.
8. **CSP is now unblocked** (INTEGRATION §7): there is no off-origin script left,
   so `script-src` no longer needs `cdn.jsdelivr.net`. Inline `<script>` blocks
   still exist (the `SKRIBL_MODE` config block, and Jinja-injected data), so a
   strict policy still needs nonces or hashes — vendoring removed the third-party
   origin, not the inline sources.

## Data contract
`POST /api/skribls` -> `{id, url:"/s/<id>"}`. Frame shape:
`{strokes, strokeGroups, baseSnapshot, background:{color}, photo|null, music|null}`,
media on **frame 0**. `music`/`photo`/`background`/`canvasSize` must be objects|null;
`frames`/`strokes`/`strokeGroups` must be lists. `normalizeSkribl()` sets
`playbackMode:'flip'` for multi-frame and surfaces frame-0 media.

**As of v102 both surfaces post an already-cropped loop**: `music.data` is the
loop itself, `trimStart` is 0, `trimEnd` is the loop length, and `crossfadeMs` is
absent because the fold is baked into the samples. A player must NOT re-apply a
crossfade to posted audio.
