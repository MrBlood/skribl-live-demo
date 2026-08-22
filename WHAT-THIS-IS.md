# v215-minimal — sealed v214 plus ONE fix, nothing else

## What changed from the sealed v214

Exactly one thing: **Flip had no navigation guard.** `flipBtn` was a bare
`<a href="/flip">` with no `beforeunload`, no confirm, and no JavaScript
touching it anywhere in the tree. Tapping it left Pad and dropped unposted work
silently. Both surfaces now show a confirm before navigating.

## What did NOT change

**Nothing about the toolbar, the drawer, or any icon.** Specifically absent:

* the colour ring on the swatch
* the merged Media icon and its drawer
* the Pen / Background switcher
* the mode-aware inspector
* the segmented-pill parity change
* the `.draw-inline` wrap fix
* Flip moving into the overflow menu
* `verify_layout.py`

Those all exist in the separate `skribl-v215-build` archive. They are not here.

## Why this build exists

Drawing was reported as laggy after the v215 UI work. Three causes were
eliminated by measurement — the segslider trackers (0.4ms per 600 stroke
segments), forced layout per pointer move (v215 measured *faster* than v214),
and DOM size (identical node count). GPU compositing could not be measured off
the affected device.

Rather than keep guessing, this build removes every UI change so the question
can be answered in one step: **if drawing is smooth here, the lag came from the
UI work. If it is still laggy, the lag is not from any of it.**

## Changed files

    skribl/core.py                              version string
    skribl/static/app.js                        guard appended
    skribl/static/flip.js                       guard appended
    skribl/static/styles.css                    leave-sheet styles appended
    skribl/templates/skribl/skribl_editor.html  leave sheet markup
    skribl/templates/skribl/skribl_flip.html    leave sheet markup
    SHA256SUMS                                  regenerated
    WHAT-THIS-IS.md                             this file

Nothing else is touched. No files removed.

## Not verified

No harness run stands behind this. Verified mechanically only: `node --check`
on both JS files, Jinja parse on all templates, and the manifest.
