# What this archive is

**Source version: `SKRIBL_VERSION = "v273"` (skribl/core.py).**

This is the sealed delivery of the Skribl source tree — the same files as the
repository, packaged with the evidence of the run they were tested by.

**The release evidence in this archive is THIS tree's.**
`harness/RELEASE.md` and `harness/LAST-RUN.txt` are generated from a full
aggregate run executed against the tree in this archive. **Read the totals
there, not here** — the result, the assertion count, the suites reporting and
anything skipped are all stated in `harness/RELEASE.md`, and restating them in
this paragraph is how a number goes stale one release later while still
sounding authoritative. (`verify_mp4.py` skips in any build container without
an H.264 profile; a skipped suite contributes zero assertions and is not
evidence of coverage.) The tree hash in `RELEASE.md` is computed, and every
file here is listed in `SHA256SUMS`, so both claims are checkable without
trusting this sentence.

## Verifying the seal

From the archive root:

    grep -Ec '^[0-9a-f]{64} ' SHA256SUMS            # N: the manifest's own entry count
    sha256sum -c SHA256SUMS | grep -c ': OK'        # must equal N

`SHA256SUMS` covers every file in the archive and excludes itself. It does
**not** cover the ZIP container — a file cannot contain its own digest.

**WHAT "SEALED" DOES NOT MEAN.** It means this archive is internally consistent:
every file matches the manifest, and the manifest matches the tree the evidence
was produced from. It is **not** provenance. `SHA256SUMS` lives inside the
archive it authenticates, and so does `harness/RELEASE.md`'s tree hash — anyone
who can replace the archive can replace both. The seal detects corruption and
accidental substitution; it does not prove who built this or that it is the
build someone approved.

If you need provenance, take the hash of the **zip** from a channel that did
not travel with the zip. This project records it in the git commit that seals
each release, on the branch the archive was built from — compare
`sha256sum` of the zip against the value in that commit message. A signed tag
or a CI attestation would be stronger and neither exists yet; the git-history
channel is what is actually here, and saying so beats implying more.

The filename is DERIVED from `SKRIBL_VERSION`, not typed alongside it: earlier
deliveries were named for a version the code inside did not declare, and
`verify_docs.py` now asserts the version is single-sourced so that cannot
recur.

## Where to go next

- `README.md` — what Skribl is and how to run it.
- `START-HERE.md` — the working brief: architecture, invariants, open items.
- `DECISIONS.md` — decisions that are the owner's to confirm, and the reasoning
  record.
- `docs/INTEGRATION.md` — embedding Skribl in a larger Flask app.
- `harness/README.md` — the test suites and how to run them.
- `harness/RELEASE.md` — the generated release evidence for this tree.
