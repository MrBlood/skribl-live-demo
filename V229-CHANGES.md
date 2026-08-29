# v229 — two autosave bugs, reported from the live phone

Both were found by the owner on a phone, minutes after v228 went live, and
neither was reachable on a desktop. They are independent defects that happened
to compound into one symptom: **the only autosave state a phone user could ever
see was a warning.**

## 1. Pad never said "Saved" on a phone — and Flip's warning looked stuck

`lib/pillfit.js` exists because the autosave pill is `position:fixed` at
bottom-left and the tool row is also at the bottom, so on a phone they overlap.
Its own header says so: *"measured on both surfaces at every phone size."* Its
remedy was to **fade the pill out**.

That remedy is correct on a desktop, where it fires almost never. On a phone the
collision is **permanent**, so the remedy ran every single time, and the
reassuring "Saved" was never visible at all. The report was exactly that: *"on
pad I'm not seeing saved at all on autosave."*

Then it interacted. Warnings are deliberately exempt from fading — a warning
that fades claims it was resolved. So on a phone the amber "Saved without media"
was the **only** pill state that could appear, and the green "Saved" that should
have replaced it was being hidden by this same library. A permanently stuck
warning was the designed behaviour of the two rules combined, and neither rule
was wrong on its own.

**The pill now lifts above the bars instead of vanishing**, and only falls back
to fading when there is no room above. Measured: Pad lifts 62px, Flip 209px
(strip + tools + the Duplicate/Blank/In-between row, which joined the target
list when clearing one bar landed the pill on the next).

The invariant this suite protects was never "it fades" — it is "it does not
cover a control." Lifting satisfies that and still tells the user their work is
safe.

## 2. Flip's amber announced a failure that had not happened

Flip writes the drawing to localStorage and spills media bytes to IndexedDB.
It painted `saved-no-media` — an amber warning that by design **never fades** —
synchronously, before the spill settled, on the path its own comments call *the
normal way media gets saved*. Instrumented:

```
put:start bytes=4215866
pill:saved-no-media        (+1ms)
put:RESOLVED / pill:saved  (+13ms)
```

13ms of amber is invisible on a desktop. That is why it shipped, and why the
existing pill assertion — Pad only, resting state only — could not see it. On a
phone writing megabytes it is visible, and if the write is slow or fails it
never clears.

While the write is in flight the pill now says **"Saving…"**, which is true,
already stays up without fading, and resolves to `saved` or to a
`saved-no-media` that is **earned**. A real failure still raises the amber and
still keeps it on screen — asserted, because "never show amber" is otherwise
satisfiable by deleting the warning.

## 3. A requestAnimationFrame loop that never stopped (found while fixing 1)

`sync()` writes the pill's `class`; the library observes the pill's `class`.
`classList.remove()` sets the attribute even when the token was absent, and
setting an attribute fires a MutationObserver record even when the value is
unchanged — so every unconditional write fed the observer, which scheduled
another frame, forever, on an idle page with the pill hidden.

Measured on a phone viewport, three seconds after everything settled:
**133** attribute writes before the guard existed, **364** once lifting added
two more writes per pass, **0** after. This predates v229; the lifting work
doubled it and is how it was noticed. Writes are now guarded to only fire when
the value actually changes.

## Testing

`verify_pillfit` 18 → 20, `verify_drafts` 17 → 24. Three mutations, each
confirmed to fail the right assertion: restore the premature amber (the sequence
check catches `['saving','saved-no-media','saved']`), restore fade-instead-of-lift
(four checks fail across both surfaces), unguard the writes (360 idle mutations).

The new Flip section records the **whole pill sequence** rather than the resting
state, because a resting-state check passes on the broken and the fixed build
alike — which is precisely why this shipped in v228.
