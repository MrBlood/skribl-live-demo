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

- Enabling, re-enabling, or widening CI triggers, paid runners, larger
  runner sizes, or anything that consumes metered Actions minutes beyond
  the current workflow configuration.
- Creating or upgrading services, plans, databases, storage, bandwidth
  tiers, or autoscaling on Render (or any host).
- Signing the project up for any third-party service that has a paid tier,
  even when starting on the free tier.
- Anything whose cost scales with usage in a way the owner cannot see
  coming (per-request billing, storage growth, egress).

When in doubt about whether something bills, treat it as if it does: stop
and ask, with a plain-language estimate of the cost. Context: the full CI
battery once burned the entire monthly Actions allowance in a single day
(30 full runs — see the note atop `.github/workflows/harness.yml`).

## CI economics

Pull requests run only the smoke job; the full three-job harness runs on
pushes to main and manual dispatch. Do not widen these triggers without
the owner's explicit approval (see the spending rule above). The full
suites run locally before every push — that is what makes the PR-side
trim safe.
