/* Exclusive drawer controller — the ONE implementation of a machine both
 * editors had hand-rolled: named panels above/below a toolbar, at most one
 * open, the opener button reflecting state, and a scroll that reveals the
 * opened panel without stranding it under browser chrome.
 *
 * What was duplicated before this: Pad's openDrawer() (idMap + class toggling
 * + reduced-motion scroll) and Flip's openPop/closePop/openPhoto/openMusic/
 * hidePhoto/hideMusic/closeMediaDrawers/refitDrawer octet — eight functions
 * whose pairwise "close the others first" calls were the exclusivity rule
 * written out by hand, differently, twice. The editors keep their own hooks
 * (repositioning, waveforms, slider positioning); only the machine moved.
 *
 * skriblDrawers({
 *   panels: {
 *     name: {
 *       panel:  element or id            (required)
 *       button: element or id            (optional: gets openClass/aria)
 *       openClass: 'open'                (optional: class toggled on button)
 *       aria: true                       (optional: aria-expanded on button)
 *       onOpen(), onClose()              (optional hooks, run AFTER state set)
 *     }, ...
 *   },
 *   reveal(openPanelOrNull, name|null)   (required: editor's scroll behaviour)
 * }) -> { open(name|null), toggle(name), current(), isOpen(name) }
 *
 * open(name) closes whatever else is open (firing its onClose), opens `name`,
 * then calls reveal() exactly once — the hand-rolled versions refitted after
 * every intermediate close, scrolling panels that were about to vanish.
 * open(null) closes everything. Degrades safely: a name whose panel is
 * missing from the DOM is ignored, like every other lib here.
 */
(function () {
  'use strict';

  function _el(ref) {
    if (!ref) return null;
    return typeof ref === 'string' ? document.getElementById(ref) : ref;
  }

  function skriblDrawers(cfg) {
    var panels = {};
    var order = [];
    Object.keys(cfg.panels || {}).forEach(function (name) {
      var d = cfg.panels[name];
      var panel = _el(d.panel);
      if (!panel) return;                 // absent in this page's DOM: skip
      panels[name] = {
        panel: panel,
        button: _el(d.button),
        openClass: d.openClass || null,
        aria: !!d.aria,
        onOpen: d.onOpen || null,
        onClose: d.onClose || null
      };
      order.push(name);
    });
    var currentName = null;

    function _set(name, open) {
      var d = panels[name];
      d.panel.hidden = !open;
      if (d.button) {
        if (d.openClass) d.button.classList.toggle(d.openClass, open);
        if (d.aria) d.button.setAttribute('aria-expanded', String(open));
      }
      var hook = open ? d.onOpen : d.onClose;
      if (hook) hook();
    }

    function open(name) {
      if (name != null && !panels[name]) name = null;
      var prev = currentName;
      if (prev === name) {
        if (name != null && cfg.reveal) cfg.reveal(panels[name].panel, name);
        return;
      }
      currentName = name;               // set BEFORE hooks: a hook asking
      if (prev != null) _set(prev, false);   // current() must see the new state
      if (name != null) _set(name, true);
      if (cfg.reveal) cfg.reveal(name != null ? panels[name].panel : null, name);
    }

    return {
      open: open,
      toggle: function (name) { open(currentName === name ? null : name); },
      current: function () { return currentName; },
      isOpen: function (name) { return currentName === name; }
    };
  }

  if (typeof window !== 'undefined') window.skriblDrawers = skriblDrawers;
  if (typeof module !== 'undefined' && module.exports) module.exports = { skriblDrawers: skriblDrawers };
})();
