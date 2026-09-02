/* Eyedropper — the armed-state machine, shared by both editors.
 *
 * WHY ONE PATH AND NOT TWO. Pad used to call the browser's native
 * `window.EyeDropper` when present and fall back to tap-to-sample otherwise;
 * Flip only ever did tap-to-sample. That native branch is not an ALTERNATIVE
 * to the fallback, it is an EXTRA: Safari, Firefox and every browser on iOS
 * have no EyeDropper, so the in-app path has to exist regardless. Keeping both
 * meant maintaining two implementations forever and shipping two different
 * experiences behind one button depending on which browser opened it.
 *
 * It was also the wrong semantics. The native picker samples anything on the
 * screen, including other applications, when the thing being asked for is "the
 * colour of that part of my drawing". And an OS-level dialog cannot be driven
 * by the harness, so the path most desktop users took was the path no
 * assertion could reach.
 *
 * Deleting it removes a path rather than adding one. The cost is that desktop
 * Chrome loses screen-wide sampling; if that is wanted back it belongs here,
 * once, not in one editor only.
 *
 * WHAT THIS OWNS: armed/disarmed, the button's class and aria-pressed, the
 * canvas cursor, Escape, the one-shot semantics (a sample disarms), and the
 * LOUPE — the magnified press-drag picker below.
 * WHAT IT DOES NOT: reading the pixel. Pad and Flip genuinely differ there —
 * different contexts, device-pixel-ratio handling and transparent-pixel
 * fallbacks — so `onSample` is injected and each surface keeps its own.
 *
 * THE LOUPE. Tap-to-sample has a physical flaw on the surface most people
 * pick colours on: a fingertip is forty pixels wide and the pixel being
 * sampled is under it (owner: "when you hit eye dropper it needs to open a
 * magnified box so you can see what color you choose"). So an armed press
 * opens the standard loupe — a circle above the finger showing the stage
 * magnified, a reticle on the exact cell, the ring and a chip wearing the
 * colour it currently reads — and RELEASE is what picks. Drag to aim.
 * A plain tap still works: press and release in place picks that point.
 * Escape or pointercancel mid-drag abandons the pick without committing.
 *
 * The loupe draws from the surface's COMPOSITED stage (padArtwork /
 * paintArtwork via `artwork`), the same canvas the sampler reads, so what
 * the magnifier shows and what release picks cannot disagree — photo,
 * background colour and strokes included, onion skin and guides excluded
 * for exactly the reason sampling excludes them.
 */
(function () {
  'use strict';

  /* Geometry shared with the .eyedropper-loupe CSS: 120px circle with a 4px
   * ring leaves a 112px window; keep these in step with styles.css. */
  var LOUPE_SIZE = 120, LOUPE_RING = 4, LOUPE_INNER = LOUPE_SIZE - 2 * LOUPE_RING;
  var LOUPE_ZOOM = 6;      // one stage CSS px becomes six loupe CSS px
  var LOUPE_GAP = 26;      // between the pointer and the loupe's near edge

  function buildLoupe() {
    var el = document.createElement('div');
    el.className = 'eyedropper-loupe';
    el.hidden = true;
    var cv = document.createElement('canvas');
    var ldpr = window.devicePixelRatio || 1;
    cv.width = Math.round(LOUPE_INNER * ldpr);
    cv.height = Math.round(LOUPE_INNER * ldpr);
    var chip = document.createElement('div');
    chip.className = 'eyedropper-loupe-chip';
    el.appendChild(cv);
    el.appendChild(chip);
    document.body.appendChild(el);
    return { el: el, cv: cv, ctx: cv.getContext('2d'), chip: chip };
  }

  function create(opts) {
    opts = opts || {};
    var button = opts.button || null;
    var surface = opts.surface || null;             // element that shows the cursor
    var idleCursor = opts.idleCursor || '';         // Pad restores '', Flip 'none'
    var onSample = typeof opts.onSample === 'function' ? opts.onSample : function () {};
    var onArm = typeof opts.onArm === 'function' ? opts.onArm : function () {};
    var onChange = typeof opts.onChange === 'function' ? opts.onChange : function () {};
    // Loupe wiring — all four present enables the press-drag picker;
    // without them beginPick() declines and the surface's tap path runs.
    var getPoint = typeof opts.getPoint === 'function' ? opts.getPoint : null;
    var artwork = typeof opts.artwork === 'function' ? opts.artwork : null;
    var dprOf = typeof opts.dpr === 'function' ? opts.dpr : function () { return window.devicePixelRatio || 1; };
    var bgOf = typeof opts.bg === 'function' ? opts.bg : function () { return '#000000'; };
    var onPick = typeof opts.onPick === 'function' ? opts.onPick : null;
    var armed = false;
    var loupe = null;      // built on first press, reused after
    var session = null;    // the active press-drag pick, or null

    /* The same read both surfaces' samplers do — composited stage, clamped
     * to its bounds, transparent means the background colour. */
    function readColorAt(x, y) {
      try {
        var art = artwork();
        var adpr = dprOf();
        var cx = Math.min(Math.max(Math.round(x * adpr), 0), art.width - 1);
        var cy = Math.min(Math.max(Math.round(y * adpr), 0), art.height - 1);
        var d = art.getContext('2d').getImageData(cx, cy, 1, 1).data;
        if (d[3] < 10) return bgOf();
        return '#' + [d[0], d[1], d[2]].map(function (v) {
          return v.toString(16).padStart(2, '0');
        }).join('');
      } catch (e) { return bgOf(); }
    }

    function drawLoupe(x, y, clientX, clientY) {
      var art = artwork();
      var adpr = dprOf();
      var ctx = loupe.ctx, W = loupe.cv.width, H = loupe.cv.height;
      var srcPx = (LOUPE_INNER / LOUPE_ZOOM) * adpr;   // stage device px shown
      var sx = x * adpr - srcPx / 2, sy = y * adpr - srcPx / 2;
      ctx.imageSmoothingEnabled = false;
      // Off-stage area wears the background colour — the same thing sampling
      // says a pixel out there would be.
      ctx.fillStyle = bgOf();
      ctx.fillRect(0, 0, W, H);
      // Intersect the source rect with the stage by hand: browsers disagree
      // about drawImage source rects that hang off the canvas.
      var ix0 = Math.max(0, sx), iy0 = Math.max(0, sy);
      var ix1 = Math.min(art.width, sx + srcPx), iy1 = Math.min(art.height, sy + srcPx);
      if (ix1 > ix0 && iy1 > iy0) {
        var k = W / srcPx;
        ctx.drawImage(art, ix0, iy0, ix1 - ix0, iy1 - iy0,
                      (ix0 - sx) * k, (iy0 - sy) * k, (ix1 - ix0) * k, (iy1 - iy0) * k);
      }
      // Reticle on the sampled cell: black under white so it reads on any ink.
      var cell = LOUPE_ZOOM * (W / LOUPE_INNER);
      ctx.strokeStyle = 'rgba(0,0,0,0.8)';
      ctx.lineWidth = 3;
      ctx.strokeRect((W - cell) / 2, (H - cell) / 2, cell, cell);
      ctx.strokeStyle = '#ffffff';
      ctx.lineWidth = 1.5;
      ctx.strokeRect((W - cell) / 2, (H - cell) / 2, cell, cell);

      var hex = readColorAt(x, y);
      loupe.el.style.borderColor = hex;
      loupe.chip.textContent = hex.toUpperCase();

      // Above the finger, clamped on-screen; below it when there's no room.
      var left = Math.min(Math.max(clientX - LOUPE_SIZE / 2, 8),
                          window.innerWidth - LOUPE_SIZE - 8);
      var top = clientY - LOUPE_SIZE - LOUPE_GAP;
      if (top < 8) top = clientY + LOUPE_GAP;
      loupe.el.style.left = left + 'px';
      loupe.el.style.top = top + 'px';
      return hex;
    }

    function endSession(commit) {
      if (!session) return;
      var s = session;
      session = null;
      if (s.raf) cancelAnimationFrame(s.raf);
      window.removeEventListener('pointermove', s.move, true);
      window.removeEventListener('pointerup', s.up, true);
      window.removeEventListener('pointercancel', s.cancel, true);
      if (loupe) loupe.el.hidden = true;
      if (commit && armed && onPick) {
        onPick(readColorAt(s.x, s.y), s.x, s.y);
        disarm();
      }
    }

    /* Call from the surface's press handler while armed. Returns true when it
     * took the press (the caller returns instead of falling back to its
     * one-shot tap sample). Release commits; Escape/cancel abandons.
     *
     * The session listens on WINDOW, capture phase, for POINTER events —
     * never on the surface, and never via setPointerCapture. Pad starts
     * strokes from mousedown/touchstart, so the press event this receives
     * may have no pointerId to capture with; the browser still emits the
     * pointer stream for the same drag, window sees it wherever the finger
     * wanders, and capture-phase means no stopPropagation between here and
     * the surface can starve the loupe. `sameSource` matches the stream to
     * the press: by pointerId when the press had one, by primary-ness when
     * it did not (a mousedown/touchstart press). */
    function beginPick(ev) {
      if (!armed || !getPoint || !artwork || !onPick) return false;
      if (session) return true;                       // second finger: ignore
      if (!loupe) loupe = buildLoupe();
      function sameSource(e) {
        if (ev.pointerId != null && e.pointerId != null) return e.pointerId === ev.pointerId;
        return e.isPrimary !== false;
      }
      var s = session = {
        raf: 0, x: 0, y: 0,
        move: function (e) {
          if (!sameSource(e)) return;
          s.pending = e;
          // rAF-gated: the stage recomposites on every frame drawn, and a
          // pointermove stream outruns the display.
          if (!s.raf) s.raf = requestAnimationFrame(function () {
            s.raf = 0;
            if (session === s && s.pending) s.show(s.pending);
          });
        },
        up: function (e) { if (sameSource(e)) endSession(true); },
        cancel: function (e) { if (sameSource(e)) endSession(false); },
        show: function (e) {
          var p = getPoint(e);
          s.x = p.x; s.y = p.y;
          // A touchstart press carries its coordinates in touches[0].
          var t = (e.touches && e.touches.length) ? e.touches[0] : e;
          drawLoupe(p.x, p.y, t.clientX, t.clientY);
        }
      };
      window.addEventListener('pointermove', s.move, true);
      window.addEventListener('pointerup', s.up, true);
      window.addEventListener('pointercancel', s.cancel, true);
      loupe.el.hidden = false;
      s.show(ev);
      return true;
    }

    function apply() {
      if (button) {
        button.classList.toggle('picking', armed);
        // An armed mode indistinguishable from an unarmed one makes the next
        // canvas tap a surprise, and a class alone says nothing to a screen
        // reader.
        button.setAttribute('aria-pressed', armed ? 'true' : 'false');
      }
      // Inline, because setTool() writes surface.style.cursor inline and an
      // inline style beats any stylesheet rule.
      if (surface) surface.style.cursor = armed ? 'crosshair' : idleCursor;
      onChange(armed);
    }

    function setArmed(v) {
      v = !!v;
      if (v === armed) return;
      armed = v;
      // Disarming mid-drag (Escape, drawer closing) abandons the pick: the
      // loupe hides and nothing commits.
      if (!armed) endSession(false);
      apply();
      if (armed) onArm();
    }

    function toggle() { setArmed(!armed); }
    function disarm() { setArmed(false); }

    /* Call from the surface's own pointer handler when a tap lands on the
     * canvas while armed. Returns true if it consumed the event, so the
     * caller can `return` rather than also starting a stroke. */
    function handleTap(ev) {
      if (!armed) return false;
      try { onSample(ev); } catch (e) {}
      disarm();
      return true;
    }

    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && armed) { e.preventDefault(); disarm(); }
    });

    if (button) {
      button.addEventListener('click', function (e) {
        e.stopPropagation();
        toggle();
      });
    }

    apply();

    return {
      toggle: toggle,
      disarm: disarm,
      handleTap: handleTap,
      beginPick: beginPick,
      isArmed: function () { return armed; }
    };
  }

  window.SkriblEyedropper = { create: create };
}());
