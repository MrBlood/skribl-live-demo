# Next session: the handoff (Nov 24, 2026, Mountain Time, written in the evening)

A snapshot from the session of Tuesday evening, Nov 24. It is not
maintained: where things stand is the newest entries at the bottom of
`DECISIONS.md`, and how to work is `WORKING-AGREEMENTS.md`. Read this after
`START-HERE.md`; once you have, replace it with your own or delete it, so
it never goes stale here.

## Before anything: read main's newest full runs

Every job, before believing main is green. Main went green again with
#1078 (the "main is red" issue, #1067, closed itself at 5:26 PM), and the
runs after #1080 and #1081 were green, every job. The runs after #1082,
#1083 and this note were still going when it was written: those are the
ones to read.

Not sealed since v330. That is fine: seal only when there is a reason
(`WORKING-AGREEMENTS.md`, "Sealing a release").

## The environment

Start in the environment named skribl-live-demo, not Default. Its network
allows the live demo, `skribls.net` and `media.skribls.net`, and Another
App's site (kept out of this public repository on purpose; get_environment
lists it). Its setup script builds the test Python at `/tmp/skribl-venv`;
if that is missing or half-made, `harness/bootstrap.sh` makes or finishes
it. No secrets are saved on it, and none are needed.

This session ran in Default: `harness/bootstrap.sh` built the venv in a few
minutes, and nothing tonight needed the other hosts.

## What merged on Nov 24 (each has its DECISIONS.md entry)

- #1078 Main red after #1065: Text's box had a touchend and no touchcancel
  (`verify_tools` V214b).
- #1079 Text: a press on the words holds them, wherever the screen sends it.
  On the owner's iPhone a finger on the words reached the drawing, which
  moved the words to the press ("jumps right every touch").
- #1080 Text inside a post on an iPhone: the editor's own page holds while
  the words are typed, the typing view stays while they are in focus, and
  Report a problem carries `Text:` readings of what the keyboard did.
- #1081 How it works opened from the site's page: closed as it is read
  (its ×, the dim, Escape), back to the page.
- #1082 The Gallery's chosen New reads 7:1 (the Library's own ink), and
  `verify_galib` reads words inside the spans `lib/labels.js` makes.
- #1083 Text: once the words are down, only a drag moves them (the owner's
  "all yes"). A press before any words show still says where they go.

## Waiting on the owner's phone

- Text, drag: words in Text's box, a finger on their right half and a drag:
  they go with the finger. A tap on the drawing away from them leaves them
  where they are.
- Text, letters in Make: if a letter still moves the Pad, ⋯ → Report a
  problem → Copy, pasted: its `Text:` lines say whether the phone scrolled
  the editor's page (`page`) or panned its whole view (`seen …@`). The
  likelier rest of bug 1 is the pan (see #1080's entry, "WHAT THE HOLD
  CANNOT DO"); its mend wants those numbers.
- How it works: from the site's How it works page, choose the Pad, then
  close How it works with its ×: back on the site's page.
- From Nov 21 and 22: does the bottom bar still ride the page (#1040); does
  a held finger still select anything (#1051); does a press show on Blooby
  (#1058)? And the long-carried device check (`docs/DEVICE-CHECKLIST.md`).

## Waiting on the owner's picks (mocks, nothing built)

- Four Small Picks, https://claude.ai/artifact/6LBvgdt8rnn3F3PaGU5ibg:
  Draw back's pill (A: gone at the first stroke, Theirs in Media's place in
  the dock), How it works' row with a mouse (A: ‹ › arrows, mouse only),
  Repost on your own drawing (A: Post it), Flip's desk page bar (A: 10px
  padding). Cal's pick is A each.
- Draw Back, Two Hands, https://claude.ai/artifact/FQGL42ZgaWaqwsytxqZkVe:
  a draw-back kept as two people's own work (Both · hers · his to watch;
  hers removed), and the nine questions before any schema, Cal's pick A
  each. They follow the open list in the owner's final recommendations
  (`docs/research/blooby-final-recommendations/LAYERS_AND_DRAWBACK_ARCHITECTURE.md`).
  No schema change until they are answered.
- Pin This Post, https://claude.ai/artifact/AdKKmDpwvsTHcQuLvYikNJ: Pin in
  the post's ⋯ (A), and the pinned post first in Posts with a "Pinned"
  line (A) or above the tabs (B).

## Then, in the decided order

Flip page for page (Draw back's Flip twin, perhaps the first user of the
contribution model), recolours on a draw-back, messages as drawn letters,
watching first everywhere.

The precedence: `docs/research/blooby-final-recommendations/` is the one
source, read as advice (its author read files; no app, no tests). The
owner's clarifications are `DECISIONS.md`, "The owner's clarifications to
the final recommendations": bugs first; the contribution architecture
mocked and approved before any schema; Fill stays in Flip; and an approved
feature is never held back by the package's order without talking through
its real dependencies first.

Parked: initials in "Liked by", a tablet's Make card, bands for one-line
lists. Optional, when the owner asks or there is room: a walk of Another
App (the owner's ask, Nov 23): how it behaves, never its look; as a
visitor, politely, skipping what its robots file asks crawlers to skip;
ask before signing up or posting anything there.

For reference only: the owner's Blooby brand ideas,
`docs/research/blooby-brand-and-mascot-vision/`, with Cal's notes beside
them. Ideas, nothing on the build list; the owner likes the peeking Blooby
most.

## Open thread carried

On SQLite with media kept in a store, a post with a photo or music answers
"busy" (503). The site's post route reads through the request's session
before Skribl stores the post; the store's claim then commits on a
connection of its own (`skribl/creation.py`), which waits on SQLite's lock
and gives up. Not the live site (it posts music), not PostgreSQL. Ending the
request's read before `create_post` would likely mend it, but it touches
every post, so it wants its own look.

## How this session worked, and what saves time

- The container restarted twice mid-run and took every background run with
  it. Commit before running, and re-run whole what was cut off.
- A finger, in Chromium, on Text's box reaches the box; the iPhone did not.
  `verify_text` 25 stands in for the iPhone by letting the press through the
  box to the drawing.
- Once Text's words show, a press no longer moves them. A check that needs
  them somewhere presses before they show (`place_words` in
  `harness/verify_text.py`), or sets them by the call a press makes
  (`set_words`).
- `verify_galib`'s reader reads every word in a box, each by its own
  element; a row that counted pieces counts what it now sees (the Drafts
  menu's four).

## Still true (carried from earlier handoffs)

- Suites side by side: `harness/run_parallel.py -j 3 <suites>` on a clean
  worktree of the commit (commit first). More than three side by side makes
  frame-paced checks intermittent, so a red beside others is re-run alone.
- Calibrate on a copy of the tree with one break, served by a server of its
  own, running only the part that matters (`TEXT_PART`,
  `SOCIALPROFILE_PART`; each suite's header says how).
- Put the venv first on PATH: with the box's own python3, `verify_docs` goes
  red on two rows (the interpreter and the lock).
- After a squash merge, check that main's tree is the tree that was tested,
  then restart the branch from main (`git checkout -B <branch> origin/main`)
  and push with `--force-with-lease=<branch>:<old sha>`.
  `merge_pull_request` needs the head's full sha.
- While long work is in progress, keep an hourly check-in on the session;
  remove it once the work is merged, main's run read, and the owner told.
- The site warms its static files when it starts: after a change to
  `social/static/social.css` or `social/static/posts.js`, restart the
  server before believing what you see.
- Every Pad drawing carries a picture of its blank paper (`baseSnapshot`),
  so Skribl's `on_photo` is true for nearly every Pad drawing. A photo is
  `frames[0].photo.data`.
- `harness/verify_seam.py` pins some import lines of `skribl/describing.py`
  and `skribl/__init__.py` word for word, and resolves names at the module's
  top.
- The in-post player's byte budget rises only for a named cost the owner
  said yes to.
- A block is held twice for anything of Skribl's (the site's own check, and
  Skribl's `visible_to` through the site's hook): to see a block's row go
  red, take both away.
- Pictures for a mock of the site: posts made through the site's requests
  carry no resting picture. Post through the composer (Make, the Pad,
  `loadSkribl(payload)`, Add, Post; Flip's is `window.SkriblComposeLoad`)
  or paint the payload in the Pad and picture its canvas. The suites'
  fixtures (the head of `harness/verify_socialcomments.py`) make a site
  with people in a minute.
- The iPhone's own strip (^ v and the tick) is about 60px tall and floats
  over the keys; the visual viewport sometimes counts it and sometimes does
  not.
- "It doesn't show on my phone": give a one-glance tell for the new build
  and ask for a reload first.
