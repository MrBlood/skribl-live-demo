# Working agreements for this repository

## Start here (read order for a new session)

1. **`START-HERE.md`** — the session primer, and the current state of the
   tree. Its opening block deliberately contains no numbers: verify totals
   against `harness/RELEASE.md` and `SHA256SUMS` rather than trusting prose.
   Its "Closed in vNNN" sections carry the invariants a change can break.
2. **`DECISIONS.md`** — why the tree is the way it is, newest at the bottom.
   Version headings REPEAT (the numbering restarted twice), so the LAST
   occurrence of a number is the current one; see the note at the head of
   its version log. Entries are true as written and not maintained after.
3. **`FUTURE.md`** for direction, **`docs/INTEGRATION.md`** to mount Skribl
   into another Flask app.

Conversations are not the memory — these files are. Prefer a fresh session
reading them over a long one carrying a compacted summary.

## How work ships here

Implement → run the AFFECTED suites locally → commit with an explicit file
list (never `git add -A`) → push → PR → squash-merge. Quote the suite counts
in the PR: that local run is what justifies CI's PR-side trim (below).

- Run suites with `./harness/run_harness.sh [verify_x.py ...]`; bare runs
  everything. A run reporting `skipped N` is not the run you think it is.
- After ANY change to `skribl/static/styles.css`, re-emit the player's CSS:
  `python3 harness/tools/cssgraph.py --emit harness/tools/css_live.json
  skribl/static/player.css`.
- All work goes on the branch the session names; it is reused across PRs.

**Gates that bite, in `verify_docs.py`:** every `lib/*.js` must be named in
some `.md` (the shared-module index in START-HERE.md is where); no document
may name a repo file that is not there; no doc may hand-type a tree hash or
an assertion count outside the generated `<!-- HARNESS-COUNTS -->` stanza.
Numbers in prose go stale silently — point at the generated record instead.

## Calibrate the instrument before believing it

**Run every new check against one case you know is BAD and one you know is
GOOD. If it cannot tell them apart, the instrument is wrong, not the tree.**

This is the mutation test moved BEFORE the fix instead of after, and it is
here because the v281/v282 work produced roughly as many broken instruments
as real defects. Each of these reached a commit or a run:

- The README route-table gate reused a set of PATHS, so GET, PATCH and DELETE
  on one route collapsed into a single entry. **It would have passed on the
  tree that motivated it.** A mutation said so; nothing else would have.
- The packaging verifier called `db.create_all()` and never opened
  `alembic.ini` or `skribl/migrations` — it would have reported a runtime
  package missing either as VERIFIED. The `Procfile` runs
  `alembic upgrade head`; so does the check now.
- `verify_ux`'s ink measure counted `alpha > 0`. Flip's canvas is opaque, so
  it always returned exactly width*height/4 and `ink > 5000` would have
  passed on a blank page — since v206, because the fixture in use saturated
  it too.
- `import browsing` landed below first use in five suites. The check had been
  "all 99 parse", and a misplaced import is valid syntax: parsing proves
  nothing about importing.

A green check is not evidence until it has been shown to go red.

**Mutate per COMPONENT, not once per change** (learned in v212, where it was
the only thing that caught the error). A single all-or-nothing revert can show
red for one component's sake while another's assertion pins nothing. That
release fixed the same unguarded line on Pad and Flip and asserted both the
same way — but Flip's `reveal()` already repainted both canvases, so Flip
**self-heals the scenario and was never broken by it**. The Flip assertion was
green against the broken tree and green against the fix.

Which yields a second rule: **when two surfaces share a fix, they may need
DIFFERENT assertions.** Pin the surface that can fail the user-visible
scenario with that scenario; pin the surface that cannot with the property the
fix actually governs.

**Its companion, learned the expensive way: do not edit mechanically where
prose and code interleave.** Three automated passes over the stylesheets each
produced fresh damage — a stranded trailing comment, an emptied media query, a
deleted note documenting a live token, and finally a corrupted `.slider` rule
that `verify_sizeclass` and `verify_tray` caught. Comments are prose and prose
needs reading.

**And for a change that touches many suites, the sample IS the full run.** The
five broken imports and two crashed suites above were each caught by running
all 99, never by a representative subset. Commit before running it, so the
work survives being wrong.

**A CHECK FOR ABSENCE MUST MATCH THE MECHANISM, NOT THE WORD** — and this one
has now happened three times, in three different files, which is why it is a
rule rather than an anecdote:

- `verify_review` asserted "the player does not load this module" with a
  substring search. The template's COMMENT explaining the absence contains the
  filename, so the check read the explanation as the thing it was looking for.
- Two `/library` gates were substring searches that passed on their own prose.
- v283: a comment in `run_harness.sh` explained that generated names must be
  spelled out — by SHOWING the flag syntax it was describing. `verify_docs`
  scrapes that file for exactly that syntax, so it read the illustration and
  found a file called `...`.

Match the tag, the token, the parsed structure — never the human sentence
around it. And do not write an example of a machine-read literal in prose the
machine reads: the v281 stamp nearly deleted a whole section because notes
quoted the counts marker verbatim.

**An assertion that can only pass while the work is OUTSTANDING is a TODO in a
test's clothes.** `verify_seam`'s "a split is still worth doing" asserted
`editor_lines > player_lines` and went red the moment `editor_draw.js` landed —
the fix succeeding is what broke it. Invert such a check to guard the
achievement instead, so it goes red when the ground is LOST.

**NEVER `git checkout` OR `git stash` A FILE THAT HOLDS UNCOMMITTED WORK.**
With nothing committed to fall back to, checkout is not an undo, it is a
delete. Read an old version with `git show <rev>:<path> > /tmp/copy`, which
cannot touch the working tree. When an edit script goes wrong, FIX IT FORWARD —
reverting looks faster and is the destructive choice. (Twice: v213, v283.)

## Decluttering has a stopping condition

Continue only while a targeted semantic review identifies a specific duplicated
or obsolete concept with concrete maintenance cost. **"Load-bearing" and "reason
unknown" are valid outcomes, not invitations to keep searching.** Resume cleanup
when a concrete stale claim, duplication, defect, or maintenance problem
provides a target.

So the question is not "what can we declutter next?" but "what concrete thing is
currently duplicated, stale, contradictory, or costly to maintain?" If there is
no answer, do not run a pass. No percentage, no clutter score, no recurring
duplication scan — the tree has enough machinery. (Outside review of v285, which
ended the broad arc that ran from v282.)

## Sealing a release

Bump `SKRIBL_VERSION` in `skribl/core.py`, add the `DECISIONS.md` entry, and
update the version lines in `README.md` and `ARCHIVE-README.md` (both are
pinned by `verify_docs`). Then `harness/release_run.py` for the full
aggregate — it checkpoints, so a killed run resumes on the same frozen tree.
On PASS, `harness/stamp_docs.py` writes the counts into the docs. **Do not
edit a tracked file once a run has frozen its tree hash**, or the sealed
record describes a tree that no longer exists; restart the run instead.

**And do not run `run_harness.sh` AFTER the release run.** Every invocation
rewrites `harness/LAST-RUN.txt`, so one ad-hoc suite replaces the whole-run
record with a one-suite record, and the checkpoint is deleted on success so
there is nothing to resume from — it costs a full re-run. The stanza-restore
habit covers the docs and not this. For a source-only suite, invoke it
directly (`python3 harness/verify_docs.py`), which does not touch the record.
Order the seal: release run, then `stamp_docs.py`, then commit, and check
`stamp_docs.py --check` rather than re-running a suite.

**DO NOT RUN POSTGRESQL IN THIS CONTAINER DURING A SEAL.** `verify_postgres.py`
skipping locally is the DESIGNED configuration, not a gap: `SKIP_COVERAGE` names
the `postgres` CI job that runs it in an environment this one lacks, and the
sealed record says so by name. Starting the cluster to "improve" the record from
two skips to one costs more than it buys.

Measured, same tree, same suite, the only variable being the cluster:

    PostgreSQL up      verify_hold 2nd-worst frame deviation  32 ms  FAIL
    PostgreSQL down    verify_hold 2nd-worst frame deviation   1 ms  PASS

`verify_hold` asserts frame-pacing evenness and its tolerance already allows one
contention outlier; the checkpointer and autovacuum supply a second. The same
holds for anything else periodically hungry on this box during a run — the
browser timing suites are the instrument, and background load is noise in it.

**THE MP4 ATTESTATION HAS TO BE PULLED INTO THE TREE, NOT MERELY DISPATCHED.**
`release_run.py` reads `harness/MP4-ATTESTATION.txt` from the LOCAL working
tree when it renders `RELEASE.md` at the end of the run; the CI job writes that
file on the runner. Those two never meet on their own, so **dispatching the job
concurrently is necessary and NOT sufficient** — the attestation has to be
carried across by hand, while the run is still going:

1. Dispatch `harness.yml` on the branch carrying the exact tree being sealed.
2. When the `mp4` job finishes (~1 minute), write its attestation into
   `harness/MP4-ATTESTATION.txt`. The file is in `GENERATED`, so writing it
   does NOT move the frozen tree hash — confirm that with `release_run.tree_hash()`
   before believing it.
3. Confirm `release_run.mp4_attestation(frozen)` says `verified`, not `STALE`.
4. Only then let the run reach its final render.

Get it wrong and the choice is a re-run (~42 minutes) or a sealed record whose
mp4 line contradicts evidence already in hand. The second is an evidence gap,
so it is a re-run.

If the environment's egress proxy refuses GitHub's artifact blob storage (403
on CONNECT, which is the normal case here), the job's own `cat` step puts the
file verbatim in the log — transcribe from there. That is not hand-typed
evidence: nothing is computed or invented, and the load-bearing field
self-verifies, because `release_run` reports STALE on any tree-hash mismatch.
A bad transcription fails closed.

## Spending: ask before incurring costs (owner's standing rule)

Never take an action that could create or increase a bill on any of the
owner's accounts — GitHub, Render, or any other service — without asking
first and getting an explicit yes. This includes, concretely:

- Moving CI onto larger runners (4-core and up, GPU, macOS), self-hosted
  paid runners, or any runner class that is not GitHub's standard hosted
  one. **Standard runners are the free case; runner SIZE is the billable
  knob.** See the note below before assuming a CI change costs anything.
- Creating or upgrading services, plans, databases, storage, bandwidth
  tiers, or autoscaling on Render (or any host).
- Signing the project up for any third-party service that has a paid tier,
  even when starting on the free tier.
- Anything whose cost scales with usage in a way the owner cannot see
  coming (per-request billing, storage growth, egress).

When in doubt about whether something bills, treat it as if it does: stop
and ask, with a plain-language estimate of the cost.

**GITHUB ACTIONS DOES NOT BILL THIS REPOSITORY, and this paragraph exists
because the rule above used to say it did.** `MrBlood/skribl-live-demo` is
public, and every job in `.github/workflows/harness.yml` runs on
`ubuntu-latest` — a standard GitHub-hosted runner. Standard runners on
public repositories have no minute allowance and no per-minute charge, and
Actions artifact and cache storage is free there too. So running the full
battery, dispatching a job by hand, or adding a trigger costs nothing.

Two things that WOULD bill even on a public repository, and are the reason
the bullet above still exists: a larger runner size, and a self-hosted
runner on paid infrastructure.

**The history is real and its billing premise is not.** The note atop
`harness.yml` records a day when the full battery ran 30 times; whatever
the repository's visibility was then, it is public now, so that day would
cost nothing today. Verify before repeating the claim — the visibility and
the `runs-on:` labels are the two facts that decide it, and both are
checkable in about ten seconds:

    gh repo view --json visibility        # or the API; must say "public"
    grep -n 'runs-on' .github/workflows/*.yml

A standing rule that asks for permission on something that cannot cost
money teaches the assistant to ask for permission theatrically, which is
how a real spending question gets waved through with the rest.

## CI economics — turnaround, not money

Pull requests run only the smoke job; the full three-job harness runs on
pushes to main and manual dispatch. The full suites run locally before
every push — that is what makes the PR-side trim safe.

**The trim's justification is WALL-CLOCK, not cost.** Three jobs at 40-90
minutes each is a long time to sit on a pull request, and free minutes are
not free minutes-of-your-life. The trim was originally written up as a
money-saving measure; on a public repository with standard runners it never
was one, and keeping the wrong reason attached to a right decision is how
the decision gets reversed by someone who checks the reason.

Still ask before widening triggers — not because it bills, but because it
is the owner's call how much CI noise a pull request generates.
