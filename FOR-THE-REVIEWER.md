# For the reviewer

Written by the assistant that made these changes, for whoever checks them.

---

## Before anything else

**This is v222, UNSEALED.** The durability release: flush-on-leave, a
durability-keyed navigation guard, IndexedDB media drafts, and the P0 prefix
navigation fix — plus a harness-integrity repair the work itself surfaced
(a suite that could fail 4 assertions and still aggregate as PASS).
Narrative and technical notes: `V222-CHANGES.md`. Every suite touched by or
adjacent to this work has been run green (the list is in V222-CHANGES.md),
but the FULL release aggregate has NOT been executed against this tree —
`harness/RELEASE.md` still describes the v221 seal, deliberately left rather
than restamped, exactly as the v219 note below explains. Run
`python3 harness/release_run.py` before treating this as a release.

(The v221 paragraph this replaces: v221 was the identity release — header
piece marks, accent token work, tree-hash unification; a full run stood
behind its seal. Everything below was written at earlier seals and is kept
as history; its discipline is unchanged.)

For most of its life this file said the opposite, and that was correct at the
time: v219 was built without a run, and `harness/RELEASE.md` and
`harness/LAST-RUN.txt` were deliberately left describing **v214** rather than
restamped, because restamping would have made the archive claim evidence it did
not have. That state is recorded here rather than deleted, because the reason it
existed is the discipline itself.

What has changed is only that the run was executed. `harness/RELEASE.md` and
`harness/LAST-RUN.txt` are generated from it and describe THIS tree hash. Both
numbers are computed by `release_run.py`, never typed into prose.

The earlier build was also verified mechanically, and those checks still hold:
`node --check` on every changed script, a Jinja parse of all 13 templates, a
`<div>` balance check on both editors, the rendered DOM structure of both
editors, and toolbar/header geometry measured in headless Chromium from 320px to
1280px. The run does not replace those; it adds the thing they could not give —
**the app actually running.**

Two gaps in this run are named rather than buried, because a skip is not
coverage: see the skip list in the RELEASE.md header and read it before treating
an absence of failures as an absence of gaps.

---

## Verify before believing any of this, including me

    cd skribl-v222
    grep -Ec '^[0-9a-f]{64} ' SHA256SUMS      # N: the manifest's own entry count
    sha256sum -c SHA256SUMS | grep -c ': OK'  # must equal N, no line missing or extra
    grep -o 'SKRIBL_VERSION = "[^"]*"' skribl/core.py            # expect v222

(These commands deliberately carry no hardcoded file count. This file is
inside the tree hash, so a literal count written here fossilises the moment
the file set changes — the v221 seal shipped with this very block still
saying `expect v219`, and only an archive review caught it. A check that
compares the manifest against itself cannot go stale.)


A NOTE ON THAT FIRST NUMBER, because it is the point. The first draft of this
file said "expect 198". It was correct when written — and then this very file
was added to the archive, which made it 199. A reviewer ran the command, got a
mismatch, and reasonably flagged a sound archive as suspect. It is the exact
failure this project's documentation discipline exists to prevent, committed in
the document that warns about it. `verify_docs.py` now catches it.

Every number quoted in `V219-CHANGES.md` was re-measured against THIS tree
immediately before it was written. None is carried forward from an earlier
build. That matters because carrying numbers forward is precisely the mistake
that produced the stale claims this pass had to correct — see "Corrected claims"
in that file, where a known-open entry had been asserting a 396px-against-355
overage that a later, unrelated change had already fixed.

---

## Run it on the pinned runtime

`.python-version` pins **Python 3.12**, and `constraints.txt` is a hash-locked
cp312 environment. A harness run on any other interpreter cannot be used as
release evidence for this deployment, because the versions it resolves are ones
no assertion has exercised. `verify_docs.py` fails if the pin, the lock and the
running interpreter disagree.

A first review of this archive ran on 3.13 with Flask absent, which is why the
browser and integration suites could not execute. That is an environment
mismatch rather than a repository defect, but it does mean those results cannot
gate a release.

## What a first reviewer found, and what happened to it

An external stress review of this archive found five real documentation
failures, all caught by the project's own `verify_docs.py`:

* README.md and ARCHIVE-README.md still claimed **v214** while the code declared
  v219, and ARCHIVE-README did not lead with the real version.
* **This file told the reader to expect 198 manifest OKs when there were 199.**
  It was correct when written, and then this very file was added to the archive,
  which changed the count. A reviewer ran the command, got a mismatch, and
  reasonably flagged a sound archive as suspect.
* START-HERE.md carried stale expected counts of 196.

All five are fixed and `verify_docs.py` is green on this tree — see RELEASE.md
for the count, which is generated; the figure that stood here was typed, and had
already drifted from the real one. The
second one is worth dwelling on: it is the exact failure this project's
documentation discipline exists to prevent, committed inside the document that
warns about it. Numbers that are typed rather than derived go stale, including
mine.

The same review also confirmed that the four unresolved product risks below are
genuinely recorded rather than hidden, and found no new high-severity security
issue in a source pass. Its central point has now been answered rather than merely
recorded: v219 changed real browser behaviour, and it is no longer packaged with
v214's release evidence — the suites that exercise that behaviour have been run
against this tree.

## Where to start

1. **`V219-CHANGES.md`** — everything since the v214 seal, with the measurements.
2. **`START-HERE.md`** — the project primer. Three decisions from this session
   were added to it so they are not rediscovered or accidentally reverted:
   the Pad/Flip navigation-guard asymmetry, the 360/320 width policy, and the
   rule that every repaint must route through `makeStrokeCompositor`.
3. **`harness/verify_layout.py`** — a new suite. Rendered geometry only:
   `getBoundingClientRect`, `scrollWidth` against `clientWidth`, `offsetParent`.
   Never computed styles, never class lists.

---

## Three things I would attack first

**1. Every geometry number came from a headless browser with `fitBrand()` not
running.** `fitBrand()` is the JavaScript that decides whether the wordmark
shows, so it is exactly what sizes the element I was measuring around. The
margins are comfortable rather than thin — idle header has +19px at 375px,
recording +124px — so I expect them to hold. But a reviewer on a real device is
worth more than my measurements, and this is the assumption the header work
rests on.

**2. `verify_layout.py` has never executed.** It needs a running server. Its
selectors were inferred from the tree, not confirmed: `#pad` in section 2, and
Flip's back-link in section 4. Section 4 also clicks `#flipBtn`, which now lives
inside a CLOSED overflow menu — it almost certainly needs the menu opened first.
Expect to fix it before it passes.

**3. The Air-brush beading fix.** `selRepaint` was the only repaint in the editor
passing the raw `drawDot`/`drawLine` painters straight to
`replayTimelineToCanvas`, so a see-through stroke's own overlaps stacked at every
captured point — and `setTool()` calls it on every tool change, so picking the
eraser re-beaded the whole canvas. It now routes through `makeStrokeCompositor`
like preview, playback and all three export paths already did.

I verified the mechanism synthetically (one 22%-alpha stroke painted both ways:
alpha spread 153 direct against 50 composited) and the owner confirmed it by eye
on device. **It is not pinned by an assertion.** The right test compares the
pixel profile of a translucent stroke before and after a tool change and requires
it not to change — that is a pixel comparison, which `verify_layout.py` cannot
do, and it is the gap I would close first.

---

## Where this is going

`DESIGN-DIRECTION.md` in this archive is the product direction written at this
seal. It matters to a reviewer for one reason: **several things listed below as
"known-open" are not scheduled to be fixed in place — they are scheduled to stop
existing.** Flip's two "Move" buttons and the destructive Clear-all in the draw
drawer are both defects in an interface the direction deletes: Flip's frame strip
becomes directly manipulable, and Pad's permanent media buttons collapse into a
single `+` sheet.

Judge them as real defects today. But if you are weighing whether to demand a fix
now, the honest answer is that fixing them individually would be motion rather
than progress.

Two items in that document are NOT deferrable and are stated there as
prerequisites: **pointer identity** (the stray-line defect) and **durable drafts**
(autosave holds strokes but not media bytes). Those are correctness and data
trust, and no amount of visual restraint substitutes for them.

## Known-open, carried honestly

* **`verify_tools.py`'s V213n block is PARKED, not deleted** — seven assertions
  behind `_SELECT_TOOL_ON_PAD = False`, because v219 removed Select from Pad.
  One of them was the only thing pinning the history-stack aliasing fix
  (`makeHistoryState` does `strokes.slice()`, copying the array but not the point
  objects). **That fix is still in the code and must stay.** It is now a third
  unpinned guard and is recorded as such in START-HERE.
* **The 641px cliff.** One pixel of resize takes Pad's bar from 398px to 565px
  and three buttons regain text labels. 560–640px gets the phone layout on a
  viewport with room to spare. Needs size classes, not a pixel breakpoint.
* **Clear all** still sits at the foot of the draw drawer. It is a destructive
  document command, not a pen attribute.
* **The stray line from the v213 bug report** remains unexplained and untested.
* **Flip's page bar has two buttons both labelled "Move"** doing opposite things.

---

## The thing I would most want a reviewer to know

**Four broken builds reached the owner during this session.** Unbalanced HTML
that closed the toolbar's container early. A modal nested inside a hidden panel,
so clicking the button appeared to do nothing. CSS class names I assumed existed
and never checked. An unguarded `getElementById(...).addEventListener` on an
element I had just deleted, which threw at load and killed every line of
`flip.js` after it.

**Every one passed `node --check`, template parsing and geometry measurement.
Every one was caught by a screenshot.**

If you want a single lever on this archive, that is it: **the automated checks
here verify structure, and the failures that got through were failures of
appearance.** Section 4 of `verify_layout.py` was written in that spirit — it
asserts the URL after clicking Flip rather than asserting the confirm dialog
appeared, because a dialog appearing proves a dialog appeared, and only the URL
proves the work survived.

The same instinct is worth applying to whatever you check next.
