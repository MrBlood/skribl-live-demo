# v206 — owner review of v205 (drawer bug, toast redesign, menus, .skribl)

Owner-driven fixes after using v205 on desktop and iPhone.

## The Flip image/music drawer "does not open" — root cause found

It opened fine, then closed itself the instant a file was picked. Flip's file
inputs (#imageInput/#musicInput/#draftInput) live at the PAGE ROOT, outside the
drawer panels — the shared drawer partial deliberately omits them for Flip and
the Flip template supplies its own. Flip's "click outside the drawer closes it"
handler then read the browser's post-dialog click on that input as "outside"
and hid the drawer. Pad never hit this: its inputs sit INSIDE the drawer
partial. Fix: the click-outside handler ignores file inputs. Verified with the
exact click the browser dispatches (headless cannot open the OS dialog, which
is why it was unreproducible for several rounds), and the pin was proven to
FAIL against the old handler before being trusted.

## Toast redesigned (owner's design)

The v205 "panel" toast — large, non-dismissing, pointer-events:none so strokes
pass through — hid the mouse pointer behind it and, at z-index 380 across the
top of the page, was a dead-zone risk. Retired. The intro is now a normal small
timed tap-to-dismiss toast carrying a "How it works ->" action that opens the
full help drawer. One essential line, with the rest a tap away.

## Menus aligned; Clear all in both

Side-by-side audit: Pad said "Save draft / Load draft / Export", Flip said
"Save draft (.skribl) / Load draft (.skribl) / Export…". Pad aligned to Flip
(the .skribl hint is useful; … signals a dialog). "How it works" vs "How Flip
works" kept — the content differs per editor. Flip's "Clear all pages" lived
only in the draw drawer; it is now also in the ... menu with the Pad's
two-tap arm (tap -> "Tap again", 3s auto-disarm, disarms on menu close),
delegating to the existing clear so it keeps the undo backup.

## .skribl drafts

- iPhone: Safari maps `accept` to file-type identifiers and an unregistered
  extension (.skribl) resolves to nothing, so the picker hid the files.
  `accept` broadened with the types iOS tags an unknown JSON file
  (text/plain, application/octet-stream); the loader validates content and
  rejects junk, so this is safe.
- Cross-loading was silently broken and is now guarded: a Flip .skribl into
  Pad said "Draft loaded" and showed an EMPTY drawing (data loss dressed as
  success); a Pad .skribl into Flip loaded as a lone 1-page animation with no
  error. Neither checked playbackMode. Both now refuse the wrong format with
  directions. Guard is on the draft-file path only — the shared player still
  opens Flip posts.

## Also

Grid toggle now lights (it toggled `.on`; its .onion-tint siblings light on
`.active` — v204 leftover). Music drawer option A: nudge +/- 26->32 (30 phone),
pending-dismiss 32, waveform handles 16->28, all with 44pt tap areas; the
3-column nudge grid verified to fit 375px with real music loaded, and a click
5px outside a nudge changes the readout. Remaining pill sliders (Smoothing,
Tips, Canvas) unified with the tune-drawer feel (roomier, centered; not fixed
width since they carry text).

## Gates

ux 194 (new pins: drawer survives file-input click both drawers; toast is the
action variant and opens help; menu labels aligned; Clear all in both menus;
iOS-friendly accept; cross-load refused both ways; grid/motion/tint light;
nudge grid fits + tap area fires), visual 76, parity 115, cssplit 16, tips 43,
pages 44, move 79, exopts 26.

## ⚑ Owner decision: player-JS ratchet raised 142,220 → 142,344 (+119 B)

The cross-load guard in Pad's draft-input handler ("That's a Flip Skribl —
open it in Flip Mode") is 119 functional bytes in app.js, which the player
also loads. It could not be moved to editor-only JS because the player
template carries #draftInput too. Golfed to its irreducible condition +
message. Same category as the two prior approved raises (A1 audio, grid
hook): small, functional, user-protecting. **Approve or direct a cut.**
