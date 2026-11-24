# Next session: the handoff (Nov 22, 2026, Mountain Time: written at about 3:15 PM, added to on the morning of Nov 23, for Tuesday evening, Nov 24)

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

THE RUN ON #1065 FINISHED RED, read at 3:55 PM. It failed in shard 1 on
both databases. The SQLite log names the row: `verify_tools` V214b,
"every touchend handler on ANY receiver is paired with a touchcancel
handler, or named in the allowlist with a reason", pointing at
`textwrite.js:els.field.function`. That is #1065's tap on Text's box,
which listens for touchend and has no touchcancel. (The PostgreSQL log's
summary was not read; it ran the same suites.)

- The app is not hurt: the next touchstart resets the tap.
- The rule stands. Add a touchcancel that clears the tap's start, and
  show V214b red without it and green with it.
- Expect the same row on every later run until it is mended.

Read main's newest full runs, every job, before believing main is green.
A red is work in progress: read the failing row, mend the defect (or the
check that cries wolf, with a calibrated check), open a PR, merge on green.

Not sealed since v330. That is fine: seal only when there is a reason
(`WORKING-AGREEMENTS.md`, "Sealing a release").

## The environment this work runs in (cloud settings, as of Nov 23)

Start the session in the environment named **skribl-live-demo**, not
Default. Default allows only the demo site; skribl-live-demo has
everything below.

- NETWORK: limited. The allowed hosts are:
  - `skribl-live-demo.onrender.com`, the live demo;
  - `skribls.net` and `media.skribls.net`, the owner's site and its media;
  - Another App's site, added Nov 23 for the walk below. Its address is
    kept out of this public repository on purpose: it is the one allowed
    host not named here, and get_environment lists it.

  Package managers and MCP servers are allowed too.
- SETUP SCRIPT, added Nov 23: it builds the test Python at
  `/tmp/skribl-venv`, the venv `harness/bootstrap.sh` uses (Python 3.12,
  the hash-locked install from `constraints.txt`, then
  `harness/requirements.txt`).
  - It runs when a container is built fresh, and skips itself when the
    venv is already there or the repository is not.
  - It was tried here from scratch, and on both skips. It has NOT yet been
    seen on a fresh container: check that `/tmp/skribl-venv` is there.
  - If it is missing or half-made, `harness/bootstrap.sh` makes or
    finishes it (the script leaves bootstrap's own mark on a cut-off
    install).
- `harness/bootstrap.sh` still boots a server when one is wanted, and
  `harness/run_parallel.py` boots its own.
- If the work needs a host the environment blocks, ask for it with the
  session's own tools; the owner approves a card. On Nov 23 the owner's
  own edit to the settings had not reached the environment, and adding the
  host from the session did.
- No secrets are saved on the environment, and none are needed.

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

## Found after this was written (the owner on a desk, Nov 22 evening and Nov 23 morning)

### 1. With Text open, a click anywhere on the drawing moves the words there

"The text on a desktop moves wherever you click. so if I click at the
bottom, it moves there. if I click in upper right corner, it moves there".

- That is today's design: `place()` says "with the drawer up, moves the
  words there".
- It is very likely bug 2's mechanism on a phone.
- THE OWNER'S TO DECIDE, asked and not yet answered: should a click move
  the words, or only a drag?
- Cal's pick: once the words are down, only a drag moves them (their box
  says "Drag to move"), and a click elsewhere leaves them where they are.
- Settle this before mending bug 2: the answer may be the mend.

### 2. How it works' row of examples cannot be scrolled with a mouse

This is the Pad's How it works sheet ("What would you like to do?"),
opened from the site's How it works page, on a desk.

- The row of example cards (Draw, Add music, Post, and more past the right
  edge) scrolls sideways with a finger.
- A mouse has no way to it: no scrollbar, no arrows.
- The answer changes how the row looks on a desk (arrows on a device that
  hovers, a scrollbar that shows, or a row that wraps), so mock it first.
- Check Flip's sheet too.

### 3. No way back from How it works to where you were

- Choosing Pad on the site's How it works page opens the Pad with its own
  How it works over it.
- Closing How it works leaves you in the Pad, though you came from the
  site's page.
- The same happens with Flip's How it works from the main menu.

By "The way back" (`DECISIONS.md`) and "Never stranded"
(`WORKING-AGREEMENTS.md`), closing it should bring you back where you
were. It is a bug, so it needs no yes. Start at padOver's help() in
`social/static/social.js`, which opens the editor and asks for its help,
and at how the editor's help sheet closes.

## Also on Tuesday's list: a walk of Another App (the owner's ask, Nov 23)

OPTIONAL (the owner, Nov 24): research for later, not a dependency of the
architecture work. It stays available; do it when the owner asks, or when
there is room.

The owner: "can you add that to the list of things to do when we start a
new session tomorrow night?"

The owner asked that the other site be called Another App here, never by
its name (Nov 24): this repository is public. Its address is the allowed
host in the environment section above.

The ask is a walk of Another App to see how it works and all of its
functions, then a write-up of what it means for Blooby. That means how
it behaves, never its look: the same rule as Bluesky's app in
`WORKING-AGREEMENTS.md`. It is a drawing community built around remixing
each other's drawings.

What a first look found (Nov 23: three public pages, signed out, in the
browser here):

- THE FEED: My Feed, Latest, Trending and Challenges, as a grid or a
  list. Each drawing's card shows its counts, Save for later, and Remix.
  Remix is an answer drawn on someone else's drawing: the nearest thing to
  our Draw back.
- THE DRAWING APP:
  - brushes: round, square, halftone, soft airbrush, blend;
  - an eraser, a fill bucket, text, and a freehand lasso;
  - layers, a colour picker, zoom and pan;
  - buttons to download the canvas and to post it.
- THE REST: profiles, challenges, a forum, help, guidelines and updates.
  The sitemap lists about 1,300 public pages, mostly drawings, some of
  them deleted.

How to walk it:

- As a visitor, in the browser here, politely: a modest number of pages.
- Skip every path its robots file asks crawlers to skip: its API,
  settings, moderation, its challenge pages and a few more.
- Posting, remixing, commenting, following, bookmarks and notifications
  need an account. Ask the owner before signing up or posting anything
  there: it puts things on someone else's site.
- Look first at whether a drawing replays its strokes, and at how Remix
  works.

The write-up is for the owner: what each function does, how it feels, and
which ideas could serve Blooby as the place where people talk in drawings.

## Also on Tuesday's list: a question to mock first, draw-backs as layers (the owner, Nov 23)

The owner asked whether a draw-back should be a separate layer. Today it
is its own post, the answerer's, holding one joined COPY of her drawing
with his (`social/drawback.py`): hers first, squeezed to about three
seconds, then his.

Cal's view, given to the owner and not yet decided: keep the separate
post, but store the drawing as two layers. That means her drawing BY
REFERENCE, with his strokes over it.

- What it would give:
  - Her deleting her drawing takes it out of every draw-back. Today a
    copy lives on in his post.
  - Recolours become possible (they are refused now because of the
    copy).
  - A viewer could choose her part faint, full or hidden, and watch it at
    its own speed.
- What it costs:
  - The player plays two layers, within the in-post player's byte budget
    (`harness/verify_inline.py`).
  - Existing draw-backs are converted, or left as they are.
  - A choice of what a draw-back shows once her drawing is gone. Cal's
    guess: his strokes alone, with a quiet "the original was removed".

THE OWNER ASKED FOR A MOCK FIRST. Build nothing until they say yes to it.

NOW (Nov 24): the owner's final recommendations make this the core
architecture investment, and point the same way as Cal's view. Each
draw-back becomes an independently authored contribution that references
a stable version of its parent, composed together for viewing. Its brief,
`docs/research/blooby-final-recommendations/LAYERS_AND_DRAWBACK_ARCHITECTURE.md`,
lists the owner decisions that come first: deletion, versions,
permissions, rights, recolour, media, depth, and old draw-backs. It also
gives a prototype order, starting with one original and one answer. Cal's
guess above about a removed original is one option among those, not a
decision. The owner's condition stands: a mock first, and nothing built
without a yes.

The owner, the same day: this foundation keeps each artist's
contribution, ownership identity and replay history separate. It is
designed for reuse in both Pad and Flip from the start, without waiting
for either editor's layer interface. Page-for-page Flip Draw back may be
an early consumer of it.

## Also on Tuesday's list: the Draw back banner covers the drawing (the owner, Nov 23, on a desk)

"the drawing back on someone's drawing toast never goes away when drawing
back so you can't draw there (under it)."

While drawing back, the pill "Drawing back on Ana's drawing · Theirs"
stays over the top middle of the canvas for the whole drawing. On their
own drawing it reads "Drawing back on your own drawing". Nothing can be
drawn under it.

`WORKING-AGREEMENTS.md`, "The canvas is the hero": something that covers
the canvas moves or goes once its job is done. That makes this a bug.

The catch: the pill holds the Theirs switch (faint, full, hidden), which
must stay reachable. Where the switch goes is a small design choice, so
mock it first with two or three options and say what it does to Flip.
Cal's pick to offer: the pill glides away once the pen first touches, and
Theirs lives in a small control by the tools that brings it back.

## Also on Tuesday's list: repost of your own drawing, and Pin this post (the owner, Nov 23)

### Repost does not seem to repost your own drawing

"repost does not seem to repost (my own drawing), but quote post does."

- First find whether this is a rule or a bug.
- Some sites refuse a repost of your own post, or only light the button.
  Bluesky allows it, and it shows in your followers' feeds.
- If our code refuses it on purpose, say so to the owner and ask whether
  it should change. If it fails, it is a bug: mend it, and check it the
  way the repost suites do (`harness/verify_socialreposts.py`).

### An idea to weigh: "Pin this post" in a post's ⋯ menu

The owner's idea: your chosen post stays at the top of your profile.

- Ask first how it serves talking in drawings (the roots). Cal's reading:
  it lets a person lead with the drawing that says who they are, which
  fits.
- It is a new feature, so mock it first. Show where Pin sits in the ⋯
  menu, how the pinned post is marked on the profile, and that only one
  post is pinned at a time.
- Build nothing until the owner says yes.

## Also on Tuesday's list: the owner's final recommendations (Nov 24), the one source

The owner gave a final package that combines and supersedes every earlier
review, and asked that the suggestions here not contradict each other:
`docs/research/blooby-final-recommendations/`. Two earlier reviews were
kept here on Nov 23 and 24; they are now retired (see the end of this
entry).

The package is an outside synthesis. Its author checked it against an
uploaded copy of this repository at v330, but only by reading files: no
app run, no tests, no live site. Read it as advice, not instructions; it
says so itself.

Read it in this order:

1. `README_START_HERE.md`.
2. `FINAL_RECOMMENDATION.md`: the one canonical recommendation.
3. `LAYERS_AND_DRAWBACK_ARCHITECTURE.md`: a design brief, not a schema.
4. `DELIVERY_AND_ACCEPTANCE.md`: proposed stages and checks.
5. `RECONCILIATION_FOR_DEVELOPER.md` and `CURRENT_REPO_AUDIT.md`: how it
   fits this repository.

WHAT IT SETTLES (the precedence, Nov 24):

- No conventional instant Fill in Pad; Fill stays in Flip. This is the
  owner's call, given with the refined review on Nov 24, and it stands.
- The order:
  1. Fix the reported bugs first. Reproduce each on current main and a
     real device before calling it open or closed.
  2. Alongside the fixes, refine the Watch, Draw back, Explore journey.
  3. Then independently authored Draw back contributions with their
     lineage. This is the core architecture investment: owner-backed
     direction, MOCK FIRST, and the owner's decisions before any schema.
  4. Then a simple family view: a drawing's parent and its direct
     responses.
  5. Then Pad editing layers, two of them (Rough and Ink).
  6. Flip layers come later.
- Pad already has rectangular, stroke-group selection. A lasso is a later
  refinement, not a gap.
- The existing "Stroke layers" setting
  (`skribl/static/lib/strokelayers.js`) is a compositing setting, not
  editing layers. Don't confuse the names.
- Improve the existing home page, social pieces and help; don't rebuild
  them.
- Deferred, or not goals:
  - more brushes, or matching another app's painting tools;
  - a full family-tree graph;
  - a recommendation feed;
  - direct messages;
  - competitive rankings.

STILL THE OWNER'S TO DECIDE, before any of the contribution work is built
(the package's own open list):

- versions of published contributions;
- what happens to responses when an original is deleted or moderated;
- permissions and creator rights;
- recolouring your own strokes, as against the source's;
- photos, music and size limits;
- how deep a chain can go;
- old draw-backs, which stay as they are by default;
- whether hidden layers show in a public replay;
- the exact layer design.

WHERE IT TOUCHES THIS LIST: the owner settled it on Nov 24. The record
is `DECISIONS.md`, "The owner's clarifications to the final
recommendations".

- The contribution architecture is foundational, and is designed for
  reuse in both Pad and Flip without first needing either editor's
  layer interface.
- Flip Draw back ("Flip, page for page", below) and Flip editing layers
  are separate features. Evaluate the Flip Draw back as a possible early
  consumer of the contribution architecture; its dependencies set its
  place, not the order of editor-layer work.
- "Messages as drawn letters" (below) are not the conventional direct
  messages the package defers. They stay on the owner's list. How they're
  built and delivered, their privacy and their priority are separate
  decisions.
- The walk of Another App (above) stays optional: research for later, not
  a dependency.
- Bugs and reliability first; the contribution architecture is mocked,
  reviewed and approved before any schema change.
- Under all of it: the package's sequence never delays a feature the
  owner approved on its own. Any such delay is discussed first, in terms
  of its real dependencies.

WHAT WAS RETIRED (Nov 24), and where each point now lives. Section numbers
are `FINAL_RECOMMENDATION.md`'s.

- `docs/research/blooby-vs-another-app/`, the Nov 23 comparison:
  - its Fill in Pad is withdrawn (sections 3 and 11);
  - its "layers first" is reordered (sections 2 and 7);
  - "bring Select to Pad" is corrected, since Pad already has it
    (section 3);
  - its family-tree idea is staged (section 6);
  - its "don't merge Pad and Flip" stands (section 1).
- `docs/research/blooby-skribl-refined-review/`, the Nov 24 refined plan
  with the owner's Fill clarification:
  - its Release A is section 4;
  - Draw back contributions are section 6, with the architecture brief;
  - Pad editing layers now come after Draw back (section 7);
  - the Fill clarification is section 3, and the owner's decision stands;
  - replay chapters, a share teaser, prompts and a Gallery "Draw back
    ready" filter are sections 5 and 8, after the core loop.

Both are still in git history.

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

THE OWNER, Nov 24 (`DECISIONS.md`, "The owner's clarifications to the
final recommendations"):

- Item 1 is placed by its own dependencies. Evaluate it as a possible
  early consumer of the Draw back contribution architecture; Flip editing
  layers coming later does not delay it.
- Messages as drawn letters (item 3) stay on this list. They are not the
  conventional direct messages the package defers, and how, privacy and
  priority are separate decisions.
- The package's contribution model is also what would let a person
  recolour their own strokes in a draw-back (item 2). How it does so is
  one of its open decisions.

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
