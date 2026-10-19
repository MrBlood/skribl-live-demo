/* Saved drafts — ⋯ "Save draft" and "Open a draft…" on both editors (v316), and the Library's Drafts tab (v317).
 *
 * WHAT IT IS FOR, in the owner's words: "a way to save skribl drafts (not on
 * my machine as a file), so I could just click the pen to add a skribl to the
 * post, load the saved skribl, then add it to post." A draft is the editor's
 * own draft object (the one a .skribl backup file holds), so opening one is
 * the path opening a backup already takes, on the editor that made it.
 *
 * TWO PLACES, ONE LIST. Signed in (a host that supplies current_user_id), a
 * draft goes to the author's account through /api/drafts and follows them to
 * any device. Signed out (the standalone demo has no accounts) it stays in THIS
 * browser, in IndexedDB beside the autosave's media store. The sheet says
 * which, so nobody believes a browser-only draft is on their phone too.
 *
 * WHAT IT OWNS: the list sheet, save (create, or overwrite the draft that is
 * open), open (on this editor, or hand-off to the other one with ?draft=<id>),
 * delete (two taps). WHAT IT DOES NOT: serialising and loading a drawing,
 * which each editor passes in, because the Pad's and Flip's documents differ.
 *
 * The editors and the Library load it; the Library lists, ends its rows
 * (rowEnd: Save a .skribl file, Delete) and never calls init(), so open()
 * does nothing there. The player never saves anything
 * (verify_player_isolation).
 */
(function (global) {
  'use strict';

  var doc = global.document;
  var cfg = global.SKRIBL_DRAFTS || {};
  var LIMIT = cfg.limit || 25;
  var THUMB_W = 240;

  function jsonHeaders() {
    var h = { 'Content-Type': 'application/json' };
    if (global.SKRIBL_CSRF_TOKEN) h['X-Skribl-CSRF'] = global.SKRIBL_CSRF_TOKEN;
    return h;
  }
  function failWith(r) {
    return r.json().catch(function () { return {}; }).then(function (d) {
      var e = new Error(d.error || ('The drafts service answered ' + r.status + '.'));
      e.conflict = !!d.conflict;   // a 409 from a save made over an older copy (below)
      throw e;
    });
  }

  /* ---- where drafts live ---------------------------------------------- */
  var server = {
    where: 'account',
    list: function () {
      return fetch(cfg.api, { credentials: 'same-origin' })
        .then(function (r) { return r.ok ? r.json() : failWith(r); })
        .then(function (d) { return d.items || []; });
    },
    load: function (id) {
      return fetch(cfg.api + '/' + encodeURIComponent(id), { credentials: 'same-origin' })
        .then(function (r) { return r.ok ? r.json() : failWith(r); });
    },
    save: function (id, body) {
      return fetch(id ? cfg.api + '/' + encodeURIComponent(id) : cfg.api, {
        method: id ? 'PUT' : 'POST', credentials: 'same-origin',
        headers: jsonHeaders(), body: JSON.stringify(body)
      }).then(function (r) { return r.ok ? r.json() : failWith(r); });
    },
    remove: function (id) {
      return fetch(cfg.api + '/' + encodeURIComponent(id), {
        method: 'DELETE', credentials: 'same-origin', headers: jsonHeaders()
      }).then(function (r) { if (!r.ok && r.status !== 404) return failWith(r); });
    }
  };

  /* This browser: an index record of summaries, and one record per draft. */
  var IDX = 'saved:index';
  function store() {
    if (!global.SkriblDraftStore) throw new Error('This browser cannot keep drafts.');
    return global.SkriblDraftStore;
  }
  /* A READ THAT FAILED IS NOT AN EMPTY LIST (v317). This swallowed the error
     and answered [] -- so a storage hiccup showed "no drafts", and a save that
     followed wrote an index holding only the new draft over the real one,
     which is how the owner's drafts "were there, then they disappeared". The
     error now travels: the sheet says so, and save and delete refuse to write
     an index they could not read. */
  function readIndex() {
    return store().get(IDX).then(function (v) { return (v && v.items) || []; });
  }
  /* THE WAY BACK for drafts an index already lost. Each draft's record
     ('saved:<id>') outlived the index that listed it, so the list gathers any
     record the index does not name and writes it back in. And the other way:
     a row whose record is gone (a delete that stopped half-way) is dropped,
     not shown as a draft that answers "not found". */
  function byNewest(a, b) { return String(b.updatedAt || '').localeCompare(String(a.updatedAt || '')); }
  function recover(items) {
    if (!store().keys) return Promise.resolve(items);
    return store().keys().then(function (ks) {
      var have = {}, known = {};
      ks.forEach(function (k) { have[k] = true; });
      var kept = items.filter(function (i) { return have['saved:' + i.id]; });
      var pruned = kept.length !== items.length;
      items = kept;
      items.forEach(function (i) { known['saved:' + i.id] = true; });
      var lost = ks.filter(function (k) {
        return typeof k === 'string' && k.indexOf('saved:') === 0 && k !== IDX && !known[k];
      });
      if (!lost.length) {
        if (!pruned) return items;
        return store().put(IDX, { items: items }).then(function () { return items; },
                                                      function () { return items; });
      }
      return Promise.all(lost.map(function (k) {
        return store().get(k).catch(function () { return null; });
      })).then(function (recs) {
        var back = recs.filter(function (r) { return r && r.id && r.payload; }).map(function (r) {
          return { id: r.id, kind: r.kind === 'flip' ? 'flip' : 'pad', title: r.title || 'Untitled Skribl',
                   thumbnail: r.thumbnail || null, createdAt: r.savedAt || null, updatedAt: r.savedAt || null };
        });
        if (!back.length && !pruned) return items;
        var all = items.concat(back).sort(byNewest);
        return store().put(IDX, { items: all }).then(function () { return all; },
                                                     function () { return all; });
      });
    }, function () { return items; });
  }
  var local = {
    where: 'browser',
    list: function () { return readIndex().then(recover); },
    load: function (id) {
      return store().get('saved:' + id).then(function (rec) {
        if (!rec) throw new Error('Draft not found.');
        return rec;
      });
    },
    save: function (id, body) {
      return readIndex().then(function (items) {
        var now = new Date().toISOString();
        var existing = id ? items.filter(function (i) { return i.id === id; })[0] : null;
        if (!existing && items.length >= LIMIT) {
          throw new Error('You have ' + items.length + ' saved drafts, which is the limit. Delete one to save another.');
        }
        var sum = {
          id: existing ? existing.id : ('b' + Date.now().toString(36) + Math.random().toString(36).slice(2, 8)),
          kind: body.kind, title: body.title || 'Untitled Skribl', thumbnail: body.thumbnail || null,
          createdAt: existing ? existing.createdAt : now, updatedAt: now
        };
        var rest = items.filter(function (i) { return i.id !== sum.id; });
        // The record carries its own summary, so recover() can rebuild a row.
        return store().put('saved:' + sum.id, { id: sum.id, kind: sum.kind, title: sum.title, payload: body.payload,
                                                thumbnail: sum.thumbnail, savedAt: sum.updatedAt })
          .then(function () { return store().put(IDX, { items: [sum].concat(rest) }); })
          .then(function () { return sum; });
      });
    },
    // THE RECORD FIRST, THEN THE ROW (v317). The other order, with recover()
    // re-adding any record the index does not name, brought a draft back
    // whenever the second step failed. Now a failed first step changes nothing,
    // and a failed second step leaves a row recover() drops on the next list.
    remove: function (id) {
      return readIndex().then(function (items) {
        return store().del('saved:' + id).then(function () {
          return store().put(IDX, { items: items.filter(function (i) { return i.id !== id; }) });
        });
      });
    }
  };

  var backend = (cfg.signedIn && cfg.api) ? server : local;

  /* ---- helpers --------------------------------------------------------- */
  function thumbFrom(canvas) {
    if (!canvas || !canvas.width) return null;
    try {
      var t = doc.createElement('canvas');
      t.width = THUMB_W;
      t.height = Math.max(1, Math.round(canvas.height * THUMB_W / canvas.width));
      var x = t.getContext('2d');
      x.fillStyle = '#0d0f14';
      x.fillRect(0, 0, t.width, t.height);
      x.drawImage(canvas, 0, 0, t.width, t.height);
      return t.toDataURL('image/jpeg', 0.72);
    } catch (e) { return null; }
  }
  function ago(iso) {
    if (!iso) return '';
    var t = Date.parse(/Z|[+-]\d\d:\d\d$/.test(iso) ? iso : iso + 'Z');
    if (isNaN(t)) return '';
    // The Library's vocabulary (lib/posted.js), which every page that shows
    // drafts loads first; the compact form only if it somehow did not.
    if (global.SkriblPosted && global.SkriblPosted.ago) return global.SkriblPosted.ago(t);
    var s = Math.max(0, (Date.now() - t) / 1000);
    if (s < 60) return 'just now';
    if (s < 3600) return Math.floor(s / 60) + 'm ago';
    if (s < 86400) return Math.floor(s / 3600) + 'h ago';
    if (s < 86400 * 7) return Math.floor(s / 86400) + 'd ago';
    return new Date(t).toLocaleDateString();
  }
  function el(tag, cls, text) {
    var e = doc.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = text;
    return e;
  }

  /* ---- the sheet ------------------------------------------------------- */
  var sheet = null, scrim = null, listEl = null, opts = null, opener = null, thisPic = null;
  var armOnRender = null;   // a ?draft=<id> that arrived over work on the canvas

  function build() {
    scrim = el('div', 'sdrafts-scrim');
    scrim.hidden = true;
    sheet = el('div', 'sdrafts-sheet');
    sheet.id = 'savedDraftsSheet';
    sheet.hidden = true;
    sheet.setAttribute('role', 'dialog');
    sheet.setAttribute('aria-modal', 'true');
    sheet.setAttribute('aria-label', 'Your drafts');
    var head = el('div', 'sdrafts-head');
    var h = el('h2', 'sdrafts-title', 'Your drafts');
    var close = el('button', 'sdrafts-close');
    close.type = 'button';
    close.setAttribute('aria-label', 'Close');
    if (global.SkriblMarks) global.SkriblMarks.into(close, 'close', '\u2715'); else close.textContent = '\u2715';
    close.addEventListener('click', hide);
    head.appendChild(h);
    head.appendChild(close);
    var sub = el('p', 'sdrafts-sub', backend.where === 'account'
      ? 'Saved to your account, on every device you sign in on.'
      : 'Saved on this browser only.');
    listEl = el('div', 'sdrafts-list');
    // The scroll bar's lane, only while the list scrolls (styles.css).
    if (typeof global.ResizeObserver === 'function') new global.ResizeObserver(lane).observe(listEl);
    /* THIS DRAWING, and THE FILE BOTH WAYS (owner, after v323: drafts and
       backups as one choice). The ⋯ menu writes the name row and the two
       .skribl rows in .menu-movers (templates/skribl/_skribl_menu.html); the
       elements themselves move here, so the listeners each editor bound to
       them at load (lib/nametab.js; editor_menu.js / flip.js) come along. A
       tap on one puts this sheet away first: each opens something of its own. */
    var movers = doc.querySelector('.menu-movers');
    var nameBtn = movers && movers.querySelector('[data-drafts-slot="name"]');
    var fileBtns = movers ? [].slice.call(movers.querySelectorAll('[data-drafts-slot="file"]')) : [];
    var mine = el('div', 'sdrafts-this');
    thisPic = el('span', 'sdrafts-thumb sdrafts-this-thumb');
    thisPic.setAttribute('aria-hidden', 'true');
    var saveNow = el('button', 'sdrafts-save', 'Save');
    saveNow.type = 'button';
    saveNow.setAttribute('aria-label', 'Save this drawing to your drafts');
    saveNow.addEventListener('click', function () {
      if (asks()) hide();   // the name box drops from the header, under this sheet
      saveAsking().then(function (sum) { if (sum && !sheet.hidden) refresh(); });
    });
    mine.appendChild(thisPic);
    if (nameBtn) { nameBtn.addEventListener('click', hide, true); mine.appendChild(nameBtn); }
    mine.appendChild(saveNow);
    var savedLbl = el('h3', 'sdrafts-label', 'Saved drafts');
    var files = el('div', 'sdrafts-files');
    fileBtns.forEach(function (b) { b.addEventListener('click', hide, true); files.appendChild(b); });
    // A phone's grabber, like every other sheet's: tap it or swipe the sheet
    // down to close (lib/sheetswipe.js). Hidden above phone widths.
    var grab = el('div', 'sdrafts-grab');
    grab.setAttribute('aria-hidden', 'true');
    sheet.appendChild(grab);
    sheet.appendChild(head);
    sheet.appendChild(mine);
    sheet.appendChild(savedLbl);
    sheet.appendChild(sub);
    sheet.appendChild(listEl);
    if (fileBtns.length) {
      sheet.appendChild(el('h3', 'sdrafts-label', 'As a file'));
      sheet.appendChild(files);
    }
    doc.body.appendChild(scrim);
    doc.body.appendChild(sheet);
    scrim.addEventListener('click', hide);
    if (window.SkriblSheetSwipe) window.SkriblSheetSwipe.attach(sheet, { handle: grab, close: hide });
    sheet.addEventListener('keydown', function (e) { if (e.key === 'Escape') { e.stopPropagation(); hide(); } });
  }

  function hide() {
    if (!sheet || sheet.hidden) return;
    if (global.SkriblModal) global.SkriblModal.close(sheet);
    // Eases down on a phone with its dim, then hides (lib/sheetswipe.js).
    var gone = function () { sheet.hidden = true; scrim.hidden = true; };
    if (global.SkriblSheetSwipe) global.SkriblSheetSwipe.slideOut(sheet, { fade: [scrim], done: gone });
    else gone();
  }

  /* ONE ROW ASKS AT A TIME (v317). The owner's phone showed two rows both
     saying "Tap again" -- arming a row never disarmed the one armed before it,
     so an old question sat beside a new one. Every row registers how to put
     itself back, and arming any row puts every other one back first. */
  var disarmers = [];
  function disarmOthers(keep) {
    disarmers.forEach(function (d) { if (d !== keep) d(); });
  }
  // A bin, not a ×: a × reads as "close", and it was the smallest thing on the row.
  var BIN = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" '
    + 'stroke-linejoin="round" aria-hidden="true"><path d="M3 6h18"/><path d="M8 6V4h8v2"/>'
    + '<path d="M19 6l-1 14H6L5 6"/><path d="M10 11v6M14 11v6"/></svg>';

  /* When the store is not answering, drafts saved now are kept in a smaller
     one and older ones may not show until it answers: say so, above the list,
     rather than let an incomplete list pass for the whole one. */
  function stalled() {
    return backend === local && global.SkriblDraftStore && global.SkriblDraftStore.degraded
      && global.SkriblDraftStore.degraded();
  }
  var STALLED = 'This browser\u2019s storage is slow to answer. Drafts you save now are kept, and older ones will show when it answers.';
  function render(items) {
    listEl.textContent = '';
    disarmOthers(null);   // a stale question takes its listener with it
    disarmers = [];
    if (stalled()) listEl.appendChild(el('p', 'sdrafts-stalled', STALLED));
    if (!items.length) {
      listEl.appendChild(el('p', 'sdrafts-empty',
        'No saved drafts yet. Save this one with Save, above.'));
      return;
    }
    items.forEach(function (it) {
      var row = el('div', 'sdrafts-row');
      var openBtn = el('button', 'sdrafts-open');
      openBtn.type = 'button';
      openBtn.setAttribute('data-draft-id', it.id);
      var pic = el('span', 'sdrafts-thumb');
      if (it.thumbnail) {
        var img = doc.createElement('img');
        img.alt = '';
        img.src = it.thumbnail;
        pic.appendChild(img);
      }
      var words = el('span', 'sdrafts-words');
      var name = el('span', 'sdrafts-name', it.title || 'Untitled Skribl');
      var other = it.kind !== opts.kind;
      var meta = el('span', 'sdrafts-meta', (it.kind === 'flip' ? 'Flip' : 'Pad') + ' \u00B7 ' + ago(it.updatedAt)
        + (other ? ' \u00B7 opens in ' + (it.kind === 'flip' ? 'Flip' : 'Pad') : ''));
      words.appendChild(name);
      words.appendChild(meta);
      openBtn.appendChild(pic);
      openBtn.appendChild(words);
      var del = el('button', 'sdrafts-del');
      del.type = 'button';
      var delLabel = 'Delete ' + (it.title || 'this draft');
      del.setAttribute('aria-label', delLabel);
      del.innerHTML = BIN;
      // The row's question is spoken when it is asked, not only shown.
      meta.setAttribute('aria-live', 'polite');
      var armedOpen = false, armedDel = false, metaText = meta.textContent, armT = null;
      function outside(e) { if (!del.contains(e.target)) disarm(); }
      function disarm() {
        if (armedDel) {
          clearTimeout(armT);
          doc.removeEventListener('pointerdown', outside, true);
        }
        armedOpen = false; armedDel = false;
        meta.textContent = metaText;
        row.classList.remove('armed');
        del.classList.remove('armed');
        del.setAttribute('aria-label', delLabel);
        del.innerHTML = BIN;
      }
      disarmers.push(disarm);
      del.addEventListener('focusout', function () { if (armedDel) disarm(); });
      openBtn.addEventListener('click', function () {
        // Opening REPLACES the canvas. Work on it is asked about once, on the
        // row itself, the way New Skribl asks: a second tap confirms.
        if (!armedOpen && opts.hasContent && opts.hasContent()) {
          disarmOthers(disarm);
          if (armedDel) disarm();
          armedOpen = true;
          meta.textContent = 'Tap again \u2014 this replaces what is on your canvas';
          row.classList.add('armed');
          return;
        }
        openDraft(it);
      });
      del.addEventListener('click', function () {
        if (!armedDel) {
          disarmOthers(disarm);
          if (armedOpen) disarm();
          armedDel = true;
          /* THE BIN ASKS WITHOUT MOVING (the v317 bin rule, which the media
             drawer's bin follows): it keeps its 44px box and tints its icon,
             and the meta line -- a live region -- asks. It used to grow into
             a "Delete?" pill over the row. It disarms when focus leaves it, on
             a tap anywhere else, and on a 20 s safety net. */
          meta.textContent = 'Tap the bin again to delete';
          // Its name says what the next tap does; the old label hid the question.
          del.setAttribute('aria-label', 'Tap again to delete ' + (it.title || 'this draft'));
          del.classList.add('armed');
          armT = setTimeout(disarm, 20000);
          doc.addEventListener('pointerdown', outside, true);
          return;
        }
        disarm();
        // The list is rebuilt, and the bin that had focus goes with it; a
        // keyboard user left on <body> was outside the dialog, where Tab and
        // Escape no longer reached it (third review). Focus lands on the row
        // that took this one's place, or the sheet's close button.
        var at = Array.prototype.indexOf.call(listEl.querySelectorAll('.sdrafts-row'), row);
        var hadFocus = row.contains(document.activeElement);
        backend.remove(it.id).then(function () {
          if (opts._current === it.id) opts._current = null;
          return refresh();
        }, function (e) { opts.toast(e.message); return false; }).then(function (ok) {
          if (ok === false || !hadFocus || sheet.hidden) return;   // a refused delete keeps its row, and focus
          var rows = listEl.querySelectorAll('.sdrafts-row');
          var next = rows[Math.min(at, rows.length - 1)];
          var target = (next && next.querySelector('.sdrafts-open')) || sheet.querySelector('.sdrafts-close');
          if (target) target.focus();
        });
      });
      row.appendChild(openBtn);
      row.appendChild(del);
      listEl.appendChild(row);
      if (armOnRender === it.id) {
        armOnRender = null;
        openBtn.click();   // arms, because the canvas has work on it
        openBtn.focus();
      }
    });
    lane();
  }
  /* iOS paints its scroll bar OVER the list, so while the list scrolls the
     rows leave it a lane (v317); while it does not, they are as wide as the
     cards above and below them (owner's iPhone, after v324). */
  function lane() {
    if (listEl) listEl.classList.toggle('sdrafts-scrolls', listEl.scrollHeight > listEl.clientHeight + 1);
  }

  // Only the LATEST list draws: an earlier read that answers late would put a
  // just-deleted row back, which then answers "not found" (v317 review).
  var listSeq = 0;
  function refresh() {
    var mine = ++listSeq;
    listEl.textContent = '';
    listEl.appendChild(el('p', 'sdrafts-empty', 'Loading\u2026'));
    return backend.list().then(function (items) {
      if (mine === listSeq) render(items);
    }, function (e) {
      if (mine !== listSeq) return;
      /* A list that cannot be read says so and offers the way back, rather
         than "Loading…" for good (v317, the owner's iPhone). */
      listEl.textContent = '';
      listEl.appendChild(el('p', 'sdrafts-empty', e.message));
      var again = el('button', 'sdrafts-retry', 'Try again');
      again.type = 'button';
      again.addEventListener('click', refresh);
      listEl.appendChild(again);
    });
  }

  // The drawing on the canvas, small, as its draft would be saved.
  function paintThis() {
    if (!thisPic) return;
    thisPic.textContent = '';
    var src = thumbFrom(opts.thumbnail && opts.thumbnail());
    if (!src) return;
    var img = doc.createElement('img');
    img.alt = '';
    img.src = src;
    thisPic.appendChild(img);
  }

  function show(from) {
    if (!opts) return;   // the sheet is an editor's; the Library lists drafts itself
    if (!sheet) build();
    opener = from || null;
    if (global.SkriblSheetSwipe) global.SkriblSheetSwipe.cancelSlide(sheet);
    paintThis();
    sheet.hidden = false;
    scrim.hidden = false;
    if (global.SkriblSheetSwipe) global.SkriblSheetSwipe.slideIn(sheet);
    if (global.SkriblModal) global.SkriblModal.open(sheet, opener);
    refresh();
  }

  /* The other editor opens it: the draft's id rides in the URL of that
     editor's own menu link, so a composer session stays a composer session. */
  function handOff(it) {
    var url = opts.otherUrl && opts.otherUrl();
    if (!url) return;
    global.location.href = url + (url.indexOf('?') >= 0 ? '&' : '?') + 'draft=' + encodeURIComponent(it.id);
  }

  function openDraft(it) {
    if (it.kind !== opts.kind) { hide(); handOff(it); return; }
    backend.load(it.id).then(function (rec) {
      hide();
      opts.load(rec.payload);
      opts._current = it.id;
      opts._base = rec.updatedAt || null;
      if (global.SkriblName && rec.title) global.SkriblName.set(rec.title);
      opts.toast('Opened \u201C' + (rec.title || 'Untitled Skribl') + '\u201D');
    }, function (e) { opts.toast(e.message); });
  }

  function save() {
    // A file still being read would be saved under its new name with the old
    // bytes, or not at all while the toast said Saved (third review). First,
    // because a photo on its way is work even before it counts as content.
    if (opts.busy && opts.busy()) { opts.toast('Preparing media \u2014 try again in a moment'); return Promise.resolve(null); }
    if (opts.hasContent && !opts.hasContent()) { opts.toast('Draw something to save'); return Promise.resolve(null); }
    var payload;
    try { payload = opts.serialize(); } catch (e) { opts.toast('Could not read the drawing to save it.'); return Promise.resolve(null); }
    var title = (global.SkriblName && global.SkriblName.get()) || 'Untitled Skribl';
    var body = { kind: opts.kind, title: title, payload: payload, thumbnail: thumbFrom(opts.thumbnail && opts.thumbnail()) };
    var was = opts._current;
    /* THE COPY THIS SAVE IS MADE FROM (the v321 audit's SK-AUD-004). An
       account draft can be open on two devices; without this the second save
       replaced the first, silently. The server overwrites only if the stored
       draft is still the one this editor opened or last saved, and answers 409
       otherwise -- and then BOTH are kept: this one is saved as a new copy and
       the toast says why. This browser's own store has one writer per draft
       and ignores it. */
    if (was && opts._base) body.baseUpdatedAt = opts._base;
    return backend.save(was, body).then(function (sum) {
      opts._current = sum.id;
      opts._base = sum.updatedAt || null;
      // "Updated" only when it was: a local store answers a vanished id with a
      // new draft rather than an error.
      opts.toast(was && sum.id === was ? 'Draft updated' : (backend.where === 'account' ? 'Saved to your drafts' : 'Saved to drafts on this browser'));
      return sum;
    }, function (e) {
      // A draft deleted elsewhere since it was opened: save it as a new one.
      if (was && /not found/i.test(e.message)) { opts._current = null; opts._base = null; return save(); }
      // Changed on another device since it was opened: keep both.
      if (was && e.conflict) {
        delete body.baseUpdatedAt;
        body.title = title + ' (copy)';
        return backend.save(null, body).then(function (sum) {
          opts._current = sum.id;
          opts._base = sum.updatedAt || null;
          opts.toast('This draft changed on another device, so yours was saved as a copy.');
          return sum;
        }, function (e2) { opts.toast(e2.message); return null; });
      }
      opts.toast(e.message);
      return null;
    });
  }

  /* THE FIRST SAVE ASKS FOR A NAME (owner, after the menu: "Should save draft
     ask for a name?"). Saved under a date name straight away, Your drafts
     filled with names nobody could tell apart. So the first Save of a drawing
     that has no name and is not a draft yet drops the name box (lib/nametab.js),
     filled with the date name and selected: one tap on Save keeps it, typing
     replaces it. Every Save after that is quiet. Backing out leaves the
     drawing as unnamed as it was: the filled-in name goes with the box.
     A date name in the field is still no name (a reopened drawing brings its
     date name back as its title): the box asks with that one selected. */
  function nameField() { return doc.getElementById('skriblName'); }
  function asks() {
    var el = nameField();
    if (!el || opts._current || !global.SkriblName || !global.SkriblName.open) return false;
    var v = el.value.trim();
    return !v || (global.SkriblName.isAuto && global.SkriblName.isAuto(v));
  }
  function saveAsking() {
    if (!asks()) return save();
    // Refusals first, so the box never opens for a save that cannot happen.
    if (opts.busy && opts.busy()) { opts.toast('Preparing media \u2014 try again in a moment'); return Promise.resolve(null); }
    if (opts.hasContent && !opts.hasContent()) { opts.toast('Draw something to save'); return Promise.resolve(null); }
    return new Promise(function (resolve) {
      var el = nameField(), shell = doc.getElementById('nameShell');
      var filled = null, kept = false, seen = false, watch = null;
      global.SkriblName.open({ label: 'Save', onConfirm: function () { kept = true; save().then(resolve); } });
      setTimeout(function () {
        if (!el) return;
        if (!el.value) {
          filled = global.SkriblName.get();
          el.value = filled;
          el.dispatchEvent(new Event('input'));
        }
        // Selected: the box selects its text as it takes focus (nametab.js).
      }, 60);
      if (shell && global.MutationObserver) {
        watch = new MutationObserver(function () {
          var open = shell.classList.contains('open');
          if (open) { seen = true; return; }
          if (!seen) return;
          watch.disconnect();
          if (!kept && filled && el.value === filled) { el.value = ''; el.dispatchEvent(new Event('input')); }
          if (!kept) resolve(null);
        });
        watch.observe(shell, { attributes: true, attributeFilter: ['class'] });
      }
    });
  }

  /* ?draft=<id> on the way in: the other editor handed this one over. */
  function openFromUrl() {
    var id = null;
    try { id = new URLSearchParams(global.location.search).get('draft'); } catch (e) { return; }
    if (!id) return;
    try {
      var u = new URL(global.location.href);
      u.searchParams.delete('draft');
      global.history.replaceState(null, '', u.pathname + u.search + u.hash);
    } catch (e) {}
    backend.load(id).then(function (rec) {
      /* WORK ON THE CANVAS IS ASKED ABOUT, never replaced (v317). Opening a
         draft from the Library lands on an editor that may be holding its own
         autosaved drawing, and loading over it lost that drawing without a
         word. So the sheet opens with this draft's row already asking "Tap
         again -- this replaces...", the question the sheet always asks. */
      if (opts.hasContent && opts.hasContent()) {
        armOnRender = id;
        show(null);
        return;
      }
      opts.load(rec.payload);
      opts._current = id;
      opts._base = rec.updatedAt || null;
      if (global.SkriblName && rec.title) global.SkriblName.set(rec.title);
    }, function (e) { opts.toast(e.message); });
  }

  /* ---- a draft row's end (D3) ------------------------------------------ */
  /* THE SAME ⋯ AS A POSTED ROW (D3, the owner's pick A). A draft row ended in
     a bin while a posted row ended in a ⋯ on a phone and labelled buttons on
     a desk, so the two lists behaved differently. Now a phone's ⋯ opens Open
     in Pad (or Flip), Save a .skribl file, and Delete, last, under a line; a
     desk shows Save file and Delete, and the card itself opens the draft.
     Delete asks once, on itself, as a posted row's does: its word becomes the
     question and it turns red. The Library's Drafts tab and the editors' sheet
     end their rows here, so the two lists cannot drift apart again.

       rowEnd(row, it, { href | open(), remove() -> Promise, meta,
                         disarmers: [] })

     `meta` is the row's second line, made a live region: a passing answer
     (a file that could not be made, a refused delete) and a desk's Delete
     question are said there. `disarmers` is the list's, so only one row asks
     at a time. */
  var DOTS = '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="5" cy="12" r="1.9"/>'
    + '<circle cx="12" cy="12" r="1.9"/><circle cx="19" cy="12" r="1.9"/></svg>';
  function ico(paths) {
    return '<svg class="draft-ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" '
      + 'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + paths + '</svg>';
  }
  // The kinds' own marks (lib/postedui.js), the download arrow, the one bin.
  var MARK = {
    pad: '<path d="M17 3.5a2.1 2.1 0 0 1 3 3L8.5 18 4 20l2-4.5z"/>',
    flip: '<path d="M12 6.5C9.5 4.9 6.4 4.6 3 5.2v13c3.4-.6 6.5-.3 9 1.3 2.5-1.6 5.6-1.9 9-1.3v-13c-3.4-.6-6.5-.3-9 1.3z"/>'
        + '<path d="M12 6.5v13.3"/>'
  };
  var DOWN = '<path d="M12 3v12"/><path d="M7 10l5 5 5-5"/><path d="M5 21h14"/>';
  var BIN_D = '<path d="M3 6h18"/><path d="M8 6V4h8v2"/><path d="M19 6l-1 14H6L5 6"/><path d="M10 11v6M14 11v6"/>';

  // Delete's question is spoken as it is shown, through a live region (as the
  // posted rows' #postedStatus is), with no second line of words on screen.
  var live = null;
  function speak(words) {
    if (!live) {
      live = el('span', 'vis-hidden');
      live.setAttribute('role', 'status');
      live.setAttribute('aria-live', 'polite');
      doc.body.appendChild(live);
    }
    live.textContent = words;
  }

  // One row's menu is open at a time; a tap anywhere else or Escape shuts it,
  // and Escape hands focus back to its ⋯.
  var openRow = null;
  function rowMenu(row) {
    if (openRow && openRow !== row) {
      openRow.classList.remove('more-open', 'up');
      var was = openRow.querySelector('.draft-more');
      if (was) was.setAttribute('aria-expanded', 'false');
    }
    openRow = row || null;
    if (!row) return;
    row.classList.add('more-open');
    row.querySelector('.draft-more').setAttribute('aria-expanded', 'true');
    flip(row, row.querySelector('.draft-acts'));
    var first = row.querySelector('.draft-act');
    if (first) first.focus();
  }
  /* ABOVE ITS ⋯ WHERE THE SCREEN ENDS FIRST (the owner's phone: the last
     draft's menu opened under its row, past the screen's foot, with only Open
     in sight). The phone's menu hangs from its row (skribl_library.html);
     .up stands it on the row's top instead, when the screen ends below it
     and there is more room above. lib/postedui.js does the same for a posted
     row's menu, whose rules these share. */
  function flip(row, menu) {
    row.classList.remove('up');
    var q = menu && menu.getBoundingClientRect(), r = row.getBoundingClientRect();
    if (q && q.height && q.bottom > global.innerHeight - 8 && r.top > global.innerHeight - r.bottom) row.classList.add('up');
  }
  if (doc) {
    doc.addEventListener('pointerdown', function (e) {
      if (openRow && !openRow.contains(e.target)) rowMenu(null);
    }, true);
    doc.addEventListener('keydown', function (e) {
      if (e.key !== 'Escape' || !openRow || !openRow.contains(e.target)) return;
      e.stopPropagation();
      var row = openRow;
      rowMenu(null);
      row.querySelector('.draft-more').focus();
    }, true);
  }

  /* SAVE A .SKRIBL FILE without opening the draft (D3): the file the editor's
     Save as a file makes, which is what a draft holds. A Flip draft keeps an
     in-between page as its recipe, which only Flip can draw, so a Flip draft
     holding one says so rather than write a file nothing else could read. */
  function saveFile(it) {
    return backend.load(it.id).then(function (rec) {
      var data = rec && rec.payload;
      if (!data || typeof data !== 'object') throw new Error('Couldn’t read that draft.');
      if ((data.frames || []).some(function (f) { return f && f.gen; })) {
        throw new Error('Only Flip can save this one as a file: open it there.');
      }
      var title = data.title || rec.title || it.title || 'Untitled Skribl';
      var file = data.title ? data : Object.assign({}, data, { title: title });
      // A plain download, not JSON, as the editors' own (iPhone Safari named
      // a JSON blob "name.skribl.json" and showed it instead of saving it).
      var blob = new Blob([JSON.stringify(file)], { type: 'application/octet-stream' });
      var a = doc.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = global.SkriblName ? global.SkriblName.filename(title) : 'skribl.skribl';
      doc.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(function () { URL.revokeObjectURL(a.href); }, 4000);
      return true;
    });
  }

  function rowEnd(row, it, how) {
    var title = it.title || 'Untitled Skribl';
    var flip = it.kind === 'flip';
    row.classList.add('has-more');
    var more = el('button', 'draft-more');
    more.type = 'button';
    more.setAttribute('aria-expanded', 'false');
    more.setAttribute('aria-label', 'More for ' + title);
    more.innerHTML = DOTS;
    more.addEventListener('click', function () { rowMenu(row.classList.contains('more-open') ? null : row); });
    var acts = el('span', 'draft-acts');
    // Open is said in the phone's menu; on a desk the card itself opens it.
    var go = el(how.href ? 'a' : 'button', 'draft-act draft-go');
    if (how.href) go.href = how.href;
    else { go.type = 'button'; go.addEventListener('click', function () { rowMenu(null); how.open(); }); }
    go.innerHTML = ico(flip ? MARK.flip : MARK.pad) + '<span class="draft-lbl">Open in ' + (flip ? 'Flip' : 'Pad') + '</span>';
    var file = el('button', 'draft-act draft-file');
    file.type = 'button';
    file.setAttribute('aria-label', 'Save ' + title + ' as a .skribl file');
    file.innerHTML = ico(DOWN) + '<span class="draft-lbl">Save<span class="draft-long"> a .skribl</span> file</span>';
    var meta = how.meta || null, metaText = meta ? meta.textContent : '', sayT = null;
    if (meta) meta.setAttribute('aria-live', 'polite');
    function say(words) {
      if (!meta) return;
      clearTimeout(sayT);
      meta.classList.remove('asks');
      meta.textContent = words;
      sayT = setTimeout(function () { meta.textContent = metaText; }, 8000);
    }
    file.addEventListener('click', function () {
      file.disabled = true;
      saveFile(it).then(function () { file.disabled = false; rowMenu(null); },
        function (e) { file.disabled = false; rowMenu(null); say(e.message); });
    });
    var del = el('button', 'draft-act draft-del');
    del.type = 'button';
    del.setAttribute('aria-label', 'Delete ' + title);
    del.innerHTML = ico(BIN_D) + '<span class="draft-lbl">Delete</span>';
    var word = del.querySelector('.draft-lbl');
    /* ASKED ONCE, AND IT HOLDS UNTIL THE PERSON LEAVES IT (the rule the
       posted rows' Delete and the editors' New Skribl follow): focus leaving
       it, a tap anywhere else, or a 20 s safety net puts it back.
       AND THE ARM NEVER MOVES (the v317 bin rule). In the phone's menu the
       button is the menu's width, so its word becomes the question; on a
       desk a longer word would push Save file aside, under the next click, so
       the button keeps its word and its box and turns red, and the row's
       second line asks. */
    var armed = false, armT = null;
    function outside(e) { if (!del.contains(e.target)) disarm(); }
    function disarm() {
      if (!armed) return;
      armed = false;
      clearTimeout(armT);
      doc.removeEventListener('pointerdown', outside, true);
      del.classList.remove('armed');
      word.textContent = 'Delete';
      del.setAttribute('aria-label', 'Delete ' + title);
      if (meta && meta.classList.contains('asks')) { meta.classList.remove('asks'); meta.textContent = metaText; }
    }
    if (how.disarmers) how.disarmers.push(disarm);
    del.addEventListener('focusout', disarm);
    del.addEventListener('click', function () {
      if (!armed) {
        if (how.disarmers) how.disarmers.forEach(function (d) { if (d !== disarm) d(); });
        armed = true;
        del.classList.add('armed');
        del.setAttribute('aria-label', 'Tap again to delete ' + title);
        if (row.classList.contains('more-open') || !meta) {
          word.textContent = 'Tap again to delete';
          speak('Tap again to delete ' + title);
        } else {
          clearTimeout(sayT);
          meta.classList.add('asks');
          meta.textContent = 'Tap Delete again to delete it';   // a live region: said as shown
        }
        armT = setTimeout(disarm, 20000);
        doc.addEventListener('pointerdown', outside, true);
        return;
      }
      disarm();
      // Asked first: the caller reads where focus is, and a disabled button drops it.
      var done = how.remove();
      del.disabled = true;
      Promise.resolve(done).then(function (ok) { if (ok === false) del.disabled = false; },
        function (e) { del.disabled = false; say(e.message); });
    });
    acts.appendChild(go);
    acts.appendChild(file);
    acts.appendChild(del);
    row.appendChild(more);
    row.appendChild(acts);
    return acts;
  }

  global.SkriblSavedDrafts = {
    /* opts: {kind, serialize(), load(obj), hasContent(), busy() -> media still
              being read, thumbnail() -> canvas, otherUrl() -> the other
              editor's menu link, toast(msg)} */
    init: function (o) {
      opts = o;
      opts._current = null;
      var saveBtn = doc.getElementById('saveCloudDraftItem');
      var openBtn = doc.getElementById('openCloudDraftItem');
      if (saveBtn) saveBtn.addEventListener('click', function () { if (opts.closeMenu) opts.closeMenu(); saveAsking(); });
      if (openBtn) openBtn.addEventListener('click', function () { if (opts.closeMenu) opts.closeMenu(); show(openBtn); });
      openFromUrl();
      return this;
    },
    save: save,
    saveAsking: saveAsking,   // the menu's Save: asks for a name the first time
    open: show,
    close: hide,
    /* New Skribl: whatever is drawn next is a new draft, not the old one. */
    // forget() hands back the draft it let go of, so an Undo can resume() it
    // and the next Save updates that draft instead of making a copy (v317).
    forget: function () {
      var was = opts ? opts._current : null;
      if (opts) { opts._forgotBase = opts._base; opts._current = null; opts._base = null; }
      return was;
    },
    resume: function (id) { if (opts && id) { opts._current = id; opts._base = opts._forgotBase || null; } },
    current: function () { return opts ? opts._current : null; },
    where: function () { return backend.where; },
    /* For a page that lists drafts without editing one (the Library's Drafts
       tab, v317): the same storage the sheet reads, so the two cannot differ. */
    list: function () { return backend.list(); },
    // The Library shows the same note the sheet does (lib/draftstore.js's shelf).
    stalled: function () { return stalled() ? STALLED : ''; },
    remove: function (id) { return backend.remove(id); },
    /* A drawing this tab is NOT holding becomes a new draft as it is: another
       tab's autosave, kept for later (lib/othertab.js). No thumbnail: there is
       no canvas showing it to take one from. Resolves true once it is kept. */
    keep: function (kind, title, payload) {
      return backend.save(null, { kind: kind, title: title || 'Untitled Skribl', payload: payload, thumbnail: null })
        .then(function () { return true; });
    },
    /* The drawing on screen becomes a new draft, made as Save draft makes one
       (its name, its picture, its media), never written over the draft it was
       opened from: "Open it" keeps it before another tab's drawing opens in
       its place (lib/othertab.js, D2). Resolves true once it is kept; false
       while media is still being read, and the drawing is kept another way. */
    keepShown: function () {
      if (!opts || (opts.busy && opts.busy())) return Promise.resolve(false);
      var payload;
      try { payload = opts.serialize(); } catch (e) { return Promise.resolve(false); }
      var title = (global.SkriblName && global.SkriblName.get()) || 'Untitled Skribl';
      return backend.save(null, { kind: opts.kind, title: title, payload: payload, thumbnail: thumbFrom(opts.thumbnail && opts.thumbnail()) })
        .then(function () { return true; });
    },
    rowEnd: rowEnd,
    saveFile: saveFile,
    ago: ago
  };
})(window);
