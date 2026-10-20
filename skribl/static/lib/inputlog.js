/* The input log: what the screen said, for a bug only a phone shows. The two
 * editors only, and only when the page was opened with ?inputlog in its address.
 *
 * WHY IT EXISTS (the owner's iPhone, after v326, T1): "When I go really fast it
 * stops drawing. It seems like it's processing because if you wait a second it
 * will accept your strokes" -- one finger, no thumb resting, nowhere near an
 * edge, and Flip fine. Chromium here keeps every stroke, 120 quick ones with
 * the processor slowed six times, so the answer is on the phone, which has no
 * console without a Mac and a cable. Two fixes (#528, #553) were built on a
 * reading of the phone that the phone never confirmed. This asks it.
 *
 * WHAT IT KEEPS. Every press, lift and cancel the page hears, pointer and touch
 * alike, with where it landed, how many fingers the screen listed, and what
 * the editor was doing just before (drawing, whose stroke, pinching, playing,
 * how many strokes it holds); a press that began no stroke is marked so; moves
 * are counted, not listed; a frame that came late, and the page losing focus or
 * going out of sight, are noted. No drawing, no title, no words: the shape of
 * the problem is in the timings.
 *
 * IT SENDS NOTHING, as "Report a problem" sends nothing (lib/report.js): Copy
 * puts the log on the clipboard, and the person pastes it where they choose.
 *
 * IT CHANGES NOTHING IT WATCHES. Every listener is passive and on the window,
 * in the capture phase, so it hears each event before the editor does and can
 * cancel none of them. Off, it adds no listener and no element at all.
 *
 *   SkriblInputLog.watch(surface, {
 *     editor    'Pad' or 'Flip', for the log's first line
 *     state()   { d, id, pin, play, tool, g }: drawing, the stroke's
 *               pointerId, pinching, playing, the tool, and the stroke count;
 *               any other keys are written too
 *   })
 *   SkriblInputLog.on()      true while recording
 *   SkriblInputLog.text()    the log as it would be copied
 */
(function (global) {
  'use strict';
  var doc = global.document;
  var MAX = 900;                // lines kept; the oldest go first
  var STALL_MS = 120;           // a frame later than this is noted

  function asked() {
    try { return /[?&#]inputlog\b/.test(global.location.search + global.location.hash); } catch (e) { return false; }
  }
  var active = asked();
  var lines = [], dropped = 0, t0 = 0, opts = null, surf = null, ui = null;

  function now() { return (global.performance && performance.now) ? performance.now() : Date.now(); }
  function stamp() { var s = (now() - t0) / 1000; return (s < 10 ? '  ' : s < 100 ? ' ' : '') + s.toFixed(3); }
  function push(s) {
    lines.push(stamp() + ' ' + s);
    if (lines.length > MAX) { lines.splice(0, 100); dropped += 100; }
  }
  function where(el) {
    if (!el || el === global || el === doc) return 'page';
    if (surf && (el === surf || (surf.contains && surf.contains(el)))) return el === surf ? 'DRAWING' : 'DRAWING>' + (el.id || el.tagName.toLowerCase());
    if (el.id) return '#' + el.id;
    var c = typeof el.className === 'string' ? el.className.split(/\s+/)[0] : '';
    return el.tagName ? el.tagName.toLowerCase() + (c ? '.' + c : '') : '?';
  }
  function state() {
    var s = null;
    try { s = opts && opts.state ? opts.state() : null; } catch (e) { return ' | state threw ' + e.message; }
    if (!s) return '';
    var out = [];
    for (var k in s) {
      if (!Object.prototype.hasOwnProperty.call(s, k)) continue;
      var v = s[k];
      out.push(k + (v === true ? '1' : v === false ? '0' : v == null ? '-' : typeof v === 'string' ? '=' + v : String(v)));
    }
    return ' | ' + out.join(' ');
  }

  // A press on the drawing that began no stroke: judged at the next thing the
  // page hears, by which time the editor has had its say.
  var pending = null;   // { n: the press's line, counted from the first ever, id }
  function judge() {
    if (!pending) return;
    var p = pending, i = p.n - dropped, s = null;
    pending = null;
    if (i < 0) return;
    try { s = opts.state(); } catch (e) { return; }
    if (s && !s.d) lines[i] += '   <-- NO STROKE';
    else if (s && s.id != null && s.id !== p.id) lines[i] += '   <-- REFUSED, stroke ' + s.id + ' still down';
  }

  var moves = {};
  function onPointer(e) {
    if (e.type === 'pointermove') { moves[e.pointerId] = (moves[e.pointerId] || 0) + 1; return; }
    judge();
    var short = { pointerdown: 'down', pointerup: 'up', pointercancel: 'CANCEL',
                  gotpointercapture: 'got-capture', lostpointercapture: 'lost-capture' }[e.type] || e.type;
    var m = '';
    if ((e.type === 'pointerup' || e.type === 'pointercancel') && moves[e.pointerId]) {
      m = ' moves ' + moves[e.pointerId]; delete moves[e.pointerId];
    }
    push('ptr ' + short + ' #' + e.pointerId + ' ' + (e.pointerType || '?') + (e.isPrimary ? '' : ' (not primary)')
      + ' at ' + Math.round(e.clientX) + ',' + Math.round(e.clientY) + ' on ' + where(e.target) + m + state());
    if (e.type === 'pointerdown' && surf && (e.target === surf || (surf.contains && surf.contains(e.target)))) {
      pending = { n: dropped + lines.length - 1, id: e.pointerId };
    }
  }
  var tmoves = 0;
  function onTouch(e) {
    if (e.type === 'touchmove') { tmoves++; return; }
    judge();
    var ch = [], all = [];
    for (var i = 0; i < e.changedTouches.length; i++) ch.push(e.changedTouches[i].identifier);
    for (var j = 0; j < e.touches.length; j++) {
      var t = e.touches[j];
      all.push(t.identifier + ':' + where(t.target));
    }
    var short = { touchstart: 'start', touchend: 'end', touchcancel: 'CANCEL' }[e.type];
    var m = (e.type !== 'touchstart' && tmoves) ? ' moves ' + tmoves : '';
    if (e.type !== 'touchstart') tmoves = 0;
    push('touch ' + short + ' [' + ch.join(',') + '] on screen ' + e.touches.length
      + (all.length ? ' (' + all.join(' ') + ')' : '') + m + state());
  }
  function onOther(e) {
    judge();
    var what = e.type === 'visibilitychange' ? (doc.hidden ? 'page hidden' : 'page shown') : e.type === 'blur' ? 'page lost focus'
      : e.type === 'focus' ? 'page has focus' : e.type === 'pagehide' ? 'pagehide' : e.type === 'pageshow' ? 'pageshow'
      : e.type === 'resize' ? 'resize ' + global.innerWidth + 'x' + global.innerHeight : e.type;
    push('-- ' + what + state());
  }
  var errs = 0;
  function onError(e) {
    if (errs++ >= 10) return;
    var msg = e.type === 'error' ? (e.message || 'error') : ('promise: ' + ((e.reason && e.reason.message) || e.reason));
    push('!! ' + String(msg).slice(0, 160));
  }

  var last = 0;
  function frame(t) {
    if (last && !doc.hidden && t - last > STALL_MS) push('.. frame late by ' + Math.round(t - last) + ' ms' + state());
    last = doc.hidden ? 0 : t;
    global.requestAnimationFrame(frame);
  }

  function header() {
    var build = '';
    try { var b = doc.querySelector('script[data-build]'); build = b ? b.getAttribute('data-build') : ''; } catch (e) {}
    var standalone = false;
    try { standalone = global.navigator.standalone === true || global.matchMedia('(display-mode: standalone)').matches; } catch (e) {}
    return [
      'Skribl input log · ' + ((opts && opts.editor) || '?') + ' · build ' + (build || '?'),
      new Date().toISOString() + ' · ' + global.navigator.userAgent,
      'screen ' + global.innerWidth + 'x' + global.innerHeight + ' · dpr ' + (global.devicePixelRatio || 1)
        + ' · ' + (standalone ? 'Home Screen app' : 'browser tab') + ' · ' + (lines.length + dropped) + ' lines'
        + (dropped ? ' (the first ' + dropped + ' dropped)' : ''),
      'state keys: d drawing, id the stroke\'s pointer, pin pinching, play playing, g strokes kept',
      ''
    ].join('\n');
  }
  function text() { judge(); return header() + lines.join('\n') + '\n'; }

  function button(label, fn) {
    var b = doc.createElement('button');
    b.type = 'button';
    b.textContent = label;
    var s = b.style;
    s.font = '600 14px/1 -apple-system, system-ui, sans-serif'; s.color = '#fff';
    s.background = 'rgba(255,255,255,.16)'; s.border = '0'; s.borderRadius = '14px';
    s.minHeight = '36px'; s.padding = '0 11px'; s.cursor = 'pointer';
    b.addEventListener('click', fn);
    return b;
  }
  function showText(t) {
    var box = doc.createElement('div');
    var s = box.style;
    s.position = 'fixed'; s.inset = '12px'; s.zIndex = '2147483000'; s.display = 'flex'; s.flexDirection = 'column';
    s.gap = '8px'; s.padding = '12px'; s.borderRadius = '16px'; s.background = 'rgba(20,14,36,.96)';
    var area = doc.createElement('textarea');
    area.value = t;
    area.setAttribute('aria-label', 'The input log');
    area.readOnly = true;
    var a = area.style;
    a.flex = '1'; a.font = '400 16px/1.35 ui-monospace, Menlo, monospace'; a.color = '#fff';
    a.background = 'rgba(255,255,255,.08)'; a.border = '0'; a.borderRadius = '10px'; a.padding = '8px';
    box.appendChild(area);
    box.appendChild(button('Done', function () { box.remove(); }));
    doc.body.appendChild(box);
    area.focus(); area.select();
  }
  function copy(btn) {
    var t = text();
    function said(w) { btn.textContent = w; setTimeout(function () { btn.textContent = 'Copy log'; }, 2000); }
    try {
      if (global.navigator.clipboard && global.navigator.clipboard.writeText) {
        global.navigator.clipboard.writeText(t).then(function () { said('Copied'); }, function () { showText(t); });
        return;
      }
    } catch (e) {}
    showText(t);
  }
  function pill() {
    var box = doc.createElement('div');
    box.id = 'skriblInputLog';
    box.setAttribute('role', 'group');
    box.setAttribute('aria-label', 'Input log');
    var s = box.style;
    s.position = 'fixed'; s.left = '8px'; s.top = 'calc(env(safe-area-inset-top, 0px) + 4px)'; s.zIndex = '2147483000';
    s.display = 'flex'; s.alignItems = 'center'; s.gap = '6px'; s.padding = '3px 3px 3px 12px';
    s.borderRadius = '18px'; s.background = 'rgba(20,14,36,.88)'; s.color = '#fff';
    s.font = '600 13px/1 -apple-system, system-ui, sans-serif'; s.boxShadow = '0 4px 14px rgba(0,0,0,.3)';
    var dot = doc.createElement('span');
    dot.setAttribute('aria-hidden', 'true');
    dot.style.cssText = 'width:8px;height:8px;border-radius:4px;background:#ff5a5f';
    var copyBtn = button('Copy log', function () { copy(copyBtn); });
    var clear = button('Clear', function () { lines = []; dropped = 0; moves = {}; tmoves = 0; pending = null; t0 = now(); push('-- cleared' + state()); });
    box.appendChild(dot); box.appendChild(copyBtn); box.appendChild(clear);
    doc.body.appendChild(box);
    return { box: box };
  }

  function watch(surface, o) {
    if (!active || !surface || surf) return;
    surf = surface; opts = o || {};
    t0 = now();
    var cap = { capture: true, passive: true };
    ['pointerdown', 'pointermove', 'pointerup', 'pointercancel', 'gotpointercapture', 'lostpointercapture'].forEach(function (k) {
      global.addEventListener(k, onPointer, cap);
    });
    ['touchstart', 'touchmove', 'touchend', 'touchcancel'].forEach(function (k) { global.addEventListener(k, onTouch, cap); });
    ['blur', 'focus', 'pagehide', 'pageshow', 'resize'].forEach(function (k) { global.addEventListener(k, onOther, cap); });
    doc.addEventListener('visibilitychange', onOther, cap);
    global.addEventListener('error', onError, cap);
    global.addEventListener('unhandledrejection', onError, cap);
    function start() { ui = pill(); push('-- recording' + state()); global.requestAnimationFrame(frame); }
    if (doc.body) start(); else doc.addEventListener('DOMContentLoaded', start);
  }

  var api = { watch: watch, on: function () { return active && !!surf; }, text: text };
  global.SkriblInputLog = api;
})(window);
