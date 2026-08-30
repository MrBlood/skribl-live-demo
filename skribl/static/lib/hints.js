/* First-use hints — one short toast the first time a control is used.
 *
 * WHY THESE AND NOT MORE TOOLTIPS. A tooltip answers "what is this button".
 * Some things need "and here is how you drive it", which is too long to hover
 * over and is only wanted once. Magnify is the example that prompted this: the
 * button zooms, but zooming to a PARTICULAR spot needs scroll or space-drag,
 * and that was documented only in the help drawer under a separate heading —
 * findable only if you already knew to look.
 *
 * SHOWN ONCE, EVER, PER HINT. A hint that reappears is an interruption. Seen
 * hints persist in localStorage, and the whole system has an off switch,
 * because someone who knows the app should not be taught it again.
 *
 * FAILS QUIET. If localStorage is unavailable — Safari private mode throws on
 * access, not just on write — hints simply show every time rather than the
 * editor breaking. A teaching aid must never be load-bearing.
 */
(function (global) {
  'use strict';

  var SEEN_KEY = 'skribl_hints_seen_v1';
  var OFF_KEY = 'skribl_hints_off_v1';
  var DURATION = 6200;    // long enough to read two clauses, not long enough to nag

  var el = null, timer = null;

  function read(key) {
    try { return global.localStorage.getItem(key); } catch (e) { return null; }
  }
  function write(key, val) {
    try { global.localStorage.setItem(key, val); return true; } catch (e) { return false; }
  }

  function seen() {
    var raw = read(SEEN_KEY);
    if (!raw) return {};
    try {
      var o = JSON.parse(raw);
      return (o && typeof o === 'object') ? o : {};
    } catch (e) { return {}; }
  }

  function isEnabled() { return read(OFF_KEY) !== '1'; }

  function setEnabled(on) {
    write(OFF_KEY, on ? '0' : '1');
    if (!on) hide();
    return on;
  }

  /* Forgetting what has been seen is what makes the toggle useful twice: turn
   * hints back on and you actually get them again, rather than a setting that
   * silently does nothing because every hint is already marked seen. */
  function reset() {
    write(SEEN_KEY, '{}');
    write(OFF_KEY, '0');
  }

  function ensure() {
    if (el) return el;
    el = document.createElement('div');
    el.className = 'skribl-hint';
    el.setAttribute('role', 'status');
    el.hidden = true;
    document.body.appendChild(el);
    return el;
  }

  /* Run when THIS hint goes away, whichever way it goes -- timer, tap, or a
     later hint replacing it. It exists so a caller can tie something visual to
     the toast's lifetime without duplicating the dwell arithmetic: the stamp
     spotlight used a hard-coded 6000 while an action hint dwells DURATION * 2,
     so the ring went out six seconds before the sentence explaining it did. */
  var onHide = null;
  function hide() {
    clearTimeout(timer);
    var cb = onHide; onHide = null;
    if (cb) { try { cb(); } catch (e) {} }
    if (el) { el.classList.remove('in'); }
    // Wait out the fade before hiding, or it vanishes instead of fading.
    setTimeout(function () { if (el && !el.classList.contains('in')) el.hidden = true; }, 220);
  }

  /* key  - stable id; the hint shows once per key, forever
   * text - one or two clauses. Longer than that belongs in the help drawer.
   * opts - optional { action: { label, onClick } }. An ACTION hint is a normal
   *        auto-dismissing toast that also carries a tappable link (e.g.
   *        "How it works ->") for anyone who wants the full explanation. It
   *        replaces the v205 "panel" variant, which was a large non-dismissing
   *        pointer-events:none box: the pointer vanished behind it, and its
   *        size/z-index made it easy to leave a dead zone over the toolbar.
   *        Small, timed, tap-to-dismiss, with an optional deeper link. */
  /* opts.onHide - called when this toast goes away, for anything that has to
   *        live exactly as long as it does.
   * opts.icon - raw SVG markup shown before the text, aria-hidden. Lift it from
   *        the control being described rather than drawing it again. */
  function show(key, text, opts) {
    if (!key || !text || !isEnabled()) return false;
    var s = seen();
    if (s[key]) return false;
    s[key] = 1;
    write(SEEN_KEY, JSON.stringify(s));

    var action = opts && opts.action;
    onHide = (opts && typeof opts.onHide === 'function') ? opts.onHide : null;
    var node = ensure();
    node.classList.remove('skribl-hint-panel');   // v205 variant, retired
    clearTimeout(timer);
    node.textContent = '';
    /* An optional glyph, shown BEFORE the text. It exists because a hint that
       says "the highlighted button" is describing something the reader still has
       to find: the ring narrows it down, and the picture settles it. Raw SVG
       markup, aria-hidden, so the sentence still reads correctly in speech --
       the caller lifts it from the real control rather than drawing a second
       copy, which is what keeps the two from ever disagreeing. */
    if (opts && opts.icon) {
      var ic = document.createElement('span');
      ic.className = 'skribl-hint-ic';
      ic.setAttribute('aria-hidden', 'true');
      ic.innerHTML = opts.icon;
      node.appendChild(ic);
    }
    var span = document.createElement('span');
    span.className = 'skribl-hint-text';
    span.textContent = text;
    node.appendChild(span);
    if (action && action.label && typeof action.onClick === 'function') {
      var a = document.createElement('button');
      a.type = 'button';
      a.className = 'skribl-hint-action';
      a.textContent = action.label;
      a.onclick = function (e) { e.stopPropagation(); hide(); action.onClick(); };
      node.appendChild(a);
    }
    node.onclick = hide;               // tap anywhere on the toast to dismiss
    node.hidden = false;
    global.requestAnimationFrame(function () { node.classList.add('in'); });
    // Longer dwell when there is an action to read + tap; still auto-dismisses.
    timer = setTimeout(hide, action ? DURATION * 2 : DURATION);
    return true;
  }

  /* Two tabs, one setting. The store is already shared between Pad and Flip —
   * a single key, not one per surface — so turning tips off in one place turns
   * them off everywhere. Without this listener the OTHER tab keeps showing the
   * old position until it is reopened, which looks like the switch not working.
   */
  global.addEventListener('storage', function (e) {
    if (e && (e.key === OFF_KEY || e.key === SEEN_KEY)) {
      if (typeof global._skriblSyncHintToggle === 'function') global._skriblSyncHintToggle();
    }
  });

  global.SkriblHints = {
    show: show, hide: hide, reset: reset,
    isEnabled: isEnabled, setEnabled: setEnabled
  };
})(window);
