# START HERE — Skribl session primer

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

    cd skribl-v*                                    # the name derives from SKRIBL_VERSION
    grep -Ec '^[0-9a-f]{64} ' SHA256SUMS            # N: the manifest's own entry count
    sha256sum -c SHA256SUMS | grep -c ': OK'        # must equal N
    grep -m1 'tree hash' harness/RELEASE.md
    python3 -c "import sys;sys.path.insert(0,'harness');import release_run as r;print(r.tree_hash())"

**What a visitor downloads on a shared link — RUN IT, do not read it:**

    ./harness/run_harness.sh verify_player_isolation.py

Its last assertion prints the whole payload broken down — JS, HTML and CSS
separately, their sum, and the gzipped figure — and the suite fails if any part
grows past its ratchet. **The numbers are deliberately not repeated here.** This
block used to carry nine of them across two tables, every one measured at v199,
and they were still sitting here unchanged dozens of releases later describing a
player that had shrunk under all of them. That is the same failure the paragraph
above this one warns about, committed fifteen lines after warning about it.

One of those numbers is worth knowing as a SHAPE rather than a value: the
gzipped "on the wire" figure is roughly a quarter of the source total, and must
never be quoted as "the player's JavaScript" — the suite says so at the
assertion itself.

`skribl/jsstrip.py` removes comments from the RESPONSE — the files on disk keep
every word, which is the only reason this was allowed at all — and
`harness/tools/cssgraph.py` classifies rules inside a media block instead of
keeping the whole block whenever one rule matched. Neither moved a byte of
source.
`verify_jsstrip.py` is the gate on the first (Chromium compiles and evaluates
every case; the lexer checking its own output proves nothing) and
`verify_cssplit.py` on the second (eleven scenes, pixel-identical).

## Invariants, and what enforces each one

These outlived the releases that produced them. Each line is a rule a change
can break, followed by the suite that would catch it — **checked by grep, not
recalled.** An invariant with no enforcer is marked as such, because "we all
know that" is how a rule stops being true.

These rows replaced the "Closed in vNNN" narratives (708 lines, v282) and then
the whole HISTORICAL NARRATIVE band (1,370 lines, v283). The reasoning behind
each release lives in `DECISIONS.md`; the *history* lives in git. What has to be
here is the rule you can break tomorrow.

| invariant | enforced by |
|---|---|
| A route flushes; it never commits the shared session. | `verify_txcontract.py` (AST over every module, exemptions named per function) |
| Undo stores a DRAWING, not a screenshot — replay reconstructs from strokes. | `verify_move.py`, `verify_stamps.py`, `verify_liquify.py` |
| An anonymous post is revoked by a CAPABILITY, never by an account. | `verify_deletion.py`, `verify_posted.py` |
| Possess the id and the key → revoke through the product, whatever this browser remembers. | `verify_posted.py` |
| A 404 from DELETE means UNKNOWN. The client must not turn it into success. | `verify_posted.py` |
| The player carries no editor-only module. | `verify_player_isolation.py` |
| The player's JS stays under its ratchet, measured on what is SERVED (comments stripped), not what is on disk. | `verify_jsstrip.py`, `verify_player_isolation.py` |
| `[hidden]` is honoured on every control that uses it. | `verify_layout.py`, `verify_help.py`, `verify_move.py` |
| No readable text uses a token that fails WCAG AA. | `verify_a11y.py` |
| A token that cannot pass AA must be USED somewhere the requirement does not reach, or not exist. | `verify_a11y.py` |
| Every `aria-modal` surface is routed through `SkriblModal`, and the population is generated from the DOM and the JS source, not listed. | `verify_a11y.py` |
| Every id on a rendered page is unique — `getElementById` and `url(#…)` both take the first match. | `verify_a11y.py` |
| No page loads a `lib/` module nothing on that page reads. | `verify_surfaces.py` |
| No stylesheet keeps a rule-set whose every selector is unmatched. | `verify_surfaces.py` |
| Every route the blueprint registers is named in at least one document. | `verify_docs.py` |
| Every host seam `create_blueprint()` accepts is documented in `docs/INTEGRATION.md`. | `verify_docs.py` (reflection over the signature) |
| Every `SKRIBL_*` the code reads is named in a doc or `.env.example`. | `verify_docs.py` |
| No document hand-types a tree hash or an assertion count outside the generated stanza. | `verify_docs.py` |
| The generated doc tables match their source. | `verify_docs.py` → `gen_docs.py --check` |
| A skipped suite contributes ZERO assertions and is not evidence of coverage. | `run_harness.sh` emits it; `stamp_docs.py` writes it into every stanza |
| The release run must be the LAST harness invocation — anything after it rewrites `LAST-RUN.txt`. | `verify_docs.py` (RELEASE.md/LAST-RUN.txt agreement), and the guard in `stamp_docs.py` |
| Every suite on disk appears in exactly one `release_run.py` batch. | `release_run.py` refuses to start otherwise |
| The assertion output format is a contract `run_harness.sh` parses. | `harness/assertions.py` self-test, run by `verify_docs.py` |
| Every tool emits ORDINARY STROKE POINTS — a point carries no field outside `{x, y, color, size, t, start, erase}`. A shape primitive or brush id would be a schema change every existing post has to survive. | `verify_tools.py`, `verify_inline.py`, `verify_tween.py` |
| Replay joins consecutive points, so any group holding two distant places draws a line across the canvas. Flip refuses the share outright when `strokeGroups` does not account for every point. | `verify_strokegroups.py` |
| `pauseMode` is serialized and preview speed is not — a setting that changes what the drawing IS travels with it; one that changes how you review it does not. | `verify_tools.py` |
| COMPOSE MODE PUBLISHES NOTHING. "Add to post" hands the payload to the host; only the host publishes. | `verify_compose.py` |
| The compose handshake targets a specific origin, never `'*'`. | `verify_compose.py` |
| A host must limit its own compose view — Skribl's limiter cannot follow the payload into somebody else's composer. | `verify_compose.py` |
| When the drawing stops, the music stops. | `verify_audiosession.py`, `verify_inline.py` |
| How long a page lasts and how much of a drawing page is revealed are `lib/holdtiming.js`'s answers, not each surface's. Four surfaces render a reveal and they agreed in the middle of the range and disagreed at both ends. | `verify_sharedrules.py`, `verify_inline.py` |
| A drawing page is EXEMPT FROM fps everywhere, the exported file included — a file has frames, so it samples the page's millisecond timeline rather than re-denominating the page in slots. | `verify_sharedrules.py` |
| Every Draw-on page begins empty, reveals monotonically, reaches its COMPLETE recorded state, and only then yields to the next page. This is about the COMPOSITION of indexAtMs, progressAt and dueCount — all three were individually correct while the terminal state could never occur — so it is asserted through the actual surface clock, on both players. | `verify_sharedrules.py`, `verify_inline.py`, `verify_hold.py` |
| Every mandatory external lane writes an attestation NAMING THE TREE it describes. A lane that is merely claimed by a CI job is pending, not covered — existence of a job is not a result. | `verify_docs.py` (mechanism calibrated against a wrong-tree attestation) |
| Both editors build the pen palette from `lib/palette.js` — same list, same order, from the lib and not from a copy. | `verify_parity.py` |
| Every grey the chrome paints is a token, not a literal — including the `rgb()` function form, which the first version of the ratchet could not see. | `verify_surfaces.py` |
| `color`, `fill` and `stroke` hold no colour literal except `#fff` and `#0d0f14`. A red is not a neutral, so a grey audit walks straight past it. | `verify_theme.py` |
| A token named for the CANVAS is not chrome and is exempt — naming it in `:root` is what makes that a decision rather than a literal somebody missed. | `verify_surfaces.py` |
| A run whose suite names begin with `_` is a scratch probe and must never be published as the project's result. | `stamp_docs.py` refuses it |
| Hiding a control is only safe when nothing reachable ONLY through it becomes unreachable. | **no enforcer** — found by looking; `beginPinch` revealing the zoom HUD is what made hiding Magnify safe |
| A colour ratchet cannot see a mark that is white ON PURPOSE — five vanished in light mode and were found by eye. | **no enforcer** — `#fff` is exempt because it is nearly always text on a coloured fill |

**One from v179 did NOT survive, and is recorded here rather than quietly
dropped.** "Segmented controls state a height" was true when written; `flip.css`
now says `--seg-h intentionally NOT set`, because the control has only been
measured on one machine and its height follows the installed font. Opting it in
would mean choosing a number for every viewer. The rule was superseded by a
deliberate decision, and START-HERE asserted the old one until v282.

### What the gates caught, including one I built last release

**`verify_a11y`'s modal census passed over both new dialogs.** The v280 gate
enumerated `[aria-modal="true"]` from the live DOM and primed the one
runtime-built dialog it knew about by name. Two more arrived in `recoverykey.js`
and the census could not see them, because a sweep taken at load cannot see a
node that does not exist yet. That is the hole the v280 note warned about, in
writing, one release before walking into it. There is now a **JS-source
census** beside the template one: every non-minified `.js` under
`skribl/static/` that mentions `aria-modal` has its assigned element ids
extracted and required to be recipe-backed, so the next runtime-built dialog
fails the suite instead of slipping through.

**The wrong-key test passed with the bug fully restored.** Deleting a row calls
`confirm()`, Playwright dismisses dialogs by default, so `destroy()` never ran
and the assertion was checking that nothing had changed after nothing had
happened. It drives `destroy()` directly now. Measuring something ADJACENT to
the claim is the recurring failure of this whole sequence of releases — it has
happened in most of them, to me, in assertions I had just written — and it is
the argument for mutating every new assertion rather than trusting a green
one.

### `verify_a11y.py` generates its population now

Three of seven `aria-modal` surfaces were routed through `SkriblModal`; the
suite tested one of the three by hand and passed. The audit named the shape:
*a global semantic claim should generate its test population from the DOM, not
from a manually chosen specimen.* The suite had already learned to assert
behaviour instead of attributes, and then asserted the right thing about the
wrong population — the same error one level up.

All eight surfaces route through the utility (the eighth is the new recovery
panel). Section 2 reads `[aria-modal="true"]` out of the live DOM; a surface
with no recipe **fails** rather than being skipped, a recipe naming a deleted
surface fails too, and a template census backstops the dialog that lives behind
an unrendered branch. A dialog built at runtime escapes a census taken at load,
so `recoverykey.js`'s overlay is primed before the sweep — anything added the
same way must be primed too, and the template census is what will say so.

**It immediately found a defect in `modalfocus.js` itself.** `close()` checked
`isConnected`, but an opener can be present and `display:none` — the leave
confirm closes the menu holding its opener on the way up. `focus()` was then a
silent no-op and the user landed on `<body>`: the exact outcome the utility
exists to prevent, reached through the one door it did not cover. It checks
`offsetParent` now and falls back to whatever had focus when the dialog opened.

### Two gates that were representatives of a global contract

`verify_txcontract.py` scanned two files — the two where the v224 violation
happened to be found — so `takedown.py` could have committed the shared session
from request-shaped code and stayed green. It scans every module now, by AST
rather than by grep, with exemptions named **per function**. Per function
because widening it produced a finding at once: `storage.py` is a library a
host imports and only its batch function may commit, so a file-level allowlist
would have waved the whole module through. Its stale-exemption check then
caught an exemption I had granted on an assumption, for a function that does
not commit at all.

`verify_docs.py` gates the CI-cost claim. Two of this release's findings were
stale statements in **source comments**, where the v279 sweep never looked: 22
lines above the delete routes still calling the v278 identity gate "the whole
design", and the header of `harness.yml`, which used to say a heavy CI day had
burned a monthly Actions allowance. This repository is public and every job
runs on `ubuntu-latest`, so there is no allowance — see `CLAUDE.md`. The gate
asserts the half that is checkable offline: while every runner is standard,
nothing current may call this project's minutes finite or billed. Move to a
larger runner and the claim becomes sayable again and the gate stands down by
itself.

### `verify_a11y.py` — keyboard and assistive technology, as its own suite

Added after an accessibility audit of v278, and a suite rather than more of
`verify_ux.py` because of the audit's structural point: the tree carried
thousands of assertions — the count is in `harness/RELEASE.md`, never typed
here — while basic keyboard failures were visible in the source. Three
playback scrubbers were pointer-only, two of them declaring `role="slider"`
with no tabindex, no `aria-valuenow` and no key handler — announcing a control
that could not be operated. Every `aria-modal` dialog did nothing about
focus — this said "Five" until v280, when counting them for the enumeration
gate found seven.
Visible slider captions were not labels. Segmented controls kept selection in a
CSS class. Nothing announced that a post had succeeded or failed.

Its own rule: **assert the behaviour, not the attribute** — `role="slider"`
being present is exactly what was true while it was broken. It presses keys and
reads what moved, focuses things and reads where focus went.

Two things it caught that the audit had not: five unnamed controls in Flip's
share sheet and image drawer, and `--text-faint-2` on `.accordion-count` at
3.47:1.

And one about ITSELF. The contrast gate's first version exempted any line
matching `--text-`, meaning to skip the token definitions — but
`var(--text-dim)` contains `--text-`, so it skipped every use as well and the
check was vacuous. Putting a failing token back on readable text left it at
37/37. Definitions are excluded by shape now.

### Identities are opaque text

`skribl_posts.user_id` is `String(255)` behind a `TypeDecorator`, not `Integer`.
The column was Integer while `docs/INTEGRATION.md` advertised "your user id",
so a host using UUIDs, ULIDs or an OAuth subject could not integrate at all.
Integer hosts are unaffected — 42 stores as "42" and both sides of every
comparison normalise. `author.id` in the API is a JSON string now.

**Both sides, not just the argument.** Normalising only the incoming id passed
every suite that goes through `create_post` and failed `verify_privacy`, which
builds `SkriblPost(user_id=7)` in memory and never flushes it — so the
TypeDecorator never ran and an author could not read their own private post.
The type covers what is stored and loaded; the comparison covers what was never
persisted. Both are needed and for different reasons.

### The MP4 attestation — what a seal can honestly say about H.264

`verify_mp4.py` skips wherever Chromium is the browser: Playwright ships the
open-source build, which has WebCodecs but no H.264 encoder. (Probing
`VideoEncoder` on `about:blank` reports "no WebCodecs at all" and is
misleading — the suite checks on a real page, where the API is present and the
three `avc1.*` profiles are all unsupported.)

The `mp4 (real Chrome)` CI job covers it, and until v279 its result never
reached the archive: the seal said `skipped 1 (verify_mp4.py)` and nothing
about whether the gap had been closed elsewhere, so a reader could not tell
"not covered" from "covered somewhere you cannot see". An audit of v278 called
that an evidence gap rather than a defect, which is exactly what it was.

`harness/MP4-ATTESTATION.txt` is that job's answer, and `RELEASE.md` now
carries an `mp4 (H.264)` line computed from it. **The tree hash in the
attestation must match the one the release froze** — evidence about different
code is worse than no evidence, because the seal would then assert coverage it
does not have. Three outcomes, all stated rather than implied: verified, STALE,
or NOT VERIFIED with the command to fix it.

It never blocks a release. Whether an unverified MP4 path is shippable is a
product decision; the seal's job is to state the fact.

The file is excluded from BOTH tree-hash lists (`release_run.GENERATED` and
`run_harness.sh`'s `_tree_files`) for the same reason `RELEASE.md` is: it names
a hash, so including it would make writing the evidence change the thing the
evidence is about. The two lists must stay identical — that is the v221 defect.

### Environment traps, in the order they will bite

* `apt-get update` fails outright until the blocked nodesource repo is moved
  aside: `mv /etc/apt/sources.list.d/nodesource.list /tmp/`. Then install
  postgresql, start it, create the `skribl` role and database.
* `pip install -r constraints.txt --require-hashes --break-system-packages`, and
  `python3 -m playwright install chromium`.
* **PILLOW IS NOT IN requirements.txt AND THREE SUITES NEED IT.** `verify_cssplit`
  and `verify_smudgeblur` CRASH without it; `verify_sizeclass` is worse — it
  reports 81/82 with a single tidy failure while **eight of its assertions
  silently do not run**, which is the shape of problem this whole harness exists
  to refuse. With Pillow it is 89/89. A v273 release run reached batch 42 of 44
  before these three sank it. `pip install Pillow`.
* **PLAYWRIGHT MUST MATCH THE CHROMIUM BUILD ON DISK.** Check with
  `ls /opt/pw-browsers` (or wherever `PLAYWRIGHT_BROWSERS_PATH` points): build
  1194 wants playwright 1.56.0, and 1.62 fails to launch with an executable-not-
  found error that reads like a missing browser rather than a version mismatch.
* **THE INTERPRETER MUST BE THE PINNED 3.12, and a container's default may not
  be.** `verify_docs.py` fails the run outright when `.python-version` and the
  running interpreter disagree — deliberately, because evidence produced on a
  different interpreter from the deployed one describes nothing. If the default
  `python3` is not 3.12, build a venv from the 3.12 that is installed and put it
  on PATH ahead of everything for the whole run.
* **THE SEAL AND CI DO NOT TEST THE SAME THING, and CI's mode is the stricter
  one.** `release_run.py` runs its batches SEPARATELY, each getting a fresh
  server and database on a quiet machine. CI runs every suite in ONE invocation
  on a contended two-core runner. (Both counts were typed here once and both
  went stale — the suite count was caught by `verify_docs`, the batch count was
  not, because nothing checks it. `release_run.py --dry-run` prints them.) Anything sensitive to write contention or to
  cross-suite state therefore passes the seal and fails CI — which is exactly
  what happened: a 500 under SQLite lock contention (v274) failed main's sqlite
  job on one push and passed it on the next, with the bug unchanged in both,
  while v273 sealed green TWICE on this box. **A green seal is not a prediction
  that CI will be green — and a CI failure that clears itself on the next push
  is not thereby a flake.** If a suite fails only in CI, do not
  reach for "flake": reproduce it by loading the machine —
  `for i in $(seq 1 12); do (while :; do :; done) & done` — and it will very
  likely fall over locally too.
* **A suite's subprocess servers send stderr to DEVNULL, so the traceback you
  need is thrown away.** `verify_review.py`'s `server()` helper does this. When
  a request 500s inside a suite-launched server, patch that redirect to a file
  before theorising — the v274 bug named its own cause in the first traceback
  captured, after the wrong writer had been suspected on reasoning alone.
* **PostgreSQL: if `verify_postgres` SKIPS, the seal is weaker than the last
  one.** It wants `postgresql://skribl:skribl@127.0.0.1:5432/skribl` (override
  with `SKRIBL_PG_DSN`), and it skips rather than fails when it cannot connect —
  so a run can go green having never tested the multi-process behaviour SQLite
  cannot establish. `pg_ctlcluster 16 main start`, then create the role and
  database, then confirm the suite reports 20/20 rather than SKIPPED.
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

**THE JS TARGET IS MET. This section argued for years that it could not be, and
that argument is over.** `verify_jsstrip.py` asserts the player reaches the
153,600 B target after the serve-time strip, with room to spare, and
`verify_player_isolation.py` holds the ratchet below it. Run either for the
number; it is not typed here, because every previous number in this section
outlived the tree it described by dozens of releases.

How it was won, and why the old plan was the wrong plan:

* **Self-contained IIFEs** — `editor_export`, `editor_post`, `editor_menu`.
* **Wiring extraction** (move STATEMENTS, leave functions and state) — both
  drawers: `editor_music`, `editor_photo`.
* **The carves — there are NINE, not the four this file used to name.**
  `editor_draft`, `editor_draw`, `editor_export`, `editor_menu`,
  `editor_music`, `editor_photo`, `editor_post`, `editor_shapes` and
  `editor_tune` are all absent from the player. Pad loads every one; Flip loads
  only `editor_shapes`; the player loads none. `verify_player_isolation.py`
  reads that list OFF DISK now rather than from a hardcoded tuple of four, so
  five of them were unguarded until v273 and a tenth would be covered the day
  it lands.
* **The serve-time comment strip** — `skribl/jsstrip.py` removes comments from
  the RESPONSE; the files on disk keep every word. This is what closed the gap,
  and it moved no source at all.

**The plan this section used to prescribe was function relocation, and it was
never executed.** It held that shared paths NAME the editor-only functions, so
moving them means dependency inversion rather than relocation — and that even
moving all of them still would not reach the target. Both statements were true
of the tree they were measured on. Neither is now the binding question, because
the strip got there without moving a function. The AST tool built to de-risk
that relocation (`harness/tools/refgraph.js`) was DISPROVED — it fails its own
superset gate and would move the four functions the v132 attempt got wrong. The
v132 failure was load order, not classification. Read `docs/REFACTOR-v132.md`
before planning anything here.

**WHAT IS ACTUALLY OUTSTANDING IS CSS, NOT JS.** `verify_player_isolation.py`
carries a `CSS_TARGET` and the player's stylesheet is well above it, under a
ratchet (`CSS_RATCHET`) set far looser than the current value. That is the open
size question, and it is a different problem from the one this section spent its
life on: `player.css` is generated by `harness/tools/cssgraph.py`, so the lever
is the classifier, not a carve. See the CSS-ratchet decision under "Decisions
that are the user's" — the ratchet's slack is an owner call.

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

**Read this file, `DECISIONS.md` and `ARCHIVE-README.md` before changing
anything.** The per-version narrative lives in `docs/HANDOFF.md` and in git
history. Everything below was verified by running it, not by reading the code.
(Historical sections below narrate older work; the numbers in prose are that
era's, not this build's.)

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
    client assets    app.js / flip.js / styles.css / flip.css and lib/ — one
                     continuous line of work; the per-version story is in
                     docs/HANDOFF.md and git history
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
**PASS WITH SKIPS — 4752 assertions across 97 reporting suites (99 on disk, 2 skipped), none failing** on sqlite as of v289 (tree `8266b983acc6`).

These totals are generated by `harness/stamp_docs.py` from `harness/LAST-RUN.txt` — never typed. `verify_docs.py` fails if any doc disagrees with the recorded run.

Skipped in that run: verify_mp4.py, verify_postgres.py. A skipped suite contributes zero assertions and is not evidence of coverage.
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

    cd skribl-v*
    grep -Ec '^[0-9a-f]{64} ' SHA256SUMS            # N: the manifest's own entry count
    sha256sum -c SHA256SUMS | grep -c ': OK'        # must equal N

    # v224: the expected count is no longer TYPED here at all. It used to be,
    # with a note explaining that you should compare against the manifest
    # rather than against the number — which is an odd thing to write beside a
    # number, and it went stale anyway every time the file set changed. The
    # manifest already states its own size; asking it is strictly better than
    # asserting it. `verify_docs.py` still checks any count that IS typed
    # elsewhere against SHA256SUMS.

---

## The live demo

`skribl-live-demo.onrender.com` — a Render Starter web service ($7/mo) deployed
from GitHub (`MrBlood/skribl-live-demo`, branch `main`), backed by a paid
Postgres Basic instance ($6/mo), running the `inline` media backend.

**The deployed code can lag this tree** — Render deploys from `main`, so
anything merged is live after its build finishes and anything unmerged is not.
Check the version label in the app footer before diagnosing anything.

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
run v135-v141. The live Postgres has run at least through `f0a3d81b47e2`. Do not
propose collapsing it again.

**The deploy now runs `alembic upgrade head` — via the RENDER START COMMAND,
not the Procfile (v270).** v267 wired the migrate-then-serve command into the
Procfile and declared the drift closed; **Render does not read Procfiles**
(that is a Heroku convention), so migrations still never ran on deploy, which
the v269 outage proved when the db rate limiter met a `skribl_rate_events`
table the stamp had promised and nobody had built (DECISIONS v270). The
authoritative setting is the Render dashboard's **Start Command**:
`python -m alembic upgrade head && gunicorn app:app`. The Procfile carries the
same line for Heroku-convention hosts and local reference, but changing it does
NOT change the deploy. `skribl/migrations/env.py` also runs a pre-flight that
recreates a baseline table a stamped-over database is missing, so the chain can
run at all on a database whose stamp lied.

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
*"Take saved — Play to preview, or Add take to draw more"* — and the way
forward is an "+ Add take" pill floating on the locked canvas; since v288 the
header's Record button is not even there on a finished take (it is a Stop
button while a take runs, and appears idle only over unrecorded ink).
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

**The CSS ratchet decision is STILL OPEN, and the restatement it was given last
time has itself gone stale — read the numbers off the suite, not off this
paragraph.** It was long carried as "set at exactly the current size, so it has
no headroom by construction". That was true when `player.css` did not exist and
the player linked the whole of `styles.css`. It does exist, so `CSS_RATCHET` sits
well above what the player actually links and the mechanism has real headroom —
the same inert state the JS ratchet was in when it was reading gzipped lengths,
arrived at a different way.

**The size of that headroom has changed twice since anyone wrote it down here,
so this paragraph no longer quotes it.** `verify_player_isolation.py` prints the
ratchet, the linked total and the target on one line; run it. Note also that the
linked total has GROWN since the restatement, which is precisely what an inert
ratchet permits and why the decision matters.

The decision itself is unchanged and is the owner's: set the ratchet at today's
value (the convention the JS ratchet and the comment beside `CSS_RATCHET` both
follow) or at something with deliberate slack. Leaving it alone has now made it
staler twice, which is worth knowing when deciding.

---

## The shared modules, all of them

`skribl/static/lib/` is where a rule lives once instead of twice. The two
editors are separate controllers — app.js and flip.js — so anything they both
obey drifts unless something owns it, and `verify_parity.py` exists because it
did. Eight of these had never been named in any document, which is how a
module gets forgotten and reimplemented.

Surfaces are read from the template `<script>` tags; the descriptions are each
file's own opening line. `verify_docs.py` fails if a lib here is named nowhere.

ONE ENTRY READS "HOST" RATHER THAN A SURFACE. `composehost.js` is the pad
button's lifecycle for a host's own composer, so nothing Skribl serves loads it
except the `/feed` preview standing in for a host. It is in `lib/` for the same
reason everything else is — the alternative is every host writing the same four
rules, three of them right — but it is the one module whose reader is somebody
else's page. It is not in `skribl_inline_assets()` and carries its own byte
ratchet in `verify_inline.py`, separate from the embed's: a page that only
DISPLAYS Skribls never composes one and must not be charged for it.

"in-post" is the fourth surface: the player a host embeds in a feed post (`skribl/static/inlineplayer.js`, `templates/skribl/_skribl_inline_player.html`).
It loads THREE of these — `canvassizes.js` for a legacy payload's default
shape, `holdtiming.js` for how long a page lasts and how much of one that
draws itself has been revealed, and `audiosession.js`
for the iOS ringer fix — and its own code reads all three. This said "exactly
two ... and reads nothing else from `lib/`" until v281; `audiosession.js`
arrived with the ringer fix and the sentence did not move.

`sharecard.js` USED to be a fifth, and v281 dropped it. The idle poster's crop
is literals in `inlineplayer.css`; nothing in the page ever read
`window.SkriblShareCard`. The only reader was `verify_inline.py`, evaluating
`band()` in the page to check those literals still agree with the module's
arithmetic — a real assertion that did not need the payload. The suite injects
the module now (by `evaluate()`, since the page's CSP correctly refuses an
injected `<script>`), and the embed ratchet came down 32,000 → 31,000 rather
than banking the saving as slack.

**The saving is 993 B, not the 5,210 B this paragraph first claimed.** That was
the size on disk; `jsstrip.py` serves these files without comments and the
budget counts served bytes. The correct figure was in `verify_inline.py`'s own
note the whole time. A five-fold overstatement in the direction that made the
finding look better is exactly the kind worth writing down. `verify_inline.py` asserts both that it reads them and that the
macro loads them, because reading a global nothing loads is a silent fallback
rather than a shared rule.

<!-- GEN:MODULE-INDEX -->
| module | loaded on | what it owns |
|---|---|---|
| `artwork.js` | Pad+Flip | The artwork stage — ONE implementation, shared by Pad and Flip. |
| `audioloop.js` | Pad+Flip+player | Skribl shared audio-loop DSP — canonical copy (INTEGRATION step 3b). |
| `audiosession.js` | Pad+Flip+player+in-post | Making Web Audio audible on an iPhone whose ringer switch is off. |
| `brushes.js` | Pad+Flip | Brushes — presets expressed entirely through per-point size and colour. |
| `brushfield.js` | Flip | The arithmetic behind tools that act on ink already on the page. |
| `canvassizes.js` | Pad+Flip+library+in-post | Canvas presets — the one table both editors read. |
| `colorselect.js` | Pad+Flip | Colour selection — the part both editors must agree on. |
| `composehost.js` | HOST | The pad button's lifecycle, for a HOST's composer. |
| `constrain.js` | Pad+Flip | Shift-to-constrain — snap a stroke to the nearest axis, shared by both editors. |
| `draftstore.js` | Pad+Flip | Draft media persistence — the bytes localStorage cannot hold. |
| `drawerdetent.js` | Pad+Flip | The draw drawer's HALF detent — one implementation, both editors. |
| `drawers.js` | Pad+Flip | Exclusive drawer controller — the ONE implementation of a machine both editors had hand-rolled: named panels above/below a toolbar, at most one open, the opener button reflecting state, and a scroll that reveals the opened panel without stranding it under browser chrome. |
| `erasersize.js` | Pad+Flip | Eraser size — shared by both editors. |
| `eventpoint.js` | Pad+Flip+player | Which contact a gesture belongs to — shared by Pad, Flip and the player. |
| `eyedropper.js` | Pad+Flip | Eyedropper — the armed-state machine, shared by both editors. |
| `floodfill.js` | Flip | Flood fill, expressed in the only vocabulary this project has: strokes. |
| `framebitmap.js` | Flip+player | Frame bitmaps — a painted page is rasterised once per playback, shared rule. |
| `gridoverlay.js` | Pad+Flip | Grid overlay — the alignment guides both editors draw over the canvas. |
| `helpsearch.js` | Pad+Flip | Help drawer search + live section counts. |
| `hints.js` | Pad+Flip | First-use hints — one short toast the first time a control is used. |
| `holdtiming.js` | Pad+Flip+player+library+in-post | Per-page timing — the ONE definition of how long a page lasts and how much of a drawing page has been revealed, shared by the Flip editor and every surface that plays one. |
| `inputsamples.js` | Flip | The points the browser already captured and the handler was throwing away. |
| `keyregistry.js` | Flip | lib/keyregistry.js — what is bound to which key, and whether two things answer at once. |
| `looptrim.js` | Pad+Flip+player | Loop trim clamping — the rule both editors apply six times between them. |
| `media_validation.js` | Pad+Flip | media_validation.js — one owner for media format policy and byte verification. |
| `mirror.js` | Pad+Flip | Mirror drawing — reflect each point across the canvas centre, shared by both. |
| `modalfocus.js` | Pad+Flip | Focus for surfaces that declare aria-modal="true". |
| `nametab.js` | Pad+Flip | The skribl NAME drawer — a title for the drawing, shared by Pad and Flip. |
| `pagespan.js` | Flip | Page spans — a contiguous run of Flip pages, and the operations on it. |
| `palette.js` | Pad+Flip | The pen palette — one list, both editors. |
| `photofit.js` | Pad+Flip | Photo fit geometry — the part both editors and the player must agree on. |
| `pillfit.js` | Pad+Flip | The autosave pill yields to the controls it would sit on. |
| `pinchgesture.js` | Pad+Flip | Pinch contact tracking — the two editors only, never the player. |
| `popdrag.js` | Pad+Flip | Draggable tool popovers — one grip, both editors. |
| `posted.js` | Pad+Flip | Your Skribls — a local record of what you have posted. |
| `postedaudio.js` | Pad+Flip | What a POST stores, which is deliberately not what an EXPORT downloads. |
| `postedcard.js` | Pad+Flip | Compositing /s/<id>/card.png — the post-time half of lib/sharecard.js. |
| `postedui.js` | Pad+Flip | Your Skribls — rendering. |
| `pressure.js` | Pad+Flip | Stylus pressure — the curve, the floor, and the on/off, shared by both editors. |
| `recentcolors.js` | Pad+Flip | Recent colours — the first controller shared by both editors. |
| `recoverykey.js` | Pad+Flip | Both ends of an anonymous author's revocation key: showing one, taking one back, and standing between a bulk clear and the keys it would discard. |
| `report.js` | Pad+Flip | "Report a problem" — the context, collected once, for both editors. |
| `scrubkeys.js` | Pad+Flip+player | Keyboard operation and live value for the three playback scrubbers. |
| `segslider.js` | Pad+Flip | Keeps a .seg-slider pill aligned to the selected button in a .seg group. |
| `selection.js` | Pad+Flip | Selection — pick a region, then move what is inside it. |
| `shapes.js` | Pad+Flip | Shapes — line, rectangle and ellipse, expressed as ordinary stroke points. |
| `sharecard.js` | Pad+Flip | /s/<id>/card.png: WHERE THE DRAWING SITS INSIDE IT. |
| `sizeclass.js` | Flip | One size decision, made once, for the whole app. |
| `smoothing.js` | Pad+Flip | Smoothing (the stroke stabilizer) — shared by both editors. |
| `stamps.js` | Flip | Stamps — the clipboard, but named, persistent and multi-slot. |
| `strokelayers.js` | Pad+Flip+player | Stroke layers — the see-through-stroke compositor's on/off, shared by both. |
| `theme.js` | Pad+Flip | Light/dark chrome — the stored setting, and the one place that applies it. |
| `toolshelf.js` | Pad+Flip | Tool shelf + overflow tray — shared by Pad and Flip. |
| `tooltip.js` | Pad+Flip | Styled tooltips, replacing the browser's. |
| `zoomstep.js` | Pad+Flip | The loop-detail magnification stepper — the ladder, the chrome, and the rule for stepping it, in one place because Pad and Flip both draw this control. |
<!-- /GEN:MODULE-INDEX -->

Generated by `harness/gen_docs.py`: the surfaces come from the templates that
load each module and the description is the module's own opening sentence, so
neither can drift from the thing it describes.

Two are worth calling out because they were extracted after a bug, not before:
`holdtiming.js` (the editor and the player disagreed about what a hold means,
and one release later four surfaces disagreed about what a reveal shows at its
first frame)
and the budget inside `strokelayers.js` (the editor capped its compositing cost
and the player did not). Both are covered by `verify_sharedrules.py`.

## Known-open, in the order worth doing

### Deferred: the bottom-toolbar redesign (owner-approved, still open)

The proposal: replace the bottom bar with Pen / Eraser / Shape / Select / Colour
/ **Tools** on Pad (Flip drops Shape), moving Image, Music and Magnify into a
labelled "Tools" action sheet — NOT another `•••`, because the top menu already
owns that glyph and two identical symbols meaning different collections is
avoidable ambiguity. Two things were never resolved: where Undo/Redo go once
they leave the bar, and whether Image/Music belong in "Tools" at all when they
are content rather than tools.

**Its measured premise no longer holds, and that is why the 208 lines of
measurement that used to sit here are gone.** The section argued from a v213
bug report: Pad WRAPPED at 320px with Image and Music orphaned on a second row
and the bar 113px tall, and Flip OVERFLOWED horizontally by 16px, which it
called the worse of the two because content was clipped with no cue. Re-measured
at 320px on the v282 tree:

    Pad    toolbar 92px          horizontal overflow 0
    Flip   toolbar 56px          horizontal overflow 0
    both   document overflow 0 — content is narrower than the viewport

Flip's clipping is gone and Pad's bar is 21px shorter than the number the
argument rested on. The proposal may still be worth doing on design grounds;
the emergency it was written up as is over. Anyone reviving it should re-measure
first rather than trust a snapshot — which is the whole reason this replaced it.

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

On Render, the middle two run together from the dashboard **Start Command**
(`python -m alembic upgrade head && gunicorn app:app`) — set in v270, when it
emerged that Render never reads the `Procfile` v267 had wired the same line
into, and production had therefore never run a migration on deploy (DECISIONS
v270). The Procfile keeps the same command for Heroku-style hosts and as local
reference only. If you ever run more than one web instance, move the migrate to
a Render `preDeployCommand` so two boots cannot race the same `upgrade head`.

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
