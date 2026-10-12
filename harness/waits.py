"""Wait for a STATE, not a guessed number of seconds.

The suites slept about thirty minutes in fixed `wait_for_timeout` calls,
written once each and repeated through their loops, much of it after an
upload, a reload or a save: each a guess at how long a decode, an IndexedDB
write or a restore takes on this box. Too short on a slower runner, so a
check read too early; mostly idle time here. These wait for the app's own
signal instead, up to a ceiling well above the old guess.

A WAIT IS NOT AN ASSERTION. On timeout `until` prints a note and returns
False, and the check after it decides, under its own name, rather than the
run dying on a Playwright error with no summary. A sleep that guards an
ABSENCE ("no toast within two seconds") cannot become one of these; it stays
a sleep.

The predicates read the same state the app's own pills report: the media tab
dots and re-add cards, Flip's media spill, the Pad's draft durability.
"""
import time

from playwright.sync_api import TimeoutError as PWTimeout


def until(page, js, name, ms=15000, window=None):
    """Wait for the state JS describes, up to MS.

    WINDOW is the sleep this replaces, in ms. A state can arrive before the
    work behind it ends (the music's dot lights while its decode still runs,
    and a decode that fails late would turn it amber), so once the state is
    here the rest of the old window is settled too: anything the page still
    has in flight that the sleep would have waited for, it still waits for.
    On an instrumented page that is usually a tenth of a second; on one that
    is not, it is the rest of the old sleep."""
    t0 = time.monotonic()
    try:
        page.wait_for_function(js, timeout=ms)
        ok = True
    except PWTimeout:
        print(f"  [NOTE] waited {ms / 1000:.0f}s for {name}; it never came -- the check below decides")
        ok = False
    if ok and window:
        left = window - (time.monotonic() - t0) * 1000
        if left > 0:
            settle(page, left)
    return ok


# Flip, music chosen: its tab dot is lit (not pending) and the media spill to
# IndexedDB has finished, so a reload now can bring it back.
FLIP_MUSIC_SAVED = """() => { const d = document.getElementById('musicTabDot');
    return !!d && !d.hidden && !d.classList.contains('pending')
        && typeof _mediaSpillState !== 'undefined' && _mediaSpillState === 'durable'; }"""

# Flip, music chosen where IndexedDB is missing: the track is loaded (dot
# shown) and the spill has given up, so a reload will have to ask for it back.
FLIP_MUSIC_UNSAVED = """() => { const d = document.getElementById('musicTabDot');
    return !!d && !d.hidden && typeof _mediaSpillState !== 'undefined' && _mediaSpillState === 'failed'; }"""

# Either editor after a reload: the music came back (dot lit, re-add card hidden).
MUSIC_BACK = """() => { const d = document.getElementById('musicTabDot'), c = document.getElementById('musicPending');
    return !!d && !d.hidden && !d.classList.contains('pending') && !!c && c.hidden; }"""

# Either editor after a reload when the bytes could not be kept: amber, and
# the re-add card is showing.
MUSIC_NEEDS_READD = """() => { const d = document.getElementById('musicTabDot'), c = document.getElementById('musicPending');
    return !!d && d.classList.contains('pending') && !!c && !c.hidden; }"""

# Pad, music chosen: its bytes are in IndexedDB and the draft on disk matches
# the drawing (the predicate the Pad's own leave-page guard uses).
PAD_MUSIC_SAVED = ("() => typeof mediaDraft !== 'undefined' && mediaDraft.music === 'durable'"
                   " && typeof draftIsDurable === 'function' && draftIsDurable()")

# Pad after a reload: the track itself is back, not only its dot.
PAD_TRACK_BACK = """() => { const d = document.getElementById('musicTabDot');
    return typeof audioEl !== 'undefined' && !!audioEl && !!audioEl._fileName
        && !!d && !d.hidden && !d.classList.contains('pending'); }"""


# ---------------------------------------------------------------------------
# SETTLE: the general case of the sleeps after a load, a click or a reload.
#
# 570 places slept a fixed 0.6-1.8s after `goto` or `reload` alone. Each
# meant "let the page finish what it is doing", and a page can be asked that
# directly: an init script keeps count of the work it has in flight -- timers,
# fetches and XHRs, IndexedDB transactions, file reads, audio decodes -- and
# `settle(page, ms)` returns as soon as none of it is still due inside the old
# window, fonts are loaded and no finite animation is running.
#
# NEVER WEAKER THAN THE SLEEP IT REPLACES. Anything that would have happened
# before the old sleep ended still has to happen before settle returns: a
# timer due inside the window holds it open, and so does a request in flight.
# A timer due after the window was never seen by the sleep either. At the old
# duration it returns regardless, exactly as the sleep did. A chain of
# animation frames holds it while it keeps asking, so a page that animates
# until the deadline (a replay) gets the old sleep, never less. An infinite
# CSS animation (the recording pulse) does not hold it: it moves no layout.
QUIET_JS = r"""
(() => {
  if (window.__skQuiet) return;
  const q = window.__skQuiet = { timers: new Map(), busy: 0 };
  const now = () => performance.now();
  const _st = window.setTimeout, _ct = window.clearTimeout;
  window.setTimeout = function (fn, ms, ...rest) {
    const due = now() + (Number(ms) || 0);
    let id;
    const wrapped = typeof fn === 'function'
      ? function () { q.timers.delete(id); return fn.apply(this, arguments); }
      : fn;
    id = _st.call(this, wrapped, ms, ...rest);
    if (typeof fn === 'function') q.timers.set(id, due);
    return id;
  };
  window.clearTimeout = function (id) { q.timers.delete(id); return _ct.call(this, id); };
  // An interval holds settle whenever its next tick falls inside the window.
  const _si = window.setInterval, _ci = window.clearInterval;
  window.setInterval = function (fn, ms, ...rest) {
    const period = Math.max(0, Number(ms) || 0);
    let id;
    const wrapped = typeof fn === 'function'
      ? function () { q.timers.set(id, now() + period); return fn.apply(this, arguments); }
      : fn;
    id = _si.call(this, wrapped, ms, ...rest);
    if (typeof fn === 'function') q.timers.set(id, now() + period);
    return id;
  };
  window.clearInterval = function (id) { q.timers.delete(id); return _ci.call(this, id); };
  if (window.requestIdleCallback) { const _ric = window.requestIdleCallback, _cic = window.cancelIdleCallback;
    window.requestIdleCallback = function (fn, opts) {
      let id;
      id = _ric.call(this, function () { q.timers.delete('idle' + id); return fn.apply(this, arguments); }, opts);
      q.timers.set('idle' + id, now()); return id; };
    window.cancelIdleCallback = function (id) { q.timers.delete('idle' + id); return _cic.call(this, id); };
  }
  // A chain of animation frames holds settle until it stops asking: a fit
  // measured over a few frames, a glide done by hand. One that never stops
  // (a replay) holds it to the deadline, which is the old sleep, not less.
  q.lastFrame = -Infinity;
  // A smooth scroll (scroll-behavior: smooth, a drawer's glide) runs no timer
  // and asks for no frame of the page's own, so it is seen by its scroll
  // events: caught on the way down, from the document or any element in it.
  q.lastScroll = -Infinity;
  addEventListener('scroll', () => { q.lastScroll = now(); }, { capture: true, passive: true });
  const _raf = window.requestAnimationFrame;
  window.requestAnimationFrame = function (cb) { q.lastFrame = now(); return _raf.call(this, cb); };
  const hold = p => { q.busy++; const done = () => { q.busy--; };
                      p.then(done, done); return p; };
  const holdAll = (proto, names) => { if (proto) for (const m of names) { const f = proto[m];
    if (typeof f === 'function') proto[m] = function () { return hold(f.apply(this, arguments)); }; } };
  if (window.fetch) { const _f = window.fetch;
    window.fetch = function () { return hold(_f.apply(this, arguments)); }; }
  // A response's body arrives after the fetch itself resolves.
  holdAll(window.Response && Response.prototype, ['json', 'text', 'arrayBuffer', 'blob', 'formData']);
  holdAll(window.Blob && Blob.prototype, ['text', 'arrayBuffer']);
  holdAll(window.HTMLImageElement && HTMLImageElement.prototype, ['decode']);
  holdAll(window.OffscreenCanvas && OffscreenCanvas.prototype, ['convertToBlob']);
  holdAll(window.Clipboard && Clipboard.prototype, ['writeText', 'readText', 'write', 'read']);
  holdAll(window.CacheStorage && CacheStorage.prototype, ['open', 'match', 'keys', 'delete', 'has']);
  holdAll(window.Cache && Cache.prototype, ['add', 'addAll', 'put', 'match', 'delete', 'keys']);
  holdAll(window.OfflineAudioContext && OfflineAudioContext.prototype, ['startRendering']);
  if (window.HTMLCanvasElement && HTMLCanvasElement.prototype.toBlob) {
    const _tb = HTMLCanvasElement.prototype.toBlob;
    HTMLCanvasElement.prototype.toBlob = function (cb, ...rest) {
      q.busy++; let open = true;
      return _tb.call(this, function () { if (open) { open = false; q.busy--; }
                                          return cb && cb.apply(this, arguments); }, ...rest); }; }
  // Opening a database (and its upgrade) comes before any transaction.
  if (window.IDBFactory) for (const m of ['open', 'deleteDatabase']) {
    const _o = IDBFactory.prototype[m];
    IDBFactory.prototype[m] = function () {
      const r = _o.apply(this, arguments); q.busy++;
      let open = true; const end = () => { if (open) { open = false; q.busy--; } };
      r.addEventListener('success', end); r.addEventListener('error', end); r.addEventListener('blocked', end);
      return r; }; }
  const _xs = XMLHttpRequest.prototype.send;
  XMLHttpRequest.prototype.send = function () {
    q.busy++; this.addEventListener('loadend', () => { q.busy--; }, { once: true });
    return _xs.apply(this, arguments); };
  if (window.IDBDatabase) { const _tx = IDBDatabase.prototype.transaction;
    IDBDatabase.prototype.transaction = function () {
      const t = _tx.apply(this, arguments); q.busy++;
      let open = true; const end = () => { if (open) { open = false; q.busy--; } };
      t.addEventListener('complete', end); t.addEventListener('abort', end); t.addEventListener('error', end);
      return t; }; }
  for (const m of ['readAsArrayBuffer', 'readAsDataURL', 'readAsText', 'readAsBinaryString']) {
    const _r = FileReader.prototype[m];
    if (_r) FileReader.prototype[m] = function () {
      q.busy++; this.addEventListener('loadend', () => { q.busy--; }, { once: true });
      return _r.apply(this, arguments); }; }
  // A media or image load holds until it loads or fails, on or off the page.
  const watchSrc = (proto, ok) => {
    const d = Object.getOwnPropertyDescriptor(proto, 'src');
    if (!d || !d.set) return;
    Object.defineProperty(proto, 'src', { configurable: true, enumerable: d.enumerable, get: d.get,
      set(v) {
        if (v) { q.busy++; let open = true;
          const end = () => { if (open) { open = false; q.busy--; } };
          for (const e of [ok, 'error', 'abort', 'emptied']) this.addEventListener(e, end, { once: true }); }
        return d.set.call(this, v); } });
  };
  watchSrc(HTMLImageElement.prototype, 'load');
  watchSrc(HTMLMediaElement.prototype, 'loadedmetadata');
  if (window.createImageBitmap) { const _cib = window.createImageBitmap;
    window.createImageBitmap = function () { return hold(_cib.apply(this, arguments)); }; }
  const AC = window.BaseAudioContext || window.AudioContext;
  if (AC && AC.prototype.decodeAudioData) { const _d = AC.prototype.decodeAudioData;
    AC.prototype.decodeAudioData = function () { return hold(_d.apply(this, arguments)); }; }
  q.quiet = (until) => {
    if (q.busy > 0) return false;
    if (now() - q.lastFrame < 50) return false;   // asked for a frame in the last three
    if (now() - q.lastScroll < 60) return false;  // still scrolling
    for (const due of q.timers.values()) if (due <= until) return false;
    if (document.fonts && document.fonts.status !== 'loaded') return false;
    if (document.getAnimations) for (const a of document.getAnimations()) {
      if (a.playState !== 'running') continue;
      const end = a.effect && a.effect.getComputedTiming ? a.effect.getComputedTiming().endTime : Infinity;
      if (end !== Infinity) return false;
    }
    return document.readyState === 'complete';
  };
})();
"""


def instrument(target):
    """Install the work counter on a browser's or context's future pages."""
    if hasattr(target, "add_init_script"):          # BrowserContext or Page
        target.add_init_script(QUIET_JS)
        return target
    _np, _nc = target.new_page, target.new_context

    def new_context(*a, **k):
        c = _nc(*a, **k); c.add_init_script(QUIET_JS); return c

    def new_page(*a, **k):
        p = _np(*a, **k); p.add_init_script(QUIET_JS); return p

    target.new_context, target.new_page = new_context, new_page
    return target


def settle(page, ms):
    """Return when nothing the page has in flight is due within MS, or at MS.

    Quiet for 100ms (six frames) before it counts, so a handler that
    schedules the next step as the last one finishes is seen, and so is
    layout that settles over a few frames (a fit measured in a ResizeObserver
    or a requestAnimationFrame). A page without the counter (not
    instrumented) gets the plain sleep it had before.

    THE DEADLINE IS KEPT HERE, not in the page: a navigation restarts the
    page's clock, and a deadline read from the old page would hold the new
    one far past the old sleep. Each poll hands the page what is left."""
    end = time.monotonic() + ms / 1000
    try:
        armed = page.evaluate("() => !!window.__skQuiet")
    except Exception:
        armed = False
    if not armed:
        page.wait_for_timeout(ms)
        return
    quiet_since = None
    while True:
        left = (end - time.monotonic()) * 1000
        if left <= 0:
            return
        try:
            q = page.evaluate("(r) => !!(window.__skQuiet && window.__skQuiet.quiet(performance.now() + r))", left)
        except Exception:       # mid-navigation: nothing to ask yet, so not quiet
            q = False
        now = time.monotonic()
        if q:
            if quiet_since is not None and (now - quiet_since) * 1000 >= 100:
                return
            if quiet_since is None:
                quiet_since = now
        else:
            quiet_since = None
        page.wait_for_timeout(min(25, max(1, left)))
