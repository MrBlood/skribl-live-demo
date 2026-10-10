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
  const titleInput = document.getElementById('postTitleInput');
  const captionInput = document.getElementById('postCaptionInput');
  const submitBtn = document.getElementById('postSubmitBtn');
  const publicInput = document.getElementById('postPublicInput');   // absent in compose mode
  const submitLabel = document.getElementById('postSubmitLabel');
  let lastPostUrl = null, lastPostTitle = '';
  // The device-only save this open sheet made when the server did not answer
  // (v315). If Try again then posts for real, this is the copy it replaces,
  // so the library does not end up holding the same drawing twice.
  let pendingLocalId = null;
  const status = document.getElementById('postStatus');
  const statusLabel = document.getElementById('postStatusLabel');
  // THE SHEET ITSELF IS SHARED WITH FLIP (lib/postsheet.js): opening and
  // closing it, the keyboard lift, its states, the sound mark, and the Watch /
  // Share / Copy link row. This file keeps what is the Pad's own: the payload,
  // the network call, the device-only save and the posted list.
  const ui = window.SkriblPostSheet.attach({
    compose: window.SKRIBL_MODE === 'compose',
    toast: showToast,
    submit: () => submit(),
    cancel: () => { if (sendSkribl._abort) sendSkribl._abort.abort(); },
    onOpen: () => { pendingLocalId = null; renderSpeed(); },
    // Mirror the pad's shape so the snapshot shows whole (no crop), and match
    // the frame background to the canvas color so there are never odd bars.
    preview: () => {
      const src = buildPreviewDataURL();
      return src ? { src, bg: bgColor || '#0d0f14',
                     ratio: (canvas.width && canvas.height) ? (canvas.width / canvas.height) : 1.6 } : null;
    }
  });

  // ---- WHERE A VIEWER STARTS (the owner's pick D1) ----
  // Writes app.js's authorSpeed, which serializeSkribl() posts as `playSpeed`
  // and lib/replayline.js fromPost() turns into a start: Auto (as drawn under
  // a minute of drawing, Fit over it), As drawn, Fit, or a rate. The fourth
  // button is a rate the author already chose, or else the speed the Pad's
  // preview last watched at when that is neither 1x nor Fit -- "the speed you
  // last watched it at", which is what a picked speed usually is.
  const speedSeg = document.getElementById('postSpeedSeg');
  const speedHint = document.getElementById('postSpeedHint');
  const SPEED_HINTS = {
    auto: 'As drawn if it took under a minute, fit to about 30 seconds if longer.',
    drawn: 'In real time, with your pause setting.',
    fit: 'The whole drawing in about 30 seconds.',
  };
  function renderSpeed() {
    if (!speedSeg) return;
    const cur = authorSpeed || 'auto';
    const rate = typeof cur === 'number' ? cur
      : (typeof replayChoice === 'number' && replayChoice !== 1 ? replayChoice : null);
    const fourth = speedSeg.querySelector('[data-speed=""], [data-rate-pick]');
    fourth.hidden = rate == null;
    if (rate != null) {
      fourth.dataset.speed = String(rate);
      fourth.setAttribute('data-rate-pick', '');
      fourth.textContent = SkriblReplayLine.label(rate);
    }
    speedSeg.querySelectorAll('button').forEach(b => b.classList.toggle('on', b.dataset.speed === String(cur)));
    speedHint.textContent = (SPEED_HINTS[cur] || 'At ' + SkriblReplayLine.label(rate) +
      ', the speed you watched it at.') + ' Anyone watching can change it.';
  }
  if (speedSeg) speedSeg.addEventListener('click', (e) => {
    const b = e.target.closest('button');
    if (!b || b.hidden) return;
    const v = b.dataset.speed;
    authorSpeed = +v ? +v : v;
    renderSpeed();
  });

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
      let body = JSON.stringify(payload);

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
      // "UNCHANGED" IS JUDGED WITH THE TIMESTAMPS TAKEN OUT (SK-AUD-001).
      // serializeSkribl() stamps draftId, createdAt and updatedAt at the
      // moment of serialising, so two submits of the same drawing were never
      // the same bytes, this branch minted a fresh key every time, and from
      // v200 until the audit's lost-response pin in verify_posted no Pad retry
      // had ever replayed — for an author with an account either. The server
      // reads none of the three (it stamps its own createdAt), so the retry
      // resends the FIRST attempt's exact bytes, which is what the server's
      // fingerprint (F4) requires of a replay and also the truer timestamp.
      const work = JSON.stringify(payload, (k, v) =>
        (k === 'draftId' || k === 'createdAt' || k === 'updatedAt') ? undefined : v);
      if (sendSkribl._idemWork !== work) {
        sendSkribl._idemKey = null;
        sendSkribl._idemTok = null;
        sendSkribl._idemWork = work;
        sendSkribl._idemBody = body;
      } else {
        body = sendSkribl._idemBody;
      }
      if (!sendSkribl._idemKey) {
        sendSkribl._idemKey = (typeof crypto !== 'undefined' && crypto.randomUUID)
          ? crypto.randomUUID()
          : 'k' + Date.now().toString(36) + Math.random().toString(36).slice(2, 12);
      }
      const baseHeaders = skriblPostHeaders();
      baseHeaders['Idempotency-Key'] = sendSkribl._idemKey;
      // THE TWO CLIENT CAPABILITIES (SK-AUD-001; lib/posted.js explains both).
      // The client id is what lets the server honour the key for an anonymous
      // author at all; the delete token, minted here and held for exactly as
      // long as the key, is what survives the response being lost — the
      // server's own would have been handed over once, in the answer that
      // never arrived. Both ride the retry, so a replayed post ends with this
      // browser holding the key that deletes it. Either is null without Web
      // Crypto (RE-AUD-001), and a null is not sent: the server then mints
      // the key, as it always did.
      if (window.SkriblPosted) {
        const cid = window.SkriblPosted.clientId();
        if (cid) baseHeaders['X-Skribl-Client'] = cid;
        if (!sendSkribl._idemTok) sendSkribl._idemTok = window.SkriblPosted.mintSecret();
        if (sendSkribl._idemTok) baseHeaders['X-Skribl-Delete-Token'] = sendSkribl._idemTok;
      }

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
      // Cancel (lib/postsheet.js, after a slow wait) aborts this request. The
      // key is kept: if the server did make the post, Try again finds it.
      sendSkribl._abort = (typeof AbortController === 'function') ? new AbortController() : null;
      try {
        res = await fetch(apiBase, {
          method: 'POST',
          headers: packed.headers,
          body: packed.body,
          signal: sendSkribl._abort ? sendSkribl._abort.signal : undefined
        });
      } catch (netErr) {
        if (netErr && netErr.name === 'AbortError') {
          throw new Error('Cancelled \u2014 not posted. Your Skribl is safe here; Try again sends it.');
        }
        // Network failure (offline / DNS / CORS) — temporary. Save locally so
        // the user's work isn't lost, but flag it so the UI won't claim "Posted".
        console.warn('sendSkribl: network error, saving locally —', netErr);
        return saveLocalFallback(payload, true);
      }
      if (res.ok) {
        const data = await res.json().catch(() => null);
        // Server returns { id, url:"/s/<id>" } — a real, shared post. (A 200
        // with idempotentReplay:true is the same post found again after a
        // lost response; identical shape, treated identically.)
        if (data && data.id && data.url) {
          // THE KEY THE AUTHOR HOLDS. The server's, when the answer carried one
          // (a fresh create); the one this client minted, when it did not (a
          // replay after a lost response answers with the id alone, and the
          // token it was created under is the one we sent). Until SK-AUD-001
          // this object carried no token at all, so Pad's Your Skribls entries
          // never held their revocation key — the "Delete" and "Copy key"
          // affordances lib/postedui.js shows only where a key is held had been
          // absent from every Pad post since they were built. Flip's had them.
          const tok = data.deleteToken || sendSkribl._idemTok || null;
          sendSkribl._idemKey = null;   // confirmed: the next post is new work
          sendSkribl._idemTok = null;
          return { id: data.id, url: data.url, local: false, deleteToken: tok };
        }
        throw new Error('The server returned an unexpected response.');
      }
      // Server errors ≥500 are temporary → local fallback (flagged). But a 4xx
      // means the post was REJECTED (bad/oversized payload, auth, etc.) — never
      // fake success; surface the real error so the user knows it wasn't shared.
      if (res.status >= 500) {
        console.warn('sendSkribl: server ' + res.status + ', saving locally');
        return saveLocalFallback(payload, true);
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
  // say "Not posted" rather than "posted/shared". `retryable` is true when a
  // server exists and did not answer (offline, a 5xx) -- the composer then
  // offers Try again -- and false for a build with no server at all, where a
  // retry would only make a second copy on this device.
  async function saveLocalFallback(payload, retryable) {
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
    return { id, url: '#skribl=' + id, local: true, retryable: !!retryable };
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

  // Saved drafts' list picture (lib/savedrafts.js) is the same flattening.
  window.skriblPreviewCanvas = function () { return buildPreviewCanvas(); };
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
    // THE PUBLIC CHOICE (v304). Sent only when the author ticked it and only
    // when this Pad is posting for itself: in compose mode the checkbox is not
    // rendered and the HOST's composer sets visibility on the body it posts.
    // Unticked, the key is left out — the server's "unlisted" default is the
    // one statement of what an unmarked post is, and repeating it here would
    // be a second copy to drift.
    if (publicInput && publicInput.checked && window.SKRIBL_MODE !== 'compose') {
      payload.visibility = 'public';
    }
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
    ui.setState('sending');
    const payload = await buildPostPayload();
    if (!payload) { ui.setState('idle'); return; }
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
      ui.setState('idle');
      ui.close();
      return;
    }
    try {
      const res = await sendSkribl(payload);
      lastPostUrl = (res && res.url) || null;
      lastPostTitle = payload.title || '';   // what was posted, with the default applied; Share hands it on
      const localOnly = !!(res && res.local);
      // A LOCAL SAVE IS RECORDED TOO (SK-AUD-010), flagged so the tray shows it
      // as "on this device" with nothing to send. This used to record only a
      // real post, on the argument that a local save is not shareable — and an
      // unlisted 'skribl_post_*' blob is what lib/posted.js's orphan sweep
      // deletes under storage pressure, so "Saved on this device only" was
      // describing bytes the next full store would remove. The url stored is
      // the Pad's own path plus the hash, so the row opens from Flip's tray as
      // well as this one.
      if (localOnly && res && res.id && window.SkriblPosted) {
        window.SkriblPosted.add({
          id: res.id, kind: 'pad', pages: 1, local: true,
          url: location.pathname + location.search + res.url,
          title: (titleInput.value || '').trim()
        });
        if (window._skriblPostedUI) window._skriblPostedUI.render();
      }
      if (!localOnly && pendingLocalId && window.SkriblPosted) {
        // Try again worked: the device-only copy from the first attempt is
        // superseded by the post, bytes and all.
        window.SkriblPosted.remove(pendingLocalId);
        pendingLocalId = null;
      }
      if (!localOnly && res && res.id && window.SkriblPosted) {
        const kept = window.SkriblPosted.add({
          id: res.id, url: res.url, kind: 'pad', pages: 1,
          title: (titleInput.value || '').trim(),
          visibility: (publicInput && publicInput.checked && window.SKRIBL_MODE !== 'compose') ? 'public' : 'unlisted',
          // The create response carries the revocation capability exactly
          // once for an anonymous post. Stored here, and since v281 also
          // re-enterable through Your Skribls if the author kept a copy.
          tok: res.deleteToken || null,
          // The server's reading of the payload, not this client's guess.
          has_audio: typeof res.hasAudio === 'boolean' ? res.hasAudio : null
        });
        if (window._skriblPostedUI) window._skriblPostedUI.render();
        // THE RETURN VALUE IS CHECKED NOW. It was discarded until v280, so a
        // browser that could not write left the post live and its only
        // revocation key gone, with this same code path reporting success two
        // lines later. When the store cannot hold the key, the user is the
        // only remaining custodian and gets the chance to be one.
        if (kept && !kept.durable && kept.key && window.SkriblRecoveryKey) {
          window.SkriblRecoveryKey.present({ key: kept.key, url: res.url });
        }
      }
      // The title and caption are NOT cleared: they stay in their fields as
      // the record of what was just posted, and are still there for the next
      // post of the same drawing. Wiping them read as losing them.
      ui.setState('success');
      // A posted (or locally-saved) Skribl is finished, so drop the crash-recovery
      // autosave — otherwise returning to the editor (e.g. via "Make your own
      // Skribl") offers to restore the drawing you just posted. Recovery turns
      // back on by itself as soon as you start a new drawing (scheduleAutosave).
      if (typeof clearAutosave === 'function') clearAutosave();
      if (localOnly) {
        // Saved to this device only (no server, or a temporary server/network
        // failure). Be honest — this is NOT a shared post. v315 (SK312-008):
        // it said "Saved on this device only" under a button called Post, and
        // an outside audit pointed out that people scan outcomes rather than
        // read them. It now leads with what did NOT happen, is drawn as a
        // warning, and -- where a server exists -- keeps a way to finish the
        // job in the sheet: Try again posts the same drawing.
        statusLabel.textContent = 'Not posted \u2014 saved on this device';
        status.classList.add('error');
        showToast('Not posted \u2014 saved on this device', null);
        // A retry that still could not reach the server makes a new save; the
        // one it retried is dropped, so there is only ever one copy to find.
        if (pendingLocalId && res && pendingLocalId !== res.id && window.SkriblPosted) {
          window.SkriblPosted.remove(pendingLocalId);
          if (window._skriblPostedUI) window._skriblPostedUI.render();
        }
        pendingLocalId = null;
        if (res && res.retryable) {
          pendingLocalId = res.id;
          submitBtn.hidden = false;
          submitBtn.disabled = false;
          submitLabel.textContent = 'Try again';
        }
      } else {
        showToast('Posted! 🎨', null);
      }
      ui.result(lastPostUrl, lastPostTitle, { localOnly });
    } catch (e) {
      ui.setState('error');
      if (e && e.message) statusLabel.textContent = e.message;
    }
  }

  // The Post button in the header opens the composer.
  postBtn.addEventListener('click', ui.open);
})();

