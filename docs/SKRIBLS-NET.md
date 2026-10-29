# Mounting Skribl in skribls.net: what the real site needs

Written from a saved copy of a real skribls.net page (a profile, with its own
`style.css`, `app.js`, `composer.js`, `composer-core.js` and
`infinitescroll.js`), served locally with a real Skribl in-post player placed
in a post's media slot, and driven in a browser (v316). Checked again after
v322 against the source of the signed-in Home page and its `threadcompose.js`:
a Pad post and a Flip post, put in by Skribl's own macros and photographed in
every state of the player, dark and light, phone and desk. No server code was
available, so what follows about the server is inferred from the client and
says so.

## What the site is

* **Flask with Flask-WTF.** The page carries `<meta name="csrf-token">` and a
  `csrf_token` hidden input in every form, in the signed format Flask-WTF's
  `generate_csrf()` produces. `composer.js` names `app/utils/embeds.py`.
* **No strict Content-Security-Policy** in the page (inline `onsubmit=`
  handlers are used). If one is added later, Skribl's pages keep their own; see
  INTEGRATION.md, "Your site's security headers".
* **The composer is a server-side form, and on Home it writes threads.**
  `#thread-form` posts to `/compose/thread`: one or more parts, each a
  `seg_body` of up to 1,000 characters (`data-max`) with its own row of tools
  (up to four photos resized in the browser, a video, emoji, a GIF, a poll)
  whose fields are named `seg{i}_…` in the parts' order. Save draft submits the
  same form to `/drafts/thread`. It submits natively, so the Skribl rides in a
  hidden field and the site's view calls `skribl.create_post()` in the same
  commit as its own post row: the shape `examples/host_app/` demonstrates.
* **Posts** are `article.post[data-href]` in `main.feed`; a post's words and
  media sit in `.reveal-wrap`. Photos go in `.post-media`, which is a frame (a
  1px border, 16px corners, `overflow: hidden`); an uploaded video sits beside
  it in `.video-embed.video-upload`, which turns that frame off because the
  video brings its own. A Skribl goes in the way a video does (item 3).
* **Theme** is `data-theme` on `<html>`, and the site defines every token the
  in-post player reads (`--bg-elev`, `--border`, `--radius`, `--accent`,
  `--accent-2`) for dark and light. The player followed the light theme on
  the saved page with nothing added.
* **Media** is served from `media.skribls.net`, a separate origin.

## What was checked, and what it found

| Check | Result |
|---|---|
| Class names shared between the site's CSS and the player's | only `.on`, scoped on both sides: no clash |
| The player in a post, dark and light, desktop and phone | fits the post, follows the theme |
| The player inside `.post-media` (after v322) | **a frame inside a frame**, and the line under the drawing ran into the frame's edges (0px): placed like a video instead, item 3 |
| The line before anybody taps, without `line_info` (after v322) | **a dotted placeholder and only "watching at 1×"** until the drawing arrives: item 3 passes it |
| Tapping the player | **navigated to the post page**: fixed in `inlineplayer.js` (v316), pinned by `verify_inline` |
| Posts added by infinite scroll | **would not play**: the site must call `SkriblInline.mount()`, below |
| Flask-WTF `CSRFProtect` on site-wide | **every post refused**: recipe in INTEGRATION.md, pinned by `verify_integration` |
| The guide's minimal example | **lost every post**: fixed in the guide (v316) |

## What skribls.net has to change

1. **Mount Skribl** with the Flask-WTF recipe in INTEGRATION.md
   (`WTF_CSRF_HEADERS` gains `X-Skribl-CSRF`; Skribl is handed
   `generate_csrf`/`validate_csrf`), and commit per request in
   `after_request` if the site does not already.
2. **In `infinitescroll.js`**, after the new cards are inserted:

       if (window.SkriblInline) window.SkriblInline.mount(sentinel.parentNode);

   beside `skriblObserveVideos()`. Without it a Skribl on page two shows its
   poster and does nothing when tapped.
3. **Render** `{{ skribl_inline_assets() }}` once in the base template's
   `<head>`, and for a post that has a drawing, the player with its size and
   its line, in `.reveal-wrap` where a video would go, NOT inside
   `.post-media`:

       <div class="skribl-embed">
         {{ skribl_inline(post.skribl_id, canvas_w=sk.canvas_w,
                          canvas_h=sk.canvas_h, line_info=sk.line) }}
       </div>

   with one rule in the site's stylesheet, the photo frame's own margin:
   `.skribl-embed { margin: 8px 0; }`. `post` is the site's post and `sk` is
   Skribl's own post for its `skribl_id` (a `SkriblPost`, by `public_id`; the
   listing JSON carries the same three keys). A drawing deleted since leaves
   `sk` empty: the box still renders, without its shape or numbers, and says so
   when tapped.
   * **Why not `.post-media`.** The player draws its own frame from the same
     tokens the photo frame uses (`--border`, `--radius`), so in there the
     drawing had two, and the line under it ran into the frame's edges: the
     loop button touched it, 0px. Beside it, the drawing is framed exactly like
     a photo and its line sits under it on the post, the way the site already
     treats a video.
   * **`line_info`** lets the line say "Drawn in 15 sec" (a Flip: "12 pages")
     and show the drawing's shape before anybody taps. Without it the line is a
     dotted placeholder and "watching at 1×" until the drawing arrives.
     INTEGRATION.md has carried it since v322; this list had not.
4. **Composer**: ONE Skribl button in each part's row of tools, beside GIF,
   that opens the Pad in compose mode (Flip is one ⋯ tap away inside it, v316)
   and fills a hidden field in that part; the overlay is full-screen on a phone
   and floats no close of its own (the editor's header has one). Three things
   in `threadcompose.js` and behind it then have to know about the drawing:
   * `refresh()` renames every part's fields to `seg{i}_…` in the parts'
     order, so the drawing's field joins them as `seg{i}_skribl`, or
     reordering a thread hands the drawing to the wrong part.
   * The same `refresh()` decides whether Post is enabled: a part whose only
     content is a drawing has to count, or a post that is only a drawing keeps
     Post disabled.
   * The view behind `/compose/thread` calls `skribl.create_post()` for each
     part that carries one.

   Leave the part's words alone: the drawing follows them the way a photo does
   (as Skribl's own demo feed has since v321), so there is no `[skribl]`
   marker to keep out of the 1,000 characters.

5. **Author it.** The view that publishes calls
   `skribl.create_post(payload, author_id=<the signed-in user's id>)`, and the
   blueprint is mounted with `current_user_id`. That id is what puts the post
   in the author's `/library` on every device they sign in on; a post created
   without it is anonymous and appears in nobody's Library.
6. **Drafts must carry the drawing.** "Add to post" publishes nothing: the
   drawing lives in the open page until Post, so an abandoned post leaves no
   Skribl, no Library entry and no spent quota behind. The flip side is that a
   tab closed before Post loses it, and the compose editor keeps no draft of
   its own on purpose. Save draft submits the whole form to `/drafts/thread`,
   so a part's `seg{i}_skribl` travels with it; the view behind it has to keep
   that field, and reopening the draft has to hand it back
   (`pad.setPayload(payload, editor)`) before the Skribl button is pressed.
   The composer's own copy in `localStorage` keeps the parts' words only, as
   it does for photos.
7. **Saved drafts come with the mount** (v316). Signed in, the Pad's and
   Flip's ⋯ Save draft keeps a drawing on the author's account, and ⋯ Open a
   draft… inside the composer puts it back on the canvas, ready to Add to post.
   Nothing to build for it beyond item 1 (the `current_user_id` and CSRF it
   already needs) and the migration that creates `skribl_drafts`. This is
   separate from item 6: a saved Skribl draft outlives any one post; the
   composer's draft of a POST still has to carry its own hidden field.

8. **Name the way home.** Mount with `home_url` set to the timeline and
   `home_label="skribls.net"` (INTEGRATION.md, "The way back to your site"):
   once a drawing has posted, the Post sheet then offers "Back to
   skribls.net" beside Make another. Without it the card has no way back
   but closing it (the owner: "if this sits in a social media site, how do
   you get back to the timeline?").

The player needs nothing from `media.skribls.net`: its poster and payload come
from Skribl's own routes under the site's prefix.
