# Real-device checklist

What the suites cannot prove. They run headless Chromium on Linux: no iOS
Safari, no Apple Pencil, no VoiceOver, no silent switch, no Dynamic Type. Every
line below is a thing that has broken on a real phone before, or would, with
the suites green. About twenty-five minutes on an iPhone; do it before a release
the owner will show people, and after anything touching input, audio, zoom or
text size.

Open the live site in **Safari** (not an in-app browser) unless a line says
otherwise. For each line: do it, and it is right if what follows the arrow
happens. Anything else is a bug; `•••` → **Report a problem** copies the
details to send with it.

## First time: the hello

The hello plays once per browser, on the first visit. Add `?hello=again` to
the address to see it again; every reload of that address replays it.

- [ ] Open `https://skribl-live-demo.onrender.com/?hello=again` → the skribl
      mark writes itself in one stroke, the dot drops onto the i (straight
      over it, not off to the right), bounces, winks once, then the ink lifts
      away left to right into the canvas. Sharp edges, not soft; about three
      and a half seconds.
- [ ] Reload it and watch the very first moment → the hello's ground is there
      from the start; the canvas does not flash up first.
- [ ] Reload, and while it plays tap where the `•••` menu sits, top right →
      the hello goes and the menu stays shut.
- [ ] The same address with `/flip?hello=again` → the same hello, then Flip.
- [ ] Settings → Accessibility → Motion → Reduce Motion on, reload → the mark
      shows still, dot at rest, and simply fades. (Turn it off again after.)
- [ ] Open the Pad from the Home Screen icon for the first time → note
      whether the hello plays (the Home Screen app keeps its own storage, so
      it may meet it as a first visit).

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

## Recolor (Pad, then Flip)

- [ ] Draw three lines in three colours, open the draw drawer → the
      eyedropper and Recolor sit side by side at the end of the Pen |
      Background row, and the nine colours below have clear room between
      them (nothing touching at the phone's width).
- [ ] Pick a new colour, tap Recolor → the drawer closes and the bottom bar
      reads "Tap a line to recolor" with the pen's colour, Undo and Done;
      nothing else on the page moves.
- [ ] Tap a line → the new colour runs along it from your finger, both ways
      at once. Drag across the other two → both change. Put two fingers down
      to pinch → nothing is recoloured.
- [ ] Undo in the bar → the last tap or drag goes back. Tap the colour in the
      bar → the drawer opens; pick a colour → it closes and you are still in
      Recolor. Done → back to the pen.
- [ ] Press Play → each recoloured line first draws in its old colour; at the
      moment you recoloured it the new colour runs along it, and the replay
      carries on. The bar under the drawing has a dot of the new colour where
      each change happens (a colour that would not show against the bar has a
      ring round it).
- [ ] Post it and open its link, in light and in dark → the same replay and
      the same dots.
- [ ] In Flip, draw a line on a page, Recolor it, Undo, Recolor again, Done →
      it behaves as on the Pad (Flip has no replay of the change, and no dots).

## Sound

- [ ] Add music, draw, tap Done, play back with the ring/silent switch ON (silent) →
      the drawing plays; note whether sound plays. Then switch silent OFF and
      play → sound plays.
- [ ] Play a post with sound in the feed, then tap a second one → the first
      stops, only the second is heard.

## Posting and drafts

- [ ] Draw something, close the tab, reopen the Pad → "Draft restored" and the
      drawing is back.
- [ ] Turn on Airplane Mode, post → "Couldn't post. Your drawing is still here,
      saved on this device. Try again when you're back online." with a Try again. Airplane Mode off, Try again → it posts and the device copy
      is gone.
- [ ] Two Safari tabs of the Pad: draw in one, then in the other, close both,
      open the Pad again → the newest drawing opens and "Another drawing is
      waiting, from a different tab at …" offers the other. Open it → the page
      reloads into it, says "The drawing you had open is in Drafts" and asks
      nothing more; Keep for later → it shows under Drafts in the Library.
- [ ] Library → Drafts on the phone: a draft's ⋯ → Open in Pad (or Flip),
      Save a .skribl file, and Delete, last, which asks once. Save a .skribl
      file → Files has a .skribl that the Pad's Open a file… opens. A Flip
      draft with in-between pages says to open it in Flip and save it there.
- [ ] In a **Private** tab, draw and post → it works; nothing throws, even
      though storage is refused there.
- [ ] Feed demo: write a line, attach a Skribl, write another line, Post →
      all the words, then the drawing (the drawing goes after the words, as a
      photo does).

## Exporting

- [ ] From the Pad, export a recoloured drawing as a GIF and open the file
      it gives you → a glowing dot rides the line as it draws, sits on the tap in
      the new colour while a colour runs, and is gone from the finished
      drawing.
- [ ] Export the same drawing as a video, once with music added → note
      whether the phone made an MP4 or a WebM, whether it plays on the phone,
      and whether the music is in it. The glowing dot rides it as in the GIF.

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
- [ ] On the Gallery, tap a pale drawing, then a dark one → the controls are
      white glass on the pale one and dark glass on the dark one, with no grey
      band across the drawing and its bottom corners still round. A drawing
      with no sound has no Mute button at all, and nothing moves when it starts.
- [ ] Full screen a pale drawing on the Gallery and on a shared link, then a
      dark one → no grey band and no white fog over the drawing; the buttons
      are white glass over pale ground and dark glass over dark; the time
      reads. On a desk, a tall drawing's title sits in a small glass capsule
      where it crosses the drawing's edge. Pad's and Flip's own full screen
      look the same.
- [ ] Turn the phone sideways on the Pad and on a shared link → nothing is cut
      off, and the drawing is not stretched.
- [ ] Flip with a dozen pages, a loop and a hold of ×2 → every word on the page
      strip reads in SF and nothing sits on anything else, even on page 10 and
      on; the page you are on has one ⋯ in its top corner, and its menu's
      Delete removes the page (Undo brings it back).
- [ ] Add to Home Screen, open it from there → it opens without Safari's bars,
      with the right icon and name.
- [ ] In the Library, play a Flip with Loop off → it ends on its last page,
      whole, not on a blank first page.
- [ ] How it works → Trading card (a Pad example) and A card that waves (a
      Flip one) → the skribl title's dot sits straight over the i, as in the
      header.
