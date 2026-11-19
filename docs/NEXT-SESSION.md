# Next session: the handoff (Nov 19, 2026, morning, Mountain Time)

A snapshot from the session that built Draw back, written as its last step.
It is not maintained: where things stand is the newest entries at the bottom
of `DECISIONS.md`, and how to work is `WORKING-AGREEMENTS.md`. Read this
after `START-HERE.md`; once you have, replace it with your own handoff or
delete it, so it never goes stale here.

## The thread

"Blooby is where people talk in drawings" (`WORKING-AGREEMENTS.md`, the
roots). Draw back is its one new verb: answering a drawing by drawing with
it, theirs faint under your pen, the answer playing theirs and then yours.
The owner said "All yes and completely remove open" to the mock
(https://claude.ai/artifact/Sa9HeL7MyFyRiUmRtoRc2W); `DECISIONS.md`, "Draw
back, mocked", holds the eight choices.

## What happened on Nov 19 (all merged)

- #984 Open › off every card: a tap on the card, or its time, opens it.
- #986 Draw back, step 1: the pen after the heart; the composer and the Pad
  over it, on the original's shape and paper, the original faint under the
  pen in its own colours (Theirs: faint, full, hidden); the server joins
  the two (theirs first, squeezed to about three seconds, then yours); the
  card's "Drew back on Ana’s" and her face small at the foot of his.
- #987 Draw back, step 2: Activity's "Theo drew back on your drawing", the
  dot and the nudge (Replies); her post's strip of draw-backs; "Watch again"
  and Draw back rising when a replay ends (Skribl's player says
  `skribl:ended`).
- The PR after it: no pen where it can't be done yet (a photo, music,
  recolours), read when the post is made (`undrawable`); and the picture a
  draw-back rests on is both drawings (the owner had seen empty boxes).

`docs/SOCIAL-SITE.md` section 20 says what is built. The code: the join in
`social/drawback.py`; the route, the posting and the counts in
`social/posts.py`; the underlay in Skribl's `skribl/static/lib/drawback.js`,
handed over by `skribl/static/lib/composehost.js`; Activity's rows in
`social/activity.py`. `harness/verify_socialdrawback.py` holds it, and its
section 4 drives the whole way in a browser: the quickest look at it.

## What is still to build, in the decided order

1. **Her say** (choice 7, approved): she may hide a draw-back from her post
   (it stays on its maker's page; nothing deleted, nobody told), and each
   post has "Who can draw back: Everyone · People I follow · Nobody",
   starting at Everyone. WHERE THE CONTROLS SIT was never mocked: mock that
   first (her post's ⋯ is the likely home of the first; the second may want
   a place on the composer or the post's ⋯).
2. **The words** (choice 4, approved): the line under a draw-back says "Ana
   + Theo · drawn in 15 sec + 9 sec · watching at 1×", the card's play
   button "Ana + Theo · 24 sec", a jam "Ana + Theo + Mira", then "Ana + 4
   others". The line is Skribl's (`skribl/static/lib/replayline.js`), which
   knows no names: the site would hand it the hands (names and each one's
   drawing time, kept when the draw-back is made: the joined drawing
   squeezes the original, so its own time cannot be read back from it). The
   in-post player has a byte budget (`harness/verify_inline.py`), and the
   words at 402px with long names were never measured: mock the layout.
3. **Flip, page for page**: its own mock. The page that stays underneath
   (`FUTURE.md` 6i) is its twin.
4. **A photo, music and recolours**: refused with why for now
   (`social/drawback.py` drawable); each a step of its own.

Then the owner's list from Nov 18 resumes: messages as drawn letters, then
watching first everywhere (the old handoff's items 2 and 3; `docs/SOCIAL-SITE.md`
section 17 for messages).

## Asked, not decided

- **The eraser while drawing back.** It seems to erase only his lines
  (hers are on their own canvas), but the posted drawing is one list of
  strokes, so the replay erases hers too where he erased over them. Options
  put to the owner: the eraser off while drawing back (Undo still there), or
  his erasing kept to his own lines in the replay (a layer the replay does
  not have yet). `DECISIONS.md`, "the picture a draw-back rests on".

## Open threads

- Main's full runs after #986, #987 and the PR after them were still going
  when this was written. Look at the newest runs on main first.
- Not sealed since v330. That is fine: seal only when there is a reason.
- Not tried on the owner's iPhone: no WebKit here. The owner asked "what
  should I see?" at 6:30 AM; the tells were the row ending at ⋯ (no Open ›)
  and the pen after the heart, signed in.

## Things learned that will save you time

- The site warms its static files when it starts, so a change to
  `social/static/social.css` or `social/static/posts.js` is not served by a
  server already running. Restart it before believing what you see.
- Every Pad drawing carries a picture of its blank paper (`baseSnapshot`),
  so Skribl's `on_photo` is true for nearly every Pad drawing. It does not
  mean a photo; a photo is `frames[0].photo.data`.
- `harness/verify_seam.py` reads `skribl/describing.py` and
  `skribl/__init__.py` closely: it pins some import lines word for word and
  resolves names at the module's top, so an import inside a function is
  red there.
- `harness/verify_socialposts.py` 7 floors how many words it reads on each
  screen: taking a word off a page (Open ›) lowers a floor.
- The in-post player's byte budget rises only for a named cost the owner
  said yes to, written beside it in its own format.
- A block is held twice for anything of Skribl's (the site's own check, and
  Skribl's `visible_to` through the site's hook): to see a block's row go
  red, take both away.
- After a branch's PR merges, merge main into the branch and push; a force
  push was refused here.
- Mocks are made by driving the real site with Playwright and laying the
  option over it; the suites' fixtures (`harness/verify_socialcomments.py`'s
  head) make a site with people in a minute. Scratch files do not survive a
  new container.
