# v215 — what changed, and what is NOT true of this build

## READ THIS FIRST: this is a BUILD, not a SEAL

**No harness run stands behind these files.** The environment they were
produced in has no PostgreSQL, no running server, and no capacity for the ~25
minute checkpointed aggregate `release_run.py` needs. By this project's own
standard — evidence generated on one frozen tree — **this archive is
unverified**.

What WAS verified, mechanically:

    node --check skribl/static/app.js          syntax OK
    node --check skribl/static/flip.js         syntax OK
    jinja2 parse, all 14 templates             OK
    python3 -m ast, harness/verify_layout.py   OK
    Chromium geometry, both toolbars           measured, below

What was NOT verified: **anything requiring the app to run.** No suite was
executed. `harness/RELEASE.md` and `harness/LAST-RUN.txt` still describe v214
and have deliberately NOT been restamped, because stamping them would make this
build claim evidence it does not have.

**Before this is a release:** run the harness, stamp the docs, regenerate
`SHA256SUMS`, and expect `verify_layout.py` section 2 to fail (see below).

---

## Measured, in Chromium, against the real stylesheet

Pad's toolbar, with Image + Music + Magnify merged into one Media control:

    375px   bar 308px   one row   8 controls   smallest 34px
    390px   bar 308px   one row   8 controls   smallest 34px
    393px   bar 308px   one row   8 controls   smallest 34px
    430px   bar 308px   one row   8 controls   smallest 34px
    600px   bar 308px   one row   8 controls   smallest 34px
    641px   bar 550px   one row   8 controls   smallest 40px

Flip's `.flip-tools`, before and after, same measurement:

    v214    156px wide, 160-204px tall, 6-7 controls
    v215    156px wide, 130px tall,     5 controls

Both are the merge working. Pad was wrapping at 320 and 360 before.

---

## Changes

### 1. Flip navigation guard — the only bug fix here

`flipBtn` was a bare `<a href="/flip">`. There was no `beforeunload`, no
confirm, and no JavaScript anywhere in the tree touching it: tapping it left
Pad and dropped unposted work silently. Both surfaces now show a confirm.

Deliberately not `beforeunload` — that fires on reload and tab-close too, where
the browser shows its own untranslatable string and cannot say which work is at
risk. It only fires when there is something to lose; a guard that appears on an
empty canvas trains people to dismiss it unread. Focus lands on **Keep
drawing**, so a mis-tap keeps the work.

Flip's back-link guard fails OPEN — if it cannot determine whether there is
work, it guards anyway. A false prompt is cheaper than lost work.

### 2. Colour icon — spectrum ring, current-colour core

The plain disc said *what* colour you were on and nothing said it was tappable.

**The ring is on a `.color-ring` wrapper, never on the element JS writes to.**
`app.js:669` and `flip.js` both set the colour as an *inline* background, and an
inline style beats any rule. Put the gradient on that element and the first
colour change erases it — while initial render still looks right, so a
load-time assertion would never catch it.

* **Pad** needed only a wrapper. `#toolColorChip` already existed; `app.js` is
  unchanged.
* **Flip** needed markup AND a JS change: `#colorCurrent` *is* the button, so a
  `#colorCurrentCore` was added and `flip.js` now writes to it.

`.tool-chip`'s old `box-shadow: 0 0 0 2px rgba(255,255,255,.4)` was removed —
it sat between the core and the spectrum and read as a halo.

### 3. Media icon and drawer

Image, Music and Magnify collapse into one Media control opening a router
drawer: **Add image / Add music / Zoom**. The rows open the existing photo and
music drawers; nothing about their internals changed.

**The dot rule.** `.tab-dot` already meant something: green = media attached,
amber (`.pending`) = the file is remembered but missing and must be re-added,
deliberately the same yellow as the autosave pill. Those were NOT repurposed as
menu state. Merging gives two sources and one dot:

    either item missing  ->  AMBER    (amber beats green: only amber asks
    either item present  ->  GREEN     anything of the user)
    neither              ->  no dot

Because a merged dot cannot say WHICH item needs attention, the drawer rows
carry their own. The toolbar generalises; the drawer localises.

**Zoom is in the drawer because the inline magnify button is a DESKTOP
affordance** — desktop has no pinch. On a phone the gesture replaces the button,
and this row is how Fit and the presets stay reachable. Hiding a control is only
safe when nothing reachable only through it becomes unreachable.

### 4. Draw drawer — Pen / Background switcher

Stroke colour and Background were two identical dot grids stacked on each other
meaning opposite things. One segmented switcher now swaps which grid is shown.
Size, opacity and brush stay put underneath and never move.

Deliberately not a tab: a tab hides half the sheet behind a control people
forget to press. And the two sets stay in ONE view because choosing a pen
colour is relative to what it sits on — you cannot judge contrast across two
drawers. Background swatches stay square so the sets cannot be confused.

The inspector is mode-aware: with Eraser selected, colour, brush and opacity are
*absent*, not greyed. A greyed control still costs a glance and invites a tap.

### 5. Segmented pill parity

`_skribl_draw_drawer.html` carried `{% if kind == 'flip' %}` around
`.seg-slider` five times, so Flip had an animated pill and Pad did not. The
guard is gone. Nothing new was needed: `.smooth-seg` is already
`position: relative`, `.smooth-btn` is already `z-index: 1`, `.seg-slider` is
already in `styles.css` not `flip.css`, and Pad was already a
`SkriblSegSlider` consumer. `lib/segslider.js`'s own header says it exists for
template-written groups exactly like these. **This finished an extraction that
had stopped one step short.**

`track()` is used rather than `place()`: the drawer ships `hidden`, so at init
the buttons have no layout and a one-shot call bails, leaving the pill at
opacity 0 — the bug that module documents. Flip's private
`positionSmoothSeg()` now delegates to the shared module.

### 6. `harness/verify_layout.py` — new suite

Rendered geometry: `getBoundingClientRect`, `scrollWidth` vs `clientWidth`,
`offsetParent`. Not computed styles, not class lists.

**Section 2 is expected to FAIL.** The recording header needs 396px against
355 available at 375px, on the v214 tree, before any redesign. The assertion
reproduces the bug rather than hiding it. Either fix the header in this release
or mark it as reproducing a known-open — but do not delete it.

Its selectors are UNVERIFIED. `#pad` in section 2 and Flip's back-link in
section 4 were inferred from the tree, not confirmed against a running app.

---

## Not done, and deliberately

* **The header redesign.** Logo to watermark, Flip into the overflow menu,
  Post in the header, undo/redo always visible, recording as a swapping state.
  Every header measurement behind it came from a static extract with
  `fitBrand()` not running — and `fitBrand()` is precisely what sizes the
  brand. Those numbers must be re-taken against a running app before anything
  is built on them.
* **The 641px cliff.** Needs size classes, not a pixel breakpoint.
* **Clear all** moving to the overflow menu and joining the undo stack.
* **`SHA256SUMS` regeneration and doc stamping** — see the top of this file.
