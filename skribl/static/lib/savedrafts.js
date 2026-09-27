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
 * The editors and the Library load it; the Library only lists and deletes
 * (list/remove/ago) and never calls init(), so open() does nothing there.
 * The player never saves anything (verify_player_isolation).
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
      throw new Error(d.error || ('The drafts service answered ' + r.status + '.'));
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
     record the index does not name and writes it back in. */
  function recover(items) {
    if (!store().keys) return Promise.resolve(items);
    return store().keys().then(function (ks) {
      var known = {};
      items.forEach(function (i) { known['saved:' + i.id] = true; });
      var lost = ks.filter(function (k) {
        return typeof k === 'string' && k.indexOf('saved:') === 0 && k !== IDX && !known[k];
      });
      if (!lost.length) return items;
      return Promise.all(lost.map(function (k) {
        return store().get(k).catch(function () { return null; });
      })).then(function (recs) {
        var back = recs.filter(function (r) { return r && r.id && r.payload; }).map(function (r) {
          return { id: r.id, kind: r.kind === 'flip' ? 'flip' : 'pad', title: r.title || 'Untitled Skribl',
                   thumbnail: r.thumbnail || null, createdAt: r.savedAt || null, updatedAt: r.savedAt || null };
        });
        if (!back.length) return items;
        var all = items.concat(back);
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
    remove: function (id) {
      return readIndex().then(function (items) {
        return store().put(IDX, { items: items.filter(function (i) { return i.id !== id; }) });
      }).then(function () { return store().del('saved:' + id); });
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
  var sheet = null, scrim = null, listEl = null, opts = null, opener = null;
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
    close.textContent = '\u2715';
    close.addEventListener('click', hide);
    head.appendChild(h);
    head.appendChild(close);
    var sub = el('p', 'sdrafts-sub', backend.where === 'account'
      ? 'Saved to your account, on every device you sign in on.'
      : 'Saved on this browser only.');
    listEl = el('div', 'sdrafts-list');
    sheet.appendChild(head);
    sheet.appendChild(sub);
    sheet.appendChild(listEl);
    doc.body.appendChild(scrim);
    doc.body.appendChild(sheet);
    scrim.addEventListener('click', hide);
    sheet.addEventListener('keydown', function (e) { if (e.key === 'Escape') { e.stopPropagation(); hide(); } });
  }

  function hide() {
    if (!sheet || sheet.hidden) return;
    sheet.hidden = true;
    scrim.hidden = true;
    if (global.SkriblModal) global.SkriblModal.close(sheet);
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

  function render(items) {
    listEl.textContent = '';
    disarmers = [];
    if (!items.length) {
      listEl.appendChild(el('p', 'sdrafts-empty',
        'No saved drafts yet. Save one from \u22EF \u2192 Save draft.'));
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
      del.setAttribute('aria-label', 'Delete ' + (it.title || 'this draft'));
      del.innerHTML = BIN;
      var armedOpen = false, armedDel = false, metaText = meta.textContent;
      function disarm() {
        armedOpen = false; armedDel = false;
        meta.textContent = metaText;
        row.classList.remove('armed');
        del.classList.remove('armed');
        del.innerHTML = BIN;
      }
      disarmers.push(disarm);
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
          del.textContent = 'Delete?';
          del.classList.add('armed');
          return;
        }
        backend.remove(it.id).then(function () {
          if (opts._current === it.id) opts._current = null;
          refresh();
        }, function (e) { opts.toast(e.message); });
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
  }

  function refresh() {
    listEl.textContent = '';
    listEl.appendChild(el('p', 'sdrafts-empty', 'Loading\u2026'));
    return backend.list().then(render, function (e) {
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

  function show(from) {
    if (!opts) return;   // the sheet is an editor's; the Library lists drafts itself
    if (!sheet) build();
    opener = from || null;
    sheet.hidden = false;
    scrim.hidden = false;
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
      if (global.SkriblName && rec.title) global.SkriblName.set(rec.title);
      opts.toast('Opened \u201C' + (rec.title || 'Untitled Skribl') + '\u201D');
    }, function (e) { opts.toast(e.message); });
  }

  function save() {
    if (opts.hasContent && !opts.hasContent()) { opts.toast('Draw something to save'); return Promise.resolve(null); }
    var payload;
    try { payload = opts.serialize(); } catch (e) { opts.toast('Could not read the drawing to save it.'); return Promise.resolve(null); }
    var title = (global.SkriblName && global.SkriblName.get()) || 'Untitled Skribl';
    var body = { kind: opts.kind, title: title, payload: payload, thumbnail: thumbFrom(opts.thumbnail && opts.thumbnail()) };
    var was = opts._current;
    return backend.save(was, body).then(function (sum) {
      opts._current = sum.id;
      opts.toast(was ? 'Draft updated' : (backend.where === 'account' ? 'Saved to your drafts' : 'Saved to drafts on this browser'));
      return sum;
    }, function (e) {
      // A draft deleted elsewhere since it was opened: save it as a new one.
      if (was && /not found/i.test(e.message)) { opts._current = null; return save(); }
      opts.toast(e.message);
      return null;
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
      if (global.SkriblName && rec.title) global.SkriblName.set(rec.title);
    }, function (e) { opts.toast(e.message); });
  }

  global.SkriblSavedDrafts = {
    /* opts: {kind, serialize(), load(obj), hasContent(), thumbnail() -> canvas,
              otherUrl() -> the other editor's menu link, toast(msg)} */
    init: function (o) {
      opts = o;
      opts._current = null;
      var saveBtn = doc.getElementById('saveCloudDraftItem');
      var openBtn = doc.getElementById('openCloudDraftItem');
      if (saveBtn) saveBtn.addEventListener('click', function () { if (opts.closeMenu) opts.closeMenu(); save(); });
      if (openBtn) openBtn.addEventListener('click', function () { if (opts.closeMenu) opts.closeMenu(); show(openBtn); });
      openFromUrl();
      return this;
    },
    save: save,
    open: show,
    close: hide,
    /* New Skribl: whatever is drawn next is a new draft, not the old one. */
    forget: function () { if (opts) opts._current = null; },
    current: function () { return opts ? opts._current : null; },
    where: function () { return backend.where; },
    /* For a page that lists drafts without editing one (the Library's Drafts
       tab, v317): the same storage the sheet reads, so the two cannot differ. */
    list: function () { return backend.list(); },
    remove: function (id) { return backend.remove(id); },
    ago: ago
  };
})(window);
