# Next session: the handoff (Nov 18, 2026, evening, Mountain Time)

A snapshot from the session that built nudges, written at the owner's ask
("Make a handoff file"). It is not maintained: where things stand is the
newest entries at the bottom of `DECISIONS.md`, and how to work is
`WORKING-AGREEMENTS.md`. Read this after `START-HERE.md`; once you have,
replace it with your own handoff or delete it, so it never goes stale here.

## Read this first: the thread, found again

At the end of the evening the owner stepped back: "We're not sure if
skribls.net want us so we're designing a platform, maybe losing our way a
little.. we have a historical philosophy and pillars and roots. A vibe. Are
we kind? Have we lost the thread? How can we build this site to be unique
and kind and integrate skribl pad/flip into this independent social site?
This needs to flow."

The answer they agreed with: a little, yes. For a week the site gained "what
any social site has", each piece done well and kind (the dot's rule, quiet
mutes, real deletion, no algorithm), but the drawing rode along instead of
leading. The rare thing is the performance, "drawings that draw themselves"
(`FUTURE.md` §1). Then the owner: "I like your recommendation. Good job
bringing it back. Let's figure out how to make this social, art
communication and art for art, but look good as a social site. It has to
work intuitively. Be powerful, simple, kind and.. this is new. Let's harness
it." The roots section of `WORKING-AGREEMENTS.md` now says it too.

## The owner's next ask, in their chosen order

1. **Draw back** (next, the first mock; the owner: "Drawback is genius"):
   answering a drawing by drawing with it. `FUTURE.md` §4, idea 7, "Skribl as a reply": "the feature that would
   make a network worth having", needing almost nothing new (the Pad's onion
   skin and backgrounds already do the work). The first sketch, for the mock
   to test against other options:
   - "Draw back" beside Reply on every drawing: the Pad opens with their
     drawing faint underneath, so you draw with them, never over them.
   - The draw-back plays theirs, then yours: one performance, two hands.
     Credited both ways ("Drawn back on Ana's").
   - Draw-backs on draw-backs make a jam that plays from the first stroke to
     the last: art for art.
   - It looks like a social site (cards, faces, the feed, Activity); the
     drawing leads, and Draw back is the one new verb to learn.
   - Kind: you add, never erase; what the first artist may do about a
     draw-back of theirs (hide it from their post?) is the owner's call.
   Its name, for the mock to show: the owner wrote it as one word,
   "Drawback", which in English also means a downside; on a button, "Draw
   back" (two words) reads as the thing you do. Show both, recommend one.
   Questions the mock will likely ask: is a draw-back a comment, a post of
   its own linked to the original, or both; how it shows in the feed and in
   Activity (and whether it nudges, as a reply does); how a jam plays; what
   Flip does (a page that stays underneath, `FUTURE.md` 6i, may be its
   twin); and the replay's own speed and "drawn in · watching at" words.
2. **Messages as drawn letters** (the map's part two, item 8,
   `docs/SOCIAL-SITE.md` section 17): the same Pad, privately, draw first
   with words welcome, a letter drawing itself when opened; kind defaults
   (no "seen", no "typing…", strangers wait in requests).
3. **Watching first, everywhere**: every drawing says "drawn in 47 min ·
   watching at 8×" and plays when looked at.

**Bluesky as a reference** (the owner asked for it): their open app,
github.com/bluesky-social/social-app, for how a social site behaves
(threads, chat requests, who may message you, moderation), never for its
look. `FUTURE.md` §3 also names a bigger door, for another day: Bluesky's
open network (AT Protocol) would let people already there see and follow
Blooby's drawings without the site running everything. Blooby must stay
able to be its own site either way.

Mock first, as always: light and dark, a touch phone (402) and a desk, "now"
beside each option, measured contrast and 44px targets, two or three options
with one recommended, the choices batched so "All yes" is a whole answer,
and a line on what it does to Pad and Flip, which it touches this time.

For messages, when they come, questions the mock will likely ask (offer,
recommend one):
- Where messages live: the phone's bar keeps four places, and Activity is
  not in it (a bell at the top of Home and Explore; the rail on a desk).
- Who may message you: everyone, people you follow, or nobody; a requests
  inbox for the rest, nothing said to the sender while it waits.
- A drawing in a message: the composer's own Draw and Flip (`compose.js`),
  and a drawing that draws itself in the thread (Pad first: "drawings that
  draw themselves").
- Nudges: a message needs an answer, so by the dot's rule it buzzes; a new
  switch in Settings' "Notifications on this phone" (`social/push.py`).
- Safety: block, mute and report reach messages; whether anybody else can
  ever read one is the owner's call, said plainly in the mock.
- Read receipts and "typing…": most sites have them; ask, with kindness in
  mind.

## What happened on Nov 18 (all merged)

- #969 the comment thread, Bluesky's way; #971 and #972 the comment you
  opened (its band, the ring round its face, the line stopping at the band).
- #970 and #973 Repeat's ring in the Play pill (main red, then the owner's A).
- #975 **nudges**, push notifications: the dot's rule (replies, comments on
  your post and mentions buzz; likes, follows and reposts wait unless a
  device switches them on), Activity's card asking once, Settings' switches,
  the number on the icon. `docs/SOCIAL-SITE.md` section 19 says it all.
- #976 a like or a repost refused while its count faded in kept its "1"
  (found from main's one red after #972; a real race, now fixed and checked).
- #977 and #978 **Send me a test nudge** in Settings, saying what the push
  service answered ("Sent, and Apple took it."), naming the device, a tap
  opening Settings.

**Proven on the owner's iPhone** (from the Home Screen app): a test nudge
went through Apple and arrived. A real reply or mention from somebody else
had not been tried yet when this was written. Your own likes never nudge you,
and likes and reposts start Off, which surprised the owner once.

## Open threads

- Main's full runs after #976, #977 and #978 were still going when this was
  written; the session before you checks them that evening and fixes any red.
  Look at the newest commits and runs on main first, in case it pushed a fix.
- Not sealed since v330 (`SKRIBL_VERSION` is still v330). That is fine: seal
  only when there is a reason.

## Things learned that will save you time

- Chromium's headless shell says no to every notification; a suite that
  needs the permission launches `channel="chromium"`, as
  `harness/verify_socialpush.py` and `harness/verify_social.py` do. In the
  other suites Settings shows the nudges card's "told no" state.
- `harness/verify_socialcomments.py` can go red on its desk Reply glide when
  run beside others and green alone: load, not a defect.
- Calibrate every new check red, then green, one part at a time; a worktree
  per broken part, three at a time, keeps the main tree free.
- `harness/run_parallel.py -j 3 <suites>` for the affected suites; it re-runs
  a measuring suite alone when it goes red beside the others. Read its red
  before believing the label: once tonight it called an intermittent what was
  a defect in a new check (fixed before the merge).
- Mocks are made by driving the real site with Playwright and laying the
  option over it; the suites' own fixtures (an invited member, a post, a
  comment) are the quickest start. Scratch files do not survive a new
  container, so nothing from tonight's mocks is waiting for you.
