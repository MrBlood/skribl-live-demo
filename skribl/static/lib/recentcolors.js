/* Recent colours — the first controller shared by both editors.
 *
 * WHY THIS FILE EXISTS. app.js and flip.js each carried their own addRecent()
 * and renderRecent(). They agreed on the things anyone would check — a cap of
 * six, most-recent-first, de-duplication, the same localStorage key — and
 * disagreed on everything else:
 *
 *   - Pad validated /^#[0-9a-f]{6}$/ and lower-cased; Flip did neither, so
 *     '#AABBCC' and '#aabbcc' could both be stored and an unvalidated string
 *     rendered as a transparent swatch that set the pen to nothing.
 *   - Pad gave each swatch an aria-label; Flip set only title, which is not an
 *     accessible name and does nothing at all on a touch device.
 *
 * Neither divergence was deliberate. Both were invisible until the two files
 * were read side by side, which is the whole argument for this extraction:
 * every fix to a duplicated controller has to be made twice, and the second
 * one is the one that gets forgotten.
 *
 * WHAT IS DELIBERATELY NOT SHARED. What happens when a swatch is PICKED. Pad
 * sets the pen and leaves its bottom drawer open; Flip sets the pen and closes
 * its popover, which sits over the canvas and would otherwise cover the drawing
 * you are about to make. That is a real difference between the two surfaces,
 * so it is an injected callback rather than something this file decides.
 * Extract behaviour, not layout: Pad and Flip are meant to feel different.
 */
(function () {
  'use strict';

  var KEY = 'skribl_recent_colors';
  var LIMIT = 6;
  var HEX = /^#[0-9a-f]{6}$/;

  function normalise(hex) {
    hex = String(hex == null ? '' : hex).trim().toLowerCase();
    return HEX.test(hex) ? hex : null;
  }

  function load() {
    try {
      var raw = JSON.parse(localStorage.getItem(KEY) || '[]');
      if (!Array.isArray(raw)) return [];
      var out = [];
      for (var i = 0; i < raw.length; i++) {
        var c = normalise(raw[i]);
        // Filtered on the way IN as well as the way out: a list persisted by
        // an older build could contain mixed-case or invalid entries.
        if (c && out.indexOf(c) === -1) out.push(c);
      }
      return out.slice(0, LIMIT);
    } catch (e) {
      return [];
    }
  }

  function save(list) {
    try { localStorage.setItem(KEY, JSON.stringify(list)); } catch (e) {}
  }

  /* create({ wrap, row, onPick, onChange })
   *   wrap     element the swatches are rendered into
   *   row      element hidden when the list is empty (optional)
   *   onPick   called with a hex when a swatch is activated
   *   onChange called with the new list after every change, so a surface can
   *            keep its own `recentColors` identifier in step — several call
   *            sites in both editors read that variable directly.
   */
  function create(opts) {
    opts = opts || {};
    var wrap = opts.wrap || null;
    var row = opts.row || null;
    var onPick = typeof opts.onPick === 'function' ? opts.onPick : function () {};
    var onChange = typeof opts.onChange === 'function' ? opts.onChange : function () {};
    var list = load();

    function render() {
      if (!wrap) return;
      wrap.innerHTML = '';
      for (var i = 0; i < list.length; i++) {
        (function (hex) {
          var b = document.createElement('button');
          b.type = 'button';
          b.className = 'recent-swatch';
          b.style.background = hex;
          // Both, not either: the label is the accessible name, the title is
          // the pointer tooltip, and neither substitutes for the other.
          b.setAttribute('aria-label', 'Use colour ' + hex);
          b.title = hex;
          b.addEventListener('click', function () { onPick(hex); });
          wrap.appendChild(b);
        }(list[i]));
      }
      if (row) row.hidden = list.length === 0;
    }

    function add(hex) {
      var c = normalise(hex);
      if (!c) return false;          // say no rather than store a non-colour
      var next = [c];
      for (var i = 0; i < list.length; i++) {
        if (list[i] !== c) next.push(list[i]);
      }
      list = next.slice(0, LIMIT);
      save(list);
      render();
      onChange(list.slice());
      return true;
    }

    render();
    onChange(list.slice());

    return {
      add: add,
      render: render,
      list: function () { return list.slice(); },
      clear: function () { list = []; save(list); render(); onChange([]); }
    };
  }

  window.SkriblRecentColors = { create: create, LIMIT: LIMIT };
}());
