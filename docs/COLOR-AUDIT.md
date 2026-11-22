# The colour crisp audit (Nov 21, 2026)

The owner, the morning of Nov 21, after "Yes to all" to that day's eight
choices: "Once you finish up, I would like to do a color cris[p] audit", with
a written specification of what to measure. This is what was measured, how,
what it found, and what it put to the owner.

**NOTHING IN IT IS BUILT.** It found five things to fix and eleven choices
that are the owner's. This file is the audit as it was put to them, true as
written and not maintained after; what has been answered and built since is
in `DECISIONS.md` (the entries from "The colour crisp audit" down).

- **The report the owner was sent**, with the pictures and every table: the
  artifact "Colour Crisp Audit",
  https://claude.ai/artifact/Jqzoat7mwLv78eXVAkg8yc
- **The table the audit required** (every colour token, light and dark, as
  HEX or sRGB and as OKLCH, with its usage): `docs/COLOR-TOKENS.md`, made by
  `harness/tools/coloraudit.py`.
- **What was read**: main after that day's two builds (#1035 the editors,
  #1036 the site), served from a scratch copy with five made-up people and
  their drawings, in Chromium: a touch phone (402 by 874, at 3x) and a desk,
  light and dark.

## The answer in short

It is in good shape, and the day's builds made it crisper. Words can be read
everywhere that was looked at, the keyboard's ring shows almost everywhere,
and light and dark keep the same order of depth. What is left is small.

| | |
|---|---|
| Words read against what is painted behind them | 2,552, on 150 screens |
| Under the line, on those screens | 1 (a search hint, in dark) |
| Hints in text boxes under the line, every box opened | 6, in five places; none on the site |
| Keyboard stops that show a clear 2px ring | 374 of 400 |
| Colour tokens tabled, both themes | 148 (the site 53, the editors 95) |
| A thin line | 1 sharp pixel at 1x, 2x and 3x (in Chromium); two soft ones in between |
| A chosen option's tile against what is beside it | 1.2 to 1.4 to 1 |

## What was asked

The owner's specification, by its own part numbers: 1.6 perceptual design,
light mixing, rendering and accessibility kept apart; 1.7 gamut; 1.8
perceptual brightness against luminance; 1.9 contrast polarity and how dark
behaves; 1.10 colour difference as a diagnostic; 1A display and compositing;
2A physically coherent elevation; 3A the token system; 3B semantic
invariants; 4A accessibility (WCAG 2.2 AA: 4.5 to 1 for words, 3 to 1 for
large ones and for marks, focus visible and not obscured; 2.4.13 as an aim);
4B what the browser and the system paint; 4C forced colours and people's
settings; 7A how the CSS writes colour; 8A pixels; 8B checks that run by
themselves; 8C a picture matrix. And a required deliverable: one table,
`| Token | Light HEX/sRGB | Light OKLCH | Dark HEX/sRGB | Dark OKLCH | Usage |`,
wide-gamut tokens listed apart, contrast always as a pair of ink and ground.

FOUR OF ITS RULES WERE HELD THROUGHOUT, in its own words, and anything
built from this audit holds them too:
- "Never infer WCAG compliance from OKLCH L values alone." Contrast is
  WCAG's own sum on sRGB, as painted.
- "Provide contrast results as foreground/background pairs rather than
  treating contrast ratio as an intrinsic property of one token."
- "Do not use Delta E as an accessibility metric." Here it is Delta E OK,
  the distance in Oklab: how alike two colours look, and nothing more.
- "Never evaluate a translucent token in isolation." A see-through colour
  has no contrast until it has landed on a ground.

AN AUDIT MEASURES. The specification is written as rules for a colour
system and speaks once of "this refactor"; the owner called it an audit,
and a design change waits for a plain yes. So nothing was changed, and
everything it would change is put as a fix or a choice. That is Cal's
reading and the owner's to overrule.

## How it was read

Each of these was a scratch script and went with the session, except the
token table's. They are described closely enough to be made again; what each
choice needs when it is built is a check of its own, shown red first.

- **Words (4A).** Each screen is photographed twice, the second time with
  every word made see-through. A word's ink is its computed colour times its
  own alpha and its ancestors' opacity; its ground is what is really painted
  in its own box (the middle of nine points, the worst of the nine kept as
  its edge). Glass, tints, the page's glow and shadows are all in that
  photograph. A word is one of: seen, see-through on purpose, not painted,
  covered. It is called low only when the sum and the painted reading
  agree. SHOWN TO WORK FIRST: a page with a too-faint name, see-through
  words and a faded card; it called each, and none as built. (The first
  version called thirteen things low that were not: labels waiting at
  opacity 0, a word under its own fill, the inside of a closed fold, a
  point on a rounded corner. A reader that has not been shown both is not
  to be believed.)
- **Marks (4A, non-text).** A field's edge and an icon standing alone, each
  against the pixel beside it, off the paint.
- **Keyboard focus (4A).** Tab through each screen, on a desk. At each
  stop, one picture focused and one not: the pixels that changed are the
  indicator. Kept: its area against a 2px line around the control, the
  share of its pixels that stand 3 to 1 from the same pixel unfocused, and
  whether a fixed bar covers the stop. AND AFTERWARDS A PHONE'S LAYOUT,
  walked with Tab the same way: what is painted on top of each stop at
  nine points of it, itself or something fixed over it, which is named.
- **Chosen states (4A, 8C).** Every element that says it is chosen
  (`aria-pressed`, `aria-current`, `aria-selected`, `aria-checked`) beside
  a sibling of its own kind that is not: the fill painted inside each with
  words and icons made see-through, the two inks as painted, and what
  differs that is not colour (weight, an underline, a ring, the icon's
  shape, a drawn mark). THEN LOOKED AT: the reader missed the squiggle
  under a current tab and a filled icon, and took an invisible hit area
  for a drawn mark; and a tray forced open on the Pad, where a phone never
  shows it, drew a tile with no icon. The pictures are what is believed.
- **Forced colours and "more contrast" (4C).** Chromium's own emulation of
  each, light and dark. It is not a real Windows high-contrast theme.
- **Thin lines (8A).** The same screens at seven densities (1, 1.25, 1.5,
  1.75, 2, 2.625 and 3 screen pixels to a page pixel), light and dark: how
  many screen pixels each line takes across its width, and whether they are
  the full colour or two part ones.
- **Depth (2A).** Every shadow the browser computed, on every element of
  every state of the Pad and Flip (85 states on a phone in light) and of
  the site, sorted into rings, lines, close shadows and soft ones (a blur
  over 2.5px).
- **Tokens (3A and the deliverable).** `harness/tools/coloraudit.py`: every
  custom property on the root, as the page resolves it with each theme
  stamped, mixes worked out by the browser.
- **The colour science (1.6 to 1.10).** OKLCH and Delta E OK worked out for
  every token (the table carries both), and each `color-mix()` done again
  in Oklab beside the sRGB one the sheets ask for.

## What it found, part by part

**Words (4A).** The site: 2,048 words on 110 screens, 1,997 on show, the
rest hidden on purpose. NONE UNDER THE LINE. The tightest in light is the
grey line under a drawing ("Drawn in … watching at"), `#6a6c71` on `#f6f8fa`,
4.91; in dark, white on the purple button `#6d4cf0`, 5.33. The Pad, Flip and
Skribl's own pages: 504 words on 40 screens, ONE UNDER THE LINE (fix A).
Two desk scenes of the editors' menu were not reached and are not counted:
a desk has no ☰, its rail is the menu.

THOSE FORTY SCREENS WERE TEN SCENES, AND NOT EVERY SHEET, and the report
first said "every other box clears 6.7", which those scenes could not
know. Building fix A, every text box's hint (its placeholder) was read on
every page of Skribl's and of the site, then each low one opened as a
person opens it and read off the paint: the hint's own pixels are the ones
that change when it is made see-through. FIVE MORE ARE UNDER THE LINE, all
on Skribl's own pages and the Pad's sheets; the site's three hints read
6.7 to 9.7. No suite reads a hint: `verify_contrast` makes them
see-through to photograph a sheet and reads the words that are left.

**Marks and focus (4A).** A field's edge: Edit profile 3.26 in light, 3.77
in dark; the site's Gallery search 3.10 and 4.13. Two boxes have no edge on
purpose (Make's words box on the calm sheet, the Pad's title). An icon alone:
the lowest that is not the wordmark is the player's Repeat and Full screen
at 4.94 in light; in dark nothing is under 6.7. Keyboard focus: 400 stops on
24 walks (twelve screens of a desk, light and dark); 374 paint the same
indicator everywhere, a 2px ring in the focus colour set 2px off, an
outline and never a shadow or a glow alone (the site `#6d4cf0` in light,
`#c1b2ff` in dark; the editors and the player `#7c5cff`), typically 94% of
its pixels 3 to 1 from the same pixel unfocused. THE 26 THAT PAINT NOTHING:
24 are the in-post player's four hidden controls (fix B); 2 are Make's
words box, which shows its typing cursor and nothing more (left: a caret
is a field's indicator, and the sheet is calm on purpose). No stop is
covered by a bar on a desk. AT A PHONE'S WIDTH SOME ARE (fix E): that
layout was walked with a keyboard after the report was first sent. On a
post's page five stops in a row sat wholly under the bottom bar (a
comment's time, Reply, Repost, Like, its dots) and six more mostly under
the answer bar; in Settings, See reports and both Sign out buttons; none
on Home, the Gallery, Edit profile, Activity, the Pad or Flip. With forced
colours on, 394 of 418 keep a ring in the system's colour. Switched off:
Post with nothing to post reads 9 to 10; Undo and Redo are choice 7.

**Chosen states (4A, 8C).** ONE IDIOM EVERYWHERE, AND IT IS FAINT. A
chosen thing wears a lilac tile behind it and violet words. Off the paint,
the tile against what is beside it, light and dark: the one pill (Following
| Everyone, New | Hot, Light | System | Dark, Who can draw back; Tune's
choices, Skribl's Gallery and Library) 1.28 and 1.25; the rules' three
tabs 1.2 and 1.4, the same ink on all three; the chosen tool in the Pad's
and Flip's row 1.32 and 1.26, in Flip's tray 1.31 and 1.27. The two inks
differ in hue more than in lightness (1.0 to 1.6 to 1 between them), and
the words are one weight on purpose. WHERE THE SQUIGGLE IS, IT IS CLEAR: a
phone's bar and a desk's rail mark this page with a filled icon and the
squiggle, a profile's tabs with the squiggle, and it reads 4.1 to 4.2 in
light and 4.8 to 5.5 in dark. The heart is a filled shape. Choice 11.

**The ladders (3B).** Lightness as the eye reads it (OKLCH L, 0 to 100).
The site in dark climbs: page 18.2, a tile 22.3, a card 25.6. The site in
light cannot climb past white: page 97.8, a tile 95.4, a card 100, and the
edge does the telling, which is why the edges matter so much. ONE STEP IS
OUT OF ORDER ON PURPOSE: in dark a sheet's paper (20.7) is darker than a
card (25.6) though a sheet floats above everything. The sheet is a quiet
paper and its rows are the cards; it never sits beside a card of the page,
because the page behind it is dimmed. Left.

**Depth (2A).** The model the tokens already describe: light from above. A
thing on the page has its edge and one line of shade under it (1px, no
blur); a thing in a card its edge alone; a thing that floats one short,
close shadow pulled in under its foot. In dark, where a shadow cannot be
seen on a dark page, the same heights are a line of light inside the top
edge. The site writes no soft shadow of its own and its suite holds the
count at rest at none. THE EDITORS' SHEET STILL DECLARES 51 SOFT SHADOWS;
many are old lines the crisp rules further down override, and about a dozen
kinds are still painted (choice 2). Four of them fall UP the screen (the
sheets that rise from the bottom). Skribl's own Gallery and Library cards
are the last place wearing the old look (choice 3). LIGHT ON AN EDGE: in
dark a card's line of white inside its top is 7% and a float's 8%, two
heights and two strengths, plain white and not mixed from the surface
under it (no cast can be seen on these cards; left). The one place with
light above and shade below is the action's fill (`--fill-drop`: white at
32% inside its top, a deep violet inside its foot, a 2px close shadow, the
same in both themes): the crisp build's "enamel", and the owner's "buttons
stay" of the same morning. At one pixel each it reads as an edge and not a
bevel; said here so it is not found again as a finding.

**Pixels (8A).** Every thin line is a ring one hairline wide, and the
hairline is 1, a half or a third of a page pixel by three steps of density
(`--hair`). So it is ONE SHARP PIXEL AT 1x, 2x AND 3x (in Chromium: the
owner's iPhone is 3x and is drawn by WebKit, which is not here), and two
soft ones between the steps: a Windows laptop at 125%, 150% or 175%, many
Android phones (choice 1). Where the fix does not help, the box itself sits a
fraction of a pixel off the screen's grid (Edit profile's field at every
in-between density, most things at 2.625x), which no stylesheet can mend.
Also: one shadow in each sheet asks for half a pixel on its own; and a
pop's pointer is a square turned 45 degrees, so its edge is a diagonal.

**See-through colours and gradients (1A).** Thirteen of the site's tokens
are see-through, fourteen of the editors'. They are thin lines, washes and
grips, where changing with the ground is the point; the ones that carry
structure were made solid already (a card's edge is mixed to one colour,
a tile and the second button are flat). One that is not: a Gallery tile's
line (`--card-line`) reads 1.53 on a light tile and 1.60 on a dark one;
left. The site writes seven gradients: the page's glow (twice, a phone's
and a desk's), the opening splash's four, and the mask a face is cut with.
The glow is the one on every page at rest (choice 9): the page is
`#f6f8fa`, under the glow's brightest point `#ecebfa`, a tile `#eeeff8`, so
the Gallery's first row sits on a step of about 1.03 to 1 where the rows
below get 1.08. No banding: one shade a step, the longest band 12px in
light and 10px in dark. The editors write twenty-one: sliders, the colour
wheel and fades that hide an edge do a job; three are decoration (the same
page glow, the Post band, the name's Done button).

**The colour science (1.6 to 1.10, 7A).** Every colour in every sheet is a
hex or an rgb with alpha: sRGB. No OKLCH, no wide-gamut colour, so nothing
can be clipped and there is no P3 token to list. `color-mix()` is always
"in srgb" (seven times on the site, thirty-nine in the editors, two
nested); the same mixes done in Oklab move a card's edge by a Delta E OK
of 0.017 at the most, which nobody could see. Nothing in the sheets is
meant as a mix of emitted light (the opening splash's beam is one colour
fading to nothing), so nothing wants a linear-light space. The dark
accents were made the careful way, lighter and calmer rather than turned
up (the wordmark from L 60, C 0.23 to L 65, C 0.20; small violet words
from L 45 to L 80 at half the strength). Dark's words are a soft white on a page that is not
black: 16.6 to 1 where white on black would be 21. Grey words never drop
under 7.0 in dark or 5.9 in light. The violets sit between 282 and 296
degrees of hue, deep ones nearer blue and pale ones nearer pink, and read
as one family.

**The token system (3A).** Two sheets hold the colours: the site's (53
colour tokens and 4 shadows) and the editors' (95 and 7). The editors' goes
from raw steps up to roles; the site is all roles, and where a role is the
editors' own it copies the value and says so in a comment. Fifteen of the
site's 53 are exact copies. THAT COPYING IS THE WEAK SPOT: nothing holds a
copy to its original but the comment, and three have drifted (choice 6).
The dark ramp is written twice on the site and a check does hold those two
together word for word (`verify_socialsettings`), which is the pattern to
repeat. In the editors two groups of five names each mean one colour in
both themes (choice 10), and 238 colours are written straight into rules
(the site has 13). One token is read by nothing (fix D).

**The browser's own parts (4B).** Every page says which theme it is and
every built-in control follows; the theme is stamped by a script in the
head before anything is drawn, so no flash of the wrong one; a phone's
address bar takes the theme's colour on the site and in the editors;
scrollbars, the typing cursor and selected text follow the theme. There is
no dropdown, date or time picker anywhere. TWO SMALL GAPS: four hints
left to the browser's grey and two set too dim (fix A); and the Pad, Flip
and Skribl's own pages do not carry the one-line `color-scheme` hint in
the head that the site does (to add with the fixes).

**Forced colours and "more contrast" (4C).** Forced colours holds up well:
cards keep an outline, a drawing keeps its own colours, icons follow the
words, focus rings survive, and the Pad and Flip were built for it (the
chosen tool keeps a strong outline). THE CHOSEN PILL IS THE ONE THING LOST
(fix C). The site's sheet has no block for either setting; the editors'
has three for forced colours and one for more contrast (choice 5).

**The picture matrix (8C).** Every kind of control at rest, under a
pointer, with focus and pressed, at one size, light and dark: these are the
"before" pictures for anything built from this audit, and they are in the
report. Focus is the same ring everywhere. Under a pointer and under a
press the site is patchy (choice 4).

**Checks that run by themselves (8B).** Already on every merge: every word
on every editor sheet against its painted ground (`verify_contrast`) and
every word of the site the same way (`verify_socialposts`); every outline
one screen pixel at 3x; the site's soft shadows at rest held at none; no
see-through grey where a clear colour reads; the dark ramp's two copies
word for word; the Pad and Flip painted alike; every text box 16px or
more. WHAT NOTHING GUARDS: a copied colour against its original (choice
6); a new colour written straight into a rule (choice 10); a thin line at
an in-between density (choice 1); a placeholder left to the browser
(fix A).

## Five things to fix

A, B, C and E are bugs; D is tidying nobody would see. By the working
agreements a bug fix needs no OK, but the owner was told none is built and
to say if they would rather see any first.

BUILT, ALL FIVE, the evening of Nov 21 (`DECISIONS.md`, "The colour
audit's five fixes, built"): what each became, the check that holds it and
how each check was shown red. What follows is the finding as it was put.

**A. Six hints in text boxes are too faint.** The words in a box before
anything is typed. FIRST REPORTED AS ONE (the Gallery's search); the other
five were found on building it, and the report corrected.

| The hint | Where | Light | Dark | Why |
|---|---|---|---|---|
| "Untitled Skribl" | the Post sheet's title, Pad and Flip | 3.05 | 2.47 | set to the dim ink |
| "Say something about it…" | the Post sheet's caption | 3.05 | 2.47 | set to the dim ink |
| "https://…/s/abc123" | the recovery box: Pad, Flip, Library | 3.96, 4.15 | 3.78, 3.74 | the browser's grey |
| "What should we know?" | Skribl's Gallery, Report | 4.15 | 3.74 | the browser's grey |
| "Search titles, captions" | Skribl's Gallery, search | 4.61 | 3.45 | the browser's grey |
| "title…" | Skribl's Library, search | 4.61 | 3.45 | the browser's grey |

Each but the last was read off the paint with its box open; the Library's
search shows only to somebody with skribls of their own and is as
computed. FOUR ARE LEFT TO THE BROWSER, which in Chromium is `#757575`;
Safari's grey is another, so what the owner's iPhone shows is not known,
and setting our own ink mends it everywhere. TWO ARE THE EDITORS' DIM INK
(`--text-dim`, `.post-input::placeholder`), from before the second ink was
made the rule for every word (`DECISIONS.md`, "Two inks, sharp": 7 to 1);
Export's name, called "the same field as .post-input, deliberately" in the
stylesheet, already wears the second ink at 10 and 8.6. THE MEND: each
hint takes its page's second ink at full strength, as every hint on the
site does. (The Pad's and Flip's name field wears the dim ink too, 2.97
and 3.02; it is under the canvas at rest and on show only while the name's
panel is open.) A CRUDE READING OF THE PAINT FOOLED ITSELF ONCE HERE: "the
strongest pixel in the box" took the caption's resize grip for its hint
and called it fine. The hint's own pixels are the ones that change when
the hint is made see-through; read those.

**B. Four stops a keyboard can land on and see nothing.** A drawing that
has not been played keeps its line of controls hidden, the calm card
(`.skribl-inline-line.is-waiting` in `skribl/static/inlineplayer.css`:
no height, no opacity). Hidden to the eye, the Tab key still stops on
each: Scrub, Repeat, Full screen and the speed. They are 24 of the 26
stops that show nothing. The fix is Skribl's player's, so Pad, Flip, the
link page and the site get it together: they wait their turn for the
keyboard too. Mind the in-post player's byte budget (`verify_inline`).

**C. In forced colours the chosen pill is not marked.** Following |
Everyone, New | Hot and Light | System | Dark (`.fo-seg` and
`.theme-switch` in `social/static/social.css`; the second is also Who can
draw back and the notifications' choices) say which is chosen with a tint
behind it. Forced colours takes tints away and nothing else says which is
on: read off the picture, the chosen and the other are painted alike. A
few lines for that mode alone; nothing changes for anybody else.

**D. One colour nobody uses.** `--line-mid-2` is declared in the editors'
sheet, light and dark, and nothing reads it: not a stylesheet, a template
or a script. It rides along in `player.css`, which is on a byte budget.

**E. At a phone's width the keyboard can land under the bottom bar.** The
site's bar is fixed to the foot of the screen under 900px (65px and the
safe area), and a post's page stands its answer bar on it (60px more).
The page's last line clears both (`.main`'s padding), but a control that
Tab scrolls into view is put at the very foot of the screen, under them:
focused, ringed and unseen. WCAG 2.2's 2.4.11, Focus Not Obscured, asks
that a focused control not be entirely hidden. Who meets it: an iPad in a
narrow split with its keyboard, Switch Control or Full Keyboard Access on
an iPhone, any browser window under 900px. The mend is one rule on the
page's own scroller (`scroll-padding-bottom`, the bars' height); it also
moves where a script's own scroll-into-view lands, so the suites that
read a comment's landing place are the ones to run. ADDED AT 4:25 PM with
choice 11.

## Eleven choices, each with Cal's pick

Put to the owner in one list, so "all yes" is a complete answer. 2, 3, 4
and 11 change how things look, so each gets a mock first (now beside after,
light and dark, a touch phone and a desk). The rest can be built straight
away, each with a check shown red first.

ANSWERED "All yes." the same afternoon. BUILT that night: 1, 5, 6, 7, 8
and the first half of 10 (`DECISIONS.md`, "The colour audit's yes,
built"). 2, 3, 4 and 11 wait for their mocks; 9 was "leave it"; 10's
second half had no pick, so it is asked again.

ANSWERED AGAIN, Nov 22, 8:31 AM, to the mocks ("Four Looks"): "All yes":
11 A, 3 A, 4 A, 2 after, and 10's second half yes (`DECISIONS.md`, "Four
Looks, the owner's 'All yes'"). Each is built in a pull request of its
own; 10's second half first (`verify_surfaces`).

1. **Thin lines on in-between screens. Pick: yes.** Add the steps of
   `--hair` between the three, so a line is one sharp pixel at 125 to 175%
   and 2.75x too. Tried: the card, the tile and the Pad's menu card go from
   two soft pixels to one at 1.25, 1.5, 1.75 and 2.75; mixed at 2.625; a
   field on a fractional pixel is not helped. Nothing changes at 1x, 2x or
   the owner's 3x. `--hair` is written in `social.css`, `styles.css` (twice),
   `gallerysection.css` and `pagemenu.css`, and `player.css` carries the
   editors' by generation. Whether the owner's Windows display is at an
   in-between scale is not known.
2. **The soft shadows still painted in the Pad and Flip. Pick: yes, a mock
   first.** One rule each: what floats over the drawing (the Add a take
   pill, a button's card, the Draw along pill, a draft row's little menu,
   Text's drag handle) gets the one short, close shadow the tray got on
   Nov 21 (`--chip-lift`), in place of its big one; a sheet (Your drafts,
   How it works, the little book) gets its edge and the dimmed page behind
   it and no shadow; a knob you drag keeps its tiny one; nothing inside a
   card casts a shadow (one video does); the green dots' glow becomes a
   clean ring; the canvas's faint inner shade and the wordmark's pressed-in
   look stay. THIS IS "LAST SOFT SHADOWS" AGAIN (`DECISIONS.md`, "The last
   soft shadows, mocked"), its nine calls and their picks withdrawn after
   the owner's "shadows are good if they add crispness, not if they are too
   big".
3. **Skribl's own Gallery and Library cards. Pick: yes, a mock first.**
   The two pages outside the site still wear a soft 18px shadow under each
   card (light: a ring and `0 6px 18px` at 9%; dark: a ring at 12% and
   `0 6px 18px` black at 35%), and in dark the faint 12% edge that was
   doubled everywhere else. They would take the same edge and one line as
   every other card. Not tiles: these are whole cards, one drawing each.
4. **A press should show, on the site as on the Pad. Pick: yes, a mock
   first.** The Pad and Flip answer a press in about forty rules (a tool
   dips: `transform: scale(0.94)`); the site in none, and it switches the
   phone's own tap flash off in fourteen places. On a desk Danger brightens
   under a pointer and the main purple button does not. Pad is the model.
5. **Answer "more contrast" on the site. Pick: yes.** With the setting on,
   not one pixel of Home, Edit profile, Make or the Gallery changes. For
   people who ask for it: firmer edges and grey words a step stronger.
   Nobody without the setting would see a difference.
6. **Three colours copied by hand that drifted. Pick: set each to the
   editors' value, and add a check that holds the copies together.** The
   thin rule between rows (`--rule` 12% and 14% on the site; the editors'
   `--menu-card-rule` 10% and 12%); the chosen pill's words in dark
   (`#d4c9ff` on the site, `#dad1ff` in the editors and Skribl's Gallery);
   the other pill's words in light (`#3f4756` against `#3b4251`). Nobody
   could see these side by side: it is drift, not a look. THE RECORD AGREES
   ON THE PILL: the site's three tokens were made as "the same values, not
   new ones" (the Gallery's), and the Gallery's own moved a step later with
   the editors' ("Just a Border, the editors") while the site's stayed. On
   the rule, which of the two moved is older than this clone's history; the
   site's line names the editors' token beside its value, and the owner's
   Nov 21 answer left the editors' rule where it is. Matching takes the
   site's rule a hair fainter: 1.21 to 1.17 from a card in light, 1.28 to
   1.23 in dark.
7. **Undo and Redo with nothing to undo. Pick: yes.** Light's `--off-ink`
   reads 2.38 to 1 on the Pad's ground where dark's reads 3.99. One step
   deeper (`#928ab8`) is 3.01: still clearly off, and you can tell what
   the button is.
8. **Stop thinning the letters on Macs. Pick: yes.** The sheets ask for
   `-webkit-font-smoothing: antialiased` on the root of each surface (the
   editors' body, the site's body, Skribl's Gallery section) and repeat it
   in three places that restate their root's type (`.pending-btn`, the
   full-screen band in `fullband.css` and its copy in `gallerysection.css`).
   It does nothing on an iPhone or on Windows; on a Mac it draws letters
   thinner than the system would, and thin light-on-dark words are where it
   hurts. NOT TESTED: there is no Mac here; this goes by what the setting
   is known to do.
9. **The glow at the top of the site's page. Pick: leave it.** It is warm,
   and a tile's edge still shows under it. The other two ways: end it above
   the first row, or take it away. The owner's to call by eye; a mock of the
   three on request.
10. **Tidy the token names. Pick: yes to the first; the second is the
    owner's.** First: `--text-soft`, `--text-soft-2`, `--text-soft-3`,
    `--text-secondary` and `--text-muted` are one grey, and `--accent`,
    `--ui-hi`, `--ui-active`, `--ui-line` and `--focus-ring` one violet;
    make four of each point at the one. No look changes. Second: a check
    that fails when a new colour is written straight into a rule (hold the
    238 and the 13 where they are; do not chase them). That one is about how
    noisy a pull request's checks are, so it is the owner's call.
11. **Telling which one is chosen. Pick: yes, the quiet way, a mock
    first.** A CHOSEN THING IS A TINT BY THE OWNER'S OWN CHOICE, TWICE: the
    one pill, chosen from four mocks (`DECISIONS.md`, "one pill,
    everywhere": "the soft tint under the choice, one label weight"), and
    "A ring only where a tint cannot show" (the owner had asked why
    anything besides a search box wears a bright ring, and the rings came
    off). Nothing here asks to undo either. The finding is narrower: the
    tint is 1.2 to 1.4 to 1 from what is beside it and the words change
    hue more than lightness. WCAG asks
    that a state not be told by colour alone (1.4.1), or else that the
    difference stand 3 to 1 (1.4.11); by a strict reading the pill does
    neither. THAT READING IS CAL'S: WCAG's own pages could not be opened
    from this box to quote, and plenty of well-known apps ship such a pill.
    THE PICK keeps the tint and adds no ring: the chosen word a step
    bolder, its width held so nothing moves (one weight was chosen partly
    because 500 beside 600 made Flip's move bar grow 3px at 360 and scroll:
    the mock is read there first). And where a tint cannot show, an edge,
    by the owner's rule: forced colours (fix C; the editors already do it)
    and "more contrast" (choice 5). Or leave it. FIRST PUT WRONGLY: the
    pick drafted was "a crisp edge round the chosen tile", which is the
    bright ring the owner had taken off; it was changed on reading the
    record, before the page was republished. Read the record before
    recommending. ADDED AT 4:25 PM, forty-five minutes after the report was
    first sent, from reading the specification again clause by clause.

PAD AND FLIP: 2, 7 and 10 are theirs and shared (one stylesheet). 1 is the
site's and theirs. 3 is Skribl's own pages. 4, 5, 6 and 9 are the site's.
8 is all three. 11 is the site's and theirs: one pill, the Pad's the
model. AGAINST THE FOUR: powerful, nothing here adds or removes a feature;
playful, a button that dips when you press it; simple, one rule for depth
kept everywhere; kind, the people who use a keyboard, forced colours or
"more contrast" get the same care as everyone else.

## Calls made in doing it

Each is Cal's reading and the owner's to overrule; the report says each.

- NOT REBUILT INTO THREE FORMAL LAYERS (raw, role, component), and not
  moved to the Design Tokens file format, as the specification describes.
  It would touch every rule in ten thousand lines for no change on screen,
  and the roles already do the job. What is worth doing is small: hold the
  copies together with a check, fold the same-colour names, and keep the
  table made rather than typed.
- NO OKLCH IN THE STYLESHEETS, and no wide-gamut purple. OKLCH was used
  where it helps, for laying tokens side by side. An iPhone could show a
  more vivid purple than `#7c5cff`; it would be one more thing to keep true
  in two places for a difference only some screens show.
- LEFT AS THEY ARE: a sheet's paper darker than a card in dark; Make's
  words box and the Pad's title with no edge; a Gallery tile's see-through
  line; the Rules page at 16.6 to 1 (bright for a long read, fine for a
  page that short); the pale "▶ 29 sec" chip on a dark drawing in dark (the
  same in both themes because the drawing under it does not change with
  the theme).

## The report was corrected twice

Sent at 3:40 PM; republished the same afternoon after the specification
was read again clause by clause against it, and once more when building
fix A showed it was six hints and not one (the count at the top and fix A
say so now). What changed: choice 11 was
added (a chosen state had not been measured) and fix E (a phone's layout
had not been walked with a keyboard); choice 1 and the numbers at
the top said a thin line is one pixel "on your iPhone", which was Chromium
at an iPhone's density and is said so now; choice 8 said "one line in each
of three stylesheets" and it is six lines in four; and Depth gained the
paragraph on light on an edge. The page says what changed.

## Not tested here

Safari on an iPhone; Segoe UI or SF (this box has neither); a Mac (so
choice 8 is not tested at all); a real Windows high-contrast theme; a
wide-gamut screen; the colours a browser paints into a box it has filled
in for you. At 1.25x to 2.625x the pictures are Chromium's, on this box:
what the owner's own Windows display does at its scale is not known. And
WCAG's own pages could not be opened from this box (its network does not
reach them), so what WCAG asks is said from knowing it, not from reading
it that day.
