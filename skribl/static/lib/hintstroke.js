/* THE EMPTY CANVAS'S ONE STROKE (the owner's B, after the "Skribl's first
 * look" mock: "it's gonna happen every time so it should be subtle but magic").
 *
 * Under "Draw anything" (Flip: "Draw page 1") one small stroke writes itself,
 * a line with a loop in it, the way a pen would: a nib leads it, it thickens
 * where the hand pressed and thins where it lifted, and then it stays. It is
 * a recording, not a drawn path: harness/tools/make_hintstroke.py performs it
 * on the real Pad with pen pressure (artdraw.py, the driver every example is
 * drawn with) and writes what the Pad recorded into MARK below.
 *
 * EVERY TIME THE CANVAS IS EMPTY, and only then. It writes when the words
 * appear (the page opens on an empty canvas, a new Skribl, Undo back to
 * nothing) and goes with them at the first stroke: the editors already show
 * and hide the words (`.hidden` on the hint, app.js updateEmptyHint and
 * flip.js updateFlipEmptyHint), so this only watches that class and adds no
 * byte to app.js, which the link player loads too. While the first-open hello
 * is on screen it waits, and writes as the hello lifts away.
 *
 * IN YOUR PEN'S COLOUR, so the canvas shows the ink it is ready with: the
 * editors' `color` (purple until another is picked). A colour that would not
 * show on the canvas's ground (under 3:1, a dark pen on a dark ground) writes
 * in Skribl purple instead, and where purple would not show either, in the
 * words' own colour, which is chosen for that ground (styles.css .light-bg).
 *
 * THE WORDS DO NOT MOVE: the stroke sits under them, placed from the smaller
 * line's bottom, out of the hint's flex column (verify_identity holds the
 * words at the canvas's middle). Reduce Motion: the stroke is there at once,
 * whole, with no nib.
 */
(function () {
  'use strict';

  var doc = document;
  var hint = doc.getElementById('canvasEmptyHint') || doc.getElementById('flipEmptyHint');
  if (!hint || !hint.querySelector('.canvas-empty-sub')) return;

  /* MARK:BEGIN -- written by harness/tools/make_hintstroke.py; do not edit by hand.
   * [x, y, width, ms] in a 200 x 40 box, as the Pad recorded the stroke. */
  var MARK = [[8.1,27.0,2.48,0],[8.3,26.9,2.5,3],[8.4,26.9,2.53,5],[8.5,26.9,2.59,17],[8.6,26.9,2.67,24],[8.7,26.9,2.77,29],[8.8,26.8,2.89,36],[9.0,26.8,3.03,40],[9.1,26.8,3.18,45],[9.3,26.8,3.34,51],[9.4,26.8,3.51,56],[9.9,26.8,3.66,62],[10.4,26.7,3.84,67],[10.9,26.7,4.02,74],[11.5,26.7,4.2,81],[12.1,26.7,4.38,85],[12.7,26.7,4.56,91],[13.3,26.7,4.73,96],[13.9,26.7,4.88,102],[14.6,26.7,5.03,108],[15.4,26.6,5.15,114],[16.2,26.6,5.27,121],[17.0,26.6,5.36,126],[17.9,26.6,5.43,131],[19.0,26.5,5.48,136],[20.1,26.5,5.5,142],[21.4,26.5,5.5,147],[23.0,26.4,5.48,152],[24.7,26.3,5.45,157],[26.8,26.2,5.42,162],[29.2,26.1,5.38,166],[31.9,26.0,5.35,170],[35.0,25.9,5.33,175],[38.2,25.8,5.32,180],[41.4,25.6,5.32,185],[44.6,25.4,5.33,189],[47.6,25.3,5.34,194],[50.6,25.2,5.35,199],[53.5,25.1,5.37,207],[56.0,25.0,5.41,214],[58.1,25.0,5.46,222],[59.8,25.0,5.48,229],[61.5,25.0,5.47,234],[63.3,25.1,5.45,240],[65.6,25.2,5.38,244],[68.2,25.4,5.39,248],[70.3,25.5,5.46,253],[72.0,25.5,5.49,258],[73.5,25.5,5.5,263],[74.9,25.5,5.51,268],[76.2,25.5,5.52,272],[77.5,25.4,5.51,276],[79.0,25.2,5.48,281],[80.6,25.0,5.47,286],[82.3,24.7,5.47,291],[84.0,24.4,5.48,296],[85.6,24.1,5.48,301],[87.2,23.8,5.49,306],[88.6,23.4,5.5,311],[90.0,23.0,5.5,316],[91.3,22.6,5.51,321],[92.5,22.1,5.52,326],[93.6,21.7,5.54,331],[94.6,21.2,5.54,336],[95.5,20.6,5.55,342],[96.3,20.0,5.54,347],[97.2,19.3,5.54,352],[97.9,18.6,5.54,357],[98.6,17.7,5.54,363],[99.3,16.9,5.54,370],[99.9,16.0,5.54,374],[100.4,15.0,5.55,384],[100.7,14.1,5.56,389],[101.0,13.2,5.57,394],[101.1,12.4,5.58,399],[101.1,11.6,5.58,404],[101.0,10.8,5.58,409],[100.6,10.0,5.57,414],[100.2,9.3,5.56,419],[99.6,8.5,5.55,424],[98.9,7.7,5.54,429],[98.1,6.9,5.54,434],[97.2,6.2,5.54,443],[96.3,5.6,5.55,448],[95.4,5.1,5.55,453],[94.5,4.7,5.56,460],[93.7,4.4,5.57,465],[92.9,4.3,5.57,470],[92.1,4.2,5.57,476],[91.2,4.3,5.56,481],[90.3,4.5,5.55,486],[89.3,4.8,5.55,491],[88.3,5.2,5.54,496],[87.3,5.6,5.54,502],[86.4,6.1,5.55,508],[85.5,6.6,5.55,517],[84.8,7.1,5.56,524],[84.1,7.7,5.57,527],[83.5,8.2,5.58,533],[83.1,8.8,5.59,537],[82.7,9.4,5.59,542],[82.5,10.0,5.59,547],[82.3,10.7,5.58,552],[82.1,11.5,5.58,556],[82.1,12.3,5.57,562],[82.1,13.2,5.57,567],[82.1,14.1,5.56,572],[82.2,15.0,5.56,576],[82.4,15.8,5.56,581],[82.6,16.7,5.57,586],[82.9,17.6,5.57,591],[83.2,18.4,5.57,596],[83.5,19.1,5.58,601],[83.9,19.8,5.58,606],[84.4,20.4,5.58,611],[84.9,21.0,5.58,616],[85.5,21.6,5.57,620],[86.1,22.2,5.57,626],[86.8,22.7,5.57,631],[87.6,23.2,5.56,635],[88.4,23.7,5.56,641],[89.2,24.1,5.56,645],[90.2,24.5,5.55,650],[91.1,24.9,5.55,655],[92.2,25.2,5.54,660],[93.2,25.5,5.53,665],[94.4,25.8,5.53,670],[95.6,26.0,5.52,677],[96.9,26.3,5.52,682],[98.2,26.4,5.52,690],[99.5,26.6,5.51,695],[100.9,26.7,5.5,699],[102.4,26.7,5.48,704],[104.1,26.8,5.46,710],[106.0,26.8,5.44,715],[108.2,26.8,5.41,721],[110.8,26.7,5.37,724],[113.8,26.6,5.32,730],[117.1,26.4,5.32,734],[120.4,26.3,5.31,740],[123.5,26.2,5.33,747],[126.8,26.1,5.31,752],[130.2,26.0,5.31,757],[133.4,25.9,5.32,761],[136.7,25.8,5.33,766],[139.8,25.6,5.35,771],[142.6,25.5,5.36,776],[145.1,25.3,5.36,781],[147.4,25.1,5.36,786],[149.5,24.9,5.32,793],[152.0,24.6,5.24,798],[154.5,24.4,5.22,803],[156.8,24.1,5.18,809],[158.9,23.8,5.14,815],[160.9,23.5,5.09,820],[162.8,23.2,5.02,825],[164.5,22.9,4.96,830],[166.2,22.6,4.88,834],[167.8,22.3,4.81,839],[169.4,22.0,4.73,843],[170.8,21.6,4.65,848],[172.0,21.3,4.56,855],[173.1,21.0,4.47,859],[174.1,20.7,4.38,864],[175.1,20.4,4.27,869],[176.0,20.1,4.17,874],[176.9,19.7,4.07,879],[177.8,19.4,3.97,884],[178.7,19.1,3.86,889],[179.5,18.7,3.76,893],[180.2,18.4,3.66,898],[181.0,18.1,3.56,903],[181.6,17.8,3.46,908],[182.3,17.5,3.37,913],[182.9,17.2,3.28,918],[183.5,17.0,3.19,923],[184.2,16.7,3.1,929],[184.7,16.4,3.02,934],[185.3,16.2,2.94,939],[186.0,15.9,2.87,945],[186.5,15.6,2.8,951],[187.1,15.4,2.73,956],[187.6,15.2,2.68,962],[188.1,15.0,2.63,967],[188.5,14.8,2.59,971],[188.8,14.7,2.55,975],[189.1,14.5,2.53,985],[189.4,14.4,2.51,990],[189.7,14.3,2.49,995],[189.9,14.2,2.48,1000]];
  /* MARK:END */
  var BOX_W = 200, BOX_H = 40, CSS_W = 150, GAP = 6;
  var PURPLE = '#7c5cff';
  if (!MARK.length) return;
  var END = MARK[MARK.length - 1][3];

  var cv = doc.createElement('canvas');
  cv.className = 'canvas-empty-stroke';
  cv.setAttribute('aria-hidden', 'true');
  hint.appendChild(cv);
  var ctx = cv.getContext('2d');
  var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)');
  /* 'idle' blank, 'writing', 'done'. Blank until it writes: under the hello
   * it waits empty, so the hello lifts onto words and then the stroke writes,
   * never onto a finished stroke that starts over. */
  var raf = 0, t0 = 0, ink = PURPLE, state = 'idle';

  function rgbOf(hex) {
    var m = /^#?([0-9a-f]{6})$/i.exec(String(hex || '').trim());
    if (!m) return null;
    var n = parseInt(m[1], 16);
    return [n >> 16 & 255, n >> 8 & 255, n & 255];
  }
  function lum(c) {
    function f(u) { u /= 255; return u <= 0.04045 ? u / 12.92 : Math.pow((u + 0.055) / 1.055, 2.4); }
    return 0.2126 * f(c[0]) + 0.7152 * f(c[1]) + 0.0722 * f(c[2]);
  }
  function contrast(a, b) {
    var x = lum(a), y = lum(b);
    return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05);
  }
  /* The pen's colour if it shows on this ground, else purple, else the
   * words' own colour (see the header). Read each time it writes. */
  function pickInk() {
    /* `color` and `bgColor` are the editors' own (app.js, flip.js), read by
     * name as every tool and suite here reads them. */
    var ground = rgbOf(typeof bgColor === 'string' ? bgColor : '') || rgbOf('#0d0f14');
    var pen = typeof color === 'string' ? color : PURPLE;
    var p = rgbOf(pen);
    if (p && contrast(p, ground) >= 3) return pen;
    if (contrast(rgbOf(PURPLE), ground) >= 3) return PURPLE;
    return getComputedStyle(hint.firstElementChild).color;
  }

  /* Under the smaller line, centred, without moving the words. */
  function place() {
    var sub = hint.querySelector('.canvas-empty-sub');
    var dpr = Math.min(window.devicePixelRatio || 1, 3);
    var w = CSS_W, h = Math.round(CSS_W * BOX_H / BOX_W);
    if (cv.width !== Math.round(w * dpr)) { cv.width = Math.round(w * dpr); cv.height = Math.round(h * dpr); }
    cv.style.width = w + 'px';
    cv.style.height = h + 'px';
    cv.style.top = (sub.offsetTop + sub.offsetHeight + GAP) + 'px';
    ctx.setTransform(cv.width / BOX_W, 0, 0, cv.height / BOX_H, 0, 0);
  }

  /* The stroke up to `t` ms: each segment at the mean of its two widths,
   * round-capped, and the last one cut where the pen is. */
  function paint(t) {
    ctx.clearRect(0, 0, BOX_W, BOX_H);
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    ctx.strokeStyle = ink;
    var head = null;
    for (var i = 1; i < MARK.length; i++) {
      var a = MARK[i - 1], b = MARK[i];
      if (a[3] > t) break;
      var f = b[3] <= t ? 1 : (t - a[3]) / ((b[3] - a[3]) || 1);
      var x = a[0] + (b[0] - a[0]) * f, y = a[1] + (b[1] - a[1]) * f;
      ctx.lineWidth = (a[2] + b[2]) / 2;
      ctx.beginPath(); ctx.moveTo(a[0], a[1]); ctx.lineTo(x, y); ctx.stroke();
      head = [x, y];
    }
    /* The nib while it writes: a soft dot of the ink at the pen. */
    if (head && t < END) {
      ctx.save();
      ctx.globalAlpha = 0.35;
      ctx.fillStyle = ink;
      ctx.beginPath(); ctx.arc(head[0], head[1], 3.2, 0, Math.PI * 2); ctx.fill();
      ctx.restore();
    }
  }

  function frame(now) {
    if (!t0) t0 = now;
    var t = now - t0;
    paint(t);
    if (t < END) raf = requestAnimationFrame(frame);
    else { raf = 0; state = 'done'; }
  }

  /* Writes it from the start: the words have just appeared. */
  function write() {
    cancelAnimationFrame(raf); raf = 0; t0 = 0;
    ink = pickInk();
    place();
    if (reduce && reduce.matches) { paint(END); state = 'done'; return; }
    state = 'writing';
    paint(0);
    raf = requestAnimationFrame(frame);
  }
  /* The words are going: it goes with them as it is (their fade carries
   * it), and the next time they show it writes from the start. */
  function stop() { cancelAnimationFrame(raf); raf = 0; }

  /* The hello on the first open covers the canvas: write as it lifts away. */
  function helloUp() {
    var h = doc.getElementById('skriblHello');
    return !!h && doc.documentElement.hasAttribute('data-hello-comes');
  }
  function shown() { return !hint.classList.contains('hidden'); }

  var wasShown = false;
  function sync() {
    var now = shown() && !helloUp();
    if (now && !wasShown) write();
    else if (!now && wasShown) stop();
    wasShown = now;
  }
  new MutationObserver(sync).observe(hint, { attributes: true, attributeFilter: ['class'] });
  /* lib/hello.js takes its element out when it has gone: watched where it is. */
  var helloEl = doc.getElementById('skriblHello');
  if (helloEl && helloEl.parentNode) new MutationObserver(sync).observe(helloEl.parentNode, { childList: true });
  /* The words re-wrap when the canvas changes size; the stroke follows them,
   * repainted whole only once it has been written (resizing clears it). */
  if (window.ResizeObserver) new ResizeObserver(function () { place(); if (state === 'done') paint(END); }).observe(hint);

  if (doc.readyState === 'loading') doc.addEventListener('DOMContentLoaded', sync);
  else sync();
})();
