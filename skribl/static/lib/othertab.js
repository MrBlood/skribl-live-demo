/* TWO TABS, TWO DRAWINGS, NOTHING LOST (SK-AUD-006; the owner's pick T1).
 *
 * Both editors keep one autosave slot in localStorage. Two tabs of one editor
 * shared it and the last to write won: tab A draws, tab B draws, and A's
 * drawing was gone the moment A closed. v321 (PF-008) said so in the tab that
 * lost the slot and offered to take it back -- which still needed someone to
 * press a button before closing the tab.
 *
 * Now no save replaces another tab's drawing. The slot remembers who wrote it
 * (`<key>:owner`, { w: writer, at: time }). A tab about to write over a drawing
 * it neither wrote nor opened moves that drawing aside first, to
 * `<key>:waiting:<writer>`; a tab that writes the slot takes its own waiting
 * copy back. So the slot always holds the newest drawing, and every other
 * tab's newest drawing waits beside it.
 *
 * On the next visit the newest opens, as it always did, and a waiting drawing
 * is OFFERED in one line that says when it was left: "Open it" or "Keep for
 * later" (it goes to Drafts). Only a drawing no open tab is still holding: the
 * tabs answer a roll call on a BroadcastChannel first.
 *
 * ONE QUESTION, ANSWERED ONCE (D2, the owner's pick A). "Open it" used to put
 * this tab's drawing where the other had waited, so the reload asked the same
 * question about the drawing just left, and "Open it" again swapped them back,
 * forever. Now it keeps this tab's drawing in Drafts first, as Save draft makes
 * one, and after the reload one note says where it went. Only if Drafts can't
 * take it does it wait in the other's place, as before: nothing is lost either
 * way. And the editor's "Draft restored" waits until no question is showing;
 * said at boot, it sat on the question's words.
 *
 *   var slot = SkriblOtherTab.slot(key)
 *   slot.read()           the newest drawing (the slot's text), or null
 *   slot.write(text)      write this tab's drawing; moves another's aside.
 *                         Throws what localStorage throws (a full store).
 *   slot.remove()         this tab's drawing is finished (posted, cleared):
 *                         removes it, never another tab's
 *   slot.adopt()          this tab just opened the drawing in the slot, so it
 *                         may write over that one without moving it
 *   slot.offer({ later(text, at) -> Promise<bool>, current() -> text,
 *                keep() -> Promise<bool>, restored, note(words) })
 *                         after the editor has restored: offer what waits.
 *                         "Open it" keeps this tab's drawing in Drafts (keep();
 *                         if it can't, current() waits in the other's place),
 *                         makes the other the newest and reloads. note() is
 *                         the visit's one note, said once no question shows:
 *                         where "Open it" put the last drawing, or "Draft
 *                         restored" when the editor restored one.
 *   slot.frozen()         true once "Open it" has run: write nothing more
 *   slot.wouldMove()      a write now would move another tab's drawing aside
 *                         (a flush with nothing new skips it, or a tab closing
 *                         would make its older drawing the newest)
 *
 * Both editors call the same few; what differs is passed in -- how a drawing
 * becomes a draft, and what this tab is holding now.
 */
(function (global) {
  'use strict';
  var doc = global.document;
  function ls() { try { return global.localStorage; } catch (_) { return null; } }
  function ss() { try { return global.sessionStorage; } catch (_) { return null; } }

  // When a waiting drawing was left: its time today, its day before that.
  function when(at) {
    if (!at) return '';
    try {
      var d = new Date(at);
      var tm = d.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
      if (d.toDateString() === new Date().toDateString()) return ' at ' + tm;
      return ' on ' + d.toLocaleDateString([], { month: 'short', day: 'numeric' }) + ' at ' + tm;
    } catch (_) { return ''; }
  }

  function slot(key) {
    var me = Math.random().toString(36).slice(2) + Date.now().toString(36);
    var OWNER = key + ':owner';
    var WAIT = key + ':waiting:';
    var KEPT = key + ':kept';   // sessionStorage: "Open it" kept this tab's drawing in Drafts
    var adopted = null;   // the owner record of the drawing this tab opened
    var frozen = false;   // set by "Open it": this page is about to reload
    var alive = {};       // writers that answered the roll call
    var chan = null;
    try {
      chan = new global.BroadcastChannel('skribl-tabs:' + key);
      chan.onmessage = function (e) {
        var m = e.data || {};
        if (m.who) chan.postMessage({ here: me });
        if (m.here) alive[m.here] = true;
      };
    } catch (_) { chan = null; }

    function owner() {
      try { return JSON.parse(ls().getItem(OWNER) || 'null'); } catch (_) { return null; }
    }
    // A slot nobody signed (written before this, or empty) is anybody's.
    function mine(o) {
      return !o || !o.w || o.w === me || !!(adopted && o.w === adopted.w && o.at === adopted.at);
    }

    function write(text) {
      if (frozen) return;
      var s = ls();
      if (!s) throw new Error('no localStorage');
      var o = owner();
      var cur = s.getItem(key);
      if (cur && !mine(o)) {
        try {
          s.setItem(WAIT + o.w, JSON.stringify({ w: o.w, at: o.at, data: cur }));
        } catch (full) {
          // No room to move theirs: leave it in the slot and keep this tab's
          // drawing aside instead. Both survive, or the error says why.
          s.setItem(WAIT + me, JSON.stringify({ w: me, at: Date.now(), data: text }));
          return;
        }
      }
      s.setItem(key, text);
      try { s.setItem(OWNER, JSON.stringify({ w: me, at: Date.now() })); } catch (_) {}
      adopted = null;
      try { s.removeItem(WAIT + me); } catch (_) {}
    }

    function remove() {
      var s = ls();
      if (!s || frozen) return;
      try {
        if (mine(owner())) { s.removeItem(key); s.removeItem(OWNER); }
        s.removeItem(WAIT + me);
      } catch (_) {}
    }

    function adopt() { adopted = owner(); }
    // Would a write now move another tab's drawing aside? A tab closing with
    // nothing new must not: it would make its old drawing the newest.
    function wouldMove() {
      var s = ls();
      try { return !!(s && s.getItem(key) && !mine(owner())); } catch (_) { return false; }
    }

    function waiting() {
      var s = ls(), out = [];
      if (!s) return out;
      for (var i = 0; i < s.length; i++) {
        var k = s.key(i);
        if (!k || k.indexOf(WAIT) !== 0) continue;
        try {
          var rec = JSON.parse(s.getItem(k));
          if (rec && rec.data && rec.w !== me && !alive[rec.w]) out.push({ key: k, at: rec.at || 0, data: rec.data });
        } catch (_) {}
      }
      return out.sort(function (a, b) { return b.at - a.at; });
    }

    var bar = null;
    function hide() { if (bar) bar.hidden = true; }
    function offer(opts) {
      opts = opts || {};
      // The visit's one note: where "Open it" put the drawing this tab had
      // open (marked just before its reload), or else "Draft restored".
      var owed = null;
      try {
        var t = ss();
        if (t && t.getItem(KEPT)) { t.removeItem(KEPT); owed = 'The drawing you had open is in Drafts'; }
      } catch (_) {}
      if (!owed && opts.restored) owed = 'Draft restored';
      function say() { var w = owed; owed = null; if (w && opts.note) opts.note(w); }
      function go() {
        var list = waiting();
        if (!list.length) { hide(); say(); return; }
        var entry = list[0];
        if (!bar) {
          bar = doc.createElement('div');
          bar.className = 'othertab';
          bar.setAttribute('role', 'status');
          bar.setAttribute('aria-live', 'polite');
          bar.innerHTML = '<span class="othertab-words"></span>'
            + '<button type="button" class="othertab-open">Open it</button>'
            + '<button type="button" class="othertab-later">Keep for later</button>'
            + '<button type="button" class="othertab-x" aria-label="Not now">'
            + '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" '
            + 'stroke-linecap="round" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18"/></svg></button>';
          doc.body.appendChild(bar);
          bar.querySelector('.othertab-x').addEventListener('click', function () { hide(); say(); });
        }
        var words = bar.querySelector('.othertab-words');
        var openBtn = bar.querySelector('.othertab-open');
        var laterBtn = bar.querySelector('.othertab-later');
        words.textContent = 'Another drawing is waiting, from a different tab' + when(entry.at) + '.';
        /* OPENED THE WAY EVERY VISIT OPENS ONE. The other becomes the newest
           and the page reloads: the editor's own boot restore -- the tested
           path, media and all -- does the rest. Nothing is replaced until this
           tab's drawing is safe: in Drafts, or else (`aside`) waiting in the
           other's place. If there is no room for that, nothing is. */
        function swap(aside, kept) {
          var s = ls();
          var put = [];
          try {
            if (aside) {
              var id = 'kept-' + Date.now().toString(36);
              s.setItem(WAIT + id, JSON.stringify({ w: id, at: Date.now(), data: aside }));
              put.push(WAIT + id);
            }
            s.setItem(key, entry.data);
            s.setItem(OWNER, JSON.stringify({ w: 'opened-' + Date.now().toString(36), at: Date.now() }));
            s.removeItem(entry.key);
          } catch (_) {
            put.forEach(function (k) { try { s.removeItem(k); } catch (e) {} });
            words.textContent = 'There’s no room here to keep both. Keep it for later instead.';
            return;
          }
          if (kept) { try { ss().setItem(KEPT, '1'); } catch (_) {} }
          frozen = true;
          hide();
          (opts.open || function () { global.location.reload(); })();
        }
        openBtn.onclick = function () {
          var current = opts.current ? opts.current() : null;
          if (!current || !opts.keep) { swap(current, false); return; }
          laterBtn.disabled = openBtn.disabled = true;
          Promise.resolve().then(opts.keep).then(function (ok) { return !!ok; }, function () { return false; })
            .then(function (ok) {
              laterBtn.disabled = openBtn.disabled = false;
              swap(ok ? null : (opts.current() || current), ok);
            });
        };
        laterBtn.onclick = function () {
          laterBtn.disabled = openBtn.disabled = true;
          Promise.resolve(opts.later(entry.data, entry.at)).then(function (ok) {
            laterBtn.disabled = openBtn.disabled = false;
            if (!ok) return;   // not kept: it stays waiting, and the editor said why
            owed = null;       // the editor said where it went: that was the note
            try { ls().removeItem(entry.key); } catch (_) {}
            go();
          }, function () { laterBtn.disabled = openBtn.disabled = false; });
        };
        bar.hidden = false;
      }
      // Nothing waiting, nothing to ask: the note is said at once.
      if (!waiting().length) say();
      // The roll call: an open tab answers within a frame or two.
      if (chan) { chan.postMessage({ who: true }); setTimeout(go, 300); } else go();
    }

    return { id: me, read: function () { var s = ls(); return s ? s.getItem(key) : null; },
             write: write, remove: remove, adopt: adopt, offer: offer, waiting: waiting, hide: hide, wouldMove: wouldMove,
             frozen: function () { return frozen; } };
  }

  global.SkriblOtherTab = { slot: slot };
})(window);
