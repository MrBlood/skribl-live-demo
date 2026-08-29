# v225 — what changed since the sealed v224

**Evidence status: SEALED.** `harness/RELEASE.md` is generated from a full
aggregate run against this tree and states the result, the assertion count, the
suites reporting and anything skipped. Read it there. Beside each skip it now
also names the CI job that covers it, or says NOT COVERED.

This release answers an outside review of the sealed v224 archive. That review
found **no new critical or high-severity vulnerability**, and its own bottom line
was that it would not block v224 on a security flaw. Its strongest finding was
about the release process rather than the code, and it was right.

## Narrative

**The headline is that documentation rot cost a reviewer real time.**

`verify_docs.py` has guarded this project's volatile facts for many releases —
suite counts, file counts, assertion totals, tree hashes, version strings. Every
one of them is a NUMBER. It never occurred to anyone here that the same rot
happens to prose, and prose is what people act on. So `FOR-THE-REVIEWER.md`
still called durable drafts and pointer identity "NOT deferrable prerequisites"
two releases after both shipped, `DESIGN-DIRECTION.md` stated the draft problem
as current, and `START-HERE.md` said Pad's autosave "holds strokes but not media
bytes" seven hundred lines above its own paragraph explaining that the bytes go
to IndexedDB. A 3,328-assertion harness saw none of it.

The cost was not embarrassment. The reviewer read a stale docstring in
`skribl/models.py` claiming the database rate limiter was *"NOT yet verified on
PostgreSQL across processes"* and filed a MEDIUM finding asking for a test that
`verify_postgres.py` has been running since v211 — four real gunicorn worker
PROCESSES, twelve barrier-released requests against a quota of two, asserting
both no over-admission and no under-admission, with worker PIDs compared before
and after so a respawn cannot mask the result. **Stale prose does not merely
mislead a reader; it spends the attention of the person paid to find real
problems.**

That same docstring was wrong a second way, which nobody had reported: it said
*"there is no row lock or advisory lock enforcing 'at most N active slots'"*
while `ratelimit.py` runs `pg_advisory_xact_lock` on every reservation. It
**understated a security-relevant guarantee** and denied the mechanism that makes
it correct. It also got the original bug backwards — the failure was not
over-admission but the opposite: twelve concurrent posts against a quota of two
all inserted before any count ran, every request saw 12 > 2, every request
withdrew, and ZERO were admitted. SQLite's single-writer lock hid it completely.

**The gate.** `verify_docs.py` now pairs a capability with the artifact that
PROVES it shipped and with the phrasings that would only appear if it had not.
When the proof holds, no current-facing document may deny it. Written against
the unfixed tree it caught all five stale locations, which is the order these
things should happen in.

Two design choices carry the weight. It scans **source files** as well as
documents — the reviewer's false finding came from a docstring, and code comments
are read more literally than prose, not less; that extension immediately found
the two extra instances above. And its exemption list is a small **closed set of
explicit markers**, so a changelog can still state what used to be true, and
adding an escape hatch is a decision rather than a slide. `DESIGN-DIRECTION.md`
keeps both superseded requirements verbatim under a status header, because a
deleted requirement cannot be checked against what was built.

Stated in the code, because overclaiming here would be the same sin: it catches
denials it has PATTERNS for. A newly-invented stale sentence about some other
capability sails through exactly as before.

**The beading fix is pinned now.** v224 shipped the Air-brush translucent-stroke
fix with an honest note saying it was *not pinned by an assertion*. The review
ranked that second and was right — disclosure does not stop a refactor from
silently undoing it. Nothing else here could see it: the strokes are
byte-identical before and after the repaint, so it is not a geometry, structural
or data change. Only the pixels differ.

`verify_beading.py` draws one Air-brush stroke with the mouse and repaints it
three ways, comparing ALPHA profiles: through the marquee-selection repaint,
through the tool-change path that made picking the eraser re-bead the whole
canvas, and through the raw painters that were the pre-fix code. The mutation is
the load-bearing part — the raw path must come back WORSE, or the compositor is
doing nothing. Measured: composited mean alpha **51**, raw **118**, healed back
to **51**.

Two measurement traps are recorded because both produced a green-looking lie in
the first draft. It reads the **alpha channel**: the canvas is transparent-backed,
so `getImageData` returns straight RGBA and a 22% white stroke reads r=255, a=56
— the colour channels are saturated and carry no coverage at all. Measuring red
reported a spread of ZERO on a visibly correct stroke. And it **ignores non-grey
pixels**, because a marquee paints a purple outline that is not ink; counting it
reported a spread of 138 for a repaint that was perfect.

**Evidence that names its own coverage.** The review filed the `verify_mp4.py`
skip as an open gap and recommended a CI lane with real H.264 — which
`.github/workflows/harness.yml` has run since v103, and which FAILS if the suite
merely skips. The lane was shipping inside the archive under review. The finding
was not careless: the evidence never pointed at the thing that closed the gap.
`RELEASE.md` now prints, beside each skip, the CI job that covers it or the words
NOT COVERED — generated from a table, never typed — and `verify_docs.py` checks
that each named job exists in the workflow and actually invokes that suite.

**"Sealed" now says what it is not.** `SHA256SUMS` lives inside the archive it
authenticates, and so does the tree hash. The seal detects corruption and
accidental substitution; it does not prove who built the archive. The documents
say so, and point at the one provenance channel that actually exists here — the
hash of the zip, recorded in the git commit that seals the release, which did not
travel with the file. A signed tag or CI attestation would be stronger and
neither exists yet.

## Findings and where they went

| Finding | Severity | Outcome |
| --- | --- | --- |
| R1 documentation contradicts implemented state | MEDIUM | **Fixed**, plus the gate that prevents recurrence (`verify_docs.py`) |
| R2 beading fix unpinned | MEDIUM | **Fixed** — `verify_beading.py`, 16 assertions with a mutation pass |
| R3 PG cross-process limiter unproven | MEDIUM | **Was already proven** since v211; the docstring saying otherwise is corrected, and it also understated the advisory lock |
| R4 MP4 skip not release-gated | LOW | **Lane already existed**; the evidence now names it, and `verify_docs` checks it is real |
| R5 seal is not provenance | LOW | **Accepted and documented**; zip hash published through git |
| R6 carried UX debt | LOW | Doc half fixed with R1; the UX items remain open and scheduled by the owner |

## Still open, carried honestly

* The **v213 stray-line report** has never been shown to be the contact-identity
  defect that `lib/eventpoint.js` fixed. Contact identity is closed; that report
  is not.
* The **641px layout cliff**, **Clear all**'s placement, and Flip's **two buttons
  both labelled "Move"** are unchanged and are owner scheduling, not defects
  awaiting a decision.
* A **signed tag or CI attestation** for release provenance does not exist.
* `verify_tools.py`'s **V213n block is still PARKED** behind
  `_SELECT_TOOL_ON_PAD = False`, and one of its assertions is still the only
  thing that pinned the history-stack aliasing fix.
