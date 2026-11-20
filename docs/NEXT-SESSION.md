# Next session: the handoff (Nov 19, 2026, Mountain Time: written that morning, its status lines added to through the evening and the morning after)

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
   MOCKED NOV 20 (https://claude.ai/artifact/NRZR69jirnAfhTQzroK3rr;
   `DECISIONS.md`, "Her say, mocked"), AND WAITING ON THE OWNER'S ANSWER to
   its seven choices. Nothing is built. The picks: the Gallery tab's eye on
   each tile of her own strip, beside the name; Settings' pill in a card of
   her post's ⋯, and one quiet line in the composer that opens it. Build
   hiding first, then who can draw back, once the owner has said.
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

THE BIGGER QUESTION, the owner's, ANSWERED (Nov 19, late morning): "yes to
A, go ahead with the mocks." It was a separate repository where Pad and
Flip are "totally a part of" the site (blooby.app), this one keeping them
independent for skribls.net; the answer given had three ways, and A is one
repository, the editors still able to stand alone, giving up their own
doors inside the site and using its places and words. (B was a second
repository with its own copy of the editors, about 61,000 lines and most of
the suites to keep in step for good; C was deciding now for the site alone
and taking the standalone side out.)

"ALL YES" (the owner, Nov 19, about noon) to the ten choices below, ALL TEN
BUILT, in three pieces (`DECISIONS.md`, the entries after "One
repository"): 1 and 2 (the menu inside a post, no gallery tick: #992); 3,
4, 5 and 7 to 10 (a post's page and the small ones: #993); 6 (what a
draw-back says: each hand's drawing time kept on the post, a migration, and
numbers the site hands Skribl's player: #994). Read DECISIONS and main's
runs for what has merged and how it ran.
MAIN IS GREEN ON THE FINAL TREE (run 2369, Nov 19, 6:51 PM, after #1000);
what was red on the way, and why, is in the three entries of `DECISIONS.md`
before the last. THE OWNER SAID "YES TO ALL" TO THE SEVEN (about 5:50 PM):
1 to 4 below are decided as built; 5 to 7 were a go-ahead to mocks and a
walk, now made, with the owner's own idea of that evening (the pencil's
line in colour) beside them: https://claude.ai/artifact/28w1ZWVgWNRC9YF7Cywt8t
"ALL YES" TO THOSE SIX (the owner, Nov 19, about 7:40 PM), ALL BUILT THAT
EVENING, four pull requests, each with its entry in `DECISIONS.md` (the
four after "the evening's mocks") and `docs/SOCIAL-SITE.md` section 22:
- #1002, the pencil's line: Draw back's wave in the pen-line purple, white
  on the action's fill.
- #1003, a draft's tile on your profile opens inside a post (and a posted
  draft stays in Drafts, as it did: nothing built).
- #1004, Your hand opens over the post and the drawing waits (Skribl's
  `lib/handover.js`, both editors, compose mode alone).
- #1005, How it works: the ☰'s first row, a tab in a desk's rail, and the
  site's own page `/social/how`.
THE PICTURES OF ALL OF IT AS BUILT, on the page the owner was sent:
https://claude.ai/artifact/8Am1CGcfGHTbfuuqfYiZ3x (`DECISIONS.md`, "The
six as built").
MAIN'S RUNS: green on the tree after #1003, which holds #1002 too (run
2375, done 9:30 PM; the run after #1002 alone was cancelled by the queue,
not run). RED AFTER #1004 AND AFTER #1005 (runs 2377 and 2379), ON ONE ROW,
BOTH DATABASES: verify_a11y's template census, "handOver". Your hand's
layer said it was a dialog and had no recipe there; driven with a keyboard
it let Tab out and did nothing on Escape. Mended the morning of Nov 20
(`DECISIONS.md`, "Main was red for a night"). READ THE RUN ON THE TREE
AFTER THAT FIX before believing main is green.
THE OWNER'S "ALL YES, GO" (Nov 20, about 6:50 AM): the eight calls no mock
showed are decided as built (`DECISIONS.md`, "The owner's All yes to the
eight"), and Her say is mocked (item 1 of "What is still to build", above).
A POST WITH NOTHING UNDER IT YET, MOCKED (the owner's picture of Nov 20,
"busy and disorganized"; `DECISIONS.md`, "A post with nothing under it
yet"; https://claude.ai/artifact/1aQvBWEmTpBaMReRM8nEmD): three ways, the
pick one quiet line and two buttons where two empty headings stand. WAITING
ON THE OWNER'S ANSWER; nothing built. The owner's words are in
`WORKING-AGREEMENTS.md` ("Never busy, never confusing").
THEN THE OWNER ASKED FOR THE WHOLE LOOK TO BE READ BESIDE BLUESKY ("Are we
looking good and feeling good?"), and the post's page is MOCKED CALMER
(`DECISIONS.md`, the entry of that name;
https://claude.ai/artifact/LGjra5dDzRVUC6a1eSb34t): one answer bar at the
foot, quiet labels, no "More from". It would replace the three ways above.
FIVE CHOICES WAITING; nothing built.
THE SESSION STOPPED ON THE OWNER'S USAGE LIMIT at about 10:25 PM, with
those two runs unread, and nothing moved until the owner wrote at 5:56 AM.
The owner's rule since: come back and finish without being asked
(`WORKING-AGREEMENTS.md`, "When the owner's usage runs out mid-work"; an
hourly check-in is kept while work is in progress).
DECIDED BEYOND THE MOCKS, TOLD TO THE OWNER, THEIRS TO CHANGE:
- the pencil's wave stays white on the purple "Draw back" pill that rises
  when a replay ends (purple on that purple is 1.23:1);
- a draft opened from its tile: the editor's × takes the sheet with it
  (back on your drafts, not an empty post), and only the editor is seen
  rising;
- Your hand over a face's Pad says "Your drawing is waiting for you." (no
  post to name), and it fades in place under Reduce Motion, past the
  editors' own rule that stops every transition there;
- How it works: its examples are files, not posts (Skribl's cat and Flip,
  and a draw-back made for it, a ball of yarn on the cat); they play where
  they sit, the first by itself once; a row goes where the thing is done;
  a visitor's four are plain lines with Sign in beside one line; "The Pad"
  and "Flip" open the editor INSIDE A POST with its help showing, where the
  mock said only "into the Pad's and Flip's own How it works".
NOT TESTED ANYWHERE THIS EVENING: Safari on an iPhone, SF, Segoe UI.
MAIN AFTER #993 WAS RED ON ONE ROW (verify_socialcomments 33, "the tint
fading", sqlite 4 of 6): the check's clock, not the site (`DECISIONS.md`,
"Main's red after #993"); its watch now starts when the comment arrives.
THE RUN AFTER #996 WAS RED ON TWO MORE, NEITHER THE SITE (`DECISIONS.md`,
"Main's red on the tree after #996"): a row of #994's in verify_inline
whose sample fitted this box's Inter and not CI's DejaVu Sans (shard 1 of
both databases; mended, and read in DejaVu Sans here), and a contrast read
of the Pad's "Photo" tab taken while a colour passed under it (sqlite 2;
the reading reads again when a short word's ground was on its way).
READ THE RUN ON THE TREE AFTER THOSE FIXES before believing main is green:
the runs after #994, #995 and #998 were cancelled by the queue, not run,
and the one after #999 still holds the verify_inline row.
THE PICTURES OF ALL TEN AS BUILT, on the page the owner was sent:
https://claude.ai/artifact/4BFRLCBk6cB8BMg8VZQt68 (`DECISIONS.md`, "The ten
as built", has what was read on the built pages and main's runs).
PUT TO THE OWNER, THEIRS TO ANSWER (each built the way named first):
- a drawn comment's play button is the card's own pill at its foot, saying
  the time; the mock drew a small round mark in the corner;
- the initial on cards changes their Nov 13 "never an initial"; lists of
  people (followers, who liked it, search) still show the blank circle;
- two faces sharing a row of Activity stay plain (a letter there was cut:
  the one behind by the face in front, a wide one in front by the heart);
  letters for a pair would need the faces or the badge to sit differently,
  and so a mock;
- Export's GIF row wears the infinity sign with the players' loop;
- the Text drawer's way out of a post ("Yours" with no hand yet, and "Edit
  your hand", leave the composer's frame and the drawing is gone): not
  fixed; the answer offered is that inside a post "Edit your hand" is not
  shown and "Yours" with no hand says where to make one;
- THE OWNER'S OWN QUESTION (about 4:10 PM): what comes next to make the
  site smooth with the editors, whether anything in their menu belongs in
  the site's, "somehow link to how it works?". Answered, not decided
  (`DECISIONS.md`, the newest entry): the site has no door to How it works
  today; offered, a row in the site's menu (a mock first), and a walk of
  Save and Drafts between the editors and the profile, which was not
  walked.

THE SIX MOCKS, as they were put up:
https://claude.ai/artifact/MxPYZyHAtdR4hEg9YiXAuR, ten choices with a
default each (`DECISIONS.md`, "One repository (the owner's yes to A), and
the walkthrough's six mocks", lists them and what was measured). Build only
what the owner answers, the editors' menu first:
- A DEFECT WAITS ON CHOICE 1. From a host's composer the menu's Library and
  Public gallery are plain links: the frame leaves the Pad, compose keeps
  no draft, the drawing is gone and nothing asks. A takes the two doors out
  inside a post; B keeps them behind the question the switch to the other
  editor already asks. Either mends it; show it red first (a drawing, the
  door, the canvas after).
- THE OWNER ASKED "why take out library? you're taking out the ability to
  load .skribls into the pad?" A `.skribl` file is opened and saved in Your
  drafts, never in the Library, and that stays (tried inside the composer:
  saved, opened again, every stroke back). Say so first if it comes up
  again, and never mock that door away.
- THE ADD SHEET STAYS (minus the gallery tick) and THE ROW UNDER A POST IS
  NOT TOUCHED: both were the other way in the page's draft and were changed
  by reading the record first.
- The first step needs no switch: the menu already knows it is inside a
  post, and the tick is asked for by the site's own composer.

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

The walkthrough's copy of the site, and the mocks' (five made-up people,
eleven posts), were scratch and are gone with the session; the pictures are
in the mock page.

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
