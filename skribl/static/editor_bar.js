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
