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

  function hide() {
    clearTimeout(timer);
    if (el) { el.classList.remove('in'); }
    // Wait out the fade before hiding, or it vanishes instead of fading.
    setTimeout(function () { if (el && !el.classList.contains('in')) el.hidden = true; }, 220);
  }

  /* key  - stable id; the hint shows once per key, forever
   * text - one or two clauses. Longer than that belongs in the help drawer. */
  function show(key, text) {
    if (!key || !text || !isEnabled()) return false;
    var s = seen();
    if (s[key]) return false;
    s[key] = 1;
    write(SEEN_KEY, JSON.stringify(s));

    var node = ensure();
    node.textContent = text;
    node.hidden = false;
    global.requestAnimationFrame(function () { node.classList.add('in'); });
    clearTimeout(timer);
    timer = setTimeout(hide, DURATION);
    // Dismissable: someone who has read it should not wait out the timer.
    node.onclick = hide;
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
