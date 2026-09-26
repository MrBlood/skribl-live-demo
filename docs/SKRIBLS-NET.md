# Mounting Skribl in skribls.net: what the real site needs

Written from a saved copy of a real skribls.net page (a profile, with its own
`style.css`, `app.js`, `composer.js`, `composer-core.js` and
`infinitescroll.js`), served locally with a real Skribl in-post player placed
in a post's media slot, and driven in a browser (v316). No server code was
available, so what follows about the server is inferred from the client and
says so.

## What the site is

* **Flask with Flask-WTF.** The page carries `<meta name="csrf-token">` and a
  `csrf_token` hidden input in every form, in the signed format Flask-WTF's
  `generate_csrf()` produces. `composer.js` names `app/utils/embeds.py`.
* **No strict Content-Security-Policy** in the page (inline `onsubmit=`
  handlers are used). If one is added later, Skribl's pages keep their own; see
  INTEGRATION.md, "Your site's security headers".
* **The composer is a server-side form.** Body (300 characters, a video link
  not counted), up to four photos resized in the browser, a video, a GIF, a
  poll, drafts saved over `fetch`. It submits natively, so the Skribl rides in
  a hidden field and the site's view calls `skribl.create_post()` in the same
  commit as its own post row: the shape `examples/host_app/` demonstrates.
* **Posts** are `article.post[data-href]` in `main.feed`; media sits in
  `.post-media > .post-media-item`, which is where `skribl_inline()` goes.
* **Theme** is `data-theme` on `<html>`, and the site defines every token the
  in-post player reads (`--bg-elev`, `--border`, `--radius`, `--accent`,
  `--accent-2`) for dark and light. The player followed the light theme on
  the saved page with nothing added.
* **Media** is served from `media.skribls.net`, a separate origin.

## What was checked, and what it found

| Check | Result |
|---|---|
| Class names shared between the site's CSS and the player's | only `.on`, scoped on both sides: no clash |
| The player inside a post, dark and light, desktop and phone | fits the media slot, follows the theme |
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
   `<head>`, and `{{ skribl_inline(post.skribl_id, canvas_w=..., canvas_h=...) }}`
   inside `.post-media` for a post that has one.
4. **Composer**: a Skribl button beside GIF and video that opens the Pad in
   compose mode and fills a hidden field; the view calls
   `skribl.create_post()`. `hasMedia()` in `composer.js` has to count it, or a
   post that is only a drawing keeps Post disabled. If the site uses the
   `[skribl]` placement marker, `effectiveLen()` should not count it toward
   the 300 characters, as it already skips a video link.

The player needs nothing from `media.skribls.net`: its poster and payload come
from Skribl's own routes under the site's prefix.
