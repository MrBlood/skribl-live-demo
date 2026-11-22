# Next session: the handoff (Nov 22, 2026, Mountain Time: written at about 3:15 PM, for Tuesday evening, Nov 24)

A snapshot from the session of Nov 20 to 22, written as its last step at
the owner's request: "I will start a new session on Tuesday evening, so
make a comprehensive handoff for the new session". It is not maintained:
where things stand is the newest entries at the bottom of `DECISIONS.md`,
and how to work is `WORKING-AGREEMENTS.md`. Read this after
`START-HERE.md`; once you have, replace it with your own handoff or delete
it, so it never goes stale here.

The owner stopped for the week with a little usage left, and said: "Let's
not start anything new and just let everything finish". Nothing was left
half-built: every change is merged, and the branch held nothing else.

## Before anything: read main's newest full runs

Two of main's full runs were still going when this was written:

- the one on #1065 (Text on a phone), started at 2:43 PM. The old
  session's last check read it at 3:55 PM and told the owner; that result
  is in the old conversation, not here;
- the one on the pull request that brought this handoff (documents only).

Read main's newest full runs, every job, before believing main is green.
A red is work in progress: read the failing row, mend the defect (or the
check that cries wolf, with a calibrated check), open a PR, merge on green.

Not sealed since v330. That is fine: seal only when there is a reason
(`WORKING-AGREEMENTS.md`, "Sealing a release").

## First: Text on the owner's iPhone, two bugs not yet mended

The owner's iPhone 17 (iOS 26), the Home Screen app, Nov 22 from 2:50 PM,
after #1065 had merged. Six pictures, then a test on the Pad on its own.

WHAT WORKS NOW (#1064, #1065; the owner: "The text drawer looks great
when we start and when I click in box"):

- Text opens with its whole drawer and no keyboard.
- A tap on the box brings the keyboard. The drawer then sits on the keys:
  the box, Write it, and Style's four chips.
- The keyboard's tick brings the whole drawer back.
- Inside the site, the page behind the Pad no longer moves (the timeline
  no longer creeps under it).

### Bug 1: inside the site only, each letter moves the Pad

"1st letter jumps and second letter jumps again. Third letter jumps to
this. 4th is still there." The Pad was in the site's frame over Make
(`social/static/social.js`, padOver), the keyboard up and the box
focused:

- The first letter moved the Pad: its header went up inside the frame,
  and the drawer slid down under the iPhone's own strip (^ v and the
  tick, which floats over the top of the keys).
- The second letter moved it again.
- After the third, the drawer showed Size, Thickness and Speed. The
  typing view had dropped, though the keyboard was still up and the box
  still focused. The drawer's foot sat at the strip's top, the tools above
  it.
- The fourth letter moved nothing.

Then, on the Pad on its own page (not from Make): "The drawer works". No
jumps there. So bug 1 belongs to the frame.

Where to look:

- `skribl/static/lib/textwrite.js`, fitKeyboard. The typing view needs a
  phone, the box in focus, and `kb` over 80. `kb` is the outermost
  window's `innerHeight` less its visual viewport's height (the function
  just above fitKeyboard reads the outermost window). After the third
  letter that test went false with the keyboard up. So either the outer
  `innerHeight` came down to the visual viewport's height (iOS resizing
  its layout viewport), or the box let go of its focus for a moment.
- `social/static/social.css` `body.facepad-open` and padOver's hold() and
  letGo() (#1065): while the editor is up, the page behind is fixed where
  it stood. Before #1065 the page behind scrolled on every letter; now the
  frame's own document does instead. Each keystroke seems to scroll
  whatever can still scroll. That is most likely iOS revealing the caret
  of a box in a `position: fixed` drawer, inside a frame, inside a fixed
  overlay: a long-standing WebKit habit. Not reproduced here, because
  there is no WebKit in this box.
- The Pad on its own does not jump. Compare what differs: the frame, the
  fixed overlay, the frame's height, the fixed page behind.

Ideas to weigh, none tried, none to believe until the owner's phone says:

- hold the frame's own document still while typing, as the page behind is
  held;
- read the keyboard so that neither a pan nor a resized layout viewport
  can drop the typing view while the box is in focus;
- keep the box out of a fixed layer while typing.

If a guess needs numbers, ask the owner for the Viewport line that the
Pad's Report a problem copies (`docs/DEVICE-CHECKLIST.md`), taken inside
Make before and after a letter.

### Bug 2: everywhere, the words cannot be dragged with a finger

"can't drag letters, still jumps right every touch. Not draggable", and
from the Pad on its own: "can't drag on skribl pad standalone". Before
#1065 it was the same: "Each time I touch it it jumps to right or up and
over to the right."

- THE CHECK WAS BLIND TO IT. `harness/verify_text.py` part 16's drag row
  drags with a MOUSE, and checks only that the words moved right and up.
  A jump to the right passes it. Make it drive a finger (touch events on
  a touch page) and check that the words follow the finger by the drag's
  own amount. Show it red on today's tree before mending anything.
- A LEAD, NOT A FINDING. With the drawer up, a press on the drawing moves
  the words to the press. That is the TEXT branch of the drawing's press
  in `skribl/static/editor_draw.js`, which calls `SkriblText.place`; Flip
  has the same call in `skribl/static/flip.js`, and `place()` itself is in
  `skribl/static/lib/textwrite.js`. Suppose an iPhone's finger on the
  words reaches the drawing's press instead of the words' own box (whose
  pointerdown starts the drag). Then every touch moves the words' anchor
  to the finger, which is right of where they were when the finger is on
  their middle, and they never drag. That would match the owner's words
  exactly.
- One cure that holds whatever the cause: a press on the drawing that
  lands inside the words' own box starts their drag instead of placing
  them anew.
- Keep what #1065 did for a drag while typing: the drawer no longer steps
  aside, so the keyboard stays.

The Pad and Flip share the drawer and its script: whatever mends it mends
both, and says so.

## What happened Nov 21 and 22 (all merged)

Nov 21, evening:

- #1040 The moving bottom bar: a phone that still thinks its keyboard is
  up is asked to measure again.
- #1041 Report a problem says what the phone takes its screen for (a
  Viewport line).
- #1042 The colour audit's five fixes.
- #1043 The colour audit's yes: 1, 5, 6, 7, 8 and 10a.

Nov 22:

- #1044 A draw-back's card: the time's words take their own taps.
- #1046 Main red after the yes-choices: `verify_a11ypages` follows a
  colour's name to its colour.
- #1047 A button takes the page's font (the editors' buttons were in
  Arial on Windows).
- #1049 Text inside a post: the drawer sits on the iPhone's keyboard, and
  New takes the words in the box.
- #1050 Main red after the button font. CI draws the editors in
  Liberation Sans.
- #1051 A held finger selects no control.
- #1052 and #1053 "Blooby and Search": the wordmark in the middle on a
  phone, five places, and Search of its own.
- #1054 See all has its way back.
- #1056 No new colour written straight into a rule (the audit's 10b).
- #1057, #1058, #1059 and #1060 "Four Looks":
  - Skribl's own Gallery and Library cards have the edge alone (3, A);
  - a press that shows, on Blooby (4, A);
  - the Pad's and Flip's last soft shadows (2, after);
  - the chosen word a step bolder, its room kept (11, A).
- #1061 Text's drawer kept room for the iPhone's strip. Replaced by #1064.
- #1063 Main red after #1060 mended: the Who can draw back pill keeps its
  room, and a sign-in read waits for its page.
- #1064 Text: Style stays under the words while they are typed, and the
  empty room goes.
- #1065 Text on a phone:
  - it opens whole, and a tap on the box brings the keyboard;
  - inside the site, the page behind holds still;
  - a drag keeps the keyboard.

Each has its `DECISIONS.md` entry, with what was checked and what was
shown red.

## Waiting on the owner

- Their iPhone, still to say: has the bottom bar ridden the page since
  #1040? Does a held finger still select anything (#1051)? Does a press
  show, on Blooby (#1058)?
- Flip's desk page bar lost its group gaps after #1047 in this box's font
  (`harness/verify_pages.py` is red here and green in CI's font). See
  `DECISIONS.md`, "FOUND ON THE WAY, ITS OWN NEXT". Mock it if they want
  one.
- The Gallery's chosen "New" reads 6.24:1 in light: over AA, under the
  page's own 7:1. The 7:1 check in `harness/verify_galib.py` cannot read
  words in the span that `skribl/static/lib/labels.js` adds. See
  `DECISIONS.md`, "AND A BLIND SPOT, NOT MENDED HERE".
  - The owner's to say: hold that pill to AA, or darken it.
  - Mending the check's blind spot is a bug fix, and needs no yes.
- Not decided, carried from Nov 20:
  - initials in the empty circles of "Liked by";
  - whether a tablet's Make card rides its keyboard;
  - bands for lists of one thing a line (Activity, people).

## Still to build, in the decided order (from the Nov 19 handoff)

1. Flip, page for page: Draw back's Flip twin. Its own mock first. The
   page that stays underneath (`FUTURE.md` 6i) is its twin.
2. Recolours on a draw-back: refused, with why, for now
   (`social/drawback.py`, drawable). They index the strokes by number and
   time, which the join would have to carry over.
3. Then the owner's list from Nov 18: messages as drawn letters
   (`docs/SOCIAL-SITE.md` section 17), then watching first everywhere.

Behind all of it are the roots in `WORKING-AGREEMENTS.md`: "Skribl Pad
first", and Blooby as the place where people talk in drawings.

## Open thread carried

On SQLite with media kept in a store, a post with a photo or music answers
"busy" (503). The site's post route reads through the request's session
before Skribl stores the post. The store's claim then commits on a
connection of its own (`skribl/creation.py`), which waits on SQLite's lock
and gives up. This doesn't affect the live site (it posts music) or
PostgreSQL. Not fixed: ending the request's read before `create_post`
would likely mend it, but it touches every post, so it wants its own look.

## How this session worked, and what saves time

How to run things:

- Suites ran side by side with `harness/run_parallel.py -j 3 <suites>`,
  on a clean worktree of the commit (commit first). This box has four
  cores. More than three side by side made frame-paced checks
  intermittent, so a red beside others is re-run alone before believing
  it.
- A check was calibrated on a copy of the tree with one break applied,
  served by a server of its own, running only the part that matters.
  `TEXT_PART` and `SOCIALPROFILE_PART` run one part alone; each suite's
  header says how.
- `harness/bootstrap.sh` makes the pinned Python (`/tmp/skribl-venv` by
  default). Put it first on PATH: with the box's own python3,
  `verify_docs` goes red on two rows (the interpreter and the lock).
- The scratch scripts this session used (runs on worktrees, calibration
  copies) were in its scratchpad and are gone with the container. Make
  them again if useful.

Lessons from Nov 22:

- A drag check drives a finger and checks the follow, not just the
  direction (bug 2's blind spot).
- The iPhone's own strip (^ v and the tick) is about 60px tall and floats
  over the top of the keys. The visual viewport sometimes counts it and
  sometimes does not, and no web API says which (`DECISIONS.md`, "Text's
  drawer clears the iPhone's own bar"). Style under the box while typing
  (#1064) made the strip's place matter less.
- A tap on Text's box is taken by the page (its default stopped), so that
  the phone does not slide the page up to show the box (#1065).
- Inside the site, the editor overlay holds the page behind:
  `body.facepad-open` in `social/static/social.css`, held by
  `harness/verify_socialprofile.py` part 21.
- For "it doesn't show on my phone", give a one-glance tell for the new
  build and ask for a reload first.

Habits:

- After a squash merge, check that main's tree is the tree that was
  tested. Then restart the branch from main (`git checkout -B <branch>
  origin/main`) and push with `--force-with-lease=<branch>:<old sha>`.
  That worked through Nov 22. `merge_pull_request` needs the head's full
  sha.
- While long work is in progress, keep an hourly check-in on the session
  (the owner's rule, `WORKING-AGREEMENTS.md`). Remove it once the work is
  merged, main's run is read, and the owner is told. At the end of this
  session it was turned into one last check at 3:55 PM, which reads main's
  run and then deletes itself.

Still true from the Nov 19 handoff:

- The site warms its static files when it starts, so a change to
  `social/static/social.css` or `social/static/posts.js` is not served by
  a server already running. Restart it before believing what you see.
- Every Pad drawing carries a picture of its blank paper
  (`baseSnapshot`), so Skribl's `on_photo` is true for nearly every Pad
  drawing. It does not mean a photo; a photo is `frames[0].photo.data`.
- `harness/verify_seam.py` reads `skribl/describing.py` and
  `skribl/__init__.py` closely. It pins some import lines word for word
  and resolves names at the module's top, so an import inside a function
  is red there.
- The in-post player's byte budget rises only for a named cost the owner
  said yes to, written beside it in its own format.
- A block is held twice for anything of Skribl's (the site's own check,
  and Skribl's `visible_to` through the site's hook). To see a block's row
  go red, take both away.
- A post made through the site's own requests carries no picture (the Pad
  makes it). For a site that looks real, open the composer's Pad and call
  `loadSkribl(payload)` in its frame (Flip's is
  `window.SkriblComposeLoad`), then Add and Post.
- Mocks are made by driving the real site with Playwright and laying the
  option over it. The suites' fixtures (the head of
  `harness/verify_socialcomments.py`) make a site with people in a minute.
