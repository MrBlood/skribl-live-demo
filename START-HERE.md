# START HERE — Skribl v219 session primer

## Next session: read this block first

    result       see harness/RELEASE.md — generated, never typed here
    tree hash    see harness/RELEASE.md — generated, never typed here
    files        see SHA256SUMS — the command below prints the count

Nothing in this block is a number, deliberately. It used to carry an assertion
total, a suite count, a skip count and a file count, and carried all four
unchanged through three builds that changed every one of them. `verify_docs.py`
caught the suite count only because that one happened to be checked against the
directory listing. A number typed here is a number that goes stale silently.

Verify before believing anything in prose, including this file:

    cd skribl-v222 && sha256sum -c SHA256SUMS | grep -c ': OK'    # expect 208
    grep -m1 'tree hash' harness/RELEASE.md
    python3 -c "import sys;sys.path.insert(0,'harness');import release_run as r;print(r.tree_hash())"

**What a visitor downloads on a shared link, across the last session:**

    JavaScript   329,159 -> 231,106 B
    HTML          56,716 ->   7,989 B
    total        385,875 -> 239,095 B   (-146,780, 38%)

**What v199 changed, all of it measured by `verify_player_isolation.py`:**

    JavaScript   234,611 -> 155,843 B   serve-time comment strip
    CSS           36,612 ->  32,515 B   splitting INSIDE @media blocks
    HTML                     8,289 B    unchanged
    parsed       279,512 -> 196,647 B   on the wire (gzip) 48,309 B

Neither change moved a byte of source. `skribl/jsstrip.py` removes comments from
the RESPONSE — the files on disk keep every word, which is the only reason this
was allowed at all — and `harness/tools/cssgraph.py` now classifies rules inside
a media block instead of keeping the whole block whenever one rule matched.
`verify_jsstrip.py` is the gate on the first (Chromium compiles and evaluates
every case; the lexer checking its own output proves nothing) and
`verify_cssplit.py` on the second (eleven scenes, pixel-identical).

### Environment traps, in the order they will bite

* `apt-get update` fails outright until the blocked nodesource repo is moved
  aside: `mv /etc/apt/sources.list.d/nodesource.list /tmp/`. Then install
  postgresql, start it, create the `skribl` role and database.
* `pip install -r constraints.txt --require-hashes --break-system-packages`, and
  `python3 -m playwright install chromium`.
* **PostgreSQL dies between tool invocations.** Start it in the SAME invocation
  as whatever needs it, and check `pg_isready`.
* **Background processes do not survive between invocations**, and one
  invocation is capped well below the ~25 minutes a full aggregate needs. That is
  why `release_run.py` checkpoints:

      python3 harness/release_run.py --restart --budget 160   # first slice
      python3 harness/release_run.py --budget 160             # repeat ~5x

  It re-verifies the frozen tree hash on every resume and aborts if the tree
  changed, so the guarantee is stronger than a single-process run. The checkpoint
  is deleted on completion.

### Eight suites could fail silently — fixed at this seal

`run_harness.sh` takes ok/FAIL from a suite's **exit code**. Eight suites
(`verify_amber`, `verify_audio`, `verify_dots`, `verify_feed`, `verify_fix`,
`verify_lib`, `verify_privacy`, `verify_seam`) printed their failures and then
exited 0. The runner reported them as `ok`, and a full aggregate would have been
recorded as PASS with a failed assertion inside it. `verify_docs` was the ninth,
caught in the act: it printed `32/33 passed FAILURES: ...` and the runner said
`ok`.

All nine now end with `sys.exit(1 if bad else 0)`.

**This is very likely what the `verify_amber` "flake" earlier in the session
was.** It was reported as a crash by a parser bug that has since been fixed, and
it would ALSO have been reported as ok had it merely failed. Two independent
reporting holes over the same suite. Do not trust any green run recorded before
this seal for those eight suites.

The lesson generalises: **a suite's failure has to travel through the channel the
runner actually reads.** Printing it is not reporting it.

### The next step, and the honest distance

`app.js` is 214,132 B. The player executes about 88 KB of it; the rest never runs
there. Reaching the 153,600 target needs nearly ALL of that removed — the gap and
the dead weight are the same size, so there is no slack.

The cheap techniques are exhausted:

* **Self-contained IIFEs** — done: `editor_export`, `editor_post`, `editor_menu`.
* **Wiring extraction** (move STATEMENTS, leave functions and state) — done for
  both drawers: `editor_music`, `editor_photo`.
* **What remains is functions**, and they cannot be relocated the same way
  because shared paths still NAME them. `drawZoomWaveform` (4,457 B) is the
  clearest case: dead on the player, but `loadSkribl` names it, so it stays.
  Moving them means restructuring call sites — dependency inversion, not
  relocation.

**AND THAT RESTRUCTURING STILL DOES NOT REACH 153,600.** Measured since:
move every editor-only function out of `app.js` — all 71,633 B, including the
~34 KB the restructuring exists to unpin — and the player lands at 159,473 B,
still 5,873 over. What is left is not functions; ~88 KB of `app.js` is top-level
wiring and comments.

**v199 CORRECTION — the comments were never the player's to carry.** That whole
argument treated comment text as weight that had to be MOVED, and it does not:
`skribl/jsstrip.py` strips comments at serve time, out of the response and never
out of the source. The player now parses **155,843 B**, down from 234,611,
without a single function relocated and without a separate entry point. So the
paragraph above is answering a question that is no longer the binding one.

It is also not a clean win for the opposite claim. Stripping alone lands
**2,243 B OVER** the 153,600 target — not the 141 B a predicted 153,741 implied;
that figure is not reproducible and the difference is mostly indentation
accounting. `verify_jsstrip.py` asserts the gap so that neither this document's
old conclusion nor that prediction can be read as settled. What remains is a
2,243 B question, which is a much smaller thing than `app.js` ceasing to be the
player's file.

The AST step that `docs/REFACTOR-v132.md`
prescribed as the way to de-risk this was built (`harness/tools/refgraph.js`)
and DISPROVED: it fails its own superset gate and would move all four functions
the v132 attempt got wrong. The v132 failure was load order, not
classification. Read that section before planning anything here.

**The rule that governs all of it:** a binding declared in an editor-only file
does not exist on the player, so any player code touching it throws. Wiring moves
because nothing names it; state and shared functions cannot. Ask which direction
the reference runs.

### Before touching the loop engine

The isolation fixture carries real audio and asserts playback through an analyser
tap. Keep it that way. A silent fixture made Chrome's coverage profile report
every loop-building function as unused, and acting on that would have shipped a
player that cannot play music — with the suite calling it green.

---

**`FOR-THE-REVIEWER.md` is written for anyone auditing this archive** — it
states plainly what is and is not verified, and what to attack first.

**`V219-CHANGES.md` is the changelog for everything since the v214 seal**, and
every number in it was re-measured against this tree rather than carried
forward. Read it, this file, and `ARCHIVE-README.md` before changing anything. Everything below was
verified by running it, not by reading the code.

**Upload the current sealed zip (`skribl-v214-sealed.zip`) alongside this file.**
Unzip it; it produces a folder `skribl-v214/`. `git init` goes INSIDE that
folder, not above it. (Historical sections below narrate v199-era work; the
numbers in prose are that era's, not this build's.)

---

## What this is

Skribl is a browser drawing/animation tool — **Pad** (records a drawing and
replays it with its timing), **Flip** (frame-by-frame animation) and a
read-only **Player** — packaged as a Flask blueprint to drop into a social
platform.

    SKRIBL_VERSION   see skribl/core.py — the archive name derives from it.
                     This line used to hand-type it, and read v191 while the
                     code said v211: four releases stale, in the file whose
                     whole opening section is about numbers going stale
                     silently. Read the constant.
    client assets    v131      plus six integration edits, the v142-v179 work,
                     and the v215-v219 UI pass (see V219-CHANGES.md)
    harness          see harness/RELEASE.md — the count is generated, and a
                     hand-typed one is exactly what drifts
    migrations       6 Alembic revisions
    last run         see the stamped stanza below — it is generated, and a
                     hand-typed total is exactly what drifts
    tree hash        see the generated stanza below — NEVER typed here
                     (a hand-typed hash in this file is what made an
                     external reviewer distrust the whole archive)

**Release evidence lives in `harness/RELEASE.md`** — every suite on disk,
on one frozen tree, generated by `harness/release_run.py`. The stanza below is
narrower: it records only the LAST `run_harness.sh` invocation, which is a batch,
not the release. When the two disagree it is because they answer different
questions; RELEASE.md is the one to quote.

**The last recorded run** — generated by `stamp_docs.py`, never typed:

<!-- HARNESS-COUNTS -->
**PASS WITH SKIPS — 2938 assertions across 68 suites, none failing, 1 skipped** on sqlite as of v222 (tree `4162f6bcb3f4`).

These totals are generated by `harness/stamp_docs.py` from `harness/LAST-RUN.txt` — never typed. `verify_docs.py` fails if any doc disagrees with the recorded run.

Skipped in that run: verify_mp4.py. A skipped suite contributes zero assertions and is not evidence of coverage.
<!-- /HARNESS-COUNTS -->

**The deployed runtime is pinned to Python 3.12** (`.python-version`, mirrored
by `PYTHON_VERSION` on the Render service). `constraints.txt` is a hash-locked
cp312 environment and the recorded evidence is produced on the same interpreter,
so the numbers in `harness/RELEASE.md` describe what production runs rather than
a configuration nobody has. Render's default Python depends on when the service
was created and moves over time; unpinned, the build resolves `requirements.txt`
fresh and runs versions no assertion ever exercised. `verify_docs.py` fails if
the pin, the lock and the interpreter running the harness disagree.

**Verify the archive first, in one command:**

    cd skribl-v222 && sha256sum -c SHA256SUMS | grep -c ': OK'      # expect 208
    # Compare against the manifest, not against this number — the manifest is
    # generated, this line is typed, and typed numbers are what drift. The
    # explanation that used to sit here listed which files had joined since
    # some earlier count, and was itself three sessions stale; the manifest
    # already says which files exist, so the prose said nothing the tree did
    # not, less accurately. `verify_docs.py` checks this number against
    # SHA256SUMS on every run.

---

## The live demo

`skribl-live-demo.onrender.com` — a Render Starter web service ($7/mo) deployed
from GitHub (`MrBlood/skribl-live-demo`, branch `main`), backed by a paid
Postgres Basic instance ($6/mo), running the `inline` media backend.

**The deployed code is usually BEHIND this archive.** The owner deploys by
applying `docs/v179-seg-hidden.patch` (3 files) or dropping in the whole tree. Ask what
is actually live before diagnosing anything.

**Two operational facts learned the hard way:**

* A free Postgres instance expired mid-session and every `POST /api/skribls`
  returned 500 with `failed to resolve host 'dpg-...'`. It looked exactly like
  a broken client, and three client-side theories were chased before a server
  log settled it in one line. **Check the server log first.**
* **HISTORICAL — this is the incident that caused the pin, not the current
  state.** Render was building on **Python 3.14** while `constraints.txt`
  carried cp312 hashes, so production resolved `requirements.txt` fresh and was
  NOT running the versions the harness tested. **Fixed by pinning:**
  `.python-version` holds 3.12 and `PYTHON_VERSION` mirrors it on the Render
  service — see "The deployed runtime is pinned to Python 3.12" above, which is
  the current statement. `verify_docs.py` fails if the pin, the lock and the
  interpreter running the harness ever disagree again.

  Two statements about the runtime appeared in this file at once, one current
  and one historical, with nothing marking which was which. An external review
  flagged it: *"Both statements cannot describe the same current deployment."*
  It was right, and the fix is the label rather than a change of fact — CURRENT
  STATE and PAST INCIDENTS must be distinguishable at a glance.

---

## Decisions that are the user's, not the assistant's

**The migration chain collapse is CLOSED.** It required that no database had
run v135-v141. The live Postgres is stamped at head `f0a3d81b47e2`. Do not
propose collapsing it again.

**THE PAD/FLIP GUARD ASYMMETRY IS DELIBERATE.** Pad confirms before leaving for
Flip; Flip does NOT confirm on the way back. That is not an oversight and should
not be "fixed". Pad's autosave keeps strokes but NOT media — photo and audio
bytes never fit in localStorage, which is why the status pill reads *"Saved
without media"* whenever either is attached — so leaving Pad loses the photo and
the music. Flip persists pages, music and the background image, so a confirm
there could only ever be a false alarm. Pad's guard fires on
`photoBg || currentAudioBuffer`, not on "there is a drawing": a confirm that is
usually wrong is one people learn to dismiss unread, and then it fails on the
occasion that mattered.

**360px IS THE DESIGN TARGET; 320px IS THE SAFETY NET.** 360 must work properly
on one row — it is a very common Android width, so a two-row bar there is not a
rare fallback. 320 is Display Zoom on a modern iPhone, an accessibility setting
rather than a legacy device, so it must degrade rather than break. The two
surfaces degrade DIFFERENTLY and both are correct: Pad wraps, Flip scrolls
(`flip.css` sets `flex-wrap: nowrap; overflow-x: auto` below 560px on purpose).
`verify_layout.py` asserts that every control stays REACHABLE, not that a
particular mechanism is used — an earlier version asserted no-overflow and would
have failed Flip's scroll row as though a deliberate decision were a defect.

**EVERY REPAINT MUST GO THROUGH `makeStrokeCompositor`.** A see-through stroke
painted segment by segment stacks its own overlaps at every captured point —
measured, one 22%-alpha stroke: alpha spread 153 painted directly against 50
composited once. `selRepaint` was the last repaint in the editor passing the raw
`drawDot`/`drawLine` painters straight to `replayTimelineToCanvas`, and
`setTool()` calls it on EVERY tool change, so simply picking the eraser re-beaded
the whole canvas. Preview, playback and all three export paths already routed
through the compositor. If you add a repaint, route it through the compositor or
branch on `strokeLayersOn()` — never neither.

**THE CANVAS LOCK AFTER A TAKE IS DELIBERATE — do not "fix" it.** When a take
ends, `updateCanvasLockCue()` sets `cursor: not-allowed` and the canvas is not
drawable until you Record again or Clear. This looks like a dead end and is not:
it is the multi-take model, and `endRecordingTake()` says so in a toast —
*"Take saved — Record again to add more to this Skribl, or Play to preview."*
An external design pass in v215 read the lock as a bug and came close to
recommending its removal, which would have turned every stray tap after a take
into recorded timing. The round-trip through Record is the cost of knowing when
the clock is running. If it is ever revisited, the narrower change is to let
drawing on a locked canvas START the next take — same model, no round-trip —
rather than removing the lock.

**Visibility defaults to `unlisted`,** and the migration backfilled every
existing post as `unlisted`. The platform must send `"visibility": "public"`
explicitly or posts appear in no feed, silently. Leave the backfill alone.

**v140's recall framing is confirmed correct** — no database ran the v140 copy
of `f0a3d81b47e2` at `BATCH = 500`.

**The CSS ratchet decision has a FALSE PREMISE and needs restating before it can
be decided.** It has been carried as "set at exactly the current size, so it has
no headroom by construction". That was true when `player.css` did not exist and
the player linked the whole of `styles.css`. It does exist: `CSS_RATCHET` is
123,283 and the player links 32,515, so the mechanism has **90,768 B of
headroom** — the same inert state the JS ratchet was in when it was reading
gzipped lengths, arrived at a different way. Two candidate numbers, and this is
a decision, not an edit: 32,515 (today's value, the convention the JS ratchet
and the comment beside `CSS_RATCHET` both follow) or something with deliberate
slack. It was left alone this session because the number is listed here as the
user's; leaving it alone made it staler, which is worth knowing when deciding.

---

## What was built in v142-v179

Client work, all covered by suites that drive a real browser:

* **Flip sends a typed title and caption** — it hardcoded `'Flip animation'`.
* **Stylus pressure** on both editors, scaled into the existing per-point
  `size` rather than a new field the player cannot read.
* **Export sheet**: Size/Pages had NO CSS at all; plus a Loops control, because
  video silently exported two passes.
* **Help drawer search** across ~50 entries, with derived section counts.
* **Your Skribls** (`lib/posted.js`) and **Report a problem** (`lib/report.js`,
  captures JS errors — it loads first so it can see failures in the editors).
* **Canvas presets shared by both editors** (`lib/canvassizes.js`); Pad used to
  inherit the viewport, so a drawing's shape depended on window width.
* **Styled tooltips** (`lib/tooltip.js`) and **first-use hints**
  (`lib/hints.js`) — native `title` cannot be styled at all.
* **A pixel-snapped canvas grid** with a sub-grid at every size.
* **Move artwork** — see below. Its transform bar now states its own
  geometry, and its offset readout accepts typed coordinates.

---

## Move artwork — the newest feature, and what it sets up

`Artwork` in Flip's page bar enters a mode where dragging the canvas moves the
whole page's drawing. The page bar is REPLACED by a transform bar (offset
readout, This page / & after, Reset, Done). Escape cancels; Done commits.

Design notes worth keeping:

* It is a PAGE operation, so it lives with Copy/Hold/Delete, not with
  Pen/Eraser — and the tool row is full on a phone anyway.
* **Undo stores the inverse offset, not a snapshot.** A translation is exactly
  reversible. Not bit-exact (float), so `verify_move.py` asserts to 1e-6.
* **`actionLog` records the order of undoable actions** so undo after
  "draw, move" undoes the MOVE. Flip's undo otherwise just pops stroke groups.
* The offset applies to a working COPY of the original points, so a long drag
  cannot drift and Reset lands exactly.
* The drag is measured in canvas units (`CW / rect.width`), not screen pixels.

**Selection — moving PART of a drawing — reuses all of this**: the mode, the
bar, the readout, Reset, Done, Escape and the undo mechanism. Only hit-testing
and a selection overlay are new. That was the argument for building the
whole-page move first, and it is the natural next feature.

---

## Closed since the v179 archive was cut

* **`[hidden]` works everywhere now.** `styles.css` carries
  `[hidden] { display: none !important; }`. The UA rule loses to any author
  rule, so `el.hidden = true` drew nothing for 380 elements on Flip and 366 on
  Pad — the page bar rendered 55px tall throughout Move artwork's life while
  reporting `hidden === true`. Four one-off `.thing[hidden]` rules had been
  written before anyone looked for the general case.
* **Segmented controls state a height.** `--seg-h` was declared four times and
  read nowhere, so a `.seg` inherited its height through `font: inherit` and
  followed the VIEWER'S font: 20px headless, 23px on the owner's Mac, while
  `.pb` matched exactly. `.seg` now reads `var(--seg-h)` with NO fallback, so
  an unmeasured control keeps `auto` and opting one in is deliberate.
  `.mb-scope` and `.mb-offset` are 30px; the export segs 32px.
* **The offset readout takes typed coordinates.** Click it, type `40, -12`.
  Same moveDx/moveDy as a drag, so the same Reset, Done and single undo entry.
* **Skribl no longer steals a host application's homepage, and `docs/INTEGRATION.md`
  is now a real guide.** Both came out of the first actual DROP-IN TEST: a
  throwaway Flask host app, built from the docs, that is not `app.py`.
  The blueprint registered `GET /` unconditionally — a second copy of the Pad
  editor, there so the standalone demo had a landing page. Flask resolves
  duplicate rules by registration order and the blueprint registers first, so
  **mounting Skribl silently replaced the host's front page.** No error. It is
  now `create_blueprint(index_route=False)` by default; `app.py` opts in.
  Two more integration facts that were true but undiscoverable: a host's
  `db.create_all()` creates **nothing** without
  `skribl.models.attach_to_metadata(db.metadata)` — no tables, no error — and
  `docs/INTEGRATION.md` was a v98–v136 planning record that opened by admitting
  its own signature was obsolete, while `README.md` pointed integrators at it.
  The plan is preserved as `docs/INTEGRATION-HISTORY.md`; the guide is rewritten
  around a copy-pasteable example that was executed, not imagined.
  `harness/verify_integration.py` (14 assertions, no browser, seconds) pins all
  of it, including the negative controls — install a visibility policy, prove it
  changes the outcome, clear it, prove the default returns.
  One limitation is now DECLARED rather than silent: the feed filters
  `visibility == 'public'` in SQL and never consults the host policy, because a
  Python predicate over a keyset-paginated query would break the pagination. A
  policy-refused post can appear in the feed as metadata; no payload or image
  leaks. Fixing it properly needs a `feed_filter` seam contributing SQL.
* **Loop trim clamping is extracted to `lib/looptrim.js`, and it found a second
  real bug.** The 20-second cap was a named constant on Flip
  (`MAX_LOOP_SECONDS`, nine uses) and a **bare `20` on Pad, eight times, with no
  constant in the file** — so changing the cap meant one edit on one surface and
  eight on the other, with nothing failing if the second was missed.
  **Flip re-clamped the cap inside `updateTrimUI`**, with a comment calling it
  "the single choke point ... so the <=20s invariant can't be bypassed".
  **Pad had no such line**: it enforced the cap on drag and nudge ONLY, so a
  loop arriving any other way — a load, a draft restore, a re-add — kept
  whatever length it came with, and travelled in the payload. Measured: a 60s
  loop through `updateTrimUI` stayed 60s on Pad and became 20s on Flip. Pad now
  has the same choke point and both read the shared constant.
  The clamp rule itself existed in **six copies** across the two files, in two
  behaviours: `'constrain'` (the dragged handle stops at the cap) on the main
  track, `'slide'` (the OTHER end is pushed, so the window slides) on the zoom
  track and nudge. **Pad and Flip are identical about this, path for path**, so
  it is a design inconsistency faithfully duplicated, not drift — the mode is
  now an explicit named argument at each call site rather than hidden inside
  six copies of the arithmetic. Verified against all six transcribed sites
  across 140 scenarios: zero disagreements.
  **The player needed the module too** and the harness caught it: `updateTrimUI`
  lives in `app.js`, which serves the player, so the player threw
  `Cannot read properties of undefined` until `looptrim.js` was added to its
  template. Any client constant `app.js` reads has to load on THREE templates,
  not two.
* **Photo fit geometry is extracted to `lib/photofit.js`, and extracting it
  found a real bug.** Pad drew the background with `drawPhotoFitted`, Flip
  computed it with `photoRect`, and the PLAYER used Pad's copy — three call
  sites, two implementations. They agreed on cover and contain and disagreed on
  the third mode's NAME, which is why the shared partial carried
  `data-fit="{{ 'fill' if kind == 'flip' else 'stretch' }}"`: the markup had
  been bent to fit two vocabularies. flip.js posts
  `fit:(photoFit==='fill'?'stretch':fit)`, so **'stretch' is what the player and
  the database see** — but Flip's restore whitelist was
  `['cover','contain','fill']` and `photoRect` special-cased only `'fill'`.
  **Flip could not read the value Flip writes.** Measured on a 100x50 image
  before the fix, `fit='stretch'` returned `[-204,0,1224,612]` — byte-identical
  to cover — while `'fill'` returned `[0,0,816,612]`, and the fit row showed no
  active button at all. The lib treats `'fill'` as an alias of `'stretch'`, and
  Flip normalises at both entry points, so the value round-trips. Neither
  surface's PERSISTED vocabulary was changed: that is a decision about live
  data, not a refactor. The template conditional and the split vocabulary are
  still there, deliberately — see the open question below.
  Verified behaviour-preserving by comparing the lib against BOTH pre-extraction
  implementations across 405 combinations of size, canvas, offset, zoom and
  fit: zero disagreements. `lib/photofit.js` loads on the editor, Flip AND the
  player — the player draws photos through `app.js`, so omitting it there would
  have left viewers a blank background.
* **`lib/colorselect.js` is now covered by `verify_parity.py`.** It is the
  fifth shared-controller extraction (after `eyedropper`, `recentcolors`,
  `segslider`, `smoothing`) and it entered the archive with no parity
  assertions naming it. The suite already asserted the BEHAVIOUR it
  implements — hex validation, case normalisation, exactly one active swatch,
  on both surfaces — and all of that still passed when Flip was given back its
  own private copy of the logic. Behavioural parity says the copies agree
  today, not that there is one copy. Nine assertions now pin the extraction
  itself: one module, one URL including its content hash, one implementation,
  and — the load-bearing one — each editor's setter is spied on to prove it
  actually CALLS the module. Only that last assertion caught the re-inline;
  `verify_ux.py`'s source grep for `classList.toggle('active'` passed 130/130
  against a copy that merely wrote `classList["toggle"]("active"`.
* **The loop magnifier is NOT unstyled** — a claim made and withdrawn this
  session. `app.js` injects its CSS at runtime, including the
  `position: relative` the seg pill needs. Grep both stylesheets AND the
  injected `<style>` before believing a component has no rules.

## Closed after the v184 dotfix

* **The move-offset field summoned the wrong keyboard.** `#mbOffsetInput` takes
  BOTH coordinates in one box (`"40, -12"`) and declared `inputmode="numeric"`,
  which on a phone offers digits only — no comma, and on most keyboards no minus,
  so a negative offset could not be typed at all. `decimal` is not the fix; that
  adds a decimal POINT, not a separator. It is `text` now. The parser needed no
  change: `parseOffsetEntry()` already accepts a comma or a space between the two
  numbers plus a leading minus and decimals, and `verify_move.py` now asserts
  both halves — the attribute, and that the parser takes every form the fuller
  keyboard allows while still rejecting junk. Mutation-tested: restoring
  `numeric` fails the assertion.

* **The play scrubber's shape is no longer unverified — and it was correct.**
  It had never been seen rendered. Driving Pad through draw → stop → play and
  measuring the real shown state gives, at 1280x900 and at 390x844 alike: inset
  **24px at both ends, exactly `--r-frame`**, flush to the canvas bottom (gap 0),
  spanning wrap width less 48, radius reaching past half the height so the ends
  read round. Nothing needed adjusting. `verify_scrub.py` (17) pins it, and its
  FIRST assertion is the negative control: at rest the bar is genuinely not laid
  out, because `positionScrub()` returns early on `hidden` — so an element forced
  visible measures 0 wide and reads as catastrophic misalignment that is entirely
  an artifact. A gate assertion also refuses to compare insets until a real
  replay has actually shown the bar; a symmetric zero is a broken probe, not
  agreement. Mutation-tested: zeroing `_inset` fails four assertions.

* **`positionPlayScrub` does not exist.** The function is `positionScrub()`
  (`app.js`). The name was wrong in the `styles.css` comment that points at it
  and in the handoff, so anyone grepping for it found nothing. Corrected.

* **`verify_deletion_foundation.py` is in `harness/` now, and it crashed on
  arrival.** It resolved the repository root with `os.path.abspath(".")`, but
  `run_harness.sh` does `cd $ROOT/harness` before invoking a suite — so `from app
  import ...` raised `ModuleNotFoundError` and the suite reported zero assertions
  rather than eight. It anchors on `__file__` now, matching `verify_storage.py`.
  8/8 on PostgreSQL with the local media backend; it needs BOTH
  `SKRIBL_MEDIA_BACKEND=local` and a Postgres `DATABASE_URL`, and skips cleanly
  without them.

* **Hand-typed counts that had drifted are gone rather than corrected.** Three
  documents quoted three different line counts for `app.js` and none matched the
  tree; four places hand-typed the suite count. Replacing a stale number with a
  fresh one only resets the clock, so they now point at `wc -l` and at
  `harness/RELEASE.md`. `verify_docs.py` caught the suite counts by itself the
  moment the two new suites landed — that check works, and it is why this list
  can be trusted where prose cannot.

* **SQLite declared the foreign key and never enforced it.** `PRAGMA
  foreign_keys` defaults to OFF per connection, so revision `c7e1a5f04b93`'s
  `skribl_post_media.post_id -> skribl_posts.id` ON DELETE CASCADE was written
  into the schema and ignored. Deleting a post left its association row behind,
  `sweep_orphans` then read the media as still REFERENCED, and the bytes were
  never reclaimed — the exact leak the constraint was added to close, still open
  on the one engine the assertion had never been run against. It surfaced only
  because `verify_deletion_foundation.py` joined the aggregate, which runs on
  SQLite; standalone it had only ever run on PostgreSQL, where it passes 8/8
  because PostgreSQL enforces the constraint natively.
  **Access was never exposed** — `/media/<key>` authorises through an EXISTS join
  to the post, so a deleted post's media is refused (404) whether or not the
  orphan survives. It is a data-integrity and storage leak, not a security hole.
  `models.enable_sqlite_foreign_keys()` now sets the pragma, installed from
  `init_skribl()` so a process that merely imports Skribl without mounting it is
  untouched. Measured both ways: cascade fires with it, orphan survives with
  `SKRIBL_SQLITE_FOREIGN_KEYS=0`.
  **Scope worth knowing before deploying on SQLite:** the pragma is a property of
  the CONNECTION, so there is no way to enforce Skribl's foreign keys and not the
  host's. A host whose own data violates a constraint it declared will now get an
  error where it previously got silence. That is the correct outcome and it is a
  behaviour change; the env var is the opt-out.

* **A generated aggregate now survives being interrupted.** A full run needs
  ~25 minutes, longer than some environments allow in one invocation, and
  background processes do NOT reliably survive between invocations here —
  ARCHIVE-README claims they do, and a run killed after batch 1 proved otherwise.
  The tempting workaround is running batches by hand and adding up the totals,
  which is the hand-typed number this project keeps abolishing. `release_run.py`
  checkpoints after every batch instead (`--budget`, `--restart`; state lives
  OUTSIDE the tree, or writing it would change the hash of the tree it describes)
  and re-verifies the frozen tree hash on every resume — so an edit made between
  invocations aborts the run exactly as an edit between batches does. The
  checkpoint is deleted on completion, or the next release would silently resume
  a finished one.

## Player extraction — first cut landed, most of it still to do

**Do not read `verify_player_isolation.py` going green as "the player is
extracted."** Its Half B assertions are RATCHETS: they hold the ground already
won and state the target beside each number. Half A (playback) is the real
regression net and must never go red.

Where it stands, all measured:

* **Down 56,727 bytes.** A player page downloaded 329,159 bytes of JavaScript
  before this session and downloads 272,432 now. The target is 153,600.
  **v199: 155,843 B**, after the serve-time comment strip — 2,243 over the
  target, and the figure the ratchet is now set at. `verify_player_isolation.py`
  measures `r.body()`, the decoded response, so this is what a browser parses;
  the wire figure is 48,309 B and must never be quoted as the first number.
* **What moved:** `editor_export.js` (the PNG/GIF/WebM encoders and share-card
  builder) and `editor_post.js` (the post composer), lifted VERBATIM out of
  `app.js` and loaded only by `skribl_editor.html`. Not rewritten — a second
  implementation would drift, and this project has been bitten by exactly that.
  Both were self-contained IIFEs; the only name crossing the boundary was
  `drawPhotoFitted`, defined AND used inside the moved region (the two hits
  outside it are comments). `verify_exportui` 45/45, `verify_exopts` 26/26 and
  `verify_posted` 34/34 all still pass, and the isolation suite's own fixture
  posts through the editor, so the moved composer is exercised on every run.
* **Ground truth, from Chrome's coverage profiler** rather than from reading:
  of 284 named functions in `app.js`, a player page executes **78**. The player
  was calling `initExport()` and `initPostComposer()` on every shared link to
  wire up controls it does not have.

**Why the next cut is not another line-range move.** The two sections that came
out were the only ones that could. Leak analysis on the other candidates —
each name defined inside a region and referenced outside it:

    more-tools drawer     498 lines   21.7 KB   21 names leak
    overflow menu         329 lines   13.4 KB    2 names leak
    draft save/autosave   336 lines   15.4 KB    9 names leak
    music upload + trim   791 lines   34.2 KB   34 names leak
    loop preview/seam     286 lines   10.5 KB    3 names leak

The music drawer alone shares 34 names with the rest of the file. Moving these
means separating shared STATE (`audioEl`, `trimStart`, `strokes`, the canvas
handles) into a core module both halves import — real decoupling, not a cut.
The overflow menu (2 names) and loop preview (3 names) are the next smallest
and the sensible next targets.

**A trap on the audio path.** The coverage above was taken with a fixture that
has NO AUDIO, so every loop-building function reads as unused. Moving audio code
on the strength of that measurement would break playback for every Skribl with
music, and the isolation suite would not catch it, because its fixture is silent
too. Add audio to the fixture BEFORE touching anything under
"Sample-accurate live loop engine".

* **The runner reported every failing suite as a crash.** `run_harness.sh`
  matched a summary with `^[0-9]+/[0-9]+ passed$`, anchored at both ends. Suites
  do not agree on one format — several print
  `32/33 passed  FAILURES: <what failed>` on a single line — so the anchor
  rejected it, the runner concluded NO SUMMARY, and the suite was reported as
  "crashed before reporting": the one classification that says nothing about
  what went wrong. A failing suite and a suite killed mid-run were
  indistinguishable. `verify_amber` was written off as a flake on exactly this
  evidence; it may have been a real assertion failure, and that can no longer be
  recovered from the logs. The trailing anchor is gone; the leading one stays, so
  a mid-sentence "1/2 passed" still cannot be mistaken for a summary. **If a
  suite reports ERROR now, it really did crash.**

## Player extraction — second and third cuts

Cumulative, all measured by `verify_player_isolation.py`:

    329,159 bytes / 7 globals   unsplit
    272,432 / 6                 editor_export.js + editor_post.js
    261,707 / 5                 editor_menu.js

`editor_menu.js` holds the overflow menu, clear-all, the sheet gestures and the
help drawer. The player has none of those and was running `initClearAllMenu()`
and `setupSheetGestures()` on every shared link to attach handlers to elements
it never paints. `openHelpDrawer` is no longer reachable there.

**The obvious boundary was wrong.** Cutting the whole span from the "Overflow
menu" comment to the next section would have swallowed `initBrandFit()`, whose
inner `fit()` the PLAYER executes — it is why the header brand collapses
correctly on a shared link. Chrome's coverage profile reports function NAMES, so
a nested `fit()` is indistinguishable from any other until you look at where it
is defined. The cut stops before it. `verify_help` 61/61, `verify_ux` 130/130,
`verify_pages` 44/44 all still pass, and `verify_seam` still totals 2485
editor-only lines against 2467 before any of this — nothing became
player-reachable, the code only moved.

**The loop-preview region is NOT movable, despite looking like the next easy
cut.** Its leaked names are real calls, not guarded ones: `stopLoopPreview` is
called from four places outside it (1237, 1450, 2520, 4166) and `playMusicLooped`
from the editor replay path, and `stopLoopPreview` is in the player's executed
set. Moving it would throw on the player. Compare `closeMenu`, the only name
leaking out of the menu region, whose one external call site already reads
`typeof closeMenu === 'function'` — inert on the player instead of fatal. **That
guard is the difference between a movable region and one that is not**, and it is
worth checking for before planning any further cut.

## Why the music drawer will not extract — and the fix that unblocks it

The region has **64 top-level names, 36 of them referenced by code the player
executes.** Not all state: `audioEl`, `trimStart`, `trimEnd`, `audioCtx`,
`currentAudioBuffer` and `loopCrossfadeMs` are genuinely shared, but so are
`drawWaveform`, `drawZoomWaveform`, `updateTrimUI` and `updateZoomHandles` —
**and those are called from `loadSkribl`, which the player runs.** The player is
drawing waveforms into canvases it never paints.

That is the real obstacle, and it is not a file boundary. **`loadSkribl` calls
editor UI unconditionally, in player mode as well.** So the drawer cannot be
moved while a shared function reaches into it. The unblocking change is to guard
those calls the way the rest of `app.js` already guards
(`document.body.classList.contains('player-mode')`), after which the drawer's
dependency on shared code is one-directional and the cut becomes possible.
Cutting first and guarding later gets a player that throws.

`showToast` is also declared inside this region and used across the whole file —
a general utility that ended up filed under music. It should move up to the
shared section regardless of what happens to the drawer.

**A caution about the measurement that produced this.** The first pass matched
declarations with `^\s{0,2}(?:const|let|var)`, allowing two spaces of indent. It
swept up locals declared inside IIFEs — `s`, `w`, `data`, `file`, `err` — and
reported 65 names as shared state, which would have made the region look
hopeless. Column-zero matching gives 36. Same failure as the flattened DOM
selector that once invented a "mixed register" grammar problem: a loose pattern
inventing structure that is not there. **Anchor at column zero when asking what
is top-level.**

## Step 7 in progress — the shared paths are guarded, the drawer is not yet cut

`updateTrimUI` was never a UI function. It is **the choke point that clamps
`trimStart`/`trimEnd` and enforces the 20s loop cap on load**, and the player
reaches it through `loadSkribl`. The obvious decoupling — a player-mode guard
around the whole function — would have let a shared link play a loop longer than
either editor allows, reintroducing on the player exactly the bug that choke
point was added to fix. It is now split: `clampTrim()` runs on both surfaces,
the DOM half is guarded and null-checked.

`loadSkribl` and `resetMediaForLoad` now separate state from drawer UI. The
player no longer decodes waveforms into canvases it never shows, nor rewrites
button labels for a drawer it does not have. `dragZoomPan` needed nothing — it
is a drag handler for a zoom track the player has no markup for, and
`updateTrimUI` is null-safe now regardless.

**A ratchet was loosened, once, on purpose: 263,000 -> 264,000.** The guards cost
about 1.7 KB. I first wrote that they unlock "roughly 34 KB" — that was the size
of the whole region, claimed before measuring, and it is wrong. **Measured:**

    music region              34,947 B total
      stuck (player calls it) 14,891 B   drawWaveform, showToast, clampTrim, ...
      no outside reference     6,067 B   the drag handlers, validateMusicFile, ...
      top-level wiring        ~14,000 B

The debt is written beside the number in `verify_player_isolation.py`: when the
drawer moves, it must come back below 262,000. **If that line still reads 264,000
with no drawer cut behind it, the prep was never cashed in.** Worth noting the
ratchet fired on the change that set it — the mechanism caught its own author
twice in one session, which is the only real test of whether it works.

**The 6 KB is NOT independently movable, and this is the trap to avoid.** Those
eight functions have no reference outside the region, which makes them look free
to take. But they are called from TOP-LEVEL statements inside it —
`dragHandle(handleStart, true)` at what is now line 2320, `dragZoomHandle(...)`
at 1773, `validateMusicFile(file)` at 2044. Top-level calls evaluate at LOAD, on
the player, so moving the function without its call site throws immediately on
every shared link. Function and wiring have to travel together.

**The recipe, in order:**

1. Hoist the 12 stuck functions and the shared state declarations (`audioEl`,
   `trimStart`, `trimEnd`, `audioCtx`, `currentAudioBuffer`, `loopCrossfadeMs`,
   `audioDuration`) OUT of the region, into a marked shared section above it.
   Shared state can never live in an editor-only file: a binding declared there
   simply does not exist on the player, and any player code touching it throws.
2. `showToast` goes with them — it is used file-wide and only lives here by
   accident.
3. What remains in the region is then wiring plus its own helpers, and moves
   wholesale into `editor_music.js`.
4. Re-measure. Tighten the ratchet below 262,000 or explain why not.

## The editor shell is out of the player template

**31,530 bytes of markup removed** — the player's template went 56,716 -> 25,186 B
and the DOM ratchet reached its target: **0 authoring controls**, down from 8.

Out: the overflow menu, export sheet, post composer and help drawer (422 lines,
and safe to remove precisely BECAUSE the earlier cuts moved their JS into bundles
the player never loads — the markup had nothing left to wire it up), then the
record, post and undo buttons and the music and photo file inputs.

**The stub pattern is what made the controls removable.** `app.js` writes to them
from more than twenty places — `.disabled`, `.hidden`, `.innerHTML`,
`.classList` — so guarding each site would have cost more bytes on every shared
link than the markup it replaced, and would still have missed the next one added.
Instead `_authoringCtl(id, tag)` falls back to a DETACHED element of the same
kind: writes land harmlessly on something nothing renders, reads round-trip. Two
genuine null-crashes still had to be fixed by hand first (`photoInputEl` and the
autosave wiring, the latter rerouted through the `bindEl` helper that already
null-checks and predates the problem).

**The byte ratchet was measuring half the payload.** JS-only. So 31.5 KB of
markup leaving the player was invisible, while the ~700 bytes of guards that MADE
the removal safe registered as a regression and failed the run. A measurement
that sees one half of the payload rewards moving weight across the boundary
instead of removing it. There is now an HTML ratchet beside the JS one.

**Two mistakes worth not repeating.** A regex ending `(?:</\1>|>)` matched a
multi-line `<button>` only as far as its first `>`, orphaning the label and the
closing tag — tag counts went 54 open / 57 close and the template stopped
parsing. Match balanced tags, or count opens and closes. And when that produced a
blank player, `'playerShell' in template` read False and looked like the cause:
it is a red herring, `playerShell` lives in `_skribl_player_controls.html`, which
is included, not inlined.

**The next template target, found by a suite that caught up with reality.**
`verify_review` asserted the player "really does render media inputs" — true and
load-bearing when the player carried the whole shell, false now. Inverting it
surfaced the follow-up: the draw, music and photo TAB PANELS are still in the
player's template, and their `#photoUploadBtn` / `#musicUploadBtn` drop handlers
are the only remaining reason `lib/media_validation.js` (7,130 B) loads on the
player. Remove the panels and the module leaves with them.

## The player is down to a player

    JavaScript   329,159 -> 257,592 B
    HTML          56,716 ->   7,989 B
    total        385,875 -> 265,581 B   (-120,294, 31%)

The tab bar and the draw, music and photo panels are out of the player template
(862 lines -> under 150). That removed 87 elements the player never painted, 44
of which `app.js` dereferenced, and it broke the player four times on the way —
each caught by Half A and fixed at the source:

* **12 load-time listeners** now go through the detached-element fallback.
* **`waveformCanvas.getContext('2d')` at load.** A detached `<canvas>` returns a
  real 2D context, so `drawWaveform` and every `clearRect` downstream work
  unchanged and paint into nothing.
* **Three drag installers take an ELEMENT, not an id**, so the stub cannot help
  at the call site. One guard at each function's entry covers every caller.
* **The photo teardown in `resetMediaForLoad`** mixed state resets with
  unguarded DOM writes; split like the music half.

**`lib/media_validation.js` is off the player** — 7,130 B. Its only callers are
the photo and music drop/change handlers, and both upload buttons and both file
inputs left with the panels. `verify_review` asserts the editors still load it
and the player does not, so the saving cannot quietly revert.

**The ratchet debt is repaid.** It was loosened to 264,000 with a promise to get
back under 262,000; it is 257,592, and the ratchets now stand at 258,000 JS and
9,000 HTML.

**A test that something is ABSENT must match the mechanism, not the word.**
`verify_review` failed on "the player does not load the module" because the
template's comment explaining the absence contains the filename, and a substring
check read the comment as the thing it was looking for. Both checks now match the
`<script` tag. That is the third assertion in that file to encode a fact my
changes made false — and each one pointed at the next target.

## The music drawer's WIRING did move — the earlier "not worth cutting" was half wrong

`editor_music.js`, **14,286 bytes**: the upload and drop handlers, the trim-track
drag installers, the zoom-magnification and fine-tune controls, the remove
button, and the five helpers only they call (`dragHandle`, `dragZoomHandle`,
`dragRangeWindow`, `positionSegSlider`, `validateMusicFile`). Every call site of
those five was inside the moved set, so nothing left in `app.js` names them.

I had written this region off after measuring that only ~5.4 KB of FUNCTIONS were
free. That was true and it was the wrong question. The region is three kinds of
thing:

    declarations   5,115 B   state + element handles — can never move
    functions     18,358 B   mostly reached from loadSkribl — must stay
    wiring        8,717 B    listeners and IIFEs — nothing names them

Wiring moves even when the functions around it cannot, because a classic script
loaded AFTER `app.js` can read every top-level `let`/`const` it declares. The
direction that fails is the opposite one: a binding declared in an editor-only
file does not exist on the player at all. **Ask which direction the reference
runs, not whether the region is "shared".**

Since the player template lost the music panel, these listeners had been
attaching to detached stub elements on every shared link — work with no possible
effect.

## Photo drawer wiring out too

`editor_photo.js`, **12,298 bytes**: upload and drop handlers, the fit buttons,
reposition, the opacity and blur sliders and their nudgers, and the eraser
cursor's canvas listeners. Same rule as `editor_music.js` — only STATEMENTS
move; the functions they call stay in `app.js`.

The eraser cursor's listeners are on `.canvas-wrap`, which the player DOES have.
They are editor-only because the player has no eraser, not because the element is
missing — worth noting, since "the element is absent" was the test for everything
before this.

**A gap in `verify_seam` that this exposed.** Its "editor-only extracted" figure
counts named FUNCTION spans, so it read 951 lines both before and after 12.3 KB
of wiring moved: `editor_photo.js` contains no top-level functions at all. The
suite still passes and its leak assertion is still meaningful, but **that number
cannot see a wiring extraction**, and anyone using it to judge progress will
conclude nothing happened. `verify_player_isolation.py`'s byte ratchet is the
measurement that tracks this work.

## Closed in v212 — the trim strip, and an assertion that pinned nothing

**The bug.** `drawWaveform()` sized `#waveformCanvas` straight from
`musicTrack.getBoundingClientRect()` with no guard, and the decode chain is its
ONLY caller. Sizing a canvas from a 0-wide rect is not a no-op: it sets
`canvas.width = 0`, which CLEARS the bitmap, and the loop then paints zero
peaks. So a decode landing while the music drawer was shut left the strip blank
for the rest of the session, while `drawZoomWaveform` — guarded, and re-called
from `updateTrimUI()` — drew Loop Detail correctly from the SAME buffer. One
decoded buffer, two canvases, one painted. Reported from a phone, where the
slower decode makes it easier to hit; the realistic routes in are a draft reload
or closing the drawer before decode lands.

Reproduced before any edit, by holding `decodeAudioData` until the drawer was
shut: strip 0x0 with 0 ink, zoom 638x72 with 45,936 ink. That is the screenshot.

**The fix.** The guard on `drawWaveform` on both editors, plus a repaint from
Pad's `openDrawer()` music branch, two frames after opening so `musicTrack`
reports real width rather than 0.

**THE PART WORTH READING. My first Flip assertion pinned nothing, and only the
mutation test found it.** The handoff note said "same on Flip, which had the
identical unguarded line". The LINE is identical; the conclusion was wrong.
Flip's `reveal()` already calls `requestZoomWaveformDraw()`, and Flip's copy of
that repaints BOTH canvases — so **Flip self-heals this scenario and was never
broken by it.** An assertion that Flip "shows a painted strip after opening the
drawer" is green against the sealed v211 archive and green against the fix.

So the two surfaces are pinned by DIFFERENT assertions, deliberately:

* **Pad** fails the user-visible scenario, so the scenario is its pin.
* **Flip** cannot fail that scenario, so its guard is pinned by the property the
  guard actually governs: paint the strip, take the track's layout away, call
  `drawWaveform`, restore layout WITHOUT scheduling a repaint, read the canvas.
  Guarded, 9,499 ink survives; unguarded, the canvas is 0x0 and empty. The whole
  sequence runs inside ONE `evaluate` so no rAF can slip in and repaint between
  the wipe and the measurement — that would make the probe green for a reason
  having nothing to do with the guard.

**Generalises, and this project keeps relearning it.** `verify_parity`'s
re-inline caught the same class: behavioural parity says the copies agree today,
not that the assertion depends on the fix. **Run the mutation per COMPONENT, not
once for the whole change** — a single all-or-nothing revert would have shown
three reds and hidden that one of them was unreachable.

Mutation matrix, each component reverted independently (the full revert is
byte-identical to the sealed v211 `app.js` and `flip.js`):

    mutation      pad gate  pad scenario  pad no-wipe  flip no-wipe   total
    none            PASS       PASS          PASS         PASS       298/298
    pad-guard       PASS       PASS          FAIL         PASS       297/298
    pad-reveal      PASS       FAIL          FAIL         PASS       296/298
    flip-guard      PASS       PASS          PASS         FAIL       297/298
    all (= v211)    PASS       FAIL          FAIL         FAIL       295/298

The gate assertion stays green under every mutation BY DESIGN — it asserts the
scenario entered the failing state, so a red gate means a broken probe, not a
caught bug. Under `pad-reveal` the no-wipe pin fails on its own self-gate
(`before.ink > 500`), not on a wipe: the strip was never painted to begin with.
Same colour, different reason, and worth reading the detail line rather than the
column.

**Cost: 209 B served, 2,428 B of source.** Almost all of it is the comment
naming the pattern, which `jsstrip.py` removes from the response — this is the
third "sized from a rect with no layout yet" bug in this drawer, so naming it in
place is worth 209 B. The ratchet went 146,911 -> 147,120, set to fit, with the
accounting line beside it.

**A number from the previous handoff that was wrong: "+360 B".** It was recorded
against a fix whose Flip half was mischaracterised, and the measured figure is
209 B. Nothing from that note should be carried forward without re-measuring.

## Also closed in v212 — two generators, one stanza, and they disagreed

**Found while sealing this build, by causing it.** `release_run.py` drives
`run_harness.sh` one batch at a time, so the record it leaves behind describes
only the final batch. It already fixes that from one side: it rewrites
`LAST-RUN.txt` to cover every batch and re-stamps. **That holds only while the
release run is the LAST harness invocation.** A bare
`./harness/run_harness.sh verify_docs.py` afterwards rewrites `LAST-RUN.txt` and
re-stamps from it — publishing **a stanza claiming 36 assertions from a single
batch, beside a `RELEASE.md` recording 2400 across every suite on disk, on the
same frozen tree.**

**This is worse than a hand-typed number, not better.** It is machine-generated,
so it carries exactly the authority this project grants generated figures, and
it is wrong. The generated-not-typed rule assumes ONE generator. There are two,
and nothing made them agree.

`stamp_docs.py` now REFUSES a stamp that would narrow the record for the same
tree; `--force` is the deliberate override.

* **It compares ASSERTION TOTALS, not suite counts.** `read_run()` counts suites
  that REPORTED (59 here), while `RELEASE.md` counts suites reported INCLUDING
  skips (61). A suite-count comparison refuses a legitimate full release. The
  assertion total is the one figure both generators compute the same way,
  because a skipped suite contributes zero to each.
* **A `RELEASE.md` for a DIFFERENT tree does not gate at all.** It says nothing
  about the run being stamped, and gating on it would wedge every build — which
  is precisely the state the tree is in mid-release, since `RELEASE.md` is
  written at the END.

**The pin runs in an isolated temp ROOT, and that is load-bearing.** The first
version drove the real `stamp_docs` against the real files and could not work:
`stamp_docs` resolves `ROOT` from `__file__`, so mid-release it reads a
`RELEASE.md` describing the PREVIOUS tree, the guard correctly declines to gate,
and there is nothing to refuse — the assertion would fail inside the very run
that seals the archive. It also restored "the real record" from disk, which at
that moment WAS the damaged narrow one. Four assertions in `verify_docs.py` now
build a fabricated tree instead: refuse-on-narrow, stanza-untouched (exit code
alone would pass against a script that refuses loudly and writes anyway),
stamp-on-wide, and no-gate-on-other-tree. Mutation-tested: remove the guard and
the two refusal assertions go red while both controls stay green.

**The general lesson, and it is the one this file keeps restating.** A second
generator is a second place for a number to come from. When two of them write
the same field, something has to make them agree, or "generated" stops meaning
"trustworthy" and starts meaning "unattributable".

## The v213 loss — commit before anything destructive

**I destroyed several hours of harness work with `git checkout`.** The tree had
exactly ONE commit — the v211 baseline — and everything since was uncommitted.
`git checkout harness/verify_ux.py`, reached for as a cleanup after a botched
edit script, reverted that file to the baseline and wiped all 68 v213
assertions.

The source survived (only that one file was named), so every feature still
worked. What was gone was the evidence that it worked, which in this project is
most of the value.

**Root cause is not the command.** It is that nothing had been committed all
session, so `git checkout` had nothing to fall back to except the beginning.
`git checkout <file>` in a tree like that is not an undo, it is a delete.

**Rules that follow.**

* Commit before anything destructive, and commit as work lands rather than at
  the end. A commit costs nothing and is the only thing that makes a mistake
  cheap.
* Never `git checkout` a file with uncommitted work in it. For mutation tests,
  `cp` from a `/tmp` copy — that is what every source-file mutation in this
  session did, and it is why app.js, flip.js and the libs all survived while the
  one file handled with git did not.
* When an edit script goes wrong, FIX IT FORWARD. The botched split turned a
  2,770-line file into 3,941 by duplicating a range; that was recoverable by
  inspection. Reverting was the destructive choice, taken because it looked
  faster.

**What made recovery possible** was `/tmp/ux.log` from the last green run: it
held every assertion name WITH its measured detail values, so the rebuild could
be checked against the figures the code had actually produced (peak alpha
89/225, tall-grid aspect 0.99, 1,889ms against 410ms, 282x282 circles) rather
than against fresh guesses. Keep run logs. They are cheap and they are the only
reason this was a rebuild rather than a redesign.

## When to split a suite — measure runtime, not assertions

**The trigger is RUNTIME AND BROWSER LAUNCHES, not assertion count.** Assertions
are nearly free; a `chromium.launch()` and a page load are not, and it is wall
time that decides whether a suite still finishes inside one invocation. A suite
of 400 cheap assertions sharing two pages is fine; one of 40 that launches a
browser each is not.

Measured at v214, on this container:

    suite              launches   runtime   assertions
    verify_ux.py            17      206 s          298
    verify_tools.py         13      134 s           93

`verify_ux` needed splitting at ~366 assertions and roughly 20 launches, when it
stopped finishing in a single tool invocation and had to be run in the
background and polled. That is the failure to avoid: **a suite that becomes slow
enough stops being run**, and an unrun suite is worth less than no suite,
because it still reads as coverage.

**Rule of thumb: past ~150 s or ~15 launches, split BEFORE adding the next
feature's pins, not after the suite becomes unreliable.** `verify_tools` is at
134 s / 13 launches — close, so the next tool's pins should go into a new suite
rather than onto the end of this one.

**The cheap fix before splitting** is to share pages. The v213 mirror pin opened
six browser contexts (one per mode per surface) and was cut to two by reusing
one page and resetting the stroke arrays between cases. Reloads are the
expensive part, not assertions.

## Suites: verify_boot.py

**The most expensive bug in this codebase, measured in debugging rounds**, is not
a wrong pixel. It is `flip.js` throwing at top level and silently abandoning
every line after the throw. The page still renders, the markup is all there, and
an arbitrary SUFFIX of the behaviour is missing — so it presents as several
unrelated features breaking at once and sends you after whichever one you
noticed first. Four rounds in one session, every one the same shape: a function
that runs during init (`setTool()` is the usual culprit) reaches a `let` declared
further down and hits its temporal dead zone. `let` and `const` do not hoist the
way `function` does, and **no `typeof` guard can rescue them — only declaration
order can.**

So each editor script ends with one statement whose only job is to say it got
there — `window.__skriblBoot.flip = true` — and this suite reads it. That beats a
page-error listener twice over: it also catches a throw something swallowed, and
it names WHICH file died instead of reporting a symptom three screens away.
Verified by reintroducing the bug on purpose: the suite fails with *"Cannot
access '__tdzCanary' before initialization"* rather than with a missing
filmstrip.

**Rule going in: state any early path can reach belongs with the early state, and
anything touching state declared further down belongs in the load handler.**

The suite loads each surface twice, empty and restoring a draft, because restore
is a second load-time path with its own ordering and it is the one a returning
user takes. It pins the two surfaces' genuinely different behaviour rather than
flattening it: Flip restores silently, Pad offers a "Discard / Restore" banner
because its autosave holds strokes but not media bytes.

One trap worth remembering, found while writing it: `typeof frames !== 'undefined'`
is **always true** in a browser — `window.frames` is the iframe list. On Flip a
real top-level `let frames` shadows it and the expression worked by luck; on Pad
it resolved to `window.frames[0]` and threw.

## The pen palette lives in lib/palette.js

It used to live in two places: seven `<button>`s written into
`_skribl_draw_drawer.html` for Pad, and a `COLORS` array at the top of `flip.js`
for Flip — the same seven hexes in the same order, kept in step by hand, with
nothing comparing them. The failure mode of forgetting one is not an error. It
is two editors quietly offering different colours, which nobody notices until
someone switches surfaces mid-drawing. Both build from the lib now, and
`verify_parity` asserts they render the same list, in the same order, and that
the list came from the lib rather than from a copy.

**The colours are Risograph inks** — fluorescent pink, hot orange, acid yellow,
a printed green and a federal blue, plus paper white and a toner black. That is
what small-press zines are actually printed with, and it is a deliberate
replacement for what was there: a purple and a blue lifted straight from the UI
accent, a mint green and a muddy amber. *A drawing palette that matches the
chrome is a palette that was never chosen.* Riso inks are spot colours, mixed
to sit on paper rather than to pass a contrast check, so they are strongest on
the dark grounds the background swatches default to — acid yellow on white is
nearly nothing, which is true of the ink as well.

The lib marks its dark swatches with `dark: true` and deliberately does **not**
say what colour their rim is. A near-black dot on a near-black drawer is an
empty hole, but the drawer is near-*white* in light mode, where the dot needs no
help and a light rim would be the thing that vanishes — so the rim is CSS,
keyed off `[data-ink="dark"]`, and follows the theme.

**Building the dots at runtime is what let the two lists become one.** Pad's
click handler is delegated on `#colorGroup`, so a dot created after load needs
no listener; Flip passes an `onPick` because it also closes the drawer. The
custom picker and the eyedropper stay in the markup — they are controls, not
colours, and they are what the dots get inserted before.

## Colour ratchets: three of them, and each was added after something escaped

1. **Neutrals outside `:root`** (`verify_surfaces`) — every grey the chrome
   paints must be a token, or it will not follow a light theme.
2. **Chromatic ink** (`verify_theme`) — stricter: `color`, `fill` and `stroke`
   may hold no literal at all except `#fff` and `#0d0f14`. A red is not a
   neutral by any measure, so the grey audit walked straight past `#f4326f` at
   3.32:1 on a light sheet.
3. **The `rgb()` function form** (`verify_surfaces`) — the first version of the
   neutral ratchet only looked for `#hex`, so `background: rgb(23, 27, 35)` sat
   on two controls and stayed dark in light mode with nothing to say so.

There is one exemption and it is a rule rather than a list: a token named for
the **canvas** is not chrome. `--on-canvas-rgb` is the empty-state hint, painted
on the drawing surface, which follows no theme — and naming it in `:root` is
what makes that a visible decision instead of a literal somebody missed.

**What a ratchet cannot see is a mark that is white on purpose.** `#fff` is
exempt because it is nearly always text on a coloured fill — but five marks were
white against a surface that flips, and simply disappeared in light mode: the
brush-size preview dot, the size-preset dots, the music playhead, the spinner's
leading arc, and the ring around the selected swatch. Those were found by
looking, not by asserting.

## Suites: verify_fuzz.py

**Every other suite here tests a feature. This one tests the document**, against
the single rule that has broken three separate times for three unrelated
reasons:

```
'frames[9].strokeGroups' accounts for 317 points, but the strokes array contains 318.
```

That is the server refusing a share. It is not cosmetic — the user has finished
a drawing and the app will not let them post it — and all three occurrences were
found the same way: in production, by the owner, on a phone. The causes were a
second pointer landing mid-stroke, a page change mid-stroke, and a shape
committing its group before its points. **Nothing they had in common was visible
in a diff, and no feature suite would have caught any of them, because each one
only appears when two features interleave.**

So this drives the editor the way a person actually uses it — a shuffled stream
of draws, erases, page adds and deletes, duplicates, selections, moves, mirrors,
cuts, pastes, smudges, undos and redos — and re-checks the invariants after
**every** operation: strokes length equals the sum of strokeGroups, every group
count is a positive integer, the page index is in range, every coordinate is
finite. Then it posts the result and requires the server to take it. That last
step is the one that matters: **the invariants are this file's model of the
rule; the POST is the rule.** If `validation.py` and this file ever disagree,
that assertion is what says so.

**The seed is fixed and printed**, and the last dozen operations are dumped on
failure. A fuzz failure that cannot be replayed is a story, not a bug report.

**Two anti-vacuity assertions, and they are not decoration.** The first version
guessed the page-operation names (`addPage`, `dupPage`, `delPage`; the real ones
are `addFrame(copy)` and `delFrame(i)`) and wrapped them in
`typeof fn === 'function'` guards. Every page operation became a silent no-op:
the fuzz spent its whole budget on one page and reported a confident pass having
never changed page at all — while the invariants, which an untouched empty
document satisfies trivially, stayed green throughout. So the suite now asserts
that it drew something *and* that it used more than one page. **A guard that
skips is a guard that lies about coverage.**

**A failure here does not mean "the fuzzer is flaky."** Every operation is
something a person can do with a mouse, in an order a person could do it in. If
this goes red, some pair of features has stopped composing.

## Suites: verify_smudge.py

**A smudge tool on a document that has no pixels.** Every smudge tool you have
used pushes colour around a bitmap: sample under the brush, blend, write back.
Skribl has no bitmap to push. A page is a list of points, and that same list is
what the player replays, what export walks and what the draft stores.
Rasterising a page to smudge it would invent a second kind of content that undo,
export, the draft schema and the player would all have to learn — and it would
kill replay outright, because a flattened image has no stroke order left to
animate.

So this smudges the **geometry**. Points inside the brush are dragged along with
the pointer, weighted by distance from its centre, and the strokes bend. It is a
warp brush wearing a smudge's clothes, and for a line document that is the more
honest instrument: it moves the ink you drew rather than averaging it into mud.

**What it costs, stated plainly:** no colour bleed. Two crossing strokes bend
towards each other but never mix, and nothing in this format can make them mix.
**What it keeps** is the reason to do it this way — replay, export, the player,
the draft, and an exact undo. The suite proves that end to end: it smudges a
page, posts it, and loads the result in the player, which was never taught
about smudge and does not need to be.

**`SMUDGE_STRENGTH` is what makes it a smear instead of a spike.** At full
strength a point in the centre of the brush moves the entire delta — which lands
it back in the centre for the next move event, at weight 1 again. It rides the
cursor forever, and every line the brush crosses gets dragged to the same single
point. Measured on three parallel lines: all three converged to one vertex.
Below 1 the ink lags behind the brush, slides toward the rim, and sheds on its
own — which is what dragging a finger through wet ink actually does. The suite
pins the *property* rather than the constant: three parallel lines must still be
three lines afterwards.

**Undo stores coordinates, not a displacement**, for the reason `selRestore`'s
comment already gives: a smudge accumulates over dozens of move events at a
different weight each time, so there is no single delta to negate and
re-deriving one would walk the artwork further from home on every cycle. Ten
undo/redo round trips are asserted to leave it bit-identical.

**A smudge belongs to the page it started on.** The frame index is pinned at
pointerdown, exactly as `strokeFrame` is for a stroke. Changing page mid-drag
and re-reading `frame()` would apply the back half of the gesture to different
artwork, at indices that mean something else there, and hand undo a
before/after pair for strokes nobody touched.

**A tap logs nothing.** Neither does a drag across empty canvas. A no-op on the
history puts the stroke the user actually wants back one press further away than
they expect.

**One test-isolation trap, found the hard way and worth repeating.** `fresh()`
originally reset the document but not the *tool* — so a section that left smudge
selected made the next section's setup silently draw nothing, and the assertions
downstream then passed or failed for reasons unrelated to what they named. One
of them passed *vacuously*: "undo restores the exact coordinates" compared an
untouched page against itself. `fresh()` now restores the pen and asserts it,
and `line()` asserts that it actually drew something. **A setup step that
quietly does nothing is worse than one that fails.**

## Suites: verify_theme.py

Light mode, and the four things that make a second palette a feature rather
than a liability.

**It is opt-in, and that is a decision.** There is no
`@media (prefers-color-scheme: light)` rule in the sheet. The first pass had
one, and it flipped the default for every visitor whose OS is set to light —
which is most of them, on an app whose entire identity is dark. Skribl would
have changed for everyone overnight without anyone asking. Following the system
is one block away (wrap the light ramp in the media query and guard it with
`:root:not([data-theme="dark"])`) but it is the owner's call about the product,
not a detail of the implementation. The suite emulates **both** OS preferences
and asserts the default load is dark under each, because a rule that only
misfires under one of them is exactly what nearly shipped.

**It does not flash.** The setting lives in localStorage, which no stylesheet
can read, and every script in both templates is deferred (`verify_surfaces`
pins that). Stamped by a deferred script, the browser would paint a dark frame
first — a black flash on every navigation for the people who chose light
specifically to avoid one. `_skribl_theme_boot.html` is a tiny inline script in
`<head>`; the test for it serves the page with **every external script
aborted** and asserts the theme is still right. If it needs anything deferred,
it flashes.

**The canvas does not follow it.** This is the load-bearing rule and the reason
the job was scoped to chrome only. A drawing's ground is part of the drawing —
exported, posted, seen by other people — so a UI preference must never repaint
it. The check reads an actual pixel from the middle of the canvas in both
themes and demands they be identical; `#0d0f14` is excluded from the palette
and from both colour ratchets for the same reason.

**The ramp cannot rot.** Add a token to `:root` next month, forget the light
value, and that one control keeps its dark colour while everything around it
flips — silently. Rather than a hand-kept list, the assertion is structural:
every *neutral* colour token must be overridden, which lets the accent family
and the radii and easings through automatically because they are not neutral
colours.

**Chromatic ink was the half phase 1 could not see.** That pass moved neutrals,
because greys are what a theme obviously flips, and left every coloured literal
alone. But the danger red, the warn amber and the ok green were all picked
against a near-black ground: `#f4326f` measures **3.32:1** on the light menu
sheet — below AA for body text, and it is what "Clear all" is written in. So
v233 tokenised them (`--danger`, `--warn`, `--good`, and friends) at their
existing dark values, restated them darker at the same hues for light, and the
ratchet for ink is stricter than the one for greys: **no literal at all**, with
`#fff` and `#0d0f14` the only exemptions.

**The legibility threshold is relative, not absolute, and getting that wrong
cost a round.** Demanding 4.5:1 of every label failed on `.menu-version` at
4.42 — the version footer, deliberately tertiary, dim in *both* themes.
Satisfying it would have meant darkening the upper half of the light text ramp,
i.e. breaking the mirrored relationship on purpose to fix something this work
never touched. What light mode is answerable for is not regressing, so each
element is measured in both themes: a floor of 3:1, and a drop is a failure
only if it lands under AA *and* loses more than 15%. `#f4326f` went 5.5 → 3.32,
caught twice over. White on the accent (4.35:1, identical in both themes and
older than this work) is printed as a number rather than asserted — it is a
palette question about the accent, not a theme one.

**A sweep over a hidden element measures nothing and passes.** The first
version swept a closed menu, found no neutral-ground text on Flip, and reported
a triumphant 99:1 having measured zero elements. It opens the menu now, and
asserts the count of laid-out elements before trusting the numbers.

## Suites: verify_flipdraft.py

Closes the bug the owner reported as "autosave is failing on pad". It was not
Pad's fault: localStorage is capped at roughly **5 MB per origin** and both
editors share it, and Flip was writing its media into that budget as base64 data
URLs — inflated 4/3 by the encoding, so a 30-second WAV is ~6.7 MB on its own.
One Flip draft measured 2.7 MB of the shared 5 MB, and Pad's autosave was what
fell over.

The spill to IndexedDB already existed, but only as an EMERGENCY path reached
after localStorage had refused the write — which made a 5 MB quota the thing
standing between a user and their drawing. It is the normal path now: strokes
and media metadata to localStorage, media bytes to `lib/draftstore.js`. The
merge on the restore side was written for the quota case and was correct all
along; what changed is that it is reached on purpose.

The number this suite exists to hold: **the same draft that wrote 1,683,508 B
to localStorage now writes about 3,500 B.**

Backward compatibility is the last section and is not optional — anyone with a
draft saved before this has the old full payload sitting in localStorage with
media inline, and it has to keep restoring.

Two isolation traps are documented in the file itself, because both produced
failures that lied about their cause. `clean()` must empty the DOCUMENT as well
as the stores, or the live page saves its media back on the next unload. And the
legacy section runs on a **fresh page**: `_sessionOwnedDraft` licenses `saveNow()`
to delete the slot when the document is empty, so emptying a page that had
already saved made the flush remove the planted record, and the section reported
0 strokes against a backward-compatibility failure that did not exist.

## Suites: verify_select.py

Select exists on Flip and **must not** exist on Pad, and this suite pins both
halves of that.

v219 pulled Select from Pad because Pad records a timed performance: moving
points that were already recorded made replay draw a stroke at its NEW position
at its OLD timestamp. Flip has no timeline within a page — playback reveals
strokes in index order — so moving a point changes only where it is, never when.
Flip's own Move mode has translated whole pages this way since v213. The last
section asserts Pad's registry still does not list the tool, so a future "make
the surfaces match" cannot quietly reintroduce the bug v219 removed.

**Transform (v228)** adds four corner handles and a rotate grip. Scale is
UNIFORM and corners-only: a point carries one scalar `size`, so a non-uniform
scale has no honest answer for stroke weight — stretch a drawing horizontally
and the verticals would need to be thicker than the horizontals — and edge
handles are absent by design rather than missing. A scale multiplies `size`
along with position, which is what makes it worth having: shrink a drawing and
its strokes get thinner, rather than the same-weight outline of a smaller shape.
Rotation leaves `size` alone. Both are pinned.

A transform's undo RESTORES COORDINATES rather than inverting itself, unlike
`selmove`, which negates its dx/dy. Negating a translate is exact; dividing by a
scale ratio is not, and repeated undo/redo would walk the artwork off its mark.
Every gesture also recomputes from a snapshot taken on pointerdown rather than
applying to the previous frame — compounding a ratio sixty times a second walks
the geometry away from the finger, and a drag out and back would not return.

**Mirror, duplicate, cut and paste (v229)** live on `#selbar`, which REPLACES
the page bar while a selection exists — the pattern `setMoveMode()` established.
Five more actions do not fit on a 320px phone as extra chrome; they fit as a
different job for the same row, and `.pb-tx` already drops the labels below 640.

All four share ONE undo shape, `selframe`, carrying a before/after pair of that
page's `strokes` and `strokeGroups`. `selmove` negates its dx/dy and a transform
restores coordinates, because both leave the arrays the same length. These do
not — duplicate appends, cut splices, paste appends — and undoing an index-range
edit whose indices have since moved is the class of bug this codebase keeps
finding. The entry carries the arrays instead of the arithmetic.

Cut writes to a clipboard rather than just deleting: a flipbook's real use for
cut is taking artwork off one page and putting it on the next, and the suite
pins that cross-page paste. Paste is hidden until the clipboard has something —
on a bar this tight a disabled control is a cell of dead width. Duplicate leaves
the COPY selected, not the original, because the two sit on top of each other
and moving the wrong one would be silent.

Two properties carry the design and are pinned hardest:

* **Whole strokes, never fragments.** The marquee selects by GROUP, so a box
  that clips a stroke takes all of it or none. Moving half a stroke would leave
  `strokeGroups` accounting for points that had walked away from their run.
* **Undo is an operation, not a snapshot.** Pad had to clone the selected point
  objects *before* snapshotting, or `strokes.slice()` aliased them and undo
  silently restored the moved position. Flip's `actionLog` stores what was done,
  so undo is the same translation negated and there is nothing to alias. Pinned
  by moving, undoing and redoing and comparing every point to its original.

Note `fresh()`: Flip autosaves and restores on load, so a section that has just
drawn leaves its strokes waiting for the next one. Clearing localStorage is **not
enough on its own** — the live page still holds the drawing in memory and saves
on the way out, so the draft is written back after the clear and restored by the
very reload meant to be rid of it. `fresh()` empties the document first, then
clears, then reloads, and asserts zero points afterwards; without that last check
a polluted page turns every stroke-index assertion into a coin flip.

## Suites: verify_tray.py

Guards a **process**, not a bug. Flip's bottom row was holding two populations
out of one width budget: the document controls (colour, undo, redo, image,
music, magnify), which are a closed set, and the mark-making tools, which are
not. They shared one shelf, so every new tool competed with undo for the same
pixels and each addition became a fresh fitting exercise across six breakpoints
and two surfaces. Measured before the tray: a fourth cell takes the pill
121 -> 158px and wraps the row at 320, 344, 360, 375, 390 and 431.

`verify_tray.py` runs on BOTH surfaces and is mostly ONE assertion repeated at
six widths each:
**adding a tool does not change the pill's width.** If that stops being true the
tray has failed at the only job it was built for.

The two rosters differ on purpose and this suite is where that is recorded: Pad
ships `pen/eraser/shape`, Flip ships those plus `select` since v227, so Pad is
asserted dormant (three cells, chevron hidden) and Flip asserted overflowing
(three cells ending in the chevron). The trial tool it registers is called
`trial` rather than `select` for the same reason — `register()` returns false
for a duplicate id, so registering `select` on Flip silently stopped testing
anything and the width assertions compared a shelf against itself.

It also carries two regression pins for bugs the first version did not catch:
the chevron is a `.tool-btn`, so it was swept up by the binding that calls
`setTool(btn.dataset.tool)` on every tool cell — it has no `data-tool`, so
opening the tray called `setTool(undefined)` and left Pad with no tool selected;
and the tray cells were styled `font: 600 10px/1 inherit`, an invalid shorthand
whose family slot rejects `inherit`, so the whole declaration was dropped.

The fourth tool is registered through the surface's own `register()` — the
real extension point, not a test seam. It is how a tool will actually be added,
so testing registration is testing the feature, and this file never has to ship
a fake tool of its own. Nothing here asserts that Select, Fill or Text exist:
they do not, and the tray was never a promise that they would.

Below 641 the cells are icon-only and the width must not move at all. At 900 the
labels are visible, so swapping "Shape" for "More" legitimately changes it; that
width is pinned on not wrapping instead.

## Suites: verify_tools.py

Split from `verify_ux.py` at v213, which had reached 366 assertions and a dozen
browser launches and stopped finishing inside a single tool invocation. **A
suite that cannot be run in one go stops being run** — the same failure this
project writes pins against.

`verify_tools.py` holds the v213 tool work: the five settings that had no
control (stroke layers, eraser width, grid density, pause handling, pressure)
and the four new behaviours (shift-constrain, shortcuts, shapes, mirror).
`verify_ux.py` keeps V213/V213b, which are behaviour fixes to recording and
drawing rather than tools.

When writing pins here, reuse ONE page per surface and reset state between
cases instead of reloading. Three reloads per surface is what pushed the old
combined suite over the limit.

## Closed in v213 — nine settings, four tools, four carves

**The shape of the release.** Five behaviours the code already had and no
control could reach were exposed; four genuinely new tools were added; and the
draw path was carved out of `app.js`. Everything is on BOTH editors unless
noted, and lives in `harness/verify_tools.py` (84 assertions), split out of
`verify_ux.py` when that suite stopped finishing in one invocation.

**Exposed, not invented** — stroke layers, eraser width, grid density, pause
handling (Pad only), pressure. Each is asserted through the code path that USES
it — painted pixels, `_eraserSize`, the grid overlay, `getPlaybackDuration` —
never through the control's own aria state. A switch that updates itself and
nothing else passes every attribute check ever written, and the eraser mutation
proved it: re-inlining Pad's copy left *"the editor CALLS lib/erasersize.js"*
GREEN while the draw-path assertion caught it.

**New** — shift-to-constrain, keyboard shortcuts, shapes, mirror, brushes,
preview speed (Pad only), selection (Pad only).

### The one rule that shaped every new tool

**Shapes, mirror and brushes all generate ORDINARY STROKE POINTS.** A Skribl is
a flat array of `{x, y, color, size, t, start, erase}` that the player replays
by calling `drawLine`; a shape primitive, a mirror flag or a brush id would each
mean a schema change, new rendering in the player, and every existing post
needing to keep working. Instead each feature shapes the numbers at CAPTURE
time. Three separate pins assert that no point carries a field outside that set
— that is what catches the format opening up.

The corollary is worth keeping: **anything a feature wants that cannot be said
in a position, a width and an `rgba()` is not available.** That is why the brush
list stops where it does. Texture, scatter and blend modes are not omissions.

### Two settings that look alike and go opposite ways

`pauseMode` IS serialized; preview speed is NOT. They sit one row apart in the
same drawer, and the distinction is whether the setting describes **the work**
or **the act of reviewing it**. Pause handling changes what the drawing is, so a
viewer must get the author's choice — the pin loads an author's `keep` drawing
into a browser set to `tight` and requires the same duration. Preview speed is
zoom, not content; posting it would impose one author's review habits on
everyone opening the link.

The mutation is the reason the round-trip assertion exists: with `loadSkribl`'s
adopt removed, *"the choice is written into the payload"* stayed GREEN while the
author's 1,903ms replay collapsed to 410ms for the viewer.

### Grouping, and the connecting-line family of bugs

Mirror emits **one group per reflection**; selection selects **whole groups**;
shapes commit as **one run**. All three are the same rule: the replay joins
consecutive points, so any structure that puts two distant places in one group
draws a line straight across the canvas between them. Flip refuses a share
outright when `strokeGroups` does not account for every point, so on that
surface the failure is a rejected upload rather than a stray line.

### The carves, and doing them in the right order

`editor_draw.js` is the fourth, after `editor_music.js`, `editor_photo.js` and
`editor_shapes.js`. The whole stroke CAPTURE path moved; `drawLine`, `drawDot`,
`getPos`, `pressureSize`, `_eraserSize` and `_brushWidth` stayed, because
`replayTimelineToCanvas` hands the first two to the PLAYER as its painters. The
listeners moved WITH the functions — a binding left behind would ReferenceError
on every player load.

**The numbers make the ordering lesson concrete.** The shape tool was built in
the shared file and carved afterwards: it cost the player 3,191 B, then a
second pass to get 2,337 B back. Selection was built AFTER `editor_draw.js`
existed and cost **195 B**. Same size of feature, one-sixteenth the price.
Carve first when the target is a tool the player has no use for.

`verify_player_isolation` now asserts the carve DIRECTLY as well as by bytes: no
editor-only file is referenced by the player template, and `startDraw`/`endDraw`
are absent from `app.js`. A byte ratchet notices size coming back; it does not
notice code coming back, and a later raise would hide it.

### Latent bug: the history stack aliases its points

`makeHistoryState()` does `strokes.slice()` — the ARRAY is copied, the point
objects are not. Every other writer in this codebase APPENDS points, so nothing
had ever mutated an existing one and the aliasing had never mattered. Selection
moves points in place, so it edited the undo snapshot too and Ctrl+Z restored
the moved position: undo "succeeding" and changing nothing.

Fixed by snapshotting FIRST and only then swapping the selected points for
clones. **The order is the fix** — cloning first captures the clones and fails
identically one step later, which is the mistake I made on the first attempt.
Mutation-tested; the reversed order reproduces the silent no-op exactly.

### Two assertions that were wrong rather than failing

* `verify_seam`'s *"a split is still worth doing"* was a TODO wearing a test's
  clothes: it asserted `editor_lines > player_lines` and could only pass while
  the work was OUTSTANDING. It went red the moment `editor_draw.js` landed.
  Inverted to guard the achievement instead — what is left in the shared file
  must STAY below the player's reachable set.
* `V213e`'s grid probe COUNTED grid lines and divided. With only ~4 columns on
  a `tall` canvas, missing one boundary swung the count 4→3 and the aspect
  0.99→1.31, and it flipped red when an unrelated tune row changed the panel
  height by a few pixels. It now measures MEDIAN SPACING between adjacent
  lines, which a missed edge cannot distort — and which turned out to be more
  accurate too, reporting the true 8x6 where the count version had undercounted
  at 7x5 all along.

### Scratch probes must not be published as the project's result

`stamp_docs.py` now refuses a run whose suite names begin with `_`. A one-off
`_probe_mir.py`, written to look at a screenshot, put *"RUN NOT GREEN — 1
suite(s) failed"* into four docs. The v212 narrowing guard did not catch it:
that only engages when `RELEASE.md` describes the CURRENT tree, and a scratch
probe is usually run mid-change when it does not.

### The tool row is full

Four tools plus five controls did not fit a 375px phone, which is what drove the
v219 redesign: Select left Pad and Flip Mode moved to the overflow menu, and the
row is now eight controls that fit from 360px. Magnify is hidden below 641px —
pinch already zooms, and the button exists where the gesture does not — but **hiding it was not safe as
written**: the zoom HUD is where Fit lives, and `beginPinch` enabled the zoom
without ever revealing the HUD, so a pinch-zoomed user would have had no way
back to 100%. `beginPinch` now reveals it. Hiding a control is only safe when
nothing reachable ONLY through it becomes unreachable.

**CORRECTED — the buttons are NOT at 44px.** That claim was carried for several
releases and is wrong: `styles.css` sets `.tool-open` and `.toolbar .undo-btn`
below 640px, and the smallest control *renders* well under 44px on every phone
width, including the v214 row this note was written against. 44px is the desktop
value. Re-measured on the v219 tree:

    320px       bar 288px  WRAPS (safety net)   smallest control 34px
    360px       bar 328px  one row              smallest control 34px
    375px       bar 343px  one row              smallest control 34px
    393px       bar 361px  one row              smallest control 36px
    430px       bar 398px  one row              smallest control 36px
    641px+      bar 565px  one row              smallest control 40px

So the row was never at the tap-target minimum, and any argument that started
"there is no room because we are already at 44" was resting on a number that
had not been true for some time. Whether 34px is acceptable is a decision, and
`verify_layout.py` pins it in ONE place (`MIN_TOUCH_PX`) so raising it is a
deliberate edit rather than a discovery.

## Closed in v214 — seven defects from two external review passes

**Read this before touching media, document loading, or touch gestures.** All
seven came from external review of the sealed v213 archive. None was found by
the harness, which was green throughout: they are phone-specific gesture
lifecycle bugs and asynchronous ordering bugs, and a steady-state desktop suite
cannot see either.

### The two families

**Touch cancellation (3 defects).** `touchcancel` is a real termination that a
browser or OS can deliver INSTEAD of `touchend` — a system gesture, an incoming
call, a scroll taking the pointer. Cleanup keyed only to `touchend` leaves the
move listener installed and the drag state set, so the next unrelated touch goes
on driving a gesture that is already over.

* `editor_music.js` — three trim drags. Reproduced: after a cancel, a further
  move took `trimStart` 1.129 -> 3.386 with `.dragging` still set.
* `editor_menu.js` — the mobile sheet swipe. Kept `transition: none` and its
  `translateY`, and carried the cancelled drag from 50px to 90px.
* `editor_photo.js` — the eraser ring left painted with no finger near it.

**Asynchronous ordering (4 defects).** An operation that completes LAST is not
the operation the user is looking at. Each of these let a superseded completion
write into current state.

* Music decode, Pad and Flip. A=3.00s, B=9.00s, B lands then A: Pad left
  `currentAudioBuffer` at 3.00s while `audioDuration` read 9.00s. The poster
  crops from the buffer, so the track shown and the audio shipped were
  different recordings. Flip's stale completion also rewrote `audioDuration`
  and the trim window.
* `loadSkribl` document loads. A rewrote buffer, duration AND `trimEnd` of the
  open Skribl — and `loadSkribl` schedules `writeAutosave` 300ms later, so the
  corruption PERSISTS. This is the only one that reaches disk.
* Flip draft restore. `applyPayload()` clears `currentAudioBuffer` and
  `ensureAudio()` only builds the `<audio>` element, so `loadDraftFile` restored
  music with no decoded buffer. `buildSharePayload()` crops to the loop ONLY
  when that buffer exists and otherwise ships the whole sample: **588,082 B
  posted after a fresh selection against 3,528,082 B after restoring the same
  draft, both reporting the same 5.00s loop.** A user's saved work posting six
  times the audio, with only a `console.warn` to say so.
* Flip image `Image.onload`. The token guarded validation and the FileReader
  but stopped before the Image load, so `bgImageObj` (what `render()` draws)
  could be A while `bgImage` and the serialized payload were B.

### The rule that came out of it

**A generation token must be checked at the WRITE, not before the await.**
`musicSelectionSeq` already existed and Pad's handler checked it TWICE — both
before `decodeAudioData` was awaited, which proves only that the selection was
current when the decode STARTED. That is not the question. Every async
completion that writes shared state now re-checks its token immediately before
writing.

`skriblLoadSeq` (app.js) is the document-load version: stamped once per
`loadSkribl` and checked at all five completions. A uniform token beats a guard
per callback, because the failure mode is a callback nobody remembered.

Flip bumps `imageSelectionSeq` and `musicSelectionSeq` on draft load, because a
draft load is a DOCUMENT BOUNDARY — a selection made moments earlier must not
complete into the new document.

### THE TWO UNPINNED GUARDS — defence in depth, not demonstrated behaviour

Both are labelled in the source at their own line. **Do not read them as tested,
and do not delete them assuming the suite would catch it — it would not.**

1. **`loadSkribl`'s deferred `writeAutosave` guard** (app.js). Removing it
   reddens nothing. With the other four guards holding, the state at 300ms IS
   the current document, so a stale timer autosaves the RIGHT thing and no
   assertion can see the difference. Pinning it would need a COMPOUND mutation
   (this guard and another removed together), which is weaker evidence than
   none. It earns its place only if one of the others is ever removed.
2. **Flip's draft-boundary `imageSelectionSeq++; musicSelectionSeq++`**
   (flip.js, in `loadDraftFile`). Added beyond the review's report because the
   model is right — a draft load is a new document. Removing it reddens
   nothing: no scenario drives a selection that is still in flight when a draft
   file is opened. Reasonable, unproven.

The other three `loadSkribl` guards and every guard in the other six fixes ARE
demonstrated: remove one and its specific assertion goes red.

### The pre-seal mutation pass earned its place

Removing each guard independently found that **three of five were decoration**.
Two were then given scenarios:

* The **fetch** guard reddened nothing because a `data:` URL fetch resolves long
  before the second load starts. Gating `window.fetch` as well as
  `decodeAudioData` exercises it, and it fails properly: `elDur` drops to 3
  while the decoded buffer stays 9. **A third split-state variant, found only by
  the mutation pass** — the `<audio>` element the transport plays from swapped
  to A's track while the buffer the poster crops from stayed B's.
* The **base snapshot** guard reddened nothing because the payloads carried no
  `baseSnapshot`. Now pinned with two known snapshot colours: remove it and the
  open document's blue canvas is overwritten by A's red.

**Run the mutation pass BEFORE sealing, not after.** A guard with no assertion
behind it is indistinguishable from a comment.

### FOUR TEST DEFECTS, all false confidence

Each would have produced a wrong result, and three of them made a WORKING fix
look broken or a BROKEN one look fixed:

1. **Hand-copied the flow instead of calling it.** The draft probe replicated
   `loadDraftFile`'s steps inline; the replica diverged from the code the moment
   the fix landed and reported a working fix as ineffective. Drive the real
   entry point — construct a `File` and call `loadDraftFile(f)`.
2. **Read the wrong payload path.** `pay.music` instead of
   `pay.frames[0].music`. Both routes read `None`, so the comparison was
   vacuous and passed.
3. **Targeted the wrong element.** `#photoInput` instead of `#imageInput`.
4. **Released gated images by INDEX.** Each `loadSkribl` enqueues more than one
   image, so "index 1 is B's" released one of A's. The GATE caught it as a black
   canvas rather than letting the real assertion pass for the wrong reason —
   release by load RANGE instead.

Add to the earlier vacuous-range-window case and the window-listener
contamination case, and the pattern is clear: **when an assertion behaves
strangely, suspect the probe first.** A gate assertion that proves the scenario
actually entered the failing state is what turns these from silent passes into
visible failures.

### Techniques worth reusing

* **Gate the async primitive into a queue released by index or range.**
  `decodeAudioData`, `window.fetch` and the `HTMLImageElement.prototype.src`
  setter are all overridable in an init script. This makes "B finishes first, A
  finishes last" EXACT. A sleep-based version passes whenever the machine
  happens to order them the other way.
* **Assert the invariant the user cares about.** For the image race that is
  "rendered and serialized AGREE", not "both are B" — a split between preview
  and posted content is worse than either being wrong alone, because nothing on
  screen says so.
* **Assert equivalence between routes, not a fixed number.** The draft pin
  compares restore against fresh selection, so it fails if EITHER route changes.
* **Mutate per component.** All three music trim paths went red from one removal
  until the probe cleared stale WINDOW listeners between cases; per-path
  isolation is what tells you which path a fix belongs to.

### The touch audit is now an assertion (V214b)

The first audit was described as whole-tree and was not: it matched
`window.addEventListener` only, so element-local registrations were invisible —
which is exactly how the menu sheet and eraser cursor escaped it. **An audit
that matches a RECEIVER NAME is the same mistake as an assertion that matches a
word instead of a mechanism.**

`verify_tools.py` now scans ANY receiver every run, with a three-entry allowlist
(`scheduleAutosave` — save triggers, not drag cleanups) and a check that no
exemption is stale. It matches by RECEIVER, not handler name, because the menu's
correct fix uses a DIFFERENT function for cancel — `onTouchEnd` dismisses the
menu past 80px, so wiring cancel to it would let a gesture the OS took away
commit a dismissal the user never finished. The weaker invariant is stated at
the assertion site; the behavioural pins cover the semantics.

## Known-open, in the order worth doing

### Open at the v214 seal

**1. Bottom-toolbar redesign (owner-approved, deliberately deferred).** A
proposal exists to replace the current bar with Pen / Eraser / Shape / Select /
Color / **Tools** on Pad (Flip drops Shape), moving Image, Music and Magnify
into a labelled "Tools" action sheet — NOT another `•••`, because the top menu
already owns that symbol and two identical glyphs meaning different collections
is avoidable ambiguity.

Measured premise, verified before deferring: **Pad WRAPS at 320px** (Image and
Music orphaned on a second row, bar 113px tall against 68px at 375px) and
**Flip OVERFLOWS horizontally by 16px at 320px** — different failures, and
Flip's is worse because content is clipped with no cue that anything is missing.

Two things unresolved. The spec removes Undo/Redo from the bar without saying
where they go, and the header has NO free space: at 320px idle the actions block
is already 210 of 286px, and it is the same header that overflowed and wrapped
the record pill in the v213 bug report. And the owner noted Image/Music may be
COMBINED later, which would change whether a Tools sheet is needed at all.

**CLOSED IN v219 — but NOT the way the v215 note said, and that note was wrong.**

The bottom bar was redesigned. What actually shipped, measured on the v219 tree:

    Pad   320px  288px  WRAPS (safety net)   360-390px  326px  one row
          393px+ 359px  one row              641px+     565px  one row
    Flip  320px  scrolls (deliberate)        360px+     334px  one row

  * **The Image + Music + Magnify merge was tried and REVERTED.** A v215 note
    here claimed it shipped; it did not. Removing Select from Pad freed the room
    the merge was for, and measured, the merge then saved 3px — 305px against
    308px. It cost two real bugs while it was in. Image and music are two
    buttons again, restored verbatim from v214.
  * **What actually fixed the row was removing Select** (Pad-only, and it
    conflicted with Pad being a performance capture) and moving **Flip Mode into
    the ••• menu**.
  * **360px is the design target, 320px the safety net.** Pad wraps at 320,
    Flip scrolls — `flip.css` sets `overflow-x: auto` below 560px on purpose.
    Both keep every control reachable; `verify_layout.py` asserts reachability
    rather than a mechanism.
  * **The Pointer tool was never added.** It appeared in one review mockup and
    not the other, and it costs exactly the breakpoint the redesign bought.
  * **The 641px cliff is real and STILL unaddressed.** One pixel takes Pad's bar
    from 359px to 565px. Size classes, not a pixel breakpoint.

`harness/verify_layout.py` covers this. It is a NEW suite, as the deferral
required.

**A THIRD UNPINNED GUARD: the history-stack aliasing fix.** `makeHistoryState()`
does `strokes.slice()` — the ARRAY is copied, the point objects are not. Every
writer in this codebase APPENDS, so nothing had ever mutated an existing point
and the aliasing never mattered. Selection was the first thing that did: it
moved points in place, edited the undo snapshot too, and Ctrl+Z "succeeded"
while changing nothing. The fix is to snapshot FIRST and only then swap the
selected points for clones — **the order IS the fix**, and it is still in the
code and must stay there.

**v218 removed Select from Pad**, because it edited already-recorded points, so
replay drew a stroke at its NEW position at its OLD timestamp — a conflict with
what Pad is, not a bug in Select. Its seven assertions in `verify_tools.py`
(V213n) are PARKED behind `_SELECT_TOOL_ON_PAD = False`, not deleted, because
one of them — *"undo restores the pre-move coordinates EXACTLY"* — was the only
thing pinning the aliasing fix. Set that flag to `True` if Select ever returns
and the block runs again as written.

**2. THE RECORDING HEADER IS NO LONGER OVER BUDGET — this entry is CLOSED, and
the number it used to carry is a good example of why numbers go stale.** It read
396px needed against 355 available at 375px. That was true when measured on
v214. Moving Flip Mode into the ••• menu freed 40px of header, which is more than
the overage, and it closed as a side effect of a change made for discoverability.
Re-measured on v219: recording has **+124px of slack at 375px**, +109px at 360px.
The header stays one row and the wordmark collapses to logo-only under pressure,
which is `fitBrand()` behaving as designed rather than clipping.

**2. The two unpinned guards.** Described in the v214 section. Neither is
demonstrated; both are labelled at their own line in the source.

**3. `verify_mp4.py` has still never run anywhere but real Chrome.** Unchanged
since v211. The headless Chromium here reports WebCodecs present but supports no
H.264 profile.

**4. PostgreSQL is UNVERIFIED, not passing.** External review flagged this as
the more valuable of the two skips, because SQLite cannot establish the
multi-process and concurrency behaviour the suite covers. It is recorded by name
in `RELEASE.md` for that reason.

**5. The stray line from the v213 bug report remains unexplained.** A stroke
that shot off-screen mid-draw, reported once and never reproduced. The lead —
`getPos`'s `e.touches[0]` assumes the first touch is the drawing finger, which
a palm landing mid-stroke would break — is UNTESTED. Given that v214 found
three touch-lifecycle defects the harness could not see, this is more plausible
now than when it was filed.


**Comments no longer ship to users, and the guidance that followed from that is
withdrawn.** This section used to say that long reasoning belonged in
START-HERE and the code should carry "a short warning and a pointer", because
`app.js` reached every visitor uncompressed. There is still no build step, but
there is now a serve step: `skribl/jsstrip.py` strips comments from the response
and the file on disk is untouched. **Write the comment.** The v199 measurement
is that 32% of `app.js` was comment text and removing it from the wire cost the
source nothing — so a comment is no longer a trade against a viewer's download,
and the ratchet can no longer be fired by explaining yourself.

Two things to know before relying on that. Only URLs carrying a `?v=` bust are
stripped, because that is the only cache key available and lexing `app.js` costs
~90 ms; an unbusted request serves the file whole. And a comment inside a
template-literal `${...}` substitution survives the strip — there are currently
none, and `verify_jsstrip.py` would not fail if you added one, it would just be
bytes.


1. **`verify_mp4.py` has never run.** Headless Chromium has WebCodecs but no
   H.264 encoder, so it SKIPS. MP4 export works in the real world (confirmed by
   hand on an iPhone) but no suite has proven it. The CI `mp4` job runs it on
   real Chrome.
2. **Pad's stylus path is unverified on a device.** `touchType` is an iOS
   extension with no `Touch` constructor support, so an Apple Pencil stroke
   cannot be synthesised in Chromium. An Android stylus draws at constant width
   — Android touch events expose no `touchType`.
3. **The record does not cover every suite.** See RELEASE.md for which
   reported and which skipped; CI is configured for the rest.
4. **A full single-invocation run hangs.** Name suites explicitly, in batches.
5. **The two editors duplicate their controllers.** `app.js` and `flip.js`
   drive the SAME shared partials. Sizes are deliberately not quoted here —
   three documents carried three different line counts for `app.js` and none
   matched the tree. Run `wc -l skribl/static/app.js skribl/static/flip.js`. Five controllers have been
   extracted to `lib/` — `eyedropper`, `recentcolors`, `segslider`,
   `smoothing`, `colorselect`, `photofit` and `looptrim` — and each is pinned
   by parity assertions that prove both editors CALL the shared module, not
   merely that they behave alike. What remains in both photo and music is the
   DRAWER WIRING rather than the logic: the fit slider, drag-to-reposition,
   opacity/blur/zoom, the waveform renderers (`drawWaveform`,
   `drawZoomWaveform`), `updateTrimUI`'s DOM half and the preview transport.
   The pure arithmetic under both is now shared. Count the references before
   planning the work rather than trusting a number in a handoff: the counts
   quoted between sessions have not matched the tree.

   **TWO DECISIONS ARE WAITING HERE.** Neither is an assistant's to make.
   (a) The third photo fit is `'stretch'` on Pad and `'fill'` on Flip for the
   same button, and the shared partial branches to emit both. `photofit` makes
   them one mode behaviourally, but unifying the spelling changes what Flip
   persists in existing drafts and posts — a live-data decision.
   (b) Dragging a trim handle past the 20s cap **constrains** the handle on the
   main track and **slides** the far end on the zoom track and nudge. Both
   surfaces do both, identically, so nothing is broken — but it is one control
   behaving two ways depending on which track you grabbed. `looptrim` makes the
   choice a named argument, so picking one is now a small edit at six call
   sites instead of a rewrite. Every fix must be made twice, and most bugs this session were one
   surface having a fix the other lacked. Extracting the shared drawer
   controllers is the highest-value refactor available. Use an AST, not a
   regex; `node` is available. See docs/REFACTOR-v132.md.
6. **`app.js` serves both editor and player**, so every viewer downloads the
   authoring surface. A split was ATTEMPTED and REVERTED.
7. **Payloads are ~476 KB inline in Postgres — the S3 backend now EXISTS**
   (`S3Store`, foot of `skribl/storage.py`, `SKRIBL_MEDIA_BACKEND=s3`).
   SigV4 signed with the stdlib, no boto3, so `requirements.txt` is unchanged.
   `verify_s3.py` drives it against a fake bucket that RECOMPUTES the signature
   and 403s a mismatch, with a bad-secret negative control.
   **Objects are served through /media/<key>, not as bucket URLs.** The obvious
   design puts the bucket URL in the payload, and `routes.media` used to say an
   S3 deployment "never routes through here" — which would route around the
   authorisation that route exists for, re-opening the bug where a private
   Skribl's audio was readable by anyone holding the URL. Put a CDN in front of
   /media/<key> instead; the response is already immutable for public-only
   objects and `private, no-store` otherwise, a distinction a bucket cannot make.
   **What is NOT proven: Amazon.** Nothing here can reach a real bucket, so the
   requests are proven well-formed and correctly signed, not accepted. Point it
   at MinIO or a test prefix once; that is a minute of work and closes it.
   Layers are no longer blocked on storage.
8. **Opaque custom-store media URLs** cannot have their associations
   reconstructed. Severity is lower than it sounds; see ARCHIVE-README.
9. **Multi-take** has no data model, by design.

---

## Things that will bite an unwary assistant

* **NEVER edit a released Alembic migration.** `RELEASED.txt` freezes every
  digest and `verify_migrations.py` fails if one changes.
* **`view` does not show the user anything.** It renders an image for the
  assistant only. To show someone a screenshot, write it to
  `/mnt/user-data/outputs/` and call `present_files`. Saying "here it is" after
  a `view` call is describing something they cannot see.
* **Measure rendered geometry, not arithmetic.** Flex shrinks controls before
  anything overflows, so summing child widths reports room that is not there.
  Force the candidate into the DOM and read `scrollWidth` against
  `clientWidth`. Likewise `offsetParent`, not the `hidden` property.
* **An explicit `display` defeats `[hidden]`.** Hit three times. Scope layout
  rules with `:not([hidden])` or pair them with `[hidden]{display:none}`.
* **`classList.toggle(name, undefined)` TOGGLES.** An `&&` chain that can yield
  undefined must be wrapped in `!!` — this made two colour swatches appear
  selected at once.
* **An inline style beats any stylesheet rule.** `setTool()` writes
  `pad.style.cursor` inline, so cursor changes must also be inline.
* **Top-level `let` is not on `window`.** `window.frames` is the browser's
  frame collection and `window.fps` is the element with `id="fps"`. Read
  editor state through a bare identifier, not off `window`.
* **A retry must accept on the property the assertion checks.** A WebM test
  retried on byte count and asserted on duration; it flaked three times.
* **The two editors bind DIFFERENT event families.** Flip uses Pointer Events,
  Pad uses `mousedown`/`touchstart`. Code written for one is dead in the other,
  silently.
* **Finish all documentation BEFORE the final harness run.** `run_harness.sh`
  calls `stamp_docs.py` itself, and the run recorded LAST is the one stamped —
  so the recorded set must be the final invocation. Regenerate `SHA256SUMS`
  after, and delete any scratch probe suite first or it ships.
* **A skip is not coverage.**

---

## Running it

    pip install -r constraints.txt --require-hashes    # the pinned lock
    python -m alembic upgrade head                     # NOT create_all()
    gunicorn app:app

    ./harness/run_harness.sh verify_move.py            # name them; a bare run hangs
    python3 harness/stamp_docs.py                      # docs from LAST-RUN.txt

`pip install -r requirements.txt` also works. What does NOT work is
`-r requirements.txt -c constraints.txt` — the lock carries hashes, which puts
pip in `--require-hashes` mode, and that mode rejects version ranges.

---

## A note on process

Almost every bug this session was found by RUNNING something, after the code
read correctly — and several were found by the owner on a real phone after the
suite was green. Screenshots caught what assertions did not: a canvas picker
that painted a purple bar over its own menu passed 21/21 first.

The pattern worth carrying: **when a change touches a surface, write the
assertion that reproduces the OLD behaviour first**, and prefer measuring what
is rendered over what the code was told to do.
