# START HERE — Skribl v204 session primer

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

    cd skribl-v204 && sha256sum -c SHA256SUMS | grep -c ': OK'    # expect 172
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

Read this and `ARCHIVE-README.md` before changing anything. Everything below was
verified by running it, not by reading the code.

**Upload the current sealed zip (`skribl-v204-sealed.zip`) alongside this file.**
Unzip it; it produces a folder `skribl-v204/`. `git init` goes INSIDE that
folder, not above it. (Historical sections below narrate v199-era work; the
numbers in prose are that era's, not this build's.)

---

## What this is

Skribl is a browser drawing/animation tool — **Pad** (records a drawing and
replays it with its timing), **Flip** (frame-by-frame animation) and a
read-only **Player** — packaged as a Flask blueprint to drop into a social
platform.

    SKRIBL_VERSION   v191      (skribl/core.py — the archive name derives from it)
    client assets    v131      plus six integration edits and the v142-v179 work
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
**PASS WITH SKIPS — 2199 assertions across 59 suites, none failing, 1 skipped** on sqlite as of v204 (tree `2e14c9170240`).

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

    cd skribl-v204 && sha256sum -c SHA256SUMS | grep -c ': OK'      # expect 172
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
* Render builds on **Python 3.14** while `constraints.txt` carries cp312
  hashes, so production resolves `requirements.txt` fresh and is NOT running
  the versions the harness tested. Regenerate the lock on the real target, or
  pin the runtime.

---

## Decisions that are the user's, not the assistant's

**The migration chain collapse is CLOSED.** It required that no database had
run v135-v141. The live Postgres is stamped at head `f0a3d81b47e2`. Do not
propose collapsing it again.

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

## Known-open, in the order worth doing

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
