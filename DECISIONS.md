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
Without it, any third-party page can post as the logged-in user.

**v224: this is now enforced, not advised.** Passing `current_user_id` without
a `csrf` verifier RAISES at blueprint construction. The default above is
untouched — it is the default for an *unauthenticated* deployment, which is
what standalone Skribl is — but the combination "authenticated and unprotected"
can no longer be reached by not noticing a log line. `csrf=False` is the
explicit declaration for a host whose authentication is not cookie-based, and
its existence is what makes refusing fair rather than presumptuous. See v246.

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

**The music note is drawn at final size, because scaling it down is what broke
it.** The composite took the 24-unit music icon and shrank it with
`transform: scale(0.62)`, then thickened the stroke back up so it stayed visible
at that size. That took the stroke-to-radius ratio from the source icon's ~0.67
to 1.0 -- and at 1.0 each stem's end cap lands exactly on its note head's stroke
centreline. Both stems meet their heads TANGENTIALLY by design, so the ratio is
the whole ballgame: at 0.67 it is a clean join, at 1.0 it is a blob, and the
blob is what "the lines overlap the circles" describes.

Redrawn natively at r=2.3 with a 1.8 stroke (ratio 0.78), no group transform.
The heads also had to move APART: at the scaled geometry they were tangent to
each other as well, and two touching rings read as one lumpy shape rather than
two notes. 5.6 apart at r=2.3 leaves a full unit of gap.

The note now sits far enough outside the frame that the mask cuts a SEAM between
them instead of biting a piece out of the frame. The scaled version was
amputating the frame's bottom-right corner and the tip of its mountain, which is
the other half of what read as "drifting" -- the two shapes were not sitting
next to each other, they were eating each other.

General lesson worth keeping: scaling a stroked icon does not scale its stroke,
and compensating by thickening the stroke changes every ratio the icon's
geometry depends on. Draw it at the size it will be shown.

**"Autosave failed" now says WHICH failure, because four words could not be
diagnosed.** The catch in `writeAutosave()` wraps the whole expression --
`localStorage.setItem(KEY, JSON.stringify(serializeAutosave()))` -- so a
QuotaExceededError, a private-mode rejection and a plain TypeError inside
`serializeAutosave()` all arrived on screen as the identical message. A report
of "autosave is failing" with a screenshot was therefore not enough to tell a
full disk from a bug, which is the wrong place for a durability warning to be.

Storage-full is now its own state and its own words -- "Storage full — not
saved" -- because it is the one the user can act on. Everything else stays
"Autosave failed". Engines disagree on the name (QuotaExceededError,
NS_ERROR_DOM_QUOTA_REACHED, code 22, code 1014) so the test is deliberately
loose. The console additionally gets the exception name and message, the total
localStorage in use, the key count and the LARGEST key, so the next report
arrives with its own diagnosis attached.

FOUND WHILE LOOKING, NOT FIXED, AND DELIBERATELY SO: `saveLocalFallback()` in
editor_post.js writes an entire drawing payload -- media bytes included -- to
`skribl_post_<id>`, a unique key per save, and NOTHING EVER REMOVES THEM.
lib/posted.js caps its INDEX at 200 entries, but the index holds metadata; the
payload blobs are unbounded. Every local save is a permanent megabyte-scale
tenant of a ~5MB origin quota shared with the autosave key, so a run of them
starves autosave for every drawing afterwards, however small. That is the most
plausible cause of the report and it is a real defect on its own terms.

FIXED, once the owner's storage listing settled what was actually happening --
and it was worse than described. `remove()` deleted the INDEX ENTRY and left the
payload behind, so deleting a Skribl from the tray freed 1KB of metadata and
stranded two megabytes that nothing could ever reach again. That is why "I
deleted a skribl from the tray and it still didn't autosave".

Three changes, cheapest first:
  * `remove()` and `clear()` now drop the payload with the entry.
  * `sweepOrphans()` deletes any `skribl_post_*` blob with no index entry.
    Nothing is lost: the tray is the only route to one, so an orphan is already
    unreachable.
  * `evictOldest()` drops the oldest local save, payload and entry together.
    This one IS destructive and is the owner's explicit call. It runs only when
    the store is genuinely full and a drawing is about to be lost for want of
    room, and it says what it did in the console. An old saved copy is worth
    less than the work on screen.

Pad's autosave and Flip's last-ditch write both call `reclaim(needBytes)`, which
sweeps first and only then evicts. Verified: a forced QuotaExceededError now
reclaims and the pill reads "Saved" instead of failing.

Still outstanding, and NOT this: on the owner's machine
`skribl_flip_autosave_v1` alone was 2,763KB -- over half the origin's ~5MB, in
one key, for one 24-page flip. Flip already degrades to a media-free "lite"
payload under quota pressure, so it is not broken, but the drawing data itself
lives in localStorage while the media bytes already live in IndexedDB. Moving it
there is the real fix for the ceiling and it is a bigger change than this one.

**The one media control is REVERTED. Image and Music are two buttons again.**
Everything above about the merged glyph, the router drawer, the status light and
the tinted halves describes code that is no longer in the tree. It is kept
because the reasoning still holds for anyone who tries this again, and because
the reason it failed is not in any of it.

The merge cost a tap. Opening a photo went from one press to two -- the router,
then the row -- and the router's own rows were not self-evident enough to pay
for that. Every media action on both surfaces got slower and less obvious, all
day, in exchange for width.

And the width no longer needed buying. The merge was drawn up when Pad's row was
563px at 1280 and wrapping at 352; by the time it landed, the same version's
spacing work had it at 316px on a phone with headroom to spare. The saving that
justified the merge had already been won by cheaper means, so what remained was
purely the cost. A control that trades a tap for pixels is a good trade only
while the pixels are scarce.

WHAT CAME BACK CHANGED, because the old placement had a bug worth keeping fixed.
The status dot was anchored to the BUTTON: `top: 6px; right: 6px`. The button is
44px wide on desktop and 34px on a phone while the icon stays 24px, so one rule
produced two placements -- floating above the icon's top edge and off its right
on desktop, drifting inward over the glyph on a phone. It is anchored to the
ICON now, `left: calc(50% + 4.5px); top: calc(50% - 11.5px)`, which lands the
dot 4px inside the icon's top-right corner on both. Measured: desktop icon
corner (34, 10) with the dot at (30, 14); phone corner (29, 10) with the dot at
(25, 14). The same relationship, which it never was before.

The ring around the dot is the row's ground now (#06070a), not the tray colour
it inherited from v205. The tray went in 31ed04f and a #171a22 ring on a #06070a
row was a faint halo around every dot.

`.tab-dot-empty` is retired with it: an empty tab no longer shows a grey circle.
It answered "is there no media?", which a resting toolbar should not be
answering, and it put two permanent marks on a row that had just spent a version
getting quieter. Reversal is in the CSS comment.

ONE THING THE ROUTER DID THAT NOTHING DOES NOW: its Zoom row was the only way to
reach magnify on a phone, where the button is hidden at 430 and below. That gap
is not new -- it existed before the merge and is back exactly as it was -- but
it is the one piece of the router worth stealing if magnify should be reachable
on a phone at all.

**The header is a 36px row on both surfaces, and tune and ⋯ lose their box.**
Flip already read this way and Pad did not: Flip draws its tune and ⋯ as bare
glyphs, Pad drew them as 44px bordered tiles with a fill. Side by side the same
two controls looked like two different design systems, and the heavier of the
two was on the surface with more in its header.

The box goes. `.icon-btn`'s border and fill were v205-fix's "bordered action"
tier and they earned their place while the header sat in a tray — the tray went
in 31ed04f, and a bordered tile on a bare header is a frame around nothing. The
class keeps its border everywhere else; only the header's two openers drop it.

36 across the row — tune, ⋯, Record, Play, Post — because that is the size
Flip's header already used and the one the owner picked looking at both. Flip's
own tune was 34, two pixels short of the ⋯ beside it for no recorded reason; it
is 36 now too.

The 44px TAP band is not given up. It moves to the `::before` via `--tap-grow`,
the mechanism `.color-dot`, `.onion-tint` and `.toolbar .undo-btn` already use.
verify_ux pins all three facts — the painted box is 36, the hit box is still 44,
and a tap 3px outside the visual box still lands on the button. That last one
matters: the ::before extends over the header, and without the stacking context
the header wins the hit test and the grown target is a fiction. Pinning only the
visual size is how a shrink quietly costs a tap target.

One number changed in place rather than being overridden:
`.header.compact .btn.play.btn-icon` carries `height` at (0,4,0), which no
row-wide rule can reach past. Its comment already said "match Play's height to
Record/Post"; the row is 36 now, so the intent is preserved by changing the
number where it lives.

Flip's back arrow followed, one step further down. It was the last bordered tile
in either header and at 44px it outweighed the wordmark beside it: the heaviest
thing in the lead was the control you press least.

It does NOT join the 36px tier with tune and the overflow menu, and that is the
point. Those two act ON the drawing; the back arrow leaves the surface entirely.
Sizing it identically would say they are peers. 32px in a muted grey reads as
chrome -- findable, clearly a control, quieter than everything beside it. Four
treatments were rendered in the running header before picking: 44 boxed (the
old one), 36 bare, 32 muted, tucked tight to the wordmark, and a hairline rule
in place of the box. The rule was rejected on principle -- it re-draws the edge
this version spent its time removing.

Tap band 44 via `--tap-grow: 6px`, verified by hit test: a point 4px outside the
32px box still resolves to the anchor.

---

## A lit `.tool-open` is square, and the status dot is anchored to the glyph

Two defects that only showed up on a phone, both fixed by making a control's
*painted* box match the shape the rest of the row settled on.

**The elongated lit state.** `.tool-open` is borderless -- colour, image, music
and magnify paint nothing at rest -- so nobody noticed its box had stayed
`36x44` / `34x44` / `32x44` while every tile around it was squared. Measured on
Pad at 390px with the colour drawer open: `[34, 44]`, filled
`rgba(124,92,255,.16)` with an inset accent ring. The only lit thing in the row
was an elongated pill standing beside square neighbours. The shape was always
wrong; opening a drawer is just what made it visible.

Now square at every tier on both surfaces, with the 44px tap band moved to a
transparent `::before` -- the same trade `.toolbar .undo-btn` and the header's
openers already take. Width is untouched, so the measured row ladder does not
move by a pixel. Verified by hit test at 3px outside the painted edge: 36px
tier, 34px tier and Flip's 32px tier all still resolve to the button.

**The dot that only fitted one surface.** `.tool-open .tab-dot` positioned
itself with hard-coded offsets that assumed a 24px glyph. Pad holds 24px at
every width, but Flip steps `.flip-tools .tool-open svg` to 21px below 640 --
so the same rule put the dot 2px *past* the corner there: 5.5px outside the
icon, 1.5px inside, reading as a mark floating beside the glyph rather than a
badge on it.

The offsets now measure from `--icon-half`, redeclared where the icon changes
size (`12px` default, `10.5px` in Flip's `<= 640` block). The dot's centre lands
exactly on the icon box's top-right corner, so a 7px dot sits 3.5px out and
3.5px in -- half nestled, half proud -- on Pad and Flip alike, at 44px, 36px,
34px and 32px buttons. The 1.5px ground-coloured ring stays: half the dot now
overlaps the glyph's stroke, and the ring is what keeps the two from merging.

**How to reverse either.** For the shape, delete the `v225: a lit .tool-open
must be SQUARE` block in `styles.css` and the three `.flip-tools .tool-open`
`height` declarations in `flip.css` -- heights return to 44 and the tap band
comes back from the box itself. For the dot, replace the two `calc()`s in
`.tool-open .tab-dot` with `left: calc(50% + 9px); top: calc(50% - 16px)`, which
is where they sat before, and drop the `--icon-half` declaration in `flip.css`.

**Follow-up, same version.** Two things the owner caught by looking at the
running app.

*The merged Play pill was 38 tall, not 36.* `.header .actions .btn` brought
Record and Post to 36 and Play came with them, but Play is not the outer box --
it sits inside `.play-wrap`, the shell that merges it with the duration badge,
and the wrap had no height of its own: it hugged a 36px button and added its own
1px border top and bottom. Measured at 1280: Record `[100, 36]`, Post
`[138, 36]`, playWrap `[92, 38]`. The wrap takes the 36 now (border-box) and the
button inside comes down to 34; the divider needs no rule, `align-self: stretch`
already follows the wrap's content box. Desktop only -- below 641 the wrap goes
transparent and borderless and the button carries its own border, so that box
was already 36.

*The dot's offset is 0.5 of the icon, not 0.375.* Half in / half out of the
ICON BOX, which is what the pre-v224 rule produced and what the owner's
reference screenshot of the old look shows. 0.375 was tried in between, on a
reading of the same phrase as half over the ARTWORK: both glyphs stop at
`(21, 3)` in their 24-unit viewBox rather than at the box corner, so 9 units
puts the dot squarely on the stroke. It reads as a mark ON the icon rather than
a badge attached to it. Recorded so it is not rediscovered as an improvement.

**Follow-up 2: the dot offset is 0.4 of the icon, and the number is the
button's, not taste.** 0.5 put the dot's centre exactly on the icon box corner
-- correct on a 44px desktop button, and what the pre-v224 rule resolved to
there. But `.tool-open` carries a 12px corner radius and shrinks to 36 and 34
on phones while the icon stays 24, so the dot ran into the rounded corner of the
LIT box. Diagonal clearance between the dot's outer edge and the corner's
painted surface, measured per tier:

| tier | 0.5 | 0.4 |
| --- | --- | --- |
| Pad desktop 44/24 | +5.67 | +9.07 |
| Pad 393-640 36/24 | +0.01 | +3.41 |
| Pad <=392 34/24 | **-1.40** | +1.99 |
| Flip 393-640 36/21 | +2.14 | +5.11 |
| Flip <=392 34/21 | +0.72 | +3.69 |
| Flip <=359 32/21 | **-0.69** | +2.28 |

Two tiers were negative -- the dot crossed the accent ring of an open drawer,
which is the state it is most visible in. 0.4 is the largest offset that clears
every tier by about two pixels. The cost is 2.4px of inward travel on desktop,
where there was never a clearance problem, paid so the dot sits in the same
place relative to the icon at every width. That is the property the
button-anchored rule could not hold, and it is the whole reason for the
re-anchoring.

---

## The tool shelf holds a fixed number of cells; the tray holds the rest

**This is a decision about process, not about a tool.** Flip's bottom row was
holding two populations out of one width budget. The document controls -- colour,
undo, redo, image, music, magnify -- are a CLOSED set. The mark-making tools are
not: pen, eraser and shape today, with select, fill and text all plausible. They
shared one shelf, so every new tool competed with undo for the same pixels, and
each addition became a fresh fitting exercise across six breakpoints and two
surfaces. Measured before the change: a fourth cell takes the pill 121 -> 158px
and wraps the row at 320, 344, 360, 375, 390 and 431.

`TOOLS` in `flip.js` is now the single place a tool is declared. The shelf shows
at most `SHELF_MAX` (3) cells; anything beyond lives in `#toolTray` behind a
chevron. **The pill's width therefore stops being a function of how many tools
exist** -- verified at 320, 360, 375, 390 and 430: 103 -> 103 and 121 -> 121 when
a fourth tool is registered.

**With three tools nothing changes.** 3 <= SHELF_MAX, so all three keep their
cells, the chevron stays hidden and the tray is never built. This was deliberate:
a tray that immediately demoted Shape to two taps would be a regression paid for
a benefit that has not arrived yet. The mechanism is dormant until a fourth tool
exists, and the row does not move when it does -- three cells is what it already
held.

**Most-recently-used, not fixed.** Once overflowing, the shelf shows the two most
recent tools plus the chevron. The active tool is always the MRU head, which is
what guarantees it has a visible cell and therefore that `positionToolSlider()`
always has a button to sit under. A tool picked from the tray is promoted onto
the shelf, so the second reach for it is one tap.

**The registry is a real entry point, not a test seam.**
`window.SkriblFlipTools.register({id, label, icon})` is how a tool will actually
be added, and it is how `verify_tray.py` exercises the overflow path -- so the
suite never has to ship a fake tool, and what it tests is what will be used.

**What this does NOT do.** It adds no tools. Fill, Text and Smudge do not exist
anywhere in the tree; Select exists on Pad only (`editor_draw.js` plus
`lib/selection.js`) and needs porting to Flip's per-frame model. The eight-cell
mock that argued for this was showing that the container holds eight, not
promising them.

**Flip only, for now.** Pad has the same three tools and the same structure, and
should get the same treatment when it next needs a fourth. Doing both at once
would have doubled the surface under test for no behaviour change on either.

**How to reverse it.** Set `SHELF_MAX` to a number larger than `TOOLS.length` and
the chevron never appears; delete `#toolTray`, `#toolMoreBtn`, the `tools` entry
in `_flipDrawerCtl`, the `.tool-tray*` rules in `flip.css` and
`harness/verify_tray.py`. `setTool()` and `activeToolBtn()` now read the registry
rather than a hard-coded roster and are worth keeping either way.

**Follow-up: Pad gets the tray, and the shelf moves to a shared lib.** The
mechanics are in `skribl/static/lib/toolshelf.js` now and both editors create one
-- rather than flip.js keeping its copy and app.js gaining a second.
`verify_surfaces.py` exists because app.js and flip.js define 57 functions with
the same names and share zero runs of six identical lines; adding a 58th by
copying would be the exact failure it measures. The CSS moved the same way, from
flip.css to styles.css, which both templates load.

The ratchet then caught the one thing left behind: extracting Pad's slider
placement into a named function took the shared-name count from 60 to 61 and
`verify_surfaces` failed. Both surfaces had arrived at an identical
`offsetLeft - group padding` by independently fixing the SAME two bugs -- a
two-button assumption that parked the pill under the wrong cell once a third tool
existed, and a double subtraction of the group's own offsetLeft. That is
precisely what the ratchet is for, so the placement moved into the lib too and
the count went back to 60.

**Two bugs this introduced, both now pinned.** The chevron is a `.tool-btn` --
it has to be, to inherit the pill's shape and the sliding highlight's geometry --
so it was swept up by the binding that calls `setTool(btn.dataset.tool)` on every
tool cell. It carries no `data-tool`, so opening the tray called
`setTool(undefined)`: Flip clamps unknown ids to the pen and merely looked fine,
while Pad assigns `tool` unconditionally and was left with **no tool selected at
all**. And the tray cells were styled `font: 600 10px/1 inherit`, which is an
invalid shorthand -- the family slot does not accept `inherit` -- so the whole
declaration was dropped and the labels rendered in the UA default face at ~13px.
Neither was caught by the first version of `verify_tray.py`, which is why it now
pins "opening the tray does not change the tool" and the computed font size, on
both surfaces.

Pad's row already wraps at 320 with three tools, so the width pin there asserts
that adding a tool does not CHANGE whether it wraps, rather than that it never
wraps. Measured: Pad 118 -> 118px and Flip 121 -> 121px (103 at 320) with a
fourth tool registered.

---

## Select is a tool on Flip, and still absent from Pad

**The owner's argument settled this, and it reversed mine.** I had proposed
Select as a third scope on Move's segmented control -- "what does this offset
apply to?" -- on the grounds that it is not a way of making marks. That holds
only while the single operation is translate. Transform accompanies Select
(scale, rotate, mirror), and Move's entire vocabulary is one `(dx, dy)` offset,
typed as `40, -12` and applied to a page or a run of pages. It cannot express a
rotation, and "and following" is meaningless for a rotation of a subset --
different strokes on every page. Bolting transform onto `mbScope` would mean
rebuilding the move bar into a transform bar, at which point "scope" is the
wrong frame entirely.

So the division is:

* **Move mode** -- translate a whole page, or a run of pages, by one offset.
  Cross-page. Typed coordinates.
* **Select tool** -- pick a subset of THIS page, then transform it. Per-page.

**Why it is safe on Flip and was not on Pad.** v219 removed Select from Pad
because Pad records a timed performance: moving points that were already
recorded made replay draw a stroke at its NEW position at its OLD timestamp.
Flip has no timeline within a page -- playback reveals strokes in index order --
so moving a point changes only where it is, never when. Flip's Move mode has
translated whole pages this way since v213. `verify_select.py` asserts Pad's
registry still does not list the tool, so a future "make the surfaces match"
cannot quietly reintroduce what v219 removed.

**Undo is an operation, not a snapshot, and that is why this port is short.**
Pad's Select had to clone the selected point objects BEFORE snapshotting, or
`strokes.slice()` aliased them and undo silently restored the moved position --
its own comment is emphatic about the ordering. Flip's `actionLog` stores what
was done, so undoing a selection move is the same translation negated and there
is nothing to alias. The entry is `{type:'selmove', idx, spans, dx, dy}` and the
object branch of `undoStroke()` now dispatches on `type` -- it used to assume
every object was a Move-mode entry and would have translated the whole page.

**Whole strokes, never fragments.** The marquee selects by GROUP, so a box that
clips a stroke takes all of it or none. Moving half a stroke would leave
`strokeGroups` accounting for points that had walked away from their run, which
is the shape the server rejects on share.

**Transform is NOT in this change.** Scale, rotate and mirror are a separate
piece of work: the handles, their hit-testing, and the live preview. The model
is ready for it -- a point is `{x, y, color, size, t, erase}` and `size` is
per-point, so a scale can scale weight along with position rather than producing
a stretched outline.

**How to reverse it.** Remove the `select` entry from Flip's tool registry in
`flip.js` and the tool is gone from both the shelf and the tray; the marquee code
and `translateSpans()` become dead but harmless. Drop `lib/selection.js` from the
Flip template and `harness/verify_select.py` to finish.

## Transform: uniform scale on corners, rotation on a grip

**Scale is UNIFORM and corners-only, and that is the model's decision, not a
shortcut.** A point is `{x, y, color, size, t, erase}` and `size` is a single
scalar. A non-uniform scale has no honest answer for stroke weight: stretch a
drawing horizontally and its verticals would have to be thicker than its
horizontals, which one number per point cannot express. Edge handles are absent
by design rather than missing. If they are ever wanted, `size` has to become a
pair -- and that is a payload change, so it is a decision, not an afternoon.

**A scale multiplies `size` along with position**, which is what makes it worth
having at all: shrink a drawing and its strokes get thinner, rather than the
same-weight outline of a smaller shape. Rotation leaves `size` alone.

**Every gesture recomputes from a snapshot taken on pointerdown**, never on top
of the previous frame. Translate could get away with compounding deltas -- it is
exact under addition, and `selmove` does exactly that -- but a ratio applied to
an already-scaled value sixty times a second walks the geometry away from the
finger, and a drag out and back would not return to where it started.

**Undo restores coordinates rather than inverting the transform.** Negating a
translate is exact; dividing by a scale ratio is not, and repeated undo/redo
would drift. The entry carries `before` and `after` arrays of `{i, x, y, size}`
for the selected points only -- one or two strokes, so tens of points.

**Still missing from the FlipaClip list this came from:** mirror, clone and cut.
All three are cheap now that the transform pipeline exists -- mirror is a
negative scale on one axis, clone is a span copy, cut is a span splice -- and
none of them needs a new handle.

**One test lesson worth keeping.** `fresh()` in `verify_select.py` clears
localStorage AND empties the in-memory document before reloading. Clearing
storage alone does not work: the live page still holds the drawing and saves on
the way out, so the draft is written back after the clear and restored by the
very reload meant to be rid of it. It now also asserts zero points afterwards,
because a polluted page turns every stroke-index assertion into a coin flip --
which is exactly how it failed, reporting "the unselected stroke was touched"
when the real fault was that the selected stroke was not the one the test thought.

## Mirror, duplicate, cut and paste live on a bar that replaces the page bar

`#selbar` appears exactly while a selection exists and takes `#pagebar`'s row --
the pattern `setMoveMode()` established. Five more actions do not fit on a 320px
phone as extra chrome; they fit as a different job for the same row. `.pb-tx`
already hides below 640, so every cell drops to its glyph for free.

**One undo shape for all four: `selframe`,** carrying a before/after pair of that
page's `strokes` and `strokeGroups`. `selmove` negates its dx/dy and a transform
restores coordinates, because both leave the arrays the same length. These do
not -- duplicate appends groups, cut splices them out, paste appends -- and
undoing an index-range edit whose indices have since moved is exactly the class
of bug this codebase keeps finding. The entry carries the arrays rather than the
arithmetic. One page's points is the same order of magnitude the redo stack
already holds.

**Cut writes to a clipboard, and that is a deliberate widening of the request.**
Asked for "cut", the narrow reading is remove-the-selection -- but that is
Delete wearing the wrong name, and a flipbook's real use for cut is taking
artwork off one page and putting it on the next. So Cut remembers and a Paste
cell appears; the suite pins the cross-page case specifically. Paste is HIDDEN
rather than disabled until the clipboard has something: on a bar this tight a
disabled control is a cell of dead width.

**Duplicate leaves the COPY selected, not the original.** The next thing anyone
does after duplicating is move the new one, and the two sit on top of each
other -- selecting the original would move the wrong artwork silently.

**A selection never crosses pages.** `go()` clears it. Spans are index ranges
into ONE page's strokes array; carried to another page they would point at
different artwork, or run off the end of a shorter one.

**A note on this file's shape, now that it has bitten three times.** flip.js is
one ~4000-line classic script with `let` state scattered through it, and
`setTool()` runs during init. Three separate crashes in this version came from
the same cause: a function called early reached a `let` declared later, threw
"Cannot access X before initialization", and killed every line of the file after
it -- taking the filmstrip, the tool shelf and every later handler with it. A
`typeof` guard cannot rescue a `let`; only declaration order can. The selection
state, the move state and the clipboard are all hoisted to the top now, and the
rule going in is: state any early path can reach belongs with the early state,
and anything touching state declared further down belongs in the load handler.

## Light mode, phase 1: the chrome's colours move into :root

**I mis-scoped this out loud and the correction is the point.** I said light mode
was "the tokens exist, it's a palette block". It was not. There were 37 tokens
and **462 colour literals outside them** -- 225 hex uses across 57 distinct
values, plus 237 rgb/rgba of which 91 were white or black overlays that have to
invert. No theme scaffolding existed at all.

Phase 1 moves 179 neutral literals into `:root` **with their values unaltered**.
All nine rendered scenes -- both editors at two widths, plus the draw drawer, the
menu, the tune sheet and the overflow menu -- came back pixel-identical, worst
channel delta 0 against a capture-noise floor of 4 measured on this machine.

**The ramp is deliberately not collapsed.** Several tokens are within a couple of
luminance steps of each other and could merge, but merging them here would be a
visual change smuggled inside a mechanical one, and the two are indistinguishable
in a diff. Phase 2 has to choose a light value for each of these anyway, and the
duplicates fall out there, on purpose.

**Two things stayed literal.**
* `#0d0f14` is the CANVAS default background. That is the document's own colour
  -- saved, shared, exported -- so it must not follow the UI theme. A Skribl
  cannot change because the person looking at it prefers a light interface.
  (The owner chose chrome-only when asked.)
* `#fff` is almost always text on a coloured fill, and white on violet stays
  white in either theme.

**White washes became a triplet, not a colour.** `rgba(255,255,255,α)` at 52 call
sites became `rgba(var(--wash-rgb), α)` so each site keeps its own alpha and a
light theme flips all of them with one line. Black `rgba()` was left alone: those
are drop shadows and scrims, which stay dark whichever way the chrome goes.

**`verify_surfaces.py` now holds the line.** It fails on any hard-coded neutral
outside `:root` in either sheet. One grey added next month is one control that
stays dark when the theme flips, and nothing else would catch it.

**A tooling note worth remembering.** The rewrite script blanked comments and
`:root` into placeholders before substituting -- comments quote colours in prose,
and `:root` is where the values are defined. Restoring them in ONE pass corrupted
both stylesheets into binary: `:root` is stashed after the comments are, so the
stashed `:root` text still contained comment placeholders, and a single
`re.sub` left raw NULs in the file. The restore loops to a fixed point now and
asserts no placeholders survive.

## Flip's draft: strokes in localStorage, media bytes in IndexedDB

**This closes the bug the owner reported as "autosave is failing on pad", and it
was not Pad's fault.** localStorage is capped at roughly 5 MB PER ORIGIN and both
editors share it. Flip was writing its media into that budget as base64 data
URLs, inflated 4/3 by the encoding -- a 30-second WAV is ~6.7 MB on its own. One
Flip draft measured 2.7 MB of the shared 5 MB, and Pad's autosave was the thing
that fell over. The reclaim-and-evict fix shipped earlier in this session treated
the symptom.

The spill to IndexedDB already existed but only as an EMERGENCY path, reached
after localStorage had refused the write -- which made a 5 MB quota the thing
standing between a user and their drawing. It is the normal path now. Measured on
the same draft: **localStorage went from 1,683,508 B to about 3,500 B**, with both
media intact in IndexedDB.

The merge on the restore side needed no design work: it was written for the quota
case and had been correct all along. What changed is that it is reached on
purpose.

**Two bugs surfaced by making the rare path common.**

*The hydration guard was a byte comparison.* It refused to merge the media if
`localStorage` differed from what it held when the read started -- but every save
rewrites `savedAt`, so any autosave landing in the gap made the string differ and
the media never came back from a restore that had done nothing wrong. It is a
per-medium check now: refuse bytes only if the session already has bytes, with
the existing name check for identity.

*"Can I spill?" tested for the library, not for IndexedDB.* `lib/draftstore.js`
loads and defines its API whether or not IndexedDB exists -- it reports the
absence by rejecting, asynchronously, long after a strategy has to be chosen. So
a browser with IndexedDB disabled took the spill path anyway, the put rejected,
and a track that would have fit in localStorage came back as "Saved without
media". `verify_fix.py` runs its whole context with `window.indexedDB` undefined
and caught it.

**I nearly broke a correct test.** `verify_fix.py` TEST 3 pins that a track small
enough to fit stays inline in localStorage, and my first move was to rewrite it
as out of date. It was not: that suite deliberately disables IndexedDB, so it is
pinning the FALLBACK contract, which is unchanged and still correct. The test was
restored and its reasoning written into it. The lesson is the general one -- a
test that contradicts a change is a claim to be understood before it is a
blocker to be removed.

**`pendingPhotoMeta` / `pendingMusicMeta` are set only on real failure now.** They
used to be set on every spill, which was right when reaching that code meant the
bytes had been dropped and wrong once it became how media is saved. Nothing
visible depended on it -- every re-add card is guarded by `&& !bgImage` -- but
`serializeFlip()` reads them for `mediaOmitted`, so the record that HAS the bytes
was stamping itself as missing them.

**Still worth doing:** the bytes go to IndexedDB as base64 data URLs, not Blobs.
`draftstore.js` stores Blobs natively, which would drop the 4/3 encoding
overhead, but the whole app handles `bgImage` as a data URL string, so that is a
wider change than this one.

## Each editor script ends by saying it got there

**The most expensive bug in this codebase, measured in debugging rounds, is a
top-level throw in `flip.js`.** The page still renders, the markup is all there,
and an arbitrary SUFFIX of the behaviour is missing -- so it presents as several
unrelated features breaking at once and sends you after whichever one you
noticed first. Four rounds in a single session, every one the same shape: a
function that runs during init reaches a `let` declared further down and hits its
temporal dead zone. `let` and `const` do not hoist the way `function` does, and no
`typeof` guard can rescue them -- only declaration order can.

So `flip.js` and `app.js` each end with one statement whose only job is to prove
they reached it, and `verify_boot.py` reads it. That beats a page-error listener
twice: it also catches a throw something swallowed, and it names WHICH file died
rather than reporting a symptom three screens away. Verified by reintroducing the
bug deliberately -- the suite failed with "Cannot access '__tdzCanary' before
initialization" instead of with a missing filmstrip.

**The rule going in:** state any early path can reach belongs with the early
state; anything touching state declared further down belongs in the load handler.

**A STATIC checker was tried first and thrown away.** A regex pass over `let`
and `const` declarations reported 512 hazards in flip.js and 866 in app.js --
almost all of them property names (`style`, `length`, `width`) and keywords
(`return`, `true`) that regex cannot tell from identifiers, plus declarations
inside function bodies it had no way to scope. Scope analysis needs a real
parser, and the dynamic check is both cheaper and exact: the symptom is always
"the file stopped", which is one boolean to test.

**One footgun found while writing the suite.** `typeof frames !== 'undefined'` is
ALWAYS true in a browser -- `window.frames` is the iframe list. On Flip a real
top-level `let frames` shadows it and the expression worked by luck; on Pad it
resolved to `window.frames[0]` and threw, which the suite then reported as the
boot path failing.

**The suite pins a real difference between the surfaces** rather than flattening
it: Flip restores a draft silently, because it persists pages, media and
background and has nothing to warn about; Pad offers a "Discard / Restore"
banner, because its autosave holds strokes but NOT media bytes and a silent
restore would present a partial drawing as the whole one.

---

# The version log

Everything below is the record, newest at the BOTTOM. Two things about the
headings will otherwise mislead you.

**Version numbers repeat.** The numbering restarted twice in this project's
life, so the log runs v232->v297, then v240->v264, then v255->v272. There are
two `## v272` headings and they are unrelated releases; the same is true of
most numbers in the v240-v297 band. **When a number is ambiguous, the LAST
occurrence in the file is the current one** -- reading order, not search order,
is what disambiguates. Prose elsewhere that cites "DECISIONS v240" was written
when that number meant one thing; date it by the file it sits in, not by a
search hit.

**These entries were true when written and are not maintained afterwards.** An
entry describes the change it shipped with, including code that later moved or
was replaced -- v272's undo rewrite retired a mechanism v213 documents in the
present tense, and v213's entry is not wrong, it is old. START-HERE.md carries
the CURRENT state of the tree; this file carries how it got there and why.

## v232-v233 -- Light mode: opt-in, chrome only, and the half that greys miss

**Light is OPT-IN. There is no `@media (prefers-color-scheme: light)` rule.**
Adding one was the obvious move and it was wrong. It flips the DEFAULT for every
visitor whose OS is set to light -- which is most of them -- on an app whose
entire identity is dark: the palette, both brand marks and the accent purple
were all drawn against a near-black ground. Skribl would have changed for
everyone overnight without anyone asking for it. The rule was written, observed
to flip the harness's own headless Chromium (which reports `light`), and
removed. Following the system is one block away and documented in place above
the light ramp, but it is the owner's call about the product, not a detail of
the implementation. `verify_theme.py` emulates BOTH OS preferences and asserts
the default load is dark under each, because a rule that only misfires under one
of them is exactly what nearly shipped.

**THE CANVAS IS NOT THEMED, and that was the owner's answer to the only
question worth asking before starting.** A drawing's background is part of the
drawing -- it is exported, it is posted, it is what other people see -- so a UI
preference must never repaint it. `#0d0f14` is excluded from the palette and
from both colour ratchets for that reason, and the assertion is a real pixel
read from the middle of the canvas in both themes rather than a CSS value,
because only the bitmap can say whether a token leaked in.

**The theme has to be stamped BEFORE first paint.** The setting lives in
localStorage, which no stylesheet can read, and every script in both templates
is deferred (`verify_surfaces` pins that). Applied by `lib/theme.js`, the
browser paints a dark frame first -- a black flash on every navigation, for the
people who chose light specifically to avoid one. So a tiny inline script in
`<head>` does it, shared as a partial rather than copied into two templates
because the storage key is a contract and a second copy of a contract is a
second thing to drift. The test serves the page with EVERY external script
aborted: if the theme is still right, nothing deferred was needed to get it.

**Phase 1 moved 179 neutral literals into `:root` WITHOUT changing a value, and
that is why phase 2 was a palette rather than an archaeology exercise.** All
nine rendered scenes came back pixel-identical, worst channel delta 0 against a
measured capture-noise floor of 4. Splitting the work that way meant the risky
half was mechanical and provable, and the creative half touched one block.

**Nine surfaces stayed dark after the first pass because they are TRANSLUCENT.**
Phase 1 converted `rgba(255,255,255,a)` only; the header, the page bar, the
filmstrip well, the page-bar buttons and the autosave pill are a dark colour at
partial opacity, which no hex-literal sweep sees. They became RGB-triplet tokens
(`rgba(var(--surface-well-2-rgb), 0.78)`) across 23 call sites. **A luminance
sweep over the rendered chrome is what found them** -- the static audit had
already declared the job done.

**CHROMATIC INK IS THE HALF A GREY AUDIT CANNOT SEE.** Phase 1 moved neutrals,
because greys are what a theme obviously flips, and walked past every coloured
literal. But the danger red, the warn amber and the ok green were every one of
them chosen against a near-black ground: `#f4326f` measures **3.32:1** on the
light menu sheet, below AA for body text, and it is what "Clear all" is written
in. v233 tokenised them at their existing dark values (so dark mode resolves to
exactly the old literals, verified token by token) and restated them darker at
the same hues for light. **The ratchet for ink is stricter than the one for
greys: no literal at all**, with `#fff` (text on a coloured fill, white in both
themes) and `#0d0f14` (the canvas) the only exemptions.

**The legibility threshold is RELATIVE, and getting that wrong cost a round.**
Demanding 4.5:1 of every label failed on `.menu-version` at 4.42 -- the version
footer, deliberately tertiary, and dim in BOTH themes. Passing it would have
meant darkening the upper half of the light text ramp: breaking the mirrored
relationship on purpose to satisfy a number about something this work never
touched. What light mode is answerable for is not regressing, so every element
is measured in both themes -- a 3:1 floor, and a drop fails only if it lands
under AA and loses more than 15%. `#f4326f` went 5.5 -> 3.32, caught twice over.
White on the accent (4.35:1) is printed rather than asserted: it is identical in
both themes and older than this work, so it is a palette question about the
accent, not a theme one.

**The ramp is mirrored by RELATIONSHIP, not by arithmetic.** Inverting each
luminance mechanically gives a light theme where every contrast is technically
preserved and nothing looks right: the darkest surface is the one the eye reads
as furthest back, and in a light interface that is the LIGHTEST. So
`--surface-deep` becomes white and the ramp climbs away from it in the opposite
direction, keeping the cool blue-grey hue (~220deg, low saturation) throughout;
a neutral grey would read as a different product.

**A sweep over a hidden element measures nothing and passes.** The first
legibility pass swept a closed menu, found no neutral-ground text on Flip, and
reported a triumphant 99:1 having measured zero elements. Every sweep now
asserts the COUNT of laid-out elements before trusting its numbers.

**How the ramp is kept from rotting is structural, not a list.** Add a token to
`:root` next month, forget the light value, and that one control keeps its dark
colour while everything around it flips -- silently, and nothing else would
catch it. So the assertion is: every NEUTRAL colour token must be overridden.
That lets the accent family through automatically (it is chromatic and does not
flip by design) along with the radii and easings (not colours), with no
hand-kept exclusion list to fall out of date.

---

## v234 -- The pen palette: one list, and Riso inks instead of the UI accent

**It was two lists.** Seven `<button>`s in `_skribl_draw_drawer.html` for Pad,
and a `COLORS` array at the top of `flip.js` for Flip: the same seven hexes in
the same order, kept in step by hand, with nothing comparing them. The failure
mode of forgetting one is not an error -- it is two editors quietly offering
different colours, which nobody notices until someone switches surfaces
mid-drawing. `lib/palette.js` is the list now, both surfaces build their dots
from it, and `verify_parity` asserts they render the same colours in the same
order AND that what they rendered came from the lib rather than from a copy.

**Building the dots at runtime is what made one list possible.** Pad's click
handler is delegated on `#colorGroup`, so a dot created after load needs no
listener of its own; Flip passes an `onPick` because it also closes the drawer.
The custom picker and the eyedropper stay in the markup -- they are controls,
not colours, and they are what the dots get inserted before.

**The colours are Risograph inks.** Fluorescent pink, hot orange, acid yellow, a
printed green and a federal blue, plus paper white and a toner black -- what
small-press zines are actually printed with. What was there before was a purple
and a blue lifted straight from the UI accent, a mint green and a muddy amber:
**a drawing palette that matches the chrome is a palette that was never chosen.**
Riso inks are spot colours mixed to sit on uncoated paper rather than to pass a
contrast check, so they are strongest on the dark grounds the background
swatches default to. Acid yellow on white is nearly nothing, which is true of
the ink as well.

**The lib says WHICH swatches are dark and deliberately not what colour their
rim is.** A near-black dot on a near-black drawer is an empty hole -- but the
drawer is near-WHITE in light mode, where the dot needs no help and a light rim
would be the thing that vanishes. So `dark: true` becomes `[data-ink="dark"]`
and the rim is a themed token in CSS.

**Every swatch is named now.** Flip labelled its dots with the raw hex, because
it built them itself and had nothing else to hand. "#ff48b0" is not a colour
anyone recognises being read aloud.

## v234 -- What the colour ratchets could not see

**The `rgb()` FUNCTION form.** The neutral ratchet only looked for `#hex`, so
`background: rgb(23, 27, 35)` sat on two controls -- the brush-size tray and a
segmented row -- and stayed dark in light mode with nothing to say so. Found by
looking at a screenshot. The ratchet reads both forms now.

**Marks that are white ON PURPOSE.** `#fff` is exempt from the ink ratchet
because it is nearly always text on a coloured fill, which stays white either
way. Five marks were white against a surface that FLIPS, and simply disappeared
in light mode: the brush-size preview dot, the size-preset dots, the music
playhead, the spinner's leading arc, and the ring around the selected colour
swatch -- which meant the selected colour stopped looking selected. None of the
three ratchets can distinguish those cases from the legitimate ones; they were
found by opening the drawers and looking.

**The lesson, twice in one day:** a static audit tells you what is not a token.
Only a rendered pixel tells you what is the wrong colour. Both passes are
needed, and the rendered one has to open the drawers -- a sweep over a hidden
element measures nothing and passes.

---

## v236 -- Liquify, and why it is not called Smudge

**THE ASK CAME AS A QUESTION: "where is smudge".** It had not been built, and my
first answer was that it could not be -- that smudge is a pixel operation, the
same class as fill and text, and that all three need a new primitive in the
frame format which undo, export, the draft schema and the player would have to
learn. That is true of the USUAL implementation and it is not true of the tool.

**IT SHIPPED AS "SMUDGE" AND WAS RENAMED BEFORE IT REACHED MAIN.** The rename is
the decision worth recording, not a tidy-up. A real smudge is COLOUR TRANSPORT:
Photoshop, Procreate and Krita's Color Smudge engine sample the pixels under the
brush, carry that colour along the drag and blend it down. Blending two colours
and softening a hard edge are precisely what people reach for smudge to do, and
this does NEITHER. The family it actually belongs to is Photoshop's
Liquify > Forward Warp, Procreate's Liquify > Push, and Inkscape's Tweak tool in
"push parts of paths" mode, which displaces path nodes by a distance-weighted
delta exactly as this does.

Keeping the name would have been the cheap option, and it would have made the
control lie about itself: every user arriving with a smudge tool's expectations
would find a tool that never blends and conclude it was broken. **A control that
lies about what it does is worse than one that is merely limited.** Renaming it
also makes a future colour-blending smudge an honest separate feature rather
than a bug report against this one -- and that feature needs a raster layer in
the format, which is still the owner's call.

**AND COLOUR TRANSPORT WAS NEVER AVAILABLE HERE ANYWAY.** Blending needs pixels
to sample and Skribl has none. A page is a list of points, and that same list is
what the player replays, what export walks and what the draft stores.
Rasterising a page to blend it would kill replay outright -- a flattened image
has no stroke order left to animate.

**So this moves the GEOMETRY.** Points inside the brush are dragged along with
the pointer, weighted by distance from its centre, and the strokes bend. For a
line document that is the better instrument anyway: it moves the ink you drew
rather than averaging it into mud, and it is LOSSLESS where a raster smudge is
not -- ten undo/redo round trips come back bit-identical, which no colour smudge
can offer.

**What it costs, stated plainly:** no colour bleed. Two crossing strokes bend
towards each other but never mix, and nothing in this format can make them mix.
**What it keeps** is the entire reason to do it this way: replay, export, the
player, the draft, and an exact undo. `verify_liquify` proves it end to end --
it liquifies a page, POSTS it, and loads the result in the player, which was never
taught about liquify and did not need to be.

**THE FIRST VERSION SPIKED INSTEAD OF SMEARING, and the fix is one constant.**
At full strength a point in the centre of the brush moves the entire delta --
which lands it back in the centre for the next move event, at weight 1 again. It
rides the cursor forever, and every line the brush crosses is dragged to the
same single point. Measured on three parallel lines: all three converged to one
vertex, a hard V rather than a smear. `LIQUIFY_STRENGTH` below 1 makes the ink
LAG behind the brush; lagging, it sits further from the centre; further, its
weight drops; and it sheds off the back on its own. That is what dragging a
finger through wet ink actually does. The suite pins the PROPERTY rather than
the constant: three parallel lines must still be three lines afterwards.

**The falloff is squared, not linear.** Linear reads as a shove -- the whole
disc lurches and the rim of the brush leaves a visible crease across the stroke.
Squaring pulls the centre along and lets the rim off almost untouched.

**Undo stores COORDINATES, not a displacement**, for the reason selRestore's
comment already gives: a liquify stroke accumulates over dozens of move events at a
different weight each time, so there is no single delta to negate, and
re-deriving one would walk the artwork further from home on every cycle. Ten
undo/redo round trips are asserted bit-identical.

**A liquify stroke belongs to the page it STARTED on.** The frame index is pinned at
pointerdown, exactly as `strokeFrame` is for a stroke -- the same trap, in the
same file, for the same reason. Changing page mid-drag and re-reading `frame()`
would apply the back half of the gesture to different artwork at indices that
mean something else there, and hand undo a before/after pair for strokes nobody
touched.

**A tap logs nothing, and neither does a drag across empty canvas.** A no-op on
the history puts the stroke the user actually wants back one press further away
than they expect.

**The reach ring is dashed and the reach is wider than the brush paints.** A
solid ring that size would read as a colossal brush about to lay ink; dashed
says influence. Reach is tied to the brush slider, so the tool needs no control
of its own -- the row is already full, and "the size you draw with is the size
you push with" is one less thing to explain.

**THE TRAY EARNED ITS KEEP A SECOND TIME.** Liquify is the fifth tool and the row
did not have to be re-fitted for it, exactly as the tray was built to allow.
That is now two features that cost nothing in layout.

## v236 -- A setup step that quietly does nothing is worse than one that fails

`verify_liquify`'s `fresh()` reset the document but not the TOOL. A section that
left liquify selected made the next section's setup silently draw nothing --
`line()` liquified an empty page instead of drawing on it -- and three assertions
downstream then passed or failed for reasons that had nothing to do with what
they named. One of them passed VACUOUSLY: "undo restores the exact coordinates"
compared an untouched page against itself and reported 0 points differing.

Two changes, both of which belong in any suite that builds its own fixtures:
`fresh()` restores the pen and ASSERTS it, and `line()` asserts that the stroke
count actually went up. The suite is allowed to fail; it is not allowed to
measure the wrong thing and call it a pass.

---

## v237 -- The in-between, and what the reference photograph was actually showing

**THE OWNER ASKED FOR A REAL SMUDGE, "used to simulate motion", and then sent a
stop-motion reference:** three frames of a wire puppet, the middle one blurred.
Reading that photograph properly is what produced this feature, and my earlier
answers had all been aimed at the wrong target.

What sells that middle frame is NOT blur. It is that the blur is UNEVEN -- the
feet, which barely travelled, are nearly sharp; the arms, which swung furthest,
smear away to nothing. It is one long exposure integrating the path between two
poses, and the sharpness gradient IS the motion information.

**That is why it can be done honestly in a stroke document.** Sample the motion
between two pages at N steps and draw every step faintly. A point that hardly
moves lays all N of its copies on top of each other and stays crisp; a point
that travels far spreads them along its path and goes soft. Nobody authors the
falloff -- it is what integrating a motion MEANS. Measured in the suite: the arm
tip spans 150px across the exposure and the foot spans 2px.

**NO FORMAT CHANGE AT ALL, which is the part I got wrong three times before
getting right.** I said blur needed a raster layer; then that it needed a render
attribute the player must learn. Neither is true of THIS. Opacity already rides
inside each point's rgba() and the player already honours it, so an exposure is
just strokes -- editable, erasable, exportable, postable, replayed in order like
anything else. The player was never told about it and did not need to be.

**The blur is still available and still a decision.** ctx.filter carries a real
gaussian and it works in this engine (measured). 26 samples unblurred is most of
the way to the photograph; the faint ribbing left over reads as a DRAWN
in-between rather than a photographic one, which suits an app that looks like a
printed zine. Adding the gaussian means a render attribute the PLAYER has to
honour -- the same trap the `pressure` note records -- so it waits for the owner
to see this in the app first.

**THE POINT BUDGET IS THE HAZARD, again.** Multiplying a page by 27 is exactly
how a feature makes a drawing unpostable: the server refuses a frame over 20,000
points, and it would refuse at the moment the user tried to share, with no
earlier warning. N adapts -- a 900-point page that would have produced 24,300
points produces 14,400 instead. Third feature in a row where the cap was the
thing that needed designing around rather than discovering.

**It refuses rather than guessing.** Interpolation needs corresponding strokes,
which Duplicate-then-drag produces and two freehand redraws do not. Inventing a
pairing would produce a mess that reads as a bug in the tool rather than a limit
of the idea, so it says "An in-between needs the same strokes on both".

## v237 -- "Page 21 / 43" was clipping the Delete button

The counter cost 69px against 30px for "21/43", in a `nowrap` bar whose contents
already measured **369px inside 340** at a 360px viewport. The last button was
being cut off, and had been for some time -- found while answering the owner's
question about whether there was room for a new button, which there was, because
the new button is in the FILMSTRIP and never competed with this bar at all.

In a bar whose every other control is a page operation, directly above a
filmstrip of numbered pages, "Page" was spending real estate to say what the
context already said.

**The accessible name keeps the full sentence** (`aria-label="Page 21 of 43"`).
An abbreviation may shorten how a control LOOKS; it may never shorten its
accessible name. Both halves are asserted, so a later tidy-up cannot drop the
spoken one -- and verify_pages, which asserted `"Page " in textContent`, now
asserts the INTENT (a digit on screen, "Page" in the accessible name) rather
than the wording. A test that contradicts a change is a claim to be understood
before it is a blocker to be edited.

---

## v238 -- The autosave pill fades where it would cover a control

**It sat on the pen button, on every phone size, on both surfaces.**
`.autosave-status` is position:fixed at bottom-left and on a phone the tool row
is at the bottom too. Desktop never collides -- which is exactly why it lasted:
IT IS INVISIBLE ON THE MACHINE IT WAS BUILT ON.

**A rule for a nearby case already existed** and had the right instinct: the
pill fades while a drawer is open, because "a pill covering a destructive button
is worse than one you cannot see". It fixed the collision somebody noticed
rather than the general one. CSS cannot ask whether two boxes intersect, so the
general case needed measuring, and lib/pillfit.js measures it.

**A WARNING IS NEVER FADED.** `failed` and `partial` stay on screen deliberately
-- flip.js records why: "a warning that fades claims it was resolved". Fading one
because it happened to overlap would trade a cosmetic problem for a durability
one, silently, in the exact situation where the user most needs telling. The
overlap rule applies to the reassuring states only, and most of
verify_pillfit.py is spent on that distinction rather than on the easy half.

**The pill was already pointer-events:none**, so none of this was ever about
blocking taps -- it obscures a control without disabling it. Worth establishing
before weighing the fix, and asserted so a later change cannot make the pill
interactive and turn an overlap into a dead button.

**THE CONSEQUENCE, STATED RATHER THAN DISCOVERED LATER: "Saved" no longer
appears on a phone at all.** The owner chose fading over moving it, and on a
phone the overlap is permanent rather than occasional -- so this is a change
from "visible and in the way" to "not shown". The states that actually need
reading still show everywhere. If the reassurance turns out to be wanted on
mobile, the answer is to give the pill somewhere to go, not to weaken the rule
about warnings.

**Shared, not written twice.** Both editors show the same pill from their own
showAutosaveStatus(), and verify_surfaces counts the names those two files define
in common -- so this is a lib rather than a function added to each. The player
has no autosave and does not load it.

---

## v239 -- The in-between stalled playback, and the fix was the colour FORM

**REPORTED FROM A PHONE, on work that had already shipped to main: "it takes 2
seconds to play 3 frames".** The in-between rendered, but it could not be
played, which for an animation tool is most of the point.

**The cause.** paintStatic gives every translucent stroke its own offscreen
layer -- clear a full canvas, redraw, composite it back -- so that a see-through
stroke does not bead at its own overlaps. That is right for a stroke somebody
drew. An exposure is 27 samples of EVERY stroke, so a six-limb figure is 162
translucent strokes and roughly 486 full-canvas operations per frame. Measured:
**221 ms to render one in-between against a 12 fps budget of 83 ms**, and worse
on a denser drawing -- the owner's was worse. render() is synchronous and runs
before the next frame's timer is armed, so the PREVIOUS frame sits on screen for
the duration. That is why the stall appeared on the page before the in-between
as well as on it, which is exactly how it was reported and is the detail that
identified the mechanism.

**AND THE LAYERING WAS WRONG FOR THIS CONTENT ANYWAY.** It exists to stop a
stroke compounding at its own overlaps. An exposure IS compounding overlaps --
the density where samples pile up is the effect.

**Two fixes were tried and rejected before the right one.** Opaque samples on a
brightness ramp: 40x faster and it looks like a solid white wedge, because
opaque strokes cover rather than accumulate. Fewer samples: the cost is per
STROKE, so a six-limb figure would need about three samples to fit the budget,
which is three copies rather than a smear.

**THE FIX IS THE COLOUR FORM.** Both renderers decide whether to layer by
matching the rgba() FUNCTION form -- alphaOf here, parseStrokeAlpha in app.js,
which is also the player's renderer -- and neither matches an 8-digit hex.
Canvas honours #rrggbbaa and accumulates it either way (verified: two passes of
#ffffff21 over black give 33 then 61). **221 ms -> 5.8 ms, the same picture**
(+3.3% ink mass from the extra intra-stroke accumulation, median pixel delta 3),
with NO new field, NO renderer edit, and NOTHING for the player to learn.

**This is why it was worth looking again rather than asking.** The fix I had
lined up needed a per-stroke marker both renderers would have to honour -- the
format contract the owner has repeatedly reserved. Being pushed to find a
cheaper answer produced one that needs no decision at all. A format change is a
last resort, and "I cannot see another way" is not the same as "there is none".

**The assertion is on the COST, not on the colour string.** Teaching alphaOf to
understand hex would make exposures slow again -- not broken, just slow, which
is the kind of regression that ships. A cost budget catches that; a test on the
string would not, because the string could stay the same while the heuristic
around it changed.

---

## v240 -- A fix that only applies to NEW data is half a fix

**Reported a second time, from the same phone, after the first fix had shipped:
"it still pausing on the blurred slides".** v239 wrote the fade as an 8-digit
hex so the renderer would stop giving every sample its own full-canvas layer.
That was the right diagnosis and the right mechanism -- and it changed the
GENERATOR only. Every in-between already saved in a draft still carried rgba()
and still cost 218 ms. Measured side by side on one page: 5.2 ms as hex, 218.4
ms after rewriting the same colours back to rgba().

**I shipped it, verified it on a page I had just generated, and called it
fixed.** The verification was real and the sample was wrong: the only pages that
could show the bug were the ones that already existed, and I tested a new one.

paintStatic now carries a COST CEILING. Layering costs a full-canvas round trip
per translucent stroke -- about 1.4 ms at 816x612 -- so a frame holding more
than a frame-budget's worth of them paints direct. Old pages 218 ms -> 5.1 ms.
It covers pages saved before v239, hand-edited pages, and any future content
heavy enough to stall, none of which a generator-side fix can reach.

**The ceiling is a ceiling, not a ban**, and the suite asserts both halves: an
old-format in-between must render fast, AND a hand-drawn frame with six
see-through strokes must still get its layers. A guard that silently stopped
compositing ordinary painting would be a worse bug than the one it fixed.

**The habit worth keeping:** when a fix changes how data is WRITTEN, ask what
happens to the data already written. The people most likely to hit the bug again
are exactly the ones who hit it the first time, because they are the ones with
the old data.

---

## v241 -- Page holds were saved and then silently thrown away on load

**Found by hand, generating a demo file.** Three key poses were set to a x2 hold
so they would sit a beat either side of each in-between smear. The .skribl
contained `hold: [2, null, 2, null, 2]` -- serializeFlip writes it correctly --
and after loading, every page was back at 1.

applyPayload rebuilds each current-format frame through healFrame, and all four
of its return paths produced `{strokes, strokeGroups}`. The hold was read out of
nothing and dropped on the floor. **The same path restores the AUTOSAVE**, so a
hold did not survive an ordinary reload either -- set a page to x3, come back
tomorrow, and the timing is gone with nothing to say so.

**WHY verify_hold DID NOT CATCH IT, which is the useful part.** That suite has
thirty-odd assertions and every one of them is about WRITING: the badge appears,
the payload gains a `hold` key, unheld pages stay absent, copy/paste carries it,
the exported GIF has the right frame delays. Not one asked whether a hold comes
BACK. The feature was verified in the direction it worked.

The new assertion is a genuine round trip -- serialise, WIPE the live state,
load it back, read the hold off the restored frames. Verified by removing the
fix: it reports [1, 1, 1, 1] while the other 38 assertions stay green, which is
exactly how the bug survived.

**The pattern, twice in two days:** verify_tween proved an in-between was
correct and never asked whether it was fast enough to play; verify_hold proved a
hold was written and never asked whether it was read. **A suite that only tests
the direction a feature works will pass forever while the feature is broken.**
When something is written, test that it comes back. When something is drawn,
test that it can be played.

## v242 -- The blur inflated big objects, and nobody had measured a big object

Reported as "that looks terrible", with screenshots of a bouncing ball. It was.

The blur's halo was a MULTIPLE of the brush -- the widest pass 3.4x. On the 6px
stroke every earlier measurement used, that is a 7px soft edge and it looks
right. On a 60px ball it is a 204px cloud: the ball INFLATES instead of
smearing, and reads as a lumpy blob rather than something moving fast.

**Only one brush size was ever checked, and it was the size that hides the
defect.** verify_tween had eleven assertions about the blur and every one of
them passed while objects were being fattened by 288px, because they all asked
WHETHER there was a falloff and none asked how wide it got RELATIVE to what was
being blurred. The new checks span 8 to 120px.

The model was wrong, not just the constant. Motion blur does not fatten an
object: it smears it ALONG its travel -- which the sample sequence already did,
and which was never the problem -- and leaves the edge ACROSS the travel nearly
sharp. So the halo is a small bounded softness ADDED to the brush, and
smoothness along the path comes from sample COUNT, not from halo width.

## v243 -- A blur pass cannot carry a colour it has no bits for

Found while making a demo: an orange ball grew a RED halo. Measured off the
canvas rather than guessed -- a plain ball reads (255,176,32), the same ball
blurred peaked at (240,134,2). The blue was not dimmed. It was gone.

Canvas composites through PREMULTIPLIED 8-bit alpha: a channel is stored as
round(channel * alpha). A halo pass at alpha 2/255 turns #ffb020's blue (32)
into round(0.25) = 0 before any compositing happens. Same mechanism dashed a
static ground line drawn inside a tween: #5b6472 at alpha 1/255 premultiplies to
(0,0,0) and contributes nothing at all.

Measured across three inks at nine alphas: hue holds from about
`darkest_channel * alpha >= 1.2` and is visibly wrong below it -- and **alpha
1/255 is wrong for every ink, including near-white.** Which pass survives
therefore depends on the drawing, so the test is per-frame.

The fix sheds passes the ink cannot colour, always keeping the core. A
saturated ink gets a sharper exposure; a pale one keeps the full falloff.
Coarsening the exposure instead would have traded smoothness for colour on
every page, including the ones with no problem.

**Why every earlier measurement missed it:** they all used white or near-white
ink, whose channels are equal and high, and which is the one case where
premultiplied rounding cannot shift a hue. The test that would have caught it is
the one that varies the input along the axis the code is sensitive to -- here,
saturation -- rather than the axis that is convenient to draw.

## v244 -- Verified standalone is not verified in place

run275 failed on verify_hold with "Event loop is closed! Is Playwright already
stopped?". The new block called `br.new_page()`, but `br` belonged to a
sync_playwright() context that had exited long before.

The block had been checked standalone, in a script that opened its OWN
Playwright context -- an arrangement where that bug cannot exist. Passing in
isolation said nothing about passing in place, and it was taken as evidence for
both. A full sweep was spent finding out.

`run_harness.sh` takes a suite name as an argument, so checking one suite where
it actually lives costs about a minute. **Extracting code to test it changes the
thing being tested.** Run it where it will run.

## v245 -- An eraser takes away whatever is under it

The first pass at a drawn-in-Pad demo put a mistake-and-erase late in the
sequence, so the scrub went through finished artwork down to the paper and left
a white band across the face. Obvious once seen, and not obvious while writing
it: the mental model was "undo the wrong stroke", but an eraser is not undo.

Mistakes in a replay demo belong in the layer that is still on top -- during
construction, before anything is painted over them.

## v246 -- A warning is the wrong instrument when the safe state is "did not notice"

`current_user_id` without a CSRF verifier logged a warning, on the reasoning
that a bearer-token host does not need CSRF and should not be refused. The
reasoning was right and the mechanism was wrong. The failure mode is "any
third-party page can post as your logged-in user"; the warning went to a logger
the host may never have configured, at import time, in a stream nobody reads
during a deploy. The state you got by not noticing was the unsafe one.

It refuses now. **What makes refusing acceptable is that there is an explicit
declaration for the legitimate case** -- `csrf=False`, meaning "my
authentication is not cookie-based". Without that opt-out the refusal would be
punishing a correct configuration, which is how a hard error earns a reputation
for being wrong and gets worked around.

The rule generalises: a warning is right when the reader can act on it and the
default is safe. When the default is unsafe, the choice is refuse-with-an-
opt-out, not warn.

## v247 -- A number stated three times is stated zero times

Title and caption lengths lived in three places: `String(80)`/`String(300)` on
the columns, `[:80]`/`[:300]` truncating in the create endpoint, and
`maxlength="60"`/`"280"` in both editors. No two agreed, and an earlier session
had written a harness block headed "280 and 300 are different numbers ON
PURPOSE" -- pinning the drift as if it were a design.

It was not a design. A caption of 290 could not be typed into the editor but
posted fine; one of 350 came back **201** with fifty characters silently gone.

**OWNER, FLAGGED:** this reverses that earlier decision, and two assertions in
`verify_apiedges.py` were removed rather than adjusted, because what they
asserted was the drift. There is one constant per field in `core.py` now; the
columns are declared from it, the endpoint rejects with a 400 naming the limit,
and the templates render `maxlength` from it through the context processor.

The general form: when the same fact appears in N places, N-1 of them are
documentation of the other one, and only the one that can refuse is real.

## v248 -- A cap on bytes is not a cap on cost

Media validation proved the declared type matched the leading bytes and that the
base64 was under a size cap. Neither says anything about what decoding costs. A
66-byte PNG whose IHDR declares 30000x30000 passed everything, and every browser
that opened the post then allocated about 3.6 GB.

Bytes cannot be a proxy for decode cost, because the entire point of a
decompression bomb is that it is small. The dimensions are in the header of all
four accepted formats, so they read without a decoder and without a dependency.

Two choices inside it worth keeping. **An unparseable header ACCEPTS** -- a file
that will not parse does not decode either, and rejecting on "unparseable" turns
every rare corner of these formats into a 400 for no gain. And **the parser must
not become the attack** -- the JPEG segment walk is bounded by segment count and
byte offset, or a crafted file makes the scan itself the denial of service.

## v249 -- A maintenance function nothing can run is a maintenance plan, not a job

`sweep_orphans` reclaimed disk since v180 and was documented as the answer to
orphaned media. Nothing shipped could invoke it. Every deployment was left to
resolve its own app, find the store the host passed in, get a session, and get
the argument order right on a function whose third positional argument deletes
user data.

It was also unobservable: returning only the removed keys meant a run that
removed nothing looked identical whether there was nothing to reclaim, the
credentials were pointed at the wrong prefix, or the grace period was swallowing
everything. Every branch that DECLINES to delete is now counted separately,
which is what makes a zero interpretable.

And it was fragile: `delete_key` ran uncaught, so one object a bucket policy
refuses aborted the run and left every later orphan in place -- while the key
was already in the returned list, reporting a deletion that never happened.

The test for "is this operable" is not "does the function work". It is: can
someone schedule it, can they tell what it did, and does it survive one object
going wrong.

## v250 -- A number that goes stale is caught; a sentence that goes stale is not

`verify_docs.py` has guarded this project's volatile facts for many releases:
suite counts, file counts, assertion totals, tree hashes, version strings. Every
one of them is a NUMBER, and numbers are what it can compare.

It never occurred to anyone -- me included -- that the same rot happens to
prose, and prose is what people actually act on. `FOR-THE-REVIEWER.md` called
durable drafts and pointer identity "NOT deferrable prerequisites" two releases
after both shipped. `DESIGN-DIRECTION.md` stated the draft problem as current.
`START-HERE.md` said Pad's autosave "holds strokes but not media bytes" seven
hundred lines above its own paragraph explaining that the bytes go to IndexedDB.
A 3,328-assertion harness saw none of it.

**The cost was not embarrassment, it was a reviewer's time.** An outside review
of v224 read a stale docstring in `models.py` claiming the database limiter was
"NOT yet verified on PostgreSQL across processes" and filed a MEDIUM finding
asking for a test `verify_postgres.py` had been running since v211 -- four
gunicorn worker processes, twelve barrier-released requests, quota two. The same
docstring also denied that any advisory lock existed while `ratelimit.py` runs
`pg_advisory_xact_lock` on every reservation, so it UNDERSTATED a
security-relevant guarantee. Stale prose does not merely mislead a reader; it
spends the attention of the one person paid to find real problems.

The gate now pairs a capability with the artifact that PROVES it shipped and the
phrasings that would only appear if it had not. Two design choices are the
useful part. It scans SOURCE FILES as well as documents, because the finding
came from a docstring and code comments are read more literally than prose, not
less -- and that extension immediately found two more instances nobody had
reported. And its exemption list is a small CLOSED set of explicit markers, so a
changelog can still say what used to be true and adding an escape hatch is a
decision rather than a slide.

Stated in the code, because overclaiming here would be the same sin: it catches
denials it has PATTERNS for. A newly-invented stale sentence sails through
exactly as before.

## v251 -- Saying a fix is untested is not a substitute for testing it

The Air-brush beading fix shipped with an honest note in the reviewer document:
the mechanism was verified synthetically, the owner confirmed it by eye, and
**it is not pinned by an assertion**. That disclosure felt like diligence. The
v224 outside review ranked it as the second-most-important finding, and was
right to: an unpinned rendering fix is one refactor away from silently
returning, and the honesty in the document does nothing to stop that.

Why nothing else could see it: the STROKES ARE BYTE-IDENTICAL before and after
the repaint. It is not a geometry change, not a structural one, not a data one.
Only the pixels differ, and no suite here read pixels for this.

Two things about measuring it are worth keeping. **Read the alpha channel, not
the colour channels.** The canvas is transparent-backed -- the dark ground is
CSS behind it -- so `getImageData` returns STRAIGHT, un-premultiplied RGBA, and
a 22%-alpha white stroke reads r=255, a=56. The first draft measured red and
reported a spread of zero on a visibly correct stroke. That is the third time
this project has met premultiplied-vs-straight alpha in a new disguise. And
**exclude what is not ink**: a marquee paints a purple outline, and counting it
reported a spread of 138 for a repaint that was perfect.

The mutation is what makes the suite worth anything. It repaints through the raw
painters -- the pre-fix code path -- and REQUIRES the result to come back worse.
Composited mean alpha 51, raw 118. Without that, every other assertion could
pass on a canvas that never repainted at all.

## v252 -- "Sealed" is corruption detection, not provenance

`SHA256SUMS` lives inside the archive it authenticates, and so does the tree hash
in `RELEASE.md`. Anyone who can replace the archive can replace both. The v224
review said so and it is correct: the seal proves this archive is internally
consistent and the evidence describes this tree. It proves nothing about who
built it.

The honest fix available here is to publish the hash of the ZIP through a channel
that did not travel with the zip -- the git commit that seals each release. A
signed tag or a CI attestation would be stronger, and neither exists. The
documents now say which of those is true rather than letting "sealed" imply the
stronger one.

## v253 -- Evidence that does not name its own coverage invites a false finding

`RELEASE.md` recorded `skipped 1 (verify_mp4.py)` and stopped there. The v224
reviewer filed that as an open gap and recommended a CI lane with real H.264 --
which `.github/workflows/harness.yml` has run since v103, and which FAILS if the
suite merely skips. **The lane was shipping inside the archive under review.**

The finding was not careless; the evidence simply never pointed at the thing that
closed the gap, and a reviewer is not obliged to go looking for it. `RELEASE.md`
now prints, beside each skip, the CI job that covers it or the words NOT COVERED
-- generated from a table, never typed -- and `verify_docs.py` checks that each
named job really exists in the workflow and really invokes that suite, so the
sentence cannot outlive the lane.

## v254 -- A control belongs where its OBJECT is, not where its neighbours are

Flip's page bar held six controls. Five acted on a page; the sixth, "Move
artwork", moved the DRAWING. It had sat there since v124 for one reason: it was
added at the same time as the others, and a row already existed.

Nothing about it fitted. It takes a drag on the canvas, it has a mode, it
disables the strip while it runs, and it sits beside Select and Liquify in every
respect except where it was filed. It is now a tool in the tool shelf, which
cost a registry entry, a `setTool` branch, and one flagged ratchet edit in
`verify_tray.py` -- the roster there is deliberately exact so that a change to
what the product IS costs somebody a deliberate line.

**⚑ OWNER, FLAGGED:** that ratchet now reads six tools for Flip. Read it as a
control moving house, not as a new tool.

One bug fell out of the move and is worth recording, because it is the shape
these always take. `setTool` ended with `pad.style.cursor='none'` for the custom
brush cursor -- unconditional, and correct for every tool that existed when it
was written. Entering Artwork through `setTool` meant `setMoveMode` set the grab
cursor and then, four lines later in the same function, the old line wiped it:
the mode was live and the canvas did not say so. **Moving a feature into a
shared code path subjects it to every unconditional line already in that path.**

## v255 -- The badge was already drawn; it just was not a control

The page bar's ×hold button cycled a value that the filmstrip was ALREADY
displaying, on the tile it applied to. Two pieces of interface for one fact,
and the one that was better positioned was the one you could not press.

Making the badge the control removed the button. The only real design question
was what to do at hold = 1, where the badge did not render at all -- which is
why the button had to exist, since there was no way to START a hold from the
strip. It renders always now, and CSS hides the ×1 state unless the tile is
active, hovered or focused: exactly the rule the delete ✕ on the same tile
already followed. One idea about when per-tile controls exist, instead of two.

`focus-within` rather than `:hover` alone, because a control that appears only
under a pointer is a control keyboard users do not have.

The same reasoning retired the Paste button. A button in the add column could
say WHAT but not WHERE -- "after the current page" was a rule you had to know.
A dashed ghost tile standing in the gap the pages will fill says both at once,
and disappears with the clipboard.

## v256 -- Hover was spending the brand colour

`.pb:hover` tinted 16% violet and pulled its border to the accent. So did
`.addbtn:hover`. Six controls above a filmstrip, each lighting up in the one
colour the design direction wants spent almost nowhere, so that POST reads as
electricity.

Hover means "this is live", and a neutral lift says that. The accent is kept for
`:focus-visible`, where it is doing work no other signal does. The labels also
moved from `--text-primary`/600 to `--text-secondary`/500: chrome around
artwork should sit under it, and six full-contrast labels above a strip whose
job is to show DRAWINGS read as six things demanding attention.

Geometry was deliberately NOT touched -- 38px, 9px radius, and the invisible
44pt tap expander all stay. `.pb` is "labelled pill = named action" in the
documented shape language (DECISIONS #5) and its radius is not a tone question.

## v257 -- A refactor that moves the boundary is not a refactor

Flip's stylesheet carried eight `max-width` rules -- 359, 360, 392, 400, 440,
559, 560, 640 -- and styles.css had its own set. Not a responsive design: eight
patches, each correct on the day it was written, none of them agreeing about
where "small" begins. The measured cost is in this project's own review notes:
one pixel of resize takes Pad's toolbar from 398px to 565px, and 560-640px gets
the phone layout on a viewport with room to spare.

`lib/sizeclass.js` is the one decision those rules migrate onto. **What is worth
recording is the mistake made building it.**

The first version measured the ROOT ELEMENT rather than the viewport, on a good
argument: what every one of those rules actually wants to know is whether THIS
app has room, and Skribl is a blueprint a host mounts, possibly beside its own
chrome. But `getBoundingClientRect()` excludes the scrollbar, so a 641px viewport
measured ~626 and classified COMPACT where the media query it replaced said
regular. **The boundary moved by fifteen pixels inside a change announced as a
no-op.** The suite caught it because the no-op claim was the thing it was
pointed at hardest -- an assertion at 640 and another at 641, either side of one
pixel.

It measures `window.innerWidth` now, which is what the CSS `width` feature uses,
scrollbar included. Container-awareness is still the better long-run answer and
is recorded in the file as a BEHAVIOUR CHANGE to be taken deliberately once the
rules have moved, with the layout suite re-measured -- not slipped in on the way
past.

The general form, and this session has now produced it twice in two different
disguises: **when a change is sold as structural, the assertion that earns its
keep is the one that would fail if it were not.** Everything else in that suite
would have passed with the boundary in the wrong place.

## v258 -- Say what did NOT move

`verify_sizeclass.py` asserts that fourteen `max-width` queries REMAIN in
flip.css. That looks like an odd thing to test until you ask what the suite is
for: this step was announced as "replace the eight breakpoints" and delivered as
"add the class and migrate one as proof". Those are different sizes of work, and
the difference is exactly the kind that gets quietly forgotten between sessions.

An assertion that names the remaining work makes the narrowing permanent and
visible instead of conversational. It will fail, deliberately, when someone
finishes the migration -- and finishing it should cost a deliberate edit here,
the same way `verify_tray`'s exact tool roster does.

## v259 -- The host column is the case that decides how "small" is measured

**⚑ OWNER INPUT, and it reversed a decision made one release earlier.** The
social site reserves a COLUMN for Pad and Flip -- **around 510px, to be
confirmed by the owner.**

v257 chose to measure `window.innerWidth`, because the claim being made at the
time was that migrating a rule off `max-width: 640px` onto a size class was a
no-op, and innerWidth is what the CSS `width` feature uses. That was right for
that claim. It is wrong for the product.

A 510px column inside a 1400px window measures 1400 by the viewport and 510 by
the element. Viewport measurement therefore classifies the app REGULAR and lays
a persistent command row into a space that cannot hold one -- wrong in the
primary embedding, and wrong in the direction that breaks the layout rather than
the direction that wastes space. It measures the element now.

What that costs is asserted rather than discovered: `getBoundingClientRect()`
excludes the scrollbar, so a standalone window between about 641 and 655 now
classifies compact where a media query would say regular. Inside that band the
one migrated rule and the fourteen unmigrated queries disagree. **That is an
argument for finishing the migration, not for measuring the wrong thing in the
meantime.**

**STILL TO DISCUSS, once the owner confirms the number.** If the column really
is ~510px then Skribl inside the host is ALWAYS compact and never sees the
regular surface at all -- the persistent command row would exist only in the
standalone app. Two things follow, and both are the owner's call:

  * **Is 640 the right threshold for a column?** It was inherited from the
    existing breakpoints, which were written about phone viewports. A column has
    different arithmetic: no browser chrome, no address bar, and a known width.
  * **Is a second breakpoint worth having between 510 and 640?** A ~510 column
    is not a phone. It has a mouse, hover, and a keyboard, and it can afford
    controls a 360px phone cannot even if it cannot afford the full row. The
    compact/regular pair may want to become compact/column/regular -- which is
    a real design question and should not be answered by whoever next touches
    a stylesheet.

Nothing here should be built until the width is confirmed. `SkriblSize.COMPACT_MAX`
is one constant in one file precisely so that changing the answer is one edit.

## v260 -- Stage 4 shipped because its condition was met, not because it looked good

The compact surface drops the page bar for a ⋯ on the active tile. The design
note set one gate on this and it was not visual: **every operation must stay
reachable and announced**, because a filmstrip you can only operate by dragging
is a filmstrip some people cannot operate at all.

So the trigger is a real button with `aria-haspopup` on a tile in the tab order,
opening a `role="menu"` of real buttons; focus moves in on open, arrows walk it,
Escape returns focus to the trigger, and the items are no smaller than the `.pb`
buttons they replace. Each of those is an assertion, not a description. There is
also one proving the REGULAR surface was untouched -- **a change scoped to one
surface is only correct if it left the other alone**, and nothing else would
have caught it if stage 4 had quietly hidden the desktop row too.

The visible scope goes in `aria-label`, not `title`: `lib/tooltip.js` adopts
every `[title]` into `data-tip` and REMOVES the attribute so a styled tooltip can
replace the native one. A screen reader hears "Move these 3 pages left" while
the menu still reads "Move left".

## v261 -- Removing a surface makes the rules that styled it unreachable

Stage 4 hides the page bar on compact. Compact is every width at or below 640 --
which is every width the `.pb-tx` label-hiding rules applied to. **The bar is
therefore never icon-only any more, and those rules are dead.**

verify_hold had a whole section built on that premise: it ran at a 390px
viewport precisely because the labels were hidden there. After stage 4 that
section measured a bar inside a `display:none` ancestor, and `querySelector`
finds hidden markup perfectly well -- so most of its assertions kept PASSING,
vacuously, and only the one that asked about LAYOUT (`offsetParent`) noticed
anything had changed.

That is the failure mode this project keeps meeting from new angles: a test that
reads structure passes forever after the structure stops being rendered. The
section runs at a regular width now, asserts the compact half explicitly, and
says in a comment that the premise inverted rather than quietly reversing it.

The dead CSS is FLAGGED, not removed -- it goes with the rest of the breakpoint
migration, not piecemeal.

## v262 -- Removing a surface silently retires the assertions about it

Stage 4 hid the page bar on compact. Three suites then had assertions that no
longer meant anything, and only ONE of them failed.

`verify_tips` clicked `#pbLeft` at 390px and crashed on an invisible element --
loud, obvious, fixed in a minute. `verify_hold` measured the bar's glyphs at
390px and mostly kept PASSING, because `querySelector` finds hidden markup
perfectly well; only its one `offsetParent` assertion noticed. And `verify_move`
asserted at 393px that entering move mode "replaces the page bar, not adds to
it" -- which stayed green while proving nothing, because the bar was already
`display:none` before the mode started.

That last one is the sharpest version. Its own comment, four lines above, warns
that the assertion had previously passed for four versions against a visibly
broken surface "because it asked the DOM what it had been told, not what it
drew". It was rewritten to measure layout. **Measuring layout was not enough**:
once the element is unconditionally hidden, a layout assertion about it is
vacuous too. The claim needed a width where the bar exists, so it now has its
own page at 1100px, and the 393px section asserts the thing that is meaningful
there -- that the move bar appeared.

**The rule this arc adds: when a surface stops rendering, grep for every suite
that names it.** Not for the ones that fail -- the failures find themselves. For
the ones that keep passing.

Practically: `grep` the suites for the ids of anything removed, cross-referenced
against the viewport widths each file uses. Three suites named page-bar ids at
compact widths here; one crashed and two went quiet.

## v263 -- Adding a prefix to a selector is a specificity change first

Finishing the size-class migration meant putting `[data-size="compact"]` in
front of rules that already existed. That reads like a scoping change. It is
first of all a **specificity** change: `.flip-tools` is (0,1,0) and
`[data-size="compact"] .flip-tools` is (0,2,0), and every rule the original lost
to, the prefixed one now beats.

`flip.css` is exactly the file where that matters, and it knew it. Its own
comment at the max-640 block reads: *"This block is LATER IN THE FILE than the
max-560 and max-392 tiers above at equal specificity, so it wins on source order
-- which is why the row's phone gap, padding and group margins are declared here
and not up there with the widths. Moving them loses them silently; that is
exactly how the old max-380 tier's gap came to be dead code."*

So the ladder is held together by source order among rules that are all
(0,1,0). Prefixing the boundary rules lifts them out of that contest and they
win at every width. **Measured, not reasoned: the 320px tier's gap went 2px ->
3px** -- a phone regression, inside a change whose entire claim was "no-op".

The fix is `:where()`, which contributes zero specificity, so source order still
decides. The mutation is in `verify_sizeclass`: strip the `:where` and the 320px
assertion fails. That mutation is the point -- without it the `:where` looks
like a stylistic tic and the next person deletes it.

**The general rule: before prefixing an existing selector, ask what it currently
LOSES to.** If the answer is "rules at equal specificity, decided by order",
a prefix is a rewrite of the cascade and `:where()` is how you avoid it.

## v264 -- A progress counter is not an invariant

`verify_sizeclass` asserted `left > 0`: some `max-width` queries still exist.
The comment beside it was honest about why -- asserting their absence would fail
for the honest reason that the migration was incremental.

It was still the wrong assertion, and it stayed green through a real defect. It
is equally true of a migration 1/8 done and 7/8 done, so it measures **how far
along** the work is, and nobody was in doubt about that. What it could not see
is whether the queries left behind **disagreed** with the class -- and they did.
The class measured the element, the queries measured the viewport, and from 641
to 660 viewport px the page bar was hidden while the tool row kept its 44px
desktop sizing: the compact surface wearing the regular toolbar, shipped in
v227, with a passing suite.

The replacement is structural rather than a count: **no width query may sit at
or above `COMPACT_MAX`.** A query below the boundary can only refine the layout
inside compact; it cannot reach the edge to contradict the class. That holds at
1/8 done and at 8/8, it does not need editing as work proceeds, and it is false
exactly when the defect is present.

**The rule: when a migration is incremental, assert the INVARIANT that survives
every intermediate state, not the progress through them.** "Some remain" is a
status line. "None of the remainder can contradict the decision" is a test.

## v265 -- A remedy that always fires is not a remedy, it is the behaviour

`lib/pillfit.js` faded the autosave pill when it would cover a control. On a
desktop that condition is rare, so fading reads as a graceful exception. On a
phone the pill's fixed bottom-left corner overlaps the tool row at EVERY size --
the file's own header says so, in the sentence right above the fix -- so the
exception fired every single time and "Saved" was never once visible on a phone.

The file knew the collision was universal on phones and still chose a remedy
whose cost is proportional to how often it fires. Nobody measured the frequency,
because on the machine it was written on the answer was "almost never".

**Ask how often a fallback runs before choosing one.** A fallback that fires 1%
of the time can afford to be lossy. A fallback that fires 100% of the time on an
entire class of device IS the product's behaviour there, and it has to be as
good as the primary path -- or it has to be a different fallback. Lifting the
pill was available the whole time and costs nothing.

**And check what it composes with.** Warnings were exempt from fading, for a
good reason. Combine "reassurance always hidden on phones" with "warnings never
hidden" and the emergent behaviour is that a phone shows warnings and nothing
else -- a stuck amber pill on a healthy session. Neither rule was wrong. The
pair was, and no test covered the pair.

## v266 -- Do not paint a warning before the thing it warns about has happened

Flip's media autosave showed the amber "Saved without media" -- a pill that by
design NEVER fades, because a warning that fades claims it was resolved --
synchronously, before the IndexedDB write it describes had settled. Reaching
that code is the NORMAL path for saving media; the comments 80 lines up say so
outright.

Instrumented, the real sequence was:

    put:start bytes=4215866
    pill:saved-no-media        (+1ms)
    put:RESOLVED / pill:saved  (+13ms)

**13ms of a false alarm is not visible on the machine that writes the code**, and
that is the entire reason it shipped. On a phone spilling megabytes the gap is
long enough to see, and if the write is slow or fails the warning is permanent:
an amber durability alarm parked on a session that is completely fine.

The honest state for a pending write is "Saving…", which already exists and
already stays up. Amber should be reachable only from the failure handler.

**The rule: a state that means "something went wrong" may only be set by the
code that LEARNED something went wrong.** Setting it optimistically and
correcting it later inverts the cost -- the correction is the fast path on fast
hardware and the slow path exactly where the user is least able to tolerate it.

**And the test that missed it was checking the resting state.** A resting-state
assertion passes identically on the broken and the fixed build; only recording
the whole sequence could tell them apart. When a bug lives in an intermediate
state, assert the sequence.

## v267 -- Writing an attribute you observe is a loop, even when nothing changes

`pillfit.sync()` writes the pill's `class`; `pillfit` observes the pill's
`class`. `classList.remove()` sets the attribute even when the token was not
present, and setting an attribute fires a MutationObserver record even when the
serialized value is identical. So every unconditional write fed the observer,
which scheduled another animation frame, forever -- on an idle page, with the
pill hidden, doing nothing.

Measured on a phone viewport three seconds after everything settled: **133**
writes before the guard, **364** once lifting added two more per pass, **0**
after. It predates the v229 work; lifting doubled it, which is the only reason
it was noticed at all.

**Guard every write behind "would this change anything?"** when the writer and
the observer are the same component. It is not a micro-optimisation there; it
is the difference between converging and spinning. And a drawing app that keeps
a requestAnimationFrame loop alive while the user is doing nothing is spending
a phone battery to accomplish nothing.

## v268 -- A second route to an action orphans the first route's side effects

Shape has a kind picker. It opened from a click handler bound to
`#toolGroup .tool-btn` -- the tool SHELF -- and that was complete and correct
until v227 put a TRAY in front of the shelf.

After that, picking Shape from the tray called `setTool('shape')` through
`lib/toolshelf.js` and never touched the shelf's handler. The tool switched. The
picker did not open. Shape used whatever kind it already had, which for anyone
who had never happened to have Shape sitting on the shelf was `line`, forever.
It shipped in v227 and survived v228, v229 and v230 before a user said "shape is
not giving a choice, just gives you line".

**Nothing failed.** The action still worked; only its follow-on was missing, and
only on the new path. That is what made it invisible: no error, no dead control,
no wrong pixel -- just a dialog that never appeared, in a product where nobody
knew it was supposed to.

**The rule: when you add a second way to trigger an action, list every side
effect attached to the first way and move them to where the routes converge.**
Not "check the new path works" -- it did work. Ask what the OLD path did
BESIDES the action itself.

Here the convergence point already existed: `lib/toolshelf.js` calls the
surface's `setTool` for shelf and tray alike. The fix was three lines and the
diagnosis was the whole job.

And the test has to exercise the NEW route. The shelf route never broke;
asserting it proves nothing at all.

## v269 -- The union of rows is not the shape, and it perforates every slope

Fill's first version collapsed 6 pixel rows into one band and gave the band the
UNION of their extents. On a straight edge that is exact, which is why every
test and every desktop check passed. On a DIAGONAL the union is wider than the
narrow rows in it; the round-cap inset then pulls each run's ends back by half
its width; and where the region is narrow the run comes out shorter than its own
width and hits the short-run fallback, which draws a DOT.

So the first fill on the live demo drew a neat dotted line down the slope of a
triangle -- the fallback firing correctly, over and over, on geometry the banding
had misdescribed.

**Fixed-size decomposition of a shape is a guess about the shape.** Six rows is
right for a rectangle and wrong for everything else, and the wrongness does not
show up as an error, it shows up as an artefact somewhere nobody was looking.

Grouping rows by their ACTUAL extent removes the guess: a flat region is one run
however tall it is (48x47 box: 8 runs -> 1), a sloping edge is one run per row,
and the two cases need no separate handling. Cost follows the perimeter rather
than the area, which is both cheaper on ordinary shapes and exact on the hard
ones. **When a decomposition has a tuning constant, ask what the constant is
standing in for -- often the data already knows the answer.**

## v270 -- A tool's strength must not be a property of the device's sample rate

Blur's first version faded each touched point a little on every `pointermove`.
That reads as obviously correct and is obviously wrong the moment you ask how
many pointermoves there are: a 240Hz digitiser fires several times more often
than a 60Hz one for the same gesture, so the same swipe blurred several times
harder on a phone than on a laptop. v230's coalesced sampling had just raised
that rate ON PURPOSE, so the newer the hardware, the worse it got.

Measured: one short swipe took `#ffffff` to `rgb(87,89,92)`.

**Saturating the accumulation was the obvious repair and it was not enough.** A
cap bounds the maximum; it does not make a 4-event sweep land where a 40-event
sweep lands, because neither has reached the cap. The fix is to accrue against
the physical quantity the tool actually deposits along -- **distance travelled**
-- which is the same number however often the OS sampled the finger. 117/255
apart before, 6/255 after, and the residual is arithmetic: a falloff integrated
from 4 samples cannot equal one integrated from 40.

**The rule: when an effect accumulates over a gesture, accrue it against
distance or time, never against event count.** Event count is a property of the
hardware and the browser's scheduling, not of what the user did.

And the assertion that catches this cannot be a screenshot or a "did it blur"
check -- both pass. It has to run the same gesture at two sample rates and
compare, which is a strange-looking test until you know why it exists.

## v271 -- Look for what the format already honours before declaring it impossible

Blur looked unbuildable. The format is points; you cannot blur a polyline by
moving its points; there is no raster layer; adding one is a format change the
player must honour and therefore the owner's call, not a tool's.

That reasoning was sound and the conclusion was wrong, because of one detail in
`paintStatic()`: a stroke whose FIRST point is opaque gets painted by
`paintSeg` with **each point's own colour and own size**. Per-point colour is
already honoured, already replayed by the player, already in every saved file.
Blur is then just "fade this point toward the ground and widen it" -- entirely
sayable, no format change, no player change.

**Before concluding a feature needs a format change, enumerate what the RENDERER
already reads per point.** The format is not what the schema says; it is what
the paint path actually honours, and those can differ by more than one feature's
worth.

The corollary matters too: the obvious route -- per-point ALPHA -- genuinely is
not honoured, because `paintStatic` takes alpha from the segment's first point.
Two neighbouring fields, one usable and one not, and only reading the paint path
tells you which is which.

## v272 -- Test the renderer, not the plan

`verify_fill` had eighteen assertions and every one of them was about the shape
of the RUNS: one run per row on a slope, bounded height, every row covered
exactly once, two points per run. All eighteen passed on a build whose fills
visibly had holes in them, and the same bug got reported twice.

They passed because none of them knew that `drawLine` paints a STADIUM. Round
caps curve inward toward the top and bottom of a thick line, so a run's coverage
is not the rectangle its coordinates describe. The plan was correct and the paint
was not, and no amount of checking the plan could see it.

The assertion that found it rasterises the runs onto a canvas exactly as flip.js
draws them, then counts mask pixels the paint missed. It failed on its first run
-- 52 of 7845 -- and that is how the second half of the fix got found rather
than shipped a third time.

**When a component hands its output to a renderer, at least one test has to go
through the renderer.** Geometry tests are cheaper, they localise failures
better, and they cannot see anything the drawing API does on its own.

## v273 -- Prefer bleed to gaps

Fill's runs were inset by half their lineWidth so round caps would not paint past
the region's edge. That is careful, correct about the line's centre row, and
wrong at every other row of a thick line -- which is where the bare corners came
from.

Drawn to full extent instead, the cap bulges OUTWARD: every pixel of the region
is covered and the cost is a couple of pixels of bleed sideways, underneath a
boundary line already wider than that.

**Between an edge that stops short and one that runs over, the one that runs over
is the one nobody reports.** A gap shows as a hole against the ground; two pixels
of overlap disappear under the line that was already there. When a rendering
tolerance has to go one way, take the direction whose failure mode is invisible.

## v274 -- A promise with no timeout is a state machine with no exit

`SkriblDraftStore.put()` was awaited with a .then and a .catch and no deadline.
IndexedDB on iOS Safari can accept a multi-megabyte write and then settle
NEITHER way, so `_mediaSpillState` stayed 'saving' for the rest of the session
and the pill sat on "Saving..." forever. Worse, every subsequent save re-entered
the same branch and re-reported 'saving', so the stuck state was self-renewing.

Two handlers look like complete coverage and are not: success and failure are
not the only outcomes of an async call to something outside your process. The
third is SILENCE, and it has to be handled explicitly or it becomes a state the
UI can enter and never leave.

**Anything that can hang needs a deadline, and the deadline needs an opinion.**
Here the opinion is that bytes which have not landed in twelve seconds are lost,
because that is what a reload will find. A late resolve is then ignored on
purpose: the user has already been told the truth, and flipping the pill back to
green would un-tell it.

## v275 -- A test whose fixture is too easy is a test that passes on the bug

Two assertions were written for the fill's fringe gap and BOTH were vacuous.

The first drew a BOX. Axis-aligned edges barely anti-alias, so there was no
fringe for the fill to miss, and the assertion passed on a build with GROW set
to zero -- the exact defect it was written to catch. The second counted holes in
the shape's INTERIOR, shrunk by 18%, which excluded precisely the edge band
where the artefact lives.

Neither was a wrong assertion. Both were the right assertion pointed at a
fixture that could not exhibit the failure.

**Mutation testing is what caught it, and it is the only thing that could have.**
The assertions passed on the good build and on the broken one, so nothing about
running them told you anything. A test's fixture has to be able to FAIL, and the
cheapest way to know is to break the code and watch.

**Practically: when a bug is reported on a curve, test a curve.** The reproduction
the user gave is the fixture; simplifying it to a rectangle for convenience
throws away the property that produced the bug.

## v276 -- A point is a payload field, not a scratchpad

Smudge needed per-point state: how far this point has been smeared, and what its
colour and size were before the drag started. The obvious place is a property on
the point.

Points are serialised wholesale into every autosaved draft and every shared
Skribl, and copied by Object.assign into the undo snapshot. A scratch field
named `_sm` would have ridden into all of it and arrived at the server's
validator, on every stroke the user ever smudged.

It lives in a WeakMap keyed by the point object instead -- which also happens to
be more correct: liquifySubdivide INSERTS points mid-drag, so an index captured
before a split refers to a different point after it. Keying off identity
survives that; keying off position does not.

**Anything shaped like a record that leaves the process needs its scratch state
kept somewhere else,** and the assertion is cheap: no key on a point may begin
with an underscore.

## v277 -- A status is about THIS operation, not about the history

Flip's autosave pill reported "Saved without media" whenever a pending media
record existed. Reaching that branch means there is no photo and no track on the
page at all: the save omitted NOTHING. The record is a memo about a past loss,
kept so the user can re-add the same image with its settings.

Conflating the two put a permanent amber warning on a drawing with no media in
it. It was permanent because three separate things lined up: the record
round-trips through the draft, the control that clears it is 0x0 until a drawer
is opened, and warnings deliberately never fade. A warning with no reachable
resolution.

**The cost is not the wrong word on a pill; it is the colour.** Amber has to
carry a real "your bytes are gone", and it can only do that if it is rare and
true. A status that fires on history teaches people to ignore it, and then the
one that matters arrives in a colour they have learned means nothing.

**The rule: a status describes the operation that just ran.** If the state is
about something that happened earlier, it belongs to whatever offers the remedy
-- here, the re-add card -- not to the indicator for the current write.

## v278 -- A shared test helper is not surface-agnostic just because it is shared

A new Flip assertion used `DRAW_STROKE`, the helper the Pad sections use. It
targets `#canvas`, which is Pad's element; Flip draws on `#pad`. So on Flip it
drew nothing, scheduled no save, and the assertion read whatever the pill
happened to be showing.

It did not error. It reported "Saving..." and failed for a reason that looked
plausible -- a save still in flight -- which cost a round of chasing the wrong
thing.

**A helper lifted to the top of a file reads as applying to the whole file.**
When two surfaces share a suite, anything that touches the DOM has to say which
surface it is for, or be parameterised by it. The tell is an assertion that fails
with a value that is merely UNEXPECTED rather than wrong.

## v279 -- Ask what the structure survives, not just what it looks like

A fill and a line look identical once drawn: white ink on the page. They behave
completely differently the moment something drags them, because a line is ONE
stroke and a fill is a stack of thin horizontal ones. Smudge moves neighbouring
runs by different amounts -- that is what a falloff IS -- so the stack fans
apart and the ground shows through as a comb.

The number is small and decides everything: runs 0.9px apart, the falloff
varying 4.7% across that spacing, so separation grows at ~4.3% of the drag. With
3.1px of overlap the fill survives 72px of dragging and no further.

**A representation is not finished when it renders correctly.** It has to be
asked what happens when the OTHER tools touch it. Fill was measured against
"does it cover the region", and it did, perfectly -- and it was still the wrong
shape for a canvas where things get pulled around afterwards.

The follow-on is that the mitigation has a ceiling worth stating plainly rather
than tuning toward: surviving a 200px pull needs 8px of overlap, and the fill
would spill past its own boundary. Some limits are not bugs to be fixed but
consequences to be named, so the next person does not spend a day rediscovering
them.

## v280 -- Pin the constant that does not look load-bearing

`BLEED` reads like a rounding guard: draw each run a pixel taller so adjacent
ones meet instead of leaving a seam. It is also, and much more importantly, the
entire budget a filled region has for being smudged, liquified or moved.

Nothing about the name or the value says that. A later reader doing honest
cleanup -- "the runs already tile exactly, why is this wider than the group?" --
would halve the drag distance a fill survives, and see nothing wrong in any
screenshot they took.

So the assertion states the consequence, not the value: runs must be drawn
wider than their group, and the failure message carries the measurement (3.1px
of slack combs after ~72px, 5.1px after ~119px).

**When a constant's obvious purpose is not its important one, the test is where
you say so** -- a comment is read by someone already editing the line, and a
test is read by someone who just broke it.

## v281 -- A test that depends on list order is a test waiting to change meaning

`verify_tools` checked "Shift gives a circle" on Flip directly after a loop over
the shape kinds, with no selection of its own. It worked because 'ellipse'
happened to be last in KINDS. Adding a fourth kind made the loop end on 'poly',
and the check started drawing a shifted POLYGON -- which has a real bounding
box, so it failed with plausible-looking numbers rather than an error.

That is the expensive shape of this bug: the failure looked like a geometry
regression in the code under test, not like a precondition that had gone stale.
Pad's equivalent assertion selected 'ellipse' explicitly and was untouched.

**State a test's preconditions rather than inheriting them.** Anything a check
depends on -- the current tool, the current kind, the current page -- has to be
set by that check, even when the line above happens to leave it right. The cost
is one line; the alternative is a failure that sends someone into the wrong file.

## v282 -- Clamp in the geometry, not on the control

The corner-rounding slider can be asked for more radius than an edge can give,
which folds the shape through itself. The obvious guard is a `max` on the range
input -- and it cannot work, because the limit is half the SHORTEST EDGE of a
shape the user has not drawn yet. It differs with every kind, every drag size
and every aspect ratio.

So the clamp lives where the shape is built. Run the slider to its end and
rounding simply stops increasing, which is what a control at its limit should
do, and there is no state where a legal input produces an illegal shape.

**When a control's valid range depends on data the control cannot see, the
validation belongs to the thing that CAN see it.** A widget-level max is a
promise about a relationship it has no access to, and it will be wrong in
exactly the cases nobody tried.

## v283 -- Derive a mode's UI from the mode, do not toggle it at the call site

The stamp shelf has to be on screen for as long as the Stamp tool is selected:
without an armed stamp the tool does nothing, so "which stamp is loaded" is not
decoration, it is the tool's only state.

The shape picker, one control along, is the version that toggles. It opens in
the tool-shelf config, which is where the shelf button and the overflow tray
both converge -- and that was already a repair. The picker originally opened
from a click handler bound to the shelf, which was complete until v227 put a
tray in front of it; after that, choosing Shape from the tray never opened the
picker and Shape silently stayed on whatever kind it had. That reached the live
demo as "shape is not giving a choice, just gives you line".

Writing stamps the same way passed every assertion I wrote by hand and failed
the first one the suite ran, because the suite reached the tool by a route the
config does not sit on. Two routes had become three.

So the shelf's visibility is DERIVED, in `setTool()`, from which tool is active:
`hidden = (flipTool !== 'stamp')`. There is no route that can forget it, because
there is nothing to remember. The only thing left at the call site is the
deliberate override -- tapping the tool button while its own tool is already
active puts the shelf away -- and that is applied after the derivation rather
than instead of it.

**A UI that belongs to a mode should be computed from the mode, not switched on
by whoever happened to enter it.** Every new entry point is another place to
forget, and the forgetting is silent: the feature does not break, it just is not
there for the people who arrived the other way.

## v284 -- A shelf that only grows needs a byte budget, not a slot count

localStorage is ONE allowance, about 5 MB, for the whole origin. v231 has the
scar: Flip's draft grew to 2.7 MB of it and the Pad's autosave -- an unrelated
feature on an unrelated page -- started failing, with nothing in either feature
mentioning the other.

A stamp shelf is that trap by construction, because it only ever grows: every
stamp you save stays until you delete it. Capping the number of slots is the
obvious defence and it is a proxy for the thing that matters and a bad one --
one traced outline is worth fifty doodles. So the cap is on BYTES, the encoding
is compact enough that the budget buys a useful number of stamps, and the shelf
lives in its own key so a shelf that will not write can never take the drawing
down with it.

It also **refuses rather than evicting**. Dropping the oldest stamp to fit a new
one is the friendlier-looking design and it is the amber-pill failure over
again: the user's work disappearing with no event they can connect it to. A
stamp is something they deliberately made. Losing one has to be their decision,
so a full shelf says it is full.

**When a store only grows, decide what happens at the ceiling before you build
it, and measure the ceiling in the unit the resource is actually rationed in.**

## v285 -- The fixture is the assertion; two mutations proved it twice in one file

Every assertion in `verify_stamps.py` passed on the first build. Two of them
also passed on a deliberately broken one.

The undo contract -- one tap is one undo, however many stroke groups the
placement produced -- was tested with a stamp made from a SINGLE stroke. On a
build that recorded `groups: 1` instead of the real count, one group and the
real count are the same number, so the assertion agreed with the bug.

The no-op contract -- a tap with nothing armed places nothing -- was tested
against an EMPTY shelf. On a build that helpfully armed the first slot for you,
there was no first slot to arm.

Neither is a missing assertion. Both are assertions whose fixture could not tell
the two answers apart. The fixes are a two-stroke drawing and a shelf that has a
stamp on it, and the reasoning is now written into the fixture helper rather than
next to the check, because that is where the next person will change it.

**An assertion is only as strong as the case it runs on, and the weakest fixture
is the one where the right answer and the wrong answer coincide.** Mutating the
code is the only way to find those; reading the test will not do it, because the
test reads correctly.

## v286 -- A warning is only intolerable when it has nowhere to go

`verify_amber.py` was FAILING on `main`, on one assertion, and I caused it. It
passed at v234 and my v235 change broke it -- confirmed by checking out v234's
`flip.js` and watching the assertion go green again. It went unnoticed for three
merges because each was reviewed against the suites its own diff touched.

**What v235 was answering.** A live report: the amber "Saved without media" pill
sitting permanently on a drawing, coming back on every save, with no way to
clear it. v235 made the save status describe only the write it belongs to, so
the no-media path reports plain "Saved".

**What that cost.** Reload a session whose track genuinely never saved and the
pill says "Saved" with the track gone. And there is nothing in the code to tell
the two cases apart: in the live report and in the failing test the draft is
IDENTICAL -- `mediaOmitted` set, a pending record restored, no bytes. Either the
warning is shown or the loss is silent.

**So the fix was never about which state to show.** What made the old amber
intolerable was not that it was wrong. It was that it went nowhere: the pill
said media was missing, and the only controls that could do anything -- Re-add
and Dismiss, on the pending card -- lived inside a shut drawer, measuring 0x0
until something opened it. Nothing on screen pointed there. v235 removed the
warning instead of the dead end.

The amber is back and the pill is now the route: it reads "Media missing -- tap
to re-add", it is a control while and only while there is something to re-add,
and tapping it opens the drawer holding the card. Dismissing clears the record,
which schedules a save, which reports plain "Saved" -- the warning ends because
the situation did. Two wordings, because an amber raised when the media is still
LOADED (no store to spill to) has nothing to re-add and must not promise
otherwise.

**A true warning the user cannot act on trains them to ignore the colour.** The
repair for that is a route, not silence. Deleting the warning makes the screen
calmer and the product worse, and it is the easier change, which is why it is
the one that gets made.

Three things this needed that were invisible from the JS:

* `pointer-events: none` on the base pill. Correct -- a floating status must not
  eat a tap meant for the control beneath it -- and it meant a click listener
  did nothing at all, because the event never reached the element.
* `transform` collides. `pillfit` LIFTS the pill with `translateY` (209px on a
  390px phone); an `:active { transform: scale(.97) }` in a later stylesheet
  REPLACES that lift, so pressing the pill dropped it 209px out from under the
  finger pressing it. Found by a click that timed out, which is the same thing a
  thumb would have experienced.
* `typeof x !== 'undefined'` does not shield a `let` in its temporal dead zone;
  it throws the identical ReferenceError. The pending records had to move up to
  the media state, not acquire a guard that does not guard.

## v287 -- A mutation caught is not a mutation reported

Six mutations of the fix above were all caught. Four of them were caught as
`ERROR -- crashed before reporting`, with no assertion named.

The cause is that Playwright waits for actionability before clicking. Against a
pill still carrying `pointer-events: none`, or a Dismiss button sitting 0x0 in a
drawer that never opened, `page.click` does not fail fast -- it blocks for the
full default timeout and raises. Both of those are exactly the states the
section is testing for, so the defect under test was also the thing destroying
the report of it.

A crash and a failure are not the same signal. A crash reads as an
infrastructure problem, it names nothing, and this project has a section in
START-HERE about suites whose failure could not travel through the reporting
channel. The clicks now go through one guarded helper with a short timeout that
turns "was never actionable" into an ordinary FAIL with a sentence.

**When the thing you are testing for is also a thing that can wedge your test
harness, the guard against wedging IS the assertion.** Verify a suite by
mutation, then look at HOW it failed, not just that it did.


## v288 -- Measure the thing the eye is responding to, not the thing that is easy to measure

"Fill is a weak icon" turned out to be measurable. Rasterise every tray glyph and
read its ink bounding box off the alpha channel: Fill filled 15.0x16.3 of its 24
box where every other tool sat near 19x18. It was the smallest thing in the tray,
and it was a hollow diamond whose handle was a 3px stub, so at tray size it read
as a tilted square with a dot.

The measurement had to be of the RENDERED icon. Path coordinates say nothing
about how much of the box a drawing occupies -- stroke width, caps, joins and
fills all add ink outside the geometry, and two icons with identical viewBoxes
can differ by a third in apparent size. Reading the SVG source would have found
nothing.

**Two numbers were available and only one of them was the answer.** Ink EXTENT
tracked the complaint exactly. Ink COVERAGE -- the share of the box painted --
did not, and following it did damage: Stamps was "improved" from 24.3% to 19.7%
coverage and came out visibly worse, because the weight being removed was a solid
base bar holding the icon together. Two glyphs at the same coverage look nothing
alike when one is a thin outline over a wide area and the other is a small solid
mass. The suite reports coverage and refuses to assert it.

## v289 -- An exemption needs a sentence, or the band eats the drawing

Liquify is the flattest icon in the tray by a wide margin: 20 wide, 13.5 tall,
against an ~18 norm. By the band it is the worst offender in the set. It is also
correct -- it is a smear, and a smear is wide and low.

I redrew it to fill the box's height. The number improved. The icon became a
caret with a detached curl, and I only found that by rendering it next to the old
one and looking. The metric was satisfied and the drawing was worse, so the
drawing won and the redraw was reverted.

Which leaves a suite whose band Liquify fails. The fix is not to widen the band
until it passes -- that would re-admit the 15x16 Fill this all started with. It
is exempt BY NAME, in a dict whose values are the REASON, printed in the
assertion's detail. The next person to run this finds "a smear is wide and low;
the tall redraw read as a caret" instead of a red line inviting them to make the
same change I did.

**A numeric band over a design decision will eventually be satisfied by someone
who cannot see the design.** Carry the reason in the exemption, in the output,
where it will be read at the moment it is needed.

## v290 -- At 24px only the silhouette survives, so judge at 24px

The first repair of the Fill icon grew it from 15.0x16.3 to 19.8x18.8 -- into the
band, measurably fixed -- and the owner said "there's got to be a better one".
They were right. The size was never the whole complaint. The handle was a 3px
stub, and a stub does not become a handle by being scaled.

Fifteen candidates were drawn and rendered side by side at 4x AND at the 24px
the tray actually uses. The 4x row is nearly useless for deciding: a tipped can
with an open elliptical rim, a bucket pouring into a pool, a region with a drop
falling into it all read beautifully at 4x and turned to mush at 24px. The pour
became a desk lamp. The open rim became a rolling pin.

What survives 24px is the SILHOUETTE and nothing else. Which is why the winner
kept the original diamond-can outline -- already the strongest small shape in the
set -- and spent every change on the two things that were not legible: the stub
became a quarter-arc handle, and the drip grew until it stayed a separate shape
instead of merging into the can's corner.

Solid-bodied variants read better still in isolation, and at ~40% ink coverage
were twice the weight of anything else in the tray. An icon is not judged alone;
it is judged in the row it sits in.

**Render every candidate at the size it will actually be used, and decide there.
A comparison at 4x is a comparison of drawings, not of icons.**

## v291 -- A shared icon spec on paper is not a shared scale in practice

The tool glyphs are 24x24, 2px stroke, round caps and joins. That is Lucide's
spec exactly, so dropping two Lucide icons in should have been a copy and paste.
Measured, it was not: Lucide draws to the full box and `paint-bucket` and `stamp`
came in at 22.0-22.2 units of ink against a set that sits near 19. Fifteen per
cent larger, and correspondingly heavier, than the eight glyphs beside them.

Nothing in either SVG says so. Same viewBox, same stroke width, same joins --
and a visibly different size on screen, because "how much of the box the drawing
occupies" is not a property either file declares. It is only visible if you
rasterise and measure, which is the same lesson as v288 arriving from a new
direction.

Each is now scaled 0.88 about the box centre with its authored stroke raised to
2.27, so the RENDERED stroke lands back on 2px. The drawing is Lucide's,
untouched; only its size in our box is ours, and the attribution says so rather
than claiming the icons are unmodified.

**Matching a spec is not the same as matching a look. Verify the rendering, not
the declaration.**

## v292 -- Two exemptions is a smell, so make the exemption cost something

`verify_icons.py` now excuses Liquify from the height floor (a smear is wide and
low) and Stamps from the width floor (a rubber stamp is tall and narrow; Lucide's
is 18:22 and no uniform scale satisfies both the width floor and the height
ceiling). Two exemptions in a ten-icon band, the second added to admit a change
I was making, is exactly the shape of a guard being quietly dismantled.

So the exemption was given a price: an area floor that applies to every icon,
exempt or not. A glyph excused on one axis still has to occupy a comparable
amount of the box. Mutation-tested three ways -- the original weak Fill still
fails, an exempted icon shrunk to nothing still fails, and raw unscaled Lucide
still fails.

The margin is thin and is written down rather than rounded to something tidier:
Liquify at 270 is the smallest thing that must pass, the original Fill was 245.
Which is why the comment says outright that this is a BACKSTOP and not the
guard -- the per-axis floors do the real work, and that Fill failed both of them
too.

**When you widen a rule to admit your own change, add a rule that the change
still has to pass.** An exemption that costs nothing is a deletion with extra
steps.

## v293 -- A mockup is not a bill of materials

The icon options came as two images: a set of tray mockups and a grid of forty
named Lucide icons with seven recommended picks. The names were checkable, so
they got checked against lucide-static 1.37.0.

Fourteen of the forty do not exist. `pen-nib`, `hand-move`, `move-2`,
`paint-bucket-icon`, `square-fill`, `circle-fill`, `bucket`, `swirl`,
`wavy-lines`, `ripple`, `distort`, `blur`, `seal`, `picture-frame` -- including
four of the seven RECOMMENDED picks. And the glyph pictured for Liquify was a
finger with ripples while the name under it was `waves`, which in Lucide is three
wavy lines: the picture and the name were different icons.

The two that mattered were real, and both shipped. But a shopping list that is a
third fiction would have produced a pile of 404s and a quiet substitution of
whatever was nearest.

**Check names against the package, not the mockup.** It took one `npm pack` and
a loop.

## v294 -- The shape of the thing constrains the shape of the rule

Fill became a drop, on the owner's call, and a drop does not fit a band derived
from ten square-ish icons. A teardrop that reads as a teardrop is roughly 17:22 --
a sharp point over a round body -- against a band that wants at least 17.5 wide
and at most 21 tall.

The first attempt widened it to fit. The apex blunted, and it came out looking
like a peach. The band was satisfied and the icon was no longer a drop.

What fixed it was inverting the order: the APEX is the icon, so the control
points were set first to keep the tangent leaving the point steep, and the
proportions were tuned around that until 18.5x20.8 fell out. Inside the band
without touching the band, and still unmistakably a drop.

That mattered because the alternative was a third named exemption, three weeks
into a suite with two. Two exemptions describe a set with two genuinely
non-square members. Three, each added to admit the change being made at the time,
describes a rule that no longer constrains anything.

**When a design constraint and a numeric rule collide, try re-deriving the design
from its essential feature before touching the rule.** The rule is often fine and
the drawing was simply built in the wrong order.

## v295 -- Blur should look blurry

The Blur glyph was three concentric outlined rings, which reads as a target. The
reference sets proposed a dashed circle, which reads as a selection marquee.
Neither is blurry.

It is now a filled core inside progressively larger, fainter filled halos --
which is what defocus actually looks like, and which survives 24px precisely
because it has no internal edges to lose. It is the only soft form in a tray of
line drawings, and that is not an inconsistency to tidy away: it is the only tool
whose entire subject is softness.

**An icon for a visual effect should exhibit the effect, not diagram it.**

## v296 -- Three exceptions is not three exceptions, it is a wrong rule

`verify_icons.py` policed icon size with a per-AXIS band: width 17.5-22.5, height
17.0-21.0, derived from ten roughly square glyphs. Then three icons in a row
turned out to be legitimately non-square, and each needed a named exemption:

    Liquify  20.0 x 13.5   a warp is wide and low
    Stamps   16.5 x 20.0   a rubber stamp is tall and narrow
    Fill     16.0 x 21.5   a drop is a sharp point over a round body

v292 already called two exemptions "the shape of a guard being dismantled" and
answered it by making the exemption cost something. That was treating the
symptom. The third one is the diagnosis: the per-axis floors were never the rule,
they were a PROXY for it. What the band means is "occupies a comparable amount of
the box", and none of those three is out of line on that -- 270, 330 and 344
against a set running 324 to 429.

So the rule now says what it means. An AREA band does the work at both ends, and
the per-axis limits are reduced to what they can honestly police: collapse in one
dimension, and overflow of the 24 box. All three exemptions are gone.

Verified by mutation that the new rule is not merely looser: the original 15.0 x
16.3 Fill still fails (245, under the floor), an icon inflated to fill the box
still fails (484, over the ceiling), and a 3 x 21 splinter still fails on the
axis floor that area alone would admit.

**A special case is a fact about your rule, not about the world. One is a
detail; three in a row is the rule telling you it is measuring the wrong thing.**

## v297 -- Measure the reference instead of squinting at it

The owner sent a photograph of a drop with no text. The obvious reading is "make
it this", and the obvious next step is to eyeball it.

Instead: threshold the image, take the ink bounding box, get 116 x 158, aspect
0.734. The shipped drop was 0.889. That is not a nuance, it is a different shape
-- and the number immediately said what the eyeballing could not, which is that
matching it at the old band's height gives a width of 15.3, narrower than the
icon everybody agreed was too small.

That one number turned "they want a slightly different drop" into "this shape
cannot satisfy that rule", which is what produced v296.

**A reference image is data. Measure it.** It costs one script and it converts an
argument about taste into an arithmetic fact everyone can check.

## v240 -- A reload is not a clean slate when the app saves on pagehide

A new section of `verify_fill.py` needed an empty page, and did the obvious
thing: clear localStorage, reload, start fresh. It was not fresh. `reload()`
fires `pagehide`, `pagehide` runs `flushFlipDraft()`, and the outgoing page
wrote its drawing straight back into the slot the clear had just emptied.

Everything the previous twenty assertions had drawn came back. The flood under
test then crossed those old strokes instead of the photograph, and a mutation
that removed the entire fix still passed -- with 136 runs where the real answer
was 2.

The order matters and the fix is one line: reload FIRST, then clear, then empty
the frame explicitly and assert it is empty before proceeding.

**Autosave and test isolation are the same mechanism pointed in opposite
directions.** In an app that persists aggressively, a fixture has to say what
state it wants and check it got it -- "I reloaded" is not a statement about
state.

## v241 -- A mutation that does not apply is a mutation that passes

The same fix was mutation-tested four times and passed every time, which should
have been the tell. Two separate causes, both silent:

1. `str.replace()` returns the string unchanged when the pattern is absent. The
   inline `python3 -c` mutations had no assertion, so a pattern that did not
   match wrote the file back untouched and the suite ran the FIXED code. It
   reported PASS, which reads exactly like "the assertion is too weak".
2. The fixture contamination above, which made the real mutation survivable.

The habit that fixes it costs one line: `assert s.count(old) == 1` before every
mutating replace, and grep the file afterwards to confirm the code is gone. Both
were already the norm in the heredoc mutations in this session; the shortcut
form is where it slipped.

**When a mutation passes, suspect the mutation before the test.** A test that
cannot fail and a mutation that cannot apply produce identical output.

## v242 -- Fill over a photograph, and the rule that did not survive contact

`doFill` sampled the composited canvas -- backdrop, photo and all -- on the
stated reasoning that this is what the user is pointing at, and that filling
"the white part" of a photo has to see the photo. Reasonable, and it fails on
any real photograph.

A photo is texture. The flood is anchored to the SEED colour with a tolerance of
32 in squared RGBA distance, so on photo grain it stops within a few pixels.
Measured on a noisy image with a drawn box around the seed: **2 runs against 54**
for the same tap. Two runs is a speck, and a speck is why it was reported as the
tool not working.

The tolerance cannot be raised to fix it -- loose enough to cross photo grain is
loose enough to walk through a drawn line. So with a photo showing, the flood
runs against the background colour plus this frame's strokes: fill what MY INK
encloses. Identical behaviour when there is no photo, because then the two
images are the same.

The original comment was right that this has a cost, and it is written down
rather than dropped: a tap outside your strokes now floods up to them, over the
photo. That is what a tap outside a shape has always done on a plain background.

**"What the user is pointing at" is a good rule and it is not the same as "what
the algorithm can act on".** Test the rule against the messiest real input before
trusting the reasoning.

## v243 -- A picker that closes on every pick throws away what the pick revealed

Choosing a shape kind ran `syncShapeKnobs()`, which reveals Sides for a polygon
and Corners for a polygon or a rectangle, and then a separate listener closed the
popover on ANY click that hit a `[data-shape]` button. So picking Poly showed the
two knobs and hid them again in the same click. Reported from the live demo:
**"when you push poly it chooses it, but you have to choose it again to get the
menu."**

The old rule was keyed on the fact that a pick happened. The new one is keyed on
what the pick DID: if the chosen kind has a knob, the picker stays up, because
that knob is the only reason it is still needed. Line and Oval still close, and
that half is asserted too -- a fix that leaves the popover parked over the canvas
forever is not better than the bug.

**The rule about which kinds have which knobs moved into `lib/shapes.js`.** It
had been written twice, once in each surface's `syncShapeKnobs`, which was
tolerable while the only question asked of it was "hide this row". The close
decision made it a second question, and the first draft of this fix answered it
with a `shapePickShouldClose()` helper copied into both editors -- a third copy,
and `verify_surfaces` caught it as the 61st duplicated function name against a
ceiling of 60.

That ratchet was right and the ceiling was not the thing to change. `knobs(kind)`
belongs with the shapes because it is shape knowledge, not DOM knowledge, and
moving it there removed the duplicated helper AND the duplicated rule underneath
it. It hands out a copy of its list rather than the list, so one caller cannot
edit the rule out from under the other.

**A duplication ratchet firing on your own fix is information about the fix.**
The reflex is to read it as the limit being one too tight. It was pointing at a
rule that wanted a home.

**The assertion has to survive the mutation it is testing.** Three of the six
mutations here originally crashed the suite instead of failing it: with the
popover in the wrong state, the next `page.click` timed out on a hidden button
and the run died before printing the assertion that had already failed. Every
step that needs the picker open now reopens it if it is closed, so a regression
is reported by name rather than as a Playwright timeout.

## v244 -- A control the browser paints takes the browser's theme, not yours

Sides, Corners and stamp Size were added as bare `<input type="range">` without
`class="slider"`, so the shared custom track never applied and the UA painted its
own. A UA-painted control takes the document's `color-scheme`, which this app had
never declared, so it defaulted to **light**: a white track sitting inside a
near-black popover. Reported from the live demo as "the new sliders are for light
theme".

The class was the bug. `color-scheme: dark` on `:root` (and `light` under
`[data-theme="light"]`) is the second half, and it is the more useful half: it
does not fix these three sliders, it makes the NEXT control that slips through
degrade to a dark default instead of a light one. Scrollbars and date pickers
were already taking the light default and nobody had noticed.

The assertion is written over EVERY range input on both surfaces, not over the
three that were wrong, because the defect is "a new slider forgot the class" and
the next one will forget it too. `appearance: none` is what `.slider` sets and
what the UA does not, which is what distinguishes a control we style from one we
merely place.

**A shared class is only shared if using it is easier than not using it.** The
comment on `.slider` said "any future slider" and three future sliders did not
use it. A comment cannot enforce anything; the assertion can.

## v245 -- The reference could not become the icon, and that was arithmetic

Smudge took four icons before this one. The last was traced from a reference the
owner supplied: a hand, thumb hooked, fingers curled, index extended. It reads as
a hand in the reference because the reference is drawn large.

Traced into a 24 box it does not, and the reason is not craft. Four versions were
rendered side by side at 86px and at tray size -- faithful, one curl dropped,
silhouette only, and opened out at the set's weight. Every one was a squiggle at
24px, and each simplification produced a simpler squiggle rather than a clearer
hand. The strokes are wider than the gaps between the fingers, so they fuse
before they are drawn.

**A reference is a picture of what you want, not a promise that it fits.** Test
the reduction before adopting the reference, not after shipping it.

## v246 -- Matching the spec is not matching the hand

Fill also took four. The size rule in verify_icons.py passed every one of them:
box, stroke, ink area, centre. The owner rejected all four anyway, and was right
each time.

What the hand-drawn ones missed was not measurable in any of those terms. The
four icons in this tray that were never complained about -- Shape, Select,
Liquify, Stamps -- are Lucide, drawn by one person against a house style with
conventions no spec here captures: how a corner turns, where a stroke stops short
of a join, how much air sits inside a closed form. An improvised icon beside a
professionally drawn set reads as improvised no matter how carefully it is
measured, and the measurements say it is fine, which is worse than useless
because it argues with the eye.

Both slots now take Lucide. That is not a defeat of the size rule -- the rule
caught a genuinely undersized Fill (15.0x16.3, area 245, against a band of
260-450) and the owner's word for it was "weak", which is the same finding in
English. The rule is a floor, not a substitute for being drawn by the same hand
as its neighbours.

## v247 -- A metric that cannot fail the bad case is not a metric

An assertion was attempted for the defect that shipped twice: an icon legible at
4x and illegible at 24px. The proposed measure was internal holes -- a line
drawing whose strokes fuse loses them -- counted at both sizes.

Measured across the whole tray it does not discriminate. Liquify and Blur have no
internal holes at any size and are perfectly legible; the rejected hand also has
none; the accepted thumbprint reports MORE holes at 24px than at 96px, which is
antialiasing, not structure.

So no assertion was added. A check that passes the bad case and fails good ones
would have made the suite longer and the tray no safer, while reading in the diff
as though the problem had been handled.

**Some defects have no cheap metric, and the honest response is to say so rather
than ship a plausible-looking one.** The guard here is procedural: render the
tray at real size and look at it, which is the step that was skipped.

## v248 -- A wrong answer in the help is worse than no answer

Five of Flip's ten tools -- Select, Smudge, Blur, Fill and Stamps -- had no entry
in How it works. Two of the five were worse than absent. The Background image
section carries controls named "Fill / Fit / Stretch" and "Blur", the help has a
search box, and so a reader looking up either TOOL got a confident paragraph
about framing a photo. They get an answer, it is the wrong one, and they stop
looking. A missing entry at least leaves someone still searching.

**The link is an attribute, not the label.** Every documented tool now carries
`data-help-tool="<id>"`, and the assertion walks the tool REGISTRY -- where a
tool is declared -- and requires an entry for each id. Matching on the label text
would have paired Fill and Blur with the image controls and reported full
coverage, which is precisely the failure being fixed. An attribute can only be
written on purpose.

Three sentences were also stale rather than missing, and every one of them was
true when it was written:

  * Shape offered "a line, a rectangle or an ellipse". There are four kinds; poly
    shipped in v237 and was never written down.
  * Shape said to pick the kind "in the Draw menu". The picker moved onto the
    tool button in v237, so the help sent the reader to a menu that does not
    contain it.
  * The eraser tooltip hard-coded "three times the brush size". The multiplier is
    [2, 3, 5] and settable -- the help entry beside it had this right.

verify_docs.py catches facts that go stale NUMERICALLY -- versions, counts,
hashes -- and by construction cannot catch a sentence. Nothing compared the
roster to the prose, so the prose drifted for seven versions.

**The check that matters is the one tied to the declaration.** A count of help
entries would have passed throughout. Asserting against the registry means a tool
added without an explanation fails the suite rather than shipping mute.

## v249 -- A mutation that breaks the template is not a mutation that passed

The orphan assertion was mutation-tested by deleting an `{% if is_flip %}` and
leaving its `{% endif %}`. The template then failed to render, the page 500'd,
`page.evaluate` threw, and the suite died before printing anything -- and the
grep used to read the result looked only for FAIL lines, so it reported nothing
and looked like a clean pass of the mutation.

Rewritten as `{% if true %}`, which changes the behaviour under test while
keeping the tags balanced, it fails immediately and names all five leaked
entries.

This is the v241 lesson arriving a second time by a different route. First time
the mutation did not apply because a `str.replace` silently matched nothing; this
time it applied and destroyed the thing under test. **Read the suite's RESULT
line, not a grep of its failures** -- a crash and a pass are indistinguishable
through a filter that only shows failures.

## v250 -- Seven tools wore one cursor

Liquify had its dashed influence ring and the eraser its circle. Smudge, Blur,
Fill, Select, Stamps, Shape and Artwork all fell through to the PEN's ring, so
the canvas could not answer "which tool am I holding" and the only way to know
what a drag would do was to remember what you last tapped. The owner asked
directly.

The badge is the tool's own glyph, lifted from its shelf button at runtime rather
than copied into a second table, so there is one drawing of each tool and this is
it. It rides beside the ring rather than replacing it: the ring says how big, the
badge says which, and those are different questions.

**The assertion is "it is THIS tool's glyph", not "a badge appears".** One shared
badge would satisfy the weaker version and tell the user nothing -- mutation
tested by pointing every tool at the pen's icon, which passes a presence check
and fails this one on nine tools.

## v251 -- A fix scoped to the case that was reported

v240 gave Smudge, Blur and Liquify a note for one situation: a photo showing.
That was the case the owner hit, and it was fixed properly. The case UNDERNEATH
it was left mute -- a drag that simply missed the ink -- and it is the commoner
one by far. You aim slightly off your line, nothing happens, nothing is said, and
the tool reads as broken for exactly the reason the photo case did.

Found by driving all ten tools through Playwright rather than reading the code:
on an empty canvas, three tools did nothing and said nothing. The same audit
found Fill flooding the whole page through a gap in an outline, silently, adding
438 points -- which the owner had already reported once as "still not filling
completely".

Both now speak, and the wording differs by case: "draw something first" is wrong
and faintly insulting when there is a drawing on screen, so ink-present says
"needs to be dragged over your lines". Mutation tested by collapsing the two into
one message, which fails four assertions.

The fill note is a NOTE, not a refusal -- flooding a background on purpose is a
real thing to want, and a tool that argues with you is worse than one that
explains itself. It fires above two thirds of the canvas rather than a half,
because a warning that cries wolf is one nobody reads; both ends are asserted.

**Ask what the reported case is an INSTANCE of.** A fix that closes exactly the
reported case and none of its siblings will be reported again in a month, wearing
different clothes.

## v252 -- The audit found more bugs in the audit than in the app

Of five things the first tool audit flagged, three were defects in the audit:

  * "Blur does nothing on a real line" -- the probe compared point positions and
    counts. Blur changes SIZE and colour and moves nothing, which is precisely
    what it says it does, so a position check could not see it working.
  * "Select creates no selection" -- the probe read a global named `selection`.
    The state is `selSpans` and `selRect`.
  * "The shape picker will not open after Select" -- a click helper racing the
    tray, not reproducible when driven directly.

And a fourth was mine at a different layer: the flood-area calculation used
`sizeOf(run) * points(run).length`, but a run's points are SPACED along it rather
than one per pixel, so the estimate was an order of magnitude low and the escape
note never fired. A run is {y, x0, x1, h}; its area is span times height.

**An instrument that disagrees with the thing it measures is usually wrong.**
Every one of these was found by asking "what would this tool have to do for my
check to see it?" before believing the check.

## v253 -- The instruction was displayed at the one moment its target did not exist

The empty stamp shelf said "Pick something with Select, then tap Stamp to save it
here." Reported from the live demo: "I didn't know where the stamp was so I kept
pushing stamp in the tool menu. I didn't see the stamp button."

Three separate faults sent them there, and each alone would have been enough:

  1. THE BUTTON DID NOT EXIST YET. It lives in the SELECTION bar, which is
     created by a selection -- so at the moment that sentence is read, with the
     shelf open and nothing selected, its target cannot be on screen.
  2. "STAMP" NAMES TWO THINGS. The tray has a tool called Stamps, and the tray is
     the one place the WORD is rendered. The sentence pointed straight at it.
  3. THE LABEL IS NOT DRAWN AT ALL BELOW "REGULAR". `.pb-tx { display: none }`,
     so on a phone that bar is icons only and NO button is labelled "Stamp". The
     sentence named a label the surface does not render.

The first repair repeated fault 3: a hint reading "tap Stamp in the bar along the
bottom", which is exactly as unfindable. The codebase already carries this
warning, on the page-move hint -- "a hint that describes a control the surface
does not have is worse than no hint" -- and it was written for the same reason.

So: the shelf offers the step that must come first as a BUTTON rather than a
sentence; the sentence shows the glyph inline, because a picture can be matched
against a picture; and the control is SPOTLIT at the one moment it exists and
the shelf is still empty. The assertions run at 430px on purpose -- at desktop
width the labels are drawn and the reported bug cannot reproduce.

**When someone cannot find a control, check whether it is on screen at the moment
you told them about it, and whether the name you used is rendered anywhere near
it.** Both answers here were no, and neither is visible from reading the code.

## v254 -- A transient overlay that eats the interaction it comments on

The stamp hint fires the instant a selection is made -- which is also the instant
the user starts dragging that selection's handles. `.skribl-hint` is
position: fixed over the canvas and was pointer-reactive, so it swallowed
anything aimed underneath. It broke verify_select's rotation drag by sitting on
the handle: a suite that had nothing to do with stamps, failing because of a
toast.

Hints no longer take the pointer; their action buttons still do. The cost is
stated rather than buried: tap-anywhere-to-dismiss is gone for a real pointer,
leaving the timer and the action button.

**And the assertion for it was worthless on the first attempt.** It read
`elementFromPoint(...).tagName` and accepted "div" -- but the hint IS a div, so
it passed whether the fix was present or not. Only mutating the CSS back to
pointer-events: auto exposed that. The working version asks `h.contains(el)`,
which is the actual question.

Worth noting why the existing suites could not have caught the original defect:
they dismiss hints with `element.click()`, which dispatches directly to the node
and ignores pointer-events entirely. Every one of them would have stayed green
with the toast blocking the whole canvas. **A test that reaches past the
mechanism under test is not testing it.**

## v255 -- The icons were small because nobody had measured them

"Those icons are so small. Do they have to be so small?"

Measured: 13x13 inside a 38x38 button, over 12px of empty padding on every side,
and the same 13px at EVERY width. The tool tray beside it draws at 21px, so two
rows of controls of equal importance differed by 62% and had done since the bar
was written.

Width was never the constraint, which is the part that makes this a mistake
rather than a trade-off. At 430px the six selection-bar buttons used 228 of
410px; at 320px, 198 of 300. There was 180px of unused bar sitting next to icons
too small to read.

18px, not 20: at 20 the glyph starts touching the button's border, and contents
that reach the edge read as cramped rather than as bigger. The button box is
untouched, so the 44px tap band --tap-grow builds is untouched with it.

**Three assertions, not one**, because the likely regression is fixing one of
these at the cost of another: the glyph is large enough to read, the tap band is
still 44, and the bar still fits on one row at 320. Mutation tested in both
directions -- shrinking the glyph back to 13 fails four checks, and removing
--tap-grow to pay for a bigger drawing fails its own.

**A number that has never been questioned is not the same as a number that was
chosen.** 13px had survived every review of this bar because nobody had put it
next to the 21px it sits beside.

## v256 -- A toggle written, and undone by a second listener on the same button

"The stamp library doesn't go away until another tool is chosen." Press-again-to-
close was already in the code and had never worked.

#stampToolBtn carried TWO click listeners. lib/toolshelf.js binds the cells it
builds to the registry's setTool; each surface ALSO bound every
'#toolGroup .tool-btn' to its own. A DERIVING handler survives being run twice --
which is why nothing else showed a symptom -- and a TOGGLING one does not: the
registry's toggle closed the shelf and the surface's setTool re-derived it open
in the same click.

Static cells in the template were never bound by the registry, so they only ever
had one route; the cells the registry BUILDS had both. The fix marks what the
registry binds and has each surface skip it, so every button has exactly one
route. The guard is in Pad too, where it changes nothing today -- both of Pad's
routes merely derive -- because the two surfaces drifting is how one of them
acquires this bug later.

**Idempotence is what let this hide.** A double-fired handler is invisible until
something stateful runs inside it, and then it looks like the feature was never
written.

Two further traps, both hit while fixing it and both worth the same warning:

  * The toggle read `stampPop.hidden` AFTER setTool had rederived it, so it saw
    `false` every time and could only ever CLOSE -- shut on the second tap and
    never back on the third. Read the state before the call that changes it.
  * The spotlight ran its own 6000ms timer while an ACTION hint dwells
    DURATION * 2 = 12400, so the ring went out six seconds before the sentence
    calling it "the highlighted button" did. It now ends through an `onHide`
    callback on the hint, so the two cannot disagree even if the dwell is
    retuned -- the number is not copied, it is not known here at all.

The timing assertion is pinned at 8s, where the OLD and NEW behaviours disagree,
rather than at an exact end time that would be flaky and would break on every
retune.

## v257 -- Show the control, do not only describe it

The stamp hint said "The highlighted button saves this selection to your Stamps
shelf." That sentence works only if the highlight is noticed. The owner asked the
obvious question: why not put the icon in the toast?

So hints can now carry a glyph, and this one shows #sbStamp's OWN svg, lifted at
runtime rather than redrawn. The assertion compares the markup rather than
checking that an icon exists, because a second copy is only correct until either
side changes -- pointing the toast at the pen's icon passes a presence check and
fails this one.

The wording dropped "The highlighted button" with it. The requirement was never a
particular WORD: it is that the hint must not name a label the surface does not
draw, since below the "regular" size class the selection bar has none and the
word "Stamp" IS rendered in the tool tray. The assertion now states that rule
directly instead of insisting on the word that used to imply it.

Two layout traps, both from turning a centred block into a row:

  * `.skribl-hint-text` is display:block, so an inline icon before it lands on
    its own line and the toast reads as a caption over a paragraph. Fixed with
    a flex row, scoped by :has() so hints WITHOUT an icon keep the centred
    layout they were written for.
  * The toast is position:fixed with no width, so it shrink-wraps. Harmless for
    a block whose text fills to max-width, wrong for a flex row: the items
    shrank instead and a two-word action button broke across two lines. The row
    variant sets an explicit width.

**A design that works as one layout does not survive being turned into another.**
Both of these looked correct in the CSS and only showed up in a screenshot.

## v258 -- 44px of grab, 22px of layout, and four measured exceptions

Every slider in the app was 22px tall against Apple's documented 44pt minimum --
half. The obvious fix, the --tap-grow ::before the buttons use, DOES NOT WORK
here: pseudo-elements do not render on <input>. So the element itself is 44 and
negative margins hand the 22 back to the flow. The box that takes the press is
twice as tall and nothing moved -- which matters, because the draw drawer is
already 628px of a 950px phone and both drawers reach the bottom edge.

Both halves are asserted, because each is the other's likely regression: shrink
the box and four checks fail; drop the negative margin and the layout checks fail
naming the sliders that grew the page.

FOUR SLIDERS ARE DELIBERATELY LEFT SHORT, measured before the change rather than
discovered after:

    photoZoom   vs Reposition      11px      shapeSides vs Corners        5-7px
    photoBlur   vs Reset            3px      shapeSides vs kind buttons   1-7px

Where two hit areas overlap, the winner is DOM order and stacking -- so growing
these would MOVE a tap target rather than enlarge it, which is worse than leaving
them small. They carry .slider-tight, the exception is pinned by an assertion so
it stays a decision, and the real fix is row spacing in the popover and the image
drawer: mocked at 44px it clears every collision and takes the shape picker from
102px to 151.

**The default is the correct behaviour and the exceptions are marked.** A slider
added later is reachable without anyone remembering to opt in, and each opt-out
carries the measurement that justifies it.

One artifact worth recording: the analysis also reported stampScale colliding
with shapeSides. It does not -- the probe had forced both popovers open at once,
and through a real route choosing Stamps hides the shape picker. **A collision
found in a state the app cannot reach is not a collision.**

## v259 -- A 44px box is not a 44px target

The shape knobs were grown to 44px and STILL lost their band: the rows were 6px
apart, so measured with elementFromPoint only 3 of 9 sample points across Sides
reached Sides -- the rest went to the kind buttons above and to Corners below.
17px of row spacing is the first value where all 18 points across both sliders
land on the slider they belong to; 11 and 14 still leak 3 each. The picker goes
102px to 181 on Flip, 98 to 201 on Pad, which a popover can afford.

**The first fix went into flip.css, which Pad does not load.** Both surfaces
render this markup, so Flip read 9/9 while Pad read 4/9 -- and a size-only check
passed both, because the boxes were 44 on each. The rule moved to styles.css and
the assertion now samples the band rather than measuring the box.

## v260 -- Three ways a measurement lied, in one sitting

Every one of these produced a confident number that was wrong, and each was
caught only by disbelieving the instrument:

  * THE "AFTER" WAS MEASURED WITH NO GROWTH ALLOWANCE. The mockup compared a
    22px slider grown by 11 against a 44px slider grown by 0, so the after state
    could not report a collision by construction. It printed "5 -> 0" and the
    zero meant nothing.
  * GEOMETRY IGNORED STACKING. Counting rect overlap flagged the page bar's
    Duplicate and Blank buttons as collisions with a popover that sits ON TOP of
    them and occludes them entirely. The only honest question is which element
    receives the press, which is elementFromPoint, not arithmetic.
  * THE FIX FOR A TOAST IN THE WAY DELETED THE THING UNDER TEST. Dismissing the
    hint with h.click() bubbled to shapePopDismiss -- a click outside #shapePop
    closes the picker -- so Flip's two checks found no rect and SKIPPED, silently,
    while Pad's still ran and passed. The suite went green with a third of its
    new coverage missing. Now the hint is removed rather than clicked, and a
    check asserts both knobs were on screen at all.

**A check that disappears is worse than one that fails.** Two of these three
were only visible by reading which assertion names were absent from a passing
run.

## v261 -- Most of the white space was mine

Asked whether the gaps in the image drawer were all necessary, the honest answer
was that the drawer being looked at was a MOCKUP: +24px row spacing that this
session had injected to show what 44px targets would cost. Measured, the shipped
gaps are 8, 0, 12, 12, 8 and 0 pixels; the mockup's were 48, 24, 24, 24, 48 and
24. Nothing needed removing.

The one real finding was a duplicated heading, and it is narrower than it looked
too: the dropzone shows the FILE NAME, and only falls back to "Background image"
-- directly under a section label reading "Background image" -- when no name was
stored, which is what a synthetic test image does. The fallback now reads "Image
added".

**Before treating a screenshot as evidence, check whose CSS is in it.**

## v262 -- Pad had been drawing the shape knobs unstyled since they shipped

The owner put the two surfaces side by side and asked why Flip looked different.
The whole of `.shape-knob` -- the flex row, the 10px uppercase label, the
min-widths, the tabular output -- lived in flip.css, which PAD DOES NOT LOAD. Pad
renders identical markup, so it fell back to a block: label under the slider, at
16px, in sentence case. It had looked like that since the knobs arrived in v237.

**Nothing caught it, and the reasons are worth listing**, because each is a check
that exists and was satisfied:

  * the markup is identical, so a structural comparison passes;
  * both surfaces have the same tap targets once the SPACING moved, so the size
    checks pass;
  * verify_surfaces is file-only -- it counts stylesheet bytes and never renders
    either page, so it cannot see a rule that reaches one surface.

This is the second time in two versions that a fix went into flip.css and missed
Pad. The first was the 17px row spacing an hour earlier, found only because the
hit test happened to run on both surfaces. **When both surfaces render the same
markup, the rule belongs in styles.css, and the way to prove it is to render both
and compare -- not to compare the files.**

The assertion now captures how the row is drawn on each surface and requires them
to be equal. Mutated by moving the rules back to flip.css, it reports Pad as
display:block, 16px, textTransform:none -- which is exactly the screenshot that
started this.

## v263 -- The fix was measured on the wrong property

v250 made every slider's hit box 44px and reported it fixed. The owner looked at
the app and said brush size and opacity still seemed small. They were: the thumb
was still 16px on a 4px track. A hit area is invisible, so the control became
easy to grab and looked exactly as it had before.

Both properties are real and independent, and BOTH are now asserted -- reach by
sampling elementFromPoint across the band, appearance by measuring what is drawn.
24px on a 6px track: iOS draws roughly a 28pt thumb on a 4pt track, 16 was about
half that, and 28 crowds the row and makes the track look short beside it. The
hit box, the flow height and the drawer heights are all unchanged, which is what
makes this purely a visual change.

**Appearance had to be measured in PIXELS.** getComputedStyle(el,
'::-webkit-slider-thumb') returns the HOST element's box -- 260x44 here -- so it
cannot see the thumb at all. Screenshotting the control and reading ink height
per column gives the thumb as the tallest column and the track as the median,
and reverting to 16/4 fails three checks by name.

One impurity is recorded rather than papered over: the measurement includes the
thumb's glow ring when the crop does not clip it, so Pad reads 31 where Flip
reads 24 for the same CSS. The bounds are wide enough that this does not matter,
and the direction is what is being tested.

**"Fixed" is a claim about a property, and the user is entitled to a different
one.** Reporting a tap-target measurement against a question about size was
answering the wrong question with real numbers, which is more misleading than
saying nothing.

## v264 -- The zoom control was short on space and short on reach

The loop-detail row carried a four-cell segmented magnification control (1x 2x
4x 8x) that took 179px and pushed the bar to 74px -- two lines on a phone. The
owner asked whether the two halves could share a line, and suggested a
`< 2x >` stepper.

They can, and the stepper is the reason. Three cells of chrome instead of four
labels is 94px, and the bar collapses to 36px -- one line at both 390 and 430.
It still wraps at 320, where `Loop | Start | End` alone is 172px of the 220
available; it wrapped there before too.

**The ceiling was a defect, not a limit.** `halfSpan = (loopDuration / 2 +
contextSeconds) / zoomMag` has nothing structural stopping it, and the finest
nudge step is 0.01s. On a 330px waveform at 8x that step moves the marker 0.94px
on a 20s loop and 0.39px on a 60s one -- the tool offered an adjustment you could
not see it make. The ladder now runs 1, 2, 4, 8, 16, 32; at 32x that same step is
11.7px. A stepper can afford six rungs because it costs the same as one; four
labelled cells could not, which is how a layout constraint had quietly become a
functional one.

**The magnifier had to BE the button, not sit beside it.** A leading magnifying
glass with the stepper after it measured 118px and wrapped the bar again at 390,
which gave back the whole saving. Putting Lucide's zoom-out and zoom-in glyphs
on the two step buttons identifies the control and steps it with the same pixels.

**It was built on Flip and Pad still had the old one.** This control existed as
a literal HTML string in `flip.js` and a second literal HTML string in
`editor_music.js`, and nothing made them agree -- the surfaces would simply have
offered different zoom ceilings, which is the drift the owner has had to report
by eye before. It is now `lib/zoomstep.js`, loaded by both editors and not by
the player, which has no loop-detail panel and should not carry the markup.

The ladder is shared but the WIRING is not: each surface keeps its own click
handler assigning to its own `zoomMag`. So the behaviour is asserted per surface
rather than once -- stepping the ladder, the readout, the two end-stops and the
window actually tightening, on Pad and on Flip. Reversing Pad's step direction
alone fails four checks on Pad and none on Flip.

**The shell was 11px against a 12px neighbour while the comment above it claimed
they matched.** The assertion reads `.edge-controls`' radius at runtime and
compares; a check written against the typed number would have agreed with the
mistake. Both the shell and its cells now derive from `--r-seg`, the way
`.nudge-btn` already did.

**One assertion had to be corrected rather than the code.** "Every step narrows
the window" failed at 1x and 2x -- `getZoomWindow` clamps to the audio, and the
fixture is a one-second clip, so the first two levels both ask for more than
exists. That is the clamp working. Pinning "no step ever widens, and the ceiling
is at least 8x tighter than the floor" tests the control; the original would
have been pinning the fixture's length.

## v264 -- Nine checks ran where eighteen were written

The new magnification assertions were appended to `verify_audio.py` BELOW the
line that collects failures:

    bad = [r for r in results if not r[0]]

All eighteen printed. The suite counted nine, and the nine new ones could not
fail the run no matter what they found -- the list they appended to had already
been read. A green suite and a full transcript both looked exactly right.

Moving the block above the summary is the whole fix, and four mutations then died
by name: restoring the 8x ceiling ("the ladder climbs 1 to 32 by doubling -- [1,
2, 4, 8]"), freezing the readout at 1x, never disabling the ends ("[1, 2, 4, 8,
16, 32, 32, 32]"), and widening the buttons ("the stepper is the compact one --
[172, 142]").

**Where an assertion is added is part of the assertion.** The count in the
summary line is the only thing that says a check was live; a check that prints
its result after the verdict has been computed is decoration.

## v255 -- The tool for the job already existed and refused the job

The owner said blur and smudge did not seem to work, sent a Photoshop brush-engine
spec, and then said the thing that actually mattered: "Maybe we don't need to
rasterize because I like that we can scale up exactly. I just want to be able to
simulate motion between still frames."

That is not a blur tool. That is the IN-BETWEEN, which has existed since v237 --
a generated page that integrates the motion between two poses like a long
exposure, built out of ordinary stroke data. It was refusing the case it exists
for.

`tweenMismatch` required the two pages to be structurally identical: the same
number of strokes AND the same number of points in each. That is exactly what
Duplicate-then-drag produces, and for that workflow the requirement is right.
But drawing the next pose by hand is what frame-by-frame animation IS, and a
redraw of the same shape lands a different vertex count every time -- a ball
drawn twice measured 38 points and 32. So the feature covered the workflow it
was developed against and declined the ordinary one.

**A stroke is a PATH, not a list of vertices.** Walking it at even spacing along
its own arc length re-emits the same shape at any vertex count. Resample both
poses to a common count and they correspond point for point; the exposure
arithmetic runs completely unchanged. This is not a guess at a pairing -- stroke
s still pairs with stroke s, exactly as before -- it only stops the VERTEX counts
from being the thing that decides.

Two hand-drawn poses, one of them squashed, now produce a tapering smear that
reads the squash. Nothing about the format changed.

**WHAT THE COMPARISON WAS FOR.** FlipaClip has both a Blur and a Smudge brush
because FlipaClip is raster -- their own knowledge base says so, in the article
explaining why lasso copies come out blurry. Every layer is already a pixel
buffer, so blur is a real convolution and smudge is real transport. They pay for
it with a canvas size fixed at creation, pixelation on zoom, and copies that
degrade as they are re-transformed. Skribl bought the opposite trade
deliberately, and the owner named the reason to keep it.

**THE DIAGNOSIS WAS RIGHT AND THE PRESCRIPTION WAS WRONG.** Blur genuinely does
no low-pass -- measured on a vertical slice through a line, the feathered
transition band was 5 rows before and 5 rows after, while the peak halved and
the core doubled. It is a fade. But the fix for that is not a better blur; it is
noticing that nobody wanted a blur. Four options were drafted and put to the
owner, and the one they chose was not among them, because all four had taken
"the tools are wrong" as the requirement instead of asking what the tools were
being reached for.

## v255 -- The assertion could not fail, because both sides were dots

A single-point run has no arc length to walk, so resampling it has to emit n
copies of the one point. The first test for this put a dot on BOTH pages -- where
n is 1 either way, so returning the run untouched and resampling it produce the
same answer. The mutation that returns `pts.map(...)` instead of `n` copies
passed the suite untouched.

Pairing the dot against a REAL run in the other pose is the case that can go
wrong: n is then the other run's count, and the bug leaves the two pages
mismatched again -- which is the exact defect the change is about. Rewritten
that way, the same mutation fails by name, and so does resampling to the SPARSER
of the two runs.

**A test whose two inputs are identical is testing that the function is
deterministic, not that it is correct.** Both mutations here were invisible for
the same reason: with n fixed at 1 there was nothing for the resampler to do.

## v256 -- Blur was a fade, and the vector answer was already in the file

Measured on a vertical slice through a line, the old blur moved the feathered
transition band from 5 rows to 5 rows while halving the peak and doubling the
core. It mixed each touched point toward bgColor and widened it: dimmer, fatter,
same knife-sharp edge. Softening an edge is the one thing the word promises.

Nothing done to a point's COLOUR can feather anything, because a point is drawn
as a solid round dab. The vector-native blur is expanded translucent copies --
the same path drawn several times, widest and faintest first, so the crisp core
lands on its own halo and the overlap of the passes IS the falloff. The
reference the owner sent says exactly this, and TWEEN_BLUR has been doing it in
the in-between since v238. The blur brush was the one thing on the surface not
using the machinery already sitting beside it.

**THE ALPHA IS AN 8-DIGIT HEX AND THAT IS WHAT MAKES IT AFFORDABLE.** Four
translucent passes per blurred stroke against a LAYER_BUDGET of 24 would flip a
frame to direct painting after six strokes, changing how every other stroke on
it looks -- which is what was reported to the owner as a hard limit of about
five blurred strokes per frame. That was wrong. alphaOf, the layering test, only
recognises rgba(), while the canvas renders '#rrggbbaa' translucent natively.
Measured: ten strokes drawn, five hex and five rgba, layerable count 4. The
in-between had already solved this in v239 for its own reasons.

**DIRECT PAINTING IS WHY DENSITY IS NOT COSMETIC.** Dodging the layered path
means translucent dabs COMPOUND where they overlap, and at the source line's own
point spacing that drew a visible string of circles. Resampling each halo run to
sit well inside a dab width makes the overlap uniform instead of periodic.
Density then made it too BRIGHT -- peak 254, brighter than the line it was meant
to soften -- so the alpha is paid back: n dabs of alpha x give 1 - (1-x)^n, so
the per-dab alpha is 1 - (1-T)^(1/n). Derived, not tuned. The core needed the
same treatment for the same reason and beaded on its own until it got it.

Final: feathered rows 2 -> 8, peak 255 -> 202, no beading.

## v256 -- Two metrics in a row ranked the broken build as the better one

The beading had to be pinned, and the first two attempts both preferred the bug.

Brightness along the line's CENTRE row scored the beaded build 1.0 and the
shipped one 6.4 -- backwards, because at the centre a beaded line and a smooth
one are equally white; the beads bulge at the edges. Lit height per column
scored them 0.064 and 0.072 -- backwards again, because without the alpha
compensation the undensified halo is simply more opaque, and a 60/255 threshold
reads that as a taller, steadier column.

Before either of those, the same measurement across the FULL line width read a
plain line at 8.1 and a blurred one at 13.6 and looked like proof of beading. It
was measuring the boundary between the swept span and the untouched ink either
side of it.

What ships instead is the property densification actually guarantees: the widest
gap between consecutive samples as a fraction of the dab drawn there, 0.2 shipped
against about 0.5 undensified. Exact, cheap, and it dies the moment the
resampling is removed.

**A check that prefers the bug is worse than no check.** Three measurements were
built and discarded before one separated the cases, and the discarded ones all
LOOKED like evidence.

## v256 -- A ratio cannot see the difference between 1-to-4 and 2-to-8

"Blur softens the edge" was first asserted as feather >= 2x. Reverting the soft
edge to the old 0.55x scale measures 1 -> 4 feathered rows; the shipped 2.4x
scale measures 2 -> 8. Both are 4x, so the mutation that undid the whole visual
change passed the assertion meant to catch it.

The absolute band is what the eye reads, so there is now a floor as well as a
ratio -- and beside it the same claim in DATA, where it is exact rather than
sampled: the widest halo pass against the stroke it softens, 1.55x on the old
scale and 3.4x on the shipped one. That one is the check that actually kills the
mutation; the pixel measurement is the one that says it matters.

Its own first version asked for the widest OPAQUE run as the baseline and got
zero, because after this change the core is translucent too. The baseline is now
read from the stroke BEFORE the blur.

## v257 -- Momentum does not belong in a vector smudge, and here is why

The owner asked for the reference's momentum term. It was built three ways and
none of them ships. This entry exists so the dead end is not rediscovered.

**THE DESIGN RULE.** In a vector deformation smudge, directional momentum is not
equivalent to raster pigment momentum. Point coasting increases displacement
contrast and produces spikes, so smear length should be controlled through the
existing spread/fade response rather than post-contact inertia.

**Why the reference form is a no-op, provably.** It is

    v_new = lambda*v_old + (1-lambda)*delta,   p += v_new * S * W(d)

and v is a convex combination of unit vectors, so |v| <= 1 and the displacement
is at most the delta*S*W already applied -- equal when the direction holds,
SHORTER when it turns. It can shorten or misdirect a vector smear; it cannot
lengthen one. Measured anyway: a curving drag came out at 14.3 against 14.2
without it, and three lag settings (10px, 26px and 95px direction half-life)
were visually identical.

The reason is structural rather than numerical. In a raster smudge the velocity
carries a sampled colour RESERVOIR forward, and the reservoir's inertia is what
extends the smear. Here the geometry IS the material: once p += delta*S*W(d) has
been applied there is no second thing whose inertia could carry anything, and
filtering the movement vector only changes its direction and magnitude.

**And the obvious workaround is ruled out too.** Letting points coast after the
brush passes -- the part the reference gates away with W(d) -- does lengthen the
smear, and it took three iterations to make it honest: per-event decay measured
183.6 / 187.2 / 193.0 for the same gesture at 4, 20 and 60 events; integrating
over distance but coasting in-brush points too was still rate-dependent, because
their budget is refreshed every event so the gain ramp is always sampled at its
top; coasting only the points behind the brush was finally rate-independent to
half a pixel.

It still looks wrong, and that is the finding. Points with the strongest prior
influence coast furthest, which AMPLIFIES the difference against their
neighbours -- and a large difference between adjacent points is the definition
of a spike. The smear got longer and pointier. Rendered at three strengths it
goes from a shallow dip to a hard V.

**The metric rewarded the artefact.** The y-spread of the dragged points rose
from 14.2 to 18.6 to 37.4 as the coasting got stronger, and every one of those
numbers is the spike getting longer. Only the picture caught it. That is now
twice in this area -- see the v256 entry on the beading metrics.

## v257 -- The smear response, raised after looking at three gestures

What DOES improve smudge is the response curve it already has.
SMUDGE_FADE_MAX / SMUDGE_SPREAD_MAX go 0.32 / 0.45 -> 0.55 / 0.9.

Chosen by rendering three gesture classes at four settings: a single
perpendicular pull, repeated back-and-forth rubbing across a line, and a tight
curved scrub. 0.55 / 0.9 was better than the old values in all three; 0.68 /
1.15 was worse in all three, going muddy against the dark ground and reading as
a blob rather than as pigment.

This is a response curve, not a mechanism. The deformation field is untouched
and still rate-independent, no per-point state is added, and there is no new
failure mode on turns or reversals -- which is exactly what disqualified
coasting.

**An earlier verdict of mine was wrong and is corrected here.** "Smudge pulls a
clean spike rather than smearing" came from a single perpendicular pull. Rubbed
across a line -- the gesture people actually use -- even the old constants read
as a smudge. The gesture was the wrong test, not the tool.

The suite's own smear check was `smeared > 0`, which passes at every setting
including the one originally reported as "looks like liquefy". The magnitude is
now bounded on both constants, and reverting either one alone fails by name.

## v257 -- A reload restores the draft, so it is not a reset

The v256 pixel assertions reloaded the page before drawing their test line. The
editor persists its draft in IndexedDB, so the reload RESTORED whatever the
previous section had left -- and clearing localStorage does not touch it.

The blur section then measured a 25.5px "source stroke" against the 7px line it
had just drawn, because the section in front of it had left blurred halo passes
in the draft. It had passed for one commit purely because of what happened to
run before it; inserting a new section ahead of it broke two assertions that
had nothing to do with the change.

Emptying the frame in the page and pinning the brush size is exact, depends on
no persistence layer, and reads 7 where it should read 7.

**A test that depends on what ran before it is not passing, it is agreeing.**

## v258 -- The image drawer's sliders were half-size because the rows were too close

photoZoom and photoBlur carried .slider-tight -- the marker for "we know this
one is 22px against a 44pt minimum" -- because a 44px box on either overlapped a
neighbour. The note beside them said the fix was row spacing in the image
drawer, "a layout change and not smuggled in here". This is that change.

THE ARITHMETIC, which is the whole of it. A grown slider is a 44px box with
-11px margins: the flow keeps its 22 and the box overhangs 11px above and below.

  * Two stacked sliders therefore need 22px between rows -- exactly the two
    overhangs. They had 12, so every pair overlapped by 10 and the LOWER slider
    took the top of the upper one's band, because where two hit areas overlap
    the winner is paint order.
  * A 35px button next to one needs 4.5px of its own to reach 44, so the gap
    above the first slider and below the last is 11 + 5 = 16.

Rows 12 -> 22, clearance above and below 0/8 -> 16/16. The drawer grows 251px to
295px on Flip, and it reads as breathing room rather than padding: before, Zoom
was jammed under the reposition hint and Blur against Reset.

Reset's 8px lived as an inline style on the button, where an author rule can
only beat it with !important. It moved into styles.css beside the other three
numbers it has to agree with.

## v258 -- The check could only ever find the slider

The first version asserted the fix from the slider's side: sample the 44px band,
ask elementFromPoint who gets each tap. It reported 9/9 everywhere and it could
not have reported anything else.

`pad` is (44 - height) / 2, so for a slider that is ALREADY 44 it is zero and
the grid never leaves the slider's own box. And when a band does overlap a
button, the slider WINS -- it paints later. So the control that loses points is
never the one being measured. The .slider-tight note had said this exactly:
growing them "would silently move a tap target rather than enlarge it". The
moved target is the neighbour's.

Sampling repositionBtn and resetPhotoBtn as well found the shipped fix was still
wrong: repositionBtn read 8/9 with one point taken by photoZoom, because 12px of
clearance left the button's own 4.5px band and the slider's 11px overhang
fighting over 3.5px. 16px settles it.

**Assert the fix from the side that can lose.** Three mutations now fail by
name: rows back to 12 (photoOpacity 9/9 -> stolen), the top clearance back to 12
(repositionBtn and resetPhotoBtn), the bottom back to 8 (resetPhotoBtn).

## v258 -- A hidden element is still a sibling, and the resting state is the one to test

Two smaller things, both of which passed before they were right.

`.reposition-btn + .photo-opacity-row` was written to give the Zoom row
clearance when the reposition hint is hidden. It never matched: the DOM order is
button, hint, row, and `display:none` does not remove an element from the
sibling chain. The rule was dead on arrival and the hint's own selector, which
applies in both states, is what does the work.

And the test forced the hint VISIBLE. That is the wrong layout: with the hint
present the thing above the Zoom row is a paragraph, and the sampler counts a
non-interactive element as "mine" because no tap is stolen. The hint is
display:none until Reposition is pressed, so the resting neighbour is the
button. Removing the clearance passed in the shown state and fails in the hidden
one.

Two of the four .slider-tight exceptions are gone. shapeSides and shapeRadius
remain, for the shape popover's own spacing.

## v259 -- The player repainted a still picture sixty times a second

Reported: the in-between plays, but the flip "slows way down" on the blurred
pages. It did, and the cause was not the in-between.

requestAnimationFrame runs at the display's rate. A flipbook advances at fps. The
player's frame loop called drawFlipFrame() on every RAF, so at 12fps on a 60Hz
screen four repaints in five redrew a picture already on screen. That was
invisible for as long as every page cost the same: a key page paints in 0.4ms, so
the waste was 1.6ms of an 83ms slot.

A blurred in-between of the same drawing paints in 41ms -- 26 samples of every
stroke at several passes each, 8,100 points against the key page's 75 -- and five
of those is 205ms of work for an 83ms slot, which the loop cannot deliver.

Measured on a 3-page 12fps loop over three seconds, where 36 frames actually
change: 289 full-canvas repaints before, 73 after, and the median gap between
repaints went from 14ms -- one per display refresh -- to 81ms, which is the
flipbook's own rate.

A flip frame is static, so the memo is simply the right thing: paint an index
only when it differs from the one on screen. Seek and the end-of-play paint go
through the same function and are correct without forcing, because if the frame
they want is already displayed then not repainting it is the answer.

**THE EDITOR WAS ALREADY RIGHT, which is worth recording so nobody "fixes" it.**
Its playback is a setTimeout that subtracts the upcoming paint's measured cost
from the interval, so each page still occupies its full slot. Instrumented at
12fps: key pages held 82.2 + 0.8 and 82.3 + 0.7, the in-between held 41.2 + 41.9.
All three are 83ms. The waste was the player's alone.

## v259 -- What the memo does not fix

41ms for one in-between paint is inside an 83ms slot on a desktop and outside it
on a phone, which is three to five times slower. The memo removes the repeats; it
does not make the paint cheap, and no scheduling can -- the editor's compensation
already clamps to zero and the frame simply takes longer than its slot.

The cost is 8,100 individual line segments, each its own beginPath/stroke,
because paintSeg draws point to point. Batching a run into one path would be much
faster and WOULD CHANGE HOW IN-BETWEENS LOOK: the passes are translucent, so
overlapping round caps compound at every joint, and a single stroked path does
not. That density is the effect. Trading it for speed is a decision about the
drawing, not a refactor, and it is left to the owner rather than taken.

## v259 -- A reset that cannot currently run, kept and labelled

sizePlayerCanvas() assigns canvas.width, which clears the bitmap, so it resets
the memo. Removing that line passes the suite: the function runs once, on the
line after its own definition, before any frame is drawn, and every resize path
goes to layoutPlayerCanvas(), which is CSS only.

It stays, and the comment says plainly that it is unreachable rather than
implying it is load-bearing. The one change that would reach it -- calling
sizePlayerCanvas() a second time -- has a blank player as its failure mode, and
the reset costs nothing sitting beside the assignment that causes it.

## v260 -- The exposure was budgeted for the server and not for the screen

The owner sent the file. 46 pages at fps 24, 22 of them in-betweens alternating
with key pages, each in-between 11,826 points against a key page's 438. Measured
on those exact frames: the key page paints in 1.8ms, the in-between in 46.8ms,
and the slot at 24fps is 41.7ms. Every other page overran and the flip dragged.

11,826 / 438 is exactly 27, which is TWEEN_POINT_CAP's answer for a page that
size -- the plan was already at its ceiling, and that ceiling is the SERVER's:
what a frame may contain. It says nothing about how long the frame takes to
draw, and the drawing happens once per appearance inside whatever slot the
document's own rate leaves. The same document at 12fps is comfortable, so this
was never the in-between alone but the in-between AND the rate.

So the allowance now scales with the slot: at 12fps and below the server cap
binds and nothing changes, above it the budget falls in proportion. Measured on
the owner's poses, regenerating the in-between at each rate:

    fps 8   27 samples  11,826 pts  47.0ms of 125ms
    fps 12  27 samples  11,826 pts  46.3ms of  83ms
    fps 24  15 samples   6,570 pts  28.9ms of  42ms
    fps 30  12 samples   5,256 pts  24.0ms of  33ms
    fps 60   7 samples   3,066 pts  12.6ms of  17ms

**IT NEVER CAUSES A REFUSAL.** Turning "here is a coarser exposure" into "this
page is too heavy for an in-between" would trade the feature away for a frame
rate. The server cap still decides whether an exposure is possible; the render
cap only decides how fine it is, and below TWEEN_MIN_SAMPLES it stops applying.

The cost is honest: 15 samples ribs slightly more visibly than 27. It still
reads as a smear, and a smear that plays beats a smoother one that stalls.

## v260 -- The optimisation that measured identical and was not

Before this, the fix looked like batching: paintSeg draws a run point to point,
so an in-between is eleven thousand beginPath/stroke pairs. Stroking each run as
ONE path took the owner's page from 46.8ms to 27ms, and the equivalence looked
perfect -- mean pixel difference 1.18/255, ink brightness 235.8 -> 235.8.

Both numbers were measured on the RGB channels of a SATURATED image. An exposure
is 27 copies of the same runs piled up; the composite is near-opaque wherever
there is ink, so nothing could move there however much each run changed.

Measuring the ALPHA channel on a bare run instead:

    gap/size 0.2   per-segment 146.7   one path 50.3   -66%
    gap/size 0.5               102.5             50.7  -51%
    gap/size 1.0                79.6             50.8  -36%
    gap/size 2.0                65.7             50.9  -23%

Canvas strokes a path as one shape, so self-overlap is painted once; separate
segments paint it twice, and consecutive segments ALWAYS share a round cap at
the vertex between them. Batching therefore removes a third of the ink at the
spacing an exposure uses, and two thirds at the spacing v256's blur halo is
densified to. It only looked identical on the one drawing dense enough to hide
it. Reverted, unshipped.

**A saturated measurement cannot see a change, and it does not say so.** That is
three times in this area -- the beading metrics in v256, the smudge y-spread in
v257, and this. The pattern each time: the quantity moved was not the quantity
measured, and the number came back clean.

## v260 -- A mutation that crashes is not a mutation that named its failure

The render ceiling applied as the POSTABILITY test refuses 60fps outright and
returns null. Three checks then indexed into that null and the suite ERRORed
before printing a summary -- caught as a failure by the harness, but the four
words that say WHICH guarantee broke never appeared.

Every read of a plan in that block is null-safe now, and the same mutation names
all three: the allowance no longer falls with the slot, a postable page was
refused, and the floor was breached.

## v261 -- The rate fix that could not reach the pages that needed it

v260 budgets the exposure against the document's frame rate, and it does that
where the exposure is BUILT. Every in-between already sitting in a file was
built under the old budget and keeps it forever: the reported 46-page document
was 22 in-betweens baked at 27 samples, and opening it in v260 changed nothing
about why it dragged. The fix existed and could not reach the only pages that
had the problem.

"Rebuild in-betweens" in the ... menu re-runs buildTween over every generated
page at the current rate. On the owner's file: 22 found, 270,692 -> 155,060
points, 44% lighter, about a second.

The hard part is not rebuilding, it is KNOWING WHICH PAGES TO REBUILD. Nothing
in the format marks a page as generated -- an in-between is an ordinary frame of
ordinary strokes -- and a false positive does not degrade anything, it
OVERWRITES A DRAWING. So three independent things have to agree:

  * every point's colour is an 8-digit hex. tweenFade writes those; the pen
    writes '#rrggbb' or an rgba(), never both halves of that.
  * the neighbours either side still interpolate, which is what produced the
    page to begin with.
  * the run count is an exact multiple of the previous page's, at least
    TWEEN_MIN_SAMPLES of them, because an exposure emits the whole run list
    once per sample per pass.

A page already at the right count is skipped, so the action is idempotent and
says so: run it twice and the second run reports "22 in-betweens are already
right for 24 fps" rather than rebuilding them identically.

One thing the rebuild must not do is edit the timing. buildTween always returns
`hold: 1`, which frameHold() reads the same as absent but the FILE does not, so
the page's own hold is copied back on and a page that carried none has it
deleted. How long a page is shown is the author's, and a rebuild is not an
occasion to have an opinion about it.

## v261 -- One fake page cannot test two rules

The detector has two rules that each stand alone against overwriting a drawing:
the ink must be 8-digit hex, and the run count must be a multiple of the
source's. The first safety check built ONE page that broke both at once and
asserted it was rejected.

Dropping the colour rule left that check green. The fake had the same run count
as its source, so `copies` came out at 1, the multiple rule rejected it first,
and the colour rule was never consulted -- the check passed through a rule it
was not testing. Rebuilding every page instead of only the stale ones also
survived, for its own reason.

There are two fixtures now, each rejectable by exactly one rule: a page shaped
like a clean 8x multiple of the source's run list but drawn in ordinary
'#26b0ff' (only the colour rule can refuse it), and a page of pure '#26b0ff80'
whose run count is deliberately one off a multiple (only the shape rule can).
Deleting either rule now fails the check named for it.

**A test whose input fails for several reasons only tests the first one.** Same
family as v260's saturated measurement and v256's beading metrics: the check ran,
the number came back clean, and the thing it was supposed to see was hidden
behind something else.

## v262 -- The picture does not change, so painting it twice was the bug

Third report of the same stall, after two fixes: "it takes about 5.5 seconds
to play 46 slides at 24 fps." The file behind it told the whole story -- saved
at 12 fps, in-betweens re-added by hand before v261 shipped, every one back at
27 samples and 11,826 points, the exact totals of the original file. At 12 fps
the v260 budget thins nothing, because nothing needs thinning ON THE MACHINE
THE BUDGET WAS CALIBRATED ON.

That calibration is the real finding. Measured at 4x CPU throttle, roughly a
mid-range phone: one of those in-betweens costs ~215ms to paint against a
41.7ms slot at 24 fps -- 6.2s for a 1.92s loop, which is the report to the
millisecond. Rebuilding at 24 fps (v261) brings it to ~123ms: better, and
still three times the slot. No sample budget closes a 5x gap between devices,
and chasing it down would mean exposures so coarse they stop reading as
exposures.

The frame is STATIC. Rasterising it more than once per playback was always
wasted work; it just took a phone to make the waste visible. So the first
paint of a heavy page is captured as a bitmap and every later visit is one
drawImage (~1ms at the same throttle): the first loop costs what it always
did and fills the cache; every loop after plays on time. Measured on the same
file, same throttle: cached loops of 1911ms and 1916ms against 1917 nominal.

The rule lives in lib/framebitmap.js and BOTH surfaces load it, because the
editor getting fast while every shared link stayed slow is this codebase's
signature failure. The editor's store lives from play() to stop() and is
keyed by frame object, so a replaced page misses safely; the player's is
keyed by index, because its frames never change.

The memory ceiling is the design, not a guard: bitmaps are how canvases die
on phones. Only pages past 1,500 points earn one; captures are taken at the
displayed resolution, not the backing store, which is what keeps a 46-page
phone cache tens of MB instead of hundreds; past a 64MB budget -- or on the
first failed allocation -- frames simply paint direct, slower but never
broken.

## v262 -- The scheduler believed a cost that could no longer happen

Shipping the cache alone made cached loops play FAST: 1.5s for a 1.92s loop.
The play timer subtracts each frame's expected paint cost from its slot, and
the expectation was the measured rasterisation -- 215ms that would now never
happen again. The wait clamped to zero and the loop rushed.

Two repairs, both to bookkeeping. The wait asks whether the upcoming frame
HOLDS A BITMAP and estimates a blit when it does; and a blit's measured cost
REPLACES the frame's book entry rather than blending in, because an EMA that
smooths a 215ms rasterisation into a 1ms blit stays wrong for three loops.

The suite's first version of that assertion checked the book after the THIRD
visit and a blend passed it -- on an unthrottled desktop the EMA decays fast
enough to sneak under any workable bound by then. The moment where blend and
replace are provably far apart is right after the FIRST blit, where a blend
still carries >=60% of the stale cost. The assertion moved there and the
mutation dies by name now. Same lesson as v261's detector, from the other
side: WHEN a property is measured is part of what is measured.

## v263 -- The tree is the product now, so the tree got the cleanup

The owner is taking this public on a fresh repository and asked for no loose
ends. Thirty-five files left the tree, in four families, every one preserved
in git history rather than destroyed:

  * sixteen V2xx-CHANGES.md changelogs -- per-seal narratives whose job passed
    to docs/HANDOFF.md and the commit log;
  * thirteen review-thread documents (REVIEW-RESPONSE.md, the
    docs/REVIEW-RESPONSE-v2xx set, REVIEW-RETORT-v207) -- each one records
    what was true AT THE TIME of a review that is over;
  * two superseded briefs, FOR-THE-REVIEWER.md ("This is v227, SEALED") and
    HANDOFF-NEXT-SESSION.md ("Current sealed build: v228") -- both were still
    on verify_docs' CURRENT_DOCS list, which is exactly how a stale doc stays
    authoritative: a ratchet was pointing readers at them as guidance
    thirty-five versions after they stopped describing anything;
  * the workshop leavings -- INTEGRATION-HISTORY.md (self-declared
    historical), ROADMAP.md (checkboxes superseded by START-HERE's open list),
    UI-PROPOSALS.html, and four v17x/v18x patch files for trees that no
    longer exist.

ARCHIVE-README.md was rewritten rather than removed: 1,589 lines of v131-era
delivery narrative ("this archive is built on the v131 client code...") down
to 58 that describe the archive that actually ships. SHA256SUMS left the
repository and is generated into the archive at seal time -- a checksum
manifest committed to a live tree is stale from the next commit onward, and
verify_docs already treated it as optional.

Two rules governed every deletion. A file was removed only if its content is
either superseded by a living document or preserved verbatim in git history --
usually both. And every reference TO a removed file was repaired in the same
change, because the check that would have caught a dangling path only scans
four docs: the rest were found by grep, which is the tool the check exists to
replace. docs/REFACTOR-v132.md stayed for that same reason in reverse -- two
live suites cite it as the explainer of the blueprint seam, so it is not a
vestige, it is documentation.

## v264 -- An outside review of v263, and what a bounded scan must do when it gives up

A reviewer went over the sealed v263 archive and reproduced one real defect,
raised two more worth code, and filed a set of documentation and configuration
findings. What follows is what changed and, as important, what did not.

### H1 -- a bomb check that fails open at its own safety cap (fixed)

`_jpeg_dimensions` reads the declared size out of a JPEG's SOF segment to reject
a declared decompression bomb before a browser allocates W x H x 4 for it. The
walk is bounded -- by segment count and byte offset -- so a crafted file cannot
turn the scan itself into the DoS. The bug was in what happened at the bound: it
returned None, and None means ACCEPT. So 64 empty APP0 segments followed by a
real SOF0 declaring 65535x65535 slipped through -- the scan quit one segment
early, and the browser, which has no such limit, decoded the bomb.

The reviewer's own repro is now a regression fixture. The fix distinguishes the
two ways a walk can end. Ran out of data -> the file is truncated, a browser
cannot decode it into a bomb either -> None -> accept, unchanged. Hit a safety
cap before an SOF -> the dimensions are UNKNOWN AND AN SOF MAY SIT JUST PAST
WHERE WE STOPPED -> a new `_UNSCANNABLE` sentinel -> refuse. A scan that stops
at its own cap must fail CLOSED, or the cap is the bypass. The segment cap was
also raised from 64 to 128 so the reviewer's exact file is now rejected on its
real declared size rather than merely refused as unscannable -- the stronger
outcome, a real number caught -- while the sentinel still closes the general
case of an SOF buried past any finite cap.

**A bounded resource check has two exits, and only one of them is "safe".**
Accepting on give-up turned the cost bound into the vulnerability.

### H2 -- production booted on the placeholder SECRET_KEY (fixed)

The secret-key guard refused an EMPTY key in production but not the known
placeholder `.env.example` ships (`SECRET_KEY=change-me`). Copied verbatim, that
is a publicly-known signing key: anyone who read the repo could forge a session
cookie or a CSRF token. The guard now rejects an allow-list of known
placeholders as well as the empty string wherever it detects a real deployment,
`.env.example` ships the key BLANK with a generate command beside it, and the
ephemeral-secret opt-out still overrides for a genuine throwaway. An empty
value was treated as dangerous; a value that is dangerous in exactly the same
way was not, because it was non-empty.

### H3 -- the sweep reuse race, narrowed and stated honestly (partially fixed)

The reviewer held that a data-loss TOCTOU remains in orphan sweeping despite the
v223 touch-and-re-check fix. They are right, and the honest response is to close
what is cheaply closable and document the rest rather than claim victory.
`put_bytes` reuses an existing blob by touching its mtime; between the exists()
check and the utime() the sweeper can delete the object it listed as old, and
the old code swallowed the resulting FileNotFoundError and returned as if the
reuse had worked -- leaving the committing post pointing at deleted bytes. Since
`put_bytes` holds the bytes, that race now REWRITES them. This does not close
the whole window (the sweeper can still delete after a successful touch; that
residue is bounded by the 24h grace period and the sweeper's own pre-delete
re-stat), and fully eliminating it needs a reservation/lease the association can
be checked against, which is tracked as future work. Severity in practice is
lower than filed: it requires reusing a 24h-old object within microseconds of
the sweeper deleting that exact key.

### The configuration findings that were real (fixed)

  * M1 -- the ephemeral-secret opt-out silently also reverted the rate limiter
    to the per-process backend, because production detection short-circuited on
    it. The flag now affects ONLY the secret; a deployment that opts into an
    ephemeral key still gets the shared rate backend it needs.
  * M2 -- `.env.example` shipped `SKRIBL_RATE_BACKEND=memory`, which overrode the
    production-safe auto-selection. Commented out, so production auto-picks `db`.
  * M3 -- an unknown `SKRIBL_MEDIA_BACKEND` silently fell back to inline DB
    blobs; a typo like `S3` stored every blob in Postgres. It now fails fast.
  * M5 -- `LocalDiskStore.delete_key` swallowed every OSError, so a delete the
    filesystem refused was counted as a removal. Only "already gone" is a silent
    success now; any other error propagates and the sweep records it.
  * M7 -- the final doc-stamping subprocess in the release run was unchecked; a
    failed stamp would have left stale counts under a PASS. Its exit code is
    checked and fails the release.

### The findings answered in prose, not code

  * M4 -- production detection is positive-only by design (a missing marker gets
    the permissive dev path so `python -c "from app import app"` keeps working).
    The residual -- an unlisted platform with no SKRIBL_ENV gets a dev config --
    is real; the answer is to set `SKRIBL_ENV=production` explicitly, now
    documented, not to guess a laptop apart from a server by heuristic alone.
  * M6 -- the frozen release tree hash excludes the stamped docs and SHA256SUMS
    because a doc cannot contain the hash of a tree that includes itself. This
    was already true and compensated (verify_docs keeps them in step, SHA256SUMS
    covers their final bytes); RELEASE.md now says so outright.
  * L4/L5 -- S3 credentials are validated lazily on first use, not at boot (no
    boot dependency on bucket liveness); the harness needs network to fetch
    pinned wheels and Chromium. Both are accepted as designed.

### The documentation that had rotted (fixed)

M8 (README "all optional" -- SECRET_KEY is required in production), M9
(START-HERE named v219/v227 as if current, in the file that preaches against
typed version numbers), M10 and L2 (FUTURE.md called the S3 backend "a subclass
stub" and "the single highest-leverage piece of work left" -- it is a full,
tested implementation; the line counts and byte sizes were stale), L1 (README's
layout diagram predated the blueprint refactor and showed a flat tree), and L3
(the stamp said "86 suites" while RELEASE.md said "88" with nothing saying
86 = 88 - 2). All corrected. Going public is exactly when a reader trusts the
prose, so a stale doc is a defect on that day even when the code is right.

### L6 -- a Python invalid-escape warning in a test's embedded JS regex (fixed)

`verify_smudgeblur.py` held a JS regex in a plain triple-quoted string, so `\(`
warned. The string is raw now. The warning never affected a result; it is the
kind of residue a public repo should not ship.

## v265 -- The second review: two more real races, and one held open on purpose

The reviewer came back over v264 and went looking past the explicit fixes for
adjacent failure modes. Three findings had teeth. Two are fixed here; the third
is real, architecturally significant, and held open deliberately with a plan.

### #3 -- the release journal could lose an append to a concurrent take (fixed)

The SQLite rate-limiter's durable release journal is read-all-then-truncate.
`_journal_take` read every line and then `seek(0); truncate()`; an append that
landed from another worker BETWEEN the read and the truncate was erased unread.
That release record was lost and its pending reservation kept counting against
the quota until TTL -- users seeing false 429s, and the journal not delivering
the durable cross-worker guarantee its own comment promised.

An exclusive advisory lock (`flock` on a sidecar `.lock`, so a truncate never
races a lock on the fd being truncated) now serialises append against take. It
degrades to the old best-effort behaviour where `fcntl` is absent, which is
never the SQLite+single-host deployment this journal is for. Proven two ways:
the lock blocks a second holder until release, and 500 appends across five
threads during a spinning taker lose none -- where disabling the lock loses
~116 of 500.

### #4 -- an S3 deployment booted without credentials and failed on first post (fixed)

`S3Store` required a bucket but accepted `access_key=None`, then signed with
`Credential=None` and an empty secret. This store signs with STATIC keys only --
there is no instance-role or metadata path in it -- so a missing key is always
an error, and the honest place to raise it is construction, not someone's first
post in production. It now refuses to build without both keys.

### #1 -- the orphan-sweep race is real, and the fix is deferred with a plan

The reviewer is right, and I said as much in v264: touch-and-re-check narrows
the window but cannot close it, because the association row commits in the
HOST's transaction AFTER the media is written, so no delete-time check can ever
see it. The exact ordering -- sweeper reference-check, sweeper stat sees OLD,
poster utime succeeds, poster returns, sweeper delete, poster commits -- was
reproduced deterministically (a store that performs the reuse at the stat seam;
the reused object is deleted, and its committed post 404s forever).

**Repeating stat() cannot eliminate a TOCTOU.** Closing it needs durable
ownership the sweeper can see: a committed pending-media claim, a per-key lease,
or a quarantine protocol. The owner's call was to SHIP the current build and fix
this next rather than land an ownership scheme in a rushed release, and that is
recorded here rather than papered over. Practical exposure is low but not zero:
it requires reusing an object older than the 24h grace within the microsecond
window of the sweeper deleting that exact key.

The chosen approach for the fix, so the next session starts from a decision and
not a blank page, is in FUTURE.md: a committed pending-media reservation, which
is backend-agnostic (identical for local disk and S3, correct across hosts),
keeps the MediaStore interface unchanged, and matches the durable-journal
pattern this codebase already uses for the rate limiter. The deterministic
reproduction above is the acceptance test it must turn green.

### M4 -- production detection stays positive by design

The reviewer would prefer detection fail closed on an unrecognised host. The
project's deliberate choice is positive detection so `python -c "from app
import app"`, one-off scripts and the harness boot without configuration; the
residual (an unlisted platform with no SKRIBL_ENV gets the dev secret) is an
operator-configuration matter, and `.env.example` now documents setting
SKRIBL_ENV=production explicitly. The owner confirmed: docs, not a runtime
behaviour change. This is a stance, stated, not an oversight.

## v266 -- The sweep race is closed: a claim the sweeper can see

Three releases circled this, and v265 shipped it deliberately open with a plan.
Here is the fix: a committed pending-media reservation, the one mechanism that
gives the orphan sweeper durable ownership to look at.

The race was never a missing re-check; it was that the thing to check -- the
post's SkriblPostMedia association -- commits in the HOST's transaction AFTER
the bytes are written, so at delete time it does not yet exist to be seen. No
number of stat re-reads can see an uncommitted row. So the poster now writes a
short-TTL claim to `skribl_pending_media` the instant after it writes the bytes,
COMMITTED on its own connection (independent of the host transaction, so it is
durable and visible immediately), and the sweeper spares any object carrying an
unexpired claim. The claim ages out by `expires_at` -- a post finishes in
milliseconds, so the TTL only bounds a poster that died between claiming and
committing -- and a rolled-back post's claim simply expires, so nothing has to
delete it on the happy path.

Two checks, for the two orderings. The batch reference query unions claims, so
an object claimed before the sweep is spared outright. And a FINAL per-key claim
re-check runs immediately before the delete -- the analogue of the age re-check
-- because a claim can be committed in the up-to-500-key window between the
batch query and the delete. That per-key re-check is the half that closes the
reviewer's exact ordering: sweeper lists old, poster claims and reuses, sweeper
reaches delete. The deterministic reproduction they asked for is in
verify_sweepjob and fails the moment that re-check is removed.

Read the claim on a FRESH connection, not the sweeper's session. The claim is
committed on a different connection, and the sweeper's session may hold a
transaction whose snapshot predates it -- SQLite is snapshot-isolated per
transaction -- so a query through the session could miss a claim that is already
durably committed, which is the whole race. A new connection reads the latest
committed state on both backends.

What is honestly bounded: the CLAIM WRITE is best-effort on SQLite. In rollback-
journal mode a second writer blocks while the sweeper holds a read, so a claim
written during a concurrent sweep may not land, and there the v264 age re-check
still narrows the window. This does not matter where it is load-bearing:
production is PostgreSQL, where MVCC lets the separate connection write and be
read immediately, and single-file SQLite is single-process and does not run a
sweeper against its own live writer. The test commits the claim through the
session to exercise the sweeper's re-check deterministically on SQLite, and
tests the real claim_media write path separately.

The claim is internal reservation state -- no foreign key, pruned by expiry, and
never seen by the player -- so it is not a payload or format change. It is a
table plus a migration, confirmed as the owner's call before landing.

## v266 -- A git checkout in a mutation test ate the fix, twice

Worth recording because it happened twice this run and both times the release
aggregate caught it. Mutation-testing an UNCOMMITTED change by editing a file
and then `git checkout -- <file>` restores the file to HEAD -- which discards
the real fix along with the injected mutant, because the fix was never
committed. The first time (H1, v264) the full run failed on a missing sentinel;
the second (this fix) on a missing `claim_media` import. The lesson is cheap:
commit the fix before mutation-testing it, so the checkout reverts only the
mutant. The safety-point commit is now part of the loop.

## v267 -- The migration that never ran, and the deploy that now runs it

v266 added `skribl_pending_media` and a migration to create it. Production never
got the table, and every `POST /api/skribls` carrying a photo or audio loop
started returning 500. The claim path writes a reservation and then, inside the
post's savepoint, DELETEs it once the association row exists -- and that DELETE
runs on the HOST session. On PostgreSQL one missing-table error aborts the
entire transaction, so the rate-limiter's next INSERT failed with
`PendingRollbackError` and the whole post fell over. It passed every SQLite test
because SQLite does not abort the transaction on a failed statement: the same
code there raises a plain `no such table` from the DELETE and nothing downstream
is poisoned. A Postgres-only failure mode that the SQLite suite is structurally
blind to -- the recurring shape of this project's transaction bugs.

The root cause was not the DELETE; it was that **the migration was never
applied.** `db.create_all()` lives only in the `init-db` CLI, and the deploy's
start command was a bare `gunicorn app:app` with no migration step, so the
schema in production only ever changed when someone ran Alembic by hand. Every
release since has depended on remembering to do that, and v203 is the one that
got missed. START-HERE has said for a dozen versions that the startup sequence
begins with `alembic upgrade head` -- it just was not wired into anything that
runs on a deploy.

Two changes, and the second is the one that matters:

1. **Gate the claim path on the table existing.** `storage.pending_media_ready`
   is a cached `has_table("skribl_pending_media")` check, re-evaluated every
   process start (i.e. every deploy). `claim_media` returns 0 when it is absent,
   and the host-session DELETE in routes.py is gated on it too, so it can never
   issue a statement against a missing table. Where the table is absent the
   claim path is a clean no-op -- posting works, and the H3 sweep protection is
   simply inactive until the schema catches up. This shipped first, unsealed, to
   stop the bleeding.

2. **Wire the migration into the deploy.** The Procfile's web process is now
   `python -m alembic upgrade head && gunicorn app:app`. Every deploy converges
   the schema to head before the app accepts a request, and a migration that
   fails takes the deploy down with it rather than serving on a broken schema --
   which is the correct failure. On the single Starter instance there is no
   concurrency to worry about: the start command runs once per container boot,
   before gunicorn forks its workers. If this ever scales past one web instance,
   move the migrate to a Render `preDeployCommand` so two instances cannot race
   the same `upgrade head`; `alembic upgrade head` is idempotent, so the race is
   wasteful rather than dangerous, but a pre-deploy phase is the right home for
   it at that point.

`verify_migrations.py` now pins the Procfile wiring (migrate present, before
gunicorn, chained with `&&`), so a future edit cannot quietly regress it to bare
gunicorn. `verify_sweepjob.py` drops the table and proves a media-carrying POST
still returns 201 -- the exact production case, reproduced deterministically.

The honest bound: the gate reads the schema once per process. A database that
gains the table while the process is live keeps no-oping until the next deploy
restarts it -- which, since the same deploy is what applies the migration, is
exactly when it should start working. The two are wired to the same event.

## v268 -- A skribl gets a name, from a tab both editors share

Saving a `.skribl` produced a nameless file. The Pad defaulted every draft to
"Untitled Skribl"; Flip named its download by the DATE, so two Flip saves the
same day landed as "…date.skribl" and "…date (1).skribl" -- the browser's
collision suffix standing in for the name the app never asked for. Two surfaces,
the same missing feature, diverging in two different wrong directions: the exact
shape of bug this project keeps paying for.

So the fix is ONE module, `lib/nametab.js`, that both editors include. It wires
a name tab on the header -- a seamless tongue in the header's own surface (no
hairline, because the header has none) centred on its lower edge -- that drops a
title strip down with the Tune drawer's exact grid-rows motion. It exposes
`window.SkriblName`: `get()` returns the typed title or an auto-filled default,
`set()` pushes a loaded draft's title back in, and `filename()` slugs a title to
a filesystem-safe `<slug>.skribl`. Both serialisers read `get()`; both download
paths read `filename()`; both load paths call `set()`. The name also rides the
payload's `title`, so it is the posted and library title too.

The default is NAME + TIME ("Skribl · Aug 31 9:12 PM"), not a bare date, and it
is computed once per session so it is stable while you edit. Time, not date, is
the point: the old collisions were day-granular. `filename()` reduces anything
to `[a-z0-9-]` so a space, a "·" or a ":" never reaches a Windows filename or a
shell. Empty is never nameless -- the default fills in -- so a save always has a
real name without forcing a naming step first.

Placement was the owner's call, made against real screenshots: centred, and the
tab uses a SOLID `--surface-panel` (exactly what the header's translucent fill
composites to over the near-black page) rather than a translucent fill, which
had tinted toward the canvas behind it where it hangs. On the Pad it hangs into
the ~12px gap between the header and the canvas. Flip's header is a floating card
OVER the canvas, so there is no gap there and the tab sits at the very top of the
drawing area -- consistent with Flip's floating chrome, and noted rather than
hidden.

`verify_nametab.py` drives both editors: the tab is present, the shared
`window.SkriblName` behaves IDENTICALLY on Pad and Flip (the two-surfaces
guarantee, asserted, not assumed), a messy title slugs safely, the auto-name
carries a time, and the typed name reaches `serializeSkribl`/`serializeFlip`.

## v269 -- Canvas-first, one signature, and naming moves off the canvas

Four decisions in one release, all of them reversals of things v268 and earlier
had treated as settled.

**The canvas fills the device.** A fresh document now opens on the preset that
displays LARGEST in the band between header and toolbar (`bestFor()` in
`lib/canvassizes.js`): a portrait phone gets 9:16 filling ~73% of the screen
(it was a 4:3 letterbox under a third), the desktop column gets 1:1 or 4:3 by
window height. Still always an exact table preset -- never a viewport echo --
so two people on the same kind of screen get the same shape; a stored draft or
an explicit pick always wins, and resizing never re-shapes an established
canvas. The old contract ("the default IS the first preset") is retired in
`verify_canvas`/`verify_padcanvas` in favour of "the default is a real preset,
chosen by fit, stable under resize".

**Naming lives in the menu, and Save draft goes through it.** The v268 header
tab was obtrusive over the drawing (worse on phones, where Flip's header floats
on the canvas). "Name this skribl" is now a menu row whose sub-label echoes the
title; Save draft opens the same drawer with its button relabelled "Save draft",
so a draft is named as it is saved. One shared path: `SkriblName.open({label,
onConfirm})`.

**The brand is a skribl.** The per-mode graffiti stickers are retired (icon /
avatar duty only). The one mark everywhere is lowercase "skribl" hand-lettered
as a SINGLE continuous stroke -- the pen lifts once, to dot the i -- shipped as
inline SVG (`_skribl_brand_mark.html`, ~1.4KB, stroke=currentColor so it is
real ink in both themes), signature-sized (20px) beside a tiny 10px caps mode
tag (PAD / FLIP -- words kept until a differentiation direction is chosen). On
a SHARED page the mark earns its keep: the player's "made with skribl" footer
line draws itself stroke-by-stroke when the card becomes visible -- triggered
on visibility, not load, because a transition fired into the still-hidden
shell applied instantly and the visitor met a finished word. The player's HTML
byte ratchet moved 9,000 -> 10,500 for exactly this, with the arithmetic in
the check.

**The header holds still and speaks plainly.** Post occupies its slot from
first paint (disabled until a take exists) instead of popping in and out, and
the shed order follows which action is current -- the mode tag is always the
cheapest shed, so Record keeps its word at rest and Post keeps its word with a
take from 390px up. The rec pill reads "0:06 · plays 0:01"; the menu says
"Save draft"/"Open draft…" with the extension demoted to a sub-label; export
descriptions carry the tradeoff, not the container the title already names;
Flip's selection-bar duplicate is labelled Duplicate, ending the Copy/Copy
collision. Generic toggles light in the accent (amber survives only on the
onion controls, whose pages genuinely tint #ff9f43); autosave stopped
narrating every stroke; Flip's blank page whispers "Draw page 1"; the dark
canvas gets a 1px seat in light theme.

## v270 -- The stamp that lied, one pen for the whole lockup, and Safari's clips

Sealed the same day v269 shipped, driven almost entirely by the owner testing
the live site on a real iPhone. Two of these decisions close operational holes
that had been open for months while looking closed; the rest are the brand
lockup reaching its final form under a phone's scrutiny.

**Migrations had NEVER run on production, and the fix is layered.** The v269
deploy switched the rate limiter to its db backend in production and every
POST 500'd: `skribl_rate_events` did not exist, though the v131 baseline
creates it and v267 had "wired migrations into the deploy". Three findings,
three layers. (1) **Render does not read Procfiles** -- v267's wiring was
decorative; the authoritative setting is the dashboard Start Command, which
now carries `python -m alembic upgrade head && gunicorn app:app`. (2) The
database was STAMPED at the baseline without the baseline's DDL ever running,
so the first real `upgrade head` crashed inside v180 (which alters the missing
table) -- released revisions are frozen, so `skribl/migrations/env.py` gained a
pre-flight that recreates a baseline table a stamp promised, in baseline shape,
letting the chain apply its own alters; it hands Alembic a transaction-free
connection, because Alembic will not manage one it finds already begun (the
first draft silently rolled back stamps). (3) Head revision `e9f4a7c31b28`
backstops any table still missing at the end. Verified against an exact replica
of the production database on PostgreSQL 16, then in production itself: the
deploy log showed the pre-flight fire, eleven revisions apply, and posting came
alive for the first time since the stamp.

**The mode words are written by the signature's pen, full size.** "pad" and
"flip" are hand-lettered continuations of the skribl signature -- same
continuous-stroke construction, same 30-unit box, and after three rounds of
owner review, the SAME 36px and stroke-width 2.3 (26px stepping with the mark
on phones). Legibility came from stretching the x-height zone of the letterforms
that already read correctly (piecewise y-remap, baseline and ascenders fixed),
not from redrawing -- three redraw attempts produced "prl", "ped" and "pod".
The words seat on the signature's exact baseline: a 3px optical seat from the
text-tag era and an align-self:flex-end leftover had them measurably 1.5px low.
The icon experiments (pencil, book, reference art) are all retired; DECISIONS
records them so nobody re-walks that road.

**A restored drawing is a postable drawing.** v269 changed Post's posture to
disabled-in-the-header and updated every take-producing path except
restoreAutosave, which still only un-hid the button -- the entire reveal back
when Post was hidden-until-take. Reported from the live demo the day it
shipped; one line, plus a verify_drafts pin proven against the unfixed code.

**Phone realities, each one measured.** The two drawer shells' -10px header
tucks pull both editors' canvas bands up 20px; Flip got a 22px stage shield
earlier in the day and Pad's canvas-area now carries the same number, after the
owner's tall-phone 9:16 canvas slid visibly under the header. Record's bare
phone glyph kept its pill's invisible 16px paddings and stranded the tune icon
25px away -- glyph padding now, and the reclaimed width lets the full lockup
fit at 390. The ⋯ menus became one design: Pad's bottom sheet, row metrics and
all, with the grabber a REAL .menu-handle element on both editors after a
::before drew inconsistently on the iPhone -- and the grabber's original
invisibility was var(--hairline-strong) on a dark sheet, not absence. Photos
punched square corners through the canvas frame only on the phone: Safari does
not reliably clip transformed children (.zoom-layer) to a rounded
overflow:hidden, so the photo layer wears the frame's own radius and the wrap
carries the -webkit-mask-image nudge. CI's harness jobs get 90 minutes; the
suite outgrew 30 and every push since the Aug 31 runner outage lifted was
cancelled mid-run while looking like a code failure.


## v271 -- The chrome learns manners: yield, step aside, sign in violet

A polish release, every line of it owner-driven from live phone review, and
the through-line is MANNERS: chrome that reacts to what the hand is doing
instead of standing where it stood.

**The custom color swatch stopped impersonating a preset.** It wore an inline
fill identical to the dot beside it plus a 7px mystery badge; now it wears a
rainbow conic (border 0 -- the base swatch's transparent border let the
gradient bleed past the radius as slivers), its wrapper shrink-wraps so the
badge-a-corner-away era is over, and the badge itself is deleted. The compact
pen row breathes at 26px dots with tap targets held at 44 by --tap-grow.

**The eyedropper grew a loupe.** A fingertip is forty pixels wide and the
pixel being sampled is under it. An armed press now opens the standard
magnifier -- reticle on the exact cell, ring and chip wearing the colour it
reads, drag to aim, RELEASE picks. Shared in lib/eyedropper.js; the loupe
draws from each surface's composited stage, the same canvas the sampler
reads, so magnifier and pick cannot disagree. The drag session listens on
window in the capture phase because Pad starts strokes from
mousedown/touchstart and the press may carry no pointerId to capture with.
On Flip the draw popout is VEILED while armed (visibility, never the drawer
state machine, whose onClose hook would disarm the pick it is making room
for): on a phone it covered nearly the whole canvas.

**The shape picker became a well-mannered palette.** The press that starts a
shape shoves it aside and the same gesture draws -- the click dismisser fired
after the pointer came UP, so the card stood over the canvas through every
drag. It grew a grip (lib/popdrag.js): drag the pill and the pop goes where
you put it, MOVED MEANS PINNED -- a positioned pop stops auto-dismissing and
behaves like a floating palette, veiled for each stroke and back on release.
The drag composes translate(var(--pop-dx), var(--pop-dy)) after the anchor
transform; the phone tier's `transform: none` override silently disconnected
the grip on exactly the screens that asked for it. And the hide/veil sits
BELOW every press-swallowing guard: on a post-record-locked canvas the press
closed the picker and drew nothing, which read as a broken tool.

**The grabber was never a contrast problem.** Third report, and the pixels
told the truth: 27pt of EMPTY space where the pill belongs. The menu sheet is
a column flexbox capped at 88dvh; when content overflows, flex shrinks
children before scrolling, and an empty 5px div has min-content height ZERO
-- the one child that could be crushed completely, only on real phones, whose
Safari chrome shortens the viewport our full-height dev runs never did.
flex: none. Two earlier contrast calibrations had "fixed" a pill that was
not a contrast problem.

**The autosave pill fades under a popover instead of climbing it.** The
popovers joined pillfit's target list so the pill would YIELD to them; on a
phone the lift "fit" and Saving rode the shape pop's tower to mid-screen.
BARS are climbed, POPS are fade-only; a warning still never fades. And the
lift now survives hiding, because stripping it at fade-out snapped "Saved"
to its home corner mid-fade.

**The recording header sits straight.** The stop square was accent-purple
inside an otherwise crimson pill (the idle whisper-of-purple glyph rule was
never taken back by the active state; currentColor now flows). The bar was
lopsided 24/14 -- the collapsed brand is a zero-width flex item that still
earns the header's gap, so recording mirrors the phantom on the right. And
the Stop pill's 15px flanks had been silently losing a specificity tie to
the newer tune-to-Record 6px rule for months.

**The signature signs in violet, pressed into a rimmed card.** Owner-walked,
step by step: black-on-white light theme read as heavy handwriting (the halo
vanishes against white), so light got a deep violet pen (#4a33c2); then dark
went purple too (--accent-bright, a step lighter than Post so the accent
budget holds); then the halo retired for a LETTERPRESS relief (bright ledge
below, shade above, physics restated per theme) chosen from a rendered
eight-way; and the header wears --header-rim, a border that is felt rather
than seen -- near-black in dark, near-white in light, drawn as a box-shadow
RING because a real border eats 2px of interior width and the 390px header
fit is measured to the pixel (the v269 pin caught it: Post shed its label).

One tokened pen (--brand-ink), one press (--brand-relief), one rim
(--header-rim): mark, words, surfaces and player all change together.

## v272 -- Undo remembers the drawing; the chrome finishes learning manners

Thirteen shipped changes across one day of live phone-and-desktop review. Most
continue v271's manners line. One is a real performance defect, and it is the
reason this release exists.

**Undo stored a SCREENSHOT of every stroke, and it broke a machine.** The owner
drew a thousand dots and four hexagons -- a 287 KB drawing -- and the whole
computer crawled. `makeHistoryState()` copied the entire canvas into an
offscreen canvas on every stroke START and kept the last thirty: ~17 MB a copy
at desktop hi-DPI, so roughly half a gigabyte pinned for undo, plus a thousand
multi-MB allocations churned through while dotting. Restoring that draft was
worse -- the history rebuild RENDERED and SNAPSHOTTED every stroke boundary in
one synchronous burst, which is the "fine until all of a sudden it slowed down"
the owner described.

The fix is not a smaller cache, it is the observation that the pixels were
never the truth. The canvas at any stroke boundary IS `preRecordSnapshot +
paintStrokesStatic(strokes)` -- the exact identity `stopPlayback()` already
relied on to restore the drawing after every preview. So a state is now the
stroke slices plus a REFERENCE to its base, and `restoreHistoryState()`
repaints. Live stacks and the restored-draft rebuild both.

That identity has one exception, and naming it is the whole safety argument: a
stroke drawn while NOT recording never enters `strokes`, so its pixels live
nowhere else. `unrecordedInk` tracks precisely that window; while it is up a
state carries a real snapshot, exactly as before. A fresh-take base capture
bakes the ink into the base, a clear blanks it, a load replaces it -- each
drops the flag -- and `restoreHistoryState()` settles it either way, because a
restore determines the canvas contents exactly. Clear-undo also restores the
state's base into `preRecordSnapshot` now, closing a latent divergence where a
replay after clear-undo lost its base layer. Measured at 1414x1414 with a
thousand strokes: zero pixel entries, 9 MB heap, undo 0.8 ms, draft restore
0.48 s where it used to freeze -- and undo/redo pixel-compared EXACT against
live reference states across pen, eraser and shape.

**The chrome recedes while the pen is down.** Header, toolbar, status and the
Flip furniture fade to 10% on `body.stroking` with a 0.12 s exit delay and an
immediate return -- the art gets the screen during the only moment it is being
made.

**The draw drawer opens half-height on phones** (`lib/drawerdetent.js`), and
the reveal took three attempts to land on a real iPhone. Two scrollIntoView
rounds left the "Brush, smoothing & more" button below the fold while every
Chromium run scrolled perfectly. `revealPanelEnd()` computes the absolute
target and writes `document.scrollingElement.scrollTop`, the bluntest primitive
there is; measures the fold against `visualViewport.height`, because iOS
Safari's bottom bar overlays the layout viewport and `innerHeight` lies about
what a person can see; and re-asserts at 300 / 700 / 1200 ms, because the
device settles URL bar, layout and its own competing scrolls on a schedule no
single timeout catches. Each assert is a no-op when the end is already visible.

**The post-record lock stopped being silent.** A finished take locks the canvas
and the only explanation was a toast fired by the press that had already
failed. "+ Add take" now floats at the locked canvas's bottom edge, appends a
take on tap, and nudges when a press lands on the lock -- the answer bounces
where the eye already is. Outside `#zoomLayer` so magnifying never scales it;
hidden under `body.replaying`, since it sits where the replay performs.

**One gradient sweep across the whole lockup.** The signature and its mode word
each restarted the accent gradient, so "skribl pad" read as two balanced
sweeps. Both now run `userSpaceOnUse` in the shared 30-unit hand: the mark runs
0 -> the lockup's full width (`brand_sweep`, passed by the including page), and
each word starts at the matching NEGATIVE x, continuing the mark's sweep rather
than restarting it. Standalone includes default to the mark's own width.

**Three smaller manners, one costume change.** The status pill now yields to
open menus and sheets as it already did to drawers (the amber media warning was
sitting on the Flip menu). The restore banner clears the toolbar on phones --
its 20px anchor was written for a desktop where the bottom edge is empty air,
and on a phone it covered the tools until dismissed. Flip's Duplicate / Blank /
In-between stopped wearing dashed-and-hollow, which is this app's vocabulary
for "nothing here yet" (the paste ghost, the liquify reach) and wrong on three
of its most-used ACTIONS; they wear the page bar's recipe now, with the accent
plus that marks "this adds something". And the custom swatch keeps its rainbow
as a RING around the picked colour -- painting it solid made the one control
that opens the picker impersonate an eighth preset -- while recents record the
COMMITTED pick (`change`) instead of every shade a drag passes through
(`input`), which had been filling the row with gradations of one colour.

**CI stopped costing more than it proved.** A single productive day ran the
full three-job harness thirty times and consumed the account's entire monthly
Actions allowance. Pull requests now run one smoke job; the full battery runs
on pushes to main and manual dispatch. The trim is safe because the affected
suites run locally before every push and their counts are quoted in the PR:
CI's job on a PR is to catch a broken push, not to re-verify a verified one.
`CLAUDE.md` now carries the owner's standing rule -- ask before taking any
action that could create or increase a bill on their accounts -- because the
lesson generalises past Actions minutes to every metered thing a host sells.

## v273 -- A posted loop is mono, and the docs stop describing a tree that shrank

Two pieces of work, and the second is the reason the first took a whole session
to reach.

**The documents were wrong in a way that cost real time.** A session read
START-HERE's known-open list, picked what it said were the two most valuable
open items, and found both already shipped -- the touches[0] contact-identity
lead closed in v264, and the post-time loop crop closed in v102 and re-fixed as
BUG B in v210. A third pick, "PostgreSQL is UNVERIFIED, not passing", had been
passing for releases. Nothing in the tree was broken; the map was.

The sweep that followed was mechanical, not editorial, because reading is what
had failed:

  * Numbers. START-HERE's opening block carried nine byte figures measured at
    v199 and never revisited. Its "next step, and the honest distance" section
    argued at length that the player could not reach its 153,600 B JS target
    without a function-relocation refactor -- while verify_jsstrip.py asserted,
    every run, that the target IS reached, comfortably, and that the
    serve-time comment strip is what got there without moving a function. The
    document and the suite had contradicted each other for a long time and only
    the suite ran. Both are now pointers to the suites that generate the
    figures, which is what the file's own preamble had been preaching fifteen
    lines above the offending block.

  * Claims. "The 641px cliff is real and STILL unaddressed. One pixel takes
    Pad's bar from 359px to 565px." Measured on this tree: 608.0px at 640 to
    569.3px at 641 -- the other direction, different magnitude -- with
    scrollWidth equal to clientWidth at every width on both surfaces, and the
    size-class remedy the line asked for shipped as lib/sizeclass.js.

  * Absences, which reading cannot find. /library is registered by the
    blueprint and appeared in NO document, so a host mounting Skribl got that
    route in their own URL space with no warning. Six SKRIBL_* environment
    variables were read at runtime and named nowhere a deployer looks; three of
    them change security behaviour.

**The gates now carry what the prose could not.** verify_docs.py already had
the right mechanism -- a capability, the suite that proves it, and the phrasings
that would deny it -- and its pattern list was simply too literal: it matched
"NOT yet verified on PostgreSQL across processes" and missed "PostgreSQL is
UNVERIFIED, not passing". The patterns now match the capability plus a denial
word near it, two new claims cover the JS target and the player carves, and two
new checks assert that every registered route and every SKRIBL_* the code reads
is named somewhere. All six were mutation-tested against the ACTUAL historical
sentences rather than invented ones.

START-HERE also gained a loud divider at the start of its historical band, and
three headings inside it that asserted currency in their own words -- "the
newest feature", "most of it still to do", "will not extract" -- now say when
they were true.

**A posted loop is mono; an exported one is not.** The crop has been post-only
since v102, but the clip was stored at the source's channel count: half the
bytes of the largest term in a music-bearing payload_json row, and those rows
sit inline in Postgres. Measured on verify_loopcap's fixture, an 8s loop went
1.41 MB to 0.71 MB. lib/postedaudio.js is loaded by the two editor templates
only, for two reasons each caught by a suite rather than by review: the player
loads audioloop.js and never posts, so putting the bake there blew
verify_player_isolation.py's byte ratchet; and a one-line shim in both editors
would have been a 61st shared name against verify_surfaces.py's ratchet of 60,
so both post paths call the module directly.

**22.05 kHz WAS TRIED AND REVERTED, and this is the part to remember.** It
halves the bytes again and puts an audible click on every loop repeat:
verify_audio.py's seam check goes from 1.32x the mid-loop delta to 12.36x. The
fault is not in the resampler -- adding a wrapping box filter left the seam
figure byte-identical at 0.13114, and dropping the resample restored the exact
pre-change 1.32x. decodeAudioData resamples anything whose rate differs from
the AudioContext's and zero-pads the edges, so the clip's end stops joining its
start, which is the whole game for something played with loop = true. A
compressed codec hits the same wall, and Opus-in-WebM additionally does not
decode on iOS Safari before 17.4, where it fails silently as a Skribl with no
music. The owner chose the certain 2x over the conditional 4x.

**A second audit pass, asked for after the first seal, found the deeper half.**
The first pass checked what the documents SAID. This one checked what they
never mentioned, which reading cannot find.

**Twenty-eight stale hand-typed assertion counts.** CLAUDE.md has always said no
document may hand-type an assertion count outside the generated stanza. The
tree-hash half of that rule was enforced; the count half never was. Thirty-six
typed per-suite counts existed across six files and twenty-eight were wrong --
harness/README.md alone carried seventeen inside a code block, invisible to a
prose-scoped check, including verify_ux.py written as 24 against an actual 330.
A wrong number under the harness's own name is worse than no number. They are
gone from every document that describes the present, and enforced.

**FIVE OF THE NINE CARVES WERE NEVER GUARDED.** The player-isolation carve is
the architectural guarantee this project spends most of its words on, and the
assertion named four editor_*.js files in a hardcoded tuple. There are nine.
editor_draft, editor_export, editor_menu, editor_post and editor_tune could
each have drifted back onto every shared link with nothing to catch it, and a
tenth carve would have been unguarded on the day it landed. Two of the five
appeared in no document at all despite each calling itself a carve in its own
header. The list is read off disk now. Three documents that said "four" say
nine and name them.

**The harness's dependencies were declared nowhere.** harness/README.md said
`pip install flask_sqlalchemy` -- one package of the eight a run needs -- and
neither Playwright nor Pillow appeared in any file. harness/requirements.txt now
carries both, deliberately NOT the root requirements.txt: nothing under skribl/
imports PIL, only three suites do, and requirements.txt is the application
runtime whose hashed lock every deploy installs. Pillow's absence is not a loud
failure either: verify_sizeclass guards its pixel assertions on PIL importing,
so without it the suite reports 81/82 -- one tidy failure -- while EIGHT
assertions silently do not run.

**Two comments described a layout that had been dead for releases**, both in the
files a reader would most trust on the subject: verify_player_isolation.py still
said "the player links the WHOLE of styles.css", and skribl_player.html's own
justification for linking player.css instead cited a styles.css size less than
half what it had grown to.

**Every gate added across both passes was mutation-tested**, and two of them
failed that test first time and were fixed because of it: the dependency check
substring-searched the file, so deleting the Pillow requirement left the word
"Pillow" in the comment above it and the gate passed on a mention rather than a
declaration; and the count check reported a line forty lines from the real
offender, because re.sub had removed the stanza's LINES and shifted every number
after it. A gate that has not been shown to fail on the real defect is a gate
nobody has tested.

## v274 -- The 500 v264 fixed had a twin one function away

**The bug.** Under write contention on SQLite the db-backed rate limiter
answered some concurrent posts with 500 instead of 429. v264 had already
diagnosed and fixed exactly this, in `_db_rate_reserve_post`: a locked store
must refuse a slot rather than raise, because "a limiter that cannot account
for a slot must not hand one out". What it did not do was look one function up.

`_db_rate_limited` charges the ATTEMPTS bucket, and attempts are charged on
EVERY request, before a post slot is ever reserved. So the v264 fix moved the
500 rather than removing it: under contention the request now died one step
earlier, with the identical symptom. Nine releases later it was still there.

**Why nine releases: it is INTERMITTENT, so it reads as a flake.** Nothing
pinned it. The only cover was verify_review's #13b -- twelve threads racing for
two slots -- which needs real write contention to fire and passes on any idle
machine. It depends on how loaded the runner happens to be: main's sqlite job
FAILED at e2bbfdd (run 288) and PASSED at ff19fc9 (run 292) with the bug
present and unchanged in both. A steady red gets fixed; a red that goes green
on the next push gets called flaky and waved past, which is what happened here
nine times over.

Two structural reasons it never showed up locally. **release_run.py runs 44
SEPARATE batches on a quiet machine; CI runs all 89 suites in ONE contended
invocation** -- the seal and CI do not test the same thing, and CI's mode is
the one that catches this class. And the suite's subprocess servers send stderr
to DEVNULL, so the one artefact that names the cause was being discarded on
every run.

**Found by the server log, not by reasoning.** The suite sends its subprocess
servers' stderr to DEVNULL, so the traceback had never been seen. Captured it,
and the failing statement named the bucket itself:

    [parameters: ('attempts', 'ceb36866...', ..., 'committed')]
    sqlite3.OperationalError: database is locked

That is the project's own rule -- check the server log before theorising about
the client -- and it turned a guess about which of two writers was at fault
into a fact in one run.

**The fix refuses, and refusing is the safe direction.** Same shape and same
reasoning as v264's: catch the OperationalError, log, return "limited". Failing
OPEN here would have been worse than the 500 it replaces, because it would let
anyone able to induce write contention walk straight through the flood
protection this bucket exists to provide. The cost is a poster occasionally
told to retry while the store is briefly contended, which is what 429 means,
instead of being shown a server error for a Skribl still safely in their
browser.

**Both writers are now pinned deterministically** (#13c), by raising the error
directly instead of racing for it -- including v264's own fix, which had been
unpinned since the day it shipped. Verified by reverting the fix: the suite
dies on the attempts INSERT; restored, 283/283. And under the twelve-spinner
CPU load that reproduced CI exactly, #13b went from 278/281 to 281/281 with no
assertion weakened -- it still demands exactly two winners, ten refusals, and
no other status.

**A test that only fails under load is a test that does not run.**

## v275 -- A Skribl learns to live inside somebody else's post

Four surfaces now play a Skribl and only one of them is ours. The sealed player
is a PAGE -- `/s/<id>`, app.js plus eight modules, an app shell, a full
transport -- and twenty of those in a feed is not a feed. So this release adds
a second, small playback implementation and the three surfaces that need it:
a post, a draft composer, a profile tab. It also fixes the picture all three
of them show when they are not playing.

**The decision that shapes everything else: A SECOND PLAYBACK IMPLEMENTATION,
accepted deliberately.** `verify_sharedrules.py` has warned for many releases
that two implementations of one rule drift, and it is right; the failure mode
here is worse than usual, because the AUTHOR opens `/s/<id>`, sees it look
correct, and every viewer scrolling past a feed sees something else. It was
still the right call -- embedding the page was never available, and a feed that
loads a 150 KB player per post is not a feed. Three things hold the two
together, and they are the price of the decision:

  * the RULES come out of `lib/` rather than being restated -- `holdtiming.js`
    for what a hold means, `canvassizes.js` for a legacy payload's shape;
  * what is genuinely retyped (the capped-gap timeline, `drawDot`/`drawLine`)
    is retyped VERBATIM and names its origin in app.js at the line;
  * `verify_inline.py` plays the SAME posted drawing in both players off the
    same clock and compares where each has reached and what each has drawn.

**The comparison's first numbers were worthless, and mutation is what said so.**
A 32x32 grid at tolerance 48 passed while the in-post player was reading a BLANK
canvas -- the selector matched the first post in the feed rather than the one
playing -- and passed AGAIN with the gap cap deliberately set to 500 ms, with
the two players 0.58 and 0.34 through the same drawing. A tolerance loose enough
to admit a blank canvas is not a tolerance. It is 96x96 at tolerance 18 now,
floor-subtracted (the two surfaces paint the drawing's ground in different
places -- one on the canvas, one on `.canvas-wrap` behind it, so compared
absolutely all 9,216 cells differ and the assertion becomes a claim about paint
order), plus a scale-free ink-mass ratio.

**COMPOSE MODE PUBLISHES NOTHING, and that is forced rather than chosen.**
"Add to post" hands the host the PAYLOAD, not an id. `POST /api/skribls` is
create-only -- routes.py registers one POST and two GETs -- so "publish on add,
republish on edit" orphans a skribl per edit, each having spent a slot of the
author's posting quota, and an abandoned draft leaves a published, shareable
skribl the host has no way to withdraw. `verify_compose.py`'s main instrument is
therefore A COUNT OF POSTS rather than a "does it work": zero while attaching,
zero after an edit, exactly one when the host posts.

**One builder, two endings.** `editor_post.js`'s `submit()` was split so that
everything preparing a payload for posting -- serialise, share-card thumbnail,
mono audio bake -- is now `buildPostPayload()`, called by both endings. A
composed skribl is byte-for-byte a Pad-posted one. Two paths each preparing
"the payload, but for posting" is precisely the shape of that file's own BUG B:
a post-time step that silently stopped running on one path while the metadata
looked identical.

**The encoding rule was wrong by 16x, and the in-post player is what made it
matter.** The share-card builder chose PNG for line art and JPEG for photos, on
the recorded grounds that PNG is both smaller and crisper for lines. Measured on
an actual card: **451,824 B as PNG against 28,062 B as JPEG q0.92.** The cause
is the accent wash -- Chromium DITHERS a canvas gradient, scattering per-pixel
noise across all 1,200x630 that PNG cannot compress -- so the rule was true
before the wash existed and was never re-checked. It survived because a 450 KB
card is not WRONG, only expensive, and nobody looks at the byte count of their
own unfurl. Turning that image into the idle frame of every post in a feed is
what turned expensive into unusable: a screenful was over five megabytes to show
twelve thumbnails. The fix is to stop having a rule -- encode both, keep the
smaller. Real cards are ~20 KB, and `verify_sharecard.py` pins a 200,000 B
ceiling, which is the check that would have caught the original.

**Flip had never built a share card at all.** `buildShareCardDataURL()` lived in
`editor_post.js`, which is PAD-ONLY, and `flip.js` set no `thumbnail`. So every
Flip Skribl ever posted fell back to the static branded og-card in three places
at once -- its `/s/<id>` unfurl, its idle poster in a feed, its tile on a
profile. An advert where the drawing should be. Same shape as the title bug
`verify_flipmeta.py` records: a whole control surface built on one of the two
editors and never carried to the other.

**TWO MODULES, NOT ONE, and the byte ratchet is what said so.** The first cut
put the card COMPOSITOR beside its GEOMETRY in `lib/sharecard.js` -- which the
in-post player loads, because it crops the poster by `band()`. `verify_inline`'s
embed ratchet failed on the next run, correctly: 2 KB of canvas work shipped to
every feed page in the world, to composite a card a feed never makes. Split on
the rule `lib/postedaudio.js` already states -- THE READER IS NOT THE WRITER. A
host embeds the geometry and never the compositor, because a host never posts.

**The ratchet also caught PROSE.** Explaining the poster crop added 2,800 B of
comment to `inlineplayer.css` and pushed the embed past its limit -- correctly,
because `jsstrip.py` strips JavaScript RESPONSES and nothing strips CSS, so a
paragraph in that file ships to every host on every page. It moved into
`inlineplayer.js`'s header and the CSS kept the numbers and a pointer: same
words, a third of the weight. A ratchet that prices comments is a ratchet that
tells you where comments are free.

**The owner reversed a decision made three hours earlier, and the reversal is
recorded because the original reasoning was not wrong.** The in-post player
shipped with ONE viewer control -- mute -- on the argument that a feed is not a
media player and a Pad replay stopping dead on its finished drawing reads as a
broken GIF. Both halves are still true. What was missing is that some drawings
are two seconds long and a viewer may simply want them to stop. There are two
controls now, and the asymmetry between them is the decision:

    mute   PAGE-WIDE, session-remembered, off by default
    loop   PER POST, not remembered, on by default

Sound is environmental -- someone in a quiet room wants it off for the whole
feed. Repeating is a property of the drawing in front of you, and a two-second
loop you want to watch twice says nothing about the next post.

**WHEN THE DRAWING STOPS, THE MUSIC STOPS, as ONE call rather than two.** The
end of a non-looping replay routes through `pause()`, which takes the audio down
in the same breath. It could have been a `cancelAnimationFrame` and a class
change, and then a finished drawing would sit there with a loop still playing
underneath -- a post that will not shut up, which is worse than one that never
started. `verify_inline.py` measures this on the AUDIO GRAPH through the
analyser tap `verify_player_isolation.py` uses, because "the music stops" is a
claim about sound and cannot be checked from the DOM. Mutation-tested: stop the
drawing without routing through `pause()` and the peak reads 71 where it should
read 0.

**Three defects found by building compose mode, all real:**

  * `setState('idle')` hardcoded `'Post to Skribl'`, overwriting the label the
    TEMPLATE had rendered. Harmless duplicate string before compose mode
    existed; with it, the attach button relabelled itself to publishing the
    first time anything reset the sheet.
  * The post sheet stayed open after delivering. The host closes its overlay
    immediately so nobody sees it -- until the pad icon is pressed again, which
    reopens the SAME iframe with the sheet sitting over the canvas.
  * **The underlay repaint moved time.** `img.onload` called `render(elapsed,
    true)`, and `elapsed` is 0 while idle, so on a drawing with a photo or a
    base snapshot the underlay finishing its decode wiped the canvas and
    repainted the FIRST frame. Invisible on a posted skribl, where the poster
    hides it, and fatal on a draft, where idle IS the finished drawing: the
    composer showed an empty box. Every Pad recording carries a baseSnapshot,
    so this fired every time.

**`asset_url()` built a RELATIVE endpoint** (`url_for(".static")`), which
resolves against `request.blueprint` -- always Skribl's, while every caller so
far was a template Skribl itself rendered. The embed macros render on the HOST's
view, where a leading dot raises BuildError. It names the blueprint outright now,
which is identical inside Skribl's own pages and works everywhere else, and
`init_skribl()` registers `skribl_asset` as the ONE app-wide template global --
added, never overwritten.

**`POST /api/skribls` defaults to `unlisted` and Pad's composer has no
visibility control**, so nothing posted from Pad appears in `GET /api/skribls`.
The demo feed was empty on its first run and its suite was asserting against an
empty list. The default is correct -- it is what a link-sharing product should
do -- but it means a HOST's composer is what sends `"visibility": "public"`, and
the empty state says so now instead of telling you to go and post from the Pad.

**`library.js` had been drawing its own content.** It carried its own replay
engine and a table of hand-drawn motifs -- a bolt, a cassette, a smiley -- and
rendered those, while the route was registered the whole time, so a host
mounting Skribl served invented drawings out of their own URL space and
README.md carried a warning saying so. The problem was never the pretending: a
page that draws its own content cannot tell you whether the thing it previews
WORKS. It contains no player now; the stage is `inlineplayer.js` driven through
its handle, and `verify_library.py` gates that at the source by forbidding
`requestAnimationFrame` in the file.

**TWO OF THAT SUITE'S GATES WERE SUBSTRING SEARCHES THAT PASSED ON THEIR OWN
PROSE.** One looked for `offset` and matched a comment explaining why offset
paging is wrong; one looked for `cassette` and matched a description of the
motifs it had just deleted. This is the same failure a v273 gate made by
searching for "Pillow" and matching a comment that mentioned it -- twice in
three releases, so it is a pattern rather than a slip. They match SYNTAX now
(`offset=`), and the second became a check on the DOCUMENTS instead: a page that
stops lying while its docs keep saying the old thing has moved the lie, not
removed it.

**A route literal in client JS, in the one file whose comment says it never
uses one.** `inlineplayer.js` read its endpoint from `data-skribl-api` and fell
back to `'/api/skribls'`. On a host mounting the blueprint under a prefix that
fallback fetches a path that does not exist, and fails QUIETLY into the box's
error panel -- the exact defect the surrounding comment describes as the reason
the attribute exists. `verify_seam.py` SECTION 1 caught it. There is no fallback
now: a box with no endpoint says it is not wired up, which is the honest
failure. Worth recording because the comment was written by the same hand, in
the same file, in the same hour as the line that contradicted it. A comment is
not a gate.

**Two suites broke on this release and both were right to.**
`verify_flipmeta.py` read a POST body as JSON, and `lib/posted.js` gzips any
body over 4,096 B -- its one-stroke fixture sat under that until a 25 KB card
was attached, so it inflates now. `verify_library.py`'s search matched
`verify_inline.py`'s "Harness fixture A" as well as its own, because
`run_harness.sh` gives ONE database to every suite in an invocation; its
fixtures carry a per-run token now. Exactly the cross-suite state coupling that
passes a seal and fails CI.

**Known gap, named rather than hidden:** the in-post player has no wet/dry
stroke compositor, so a sub-100%-opacity stroke beads at its overlaps where it
does not on `/s/<id>`. The fixture draws opaque deliberately, so the pixel
assertion stays meaningful instead of being quietly tolerant of a gap it cannot
see. And the poster crop is exact vertically and cannot be horizontally: the
drawing's width depends on its own aspect, and `canvasSize` lives inside
`payload_json` which `GET /api/skribls` defers on purpose. The box is 16:9
because that is the widest canvas, so a symmetric crop can only ever remove
ground. The real fix is canvas size as a real COLUMN, which is a migration.

## v276 -- The drop-in stops being a description and becomes a thing you can run

v275 made a Skribl displayable inside somebody else's post. It did not make the
integration OBTAINABLE: a host still had to read four documents and write the
same hundred and fifty lines everyone else writes. This release closes that,
and every piece of it was shaped by the same question -- what does the host
actually have to type, and what have we made them type twice?

**`skribl.create_post()`, and the shape of host it exists for.** `POST
/api/skribls` serves a host whose composer is a BROWSER. skribls.net's is a
server-side FORM: the author types words, attaches things, and their browser
sends one ordinary POST to the host's own view. That host already has the
payload, has authenticated the author and has checked its own CSRF token, so
turning round and POSTing to its own JSON endpoint buys it a second request, a
second authentication, a second CSRF exchange and -- the part that actually
breaks -- a SEPARATE TRANSACTION. A failure between the two leaves a Skribl
nothing points at, or a post pointing at a Skribl that was never stored. The
function runs in the caller's request, on the caller's session, so one commit
makes the Skribl and the host's own row durable together.

**IT IS A CARVE, NOT A SECOND PATH, and the direction is the whole point.**
Everything in `skribl/creation.py` was MOVED out of `create_skribl`'s body; the
route calls it and does nothing to the payload itself. Two functions that both
"validate a payload and insert a post" is precisely the shape of the bug
`editor_post.js` records as its own BUG B, where a post-time step silently
stopped running on one of two paths while the metadata looked identical. What
stayed in the route is exactly what is HTTP: the two rate budgets, CSRF, the
`Idempotency-Key` header, and jsonify.

**THE RATE LIMITER CANNOT FOLLOW, and finding out why was worth more than the
assertion.** The plan was to state in the docs that a host calling create_post
is not throttled by Skribl. Then the mutation written to prove the assertion --
make create_post charge the limiter -- never reached the assertion at all: it
died on "Working outside of request context", because `_client_ip()` reads the
Flask `request` and the reservation is settled in a Flask teardown. So it is not
a policy that a host owns abuse control on its own path; it is a fact about what
the limiter is made of, and a host that assumes otherwise has an unlimited
posting endpoint with no sign of it. `docs/INTEGRATION.md` says so in those
words.

**The instrument for a carve is AGREEMENT.** `verify_createpost.py` drives ten
bad payloads through BOTH callers from one table and compares status and
message. "The route calls it" is a fact about today's tree; the danger is a rule
added to one side only, and the mutation for that (a rejection message given to
the route alone) fails the comparison and prints both strings. Same instrument
`verify_inline.py` points at the two playback implementations.

**`lib/composehost.js`: the pad button's lifecycle, once.** Four rules that are
the same in every host and easy to get subtly wrong -- the editor's `src` set on
first open and never in markup, the payload pushed into an already-loaded
editor, `clear()` resetting the frame, the origin checked inbound and targeted
outbound. A host wires its own buttons to a handle.

**AND ITS OWN COMMENT WAS WRONG ABOUT THE MOST IMPORTANT RULE.** It claimed
that without the re-edit push the editor "reopens EMPTY over a drawing the draft
is still holding". It does not: the iframe kept the drawing on its canvas, so a
host answering only `ready` looks correct. What such a host is really doing is
trusting the editor's retained state, which is a coincidence rather than a
contract -- the rule earns its place when the draft's payload and the editor's
differ, which is a host calling `setPayload()` to re-edit a saved post. Written
from reasoning, corrected by a mutation that failed to fail.

**AND THE SUITE DID NOT COVER IT.** Disabling that rule left `verify_compose`
at a clean 29/29, because "re-opening the editor brings the drawing back"
measures the editor's leftover ink. It counts the `skribl:compose:load` message
now: 0 under the mutation, while the ink assertion stays green beside it. In the
same file, one assertion was `check(..., True, "src is set on open")` -- an
assertion of the literal True, in the file that names lazy loading as a rule.

**TWO BYTE RATCHETS, BECAUSE THEY ARE TWO COSTS.** `verify_inline` scraped every
`/static/skribl/` URL on the feed page, so a compose module would have been
charged to every host page that merely DISPLAYS Skribls. Display and compose are
paid by different pages and now have different budgets; blurring them into one
number would have hidden whichever grew. Same reader-is-not-the-writer split
that put the card compositor in `lib/postedcard.js`.

**`examples/host_app`, and why an example needs a suite.** Every other document
here DESCRIBES the drop-in. This one is the drop-in -- a separate Flask site with
its own users and posts, mounting the blueprint under a PREFIX, composing with a
server-side form. `verify_example.py` boots it as a real server on its own port
and drives a real browser through drawing and posting, then checks on a FRESH
connection that the host's post row and the Skribl were committed together. An
example nothing runs is a document that goes stale silently, which is the
failure mode this tree has been bitten by repeatedly.

**BUILDING IT FOUND THE PLAYER'S MARKUP WRITTEN THREE TIMES.** A draft has no
public id and the macro required one, so `skribl_feed.html` hand-copied twenty
lines of the macro's internals for its composer box, `skribl_library.html`
copied a variant for its stage, and the example was about to be the third. This
is the general lesson of the release: **the third caller is what exposes the
duplication, because the first two each had a reason.** The insides are one
macro now with a `skribl_inline_draft(id, controls)` entry point, and the gate
added for it -- no template outside the macro file may write the player's
internal class names -- FAILED ON ITS FIRST RUN and named the library. The third
copy was found rather than guessed at.

**A route literal in the one file whose comment says it never uses one.**
`inlineplayer.js` read its endpoint from `data-skribl-api` and fell back to
`'/api/skribls'`. Under a prefix that fetches a path that does not exist and
fails quietly into the box's error panel -- the exact defect the surrounding
comment describes as the reason the attribute exists. `verify_seam.py` caught
it. There is no fallback now. Recorded because the comment and the line that
contradicted it were written by the same hand, in the same file, in the same
hour: a comment is not a gate.

**And a stale number nothing was checking.** `START-HERE.md` typed two counts in
one sentence -- "44 SEPARATE batches" and "all 93 suites". `verify_docs` caught
the suite count. Nothing checks the batch count and it was stale too. Both
removed rather than updated, per that file's own rule about numbers in prose.

## v277 -- Five things the owner found on a phone, and one of them is not verified

Every change in this release came from the owner using the app on an iPhone
rather than from a suite going red, which is worth saying at the top because it
is the pattern: the harness runs Chromium on Linux, and four of the five defects
below are invisible there by construction.

**The post sheet gets the toolbar's music mark.** A Skribl with a loop and one
without looked identical at the moment of posting. The owner's sketch beat the
design I proposed -- I offered a labelled pill that BORROWED the tool row's
green; they asked why not use the tool row's actual mark. It is cleaner, needs
no learning, and dropping the text label dissolved my own objection to putting
it on the header, which was an argument against a variable-width chip reflowing
against a variable-width string and not against a 17px marker.

ONE GLYPH, NOT TWO THAT AGREE TODAY. The path data was about to be written a
second time, so it is a Jinja macro called by both callers, and the suite
compares the two as RENDERED rather than grepping the template -- a copy would
satisfy any grep and drift the first time either was redrawn. The dot's POSITION
is shared too: `.post-sound` joins `.tool-open`'s selector rather than restating
a calc whose 0.4 offset carries an essay deriving it from measured clearances at
six button tiers.

**Exports could not be named.** Every media export was a hardcoded literal --
skribl.gif, skribl.png, skribl-flip.mp4 -- so two exports of one drawing arrived
as "skribl.gif" and "skribl (1).gif" with nothing to tell them apart, and
titling the drawing changed none of it. Drafts had been named properly through
`lib/nametab.js` for releases; the media exports were simply never wired to it.
A field in the export sheet, seeded from the title, edited independently:
naming an export is not renaming the drawing.

**PLACING THAT FIELD'S LABEL FOUND A BUG NO SUITE COULD SEE.**
`.export-optlbl` was defined only in `flip.css`, which Pad does not load, and
the shared export partial uses that class for the GIF toggle's "Background"
label outside the flip-only block. Pad had been rendering it at browser-default
size for several releases. `verify_exportui`'s sweep could not catch it because
it concatenates styles.css AND flip.css, so a class styled for ONE surface
passes as if styled for both -- an assertion that reads as coverage and is not.
The sweep is split by surface now, and the hole was demonstrated by reverting
the class: the new gate fails, the old one still passes.

**The GIF background control was a banner.** `width: 100%`, commented "Full
width so both labels fit", which did not survive being measured: the labels need
about 200px of a 330px card. What full width actually bought was a 160px violet
pill, 41% of a phone screen and the brightest thing on a sheet whose actual
actions are three format buttons. It is an inline row now. The mutation
restoring full width fails in the most telling way -- both labels forced to
143px, so the sliding pill cannot tell them apart -- which is a better argument
against the old rule than the one I had.

**And the green was too dull.** #1bcf8f -> #30e8a7. It was never short of
CONTRAST (9.6:1, measured) but short of VIVIDNESS, and it is spent almost
entirely on 6-7px dots where hue reads weakly and lightness carries the signal.
Three rules hardcoded `rgba(27, 207, 143, ...)`, the token's own RGB, and would
have kept the old hue silently; they read a `--good-rgb` companion now. The
light theme's darker green is deliberately unchanged -- it sits on white, where
brighter is worse.

**iOS SILENCES WEB AUDIO WHEN THE RINGER SWITCH IS OFF, AND THIS IS THE ONE
THAT MATTERS.** The owner reported Preview Loop playing no sound. Test Seam, on
the same phone with the same file, played fine. Test Seam is a plain `<audio>`
element; Preview Loop is Web Audio, and iOS routes Web Audio into an "ambient"
session the hardware switch mutes while leaving `<audio>` alone.

The preview button is the least of it. `/s/<id>` and the in-post player are both
Web Audio, so on any iPhone in silent mode a shared link's music and every feed
post's music are silent too -- for a component whose entire purpose is playing
inside somebody else's feed, that is the feature not working.

**Why every existing guard missed it, and this is the lesson worth keeping.**
app.js carries an elaborate hand-off for a context that never unlocks, built
over several releases, and every one of its tests is `state !== 'running'`. In
silent mode the context reaches `running` perfectly well and is merely
inaudible. So all the guards pass, the native `<audio>` fallback is deliberately
suppressed, and the result is confident silence. The file's own warning --
"A source object existing is NOT the same as audible playback" -- turns out to
apply one level further out than where it was written. A guard is only as good
as the failure it imagines.

**THIS RELEASE SEALS AN UNVERIFIED FIX, DELIBERATELY AND WITH IT SAID OUT LOUD.**
`lib/audiosession.js` holds a silent looping `<audio>` element, which moves the
session to "playback". Claimed only on a gesture that asks for sound -- the
unmute tap, the Preview button -- never at load, because a held session shows
Skribl as playing media in Control Center; overriding the switch is defensible
only because sound here is never automatic. But Chromium on Linux has no ringer
switch. `verify_audiosession.py` pins the MECHANISM -- one element, silent,
looping, playing, idempotent, released, loaded on all four surfaces -- and
prints a closing line saying none of it proves an iPhone is audible. It is the
same limit app.js already recorded: "Desktop never showed it ... including in
the harness." **A green seal is not evidence this works.** The phone is.

It cost the player's byte ratchets, which is the budget this project guards
hardest: JS 151,845 -> 153,000 and HTML 10,800 -> 10,900, leaving ~600 B to the
153,600 target. The embed ratchet moved too, 27,500 -> 29,500. Both raises are
recorded at the ratchet with the reason, and the module was shrunk first -- a
byte-by-byte WAV builder read better and cost 1,650 B against ~450 for a base64
constant, and the player's ratchet is not the place to spend 1,200 B on
legibility.

**One gap this closed that let a person find a bug before a suite did:**
`verify_audiostate` drove Preview Loop under a HUNG unlock and asserted the
fallback plumbing in detail, but nothing anywhere asserted that preview produces
a sound at all.

**AND I PUT A LIVE CLOCK INTO A COMPARED SCENE.** The export field seeded itself
from `nametab.get()`, which falls back to a timestamped auto-name.
`verify_cssplit` renders the export scene twice in one run and compares the
pixels, so the two captures straddled a clock tick and editor-export went
intermittently red -- the diff box moving one pixel between runs, which is the
tell. `lib/nametab.js`'s own header warns about exactly this, one function above
the one I wrote: "a live timestamp there renders differently between two frames
and makes any pixel comparison of the editor flaky (verify_cssplit)". It seeds
only a typed title now and leaves an unnamed drawing's field empty behind a
static placeholder; the filename still resolves the timestamp at export time.

