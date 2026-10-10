# Real-device checklist

What the suites cannot prove. They run headless Chromium on Linux: no iOS
Safari, no Apple Pencil, no VoiceOver, no silent switch, no Dynamic Type. Every
line below is a thing that has broken on a real phone before, or would, with
the suites green. About fifteen minutes on an iPhone; do it before a release
the owner will show people, and after anything touching input, audio, zoom or
text size.

Open the live site in **Safari** (not an in-app browser) unless a line says
otherwise. For each line: do it, and it is right if what follows the arrow
happens. Anything else is a bug; `•••` → **Report a problem** copies the
details to send with it.

## Drawing (Pad)

- [ ] Draw a long stroke fast → the line follows the finger with no gaps or
      lag, and the page does not scroll.
- [ ] Two fingers on the canvas, pinch → the drawing zooms, and no stroke is
      left behind from the fingers landing.
- [ ] With an Apple Pencil (iPad): press lightly, then hard → the line gets
      wider. With a finger → the width does not change.
- [ ] Draw (recording starts by itself), tap Done, press Play → the drawing
      replays as drawn, the scrub bar moves, and it stops at the end.
- [ ] While it replays, tap the speed in "watching at 1×" under the drawing →
      a row of speeds opens above it; tap 4× → the row closes and the drawing
      carries on from where it was, four times as fast.
- [ ] Drag the bar under the drawing → a bubble shows the time; keep the finger
      down and slide it up → the same movement moves the drawing more slowly.
      Drag sideways across the drawing itself → it scrubs too; a tap still
      pauses.
- [ ] On a shared link (`/s/<id>`), tap the drawing while it plays → it pauses
      with a play mark in the middle; tap again → it carries on.
- [ ] Tap the zoom % and type a number → the page does NOT zoom in (a text
      field under 16px makes iOS magnify the whole page).

## Sound

- [ ] Add music, draw, tap Done, play back with the ring/silent switch ON (silent) →
      the drawing plays; note whether sound plays. Then switch silent OFF and
      play → sound plays.
- [ ] Play a post with sound in the feed, then tap a second one → the first
      stops, only the second is heard.

## Posting and drafts

- [ ] Draw something, close the tab, reopen the Pad → "Draft restored" and the
      drawing is back.
- [ ] Turn on Airplane Mode, post → "Not posted — saved on this device" with a
      Try again. Airplane Mode off, Try again → it posts and the device copy
      is gone.
- [ ] Two Safari tabs of the Pad: draw in one, then in the other, close both,
      open the Pad again → the newest drawing opens and "Another drawing from
      a different tab is waiting" offers the other. Open it → the page reloads
      into it; Keep for later → it shows under Drafts in the Library.
- [ ] In a **Private** tab, draw and post → it works; nothing throws, even
      though storage is refused there.
- [ ] Feed demo: write a line, attach a Skribl, write another line, Post →
      all the words, then the drawing (the drawing goes after the words, as a
      photo does).

## Reading and hearing it (accessibility)

- [ ] Settings → Accessibility → Display & Text Size → Larger Text, near the
      top → headers, menus and the player controls still fit; no text is cut
      off or overlapping.
- [ ] Turn on VoiceOver. On a shared link (`/s/<id>`), swipe through → every
      control is read with a name (Play, Restart, Loop, Mute, Full screen),
      not "button".
- [ ] VoiceOver in the `•••` menu on the Library → it is announced as a menu or
      dialog, swiping stays inside it, and closing returns you to `•••`.
- [ ] Pinch-zoom the page itself on the Gallery → it zooms (the site must
      never block pinch-zoom).

## Look

- [ ] Settings → Display → Light, then Dark → Pad, Flip, Library and Gallery
      follow it when the menu's Theme is System.
- [ ] Turn the phone sideways on the Pad and on a shared link → nothing is cut
      off, and the drawing is not stretched.
- [ ] Add to Home Screen, open it from there → it opens without Safari's bars,
      with the right icon and name.
