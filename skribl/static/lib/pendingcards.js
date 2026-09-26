/* The "re-add your file" cards in the Image and Music drawers, and the tab
 * dots that hint media is waiting: one implementation for both editors
 * (SK312-003, v315; refreshPendingCards was 0.76 alike in app.js and flip.js).
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

  global.SkriblPendingCards = { render: render };
})(window);
