/* Skribl audio diagnostic — loaded ONLY for ?audioDebug=1.
 *
 * WHY THIS FILE EXISTS, AND WHY IT IS SEPARATE.
 * The iPhone found a bug three builds of green tests could not: the player
 * built its AudioContext at page load (no user activation), iOS handed back a
 * SUSPENDED context, and the code started a buffer source on it anyway. A
 * source object existed, so the retry that was supposed to repair the start
 * ("if (running && !paSource)") never ran, and every shared link was silent on
 * iPhone while desktop and the harness were perfectly happy — their contexts
 * are running from the first frame, so the broken branch is unreachable there.
 *
 * Neither of us can attach devtools to that phone, so this makes the state
 * legible ON the device: open any Skribl URL with ?audioDebug=1 and screenshot
 * the panel.
 *
 * IT INSTRUMENTS THE REAL API, NOT THE APP. Earlier drafts had app.js call
 * hooks like _skriblAudioDebug.started(). That was wrong twice over: it cost
 * the player bytes forever for a diagnostic almost nobody runs, and it would
 * have reported what app.js BELIEVES rather than what WebKit did — which is
 * precisely the gap that hid this bug. So this wraps AudioContext, resume,
 * decodeAudioData, createBufferSource and start, and reports the context's own
 * state at each moment. app.js contains no reference to this file.
 *
 * THE FIELD THAT MATTERS MOST is currentTime before start vs ~500 ms after. If
 * it advances and you still hear nothing, the context is genuinely running and
 * the fault is downstream (routing, gain, the silent switch). If it does not
 * advance, the context is not really running whatever `state` claims.
 */
(function () {
  'use strict';
  var AC = window.AudioContext || window.webkitAudioContext;
  if (!AC) return;

  var t0 = performance.now();
  var rows = [];
  var seq = 0;

  function stamp() { return ((performance.now() - t0) / 1000).toFixed(3) + 's'; }

  function log(label, value) {
    rows.push({ n: ++seq, at: stamp(), label: label, value: String(value) });
    render();
  }

  // Is a user gesture being dispatched RIGHT NOW? Capture-phase listeners run
  // before the app's, and the flag is cleared in a task, so anything
  // constructed synchronously inside the handler is correctly attributed.
  var inGesture = false;
  ['pointerdown', 'touchstart', 'mousedown', 'click'].forEach(function (t) {
    document.addEventListener(t, function () {
      inGesture = true;
      setTimeout(function () { inGesture = false; }, 0);
    }, true);
  });

  var panel, body, pill, open = false;

  function render() {
    if (!body) return;
    var html = '';
    for (var i = 0; i < rows.length; i++) {
      // Phone-first: a fixed 150px label column pushed the value into a
      // three-line ragged wrap at 390. Label wraps, value takes the rest.
      html += '<div style="display:flex;gap:6px;border-bottom:1px solid #222;padding:3px 0">'
        + '<span style="color:#666;flex:0 0 40px">' + rows[i].at + '</span>'
        + '<span style="color:#9ecbff;flex:0 0 96px">' + rows[i].label + '</span>'
        + '<span style="color:#fff;flex:1 1 auto;word-break:break-word">' + rows[i].value + '</span>'
        + '</div>';
    }
    body.innerHTML = html;
    body.scrollTop = body.scrollHeight;
    if (pill) pill.textContent = 'AUDIO ' + rows.length;
  }

  function setOpen(v) {
    open = v;
    panel.style.display = v ? 'flex' : 'none';
    pill.style.display = v ? 'none' : 'block';
    if (v) render();
  }

  function mount() {
    // COLLAPSED BY DEFAULT. A fixed panel across the bottom sits exactly on top
    // of the editor's toolbar and the player's controls — you cannot tap Play
    // through a debug overlay. So the resting state is a small pill out of the
    // way; expand it only when it is time to screenshot.
    pill = document.createElement('button');
    pill.setAttribute('style', 'position:fixed;right:8px;bottom:8px;z-index:99999;'
      + 'background:#6c5cff;color:#fff;border:0;border-radius:999px;padding:6px 12px;'
      + 'font:700 11px ui-monospace,Menlo,monospace;box-shadow:0 2px 8px rgba(0,0,0,.5)');
    pill.textContent = 'AUDIO 0';
    pill.addEventListener('click', function () { setOpen(true); });

    panel = document.createElement('div');
    panel.setAttribute('style', 'position:fixed;left:0;right:0;bottom:0;z-index:99999;'
      + 'background:#000;color:#fff;font:10px/1.3 ui-monospace,Menlo,monospace;'
      + 'max-height:60vh;display:none;flex-direction:column;border-top:2px solid #6c5cff');
    var head = document.createElement('div');
    head.setAttribute('style', 'padding:6px 8px;background:#6c5cff;color:#fff;font-weight:700;'
      + 'display:flex;justify-content:space-between;align-items:center');
    head.innerHTML = '<span>SKRIBL AUDIO DEBUG</span>';
    var close = document.createElement('button');
    close.textContent = 'collapse';
    close.setAttribute('style', 'background:#000;color:#fff;border:0;padding:4px 10px;border-radius:6px;font:700 11px ui-monospace,monospace');
    close.addEventListener('click', function () { setOpen(false); });
    head.appendChild(close);
    body = document.createElement('div');
    body.setAttribute('style', 'overflow:auto;padding:6px 8px;-webkit-overflow-scrolling:touch');
    panel.appendChild(head);
    panel.appendChild(body);
    document.body.appendChild(panel);
    document.body.appendChild(pill);
    render();
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', mount);
  } else {
    mount();
  }
  function describeCtx(ctx) {
    var dest = ctx.destination || {};
    return ctx.state + ' | rate ' + ctx.sampleRate
      + 'Hz | ch ' + (dest.maxChannelCount != null ? dest.maxChannelCount : '?')
      + ' | t=' + ctx.currentTime.toFixed(3);
  }

  function instrument(ctx) {
    log('context created', describeCtx(ctx));
    log('created in gesture', inGesture ? 'YES' : 'NO  <- suspended on iOS');

    // The transition sequence WebKit actually performs. The sampled states at
    // createBufferSource/start tell you what was true at those two instants;
    // this tells you every move in between, which is what distinguishes "never
    // unlocked" from "unlocked, then re-suspended".
    var prevState = ctx.state;
    ctx.addEventListener('statechange', function () {
      log('state change', prevState + ' -> ' + ctx.state + ' | t=' + ctx.currentTime.toFixed(3));
      prevState = ctx.state;
    });

    var resume = ctx.resume;
    ctx.resume = function () {
      var n = seq + 1;
      log('resume() called', 'state=' + ctx.state + (inGesture ? ' (in gesture)' : ' (NOT in gesture)'));
      var p;
      try {
        p = resume.apply(ctx, arguments);
      } catch (e) {
        log('resume() THREW', e && e.message);
        throw e;
      }
      if (p && p.then) {
        p.then(function () { log('resume resolved #' + n, describeCtx(ctx)); },
               function (e) { log('resume REJECTED #' + n, (e && e.message) || e); });
      } else {
        log('resume returned', 'no promise (old WebKit)');
      }
      return p;
    };

    var decode = ctx.decodeAudioData;
    if (decode) {
      ctx.decodeAudioData = function (data) {
        var p = decode.apply(ctx, arguments);
        if (p && p.then) {
          p.then(function (b) {
            log('decoded', b.duration.toFixed(2) + 's | ' + b.numberOfChannels
              + 'ch | ' + b.sampleRate + 'Hz');
          }, function (e) { log('decode FAILED', (e && e.message) || e); });
        }
        return p;
      };
    }

    var create = ctx.createBufferSource;
    ctx.createBufferSource = function () {
      var src = create.apply(ctx, arguments);
      // THE assertion the reviewer asked for, made visible: construction while
      // suspended is itself the defect, not just the start() that follows.
      log('createBufferSource', 'state=' + ctx.state
        + (ctx.state === 'running' ? '' : '  <- CONSTRUCTED WHILE NOT RUNNING'));
      var start = src.start;
      src.start = function () {
        var before = ctx.currentTime;
        log('source.start()', 'state=' + ctx.state + ' | t before=' + before.toFixed(3));
        var r = start.apply(src, arguments);
        setTimeout(function () {
          var after = ctx.currentTime;
          log('+500ms', 'state=' + ctx.state + ' | t=' + after.toFixed(3)
            + (after > before ? ' | CLOCK ADVANCED' : ' | CLOCK FROZEN <- not really running'));
        }, 500);
        return r;
      };
      return src;
    };
  }

  function Wrapped() {
    var ctx = new AC(arguments[0]);
    try { instrument(ctx); } catch (e) { log('instrument failed', e && e.message); }
    return ctx;
  }
  Wrapped.prototype = AC.prototype;
  window.AudioContext = Wrapped;
  if (window.webkitAudioContext) window.webkitAudioContext = Wrapped;

  log('debug build', 'ready — tap Play, then screenshot this panel');
})();
