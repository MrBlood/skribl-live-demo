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
// color, strokeOpacity, bgColor and _padDrawerCtl.

const paintPenSwoosh = (window.SkriblPenSwoosh && window.SkriblPenSwoosh.wire)
  ? window.SkriblPenSwoosh.wire({
      canvas: 'penSwoosh', button: 'penToolBtn', range: 'brushSizeRange', scope: '#drawPanel, #toolBar',
      state: () => ({ brush: window.SkriblBrush ? window.SkriblBrush.name() : 'pen',
                      size: size, color: color, opacity: strokeOpacity, bg: bgColor })
    })
  : () => {};

const _mediaTabs = (window.SkriblMediaTabs && _padDrawerCtl) ? window.SkriblMediaTabs.attach({
  ctl: _padDrawerCtl, button: 'mediaOpenBtn', strip: 'mediaTabs',
  dot: 'mediaTabDot', sources: ['photoTabDot', 'musicTabDot']
}) : null;
function syncMediaTabs(name) { if (_mediaTabs) _mediaTabs.sync(name); }
