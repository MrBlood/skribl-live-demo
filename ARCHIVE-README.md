# What this archive is

**Source version: `SKRIBL_VERSION = "v320"` (skribl/core.py).**

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

## Three packages, and which one you want

`harness/package.py` builds the release as three archives rather than one, and
each carries its own `SHA256SUMS`:

    skribl-<version>-runtime.zip    what a deployment needs, and nothing else
    skribl-<version>-source.zip     the repository as tracked
    skribl-<version>-evidence.zip   harness, fixtures, release records, attestation

**The runtime package is boot-verified, not merely filtered.**
`python3 harness/package.py <dir> --verify` migrates a fresh database with
`alembic upgrade head` — the same command the `Procfile` runs — then serves
Pad, Flip, the library, the gallery and the demo feed, posts a Skribl, renders
its share card, and revokes it with the key issued at post time. Removing `alembic.ini`,
`app.py` or `skribl/migrations` from the allowlist each fails that check by
name, which is what makes the allowlist a claim rather than a guess.

It does **not** exercise gunicorn, PostgreSQL, or anything the deployment
platform reads for itself (`.python-version`); see the docstring on
`verify_runtime` for the full list of what the check does not cover.

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
not travel with the zip. Seals up to v305 recorded it in the commit message
that sealed them; since v320 it is published on the repository's Releases page
(`SHA256SUMS-<version>.txt`), next to the attestation described below —
compare `sha256sum` of the zip against that file.

## Checking where a zip came from

Since v320 there is a stronger channel than the commit message. The three zips
are reproducible: `harness/package.py` writes them itself, entries in a fixed
order with the commit's own timestamp, so the same commit makes the same bytes
on any machine. And `.github/workflows/release.yml`, run once per seal after it
merges, builds them on GitHub from that commit and has GitHub sign a
build-provenance attestation over each one. With the GitHub CLI:

    gh attestation verify skribl-<version>-source.zip --repo MrBlood/skribl-live-demo

A pass names this repository, the release workflow and the commit the zip was
built from, and it holds however the zip reached you. The same zips and their
outer SHA256 are published on the repository's Releases page under the version's
name. What the attestation does not say is that the code is good: it says where
these exact bytes came from, and the release evidence inside says what was run
against them.

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
