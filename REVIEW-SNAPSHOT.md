# This is a REVIEW SNAPSHOT, not a sealed release

Read this before `harness/RELEASE.md`.

## The one thing that does not line up

`harness/RELEASE.md` records **PASS — 2667 assertions, 63/63 suites, 1 skipped**
against tree hash `e8e54f92…`. The tree in this archive hashes to `930ce6a6…`.

**The difference is prose in two files, and nothing else.** After that PASS run
completed, `verify_docs.py` correctly failed on a file-count mismatch: the
reviewer docs told a reader to expect 200 files in `SHA256SUMS` while the
manifest had grown to 203 (two new libs plus this file's predecessors). Fixing
that meant editing `FOR-THE-REVIEWER.md` and `HANDOFF-NEXT-SESSION.md`, which —
unlike `README.md` and `START-HERE.md` — are **not** excluded from the tree
hash. Editing them after the run invalidated the run's own tree pin.

No source file, template, stylesheet or suite changed. The code in this archive
is byte-identical to the code that passed twice: once at tree `da2216b2` (as
v219) and once at `e8e54f92` (as v220, after the version bump).

## What that means for you

- **Trust the code.** It is verified.
- **Do not quote `RELEASE.md`'s tree hash as this archive's hash.** It describes
  the tree as it stood two prose edits ago.
- A re-run on `930ce6a6…` is the only thing outstanding before this is a real
  seal. It is expected to reproduce the same result; that expectation is not
  evidence, which is exactly why this file exists rather than a quiet edit to
  `RELEASE.md`.

## Verify what IS verifiable here

    cd skribl-v220 && sha256sum -c SHA256SUMS | grep -c ': OK'   # expect 204
    python3 -c "import sys;sys.path.insert(0,'harness');import release_run as r;print(r.tree_hash())"

The manifest covers every file in the archive and excludes itself. It does not
cover the ZIP container — a file cannot contain its own digest — so the archive's
external SHA-256 travels with the delivery.

## The sealing order, learned the hard way this session

Two complete harness runs were lost to getting this wrong. For next time:

1. Settle **every non-generated file** first: `SKRIBL_VERSION` in
   `skribl/core.py`, the archive directory name, `ARCHIVE-README.md`,
   `FOR-THE-REVIEWER.md`, `HANDOFF-NEXT-SESSION.md`, `DECISIONS.md`.
2. Run the full aggregate on that frozen tree.
3. **Only then** regenerate `SHA256SUMS` and the stamped stanzas — those are all
   on the excluded list, so writing them cannot move the tree hash.
4. Zip. Touch nothing in between.

The excluded set is defined in `harness/run_harness.sh` (`_tree_files`):
`harness/LAST-RUN.txt`, `SHA256SUMS`, `README.md`, `harness/README.md`,
`docs/HANDOFF.md`, `START-HERE.md`, `harness/RELEASE.md`. Anything else you edit
after a run invalidates that run.
