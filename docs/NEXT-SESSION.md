# Next session: the handoff (Nov 25, 2026, Mountain Time, written mid-morning)

A snapshot from a session of Wednesday morning, Nov 25. It is not
maintained: where things stand is the newest entries at the
bottom of `DECISIONS.md`, and how to work is `WORKING-AGREEMENTS.md`. Read
this after `START-HERE.md`; once you have, replace it with your own or
delete it, so it never goes stale here.

## Before anything: read main's newest full runs

Every job, before believing main is green. The run after #1098 (Flip's Draw
back) is the one that covers it: read it whole. Main was green on every job
after #1095 (it covered Pin and Two Hands). Not sealed since v330, which is
fine (`WORKING-AGREEMENTS.md`, "Sealing a release").

## What happened this session

- THE FRIEND'S THREE DESIGN PACKS, weighed (nothing built from them):
  https://claude.ai/artifact/SpdandvSjk9XzLcQAywQLk. Most of the 78 screens
  show what is already built (they were drawn from v330's code). Worth a
  mock, the owner's to pick: drawers beside the drawing on a desk (measured:
  Pen open on a 1440×900 desk leaves 66% of the Pad's drawing on screen,
  53% of Flip's; 49% for Flip at 1536×864); Blooby peeking in empty places
  (drawn by hand in the Pad: their peek is the "little car" dropped on Nov
  12); a weekly prompt that is a draw-back ("Draw back on Blooby"). Left:
  the glossy Blooby, a permanent tool rail and side panel, words under the
  phone bar, header buttons for Save draft, Export and Share, busy panels.
  The friend's brand vision was already in the tree with Cal's notes of Nov
  24 (`docs/research/blooby-brand-and-mascot-vision/`); the packs
  themselves are not in the tree.
- #1098 FLIP'S DRAW BACK, PAGE FOR PAGE (merged about 10:20 AM): the five
  answers, A each, and what was decided in the building (`DECISIONS.md`,
  "Flip's Draw back, page for page: built"; `docs/SOCIAL-SITE.md` section
  42). Main's run after it was still going when this was written.

## The owner's two small calls from #1098, answered

The owner, Nov 25, about 10:30 AM: "Keep Copy dimmed; draw-on pages play
hers then his". A Flip with a page that draws itself has the pen now, that
page playing her strokes, then his (built the same morning). Copy stays
dimmed, and so does Draw (it is her timing; light it only if the owner
says so).

## Recolor while drawing back: all yes, building

The decided order's next step, mocked (https://claude.ai/artifact/XUcG9eV3zEBTpGn936wneo)
and answered "All yes" about 11:20 AM: Recolor on while drawing back, his
lines only; a tap on hers says whose it is; the magnifier shows hers
faint; a drawing with recolours gets the pen (`DECISIONS.md`, "Recolor
while drawing back, mocked"). Being built the same day.

## Waiting on the owner's phone

- Flip's Draw back. One-glance tell for the new build: under a Flip's card,
  the pen after the heart (a Flip had none). Tap it: Flip opens over the
  composer on her pages, her page faint under the one you are on, her pages
  faint in the strip; Blank and the rest dimmed. Draw on a page or two, Add,
  Post. Not tested here on WebKit or in SF.
- Carried: Pin, Two hands once the switch is on, and Nov 24's list
  (`git show 2c4ba23:docs/NEXT-SESSION.md`).

## Then, in the decided order

Recolours on a draw-back, messages as drawn letters, watching first
everywhere (`DECISIONS.md`, "The owner's clarifications to the final
recommendations"). Two hands' own next steps are as the morning's handoff
said (`git show 928e5d7:docs/NEXT-SESSION.md`): plays of Both not counted,
a quote of a two-hands draw-back shows his own picture, recolour off while
drawing back, a two-hands draw-back not drawn back on.

## What saves time

- `SOCIALDRAWBACK_PART=16` runs Flip's Draw back alone in about 30 seconds
  on its own server; `switch_on()` in the suite starts the second server
  with the owner's switch on, once, for whichever section asks (15 and 16).
- Calibration as a script, one worktree per break: each break a
  (file, exact text, replacement) asserted to apply once before anything
  runs, main as its own tree with the branch's suite copied in, three at a
  time, the red rows read off each log. Twenty-seven trees took about
  six minutes.
- START-HERE's module index is generated (`harness/gen_docs.py`, from each
  module's first comment and the templates that load it): never edit it by
  hand; verify_docs says STALE.
- Flip's ways in are many (buttons, keys, the ⋯, a hold on a tile): a rule
  for Flip's pages lives in the functions that change them (`flip.js`
  `dbHeld`), and one row tries every door.
