/* The Post sheet — shared by Pad and Flip (skribl/_skribl_post.html).

   THE OWNER, LOOKING AT BOTH: "shouldn't flip and pad look the same? flip is
   not as clean as pad". They were two dialogs. The Pad's was this sheet, which
   v293 had cleaned up -- the drawing as its preview, labelled fields, one Post
   button, a status line that says what happened, and Watch / Share / Copy link
   on one row. Flip's was an older centred card that had drifted on its own: no
   gap between its two fields, its title, link and buttons in the browser's
   Arial, a link field that cut the address off, and a button row that wrapped.

   One markup and this one module now, as the export chooser and the tool shelf
   already are. What stays with each editor is what genuinely differs: the
   payload, the network call and what a post leaves behind (the Pad's
   editor_post.js, Flip's shareSkribl). Both drive the sheet through the handle
   attach() returns.

   Everything below was editor_post.js's, moved rather than copied, comments and
   all, so the Pad behaves exactly as it did. */
(function () {
  'use strict';

  function attach(cfg) {
    var $ = function (id) { return document.getElementById(id); };
    var overlay = $('postOverlay');
    if (!overlay) return null;
    var sheet = $('postSheet');
    var titleInput = $('postTitleInput');
    var captionInput = $('postCaptionInput');
    var charCount = $('postCharCount');
    var previewImg = $('postPreviewImg');
    var previewFrame = $('postPreview');
    var submitBtn = $('postSubmitBtn');
    var publicInput = $('postPublicInput');   // absent in compose mode
    var submitLabel = $('postSubmitLabel');
    var soundMark = $('postSound');
    var soundDot = $('postSoundDot');
    var soundText = $('postSoundText');
    var watchBtn = $('postWatchBtn');
    var shareBtn = $('postShareBtn');
    var copyBtn = $('postCopyBtn');
    var resultRow = $('postResult');
    var status = $('postStatus');
    var statusLabel = $('postStatusLabel');
    var progressFill = $('postProgressFill');
    var body = $('postBody');
    var toast = cfg.toast || function () {};
    var lastPostUrl = null, lastPostTitle = '';
    var closeTimer = null;
    var posting = false;
    /* A POST THAT NEVER ANSWERS (v321 preflight, PF-029). The sheet cannot be
       closed while it posts, so a request that hung left "Posting…" on screen
       with nothing to press for as long as it hung. After SLOW_MS the busy
       button becomes Cancel, in its own place, so nothing moves under the
       finger; the editor aborts its request and keeps its Idempotency-Key, so
       Try again finds a post the server may already have made. Not a timeout:
       24 MB on a slow line can honestly take a minute. */
    var SLOW_MS = cfg.slowMs || 20000;
    var slowTimer = null, slow = false;
    function clearSlow() { clearTimeout(slowTimer); slowTimer = null; slow = false; }

    function updateCharCount() {
      // The limit is whatever the field enforces (rendered from
      // skribl_limits.caption); a literal here drifted to 280 against 300.
      charCount.textContent = captionInput.value.length + ' / ' + captionInput.maxLength;
    }

    // states: 'idle' | 'sending' | 'success' | 'error'
    /* The button's resting label comes from the DOM, not from a literal here.
     * The template renders it ("Post to Skribl", or "Add to post" in compose
     * mode) and setState('idle') used to overwrite it with a hardcoded copy —
     * which was already a duplicate of the template's string and would have
     * silently relabelled the compose button back to publishing the first time
     * anything reset the sheet. Same reason the busy verb is chosen by mode:
     * compose is not posting, and must not say it is. */
    var IDLE_LABEL = (submitLabel.textContent || '').trim() || 'Post to Skribl';
    var BUSY_LABEL = cfg.compose ? 'Adding…' : 'Posting…';

    function setState(state) {
      clearSlow();
      if (state === 'idle') {
        posting = false;
        status.hidden = true;
        status.classList.remove('error');
        progressFill.style.width = '0%';
        if (resultRow) resultRow.hidden = true;
        if (watchBtn) watchBtn.hidden = true;
        if (shareBtn) shareBtn.hidden = true;
        if (copyBtn) copyBtn.hidden = true;
        body.style.opacity = '';
        titleInput.disabled = false;
        captionInput.disabled = false;
        if (publicInput) publicInput.disabled = false;
        submitBtn.disabled = false;
        submitBtn.hidden = false;
        submitLabel.textContent = IDLE_LABEL;
      } else if (state === 'sending') {
        posting = true;
        status.hidden = false;
        status.classList.remove('error');
        statusLabel.textContent = BUSY_LABEL;
        progressFill.style.width = '35%';
        if (cfg.cancel) slowTimer = setTimeout(function () {
          if (!posting) return;
          slow = true;
          statusLabel.textContent = 'Still posting \u2014 a slow connection can take a minute.';
          submitLabel.textContent = 'Cancel';
          submitBtn.disabled = false;
        }, SLOW_MS);
        body.style.opacity = '0.5';
        titleInput.disabled = true;
        captionInput.disabled = true;
        if (publicInput) publicInput.disabled = true;
        submitBtn.disabled = true;
      } else if (state === 'success') {
        posting = false;
        progressFill.style.width = '100%';
        statusLabel.textContent = 'Posted!';
        submitBtn.hidden = true;
        // The form stays on screen at full strength as the record of what was
        // posted; its fields stay disabled (set by 'sending') until the sheet
        // is opened again. It used to sit at the sending state's half opacity
        // with the title wiped (v293, from a phone).
        body.style.opacity = '';
      } else if (state === 'error') {
        posting = false;
        status.classList.add('error');
        statusLabel.textContent = 'Couldn’t post — try again';
        progressFill.style.width = '100%';
        body.style.opacity = '';
        titleInput.disabled = false;
        captionInput.disabled = false;
        if (publicInput) publicInput.disabled = false;
        submitBtn.disabled = false;
        submitBtn.hidden = false;
        submitLabel.textContent = 'Try again';
      }
    }

    /* A REFUSAL BEFORE ANYTHING IS SENT, said where the post would have gone.
     * Flip's page and point budgets answer before the network does, and the
     * remedy is to change the drawing, not to press again -- so the status
     * line carries the sentence and the button keeps its own word. */
    function refuse(message) {
      status.hidden = false;
      status.classList.add('error');
      statusLabel.textContent = message;
      progressFill.style.width = '100%';
    }

    /* The row under the posted form: Watch, and for a real link Copy link,
     * and Share where the device has a share sheet. */
    function result(url, title, opts) {
      opts = opts || {};
      lastPostUrl = url || null;
      lastPostTitle = title || '';
      if (resultRow && lastPostUrl) resultRow.hidden = false;
      if (watchBtn && lastPostUrl) watchBtn.hidden = false;
      // Copy link, for a real link only: a local fallback (#skribl=…) opens
      // nowhere but here, so there is nothing to hand anyone.
      if (copyBtn && lastPostUrl && !opts.localOnly && lastPostUrl.charAt(0) !== '#') copyBtn.hidden = false;
      // Share, where the device has a share sheet (v292, SK-AUD-016); a local
      // fallback (#skribl=…) is not a link anyone else can open, so not then.
      if (shareBtn && lastPostUrl && !opts.localOnly && lastPostUrl.charAt(0) !== '#' && navigator.share) shareBtn.hidden = false;
    }

    /* THE SOUND MARKER MIRRORS THE TOOLBAR, IT DOES NOT RE-DECIDE.
     *
     * #musicTabDot is already the app's statement about the music track: hidden
     * when there is none, green when a loop is loaded, amber (.pending) when one
     * is REMEMBERED and its file is gone — the case where the author is about to
     * post silence believing otherwise, and the reason this marker exists at all.
     *
     * Reading that dot rather than inspecting the payload is deliberate. A second
     * opinion computed here could disagree with the toolbar, and then the same
     * mark would say two things on one screen. It is also the cheap answer:
     * serializing the drawing on every sheet open, to learn one boolean, would
     * copy the audio bytes for nothing.
     *
     * What it therefore does NOT claim: that the post-time mono bake succeeded.
     * The bake runs later, inside the editor's payload builder. This says what
     * the editor is holding, which is the question the author can still do
     * something about.
     */
    function syncSoundMark() {
      if (!soundMark) return;
      var dot = $('musicTabDot');
      var has = !!(dot && !dot.hidden);
      soundMark.hidden = !has;
      if (!has) return;
      var pending = dot.classList.contains('pending');
      if (soundDot) soundDot.classList.toggle('pending', pending);
      var msg = pending
        ? 'Your music file is missing — this will post without sound.'
        : 'This Skribl has sound.';
      soundMark.setAttribute('title', msg);
      if (soundText) soundText.textContent = msg;
    }

    function open() {
      setState('idle');
      if (cfg.onOpen) cfg.onOpen();
      syncSoundMark();
      // Ask before creating server state, not after — see lib/recoverykey.js.
      if (window.SkriblRecoveryKey) window.SkriblRecoveryKey.warnIfVolatile(sheet);
      // Field values persist across an accidental close within the session; they
      // reset only after a successful post. So don't clear them here.
      updateCharCount();
      // The editor's own picture of what is being posted: the Pad flattens its
      // canvas, Flip its poster page. Shaped like the drawing so it shows whole
      // (no crop), on the drawing's own ground so there are never odd bars.
      var preview = cfg.preview ? cfg.preview() : null;
      if (preview && preview.src) {
        previewImg.src = preview.src;
        if (previewFrame) {
          previewFrame.style.aspectRatio = (preview.ratio || 1.6).toFixed(4);
          previewFrame.style.background = preview.bg || '#0d0f14';
          previewFrame.style.display = '';
        }
      } else if (previewFrame) {
        previewFrame.style.display = 'none';
      }
      clearTimeout(closeTimer);
      overlay.hidden = false;
      requestAnimationFrame(function () {
        overlay.classList.add('open');
        applyKeyboardInset();
        if (window.SkriblModal) window.SkriblModal.open(sheet || overlay, cfg.opener || null);
      });
    }

    function close() {
      // WAS a conditional blur() on the two text fields, which exists to dismiss
      // the soft keyboard on a phone. Returning focus to the opener does that
      // too — focus leaves the input either way — and it also puts the user back
      // where they were instead of on <body>.
      if (window.SkriblModal) window.SkriblModal.close(sheet || overlay);
      overlay.classList.remove('open');
      if (sheet) sheet.style.maxHeight = '';
      overlay.style.top = ''; overlay.style.bottom = ''; overlay.style.height = '';
      closeTimer = setTimeout(function () { overlay.hidden = true; }, 350);
    }

    // iOS doesn't shrink CSS viewport units for the on-screen keyboard, so the
    // bottom-anchored sheet ends up behind it. Fix: resize the fixed overlay to
    // the *visible* region (above the keyboard) using visualViewport. The sheet,
    // anchored to the overlay's bottom, then sits right on the keyboard — and iOS
    // has no reason to scroll the page and push the header off the top.
    // Mobile only; desktop / unsupported clears any inline styles.
    function applyKeyboardInset() {
      var vv = window.visualViewport;
      if (overlay.hidden || window.innerWidth > 640 || !vv) {
        overlay.style.top = '';
        overlay.style.bottom = '';
        overlay.style.height = '';
        if (sheet) sheet.style.maxHeight = '';
        return;
      }
      overlay.style.top = vv.offsetTop + 'px';
      overlay.style.bottom = 'auto';
      overlay.style.height = vv.height + 'px';
      if (sheet) sheet.style.maxHeight = Math.max(200, vv.height - 12) + 'px';
    }

    captionInput.addEventListener('input', updateCharCount);
    if (cfg.submit) submitBtn.addEventListener('click', function () {
      if (posting) { if (slow && cfg.cancel) { submitBtn.disabled = true; cfg.cancel(); } return; }
      cfg.submit();
    });
    if (shareBtn) shareBtn.addEventListener('click', async function () {
      if (!lastPostUrl || !navigator.share) return;
      var abs = new URL(lastPostUrl, location.href).href;
      var title = lastPostTitle || 'My Skribl';
      try { await navigator.share({ title: title, url: abs }); }
      catch (e) { if (!e || e.name !== 'AbortError') toast('Sharing didn’t work — open it and copy the link', shareBtn); }
    });
    if (copyBtn) copyBtn.addEventListener('click', async function () {
      if (!lastPostUrl) return;
      var abs = new URL(lastPostUrl, location.href).href;
      try { await navigator.clipboard.writeText(abs); toast('Link copied', null); }
      catch (e) { toast('Couldn’t copy — open it and copy the address', copyBtn); }
    });
    if (watchBtn) watchBtn.addEventListener('click', function () {
      if (!lastPostUrl) return;
      if (lastPostUrl.charAt(0) === '#') {
        // Local fallback: #skribl=<id> — boot the in-page player via the hash.
        // Always in place: there is no server URL to open in a tab.
        location.hash = lastPostUrl;
        location.reload();
      } else if ((window.SKRIBL_PLAYER_TARGET || '_blank') === '_self') {
        // The host routes the player itself; navigate in place as it asked.
        location.href = lastPostUrl;
      } else {
        // Default. This used to be location.href unconditionally, which inside a
        // host application navigates the HOST'S page away. Configured by
        // create_blueprint(player_target=...), and the posted list's anchors
        // take the same target.
        window.open(lastPostUrl, '_blank', 'noopener');
      }
    });

    // Recompute the keyboard lift when the viewport changes or a field is focused.
    if (window.visualViewport) {
      window.visualViewport.addEventListener('resize', applyKeyboardInset);
      window.visualViewport.addEventListener('scroll', applyKeyboardInset);
    }
    titleInput.addEventListener('focus', function () { setTimeout(applyKeyboardInset, 100); });
    captionInput.addEventListener('focus', function () { setTimeout(applyKeyboardInset, 100); });

    // Backdrop tap / Escape / handle tap all close — but never mid-send.
    overlay.addEventListener('click', function (e) {
      if (posting) return;
      if (!e.target.closest('.menu-sheet')) close();
    });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && !overlay.hidden && !posting) close();
    });
    // Tap the grabber or swipe the sheet down (lib/sheetswipe.js), not mid-send.
    if (sheet && window.SkriblSheetSwipe) {
      window.SkriblSheetSwipe.attach(sheet, { handle: sheet.querySelector('.menu-handle'),
        close: close, canClose: function () { return !posting; } });
    }

    return {
      open: open,
      close: close,
      setState: setState,
      refuse: refuse,
      result: result,
      isOpen: function () { return !overlay.hidden; },
      isPosting: function () { return posting; },
      // The editor reads the words from the fields it posts, and touches the
      // status line for outcomes only it knows about (the Pad's device-only save).
      el: { overlay: overlay, sheet: sheet, titleInput: titleInput, captionInput: captionInput,
            publicInput: publicInput, submitBtn: submitBtn, submitLabel: submitLabel,
            status: status, statusLabel: statusLabel }
    };
  }

  /* WHEN A POST FAILS, ONE SET OF WORDS FOR BOTH EDITORS (owner's pick;
     SK-AUD-010). Always the same first line, so nobody wonders whether their
     drawing is gone; then what happened; then what to do. Each editor says
     only WHAT happened -- the recoveries that differ (the Pad keeps a copy on
     the device when the server cannot be reached) differ in that last clause,
     not in the first line.
       failure('server')            5xx: the server had a problem
       failure('refused', reason)   4xx: the server's own reason, when it gave one
       failure('odd')               a 2xx that is not a post (a Wi-Fi sign-in page)
       failure('offline', kept)     no answer; kept: a copy was saved on this device
       failure('cancelled')         the person cancelled a slow post */
  var FIRST = 'Couldn\u2019t post. Your drawing is still here';
  function failure(what, extra) {
    if (what === 'cancelled') return 'Not posted. Your drawing is still here; Try again sends it.';
    if (what === 'offline') return FIRST + (extra ? ', saved on this device' : '') + '. Try again when you\u2019re back online.';
    if (what === 'server') return FIRST + (extra ? ', saved on this device' : '') + '. The server had a problem; try again in a moment.';
    if (what === 'odd') return FIRST + '. The connection gave a strange answer (a Wi-Fi sign-in page?); try again.';
    return FIRST + '. ' + (extra || 'The server turned it down.');
  }

  var api = { attach: attach, failure: failure };
  if (typeof window !== 'undefined') window.SkriblPostSheet = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})();
