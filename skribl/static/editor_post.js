// Editor-only: the post composer
//
// Lifted VERBATIM out of app.js, which served the editor AND the public player:
// every visitor opening a shared link downloaded this code to run none of it.
// The code is unchanged — only its file moved — so the editor keeps one
// implementation and there is no second copy to drift.
//
// LOAD ORDER MATTERS. This is a classic script, not a module, and it reads
// globals that app.js declares (strokes, showToast, buildPreviewDataURL...). It must stay
// AFTER app.js in the template, and it is deliberately absent from
// skribl_player.html.
// ==================== POST COMPOSER ====================
// The client-side half of posting: a sheet to title/caption the Skribl, a
// preview, and a sending → success/error state machine. serializeSkribl()
// already produces the self-contained payload; sendSkribl() is the ONE seam
// where a real network call drops in later — nothing else here changes.
(function initPostComposer() {
  const overlay = document.getElementById('postOverlay');
  const sheet = document.getElementById('postSheet');
  const titleInput = document.getElementById('postTitleInput');
  const captionInput = document.getElementById('postCaptionInput');
  const charCount = document.getElementById('postCharCount');
  const previewImg = document.getElementById('postPreviewImg');
  const previewFrame = document.getElementById('postPreview');
  const submitBtn = document.getElementById('postSubmitBtn');
  const submitLabel = document.getElementById('postSubmitLabel');
  const soundMark = document.getElementById('postSound');
  const soundDot = document.getElementById('postSoundDot');
  const soundText = document.getElementById('postSoundText');
  const watchBtn = document.getElementById('postWatchBtn');
  let lastPostUrl = null;
  const status = document.getElementById('postStatus');
  const statusLabel = document.getElementById('postStatusLabel');
  const progressFill = document.getElementById('postProgressFill');
  const body = document.getElementById('postBody');
  let closeTimer = null;
  let posting = false;

  // ---- THE NETWORK SEAM ----
  // The ONE place a post leaves the app. When Flask serves the page the editor
  // template sets window.SKRIBL_API_BASE ("/api/skribls"); we POST the authored
  // serializeSkribl() payload there and return the server's { id, url } — url is
  // a real /s/<id> path. If there's no API base, or the request fails for any
  // reason, we fall back to the localStorage stub so a post never hard-fails in
  // front of the user (a Render free-tier cold start can 502 on first hit; a
  // transient failure shouldn't lose the user's work). Fallback url is a
  // #skribl=<id> hash the in-page player opens on this device only.
  async function sendSkribl(payload) {
    const apiBase = (typeof window !== 'undefined' && window.SKRIBL_API_BASE) || null;

    if (apiBase) {
      // Serialize once so the size-check and the request send the exact same bytes.
      const body = JSON.stringify(payload);

      // IDEMPOTENCY. One key per POSTING ATTEMPT of one piece of work, held
      // until the server confirms success. If the response is lost in transit
      // (timeout, dropped connection, a proxy 502 issued after the commit),
      // the user's retry carries the SAME key and the server resolves it to
      // the SAME post instead of creating a duplicate and spending a second
      // rate-limit slot. Cleared only on a confirmed success, so a fresh post
      // after that gets a fresh key; the retry-after-failure path reuses it,
      // which is the entire point.
      // Key-per-BODY (v201 review, F4): the server now 409s a reused key
      // with a different body, so an edit between an ambiguous failure and
      // the retry mints a fresh key. An unchanged body keeps its key — that
      // is the retry the whole mechanism exists for.
      if (sendSkribl._idemBody !== body) {
        sendSkribl._idemKey = null;
        sendSkribl._idemBody = body;
      }
      if (!sendSkribl._idemKey) {
        sendSkribl._idemKey = (typeof crypto !== 'undefined' && crypto.randomUUID)
          ? crypto.randomUUID()
          : 'k' + Date.now().toString(36) + Math.random().toString(36).slice(2, 12);
      }
      const baseHeaders = skriblPostHeaders();
      baseHeaders['Idempotency-Key'] = sendSkribl._idemKey;

      // Client-side size guard: the server caps the request body at
      // MAX_CONTENT_LENGTH (25 MB via a Render env var) and raises a 413 that the
      // composer would otherwise only discover after uploading the whole payload.
      // Measure the true UTF-8 byte length up front and reject instantly with the
      // same wording the server's 413 handler uses, so an oversized post fails
      // immediately instead of stalling on the way up. Keep MAX_POST_BYTES a little
      // under the server cap for HTTP/proxy overhead beyond the body; if the Render
      // env var changes, keep this roughly in step with it.
      const MAX_POST_BYTES = 24_000_000;
      const bodyBytes = (typeof Blob !== 'undefined') ? new Blob([body]).size : body.length;
      if (bodyBytes > MAX_POST_BYTES) {
        throw new Error('This Skribl is too large to post. Try a smaller photo or a shorter audio loop.');
      }

      let res;
      // Compression is an OPTIMISATION and must never be load-bearing. This
      // used to call skriblPackBody() directly, which made posting depend on
      // lib/posted.js having loaded — so a stale cache, a partial deploy or a
      // blocked request turned "posts a bit slower" into "cannot post at all",
      // with `skriblPackBody is not defined` shown to the user. Feature-detect
      // it like every other optional capability here, and fall back to the
      // uncompressed body that worked before it existed.
      const packed = (typeof skriblPackBody === 'function')
        ? await skriblPackBody(body, baseHeaders)
        : { body: body, headers: baseHeaders };
      try {
        res = await fetch(apiBase, {
          method: 'POST',
          headers: packed.headers,
          body: packed.body
        });
      } catch (netErr) {
        // Network failure (offline / DNS / CORS) — temporary. Save locally so
        // the user's work isn't lost, but flag it so the UI won't claim "Posted".
        console.warn('sendSkribl: network error, saving locally —', netErr);
        return saveLocalFallback(payload);
      }
      if (res.ok) {
        const data = await res.json().catch(() => null);
        // Server returns { id, url:"/s/<id>" } — a real, shared post. (A 200
        // with idempotentReplay:true is the same post found again after a
        // lost response; identical shape, treated identically.)
        if (data && data.id && data.url) {
          sendSkribl._idemKey = null;   // confirmed: the next post is new work
          return { id: data.id, url: data.url, local: false };
        }
        throw new Error('The server returned an unexpected response.');
      }
      // Server errors ≥500 are temporary → local fallback (flagged). But a 4xx
      // means the post was REJECTED (bad/oversized payload, auth, etc.) — never
      // fake success; surface the real error so the user knows it wasn't shared.
      if (res.status >= 500) {
        console.warn('sendSkribl: server ' + res.status + ', saving locally');
        return saveLocalFallback(payload);
      }
      let msg = 'Post rejected by the server (' + res.status + ').';
      try { const e = await res.json(); if (e && e.error) msg = e.error; } catch (e) {}
      throw new Error(msg);
    }

    // No API base at all (pure standalone build) — local-only by design.
    return saveLocalFallback(payload);
  }

  // Persist to localStorage under an id; hand back a #skribl=<id> hash URL the
  // in-page player opens on THIS device only. `local:true` tells the composer to
  // say "saved locally" rather than "posted/shared".
  async function saveLocalFallback(payload) {
    await new Promise((resolve) => setTimeout(resolve, 300));
    const id = 'local_' + Date.now().toString(36) + Math.random().toString(36).slice(2, 6);
    const post = {
      id,
      createdAt: new Date().toISOString(),
      title: payload.title,
      caption: payload.caption,
      hasAudio: !!((normalizeSkribl(payload).music) || {}).data,
      skribl: payload
    };
    try {
      localStorage.setItem('skribl_post_' + id, JSON.stringify(post));
    } catch (e) {
      throw new Error('Local storage full — could not save Skribl');
    }
    return { id, url: '#skribl=' + id, local: true };
  }

  // Flatten bg + photo + drawing into a single opaque canvas at native size.
  // Kept local (a few lines duplicated from export) so the delicate export IIFE
  // stays untouched. Returns a <canvas>, or null on failure.
  function buildPreviewCanvas() {
    try {
      const w = canvas.width, h = canvas.height;
      const out = document.createElement('canvas');
      out.width = w; out.height = h;
      const octx = out.getContext('2d');
      octx.fillStyle = bgColor || '#0d0f14';
      octx.fillRect(0, 0, w, h);
      if (photoBgImg && photoBgImg.style.display !== 'none' && photoBgImg.src) {
        octx.save();
        octx.globalAlpha = photoOpacityVal_ != null ? photoOpacityVal_ : 1;
        if (photoBlur_ > 0 && 'filter' in octx) octx.filter = `blur(${photoBlur_}px)`;
        const iw = photoBgImg.naturalWidth || w, ih = photoBgImg.naturalHeight || h;
        if (photoFit === 'stretch') {
          octx.drawImage(photoBgImg, 0, 0, w, h);
        } else {
          let scale = photoFit === 'contain' ? Math.min(w/iw, h/ih) : Math.max(w/iw, h/ih);
          if (photoFit === 'cover') scale *= photoZoom;
          const dw = iw * scale, dh = ih * scale;
          const fx = photoFit === 'cover' ? photoOffsetX : 0.5;
          const fy = photoFit === 'cover' ? photoOffsetY : 0.5;
          octx.drawImage(photoBgImg, (w-dw)*fx, (h-dh)*fy, dw, dh);
        }
        octx.restore();
      }
      octx.drawImage(canvas, 0, 0, w, h);
      return out;
    } catch (e) {
      return null;
    }
  }

  function buildPreviewDataURL() {
    const out = buildPreviewCanvas();
    return out ? out.toDataURL('image/png') : null;
  }

  // The card itself is composited by lib/postedcard.js — editors only, beside
  // lib/postedaudio.js, because a host's feed never posts. It moved out of here
  // when Flip needed one too: this
  // function was Pad-only, so every Flip post fell back to the static branded
  // og-card on its unfurl, in a feed's in-post poster and on the profile's
  // tiles. See that module's header.
  //
  // What stays HERE is the flattening — ground, photo with its fit/opacity/blur,
  // then the strokes — because that is the part that genuinely differs between
  // a Pad recording and a Flip animation, and the photo state it reads is this
  // editor's. The encoding is not passed in any more: the module encodes both
  // ways and keeps the smaller, because the content-based rule this used to
  // supply a hint for turned out to be wrong by 16x.
  function buildShareCardDataURL() {
    var PC = window.SkriblPostedCard;
    if (!PC || !PC.build) return null;
    return PC.build(buildPreviewCanvas());
  }

  function updateCharCount() {
    charCount.textContent = captionInput.value.length + ' / 280';
  }

  // states: 'idle' | 'sending' | 'success' | 'error'
  /* The button's resting label comes from the DOM, not from a literal here.
   * The template renders it ("Post to Skribl", or "Add to post" in compose
   * mode) and setState('idle') used to overwrite it with a hardcoded copy —
   * which was already a duplicate of the template's string and would have
   * silently relabelled the compose button back to publishing the first time
   * anything reset the sheet. Same reason the busy verb is chosen by mode:
   * compose is not posting, and must not say it is. */
  const IDLE_LABEL = (submitLabel.textContent || '').trim() || 'Post to Skribl';
  const BUSY_LABEL = (window.SKRIBL_MODE === 'compose') ? 'Adding…' : 'Posting…';

  function setState(state) {
    if (state === 'idle') {
      posting = false;
      status.hidden = true;
      status.classList.remove('error');
      progressFill.style.width = '0%';
      if (watchBtn) watchBtn.hidden = true;
      body.style.opacity = '';
      titleInput.disabled = false;
      captionInput.disabled = false;
      submitBtn.disabled = false;
      submitBtn.hidden = false;
      submitLabel.textContent = IDLE_LABEL;
    } else if (state === 'sending') {
      posting = true;
      status.hidden = false;
      status.classList.remove('error');
      statusLabel.textContent = BUSY_LABEL;
      progressFill.style.width = '35%';
      body.style.opacity = '0.5';
      titleInput.disabled = true;
      captionInput.disabled = true;
      submitBtn.disabled = true;
    } else if (state === 'success') {
      posting = false;
      progressFill.style.width = '100%';
      statusLabel.textContent = 'Posted!';
      submitBtn.hidden = true;
    } else if (state === 'error') {
      posting = false;
      status.classList.add('error');
      statusLabel.textContent = 'Couldn\u2019t post — try again';
      progressFill.style.width = '100%';
      body.style.opacity = '';
      titleInput.disabled = false;
      captionInput.disabled = false;
      submitBtn.disabled = false;
      submitBtn.hidden = false;
      submitLabel.textContent = 'Try again';
    }
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
   * The bake runs later, inside buildPostPayload(). This says what the editor
   * is holding, which is the question the author can still do something about.
   */
  function syncSoundMark() {
    if (!soundMark) return;
    const dot = document.getElementById('musicTabDot');
    const has = !!(dot && !dot.hidden);
    soundMark.hidden = !has;
    if (!has) return;
    const pending = dot.classList.contains('pending');
    if (soundDot) soundDot.classList.toggle('pending', pending);
    const msg = pending
      ? 'Your music file is missing — this will post without sound.'
      : 'This Skribl has sound.';
    soundMark.setAttribute('title', msg);
    if (soundText) soundText.textContent = msg;
  }

  function openPost() {
    setState('idle');
    syncSoundMark();
    // Field values persist across an accidental close within the session; they
    // reset only after a successful post. So don't clear them here.
    updateCharCount();
    const preview = buildPreviewDataURL();
    if (preview) {
      previewImg.src = preview;
      // Mirror the pad's shape so the snapshot shows whole (no crop), and match
      // the frame background to the canvas color so there are never odd bars.
      if (previewFrame) {
        const ratio = (canvas.width && canvas.height) ? (canvas.width / canvas.height) : 1.6;
        previewFrame.style.aspectRatio = ratio.toFixed(4);
        previewFrame.style.background = bgColor || '#0d0f14';
        previewFrame.style.display = '';
      }
    } else if (previewFrame) {
      previewFrame.style.display = 'none';
    }
    clearTimeout(closeTimer);
    overlay.hidden = false;
    requestAnimationFrame(() => { overlay.classList.add('open'); applyKeyboardInset(); });
  }

  function closePost() {
    if (document.activeElement === titleInput || document.activeElement === captionInput) {
      document.activeElement.blur();
    }
    overlay.classList.remove('open');
    if (sheet) sheet.style.maxHeight = '';
    overlay.style.top = ''; overlay.style.bottom = ''; overlay.style.height = '';
    closeTimer = setTimeout(() => { overlay.hidden = true; }, 350);
  }

  // iOS doesn't shrink CSS viewport units for the on-screen keyboard, so the
  // bottom-anchored sheet ends up behind it. Fix: resize the fixed overlay to
  // the *visible* region (above the keyboard) using visualViewport. The sheet,
  // anchored to the overlay's bottom, then sits right on the keyboard — and iOS
  // has no reason to scroll the page and push the header off the top.
  // Mobile only; desktop / unsupported clears any inline styles.
  function applyKeyboardInset() {
    const vv = window.visualViewport;
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

  /* EVERYTHING A PAYLOAD NEEDS BEFORE IT LEAVES THE BROWSER, in one place.
   *
   * Split out of submit() so COMPOSE MODE can reuse it exactly. A skribl the
   * host's composer attaches and a skribl Pad posts itself must be the same
   * bytes: same serialisation, same share-card thumbnail, same mono audio bake.
   * Two code paths preparing "the payload, but for posting" is precisely the
   * shape that produced BUG B below — a post-time step that silently stopped
   * running on one of the paths and looked identical in the metadata.
   *
   * Returns the payload, or null if the media is not ready (it says why).
   */
  async function buildPostPayload() {
    // Mirror saveDraft(): don't serialize while photo/music bytes are still
    // being read into base64, or the posted Skribl could omit them.
    if (mediaBusy > 0) {
      showToast('Preparing media — try again in a moment', submitBtn);
      return null;
    }
    // v211 (v210 review F2): decode is part of readiness. mediaBusy tracks the
    // FileReader; decodeAudioData is a separate promise, and in the gap the
    // crop below saw currentAudioBuffer null and silently shipped the full
    // song. Await the retained decode — it is normally already settled — so
    // the crop can never be skipped for a buffer that is merely late.
    if (window._skriblDecodePending) { try { await window._skriblDecodePending; } catch (e) {} }
    const payload = serializeSkribl();
    payload.title = (titleInput.value || '').trim() || 'Untitled Skribl';
    payload.caption = (captionInput.value || '').trim();
    // Per-Skribl share card for link unfurls. Post-only (kept out of
    // serializeSkribl so drafts stay lean); the server serves it at
    // /s/<id>/card.png and drops it from the player GET envelope. Best-effort —
    // a null card just falls back to the static branded image server-side.
    const card = buildShareCardDataURL();
    if (card) payload.thumbnail = card;
    // Crop music down to just the loop for posting. Post-only — drafts keep the
    // full sample so they can be re-trimmed. The trimmed clip IS the loop, so
    // trimStart/trimEnd become 0..loopLen. Falls back to the full sample if the
    // decoded buffer isn't ready or encoding fails, so a post never breaks here.
    // BUG B (v210): this guarded on payload.music, which serializeSkribl() has
    // not produced since the v2 frame migration — the media lives in
    // frames[0].music. The condition was therefore never true on a v2 Pad post,
    // the crop never ran, and every shared post carried the FULL song with the
    // authored trim rather than the baked loop. Proven by byte count, not by
    // trimEnd: an uncropped payload keeps the authored trim, so the metadata
    // looks identical either way. Located through the shared accessor so no
    // further consumer has to know where a frame keeps its media.
    const media = window.SkriblPayload.currentFrameMedia(payload);
    if (media.music && media.music.data && !currentAudioBuffer) {
      // Decode failed (not merely late — we awaited it). Post the full sample
      // rather than fail the post, but SAY SO: this is how the size regression
      // would hide again.
      console.warn('skribl: music not decoded at post time — posting the full sample');
    }
    if (media.music && media.music.data && currentAudioBuffer) {
      try {
        const cropped = window.SkriblPostedAudio.buildPostedLoopWav({ currentAudioBuffer, trimStart, trimEnd, loopCrossfadeMs });
        if (cropped) {
          // The clip IS the loop now, so trims collapse to 0..len and the
          // crossfade is already folded into the samples.
          media.setMusic({ data: cropped.dataUrl, name: media.music.name,
                           trimStart: 0, trimEnd: cropped.duration, crossfadeMs: 0 });
        }
      } catch (e) {
        // Keep the full-sample media rather than failing the post, but say so:
        // a silent fallback here is how the size regression would hide again.
        console.warn('skribl: loop crop failed, posting the full sample', e);
      }
    }
    return payload;
  }

  async function submit() {
    setState('sending');
    const payload = await buildPostPayload();
    if (!payload) { setState('idle'); return; }
    // COMPOSE MODE HANDS THE PAYLOAD BACK AND PUBLISHES NOTHING. The host holds
    // it on their draft; the single POST happens when they post. Everything
    // above this line has already run, so what they attach is byte-for-byte
    // what Pad would have posted. See editor_compose.js.
    // The preview is built HERE because buildPreviewDataURL is local to this
    // file — a flat PNG of the finished drawing, so the host's composer can
    // show something the instant the overlay closes.
    if (window.SkriblCompose) {
      window.SkriblCompose.deliver(payload, buildPreviewDataURL());
      // Put the sheet away and the button back to rest. The HOST closes its
      // overlay the moment it gets the payload, so nobody sees this — until
      // they press the pad icon again, which reopens the SAME iframe, and a
      // sheet left open is then sitting over the canvas they came back to
      // draw on. (Found exactly that way: the second edit could not draw.)
      setState('idle');
      closePost();
      return;
    }
    try {
      const res = await sendSkribl(payload);
      lastPostUrl = (res && res.url) || null;
      const localOnly = !!(res && res.local);
      // Record it locally, but ONLY a real post. A local fallback is not
      // shareable, so listing it under links you can send would be a lie.
      if (!localOnly && res && res.id && window.SkriblPosted) {
        window.SkriblPosted.add({
          id: res.id, url: res.url, kind: 'pad', pages: 1,
          title: (titleInput.value || '').trim()
        });
        if (window._skriblPostedUI) window._skriblPostedUI.render();
      }
      titleInput.value = '';
      captionInput.value = '';
      updateCharCount();
      setState('success');
      // A posted (or locally-saved) Skribl is finished, so drop the crash-recovery
      // autosave — otherwise returning to the editor (e.g. via "Make your own
      // Skribl") offers to restore the drawing you just posted. Recovery turns
      // back on by itself as soon as you start a new drawing (scheduleAutosave).
      if (typeof clearAutosave === 'function') clearAutosave();
      if (localOnly) {
        // Saved to this device only (no server, or a temporary server/network
        // failure). Be honest — this is NOT a shared post.
        statusLabel.textContent = 'Saved on this device only';
        showToast('Saved locally — works on this device', null);
      } else {
        showToast('Posted! 🎨', null);
      }
      if (watchBtn && lastPostUrl) watchBtn.hidden = false;
    } catch (e) {
      setState('error');
      if (e && e.message) statusLabel.textContent = e.message;
    }
  }

  captionInput.addEventListener('input', updateCharCount);
  submitBtn.addEventListener('click', submit);
  if (watchBtn) watchBtn.addEventListener('click', () => {
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
      // host application navigates the HOST'S page away — and left Pad the odd
      // one out, since Flip's Open player and the posted list are both anchors
      // with target="_blank". Configured by create_blueprint(player_target=...).
      window.open(lastPostUrl, '_blank', 'noopener');
    }
  });

  // Recompute the keyboard lift when the viewport changes or a field is focused.
  if (window.visualViewport) {
    window.visualViewport.addEventListener('resize', applyKeyboardInset);
    window.visualViewport.addEventListener('scroll', applyKeyboardInset);
  }
  titleInput.addEventListener('focus', () => setTimeout(applyKeyboardInset, 100));
  captionInput.addEventListener('focus', () => setTimeout(applyKeyboardInset, 100));

  // Backdrop tap / Escape / handle tap all close — but never mid-send.
  overlay.addEventListener('click', (e) => {
    if (posting) return;
    if (!e.target.closest('.menu-sheet')) closePost();
  });
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && !overlay.hidden && !posting) closePost();
  });
  const postHandle = sheet ? sheet.querySelector('.menu-handle') : null;
  if (postHandle) postHandle.addEventListener('click', (e) => {
    e.stopPropagation();
    if (!posting) closePost();
  });

  // The Post button in the header opens the composer.
  postBtn.addEventListener('click', openPost);
})();

