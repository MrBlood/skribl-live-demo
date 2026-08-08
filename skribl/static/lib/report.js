/* "Report a problem" — the context, collected once, for both editors.
 *
 * WHY IT EXISTS. There is no error reporting anywhere in Skribl. During a test
 * you find out about problems by being told, and "it didn't work" is not
 * actionable. Every question asked of a tester this session — what version,
 * what browser, what canvas, how many pages, did a draft restore — is
 * answerable by the page itself.
 *
 * IT SENDS NOTHING. There is no endpoint, and adding one would mean an
 * unauthenticated write path, storage, and someone reading it. This puts the
 * details on the clipboard so a tester can paste them into whatever they were
 * already going to message you on. Honest about that in the UI: a button
 * labelled "Send" that only copies would be a lie.
 *
 * PRIVACY. Titles, captions, drawings and audio are deliberately NOT included.
 * A bug report should not quietly carry someone's unpublished work, and the
 * shape of the problem is in the counts, not the content.
 */
(function (global) {
  'use strict';

  function safe(fn, fallback) {
    try {
      var v = fn();
      return (v === undefined || v === null) ? fallback : v;
    } catch (e) {
      return fallback;
    }
  }

  /* Reads a top-level `let`/`const` from the editor scripts.
   *
   * `window.NAME` DOES NOT WORK for these, and worse, it silently returns the
   * wrong thing. Top-level `let` never becomes a window property, so
   * `window.CW` is undefined — while `window.frames` is the browser's built-in
   * frame collection and `window.fps` is the element with id="fps", because
   * ids become window properties. The first version of this collector reported
   * "fps: [object HTMLSpanElement]" and no page count at all.
   *
   * Classic scripts share one global lexical scope, so a BARE identifier
   * resolves to the editor's variable. Evaluated through a Function so an
   * undeclared name throws into safe() instead of aborting the collector.
   */
  function lex(name) {
    return safe(function () { return Function('return typeof ' + name +
      " === 'undefined' ? null : " + name)(); }, null);
  }

  function num(v) {
    return (typeof v === 'number' && isFinite(v)) ? v : null;
  }

  function collect() {
    var mode = safe(function () { return global.SKRIBL_MODE; }, 'unknown');
    // The version is rendered into the menu footer from SKRIBL_VERSION, not
    // injected as a global — read it back from the DOM rather than invent one.
    var version = safe(function () {
      var el = document.querySelector('.menu-version');
      return el ? el.textContent.trim() : null;
    }, null);
    var lines = [
      version || 'Skribl (unknown version)',
      'Surface: ' + mode,
      'Page: ' + safe(function () { return location.pathname; }, '?'),
      'Browser: ' + safe(function () { return navigator.userAgent; }, '?'),
      'Screen: ' + safe(function () { return global.innerWidth + 'x' + global.innerHeight; }, '?')
        + ' @ ' + safe(function () { return global.devicePixelRatio || 1; }, 1) + 'x'
    ];

    // Flip and Pad expose different globals; ask for what each one has and skip
    // the rest rather than reporting a misleading zero.
    var cw = num(lex('CW')), ch = num(lex('CH'));
    if (cw && ch) lines.push('Canvas: ' + Math.round(cw) + 'x' + Math.round(ch));
    var aw = num(lex('authoredW')), ah = num(lex('authoredH'));
    if (aw && ah) lines.push('Canvas: ' + Math.round(aw) + 'x' + Math.round(ah));

    var frameList = lex('frames');
    if (frameList && typeof frameList.length === 'number' && Array.isArray(frameList)) {
      lines.push('Pages: ' + frameList.length);
    }
    var rate = num(lex('fps'));
    if (rate) lines.push('fps: ' + rate);

    // Counts only — never the strokes themselves.
    var points = safe(function () {
      if (Array.isArray(frameList)) {
        return frameList.reduce(function (n, f) {
          return n + ((f && f.strokes && f.strokes.length) || 0);
        }, 0);
      }
      var flat = lex('strokes');
      return Array.isArray(flat) ? flat.length : null;
    }, null);
    if (points !== null) lines.push('Points: ' + points);

    lines.push('Has music: ' + !!(lex('musicData') || lex('musicBuffer')));
    lines.push('Has image: ' + !!lex('bgImage'));
    lines.push('Saved Skribls: ' + safe(function () {
      return global.SkriblPosted ? global.SkriblPosted.list().length : 0;
    }, 0));

    return lines.join('\n');
  }

  function init(opts) {
    opts = opts || {};
    var sheet = document.getElementById(opts.sheetId || 'reportSheet');
    var overlay = document.getElementById(opts.overlayId || 'reportOverlay');
    var body = document.getElementById('reportDetails');
    var copyBtn = document.getElementById('reportCopy');
    var closeBtn = document.getElementById('reportClose');
    var openers = [].slice.call(document.querySelectorAll('[data-skribl-report]'));
    if (!overlay || !body) return null;

    function open() {
      body.textContent = collect();
      overlay.hidden = false;
      overlay.classList.add('open');
    }
    function close() {
      overlay.hidden = true;
      overlay.classList.remove('open');
    }

    openers.forEach(function (b) {
      b.addEventListener('click', function (e) { e.preventDefault(); open(); });
    });
    if (closeBtn) closeBtn.addEventListener('click', close);
    overlay.addEventListener('click', function (e) { if (e.target === overlay) close(); });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && !overlay.hidden) close();
    });

    if (copyBtn) {
      copyBtn.addEventListener('click', function () {
        var text = body.textContent;
        var done = function () {
          copyBtn.textContent = 'Copied';
          clearTimeout(copyBtn._t);
          copyBtn._t = setTimeout(function () { copyBtn.textContent = 'Copy details'; }, 1600);
        };
        // navigator.clipboard needs a secure context and can reject; the
        // selection fallback is what makes this work on a plain-http test box.
        if (navigator.clipboard && navigator.clipboard.writeText) {
          navigator.clipboard.writeText(text).then(done, function () { selectFallback(); });
        } else {
          selectFallback();
        }
        function selectFallback() {
          var r = document.createRange();
          r.selectNodeContents(body);
          var sel = global.getSelection();
          sel.removeAllRanges();
          sel.addRange(r);
          try { document.execCommand('copy'); done(); }
          catch (e) { copyBtn.textContent = 'Select and copy'; }
        }
      });
    }

    return { open: open, close: close, collect: collect };
  }

  global.SkriblReport = { init: init, collect: collect };
})(window);
