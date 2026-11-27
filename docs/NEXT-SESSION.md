# Next session: the handoff (Nov 26, 2026, Mountain Time, written about 7:15 PM)

A snapshot from the session that, after drawn letters in the morning, built
the day's tile and drawer changes. It is not maintained: where things stand
is the newest entries at the bottom of `DECISIONS.md`, and how to work is
`WORKING-AGREEMENTS.md`. Read this after `START-HERE.md`; once you have,
replace it with your own or delete it. The handoff before this one (drawn
letters, and what waited on the owner that morning) is
`git show 4749eb0:docs/NEXT-SESSION.md`; its open items stand unless a newer
`DECISIONS.md` entry says otherwise.

## Before anything: read main's newest full run

Every job. Main was green after #1122 (the drawer's tab), Nov 26, 5:31 PM,
and the main watch closed #1123 (main red after #1120). Not sealed since
v330, which is fine.

## What was built after the letters (newest last; each has its entry)

- ENAMEL TILES, B (#1117): the Gallery's tiles white and obsidian, a
  friend's colours, with their lavender edge. Bento tiles were mocked after
  it and the owner kept these (#1118, the record).
- THE TILE ANSWERS A MOUSE (#1119): on a desk, the tile under the mouse
  takes the site's hover line.
- ROOM FOR THE DRAWER (#1120): a drawing too wide to sit beside a drawer
  gets a little smaller (a quarter at most), Flip's page strip runs under
  the drawer, and Make's editor fills the window on a desk.
- CRISP TILE EDGE (#1121): the tiles' edge in whole screen pixels at every
  density (Windows' 125% and 150% smeared it), and in dark no line of light.
- THE DRAWER'S TAB (#1122): a tab on the drawer beside the drawing closes
  it; a drawer closed there slides away instead of vanishing; How it works
  says so. With it, the fix for main red after #1120.
- A DRAWN LETTER on the live site, from Pip (@pip_test) to the owner, at the
  owner's ask, to feel getting one: their own cat (the How it works line
  drawing) waving, with "hi!" by the Text tool. Sent through the site as a
  person sends one (the pattern is `harness/tools/demo_people.py`'s: a
  sign-in link from the owner, a passkey of Pip's own); the link is spent.

## Parked, not a list to work through

The owner, of these three, as the session closed: "I'm not sure any of those
things on the todo list need to be dealt with immediately, if at all." So
don't lead with them or offer them; they are here only so that, if the
owner raises one, its history is at hand.

- THE DARK GALLERY CARDS. The owner, Nov 26 evening: "The dark theme gallery
  cards look weird. Not right", then "We'll leave gallery cards for now".
  Nothing was broken on the live site (Windows 150% and a phone, beside how
  they looked that morning and after Enamel). Two suspects, put to the
  owner and not answered: two frames round each drawing (the tile's faint
  edge, then the drawing's own brighter line just inside it), and three
  blacks (the page's blue-black, the tile's purple obsidian, a dark
  drawing's own canvas). If the owner raises it: ask which, and mock
  before changing anything.
- ESCAPE closing a drawer beside the drawing: offered, not answered.
- TOGGLES AND CARDS (the owner's "Do we have any consistence in our toggles
  and cards? Backgrounds? Borders?", with eight screenshots): answered with
  a census; mocks offered for the composer's pills (white on the lilac
  paper, as the Pad's controls are) and the corners (20 against 16), not
  answered.

## What saves time

- A local rehearsal of anything a signed-in person does on the site wants
  `localhost`, not 127.0.0.1 (a passkey cannot live on an address), and for
  letters `SKRIBL_CSRF_PROTECT=1` on the server: `harness/bootstrap.sh`'s
  servers run with it off, and with it off Skribl's player reads as nobody,
  so a letter's drawing says it isn't there anymore.
- `verify_recolor`'s 320px rows ("the bar's words ... two lines at most")
  are red in this box's Inter on main as it stands, three lines, and green
  with Inter left out, as CI draws the editors: not a CI red. Whether SF at
  320px wraps like Inter is not tested here.
- A suite that put an editor away with a click beside its card (Make,
  Draw in a comment's box) needed its × once the editor filled the window
  on a desk: two did (`verify_socialprofile` 20, `verify_socialcomments` 31).
  Look for a third before changing an overlay's size again.
