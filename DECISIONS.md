# Decisions that are yours to confirm

## 1. New posts default to `unlisted`

`skribl/routes.py` — `payload.get("visibility", "unlisted")`, and the v132
migration backfills every existing row as `unlisted`.

**Why.** A v131 Skribl was already effectively unlisted: it had a share URL,
anyone with the link could watch, and it appeared in no timeline because no
timeline existed. Defaulting to `public` would have retroactively published every
Skribl anyone ever made into a brand-new feed — including drafts, tests, and
things shared with exactly one person.

**What it costs.** Your platform must opt posts IN. If the post UI does not send
`"visibility": "public"`, the Skribl is created, gets a working share link, and
appears in no feed. Nothing errors, so it is easy to miss.

**Recommendation.** Have your platform's post UI send `"visibility": "public"`
explicitly, rather than changing the default here. That keeps the safe default
for the standalone app and for any other API client, and makes "this is feed
content" a statement by the surface that actually knows.

**Leave the migration's backfill alone** either way. That concerns posts that
already exist, made under different expectations, and republishing them is not
something you can undo once people have seen it.

## 2. CSRF is off by default

`SKRIBL_CSRF_PROTECT=1` enables it. Off is correct standalone — the API is
unauthenticated, so there is no session to protect and enabling it only breaks
existing clients. Turning it on by default broke 24 assertions across other
suites, every one a token-less POST correctly getting a 403.

**A host that authenticates POST /api/skribls with a cookie MUST switch it on.**
Without it, any page on the internet can post as the logged-in user.

## 3. Media storage defaults to `inline`

`SKRIBL_MEDIA_BACKEND=local` externalises blobs. The default is still v131
behaviour, deliberately: a storage change to a system holding real posts should
be opted into, not inherited by upgrading.

## 4. No foreign key from `skribl_posts.user_id` to a host user table

`user_id` is an indexed integer with no FK. This keeps Skribl droppable and lets
it run standalone. The trade is no referential integrity and no cascade delete —
deleting a user leaves their Skribls addressed to a missing id. If your platform
wants cascade behaviour, add the constraint in your own migration rather than
here, so Skribl stays independent.

## 5. Segmented controls are squared (`--r-seg`), labelled actions stay pills

**This reverses a v207-era rule and is the owner's call, made deliberately.**
The old rule read "pill segment = one-of-N with sliding highlight" and carried
an explicit "do NOT unify to one shape". That rule is now narrower: shape still
carries meaning, but corner radius is no longer the thing carrying it.

**The rule now.**

> **Round = an action you press. Squared = a group you choose within.**
> **Radius follows the container, not the semantics** — a cell inside a
> segmented group takes the container's derived inner radius, whatever the cell
> happens to do.

**Why it changed.** A 999px radius is a promise a control cannot keep once it
gets small. Measured on Flip at phone width: the tool group's active cell was a
37x24 box at radius 999px — i.e. a **circle** — sitting 6px from rounded-square
tiles carrying a 12px corner. Radius had stopped encoding "this is a one-of-N
group" and had started reading as an inconsistency. `--r-seg: 12px` is the tile
radius (`.t-btn` / `.tool-open`), so a segmented group now shares its
neighbours' corner and is told apart by the thing that actually distinguishes
it: a shared container with a sliding highlight. That signal survives at 24px.

**What is squared** (`--r-seg`, inner radii derived as `calc(var(--r-seg) - N)`
where N is the container's padding — never typed):

| family | where |
| --- | --- |
| `.tool-group` | Pad + Flip tool rows |
| `.seg` | onion depth/tint, fps, mirror, move scope, loop focus, zoom — 7 in Flip, 6 in Pad, 2 shared |
| `.smooth-seg` | smoothing off/low/high |
| `.photo-fit-group` | Fill / Fit / Stretch |
| `.edge-controls` | loop start/end/step nudge groups |
| `.nudge-btn` | the cells inside `.edge-controls` |

**What stays round, and why each is not an oversight:**

* **Labelled actions** — Post, Record, `loop-btn` (Match Drawing Time / Test
  Seam / Preview Loop), `dropzone-remove`. These are 4:1 to 8:1 boxes where a
  round end reads as deliberate rather than as a circle. Post especially: the
  design direction wants it to be the one loud thing on the surface.
* **`layer-toggle`** — an on/off switch. Round toggle = on/off is unchanged.
* **`color-ring`** — a colour swatch. A squared colour dot reads as a chip.
* **Surfaces** — `.toolbar` (16px), `.menu-sheet` (16px), `.flip-menu` (14px),
  `.pagebar` (0). You do not choose *within* a surface, so they keep their own
  radii; squaring a 530px-tall menu sheet to 12px makes it look like a button.

**How to reverse it.** Set `--r-seg: 999px` in `:root` (styles.css) and every
pill returns in one line. Nothing else needs touching, and the harness pin does
not need editing either — `verify_ux` reads the resolved token rather than a
literal, precisely so this decision stays the owner's to make.

**One operational note.** Editing `styles.css` requires re-emitting the derived
player stylesheet:

    python3 harness/tools/cssgraph.py --emit harness/tools/css_live.json skribl/static/player.css

`verify_cssplit.py` fails if you forget. It caught exactly that during this work.

---

# v221 decisions

**The header names the mode, not the brand.** The app ships embedded in an
already-branded host, so Pad's gradient icon and the word "Skribl" left the
header (owner call, measured first: the brand block was 108px of a 358px
phone header). Flip had already made this exact move — no icon, mode-word
only — so Pad was the inconsistent surface, not the pioneer.

**The wordmarks are graffiti piece lockups, approved by the owner through
mockup rounds — never integrated without sign-off.** SKRIBL PAD and
FLIP MODE as stacked throw-ups: spray cloud, block shadow, ink outline,
brand-gradient fill, shine pass. Eleven pair-concepts were shown and
rejected or refined on the way; the approval chain ran mockup → style
choice → reference-image adaptation → star swap → brightness tune →
integrate. Reversal: the marks are plain inline SVG in the two templates;
replace the `<svg class="brand-mark">` blocks. The verify_ux pins check
visibility, aria-label and size parity — not the artwork — precisely so the
artwork stays the owner's to change.

**The original logo was demoted, not deleted.** The 12-point star (verbatim
polygon, still on the player's card) is now the glint in both marks, at
lavender/half-opacity by owner request. One star, three surfaces, one
family.

**The marks match the tallest header element (44px), one size everywhere.**
"The phone is not a thinner brand" already had a pin; the mark inherits it.
The size-up exposed the ≤340 tier rule catching the mark (squashed 30×30);
the fix is a deliberately higher-specificity selector, commented in place.

**Accent: consolidated, demoted, restored — the classification is the
asset.** ~43 hardcoded brand hexes were folded into tokens; a full neutral
demotion shipped and the owner rejected it as flat within one look. Restore
cost four lines because the demotion was role tokens, not scattered edits.
All three palettes are recorded in `:root`. Standing guidance for a retry:
TINTED QUIET plus one loud signature element; quiet must not ship alone.

**One tree, one hash.** `run_harness.sh` and `release_run.py` now exclude
identical generated sets (the .pg gunicorn logs had diverged, printing two
hashes for one archive), and `verify_docs`' parity guard now matches `.log`
names — the regex blind spot that let the divergence live. Volatile release
facts (hash, counts) live only in generated documents; prose that quotes
them goes stale on save, demonstrated twice at v220.

**The mark outranks a button's word, because the mark is the whole brand.**
A v210 rule hid the header mark whenever a take existed
(`.header:has(#playWrap:not([hidden])) .brand > span`). It was written for
the 108px icon+wordmark lockup, which genuinely could not share a phone
header with a take's controls. The v221 mark is 70px and that premise had
been gone for two releases, but the rule stayed — so on a phone the mark
disappeared when recording started (intended) and never came back when it
stopped (not intended), at EVERY width, including 430 where ~89px of room
sat empty. Retired. `body.recording` keeps its own hide: recording always
needs the room, at every mobile width, and that case is genuinely static.

**Narrow widths are decided by measurement, not by a media query.** A static
rule cannot tell 430 from 320. `initBrandFit()` already measured the real
gap, so the take-saved case now falls to its `brand-collapsed` shed. The
shed runs in two passes, and the second one is the point: pass A keeps the
mark and sheds Record's label, the inter-control gap, then Post's label;
if the mark STILL does not fit, pass B puts those labels back and sheds the
mark instead. Without pass B, 360 and below would have spent Post's word and
lost the mark anyway — worse than the bug. Measured outcome, take-saved:
mark seated at 375/390/430, shed at 320/344/360; no header overflow and no
floor violation at any width or state.

**Post goes icon-only at 375–390 with a take saved — a deliberate narrowing
of the v219 pin, owner's call.** v219 fought to keep Post's word down to
375px and its reasoning still holds on its own terms; but it was settled
while the take-saved state hid the mark unconditionally, so Post's word was
competing against empty space. It now competes against the mark. At 390 the
mark is 21px over-full, Record is already icon-only there, the gap step
frees 8px, and Post's label frees 47 — Post's word is the only thing large
enough to pay for the mark. A shed word leaves a labelled icon with a title
attribute; a shed mark leaves nothing naming the surface. Idle is untouched
and keeps the word everywhere. Reversal: restore the `pw >= 375` split in
verify_ux's V219 block and delete pass A of the shed in `initBrandFit()`;
restoring the CSS selector named above also reverses it, less cleanly, by
making the shed dead code for the take-saved state.

**A limiter that cannot account for a slot refuses it — 429, not 500.** The
DB-backed post reservation sets a short `busy_timeout` on purpose, so a
contended SQLite write surfaces in milliseconds as an `OperationalError`
instead of blocking. That was half a design: routes.py already treats a `None`
reservation as "refused" and answers 429, but nothing turned a locked store
into `None`, so the exception propagated out of
`post_token = _rate_reserve_post(client_ip)` and Flask answered 500. The
poster saw a server error for a Skribl that was still safely in their browser.

It stayed invisible because it needs real contention. The harness fires twelve
concurrent posts at a two-slot quota; on one fast machine that resolves, and
the suite passes. On a loaded two-core CI runner it reproduces every time —
the first CI run that ever executed the harness returned
`[201, 201, 429, 429, 429, 429, 429, 429, 429, 500, 500, 500]` against an
assertion that admits only 201 and 429. Five releases of local green had never
touched it, and CI could not report it while every job died at exit 126.

Refusing is the correct direction, and the one the assertion names: "refuses
the rest under concurrency rather than over-accepting". Handing out a slot the
limiter cannot record is the failure that matters; making someone retry while
the store is contended is what 429 already means. Quota still leaks only
downward, briefly, and the warning line says which. The post-commit tombstone
sweep is now best-effort for the same reason the janitor beside it already
was: after the commit the slot exists, and letting a sweep failure reach the
new guard would refuse a caller for a slot it actually holds.

Reversal: drop the `except sa.exc.OperationalError` in `_db_rate_reserve_post`
and inline `_db_rate_reserve_post_locked` back into it. The split exists so the
unguarded path stays callable — the harness probe used it to prove the guard is
load-bearing, since the inner function must still raise where the outer must
not.

**The Loop Detail magnifier glyph is gone, and the lead that propped it up
with it.** The zoom bar carries two pills — Loop/Start/End and 1×/2×/4×/8× —
and on a phone they split onto separate lines with room to spare. Measured on
the Pad: focus pill 171.5 + gap 10 + glyph 24 + zoom pill 179.3 + lead 24 =
408.8px, so the row needed a 409px bar and wrapped below it.

Two of those numbers were decoration. The 16px glyph and its 8px gap cost 24px,
and v210 then spent another 24px on a `margin-left` for the focus pill whose
only job was to shove it back into alignment with the pill the glyph had
displaced when the bar wrapped. Removing the glyph does not merely free its own
24px — it makes the lead unnecessary, because with nothing before either pill
they both start at the bar's left edge and align when wrapped by construction.
That is precisely what v210 was buying, now had for free. 361px instead of
409px; one line down to a ~465px viewport instead of ~510px.

It also closed a Pad/Flip divergence nobody had noticed: Flip shipped the glyph
but never the compensating lead, so Flip's wrapped rows were misaligned by 24px
the whole time. Both surfaces now measure identically.

1×/2×/4×/8× reads as zoom without an icon, and the group keeps its tooltip plus
a new aria-label, so the glyph's labelling job is done by the label. verify_ux's
"carries a magnifier glyph" pin is replaced by two that outlast any redesign:
the group says what it is, and the row stays within a 400px budget. The budget
is the load-bearing one — the suite runs at 1280px where anything fits, so a
"same row" assertion there would pass no matter how much chrome came back.

Reversal: restore the glyph span in editor_music.js and flip.js, restore
`.zoom-seg[data-role="focus"]{margin-left:24px}` inside the ≤640 media block,
and raise the budget pin above 409.

**The canvas owns the only hairline; every other surface is made by fill and
shadow.** The header carried `1px solid var(--hairline)` on top of a
translucent fill AND a 26px-blur shadow — three cues for one job. With the
canvas ring (`--canvas-ring`) and the toolbar's own border, that put three
concentric outlined rectangles at almost the same radius on screen, with the
tool group's pill inside the toolbar making a fourth, and the eye could not
tell which was the subject. The canvas is the subject. Its ring stays; the
header's is gone.

Layout was not the reason and did not suffer: `box-sizing: border-box` is
global, so dropping the border returns 2px of inner width. Measured across
320/344/360/375/390/430 in idle and take-saved, every gap moved +2px and no
policy changed — the mark still seats at 375/390/430 with a take saved and
sheds at 320/344/360, no overflow, no floor violation. The brand-fit shed is
2px more comfortable than it was.

Verified against an EMPTY DARK canvas, deliberately: that is the state with the
fewest edges on screen, where a removed border shows worst. It still reads as a
raised card there. Also checked with Flip's tune drawer open, where the panel
tucks under the header and is meant to look like one object with it — the seam
holds without the header border.

One rule, three surfaces: Pad and Flip share this `.header` (flip.css only
adjusts padding and gap) and the player inherits it through the derived sheet,
which must be re-emitted with `cssgraph.py --emit` in the same edit. Reversal:
restore the one declaration and re-emit. `--hairline` is used 41 times
elsewhere and is untouched — this is a change to one rule, not to the token.

**Pad's tool row loses its tray, not its measurements.** Flip's `.flip-tools`
has never had a tray; Pad's `.toolbar` had a fill, a border, a blur and a
shadow. With the canvas ring that was two concentric outlined rectangles
competing for the eye, and the tool group's own pill inside the tray made a
third. The canvas is the subject and keeps the only frame; the row is now bare,
as Flip's always was.

ONLY the chrome went. The layout — fit-content width, the auto margin,
max-width, gap, padding and the whole responsive ladder — is untouched, because
that ladder encodes decisions this change has no business re-opening: v217
measured 343px on one row at 375 with 8px to spare, the sizing is tuned for
360px because it is a very common Android width, and v213 chose to WRAP rather
than shrink, on the grounds that shaving the buttons puts the tap target under
the 44px minimum. Flip shrinks to 36px and then 34px at its narrow tiers. That
is the trade Pad already considered and declined, and removing a background is
not a reason to reverse it. Pad still wraps to two rows at 320-344, on purpose,
now without a box drawn around it. Row counts were measured before and after at
320/344/360/375/390/430/500/700/900 and are identical.

**Undo and redo become filled tiles, because the tray was their surface.**
`.toolbar .undo-btn` was `background: none; border: none` — correct while the
tray was behind it, since a fill inside a fill is a box in a box. Without it
they were the only two controls on the row with no affordance of their own, and
read as bare glyphs. They now carry `var(--surface-control)` on
`var(--hairline-strong)`, which is exactly Flip's `.t-btn`. Geometry is
unchanged at 40x44, so the measured tap target is preserved; only the surface
is new. This is the tier the sheet already names at `.icon-btn`: bordered =
action, borderless = tool toggle, so the row still says which controls DO
something and which SELECT something.

NOT done, and left as an owner call: Flip hides the Pen/Eraser/Shape labels
below 560px (`.tool-btn-label { display: none }`) and that, with its smaller
buttons, is how it holds one row at 320. Pad keeps its words. Adopting Flip's
ladder wholesale would drop them and shrink the tap targets — a UX decision,
not a consequence of removing a background.

**The tool row's separators go; whitespace does the grouping.** `.tool-sep` was
a 1px line with 5px margins either side, and it was doing two jobs badly:
drawing a divider in a row that had just lost every other line it owned (the
tray went in 31ed04f), and standing in for the air that actually separates
groups. Measured before removing it, a separator plus its own gaps is worth
about 15px — and the grouping margins that replace it need roughly that much
anyway. Dropping both saved 2px at 1280 and cost 6px at 390. So this is not a
width change; it is one fewer line drawn on screen, and the width is a wash.
Say so plainly, because the question that prompted it was "do we get more play?"
and the honest answer is no.

Reversal: restore the `.tool-sep` rule in styles.css and the two `<span>`s in
skribl_editor.html and skribl_flip.html. Nothing else referenced the class.

**The colour ring sits against the tool pill, and the row's rhythm is why.** The
gap property was uniform across the row; what the eye saw was not. Measured at
1280 before the change, the visible gap between painted edges ran 4px at the
left end and 24px at the right, because half the controls paint a box and half
do not — a bordered neighbour puts its edge on the gap, a bare glyph sits inset
behind its own padding. The pill against a bordered undo was the 4px seam, and
it read as crowded next to image-against-music at 24px.

Colour is the one control that can sit next to the pill without two hard edges
meeting: the ring is 34px inside a 44px button, so it brings 5px of its own air
to each side. Moving it there turns one 4px seam into two comfortable ones and
costs nothing — same controls, same count. The row now reads left to right as
what the mark looks like, what happened to the drawing, and what is on the page
or how you are looking at it, with magnify joining image and music at the end
because it changes how you see rather than what is there.

At 1280 the seams go from 4, 4, 14, 19, 18, 18, 19, 24 to 21, 27, 4, 28, 24, 24.
The one remaining 4 is undo against redo, which is the single place two boxes
touching is the point.

**On phones the row gives up grouping and keeps even rhythm.** The desktop
margins (8/14/14) cost 8px that 360-class phones do not have: at 6/10/10 Pad
needed 336px against the 328 available at 360 and wrapped, breaking a decision
this file already records — 360 is a very common Android width and the row is
sized for it, not for 375. The phone tiers therefore run 5/6/6, which lands at
326: the exact figure the v217 note records, and every seam within a pixel or
two of 12, which is what two bare glyphs produce unaided. It is not grouping,
but it is not the 2, 2, 4, 8, 8, 9, 12 it replaced either. Widen these three
numbers and 360-class phones get a second row; the ladder was measured at
1280/641/640/560/430/400/390/375/360/351/344/320 before and after.

**Undo and redo are painted square; the 44px tap band moves to the ::before.**
40x44 on Pad and 36x36-in-a-44-row on Flip both read as stretched rectangles
beside a pill and a circle — they are the only controls in the row whose exact
shape is visible, so the shape has to be deliberate. They are now square at
every tier (40, 36, 34, 32) and the tap target is not given up: it moves to
`--tap-grow`, the mechanism `.color-dot`, `.onion-tint`, `.smooth-btn` and `.pb`
have used since v205-fix. Width is unchanged at every width, so this costs the
row nothing horizontally. Reversal: drop the `height` and `--tap-grow` pairs and
the two now-shared `::before` selectors.

**Flip adopts Pad's ladder, and wraps where it used to scroll.** Flip's row was
595px against Pad's 543 for the same nine controls, and 68px tall against 58 —
the same row, looser, reading as two designs rather than one. It now takes Pad's
gap, padding, button geometry and tier boundaries wholesale: 615 -> 561 wide and
68 -> 58 tall at 1280.

The behavioural half matters more. Flip was `flex-wrap: nowrap; overflow-x:
auto`, which held one line by letting Music slide off the right edge with the
scrollbar hidden and nothing on screen saying so — the defect the 320-tier block
in flip.css already documents, in a wider band. Measured: it overflowed at 351
(332 against 331 available) and again from 316 down. Pad has always wrapped
instead. A control on a second line beats one you cannot see.

Taking Pad's spacing is what makes the wrap affordable: Flip now holds ONE ROW
all the way to 320, so the second line is rarer than the scroll it replaces. The
narrow tier moved from 344 to 359 for the same reason — at 344 it left a ragged
band where Flip wrapped from 359 to 345 and then un-wrapped, and a ladder that
wraps and un-wraps as the window narrows is worse than either policy alone.

Two smaller repairs rode along, both found by measuring rather than reading.
flip.css's `@media (max-width: 380px)` set `gap: 5px; padding: 9px 6px` on
`.flip-tools` and NEVER APPLIED: the `max-width: 640px` block later in the file
wins on source order at equal specificity, so the computed gap at 380px measured
3px. Only the widths in that block ever did anything. It is the same trap the
344-tier block calls out one tier down, and the phone gap, padding and group
margins are now declared in the later block for exactly that reason — move them
back up and they go silent again. Separately, magnify was hidden at 430 on Pad
and 400 on Flip, so between 401 and 430 one row showed eight controls and the
other nine; both are 430 now, Pad being the reference.

NOT done, and left where it is: the combined photo-and-music glyph. It is worth
40-50px and the state can live in the glyph itself (the sun fills for a photo,
the note heads for a loop, retiring both `.tab-dot` badges), but `#photoPanel`
and `#musicPanel` are two separate `.tab-panel` partials shared by Pad and Flip,
and one button cannot open two drawers. That is a drawer merge, not a CSS
change, and it belongs in its own edit.

**Image and Music become one control, and the drawer they open is a router.**
The two buttons went to a single `#mediaOpenBtn` on both surfaces, opening
`_skribl_media_drawer.html`: three rows — Add image, Add music, Zoom — that open
the EXISTING photo and music panels. A router, deliberately. Nothing about those
panels' internals changes: the fit slider, trim strip, waveforms and opacity
controls all stay where they are, which is what makes a merge of this size safe
to ship in one edit. Pad's row goes from eight controls to seven and loses 42px
at 1280 and 24px at 390 — more than the whole spacing pass in this same version
cost it.

THIS IS A RESTORATION, not a new idea. The partial, the router JS and the merged
button all shipped at v216e and passed a full harness run there; they were absent
from the v217 upload with no note saying why. The uploads are whole-tree
snapshots, so there is no revert commit to read and no reason recorded. Treated
as dropped by accident. Two fragments survived the drop and are what confirmed
it: an orphaned comment above `#imageOpenBtn` in skribl_editor.html describing a
merge that was not there, and the comment block for `initMediaRows` in app.js
with its function body gone. Both are now attached to working code again. If the
removal WAS deliberate, the partial's header is where that reason belongs.

The glyph is not v216e's. That drew the image and music icons side by side in a
50x24 box, which is wide — the point of merging is width. This cuts the music
note OUT of the image frame with a dilated mask, so the two shapes read as one
object with a seam rather than as an overlap, in a 24x24 box like every other
icon in the row.

**The status lights moved inside the glyph, and they are the same elements.**
The sun is the photo light and the OUTER note head is the music light — outer
because that head sits clear of the frame, where a lit dot reads as a light
rather than as a mark on the picture. Grey means nothing attached, green means
present, amber means remembered but the file is gone: the vocabulary the sheet
already had, unchanged.

They are literally `#photoTabDot` and `#musicTabDot`, the same ids the two old
buttons carried, moved and resized. That is the whole reason this was affordable:
a dozen call sites across app.js, editor_photo.js, editor_music.js and flip.js
write to those two elements, and not one of them had to change. Styling SVG
circles instead would have meant rewriting all of them, because SVG elements do
not implement the `hidden` IDL property — `el.hidden = true` on a `<circle>`
sets a JS property that never reaches the attribute, so a rule keyed on
`[hidden]` silently never fires. HTML spans over the glyph, positioned as a
percentage of the glyph box so they ride the icon down the size ladder.

The router's rows carry their own dots, and those MIRROR the toolbar lights
rather than deriving state independently — a MutationObserver copies `hidden`
and `.pending` across. One source of truth, so the toolbar and the drawer cannot
disagree, which is the failure this arrangement is built to prevent.

Two things the harness caught that reading would not have. A stray `}` left by
moving a rule block truncated styles.css's cascade: `cssgraph.py` emitted 20,694
chars instead of 40,451 and `verify_cssplit`'s regeneration assertion failed with
the exact number. And the light's placement rule was written earlier in the file
than `.tool-open .tab-dot { top: 6px; right: 6px }` at equal specificity, so that
rule won on source order and dropped the music light 6px BELOW its note head —
correct in the markup, wrong on screen. It is now placed after it and scoped
through `.tool-open` so it outranks it both ways.

**The harness opens a media drawer in two taps now, and the same two on both
surfaces.** Six suites drove `#imageOpenBtn`/`#musicOpenBtn` on Pad and
`#imageBtn`/`#musicBtn` on Flip; they now share an `open_media(pg, which)`
helper. Worth noting what that removed: the old pair was a naming divergence for
the same job, and `verify_tips` has a comment recording the day it caused a real
gap. `verify_parity`'s table gained the three router rows, and `verify_ux`'s
phone audit now opens the router AND both panels it routes to rather than the
two old buttons — skipping the panels would have quietly narrowed the audit.

The router does not toggle the way one button did. Clicking `#mediaOpenBtn` while
a panel is open opens the ROUTER, over the canvas; three call sites were using
the old button's toggle to CLOSE, and turning them into opens left a drawer
covering `#recordBtn`. Closing is its own `close_media()` now, and says so.

NOT done, and next: `.tool-open` is 36x44 on phones (34x44, then 32x44 at the
narrow tiers). Borderless it shows nothing, but a drawer-open or magnify-active
button paints `rgba(124,92,255,.16)` with an inset ring across that whole box —
an elongated lit pill next to the square tiles this version just squared. The
fix is the same one undo/redo took: paint square, keep the 44px band on the
`::before`.

**The light sits inside the ring, and there is no grey when nothing is
attached.** Two corrections to the version above, both from the owner looking at
it.

The dot BECAME the circle: a 6px light over a sun whose outer diameter is 3.2px
covered it completely, so the icon lost its sun and gained a blob. It is 4px
now, centred inside the ring, and the ring itself had to make room -- the sun
goes r=1.5/stroke-2 to r=2.7/stroke-1.4 and both note heads r=3/stroke-3 to
r=4.2/stroke-2.0. That widening is not decoration: at the original weights there
was no inside, the stroke ate the whole circle. Both heads move together so the
note stays symmetrical when nothing is lit. Measured after: the photo light
lands at (8.16, 8.16) against a sun centred on (8.20, 8.20), and the music light
at (22.55, 21.11) against a head centred on (22.56, 21.12).

**And the size was decided at 1:1, which is the only place it could be.** The
first pass was 3px, chosen while looking at the icon blown up six times, where
it read fine. Rendered at the size it actually draws it was very nearly
invisible -- a 3px dot is mostly antialiased edge, with a core of about four
true-colour pixels. 4px is the smallest that still reads as a light on screen
while leaving each ring a visible stroke of its own. Any judgement about a mark
this small that is made on a magnified image is a judgement about a different
picture.

The COLOURS never changed and this is worth recording because it was asked:
green is `rgb(27, 207, 143)` = #1bcf8f and amber is `rgb(255, 210, 63)` =
#ffd23f, read back from the computed style and confirmed by sampling the
rendered pixels. What looks different under magnification is antialiasing around
a small dot, plus the amber's own glow -- not the hue.

The grey empty state is gone entirely. `.tab-dot-empty` answered "is there no
media?", which is a question nobody asked of a resting toolbar, and it made the
merged button noisier than the two it replaced. Nothing attached is now simply
the icon. The `:has()` swap rule stays for the controls that still pair a grey
twin with a green one.

One more thing measurement caught: the light's small size was behind a
`max-width: 640px` query, which shrank it on PAD -- where `.tool-open svg` is
24px at every width and the ring had not shrunk at all. It is Flip that steps
its icons to 21px below 640, so that rule is scoped to `.flip-tools` now. A
media query is not a proxy for "the icon got smaller" when only one surface
resizes its icons.

**The media button says its state in colour, and the dots are gone.** The image
frame goes green when a photo is set and amber when one is remembered but its
file is missing; the note does the same for music. With nothing attached it is
the ordinary icon in the ordinary grey.

This supersedes both dot attempts above, and the reason is worth keeping because
the dots were MEASURED and still wrong. A 4px light inside a 24px icon is mostly
antialiased edge -- about four pixels of true colour -- so reading it took more
attention than a toolbar glyph is worth, and every judgement about it had to be
made on a magnified image, which is a judgement about a different picture. A
tinted half is unmissable at 1:1. It also needs no geometry of its own, so the
sun and the note heads went back to the sizes the source icons use: r=1.5 and
r=3, exactly as drawn before any of this started.

An earlier version of this file called the tint "too loud" while looking at it
enlarged. At the size it renders it is not loud, it is legible, and the earlier
note was wrong for the same reason the dots were.

NO JAVASCRIPT CHANGED FOR ANY OF THE THREE ATTEMPTS. `#photoTabDot` and
`#musicTabDot` remain the state and are still written by the same dozen call
sites; they are simply not drawn any more, and `:has()` reads them to paint the
matching half. Keeping the state in elements the app already maintains is what
made three different visual treatments cost three CSS edits between them, and it
is the part of this design to preserve if the look changes again.

One ordering detail, because both selectors match while a file is missing:
`.pending` is written after "present", so amber wins over green.
