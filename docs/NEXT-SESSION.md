# Next session: the handoff (Nov 18, 2026, evening, Mountain Time)

A snapshot from the session that built nudges, written at the owner's ask
("Make a handoff file"). It is not maintained: where things stand is the
newest entries at the bottom of `DECISIONS.md`, and how to work is
`WORKING-AGREEMENTS.md`. Read this after `START-HERE.md`; once you have,
replace it with your own handoff or delete it, so it never goes stale here.

## The owner's next ask

**Mock direct messages**, the map's part two, item 8 (`docs/SOCIAL-SITE.md`,
section 17): "one to one, a drawing as easily as words, who may message you,
and a requests inbox". The owner said yes to mocking it next (Nov 18) and to
starting it in a fresh session. Mock first, as always: light and dark, a
touch phone (402) and a desk, "now" beside each option, measured contrast
and 44px targets, two or three options with one recommended, the choices
batched so "All yes" is a whole answer, and a line on what it does to Pad and
Flip.

Questions the mock will likely need to ask (offer, recommend one):
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
