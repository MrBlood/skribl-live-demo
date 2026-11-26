# Next session: the handoff (Nov 26, 2026, Mountain Time, written about 7 AM)

A snapshot from a session that ran from Nov 25 into the morning of Thursday,
Nov 26. It is not maintained: where things stand is the newest entries at
the bottom of `DECISIONS.md`, and how to work is `WORKING-AGREEMENTS.md`.
Read this after `START-HERE.md`; once you have, replace it with your own or
delete it, so it never goes stale here. The handoff before this one is
`git show 9d2f6e4:docs/NEXT-SESSION.md` (Nov 25: Flip's Draw back, Recolor
while drawing back, drawers beside the drawing on a desk).

## Before anything: read main's newest full runs

Every job, before believing main is green. Main was green on every job
after #1110 (finished about 9:14 PM, Nov 25): every shard on both
databases, the MP4, Firefox and WebKit. That run covers the Two Hands fixes
(#1109); #1109's own run was cancelled when #1110 merged, as main keeps
only its newest run. Not sealed since v330, which is fine
(`WORKING-AGREEMENTS.md`, "Sealing a release").

## The job: build drawn letters

The owner, Nov 26, about 6:50 AM: "I like cal's (your) choices", A for all
six (`DECISIONS.md`, "Drawn letters, mocked", and "Drawn letters: the
owner's yes, A for all six"). The mock is a design canvas,
https://claude.ai/artifact/Ax3ZcVSfR4mnDfRzUtwyfq, and the same screens on
one scrolling page for a phone,
https://claude.ai/artifact/L3YHdMNbzNUt3htDfxNyVe. Nothing is built. Set
the hourly check-in when the build starts (WORKING-AGREEMENTS, "When the
owner's usage runs out mid-work").

FOUR PULL REQUESTS, one per part:

1. THE SERVER. A letters table on the site: sender, recipient, the
   drawing (a Skribl post), the letter it was written back on, where this
   hand starts in the drawing (the mark on the player's line), when it
   was opened, and deleted from each side. The drawing is a Skribl post
   with a visibility of the site's own, "letter", that only its two people
   can read. Who can write: two people who follow each other, and nobody
   across a block. The routes: send, write back, open, take back (the
   sender, until it is opened), delete from your side, and Report. Each
   row of a new suite is shown red first.
2. WRITING ONE IN THE PAD: opened the way Draw back opens it. Its pill
   says "A letter to Ana · only she sees it" (writing back: theirs faint
   under the pen), Post says Send, and Send lands on the two of you. The
   Pad only; Flip letters are next, on the list.
3. THE PAGES. Write beside Following, only where you follow each other.
   Letters: Activity's own rows, a new one sealed (a drawn envelope, not
   the picture). The two of you: it draws itself the first time, then
   rests, with Watch again, Write back, New letter, and a ⋯ with Report,
   Block, Take back or Delete. The envelope beside the bell at a phone's
   top, with its own dot, and Letters in a desk's rail. Light and dark,
   phone and desk, with `verify_contrast`'s rules for anything new.
4. THE DOCS AND THE RECORD: `docs/SOCIAL-SITE.md`, How it works if it
   covers letters, `DECISIONS.md`.

WHAT THE CODE ALREADY GIVES (read this session; check it again):
- Skribl lets a host add a visibility state of its own and decide who
  reads it. `skribl/models.py`: `set_visibility_values` lets
  POST /api/skribls accept the state. `visible_to` asks the host's policy
  first (`set_visibility_policy`), and a state Skribl doesn't know is the
  author's alone. The built-in feed lists only "public".
- The site already installs a policy and a feed filter for blocks
  (`app.py`, `_deny_blocked` and `_hide_blocked`). The letter rule
  belongs beside them: readable by the letter's two, and by nobody across
  a block.
- Draw back's flow is the model for writing back (`docs/SOCIAL-SITE.md`
  section 20; `social/drawback.py`). A GET hands the composer
  {payload, first}, and the composer lays her drawing faint under the pen
  (`lib/composehost.js`, `lib/drawback.js`). The server then joins the
  two from her drawing as Skribl stores it (`skribl.read_payload`): hers
  first, squeezed to three seconds when longer, then his at his own pace.
- POSTING: the site makes a Skribl post server-side with
  `skribl.create_post(payload, author_id=...)` (`skribl/creation.py`),
  which takes a visibility only if `visibility_values()` has it. So the app
  must call `set_visibility_values(("letter",), app)` beside its policy. Draw
  back's own pieces are in `social/drawback.py`: `join(original, answer)`
  (the squeeze is `OVERTURE_MS`), `drawable(payload, answer=...)`,
  `same_shape`, and `hands`. `post_drawback` in `social/posts.py` is the
  model for a GET that hands the composer {payload, first, own}.
- THE COMPOSER: the Pad sits in an iframe in `_compose.html`, which
  `SocialPadOverlay` (`social/static/social.js`) runs through
  `SkriblComposeHost.create`. `underlay` hands it the drawing to draw on,
  and `lib/drawback.js` `take()` builds the pill. The Pad's own button
  says "Add to post" in the composer, and the drawing comes back by
  `skribl:compose:done` to `social/static/compose.js`, which posts to
  /social/posts and lands on the new post. Letter mode needs its own pill
  words, Send on the Pad's button, and a landing on the two of you.
- ACTIVITY AND PUSH: there is no notifications table. Activity's rows are
  worked out from comments, likes, follows and the like
  (`social/activity.py` `listing`, the bell's `dot`), and a push
  (`push.note`) sends the newest Activity row of its kind. Letters are not
  in Activity, so a push for one needs a path of its own in
  `social/push.py`.
- SAFETY: blocks are `safety.between` and `hidden_authors`; there is no
  helper for two people who follow each other (use `follows.is_following`
  both ways). Reports allow only the kinds in a CHECK on `social_reports`
  (person, post, drawing, comment), so a "letter" kind is a migration,
  and the admin queue's takedown withholds the drawing.
- THE DATABASE: the migrations' head is `b7e3f9a2c5d1` (two hands); a new
  one goes on it. `verify_socialauth` 14 holds the exact set of tables
  and indexes and runs `alembic check`, so a new table goes into both.
- WHAT WOULD LEAK, and must be guarded and checked:
  - A letter stored as a site post: Home and the Posts tab list post rows
    with no visibility filter. Keep letters in their own table.
  - Skribl's PATCH /api/skribls/<id>: it lets the author change a
    drawing's visibility, and only "withheld" is protected. Hold
    "letter" the same way, or a written-back letter, which holds the
    other person's strokes, could be made public.
  - The site's eye (`POST /social/b/<id>/gallery`, `social/posts.py`): it
    guards only posts, comments and faces.
  - Deleting an account (`accounts.delete_person`): it needs a letters step.
  - Safe already: Skribl's listings, search, Hot, the Library and the face
    picker show public (or the author's public, unlisted and private)
    only, and every page, card, poster and payload asks `visible_to`.
- A NAME ALREADY TAKEN: the Pad's `?letters=1` is "Your hand", your drawn
  alphabet (`editor_letters.js`, `letters.css`). Call the new code
  something that cannot be mistaken for it.

DECIDED WHILE PLANNING (Cal's; say so in the PR, and the owner can
overrule):
- A LETTER IS ONE WHOLE DRAWING, the way draw-backs were before two hands.
  Writing back joins theirs and yours into the new letter's drawing, so a
  sheet written back on several times still plays in order. The two of
  you show each sheet once: a letter that was written back on is inside
  the one written on it.
- OPENED when the recipient's page starts playing it, by a POST from the
  page, not on the GET, so a prefetch opens nothing.
- TAKE BACK deletes the letter and its drawing. DELETE hides it from your
  side, and once both have deleted it, it is gone.
- NEVER LISTED ANYWHERE. A letter's drawing must not show up in either
  Gallery, your Library, the Make sheet's list of your drawings, Hot, More
  from, search, or a card or poster for anyone but the two. A letter
  written back on holds the other person's strokes, so posting it would
  publish their letter. The new suite checks every one of these.
- NOT IN ACTIVITY: the envelope has its own dot.
- NO PHOTOS OR MUSIC: refused at Send with a kind word, and the Pad dims
  those tools in letter mode.

ASKED OF THE OWNER when this was handed over (their answers are in the
conversation that follows, or in `DECISIONS.md` once recorded):
1. A push notification for a new letter? Cal's pick: yes, under a switch
   of its own in Settings, on by default.
2. When you write back, how should the replay start? Draw back squeezes
   theirs to three seconds when it runs longer, then plays yours. The
   mock's Theo's-side screen showed theirs at its own pace (0:24 for
   14 seconds and 10). Cal's pick: Draw back's way, so a long letter
   doesn't make the answer wait.

## Waiting on the owner's desk and phone

- Drawers beside the drawing. One-glance tell on the owner's Windows desk
  (a mouse, the window wide): open the pen's drawer, and it comes in at the
  drawing's right while the drawing glides left; nothing scrolls. A narrow
  window still opens it below. Not tested here on WebKit, SF or Segoe UI.
- Flip's Draw back. One-glance tell for the new build: under a Flip's card,
  the pen after the heart (a Flip had none). Tap it: Flip opens over the
  composer on her pages, her page faint under the one you are on, her pages
  faint in the strip; Blank and the rest dimmed. Draw on a page or two, Add,
  Post. Not tested here on WebKit or in SF.
- Two hands, still behind the owner's switch. Plays of Both count now, and
  a quote shows both (#1109). Drawing back on a two-hands draw-back is the
  chain of up to five hands, and needs its own mock.
- Carried: Pin, and Nov 24's list (`git show 2c4ba23:docs/NEXT-SESSION.md`).

## Then, in the decided order

Watching first everywhere, once letters are built (`DECISIONS.md`, "The
owner's clarifications to the final recommendations").

## What saves time

- A row about room (what fits where) is read in CI's face before it
  merges: a fontconfig that leaves Inter out (WORKING-AGREEMENTS, "A ROW
  ABOUT WORDS FITTING"). Main's run after #1105 was red on one that fitted
  here by a few pixels; and a suite renamed is a reason to run
  `verify_helpclaims`, which names rows.
- A flake that will not show here may be the shared database, not the
  clock: CI's shards share one database across suites, so the people and
  posts other suites made are there (the @ list's race showed only with
  two people sorting before Paz Ruiz).

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
