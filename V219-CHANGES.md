# v219 — what changed since the sealed v214

## READ THIS FIRST: this is now a SEAL

**A full harness run stands behind these files.** `harness/RELEASE.md` and
`harness/LAST-RUN.txt` are generated from that run and describe THIS tree hash.

This document was originally written when that was NOT true — v219 was built and
shipped as a BUILD, with the release evidence deliberately left at v214 rather
than restamped, because stamping it would have made the build claim evidence it
did not have. That was the right call and it is recorded here rather than
deleted. The mechanical checks from that stage still stand — `node --check` on
every changed script, a Jinja parse of every template, a div-balance check on
both editors, rendered geometry in headless Chromium — and the run adds what they
could not: the app running, with every suite reporting.

Read the skip list in RELEASE.md's header before reading the result as complete
coverage. A skip is not coverage; that is why the generator prints it by name.

Every number below was re-measured against THIS tree immediately before writing.
None is carried forward from an earlier build — carrying numbers forward is the
mistake that produced the stale claims this document replaces.

---

## Measured, on this build

Pad's toolbar — Pen/Eraser/Shape, undo, redo, colour, image, music (+ magnify at
641px and up):

    320px   bar 288px   WRAPS (safety net)   reachable   page-spill 0
    360px   bar 328px   one row              reachable   page-spill 0
    375px   bar 343px   one row              reachable   page-spill 0
    393px   bar 361px   one row              reachable   page-spill 0
    430px   bar 398px   one row              reachable   page-spill 0
    641px   bar 565px   one row (+ magnify)  reachable   page-spill 0

Flip's toolbar, same control set in the same order:

    320px   bar 300px   one row, SCROLLS     reachable   page-spill 0
    360px   bar 340px   one row              reachable   page-spill 0
    375px   bar 355px   one row              reachable   page-spill 0
    393px   bar 373px   one row              reachable   page-spill 0
    430px   bar 410px   one row              reachable   page-spill 0
    641px   bar 619px   one row              reachable   page-spill 0

Smallest rendered control: 34px below 393px, 36px from 393px, 40px on desktop.
Measured on the FULL rendered page, not an extracted fragment — a fragment
measures ~2px narrower because it lacks the surrounding layout context, and
quoting the fragment number would be the same class of small untruth this
document exists to remove.

Header, all three states, with the wordmark collapsing to logo-only under
pressure exactly as `fitBrand()` intends:

    idle        360px +14px   375px +19px   393px +37px
    recording   360px +109px  375px +124px  393px +142px
    review      360px +28px   375px +43px   393px +61px

Nothing clips. Nothing spills the page horizontally. Both editors keep every
control reachable at 320px — Pad by wrapping, Flip by scrolling.

---

## The width policy, decided this session

**360px is the design target.** It must work properly, on one row. It is a very
common Android width, so a two-row bar there is not a rare fallback.

**320px is the safety net, not a design target.** It is Display Zoom on a modern
iPhone — an accessibility setting, not a legacy device — so it must DEGRADE
rather than break.

The two surfaces degrade differently and both are correct. Pad wraps to a taller
bar. Flip scrolls, because `flip.css` sets `flex-wrap: nowrap; overflow-x: auto`
below 560px on purpose: *"keep the bottom tool row on ONE line on phones (music
was wrapping)"*. `verify_layout.py` asserts REACHABILITY rather than a particular
mechanism — an earlier version asserted no-overflow and would have failed Flip's
scroll row as though a deliberate decision were a defect.

---

## Hit regions, separated from glyph size

Measured before the change: every toolbar control was 34–36px on a phone AND
adjacent targets had a 0px gap, so a mis-tap landed on a neighbour rather than on
nothing. Apple's guidance is a 44pt control.

**The glyph and the target are not the same thing.** The visible controls keep
their size; the touchable region is now 44px tall on every control, both
surfaces, 320→1024px. Verified by `elementFromPoint` at the top and bottom edge
of each control's 44px band — not by reading rectangles, which is the check that
would have missed the defect below.

Two mechanisms, because the controls are not alike. Standalone controls get an
invisible 44px band from a pseudo-element, which takes no layout space and is
free in a 68px bar. Buttons inside `.tool-group` cannot use that — the group is
`overflow: hidden` and clips any band on its children — so they are given a 44px
minimum height directly.

**That exposed a real defect on Flip.** Its tool group had a FIXED height plus
padding and `overflow: hidden`, so it was clipping the bottom 4px of its own
44px buttons: `getBoundingClientRect` reported 44px while the hit-testable area
was 36px. **A control whose measured size and touchable size disagree is worse
than a small one, because measurement says it is fine.** Fixed with
`min-height` and `height: auto`.

**Width was NOT fixed, and the arithmetic is why:** eight controls at 44px wide
plus gaps and padding need 385px, against 336 available at 360px, 351 at 375 and
369 at 393 — over by 49, 34 and 16px. Widening would make adjacent hit regions
OVERLAP, which turns a small target into an ambiguous one. A full 44×44 needs one
fewer control in the phone row — which `DESIGN-DIRECTION.md` delivers by design
rather than by shaving.

## Bugs fixed

**Drawing was laggy, and the cause was a live `conic-gradient`.** The colour
swatch's spectrum ring was a CSS gradient sitting inside `.toolbar`, which
carries `backdrop-filter: blur(14px)`. That layer recomposites every frame the
canvas behind it changes — every frame while you draw — and a live gradient made
each recomposite expensive enough to drop stroke points. Confirmed by A/B on
device: identical builds, gradient versus flat colour, laggy versus smooth. The
ring is now a pre-rendered 2.7KB PNG data URI; a static image cannot be
re-rasterised.

Three other hypotheses were eliminated by measurement and are recorded so nobody
re-tests them: the segslider trackers (0.4ms across 600 stroke segments), forced
layout per pointer move (this build measured FASTER than v214), and DOM node
count (identical).

**The Air brush beaded on every tool change.** `setTool()` calls
`SkriblSelectTool.clear()` on every tool change, which called `selRepaint()`,
which repainted the ENTIRE drawing by passing the raw `drawDot`/`drawLine`
painters straight to `replayTimelineToCanvas`. Painted that way a see-through
stroke's own overlaps stack at every captured point — precisely what stroke
layers exists to prevent, undone by a repaint. Live drawing looked right because
it takes the wet/dry path; the beads appeared the moment anything called
`selRepaint`, and picking the eraser calls it.

Measured, one 22%-alpha stroke painted both ways, reading the alpha profile
along it:

    segment by segment      alpha spread 153   <- the beads
    solid then composite    alpha spread  50   <- soft edge only

`selRepaint` was the ONLY repaint in the editor bypassing
`makeStrokeCompositor`. Preview, playback and all three export paths already
routed through it; every other raw-painter call is the `else` branch of a
`strokeLayersOn()` check. This one had no branch at all. `selClear()` now also
returns early when nothing is selected.

**Flip's tool pill did not work, and Pad's was misplaced.** Both computed
`activeBtn.offsetLeft - group.offsetLeft`. `.tool-group` is `position: relative`
and therefore the button's offsetParent, so `offsetLeft` is ALREADY relative to
the group — subtracting the group's own offset is a double subtraction. On Pad it
was a few pixels out; on Flip the group sits after the colour and media controls,
so the offset is large and the pill landed clear off its button, which reads as
the slider simply not working. Both now measure against the group's padding,
which is what `.tool-slider`'s `left` is matched to, and both re-place on
ResizeObserver, resize, orientationchange and `fonts.ready` — one timed call is
not enough on a phone, where the bar is often laid out later.

**Leaving Pad could silently drop attached media.** `flipBtn` was a bare
`<a href="/flip">` with no guard anywhere in the tree. Pad now confirms first —
but only when there is something to lose. Pad's autosave keeps STROKES, not
media: photo and audio bytes never fit in localStorage, which is why the status
pill reads *"Saved without media"* when either is attached. So the confirm fires
on `photoBg || currentAudioBuffer` and says what is actually lost. Flip has NO
guard, deliberately: it persists pages, music and the background image, so a
confirm there could only ever be a false alarm. **A confirm that is usually wrong
is one people learn to dismiss unread, and then it fails on the occasion that
mattered.**

**The draw drawer clipped every segmented control.** `.draw-inline` was written
for two children — its own comment says "Brush sizes + Smoothing on one line" —
with `flex: 1 1 0; min-width: 0`. It had grown to six. Each got a sixth of the
width, every control needed ~210px and got 206px, and `overflow: hidden`
swallowed the difference, so labels sat on top of their own controls and "Eraser"
was cut off. Measured identically on sealed v214 at every width up to 1280px, so
this was NOT a regression from this session's work. It now wraps, with a basis
equal to what a `.smooth-seg` actually needs.

**Flip's colour swatch had a leftover white border.** `.color-current` still
carried `border: 2px solid var(--text-primary)` and an inset highlight from when
the swatch was a plain disc. With the spectrum ring inside, they stacked into
three concentric circles. The ring is the edge now.

---

## Design changes

**Select removed from Pad.** Pad captures a performance; Select edited points
that were already recorded, so replay drew a stroke at its NEW position at its
OLD timestamp. That is a conflict with what Pad IS, not a bug in Select. It is
also what forced the history-aliasing fix (see the note in START-HERE — that fix
is now UNPINNED). Shape stays: it generates ordinary points in order, which is
on-model. Flip never had Select, so this also restores symmetry.

**The shape picker moved onto the Shape button.** It lived in the draw drawer,
three taps from the tool it configures. Now: tap Shape to select the tool and
open the picker, tap a kind to set it and close, tap Shape again to switch, tap
Pen or Eraser to leave. It is a RELOCATION — the popover holds the same
`#shapeSeg` markup with the same `data-shape` buttons, so `editor_shapes.js`
binds unchanged, including the part that already called `setTool('shape')`.

**The shape kind follows the pointer.** A small line/rect/oval badge beside the
cursor while Shape is active, on the same tracking as the eraser ring and
clearing on `touchcancel` too.

**Flip Mode moved into the ••• menu**, with the ORIGINAL book glyph from v214 and
a subtitle that explains it: *Draw a frame-by-frame animation*. A 40px icon could
not say what Flip Mode is, which is why it went unrecognised. It is still an
`<a href>` so open-in-new-tab works, and still `id="flipBtn"` so the guard binds.
**This also freed 40px of header, which is what closed the recording-header
overage** — see below.

**Pen / Background switcher** in the draw drawer. Stroke colour and background
were two identical dot grids stacked on each other meaning opposite things. One
segmented switcher now swaps which grid is shown; size, opacity and brush stay
put. They remain in ONE view deliberately: choosing a pen colour is relative to
what it sits on. Recent is pen-only and hides in Background mode.

**Magnify restored, desktop only** (641px+). The justification is the gesture,
not the space: a phone has pinch, a mouse has nothing.

**Flip's toolbar now orders controls like Pad** — tools, undo/redo, colour,
image, music. Flip had colour and media first, so the two editors read
left-to-right differently for the same controls.

---

## Corrected claims

**The recording header is NOT over budget, and the note saying so was stale.**
On sealed v214 it needed 396px against 355 available at 375px. That was true when
measured and is not true now: moving Flip into the ••• menu freed more than the
overage. Re-measured on this build, recording has **+124px of slack at 375px**
and the header stays one row with the wordmark collapsing to logo-only, which is
`fitBrand()` behaving as designed. `verify_layout.py` section 2 now PASSES; an
earlier README of mine said it was expected to fail, and that was wrong.

**The 44px tap-target claim was already corrected in START-HERE** and remains
corrected here: mobile ships 34–36px and 40px on desktop. 44px is a desktop
value that has not applied on phones for some time.

---

## Where this goes next

`DESIGN-DIRECTION.md` was written at this seal and should be read before the
engineering notes. The short version: this release answered *"how do we fit all
our features"* very carefully, and that is the wrong question. The next one asks
how much interface can be deleted before Skribl stops working.

Three measurements from this tree that make the case concrete:

    Flip's onion skinning already exists, on by default, and is invisible —
      buried in the tune panel behind a slider icon
    The accent colour is used 88 times (57 styles.css + 31 flip.css), so
      nothing can read as loud
    Pad shows 11 controls at rest; the target is five

Two prerequisites, both already known-open, both stated there as blocking any
visual work: **pointer identity** and **durable drafts**.

## Not done, and deliberately

* **The 641px cliff.** One pixel of resize takes Pad's bar from 359px to 565px
  and three buttons regain text labels. Anything from 560–640px gets the phone
  layout on a viewport with room to spare — iPad Split View, Stage Manager,
  foldables. Size classes, not a pixel breakpoint, is the fix.
* **Clear all** still lives at the foot of the draw drawer. It is a destructive
  document command, not a pen attribute, and belongs in the overflow menu on the
  normal undo stack — which would also delete the bespoke *Undo clear* button.
* **The stray line from the v213 bug report** remains unexplained and untested.
  `getPos`'s `e.touches[0]` assumes the first touch is the drawing finger.
  Note for whoever fixes it: **Flip has already solved this and Pad has not.**
  `flip.js` binds `pointerdown`/`pointermove`, captures with
  `setPointerCapture(e.pointerId)`, stores `strokePointerId`, and rejects foreign
  pointers with `if(drawing && e.pointerId !== strokePointerId) return;`. Pad
  (`editor_draw.js`) is still on `mousedown`/`touchstart` into `getPos`. So the
  migration is a PORT from a working in-tree implementation, not a design job.
  Pad is not unguarded — `startDraw` diverts to `beginPinch` on two touches and
  `continueDraw` returns while `pinching` — but those guard a touch INDEX, which
  is why a further guard cannot close it: after the first finger lifts,
  `touches[0]` is a different finger and every guard still reads true.
* **Flip's page bar has two buttons both labelled "Move"** doing opposite things.
