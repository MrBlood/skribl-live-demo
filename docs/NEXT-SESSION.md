# Next session: the handoff (Nov 26, 2026, Mountain Time, written about 9 AM)

A snapshot from the session that built drawn letters on the morning of
Thursday, Nov 26. It is not maintained: where things stand is the newest
entries at the bottom of `DECISIONS.md`, and how to work is
`WORKING-AGREEMENTS.md`. Read this after `START-HERE.md`; once you have,
replace it with your own or delete it. The handoff before this one is
`git show 9a8542c:docs/NEXT-SESSION.md` (the plan for drawn letters, and
what the code already gave them).

## Before anything: read main's newest full runs

Every job. Main was green after #1111 (the docs before the build). The runs
after #1112, #1113 and #1114 (the server, the Pad, the pages) were still
going when this was written: read the newest one whole before believing
main is green. Not sealed since v330, which is fine.

## What was built: drawn letters, all four parts

The owner's yes (Nov 26, A for all six), and their two answers: a push for a
new letter under its own switch in Settings, on by default; a written-back
letter plays theirs in three seconds, then yours. `docs/SOCIAL-SITE.md`
sections 44 (the server), 45 (the Pad), 46 (the pages); `DECISIONS.md`, the
three "Drawn letters" entries after "the owner's yes".

- THE SERVER (#1112): `social/letters.py`, `social_letters`, migration
  `d3a8f1c6e2b4`; the letter's drawing is Skribl's with the site's HELD
  visibility "letter" (Skribl's new `set_visibility_values(..., held=)`),
  read by its two through `app.py`'s policy. Report of a letter, takedown,
  account deletion, the nudge and its Settings switch.
- THE PAD (#1113): Skribl's `composehost.say` (`skribl:compose:say`, both
  editors): Send, the pill, what steps aside. The site's `letters.js`.
- THE PAGES (#1114): Write on a friend's page, the envelope and Letters,
  Letters' rows, Write to…, the two of you.
- `verify_socialletters` holds all of it; every row was shown red by
  breaking its part (the calibration script's breaks are listed in the
  DECISIONS entries).

## Waiting on the owner

- ONE-GLANCE TELL for the new build, on a phone: an envelope beside the
  bell at the top of Home. On a friend's page (you follow each other),
  Write beside Following. Not tested here on WebKit, SF or Segoe UI.
- ASKED: the desk board's three columns (list and letter side by side) were
  not built; a desk shows Letters and the two of you as two pages. Build it,
  or keep two pages?
- SAID, overrulable: "only the two of you see it" in the Pad's pill (the
  mock said "only she sees it"; the site keeps no pronouns); one Write back
  and New letter per page; the ⋯ per sheet; the hand-off mark as the
  player's own dot; no "Today" headings.
- Carried from before: drawers beside the drawing on a desk, Flip's Draw
  back, two hands behind the owner's switch, Pin
  (`git show 9a8542c:docs/NEXT-SESSION.md`, "Waiting on the owner's desk
  and phone").

## Then, in the decided order

Watching first everywhere (`DECISIONS.md`, "The owner's clarifications to
the final recommendations"). On the list for letters: a Flip letter, page
for page, as Flip's Draw back is (Skribl's part already serves both
editors); photos and music in letters, if the owner wants them later.

## What saves time

- `SOCIALLETTERS_PART=15` runs the pages' rows alone in about a minute on
  their own server; `SOCIALLETTERS_SHOTS=<dir>` writes screenshots of the
  pages as the rows walk them.
- Calibration as a script, one worktree per break, three at a time: each
  break a (file, exact text, replacement, part) asserted to apply once,
  the suite run with that part alone. Thirty-odd breaks took under an hour.
- The rail's order is pinned by `verify_socialactivity` and
  `verify_socialsearch`: a new rail item changes both.
- A new site page that reuses a class another suite reads by (the rail's
  `.tab-activity`) shows up as that suite's red: give it a class of its own.
