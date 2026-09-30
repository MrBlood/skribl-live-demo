/* The file rows of the Photo and Music drawers -- the drop area until a file
 * is added, then the file itself and its bin -- with the "re-add your file"
 * cards and the tab dots that hint media is waiting: one implementation for
 * both editors.
 *
 * The cards and dots came first (SK312-003, v315; refreshPendingCards was 0.76
 * alike in app.js and flip.js). The file row joined them in the drawer
 * redesign: it is the element the card stands in for, in the same two
 * drawers, and this file already owned their DOM -- so no new module, and the
 * row's m:ss and Fill / Fit / Stretch words are the card's own.
 *
 * A draft keeps a track's or photo's SETTINGS but not always its bytes; when
 * the bytes are gone the card names the file and says what was kept, so the
 * person can re-add it and have the loop and adjustments come back.
 *
 * render({music: {meta, loaded, has}, photo: {meta, loaded, has}}):
 *   meta    the pending settings, or null when nothing is waiting
 *   loaded  the editor already holds this medium (a card would be a lie)
 *   has     the tab dot should show as "has media" once nothing is pending
 * Each editor keeps its own state and hands it in; this file owns the DOM.
 *
 * THE DOT'S hidden IS RESTORED, not just its class. Dropping only 'pending'
 * left a visible dot in the "has media" green claiming media the session did
 * not have (v294 bug check, found on both editors separately).
 *
 * Editors only: the player has no drawers.
 */
(function (global) {
  'use strict';

  function $(id) { return document.getElementById(id); }
  function fmt(sec) {
    var m = Math.floor(sec / 60), s = Math.floor(sec % 60);
    return m + ':' + String(s).padStart(2, '0');
  }
  var FIT = { cover: 'Fill', contain: 'Fit', fill: 'Stretch', stretch: 'Stretch' };

  function musicMeta(m) {
    if (m.trimStart == null || m.trimEnd == null) return 'Loop saved';
    return 'Loop ' + fmt(m.trimStart) + '–' + fmt(m.trimEnd) + ' · '
      + (m.trimEnd - m.trimStart).toFixed(1) + 's';
  }
  function photoMeta(p) {
    var parts = [];
    if (p.fit) parts.push(FIT[p.fit] || p.fit);
    if (p.opacity != null) parts.push(Math.round(p.opacity * 100) + '% opacity');
    if (p.blur) parts.push(p.blur + 'px blur');
    if (p.zoom && p.zoom !== 1) parts.push(Math.round(p.zoom * 100) + '% zoom');
    return parts.length ? parts.join(' · ') : 'Adjustments saved';
  }

  function one(kind, st, fallbackName, describe) {
    var card = $(kind + 'Pending');
    if (!card) return;
    var up = $(kind + 'UploadBtn'), dot = $(kind + 'TabDot');
    if (st.meta && !st.loaded) {
      var name = $(kind + 'PendingName'), meta = $(kind + 'PendingMeta');
      if (name) name.textContent = st.meta.name || fallbackName;
      if (meta) meta.textContent = describe(st.meta);
      card.hidden = false;
      if (up) up.hidden = true;
      if (dot) { dot.hidden = false; dot.classList.add('pending'); }
    } else {
      card.hidden = true;
      if (up) up.hidden = false;
      if (dot) { dot.classList.remove('pending'); dot.hidden = !st.has; }
    }
  }

  function render(s) {
    one('music', s.music, 'Your track', musicMeta);
    one('photo', s.photo, 'Your image', photoMeta);
  }

  /* ---- THE FILE ROW --------------------------------------------------------
   * #photoUploadBtn / #musicUploadBtn is ONE element with two faces. Its
   * .loaded class -- which each editor already sets when it holds the file --
   * is the only thing that says which; CSS draws the face, and nothing here
   * takes a second opinion about "loaded", so the words and the class cannot
   * disagree. The empty face is static markup (.dz-add). The loaded face is
   * written here:
   *
   * renderRow(kind, { name, src, fit, dur, on })
   *   name  the file's name ('Photo from draft' / 'Music from draft' when a
   *         restored draft saved none -- the Pad's words, now both editors')
   *   src   photo only: the picture, for the thumbnail
   *   fit   photo only: 'cover' | 'contain' | 'fill' | 'stretch'
   *   dur   music only: the track's length in seconds, shown only when it is
   *         a real number (an element's duration can be Infinity or NaN)
   *   on    the on/off switch. Off reads "Hidden · Fit" / "Muted · 0:08", so
   *         the words never contradict the switch beside them.
   * Each editor calls it after every change it makes to the row's state.
   */
  var FALLBACK = { photo: 'Photo from draft', music: 'Music from draft' };
  var lastIn = { photo: null, music: null };   // the row's control that last had focus
  var arms = {};                               // kind -> disarm()

  function rowMeta(kind, st) {
    var on = st.on !== false;
    if (kind === 'photo') {
      return (on ? 'Behind the drawing' : 'Hidden') + ' · ' + (FIT[st.fit] || 'Fill');
    }
    var d = st.dur, t = (typeof d === 'number' && isFinite(d) && d > 0) ? fmt(d) : '';
    return (on ? 'Loops under the drawing' : 'Muted') + (t ? ' · ' + t : '');
  }

  function renderRow(kind, st) {
    var zone = $(kind + 'UploadBtn');
    if (!zone) return;
    st = st || {};
    var loaded = zone.classList.contains('loaded');
    var name = $(kind + 'BtnLabel'), meta = $(kind + 'BtnMeta'), thumb = $(kind + 'Thumb');
    if (name) name.textContent = loaded ? (st.name || FALLBACK[kind]) : '';
    if (meta) meta.textContent = loaded ? rowMeta(kind, st) : '';
    if (thumb) {
      if (loaded && st.src) { if (thumb.getAttribute('src') !== st.src) thumb.setAttribute('src', st.src); }
      else thumb.removeAttribute('src');
    }
    if (!loaded && arms[kind]) arms[kind]();
    handFocus(kind, loaded);
  }

  /* FOCUS IS HANDED ON, NOT DROPPED. Each face hides the control that was
   * just used: attaching a file hides the add button, removing it hides the
   * bin. A hidden element gives focus to <body>, which leaves a keyboard user
   * outside the drawer altogether (the saved-drafts bin moves focus for the
   * same reason, lib/savedrafts.js). So the add button hands on to the switch,
   * and the bin to the add button. `lastIn` covers a browser that has already
   * sent focus to <body> by the time the editor re-renders; a tap or a focus
   * anywhere else clears it, so a file that arrives later steals nothing. */
  function handFocus(kind, loaded) {
    var a = document.activeElement, lost = !a || a === document.body;
    var add = $(kind + 'AddBtn'), bin = $(kind + 'Remove'), sw = $(kind + 'Toggle');
    var from = (a && (a === add || a === bin)) ? a : (lost ? lastIn[kind] : null);
    if (loaded && from && from === add && sw) { lastIn[kind] = null; sw.focus(); }
    else if (!loaded && from && from === bin && add) { lastIn[kind] = null; add.focus(); }
  }

  /* THE BIN ASKS FIRST, as the saved-drafts bin does (lib/savedrafts.js): one
   * tap on an icon that removes a file -- and on the Pad deletes its stored
   * bytes -- is a warning nobody read (DECISIONS v310). The first tap arms it:
   * the icon turns the danger colour in its own 36px box, the row's subtitle
   * asks "Tap the bin again to remove" (.dz-ask, drawn by CSS off .armed), its
   * name becomes "Tap again to remove <file>", and #confirmStatus says so
   * aloud. Nothing moves: a bin that widened into a "Remove?" pill grew over
   * the switch, and the next tap aimed at the switch removed the file. The second tap is the
   * editor's own Remove, untouched. It disarms when focus or a tap goes
   * anywhere else, when the row empties, and on a long safety net -- never a
   * race against a short timer (SK-AUD-018).
   *
   * A CAPTURE listener on the row, so the arming tap never reaches the
   * editors' Remove handlers and neither editor's Remove had to change.
   * removeNow(kind) is the one way past the question, for a caller that has
   * already asked it (the Pad's "New Skribl", which arms itself). */
  var ARM_MS = 20000;
  var bypass = false;
  function announce(text) {
    var st = $('confirmStatus');
    if (st) { st.textContent = ''; st.textContent = text; }
  }
  function wireBin(kind) {
    var zone = $(kind + 'UploadBtn'), bin = $(kind + 'Remove');
    if (!zone || !bin || arms[kind]) return;
    var label = bin.getAttribute('aria-label') || '', armed = false, timer = null;
    function outside(e) { if (!bin.contains(e.target)) disarm(); }
    function disarm() {
      if (!armed) return;
      armed = false;
      clearTimeout(timer);
      bin.classList.remove('armed');
      bin.setAttribute('aria-label', label);
      document.removeEventListener('pointerdown', outside, true);
    }
    arms[kind] = disarm;
    bin.addEventListener('focusout', disarm);
    zone.addEventListener('click', function (e) {
      if (!bin.contains(e.target)) return;
      if (bypass || armed) { disarm(); return; }   // on to the editor's Remove
      e.stopPropagation();
      e.preventDefault();
      armed = true;
      var n = ($(kind + 'BtnLabel') || {}).textContent || (kind === 'photo' ? 'the photo' : 'the track');
      var say = 'Tap again to remove ' + n;
      bin.classList.add('armed');
      bin.setAttribute('aria-label', say);
      announce(say);
      timer = setTimeout(disarm, ARM_MS);
      document.addEventListener('pointerdown', outside, true);
    }, true);
  }
  function removeNow(kind) {
    var bin = $(kind + 'Remove');
    if (!bin) return;
    bypass = true;
    try { bin.click(); } finally { bypass = false; }
  }

  /* A FILE DROPPED ANYWHERE ON THE CARD goes to the open drawer. The empty
   * row says "or drop one here", and a drop that missed it by a few pixels --
   * onto the tabs, the card's edge, or the re-add card that stands in for the
   * row -- opened the file in the tab and took the drawing with it. So the
   * card takes the drop, checks it against the same types the picker offers,
   * and hands it to the editor's own file input, whose change handler does
   * the rest (decode check, a waiting re-add's settings, storage). A row that
   * already holds a file does not take a drop, as it does not take a tap --
   * but it SAYS so: the page has already accepted the drag (the copy cursor),
   * and a drop that then does nothing reads as broken. The highlight is
   * the row's, and it does not flicker as the pointer crosses the row's own
   * children: a dragleave into something still inside the card is no leave.
   *
   * bindDrops({ card, current() -> 'photo' | 'music' | null,
   *             inputs: { photo: id, music: id }, say(message, anchor) }) */
  function refusal(kind, file) {
    var M = global.SkriblMedia;
    if (!M) return null;
    if (kind === 'photo') return M.isImageFile(file) ? null : 'Please drop an image file — jpg, png, gif, or webp';
    return M.validateAudioFile(file);
  }
  function bindDrops(o) {
    var card = $(o.card);
    if (!card || card.hasAttribute('data-drops')) return;
    card.setAttribute('data-drops', '');
    function open() {
      var k = o.current ? o.current() : null;
      return (k === 'photo' || k === 'music') ? k : null;
    }
    function clear() {
      ['photo', 'music'].forEach(function (k) { var z = $(k + 'UploadBtn'); if (z) z.classList.remove('drag-over'); });
    }
    card.addEventListener('dragover', function (e) {
      e.preventDefault();
      var k = open(), z = k && $(k + 'UploadBtn');
      if (z && !z.hidden && !z.classList.contains('loaded')) z.classList.add('drag-over');
    });
    card.addEventListener('dragleave', function (e) {
      if (e.relatedTarget && card.contains(e.relatedTarget)) return;
      clear();
    });
    card.addEventListener('drop', function (e) {
      e.preventDefault();
      clear();
      var k = open();
      var file = e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0];
      if (!k || !file) return;
      var zone = $(k + 'UploadBtn');
      if (zone && zone.classList.contains('loaded')) {
        if (o.say) o.say(k === 'photo' ? 'Remove the photo first to add another' : 'Remove the track first to add another', zone);
        return;
      }
      var why = refusal(k, file);
      if (why) { if (o.say) o.say(why, zone && !zone.hidden ? zone : card); return; }
      var input = $(o.inputs[k]);
      if (!input) return;
      var dt = new DataTransfer();
      dt.items.add(file);
      input.files = dt.files;
      input.dispatchEvent(new Event('change', { bubbles: true }));
    });
  }

  ['photo', 'music'].forEach(function (kind) {
    wireBin(kind);
    var zone = $(kind + 'UploadBtn');
    if (zone) zone.addEventListener('focusin', function (e) { lastIn[kind] = e.target; });
  });
  function forget(e) {
    ['photo', 'music'].forEach(function (kind) {
      var zone = $(kind + 'UploadBtn');
      if (zone && !zone.contains(e.target)) lastIn[kind] = null;
    });
  }
  document.addEventListener('focusin', forget);
  document.addEventListener('pointerdown', forget, true);

  global.SkriblPendingCards = { render: render, renderRow: renderRow, removeNow: removeNow, bindDrops: bindDrops };
})(window);
