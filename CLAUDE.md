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

## Sealing a release

Bump `SKRIBL_VERSION` in `skribl/core.py`, add the `DECISIONS.md` entry, and
update the version lines in `README.md` and `ARCHIVE-README.md` (both are
pinned by `verify_docs`). Then `harness/release_run.py` for the full
aggregate — it checkpoints, so a killed run resumes on the same frozen tree.
On PASS, `harness/stamp_docs.py` writes the counts into the docs. **Do not
edit a tracked file once a run has frozen its tree hash**, or the sealed
record describes a tree that no longer exists; restart the run instead.

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
