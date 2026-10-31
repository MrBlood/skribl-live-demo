// Editor-only: the Pad's bar -- the pen swoosh and the Media button.
//
// The dock redesign made the pen button draw the stroke it will make
// (lib/penswoosh.js) and folded Image and Music into one Media button with
// Photo | Music tabs (lib/mediatabs.js). Both libs are editor furniture the
// player never loads, so the wiring lives here rather than in app.js, which
// every player downloads: verify_player_isolation's byte ratchet is the reason,
// and the same carve editor_tools.js, editor_music.js and editor_photo.js made.
//
// Loaded right after app.js. It declares the two functions app.js reaches by
// name -- paintPenSwoosh (updateCurrentColorChip) and syncMediaTabs (the photo
// and music drawer hooks) -- and reads the globals app.js declares: size,
// color, strokeOpacity, bgColor and _padDrawerCtl. It also hands the media
// card's file drops to the open drawer.

const _paintSwoosh = (window.SkriblPenSwoosh && window.SkriblPenSwoosh.wire)
  ? window.SkriblPenSwoosh.wire({
      canvas: 'penSwoosh', button: 'penToolBtn', range: 'brushSizeRange', scope: '#drawPanel, #toolBar',
      state: () => ({ brush: window.SkriblBrush ? window.SkriblBrush.name() : 'pen',
                      size: size, color: color, opacity: strokeOpacity, bg: bgColor })
    })
  : () => {};
// Every pen colour change comes through here (updateCurrentColorChip), so the
// Recolor bar's colour follows it from here too (lib/recolor.js sync).
function paintPenSwoosh() {
  _paintSwoosh();
  if (window.SkriblPadRecolor) window.SkriblPadRecolor.sync();
}

const _mediaTabs = (window.SkriblMediaTabs && _padDrawerCtl) ? window.SkriblMediaTabs.attach({
  ctl: _padDrawerCtl, button: 'mediaOpenBtn', strip: 'mediaTabs',
  dot: 'mediaTabDot', sources: ['photoTabDot', 'musicTabDot']
}) : null;
function syncMediaTabs(name) { if (_mediaTabs) _mediaTabs.sync(name); }
// A file dropped anywhere on the media card goes to the open drawer's input,
// once it is the right kind of file (lib/pendingcards.js bindDrops, which Flip
// calls too). The rows used to take drops themselves, and a drop that missed
// one opened the file in the tab.
if (window.SkriblPendingCards && window.SkriblPendingCards.bindDrops && _padDrawerCtl) {
  window.SkriblPendingCards.bindDrops({
    card: 'mediaCard', current: () => _padDrawerCtl.current(),
    inputs: { photo: 'photoInput', music: 'musicInput' },
    say: (msg, anchor) => showToast(msg, anchor)
  });
}
// The canvas re-fits when the header or the dock changes size, whether or not
// the window says so: a Page Zoom changed while Safari sat in the background
// arrived with no resize event, and the drawing kept its 150% size at 100%
// (owner, L3). lib/chromefit.js, the watch Flip has kept since #289.
if (window.SkriblChromeFit) {
  window.SkriblChromeFit.watch({
    chrome: [document.querySelector('.header'), document.getElementById('toolBar')],
    target: canvas, fit: resizeCanvas
  });
}
// ...and when a song or a photo lands, the card grows below what opening it
// revealed: bring its end on screen again, short of the dock passing under the
// header (lib/drawerdetent.js followGrowth, which Flip calls too).
if (window.SkriblDrawerDetent && window.SkriblDrawerDetent.followGrowth && _padDrawerCtl) {
  window.SkriblDrawerDetent.followGrowth(document.getElementById('mediaCard'), {
    current: () => { const c = _padDrawerCtl.current(); return c === 'photo' || c === 'music' ? c : null; },
    dock: document.getElementById('toolBar')
  });
}

// THE TAKE SAYS SO (owner, after v330: "It's not noticeable. I had to look
// around to find it and wasn't sure I was even recording"; the mock's three,
// all yes). Done wears the action's purple (styles.css, DONE, NOT STOP, AND IN
// THE ACCENT); the two moving parts are here, because app.js is every
// player's download and a player never records.
//
// THE FIRST LINE. The first time a stroke ends while a take records, a hint
// hangs under Done, its caret on it: "You're recording. Tap Done when you're
// finished." (Click, with a mouse.) lib/hints.js shows a key once, ever, and
// honours the tips switch in the menu; the take ending puts it away (below).
// Automation never meets it unless it asks (window.__skriblTakeHintForce, as
// the hello and the help cards ask): a toast over the canvas's top edge would
// be in every suite's way after its first stroke. editor_draw.js calls this
// at pen-up.
function showTakeHint() {
  if (!recording || !window.SkriblHints || !recordBtn || recordBtn.hidden) return;
  if (navigator.webdriver && window.__skriblTakeHintForce !== true) return;
  const touch = !!(window.matchMedia && window.matchMedia('(hover: none)').matches);
  window.SkriblHints.show('take-done',
    'You’re recording. ' + (touch ? 'Tap' : 'Click') + ' Done when you’re finished.', { under: recordBtn });
}
// THE DOT BREATHES while a take records: its halo (the dot's ::before) swells
// from a 3px ring at 0.16 to a 7px ring at 0.30 and settles, every 2.4s, so
// the readout looks alive between strokes too, when the bars hold still. Web
// Animations, transform and opacity only, so a phone paints nothing for it;
// not CSS keyframes, which would ship to the player's stylesheet (every
// @keyframes does, and it has a byte budget). Under Reduce Motion, or where a
// browser cannot animate a ::before, the halo keeps its still 4px ring.
(function () {
  const dot = document.querySelector('#recIndicator .dot');
  const still = window.matchMedia ? window.matchMedia('(prefers-reduced-motion: reduce)') : { matches: false };
  const can = !!(dot && dot.animate && typeof KeyframeEffect !== 'undefined' && 'pseudoElement' in KeyframeEffect.prototype);
  let breath = null, was = false;
  function sync() {
    const rec = document.body.classList.contains('recording');
    if (was && !rec && window.SkriblHints) window.SkriblHints.hide('take-done');   // it spoke of a take that has ended
    was = rec;
    const on = can && rec && !still.matches;
    if (on && !breath) {
      breath = dot.animate([
        { transform: 'scale(0.636)', opacity: 0.533, easing: 'ease-in-out' },
        { transform: 'scale(1)', opacity: 1, easing: 'ease-in-out' },
        { transform: 'scale(0.636)', opacity: 0.533 }
      ], { duration: 2400, iterations: Infinity, pseudoElement: '::before' });
    } else if (!on && breath) { breath.cancel(); breath = null; }
  }
  new MutationObserver(sync).observe(document.body, { attributes: true, attributeFilter: ['class'] });
  if (still.addEventListener) still.addEventListener('change', sync);
  sync();
})();
