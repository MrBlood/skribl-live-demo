# Session context — how to work in this tree, and where it came from

`START-HERE.md` says what the tree IS. `DECISIONS.md` says why. `FUTURE.md`
says where it is going. This file carries what none of them can: how a fresh
session gets from a clone to a running server, how the release ritual is
actually executed, how the owner works, and the shape of the history behind
all of it.

It was written at v302 from the handoff files of the session that sealed it,
and rewritten so that nothing in it is a number a release changes. Every count
and hash it could have quoted lives in a generated record, and it points there
instead. `harness/verify_docs.py` holds this file to that — file names that
exist, no hand-typed tree hash, no hand-typed totals, no claim the suites have
since disproved — on the same terms as `README.md`. Where a fact belongs to
another file it is pointed at rather than copied. The one exception is §6, the
history, which exists in one piece nowhere else.

Read it after `CLAUDE.md`, whose rules bind, and before changing anything.

---

## 1. Check the ground before reading about it

Every handoff, this file included, describes the tree at the moment it was
written. Find out whether that is still the tree:

    git fetch origin main && git log -1 --oneline origin/main
    git status --short
    grep -m1 'tested tree hash' harness/RELEASE.md
    python3 -c 'import sys; sys.path.insert(0,"harness"); import release_run as r; print(r.tree_hash()); print(r.source_state())'

Three readings, and each means something different:

- **The computed hash equals the one in `harness/RELEASE.md` and the state is
  `clean`.** The checkout is the sealed tree. Every number in the stamped
  stanzas describes it.
- **The hash differs and the state is `clean`.** Work has landed since the last
  seal. That is normal between seals — five merges did so between v300 and
  v302, and there is no v301 for that reason — and it means `RELEASE.md`
  describes the seal, not the tree. `git log` from the sealed commit is the
  record of the difference.
- **The state is `dirty`.** Either uncommitted work, or something untracked
  that `.gitignore` hides from `git status` and `release_run.tree_files()`
  does not — the corpus renderer's output directory is the one that has done
  it. Nothing sealable comes from a dirty tree; find the file first.

If the hash is not the one in the record, treat §5 and §6 of this file as
history and read the DECISIONS entries after the seal for what changed.

---

## 2. Rebuild the environment

The container is ephemeral: the venv, the scratch files and every server are
gone in a new session. One script rebuilds the environment the way CI does and
leaves a server up:

    harness/bootstrap.sh                 # /tmp/skribl-venv, port 5001

Its header explains each step and the failure it prevents. The short version:
the interpreter is the one `.python-version` pins, the install is the
hash-locked one from `constraints.txt` plus `harness/requirements.txt`, the
tables are created on a fresh sqlite database exactly as `run_harness.sh`
creates them, the posting rate limit is raised to the harness's default, and
readiness is proven with a request that reads a table rather than one that
renders a page — because the first draft of that script passed the boot suite
and answered 500 to every post.

Then suites run directly against it, one at a time:

    SKRIBL_BASE=http://127.0.0.1:5001 /tmp/skribl-venv/bin/python3 harness/verify_boot.py

**What the script cannot fix, and START-HERE's "Environment traps" does not
already say.** The traps about the interpreter, the difference between the
seal and CI, suites that discard their servers' stderr, and PostgreSQL are in
`START-HERE.md`; read that list. These are the rest:

- **Keep the shared server on port 5001.** Only some suites read
  `SKRIBL_BASE`; a third hardcode `127.0.0.1:5001`, and the rest start their
  own app or need none. `grep -L SKRIBL_BASE harness/verify_*.py` lists the
  suites that do not read it on the current tree; do not trust a count typed here.
- **A server started by hand posts into the real rate limit.** `run_harness.sh`
  and `harness/bootstrap.sh` both export `SKRIBL_RATE_MAX_POSTS` for the
  harness; start Flask without it and the posting suites together sit near the
  default hourly quota, so a few new posting assertions produce 429s that look
  like validation failures. Parallel posting suites trip it the same way, so
  run posting suites one at a time.
- **Jinja caches templates when debug is off.** Restart the server after a
  template edit or the suite tests the old markup.
- **An in-process suite reads `DATABASE_URL`, not `SKRIBL_BASE`.**
  `verify_delivery.py` imports `app` and posts through a test client of its
  own; with nothing exported it opens the app's default sqlite file, which the
  bootstrap never created, and two upload checks fail with "no such table"
  under a traceback that looks like a server bug. Export the bootstrap's
  (`DATABASE_URL=sqlite:////tmp/skribl-fresh-<stamp>.db`, printed as `db:` at
  start) and it passes; `run_harness.sh` does this for every suite.
- **Stop a server by port, never by a pattern typed on the same line.**
  `fuser -k 5001/tcp` or `kill $(lsof -ti :5001)`. `ss` and `netstat` are not
  installed in the remote container, and `pgrep -f <pattern>` matches the shell
  that is running the `pgrep` when the pattern is in that command line — it has
  killed the session's shell more than once. Put a pattern in a separate script,
  or bracket its first character (`"[r]elease_run.py"`).
- **Long work goes in the background.** The agent sandbox caps a foreground
  command well below the length of a release run, and background processes are
  reaped while the session is idle. `release_run.py` checkpoints for exactly
  this; run it under `nohup`, or in `--budget` slices, and re-invoke.
- **Egress goes through a proxy with opinions.** `*.onrender.com` and GitHub's
  artifact blob storage are refused (a 403 on CONNECT), so the live deploy is
  unverifiable from here and CI artifacts cannot be downloaded — transcribe from
  the job's own log instead, per CLAUDE.md. Unauthenticated GETs to
  `api.github.com` work for public reads. Writes to GitHub go through the tools
  the session has for it, not `gh`. Loopback is in the proxy's exclusion list,
  so `curl http://127.0.0.1:5001/` needs no special flag; an earlier handoff
  said otherwise and was describing a different container.
- **The browser build and the Playwright version are coupled.** The container
  ships a Chromium under `PLAYWRIGHT_BROWSERS_PATH` with downloads disabled;
  `harness/requirements.txt` pins the Playwright range that drives it and says
  how to check. An unpinned install pulls a newer Playwright that refuses the
  build and asks for a download the proxy may refuse.
- **Delete the corpus renderer's output before a release run.** The `.gitignore`
  entry keeps `git status` readable and does not keep the directory out of the
  frozen tree hash; its own comment says so, and a v302 seal found out.
- **Do not start PostgreSQL during a seal.** CLAUDE.md carries the
  measurement. `verify_postgres.py` skipping here is the designed
  configuration; the `postgres` CI job runs it and writes the attestation.

---

## 3. The working loop

**Run the affected suites directly, not through the runner, between seals.**
`./harness/run_harness.sh verify_pages.py` starts its own server on a fresh
database, which is what you want for a suite that needs one — and it rewrites
`harness/LAST-RUN.txt` and re-stamps the four documents from it, so the
whole-run record of the last seal becomes a one-suite record. Driven directly
against the bootstrap server a suite touches no record. If the runner was used
anyway, restore the run record and the stamped documents from the last commit
before committing; they hold no uncommitted work of yours, which is the one
condition under which CLAUDE.md's rule against `git checkout` does not apply.

**Every new assertion is calibrated per component before it is believed**, and
the shape of the script that does it is worth keeping even though the script
itself is rewritten each time: back the files up with `cp` (never `git
checkout` — the fix is uncommitted), apply ONE mutation whose anchor string is
asserted to occur exactly once (a mutation that silently fails to apply reads
as a pass), run only the pins that should move, restore by `cp`, and go to the
next. Two surfaces sharing a fix may need different assertions; CLAUDE.md
records why.

**Commit with an explicit file list, push, open a pull request, quote the
suite runs in it, squash-merge.** Pull requests run the smoke job, which is the boot suite plus the
browserless/serverless suites (EXT-P1-9); the
push to `main` runs the full three-job battery, and Render deploys `main`. The
branch the session was given is reused across pull requests.

**When the owner asks for a bug check before a seal, expect to find bugs.**
The v302 seal passed, the bug check that followed found five defects in the
code that seal covered, and the tree was re-sealed. Read the changed behaviour,
try to break it, then seal — a green harness is the precondition, not the
evidence. Budget the time for fixes, per-component calibration and a second run.

**For a rendering defect, measure pixels before naming a mechanism.** The v302
mesh was diagnosed backwards from geometry and put right by a pixel measurement;
the same arc retracted a timing claim by rendering both variants and comparing
their luminance. The owner reports what a phone shows in one sentence; that
sentence is the bug report, and reproducing it with a measurement comes before
any theory about why.

---

## 4. The seal, as it is actually executed

CLAUDE.md's "Sealing a release" is the rule; this is the sequence that has
satisfied it, with the mechanics the rule leaves out.

1. Bump `SKRIBL_VERSION` in `skribl/core.py`, write the DECISIONS entry, update
   the version lines in `README.md` and `ARCHIVE-README.md`. If a `lib/*.js`
   was added, `python3 harness/gen_docs.py` regenerates the module index. Run
   `python3 harness/verify_docs.py` directly — it is source-only and touches no
   record — and fix what it names.
2. Delete the corpus renderer's output directory. Commit everything. Confirm
   `release_run.source_state()` says `clean`.
3. Dispatch `harness.yml` on the branch carrying the exact tree being sealed.
   Actions is free here (public repository, standard runners; CLAUDE.md says
   why and how to check).
4. Start `python3 harness/release_run.py --hold-lanes 3600` in the background,
   or in `--budget` slices with the same flag on every invocation. Every resume
   re-verifies the frozen hash and refuses a changed tree. The flag is the
   seal's engineered margin: after the last batch and before the render, the
   run re-reads both attestations every 30 seconds until they verify or the
   hold expires, and says which lane it is waiting for. (v303 sealed without
   it and the last batch rendered two minutes after the PostgreSQL attestation
   landed — a valid record on a lucky margin. Pausing with `--budget` slicing
   or `kill -STOP` is the fallback, and the slice boundary is not the render.)
5. **While it holds, carry both attestations into the tree.** The `mp4` and
   `postgres` jobs each write a file naming the tree they tested; artifact
   download is blocked, so transcribe each from the job's own `cat` step (the
   postgres job prints its attestation last, because its service container's
   teardown pushes anything earlier out of the log reader's reach). Write them
   to `harness/MP4-ATTESTATION.txt` and `harness/POSTGRES-ATTESTATION.txt`.
   Both are in `release_run.GENERATED`, so writing them does not move the
   frozen hash — confirm with `release_run.tree_hash()`, then confirm
   `release_run.mp4_attestation(frozen)` and
   `release_run.postgres_attestation(frozen)` both say `verified`, not STALE.
   The hold releases itself on the next recheck.
6. The run writes `harness/RELEASE.md` and `harness/LAST-RUN.txt` and stamps
   the documents. Commit the generated set by name; `release_run.GENERATED` is
   the list, read it rather than retype it. Check with
   `python3 harness/stamp_docs.py --check`. **Do not run `run_harness.sh`
   after this.**
7. Pull request, wait for the smoke job (boot + the source suites), squash-merge pinned to the head, and
   the push to `main` runs the full battery and deploys.

Getting step 5 wrong costs either a re-run or a sealed record that contradicts
evidence already in hand; the second is an evidence gap, so it is a re-run.

---

## 5. The code in one screen

Two editors and a player over one payload format. **Pad** (`skribl/static/app.js`
with the `editor_*.js` carves) records a drawing with its timing and replays
it. **Flip** (`skribl/static/flip.js`) is frame-by-frame pages. The **player**
at `/s/<id>` is `app.js` with the editor-only files absent — `verify_player_isolation.py`
holds that boundary and prints the byte figures; run it rather than quote them.
The **in-post player** (`skribl/static/inlineplayer.js`) is a second, small
playback implementation a host embeds in a feed, and `verify_inline.py` plays
the same drawing on both and compares. Everything both editors must agree on
lives once in `skribl/static/lib/`; START-HERE's generated module index says
what each module owns and who loads it.

**A page is strokes, and a point carries nothing outside the seven fields
START-HERE's invariants table names.** That is the contract every post ever
made depends on, and it is why there is no fill primitive, no raster layer and
no per-stroke render attribute: fill, blur, smudge, stamps, in-betweens and
Motion Smear are all expressed as ordinary points.

**Painting walks a stroke array into runs.** A run of one colour and one width
is one canvas path (`uniformRun`). A run of one alpha that is not one path is
composited once through a temporary layer (`uniformAlpha`). Anything else is
layered per dab, and the number of layered things a frame may hold is one
budget, counted by one predicate in `lib/strokelayers.js`, on Pad, Flip and the
player alike — START-HERE's invariants say so and name the suites. The two
spellings of alpha are deliberately asymmetric: `rgba()` marks ink that is
layered per stroke, generated ink is written as 8-digit hex and takes the
cheaper once-composited route, and since v302 both populations are counted
against the one budget. DECISIONS v239 and v302 explain why the asymmetry is a
design and not a gap.

**Generated pages are two features on one pairing.** The in-between emits one
pose between two pages; Motion Smear draws the pose mid-travel with a ghost
trail. Both pair strokes by shape (`tweenMatch`), both are refused before the
document's two ceilings — points and pages, owned by `lib/pointbudget.js` and
pinned against the server's caps — and a generated page's recipe rides in a
WeakMap beside the frame so a draft stores a few bytes and rebuilds the page.
`harness/tools/corpus/` renders the cases and states what each expects.

**Three ratchets decide whether a change to the player is affordable**, and
each prints its number: the player's served bytes and CSS in
`verify_player_isolation.py`, its reachable lines in `verify_seam.py`, the
embed's bytes in `verify_inline.py`. Raising one is an argument written at the
ratchet, spent against first; the v302 entry records both a raise and a refusal.

---

## 6. Where we came from

Dates are from `git log`; the reasoning behind each turn is in `DECISIONS.md`,
whose version log restarts its numbering twice and whose LAST occurrence of a
number is the current one. This is the map, not the record.

- **July 2026 — a page edited in the browser.** The first commit is 8 July.
  For three weeks the repository is a Flask app edited through GitHub's web
  interface, several hundred commits titled "Update app.js": Pad, then the
  player, then Flip by mid-month. Versions were counted in the owner's handoff
  zips, and none of that numbering reached git.
- **Late July to 1 August — the harness is born (v100–v131).** The first
  version label in git is v100 on 25 July. Within a week: the first suites, the
  two vendored encoders, a real Content-Security-Policy and server-side media
  validation, then rounds of external security review and the PostgreSQL
  concurrency suite. `docs/HANDOFF.md` is that era's changelog and stops at
  v131 by design.
- **Early August — Skribl becomes a blueprint (v132–v141).** `app.py` shrinks
  to a host, `skribl/` becomes a package a Flask app mounts, the feed, CSRF,
  migrations and storage backends arrive as integration blockers, and a
  sequence of external reviews closes them. `docs/REFACTOR-v132.md` records
  the split, including the player-carve attempt that was reverted — two live
  suites still cite it, which is why it stays. `DECISIONS.md` and the CI
  workflow start here.
- **Mid August — the shared library and the seal (v142–v198).** Rules both
  editors kept in two copies start moving into `skribl/static/lib/`.
  `START-HERE.md` and `FUTURE.md` appear, and `harness/release_run.py` turns a
  pile of batch records into one frozen-tree aggregate, because an outside
  reviewer had read a single batch's total as the release's.
- **Late August — the design direction and the shell (v199–v231).** A design
  critique becomes `DESIGN-DIRECTION.md`; the brand lockup, the header, the
  tool shelf and tray, selection and transform, light mode's first phase and
  durable drafts follow. The v224 outside review produces the capability gate
  in `verify_docs.py`: prose can go stale as surely as numbers.
- **28 August to 2 September — micro-releases, then public.** Dozens of
  one-idea releases in six days, each a paragraph in the version log; the
  numbering restarts twice in the process. Pull requests replace direct pushes,
  the repository is cleaned for going public, the sealed-archive ceremony and
  the attestation model take shape, and `CLAUDE.md` is written so a new
  session inherits the rules rather than the conversation.
- **3 to 8 September — audits and the seams (v273–v287).** A staleness sweep
  finds the map wrong where the code was right; the in-post player, compose
  mode and `create_post()` make Skribl mountable inside someone else's post;
  two adversarial audits produce the recovery key and the rule that a
  population must be generated, not sampled; a decluttering arc runs from v282
  and is ended by decision at v285; Draw-on pages and the PostgreSQL
  attestation land.
- **12 to 15 September — the shell tiers and the phone (v288–v298).** Four
  audit tiers on the chrome, the owner's screenshots, the media audit, and the
  generative engine's turn: the in-between becomes what its name promised and
  the exposure becomes Motion Smear.
- **15 to 19 September — the engine judged on pictures (v299–v302).** An
  engine audit, the finding the record had omitted, a corpus that states what
  it expects instead of what it drew last time, and the smudge-over-smear
  work whose seal was voided by its own bug check. The bug-check-before-seal
  order is the precedent this file inherits.

What the arc keeps teaching, in the words the repository already uses: run it,
do not read it; measure the rendered thing, not the arithmetic; a green check
is not evidence until it has gone red; the two surfaces diverge, so ask what
the other one does; and the person holding the phone is the instrument the
tree cannot replace.

---

## 7. How the owner works

Short imperatives — "Land it", "Go for it", "What's next", "Are you cooking?"
— and the expectation that the work behind them is complete when it is
reported done. Tests on a phone against the live deploy and sends screenshots
with one sentence each; that sentence is the bug report. Wants the thing to
look right before wanting a knob for it. Asks for a bug check before a seal and
expects it to find something. Wants to be asked before anything that could
bill, and not asked about things that cannot — CLAUDE.md says why theatrical
permission costs real permission. Reviews arrive from an outside auditor
working from a packet: per-merge diffs, changed files whole, the sealed
records, the release archives, the CI job table, and a README that points at
generated numbers rather than restating them. Prefers a fresh session that has
read the files to a long one carrying a compacted summary; this file exists
because of that.

---

## 8. What a fresh session actually needs

In the order that would have saved the most time:

1. **§1, then §2.** Check the ground, rebuild the environment, prove the server
   with a suite. Every environment trap above is either avoided by the script
   or written beside it.
2. **Read `CLAUDE.md` as rules, not background.** Each "never" is a scar from
   this project. The two that have cost the most: the run-record rule (no
   `run_harness.sh` after a seal) and the uncommitted-work rule (no `git
   checkout` or `git stash` of a file holding work).
3. **Open the file before citing it.** Compaction loses the location of things
   first and their existence last; a summary that says a specification is in
   FUTURE.md when it is in DECISIONS is the kind of error one grep catches and
   a fresh session repeats.
4. **Ask the owner what to do; do not pick from a list.** Every handoff in this
   project has said so, and the candidates are recorded without ranking for
   that reason (§9).
5. **Land finished work; ask before anything that could bill.**

---

## 9. Where the open list lives

Not here, and not copied here, because two copies of an open list disagree
within a release. `FUTURE.md` §6c onward carries the measured, unbuilt items
with their reasoning; the latest entry in `DECISIONS.md` ends with a "still
open" paragraph for what its release left; START-HERE's invariants table marks
the rules that have no enforcer. Read those three, in that order, and let the
owner choose.
