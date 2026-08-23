# Skribl — the design direction

Written at the v219 seal, from the owner's brief and an external design critique.
This is not a punch-list. It is the shape the product should take, and the next
session should treat it as the frame rather than as a list of tickets.

---

## What Skribl is

> A tiny underground sketch machine.
> Open it. Make something. Make it move. Send it.

Not a web drawing application. Not a mini Photoshop. Not Notes with more buttons.

**The art should look messy. The interface should be immaculate.** That tension is
the product. Beautifully crude marks, made in an environment with almost no
visible chrome.

The reference points are Apple-level *restraint* with a personality that is
deliberately not Apple's: zine culture, early Macintosh playfulness, a
well-engineered tool somebody cool made at 2 a.m. Controlled imperfection. The
interaction philosophy is Apple-like; the visual identity should not be, or it
goes sterile.

---

## The question that changes everything

The v219 work — this whole session — was a competent answer to:

> *How do we fit all of our features?*

Eight controls measured into 360px. 34px against 36px. Flip moved to an overflow
menu to buy back 40px. All careful, all real, and all inside a frame nobody
questioned.

**The right question is: how much interface can we delete before Skribl stops
working? Then delete one more thing.**

Skribl can carry that further than most tools, because the user's creation can
literally occupy the entire interface.

---

## Three things in this tree that prove the point

These are measured against the v219 source, not asserted:

**1. Flip already has onion skinning, and it is invisible.** `onion = true` by
default, with depth and tint controls, composited on its own offscreen layer so
overlapping frames do not stack into blobs. Someone built it properly. It lives
in the tune panel behind a slider icon, and an external reviewer reading the
source did not find it. The design critique ranked elegant onion skinning above
almost every cosmetic feature — **it is already there.** The failure is not
capability. It is that the interface hides its best idea.

**2. The accent colour is used 88 times** (57 in `styles.css`, 31 in `flip.css`).
The direction wants ONE brand colour, spent almost nowhere, so that POST reads as
electricity. Today the accent is the tool pill, the record dot, focus rings,
active segments, slider fills, the Flip page border. It is ambient. **Nothing can
be loud when everything is.**

**3. Pad shows 11 controls at rest.** The proposed Pad shows five.

---

## The target shapes

**Pad** — the canvas owns the screen.

    SKRIBL                                    •••

              (the drawing, edge to edge)

    ↶    ✎    ●    ＋                        POST

Tap the pencil: you are drawing. Tap it again: a small floating strip — thin ▸
thick, opacity, eraser — which then disappears. Long-press the colour dot for the
palette. Tap `+` for a sheet: PHOTO · TEXT · SHAPE · MUSIC.

**One conceptual decision removes a shocking amount of interface:** things you can
*add* belong together, behind `+`. There is no permanent Photo button, Music
button, Shape button, settings button.

**Flip** — not Pad with animation bolted on. **A stack of drawings.**

    FLIP 04/12

              (the current frame)

    ‹      ● ● ● ● ○ ○      ›

    ↶    ✎    ＋                              ▶

The strip at the bottom IS the film. Swipe between frames. Tap a thumb to jump.
Hold and drag to reorder. Swipe a frame up to delete. `+` duplicates or adds.
Hold ▶ to preview, tap ▶ to play.

**No "Move left". No "Move right". No page-management cluster.** The object itself
is manipulable — that is the Apple-ish part, not rounded corners. Direct
manipulation.

The strip should read as a contact sheet or film strip, not a web carousel. The
active frame lifts 2px. Dragging separates its neighbours. A duplicate slides in
beside its source; a deletion closes the gap. **The UI communicates what Flip is.**

---

## Craft notes

**Undo should feel physical.** A stroke retracts. A sticker drops. A deleted page
slides back. 120–180ms, subtle, never theatrical. Undo is one of the few
permanent controls in a creative tool and it should feel tactile, not like DOM
state changed.

**The colour picker is a signature opportunity.** Six slightly imperfect inked
circles blooming outward; the selected one expands; hold for the exact picker. A
child understands it instantly and an illustrator can still hit a hex value. That
is progressive disclosure with personality.

**POST is the only loud thing.** One accent, never spent casually. The canvas is
the colour; the interface is ink; POST is electricity.

**Typography stabilises the chaos.** A very good neutral grotesk for UI —
confident, not quirky. Reserve any hand-made treatment for tiny moments: the
wordmark, frame numbers, empty states, export branding. A handwriting font
everywhere is the obvious move and it will cheapen the product.

**Resist the pill.** Too many rounded rectangles reads as SaaS dashboard. Soft
canvas corners, circular tool controls, a few floating sheets, and icons mostly
sitting naked in space. Almost no button-shaped buttons.

**Voice, sparingly.** Empty Flip: *draw something.* Empty Pad: nothing at all.
404: *lost this one.* Offline: *still here.* A loading indicator that is a
scribble completing itself. Export progress as a sketch filling in.

**Desktop is not phone-but-wider.** Tools · huge canvas · frames. Both side areas
collapse. Tab hides everything but the artwork; Tab again brings the studio back.

**Mobile is brutally simple.** 44–48px hit areas with 18–20px glyphs — small
*looking*, comfortable *feeling*. (v219 already separated hit region from glyph
size; see the note in `styles.css`. The height is done; the width needs one fewer
control in the row, which this direction delivers by itself.)

**Onboarding is the first stroke.** No dashboard, no welcome, no tour, no modal
explaining Flip. Open it: blank page, pencil selected, draw. POST appears once
there is something to post. Play appears once there is a second frame. The UI
reveals itself because you earned the next action.

---

## Two things that must come FIRST, and why

The calm this direction wants is not achievable as a skin. Two structural items
are prerequisites, and both are already known-open:

**1. Pointer identity.** `getPos` uses `e.touches[0]` and assumes the first touch
is the drawing finger. A second finger — a pinch beginning mid-stroke — can
redirect the mark. Migrate to Pointer Events with `pointerId` capture: a stroke
owns exactly one pointer from `pointerdown` to `pointerup`/`cancel`, and gestures
are a separate state machine.

**"My mark goes where my finger went" is the first promise a drawing app makes.**
No amount of restraint elsewhere compensates for breaking it.

**2. Durable drafts.** Pad's autosave stores strokes but not media bytes, because
localStorage cannot hold them; Flip drops media when the quota is exceeded. Move
drafts to IndexedDB or OPFS with blobs stored separately, and make the save atomic
at the document level.

The direction says *"Autosaved: maybe don't even tell me. Just save it."* That is
right, and it is only right AFTER this. Today the amber "Saved without media" pill
is not decoration — it is a true warning. Hiding it before persistence is fixed
would convert honest ugliness into quiet data loss. **Solve the persistence, then
delete the status, then delete the navigation guard that exists only because
persistence is partial.**

---

## One caution, from this project's own history

Progressive reveal — POST appearing after the first stroke — is lovely, and this
codebase has been burned by an adjacent instinct. Flip Mode shipped as a bare 40px
icon and went unrecognised for several versions; the fix was a menu row with a
subtitle saying what it is. Revealing on *earned action* is a different mechanism
from hiding behind an icon, and probably fine. **But test it rather than assume
it.** This project's most expensive mistakes have all been confident assumptions
about what a user would recognise.

---

## What is NOT threatened

The engine is good and none of this touches it: the stroke compositor, the replay
timeline, the export paths, the media validation, the rate limiter, the harness.
The v219 work that survives is the correctness work — the lag fix, the beading
fix, the tool-pill maths, the hit regions, the guard logic.

**It is the chrome that goes.** Underneath a stupidly simple surface can sit all
the sophisticated engineering already built. That is the point.

---

## The order I would take it

1. **Pointer identity** — the only outstanding correctness defect.
2. **Durable drafts** — makes the calm possible and deletes two apologies.
3. **Delete the interface** — Pad to five controls, `+` sheet, colour bloom.
4. **Flip as a stack of drawings** — direct-manipulation strip, onion skinning
   promoted out of the tune panel to where it can be seen.
5. **One accent** — audit all 88 uses; keep POST, demote the rest.
6. **Craft pass** — tactile undo, voice, typography, corners.

Items 3–6 are where the product becomes itself. Items 1–2 are what make it
honest enough to deserve them.
