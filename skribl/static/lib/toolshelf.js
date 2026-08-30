/* Tool shelf + overflow tray — shared by Pad and Flip.

   THE PROBLEM THIS SOLVES IS A PROCESS, NOT A BUG. Both editors' bottom rows
   were holding two populations out of one width budget. The document controls —
   colour, undo, redo, image, music, magnify — are a CLOSED set. The mark-making
   tools are not: pen, eraser and shape today, with select, fill and text all
   plausible. Sharing one shelf meant every new tool competed with undo for the
   same pixels, so each addition became a fresh fitting exercise across six
   breakpoints and two surfaces. Measured on Flip before the tray: a fourth cell
   takes the pill 121 -> 158px and wraps the row at 320, 344, 360, 375, 390, 431.

   `tools` is the single place a tool is declared. The shelf shows at most
   `shelfMax` cells; anything beyond lives in the tray behind a chevron. So the
   pill's width stops being a function of how many tools exist.

   WHILE EVERYTHING FITS THE MECHANISM IS DORMANT. tools.length <= shelfMax means
   every tool keeps its cell, the chevron stays hidden and the tray is never
   built — so adding this to a surface with three tools changes nothing you can
   see. That is deliberate: a tray that immediately demoted a tool to two taps
   would be a regression paid for a benefit that has not arrived.

   SHARED ON PURPOSE. verify_surfaces.py exists because app.js and flip.js define
   57 functions with the same names and share zero runs of six identical lines —
   parallel implementations that no diff will ever show you diverging. This was
   written inline in flip.js first; it moved here rather than being copied, so
   there is one shelf and not two that drift.

   The surface supplies its own elements, its own setTool and its own tray
   open/close (each editor already owns a drawer controller, and the tray joins
   that set so it is mutually exclusive with colour, photo and music). */
(function () {
  'use strict';

  function create(cfg) {
    var group = cfg.group;
    var moreBtn = cfg.moreBtn;
    var tray = cfg.tray;
    var shelfMax = cfg.shelfMax || 3;
    var tools = (cfg.tools || []).slice();
    // Most-recently-used, newest first. The ACTIVE tool is always its head,
    // which is what guarantees the active tool has a shelf cell — and therefore
    // that the sliding highlight always has a visible button to sit under.
    var mru = tools.map(function (t) { return t.id; });

    function byId(id) {
      for (var i = 0; i < tools.length; i++) if (tools[i].id === id) return tools[i];
      return null;
    }
    function btnEl(id) {
      var t = byId(id);
      return t && t.btn ? document.getElementById(t.btn) : null;
    }
    function current() { return cfg.currentTool ? cfg.currentTool() : null; }

    /* A tool registered at runtime has no cell in the template, so it gets one,
       built to match the static cells exactly — including the label span the
       phone tiers hide. Inserted BEFORE the chevron so the chevron stays last. */
    function makeShelfBtn(tool) {
      var b = document.createElement('button');
      b.type = 'button';
      b.className = 'tool-btn';
      b.id = tool.btn;
      b.setAttribute('data-tool', tool.id);
      b.title = tool.label;
      b.innerHTML = (tool.icon || '') +
                    '<span class="tool-btn-label">' + tool.label + '</span>';
      /* MARKED, so the surface's own '.tool-btn' click binding can skip it.
         Both bindings used to fire on a button this function created, and a
         DERIVING handler survives that while a TOGGLING one does not: the
         registry's setTool closed the stamp shelf on a second tap and the
         surface's setTool immediately re-derived it open, so the shelf could
         only be dismissed by leaving the tool. Static cells in the template are
         not bound here and keep the surface route; every button therefore has
         exactly one. */
      b.dataset.shelfBound = '1';
      b.addEventListener('click', function () { cfg.setTool(tool.id); });
      if (group && moreBtn) group.insertBefore(b, moreBtn);
      else if (group) group.appendChild(b);
      return b;
    }

    /* A tool declared in `tools` need not have a cell in the template. The three
       that shipped with the row do; Select, added in v227, does not — and
       requiring markup for it would put the roster in two places, which is the
       thing this registry exists to prevent. Any initial tool whose element is
       missing gets one built the same way a registered one does. */
    tools.forEach(function (t) { if (t.btn && !document.getElementById(t.btn)) makeShelfBtn(t); });

    function overflowing() { return tools.length > shelfMax; }

    /* Which tools get a shelf cell: everything fits, or the most recent
       shelfMax - 1 do and the chevron takes the last slot. */
    function shelf() {
      if (!overflowing()) return tools.map(function (t) { return t.id; });
      return mru.slice(0, shelfMax - 1);
    }

    /* The sliding accent pill. Both editors computed this identically — the same
       `offsetLeft - group padding`, the same two style writes — and both had
       arrived there by fixing the SAME two bugs independently: a two-button
       assumption that parked the pill under the wrong cell once a third tool
       existed, and a double subtraction of the group's own offsetLeft that only
       looked right while the row's padding happened to match the group's.
       Two copies of one fix is what verify_surfaces.py exists to catch, and it
       caught this one: extracting it here is what the ratchet asked for.

       offsetLeft is ALREADY relative to the group, which is position: relative
       and therefore the button's offsetParent; the padding subtraction is what
       matches .tool-slider's own `left`. */
    function placeSlider(activeBtn) {
      var sl = cfg.slider;
      if (!sl || !group) return;
      var btn = activeBtn || btnEl(current()) || document.getElementById('penToolBtn');
      if (!btn) return;
      var padL = parseFloat(getComputedStyle(group).paddingLeft) || 0;
      sl.style.width = btn.offsetWidth + 'px';
      sl.style.transform = 'translateX(' + (btn.offsetLeft - padL) + 'px)';
    }

    function sync() {
      var shown = {};
      shelf().forEach(function (id) { shown[id] = true; });
      tools.forEach(function (t) {
        var el = btnEl(t.id);
        if (el) el.hidden = !shown[t.id];
      });
      if (moreBtn) {
        moreBtn.hidden = !overflowing();
        // The arrow points at the CHEVRON, not at the row's centre: the tool
        // group sits at the left end, so a centred arrow would point at the
        // colour ring. Measured rather than guessed, because the pill's width
        // moves with the width tier.
        if (overflowing() && tray) {
          var r = moreBtn.getBoundingClientRect();
          var p = tray.getBoundingClientRect();
          if (r.width && p.width) {
            tray.style.setProperty('--tray-arrow',
              Math.round(r.left + r.width / 2 - p.left) + 'px');
          }
        }
      }
      placeSlider();
    }

    /* Rebuilt on open rather than cached: a tool can be registered at any time,
       and a stale tray missing one is worse than the cost of a few appendChild
       calls on a control the user has just deliberately opened. */
    function buildTray() {
      if (!tray) return;
      tray.innerHTML = '';
      var active = current();
      tools.forEach(function (t) {
        var b = document.createElement('button');
        b.type = 'button';
        b.className = 'tool-tray-btn' + (t.id === active ? ' active' : '');
        b.setAttribute('data-tool', t.id);
        b.setAttribute('aria-pressed', String(t.id === active));
        var shelfBtn = btnEl(t.id);
        var svg = shelfBtn ? shelfBtn.querySelector('svg') : null;
        b.innerHTML = (t.icon || (svg ? svg.outerHTML : '')) +
                      '<span>' + t.label + '</span>';
        b.addEventListener('click', function (e) {
          e.stopPropagation();
          cfg.setTool(t.id);
          if (cfg.closeTray) cfg.closeTray();
        });
        tray.appendChild(b);
      });
    }

    /* Called by the surface's setTool AFTER it has settled on a tool id. Records
       the MRU, re-syncs the shelf and repaints the tray's pressed state. */
    function noteUse(id) {
      if (!byId(id)) return;
      mru = [id].concat(mru.filter(function (x) { return x !== id; }));
      sync();
      var cells = tray ? tray.querySelectorAll('.tool-tray-btn') : [];
      for (var i = 0; i < cells.length; i++) {
        var on = cells[i].getAttribute('data-tool') === id;
        cells[i].classList.toggle('active', on);
        cells[i].setAttribute('aria-pressed', String(on));
      }
    }

    return {
      /* The real extension point, and the one the harness drives: adding a tool
         is one call, not a template edit plus a JS edit plus six breakpoints. */
      register: function (tool) {
        if (!tool || !tool.id || byId(tool.id)) return false;
        var entry = { id: tool.id, label: tool.label || tool.id,
                      btn: tool.btn || (tool.id + 'ToolBtn'), icon: tool.icon || '' };
        tools.push(entry);
        mru.push(entry.id);
        makeShelfBtn(entry);
        sync();
        return true;
      },
      has: function (id) { return !!byId(id); },
      btnFor: btnEl,
      list: function () { return tools.map(function (t) { return t.id; }); },
      shelf: shelf,
      overflowing: overflowing,
      sync: sync,
      placeSlider: placeSlider,
      buildTray: buildTray,
      noteUse: noteUse
    };
  }

  var api = { create: create };
  if (typeof window !== 'undefined') window.SkriblToolShelf = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})();
