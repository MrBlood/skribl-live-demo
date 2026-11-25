# Next session: the handoff (Nov 25, 2026, Mountain Time, written in the morning)

A snapshot from the session of Wednesday morning, Nov 25. It is not
maintained: where things stand is the newest entries at the bottom of
`DECISIONS.md`, and how to work is `WORKING-AGREEMENTS.md`. Read this after
`START-HERE.md`; once you have, replace it with your own or delete it, so
it never goes stale here.

## Before anything: read main's newest full runs

Every job, before believing main is green. Main was green on every job
after #1092 (the Nov 24 handoff). A push to main cancels the run still
going before it, so the run after this note's own merge is the one that
covers Pin (#1093) and Two Hands (#1094) too: read it whole.

Not sealed since v330. That is fine: seal only when there is a reason
(`WORKING-AGREEMENTS.md`, "Sealing a release").

## What merged on Nov 25 (each has its DECISIONS.md entry)

- #1093 Pin this post: "Pin to your page" in the ⋯ of your own posts,
  after Bookmark; one at a time; the pinned post first on your Posts tab
  with a small "Pinned" line, for anyone (the owner's "all yes", A and A).
- #1094 Draw back, two hands: the nine answers (A each) in
  `DECISIONS.md`, and the first step, behind the owner's switch.

## The owner's switch, and how to turn it on

`SKRIBL_SOCIAL_TWO_HANDS=1` in the live site's environment on Render (the
service's Environment page; saving it redeploys). Off, which is where it
is, nothing changes for anyone. On, every new draw-back is kept as two
hands; what was made while it was on stays two hands if it is turned off
again. `docs/SOCIAL-SITE.md` section 41 says what each viewer sees.

## Two hands: what is not done yet (each its own step)

- Plays of Both are not counted: Skribl counts a play only on its own
  route, and Both comes from the site's (`/social/hands/play/...`). A small
  Skribl seam to count a play a host serves would mend it.
- A quote of a two-hands draw-back shows his own picture, not both
  (`reposts.Quoted.card` builds the quote's `sk` without the hands state).
- Recolour stays off while drawing back (the fifth answer opens it for his
  own strokes only).
- A two-hands draw-back is not drawn back on (the seventh answer: one
  original and one answer first, then up to five hands).
- The views are on a post's own page; cards play Both.
- Flip page for page is meant to be the contribution model's first user.

## Waiting on the owner's picks (a mock, nothing built)

Flip Draw Back, https://claude.ai/artifact/J9hTtwTp2r1h2pA9rwvuUF (the
owner's "Start Flip's Draw back next, mock first", Nov 25): Ana's bouncing
ball (How it works' Flip) answered page for page by Theo's shadow and
bounce marks. Five choices, Cal's pick A each: pages follow hers (no adding,
moving or deleting while drawing back); it plays together, page for page;
kept as the Pad's (joined with the switch off, two hands on); the eraser off
as on the Pad; her pages faint in the page strip. Not in the first step: a
Flip with a loop, a page underneath or beat timing. Build nothing until a
plain yes.

What the mock found for the build: `lib/drawback.js` runs inside Flip as it
is (the same `.zoom-layer`, the shared styles), but its fold looks for the
Pad's `.canvas-wrap`, so Flip needs its frame (`.flip-wrap`) named to it;
Flip's own paper has to become hers (`setBg`), or her dark ink vanishes on
Flip's dark page; and her pages in the strip are Flip's `drawThumb` with
hers painted faint after it. The pictures' script is in that session's
scratch folder, gone with it; the page says how each picture was made.

The owner has a friend's mocks of ideas to show the next session ("fresh
eyes"): read them as advice, weigh each against `DECISIONS.md`, and answer
with what to take, what not, and why.

## Waiting on the owner's phone

- Pin: your own post's ⋯, "Pin to your page"; your page's Posts tab leads
  with it, "Pinned" above it; pin another and the toast says the first
  went back.
- Two hands, once the switch is on: draw back on somebody's drawing; your
  post looks as a draw-back always has; on its page the pill under the
  drawing (Both · theirs · yours). Not tested here on WebKit or in SF.
- Carried from Nov 24 (`git show 2c4ba23:docs/NEXT-SESSION.md`): Text's
  drag and letters in Make, How it works from the site's page, the folded
  Theirs button, Post it, the desk's arrows, Flip's page bar.

## Then, in the decided order

Flip page for page (Draw back's Flip twin), recolours on a draw-back,
messages as drawn letters, watching first everywhere. The precedence and
the parked list are as Nov 24's handoff said (`DECISIONS.md`, "The owner's
clarifications to the final recommendations").

## How this session worked, and what saves time

- A change to a row the ⋯ shows moves three suites' word-for-word lists
  (`verify_socialbookmarks` 1, `verify_socialmute`, `verify_socialposts`
  the ⋯ and its risky card): grep `"Copy link", "Share…"` in `harness/`
  first.
- A check that needs two settings of the same server (the switch off and
  on) runs a second server on the same SQLite file with the same
  SECRET_KEY: a sign-in on one is good on the other
  (`verify_socialdrawback` 15).
- Calibration as a script: a worktree per break (`git worktree add
  --detach`), each break asserted to apply exactly as often as it should
  before anything runs, three at a time, one part each.
- The site's own modules may import only from `skribl` itself; a new need
  is a documented seam in `skribl.__all__` with a `verify_hostseams` row
  (`line_of`).
