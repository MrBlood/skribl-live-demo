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
- #988: no pen where it can't be done yet, read when the post is made
  (`undrawable`); the picture a draw-back rests on is both drawings (the
  owner had seen empty boxes); its own page says it is one.
- The PR after it: the owner's "All yes" to four questions (the background
  is the original artist's; the eraser off while drawing back; your own
  drawing said so; a name that starts with a title said whole), and the
  author's background and music (below).

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
4. **Recolours**: refused with why for now (`social/drawback.py`
   drawable): they index the strokes by number and time, which the join
   would have to carry over.

Then the owner's list from Nov 18 resumes: messages as drawn letters, then
watching first everywhere (the old handoff's items 2 and 3; `docs/SOCIAL-SITE.md`
section 17 for messages).

## Decided since, and built

The owner's "All yes" (7:09 AM) to the four questions: the background is
the original artist's; the eraser off while drawing back; "Drew back on
their own drawing"; a name that starts with a title said whole.
`DECISIONS.md`, "the owner's All yes to the four questions".

Then their own idea, and their yes: "why not just only let a drawback be on
author's background and music?" A draw-back keeps her photo and her song;
the answer adds none. `DECISIONS.md`, "your own drawing, and the author's
background and music".

## The walkthrough (Nov 19, 8:40 AM): done, and waiting on the owner's answer

The owner: "can you do a run on the social site and draw, draw-back,
comments, etc and do a logic test? ... I feel like we are getting convoluted
and it's simplicity is slipping away. I would be confused using this app I
think." Done on a fresh copy of the site (five people, ten posts, comments,
draw-backs, all through the real screens), as a new member on a touch phone
(402 wide), then a desk and dark. Nothing was changed. The report, with
pictures: https://claude.ai/artifact/C3mVr5QGaZ969wHwvLp9Ek

The verdict given: the look holds up; what is slipping is the number of
ways to do one thing. What was found, biggest first:

1. Three ways to answer a drawing with a drawing: Draw back, Draw (and
   Flip) in the comment box, and Quote "with your own words, or a drawing".
   Activity then says "drew back on your drawing" or "drew something on your
   post".
2. Every comment is a small post: four buttons under each (reply, repost,
   like, more), its own page, repost, quote, bookmark, share; seven comments
   put 40 things to press in the thread. A drawn comment made on a phone
   shows 294 by 601 with its own scrubber and speed; the post's drawing is
   370 by 278.
3. Four buttons to post a drawing from the composer: Done, Add, Add to post
   (the Pad's own sheet), Post. That sheet's "Show in the Skribls gallery /
   Off, it shows in your post only" is not true on the site: with it off for
   every drawing, all nine were on the Gallery tab, signed out (the site's
   Gallery shows a post's drawing unless its maker hides it with the eye;
   the tick is Skribl's own visibility, and Skribl's own gallery was empty).
4. Draw-backs repeat the original: Home's first four cards and the Gallery's
   first four tiles were the same cat; a card does not show what was added
   until it plays; its play button says "drawn in 4 sec" (the squeezed
   replay) on a cat that took 15.
5. Pictures without words: a phone's four tabs have no names while empty
   pages say "Tap Make"; the loop button and the repost button are nearly
   the same picture, one above the other; a pen means Make, Draw back, Edit
   drawing and Quote.
6. The Pad inside a post is the whole standalone Pad: its menu has New,
   Save, Export, Library, a switch to Flip and "Public gallery".
7. Small: blank faces on cards and Activity, an initial in comments; the
   Gallery has Following and Everyone as well as New and Hot, and its search
   words are cut off at 402; Activity's empty words leave out draw-backs.

THREE BUGS, found and not fixed (the owner was told nothing would change):
- A draw-back's own page: the original artist's face (`.db-face`) is as big
  as the poster's and lies over it (48 by 48 both; on the card 22 at the
  foot of 44).
- The draw-backs strip: its first tile at 0 from the screen's edge with
  three tiles, the page's gutter 16.
- The "eraser is off" toast lands on the "Drawing back on Ana’s" pill.

THE FIRST LIST OF CHOICES WAS WRONG IN HALF, and was taken back the same
hour. The owner: "do all your suggestions make sense? double check and make
sure we're not changing anything that needs to be there." Checked against
the code and this record, about half would have undone a choice of the
owner's or removed something needed. Check the record BEFORE recommending a
removal: most of what is on the site is there by a decision.

WHAT HOLDS UP (removes nothing, undoes nothing; the report's page now says
this):
- the three bugs;
- TWO DETAILS OF THE OWNER'S "ALL YES" TO DRAW BACK THAT ARE NOT BUILT
  (`DECISIONS.md`, "Draw back, mocked", choices 2 and 3): on a post's own
  page Draw back carries its words at the row's end (the page shows the pen
  alone), and the composer's button says "Post draw-back" (it says "Post");
  and choice 4's "Ana + Theo" words, in place of "drawn in 4 sec";
- words: empty pages say "Tap Make" where a phone's bar has no names (the
  owner took them off, Nov 15); Activity's "drew something on your post"
  beside "drew back on your drawing" (a drawn reply already says "replied
  with a drawing"); Activity's empty words leave out draw-backs; the
  Gallery's search words are cut off at 402;
- a drawn comment no taller than the post's own drawing (the owner's B,
  Nov 17, is "as wide as the bubble": a phone's tall drawing was not in
  that mock), and more room between conversations than inside one;
- a mock each: another picture for loop (Skribl's player, so Pad, Flip and
  the link page with it, and the in-post player's byte budget), a quote mark
  for Quote, an initial in a blank face on cards and in Activity (a
  Gallery tile's 22px face is "never an initial", by an earlier decision).

THE OWNER'S ANSWER (Nov 19, about 9 AM): "I'd say yes to your suggestions,
but the comment row stays (maybe even add bookmark)", and "I do want to fix
the bugs and logic flaws also."
- THE COMMENT'S ROW STAYS, as chosen on Nov 17. A bookmark in it was a
  maybe: the answer given was to leave it under the dots (a phone's post row
  is full, and a comment would have a button a post does not), with a mock
  on offer. Not asked for since.
- BUILT, in the PR after #989 (`DECISIONS.md`, "The walkthrough of the
  site"): the three bugs; "Post draw-back"; "Tap the pencil", "commented
  with a drawing", draw-backs in Activity's words.
- AND MAIN'S RED AFTER #989, a real defect: the Pad said "ready" before all
  its own scripts had run, so on a slow line the drawing to lay under the
  pen was dropped and the Pad opened blank. Fixed in the same PR
  (`editor_compose.js`: ready at DOMContentLoaded), with a check that holds
  the scripts back. A timeout in section 4 of `verify_socialdrawback` seen
  under load before that fix was this, not the load.
- STILL TO MOCK, each agreed as an idea: "Draw back" in words on a post's
  own page (choice 2; it does not fit the row once the row has counts: the
  mock's post had none); a drawn comment no taller than its post's drawing,
  and more room between conversations; the "Ana + Theo" words; another
  picture for loop, a quote mark for Quote, an initial in a blank face; room
  for the Gallery's search words at 402 (the words are the owner's).

THE BIGGER QUESTION, the owner's, waiting on their answer: a separate
repository where Pad and Flip are "totally a part of" the site (blooby.app),
this one keeping them independent for skribls.net. The answer given, three
ways: A, one repository and a switch the site turns on, with which the
editors drop their own doors (Skribl's own gallery and its tick, the
Library) and use the site's places and words (recommended; its first step
would be the Add sheet's gallery tick and the Pad menu's Library and Public
gallery, mocked first); B, a second repository with its own copy of the
editors (about 61,000 lines and most of the suites, to keep in step for
good); C, deciding now for the site alone and taking the standalone side
out (closes the skribls.net door; a small job after A). THE GALLERY TICK
waits on this: the site's composer asks for it (`gallery=1` in
`_compose.html`), and with A it would stop asking.

TAKEN BACK, and why: Quote without a drawing (the only way to answer a Flip
or a post of words with a drawing in a post of your own); Flip out of the
comment box (Pad and Flip do not drift); no Add sheet (the owner's pick,
and "Viewers start at" is the author's speed, a root; Tune's Watching speed
is the preview's); names under a phone's tabs (the owner's own choice,
Nov 15); a draw-back's card with the original faint (washed-out ink on
every card: "no dinge"); one Gallery tile a drawing (the test site's ten
posts held four draw-backs; wait for the live site); a three-item Pad menu
in the composer (New, Your drafts and the Pad and Flip switch are there on
purpose; only Library and Public gallery lead out, read in the template and
not tried on screen); the Gallery without Following and Everyone (the map);
leaving "Who can draw back" for later (the artist's say over her own art:
build both parts of choice 7).

The walkthrough's copy of the site is gone (its server did not outlive the
turn); its scripts were scratch.

## Open threads

- **On SQLite with media kept in a store, a post with a photo or music
  answers "busy"** (503). Found while testing the author's background and
  music: the site's post route reads through the request's session before
  Skribl stores the post (the taken-down check, a quote's reads), and the
  store's claim commits on a connection of its own (`skribl/creation.py`,
  H3), which waits on SQLite's lock and gives up. The same post made
  through `create_post` with nothing read first is stored. Not the live
  site (it posts music), and PostgreSQL has no such lock. Not fixed:
  ending the request's read before `create_post` would likely mend it,
  but it touches every post, so it wants its own look.

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
- A post made through the site's own requests carries no picture (the
  Pad makes it), so it rests as a blank box: for a site that looks real,
  open the composer's Pad and call `loadSkribl(payload)` in its frame
  (Flip's is `window.SkriblComposeLoad`), then Add and Post, as the
  walkthrough did with the drawings under `skribl/static/help/demos/`.
- Mocks are made by driving the real site with Playwright and laying the
  option over it; the suites' fixtures (`harness/verify_socialcomments.py`'s
  head) make a site with people in a minute. Scratch files do not survive a
  new container.
