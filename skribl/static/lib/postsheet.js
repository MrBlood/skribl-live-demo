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
    var postIcon = $('postSubmitIcon');
    var backupIcon = $('postBackupIcon');
    var backingUp = false;   // the button is Save as a file (offerBackup)
    var soundMark = $('postSound');
    var soundDot = $('postSoundDot');
    var soundText = $('postSoundText');
    var watchBtn = $('postWatchBtn');
    var shareBtn = $('postShareBtn');
    var copyBtn = $('postCopyBtn');
    var resultRow = $('postResult');
    var keyRow = $('postKeyRow');        // absent in compose mode and when signed in
    var keyBtn = $('postKeyBtn');
    var publicSub = $('postPublicSub');
    var lastKey = null;
    var status = $('postStatus');
    var statusLabel = $('postStatusLabel');
    var progressFill = $('postProgressFill');
    var body = $('postBody');
    var toast = cfg.toast || function () {};
    var lastPostUrl = null, lastPostTitle = '';
    // POSTED!, THE MOMENT (_skribl_post.html): the band, the card, and where
    // to go next. None of it is rendered in compose mode.
    var done = $('postDone');
    var next = $('postNext');
    var jumpImg = $('postJump');
    var cardMedia = $('postCardMedia');
    var cardPic = $('postCardPic');
    var cardTpl = $('postCardTpl'), cardBox = null;   // the player's box, put in on the first post
    var cardTitle = $('postCardTitle');
    var cardCaption = $('postCardCaption');
    var cardMore = $('postCardMore');
    var cardMeta = $('postCardMeta');
    var homeBtn = $('postHomeBtn');
    var homeLabel = $('postHomeLabel');
    var anotherBtn = $('postAnotherBtn');
    var closeBtn = $('postCloseBtn');
    var previewBg = null, previewRatio = 1.6;
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

    /* THE REASON IS ON SCREEN. The status line is the sheet's last row, and on
       a desk window 820px tall it sat 10px under the sheet's bottom edge, not
       drawn: a post that failed showed "Try again" and no reason, unless you
       thought to scroll a sheet that did not look scrollable (measured for the
       v322 plan's decisions, both themes). So whenever the line shows or
       changes, the sheet scrolls just far enough to bring it in, with a little
       air under it. Watched rather than called from each state: both editors
       write the line themselves after setState(), and the Pad's device-only
       save never calls setState() at all. */
    function revealStatus() {
      if (!sheet || status.hidden || overlay.hidden) return;
      // A reason is a card right above Try again (styles.css), so the button
      // under it comes into view too: the press that fixes it, not half of it.
      var last = status;
      if (status.classList.contains('error') && submitBtn.getClientRects().length
          && submitBtn.getBoundingClientRect().bottom > status.getBoundingClientRect().bottom) last = submitBtn;
      var room = Math.min(sheet.getBoundingClientRect().bottom, window.innerHeight) - 12;
      var over = last.getBoundingClientRect().bottom - room;
      if (over > 0) sheet.scrollTop += Math.ceil(over);
      // A layout where something other than the sheet scrolls: the browser's own way.
      if (last.getBoundingClientRect().bottom > window.innerHeight) last.scrollIntoView({ block: 'nearest' });
    }
    if (status && typeof MutationObserver === 'function') {
      var revealFrame = 0;
      new MutationObserver(function () {
        cancelAnimationFrame(revealFrame);
        revealFrame = requestAnimationFrame(revealStatus);   // after the caller's words are laid out
      }).observe(status, { attributes: true, attributeFilter: ['hidden', 'class'],
                           childList: true, characterData: true, subtree: true });
    }

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
        unpost();
        status.hidden = true;
        status.classList.remove('error');
        progressFill.style.width = '0%';
        if (resultRow) resultRow.hidden = true;
        if (watchBtn) watchBtn.hidden = true;
        if (shareBtn) shareBtn.hidden = true;
        if (copyBtn) copyBtn.hidden = true;
        if (keyRow) keyRow.hidden = true;
        lastKey = null;
        body.style.opacity = '';
        titleInput.disabled = false;
        captionInput.disabled = false;
        if (publicInput) publicInput.disabled = false;
        submitBtn.disabled = false;
        submitBtn.hidden = false;
        submitLabel.textContent = IDLE_LABEL;
        showBackup(false);
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
        // The card plays the post in the in-post player: asked for now, so it
        // is here by the time the server answers.
        if (done && !still()) loadPlayer().catch(function () {});
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

    /* TOO LONG TO POST (the Pad plan, step 2; the owner's pick A). The reason
     * in plain words, said before anything is sent, and the button becomes the
     * one thing that helps: Save as a file, the ⋯ menu's own words and icon,
     * which makes a .skribl file. Pressing it puts the sheet away and opens the
     * editor's own backup (cfg.backup), the drawer the menu opens. Every open
     * starts at idle, which puts Post back. An editor with no backup to offer
     * gets the refusal alone. */
    function offerBackup(message) {
      refuse(message);
      if (cfg.backup) showBackup(true);
    }
    function showBackup(on) {
      backingUp = on;
      if (on) submitLabel.textContent = 'Save as a file';
      // SVG elements have no .hidden property; the attribute is what hides them.
      if (postIcon) postIcon.toggleAttribute('hidden', on);
      if (backupIcon) backupIcon.toggleAttribute('hidden', !on);
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
      // The delete key, when the post came back with one (an anonymous post;
      // a signed-in author's account is their key, and the row is not rendered).
      lastKey = (!opts.localOnly && opts.key) || null;
      if (keyRow) keyRow.hidden = !lastKey;
      // A real post: the moment, and the status line, its job done, goes. A
      // save on this device only keeps its warning in the status line, and the
      // form stays, since Try again posts it.
      if (lastPostUrl && !opts.localOnly && lastPostUrl.charAt(0) !== '#') {
        status.hidden = true;
        posted(opts.payload || null);
      }
    }

    /* POSTED!, THE MOMENT (the owner's A from the Post sheet mock). The form
     * folds away and the sheet glides to its new height while the band, the
     * card, what to do with it and where to go next rise in, one after another
     * (styles.css). Blooby jumps once. The card is the post as people will see
     * it: on the drawing's own ground, the drawing drawing itself, in the
     * in-post player, from the payload the editor just sent (`payload`). The
     * Pad's plays once, in about three seconds, and rests on the finished
     * drawing; a Flip plays twice and rests on its first page. Reduce Motion:
     * nothing glides, rises or jumps, and the card is the picture. Decided
     * here, not by a media query: styles.css says why. */
    function posted(payload) {
      if (!done || !sheet) return;
      var title = (lastPostTitle || '').trim() || titleInput.placeholder || 'Untitled Skribl';
      var caption = (captionInput.value || '').trim();
      cardTitle.textContent = title;
      cardCaption.textContent = caption;
      cardCaption.hidden = !caption;
      // Two lines and a "more" (lib/capmore.js), shut again for each post:
      // the card is not shown yet, so toggle() changes it at once.
      if (cardMore && window.SkriblCapMore) {
        window.SkriblCapMore.attach(cardCaption, cardMore);
        if (cardCaption._open) window.SkriblCapMore.toggle(cardCaption);
      }
      cardMeta.textContent = publicInput && publicInput.checked ? 'In the public gallery' : 'Shared by its link only';
      if (cardMedia) {
        cardMedia.style.background = previewBg || '';
        cardMedia.style.setProperty('--shape', previewRatio.toFixed(4));
      }
      if (cardPic) { if (previewImg.src) cardPic.src = previewImg.src; else cardPic.removeAttribute('src'); }
      var home = window.SKRIBL_HOME || null;
      if (homeBtn) {
        homeBtn.hidden = !(home && home.url);
        if (home && home.url) homeLabel.textContent = 'Back to ' + home.label;
      }
      var had = document.activeElement, rise = !still();
      glide(function () {
        sheet.classList.add('is-posted');
        done.hidden = false;
        if (next) next.hidden = false;
        // Fitted before the parts are set low: their 10px would read as
        // the sheet running over.
        fitCard();
        if (rise) sheet.classList.add('is-rising');
      });
      if (rise) {
        // Laid out low and clear, then let go: each part comes up into place.
        void sheet.offsetHeight;
        requestAnimationFrame(function () { sheet.classList.remove('is-rising'); });
      }
      // The press that posted is gone with the form: focus goes to Watch, as
      // the next thing to do, so a keyboard is not left on nothing.
      if (!had || had === document.body || !had.getClientRects().length || had.closest('.post-body, #postSubmitBtn')) {
        if (watchBtn && !watchBtn.hidden) watchBtn.focus({ preventScroll: true });
      }
      jump();
      // The card starts on the drawing's own ground and the drawing draws
      // itself there, after the glide: the player's work on the page would
      // hold the height's frames. Its picture is the card when there is no
      // drawing to play, under Reduce Motion, or while a slow one starts.
      var plays = !!(payload && cardTpl && !still());
      if (cardMedia) cardMedia.classList.toggle('is-waiting', plays);
      if (plays) {
        cardTimer = setTimeout(function () { playCard(payload); }, 400);
        picTimer = setTimeout(showPic, 1500);
      }
    }
    function showPic() { if (cardMedia) cardMedia.classList.remove('is-waiting'); }

    /* THE DRAWING'S ROOM (styles.css .post-card-media): its own shape, up to
     * about half the screen, and no taller than the sheet has room for once
     * everything else in it is laid out, so Watch and the rest stay on the
     * screen; never under ROOM_MIN, where the sheet scrolls instead. Asked
     * with the caption at its two lines: an open caption scrolls the sheet,
     * it does not take the drawing's room. Again when the window changes. */
    var ROOM_MIN = 160;
    function fitCard() {
      if (!cardMedia || !sheet || !sheet.classList.contains('is-posted')) return;
      if (cardMore && window.SkriblCapMore) window.SkriblCapMore.sync(cardCaption);
      cardMedia.style.setProperty('--room', Math.round(innerHeight / 2) + 'px');
      var open = cardCaption._open && cardCaption._shut ? cardCaption.getBoundingClientRect().height - cardCaption._shut : 0;
      var over = sheet.scrollHeight - sheet.clientHeight - Math.max(0, open);
      if (over > 0) {
        var h = cardMedia.getBoundingClientRect().height;
        cardMedia.style.setProperty('--room', Math.max(ROOM_MIN, Math.floor(h - over)) + 'px');
      }
    }
    addEventListener('resize', function () { if (sheet && !sheet.classList.contains('is-gliding')) fitCard(); });

    function unpost() {
      clearTimeout(jumpTimer);
      clearTimeout(cardTimer);
      clearTimeout(picTimer);
      if (cardPlayer) { cardPlayer.settle(); cardPlayer = null; }
      if (cardBox) cardBox.classList.remove('is-on');
      if (!sheet) return;
      sheet.classList.remove('is-posted', 'is-rising', 'is-gliding');
      sheet.style.height = '';
      if (done) done.hidden = true;
      if (next) next.hidden = true;
    }

    function still() {
      try { return window.matchMedia('(prefers-reduced-motion: reduce)').matches; } catch (e) { return false; }
    }

    /* THE GLIDE: from the height the sheet had to the one it has now, in one
     * movement (lib/sheetswipe.js's sheet keeps its own transform). */
    var glideTimer = 0;
    function glide(change) {
      var from = sheet.getBoundingClientRect().height;
      change();
      if (still() || overlay.hidden || !from) return;
      var to = sheet.getBoundingClientRect().height;
      if (Math.abs(to - from) < 1) return;
      sheet.style.height = from + 'px';
      void sheet.offsetHeight;
      sheet.classList.add('is-gliding');
      sheet.style.height = to + 'px';
      clearTimeout(glideTimer);
      glideTimer = setTimeout(function () {
        sheet.classList.remove('is-gliding');
        sheet.style.height = '';
      }, 420);
    }

    /* BLOOBY JUMPS, his hands in the air: the seven poses of one jump
     * (brand/blooby-jump.webp, drawn by harness/tools/blooby.py jump, whose
     * jump_poses() holds these times), then he stays in the last, the cheer
     * badge's. Under Reduce Motion he is simply there, cheering. */
    var JUMP_MS = [200, 80, 100, 240, 80, 130];
    var jumpTimer = 0;
    function pose(k) { if (jumpImg) jumpImg.style.transform = 'translateX(' + (-k * 100 / 7) + '%)'; }
    function jump() {
      clearTimeout(jumpTimer);
      if (still()) { pose(6); return; }
      var k = 0;
      pose(0);
      (function step() {
        jumpTimer = setTimeout(function () { pose(++k); if (k < 6) step(); }, JUMP_MS[k]);
      })();
    }

    /* THE CARD'S PLAYER: the in-post player (inlineplayer.js), which the
     * editors do not load, asked for once a post starts going. holdtiming.js
     * it reads is already on both editors' pages. */
    var playerComing = null;
    function loadPlayer() {
      if (window.SkriblInline) return Promise.resolve();
      if (playerComing) return playerComing;
      function get(el, ready) {
        return new Promise(function (ok, fail) {
          el.onload = function () { if (ready()) ok(); else fail(); };
          el.onerror = fail;
          document.head.appendChild(el);
        });
      }
      var css = document.createElement('link');
      css.rel = 'stylesheet';
      css.href = done.getAttribute('data-player-css');
      var js = document.createElement('script');
      js.src = done.getAttribute('data-player-js');
      playerComing = Promise.all([get(css, function () { return true; }),
                                  get(js, function () { return !!window.SkriblInline; })]);
      playerComing.catch(function () { playerComing = null; });
      return playerComing;
    }

    var cardPlayer = null, cardTimer = 0, picTimer = 0;
    function playCard(payload) {
      loadPlayer().then(function () {
        if (!sheet.classList.contains('is-posted')) return;   // put away meanwhile
        if (!cardBox) {
          cardMedia.appendChild(cardTpl.content.cloneNode(true));
          cardBox = $('postCardPlayer');
        }
        cardBox.classList.add('is-immersive', 'is-bare');
        var p = window.SkriblInline.attach(cardBox, payload, { ambient: true });
        if (!p) { showPic(); return; }
        cardPlayer = p;
        var tries = 0;
        (function start() {
          if (cardPlayer !== p) return;
          var st = p.state();
          if (!st.loaded) { if (++tries < 200) cardTimer = setTimeout(start, 50); else showPic(); return; }
          if (st.kind === 'flip') {
            // Twice round, then its first page: the turn into the second
            // round is watched for on the player's own clock, and that round
            // is its last.
            p.setLoop(true);
            var was = 0;
            (function turn() {
              if (cardPlayer !== p) return;
              var s = p.state();
              if (s.state === 'playing' && s.elapsedMs + 1 < was) { p.setLoop(false); rest(); return; }
              was = s.elapsedMs;
              cardTimer = setTimeout(turn, 30);
            })();
          } else {
            p.setLoop(false);
            p.setRate(Math.max(1, st.totalMs / 3000));
          }
          p.seek(0);
          p.play();
          cardBox.classList.add('is-on');
          clearTimeout(picTimer);
        })();
        function rest() {
          if (cardPlayer !== p) return;
          if (p.state().state === 'playing') { cardTimer = setTimeout(rest, 200); return; }
          p.seek(0);
        }
      }, showPic);
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

    /* THE TITLE STARTS FROM THE DRAWING'S NAME (the owner's yes, Q3). Only a
     * name a person gave: the date name a blank drawing saves under
     * (lib/nametab.js isAuto) is not one. The box follows the name while what
     * is in it is still what this put there, so a rename, or a New Skribl,
     * carries through. Words typed in the box are the person's and stay; so
     * does a box they emptied, until the drawing's name changes. */
    var filled = null, typedUnder = null;
    function fillTitle() {
      var N = window.SkriblName;
      if (!N) return;
      var named = N.get(), v = titleInput.value;
      if (typedUnder === named || (v.trim() && v !== filled)) return;
      var t = N.isAuto(named) ? '' : named;
      titleInput.value = filled = titleInput.maxLength > 0 ? t.slice(0, titleInput.maxLength) : t;
    }
    titleInput.addEventListener('input', function () {
      filled = null;
      typedUnder = window.SkriblName ? window.SkriblName.get() : null;
    });

    function open() {
      setState('idle');
      if (cfg.onOpen) cfg.onOpen();
      syncSoundMark();
      syncPublicSub();
      // Ask before creating server state, not after — see lib/recoverykey.js.
      if (window.SkriblRecoveryKey) window.SkriblRecoveryKey.warnIfVolatile(sheet);
      // Field values persist across a close within the session, a post's too
      // (v293), so nothing clears them here; the title may follow the
      // drawing's name, never over words typed in the box (fillTitle).
      fillTitle();
      updateCharCount();
      // The editor's own picture of what is being posted: the Pad flattens its
      // canvas, Flip its poster page. Shaped like the drawing so it shows whole
      // (no crop), on the drawing's own ground so there are never odd bars.
      var preview = cfg.preview ? cfg.preview() : null;
      previewBg = preview ? preview.bg || null : null;
      previewRatio = (preview && preview.ratio) || 1.6;
      if (jumpImg && !jumpImg.getAttribute('src')) jumpImg.src = jumpImg.getAttribute('data-src');
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
      clearTimeout(jumpTimer);
      clearTimeout(cardTimer);
      clearTimeout(picTimer);
      if (cardPlayer) cardPlayer.pause();
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
      if (backingUp) { close(); cfg.backup(); return; }
      cfg.submit();
    });
    if (shareBtn) shareBtn.addEventListener('click', async function () {
      if (!lastPostUrl || !navigator.share) return;
      var abs = new URL(lastPostUrl, location.href).href;
      var title = lastPostTitle || 'My Skribl';
      try { await navigator.share({ title: title, url: abs }); }
      catch (e) { if (!e || e.name !== 'AbortError') toast('Sharing didn’t work — open it and copy the link', shareBtn); }
    });
    if (keyBtn) keyBtn.addEventListener('click', function () {
      if (!lastKey) return;
      var R = window.SkriblRecoveryKey;
      var done = R && R.copy ? R.copy(lastKey)
        : navigator.clipboard.writeText(lastKey).then(function () { return true; }, function () { return false; });
      done.then(function (ok) {
        toast(ok ? 'Delete key copied. Keep it somewhere safe'
                 : 'Couldn’t copy. The Library has it under Copy key', ok ? null : keyBtn);
      });
    });
    // The gallery tick says what ticking it means, and for an anonymous
    // author that the key matters most once a post is public.
    function syncPublicSub() {
      if (publicInput && publicSub) publicSub.textContent = publicInput.checked ? publicSub.dataset.on : publicSub.dataset.off;
    }
    if (publicInput) publicInput.addEventListener('change', syncPublicSub);

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
      } else if ((window.SKRIBL_PLAYER_TARGET || '_blank') === '_self'
                 || document.documentElement.hasAttribute('data-skribl-app')) {
        // The host routes the player itself; navigate in place as it asked.
        // So does Skribl on the Home Screen (lib/homescreen.js marks it): a
        // new tab there leaves the app for Safari, with no way back to it.
        location.href = lastPostUrl;
      } else {
        // Default. This used to be location.href unconditionally, which inside a
        // host application navigates the HOST'S page away. Configured by
        // create_blueprint(player_target=...), and the posted list's anchors
        // take the same target.
        window.open(lastPostUrl, '_blank', 'noopener');
      }
    });

    if (closeBtn) closeBtn.addEventListener('click', close);
    // Make another: the sheet goes and the editor's New Skribl runs, with its
    // own Undo (lib/newundo.js). The post is safe: it is posted, and in the
    // Library.
    if (anotherBtn) anotherBtn.addEventListener('click', function () {
      close();
      if (cfg.another) cfg.another();
    });
    // Back to the site Skribl lives in, which named its home (SKRIBL_HOME,
    // create_blueprint(home_url=...)). Never a place a query string chose.
    if (homeBtn) homeBtn.addEventListener('click', function () {
      var home = window.SKRIBL_HOME;
      if (home && home.url) location.href = home.url;
    });

    // Recompute the keyboard lift when the viewport changes or a field is focused.
    if (window.visualViewport) {
      window.visualViewport.addEventListener('resize', applyKeyboardInset);
      window.visualViewport.addEventListener('scroll', applyKeyboardInset);
    }
    titleInput.addEventListener('focus', function () { setTimeout(applyKeyboardInset, 100); });
    captionInput.addEventListener('focus', function () { setTimeout(applyKeyboardInset, 100); });

    // Backdrop tap / Escape / handle tap all close — but never mid-send.
    // Judged by the path the press took, not by where its target is by now:
    // a button that rewrites its own words as it is pressed (the card's
    // more and less; lib/labels.js keeps a word in a span) has taken the
    // pressed node out of the page before the press bubbles up to here.
    overlay.addEventListener('click', function (e) {
      if (posting) return;
      var path = e.composedPath();
      for (var i = 0; i < path.length; i++) if (path[i].classList && path[i].classList.contains('menu-sheet')) return;
      close();
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
      offerBackup: offerBackup,
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
       failure('cancelled')         the person cancelled a slow post
       failure('pages', why)        Flip: more pages than a post holds, and how
                                    many to delete (found before sending)
       failure('long', hint)        longer than a post can hold, found before
                                    anything was sent (the owner's pick A for
                                    the Pad plan, step 2); hint: what else the
                                    editor knows would help (Flip's generated
                                    pages), after the backup
     `noun` is what the editor makes: a drawing, unless it says otherwise.
     Flip's say animation (the owner's yes on the plain words: "Your
     animation is still here, saved on this device"). */
  function failure(what, extra, noun) {
    var it = 'Your ' + (noun || 'drawing') + ' is still here', first = 'Couldn\u2019t post. ' + it;
    if (what === 'cancelled') return 'Not posted. ' + it + '; Try again sends it.';
    if (what === 'offline') return first + (extra ? ', saved on this device' : '') + '. Try again when you\u2019re back online.';
    if (what === 'server') return first + (extra ? ', saved on this device' : '') + '. The server had a problem; try again in a moment.';
    if (what === 'odd') return first + '. The connection gave a strange answer (a Wi-Fi sign-in page?); try again.';
    if (what === 'pages') return first + '. ' + extra;
    if (what === 'long') return first + '. It\u2019s longer than a post can hold, so save it as a file to keep a copy.' + (extra ? ' ' + extra : '');
    return first + '. ' + (extra || 'The server turned it down.');
  }

  var api = { attach: attach, failure: failure };
  if (typeof window !== 'undefined') window.SkriblPostSheet = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})();
